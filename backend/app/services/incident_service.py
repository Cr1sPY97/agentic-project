from datetime import datetime, timezone
from typing import Optional, List, Tuple, Dict, Any
from sqlalchemy.orm import Session
from app.db.models import (
    Incident,
    IncidentStatusHistory,
    IncidentCorrelation,
    User,
    SeverityEnum,
    StatusEnum,
    RoleEnum,
)
from app.schemas.incident import (
    IncidentCreate,
    IncidentUpdate,
    IncidentStatusUpdateRequest,
    IncidentAssignRequest,
    IncidentResolveRequest,
)
from app.repositories.incident_repository import IncidentRepository
from app.repositories.user_repository import UserRepository
from app.services.severity_service import SeverityEngine
from app.services.correlation_service import IncidentCorrelationEngine
from app.services.audit_service import AuditService


class InvalidStatusTransitionError(ValueError):
    pass


class IncidentService:
    # Explicit state transition map defining legal transitions
    VALID_TRANSITIONS = {
        StatusEnum.OPEN.value: {
            StatusEnum.INVESTIGATING.value,
            StatusEnum.MITIGATED.value,
            StatusEnum.RESOLVED.value,
            StatusEnum.CLOSED.value,
        },
        StatusEnum.INVESTIGATING.value: {
            StatusEnum.MITIGATED.value,
            StatusEnum.RESOLVED.value,
            StatusEnum.CLOSED.value,
            StatusEnum.OPEN.value,
        },
        StatusEnum.MITIGATED.value: {
            StatusEnum.RESOLVED.value,
            StatusEnum.INVESTIGATING.value,
            StatusEnum.OPEN.value,
            StatusEnum.CLOSED.value,
        },
        StatusEnum.RESOLVED.value: {
            StatusEnum.CLOSED.value,
            StatusEnum.INVESTIGATING.value,
            StatusEnum.OPEN.value,
        },
        StatusEnum.CLOSED.value: {
            StatusEnum.OPEN.value,  # Allow reopening
        },
    }

    def __init__(self, db: Session):
        self.db = db
        self.incident_repo = IncidentRepository(db)
        self.user_repo = UserRepository(db)
        self.audit_service = AuditService(db)

    def create_incident(self, data: IncidentCreate, creator: Optional[User] = None) -> Incident:
        # Calculate initial deterministic severity if omitted
        initial_severity = data.severity
        if not initial_severity:
            initial_severity = SeverityEngine.calculate_severity(
                service_name=data.service_name,
                environment=data.environment.value,
                error_message=data.error_message,
                stack_trace=data.stack_trace,
                error_frequency=data.error_frequency,
                affected_users=data.affected_users,
                request_metadata=data.request_metadata,
            )

        incident = Incident(
            title=data.title,
            service_name=data.service_name,
            environment=data.environment.value,
            severity=initial_severity.value if isinstance(initial_severity, SeverityEnum) else initial_severity,
            status=StatusEnum.OPEN.value,
            error_message=data.error_message,
            stack_trace=data.stack_trace,
            logs=data.logs,
            affected_endpoint=data.affected_endpoint,
            request_metadata=data.request_metadata,
            error_frequency=data.error_frequency,
            affected_users=data.affected_users,
            deployment_version=data.deployment_version,
            additional_context=data.additional_context,
            created_by_id=creator.id if creator else None,
        )
        created = self.incident_repo.create(incident)

        # Record initial status history
        self.incident_repo.add_status_history(
            incident_id=created.id,
            old_status="NONE",
            new_status=StatusEnum.OPEN.value,
            changed_by_id=creator.id if creator else None,
            notes="Incident received and registered.",
        )

        # Run correlation matching against recent incidents
        recent_incidents = self.incident_repo.get_recent_incidents(
            exclude_id=created.id,
            hours=48,
            limit=50,
        )
        correlations = IncidentCorrelationEngine.find_correlations(created, recent_incidents)
        for match in correlations:
            self.incident_repo.add_correlation(
                incident_id=created.id,
                related_incident_id=match.related_incident.id,
                correlation_score=match.score,
                reason=match.reason,
            )

        # Record audit log
        self.audit_service.log_event(
            action="INCIDENT_CREATED",
            resource_type="incident",
            resource_id=str(created.id),
            actor=creator,
            details={
                "title": created.title,
                "service": created.service_name,
                "severity": created.severity,
                "correlations_found": len(correlations),
            },
        )

        return created

    def get_incident(self, incident_id: int) -> Optional[Incident]:
        return self.incident_repo.get_by_id(incident_id)

    def list_incidents(
        self,
        status: Optional[str] = None,
        severity: Optional[str] = None,
        service_name: Optional[str] = None,
        environment: Optional[str] = None,
        search: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        page: int = 1,
        size: int = 20,
    ) -> Tuple[List[Incident], int]:
        return self.incident_repo.list_incidents(
            status=status,
            severity=severity,
            service_name=service_name,
            environment=environment,
            search=search,
            start_date=start_date,
            end_date=end_date,
            page=page,
            size=size,
        )

    def update_incident(self, incident_id: int, data: IncidentUpdate, actor: Optional[User] = None) -> Incident:
        incident = self.get_incident(incident_id)
        if not incident:
            raise ValueError(f"Incident {incident_id} not found.")

        updated_fields = {}
        for field, value in data.model_dump(exclude_unset=True).items():
            if value is not None:
                if field == "severity" and isinstance(value, SeverityEnum):
                    value = value.value
                setattr(incident, field, value)
                updated_fields[field] = value

        saved = self.incident_repo.update(incident)

        self.audit_service.log_event(
            action="INCIDENT_UPDATED",
            resource_type="incident",
            resource_id=str(incident.id),
            actor=actor,
            details={"updated_fields": updated_fields},
        )
        return saved

    def update_status(
        self,
        incident_id: int,
        target_status: StatusEnum,
        notes: Optional[str] = None,
        actor: Optional[User] = None,
    ) -> Incident:
        incident = self.get_incident(incident_id)
        if not incident:
            raise ValueError(f"Incident {incident_id} not found.")

        current_status = incident.status
        new_status = target_status.value if isinstance(target_status, StatusEnum) else target_status

        if current_status == new_status:
            return incident

        valid_targets = self.VALID_TRANSITIONS.get(current_status, set())
        if new_status not in valid_targets:
            raise InvalidStatusTransitionError(
                f"Invalid status transition from '{current_status}' to '{new_status}'. Allowed transitions: {sorted(list(valid_targets))}"
            )

        incident.status = new_status

        if new_status in (StatusEnum.RESOLVED.value, StatusEnum.CLOSED.value):
            if not incident.resolved_at:
                incident.resolved_at = datetime.now(timezone.utc)
        elif new_status in (StatusEnum.OPEN.value, StatusEnum.INVESTIGATING.value):
            incident.resolved_at = None

        saved = self.incident_repo.update(incident)

        self.incident_repo.add_status_history(
            incident_id=saved.id,
            old_status=current_status,
            new_status=new_status,
            changed_by_id=actor.id if actor else None,
            notes=notes,
        )

        self.audit_service.log_event(
            action="STATUS_CHANGED",
            resource_type="incident",
            resource_id=str(saved.id),
            actor=actor,
            details={"old_status": current_status, "new_status": new_status, "notes": notes or ""},
        )
        return saved

    def assign_incident(
        self, incident_id: int, assigned_to_id: int, actor: Optional[User] = None
    ) -> Incident:
        incident = self.get_incident(incident_id)
        if not incident:
            raise ValueError(f"Incident {incident_id} not found.")

        assignee = self.user_repo.get_by_id(assigned_to_id)
        if not assignee:
            raise ValueError(f"User {assigned_to_id} does not exist.")

        incident.assigned_to_id = assignee.id
        
        # If incident was OPEN, move to INVESTIGATING automatically upon assignment
        if incident.status == StatusEnum.OPEN.value:
            incident.status = StatusEnum.INVESTIGATING.value
            self.incident_repo.add_status_history(
                incident_id=incident.id,
                old_status=StatusEnum.OPEN.value,
                new_status=StatusEnum.INVESTIGATING.value,
                changed_by_id=actor.id if actor else None,
                notes=f"Auto-transitioned to INVESTIGATING upon assignment to @{assignee.username}",
            )

        saved = self.incident_repo.update(incident)

        self.audit_service.log_event(
            action="INCIDENT_ASSIGNED",
            resource_type="incident",
            resource_id=str(saved.id),
            actor=actor,
            details={"assigned_to_id": assignee.id, "assigned_to_username": assignee.username},
        )
        return saved

    def resolve_incident(
        self, incident_id: int, notes: Optional[str] = "Incident resolved", actor: Optional[User] = None
    ) -> Incident:
        return self.update_status(
            incident_id=incident_id,
            target_status=StatusEnum.RESOLVED,
            notes=notes,
            actor=actor,
        )

    def delete_incident(self, incident_id: int, actor: Optional[User] = None) -> None:
        incident = self.get_incident(incident_id)
        if not incident:
            raise ValueError(f"Incident {incident_id} not found.")

        self.incident_repo.delete(incident)

        self.audit_service.log_event(
            action="INCIDENT_DELETED",
            resource_type="incident",
            resource_id=str(incident_id),
            actor=actor,
            details={"title": incident.title, "service": incident.service_name},
        )

    def get_correlations(self, incident_id: int) -> List[IncidentCorrelation]:
        return self.incident_repo.get_correlations(incident_id)

    def get_status_history(self, incident_id: int) -> List[IncidentStatusHistory]:
        return self.incident_repo.get_status_history(incident_id)

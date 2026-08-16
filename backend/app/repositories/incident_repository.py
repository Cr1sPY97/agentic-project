from datetime import datetime, timezone, timedelta
from typing import Optional, List, Tuple
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc, func, and_, or_
from app.db.models import (
    Incident,
    IncidentStatusHistory,
    IncidentCorrelation,
    IncidentAnalysis,
    SeverityEnum,
    StatusEnum,
    EnvironmentEnum,
)


class IncidentRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, incident_id: int) -> Optional[Incident]:
        return (
            self.db.query(Incident)
            .options(
                joinedload(Incident.creator),
                joinedload(Incident.assignee),
                joinedload(Incident.analyses),
            )
            .filter(Incident.id == incident_id)
            .first()
        )

    def create(self, incident: Incident) -> Incident:
        self.db.add(incident)
        self.db.commit()
        self.db.refresh(incident)
        return incident

    def update(self, incident: Incident) -> Incident:
        self.db.commit()
        self.db.refresh(incident)
        return incident

    def delete(self, incident: Incident) -> None:
        self.db.delete(incident)
        self.db.commit()

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
        query = self.db.query(Incident).options(
            joinedload(Incident.creator),
            joinedload(Incident.assignee),
            joinedload(Incident.analyses),
        )

        if status:
            query = query.filter(Incident.status == status)
        if severity:
            query = query.filter(Incident.severity == severity)
        if service_name:
            query = query.filter(Incident.service_name.ilike(f"%{service_name}%"))
        if environment:
            query = query.filter(Incident.environment == environment)
        if search:
            query = query.filter(
                or_(
                    Incident.title.ilike(f"%{search}%"),
                    Incident.error_message.ilike(f"%{search}%"),
                    Incident.service_name.ilike(f"%{search}%"),
                )
            )
        if start_date:
            query = query.filter(Incident.created_at >= start_date)
        if end_date:
            query = query.filter(Incident.created_at <= end_date)

        total = query.count()
        offset = (page - 1) * size
        items = query.order_by(desc(Incident.created_at)).offset(offset).limit(size).all()

        return items, total

    def get_recent_incidents(
        self,
        exclude_id: Optional[int] = None,
        service_name: Optional[str] = None,
        environment: Optional[str] = None,
        hours: int = 48,
        limit: int = 50,
    ) -> List[Incident]:
        since = datetime.now(timezone.utc) - timedelta(hours=hours)
        query = self.db.query(Incident).filter(Incident.created_at >= since)
        if exclude_id:
            query = query.filter(Incident.id != exclude_id)
        if service_name:
            query = query.filter(Incident.service_name == service_name)
        if environment:
            query = query.filter(Incident.environment == environment)
        return query.order_by(desc(Incident.created_at)).limit(limit).all()

    def add_status_history(
        self,
        incident_id: int,
        old_status: str,
        new_status: str,
        changed_by_id: Optional[int] = None,
        notes: Optional[str] = None,
    ) -> IncidentStatusHistory:
        history = IncidentStatusHistory(
            incident_id=incident_id,
            old_status=old_status,
            new_status=new_status,
            changed_by_id=changed_by_id,
            notes=notes,
        )
        self.db.add(history)
        self.db.commit()
        self.db.refresh(history)
        return history

    def get_status_history(self, incident_id: int) -> List[IncidentStatusHistory]:
        return (
            self.db.query(IncidentStatusHistory)
            .options(joinedload(IncidentStatusHistory.changed_by))
            .filter(IncidentStatusHistory.incident_id == incident_id)
            .order_by(desc(IncidentStatusHistory.created_at))
            .all()
        )

    def add_correlation(
        self,
        incident_id: int,
        related_incident_id: int,
        correlation_score: float,
        reason: str,
    ) -> IncidentCorrelation:
        correlation = IncidentCorrelation(
            incident_id=incident_id,
            related_incident_id=related_incident_id,
            correlation_score=correlation_score,
            reason=reason,
        )
        self.db.add(correlation)
        self.db.commit()
        self.db.refresh(correlation)
        return correlation

    def get_correlations(self, incident_id: int) -> List[IncidentCorrelation]:
        return (
            self.db.query(IncidentCorrelation)
            .options(joinedload(IncidentCorrelation.related_incident))
            .filter(IncidentCorrelation.incident_id == incident_id)
            .order_by(desc(IncidentCorrelation.correlation_score))
            .all()
        )

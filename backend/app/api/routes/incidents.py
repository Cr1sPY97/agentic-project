from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
import math
from app.db.database import get_db
from app.db.models import User, RoleEnum, StatusEnum, SeverityEnum, EnvironmentEnum
from app.schemas.incident import (
    IncidentCreate,
    IncidentUpdate,
    IncidentResponse,
    IncidentListResponse,
    IncidentAssignRequest,
    IncidentStatusUpdateRequest,
    IncidentResolveRequest,
    IncidentCorrelationResponse,
    IncidentStatusHistoryResponse,
)
from app.schemas.audit import AuditLogResponse
from app.schemas.stats import IncidentDashboardStats
from app.services.incident_service import IncidentService, InvalidStatusTransitionError
from app.services.stats_service import StatsService
from app.services.audit_service import AuditService
from app.api.dependencies import get_current_user, require_roles

router = APIRouter()


def _format_incident_response(incident) -> IncidentResponse:
    latest_analysis = incident.analyses[0] if incident.analyses else None
    resp = IncidentResponse.model_validate(incident)
    if latest_analysis:
        resp.latest_analysis = latest_analysis
    return resp


@router.get("/stats", response_model=IncidentDashboardStats, tags=["Dashboard & Metrics"])
def get_incident_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Dashboard metrics and statistics endpoint.
    Aggregates incident counts by severity, status, environment, top services, MTTR, and AI-assisted rates.
    """
    service = StatsService(db)
    return service.get_dashboard_stats()


@router.post("", response_model=IncidentResponse, status_code=status.HTTP_201_CREATED)
def create_incident(
    incident_in: IncidentCreate,
    current_user: User = Depends(require_roles(RoleEnum.ADMIN, RoleEnum.RESPONDER)),
    db: Session = Depends(get_db),
):
    """
    Ingest a new service incident.
    Calculates deterministic rule-based initial severity and runs incident correlation.
    """
    service = IncidentService(db)
    created = service.create_incident(incident_in, creator=current_user)
    return _format_incident_response(created)


@router.get("", response_model=IncidentListResponse)
def list_incidents(
    status: Optional[str] = Query(None, description="Filter by status (OPEN, INVESTIGATING, MITIGATED, RESOLVED, CLOSED)"),
    severity: Optional[str] = Query(None, description="Filter by severity (LOW, MEDIUM, HIGH, CRITICAL)"),
    service_name: Optional[str] = Query(None, description="Filter by service name"),
    environment: Optional[str] = Query(None, description="Filter by environment (production, staging, development)"),
    search: Optional[str] = Query(None, description="Keyword search in title, service, and error message"),
    start_date: Optional[datetime] = Query(None, description="Start date filter (ISO format)"),
    end_date: Optional[datetime] = Query(None, description="End date filter (ISO format)"),
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Items per page"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Paginated incident list with filtering and search capabilities.
    """
    service = IncidentService(db)
    items, total = service.list_incidents(
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
    pages = math.ceil(total / size) if size > 0 else 1
    return {
        "items": [_format_incident_response(item) for item in items],
        "total": total,
        "page": page,
        "size": size,
        "pages": pages,
    }


@router.get("/{incident_id}", response_model=IncidentResponse)
def get_incident(
    incident_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve full incident details by ID."""
    service = IncidentService(db)
    incident = service.get_incident(incident_id)
    if not incident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident {incident_id} not found",
        )
    return _format_incident_response(incident)


@router.patch("/{incident_id}", response_model=IncidentResponse)
def update_incident(
    incident_id: int,
    update_in: IncidentUpdate,
    current_user: User = Depends(require_roles(RoleEnum.ADMIN, RoleEnum.RESPONDER)),
    db: Session = Depends(get_db),
):
    """Update mutable incident attributes."""
    service = IncidentService(db)
    try:
        updated = service.update_incident(incident_id, update_in, actor=current_user)
        return _format_incident_response(updated)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.delete("/{incident_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_incident(
    incident_id: int,
    current_user: User = Depends(require_roles(RoleEnum.ADMIN)),
    db: Session = Depends(get_db),
):
    """Delete an incident. Restricted to ADMIN."""
    service = IncidentService(db)
    try:
        service.delete_incident(incident_id, actor=current_user)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.post("/{incident_id}/assign", response_model=IncidentResponse)
def assign_incident(
    incident_id: int,
    assign_in: IncidentAssignRequest,
    current_user: User = Depends(require_roles(RoleEnum.ADMIN, RoleEnum.RESPONDER)),
    db: Session = Depends(get_db),
):
    """Assign an on-call responder to the incident."""
    service = IncidentService(db)
    try:
        updated = service.assign_incident(
            incident_id=incident_id,
            assigned_to_id=assign_in.assigned_to_id,
            actor=current_user,
        )
        return _format_incident_response(updated)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.post("/{incident_id}/status", response_model=IncidentResponse)
def update_incident_status(
    incident_id: int,
    status_in: IncidentStatusUpdateRequest,
    current_user: User = Depends(require_roles(RoleEnum.ADMIN, RoleEnum.RESPONDER)),
    db: Session = Depends(get_db),
):
    """
    Transition incident lifecycle state (OPEN -> INVESTIGATING -> MITIGATED -> RESOLVED -> CLOSED).
    Enforces strict valid transition rules and records status history.
    """
    service = IncidentService(db)
    try:
        updated = service.update_status(
            incident_id=incident_id,
            target_status=status_in.status,
            notes=status_in.notes,
            actor=current_user,
        )
        return _format_incident_response(updated)
    except InvalidStatusTransitionError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.post("/{incident_id}/resolve", response_model=IncidentResponse)
def resolve_incident(
    incident_id: int,
    resolve_in: IncidentResolveRequest = IncidentResolveRequest(),
    current_user: User = Depends(require_roles(RoleEnum.ADMIN, RoleEnum.RESPONDER)),
    db: Session = Depends(get_db),
):
    """Fast resolve endpoint to transition incident directly to RESOLVED."""
    service = IncidentService(db)
    try:
        updated = service.resolve_incident(
            incident_id=incident_id,
            notes=resolve_in.notes,
            actor=current_user,
        )
        return _format_incident_response(updated)
    except InvalidStatusTransitionError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.get("/{incident_id}/correlations", response_model=List[IncidentCorrelationResponse])
def get_incident_correlations(
    incident_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Fetch correlated cascade or related incidents discovered by the correlation engine."""
    service = IncidentService(db)
    correlations = service.get_correlations(incident_id)
    
    results = []
    for c in correlations:
        resp = IncidentCorrelationResponse.model_validate(c)
        if c.related_incident:
            resp.related_service_name = c.related_incident.service_name
            resp.related_title = c.related_incident.title
            resp.related_status = c.related_incident.status
        results.append(resp)
    return results


@router.get("/{incident_id}/status-history", response_model=List[IncidentStatusHistoryResponse])
def get_incident_status_history(
    incident_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Fetch lifecycle status transition history."""
    service = IncidentService(db)
    history = service.get_status_history(incident_id)
    results = []
    for h in history:
        resp = IncidentStatusHistoryResponse.model_validate(h)
        if h.changed_by:
            resp.changed_by_username = h.changed_by.username
        results.append(resp)
    return results


@router.get("/{incident_id}/audit", response_model=List[AuditLogResponse])
def get_incident_audit_trail(
    incident_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Fetch complete immutable audit trail for the incident."""
    audit_service = AuditService(db)
    logs = audit_service.get_logs_for_resource("incident", str(incident_id))
    return logs

from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.db.models import User, RoleEnum
from app.schemas.audit import AuditLogListResponse
from app.services.audit_service import AuditService
from app.api.dependencies import require_roles

router = APIRouter()


@router.get("", response_model=AuditLogListResponse)
def list_audit_logs(
    action: Optional[str] = Query(None, description="Filter by action name"),
    resource_type: Optional[str] = Query(None, description="Filter by resource type"),
    resource_id: Optional[str] = Query(None, description="Filter by resource ID"),
    actor_id: Optional[int] = Query(None, description="Filter by actor ID"),
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=200),
    current_user: User = Depends(require_roles(RoleEnum.ADMIN)),
    db: Session = Depends(get_db),
):
    """
    Query platform audit log trail. Restricted to ADMIN.
    """
    audit_service = AuditService(db)
    items, total = audit_service.list_logs(
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        actor_id=actor_id,
        page=page,
        size=size,
    )
    return {"items": items, "total": total}

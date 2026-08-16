from typing import Optional, Dict, Any, List, Tuple
from sqlalchemy.orm import Session
from app.db.models import AuditLog, User
from app.repositories.audit_repository import AuditRepository


class AuditService:
    def __init__(self, db: Session):
        self.db = db
        self.repository = AuditRepository(db)

    def log_event(
        self,
        action: str,
        resource_type: str,
        resource_id: Optional[str] = None,
        actor: Optional[User] = None,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
    ) -> AuditLog:
        entry = AuditLog(
            actor_id=actor.id if actor else None,
            actor_username=actor.username if actor else "system",
            action=action,
            resource_type=resource_type,
            resource_id=str(resource_id) if resource_id is not None else None,
            details=details or {},
            ip_address=ip_address,
        )
        return self.repository.create(entry)

    def list_logs(
        self,
        action: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        actor_id: Optional[int] = None,
        page: int = 1,
        size: int = 50,
    ) -> Tuple[List[AuditLog], int]:
        return self.repository.list_logs(
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            actor_id=actor_id,
            page=page,
            size=size,
        )

    def get_logs_for_resource(self, resource_type: str, resource_id: str) -> List[AuditLog]:
        return self.repository.get_by_resource(resource_type, resource_id)

from typing import Optional, List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import desc
from app.db.models import AuditLog


class AuditRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, log_entry: AuditLog) -> AuditLog:
        self.db.add(log_entry)
        self.db.commit()
        self.db.refresh(log_entry)
        return log_entry

    def list_logs(
        self,
        action: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        actor_id: Optional[int] = None,
        page: int = 1,
        size: int = 50,
    ) -> Tuple[List[AuditLog], int]:
        query = self.db.query(AuditLog)
        if action:
            query = query.filter(AuditLog.action == action)
        if resource_type:
            query = query.filter(AuditLog.resource_type == resource_type)
        if resource_id:
            query = query.filter(AuditLog.resource_id == str(resource_id))
        if actor_id:
            query = query.filter(AuditLog.actor_id == actor_id)

        total = query.count()
        offset = (page - 1) * size
        items = query.order_by(desc(AuditLog.created_at)).offset(offset).limit(size).all()
        return items, total

    def get_by_resource(self, resource_type: str, resource_id: str) -> List[AuditLog]:
        return (
            self.db.query(AuditLog)
            .filter(AuditLog.resource_type == resource_type, AuditLog.resource_id == str(resource_id))
            .order_by(desc(AuditLog.created_at))
            .all()
        )

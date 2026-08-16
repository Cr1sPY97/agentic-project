from datetime import datetime, timezone
import enum
from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
    ForeignKey,
    Float,
    JSON,
    Boolean,
)
from sqlalchemy.orm import relationship
from app.db.database import Base


class RoleEnum(str, enum.Enum):
    ADMIN = "ADMIN"
    RESPONDER = "RESPONDER"
    VIEWER = "VIEWER"


class SeverityEnum(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class StatusEnum(str, enum.Enum):
    OPEN = "OPEN"
    INVESTIGATING = "INVESTIGATING"
    MITIGATED = "MITIGATED"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"


class EnvironmentEnum(str, enum.Enum):
    PRODUCTION = "production"
    STAGING = "staging"
    DEVELOPMENT = "development"


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(64), unique=True, index=True, nullable=False)
    email = Column(String(128), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(32), nullable=False, default=RoleEnum.VIEWER.value)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    created_incidents = relationship("Incident", back_populates="creator", foreign_keys="Incident.created_by_id")
    assigned_incidents = relationship("Incident", back_populates="assignee", foreign_keys="Incident.assigned_to_id")
    audit_logs = relationship("AuditLog", back_populates="actor")


class Incident(Base):
    __tablename__ = "incidents"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False, index=True)
    service_name = Column(String(128), index=True, nullable=False)
    environment = Column(String(64), index=True, nullable=False, default=EnvironmentEnum.PRODUCTION.value)
    severity = Column(String(32), default=SeverityEnum.LOW.value, nullable=False, index=True)
    ai_severity = Column(String(32), nullable=True)
    status = Column(String(32), default=StatusEnum.OPEN.value, nullable=False, index=True)
    
    error_message = Column(Text, nullable=False)
    stack_trace = Column(Text, nullable=True)
    logs = Column(Text, nullable=True)
    affected_endpoint = Column(String(255), nullable=True)
    request_metadata = Column(JSON, nullable=True)
    
    error_frequency = Column(Integer, default=1, nullable=False)  # Occurrences/RPM
    affected_users = Column(Integer, default=0, nullable=False)
    deployment_version = Column(String(64), nullable=True)
    additional_context = Column(JSON, nullable=True)

    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    assigned_to_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)
    resolved_at = Column(DateTime(timezone=True), nullable=True)

    creator = relationship("User", foreign_keys=[created_by_id], back_populates="created_incidents")
    assignee = relationship("User", foreign_keys=[assigned_to_id], back_populates="assigned_incidents")
    analyses = relationship("IncidentAnalysis", back_populates="incident", cascade="all, delete-orphan", order_by="desc(IncidentAnalysis.created_at)")
    status_history = relationship("IncidentStatusHistory", back_populates="incident", cascade="all, delete-orphan", order_by="IncidentStatusHistory.created_at")
    correlations = relationship("IncidentCorrelation", foreign_keys="IncidentCorrelation.incident_id", back_populates="incident", cascade="all, delete-orphan")


class IncidentAnalysis(Base):
    __tablename__ = "incident_analyses"

    id = Column(Integer, primary_key=True, index=True)
    incident_id = Column(Integer, ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False, index=True)
    model_provider = Column(String(64), nullable=False)
    model_name = Column(String(64), nullable=False)
    prompt_version = Column(String(64), nullable=False)
    
    classification = Column(String(128), nullable=False)
    ai_severity = Column(String(32), nullable=False)
    probable_root_cause = Column(Text, nullable=False)
    confidence_score = Column(Float, nullable=False)
    impact_assessment = Column(Text, nullable=False)
    evidence = Column(JSON, nullable=False, default=list)
    immediate_mitigation_steps = Column(JSON, nullable=False, default=list)
    recommended_remediation_steps = Column(JSON, nullable=False, default=list)
    prevention_recommendations = Column(JSON, nullable=False, default=list)
    human_readable_summary = Column(Text, nullable=False)
    raw_response = Column(JSON, nullable=True)
    
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    incident = relationship("Incident", back_populates="analyses")


class IncidentStatusHistory(Base):
    __tablename__ = "incident_status_history"

    id = Column(Integer, primary_key=True, index=True)
    incident_id = Column(Integer, ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False, index=True)
    old_status = Column(String(32), nullable=False)
    new_status = Column(String(32), nullable=False)
    changed_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    incident = relationship("Incident", back_populates="status_history")
    changed_by = relationship("User")


class IncidentCorrelation(Base):
    __tablename__ = "incident_correlations"

    id = Column(Integer, primary_key=True, index=True)
    incident_id = Column(Integer, ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False, index=True)
    related_incident_id = Column(Integer, ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False, index=True)
    correlation_score = Column(Float, nullable=False)
    reason = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    incident = relationship("Incident", foreign_keys=[incident_id], back_populates="correlations")
    related_incident = relationship("Incident", foreign_keys=[related_incident_id])


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    actor_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    actor_username = Column(String(64), nullable=True)
    action = Column(String(64), nullable=False, index=True)
    resource_type = Column(String(64), nullable=False, index=True)
    resource_id = Column(String(64), nullable=True, index=True)
    details = Column(JSON, nullable=True)
    ip_address = Column(String(64), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False, index=True)

    actor = relationship("User", back_populates="audit_logs")

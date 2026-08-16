from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict
from app.db.models import SeverityEnum, StatusEnum, EnvironmentEnum
from app.schemas.user import UserResponse
from app.schemas.analysis import IncidentAnalysisResponse


class IncidentBase(BaseModel):
    title: str = Field(..., min_length=3, max_length=255)
    service_name: str = Field(..., min_length=2, max_length=128)
    environment: EnvironmentEnum = EnvironmentEnum.PRODUCTION
    error_message: str = Field(..., min_length=1)
    stack_trace: Optional[str] = None
    logs: Optional[str] = None
    affected_endpoint: Optional[str] = None
    request_metadata: Optional[Dict[str, Any]] = None
    error_frequency: int = Field(1, ge=1, description="Errors per minute or recurrence count")
    affected_users: int = Field(0, ge=0, description="Estimated number of affected users")
    deployment_version: Optional[str] = None
    additional_context: Optional[Dict[str, Any]] = None


class IncidentCreate(IncidentBase):
    severity: Optional[SeverityEnum] = Field(
        None,
        description="Optional manual severity override. If omitted, calculated deterministically via rules engine"
    )


class IncidentUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=3, max_length=255)
    severity: Optional[SeverityEnum] = None
    error_frequency: Optional[int] = Field(None, ge=1)
    affected_users: Optional[int] = Field(None, ge=0)
    deployment_version: Optional[str] = None
    additional_context: Optional[Dict[str, Any]] = None


class IncidentAssignRequest(BaseModel):
    assigned_to_id: int


class IncidentStatusUpdateRequest(BaseModel):
    status: StatusEnum
    notes: Optional[str] = Field(None, max_length=1000)


class IncidentResolveRequest(BaseModel):
    notes: Optional[str] = Field("Incident resolved", max_length=1000)


class IncidentCorrelationResponse(BaseModel):
    id: int
    incident_id: int
    related_incident_id: int
    correlation_score: float
    reason: str
    created_at: datetime
    related_service_name: Optional[str] = None
    related_title: Optional[str] = None
    related_status: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class IncidentStatusHistoryResponse(BaseModel):
    id: int
    incident_id: int
    old_status: str
    new_status: str
    changed_by_id: Optional[int] = None
    changed_by_username: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class IncidentResponse(IncidentBase):
    id: int
    severity: SeverityEnum
    ai_severity: Optional[SeverityEnum] = None
    status: StatusEnum
    created_by_id: Optional[int] = None
    assigned_to_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    resolved_at: Optional[datetime] = None
    creator: Optional[UserResponse] = None
    assignee: Optional[UserResponse] = None
    latest_analysis: Optional[IncidentAnalysisResponse] = None

    model_config = ConfigDict(from_attributes=True)


class IncidentListResponse(BaseModel):
    items: List[IncidentResponse]
    total: int
    page: int
    size: int
    pages: int

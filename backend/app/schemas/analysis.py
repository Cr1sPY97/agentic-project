from datetime import datetime
from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field, field_validator, ConfigDict
from app.db.models import SeverityEnum


class AIAnalysisStructuredOutput(BaseModel):
    """
    Strict schema representing validated LLM structured output.
    """
    classification: str = Field(
        ...,
        description="Category of incident e.g. 'Database Connection Exhaustion', 'Authentication Latency Spike', 'Memory Leak', 'NullPointerException'"
    )
    severity: SeverityEnum = Field(
        ...,
        description="AI-assessed severity level: LOW, MEDIUM, HIGH, or CRITICAL"
    )
    probable_root_cause: str = Field(
        ...,
        description="Detailed technical hypothesis of the primary root cause grounded solely in the evidence"
    )
    confidence_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Diagnostic confidence between 0.0 (uncertain) and 1.0 (verified by unambiguous stack trace/logs)"
    )
    impact_assessment: str = Field(
        ...,
        description="Impact on users, dependent services, SLAs, and data integrity"
    )
    evidence: List[str] = Field(
        default_factory=list,
        description="List of observed, factual evidence lines extracted from logs, stack trace, and metrics"
    )
    immediate_mitigation_steps: List[str] = Field(
        default_factory=list,
        description="Fast tactical actions to arrest downtime immediately (e.g. restart worker, scale pool, rollback deploy)"
    )
    recommended_remediation_steps: List[str] = Field(
        default_factory=list,
        description="Permanent architectural, code, or configuration fixes to resolve root cause"
    )
    prevention_recommendations: List[str] = Field(
        default_factory=list,
        description="Long-term resiliency improvements, alerts, circuit breakers, and runbooks"
    )
    human_readable_summary: str = Field(
        ...,
        description="Clear executive/SRE summary explaining what happened, why, and what is being done"
    )

    @field_validator("confidence_score")
    @classmethod
    def validate_confidence(cls, v: float) -> float:
        return round(float(v), 2)


class AnalysisTriggerRequest(BaseModel):
    run_async: bool = Field(False, description="If True, process AI analysis in background")
    custom_context: Optional[str] = Field(None, description="Optional extra diagnostic hints or runbook context")


class IncidentAnalysisResponse(BaseModel):
    id: int
    incident_id: int
    model_provider: str
    model_name: str
    prompt_version: str
    classification: str
    ai_severity: str
    probable_root_cause: str
    confidence_score: float
    impact_assessment: str
    evidence: List[str]
    immediate_mitigation_steps: List[str]
    recommended_remediation_steps: List[str]
    prevention_recommendations: List[str]
    human_readable_summary: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

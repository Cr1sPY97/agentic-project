from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from app.db.models import Incident, IncidentAnalysis, User, SeverityEnum
from app.repositories.analysis_repository import AnalysisRepository
from app.repositories.incident_repository import IncidentRepository
from app.services.audit_service import AuditService
from app.ai.prompts import get_prompt, build_incident_user_prompt
from app.ai.client import AIClientFactory, HeuristicSREEngineClient
from app.ai.parser import parse_structured_ai_response
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("app.services.ai_analysis")


class AIAnalysisService:
    def __init__(self, db: Session):
        self.db = db
        self.analysis_repo = AnalysisRepository(db)
        self.incident_repo = IncidentRepository(db)
        self.audit_service = AuditService(db)

    async def analyze_incident(
        self,
        incident_id: int,
        actor: Optional[User] = None,
        custom_context: Optional[str] = None,
    ) -> IncidentAnalysis:
        incident = self.incident_repo.get_by_id(incident_id)
        if not incident:
            raise ValueError(f"Incident {incident_id} not found.")

        # Log analysis initiation
        self.audit_service.log_event(
            action="AI_ANALYSIS_REQUESTED",
            resource_type="incident",
            resource_id=str(incident_id),
            actor=actor,
            details={"custom_context": custom_context or ""},
        )

        incident_payload = {
            "id": incident.id,
            "title": incident.title,
            "service_name": incident.service_name,
            "environment": incident.environment,
            "severity": incident.severity,
            "error_message": incident.error_message,
            "stack_trace": incident.stack_trace,
            "logs": incident.logs,
            "affected_endpoint": incident.affected_endpoint,
            "request_metadata": incident.request_metadata,
            "error_frequency": incident.error_frequency,
            "affected_users": incident.affected_users,
            "deployment_version": incident.deployment_version,
            "additional_context": incident.additional_context,
        }

        prompt_version = settings.PROMPT_VERSION
        system_prompt = get_prompt(prompt_version)
        user_prompt = build_incident_user_prompt(incident_payload, custom_context or "")

        client = AIClientFactory.get_client()
        raw_response: Optional[str] = None
        model_provider = client.get_provider_name()
        model_name = client.get_model_name()

        try:
            raw_response = await client.generate_analysis(system_prompt, user_prompt, incident_payload)
            structured_output = parse_structured_ai_response(raw_response)
        except Exception as exc:
            logger.warning(
                f"Primary AI client ({model_provider}/{model_name}) failed with: {exc}. "
                "Engaging resilient Heuristic SRE Engine fallback."
            )
            # Graceful fallback to heuristic engine to ensure continuous platform availability
            fallback_client = HeuristicSREEngineClient()
            model_provider = fallback_client.get_provider_name()
            model_name = fallback_client.get_model_name()
            raw_response = await fallback_client.generate_analysis(system_prompt, user_prompt, incident_payload)
            structured_output = parse_structured_ai_response(raw_response)

        # Create database analysis record
        analysis_record = IncidentAnalysis(
            incident_id=incident.id,
            model_provider=model_provider,
            model_name=model_name,
            prompt_version=prompt_version,
            classification=structured_output.classification,
            ai_severity=structured_output.severity.value,
            probable_root_cause=structured_output.probable_root_cause,
            confidence_score=structured_output.confidence_score,
            impact_assessment=structured_output.impact_assessment,
            evidence=structured_output.evidence,
            immediate_mitigation_steps=structured_output.immediate_mitigation_steps,
            recommended_remediation_steps=structured_output.recommended_remediation_steps,
            prevention_recommendations=structured_output.prevention_recommendations,
            human_readable_summary=structured_output.human_readable_summary,
            raw_response={"raw": raw_response},
        )

        saved_analysis = self.analysis_repo.create(analysis_record)

        # Update AI severity on incident record
        incident.ai_severity = structured_output.severity.value
        self.incident_repo.update(incident)

        # Record audit log
        self.audit_service.log_event(
            action="AI_ANALYSIS_COMPLETED",
            resource_type="incident",
            resource_id=str(incident_id),
            actor=actor,
            details={
                "analysis_id": saved_analysis.id,
                "model_provider": model_provider,
                "classification": structured_output.classification,
                "ai_severity": structured_output.severity.value,
                "confidence_score": structured_output.confidence_score,
            },
        )

        return saved_analysis

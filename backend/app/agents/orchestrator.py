from sqlalchemy.orm import Session
from app.db.models import Incident, IncidentAnalysis, RemediationAction, IncidentRelationship
from app.agents.ai_provider import get_ai_provider

class IncidentOrchestrator:
    def __init__(self, db: Session):
        self.db = db
        self.ai = get_ai_provider()

    def process_incident(self, incident: Incident):
        incident_data = {
            "service": incident.service,
            "environment": incident.environment,
            "error_type": incident.error_type,
            "message": incident.message,
            "endpoint": incident.endpoint,
            "response_time": incident.response_time,
            "metadata": incident.metadata_
        }

        # 1. Severity Agent
        severity_result = self.ai.analyze_severity(incident_data)

        # 2. Root Cause Agent
        # Fetch historical incidents for the same service in the last 24h
        # (Mocked as empty for simplicity in this implementation)
        historical_data = [] 
        root_cause_result = self.ai.analyze_root_cause(incident_data, historical_data)

        # 3. Correlation Agent
        correlation_result = self.ai.correlate_incidents(incident_data, historical_data)

        # Combine analysis
        analysis = IncidentAnalysis(
            incident_id=incident.id,
            severity=severity_result.get("severity"),
            root_cause=root_cause_result.get("root_cause"),
            impact="High" if severity_result.get("severity") in ["HIGH", "CRITICAL"] else "Low",
            confidence=root_cause_result.get("confidence", 0.0),
            analysis_summary=f"Severity: {severity_result.get('reason')}. Root Cause: {root_cause_result.get('reasoning')}"
        )
        self.db.add(analysis)
        self.db.commit()
        
        # Optional: Save correlation if related
        # if correlation_result.get("related"):
        #     rel = IncidentRelationship(incident_id=incident.id, related_incident_id=..., relationship_type="correlation", confidence=correlation_result.get("confidence"))
        #     self.db.add(rel)

        # 4. Remediation Agent
        remediation_actions = self.ai.generate_remediation(incident_data, root_cause_result)
        for action_data in remediation_actions:
            action = RemediationAction(
                incident_id=incident.id,
                action=action_data.get("action"),
                priority=action_data.get("priority", 1),
                reasoning=action_data.get("reasoning")
            )
            self.db.add(action)
        
        self.db.commit()
        
        # Here we emit WebSocket events
        import asyncio
        from app.api.websockets import manager
        import json
        
        try:
            # Create a new event loop or use existing one if available to send async message from sync code
            loop = asyncio.get_running_loop()
            loop.create_task(manager.broadcast(json.dumps({"type": "NEW_INCIDENT", "incident_id": incident.id})))
        except RuntimeError:
            pass # Ignore if no running event loop


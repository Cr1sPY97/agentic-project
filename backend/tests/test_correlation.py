from datetime import datetime, timezone
from app.db.models import Incident
from app.services.correlation_service import IncidentCorrelationEngine


def test_correlation_engine_detects_related_incidents():
    now = datetime.now(timezone.utc)
    
    target = Incident(
        id=1,
        title="Payment Gateway Database Timeout",
        service_name="payment-gateway",
        environment="production",
        affected_endpoint="/api/v1/charge",
        deployment_version="v2.1.0",
        error_message="Connection pool exhausted after 30s timeout",
        created_at=now,
    )

    candidate_related = Incident(
        id=2,
        title="Payment Gateway Slow Query Queue Overload",
        service_name="payment-gateway",
        environment="production",
        affected_endpoint="/api/v1/charge",
        deployment_version="v2.1.0",
        error_message="QueuePool limit reached while executing payment charge",
        created_at=now,
    )

    candidate_unrelated = Incident(
        id=3,
        title="Marketing Email Template Syntax Error",
        service_name="marketing-service",
        environment="staging",
        affected_endpoint="/emails/render",
        deployment_version="v1.0.0",
        error_message="Jinja template variable missing",
        created_at=now,
    )

    matches = IncidentCorrelationEngine.find_correlations(target, [candidate_related, candidate_unrelated])
    assert len(matches) == 1
    assert matches[0].related_incident.id == 2
    assert matches[0].score >= 0.50
    assert "Identical service" in matches[0].reason

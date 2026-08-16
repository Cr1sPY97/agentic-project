import pytest
from fastapi.testclient import TestClient
from app.ai.parser import parse_structured_ai_response
from app.schemas.analysis import AIAnalysisStructuredOutput


def test_parser_with_clean_json():
    raw = """
    {
      "classification": "Database Connection Exhaustion",
      "severity": "CRITICAL",
      "probable_root_cause": "Unindexed full table scan causing connection starvation in worker threads.",
      "confidence_score": 0.95,
      "impact_assessment": "100% 500 error rate on checkout endpoint.",
      "evidence": ["Connection pool limit reached", "Active connections 30/30"],
      "immediate_mitigation_steps": ["Kill long running transactions", "Restart worker pods"],
      "recommended_remediation_steps": ["Add composite index on transactions table", "Tune pool size"],
      "prevention_recommendations": ["Add alert on pool saturation > 80%"],
      "human_readable_summary": "Critical DB starvation in payment service during flash sale."
    }
    """
    output = parse_structured_ai_response(raw)
    assert isinstance(output, AIAnalysisStructuredOutput)
    assert output.classification == "Database Connection Exhaustion"
    assert output.severity.value == "CRITICAL"
    assert output.confidence_score == 0.95
    assert len(output.evidence) == 2


def test_parser_with_markdown_fences_and_preamble():
    raw = """
    Here is my expert SRE diagnosis:
    ```json
    {
      "classification": "Memory Saturation",
      "severity": "HIGH",
      "probable_root_cause": "Batch import loading 500k records into memory without chunking.",
      "confidence_score": 0.88,
      "impact_assessment": "Periodic OOM-killer restarts.",
      "evidence": ["cgroup limit exceeded"],
      "immediate_mitigation_steps": ["Increase pod memory"],
      "recommended_remediation_steps": ["Add streaming cursor"],
      "prevention_recommendations": ["Memory alert at 80%"],
      "human_readable_summary": "Service experiencing OOM crashes due to unpaginated data load."
    }
    ```
    I hope this helps!
    """
    output = parse_structured_ai_response(raw)
    assert output.classification == "Memory Saturation"
    assert output.confidence_score == 0.88


def test_trigger_ai_analysis_endpoint(client: TestClient, responder_headers):
    # Ingest incident
    inc_payload = {
        "title": "Payment Pool Exhaustion",
        "service_name": "payment-gateway",
        "environment": "production",
        "error_message": "QueuePool limit of size 20 reached, connection pool exhausted",
        "error_frequency": 400,
        "affected_users": 1500,
        "affected_endpoint": "/api/v1/payments/charge",
    }
    create_res = client.post("/api/v1/incidents", json=inc_payload, headers=responder_headers)
    inc_id = create_res.json()["id"]

    # Trigger AI analysis
    analyze_res = client.post(
        f"/api/v1/incidents/{inc_id}/analyze",
        json={"run_async": False, "custom_context": "Flash sale event underway"},
        headers=responder_headers,
    )
    assert analyze_res.status_code == 200
    analysis = analyze_res.json()
    assert analysis["incident_id"] == inc_id
    assert "classification" in analysis
    assert analysis["confidence_score"] > 0.0
    assert len(analysis["evidence"]) > 0
    assert len(analysis["immediate_mitigation_steps"]) > 0
    assert len(analysis["recommended_remediation_steps"]) > 0

    # Verify AI severity was written to incident
    inc_res = client.get(f"/api/v1/incidents/{inc_id}", headers=responder_headers)
    assert inc_res.json()["ai_severity"] is not None

    # Fetch analyses history
    history_res = client.get(f"/api/v1/incidents/{inc_id}/analyses", headers=responder_headers)
    assert history_res.status_code == 200
    assert len(history_res.json()) >= 1

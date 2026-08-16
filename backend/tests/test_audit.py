from fastapi.testclient import TestClient


def test_audit_trail_records_lifecycle_and_analysis_events(
    client: TestClient, admin_headers, responder_headers
):
    # 1. Create incident
    inc_payload = {
        "title": "Audit Trail Verification Incident",
        "service_name": "auth-service",
        "environment": "production",
        "error_message": "JWT decoding failure",
    }
    create_res = client.post("/api/v1/incidents", json=inc_payload, headers=responder_headers)
    inc_id = create_res.json()["id"]

    # 2. Transition status
    client.post(
        f"/api/v1/incidents/{inc_id}/status",
        json={"status": "INVESTIGATING", "notes": "On-call starting investigation"},
        headers=responder_headers,
    )

    # 3. Trigger AI analysis
    client.post(
        f"/api/v1/incidents/{inc_id}/analyze",
        json={"run_async": False},
        headers=responder_headers,
    )

    # 4. Query incident-specific audit trail
    audit_res = client.get(f"/api/v1/incidents/{inc_id}/audit", headers=responder_headers)
    assert audit_res.status_code == 200
    logs = audit_res.json()
    assert len(logs) >= 3
    actions = [l["action"] for l in logs]
    assert "INCIDENT_CREATED" in actions
    assert "STATUS_CHANGED" in actions
    assert "AI_ANALYSIS_COMPLETED" in actions

    # 5. Query global audit trail (Admin only)
    global_audit = client.get("/api/v1/audit", headers=admin_headers)
    assert global_audit.status_code == 200
    assert global_audit.json()["total"] >= 3

import pytest
from fastapi.testclient import TestClient


def test_create_incident_with_rule_based_severity(client: TestClient, responder_headers):
    payload = {
        "title": "Critical Redis Out Of Memory Failure",
        "service_name": "payment-gateway",
        "environment": "production",
        "error_message": "OOM command not allowed when used memory > 'maxmemory'",
        "error_frequency": 500,
        "affected_users": 1200,
        "affected_endpoint": "/api/v1/checkout",
        "deployment_version": "v3.1.0",
    }
    response = client.post("/api/v1/incidents", json=payload, headers=responder_headers)
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == payload["title"]
    assert data["service_name"] == "payment-gateway"
    assert data["status"] == "OPEN"
    # Deterministic rule engine should compute CRITICAL based on service, OOM, users, frequency, prod
    assert data["severity"] == "CRITICAL"


def test_list_and_filter_incidents(client: TestClient, responder_headers):
    # Ingest 2 incidents
    inc1 = {
        "title": "Staging DB Slow Query",
        "service_name": "reporting-service",
        "environment": "staging",
        "error_message": "Query exceeded 5000ms threshold",
        "error_frequency": 2,
        "affected_users": 0,
    }
    inc2 = {
        "title": "Prod Auth Timeout",
        "service_name": "auth-service",
        "environment": "production",
        "error_message": "Token verification timeout",
        "error_frequency": 300,
        "affected_users": 800,
    }
    client.post("/api/v1/incidents", json=inc1, headers=responder_headers)
    client.post("/api/v1/incidents", json=inc2, headers=responder_headers)

    # Filter by environment
    res_staging = client.get("/api/v1/incidents?environment=staging", headers=responder_headers)
    assert res_staging.status_code == 200
    items = res_staging.json()["items"]
    assert len(items) == 1
    assert items[0]["service_name"] == "reporting-service"

    # Filter by service name search
    res_search = client.get("/api/v1/incidents?search=Auth", headers=responder_headers)
    assert res_search.status_code == 200
    assert len(res_search.json()["items"]) == 1


def test_status_lifecycle_transitions(client: TestClient, responder_headers):
    # Create incident (starts OPEN)
    inc_payload = {
        "title": "Test Lifecycle Incident",
        "service_name": "order-service",
        "environment": "production",
        "error_message": "Null pointer on order dispatch",
    }
    create_res = client.post("/api/v1/incidents", json=inc_payload, headers=responder_headers)
    inc_id = create_res.json()["id"]

    # Transition OPEN -> INVESTIGATING (Valid)
    res_inv = client.post(
        f"/api/v1/incidents/{inc_id}/status",
        json={"status": "INVESTIGATING", "notes": "Investigating logs"},
        headers=responder_headers,
    )
    assert res_inv.status_code == 200
    assert res_inv.json()["status"] == "INVESTIGATING"

    # Transition INVESTIGATING -> MITIGATED (Valid)
    res_mit = client.post(
        f"/api/v1/incidents/{inc_id}/status",
        json={"status": "MITIGATED", "notes": "Applied rate limit patch"},
        headers=responder_headers,
    )
    assert res_mit.status_code == 200
    assert res_mit.json()["status"] == "MITIGATED"

    # Fast resolve endpoint MITIGATED -> RESOLVED
    res_res = client.post(
        f"/api/v1/incidents/{inc_id}/resolve",
        json={"notes": "Permanent fix deployed in v2.4.2"},
        headers=responder_headers,
    )
    assert res_res.status_code == 200
    assert res_res.json()["status"] == "RESOLVED"
    assert res_res.json()["resolved_at"] is not None

    # Check status history records
    history_res = client.get(f"/api/v1/incidents/{inc_id}/status-history", headers=responder_headers)
    assert history_res.status_code == 200
    history = history_res.json()
    assert len(history) >= 4


def test_invalid_status_transition_rejected(client: TestClient, responder_headers):
    inc_payload = {
        "title": "State Machine Violation Incident",
        "service_name": "notification-service",
        "environment": "production",
        "error_message": "Worker timeout",
    }
    create_res = client.post("/api/v1/incidents", json=inc_payload, headers=responder_headers)
    inc_id = create_res.json()["id"]

    # Transition OPEN -> CLOSED -> RESOLVED (CLOSED cannot go to RESOLVED directly)
    client.post(
        f"/api/v1/incidents/{inc_id}/status",
        json={"status": "CLOSED", "notes": "Closing incident"},
        headers=responder_headers,
    )
    # Attempt invalid CLOSED -> RESOLVED
    invalid_res = client.post(
        f"/api/v1/incidents/{inc_id}/status",
        json={"status": "RESOLVED", "notes": "Illegal hop"},
        headers=responder_headers,
    )
    assert invalid_res.status_code == 422
    assert "Invalid status transition" in invalid_res.json()["detail"]


def test_assign_incident(client: TestClient, responder_headers, responder_user):
    inc_payload = {
        "title": "Incident Assignment Test",
        "service_name": "billing-service",
        "environment": "production",
        "error_message": "Stripe webhook secret mismatch",
    }
    create_res = client.post("/api/v1/incidents", json=inc_payload, headers=responder_headers)
    inc_id = create_res.json()["id"]

    assign_res = client.post(
        f"/api/v1/incidents/{inc_id}/assign",
        json={"assigned_to_id": responder_user.id},
        headers=responder_headers,
    )
    assert assign_res.status_code == 200
    data = assign_res.json()
    assert data["assigned_to_id"] == responder_user.id
    # Should auto-move from OPEN to INVESTIGATING upon assignment
    assert data["status"] == "INVESTIGATING"

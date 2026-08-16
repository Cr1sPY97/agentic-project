from fastapi.testclient import TestClient


def test_dashboard_statistics_calculation(client: TestClient, responder_headers):
    # Ingest 2 incidents (one critical, one medium)
    client.post(
        "/api/v1/incidents",
        json={
            "title": "Critical Outage",
            "service_name": "payment-gateway",
            "environment": "production",
            "error_message": "Connection pool exhausted",
            "affected_users": 1500,
            "error_frequency": 600,
        },
        headers=responder_headers,
    )
    inc2_res = client.post(
        "/api/v1/incidents",
        json={
            "title": "Low Priority Bug",
            "service_name": "notification-service",
            "environment": "staging",
            "error_message": "Template warning",
            "affected_users": 0,
            "error_frequency": 1,
        },
        headers=responder_headers,
    )
    inc2_id = inc2_res.json()["id"]

    # Resolve one incident to generate MTTR metric
    client.post(f"/api/v1/incidents/{inc2_id}/resolve", headers=responder_headers)

    # Fetch stats
    stats_res = client.get("/api/v1/incidents/stats", headers=responder_headers)
    assert stats_res.status_code == 200
    stats = stats_res.json()
    assert stats["total_incidents"] == 2
    assert stats["open_incidents"] == 1
    assert stats["resolved_incidents"] == 1
    assert "payment-gateway" in [s["service_name"] for s in stats["top_affected_services"]]

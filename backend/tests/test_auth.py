import pytest
from fastapi.testclient import TestClient


def test_register_first_user_becomes_admin(client: TestClient):
    payload = {
        "username": "superadmin",
        "email": "superadmin@example.com",
        "password": "Password123!",
        "role": "VIEWER",
    }
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["username"] == "superadmin"
    assert data["email"] == "superadmin@example.com"
    assert data["role"] == "ADMIN"  # First user bootstraps as ADMIN


def test_register_duplicate_username_fails(client: TestClient, admin_user):
    payload = {
        "username": admin_user.username,
        "email": "another@example.com",
        "password": "Password123!",
        "role": "VIEWER",
    }
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 400
    assert "already registered" in response.json()["detail"]


def test_login_success(client: TestClient, admin_user):
    response = client.post(
        "/api/v1/auth/login",
        data={"username": admin_user.username, "password": "AdminPass123!"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["username"] == admin_user.username
    assert data["role"] == "ADMIN"


def test_login_invalid_password(client: TestClient, admin_user):
    response = client.post(
        "/api/v1/auth/login",
        data={"username": admin_user.username, "password": "WrongPassword!"},
    )
    assert response.status_code == 401
    assert "Incorrect" in response.json()["detail"]


def test_get_me_endpoint(client: TestClient, responder_headers, responder_user):
    response = client.get("/api/v1/auth/me", headers=responder_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == responder_user.username
    assert data["role"] == "RESPONDER"


def test_rbac_admin_only_routes(client: TestClient, admin_headers, responder_headers, viewer_headers):
    # Admin can list users
    res_admin = client.get("/api/v1/users", headers=admin_headers)
    assert res_admin.status_code == 200

    # Responder forbidden on users list
    res_resp = client.get("/api/v1/users", headers=responder_headers)
    assert res_resp.status_code == 403

    # Viewer forbidden on users list
    res_viewer = client.get("/api/v1/users", headers=viewer_headers)
    assert res_viewer.status_code == 403

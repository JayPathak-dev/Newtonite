"""Authentication and session tests."""
import pytest
from fastapi.testclient import TestClient


def test_login_success(client: TestClient, seeded_env):
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "sarah@test.com", "password": "Password123!"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "sarah@test.com"
    assert data["user"]["name"] == "Sarah Approver"
    # Ensure cookie is set
    assert "access_token" in response.cookies


def test_login_invalid_password(client: TestClient, seeded_env):
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "sarah@test.com", "password": "WrongPassword!"},
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"


def test_login_nonexistent_user(client: TestClient, seeded_env):
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "nobody@test.com", "password": "Password123!"},
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"


def test_get_me_authenticated(client: TestClient, auth_headers):
    response = client.get("/api/v1/auth/me", headers=auth_headers["sarah"])
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "sarah@test.com"
    assert data["role"] == "USER"
    assert len(data["teams"]) == 1
    assert data["teams"][0]["team_name"] == "Payments"
    assert data["teams"][0]["team_role"] == "APPROVER"


def test_get_me_unauthenticated(client: TestClient):
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"

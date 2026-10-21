"""Tests for CSRF protection and Origin validation."""
import pytest
from fastapi.testclient import TestClient
from app.models.work_item import WorkType, WorkItemPriority
from app.models.user import User


def test_csrf_cookie_auth_without_token_rejected(client: TestClient, seeded_env):
    """A state-changing request authenticated via HttpOnly cookie must be rejected if X-CSRF-Token is missing."""
    sarah = seeded_env["users"]["sarah"]
    payments_team = seeded_env["teams"]["payments"]

    # 1. Log in to get the HttpOnly access_token cookie
    login_res = client.post(
        "/api/v1/auth/login",
        json={"email": sarah.email, "password": "Password123!"},
    )
    assert login_res.status_code == 200
    assert "access_token" in login_res.cookies

    # 2. Attempt POST mutation WITHOUT X-CSRF-Token header
    res = client.post(
        "/api/v1/work-items",
        json={
            "title": "Dispute without CSRF header",
            "team_id": payments_team.id,
            "work_type": WorkType.PAYMENT_INVESTIGATION.value,
            "priority": WorkItemPriority.HIGH.value,
        },
    )
    assert res.status_code == 403
    data = res.json()
    assert data["error"]["code"] == "CSRF_ERROR"


def test_csrf_cookie_auth_with_mismatched_token_rejected(client: TestClient, seeded_env):
    """A state-changing request with an invalid/mismatched X-CSRF-Token must be rejected."""
    sarah = seeded_env["users"]["sarah"]
    payments_team = seeded_env["teams"]["payments"]

    client.post(
        "/api/v1/auth/login",
        json={"email": sarah.email, "password": "Password123!"},
    )

    # Supply an invalid token
    res = client.post(
        "/api/v1/work-items",
        json={
            "title": "Dispute with wrong CSRF header",
            "team_id": payments_team.id,
            "work_type": WorkType.PAYMENT_INVESTIGATION.value,
            "priority": WorkItemPriority.HIGH.value,
        },
        headers={"X-CSRF-Token": "bogus-csrf-token-12345"},
    )
    assert res.status_code == 403
    assert res.json()["error"]["code"] == "CSRF_ERROR"


def test_csrf_cookie_auth_with_valid_token_succeeds(client: TestClient, seeded_env):
    """When both cookie and matching X-CSRF-Token are present, mutation succeeds."""
    sarah = seeded_env["users"]["sarah"]
    payments_team = seeded_env["teams"]["payments"]

    login_res = client.post(
        "/api/v1/auth/login",
        json={"email": sarah.email, "password": "Password123!"},
    )
    assert login_res.status_code == 200
    csrf_token = login_res.cookies["csrf_token"]

    res = client.post(
        "/api/v1/work-items",
        json={
            "title": "Valid CSRF Dispute",
            "team_id": payments_team.id,
            "work_type": WorkType.PAYMENT_INVESTIGATION.value,
            "priority": WorkItemPriority.HIGH.value,
        },
        headers={"X-CSRF-Token": csrf_token},
    )
    assert res.status_code == 201
    assert res.json()["title"] == "Valid CSRF Dispute"


def test_csrf_untrusted_origin_rejected(client: TestClient, seeded_env):
    """Mutations with untrusted Origin header must be rejected."""
    sarah = seeded_env["users"]["sarah"]
    payments_team = seeded_env["teams"]["payments"]

    login_res = client.post(
        "/api/v1/auth/login",
        json={"email": sarah.email, "password": "Password123!"},
    )
    csrf_token = login_res.cookies.get("csrf_token", "")

    res = client.post(
        "/api/v1/work-items",
        json={
            "title": "Malicious origin dispute",
            "team_id": payments_team.id,
            "work_type": WorkType.PAYMENT_INVESTIGATION.value,
            "priority": WorkItemPriority.HIGH.value,
        },
        headers={
            "Origin": "http://evil-attacker-site.com",
            "X-CSRF-Token": csrf_token,
        },
    )
    assert res.status_code == 403
    assert res.json()["error"]["code"] == "FORBIDDEN_ORIGIN"

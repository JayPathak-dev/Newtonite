"""Tests for login rate limiting."""
from fastapi.testclient import TestClient
from app.core.rate_limit import clear_all_rate_limits


def test_login_rate_limiting_triggers_after_max_attempts(client: TestClient, seeded_env):
    """Exceeding 15 rapid failed attempts triggers HTTP 429 Too Many Requests."""
    clear_all_rate_limits()

    # Attempt 15 invalid logins
    for i in range(15):
        res = client.post(
            "/api/v1/auth/login",
            json={"email": "sarah@test.com", "password": "WrongPassword!"},
        )
        assert res.status_code == 401

    # Attempt 16 must be blocked by rate limiter with 429
    res = client.post(
        "/api/v1/auth/login",
        json={"email": "sarah@test.com", "password": "WrongPassword!"},
    )
    assert res.status_code == 429
    data = res.json()
    assert data["error"]["code"] == "RATE_LIMIT_EXCEEDED"

    clear_all_rate_limits()

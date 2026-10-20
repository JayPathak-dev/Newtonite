"""Authorization & Cross-Team Isolation tests."""
import pytest
from fastapi.testclient import TestClient


def test_viewer_cannot_create_work_item(client: TestClient, seeded_env, auth_headers):
    """Viewers cannot create work items (HTTP 403 Forbidden)."""
    payments_team = seeded_env["teams"]["payments"]

    res = client.post(
        "/api/v1/work-items",
        headers=auth_headers["viewer"],
        json={
            "title": "Viewer attempt",
            "team_id": payments_team.id,
            "work_type": "task",
            "priority": "LOW",
        },
    )
    assert res.status_code == 403
    assert res.json()["error"]["code"] == "FORBIDDEN"


def test_viewer_cannot_update_claim_or_comment(client: TestClient, seeded_env, auth_headers):
    """Viewers cannot modify, claim, or comment on items."""
    payments_team = seeded_env["teams"]["payments"]

    # Sarah creates item
    res = client.post(
        "/api/v1/work-items",
        headers=auth_headers["sarah"],
        json={
            "title": "Viewer test item",
            "team_id": payments_team.id,
            "work_type": "task",
            "priority": "LOW",
        },
    )
    item_id = res.json()["id"]

    # Viewer can view
    get_res = client.get(f"/api/v1/work-items/{item_id}", headers=auth_headers["viewer"])
    assert get_res.status_code == 200

    # Viewer cannot update
    upd_res = client.patch(
        f"/api/v1/work-items/{item_id}",
        headers=auth_headers["viewer"],
        json={"title": "Viewer modified", "version": 1},
    )
    assert upd_res.status_code == 403

    # Viewer cannot claim
    claim_res = client.post(
        f"/api/v1/work-items/{item_id}/claim",
        headers=auth_headers["viewer"],
    )
    assert claim_res.status_code == 403

    # Viewer cannot comment
    comm_res = client.post(
        f"/api/v1/work-items/{item_id}/comments",
        headers=auth_headers["viewer"],
        json={"body": "Viewer commenting"},
    )
    assert comm_res.status_code == 403


def test_cross_team_isolation_returns_404_not_found(client: TestClient, seeded_env, auth_headers):
    """
    User from Customer Operations (Oscar Outsider) attempting to access
    a Payments item by exact UUID receives 404 Not Found to prevent resource enumeration.
    """
    payments_team = seeded_env["teams"]["payments"]

    # Sarah creates item in Payments
    res = client.post(
        "/api/v1/work-items",
        headers=auth_headers["sarah"],
        json={
            "title": "Confidential payments audit",
            "team_id": payments_team.id,
            "work_type": "incident",
            "priority": "CRITICAL",
        },
    )
    item_id = res.json()["id"]

    # Oscar Outsider (only in Customer Ops) attempts to get it
    get_res = client.get(f"/api/v1/work-items/{item_id}", headers=auth_headers["outsider"])
    assert get_res.status_code == 404
    assert get_res.json()["error"]["code"] == "NOT_FOUND"

    # Oscar cannot update it either (returns 404)
    patch_res = client.patch(
        f"/api/v1/work-items/{item_id}",
        headers=auth_headers["outsider"],
        json={"title": "Hacked", "version": 1},
    )
    assert patch_res.status_code == 404


def test_list_items_scopes_to_user_teams(client: TestClient, seeded_env, auth_headers):
    """Listing items only returns items belonging to teams the user is a member of."""
    payments_team = seeded_env["teams"]["payments"]
    ops_team = seeded_env["teams"]["ops"]

    # Create 1 Payments item
    client.post(
        "/api/v1/work-items",
        headers=auth_headers["sarah"],
        json={"title": "Payments Secret", "team_id": payments_team.id, "work_type": "task", "priority": "LOW"},
    )

    # Create 1 Ops item
    client.post(
        "/api/v1/work-items",
        headers=auth_headers["admin"],
        json={"title": "Ops Public Item", "team_id": ops_team.id, "work_type": "task", "priority": "LOW"},
    )

    # Oscar Outsider (only member of Customer Ops) lists items
    res = client.get("/api/v1/work-items", headers=auth_headers["outsider"])
    assert res.status_code == 200
    items = res.json()["items"]
    # Oscar should only see Ops items, never Payments items
    for item in items:
        assert item["team_id"] == ops_team.id
        assert "Payments" not in item["title"]


def test_admin_can_access_all_teams(client: TestClient, seeded_env, auth_headers):
    """Admin has global access across all teams."""
    payments_team = seeded_env["teams"]["payments"]

    res = client.post(
        "/api/v1/work-items",
        headers=auth_headers["sarah"],
        json={"title": "Payments Task", "team_id": payments_team.id, "work_type": "task", "priority": "LOW"},
    )
    item_id = res.json()["id"]

    admin_res = client.get(f"/api/v1/work-items/{item_id}", headers=auth_headers["admin"])
    assert admin_res.status_code == 200
    assert admin_res.json()["title"] == "Payments Task"

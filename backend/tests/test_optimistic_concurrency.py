"""Feature 2 Tests: Optimistic Concurrency Control (OCC)."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.models.work_item import WorkItem, WorkItemPriority
from app.models.activity import ActivityLog, EventType


def test_occ_update_success_increments_version(client: TestClient, seeded_env, auth_headers):
    """An update with the matching version increments version by 1."""
    payments_team = seeded_env["teams"]["payments"]

    # Create item
    res = client.post(
        "/api/v1/work-items",
        headers=auth_headers["sarah"],
        json={
            "title": "Database connection spike",
            "team_id": payments_team.id,
            "work_type": "incident",
            "priority": "LOW",
        },
    )
    assert res.status_code == 201
    item = res.json()
    assert item["version"] == 1

    # Update with version 1 -> becomes version 2
    update_res = client.patch(
        f"/api/v1/work-items/{item['id']}",
        headers=auth_headers["sarah"],
        json={
            "title": "Database connection spike - verified",
            "priority": "CRITICAL",
            "version": 1,
        },
    )
    assert update_res.status_code == 200
    updated = update_res.json()
    assert updated["version"] == 2
    assert updated["priority"] == "CRITICAL"
    assert updated["title"] == "Database connection spike - verified"


def test_occ_stale_update_rejected_with_409(client: TestClient, seeded_env, auth_headers, db_session: Session):
    """
    Simulate two concurrent editors:
    1. User A loads version 1.
    2. User B updates item to version 2.
    3. User A submits an edit based on stale version 1.
    Expected: User A gets HTTP 409 STALE_VERSION, User B's change is preserved intact.
    """
    payments_team = seeded_env["teams"]["payments"]

    # 1. Create item (Version 1)
    res = client.post(
        "/api/v1/work-items",
        headers=auth_headers["sarah"],
        json={
            "title": "Concurrent edit demo",
            "team_id": payments_team.id,
            "work_type": "task",
            "priority": "MEDIUM",
        },
    )
    item_id = res.json()["id"]

    # 2. User B (Alex) updates item to version 2 (changes priority to HIGH)
    res_b = client.patch(
        f"/api/v1/work-items/{item_id}",
        headers=auth_headers["alex"],
        json={
            "priority": "HIGH",
            "version": 1,
        },
    )
    assert res_b.status_code == 200
    assert res_b.json()["version"] == 2
    assert res_b.json()["priority"] == "HIGH"

    # 3. User A (Sarah) attempts to update based on stale version 1
    res_a = client.patch(
        f"/api/v1/work-items/{item_id}",
        headers=auth_headers["sarah"],
        json={
            "priority": "LOW",
            "version": 1,  # Stale! Current is 2
        },
    )
    assert res_a.status_code == 409
    err = res_a.json()["error"]
    assert err["code"] == "STALE_VERSION"
    assert err["details"]["current_version"] == 2

    # 4. Verify DB state is intact with User B's update
    db_session.expire_all()
    current_item = db_session.query(WorkItem).filter(WorkItem.id == item_id).one()
    assert current_item.version == 2
    assert current_item.priority == WorkItemPriority.HIGH


def test_occ_on_status_transition(client: TestClient, seeded_env, auth_headers):
    """Status transition also enforces optimistic concurrency control."""
    payments_team = seeded_env["teams"]["payments"]

    res = client.post(
        "/api/v1/work-items",
        headers=auth_headers["sarah"],
        json={
            "title": "Transition OCC demo",
            "team_id": payments_team.id,
            "work_type": "task",
            "priority": "MEDIUM",
        },
    )
    item_id = res.json()["id"]

    # First update bumps to version 2
    client.patch(
        f"/api/v1/work-items/{item_id}",
        headers=auth_headers["sarah"],
        json={"title": "Updated title", "version": 1},
    )

    # Attempt status transition with stale version 1
    trans_res = client.post(
        f"/api/v1/work-items/{item_id}/transition",
        headers=auth_headers["sarah"],
        json={"status": "IN_PROGRESS", "version": 1},
    )
    assert trans_res.status_code == 409
    assert trans_res.json()["error"]["code"] == "STALE_VERSION"

    # Now transition with correct version 2 -> succeeds
    trans_ok = client.post(
        f"/api/v1/work-items/{item_id}/transition",
        headers=auth_headers["sarah"],
        json={"status": "IN_PROGRESS", "version": 2},
    )
    assert trans_ok.status_code == 200
    assert trans_ok.json()["version"] == 3
    assert trans_ok.json()["status"] == "IN_PROGRESS"

"""Tests for assignee and team membership validation."""
import pytest
import uuid
from fastapi.testclient import TestClient
from app.models.work_item import WorkItem, WorkItemStatus, WorkItemPriority, WorkType
from app.core.security import hash_password
from app.models.user import User, SystemRole


def test_cannot_assign_nonexistent_user(client: TestClient, seeded_env, auth_headers):
    """Creating or assigning to a non-existent user UUID is rejected."""
    payments_team = seeded_env["teams"]["payments"]
    fake_uuid = str(uuid.uuid4())

    res = client.post(
        "/api/v1/work-items",
        json={
            "title": "Invalid user assignment",
            "team_id": payments_team.id,
            "work_type": WorkType.PAYMENT_INVESTIGATION.value,
            "priority": WorkItemPriority.MEDIUM.value,
            "assignee_id": fake_uuid,
        },
        headers=auth_headers["sarah"],
    )
    assert res.status_code == 400
    assert res.json()["error"]["code"] == "VALIDATION_ERROR"
    assert "Assignee does not exist" in res.json()["error"]["message"]


def test_cannot_assign_non_team_member(client: TestClient, seeded_env, auth_headers):
    """Assigning work to a user who does not belong to the work item's team is rejected."""
    payments_team = seeded_env["teams"]["payments"]
    outsider = seeded_env["users"]["outsider"]  # only in ops team

    res = client.post(
        "/api/v1/work-items",
        json={
            "title": "Cross-team invalid assignee",
            "team_id": payments_team.id,
            "work_type": WorkType.PAYMENT_INVESTIGATION.value,
            "priority": WorkItemPriority.MEDIUM.value,
            "assignee_id": outsider.id,
        },
        headers=auth_headers["sarah"],
    )
    assert res.status_code == 400
    assert res.json()["error"]["code"] == "VALIDATION_ERROR"
    assert "not a member of team" in res.json()["error"]["message"]


def test_cannot_assign_inactive_user(client: TestClient, seeded_env, db_session, auth_headers):
    """Assigning to an inactive user is rejected."""
    payments_team = seeded_env["teams"]["payments"]
    
    inactive_user = User(
        name="Inactive Person",
        email="inactive@test.com",
        password_hash=hash_password("Password123!"),
        role=SystemRole.USER,
        is_active=False,
    )
    db_session.add(inactive_user)
    db_session.commit()

    res = client.post(
        "/api/v1/work-items",
        json={
            "title": "Inactive assignee task",
            "team_id": payments_team.id,
            "work_type": WorkType.PAYMENT_INVESTIGATION.value,
            "priority": WorkItemPriority.LOW.value,
            "assignee_id": inactive_user.id,
        },
        headers=auth_headers["sarah"],
    )
    assert res.status_code == 400
    assert "Cannot assign work to an inactive user" in res.json()["error"]["message"]


def test_reassign_to_non_member_rejected(client: TestClient, seeded_env, auth_headers):
    """Reassigning an existing item to someone outside the team is rejected."""
    payments_team = seeded_env["teams"]["payments"]
    alex = seeded_env["users"]["alex"]
    outsider = seeded_env["users"]["outsider"]

    # 1. Create valid item assigned to Alex (Payments member)
    create_res = client.post(
        "/api/v1/work-items",
        json={
            "title": "Legit payment dispute",
            "team_id": payments_team.id,
            "work_type": WorkType.PAYMENT_INVESTIGATION.value,
            "priority": WorkItemPriority.HIGH.value,
            "assignee_id": alex.id,
        },
        headers=auth_headers["sarah"],
    )
    assert create_res.status_code == 201
    item_id = create_res.json()["id"]

    # 2. Try reassigning to outsider
    assign_res = client.post(
        f"/api/v1/work-items/{item_id}/assign",
        json={"assignee_id": outsider.id, "version": 1},
        headers=auth_headers["sarah"],
    )
    assert assign_res.status_code == 400
    assert "not a member of team" in assign_res.json()["error"]["message"]

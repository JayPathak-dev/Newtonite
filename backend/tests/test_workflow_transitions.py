"""Workflow transition validation and approval rules tests."""
import pytest
from fastapi.testclient import TestClient
from app.models.work_item import WorkItemStatus


def test_valid_workflow_lifecycle(client: TestClient, seeded_env, auth_headers):
    """
    Test standard valid transitions:
    OPEN -> IN_PROGRESS -> IN_REVIEW -> RESOLVED -> CLOSED
    """
    payments_team = seeded_env["teams"]["payments"]

    # 1. Create OPEN item
    res = client.post(
        "/api/v1/work-items",
        headers=auth_headers["sarah"],
        json={
            "title": "Lifecycle test item",
            "team_id": payments_team.id,
            "work_type": "task",
            "priority": "MEDIUM",
        },
    )
    assert res.status_code == 201
    item = res.json()
    assert item["status"] == "OPEN"
    version = item["version"]

    # 2. OPEN -> IN_PROGRESS
    res = client.post(
        f"/api/v1/work-items/{item['id']}/transition",
        headers=auth_headers["sarah"],
        json={"status": "IN_PROGRESS", "version": version},
    )
    assert res.status_code == 200
    assert res.json()["status"] == "IN_PROGRESS"
    version = res.json()["version"]

    # 3. IN_PROGRESS -> IN_REVIEW
    res = client.post(
        f"/api/v1/work-items/{item['id']}/transition",
        headers=auth_headers["sarah"],
        json={"status": "IN_REVIEW", "version": version},
    )
    assert res.status_code == 200
    assert res.json()["status"] == "IN_REVIEW"
    version = res.json()["version"]

    # 4. IN_REVIEW -> RESOLVED
    res = client.post(
        f"/api/v1/work-items/{item['id']}/transition",
        headers=auth_headers["sarah"],
        json={"status": "RESOLVED", "version": version},
    )
    assert res.status_code == 200
    assert res.json()["status"] == "RESOLVED"
    assert res.json()["resolved_at"] is not None
    version = res.json()["version"]

    # 5. RESOLVED -> CLOSED
    res = client.post(
        f"/api/v1/work-items/{item['id']}/transition",
        headers=auth_headers["sarah"],
        json={"status": "CLOSED", "version": version},
    )
    assert res.status_code == 200
    assert res.json()["status"] == "CLOSED"
    assert res.json()["closed_at"] is not None


def test_invalid_transitions_rejected(client: TestClient, seeded_env, auth_headers):
    """Illegal transitions are rejected with HTTP 400 WORKFLOW_ERROR."""
    payments_team = seeded_env["teams"]["payments"]

    # Create OPEN item
    res = client.post(
        "/api/v1/work-items",
        headers=auth_headers["sarah"],
        json={
            "title": "Illegal transitions item",
            "team_id": payments_team.id,
            "work_type": "task",
            "priority": "MEDIUM",
        },
    )
    item_id = res.json()["id"]

    # 1. OPEN -> RESOLVED (cannot jump straight to RESOLVED)
    bad_1 = client.post(
        f"/api/v1/work-items/{item_id}/transition",
        headers=auth_headers["sarah"],
        json={"status": "RESOLVED", "version": 1},
    )
    assert bad_1.status_code == 400
    assert bad_1.json()["error"]["code"] == "WORKFLOW_ERROR"

    # Close directly from OPEN (allowed by policy)
    close_res = client.post(
        f"/api/v1/work-items/{item_id}/transition",
        headers=auth_headers["sarah"],
        json={"status": "CLOSED", "version": 1},
    )
    assert close_res.status_code == 200
    version = close_res.json()["version"]

    # 2. CLOSED -> IN_PROGRESS (CLOSED is terminal)
    bad_2 = client.post(
        f"/api/v1/work-items/{item_id}/transition",
        headers=auth_headers["sarah"],
        json={"status": "IN_PROGRESS", "version": version},
    )
    assert bad_2.status_code == 400
    assert bad_2.json()["error"]["code"] == "WORKFLOW_ERROR"


def test_approval_requirement_blocks_resolution(client: TestClient, seeded_env, auth_headers):
    """
    Work item requiring approval cannot be resolved until an authorized approver approves it.
    """
    payments_team = seeded_env["teams"]["payments"]

    # 1. Create item requiring approval
    res = client.post(
        "/api/v1/work-items",
        headers=auth_headers["alex"],
        json={
            "title": "High value refund approval needed",
            "team_id": payments_team.id,
            "work_type": "approval_request",
            "priority": "HIGH",
            "requires_approval": True,
        },
    )
    assert res.status_code == 201
    item = res.json()
    item_id = item["id"]
    assert item["approval_status"] == "pending"

    # Move to IN_PROGRESS
    res = client.post(
        f"/api/v1/work-items/{item_id}/transition",
        headers=auth_headers["alex"],
        json={"status": "IN_PROGRESS", "version": item["version"]},
    )
    version = res.json()["version"]

    # 2. Attempt to resolve while approval is still PENDING -> Must be rejected!
    res_bad = client.post(
        f"/api/v1/work-items/{item_id}/transition",
        headers=auth_headers["alex"],
        json={"status": "RESOLVED", "version": version},
    )
    assert res_bad.status_code == 400
    assert "requires approval" in res_bad.json()["error"]["message"]

    # 3. Unauthorized user (Alex is only MEMBER, not APPROVER) attempts to approve -> 403 Forbidden!
    alex_appr = client.post(
        f"/api/v1/work-items/{item_id}/approval",
        headers=auth_headers["alex"],
        json={"decision": "approved", "explanation": "Self approving"},
    )
    assert alex_appr.status_code == 403

    # 4. Authorized approver (Sarah is APPROVER) approves
    sarah_appr = client.post(
        f"/api/v1/work-items/{item_id}/approval",
        headers=auth_headers["sarah"],
        json={"decision": "approved", "explanation": "Verified invoice discrepancy"},
    )
    assert sarah_appr.status_code == 200
    approved_item = sarah_appr.json()
    assert approved_item["approval_status"] == "approved"
    version = approved_item["version"]

    # 5. Now resolution succeeds!
    res_ok = client.post(
        f"/api/v1/work-items/{item_id}/transition",
        headers=auth_headers["alex"],
        json={"status": "RESOLVED", "version": version},
    )
    assert res_ok.status_code == 200
    assert res_ok.json()["status"] == "RESOLVED"

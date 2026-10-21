"""Tests for atomic approval decisions and race-condition prevention."""
from concurrent.futures import ThreadPoolExecutor, as_completed
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient
from app.models.work_item import WorkItem, WorkItemStatus, WorkItemPriority, WorkType, ApprovalStatus
from app.models.activity import ActivityLog, EventType
from app.models.approval import ApprovalRecord, ApprovalDecision
from tests.conftest import TestingSessionLocal, make_auth_headers


def test_competing_approval_decisions_race_condition(seeded_env, db_session: Session):
    """
    Two concurrent requests submit conflicting decisions (approved vs rejected)
    for the same pending approval.
    Invariant: Exactly 1 decision succeeds (200 OK), exactly 1 receives conflict (409 Conflict),
    and exactly 1 decision event is written in the activity log.
    """
    payments_team = seeded_env["teams"]["payments"]
    sarah = seeded_env["users"]["sarah"]      # Approver
    admin = seeded_env["users"]["admin"]      # Admin (also eligible approver)
    alex = seeded_env["users"]["alex"]

    # 1. Create a work item that requires approval in PENDING state
    item = WorkItem(
        key="OPS-APPR-1",
        title="High value settlement refund",
        work_type=WorkType.PAYMENT_INVESTIGATION,
        priority=WorkItemPriority.CRITICAL,
        status=WorkItemStatus.IN_REVIEW,
        team_id=payments_team.id,
        assignee_id=alex.id,
        created_by_id=alex.id,
        requires_approval=True,
        approval_status=ApprovalStatus.PENDING,
        version=1,
    )
    db_session.add(item)
    db_session.commit()
    item_id = item.id

    from app.main import app
    from app.database import get_db

    def override_get_db():
        s = TestingSessionLocal()
        try:
            yield s
        finally:
            s.close()

    app.dependency_overrides[get_db] = override_get_db

    # Worker 1: Sarah approves
    def submit_approve():
        with TestClient(app) as tc:
            headers = make_auth_headers(sarah)
            res = tc.post(
                f"/api/v1/work-items/{item_id}/approval",
                json={"decision": "approved", "explanation": "Authorized by Sarah"},
                headers=headers,
            )
            return res.status_code, res.json()

    # Worker 2: Admin rejects
    def submit_reject():
        with TestClient(app) as tc:
            headers = make_auth_headers(admin)
            res = tc.post(
                f"/api/v1/work-items/{item_id}/approval",
                json={"decision": "rejected", "explanation": "Denied by Admin"},
                headers=headers,
            )
            return res.status_code, res.json()

    results = []
    with ThreadPoolExecutor(max_workers=2) as executor:
        f1 = executor.submit(submit_approve)
        f2 = executor.submit(submit_reject)
        for f in as_completed([f1, f2]):
            results.append(f.result())

    status_codes = [r[0] for r in results]
    assert 200 in status_codes, f"Expected exactly one 200 OK: {status_codes}"
    assert 409 in status_codes, f"Expected exactly one 409 Conflict: {status_codes}"

    # Expire cached session state to read external thread's committed data
    db_session.expire_all()
    refreshed_item = db_session.query(WorkItem).filter(WorkItem.id == item_id).first()
    assert refreshed_item.approval_status in (ApprovalStatus.APPROVED, ApprovalStatus.REJECTED)
    assert refreshed_item.version == 2

    # Verify exactly 1 decision event in activity history
    decision_events = (
        db_session.query(ActivityLog)
        .filter(
            ActivityLog.work_item_id == item_id,
            ActivityLog.event_type.in_([EventType.APPROVAL_GRANTED, EventType.APPROVAL_REJECTED]),
        )
        .all()
    )
    assert len(decision_events) == 1

    # Verify losing request response details
    conflict_res = next(r[1] for r in results if r[0] == 409)
    assert conflict_res["error"]["code"] == "ALREADY_DECIDED"


def test_unauthorized_user_cannot_decide_approval(client: TestClient, seeded_env, auth_headers):
    """An ordinary team member without APPROVER or LEAD role cannot approve or reject."""
    payments_team = seeded_env["teams"]["payments"]
    alex = seeded_env["users"]["alex"]  # ordinary member

    # Create work item
    create_res = client.post(
        "/api/v1/work-items",
        json={
            "title": "Needs compliance signoff",
            "team_id": payments_team.id,
            "work_type": WorkType.COMPLIANCE_REQUEST.value,
            "priority": WorkItemPriority.HIGH.value,
            "requires_approval": True,
        },
        headers=auth_headers["sarah"],
    )
    assert create_res.status_code == 201
    item_id = create_res.json()["id"]

    # Alex attempts approval
    res = client.post(
        f"/api/v1/work-items/{item_id}/approval",
        json={"decision": "approved", "explanation": "I am trying to self approve"},
        headers=auth_headers["alex"],
    )
    assert res.status_code == 403
    assert res.json()["error"]["code"] == "FORBIDDEN"


def test_cannot_overwrite_completed_approval(client: TestClient, seeded_env, auth_headers):
    """Subsequent approval decisions on an already decided item are rejected with 409 Conflict."""
    payments_team = seeded_env["teams"]["payments"]

    # 1. Create item requiring approval
    create_res = client.post(
        "/api/v1/work-items",
        json={
            "title": "Dual approval test",
            "team_id": payments_team.id,
            "work_type": WorkType.COMPLIANCE_REQUEST.value,
            "priority": WorkItemPriority.HIGH.value,
            "requires_approval": True,
        },
        headers=auth_headers["sarah"],
    )
    item_id = create_res.json()["id"]

    # 2. First decision succeeds
    first_dec = client.post(
        f"/api/v1/work-items/{item_id}/approval",
        json={"decision": "approved", "explanation": "Approved by Sarah"},
        headers=auth_headers["sarah"],
    )
    assert first_dec.status_code == 200

    # 3. Second decision fails with 409
    second_dec = client.post(
        f"/api/v1/work-items/{item_id}/approval",
        json={"decision": "rejected", "explanation": "Late rejection attempt"},
        headers=auth_headers["admin"],
    )
    assert second_dec.status_code == 409
    assert second_dec.json()["error"]["code"] == "ALREADY_DECIDED"


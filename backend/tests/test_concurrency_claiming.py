"""Feature 1 Tests: Atomic Assignment & Concurrent Claiming."""
import pytest
from concurrent.futures import ThreadPoolExecutor, as_completed
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.models.work_item import WorkItem, WorkItemStatus, WorkItemPriority, WorkType
from app.models.activity import ActivityLog, EventType
from tests.conftest import TestingSessionLocal, make_auth_headers


def test_claim_unassigned_work_item_success(client: TestClient, seeded_env, auth_headers, db_session: Session):
    """A user in the team can claim an unassigned work item."""
    payments_team = seeded_env["teams"]["payments"]
    sarah = seeded_env["users"]["sarah"]

    # Create unassigned item
    create_res = client.post(
        "/api/v1/work-items",
        headers=auth_headers["sarah"],
        json={
            "title": "Unassigned payment issue",
            "team_id": payments_team.id,
            "work_type": "incident",
            "priority": "HIGH",
        },
    )
    assert create_res.status_code == 201
    item_id = create_res.json()["id"]

    # Claim item
    claim_res = client.post(
        f"/api/v1/work-items/{item_id}/claim",
        headers=auth_headers["alex"],
    )
    assert claim_res.status_code == 200
    claimed_data = claim_res.json()
    assert claimed_data["assignee_id"] == seeded_env["users"]["alex"].id
    assert claimed_data["version"] == 2

    # Verify activity history has exactly one claim event
    activities = (
        db_session.query(ActivityLog)
        .filter(ActivityLog.work_item_id == item_id, ActivityLog.event_type == EventType.WORK_ITEM_CLAIMED)
        .all()
    )
    assert len(activities) == 1
    assert activities[0].actor_id == seeded_env["users"]["alex"].id


def test_subsequent_claim_returns_409_already_claimed(client: TestClient, seeded_env, auth_headers):
    """Once claimed, any subsequent claim request returns HTTP 409 conflict."""
    payments_team = seeded_env["teams"]["payments"]
    sarah = seeded_env["users"]["sarah"]

    # Create unassigned item
    create_res = client.post(
        "/api/v1/work-items",
        headers=auth_headers["sarah"],
        json={
            "title": "Payout discrepancy",
            "team_id": payments_team.id,
            "work_type": "task",
            "priority": "MEDIUM",
        },
    )
    item_id = create_res.json()["id"]

    # Alex claims first
    claim_1 = client.post(
        f"/api/v1/work-items/{item_id}/claim",
        headers=auth_headers["alex"],
    )
    assert claim_1.status_code == 200

    # Sarah attempts to claim already claimed item
    claim_2 = client.post(
        f"/api/v1/work-items/{item_id}/claim",
        headers=auth_headers["sarah"],
    )
    assert claim_2.status_code == 409
    err = claim_2.json()["error"]
    assert err["code"] == "ALREADY_CLAIMED"
    assert "Alex Member" in err["message"] or "Alex" in str(err["details"])


def test_high_concurrency_claiming(seeded_env, db_session: Session):
    """
    Stress test with 10 concurrent requests to claim the same unassigned item.
    Proves that the atomic database UPDATE (WHERE assignee_id IS NULL)
    guarantees exactly 1 winner (200 OK) and 9 losers (409 Conflict),
    with no race condition, data corruption, or duplicate activity log.
    """
    payments_team = seeded_env["teams"]["payments"]
    admin = seeded_env["users"]["admin"]

    # Create an unassigned item directly in DB
    item = WorkItem(
        key="NEW-CONC-1",
        title="High concurrency settlement dispute",
        work_type=WorkType.PAYMENT_INVESTIGATION,
        priority=WorkItemPriority.CRITICAL,
        status=WorkItemStatus.OPEN,
        team_id=payments_team.id,
        assignee_id=None,
        created_by_id=admin.id,
        version=1,
    )
    db_session.add(item)
    db_session.commit()
    item_id = item.id

    # Create 10 distinct test clients and users
    results = []

    def attempt_claim(worker_idx: int):
        from fastapi.testclient import TestClient
        from app.main import app
        from app.database import get_db

        def override_get_db():
            s = TestingSessionLocal()
            try:
                yield s
            finally:
                s.close()

        app.dependency_overrides[get_db] = override_get_db
        headers = make_auth_headers(admin)
        with TestClient(app) as tc:
            res = tc.post(f"/api/v1/work-items/{item_id}/claim", headers=headers)
            return res.status_code, res.json()

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(attempt_claim, i) for i in range(10)]
        for f in as_completed(futures):
            results.append(f.result())

    status_codes = [r[0] for r in results]
    successes = [code for code in status_codes if code == 200]
    conflicts = [code for code in status_codes if code == 409]

    # Invariants: Exactly 1 winner, exactly 9 conflicts!
    assert len(successes) == 1, f"Expected 1 winner, got {len(successes)}: {status_codes}"
    assert len(conflicts) == 9, f"Expected 9 conflicts, got {len(conflicts)}: {status_codes}"

    # Database verification
    db_session.expire_all()
    refreshed_item = db_session.query(WorkItem).filter(WorkItem.id == item_id).one()
    assert refreshed_item.assignee_id is not None
    assert refreshed_item.version == 2

    # Exactly 1 activity log entry for claim
    claim_logs = (
        db_session.query(ActivityLog)
        .filter(ActivityLog.work_item_id == item_id, ActivityLog.event_type == EventType.WORK_ITEM_CLAIMED)
        .all()
    )
    assert len(claim_logs) == 1

"""Feature 3 Tests: Idempotent Work Item Creation."""
import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.models.work_item import WorkItem
from app.models.activity import ActivityLog, EventType
from app.models.idempotency import IdempotencyRecord


def test_idempotent_creation_returns_same_item_on_retry(client: TestClient, seeded_env, auth_headers, db_session: Session):
    """
    Submitting the same creation request with the same idempotency key
    returns the original item without creating duplicates.
    """
    payments_team = seeded_env["teams"]["payments"]
    idempotency_key = f"idem-key-{uuid.uuid4()}"

    payload = {
        "title": "Idempotent payment refund request",
        "team_id": payments_team.id,
        "work_type": "payment_investigation",
        "priority": "HIGH",
        "description": "Network timeout retry demo",
        "idempotency_key": idempotency_key,
    }

    # 1. First submission (returns 201)
    res_1 = client.post("/api/v1/work-items", headers=auth_headers["sarah"], json=payload)
    assert res_1.status_code == 201
    item_1 = res_1.json()

    # 2. Retry with the EXACT SAME key and payload
    res_2 = client.post("/api/v1/work-items", headers=auth_headers["sarah"], json=payload)
    assert res_2.status_code == 201
    item_2 = res_2.json()

    # Must be the exact same work item
    assert item_1["id"] == item_2["id"]
    assert item_1["key"] == item_2["key"]
    assert item_1["created_at"] == item_2["created_at"]

    # 3. Verify exactly ONE work item exists in DB
    items_count = db_session.query(WorkItem).filter(WorkItem.title == "Idempotent payment refund request").count()
    assert items_count == 1

    # 4. Verify exactly ONE WORK_ITEM_CREATED activity event exists
    activities = (
        db_session.query(ActivityLog)
        .filter(ActivityLog.work_item_id == item_1["id"], ActivityLog.event_type == EventType.WORK_ITEM_CREATED)
        .all()
    )
    assert len(activities) == 1

    # 5. Verify idempotency record exists in DB
    idem_rec = (
        db_session.query(IdempotencyRecord)
        .filter(IdempotencyRecord.idempotency_key == idempotency_key)
        .one()
    )
    assert idem_rec.result_resource_id == item_1["id"]


def test_idempotency_key_reuse_with_different_payload_returns_409(client: TestClient, seeded_env, auth_headers):
    """Reusing the same key with a different payload returns HTTP 409 Conflict."""
    payments_team = seeded_env["teams"]["payments"]
    idempotency_key = f"idem-key-{uuid.uuid4()}"

    # 1. First submission
    payload_1 = {
        "title": "Original title",
        "team_id": payments_team.id,
        "work_type": "task",
        "priority": "LOW",
        "idempotency_key": idempotency_key,
    }
    res_1 = client.post("/api/v1/work-items", headers=auth_headers["sarah"], json=payload_1)
    assert res_1.status_code == 201

    # 2. Submitting same key with DIFFERENT title/priority
    payload_2 = {
        "title": "Completely different title",
        "team_id": payments_team.id,
        "work_type": "incident",
        "priority": "CRITICAL",
        "idempotency_key": idempotency_key,
    }
    res_2 = client.post("/api/v1/work-items", headers=auth_headers["sarah"], json=payload_2)
    assert res_2.status_code == 409
    err = res_2.json()["error"]
    assert err["code"] == "IDEMPOTENCY_CONFLICT"


def test_distinct_idempotency_keys_create_distinct_items(client: TestClient, seeded_env, auth_headers):
    """Two different keys create two distinct items."""
    payments_team = seeded_env["teams"]["payments"]

    res_1 = client.post(
        "/api/v1/work-items",
        headers=auth_headers["sarah"],
        json={
            "title": "Item One",
            "team_id": payments_team.id,
            "work_type": "task",
            "priority": "LOW",
            "idempotency_key": str(uuid.uuid4()),
        },
    )
    assert res_1.status_code == 201

    res_2 = client.post(
        "/api/v1/work-items",
        headers=auth_headers["sarah"],
        json={
            "title": "Item Two",
            "team_id": payments_team.id,
            "work_type": "task",
            "priority": "LOW",
            "idempotency_key": str(uuid.uuid4()),
        },
    )
    assert res_2.status_code == 201
    assert res_1.json()["id"] != res_2.json()["id"]
    assert res_1.json()["key"] != res_2.json()["key"]

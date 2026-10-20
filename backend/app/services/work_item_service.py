"""Work item service - core business logic with transactional correctness."""
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import text, update
from sqlalchemy.exc import IntegrityError

from app.models.work_item import WorkItem, WorkItemStatus, WorkItemPriority, WorkType, ApprovalStatus
from app.models.activity import EventType
from app.models.user import User
from app.core.exceptions import (
    NotFoundError, ForbiddenError, StaleVersionError,
    AlreadyClaimedError, IdempotencyConflictError, WorkflowError
)
from app.core.permissions import can_access_work_item, can_update_work_item, can_claim_work_item, can_assign_work_item
from app.services.activity_service import log_event
from app.services.workflow_service import validate_transition
from app.services.idempotency_service import check_or_create_idempotency, record_idempotency_result
import logging

logger = logging.getLogger(__name__)


def _get_next_key(db: Session) -> str:
    """Generate next work item key atomically using PostgreSQL sequence."""
    result = db.execute(text("SELECT nextval('work_item_key_seq')"))
    seq_num = result.scalar()
    return f"OPS-{seq_num}"


def get_work_item_or_404(db: Session, work_item_id: str, user: User) -> WorkItem:
    """
    Get a work item by ID, enforcing access control.
    Returns 404 for both missing and unauthorized items (prevents resource enumeration).
    """
    item = db.query(WorkItem).filter(WorkItem.id == work_item_id).first()
    if not item or not can_access_work_item(user, item):
        raise NotFoundError("Work item not found")
    return item


def create_work_item(
    db: Session,
    actor: User,
    title: str,
    team_id: str,
    work_type: WorkType,
    priority: WorkItemPriority,
    description: Optional[str] = None,
    assignee_id: Optional[str] = None,
    due_at: Optional[datetime] = None,
    requires_approval: bool = False,
    idempotency_key: Optional[str] = None,
) -> WorkItem:
    """
    Create a work item with idempotency support.
    All operations (create + activity log + idempotency record) are in a single transaction.
    """
    # Build fingerprint-relevant data (without idempotency key itself)
    request_data = {
        "title": title,
        "team_id": team_id,
        "work_type": work_type.value if isinstance(work_type, WorkType) else work_type,
        "priority": priority.value if isinstance(priority, WorkItemPriority) else priority,
        "description": description,
        "assignee_id": assignee_id,
        "due_at": due_at.isoformat() if due_at else None,
        "requires_approval": requires_approval,
    }

    # Check idempotency before doing any work
    if idempotency_key:
        try:
            is_duplicate, existing_id = check_or_create_idempotency(
                db, idempotency_key, actor.id, "create_work_item", request_data
            )
            if is_duplicate and existing_id:
                existing = db.query(WorkItem).filter(WorkItem.id == existing_id).first()
                if existing:
                    return existing
        except IdempotencyConflictError:
            raise

    # Generate key atomically
    key = _get_next_key(db)

    # Set approval status
    approval_status = ApprovalStatus.PENDING if requires_approval else ApprovalStatus.NOT_REQUIRED

    work_item = WorkItem(
        key=key,
        title=title,
        description=description,
        work_type=work_type,
        priority=priority,
        status=WorkItemStatus.OPEN,
        team_id=team_id,
        assignee_id=assignee_id,
        created_by_id=actor.id,
        due_at=due_at,
        requires_approval=requires_approval,
        approval_status=approval_status,
        version=1,
    )
    db.add(work_item)
    db.flush()  # Get the ID without committing

    # Record activity - in same transaction
    log_event(
        db, work_item, actor, EventType.WORK_ITEM_CREATED,
        f"Created work item {key}: {title}",
        metadata={"key": key, "priority": priority.value if hasattr(priority, 'value') else priority},
    )

    # Record idempotency result - in same transaction
    if idempotency_key:
        try:
            record_idempotency_result(
                db, idempotency_key, actor.id, "create_work_item", request_data, work_item.id
            )
        except IntegrityError:
            # Another concurrent request with same key completed first
            db.rollback()
            # Re-fetch the winning record
            is_duplicate, existing_id = check_or_create_idempotency(
                db, idempotency_key, actor.id, "create_work_item", request_data
            )
            if is_duplicate and existing_id:
                existing = db.query(WorkItem).filter(WorkItem.id == existing_id).first()
                if existing:
                    return existing

    db.commit()
    db.refresh(work_item)
    return work_item


def update_work_item(
    db: Session,
    actor: User,
    work_item_id: str,
    expected_version: int,
    **updates,
) -> WorkItem:
    """
    Update a work item with optimistic concurrency control.
    Uses conditional UPDATE checking both ID and version atomically.
    All changes + activity events are committed in a single transaction.
    """
    # First check access (for 404 policy consistency)
    item = get_work_item_or_404(db, work_item_id, actor)

    if not can_update_work_item(actor, item):
        raise ForbiddenError("You don't have permission to update this work item")

    # Build update dict with only provided fields
    update_dict = {}
    activity_events = []

    if "title" in updates and updates["title"] != item.title:
        activity_events.append({
            "event_type": EventType.TITLE_CHANGED,
            "field_name": "title",
            "previous_value": item.title,
            "new_value": updates["title"],
            "summary": f"Changed title from '{item.title}' to '{updates['title']}'",
        })
        update_dict["title"] = updates["title"]

    if "description" in updates and updates["description"] != item.description:
        activity_events.append({
            "event_type": EventType.DESCRIPTION_CHANGED,
            "field_name": "description",
            "previous_value": item.description,
            "new_value": updates["description"],
            "summary": "Updated description",
        })
        update_dict["description"] = updates["description"]

    if "priority" in updates and updates["priority"] != item.priority:
        old_priority = item.priority.value if hasattr(item.priority, 'value') else item.priority
        new_priority = updates["priority"].value if hasattr(updates["priority"], 'value') else updates["priority"]
        activity_events.append({
            "event_type": EventType.PRIORITY_CHANGED,
            "field_name": "priority",
            "previous_value": old_priority,
            "new_value": new_priority,
            "summary": f"Changed priority from {old_priority} to {new_priority}",
        })
        update_dict["priority"] = updates["priority"]

    if "due_at" in updates and updates["due_at"] != item.due_at:
        activity_events.append({
            "event_type": EventType.DUE_DATE_CHANGED,
            "field_name": "due_at",
            "previous_value": item.due_at.isoformat() if item.due_at else None,
            "new_value": updates["due_at"].isoformat() if updates["due_at"] else None,
            "summary": "Updated due date",
        })
        update_dict["due_at"] = updates["due_at"]

    if "assignee_id" in updates and updates["assignee_id"] != item.assignee_id:
        if not can_assign_work_item(actor, item):
            raise ForbiddenError("You don't have permission to assign this work item")
        activity_events.append({
            "event_type": EventType.ASSIGNEE_CHANGED,
            "field_name": "assignee_id",
            "previous_value": item.assignee_id,
            "new_value": updates["assignee_id"],
            "summary": "Changed assignee",
        })
        update_dict["assignee_id"] = updates["assignee_id"]

    if not update_dict:
        return item  # Nothing to change

    update_dict["version"] = item.version + 1
    update_dict["updated_at"] = datetime.now(timezone.utc)

    # Conditional UPDATE - atomically checks version
    result = db.execute(
        update(WorkItem)
        .where(WorkItem.id == work_item_id, WorkItem.version == expected_version)
        .values(**update_dict)
        .returning(WorkItem.version)
    )
    updated = result.fetchone()

    if not updated:
        # Either the item was deleted or version changed
        db.rollback()
        # Re-fetch to determine current version (for the 409 response)
        current = db.query(WorkItem).filter(WorkItem.id == work_item_id).first()
        if not current or not can_access_work_item(actor, current):
            raise NotFoundError("Work item not found")
        raise StaleVersionError(current_version=current.version)

    # Record activity events - in same transaction
    db.refresh(item)
    for evt in activity_events:
        log_event(db, item, actor, **evt)

    db.commit()
    db.refresh(item)
    return item


def transition_status(
    db: Session,
    actor: User,
    work_item_id: str,
    new_status: WorkItemStatus,
    expected_version: int,
) -> WorkItem:
    """
    Transition a work item's status with workflow validation.
    Atomically updates status + version + timestamps in a single transaction.
    """
    item = get_work_item_or_404(db, work_item_id, actor)

    if not can_update_work_item(actor, item):
        raise ForbiddenError("You don't have permission to change this work item's status")

    # Validate workflow transition (raises WorkflowError if invalid)
    validate_transition(item.status, new_status)

    # Check if item requires approval before proceeding to resolved or closed
    if item.requires_approval and item.approval_status != ApprovalStatus.APPROVED:
        if new_status in (WorkItemStatus.RESOLVED, WorkItemStatus.CLOSED):
            raise WorkflowError("Work item requires approval before it can be resolved or closed")

    now = datetime.now(timezone.utc)
    update_dict = {
        "status": new_status,
        "version": item.version + 1,
        "updated_at": now,
    }

    # Handle resolved/closed timestamps
    if new_status == WorkItemStatus.RESOLVED:
        update_dict["resolved_at"] = now
        event_type = EventType.WORK_ITEM_RESOLVED
    elif new_status == WorkItemStatus.CLOSED:
        update_dict["closed_at"] = now
        event_type = EventType.WORK_ITEM_CLOSED
    elif item.status in (WorkItemStatus.RESOLVED, WorkItemStatus.CLOSED) and new_status == WorkItemStatus.IN_PROGRESS:
        # Reopening - clear resolution timestamps
        update_dict["resolved_at"] = None
        update_dict["closed_at"] = None
        event_type = EventType.WORK_ITEM_REOPENED
    else:
        event_type = EventType.STATUS_CHANGED

    old_status = item.status

    # Conditional update with version check
    result = db.execute(
        update(WorkItem)
        .where(WorkItem.id == work_item_id, WorkItem.version == expected_version)
        .values(**update_dict)
        .returning(WorkItem.version)
    )
    updated = result.fetchone()

    if not updated:
        db.rollback()
        current = db.query(WorkItem).filter(WorkItem.id == work_item_id).first()
        if not current or not can_access_work_item(actor, current):
            raise NotFoundError("Work item not found")
        raise StaleVersionError(current_version=current.version)

    db.refresh(item)
    log_event(
        db, item, actor, event_type,
        f"Changed status from {old_status.value} to {new_status.value}",
        field_name="status",
        previous_value=old_status.value,
        new_value=new_status.value,
    )

    db.commit()
    db.refresh(item)
    return item


def claim_work_item(db: Session, actor: User, work_item_id: str) -> WorkItem:
    """
    Atomically claim a work item (assign to self).
    Uses conditional UPDATE to prevent race conditions:
    Only updates if assignee is currently NULL.
    If another user claims simultaneously, exactly one wins.
    """
    item = get_work_item_or_404(db, work_item_id, actor)

    if not can_claim_work_item(actor, item):
        raise ForbiddenError("You don't have permission to claim this work item")

    now = datetime.now(timezone.utc)

    # Atomic conditional update: only succeeds if assignee is still NULL
    result = db.execute(
        update(WorkItem)
        .where(WorkItem.id == work_item_id, WorkItem.assignee_id.is_(None))
        .values(
            assignee_id=actor.id,
            version=WorkItem.version + 1,
            updated_at=now,
        )
        .returning(WorkItem.version, WorkItem.assignee_id)
    )
    updated = result.fetchone()

    if not updated:
        db.rollback()
        # Re-fetch current state to provide informative error
        current = db.query(WorkItem).filter(WorkItem.id == work_item_id).first()
        if not current or not can_access_work_item(actor, current):
            raise NotFoundError("Work item not found")
        # Item already assigned
        assignee_name = current.assignee.name if current.assignee else "another user"
        raise AlreadyClaimedError(assignee_name=assignee_name)

    db.refresh(item)
    log_event(
        db, item, actor, EventType.WORK_ITEM_CLAIMED,
        f"{actor.name} claimed this work item",
        field_name="assignee_id",
        previous_value=None,
        new_value=actor.id,
    )

    db.commit()
    db.refresh(item)
    return item


def assign_work_item(
    db: Session,
    actor: User,
    work_item_id: str,
    assignee_id: Optional[str],
    expected_version: int,
) -> WorkItem:
    """Assign a work item to a specific user (or unassign if assignee_id is None)."""
    item = get_work_item_or_404(db, work_item_id, actor)

    if not can_assign_work_item(actor, item):
        raise ForbiddenError("You don't have permission to assign this work item")

    old_assignee_id = item.assignee_id
    now = datetime.now(timezone.utc)

    result = db.execute(
        update(WorkItem)
        .where(WorkItem.id == work_item_id, WorkItem.version == expected_version)
        .values(
            assignee_id=assignee_id,
            version=WorkItem.version + 1,
            updated_at=now,
        )
        .returning(WorkItem.version)
    )
    updated = result.fetchone()

    if not updated:
        db.rollback()
        current = db.query(WorkItem).filter(WorkItem.id == work_item_id).first()
        if not current or not can_access_work_item(actor, current):
            raise NotFoundError("Work item not found")
        raise StaleVersionError(current_version=current.version)

    db.refresh(item)
    log_event(
        db, item, actor, EventType.ASSIGNEE_CHANGED,
        f"Assignee changed",
        field_name="assignee_id",
        previous_value=old_assignee_id,
        new_value=assignee_id,
    )

    db.commit()
    db.refresh(item)
    return item


def decide_approval(
    db: Session,
    actor: User,
    work_item_id: str,
    decision: str,  # "approved" or "rejected"
    explanation: Optional[str] = None,
) -> WorkItem:
    """Record an approval or rejection for a work item requiring approval."""
    from app.models.approval import ApprovalRecord, ApprovalDecision
    from app.core.permissions import can_approve_work_item

    item = get_work_item_or_404(db, work_item_id, actor)

    if not can_approve_work_item(actor, item):
        raise ForbiddenError("You don't have permission to approve/reject this work item")

    if not item.requires_approval or item.approval_status != ApprovalStatus.PENDING:
        raise WorkflowError("This work item does not have a pending approval request")

    approval_decision = (
        ApprovalDecision.APPROVED if decision.lower() == "approved" else ApprovalDecision.REJECTED
    )
    new_approval_status = (
        ApprovalStatus.APPROVED if approval_decision == ApprovalDecision.APPROVED else ApprovalStatus.REJECTED
    )
    now = datetime.now(timezone.utc)

    # Insert approval record
    record = ApprovalRecord(
        work_item_id=item.id,
        requested_by_id=item.created_by_id,
        decided_by_id=actor.id,
        decision=approval_decision,
        explanation=explanation,
        decided_at=now,
    )
    db.add(record)

    # Update item approval status & bump version
    item.approval_status = new_approval_status
    item.version = item.version + 1
    item.updated_at = now

    event_type = (
        EventType.APPROVAL_GRANTED
        if approval_decision == ApprovalDecision.APPROVED
        else EventType.APPROVAL_REJECTED
    )
    decision_text = "approved" if approval_decision == ApprovalDecision.APPROVED else "rejected"
    summary = f"{actor.name} {decision_text} the approval request"
    if explanation:
        summary += f": {explanation}"

    log_event(
        db, item, actor, event_type, summary,
        field_name="approval_status",
        previous_value=ApprovalStatus.PENDING.value,
        new_value=new_approval_status.value,
        metadata={"decision": approval_decision.value, "explanation": explanation},
    )

    db.commit()
    db.refresh(item)
    return item


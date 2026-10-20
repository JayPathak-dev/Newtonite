"""Activity log service - creates audit events."""
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.models.activity import ActivityLog, EventType
from app.models.user import User
from app.models.work_item import WorkItem


def log_event(
    db: Session,
    work_item: WorkItem,
    actor: User,
    event_type: EventType,
    summary: str,
    field_name: str = None,
    previous_value: str = None,
    new_value: str = None,
    metadata: dict = None,
) -> ActivityLog:
    """
    Create an activity log entry. This should be called within the same
    transaction as the corresponding business operation.
    """
    log = ActivityLog(
        work_item_id=work_item.id,
        actor_id=actor.id,
        event_type=event_type,
        field_name=field_name,
        previous_value=str(previous_value) if previous_value is not None else None,
        new_value=str(new_value) if new_value is not None else None,
        summary=summary,
        metadata_=metadata,
        created_at=datetime.now(timezone.utc),
    )
    db.add(log)
    return log

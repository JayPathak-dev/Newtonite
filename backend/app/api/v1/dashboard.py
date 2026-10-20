"""Dashboard API router."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.services.dashboard_service import (
    get_dashboard_summary, get_needs_attention,
    get_my_work, get_recent_activity_items, get_status_breakdown,
)

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary")
def dashboard_summary(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return get_dashboard_summary(db, current_user)


@router.get("/needs-attention")
def needs_attention(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    items = get_needs_attention(db, current_user, limit=10)
    return _serialize_items(items)


@router.get("/my-work")
def my_work(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    items = get_my_work(db, current_user, limit=10)
    return _serialize_items(items)


@router.get("/recent-activity")
def recent_activity(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    items = get_recent_activity_items(db, current_user, limit=10)
    return _serialize_items(items)


@router.get("/status-breakdown")
def status_breakdown(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return get_status_breakdown(db, current_user)


def _serialize_items(items) -> list:
    result = []
    for item in items:
        result.append({
            "id": item.id,
            "key": item.key,
            "title": item.title,
            "status": item.status.value,
            "priority": item.priority.value,
            "work_type": item.work_type.value,
            "team_id": item.team_id,
            "team_name": item.team.name if item.team else None,
            "assignee_id": item.assignee_id,
            "assignee_name": item.assignee.name if item.assignee else None,
            "due_at": item.due_at.isoformat() if item.due_at else None,
            "updated_at": item.updated_at.isoformat(),
            "created_at": item.created_at.isoformat(),
        })
    return result

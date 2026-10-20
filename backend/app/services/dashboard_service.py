"""Dashboard service - real database aggregates."""
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, case
from app.models.work_item import WorkItem, WorkItemStatus, WorkItemPriority, ApprovalStatus
from app.models.user import User, SystemRole
from app.core.permissions import get_user_team_ids


def get_user_scope_filter(user: User):
    """Build SQLAlchemy filter for work items visible to this user."""
    if user.role == SystemRole.ADMIN:
        return None  # No filter - see everything
    team_ids = list(get_user_team_ids(user))
    if not team_ids:
        return WorkItem.id == None  # User has no teams - see nothing
    return WorkItem.team_id.in_(team_ids)


def get_dashboard_summary(db: Session, user: User) -> dict:
    """Compute dashboard summary metrics scoped to user's authorized teams."""
    scope_filter = get_user_scope_filter(user)
    now = datetime.now(timezone.utc)

    base_query = db.query(WorkItem)
    if scope_filter is not None:
        base_query = base_query.filter(scope_filter)

    active_statuses = [
        WorkItemStatus.OPEN, WorkItemStatus.IN_PROGRESS,
        WorkItemStatus.BLOCKED, WorkItemStatus.IN_REVIEW
    ]
    active_query = base_query.filter(WorkItem.status.in_(active_statuses))

    total_open = active_query.count()
    critical = active_query.filter(WorkItem.priority == WorkItemPriority.CRITICAL).count()
    unassigned = active_query.filter(WorkItem.assignee_id.is_(None)).count()
    overdue = active_query.filter(
        WorkItem.due_at.isnot(None),
        WorkItem.due_at < now,
    ).count()
    pending_approvals = base_query.filter(
        WorkItem.approval_status == ApprovalStatus.PENDING
    ).count()
    blocked = base_query.filter(WorkItem.status == WorkItemStatus.BLOCKED).count()

    return {
        "total_open": total_open,
        "critical": critical,
        "unassigned": unassigned,
        "overdue": overdue,
        "pending_approvals": pending_approvals,
        "blocked": blocked,
    }


def get_needs_attention(db: Session, user: User, limit: int = 10) -> list[WorkItem]:
    """Get work items needing attention: critical, overdue, blocked, or unassigned."""
    scope_filter = get_user_scope_filter(user)
    now = datetime.now(timezone.utc)
    active_statuses = [
        WorkItemStatus.OPEN, WorkItemStatus.IN_PROGRESS,
        WorkItemStatus.BLOCKED, WorkItemStatus.IN_REVIEW
    ]

    query = db.query(WorkItem).filter(WorkItem.status.in_(active_statuses))
    if scope_filter is not None:
        query = query.filter(scope_filter)

    query = query.filter(
        (WorkItem.priority == WorkItemPriority.CRITICAL) |
        (and_(WorkItem.due_at.isnot(None), WorkItem.due_at < now)) |
        (WorkItem.status == WorkItemStatus.BLOCKED) |
        (WorkItem.assignee_id.is_(None))
    )

    return query.order_by(
        # Critical first, then blocked, then overdue, then unassigned
        case(
            (WorkItem.priority == WorkItemPriority.CRITICAL, 0),
            (WorkItem.status == WorkItemStatus.BLOCKED, 1),
            else_=2,
        ),
        WorkItem.updated_at.desc(),
    ).limit(limit).all()


def get_my_work(db: Session, user: User, limit: int = 10) -> list[WorkItem]:
    """Get work items assigned to the current user."""
    active_statuses = [
        WorkItemStatus.OPEN, WorkItemStatus.IN_PROGRESS,
        WorkItemStatus.BLOCKED, WorkItemStatus.IN_REVIEW
    ]
    return (
        db.query(WorkItem)
        .filter(
            WorkItem.assignee_id == user.id,
            WorkItem.status.in_(active_statuses),
        )
        .order_by(WorkItem.updated_at.desc())
        .limit(limit)
        .all()
    )


def get_recent_activity_items(db: Session, user: User, limit: int = 10) -> list[WorkItem]:
    """Get recently updated work items visible to user."""
    scope_filter = get_user_scope_filter(user)
    query = db.query(WorkItem)
    if scope_filter is not None:
        query = query.filter(scope_filter)
    return query.order_by(WorkItem.updated_at.desc()).limit(limit).all()


def get_status_breakdown(db: Session, user: User) -> list[dict]:
    """Get count of work items by status."""
    scope_filter = get_user_scope_filter(user)
    query = db.query(WorkItem.status, func.count(WorkItem.id).label("count"))
    if scope_filter is not None:
        query = query.filter(scope_filter)
    results = query.group_by(WorkItem.status).all()
    return [{"status": r.status.value, "count": r.count} for r in results]

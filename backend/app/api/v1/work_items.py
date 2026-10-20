"""Work items API router."""
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, Query, Header
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, func

from app.database import get_db
from app.core.dependencies import get_current_user
from app.core.permissions import can_create_work_item, can_access_work_item, can_comment_on_work_item
from app.core.exceptions import ForbiddenError, NotFoundError
from app.models.work_item import WorkItem, WorkItemStatus, WorkItemPriority, WorkType, ApprovalStatus
from app.models.comment import Comment
from app.models.activity import ActivityLog
from app.models.approval import ApprovalRecord
from app.models.user import User
from app.schemas.work_item import (
    WorkItemCreate, WorkItemUpdate, WorkItemResponse,
    WorkItemListResponse, StatusTransitionRequest, AssignRequest,
)
from app.schemas.comment import CommentCreate, CommentResponse, ActivityLogResponse, PaginatedActivityResponse
from app.schemas.team import ApprovalDecisionRequest, ApprovalRecordResponse
from app.services.work_item_service import (
    create_work_item, update_work_item, transition_status,
    claim_work_item, assign_work_item, get_work_item_or_404,
    decide_approval,
)
from app.services.activity_service import log_event
from app.models.activity import EventType

router = APIRouter(prefix="/work-items", tags=["work-items"])

VALID_SORT_FIELDS = {"created_at", "updated_at", "priority", "status", "due_at", "key"}


@router.post("", response_model=WorkItemResponse, status_code=201)
def create_item(
    data: WorkItemCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not can_create_work_item(current_user, data.team_id):
        raise ForbiddenError("You don't have permission to create work items in this team")

    item = create_work_item(
        db=db,
        actor=current_user,
        title=data.title,
        team_id=data.team_id,
        work_type=data.work_type,
        priority=data.priority,
        description=data.description,
        assignee_id=data.assignee_id,
        due_at=data.due_at,
        requires_approval=data.requires_approval,
        idempotency_key=data.idempotency_key,
    )
    return item


@router.get("", response_model=WorkItemListResponse)
def list_items(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    search: Optional[str] = Query(default=None),
    status: Optional[WorkItemStatus] = Query(default=None),
    priority: Optional[WorkItemPriority] = Query(default=None),
    work_type: Optional[WorkType] = Query(default=None),
    team_id: Optional[str] = Query(default=None),
    assignee_id: Optional[str] = Query(default=None),
    approval_status: Optional[ApprovalStatus] = Query(default=None),
    overdue: Optional[bool] = Query(default=None),
    sort_by: str = Query(default="updated_at"),
    sort_order: str = Query(default="desc"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from app.core.permissions import get_user_team_ids
    from app.models.user import SystemRole

    # Validate sort field
    if sort_by not in VALID_SORT_FIELDS:
        sort_by = "updated_at"
    if sort_order not in ("asc", "desc"):
        sort_order = "desc"

    query = db.query(WorkItem)

    # Scope to authorized teams
    if current_user.role != SystemRole.ADMIN:
        team_ids = list(get_user_team_ids(current_user))
        if not team_ids:
            return WorkItemListResponse(items=[], total=0, page=page, page_size=page_size, total_pages=0)
        query = query.filter(WorkItem.team_id.in_(team_ids))

    # Apply filters
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            or_(
                WorkItem.title.ilike(search_term),
                WorkItem.key.ilike(search_term),
                WorkItem.description.ilike(search_term),
            )
        )
    if status:
        query = query.filter(WorkItem.status == status)
    if priority:
        query = query.filter(WorkItem.priority == priority)
    if work_type:
        query = query.filter(WorkItem.work_type == work_type)
    if team_id:
        query = query.filter(WorkItem.team_id == team_id)
    if approval_status:
        query = query.filter(WorkItem.approval_status == approval_status)
    if assignee_id:
        if assignee_id == "unassigned":
            query = query.filter(WorkItem.assignee_id.is_(None))
        else:
            query = query.filter(WorkItem.assignee_id == assignee_id)
    if overdue:
        now = datetime.now(timezone.utc)
        query = query.filter(
            WorkItem.due_at.isnot(None),
            WorkItem.due_at < now,
            WorkItem.status.notin_([WorkItemStatus.RESOLVED, WorkItemStatus.CLOSED]),
        )

    total = query.count()

    # Apply sorting
    sort_col = getattr(WorkItem, sort_by)
    if sort_order == "desc":
        sort_col = sort_col.desc()
    # Always add secondary sort for determinism
    query = query.order_by(sort_col, WorkItem.id.asc())

    # Pagination
    offset = (page - 1) * page_size
    items = query.offset(offset).limit(page_size).all()
    total_pages = (total + page_size - 1) // page_size if total > 0 else 0

    return WorkItemListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/{work_item_id}", response_model=WorkItemResponse)
def get_item(
    work_item_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return get_work_item_or_404(db, work_item_id, current_user)


@router.patch("/{work_item_id}", response_model=WorkItemResponse)
def update_item(
    work_item_id: str,
    data: WorkItemUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    updates = data.model_dump(exclude={"version"}, exclude_none=False, exclude_unset=True)
    return update_work_item(db, current_user, work_item_id, data.version, **updates)


@router.post("/{work_item_id}/transition", response_model=WorkItemResponse)
def transition_item_status(
    work_item_id: str,
    data: StatusTransitionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return transition_status(db, current_user, work_item_id, data.status, data.version)


@router.post("/{work_item_id}/claim", response_model=WorkItemResponse)
def claim_item(
    work_item_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return claim_work_item(db, current_user, work_item_id)


@router.post("/{work_item_id}/assign", response_model=WorkItemResponse)
def assign_item(
    work_item_id: str,
    data: AssignRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return assign_work_item(db, current_user, work_item_id, data.assignee_id, data.version)


@router.post("/{work_item_id}/approval", response_model=WorkItemResponse)
def submit_approval_decision(
    work_item_id: str,
    data: ApprovalDecisionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return decide_approval(
        db=db,
        actor=current_user,
        work_item_id=work_item_id,
        decision=data.decision,
        explanation=data.explanation,
    )


@router.get("/{work_item_id}/approvals", response_model=list[ApprovalRecordResponse])
def get_work_item_approvals(
    work_item_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    get_work_item_or_404(db, work_item_id, current_user)
    return (
        db.query(ApprovalRecord)
        .filter(ApprovalRecord.work_item_id == work_item_id)
        .order_by(ApprovalRecord.requested_at.desc())
        .all()
    )



@router.post("/{work_item_id}/comments", response_model=CommentResponse, status_code=201)
def add_comment(
    work_item_id: str,
    data: CommentCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    item = get_work_item_or_404(db, work_item_id, current_user)
    if not can_comment_on_work_item(current_user, item):
        raise ForbiddenError("You don't have permission to comment on this work item")

    comment = Comment(
        work_item_id=work_item_id,
        author_id=current_user.id,
        body=data.body,
    )
    db.add(comment)
    db.flush()

    log_event(
        db, item, current_user, EventType.COMMENT_ADDED,
        f"{current_user.name} added a comment",
        metadata={"comment_id": comment.id},
    )

    db.commit()
    db.refresh(comment)
    return comment


@router.get("/{work_item_id}/comments", response_model=list[CommentResponse])
def get_comments(
    work_item_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    item = get_work_item_or_404(db, work_item_id, current_user)
    return (
        db.query(Comment)
        .filter(Comment.work_item_id == work_item_id)
        .order_by(Comment.created_at.asc())
        .all()
    )


@router.get("/{work_item_id}/activity", response_model=PaginatedActivityResponse)
def get_activity(
    work_item_id: str,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    item = get_work_item_or_404(db, work_item_id, current_user)

    query = db.query(ActivityLog).filter(ActivityLog.work_item_id == work_item_id)
    total = query.count()
    offset = (page - 1) * page_size
    items = query.order_by(ActivityLog.created_at.desc(), ActivityLog.id.asc()).offset(offset).limit(page_size).all()

    return PaginatedActivityResponse(items=items, total=total, page=page, page_size=page_size)

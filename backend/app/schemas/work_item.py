"""Work item Pydantic schemas."""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, field_validator, model_validator
from app.models.work_item import WorkItemStatus, WorkItemPriority, WorkType, ApprovalStatus


class UserBrief(BaseModel):
    id: str
    name: str
    email: str
    model_config = {"from_attributes": True}


class TeamBrief(BaseModel):
    id: str
    name: str
    model_config = {"from_attributes": True}


class WorkItemCreate(BaseModel):
    title: str
    description: Optional[str] = None
    work_type: WorkType
    priority: WorkItemPriority
    team_id: str
    assignee_id: Optional[str] = None
    due_at: Optional[datetime] = None
    requires_approval: bool = False
    idempotency_key: Optional[str] = None

    @field_validator("title")
    @classmethod
    def title_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Title cannot be empty")
        if len(v) > 500:
            raise ValueError("Title must be 500 characters or fewer")
        return v


class WorkItemUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[WorkItemPriority] = None
    assignee_id: Optional[str] = None
    due_at: Optional[datetime] = None
    version: int  # Required for optimistic concurrency

    @field_validator("title")
    @classmethod
    def title_not_empty(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip()
            if not v:
                raise ValueError("Title cannot be empty")
        return v


class StatusTransitionRequest(BaseModel):
    status: WorkItemStatus
    version: int


class AssignRequest(BaseModel):
    assignee_id: Optional[str]
    version: int


class WorkItemResponse(BaseModel):
    id: str
    key: str
    title: str
    description: Optional[str]
    status: WorkItemStatus
    priority: WorkItemPriority
    work_type: WorkType
    team_id: str
    team: Optional[TeamBrief] = None
    assignee_id: Optional[str]
    assignee: Optional[UserBrief] = None
    created_by_id: str
    created_by: Optional[UserBrief] = None
    due_at: Optional[datetime]
    requires_approval: bool
    approval_status: ApprovalStatus
    version: int
    created_at: datetime
    updated_at: datetime
    resolved_at: Optional[datetime]
    closed_at: Optional[datetime]

    model_config = {"from_attributes": True}


class WorkItemListResponse(BaseModel):
    items: list[WorkItemResponse]
    total: int
    page: int
    page_size: int
    total_pages: int

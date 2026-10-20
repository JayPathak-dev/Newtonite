"""Comment and activity schemas."""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, field_validator


class CommentCreate(BaseModel):
    body: str

    @field_validator("body")
    @classmethod
    def body_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Comment body cannot be empty")
        if len(v) > 10000:
            raise ValueError("Comment must be 10000 characters or fewer")
        return v


class UserBrief(BaseModel):
    id: str
    name: str
    email: str
    model_config = {"from_attributes": True}


class CommentResponse(BaseModel):
    id: str
    work_item_id: str
    author_id: str
    author: Optional[UserBrief] = None
    body: str
    created_at: datetime
    updated_at: datetime
    model_config = {"from_attributes": True}


class ActivityLogResponse(BaseModel):
    id: str
    work_item_id: str
    actor_id: Optional[str]
    actor: Optional[UserBrief] = None
    event_type: str
    field_name: Optional[str]
    previous_value: Optional[str]
    new_value: Optional[str]
    summary: str
    created_at: datetime
    model_config = {"from_attributes": True}


class PaginatedActivityResponse(BaseModel):
    items: list[ActivityLogResponse]
    total: int
    page: int
    page_size: int

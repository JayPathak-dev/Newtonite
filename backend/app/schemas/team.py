"""Team and approval schemas."""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class UserBrief(BaseModel):
    id: str
    name: str
    email: str
    role: str
    model_config = {"from_attributes": True}


class TeamMemberResponse(BaseModel):
    user_id: str
    team_id: str
    team_role: str
    user: Optional[UserBrief] = None
    created_at: datetime
    model_config = {"from_attributes": True}


class TeamResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    is_active: bool
    created_at: datetime
    members: list[TeamMemberResponse] = []
    model_config = {"from_attributes": True}


class ApprovalDecisionRequest(BaseModel):
    decision: str  # "approved" or "rejected"
    explanation: Optional[str] = None


class ApprovalRecordResponse(BaseModel):
    id: str
    work_item_id: str
    decision: str
    explanation: Optional[str]
    requested_at: datetime
    decided_at: Optional[datetime]
    model_config = {"from_attributes": True}

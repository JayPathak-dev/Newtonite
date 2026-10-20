"""Work Item model with all business fields."""
import uuid
import enum
from datetime import datetime, timezone
from sqlalchemy import (
    String, Text, Boolean, DateTime, ForeignKey, Integer,
    Enum as SAEnum, Index, CheckConstraint
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base


class WorkItemStatus(str, enum.Enum):
    OPEN = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    BLOCKED = "BLOCKED"
    IN_REVIEW = "IN_REVIEW"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"


class WorkItemPriority(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class WorkType(str, enum.Enum):
    INCIDENT = "incident"
    TASK = "task"
    CUSTOMER_ISSUE = "customer_issue"
    ENGINEERING_ISSUE = "engineering_issue"
    PAYMENT_INVESTIGATION = "payment_investigation"
    COMPLIANCE_REQUEST = "compliance_request"
    APPROVAL_REQUEST = "approval_request"


class ApprovalStatus(str, enum.Enum):
    NOT_REQUIRED = "not_required"
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class WorkItem(Base):
    __tablename__ = "work_items"
    __table_args__ = (
        Index("ix_work_items_status", "status"),
        Index("ix_work_items_priority", "priority"),
        Index("ix_work_items_team_id", "team_id"),
        Index("ix_work_items_assignee_id", "assignee_id"),
        Index("ix_work_items_created_by_id", "created_by_id"),
        Index("ix_work_items_due_at", "due_at"),
        Index("ix_work_items_updated_at", "updated_at"),
    )

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    key: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    status: Mapped[WorkItemStatus] = mapped_column(SAEnum(WorkItemStatus), default=WorkItemStatus.OPEN, nullable=False)
    priority: Mapped[WorkItemPriority] = mapped_column(SAEnum(WorkItemPriority), default=WorkItemPriority.MEDIUM, nullable=False)
    work_type: Mapped[WorkType] = mapped_column(SAEnum(WorkType), default=WorkType.TASK, nullable=False)

    # Foreign keys
    team_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("teams.id"), nullable=False)
    assignee_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=True)
    created_by_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False)

    # Timing
    due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    resolved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)

    # Approval
    requires_approval: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    approval_status: Mapped[ApprovalStatus] = mapped_column(
        SAEnum(ApprovalStatus), default=ApprovalStatus.NOT_REQUIRED, nullable=False
    )

    # Optimistic concurrency control
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    # Relationships
    team = relationship("Team", back_populates="work_items")
    assignee = relationship("User", foreign_keys=[assignee_id], back_populates="assigned_work_items")
    created_by = relationship("User", foreign_keys=[created_by_id], back_populates="created_work_items")
    comments = relationship("Comment", back_populates="work_item", order_by="Comment.created_at")
    activity_logs = relationship("ActivityLog", back_populates="work_item", order_by="ActivityLog.created_at")
    approvals = relationship("ApprovalRecord", back_populates="work_item")

    def __repr__(self) -> str:
        return f"<WorkItem key={self.key} status={self.status}>"

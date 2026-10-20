"""Activity Log model for immutable event history."""
import uuid
import enum
from datetime import datetime, timezone
from sqlalchemy import String, Text, DateTime, ForeignKey, JSON, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base


class EventType(str, enum.Enum):
    WORK_ITEM_CREATED = "WORK_ITEM_CREATED"
    ASSIGNEE_CHANGED = "ASSIGNEE_CHANGED"
    WORK_ITEM_CLAIMED = "WORK_ITEM_CLAIMED"
    STATUS_CHANGED = "STATUS_CHANGED"
    PRIORITY_CHANGED = "PRIORITY_CHANGED"
    TEAM_CHANGED = "TEAM_CHANGED"
    DUE_DATE_CHANGED = "DUE_DATE_CHANGED"
    DESCRIPTION_CHANGED = "DESCRIPTION_CHANGED"
    TITLE_CHANGED = "TITLE_CHANGED"
    COMMENT_ADDED = "COMMENT_ADDED"
    APPROVAL_REQUESTED = "APPROVAL_REQUESTED"
    APPROVAL_GRANTED = "APPROVAL_GRANTED"
    APPROVAL_REJECTED = "APPROVAL_REJECTED"
    WORK_ITEM_RESOLVED = "WORK_ITEM_RESOLVED"
    WORK_ITEM_CLOSED = "WORK_ITEM_CLOSED"
    WORK_ITEM_REOPENED = "WORK_ITEM_REOPENED"


class ActivityLog(Base):
    __tablename__ = "activity_logs"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    work_item_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("work_items.id", ondelete="CASCADE"), nullable=False, index=True)
    actor_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=True)
    event_type: Mapped[EventType] = mapped_column(SAEnum(EventType), nullable=False)
    field_name: Mapped[str] = mapped_column(String(100), nullable=True)
    previous_value: Mapped[str] = mapped_column(Text, nullable=True)
    new_value: Mapped[str] = mapped_column(Text, nullable=True)
    summary: Mapped[str] = mapped_column(String(500), nullable=False)
    metadata_: Mapped[dict] = mapped_column("metadata", JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)

    # Relationships
    work_item = relationship("WorkItem", back_populates="activity_logs")
    actor = relationship("User", back_populates="activity_logs")

    def __repr__(self) -> str:
        return f"<ActivityLog event={self.event_type} work_item={self.work_item_id}>"

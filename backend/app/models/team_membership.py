"""Team Membership model."""
import uuid
import enum
from datetime import datetime, timezone
from sqlalchemy import String, DateTime, ForeignKey, Enum as SAEnum, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base


class TeamRole(str, enum.Enum):
    MEMBER = "MEMBER"
    LEAD = "LEAD"
    APPROVER = "APPROVER"


class TeamMembership(Base):
    __tablename__ = "team_memberships"
    __table_args__ = (
        UniqueConstraint("user_id", "team_id", name="uq_team_membership"),
    )

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    team_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("teams.id", ondelete="CASCADE"), nullable=False, index=True)
    team_role: Mapped[TeamRole] = mapped_column(SAEnum(TeamRole), default=TeamRole.MEMBER, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationships
    user = relationship("User", back_populates="team_memberships")
    team = relationship("Team", back_populates="members")

    def __repr__(self) -> str:
        return f"<TeamMembership user={self.user_id} team={self.team_id} role={self.team_role}>"

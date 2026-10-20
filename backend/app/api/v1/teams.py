"""Teams and users API router."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.core.dependencies import get_current_user
from app.core.permissions import can_access_work_item, get_user_team_ids
from app.core.exceptions import NotFoundError, ForbiddenError
from app.models.team import Team
from app.models.team_membership import TeamMembership
from app.models.user import User, SystemRole

router = APIRouter(tags=["teams"])
users_router = APIRouter(prefix="/users", tags=["users"])


@router.get("/teams")
def list_teams(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role == SystemRole.ADMIN:
        teams = db.query(Team).filter(Team.is_active == True).all()
    else:
        team_ids = list(get_user_team_ids(current_user))
        teams = db.query(Team).filter(Team.id.in_(team_ids), Team.is_active == True).all()

    return [
        {
            "id": t.id,
            "name": t.name,
            "description": t.description,
            "is_active": t.is_active,
            "created_at": t.created_at,
            "member_count": len(t.members),
        }
        for t in teams
    ]


@router.get("/teams/{team_id}")
def get_team(
    team_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise NotFoundError("Team not found")

    if current_user.role != SystemRole.ADMIN:
        if team_id not in get_user_team_ids(current_user):
            raise NotFoundError("Team not found")

    return {
        "id": team.id,
        "name": team.name,
        "description": team.description,
        "is_active": team.is_active,
        "created_at": team.created_at,
        "members": [
            {
                "user_id": m.user_id,
                "team_id": m.team_id,
                "team_role": m.team_role.value,
                "user": {"id": m.user.id, "name": m.user.name, "email": m.user.email, "role": m.user.role.value},
                "created_at": m.created_at,
            }
            for m in team.members
        ],
    }


@router.get("/teams/{team_id}/members")
def get_team_members(
    team_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role != SystemRole.ADMIN:
        if team_id not in get_user_team_ids(current_user):
            raise NotFoundError("Team not found")

    members = (
        db.query(TeamMembership)
        .filter(TeamMembership.team_id == team_id)
        .all()
    )
    return [
        {
            "user_id": m.user_id,
            "team_id": m.team_id,
            "team_role": m.team_role.value,
            "user": {"id": m.user.id, "name": m.user.name, "email": m.user.email},
            "created_at": m.created_at,
        }
        for m in members
    ]


@users_router.get("")
def list_users(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    team_id: Optional[str] = Query(default=None),
):
    """List users for assignment/mention purposes."""
    query = db.query(User).filter(User.is_active == True)

    if current_user.role != SystemRole.ADMIN:
        # Only show users in the same teams
        user_team_ids = list(get_user_team_ids(current_user))
        from app.models.team_membership import TeamMembership
        users_in_teams = db.query(TeamMembership.user_id).filter(
            TeamMembership.team_id.in_(user_team_ids)
        ).subquery()
        query = query.filter(User.id.in_(users_in_teams))

    if team_id:
        from app.models.team_membership import TeamMembership
        users_in_team = db.query(TeamMembership.user_id).filter(
            TeamMembership.team_id == team_id
        ).subquery()
        query = query.filter(User.id.in_(users_in_team))

    users = query.order_by(User.name).all()
    return [
        {"id": u.id, "name": u.name, "email": u.email, "role": u.role.value}
        for u in users
    ]

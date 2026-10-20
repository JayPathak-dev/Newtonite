"""Permission checking logic."""
from typing import Optional
from app.models.user import User, SystemRole
from app.models.team_membership import TeamRole
from app.models.work_item import WorkItem, WorkItemStatus


def get_user_team_ids(user: User) -> set[str]:
    """Return set of team IDs the user belongs to."""
    return {m.team_id for m in user.team_memberships}


def get_user_team_role(user: User, team_id: str) -> Optional[TeamRole]:
    """Get user's role in a specific team, or None if not a member."""
    for m in user.team_memberships:
        if m.team_id == team_id:
            return m.team_role
    return None


def can_access_work_item(user: User, work_item: WorkItem) -> bool:
    """
    Can the user read this work item?
    ADMINs can see all. Others can only see items in their teams.
    We return False for unauthorized access (mapped to 404 to avoid resource enumeration).
    """
    if user.role == SystemRole.ADMIN:
        return True
    return work_item.team_id in get_user_team_ids(user)


def can_create_work_item(user: User, team_id: str) -> bool:
    """Can the user create work items in this team?"""
    if user.role == SystemRole.ADMIN:
        return True
    if user.role == SystemRole.VIEWER:
        return False
    return team_id in get_user_team_ids(user)


def can_update_work_item(user: User, work_item: WorkItem) -> bool:
    """Can the user update this work item's fields?"""
    if user.role == SystemRole.ADMIN:
        return True
    if user.role == SystemRole.VIEWER:
        return False
    return work_item.team_id in get_user_team_ids(user)


def can_transition_status(user: User, work_item: WorkItem, new_status: WorkItemStatus) -> bool:
    """Can the user change this work item's status?"""
    return can_update_work_item(user, work_item)


def can_assign_work_item(user: User, work_item: WorkItem) -> bool:
    """Can the user assign this work item to someone?"""
    if user.role == SystemRole.ADMIN:
        return True
    if user.role == SystemRole.VIEWER:
        return False
    team_role = get_user_team_role(user, work_item.team_id)
    if team_role is None:
        return False
    # Anyone in the team can assign, but LEAD has broader latitude
    return True


def can_claim_work_item(user: User, work_item: WorkItem) -> bool:
    """Can the user claim this work item (assign to themselves)?"""
    if user.role == SystemRole.VIEWER:
        return False
    if user.role == SystemRole.ADMIN:
        return True
    return work_item.team_id in get_user_team_ids(user)


def can_comment_on_work_item(user: User, work_item: WorkItem) -> bool:
    """Can the user add a comment?"""
    if user.role == SystemRole.VIEWER:
        return False
    return can_access_work_item(user, work_item)


def can_approve_work_item(user: User, work_item: WorkItem) -> bool:
    """Can the user approve or reject this work item?"""
    if user.role == SystemRole.ADMIN:
        return True
    team_role = get_user_team_role(user, work_item.team_id)
    return team_role in (TeamRole.APPROVER, TeamRole.LEAD)


def can_manage_team(user: User, team_id: str) -> bool:
    """Can the user manage team members?"""
    if user.role == SystemRole.ADMIN:
        return True
    team_role = get_user_team_role(user, team_id)
    return team_role == TeamRole.LEAD

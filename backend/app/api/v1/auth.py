"""Auth API router."""
from fastapi import APIRouter, Depends, Response, Cookie
from typing import Optional
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.auth import LoginRequest, TokenResponse, MeResponse
from app.services.auth_service import authenticate_user, create_user_token
from app.core.dependencies import get_current_user
from app.core.exceptions import AppError
from app.models.user import User

router = APIRouter(prefix="/auth", tags=["auth"])


def _format_me_response(user: User) -> dict:
    memberships = []
    for m in user.team_memberships:
        memberships.append({
            "team_id": m.team_id,
            "team_name": m.team.name if m.team else None,
            "team_role": m.team_role.value,
        })
    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "role": user.role.value,
        "is_active": user.is_active,
        "team_memberships": memberships,
        "teams": memberships,
    }


@router.post("/login")
def login(request: LoginRequest, response: Response, db: Session = Depends(get_db)):
    user = authenticate_user(db, request.email, request.password)
    token = create_user_token(user)

    # Set HttpOnly cookie for browser clients
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        samesite="lax",
        max_age=86400,  # 24 hours
        # secure=True  # Enable in production
    )

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": _format_me_response(user),
    }


@router.post("/logout")
def logout(response: Response, current_user: User = Depends(get_current_user)):
    response.delete_cookie("access_token")
    return {"message": "Logged out successfully"}


@router.get("/me")
def get_me(current_user: User = Depends(get_current_user)):
    return _format_me_response(current_user)

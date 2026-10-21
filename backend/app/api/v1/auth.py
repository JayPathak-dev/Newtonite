"""Auth API router."""
from fastapi import APIRouter, Depends, Response, Request
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.auth import LoginRequest
from app.services.auth_service import authenticate_user, create_user_token
from app.core.dependencies import get_current_user
from app.core.security import generate_csrf_token
from app.core.rate_limit import check_login_rate_limit, reset_login_rate_limit
from app.config import settings
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
def login(login_req: LoginRequest, request: Request, response: Response, db: Session = Depends(get_db)):
    # 1. Rate limiting check
    check_login_rate_limit(request)

    # 2. Authenticate user
    user = authenticate_user(db, login_req.email, login_req.password)
    reset_login_rate_limit(request)

    # 3. Create tokens
    token = create_user_token(user)
    csrf_token = generate_csrf_token()

    # 4. Set HttpOnly access token cookie
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        samesite="lax",
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        secure=settings.is_production,
        path="/",
    )

    # 5. Set readable CSRF cookie for client header submission
    response.set_cookie(
        key="csrf_token",
        value=csrf_token,
        httponly=False,
        samesite="lax",
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        secure=settings.is_production,
        path="/",
    )

    return {
        "access_token": token,
        "token_type": "bearer",
        "csrf_token": csrf_token,
        "user": _format_me_response(user),
    }


@router.post("/logout")
def logout(response: Response, current_user: User = Depends(get_current_user)):
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("csrf_token", path="/")
    return {"message": "Logged out successfully"}


@router.get("/me")
def get_me(request: Request, response: Response, current_user: User = Depends(get_current_user)):
    # Ensure CSRF token cookie is present on restoration
    existing_csrf = request.cookies.get("csrf_token")
    if not existing_csrf:
        new_csrf = generate_csrf_token()
        response.set_cookie(
            key="csrf_token",
            value=new_csrf,
            httponly=False,
            samesite="lax",
            max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            secure=settings.is_production,
            path="/",
        )
    return _format_me_response(current_user)


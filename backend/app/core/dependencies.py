"""FastAPI dependencies: authentication and authorization."""
from typing import Optional
from fastapi import Depends, HTTPException, status, Cookie, Header
from sqlalchemy.orm import Session
from app.database import get_db
from app.core.security import decode_access_token
from app.core.exceptions import UnauthorizedError, ForbiddenError
from app.models.user import User, SystemRole
import logging

logger = logging.getLogger(__name__)


def get_token_from_cookie_or_header(
    access_token: Optional[str] = Cookie(default=None),
    authorization: Optional[str] = Header(default=None),
) -> Optional[str]:
    """Extract token from HttpOnly cookie or Authorization header."""
    if access_token:
        return access_token
    if authorization and authorization.startswith("Bearer "):
        return authorization[7:]
    return None


def get_current_user(
    db: Session = Depends(get_db),
    token: Optional[str] = Depends(get_token_from_cookie_or_header),
) -> User:
    """Get the currently authenticated user. Raises 401 if not authenticated."""
    if not token:
        raise UnauthorizedError("Authentication required")

    payload = decode_access_token(token)
    if not payload:
        raise UnauthorizedError("Invalid or expired token")

    user_id: str = payload.get("sub")
    if not user_id:
        raise UnauthorizedError("Invalid token payload")

    user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
    if not user:
        logger.warning(f"Token references non-existent or inactive user: {user_id}")
        raise UnauthorizedError("User account not found or inactive")

    return user


def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """Alias for get_current_user - ensures user is active."""
    return current_user


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """Require the user to have ADMIN role."""
    if current_user.role != SystemRole.ADMIN:
        raise ForbiddenError("Admin access required")
    return current_user

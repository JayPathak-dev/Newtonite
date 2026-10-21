"""Auth service - login and user lookup."""
from sqlalchemy.orm import Session
from app.models.user import User
from app.core.security import verify_password, create_access_token
from app.core.exceptions import UnauthorizedError
import logging

logger = logging.getLogger(__name__)


def authenticate_user(db: Session, email: str, password: str) -> User:
    """Authenticate user by email and password. Returns User or raises UnauthorizedError."""
    user = db.query(User).filter(
        User.email == email.lower().strip()
    ).first()
    
    if not user:
        logger.warning(f"Login attempt for unknown email: {email}")
        raise UnauthorizedError("Invalid email or password")

    if not user.is_active:
        logger.warning(f"Login attempt for inactive user: {user.id}")
        raise UnauthorizedError("User account is inactive")
    
    if not verify_password(password, user.password_hash):
        logger.warning(f"Failed login attempt for user: {user.id}")
        raise UnauthorizedError("Invalid email or password")
    
    return user


def create_user_token(user: User) -> str:
    """Create JWT access token for a user."""
    return create_access_token({"sub": str(user.id), "role": user.role.value})

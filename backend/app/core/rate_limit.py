"""In-memory rate limiter for login abuse prevention."""
import time
from collections import defaultdict
from fastapi import Request
from app.core.exceptions import AppError

# Stores timestamps of login attempts per client IP
_LOGIN_ATTEMPTS: dict[str, list[float]] = defaultdict(list)
_WINDOW_SECONDS = 60
_MAX_ATTEMPTS = 15


def check_login_rate_limit(request: Request) -> None:
    """Check if the requesting client IP has exceeded login attempt limits."""
    client_ip = request.client.host if request.client else "unknown"
    now = time.time()
    cutoff = now - _WINDOW_SECONDS

    # Filter out attempts older than window
    attempts = [t for t in _LOGIN_ATTEMPTS[client_ip] if t > cutoff]
    attempts.append(now)
    _LOGIN_ATTEMPTS[client_ip] = attempts

    if len(attempts) > _MAX_ATTEMPTS:
        raise AppError(
            code="RATE_LIMIT_EXCEEDED",
            message="Too many login attempts. Please wait 1 minute before retrying.",
            status_code=429,
        )


def reset_login_rate_limit(request: Request) -> None:
    """Reset attempts on successful login."""
    client_ip = request.client.host if request.client else "unknown"
    _LOGIN_ATTEMPTS.pop(client_ip, None)


def clear_all_rate_limits() -> None:
    """Clear all rate limit records (useful for tests)."""
    _LOGIN_ATTEMPTS.clear()

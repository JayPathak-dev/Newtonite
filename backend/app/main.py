"""FastAPI main application."""
import logging
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.api.router import api_router
from app.core.exceptions import AppError

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL, "INFO"),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Newtonite Ops API",
    description="Operational work management platform",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def csrf_protection_middleware(request: Request, call_next):
    """
    CSRF protection for state-changing HTTP requests.
    Validates Origin/Referer headers and double-submit CSRF cookie/header
    whenever an authenticated session cookie is present.
    """
    # Safe methods do not require CSRF token
    if request.method in ("GET", "HEAD", "OPTIONS"):
        return await call_next(request)

    path = request.url.path

    # Public unauthenticated endpoints exempted from CSRF token check
    if path in ("/api/v1/auth/login", "/health/live", "/health/ready"):
        return await call_next(request)

    # Origin header verification
    origin = request.headers.get("origin")
    if origin and settings.cors_origins_list:
        if origin not in settings.cors_origins_list and origin != f"http://{request.url.netloc}":
            logger.warning(f"Rejected request from untrusted origin: {origin}")
            return JSONResponse(
                status_code=403,
                content={
                    "error": {
                        "code": "FORBIDDEN_ORIGIN",
                        "message": "Request origin is not allowed",
                        "details": {"origin": origin},
                    }
                },
            )

    # If authenticated via HttpOnly cookie, enforce double-submit CSRF token
    has_auth_cookie = "access_token" in request.cookies
    if has_auth_cookie:
        from app.core.security import validate_csrf_tokens
        cookie_csrf = request.cookies.get("csrf_token")
        header_csrf = request.headers.get("X-CSRF-Token") or request.headers.get("x-csrf-token")

        if not validate_csrf_tokens(cookie_csrf, header_csrf):
            logger.warning(f"CSRF validation failed for {request.method} {path}")
            return JSONResponse(
                status_code=403,
                content={
                    "error": {
                        "code": "CSRF_ERROR",
                        "message": "CSRF validation failed: missing or invalid X-CSRF-Token header",
                        "details": {},
                    }
                },
            )

    return await call_next(request)



@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "details": exc.details,
            }
        },
    )


@app.exception_handler(Exception)
async def generic_error_handler(request: Request, exc: Exception):
    logger.exception(f"Unhandled error on {request.method} {request.url}: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred. Please try again.",
                "details": {},
            }
        },
    )


app.include_router(api_router)


@app.get("/health/live")
def liveness():
    return {"status": "ok"}


@app.get("/health/ready")
def readiness():
    """Check database connectivity."""
    from app.database import engine
    from sqlalchemy import text
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "ok", "database": "connected"}
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={"status": "error", "database": "disconnected"},
        )

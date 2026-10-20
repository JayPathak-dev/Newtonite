"""Core exception classes for the application."""
from fastapi import HTTPException, status


class AppError(Exception):
    """Base application error."""
    def __init__(self, code: str, message: str, status_code: int = 400, details: dict = None):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(message)


class NotFoundError(AppError):
    def __init__(self, message: str = "Resource not found", details: dict = None):
        super().__init__("NOT_FOUND", message, 404, details)


class ForbiddenError(AppError):
    def __init__(self, message: str = "Access denied", details: dict = None):
        super().__init__("FORBIDDEN", message, 403, details)


class UnauthorizedError(AppError):
    def __init__(self, message: str = "Authentication required", details: dict = None):
        super().__init__("UNAUTHORIZED", message, 401, details)


class ConflictError(AppError):
    def __init__(self, code: str, message: str, details: dict = None):
        super().__init__(code, message, 409, details)


class StaleVersionError(ConflictError):
    def __init__(self, current_version: int = None):
        details = {"current_version": current_version} if current_version is not None else {}
        super().__init__(
            "STALE_VERSION",
            "This work item has changed since you opened it. Please refresh and try again.",
            details,
        )


class AlreadyClaimedError(ConflictError):
    def __init__(self, assignee_name: str = None):
        details = {"assignee_name": assignee_name} if assignee_name else {}
        super().__init__(
            "ALREADY_CLAIMED",
            "This work item has already been claimed by another user.",
            details,
        )


class IdempotencyConflictError(ConflictError):
    def __init__(self, message: str = "Idempotency key already used with a different request"):
        super().__init__("IDEMPOTENCY_CONFLICT", message)


class ValidationError(AppError):
    def __init__(self, message: str, details: dict = None):
        super().__init__("VALIDATION_ERROR", message, 400, details)


class WorkflowError(AppError):
    def __init__(self, message: str, details: dict = None):
        super().__init__("WORKFLOW_ERROR", message, 400, details)

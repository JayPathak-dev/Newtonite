"""Idempotency service - prevents duplicate work item creation."""
import hashlib
import json
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.models.idempotency import IdempotencyRecord
from app.core.exceptions import IdempotencyConflictError


def _fingerprint(data: dict) -> str:
    """Compute a canonical SHA-256 fingerprint of a request dict."""
    canonical = json.dumps(data, sort_keys=True, default=str)
    return hashlib.sha256(canonical.encode()).hexdigest()


def check_or_create_idempotency(
    db: Session,
    idempotency_key: str,
    actor_id: str,
    operation: str,
    request_data: dict,
) -> tuple[bool, str | None]:
    """
    Check if an idempotency key exists.
    
    Returns:
        (is_duplicate, existing_resource_id)
        - is_duplicate=True, existing_resource_id=str: return cached result
        - is_duplicate=False, existing_resource_id=None: proceed with operation
    
    Raises:
        IdempotencyConflictError: if same key used with different payload
    """
    fingerprint = _fingerprint(request_data)
    
    existing = db.query(IdempotencyRecord).filter(
        IdempotencyRecord.idempotency_key == idempotency_key,
        IdempotencyRecord.actor_id == actor_id,
        IdempotencyRecord.operation == operation,
    ).first()
    
    if existing:
        if existing.request_fingerprint != fingerprint:
            raise IdempotencyConflictError(
                "Idempotency key already used with a different request payload"
            )
        return True, existing.result_resource_id
    
    return False, None


def record_idempotency_result(
    db: Session,
    idempotency_key: str,
    actor_id: str,
    operation: str,
    request_data: dict,
    result_resource_id: str,
) -> IdempotencyRecord:
    """
    Persist the idempotency record after successful creation.
    Must be called within the same transaction as the creation.
    The database uniqueness constraint protects against simultaneous duplicate requests.
    """
    fingerprint = _fingerprint(request_data)
    record = IdempotencyRecord(
        idempotency_key=idempotency_key,
        actor_id=actor_id,
        operation=operation,
        request_fingerprint=fingerprint,
        result_resource_id=result_resource_id,
    )
    db.add(record)
    return record

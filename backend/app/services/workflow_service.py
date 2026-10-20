"""Workflow validation: defines and enforces allowed status transitions."""
from app.models.work_item import WorkItemStatus
from app.core.exceptions import WorkflowError

# Define allowed transitions: from_status -> set of allowed to_statuses
ALLOWED_TRANSITIONS: dict[WorkItemStatus, set[WorkItemStatus]] = {
    WorkItemStatus.OPEN: {
        WorkItemStatus.IN_PROGRESS,
        WorkItemStatus.CLOSED,  # close without work
    },
    WorkItemStatus.IN_PROGRESS: {
        WorkItemStatus.BLOCKED,
        WorkItemStatus.IN_REVIEW,
        WorkItemStatus.RESOLVED,
    },
    WorkItemStatus.BLOCKED: {
        WorkItemStatus.IN_PROGRESS,
        WorkItemStatus.CLOSED,
    },
    WorkItemStatus.IN_REVIEW: {
        WorkItemStatus.IN_PROGRESS,   # send back for more work
        WorkItemStatus.RESOLVED,
    },
    WorkItemStatus.RESOLVED: {
        WorkItemStatus.CLOSED,
        WorkItemStatus.IN_PROGRESS,  # reopen
    },
    WorkItemStatus.CLOSED: set(),    # terminal state - no transitions allowed
}


def validate_transition(current_status: WorkItemStatus, new_status: WorkItemStatus) -> None:
    """
    Validate a status transition. Raises WorkflowError if invalid.
    This is the single source of truth for workflow rules.
    """
    if current_status == new_status:
        raise WorkflowError(
            f"Work item is already in status {current_status.value}",
            {"current_status": current_status.value, "requested_status": new_status.value},
        )

    allowed = ALLOWED_TRANSITIONS.get(current_status, set())
    if new_status not in allowed:
        raise WorkflowError(
            f"Cannot transition from {current_status.value} to {new_status.value}",
            {
                "current_status": current_status.value,
                "requested_status": new_status.value,
                "allowed_transitions": [s.value for s in sorted(allowed, key=lambda x: x.value)],
            },
        )

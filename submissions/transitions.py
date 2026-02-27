"""Submission status transition rules."""

from .models import (
    STATUS_ACCEPTED,
    STATUS_DECISION_PENDING,
    STATUS_DESK_REJECTED,
    STATUS_DRAFT,
    STATUS_REJECTED,
    STATUS_REVISION_REQUIRED,
    STATUS_RESUBMITTED,
    STATUS_SCREENING,
    STATUS_SUBMITTED,
    STATUS_UNDER_REVIEW,
    STATUS_PUBLISHED,
    STATUS_WITHDRAWN,
)

# Allowed transitions: from_status -> [to_statuses]
ALLOWED_TRANSITIONS = {
    STATUS_DRAFT: [STATUS_SUBMITTED, STATUS_WITHDRAWN],
    STATUS_SUBMITTED: [STATUS_SCREENING, STATUS_WITHDRAWN],
    STATUS_SCREENING: [STATUS_DESK_REJECTED, STATUS_UNDER_REVIEW, STATUS_WITHDRAWN],
    STATUS_UNDER_REVIEW: [STATUS_DECISION_PENDING, STATUS_WITHDRAWN],
    STATUS_DECISION_PENDING: [STATUS_ACCEPTED, STATUS_REJECTED, STATUS_REVISION_REQUIRED, STATUS_WITHDRAWN],
    STATUS_REVISION_REQUIRED: [STATUS_RESUBMITTED, STATUS_WITHDRAWN],
    STATUS_RESUBMITTED: [STATUS_UNDER_REVIEW, STATUS_SCREENING, STATUS_WITHDRAWN],
    STATUS_ACCEPTED: [STATUS_PUBLISHED, STATUS_WITHDRAWN],
    # Final states: no outgoing transitions
    STATUS_DESK_REJECTED: [],
    STATUS_REJECTED: [],
    STATUS_PUBLISHED: [],
    STATUS_WITHDRAWN: [],
}


def can_transition(current_status: str, new_status: str) -> bool:
    """Check if transition from current_status to new_status is allowed."""
    allowed = ALLOWED_TRANSITIONS.get(current_status, [])
    return new_status in allowed


def validate_transition(current_status: str, new_status: str) -> None:
    """Raise ValueError if transition is invalid."""
    if not can_transition(current_status, new_status):
        raise ValueError(
            f"Invalid status transition: {current_status} -> {new_status}. "
            f"Allowed: {ALLOWED_TRANSITIONS.get(current_status, [])}"
        )

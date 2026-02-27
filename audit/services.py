"""Audit logging service."""


def log(
    actor_user,
    action_type: str,
    target_type: str,
    target_id,
    old_value=None,
    new_value=None,
):
    """
    Create an audit log entry.
    target_id is coerced to string for consistency.
    """
    from .models import AuditLog

    AuditLog.objects.create(
        actor_user=actor_user,
        action_type=action_type,
        target_type=target_type,
        target_id=str(target_id),
        old_value=old_value,
        new_value=new_value,
    )

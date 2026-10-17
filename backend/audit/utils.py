"""
Append-only audit utility for recording immutable governance events.
"""
from audit.models import AuditEvent


def log_audit(event_type, entity_id, summary, actor=None, details=None):
    """
    Creates an immutable audit record denormalizing actor name for compliance.
    """
    actor_name = 'System'
    if actor:
        actor_name = f"{actor.get_full_name() or actor.username} ({actor.role})"

    return AuditEvent.objects.create(
        type=event_type,
        actor=actor,
        actor_name=actor_name,
        entity_id=str(entity_id),
        summary=summary,
        details=details or {}
    )

import uuid

from audit.models import AuditLog


def log_action(actor, action, entity_type=None, entity_id=None, metadata=None, ip=None):
    payload = metadata.copy() if isinstance(metadata, dict) else {}
    stored_entity_id = None

    if entity_id is not None:
        try:
            stored_entity_id = uuid.UUID(str(entity_id))
        except (TypeError, ValueError, AttributeError):
            payload['entity_id'] = str(entity_id)

    return AuditLog.objects.create(
        user=actor,
        action=action,
        entity_type=entity_type or '',
        entity_id=stored_entity_id,
        metadata=payload,
        ip_adress=ip,
    )
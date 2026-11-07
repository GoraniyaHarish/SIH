"""Audit logging helper. Writes are best-effort but never silently lost on admin actions."""
from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models.users import AuditLog

log = get_logger("audit")


def record(
    db: Session,
    *,
    actor_id: uuid.UUID | None,
    actor_role: str | None,
    action: str,
    resource_type: str | None = None,
    resource_id: str | None = None,
    outcome: str = "success",
    detail: str | None = None,
    ip_hash: str | None = None,
) -> None:
    entry = AuditLog(
        actor_id=actor_id,
        actor_role=actor_role,
        action=action,
        resource_type=resource_type,
        resource_id=str(resource_id)[:64] if resource_id else None,
        outcome=outcome,
        detail=(detail or "")[:2000] or None,
        ip_hash=ip_hash,
    )
    db.add(entry)
    # Caller commits. If the enclosing transaction fails, the audit row rolls back with it,
    # which keeps the log consistent with actual state changes.
    log.info("audit", extra={"extra_fields": {
        "action": action, "resource": resource_type, "outcome": outcome,
    }})

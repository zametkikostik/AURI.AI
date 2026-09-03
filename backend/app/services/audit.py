"""Audit logging service."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.audit import AuditLog

logger = get_logger(__name__)


async def write_audit(
    db: AsyncSession,
    *,
    organization_id: uuid.UUID,
    action: str,
    actor_id: uuid.UUID | None = None,
    resource_type: str | None = None,
    resource_id: str | uuid.UUID | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
    meta: dict[str, Any] | None = None,
) -> AuditLog:
    entry = AuditLog(
        organization_id=organization_id,
        actor_id=actor_id,
        action=action,
        resource_type=resource_type,
        resource_id=str(resource_id) if resource_id is not None else None,
        ip_address=ip_address,
        user_agent=user_agent[:500] if user_agent else None,
        meta=meta,
    )
    db.add(entry)
    await db.flush()
    logger.info(
        "audit",
        action=action,
        org=str(organization_id),
        actor=str(actor_id) if actor_id else None,
        resource=f"{resource_type}:{resource_id}" if resource_type else None,
    )
    return entry

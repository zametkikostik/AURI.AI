"""Data retention & GDPR helpers."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.meeting import Meeting, Recording
from app.models.settings import OrganizationSettings
from app.services.storage import get_storage_service
from app.services.qdrant import get_qdrant_service

logger = get_logger(__name__)


async def get_retention_days(db: AsyncSession, organization_id: UUID) -> int | None:
    row = (
        await db.execute(
            select(OrganizationSettings).where(
                OrganizationSettings.organization_id == organization_id
            )
        )
    ).scalar_one_or_none()
    if not row or not row.meta:
        return None
    days = row.meta.get("retention_days")
    if days is None:
        return None
    try:
        d = int(days)
        return d if d > 0 else None
    except (TypeError, ValueError):
        return None


async def purge_expired_meetings(
    db: AsyncSession,
    organization_id: UUID,
    *,
    dry_run: bool = True,
) -> dict[str, Any]:
    days = await get_retention_days(db, organization_id)
    if not days:
        return {"ok": True, "purged": 0, "message": "No retention policy set"}

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    result = await db.execute(
        select(Meeting).where(
            and_(
                Meeting.organization_id == organization_id,
                Meeting.created_at < cutoff,
            )
        )
    )
    meetings = list(result.scalars().all())
    if dry_run:
        return {
            "ok": True,
            "dry_run": True,
            "would_purge": len(meetings),
            "cutoff": cutoff.isoformat(),
            "retention_days": days,
        }

    storage = get_storage_service()
    qdrant = get_qdrant_service()
    purged = 0
    for m in meetings:
        recs = (
            await db.execute(select(Recording).where(Recording.meeting_id == m.id))
        ).scalars().all()
        for r in recs:
            try:
                await storage.delete_object(r.storage_key)
            except Exception as e:
                logger.warning("retention_storage_delete_failed", error=str(e))
        try:
            qdrant.delete_meeting(str(m.id), str(organization_id))
        except Exception as e:
            logger.warning("retention_qdrant_delete_failed", error=str(e))
        await db.delete(m)
        purged += 1

    await db.commit()
    logger.info("retention_purge_done", org=str(organization_id), purged=purged)
    return {
        "ok": True,
        "dry_run": False,
        "purged": purged,
        "cutoff": cutoff.isoformat(),
        "retention_days": days,
    }


async def export_user_data(db: AsyncSession, organization_id: UUID, user_id: UUID) -> dict:
    from app.models.user import User
    from app.models.audit import AuditLog

    user = await db.get(User, user_id)
    meetings = (
        await db.execute(
            select(Meeting).where(
                Meeting.organization_id == organization_id,
                Meeting.owner_id == user_id,
            )
        )
    ).scalars().all()
    audits = (
        await db.execute(
            select(AuditLog)
            .where(
                AuditLog.organization_id == organization_id,
                AuditLog.actor_id == user_id,
            )
            .limit(500)
        )
    ).scalars().all()

    return {
        "user": {
            "id": str(user.id) if user else None,
            "email": user.email if user else None,
            "full_name": user.full_name if user else None,
            "role": user.role if user else None,
            "created_at": user.created_at.isoformat() if user and user.created_at else None,
        },
        "meetings": [
            {
                "id": str(m.id),
                "title": m.title,
                "status": m.status,
                "created_at": m.created_at.isoformat() if m.created_at else None,
                "executive_summary": m.executive_summary,
            }
            for m in meetings
        ],
        "audit_sample": [
            {
                "action": a.action,
                "created_at": a.created_at.isoformat() if a.created_at else None,
                "resource_type": a.resource_type,
            }
            for a in audits
        ],
        "exported_at": datetime.now(timezone.utc).isoformat(),
    }

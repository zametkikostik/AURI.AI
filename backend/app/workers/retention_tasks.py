"""Celery beat-friendly retention purge task."""

from __future__ import annotations

import asyncio
from typing import Any

from app.workers.celery_app import celery_app
from app.core.logging import get_logger

logger = get_logger(__name__)


def _run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(name="retention.purge_all_orgs")
def purge_all_orgs_task(dry_run: bool = False) -> dict[str, Any]:
    return _run(_purge_all(dry_run=dry_run))


async def _purge_all(dry_run: bool = False) -> dict[str, Any]:
    from sqlalchemy import select
    from app.core.database import AsyncSessionLocal
    from app.models.user import Organization
    from app.services.retention import purge_expired_meetings

    results = []
    async with AsyncSessionLocal() as session:
        orgs = (await session.execute(select(Organization.id))).scalars().all()
        for oid in orgs:
            try:
                r = await purge_expired_meetings(session, oid, dry_run=dry_run)
                results.append({"organization_id": str(oid), **r})
            except Exception as e:
                logger.error("retention_org_failed", org=str(oid), error=str(e))
                results.append({"organization_id": str(oid), "ok": False, "error": str(e)})
    return {"ok": True, "orgs": len(results), "results": results}

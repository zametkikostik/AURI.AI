"""Audit log API — admin only."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import RequireAdmin
from app.models.audit import AuditLog

router = APIRouter()


class AuditOut(BaseModel):
    id: UUID
    action: str
    actor_id: UUID | None
    resource_type: str | None
    resource_id: str | None
    ip_address: str | None
    meta: dict | None
    created_at: datetime

    model_config = {"from_attributes": True}


@router.get("")
async def list_audit_logs(
    db: Annotated[AsyncSession, Depends(get_db)],
    ctx: RequireAdmin,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    action: str | None = None,
):
    base = select(AuditLog).where(AuditLog.organization_id == ctx.org_id)
    if action:
        base = base.where(AuditLog.action == action)

    total = (await db.execute(select(func.count()).select_from(base.subquery()))).scalar() or 0
    q = base.order_by(AuditLog.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    rows = (await db.execute(q)).scalars().all()

    return {
        "items": [AuditOut.model_validate(r) for r in rows],
        "total": total,
        "page": page,
        "page_size": page_size,
    }

"""GDPR / retention endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.deps import RequireAdmin, CurrentUser
from app.models.settings import OrganizationSettings
from app.services.audit import write_audit
from app.services.retention import export_user_data, get_retention_days, purge_expired_meetings

router = APIRouter()


class RetentionUpdate(BaseModel):
    retention_days: int | None = Field(None, ge=1, le=3650)


@router.get("/retention")
async def get_retention(db: Annotated[AsyncSession, Depends(get_db)], ctx: RequireAdmin):
    days = await get_retention_days(db, ctx.org_id)
    return {"retention_days": days}


@router.put("/retention")
async def set_retention(
    body: RetentionUpdate,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    ctx: RequireAdmin,
):
    result = await db.execute(
        select(OrganizationSettings).where(OrganizationSettings.organization_id == ctx.org_id)
    )
    row = result.scalar_one_or_none()
    if not row:
        row = OrganizationSettings(organization_id=ctx.org_id)
        db.add(row)
        await db.flush()
    meta = dict(row.meta or {})
    if body.retention_days is None:
        meta.pop("retention_days", None)
    else:
        meta["retention_days"] = body.retention_days
    row.meta = meta
    await write_audit(
        db,
        organization_id=ctx.org_id,
        actor_id=ctx.user_id,
        action="gdpr.retention_update",
        resource_type="organization_settings",
        ip_address=request.client.host if request.client else None,
        meta={"retention_days": body.retention_days},
    )
    await db.commit()
    return {"ok": True, "retention_days": body.retention_days}


@router.post("/retention/purge")
async def run_purge(
    db: Annotated[AsyncSession, Depends(get_db)],
    ctx: RequireAdmin,
    dry_run: bool = Query(True),
):
    return await purge_expired_meetings(db, ctx.org_id, dry_run=dry_run)


@router.get("/export/me")
async def export_my_data(db: Annotated[AsyncSession, Depends(get_db)], ctx: CurrentUser):
    return await export_user_data(db, ctx.org_id, ctx.user_id)


@router.delete("/me")
async def delete_my_account(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    ctx: CurrentUser,
):
    if ctx.role == "admin":
        from app.models.user import User
        from sqlalchemy import func

        admins = (
            await db.execute(
                select(func.count())
                .select_from(User)
                .where(
                    User.organization_id == ctx.org_id,
                    User.role == "admin",
                    User.is_active.is_(True),
                )
            )
        ).scalar() or 0
        if admins <= 1:
            raise HTTPException(
                status_code=400,
                detail="Cannot delete the only admin. Transfer admin role first.",
            )

    ctx.user.is_active = False
    ctx.user.email = f"deleted+{ctx.user.id}@invalid.local"
    ctx.user.hashed_password = None
    ctx.user.full_name = "Deleted User"
    await write_audit(
        db,
        organization_id=ctx.org_id,
        actor_id=ctx.user_id,
        action="gdpr.account_deactivate",
        resource_type="user",
        resource_id=ctx.user_id,
        ip_address=request.client.host if request.client else None,
    )
    await db.commit()
    return {"ok": True, "message": "Account deactivated"}

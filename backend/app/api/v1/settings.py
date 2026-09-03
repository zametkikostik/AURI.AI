"""Organization settings API."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import RequireAdmin, RequireViewer
from app.models.settings import OrganizationSettings
from app.schemas.settings import OrgSettingsOut, OrgSettingsUpdate
from app.services.audit import write_audit
from app.core.crypto import encrypt_secret

router = APIRouter()


def _mask(url: str | None) -> str | None:
    if not url:
        return None
    if len(url) < 12:
        return "***"
    return url[:8] + "…" + url[-4:]


def _to_out(row: OrganizationSettings) -> OrgSettingsOut:
    return OrgSettingsOut(
        id=row.id,
        organization_id=row.organization_id,
        ai_mode=row.ai_mode,
        slack_webhook_configured=bool(row.slack_webhook_url),
        notion_configured=bool(row.notion_token and row.notion_database_id),
        zapier_configured=bool(row.zapier_webhook_url),
        notify_on_ready=row.notify_on_ready,
        notify_slack=row.notify_slack,
        notify_notion=row.notify_notion,
        slack_webhook_hint=_mask(row.slack_webhook_url),
        updated_at=row.updated_at,
    )


async def _get_or_create(db: AsyncSession, org_id) -> OrganizationSettings:
    result = await db.execute(
        select(OrganizationSettings).where(OrganizationSettings.organization_id == org_id)
    )
    row = result.scalar_one_or_none()
    if row:
        return row
    row = OrganizationSettings(organization_id=org_id)
    db.add(row)
    await db.flush()
    return row


@router.get("/organization", response_model=OrgSettingsOut)
async def get_org_settings(db: Annotated[AsyncSession, Depends(get_db)], ctx: RequireViewer):
    row = await _get_or_create(db, ctx.org_id)
    await db.commit()
    return _to_out(row)


@router.patch("/organization", response_model=OrgSettingsOut)
async def update_org_settings(
    body: OrgSettingsUpdate,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    ctx: RequireAdmin,
):
    row = await _get_or_create(db, ctx.org_id)
    data = body.model_dump(exclude_unset=True)
    secret_fields = {"slack_webhook_url", "notion_token", "zapier_webhook_url"}
    for k, v in data.items():
        if k in secret_fields and isinstance(v, str):
            v = encrypt_secret(v)
        setattr(row, k, v)

    await write_audit(
        db,
        organization_id=ctx.org_id,
        actor_id=ctx.user_id,
        action="settings.update",
        resource_type="organization_settings",
        resource_id=row.id,
        ip_address=request.client.host if request.client else None,
        meta={"fields": list(data.keys())},
    )
    await db.commit()
    await db.refresh(row)
    return _to_out(row)

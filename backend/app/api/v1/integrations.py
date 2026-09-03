"""Integration endpoints: Slack, Notion, generic webhook."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import RequireEditor
from app.models.meeting import Meeting
from app.services.audit import write_audit
from app.services.notifications import export_to_notion, notify_slack, send_generic_webhook

router = APIRouter()


class SlackNotifyBody(BaseModel):
    meeting_id: UUID
    webhook_url: str = Field(..., min_length=10)


class NotionExportBody(BaseModel):
    meeting_id: UUID
    token: str = Field(..., min_length=10)
    database_id: str = Field(..., min_length=10)


class GenericWebhookBody(BaseModel):
    meeting_id: UUID
    url: str = Field(..., min_length=10)


async def _get_meeting(db: AsyncSession, meeting_id: UUID, org_id: UUID) -> Meeting:
    result = await db.execute(
        select(Meeting).where(Meeting.id == meeting_id, Meeting.organization_id == org_id)
    )
    meeting = result.scalar_one_or_none()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    return meeting


@router.post("/slack/notify")
async def slack_notify(
    body: SlackNotifyBody,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    ctx: RequireEditor,
):
    meeting = await _get_meeting(db, body.meeting_id, ctx.org_id)
    result = await notify_slack(
        body.webhook_url,
        title=meeting.title,
        summary=meeting.executive_summary,
        meeting_id=str(meeting.id),
        action_items=meeting.action_items,
    )
    await write_audit(
        db,
        organization_id=ctx.org_id,
        actor_id=ctx.user_id,
        action="integration.slack_notify",
        resource_type="meeting",
        resource_id=meeting.id,
        ip_address=request.client.host if request.client else None,
        meta={"ok": result.get("ok")},
    )
    await db.commit()
    return result


@router.post("/notion/export")
async def notion_export(
    body: NotionExportBody,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    ctx: RequireEditor,
):
    meeting = await _get_meeting(db, body.meeting_id, ctx.org_id)
    result = await export_to_notion(
        body.token,
        body.database_id,
        title=meeting.title,
        summary=meeting.executive_summary,
        topics=meeting.topics,
        meeting_id=str(meeting.id),
    )
    await write_audit(
        db,
        organization_id=ctx.org_id,
        actor_id=ctx.user_id,
        action="integration.notion_export",
        resource_type="meeting",
        resource_id=meeting.id,
        ip_address=request.client.host if request.client else None,
        meta={"ok": result.get("ok")},
    )
    await db.commit()
    return result


@router.post("/webhook/send")
async def generic_webhook(
    body: GenericWebhookBody,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    ctx: RequireEditor,
):
    meeting = await _get_meeting(db, body.meeting_id, ctx.org_id)
    payload = {
        "event": "meeting.ready",
        "meeting_id": str(meeting.id),
        "title": meeting.title,
        "status": meeting.status,
        "executive_summary": meeting.executive_summary,
        "topics": meeting.topics,
        "action_items": meeting.action_items,
    }
    result = await send_generic_webhook(body.url, payload)
    await write_audit(
        db,
        organization_id=ctx.org_id,
        actor_id=ctx.user_id,
        action="integration.webhook_send",
        resource_type="meeting",
        resource_id=meeting.id,
        ip_address=request.client.host if request.client else None,
        meta={"ok": result.get("ok")},
    )
    await db.commit()
    return result

"""Calendar integration stubs — Google Calendar / Outlook."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.core.deps import RequireEditor, RequireViewer
from app.core.logging import get_logger

router = APIRouter()
logger = get_logger(__name__)


class CalendarEventIn(BaseModel):
    title: str
    start: datetime
    end: datetime
    meeting_url: str | None = None
    attendees: list[str] = Field(default_factory=list)
    external_id: str | None = None
    source: str = "manual"


class CalendarSyncRequest(BaseModel):
    provider: str = Field(..., pattern="^(google|outlook)$")
    access_token: str | None = None


@router.get("/events")
async def list_upcoming(ctx: RequireViewer) -> dict[str, Any]:
    return {
        "events": [],
        "message": "Connect Google/Outlook OAuth to sync calendar events.",
    }


@router.post("/sync")
async def sync_calendar(body: CalendarSyncRequest, ctx: RequireEditor) -> dict[str, Any]:
    logger.info("calendar_sync_requested", provider=body.provider, org=str(ctx.org_id))
    return {
        "ok": False,
        "provider": body.provider,
        "message": f"{body.provider} calendar sync not fully configured.",
    }


@router.post("/events")
async def create_event_from_calendar(
    body: CalendarEventIn, ctx: RequireEditor
) -> dict[str, Any]:
    return {
        "ok": True,
        "planned": {
            "title": body.title,
            "start": body.start.isoformat(),
            "end": body.end.isoformat(),
            "meeting_url": body.meeting_url,
            "bot_join": bool(body.meeting_url),
            "source": body.source,
        },
        "message": "Event accepted (stub). Wire to Meeting.create + bots.join.",
    }

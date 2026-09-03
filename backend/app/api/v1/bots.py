"""Bot join API stubs."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import RequireEditor
from app.services.bots import BotJoinRequest, BotPlatform, get_bot
from app.services.audit import write_audit

router = APIRouter()


class JoinBotBody(BaseModel):
    platform: BotPlatform
    meeting_url: str = Field(..., min_length=8, max_length=1000)
    title: str | None = None
    external_id: str | None = None


@router.post("/join")
async def join_meeting_bot(
    body: JoinBotBody,
    db: Annotated[AsyncSession, Depends(get_db)],
    ctx: RequireEditor,
):
    bot = get_bot(body.platform)
    result = await bot.join(
        BotJoinRequest(
            meeting_url=body.meeting_url,
            external_id=body.external_id,
            title=body.title,
            organization_id=str(ctx.org_id),
        )
    )
    await write_audit(
        db,
        organization_id=ctx.org_id,
        actor_id=ctx.user_id,
        action="bot.join_request",
        resource_type="bot",
        meta={
            "platform": body.platform.value,
            "success": result.success,
            "message": result.message,
        },
    )
    await db.commit()
    return {
        "success": result.success,
        "platform": result.platform.value,
        "bot_session_id": result.bot_session_id,
        "message": result.message,
    }

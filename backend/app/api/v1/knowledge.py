"""Knowledge Hub API."""

from __future__ import annotations

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import RequireViewer
from app.models.meeting import Meeting

router = APIRouter()


@router.get("/meetings/{meeting_id}")
async def get_meeting_knowledge(
    meeting_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    ctx: RequireViewer,
) -> dict[str, Any]:
    result = await db.execute(
        select(Meeting).where(
            Meeting.id == meeting_id,
            Meeting.organization_id == ctx.org_id,
        )
    )
    meeting = result.scalar_one_or_none()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    knowledge = (meeting.meta or {}).get("knowledge", {})
    return {
        "meeting_id": str(meeting.id),
        "title": meeting.title,
        "topics": meeting.topics or knowledge.get("topics"),
        "action_items": meeting.action_items or knowledge.get("action_items"),
        "executive_summary": meeting.executive_summary,
        "knowledge": knowledge,
    }


@router.get("/topics")
async def list_org_topics(
    db: Annotated[AsyncSession, Depends(get_db)],
    ctx: RequireViewer,
    limit: int = Query(50, ge=1, le=200),
) -> dict[str, Any]:
    result = await db.execute(
        select(Meeting.topics, Meeting.title, Meeting.id)
        .where(Meeting.organization_id == ctx.org_id, Meeting.topics.isnot(None))
        .order_by(Meeting.created_at.desc())
        .limit(100)
    )
    rows = result.all()
    freq: dict[str, int] = {}
    examples: dict[str, list[str]] = {}
    for topics, title, mid in rows:
        if not topics:
            continue
        for t in topics:
            key = str(t).strip()
            if not key:
                continue
            freq[key] = freq.get(key, 0) + 1
            examples.setdefault(key, [])
            if len(examples[key]) < 3:
                examples[key].append(title)

    ranked = sorted(freq.items(), key=lambda x: x[1], reverse=True)[:limit]
    return {
        "topics": [
            {"name": name, "count": count, "example_meetings": examples.get(name, [])}
            for name, count in ranked
        ]
    }

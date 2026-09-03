"""Export meeting artifacts (JSON / Markdown / TXT)."""

from __future__ import annotations

from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import RequireViewer
from app.services.audit import write_audit
from app.services.export import export_json, export_markdown, export_txt, load_meeting_for_export

router = APIRouter()

Format = Literal["json", "md", "txt"]


@router.get("/meetings/{meeting_id}")
async def export_meeting(
    meeting_id: UUID,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    ctx: RequireViewer,
    format: Format = "json",
):
    meeting = await load_meeting_for_export(db, meeting_id, ctx.org_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    if format == "json":
        body, media, ext = export_json(meeting), "application/json", "json"
    elif format == "md":
        body, media, ext = export_markdown(meeting), "text/markdown; charset=utf-8", "md"
    else:
        body, media, ext = export_txt(meeting), "text/plain; charset=utf-8", "txt"

    safe_title = "".join(c if c.isalnum() or c in "-_ " else "_" for c in meeting.title)[:60]
    filename = f"{safe_title or 'meeting'}.{ext}"

    await write_audit(
        db,
        organization_id=ctx.org_id,
        actor_id=ctx.user_id,
        action="meeting.export",
        resource_type="meeting",
        resource_id=meeting_id,
        ip_address=request.client.host if request.client else None,
        meta={"format": format},
    )
    await db.commit()

    return Response(
        content=body,
        media_type=media,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )

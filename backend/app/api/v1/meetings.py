"""Meetings API endpoints — authenticated + RBAC."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import RequireEditor, RequireViewer
from app.schemas.meeting import (
    MeetingCreate,
    MeetingDetailOut,
    MeetingListOut,
    MeetingOut,
    MeetingUpdate,
    RecordingOut,
)
from app.services.audit import write_audit
from app.services.meeting import MeetingService
from app.services.billing import LimitExceeded

router = APIRouter()


@router.post("", response_model=MeetingOut, status_code=status.HTTP_201_CREATED)
async def create_meeting(
    body: MeetingCreate,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    ctx: RequireEditor,
):
    service = MeetingService(db)
    try:
        meeting = await service.create_meeting(
            body, organization_id=ctx.org_id, owner_id=ctx.user_id
        )
    except LimitExceeded as e:
        raise HTTPException(status_code=402, detail=e.message)
    await write_audit(
        db,
        organization_id=ctx.org_id,
        actor_id=ctx.user_id,
        action="meeting.create",
        resource_type="meeting",
        resource_id=meeting.id,
        ip_address=request.client.host if request.client else None,
        meta={"title": meeting.title},
    )
    await db.commit()
    return meeting


@router.get("", response_model=MeetingListOut)
async def list_meetings(
    db: Annotated[AsyncSession, Depends(get_db)],
    ctx: RequireViewer,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status_filter: str | None = Query(None, alias="status"),
):
    service = MeetingService(db)
    items, total = await service.list_meetings(
        organization_id=ctx.org_id,
        page=page,
        page_size=page_size,
        status=status_filter,
    )
    return MeetingListOut(items=items, total=total, page=page, page_size=page_size)


@router.get("/{meeting_id}", response_model=MeetingDetailOut)
async def get_meeting(
    meeting_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    ctx: RequireViewer,
):
    service = MeetingService(db)
    meeting = await service.get_meeting(meeting_id, ctx.org_id, with_details=True)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    return meeting


@router.patch("/{meeting_id}", response_model=MeetingOut)
async def update_meeting(
    meeting_id: uuid.UUID,
    body: MeetingUpdate,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    ctx: RequireEditor,
):
    service = MeetingService(db)
    meeting = await service.get_meeting(meeting_id, ctx.org_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    updated = await service.update_meeting(meeting, body)
    await write_audit(
        db,
        organization_id=ctx.org_id,
        actor_id=ctx.user_id,
        action="meeting.update",
        resource_type="meeting",
        resource_id=meeting_id,
        ip_address=request.client.host if request.client else None,
    )
    await db.commit()
    return updated


@router.post(
    "/{meeting_id}/recordings",
    response_model=RecordingOut,
    status_code=status.HTTP_201_CREATED,
)
async def upload_recording(
    meeting_id: uuid.UUID,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    ctx: RequireEditor,
    file: UploadFile = File(...),
):
    service = MeetingService(db)
    meeting = await service.get_meeting(meeting_id, ctx.org_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    allowed = {
        "audio/mpeg", "audio/mp3", "audio/wav", "audio/x-wav",
        "audio/webm", "audio/ogg", "audio/mp4", "video/mp4",
        "video/webm", "application/octet-stream",
    }
    content_type = file.content_type or "application/octet-stream"
    if content_type not in allowed:
        raise HTTPException(status_code=400, detail=f"Unsupported content type: {content_type}")

    recording = await service.upload_recording(
        meeting=meeting,
        file_obj=file.file,
        filename=file.filename or "recording.mp3",
        content_type=content_type,
    )
    await write_audit(
        db,
        organization_id=ctx.org_id,
        actor_id=ctx.user_id,
        action="recording.upload",
        resource_type="recording",
        resource_id=recording.id,
        ip_address=request.client.host if request.client else None,
        meta={"meeting_id": str(meeting_id), "filename": file.filename},
    )
    await db.commit()
    return recording


@router.get("/{meeting_id}/recordings/{recording_id}/url")
async def get_recording_url(
    meeting_id: uuid.UUID,
    recording_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    ctx: RequireViewer,
):
    from sqlalchemy import select
    from app.models.meeting import Recording
    from app.services.storage import get_storage_service

    service = MeetingService(db)
    meeting = await service.get_meeting(meeting_id, ctx.org_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    result = await db.execute(
        select(Recording).where(
            Recording.id == recording_id,
            Recording.meeting_id == meeting_id,
        )
    )
    recording = result.scalar_one_or_none()
    if not recording:
        raise HTTPException(status_code=404, detail="Recording not found")

    storage = get_storage_service()
    url = await storage.generate_presigned_url(recording.storage_key, expires_in=3600)
    return {"url": url, "expires_in": 3600, "content_type": recording.content_type}

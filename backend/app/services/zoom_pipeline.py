"""Zoom recording.completed → Meeting + Recording + Celery pipeline."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.meeting import Meeting, MeetingStatus, Recording, TranscriptionStatus
from app.models.user import User
from app.services.storage import get_storage_service
from app.workers.tasks import process_recording_task

logger = get_logger(__name__)


async def handle_zoom_recording_completed(
    db: AsyncSession,
    *,
    organization_id: uuid.UUID,
    owner_id: uuid.UUID,
    payload: dict[str, Any],
) -> dict[str, Any]:
    obj = (payload.get("payload") or {}).get("object") or payload.get("object") or payload
    topic = obj.get("topic") or obj.get("topic_name") or "Zoom Meeting"
    external_id = obj.get("uuid") or obj.get("id") or str(uuid.uuid4())
    files = obj.get("recording_files") or []

    download_url = None
    content_type = "audio/mpeg"
    for f in files:
        ftype = (f.get("file_type") or "").upper()
        if ftype in ("M4A", "MP3", "WAV"):
            download_url = f.get("download_url")
            content_type = "audio/mp4" if ftype == "M4A" else f"audio/{ftype.lower()}"
            break
    if not download_url:
        for f in files:
            if (f.get("file_type") or "").upper() == "MP4":
                download_url = f.get("download_url")
                content_type = "video/mp4"
                break

    meeting = Meeting(
        title=topic,
        organization_id=organization_id,
        owner_id=owner_id,
        source="zoom",
        external_id=str(external_id),
        status=MeetingStatus.PROCESSING.value,
        language="en",
        started_at=_parse_dt(obj.get("start_time")),
        duration_seconds=int(obj.get("duration") or 0) * 60 or None,
    )
    db.add(meeting)
    await db.flush()

    if not download_url:
        meeting.status = MeetingStatus.FAILED.value
        await db.commit()
        return {"ok": False, "meeting_id": str(meeting.id), "error": "No downloadable recording file in payload"}

    try:
        async with httpx.AsyncClient(timeout=120.0, follow_redirects=True) as client:
            resp = await client.get(download_url)
            resp.raise_for_status()
            audio_bytes = resp.content
    except Exception as e:
        logger.error("zoom_download_failed", error=str(e))
        meeting.status = MeetingStatus.FAILED.value
        await db.commit()
        return {"ok": False, "meeting_id": str(meeting.id), "error": str(e)}

    storage = get_storage_service()
    try:
        await storage.ensure_bucket()
    except Exception:
        pass

    key = storage.build_key(
        organization_id=organization_id,
        meeting_id=meeting.id,
        filename=f"zoom_{external_id}.mp4",
    )
    info = await storage.upload_file(
        file_obj=audio_bytes,
        key=key,
        content_type=content_type,
        metadata={"source": "zoom", "external_id": str(external_id)},
    )

    recording = Recording(
        meeting_id=meeting.id,
        storage_key=info["key"],
        storage_bucket=info["bucket"],
        content_type=info["content_type"],
        file_size_bytes=info["size"],
        original_filename=f"zoom_{external_id}",
        checksum=info["checksum"],
        status=TranscriptionStatus.PENDING.value,
    )
    db.add(recording)
    await db.commit()
    await db.refresh(recording)

    process_recording_task.delay(str(recording.id), str(meeting.id))
    return {
        "ok": True,
        "meeting_id": str(meeting.id),
        "recording_id": str(recording.id),
        "title": topic,
    }


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception:
        return None


async def resolve_default_org_owner(db: AsyncSession, organization_id: uuid.UUID):
    result = await db.execute(
        select(User.id)
        .where(User.organization_id == organization_id, User.is_active.is_(True))
        .order_by(User.created_at.asc())
        .limit(1)
    )
    return result.scalar_one_or_none()

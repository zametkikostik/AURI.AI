"""Meeting business logic."""

from __future__ import annotations

import uuid
from typing import BinaryIO

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.logging import get_logger
from app.models.meeting import (
    Meeting,
    MeetingStatus,
    Recording,
    TranscriptionStatus,
)
from app.schemas.meeting import MeetingCreate, MeetingUpdate
from app.services.storage import get_storage_service
from app.workers.tasks import process_recording_task
from app.services.billing import LimitExceeded, assert_can_create_meeting, assert_can_upload_hours

logger = get_logger(__name__)


class MeetingService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.storage = get_storage_service()

    async def create_meeting(
        self,
        data: MeetingCreate,
        organization_id: uuid.UUID,
        owner_id: uuid.UUID,
    ) -> Meeting:
        await assert_can_create_meeting(self.db, organization_id)
        meeting = Meeting(
            title=data.title,
            description=data.description,
            organization_id=organization_id,
            workspace_id=data.workspace_id,
            owner_id=owner_id,
            language=data.language,
            is_private=data.is_private,
            scheduled_at=data.scheduled_at,
            source=data.source,
            meeting_url=data.meeting_url,
            status=MeetingStatus.SCHEDULED.value,
        )
        self.db.add(meeting)
        await self.db.commit()
        await self.db.refresh(meeting)
        logger.info("meeting_created", meeting_id=str(meeting.id), title=meeting.title)
        return meeting

    async def get_meeting(
        self,
        meeting_id: uuid.UUID,
        organization_id: uuid.UUID,
        with_details: bool = False,
    ) -> Meeting | None:
        q = select(Meeting).where(
            Meeting.id == meeting_id,
            Meeting.organization_id == organization_id,
        )
        if with_details:
            q = q.options(
                selectinload(Meeting.recordings),
                selectinload(Meeting.transcript),
            )
        result = await self.db.execute(q)
        return result.scalar_one_or_none()

    async def list_meetings(
        self,
        organization_id: uuid.UUID,
        page: int = 1,
        page_size: int = 20,
        status: str | None = None,
    ) -> tuple[list[Meeting], int]:
        base = select(Meeting).where(Meeting.organization_id == organization_id)
        if status:
            base = base.where(Meeting.status == status)

        count_q = select(func.count()).select_from(base.subquery())
        total = (await self.db.execute(count_q)).scalar() or 0

        q = (
            base.order_by(Meeting.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self.db.execute(q)
        items = list(result.scalars().all())
        return items, total

    async def update_meeting(self, meeting: Meeting, data: MeetingUpdate) -> Meeting:
        payload = data.model_dump(exclude_unset=True)
        for k, v in payload.items():
            setattr(meeting, k, v)
        await self.db.commit()
        await self.db.refresh(meeting)
        return meeting

    async def upload_recording(
        self,
        meeting: Meeting,
        file_obj: BinaryIO,
        filename: str,
        content_type: str = "audio/mpeg",
    ) -> Recording:
        try:
            await assert_can_upload_hours(self.db, meeting.organization_id)
        except LimitExceeded:
            raise
        key = self.storage.build_key(
            organization_id=meeting.organization_id,
            meeting_id=meeting.id,
            filename=filename,
        )

        try:
            await self.storage.ensure_bucket()
        except Exception as e:
            logger.warning("ensure_bucket_failed", error=str(e))

        info = await self.storage.upload_file(
            file_obj=file_obj,
            key=key,
            content_type=content_type,
            metadata={
                "meeting_id": str(meeting.id),
                "organization_id": str(meeting.organization_id),
            },
        )

        recording = Recording(
            meeting_id=meeting.id,
            storage_key=info["key"],
            storage_bucket=info["bucket"],
            content_type=info["content_type"],
            file_size_bytes=info["size"],
            original_filename=filename,
            checksum=info["checksum"],
            status=TranscriptionStatus.PENDING.value,
        )
        self.db.add(recording)

        meeting.status = MeetingStatus.PROCESSING.value
        await self.db.commit()
        await self.db.refresh(recording)

        process_recording_task.delay(str(recording.id), str(meeting.id))
        logger.info(
            "recording_uploaded_and_enqueued",
            recording_id=str(recording.id),
            meeting_id=str(meeting.id),
            size=info["size"],
        )
        return recording

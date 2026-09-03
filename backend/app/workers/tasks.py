"""Celery tasks for the meeting processing pipeline."""

from __future__ import annotations

import asyncio
import time
import uuid
from typing import Any

from app.workers.celery_app import celery_app
from app.core.logging import get_logger

logger = get_logger(__name__)


def _run_async(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(bind=True, name="meetings.process_recording", max_retries=3)
def process_recording_task(self, recording_id: str, meeting_id: str) -> dict[str, Any]:
    """Download → transcribe → summarize → knowledge → embed → Qdrant."""
    logger.info(
        "process_recording_started",
        recording_id=recording_id,
        meeting_id=meeting_id,
        task_id=self.request.id,
    )
    try:
        result = _run_async(_process_recording_async(recording_id, meeting_id))
        logger.info("process_recording_finished", recording_id=recording_id)
        return result
    except Exception as exc:
        logger.error(
            "process_recording_failed",
            recording_id=recording_id,
            error=str(exc),
            attempt=self.request.retries,
        )
        raise self.retry(exc=exc, countdown=30 * (self.request.retries + 1))


async def _process_recording_async(recording_id: str, meeting_id: str) -> dict[str, Any]:
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    from app.core.database import AsyncSessionLocal
    from app.models.meeting import (
        Meeting,
        MeetingStatus,
        Recording,
        Transcript,
        TranscriptionStatus,
    )
    from app.services.storage import get_storage_service
    from app.ai.transcription import get_transcription_provider
    from app.ai.router import get_ai_router
    from app.services.chunking import chunk_transcript
    from app.services.qdrant import get_qdrant_service
    from app.services.knowledge import extract_knowledge

    started = time.time()
    storage = get_storage_service()

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Recording)
            .where(Recording.id == uuid.UUID(recording_id))
            .options(selectinload(Recording.meeting))
        )
        recording = result.scalar_one_or_none()
        if not recording:
            raise ValueError(f"Recording {recording_id} not found")

        meeting = recording.meeting
        if not meeting:
            raise ValueError(f"Meeting for recording {recording_id} not found")

        recording.status = TranscriptionStatus.PROCESSING.value
        meeting.status = MeetingStatus.PROCESSING.value
        await session.commit()

        try:
            # 1. Download audio
            audio_bytes = await storage.download_bytes(recording.storage_key)

            # 2. Transcribe
            stt = await get_transcription_provider()
            transcription = await stt.transcribe(
                audio_bytes=audio_bytes,
                language=meeting.language,
                diarize=True,
            )

            segments_payload = transcription.words or []
            speakers_payload = transcription.speakers or []

            # 3. Save transcript
            existing = await session.execute(
                select(Transcript).where(Transcript.meeting_id == meeting.id)
            )
            transcript_row = existing.scalar_one_or_none()
            if transcript_row:
                transcript_row.full_text = transcription.text
                transcript_row.segments = segments_payload
                transcript_row.speakers = speakers_payload
                transcript_row.language = transcription.language
                transcript_row.provider = transcription.provider
                transcript_row.status = TranscriptionStatus.COMPLETED.value
            else:
                transcript_row = Transcript(
                    meeting_id=meeting.id,
                    full_text=transcription.text,
                    segments=segments_payload,
                    speakers=speakers_payload,
                    language=transcription.language,
                    provider=transcription.provider,
                    status=TranscriptionStatus.COMPLETED.value,
                )
                session.add(transcript_row)

            if transcription.duration_seconds:
                recording.duration_seconds = transcription.duration_seconds
                meeting.duration_seconds = int(transcription.duration_seconds)

            recording.status = TranscriptionStatus.COMPLETED.value

            # 4. Summarize via Ollama
            summary_data = None
            try:
                ai_router = get_ai_router()
                llm = await ai_router.get_llm()
                summary = await llm.summarize_meeting(
                    transcript=transcription.text,
                    meeting_title=meeting.title,
                    language=meeting.language or "en",
                )
                meeting.executive_summary = summary.executive_summary
                meeting.topics = summary.topics
                meeting.action_items = summary.action_items
                summary_data = {
                    "executive_summary": summary.executive_summary,
                    "topics": summary.topics,
                    "action_items": summary.action_items,
                    "provider": summary.provider,
                    "model": summary.model,
                }
            except Exception as e:
                logger.warning("summary_generation_skipped", error=str(e))

# 5. Knowledge extraction
            knowledge_data = None
            try:
                knowledge_data = await extract_knowledge(
                    transcript=transcription.text,
                    meeting_title=meeting.title,
                )
                if knowledge_data.get("topics") and not meeting.topics:
                    meeting.topics = knowledge_data["topics"]
                if knowledge_data.get("action_items") and not meeting.action_items:
                    meeting.action_items = knowledge_data["action_items"]
                meta = dict(meeting.meta or {})
                meta["knowledge"] = knowledge_data
                meeting.meta = meta
            except Exception as e:
                logger.warning("knowledge_extraction_skipped", error=str(e))

            # 6. Chunk + embed → Qdrant
            embedded_count = 0
            try:
                chunks = chunk_transcript(
                    full_text=transcription.text,
                    segments=segments_payload,
                )
                if chunks:
                    ai_router = get_ai_router()
                    emb_provider = await ai_router.get_embedding()
                    texts = [c["text"] for c in chunks]
                    embeddings = await emb_provider.embed(texts)

                    points = []
                    for chunk, emb in zip(chunks, embeddings):
                        points.append(
                            {
                                "id": chunk["id"],
                                "vector": emb.embedding,
                                "payload": {
                                    "organization_id": str(meeting.organization_id),
                                    "meeting_id": str(meeting.id),
                                    "text": chunk["text"],
                                    "chunk_index": chunk["chunk_index"],
                                    "start": chunk.get("start"),
                                    "end": chunk.get("end"),
                                    "speaker": chunk.get("speaker"),
                                    "chunk_type": chunk.get("chunk_type", "transcript"),
                                    "title": meeting.title,
                                },
                            }
                        )

                    qdrant = get_qdrant_service()
                    qdrant.delete_meeting(str(meeting.id), str(meeting.organization_id))
                    embedded_count = qdrant.upsert_chunks(points)
            except Exception as e:
                logger.warning("embedding_pipeline_skipped", error=str(e))

            meeting.status = MeetingStatus.READY.value
            await session.commit()

            # 7. Optional integrations notify
            try:
                from sqlalchemy import select as sa_select
                from app.models.settings import OrganizationSettings
                from app.core.crypto import decrypt_secret
                from app.services.notifications import notify_slack, export_to_notion

                srow = (
                    await session.execute(
                        sa_select(OrganizationSettings).where(
                            OrganizationSettings.organization_id == meeting.organization_id
                        )
                    )
                ).scalar_one_or_none()
                if srow and srow.notify_on_ready:
                    if srow.notify_slack and srow.slack_webhook_url:
                        await notify_slack(
                            decrypt_secret(srow.slack_webhook_url) or "",
                            title=meeting.title,
                            summary=meeting.executive_summary,
                            meeting_id=str(meeting.id),
                            action_items=meeting.action_items,
                        )
                    if srow.notify_notion and srow.notion_token and srow.notion_database_id:
                        await export_to_notion(
                            decrypt_secret(srow.notion_token) or "",
                            srow.notion_database_id,
                            title=meeting.title,
                            summary=meeting.executive_summary,
                            topics=meeting.topics,
                            meeting_id=str(meeting.id),
                        )
            except Exception as e:
                logger.warning("integration_notify_skipped", error=str(e))

            return {
                "status": "ok",
                "recording_id": recording_id,
                "meeting_id": meeting_id,
                "provider": transcription.provider,
                "language": transcription.language,
                "duration_seconds": transcription.duration_seconds,
                "processing_time_seconds": round(time.time() - started, 2),
                "summary": summary_data,
                "knowledge": knowledge_data,
                "embedded_chunks": embedded_count,
            }

        except Exception as e:
            recording.status = TranscriptionStatus.FAILED.value
            recording.error_message = str(e)[:2000]
            meeting.status = MeetingStatus.FAILED.value
            await session.commit()
            raise

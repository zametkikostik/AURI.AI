"""Semantic + keyword search over meetings."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.router import get_ai_router
from app.core.logging import get_logger
from app.models.meeting import Meeting, Transcript
from app.services.qdrant import get_qdrant_service

logger = get_logger(__name__)


class SearchService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.qdrant = get_qdrant_service()

    async def semantic_search(
        self,
        query: str,
        organization_id: uuid.UUID,
        limit: int = 10,
        meeting_id: uuid.UUID | None = None,
    ) -> list[dict[str, Any]]:
        router = get_ai_router()
        emb_provider = await router.get_embedding()
        emb = await emb_provider.embed_query(query)

        hits = self.qdrant.search(
            query_vector=emb.embedding,
            organization_id=str(organization_id),
            limit=limit,
            meeting_id=str(meeting_id) if meeting_id else None,
            score_threshold=0.25,
        )

        meeting_ids = list(
            {h["payload"].get("meeting_id") for h in hits if h["payload"].get("meeting_id")}
        )
        titles: dict[str, str] = {}
        if meeting_ids:
            uuids = []
            for mid in meeting_ids:
                try:
                    uuids.append(uuid.UUID(mid))
                except ValueError:
                    continue
            if uuids:
                result = await self.db.execute(
                    select(Meeting.id, Meeting.title).where(
                        Meeting.id.in_(uuids),
                        Meeting.organization_id == organization_id,
                    )
                )
                for mid, title in result.all():
                    titles[str(mid)] = title

        enriched = []
        for h in hits:
            payload = h["payload"]
            mid = payload.get("meeting_id")
            enriched.append(
                {
                    "score": h["score"],
                    "meeting_id": mid,
                    "meeting_title": titles.get(mid),
                    "text": payload.get("text"),
                    "chunk_index": payload.get("chunk_index"),
                    "start": payload.get("start"),
                    "end": payload.get("end"),
                    "speaker": payload.get("speaker"),
                    "chunk_type": payload.get("chunk_type"),
                }
            )
        return enriched

    async def keyword_search(
        self,
        query: str,
        organization_id: uuid.UUID,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        pattern = f"%{query}%"
        q = (
            select(Meeting, Transcript)
            .outerjoin(Transcript, Transcript.meeting_id == Meeting.id)
            .where(
                Meeting.organization_id == organization_id,
                or_(
                    Meeting.title.ilike(pattern),
                    Meeting.executive_summary.ilike(pattern),
                    Transcript.full_text.ilike(pattern),
                ),
            )
            .limit(limit)
        )
        result = await self.db.execute(q)
        rows = result.all()

        items = []
        for meeting, transcript in rows:
            snippet = None
            if transcript and transcript.full_text:
                idx = transcript.full_text.lower().find(query.lower())
                if idx >= 0:
                    start = max(0, idx - 80)
                    end = min(len(transcript.full_text), idx + 120)
                    snippet = transcript.full_text[start:end]
            items.append(
                {
                    "meeting_id": str(meeting.id),
                    "meeting_title": meeting.title,
                    "status": meeting.status,
                    "executive_summary": meeting.executive_summary,
                    "snippet": snippet,
                    "topics": meeting.topics,
                }
            )
        return items

    async def hybrid_search(
        self,
        query: str,
        organization_id: uuid.UUID,
        limit: int = 10,
    ) -> dict[str, Any]:
        semantic = await self.semantic_search(query, organization_id, limit=limit)
        keyword = await self.keyword_search(query, organization_id, limit=limit)
        return {"query": query, "semantic": semantic, "keyword": keyword}

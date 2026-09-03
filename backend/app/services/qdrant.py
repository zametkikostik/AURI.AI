"""Qdrant vector store service — hybrid search with org isolation."""

from __future__ import annotations

from typing import Any

from qdrant_client import QdrantClient, models
from qdrant_client.http.exceptions import UnexpectedResponse

from app.core.config import get_settings
from app.core.logging import get_logger

settings = get_settings()
logger = get_logger(__name__)

COLLECTION = settings.qdrant_collection
VECTOR_SIZE = 768


class QdrantService:
    def __init__(self) -> None:
        self.client = QdrantClient(
            host=settings.qdrant_host,
            port=settings.qdrant_port,
            api_key=settings.qdrant_api_key or None,
            prefer_grpc=False,
        )

    def ensure_collection(self, vector_size: int = VECTOR_SIZE) -> None:
        try:
            self.client.get_collection(COLLECTION)
            return
        except (UnexpectedResponse, Exception):
            pass

        logger.info("creating_qdrant_collection", name=COLLECTION, size=vector_size)
        self.client.create_collection(
            collection_name=COLLECTION,
            vectors_config=models.VectorParams(
                size=vector_size,
                distance=models.Distance.COSINE,
            ),
        )
        for field in ("organization_id", "meeting_id", "chunk_type"):
            try:
                self.client.create_payload_index(
                    collection_name=COLLECTION,
                    field_name=field,
                    field_schema=models.PayloadSchemaType.KEYWORD,
                )
            except Exception:
                pass

    def upsert_chunks(self, points: list[dict[str, Any]]) -> int:
        if not points:
            return 0
        self.ensure_collection(len(points[0]["vector"]))
        qdrant_points = [
            models.PointStruct(id=p["id"], vector=p["vector"], payload=p["payload"])
            for p in points
        ]
        self.client.upsert(collection_name=COLLECTION, points=qdrant_points)
        logger.info("qdrant_upserted", count=len(qdrant_points))
        return len(qdrant_points)

    def search(
        self,
        query_vector: list[float],
        organization_id: str,
        limit: int = 10,
        meeting_id: str | None = None,
        score_threshold: float = 0.3,
    ) -> list[dict[str, Any]]:
        self.ensure_collection(len(query_vector))
        must = [
            models.FieldCondition(
                key="organization_id",
                match=models.MatchValue(value=organization_id),
            )
        ]
        if meeting_id:
            must.append(
                models.FieldCondition(
                    key="meeting_id",
                    match=models.MatchValue(value=meeting_id),
                )
            )
        results = self.client.search(
            collection_name=COLLECTION,
            query_vector=query_vector,
            query_filter=models.Filter(must=must),
            limit=limit,
            score_threshold=score_threshold,
            with_payload=True,
        )
        return [
            {"id": str(r.id), "score": r.score, "payload": r.payload or {}}
            for r in results
        ]

    def delete_meeting(self, meeting_id: str, organization_id: str) -> None:
        try:
            self.client.delete(
                collection_name=COLLECTION,
                points_selector=models.FilterSelector(
                    filter=models.Filter(
                        must=[
                            models.FieldCondition(
                                key="meeting_id",
                                match=models.MatchValue(value=meeting_id),
                            ),
                            models.FieldCondition(
                                key="organization_id",
                                match=models.MatchValue(value=organization_id),
                            ),
                        ]
                    )
                ),
            )
            logger.info("qdrant_meeting_deleted", meeting_id=meeting_id)
        except Exception as e:
            logger.warning("qdrant_delete_failed", error=str(e))


def get_qdrant_service() -> QdrantService:
    return QdrantService()

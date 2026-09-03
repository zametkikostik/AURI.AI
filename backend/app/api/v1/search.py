"""Search API — semantic, keyword, hybrid."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import RequireViewer
from app.services.search import SearchService

router = APIRouter()


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000)
    limit: int = Field(10, ge=1, le=50)
    meeting_id: UUID | None = None


@router.post("/semantic")
async def semantic_search(
    body: SearchRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    ctx: RequireViewer,
):
    service = SearchService(db)
    results = await service.semantic_search(
        query=body.query,
        organization_id=ctx.org_id,
        limit=body.limit,
        meeting_id=body.meeting_id,
    )
    return {"query": body.query, "results": results, "count": len(results)}


@router.get("/keyword")
async def keyword_search(
    db: Annotated[AsyncSession, Depends(get_db)],
    ctx: RequireViewer,
    q: str = Query(..., min_length=1, max_length=500),
    limit: int = Query(20, ge=1, le=50),
):
    service = SearchService(db)
    results = await service.keyword_search(
        query=q, organization_id=ctx.org_id, limit=limit
    )
    return {"query": q, "results": results, "count": len(results)}


@router.post("/hybrid")
async def hybrid_search(
    body: SearchRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    ctx: RequireViewer,
):
    service = SearchService(db)
    return await service.hybrid_search(
        query=body.query, organization_id=ctx.org_id, limit=body.limit
    )

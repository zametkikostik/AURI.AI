"""SSE realtime events via Redis bus."""

from __future__ import annotations

import json

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from app.services.realtime_bus import subscribe

router = APIRouter()


async def publish_event(organization_id: str, event: dict) -> None:
    from app.services.realtime_bus import publish

    await publish(organization_id, event)


@router.get("/events")
async def stream_events(request: Request, organization_id: str):
    async def event_generator():
        async for item in subscribe(organization_id):
            if await request.is_disconnected():
                break
            if item.get("type") == "keepalive":
                yield ": keepalive\n\n"
            else:
                yield f"data: {json.dumps(item, default=str)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )

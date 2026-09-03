"""Realtime event bus (Redis pub/sub + in-process fallback)."""

from __future__ import annotations

import asyncio
import json
from collections import defaultdict
from typing import Any, AsyncIterator

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()

CHANNEL_PREFIX = "auri:events:"
_local_subs: dict[str, list[asyncio.Queue]] = defaultdict(list)
_local_lock = asyncio.Lock()


async def publish(organization_id: str, event: dict[str, Any]) -> None:
    payload = {**event, "organization_id": organization_id}
    message = json.dumps(payload, default=str)

    try:
        import redis.asyncio as aioredis

        client = aioredis.from_url(settings.redis_url, decode_responses=True)
        await client.publish(f"{CHANNEL_PREFIX}{organization_id}", message)
        await client.aclose()
    except Exception as e:
        logger.debug("redis_publish_fallback", error=str(e))

    async with _local_lock:
        queues = list(_local_subs.get(organization_id, []))
    for q in queues:
        try:
            q.put_nowait(payload)
        except asyncio.QueueFull:
            pass


async def subscribe(organization_id: str) -> AsyncIterator[dict[str, Any]]:
    queue: asyncio.Queue = asyncio.Queue(maxsize=200)
    async with _local_lock:
        _local_subs[organization_id].append(queue)

    stop = asyncio.Event()

    async def redis_listener():
        try:
            import redis.asyncio as aioredis

            client = aioredis.from_url(settings.redis_url, decode_responses=True)
            pubsub = client.pubsub()
            await pubsub.subscribe(f"{CHANNEL_PREFIX}{organization_id}")
            while not stop.is_set():
                msg = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                if msg and msg.get("type") == "message":
                    data = json.loads(msg["data"])
                    await queue.put(data)
            await pubsub.unsubscribe()
            await client.aclose()
        except Exception as e:
            logger.debug("redis_subscribe_unavailable", error=str(e))

    redis_task = asyncio.create_task(redis_listener())

    try:
        yield {"type": "connected", "organization_id": organization_id}
        while True:
            try:
                item = await asyncio.wait_for(queue.get(), timeout=25.0)
                yield item
            except asyncio.TimeoutError:
                yield {"type": "keepalive"}
    finally:
        stop.set()
        redis_task.cancel()
        try:
            await redis_task
        except asyncio.CancelledError:
            pass
        async with _local_lock:
            subs = _local_subs.get(organization_id, [])
            if queue in subs:
                subs.remove(queue)

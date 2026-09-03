"""Redis-backed sliding window rate limiter."""

from __future__ import annotations

import time
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()


class RedisRateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app,
        default_limit: int = 120,
        window_seconds: int = 60,
        auth_limit: int = 20,
    ):
        super().__init__(app)
        self.default_limit = default_limit
        self.window = window_seconds
        self.auth_limit = auth_limit
        self._redis = None

    def _limit_for(self, path: str) -> int:
        if path.startswith("/api/v1/auth"):
            return self.auth_limit
        return self.default_limit

    async def _get_redis(self):
        if self._redis is not None:
            return self._redis
        try:
            import redis.asyncio as aioredis

            self._redis = aioredis.from_url(settings.redis_url, decode_responses=True)
            await self._redis.ping()
            return self._redis
        except Exception as e:
            logger.warning("redis_rate_limit_unavailable", error=str(e))
            self._redis = False  # type: ignore
            return None

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if request.method == "OPTIONS":
            return await call_next(request)

        path = request.url.path
        if not path.startswith("/api"):
            return await call_next(request)

        limit = self._limit_for(path)
        client = request.client.host if request.client else "unknown"
        bucket = path.split("/")[3] if path.count("/") >= 3 else "api"
        key = f"rl:{client}:{bucket}"
        now = time.time()
        window_start = now - self.window

        r = await self._get_redis()
        if not r:
            if getattr(settings, "rate_limit_fail_closed", False):
                return JSONResponse(
                    status_code=503,
                    content={"detail": "Rate limiter unavailable"},
                )
            return await call_next(request)

        try:
            pipe = r.pipeline()
            pipe.zremrangebyscore(key, 0, window_start)
            pipe.zadd(key, {f"{now}": now})
            pipe.zcard(key)
            pipe.expire(key, self.window + 1)
            results = await pipe.execute()
            count = int(results[2])
        except Exception as e:
            logger.warning("redis_rate_limit_error", error=str(e))
            return await call_next(request)

        if count > limit:
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded. Try again later."},
                headers={
                    "Retry-After": str(self.window),
                    "X-RateLimit-Limit": str(limit),
                    "X-RateLimit-Remaining": "0",
                },
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(max(0, limit - count))
        return response

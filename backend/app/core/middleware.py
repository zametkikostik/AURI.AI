"""HTTP middleware: request ID, simple in-memory rate limit."""

from __future__ import annotations

import time
import uuid
from collections import defaultdict, deque
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.core.logging import get_logger

logger = get_logger(__name__)


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
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
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def _limit_for(self, path: str) -> int:
        if path.startswith("/api/v1/auth"):
            return self.auth_limit
        return self.default_limit

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if request.method == "OPTIONS":
            return await call_next(request)

        path = request.url.path
        if not path.startswith("/api"):
            return await call_next(request)

        client = request.client.host if request.client else "unknown"
        key = f"{client}:{path.split('/')[3] if path.count('/') >= 3 else 'api'}"
        limit = self._limit_for(path)
        now = time.time()
        window_start = now - self.window

        q = self._hits[key]
        while q and q[0] < window_start:
            q.popleft()

        if len(q) >= limit:
            logger.warning("rate_limit_exceeded", client=client, path=path)
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded. Try again later."},
                headers={"Retry-After": str(self.window)},
            )

        q.append(now)
        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(max(0, limit - len(q)))
        return response

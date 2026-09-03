"""Prometheus metrics endpoint."""

from __future__ import annotations

from app.core.logging import get_logger

logger = get_logger(__name__)


def setup_metrics(app) -> bool:
    try:
        from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest, REGISTRY
        from starlette.requests import Request
        from starlette.responses import Response
        import time

        REQUESTS = Counter(
            "auri_http_requests_total",
            "Total HTTP requests",
            ["method", "path", "status"],
        )
        LATENCY = Histogram(
            "auri_http_request_duration_seconds",
            "HTTP request latency",
            ["method", "path"],
            buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
        )

        @app.middleware("http")
        async def metrics_middleware(request: Request, call_next):
            if request.url.path in ("/metrics", "/live", "/ready"):
                return await call_next(request)
            start = time.perf_counter()
            response = await call_next(request)
            elapsed = time.perf_counter() - start
            parts = request.url.path.strip("/").split("/")[:3]
            path = "/" + "/".join(parts)
            REQUESTS.labels(request.method, path, str(response.status_code)).inc()
            LATENCY.labels(request.method, path).observe(elapsed)
            return response

        @app.get("/metrics")
        async def metrics():
            return Response(generate_latest(REGISTRY), media_type=CONTENT_TYPE_LATEST)

        logger.info("prometheus_metrics_enabled")
        return True
    except Exception as e:
        logger.warning("prometheus_metrics_unavailable", error=str(e))

        @app.get("/metrics")
        async def metrics_stub():
            return {"detail": "prometheus_client not installed"}

        return False

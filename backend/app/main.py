from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.logging import setup_logging, get_logger
from app.core.middleware import RateLimitMiddleware, RequestIdMiddleware
from app.core.rate_limit_redis import RedisRateLimitMiddleware
from app.core.security_headers import SecurityHeadersMiddleware
from app.ai.ollama_provider import check_ollama_health
from app.core.observability import setup_sentry, setup_opentelemetry
from app.core.metrics import setup_metrics

settings = get_settings()
setup_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(
        "starting_auri",
        env=settings.app_env,
        ai_mode=settings.ai_mode,
        debug=settings.debug,
    )
    ollama_status = await check_ollama_health()
    logger.info("ollama_health_check", **ollama_status)
    if settings.ai_mode == "strict_private" and ollama_status.get("status") != "ok":
        logger.warning(
            "strict_private_mode_but_ollama_unavailable",
            message="AI features will fail until Ollama is running",
        )
    yield
    logger.info("shutting_down_auri")


app = FastAPI(
    title=settings.app_name,
    description="AI Meeting Assistant & Knowledge Platform — Privacy-first",
    version="0.3.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.is_development else None,
    redoc_url="/redoc" if settings.is_development else None,
)

setup_sentry()
setup_opentelemetry(app)
setup_metrics(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RequestIdMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
if settings.use_redis_rate_limit:
    app.add_middleware(RedisRateLimitMiddleware)
else:
    app.add_middleware(RateLimitMiddleware)

from app.api.v1 import api_router

app.include_router(api_router, prefix=settings.api_v1_prefix)


@app.get("/health")
async def health():
    ollama = await check_ollama_health()
    redis_ok = False
    try:
        import redis.asyncio as aioredis

        r = aioredis.from_url(settings.redis_url, decode_responses=True)
        await r.ping()
        await r.aclose()
        redis_ok = True
    except Exception:
        redis_ok = False
    return {
        "status": "ok",
        "app": settings.app_name,
        "env": settings.app_env,
        "ai_mode": settings.ai_mode,
        "version": "0.3.0",
        "ollama": ollama,
        "redis": redis_ok,
        "stripe_configured": bool(getattr(settings, "stripe_secret_key", None)),
    }


@app.get("/")
async def root():
    return {
        "message": f"Welcome to {settings.app_name}",
        "docs": "/docs",
        "health": "/health",
        "ai_mode": settings.ai_mode,
        "version": "0.3.0",
    }


@app.get("/ready")
async def ready():
    from sqlalchemy import text as sa_text
    from app.core.database import engine
    from fastapi.responses import JSONResponse

    checks = {"database": False, "redis": False}
    try:
        async with engine.connect() as conn:
            await conn.execute(sa_text("SELECT 1"))
        checks["database"] = True
    except Exception:
        checks["database"] = False
    try:
        import redis.asyncio as aioredis

        r = aioredis.from_url(settings.redis_url, decode_responses=True)
        await r.ping()
        await r.aclose()
        checks["redis"] = True
    except Exception:
        checks["redis"] = False

    ok = all(checks.values())
    return JSONResponse(
        status_code=200 if ok else 503,
        content={"status": "ready" if ok else "not_ready", "checks": checks},
    )


@app.get("/live")
async def live():
    return {"status": "alive"}

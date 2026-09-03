"""AI test & utility endpoints."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.ai.router import get_ai_router
from app.core.config import get_settings
from app.core.logging import get_logger

router = APIRouter()
settings = get_settings()
logger = get_logger(__name__)


class SummarizeRequest(BaseModel):
    transcript: str = Field(..., min_length=20, max_length=200_000)
    title: str | None = None
    language: str = "en"


class EmbedRequest(BaseModel):
    texts: list[str] = Field(..., min_length=1, max_length=32)


@router.post("/summarize")
async def summarize_meeting(body: SummarizeRequest):
    try:
        router_ai = get_ai_router()
        llm = await router_ai.get_llm()
        result = await llm.summarize_meeting(
            transcript=body.transcript,
            meeting_title=body.title,
            language=body.language,
        )
        return result
    except Exception as e:
        logger.error("summarize_failed", error=str(e))
        raise HTTPException(status_code=503, detail=str(e))


@router.post("/embed")
async def embed_texts(body: EmbedRequest):
    try:
        router_ai = get_ai_router()
        emb = await router_ai.get_embedding()
        results = await emb.embed(body.texts)
        return {
            "count": len(results),
            "dimensions": results[0].dimensions if results else 0,
            "provider": results[0].provider if results else None,
            "model": results[0].model if results else None,
            "embeddings": [r.embedding for r in results],
        }
    except Exception as e:
        logger.error("embed_failed", error=str(e))
        raise HTTPException(status_code=503, detail=str(e))


@router.get("/status")
async def ai_status():
    from app.ai.ollama_provider import check_ollama_health

    ollama = await check_ollama_health()
    return {
        "ai_mode": settings.ai_mode,
        "ollama": ollama,
        "ollama_llm_model": settings.ollama_llm_model,
        "ollama_embed_model": settings.ollama_embed_model,
        "is_private_mode": settings.is_private_mode,
    }

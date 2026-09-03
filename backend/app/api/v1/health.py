from fastapi import APIRouter

from app.ai.ollama_provider import check_ollama_health
from app.core.config import get_settings

router = APIRouter()
settings = get_settings()


@router.get("/health")
async def health_check():
    ollama = await check_ollama_health()
    return {
        "status": "ok",
        "app": settings.app_name,
        "env": settings.app_env,
        "ai_mode": settings.ai_mode,
        "ollama": ollama,
    }

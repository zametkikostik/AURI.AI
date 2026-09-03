"""AI Router — selects provider based on AI_MODE (Ollama-first in strict_private)."""

from functools import lru_cache

from app.ai.base import BaseEmbeddingProvider, BaseLLMProvider
from app.ai.ollama_provider import (
    OllamaEmbeddingProvider,
    OllamaLLMProvider,
    check_ollama_health,
)
from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()


class AIRouter:
    def __init__(self) -> None:
        self._llm: BaseLLMProvider | None = None
        self._embed: BaseEmbeddingProvider | None = None

    async def get_llm(self) -> BaseLLMProvider:
        if self._llm is not None:
            return self._llm

        if settings.ai_mode == "strict_private":
            health = await check_ollama_health()
            if health.get("status") != "ok":
                raise RuntimeError(
                    f"Strict private mode requires Ollama, but it is unavailable: {health}"
                )
            self._llm = OllamaLLMProvider()
            logger.info("llm_provider_selected", provider="ollama", mode=settings.ai_mode)
            return self._llm

        try:
            health = await check_ollama_health()
            if health.get("status") == "ok" and health.get("llm_ready"):
                self._llm = OllamaLLMProvider()
                logger.info("llm_provider_selected", provider="ollama", mode=settings.ai_mode)
                return self._llm
        except Exception:
            pass

        raise RuntimeError(
            "No available LLM provider. Configure Ollama or cloud API keys."
        )

    async def get_embedding(self) -> BaseEmbeddingProvider:
        if self._embed is not None:
            return self._embed

        try:
            health = await check_ollama_health()
            if health.get("status") == "ok" and health.get("embed_ready"):
                self._embed = OllamaEmbeddingProvider()
                logger.info("embedding_provider_selected", provider="ollama")
                return self._embed
        except Exception:
            pass

        if settings.ai_mode == "strict_private":
            raise RuntimeError("Strict private mode requires local embeddings (Ollama)")

        raise RuntimeError("No available embedding provider")


@lru_cache
def get_ai_router() -> AIRouter:
    return AIRouter()

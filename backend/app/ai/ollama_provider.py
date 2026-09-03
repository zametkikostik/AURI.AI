"""
Ollama Provider — Local / Privacy-first AI

All inference happens inside the customer's infrastructure.
No meeting data is sent to external services.
"""

import json
from typing import Any

import httpx
import ollama
from tenacity import retry, stop_after_attempt, wait_exponential

from app.ai.base import (
    BaseEmbeddingProvider,
    BaseLLMProvider,
    EmbeddingResult,
    SummaryResult,
    AIProviderType,
)
from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()


MEETING_SUMMARY_SYSTEM = """You are an expert meeting analyst. 
Your task is to extract structured information from meeting transcripts.
Rules:
- Use ONLY information present in the transcript. Never invent facts.
- Be concise and professional.
- Output valid JSON only.
- If something is missing, use empty list or null.
"""

MEETING_SUMMARY_PROMPT = """Analyze the following meeting transcript and return a JSON object with this exact structure:

{{
  "executive_summary": "2-4 sentence high-level summary",
  "detailed_summary": "Longer structured summary (optional, can be null)",
  "action_items": [
    {{"who": "person name or null", "what": "task description", "deadline": "date or null"}}
  ],
  "key_decisions": ["decision 1", "decision 2"],
  "open_questions": ["question 1"],
  "risks_blockers": ["risk or blocker 1"],
  "topics": ["topic1", "topic2"]
}}

Meeting title: {title}
Language: {language}

Transcript:
---
{transcript}
---

Return ONLY the JSON object, no markdown, no explanations.
"""


class OllamaLLMProvider(BaseLLMProvider):
    provider_type = AIProviderType.OLLAMA

    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
        timeout: int | None = None,
    ):
        self.base_url = base_url or settings.ollama_base_url
        self.model = model or settings.ollama_llm_model
        self.timeout = timeout or settings.ollama_timeout
        self.client = ollama.AsyncClient(host=self.base_url)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def generate(
        self,
        prompt: str,
        system: str | None = None,
        temperature: float = 0.2,
        max_tokens: int = 4096,
        json_mode: bool = False,
    ) -> str:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        options: dict[str, Any] = {
            "temperature": temperature,
            "num_predict": max_tokens,
        }

        try:
            response = await self.client.chat(
                model=self.model,
                messages=messages,
                options=options,
                format="json" if json_mode else None,
            )
            return response["message"]["content"]
        except Exception as e:
            logger.error("ollama_generate_failed", error=str(e), model=self.model)
            raise

    async def summarize_meeting(
        self,
        transcript: str,
        meeting_title: str | None = None,
        language: str = "en",
    ) -> SummaryResult:
        prompt = MEETING_SUMMARY_PROMPT.format(
            title=meeting_title or "Untitled Meeting",
            language=language,
            transcript=transcript[:120_000],
        )

        raw = await self.generate(
            prompt=prompt,
            system=MEETING_SUMMARY_SYSTEM,
            temperature=0.1,
            max_tokens=4096,
            json_mode=True,
        )

        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            start = raw.find("{")
            end = raw.rfind("}") + 1
            if start >= 0 and end > start:
                data = json.loads(raw[start:end])
            else:
                logger.warning("failed_to_parse_summary_json", raw=raw[:500])
                data = {
                    "executive_summary": raw[:1000],
                    "action_items": [],
                    "key_decisions": [],
                    "open_questions": [],
                    "risks_blockers": [],
                    "topics": [],
                }

        return SummaryResult(
            executive_summary=data.get("executive_summary", ""),
            detailed_summary=data.get("detailed_summary"),
            action_items=data.get("action_items", []),
            key_decisions=data.get("key_decisions", []),
            open_questions=data.get("open_questions", []),
            risks_blockers=data.get("risks_blockers", []),
            topics=data.get("topics", []),
            provider=self.provider_type.value,
            model=self.model,
        )


class OllamaEmbeddingProvider(BaseEmbeddingProvider):
    provider_type = AIProviderType.OLLAMA

    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
    ):
        self.base_url = base_url or settings.ollama_base_url
        self.model = model or settings.ollama_embed_model
        self.client = ollama.AsyncClient(host=self.base_url)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=8))
    async def embed(self, texts: list[str]) -> list[EmbeddingResult]:
        results = []
        for text in texts:
            try:
                response = await self.client.embeddings(
                    model=self.model,
                    prompt=text,
                )
                embedding = response["embedding"]
                results.append(
                    EmbeddingResult(
                        embedding=embedding,
                        model=self.model,
                        dimensions=len(embedding),
                        provider=self.provider_type.value,
                    )
                )
            except Exception as e:
                logger.error("ollama_embed_failed", error=str(e), model=self.model)
                raise
        return results

    async def embed_query(self, text: str) -> EmbeddingResult:
        results = await self.embed([text])
        return results[0]


async def check_ollama_health() -> dict[str, Any]:
    """Check if Ollama is reachable and which models are available."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{settings.ollama_base_url}/api/tags")
            if resp.status_code == 200:
                models = [m["name"] for m in resp.json().get("models", [])]
                return {
                    "status": "ok",
                    "models": models,
                    "llm_ready": any(settings.ollama_llm_model in m for m in models),
                    "embed_ready": any(settings.ollama_embed_model in m for m in models),
                }
    except Exception as e:
        return {"status": "error", "error": str(e)}
    return {"status": "unreachable"}

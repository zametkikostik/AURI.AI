"""AI Provider Abstraction Layer"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class AIProviderType(str, Enum):
    OLLAMA = "ollama"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    DEEPGRAM = "deepgram"
    ASSEMBLYAI = "assemblyai"


class TranscriptionResult(BaseModel):
    text: str
    language: str | None = None
    duration_seconds: float | None = None
    words: list[dict[str, Any]] = Field(default_factory=list)
    speakers: list[dict[str, Any]] = Field(default_factory=list)
    confidence: float | None = None
    provider: str


class EmbeddingResult(BaseModel):
    embedding: list[float]
    model: str
    dimensions: int
    provider: str


class SummaryResult(BaseModel):
    executive_summary: str
    detailed_summary: str | None = None
    action_items: list[dict[str, Any]] = Field(default_factory=list)
    key_decisions: list[str] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)
    risks_blockers: list[str] = Field(default_factory=list)
    topics: list[str] = Field(default_factory=list)
    provider: str
    model: str


class BaseLLMProvider(ABC):
    provider_type: AIProviderType

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        system: str | None = None,
        temperature: float = 0.2,
        max_tokens: int = 4096,
        json_mode: bool = False,
    ) -> str:
        ...

    @abstractmethod
    async def summarize_meeting(
        self,
        transcript: str,
        meeting_title: str | None = None,
        language: str = "en",
    ) -> SummaryResult:
        ...


class BaseEmbeddingProvider(ABC):
    provider_type: AIProviderType

    @abstractmethod
    async def embed(self, texts: list[str]) -> list[EmbeddingResult]:
        ...

    @abstractmethod
    async def embed_query(self, text: str) -> EmbeddingResult:
        ...


class BaseTranscriptionProvider(ABC):
    provider_type: AIProviderType

    @abstractmethod
    async def transcribe(
        self,
        audio_url: str | None = None,
        audio_bytes: bytes | None = None,
        language: str | None = None,
        diarize: bool = True,
    ) -> TranscriptionResult:
        ...

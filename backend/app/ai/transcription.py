"""Transcription providers — local faster-whisper in strict_private."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

from app.ai.base import AIProviderType, BaseTranscriptionProvider, TranscriptionResult
from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()


class LocalWhisperProvider(BaseTranscriptionProvider):
    """Local transcription via faster-whisper. Fully private."""

    provider_type = AIProviderType.OLLAMA

    def __init__(self, model_size: str = "base") -> None:
        self.model_size = model_size
        self._model = None

    def _load_model(self):
        if self._model is not None:
            return self._model
        try:
            from faster_whisper import WhisperModel

            self._model = WhisperModel(
                self.model_size,
                device="cpu",
                compute_type="int8",
            )
            logger.info("faster_whisper_loaded", model=self.model_size)
            return self._model
        except ImportError:
            logger.warning("faster_whisper_not_installed")
            raise RuntimeError(
                "faster-whisper is not installed. Run: pip install faster-whisper"
            )

    async def transcribe(
        self,
        audio_url: str | None = None,
        audio_bytes: bytes | None = None,
        language: str | None = None,
        diarize: bool = True,
    ) -> TranscriptionResult:
        if audio_bytes is None and audio_url is None:
            raise ValueError("Either audio_bytes or audio_url is required")

        model = self._load_model()

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            if audio_bytes:
                tmp.write(audio_bytes)
            else:
                raise NotImplementedError("audio_url download not yet implemented")
            tmp_path = tmp.name

        try:
            segments_iter, info = model.transcribe(
                tmp_path,
                language=language,
                beam_size=5,
                word_timestamps=True,
                vad_filter=True,
            )

            words: list[dict[str, Any]] = []
            full_text_parts: list[str] = []

            for seg in segments_iter:
                full_text_parts.append(seg.text.strip())
                if seg.words:
                    for w in seg.words:
                        words.append(
                            {
                                "start": w.start,
                                "end": w.end,
                                "word": w.word,
                                "confidence": getattr(w, "probability", None),
                            }
                        )

            full_text = " ".join(full_text_parts)

            from app.ai.diarization import (
                diarize_with_pyannote,
                merge_diarization_with_words,
                assign_speakers_heuristic,
            )

            diar = diarize_with_pyannote(tmp_path)
            if diar:
                seg_out, speakers = merge_diarization_with_words(words, diar)
            else:
                seg_out, speakers = assign_speakers_heuristic(words)

            if seg_out:
                words = [
                    {
                        "start": s.get("start"),
                        "end": s.get("end"),
                        "word": s.get("text"),
                        "text": s.get("text"),
                        "speaker": s.get("speaker"),
                        "confidence": None,
                    }
                    for s in seg_out
                ]

            return TranscriptionResult(
                text=full_text,
                language=info.language if info else language,
                duration_seconds=info.duration if info else None,
                words=words,
                speakers=speakers,
                confidence=None,
                provider="faster-whisper",
            )
        finally:
            Path(tmp_path).unlink(missing_ok=True)


class MockTranscriptionProvider(BaseTranscriptionProvider):
    provider_type = AIProviderType.OLLAMA

    async def transcribe(
        self,
        audio_url: str | None = None,
        audio_bytes: bytes | None = None,
        language: str | None = None,
        diarize: bool = True,
    ) -> TranscriptionResult:
        logger.warning("using_mock_transcription_provider")
        return TranscriptionResult(
            text=(
                "[Mock transcript] Placeholder — install faster-whisper "
                "or configure Deepgram/AssemblyAI."
            ),
            language=language or "en",
            duration_seconds=60.0,
            words=[],
            speakers=[{"id": "speaker_0", "name": "Speaker 1"}],
            confidence=0.99,
            provider="mock",
        )


async def get_transcription_provider() -> BaseTranscriptionProvider:
    if settings.ai_mode == "strict_private":
        try:
            return LocalWhisperProvider(model_size="base")
        except Exception as e:
            logger.warning("local_whisper_unavailable", error=str(e))
            return MockTranscriptionProvider()

    try:
        return LocalWhisperProvider(model_size="base")
    except Exception:
        return MockTranscriptionProvider()

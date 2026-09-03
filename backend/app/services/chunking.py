"""Transcript chunking for embeddings and retrieval."""

from __future__ import annotations

import re
import uuid
from typing import Any


def chunk_transcript(
    full_text: str,
    segments: list[dict[str, Any]] | None = None,
    max_chars: int = 800,
    overlap_chars: int = 120,
) -> list[dict[str, Any]]:
    if not full_text or not full_text.strip():
        return []

    if segments and len(segments) > 0:
        return _chunk_from_segments(segments, max_chars=max_chars, overlap_chars=overlap_chars)

    return _chunk_plain_text(full_text, max_chars=max_chars, overlap_chars=overlap_chars)


def _chunk_from_segments(
    segments: list[dict[str, Any]],
    max_chars: int,
    overlap_chars: int,
) -> list[dict[str, Any]]:
    chunks: list[dict[str, Any]] = []
    current_texts: list[str] = []
    current_start: float | None = None
    current_end: float | None = None
    current_speaker: str | None = None
    idx = 0

    def flush():
        nonlocal current_texts, current_start, current_end, current_speaker, idx
        if not current_texts:
            return
        text = " ".join(current_texts).strip()
        if text:
            chunks.append(
                {
                    "id": str(uuid.uuid4()),
                    "text": text,
                    "start": current_start,
                    "end": current_end,
                    "chunk_index": idx,
                    "speaker": current_speaker,
                    "chunk_type": "transcript",
                }
            )
            idx += 1
        current_texts = []
        current_start = None
        current_end = None
        current_speaker = None

    for seg in segments:
        text = (seg.get("text") or seg.get("word") or "").strip()
        if not text:
            continue
        start = seg.get("start")
        end = seg.get("end")
        speaker = seg.get("speaker")

        prospective = (" ".join(current_texts) + " " + text).strip()
        if current_texts and len(prospective) > max_chars:
            flush()
            if chunks and overlap_chars > 0:
                prev = chunks[-1]["text"]
                overlap = prev[-overlap_chars:] if len(prev) > overlap_chars else prev
                current_texts = [overlap]
                current_start = chunks[-1].get("end")
                current_end = chunks[-1].get("end")

        if not current_texts:
            current_start = start
            current_speaker = speaker
        current_texts.append(text)
        current_end = end if end is not None else current_end

    flush()
    return chunks


def _chunk_plain_text(
    text: str,
    max_chars: int,
    overlap_chars: int,
) -> list[dict[str, Any]]:
    paragraphs = re.split(r"\n{2,}", text.strip())
    sentences: list[str] = []
    for p in paragraphs:
        parts = re.split(r"(?<=[.!?])\s+", p.strip())
        sentences.extend([s.strip() for s in parts if s.strip()])

    chunks: list[dict[str, Any]] = []
    current: list[str] = []
    idx = 0

    def flush():
        nonlocal current, idx
        if not current:
            return
        body = " ".join(current).strip()
        if body:
            chunks.append(
                {
                    "id": str(uuid.uuid4()),
                    "text": body,
                    "start": None,
                    "end": None,
                    "chunk_index": idx,
                    "speaker": None,
                    "chunk_type": "transcript",
                }
            )
            idx += 1
        current = []

    for sent in sentences:
        prospective = (" ".join(current) + " " + sent).strip()
        if current and len(prospective) > max_chars:
            flush()
            if chunks and overlap_chars > 0:
                prev = chunks[-1]["text"]
                overlap = prev[-overlap_chars:] if len(prev) > overlap_chars else prev
                current = [overlap]
        current.append(sent)

    flush()
    return chunks

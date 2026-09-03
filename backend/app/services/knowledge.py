"""Knowledge extraction and lightweight knowledge graph helpers."""

from __future__ import annotations

import json
import re
from typing import Any

from app.ai.router import get_ai_router
from app.core.logging import get_logger

logger = get_logger(__name__)

ENTITY_PROMPT = """Extract structured knowledge from the meeting transcript.
Return ONLY valid JSON with this schema:

{{
  "people": ["Name1", "Name2"],
  "organizations": ["Org1"],
  "projects": ["Project name"],
  "decisions": ["Decision text"],
  "action_items": [
    {{"who": "person or null", "what": "task", "deadline": "date or null"}}
  ],
  "topics": ["topic1", "topic2"],
  "risks": ["risk1"],
  "relations": [
    {{"from": "entity", "to": "entity", "type": "owns|works_on|decided|mentioned"}}
  ]
}}

Rules:
- Use only facts present in the transcript.
- Prefer short canonical names.
- If nothing found, use empty lists.

Transcript:
---
{transcript}
---
"""


async def extract_knowledge(
    transcript: str,
    meeting_title: str | None = None,
) -> dict[str, Any]:
    empty = {
        "people": [],
        "organizations": [],
        "projects": [],
        "decisions": [],
        "action_items": [],
        "topics": [],
        "risks": [],
        "relations": [],
    }

    if not transcript or len(transcript.strip()) < 40:
        return empty

    try:
        router = get_ai_router()
        llm = await router.get_llm()
        prompt = ENTITY_PROMPT.format(transcript=transcript[:100_000])
        raw = await llm.generate(
            prompt=prompt,
            system="You are a precise knowledge extraction engine. Output JSON only.",
            temperature=0.1,
            max_tokens=3000,
            json_mode=True,
        )
        data = _parse_json(raw)
        return {**empty, **{k: data.get(k, empty[k]) for k in empty}}
    except Exception as e:
        logger.warning("knowledge_extraction_failed", error=str(e))
        return empty


def _parse_json(raw: str) -> dict[str, Any]:
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        start = raw.find("{")
        end = raw.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(raw[start:end])
        raise


def simple_keyword_extract(text: str, max_topics: int = 12) -> list[str]:
    stop = {
        "the", "and", "for", "that", "with", "this", "from", "have", "will",
        "are", "was", "were", "been", "being", "has", "had", "not", "but",
    }
    words = re.findall(r"[a-zA-Zа-яА-ЯёЁ]{4,}", text.lower())
    freq: dict[str, int] = {}
    for w in words:
        if w in stop:
            continue
        freq[w] = freq.get(w, 0) + 1
    ranked = sorted(freq.items(), key=lambda x: x[1], reverse=True)
    return [w for w, _ in ranked[:max_topics]]

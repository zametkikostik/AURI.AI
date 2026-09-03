"""Export meetings to JSON / Markdown / TXT."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.meeting import Meeting


async def load_meeting_for_export(
    db: AsyncSession, meeting_id: UUID, organization_id: UUID
) -> Meeting | None:
    result = await db.execute(
        select(Meeting)
        .where(Meeting.id == meeting_id, Meeting.organization_id == organization_id)
        .options(selectinload(Meeting.transcript), selectinload(Meeting.recordings))
    )
    return result.scalar_one_or_none()


def meeting_to_dict(meeting: Meeting) -> dict[str, Any]:
    knowledge = (meeting.meta or {}).get("knowledge", {})
    return {
        "id": str(meeting.id),
        "title": meeting.title,
        "description": meeting.description,
        "status": meeting.status,
        "language": meeting.language,
        "duration_seconds": meeting.duration_seconds,
        "created_at": meeting.created_at.isoformat() if meeting.created_at else None,
        "executive_summary": meeting.executive_summary,
        "topics": meeting.topics,
        "action_items": meeting.action_items,
        "knowledge": knowledge,
        "transcript": {
            "full_text": meeting.transcript.full_text if meeting.transcript else None,
            "language": meeting.transcript.language if meeting.transcript else None,
            "provider": meeting.transcript.provider if meeting.transcript else None,
            "speakers": meeting.transcript.speakers if meeting.transcript else None,
        }
        if meeting.transcript
        else None,
        "exported_at": datetime.now(timezone.utc).isoformat(),
    }


def export_json(meeting: Meeting) -> bytes:
    return json.dumps(meeting_to_dict(meeting), ensure_ascii=False, indent=2).encode("utf-8")


def export_markdown(meeting: Meeting) -> bytes:
    d = meeting_to_dict(meeting)
    lines = [
        f"# {d['title']}",
        "",
        f"- Status: {d['status']}",
        f"- Language: {d['language']}",
        f"- Duration: {d.get('duration_seconds') or '—'} sec",
        f"- Exported: {d['exported_at']}",
        "",
        "## Executive Summary",
        "",
        d.get("executive_summary") or "_No summary_",
        "",
        "## Topics",
        "",
    ]
    for t in d.get("topics") or []:
        lines.append(f"- {t}")
    if not d.get("topics"):
        lines.append("_None_")

    lines += ["", "## Action Items", ""]
    for a in d.get("action_items") or []:
        if isinstance(a, dict):
            who = a.get("who") or "—"
            what = a.get("what") or ""
            deadline = a.get("deadline") or ""
            lines.append(f"- **{who}**: {what}" + (f" (due {deadline})" if deadline else ""))
        else:
            lines.append(f"- {a}")
    if not d.get("action_items"):
        lines.append("_None_")

    knowledge = d.get("knowledge") or {}
    if knowledge.get("decisions"):
        lines += ["", "## Key Decisions", ""]
        for x in knowledge["decisions"]:
            lines.append(f"- {x}")

    if knowledge.get("risks"):
        lines += ["", "## Risks & Blockers", ""]
        for x in knowledge["risks"]:
            lines.append(f"- {x}")

    lines += ["", "## Transcript", ""]
    text = (d.get("transcript") or {}).get("full_text") or "_No transcript_"
    lines.append(text)
    lines.append("")
    return "\n".join(lines).encode("utf-8")


def export_txt(meeting: Meeting) -> bytes:
    return export_markdown(meeting)

"""Outbound notifications: Slack, Notion, generic webhook."""

from __future__ import annotations

from typing import Any

import httpx

from app.core.logging import get_logger

logger = get_logger(__name__)


async def notify_slack(
    webhook_url: str,
    *,
    title: str,
    summary: str | None,
    meeting_id: str,
    action_items: list | None = None,
) -> dict[str, Any]:
    if not webhook_url:
        return {"ok": False, "error": "webhook_url missing"}

    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": f"Meeting ready: {title[:150]}"},
        },
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": (summary or "_No summary_")[:2900]},
        },
    ]
    if action_items:
        lines = []
        for a in action_items[:10]:
            if isinstance(a, dict):
                lines.append(f"• {a.get('what', '')} ({a.get('who') or 'unassigned'})")
            else:
                lines.append(f"• {a}")
        blocks.append(
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": "*Action items*\n" + "\n".join(lines)},
            }
        )
    blocks.append(
        {
            "type": "context",
            "elements": [{"type": "mrkdwn", "text": f"Meeting ID: `{meeting_id}`"}],
        }
    )

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(webhook_url, json={"blocks": blocks})
            ok = resp.status_code < 300
            logger.info("slack_notify", status=resp.status_code, ok=ok)
            return {"ok": ok, "status_code": resp.status_code}
    except Exception as e:
        logger.error("slack_notify_failed", error=str(e))
        return {"ok": False, "error": str(e)}


async def export_to_notion(
    token: str,
    database_id: str,
    *,
    title: str,
    summary: str | None,
    topics: list[str] | None = None,
    meeting_id: str,
) -> dict[str, Any]:
    if not token or not database_id:
        return {"ok": False, "error": "token or database_id missing"}

    props = {"Name": {"title": [{"text": {"content": title[:200]}}]}}
    children = [
        {
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [{"type": "text", "text": {"content": (summary or "")[:2000]}}]
            },
        }
    ]
    if topics:
        children.append(
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {"content": "Topics: " + ", ".join(topics[:20])},
                        }
                    ]
                },
            }
        )

    body = {"parent": {"database_id": database_id}, "properties": props, "children": children}

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post(
                "https://api.notion.com/v1/pages",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Notion-Version": "2022-06-28",
                    "Content-Type": "application/json",
                },
                json=body,
            )
            ok = resp.status_code < 300
            data = resp.json() if resp.content else {}
            return {"ok": ok, "status_code": resp.status_code, "page_id": data.get("id")}
    except Exception as e:
        logger.error("notion_export_failed", error=str(e))
        return {"ok": False, "error": str(e)}


async def send_generic_webhook(url: str, payload: dict[str, Any]) -> dict[str, Any]:
    if not url:
        return {"ok": False, "error": "url missing"}
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(url, json=payload)
            return {"ok": resp.status_code < 300, "status_code": resp.status_code}
    except Exception as e:
        return {"ok": False, "error": str(e)}

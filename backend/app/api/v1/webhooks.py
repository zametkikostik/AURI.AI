"""Inbound webhooks: Zoom / Google / Teams."""

from __future__ import annotations

import hashlib
import hmac
import json
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from fastapi.responses import PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db
from app.core.logging import get_logger

router = APIRouter()
logger = get_logger(__name__)
settings = get_settings()


def _verify_hmac(secret: str, body: bytes, signature: str | None) -> bool:
    if not secret or not signature:
        return False
    digest = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    sig = signature.removeprefix("sha256=")
    return hmac.compare_digest(digest, sig)


@router.post("/zoom")
async def zoom_webhook(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    x_zm_signature: Annotated[str | None, Header()] = None,
    organization_id: Annotated[str | None, Query()] = None,
):
    body = await request.body()
    secret = settings.zoom_webhook_secret or ""
    if secret and not _verify_hmac(secret, body, x_zm_signature):
        raise HTTPException(status_code=401, detail="Invalid Zoom signature")

    try:
        payload: dict[str, Any] = json.loads(body.decode() or "{}")
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    event = payload.get("event") or payload.get("event_type") or "unknown"
    logger.info("zoom_webhook_received", event=event)

    if event == "endpoint.url_validation":
        plain = (payload.get("payload") or {}).get("plainToken", "")
        return {"plainToken": plain, "encryptedToken": plain}

    if event in ("recording.completed", "recording.transcript_completed"):
        if not organization_id:
            return {
                "ok": True,
                "event": event,
                "handled": False,
                "message": "Pass ?organization_id=<uuid> to auto-ingest recordings",
            }
        try:
            org_uuid = UUID(organization_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid organization_id")

        from app.services.zoom_pipeline import (
            handle_zoom_recording_completed,
            resolve_default_org_owner,
        )

        owner_id = await resolve_default_org_owner(db, org_uuid)
        if not owner_id:
            return {"ok": False, "error": "No active user in organization"}

        result = await handle_zoom_recording_completed(
            db,
            organization_id=org_uuid,
            owner_id=owner_id,
            payload=payload,
        )
        return {"ok": True, "event": event, "handled": True, **result}

    return {"ok": True, "event": event, "handled": False}


@router.post("/google")
async def google_webhook(request: Request, db: Annotated[AsyncSession, Depends(get_db)]):
    body = await request.body()
    try:
        payload = json.loads(body.decode() or "{}")
    except json.JSONDecodeError:
        payload = {}
    logger.info("google_webhook_received", keys=list(payload.keys())[:10])
    return {"ok": True, "handled": False, "message": "Stub: Google webhook accepted"}


@router.post("/teams")
async def teams_webhook(request: Request, db: Annotated[AsyncSession, Depends(get_db)]):
    body = await request.body()
    try:
        payload = json.loads(body.decode() or "{}")
    except json.JSONDecodeError:
        payload = {}

    token = request.query_params.get("validationToken")
    if token:
        return PlainTextResponse(content=token)

    logger.info("teams_webhook_received", keys=list(payload.keys())[:10])
    return {"ok": True, "handled": False, "message": "Stub: Teams webhook accepted"}

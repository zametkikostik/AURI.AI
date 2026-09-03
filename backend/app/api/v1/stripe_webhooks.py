"""Stripe webhook: checkout.session.completed → upgrade org plan."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.logging import get_logger
from app.models.user import Organization
from app.services.audit import write_audit
from app.services.stripe_billing import construct_webhook_event, stripe_configured

router = APIRouter()
logger = get_logger(__name__)


@router.post("/stripe")
async def stripe_webhook(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    if not stripe_configured():
        raise HTTPException(status_code=501, detail="Stripe not configured")

    payload = await request.body()
    sig = request.headers.get("stripe-signature")

    try:
        event = construct_webhook_event(payload, sig)
    except Exception as e:
        logger.warning("stripe_webhook_invalid", error=str(e))
        raise HTTPException(status_code=400, detail=str(e))

    etype = event.get("type") if isinstance(event, dict) else event["type"]
    data = event.get("data", {}).get("object", {}) if isinstance(event, dict) else event["data"]["object"]

    logger.info("stripe_webhook", type=etype)

    if etype == "checkout.session.completed":
        meta = data.get("metadata") or {}
        org_id = meta.get("organization_id") or data.get("client_reference_id")
        if not org_id:
            return {"ok": True, "handled": False, "reason": "no organization_id"}
        try:
            oid = UUID(str(org_id))
        except ValueError:
            return {"ok": False, "error": "invalid organization_id"}

        org = await db.get(Organization, oid)
        if not org:
            return {"ok": False, "error": "org not found"}

        org.plan = "enterprise"
        customer_id = data.get("customer")
        if customer_id:
            from sqlalchemy import select
            from app.models.settings import OrganizationSettings

            srow = (
                await db.execute(
                    select(OrganizationSettings).where(
                        OrganizationSettings.organization_id == oid
                    )
                )
            ).scalar_one_or_none()
            if not srow:
                srow = OrganizationSettings(organization_id=oid)
                db.add(srow)
                await db.flush()
            meta = dict(srow.meta or {})
            meta["stripe_customer_id"] = customer_id
            srow.meta = meta
        await write_audit(
            db,
            organization_id=oid,
            actor_id=None,
            action="billing.stripe_upgrade",
            resource_type="organization",
            resource_id=oid,
            meta={
                "session_id": data.get("id"),
                "customer_email": data.get("customer_email"),
                "customer": customer_id,
            },
        )
        await db.commit()
        logger.info("org_upgraded_via_stripe", org_id=str(oid))
        return {"ok": True, "handled": True, "plan": "enterprise"}

    return {"ok": True, "handled": False, "type": etype}

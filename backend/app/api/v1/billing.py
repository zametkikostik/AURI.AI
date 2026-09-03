"""Billing / plan usage endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import RequireAdmin, RequireViewer
from app.models.user import Organization
from app.services.billing import usage_snapshot
from app.services.stripe_billing import create_checkout_session, create_portal_session, stripe_configured

router = APIRouter()


@router.get("/usage")
async def get_usage(
    db: Annotated[AsyncSession, Depends(get_db)],
    ctx: RequireViewer,
):
    return await usage_snapshot(db, ctx.org_id)


@router.get("/plans")
async def list_plans():
    return {
        "plans": [
            {
                "id": "free",
                "name": "Free",
                "max_meetings": 5,
                "max_hours_per_month": 5,
                "max_members": 3,
                "sso": False,
            },
            {
                "id": "enterprise",
                "name": "Enterprise",
                "max_meetings": None,
                "max_hours_per_month": None,
                "max_members": None,
                "sso": True,
            },
        ]
    }


@router.post("/upgrade")
async def upgrade_to_enterprise(
    db: Annotated[AsyncSession, Depends(get_db)],
    ctx: RequireAdmin,
):
    org = await db.get(Organization, ctx.org_id)
    if not org:
        return {"ok": False, "error": "org not found"}

    if stripe_configured():
        return create_checkout_session(
            organization_id=ctx.org_id,
            customer_email=ctx.user.email,
        )

    org.plan = "enterprise"
    await db.commit()
    return {
        "ok": True,
        "plan": "enterprise",
        "message": "Upgraded without Stripe (dev fallback)",
        "checkout_url": None,
    }


@router.get("/stripe/status")
async def stripe_status():
    return {"configured": stripe_configured()}


@router.post("/portal")
async def customer_portal(
    db: Annotated[AsyncSession, Depends(get_db)],
    ctx: RequireAdmin,
):
    org = await db.get(Organization, ctx.org_id)
    if not org:
        return {"ok": False, "error": "org not found"}
    customer_id = None
    from sqlalchemy import select
    from app.models.settings import OrganizationSettings

    row = (
        await db.execute(
            select(OrganizationSettings).where(
                OrganizationSettings.organization_id == ctx.org_id
            )
        )
    ).scalar_one_or_none()
    if row and row.meta:
        customer_id = (row.meta or {}).get("stripe_customer_id")
    if not customer_id:
        return {
            "ok": False,
            "error": "No Stripe customer linked. Complete checkout first.",
            "url": None,
        }
    return create_portal_session(customer_id=customer_id)

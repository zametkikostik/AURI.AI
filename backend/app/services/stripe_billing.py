"""Stripe Checkout for Enterprise upgrades."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()


def stripe_configured() -> bool:
    return bool(
        getattr(settings, "stripe_secret_key", None)
        and getattr(settings, "stripe_price_enterprise", None)
    )


def create_checkout_session(
    *,
    organization_id: UUID,
    customer_email: str | None = None,
    success_path: str = "/settings?upgrade=success",
    cancel_path: str = "/settings?upgrade=cancel",
) -> dict[str, Any]:
    if not stripe_configured():
        return {"ok": False, "error": "Stripe not configured", "checkout_url": None}

    import stripe

    stripe.api_key = settings.stripe_secret_key
    frontend = getattr(settings, "frontend_url", None) or "http://localhost:3000"
    price = settings.stripe_price_enterprise

    session = stripe.checkout.Session.create(
        mode="subscription",
        line_items=[{"price": price, "quantity": 1}],
        success_url=f"{frontend.rstrip('/')}{success_path}&session_id={{CHECKOUT_SESSION_ID}}",
        cancel_url=f"{frontend.rstrip('/')}{cancel_path}",
        customer_email=customer_email,
        metadata={"organization_id": str(organization_id), "plan": "enterprise"},
        client_reference_id=str(organization_id),
    )
    logger.info("stripe_checkout_created", session_id=session.id, org=str(organization_id))
    return {"ok": True, "session_id": session.id, "checkout_url": session.url}


def construct_webhook_event(payload: bytes, sig_header: str | None):
    import stripe

    secret = getattr(settings, "stripe_webhook_secret", None)
    if not secret:
        raise ValueError("STRIPE_WEBHOOK_SECRET not set")
    return stripe.Webhook.construct_event(payload, sig_header or "", secret)


def create_portal_session(*, customer_id: str, return_path: str = "/settings") -> dict:
    if not stripe_configured():
        return {"ok": False, "error": "Stripe not configured", "url": None}
    import stripe

    stripe.api_key = settings.stripe_secret_key
    frontend = getattr(settings, "frontend_url", None) or "http://localhost:3000"
    session = stripe.billing_portal.Session.create(
        customer=customer_id,
        return_url=f"{frontend.rstrip('/')}{return_path}",
    )
    return {"ok": True, "url": session.url}

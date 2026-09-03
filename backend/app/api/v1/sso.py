"""SSO stubs: Google / Microsoft / Okta OIDC."""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core.deps import RequireAdmin

router = APIRouter()

Provider = Literal["google", "microsoft", "okta"]


class SSOStatus(BaseModel):
    provider: Provider
    configured: bool
    authorize_url: str | None = None
    message: str


@router.get("/providers")
async def list_sso_providers(ctx: RequireAdmin):
    providers = []
    for p in ("google", "microsoft", "okta"):
        providers.append(
            {
                "provider": p,
                "configured": False,
                "message": "Ready for OIDC setup",
            }
        )
    return {"providers": providers}


@router.get("/{provider}/start")
async def sso_start(provider: Provider, ctx: RequireAdmin):
    raise HTTPException(
        status_code=501,
        detail=f"{provider} SSO not configured. Set client id/secret in environment.",
    )

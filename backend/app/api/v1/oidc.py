"""OIDC / SSO flows for Google, Microsoft, Okta."""

from __future__ import annotations

import secrets
from typing import Annotated, Any, Literal
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import get_settings
from app.core.database import get_db
from app.core.security import create_access_token, create_refresh_token
from app.models.user import User
from app.services.audit import write_audit

router = APIRouter()
settings = get_settings()

Provider = Literal["google", "microsoft", "okta"]
_states: dict[str, dict[str, Any]] = {}


def _client_config(provider: Provider) -> dict[str, str] | None:
    if provider == "google":
        cid = getattr(settings, "google_oidc_client_id", None) or getattr(settings, "google_api_key", None)
        secret = getattr(settings, "google_oidc_client_secret", None)
        if not cid or not secret:
            return None
        return {
            "client_id": cid,
            "client_secret": secret,
            "authorize_url": "https://accounts.google.com/o/oauth2/v2/auth",
            "token_url": "https://oauth2.googleapis.com/token",
            "userinfo_url": "https://openidconnect.googleapis.com/v1/userinfo",
            "scope": "openid email profile",
        }
    if provider == "microsoft":
        cid = getattr(settings, "microsoft_oidc_client_id", None)
        secret = getattr(settings, "microsoft_oidc_client_secret", None)
        if not cid or not secret:
            return None
        tenant = getattr(settings, "microsoft_oidc_tenant", None) or "common"
        return {
            "client_id": cid,
            "client_secret": secret,
            "authorize_url": f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/authorize",
            "token_url": f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token",
            "userinfo_url": "https://graph.microsoft.com/oidc/userinfo",
            "scope": "openid email profile User.Read",
        }
    if provider == "okta":
        cid = getattr(settings, "okta_oidc_client_id", None)
        secret = getattr(settings, "okta_oidc_client_secret", None)
        domain = getattr(settings, "okta_domain", None)
        if not cid or not secret or not domain:
            return None
        base = f"https://{domain.rstrip('/')}"
        return {
            "client_id": cid,
            "client_secret": secret,
            "authorize_url": f"{base}/oauth2/v1/authorize",
            "token_url": f"{base}/oauth2/v1/token",
            "userinfo_url": f"{base}/oauth2/v1/userinfo",
            "scope": "openid email profile",
        }
    return None


def _redirect_uri(provider: Provider) -> str:
    base = getattr(settings, "oidc_redirect_base", None) or "http://localhost:8000"
    return f"{base.rstrip('/')}/api/v1/oidc/{provider}/callback"


@router.get("/{provider}/start")
async def oidc_start(provider: Provider):
    cfg = _client_config(provider)
    if not cfg:
        raise HTTPException(
            status_code=501,
            detail=f"{provider} OIDC not configured. Set client id/secret in environment.",
        )
    state = secrets.token_urlsafe(24)
    _states[state] = {"provider": provider}
    params = {
        "client_id": cfg["client_id"],
        "response_type": "code",
        "redirect_uri": _redirect_uri(provider),
        "scope": cfg["scope"],
        "state": state,
        "access_type": "online",
        "prompt": "select_account",
    }
    url = f"{cfg['authorize_url']}?{urlencode(params)}"
    return {"authorize_url": url, "state": state}


@router.get("/{provider}/callback")
async def oidc_callback(
    provider: Provider,
    db: Annotated[AsyncSession, Depends(get_db)],
    code: str = Query(...),
    state: str = Query(...),
):
    meta = _states.pop(state, None)
    if not meta or meta.get("provider") != provider:
        raise HTTPException(status_code=400, detail="Invalid state")

    cfg = _client_config(provider)
    if not cfg:
        raise HTTPException(status_code=501, detail="Provider not configured")

    async with httpx.AsyncClient(timeout=20.0) as client:
        token_resp = await client.post(
            cfg["token_url"],
            data={
                "code": code,
                "client_id": cfg["client_id"],
                "client_secret": cfg["client_secret"],
                "redirect_uri": _redirect_uri(provider),
                "grant_type": "authorization_code",
            },
            headers={"Accept": "application/json"},
        )
        if token_resp.status_code >= 300:
            raise HTTPException(status_code=400, detail="Token exchange failed")
        tokens = token_resp.json()
        access = tokens.get("access_token")
        if not access:
            raise HTTPException(status_code=400, detail="No access_token")

        ui = await client.get(
            cfg["userinfo_url"],
            headers={"Authorization": f"Bearer {access}"},
        )
        if ui.status_code >= 300:
            raise HTTPException(status_code=400, detail="Userinfo failed")
        info = ui.json()

    email = (info.get("email") or "").lower()
    if not email:
        raise HTTPException(status_code=400, detail="Email not provided by IdP")

    result = await db.execute(
        select(User)
        .where(User.email == email, User.is_active.is_(True))
        .options(selectinload(User.organization))
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=403,
            detail="No account for this email. Accept an invite or register first.",
        )

    user.sso_provider = provider
    user.sso_subject = str(info.get("sub") or info.get("id") or "")
    await write_audit(
        db,
        organization_id=user.organization_id,
        actor_id=user.id,
        action="auth.sso_login",
        resource_type="user",
        resource_id=user.id,
        meta={"provider": provider},
    )
    await db.commit()

    jwt_access = create_access_token(str(user.id))
    jwt_refresh = create_refresh_token(str(user.id))
    frontend = getattr(settings, "frontend_url", None) or "http://localhost:3000"
    return RedirectResponse(
        f"{frontend.rstrip('/')}/login#access_token={jwt_access}&refresh_token={jwt_refresh}"
    )


@router.get("/status")
async def oidc_status():
    return {
        "google": _client_config("google") is not None,
        "microsoft": _client_config("microsoft") is not None,
        "okta": _client_config("okta") is not None,
    }

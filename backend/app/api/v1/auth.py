"""Auth endpoints: register, login, me."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import CurrentUser
from app.schemas.auth import (
    LoginRequest,
    MeResponse,
    OrganizationOut,
    RegisterRequest,
    TokenResponse,
    UserOut,
)
from app.services.auth import AuthService

router = APIRouter()


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    body: RegisterRequest,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    service = AuthService(db)
    try:
        user, org, access, refresh = await service.register(
            body, ip=request.client.host if request.client else None
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return TokenResponse(access_token=access, refresh_token=refresh)


@router.post("/login", response_model=TokenResponse)
async def login(
    body: LoginRequest,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    service = AuthService(db)
    try:
        user, org, access, refresh = await service.login(
            email=body.email,
            password=body.password,
            ip=request.client.host if request.client else None,
            ua=request.headers.get("user-agent"),
        )
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    return TokenResponse(access_token=access, refresh_token=refresh)


@router.get("/me", response_model=MeResponse)
async def me(ctx: CurrentUser):
    return MeResponse(
        user=UserOut.model_validate(ctx.user),
        organization=OrganizationOut.model_validate(ctx.organization),
    )

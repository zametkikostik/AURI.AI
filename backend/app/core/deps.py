"""FastAPI dependencies: auth, RBAC, current user/org."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.security import decode_token
from app.models.user import Organization, User

security = HTTPBearer(auto_error=False)


class CurrentContext:
    def __init__(self, user: User, organization: Organization) -> None:
        self.user = user
        self.organization = organization

    @property
    def user_id(self) -> uuid.UUID:
        return self.user.id

    @property
    def org_id(self) -> uuid.UUID:
        return self.organization.id

    @property
    def role(self) -> str:
        return self.user.role


async def get_current_context(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
) -> CurrentContext:
    if creds is None or not creds.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_token(creds.credentials)
    if not payload or payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    sub = payload.get("sub")
    if not sub:
        raise HTTPException(status_code=401, detail="Invalid token subject")

    try:
        user_id = uuid.UUID(sub)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid token subject")

    result = await db.execute(
        select(User)
        .where(User.id == user_id, User.is_active.is_(True))
        .options(selectinload(User.organization))
    )
    user = result.scalar_one_or_none()
    if not user or not user.organization or not user.organization.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")

    request.state.user_id = user.id
    request.state.org_id = user.organization_id
    request.state.role = user.role

    return CurrentContext(user=user, organization=user.organization)


def require_roles(*roles: str):
    allowed = set(roles)

    async def checker(
        ctx: Annotated[CurrentContext, Depends(get_current_context)],
    ) -> CurrentContext:
        if ctx.user.is_superuser:
            return ctx
        if ctx.role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires one of roles: {', '.join(sorted(allowed))}",
            )
        return ctx

    return checker


RequireAdmin = Annotated[CurrentContext, Depends(require_roles("admin"))]
RequireEditor = Annotated[CurrentContext, Depends(require_roles("admin", "editor"))]
RequireViewer = Annotated[
    CurrentContext, Depends(require_roles("admin", "editor", "viewer", "member"))
]
CurrentUser = Annotated[CurrentContext, Depends(get_current_context)]

"""Authentication service."""

from __future__ import annotations

import re
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.security import (
    create_access_token,
    create_refresh_token,
    get_password_hash,
    verify_password,
)
from app.models.user import Organization, User, Workspace
from app.schemas.auth import RegisterRequest
from app.services.audit import write_audit


def _slugify(name: str) -> str:
    s = name.lower().strip()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = s.strip("-")[:80]
    return s or f"org-{uuid.uuid4().hex[:8]}"


class AuthService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def register(self, data: RegisterRequest, ip: str | None = None):
        existing = await self.db.execute(
            select(User).where(User.email == data.email.lower())
        )
        if existing.scalar_one_or_none():
            raise ValueError("Email already registered")

        base_slug = _slugify(data.organization_name)
        slug = base_slug
        n = 1
        while True:
            clash = await self.db.execute(
                select(Organization).where(Organization.slug == slug)
            )
            if not clash.scalar_one_or_none():
                break
            n += 1
            slug = f"{base_slug}-{n}"

        org = Organization(
            name=data.organization_name,
            slug=slug,
            plan="free",
            ai_mode="strict_private",
        )
        self.db.add(org)
        await self.db.flush()

        user = User(
            email=data.email.lower(),
            hashed_password=get_password_hash(data.password),
            full_name=data.full_name,
            role="admin",
            organization_id=org.id,
            is_superuser=False,
        )
        self.db.add(user)

        ws = Workspace(
            name="Default",
            slug="default",
            organization_id=org.id,
        )
        self.db.add(ws)
        await self.db.flush()

        await write_audit(
            self.db,
            organization_id=org.id,
            actor_id=user.id,
            action="auth.register",
            resource_type="user",
            resource_id=user.id,
            ip_address=ip,
            meta={"email": user.email},
        )

        await self.db.commit()
        await self.db.refresh(user)
        await self.db.refresh(org)

        access = create_access_token(str(user.id))
        refresh = create_refresh_token(str(user.id))
        return user, org, access, refresh

    async def login(
        self, email: str, password: str, ip: str | None = None, ua: str | None = None
    ):
        result = await self.db.execute(
            select(User)
            .where(User.email == email.lower(), User.is_active.is_(True))
            .options(selectinload(User.organization))
        )
        user = result.scalar_one_or_none()
        if not user or not user.hashed_password:
            raise ValueError("Invalid credentials")
        if not verify_password(password, user.hashed_password):
            raise ValueError("Invalid credentials")
        if not user.organization or not user.organization.is_active:
            raise ValueError("Organization inactive")

        await write_audit(
            self.db,
            organization_id=user.organization_id,
            actor_id=user.id,
            action="auth.login",
            resource_type="user",
            resource_id=user.id,
            ip_address=ip,
            user_agent=ua,
        )
        await self.db.commit()

        access = create_access_token(str(user.id))
        refresh = create_refresh_token(str(user.id))
        return user, user.organization, access, refresh

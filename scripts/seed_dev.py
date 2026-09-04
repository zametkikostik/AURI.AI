"""Seed a development organization + user."""

from __future__ import annotations

import asyncio
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.core.database import AsyncSessionLocal, engine, Base
from app.core.security import get_password_hash
from app.models.user import Organization, User, Workspace

DEV_ORG_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
DEV_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000002")
DEV_WS_ID = uuid.UUID("00000000-0000-0000-0000-000000000003")


async def seed() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        if not await session.get(Organization, DEV_ORG_ID):
            session.add(
                Organization(
                    id=DEV_ORG_ID,
                    name="AURI Dev Org",
                    slug="auri-dev",
                    plan="enterprise",
                    ai_mode="strict_private",
                )
            )
            print("Created organization")

        if not await session.get(User, DEV_USER_ID):
            session.add(
                User(
                    id=DEV_USER_ID,
                    email="dev@auri.ai",
                    hashed_password=get_password_hash("devpassword123"),
                    full_name="Dev User",
                    role="admin",
                    organization_id=DEV_ORG_ID,
                    is_superuser=True,
                )
            )
            print("Created user: dev@auri.ai / devpassword123")

        if not await session.get(Workspace, DEV_WS_ID):
            session.add(
                Workspace(
                    id=DEV_WS_ID,
                    name="Default Workspace",
                    slug="default",
                    organization_id=DEV_ORG_ID,
                )
            )
            print("Created workspace")

        await session.commit()
        print("Seed complete.")


if __name__ == "__main__":
    asyncio.run(seed())

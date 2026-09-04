"""Lightweight E2E-style API tests."""

from __future__ import annotations

import os
import uuid
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

os.environ.setdefault("APP_ENV", "development")
os.environ.setdefault("AI_MODE", "strict_private")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-jwt-please-change")
os.environ.setdefault(
    "DATABASE_URL",
    os.environ.get("TEST_DATABASE_URL", "postgresql+asyncpg://auri:auri_secret@localhost:5432/auri"),
)


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.asyncio
async def test_health():
    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        with patch("app.main.check_ollama_health", new=AsyncMock(return_value={"status": "ok"})):
            r = await client.get("/health")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "ok"


@pytest.mark.asyncio
async def test_plan_limits_logic():
    from app.services.billing import PLANS, get_plan

    free = get_plan("free")
    ent = get_plan("enterprise")
    assert free.max_meetings == 5
    assert ent.max_meetings is None
    assert "free" in PLANS and "enterprise" in PLANS


@pytest.mark.asyncio
async def test_chunking():
    from app.services.chunking import chunk_transcript

    text = "First sentence. Second sentence. " * 40
    chunks = chunk_transcript(text, max_chars=200, overlap_chars=20)
    assert len(chunks) >= 2
    assert all(c["text"] for c in chunks)

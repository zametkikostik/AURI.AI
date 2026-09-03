"""Meeting bot integration stubs (Zoom / Google Meet / MS Teams)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any

from app.core.logging import get_logger

logger = get_logger(__name__)


class BotPlatform(str, Enum):
    ZOOM = "zoom"
    GOOGLE_MEET = "gmeet"
    TEAMS = "teams"


@dataclass
class BotJoinRequest:
    meeting_url: str
    external_id: str | None = None
    title: str | None = None
    scheduled_at: str | None = None
    organization_id: str | None = None


@dataclass
class BotJoinResult:
    success: bool
    platform: BotPlatform
    bot_session_id: str | None = None
    message: str = ""
    raw: dict[str, Any] | None = None


class BaseMeetingBot(ABC):
    platform: BotPlatform

    @abstractmethod
    async def join(self, req: BotJoinRequest) -> BotJoinResult:
        ...

    @abstractmethod
    async def leave(self, bot_session_id: str) -> bool:
        ...


class ZoomBot(BaseMeetingBot):
    platform = BotPlatform.ZOOM

    async def join(self, req: BotJoinRequest) -> BotJoinResult:
        logger.info("zoom_bot_join_stub", url=req.meeting_url)
        return BotJoinResult(
            success=False,
            platform=self.platform,
            message="Zoom bot not configured. Set ZOOM_ACCOUNT_ID / ZOOM_CLIENT_ID / ZOOM_CLIENT_SECRET.",
        )

    async def leave(self, bot_session_id: str) -> bool:
        return False


class GoogleMeetBot(BaseMeetingBot):
    platform = BotPlatform.GOOGLE_MEET

    async def join(self, req: BotJoinRequest) -> BotJoinResult:
        logger.info("gmeet_bot_join_stub", url=req.meeting_url)
        return BotJoinResult(
            success=False,
            platform=self.platform,
            message="Google Meet bot not configured. Set GOOGLE_SERVICE_ACCOUNT_JSON.",
        )

    async def leave(self, bot_session_id: str) -> bool:
        return False


class TeamsBot(BaseMeetingBot):
    platform = BotPlatform.TEAMS

    async def join(self, req: BotJoinRequest) -> BotJoinResult:
        logger.info("teams_bot_join_stub", url=req.meeting_url)
        return BotJoinResult(
            success=False,
            platform=self.platform,
            message="Teams bot not configured. Set AZURE_BOT_APP_ID / AZURE_BOT_PASSWORD.",
        )

    async def leave(self, bot_session_id: str) -> bool:
        return False


def get_bot(platform: BotPlatform | str) -> BaseMeetingBot:
    p = BotPlatform(platform) if isinstance(platform, str) else platform
    mapping = {
        BotPlatform.ZOOM: ZoomBot,
        BotPlatform.GOOGLE_MEET: GoogleMeetBot,
        BotPlatform.TEAMS: TeamsBot,
    }
    return mapping[p]()

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class OrgSettingsUpdate(BaseModel):
    ai_mode: str | None = Field(None, pattern="^(strict_private|hybrid|cloud)$")
    slack_webhook_url: str | None = None
    notion_token: str | None = None
    notion_database_id: str | None = None
    zapier_webhook_url: str | None = None
    notify_on_ready: bool | None = None
    notify_slack: bool | None = None
    notify_notion: bool | None = None


class OrgSettingsOut(BaseModel):
    id: UUID
    organization_id: UUID
    ai_mode: str
    slack_webhook_configured: bool
    notion_configured: bool
    zapier_configured: bool
    notify_on_ready: bool
    notify_slack: bool
    notify_notion: bool
    slack_webhook_hint: str | None = None
    updated_at: datetime

    model_config = {"from_attributes": True}

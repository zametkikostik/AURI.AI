"""Per-organization integration settings."""

import uuid

from sqlalchemy import Boolean, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin


class OrganizationSettings(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "organization_settings"
    __table_args__ = (
        UniqueConstraint("organization_id", name="uq_org_settings_org"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    ai_mode: Mapped[str] = mapped_column(String(30), default="strict_private")

    slack_webhook_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    notion_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    notion_database_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    zapier_webhook_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    notify_on_ready: Mapped[bool] = mapped_column(Boolean, default=True)
    notify_slack: Mapped[bool] = mapped_column(Boolean, default=False)
    notify_notion: Mapped[bool] = mapped_column(Boolean, default=False)

    meta: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

"""organization_settings

Revision ID: 004
Revises: 003
Create Date: 2026-09-03
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "organization_settings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("ai_mode", sa.String(30), server_default="strict_private"),
        sa.Column("slack_webhook_url", sa.Text(), nullable=True),
        sa.Column("notion_token", sa.Text(), nullable=True),
        sa.Column("notion_database_id", sa.String(128), nullable=True),
        sa.Column("zapier_webhook_url", sa.Text(), nullable=True),
        sa.Column("notify_on_ready", sa.Boolean(), server_default="true"),
        sa.Column("notify_slack", sa.Boolean(), server_default="false"),
        sa.Column("notify_notion", sa.Boolean(), server_default="false"),
        sa.Column("meta", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("organization_id", name="uq_org_settings_org"),
    )
    op.create_index("ix_organization_settings_organization_id", "organization_settings", ["organization_id"])


def downgrade() -> None:
    op.drop_table("organization_settings")

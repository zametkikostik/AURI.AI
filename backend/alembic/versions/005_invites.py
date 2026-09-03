"""invites table

Revision ID: 005
Revises: 004
Create Date: 2026-09-03
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "invites",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("role", sa.String(50), server_default="member"),
        sa.Column("token", sa.String(64), nullable=False),
        sa.Column("invited_by_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(20), server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("organization_id", "email", name="uq_invite_org_email"),
        sa.UniqueConstraint("token", name="uq_invite_token"),
    )
    op.create_index("ix_invites_organization_id", "invites", ["organization_id"])
    op.create_index("ix_invites_email", "invites", ["email"])
    op.create_index("ix_invites_token", "invites", ["token"])
    op.create_index("ix_invites_status", "invites", ["status"])


def downgrade() -> None:
    op.drop_table("invites")

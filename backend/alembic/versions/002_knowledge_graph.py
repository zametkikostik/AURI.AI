"""knowledge entities and relations

Revision ID: 002
Revises: 001
Create Date: 2026-09-03
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "knowledge_entities",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("entity_type", sa.String(50), nullable=False),
        sa.Column("canonical_name", sa.String(500), nullable=False),
        sa.Column("display_name", sa.String(500), nullable=True),
        sa.Column("meta", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("organization_id", "entity_type", "canonical_name", name="uq_entity_org_type_name"),
    )
    op.create_index("ix_knowledge_entities_organization_id", "knowledge_entities", ["organization_id"])
    op.create_index("ix_knowledge_entities_entity_type", "knowledge_entities", ["entity_type"])

    op.create_table(
        "knowledge_relations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("from_entity_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("knowledge_entities.id", ondelete="CASCADE"), nullable=False),
        sa.Column("to_entity_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("knowledge_entities.id", ondelete="CASCADE"), nullable=False),
        sa.Column("relation_type", sa.String(50), nullable=False),
        sa.Column("meeting_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("meetings.id", ondelete="SET NULL"), nullable=True),
        sa.Column("evidence", sa.Text(), nullable=True),
        sa.Column("meta", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_knowledge_relations_organization_id", "knowledge_relations", ["organization_id"])
    op.create_index("ix_knowledge_relations_from_entity_id", "knowledge_relations", ["from_entity_id"])
    op.create_index("ix_knowledge_relations_to_entity_id", "knowledge_relations", ["to_entity_id"])
    op.create_index("ix_knowledge_relations_meeting_id", "knowledge_relations", ["meeting_id"])


def downgrade() -> None:
    op.drop_table("knowledge_relations")
    op.drop_table("knowledge_entities")

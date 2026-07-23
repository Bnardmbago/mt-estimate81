"""Add proposals and proposal_exports tables.

Revision ID: 032_proposals
Revises: 031_timeline_planning_field
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "032_proposals"
down_revision: Union[str, None] = "031_timeline_planning_field"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "proposals",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("estimate_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("estimates.id", ondelete="CASCADE"), nullable=False),
        sa.Column("locale", sa.String(length=2), nullable=False, server_default="en"),
        sa.Column("include_poc", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="draft"),
        sa.Column("source_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("assessment", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("proposal_body", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("poc", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("diagrams", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("milestones", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("generation_meta", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("source_fingerprint", sa.String(length=128), nullable=False, server_default=""),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("finalized_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("estimate_id", "locale", name="uq_proposals_estimate_locale"),
    )
    op.create_index("ix_proposals_estimate_id", "proposals", ["estimate_id"])

    op.create_table(
        "proposal_exports",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("proposal_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("proposals.id", ondelete="CASCADE"), nullable=False),
        sa.Column("format", sa.String(length=16), nullable=False),
        sa.Column("variant", sa.String(length=16), nullable=False, server_default="full"),
        sa.Column("storage_path", sa.String(length=1024), nullable=False),
        sa.Column("locale", sa.String(length=2), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("generated_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("generated_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
    )
    op.create_index("ix_proposal_exports_proposal_id", "proposal_exports", ["proposal_id"])


def downgrade() -> None:
    op.drop_index("ix_proposal_exports_proposal_id", table_name="proposal_exports")
    op.drop_table("proposal_exports")
    op.drop_index("ix_proposals_estimate_id", table_name="proposals")
    op.drop_table("proposals")

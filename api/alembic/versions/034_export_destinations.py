"""Add export destination metadata and oauth_connections.

Revision ID: 034_export_destinations
Revises: 033_presentation_presets
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "034_export_destinations"
down_revision: Union[str, None] = "033_presentation_presets"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "oauth_connections",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("access_token", sa.Text(), nullable=False),
        sa.Column("refresh_token", sa.Text(), nullable=True),
        sa.Column("token_expires_at", sa.DateTime(), nullable=True),
        sa.Column("scopes", sa.String(length=1024), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "provider", name="uq_oauth_connections_user_provider"),
    )
    op.create_index("ix_oauth_connections_user_id", "oauth_connections", ["user_id"])

    for table in ("exports", "proposal_exports"):
        op.add_column(table, sa.Column("destination", sa.String(length=32), nullable=True))
        op.add_column(table, sa.Column("external_file_id", sa.String(length=255), nullable=True))
        op.add_column(table, sa.Column("external_url", sa.String(length=2048), nullable=True))
        op.add_column(table, sa.Column("manually_edited_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    for table in ("exports", "proposal_exports"):
        op.drop_column(table, "manually_edited_at")
        op.drop_column(table, "external_url")
        op.drop_column(table, "external_file_id")
        op.drop_column(table, "destination")

    op.drop_index("ix_oauth_connections_user_id", table_name="oauth_connections")
    op.drop_table("oauth_connections")

"""Re-add OAuth connections and app credential columns (undo 036).

Revision ID: 038_restore_oauth_destinations
Revises: 037_proposal_ai_settings
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "038_restore_oauth_destinations"
down_revision: Union[str, None] = "037_proposal_ai_settings"
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

    op.add_column("system_config", sa.Column("google_oauth_client_id", sa.String(length=255), nullable=True))
    op.add_column("system_config", sa.Column("google_oauth_client_secret", sa.String(length=255), nullable=True))
    op.add_column("system_config", sa.Column("google_oauth_redirect_uri", sa.String(length=512), nullable=True))
    op.add_column("system_config", sa.Column("canva_client_id", sa.String(length=255), nullable=True))
    op.add_column("system_config", sa.Column("canva_client_secret", sa.String(length=255), nullable=True))
    op.add_column("system_config", sa.Column("canva_redirect_uri", sa.String(length=512), nullable=True))
    op.add_column("system_config", sa.Column("canva_template_proposal_en", sa.String(length=128), nullable=True))
    op.add_column("system_config", sa.Column("canva_template_proposal_ja", sa.String(length=128), nullable=True))
    op.add_column("system_config", sa.Column("canva_template_poc_en", sa.String(length=128), nullable=True))
    op.add_column("system_config", sa.Column("canva_template_poc_ja", sa.String(length=128), nullable=True))


def downgrade() -> None:
    op.drop_column("system_config", "canva_template_poc_ja")
    op.drop_column("system_config", "canva_template_poc_en")
    op.drop_column("system_config", "canva_template_proposal_ja")
    op.drop_column("system_config", "canva_template_proposal_en")
    op.drop_column("system_config", "canva_redirect_uri")
    op.drop_column("system_config", "canva_client_secret")
    op.drop_column("system_config", "canva_client_id")
    op.drop_column("system_config", "google_oauth_redirect_uri")
    op.drop_column("system_config", "google_oauth_client_secret")
    op.drop_column("system_config", "google_oauth_client_id")

    op.drop_index("ix_oauth_connections_user_id", table_name="oauth_connections")
    op.drop_table("oauth_connections")

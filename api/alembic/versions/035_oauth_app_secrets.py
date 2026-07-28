"""Add OAuth app credential columns to system_config.

Revision ID: 035_oauth_app_secrets
Revises: 034_export_destinations
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "035_oauth_app_secrets"
down_revision: Union[str, None] = "034_export_destinations"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
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

"""Add SMTP settings to system_config

Revision ID: 011_smtp_settings
Revises: 010_user_admin_fields
Create Date: 2026-06-08
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "011_smtp_settings"
down_revision: Union[str, None] = "010_user_admin_fields"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("system_config", sa.Column("smtp_host", sa.String(length=255), nullable=True))
    op.add_column("system_config", sa.Column("smtp_port", sa.Integer(), nullable=True))
    op.add_column("system_config", sa.Column("smtp_user", sa.String(length=255), nullable=True))
    op.add_column("system_config", sa.Column("smtp_password", sa.String(length=255), nullable=True))
    op.add_column("system_config", sa.Column("smtp_from", sa.String(length=255), nullable=True))
    op.add_column("system_config", sa.Column("smtp_use_tls", sa.Boolean(), nullable=True))


def downgrade() -> None:
    op.drop_column("system_config", "smtp_use_tls")
    op.drop_column("system_config", "smtp_from")
    op.drop_column("system_config", "smtp_password")
    op.drop_column("system_config", "smtp_user")
    op.drop_column("system_config", "smtp_port")
    op.drop_column("system_config", "smtp_host")

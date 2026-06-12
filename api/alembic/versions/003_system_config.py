"""add system_config table

Revision ID: 003
Revises: 002
Create Date: 2026-06-07

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "system_config",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("ai_provider", sa.String(length=20), nullable=True),
        sa.Column("ai_model", sa.String(length=100), nullable=True),
        sa.Column("openai_api_key", sa.String(length=255), nullable=True),
        sa.Column("anthropic_api_key", sa.String(length=255), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("system_config")

"""Add ai_instruction_layers table for admin-configurable AI prompts.

Revision ID: 022_ai_instruction_layers
Revises: 021_japan_system_rc
Create Date: 2026-06-30
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "022_ai_instruction_layers"
down_revision: Union[str, None] = "021_japan_system_rc"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ai_instruction_layers",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("location", sa.String(length=50), nullable=False),
        sa.Column("locale", sa.String(length=2), nullable=False),
        sa.Column("system_prompt", sa.Text(), nullable=True),
        sa.Column("default_prompt", sa.Text(), nullable=True),
        sa.Column("user_prompt", sa.Text(), nullable=True),
        sa.Column("negative_prompt", sa.Text(), nullable=True),
        sa.Column("parameters", sa.JSON(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("location", "locale", name="uq_ai_instruction_layers_location_locale"),
    )


def downgrade() -> None:
    op.drop_table("ai_instruction_layers")

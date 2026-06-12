"""Add user is_active and preferred_currency

Revision ID: 010_user_admin_fields
Revises: 009_feature_item_localizations
Create Date: 2026-06-08
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "010_user_admin_fields"
down_revision: Union[str, None] = "009_feature_item_localizations"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
    )
    op.add_column(
        "users",
        sa.Column(
            "preferred_currency",
            sa.String(length=3),
            nullable=False,
            server_default="JPY",
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "preferred_currency")
    op.drop_column("users", "is_active")

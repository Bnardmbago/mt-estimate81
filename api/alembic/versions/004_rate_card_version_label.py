"""add rate card version label

Revision ID: 004
Revises: 003
Create Date: 2026-06-07

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "rate_card_versions",
        sa.Column("label", sa.String(length=255), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("rate_card_versions", "label")

"""Add estimate discount rate to system_config

Revision ID: 012_estimate_discount_rate
Revises: 011_smtp_settings
Create Date: 2026-06-11
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "012_estimate_discount_rate"
down_revision: Union[str, None] = "011_smtp_settings"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "system_config",
        sa.Column("estimate_discount_rate", sa.Float(), nullable=True),
    )
    op.execute(
        "UPDATE system_config SET estimate_discount_rate = 0.30 WHERE id = 1"
    )


def downgrade() -> None:
    op.drop_column("system_config", "estimate_discount_rate")

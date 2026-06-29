"""Add estimate markup rate to system_config

Revision ID: 020_estimate_markup_rate
Revises: 019_contact_estimate_access
Create Date: 2026-06-29
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "020_estimate_markup_rate"
down_revision: Union[str, None] = "019_contact_estimate_access"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "system_config",
        sa.Column("estimate_markup_rate", sa.Float(), nullable=True),
    )
    op.execute(
        "UPDATE system_config SET estimate_markup_rate = 0.30 WHERE id = 1"
    )


def downgrade() -> None:
    op.drop_column("system_config", "estimate_markup_rate")

"""Add company_name to users

Revision ID: 013_user_company_name
Revises: 012_estimate_discount_rate
Create Date: 2026-06-11
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "013_user_company_name"
down_revision: Union[str, None] = "012_estimate_discount_rate"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("company_name", sa.String(length=255), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("users", "company_name")

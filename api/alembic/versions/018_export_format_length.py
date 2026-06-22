"""Widen exports.format for pdf_preliminary

Revision ID: 018_export_format_length
Revises: 017_fx_rates
Create Date: 2026-06-20
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "018_export_format_length"
down_revision: Union[str, None] = "017_fx_rates"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "exports",
        "format",
        existing_type=sa.String(length=10),
        type_=sa.String(length=20),
        existing_nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "exports",
        "format",
        existing_type=sa.String(length=20),
        type_=sa.String(length=10),
        existing_nullable=False,
    )

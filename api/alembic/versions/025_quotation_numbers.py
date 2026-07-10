"""Add quotation number fields for formal quotation exports.

Revision ID: 025_quotation_numbers
Revises: 024_rc_default_name
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "025_quotation_numbers"
down_revision: Union[str, None] = "024_rc_default_name"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "exports",
        "format",
        existing_type=sa.String(length=20),
        type_=sa.String(length=32),
        existing_nullable=False,
    )
    op.add_column("exports", sa.Column("quotation_number", sa.String(length=32), nullable=True))
    op.add_column("exports", sa.Column("registration_number", sa.String(length=32), nullable=True))

    op.add_column(
        "system_config",
        sa.Column("quotation_invoice_registration_number", sa.String(length=32), nullable=True),
    )
    op.add_column(
        "system_config",
        sa.Column("quotation_number_prefix", sa.String(length=10), server_default="BAI", nullable=False),
    )
    op.add_column(
        "system_config",
        sa.Column("quotation_number_date", sa.Date(), nullable=True),
    )
    op.add_column(
        "system_config",
        sa.Column(
            "quotation_number_sequence",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("system_config", "quotation_number_sequence")
    op.drop_column("system_config", "quotation_number_date")
    op.drop_column("system_config", "quotation_number_prefix")
    op.drop_column("system_config", "quotation_invoice_registration_number")
    op.drop_column("exports", "registration_number")
    op.drop_column("exports", "quotation_number")
    op.alter_column(
        "exports",
        "format",
        existing_type=sa.String(length=32),
        type_=sa.String(length=20),
        existing_nullable=False,
    )

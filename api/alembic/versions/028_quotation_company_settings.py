"""Add quotation company contact, bank, and logo settings.

Revision ID: 028_quotation_company_settings
Revises: 027_registration_number_sequence
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "028_quotation_company_settings"
down_revision: Union[str, None] = "027_registration_number_sequence"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "system_config",
        sa.Column("quotation_company_postal_code", sa.String(length=32), nullable=True),
    )
    op.add_column(
        "system_config",
        sa.Column("quotation_company_address", sa.Text(), nullable=True),
    )
    op.add_column(
        "system_config",
        sa.Column("quotation_company_tel", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "system_config",
        sa.Column("quotation_company_email", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "system_config",
        sa.Column("quotation_bank_details_ja", sa.Text(), nullable=True),
    )
    op.add_column(
        "system_config",
        sa.Column("quotation_bank_details_en", sa.Text(), nullable=True),
    )
    op.add_column(
        "system_config",
        sa.Column("quotation_logo_storage_path", sa.String(length=512), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("system_config", "quotation_logo_storage_path")
    op.drop_column("system_config", "quotation_bank_details_en")
    op.drop_column("system_config", "quotation_bank_details_ja")
    op.drop_column("system_config", "quotation_company_email")
    op.drop_column("system_config", "quotation_company_tel")
    op.drop_column("system_config", "quotation_company_address")
    op.drop_column("system_config", "quotation_company_postal_code")

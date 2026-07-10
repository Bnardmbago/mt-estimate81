"""Add quotation contact person to system_config.

Revision ID: 026_quotation_contact_person
Revises: 025_quotation_numbers
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "026_quotation_contact_person"
down_revision: Union[str, None] = "025_quotation_numbers"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "system_config",
        sa.Column("quotation_contact_person", sa.String(length=255), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("system_config", "quotation_contact_person")

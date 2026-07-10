"""Add auto-increment registration number sequence.

Revision ID: 027_registration_number_sequence
Revises: 026_quotation_contact_person
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "027_registration_number_sequence"
down_revision: Union[str, None] = "026_quotation_contact_person"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# First issued number will be T9010001234562.
DEFAULT_REGISTRATION_SEQUENCE = 9010001234561


def upgrade() -> None:
    op.add_column(
        "system_config",
        sa.Column(
            "registration_number_sequence",
            sa.BigInteger(),
            server_default=str(DEFAULT_REGISTRATION_SEQUENCE),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("system_config", "registration_number_sequence")

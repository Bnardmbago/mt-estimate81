"""Rename system rate cards to canonical default name.

Revision ID: 024_rc_default_name
Revises: 023_quotation_special_notes
"""

from typing import Sequence, Union

from alembic import op

revision: str = "024_rc_default_name"
down_revision: Union[str, None] = "023_quotation_special_notes"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE rate_cards
        SET name = 'Rate Card Default'
        WHERE is_system IS TRUE
        """
    )


def downgrade() -> None:
    pass

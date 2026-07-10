"""Add nrc_rc_assumptions to estimates.

Revision ID: 030_estimate_nrc_rc_assumptions
Revises: 029_questionnaire_field_updates
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "030_estimate_nrc_rc_assumptions"
down_revision: Union[str, None] = "029_questionnaire_field_updates"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "estimates",
        sa.Column("nrc_rc_assumptions", JSONB, nullable=False, server_default="{}"),
    )
    op.alter_column("estimates", "nrc_rc_assumptions", server_default=None)


def downgrade() -> None:
    op.drop_column("estimates", "nrc_rc_assumptions")

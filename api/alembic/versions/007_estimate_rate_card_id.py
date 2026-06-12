"""add estimate rate_card_id

Revision ID: 007
Revises: 006
Create Date: 2026-06-07

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "007"
down_revision: Union[str, None] = "006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "estimates",
        sa.Column("rate_card_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_estimates_rate_card_id",
        "estimates",
        "rate_cards",
        ["rate_card_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint("fk_estimates_rate_card_id", "estimates", type_="foreignkey")
    op.drop_column("estimates", "rate_card_id")

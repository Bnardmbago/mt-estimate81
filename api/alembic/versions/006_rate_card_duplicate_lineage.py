"""add rate card duplicate lineage

Revision ID: 006
Revises: 005
Create Date: 2026-06-07

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "006"
down_revision: Union[str, None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "rate_cards",
        sa.Column("duplicated_from_rate_card_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_rate_cards_duplicated_from",
        "rate_cards",
        "rate_cards",
        ["duplicated_from_rate_card_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint("fk_rate_cards_duplicated_from", "rate_cards", type_="foreignkey")
    op.drop_column("rate_cards", "duplicated_from_rate_card_id")

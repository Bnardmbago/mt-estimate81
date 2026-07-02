"""Add quotation special notes templates to system_config

Revision ID: 023_quotation_special_notes
Revises: 022_ai_instruction_layers
Create Date: 2026-07-02
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "023_quotation_special_notes"
down_revision: Union[str, None] = "022_ai_instruction_layers"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "system_config",
        sa.Column("quotation_special_notes_title_ja", sa.Text(), nullable=True),
    )
    op.add_column(
        "system_config",
        sa.Column("quotation_special_notes_title_en", sa.Text(), nullable=True),
    )
    op.add_column(
        "system_config",
        sa.Column("quotation_special_notes_body_ja", sa.Text(), nullable=True),
    )
    op.add_column(
        "system_config",
        sa.Column("quotation_special_notes_body_en", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("system_config", "quotation_special_notes_body_en")
    op.drop_column("system_config", "quotation_special_notes_body_ja")
    op.drop_column("system_config", "quotation_special_notes_title_en")
    op.drop_column("system_config", "quotation_special_notes_title_ja")

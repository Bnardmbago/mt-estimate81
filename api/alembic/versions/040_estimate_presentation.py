"""Add presentation presets and cover values to estimates.

Revision ID: 040_estimate_presentation
Revises: 039_presentation_drafts_cover
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "040_estimate_presentation"
down_revision: Union[str, None] = "039_presentation_drafts_cover"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("estimates", sa.Column("theme_id", sa.String(length=64), nullable=True))
    op.add_column("estimates", sa.Column("style_id", sa.String(length=64), nullable=True))
    op.add_column("estimates", sa.Column("template_id", sa.String(length=64), nullable=True))
    op.add_column(
        "estimates",
        sa.Column(
            "cover_values",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )


def downgrade() -> None:
    op.drop_column("estimates", "cover_values")
    op.drop_column("estimates", "template_id")
    op.drop_column("estimates", "style_id")
    op.drop_column("estimates", "theme_id")

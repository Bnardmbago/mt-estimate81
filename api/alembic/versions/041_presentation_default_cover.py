"""Add presentation default cover template id to system_config.

Revision ID: 041_presentation_default_cover
Revises: 040_estimate_presentation
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "041_presentation_default_cover"
down_revision: Union[str, None] = "040_estimate_presentation"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "system_config",
        sa.Column(
            "presentation_default_cover_template_id",
            sa.String(length=64),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("system_config", "presentation_default_cover_template_id")

"""backfill rate card development_approach in settings

Revision ID: 008
Revises: 007
Create Date: 2026-06-07

"""

from typing import Sequence, Union

from alembic import op

revision: str = "008"
down_revision: Union[str, None] = "007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE rate_card_versions
        SET settings = settings || '{"development_approach": "traditional"}'::jsonb
        WHERE settings->>'development_approach' IS NULL
           OR settings->>'development_approach' = ''
        """
    )


def downgrade() -> None:
    op.execute(
        """
        UPDATE rate_card_versions
        SET settings = settings - 'development_approach'
        WHERE settings ? 'development_approach'
        """
    )

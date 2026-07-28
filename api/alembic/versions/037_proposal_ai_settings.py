"""Add proposal_ai_settings JSONB to system_config.

Revision ID: 037_proposal_ai_settings
Revises: 036_drop_oauth_destinations
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "037_proposal_ai_settings"
down_revision: Union[str, None] = "036_drop_oauth_destinations"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "system_config",
        sa.Column(
            "proposal_ai_settings",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text(
                "'{\"assessment_purpose\": \"standard\", "
                "\"proposal_purpose\": \"detailed\", "
                "\"poc_purpose\": \"detailed\"}'::jsonb"
            ),
        ),
    )


def downgrade() -> None:
    op.drop_column("system_config", "proposal_ai_settings")

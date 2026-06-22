"""Add header questionnaire fields to default form template

Revision ID: 016_header_questionnaire
Revises: 015_template_categories
Create Date: 2026-06-19
"""

import json
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from app.estimates.form_fields import build_default_template_fields

revision: str = "016_header_questionnaire"
down_revision: Union[str, None] = "015_template_categories"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

DEFAULT_FIELDS_JSON = json.dumps(build_default_template_fields())


def upgrade() -> None:
    op.execute(
        sa.text(
            """
            UPDATE form_templates
            SET fields = CAST(:fields AS jsonb),
                updated_at = NOW()
            WHERE is_default = true
            """
        ).bindparams(fields=DEFAULT_FIELDS_JSON)
    )


def downgrade() -> None:
    pass

"""Update client questionnaire desired_system and usage_platform fields.

Revision ID: 029_questionnaire_field_updates
Revises: 028_quotation_company_settings
"""

import json
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from app.estimates.form_fields import build_default_template_fields

revision: str = "029_questionnaire_field_updates"
down_revision: Union[str, None] = "028_quotation_company_settings"
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

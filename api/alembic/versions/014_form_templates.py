"""Add form templates and estimate schema snapshots

Revision ID: 014_form_templates
Revises: 013_user_company_name
Create Date: 2026-06-19
"""

import json
import uuid
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from app.estimates.form_fields import build_default_template_fields

revision: str = "014_form_templates"
down_revision: Union[str, None] = "013_user_company_name"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

DEFAULT_TEMPLATE_ID = uuid.uuid4()
DEFAULT_FIELDS_JSON = json.dumps(build_default_template_fields())


def upgrade() -> None:
    op.create_table(
        "form_templates",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False, unique=True),
        sa.Column("description", sa.String(length=500), nullable=True),
        sa.Column("fields", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    op.add_column(
        "estimates",
        sa.Column("form_template_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "estimates",
        sa.Column(
            "form_schema_snapshot",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="[]",
        ),
    )
    op.create_foreign_key(
        "fk_estimates_form_template_id",
        "estimates",
        "form_templates",
        ["form_template_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.execute(
        sa.text(
            """
            INSERT INTO form_templates (id, name, description, fields, is_default, created_at, updated_at)
            VALUES (
                CAST(:id AS uuid),
                'Default questionnaire',
                'Standard 20-field project questionnaire',
                CAST(:fields AS jsonb),
                true,
                NOW(),
                NOW()
            )
            """
        ).bindparams(id=DEFAULT_TEMPLATE_ID, fields=DEFAULT_FIELDS_JSON)
    )

    op.execute(
        sa.text(
            """
            UPDATE estimates
            SET form_template_id = CAST(:template_id AS uuid),
                form_schema_snapshot = CAST(:fields AS jsonb)
            """
        ).bindparams(template_id=DEFAULT_TEMPLATE_ID, fields=DEFAULT_FIELDS_JSON)
    )


def downgrade() -> None:
    op.drop_constraint("fk_estimates_form_template_id", "estimates", type_="foreignkey")
    op.drop_column("estimates", "form_schema_snapshot")
    op.drop_column("estimates", "form_template_id")
    op.drop_table("form_templates")

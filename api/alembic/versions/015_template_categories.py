"""Add template nature-of-work and language categories

Revision ID: 015_template_categories
Revises: 014_form_templates
Create Date: 2026-06-19
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "015_template_categories"
down_revision: Union[str, None] = "014_form_templates"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "form_templates",
        sa.Column(
            "nature_of_work_category",
            sa.String(length=32),
            nullable=False,
            server_default="general",
        ),
    )
    op.add_column(
        "form_templates",
        sa.Column(
            "language",
            sa.String(length=8),
            nullable=False,
            server_default="both",
        ),
    )
    op.create_index(
        "ix_form_templates_category_language",
        "form_templates",
        ["nature_of_work_category", "language"],
    )


def downgrade() -> None:
    op.drop_index("ix_form_templates_category_language", table_name="form_templates")
    op.drop_column("form_templates", "language")
    op.drop_column("form_templates", "nature_of_work_category")

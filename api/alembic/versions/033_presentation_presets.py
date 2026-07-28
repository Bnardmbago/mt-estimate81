"""Add presentation Theme/Style/Template catalogs and Proposal presentation columns.

Revision ID: 033_presentation_presets
Revises: 032_proposals
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "033_presentation_presets"
down_revision: Union[str, None] = "032_proposals"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "presentation_themes",
        sa.Column("id", sa.String(length=64), primary_key=True, nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=True),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("config", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("logo_storage_path", sa.String(length=1024), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_table(
        "presentation_styles",
        sa.Column("id", sa.String(length=64), primary_key=True, nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=True),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("config", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_table(
        "presentation_templates",
        sa.Column("id", sa.String(length=64), primary_key=True, nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=True),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("config", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
    )

    op.add_column("proposals", sa.Column("theme_id", sa.String(length=64), nullable=True))
    op.add_column("proposals", sa.Column("style_id", sa.String(length=64), nullable=True))
    op.add_column("proposals", sa.Column("template_id", sa.String(length=64), nullable=True))
    op.add_column(
        "proposals",
        sa.Column(
            "presentation_meta",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )
    op.add_column("proposal_exports", sa.Column("theme_id", sa.String(length=64), nullable=True))
    op.add_column("proposal_exports", sa.Column("style_id", sa.String(length=64), nullable=True))
    op.add_column("proposal_exports", sa.Column("template_id", sa.String(length=64), nullable=True))

    # Seed via Python to keep configs in sync with app.presentation.seeds
    from app.presentation.seeds import SEED_STYLES, SEED_TEMPLATES, SEED_THEMES

    themes = sa.table(
        "presentation_themes",
        sa.column("id", sa.String),
        sa.column("name", sa.String),
        sa.column("description", sa.String),
        sa.column("is_default", sa.Boolean),
        sa.column("is_active", sa.Boolean),
        sa.column("config", postgresql.JSONB),
    )
    styles = sa.table(
        "presentation_styles",
        sa.column("id", sa.String),
        sa.column("name", sa.String),
        sa.column("description", sa.String),
        sa.column("is_default", sa.Boolean),
        sa.column("is_active", sa.Boolean),
        sa.column("config", postgresql.JSONB),
    )
    templates = sa.table(
        "presentation_templates",
        sa.column("id", sa.String),
        sa.column("name", sa.String),
        sa.column("description", sa.String),
        sa.column("is_default", sa.Boolean),
        sa.column("is_active", sa.Boolean),
        sa.column("config", postgresql.JSONB),
    )
    op.bulk_insert(
        themes,
        [
            {
                "id": row["id"],
                "name": row["name"],
                "description": row["description"],
                "is_default": row["is_default"],
                "is_active": row["is_active"],
                "config": row["config"],
            }
            for row in SEED_THEMES
        ],
    )
    op.bulk_insert(
        styles,
        [
            {
                "id": row["id"],
                "name": row["name"],
                "description": row["description"],
                "is_default": row["is_default"],
                "is_active": row["is_active"],
                "config": row["config"],
            }
            for row in SEED_STYLES
        ],
    )
    op.bulk_insert(
        templates,
        [
            {
                "id": row["id"],
                "name": row["name"],
                "description": row["description"],
                "is_default": row["is_default"],
                "is_active": row["is_active"],
                "config": row["config"],
            }
            for row in SEED_TEMPLATES
        ],
    )


def downgrade() -> None:
    op.drop_column("proposal_exports", "template_id")
    op.drop_column("proposal_exports", "style_id")
    op.drop_column("proposal_exports", "theme_id")
    op.drop_column("proposals", "presentation_meta")
    op.drop_column("proposals", "template_id")
    op.drop_column("proposals", "style_id")
    op.drop_column("proposals", "theme_id")
    op.drop_table("presentation_templates")
    op.drop_table("presentation_styles")
    op.drop_table("presentation_themes")

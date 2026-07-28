"""Add presentation preset drafts and proposal cover values.

Revision ID: 039_presentation_drafts_cover
Revises: 038_restore_oauth_destinations
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "039_presentation_drafts_cover"
down_revision: Union[str, None] = "038_restore_oauth_destinations"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "presentation_preset_drafts",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="draft"),
        sa.Column("source_locale", sa.String(length=2), nullable=False, server_default="en"),
        sa.Column(
            "theme_draft",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "style_draft",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "template_draft",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("target_theme_id", sa.String(length=64), nullable=True),
        sa.Column("target_style_id", sa.String(length=64), nullable=True),
        sa.Column("target_template_id", sa.String(length=64), nullable=True),
        sa.Column(
            "generation_meta",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "errors",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.Column(
            "expires_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("NOW() + INTERVAL '30 days'"),
        ),
        sa.ForeignKeyConstraint(
            ["target_style_id"],
            ["presentation_styles.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["target_template_id"],
            ["presentation_templates.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["target_theme_id"],
            ["presentation_themes.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.add_column(
        "proposals",
        sa.Column(
            "cover_values",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )


def downgrade() -> None:
    op.drop_column("proposals", "cover_values")
    op.drop_table("presentation_preset_drafts")

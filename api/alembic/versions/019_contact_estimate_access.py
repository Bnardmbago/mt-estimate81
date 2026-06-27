"""Contact estimate access: contact users, magic links, system rate cards

Revision ID: 019_contact_estimate_access
Revises: 018_export_format_length
Create Date: 2026-06-25
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "019_contact_estimate_access"
down_revision: Union[str, None] = "018_export_format_length"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("account_type", sa.String(length=20), nullable=False, server_default="full"),
    )
    op.add_column(
        "users",
        sa.Column("email_verified_at", sa.DateTime(), nullable=True),
    )
    op.alter_column(
        "users",
        "password_hash",
        existing_type=sa.String(length=255),
        nullable=True,
    )

    op.add_column(
        "rate_cards",
        sa.Column("is_system", sa.Boolean(), nullable=False, server_default=sa.false()),
    )

    op.create_table(
        "contact_magic_links",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("used_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("request_ip", sa.String(length=45), nullable=True),
    )
    op.create_index("ix_contact_magic_links_token_hash", "contact_magic_links", ["token_hash"])
    op.create_index("ix_contact_magic_links_user_id", "contact_magic_links", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_contact_magic_links_user_id", table_name="contact_magic_links")
    op.drop_index("ix_contact_magic_links_token_hash", table_name="contact_magic_links")
    op.drop_table("contact_magic_links")

    op.drop_column("rate_cards", "is_system")

    op.alter_column(
        "users",
        "password_hash",
        existing_type=sa.String(length=255),
        nullable=False,
    )
    op.drop_column("users", "email_verified_at")
    op.drop_column("users", "account_type")

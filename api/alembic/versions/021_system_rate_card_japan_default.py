"""Set system rate cards to Japan default region and standard hourly rates.

Revision ID: 021_japan_system_rc
Revises: 020_estimate_markup_rate
Create Date: 2026-06-29
"""

import json
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from app.rate_cards.standard_rates import patch_settings_standard_roles_for_region

revision: str = "021_japan_system_rc"
down_revision: Union[str, None] = "020_estimate_markup_rate"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    connection = op.get_bind()
    system_cards = connection.execute(
        sa.text("SELECT id FROM rate_cards WHERE is_system IS TRUE")
    ).fetchall()

    for (card_id,) in system_cards:
        version_row = connection.execute(
            sa.text(
                """
                SELECT id, settings
                FROM rate_card_versions
                WHERE rate_card_id = :card_id
                ORDER BY version_number DESC
                LIMIT 1
                """
            ),
            {"card_id": card_id},
        ).first()
        if version_row is None:
            continue

        settings = dict(version_row.settings or {})
        patched = patch_settings_standard_roles_for_region(
            settings,
            "japan",
            currency="JPY",
        )
        connection.execute(
            sa.text(
                """
                UPDATE rate_card_versions
                SET settings = CAST(:settings AS JSONB)
                WHERE id = :version_id
                """
            ),
            {
                "settings": json.dumps(patched),
                "version_id": version_row.id,
            },
        )


def downgrade() -> None:
    # Non-destructive: prior region/rates cannot be restored without a snapshot.
    pass

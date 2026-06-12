import uuid
from unittest.mock import AsyncMock, patch

import pytest

from app.estimates.rate_card_stale import (
    RATE_CARD_FINGERPRINT_KEY,
    get_stored_rate_card_fingerprint,
    is_rate_card_stale_for_estimate,
)
from app.models.estimate import Estimate, EstimateStatus


def test_get_stored_rate_card_fingerprint_reads_maintenance_assumptions():
    estimate = Estimate(
        id=uuid.uuid4(),
        project_name="Test",
        client_name="ACME",
        created_by=uuid.uuid4(),
        maintenance_assumptions={RATE_CARD_FINGERPRINT_KEY: "abc123"},
    )
    assert get_stored_rate_card_fingerprint(estimate) == "abc123"


@pytest.mark.asyncio
async def test_is_rate_card_stale_when_fingerprints_differ():
    estimate = Estimate(
        id=uuid.uuid4(),
        project_name="Test",
        client_name="ACME",
        status=EstimateStatus.CALCULATED.value,
        created_by=uuid.uuid4(),
        rate_card_id=uuid.uuid4(),
        extracted_data={"functional_requirements": []},
        maintenance_assumptions={RATE_CARD_FINGERPRINT_KEY: "old"},
    )
    db = AsyncMock()

    with patch(
        "app.estimates.rate_card_stale.resolve_extracted_rate_card_fingerprint",
        new=AsyncMock(return_value="old"),
    ), patch(
        "app.estimates.rate_card_stale.get_latest_rate_card_fingerprint",
        new=AsyncMock(return_value="new"),
    ):
        assert await is_rate_card_stale_for_estimate(db, estimate) is True


@pytest.mark.asyncio
async def test_is_rate_card_stale_for_legacy_extract_without_fingerprint():
    estimate = Estimate(
        id=uuid.uuid4(),
        project_name="Test",
        client_name="ACME",
        status=EstimateStatus.EXPORTED.value,
        created_by=uuid.uuid4(),
        rate_card_id=uuid.uuid4(),
        extracted_data={"functional_requirements": []},
        maintenance_assumptions={},
    )
    db = AsyncMock()

    with patch(
        "app.estimates.rate_card_stale.resolve_extracted_rate_card_fingerprint",
        new=AsyncMock(return_value=None),
    ), patch(
        "app.estimates.rate_card_stale.has_completed_extraction",
        new=AsyncMock(return_value=True),
    ):
        assert await is_rate_card_stale_for_estimate(db, estimate) is True

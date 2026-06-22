from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest

from app.fx.frankfurter import FRANKFURTER_BASE_URL, fetch_latest_rates


@pytest.mark.asyncio
async def test_fetch_latest_rates_uses_frankfurter_dev_v1():
    mock_response = AsyncMock()
    mock_response.raise_for_status = lambda: None
    mock_response.json = lambda: {"rates": {"JPY": 150.0}}

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("app.fx.frankfurter.httpx.AsyncClient", return_value=mock_client):
        rates = await fetch_latest_rates("USD", ["JPY"])

    mock_client.get.assert_awaited_once_with(
        f"{FRANKFURTER_BASE_URL}/latest",
        params={"from": "USD", "to": "JPY"},
    )
    assert rates == {"JPY": Decimal("150.0")}

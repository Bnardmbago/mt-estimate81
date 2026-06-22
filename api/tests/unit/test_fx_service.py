from datetime import datetime, timezone
from decimal import Decimal

import pytest

from app.fx.service import FxService


class FakeResult:
    def __init__(self, row):
        self._row = row

    def scalar_one_or_none(self):
        return self._row


class FakeSession:
    def __init__(self, rows: dict[tuple[str, str], tuple[float, datetime]] | None = None):
        self.rows = rows or {}
        self.committed = False

    async def execute(self, _stmt):
        return FakeResult(None)

    async def commit(self):
        self.committed = True

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return False


class FakeSessionFactory:
    def __init__(self, session: FakeSession):
        self.session = session

    def __call__(self):
        return self.session


@pytest.mark.asyncio
async def test_convert_amount_same_currency():
    service = FxService(FakeSessionFactory(FakeSession()))
    service._memory_cache[("JPY", "USD")] = (Decimal("0.0067"), datetime.now(timezone.utc))
    service._last_refresh_at = datetime.now(timezone.utc)

    assert await service.convert_amount(1000, "JPY", "JPY") == 1000


@pytest.mark.asyncio
async def test_get_rate_uses_memory_cache(monkeypatch):
    service = FxService(FakeSessionFactory(FakeSession()))
    service._memory_cache[("USD", "JPY")] = (Decimal("150"), datetime.now(timezone.utc))
    service._last_refresh_at = datetime.now(timezone.utc)

    rate = await service.get_rate("USD", "JPY")
    assert rate == Decimal("150")


@pytest.mark.asyncio
async def test_convert_amount_with_cached_rate(monkeypatch):
    service = FxService(FakeSessionFactory(FakeSession()))
    service._memory_cache[("USD", "JPY")] = (Decimal("150"), datetime.now(timezone.utc))
    service._last_refresh_at = datetime.now(timezone.utc)

    converted = await service.convert_amount(10, "USD", "JPY")
    assert converted == 1500

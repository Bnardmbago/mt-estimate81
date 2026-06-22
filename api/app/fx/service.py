from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.fx.frankfurter import fetch_latest_rates
from app.fx.models import FxRate

logger = logging.getLogger(__name__)

SUPPORTED_CURRENCIES = ("JPY", "USD", "PHP")
STALE_AFTER = timedelta(hours=2)

# Used when Frankfurter is unreachable so apply/calculate can still run.
FALLBACK_RATES: dict[tuple[str, str], Decimal] = {
    ("JPY", "USD"): Decimal("0.0067"),
    ("USD", "JPY"): Decimal("150"),
    ("JPY", "PHP"): Decimal("0.39"),
    ("PHP", "JPY"): Decimal("2.56"),
    ("USD", "PHP"): Decimal("58"),
    ("PHP", "USD"): Decimal("0.017"),
}

# Pairs fetched from Frankfurter (base -> quote).
FETCH_PAIRS: list[tuple[str, str]] = [
    ("JPY", "USD"),
    ("JPY", "PHP"),
    ("USD", "PHP"),
    ("USD", "JPY"),
    ("PHP", "JPY"),
    ("PHP", "USD"),
]


class FxService:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        *,
        refresh_interval_seconds: int = 3600,
    ):
        self._session_factory = session_factory
        self._refresh_interval_seconds = refresh_interval_seconds
        self._memory_cache: dict[tuple[str, str], tuple[Decimal, datetime]] = {}
        self._last_refresh_at: datetime | None = None
        self._refresh_lock = asyncio.Lock()

    async def start_background_refresh(self) -> asyncio.Task:
        return asyncio.create_task(self._periodic_refresh())

    async def _periodic_refresh(self) -> None:
        while True:
            try:
                await asyncio.sleep(self._refresh_interval_seconds)
                await self.refresh_all()
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("FX background refresh failed")

    async def refresh_all(self) -> None:
        async with self._refresh_lock:
            fetched_at = datetime.now(timezone.utc)
            bases: dict[str, set[str]] = {}
            for base, quote in FETCH_PAIRS:
                bases.setdefault(base, set()).add(quote)

            try:
                for base, quotes in bases.items():
                    rates = await fetch_latest_rates(base, sorted(quotes))
                    for quote, rate in rates.items():
                        await self._store_rate(base, quote, rate, fetched_at)
            except Exception:
                logger.exception("Frankfurter FX fetch failed; using fallback rates")
                if not self._memory_cache:
                    for (base, quote), rate in FALLBACK_RATES.items():
                        await self._store_rate(base, quote, rate, fetched_at)
                elif self._last_refresh_at is None:
                    raise

            self._last_refresh_at = fetched_at

    async def _store_rate(
        self,
        base: str,
        quote: str,
        rate: Decimal,
        fetched_at: datetime,
    ) -> None:
        self._memory_cache[(base, quote)] = (rate, fetched_at)
        async with self._session_factory() as session:
            stmt = (
                insert(FxRate)
                .values(
                    base_currency=base,
                    quote_currency=quote,
                    rate=float(rate),
                    fetched_at=fetched_at,
                )
                .on_conflict_do_update(
                    index_elements=["base_currency", "quote_currency"],
                    set_={
                        "rate": float(rate),
                        "fetched_at": fetched_at,
                    },
                )
            )
            await session.execute(stmt)
            await session.commit()

    async def ensure_fresh(self) -> None:
        if self._last_refresh_at is None:
            try:
                await self.refresh_all()
            except Exception:
                if not self._memory_cache:
                    raise
                logger.warning("FX refresh failed on first use; continuing with cached rates")
            return

        if datetime.now(timezone.utc) - self._last_refresh_at > STALE_AFTER:
            try:
                await self.refresh_all()
            except Exception:
                logger.warning("FX stale refresh failed; continuing with cached rates")

    async def get_rate(self, from_ccy: str, to_ccy: str) -> Decimal:
        from_ccy = from_ccy.upper()
        to_ccy = to_ccy.upper()
        if from_ccy == to_ccy:
            return Decimal("1")

        await self.ensure_fresh()
        direct = await self._lookup_rate(from_ccy, to_ccy)
        if direct is not None:
            return direct

        await self.refresh_all()
        direct = await self._lookup_rate(from_ccy, to_ccy)
        if direct is not None:
            return direct

        via_usd = await self._cross_rate(from_ccy, "USD", to_ccy)
        if via_usd is not None:
            return via_usd

        raise ValueError(f"No FX rate available for {from_ccy}->{to_ccy}")

    async def _cross_rate(self, from_ccy: str, bridge: str, to_ccy: str) -> Decimal | None:
        first = await self._lookup_rate(from_ccy, bridge)
        second = await self._lookup_rate(bridge, to_ccy)
        if first is None or second is None:
            return None
        return first * second

    async def _lookup_rate(self, from_ccy: str, to_ccy: str) -> Decimal | None:
        cached = self._memory_cache.get((from_ccy, to_ccy))
        if cached is not None:
            return cached[0]

        async with self._session_factory() as session:
            result = await session.execute(
                select(FxRate).where(
                    FxRate.base_currency == from_ccy,
                    FxRate.quote_currency == to_ccy,
                )
            )
            row = result.scalar_one_or_none()
            if row is None:
                return None

            rate = Decimal(str(row.rate))
            fetched_at = row.fetched_at
            if fetched_at.tzinfo is None:
                fetched_at = fetched_at.replace(tzinfo=timezone.utc)
            self._memory_cache[(from_ccy, to_ccy)] = (rate, fetched_at)
            return rate

    async def convert_amount(self, amount: int | float, from_ccy: str, to_ccy: str) -> int:
        rate = await self.get_rate(from_ccy, to_ccy)
        return int(Decimal(str(amount)) * rate)

    async def build_snapshot(self) -> dict[str, str | float | None]:
        await self.ensure_fresh()
        snapshot: dict[str, str | float | None] = {}
        latest_fetched_at: datetime | None = None

        for base, quote in FETCH_PAIRS:
            rate = await self._lookup_rate(base, quote)
            if rate is None:
                continue
            snapshot[f"{base}_{quote}"] = float(rate)
            cached = self._memory_cache.get((base, quote))
            if cached and (latest_fetched_at is None or cached[1] > latest_fetched_at):
                latest_fetched_at = cached[1]

        snapshot["fetched_at"] = latest_fetched_at.isoformat() if latest_fetched_at else None
        return snapshot

    async def get_public_rates(self) -> dict[str, str | float | None]:
        return await self.build_snapshot()


_fx_service: FxService | None = None


def init_fx_service(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    refresh_interval_seconds: int = 3600,
) -> FxService:
    global _fx_service
    _fx_service = FxService(
        session_factory,
        refresh_interval_seconds=refresh_interval_seconds,
    )
    return _fx_service


def get_fx_service() -> FxService:
    if _fx_service is None:
        raise RuntimeError("FX service has not been initialized")
    return _fx_service


def get_fx_service_optional() -> FxService | None:
    return _fx_service

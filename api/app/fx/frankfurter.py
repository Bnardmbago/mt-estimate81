from decimal import Decimal

import httpx

# Frankfurter moved from api.frankfurter.app to api.frankfurter.dev/v1 (2025+).
FRANKFURTER_BASE_URL = "https://api.frankfurter.dev/v1"


async def fetch_latest_rates(base: str, targets: list[str]) -> dict[str, Decimal]:
    if not targets:
        return {}

    params = {"from": base, "to": ",".join(targets)}
    async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
        response = await client.get(f"{FRANKFURTER_BASE_URL}/latest", params=params)
        response.raise_for_status()
        payload = response.json()

    rates = payload.get("rates") or {}
    return {currency: Decimal(str(value)) for currency, value in rates.items()}

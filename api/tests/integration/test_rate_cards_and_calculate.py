import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.service import create_access_token, hash_password
from app.models.estimate import Estimate, EstimateStatus, FeatureItem
from app.models.rate_card import RateCard, RateCardVersion
from app.models.user import User
from app.rate_cards.defaults import DEFAULT_RATE_CARD_SETTINGS


@pytest.fixture
async def admin_user(db_session: AsyncSession) -> User:
    user = User(
        id=uuid.uuid4(),
        email="admin@example.com",
        password_hash=hash_password("adminpass"),
        display_name="Admin",
        is_admin=True,
        preferred_locale="en",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
def admin_headers(admin_user: User) -> dict[str, str]:
    token = create_access_token({"sub": str(admin_user.id), "is_admin": admin_user.is_admin})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def active_rate_card(db_session: AsyncSession, admin_user: User) -> RateCardVersion:
    rate_card = RateCard(
        name="Test Rates",
        is_active=True,
        created_by=admin_user.id,
    )
    db_session.add(rate_card)
    await db_session.flush()

    version = RateCardVersion(
        rate_card_id=rate_card.id,
        version_number=1,
        settings=DEFAULT_RATE_CARD_SETTINGS,
    )
    db_session.add(version)
    await db_session.commit()
    await db_session.refresh(version)
    return version


@pytest.fixture
async def review_estimate(
    db_session: AsyncSession,
    client: AsyncClient,
    active_rate_card: RateCardVersion,
) -> str:
    user = client.test_user  # type: ignore[attr-defined]
    estimate = Estimate(
        project_name="Calc Test",
        client_name="ACME",
        locale="en",
        status=EstimateStatus.REVIEW.value,
        created_by=user.id,
        maintenance_assumptions={"monthly_support_hours": 20, "support_role": "developer"},
    )
    db_session.add(estimate)
    await db_session.flush()

    db_session.add(
        FeatureItem(
            estimate_id=estimate.id,
            sort_order=0,
            name="Auth",
            description="Login",
            hours=40,
            phase="development",
            role="developer",
            is_ai_generated=False,
        )
    )
    await db_session.commit()
    return str(estimate.id)


@pytest.mark.asyncio
async def test_non_admin_cannot_access_rate_cards(
    client: AsyncClient,
    auth_headers: dict[str, str],
    active_rate_card: RateCardVersion,
):
    response = await client.get("/admin/rate-cards/active", headers=auth_headers)
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_get_active_rate_card(
    client: AsyncClient,
    admin_headers: dict[str, str],
    active_rate_card: RateCardVersion,
):
    response = await client.get("/admin/rate-cards/active", headers=admin_headers)
    assert response.status_code == 200
    payload = response.json()
    assert payload["version_number"] == 1
    assert len(payload["settings"]["roles"]) == 3


@pytest.mark.asyncio
async def test_update_rate_card_creates_version(
    client: AsyncClient,
    admin_headers: dict[str, str],
    active_rate_card: RateCardVersion,
):
    settings = dict(DEFAULT_RATE_CARD_SETTINGS)
    settings["contingency_rate"] = 0.20

    response = await client.put(
        "/admin/rate-cards",
        json={"settings": settings},
        headers=admin_headers,
    )
    assert response.status_code == 200
    assert response.json()["version_number"] == 2
    assert response.json()["settings"]["contingency_rate"] == 0.20

    versions = await client.get("/admin/rate-cards/versions", headers=admin_headers)
    assert versions.status_code == 200
    assert len(versions.json()) == 2


@pytest.mark.asyncio
async def test_update_rate_card_rejects_invalid_phase_sum(
    client: AsyncClient,
    admin_headers: dict[str, str],
    active_rate_card: RateCardVersion,
):
    settings = dict(DEFAULT_RATE_CARD_SETTINGS)
    settings["phases"] = [{"name": "development", "percentage": 0.50}]

    response = await client.put(
        "/admin/rate-cards",
        json={"settings": settings},
        headers=admin_headers,
    )
    assert response.status_code == 400
    assert response.json()["code"] == "INVALID_PHASE_SUM"


@pytest.mark.asyncio
async def test_calculate_estimate(
    client: AsyncClient,
    auth_headers: dict[str, str],
    review_estimate: str,
):
    response = await client.post(
        f"/estimates/{review_estimate}/calculate",
        headers=auth_headers,
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "calculated"
    assert payload["rate_card_version_id"] is not None
    assert payload["calculation_result"]["nrc"]["total_jpy"] > 0
    assert payload["calculation_result"]["first_year_total_jpy"] > 0


@pytest.mark.asyncio
async def test_recalculate_uses_frozen_rate_card(
    client: AsyncClient,
    admin_headers: dict[str, str],
    auth_headers: dict[str, str],
    review_estimate: str,
    db_session: AsyncSession,
    active_rate_card: RateCardVersion,
):
    first = await client.post(
        f"/estimates/{review_estimate}/calculate",
        headers=auth_headers,
    )
    frozen_version_id = first.json()["rate_card_version_id"]
    original_total = first.json()["calculation_result"]["nrc"]["total_jpy"]

    settings = dict(DEFAULT_RATE_CARD_SETTINGS)
    settings["contingency_rate"] = 0.50
    await client.put(
        "/admin/rate-cards",
        json={"settings": settings},
        headers=admin_headers,
    )

    second = await client.post(
        f"/estimates/{review_estimate}/calculate",
        headers=auth_headers,
    )
    assert second.json()["rate_card_version_id"] == frozen_version_id
    assert second.json()["calculation_result"]["nrc"]["total_jpy"] == original_total


@pytest.mark.asyncio
async def test_recalculate_with_current_rates(
    client: AsyncClient,
    admin_headers: dict[str, str],
    auth_headers: dict[str, str],
    review_estimate: str,
):
    first = await client.post(
        f"/estimates/{review_estimate}/calculate",
        headers=auth_headers,
    )
    original_total = first.json()["calculation_result"]["nrc"]["total_jpy"]

    settings = dict(DEFAULT_RATE_CARD_SETTINGS)
    settings["contingency_rate"] = 0.50
    await client.put(
        "/admin/rate-cards",
        json={"settings": settings},
        headers=admin_headers,
    )

    second = await client.post(
        f"/estimates/{review_estimate}/calculate?recalculate_with_current_rates=true",
        headers=auth_headers,
    )
    assert second.json()["calculation_result"]["nrc"]["total_jpy"] > original_total

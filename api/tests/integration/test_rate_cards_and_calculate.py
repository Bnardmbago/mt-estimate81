import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.service import create_access_token, hash_password
from app.models.estimate import Estimate, EstimateStatus, FeatureItem
from app.models.rate_card import RateCard, RateCardVersion
from app.models.user import User
from app.rate_cards.defaults import DEFAULT_RATE_CARD_SETTINGS


async def _mark_estimate_exported(db_session: AsyncSession, estimate_id: str) -> None:
    estimate = await db_session.get(Estimate, uuid.UUID(estimate_id))
    assert estimate is not None
    estimate.status = EstimateStatus.EXPORTED.value
    await db_session.commit()


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
async def active_rate_card(
    db_session: AsyncSession,
    client: AsyncClient,
) -> RateCardVersion:
    user = client.test_user  # type: ignore[attr-defined]
    rate_card = RateCard(
        name="Test Rates",
        is_active=True,
        created_by=user.id,
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
        rate_card_id=active_rate_card.rate_card_id,
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
async def test_authenticated_user_can_access_rate_cards(
    client: AsyncClient,
    auth_headers: dict[str, str],
    active_rate_card: RateCardVersion,
):
    response = await client.get("/rate-cards/active", headers=auth_headers)
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_get_active_rate_card(
    client: AsyncClient,
    admin_headers: dict[str, str],
    active_rate_card: RateCardVersion,
):
    response = await client.get("/rate-cards/active", headers=admin_headers)
    assert response.status_code == 200
    payload = response.json()
    assert payload["version_number"] == 1
    assert len(payload["settings"]["roles"]) == 3
    assert payload["settings"]["development_approach"] == "traditional"


@pytest.mark.asyncio
async def test_create_rate_card_requires_development_approach(
    client: AsyncClient,
    admin_headers: dict[str, str],
):
    response = await client.post(
        "/rate-cards/cards",
        json={"name": "Missing Approach", "activate": False},
        headers=admin_headers,
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_calculate_uses_development_approach_effort_multiplier(
    client: AsyncClient,
    admin_headers: dict[str, str],
    auth_headers: dict[str, str],
    review_estimate: str,
    active_rate_card: RateCardVersion,
):
    settings = dict(DEFAULT_RATE_CARD_SETTINGS)
    settings["development_approach"] = "ai_assisted"

    response = await client.put(
        f"/rate-cards/versions/{active_rate_card.id}",
        json={"settings": settings},
        headers=admin_headers,
    )
    assert response.status_code == 200

    calc = await client.post(f"/estimates/{review_estimate}/calculate", headers=auth_headers)
    assert calc.status_code == 200
    payload = calc.json()["calculation_result"]
    assert payload["development_approach"] == "ai_assisted"
    assert payload["development_approach_effort_multiplier"] == 0.75
    assert payload["total_effort_hours"] == 30.0


@pytest.mark.asyncio
async def test_get_rate_card_version_by_id(
    client: AsyncClient,
    admin_headers: dict[str, str],
    active_rate_card: RateCardVersion,
):
    response = await client.get(
        f"/rate-cards/versions/{active_rate_card.id}",
        headers=admin_headers,
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["version_id"] == str(active_rate_card.id)
    assert payload["settings"]["setup_cost_items"]


@pytest.mark.asyncio
async def test_update_rate_card_version_in_place(
    client: AsyncClient,
    admin_headers: dict[str, str],
    active_rate_card: RateCardVersion,
):
    settings = dict(DEFAULT_RATE_CARD_SETTINGS)
    settings["contingency_rate"] = 0.25

    response = await client.put(
        f"/rate-cards/versions/{active_rate_card.id}",
        json={"label": "Updated in place", "settings": settings},
        headers=admin_headers,
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["version_number"] == 1
    assert payload["version_label"] == "Updated in place"
    assert payload["settings"]["contingency_rate"] == 0.25

    versions = await client.get("/rate-cards/versions", headers=admin_headers)
    assert len(versions.json()) == 1


@pytest.mark.asyncio
async def test_delete_rate_card_version(
    client: AsyncClient,
    admin_headers: dict[str, str],
    active_rate_card: RateCardVersion,
):
    settings = dict(DEFAULT_RATE_CARD_SETTINGS)
    settings["contingency_rate"] = 0.20
    second = await client.put(
        "/rate-cards/",
        json={"settings": settings, "version_label": "Second"},
        headers=admin_headers,
    )
    second_id = second.json()["version_id"]

    response = await client.delete(
        f"/rate-cards/versions/{second_id}",
        headers=admin_headers,
    )
    assert response.status_code == 204

    versions = await client.get("/rate-cards/versions", headers=admin_headers)
    assert len(versions.json()) == 1


@pytest.mark.asyncio
async def test_cannot_delete_last_rate_card_version(
    client: AsyncClient,
    admin_headers: dict[str, str],
    active_rate_card: RateCardVersion,
):
    response = await client.delete(
        f"/rate-cards/versions/{active_rate_card.id}",
        headers=admin_headers,
    )
    assert response.status_code == 400
    assert response.json()["code"] == "RATE_CARD_VERSION_LAST"


@pytest.mark.asyncio
async def test_cannot_delete_rate_card_version_in_use(
    client: AsyncClient,
    admin_headers: dict[str, str],
    auth_headers: dict[str, str],
    review_estimate: str,
    active_rate_card: RateCardVersion,
):
    settings = dict(DEFAULT_RATE_CARD_SETTINGS)
    settings["contingency_rate"] = 0.20
    created = await client.put(
        "/rate-cards/",
        json={"settings": settings, "version_label": "Second version"},
        headers=admin_headers,
    )
    assert created.status_code == 200
    version_in_use_id = created.json()["version_id"]

    await client.post(f"/estimates/{review_estimate}/calculate", headers=auth_headers)

    response = await client.delete(
        f"/rate-cards/versions/{version_in_use_id}",
        headers=admin_headers,
    )
    assert response.status_code == 400
    assert response.json()["code"] == "RATE_CARD_VERSION_IN_USE"


@pytest.mark.asyncio
async def test_rename_rate_card_version(
    client: AsyncClient,
    admin_headers: dict[str, str],
    active_rate_card: RateCardVersion,
):
    response = await client.patch(
        f"/rate-cards/versions/{active_rate_card.id}",
        json={"label": "Q2 2026 Standard"},
        headers=admin_headers,
    )
    assert response.status_code == 200
    assert response.json()["label"] == "Q2 2026 Standard"


@pytest.mark.asyncio
async def test_update_rate_card_with_name_and_label(
    client: AsyncClient,
    admin_headers: dict[str, str],
    active_rate_card: RateCardVersion,
):
    settings = dict(DEFAULT_RATE_CARD_SETTINGS)
    settings["roles"] = [
        {"name": "developer", "hourly_rate_jpy": 7000},
        *settings["roles"][1:],
    ]

    response = await client.put(
        "/rate-cards/",
        json={
            "name": "2026 Premium Rates",
            "version_label": "Premium v2",
            "settings": settings,
        },
        headers=admin_headers,
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["name"] == "2026 Premium Rates"
    assert payload["version_label"] == "Premium v2"
    assert payload["settings"]["roles"][0]["daily_rate"] == 7000 * 8


@pytest.mark.asyncio
async def test_update_rate_card_preserves_custom_daily_rate(
    client: AsyncClient,
    admin_headers: dict[str, str],
    active_rate_card: RateCardVersion,
):
    settings = dict(DEFAULT_RATE_CARD_SETTINGS)
    settings["roles"] = [
        {"name": "developer", "hourly_rate_jpy": 6000, "daily_rate_jpy": 55000},
        *settings["roles"][1:],
    ]

    response = await client.put(
        "/rate-cards/",
        json={"settings": settings},
        headers=admin_headers,
    )
    assert response.status_code == 200
    assert response.json()["settings"]["roles"][0]["daily_rate"] == 55000


@pytest.mark.asyncio
async def test_update_rate_card_creates_version(
    client: AsyncClient,
    admin_headers: dict[str, str],
    active_rate_card: RateCardVersion,
):
    settings = dict(DEFAULT_RATE_CARD_SETTINGS)
    settings["contingency_rate"] = 0.20

    response = await client.put(
        "/rate-cards/",
        json={"settings": settings},
        headers=admin_headers,
    )
    assert response.status_code == 200
    assert response.json()["version_number"] == 2
    assert response.json()["settings"]["contingency_rate"] == 0.20

    versions = await client.get("/rate-cards/versions", headers=admin_headers)
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
        "/rate-cards/",
        json={"settings": settings},
        headers=admin_headers,
    )
    assert response.status_code == 400
    assert response.json()["code"] == "INVALID_PHASE_SUM"


@pytest.mark.asyncio
async def test_list_rate_card_versions_for_authenticated_user(
    client: AsyncClient,
    auth_headers: dict[str, str],
    active_rate_card: RateCardVersion,
):
    response = await client.get("/rate-cards/versions", headers=auth_headers)
    assert response.status_code == 200
    payload = response.json()
    assert len(payload) >= 1
    assert payload[0]["id"] == str(active_rate_card.id)


@pytest.mark.asyncio
async def test_calculate_with_selected_rate_card(
    client: AsyncClient,
    admin_headers: dict[str, str],
    auth_headers: dict[str, str],
    review_estimate: str,
    active_rate_card: RateCardVersion,
):
    second_card = await client.post(
        "/rate-cards/cards",
        json={"name": "Alternate Rates", "activate": False, "development_approach": "traditional"},
        headers=auth_headers,
    )
    assert second_card.status_code == 201
    alternate_card_id = second_card.json()["id"]

    settings = dict(DEFAULT_RATE_CARD_SETTINGS)
    settings["contingency_rate"] = 0.20
    await client.put(
        "/rate-cards/",
        json={"settings": settings, "version_label": "High contingency"},
        headers=admin_headers,
    )

    await client.patch(
        f"/estimates/{review_estimate}",
        json={"rate_card_id": alternate_card_id},
        headers=auth_headers,
    )

    response = await client.post(
        f"/estimates/{review_estimate}/calculate",
        headers=auth_headers,
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["rate_card_id"] == alternate_card_id
    assert payload["rate_card_version_id"] is not None
    assert payload["calculation_result"]["rate_card_version_id"] is not None


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
        "/rate-cards/",
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
    active_rate_card: RateCardVersion,
):
    settings = dict(DEFAULT_RATE_CARD_SETTINGS)
    settings["contingency_rate"] = 0.50
    await client.put(
        "/rate-cards/",
        json={"settings": settings, "version_label": "High contingency"},
        headers=admin_headers,
    )

    first = await client.post(
        f"/estimates/{review_estimate}/calculate",
        headers=auth_headers,
    )
    assert first.status_code == 200
    original_total = first.json()["calculation_result"]["nrc"]["total_jpy"]
    frozen_version_id = first.json()["rate_card_version_id"]

    second = await client.post(
        f"/estimates/{review_estimate}/calculate?recalculate_with_current_rates=true",
        headers=auth_headers,
    )
    assert second.status_code == 200
    payload = second.json()
    assert payload["rate_card_id"] == str(active_rate_card.rate_card_id)
    assert payload["rate_card_version_id"] == frozen_version_id
    assert payload["calculation_result"]["nrc"]["total_jpy"] == original_total


@pytest.mark.asyncio
async def test_list_rate_card_options(
    client: AsyncClient,
    admin_headers: dict[str, str],
    active_rate_card: RateCardVersion,
):
    response = await client.get("/rate-cards/cards/options", headers=admin_headers)
    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["id"] == str(active_rate_card.rate_card_id)
    assert payload[0]["name"] == "Test Rates"
    assert payload[0]["is_active"] is True


@pytest.mark.asyncio
async def test_list_rate_cards(
    client: AsyncClient,
    admin_headers: dict[str, str],
    active_rate_card: RateCardVersion,
):
    response = await client.get("/rate-cards/cards", headers=admin_headers)
    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["name"] == "Test Rates"
    assert payload[0]["is_active"] is True
    assert payload[0]["development_approach"] == "traditional"
    assert payload[0]["latest_version_number"] == 1
    assert payload[0]["estimate_count"] == 0


@pytest.mark.asyncio
async def test_get_rate_card_by_id(
    client: AsyncClient,
    admin_headers: dict[str, str],
    active_rate_card: RateCardVersion,
):
    response = await client.get(
        f"/rate-cards/cards/{active_rate_card.rate_card_id}",
        headers=admin_headers,
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["id"] == str(active_rate_card.rate_card_id)
    assert payload["name"] == "Test Rates"
    assert payload["settings"]["development_approach"] == "traditional"


@pytest.mark.asyncio
async def test_create_rate_card(
    client: AsyncClient,
    admin_headers: dict[str, str],
    active_rate_card: RateCardVersion,
):
    response = await client.post(
        "/rate-cards/cards",
        json={"name": "Client B Rates", "activate": True, "development_approach": "traditional"},
        headers=admin_headers,
    )
    assert response.status_code == 201
    payload = response.json()
    assert payload["name"] == "Client B Rates"
    assert payload["version_number"] == 1
    assert len(payload["settings"]["roles"]) == 3

    cards = (await client.get("/rate-cards/cards", headers=admin_headers)).json()
    assert len(cards) == 2
    active_cards = [card for card in cards if card["is_active"]]
    assert len(active_cards) == 1
    assert active_cards[0]["name"] == "Client B Rates"


@pytest.mark.asyncio
async def test_activate_rate_card(
    client: AsyncClient,
    admin_headers: dict[str, str],
    active_rate_card: RateCardVersion,
):
    created = await client.post(
        "/rate-cards/cards",
        json={"name": "Client B Rates", "activate": True, "development_approach": "traditional"},
        headers=admin_headers,
    )
    first_card_id = str(active_rate_card.rate_card_id)

    response = await client.post(
        f"/rate-cards/cards/{first_card_id}/activate",
        headers=admin_headers,
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Test Rates"

    active = (await client.get("/rate-cards/active", headers=admin_headers)).json()
    assert active["name"] == "Test Rates"
    assert active["id"] == first_card_id
    assert created.json()["id"] != first_card_id


@pytest.mark.asyncio
async def test_list_versions_includes_estimate_count(
    client: AsyncClient,
    admin_headers: dict[str, str],
    auth_headers: dict[str, str],
    review_estimate: str,
):
    await client.post(
        f"/estimates/{review_estimate}/calculate",
        headers=auth_headers,
    )

    response = await client.get("/rate-cards/versions", headers=admin_headers)
    assert response.status_code == 200
    versions = response.json()
    assert len(versions) >= 1
    assert any(version["estimate_count"] >= 1 for version in versions)


@pytest.mark.asyncio
async def test_list_card_estimates_after_calculate(
    client: AsyncClient,
    admin_headers: dict[str, str],
    auth_headers: dict[str, str],
    active_rate_card: RateCardVersion,
    review_estimate: str,
):
    await client.post(
        f"/estimates/{review_estimate}/calculate",
        headers=auth_headers,
    )

    response = await client.get(
        f"/rate-cards/cards/{active_rate_card.rate_card_id}/estimates",
        headers=admin_headers,
    )
    assert response.status_code == 200
    estimates = response.json()
    assert len(estimates) >= 1
    assert any(item["estimate_id"] == review_estimate for item in estimates)


@pytest.mark.asyncio
async def test_save_card_after_export_still_editable(
    client: AsyncClient,
    db_session: AsyncSession,
    admin_headers: dict[str, str],
    auth_headers: dict[str, str],
    active_rate_card: RateCardVersion,
    review_estimate: str,
):
    await client.post(
        f"/estimates/{review_estimate}/calculate",
        headers=auth_headers,
    )
    await _mark_estimate_exported(db_session, review_estimate)

    settings = dict(DEFAULT_RATE_CARD_SETTINGS)
    settings["contingency_rate"] = 0.30

    saved = await client.put(
        f"/rate-cards/cards/{active_rate_card.rate_card_id}",
        json={"settings": settings},
        headers=admin_headers,
    )
    assert saved.status_code == 200
    assert saved.json()["is_locked"] is False
    assert saved.json()["settings"]["contingency_rate"] == 0.30


@pytest.mark.asyncio
async def test_duplicate_creates_editable_copy(
    client: AsyncClient,
    admin_headers: dict[str, str],
    auth_headers: dict[str, str],
    active_rate_card: RateCardVersion,
    review_estimate: str,
):
    await client.post(
        f"/estimates/{review_estimate}/calculate",
        headers=auth_headers,
    )

    duplicate = await client.post(
        f"/rate-cards/cards/{active_rate_card.rate_card_id}/duplicate",
        json={"name": "Duplicated Rates"},
        headers=admin_headers,
    )
    assert duplicate.status_code == 201
    body = duplicate.json()
    assert body["name"] == "Duplicated Rates"
    assert body["id"] != str(active_rate_card.rate_card_id)
    assert body["is_active"] is True
    assert body["estimate_count"] == 0
    assert body["is_locked"] is False
    assert body["settings"]["contingency_rate"] == DEFAULT_RATE_CARD_SETTINGS["contingency_rate"]

    settings = dict(DEFAULT_RATE_CARD_SETTINGS)
    settings["contingency_rate"] = 0.25

    saved = await client.put(
        f"/rate-cards/versions/{body['version_id']}",
        json={"settings": settings, "name": "Duplicated Rates"},
        headers=admin_headers,
    )
    assert saved.status_code == 200
    assert saved.json()["settings"]["contingency_rate"] == 0.25


@pytest.mark.asyncio
async def test_duplicate_unused_source_unchanged(
    client: AsyncClient,
    db_session: AsyncSession,
    admin_headers: dict[str, str],
    auth_headers: dict[str, str],
    active_rate_card: RateCardVersion,
    review_estimate: str,
):
    await client.post(
        f"/estimates/{review_estimate}/calculate",
        headers=auth_headers,
    )
    await _mark_estimate_exported(db_session, review_estimate)

    duplicate = await client.post(
        f"/rate-cards/cards/{active_rate_card.rate_card_id}/duplicate",
        json={"name": "Copy for edits"},
        headers=admin_headers,
    )
    assert duplicate.status_code == 201
    new_card_id = duplicate.json()["id"]

    source = await client.get("/rate-cards/active", headers=admin_headers)
    assert source.status_code == 200
    assert source.json()["id"] == new_card_id

    cards = (await client.get("/rate-cards/cards", headers=admin_headers)).json()
    source_summary = next(
        card for card in cards if card["id"] == str(active_rate_card.rate_card_id)
    )
    new_summary = next(card for card in cards if card["id"] == new_card_id)

    assert source_summary["is_locked"] is False
    assert source_summary["estimate_count"] >= 1
    assert new_summary["is_locked"] is False
    assert new_summary["estimate_count"] == 0


@pytest.mark.asyncio
async def test_unused_card_still_editable(
    client: AsyncClient,
    admin_headers: dict[str, str],
    active_rate_card: RateCardVersion,
):
    settings = dict(DEFAULT_RATE_CARD_SETTINGS)
    settings["contingency_rate"] = 0.22

    response = await client.put(
        f"/rate-cards/versions/{active_rate_card.id}",
        json={"settings": settings},
        headers=admin_headers,
    )
    assert response.status_code == 200
    assert response.json()["settings"]["contingency_rate"] == 0.22
    assert response.json()["is_locked"] is False


@pytest.mark.asyncio
async def test_delete_unused_rate_card(
    client: AsyncClient,
    admin_headers: dict[str, str],
    active_rate_card: RateCardVersion,
):
    created = await client.post(
        "/rate-cards/cards",
        json={"name": "Unused Card", "activate": False, "development_approach": "traditional"},
        headers=admin_headers,
    )
    assert created.status_code == 201
    card_id = created.json()["id"]

    response = await client.delete(
        f"/rate-cards/cards/{card_id}",
        headers=admin_headers,
    )
    assert response.status_code == 204

    cards = (await client.get("/rate-cards/cards", headers=admin_headers)).json()
    assert all(card["id"] != card_id for card in cards)


@pytest.mark.asyncio
async def test_cannot_delete_last_rate_card(
    client: AsyncClient,
    admin_headers: dict[str, str],
    active_rate_card: RateCardVersion,
):
    response = await client.delete(
        f"/rate-cards/cards/{active_rate_card.rate_card_id}",
        headers=admin_headers,
    )
    assert response.status_code == 400
    assert response.json()["code"] == "RATE_CARD_LAST"


@pytest.mark.asyncio
async def test_cannot_delete_rate_card_in_use(
    client: AsyncClient,
    admin_headers: dict[str, str],
    auth_headers: dict[str, str],
    active_rate_card: RateCardVersion,
    review_estimate: str,
):
    await client.post(
        f"/estimates/{review_estimate}/calculate",
        headers=auth_headers,
    )

    response = await client.delete(
        f"/rate-cards/cards/{active_rate_card.rate_card_id}",
        headers=admin_headers,
    )
    assert response.status_code == 400
    assert response.json()["code"] == "RATE_CARD_IN_USE"


@pytest.mark.asyncio
async def test_delete_active_rate_card_auto_activates(
    client: AsyncClient,
    admin_headers: dict[str, str],
    active_rate_card: RateCardVersion,
):
    created = await client.post(
        "/rate-cards/cards",
        json={"name": "Temporary Active", "activate": True, "development_approach": "traditional"},
        headers=admin_headers,
    )
    assert created.status_code == 201
    temp_card_id = created.json()["id"]

    response = await client.delete(
        f"/rate-cards/cards/{temp_card_id}",
        headers=admin_headers,
    )
    assert response.status_code == 204

    active = (await client.get("/rate-cards/active", headers=admin_headers)).json()
    assert active["id"] == str(active_rate_card.rate_card_id)
    assert active["name"] == "Test Rates"


@pytest.mark.asyncio
async def test_calculate_stores_gantt_timeline(
    client: AsyncClient,
    auth_headers: dict[str, str],
    review_estimate: str,
):
    response = await client.post(
        f"/estimates/{review_estimate}/calculate",
        json={"project_start_date": "2026-06-09"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    payload = response.json()
    gantt = payload["calculation_result"]["gantt"]
    assert gantt["project_start_date"] == "2026-06-09"
    assert len(gantt["tasks"]) >= 1
    assert payload["project_start_date"] == "2026-06-09"


@pytest.mark.asyncio
async def test_gantt_preview_endpoint(
    client: AsyncClient,
    auth_headers: dict[str, str],
    review_estimate: str,
):
    response = await client.get(
        f"/estimates/{review_estimate}/gantt?start_date=2026-06-09",
        headers=auth_headers,
    )
    assert response.status_code == 200
    gantt = response.json()["gantt"]
    assert gantt["project_start_date"] == "2026-06-09"
    assert len(gantt["tasks"]) >= 1


@pytest.mark.asyncio
async def test_calculate_applies_admin_discount_rate(
    client: AsyncClient,
    admin_headers: dict[str, str],
    auth_headers: dict[str, str],
    review_estimate: str,
):
    await client.patch(
        "/admin/discount-settings",
        headers=admin_headers,
        json={"estimate_discount_rate": 0.0},
    )

    baseline = await client.post(
        f"/estimates/{review_estimate}/calculate",
        headers=auth_headers,
    )
    assert baseline.status_code == 200
    baseline_total = baseline.json()["calculation_result"]["nrc"]["total_jpy"]
    baseline_rc = baseline.json()["calculation_result"]["rc"]["monthly_total_jpy"]

    await client.patch(
        f"/estimates/{review_estimate}",
        json={"status": "review"},
        headers=auth_headers,
    )

    await client.patch(
        "/admin/discount-settings",
        headers=admin_headers,
        json={"estimate_discount_rate": 0.30},
    )

    discounted = await client.post(
        f"/estimates/{review_estimate}/calculate",
        headers=auth_headers,
    )
    assert discounted.status_code == 200
    discounted_result = discounted.json()["calculation_result"]
    discounted_total = discounted_result["nrc"]["total_jpy"]
    assert discounted_total < baseline_total
    assert discounted_total == int(round(baseline_total * 0.7))
    assert discounted_result["rc"]["monthly_total_jpy"] == baseline_rc

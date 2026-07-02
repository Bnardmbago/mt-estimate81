import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.rate_card import RateCard, RateCardVersion
from app.models.user import User
from app.rate_cards.defaults import DEFAULT_RATE_CARD_SETTINGS
from tests.conftest import _create_rate_card_for_user


async def _create_estimate(client: AsyncClient, headers: dict[str, str]) -> str:
    response = await client.post(
        "/estimates",
        json={
            "project_name": "Access Test",
            "client_name": "ACME",
            "locale": "en",
        },
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()["id"]


@pytest.mark.asyncio
async def test_owner_lists_only_own_rate_cards(
    client: AsyncClient,
    auth_headers: dict[str, str],
    other_headers: dict[str, str],
    user_owned_rate_card: RateCardVersion,
    db_session: AsyncSession,
    other_user: User,
):
    await _create_rate_card_for_user(
        db_session,
        other_user,
        name="Other User Rates",
        is_active=False,
    )

    response = await client.get("/rate-cards/cards", headers=auth_headers)
    assert response.status_code == 200
    ids = {item["id"] for item in response.json()}
    assert str(user_owned_rate_card.rate_card_id) in ids
    assert len(ids) == 1


@pytest.mark.asyncio
async def test_user_lists_system_default_rate_card(
    client: AsyncClient,
    auth_headers: dict[str, str],
    user_owned_rate_card: RateCardVersion,
    db_session: AsyncSession,
    admin_user: User,
):
    from app.rate_cards.defaults import DEFAULT_RATE_CARD_NAME, DEFAULT_RATE_CARD_SETTINGS
    from app.models.rate_card import RateCard, RateCardVersion

    system_card = RateCard(
        name=DEFAULT_RATE_CARD_NAME,
        is_active=True,
        is_system=True,
        created_by=admin_user.id,
    )
    db_session.add(system_card)
    await db_session.flush()
    db_session.add(
        RateCardVersion(
            rate_card_id=system_card.id,
            version_number=1,
            settings=DEFAULT_RATE_CARD_SETTINGS,
        )
    )
    await db_session.commit()

    response = await client.get("/rate-cards/cards", headers=auth_headers)
    assert response.status_code == 200
    ids = {item["id"] for item in response.json()}
    assert str(user_owned_rate_card.rate_card_id) in ids
    assert str(system_card.id) in ids
    system_row = next(item for item in response.json() if item["id"] == str(system_card.id))
    assert system_row["is_system"] is True


@pytest.mark.asyncio
async def test_user_can_open_system_default_rate_card(
    client: AsyncClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
    admin_user: User,
):
    from app.rate_cards.defaults import DEFAULT_RATE_CARD_NAME, DEFAULT_RATE_CARD_SETTINGS
    from app.models.rate_card import RateCard, RateCardVersion

    system_card = RateCard(
        name=DEFAULT_RATE_CARD_NAME,
        is_active=True,
        is_system=True,
        created_by=admin_user.id,
    )
    db_session.add(system_card)
    await db_session.flush()
    db_session.add(
        RateCardVersion(
            rate_card_id=system_card.id,
            version_number=1,
            settings=DEFAULT_RATE_CARD_SETTINGS,
        )
    )
    await db_session.commit()

    response = await client.get(f"/rate-cards/cards/{system_card.id}", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["is_system"] is True


@pytest.mark.asyncio
async def test_cannot_delete_system_default_rate_card(
    client: AsyncClient,
    auth_headers: dict[str, str],
    user_owned_rate_card: RateCardVersion,
    db_session: AsyncSession,
    admin_user: User,
):
    from app.rate_cards.defaults import DEFAULT_RATE_CARD_NAME, DEFAULT_RATE_CARD_SETTINGS
    from app.models.rate_card import RateCard, RateCardVersion

    system_card = RateCard(
        name=DEFAULT_RATE_CARD_NAME,
        is_active=True,
        is_system=True,
        created_by=admin_user.id,
    )
    db_session.add(system_card)
    await db_session.flush()
    db_session.add(
        RateCardVersion(
            rate_card_id=system_card.id,
            version_number=1,
            settings=DEFAULT_RATE_CARD_SETTINGS,
        )
    )
    await db_session.commit()

    response = await client.delete(
        f"/rate-cards/cards/{system_card.id}",
        headers=auth_headers,
    )
    assert response.status_code == 400
    assert response.json()["code"] == "RATE_CARD_SYSTEM"


@pytest.mark.asyncio
async def test_get_active_prefers_system_default_when_user_has_no_active_card(
    client: AsyncClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
    admin_user: User,
):
    from app.rate_cards.defaults import DEFAULT_RATE_CARD_NAME, DEFAULT_RATE_CARD_SETTINGS
    from app.models.rate_card import RateCard, RateCardVersion

    for card in (await db_session.execute(select(RateCard))).scalars():
        card.is_active = False
    await db_session.flush()

    system_card = RateCard(
        name=DEFAULT_RATE_CARD_NAME,
        is_active=True,
        is_system=True,
        created_by=admin_user.id,
    )
    db_session.add(system_card)
    await db_session.flush()
    db_session.add(
        RateCardVersion(
            rate_card_id=system_card.id,
            version_number=1,
            settings=DEFAULT_RATE_CARD_SETTINGS,
        )
    )
    await db_session.commit()

    response = await client.get("/rate-cards/active", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["id"] == str(system_card.id)


@pytest.mark.asyncio
async def test_other_user_does_not_see_owner_rate_card_in_list(
    client: AsyncClient,
    auth_headers: dict[str, str],
    other_headers: dict[str, str],
    user_owned_rate_card: RateCardVersion,
):
    response = await client.get("/rate-cards/cards", headers=other_headers)
    assert response.status_code == 200
    ids = {item["id"] for item in response.json()}
    assert str(user_owned_rate_card.rate_card_id) not in ids


@pytest.mark.asyncio
async def test_admin_lists_all_rate_cards(
    client: AsyncClient,
    auth_headers: dict[str, str],
    admin_headers: dict[str, str],
    user_owned_rate_card: RateCardVersion,
    db_session: AsyncSession,
    admin_user: User,
):
    admin_card = await _create_rate_card_for_user(
        db_session,
        admin_user,
        name="Admin Rates",
        is_active=False,
    )

    response = await client.get("/rate-cards/cards", headers=admin_headers)
    assert response.status_code == 200
    ids = {item["id"] for item in response.json()}
    assert str(user_owned_rate_card.rate_card_id) in ids
    assert str(admin_card.rate_card_id) in ids


@pytest.mark.asyncio
async def test_owner_can_get_patch_and_delete_own_rate_card(
    client: AsyncClient,
    auth_headers: dict[str, str],
    user_owned_rate_card: RateCardVersion,
):
    spare = await client.post(
        "/rate-cards/cards",
        json={"name": "Spare Card", "activate": False, "development_approach": "traditional"},
        headers=auth_headers,
    )
    assert spare.status_code == 201

    card_id = str(user_owned_rate_card.rate_card_id)

    get_response = await client.get(f"/rate-cards/cards/{card_id}", headers=auth_headers)
    assert get_response.status_code == 200

    settings = dict(DEFAULT_RATE_CARD_SETTINGS)
    settings["contingency_rate"] = 0.15
    patch_response = await client.put(
        f"/rate-cards/cards/{card_id}",
        json={"settings": settings},
        headers=auth_headers,
    )
    assert patch_response.status_code == 200
    assert patch_response.json()["settings"]["contingency_rate"] == 0.15

    delete_response = await client.delete(f"/rate-cards/cards/{card_id}", headers=auth_headers)
    assert delete_response.status_code == 204


@pytest.mark.asyncio
async def test_other_user_cannot_get_owner_rate_card(
    client: AsyncClient,
    auth_headers: dict[str, str],
    other_headers: dict[str, str],
    user_owned_rate_card: RateCardVersion,
):
    card_id = str(user_owned_rate_card.rate_card_id)

    response = await client.get(f"/rate-cards/cards/{card_id}", headers=other_headers)
    assert response.status_code == 403
    assert response.json()["code"] == "RATE_CARD_ACCESS_DENIED"

    owner_get = await client.get(f"/rate-cards/cards/{card_id}", headers=auth_headers)
    assert owner_get.status_code == 200


@pytest.mark.asyncio
async def test_other_user_cannot_assign_owner_rate_card_to_estimate(
    client: AsyncClient,
    other_headers: dict[str, str],
    user_owned_rate_card: RateCardVersion,
):
    estimate_id = await _create_estimate(client, other_headers)

    response = await client.patch(
        f"/estimates/{estimate_id}",
        json={"rate_card_id": str(user_owned_rate_card.rate_card_id)},
        headers=other_headers,
    )
    assert response.status_code == 403
    assert response.json()["code"] == "RATE_CARD_ACCESS_DENIED"


@pytest.mark.asyncio
async def test_admin_can_get_any_rate_card(
    client: AsyncClient,
    admin_headers: dict[str, str],
    user_owned_rate_card: RateCardVersion,
):
    card_id = str(user_owned_rate_card.rate_card_id)

    response = await client.get(f"/rate-cards/cards/{card_id}", headers=admin_headers)
    assert response.status_code == 200
    assert response.json()["id"] == card_id


@pytest.mark.asyncio
async def test_owner_get_active_returns_own_active_card(
    client: AsyncClient,
    auth_headers: dict[str, str],
    user_owned_rate_card: RateCardVersion,
):
    response = await client.get("/rate-cards/active", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["id"] == str(user_owned_rate_card.rate_card_id)


@pytest.mark.asyncio
async def test_other_user_get_active_when_only_admin_card_is_active(
    client: AsyncClient,
    other_headers: dict[str, str],
    db_session: AsyncSession,
    admin_user: User,
):
    for card in (await db_session.execute(select(RateCard))).scalars():
        card.is_active = False
    await db_session.commit()

    await _create_rate_card_for_user(
        db_session,
        admin_user,
        name="Admin Active Rates",
        is_active=True,
    )

    response = await client.get("/rate-cards/active", headers=other_headers)
    assert response.status_code == 404

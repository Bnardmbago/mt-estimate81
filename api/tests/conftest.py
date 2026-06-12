import uuid
from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.pool import StaticPool

from app.auth.service import create_access_token, hash_password
from app.database import Base, get_db
from app.main import app
from app.models.rate_card import RateCard, RateCardVersion
from app.models.system_config import SystemConfig
from app.models.user import User
from app.rate_cards.defaults import DEFAULT_RATE_CARD_SETTINGS

TEST_DATABASE_URL = "sqlite+aiosqlite://"


@compiles(uuid.UUID, "sqlite")
def _compile_uuid_sqlite(type_, compiler, **kw):
    return "CHAR(36)"


try:
    from sqlalchemy.dialects.postgresql import JSONB, UUID

    @compiles(JSONB, "sqlite")
    def _compile_jsonb_sqlite(type_, compiler, **kw):
        return "JSON"

    @compiles(UUID, "sqlite")
    def _compile_pg_uuid_sqlite(type_, compiler, **kw):
        return "CHAR(36)"
except ImportError:
    pass


@pytest.fixture
async def test_engine():
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    session_factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session


@pytest.fixture
async def test_user(db_session: AsyncSession) -> User:
    user = User(
        id=uuid.uuid4(),
        email="test@example.com",
        password_hash=hash_password("testpass"),
        display_name="Test User",
        is_admin=False,
        preferred_locale="en",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def other_user(db_session: AsyncSession) -> User:
    user = User(
        id=uuid.uuid4(),
        email="other@example.com",
        password_hash=hash_password("otherpass"),
        display_name="Other User",
        is_admin=False,
        preferred_locale="en",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
def other_headers(other_user: User) -> dict[str, str]:
    token = create_access_token({"sub": str(other_user.id), "is_admin": other_user.is_admin})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def admin_user(db_session: AsyncSession) -> User:
    user = User(
        id=uuid.uuid4(),
        email="admin@example.com",
        password_hash=hash_password("adminpass"),
        display_name="Admin User",
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
def auth_headers(client: AsyncClient) -> dict[str, str]:
    user = client.test_user  # type: ignore[attr-defined]
    token = create_access_token({"sub": str(user.id), "is_admin": user.is_admin})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def client(test_engine) -> AsyncGenerator[AsyncClient, None]:
    session_factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)

    user = User(
        id=uuid.uuid4(),
        email="test@example.com",
        password_hash=hash_password("testpass"),
        display_name="Test User",
        is_admin=False,
        preferred_locale="en",
    )

    async with session_factory() as session:
        session.add(user)
        session.add(SystemConfig(id=1))
        await session.commit()
        await session.refresh(user)

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        ac.test_user = user  # type: ignore[attr-defined]
        yield ac

    app.dependency_overrides.clear()


async def _create_rate_card_for_user(
    db_session: AsyncSession,
    user: User,
    *,
    name: str = "Test Rates",
    is_active: bool = True,
) -> RateCardVersion:
    rate_card = RateCard(
        name=name,
        is_active=is_active,
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
async def user_owned_rate_card(db_session: AsyncSession, client: AsyncClient) -> RateCardVersion:
    user = client.test_user  # type: ignore[attr-defined]
    return await _create_rate_card_for_user(db_session, user)


@pytest.fixture
async def active_rate_card(user_owned_rate_card: RateCardVersion) -> RateCardVersion:
    return user_owned_rate_card

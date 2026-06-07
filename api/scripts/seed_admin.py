import asyncio

from sqlalchemy import select

from app.auth.service import hash_password
from app.database import SessionLocal
from app.models.rate_card import RateCard, RateCardVersion
from app.models.user import User
from app.rate_cards.defaults import DEFAULT_RATE_CARD_NAME, DEFAULT_RATE_CARD_SETTINGS


async def _ensure_rate_card(db, admin_id) -> None:
    existing = await db.execute(select(RateCard).where(RateCard.is_active.is_(True)))
    if existing.scalar_one_or_none():
        print("Active rate card already exists")
        return

    rate_card = RateCard(
        name=DEFAULT_RATE_CARD_NAME,
        is_active=True,
        created_by=admin_id,
    )
    db.add(rate_card)
    await db.flush()

    version = RateCardVersion(
        rate_card_id=rate_card.id,
        version_number=1,
        settings=DEFAULT_RATE_CARD_SETTINGS,
    )
    db.add(version)
    print(f"Rate card created: {DEFAULT_RATE_CARD_NAME} (v1)")


async def main():
    async with SessionLocal() as db:
        existing = await db.execute(select(User).where(User.email == "admin@example.com"))
        admin = existing.scalar_one_or_none()
        if admin:
            print("Admin already exists")
        else:
            admin = User(
                email="admin@example.com",
                password_hash=hash_password("admin123"),
                display_name="Admin",
                is_admin=True,
                preferred_locale="ja",
            )
            db.add(admin)
            await db.flush()
            print("Admin created: admin@example.com / admin123")

        await _ensure_rate_card(db, admin.id)
        await db.commit()


if __name__ == "__main__":
    asyncio.run(main())

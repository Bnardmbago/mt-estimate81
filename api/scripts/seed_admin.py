import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select

from app.auth.service import hash_password
from app.database import SessionLocal
from app.models.user import User
from app.rate_cards.system import ensure_system_rate_card, sync_system_rate_card_from_defaults


async def _ensure_rate_card(db, admin: User) -> None:
    card = await ensure_system_rate_card(db, admin)
    synced = await sync_system_rate_card_from_defaults(db, admin=admin)
    print(f"System rate card ready: {synced.name} (synced from defaults if drifted)")


async def main():
    async with SessionLocal() as db:
        existing = await db.execute(select(User).where(User.email == "admin@example.com"))
        admin = existing.scalar_one_or_none()
        if admin:
            changed = False
            if not admin.is_admin:
                admin.is_admin = True
                changed = True
            if not admin.is_active:
                admin.is_active = True
                changed = True
            if not admin.preferred_currency:
                admin.preferred_currency = "JPY"
                changed = True
            if changed:
                print("Admin account restored: admin@example.com (admin access re-enabled)")
            else:
                print("Admin already exists")
        else:
            admin = User(
                email="admin@example.com",
                password_hash=hash_password("admin123"),
                display_name="Admin",
                is_admin=True,
                is_active=True,
                preferred_locale="ja",
                preferred_currency="JPY",
            )
            db.add(admin)
            await db.flush()
            print("Admin created: admin@example.com / admin123")

        await _ensure_rate_card(db, admin)
        await db.commit()


if __name__ == "__main__":
    asyncio.run(main())

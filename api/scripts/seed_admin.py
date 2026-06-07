import asyncio

from sqlalchemy import select

from app.auth.service import hash_password
from app.database import SessionLocal
from app.models.user import User


async def main():
    async with SessionLocal() as db:
        existing = await db.execute(select(User).where(User.email == "admin@example.com"))
        if existing.scalar_one_or_none():
            print("Admin already exists")
            return
        admin = User(
            email="admin@example.com",
            password_hash=hash_password("admin123"),
            display_name="Admin",
            is_admin=True,
            preferred_locale="ja",
        )
        db.add(admin)
        await db.commit()
        print("Admin created: admin@example.com / admin123")


if __name__ == "__main__":
    asyncio.run(main())

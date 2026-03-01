"""Quick script to create a user in the database."""

import asyncio
import sys

import bcrypt
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.config.settings import get_settings


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("utf-8")


async def create_user(email: str, password: str) -> None:
    settings = get_settings()
    engine = create_async_engine(settings.async_database_url)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory() as session:
        result = await session.execute(
            text("SELECT id FROM users WHERE email = :email"),
            {"email": email},
        )
        if result.scalar_one_or_none():
            print(f"User '{email}' already exists.")
            await engine.dispose()
            return

        password_hash = hash_password(password)
        await session.execute(
            text("INSERT INTO users (email, password_hash) VALUES (:email, :hash)"),
            {"email": email, "hash": password_hash},
        )
        await session.commit()
        print(f"User '{email}' created successfully.")

    await engine.dispose()


if __name__ == "__main__":
    email = sys.argv[1] if len(sys.argv) > 1 else "admin@test.com"
    password = sys.argv[2] if len(sys.argv) > 2 else "test1234"
    asyncio.run(create_user(email, password))

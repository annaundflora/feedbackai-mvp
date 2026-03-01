# backend/app/auth/repository.py
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class UserRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def get_by_email(self, email: str) -> dict[str, Any] | None:
        result = await self._db.execute(
            text("SELECT id, email, password_hash, created_at FROM users WHERE email = :email"),
            {"email": email},
        )
        row = result.mappings().one_or_none()
        return dict(row) if row else None

    async def get_by_id(self, user_id: str) -> dict[str, Any] | None:
        result = await self._db.execute(
            text("SELECT id, email, password_hash, created_at FROM users WHERE id = :id"),
            {"id": UUID(user_id)},
        )
        row = result.mappings().one_or_none()
        return dict(row) if row else None

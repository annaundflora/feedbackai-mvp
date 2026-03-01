# backend/app/auth/service.py
from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import get_settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=12)


class AuthenticationError(Exception):
    """Raised when credentials are invalid."""


class AuthService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def login(self, email: str, password: str) -> dict[str, Any]:
        """Validate credentials, return JWT access token."""
        from app.auth.repository import UserRepository

        repo = UserRepository(self._db)
        user = await repo.get_by_email(email.lower().strip())
        if user is None or not pwd_context.verify(password, user["password_hash"]):
            raise AuthenticationError("Invalid email or password")

        token = self._create_token(str(user["id"]))
        return {
            "access_token": token,
            "token_type": "bearer",
            "user": {
                "id": str(user["id"]),
                "email": user["email"],
                "created_at": user["created_at"].isoformat(),
            },
        }

    def _create_token(self, user_id: str) -> str:
        settings = get_settings()
        expire = datetime.now(timezone.utc) + timedelta(hours=24)
        payload = {"sub": user_id, "exp": expire}
        return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)

    @staticmethod
    def decode_token(token: str) -> str:
        """Decode JWT, return user_id (sub claim). Raises JWTError on failure."""
        settings = get_settings()
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
        )
        user_id: str | None = payload.get("sub")
        if user_id is None:
            raise JWTError("Missing sub claim")
        return user_id

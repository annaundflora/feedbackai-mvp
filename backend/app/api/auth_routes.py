# backend/app/api/auth_routes.py
import time
from collections import defaultdict
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.middleware import get_current_user
from app.auth.service import AuthService, AuthenticationError
from app.config.settings import Settings
from app.db.session import get_session_factory

router = APIRouter(prefix="/api/auth", tags=["auth"])

# In-memory rate limiter: max 5 login attempts per minute per IP
_login_attempts: dict[str, list[float]] = defaultdict(list)


def _check_rate_limit(client_ip: str) -> None:
    now = time.monotonic()
    _login_attempts[client_ip] = [t for t in _login_attempts[client_ip] if now - t < 60]
    if len(_login_attempts[client_ip]) >= 5:
        raise HTTPException(status_code=429, detail="Too many login attempts. Try again in 1 minute.")
    _login_attempts[client_ip].append(now)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: str
    email: str
    created_at: str


class AuthResponse(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse


@router.post("/login", response_model=AuthResponse)
async def login(
    request: Request,
    body: LoginRequest,
) -> Any:
    client_ip = request.client.host if request.client else "unknown"
    _check_rate_limit(client_ip)

    settings: Settings = request.app.state.settings
    session_factory = get_session_factory(settings)
    async with session_factory() as session:
        try:
            result = await AuthService(session).login(body.email, body.password)
        except AuthenticationError:
            raise HTTPException(status_code=401, detail="Invalid email or password")
    return result


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: dict = Depends(get_current_user),
) -> Any:
    return {
        "id": str(current_user["id"]),
        "email": current_user["email"],
        "created_at": current_user["created_at"].isoformat(),
    }

# backend/app/auth/middleware.py
from typing import AsyncGenerator

from fastapi import Depends, HTTPException, Query, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.service import AuthService
from app.config.settings import Settings
from app.db.session import get_session_factory

http_bearer = HTTPBearer()


async def _get_db_session(request: Request) -> AsyncGenerator[AsyncSession, None]:
    """FastAPI Dependency: yields a fresh AsyncSession from the request's settings."""
    settings: Settings = request.app.state.settings
    session_factory = get_session_factory(settings)
    async with session_factory() as session:
        yield session


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(http_bearer),
) -> dict:
    """FastAPI Dependency: validates Bearer token, returns user dict."""
    try:
        user_id = AuthService.decode_token(credentials.credentials)
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    from app.auth.repository import UserRepository

    settings: Settings = request.app.state.settings
    session_factory = get_session_factory(settings)
    async with session_factory() as session:
        user = await UserRepository(session).get_by_id(user_id)

    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    return user


async def get_current_user_from_token(
    request: Request,
    token: str = Query(..., description="JWT token for SSE auth"),
) -> dict:
    """FastAPI Dependency for SSE: validates ?token= query param."""
    try:
        user_id = AuthService.decode_token(token)
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    from app.auth.repository import UserRepository

    settings: Settings = request.app.state.settings
    session_factory = get_session_factory(settings)
    async with session_factory() as session:
        user = await UserRepository(session).get_by_id(user_id)

    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    return user

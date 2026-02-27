"""InterviewRepository -- CRUD fuer mvp_interviews-Tabelle.

Alle DB-Calls nutzen SQLAlchemy async Sessions mit Raw SQL.
"""
import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


class InterviewRepository:
    """Repository fuer die mvp_interviews-Tabelle.

    Kapselt alle DB-Operationen via SQLAlchemy async.
    """

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory
        self._table = "mvp_interviews"

    async def create_session(
        self,
        session_id: str,
        anonymous_id: str,
    ) -> dict[str, Any]:
        """Erstellt eine neue Interview-Session in der DB."""
        async with self._session_factory() as session:
            result = await session.execute(
                text(
                    f"INSERT INTO {self._table} (session_id, anonymous_id, status, message_count) "
                    "VALUES (:session_id, :anonymous_id, :status, :message_count) "
                    "RETURNING *"
                ),
                {
                    "session_id": session_id,
                    "anonymous_id": anonymous_id,
                    "status": "active",
                    "message_count": 0,
                },
            )
            await session.commit()
            row = result.mappings().first()
            return dict(row) if row else {}

    async def get_session(self, session_id: str) -> dict[str, Any] | None:
        """Liest eine Session aus der DB."""
        async with self._session_factory() as session:
            result = await session.execute(
                text(f"SELECT * FROM {self._table} WHERE session_id = :session_id"),
                {"session_id": session_id},
            )
            row = result.mappings().first()
            return dict(row) if row else None

    async def complete_session(
        self,
        session_id: str,
        transcript: list[dict[str, str]],
        summary: str,
        message_count: int,
        status: str = "completed",
    ) -> dict[str, Any]:
        """Schliesst eine Interview-Session ab."""
        now = datetime.now(timezone.utc)
        async with self._session_factory() as session:
            result = await session.execute(
                text(
                    f"UPDATE {self._table} SET "
                    "status = :status, "
                    "transcript = :transcript, "
                    "summary = :summary, "
                    "message_count = :message_count, "
                    "completed_at = :completed_at, "
                    "updated_at = :updated_at "
                    "WHERE session_id = :session_id "
                    "RETURNING *"
                ),
                {
                    "session_id": session_id,
                    "status": status,
                    "transcript": json.dumps(transcript),
                    "summary": summary,
                    "message_count": message_count,
                    "completed_at": now,
                    "updated_at": now,
                },
            )
            await session.commit()
            row = result.mappings().first()
            return dict(row) if row else {}

    async def get_recent_summaries(
        self,
        anonymous_id: str,
        limit: int = 3,
    ) -> list[str]:
        """Laedt die letzten N Summaries eines Users."""
        async with self._session_factory() as session:
            result = await session.execute(
                text(
                    f"SELECT summary FROM {self._table} "
                    "WHERE anonymous_id = :anonymous_id "
                    "AND status IN ('completed', 'completed_timeout') "
                    "AND summary IS NOT NULL "
                    "ORDER BY completed_at DESC "
                    "LIMIT :limit"
                ),
                {"anonymous_id": anonymous_id, "limit": limit},
            )
            rows = result.mappings().all()
            return [row["summary"] for row in rows]

    async def increment_message_count(self, session_id: str) -> None:
        """Inkrementiert den message_count einer Session atomar."""
        async with self._session_factory() as session:
            await session.execute(
                text(
                    f"UPDATE {self._table} SET "
                    "message_count = message_count + 1, "
                    "updated_at = :updated_at "
                    "WHERE session_id = :session_id"
                ),
                {
                    "session_id": session_id,
                    "updated_at": datetime.now(timezone.utc),
                },
            )
            await session.commit()

    async def update_timestamp(self, session_id: str) -> None:
        """Aktualisiert den updated_at Timestamp einer Session."""
        async with self._session_factory() as session:
            await session.execute(
                text(
                    f"UPDATE {self._table} SET updated_at = :updated_at "
                    "WHERE session_id = :session_id"
                ),
                {
                    "session_id": session_id,
                    "updated_at": datetime.now(timezone.utc),
                },
            )
            await session.commit()

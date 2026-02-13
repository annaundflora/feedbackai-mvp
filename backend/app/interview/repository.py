"""InterviewRepository -- CRUD fuer interviews-Tabelle.

Alle DB-Calls nutzen den Supabase Client und sind synchron
(supabase-py ist synchron, wird aber in async Service-Methoden aufgerufen).
"""
import asyncio
from datetime import datetime, timezone
from typing import Any

from supabase import Client

from app.config.settings import Settings


class InterviewRepository:
    """Repository fuer die interviews-Tabelle.

    Kapselt alle Supabase CRUD-Operationen.
    DB_TIMEOUT_SECONDS wird im Client konfiguriert (nicht hier).
    """

    def __init__(self, supabase_client: Client, settings: Settings) -> None:
        self._client = supabase_client
        self._settings = settings
        self._table = "interviews"

    async def create_session(
        self,
        session_id: str,
        anonymous_id: str,
    ) -> dict[str, Any]:
        """Erstellt eine neue Interview-Session in der DB.

        Args:
            session_id: UUID der Session (= LangGraph thread_id).
            anonymous_id: Client-generierte User-ID.

        Returns:
            Eingefuegte Row als Dict.
        """
        data = {
            "session_id": session_id,
            "anonymous_id": anonymous_id,
            "status": "active",
            "message_count": 0,
        }
        response = await self._execute(
            lambda: (
                self._client.table(self._table)
                .insert(data)
                .execute()
            )
        )
        return response.data[0] if response.data else {}

    async def get_session(self, session_id: str) -> dict[str, Any] | None:
        """Liest eine Session aus der DB.

        Args:
            session_id: UUID der Session.

        Returns:
            Row als Dict oder None falls nicht gefunden.
        """
        response = await self._execute(
            lambda: (
                self._client.table(self._table)
                .select("*")
                .eq("session_id", session_id)
                .execute()
            )
        )
        return response.data[0] if response.data else None

    async def complete_session(
        self,
        session_id: str,
        transcript: list[dict[str, str]],
        summary: str,
        message_count: int,
        status: str = "completed",
    ) -> dict[str, Any]:
        """Schliesst eine Interview-Session ab.

        Speichert Transkript, Summary und setzt Status auf completed.

        Args:
            session_id: UUID der Session.
            transcript: Gespraechsverlauf als Liste von {role, content} Dicts.
            summary: Zusammenfassung (Placeholder in diesem Slice).
            message_count: Anzahl User-Nachrichten.
            status: Ziel-Status ("completed" oder "completed_timeout").

        Returns:
            Aktualisierte Row als Dict.
        """
        data = {
            "status": status,
            "transcript": transcript,
            "summary": summary,
            "message_count": message_count,
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        response = await self._execute(
            lambda: (
                self._client.table(self._table)
                .update(data)
                .eq("session_id", session_id)
                .execute()
            )
        )
        return response.data[0] if response.data else {}

    async def get_recent_summaries(
        self,
        anonymous_id: str,
        limit: int = 3,
    ) -> list[str]:
        """Laedt die letzten N Summaries eines Users.

        Wird in diesem Slice implementiert, aber erst in Slice 5
        tatsaechlich von InterviewService aufgerufen.

        Args:
            anonymous_id: Client-generierte User-ID.
            limit: Maximale Anzahl Summaries (Default: 3).

        Returns:
            Liste von Summary-Strings, neueste zuerst.
        """
        response = await self._execute(
            lambda: (
                self._client.table(self._table)
                .select("summary")
                .eq("anonymous_id", anonymous_id)
                .in_("status", ["completed", "completed_timeout"])
                .not_.is_("summary", "null")
                .order("completed_at", desc=True)
                .limit(limit)
                .execute()
            )
        )
        return [row["summary"] for row in response.data] if response.data else []

    async def increment_message_count(self, session_id: str) -> None:
        """Inkrementiert den message_count einer Session.

        Nutzt direkt ein SQL-RPC oder ein einfaches Update mit aktuellem Wert.

        Args:
            session_id: UUID der Session.
        """
        # Erst aktuellen Wert lesen, dann inkrementieren
        session = await self.get_session(session_id)
        if session:
            current_count = session.get("message_count", 0)
            await self._execute(
                lambda: (
                    self._client.table(self._table)
                    .update({
                        "message_count": current_count + 1,
                        "updated_at": datetime.now(timezone.utc).isoformat(),
                    })
                    .eq("session_id", session_id)
                    .execute()
                )
            )

    async def update_timestamp(self, session_id: str) -> None:
        """Aktualisiert den updated_at Timestamp einer Session.

        Args:
            session_id: UUID der Session.
        """
        await self._execute(
            lambda: (
                self._client.table(self._table)
                .update({
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                })
                .eq("session_id", session_id)
                .execute()
            )
        )

    async def _execute(self, operation):
        """Fuehrt eine synchrone Supabase-Operation in einem Thread aus.

        supabase-py ist synchron, daher wird die Operation via
        asyncio.to_thread in einem separaten Thread ausgefuehrt,
        um den Event-Loop nicht zu blockieren.

        Args:
            operation: Callable das die Supabase-Operation ausfuehrt.

        Returns:
            Supabase API Response.

        Raises:
            asyncio.TimeoutError: DB-Call dauert laenger als DB_TIMEOUT_SECONDS.
            Exception: Supabase API Fehler.
        """
        return await asyncio.wait_for(
            asyncio.to_thread(operation),
            timeout=self._settings.db_timeout_seconds,
        )

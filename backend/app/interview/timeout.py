"""TimeoutManager -- Ueberwacht Session-Inaktivitaet und triggert Auto-Summary.

Nutzt asyncio.Task fuer jeden aktiven Timer. Bei Inaktivitaet wird
on_timeout aufgerufen, der Graph-History liest, Summary generiert und
die Session als completed_timeout in Supabase markiert.
"""
import asyncio
import logging
from typing import Awaitable, Callable

logger = logging.getLogger(__name__)


class TimeoutManager:
    """Verwaltet Session-Timeout-Timer via asyncio.Task.

    Thread-safe fuer concurrent Sessions: Jede Session hat ihren eigenen
    asyncio.Task. Tasks werden via dict[session_id -> Task] verwaltet.

    Attributes:
        _tasks: Dict von session_id zu asyncio.Task.
        _timeout_seconds: Timeout-Dauer aus Settings.
        _on_timeout_callback: Async Callback der bei Timeout aufgerufen wird.
    """

    def __init__(
        self,
        timeout_seconds: int,
        on_timeout_callback: Callable[[str], Awaitable[None]],
    ) -> None:
        """Initialisiert den TimeoutManager.

        Args:
            timeout_seconds: Sekunden bis zum Timeout (SESSION_TIMEOUT_SECONDS).
            on_timeout_callback: Async Funktion die bei Timeout aufgerufen wird.
                                  Signatur: async def callback(session_id: str) -> None
        """
        self._tasks: dict[str, asyncio.Task] = {}
        self._timeout_seconds = timeout_seconds
        self._on_timeout_callback = on_timeout_callback

    def register(self, session_id: str) -> None:
        """Registriert einen neuen Timeout-Timer fuer eine Session.

        Erstellt einen asyncio.Task der nach timeout_seconds feuert.
        Falls bereits ein Task fuer diese session_id existiert, wird
        er zuerst gecancelt.

        Args:
            session_id: UUID der Session.
        """
        # Falls schon registriert, alten Task canceln
        if session_id in self._tasks:
            self._cancel_task(session_id)

        task = asyncio.create_task(
            self._timeout_task(session_id),
            name=f"timeout-{session_id}",
        )
        self._tasks[session_id] = task
        logger.debug(f"Timeout registered for session {session_id} ({self._timeout_seconds}s)")

    def reset(self, session_id: str) -> None:
        """Setzt den Timeout-Timer einer Session zurueck.

        Cancelt den bestehenden Task und erstellt einen neuen.
        Falls keine Task fuer die session_id existiert, wird ein neuer erstellt.

        Args:
            session_id: UUID der Session.
        """
        self._cancel_task(session_id)
        task = asyncio.create_task(
            self._timeout_task(session_id),
            name=f"timeout-{session_id}",
        )
        self._tasks[session_id] = task
        logger.debug(f"Timeout reset for session {session_id} ({self._timeout_seconds}s)")

    def cancel(self, session_id: str) -> None:
        """Cancelt den Timeout-Timer einer Session.

        Wird bei explizitem /end aufgerufen. Task wird gecancelt und entfernt.

        Args:
            session_id: UUID der Session.
        """
        if session_id in self._tasks:
            self._cancel_task(session_id)
            logger.debug(f"Timeout cancelled for session {session_id}")

    def cancel_all(self) -> None:
        """Cancelt alle aktiven Timeout-Timer.

        Wird im Lifespan-Shutdown aufgerufen um alle Tasks sauber zu beenden.
        """
        session_ids = list(self._tasks.keys())
        for session_id in session_ids:
            self._cancel_task(session_id)
        logger.info(f"All timeouts cancelled ({len(session_ids)} sessions)")

    @property
    def active_count(self) -> int:
        """Gibt die Anzahl aktiver Timeout-Timer zurueck."""
        return len(self._tasks)

    async def _timeout_task(self, session_id: str) -> None:
        """Async Task der nach timeout_seconds den Callback aufruft.

        Bei CancelledError (durch reset/cancel) wird der Task still beendet.

        Args:
            session_id: UUID der Session.
        """
        try:
            await asyncio.sleep(self._timeout_seconds)
            logger.info(f"Session {session_id} timed out after {self._timeout_seconds}s")
            await self._on_timeout_callback(session_id)
        except asyncio.CancelledError:
            # Normales Verhalten bei reset() oder cancel()
            pass
        except Exception as e:
            logger.error(f"Error in timeout handler for session {session_id}: {e}")
        finally:
            # Task aus dem dict entfernen
            self._tasks.pop(session_id, None)

    def _cancel_task(self, session_id: str) -> None:
        """Cancelt einen einzelnen Task und entfernt ihn aus dem dict.

        Args:
            session_id: UUID der Session.
        """
        task = self._tasks.pop(session_id, None)
        if task and not task.done():
            task.cancel()

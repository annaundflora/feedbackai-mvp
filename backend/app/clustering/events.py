"""SseEventBus -- In-memory pub/sub Event Bus fuer SSE-Events pro Projekt.

Singleton via app.state oder Depends. Jedes Projekt bekommt eine Liste
von asyncio.Queues (eine pro SSE-Client-Verbindung).
"""
import asyncio
import logging
from collections import defaultdict
from typing import Any

logger = logging.getLogger(__name__)


class SseEventBus:
    """In-memory pub/sub Event Bus fuer SSE-Events pro Projekt.

    Jedes Projekt bekommt einen eigenen asyncio.Queue-Pool.
    Dashboard SSE-Endpoint subscribt und liefert Events.

    Pattern: Eine Queue pro SSE-Client-Verbindung pro Projekt.
    publish() sendet an alle aktiven Subscriber.
    """

    def __init__(self) -> None:
        self._queues: dict[str, list[asyncio.Queue]] = defaultdict(list)

    def subscribe(self, project_id: str) -> asyncio.Queue:
        """Erstellt einen neuen Subscriber-Queue fuer ein Projekt.

        Args:
            project_id: UUID des Projekts als String.

        Returns:
            asyncio.Queue der neue Events empfaengt.
        """
        queue: asyncio.Queue = asyncio.Queue()
        self._queues[project_id].append(queue)
        logger.debug(f"SSE subscriber added for project {project_id}, total: {len(self._queues[project_id])}")
        return queue

    def unsubscribe(self, project_id: str, queue: asyncio.Queue) -> None:
        """Entfernt einen Subscriber-Queue.

        Args:
            project_id: UUID des Projekts als String.
            queue: Die zu entfernende Queue.
        """
        if project_id in self._queues:
            try:
                self._queues[project_id].remove(queue)
                logger.debug(f"SSE subscriber removed for project {project_id}, remaining: {len(self._queues[project_id])}")
            except ValueError:
                pass  # Queue war bereits entfernt

    async def publish(self, project_id: str, event_type: str, data: dict[str, Any]) -> None:
        """Sendet ein Event an alle Subscriber eines Projekts.

        Falls kein Subscriber vorhanden: No-Op (kein Fehler).

        Args:
            project_id: UUID des Projekts als String.
            event_type: z.B. "fact_extracted", "clustering_started".
            data: Event-Daten gemaess architecture.md SSE Event Types.
        """
        event = {"type": event_type, **data}
        subscribers = self._queues.get(project_id, [])
        if not subscribers:
            logger.debug(f"No SSE subscribers for project {project_id}, event {event_type} dropped")
            return

        for queue in subscribers:
            await queue.put(event)

        logger.debug(f"SSE event '{event_type}' published to {len(subscribers)} subscriber(s) for project {project_id}")

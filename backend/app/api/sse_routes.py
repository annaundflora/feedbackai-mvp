"""SSE Route fuer Live-Updates pro Projekt.

GET /api/projects/{project_id}/events
  - Auth: JWT via ?token= Query-Parameter (EventSource unterstuetzt keine Headers)
  - Owner-Check: Projekt muss dem aktuellen User gehoeren
  - Heartbeat alle 30s damit Proxy/Load-Balancer die Verbindung offen haelt
  - Queue-Cleanup via finally-Block (verhindert Queue-Akkumulation)

Slice 8: Echte JWT-Validierung via get_current_user_from_token aus app.auth.middleware.
"""
import asyncio
import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import text
from sse_starlette.sse import EventSourceResponse

from app.api.dependencies import get_sse_event_bus
from app.auth.middleware import get_current_user_from_token
from app.clustering.events import SseEventBus
from app.config.settings import Settings
from app.db.session import get_session_factory

logger = logging.getLogger(__name__)

router = APIRouter()


async def _get_project_by_id_no_user_filter(project_id: str, request: Request) -> dict | None:
    """Laedt ein Projekt ohne User-Filter (fuer SSE Owner-Check)."""
    settings: Settings = request.app.state.settings
    session_factory = get_session_factory(settings)

    async with session_factory() as session:
        result = await session.execute(
            text("SELECT id, user_id FROM projects WHERE id = :project_id"),
            {"project_id": project_id},
        )
        row = result.mappings().first()
        return dict(row) if row else None


@router.get("/api/projects/{project_id}/events")
async def project_events(
    project_id: str,
    request: Request,
    token: str = Query(..., description="JWT token (EventSource cannot send headers)"),
    event_bus: SseEventBus = Depends(get_sse_event_bus),
    current_user: dict = Depends(get_current_user_from_token),
) -> EventSourceResponse:
    """SSE-Stream fuer Live-Updates eines Projekts.

    Auth: JWT via ?token= Query-Parameter (EventSource supports no headers).
    Owner-Check: Projekt muss dem aktuellen User gehoeren.

    Events (gemaess architecture.md SSE Event Types):
    - fact_extracted: {interview_id, fact_count}
    - clustering_started: {mode: "incremental"|"full"}
    - clustering_progress: {interview_id, step, completed, total}
    - clustering_updated: {clusters: [{id, name, fact_count}]}
    - clustering_completed: {cluster_count, fact_count}
    - clustering_failed: {error, unassigned_count}
    - suggestion: {type, source_cluster_id, ...}
    - summary_updated: {cluster_id}

    Heartbeat: Alle 30s ein Comment-Event (": heartbeat") damit Proxy/Load-Balancer
    idle Verbindungen nicht schliesst.

    Status Codes:
    - 200 OK: SSE stream gestartet
    - 401 Unauthorized: JWT invalid oder fehlend
    - 403 Forbidden: Projekt gehoert nicht dem aktuellen User
    - 404 Not Found: Projekt nicht gefunden
    """
    # Projekt-Existenz pruefen
    project = await _get_project_by_id_no_user_filter(project_id, request)

    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    # Owner-Check: Projekt muss dem aktuellen User gehoeren
    project_user_id = str(project.get("user_id", ""))
    current_user_id = str(current_user.get("id", ""))

    if project_user_id and current_user_id and project_user_id != current_user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    logger.info(f"SSE client connected for project {project_id}")

    queue = event_bus.subscribe(project_id)

    async def event_generator():
        try:
            # Heartbeat alle 30s damit Proxy/Load-Balancer Verbindung offen haelt
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=30.0)
                    yield {
                        "event": event["type"],
                        "data": json.dumps({k: v for k, v in event.items() if k != "type"}),
                    }
                except asyncio.TimeoutError:
                    # Heartbeat -- leeres Comment-Event (SSE spec: lines starting with ":")
                    yield {"comment": "heartbeat"}
        finally:
            event_bus.unsubscribe(project_id, queue)
            logger.info(f"SSE client disconnected for project {project_id}")

    return EventSourceResponse(event_generator())

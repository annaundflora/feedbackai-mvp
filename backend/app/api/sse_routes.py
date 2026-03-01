"""SSE Route fuer Live-Updates pro Projekt.

GET /api/projects/{project_id}/events
  - Auth: JWT via ?token= Query-Parameter (EventSource unterstuetzt keine Headers)
  - Owner-Check: Projekt muss dem aktuellen User gehoeren
  - Heartbeat alle 30s damit Proxy/Load-Balancer die Verbindung offen haelt
  - Queue-Cleanup via finally-Block (verhindert Queue-Akkumulation)

Slice 7: Stub-Auth (kein echtes JWT) -- Slice 8 implementiert echte JWT-Validierung.
"""
import asyncio
import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import text
from sse_starlette.sse import EventSourceResponse

from app.api.dependencies import get_sse_event_bus
from app.clustering.events import SseEventBus
from app.config.settings import Settings
from app.db.session import get_session_factory

logger = logging.getLogger(__name__)

router = APIRouter()


async def get_current_user_from_token(
    token: str = Query(..., description="JWT token (EventSource cannot send headers)"),
) -> dict:
    """FastAPI Dependency: Validiert JWT aus Query-Parameter.

    EventSource API unterstuetzt keine custom HTTP-Headers, daher wird der JWT
    als Query-Parameter uebergeben.

    Slice 7: Stub-Implementation -- akzeptiert beliebigen non-empty Token.
    Slice 8: Wird durch echte JWT-Validierung ersetzt.

    Returns:
        dict mit User-Daten (id, email)
    """
    if not token:
        raise HTTPException(status_code=401, detail="Missing authentication token")

    # Slice 7 Stub: Fixer Entwickler-User (wird in Slice 8 durch echte JWT-Validierung ersetzt)
    return {
        "id": "00000000-0000-0000-0000-000000000001",
        "email": "dev@feedbackai.com",
    }


async def _get_project_by_id_no_user_filter(project_id: str, request: Request) -> dict | None:
    """Laedt ein Projekt ohne User-Filter (fuer SSE Owner-Check).

    Slice 7: Benoetigt wegen Stub-Auth (kein echtes JWT mit User-ID).
    Slice 8: Wird durch get_current_user() Dependency ersetzt.
    """
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

    # Owner-Check (Slice 8 aktiviert echte user_id Validierung via JWT)
    project_user_id = str(project.get("user_id", ""))
    current_user_id = str(current_user.get("id", ""))

    # Slice 7 Stub: Der Stub-User "00000000-..." besitzt alle Projekte in Development
    # Wenn das Projekt einem ANDEREN User gehoert, wird 403 zurueckgegeben
    # Dies wird in Slice 8 durch echte JWT-basierte User-ID ersetzt
    if project_user_id and current_user_id:
        # Nur wenn beide IDs bekannt und verschieden: 403
        # Im Stub-Mode (token="dev" etc.) wird der Check grosszuegig gehandhabt
        if (project_user_id != current_user_id and
                project_user_id != "00000000-0000-0000-0000-000000000001"):
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

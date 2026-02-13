# Slice 3: SSE-Streaming Endpoints aufsetzen

> **Slice 3 von 6** fuer `Backend-Kern`
>
> | Navigation | |
> |------------|---|
> | **Vorheriger:** | `slice-02-langgraph-interview.md` |
> | **Naechster:** | `slice-04-supabase-persistenz.md` |

---

## Metadata (fuer Orchestrator)

| Key | Value |
|-----|-------|
| **ID** | `slice-03-sse-streaming` |
| **Test** | `cd backend && python -m pytest tests/slices/backend-kern/test_slice_03_sse_streaming.py -v` |
| **E2E** | `false` |
| **Dependencies** | `["slice-01-app-skeleton", "slice-02-langgraph-interview"]` |

---

## Slice-Uebersicht

| # | Slice | Status | Datei |
|---|-------|--------|-------|
| 1 | App-Skeleton + DDD-Struktur | Done | `slice-01-app-skeleton.md` |
| 2 | LangGraph Interview-Graph | Done | `slice-02-langgraph-interview.md` |
| 3 | SSE-Streaming Endpoints | Ready | `slice-03-sse-streaming.md` |
| 4 | Supabase-Persistenz | Pending | `slice-04-supabase-persistenz.md` |
| 5 | Summary-Generierung + Injection | Pending | `slice-05-summary-injection.md` |
| 6 | Session-Timeout + Auto-Summary | Pending | `slice-06-session-timeout.md` |

---

## Kontext & Ziel

Der Interview-Graph (Slice 2) ist standalone nutzbar, aber noch nicht per HTTP erreichbar. Dieser Slice macht den Graph ueber 3 REST-Endpoints verfuegbar und implementiert SSE-Streaming fuer die LLM-Antworten.

Scope dieses Slices:
- `POST /api/interview/start` -- SSE-Stream: Opening-Frage + metadata mit session_id
- `POST /api/interview/message` -- SSE-Stream: Interviewer-Antwort
- `POST /api/interview/end` -- JSON: Placeholder-Summary (echte Summary kommt in Slice 5)
- SSE Wire Format: `data: {"type": "text-delta|text-done|metadata|error", ...}\n\n`
- InterviewService als Orchestrator (Session-Management in-memory)
- Pydantic DTOs fuer Request/Response-Validation
- FastAPI Dependency Injection fuer Service-Instanzen

**WICHTIG -- Abgrenzung:**
- KEINE Supabase-Persistenz (kommt in Slice 4)
- KEINE echte Summary-Generierung (kommt in Slice 5)
- KEIN Timeout-Management (kommt in Slice 6)
- Session-Management ist rein In-Memory (Python Dict)

---

## Technische Umsetzung

### Architektur-Kontext (aus architecture.md)

> **Quelle:** `architecture.md` -> API Design + Server Logic + Architecture Layers

```
Client (curl -N)
  |
  v
api/routes.py          <-- HTTP Request + Pydantic Validation (schemas.py)
  |
  v
api/dependencies.py    <-- FastAPI Depends() fuer InterviewService
  |
  v
interview/service.py   <-- InterviewService: Session-Mgmt + Graph-Orchestration
  |
  v
interview/graph.py     <-- InterviewGraph (aus Slice 2): LLM-Streaming
  |
  v
SSE Response           <-- EventSourceResponse (sse-starlette)
```

### 1. Architektur-Impact

| Layer | Aenderungen |
|-------|-------------|
| `backend/app/api/schemas.py` | NEU: Pydantic DTOs (StartRequest, MessageRequest, EndRequest, EndResponse, ErrorResponse) |
| `backend/app/api/routes.py` | NEU: FastAPI Router mit 3 Endpoints (/start, /message, /end) |
| `backend/app/api/dependencies.py` | NEU: FastAPI Depends() fuer InterviewService + InterviewGraph |
| `backend/app/interview/service.py` | NEU: InterviewService (Session-Lifecycle, In-Memory Dict) |
| `backend/app/main.py` | MODIFY: Router einbinden via `app.include_router()` |

### 2. Datenfluss

```
POST /api/interview/start {"anonymous_id": "user-1"}
  |
  v
StartRequest Pydantic Validation
  |
  v
InterviewService.start(anonymous_id)
  1. session_id = uuid4()
  2. sessions[session_id] = {status: "active", anonymous_id, message_count: 0, ...}
  3. graph.astream(messages=[], session_id) -> Opening-Frage Chunks
  |
  v
SSE Stream:
  data: {"type": "text-delta", "content": "Hallo"}\n\n
  data: {"type": "text-delta", "content": "! Wie"}\n\n
  ...
  data: {"type": "text-done"}\n\n
  data: {"type": "metadata", "session_id": "uuid-here"}\n\n

---

POST /api/interview/message {"session_id": "uuid", "message": "Das Bidding nervt"}
  |
  v
MessageRequest Pydantic Validation
  |
  v
InterviewService.message(session_id, message)
  1. Validate session exists + status="active"
  2. graph.astream(messages=[HumanMessage(message)], session_id) -> Antwort Chunks
  3. sessions[session_id]["message_count"] += 1
  |
  v
SSE Stream:
  data: {"type": "text-delta", "content": "Was genau"}\n\n
  ...
  data: {"type": "text-done"}\n\n

---

POST /api/interview/end {"session_id": "uuid"}
  |
  v
EndRequest Pydantic Validation
  |
  v
InterviewService.end(session_id)
  1. Validate session exists + status="active"
  2. history = graph.get_history(session_id)
  3. message_count = sessions[session_id]["message_count"]
  4. sessions[session_id]["status"] = "completed"
  5. Return placeholder summary
  |
  v
JSON Response: {"summary": "Summary-Generierung noch nicht implementiert (Slice 5)", "message_count": 3}
```

### 3. Pydantic DTOs (schemas.py)

> **Quelle:** `architecture.md` -> API Design -> Data Transfer Objects

```python
# backend/app/api/schemas.py
from pydantic import BaseModel, Field, field_validator
import re


class StartRequest(BaseModel):
    """Request fuer POST /api/interview/start."""
    anonymous_id: str = Field(..., min_length=1, max_length=255)

    @field_validator("anonymous_id")
    @classmethod
    def strip_whitespace(cls, v: str) -> str:
        return v.strip()


class MessageRequest(BaseModel):
    """Request fuer POST /api/interview/message."""
    session_id: str
    message: str = Field(..., min_length=1, max_length=10000)

    @field_validator("session_id")
    @classmethod
    def validate_uuid_format(cls, v: str) -> str:
        uuid_pattern = re.compile(
            r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
            re.IGNORECASE,
        )
        if not uuid_pattern.match(v):
            raise ValueError("Invalid session_id format")
        return v

    @field_validator("message")
    @classmethod
    def strip_message_whitespace(cls, v: str) -> str:
        return v.strip()


class EndRequest(BaseModel):
    """Request fuer POST /api/interview/end."""
    session_id: str

    @field_validator("session_id")
    @classmethod
    def validate_uuid_format(cls, v: str) -> str:
        uuid_pattern = re.compile(
            r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
            re.IGNORECASE,
        )
        if not uuid_pattern.match(v):
            raise ValueError("Invalid session_id format")
        return v


class EndResponse(BaseModel):
    """Response fuer POST /api/interview/end."""
    summary: str
    message_count: int


class ErrorResponse(BaseModel):
    """Einheitliches Fehler-Format."""
    error: str
    detail: str | None = None
```

### 4. InterviewService (service.py)

> **Quelle:** `architecture.md` -> Server Logic -> InterviewService

Der InterviewService orchestriert den Interview-Lifecycle. In diesem Slice nutzt er ein In-Memory Dict fuer Session-Management (Supabase kommt in Slice 4).

```python
# backend/app/interview/service.py
import uuid
import json
from datetime import datetime, timezone
from typing import AsyncGenerator

from langchain_core.messages import HumanMessage, AIMessageChunk

from app.interview.graph import InterviewGraph


class SessionNotFoundError(Exception):
    """Session-ID existiert nicht."""
    pass


class SessionAlreadyCompletedError(Exception):
    """Session wurde bereits beendet."""
    pass


class InterviewService:
    """Orchestriert den Interview-Lifecycle.

    Session-Management via In-Memory Dict (wird in Slice 4 durch Supabase ergaenzt).
    """

    def __init__(self, graph: InterviewGraph) -> None:
        self._graph = graph
        self._sessions: dict[str, dict] = {}

    async def start(self, anonymous_id: str) -> AsyncGenerator[str, None]:
        """Startet ein neues Interview.

        1. Erstellt session_id (UUID)
        2. Registriert Session in-memory
        3. Streamt Opening-Frage via Graph
        4. Sendet metadata mit session_id

        Args:
            anonymous_id: Client-generierte User-ID.

        Yields:
            SSE-formatierte JSON-Strings (text-delta, text-done, metadata).
        """
        session_id = str(uuid.uuid4())
        self._sessions[session_id] = {
            "status": "active",
            "anonymous_id": anonymous_id,
            "message_count": 0,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        try:
            async for sse_line in self._stream_graph(
                messages=[],
                session_id=session_id,
            ):
                yield sse_line

            # Nach text-done: metadata mit session_id senden
            yield json.dumps({"type": "metadata", "session_id": session_id})
        except Exception as e:
            yield json.dumps({"type": "error", "message": str(e)})

    async def message(self, session_id: str, message: str) -> AsyncGenerator[str, None]:
        """Verarbeitet eine User-Nachricht und streamt die Antwort.

        1. Validiert Session (existiert, status=active)
        2. Streamt Antwort via Graph
        3. Inkrementiert message_count

        Args:
            session_id: Session-UUID.
            message: User-Nachricht.

        Yields:
            SSE-formatierte JSON-Strings (text-delta, text-done).

        Raises:
            SessionNotFoundError: Session existiert nicht.
            SessionAlreadyCompletedError: Session wurde bereits beendet.
        """
        self._validate_session(session_id)

        try:
            async for sse_line in self._stream_graph(
                messages=[HumanMessage(content=message)],
                session_id=session_id,
            ):
                yield sse_line

            self._sessions[session_id]["message_count"] += 1
        except (SessionNotFoundError, SessionAlreadyCompletedError):
            raise
        except Exception as e:
            yield json.dumps({"type": "error", "message": str(e)})

    async def end(self, session_id: str) -> dict:
        """Beendet ein Interview.

        1. Validiert Session (existiert, status=active)
        2. Liest History aus Graph
        3. Setzt status auf "completed"
        4. Gibt Placeholder-Summary zurueck (echte Summary in Slice 5)

        Args:
            session_id: Session-UUID.

        Returns:
            Dict mit summary und message_count.

        Raises:
            SessionNotFoundError: Session existiert nicht.
            SessionAlreadyCompletedError: Session wurde bereits beendet.
        """
        self._validate_session(session_id)

        message_count = self._sessions[session_id]["message_count"]
        self._sessions[session_id]["status"] = "completed"

        return {
            "summary": "Summary-Generierung noch nicht implementiert (Slice 5)",
            "message_count": message_count,
        }

    async def _stream_graph(
        self,
        messages: list,
        session_id: str,
    ) -> AsyncGenerator[str, None]:
        """Streamt Graph-Output als SSE-formatierte JSON-Strings.

        Filtert nur AIMessageChunks mit Content (keine Metadata-Chunks).

        Args:
            messages: Input-Messages fuer den Graph.
            session_id: Session-UUID (thread_id fuer MemorySaver).

        Yields:
            SSE-formatierte JSON-Strings.
        """
        async for chunk, metadata in self._graph.astream(
            messages=messages,
            session_id=session_id,
        ):
            # Nur AIMessageChunks mit Content streamen
            if isinstance(chunk, AIMessageChunk) and chunk.content:
                yield json.dumps({"type": "text-delta", "content": chunk.content})

        # Stream abgeschlossen
        yield json.dumps({"type": "text-done"})

    def _validate_session(self, session_id: str) -> None:
        """Prueft ob Session existiert und aktiv ist.

        Args:
            session_id: Session-UUID.

        Raises:
            SessionNotFoundError: Session existiert nicht.
            SessionAlreadyCompletedError: Session ist nicht mehr aktiv.
        """
        if session_id not in self._sessions:
            raise SessionNotFoundError(f"Session not found: {session_id}")

        if self._sessions[session_id]["status"] != "active":
            raise SessionAlreadyCompletedError(f"Session already completed: {session_id}")
```

### 5. FastAPI Routes (routes.py)

> **Quelle:** `architecture.md` -> API Design -> Endpoints

```python
# backend/app/api/routes.py
import json
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sse_starlette.sse import EventSourceResponse

from app.api.schemas import (
    StartRequest,
    MessageRequest,
    EndRequest,
    EndResponse,
    ErrorResponse,
)
from app.api.dependencies import get_interview_service
from app.interview.service import (
    InterviewService,
    SessionNotFoundError,
    SessionAlreadyCompletedError,
)


router = APIRouter(prefix="/api/interview", tags=["interview"])


@router.post("/start")
async def start_interview(
    request: StartRequest,
    service: InterviewService = Depends(get_interview_service),
):
    """Startet ein neues Interview und streamt die Opening-Frage via SSE.

    SSE Events:
    - text-delta: Token-Chunks der Opening-Frage
    - text-done: Opening-Frage komplett
    - metadata: session_id fuer weitere Requests
    - error: Bei LLM-Fehlern
    """

    async def event_generator():
        async for sse_data in service.start(request.anonymous_id):
            yield {"data": sse_data}

    return EventSourceResponse(event_generator())


@router.post("/message")
async def send_message(
    request: MessageRequest,
    service: InterviewService = Depends(get_interview_service),
):
    """Sendet eine Nachricht und streamt die Interviewer-Antwort via SSE.

    SSE Events:
    - text-delta: Token-Chunks der Antwort
    - text-done: Antwort komplett
    - error: Bei LLM-Fehlern
    """
    try:
        service._validate_session(request.session_id)
    except SessionNotFoundError:
        return JSONResponse(
            status_code=404,
            content=ErrorResponse(
                error="Session not found",
                detail=f"No active session with id {request.session_id}",
            ).model_dump(),
        )
    except SessionAlreadyCompletedError:
        return JSONResponse(
            status_code=409,
            content=ErrorResponse(
                error="Session already completed",
                detail=f"Session {request.session_id} has already been completed",
            ).model_dump(),
        )

    async def event_generator():
        async for sse_data in service.message(request.session_id, request.message):
            yield {"data": sse_data}

    return EventSourceResponse(event_generator())


@router.post("/end")
async def end_interview(
    request: EndRequest,
    service: InterviewService = Depends(get_interview_service),
):
    """Beendet ein Interview und gibt eine Placeholder-Summary zurueck.

    Returns:
        EndResponse mit summary und message_count.
    """
    try:
        result = await service.end(request.session_id)
    except SessionNotFoundError:
        return JSONResponse(
            status_code=404,
            content=ErrorResponse(
                error="Session not found",
                detail=f"No active session with id {request.session_id}",
            ).model_dump(),
        )
    except SessionAlreadyCompletedError:
        return JSONResponse(
            status_code=409,
            content=ErrorResponse(
                error="Session already completed",
                detail=f"Session {request.session_id} has already been completed",
            ).model_dump(),
        )

    return EndResponse(
        summary=result["summary"],
        message_count=result["message_count"],
    )
```

### 6. Dependency Injection (dependencies.py)

```python
# backend/app/api/dependencies.py
from functools import lru_cache
from fastapi import Request

from app.config.settings import Settings
from app.interview.graph import InterviewGraph
from app.interview.service import InterviewService


_interview_service: InterviewService | None = None


def get_interview_service(request: Request) -> InterviewService:
    """FastAPI Dependency fuer InterviewService (Singleton).

    Erstellt InterviewService + InterviewGraph beim ersten Aufruf.
    Nutzt app.state.settings aus Slice 1 Lifespan.
    """
    global _interview_service
    if _interview_service is None:
        settings: Settings = request.app.state.settings
        graph = InterviewGraph(settings=settings)
        _interview_service = InterviewService(graph=graph)
    return _interview_service


def reset_interview_service() -> None:
    """Setzt den Singleton zurueck (fuer Tests)."""
    global _interview_service
    _interview_service = None
```

### 7. main.py Anpassung

> **Quelle:** `architecture.md` -> Architecture Layers -> Transport Layer

```python
# backend/app/main.py -- MODIFY: Router einbinden
# Nach der bestehenden Health-Check Route:
from app.api.routes import router as interview_router

app.include_router(interview_router)
```

Die vollstaendige `main.py` nach der Aenderung:

```python
# backend/app/main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config.settings import Settings
from app.api.routes import router as interview_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    settings = Settings()
    app.state.settings = settings
    yield
    # Shutdown (cleanup spaeter)


app = FastAPI(
    title="FeedbackAI Backend",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    return {"status": "ok"}


app.include_router(interview_router)
```

### 8. SSE Wire Format Details

> **Quelle:** `architecture.md` -> API Design -> SSE Event Format

| Event Type | JSON Payload | Wann |
|------------|-------------|------|
| `text-delta` | `{"type": "text-delta", "content": "Chunk..."}` | Jeder Token/Chunk vom LLM |
| `text-done` | `{"type": "text-done"}` | LLM-Antwort komplett |
| `metadata` | `{"type": "metadata", "session_id": "uuid"}` | Nach text-done bei /start |
| `error` | `{"type": "error", "message": "..."}` | Bei LLM-Fehlern waehrend Streaming |

**Wire Format Beispiel (raw):**
```
data: {"type": "text-delta", "content": "Wie"}\n\n
data: {"type": "text-delta", "content": " geht"}\n\n
data: {"type": "text-delta", "content": " es"}\n\n
data: {"type": "text-done"}\n\n
data: {"type": "metadata", "session_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"}\n\n
```

**WICHTIG:** Das `data: ` Prefix und `\n\n` Suffix werden automatisch von `EventSourceResponse` hinzugefuegt. Der Service yieldet nur den JSON-String.

### 9. Externe Services/APIs

| Service | Zweck | Integration |
|---------|-------|-------------|
| sse-starlette | SSE-Transport fuer FastAPI | `api/routes.py` via `EventSourceResponse` |
| InterviewGraph (Slice 2) | LLM-Streaming | `interview/service.py` via `graph.astream()` |

**Error Handling:**
- `asyncio.TimeoutError` vom Graph -> SSE error-Event an Client
- `openai.APIError` vom LLM -> SSE error-Event an Client
- Session-Fehler (404, 409) -> JSON ErrorResponse (VOR dem SSE-Stream)

### 10. Abhaengigkeiten

- Bestehend: `sse-starlette` (bereits in requirements.txt)
- Bestehend: `fastapi`, `pydantic` (bereits in requirements.txt)
- Neu: Keine neuen Dependencies noetig

### 11. Wiederverwendete Code-Bausteine

| Funktion | Datei | Rueckgabetyp | Wichtige Hinweise |
|----------|-------|-------------|-------------------|
| `InterviewGraph` | `app/interview/graph.py` | Klasse | Aus Slice 2: `.astream()`, `.get_history()` Methoden |
| `InterviewGraph.astream()` | `app/interview/graph.py` | `AsyncGenerator[(chunk, metadata)]` | Yieldet `(AIMessageChunk, dict)` Tuples |
| `Settings` | `app/config/settings.py` | `Settings` Instanz | Aus Slice 1: Zugriff via `request.app.state.settings` |
| `app.state.settings` | `app/main.py` | `Settings` | Aus Slice 1: Lifespan setzt Settings |

---

## Integrations-Checkliste (Pflicht bei Backend-Aenderungen)

### 1. State-Integration
- [x] Kein eigener State -- nutzt InterviewGraph State (Slice 2)
- [x] In-Memory Sessions Dict ist internes Implementation Detail
- [x] Rueckgabetypen explizit: `EndResponse` (Pydantic), SSE-Strings, `ErrorResponse` (Pydantic)

### 2. LangGraph-Integration
- [x] `InterviewGraph.astream()` wird fuer SSE-Streaming genutzt
- [x] `InterviewGraph.get_history()` wird in Slice 5 fuer Summary genutzt (in diesem Slice noch nicht aufgerufen)
- [x] thread_id = session_id (konsistent mit Slice 2)

### 3. LLM-Integration
- [x] Keine direkte LLM-Integration -- geht ueber InterviewGraph (Slice 2)
- [x] Error-Handling fuer LLM-Fehler via try/except in _stream_graph und start/message

### 4. Datenbank-Integration
- [x] Nicht betroffen (kommt in Slice 4)

### 5. Utility-Funktionen
- [x] Settings aus Slice 1 wiederverwendet (via app.state.settings)
- [x] InterviewGraph aus Slice 2 wiederverwendet

### 6. Feature-Aktivierung
- [x] Router wird in `main.py` via `app.include_router(interview_router)` registriert
- [x] InterviewService wird als Singleton via Dependency Injection bereitgestellt
- [x] Endpoints sofort verfuegbar nach Server-Start

### 7. Datenfluss-Vollstaendigkeit
- [x] Request: Pydantic DTOs (StartRequest, MessageRequest, EndRequest) -> Validation
- [x] Service: In-Memory Sessions Dict + InterviewGraph
- [x] Response: SSE-Stream (EventSourceResponse) oder JSON (EndResponse/ErrorResponse)
- [x] Transformationen: `AIMessageChunk.content` -> `{"type": "text-delta", "content": "..."}` -> `data: ...\n\n`

---

## UI Anforderungen

Keine UI in diesem Slice (Backend-only).

---

## Acceptance Criteria

1) GIVEN der Backend-Server laeuft
   WHEN ein POST-Request an `/api/interview/start` mit `{"anonymous_id": "test-user-1"}` gesendet wird
   THEN wird ein SSE-Stream zurueckgegeben mit Content-Type `text/event-stream`, der mindestens ein `text-delta` Event, ein `text-done` Event und ein `metadata` Event mit einer validen `session_id` (UUID-Format) enthaelt

2) GIVEN ein laufendes Interview mit bekannter session_id
   WHEN ein POST-Request an `/api/interview/message` mit `{"session_id": "<id>", "message": "Das Bidding nervt"}` gesendet wird
   THEN wird ein SSE-Stream zurueckgegeben mit mindestens einem `text-delta` Event und einem `text-done` Event

3) GIVEN ein laufendes Interview mit bekannter session_id
   WHEN ein POST-Request an `/api/interview/end` mit `{"session_id": "<id>"}` gesendet wird
   THEN wird eine JSON-Response mit `{"summary": "...", "message_count": <n>}` und HTTP 200 zurueckgegeben

4) GIVEN kein Interview gestartet
   WHEN ein POST-Request an `/api/interview/message` mit `{"session_id": "00000000-0000-0000-0000-000000000000", "message": "Test"}` gesendet wird
   THEN wird HTTP 404 mit `{"error": "Session not found", "detail": "..."}` zurueckgegeben

5) GIVEN ein bereits beendetes Interview
   WHEN ein POST-Request an `/api/interview/message` oder `/api/interview/end` mit dessen session_id gesendet wird
   THEN wird HTTP 409 mit `{"error": "Session already completed", "detail": "..."}` zurueckgegeben

6) GIVEN ein POST-Request an `/api/interview/start`
   WHEN `anonymous_id` leer ist oder fehlt
   THEN wird HTTP 422 (Pydantic Validation Error) zurueckgegeben

7) GIVEN ein POST-Request an `/api/interview/message`
   WHEN `session_id` kein gueltiges UUID-Format hat
   THEN wird HTTP 422 (Pydantic Validation Error) zurueckgegeben

8) GIVEN ein POST-Request an `/api/interview/message`
   WHEN `message` leer ist oder mehr als 10000 Zeichen hat
   THEN wird HTTP 422 (Pydantic Validation Error) zurueckgegeben

9) GIVEN ein POST-Request an `/api/interview/start`
   WHEN der LLM-Call fehlschlaegt (Timeout oder API-Error)
   THEN wird ein SSE error-Event `{"type": "error", "message": "..."}` gesendet

10) GIVEN ein POST-Request an `/api/interview/message` mit einer gueltige session_id
    WHEN die Antwort fertig gestreamt ist
    THEN wurde der `message_count` der Session um 1 inkrementiert

11) GIVEN zwei separate POST /start Requests
    WHEN beide mit verschiedenen anonymous_ids gestartet werden
    THEN erhalten sie verschiedene session_ids und ihre Sessions sind voneinander isoliert

---

## Testfaelle

**WICHTIG:** Tests muessen VOR der Implementierung definiert werden! Der Orchestrator fuehrt diese Tests automatisch nach der Slice-Implementierung aus.

### Test-Datei

**Fuer diesen Slice:** `backend/tests/slices/backend-kern/test_slice_03_sse_streaming.py`

### Unit Tests (pytest)

<test_spec>
```python
# backend/tests/slices/backend-kern/test_slice_03_sse_streaming.py
import pytest
import json
import re
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessageChunk, AIMessage, HumanMessage


# -- Fixtures --

@pytest.fixture(autouse=True)
def reset_service_singleton():
    """Setzt den InterviewService-Singleton vor jedem Test zurueck."""
    from app.api.dependencies import reset_interview_service
    reset_interview_service()
    yield
    reset_interview_service()


@pytest.fixture
def mock_graph():
    """Mock InterviewGraph der vordefinierte Chunks streamt."""
    graph = AsyncMock()

    async def mock_astream(messages, session_id):
        chunks = [
            (AIMessageChunk(content="Hallo"), {"langgraph_node": "interviewer"}),
            (AIMessageChunk(content="! Wie"), {"langgraph_node": "interviewer"}),
            (AIMessageChunk(content=" geht es dir?"), {"langgraph_node": "interviewer"}),
        ]
        for chunk in chunks:
            yield chunk

    graph.astream = mock_astream
    graph.get_history.return_value = [
        HumanMessage(content="Test"),
        AIMessage(content="Antwort"),
    ]
    return graph


@pytest.fixture
def client(mock_graph):
    """TestClient mit gemocktem InterviewService."""
    with patch.dict("os.environ", {
        "OPENROUTER_API_KEY": "test-key",
        "SUPABASE_URL": "https://test.supabase.co",
        "SUPABASE_KEY": "test-supabase-key",
    }, clear=False):
        from app.interview.service import InterviewService
        from app.api import dependencies

        service = InterviewService(graph=mock_graph)
        dependencies._interview_service = service

        from app.main import app
        with TestClient(app) as c:
            yield c


def parse_sse_events(response_text: str) -> list[dict]:
    """Parst SSE-Response Text in eine Liste von Events."""
    events = []
    for line in response_text.strip().split("\n"):
        line = line.strip()
        if line.startswith("data: "):
            data_str = line[6:]
            try:
                events.append(json.loads(data_str))
            except json.JSONDecodeError:
                pass
    return events


# -- POST /api/interview/start --

class TestStartInterview:
    """AC 1, 6, 9, 11: POST /api/interview/start."""

    def test_start_returns_sse_stream(self, client):
        """AC 1: Start gibt SSE-Stream zurueck."""
        response = client.post(
            "/api/interview/start",
            json={"anonymous_id": "test-user-1"},
        )
        assert response.status_code == 200
        assert "text/event-stream" in response.headers.get("content-type", "")

    def test_start_stream_contains_text_delta(self, client):
        """AC 1: Stream enthaelt text-delta Events."""
        response = client.post(
            "/api/interview/start",
            json={"anonymous_id": "test-user-1"},
        )
        events = parse_sse_events(response.text)
        text_deltas = [e for e in events if e.get("type") == "text-delta"]
        assert len(text_deltas) >= 1
        assert "content" in text_deltas[0]

    def test_start_stream_contains_text_done(self, client):
        """AC 1: Stream enthaelt text-done Event."""
        response = client.post(
            "/api/interview/start",
            json={"anonymous_id": "test-user-1"},
        )
        events = parse_sse_events(response.text)
        text_done = [e for e in events if e.get("type") == "text-done"]
        assert len(text_done) == 1

    def test_start_stream_contains_metadata_with_session_id(self, client):
        """AC 1: Stream enthaelt metadata Event mit UUID session_id."""
        response = client.post(
            "/api/interview/start",
            json={"anonymous_id": "test-user-1"},
        )
        events = parse_sse_events(response.text)
        metadata = [e for e in events if e.get("type") == "metadata"]
        assert len(metadata) == 1
        session_id = metadata[0]["session_id"]
        uuid_pattern = re.compile(
            r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
            re.IGNORECASE,
        )
        assert uuid_pattern.match(session_id)

    def test_start_empty_anonymous_id_returns_422(self, client):
        """AC 6: Leere anonymous_id gibt 422."""
        response = client.post(
            "/api/interview/start",
            json={"anonymous_id": ""},
        )
        assert response.status_code == 422

    def test_start_missing_anonymous_id_returns_422(self, client):
        """AC 6: Fehlende anonymous_id gibt 422."""
        response = client.post(
            "/api/interview/start",
            json={},
        )
        assert response.status_code == 422

    def test_start_different_users_get_different_sessions(self, client):
        """AC 11: Verschiedene Users bekommen verschiedene session_ids."""
        resp1 = client.post(
            "/api/interview/start",
            json={"anonymous_id": "user-a"},
        )
        resp2 = client.post(
            "/api/interview/start",
            json={"anonymous_id": "user-b"},
        )
        events1 = parse_sse_events(resp1.text)
        events2 = parse_sse_events(resp2.text)
        meta1 = [e for e in events1 if e.get("type") == "metadata"][0]
        meta2 = [e for e in events2 if e.get("type") == "metadata"][0]
        assert meta1["session_id"] != meta2["session_id"]

    def test_start_llm_error_sends_sse_error_event(self, client, mock_graph):
        """AC 9: LLM-Fehler wird als SSE error-Event gesendet."""
        # mock_graph.astream so konfigurieren dass Exception geworfen wird
        async def failing_astream(messages, session_id):
            raise Exception("LLM unavailable")
            yield  # make it a generator

        mock_graph.astream = failing_astream

        response = client.post(
            "/api/interview/start",
            json={"anonymous_id": "test-user-1"},
        )
        events = parse_sse_events(response.text)
        error_events = [e for e in events if e.get("type") == "error"]
        assert len(error_events) >= 1
        assert "message" in error_events[0]
        assert "LLM unavailable" in error_events[0]["message"]


# -- POST /api/interview/message --

class TestSendMessage:
    """AC 2, 4, 5, 7, 8, 10: POST /api/interview/message."""

    def _start_session(self, client) -> str:
        """Hilfsfunktion: Startet Session und gibt session_id zurueck."""
        response = client.post(
            "/api/interview/start",
            json={"anonymous_id": "test-user"},
        )
        events = parse_sse_events(response.text)
        metadata = [e for e in events if e.get("type") == "metadata"][0]
        return metadata["session_id"]

    def test_message_returns_sse_stream(self, client):
        """AC 2: Message gibt SSE-Stream zurueck."""
        session_id = self._start_session(client)
        response = client.post(
            "/api/interview/message",
            json={"session_id": session_id, "message": "Test Nachricht"},
        )
        assert response.status_code == 200
        assert "text/event-stream" in response.headers.get("content-type", "")

    def test_message_stream_contains_text_delta_and_done(self, client):
        """AC 2: Stream enthaelt text-delta und text-done."""
        session_id = self._start_session(client)
        response = client.post(
            "/api/interview/message",
            json={"session_id": session_id, "message": "Das Bidding nervt"},
        )
        events = parse_sse_events(response.text)
        text_deltas = [e for e in events if e.get("type") == "text-delta"]
        text_done = [e for e in events if e.get("type") == "text-done"]
        assert len(text_deltas) >= 1
        assert len(text_done) == 1

    def test_message_unknown_session_returns_404(self, client):
        """AC 4: Unbekannte session_id gibt 404."""
        response = client.post(
            "/api/interview/message",
            json={
                "session_id": "00000000-0000-0000-0000-000000000000",
                "message": "Test",
            },
        )
        assert response.status_code == 404
        body = response.json()
        assert body["error"] == "Session not found"

    def test_message_completed_session_returns_409(self, client):
        """AC 5: Beendete Session gibt 409."""
        session_id = self._start_session(client)
        # Session beenden
        client.post(
            "/api/interview/end",
            json={"session_id": session_id},
        )
        # Nochmal message senden
        response = client.post(
            "/api/interview/message",
            json={"session_id": session_id, "message": "Nochmal"},
        )
        assert response.status_code == 409
        body = response.json()
        assert body["error"] == "Session already completed"

    def test_message_invalid_uuid_returns_422(self, client):
        """AC 7: Ungueltige UUID gibt 422."""
        response = client.post(
            "/api/interview/message",
            json={"session_id": "not-a-uuid", "message": "Test"},
        )
        assert response.status_code == 422

    def test_message_empty_message_returns_422(self, client):
        """AC 8: Leere Nachricht gibt 422."""
        session_id = self._start_session(client)
        response = client.post(
            "/api/interview/message",
            json={"session_id": session_id, "message": ""},
        )
        assert response.status_code == 422

    def test_message_too_long_returns_422(self, client):
        """AC 8: Zu lange Nachricht (>10000 Zeichen) gibt 422."""
        session_id = self._start_session(client)
        response = client.post(
            "/api/interview/message",
            json={"session_id": session_id, "message": "x" * 10001},
        )
        assert response.status_code == 422

    def test_message_increments_count(self, client):
        """AC 10: message_count wird inkrementiert."""
        session_id = self._start_session(client)
        # Zwei Nachrichten senden
        client.post(
            "/api/interview/message",
            json={"session_id": session_id, "message": "Erste"},
        )
        client.post(
            "/api/interview/message",
            json={"session_id": session_id, "message": "Zweite"},
        )
        # Session beenden -> message_count pruefen
        response = client.post(
            "/api/interview/end",
            json={"session_id": session_id},
        )
        body = response.json()
        assert body["message_count"] == 2


# -- POST /api/interview/end --

class TestEndInterview:
    """AC 3, 4, 5: POST /api/interview/end."""

    def _start_session(self, client) -> str:
        """Hilfsfunktion: Startet Session und gibt session_id zurueck."""
        response = client.post(
            "/api/interview/start",
            json={"anonymous_id": "test-user"},
        )
        events = parse_sse_events(response.text)
        metadata = [e for e in events if e.get("type") == "metadata"][0]
        return metadata["session_id"]

    def test_end_returns_json_with_summary(self, client):
        """AC 3: End gibt JSON mit summary zurueck."""
        session_id = self._start_session(client)
        response = client.post(
            "/api/interview/end",
            json={"session_id": session_id},
        )
        assert response.status_code == 200
        body = response.json()
        assert "summary" in body
        assert isinstance(body["summary"], str)
        assert len(body["summary"]) > 0

    def test_end_returns_message_count(self, client):
        """AC 3: End gibt message_count zurueck."""
        session_id = self._start_session(client)
        response = client.post(
            "/api/interview/end",
            json={"session_id": session_id},
        )
        body = response.json()
        assert "message_count" in body
        assert isinstance(body["message_count"], int)

    def test_end_unknown_session_returns_404(self, client):
        """AC 4: Unbekannte session_id gibt 404."""
        response = client.post(
            "/api/interview/end",
            json={"session_id": "00000000-0000-0000-0000-000000000000"},
        )
        assert response.status_code == 404

    def test_end_already_completed_returns_409(self, client):
        """AC 5: Bereits beendete Session gibt 409."""
        session_id = self._start_session(client)
        client.post(
            "/api/interview/end",
            json={"session_id": session_id},
        )
        response = client.post(
            "/api/interview/end",
            json={"session_id": session_id},
        )
        assert response.status_code == 409


# -- Pydantic DTOs --

class TestSchemas:
    """DTO-Validation."""

    def test_start_request_strips_whitespace(self):
        """anonymous_id wird getrimmt."""
        from app.api.schemas import StartRequest
        req = StartRequest(anonymous_id="  test-user  ")
        assert req.anonymous_id == "test-user"

    def test_message_request_validates_uuid(self):
        """session_id muss UUID-Format haben."""
        from app.api.schemas import MessageRequest
        with pytest.raises(Exception):
            MessageRequest(session_id="not-a-uuid", message="Test")

    def test_message_request_accepts_valid_uuid(self):
        """Gueltige UUID wird akzeptiert."""
        from app.api.schemas import MessageRequest
        req = MessageRequest(
            session_id="a1b2c3d4-e5f6-7890-abcd-ef1234567890",
            message="Test",
        )
        assert req.session_id == "a1b2c3d4-e5f6-7890-abcd-ef1234567890"

    def test_message_request_strips_message_whitespace(self):
        """message wird getrimmt."""
        from app.api.schemas import MessageRequest
        req = MessageRequest(
            session_id="a1b2c3d4-e5f6-7890-abcd-ef1234567890",
            message="  Test Nachricht  ",
        )
        assert req.message == "Test Nachricht"

    def test_end_response_model(self):
        """EndResponse hat korrekte Felder."""
        from app.api.schemas import EndResponse
        resp = EndResponse(summary="Test Summary", message_count=5)
        assert resp.summary == "Test Summary"
        assert resp.message_count == 5

    def test_error_response_model(self):
        """ErrorResponse hat korrekte Felder."""
        from app.api.schemas import ErrorResponse
        resp = ErrorResponse(error="Test Error", detail="Details")
        assert resp.error == "Test Error"
        assert resp.detail == "Details"

    def test_error_response_optional_detail(self):
        """ErrorResponse detail ist optional."""
        from app.api.schemas import ErrorResponse
        resp = ErrorResponse(error="Test Error")
        assert resp.detail is None


# -- InterviewService --

class TestInterviewService:
    """Service-Logik direkt testen."""

    @pytest.mark.asyncio
    async def test_start_creates_session(self, mock_graph):
        """start() erstellt eine neue Session."""
        from app.interview.service import InterviewService
        service = InterviewService(graph=mock_graph)
        events = []
        async for event_data in service.start("test-user"):
            events.append(json.loads(event_data))
        metadata = [e for e in events if e.get("type") == "metadata"]
        assert len(metadata) == 1
        session_id = metadata[0]["session_id"]
        assert session_id in service._sessions
        assert service._sessions[session_id]["status"] == "active"

    @pytest.mark.asyncio
    async def test_validate_session_not_found(self, mock_graph):
        """_validate_session wirft SessionNotFoundError."""
        from app.interview.service import InterviewService, SessionNotFoundError
        service = InterviewService(graph=mock_graph)
        with pytest.raises(SessionNotFoundError):
            service._validate_session("nonexistent-id")

    @pytest.mark.asyncio
    async def test_validate_session_already_completed(self, mock_graph):
        """_validate_session wirft SessionAlreadyCompletedError."""
        from app.interview.service import InterviewService, SessionAlreadyCompletedError
        service = InterviewService(graph=mock_graph)
        # Session manuell erstellen und beenden
        service._sessions["test-id"] = {"status": "completed"}
        with pytest.raises(SessionAlreadyCompletedError):
            service._validate_session("test-id")

    @pytest.mark.asyncio
    async def test_end_returns_placeholder_summary(self, mock_graph):
        """end() gibt Placeholder-Summary zurueck."""
        from app.interview.service import InterviewService
        service = InterviewService(graph=mock_graph)
        # Session starten
        async for _ in service.start("test-user"):
            pass
        session_id = list(service._sessions.keys())[0]
        result = await service.end(session_id)
        assert "summary" in result
        assert "message_count" in result
        assert service._sessions[session_id]["status"] == "completed"


# -- SSE Wire Format --

class TestSSEWireFormat:
    """SSE-Daten-Format validieren."""

    def test_text_delta_format(self):
        """text-delta Events haben type und content."""
        event = json.loads('{"type": "text-delta", "content": "Hallo"}')
        assert event["type"] == "text-delta"
        assert event["content"] == "Hallo"

    def test_text_done_format(self):
        """text-done Events haben nur type."""
        event = json.loads('{"type": "text-done"}')
        assert event["type"] == "text-done"

    def test_metadata_format(self):
        """metadata Events haben type und session_id."""
        event = json.loads('{"type": "metadata", "session_id": "test-uuid"}')
        assert event["type"] == "metadata"
        assert event["session_id"] == "test-uuid"

    def test_error_format(self):
        """error Events haben type und message."""
        event = json.loads('{"type": "error", "message": "LLM unavailable"}')
        assert event["type"] == "error"
        assert event["message"] == "LLM unavailable"


# -- Module-Existenz --

class TestModuleStructure:
    """Alle neuen Dateien existieren und sind importierbar."""

    def test_schemas_importable(self):
        """api/schemas.py ist importierbar."""
        from app.api.schemas import (
            StartRequest,
            MessageRequest,
            EndRequest,
            EndResponse,
            ErrorResponse,
        )
        assert StartRequest is not None
        assert MessageRequest is not None
        assert EndRequest is not None
        assert EndResponse is not None
        assert ErrorResponse is not None

    def test_routes_importable(self):
        """api/routes.py ist importierbar."""
        from app.api.routes import router
        assert router is not None

    def test_dependencies_importable(self):
        """api/dependencies.py ist importierbar."""
        from app.api.dependencies import get_interview_service, reset_interview_service
        assert get_interview_service is not None
        assert reset_interview_service is not None

    def test_service_importable(self):
        """interview/service.py ist importierbar."""
        from app.interview.service import (
            InterviewService,
            SessionNotFoundError,
            SessionAlreadyCompletedError,
        )
        assert InterviewService is not None
        assert SessionNotFoundError is not None
        assert SessionAlreadyCompletedError is not None
```
</test_spec>

### Manuelle Tests

1. Interview starten (SSE-Stream):
   ```bash
   curl -N -X POST http://localhost:8000/api/interview/start \
     -H "Content-Type: application/json" \
     -d '{"anonymous_id": "test-user-1"}'
   ```
   Erwartung: SSE-Stream mit text-delta Chunks, text-done, metadata mit session_id

2. Nachricht senden (SSE-Stream):
   ```bash
   curl -N -X POST http://localhost:8000/api/interview/message \
     -H "Content-Type: application/json" \
     -d '{"session_id": "<session_id>", "message": "Das Bidding ist frustrierend"}'
   ```
   Erwartung: SSE-Stream mit text-delta Chunks und text-done

3. Interview beenden (JSON):
   ```bash
   curl -X POST http://localhost:8000/api/interview/end \
     -H "Content-Type: application/json" \
     -d '{"session_id": "<session_id>"}'
   ```
   Erwartung: `{"summary": "...", "message_count": 1}`

---

## Definition of Done

- [x] Akzeptanzkriterien sind eindeutig & vollstaendig
- [x] Kein Logging/Telemetrie in diesem Slice (LangSmith-Tracing ist automatisch via LangGraph)
- [x] Sicherheits-/Privacy-Aspekte bedacht (Input-Validation via Pydantic, keine PII-Speicherung)
- [x] Kein UI in diesem Slice
- [x] Kein Rollout/Rollback noetig

---

## Constraints & Hinweise

**Betrifft:**
- Dieser Slice macht den Interview-Graph per HTTP erreichbar
- SSE-Format muss kompatibel sein mit assistant-ui LocalRuntime (Phase 2)
- InterviewService ist der zentrale Orchestrator fuer alle weiteren Slices

**API Contract:**
- `POST /api/interview/start` -> SSE-Stream (text-delta, text-done, metadata)
- `POST /api/interview/message` -> SSE-Stream (text-delta, text-done)
- `POST /api/interview/end` -> JSON EndResponse
- Error Responses: 404 (Session not found), 409 (Session already completed), 422 (Validation)

**Abgrenzung:**
- Keine Supabase-Persistenz (kommt in Slice 4)
- Keine echte Summary-Generierung im /end Endpoint (kommt in Slice 5)
- Kein Timeout-Management (kommt in Slice 6)
- `message_count` wird in-memory gezaehlt (Persistenz in Slice 4)

---

## Integration Contract (GATE 2 PFLICHT)

### Requires From Other Slices

| Slice | Resource | Type | Validation |
|-------|----------|------|------------|
| slice-01-app-skeleton | `app.main:app` | FastAPI App | `app.include_router()` funktioniert, `app.state.settings` verfuegbar |
| slice-01-app-skeleton | `Settings` | Pydantic BaseSettings | `from app.config.settings import Settings` importierbar |
| slice-02-langgraph-interview | `InterviewGraph` | Klasse | `InterviewGraph(settings)` instanziierbar, `.astream()` und `.get_history()` verfuegbar |
| slice-02-langgraph-interview | `InterviewGraph.astream()` | Async Generator | `(messages, session_id) -> AsyncGenerator[(AIMessageChunk, dict)]` |

### Provides To Other Slices

| Resource | Type | Consumer | Interface |
|----------|------|----------|-----------|
| `InterviewService` | Klasse | Slice 4 (DB-Integration), Slice 5 (Summary), Slice 6 (Timeout) | `InterviewService(graph) -> .start(), .message(), .end()` |
| `InterviewService._sessions` | In-Memory Dict | Slice 4 (wird durch DB ersetzt) | `{session_id: {status, anonymous_id, message_count, created_at}}` |
| `SessionNotFoundError` | Exception | Slice 4, 5, 6 | Error-Handling fuer ungueltige Sessions |
| `SessionAlreadyCompletedError` | Exception | Slice 4, 5, 6 | Error-Handling fuer beendete Sessions |
| `StartRequest` | Pydantic Model | Slice 4 | `anonymous_id: str` (validated) |
| `MessageRequest` | Pydantic Model | -- | `session_id: str, message: str` (validated) |
| `EndRequest` | Pydantic Model | -- | `session_id: str` (validated) |
| `EndResponse` | Pydantic Model | Slice 5 (wird erweitert) | `summary: str, message_count: int` |
| `get_interview_service` | FastAPI Dependency | Routes | `Depends(get_interview_service) -> InterviewService` |
| API Endpoints | HTTP Routes | Phase 2 (Widget), curl-Tests | `/api/interview/start`, `/message`, `/end` |

### Integration Validation Tasks

- [ ] `InterviewGraph` aus Slice 2 ist importierbar und instanziierbar
- [ ] `app.state.settings` aus Slice 1 ist im Lifespan verfuegbar
- [ ] `InterviewGraph.astream()` yieldet `(AIMessageChunk, metadata)` Tuples
- [ ] Router ist via `app.include_router()` in main.py eingebunden
- [ ] SSE-Format ist kompatibel mit dem in architecture.md spezifizierten Wire Format

---

## Code Examples (MANDATORY - GATE 2 PFLICHT)

> **KRITISCH:** Alle Code-Beispiele in diesem Dokument sind **PFLICHT-Deliverables**.
> Der Gate 2 Compliance Agent prueft, dass jedes Code-Beispiel implementiert wird.
> Abweichung nur mit expliziter Begruendung im Commit erlaubt.

| Code Example | Section | Mandatory | Notes |
|--------------|---------|-----------|-------|
| `StartRequest`, `MessageRequest`, `EndRequest`, `EndResponse`, `ErrorResponse` | Section 3 (Pydantic DTOs) | YES | Alle Felder + Validators wie spezifiziert |
| `InterviewService` Klasse | Section 4 (InterviewService) | YES | `start()`, `message()`, `end()`, `_validate_session()`, `_stream_graph()` |
| `router` mit 3 Endpoints | Section 5 (FastAPI Routes) | YES | `/start` (SSE), `/message` (SSE), `/end` (JSON) |
| `get_interview_service`, `reset_interview_service` | Section 6 (Dependency Injection) | YES | Singleton-Pattern mit Reset fuer Tests |
| `main.py` Router-Integration | Section 7 (main.py) | YES | `app.include_router(interview_router)` |

---

## Deliverables (SCOPE SAFEGUARD)

**WICHTIG: Diese Liste wird automatisch vom Stop-Hook validiert. Der Agent kann nicht stoppen, wenn Dateien fehlen.**

<!-- DELIVERABLES_START -->
### Backend
- [ ] `backend/app/api/schemas.py` -- Pydantic DTOs: StartRequest, MessageRequest, EndRequest, EndResponse, ErrorResponse mit Validators
- [ ] `backend/app/api/routes.py` -- FastAPI Router: POST /api/interview/start (SSE), POST /api/interview/message (SSE), POST /api/interview/end (JSON)
- [ ] `backend/app/api/dependencies.py` -- FastAPI Dependency Injection: get_interview_service (Singleton), reset_interview_service (Test-Helper)
- [ ] `backend/app/interview/service.py` -- InterviewService: start(), message(), end(), _validate_session(), _stream_graph(), SessionNotFoundError, SessionAlreadyCompletedError
- [ ] `backend/app/main.py` -- MODIFY: `app.include_router(interview_router)` hinzufuegen

### Tests
- [ ] `backend/tests/slices/backend-kern/test_slice_03_sse_streaming.py` -- pytest Tests fuer alle 3 Endpoints, DTOs, Service-Logik, SSE-Format, Error-Handling (404, 409, 422), LLM-Error SSE-Event (AC 9)
<!-- DELIVERABLES_END -->

**Hinweis fuer den Implementierungs-Agent:**
- Alle Dateien zwischen `<!-- DELIVERABLES_START -->` und `<!-- DELIVERABLES_END -->` sind **Pflicht**
- Der Stop-Hook prueft automatisch ob alle Dateien existieren
- Bei fehlenden Dateien wird der Agent blockiert und muss nachfragen

# Slice 4: Supabase-Persistenz aufsetzen

> **Slice 4 von 6** fuer `Backend-Kern`
>
> | Navigation | |
> |------------|---|
> | **Vorheriger:** | `slice-03-sse-streaming.md` |
> | **Naechster:** | `slice-05-summary-injection.md` |

---

## Metadata (fuer Orchestrator)

| Key | Value |
|-----|-------|
| **ID** | `slice-04-supabase-persistenz` |
| **Test** | `cd backend && python -m pytest tests/slices/backend-kern/test_slice_04_supabase_persistenz.py -v` |
| **E2E** | `false` |
| **Dependencies** | `["slice-01-app-skeleton", "slice-03-sse-streaming"]` |

---

## Slice-Uebersicht

| # | Slice | Status | Datei |
|---|-------|--------|-------|
| 1 | App-Skeleton + DDD-Struktur | Done | `slice-01-app-skeleton.md` |
| 2 | LangGraph Interview-Graph | Done | `slice-02-langgraph-interview.md` |
| 3 | SSE-Streaming Endpoints | Done | `slice-03-sse-streaming.md` |
| 4 | Supabase-Persistenz | Ready | `slice-04-supabase-persistenz.md` |
| 5 | Summary-Generierung + Injection | Pending | `slice-05-summary-injection.md` |
| 6 | Session-Timeout + Auto-Summary | Pending | `slice-06-session-timeout.md` |

---

## Kontext & Ziel

Bis jetzt werden Interview-Sessions nur in-memory verwaltet (Python Dict in `InterviewService._sessions`). Transkripte und Summaries gehen bei Server-Restart verloren, und es gibt keine Moeglichkeit, Summaries vorheriger Sessions zu laden.

Dieser Slice fuehrt Supabase-Persistenz ein:
- Supabase Client Singleton (`db/supabase.py`)
- SQL Migration Script fuer die `interviews`-Tabelle
- InterviewRepository mit CRUD-Operationen
- Integration in InterviewService: Bei `/start` wird ein DB-Insert gemacht (status=active), bei `/end` werden Transkript und Placeholder-Summary gespeichert (echte Summary-Generierung in Slice 5)
- DB_TIMEOUT_SECONDS als Timeout fuer alle DB-Calls
- `get_recent_summaries()` wird implementiert, aber erst in Slice 5 mit echten Daten genutzt

**Aktuelle Probleme:**
1. Kein Supabase Client existiert (`db/supabase.py` ist leer/fehlt)
2. Keine `interviews`-Tabelle in Supabase (Migration fehlt)
3. Kein InterviewRepository (`interview/repository.py` fehlt)
4. InterviewService speichert nichts in der Datenbank
5. Sessions ueberleben keinen Server-Restart

---

## Technische Umsetzung

### Architektur-Kontext (aus architecture.md)

> **Quelle:** `architecture.md` -> Database Schema + Architecture Layers + Server Logic

```
interview/service.py   <-- Orchestration (erweitert in diesem Slice)
  |
  +---> interview/repository.py <-- NEU: DB-Zugriff (Supabase CRUD)
  |      +-- db/supabase.py        <-- NEU: Shared Supabase Client
  |
  +---> interview/graph.py      <-- Unveraendert (aus Slice 2)
```

### 1. Architektur-Impact

| Layer | Aenderungen |
|-------|-------------|
| `backend/app/db/supabase.py` | NEU: Supabase Client Singleton mit Timeout-Konfiguration |
| `backend/app/interview/repository.py` | NEU: InterviewRepository (CRUD fuer interviews-Tabelle) |
| `backend/app/interview/service.py` | MODIFY: DB-Insert bei start(), DB-Update bei end(), Repository-Injection |
| `backend/app/api/dependencies.py` | MODIFY: InterviewRepository erstellen und an InterviewService uebergeben |
| `backend/migrations/001_create_interviews.sql` | NEU: SQL Migration Script |

### 2. Datenfluss

```
POST /api/interview/start {"anonymous_id": "user-1"}
  |
  v
InterviewService.start(anonymous_id)
  1. session_id = uuid4()
  2. sessions[session_id] = {status: "active", ...}     <-- In-Memory Cache (bleibt)
  3. repository.create_session(session_id, anonymous_id)  <-- NEU: DB-Insert
  // Slice 5: repository.get_recent_summaries(anonymous_id, limit=3)
  // Slice 5: PromptAssembler.build(base_prompt, summaries)
  4. graph.astream(messages=[], session_id) -> SSE
  // Slice 6: TimeoutManager.register(session_id)
  |
  v
Supabase INSERT: interviews (session_id, anonymous_id, status="active")

---

POST /api/interview/message {"session_id": "uuid", "message": "..."}
  |
  v
InterviewService.message(session_id, message)
  1. _validate_session(session_id)
  2. graph.astream(...) -> SSE
  3. sessions[session_id]["message_count"] += 1
  4. repository.increment_message_count(session_id)       <-- NEU: DB message_count++ & updated_at
  // Slice 6: TimeoutManager.reset(session_id)

---

POST /api/interview/end {"session_id": "uuid"}
  |
  v
InterviewService.end(session_id)
  1. _validate_session(session_id)
  // Slice 6: TimeoutManager.cancel(session_id)
  2. history = graph.get_history(session_id)
  3. transcript = _format_transcript(history)              <-- NEU: Messages -> JSONB
  4. placeholder_summary = "..."
  5. repository.complete_session(                           <-- NEU: DB-Update
       session_id, transcript, placeholder_summary, message_count)
  6. sessions[session_id]["status"] = "completed"
  7. Return {summary, message_count}
```

### 3. Supabase Client Singleton (db/supabase.py)

> **Quelle:** `architecture.md` -> Architecture Layers -> Infrastructure (db/supabase.py)

```python
# backend/app/db/supabase.py
"""Supabase Client Singleton.

Erstellt eine einzelne Supabase-Client-Instanz die von allen
Repositories geteilt wird. Konfiguriert mit DB_TIMEOUT_SECONDS.
"""
from supabase import create_client, Client
from app.config.settings import Settings


_supabase_client: Client | None = None


def get_supabase_client(settings: Settings) -> Client:
    """Gibt den Supabase Client Singleton zurueck.

    Erstellt den Client beim ersten Aufruf mit den Settings.
    Nachfolgende Aufrufe geben dieselbe Instanz zurueck.

    Args:
        settings: Pydantic Settings mit SUPABASE_URL und SUPABASE_KEY.

    Returns:
        Konfigurierter Supabase Client.
    """
    global _supabase_client
    if _supabase_client is None:
        _supabase_client = create_client(
            settings.supabase_url,
            settings.supabase_key,
            options=_build_client_options(settings),
        )
    return _supabase_client


def _build_client_options(settings: Settings):
    """Erstellt ClientOptions mit Timeout-Konfiguration.

    Args:
        settings: Pydantic Settings mit db_timeout_seconds.

    Returns:
        ClientOptions mit konfiguriertem Timeout.
    """
    from supabase.lib.client_options import ClientOptions
    from postgrest.constants import DEFAULT_POSTGREST_CLIENT_TIMEOUT

    timeout = settings.db_timeout_seconds
    return ClientOptions(
        postgrest_client_timeout=timeout,
    )


def reset_supabase_client() -> None:
    """Setzt den Client-Singleton zurueck (fuer Tests)."""
    global _supabase_client
    _supabase_client = None
```

### 4. SQL Migration Script

> **Quelle:** `architecture.md` -> Database Schema -> SQL Migration

```sql
-- backend/migrations/001_create_interviews.sql
-- Migration: Create interviews table
-- Date: 2026-02-13
-- Description: Speichert Interview-Sessions mit Transkript und Summary

CREATE TABLE IF NOT EXISTS interviews (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  anonymous_id TEXT NOT NULL,
  session_id UUID NOT NULL UNIQUE,
  status TEXT NOT NULL DEFAULT 'active'
    CHECK (status IN ('active', 'completed', 'completed_timeout')),
  transcript JSONB,
  summary TEXT,
  message_count INTEGER NOT NULL DEFAULT 0,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  completed_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_interviews_anonymous_id ON interviews(anonymous_id);
CREATE INDEX IF NOT EXISTS idx_interviews_session_id ON interviews(session_id);
CREATE INDEX IF NOT EXISTS idx_interviews_status ON interviews(status);
```

**Ausfuehrung:** Manuell im Supabase Dashboard SQL Editor oder via `psql`. Keine automatische Migration in MVP.

### 5. InterviewRepository (repository.py)

> **Quelle:** `architecture.md` -> Server Logic -> InterviewRepository

```python
# backend/app/interview/repository.py
"""InterviewRepository -- CRUD fuer interviews-Tabelle.

Alle DB-Calls nutzen den Supabase Client und sind synchron
(supabase-py ist synchron, wird aber in async Service-Methoden aufgerufen).
"""
import asyncio
from datetime import datetime, timezone
from functools import partial
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
```

### 6. InterviewService Erweiterung (service.py)

> **Quelle:** `architecture.md` -> Server Logic -> Business Logic Flow

Die bestehende `InterviewService` aus Slice 3 wird erweitert:
- Constructor akzeptiert zusaetzlich ein `InterviewRepository`
- `start()` macht DB-Insert nach Session-Erstellung
- `message()` inkrementiert message_count in DB und aktualisiert Timestamp
- `end()` formatiert Transkript und speichert in DB
- Neue Methode `_format_transcript()` konvertiert Messages zu JSONB-Format
- In-Memory `_sessions` Dict bleibt als Cache, DB ist Source of Truth

```python
# backend/app/interview/service.py
# MODIFY: Bestehende Klasse erweitern
import uuid
import json
import logging
from datetime import datetime, timezone
from typing import AsyncGenerator

from langchain_core.messages import HumanMessage, AIMessage, AIMessageChunk

from app.interview.graph import InterviewGraph
from app.interview.repository import InterviewRepository


logger = logging.getLogger(__name__)


class SessionNotFoundError(Exception):
    """Session-ID existiert nicht."""
    pass


class SessionAlreadyCompletedError(Exception):
    """Session wurde bereits beendet."""
    pass


class InterviewService:
    """Orchestriert den Interview-Lifecycle.

    Session-Management via In-Memory Dict (Cache) + Supabase (Source of Truth).
    """

    def __init__(
        self,
        graph: InterviewGraph,
        repository: InterviewRepository | None = None,
    ) -> None:
        self._graph = graph
        self._repository = repository
        self._sessions: dict[str, dict] = {}

    async def start(self, anonymous_id: str) -> AsyncGenerator[str, None]:
        """Startet ein neues Interview.

        1. Erstellt session_id (UUID)
        2. Registriert Session in-memory
        3. Erstellt Session in Supabase
        4. Streamt Opening-Frage via Graph
        5. Sendet metadata mit session_id

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

        # DB-Insert (non-blocking, Fehler werden geloggt aber blockieren nicht)
        if self._repository:
            try:
                await self._repository.create_session(session_id, anonymous_id)
            except Exception as e:
                logger.error(f"DB create_session failed for {session_id}: {e}")

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
        3. Inkrementiert message_count (in-memory + DB)

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

            # DB message_count + timestamp update
            if self._repository:
                try:
                    await self._repository.increment_message_count(session_id)
                except Exception as e:
                    logger.error(f"DB increment_message_count failed for {session_id}: {e}")
        except (SessionNotFoundError, SessionAlreadyCompletedError):
            raise
        except Exception as e:
            yield json.dumps({"type": "error", "message": str(e)})

    async def end(self, session_id: str) -> dict:
        """Beendet ein Interview.

        1. Validiert Session (existiert, status=active)
        2. Liest History aus Graph
        3. Formatiert Transkript als JSONB
        4. Speichert Transkript + Placeholder-Summary in Supabase
        5. Setzt status auf "completed"

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

        # Transkript aus Graph-History lesen und formatieren
        history = self._graph.get_history(session_id)
        transcript = self._format_transcript(history)

        placeholder_summary = "Summary-Generierung noch nicht implementiert (Slice 5)"

        # DB-Update: Transkript + Summary speichern
        if self._repository:
            try:
                await self._repository.complete_session(
                    session_id=session_id,
                    transcript=transcript,
                    summary=placeholder_summary,
                    message_count=message_count,
                )
            except Exception as e:
                logger.error(f"DB complete_session failed for {session_id}: {e}")

        self._sessions[session_id]["status"] = "completed"

        return {
            "summary": placeholder_summary,
            "message_count": message_count,
        }

    @staticmethod
    def _format_transcript(messages: list) -> list[dict[str, str]]:
        """Konvertiert LangChain Messages in JSONB-kompatibles Format.

        Args:
            messages: Liste von LangChain Message-Objekten.

        Returns:
            Liste von {role, content} Dicts fuer JSONB-Speicherung.
        """
        transcript = []
        for msg in messages:
            if isinstance(msg, HumanMessage):
                transcript.append({"role": "user", "content": msg.content})
            elif isinstance(msg, AIMessage):
                transcript.append({"role": "assistant", "content": msg.content})
        return transcript

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

### 7. Dependency Injection Erweiterung (dependencies.py)

```python
# backend/app/api/dependencies.py
# MODIFY: Repository in InterviewService injizieren
from fastapi import Request

from app.config.settings import Settings
from app.interview.graph import InterviewGraph
from app.interview.service import InterviewService
from app.interview.repository import InterviewRepository
from app.db.supabase import get_supabase_client


_interview_service: InterviewService | None = None


def get_interview_service(request: Request) -> InterviewService:
    """FastAPI Dependency fuer InterviewService (Singleton).

    Erstellt InterviewService + InterviewGraph + InterviewRepository beim ersten Aufruf.
    Nutzt app.state.settings aus Slice 1 Lifespan.
    """
    global _interview_service
    if _interview_service is None:
        settings: Settings = request.app.state.settings
        graph = InterviewGraph(settings=settings)
        supabase_client = get_supabase_client(settings)
        repository = InterviewRepository(
            supabase_client=supabase_client,
            settings=settings,
        )
        _interview_service = InterviewService(
            graph=graph,
            repository=repository,
        )
    return _interview_service


def reset_interview_service() -> None:
    """Setzt den Singleton zurueck (fuer Tests)."""
    global _interview_service
    _interview_service = None
```

### 8. Externe Services/APIs

| Service | Zweck | Integration |
|---------|-------|-------------|
| Supabase (PostgreSQL) | Persistenz fuer Interview-Sessions | `interview/repository.py` via `supabase-py` Client |

**Konfiguration:**
- `SUPABASE_URL`: Supabase Project URL (Pflicht, via Settings)
- `SUPABASE_KEY`: Supabase API Key (Pflicht, via Settings)
- `DB_TIMEOUT_SECONDS`: Timeout fuer DB-Calls, Default 10 (via Settings)

**Error Handling:**
- `asyncio.TimeoutError`: DB-Call dauert laenger als `DB_TIMEOUT_SECONDS` -> wird geloggt, blockiert nicht den Interview-Flow
- Supabase API Fehler -> wird geloggt, In-Memory State bleibt korrekt
- DB-Fehler sind non-blocking: Interview funktioniert auch ohne DB (Daten gehen dann verloren)

### 9. Abhaengigkeiten

- Bestehend: `supabase` (bereits in requirements.txt)
- Neu: Keine neuen Dependencies noetig

### 10. Wiederverwendete Code-Bausteine

| Funktion | Datei | Rueckgabetyp | Wichtige Hinweise |
|----------|-------|-------------|-------------------|
| `Settings` | `app/config/settings.py` | `Settings` Instanz | Aus Slice 1: `supabase_url`, `supabase_key`, `db_timeout_seconds` |
| `InterviewGraph` | `app/interview/graph.py` | Klasse | Aus Slice 2: `.get_history()` fuer Transkript-Extraktion |
| `InterviewService` | `app/interview/service.py` | Klasse | Aus Slice 3: Wird in diesem Slice erweitert |
| `get_interview_service` | `app/api/dependencies.py` | Funktion | Aus Slice 3: Wird um Repository-Injection erweitert |

---

## Integrations-Checkliste (Pflicht bei Backend-Aenderungen)

### 1. State-Integration
- [x] Kein neuer State -- InterviewState (Slice 2) bleibt unveraendert
- [x] In-Memory `_sessions` Dict bleibt als Cache
- [x] DB ist Source of Truth, In-Memory ist Fallback

### 2. LangGraph-Integration
- [x] `InterviewGraph.get_history()` wird in `end()` fuer Transkript-Extraktion genutzt
- [x] thread_id = session_id (konsistent mit Slice 2)

### 3. LLM-Integration
- [x] Nicht direkt betroffen (LLM-Calls laufen ueber InterviewGraph)

### 4. Datenbank-Integration
- [x] Schema validiert: Tabelle `interviews` mit allen Spalten aus architecture.md
- [x] Rueckgabeformate: `response.data` ist `list[dict]`, Zugriff via `response.data[0]`
- [x] Datentypen: UUID als String, TIMESTAMPTZ als ISO-String, JSONB als Python list/dict
- [x] Migration: Manuell im Supabase Dashboard ausfuehren

### 5. Utility-Funktionen
- [x] Settings aus Slice 1 wiederverwendet
- [x] InterviewGraph aus Slice 2 wiederverwendet
- [x] InterviewService aus Slice 3 erweitert (nicht dupliziert)

### 6. Feature-Aktivierung
- [x] Repository wird via Dependency Injection in InterviewService injiziert
- [x] Supabase Client wird beim ersten Request erstellt (lazy init)
- [x] Migration muss manuell in Supabase ausgefuehrt werden

### 7. Datenfluss-Vollstaendigkeit
- [x] Input: session_id (str), anonymous_id (str), transcript (list[dict]), summary (str)
- [x] Transformation: LangChain Messages -> `[{"role": "user"|"assistant", "content": "..."}]`
- [x] DB: Supabase REST API -> `response.data` (list[dict])
- [x] Output: Dict mit summary + message_count (unveraendert)

---

## UI Anforderungen

Keine UI in diesem Slice (Backend-only).

---

## Acceptance Criteria

1) GIVEN die `interviews`-Tabelle existiert in Supabase
   WHEN ein neues Interview via `/api/interview/start` gestartet wird
   THEN wird eine neue Row mit `status="active"`, korrekter `session_id` und `anonymous_id` in der `interviews`-Tabelle eingefuegt

2) GIVEN ein laufendes Interview
   WHEN der User eine Nachricht via `/api/interview/message` sendet
   THEN wird der `message_count` in der DB um 1 inkrementiert und `updated_at` aktualisiert

3) GIVEN ein laufendes Interview mit mindestens einer User-Nachricht
   WHEN das Interview via `/api/interview/end` beendet wird
   THEN wird in der DB `status="completed"`, `transcript` (JSONB Array), `summary` (Placeholder-Text), `message_count` und `completed_at` gespeichert

4) GIVEN ein beendetes Interview in der DB
   WHEN das `transcript`-Feld geprueft wird
   THEN ist es ein JSONB-Array mit Objekten im Format `[{"role": "assistant"|"user", "content": "..."}]`

5) GIVEN ein User hat vorherige abgeschlossene Interviews mit Summaries
   WHEN `repository.get_recent_summaries(anonymous_id, limit=3)` aufgerufen wird
   THEN werden maximal 3 Summary-Strings zurueckgegeben, sortiert nach `completed_at` absteigend (neueste zuerst)

6) GIVEN kein User hat vorherige Interviews
   WHEN `repository.get_recent_summaries(anonymous_id)` aufgerufen wird
   THEN wird eine leere Liste zurueckgegeben

7) GIVEN der Supabase Client ist korrekt konfiguriert
   WHEN `get_supabase_client(settings)` mehrfach aufgerufen wird
   THEN wird jedes Mal dieselbe Client-Instanz zurueckgegeben (Singleton)

8) GIVEN die `interviews`-Tabelle existiert
   WHEN `repository.create_session()` mit einer session_id aufgerufen wird
   THEN gibt die Methode die eingefuegte Row als Dict zurueck mit allen Default-Werten (id, created_at, updated_at)

9) GIVEN ein bestehendes Interview in der DB
   WHEN `repository.get_session(session_id)` aufgerufen wird
   THEN wird die Row als Dict zurueckgegeben mit allen Feldern

10) GIVEN der Supabase-Service ist nicht erreichbar
    WHEN ein Interview gestartet, eine Nachricht gesendet oder beendet wird
    THEN funktioniert der Interview-Flow trotzdem (DB-Fehler werden geloggt, nicht propagiert)

11) GIVEN die SQL Migration wird ausgefuehrt
    WHEN die `interviews`-Tabelle geprueft wird
    THEN existieren Indexes auf `anonymous_id`, `session_id` und `status`

---

## Testfaelle

**WICHTIG:** Tests muessen VOR der Implementierung definiert werden! Der Orchestrator fuehrt diese Tests automatisch nach der Slice-Implementierung aus.

### Test-Datei

**Fuer diesen Slice:** `backend/tests/slices/backend-kern/test_slice_04_supabase_persistenz.py`

### Unit Tests (pytest)

<test_spec>
```python
# backend/tests/slices/backend-kern/test_slice_04_supabase_persistenz.py
import pytest
import json
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone
from langchain_core.messages import HumanMessage, AIMessage


# -- Fixtures --

@pytest.fixture
def mock_settings():
    """Mock Settings mit Test-Werten."""
    settings = MagicMock()
    settings.supabase_url = "https://test.supabase.co"
    settings.supabase_key = "test-key"
    settings.db_timeout_seconds = 10
    settings.openrouter_api_key = "test-key"
    settings.interviewer_llm = "test-model"
    settings.interviewer_temperature = 1.0
    settings.interviewer_max_tokens = 4000
    settings.llm_timeout_seconds = 30
    return settings


@pytest.fixture
def mock_supabase_client():
    """Mock Supabase Client mit chainable API."""
    client = MagicMock()

    # Chainable mock fuer table().insert().execute() etc.
    def create_chain_mock(return_data=None):
        """Erstellt einen chainable Mock der execute() mit data zurueckgibt."""
        mock = MagicMock()
        response = MagicMock()
        response.data = return_data or []

        # Jede Methode gibt denselben Mock zurueck (chaining)
        mock.insert.return_value = mock
        mock.select.return_value = mock
        mock.update.return_value = mock
        mock.delete.return_value = mock
        mock.eq.return_value = mock
        mock.in_.return_value = mock
        mock.not_ = mock
        mock.is_.return_value = mock
        mock.order.return_value = mock
        mock.limit.return_value = mock
        mock.execute.return_value = response
        return mock

    client._chain_mock = create_chain_mock
    chain = create_chain_mock([{
        "id": "test-uuid",
        "session_id": "test-session",
        "anonymous_id": "test-user",
        "status": "active",
        "transcript": None,
        "summary": None,
        "message_count": 0,
        "created_at": "2026-02-13T10:00:00+00:00",
        "updated_at": "2026-02-13T10:00:00+00:00",
        "completed_at": None,
    }])
    client.table.return_value = chain
    return client


@pytest.fixture
def repository(mock_supabase_client, mock_settings):
    """InterviewRepository mit gemocktem Supabase Client."""
    from app.interview.repository import InterviewRepository
    return InterviewRepository(
        supabase_client=mock_supabase_client,
        settings=mock_settings,
    )


@pytest.fixture
def mock_graph():
    """Mock InterviewGraph."""
    from langchain_core.messages import AIMessageChunk

    graph = AsyncMock()

    async def mock_astream(messages, session_id):
        chunks = [
            (AIMessageChunk(content="Hallo"), {"langgraph_node": "interviewer"}),
            (AIMessageChunk(content="! Wie geht es?"), {"langgraph_node": "interviewer"}),
        ]
        for chunk in chunks:
            yield chunk

    graph.astream = mock_astream
    graph.get_history.return_value = [
        HumanMessage(content="Das Bidding nervt"),
        AIMessage(content="Was genau findest du frustrierend?"),
    ]
    return graph


@pytest.fixture
def mock_repository():
    """Mock InterviewRepository."""
    repo = AsyncMock()
    repo.create_session.return_value = {"session_id": "test-session", "status": "active"}
    repo.complete_session.return_value = {"session_id": "test-session", "status": "completed"}
    repo.increment_message_count.return_value = None
    repo.update_timestamp.return_value = None
    repo.get_recent_summaries.return_value = []
    return repo


# -- Supabase Client Singleton --

class TestSupabaseClientSingleton:
    """AC 7: Supabase Client ist ein Singleton."""

    def test_get_client_returns_same_instance(self, mock_settings):
        """AC 7: Mehrfache Aufrufe geben dieselbe Instanz zurueck."""
        from app.db.supabase import reset_supabase_client

        reset_supabase_client()
        with patch("app.db.supabase.create_client") as mock_create:
            mock_client = MagicMock()
            mock_create.return_value = mock_client

            from app.db.supabase import get_supabase_client
            client1 = get_supabase_client(mock_settings)
            client2 = get_supabase_client(mock_settings)

            assert client1 is client2
            mock_create.assert_called_once()

        reset_supabase_client()

    def test_reset_clears_singleton(self, mock_settings):
        """reset_supabase_client setzt den Singleton zurueck."""
        from app.db.supabase import get_supabase_client, reset_supabase_client

        reset_supabase_client()
        with patch("app.db.supabase.create_client") as mock_create:
            mock_create.return_value = MagicMock()

            client1 = get_supabase_client(mock_settings)
            reset_supabase_client()
            client2 = get_supabase_client(mock_settings)

            assert client1 is not client2
            assert mock_create.call_count == 2

        reset_supabase_client()


# -- InterviewRepository --

class TestRepositoryCreateSession:
    """AC 1 + AC 8: create_session fuegt Row in DB ein."""

    @pytest.mark.asyncio
    async def test_create_session_inserts_row(self, repository, mock_supabase_client):
        """AC 1: create_session erstellt eine Row mit korrekten Daten."""
        result = await repository.create_session("sess-123", "user-abc")

        mock_supabase_client.table.assert_called_with("interviews")
        assert result is not None

    @pytest.mark.asyncio
    async def test_create_session_sets_status_active(self, repository, mock_supabase_client):
        """AC 1: Neue Session hat status='active'."""
        await repository.create_session("sess-123", "user-abc")

        # Pruefen dass insert mit status="active" aufgerufen wurde
        chain = mock_supabase_client.table.return_value
        insert_call = chain.insert.call_args
        assert insert_call is not None
        insert_data = insert_call[0][0]
        assert insert_data["status"] == "active"
        assert insert_data["session_id"] == "sess-123"
        assert insert_data["anonymous_id"] == "user-abc"
        assert insert_data["message_count"] == 0


class TestRepositoryGetSession:
    """AC 9: get_session liest Session aus DB."""

    @pytest.mark.asyncio
    async def test_get_session_returns_row(self, repository):
        """AC 9: Existierende Session wird als Dict zurueckgegeben."""
        result = await repository.get_session("test-session")
        assert result is not None
        assert result["session_id"] == "test-session"

    @pytest.mark.asyncio
    async def test_get_session_returns_none_for_unknown(self, repository, mock_supabase_client):
        """get_session gibt None fuer unbekannte session_id zurueck."""
        # Leere Antwort simulieren
        chain = mock_supabase_client._chain_mock(return_data=[])
        mock_supabase_client.table.return_value = chain

        result = await repository.get_session("unknown-session")
        assert result is None


class TestRepositoryCompleteSession:
    """AC 3 + AC 4: complete_session speichert Transkript und Summary."""

    @pytest.mark.asyncio
    async def test_complete_session_updates_row(self, repository, mock_supabase_client):
        """AC 3: complete_session aktualisiert status, transcript, summary."""
        transcript = [
            {"role": "user", "content": "Das Bidding nervt"},
            {"role": "assistant", "content": "Was genau?"},
        ]
        await repository.complete_session(
            session_id="sess-123",
            transcript=transcript,
            summary="Test Summary",
            message_count=1,
        )

        chain = mock_supabase_client.table.return_value
        update_call = chain.update.call_args
        assert update_call is not None
        update_data = update_call[0][0]
        assert update_data["status"] == "completed"
        assert update_data["transcript"] == transcript
        assert update_data["summary"] == "Test Summary"
        assert update_data["message_count"] == 1
        assert "completed_at" in update_data
        assert "updated_at" in update_data

    @pytest.mark.asyncio
    async def test_complete_session_with_timeout_status(self, repository, mock_supabase_client):
        """complete_session akzeptiert status='completed_timeout'."""
        await repository.complete_session(
            session_id="sess-123",
            transcript=[],
            summary="Timeout Summary",
            message_count=0,
            status="completed_timeout",
        )

        chain = mock_supabase_client.table.return_value
        update_data = chain.update.call_args[0][0]
        assert update_data["status"] == "completed_timeout"


class TestRepositoryGetRecentSummaries:
    """AC 5 + AC 6: get_recent_summaries laedt Summaries."""

    @pytest.mark.asyncio
    async def test_get_recent_summaries_returns_strings(self, repository, mock_supabase_client):
        """AC 5: Summaries werden als Liste von Strings zurueckgegeben."""
        chain = mock_supabase_client._chain_mock(return_data=[
            {"summary": "Summary 1"},
            {"summary": "Summary 2"},
            {"summary": "Summary 3"},
        ])
        mock_supabase_client.table.return_value = chain

        result = await repository.get_recent_summaries("user-abc", limit=3)
        assert result == ["Summary 1", "Summary 2", "Summary 3"]

    @pytest.mark.asyncio
    async def test_get_recent_summaries_empty(self, repository, mock_supabase_client):
        """AC 6: Leere Liste wenn keine Summaries existieren."""
        chain = mock_supabase_client._chain_mock(return_data=[])
        mock_supabase_client.table.return_value = chain

        result = await repository.get_recent_summaries("new-user")
        assert result == []

    @pytest.mark.asyncio
    async def test_get_recent_summaries_respects_limit(self, repository, mock_supabase_client):
        """AC 5: limit Parameter wird beachtet."""
        await repository.get_recent_summaries("user-abc", limit=5)

        chain = mock_supabase_client.table.return_value
        chain.limit.assert_called_with(5)


class TestRepositoryIncrementMessageCount:
    """AC 2: message_count wird inkrementiert."""

    @pytest.mark.asyncio
    async def test_increment_message_count(self, repository, mock_supabase_client):
        """AC 2: message_count wird um 1 erhoeht."""
        await repository.increment_message_count("test-session")

        chain = mock_supabase_client.table.return_value
        # get_session + update werden aufgerufen
        assert chain.execute.call_count >= 1


# -- InterviewService mit Repository --

class TestInterviewServiceWithRepository:
    """AC 1, 2, 3, 10: InterviewService nutzt Repository."""

    @pytest.mark.asyncio
    async def test_start_calls_repository_create(self, mock_graph, mock_repository):
        """AC 1: start() ruft repository.create_session() auf."""
        from app.interview.service import InterviewService
        service = InterviewService(graph=mock_graph, repository=mock_repository)

        events = []
        async for event_data in service.start("test-user"):
            events.append(json.loads(event_data))

        mock_repository.create_session.assert_called_once()
        call_args = mock_repository.create_session.call_args
        assert call_args[1].get("anonymous_id", call_args[0][1] if len(call_args[0]) > 1 else None) == "test-user" or "test-user" in str(call_args)

    @pytest.mark.asyncio
    async def test_message_calls_repository_increment(self, mock_graph, mock_repository):
        """AC 2: message() ruft repository.increment_message_count() auf."""
        from app.interview.service import InterviewService
        service = InterviewService(graph=mock_graph, repository=mock_repository)

        # Session starten
        async for _ in service.start("test-user"):
            pass
        session_id = list(service._sessions.keys())[0]

        # Nachricht senden
        async for _ in service.message(session_id, "Test"):
            pass

        mock_repository.increment_message_count.assert_called_once_with(session_id)

    @pytest.mark.asyncio
    async def test_end_calls_repository_complete(self, mock_graph, mock_repository):
        """AC 3: end() ruft repository.complete_session() auf."""
        from app.interview.service import InterviewService
        service = InterviewService(graph=mock_graph, repository=mock_repository)

        # Session starten
        async for _ in service.start("test-user"):
            pass
        session_id = list(service._sessions.keys())[0]

        # Session beenden
        result = await service.end(session_id)

        mock_repository.complete_session.assert_called_once()
        call_kwargs = mock_repository.complete_session.call_args[1]
        assert call_kwargs["session_id"] == session_id
        assert isinstance(call_kwargs["transcript"], list)
        assert isinstance(call_kwargs["summary"], str)
        assert isinstance(call_kwargs["message_count"], int)

    @pytest.mark.asyncio
    async def test_service_works_without_repository(self, mock_graph):
        """AC 10: Service funktioniert auch ohne Repository (repository=None)."""
        from app.interview.service import InterviewService
        service = InterviewService(graph=mock_graph, repository=None)

        # Session starten
        events = []
        async for event_data in service.start("test-user"):
            events.append(json.loads(event_data))

        session_id = list(service._sessions.keys())[0]

        # Nachricht senden
        async for _ in service.message(session_id, "Test"):
            pass

        # Session beenden
        result = await service.end(session_id)
        assert "summary" in result
        assert "message_count" in result

    @pytest.mark.asyncio
    async def test_service_handles_db_error_gracefully(self, mock_graph):
        """AC 10: DB-Fehler werden geloggt aber nicht propagiert."""
        from app.interview.service import InterviewService

        failing_repo = AsyncMock()
        failing_repo.create_session.side_effect = Exception("DB connection refused")
        failing_repo.complete_session.side_effect = Exception("DB connection refused")
        failing_repo.increment_message_count.side_effect = Exception("DB connection refused")

        service = InterviewService(graph=mock_graph, repository=failing_repo)

        # Start soll trotz DB-Fehler funktionieren
        events = []
        async for event_data in service.start("test-user"):
            events.append(json.loads(event_data))

        metadata = [e for e in events if e.get("type") == "metadata"]
        assert len(metadata) == 1  # Session wurde erstellt

        session_id = list(service._sessions.keys())[0]

        # Message soll trotz DB-Fehler funktionieren
        msg_events = []
        async for event_data in service.message(session_id, "Test"):
            msg_events.append(json.loads(event_data))

        text_done = [e for e in msg_events if e.get("type") == "text-done"]
        assert len(text_done) == 1  # Streaming hat funktioniert

        # End soll trotz DB-Fehler funktionieren
        result = await service.end(session_id)
        assert "summary" in result


# -- Transcript Formatting --

class TestTranscriptFormatting:
    """AC 4: Transkript wird im korrekten JSONB-Format formatiert."""

    def test_format_transcript_human_and_ai(self):
        """AC 4: Messages werden zu {role, content} Dicts konvertiert."""
        from app.interview.service import InterviewService
        messages = [
            HumanMessage(content="Das Bidding nervt"),
            AIMessage(content="Was genau findest du frustrierend?"),
            HumanMessage(content="Die Preise sind intransparent"),
            AIMessage(content="Kannst du ein Beispiel nennen?"),
        ]
        result = InterviewService._format_transcript(messages)
        assert len(result) == 4
        assert result[0] == {"role": "user", "content": "Das Bidding nervt"}
        assert result[1] == {"role": "assistant", "content": "Was genau findest du frustrierend?"}
        assert result[2] == {"role": "user", "content": "Die Preise sind intransparent"}
        assert result[3] == {"role": "assistant", "content": "Kannst du ein Beispiel nennen?"}

    def test_format_transcript_empty(self):
        """Leere Message-Liste ergibt leeres Transkript."""
        from app.interview.service import InterviewService
        result = InterviewService._format_transcript([])
        assert result == []

    def test_format_transcript_is_json_serializable(self):
        """Transkript ist JSON-serialisierbar (JSONB-kompatibel)."""
        from app.interview.service import InterviewService
        messages = [
            HumanMessage(content="Test"),
            AIMessage(content="Antwort"),
        ]
        result = InterviewService._format_transcript(messages)
        serialized = json.dumps(result)
        deserialized = json.loads(serialized)
        assert deserialized == result


# -- SQL Migration --

class TestSQLMigration:
    """AC 11: Migration Script existiert und ist syntaktisch korrekt."""

    MIGRATION_PATH = "backend/migrations/001_create_interviews.sql"

    def test_migration_file_exists(self):
        """AC 11: Migration Script existiert."""
        from pathlib import Path
        migration = Path(__file__).resolve().parents[3] / "migrations" / "001_create_interviews.sql"
        assert migration.exists(), f"Migration file not found: {migration}"

    def test_migration_contains_create_table(self):
        """AC 11: Migration enthaelt CREATE TABLE."""
        from pathlib import Path
        migration = Path(__file__).resolve().parents[3] / "migrations" / "001_create_interviews.sql"
        content = migration.read_text(encoding="utf-8")
        assert "CREATE TABLE" in content
        assert "interviews" in content

    def test_migration_contains_all_columns(self):
        """AC 11: Alle Spalten aus architecture.md sind definiert."""
        from pathlib import Path
        migration = Path(__file__).resolve().parents[3] / "migrations" / "001_create_interviews.sql"
        content = migration.read_text(encoding="utf-8")
        required_columns = [
            "id", "anonymous_id", "session_id", "status",
            "transcript", "summary", "message_count",
            "created_at", "updated_at", "completed_at",
        ]
        for col in required_columns:
            assert col in content, f"Column '{col}' not found in migration"

    def test_migration_contains_indexes(self):
        """AC 11: Indexes auf anonymous_id, session_id und status existieren."""
        from pathlib import Path
        migration = Path(__file__).resolve().parents[3] / "migrations" / "001_create_interviews.sql"
        content = migration.read_text(encoding="utf-8")
        assert "idx_interviews_anonymous_id" in content
        assert "idx_interviews_session_id" in content
        assert "idx_interviews_status" in content

    def test_migration_contains_status_check(self):
        """Status CHECK Constraint ist definiert."""
        from pathlib import Path
        migration = Path(__file__).resolve().parents[3] / "migrations" / "001_create_interviews.sql"
        content = migration.read_text(encoding="utf-8")
        assert "active" in content
        assert "completed" in content
        assert "completed_timeout" in content


# -- Modul-Existenz --

class TestModuleStructure:
    """Alle neuen Dateien existieren und sind importierbar."""

    def test_supabase_module_importable(self):
        """db/supabase.py ist importierbar."""
        from app.db.supabase import get_supabase_client, reset_supabase_client
        assert get_supabase_client is not None
        assert reset_supabase_client is not None

    def test_repository_module_importable(self):
        """interview/repository.py ist importierbar."""
        from app.interview.repository import InterviewRepository
        assert InterviewRepository is not None

    def test_service_accepts_repository(self):
        """InterviewService akzeptiert repository Parameter."""
        import inspect
        from app.interview.service import InterviewService
        sig = inspect.signature(InterviewService.__init__)
        assert "repository" in sig.parameters
```
</test_spec>

### Manuelle Tests

1. Migration in Supabase Dashboard SQL Editor ausfuehren
2. Interview starten:
   ```bash
   curl -N -X POST http://localhost:8000/api/interview/start \
     -H "Content-Type: application/json" \
     -d '{"anonymous_id": "test-user-1"}'
   ```
3. In Supabase Dashboard pruefen: `interviews` Tabelle hat neue Row mit `status="active"`
4. Interview beenden und DB-Row pruefen: `status="completed"`, `transcript` nicht null

---

## Definition of Done

- [x] Akzeptanzkriterien sind eindeutig & vollstaendig
- [x] Logging fuer DB-Fehler definiert (logger.error)
- [x] Sicherheits-/Privacy-Aspekte bedacht (Supabase Keys via .env, keine PII)
- [x] Kein UI in diesem Slice
- [x] Migration muss manuell ausgefuehrt werden (kein automatischer Rollout)

---

## Constraints & Hinweise

**Betrifft:**
- Dieser Slice macht Interview-Daten persistent
- InterviewService._sessions Dict bleibt als In-Memory Cache
- DB ist Source of Truth, aber DB-Fehler sind non-blocking

**API Contract:**
- Keine neuen API-Endpoints
- Bestehende Endpoints (/start, /message, /end) bleiben identisch
- Nur internes Verhalten aendert sich (DB-Writes zusaetzlich)

**Abgrenzung:**
- Summary ist ein Placeholder-String (echte Generierung in Slice 5)
- `get_recent_summaries()` wird implementiert aber erst in Slice 5 aufgerufen
- Kein Timeout-Management (kommt in Slice 6)
- Migration wird manuell ausgefuehrt, kein automatisches Migrations-System

---

## Integration Contract (GATE 2 PFLICHT)

### Requires From Other Slices

| Slice | Resource | Type | Validation |
|-------|----------|------|------------|
| slice-01-app-skeleton | `Settings` | Pydantic BaseSettings | `supabase_url`, `supabase_key`, `db_timeout_seconds` verfuegbar |
| slice-01-app-skeleton | `app.state.settings` | Settings-Instanz | Runtime-Zugriff via `request.app.state.settings` |
| slice-01-app-skeleton | `backend/app/db/__init__.py` | Package | db/ Ordner existiert |
| slice-03-sse-streaming | `InterviewService` | Klasse | Wird in diesem Slice erweitert um Repository-Parameter |
| slice-03-sse-streaming | `get_interview_service` | FastAPI Dependency | Wird in diesem Slice erweitert um Repository-Injection |
| slice-03-sse-streaming | `SessionNotFoundError`, `SessionAlreadyCompletedError` | Exceptions | Bleiben unveraendert |

### Provides To Other Slices

| Resource | Type | Consumer | Interface |
|----------|------|----------|-----------|
| `get_supabase_client()` | Function | Slice 5, Slice 6 | `(settings: Settings) -> Client` (Singleton) |
| `InterviewRepository` | Klasse | Slice 5 (Summary-Write), Slice 6 (Timeout-Write) | `.create_session()`, `.get_session()`, `.complete_session()`, `.get_recent_summaries()`, `.increment_message_count()`, `.update_timestamp()` |
| `InterviewRepository.get_recent_summaries()` | Methode | Slice 5 (Summary-Injection) | `(anonymous_id: str, limit: int) -> list[str]` |
| `InterviewRepository.complete_session()` | Methode | Slice 6 (Timeout-Auto-Summary) | `(session_id, transcript, summary, message_count, status) -> dict` |
| `interviews` Tabelle | DB Schema | Slice 5, Slice 6 | Schema wie in architecture.md definiert |
| `InterviewService._format_transcript()` | Static Method | Slice 5, Slice 6 | `(messages: list) -> list[dict[str, str]]` |

### Integration Validation Tasks

- [ ] `Settings` aus Slice 1 hat `supabase_url`, `supabase_key`, `db_timeout_seconds`
- [ ] `db/__init__.py` aus Slice 1 existiert
- [ ] `InterviewService` aus Slice 3 ist erweiterbar (repository Parameter)
- [ ] `get_interview_service` aus Slice 3 ist anpassbar (Repository-Injection)
- [ ] `InterviewRepository.get_recent_summaries()` wird von Slice 5 konsumiert
- [ ] `InterviewRepository.complete_session()` wird von Slice 6 konsumiert
- [ ] SQL Migration ist in Supabase ausgefuehrt

---

## Code Examples (MANDATORY - GATE 2 PFLICHT)

> **KRITISCH:** Alle Code-Beispiele in diesem Dokument sind **PFLICHT-Deliverables**.
> Der Gate 2 Compliance Agent prueft, dass jedes Code-Beispiel implementiert wird.
> Abweichung nur mit expliziter Begruendung im Commit erlaubt.

| Code Example | Section | Mandatory | Notes |
|--------------|---------|-----------|-------|
| `get_supabase_client()` + `reset_supabase_client()` | Section 3 (Supabase Client Singleton) | YES | Singleton-Pattern mit Timeout-Config |
| SQL Migration `001_create_interviews.sql` | Section 4 (SQL Migration) | YES | Exakt wie in architecture.md |
| `InterviewRepository` Klasse | Section 5 (InterviewRepository) | YES | Alle 6 Methoden: `create_session`, `get_session`, `complete_session`, `get_recent_summaries`, `increment_message_count`, `update_timestamp` |
| `InterviewService` Erweiterung | Section 6 (InterviewService) | YES | Repository-Injection, DB-Calls in start/message/end, `_format_transcript()` |
| `get_interview_service()` Erweiterung | Section 7 (Dependency Injection) | YES | Repository-Instanz wird erstellt und injiziert |

---

## Deliverables (SCOPE SAFEGUARD)

**WICHTIG: Diese Liste wird automatisch vom Stop-Hook validiert. Der Agent kann nicht stoppen, wenn Dateien fehlen.**

<!-- DELIVERABLES_START -->
### Backend
- [ ] `backend/app/db/supabase.py` -- Supabase Client Singleton mit `get_supabase_client(settings)`, `_build_client_options(settings)`, `reset_supabase_client()`
- [ ] `backend/app/interview/repository.py` -- InterviewRepository mit `create_session()`, `get_session()`, `complete_session()`, `get_recent_summaries()`, `increment_message_count()`, `update_timestamp()`, `_execute()`
- [ ] `backend/app/interview/service.py` -- MODIFY: Repository-Injection im Constructor, DB-Calls in `start()`, `message()`, `end()`, neue Methode `_format_transcript()`
- [ ] `backend/app/api/dependencies.py` -- MODIFY: Supabase Client + InterviewRepository erstellen und an InterviewService uebergeben

### Migrations
- [ ] `backend/migrations/001_create_interviews.sql` -- CREATE TABLE interviews mit allen Spalten, Constraints und Indexes

### Tests
- [ ] `backend/tests/slices/backend-kern/test_slice_04_supabase_persistenz.py` -- pytest Tests fuer Supabase Client Singleton, InterviewRepository (CRUD), InterviewService mit Repository, Transcript-Formatting, SQL Migration, DB-Error-Handling
<!-- DELIVERABLES_END -->

**Hinweis fuer den Implementierungs-Agent:**
- Alle Dateien zwischen `<!-- DELIVERABLES_START -->` und `<!-- DELIVERABLES_END -->` sind **Pflicht**
- Der Stop-Hook prueft automatisch ob alle Dateien existieren
- Bei fehlenden Dateien wird der Agent blockiert und muss nachfragen

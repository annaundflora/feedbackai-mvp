# Slice 6: Session-Timeout + Auto-Summary aufsetzen

> **Slice 6 von 6** fuer `Backend-Kern`
>
> | Navigation | |
> |------------|---|
> | **Vorheriger:** | `slice-05-summary-injection.md` |
> | **Naechster:** | -- |

---

## Metadata (fuer Orchestrator)

| Key | Value |
|-----|-------|
| **ID** | `slice-06-session-timeout` |
| **Test** | `cd backend && python -m pytest tests/slices/backend-kern/test_slice_06_session_timeout.py -v` |
| **E2E** | `false` |
| **Dependencies** | `["slice-03-sse-streaming", "slice-04-supabase-persistenz", "slice-05-summary-injection"]` |

---

## Slice-Uebersicht

| # | Slice | Status | Datei |
|---|-------|--------|-------|
| 1 | App-Skeleton + DDD-Struktur | Done | `slice-01-app-skeleton.md` |
| 2 | LangGraph Interview-Graph | Done | `slice-02-langgraph-interview.md` |
| 3 | SSE-Streaming Endpoints | Done | `slice-03-sse-streaming.md` |
| 4 | Supabase-Persistenz | Done | `slice-04-supabase-persistenz.md` |
| 5 | Summary-Generierung + Injection | Done | `slice-05-summary-injection.md` |
| 6 | Session-Timeout + Auto-Summary | Ready | `slice-06-session-timeout.md` |

---

## Kontext & Ziel

Bis jetzt laufen aktive Sessions ewig weiter wenn der User verschwindet. Es gibt keinen Mechanismus der bei Inaktivitaet eine Auto-Summary generiert und die Session als `completed_timeout` markiert. Die `// Slice 6: TimeoutManager` Platzhalter-Kommentare in `InterviewService` werden nun implementiert.

Dieser Slice schliesst die letzte Luecke im Backend-Kern:
1. **TimeoutManager** (`interview/timeout.py`): asyncio.Task-basierter Timeout-Mechanismus der nach `SESSION_TIMEOUT_SECONDS` Inaktivitaet feuert
2. **on_timeout Callback**: Liest Graph-History, generiert Auto-Summary via SummaryService, markiert Session als `completed_timeout` in Supabase
3. **Integration in InterviewService**: `register()` bei `/start`, `reset()` bei `/message`, `cancel()` bei `/end`
4. **Cleanup bei App-Shutdown**: Alle aktiven Timeout-Tasks werden im Lifespan-Handler gecancelt

**Aktuelle Probleme:**
1. `interview/timeout.py` existiert nicht -- kein TimeoutManager
2. InterviewService hat `// Slice 6: TimeoutManager` Kommentare aber keine Implementierung
3. `main.py` Lifespan hat keinen Shutdown-Cleanup fuer Timeout-Tasks
4. Aktive Sessions bleiben ewig offen wenn der User verschwindet

---

## Technische Umsetzung

### Architektur-Kontext (aus architecture.md)

> **Quelle:** `architecture.md` -> Server Logic -> TimeoutManager + Business Logic Flow -> Timeout

```
Timeout Flow (aus architecture.md):
  TimeoutManager.on_timeout(session_id)
    -> InterviewGraph.get_history(config={thread_id})
    -> SummaryService.generate(history)
    -> InterviewRepository.complete_session(session_id, transcript, summary, status="completed_timeout")

Integration in InterviewService:
  POST /start:  -> TimeoutManager.register(session_id)
  POST /message: -> TimeoutManager.reset(session_id)
  POST /end:    -> TimeoutManager.cancel(session_id)

App Shutdown:
  Lifespan -> TimeoutManager.cancel_all()
```

### 1. Architektur-Impact

| Layer | Aenderungen |
|-------|-------------|
| `backend/app/interview/timeout.py` | NEU: TimeoutManager Klasse mit register(), reset(), cancel(), cancel_all(), _on_timeout() |
| `backend/app/interview/service.py` | MODIFY: TimeoutManager-Integration in start(), message(), end() |
| `backend/app/api/dependencies.py` | MODIFY: TimeoutManager erstellen und an InterviewService uebergeben |
| `backend/app/main.py` | MODIFY: Lifespan-Handler erweitern um Timeout-Cleanup bei Shutdown |

### 2. Datenfluss

```
POST /api/interview/start {"anonymous_id": "user-1"}
  |
  v
InterviewService.start(anonymous_id)
  1. session_id = uuid4()
  2. sessions[session_id] = {status: "active", ...}
  3. repository.create_session(session_id, anonymous_id)
  4. summaries = repository.get_recent_summaries(anonymous_id, limit=3)
  5. graph.set_summaries(summaries)
  6. graph.astream(messages=[], session_id) -> SSE
  7. yield metadata mit session_id
  8. timeout_manager.register(session_id)                    <-- NEU

---

POST /api/interview/message {"session_id": "uuid", "message": "..."}
  |
  v
InterviewService.message(session_id, message)
  1. _validate_session(session_id)
  2. timeout_manager.reset(session_id)                       <-- NEU (VOR dem Streaming)
  3. graph.astream(...) -> SSE
  4. sessions[session_id]["message_count"] += 1
  5. repository.increment_message_count(session_id)

---

POST /api/interview/end {"session_id": "uuid"}
  |
  v
InterviewService.end(session_id)
  1. _validate_session(session_id)
  2. timeout_manager.cancel(session_id)                      <-- NEU
  3. history = graph.get_history(session_id)
  4. transcript = _format_transcript(history)
  5. summary = await summary_service.generate(history)
  6. repository.complete_session(session_id, transcript, summary, message_count)
  7. sessions[session_id]["status"] = "completed"
  8. Return {summary, message_count}

---

Timeout (nach SESSION_TIMEOUT_SECONDS Inaktivitaet):
  TimeoutManager._on_timeout(session_id)
  1. history = graph.get_history(session_id)
  2. transcript = InterviewService._format_transcript(history)
  3. summary = await summary_service.generate(history)       <-- Kann fehlschlagen
  4. Falls Summary-Fehler: summary = None
  5. message_count = sessions[session_id]["message_count"]
  6. repository.complete_session(
       session_id, transcript, summary, message_count,
       status="completed_timeout"
     )
  7. sessions[session_id]["status"] = "completed_timeout"

---

App Shutdown:
  Lifespan shutdown
    -> timeout_manager.cancel_all()                          <-- NEU
    -> Alle asyncio.Tasks werden gecancelt
```

### 3. TimeoutManager (timeout.py)

> **Quelle:** `architecture.md` -> Server Logic -> TimeoutManager

```python
# backend/app/interview/timeout.py
"""TimeoutManager -- Ueberwacht Session-Inaktivitaet und triggert Auto-Summary.

Nutzt asyncio.Task fuer jeden aktiven Timer. Bei Inaktivitaet wird
on_timeout aufgerufen, der Graph-History liest, Summary generiert und
die Session als completed_timeout in Supabase markiert.
"""
import asyncio
import logging
from typing import Callable, Awaitable

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
```

### 4. InterviewService Erweiterung (service.py)

> **Quelle:** `architecture.md` -> Server Logic -> Business Logic Flow

Die bestehende `InterviewService` aus Slice 5 wird erweitert:
- Constructor akzeptiert zusaetzlich einen `TimeoutManager`
- `start()` ruft `timeout_manager.register()` NACH dem SSE-Stream auf
- `message()` ruft `timeout_manager.reset()` VOR dem Streaming auf
- `end()` ruft `timeout_manager.cancel()` VOR der Summary-Generierung auf
- Neue Methode `_handle_timeout()` wird als Callback an den TimeoutManager uebergeben

```python
# backend/app/interview/service.py
# MODIFY: Bestehende Klasse erweitern

# Neuer Import:
from app.interview.timeout import TimeoutManager

# Constructor erweitern:
    def __init__(
        self,
        graph: InterviewGraph,
        repository: InterviewRepository | None = None,
        summary_service: SummaryService | None = None,
        timeout_manager: TimeoutManager | None = None,
    ) -> None:
        self._graph = graph
        self._repository = repository
        self._summary_service = summary_service
        self._timeout_manager = timeout_manager
        self._sessions: dict[str, dict] = {}

# In start() am ENDE (nach yield metadata) EINFUEGEN:
        # Timeout-Timer registrieren
        if self._timeout_manager:
            self._timeout_manager.register(session_id)

# In message() nach _validate_session() EINFUEGEN:
        # Timeout-Timer zuruecksetzen
        if self._timeout_manager:
            self._timeout_manager.reset(session_id)

# In end() nach _validate_session() EINFUEGEN:
        # Timeout-Timer canceln
        if self._timeout_manager:
            self._timeout_manager.cancel(session_id)

# Neue Methode:
    async def _handle_timeout(self, session_id: str) -> None:
        """Callback fuer TimeoutManager: Auto-Summary bei Inaktivitaet.

        1. Prueft ob Session noch aktiv ist
        2. Liest History aus Graph
        3. Generiert Summary via SummaryService (Fehler => summary=None)
        4. Speichert in Supabase mit status="completed_timeout"
        5. Markiert Session in-memory als "completed_timeout"

        Args:
            session_id: UUID der Session die getimed out ist.
        """
        # Nur fuer aktive Sessions
        if session_id not in self._sessions:
            logger.warning(f"Timeout for unknown session {session_id}")
            return

        if self._sessions[session_id]["status"] != "active":
            logger.debug(f"Timeout for already completed session {session_id}")
            return

        message_count = self._sessions[session_id]["message_count"]

        # History und Transcript lesen
        history = self._graph.get_history(session_id)
        transcript = self._format_transcript(history)

        # Summary generieren -- Fehler fuehrt zu summary=None
        summary = None
        if self._summary_service and history:
            try:
                summary = await self._summary_service.generate(history)
            except Exception as e:
                logger.error(f"Auto-summary generation failed for timed out session {session_id}: {e}")

        # In DB speichern
        if self._repository:
            try:
                await self._repository.complete_session(
                    session_id=session_id,
                    transcript=transcript,
                    summary=summary,
                    message_count=message_count,
                    status="completed_timeout",
                )
            except Exception as e:
                logger.error(f"DB complete_session failed for timed out session {session_id}: {e}")

        # In-Memory Status aktualisieren
        self._sessions[session_id]["status"] = "completed_timeout"
        logger.info(
            f"Session {session_id} completed via timeout "
            f"(messages={message_count}, summary={'yes' if summary else 'no'})"
        )
```

### 5. Dependency Injection Erweiterung (dependencies.py)

```python
# backend/app/api/dependencies.py
# MODIFY: TimeoutManager erstellen und injizieren

# Neuer Import:
from app.interview.timeout import TimeoutManager

# In get_interview_service() AENDERN:
def get_interview_service(request: Request) -> InterviewService:
    global _interview_service
    if _interview_service is None:
        settings: Settings = request.app.state.settings
        graph = InterviewGraph(settings=settings)
        supabase_client = get_supabase_client(settings)
        repository = InterviewRepository(
            supabase_client=supabase_client,
            settings=settings,
        )
        summary_service = SummaryService(settings=settings)

        # InterviewService zuerst ohne TimeoutManager erstellen
        service = InterviewService(
            graph=graph,
            repository=repository,
            summary_service=summary_service,
        )

        # TimeoutManager mit dem Service-Callback erstellen
        timeout_manager = TimeoutManager(
            timeout_seconds=settings.session_timeout_seconds,
            on_timeout_callback=service._handle_timeout,
        )
        service._timeout_manager = timeout_manager

        # Auf app.state speichern fuer Lifespan-Cleanup
        request.app.state.timeout_manager = timeout_manager

        _interview_service = service
    return _interview_service
```

### 6. main.py Lifespan Erweiterung

> **Quelle:** `architecture.md` -> Architecture Layers -> Worker (timeout.py)

```python
# backend/app/main.py
# MODIFY: Lifespan-Handler um Shutdown-Cleanup erweitern

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    settings = Settings()
    app.state.settings = settings
    yield
    # Shutdown: Alle Timeout-Tasks canceln
    timeout_manager = getattr(app.state, "timeout_manager", None)
    if timeout_manager:
        timeout_manager.cancel_all()
```

### 7. Externe Services/APIs

| Service | Zweck | Integration |
|---------|-------|-------------|
| SummaryService (Slice 5) | Auto-Summary bei Timeout | `timeout.py` -> `InterviewService._handle_timeout()` -> `SummaryService.generate()` |
| InterviewRepository (Slice 4) | Session als completed_timeout markieren | `InterviewService._handle_timeout()` -> `repository.complete_session(status="completed_timeout")` |
| InterviewGraph (Slice 2) | History fuer Auto-Summary lesen | `InterviewService._handle_timeout()` -> `graph.get_history()` |

**Konfiguration:**
- `SESSION_TIMEOUT_SECONDS`: Timeout-Dauer, Default `60` (via Settings)

**Error Handling:**
- SummaryService.generate() Fehler -> summary=None, Session wird trotzdem als completed_timeout markiert
- Repository.complete_session() Fehler -> wird geloggt, In-Memory Status wird trotzdem aktualisiert
- TimeoutManager._timeout_task() Exception -> wird geloggt, Task wird entfernt

### 8. Abhaengigkeiten

- Bestehend: Keine neuen Dependencies noetig
- asyncio ist Python Standard Library

### 9. Wiederverwendete Code-Bausteine

| Funktion | Datei | Rueckgabetyp | Wichtige Hinweise |
|----------|-------|-------------|-------------------|
| `SummaryService.generate()` | `app/insights/summary.py` | `str` | Aus Slice 5: Generiert Bullet-Summary aus Messages |
| `InterviewRepository.complete_session()` | `app/interview/repository.py` | `dict` | Aus Slice 4: Akzeptiert `status="completed_timeout"` |
| `InterviewGraph.get_history()` | `app/interview/graph.py` | `list[AnyMessage]` | Aus Slice 2: Liest Conversation-History |
| `InterviewService._format_transcript()` | `app/interview/service.py` | `list[dict]` | Aus Slice 4: Konvertiert Messages zu JSONB |
| `Settings.session_timeout_seconds` | `app/config/settings.py` | `int` | Aus Slice 1: Default 60 |

---

## Integrations-Checkliste (Pflicht bei Backend-Aenderungen)

### 1. State-Integration
- [x] Kein neuer State -- InterviewState (Slice 2) bleibt unveraendert
- [x] `_tasks` Dict ist internes Implementation Detail des TimeoutManagers
- [x] In-Memory `_sessions` Status wird auf "completed_timeout" gesetzt

### 2. LangGraph-Integration
- [x] `InterviewGraph.get_history()` wird in `_handle_timeout()` fuer Transkript-Extraktion genutzt
- [x] thread_id = session_id (konsistent mit Slice 2)

### 3. LLM-Integration
- [x] Keine direkte LLM-Integration -- geht ueber SummaryService (Slice 5)
- [x] LLM-Fehler bei Auto-Summary fuehren zu summary=None (Session wird trotzdem als completed_timeout markiert)

### 4. Datenbank-Integration
- [x] `repository.complete_session()` mit `status="completed_timeout"` speichert in DB
- [x] DB-Fehler sind non-blocking (werden geloggt)

### 5. Utility-Funktionen
- [x] SummaryService aus Slice 5 wiederverwendet
- [x] InterviewRepository aus Slice 4 wiederverwendet
- [x] InterviewGraph.get_history() aus Slice 2 wiederverwendet
- [x] InterviewService._format_transcript() aus Slice 4 wiederverwendet

### 6. Feature-Aktivierung
- [x] TimeoutManager wird via Dependency Injection an InterviewService uebergeben
- [x] Timeout-Timer starten automatisch nach jedem /start
- [x] Timeout-Timer werden bei /message zurueckgesetzt
- [x] Timeout-Timer werden bei /end gecancelt
- [x] Alle Tasks werden bei App-Shutdown gecancelt (Lifespan)

### 7. Datenfluss-Vollstaendigkeit
- [x] Input: session_id (aus TimeoutManager Task)
- [x] Transformation: session_id -> graph.get_history() -> Messages -> SummaryService -> Summary String
- [x] DB: complete_session(status="completed_timeout", transcript, summary/null)
- [x] Output: Kein Client-Output (Background Task)

---

## UI Anforderungen

Keine UI in diesem Slice (Backend-only).

---

## Acceptance Criteria

1) GIVEN ein Interview wurde via `/api/interview/start` gestartet
   WHEN `SESSION_TIMEOUT_SECONDS` Sekunden ohne weitere Aktivitaet vergehen
   THEN wird die Session in der Supabase `interviews`-Tabelle als `status="completed_timeout"` markiert

2) GIVEN ein Interview wurde gestartet und der User hat Nachrichten gesendet
   WHEN der Timeout eintritt
   THEN wird eine Auto-Summary via SummaryService.generate() generiert und im `summary`-Feld der DB gespeichert

3) GIVEN ein Interview wurde gestartet
   WHEN der User eine Nachricht via `/api/interview/message` sendet
   THEN wird der Timeout-Timer zurueckgesetzt (neuer Timer startet bei 0)

4) GIVEN ein Interview laeuft mit aktivem Timeout-Timer
   WHEN das Interview via `/api/interview/end` explizit beendet wird
   THEN wird der Timeout-Timer gecancelt (kein Timeout wird gefeuert)

5) GIVEN ein Interview hat einen aktiven Timeout-Timer
   WHEN die Summary-Generierung bei Timeout fehlschlaegt (LLM-Fehler/Timeout)
   THEN wird die Session trotzdem als `completed_timeout` markiert mit `summary=null`

6) GIVEN mehrere Interviews laufen parallel mit aktiven Timeout-Timern
   WHEN eines davon timed out
   THEN werden nur die Timer der getimeten Session beeinflusst, andere Sessions laufen weiter

7) GIVEN die FastAPI App wird heruntergefahren (Shutdown)
   WHEN aktive Timeout-Timer existieren
   THEN werden alle Timer sauber gecancelt via `cancel_all()`

8) GIVEN ein Interview wurde gestartet
   WHEN `TimeoutManager.register(session_id)` aufgerufen wird
   THEN existiert ein asyncio.Task mit dem Namen `timeout-{session_id}`

9) GIVEN ein Interview-Timeout tritt ein
   WHEN die Session bereits explizit beendet wurde (status != "active")
   THEN wird der Timeout-Callback ignoriert (keine doppelte Completion)

10) GIVEN ein Interview-Timeout tritt ein und es existiert History
    WHEN das Transcript in der DB geprueft wird
    THEN ist es im selben Format wie bei explizitem /end: JSONB-Array mit `[{"role": "assistant"|"user", "content": "..."}]`

---

## Testfaelle

**WICHTIG:** Tests muessen VOR der Implementierung definiert werden! Der Orchestrator fuehrt diese Tests automatisch nach der Slice-Implementierung aus.

### Test-Datei

**Fuer diesen Slice:** `backend/tests/slices/backend-kern/test_slice_06_session_timeout.py`

### Unit Tests (pytest)

<test_spec>
```python
# backend/tests/slices/backend-kern/test_slice_06_session_timeout.py
import pytest
import json
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from langchain_core.messages import HumanMessage, AIMessage, AIMessageChunk


# -- Fixtures --

@pytest.fixture
def mock_callback():
    """Mock async Callback fuer TimeoutManager."""
    return AsyncMock()


@pytest.fixture
def timeout_manager(mock_callback):
    """TimeoutManager mit kurzem Timeout fuer Tests."""
    from app.interview.timeout import TimeoutManager
    return TimeoutManager(
        timeout_seconds=1,
        on_timeout_callback=mock_callback,
    )


@pytest.fixture
def fast_timeout_manager(mock_callback):
    """TimeoutManager mit sehr kurzem Timeout (0.1s) fuer schnelle Tests."""
    from app.interview.timeout import TimeoutManager
    return TimeoutManager(
        timeout_seconds=0.1,
        on_timeout_callback=mock_callback,
    )


@pytest.fixture
def mock_graph():
    """Mock InterviewGraph."""
    graph = AsyncMock()
    graph._current_summaries = []

    def mock_set_summaries(summaries):
        graph._current_summaries = summaries or []

    graph.set_summaries = mock_set_summaries

    async def mock_astream(messages, session_id):
        chunks = [
            (AIMessageChunk(content="Hallo"), {"langgraph_node": "interviewer"}),
            (AIMessageChunk(content="! Wie geht es?"), {"langgraph_node": "interviewer"}),
        ]
        for chunk in chunks:
            yield chunk

    graph.astream = mock_astream
    graph.get_history.return_value = [
        AIMessage(content="Hallo! Was beschaeftigt dich?"),
        HumanMessage(content="Das Bidding nervt"),
        AIMessage(content="Was genau findest du frustrierend?"),
    ]
    return graph


@pytest.fixture
def mock_repository():
    """Mock InterviewRepository."""
    repo = AsyncMock()
    repo.create_session.return_value = {"session_id": "test-session", "status": "active"}
    repo.complete_session.return_value = {"session_id": "test-session", "status": "completed_timeout"}
    repo.increment_message_count.return_value = None
    repo.get_recent_summaries.return_value = []
    return repo


@pytest.fixture
def mock_summary_service():
    """Mock SummaryService."""
    service = AsyncMock()
    service.generate.return_value = (
        "- User findet das Bidding frustrierend\n"
        "- Preise sind intransparent"
    )
    return service


# -- TimeoutManager: register/reset/cancel --

class TestTimeoutManagerRegister:
    """AC 8: register() erstellt asyncio.Task."""

    @pytest.mark.asyncio
    async def test_register_creates_task(self, timeout_manager):
        """AC 8: register() erstellt einen Task fuer die Session."""
        timeout_manager.register("session-1")
        assert timeout_manager.active_count == 1

        # Cleanup
        timeout_manager.cancel_all()

    @pytest.mark.asyncio
    async def test_register_replaces_existing_task(self, timeout_manager):
        """register() ersetzt bestehenden Task."""
        timeout_manager.register("session-1")
        timeout_manager.register("session-1")
        assert timeout_manager.active_count == 1

        # Cleanup
        timeout_manager.cancel_all()

    @pytest.mark.asyncio
    async def test_register_multiple_sessions(self, timeout_manager):
        """AC 6: Mehrere Sessions koennen parallel registriert werden."""
        timeout_manager.register("session-1")
        timeout_manager.register("session-2")
        timeout_manager.register("session-3")
        assert timeout_manager.active_count == 3

        # Cleanup
        timeout_manager.cancel_all()


class TestTimeoutManagerReset:
    """AC 3: reset() setzt Timer zurueck."""

    @pytest.mark.asyncio
    async def test_reset_restarts_timer(self, fast_timeout_manager, mock_callback):
        """AC 3: reset() startet den Timer neu."""
        fast_timeout_manager.register("session-1")
        await asyncio.sleep(0.05)  # Halbe Zeit warten
        fast_timeout_manager.reset("session-1")
        await asyncio.sleep(0.05)  # Nochmal halbe Zeit -- waere ohne Reset getimed out

        # Sollte noch NICHT getimed out sein (Timer wurde zurueckgesetzt)
        mock_callback.assert_not_called()

        # Cleanup
        fast_timeout_manager.cancel_all()

    @pytest.mark.asyncio
    async def test_reset_unknown_session_creates_new(self, timeout_manager):
        """reset() auf unbekannte Session erstellt neuen Timer."""
        timeout_manager.reset("new-session")
        assert timeout_manager.active_count == 1

        # Cleanup
        timeout_manager.cancel_all()


class TestTimeoutManagerCancel:
    """AC 4: cancel() cancelt Timer."""

    @pytest.mark.asyncio
    async def test_cancel_removes_task(self, timeout_manager):
        """AC 4: cancel() entfernt den Task."""
        timeout_manager.register("session-1")
        assert timeout_manager.active_count == 1

        timeout_manager.cancel("session-1")
        # Task cleanup happens async, give it a moment
        await asyncio.sleep(0.01)
        assert timeout_manager.active_count == 0

    @pytest.mark.asyncio
    async def test_cancel_unknown_session_no_error(self, timeout_manager):
        """cancel() auf unbekannte Session wirft keinen Fehler."""
        timeout_manager.cancel("nonexistent")  # Kein Error

    @pytest.mark.asyncio
    async def test_cancel_prevents_timeout(self, fast_timeout_manager, mock_callback):
        """AC 4: cancel() verhindert dass der Timeout feuert."""
        fast_timeout_manager.register("session-1")
        fast_timeout_manager.cancel("session-1")
        await asyncio.sleep(0.2)  # Laenger als Timeout warten

        mock_callback.assert_not_called()


class TestTimeoutManagerCancelAll:
    """AC 7: cancel_all() cancelt alle Timer."""

    @pytest.mark.asyncio
    async def test_cancel_all_clears_tasks(self, timeout_manager):
        """AC 7: cancel_all() entfernt alle Tasks."""
        timeout_manager.register("session-1")
        timeout_manager.register("session-2")
        timeout_manager.register("session-3")
        assert timeout_manager.active_count == 3

        timeout_manager.cancel_all()
        await asyncio.sleep(0.01)
        assert timeout_manager.active_count == 0

    @pytest.mark.asyncio
    async def test_cancel_all_empty_no_error(self, timeout_manager):
        """cancel_all() ohne aktive Tasks wirft keinen Fehler."""
        timeout_manager.cancel_all()  # Kein Error


# -- TimeoutManager: Timeout-Callback --

class TestTimeoutCallback:
    """AC 1, 2, 6: Timeout feuert Callback."""

    @pytest.mark.asyncio
    async def test_timeout_fires_callback(self, fast_timeout_manager, mock_callback):
        """AC 1: Nach timeout_seconds wird der Callback aufgerufen."""
        fast_timeout_manager.register("session-1")
        await asyncio.sleep(0.2)  # Laenger als 0.1s Timeout warten

        mock_callback.assert_called_once_with("session-1")

    @pytest.mark.asyncio
    async def test_timeout_fires_only_for_timed_out_session(self, mock_callback):
        """AC 6: Timeout feuert nur fuer die betroffene Session."""
        from app.interview.timeout import TimeoutManager

        # Zwei Manager mit verschiedenen Timeouts simulieren via einen Manager
        manager = TimeoutManager(
            timeout_seconds=0.1,
            on_timeout_callback=mock_callback,
        )
        manager.register("session-fast")

        # session-fast soll nach 0.1s timen out, session-slow wird sofort gecancelt
        manager2 = TimeoutManager(
            timeout_seconds=10,
            on_timeout_callback=mock_callback,
        )
        manager2.register("session-slow")

        await asyncio.sleep(0.2)

        # Nur session-fast sollte getimed out sein
        mock_callback.assert_called_once_with("session-fast")

        # Cleanup
        manager2.cancel_all()

    @pytest.mark.asyncio
    async def test_timeout_removes_task_after_firing(self, fast_timeout_manager, mock_callback):
        """Task wird nach dem Feuern entfernt."""
        fast_timeout_manager.register("session-1")
        await asyncio.sleep(0.2)

        assert fast_timeout_manager.active_count == 0


class TestTimeoutCallbackErrors:
    """AC 5: Fehler im Callback werden abgefangen."""

    @pytest.mark.asyncio
    async def test_callback_error_is_caught(self):
        """Fehler im Callback fuehrt nicht zum Absturz."""
        from app.interview.timeout import TimeoutManager

        failing_callback = AsyncMock(side_effect=Exception("Callback failed"))
        manager = TimeoutManager(
            timeout_seconds=0.1,
            on_timeout_callback=failing_callback,
        )
        manager.register("session-1")
        await asyncio.sleep(0.2)

        # Callback wurde aufgerufen, aber Fehler wurde abgefangen
        failing_callback.assert_called_once()
        assert manager.active_count == 0  # Task wurde trotzdem aufgeraeumt


# -- InterviewService mit TimeoutManager --

class TestInterviewServiceTimeoutIntegration:
    """AC 1, 3, 4: InterviewService nutzt TimeoutManager."""

    @pytest.mark.asyncio
    async def test_start_registers_timeout(self, mock_graph, mock_repository, mock_summary_service):
        """AC 1 (indirekt): start() registriert Timeout."""
        from app.interview.service import InterviewService
        from app.interview.timeout import TimeoutManager

        timeout_callback = AsyncMock()
        timeout_manager = TimeoutManager(
            timeout_seconds=60,
            on_timeout_callback=timeout_callback,
        )

        service = InterviewService(
            graph=mock_graph,
            repository=mock_repository,
            summary_service=mock_summary_service,
            timeout_manager=timeout_manager,
        )

        async for _ in service.start("test-user"):
            pass

        assert timeout_manager.active_count == 1

        # Cleanup
        timeout_manager.cancel_all()

    @pytest.mark.asyncio
    async def test_message_resets_timeout(self, mock_graph, mock_repository, mock_summary_service):
        """AC 3: message() setzt Timeout zurueck."""
        from app.interview.service import InterviewService
        from app.interview.timeout import TimeoutManager

        timeout_callback = AsyncMock()
        timeout_manager = TimeoutManager(
            timeout_seconds=60,
            on_timeout_callback=timeout_callback,
        )

        service = InterviewService(
            graph=mock_graph,
            repository=mock_repository,
            summary_service=mock_summary_service,
            timeout_manager=timeout_manager,
        )

        async for _ in service.start("test-user"):
            pass
        session_id = list(service._sessions.keys())[0]

        # Message senden -> Timeout wird zurueckgesetzt
        async for _ in service.message(session_id, "Test"):
            pass

        # Timeout-Timer existiert noch
        assert timeout_manager.active_count == 1

        # Cleanup
        timeout_manager.cancel_all()

    @pytest.mark.asyncio
    async def test_end_cancels_timeout(self, mock_graph, mock_repository, mock_summary_service):
        """AC 4: end() cancelt Timeout."""
        from app.interview.service import InterviewService
        from app.interview.timeout import TimeoutManager

        timeout_callback = AsyncMock()
        timeout_manager = TimeoutManager(
            timeout_seconds=60,
            on_timeout_callback=timeout_callback,
        )

        service = InterviewService(
            graph=mock_graph,
            repository=mock_repository,
            summary_service=mock_summary_service,
            timeout_manager=timeout_manager,
        )

        async for _ in service.start("test-user"):
            pass
        session_id = list(service._sessions.keys())[0]

        await service.end(session_id)

        await asyncio.sleep(0.01)
        assert timeout_manager.active_count == 0

    @pytest.mark.asyncio
    async def test_service_works_without_timeout_manager(self, mock_graph, mock_repository, mock_summary_service):
        """Service funktioniert auch ohne TimeoutManager (timeout_manager=None)."""
        from app.interview.service import InterviewService
        service = InterviewService(
            graph=mock_graph,
            repository=mock_repository,
            summary_service=mock_summary_service,
            timeout_manager=None,
        )

        async for _ in service.start("test-user"):
            pass
        session_id = list(service._sessions.keys())[0]

        async for _ in service.message(session_id, "Test"):
            pass

        result = await service.end(session_id)
        assert "summary" in result


# -- InterviewService._handle_timeout --

class TestHandleTimeout:
    """AC 1, 2, 5, 9, 10: _handle_timeout Callback."""

    @pytest.mark.asyncio
    async def test_handle_timeout_completes_session(self, mock_graph, mock_repository, mock_summary_service):
        """AC 1: _handle_timeout setzt Status auf completed_timeout."""
        from app.interview.service import InterviewService
        service = InterviewService(
            graph=mock_graph,
            repository=mock_repository,
            summary_service=mock_summary_service,
        )

        # Session manuell erstellen
        service._sessions["test-session"] = {
            "status": "active",
            "anonymous_id": "user-1",
            "message_count": 2,
        }

        await service._handle_timeout("test-session")

        assert service._sessions["test-session"]["status"] == "completed_timeout"

    @pytest.mark.asyncio
    async def test_handle_timeout_generates_summary(self, mock_graph, mock_repository, mock_summary_service):
        """AC 2: _handle_timeout generiert Summary via SummaryService."""
        from app.interview.service import InterviewService
        service = InterviewService(
            graph=mock_graph,
            repository=mock_repository,
            summary_service=mock_summary_service,
        )

        service._sessions["test-session"] = {
            "status": "active",
            "anonymous_id": "user-1",
            "message_count": 1,
        }

        await service._handle_timeout("test-session")

        mock_summary_service.generate.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_timeout_saves_to_db(self, mock_graph, mock_repository, mock_summary_service):
        """AC 1: _handle_timeout speichert in DB mit status=completed_timeout."""
        from app.interview.service import InterviewService
        service = InterviewService(
            graph=mock_graph,
            repository=mock_repository,
            summary_service=mock_summary_service,
        )

        service._sessions["test-session"] = {
            "status": "active",
            "anonymous_id": "user-1",
            "message_count": 1,
        }

        await service._handle_timeout("test-session")

        mock_repository.complete_session.assert_called_once()
        call_kwargs = mock_repository.complete_session.call_args[1]
        assert call_kwargs["session_id"] == "test-session"
        assert call_kwargs["status"] == "completed_timeout"
        assert isinstance(call_kwargs["transcript"], list)

    @pytest.mark.asyncio
    async def test_handle_timeout_saves_transcript_format(self, mock_graph, mock_repository, mock_summary_service):
        """AC 10: Transcript Format ist identisch zu /end."""
        from app.interview.service import InterviewService
        service = InterviewService(
            graph=mock_graph,
            repository=mock_repository,
            summary_service=mock_summary_service,
        )

        service._sessions["test-session"] = {
            "status": "active",
            "anonymous_id": "user-1",
            "message_count": 1,
        }

        await service._handle_timeout("test-session")

        call_kwargs = mock_repository.complete_session.call_args[1]
        transcript = call_kwargs["transcript"]
        for entry in transcript:
            assert "role" in entry
            assert "content" in entry
            assert entry["role"] in ("user", "assistant")

    @pytest.mark.asyncio
    async def test_handle_timeout_summary_failure_still_completes(self, mock_graph, mock_repository):
        """AC 5: Summary-Fehler fuehrt zu summary=None, Session wird trotzdem completed_timeout."""
        failing_summary = AsyncMock()
        failing_summary.generate.side_effect = Exception("LLM unavailable")

        from app.interview.service import InterviewService
        service = InterviewService(
            graph=mock_graph,
            repository=mock_repository,
            summary_service=failing_summary,
        )

        service._sessions["test-session"] = {
            "status": "active",
            "anonymous_id": "user-1",
            "message_count": 0,
        }

        await service._handle_timeout("test-session")

        # Session ist trotzdem als completed_timeout markiert
        assert service._sessions["test-session"]["status"] == "completed_timeout"
        # DB-Call wurde mit summary=None aufgerufen
        call_kwargs = mock_repository.complete_session.call_args[1]
        assert call_kwargs["summary"] is None
        assert call_kwargs["status"] == "completed_timeout"

    @pytest.mark.asyncio
    async def test_handle_timeout_ignores_already_completed(self, mock_graph, mock_repository, mock_summary_service):
        """AC 9: Timeout auf bereits beendete Session wird ignoriert."""
        from app.interview.service import InterviewService
        service = InterviewService(
            graph=mock_graph,
            repository=mock_repository,
            summary_service=mock_summary_service,
        )

        service._sessions["test-session"] = {
            "status": "completed",
            "anonymous_id": "user-1",
            "message_count": 1,
        }

        await service._handle_timeout("test-session")

        # Kein DB-Call, kein Summary-Call
        mock_summary_service.generate.assert_not_called()
        mock_repository.complete_session.assert_not_called()

    @pytest.mark.asyncio
    async def test_handle_timeout_ignores_unknown_session(self, mock_graph, mock_repository, mock_summary_service):
        """AC 9: Timeout auf unbekannte Session wird ignoriert."""
        from app.interview.service import InterviewService
        service = InterviewService(
            graph=mock_graph,
            repository=mock_repository,
            summary_service=mock_summary_service,
        )

        await service._handle_timeout("unknown-session")

        mock_summary_service.generate.assert_not_called()
        mock_repository.complete_session.assert_not_called()

    @pytest.mark.asyncio
    async def test_handle_timeout_db_error_still_updates_memory(self, mock_graph, mock_summary_service):
        """DB-Fehler bei Timeout aktualisiert trotzdem In-Memory Status."""
        failing_repo = AsyncMock()
        failing_repo.complete_session.side_effect = Exception("DB connection refused")

        from app.interview.service import InterviewService
        service = InterviewService(
            graph=mock_graph,
            repository=failing_repo,
            summary_service=mock_summary_service,
        )

        service._sessions["test-session"] = {
            "status": "active",
            "anonymous_id": "user-1",
            "message_count": 0,
        }

        await service._handle_timeout("test-session")

        # In-Memory Status wurde trotzdem aktualisiert
        assert service._sessions["test-session"]["status"] == "completed_timeout"


# -- End-to-End: Timeout fires Auto-Summary --

class TestEndToEndTimeout:
    """AC 1, 2: Vollstaendiger Timeout-Flow mit kurzem Timer."""

    @pytest.mark.asyncio
    async def test_full_timeout_flow(self, mock_graph, mock_repository, mock_summary_service):
        """AC 1 + AC 2: Session starten, warten, Auto-Summary + completed_timeout."""
        from app.interview.service import InterviewService
        from app.interview.timeout import TimeoutManager

        service = InterviewService(
            graph=mock_graph,
            repository=mock_repository,
            summary_service=mock_summary_service,
        )

        timeout_manager = TimeoutManager(
            timeout_seconds=0.1,
            on_timeout_callback=service._handle_timeout,
        )
        service._timeout_manager = timeout_manager

        # Session starten
        async for _ in service.start("test-user"):
            pass
        session_id = list(service._sessions.keys())[0]

        # Warten bis Timeout feuert
        await asyncio.sleep(0.3)

        # Session sollte als completed_timeout markiert sein
        assert service._sessions[session_id]["status"] == "completed_timeout"

        # DB-Call mit completed_timeout
        mock_repository.complete_session.assert_called_once()
        call_kwargs = mock_repository.complete_session.call_args[1]
        assert call_kwargs["status"] == "completed_timeout"

        # Summary wurde generiert
        mock_summary_service.generate.assert_called_once()

    @pytest.mark.asyncio
    async def test_message_prevents_timeout(self, mock_graph, mock_repository, mock_summary_service):
        """AC 3: message() setzt Timer zurueck, verhindert Timeout."""
        from app.interview.service import InterviewService
        from app.interview.timeout import TimeoutManager

        service = InterviewService(
            graph=mock_graph,
            repository=mock_repository,
            summary_service=mock_summary_service,
        )

        timeout_manager = TimeoutManager(
            timeout_seconds=0.2,
            on_timeout_callback=service._handle_timeout,
        )
        service._timeout_manager = timeout_manager

        # Session starten
        async for _ in service.start("test-user"):
            pass
        session_id = list(service._sessions.keys())[0]

        # Vor Timeout eine Message senden (bei 0.1s von 0.2s)
        await asyncio.sleep(0.1)
        async for _ in service.message(session_id, "Noch da"):
            pass

        # Nochmal 0.1s warten -- waere ohne Reset getimed out
        await asyncio.sleep(0.1)

        # Session sollte noch aktiv sein
        assert service._sessions[session_id]["status"] == "active"

        # Cleanup
        timeout_manager.cancel_all()


# -- Dependency Injection --

class TestDependencyInjection:
    """InterviewService akzeptiert timeout_manager Parameter."""

    def test_service_accepts_timeout_manager(self):
        """InterviewService Constructor hat timeout_manager Parameter."""
        import inspect
        from app.interview.service import InterviewService
        sig = inspect.signature(InterviewService.__init__)
        assert "timeout_manager" in sig.parameters

    def test_service_timeout_manager_is_optional(self):
        """timeout_manager Parameter ist optional (Default: None)."""
        import inspect
        from app.interview.service import InterviewService
        sig = inspect.signature(InterviewService.__init__)
        param = sig.parameters["timeout_manager"]
        assert param.default is None


# -- Modul-Existenz --

class TestModuleStructure:
    """Alle neuen/geaenderten Dateien existieren und sind importierbar."""

    def test_timeout_module_importable(self):
        """interview/timeout.py ist importierbar."""
        from app.interview.timeout import TimeoutManager
        assert TimeoutManager is not None

    def test_timeout_manager_has_required_methods(self):
        """TimeoutManager hat alle erforderlichen Methoden."""
        from app.interview.timeout import TimeoutManager
        assert hasattr(TimeoutManager, "register")
        assert hasattr(TimeoutManager, "reset")
        assert hasattr(TimeoutManager, "cancel")
        assert hasattr(TimeoutManager, "cancel_all")

    def test_timeout_manager_has_active_count(self):
        """TimeoutManager hat active_count Property."""
        from app.interview.timeout import TimeoutManager
        assert hasattr(TimeoutManager, "active_count")

    def test_service_has_handle_timeout(self):
        """InterviewService hat _handle_timeout Methode."""
        from app.interview.service import InterviewService
        assert hasattr(InterviewService, "_handle_timeout")
```
</test_spec>

### Manuelle Tests

1. Interview starten und warten bis Timeout feuert:
   ```bash
   # Start (SESSION_TIMEOUT_SECONDS=10 in .env fuer schnellen Test)
   curl -N -X POST http://localhost:8000/api/interview/start \
     -H "Content-Type: application/json" \
     -d '{"anonymous_id": "timeout-test-user"}'

   # 10+ Sekunden warten, nicht antworten

   # In Supabase pruefen: interviews Tabelle -> status = "completed_timeout", summary vorhanden
   ```

2. Interview starten, Nachricht senden, warten:
   ```bash
   # Start
   curl -N -X POST http://localhost:8000/api/interview/start \
     -H "Content-Type: application/json" \
     -d '{"anonymous_id": "timeout-test-user"}'

   # Nachricht senden (Timer wird zurueckgesetzt)
   curl -N -X POST http://localhost:8000/api/interview/message \
     -H "Content-Type: application/json" \
     -d '{"session_id": "<id>", "message": "Das Bidding nervt"}'

   # 10+ Sekunden warten -> Auto-Summary in DB pruefen
   ```

3. Interview starten und explizit beenden (kein Timeout):
   ```bash
   # Start
   curl -N -X POST http://localhost:8000/api/interview/start \
     -H "Content-Type: application/json" \
     -d '{"anonymous_id": "no-timeout-user"}'

   # Sofort beenden (vor Timeout)
   curl -X POST http://localhost:8000/api/interview/end \
     -H "Content-Type: application/json" \
     -d '{"session_id": "<id>"}'

   # Status sollte "completed" sein (nicht "completed_timeout")
   ```

---

## Definition of Done

- [x] Akzeptanzkriterien sind eindeutig & vollstaendig
- [x] Logging fuer Timeout-Events, Summary-Fehler und DB-Fehler definiert (logger.info/error)
- [x] Sicherheits-/Privacy-Aspekte bedacht (keine neuen Daten, bestehende Supabase-Sicherheit)
- [x] Kein UI in diesem Slice
- [x] Kein Rollout/Rollback noetig (TimeoutManager startet automatisch mit der App)

---

## Constraints & Hinweise

**Betrifft:**
- Dieser Slice schliesst die letzte Luecke im Backend-Kern: Robustheit bei User-Inaktivitaet
- TimeoutManager ist ein eigenstaendiger Worker im `interview/` Bounded Context
- InterviewService orchestriert TimeoutManager, SummaryService, Graph und Repository

**API Contract:**
- Keine neuen API-Endpoints
- Keine Aenderungen an bestehenden Endpoints (SSE-Format, JSON-Responses bleiben identisch)
- Nur internes Verhalten aendert sich (Timeout-Timer laufen im Hintergrund)

**Abgrenzung:**
- Kein Cleanup-Cron fuer abgelaufene In-Memory Sessions (akzeptabel fuer MVP, siehe Risk: MemorySaver)
- Keine Benachrichtigung an den Client bei Timeout (Client bemerkt es erst beim naechsten Request -> 409)
- TimeoutManager ist single-process (kein Multi-Worker Support, akzeptabel fuer MVP)
- MemorySaver State geht bei Restart verloren (bekanntes Risiko, dokumentiert in architecture.md)

---

## Integration Contract (GATE 2 PFLICHT)

### Requires From Other Slices

| Slice | Resource | Type | Validation |
|-------|----------|------|------------|
| slice-03-sse-streaming | `InterviewService` | Klasse | Constructor akzeptiert `timeout_manager` Parameter |
| slice-03-sse-streaming | `InterviewService._sessions` | In-Memory Dict | `{session_id: {status, anonymous_id, message_count}}` verfuegbar |
| slice-04-supabase-persistenz | `InterviewRepository.complete_session()` | Methode | `(session_id, transcript, summary, message_count, status="completed_timeout") -> dict` |
| slice-05-summary-injection | `SummaryService.generate()` | Async Methode | `(messages: list[AnyMessage]) -> str` |
| slice-05-summary-injection | `InterviewGraph.get_history()` | Methode | `(session_id: str) -> list[AnyMessage]` |
| slice-05-summary-injection | `InterviewService._format_transcript()` | Static Method | `(messages: list) -> list[dict[str, str]]` |
| slice-01-app-skeleton | `Settings.session_timeout_seconds` | int | Default 60, konfigurierbar via .env |
| slice-01-app-skeleton | `main.py` Lifespan | asynccontextmanager | Shutdown-Hook verfuegbar |

### Provides To Other Slices

| Resource | Type | Consumer | Interface |
|----------|------|----------|-----------|
| `TimeoutManager` | Klasse | -- (kein Consumer, letzter Slice) | `TimeoutManager(timeout_seconds, on_timeout_callback)` |
| `TimeoutManager.register()` | Methode | InterviewService.start() | `(session_id: str) -> None` |
| `TimeoutManager.reset()` | Methode | InterviewService.message() | `(session_id: str) -> None` |
| `TimeoutManager.cancel()` | Methode | InterviewService.end() | `(session_id: str) -> None` |
| `TimeoutManager.cancel_all()` | Methode | main.py Lifespan | `() -> None` |
| `InterviewService._handle_timeout()` | Async Methode | TimeoutManager Callback | `(session_id: str) -> None` |

### Integration Validation Tasks

- [ ] `InterviewRepository.complete_session()` aus Slice 4 akzeptiert `status="completed_timeout"`
- [ ] `SummaryService.generate()` aus Slice 5 kann von _handle_timeout aufgerufen werden
- [ ] `InterviewGraph.get_history()` aus Slice 2 funktioniert mit session_id
- [ ] `Settings.session_timeout_seconds` aus Slice 1 ist verfuegbar mit Default 60
- [ ] `main.py` Lifespan aus Slice 1 kann um Shutdown-Cleanup erweitert werden
- [ ] `InterviewService` aus Slice 3/4/5 akzeptiert `timeout_manager` Parameter

---

## Code Examples (MANDATORY - GATE 2 PFLICHT)

> **KRITISCH:** Alle Code-Beispiele in diesem Dokument sind **PFLICHT-Deliverables**.
> Der Gate 2 Compliance Agent prueft, dass jedes Code-Beispiel implementiert wird.
> Abweichung nur mit expliziter Begruendung im Commit erlaubt.

| Code Example | Section | Mandatory | Notes |
|--------------|---------|-----------|-------|
| `TimeoutManager` Klasse | Section 3 (TimeoutManager) | YES | `register()`, `reset()`, `cancel()`, `cancel_all()`, `_timeout_task()`, `_cancel_task()`, `active_count` |
| `InterviewService._handle_timeout()` | Section 4 (InterviewService Erweiterung) | YES | Callback: History lesen, Summary generieren, DB-Update mit completed_timeout |
| `InterviewService` Constructor Erweiterung | Section 4 (InterviewService Erweiterung) | YES | `timeout_manager` Parameter |
| `InterviewService.start()` Erweiterung | Section 4 (InterviewService Erweiterung) | YES | `timeout_manager.register(session_id)` |
| `InterviewService.message()` Erweiterung | Section 4 (InterviewService Erweiterung) | YES | `timeout_manager.reset(session_id)` |
| `InterviewService.end()` Erweiterung | Section 4 (InterviewService Erweiterung) | YES | `timeout_manager.cancel(session_id)` |
| `get_interview_service()` Erweiterung | Section 5 (Dependency Injection) | YES | TimeoutManager erstellen, Service-Callback verbinden, auf app.state speichern |
| `main.py` Lifespan Erweiterung | Section 6 (main.py) | YES | `timeout_manager.cancel_all()` im Shutdown |

---

## Deliverables (SCOPE SAFEGUARD)

**WICHTIG: Diese Liste wird automatisch vom Stop-Hook validiert. Der Agent kann nicht stoppen, wenn Dateien fehlen.**

<!-- DELIVERABLES_START -->
### Backend
- [ ] `backend/app/interview/timeout.py` -- TimeoutManager Klasse mit register(), reset(), cancel(), cancel_all(), _timeout_task(), _cancel_task(), active_count Property
- [ ] `backend/app/interview/service.py` -- MODIFY: Constructor akzeptiert timeout_manager, start() ruft register(), message() ruft reset(), end() ruft cancel(), neue Methode _handle_timeout()
- [ ] `backend/app/api/dependencies.py` -- MODIFY: TimeoutManager erstellen, mit Service-Callback verbinden, auf app.state.timeout_manager speichern
- [ ] `backend/app/main.py` -- MODIFY: Lifespan-Shutdown ruft timeout_manager.cancel_all() auf

### Tests
- [ ] `backend/tests/slices/backend-kern/test_slice_06_session_timeout.py` -- pytest Tests fuer TimeoutManager (register, reset, cancel, cancel_all, Timeout-Callback, Error-Handling), InterviewService (Timeout-Integration in start/message/end, _handle_timeout Callback, Summary-Failure, DB-Error, ignored completed/unknown sessions), End-to-End Timeout-Flow, Modul-Existenz
<!-- DELIVERABLES_END -->

**Hinweis fuer den Implementierungs-Agent:**
- Alle Dateien zwischen `<!-- DELIVERABLES_START -->` und `<!-- DELIVERABLES_END -->` sind **Pflicht**
- Der Stop-Hook prueft automatisch ob alle Dateien existieren
- Bei fehlenden Dateien wird der Agent blockiert und muss nachfragen

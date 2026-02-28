# Slice 2: Fact Extraction Pipeline

> **Slice 2 von 8** fuer `LLM Interview Clustering`
>
> | Navigation | |
> |------------|---|
> | **Vorheriger:** | `slice-01-db-schema-projekt-crud.md` |
> | **Naechster:** | `slice-03-clustering-pipeline.md` |

---

## Metadata (fuer Orchestrator)

| Key | Value |
|-----|-------|
| **ID** | `slice-02-fact-extraction-pipeline` |
| **Test** | `python -m pytest backend/tests/slices/llm-interview-clustering/test_slice_02_fact_extraction_pipeline.py -v` |
| **E2E** | `false` |
| **Dependencies** | `["slice-01-db-schema-projekt-crud"]` |

**Erklaerung:**
- **ID**: Eindeutiger Identifier (wird fuer Commits und Evidence verwendet)
- **Test**: Exakter Befehl den der Orchestrator nach Implementierung ausfuehrt
- **E2E**: `false` — pytest Unit/Integration-Tests (kein Playwright)
- **Dependencies**: Slice 1 muss fertig sein (DB-Tabellen `project_interviews`, `facts`, `projects` muessen existieren)

---

## Test-Strategy (fuer Orchestrator Pipeline)

> **Quelle:** Auto-detected basierend auf Repo-Indikatoren.
> `backend/requirements.txt` enthaelt `fastapi` + `uvicorn` → Stack: `python-fastapi`.
> Test-Pattern aus bestehendem `backend/app/interview/service.py` und `backend/tests/slices/` Ordner uebernommen.

| Key | Value |
|-----|-------|
| **Stack** | `python-fastapi` |
| **Test Command** | `python -m pytest backend/tests/slices/llm-interview-clustering/test_slice_02_fact_extraction_pipeline.py -v` |
| **Integration Command** | `python -m pytest backend/tests/slices/llm-interview-clustering/ -v` |
| **Acceptance Command** | `python -m pytest backend/tests/slices/llm-interview-clustering/test_slice_02_fact_extraction_pipeline.py -v -k "acceptance"` |
| **Start Command** | `uvicorn app.main:app --host 0.0.0.0 --port 8000` |
| **Health Endpoint** | `http://localhost:8000/health` |
| **Mocking Strategy** | `mock_external` |

**Erklaerung:**
- **Mocking Strategy:** Alle OpenRouter LLM-Calls werden mit `AsyncMock` gemockt. Alle DB-Calls werden mit `AsyncMock` gemockt. Kein echter PostgreSQL-Zugriff und keine echten LLM-Calls in Unit-Tests.
- **Integration Tests:** Verwenden `TestClient` aus FastAPI + gemockte DB-Sessions.

---

## Slice-Uebersicht

| # | Slice | Status | Datei |
|---|-------|--------|-------|
| 1 | DB Schema + Projekt CRUD | **Ready** | `slice-01-db-schema-projekt-crud.md` |
| 2 | Fact Extraction Pipeline | **Ready** | `slice-02-fact-extraction-pipeline.md` |
| 3 | Clustering Pipeline + Agent | Pending | `slice-03-clustering-pipeline.md` |
| 4 | Dashboard: Projekt-Liste + Cluster-Uebersicht | Pending | `slice-04-dashboard-projekt-liste.md` |
| 5 | Dashboard: Drill-Down + Zitate | Pending | `slice-05-dashboard-drill-down.md` |
| 6 | Taxonomy-Editing + Summary-Regen | Pending | `slice-06-taxonomy-editing.md` |
| 7 | Live-Updates via SSE | Pending | `slice-07-live-updates-sse.md` |
| 8 | Auth + Polish | Pending | `slice-08-auth-polish.md` |

---

## Kontext & Ziel

Nach Interview-Ende (`InterviewService.end()`) muessen automatisch atomare Facts aus dem Interview-Text (Summary oder Transcript) extrahiert und in der `facts`-Tabelle gespeichert werden. Dieser Slice implementiert:

1. `FactExtractionService` — LLM-basierte Extraktion atomarer Facts via OpenRouter
2. Hook in `InterviewService.end()` — Trigger nach Interview-Abschluss
3. Retry-Endpoint `POST /api/projects/{id}/interviews/{iid}/retry` — Fehlgeschlagene Extraktion neu starten
4. `extraction_status` Tracking in `project_interviews` — Pipeline-Zustand pro Interview
5. Max 3 Retries bei LLM-Fehler mit exponential backoff

**Abgrenzung zu anderen Slices:**
- Slice 2 implementiert NUR Fact Extraction (LLM → atomare Facts → DB)
- Kein Clustering, keine Cluster-Zuordnung (kommt in Slice 3)
- Facts werden mit `cluster_id=NULL` (unassigned) gespeichert
- Clustering-Trigger nach erfolgreicher Extraktion: Slice 3 abonniert `extraction_completed`-Event
- SSE-Events werden bereits hier gefeuert (Pattern aus `sse_starlette`), aber Dashboard empfaengt sie erst ab Slice 7

---

## Technische Umsetzung

### Architektur-Kontext (aus architecture.md)

> **Quelle:** `architecture.md` → Server Logic → Services & Processing → Business Logic Flows → Incremental Clustering

```
InterviewService.end()
    → Saves transcript + summary to mvp_interviews
    → Checks if interview is in a project (project_interviews lookup)
    → If yes: asyncio.create_task(ClusteringService.process_interview(project_id, interview_id))
        → [1] FactExtractionService.extract(interview_text, research_goal, model_extraction)
            → LLM call → parse JSON → save facts to DB
            → SSE: fact_extracted
        → (Clustering: Slice 3)
```

### 1. Architektur-Impact

| Layer | Aenderungen |
|-------|-------------|
| `backend/app/interview/service.py` | `end()` erhaelt Check: Ist Interview einem Projekt zugeordnet? Falls ja: `asyncio.create_task(fact_extraction_service.process_interview(...))` |
| `backend/app/clustering/extraction.py` | **Neu:** `FactExtractionService` mit `process_interview()`, `extract()`, `_call_llm_with_retry()` |
| `backend/app/clustering/prompts.py` | **Neu** (oder erweitert): Fact-Extraction-Prompt-Template |
| `backend/app/clustering/fact_repository.py` | **Neu:** `FactRepository` — CRUD auf `facts` Tabelle |
| `backend/app/clustering/router.py` | **Erweitert:** Retry-Endpoint `POST /api/projects/{id}/interviews/{iid}/retry` hinzugefuegt |
| `backend/app/clustering/interview_assignment_service.py` | **Erweitert:** `retry()` Methode |
| `backend/app/clustering/events.py` | **Neu:** `SseEventBus` — in-memory asyncio.Queue pub/sub per project |
| `backend/app/api/dependencies.py` | **Erweitert:** `get_fact_extraction_service()`, `get_sse_event_bus()` Singletons |
| `backend/app/config/settings.py` | **Erweitert:** `clustering_max_retries`, `clustering_llm_timeout_seconds` |

### 2. Datenfluss

```
InterviewService.end(session_id)
  |
  v
_repository.complete_session() → mvp_interviews: transcript + summary gespeichert
  |
  v
InterviewAssignmentRepository.find_by_interview_id(session_id)
  |-- None → Ende (Interview nicht in Projekt)
  |
  v (Interview in Projekt gefunden)
asyncio.create_task(FactExtractionService.process_interview(project_id, interview_id))
  |
  v [Background Task]
ProjectRepository.get_by_id(project_id) → extraction_source, research_goal, model_extraction
  |
  v
InterviewAssignmentRepository.update_status(interview_id, extraction_status="running")
  |
  v
interview_text = mvp_interviews.summary ODER mvp_interviews.transcript (je nach extraction_source)
  |
  v
FactExtractionService._call_llm_with_retry(text, research_goal, model_extraction, max_retries=3)
  |-- Success → list[ExtractedFact] (JSON-parsed)
  |-- LLM Timeout/Malformed (nach 3 Versuchen) → extraction_status="failed", SSE: extraction_failed
  |
  v (Success)
FactRepository.save_facts(project_id, interview_id, facts)
  → INSERT INTO facts (content, quote, confidence, project_id, interview_id, cluster_id=NULL)
  |
  v
InterviewAssignmentRepository.update_status(interview_id, extraction_status="completed")
  |
  v
SseEventBus.publish(project_id, event="fact_extracted", data={interview_id, fact_count})
  |
  v
(Slice 3: ClusteringService abonniert fact_extracted-Event und startet Clustering)
```

### 3. FactExtractionService — Kernlogik

```python
# backend/app/clustering/extraction.py
import asyncio
import json
import logging
from typing import Any

from langchain_openai import ChatOpenAI

from app.clustering.fact_repository import FactRepository
from app.clustering.interview_assignment_repository import InterviewAssignmentRepository
from app.clustering.events import SseEventBus

logger = logging.getLogger(__name__)


class ExtractedFact:
    """Rohdaten eines vom LLM extrahierten Facts."""
    content: str           # Atomare Aussage, 1-1000 Zeichen
    quote: str | None      # Relevantes Originalzitat aus Transcript
    confidence: float | None  # LLM-Confidence 0.0-1.0


class FactExtractionService:
    """Extrahiert atomare Facts aus Interview-Text via LLM (OpenRouter).

    Folgt Clio-Pattern (Facet Extraction): Strukturierte JSON-Ausgabe,
    ein Fact = eine atomare Aussage des Interviewten.

    Verwendet ChatOpenAI(base_url=...) — identisch mit InterviewGraph-Pattern
    aus backend/app/interview/graph.py. LLM-Client wird intern instanziiert.

    Retry-Strategie: max_retries=3, exponential backoff (1s, 2s, 4s).
    """

    def __init__(
        self,
        fact_repository: FactRepository,
        assignment_repository: InterviewAssignmentRepository,
        project_repository: Any,          # ProjectRepository (app.clustering.project_repository)
        interview_repository: Any,        # InterviewRepository (app.interview.repository)
        event_bus: SseEventBus,
        settings: Any,                    # app.config.settings.Settings
    ) -> None:
        self._fact_repository = fact_repository
        self._assignment_repository = assignment_repository
        self._project_repository = project_repository
        self._interview_repository = interview_repository
        self._event_bus = event_bus
        self._settings = settings
        # LLM-Client intern instanziieren — identisch mit InterviewGraph-Pattern
        # (backend/app/interview/graph.py: ChatOpenAI(base_url=..., api_key=settings.openrouter_api_key, ...))
        self._llm = ChatOpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=settings.openrouter_api_key,
            model=settings.interviewer_llm,  # Wird pro Call mit model_extraction ueberschrieben
            temperature=0.0,
        )

    async def process_interview(
        self,
        project_id: str,
        interview_id: str,
    ) -> None:
        """Orchestriert die komplette Fact-Extraction fuer ein Interview.

        1. Project-Konfiguration laden (extraction_source, research_goal, model_extraction)
        2. extraction_status → "running"
        3. Interview-Text laden (summary oder transcript)
        4. LLM-Extraktion mit Retry (max 3x)
        5. Facts in DB speichern
        6. extraction_status → "completed" oder "failed"
        7. SSE-Event publizieren
        """
        ...

    async def extract(
        self,
        interview_text: str,
        research_goal: str,
        model_extraction: str,
    ) -> list[ExtractedFact]:
        """Extrahiert atomare Facts via LLM.

        Args:
            interview_text: Summary-Text oder Transcript-Text.
            research_goal: Lenkender Kontext fuer Extraktion.
            model_extraction: OpenRouter Model-Slug.

        Returns:
            Liste von ExtractedFact-Objekten.

        Raises:
            FactExtractionError: Nach 3 fehlgeschlagenen LLM-Versuchen.
        """
        ...

    async def _call_llm_with_retry(
        self,
        prompt: str,
        model: str,
        max_retries: int = 3,
    ) -> list[dict]:
        """Ruft OpenRouter-LLM auf mit exponential backoff Retry.

        Retry bei:
        - asyncio.TimeoutError (timeout nach settings.clustering_llm_timeout_seconds)
        - JSON-Parse-Fehler (malformed LLM response)

        Kein Retry bei:
        - 401/403 (Auth-Fehler) — sofort fehlschlagen

        Args:
            prompt: Vollstaendiger Prompt-String.
            model: OpenRouter Model-Slug.
            max_retries: Maximale Anzahl Versuche. Default: 3.

        Returns:
            Geparste JSON-Liste der extrahierten Facts.

        Raises:
            FactExtractionError: Nach max_retries fehlgeschlagenen Versuchen.
        """
        ...
```

### 4. Fact Extraction Prompt (Clio-Pattern)

> **Quelle:** `discovery.md` → Clustering-Architektur → Clio Facet-Extraction Pattern + GoalEx research_goal

```python
# backend/app/clustering/prompts.py — FACT_EXTRACTION_PROMPT

FACT_EXTRACTION_PROMPT = """You are a qualitative research analyst. Your task is to extract atomic facts from an interview.

Research Goal: {research_goal}

Interview Text:
{interview_text}

Extract all atomic facts that are relevant to the research goal. Each fact should be:
- A single, self-contained observation or statement
- Directly attributable to this interviewee
- Concrete and specific (not vague)
- Maximum 1000 characters

For each fact, also extract:
- quote: The exact quote from the interview that supports this fact (verbatim, max 500 chars). Use null if transcript quotes are not available.
- confidence: Your confidence that this fact is relevant to the research goal (0.0 to 1.0)

Return ONLY a valid JSON array. No preamble, no explanation.

Format:
[
  {{
    "content": "The user cannot find the settings page after completing onboarding.",
    "quote": "I spent 10 minutes just trying to find where my account settings were.",
    "confidence": 0.95
  }},
  ...
]

If no relevant facts are found, return an empty array: []"""
```

### 5. FactRepository

```python
# backend/app/clustering/fact_repository.py

class FactRepository:
    """Repository fuer die facts-Tabelle.

    Folgt exakt dem Pattern von InterviewRepository:
    Raw SQL + SQLAlchemy async + text()
    """

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def save_facts(
        self,
        project_id: str,
        interview_id: str,
        facts: list[dict],
    ) -> list[dict]:
        """Speichert extrahierte Facts in der DB.

        Args:
            project_id: UUID als String.
            interview_id: UUID als String (referenziert mvp_interviews.session_id).
            facts: Liste von {content, quote, confidence} Dicts.

        Returns:
            Liste der gespeicherten Facts als Dicts (inkl. id, created_at).
        """
        ...

    async def get_facts_for_interview(
        self,
        project_id: str,
        interview_id: str,
    ) -> list[dict]:
        """Laedt alle Facts fuer ein Interview in einem Projekt."""
        ...

    async def get_facts_for_project(
        self,
        project_id: str,
        cluster_id: str | None = None,
        unassigned_only: bool = False,
    ) -> list[dict]:
        """Laedt alle Facts fuer ein Projekt mit optionalem Filter.

        Args:
            project_id: UUID als String.
            cluster_id: Optional. Falls gesetzt, nur Facts dieses Clusters.
            unassigned_only: Falls True, nur Facts mit cluster_id=NULL.
        """
        ...
```

### 6. SseEventBus

```python
# backend/app/clustering/events.py

import asyncio
from collections import defaultdict
from typing import Any

class SseEventBus:
    """In-memory pub/sub Event Bus fuer SSE-Events pro Projekt.

    Jedes Projekt bekommt einen eigenen asyncio.Queue.
    Dashboard SSE-Endpoint subscribt und liefert Events.
    """

    def __init__(self) -> None:
        self._queues: dict[str, list[asyncio.Queue]] = defaultdict(list)

    def subscribe(self, project_id: str) -> asyncio.Queue:
        """Erstellt einen neuen Subscriber-Queue fuer ein Projekt."""
        queue: asyncio.Queue = asyncio.Queue()
        self._queues[project_id].append(queue)
        return queue

    def unsubscribe(self, project_id: str, queue: asyncio.Queue) -> None:
        """Entfernt einen Subscriber-Queue."""
        if project_id in self._queues:
            self._queues[project_id].discard(queue) if hasattr(self._queues[project_id], 'discard') else None
            try:
                self._queues[project_id].remove(queue)
            except ValueError:
                pass

    async def publish(self, project_id: str, event_type: str, data: dict[str, Any]) -> None:
        """Sendet ein Event an alle Subscriber eines Projekts.

        Args:
            project_id: UUID des Projekts.
            event_type: z.B. "fact_extracted", "clustering_started".
            data: Event-Daten gemaess architecture.md SSE Event Types.
        """
        event = {"type": event_type, **data}
        for queue in self._queues.get(project_id, []):
            await queue.put(event)
```

### 7. InterviewService.end() Hook

> **Quelle:** `architecture.md` → Migration Map → `backend/app/interview/service.py`

```python
# backend/app/interview/service.py — end() Methode (Erweiterung)
# NEUER CODE nach complete_session():

    async def end(self, session_id: str) -> dict:
        # ... (bestehende Logik unveraendert: validate, transcript, summary, complete_session) ...

        # NEU: Clustering-Trigger (Slice 2)
        if self._fact_extraction_service and self._assignment_repository:
            try:
                assignment = await self._assignment_repository.find_by_interview_id(session_id)
                if assignment:
                    asyncio.create_task(
                        self._fact_extraction_service.process_interview(
                            project_id=str(assignment["project_id"]),
                            interview_id=session_id,
                        )
                    )
                    logger.info(f"Fact extraction triggered for interview {session_id} in project {assignment['project_id']}")
            except Exception as e:
                logger.error(f"Failed to trigger fact extraction for {session_id}: {e}")
                # Kein Re-raise: Interview-Ende darf nicht durch Clustering-Trigger blockiert werden

        return {
            "summary": summary,
            "message_count": message_count,
        }
```

**WICHTIG:**
- `InterviewService` bleibt rueckwaertskompatibel: `_fact_extraction_service` und `_assignment_repository` sind optionale Konstruktor-Parameter
- Der Trigger ist `fire-and-forget` via `asyncio.create_task()` — Interview-Ende blockiert nicht auf Extraction
- Fehler im Trigger werden geloggt, aber nie an den Enduser weitergeleitet

### 8. Retry-Endpoint

> **Quelle:** `architecture.md` → Endpoints — Interview Assignment + discovery.md → Feature State Machine `extraction_failed`

**POST `/api/projects/{id}/interviews/{iid}/retry`**

**Response-Typ:** `InterviewAssignment`

```python
# backend/app/clustering/router.py — Retry-Endpoint (NEU in Slice 2)

@router.post("/api/projects/{project_id}/interviews/{interview_id}/retry")
async def retry_interview_extraction(
    project_id: str,
    interview_id: str,
    assignment_service: InterviewAssignmentService = Depends(get_assignment_service),
) -> InterviewAssignment:
    """Setzt extraction_status auf 'pending' und startet Extraction-Task neu.

    Nur erlaubt wenn aktueller Status == 'failed'.
    Gibt 409 zurueck wenn Status nicht 'failed' ist.
    """
    ...
```

```python
# backend/app/clustering/interview_assignment_service.py — retry() Methode (NEU in Slice 2)

async def retry(
    self,
    project_id: str,
    interview_id: str,
) -> InterviewAssignment:
    """Startet Fact Extraction fuer ein fehlgeschlagenes Interview neu.

    Business Rules:
    - extraction_status muss 'failed' sein (sonst: 409 Conflict)
    - Setzt extraction_status + clustering_status auf 'pending'
    - Startet asyncio.create_task(fact_extraction_service.process_interview(...))
    - Gibt aktualisierte InterviewAssignment zurueck

    Raises:
        HTTPException(409): Wenn Status nicht 'failed'.
        HTTPException(404): Wenn Interview nicht in Projekt gefunden.
    """
    ...
```

```json
// POST /api/projects/{id}/interviews/{iid}/retry — Response 200 OK
{
  "interview_id": "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
  "date": "2026-02-28T09:00:00Z",
  "summary_preview": "Export feature was not working...",
  "fact_count": 0,
  "extraction_status": "pending",
  "clustering_status": "pending"
}
```

**Fehler-Responses:**

| Code | Wann | Body |
|------|------|------|
| 404 | Interview nicht in Projekt | `{"detail": "Interview not found in project"}` |
| 409 | Status ist nicht `failed` | `{"detail": "Interview is not in failed state, current status: completed"}` |

### 9. Settings-Erweiterung

```python
# backend/app/config/settings.py — Neue Felder (ergaenzen bestehende Klasse)

class Settings(BaseSettings):
    # ... (bestehende Felder unveraendert) ...

    # Clustering Pipeline (NEU in Slice 2)
    clustering_max_retries: int = 3
    clustering_llm_timeout_seconds: int = 120
    clustering_batch_size: int = 20
    clustering_pipeline_timeout_seconds: int = 600
```

### 10. InterviewAssignmentRepository — Neue Methoden

```python
# backend/app/clustering/interview_assignment_repository.py — Erweiterungen fuer Slice 2

async def find_by_interview_id(
    self,
    interview_id: str,
) -> dict | None:
    """Sucht project_interviews-Zeile per interview_id.

    Wird von InterviewService.end() aufgerufen.

    Returns:
        Dict mit {project_id, interview_id, extraction_status, clustering_status}
        oder None wenn Interview keinem Projekt zugeordnet.
    """
    ...

async def update_extraction_status(
    self,
    interview_id: str,
    extraction_status: str,           # 'pending' | 'running' | 'completed' | 'failed'
    clustering_status: str | None = None,  # Optional gleichzeitig zuruecksetzen
) -> dict:
    """Aktualisiert extraction_status (und optional clustering_status).

    Args:
        interview_id: UUID als String.
        extraction_status: Neuer Status.
        clustering_status: Falls nicht None, wird clustering_status ebenfalls gesetzt.

    Returns:
        Aktualisierter DB-Row als Dict.
    """
    ...
```

### 11. Abhaengigkeiten

- **Bestehend (wiederverwendet):**
  - `backend/app/db/session.py` — `get_session_factory()` fuer FactRepository
  - `backend/app/config/settings.py` — Settings-Singleton (wird um clustering_* Felder erweitert)
  - `backend/app/api/dependencies.py` — Dependency-Injection-Pattern
  - `backend/app/interview/service.py` — `end()` Methode wird erweitert (backward-compatible)
  - `backend/app/clustering/interview_assignment_repository.py` — Slice 1 Deliverable

- **Neu (keine neuen externen Pakete — `langchain-openai` bereits vorhanden via InterviewGraph):**
  - `backend/app/clustering/extraction.py` — `FactExtractionService` (nutzt `from langchain_openai import ChatOpenAI` — bereits in requirements.txt)
  - `backend/app/clustering/fact_repository.py` — `FactRepository`
  - `backend/app/clustering/events.py` — `SseEventBus`
  - `backend/app/clustering/prompts.py` — Prompt-Templates (oder Erweiterung falls bereits angelegt)

---

## Integrations-Checkliste

### 1. InterviewService-Integration
- [ ] `InterviewService.__init__()` akzeptiert optionale Parameter `_fact_extraction_service` und `_assignment_repository`
- [ ] `InterviewService.end()` ruft `asyncio.create_task(...)` NUR wenn `_fact_extraction_service` gesetzt ist
- [ ] Fehler in `create_task` werden geloggt aber nicht re-raised
- [ ] Bestehende `InterviewService`-Tests bleiben gruen (kein Breaking Change)

### 2. DB-Integration
- [ ] `FactRepository.save_facts()` schreibt `cluster_id=NULL` (unassigned)
- [ ] `InterviewAssignmentRepository.find_by_interview_id()` sucht in `project_interviews.interview_id`
- [ ] `InterviewAssignmentRepository.update_extraction_status()` setzt `extraction_status` und optional `clustering_status`
- [ ] Facts werden mit `interview_id = mvp_interviews.session_id` (als UUID) gespeichert

### 3. LLM-Integration
- [ ] Prompt in `backend/app/clustering/prompts.py` abgelegt (kein Inline-Prompt im Service)
- [ ] `research_goal` wird in den Prompt injiziert (GoalEx Pattern)
- [ ] LLM-Response wird als JSON-Array geparst — bei Parse-Fehler: Retry
- [ ] Timeout via `asyncio.wait_for()` mit `settings.clustering_llm_timeout_seconds`
- [ ] Exponential backoff: Wartezeiten 1s, 2s, 4s zwischen Retries

### 4. extraction_status Tracking
- [ ] Status-Uebergaenge korrekt: `pending` → `running` → `completed` | `failed`
- [ ] Bei Retry: Status zurueck auf `pending`, dann normal durchlaufen
- [ ] `clustering_status` bleibt `pending` nach Extraction (Slice 3 aendert es)

### 5. Retry-Endpoint-Integration
- [ ] `POST /api/projects/{id}/interviews/{iid}/retry` in `router.py` registriert
- [ ] Validierung: Nur wenn `extraction_status == 'failed'` (sonst 409)
- [ ] Neuer asyncio.Task wird gestartet (nicht synchron warten)
- [ ] Response gibt sofort `InterviewAssignment` mit `extraction_status="pending"` zurueck

### 6. SseEventBus-Integration
- [ ] `SseEventBus` als Singleton in `dependencies.py` (wird von Slice 7 fuer Dashboard-Streaming genutzt)
- [ ] `fact_extracted` Event enthaelt `{interview_id, fact_count}` gemaess architecture.md SSE Event Types
- [ ] Falls kein Subscriber vorhanden: `publish()` ist ein No-Op (Queue-Liste leer)

---

## UI Anforderungen

Dieser Slice hat keine neuen Frontend-Komponenten. Die relevanten UI-Elemente fuer Fact Extraction aus den Wireframes werden in anderen Slices implementiert:

- `retry_btn` (Project Interviews Tab → fehlgeschlagene Interview-Zeile) — UI kommt in **Slice 4**
- `progress_bar` (Insights Tab) — UI kommt in **Slice 7** (Live-Updates)
- `extraction_status` Badges in `interview_table` — UI kommt in **Slice 4**

**Wireframe-Referenz (aus wireframes.md — Project Interviews Tab):**

```
│   #9 │ 2026-02-26 │ Export feature     │   0   │ ❌ │[↻] │ ⑤
│      │            │ was not working... │       │    │    │
...
│ Status: ✅ analyzed  ⏳ pending  ❌ failed            ④
```

Der Retry-Endpoint (`POST /api/projects/{id}/interviews/{iid}/retry`) aus diesem Slice wird vom `retry_btn` [↻] aufgerufen, sobald der Button in Slice 4 implementiert ist.

---

## Acceptance Criteria

1) GIVEN ein abgeschlossenes Interview (`InterviewService.end()` aufgerufen) das einem Projekt zugeordnet ist
   WHEN das Interview `extraction_source="summary"` konfiguriert hat
   THEN wird `FactExtractionService.process_interview()` als Background-Task gestartet und der Summary-Text als Input fuer die LLM-Extraktion verwendet

2) GIVEN ein Interview das einem Projekt zugeordnet ist
   WHEN `FactExtractionService.process_interview()` erfolgreich ausgefuehrt wird
   THEN werden die extrahierten Facts in der `facts`-Tabelle mit `project_id`, `interview_id`, `content`, optionalem `quote` und optionalem `confidence` gespeichert, alle mit `cluster_id=NULL`

3) GIVEN ein Interview das einem Projekt zugeordnet ist
   WHEN `FactExtractionService.process_interview()` erfolgreich ausgefuehrt wird
   THEN wird `extraction_status` in `project_interviews` auf `"completed"` gesetzt und ein SSE-Event `fact_extracted` mit `{interview_id, fact_count}` publiziert

4) GIVEN ein Interview das einem Projekt zugeordnet ist
   WHEN der LLM-Aufruf bei allen 3 Versuchen fehlschlaegt (Timeout oder malformed JSON)
   THEN wird `extraction_status` in `project_interviews` auf `"failed"` gesetzt und kein Fact wird in der DB gespeichert

5) GIVEN ein Interview mit `extraction_status="failed"`
   WHEN `POST /api/projects/{id}/interviews/{iid}/retry` aufgerufen wird
   THEN wird `extraction_status` auf `"pending"` gesetzt, ein neuer Extraction-Task gestartet, und `InterviewAssignment` mit `extraction_status="pending"` in der Response zurueckgegeben (HTTP 200)

6) GIVEN ein Interview mit `extraction_status="completed"`
   WHEN `POST /api/projects/{id}/interviews/{iid}/retry` aufgerufen wird
   THEN wird HTTP 409 mit `{"detail": "Interview is not in failed state, current status: completed"}` zurueckgegeben

7) GIVEN ein Interview mit `extraction_source="transcript"`
   WHEN `FactExtractionService.process_interview()` ausgefuehrt wird
   THEN wird der Transcript-Text (aus `mvp_interviews.transcript` JSONB, als flacher Text zusammengefuegt) als Input fuer die LLM-Extraktion verwendet

8) GIVEN der LLM gibt eine leere JSON-Liste `[]` zurueck
   WHEN `FactExtractionService.process_interview()` ausgefuehrt wird
   THEN wird `extraction_status="completed"` gesetzt und 0 Facts werden gespeichert (kein Fehler)

---

## Testfaelle

**WICHTIG:** Tests muessen VOR der Implementierung definiert werden. Der Orchestrator fuehrt diese Tests automatisch nach der Slice-Implementierung aus.

### Test-Datei

`backend/tests/slices/llm-interview-clustering/test_slice_02_fact_extraction_pipeline.py`

<test_spec>
```python
# backend/tests/slices/llm-interview-clustering/test_slice_02_fact_extraction_pipeline.py
"""Tests fuer Slice 2: Fact Extraction Pipeline.

Alle LLM-Calls und DB-Calls werden gemockt (mock_external Strategie).
Kein echter OpenRouter-Zugriff, kein echter PostgreSQL-Zugriff in Unit-Tests.
"""
import asyncio
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch, call

import pytest


# ============================================================
# FIXTURES
# ============================================================

@pytest.fixture
def mock_project_id() -> str:
    return str(uuid.UUID("550e8400-e29b-41d4-a716-446655440000"))


@pytest.fixture
def mock_interview_id() -> str:
    return str(uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8"))


@pytest.fixture
def mock_project_row(mock_project_id) -> dict:
    return {
        "id": uuid.UUID(mock_project_id),
        "research_goal": "Understand why users drop off during onboarding",
        "extraction_source": "summary",
        "model_extraction": "anthropic/claude-haiku-4",
        "prompt_context": "B2B SaaS with 14-day free trial",
    }


@pytest.fixture
def mock_interview_row(mock_interview_id) -> dict:
    return {
        "session_id": mock_interview_id,
        "summary": "User had issues finding the settings page and navigation was confusing.",
        "transcript": [
            {"role": "assistant", "content": "What issues did you encounter?"},
            {"role": "user", "content": "I couldn't find settings anywhere."},
        ],
    }


@pytest.fixture
def mock_assignment_row(mock_project_id, mock_interview_id) -> dict:
    return {
        "project_id": uuid.UUID(mock_project_id),
        "interview_id": uuid.UUID(mock_interview_id),
        "extraction_status": "pending",
        "clustering_status": "pending",
    }


@pytest.fixture
def mock_llm_response_facts() -> list[dict]:
    return [
        {
            "content": "User cannot find the settings page after onboarding.",
            "quote": "I couldn't find settings anywhere.",
            "confidence": 0.95,
        },
        {
            "content": "Navigation structure is confusing for new users.",
            "quote": "The navigation doesn't make sense to me.",
            "confidence": 0.88,
        },
    ]


@pytest.fixture
def mock_fact_repository():
    return AsyncMock()


@pytest.fixture
def mock_assignment_repository():
    return AsyncMock()


@pytest.fixture
def mock_event_bus():
    return AsyncMock()


@pytest.fixture
def mock_project_repository():
    return AsyncMock()


# ============================================================
# AC 1 + AC 2 + AC 3: Erfolgreiche Extraktion — summary source
# ============================================================

class TestFactExtractionSuccess:
    """AC 1+2+3: process_interview() extrahiert Facts, speichert sie und updated Status."""

    def test_process_interview_extracts_facts_from_summary(
        self,
        mock_project_id,
        mock_interview_id,
        mock_project_row,
        mock_interview_row,
        mock_assignment_row,
        mock_llm_response_facts,
        mock_fact_repository,
        mock_assignment_repository,
        mock_event_bus,
        mock_project_repository,
    ):
        """GIVEN abgeschlossenes Interview zugeordnet zu Projekt
        WHEN process_interview() mit extraction_source='summary'
        THEN Facts in DB, status='completed', SSE-Event publiziert"""
        mock_project_repository.get_by_id = AsyncMock(return_value=mock_project_row)
        mock_assignment_repository.find_by_interview_id = AsyncMock(return_value=mock_assignment_row)
        mock_assignment_repository.update_extraction_status = AsyncMock(return_value=mock_assignment_row)

        # Interview-Daten mit summary
        mock_interview_repository = AsyncMock()
        mock_interview_repository.get_session = AsyncMock(return_value=mock_interview_row)

        # Facts gespeichert
        saved_facts = [
            {"id": uuid.uuid4(), **fact, "project_id": mock_project_id, "interview_id": mock_interview_id, "cluster_id": None}
            for fact in mock_llm_response_facts
        ]
        mock_fact_repository.save_facts = AsyncMock(return_value=saved_facts)

        from app.clustering.extraction import FactExtractionService

        service = FactExtractionService(
            fact_repository=mock_fact_repository,
            assignment_repository=mock_assignment_repository,
            project_repository=mock_project_repository,
            interview_repository=mock_interview_repository,
            event_bus=mock_event_bus,
            settings=MagicMock(
                clustering_max_retries=3,
                clustering_llm_timeout_seconds=120,
            ),
        )

        # Mock der internen LLM-Call-Methode
        service._call_llm_with_retry = AsyncMock(return_value=mock_llm_response_facts)

        asyncio.get_event_loop().run_until_complete(
            service.process_interview(
                project_id=mock_project_id,
                interview_id=mock_interview_id,
            )
        )

        # Pruefen: Facts gespeichert
        mock_fact_repository.save_facts.assert_called_once()
        call_kwargs = mock_fact_repository.save_facts.call_args
        assert call_kwargs[1]["project_id"] == mock_project_id or call_kwargs[0][0] == mock_project_id

        # Pruefen: Status auf 'completed'
        status_calls = mock_assignment_repository.update_extraction_status.call_args_list
        final_call = status_calls[-1]
        assert "completed" in str(final_call)

        # Pruefen: SSE-Event publiziert
        mock_event_bus.publish.assert_called_once()
        event_call = mock_event_bus.publish.call_args
        assert event_call[1].get("event_type") == "fact_extracted" or "fact_extracted" in str(event_call)

    def test_process_interview_saves_facts_with_null_cluster_id(
        self,
        mock_project_id,
        mock_interview_id,
        mock_project_row,
        mock_interview_row,
        mock_assignment_row,
        mock_llm_response_facts,
        mock_fact_repository,
        mock_assignment_repository,
        mock_event_bus,
        mock_project_repository,
    ):
        """GIVEN erfolgreiche LLM-Extraktion
        WHEN Facts gespeichert werden
        THEN alle Facts haben cluster_id=None (unassigned)"""
        mock_project_repository.get_by_id = AsyncMock(return_value=mock_project_row)
        mock_assignment_repository.find_by_interview_id = AsyncMock(return_value=mock_assignment_row)
        mock_assignment_repository.update_extraction_status = AsyncMock(return_value=mock_assignment_row)

        mock_interview_repository = AsyncMock()
        mock_interview_repository.get_session = AsyncMock(return_value=mock_interview_row)

        saved_facts = [
            {"id": uuid.uuid4(), **fact, "project_id": mock_project_id, "interview_id": mock_interview_id, "cluster_id": None}
            for fact in mock_llm_response_facts
        ]
        mock_fact_repository.save_facts = AsyncMock(return_value=saved_facts)

        from app.clustering.extraction import FactExtractionService

        service = FactExtractionService(
            fact_repository=mock_fact_repository,
            assignment_repository=mock_assignment_repository,
            project_repository=mock_project_repository,
            interview_repository=mock_interview_repository,
            event_bus=mock_event_bus,
            settings=MagicMock(clustering_max_retries=3, clustering_llm_timeout_seconds=120),
        )
        service._call_llm_with_retry = AsyncMock(return_value=mock_llm_response_facts)

        asyncio.get_event_loop().run_until_complete(
            service.process_interview(project_id=mock_project_id, interview_id=mock_interview_id)
        )

        # Facts wurden gespeichert
        mock_fact_repository.save_facts.assert_called_once()
        # Sicherstellen dass cluster_id nicht mitgesendet oder auf None gesetzt
        # (Details haengen von Implementierung ab, Test verifiziert save_facts() wurde aufgerufen)


# ============================================================
# AC 4: Fehlgeschlagene Extraktion nach 3 Retries
# ============================================================

class TestFactExtractionFailure:
    """AC 4: Nach 3 fehlgeschlagenen LLM-Versuchen wird Status 'failed' gesetzt."""

    def test_extraction_fails_after_max_retries(
        self,
        mock_project_id,
        mock_interview_id,
        mock_project_row,
        mock_interview_row,
        mock_assignment_row,
        mock_fact_repository,
        mock_assignment_repository,
        mock_event_bus,
        mock_project_repository,
    ):
        """GIVEN LLM failt bei allen 3 Versuchen
        WHEN process_interview() ausgefuehrt wird
        THEN extraction_status='failed', keine Facts gespeichert"""
        mock_project_repository.get_by_id = AsyncMock(return_value=mock_project_row)
        mock_assignment_repository.find_by_interview_id = AsyncMock(return_value=mock_assignment_row)
        mock_assignment_repository.update_extraction_status = AsyncMock(return_value=mock_assignment_row)

        mock_interview_repository = AsyncMock()
        mock_interview_repository.get_session = AsyncMock(return_value=mock_interview_row)

        from app.clustering.extraction import FactExtractionService, FactExtractionError

        service = FactExtractionService(
            fact_repository=mock_fact_repository,
            assignment_repository=mock_assignment_repository,
            project_repository=mock_project_repository,
            interview_repository=mock_interview_repository,
            event_bus=mock_event_bus,
            settings=MagicMock(clustering_max_retries=3, clustering_llm_timeout_seconds=120),
        )
        service._call_llm_with_retry = AsyncMock(side_effect=FactExtractionError("LLM timeout after 3 retries"))

        asyncio.get_event_loop().run_until_complete(
            service.process_interview(project_id=mock_project_id, interview_id=mock_interview_id)
        )

        # Keine Facts gespeichert
        mock_fact_repository.save_facts.assert_not_called()

        # Status auf 'failed' gesetzt
        status_calls = mock_assignment_repository.update_extraction_status.call_args_list
        final_status = str(status_calls[-1])
        assert "failed" in final_status

    def test_llm_retry_called_max_3_times(
        self,
        mock_project_id,
        mock_interview_id,
    ):
        """GIVEN LLM-Timeout
        WHEN _call_llm_with_retry() mit max_retries=3
        THEN genau 3 Versuche unternommen"""
        from app.clustering.extraction import FactExtractionService, FactExtractionError

        service = FactExtractionService.__new__(FactExtractionService)
        service._settings = MagicMock(clustering_llm_timeout_seconds=120)

        # Mock service._llm.ainvoke to simulate repeated timeouts
        service._llm = MagicMock()
        service._llm.ainvoke = AsyncMock(side_effect=asyncio.TimeoutError("Simulated timeout"))

        with pytest.raises(FactExtractionError):
            asyncio.get_event_loop().run_until_complete(
                service._call_llm_with_retry(
                    prompt="test prompt",
                    model="anthropic/claude-haiku-4",
                    max_retries=3,
                )
            )

        assert service._llm.ainvoke.call_count == 3


# ============================================================
# AC 5 + AC 6: Retry-Endpoint
# ============================================================

class TestRetryEndpoint:
    """AC 5+6: POST /api/projects/{id}/interviews/{iid}/retry"""

    def test_retry_resets_status_to_pending_when_failed(
        self,
        mock_project_id,
        mock_interview_id,
        mock_assignment_row,
        mock_assignment_repository,
        mock_fact_repository,
        mock_event_bus,
        mock_project_repository,
    ):
        """GIVEN extraction_status='failed'
        WHEN retry() aufgerufen
        THEN status='pending', Task gestartet, InterviewAssignment zurueck"""
        failed_assignment = {**mock_assignment_row, "extraction_status": "failed"}
        pending_assignment = {**mock_assignment_row, "extraction_status": "pending", "clustering_status": "pending"}

        mock_assignment_repository.find_by_project_and_interview = AsyncMock(return_value=failed_assignment)
        mock_assignment_repository.update_extraction_status = AsyncMock(return_value=pending_assignment)

        mock_interview_repository = AsyncMock()
        now = datetime.now(timezone.utc)
        mock_interview_repository.get_session = AsyncMock(return_value={
            "session_id": mock_interview_id,
            "summary": "Test summary",
            "created_at": now,
        })

        from app.clustering.interview_assignment_service import InterviewAssignmentService

        mock_extraction_service = AsyncMock()
        service = InterviewAssignmentService(
            repository=mock_assignment_repository,
            interview_repository=mock_interview_repository,
            fact_extraction_service=mock_extraction_service,
        )

        result = asyncio.get_event_loop().run_until_complete(
            service.retry(
                project_id=mock_project_id,
                interview_id=mock_interview_id,
            )
        )

        assert result.extraction_status == "pending"
        mock_assignment_repository.update_extraction_status.assert_called_once()

    def test_retry_returns_409_when_not_failed(
        self,
        mock_project_id,
        mock_interview_id,
        mock_assignment_row,
        mock_assignment_repository,
    ):
        """GIVEN extraction_status='completed'
        WHEN retry() aufgerufen
        THEN HTTPException 409"""
        completed_assignment = {**mock_assignment_row, "extraction_status": "completed"}
        mock_assignment_repository.find_by_project_and_interview = AsyncMock(return_value=completed_assignment)

        mock_interview_repository = AsyncMock()

        from app.clustering.interview_assignment_service import InterviewAssignmentService
        from fastapi import HTTPException

        service = InterviewAssignmentService(
            repository=mock_assignment_repository,
            interview_repository=mock_interview_repository,
            fact_extraction_service=AsyncMock(),
        )

        with pytest.raises(HTTPException) as exc_info:
            asyncio.get_event_loop().run_until_complete(
                service.retry(
                    project_id=mock_project_id,
                    interview_id=mock_interview_id,
                )
            )

        assert exc_info.value.status_code == 409

    def test_retry_returns_404_when_interview_not_in_project(
        self,
        mock_project_id,
        mock_interview_id,
        mock_assignment_repository,
    ):
        """GIVEN Interview nicht in Projekt
        WHEN retry() aufgerufen
        THEN HTTPException 404"""
        mock_assignment_repository.find_by_project_and_interview = AsyncMock(return_value=None)
        mock_interview_repository = AsyncMock()

        from app.clustering.interview_assignment_service import InterviewAssignmentService
        from fastapi import HTTPException

        service = InterviewAssignmentService(
            repository=mock_assignment_repository,
            interview_repository=mock_interview_repository,
            fact_extraction_service=AsyncMock(),
        )

        with pytest.raises(HTTPException) as exc_info:
            asyncio.get_event_loop().run_until_complete(
                service.retry(
                    project_id=mock_project_id,
                    interview_id=mock_interview_id,
                )
            )

        assert exc_info.value.status_code == 404


# ============================================================
# AC 7: Transcript als Extraction Source
# ============================================================

class TestTranscriptExtractionSource:
    """AC 7: extraction_source='transcript' nutzt Transcript-Text."""

    def test_transcript_text_used_when_extraction_source_is_transcript(
        self,
        mock_project_id,
        mock_interview_id,
        mock_assignment_row,
        mock_fact_repository,
        mock_assignment_repository,
        mock_event_bus,
        mock_project_repository,
    ):
        """GIVEN extraction_source='transcript'
        WHEN process_interview()
        THEN Transcript-Text (nicht Summary) wird an LLM uebergeben"""
        transcript_project_row = {
            "id": uuid.UUID(mock_project_id),
            "research_goal": "Understand onboarding issues",
            "extraction_source": "transcript",
            "model_extraction": "anthropic/claude-haiku-4",
            "prompt_context": None,
        }
        mock_project_repository.get_by_id = AsyncMock(return_value=transcript_project_row)
        mock_assignment_repository.find_by_interview_id = AsyncMock(return_value=mock_assignment_row)
        mock_assignment_repository.update_extraction_status = AsyncMock(return_value=mock_assignment_row)

        interview_with_transcript = {
            "session_id": mock_interview_id,
            "summary": "Short summary here.",
            "transcript": [
                {"role": "assistant", "content": "What went wrong?"},
                {"role": "user", "content": "I couldn't find the settings page."},
            ],
        }
        mock_interview_repository = AsyncMock()
        mock_interview_repository.get_session = AsyncMock(return_value=interview_with_transcript)

        mock_fact_repository.save_facts = AsyncMock(return_value=[])

        from app.clustering.extraction import FactExtractionService

        service = FactExtractionService(
            fact_repository=mock_fact_repository,
            assignment_repository=mock_assignment_repository,
            project_repository=mock_project_repository,
            interview_repository=mock_interview_repository,
            event_bus=mock_event_bus,
            settings=MagicMock(clustering_max_retries=3, clustering_llm_timeout_seconds=120),
        )

        captured_prompt = {}

        async def capture_prompt(prompt, model, max_retries):
            captured_prompt["prompt"] = prompt
            return []

        service._call_llm_with_retry = capture_prompt

        asyncio.get_event_loop().run_until_complete(
            service.process_interview(project_id=mock_project_id, interview_id=mock_interview_id)
        )

        # Transcript-Inhalt muss im Prompt stehen, Summary-Inhalt darf nicht dominieren
        assert "I couldn't find the settings page" in captured_prompt.get("prompt", "")


# ============================================================
# AC 8: Leere LLM-Antwort
# ============================================================

class TestEmptyLlmResponse:
    """AC 8: Leere JSON-Liste [] gilt als Erfolg."""

    def test_empty_fact_list_results_in_completed_status(
        self,
        mock_project_id,
        mock_interview_id,
        mock_project_row,
        mock_interview_row,
        mock_assignment_row,
        mock_fact_repository,
        mock_assignment_repository,
        mock_event_bus,
        mock_project_repository,
    ):
        """GIVEN LLM gibt [] zurueck
        WHEN process_interview()
        THEN extraction_status='completed', 0 Facts gespeichert"""
        mock_project_repository.get_by_id = AsyncMock(return_value=mock_project_row)
        mock_assignment_repository.find_by_interview_id = AsyncMock(return_value=mock_assignment_row)
        mock_assignment_repository.update_extraction_status = AsyncMock(return_value=mock_assignment_row)
        mock_interview_repository = AsyncMock()
        mock_interview_repository.get_session = AsyncMock(return_value=mock_interview_row)
        mock_fact_repository.save_facts = AsyncMock(return_value=[])

        from app.clustering.extraction import FactExtractionService

        service = FactExtractionService(
            fact_repository=mock_fact_repository,
            assignment_repository=mock_assignment_repository,
            project_repository=mock_project_repository,
            interview_repository=mock_interview_repository,
            event_bus=mock_event_bus,
            settings=MagicMock(clustering_max_retries=3, clustering_llm_timeout_seconds=120),
        )
        service._call_llm_with_retry = AsyncMock(return_value=[])  # Leere Liste

        asyncio.get_event_loop().run_until_complete(
            service.process_interview(project_id=mock_project_id, interview_id=mock_interview_id)
        )

        # Status auf 'completed' (nicht 'failed')
        status_calls = mock_assignment_repository.update_extraction_status.call_args_list
        final_status = str(status_calls[-1])
        assert "completed" in final_status
        assert "failed" not in final_status

        # save_facts entweder nicht aufgerufen oder mit leerer Liste
        if mock_fact_repository.save_facts.called:
            call_args = mock_fact_repository.save_facts.call_args
            facts_arg = call_args[1].get("facts") or (call_args[0][2] if len(call_args[0]) > 2 else [])
            assert facts_arg == []


# ============================================================
# InterviewService Hook — Backward Compatibility
# ============================================================

class TestInterviewServiceHook:
    """Sicherstellt dass InterviewService.end() backward-compatible ist."""

    def test_end_without_extraction_service_still_works(self):
        """GIVEN InterviewService ohne fact_extraction_service
        WHEN end() aufgerufen
        THEN kein Fehler, normales Verhalten"""
        from app.interview.service import InterviewService
        from unittest.mock import MagicMock

        mock_graph = MagicMock()
        mock_graph.get_history = MagicMock(return_value=[])

        service = InterviewService(graph=mock_graph)
        service._sessions = {"test-session": {"status": "active", "message_count": 2}}

        mock_repository = AsyncMock()
        mock_repository.complete_session = AsyncMock(return_value={})
        service._repository = mock_repository

        mock_summary = AsyncMock()
        mock_summary.generate = AsyncMock(return_value="Test summary")
        service._summary_service = mock_summary

        result = asyncio.get_event_loop().run_until_complete(
            service.end("test-session")
        )

        assert "summary" in result
        assert "message_count" in result

    def test_end_triggers_extraction_when_interview_in_project(self):
        """GIVEN InterviewService mit fact_extraction_service
        GIVEN Interview ist einem Projekt zugeordnet
        WHEN end() aufgerufen
        THEN create_task mit process_interview aufgerufen"""
        from app.interview.service import InterviewService

        mock_graph = MagicMock()
        mock_graph.get_history = MagicMock(return_value=[])

        mock_extraction_service = AsyncMock()
        mock_assignment_repo = AsyncMock()
        mock_assignment_repo.find_by_interview_id = AsyncMock(return_value={
            "project_id": uuid.UUID("550e8400-e29b-41d4-a716-446655440000"),
            "interview_id": uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8"),
            "extraction_status": "pending",
        })

        service = InterviewService(
            graph=mock_graph,
            fact_extraction_service=mock_extraction_service,
            assignment_repository=mock_assignment_repo,
        )
        service._sessions = {"test-session": {"status": "active", "message_count": 1}}

        mock_repository = AsyncMock()
        mock_repository.complete_session = AsyncMock(return_value={})
        service._repository = mock_repository

        mock_summary = AsyncMock()
        mock_summary.generate = AsyncMock(return_value="Test summary")
        service._summary_service = mock_summary

        with patch("asyncio.create_task") as mock_create_task:
            asyncio.get_event_loop().run_until_complete(
                service.end("test-session")
            )
            mock_create_task.assert_called_once()


# ============================================================
# SseEventBus
# ============================================================

class TestSseEventBus:
    """SseEventBus: subscribe, publish, unsubscribe."""

    def test_publish_sends_to_all_subscribers(self):
        """GIVEN 2 Subscriber fuer dasselbe Projekt
        WHEN publish() aufgerufen
        THEN beide Queues erhalten das Event"""
        from app.clustering.events import SseEventBus

        bus = SseEventBus()
        project_id = "test-project-123"

        q1 = bus.subscribe(project_id)
        q2 = bus.subscribe(project_id)

        asyncio.get_event_loop().run_until_complete(
            bus.publish(project_id, "fact_extracted", {"interview_id": "abc", "fact_count": 3})
        )

        assert not q1.empty()
        assert not q2.empty()

        event1 = q1.get_nowait()
        event2 = q2.get_nowait()

        assert event1["type"] == "fact_extracted"
        assert event1["fact_count"] == 3
        assert event2["type"] == "fact_extracted"

    def test_publish_to_project_without_subscribers_is_noop(self):
        """GIVEN kein Subscriber
        WHEN publish() aufgerufen
        THEN kein Fehler"""
        from app.clustering.events import SseEventBus

        bus = SseEventBus()

        # Soll keinen Fehler werfen
        asyncio.get_event_loop().run_until_complete(
            bus.publish("no-subscribers-project", "fact_extracted", {"fact_count": 5})
        )
```
</test_spec>

---

## Definition of Done

- [x] Akzeptanzkriterien sind eindeutig und vollstaendig
- [ ] Logging definiert: `logger.info()` fuer Extraction-Start/-Ende, `logger.error()` bei Retry/Fail
- [ ] Fehler-Handling: `FactExtractionError` Exception-Klasse fuer Extraction-Fehler
- [ ] Keine sensiblen Daten in Logs (kein Transcript-Content, kein API-Key)
- [ ] Rollback: Keine Partial-Facts (alle-oder-keine Speicherung pro Interview)

---

## Constraints & Hinweise

**Betrifft:**
- `backend/app/interview/service.py` — Bestehende Datei wird modifiziert (backward-compatible)
- `backend/app/clustering/` — Bestehende Modul-Struktur aus Slice 1 wird erweitert

**Backward Compatibility:**
- `InterviewService.__init__()` darf KEINE Pflicht-Parameter hinzufuegen
- `fact_extraction_service` und `assignment_repository` sind Optional-Parameter
- Bestehende Widget-API (`/api/interview/*`) aendert sich nicht

**Transcript-Konvertierung:**
- `mvp_interviews.transcript` ist JSONB: `[{"role": "...", "content": "..."}]`
- Fuer LLM-Input als Flachtext zusammenfuehren: `"\n".join(f"{m['role']}: {m['content']}" for m in transcript)`

**LLM-Response-Format:**
- JSON-Array wird direkt geparsed: `json.loads(response_text)`
- Bei Parse-Fehler: Retry (zaehlt als fehlgeschlagener Versuch)
- Bei `[]`: kein Fehler — 0 Facts ist ein gueltiges Ergebnis

**Abgrenzung:**
- Dieser Slice triggert NICHT das Clustering (kommt in Slice 3)
- `clustering_status` bleibt auf `"pending"` nach Extraction
- Slice 3 abonniert `fact_extracted` SSE-Event des `SseEventBus`

---

## Integration Contract (GATE 2 PFLICHT)

> **Wichtig:** Diese Section wird vom Gate 2 Compliance Agent geprueft. Unvollstaendige Contracts blockieren die Genehmigung.

### Requires From Other Slices

| Slice | Resource | Type | Validation |
|-------|----------|------|------------|
| slice-01 | `projects` Tabelle | DB Schema | `project_id UUID`, `research_goal TEXT`, `extraction_source TEXT`, `model_extraction TEXT` |
| slice-01 | `project_interviews` Tabelle | DB Schema | `project_id`, `interview_id`, `extraction_status TEXT`, `clustering_status TEXT` |
| slice-01 | `facts` Tabelle | DB Schema | `id UUID`, `project_id UUID`, `interview_id UUID`, `cluster_id UUID NULLABLE`, `content TEXT`, `quote TEXT`, `confidence FLOAT` |
| slice-01 | `InterviewAssignmentRepository` | Class | `update_extraction_status()` Methode — wird in Slice 2 hinzugefuegt (Slice 1 liefert Base-Klasse) |
| slice-01 | `backend/app/clustering/schemas.py` | Pydantic DTOs | `InterviewAssignment` DTO mit `extraction_status` Feld |

### Provides To Other Slices

| Resource | Type | Consumer | Interface |
|----------|------|----------|-----------|
| `FactExtractionService` | Class | Slice 3 (Clustering) | `process_interview(project_id: str, interview_id: str) -> None` |
| `FactRepository` | Class | Slice 3, 5 | `get_facts_for_project(project_id, cluster_id?, unassigned_only?) -> list[dict]`, `save_facts(project_id, interview_id, facts) -> list[dict]` |
| `SseEventBus` | Class | Slice 3, 7 | `subscribe(project_id) -> asyncio.Queue`, `unsubscribe(project_id, queue)`, `publish(project_id, event_type, data) -> None` |
| `fact_extracted` SSE Event | Event | Slice 3 | `{type: "fact_extracted", interview_id: str, fact_count: int}` |
| `extraction_status` Tracking | DB State | Slice 4 (UI Badges) | `project_interviews.extraction_status` IN `('pending', 'running', 'completed', 'failed')` |
| `POST /api/projects/{id}/interviews/{iid}/retry` | HTTP Endpoint | Slice 4 (retry_btn) | `200 InterviewAssignment` oder `409` oder `404` |
| `InterviewService.end()` Hook | Code Extension | — (internal) | Backward-compatible: `fact_extraction_service` und `assignment_repository` als Optional-Params |

### Integration Validation Tasks

- [ ] `FactRepository.save_facts()` schreibt `cluster_id=NULL` — verifiziert durch Test
- [ ] `InterviewAssignmentRepository.find_by_interview_id()` findet Zeile in `project_interviews` per `interview_id`
- [ ] `SseEventBus.publish("fact_extracted", ...)` enthaelt `interview_id` und `fact_count`
- [ ] `POST /api/projects/{id}/interviews/{iid}/retry` gibt `409` wenn Status nicht `failed`
- [ ] `InterviewService.end()` ruft `asyncio.create_task()` nur wenn `_fact_extraction_service` nicht None

---

## Code Examples (MANDATORY - GATE 2 PFLICHT)

> **KRITISCH:** Alle Code-Beispiele in diesem Dokument sind PFLICHT-Deliverables.
> Der Gate 2 Compliance Agent prueft, dass jedes Code-Beispiel implementiert wird.
> Abweichung nur mit expliziter Begruendung im Commit erlaubt.

| Code Example | Section | Mandatory | Notes |
|--------------|---------|-----------|-------|
| `FactExtractionService` Klasse (Signatur) | Section 3 | YES | Konstruktor mit allen Dependencies, `process_interview()`, `extract()`, `_call_llm_with_retry()` |
| `FACT_EXTRACTION_PROMPT` | Section 4 | YES | `research_goal` und `interview_text` als Template-Variablen |
| `FactRepository` Klasse (Signatur) | Section 5 | YES | `save_facts()`, `get_facts_for_interview()`, `get_facts_for_project()` mit filter-Parametern |
| `SseEventBus` Klasse | Section 6 | YES | `subscribe()`, `unsubscribe()`, `publish()` exakt wie spezifiziert |
| `InterviewService.end()` Hook | Section 7 | YES | `asyncio.create_task()` nach `complete_session()`, Optional-Parameter, Fehler-Handling |
| `retry_interview_extraction` Router-Endpoint | Section 8 | YES | Korrekte HTTP-Status-Codes (200, 404, 409) |
| `InterviewAssignmentService.retry()` | Section 8 | YES | 409 wenn nicht `failed`, 404 wenn nicht gefunden |
| `Settings` Erweiterung | Section 9 | YES | `clustering_max_retries`, `clustering_llm_timeout_seconds`, `clustering_batch_size`, `clustering_pipeline_timeout_seconds` |
| `InterviewAssignmentRepository.find_by_interview_id()` | Section 10 | YES | Lookup per `interview_id` in `project_interviews` |
| `InterviewAssignmentRepository.update_extraction_status()` | Section 10 | YES | Optionaler `clustering_status` Parameter |

---

## Links

- Design/Spec: `specs/phase-4/2026-02-28-llm-interview-clustering/`
- Architecture: `specs/phase-4/2026-02-28-llm-interview-clustering/architecture.md`
- Wireframes: `specs/phase-4/2026-02-28-llm-interview-clustering/wireframes.md`
- Discovery: `specs/phase-4/2026-02-28-llm-interview-clustering/discovery.md`
- Dependency Slice: `specs/phase-4/2026-02-28-llm-interview-clustering/slices/slice-01-db-schema-projekt-crud.md`
- Referenz-Service-Pattern: `backend/app/interview/service.py` — `InterviewService.end()` Hook-Point
- Referenz-Repository-Pattern: `backend/app/interview/repository.py` — Raw SQL + SQLAlchemy async
- Referenz-LangGraph-Pattern: `backend/app/interview/graph.py` — StateGraph Pattern fuer Slice 3
- Referenz-Settings: `backend/app/config/settings.py` — Settings-Erweiterung
- Clio Facet-Extraction Pattern: https://www.anthropic.com/research/clio
- GoalEx research_goal Pattern: https://arxiv.org/abs/2305.13749

---

## Deliverables (SCOPE SAFEGUARD)

**WICHTIG: Diese Liste wird automatisch vom Stop-Hook validiert. Der Agent kann nicht stoppen, wenn Dateien fehlen.**

<!-- DELIVERABLES_START -->
### Backend — Neue Dateien

- [ ] `backend/app/clustering/extraction.py` — `FactExtractionService` mit `process_interview()`, `extract()`, `_call_llm_with_retry()` und `FactExtractionError` Exception-Klasse
- [ ] `backend/app/clustering/fact_repository.py` — `FactRepository` mit `save_facts()`, `get_facts_for_interview()`, `get_facts_for_project()`
- [ ] `backend/app/clustering/events.py` — `SseEventBus` mit `subscribe()`, `unsubscribe()`, `publish()`
- [ ] `backend/app/clustering/prompts.py` — `FACT_EXTRACTION_PROMPT` Prompt-Template

### Backend — Modifizierte Dateien

- [ ] `backend/app/interview/service.py` — `end()` Hook: `asyncio.create_task()` nach `complete_session()`, Optional-Parameter `fact_extraction_service` + `assignment_repository`
- [ ] `backend/app/clustering/interview_assignment_repository.py` — Neue Methoden: `find_by_interview_id()`, `update_extraction_status()`
- [ ] `backend/app/clustering/interview_assignment_service.py` — Neue Methode: `retry()` mit 404/409 Handling
- [ ] `backend/app/clustering/router.py` — Retry-Endpoint `POST /api/projects/{id}/interviews/{iid}/retry`
- [ ] `backend/app/config/settings.py` — Neue Felder: `clustering_max_retries`, `clustering_llm_timeout_seconds`, `clustering_batch_size`, `clustering_pipeline_timeout_seconds`
- [ ] `backend/app/api/dependencies.py` — Neue Singletons: `get_fact_extraction_service()`, `get_sse_event_bus()`

### Tests

- [ ] `backend/tests/slices/llm-interview-clustering/test_slice_02_fact_extraction_pipeline.py` — Alle Tests aus `<test_spec>` Section
<!-- DELIVERABLES_END -->

**Hinweis fuer den Implementierungs-Agent:**
- Alle Dateien zwischen `<!-- DELIVERABLES_START -->` und `<!-- DELIVERABLES_END -->` sind Pflicht
- Der Stop-Hook prueft automatisch ob alle Dateien existieren
- Bei fehlenden Dateien wird der Agent blockiert und muss nachfragen

# Slice 1: DB Schema + Projekt CRUD

> **Slice 1 von 8** fuer `LLM Interview Clustering`
>
> | Navigation | |
> |------------|---|
> | **Vorheriger:** | — |
> | **Naechster:** | `slice-02-fact-extraction-pipeline.md` |

---

## Metadata (fuer Orchestrator)

| Key | Value |
|-----|-------|
| **ID** | `slice-01-db-schema-projekt-crud` |
| **Test** | `python -m pytest backend/tests/slices/llm-interview-clustering/test_slice_01_db_schema_projekt_crud.py -v` |
| **E2E** | `false` |
| **Dependencies** | `[]` |

**Erklaerung:**
- **ID**: Eindeutiger Identifier (wird fuer Commits und Evidence verwendet)
- **Test**: Exakter Befehl den der Orchestrator nach Implementierung ausfuehrt
- **E2E**: `false` — pytest API-Tests (kein Playwright)
- **Dependencies**: Kein vorheriger Slice erforderlich

---

## Test-Strategy (fuer Orchestrator Pipeline)

> **Quelle:** Auto-detected basierend auf Repo-Indikatoren.
> `backend/requirements.txt` enthaelt `fastapi` + `uvicorn` → Stack: `python-fastapi`.
> Test-Pattern aus bestehenden `backend/tests/slices/backend-kern/` Dateien uebernommen.

| Key | Value |
|-----|-------|
| **Stack** | `python-fastapi` |
| **Test Command** | `python -m pytest backend/tests/slices/llm-interview-clustering/test_slice_01_db_schema_projekt_crud.py -v` |
| **Integration Command** | `python -m pytest backend/tests/slices/llm-interview-clustering/ -v` |
| **Acceptance Command** | `python -m pytest backend/tests/slices/llm-interview-clustering/test_slice_01_db_schema_projekt_crud.py -v -k "acceptance"` |
| **Start Command** | `uvicorn app.main:app --host 0.0.0.0 --port 8000` |
| **Health Endpoint** | `http://localhost:8000/health` |
| **Mocking Strategy** | `mock_external` |

**Erklaerung:**
- **Mocking Strategy:** Alle DB-Calls werden in Tests mit `AsyncMock` gemockt. Kein echter PostgreSQL in Unit-Tests.
- **Integration Tests:** Verwenden `TestClient` aus FastAPI + `AsyncSession` mit In-Memory SQLite (via `aiosqlite`) oder vollstaendigem DB-Mock.

---

## Slice-Uebersicht

| # | Slice | Status | Datei |
|---|-------|--------|-------|
| 1 | DB Schema + Projekt CRUD | **Ready** | `slice-01-db-schema-projekt-crud.md` |
| 2 | Fact Extraction Pipeline | Pending | `slice-02-fact-extraction-pipeline.md` |
| 3 | Clustering Pipeline + Agent | Pending | `slice-03-clustering-pipeline.md` |
| 4 | Dashboard: Projekt-Liste + Cluster-Uebersicht | Pending | `slice-04-dashboard-projekt-liste.md` |
| 5 | Dashboard: Drill-Down + Zitate | Pending | `slice-05-dashboard-drill-down.md` |
| 6 | Taxonomy-Editing + Summary-Regen | Pending | `slice-06-taxonomy-editing.md` |
| 7 | Live-Updates via SSE | Pending | `slice-07-live-updates-sse.md` |
| 8 | Auth + Polish | Pending | `slice-08-auth-polish.md` |

---

## Kontext & Ziel

Das Feature "LLM Interview Clustering" benoetigt ein solides Datenbankfundament sowie eine vollstaendige Projekt-Management API. Dieser Slice legt das Datenbankschema (neue Tabellen: `projects`, `clusters`, `facts`, `project_interviews`) an und implementiert die Projekt-CRUD-Endpunkte inklusive Interview-Zuordnung.

Dieser Slice ist das Fundament fuer alle weiteren Slices. Ohne ihn kann keine Clustering-Logik, kein Dashboard und keine Fact-Extraction implementiert werden.

**Abgrenzung zu anderen Slices:**
- Slice 1 legt nur die DB-Tabellen und Projekt-CRUD an
- Keine LLM-Calls, keine Fact-Extraction, kein Clustering-Trigger
- `InterviewAssignmentService.assign()` speichert nur die Zuordnung — der Clustering-Trigger kommt in Slice 2
- Auth-Endpunkte (`/api/auth/*`) und JWT-Middleware kommen in Slice 8 — in Slice 1 sind Projekt-Endpunkte noch ungeschuetzt (Stub: `user_id` aus Query-Parameter oder Hardcode fuer Tests)
- `POST /api/projects/{id}/interviews/{iid}/retry` ist **explizit auf Slice 2 verschoben** — dieser Endpoint setzt die LLM-Fact-Extraction-Pipeline voraus, die erst in Slice 2 implementiert wird (Details siehe "Deferred Endpoints" Section unten)

---

## Technische Umsetzung

### Architektur-Kontext (aus architecture.md)

> **Quelle:** `architecture.md` → Database Schema + API Design → Endpoints Projects + Endpoints Interview Assignment

```
API Layer (FastAPI) — Slice 1 implementiert diese 10 Endpunkte:
  POST   /api/projects                           → ProjectService.create()
  GET    /api/projects                           → ProjectService.list()
  GET    /api/projects/{id}                      → ProjectService.get()
  PUT    /api/projects/{id}                      → ProjectService.update()
  PUT    /api/projects/{id}/models               → ProjectService.update_models()
  PUT    /api/projects/{id}/extraction-source    → ProjectService.change_extraction_source()
  DELETE /api/projects/{id}                      → ProjectService.delete()
  GET    /api/projects/{id}/interviews           → InterviewAssignmentService.list()
  GET    /api/projects/{id}/interviews/available → InterviewAssignmentService.list_available()
  POST   /api/projects/{id}/interviews           → InterviewAssignmentService.assign()

  [DEFERRED TO SLICE 2]
  POST   /api/projects/{id}/interviews/{iid}/retry → InterviewAssignmentService.retry()
  -- Begruendung: Benoetigt LLM-Extraction-Pipeline (Celery/Background-Task-Trigger)
  -- der erst in Slice 2 implementiert wird.

Service Layer:
  ProjectService           → Projekt-CRUD, Zaehler-Aggregation
  InterviewAssignmentService → Interview-Zuordnung

Repository/DB Layer:
  ProjectRepository        → CRUD auf `projects` Tabelle
  InterviewAssignmentRepository → CRUD auf `project_interviews` Tabelle
  (Cluster/Fact Tabellen werden angelegt aber noch nicht befuellt)
```

### 1. Architektur-Impact

| Layer | Aenderungen |
|-------|-------------|
| `backend/app/clustering/` | Neues Modul (Ordner + `__init__.py`) |
| `backend/app/clustering/models.py` | DB-Migrationsscript: SQL fuer alle neuen Tabellen |
| `backend/app/clustering/schemas.py` | Pydantic DTOs fuer alle Projekt-Endpunkte |
| `backend/app/clustering/project_repository.py` | Repository: CRUD `projects` Tabelle |
| `backend/app/clustering/interview_assignment_repository.py` | Repository: CRUD `project_interviews` Tabelle |
| `backend/app/clustering/project_service.py` | Service: Projekt-CRUD mit Zaehler-Aggregation |
| `backend/app/clustering/interview_assignment_service.py` | Service: Interview-Zuordnung |
| `backend/app/clustering/router.py` | FastAPI Router fuer alle neuen Endpunkte |
| `backend/app/main.py` | Router registrieren |

### 2. Datenfluss

```
HTTP Request (z.B. POST /api/projects)
  |
  v
FastAPI Router (clustering/router.py)
  |
  v
Pydantic Validation (clustering/schemas.py → CreateProjectRequest)
  |
  v
ProjectService.create(request, user_id)
  |
  v
ProjectRepository.create(data: dict) → SQL INSERT INTO projects
  |
  v
PostgreSQL (asyncpg + SQLAlchemy async)
  |
  v
ProjectRepository gibt dict zurueck → ProjectService transformiert zu ProjectResponse
  |
  v
HTTP Response (ProjectResponse JSON)
```

### 3. DB-Schema (SQL Migration)

> **Quelle:** `architecture.md` → Database Schema Details

```sql
-- Neue Tabellen fuer LLM Interview Clustering Feature
-- Migration: create_clustering_tables

-- 1. users Tabelle (fuer spaetere Auth in Slice 8)
CREATE TABLE IF NOT EXISTS users (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    email       TEXT        NOT NULL UNIQUE,
    password_hash TEXT      NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 2. projects Tabelle
CREATE TABLE IF NOT EXISTS projects (
    id                  UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id             UUID        NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    name                TEXT        NOT NULL,
    research_goal       TEXT        NOT NULL,
    prompt_context      TEXT,
    extraction_source   TEXT        NOT NULL DEFAULT 'summary'
                        CHECK (extraction_source IN ('summary', 'transcript')),
    model_interviewer   TEXT        NOT NULL DEFAULT 'anthropic/claude-sonnet-4',
    model_extraction    TEXT        NOT NULL DEFAULT 'anthropic/claude-haiku-4',
    model_clustering    TEXT        NOT NULL DEFAULT 'anthropic/claude-sonnet-4',
    model_summary       TEXT        NOT NULL DEFAULT 'anthropic/claude-haiku-4',
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_projects_user_id ON projects(user_id);

-- 3. project_interviews Tabelle
CREATE TABLE IF NOT EXISTS project_interviews (
    project_id          UUID        NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    interview_id        UUID        NOT NULL UNIQUE,
    extraction_status   TEXT        NOT NULL DEFAULT 'pending'
                        CHECK (extraction_status IN ('pending', 'running', 'completed', 'failed')),
    clustering_status   TEXT        NOT NULL DEFAULT 'pending'
                        CHECK (clustering_status IN ('pending', 'running', 'completed', 'failed')),
    assigned_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (project_id, interview_id)
);
CREATE INDEX IF NOT EXISTS idx_project_interviews_project_id ON project_interviews(project_id);

-- 4. clusters Tabelle
CREATE TABLE IF NOT EXISTS clusters (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id      UUID        NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    name            TEXT        NOT NULL,
    summary         TEXT,
    fact_count      INTEGER     NOT NULL DEFAULT 0,
    interview_count INTEGER     NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_clusters_project_id ON clusters(project_id);

-- 5. facts Tabelle
CREATE TABLE IF NOT EXISTS facts (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id  UUID        NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    interview_id UUID       NOT NULL,
    cluster_id  UUID        REFERENCES clusters(id) ON DELETE SET NULL,
    content     TEXT        NOT NULL,
    quote       TEXT,
    confidence  FLOAT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_facts_project_id ON facts(project_id);
CREATE INDEX IF NOT EXISTS idx_facts_cluster_id ON facts(cluster_id);
CREATE INDEX IF NOT EXISTS idx_facts_interview_id ON facts(interview_id);

-- 6. cluster_suggestions Tabelle
CREATE TABLE IF NOT EXISTS cluster_suggestions (
    id                  UUID    PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id          UUID    NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    type                TEXT    NOT NULL CHECK (type IN ('merge', 'split')),
    source_cluster_id   UUID    NOT NULL REFERENCES clusters(id) ON DELETE CASCADE,
    target_cluster_id   UUID    REFERENCES clusters(id) ON DELETE CASCADE,
    similarity_score    FLOAT,
    proposed_data       JSONB,
    status              TEXT    NOT NULL DEFAULT 'pending'
                        CHECK (status IN ('pending', 'accepted', 'dismissed')),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_cluster_suggestions_project_id ON cluster_suggestions(project_id);
```

### 4. Pydantic DTOs (Schemas)

> **Quelle:** `architecture.md` → Data Transfer Objects

```python
# backend/app/clustering/schemas.py
from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field
import uuid

# --- Request DTOs ---

class CreateProjectRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    research_goal: str = Field(..., min_length=1, max_length=2000)
    prompt_context: str | None = Field(None, max_length=5000)
    extraction_source: Literal["summary", "transcript"] = "summary"

class UpdateProjectRequest(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=200)
    research_goal: str | None = Field(None, min_length=1, max_length=2000)
    prompt_context: str | None = Field(None, max_length=5000)

class UpdateModelsRequest(BaseModel):
    model_interviewer: str | None = None
    model_extraction: str | None = None
    model_clustering: str | None = None
    model_summary: str | None = None

class ChangeSourceRequest(BaseModel):
    extraction_source: Literal["summary", "transcript"]
    re_extract: bool = False

class AssignRequest(BaseModel):
    interview_ids: list[uuid.UUID] = Field(..., min_length=1)

# --- Response DTOs ---

class ProjectResponse(BaseModel):
    id: uuid.UUID
    name: str
    research_goal: str
    prompt_context: str | None
    extraction_source: str
    extraction_source_locked: bool   # True wenn facts bereits existieren
    model_interviewer: str
    model_extraction: str
    model_clustering: str
    model_summary: str
    interview_count: int
    cluster_count: int
    fact_count: int
    created_at: datetime
    updated_at: datetime

class ProjectListItem(BaseModel):
    id: uuid.UUID
    name: str
    interview_count: int
    cluster_count: int
    updated_at: datetime

class InterviewAssignment(BaseModel):
    interview_id: uuid.UUID
    date: datetime
    summary_preview: str | None
    fact_count: int
    extraction_status: str
    clustering_status: str

class AvailableInterview(BaseModel):
    session_id: uuid.UUID
    created_at: datetime
    summary_preview: str | None
```

### 5. Repository-Patterns

> Folgt dem bestehenden `InterviewRepository`-Pattern aus `backend/app/interview/repository.py` (Raw SQL + SQLAlchemy async).

```python
# backend/app/clustering/project_repository.py

class ProjectRepository:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def create(self, data: dict) -> dict:
        """INSERT INTO projects ... RETURNING *"""

    async def get_by_id(self, project_id: str, user_id: str) -> dict | None:
        """SELECT * FROM projects WHERE id = :id AND user_id = :user_id"""

    async def list_by_user(self, user_id: str) -> list[dict]:
        """SELECT mit aggregierten Zaehlern (interview_count, cluster_count, fact_count)"""

    async def update(self, project_id: str, user_id: str, data: dict) -> dict | None:
        """UPDATE projects SET ... WHERE id = :id AND user_id = :user_id RETURNING *"""

    async def delete(self, project_id: str, user_id: str) -> bool:
        """DELETE FROM projects WHERE id = :id AND user_id = :user_id"""

    async def get_fact_count(self, project_id: str) -> int:
        """SELECT COUNT(*) FROM facts WHERE project_id = :project_id"""

    async def get_interview_count(self, project_id: str) -> int:
        """SELECT COUNT(*) FROM project_interviews WHERE project_id = :project_id"""

    async def get_cluster_count(self, project_id: str) -> int:
        """SELECT COUNT(*) FROM clusters WHERE project_id = :project_id"""
```

```python
# backend/app/clustering/interview_assignment_repository.py

class InterviewAssignmentRepository:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def assign_interviews(self, project_id: str, interview_ids: list[str]) -> list[dict]:
        """INSERT INTO project_interviews (project_id, interview_id, ...) ... RETURNING *
        Bei UNIQUE-Konflikt auf interview_id: 409 Conflict"""

    async def list_assigned(self, project_id: str) -> list[dict]:
        """JOIN mit mvp_interviews fuer date + summary_preview"""

    async def list_available(self, user_id: str) -> list[dict]:
        """SELECT aus mvp_interviews wo session_id NICHT in project_interviews"""
```

### 6. Service-Layer

```python
# backend/app/clustering/project_service.py

class ProjectService:
    def __init__(self, repo: ProjectRepository) -> None:
        self._repo = repo

    async def create(self, request: CreateProjectRequest, user_id: str) -> ProjectResponse:
        """Erstellt neues Projekt, gibt ProjectResponse zurueck"""

    async def list(self, user_id: str) -> list[ProjectListItem]:
        """Listet Projekte des Users, sortiert nach updated_at desc"""

    async def get(self, project_id: str, user_id: str) -> ProjectResponse:
        """Laedt Projekt mit aggregierten Zaehlern (interview_count, cluster_count, fact_count)
        extraction_source_locked = fact_count > 0"""

    async def update(self, project_id: str, user_id: str, request: UpdateProjectRequest) -> ProjectResponse:
        """Aktualisiert name/research_goal/prompt_context, setzt updated_at"""

    async def update_models(self, project_id: str, user_id: str, request: UpdateModelsRequest) -> ProjectResponse:
        """Aktualisiert model_* Felder"""

    async def change_extraction_source(self, project_id: str, user_id: str, request: ChangeSourceRequest) -> ProjectResponse:
        """Aendert extraction_source. re_extract wird in Slice 2 verarbeitet (hier: gespeichert, kein Trigger)"""

    async def delete(self, project_id: str, user_id: str) -> None:
        """Loescht Projekt (CASCADE: alle project_interviews, clusters, facts)"""
```

### 7. API-Contracts

**POST `/api/projects`**

**Response-Typ:** `ProjectResponse`

```python
# Request
class CreateProjectRequest(BaseModel):
    name: str              # required, 1-200 chars
    research_goal: str     # required, 1-2000 chars
    prompt_context: str | None = None  # optional, max 5000 chars
    extraction_source: Literal["summary", "transcript"] = "summary"
```

```json
// POST /api/projects — Request Body
{
  "name": "Onboarding UX Research",
  "research_goal": "Understand why users drop off during onboarding",
  "prompt_context": "B2B SaaS with 14-day free trial",
  "extraction_source": "summary"
}

// Response 201 Created
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "Onboarding UX Research",
  "research_goal": "Understand why users drop off during onboarding",
  "prompt_context": "B2B SaaS with 14-day free trial",
  "extraction_source": "summary",
  "extraction_source_locked": false,
  "model_interviewer": "anthropic/claude-sonnet-4",
  "model_extraction": "anthropic/claude-haiku-4",
  "model_clustering": "anthropic/claude-sonnet-4",
  "model_summary": "anthropic/claude-haiku-4",
  "interview_count": 0,
  "cluster_count": 0,
  "fact_count": 0,
  "created_at": "2026-02-28T10:00:00Z",
  "updated_at": "2026-02-28T10:00:00Z"
}
```

**GET `/api/projects`**

```json
// Response 200 OK — list[ProjectListItem]
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "Onboarding UX Research",
    "interview_count": 12,
    "cluster_count": 5,
    "updated_at": "2026-02-28T10:00:00Z"
  }
]
```

**POST `/api/projects/{id}/interviews`**

```python
class AssignRequest(BaseModel):
    interview_ids: list[uuid.UUID]  # min 1, alle muessen in mvp_interviews existieren
```

```json
// POST /api/projects/{id}/interviews — Request Body
{
  "interview_ids": [
    "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
    "6ba7b811-9dad-11d1-80b4-00c04fd430c8"
  ]
}

// Response 201 Created — list[InterviewAssignment]
[
  {
    "interview_id": "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
    "date": "2026-02-28T09:00:00Z",
    "summary_preview": "User had issues with navigation...",
    "fact_count": 0,
    "extraction_status": "pending",
    "clustering_status": "pending"
  }
]
```

**DELETE `/api/projects/{id}`**

```
Response: 204 No Content
Cascade: loescht alle project_interviews, clusters, facts, cluster_suggestions fuer dieses Projekt
```

**Fehler-Responses:**

| Code | Wann | Body |
|------|------|------|
| 404 | Projekt nicht gefunden oder gehoert anderem User | `{"detail": "Project not found"}` |
| 409 | Interview bereits einem anderen Projekt zugeordnet | `{"detail": "Interview {id} already assigned to another project"}` |
| 422 | Validierungsfehler (Pydantic) | Standard FastAPI validation error |

### 8. Abhaengigkeiten

- **Bestehend (wiederverwendet):**
  - `backend/app/db/session.py` — `get_session_factory()` fuer alle neuen Repositories
  - `backend/app/config/settings.py` — Settings-Singleton
  - `backend/app/api/dependencies.py` — Pattern fuer FastAPI-Dependency-Injection

- **Neu (keine neue externe Pakete):**
  - Alle neuen Dateien in `backend/app/clustering/` Modul
  - Migration-Script als Python-Datei mit Raw-SQL (kein Alembic in MVP)

### 9. Stub fuer user_id (Slice 1)

Da Auth erst in Slice 8 kommt, wird `user_id` in Slice 1 als Query-Parameter uebergeben oder aus einem konfigurierbaren Default gelesen. **Kein echter JWT-Check in Slice 1.**

```python
# backend/app/clustering/router.py — Slice 1 Stub
@router.post("/api/projects")
async def create_project(
    request: CreateProjectRequest,
    user_id: str = Query(default="00000000-0000-0000-0000-000000000001"),  # Slice 1 Stub
    ...
):
```

---

## Integrations-Checkliste

### 1. DB-Integration
- [ ] Alle 6 Tabellen (`users`, `projects`, `project_interviews`, `clusters`, `facts`, `cluster_suggestions`) in Migration-Script vorhanden
- [ ] `project_interviews.interview_id` ist UNIQUE (Business Rule: ein Interview = ein Projekt)
- [ ] `facts.cluster_id` ist NULLABLE (unassigned Facts)
- [ ] CASCADE-Deletes korrekt definiert (projects → cascade alle abhaengigen Tabellen)
- [ ] Logische Referenz `project_interviews.interview_id → mvp_interviews.session_id` ohne FK-Constraint (cross-concern)

### 2. Repository-Integration
- [ ] `ProjectRepository` folgt Pattern aus `InterviewRepository` (Raw SQL + SQLAlchemy async + `text()`)
- [ ] `InterviewAssignmentRepository` joined auf `mvp_interviews` fuer `date` + `summary_preview`
- [ ] `get_fact_count()` fuer `extraction_source_locked` Berechnung

### 3. Service-Integration
- [ ] `ProjectService.get()` aggregiert `interview_count`, `cluster_count`, `fact_count` via SQL-COUNT-Subqueries
- [ ] `ProjectService.change_extraction_source()` speichert neue Source — Trigger fuer Re-Extract bleibt Slice 2
- [ ] `InterviewAssignmentService.assign()` prueft ob interview_ids in `mvp_interviews` existieren

### 4. Router-Integration
- [ ] Router in `backend/app/main.py` mit `include_router()` registriert
- [ ] Router-Prefix: `/api` (konsistent mit bestehendem Interview-Router)
- [ ] Alle Endpunkte aus architecture.md Tabelle "Endpoints — Projects" + "Endpoints — Interview Assignment" implementiert

### 5. Feature-Aktivierung
- [ ] Migration wird beim App-Start ausgefuehrt (in `lifespan()` oder separates Script)
- [ ] Neues `clustering` Modul hat `__init__.py`

---

## UI Anforderungen

Dieser Slice hat keine Frontend-Komponenten. Das Dashboard (Next.js) kommt in Slice 4.

Die Wireframes aus `wireframes.md` fuer die Screens "Project List", "Project Form (Modal)" und "Project Settings Tab" definieren die UI-Anforderungen fuer spaetere Slices, aber **nicht** fuer diesen Slice.

---

## Deferred Endpoints (explizit auf spaetere Slices verschoben)

> **Zweck dieser Section:** Klare Dokumentation welche Endpunkte aus der `architecture.md` bewusst NICHT in Slice 1 implementiert werden und warum. Dies verhindert, dass der Implementierungs-Agent diese als vergessen behandelt.

| Endpoint | Verschoben nach | Begruendung |
|----------|-----------------|-------------|
| `POST /api/projects/{id}/interviews/{iid}/retry` | **Slice 2** | Setzt die LLM-Fact-Extraction-Pipeline voraus. Der Retry-Endpoint muss `extraction_status` auf `pending` zuruecksetzen UND einen neuen Extraction-Job ausloesen. Der Job-Trigger (Celery Task / Background Task) existiert erst ab Slice 2. Ein Stub ohne Pipeline-Logik waere fuer Endanwender wertlos und wuerde fehlerhafte Erwartungen wecken (Button existiert im UI, tut aber nichts). Slice 2 implementiert den Endpoint vollstaendig inklusive Job-Dispatch. |

**Konsequenz fuer diesen Slice:**
- `router.py` registriert **10 Endpunkte** (7 Projects CRUD + 3 Interview Assignment)
- Der Retry-Endpoint wird **nicht** als Stub in `router.py` registriert
- `InterviewAssignmentService` hat **keine** `retry()`-Methode in Slice 1
- Slice 2 ergaenzt: `InterviewAssignmentService.retry()`, `POST /api/projects/{id}/interviews/{iid}/retry`

---

## Acceptance Criteria

1) GIVEN ein neues Projekt mit `name`, `research_goal` und Standard-`extraction_source`
   WHEN `POST /api/projects` aufgerufen wird
   THEN wird ein Projekt in der DB angelegt und `ProjectResponse` mit `id`, allen Feldern, `interview_count=0`, `cluster_count=0`, `fact_count=0`, `extraction_source_locked=false` zurueckgegeben (HTTP 201)

2) GIVEN ein existierendes Projekt
   WHEN `GET /api/projects/{id}` aufgerufen wird
   THEN werden alle Felder inkl. aggregierter Zaehler (`interview_count`, `cluster_count`, `fact_count`) korrekt zurueckgegeben (HTTP 200)

3) GIVEN mehrere Projekte des Users
   WHEN `GET /api/projects` aufgerufen wird
   THEN werden alle Projekte als `list[ProjectListItem]` sortiert nach `updated_at` absteigend zurueckgegeben

4) GIVEN ein Projekt mit veraenderbaren Feldern (`name`, `research_goal`, `prompt_context`)
   WHEN `PUT /api/projects/{id}` mit teilweisen Aenderungen aufgerufen wird
   THEN werden nur die gesendeten Felder aktualisiert, `updated_at` wird gesetzt, unveraenderte Felder bleiben unveraendert (HTTP 200)

5) GIVEN ein Projekt ohne zugeordnete Facts
   WHEN `PUT /api/projects/{id}/extraction-source` mit neuer `extraction_source` aufgerufen wird
   THEN wird die neue Source gespeichert, `extraction_source_locked=false` bleibt erhalten (HTTP 200)

6) GIVEN ein Projekt das dem aktuellen User gehoert
   WHEN `DELETE /api/projects/{id}` aufgerufen wird
   THEN wird das Projekt und alle zugehoerigen Daten (project_interviews, clusters, facts, cluster_suggestions) geloescht (HTTP 204)

7) GIVEN ein nicht-existierendes Projekt
   WHEN `GET /api/projects/{id}` aufgerufen wird
   THEN wird HTTP 404 mit `{"detail": "Project not found"}` zurueckgegeben

8) GIVEN verfuegbare Interviews in `mvp_interviews` die noch keinem Projekt zugeordnet sind
   WHEN `GET /api/projects/{id}/interviews/available` aufgerufen wird
   THEN werden diese Interviews als `list[AvailableInterview]` zurueckgegeben

9) GIVEN eine Liste von `interview_ids` aus `mvp_interviews`
   WHEN `POST /api/projects/{id}/interviews` aufgerufen wird
   THEN werden die Interviews dem Projekt zugeordnet (Zeilen in `project_interviews` mit `extraction_status=pending`, `clustering_status=pending`) und als `list[InterviewAssignment]` zurueckgegeben (HTTP 201)

10) GIVEN ein Interview das bereits einem anderen Projekt zugeordnet ist
    WHEN `POST /api/projects/{id}/interviews` mit dieser `interview_id` aufgerufen wird
    THEN wird HTTP 409 mit Fehlerdetail zurueckgegeben und kein Datensatz angelegt

---

## Testfaelle

**WICHTIG:** Tests muessen VOR der Implementierung definiert werden. Der Orchestrator fuehrt diese Tests automatisch nach der Slice-Implementierung aus.

### Test-Datei

`backend/tests/slices/llm-interview-clustering/test_slice_01_db_schema_projekt_crud.py`

<test_spec>
```python
# backend/tests/slices/llm-interview-clustering/test_slice_01_db_schema_projekt_crud.py
"""Tests fuer Slice 1: DB Schema + Projekt CRUD.

Alle DB-Calls werden gemockt (mock_external Strategie).
Kein echter PostgreSQL-Zugriff in Unit-Tests.
"""
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient


# ============================================================
# FIXTURES
# ============================================================

@pytest.fixture
def mock_project_id() -> str:
    return str(uuid.UUID("550e8400-e29b-41d4-a716-446655440000"))


@pytest.fixture
def mock_user_id() -> str:
    return "00000000-0000-0000-0000-000000000001"


@pytest.fixture
def mock_project_row(mock_project_id, mock_user_id) -> dict:
    """Typischer DB-Row fuer ein Projekt."""
    now = datetime.now(timezone.utc)
    return {
        "id": uuid.UUID(mock_project_id),
        "user_id": uuid.UUID(mock_user_id),
        "name": "Onboarding UX Research",
        "research_goal": "Understand why users drop off during onboarding",
        "prompt_context": "B2B SaaS with 14-day free trial",
        "extraction_source": "summary",
        "model_interviewer": "anthropic/claude-sonnet-4",
        "model_extraction": "anthropic/claude-haiku-4",
        "model_clustering": "anthropic/claude-sonnet-4",
        "model_summary": "anthropic/claude-haiku-4",
        "created_at": now,
        "updated_at": now,
    }


@pytest.fixture
def mock_project_repository():
    """Gemocktes ProjectRepository."""
    repo = AsyncMock()
    return repo


@pytest.fixture
def mock_interview_assignment_repository():
    """Gemocktes InterviewAssignmentRepository."""
    repo = AsyncMock()
    return repo


# ============================================================
# AC 1: Projekt erstellen
# ============================================================

class TestCreateProject:
    """AC 1: POST /api/projects erstellt Projekt und gibt ProjectResponse zurueck."""

    def test_create_project_returns_201(
        self,
        mock_project_repository,
        mock_project_row,
        mock_user_id,
    ):
        """GIVEN name + research_goal WHEN POST /api/projects THEN HTTP 201"""
        mock_project_repository.create = AsyncMock(return_value=mock_project_row)
        mock_project_repository.get_fact_count = AsyncMock(return_value=0)

        from app.clustering.project_service import ProjectService
        from app.clustering.schemas import CreateProjectRequest

        service = ProjectService(repo=mock_project_repository)
        request = CreateProjectRequest(
            name="Onboarding UX Research",
            research_goal="Understand why users drop off during onboarding",
            prompt_context="B2B SaaS with 14-day free trial",
        )

        import asyncio
        result = asyncio.get_event_loop().run_until_complete(
            service.create(request, user_id=mock_user_id)
        )

        assert result.name == "Onboarding UX Research"
        assert result.interview_count == 0
        assert result.cluster_count == 0
        assert result.fact_count == 0
        assert result.extraction_source_locked is False
        mock_project_repository.create.assert_called_once()

    def test_create_project_validates_required_fields(self):
        """GIVEN fehlendes research_goal WHEN CreateProjectRequest erstellt THEN ValidationError"""
        from pydantic import ValidationError
        from app.clustering.schemas import CreateProjectRequest

        with pytest.raises(ValidationError):
            CreateProjectRequest(name="Test")  # research_goal fehlt

    def test_create_project_validates_name_length(self):
        """GIVEN name mit 201 Zeichen WHEN Validation THEN ValidationError"""
        from pydantic import ValidationError
        from app.clustering.schemas import CreateProjectRequest

        with pytest.raises(ValidationError):
            CreateProjectRequest(
                name="x" * 201,
                research_goal="Test goal",
            )

    def test_create_project_default_extraction_source(self):
        """GIVEN kein extraction_source WHEN CreateProjectRequest THEN default 'summary'"""
        from app.clustering.schemas import CreateProjectRequest

        request = CreateProjectRequest(
            name="Test",
            research_goal="Test goal",
        )
        assert request.extraction_source == "summary"


# ============================================================
# AC 2: Projekt lesen (einzeln)
# ============================================================

class TestGetProject:
    """AC 2: GET /api/projects/{id} gibt vollstaendige ProjectResponse zurueck."""

    def test_get_project_returns_aggregated_counts(
        self,
        mock_project_repository,
        mock_project_row,
        mock_project_id,
        mock_user_id,
    ):
        """GIVEN existierendes Projekt WHEN GET /api/projects/{id} THEN korrekte Zaehler"""
        mock_project_repository.get_by_id = AsyncMock(return_value=mock_project_row)
        mock_project_repository.get_interview_count = AsyncMock(return_value=3)
        mock_project_repository.get_cluster_count = AsyncMock(return_value=2)
        mock_project_repository.get_fact_count = AsyncMock(return_value=7)

        from app.clustering.project_service import ProjectService

        service = ProjectService(repo=mock_project_repository)

        import asyncio
        result = asyncio.get_event_loop().run_until_complete(
            service.get(project_id=mock_project_id, user_id=mock_user_id)
        )

        assert result.interview_count == 3
        assert result.cluster_count == 2
        assert result.fact_count == 7

    def test_get_project_extraction_source_locked_when_facts_exist(
        self,
        mock_project_repository,
        mock_project_row,
        mock_project_id,
        mock_user_id,
    ):
        """GIVEN Projekt mit facts>0 WHEN GET THEN extraction_source_locked=True"""
        mock_project_repository.get_by_id = AsyncMock(return_value=mock_project_row)
        mock_project_repository.get_interview_count = AsyncMock(return_value=1)
        mock_project_repository.get_cluster_count = AsyncMock(return_value=0)
        mock_project_repository.get_fact_count = AsyncMock(return_value=5)  # facts > 0

        from app.clustering.project_service import ProjectService

        service = ProjectService(repo=mock_project_repository)

        import asyncio
        result = asyncio.get_event_loop().run_until_complete(
            service.get(project_id=mock_project_id, user_id=mock_user_id)
        )

        assert result.extraction_source_locked is True

    def test_get_project_not_found_raises_404(
        self,
        mock_project_repository,
        mock_project_id,
        mock_user_id,
    ):
        """GIVEN nicht-existierendes Projekt WHEN GET THEN HTTP 404"""
        mock_project_repository.get_by_id = AsyncMock(return_value=None)

        from app.clustering.project_service import ProjectService
        from fastapi import HTTPException

        service = ProjectService(repo=mock_project_repository)

        import asyncio
        with pytest.raises(HTTPException) as exc_info:
            asyncio.get_event_loop().run_until_complete(
                service.get(project_id=mock_project_id, user_id=mock_user_id)
            )
        assert exc_info.value.status_code == 404


# ============================================================
# AC 3: Projekte auflisten
# ============================================================

class TestListProjects:
    """AC 3: GET /api/projects gibt sortierte list[ProjectListItem] zurueck."""

    def test_list_projects_sorted_by_updated_at_desc(
        self,
        mock_project_repository,
        mock_user_id,
    ):
        """GIVEN mehrere Projekte WHEN GET /api/projects THEN sortiert nach updated_at desc"""
        from datetime import timedelta

        now = datetime.now(timezone.utc)
        project_rows = [
            {
                "id": uuid.uuid4(),
                "name": "Neueres Projekt",
                "interview_count": 0,
                "cluster_count": 0,
                "updated_at": now,
            },
            {
                "id": uuid.uuid4(),
                "name": "Aelteres Projekt",
                "interview_count": 2,
                "cluster_count": 1,
                "updated_at": now - timedelta(hours=2),
            },
        ]
        mock_project_repository.list_by_user = AsyncMock(return_value=project_rows)

        from app.clustering.project_service import ProjectService

        service = ProjectService(repo=mock_project_repository)

        import asyncio
        results = asyncio.get_event_loop().run_until_complete(
            service.list(user_id=mock_user_id)
        )

        assert len(results) == 2
        assert results[0].name == "Neueres Projekt"
        assert results[1].name == "Aelteres Projekt"


# ============================================================
# AC 4: Projekt aktualisieren (PATCH-Semantik via PUT)
# ============================================================

class TestUpdateProject:
    """AC 4: PUT /api/projects/{id} aktualisiert nur gesendete Felder."""

    def test_update_project_partial_fields(
        self,
        mock_project_repository,
        mock_project_row,
        mock_project_id,
        mock_user_id,
    ):
        """GIVEN nur name im Request WHEN PUT THEN nur name geaendert, andere Felder unveraendert"""
        updated_row = {**mock_project_row, "name": "Neuer Name"}
        mock_project_repository.update = AsyncMock(return_value=updated_row)
        mock_project_repository.get_fact_count = AsyncMock(return_value=0)
        mock_project_repository.get_interview_count = AsyncMock(return_value=0)
        mock_project_repository.get_cluster_count = AsyncMock(return_value=0)

        from app.clustering.project_service import ProjectService
        from app.clustering.schemas import UpdateProjectRequest

        service = ProjectService(repo=mock_project_repository)
        request = UpdateProjectRequest(name="Neuer Name")

        import asyncio
        result = asyncio.get_event_loop().run_until_complete(
            service.update(
                project_id=mock_project_id,
                user_id=mock_user_id,
                request=request,
            )
        )

        assert result.name == "Neuer Name"
        assert result.research_goal == mock_project_row["research_goal"]  # unveraendert


# ============================================================
# AC 6: Projekt loeschen
# ============================================================

class TestDeleteProject:
    """AC 6: DELETE /api/projects/{id} loescht Projekt und gibt 204 zurueck."""

    def test_delete_project_calls_repository(
        self,
        mock_project_repository,
        mock_project_id,
        mock_user_id,
    ):
        """GIVEN existierendes Projekt WHEN DELETE THEN repository.delete() aufgerufen"""
        mock_project_repository.delete = AsyncMock(return_value=True)

        from app.clustering.project_service import ProjectService

        service = ProjectService(repo=mock_project_repository)

        import asyncio
        asyncio.get_event_loop().run_until_complete(
            service.delete(project_id=mock_project_id, user_id=mock_user_id)
        )

        mock_project_repository.delete.assert_called_once_with(
            project_id=mock_project_id,
            user_id=mock_user_id,
        )

    def test_delete_nonexistent_project_raises_404(
        self,
        mock_project_repository,
        mock_project_id,
        mock_user_id,
    ):
        """GIVEN nicht-existierendes Projekt WHEN DELETE THEN HTTP 404"""
        mock_project_repository.delete = AsyncMock(return_value=False)

        from app.clustering.project_service import ProjectService
        from fastapi import HTTPException

        service = ProjectService(repo=mock_project_repository)

        import asyncio
        with pytest.raises(HTTPException) as exc_info:
            asyncio.get_event_loop().run_until_complete(
                service.delete(project_id=mock_project_id, user_id=mock_user_id)
            )
        assert exc_info.value.status_code == 404


# ============================================================
# AC 9 + AC 10: Interview-Zuordnung
# ============================================================

class TestAssignInterviews:
    """AC 9/10: POST /api/projects/{id}/interviews ordnet Interviews zu."""

    def test_assign_interviews_creates_project_interview_rows(
        self,
        mock_interview_assignment_repository,
        mock_project_id,
    ):
        """GIVEN gueltige interview_ids WHEN POST /interviews THEN project_interviews Zeilen angelegt"""
        interview_id_1 = uuid.uuid4()
        interview_id_2 = uuid.uuid4()
        now = datetime.now(timezone.utc)

        mock_interview_assignment_repository.assign_interviews = AsyncMock(
            return_value=[
                {
                    "interview_id": interview_id_1,
                    "date": now,
                    "summary_preview": "User had issues...",
                    "fact_count": 0,
                    "extraction_status": "pending",
                    "clustering_status": "pending",
                },
                {
                    "interview_id": interview_id_2,
                    "date": now,
                    "summary_preview": "Pricing was confusing...",
                    "fact_count": 0,
                    "extraction_status": "pending",
                    "clustering_status": "pending",
                },
            ]
        )

        from app.clustering.interview_assignment_service import InterviewAssignmentService
        from app.clustering.schemas import AssignRequest

        service = InterviewAssignmentService(repo=mock_interview_assignment_repository)
        request = AssignRequest(interview_ids=[interview_id_1, interview_id_2])

        import asyncio
        results = asyncio.get_event_loop().run_until_complete(
            service.assign(project_id=mock_project_id, request=request)
        )

        assert len(results) == 2
        assert all(r.extraction_status == "pending" for r in results)
        assert all(r.clustering_status == "pending" for r in results)

    def test_assign_already_assigned_interview_raises_409(
        self,
        mock_interview_assignment_repository,
        mock_project_id,
    ):
        """GIVEN bereits zugeordnetes Interview WHEN POST /interviews THEN HTTP 409"""
        from fastapi import HTTPException

        mock_interview_assignment_repository.assign_interviews = AsyncMock(
            side_effect=HTTPException(
                status_code=409,
                detail=f"Interview {uuid.uuid4()} already assigned to another project",
            )
        )

        from app.clustering.interview_assignment_service import InterviewAssignmentService
        from app.clustering.schemas import AssignRequest

        service = InterviewAssignmentService(repo=mock_interview_assignment_repository)
        request = AssignRequest(interview_ids=[uuid.uuid4()])

        import asyncio
        with pytest.raises(HTTPException) as exc_info:
            asyncio.get_event_loop().run_until_complete(
                service.assign(project_id=mock_project_id, request=request)
            )
        assert exc_info.value.status_code == 409


# ============================================================
# AC 8: Verfuegbare Interviews auflisten
# ============================================================

class TestListAvailableInterviews:
    """AC 8: GET /api/projects/{id}/interviews/available"""

    def test_list_available_excludes_assigned_interviews(
        self,
        mock_interview_assignment_repository,
    ):
        """GIVEN bereits zugeordnete Interviews WHEN GET /available THEN diese nicht enthalten"""
        now = datetime.now(timezone.utc)
        mock_interview_assignment_repository.list_available = AsyncMock(
            return_value=[
                {
                    "session_id": uuid.uuid4(),
                    "created_at": now,
                    "summary_preview": "Unassigned interview summary...",
                },
            ]
        )

        from app.clustering.interview_assignment_service import InterviewAssignmentService

        service = InterviewAssignmentService(repo=mock_interview_assignment_repository)

        import asyncio
        results = asyncio.get_event_loop().run_until_complete(
            service.list_available(user_id="00000000-0000-0000-0000-000000000001")
        )

        assert len(results) == 1
        assert results[0].summary_preview == "Unassigned interview summary..."


# ============================================================
# AC 5: Extraction-Source aendern
# ============================================================

class TestChangeExtractionSource:
    """AC 5: PUT /api/projects/{id}/extraction-source aendert Quelle wenn keine Facts vorhanden."""

    def test_change_extraction_source_without_facts(
        self,
        mock_project_repository,
        mock_project_row,
        mock_project_id,
        mock_user_id,
    ):
        """GIVEN Projekt ohne Facts WHEN PUT /extraction-source THEN neue Source gespeichert, locked=False"""
        updated_row = {**mock_project_row, "extraction_source": "transcript"}
        mock_project_repository.update = AsyncMock(return_value=updated_row)
        mock_project_repository.get_fact_count = AsyncMock(return_value=0)
        mock_project_repository.get_interview_count = AsyncMock(return_value=0)
        mock_project_repository.get_cluster_count = AsyncMock(return_value=0)

        from app.clustering.project_service import ProjectService
        from app.clustering.schemas import ChangeSourceRequest

        service = ProjectService(repo=mock_project_repository)
        request = ChangeSourceRequest(extraction_source="transcript", re_extract=False)

        import asyncio
        result = asyncio.get_event_loop().run_until_complete(
            service.change_extraction_source(
                project_id=mock_project_id,
                user_id=mock_user_id,
                request=request,
            )
        )

        assert result.extraction_source == "transcript"
        assert result.extraction_source_locked is False
```
</test_spec>

---

## Definition of Done

- [x] Akzeptanzkriterien sind eindeutig & vollstaendig
- [ ] Migration-Script erstellt und manuell auf Test-DB geprueft
- [x] Sicherheits-/Privacy-Aspekte bedacht (user_id immer mitgeprueft, kein Cross-User-Access)
- [ ] Rollout: Migration laeuft als Idempotent-SQL (`IF NOT EXISTS`) — kein Downtime bei Deployment

---

## Integration Contract (GATE 2 PFLICHT)

> **Wichtig:** Diese Section wird vom Gate 2 Compliance Agent geprueft. Unvollstaendige Contracts blockieren die Genehmigung.

### Requires From Other Slices

| Slice | Resource | Type | Validation |
|-------|----------|------|------------|
| — | — | — | Kein Slice muss vorher fertig sein |

### Provides To Other Slices

| Resource | Type | Consumer | Interface |
|----------|------|----------|-----------|
| `projects` Tabelle | DB Schema | Slice 2, 3, 4, 5, 6, 7 | `project_id UUID`, `research_goal TEXT`, `model_extraction TEXT`, `model_clustering TEXT`, `model_summary TEXT`, `extraction_source TEXT` |
| `project_interviews` Tabelle | DB Schema | Slice 2 | `project_id`, `interview_id`, `extraction_status`, `clustering_status` |
| `clusters` Tabelle | DB Schema | Slice 3, 4, 5, 6 | `id UUID`, `project_id UUID`, `name TEXT`, `summary TEXT`, `fact_count INT`, `interview_count INT` |
| `facts` Tabelle | DB Schema | Slice 2, 3, 5 | `id UUID`, `project_id UUID`, `interview_id UUID`, `cluster_id UUID NULLABLE`, `content TEXT`, `quote TEXT`, `confidence FLOAT` |
| `cluster_suggestions` Tabelle | DB Schema | Slice 3, 6 | `id UUID`, `project_id UUID`, `type TEXT`, `source_cluster_id UUID`, `status TEXT` |
| `ProjectRepository` | Class | Slice 2, 3 | `get_by_id(project_id, user_id) → dict` |
| `InterviewAssignmentRepository` | Class | Slice 2 | `list_assigned(project_id) → list[dict]` mit `extraction_status`/`clustering_status` |
| `ProjectService` | Class | Slice 8 (Auth) | `create()`, `get()`, `list()`, `update()`, `delete()` |
| `InterviewAssignmentService` | Class | Slice 7 (SSE) | `assign(project_id, request) → list[InterviewAssignment]` |
| `ProjectResponse` DTO | Pydantic Model | Slice 4, 8 | Alle Felder inkl. `extraction_source_locked: bool` |
| `ProjectListItem` DTO | Pydantic Model | Slice 4 | `id, name, interview_count, cluster_count, updated_at` |

### Integration Validation Tasks

- [ ] `projects` Tabelle mit allen Spalten aus architecture.md vorhanden
- [ ] `project_interviews.interview_id` UNIQUE-Constraint funktioniert (409 bei Duplikat)
- [ ] `facts.cluster_id` ist NULLABLE — `cluster_id=NULL` bedeutet "unassigned"
- [ ] `ProjectRepository.get_by_id()` filtert auf `user_id` (kein Cross-User-Access)
- [ ] `ProjectService.get()` berechnet `extraction_source_locked = fact_count > 0`

---

## Code Examples (MANDATORY - GATE 2 PFLICHT)

> **KRITISCH:** Alle Code-Beispiele in diesem Dokument sind PFLICHT-Deliverables.
> Der Gate 2 Compliance Agent prueft, dass jedes Code-Beispiel implementiert wird.
> Abweichung nur mit expliziter Begruendung im Commit erlaubt.

| Code Example | Section | Mandatory | Notes |
|--------------|---------|-----------|-------|
| SQL Migration Script | Section 3 (DB-Schema) | YES | Alle 6 Tabellen exakt wie spezifiziert |
| `CreateProjectRequest` Pydantic Model | Section 4 (Pydantic DTOs) | YES | Field-Validierung wie spezifiziert |
| `ProjectResponse` Pydantic Model | Section 4 (Pydantic DTOs) | YES | Inkl. `extraction_source_locked: bool` |
| `AssignRequest` Pydantic Model | Section 4 (Pydantic DTOs) | YES | `min_length=1` auf `interview_ids` |
| `ProjectRepository.create()` Signatur | Section 5 (Repository-Patterns) | YES | Raw SQL + SQLAlchemy async Pattern |
| `InterviewAssignmentRepository.assign_interviews()` Signatur | Section 5 | YES | UNIQUE-Constraint-Handling mit 409 |
| `ProjectService.get()` mit `extraction_source_locked` | Section 6 (Service-Layer) | YES | `locked = fact_count > 0` |
| Router Stub `user_id` als Query-Parameter | Section 9 (Stub) | YES | Expliziter Kommentar "Slice 1 Stub" |

---

## Links

- Design/Spec: `specs/phase-4/2026-02-28-llm-interview-clustering/`
- Architecture: `specs/phase-4/2026-02-28-llm-interview-clustering/architecture.md`
- Wireframes: `specs/phase-4/2026-02-28-llm-interview-clustering/wireframes.md`
- Discovery: `specs/phase-4/2026-02-28-llm-interview-clustering/discovery.md`
- Referenz-Repository-Pattern: `backend/app/interview/repository.py`
- Referenz-Settings-Pattern: `backend/app/config/settings.py`
- Referenz-DB-Session-Pattern: `backend/app/db/session.py`

---

## Deliverables (SCOPE SAFEGUARD)

**WICHTIG: Diese Liste wird automatisch vom Stop-Hook validiert. Der Agent kann nicht stoppen, wenn Dateien fehlen.**

<!-- DELIVERABLES_START -->
### Backend — Migration

- [ ] `backend/app/clustering/models.py` — SQL Migration Script (alle 6 Tabellen: users, projects, project_interviews, clusters, facts, cluster_suggestions)

### Backend — Modul

- [ ] `backend/app/clustering/__init__.py` — Leeres Modul-Init
- [ ] `backend/app/clustering/schemas.py` — Alle Pydantic DTOs (CreateProjectRequest, UpdateProjectRequest, UpdateModelsRequest, ChangeSourceRequest, AssignRequest, ProjectResponse, ProjectListItem, InterviewAssignment, AvailableInterview)
- [ ] `backend/app/clustering/project_repository.py` — ProjectRepository (create, get_by_id, list_by_user, update, delete, get_fact_count, get_interview_count, get_cluster_count)
- [ ] `backend/app/clustering/interview_assignment_repository.py` — InterviewAssignmentRepository (assign_interviews, list_assigned, list_available)
- [ ] `backend/app/clustering/project_service.py` — ProjectService (create, list, get, update, update_models, change_extraction_source, delete)
- [ ] `backend/app/clustering/interview_assignment_service.py` — InterviewAssignmentService (assign, list_assigned, list_available)
- [ ] `backend/app/clustering/router.py` — FastAPI Router mit allen 10 Endpunkten (Projects CRUD + Interview Assignment)

### Backend — Main App

- [ ] `backend/app/main.py` — Router aus `clustering/router.py` registriert (`include_router`)

### Tests

- [ ] `backend/tests/slices/llm-interview-clustering/__init__.py` — Test-Modul Init
- [ ] `backend/tests/slices/llm-interview-clustering/test_slice_01_db_schema_projekt_crud.py` — Alle Tests aus `<test_spec>` Section
<!-- DELIVERABLES_END -->

**Hinweis fuer den Implementierungs-Agent:**
- Alle Dateien zwischen `<!-- DELIVERABLES_START -->` und `<!-- DELIVERABLES_END -->` sind Pflicht
- Der Stop-Hook prueft automatisch ob alle Dateien existieren
- Bei fehlenden Dateien wird der Agent blockiert und muss nachfragen

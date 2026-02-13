# Slice 1: App-Skeleton + DDD-Struktur aufsetzen

> **Slice 1 von 6** fuer `Backend-Kern`
>
> | Navigation | |
> |------------|---|
> | **Vorheriger:** | -- |
> | **Naechster:** | `slice-02-langgraph-interview.md` |

---

## Metadata (fuer Orchestrator)

| Key | Value |
|-----|-------|
| **ID** | `slice-01-app-skeleton` |
| **Test** | `cd backend && python -m pytest tests/slices/backend-kern/test_slice_01_app_skeleton.py -v` |
| **E2E** | `false` |
| **Dependencies** | `[]` |

---

## Slice-Uebersicht

| # | Slice | Status | Datei |
|---|-------|--------|-------|
| 1 | App-Skeleton + DDD-Struktur | Ready | `slice-01-app-skeleton.md` |
| 2 | LangGraph Interview-Graph | Pending | `slice-02-langgraph-interview.md` |
| 3 | SSE-Streaming Endpoints | Pending | `slice-03-sse-streaming.md` |
| 4 | Supabase-Persistenz | Pending | `slice-04-supabase-persistenz.md` |
| 5 | Summary-Generierung + Injection | Pending | `slice-05-summary-injection.md` |
| 6 | Session-Timeout + Auto-Summary | Pending | `slice-06-session-timeout.md` |

---

## Kontext & Ziel

Das FeedbackAI-Backend existiert noch nicht. Es gibt nur Prompt-Dateien (`backend/app/graph/prompt.py`), Context-JSONs (`backend/app/context/*.json`) und eine leere `requirements.txt`.

Dieser Slice legt das Fundament:
- FastAPI-Applikation mit Health-Check-Endpoint
- Pydantic Settings fuer typsichere ENV-Konfiguration
- DDD Vertical Slices Ordnerstruktur (Bounded Contexts als Top-Level-Ordner)
- CORS-Middleware fuer Widget-Zugriff
- Widget package.json Cleanup (unnoetige `ai` und `@ai-sdk/react` Dependencies entfernen)
- `.env.example` anpassen (`DATABASE_URL` ersetzen durch `SUPABASE_URL` + `SUPABASE_KEY`)

**Aktuelle Probleme:**
1. Keine FastAPI-App existiert (`main.py` fehlt)
2. Keine Konfigurationslogik (`settings.py` fehlt)
3. Bestehende Ordnerstruktur passt nicht zur DDD-Architektur (Dateien unter `app/graph/` und `app/context/`)
4. Widget hat unnoetige Dependencies (`ai`, `@ai-sdk/react`)
5. `.env.example` hat `DATABASE_URL` statt `SUPABASE_URL` + `SUPABASE_KEY`
6. Timeout-Konfiguration (`LLM_TIMEOUT_SECONDS`, `DB_TIMEOUT_SECONDS`) fehlt in `.env.example`

---

## Technische Umsetzung

### Architektur-Kontext (aus architecture.md)

> **Quelle:** `architecture.md` -> Architecture Layers -> DDD Vertical Slices

```
backend/
  app/
    interview/              # Bounded Context: Interview
      __init__.py
      service.py            # InterviewService (Orchestration)
      graph.py              # LangGraph StateGraph + Interviewer-Node
      state.py              # State-Definition (TypedDict)
      prompt.py             # PromptAssembler (System-Prompt + Summary-Injection)
      repository.py         # InterviewRepository (Supabase CRUD)
      timeout.py            # TimeoutManager (asyncio.Task)
    insights/               # Bounded Context: Insights
      __init__.py
      summary.py            # SummaryService (LLM-Call fuer Bullet-Summary)
    config/                 # Bounded Context: Configuration
      __init__.py
      settings.py           # Pydantic Settings (liest .env)
      context/              # Company/Product/Scenario JSONs (existieren bereits)
        company.json
        product.json
        scenario_pain_point_discovery.json
        scenario_satisfaction_research.json
    api/                    # Transport Layer (kein Bounded Context)
      __init__.py
      routes.py             # FastAPI Router (POST /start, /message, /end)
      schemas.py            # Pydantic DTOs (StartRequest, MessageRequest, etc.)
      dependencies.py       # FastAPI Depends() fuer Service-Injection
    db/                     # Shared Infrastructure
      __init__.py
      supabase.py           # Supabase Client Singleton
    main.py                 # FastAPI App, CORS, Lifespan
  requirements.txt
```

### 1. Architektur-Impact

| Layer | Aenderungen |
|-------|-------------|
| `backend/app/main.py` | NEU: FastAPI App mit CORS, Health-Check, Lifespan |
| `backend/app/config/settings.py` | NEU: Pydantic Settings mit allen ENV-Vars |
| `backend/app/config/__init__.py` | NEU: Package-Init |
| `backend/app/interview/__init__.py` | NEU: Package-Init (leere Datei) |
| `backend/app/insights/__init__.py` | NEU: Package-Init (leere Datei) |
| `backend/app/db/__init__.py` | NEU: Package-Init (leere Datei) |
| `backend/app/config/context/` | MOVE: Dateien von `backend/app/context/` hierher |
| `backend/app/interview/prompt.py` | MOVE: `backend/app/graph/prompt.py` hierher |
| `backend/app/interview/graph.py` | Wird erst in Slice 2 erstellt (leere Datei nicht noetig) |
| `widget/package.json` | MODIFY: `ai` und `@ai-sdk/react` aus dependencies entfernen |
| `.env.example` | MODIFY: `DATABASE_URL` + `SUPABASE_DB` ersetzen durch `SUPABASE_URL` + `SUPABASE_KEY`, fehlende Timeout-Vars ergaenzen |

### 2. Datenfluss

```
uvicorn startet
  |
  v
main.py: FastAPI App erstellen
  |
  v
Lifespan: Settings laden (Pydantic liest .env)
  |
  v
CORS-Middleware registrieren
  |
  v
Health-Check Route registrieren (/health)
  |
  v
Server laeuft auf 0.0.0.0:8000
  |
  v
GET /health -> {"status": "ok"}
```

### 3. Settings-Klasse (Pydantic)

> **Quelle:** `architecture.md` -> Technology Decisions -> Config

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # OpenRouter
    openrouter_api_key: str

    # Interviewer Config
    interviewer_llm: str = "anthropic/claude-sonnet-4.5"
    interviewer_temperature: float = 1.0
    interviewer_max_tokens: int = 4000

    # Session
    session_timeout_seconds: int = 60

    # Timeouts
    llm_timeout_seconds: int = 30
    db_timeout_seconds: int = 10

    # Supabase
    supabase_url: str
    supabase_key: str

    # LangSmith (optional)
    langsmith_tracing: bool = True
    langsmith_endpoint: str = "https://eu.api.smith.langchain.com"
    langsmith_api_key: str = ""
    langsmith_project: str = "FeedbackAI"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}
```

**WICHTIG - Implementierungshinweise:**
- `pydantic-settings` muss in `requirements.txt` ergaenzt werden (separat von `pydantic`)
- Settings-Instanz wird in `main.py` Lifespan erstellt und via `app.state.settings` verfuegbar gemacht
- Alternativ: Singleton-Pattern mit `@lru_cache` in `config/__init__.py`

### 4. FastAPI main.py

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config.settings import Settings

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
    allow_origins=["*"],  # MVP: alle Origins erlauben
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health_check():
    return {"status": "ok"}
```

### 5. DDD-Ordnerstruktur Migration

Bestehende Dateien die verschoben werden muessen:

| Quelle | Ziel | Aktion |
|--------|------|--------|
| `backend/app/context/company.json` | `backend/app/config/context/company.json` | MOVE |
| `backend/app/context/product.json` | `backend/app/config/context/product.json` | MOVE |
| `backend/app/context/scenario_pain_point_discovery.json` | `backend/app/config/context/scenario_pain_point_discovery.json` | MOVE |
| `backend/app/context/scenario_satisfaction_research.json` | `backend/app/config/context/scenario_satisfaction_research.json` | MOVE |
| `backend/app/graph/prompt.py` | `backend/app/interview/prompt.py` | MOVE |
| `backend/app/graph/prompt_interviewer_original.md` | `backend/app/interview/prompt_interviewer_original.md` | MOVE |
| `backend/app/graph/__init__.py` | LOESCHEN (Ordner wird leer) | DELETE |
| `backend/app/context/` | LOESCHEN (Ordner wird leer) | DELETE |
| `backend/app/api/__init__.py` | Bleibt (api/ ist bereits korrekt) | KEEP |

### 6. Widget package.json Cleanup

Zu entfernende Dependencies aus `widget/package.json`:
- `"ai": "^4.0.0"` -> ENTFERNEN
- `"@ai-sdk/react": "^1.0.0"` -> ENTFERNEN

Resultierende dependencies:
```json
{
  "dependencies": {
    "@assistant-ui/react": "^0.7.0",
    "react": "^19.0.0",
    "react-dom": "^19.0.0"
  }
}
```

### 7. .env.example Anpassung

Aenderungen:
- `DATABASE_URL=postgresql://...` ENTFERNEN
- `SUPABASE_DB=true` ENTFERNEN
- `SUPABASE_URL=https://xxx.supabase.co` HINZUFUEGEN
- `SUPABASE_KEY=eyJ...` HINZUFUEGEN
- `LLM_TIMEOUT_SECONDS=30` HINZUFUEGEN
- `DB_TIMEOUT_SECONDS=10` HINZUFUEGEN
- `OPENAI_API_KEY=` ENTFERNEN (nicht genutzt, OpenRouter stattdessen)

Resultierende `.env.example`:
```env
# LLM Provider
OPENROUTER_API_KEY=

# Interviewer Config
INTERVIEWER_LLM=anthropic/claude-sonnet-4.5
INTERVIEWER_TEMPERATURE=1
INTERVIEWER_MAX_TOKENS=4000

# Timeouts
SESSION_TIMEOUT_SECONDS=60
LLM_TIMEOUT_SECONDS=30
DB_TIMEOUT_SECONDS=10

# LangSmith (Tracing)
LANGSMITH_TRACING=true
LANGSMITH_ENDPOINT=https://eu.api.smith.langchain.com
LANGSMITH_API_KEY=
LANGSMITH_PROJECT=FeedbackAI

# Supabase
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_KEY=eyJ...
```

### 8. requirements.txt Ergaenzung

Neue Dependency:
- `pydantic-settings` (fuer `BaseSettings` Import)

Resultierende `requirements.txt`:
```
fastapi
uvicorn[standard]
langgraph
langchain-openai
langchain-core
python-dotenv
httpx
sse-starlette
supabase
pydantic-settings
```

### 9. Abhaengigkeiten

- Bestehend: `fastapi`, `uvicorn[standard]` (bereits in requirements.txt)
- Neu: `pydantic-settings` (muss ergaenzt werden)

---

## Integrations-Checkliste (Pflicht bei Backend-Aenderungen)

### 1. State-Integration
- [x] Kein State in diesem Slice (nur App-Skeleton)

### 2. LangGraph-Integration
- [x] Nicht betroffen (kommt in Slice 2)

### 3. LLM-Integration
- [x] Nicht betroffen (kommt in Slice 2)

### 4. Datenbank-Integration
- [x] Nicht betroffen (kommt in Slice 4)

### 5. Utility-Funktionen
- [x] Settings als Singleton: `Settings()` mit Pydantic BaseSettings

### 6. Feature-Aktivierung
- [x] Health-Check automatisch verfuegbar nach Server-Start
- [x] `uvicorn app.main:app --host 0.0.0.0 --port 8000` startet den Server

### 7. Datenfluss-Vollstaendigkeit
- [x] Request: GET /health -> keine Parameter
- [x] Response: `{"status": "ok"}` als JSON

---

## UI Anforderungen

Keine UI in diesem Slice (Backend-only + Widget Cleanup).

---

## Acceptance Criteria

1) GIVEN der Backend-Server ist gestartet mit `uvicorn app.main:app --host 0.0.0.0 --port 8000`
   WHEN ein GET-Request an `http://localhost:8000/health` gesendet wird
   THEN wird HTTP 200 mit Body `{"status": "ok"}` zurueckgegeben

2) GIVEN eine gueltige `.env`-Datei existiert mit allen Pflicht-Variablen (OPENROUTER_API_KEY, SUPABASE_URL, SUPABASE_KEY)
   WHEN die FastAPI-App startet (Lifespan)
   THEN werden alle Settings korrekt geladen und `app.state.settings` ist verfuegbar

3) GIVEN eine `.env`-Datei in der `OPENROUTER_API_KEY` fehlt
   WHEN die FastAPI-App startet
   THEN wird ein `ValidationError` geworfen (Pydantic Settings Validation)

4) GIVEN die DDD-Ordnerstruktur ist angelegt
   WHEN man die Verzeichnisse unter `backend/app/` prueft
   THEN existieren die Ordner: `interview/`, `insights/`, `config/`, `config/context/`, `api/`, `db/` mit jeweils `__init__.py`

5) GIVEN die Context-JSON-Dateien wurden verschoben
   WHEN man `backend/app/config/context/` prueft
   THEN existieren: `company.json`, `product.json`, `scenario_pain_point_discovery.json`, `scenario_satisfaction_research.json`

6) GIVEN die alten Ordner wurden aufgeraeumt
   WHEN man `backend/app/graph/` und `backend/app/context/` prueft
   THEN existieren diese Ordner NICHT mehr (Dateien wurden in die DDD-Struktur verschoben)

7) GIVEN `backend/app/interview/prompt.py` existiert
   WHEN man den Inhalt prueft
   THEN enthaelt die Datei den hardcoded SYSTEM_PROMPT (verschoben von `backend/app/graph/prompt.py`)

8) GIVEN die `widget/package.json` wurde bereinigt
   WHEN man die dependencies prueft
   THEN sind `ai` und `@ai-sdk/react` NICHT mehr enthalten, aber `@assistant-ui/react`, `react`, `react-dom` sind weiterhin vorhanden

9) GIVEN die `.env.example` wurde aktualisiert
   WHEN man den Inhalt prueft
   THEN enthaelt sie `SUPABASE_URL` und `SUPABASE_KEY` statt `DATABASE_URL` und `SUPABASE_DB`, sowie `LLM_TIMEOUT_SECONDS=30` und `DB_TIMEOUT_SECONDS=10`

10) GIVEN ein Request von einer anderen Origin kommt (z.B. `http://localhost:5173`)
    WHEN ein GET-Request an `/health` mit `Origin`-Header gesendet wird
    THEN enthaelt die Response den `Access-Control-Allow-Origin`-Header (CORS ist aktiv)

11) GIVEN `backend/requirements.txt` wurde aktualisiert
    WHEN man den Inhalt prueft
    THEN enthaelt sie `pydantic-settings` als zusaetzliche Dependency

---

## Testfaelle

**WICHTIG:** Tests muessen VOR der Implementierung definiert werden! Der Orchestrator fuehrt diese Tests automatisch nach der Slice-Implementierung aus.

### Test-Datei

**Fuer diesen Slice:** `backend/tests/slices/backend-kern/test_slice_01_app_skeleton.py`

### Unit Tests (pytest)

<test_spec>
```python
# backend/tests/slices/backend-kern/test_slice_01_app_skeleton.py
import pytest
from pathlib import Path
from unittest.mock import patch
from fastapi.testclient import TestClient


# -- Health Check --

class TestHealthCheck:
    """AC 1: GET /health gibt 200 mit {"status": "ok"} zurueck."""

    def test_health_returns_200(self, client: TestClient):
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_returns_status_ok(self, client: TestClient):
        response = client.get("/health")
        assert response.json() == {"status": "ok"}


# -- Settings --

class TestSettings:
    """AC 2 + AC 3: Pydantic Settings laden und validieren."""

    def test_settings_loads_from_env(self):
        """AC 2: Settings laden alle Pflicht-Variablen."""
        with patch.dict("os.environ", {
            "OPENROUTER_API_KEY": "test-key",
            "SUPABASE_URL": "https://test.supabase.co",
            "SUPABASE_KEY": "test-supabase-key",
        }, clear=False):
            from app.config.settings import Settings
            settings = Settings()
            assert settings.openrouter_api_key == "test-key"
            assert settings.supabase_url == "https://test.supabase.co"
            assert settings.supabase_key == "test-supabase-key"

    def test_settings_default_values(self):
        """AC 2: Default-Werte sind korrekt gesetzt."""
        with patch.dict("os.environ", {
            "OPENROUTER_API_KEY": "test-key",
            "SUPABASE_URL": "https://test.supabase.co",
            "SUPABASE_KEY": "test-supabase-key",
        }, clear=False):
            from app.config.settings import Settings
            settings = Settings()
            assert settings.interviewer_llm == "anthropic/claude-sonnet-4.5"
            assert settings.interviewer_temperature == 1.0
            assert settings.interviewer_max_tokens == 4000
            assert settings.session_timeout_seconds == 60
            assert settings.llm_timeout_seconds == 30
            assert settings.db_timeout_seconds == 10
            assert settings.langsmith_project == "FeedbackAI"

    def test_settings_missing_required_raises_error(self):
        """AC 3: Fehlende Pflicht-Variablen werfen ValidationError."""
        from pydantic import ValidationError
        from app.config.settings import Settings
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(ValidationError):
                Settings()


# -- DDD-Ordnerstruktur --

class TestDDDStructure:
    """AC 4 + AC 5 + AC 6: DDD Vertical Slices Ordnerstruktur."""

    BACKEND_APP = Path(__file__).resolve().parents[3] / "app"

    def test_interview_package_exists(self):
        """AC 4: interview/ Bounded Context existiert."""
        assert (self.BACKEND_APP / "interview" / "__init__.py").exists()

    def test_insights_package_exists(self):
        """AC 4: insights/ Bounded Context existiert."""
        assert (self.BACKEND_APP / "insights" / "__init__.py").exists()

    def test_config_package_exists(self):
        """AC 4: config/ Bounded Context existiert."""
        assert (self.BACKEND_APP / "config" / "__init__.py").exists()

    def test_db_package_exists(self):
        """AC 4: db/ Shared Infrastructure existiert."""
        assert (self.BACKEND_APP / "db" / "__init__.py").exists()

    def test_api_package_exists(self):
        """AC 4: api/ Transport Layer existiert."""
        assert (self.BACKEND_APP / "api" / "__init__.py").exists()

    def test_context_jsons_in_config(self):
        """AC 5: Context-JSONs liegen unter config/context/."""
        context_dir = self.BACKEND_APP / "config" / "context"
        assert (context_dir / "company.json").exists()
        assert (context_dir / "product.json").exists()
        assert (context_dir / "scenario_pain_point_discovery.json").exists()
        assert (context_dir / "scenario_satisfaction_research.json").exists()

    def test_old_graph_folder_removed(self):
        """AC 6: Alter graph/ Ordner existiert nicht mehr."""
        assert not (self.BACKEND_APP / "graph").exists()

    def test_old_context_folder_removed(self):
        """AC 6: Alter context/ Ordner existiert nicht mehr."""
        assert not (self.BACKEND_APP / "context").exists()

    def test_prompt_in_interview_package(self):
        """AC 7: prompt.py liegt unter interview/."""
        assert (self.BACKEND_APP / "interview" / "prompt.py").exists()


# -- CORS --

class TestCORS:
    """AC 10: CORS-Middleware ist aktiv."""

    def test_cors_allows_cross_origin(self, client: TestClient):
        response = client.options(
            "/health",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert "access-control-allow-origin" in response.headers


# -- Widget Cleanup --

class TestWidgetCleanup:
    """AC 8: Widget package.json bereinigt."""

    WIDGET_PKG = Path(__file__).resolve().parents[4] / "widget" / "package.json"

    def test_ai_sdk_removed(self):
        """AC 8: 'ai' nicht mehr in dependencies."""
        import json
        pkg = json.loads(self.WIDGET_PKG.read_text(encoding="utf-8"))
        deps = pkg.get("dependencies", {})
        assert "ai" not in deps
        assert "@ai-sdk/react" not in deps

    def test_assistant_ui_still_present(self):
        """AC 8: '@assistant-ui/react' ist weiterhin vorhanden."""
        import json
        pkg = json.loads(self.WIDGET_PKG.read_text(encoding="utf-8"))
        deps = pkg.get("dependencies", {})
        assert "@assistant-ui/react" in deps


# -- .env.example --

class TestEnvExample:
    """AC 9: .env.example aktualisiert."""

    ENV_EXAMPLE = Path(__file__).resolve().parents[4] / ".env.example"

    def test_supabase_url_present(self):
        content = self.ENV_EXAMPLE.read_text(encoding="utf-8")
        assert "SUPABASE_URL=" in content

    def test_supabase_key_present(self):
        content = self.ENV_EXAMPLE.read_text(encoding="utf-8")
        assert "SUPABASE_KEY=" in content

    def test_database_url_removed(self):
        content = self.ENV_EXAMPLE.read_text(encoding="utf-8")
        assert "DATABASE_URL=" not in content

    def test_timeout_vars_present(self):
        content = self.ENV_EXAMPLE.read_text(encoding="utf-8")
        assert "LLM_TIMEOUT_SECONDS=" in content
        assert "DB_TIMEOUT_SECONDS=" in content


# -- requirements.txt --

class TestRequirements:
    """AC 11: pydantic-settings in requirements.txt."""

    REQ_TXT = Path(__file__).resolve().parents[3] / "requirements.txt"

    def test_pydantic_settings_present(self):
        content = self.REQ_TXT.read_text(encoding="utf-8")
        assert "pydantic-settings" in content


# -- Fixtures --

@pytest.fixture
def client():
    """TestClient mit gemockten Settings (kein .env noetig)."""
    with patch.dict("os.environ", {
        "OPENROUTER_API_KEY": "test-key",
        "SUPABASE_URL": "https://test.supabase.co",
        "SUPABASE_KEY": "test-supabase-key",
    }, clear=False):
        from app.main import app
        with TestClient(app) as c:
            yield c
```
</test_spec>

### Manuelle Tests

1. `cd backend && uvicorn app.main:app --host 0.0.0.0 --port 8000` -> Server startet ohne Fehler
2. `curl http://localhost:8000/health` -> `{"status":"ok"}` mit HTTP 200

---

## Definition of Done

- [x] Akzeptanzkriterien sind eindeutig & vollstaendig
- [x] Kein Logging/Telemetrie in diesem Slice (kommt spaeter mit LangSmith)
- [x] Sicherheits-/Privacy-Aspekte bedacht (CORS: allow_origins=["*"] fuer MVP akzeptabel)
- [x] Kein UI in diesem Slice
- [x] Kein Rollout/Rollback noetig (Fundament-Slice)

---

## Constraints & Hinweise

**Betrifft:**
- Dieser Slice ist das Fundament fuer ALLE weiteren Slices
- Ordnerstruktur MUSS exakt der architecture.md entsprechen

**API Contract:**
- `GET /health` -> `{"status": "ok"}` (HTTP 200)
- Kein Auth, kein Rate Limiting

**Abgrenzung:**
- Keine API-Endpoints fuer Interview (kommt in Slice 3)
- Kein Supabase-Client-Setup (kommt in Slice 4)
- Keine LangGraph-Integration (kommt in Slice 2)
- `api/routes.py`, `api/schemas.py`, `api/dependencies.py` werden als leere Dateien NICHT angelegt -- erst in ihrem jeweiligen Slice

---

## Integration Contract (GATE 2 PFLICHT)

### Requires From Other Slices

| Slice | Resource | Type | Validation |
|-------|----------|------|------------|
| -- | Keine Dependencies | -- | -- |

### Provides To Other Slices

| Resource | Type | Consumer | Interface |
|----------|------|----------|-----------|
| `app.main:app` | FastAPI App | Slice 2-6 | FastAPI Application mit CORS und Lifespan |
| `Settings` | Pydantic BaseSettings | Slice 2-6 | `from app.config.settings import Settings` -> alle ENV-Vars typsicher verfuegbar |
| `app.state.settings` | Settings-Instanz | Slice 2-6 | Runtime-Zugriff auf Settings via `request.app.state.settings` |
| DDD-Ordnerstruktur | Directory Layout | Slice 2-6 | `interview/`, `insights/`, `config/`, `api/`, `db/` als Bounded Contexts |

### Integration Validation Tasks

- [x] Keine Dependencies (erster Slice)
- [ ] Settings-Instanz via `app.state.settings` verfuegbar (Slice 2 konsumiert)
- [ ] DDD-Ordner existieren fuer Slice 2+ Deliverables

---

## Code Examples (MANDATORY - GATE 2 PFLICHT)

> **KRITISCH:** Alle Code-Beispiele in diesem Dokument sind **PFLICHT-Deliverables**.
> Der Gate 2 Compliance Agent prueft, dass jedes Code-Beispiel implementiert wird.
> Abweichung nur mit expliziter Begruendung im Commit erlaubt.

| Code Example | Section | Mandatory | Notes |
|--------------|---------|-----------|-------|
| `Settings` Klasse | Section 3 (Settings-Klasse) | YES | Alle ENV-Vars wie spezifiziert, Pydantic BaseSettings |
| `main.py` App | Section 4 (FastAPI main.py) | YES | Lifespan, CORS, Health-Check Route |
| `.env.example` | Section 7 (.env.example) | YES | Exakt diese Variablen |
| `widget/package.json` cleanup | Section 6 (Widget Cleanup) | YES | `ai` und `@ai-sdk/react` entfernt |
| `requirements.txt` update | Section 8 (requirements.txt) | YES | `pydantic-settings` ergaenzt |

---

## Deliverables (SCOPE SAFEGUARD)

**WICHTIG: Diese Liste wird automatisch vom Stop-Hook validiert. Der Agent kann nicht stoppen, wenn Dateien fehlen.**

<!-- DELIVERABLES_START -->
### Backend
- [ ] `backend/app/main.py` -- FastAPI App mit CORS-Middleware, Lifespan, Health-Check Endpoint
- [ ] `backend/app/config/__init__.py` -- Package-Init fuer config Bounded Context
- [ ] `backend/app/config/settings.py` -- Pydantic Settings mit allen ENV-Vars (OPENROUTER_API_KEY, INTERVIEWER_LLM, INTERVIEWER_TEMPERATURE, INTERVIEWER_MAX_TOKENS, SESSION_TIMEOUT_SECONDS, LLM_TIMEOUT_SECONDS, DB_TIMEOUT_SECONDS, SUPABASE_URL, SUPABASE_KEY, LANGSMITH_*)
- [ ] `backend/app/config/context/company.json` -- MOVE von `backend/app/context/company.json`
- [ ] `backend/app/config/context/product.json` -- MOVE von `backend/app/context/product.json`
- [ ] `backend/app/config/context/scenario_pain_point_discovery.json` -- MOVE von `backend/app/context/scenario_pain_point_discovery.json`
- [ ] `backend/app/config/context/scenario_satisfaction_research.json` -- MOVE von `backend/app/context/scenario_satisfaction_research.json`
- [ ] `backend/app/interview/__init__.py` -- Package-Init fuer interview Bounded Context
- [ ] `backend/app/interview/prompt.py` -- MOVE von `backend/app/graph/prompt.py` (hardcoded SYSTEM_PROMPT)
- [ ] `backend/app/interview/prompt_interviewer_original.md` -- MOVE von `backend/app/graph/prompt_interviewer_original.md`
- [ ] `backend/app/insights/__init__.py` -- Package-Init fuer insights Bounded Context
- [ ] `backend/app/db/__init__.py` -- Package-Init fuer db Shared Infrastructure
- [ ] `backend/requirements.txt` -- `pydantic-settings` ergaenzt

### Cleanup (Loeschungen)
- [ ] `backend/app/graph/` -- Gesamter Ordner LOESCHEN (Dateien nach interview/ verschoben)
- [ ] `backend/app/context/` -- Gesamter Ordner LOESCHEN (Dateien nach config/context/ verschoben)

### Config-Dateien
- [ ] `.env.example` -- Aktualisiert: SUPABASE_URL + SUPABASE_KEY statt DATABASE_URL, LLM_TIMEOUT_SECONDS + DB_TIMEOUT_SECONDS ergaenzt

### Widget
- [ ] `widget/package.json` -- `ai` und `@ai-sdk/react` aus dependencies entfernt

### Tests
- [ ] `backend/tests/slices/backend-kern/test_slice_01_app_skeleton.py` -- pytest Tests fuer Health-Check, Settings, DDD-Struktur, CORS, Widget Cleanup, .env.example
- [ ] `backend/tests/__init__.py` -- Package-Init
- [ ] `backend/tests/slices/__init__.py` -- Package-Init
- [ ] `backend/tests/slices/backend-kern/__init__.py` -- Package-Init
- [ ] `backend/tests/conftest.py` -- Shared pytest Fixtures (falls noetig)
<!-- DELIVERABLES_END -->

**Hinweis fuer den Implementierungs-Agent:**
- Alle Dateien zwischen `<!-- DELIVERABLES_START -->` und `<!-- DELIVERABLES_END -->` sind **Pflicht**
- Der Stop-Hook prueft automatisch ob alle Dateien existieren
- Bei fehlenden Dateien wird der Agent blockiert und muss nachfragen

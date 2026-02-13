# Feature: Phase 1 -- Backend-Kern

**Epic:** FeedbackAI MVP
**Status:** Ready
**Discovery:** `discovery.md` (same folder)
**Derived from:** Discovery constraints, NFRs, and risks

---

## Problem & Solution

**Problem:**
- Kein funktionierender Interview-Loop existiert -- nur Prompt und Context-Dateien
- Ohne Backend kann das Feedback-System nicht getestet oder validiert werden
- Interview-Qualitaet (Prompt, Gespraechsfuehrung) ist unbekannt

**Solution:**
- Kompletter Backend-Kern: FastAPI + LangGraph Interview-Graph mit SSE-Streaming
- Interview per curl durchspielbar, Summary wird als Fact-Liste generiert
- Supabase-Persistenz fuer Interviews und Summaries
- Session-Kontext: Summaries vorheriger Sessions werden in den Prompt injiziert

**Business Value:**
- Frueheste Validierung der Interview-Qualitaet
- Grundlage fuer alle weiteren Phasen (Widget, Dashboard, Voice)
- Architektonisches Fundament mit DDD-Domaenen fuer Skalierbarkeit

---

## Scope & Boundaries

| In Scope |
|----------|
| FastAPI App-Skeleton (main.py, config.py, CORS, Health-Check) |
| LangGraph StateGraph: Interviewer-Node mit System-Prompt + History |
| SSE-Streaming (eigenes simples Format, kompatibel mit assistant-ui LocalRuntime) |
| API Endpoints: POST /api/interview/start, POST /api/interview/message (SSE), POST /api/interview/end |
| MemorySaver fuer In-Session Conversation-Persistenz |
| Summary-Generierung am Interview-Ende (separater LLM-Call, Bullet-Liste) |
| Auto-Summary bei Session-Timeout (SESSION_TIMEOUT_SECONDS aus .env) |
| Summary-Injection: Letzte 3 Summaries des Users in System-Prompt |
| Supabase: interviews-Tabelle (Transkript, Summary, Status) |
| Anonyme User-Identifikation (anonymous_id vom Client, localStorage) |
| OpenRouter als LLM-Provider (Claude Sonnet 4.5) |
| Widget package.json bereinigen: `ai` und `@ai-sdk/react` entfernen |
| DDD Vertical Slices Architektur |
| LangSmith-Tracing (bereits in .env vorkonfiguriert) |

| Out of Scope |
|--------------|
| Widget-UI (Phase 2) |
| Fact-Extraction (eigene Phase, spaeter) |
| Automatisches Interview-Ende / Message-Limit (rein user-gesteuert) |
| Multi-Context / dynamische Prompts (Phase 6) |
| Consent-Check im Backend (Website-Datenschutz regelt das) |
| Deployment (Phase 5) |
| Email-Einladungen (Phase 7) |

---

## API Design

### Overview

| Aspect | Specification |
|--------|---------------|
| Style | REST + SSE-Streaming |
| Authentication | Keine (anonymous_id vom Client) |
| Rate Limiting | Keines in MVP |
| Base Path | `/api/interview` |
| Content-Type (Request) | `application/json` |
| Content-Type (SSE Response) | `text/event-stream` |

### Endpoints

| Method | Path | Request DTO | Response | Auth | Business Logic |
|--------|------|-------------|----------|------|----------------|
| GET | `/health` | -- | `{ status: "ok" }` | -- | Health-Check |
| POST | `/api/interview/start` | `StartRequest` | SSE: Opening-Frage gestreamt + metadata mit session_id | -- | Session erstellen, letzte 3 Summaries laden, System-Prompt assemblieren, Opening-Frage streamen |
| POST | `/api/interview/message` | `MessageRequest` | SSE: Interviewer-Antwort gestreamt | -- | Nachricht zur History, LangGraph aufrufen, Antwort streamen |
| POST | `/api/interview/end` | `EndRequest` | `EndResponse` (JSON) | -- | Summary generieren, Transkript + Summary in Supabase speichern |

### Data Transfer Objects (DTOs)

| DTO | Fields | Validation | Notes |
|-----|--------|------------|-------|
| `StartRequest` | `anonymous_id: str` | Nicht leer, max 255 Zeichen | Client-generierte ID aus localStorage |
| `MessageRequest` | `session_id: str, message: str` | session_id: UUID-Format. message: nicht leer, max 10000 Zeichen | session_id aus /start Response |
| `EndRequest` | `session_id: str` | session_id: UUID-Format | -- |
| `EndResponse` | `summary: str, message_count: int` | -- | Summary als Bullet-Liste, Anzahl User-Nachrichten |
| `ErrorResponse` | `error: str, detail: str | null` | -- | Einheitliches Fehler-Format |

### SSE Event Format

| Event Type | Payload | Wann |
|------------|---------|------|
| `text-delta` | `{ "type": "text-delta", "content": "Chunk..." }` | Jeder Token/Chunk vom LLM |
| `text-done` | `{ "type": "text-done" }` | LLM-Antwort komplett |
| `metadata` | `{ "type": "metadata", "session_id": "..." }` | Nach text-done bei /start |
| `error` | `{ "type": "error", "message": "..." }` | Bei LLM-Fehlern waehrend Streaming |

**Wire Format:**
```
data: {"type": "text-delta", "content": "Wie"}\n\n
data: {"type": "text-delta", "content": " geht"}\n\n
data: {"type": "text-done"}\n\n
data: {"type": "metadata", "session_id": "uuid-here"}\n\n
```

---

## Database Schema

### Entities

| Table | Purpose | Key Fields |
|-------|---------|------------|
| `interviews` | Speichert komplette Interviews mit Transkript und Summary | id, anonymous_id, session_id, status, transcript, summary |

### Schema Details

| Table | Column | Type | Constraints | Index | Notes |
|-------|--------|------|-------------|-------|-------|
| `interviews` | `id` | UUID | PK, DEFAULT gen_random_uuid() | Yes | Auto-generated |
| `interviews` | `anonymous_id` | TEXT | NOT NULL | Yes | Client-generiert, fuer Summary-Lookup |
| `interviews` | `session_id` | UUID | NOT NULL, UNIQUE | Yes | LangGraph thread_id |
| `interviews` | `status` | TEXT | NOT NULL, CHECK (status IN ('active', 'completed', 'completed_timeout')) | No | Session-Status |
| `interviews` | `transcript` | JSONB | NULL | No | Null waehrend active, Array von {role, content} bei completed |
| `interviews` | `summary` | TEXT | NULL | No | Null waehrend active, Bullet-Liste bei completed |
| `interviews` | `message_count` | INTEGER | NOT NULL, DEFAULT 0 | No | Anzahl User-Nachrichten |
| `interviews` | `created_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | No | Session-Start |
| `interviews` | `updated_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | No | Letzte Aktivitaet |
| `interviews` | `completed_at` | TIMESTAMPTZ | NULL | No | Null waehrend active |

### Relationships

Keine Relationships in Phase 1 (Single Table).

### SQL Migration

```sql
CREATE TABLE interviews (
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

CREATE INDEX idx_interviews_anonymous_id ON interviews(anonymous_id);
CREATE INDEX idx_interviews_session_id ON interviews(session_id);
CREATE INDEX idx_interviews_status ON interviews(status);
```

---

## Server Logic

### Services & Processing

| Service | Responsibility | Input | Output | Side Effects |
|---------|----------------|-------|--------|--------------|
| `InterviewService` | Orchestriert Interview-Lifecycle (Start, Message, End) | Request DTOs | SSE-Stream oder EndResponse | DB writes via Repository, LangGraph-Aufrufe |
| `InterviewGraph` | LangGraph StateGraph mit Interviewer-Node | Messages + Config | AsyncGenerator von Token-Chunks | MemorySaver Checkpoint writes. LLM-Call mit LLM_TIMEOUT_SECONDS Timeout. |
| `PromptAssembler` | Baut System-Prompt aus statischem Prompt + Summary-Injection | anonymous_id, previous_summaries | Vollstaendiger System-Prompt String | Keine |
| `SummaryService` | Generiert Bullet-Summary aus Transkript | Conversation Messages | Summary String (Bullet-Liste) | LLM-Call via OpenRouter |
| `TimeoutManager` | Ueberwacht Session-Inaktivitaet, triggert Auto-Summary | session_id, timeout_seconds | -- | Triggers SummaryService + DB write bei Timeout |
| `InterviewRepository` | CRUD fuer interviews-Tabelle | Session-Daten | DB-Rows | Supabase writes/reads. DB-Calls mit DB_TIMEOUT_SECONDS Timeout. |

### Business Logic Flow

```
POST /start:
  Route(StartRequest) → InterviewService.start()
    → InterviewRepository.create_session(anonymous_id)
    → InterviewRepository.get_recent_summaries(anonymous_id, limit=3)
    → PromptAssembler.build(base_prompt, summaries)
    → InterviewGraph.invoke(system_prompt, config={thread_id})
    → SSE Stream (text-delta chunks + metadata mit session_id)
    → TimeoutManager.register(session_id)

POST /message:
  Route(MessageRequest) → InterviewService.message()
    → InterviewRepository.validate_session(session_id, status="active")
    → InterviewGraph.invoke(user_message, config={thread_id})
    → SSE Stream (text-delta chunks)
    → InterviewRepository.increment_message_count(session_id)
    → TimeoutManager.reset(session_id)

POST /end:
  Route(EndRequest) → InterviewService.end()
    → InterviewRepository.validate_session(session_id, status="active")
    → TimeoutManager.cancel(session_id)
    → InterviewGraph.get_history(config={thread_id})
    → SummaryService.generate(history)
    → InterviewRepository.complete_session(session_id, transcript, summary)
    → EndResponse(summary, message_count)

Timeout:
  TimeoutManager.on_timeout(session_id)
    → InterviewGraph.get_history(config={thread_id})
    → SummaryService.generate(history)
    → InterviewRepository.complete_session(session_id, transcript, summary, status="completed_timeout")
```

### Validation Rules

| Field | Rule | Error Code | Error Message |
|-------|------|------------|---------------|
| `anonymous_id` | Nicht leer, max 255 Zeichen | 400 | "anonymous_id is required" |
| `session_id` | UUID-Format | 400 | "Invalid session_id format" |
| `session_id` | Muss existieren | 404 | "Session not found" |
| `session_id` | Status muss "active" sein | 409 | "Session already completed" |
| `message` | Nicht leer | 400 | "Message cannot be empty" |
| `message` | Max 10000 Zeichen | 400 | "Message too long" |

---

## Security

### Authentication & Authorization

| Area | Mechanism | Notes |
|------|-----------|-------|
| API Auth | Keine | MVP: anonymous_id ist einzige Identifikation |
| Resource Access | anonymous_id-basiert | Client kann nur eigene Sessions ansprechen (via session_id) |
| Session Isolation | session_id als UUID | Nicht erratbar, jede Session einzigartig |

### Data Protection

| Data Type | Protection | Notes |
|-----------|------------|-------|
| Transkript-Inhalte | Keine Verschluesselung in MVP | Supabase encrypted at rest |
| anonymous_id | Keine PII | Client-generierte UUID, kein Personenbezug |
| API Keys (OpenRouter, Supabase) | .env, nicht im Code | .gitignore regelt Ausschluss |

### Input Validation & Sanitization

| Input | Validation | Sanitization |
|-------|------------|--------------|
| `anonymous_id` | String, nicht leer, max 255 | Strip whitespace |
| `session_id` | UUID-Format Regex | -- |
| `message` | String, nicht leer, max 10000 | Strip whitespace (kein HTML-Stripping, da kein UI-Rendering) |

### Rate Limiting & Abuse Prevention

| Resource | Limit | Window | Penalty |
|----------|-------|--------|---------|
| -- | Kein Rate Limiting in MVP | -- | -- |

---

## Architecture Layers

### DDD Vertical Slices -- Ordnerstruktur

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

### Layer Responsibilities

| Layer | Verantwortung | Pattern | Beispiel |
|-------|---------------|---------|----------|
| API (routes.py) | HTTP-Request annehmen, validieren, an Service delegieren, SSE-Response senden | Thin Controller | Route ruft `InterviewService.start()` auf, gibt `EventSourceResponse` zurueck |
| DTOs (schemas.py) | Request/Response Serialisierung und Validation | Pydantic BaseModel | `StartRequest(anonymous_id="...")` |
| Services (*/service.py) | Business-Logik orchestrieren, Domain-Objekte koordinieren | Application Service | `InterviewService` koordiniert Graph, Repository, PromptAssembler |
| Domain (*/graph.py, state.py, prompt.py) | Kern-Business-Logik | Domain Logic | LangGraph StateGraph mit Interviewer-Node |
| Repository (*/repository.py) | Datenbank-Zugriff abstrahieren | Repository Pattern | `InterviewRepository.create_session()` |
| Infrastructure (db/supabase.py) | Shared technische Infrastruktur | Singleton | Supabase Client-Instanz |
| Worker (*/timeout.py) | Async Background Tasks | asyncio.Task | TimeoutManager ueberwacht Inaktivitaet |
| Config (config/settings.py) | Zentrale Konfiguration | Pydantic Settings | Liest alle ENV-Variablen |

### Data Flow

```
Client
  │
  ▼
api/routes.py          ← HTTP Request + Pydantic Validation (schemas.py)
  │
  ▼
interview/service.py   ← Orchestration (Business Flow)
  │
  ├──▶ interview/graph.py      ← LangGraph (Domain: Gespraechsfuehrung)
  │      └── interview/state.py    ← State-Definition
  │      └── interview/prompt.py   ← Prompt-Assembly
  │
  ├──▶ interview/repository.py ← DB-Zugriff (Supabase CRUD)
  │      └── db/supabase.py        ← Shared Supabase Client
  │
  ├──▶ insights/summary.py    ← Summary-Generierung (LLM-Call)
  │
  └──▶ interview/timeout.py   ← Timeout-Ueberwachung (asyncio.Task)
         └── insights/summary.py   ← Auto-Summary bei Timeout
```

### Error Handling Strategy

| Error Type | HTTP Code | Handling | User Response | Logging |
|------------|-----------|----------|---------------|---------|
| Validation Error (Pydantic) | 422 | Automatisch durch FastAPI | Field-spezifische Fehlermeldungen | Debug |
| Business Validation (leere Nachricht) | 400 | Manuell im Service | `{"error": "Message cannot be empty"}` | Info |
| Session Not Found | 404 | Manuell im Repository | `{"error": "Session not found"}` | Info |
| Session Already Completed | 409 | Manuell im Service | `{"error": "Session already completed"}` | Info |
| LLM Error (OpenRouter) | 502 | Try/Except im Graph | `{"type": "error", "message": "LLM unavailable"}` via SSE | Error |
| Supabase Error | 500 | Try/Except im Repository | `{"error": "Internal server error"}` | Error |
| Unhandled Exception | 500 | Global Exception Handler | `{"error": "Internal server error"}` | Error + Traceback |

---

## Constraints & Integrations

### Constraints

| Constraint (from Discovery) | Technical Implication | Solution |
|----------------------------|----------------------|----------|
| Hardcoded Prompt fuer MVP | Kein dynamisches Template-System noetig | `prompt.py` liest statischen SYSTEM_PROMPT aus bestehender Datei |
| Anonyme User-IDs | Kein Auth-System, keine User-Tabelle | `anonymous_id` als String in interviews-Tabelle |
| Kein automatisches Interview-Ende | Kein Message-Counter oder Limit im Backend | Session bleibt "active" bis expliziter /end oder Timeout |
| Session-Timeout konfigurierbar | ENV-Variable muss zur Laufzeit gelesen werden | `SESSION_TIMEOUT_SECONDS` in Pydantic Settings |
| MemorySaver (In-Memory) | Conversation-State geht bei Server-Restart verloren | Akzeptabel fuer MVP. Aktive Sessions gehen verloren, abgeschlossene sind in Supabase |
| Widget Cleanup | package.json muss angepasst werden | `ai` und `@ai-sdk/react` aus widget/package.json entfernen |
| LLM-Call Timeout | OpenRouter-Calls koennen haengen | `LLM_TIMEOUT_SECONDS` (Default: 30) als ENV-Variable, in InterviewGraph als httpx/asyncio Timeout |
| DB-Call Timeout | Supabase-Calls koennen haengen | `DB_TIMEOUT_SECONDS` (Default: 10) als ENV-Variable, im Supabase Client konfiguriert |
| Supabase Env-Vars | .env.example hat nur DATABASE_URL, supabase-py braucht SUPABASE_URL + SUPABASE_KEY | .env.example anpassen: DATABASE_URL ersetzen durch SUPABASE_URL + SUPABASE_KEY |

### Integrations

| Area | System | Interface | Notes |
|------|--------|-----------|-------|
| LLM Provider | OpenRouter | HTTPS REST API (OpenAI-kompatibel) | Via `langchain-openai` ChatOpenAI mit `base_url="https://openrouter.ai/api/v1"` |
| LLM Model | Claude Sonnet 4.5 | OpenRouter Model-ID: `anthropic/claude-sonnet-4.5` | Konfigurierbar via `INTERVIEWER_LLM` .env |
| Conversation State | LangGraph MemorySaver | In-Memory Checkpointer | `thread_id` = `session_id` fuer Multi-Turn |
| Database | Supabase (PostgreSQL) | supabase-py Client (REST API) | CRUD via `supabase.table("interviews")`. Erfordert `SUPABASE_URL` + `SUPABASE_KEY` (nicht DATABASE_URL). .env.example muss angepasst werden. |
| Tracing | LangSmith | LangChain Integration (automatisch) | Env-Vars: `LANGSMITH_API_KEY`, `LANGSMITH_PROJECT`, `LANGSMITH_ENDPOINT` |
| SSE Transport | sse-starlette | `EventSourceResponse` | FastAPI-kompatibel, async generator |

---

## Quality Attributes (NFRs)

### From Discovery -> Technical Solution

| Attribute | Target | Technical Approach | Measure / Verify |
|-----------|--------|--------------------|------------------|
| Latency (First Token) | < 2s fuer ersten SSE-Chunk | Streaming via `graph.astream()` mit `stream_mode="messages"` | curl -N messen, LangSmith Trace |
| Throughput | 1 concurrent Interview (MVP) | Single-Process uvicorn, MemorySaver In-Memory | Manueller Test |
| Reliability | Interview-Daten nicht verlieren | Supabase-Persist bei Session-End, Auto-Summary bei Timeout | DB-Check nach Timeout |
| Observability | Alle LLM-Calls traceable | LangSmith-Tracing automatisch via langchain Integration | LangSmith Dashboard |
| Maintainability | Erweiterbar fuer Phase 2+ | Vertical Slices DDD, klare Service-Boundaries | Code Review |

### Monitoring & Observability

| Metric | Type | Target | Alert |
|--------|------|--------|-------|
| LLM Response Time | LangSmith Trace | < 10s | -- (MVP) |
| Interview Completion Rate | DB Query (completed / total) | -- (Baseline ermitteln) | -- |
| Timeout Rate | DB Query (completed_timeout / total) | -- (Baseline ermitteln) | -- |
| Health Check | HTTP GET /health | 200 OK | -- |

---

## Risks & Assumptions

### Assumptions

| Assumption | Technical Validation | Impact if Wrong |
|------------|---------------------|-----------------|
| OpenRouter ist zuverlaessig genug fuer MVP | LangSmith-Tracing zeigt Fehlerrate | Fallback: Direkter Anthropic API Key |
| MemorySaver reicht fuer MVP (kein Restart-Schutz) | Akzeptabel da nur curl-Tests | Aktive Sessions verloren bei Restart |
| Supabase Free Tier reicht fuer MVP | Wenige Interviews/Tag | Upgrade auf Pro Tier |
| anonymous_id ist eindeutig genug | UUID v4 aus localStorage | Kollision extrem unwahrscheinlich (2^122) |
| 60s Timeout ist sinnvoller Default | User-Testing | Anpassbar via .env |

### Risks & Mitigation

| Risk | Likelihood | Impact | Technical Mitigation | Fallback |
|------|------------|--------|---------------------|----------|
| OpenRouter Rate Limit / Downtime | Low | High (kein Interview moeglich) | Retry-Logic im Graph (1x), Error-SSE an Client | Manuell: API Key wechseln |
| MemorySaver Memory Leak bei vielen Sessions | Low (MVP: wenige Sessions) | Medium | Sessions nach Completion aus MemorySaver entfernen | Server-Restart |
| LLM generiert unpassende Antworten | Medium | Medium | Prompt ist getestet (existiert bereits), LangSmith-Monitoring | Prompt iterieren |
| Timeout-Task geht verloren bei Restart | Medium | Low | Akzeptabel fuer MVP, Supabase hat `updated_at` fuer manuelles Cleanup | Cron-Job spaeter |
| Supabase Client Connection Errors | Low | Medium | Try/Except + Retry im Repository | Fehlermeldung an User |

---

## Technology Decisions

### Stack Choices

| Area | Technology | Rationale |
|------|------------|-----------|
| Web Framework | FastAPI | Async-native, Pydantic-Integration, SSE-Support via sse-starlette |
| LLM Orchestration | LangGraph | StateGraph fuer Multi-Turn, MemorySaver fuer Session-State, Streaming-Support |
| LLM Provider | OpenRouter (ChatOpenAI mit custom base_url) | Multi-Model-Support, langchain-openai kompatibel |
| Database | Supabase (PostgreSQL) | Managed, Free Tier, supabase-py Client fuer einfaches CRUD |
| DB Client | supabase-py (REST API) | Bereits in requirements.txt, einfacher als SQLAlchemy-Setup |
| SSE Transport | sse-starlette | EventSourceResponse fuer FastAPI, async generator Support |
| Tracing | LangSmith | Native LangChain-Integration, bereits konfiguriert in .env |
| Config | Pydantic Settings | Type-safe .env Parsing, Validation, Defaults. Alle ENV-Vars: OPENROUTER_API_KEY, INTERVIEWER_LLM, INTERVIEWER_TEMPERATURE, INTERVIEWER_MAX_TOKENS, SESSION_TIMEOUT_SECONDS, LLM_TIMEOUT_SECONDS (30), DB_TIMEOUT_SECONDS (10), SUPABASE_URL, SUPABASE_KEY, LANGSMITH_* |
| Architecture | DDD Vertical Slices | Bounded Contexts als Top-Level, Layer pro Context, skalierbar |

### Trade-offs

| Decision | Pro | Con | Mitigation |
|----------|-----|-----|------------|
| MemorySaver statt PostgresSaver | Kein DB-Setup fuer Checkpoints, einfach | State verloren bei Restart | Akzeptabel fuer MVP, Upgrade spaeter |
| supabase-py statt SQLAlchemy | Einfacher, weniger Boilerplate | Keine Transactions, kein ORM | Reicht fuer einfaches CRUD in MVP |
| Eigenes SSE-Format statt Standard | Minimal, keine Dependencies, volle Kontrolle | Kein Standard-Label | assistant-ui ChatModelAdapter parst es |
| Vertical Slices statt Horizontal Layers | Hohe Kohaesion, Feature = Ordner | Weniger "reines DDD" | Layer-Pattern innerhalb der Slices |
| Einzelner uvicorn-Prozess | Einfach, kein Worker-Setup | Kein Parallelismus | MVP: 1 concurrent Interview reicht |

---

## Open Questions

| # | Question | Options | Recommended | Decision |
|---|----------|---------|-------------|----------|
| -- | Alle Fragen geklaert | -- | -- | -- |

---

## Research Log

| Date | Area | Finding |
|------|------|---------|
| 2026-02-13 | Codebase | Backend-Struktur: app/graph/prompt.py (hardcoded), app/graph/prompt_interviewer_original.md (Template), app/context/*.json |
| 2026-02-13 | Codebase | requirements.txt: fastapi, uvicorn, langgraph, langchain-openai, langchain-core, python-dotenv, httpx, sse-starlette, supabase |
| 2026-02-13 | Codebase | Widget package.json hat `ai` und `@ai-sdk/react` die entfernt werden muessen |
| 2026-02-13 | Codebase | .env.example zeigt alle ENV-Vars: OpenRouter, LangSmith, Supabase, Session-Timeout |
| 2026-02-13 | Web | LangGraph: StateGraph + add_messages + MemorySaver mit thread_id ist Standard-Pattern |
| 2026-02-13 | Web | OpenRouter: ChatOpenAI mit base_url="https://openrouter.ai/api/v1" und model="provider/model" |
| 2026-02-13 | Web | DDD mit FastAPI: Vertical Slices (Bounded Context = Ordner) ist moderner Best Practice |
| 2026-02-13 | Web | Horizontal DDD Layers (domain/application/infrastructure) ist Enterprise-Java-Stil, zu viel Boilerplate fuer Python MVP |
| 2026-02-13 | Web | supabase-py: table().select/insert/update.execute() fuer CRUD, kein ORM noetig |
| 2026-02-13 | Web | sse-starlette: EventSourceResponse mit async generator, yield dict mit data-Key |
| 2026-02-13 | Web | assistant-ui: LocalRuntime mit ChatModelAdapter kann eigenes SSE-Format parsen |

---

## Q&A Log

| # | Question | Answer |
|---|----------|--------|
| 1 | DDD-Strukturierung: Wie sollen die typischen Layer (Services, DTOs, Repositories, Controller) mit den Bounded Contexts kombiniert werden? | Vertical Slices: Bounded Contexts als Top-Level-Ordner, Layer (service.py, repository.py) innerhalb jedes Contexts. DTOs zentral in api/schemas.py. Pragmatisch und skalierbar. |
| 2 | SSE-Format: Eigenes simples Format oder standardisiertes Protokoll? | Eigenes simples Format mit 3 Event-Types (text-delta, text-done, metadata). Kein einheitlicher Standard existiert, alle Alternativen sind proprietaer (Vercel, CopilotKit). assistant-ui LocalRuntime parst eigenes Format via ChatModelAdapter. |
| 3 | Supabase-Zugriff: supabase-py Client oder SQLAlchemy mit DATABASE_URL? | supabase-py Client (REST API). Bereits in requirements.txt, einfacher als SQLAlchemy-Setup, reicht fuer CRUD in MVP. |

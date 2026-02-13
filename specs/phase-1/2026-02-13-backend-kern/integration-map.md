# Integration Map: Backend-Kern

**Generated:** 2026-02-13
**Slices:** 6
**Connections:** 28

---

## Dependency Graph (Visual)

```
+-----------------------+
|   Slice 01            |
|   App-Skeleton        |
|   + DDD-Struktur      |
+-----------+-----------+
            |
            v
+-----------------------+
|   Slice 02            |
|   LangGraph           |
|   Interview-Graph     |
+-----+--------+--------+
      |        |
      v        |
+-----------+  |
| Slice 03  |  |
| SSE-      |  |
| Streaming |  |
| Endpoints |  |
+-----+-----+  |
      |        |
      v        |
+-----------+  |
| Slice 04  |  |
| Supabase- |<-+
| Persistenz|
+-----+-----+
      |
      v
+-----------+
| Slice 05  |<--- (also depends on Slice 02)
| Summary-  |
| Injection |
+-----+-----+
      |
      v
+-----------+
| Slice 06  |<--- (also depends on Slice 03, Slice 04)
| Session-  |
| Timeout   |
+-----------+
```

---

## Nodes

### Slice 01: App-Skeleton + DDD-Struktur

| Field | Value |
|-------|-------|
| Status | APPROVED |
| Dependencies | None |
| Outputs | FastAPI App, Settings, DDD-Ordnerstruktur |

**Inputs:**

| Input | Source | Validation |
|-------|--------|------------|
| -- | -- (erster Slice) | PASS -- keine Dependencies |

**Outputs:**

| Output | Type | Consumers |
|--------|------|-----------|
| `app.main:app` | FastAPI App | Slice 02, 03, 04, 05, 06 |
| `Settings` (Pydantic BaseSettings) | Klasse | Slice 02, 03, 04, 05, 06 |
| `app.state.settings` | Settings-Instanz (Runtime) | Slice 03, 04, 05, 06 |
| DDD-Ordnerstruktur | Directory Layout | Slice 02, 03, 04, 05, 06 |
| `SYSTEM_PROMPT` in `app/interview/prompt.py` | String-Konstante | Slice 02 |

---

### Slice 02: LangGraph Interview-Graph

| Field | Value |
|-------|-------|
| Status | APPROVED |
| Dependencies | Slice 01 |
| Outputs | InterviewGraph, PromptAssembler, InterviewState |

**Inputs:**

| Input | Source | Validation |
|-------|--------|------------|
| `Settings` | Slice 01 | PASS -- `from app.config.settings import Settings` |
| `SYSTEM_PROMPT` | Slice 01 | PASS -- in `app/interview/prompt.py` |
| DDD-Ordnerstruktur (`app/interview/`) | Slice 01 | PASS -- `__init__.py` existiert |

**Outputs:**

| Output | Type | Consumers |
|--------|------|-----------|
| `InterviewGraph` | Klasse | Slice 03, 05, 06 |
| `InterviewGraph.astream()` | Async Generator | Slice 03 |
| `InterviewGraph.get_history()` | Methode | Slice 03, 05, 06 |
| `PromptAssembler` | Klasse | Slice 05 |
| `PromptAssembler.build()` | Statische Methode | Slice 05 |
| `SUMMARY_INJECTION_TEMPLATE` | String-Konstante | Slice 05 |
| `InterviewState` | TypedDict | Slice 03, 05 |

---

### Slice 03: SSE-Streaming Endpoints

| Field | Value |
|-------|-------|
| Status | APPROVED |
| Dependencies | Slice 01, Slice 02 |
| Outputs | InterviewService, API Endpoints, Pydantic DTOs |

**Inputs:**

| Input | Source | Validation |
|-------|--------|------------|
| `app.main:app` | Slice 01 | PASS -- `app.include_router()` |
| `Settings` | Slice 01 | PASS -- via `app.state.settings` |
| `app.state.settings` | Slice 01 | PASS -- Lifespan setzt Settings |
| `InterviewGraph` | Slice 02 | PASS -- `InterviewGraph(settings)` instanziierbar |
| `InterviewGraph.astream()` | Slice 02 | PASS -- yieldet `(AIMessageChunk, dict)` Tuples |

**Outputs:**

| Output | Type | Consumers |
|--------|------|-----------|
| `InterviewService` | Klasse | Slice 04, 05, 06 |
| `InterviewService._sessions` | In-Memory Dict | Slice 04, 06 |
| `SessionNotFoundError` | Exception | Slice 04, 05, 06 |
| `SessionAlreadyCompletedError` | Exception | Slice 04, 05, 06 |
| `StartRequest` | Pydantic Model | Slice 04 |
| `EndResponse` | Pydantic Model | Slice 05 |
| `get_interview_service` | FastAPI Dependency | Routes (intern) |
| `reset_interview_service` | Test-Helper | Tests |
| API Endpoints (`/start`, `/message`, `/end`) | HTTP Routes | Phase 2 (Widget) |

---

### Slice 04: Supabase-Persistenz

| Field | Value |
|-------|-------|
| Status | APPROVED |
| Dependencies | Slice 01, Slice 03 |
| Outputs | Supabase Client, InterviewRepository, interviews-Tabelle |

**Inputs:**

| Input | Source | Validation |
|-------|--------|------------|
| `Settings` | Slice 01 | PASS -- `supabase_url`, `supabase_key`, `db_timeout_seconds` |
| `app.state.settings` | Slice 01 | PASS -- Runtime-Zugriff |
| `backend/app/db/__init__.py` | Slice 01 | PASS -- Package existiert |
| `InterviewService` | Slice 03 | PASS -- erweitert um Repository-Parameter |
| `get_interview_service` | Slice 03 | PASS -- erweitert um Repository-Injection |
| `SessionNotFoundError`, `SessionAlreadyCompletedError` | Slice 03 | PASS -- unveraendert |

**Outputs:**

| Output | Type | Consumers |
|--------|------|-----------|
| `get_supabase_client()` | Function (Singleton) | Slice 05, 06 |
| `InterviewRepository` | Klasse | Slice 05, 06 |
| `InterviewRepository.get_recent_summaries()` | Methode | Slice 05 |
| `InterviewRepository.complete_session()` | Methode | Slice 05, 06 |
| `interviews` Tabelle | DB Schema | Slice 05, 06 |
| `InterviewService._format_transcript()` | Static Method | Slice 05, 06 |

---

### Slice 05: Summary-Generierung + Injection

| Field | Value |
|-------|-------|
| Status | APPROVED |
| Dependencies | Slice 02, Slice 04 |
| Outputs | SummaryService, InterviewGraph.set_summaries() |

**Inputs:**

| Input | Source | Validation |
|-------|--------|------------|
| `InterviewGraph` | Slice 02 | PASS -- instanziierbar, `.get_history()`, `.astream()` |
| `PromptAssembler.build()` | Slice 02 | PASS -- `(summaries: list[str] | None) -> str` |
| `SUMMARY_INJECTION_TEMPLATE` | Slice 02 | PASS -- String-Konstante |
| `InterviewRepository` | Slice 04 | PASS -- `.get_recent_summaries()`, `.complete_session()` |
| `InterviewRepository.get_recent_summaries()` | Slice 04 | PASS -- `(anonymous_id, limit) -> list[str]` |
| `InterviewRepository.complete_session()` | Slice 04 | PASS -- akzeptiert echten Summary-String |
| `InterviewService` | Slice 04 (erweitert) | PASS -- Constructor akzeptiert `repository` |
| `Settings` | Slice 01 | PASS -- `openrouter_api_key`, `interviewer_llm`, `llm_timeout_seconds` |

**Outputs:**

| Output | Type | Consumers |
|--------|------|-----------|
| `SummaryService` | Klasse | Slice 06 |
| `SummaryService.generate()` | Async Methode | Slice 06 |
| `InterviewGraph.set_summaries()` | Methode | Slice 06 |

---

### Slice 06: Session-Timeout + Auto-Summary

| Field | Value |
|-------|-------|
| Status | APPROVED |
| Dependencies | Slice 03, Slice 04, Slice 05 |
| Outputs | TimeoutManager (kein Consumer -- letzter Slice) |

**Inputs:**

| Input | Source | Validation |
|-------|--------|------------|
| `InterviewService` | Slice 03 | PASS -- Constructor akzeptiert `timeout_manager` |
| `InterviewService._sessions` | Slice 03 | PASS -- In-Memory Dict verfuegbar |
| `InterviewRepository.complete_session()` | Slice 04 | PASS -- akzeptiert `status="completed_timeout"` |
| `SummaryService.generate()` | Slice 05 | PASS -- `(messages: list[AnyMessage]) -> str` |
| `InterviewGraph.get_history()` | Slice 02 (via 05) | PASS -- `(session_id) -> list[AnyMessage]` |
| `InterviewService._format_transcript()` | Slice 04 (via 05) | PASS -- `(messages) -> list[dict]` |
| `Settings.session_timeout_seconds` | Slice 01 | PASS -- Default 60 |
| `main.py` Lifespan | Slice 01 | PASS -- Shutdown-Hook verfuegbar |

**Outputs:**

| Output | Type | Consumers |
|--------|------|-----------|
| `TimeoutManager` | Klasse | -- (kein externer Consumer) |
| `TimeoutManager.register()` | Methode | InterviewService.start() (intern) |
| `TimeoutManager.reset()` | Methode | InterviewService.message() (intern) |
| `TimeoutManager.cancel()` | Methode | InterviewService.end() (intern) |
| `TimeoutManager.cancel_all()` | Methode | main.py Lifespan (intern) |
| `InterviewService._handle_timeout()` | Async Methode | TimeoutManager Callback (intern) |

---

## Connections

| # | From | To | Resource | Type | Status |
|---|------|-----|----------|------|--------|
| 1 | Slice 01 | Slice 02 | `Settings` | Pydantic BaseSettings | PASS |
| 2 | Slice 01 | Slice 02 | `SYSTEM_PROMPT` | String-Konstante | PASS |
| 3 | Slice 01 | Slice 02 | DDD-Ordnerstruktur | Directory Layout | PASS |
| 4 | Slice 01 | Slice 03 | `app.main:app` | FastAPI App | PASS |
| 5 | Slice 01 | Slice 03 | `Settings` | Pydantic BaseSettings | PASS |
| 6 | Slice 01 | Slice 03 | `app.state.settings` | Settings-Instanz | PASS |
| 7 | Slice 02 | Slice 03 | `InterviewGraph` | Klasse | PASS |
| 8 | Slice 02 | Slice 03 | `InterviewGraph.astream()` | Async Generator | PASS |
| 9 | Slice 01 | Slice 04 | `Settings` | Pydantic BaseSettings | PASS |
| 10 | Slice 01 | Slice 04 | `app.state.settings` | Settings-Instanz | PASS |
| 11 | Slice 01 | Slice 04 | `db/__init__.py` | Package | PASS |
| 12 | Slice 03 | Slice 04 | `InterviewService` | Klasse (erweitert) | PASS |
| 13 | Slice 03 | Slice 04 | `get_interview_service` | FastAPI Dependency (erweitert) | PASS |
| 14 | Slice 03 | Slice 04 | `SessionNotFoundError` | Exception | PASS |
| 15 | Slice 03 | Slice 04 | `SessionAlreadyCompletedError` | Exception | PASS |
| 16 | Slice 02 | Slice 05 | `InterviewGraph` | Klasse (erweitert) | PASS |
| 17 | Slice 02 | Slice 05 | `PromptAssembler.build()` | Statische Methode | PASS |
| 18 | Slice 02 | Slice 05 | `SUMMARY_INJECTION_TEMPLATE` | String-Konstante | PASS |
| 19 | Slice 04 | Slice 05 | `InterviewRepository` | Klasse | PASS |
| 20 | Slice 04 | Slice 05 | `InterviewRepository.get_recent_summaries()` | Methode | PASS |
| 21 | Slice 04 | Slice 05 | `InterviewRepository.complete_session()` | Methode | PASS |
| 22 | Slice 01 | Slice 05 | `Settings` | Pydantic BaseSettings | PASS |
| 23 | Slice 03 | Slice 06 | `InterviewService` | Klasse (erweitert) | PASS |
| 24 | Slice 03 | Slice 06 | `InterviewService._sessions` | In-Memory Dict | PASS |
| 25 | Slice 04 | Slice 06 | `InterviewRepository.complete_session()` | Methode | PASS |
| 26 | Slice 05 | Slice 06 | `SummaryService.generate()` | Async Methode | PASS |
| 27 | Slice 02 | Slice 06 | `InterviewGraph.get_history()` | Methode | PASS |
| 28 | Slice 01 | Slice 06 | `Settings.session_timeout_seconds` | int | PASS |

---

## Validation Results

### PASS Valid Connections: 28

All declared dependencies have matching outputs in producer slices.

### Orphaned Outputs: 0

Alle Outputs haben mindestens einen Consumer oder sind finale User-facing Outputs (API Endpoints fuer Phase 2).

| Output | Defined In | Consumers | Action |
|--------|------------|-----------|--------|
| API Endpoints (`/start`, `/message`, `/end`) | Slice 03 | Phase 2 (Widget) | User-facing, kein Consumer in Backend-Kern noetig |
| `TimeoutManager` | Slice 06 | Intern (letzter Slice) | Kein externer Consumer noetig |

### Missing Inputs: 0

Keine fehlenden Inputs gefunden.

### Deliverable-Consumer Gaps: 0

Alle Connections wurden gegen die Deliverables-Listen geprueft:

| Component | Defined In | Consumer File | In Deliverables? | Status |
|-----------|------------|---------------|-------------------|--------|
| `Settings` | Slice 01 (`config/settings.py`) | Slice 02 (`interview/graph.py`) | Slice 02 Deliverables | PASS |
| `InterviewGraph` | Slice 02 (`interview/graph.py`) | Slice 03 (`interview/service.py`) | Slice 03 Deliverables | PASS |
| `InterviewService` | Slice 03 (`interview/service.py`) | Slice 04 (`interview/service.py` MODIFY) | Slice 04 Deliverables | PASS |
| `InterviewRepository` | Slice 04 (`interview/repository.py`) | Slice 05 (`interview/service.py` MODIFY) | Slice 05 Deliverables | PASS |
| `SummaryService` | Slice 05 (`insights/summary.py`) | Slice 06 (`interview/service.py` MODIFY) | Slice 06 Deliverables | PASS |
| `app/main.py` | Slice 01 | Slice 03 (`main.py` MODIFY), Slice 06 (`main.py` MODIFY) | Slice 03 + 06 Deliverables | PASS |
| `app/api/dependencies.py` | Slice 03 | Slice 04 (MODIFY), Slice 05 (MODIFY), Slice 06 (MODIFY) | Deliverables in each | PASS |

---

## Discovery Traceability

### UI Components Coverage

| Discovery Element | Type | Location | Covered In | Status |
|-------------------|------|----------|------------|--------|
| n/a (Backend-only Phase) | -- | -- | -- | n/a |

### State Machine Coverage

| State | Required UI | Available Actions | Covered In | Status |
|-------|-------------|-------------------|------------|--------|
| `idle` | n/a | Start | Slice 03 (POST /start erstellt Session) | PASS |
| `active` | n/a | Message, End | Slice 03 (POST /message, POST /end) | PASS |
| `streaming` | n/a | Warten (Client empfaengt Chunks) | Slice 03 (SSE-Stream via astream) | PASS |
| `summarizing` | n/a | Warten | Slice 05 (SummaryService.generate in end()) | PASS |
| `completed` | n/a | Neues Interview starten | Slice 04 (complete_session status=completed) | PASS |
| `completed_timeout` | n/a | Neues Interview starten | Slice 06 (_handle_timeout, status=completed_timeout) | PASS |
| `error` | n/a | Retry (Message nochmal) | Slice 03 (SSE error-Event, Session bleibt active) | PASS |

### Transitions Coverage

| From | Trigger | To | Covered In | Status |
|------|---------|-----|------------|--------|
| `idle` | POST /start | `active` | Slice 03 (start() erstellt Session mit status=active) | PASS |
| `active` | POST /message | `streaming` | Slice 03 (message() ruft graph.astream auf) | PASS |
| `streaming` | SSE complete | `active` | Slice 03 (text-done Event, Session bleibt active) | PASS |
| `streaming` | LLM error | `error` | Slice 03 (error-Event via SSE) | PASS |
| `active` | POST /end | `summarizing` | Slice 03/05 (end() ruft SummaryService.generate) | PASS |
| `active` | Timeout | `summarizing` | Slice 06 (_handle_timeout nach SESSION_TIMEOUT_SECONDS) | PASS |
| `summarizing` | Summary fertig | `completed` | Slice 05 (complete_session mit status=completed) | PASS |
| `summarizing` | Summary fertig (Timeout) | `completed_timeout` | Slice 06 (complete_session mit status=completed_timeout) | PASS |
| `error` | POST /message (retry) | `streaming` | Slice 03 (Session bleibt active, neuer Message-Call) | PASS |

### Business Rules Coverage

| Rule | Covered In | Status |
|------|------------|--------|
| Kein automatisches Ende / Message-Limit | Slice 03 (kein Limit im Code) | PASS |
| Jede Session gehoert zu anonymous_id | Slice 03 (sessions Dict speichert anonymous_id) | PASS |
| Letzte 3 Summaries laden beim Start | Slice 05 (get_recent_summaries(limit=3) in start()) | PASS |
| Summaries in System-Prompt injizieren | Slice 05 (graph.set_summaries + PromptAssembler.build) | PASS |
| Summary-Format: Bullet-Liste | Slice 05 (SUMMARY_PROMPT erzwingt "- " Format) | PASS |
| Session-Timeout konfigurierbar | Slice 01 (Settings.session_timeout_seconds), Slice 06 (TimeoutManager) | PASS |
| Bei Timeout: Auto-Summary, completed_timeout | Slice 06 (_handle_timeout + complete_session) | PASS |
| LLM-Provider: OpenRouter | Slice 02 (ChatOpenAI base_url=openrouter.ai) | PASS |
| LangSmith-Tracing aktiv | Slice 01 (Settings: langsmith_*) | PASS |
| Hardcoded Prompt fuer MVP | Slice 01 (prompt.py MOVE), Slice 02 (SYSTEM_PROMPT) | PASS |
| MemorySaver In-Memory | Slice 02 (MemorySaver als Checkpointer) | PASS |
| Supabase speichert fertige Interviews | Slice 04 (InterviewRepository CRUD) | PASS |

### Data Fields Coverage

| Field | Required | Covered In | Status |
|-------|----------|------------|--------|
| `interviews.id` | Yes | Slice 04 (SQL Migration, UUID PK) | PASS |
| `interviews.anonymous_id` | Yes | Slice 04 (create_session, Index) | PASS |
| `interviews.session_id` | Yes | Slice 04 (create_session, UNIQUE, Index) | PASS |
| `interviews.status` | Yes | Slice 04 (CHECK constraint), Slice 06 (completed_timeout) | PASS |
| `interviews.transcript` | No | Slice 04 (complete_session, JSONB) | PASS |
| `interviews.summary` | No | Slice 05 (SummaryService.generate) | PASS |
| `interviews.message_count` | Yes | Slice 04 (increment_message_count) | PASS |
| `interviews.created_at` | Yes | Slice 04 (DEFAULT now()) | PASS |
| `interviews.updated_at` | Yes | Slice 04 (increment_message_count aktualisiert) | PASS |
| `interviews.completed_at` | No | Slice 04 (complete_session setzt Timestamp) | PASS |

**Discovery Coverage:** 41/41 (100%)

---

## Summary

| Metric | Value |
|--------|-------|
| Total Slices | 6 |
| Total Connections | 28 |
| Valid Connections | 28 |
| Orphaned Outputs | 0 |
| Missing Inputs | 0 |
| Deliverable-Consumer Gaps | 0 |
| Discovery Coverage | 100% |

---

VERDICT: READY FOR ORCHESTRATION

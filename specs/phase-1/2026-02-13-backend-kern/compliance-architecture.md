# Gate 1: Architecture Compliance Report

**Gepruefte Architecture:** `specs/phase-1/2026-02-13-backend-kern/architecture.md`
**Pruefdatum:** 2026-02-13
**Retry:** 2/3
**Discovery:** `specs/phase-1/2026-02-13-backend-kern/discovery.md`
**Wireframes:** n/a (Backend-only Feature, kein UI)

---

## Summary

| Status | Count |
|--------|-------|
| PASS | 70 |
| WARNING | 0 |
| BLOCKING | 0 |

**Verdict:** APPROVED

---

## Previous Blocking Issues -- Fix Verification

| # | Issue (Retry 1) | Fix in Architecture | Evidence | Status |
|---|----------------|--------------------|---------|---------
| 1 | Kein LLM-Call Timeout definiert | LLM_TIMEOUT_SECONDS (Default: 30) ergaenzt | Arch Zeile 170: "LLM-Call mit LLM_TIMEOUT_SECONDS Timeout". Zeile 360: Constraint dokumentiert. Zeile 437: In Config/Settings gelistet. | FIXED |
| 2 | Kein DB-Call Timeout definiert | DB_TIMEOUT_SECONDS (Default: 10) ergaenzt | Arch Zeile 174: "DB-Calls mit DB_TIMEOUT_SECONDS Timeout". Zeile 361: Constraint dokumentiert. Zeile 437: In Config/Settings gelistet. | FIXED |
| 3 | Supabase Client vs DATABASE_URL Inkonsistenz | SUPABASE_URL + SUPABASE_KEY statt DATABASE_URL | Arch Zeile 362: ".env.example anpassen: DATABASE_URL ersetzen durch SUPABASE_URL + SUPABASE_KEY". Zeile 371: "Erfordert SUPABASE_URL + SUPABASE_KEY (nicht DATABASE_URL)". Zeile 437: Beide in Config gelistet. | FIXED |

**Hinweis:** `.env.example` im Repo enthaelt noch `DATABASE_URL` (Zeile 17). Die Architecture dokumentiert dies explizit als Implementierungs-Aufgabe (Zeile 362). Das ist kein Architecture-Gap sondern eine Implementation-Aufgabe fuer Slice 1.

---

## A) Feature Mapping

Jedes In-Scope Item aus Discovery wird gegen die Architecture geprueft.

| # | Discovery In-Scope Item | Architecture Section | API Endpoint | DB Schema | Status |
|---|------------------------|---------------------|--------------|-----------|--------|
| 1 | FastAPI App-Skeleton (main.py, config.py, CORS, Health-Check) | Architecture Layers: main.py, config/settings.py | GET /health | -- | PASS |
| 2 | LangGraph StateGraph: Interviewer-Node mit System-Prompt + History | Server Logic: InterviewGraph | Intern (kein Endpoint) | -- | PASS |
| 3 | SSE-Streaming (eigenes simples Format, kompatibel mit assistant-ui) | API Design: SSE Event Format (text-delta, text-done, metadata, error) | POST /start, /message | -- | PASS |
| 4 | POST /api/interview/start | API Design: Endpoints | POST /api/interview/start | interviews (create) | PASS |
| 5 | POST /api/interview/message (SSE) | API Design: Endpoints | POST /api/interview/message | interviews (update count) | PASS |
| 6 | POST /api/interview/end | API Design: Endpoints | POST /api/interview/end | interviews (complete) | PASS |
| 7 | MemorySaver fuer In-Session Conversation-Persistenz | Integrations: LangGraph MemorySaver, Risks: MemorySaver Assumptions | Intern | -- | PASS |
| 8 | Summary-Generierung am Interview-Ende (separater LLM-Call, Bullet-Liste) | Server Logic: SummaryService | Via POST /end | interviews.summary | PASS |
| 9 | Auto-Summary bei Session-Timeout | Server Logic: TimeoutManager, Business Logic Flow: Timeout | Intern (async task) | interviews (status=completed_timeout) | PASS |
| 10 | Summary-Injection: Letzte 3 Summaries des Users in System-Prompt | Server Logic: PromptAssembler, Business Logic Flow: /start | Via POST /start | interviews (read summaries) | PASS |
| 11 | Supabase: interviews-Tabelle (Transkript, Summary, Status) | Database Schema: Schema Details, SQL Migration | -- | interviews (vollstaendig) | PASS |
| 12 | Anonyme User-Identifikation (anonymous_id vom Client) | Security: anonymous_id-basiert, DTOs: StartRequest | POST /start (anonymous_id) | interviews.anonymous_id | PASS |
| 13 | OpenRouter als LLM-Provider (Claude Sonnet 4.5) | Integrations: OpenRouter, Technology Decisions: LLM Provider | -- | -- | PASS |
| 14 | Widget package.json bereinigen: ai und @ai-sdk/react entfernen | Constraints: Widget Cleanup | -- | -- | PASS |
| 15 | DDD Vertical Slices Architektur | Architecture Layers: DDD Vertical Slices Ordnerstruktur | -- | -- | PASS |
| 16 | LangSmith-Tracing | Integrations: LangSmith, NFRs: Observability | -- | -- | PASS |

**Feature Mapping Ergebnis:** 16/16 PASS -- Alle Discovery In-Scope Items sind in der Architecture adressiert.

---

## B) Constraint Mapping

### Business Rules

| # | Business Rule (Discovery) | Architecture Location | Technische Abbildung | Status |
|---|--------------------------|----------------------|---------------------|--------|
| 1 | Interview hat kein automatisches Ende / Message-Limit | Constraints: "Kein automatisches Interview-Ende" | Session bleibt active bis /end oder Timeout | PASS |
| 2 | Jede Session gehoert zu anonymous_id | DTOs: StartRequest.anonymous_id, DB: interviews.anonymous_id | anonymous_id als TEXT NOT NULL mit Index | PASS |
| 3 | Beim Start letzte 3 Summaries laden | Server Logic: /start Flow Step 3 | InterviewRepository.get_recent_summaries(anonymous_id, limit=3) | PASS |
| 4 | Summaries in System-Prompt injiziert (nach statischem Teil) | Server Logic: PromptAssembler.build(base_prompt, summaries) | PromptAssembler als eigene Klasse | PASS |
| 5 | Summary-Format: Freie Bullet-Liste | Server Logic: SummaryService | Separater LLM-Call fuer Bullet-Summary | PASS |
| 6 | Session-Timeout konfigurierbar via SESSION_TIMEOUT_SECONDS | Constraints: ENV-Variable, Config: Pydantic Settings | SESSION_TIMEOUT_SECONDS in settings.py, Default 60s | PASS |
| 7 | Bei Timeout: Auto-Summary + completed_timeout | Server Logic: Timeout Flow | TimeoutManager triggert SummaryService + DB write mit status=completed_timeout | PASS |
| 8 | LLM-Provider: OpenRouter, Modell konfigurierbar | Integrations: OpenRouter, Config | INTERVIEWER_LLM in Pydantic Settings | PASS |
| 9 | LangSmith-Tracing standardmaessig aktiv | Integrations: LangSmith | Native LangChain-Integration, ENV-Vars | PASS |
| 10 | Hardcoded Prompt fuer MVP | Constraints: "prompt.py liest statischen SYSTEM_PROMPT" | prompt.py existiert in Codebase (66 Zeilen, ca. 3000 chars) | PASS |
| 11 | MemorySaver haelt Conversation-State in-memory | Integrations: MemorySaver, Risks: Memory Leak Mitigation | Sessions nach Completion aus MemorySaver entfernen | PASS |
| 12 | Supabase speichert fertige Interviews | Database Schema: alle Felder vorhanden | interviews-Tabelle mit transcript, summary, status, created_at, updated_at, completed_at | PASS |

### Error Paths

| # | Discovery Error Path | Architecture Error Handling | Status |
|---|---------------------|---------------------------|--------|
| 1 | Timeout (User verschwindet): Auto-Summary, completed_timeout | Server Logic: Timeout Flow, TimeoutManager.on_timeout | PASS |
| 2 | LLM-Fehler: Fehler an Client, Session bleibt offen | Error Handling: LLM Error -> 502, SSE error event | PASS |
| 3 | Ungueltige session_id: 404 | Error Handling: Session Not Found -> 404 | PASS |
| 4 | Leere Nachricht: 400 | Validation Rules: message nicht leer -> 400 | PASS |
| 5 | Session bereits beendet: 409 | Error Handling: Session Already Completed -> 409 | PASS |

### State Machine Transitions

| State Transition | Discovery | Architecture | Status |
|-----------------|-----------|--------------|--------|
| idle -> active (POST /start) | Letzte 3 Summaries laden | /start Flow: create_session + get_recent_summaries + build prompt | PASS |
| active -> streaming (POST /message) | Nachricht nicht leer | Validation: message nicht leer, max 10000 | PASS |
| streaming -> active (SSE complete) | History gespeichert | /message Flow: Graph invoke + increment_message_count | PASS |
| streaming -> error (LLM error) | Fehlermeldung an Client | SSE error event: {"type": "error", "message": "..."} | PASS |
| active -> summarizing (POST /end) | User beendet explizit | /end Flow: cancel timeout, get history, generate summary | PASS |
| active -> summarizing (Timeout) | Auto-End | Timeout Flow: on_timeout -> summary -> complete | PASS |
| summarizing -> completed/completed_timeout | Transkript + Summary in Supabase INSERT | complete_session(session_id, transcript, summary) | PASS |
| error -> streaming (retry) | Gleiche Nachricht nochmal | Validation: session status=active pruefung | PASS |

**Constraint Mapping Ergebnis:** 25/25 PASS -- Alle Business Rules, Error Paths und State Transitions sind technisch abgebildet.

---

## C) Realistic Data Check

### Codebase Evidence

```
# Keine SQL-Migrations vorhanden (supabase/migrations/ ist leer)
# Erster Schema-Entwurf, keine Vergleichswerte aus bestehenden Tabellen

# Existierende Dateien:
# - backend/app/graph/prompt.py: SYSTEM_PROMPT = 66 Zeilen, ca. 3000 Zeichen
# - backend/app/context/*.json: 4 Context-Dateien (company, product, 2x scenario)
# - backend/requirements.txt: 9 Dependencies (fastapi, langgraph, supabase, etc.)
# - .env.example: DATABASE_URL=postgresql://... (Architecture plant Umbau auf SUPABASE_URL + SUPABASE_KEY)
# - widget/package.json: Hat "ai" und "@ai-sdk/react" die entfernt werden muessen (bestaetigt)
```

### External API Analysis

| API | Field | Evidence | Measured/Expected Length | Arch Type | Recommendation | Status |
|-----|-------|---------|------------------------|-----------|----------------|--------|
| OpenRouter | LLM Response (tokens) | INTERVIEWER_MAX_TOKENS=4000, ca. 16000 chars bei 4 chars/token | ~16000 chars pro Antwort | Streaming (nicht gespeichert einzeln) | n/a (wird in transcript JSONB aggregiert) | PASS |
| OpenRouter | Error Messages | Standard OpenAI-kompatible Errors | < 500 chars | SSE error event (nicht persistiert) | n/a | PASS |
| OpenRouter | API Timeout | Architecture: LLM_TIMEOUT_SECONDS Default 30s | 30 Sekunden | httpx/asyncio Timeout im InterviewGraph | PASS -- dokumentiert in Constraints und Config | PASS |
| Supabase | JSONB Capacity | PostgreSQL JSONB: max 255 MB | Transcript mit 50 Messages a 500 chars = ~25000 chars | JSONB | PASS -- JSONB hat keine praktische Groessenbeschraenkung | PASS |
| Supabase | API Timeout | Architecture: DB_TIMEOUT_SECONDS Default 10s | 10 Sekunden | Im Supabase Client konfiguriert | PASS -- dokumentiert in Constraints und Config | PASS |
| LangGraph | thread_id | UUID Format | 36 chars | UUID | PASS | PASS |
| LangSmith | Trace Data | Automatisch via LangChain, keine eigene Persistenz | n/a | n/a | PASS | PASS |

### Data Type Verdicts

| # | Field | Arch Type | Evidence | Verdict | Issue |
|---|-------|-----------|----------|---------|-------|
| 1 | interviews.id | UUID PK DEFAULT gen_random_uuid() | Standard PostgreSQL UUID, 36 chars | PASS | -- |
| 2 | interviews.anonymous_id | TEXT NOT NULL | Discovery: "vom Client, localStorage" -- UUID v4 = 36 chars, aber Format nicht erzwungen. TEXT ist korrekt da Client-generiert und Format unbekannt. DTO validiert max 255 chars. | PASS | -- |
| 3 | interviews.session_id | UUID NOT NULL UNIQUE | LangGraph thread_id ist UUID, 36 chars | PASS | -- |
| 4 | interviews.status | TEXT NOT NULL CHECK (IN 'active','completed','completed_timeout') | 3 Enum-Werte: active (6 chars), completed (9 chars), completed_timeout (17 chars). CHECK Constraint vorhanden. | PASS | -- |
| 5 | interviews.transcript | JSONB NULL | Array von {role, content} Objekten. Laengstes realistisches Interview: 100 Messages a 1000 chars = ~100KB. JSONB max 255MB. Grosszuegig. | PASS | -- |
| 6 | interviews.summary | TEXT NULL | LLM-generierte Bullet-Liste. Laenge unvorhersagbar (typisch 500-2000 chars). TEXT ist korrekt -- kein VARCHAR-Limit fuer LLM-Output. | PASS | -- |
| 7 | interviews.message_count | INTEGER NOT NULL DEFAULT 0 | Realistisch 5-50 Messages pro Interview. INTEGER max 2.147.483.647. | PASS | -- |
| 8 | interviews.created_at | TIMESTAMPTZ NOT NULL DEFAULT now() | Standard PostgreSQL Timestamp | PASS | -- |
| 9 | interviews.updated_at | TIMESTAMPTZ NOT NULL DEFAULT now() | Standard PostgreSQL Timestamp | PASS | -- |
| 10 | interviews.completed_at | TIMESTAMPTZ NULL | Nullable korrekt (null waehrend active) | PASS | -- |
| 11 | DTO: StartRequest.anonymous_id | str, max 255 | Client-generierte ID. UUID v4 = 36 chars. 255 ist grosszuegiger Buffer (7x). | PASS | -- |
| 12 | DTO: MessageRequest.message | str, max 10000 | User-Input in Chat. 10000 chars = ca. 2500 Woerter. Fuer Chat-Nachrichten mehr als ausreichend. | PASS | -- |
| 13 | DTO: MessageRequest.session_id | str, UUID-Format | UUID Validation im DTO, 36 chars | PASS | -- |
| 14 | DTO: EndResponse.summary | str | Keine Laengenbegrenzung, LLM-generiert. Korrekt als unbegrenzter String. | PASS | -- |
| 15 | DTO: EndResponse.message_count | int | Gleich wie DB-Feld (INTEGER) | PASS | -- |

**Data Type Ergebnis:** 15/15 PASS -- Alle Datentypen sind realistisch gewaehlt und evidenz-basiert validiert.

---

## D) External Dependencies

| Dependency | Rate Limits | Auth | Error Handling | Timeout | Status |
|------------|-------------|------|---------------|---------|--------|
| OpenRouter API | Risks: "Retry-Logic im Graph (1x)". Kein konkretes Rate Limit noetig fuer MVP (1 concurrent Interview). | OPENROUTER_API_KEY via .env | LLM Error -> 502, SSE error event, Session bleibt offen | LLM_TIMEOUT_SECONDS=30 (Constraints + Config) | PASS |
| Supabase (PostgreSQL) | Free Tier: 500MB Storage, unbegrenzte API Calls. Fuer MVP ausreichend. | SUPABASE_URL + SUPABASE_KEY via .env | Try/Except + Retry im Repository, 500 an Client | DB_TIMEOUT_SECONDS=10 (Constraints + Config) | PASS |
| LangSmith | Fire-and-forget Tracing, kein Rate Limit relevant | LANGSMITH_API_KEY via .env | Kein Error Handling noetig (async, non-blocking) | n/a (async) | PASS |
| LangGraph MemorySaver | n/a (In-Memory) | n/a | Memory Leak Mitigation dokumentiert (Sessions nach Completion entfernen) | n/a | PASS |
| sse-starlette | n/a (Library) | n/a | n/a | n/a | PASS |

**Dependencies Ergebnis:** 5/5 PASS -- Alle externen Abhaengigkeiten sind vollstaendig dokumentiert mit Auth, Error Handling und Timeouts.

---

## E) Completeness Check -- Architecture Template Sections

| Section | Vorhanden | Vollstaendig | Status |
|---------|-----------|-------------|--------|
| Problem & Solution | Ja | Ja, 1:1 mit Discovery | PASS |
| Scope & Boundaries | Ja | Ja, 14 In-Scope + 7 Out-of-Scope Items | PASS |
| API Design (Overview) | Ja | Style, Auth, Rate Limiting, Base Path, Content-Types | PASS |
| API Design (Endpoints) | Ja | 4 Endpoints mit DTOs, Response, Auth, Business Logic | PASS |
| API Design (DTOs) | Ja | 5 DTOs mit Fields und Validation | PASS |
| API Design (SSE Format) | Ja | 4 Event Types mit Payload und Wire Format | PASS |
| Database Schema (Entities) | Ja | 1 Table mit Purpose und Key Fields | PASS |
| Database Schema (Details) | Ja | 10 Columns mit Type, Constraints, Index, Notes | PASS |
| Database Schema (SQL Migration) | Ja | Vollstaendiges CREATE TABLE + 3 Indexes | PASS |
| Server Logic (Services) | Ja | 6 Services mit Responsibility, Input, Output, Side Effects | PASS |
| Server Logic (Business Flow) | Ja | 4 Flows (/start, /message, /end, Timeout) mit Pseudo-Code | PASS |
| Server Logic (Validation Rules) | Ja | 6 Rules mit Field, Rule, Error Code, Message | PASS |
| Security (Auth) | Ja | 3 Areas dokumentiert | PASS |
| Security (Data Protection) | Ja | 3 Data Types dokumentiert | PASS |
| Security (Input Validation) | Ja | 3 Inputs mit Validation und Sanitization | PASS |
| Security (Rate Limiting) | Ja | Explizit "Kein Rate Limiting in MVP" | PASS |
| Architecture Layers (Ordnerstruktur) | Ja | Vollstaendige Datei-fuer-Datei Auflistung (19 Dateien) | PASS |
| Architecture Layers (Responsibilities) | Ja | 8 Layer mit Pattern und Beispiel | PASS |
| Architecture Layers (Data Flow) | Ja | ASCII-Diagramm mit allen Komponenten | PASS |
| Architecture Layers (Error Handling) | Ja | 7 Error Types mit HTTP Code, Handling, Response, Logging | PASS |
| Constraints & Integrations | Ja | 9 Constraints (inkl. LLM/DB Timeouts + Supabase ENV Fix) + 6 Integrations | PASS |
| Quality Attributes (NFRs) | Ja | 5 Attributes mit Target und Measure | PASS |
| Monitoring & Observability | Ja | 4 Metrics | PASS |
| Risks & Assumptions | Ja | 5 Assumptions + 5 Risks mit Mitigation | PASS |
| Technology Decisions | Ja | 9 Stack Choices + 5 Trade-offs | PASS |
| Open Questions | Ja | Alle geklaert ("Alle Fragen geklaert") | PASS |

**Completeness Ergebnis:** 26/26 PASS -- Alle Template-Sections sind vorhanden und vollstaendig.

---

## Blocking Issues

Keine.

---

## Recommendations

1. **[Implementation]** `.env.example` muss bei Slice 1 angepasst werden: `DATABASE_URL` ersetzen durch `SUPABASE_URL` + `SUPABASE_KEY` (Architecture dokumentiert dies bereits in Constraints Zeile 362).
2. **[Implementation]** `widget/package.json` hat aktuell `ai` (^4.0.0) und `@ai-sdk/react` (^1.0.0) -- Entfernung ist als Slice 1 Aufgabe geplant.

---

## Verdict

**Status:** APPROVED

**Blocking Issues:** 0
**Warnings:** 0

**Checks durchgefuehrt:**
- Feature Mapping: 16/16 PASS
- Constraint Mapping: 25/25 PASS
- Data Type Verdicts: 15/15 PASS
- External Dependencies: 5/5 PASS
- Template Completeness: 26/26 PASS
- Previous Blocking Issues: 3/3 FIXED

**Total:** 70 PASS, 0 BLOCKING

**Next Steps:**
- Architecture ist bereit fuer Implementation
- Slice 1 (App-Skeleton + DDD-Struktur) kann beginnen

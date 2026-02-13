# Feature: Phase 1 -- Backend-Kern

**Epic:** FeedbackAI MVP
**Status:** Draft
**Wireframes:** n/a (Backend-only, kein UI)

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
| SSE-Streaming (einfaches Format, kompatibel mit assistant-ui LocalRuntime) |
| API Endpoints: POST /api/interview/start, POST /api/interview/message (SSE), POST /api/interview/end |
| MemorySaver fuer In-Session Conversation-Persistenz |
| Summary-Generierung am Interview-Ende (separater LLM-Call, Bullet-Liste) |
| Auto-Summary bei Session-Timeout (SESSION_TIMEOUT_SECONDS aus .env) |
| Summary-Injection: Letzte 3 Summaries des Users in System-Prompt |
| Supabase: interviews-Tabelle (Transkript, Summary, Status) |
| Anonyme User-Identifikation (anonymous_id vom Client, localStorage) |
| OpenRouter als LLM-Provider (Claude Sonnet 4.5) |
| Widget package.json bereinigen: `ai` und `@ai-sdk/react` entfernen |
| DDD-Domaenen-Architektur dokumentieren und im Code strukturieren |
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

## DDD-Domaenen-Architektur

### Bounded Contexts

| Domaene | Verantwortung | Phase |
|---------|---------------|-------|
| **Interview** | Gespraechsfuehrung, LangGraph, Prompt-Assembly, Streaming | MVP (Phase 1) |
| **Insights** | Summary-Generierung, Fact-Extraction, Clustering | MVP (Summary) + spaeter |
| **Configuration** | Company/Product/Scenario-Kontexte, Prompt-Templates | MVP (hardcoded) + Phase 6 |
| **Delivery** | Widget, Email-Links, Voice-Channels | Phase 2+ |
| **Identity** | Anonyme User-IDs, spaeter Auth/Tokens | MVP (anonym) + Phase 7 |

### Ordnerstruktur (Ziel)

```
backend/
  app/
    interview/       # Interview-Domaene
      graph.py       # LangGraph StateGraph
      nodes.py       # Interviewer-Node, Summary-Node
      state.py       # State-Definition
      prompt.py      # Prompt-Assembly (System-Prompt + Context-Injection)
    insights/        # Insights-Domaene
      summary.py     # Summary-Generierung
    config/          # Configuration-Domaene
      context/       # Company/Product/Scenario JSONs
      settings.py    # App-Config (.env)
    api/             # API-Layer (nicht Domaene, sondern Transport)
      routes.py      # FastAPI Endpoints
      schemas.py     # Request/Response Models
    db/              # Persistenz-Layer
      supabase.py    # Supabase Client
      models.py      # DB-Models
    main.py          # FastAPI App, CORS, Lifespan
```

### Domaenen-Grenzen in Phase 1

- **Interview** ruft **Insights** (Summary) auf nach Gespraechsende
- **Interview** liest **Configuration** (Prompt, Context)
- **API** orchestriert **Interview** und **Identity**
- **DB** wird von **Interview** (Transkript), **Insights** (Summary), **Identity** (anonymous_id) genutzt

---

## User Flow

> "User" = Carrier, der das Interview durchfuehrt. In Phase 1 via curl simuliert.

### Happy Path

1. Client sendet `POST /api/interview/start` mit `anonymous_id` → Backend erstellt Session, laedt letzte 3 Summaries, assembliert System-Prompt, gibt `session_id` + Opening-Frage (SSE) zurueck
2. Client sendet `POST /api/interview/message` mit `session_id` + User-Nachricht → Backend fuegt Nachricht zur History, ruft LangGraph auf, streamt Interviewer-Antwort via SSE
3. Schritte 2 wiederholt sich beliebig oft (kein Limit, user-gesteuert)
4. Client sendet `POST /api/interview/end` mit `session_id` → Backend generiert Summary (Bullet-Liste), speichert Transkript + Summary in Supabase, gibt Summary zurueck
5. Interview ist abgeschlossen, Session-Status = "completed"

### Error Paths

- **Timeout (User verschwindet):** Nach `SESSION_TIMEOUT_SECONDS` Inaktivitaet → Auto-Summary generieren, Session als "completed_timeout" markieren, in Supabase speichern
- **LLM-Fehler:** OpenRouter nicht erreichbar → Fehler an Client melden, Session bleibt offen, User kann es nochmal versuchen
- **Ungueltige session_id:** → 404, "Session not found"
- **Leere Nachricht:** → 400, "Message cannot be empty"
- **Session bereits beendet:** → 409, "Session already completed"

---

## UI Layout & Context

Kein UI in Phase 1. Interaktion via curl oder HTTP-Client.

### curl-Beispiel-Flow

```
# 1. Start
curl -X POST http://localhost:8000/api/interview/start \
  -H "Content-Type: application/json" \
  -d '{"anonymous_id": "test-user-1"}'

# 2. Message (SSE)
curl -N -X POST http://localhost:8000/api/interview/message \
  -H "Content-Type: application/json" \
  -d '{"session_id": "...", "message": "Das Bidding ist frustrierend"}'

# 3. End
curl -X POST http://localhost:8000/api/interview/end \
  -H "Content-Type: application/json" \
  -d '{"session_id": "..."}'
```

---

## UI Components & States

n/a (Backend-only Phase)

---

## Feature State Machine

### States Overview

| State | Beschreibung | Verfuegbare Actions |
|-------|-------------|---------------------|
| `idle` | Kein aktives Interview fuer diesen User | Start |
| `active` | Interview laeuft, wartet auf User-Nachricht | Message, End |
| `streaming` | Interviewer generiert Antwort (SSE laeuft) | Warten (Client empfaengt Chunks) |
| `summarizing` | Summary wird generiert (nach End oder Timeout) | Warten |
| `completed` | Interview abgeschlossen, Summary gespeichert | Neues Interview starten |
| `completed_timeout` | Interview durch Timeout beendet, Auto-Summary | Neues Interview starten |
| `error` | LLM-Fehler oder anderer Fehler | Retry (Message nochmal senden) |

### Transitions

| Current State | Trigger | Next State | Business Rules |
|---------------|---------|------------|----------------|
| `idle` | `POST /start` | `active` | Letzte 3 Summaries des anonymous_id laden und in Prompt injizieren |
| `active` | `POST /message` | `streaming` | Nachricht darf nicht leer sein |
| `streaming` | SSE complete | `active` | Interviewer-Antwort + User-Nachricht in History gespeichert |
| `streaming` | LLM error | `error` | Fehlermeldung an Client |
| `active` | `POST /end` | `summarizing` | User beendet Interview explizit |
| `active` | Timeout (SESSION_TIMEOUT_SECONDS) | `summarizing` | Auto-End, kein Client-Request noetig |
| `summarizing` | Summary fertig | `completed` / `completed_timeout` | Transkript + Summary in Supabase INSERT |
| `error` | `POST /message` (retry) | `streaming` | Gleiche Nachricht nochmal verarbeiten |

---

## Business Rules

- Interview hat kein automatisches Ende / Message-Limit -- rein user-gesteuert
- Jede Session gehoert zu einem `anonymous_id` (vom Client mitgegeben)
- Beim Start werden die letzten 3 Summaries des `anonymous_id` aus Supabase geladen
- Summaries werden als Kontext in den System-Prompt injiziert (nach dem statischen Teil)
- Summary-Format: Freie Bullet-Liste mit den wichtigsten Erkenntnissen/Facts
- Session-Timeout: Konfigurierbar via `SESSION_TIMEOUT_SECONDS` (.env, Default: 60s)
- Bei Timeout: Auto-Summary generieren, Session als `completed_timeout` markieren
- LLM-Provider: OpenRouter, Modell konfigurierbar via `INTERVIEWER_LLM` (.env)
- LangSmith-Tracing ist standardmaessig aktiv (konfiguriert in .env)
- Hardcoded Prompt fuer MVP (Carrier View + Pain Point Discovery)
- MemorySaver haelt Conversation-State in-memory waehrend der Session
- Supabase speichert fertige Interviews (Transkript, Summary, Status, Timestamps)

---

## Data

### Supabase: `interviews` Tabelle

| Field | Required | Validation | Notes |
|-------|----------|------------|-------|
| `id` | Yes | UUID, auto-generated | Primary Key |
| `anonymous_id` | Yes | String, nicht leer | Vom Client, localStorage-basiert |
| `session_id` | Yes | UUID, auto-generated | LangGraph thread_id |
| `status` | Yes | enum: active, completed, completed_timeout | Session-Status |
| `transcript` | No | JSON (Message-Array) | Null waehrend active, gefuellt bei completed |
| `summary` | No | Text (Bullet-Liste) | Null waehrend active, gefuellt bei completed |
| `message_count` | Yes | Integer >= 0 | Anzahl User-Nachrichten |
| `created_at` | Yes | Timestamp, auto | Session-Start |
| `updated_at` | Yes | Timestamp, auto | Letzte Aktivitaet |
| `completed_at` | No | Timestamp | Null waehrend active |

### API Request/Response Schemas

**POST /api/interview/start**
- Request: `{ anonymous_id: string }`
- Response (SSE): Opening-Frage gestreamt, dann `{ session_id: string }` als abschliessendes Event

**POST /api/interview/message**
- Request: `{ session_id: string, message: string }`
- Response (SSE): Interviewer-Antwort gestreamt

**POST /api/interview/end**
- Request: `{ session_id: string }`
- Response: `{ summary: string, message_count: number }`

### SSE-Format (einfach)

```
data: {"type": "text-delta", "content": "Chunk..."}\n\n
data: {"type": "text-done"}\n\n
data: {"type": "metadata", "session_id": "..."}\n\n
```

### Environment Variables

| Variable | Required | Default | Notes |
|----------|----------|---------|-------|
| `OPENROUTER_API_KEY` | Yes | – | OpenRouter API Key |
| `INTERVIEWER_LLM` | Yes | anthropic/claude-sonnet-4.5 | LLM-Modell |
| `INTERVIEWER_TEMPERATURE` | No | 1 | LLM Temperature |
| `INTERVIEWER_MAX_TOKENS` | No | 4000 | Max Tokens pro Antwort |
| `SESSION_TIMEOUT_SECONDS` | No | 60 | Timeout fuer Auto-Summary |
| `DATABASE_URL` | Yes | – | Supabase PostgreSQL Connection String |
| `LANGSMITH_API_KEY` | No | – | LangSmith Tracing |
| `LANGSMITH_PROJECT` | No | FeedbackAI | LangSmith Projekt-Name |

---

## Implementation Slices

### Dependencies

```
Slice 1 → Slice 2 → Slice 3 → Slice 4 → Slice 5
                                  ↓
                              Slice 6
```

### Slices

| # | Name | Scope | Testbarkeit | Abhaengigkeiten |
|---|------|-------|-------------|-----------------|
| 1 | App-Skeleton + DDD-Struktur | FastAPI main.py, Config, CORS, Health-Check, DDD-Ordnerstruktur, Widget package.json Cleanup | `curl localhost:8000/health` → 200 | – |
| 2 | LangGraph Interview-Graph | StateGraph, Interviewer-Node, MemorySaver, Prompt-Assembly (hardcoded) | Unit-Test: Graph aufrufen, Antwort erhalten | Slice 1 |
| 3 | SSE-Streaming Endpoints | POST /start (SSE), POST /message (SSE), POST /end, SSE-Format | `curl -N` → Chunks kommen gestreamt | Slice 2 |
| 4 | Supabase-Persistenz | interviews-Tabelle, Insert bei Session-End, Summary-Loading fuer Injection | Interview beenden → Row in Supabase pruefen | Slice 3 |
| 5 | Summary-Generierung + Injection | Separater LLM-Call fuer Bullet-Summary, Injection der letzten 3 Summaries in Prompt | Start mit User der vorherige Session hat → Prompt enthaelt alte Summaries | Slice 4 |
| 6 | Session-Timeout + Auto-Summary | Timeout-Mechanismus, automatische Summary bei Inaktivitaet | Session starten, warten, pruefen ob Auto-Summary in DB | Slice 5 |

### Empfohlene Reihenfolge

1. **Slice 1: App-Skeleton + DDD-Struktur** – Grundgeruest, alles baut darauf auf
2. **Slice 2: LangGraph Interview-Graph** – Der Kern-Wert, hier entsteht das Interview
3. **Slice 3: SSE-Streaming Endpoints** – Macht den Graph per HTTP erreichbar
4. **Slice 4: Supabase-Persistenz** – Interviews werden gespeichert
5. **Slice 5: Summary + Injection** – Session-uebergreifender Kontext
6. **Slice 6: Session-Timeout** – Robustheit, kein verlorenes Feedback

---

## Context & Research

### Similar Patterns in Codebase

| Feature | Location | Relevant because |
|---------|----------|------------------|
| Hardcoded MVP Prompt | `backend/app/graph/prompt.py` | Wird direkt in Slice 2 genutzt |
| Template Prompt | `backend/app/graph/prompt_interviewer_original.md` | Zeigt Platzhalter-Struktur fuer spaeter (Phase 6) |
| Context-JSONs | `backend/app/context/*.json` | Nicht in Phase 1 genutzt (hardcoded), aber Struktur fuer Phase 6 |

### Web Research

| Source | Finding |
|--------|---------|
| LangGraph Docs | StateGraph + `add_messages` Reducer + MemorySaver ist Standard-Pattern fuer Multi-Turn Conversations |
| Vercel AI SDK Docs | Data Stream Protocol mit `text-delta`, `text-done` Events. Nicht noetig -- assistant-ui kann direkt mit custom SSE arbeiten |
| assistant-ui Docs | `LocalRuntime` mit `ChatModelAdapter` ist die beste Option fuer custom Backends. `ai` und `@ai-sdk/react` nicht noetig |
| assistant-ui Docs | `useDataStreamRuntime` existiert als Alternative, erfordert aber spezifisches Protokoll |

---

## Open Questions

| # | Question | Options | Recommended | Decision |
|---|----------|---------|-------------|----------|
| 1 | SSE-Format: Eigenes simples Format oder Data Stream Protocol? | A) Eigenes Format B) Data Stream Protocol | A) Eigenes simples Format -- weniger Overhead, volle Kontrolle | Offen (Architecture-Phase) |
| 2 | Timeout-Mechanismus: Background-Task oder Middleware? | A) asyncio.Task B) Celery/Background Worker C) Middleware | A) asyncio.Task -- einfach, reicht fuer MVP | Offen (Architecture-Phase) |

---

## Research Log

| Date | Area | Finding |
|------|------|---------|
| 2026-02-13 | Codebase | Prompt existiert hardcoded (prompt.py) und als Template (prompt_interviewer_original.md) |
| 2026-02-13 | Codebase | .env.example zeigt OpenRouter, LangSmith, Supabase, Session-Timeout konfiguriert |
| 2026-02-13 | Web | LangGraph: StateGraph + add_messages + MemorySaver ist Standard-Pattern |
| 2026-02-13 | Web | Vercel AI SDK ist fuer Next.js optimiert, kein Mehrwert fuer FastAPI |
| 2026-02-13 | Web | assistant-ui: LocalRuntime mit ChatModelAdapter ist die beste Option fuer custom Backends |
| 2026-02-13 | Web | ai und @ai-sdk/react koennen entfernt werden -- assistant-ui ist eigenstaendig |

---

## Q&A Log

| # | Frage | Antwort |
|---|-------|---------|
| 1 | Welche Discovery-Tiefe fuer Phase 1? | Detailliert -- alle Edge Cases, Error Handling, Prompt-Strategie |
| 2 | Interview-Ende: Wie wird beendet? | Ausschliesslich gespraechsgesteuert. Kein automatisches Ende, kein Message-Limit. Chat ist immer auf Empfang. |
| 3 | Streaming: SSE von Anfang an oder erst JSON? | Gleich SSE -- spart Umbau in Phase 3 |
| 4 | Session-Kontext: Wie weiss der Interviewer ueber vorherige Sessions Bescheid? | Neue Session jedes Mal, aber letzte 3 Summaries werden in den Prompt injiziert |
| 5 | Braucht Vercel AI SDK einen Mehrwert neben assistant-ui? | Nein -- assistant-ui ist eigenstaendig. ai und @ai-sdk/react koennen entfernt werden |
| 6 | Summary-Format? | Freie Bullet-Liste mit den wichtigsten Facts/Erkenntnissen |
| 7 | Widget-Paketbereinigung in Phase 1? | Ja, als Teil von Slice 1 |
| 8 | Supabase schon in Phase 1? | Ja -- Summary-Injection braucht gespeicherte Summaries |
| 9 | LLM-Provider? | OpenRouter (Claude Sonnet 4.5) |
| 10 | Consent im Backend? | Nein -- Website-Datenschutzerklaerung regelt das |
| 11 | DDD-Domaenen-Architektur in Phase 1? | Ja, 5 Domaenen: Interview, Insights, Configuration, Delivery, Identity |
| 12 | Architektur-Doku wo? | In der Discovery (diese Datei) |
| 13 | User-Identifikation ueber Sessions? | Anonyme Session-ID (anonymous_id), im localStorage des Clients gespeichert |
| 14 | Wie viele vorherige Summaries injizieren? | Letzte 3 |
| 15 | Was bei Timeout (User verschwindet)? | Auto-Summary generieren, Session als completed_timeout markieren |
| 16 | Phase 1 soll komplette App-Architektur vorplanen inkl. DDD? | Ja, Domaenen-Struktur wird in Phase 1 angelegt |

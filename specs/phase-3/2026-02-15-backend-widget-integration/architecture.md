# Feature: Backend-Widget-Integration (SSE-Streaming-Bridge)

**Epic:** Phase 3 -- Backend-Widget-Integration
**Status:** Ready
**Discovery:** `discovery.md` (same folder)
**Derived from:** Discovery constraints, NFRs, and risks

---

## Problem & Solution

**Problem:**
- Backend (Phase 1) und Widget (Phase 2) existieren, können aber nicht kommunizieren
- Kein Ende-zu-Ende Interview-Flow möglich
- User kann Widget öffnen, aber kein echtes Interview durchführen
- @assistant-ui hat nur Dummy-Adapter ohne Backend-Anbindung

**Solution:**
- SSE-Streaming-Bridge zwischen Widget und Backend implementieren
- Fetch API mit ReadableStream für POST-basierte SSE-Endpoints
- ChatModelAdapter ersetzt Dummy-Implementation mit echten Backend-Calls
- E2E-Flow: Consent → Live-Interview → Summary → ThankYou

**Business Value:**
- Erstes funktionierendes MVP: Carrier können echte Feedback-Interviews durchführen
- Validierung der Interview-Qualität mit echten Usern
- Foundation für alle weiteren Phasen (Demo-Site, Voice, Dashboard)

---

## Scope & Boundaries

| In Scope |
|----------|
| Anonymous-ID Generierung (UUID v4) + localStorage Persistenz |
| SSE-Client mit Fetch API für `/api/interview/start` (POST mit Body) |
| SSE-Client mit Fetch API für `/api/interview/message` (POST mit Body) |
| Interview-Ende API-Call `/api/interview/end` (JSON Response) |
| ChatModelAdapter Implementation für @assistant-ui/react |
| Session-ID Management (React State useRef, Memory-only) |
| Assistant-Message Rendering (left-aligned, grey bubble, streaming) |
| Loading-Indicator ("Verbinde...") während /start |
| Typing-Indicator (animierte Punkte) während Assistant streamt |
| Error-Handling: Network, Timeout, SessionExpired, ServerError |
| Error-Display mit Retry-Buttons |
| Composer disabled während Streaming |
| Auto-End bei Panel-Close (während aktiver Session) |
| Stream-Cleanup bei Panel-Close |
| ThankYou-Screen mit Auto-Close (5s) nach Interview-Ende |

| Out of Scope |
|--------------|
| Chat-History Persistenz (localStorage) -- nur Memory |
| Session-Persistenz über Page-Reload -- Session verloren |
| Expliziter "Beenden"-Button -- automatisch bei Panel-Close |
| User kann während Streaming schreiben -- Composer disabled |
| Markdown-Rendering in Messages -- nur Plain-Text |
| Demo-Site (Phase 4) |
| Voice-Interface (Phase 5+) |
| Dashboard für Admins (Phase 5+) |
| Shadow DOM Isolation (später) |
| WebSocket als Alternative zu SSE |

---

## API Design

### Overview

| Aspect | Specification |
|--------|---------------|
| Style | REST (Backend Phase 1 bereits implementiert) |
| Authentication | None (Anonymous Interviews) |
| Rate Limiting | None (MVP) |

### Endpoints (Backend bereits implementiert)

| Method | Path | Request | Response | Auth | Business Logic |
|--------|------|---------|----------|------|----------------|
| POST | `/api/interview/start` | `{anonymous_id: string}` | SSE Stream (metadata, text-delta, text-done, error) | None | Creates session, streams opening question |
| POST | `/api/interview/message` | `{session_id: string, message: string}` | SSE Stream (text-delta, text-done, error) | None | Validates session, streams LLM response |
| POST | `/api/interview/end` | `{session_id: string}` | JSON `{summary: string, message_count: number}` | None | Ends session, returns summary |

### Frontend API Abstraction Layer (NEW)

**New TypeScript Module:** `widget/src/lib/api-client.ts`

| Function | Purpose | Input | Output | Side Effects |
|----------|---------|-------|--------|--------------|
| `startInterview()` | Calls /start, streams response | `anonymous_id: string` | `AsyncGenerator<SSEEvent>` | Stores session_id in React State |
| `sendMessage()` | Calls /message, streams response | `session_id: string, message: string` | `AsyncGenerator<SSEEvent>` | None |
| `endInterview()` | Calls /end, returns summary | `session_id: string` | `Promise<{summary: string, message_count: number}>` | Clears session_id |
| `parseSSE()` | Parses SSE format | `line: string` | `SSEEvent \| null` | None |

### SSE Event Types (Frontend Interface)

```typescript
type SSEEvent =
  | { type: 'metadata'; session_id: string }
  | { type: 'text-delta'; content: string }
  | { type: 'text-done' }
  | { type: 'error'; message: string }
```

### Data Transfer Objects (DTOs)

| DTO | Fields | Validation | Notes |
|-----|--------|------------|-------|
| `StartRequest` | `anonymous_id: string` | 1-255 chars, whitespace stripped | Backend validates (Pydantic) |
| `MessageRequest` | `session_id: string, message: string` | session_id: UUID format, message: 1-10000 chars | Backend validates (Pydantic) |
| `EndRequest` | `session_id: string` | UUID format | Backend validates (Pydantic) |
| `EndResponse` | `summary: string, message_count: number` | Backend generates | JSON Response |
| `ErrorResponse` | `error: string, detail?: string` | Backend generates | JSON Response (404, 409, 422) |

---

## Database Schema

**No new schema required.** Backend (Phase 1) bereits mit Supabase-Schema:

| Table | Purpose | Key Fields |
|-------|---------|------------|
| `interviews` | Stores session metadata + transcript | `session_id` (PK), `anonymous_id`, `status`, `transcript` (JSONB), `summary` |
| `summaries` | Stores generated summaries | `id` (PK), `anonymous_id`, `summary`, `message_count` |

**Widget Impact:** None. Frontend greift nur via API zu, keine direkten DB-Calls.

---

## Server Logic

**Frontend-Side Logic (NEW in Widget):**

### Services & Processing

| Service | Responsibility | Input | Output | Side Effects |
|---------|----------------|-------|--------|--------------|
| `AnonymousIDManager` | Generate/Store UUID v4 | None (first call) | `anonymous_id: string` | `localStorage.setItem('feedbackai_anonymous_id', uuid)` |
| `SSEStreamReader` | Fetch API Stream-Reader | `Response.body: ReadableStream` | `AsyncGenerator<SSEEvent>` | Parses SSE line-by-line |
| `ChatModelAdapter` | @assistant-ui Integration | `messages, abortSignal, context` | `AsyncGenerator<{content: [{type:"text", text}]}>` | Calls API-Client, transforms SSE → @assistant-ui format |
| `SessionManager` | Session-ID Storage | `session_id: string` | Stored in `useRef` | None (Memory-only) |
| `ErrorHandler` | Classify & Display Errors | `Error \| HTTP Status` | `ErrorDisplayProps` | Sets error state in reducer |

### Business Logic Flow

```
[User clicks "Los geht's"]
       ↓
[Anonymous-ID generated/loaded from localStorage]
       ↓
[State: GO_TO_CHAT + CONNECTING]
       ↓
[ChatModelAdapter.run() called by @assistant-ui]
       ↓
[startInterview(anonymous_id) → Fetch POST /start]
       ↓
[SSE Stream: metadata → session_id stored]
       ↓
[SSE Stream: text-delta → yield to @assistant-ui → UI updates]
       ↓
[SSE Stream: text-done → Composer enabled]
       ↓
[User types message, clicks Send]
       ↓
[ChatModelAdapter.run() called with new message]
       ↓
[sendMessage(session_id, message) → Fetch POST /message]
       ↓
[SSE Stream: text-delta → yield to @assistant-ui → UI updates]
       ↓
[Repeat 3-10x]
       ↓
[User closes Panel → /end called]
       ↓
[endInterview(session_id) → Fetch POST /end → JSON]
       ↓
[State: GO_TO_THANKYOU → 5s timer → CLOSE_AND_RESET]
```

### Validation Rules

| Field | Rule | Error Message |
|-------|------|---------------|
| `anonymous_id` | UUID v4 format (regex) | "Invalid anonymous_id format" |
| `session_id` | UUID format (regex) | "Invalid session_id format" |
| `message` | 1-10000 chars | "Message too long (max 10,000 characters)" |
| `apiUrl` | Valid URL (new URL()) | "Configuration error. Invalid API URL." |

---

## Security

### Authentication & Authorization

| Area | Mechanism | Notes |
|------|-----------|-------|
| API Auth | None (Anonymous) | No login, no tokens, no auth headers |
| Resource Access | Public endpoints | No RLS, no ACL (MVP) |
| Future | JWT for Admin Dashboard | Out of scope for Phase 3 |

### Data Protection

| Data Type | Protection | Notes |
|-----------|------------|-------|
| Anonymous-ID | Persistent in localStorage | Pseudo-anonymous, not linked to real identity |
| Session-ID | Memory-only (React State useRef) | Lost on page reload, DSGVO-friendly |
| Transcript | Backend-side only (Supabase) | Not exposed to frontend |
| Messages | Transient (only in API request) | Not stored in frontend |

### Input Validation & Sanitization

| Input | Validation | Sanitization |
|-------|------------|--------------|
| `anonymous_id` | UUID v4 format (regex), 1-255 chars | Whitespace stripped (backend) |
| `session_id` | UUID format (regex) | None |
| `message` | 1-10000 chars | Whitespace trimmed (frontend), no XSS (plain-text only) |
| `apiUrl` | Valid URL (new URL()) | None |

### Rate Limiting & Abuse Prevention

| Resource | Limit | Window | Penalty |
|----------|-------|--------|---------|
| None (MVP) | - | - | - |

**Rationale:** MVP hat keine Rate-Limits. Backend (Phase 1) bereits mit Session-Timeout (60s) als Spam-Prevention.

---

## Architecture Layers

### Layer Responsibilities

| Layer | Responsibility | Pattern |
|-------|----------------|---------|
| **Components** | UI-Rendering (Screens, Messages, Indicators) | React Functional Components |
| **Hooks** | State-Management, Side-Effects | `useReducer`, `useRef`, `useEffect` |
| **Services** | API-Calls, SSE-Parsing, Storage | Async Functions (api-client.ts) |
| **Adapters** | @assistant-ui Integration | ChatModelAdapter (async generator) |
| **Utils** | Anonymous-ID, Validation, Parsing | Pure Functions |

### Data Flow

```
[User Action] → [Component] → [useReducer dispatch]
                                   ↓
                            [State Update]
                                   ↓
                    [useEffect triggers Side-Effect]
                                   ↓
            [ChatModelAdapter.run() called by @assistant-ui]
                                   ↓
                    [API-Client (Fetch + SSE)]
                                   ↓
                      [Backend SSE Stream]
                                   ↓
              [AsyncGenerator yields to @assistant-ui]
                                   ↓
                    [@assistant-ui updates Thread]
                                   ↓
                          [Component re-renders]
```

### Error Handling Strategy

| Error Type | Handling | User Response | Logging |
|------------|----------|---------------|---------|
| **Network Failure** | Catch fetch() error → ERROR state | "Verbindung fehlgeschlagen. Bitte Netzwerk prüfen." + Retry-Button | console.error() |
| **Timeout** | AbortSignal timeout → ERROR state | "Zeitüberschreitung. Server antwortet nicht." + Retry-Button | console.error() |
| **Session Expired (404)** | Catch 404 → ERROR state | "Sitzung abgelaufen." + "Neu starten"-Button → Consent | console.warn() |
| **Session Completed (409)** | Catch 409 → GO_TO_THANKYOU | "Interview bereits beendet." → ThankYou-Screen | console.info() |
| **Stream Abort** | ReadableStream closed → ERROR state | "Verbindung unterbrochen." + Partial message visible + Retry-Button | console.warn() |
| **SSE Error Event** | Parse `{"type":"error"}` → ERROR state | Backend-Message anzeigen + "Neu starten"-Button | console.error() |
| **Config Error** | parseConfig() throws → Console-Error | "Konfigurationsfehler. Bitte Administrator kontaktieren." | console.error() |
| **Invalid JSON (SSE)** | JSON.parse() throws → ERROR state | "Datenformat-Fehler." + Retry-Button | console.error() |

---

## Constraints & Integrations

### Constraints (From Discovery)

| Constraint | Technical Implication | Solution |
|------------|----------------------|----------|
| **Backend nutzt POST-Endpoints** | EventSource unterstützt nur GET | **Fetch API mit ReadableStream** für manuelles SSE-Parsing |
| **SSE-Format: `data: {...}\n\n`** | Manuelles Line-Parsing erforderlich | Custom SSE-Parser: Split by `\n\n`, parse `data:` prefix |
| **Session timeout 60s** | Frontend muss 404-Error als "Session expired" behandeln | Error-Display mit "Neu starten"-Button |
| **@assistant-ui erwartet async generator** | Adapter muss SSE-Events transformieren | `yield { content: [{ type: "text", text }] }` |
| **Phase 2 Dummy-Adapter** | Ersetzung ohne Breaking Changes | Same Interface, nur Implementierung getauscht |
| **IIFE-Build (Phase 2)** | Kein Dynamic Import, alles in widget.js | API-Client als ES-Module, gebundled von Vite |

### Integrations

| Area | System / Capability | Interface | Notes |
|------|----------------------|-----------|-------|
| **@assistant-ui/react** | Chat-UI Primitives + Runtime | `useLocalRuntime(adapter)` | Version: Latest (npm) |
| **Fetch API** | Native Browser API | `fetch(url, {method, body, signal})` | AbortController für cleanup |
| **ReadableStream** | Native Streaming API | `response.body.getReader()` | Chrome/Firefox/Safari support |
| **localStorage** | Native Browser Storage | `localStorage.setItem/getItem` | Key: `feedbackai_anonymous_id` |
| **crypto.randomUUID()** | Native UUID Generator | `crypto.randomUUID()` | Browser support: Modern browsers (2021+) |

---

## Quality Attributes (NFRs)

### From Discovery → Technical Solution

| Attribute | Target (from Discovery) | Technical Approach | Measure / Verify |
|-----------|-------------------------|--------------------|------------------|
| **User Perceived Latency** | < 2s für erste LLM-Antwort | SSE-Streaming (token-by-token), Loading-Indicator | Manueller Test: Time from Consent-Click to first text-delta |
| **Progressive Rendering** | Text erscheint ohne Verzögerung | Streaming mit append (kein Re-Mount), `key={message.id}` stabil | Visual Test: Kein Flackern, smooth append |
| **Error Recovery** | User kann bei Network-Fehler fortsetzen | Retry-Button, Session bleibt aktiv (Timeout 60s) | Test: Disable Network → Enable → Retry → Interview fortsetzt |
| **Memory Leaks Prevention** | Keine Zombie-Requests bei Panel-Close | AbortController cleanup in useEffect | Test: Open/Close Panel 50x, Chrome DevTools Memory-Profile |
| **Accessibility** | Keyboard-Navigation | Tab-Focus für alle Buttons, Enter für Send | Manual Test: Tab-Navigation, Screen-Reader |
| **Mobile UX** | Touch-Friendly, Fullscreen | Fullscreen Panel auf Mobile (Phase 2), Touch-Target ≥ 44px | Test: iOS Safari, Android Chrome |

### Monitoring & Observability

| Metric | Type | Target | Alert |
|--------|------|--------|-------|
| `api_call_duration` | Histogram | < 30s für /start, < 20s für /message | console.warn() if > 30s |
| `sse_stream_errors` | Counter | < 5% Error-Rate | console.error() with stack trace |
| `session_expired_rate` | Counter | - | Track 404 errors |

**Note:** MVP hat keine Backend-Metrics. Frontend-only console.log() für Debugging.

---

## Risks & Assumptions

### Assumptions (From Discovery)

| Assumption | Technical Validation | Impact if Wrong |
|------------|---------------------|-----------------|
| **Backend-APIs sind stabil** | Phase 1 Tests grün | Wenn instabil: Häufige 500-Errors, User-Frustration |
| **CORS erlaubt Widget-Zugriff** | Backend-Config: `allow_origins=["*"]` | Wenn nicht: Fetch blocked by Browser, keine Connection |
| **Browser unterstützt Fetch/ReadableStream** | Modern Browsers (2021+) | Wenn nicht: Polyfill oder Fallback auf EventSource (nur GET) |
| **Anonymous-ID ist eindeutig** | UUID v4 = 122 bit entropy | Wenn Collision: Backend-Logik (nicht Frontend-Concern) |

### Risks & Mitigation

| Risk | Likelihood | Impact | Technical Mitigation | Fallback |
|------|------------|--------|---------------------|----------|
| **SSE-Stream bricht ab** | Medium | High | AbortController + Retry-Button, partial message bleibt sichtbar | User-Retry, Session noch aktiv (Timeout 60s) |
| **Network-Timeout (> 30s)** | Low | Medium | AbortSignal timeout, Error-Display mit Retry | User-Retry oder "Neu starten" |
| **Session Timeout (60s)** | Medium | Medium | Backend auto-summary, 404-Error → "Neu starten"-Button | User startet neues Interview |
| **localStorage blockiert** | Low | High | Try-Catch um `localStorage.setItem()`, Fallback: UUID in sessionStorage | Jede Session neue anonymous_id (kein Cross-Session-Tracking) |
| **@assistant-ui Breaking Change** | Low | High | Package-Lock auf stable Version (npm) | Wenn Breaking: Manual-Migration oder Pin auf alte Version |
| **Fetch API nicht verfügbar** | Very Low | High | Feature-Detection: `if (!window.fetch)` | Polyfill (whatwg-fetch) oder Error-Message |
| **Browser CSP blockiert fetch()** | Low | High | Host-Page muss `connect-src` konfigurieren | Error-Message: "CSP blocked. Contact admin." |
| **Mixed-Content (HTTPS → HTTP)** | Medium | High | Backend muss HTTPS sein (Vercel auto-HTTPS) | Error-Message: "Backend must be HTTPS" |

---

## Technology Decisions

### Stack Choices

| Area | Technology | Rationale |
|------|------------|-----------|
| **SSE-Client** | Fetch API + ReadableStream | POST mit Body erforderlich (Backend-Constraint), EventSource unterstützt nur GET |
| **SSE-Parsing** | Manual Line-Parsing | `data: {...}\n\n` Format, Split by `\n\n`, JSON.parse() |
| **Adapter Pattern** | @assistant-ui ChatModelAdapter | Async Generator, yields `{content: [{type:"text", text}]}` |
| **Session Storage** | React State (useRef) | Memory-only, DSGVO-friendly, Discovery-Spec |
| **Anonymous-ID Storage** | localStorage | Persistent über Sessions, Cross-Session-Tracking |
| **UUID Generation** | crypto.randomUUID() | Native Browser-API, keine Library |
| **Cleanup** | AbortController | fetch() abort() bei Panel-Close, useEffect cleanup |

### Trade-offs

| Decision | Pro | Con | Mitigation |
|----------|-----|-----|------------|
| **Fetch API statt EventSource** | POST möglich, Custom Headers | Kein auto-reconnect, manuelles Parsing | Error-Handling mit Retry-Button |
| **React State statt sessionStorage** | Einfach, DSGVO-freundlich | Session verloren bei Reload | Discovery-Decision, User akzeptiert |
| **Manuelles SSE-Parsing** | Volle Kontrolle, keine Library | Mehr Code, Fehleranfällig | Robuste Tests für Parser |
| **AbortController** | Clean cleanup, kein Memory-Leak | Browser-Support (2017+) | Moderner Standard, Feature-Detection |
| **@assistant-ui Abstraktion** | Fertige UI-Components, State-Management | Library-Dependency, Learning-Curve | Phase 2 bereits integriert, nur Adapter tauschen |

---

## Open Questions

| # | Question | Options | Recommended | Decision |
|---|----------|---------|-------------|----------|
| 1 | SSE-Client Architecture | A) EventSource B) Fetch API C) Hybrid | B) Fetch API | ✅ Fetch API (Backend needs POST with Body) |
| 2 | Session-ID Storage | A) React State B) localStorage C) sessionStorage | A) React State | ✅ React State (Memory-only, lost on reload) |
| 3 | Error-Handling Strategy | A) Retry-Button B) Auto-Retry (3x) C) Neu starten | A) Retry-Button | ✅ Retry-Button (User entscheidet) |
| 4 | Loading/Typing Indicators | A) Loading → Typing → Text B) Nur Typing C) Nur Loading | A) Loading → Typing → Text | ✅ Loading → Typing → Text (Matching Discovery) |

---

## Research Log

| Date | Area | Finding |
|------|------|---------|
| 2026-02-15 | Backend API (Phase 1) | 3 Endpoints: /start (POST, SSE), /message (POST, SSE), /end (POST, JSON). SSE-Format: `data: {"type":"...", ...}\n\n`. Session-Management: In-Memory + Supabase (non-blocking). Error-Handling: Custom Exceptions (404, 409) + SSE Error Events. Timeout: 60s → Auto-Summary. |
| 2026-02-15 | Widget (Phase 2) | @assistant-ui mit Dummy-Adapter (Phase 2 ready). State-Machine: `{panelOpen, screen}` via useReducer. Config-Parser: `data-api-url` aus Script-Tag. Chat-Components: ThreadPrimitive, MessagePrimitive, ComposerPrimitive. IIFE-Build mit CSS-Scoping. |
| 2026-02-15 | Git-History | Phase 1: EventSource + SSE-Starlette (Backend), Session-Management (In-Memory + Supabase), Error-Handling (Custom Exceptions), LangGraph mit MemorySaver, Timeout-Manager. Phase 2: @assistant-ui mit Dummy-Adapter, useReducer State-Machine, Screen Router, Vite IIFE Bundle. Keine Diskussion über Fetch API vs EventSource - Backend nutzt bereits EventSource-Response. |
| 2026-02-15 | Web: @assistant-ui ChatModelAdapter | Interface: `async *run({ messages, abortSignal, context })`. Yields: `{ content: [{ type: "text", text }] }`. Async Generator Pattern für Streaming. Sources: [LocalRuntime Docs](https://www.assistant-ui.com/docs/runtimes/custom/local), [GitHub assistant-ui](https://github.com/assistant-ui/assistant-ui) |
| 2026-02-15 | Web: Fetch API vs EventSource | EventSource: Nur GET, keine Custom Headers, auto-reconnect. Fetch API mit ReadableStream: POST möglich, Custom Headers, kein auto-reconnect. **Backend nutzt POST-Endpoints → Fetch API erforderlich!** Sources: [MDN SSE](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events/Using_server-sent_events), [SSE with POST](https://medium.com/@david.richards.tech/sse-server-sent-events-using-a-post-request-without-eventsource-1c0bd6f14425), [Beyond EventSource](https://rob-blackbourn.medium.com/beyond-eventsource-streaming-fetch-with-readablestream-5765c7de21a1), [Azure fetch-event-source](https://github.com/Azure/fetch-event-source) |
| 2026-02-15 | Web: React SSE + AbortController | AbortController für cleanup in useEffect. Signal an fetch() übergeben. abort() in cleanup function. Prevent memory leaks. EventSource.close() für EventSource-Connections. Sources: [SSE in React (OneUpTime)](https://oneuptime.com/blog/post/2026-01-15-server-sent-events-sse-react/view), [AbortController in React](https://www.j-labs.pl/en/tech-blog/how-to-use-the-useeffect-hook-with-the-abortcontroller/), [useEffect cleanup](https://blog.logrocket.com/understanding-react-useeffect-cleanup-function/) |

---

## Q&A Log

| # | Question | Answer |
|---|----------|--------|
| 1 | Soll ich zuerst umfassend recherchieren (Codebase, Git-History, Web) oder kannst du mir direkt technische Entscheidungen bestätigen? | **Umfassende Recherche (Recommended)** -- Ich durchsuche die Codebase (Backend-APIs, Widget-Components), Git-History und Web-Ressourcen für SSE Best Practices, @assistant-ui Patterns, etc. |
| 2 | SSE-Client Implementierung: Backend nutzt POST-Endpoints mit Body. EventSource unterstützt nur GET. Empfehlung: Fetch API mit ReadableStream und manuellem SSE-Parsing. Einverstanden? | **Ja, Fetch API (Recommended)** -- POST möglich, manuelles SSE-Parsing ('data: {...}\n\n'), AbortController-cleanup. Industry-Standard für POST-SSE (Azure, OpenAI, etc.). |
| 3 | Session-ID Storage: Discovery empfiehlt React State (useRef, Memory-only). Session verloren bei Page-Reload. Alternative: sessionStorage (persistiert über Reload). Was bevorzugst du? | **React State / useRef (Recommended)** -- Memory-only, einfach, DSGVO-freundlich. Bei Reload ist Session weg, User startet neu. Matching Discovery-Spec. |
| 4 | Error-Handling Strategy: Network-Error, Timeout, Stream-Abort. Was soll passieren? | **Retry-Button (Recommended)** -- Error-Display mit 'Erneut versuchen'-Button. User entscheidet. Gleiche Message wird nochmal gesendet. |
| 5 | Loading/Typing Indicators: Discovery definiert beide. Wann welche? | **Loading → Typing → Text (Recommended)** -- Loading während /start (vor metadata). Typing während Assistant streamt (vor erstem delta). Text erscheint progressiv. Matching Discovery-Spec. |

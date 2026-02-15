# Feature: Backend-Widget-Integration (SSE-Streaming-Bridge)

**Epic:** Phase 3 -- Backend-Widget-Integration
**Status:** Ready
**Wireframes:** `wireframes.md` (will be created)

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
| Session-ID Management (React State, Memory-only) |
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

## Current State Reference

> Existing functionality that will be reused (unchanged).

**Backend (Phase 1):**
- ✅ `/api/interview/start` - POST `{anonymous_id}`, returns SSE stream with metadata + text-deltas
- ✅ `/api/interview/message` - POST `{session_id, message}`, returns SSE stream with text-deltas
- ✅ `/api/interview/end` - POST `{session_id}`, returns JSON `{summary, message_count}`
- ✅ SSE Event-Types: `metadata`, `text-delta`, `text-done`, `error`
- ✅ CORS: Allow all origins (MVP)
- ✅ Session-Timeout: 60 Sekunden (Backend-Side, auto-summary bei Timeout)
- ✅ Summary-Injection: Letzte 3 Summaries werden in Prompt injiziert
- ✅ LangGraph Interview-Graph mit Claude Sonnet 4.5
- ✅ Supabase-Persistenz für Interviews und Summaries

**Widget (Phase 2):**
- ✅ Floating Button + Panel mit Slide-Up Animation
- ✅ Screen State Machine: `consent` → `chat` → `thankyou`
- ✅ Consent-Screen mit Headline, Body-Text, CTA-Button
- ✅ Chat-Screen mit @assistant-ui/react Primitives (Thread, Composer)
- ✅ ThankYou-Screen mit Auto-Close Timer (5s)
- ✅ Config-Parser: Liest `data-api-url` aus Script-Tag
- ✅ Reducer: State Management für `panelOpen` und `screen`
- ✅ ChatMessage Component: Rendert User-Messages (right-aligned, brand-color)
- ✅ ChatComposer: Input + Send-Button (disabled wenn leer)
- ✅ `dummyChatModelAdapter`: Leere Implementierung (return generator)
- ✅ IIFE-Build: `widget.js` als einzelne Datei
- ✅ CSS-Scoping: `.feedbackai-widget` Namespace

---

## UI Patterns

### Reused Patterns

| Pattern Type | Component | Usage in this Feature |
|--------------|-----------|----------------------|
| Screen State Machine | `reducer.ts` (Phase 2) | Erweitert um ERROR state |
| Message Bubble (User) | `chat/ChatMessage.tsx` (Phase 2) | Bestehend, wird wiederverwendet |
| Panel Overlay | `Panel.tsx` (Phase 2) | Container für alle Screens |
| Floating Action Button | `FloatingButton.tsx` (Phase 2) | Toggle Panel |
| Auto-Close Timer | `ThankYouScreen.tsx` (Phase 2) | Bestehend (5s delay) |
| @assistant-ui Primitives | `chat/ChatThread.tsx`, `chat/ChatComposer.tsx` (Phase 2) | Thread, Messages, Composer |

### New Patterns

| Pattern Type | Description | Rationale |
|--------------|-------------|-----------|
| SSE Streaming Client | Fetch API mit ReadableStream + manuelles SSE-Parsing | Backend nutzt POST-Endpoints, EventSource unterstützt nur GET |
| Async Generator Pattern | `streamInterviewStart()` und `streamInterviewMessage()` als async generators | Natürliche Abstraktion für SSE-Streams |
| Error-Display Component | Zentrale Error-UI mit Retry-Logik | Konsistente Error-Behandlung über alle API-Calls |
| Loading States | Loading-Indicator + Typing-Indicator | Visuelle Feedback während asynchroner Operationen |
| Assistant Message Bubble | Left-aligned, grey background, streaming-fähig | Unterscheidung zu User-Messages, progressive Text-Erweiterung |
| Anonymous-ID Manager | localStorage-basierte UUID-Persistenz | User-Tracking über Sessions hinweg (Backend-Requirement) |
| Session Cleanup Hooks | useEffect Cleanup-Functions für SSE-Streams | Verhindert Memory-Leaks bei Panel-Close |

---

## User Flow

### Happy Path

1. **Host-Page Load** → Widget-Script lädt → Floating Button erscheint (bottom-right, pulse-animation)
2. **User klickt Floating Button** → Panel gleitet hoch (300ms slide-up) → **Consent-Screen** sichtbar
   - Zeigt: Headline "Ihre Meinung zählt", Body-Text mit Datenschutz-Info, CTA-Button "Los geht's"
3. **User klickt "Los geht's"**
   - Anonymous-ID wird generiert (falls nicht in localStorage) via `crypto.randomUUID()`
   - Anonymous-ID gespeichert in `localStorage.feedbackai_anonymous_id`
   - API-URL aus `data-api-url` gelesen
   - Screen wechselt zu **Chat-Screen**
   - Loading-Indicator erscheint: "Verbinde..." (pulsierend)
4. **`/api/interview/start` POST** mit `{anonymous_id}`
   - Fetch mit POST, Body: JSON, Headers: Content-Type application/json
   - Response: SSE-Stream (text/event-stream)
5. **SSE-Stream empfängt Events:**
   - Event 1: `data: {"type":"metadata","session_id":"<uuid>"}\n\n`
     - Session-ID wird in React State (useRef) gespeichert
     - Loading-Indicator verschwindet
   - Event 2-N: `data: {"type":"text-delta","content":"Hal"}\n\n`
     - Typing-Indicator erscheint (3 animierte Punkte)
     - Erster Delta: Typing-Indicator verschwindet, Assistant-Message erscheint
     - Weitere Deltas: Text wird progressiv erweitert (kein Re-Mount)
   - Event Final: `data: {"type":"text-done"}\n\n`
     - Streaming beendet, Composer wird enabled
6. **User schreibt erste Nachricht**
   - User tippt in Composer-Input
   - Drückt Enter oder klickt Send-Button
   - User-Message erscheint sofort im Chat (right-aligned, brand-color bubble)
   - Composer wird disabled (grau, disabled attribute)
7. **`/api/interview/message` POST** mit `{session_id, message}`
   - SSE-Stream startet wie in #5 (text-deltas)
   - Assistant-Antwort erscheint als neue Message
8. **Schritte 6-7 wiederholen sich** (3-10 Nachrichten-Runden)
9. **User schließt Panel** (X-Button im Header)
   - Laufende SSE-Streams werden abgebrochen (AbortController)
   - Falls Session aktiv: `/api/interview/end` POST mit `{session_id}`
   - Response: JSON `{summary: "...", message_count: N}`
   - Screen wechselt zu **ThankYou-Screen**
10. **ThankYou-Screen**
    - Zeigt: Grünes Check-Icon, Headline "Vielen Dank!", Body-Text "Ihr Feedback hilft uns."
    - Success Icon: Green checkmark (✓)
    - Auto-Close Timer: 5 Sekunden
    - Nach 5s: Panel schließt (slide-down), `screen` reset auf `consent`, Session-ID cleared

### Alternative Paths

| Situation | User-Aktion | System-Verhalten |
|-----------|-------------|------------------|
| **User schließt Panel während Chat** | Click X-Button | Panel schließt, Session bleibt aktiv (Timeout läuft), screen bleibt `chat` |
| **User öffnet Panel erneut (< 60s)** | Click Floating Button | Panel öffnet mit Chat-Screen, History sichtbar (Memory), Interview fortsetzbar |
| **Session Timeout (60s Inaktivität)** | -- (inaktiv) | Backend generiert Auto-Summary, markiert Session als `completed_timeout` |
| **User öffnet Panel nach Timeout** | Click Floating Button | Panel öffnet, nächster /message gibt 404 → Error → "Neu starten" Button → Consent-Screen |
| **User refresht Page während Interview** | Browser-Reload | Session-ID verloren (Memory-only), Widget startet neu mit Consent-Screen, neue Session |
| **User schließt Tab während Interview** | Tab-Close | Session bleibt auf Backend (Timeout), kein /end Call |

### Error Paths

| Error-Type | Trigger | System-Verhalten | UI-Feedback | User-Aktion |
|------------|---------|------------------|-------------|-------------|
| **Network-Fehler bei /start** | Offline, DNS-Fehler, CORS | Catch in fetch() | Error-Display: "Verbindung fehlgeschlagen. Bitte Netzwerk prüfen und erneut versuchen." + Retry-Button | Click Retry → erneut /start |
| **Timeout bei /start** | > 30s keine Response | AbortSignal timeout | Error-Display: "Zeitüberschreitung. Server antwortet nicht." + Retry-Button | Click Retry → erneut /start |
| **Stream-Abbruch (Assistant-Antwort)** | Connection lost während text-delta | ReadableStream closed Event | Error-Display: "Verbindung unterbrochen." + partielle Antwort bleibt sichtbar + Retry-Button | Click Retry → erneut /message |
| **SSE-Error-Event** | `{"type":"error","message":"..."}` | Parse error-Event | Error-Display: Backend-Message anzeigen + Composer deaktiviert | Click "Neu starten" → Consent-Screen |
| **Session nicht gefunden (404)** | /message auf expired/invalid Session | HTTP 404 Response | Error-Display: "Sitzung abgelaufen." + "Neu starten" Button | Click → Consent-Screen |
| **Session bereits completed (409)** | /message auf completed Session | HTTP 409 Response | Error-Display: "Interview bereits beendet." + Auto-Redirect (3s) | Automatisch → ThankYou-Screen |
| **Server-Error (500)** | Backend-Crash, LLM-Fehler | HTTP 500 Response | Error-Display: "Ein Fehler ist aufgetreten. Bitte später versuchen." + Retry-Button | Click Retry → erneut /start oder /message |
| **API-URL nicht konfiguriert** | `data-api-url` fehlt im Script-Tag | Config-Parsing gibt `null` | Console-Error + Error-Display: "Konfigurationsfehler. Bitte Administrator kontaktieren." | Keine Aktion möglich |
| **Invalid JSON im SSE-Stream** | Backend sendet malformed JSON | JSON.parse() throws | Error-Display: "Datenformat-Fehler." + Connection abort + Retry-Button | Click Retry → erneut /start oder /message |

### Edge Cases

| Edge Case | Handling |
|-----------|----------|
| **User sendet mehrere Messages schnell** | Queue-Mechanismus: Nur 1 /message Request gleichzeitig, weitere warten in Array |
| **User sendet Message während Assistant tippt** | Composer disabled (grau), Send-Button disabled, Input disabled |
| **User sendet leere Message** | Send-Button bereits disabled wenn Input leer (Phase 2 Behavior) |
| **User sendet Message > 10.000 Zeichen** | Frontend truncates bei 10.000, zeigt Warning-Toast: "Nachricht zu lang (max. 10.000 Zeichen)" |
| **Anonymous-ID Collision** | Sehr unwahrscheinlich (UUID v4 = 122 bit entropy), Backend-Sache (nicht Frontend-Concern) |
| **data-api-url ist relative URL** | `new URL(apiUrl, window.location.origin)` für absolute URL |
| **Host-Page hat restrictive CSP** | connect-src must include Backend-URL, sonst fetch() blocked → Console-Error |
| **Backend-URL ist HTTPS, Host-Page ist HTTP** | Mixed-Content blocked by Browser → Console-Error, keine Connection möglich |
| **User klickt Floating Button während /start läuft** | Panel ist bereits open, kein Effect (idempotent) |
| **Multiple widget.js loads** | Singleton-Check in main.tsx verhindert doppeltes Mounting (Phase 2 Feature) |

---

## UI Layout & Context

### Screen: Chat-Screen (Extended with Backend-Integration)

**Position:** Panel Body (384px×600px Desktop, Fullscreen Mobile)
**When:** `screen = "chat"` AND `panelOpen = true`

**Layout:**
- **Header** (fixed top): Title "Feedback-Interview" + X-Button (right)
  - X-Button: Always top-right corner of PanelHeader
- **Thread** (flex-1, overflow-y scroll): Message-List (User + Assistant)
  - Empty State: Icon + "Bereit für Ihr Feedback" (wenn keine Messages)
  - User-Message: Right-aligned, brand-color background, white text, max 80% width, border-radius 12px
    - Brand-color: #3B82F6 (blue-500)
  - Assistant-Message: Left-aligned, grey-100 background, grey-900 text, max 80% width, border-radius 12px, optional Avatar (left)
    - Grey scheme: background grey-100, text grey-900
  - Loading-Indicator: "Verbinde..." (pulse animation) -- während /start
  - Typing-Indicator: "..." (3 animierte Punkte) -- während Assistant streamt
  - Error-Display: Full-width red box, red-50 background, red-700 border, Icon + Message + Retry-Button
- **Composer** (fixed bottom): Input (flex-1) + Send-Button (right)
  - Placeholder: "Hier tippen..." (German), "Type here..." (English)
  - Disabled State: Input grau, disabled attribute, Send-Button hidden

### Component: Loading-Indicator (NEW)

**Position:** Chat-Thread, center-aligned
**When:** State = CONNECTING (während /start läuft)

**Visual:**
- Text: "Verbinde..." (grey-600)
- Animation: Pulse (opacity 0.5 → 1.0, 1.5s infinite)
- Or: Skeleton-Message (grey-200 rectangle, shimmer animation)

### Component: Typing-Indicator (NEW)

**Position:** Chat-Thread, as temporary Assistant-Message
**When:** State = ASSISTANT_STREAMING (vor erstem text-delta)

**Visual:**
- 3 Dots "..." (grey-500)
- Animation: Bounce (translateY -4px → 0px, staggered 0.2s delay)
- Or: Simple animated ellipsis "." → ".." → "..." (cycle 1s)

### Component: Error-Display (NEW)

**Position:** Chat-Thread, full-width, below last message
**When:** State = ERROR

**Layout:**
- Border: 1px solid red-700
- Background: red-50
- Padding: 16px
- Icon: ⚠️ or X (red-700, 20px)
- All state icons: Consistent 20px size
  - Error icon options: Either warning triangle (⚠️) or X mark, developer choice
- Text: Error-Message (red-900, 14px, semi-bold)
- Retry-Button: "Erneut versuchen" (red-700 border, white background, hover: red-50)
- Close-Button: X (top-right, closes Error-Display)

### Component: Assistant-Message (NEW)

**Position:** Chat-Thread, left-aligned
**When:** LLM sends text-deltas

**Visual:**
- Avatar (optional): Circle 32px, grey-200 background, "A" or Icon (grey-600)
- Avatar Size: Exactly 32px circle diameter
  - Note: Avatar is optional - implementation can omit if desired
- Bubble: Background grey-100, Padding 12px, Border-Radius 12px
- Text: Color grey-900, Font 14px/1.5, left-aligned
- Streaming: Text wird progressiv erweitert (append, kein Re-Mount)
- Max-Width: 80% of Thread-Width

**Floating Button Specifications:**
- Size: 56×56px
- Position: Fixed bottom-right
- Background: Brand-color (#3B82F6)
- Icon: 💬 (white)
- Animation: Pulse on first load

---

## UI Components & States

| Component | Exists | States | User-Interactions | New Behavior (Phase 3) |
|-----------|--------|--------|-------------------|------------------------|
| **FloatingButton** | ✅ Phase 2 | visible, hidden | Click → OPEN_PANEL | -- (unchanged) |
| **Panel** | ✅ Phase 2 | open, closed | -- | -- (unchanged) |
| **PanelHeader** | ✅ Phase 2 | -- | X-Button → CLOSE_PANEL + cleanup | Cleanup: Abort SSE, call /end if session active |
| **ConsentScreen** | ✅ Phase 2 | -- | CTA-Button → GO_TO_CHAT + startInterview() | startInterview() calls /start API |
| **ChatScreen** | ✅ Phase 2 | idle, connecting, streaming, sending, error | -- | State-Management via reducer + API-Calls |
| **ChatThread** | ✅ Phase 2 | empty, with-messages | Scroll (auto-scroll to bottom) | Auto-Scroll when new message arrives |
| **ChatMessage (User)** | ✅ Phase 2 | -- | -- (readonly) | -- (unchanged) |
| **ChatMessage (Assistant)** | 🆕 Phase 3 | pending, streaming, complete | -- (readonly) | Progressive text rendering (streaming) |
| **ChatComposer** | ✅ Phase 2 | enabled, disabled, sending | Type, Enter/Click → sendMessage() | Disabled during CONNECTING and ASSISTANT_STREAMING |
| **ThankYouScreen** | ✅ Phase 2 | -- | Auto-Timer → CLOSE_AND_RESET | -- (unchanged) |
| **LoadingIndicator** | 🆕 Phase 3 | visible, hidden | -- | Shown during CONNECTING |
| **TypingIndicator** | 🆕 Phase 3 | visible, hidden | -- | Shown during ASSISTANT_STREAMING (before first delta) |
| **ErrorDisplay** | 🆕 Phase 3 | visible, hidden | Retry-Button → retry(), Close → hide | Shows error + retry logic |

---

## Feature State Machine

### States Overview

| State | UI | Available Actions | Composer State |
|-------|----|--------------------|----------------|
| `IDLE` | Consent-Screen | Click "Los geht's" | N/A |
| `CONNECTING` | Chat-Screen + Loading-Indicator | -- (waiting) | Disabled |
| `ASSISTANT_STREAMING` | Chat-Screen + Typing-Indicator + Text appearing | -- (waiting) | Disabled |
| `WAITING_USER_INPUT` | Chat-Screen + Composer enabled | Type, Send | Enabled |
| `SENDING_MESSAGE` | Chat-Screen + User-Message visible + Composer disabled | -- (waiting) | Disabled |
| `ERROR` | Chat-Screen + Error-Display | Retry, Cancel, Close | Disabled |
| `COMPLETED` | ThankYou-Screen | -- (auto-timer) | N/A |

### Transitions

| Current State | Trigger | UI Feedback | Next State | Business Rules |
|---------------|---------|-------------|------------|----------------|
| `IDLE` | Click "Los geht's" | Screen → Chat, Loading-Indicator | `CONNECTING` | Anonymous-ID must exist (generated if not) |
| `CONNECTING` | SSE metadata received | Loading-Indicator → hidden, session_id stored | `CONNECTING` | Session-ID stored in React State |
| `CONNECTING` | SSE first text-delta | Typing-Indicator → shown, text appears | `ASSISTANT_STREAMING` | -- |
| `CONNECTING` | SSE error or Network-Error | Error-Display → shown | `ERROR` | Error-Message from event or generic |
| `ASSISTANT_STREAMING` | SSE text-delta | Text appended to message | `ASSISTANT_STREAMING` | Progressive rendering, no re-mount |
| `ASSISTANT_STREAMING` | SSE text-done | Typing-Indicator → hidden, Composer → enabled | `WAITING_USER_INPUT` | -- |
| `ASSISTANT_STREAMING` | Connection lost | Error-Display → "Verbindung unterbrochen" | `ERROR` | Partial message remains visible |
| `WAITING_USER_INPUT` | User clicks Send (or Enter) | User-Message appears, Composer → disabled | `SENDING_MESSAGE` | Input must not be empty (button disabled if empty) |
| `SENDING_MESSAGE` | SSE first text-delta | Typing-Indicator → shown, text appears | `ASSISTANT_STREAMING` | -- |
| `SENDING_MESSAGE` | SSE error or Network-Error | Error-Display → shown | `ERROR` | User-Message remains visible |
| `ERROR` | Click Retry | Error-Display → hidden, retry logic | `CONNECTING` or `SENDING_MESSAGE` | Depends on which API-Call failed |
| `ERROR` | Click Cancel | Error-Display → hidden, screen → Consent | `IDLE` | Session-ID cleared |
| `ERROR` | 404 Error (Session Expired) | Error-Display → "Neu starten" button | `ERROR` | Auto-Redirect to IDLE after 3s (optional) |
| `ERROR` | 409 Error (Session Completed) | Error-Display → "Interview beendet" | `COMPLETED` | Auto-Redirect to ThankYou |
| `WAITING_USER_INPUT` | Click X-Button (Panel-Close) | Panel closes, /end API called | `COMPLETED` | SSE-Streams aborted, session_id sent to /end |
| `ASSISTANT_STREAMING` | Click X-Button (Panel-Close) | Panel closes, SSE aborted, /end called | `COMPLETED` | Partial message discarded |
| `COMPLETED` | /end Response received | ThankYou-Screen appears | `COMPLETED` | Summary stored (optional display) |
| `COMPLETED` | Auto-Timer (5s) | Panel closes, screen → consent | `IDLE` | Session-ID cleared |

---

## Business Rules

| # | Rule | Rationale | Enforcement |
|---|-------|-----------|-------------|
| 1 | Anonymous-ID is mandatory for /start | Backend tracks user across sessions | Frontend generates UUID v4 via `crypto.randomUUID()`, stores in localStorage key `feedbackai_anonymous_id` |
| 2 | Anonymous-ID must be UUID v4 format | Uniqueness guarantee | Validation: Regex `^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$` |
| 3 | Session-ID is mandatory for /message and /end | Backend identifies session | From /start metadata event, stored in React useRef, passed to subsequent API-Calls |
| 4 | Session-ID must be UUID format | Backend validation | Validation: Same regex as Anonymous-ID |
| 5 | Max message length: 10.000 characters | Backend validation (schemas.py MessageRequest) | Frontend truncates at 10.000, shows warning "Nachricht zu lang (max. 10.000 Zeichen)" |
| 6 | Min message length: 1 character | Prevent empty messages | Send-Button disabled when input empty (Phase 2 feature) |
| 7 | Session timeout: 60 seconds inactivity | Backend prevents zombie-sessions | Frontend handles 404 error, shows "Sitzung abgelaufen. Neu starten?" |
| 8 | Only 1 active request at a time | Prevent race-conditions | Frontend: Composer disabled during CONNECTING and ASSISTANT_STREAMING |
| 9 | Summary-Injection: Last 3 summaries | LLM context from previous sessions | Backend-logic (Phase 1), Frontend transparent |
| 10 | Interview-Ende only on completed session | Prevent duplicate /end calls | Frontend: /end called only once (state → COMPLETED), button disabled after click |
| 11 | CORS: Allow all origins (MVP) | Development & MVP simplicity | Backend-config (Phase 1), later restrict to specific domains |
| 12 | No authentication required | Anonymous interviews | No login, no tokens, no auth headers |
| 13 | API-URL must be valid URL | Prevent config errors | Validation: `new URL(apiUrl)` throws if invalid, show config-error |
| 14 | SSE-Streams must be aborted on Panel-Close | Prevent memory leaks & zombie requests | Frontend: AbortController passed to fetch(), abort() called in cleanup |
| 15 | Session-ID must be cleared after interview-end | Prevent stale session reuse | Frontend: useRef set to null after /end, localStorage not used for session_id |

---

## Data

### Anonymous ID

| Field | Type | Required | Validation | Storage | Generated When |
|-------|------|----------|------------|---------|----------------|
| `anonymous_id` | string (UUID v4) | Yes | 1-255 chars, UUID v4 format | `localStorage.feedbackai_anonymous_id` | First Consent-Accept, if not exists |

### Session

| Field | Type | Required | Validation | Storage | Source |
|-------|------|----------|------------|---------|--------|
| `session_id` | string (UUID) | Yes (after /start) | UUID format | React State (useRef) | From /start metadata event |
| `message_count` | number | No | -- | Not stored (Backend only) | From /end response |

### Message

| Field | Type | Required | Validation | Storage | Usage |
|-------|------|----------|------------|---------|-------|
| `message` | string | Yes | 1-10.000 chars | Transient (only in request) | User-Input, sent to /message |

### API Configuration

| Field | Type | Required | Validation | Storage | Source |
|-------|------|----------|------------|---------|--------|
| `apiUrl` | string (URL) | Yes | Valid URL format | Parsed at init (config.ts) | `data-api-url` attribute on script tag |
| `lang` | string ('de' or 'en') | No | -- | Parsed at init | `data-lang` attribute (default: 'de') |

### SSE Event (from Backend)

| Field | Type | Required | Values | Meaning |
|-------|------|----------|--------|---------|
| `type` | string | Yes | `metadata`, `text-delta`, `text-done`, `error` | Event-Type |
| `session_id` | string (UUID) | Yes (if type=metadata) | UUID | Session-Identifier from /start |
| `content` | string | Yes (if type=text-delta) | Any text | Token chunk from LLM |
| `message` | string | Yes (if type=error) | Error description | Error-Message from Backend |

### End Response (from Backend)

| Field | Type | Required | Meaning |
|-------|------|----------|---------|
| `summary` | string | Yes | Bullet-list summary of interview |
| `message_count` | number | Yes | Total messages in interview |

---

## Implementation Slices

### Dependencies

```
Slice 01 (Foundation)
  └─► Slice 02 (/start SSE)
       └─► Slice 05 (Adapter Start)
            └─► Slice 03 (/message SSE)
                 └─► Slice 06 (Adapter Message)
                      └─► Slice 04 (/end API)
                           └─► Slice 07 (Ende-Logic)
                                └─► Slice 08 (Error-Handling)
                                     └─► Slice 09 (Loading/Typing)
                                          └─► Slice 10 (Assistant-Messages)
                                               └─► Slice 11 (E2E-Tests)
```

### Slices

| # | Name | Scope | Testability | Dependencies |
|---|------|-------|-------------|--------------|
| 1 | Anonymous-ID + API-Client | Generate/Store UUID, fetch wrapper, URL handling | Unit: ID generation, validation, localStorage. API-Client: URL construction | -- |
| 2 | SSE-Client /start | Fetch POST /start, SSE parsing, event-types, timeouts | Unit: Parse SSE, handle events. Integration: Mock /start endpoint | Slice 01 |
| 3 | SSE-Client /message | Fetch POST /message, SSE parsing, session-validation | Unit: Parse SSE. Integration: Mock /message endpoint | Slice 02 |
| 4 | Interview-Ende /end | Fetch POST /end, JSON response, error-handling | Unit: Parse JSON. Integration: Mock /end endpoint | Slice 03 |
| 5 | Adapter Start-Flow | @assistant-ui adapter for /start, session-ID storage | Integration: Consent → Chat, LLM-Antwort sichtbar | Slice 02 |
| 6 | Adapter Message-Flow | @assistant-ui adapter for /message, streaming-state | Integration: User-Message → Assistant-Antwort | Slice 03, Slice 05 |
| 7 | Interview-Ende Logic | Panel-Close → /end, Cleanup, ThankYou-Transition | Integration: Close Panel → ThankYou-Screen | Slice 04, Slice 06 |
| 8 | Error-Handling | Error-Display, Retry-Logic, Error-Types | Unit: Error-Classification. Integration: Simulate errors | Slice 07 |
| 9 | Loading & Typing Indicators | Visual feedback, animations, auto-scroll | Visual: Indicators erscheinen. Integration: Timing | Slice 08 |
| 10 | Assistant-Message Rendering | Left-aligned bubble, streaming-text, avatar | Visual: Message-Layout. Integration: Text-Append | Slice 09 |
| 11 | E2E-Integration-Tests | Full flow, manual testing, edge-cases | E2E: Consent → 3 Messages → Ende → ThankYou | Slice 01-10 |

### Recommended Order

1. **Slice 01: Anonymous-ID + API-Client** -- Foundation ohne die nichts funktioniert
2. **Slice 02: SSE-Client /start** -- Basis für Interview-Start, testbar ohne Frontend
3. **Slice 05: Adapter Start-Flow** -- Erste sichtbare Integration, validiert Architektur
4. **Slice 03: SSE-Client /message** -- Erweiterung für User-Messages
5. **Slice 06: Adapter Message-Flow** -- Chat-Loop funktioniert, MVP fast fertig
6. **Slice 04: Interview-Ende /end** -- API für Summary-Abruf
7. **Slice 07: Interview-Ende Logic** -- Vollständiger E2E-Flow (ohne Error-Handling)
8. **Slice 08: Error-Handling** -- Robustheit, Production-Ready
9. **Slice 09: Loading & Typing Indicators** -- UX-Verbesserungen
10. **Slice 10: Assistant-Message Rendering** -- Visuelle Politur
11. **Slice 11: E2E-Integration-Tests** -- Final Validation

---

## Context & Research

### Codebase Research

| Area | Findings | Relevance |
|------|----------|-----------|
| Backend API | 3 Endpoints: /start (POST, SSE), /message (POST, SSE), /end (POST, JSON). SSE-Format: `data: {"type":"...", ...}\n\n` | Phase 3 muss exakt dieses Format unterstützen |
| Backend SSE-Streaming | EventSourceResponse von sse-starlette, LangGraph yields AIMessageChunk token-by-token | Frontend muss progressive Rendering unterstützen |
| Backend Session-Timeout | 60s Inaktivität → Auto-Summary, status=completed_timeout | Frontend muss 404-Fehler als "Session expired" behandeln |
| Backend Anonymous-ID | Whitespace-stripped, 1-255 chars, used to fetch last 3 summaries | Frontend muss UUID v4 generieren & persistent speichern |
| Widget @assistant-ui | useLocalRuntime mit ChatModelAdapter, dummyChatModelAdapter returns empty generator | Phase 3 ersetzt Dummy mit echtem Adapter |
| Widget State-Machine | Reducer mit OPEN_PANEL, CLOSE_PANEL, GO_TO_CHAT, GO_TO_THANKYOU, CLOSE_AND_RESET | Phase 3 erweitert um ERROR-Handling |
| Widget Config-Parser | Liest `data-api-url` und `data-lang` aus script-tag attributes | Phase 3 nutzt apiUrl für alle API-Calls |
| Widget IIFE-Build | Single `widget.js` file, all CSS inlined, no sourcemap | Phase 3 bleibt kompatibel mit Build-Config |

### Git History

| Date | Commit | Learning |
|------|--------|----------|
| 2026-02-15 | bfef93d "feat(phase-2): Complete Widget-Shell feature" | Phase 2 ist fertig, alle 4 Slices implementiert |
| 2026-02-13 | Phase 1 Commits | Backend-Kern mit SSE-Streaming wurde in Phase 1 fertiggestellt |
| 2026-02-12 | Phase 0 Commits | Repository-Setup, Dependencies, Context-Dateien |

### Web Research

| Source | Finding | Relevance |
|--------|---------|-----------|
| [MDN: Server-Sent Events](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events/Using_server-sent_events) | EventSource API only supports GET requests, no custom headers/body | → Must use Fetch API for POST-based SSE |
| [JavaScript.info: SSE](https://javascript.info/server-sent-events) | SSE auto-reconnects, but only for GET. Manual parsing: `data: ...\n\n` format | → Implement manual SSE-Parser with ReadableStream |
| [OneUpTime: SSE in React](https://oneuptime.com/blog/post/2026-01-15-server-sent-events-sse-react/view) | useEffect cleanup for EventSource.close(), AbortController for fetch() | → Use AbortController for cleanup on Panel-Close |
| [Upstash: Streaming LLM Responses](https://upstash.com/blog/sse-streaming-llm-responses) | SSE is de facto standard for LLM streaming, used by OpenAI, Anthropic, etc. | → Confirms SSE is correct choice for LLM streaming |
| [GitHub: assistant-ui](https://github.com/assistant-ui/assistant-ui) | ChatModelAdapter Pattern: async generator `run()` method, yields text chunks | → Adapter implementation matches @assistant-ui interface |

---

## Open Questions

> All questions have been resolved during Q&A session.

| # | Question | Options | Recommended | Decision |
|---|----------|---------|-------------|----------|
| 1 | SSE-Client Architecture | A) EventSource B) Fetch API C) Hybrid | B) Fetch API | ✅ Fetch API (Backend needs POST with Body) |
| 2 | Session-ID Storage | A) React State B) localStorage C) sessionStorage | A) React State | ✅ React State (Memory-only, lost on reload) |
| 3 | Start-Trigger | A) Consent-Accept B) First-Message C) Panel-Open | A) Consent-Accept | ✅ Consent-Accept (Clear user-intention) |
| 4 | Composer during Streaming | A) Wait B) Queue C) Interrupt | A) Wait | ✅ Disabled until text-done |
| 5 | Expliziter End-Button | A) Nein B) Ja C) Beides | A) Nein | ✅ Automatisch bei Panel-Close |
| 6 | Panel-Close während Stream | A) Stream abbrechen B) Weiterlaufen C) Session beenden | A) Stream abbrechen | ✅ Abort + /end call |
| 7 | Chat-History Persistenz | A) Nein B) Bis Ende C) Auch nach Ende | A) Nein | ✅ Memory-only, DSGVO-freundlich |
| 8 | Wireframes | A) Nein B) Ja | B) Ja | ✅ ASCII-Wireframes erstellen |

---

## Research Log

| Date | Area | Finding |
|------|------|---------|
| 2026-02-15 | Backend API | Explored all 3 endpoints, SSE-Format, Session-Management, Timeout-Logic |
| 2026-02-15 | Widget Current-State | Explored all Phase 2 components, State-Machine, @assistant-ui integration |
| 2026-02-15 | Git-History | Analyzed commits for Phase 0, 1, 2. Phase 2 completed recently. |
| 2026-02-15 | Web: SSE Best Practices | EventSource only supports GET, Fetch API for POST. AbortController for cleanup. |
| 2026-02-15 | Web: React SSE | useEffect cleanup essential. Progressive rendering for streaming text. |
| 2026-02-15 | Web: @assistant-ui Patterns | ChatModelAdapter interface: async generator `run()`. Composable primitives. |

---

## Q&A Log

| # | Question | Answer |
|---|----------|--------|
| 1 | Soll ich zuerst recherchieren oder hast du eine klare Vorstellung? | Recherchiere zuerst (Recommended) -- User wählte umfassende Recherche |
| 2 | Ist der Scope korrekt (SSE-Brücke zwischen Widget und Backend)? | Ja, genau das (Recommended) -- Phase 3 = Backend-Widget-Integration |
| 3 | Wie detailliert soll die Discovery sein? | User änderte von Standard zu **Detailliert** -- maximaler Detail-Level |
| 4 | Wie soll der SSE-Client implementiert werden? | User vertraute technischer Entscheidung → **Fetch API mit ReadableStream** (Backend braucht POST mit Body, EventSource unterstützt nur GET) |
| 5 | Wo soll die Session-ID gespeichert werden? | **React State (Recommended)** -- Memory-only, verloren bei Reload, einfach und sicher |
| 6 | Wann soll /api/interview/start aufgerufen werden? | **Bei Consent-Accept (Recommended)** -- User klickt "Los geht's" → /start → Chat mit LLM-Gruß |
| 7 | Ist der User Flow vollständig und korrekt? | **Perfekt, weiter (Recommended)** -- Flow deckt alle Szenarien ab (Happy Path, Alternative Paths, Error Paths, Edge Cases) |
| 8 | Soll User während Assistant-Streaming bereits schreiben können? | **Nein, warten (Recommended)** -- Composer disabled bis text-done, verhindert Chaos |
| 9 | Soll es einen expliziten "Interview beenden"-Button geben? | **Nein, automatisch (Recommended)** -- /end wird bei Panel-Close oder Timeout aufgerufen |
| 10 | Was passiert bei Panel-Close während Assistant streamt? | **Stream abbrechen (Recommended)** -- SSE-Connection closed, Session bleibt aktiv (Timeout läuft) |
| 11 | Soll Chat-History persistent sein (localStorage)? | **Nein (Recommended)** -- Memory-only, bei Reload alles weg, DSGVO-freundlich |
| 12 | Sollen detaillierte ASCII-Wireframes erstellt werden? | **Ja** -- Wireframes für Chat-Screen mit Assistant-Messages, Loading-States, Error-Display |

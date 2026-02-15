# E2E Checklist: Backend-Widget-Integration

**Integration Map:** `integration-map.md`
**Generated:** 2026-02-15

---

## Pre-Conditions

- [x] All slices APPROVED (Gate 2) -- 11/11 APPROVED
- [x] Architecture APPROVED (Gate 1)
- [x] Integration Map has no MISSING INPUTS -- 0 missing

---

## Happy Path Tests

### Flow 1: Complete Interview (Consent -> Chat -> 3 Exchanges -> Close -> ThankYou)

1. [ ] **Slice 01:** `getOrCreateAnonymousId()` generates UUID v4 and stores in `localStorage.feedbackai_anonymous_id`
2. [ ] **Slice 05:** User clicks "Los geht's" -> ChatScreen mounts -> adapter `run()` called
3. [ ] **Slice 05:** Adapter calls `apiClient.startInterview(anonymous_id)` with POST to `/api/interview/start`
4. [ ] **Slice 02:** SSE stream parsed: metadata event -> session_id stored in sessionIdRef
5. [ ] **Slice 09:** LoadingIndicator ("Verbinde...") visible during CONNECTING, disappears on first text-delta
6. [ ] **Slice 05:** text-delta events accumulated -> yields `{ content: [{ type: "text", text }] }` progressively
7. [ ] **Slice 10:** AssistantMessage renders left-aligned, grey-100 background, with avatar "A"
8. [ ] **Slice 05:** text-done event -> generator completes -> Composer enabled
9. [ ] **Slice 06:** User sends message -> adapter detects session_id exists -> calls `/api/interview/message`
10. [ ] **Slice 03:** SSE stream parsed via `streamMessage()`: text-delta + text-done (no metadata)
11. [ ] **Slice 09:** TypingIndicator ("...") visible before first text-delta of response
12. [ ] **Slice 06:** text-delta events yield progressive text -> AssistantMessage updates
13. [ ] **Slice 06:** text-done -> Composer re-enabled -> repeat for 2 more exchanges
14. [ ] **Slice 07:** User clicks X-Button -> `hasActiveSession()` returns true
15. [ ] **Slice 07:** `endInterview()` called: abort SSE stream, call `endInterviewSafe(sessionId)`, clear sessionIdRef
16. [ ] **Slice 07:** Dispatch `GO_TO_THANKYOU` -> ThankYou screen visible
17. [ ] **Phase 2:** Auto-close timer (5s) -> `CLOSE_AND_RESET` -> panel closes, screen resets to consent

### Flow 2: Second Visit (Anonymous-ID Reuse)

1. [ ] **Slice 01:** On second load, `getOrCreateAnonymousId()` returns existing UUID from localStorage (no new generation)
2. [ ] **Slice 05:** `/start` called with same anonymous_id -> backend injects last 3 summaries into context

---

## Edge Cases

### Error Handling

- [ ] **Network Error on /start:** `TypeError("Failed to fetch")` -> `classifyError()` returns "Verbindung fehlgeschlagen..." + retry action -> ErrorDisplay with "Erneut versuchen" button
- [ ] **Timeout on /start (>30s):** `DOMException("AbortError")` -> `classifyError()` returns "Zeituberschreitung..." + retry action
- [ ] **404 on /message (session expired):** `ApiError` with status 404 -> ErrorDisplay with "Sitzung abgelaufen." + "Neu starten" button -> click resets to consent
- [ ] **409 on /message (session completed):** `ApiError` with status 409 -> `classifyError()` returns `redirect_thankyou` -> auto-redirect to ThankYou
- [ ] **500 on /start or /message:** `ApiError` with status 500 -> ErrorDisplay with "Ein Fehler ist aufgetreten..." + "Erneut versuchen" button
- [ ] **SSE error event:** `{ type: "error", message: "..." }` -> adapter throws Error -> ErrorDisplay with backend message
- [ ] **Invalid JSON in SSE stream:** `parseSSELine()` returns null (skip) -> stream continues with valid events
- [ ] **API URL null:** `createApiClient(null)` throws "API URL not configured"
- [ ] **Response without body:** `streamStart()` / `streamMessage()` throws ApiError "No response body"
- [ ] **localStorage blocked (SecurityError):** `getOrCreateAnonymousId()` returns fresh UUID without persistence (no throw)
- [ ] **Retry after network error:** Click "Erneut versuchen" -> error cleared -> /start or /message retried
- [ ] **"Neu starten" after 404:** Click "Neu starten" -> session cleared -> screen resets to consent

### State Transitions

- [ ] **IDLE -> CONNECTING:** Click "Los geht's" -> LoadingIndicator visible, Composer disabled
- [ ] **CONNECTING -> ASSISTANT_STREAMING:** First text-delta arrives -> LoadingIndicator hidden, text appears
- [ ] **ASSISTANT_STREAMING -> WAITING_USER_INPUT:** text-done received -> Composer enabled
- [ ] **WAITING_USER_INPUT -> SENDING_MESSAGE:** User clicks Send -> User-Message appears, Composer disabled
- [ ] **SENDING_MESSAGE -> ASSISTANT_STREAMING:** First text-delta from /message -> TypingIndicator shown then replaced
- [ ] **Any active state -> COMPLETED:** X-Button -> abort + /end + ThankYou
- [ ] **ERROR -> retry -> CONNECTING/SENDING_MESSAGE:** Retry action re-triggers failed call
- [ ] **ERROR -> restart -> IDLE:** "Neu starten" clears session, shows consent

### Boundary Conditions

- [ ] **Empty message prevention:** Send button disabled when Composer input is empty (Phase 2 behavior preserved)
- [ ] **Composer disabled during streaming:** During CONNECTING and ASSISTANT_STREAMING, Composer input is disabled
- [ ] **Multiple rapid messages:** Each /message call completes before next starts (no concurrent requests)
- [ ] **SSE events split across chunks:** `readSSEStream()` correctly buffers and reassembles events
- [ ] **Multiple events in single chunk:** `readSSEStream()` yields all events from one chunk
- [ ] **Trailing slash in apiUrl:** `createApiClient("http://host/")` constructs URLs without double slashes
- [ ] **Panel close during streaming:** AbortController.abort() called, /end called (fire-and-forget)
- [ ] **Panel close without session:** No /end call, CLOSE_PANEL dispatched
- [ ] **/end fails on panel close:** Error silently ignored (endInterviewSafe), ThankYou still shows
- [ ] **prefers-reduced-motion:** LoadingIndicator and TypingIndicator animations disabled
- [ ] **AssistantMessage streaming stability:** Container DOM node stays the same during text append (no re-mount)
- [ ] **Auto-scroll:** Thread auto-scrolls to bottom when new message appears

---

## Cross-Slice Integration Points

| # | Integration Point | Slices | How to Verify |
|---|-------------------|--------|---------------|
| 1 | Anonymous-ID -> /start request body | Slice 01 -> 05 | Verify fetch body contains `anonymous_id` from localStorage |
| 2 | SSE parser -> Adapter start flow | Slice 02 -> 05 | Verify `streamStart()` yields typed SSEEvent to adapter |
| 3 | SSE parser -> Adapter message flow | Slice 02/03 -> 06 | Verify `streamMessage()` yields text-delta/text-done to adapter |
| 4 | Session-ID storage -> message/end calls | Slice 05 -> 06, 07 | Verify sessionIdRef.current used in sendMessage and endInterview |
| 5 | Adapter yields -> @assistant-ui rendering | Slice 05/06 -> UI | Verify `{ content: [{ type: "text", text }] }` format renders in thread |
| 6 | endInterviewSafe -> panel close cleanup | Slice 04 -> 07 | Verify /end called with fire-and-forget, null on error |
| 7 | InterviewControls -> main.tsx Widget | Slice 07 -> main.tsx | Verify handleClosePanel checks hasActiveSession, calls endInterview |
| 8 | classifyError -> ErrorDisplay | Slice 08 -> ChatScreen | Verify error type maps to correct German message + action |
| 9 | LoadingIndicator/TypingIndicator -> ChatThread | Slice 09 -> ChatThread | Verify indicators show/hide based on @assistant-ui thread state |
| 10 | AssistantMessage -> ChatThread components prop | Slice 10 -> ChatThread | Verify ThreadPrimitive.Messages uses separate User/Assistant components |

---

## Sign-Off

| Tester | Date | Result |
|--------|------|--------|
| | | |

**Notes:**

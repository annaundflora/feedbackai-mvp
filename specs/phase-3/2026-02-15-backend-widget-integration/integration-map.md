# Integration Map: Backend-Widget-Integration

**Generated:** 2026-02-15
**Slices:** 11
**Connections:** 23

---

## Dependency Graph (Visual)

```
                   +----------------------------+
                   |  Slice 01                  |
                   |  Anonymous-ID + API-Client |
                   +----------------------------+
                     /        |         \      \
                    v         v          v      v
+------------------+  +------------------+  +------------------+
| Slice 02         |  | Slice 03         |  | Slice 04         |
| SSE-Client /start|  | SSE-Client /msg  |  | Interview-End    |
+------------------+  +------------------+  +------------------+
   |       \              |                       |
   |        \             |                       |
   v         v            v                       |
+------------------+  +------------------+        |
| Slice 05         |  | Slice 06         |        |
| Adapter Start    |  | Adapter Message  |        |
+------------------+  +------------------+        |
   |       \              |                       |
   |        \             |                       v
   |         +------>+------------------+  +------------------+
   +--------------->| Slice 07         |<-| (endInterviewSafe)|
                    | Interview-End    |  +------------------+
                    | Logic            |
                    +------------------+
                             |
                             v
                    +------------------+
                    | Slice 08         |
                    | Error-Handling   |
                    +------------------+
                             |
                             v
                    +------------------+
                    | Slice 09         |
                    | Loading/Typing   |
                    +------------------+
                             |
                             v
                    +------------------+
                    | Slice 10         |
                    | Assistant-Message|
                    +------------------+
                             |
                             v
                    +------------------+
                    | Slice 11         |
                    | E2E Tests        |
                    +------------------+
```

---

## Nodes

### Slice 01: Anonymous-ID + API-Client

| Field | Value |
|-------|-------|
| Status | APPROVED |
| Dependencies | None (foundation) |
| Outputs | 7 resources |

**Inputs:**

| Input | Source | Validation |
|-------|--------|------------|
| None (foundation slice) | -- | PASS |

**Outputs:**

| Output | Type | Consumers |
|--------|------|-----------|
| `getOrCreateAnonymousId()` | Function | Slice 05 |
| `createApiClient(apiUrl)` | Function | Slice 02, 03, 04 |
| `ApiClient.startInterview()` | Method | Slice 02 |
| `ApiClient.sendMessage()` | Method | Slice 03, 06 |
| `ApiClient.endInterview()` | Method | Slice 04 |
| `SSEEvent` type | TypeScript Type | Slice 02, 03 |
| `EndResponse` type | TypeScript Type | Slice 04, 07 |

---

### Slice 02: SSE-Client /start

| Field | Value |
|-------|-------|
| Status | APPROVED |
| Dependencies | Slice 01 |
| Outputs | 3 resources |

**Inputs:**

| Input | Source | Validation |
|-------|--------|------------|
| `SSEEvent` type | Slice 01 | PASS |
| `ApiError` class | Slice 01 | PASS |
| `ApiClient.startInterview()` | Slice 01 | PASS |

**Outputs:**

| Output | Type | Consumers |
|--------|------|-----------|
| `parseSSELine()` | Function | Slice 03 |
| `readSSEStream()` | Function | Slice 03, 05, 06 |
| `streamStart()` | Function | Slice 05 |

---

### Slice 03: SSE-Client /message

| Field | Value |
|-------|-------|
| Status | APPROVED |
| Dependencies | Slice 01, 02 |
| Outputs | 1 resource |

**Inputs:**

| Input | Source | Validation |
|-------|--------|------------|
| `SSEEvent` type | Slice 01 | PASS |
| `ApiError` class | Slice 01 | PASS |
| `ApiClient.sendMessage()` | Slice 01 | PASS |
| `readSSEStream()` | Slice 02 | PASS |

**Outputs:**

| Output | Type | Consumers |
|--------|------|-----------|
| `streamMessage()` | Function | Slice 06 |

---

### Slice 04: Interview-End /end

| Field | Value |
|-------|-------|
| Status | APPROVED |
| Dependencies | Slice 01 |
| Outputs | 1 resource |

**Inputs:**

| Input | Source | Validation |
|-------|--------|------------|
| `ApiClient.endInterview()` | Slice 01 | PASS |
| `ApiError` class | Slice 01 | PASS |
| `EndResponse` type | Slice 01 | PASS |

**Outputs:**

| Output | Type | Consumers |
|--------|------|-----------|
| `ApiClient.endInterviewSafe()` | Method | Slice 07 |

---

### Slice 05: Adapter Start-Flow

| Field | Value |
|-------|-------|
| Status | APPROVED |
| Dependencies | Slice 01, 02 |
| Outputs | 3 resources |

**Inputs:**

| Input | Source | Validation |
|-------|--------|------------|
| `getOrCreateAnonymousId()` | Slice 01 | PASS |
| `createApiClient()` | Slice 01 | PASS |
| `ApiClient.startInterview()` | Slice 01 | PASS |
| `streamStart()` | Slice 02 | PASS |

**Outputs:**

| Output | Type | Consumers |
|--------|------|-----------|
| `createChatModelAdapter()` | Function | Slice 06 |
| `useWidgetChatRuntime(apiUrl)` | Hook | ChatScreen (Slice 05 deliverable), Slice 07 |
| Session-ID ref | React Ref | Slice 06, 07 |

---

### Slice 06: Adapter Message-Flow

| Field | Value |
|-------|-------|
| Status | APPROVED |
| Dependencies | Slice 03, 05 |
| Outputs | 1 resource |

**Inputs:**

| Input | Source | Validation |
|-------|--------|------------|
| `ApiClient.sendMessage()` | Slice 01 | PASS |
| `streamMessage()` | Slice 03 | PASS |
| `createChatModelAdapter()` | Slice 05 | PASS |
| Session-ID ref | Slice 05 | PASS |

**Outputs:**

| Output | Type | Consumers |
|--------|------|-----------|
| Complete ChatModelAdapter | ChatModelAdapter | @assistant-ui runtime (final consumer) |

---

### Slice 07: Interview-End Logic

| Field | Value |
|-------|-------|
| Status | APPROVED |
| Dependencies | Slice 04, 06 |
| Outputs | 2 resources |

**Inputs:**

| Input | Source | Validation |
|-------|--------|------------|
| `ApiClient.endInterviewSafe()` | Slice 04 | PASS |
| Session-ID ref | Slice 05 | PASS |
| `useWidgetChatRuntime()` | Slice 05 | PASS |

**Outputs:**

| Output | Type | Consumers |
|--------|------|-----------|
| `InterviewControls.endInterview()` | Function | main.tsx Widget (Slice 07 deliverable) |
| `InterviewControls.hasActiveSession()` | Function | main.tsx Widget (Slice 07 deliverable) |

---

### Slice 08: Error-Handling

| Field | Value |
|-------|-------|
| Status | APPROVED |
| Dependencies | Slice 07 |
| Outputs | 2 resources |

**Inputs:**

| Input | Source | Validation |
|-------|--------|------------|
| `ApiError` class | Slice 01 | PASS |
| `InterviewControls` | Slice 07 | PASS |

**Outputs:**

| Output | Type | Consumers |
|--------|------|-----------|
| `ErrorDisplay` | Component | ChatScreen (Slice 08 deliverable) |
| `classifyError()` | Function | ChatScreen (Slice 08 deliverable) |

---

### Slice 09: Loading & Typing Indicators

| Field | Value |
|-------|-------|
| Status | APPROVED |
| Dependencies | Slice 08 |
| Outputs | 2 resources |

**Inputs:**

| Input | Source | Validation |
|-------|--------|------------|
| @assistant-ui thread state | Slice 05/06 | PASS |

**Outputs:**

| Output | Type | Consumers |
|--------|------|-----------|
| `LoadingIndicator` | Component | ChatThread (Slice 09 deliverable) |
| `TypingIndicator` | Component | ChatThread (Slice 09 deliverable) |

---

### Slice 10: Assistant-Message Rendering

| Field | Value |
|-------|-------|
| Status | APPROVED |
| Dependencies | Slice 09 |
| Outputs | 1 resource |

**Inputs:**

| Input | Source | Validation |
|-------|--------|------------|
| `ChatMessage` (user) | Phase 2 (existing) | PASS |
| `ChatThread` | Phase 2 (existing) | PASS |

**Outputs:**

| Output | Type | Consumers |
|--------|------|-----------|
| `AssistantMessage` | Component | ChatThread (Slice 10 deliverable) |

---

### Slice 11: E2E Integration Tests

| Field | Value |
|-------|-------|
| Status | APPROVED |
| Dependencies | Slices 01-10 |
| Outputs | 1 resource |

**Inputs:**

| Input | Source | Validation |
|-------|--------|------------|
| All Slices 01-10 modules | Slices 01-10 | PASS |

**Outputs:**

| Output | Type | Consumers |
|--------|------|-----------|
| `createMockSSEResponse` | Test Helper | Future tests (final output) |

---

## Connections

| # | From | To | Resource | Type | Status |
|---|------|-----|----------|------|--------|
| 1 | Slice 01 | Slice 02 | `SSEEvent` type | TypeScript Type | PASS |
| 2 | Slice 01 | Slice 02 | `ApiError` class | Class | PASS |
| 3 | Slice 01 | Slice 02 | `ApiClient.startInterview()` | Method | PASS |
| 4 | Slice 01 | Slice 03 | `SSEEvent` type | TypeScript Type | PASS |
| 5 | Slice 01 | Slice 03 | `ApiError` class | Class | PASS |
| 6 | Slice 01 | Slice 03 | `ApiClient.sendMessage()` | Method | PASS |
| 7 | Slice 01 | Slice 04 | `ApiClient.endInterview()` | Method | PASS |
| 8 | Slice 01 | Slice 04 | `ApiError` class | Class | PASS |
| 9 | Slice 01 | Slice 04 | `EndResponse` type | TypeScript Type | PASS |
| 10 | Slice 01 | Slice 05 | `getOrCreateAnonymousId()` | Function | PASS |
| 11 | Slice 01 | Slice 05 | `createApiClient()` | Function | PASS |
| 12 | Slice 01 | Slice 08 | `ApiError` class | Class | PASS |
| 13 | Slice 02 | Slice 03 | `readSSEStream()` | Function | PASS |
| 14 | Slice 02 | Slice 05 | `streamStart()` | Function | PASS |
| 15 | Slice 03 | Slice 06 | `streamMessage()` | Function | PASS |
| 16 | Slice 04 | Slice 07 | `ApiClient.endInterviewSafe()` | Method | PASS |
| 17 | Slice 05 | Slice 06 | `createChatModelAdapter()` | Function | PASS |
| 18 | Slice 05 | Slice 06 | Session-ID ref | React Ref | PASS |
| 19 | Slice 05 | Slice 07 | Session-ID ref | React Ref | PASS |
| 20 | Slice 05 | Slice 07 | `useWidgetChatRuntime()` | Hook | PASS |
| 21 | Slice 07 | Slice 08 | `InterviewControls` | Interface | PASS |
| 22 | Slice 09 | Slice 09 | LoadingIndicator/TypingIndicator mounted in ChatThread | Component | PASS |
| 23 | Slice 10 | Slice 10 | AssistantMessage mounted in ChatThread | Component | PASS |

---

## Validation Results

### PASS Valid Connections: 23

All declared dependencies have matching outputs. Every input resource has a corresponding output in a producer slice.

### Orphaned Outputs: 0

All outputs are consumed:

| Output | Defined In | Consumers | Status |
|--------|------------|-----------|--------|
| `createMockSSEResponse` | Slice 11 | Future tests | PASS (final user-facing test utility) |
| Complete ChatModelAdapter | Slice 06 | @assistant-ui runtime | PASS (final user-facing integration) |
| `InterviewControls` | Slice 07 | main.tsx Widget | PASS (final user-facing controls) |
| `ErrorDisplay` | Slice 08 | ChatScreen | PASS (mounted in ChatScreen deliverable) |
| `classifyError()` | Slice 08 | ChatScreen | PASS (used in ChatScreen deliverable) |
| `LoadingIndicator` | Slice 09 | ChatThread | PASS (mounted in ChatThread deliverable) |
| `TypingIndicator` | Slice 09 | ChatThread | PASS (mounted in ChatThread deliverable) |
| `AssistantMessage` | Slice 10 | ChatThread | PASS (mounted in ChatThread deliverable) |

### Missing Inputs: 0

No missing inputs detected. All declared dependencies resolve to approved slice outputs.

### Deliverable-Consumer Gaps: 0

| Component | Defined In | Consumer Page | Page In Deliverables? | Status |
|-----------|------------|---------------|-----------------------|--------|
| `ErrorDisplay` | Slice 08 | `ChatScreen.tsx` | Yes (Slice 08 deliverables) | PASS |
| `LoadingIndicator` | Slice 09 | `ChatThread.tsx` | Yes (Slice 09 deliverables) | PASS |
| `TypingIndicator` | Slice 09 | `ChatThread.tsx` | Yes (Slice 09 deliverables) | PASS |
| `AssistantMessage` | Slice 10 | `ChatThread.tsx` | Yes (Slice 10 deliverables) | PASS |
| `useWidgetChatRuntime` | Slice 05 | `ChatScreen.tsx` | Yes (Slice 05 deliverables) | PASS |
| `InterviewControls` | Slice 07 | `main.tsx` | Yes (Slice 07 deliverables) | PASS |
| `chat-runtime.ts` controls | Slice 07 | `chat-runtime.ts` | Yes (Slice 07 deliverables) | PASS |

---

## Discovery Traceability

### UI Components Coverage

| Discovery Element | Type | States | Covered In | Status |
|-------------------|------|--------|------------|--------|
| FloatingButton | Existing Phase 2 | visible, hidden | Unchanged (Phase 2) | PASS |
| Panel | Existing Phase 2 | open, closed | Unchanged (Phase 2) | PASS |
| PanelHeader | Existing Phase 2 | X-Button cleanup | Slice 07 (endInterview on close) | PASS |
| ConsentScreen | Existing Phase 2 | CTA -> startInterview() | Slice 05 (adapter start flow) | PASS |
| ChatScreen | Existing Phase 2 | idle, connecting, streaming, sending, error | Slice 05, 06, 08 | PASS |
| ChatThread | Existing Phase 2 | empty, with-messages | Slice 09, 10 (indicators + assistant message) | PASS |
| ChatMessage (User) | Existing Phase 2 | readonly | Unchanged (Phase 2) | PASS |
| ChatMessage (Assistant) | NEW Phase 3 | pending, streaming, complete | Slice 10 (AssistantMessage) | PASS |
| ChatComposer | Existing Phase 2 | enabled, disabled, sending | Slice 05, 06 (disabled during streaming) | PASS |
| ThankYouScreen | Existing Phase 2 | auto-timer | Slice 07 (GO_TO_THANKYOU transition) | PASS |
| LoadingIndicator | NEW Phase 3 | visible, hidden | Slice 09 | PASS |
| TypingIndicator | NEW Phase 3 | visible, hidden | Slice 09 | PASS |
| ErrorDisplay | NEW Phase 3 | visible, hidden | Slice 08 | PASS |

### State Machine Coverage

| State | Required UI | Available Actions | Covered In | Status |
|-------|-------------|-------------------|------------|--------|
| IDLE | Consent-Screen | Click "Los geht's" | Slice 05 (adapter triggers /start) | PASS |
| CONNECTING | Chat-Screen + LoadingIndicator | -- (waiting) | Slice 05 (adapter start), Slice 09 (LoadingIndicator) | PASS |
| ASSISTANT_STREAMING | Chat-Screen + TypingIndicator + Text | -- (waiting) | Slice 05/06 (adapter yields text), Slice 09 (TypingIndicator), Slice 10 (AssistantMessage) | PASS |
| WAITING_USER_INPUT | Chat-Screen + Composer enabled | Type, Send | Slice 06 (adapter message flow) | PASS |
| SENDING_MESSAGE | Chat-Screen + User-Message + Composer disabled | -- (waiting) | Slice 06 (adapter sends /message) | PASS |
| ERROR | Chat-Screen + ErrorDisplay | Retry, Cancel, Close | Slice 08 (ErrorDisplay + classifyError) | PASS |
| COMPLETED | ThankYou-Screen | -- (auto-timer) | Slice 07 (GO_TO_THANKYOU) | PASS |

### Transitions Coverage

| From | Trigger | To | Covered In | Status |
|------|---------|-----|------------|--------|
| IDLE | Click "Los geht's" | CONNECTING | Slice 05 | PASS |
| CONNECTING | SSE metadata received | CONNECTING | Slice 05 (session_id stored) | PASS |
| CONNECTING | SSE first text-delta | ASSISTANT_STREAMING | Slice 05 (yields text) | PASS |
| CONNECTING | SSE error / Network-Error | ERROR | Slice 05 (throws), Slice 08 (classifyError) | PASS |
| ASSISTANT_STREAMING | SSE text-delta | ASSISTANT_STREAMING | Slice 05/06 (accumulates text) | PASS |
| ASSISTANT_STREAMING | SSE text-done | WAITING_USER_INPUT | Slice 05/06 (generator returns) | PASS |
| ASSISTANT_STREAMING | Connection lost | ERROR | Slice 08 (classifyError) | PASS |
| WAITING_USER_INPUT | User clicks Send | SENDING_MESSAGE | Slice 06 (adapter message flow) | PASS |
| SENDING_MESSAGE | SSE first text-delta | ASSISTANT_STREAMING | Slice 06 (yields text) | PASS |
| SENDING_MESSAGE | SSE error / Network-Error | ERROR | Slice 06 (throws), Slice 08 (classifyError) | PASS |
| ERROR | Click Retry | CONNECTING/SENDING_MESSAGE | Slice 08 (onRetry callback) | PASS |
| ERROR | Click Cancel | IDLE | Slice 08 (onRestart callback) | PASS |
| ERROR | 404 Session Expired | ERROR (Neu starten) | Slice 08 (classifyError -> restart) | PASS |
| ERROR | 409 Session Completed | COMPLETED | Slice 08 (classifyError -> redirect_thankyou) | PASS |
| WAITING_USER_INPUT | Click X-Button | COMPLETED | Slice 07 (endInterview -> GO_TO_THANKYOU) | PASS |
| ASSISTANT_STREAMING | Click X-Button | COMPLETED | Slice 07 (abort + endInterview -> GO_TO_THANKYOU) | PASS |
| COMPLETED | /end response | COMPLETED | Slice 07 (endInterviewSafe) | PASS |
| COMPLETED | Auto-Timer 5s | IDLE | Phase 2 existing (CLOSE_AND_RESET) | PASS |

### Business Rules Coverage

| Rule | Description | Covered In | Status |
|------|-------------|------------|--------|
| BR-1 | Anonymous-ID mandatory for /start | Slice 01 (getOrCreateAnonymousId), Slice 05 (calls before /start) | PASS |
| BR-2 | Anonymous-ID UUID v4 format | Slice 01 (crypto.randomUUID) | PASS |
| BR-3 | Session-ID mandatory for /message and /end | Slice 05 (stores from metadata), Slice 06 (passes to sendMessage), Slice 07 (passes to endInterview) | PASS |
| BR-4 | Session-ID UUID format | Slice 01 (from backend metadata event) | PASS |
| BR-5 | Max message length 10,000 chars | Discovery noted, backend validates | PASS |
| BR-6 | Min message length 1 char | Phase 2 (Send disabled when empty) | PASS |
| BR-7 | Session timeout 60s -> 404 | Slice 03 (404 handling), Slice 08 (classifyError) | PASS |
| BR-8 | Only 1 active request at a time | Slice 05/06 (@assistant-ui serializes run() calls) | PASS |
| BR-9 | Summary injection (backend) | Backend-only, transparent to frontend | PASS |
| BR-10 | Interview-Ende only once | Slice 07 (sessionIdRef cleared immediately) | PASS |
| BR-11 | CORS allow all origins | Backend config, transparent to frontend | PASS |
| BR-12 | No authentication required | Slice 01 (no auth headers) | PASS |
| BR-13 | API-URL must be valid | Slice 01 (createApiClient throws if null) | PASS |
| BR-14 | SSE-Streams aborted on Panel-Close | Slice 07 (AbortController.abort()) | PASS |
| BR-15 | Session-ID cleared after interview-end | Slice 07 (sessionIdRef.current = null) | PASS |

### Data Fields Coverage

| Field | Required | Covered In | Status |
|-------|----------|------------|--------|
| anonymous_id (UUID v4, localStorage) | Yes | Slice 01 | PASS |
| session_id (UUID, React useRef) | Yes (after /start) | Slice 05 (stored), Slice 06/07 (used) | PASS |
| message (1-10000 chars) | Yes | Slice 06 (extracted from @assistant-ui messages) | PASS |
| apiUrl (from data-api-url) | Yes | Slice 01 (createApiClient), Slice 05 (ChatScreen passes) | PASS |
| SSEEvent type (metadata) | Yes | Slice 01 (type), Slice 02 (parser) | PASS |
| SSEEvent type (text-delta) | Yes | Slice 01 (type), Slice 02 (parser) | PASS |
| SSEEvent type (text-done) | Yes | Slice 01 (type), Slice 02 (parser) | PASS |
| SSEEvent type (error) | Yes | Slice 01 (type), Slice 02 (parser) | PASS |
| EndResponse.summary | Yes | Slice 01 (type), Slice 04 (returned) | PASS |
| EndResponse.message_count | Yes | Slice 01 (type), Slice 04 (returned) | PASS |

**Discovery Coverage:** 57/57 (100%)

---

## Summary

| Metric | Value |
|--------|-------|
| Total Slices | 11 |
| Total Connections | 23 |
| Valid Connections | 23 |
| Orphaned Outputs | 0 |
| Missing Inputs | 0 |
| Deliverable-Consumer Gaps | 0 |
| Discovery Coverage | 100% |
| All Slices APPROVED | Yes (11/11) |

---

VERDICT: READY FOR ORCHESTRATION

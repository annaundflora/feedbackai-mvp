# Slice 06: Implement ChatModelAdapter for Message Flow

> **Slice 6 von 11** for `Backend-Widget-Integration`
>
> | Navigation | |
> |------------|---|
> | **Vorheriger:** | `slice-05-adapter-start-flow.md` |
> | **Nächster:** | `slice-07-interview-end-logic.md` |

---

## Metadata (for Orchestrator)

| Key | Value |
|-----|-------|
| **ID** | `slice-06-adapter-message-flow` |
| **Test** | `cd widget && pnpm test tests/slices/backend-widget-integration/slice-06-adapter-message-flow.test.ts` |
| **E2E** | `false` |
| **Dependencies** | `["slice-03-sse-client-message", "slice-05-adapter-start-flow"]` |

---

## Test-Strategy (for Orchestrator Pipeline)

| Key | Value |
|-----|-------|
| **Stack** | `typescript-vite-react` |
| **Test Command** | `cd widget && pnpm test tests/slices/backend-widget-integration/slice-06-adapter-message-flow.test.ts` |
| **Integration Command** | `cd widget && pnpm test tests/slices/backend-widget-integration/slice-06-adapter-message-flow.test.ts` |
| **Acceptance Command** | `cd widget && pnpm test tests/slices/backend-widget-integration/slice-06-adapter-message-flow.test.ts` |
| **Start Command** | `cd widget && pnpm dev` |
| **Health Endpoint** | N/A |
| **Mocking Strategy** | `mock_external` (fetch mocked) |

---

## Context & Goal

Extends the ChatModelAdapter from Slice 05 to handle the message flow. When `run()` is called and a session_id already exists (from /start), the adapter sends the user's latest message to `/message` and streams the assistant response.

**Key `@assistant-ui` behavior:** When the user sends a message, the runtime calls `run()` with the full message history. The adapter extracts the last user message and sends it to `/message`.

---

## Technical Implementation

### 1. Architecture Impact

| Layer | Changes |
|-------|---------|
| `widget/src/lib/chat-runtime.ts` | MODIFY - Add message flow branch to adapter's `run()` method |

### 2. Data Flow

```
[User sends message -> @assistant-ui calls adapter.run({ messages, abortSignal })]
  |
[Adapter detects: sessionIdRef.current exists -> this is a MESSAGE flow]
  |
[Extract last user message from messages array]
  |
[apiClient.sendMessage(sessionId, message, { signal: abortSignal })]
  |
[streamMessage(response) -> SSEEvent generator]
  |
[text-delta events -> yield { content: [{ type: "text", text: accumulated }] }]
  |
[text-done event -> generator returns]
  |
[@assistant-ui renders assistant response progressively]
```

---

## Acceptance Criteria

1) GIVEN a session_id exists (from previous /start) WHEN the adapter's `run()` is called with user messages THEN it calls `/api/interview/message` with the session_id and last user message text

2) GIVEN the /message SSE stream sends text-delta events WHEN the adapter processes them THEN it yields `{ content: [{ type: "text", text: accumulatedText }] }` progressively

3) GIVEN the /message SSE stream sends a text-done event WHEN the adapter processes it THEN the generator completes

4) GIVEN the /message SSE stream sends an error event WHEN the adapter processes it THEN it throws an Error with the error message

5) GIVEN the adapter receives a 404 error (session expired) WHEN processing the response THEN it throws an Error that can be caught by error handling (Slice 08)

6) GIVEN the adapter receives a 409 error (session completed) WHEN processing the response THEN it throws an Error that can be caught by error handling (Slice 08)

7) GIVEN the adapter's `run()` is called with an abortSignal WHEN the signal is aborted THEN the fetch request is cancelled

---

## Test Cases

### Test File

**Convention:** `widget/tests/slices/backend-widget-integration/slice-06-adapter-message-flow.test.ts`

### Unit Tests (Vitest)

<test_spec>
```typescript
// widget/tests/slices/backend-widget-integration/slice-06-adapter-message-flow.test.ts
import { describe, it, expect, vi, beforeEach } from 'vitest'

describe('ChatModelAdapter - Message Flow', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('should call /message with session_id and last user message', async () => {
    // Arrange: set sessionIdRef.current = 'session-123', mock fetch
    // messages = [{ role: 'assistant', content: '...' }, { role: 'user', content: 'My feedback' }]
    // Act: iterate adapter.run({ messages, abortSignal })
    // Assert: fetch called with /api/interview/message, body: { session_id: 'session-123', message: 'My feedback' }
  })

  it('should yield progressive text from text-deltas', async () => {
    // Arrange: mock SSE stream with text-delta("Das "), text-delta("freut mich"), text-done
    // Act: collect yields
    // Assert: yields { content: [{ type: "text", text: "Das " }] }, { content: [{ type: "text", text: "Das freut mich" }] }
  })

  it('should throw on error event', async () => {
    // Arrange: mock SSE stream with error event
    // Act & Assert: throws Error
  })

  it('should throw on 404 response', async () => {
    // Arrange: mock fetch returning 404
    // Act & Assert: throws ApiError with status 404
  })

  it('should throw on 409 response', async () => {
    // Arrange: mock fetch returning 409
    // Act & Assert: throws ApiError with status 409
  })

  it('should extract last user message from messages array', async () => {
    // Arrange: messages with multiple user messages
    // Act: call adapter.run()
    // Assert: only last user message text sent to /message
  })
})
```
</test_spec>

---

## Integration Contract (GATE 2 PFLICHT)

### Requires From Other Slices

| Slice | Resource | Type | Validation |
|-------|----------|------|------------|
| Slice 01 | `ApiClient.sendMessage()` | Method | `(sessionId, message, options?) => Promise<Response>` |
| Slice 03 | `streamMessage()` | Function | `(response) => AsyncGenerator<SSEEvent>` |
| Slice 05 | `createChatModelAdapter()` | Function | Base adapter with start flow |
| Slice 05 | Session-ID ref | React Ref | `{ current: string \| null }` |

### Provides To Other Slices

| Resource | Type | Consumer | Interface |
|----------|------|----------|-----------|
| Complete ChatModelAdapter | ChatModelAdapter | @assistant-ui runtime | Both start and message flows |

### Integration Validation Tasks

- [ ] Adapter correctly branches between start (no session) and message (has session)
- [ ] Last user message extracted from @assistant-ui messages array
- [ ] SSE events transformed to @assistant-ui yield format
- [ ] Errors propagate for Slice 08 error handling

---

## Code Examples (MANDATORY - GATE 2 PFLICHT)

| Code Example | Section | Mandatory | Notes |
|--------------|---------|-----------|-------|
| `chat-runtime.ts` message branch | lib/chat-runtime.ts | YES | Extends adapter from Slice 05 |

### Updated `run()` in `widget/src/lib/chat-runtime.ts`

```typescript
async *run({ messages, abortSignal }) {
  // START flow: no session yet
  if (!sessionIdRef.current) {
    const anonymousId = getOrCreateAnonymousId()
    const response = await apiClient.startInterview(anonymousId, { signal: abortSignal })

    let text = ''
    for await (const event of streamStart(response)) {
      if (event.type === 'metadata') {
        sessionIdRef.current = event.session_id
      } else if (event.type === 'text-delta') {
        text += event.content
        yield { content: [{ type: 'text' as const, text }] }
      } else if (event.type === 'error') {
        throw new Error(event.message)
      }
    }
    return
  }

  // MESSAGE flow: session exists, send last user message
  const lastUserMessage = [...messages].reverse().find(m => m.role === 'user')
  if (!lastUserMessage) return

  const messageText = lastUserMessage.content
    .filter((c): c is { type: 'text'; text: string } => c.type === 'text')
    .map(c => c.text)
    .join('')

  const response = await apiClient.sendMessage(
    sessionIdRef.current,
    messageText,
    { signal: abortSignal }
  )

  let text = ''
  for await (const event of streamMessage(response)) {
    if (event.type === 'text-delta') {
      text += event.content
      yield { content: [{ type: 'text' as const, text }] }
    } else if (event.type === 'error') {
      throw new Error(event.message)
    }
  }
}
```

---

## Deliverables (SCOPE SAFEGUARD)

<!-- DELIVERABLES_START -->
### Frontend
- [ ] `widget/src/lib/chat-runtime.ts` -- Extend adapter with message flow branch

### Tests
- [ ] `widget/tests/slices/backend-widget-integration/slice-06-adapter-message-flow.test.ts` -- Unit tests for adapter message flow
<!-- DELIVERABLES_END -->

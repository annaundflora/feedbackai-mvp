# Slice 03: Implement SSE Stream Reader for /message Endpoint

> **Slice 3 von 11** for `Backend-Widget-Integration`
>
> | Navigation | |
> |------------|---|
> | **Vorheriger:** | `slice-02-sse-client-start.md` |
> | **Nächster:** | `slice-04-interview-end.md` |

---

## Metadata (for Orchestrator)

| Key | Value |
|-----|-------|
| **ID** | `slice-03-sse-client-message` |
| **Test** | `cd widget && pnpm test tests/slices/backend-widget-integration/slice-03-sse-client-message.test.ts` |
| **E2E** | `false` |
| **Dependencies** | `["slice-01-anonymous-id-api-client", "slice-02-sse-client-start"]` |

---

## Test-Strategy (for Orchestrator Pipeline)

| Key | Value |
|-----|-------|
| **Stack** | `typescript-vite-react` |
| **Test Command** | `cd widget && pnpm test tests/slices/backend-widget-integration/slice-03-sse-client-message.test.ts` |
| **Integration Command** | `cd widget && pnpm test tests/slices/backend-widget-integration/slice-03-sse-client-message.test.ts` |
| **Acceptance Command** | `cd widget && pnpm test tests/slices/backend-widget-integration/slice-03-sse-client-message.test.ts` |
| **Start Command** | `cd widget && pnpm dev` |
| **Health Endpoint** | N/A |
| **Mocking Strategy** | `mock_external` (fetch mocked via vitest) |

---

## Context & Goal

Extends the SSE infrastructure from Slice 02 to handle `/message` endpoint responses. The `/message` endpoint returns the same SSE format as `/start` but without the `metadata` event (session_id already known). Additionally, `/message` may return HTTP 404 (session expired) or 409 (session already completed) instead of SSE streams.

This slice adds:
1. **`streamMessage()`** function - Validates response, handles 404/409 errors specifically, yields SSE events
2. Reuses `readSSEStream()` and `parseSSELine()` from Slice 02

---

## Technical Implementation

### 1. Architecture Impact

| Layer | Changes |
|-------|---------|
| `widget/src/lib/sse-parser.ts` | MODIFY - Add `streamMessage()` function |

### 2. Data Flow

```
[apiClient.sendMessage(sessionId, message)]
  |
[fetch POST /api/interview/message -> Response]
  |
[streamMessage(response)]
  |
[Check response.ok]
  |--- 404 -> throw ApiError("Session not found", 404)
  |--- 409 -> throw ApiError("Session already completed", 409)
  |--- !ok -> throw ApiError(generic, status)
  |--- ok -> readSSEStream(response.body)
  |
[Yields: text-delta -> text-delta -> ... -> text-done]
```

---

## Acceptance Criteria

1) GIVEN a successful Response from /message WHEN `streamMessage(response)` is called THEN it yields text-delta events followed by text-done event (no metadata event)

2) GIVEN a Response with status 404 WHEN `streamMessage(response)` is called THEN it throws `ApiError` with status 404 and message "Session not found"

3) GIVEN a Response with status 409 WHEN `streamMessage(response)` is called THEN it throws `ApiError` with status 409 and message "Session already completed"

4) GIVEN a Response with status 500 WHEN `streamMessage(response)` is called THEN it throws `ApiError` with status 500

5) GIVEN a Response with no body WHEN `streamMessage(response)` is called THEN it throws `ApiError` with message "No response body"

---

## Test Cases

### Test File

**Convention:** `widget/tests/slices/backend-widget-integration/slice-03-sse-client-message.test.ts`

### Unit Tests (Vitest)

<test_spec>
```typescript
// widget/tests/slices/backend-widget-integration/slice-03-sse-client-message.test.ts
import { describe, it, expect } from 'vitest'

describe('streamMessage', () => {
  it('should yield text-delta and text-done events from ok response', async () => {
    // Arrange: mock Response with SSE body (text-delta + text-done)
    // Act: collect events from streamMessage(response)
    // Assert: events are [text-delta, text-done]
  })

  it('should throw ApiError with status 404 for session not found', async () => {
    // Arrange: mock Response with status 404, body: { error: "Session not found" }
    // Act & Assert: throws ApiError, status === 404
  })

  it('should throw ApiError with status 409 for session already completed', async () => {
    // Arrange: mock Response with status 409, body: { error: "Session already completed" }
    // Act & Assert: throws ApiError, status === 409
  })

  it('should throw ApiError for generic server error', async () => {
    // Arrange: mock Response with status 500
    // Act & Assert: throws ApiError, status === 500
  })

  it('should throw ApiError when response has no body', async () => {
    // Arrange: mock Response with ok status but body === null
    // Act & Assert: throws ApiError "No response body"
  })
})
```
</test_spec>

---

## Integration Contract (GATE 2 PFLICHT)

### Requires From Other Slices

| Slice | Resource | Type | Validation |
|-------|----------|------|------------|
| Slice 01 | `SSEEvent` type | TypeScript Type | Union type |
| Slice 01 | `ApiError` class | Class | (message, status, detail?) |
| Slice 01 | `ApiClient.sendMessage()` | Method | Returns `Promise<Response>` |
| Slice 02 | `readSSEStream()` | Function | `(body) => AsyncGenerator<SSEEvent>` |

### Provides To Other Slices

| Resource | Type | Consumer | Interface |
|----------|------|----------|-----------|
| `streamMessage()` | Function | Slice 06 (Adapter Message) | `(response: Response) => AsyncGenerator<SSEEvent>` |

### Integration Validation Tasks

- [ ] `streamMessage` reuses `readSSEStream` from Slice 02
- [ ] 404 and 409 errors correctly classified as ApiError with proper status
- [ ] SSE events from /message match same format as /start (minus metadata)

---

## Code Examples (MANDATORY - GATE 2 PFLICHT)

| Code Example | Section | Mandatory | Notes |
|--------------|---------|-----------|-------|
| `streamMessage` | lib/sse-parser.ts | YES | Added to existing sse-parser.ts |

### Addition to `widget/src/lib/sse-parser.ts`

```typescript
/**
 * Validate /message response and return SSE stream reader.
 * Handles 404 (session expired) and 409 (session completed) specifically.
 */
export async function* streamMessage(response: Response): AsyncGenerator<SSEEvent> {
  if (!response.ok) {
    const error = await response.json().catch(() => ({ error: 'Unknown error' }))
    throw new ApiError(
      error.error || 'Request failed',
      response.status,
      error.detail
    )
  }

  if (!response.body) {
    throw new ApiError('No response body', 0)
  }

  yield* readSSEStream(response.body)
}
```

---

## Deliverables (SCOPE SAFEGUARD)

<!-- DELIVERABLES_START -->
### Frontend
- [ ] `widget/src/lib/sse-parser.ts` -- Add streamMessage() function (modify existing file from Slice 02)

### Tests
- [ ] `widget/tests/slices/backend-widget-integration/slice-03-sse-client-message.test.ts` -- Unit tests for streamMessage with 404/409 handling
<!-- DELIVERABLES_END -->

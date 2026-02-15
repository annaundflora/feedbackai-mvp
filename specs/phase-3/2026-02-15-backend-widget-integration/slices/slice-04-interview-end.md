# Slice 04: Implement Interview-Ende API Call /end

> **Slice 4 von 11** for `Backend-Widget-Integration`
>
> | Navigation | |
> |------------|---|
> | **Vorheriger:** | `slice-03-sse-client-message.md` |
> | **Nächster:** | `slice-05-adapter-start-flow.md` |

---

## Metadata (for Orchestrator)

| Key | Value |
|-----|-------|
| **ID** | `slice-04-interview-end` |
| **Test** | `cd widget && pnpm test tests/slices/backend-widget-integration/slice-04-interview-end.test.ts` |
| **E2E** | `false` |
| **Dependencies** | `["slice-01-anonymous-id-api-client"]` |

---

## Test-Strategy (for Orchestrator Pipeline)

| Key | Value |
|-----|-------|
| **Stack** | `typescript-vite-react` |
| **Test Command** | `cd widget && pnpm test tests/slices/backend-widget-integration/slice-04-interview-end.test.ts` |
| **Integration Command** | `cd widget && pnpm test tests/slices/backend-widget-integration/slice-04-interview-end.test.ts` |
| **Acceptance Command** | `cd widget && pnpm test tests/slices/backend-widget-integration/slice-04-interview-end.test.ts` |
| **Start Command** | `cd widget && pnpm dev` |
| **Health Endpoint** | N/A |
| **Mocking Strategy** | `mock_external` (fetch mocked via vitest) |

---

## Context & Goal

The `/api/interview/end` endpoint returns a JSON response (not SSE) with the interview summary. This slice is simple: it validates the api-client's `endInterview()` method handles all response scenarios correctly.

The `endInterview()` method was already defined in Slice 01's `api-client.ts`. This slice ensures the error handling for 404/409 is correct and adds an `endInterviewSafe()` wrapper for fire-and-forget usage (Panel close should not fail visibly).

---

## Technical Implementation

### 1. Architecture Impact

| Layer | Changes |
|-------|---------|
| `widget/src/lib/api-client.ts` | MODIFY - Add `endInterviewSafe()` method that never throws |

### 2. Data Flow

```
[Panel-Close / Interview-Ende]
  |
[apiClient.endInterview(sessionId)]
  |
[fetch POST /api/interview/end -> JSON Response]
  |--- 200 -> { summary: "...", message_count: N }
  |--- 404 -> ApiError (session not found - already expired/ended)
  |--- 409 -> ApiError (session already completed)
  |--- 500 -> ApiError (server error)
```

```
[Panel-Close (fire-and-forget)]
  |
[apiClient.endInterviewSafe(sessionId)]
  |--- Success -> { summary, message_count }
  |--- Any error -> null (silently ignored, console.warn)
```

---

## Acceptance Criteria

1) GIVEN a valid session_id WHEN `endInterview()` is called THEN it returns `{ summary: string, message_count: number }`

2) GIVEN a 404 response WHEN `endInterview()` is called THEN it throws `ApiError` with status 404

3) GIVEN a 409 response WHEN `endInterview()` is called THEN it throws `ApiError` with status 409

4) GIVEN a 500 response WHEN `endInterview()` is called THEN it throws `ApiError` with status 500

5) GIVEN any scenario WHEN `endInterviewSafe()` is called and the request succeeds THEN it returns the EndResponse

6) GIVEN any error WHEN `endInterviewSafe()` is called THEN it returns `null` and logs `console.warn()`

7) GIVEN an AbortSignal WHEN `endInterviewSafe()` is called with the signal THEN the request is cancellable

---

## Test Cases

### Test File

**Convention:** `widget/tests/slices/backend-widget-integration/slice-04-interview-end.test.ts`

### Unit Tests (Vitest)

<test_spec>
```typescript
// widget/tests/slices/backend-widget-integration/slice-04-interview-end.test.ts
import { describe, it, expect, vi, beforeEach } from 'vitest'

describe('endInterview', () => {
  it('should return summary and message_count on success', async () => {
    // Arrange: mock fetch returning 200 with { summary: "Good feedback", message_count: 5 }
    // Act: const result = await client.endInterview('session-id')
    // Assert: result === { summary: "Good feedback", message_count: 5 }
  })

  it('should throw ApiError with 404 for expired session', async () => {
    // Arrange: mock fetch returning 404
    // Act & Assert: throws ApiError, status 404
  })

  it('should throw ApiError with 409 for completed session', async () => {
    // Arrange: mock fetch returning 409
    // Act & Assert: throws ApiError, status 409
  })

  it('should throw ApiError with 500 for server error', async () => {
    // Arrange: mock fetch returning 500
    // Act & Assert: throws ApiError, status 500
  })
})

describe('endInterviewSafe', () => {
  it('should return EndResponse on success', async () => {
    // Arrange: mock fetch returning 200
    // Act: result = await client.endInterviewSafe('session-id')
    // Assert: result === { summary, message_count }
  })

  it('should return null and console.warn on error', async () => {
    // Arrange: mock fetch returning 500, spy on console.warn
    // Act: result = await client.endInterviewSafe('session-id')
    // Assert: result === null, console.warn called
  })

  it('should return null on network error', async () => {
    // Arrange: mock fetch to reject
    // Act: result = await client.endInterviewSafe('session-id')
    // Assert: result === null
  })
})
```
</test_spec>

---

## Integration Contract (GATE 2 PFLICHT)

### Requires From Other Slices

| Slice | Resource | Type | Validation |
|-------|----------|------|------------|
| Slice 01 | `ApiClient.endInterview()` | Method | `(sessionId, options?) => Promise<EndResponse>` |
| Slice 01 | `ApiError` class | Class | Thrown on non-ok responses |
| Slice 01 | `EndResponse` type | Type | `{ summary, message_count }` |

### Provides To Other Slices

| Resource | Type | Consumer | Interface |
|----------|------|----------|-----------|
| `ApiClient.endInterviewSafe()` | Method | Slice 07 (Ende Logic) | `(sessionId, options?) => Promise<EndResponse \| null>` |

### Integration Validation Tasks

- [ ] `endInterview()` correctly parses JSON response
- [ ] `endInterviewSafe()` never throws, returns null on error
- [ ] Both methods support AbortSignal

---

## Code Examples (MANDATORY - GATE 2 PFLICHT)

| Code Example | Section | Mandatory | Notes |
|--------------|---------|-----------|-------|
| `endInterviewSafe` | lib/api-client.ts | YES | Added to ApiClient interface |

### Addition to `widget/src/lib/api-client.ts`

```typescript
// Add to ApiClient interface:
export interface ApiClient {
  // ... existing methods from Slice 01
  endInterviewSafe(sessionId: string, options?: { signal?: AbortSignal }): Promise<EndResponse | null>
}

// Add to createApiClient return object:
async endInterviewSafe(sessionId, options) {
  try {
    return await this.endInterview(sessionId, options)
  } catch (error) {
    console.warn('Failed to end interview:', error)
    return null
  }
},
```

---

## Deliverables (SCOPE SAFEGUARD)

<!-- DELIVERABLES_START -->
### Frontend
- [ ] `widget/src/lib/api-client.ts` -- Add endInterviewSafe() method to ApiClient

### Tests
- [ ] `widget/tests/slices/backend-widget-integration/slice-04-interview-end.test.ts` -- Unit tests for endInterview + endInterviewSafe
<!-- DELIVERABLES_END -->

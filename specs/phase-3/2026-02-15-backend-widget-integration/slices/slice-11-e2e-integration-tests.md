# Slice 11: E2E Integration Tests

> **Slice 11 von 11** for `Backend-Widget-Integration`
>
> | Navigation | |
> |------------|---|
> | **Vorheriger:** | `slice-10-assistant-message-rendering.md` |
> | **Nächster:** | -- |

---

## Metadata (for Orchestrator)

| Key | Value |
|-----|-------|
| **ID** | `slice-11-e2e-integration-tests` |
| **Test** | `cd widget && pnpm test tests/slices/backend-widget-integration/slice-11-e2e-integration.test.ts` |
| **E2E** | `false` |
| **Dependencies** | `["slice-01-anonymous-id-api-client", "slice-02-sse-client-start", "slice-03-sse-client-message", "slice-04-interview-end", "slice-05-adapter-start-flow", "slice-06-adapter-message-flow", "slice-07-interview-end-logic", "slice-08-error-handling", "slice-09-loading-typing-indicators", "slice-10-assistant-message-rendering"]` |

---

## Test-Strategy (for Orchestrator Pipeline)

| Key | Value |
|-----|-------|
| **Stack** | `typescript-vite-react` |
| **Test Command** | `cd widget && pnpm test tests/slices/backend-widget-integration/slice-11-e2e-integration.test.ts` |
| **Integration Command** | `cd widget && pnpm test tests/slices/backend-widget-integration/slice-11-e2e-integration.test.ts` |
| **Acceptance Command** | `cd widget && pnpm test tests/slices/backend-widget-integration/slice-11-e2e-integration.test.ts` |
| **Start Command** | `cd widget && pnpm dev` |
| **Health Endpoint** | N/A |
| **Mocking Strategy** | `mock_external` (fetch mocked to simulate full backend SSE flow) |

---

## Context & Goal

This slice contains no new code. It's a comprehensive integration test suite that validates the complete E2E flow through all slices using mocked fetch responses that simulate the real backend SSE protocol.

Test scenarios:
1. **Happy Path**: Consent -> Start -> Chat (3 exchanges) -> Close -> ThankYou
2. **Error Recovery**: Network error -> Retry -> Success
3. **Session Expired**: 404 -> "Neu starten" -> Consent
4. **Session Completed**: 409 -> Auto-redirect ThankYou
5. **Stream Abort**: Close during streaming -> Cleanup -> ThankYou
6. **Edge Cases**: Multiple rapid messages, empty input prevention

---

## Technical Implementation

### 1. Architecture Impact

| Layer | Changes |
|-------|---------|
| `widget/tests/slices/backend-widget-integration/slice-11-e2e-integration.test.ts` | NEW - Integration test file |
| `widget/tests/slices/backend-widget-integration/helpers/mock-sse.ts` | NEW - Helper to create mock SSE ReadableStreams |

### 2. Mock SSE Helper

A helper function that creates a `ReadableStream` emitting SSE-formatted data:

```typescript
function createMockSSEStream(events: SSEEvent[]): ReadableStream<Uint8Array> {
  // Converts SSEEvent[] to a ReadableStream matching backend format
  // Each event: "data: {json}\n\n"
}
```

---

## Acceptance Criteria

1) GIVEN a mocked backend WHEN the complete happy path is executed (Consent -> 3 message rounds -> Close) THEN all states transition correctly and ThankYou screen shows

2) GIVEN a network error on /start WHEN the user clicks "Erneut versuchen" THEN /start is called again and the interview proceeds

3) GIVEN a 404 response on /message WHEN the ErrorDisplay shows THEN clicking "Neu starten" returns to the Consent screen

4) GIVEN a 409 response on /message WHEN the error is detected THEN the screen transitions to ThankYou automatically

5) GIVEN the panel is closed during assistant streaming WHEN the cleanup runs THEN the SSE stream is aborted AND /end is called

6) GIVEN the full flow completes WHEN checking localStorage THEN `feedbackai_anonymous_id` contains a valid UUID v4

---

## Test Cases

### Test File

**Convention:** `widget/tests/slices/backend-widget-integration/slice-11-e2e-integration.test.ts`

### Integration Tests (Vitest + React Testing Library)

<test_spec>
```typescript
// widget/tests/slices/backend-widget-integration/slice-11-e2e-integration.test.ts
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react'

describe('E2E Integration: Backend-Widget-Integration', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.restoreAllMocks()
  })

  describe('Happy Path', () => {
    it('should complete full interview flow: Consent -> Chat -> ThankYou', async () => {
      // Arrange: mock fetch for /start (SSE), /message (SSE x2), /end (JSON)
      // Act:
      //   1. Click "Los geht's"
      //   2. Wait for assistant greeting (from /start SSE)
      //   3. Type "Great service!" and send
      //   4. Wait for assistant response (from /message SSE)
      //   5. Close panel (X button)
      //   6. Verify ThankYou screen
      // Assert: All API calls made in correct order with correct payloads
    })

    it('should persist anonymous_id in localStorage', async () => {
      // After completing flow
      // Assert: localStorage.getItem('feedbackai_anonymous_id') is valid UUID v4
    })
  })

  describe('Error Recovery', () => {
    it('should retry /start on network error and succeed', async () => {
      // Arrange: first fetch rejects, second succeeds
      // Act: Click "Los geht's", see error, click "Erneut versuchen"
      // Assert: Interview proceeds normally after retry
    })

    it('should show "Neu starten" on 404 and return to consent', async () => {
      // Arrange: /message returns 404
      // Act: Send message, see error, click "Neu starten"
      // Assert: Screen shows consent
    })

    it('should auto-redirect to ThankYou on 409', async () => {
      // Arrange: /message returns 409
      // Act: Send message
      // Assert: ThankYou screen visible
    })
  })

  describe('Stream Cleanup', () => {
    it('should abort SSE stream when panel closed during streaming', async () => {
      // Arrange: /start SSE stream that doesn't complete
      // Act: Close panel during streaming
      // Assert: AbortController.abort() called, /end called
    })
  })

  describe('Edge Cases', () => {
    it('should disable composer during streaming', async () => {
      // During /start or /message streaming
      // Assert: Composer input is disabled
    })

    it('should prevent sending empty messages', async () => {
      // Assert: Send button disabled when input is empty
    })

    it('should handle multiple rapid messages correctly (queue behavior)', async () => {
      // Arrange: mock fetch for /start (success), then /message x3
      // Act: Complete /start, then rapidly send 3 messages in sequence
      // Assert: Each /message call completes before next starts (no concurrent requests)
      //         Composer disabled between sends
      //         All 3 assistant responses appear in correct order
    })
  })
})
```
</test_spec>

### Helper

```typescript
// widget/tests/slices/backend-widget-integration/helpers/mock-sse.ts
// SSEEvent type is defined in widget/src/lib/types.ts (created in Slice 01)
import type { SSEEvent } from '../../../../src/lib/types'

export function createMockSSEResponse(events: SSEEvent[], status = 200): Response {
  const encoder = new TextEncoder()
  const chunks = events.map(e => `data: ${JSON.stringify(e)}\n\n`)

  const stream = new ReadableStream<Uint8Array>({
    start(controller) {
      for (const chunk of chunks) {
        controller.enqueue(encoder.encode(chunk))
      }
      controller.close()
    }
  })

  return new Response(stream, {
    status,
    headers: { 'Content-Type': 'text/event-stream' }
  })
}
```

---

## Integration Contract (GATE 2 PFLICHT)

### Requires From Other Slices

| Slice | Resource | Type | Validation |
|-------|----------|------|------------|
| All Slices 01-10 | All implemented modules | Various | Complete feature must be working |

### Provides To Other Slices

| Resource | Type | Consumer | Interface |
|----------|------|----------|-----------|
| Test helper `createMockSSEResponse` | Function | Future tests | `(events, status?) => Response` |

### Integration Validation Tasks

- [ ] All 11 slices work together end-to-end
- [ ] Complete happy path validated
- [ ] Error scenarios validated
- [ ] Cleanup scenarios validated

---

## Code Examples (MANDATORY - GATE 2 PFLICHT)

| Code Example | Section | Mandatory | Notes |
|--------------|---------|-----------|-------|
| `mock-sse.ts` helper | tests/helpers/ | YES | SSE mock helper |
| E2E test file | tests/slice-11 | YES | Integration test suite |

---

## Deliverables (SCOPE SAFEGUARD)

<!-- DELIVERABLES_START -->
### Tests
- [ ] `widget/tests/slices/backend-widget-integration/helpers/mock-sse.ts` -- SSE mock response helper
- [ ] `widget/tests/slices/backend-widget-integration/slice-11-e2e-integration.test.ts` -- E2E integration test suite
<!-- DELIVERABLES_END -->

# Slice 02: SSE-Client für /start Endpoint

> **Slice 2 von 11** für `Backend-Widget-Integration`
>
> | Navigation | |
> |------------|---|
> | **Vorheriger:** | `slice-01-anonymous-id-api-client.md` |
> | **Nächster:** | `slice-03-sse-client-message.md` |

---

## Metadata (für Orchestrator)

| Key | Value |
|-----|-------|
| **ID** | `slice-02-sse-client-start` |
| **Test** | `cd widget && pnpm test tests/slices/backend-widget-integration/slice-02-sse-client-start.test.ts` |
| **E2E** | `false` |
| **Dependencies** | `["slice-01-anonymous-id-api-client"]` |

---

## Test-Strategy (für Orchestrator Pipeline)

> **Quelle:** Auto-detected basierend auf Repo-Indikatoren.

| Key | Value |
|-----|-------|
| **Stack** | `typescript-vite-react` |
| **Test Command** | `cd widget && pnpm test tests/slices/backend-widget-integration/slice-02-sse-client-start.test.ts` |
| **Integration Command** | `cd widget && pnpm test tests/slices/backend-widget-integration/slice-02-sse-client-start.test.ts` |
| **Acceptance Command** | `cd widget && pnpm test tests/slices/backend-widget-integration/slice-02-sse-client-start.test.ts` |
| **Start Command** | `cd widget && pnpm dev` |
| **Health Endpoint** | N/A |
| **Mocking Strategy** | `mock_external` (fetch + ReadableStream mocked via vitest) |

---

## Slice-Übersicht

| # | Slice | Status | Datei |
|---|-------|--------|-------|
| 1 | Anonymous-ID + API-Client | Ready | `slice-01-anonymous-id-api-client.md` |
| 2 | **SSE-Client /start** | **Ready** | `slice-02-sse-client-start.md` |
| 3 | SSE-Client /message | Pending | `slice-03-sse-client-message.md` |
| 4-11 | ... | Pending | ... |

---

## Kontext & Ziel

Der Backend `/api/interview/start` Endpoint erwartet POST mit `{anonymous_id}` und antwortet mit einem SSE-Stream (Server-Sent Events) im Format `data: {...}\n\n`.

**Problem:**
- Native `EventSource` API unterstützt nur GET Requests (keine POST mit Body)
- Backend nutzt POST-basierte SSE-Endpoints (architectural constraint)
- Manuelles SSE-Parsing erforderlich

**Lösung:**
Implement SSE-Client mit Fetch API + ReadableStream + manuelles Line-Parsing für Event-Format `data: {...}\n\n`.

**SSE Event-Types (Backend):**
1. `metadata` - Enthält `session_id` (UUID) nach Interview-Start
2. `text-delta` - Enthält `content` (Token-Chunk vom LLM)
3. `text-done` - Signalisiert Ende der LLM-Antwort
4. `error` - Enthält `message` bei Backend-Fehler

**Backend SSE-Format (aus `service.py`):**
```
data: {"type":"metadata","session_id":"uuid-here"}\n\n
data: {"type":"text-delta","content":"Hal"}\n\n
data: {"type":"text-delta","content":"lo!"}\n\n
data: {"type":"text-done"}\n\n
```

**Scope:**
- SSE line parser: `parseSSELine(line)` für `data: {...}\n\n` Format
- Stream reader: `readSSEStream(body)` als Async Generator
- Stream wrapper: `streamStart(response)` validiert Response + yielded SSE events
- Timeout-Handling (30s default via AbortController)
- NO UI-Komponenten in diesem Slice (kommt in Slice 05/09/10)

---

## Technische Umsetzung

### Architektur-Kontext (aus architecture.md)

> **Quelle:** `architecture.md` → Frontend API Abstraction Layer, Services & Processing

```
[User clicks "Los geht's"]
       |
[ChatModelAdapter.run() called by @assistant-ui]
       |
[apiClient.startInterview(anonymous_id) → Fetch POST /start]
       |
[streamStart(response) → ReadableStream<Uint8Array>]
       |
[readSSEStream(body) → AsyncGenerator<SSEEvent>]
       |
[parseSSELine(line) → SSEEvent object]
       |
[SSE Stream: metadata → session_id stored in React State]
       |
[SSE Stream: text-delta → yield to @assistant-ui → UI updates]
       |
[SSE Stream: text-done → Composer enabled]
```

### 1. Architektur-Impact

| Layer | Änderungen |
|-------|------------|
| `widget/src/lib/sse-parser.ts` | NEW - SSE line parser + stream reader + streamStart wrapper |
| `widget/src/lib/types.ts` | EXTEND - SSEEvent type (bereits in Slice 01 definiert) |

### 2. Datenfluss

```
[apiClient.startInterview(anonymousId, { signal })]
  |
[fetch POST /api/interview/start → Response mit ReadableStream body]
  |
[streamStart(response) validiert Response.ok]
  |
[readSSEStream(response.body) → AsyncGenerator<SSEEvent>]
  |
[response.body.getReader() → ReadableStream Reader]
  |
[read() loop: bytes → TextDecoder → UTF-8 string]
  |
[Split by '\n\n' → Lines buffer]
  |
[Each line: parseSSELine(line) → SSEEvent | null]
  |
[yield SSEEvent to caller (async generator)]
  |
[On abort or stream close: cleanup + return]
```

### 3. SSE Parsing Logic

Die `sse-starlette` Backend-Library sendet:
- Each event as `data: {json}\n\n` (with `data:` prefix)
- Events separated by double newline `\n\n`
- Stream uses `TextDecoderStream` for UTF-8 decoding

Parsing algorithm:
1. Read chunks from ReadableStream via `getReader()`
2. Decode Uint8Array to string via TextDecoder
3. Buffer partial lines (chunks may split mid-line)
4. Split by `\n\n` to get complete events
5. Strip `data: ` prefix, JSON.parse the rest
6. Yield typed SSEEvent

### 4. Dependencies

- Existing: `widget/src/lib/api-client.ts` (Slice 01 - provides `ApiClient` interface)
- Existing: `widget/src/lib/types.ts` (Slice 01 - provides `SSEEvent`, `ApiError` types)
- New: None (uses native browser APIs: fetch, ReadableStream, TextDecoder)

---

## UI Requirements

No UI changes in this slice. Pure library/utility code.

**Note:** UI-Integration (Loading-Indicator, Typing-Indicator, Assistant-Message) kommt in Slice 05/09/10.

---

## Acceptance Criteria

1) GIVEN a string `"data: {\"type\":\"metadata\",\"session_id\":\"abc\"}"` WHEN `parseSSELine()` is called THEN it returns `{ type: 'metadata', session_id: 'abc' }`

2) GIVEN a string `"data: {\"type\":\"text-delta\",\"content\":\"Hallo\"}"` WHEN `parseSSELine()` is called THEN it returns `{ type: 'text-delta', content: 'Hallo' }`

3) GIVEN a string `"data: {\"type\":\"text-done\"}"` WHEN `parseSSELine()` is called THEN it returns `{ type: 'text-done' }`

4) GIVEN a string `"data: {\"type\":\"error\",\"message\":\"LLM failed\"}"` WHEN `parseSSELine()` is called THEN it returns `{ type: 'error', message: 'LLM failed' }`

5) GIVEN an empty string or comment line (`:`) WHEN `parseSSELine()` is called THEN it returns `null`

6) GIVEN a ReadableStream that emits SSE-formatted data WHEN `readSSEStream()` is called THEN it yields SSEEvent objects in order as an async generator

7) GIVEN a ReadableStream that splits a single event across two chunks WHEN `readSSEStream()` is called THEN the event is correctly buffered and parsed

8) GIVEN a fetch Response from /start with SSE body WHEN `streamStart(response)` is called THEN it yields metadata event first, then text-delta events, then text-done event

9) GIVEN a Response with non-ok status (e.g. 500) WHEN `streamStart(response)` is called THEN it throws an ApiError with the status code

10) GIVEN invalid JSON in a `data:` line WHEN `parseSSELine()` is called THEN it returns `null` (skip malformed events) AND logs warning to console

11) GIVEN an AbortSignal is passed to apiClient.startInterview WHEN the ReadableStream is being read AND signal is aborted THEN the stream reader stops AND reader lock is released

12) GIVEN a Response without body (body is null) WHEN `streamStart(response)` is called THEN it throws an ApiError with message "No response body"

---

## Test Cases

### Test File

**Convention:** `widget/tests/slices/backend-widget-integration/slice-02-sse-client-start.test.ts`

### Unit Tests (Vitest)

<test_spec>
```typescript
// widget/tests/slices/backend-widget-integration/slice-02-sse-client-start.test.ts
import { describe, it, expect, vi, beforeEach } from 'vitest'

describe('SSE Parser - parseSSELine', () => {
  it('should parse metadata event', () => {
    // Arrange
    const line = 'data: {"type":"metadata","session_id":"abc-123"}'
    // Act
    const event = parseSSELine(line)
    // Assert
    expect(event).toEqual({ type: 'metadata', session_id: 'abc-123' })
  })

  it('should parse text-delta event', () => {
    // Arrange
    const line = 'data: {"type":"text-delta","content":"Hello"}'
    // Act
    const event = parseSSELine(line)
    // Assert
    expect(event).toEqual({ type: 'text-delta', content: 'Hello' })
  })

  it('should parse text-done event', () => {
    // Arrange
    const line = 'data: {"type":"text-done"}'
    // Act
    const event = parseSSELine(line)
    // Assert
    expect(event).toEqual({ type: 'text-done' })
  })

  it('should parse error event', () => {
    // Arrange
    const line = 'data: {"type":"error","message":"fail"}'
    // Act
    const event = parseSSELine(line)
    // Assert
    expect(event).toEqual({ type: 'error', message: 'fail' })
  })

  it('should return null for empty lines', () => {
    // Arrange
    const line = ''
    // Act
    const event = parseSSELine(line)
    // Assert
    expect(event).toBeNull()
  })

  it('should return null for SSE comments', () => {
    // Arrange
    const line = ': keep-alive'
    // Act
    const event = parseSSELine(line)
    // Assert
    expect(event).toBeNull()
  })

  it('should return null for invalid JSON and not throw', () => {
    // Arrange
    const line = 'data: not-json'
    // Act
    const event = parseSSELine(line)
    // Assert
    expect(event).toBeNull()
  })

  it('should return null for lines without data prefix', () => {
    // Arrange
    const line = '{"type":"metadata","session_id":"test"}'
    // Act
    const event = parseSSELine(line)
    // Assert
    expect(event).toBeNull()
  })
})

describe('SSE Stream Reader - readSSEStream', () => {
  it('should yield events from ReadableStream', async () => {
    // Arrange: create ReadableStream pushing SSE-formatted chunks
    const sseData = 'data: {"type":"text-delta","content":"Hello"}\n\ndata: {"type":"text-done"}\n\n'
    const stream = new ReadableStream({
      start(controller) {
        controller.enqueue(new TextEncoder().encode(sseData))
        controller.close()
      }
    })

    // Act: collect all events from readSSEStream(stream)
    const events = []
    for await (const event of readSSEStream(stream)) {
      events.push(event)
    }

    // Assert: events match expected SSEEvent objects in order
    expect(events).toEqual([
      { type: 'text-delta', content: 'Hello' },
      { type: 'text-done' }
    ])
  })

  it('should handle events split across chunks', async () => {
    // Arrange: split a single "data: {...}\n\n" across two chunks
    const chunk1 = 'data: {"type":"text-del'
    const chunk2 = 'ta","content":"Test"}\n\n'
    const stream = new ReadableStream({
      start(controller) {
        controller.enqueue(new TextEncoder().encode(chunk1))
        controller.enqueue(new TextEncoder().encode(chunk2))
        controller.close()
      }
    })

    // Act: collect events
    const events = []
    for await (const event of readSSEStream(stream)) {
      events.push(event)
    }

    // Assert: correctly assembled and parsed
    expect(events).toEqual([{ type: 'text-delta', content: 'Test' }])
  })

  it('should handle multiple events in single chunk', async () => {
    // Arrange: single chunk with multiple "data: {...}\n\n" events
    const sseData = 'data: {"type":"metadata","session_id":"abc"}\n\ndata: {"type":"text-delta","content":"Hi"}\n\n'
    const stream = new ReadableStream({
      start(controller) {
        controller.enqueue(new TextEncoder().encode(sseData))
        controller.close()
      }
    })

    // Act: collect events
    const events = []
    for await (const event of readSSEStream(stream)) {
      events.push(event)
    }

    // Assert: all events yielded
    expect(events).toEqual([
      { type: 'metadata', session_id: 'abc' },
      { type: 'text-delta', content: 'Hi' }
    ])
  })

  it('should skip malformed events and continue', async () => {
    // Arrange: stream with valid, malformed, valid events
    const sseData = 'data: {"type":"text-delta","content":"Valid1"}\n\ndata: invalid json\n\ndata: {"type":"text-delta","content":"Valid2"}\n\n'
    const stream = new ReadableStream({
      start(controller) {
        controller.enqueue(new TextEncoder().encode(sseData))
        controller.close()
      }
    })

    // Act: collect events
    const events = []
    for await (const event of readSSEStream(stream)) {
      events.push(event)
    }

    // Assert: 2 valid events yielded, malformed skipped
    expect(events).toEqual([
      { type: 'text-delta', content: 'Valid1' },
      { type: 'text-delta', content: 'Valid2' }
    ])
  })

  it('should process remaining buffer after stream ends', async () => {
    // Arrange: stream ends without final \n\n
    const sseData = 'data: {"type":"text-delta","content":"Final"}'
    const stream = new ReadableStream({
      start(controller) {
        controller.enqueue(new TextEncoder().encode(sseData))
        controller.close()
      }
    })

    // Act
    const events = []
    for await (const event of readSSEStream(stream)) {
      events.push(event)
    }

    // Assert
    expect(events).toEqual([{ type: 'text-delta', content: 'Final' }])
  })
})

describe('streamStart', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('should throw ApiError for non-ok response', async () => {
    // Arrange: mock Response with status 500
    const mockResponse = {
      ok: false,
      status: 500,
      json: vi.fn().mockResolvedValue({ error: 'Internal Server Error' })
    }

    // Act & Assert: throws ApiError with status 500
    const generator = streamStart(mockResponse as unknown as Response)
    await expect(generator.next()).rejects.toThrow('Internal Server Error')
  })

  it('should throw ApiError when response has no body', async () => {
    // Arrange
    const mockResponse = {
      ok: true,
      body: null
    }

    // Act & Assert
    const generator = streamStart(mockResponse as unknown as Response)
    await expect(generator.next()).rejects.toThrow('No response body')
  })

  it('should delegate to readSSEStream for ok response', async () => {
    // Arrange
    const sseData = 'data: {"type":"text-done"}\n\n'
    const mockResponse = {
      ok: true,
      body: new ReadableStream({
        start(controller) {
          controller.enqueue(new TextEncoder().encode(sseData))
          controller.close()
        }
      })
    }

    // Act
    const events = []
    for await (const event of streamStart(mockResponse as unknown as Response)) {
      events.push(event)
    }

    // Assert
    expect(events).toEqual([{ type: 'text-done' }])
  })
})
```
</test_spec>

---

## Definition of Done

- [x] Acceptance criteria are clear and complete
- [x] Security/Privacy aspects considered (no sensitive data in SSE, only anonymous_id + session_id)
- [x] No UI changes needed
- [x] Error-Handling documented (invalid JSON, non-ok response, no body)
- [x] AbortController-Support für Cleanup (via reader.releaseLock())

---

## Integration Contract (GATE 2 PFLICHT)

### Requires From Other Slices

| Slice | Resource | Type | Validation |
|-------|----------|------|------------|
| slice-01 | `SSEEvent` type | TypeScript Type | Union type with metadata, text-delta, text-done, error |
| slice-01 | `ApiError` class | Class | Constructor: (message, status, detail?) |
| slice-01 | `ApiClient.startInterview()` | Method | Returns `Promise<Response>` |

### Provides To Other Slices

| Resource | Type | Consumer | Interface |
|----------|------|----------|-----------|
| `parseSSELine()` | Function | Slice 03 (SSE /message) | `(line: string) => SSEEvent \| null` |
| `readSSEStream()` | Function | Slice 03, 05, 06 | `(body: ReadableStream<Uint8Array>) => AsyncGenerator<SSEEvent>` |
| `streamStart()` | Function | Slice 05 (Adapter Start) | `(response: Response) => AsyncGenerator<SSEEvent>` |

### Integration Validation Tasks

- [ ] `parseSSELine` correctly parses all 4 event types from backend
- [ ] `readSSEStream` handles chunked streams and buffering across chunk boundaries
- [ ] `streamStart` validates Response.ok before streaming AND throws ApiError for non-ok
- [ ] readSSEStream releases reader lock in finally block to prevent memory leaks
- [ ] parseSSELine is reusable for Slice 03 (same SSE format for /message)

---

## Code Examples (MANDATORY - GATE 2 PFLICHT)

| Code Example | Section | Mandatory | Notes |
|--------------|---------|-----------|-------|
| `sse-parser.ts` | lib/sse-parser.ts | YES | parseSSELine + readSSEStream + streamStart |

### `widget/src/lib/sse-parser.ts`

```typescript
import type { SSEEvent } from './types'
import { ApiError } from './types'

/**
 * Parse a single SSE data line into a typed SSEEvent.
 * Returns null for empty lines, comments, or malformed JSON.
 *
 * @param line - SSE line (e.g., "data: {...}")
 * @returns Parsed SSEEvent or null if invalid
 */
export function parseSSELine(line: string): SSEEvent | null {
  const trimmed = line.trim()
  if (!trimmed || trimmed.startsWith(':')) return null

  const dataPrefix = 'data: '
  if (!trimmed.startsWith(dataPrefix)) return null

  const jsonStr = trimmed.slice(dataPrefix.length)
  try {
    return JSON.parse(jsonStr) as SSEEvent
  } catch {
    // Skip malformed JSON - don't throw to allow stream to continue
    return null
  }
}

/**
 * Read a ReadableStream of SSE data and yield parsed SSEEvent objects.
 * Handles buffering for events split across chunks.
 *
 * @param body - ReadableStream from fetch Response.body
 * @yields Parsed SSEEvent objects
 */
export async function* readSSEStream(
  body: ReadableStream<Uint8Array>
): AsyncGenerator<SSEEvent> {
  const reader = body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  try {
    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })

      // Split by double newline (SSE event boundary)
      const parts = buffer.split('\n\n')
      // Last part may be incomplete - keep in buffer
      buffer = parts.pop() ?? ''

      for (const part of parts) {
        // Each part may have multiple lines (event: ...\ndata: ...)
        // We only care about data: lines
        for (const line of part.split('\n')) {
          const event = parseSSELine(line)
          if (event) yield event
        }
      }
    }

    // Process remaining buffer (for events without final \n\n)
    if (buffer.trim()) {
      for (const line of buffer.split('\n')) {
        const event = parseSSELine(line)
        if (event) yield event
      }
    }
  } finally {
    // Critical: release reader lock to prevent memory leaks
    reader.releaseLock()
  }
}

/**
 * Validate response and return SSE stream reader.
 * Throws ApiError for non-ok responses or missing body.
 *
 * @param response - Fetch Response from API call
 * @yields Parsed SSEEvent objects
 * @throws ApiError if response is not ok or body is missing
 */
export async function* streamStart(response: Response): AsyncGenerator<SSEEvent> {
  if (!response.ok) {
    const error = await response.json().catch(() => ({ error: 'Unknown error' }))
    throw new ApiError(error.error || 'Request failed', response.status, error.detail)
  }

  if (!response.body) {
    throw new ApiError('No response body', 0)
  }

  yield* readSSEStream(response.body)
}
```

---

## Constraints & Notes

**Applies to:**
- `widget/src/lib/sse-parser.ts` only
- No UI components modified

**API Contract:**
- Backend sends SSE in format `data: {...}\n\n` (double newline = event separator)
- Events arrive in order: metadata → text-delta (multiple) → text-done OR error
- Backend may send invalid JSON or unknown event types (parser must handle gracefully)

**Boundaries:**
- ChatModelAdapter integration is NOT in this slice (Slice 05)
- Loading/Typing indicators are NOT in this slice (Slice 09)
- Error-Display UI is NOT in this slice (Slice 08)

**Technical Notes:**
- TextDecoder with `{ stream: true }` option handles multi-byte UTF-8 characters across chunk boundaries
- Buffer accumulates incomplete lines until `\n\n` separator arrives
- reader.releaseLock() in finally block is CRITICAL to prevent memory leaks
- AbortController support is handled by fetch() API, not by stream reader directly

---

## Deliverables (SCOPE SAFEGUARD)

<!-- DELIVERABLES_START -->
### Frontend
- [ ] `widget/src/lib/sse-parser.ts` -- SSE parser (parseSSELine, readSSEStream, streamStart)

### Tests
- [ ] `widget/tests/slices/backend-widget-integration/slice-02-sse-client-start.test.ts` -- Unit tests for SSE parsing and stream reading
<!-- DELIVERABLES_END -->

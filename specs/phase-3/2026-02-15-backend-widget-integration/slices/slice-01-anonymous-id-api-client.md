# Slice 01: Implement Anonymous-ID Manager + API-Client Foundation

> **Slice 1 von 11** for `Backend-Widget-Integration`
>
> | Navigation | |
> |------------|---|
> | **Vorheriger:** | -- |
> | **Nächster:** | `slice-02-sse-client-start.md` |

---

## Metadata (for Orchestrator)

| Key | Value |
|-----|-------|
| **ID** | `slice-01-anonymous-id-api-client` |
| **Test** | `cd widget && pnpm test tests/slices/backend-widget-integration/slice-01-anonymous-id-api-client.test.ts` |
| **E2E** | `false` |
| **Dependencies** | `[]` |

---

## Test-Strategy (for Orchestrator Pipeline)

| Key | Value |
|-----|-------|
| **Stack** | `typescript-vite-react` |
| **Test Command** | `cd widget && pnpm test tests/slices/backend-widget-integration/slice-01-anonymous-id-api-client.test.ts` |
| **Integration Command** | `cd widget && pnpm test tests/slices/backend-widget-integration/slice-01-anonymous-id-api-client.test.ts` |
| **Acceptance Command** | `cd widget && pnpm test tests/slices/backend-widget-integration/slice-01-anonymous-id-api-client.test.ts` |
| **Start Command** | `cd widget && pnpm dev` |
| **Health Endpoint** | N/A |
| **Mocking Strategy** | `mock_external` (localStorage + fetch mocked via vitest) |

---

## Slice-Overview

| # | Slice | Status | File |
|---|-------|--------|------|
| 1 | **Anonymous-ID + API-Client** | **Ready** | `slice-01-anonymous-id-api-client.md` |
| 2 | SSE-Client /start | Pending | `slice-02-sse-client-start.md` |
| 3-11 | ... | Pending | ... |

---

## Context & Goal

The widget (Phase 2) has no backend connection. This slice creates the foundation layer:

1. **Anonymous-ID Manager** - Generates and persists a UUID v4 via `crypto.randomUUID()` in `localStorage` key `feedbackai_anonymous_id`
2. **API-Client** - Fetch wrapper with base URL from `data-api-url`, AbortController support, and typed request/response interfaces

These are pure utility modules with no UI changes. All subsequent slices depend on this foundation.

**Current State:**
- `config.ts` already parses `data-api-url` from script tag → `apiUrl: string | null`
- No API-client or anonymous-id management exists yet

---

## Technical Implementation

### Architecture Context (from architecture.md)

> **Source:** `architecture.md` -> Frontend API Abstraction Layer, Utils

```
[User clicks "Los geht's"]
       |
[Anonymous-ID generated/loaded from localStorage]
       |
[API-Client uses apiUrl from config]
       |
[Fetch POST to backend endpoints]
```

### 1. Architecture Impact

| Layer | Changes |
|-------|---------|
| `widget/src/lib/anonymous-id.ts` | NEW - Anonymous-ID Manager (generate, get, validate) |
| `widget/src/lib/api-client.ts` | NEW - Fetch wrapper with typed interfaces for all 3 endpoints |
| `widget/src/lib/types.ts` | NEW - Shared TypeScript types (SSEEvent, DTOs) |

### 2. Data Flow

```
[First Consent-Accept]
  |
[getOrCreateAnonymousId()]
  |
[crypto.randomUUID() -> localStorage.setItem('feedbackai_anonymous_id', uuid)]
  |
[Returns: anonymous_id string]
```

```
[API Call needed]
  |
[apiClient.startInterview(anonymous_id) / .sendMessage(session_id, message) / .endInterview(session_id)]
  |
[fetch(apiUrl + endpoint, { method: 'POST', body: JSON, headers, signal })]
  |
[Returns: Response object (stream or JSON)]
```

### 3. Dependencies

- Existing: `widget/src/config.ts` (provides `apiUrl`)
- New: None (uses native browser APIs only)

---

## UI Requirements

No UI changes in this slice. Pure library/utility code.

---

## Acceptance Criteria

1) GIVEN the widget loads for the first time WHEN `getOrCreateAnonymousId()` is called THEN a UUID v4 is generated via `crypto.randomUUID()` AND stored in `localStorage` key `feedbackai_anonymous_id` AND returned

2) GIVEN an anonymous_id already exists in localStorage WHEN `getOrCreateAnonymousId()` is called THEN the existing value is returned without generating a new one

3) GIVEN localStorage is blocked (SecurityError) WHEN `getOrCreateAnonymousId()` is called THEN a fresh UUID is generated and returned (no persistence, no throw)

4) GIVEN a valid `apiUrl` from config WHEN `createApiClient(apiUrl)` is called THEN an object with `startInterview`, `sendMessage`, `endInterview` methods is returned

5) GIVEN `apiUrl` is null WHEN `createApiClient(null)` is called THEN an error is thrown with message "API URL not configured"

6) GIVEN a valid apiClient WHEN `startInterview(anonymous_id)` is called THEN a `fetch` POST to `{apiUrl}/api/interview/start` with body `{"anonymous_id": "..."}` and Content-Type `application/json` is made AND the raw Response is returned (for SSE streaming in Slice 02)

7) GIVEN a valid apiClient WHEN `sendMessage(session_id, message)` is called THEN a `fetch` POST to `{apiUrl}/api/interview/message` with body `{"session_id": "...", "message": "..."}` is made AND the raw Response is returned

8) GIVEN a valid apiClient WHEN `endInterview(session_id)` is called THEN a `fetch` POST to `{apiUrl}/api/interview/end` with body `{"session_id": "..."}` is made AND the JSON response `{summary, message_count}` is returned

9) GIVEN any apiClient method WHEN an AbortSignal is passed THEN the fetch uses that signal AND aborting the signal cancels the request

10) GIVEN `apiUrl` has a trailing slash WHEN any endpoint is called THEN the URL is constructed correctly without double slashes

---

## Test Cases

### Test File

**Convention:** `widget/tests/slices/backend-widget-integration/slice-01-anonymous-id-api-client.test.ts`

### Unit Tests (Vitest)

<test_spec>
```typescript
// widget/tests/slices/backend-widget-integration/slice-01-anonymous-id-api-client.test.ts
import { describe, it, expect, vi, beforeEach } from 'vitest'

describe('Anonymous-ID Manager', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  it('should generate UUID v4 and store in localStorage on first call', () => {
    // Arrange: localStorage empty
    // Act: call getOrCreateAnonymousId()
    // Assert: returns UUID v4 format, localStorage has key 'feedbackai_anonymous_id'
  })

  it('should return existing ID from localStorage on subsequent calls', () => {
    // Arrange: set localStorage 'feedbackai_anonymous_id' = 'test-uuid'
    // Act: call getOrCreateAnonymousId()
    // Assert: returns 'test-uuid', crypto.randomUUID not called
  })

  it('should handle localStorage SecurityError gracefully', () => {
    // Arrange: mock localStorage.getItem to throw SecurityError
    // Act: call getOrCreateAnonymousId()
    // Assert: returns a UUID v4 (generated), no throw
  })

  it('should generate valid UUID v4 format', () => {
    // Act: call getOrCreateAnonymousId()
    // Assert: matches regex /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/
  })
})

describe('API-Client', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('should throw error when apiUrl is null', () => {
    // Act & Assert: createApiClient(null) throws "API URL not configured"
  })

  it('should create client with valid apiUrl', () => {
    // Act: createApiClient('http://localhost:8000')
    // Assert: returns object with startInterview, sendMessage, endInterview methods
  })

  it('should POST to /api/interview/start with anonymous_id', async () => {
    // Arrange: mock fetch
    // Act: client.startInterview('test-anon-id')
    // Assert: fetch called with correct URL, method POST, body, headers
  })

  it('should POST to /api/interview/message with session_id and message', async () => {
    // Arrange: mock fetch
    // Act: client.sendMessage('session-uuid', 'Hello')
    // Assert: fetch called with correct URL, method POST, body, headers
  })

  it('should POST to /api/interview/end and return parsed JSON', async () => {
    // Arrange: mock fetch returning JSON { summary: 'test', message_count: 5 }
    // Act: const result = await client.endInterview('session-uuid')
    // Assert: result === { summary: 'test', message_count: 5 }
  })

  it('should pass AbortSignal to fetch', async () => {
    // Arrange: mock fetch, create AbortController
    // Act: client.startInterview('id', { signal: controller.signal })
    // Assert: fetch called with signal option
  })

  it('should handle trailing slash in apiUrl', async () => {
    // Arrange: createApiClient('http://localhost:8000/')
    // Act: client.startInterview('id')
    // Assert: fetch URL is 'http://localhost:8000/api/interview/start' (no double slash)
  })

  it('should handle non-ok response for endInterview', async () => {
    // Arrange: mock fetch returning 404
    // Act & Assert: client.endInterview('bad-id') throws with status info
  })
})
```
</test_spec>

---

## Definition of Done

- [x] Acceptance criteria are clear and complete
- [x] Security/Privacy aspects considered (localStorage fallback, no sensitive data)
- [x] No UI changes needed

---

## Integration Contract (GATE 2 PFLICHT)

### Requires From Other Slices

| Slice | Resource | Type | Validation |
|-------|----------|------|------------|
| -- | -- | -- | -- |

### Provides To Other Slices

| Resource | Type | Consumer | Interface |
|----------|------|----------|-----------|
| `getOrCreateAnonymousId()` | Function | Slice 05 (Adapter Start) | `() => string` |
| `createApiClient(apiUrl)` | Function | Slice 02, 03, 04 (SSE Clients + End) | `(apiUrl: string) => ApiClient` |
| `ApiClient.startInterview()` | Method | Slice 02 (SSE /start) | `(anonymousId: string, options?: { signal?: AbortSignal }) => Promise<Response>` |
| `ApiClient.sendMessage()` | Method | Slice 03 (SSE /message) | `(sessionId: string, message: string, options?: { signal?: AbortSignal }) => Promise<Response>` |
| `ApiClient.endInterview()` | Method | Slice 04 (Interview End) | `(sessionId: string, options?: { signal?: AbortSignal }) => Promise<EndResponse>` |
| `SSEEvent` type | TypeScript Type | Slice 02, 03 | Union type: metadata, text-delta, text-done, error |
| `EndResponse` type | TypeScript Type | Slice 04, 07 | `{ summary: string; message_count: number }` |

### Integration Validation Tasks

- [ ] `getOrCreateAnonymousId()` returns valid UUID v4 string
- [ ] `createApiClient()` accepts apiUrl from `config.ts` parseConfig result
- [ ] All methods support AbortSignal for cleanup
- [ ] Types exported and importable by consumer slices

---

## Code Examples (MANDATORY - GATE 2 PFLICHT)

| Code Example | Section | Mandatory | Notes |
|--------------|---------|-----------|-------|
| `anonymous-id.ts` | lib/anonymous-id.ts | YES | getOrCreateAnonymousId function |
| `api-client.ts` | lib/api-client.ts | YES | createApiClient factory + ApiClient |
| `types.ts` | lib/types.ts | YES | SSEEvent, EndResponse, ApiError types |

### `widget/src/lib/types.ts`

```typescript
/** SSE Event types from backend */
export type SSEEvent =
  | { type: 'metadata'; session_id: string }
  | { type: 'text-delta'; content: string }
  | { type: 'text-done' }
  | { type: 'error'; message: string }

/** Response from POST /api/interview/end */
export interface EndResponse {
  summary: string
  message_count: number
}

/** API error with status code */
export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
    public readonly detail?: string
  ) {
    super(message)
    this.name = 'ApiError'
  }
}
```

### `widget/src/lib/anonymous-id.ts`

```typescript
const STORAGE_KEY = 'feedbackai_anonymous_id'

export function getOrCreateAnonymousId(): string {
  try {
    const existing = localStorage.getItem(STORAGE_KEY)
    if (existing) return existing

    const id = crypto.randomUUID()
    localStorage.setItem(STORAGE_KEY, id)
    return id
  } catch {
    // localStorage blocked (SecurityError) - generate without persistence
    return crypto.randomUUID()
  }
}
```

### `widget/src/lib/api-client.ts`

```typescript
import type { EndResponse } from './types'
import { ApiError } from './types'

export interface ApiClient {
  startInterview(anonymousId: string, options?: { signal?: AbortSignal }): Promise<Response>
  sendMessage(sessionId: string, message: string, options?: { signal?: AbortSignal }): Promise<Response>
  endInterview(sessionId: string, options?: { signal?: AbortSignal }): Promise<EndResponse>
}

export function createApiClient(apiUrl: string | null): ApiClient {
  if (!apiUrl) {
    throw new Error('API URL not configured')
  }

  const baseUrl = apiUrl.replace(/\/+$/, '')

  async function post(endpoint: string, body: Record<string, unknown>, signal?: AbortSignal): Promise<Response> {
    const response = await fetch(`${baseUrl}${endpoint}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
      signal,
    })
    return response
  }

  return {
    startInterview(anonymousId, options) {
      return post('/api/interview/start', { anonymous_id: anonymousId }, options?.signal)
    },

    sendMessage(sessionId, message, options) {
      return post('/api/interview/message', { session_id: sessionId, message }, options?.signal)
    },

    async endInterview(sessionId, options) {
      const response = await post('/api/interview/end', { session_id: sessionId }, options?.signal)
      if (!response.ok) {
        const error = await response.json().catch(() => ({ error: 'Unknown error' }))
        throw new ApiError(error.error || 'Request failed', response.status, error.detail)
      }
      return response.json() as Promise<EndResponse>
    },
  }
}
```

---

## Constraints & Notes

**Applies to:**
- `widget/src/lib/` directory only
- No UI components modified

**API Contract:**
- Backend expects `Content-Type: application/json`
- Backend returns SSE streams for /start and /message (consumed by Slice 02/03)
- Backend returns JSON for /end (consumed directly here)

**Boundaries:**
- SSE stream parsing is NOT in this slice (Slice 02)
- ChatModelAdapter is NOT in this slice (Slice 05/06)
- Error display UI is NOT in this slice (Slice 08)

---

## Deliverables (SCOPE SAFEGUARD)

<!-- DELIVERABLES_START -->
### Frontend
- [ ] `widget/src/lib/types.ts` -- Shared TypeScript types (SSEEvent, EndResponse, ApiError)
- [ ] `widget/src/lib/anonymous-id.ts` -- Anonymous-ID Manager (generate, get, localStorage)
- [ ] `widget/src/lib/api-client.ts` -- API-Client factory with typed methods for all 3 endpoints

### Tests
- [ ] `widget/tests/slices/backend-widget-integration/slice-01-anonymous-id-api-client.test.ts` -- Unit tests for anonymous-id + api-client
<!-- DELIVERABLES_END -->

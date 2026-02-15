# Slice 07: Implement Interview-Ende Logic (Panel-Close -> /end -> ThankYou)

> **Slice 7 von 11** for `Backend-Widget-Integration`
>
> | Navigation | |
> |------------|---|
> | **Vorheriger:** | `slice-06-adapter-message-flow.md` |
> | **Nächster:** | `slice-08-error-handling.md` |

---

## Metadata (for Orchestrator)

| Key | Value |
|-----|-------|
| **ID** | `slice-07-interview-end-logic` |
| **Test** | `cd widget && pnpm test tests/slices/backend-widget-integration/slice-07-interview-end-logic.test.ts` |
| **E2E** | `false` |
| **Dependencies** | `["slice-04-interview-end", "slice-06-adapter-message-flow"]` |

---

## Test-Strategy (for Orchestrator Pipeline)

| Key | Value |
|-----|-------|
| **Stack** | `typescript-vite-react` |
| **Test Command** | `cd widget && pnpm test tests/slices/backend-widget-integration/slice-07-interview-end-logic.test.ts` |
| **Integration Command** | `cd widget && pnpm test tests/slices/backend-widget-integration/slice-07-interview-end-logic.test.ts` |
| **Acceptance Command** | `cd widget && pnpm test tests/slices/backend-widget-integration/slice-07-interview-end-logic.test.ts` |
| **Start Command** | `cd widget && pnpm dev` |
| **Health Endpoint** | N/A |
| **Mocking Strategy** | `mock_external` (fetch mocked, React testing-library for component tests) |

---

## Context & Goal

When the user closes the panel during an active interview, the widget must:
1. Abort any running SSE streams (AbortController)
2. Call `/api/interview/end` to trigger backend summary generation
3. Transition to ThankYou screen
4. Clear session_id

This slice wires up the panel close handler (`handleClosePanel`) to the interview end logic and introduces an `InterviewContext` (or callback pattern) to share session state between the Widget component and the chat runtime.

---

## Technical Implementation

### 1. Architecture Impact

| Layer | Changes |
|-------|---------|
| `widget/src/main.tsx` | MODIFY - Wire handleClosePanel to interview cleanup + GO_TO_THANKYOU |
| `widget/src/lib/chat-runtime.ts` | MODIFY - Expose sessionIdRef and abortController for cleanup |

### 2. Data Flow

```
[User clicks X-Button (PanelHeader)]
  |
[handleClosePanel() called]
  |
[Check: sessionIdRef.current !== null? (active session)]
  |--- No session -> dispatch(CLOSE_PANEL) as before
  |--- Has session:
       |
       [Abort current SSE stream (abortController.abort())]
       |
       [apiClient.endInterviewSafe(sessionId)]
       |
       [Clear sessionIdRef.current = null]
       |
       [dispatch(GO_TO_THANKYOU)]
```

### 3. State Changes

The `main.tsx` Widget component needs access to:
- Whether a session is active
- A function to end the interview (abort + /end + clear)

Approach: `useWidgetChatRuntime` returns both the runtime AND interview control functions.

```typescript
interface InterviewControls {
  endInterview: () => Promise<void>
  hasActiveSession: () => boolean
}
```

---

## Acceptance Criteria

1) GIVEN an active interview session WHEN the user clicks the X-Button to close the panel THEN the running SSE stream is aborted via AbortController

2) GIVEN an active interview session WHEN the panel is closed THEN `/api/interview/end` is called with the session_id (fire-and-forget, errors ignored)

3) GIVEN an active interview session WHEN the panel is closed THEN the session_id is cleared (ref set to null)

4) GIVEN an active interview session WHEN the panel is closed THEN the screen transitions to `thankyou` (dispatch GO_TO_THANKYOU)

5) GIVEN NO active session (still on consent or session already ended) WHEN the panel is closed THEN it dispatches CLOSE_PANEL as before (no /end call)

6) GIVEN the /end API call fails WHEN the panel is closed THEN the error is silently ignored (endInterviewSafe) and ThankYou screen still shows

7) GIVEN the ThankYou screen auto-close timer fires WHEN 5 seconds pass THEN dispatch CLOSE_AND_RESET (existing Phase 2 behavior, unchanged)

---

## Test Cases

### Test File

**Convention:** `widget/tests/slices/backend-widget-integration/slice-07-interview-end-logic.test.ts`

### Unit Tests (Vitest)

<test_spec>
```typescript
// widget/tests/slices/backend-widget-integration/slice-07-interview-end-logic.test.ts
import { describe, it, expect, vi, beforeEach } from 'vitest'

describe('Interview End Logic', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('should call /end and transition to thankyou when session is active', async () => {
    // Arrange: sessionIdRef.current = 'session-123', mock fetch for /end
    // Act: call endInterview()
    // Assert: fetch called with /api/interview/end, sessionIdRef cleared
  })

  it('should abort running SSE stream on panel close', async () => {
    // Arrange: mock AbortController
    // Act: call endInterview()
    // Assert: abortController.abort() called
  })

  it('should not call /end when no active session', async () => {
    // Arrange: sessionIdRef.current = null
    // Act: call handleClosePanel
    // Assert: fetch NOT called, dispatch CLOSE_PANEL
  })

  it('should still show ThankYou even if /end fails', async () => {
    // Arrange: mock fetch to reject
    // Act: call endInterview()
    // Assert: no throw, session cleared, GO_TO_THANKYOU dispatched
  })

  it('should clear session_id after ending interview', async () => {
    // Arrange: sessionIdRef.current = 'session-123'
    // Act: call endInterview()
    // Assert: sessionIdRef.current === null
  })
})
```
</test_spec>

---

## Integration Contract (GATE 2 PFLICHT)

### Requires From Other Slices

| Slice | Resource | Type | Validation |
|-------|----------|------|------------|
| Slice 04 | `ApiClient.endInterviewSafe()` | Method | `(sessionId, options?) => Promise<EndResponse \| null>` |
| Slice 05 | Session-ID ref | React Ref | `{ current: string \| null }` |
| Slice 05 | `useWidgetChatRuntime()` | Hook | Returns runtime |

### Provides To Other Slices

| Resource | Type | Consumer | Interface |
|----------|------|----------|-----------|
| `InterviewControls.endInterview()` | Function | main.tsx Widget | `() => Promise<void>` |
| `InterviewControls.hasActiveSession()` | Function | main.tsx Widget | `() => boolean` |

### Integration Validation Tasks

- [ ] Panel close triggers abort + /end + clear + GO_TO_THANKYOU
- [ ] No /end call when no active session
- [ ] endInterviewSafe never throws (fire-and-forget)
- [ ] ThankYou auto-close timer still works (Phase 2 behavior preserved)

---

## Code Examples (MANDATORY - GATE 2 PFLICHT)

| Code Example | Section | Mandatory | Notes |
|--------------|---------|-----------|-------|
| `chat-runtime.ts` controls | lib/chat-runtime.ts | YES | Add InterviewControls return |
| `main.tsx` close handler | main.tsx | YES | Wire close to endInterview |

### Updated `widget/src/lib/chat-runtime.ts`

```typescript
export interface InterviewControls {
  endInterview: () => Promise<void>
  hasActiveSession: () => boolean
}

export function useWidgetChatRuntime(apiUrl: string | null): {
  runtime: ReturnType<typeof useLocalRuntime>
  controls: InterviewControls
} {
  const sessionIdRef = useRef<string | null>(null)
  const abortControllerRef = useRef<AbortController | null>(null)

  const apiClient = useMemo(() => {
    if (!apiUrl) return null
    return createApiClient(apiUrl)
  }, [apiUrl])

  const controls: InterviewControls = useMemo(() => ({
    async endInterview() {
      // Abort running stream
      abortControllerRef.current?.abort()
      abortControllerRef.current = null

      // Call /end (fire-and-forget)
      const sessionId = sessionIdRef.current
      if (sessionId && apiClient) {
        sessionIdRef.current = null
        await apiClient.endInterviewSafe(sessionId)
      }
    },
    hasActiveSession() {
      return sessionIdRef.current !== null
    }
  }), [apiClient])

  // ... adapter creation with abortControllerRef management ...

  return { runtime, controls }
}
```

### Updated `widget/src/main.tsx` (relevant part)

```typescript
function Widget({ config }: { config: WidgetConfig }) {
  const [state, dispatch] = useReducer(widgetReducer, initialState)
  const { runtime, controls } = useWidgetChatRuntime(config.apiUrl)  // Destructure controls

  const handleClosePanel = async () => {
    if (controls.hasActiveSession()) {
      await controls.endInterview()
      dispatch({ type: 'GO_TO_THANKYOU' })
    } else {
      dispatch({ type: 'CLOSE_PANEL' })
    }
  }

  // ... rest unchanged
}
```

---

## Deliverables (SCOPE SAFEGUARD)

<!-- DELIVERABLES_START -->
### Frontend
- [ ] `widget/src/lib/chat-runtime.ts` -- Add InterviewControls (endInterview, hasActiveSession) + AbortController management
- [ ] `widget/src/main.tsx` -- Wire handleClosePanel to interview end logic
- [ ] `widget/src/components/screens/ChatScreen.tsx` -- Accept runtime prop instead of creating own (if needed for controls sharing)

### Tests
- [ ] `widget/tests/slices/backend-widget-integration/slice-07-interview-end-logic.test.ts` -- Unit tests for end logic
<!-- DELIVERABLES_END -->

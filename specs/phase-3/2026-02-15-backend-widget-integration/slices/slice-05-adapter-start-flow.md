# Slice 05: Implement ChatModelAdapter for Interview Start Flow

> **Slice 5 von 11** for `Backend-Widget-Integration`
>
> | Navigation | |
> |------------|---|
> | **Vorheriger:** | `slice-04-interview-end.md` |
> | **Nächster:** | `slice-06-adapter-message-flow.md` |

---

## Metadata (for Orchestrator)

| Key | Value |
|-----|-------|
| **ID** | `slice-05-adapter-start-flow` |
| **Test** | `cd widget && pnpm test tests/slices/backend-widget-integration/slice-05-adapter-start-flow.test.ts` |
| **E2E** | `false` |
| **Dependencies** | `["slice-01-anonymous-id-api-client", "slice-02-sse-client-start"]` |

---

## Test-Strategy (for Orchestrator Pipeline)

| Key | Value |
|-----|-------|
| **Stack** | `typescript-vite-react` |
| **Test Command** | `cd widget && pnpm test tests/slices/backend-widget-integration/slice-05-adapter-start-flow.test.ts` |
| **Integration Command** | `cd widget && pnpm test tests/slices/backend-widget-integration/slice-05-adapter-start-flow.test.ts` |
| **Acceptance Command** | `cd widget && pnpm test tests/slices/backend-widget-integration/slice-05-adapter-start-flow.test.ts` |
| **Start Command** | `cd widget && pnpm dev` |
| **Health Endpoint** | N/A |
| **Mocking Strategy** | `mock_external` (fetch mocked, @assistant-ui runtime mocked) |

---

## Context & Goal

This is the critical integration slice. The existing `dummyChatModelAdapter` in `chat-runtime.ts` is replaced with a real adapter that:

1. On first `run()` call (no user messages yet) - calls `/start` with anonymous_id, stores session_id, yields assistant response
2. The adapter must conform to `@assistant-ui/react` `ChatModelAdapter` interface: async generator yielding `{ content: [{ type: "text", text }] }`

The adapter needs access to:
- `apiUrl` from config (to create api-client)
- Anonymous-ID (from localStorage)
- Session-ID (stored in a ref, set from metadata event)

**Key insight from `@assistant-ui/react`:** The `run()` method is called by the runtime whenever a new message needs a response. For the start flow, `run()` is called with empty messages (or just the system greeting context). We detect "no user messages yet" to trigger `/start`.

---

## Technical Implementation

### 1. Architecture Impact

| Layer | Changes |
|-------|---------|
| `widget/src/lib/chat-runtime.ts` | REWRITE - Replace dummyChatModelAdapter with real adapter |
| `widget/src/components/screens/ChatScreen.tsx` | MODIFY - Pass apiUrl to useWidgetChatRuntime |
| `widget/src/components/screens/ConsentScreen.tsx` | No changes (onAccept still dispatches GO_TO_CHAT) |
| `widget/src/main.tsx` | No changes (handleAcceptConsent still dispatches GO_TO_CHAT) |

### 2. Data Flow

```
[User clicks "Los geht's" -> dispatch(GO_TO_CHAT)]
  |
[ChatScreen mounts -> AssistantRuntimeProvider created]
  |
[@assistant-ui calls adapter.run() with empty messages]
  |
[Adapter detects: no session_id yet -> this is a START flow]
  |
[getOrCreateAnonymousId() -> anonymous_id]
  |
[apiClient.startInterview(anonymous_id, { signal: abortSignal })]
  |
[streamStart(response) -> SSEEvent generator]
  |
[metadata event -> store session_id in ref]
  |
[text-delta events -> yield { content: [{ type: "text", text: accumulated }] }]
  |
[text-done event -> final yield, generator returns]
  |
[@assistant-ui renders assistant message progressively]
```

### 3. @assistant-ui Adapter Interface

The `ChatModelAdapter` `run()` method must yield objects matching:
```typescript
{
  content: Array<{ type: "text"; text: string }>
}
```

Each yield updates the assistant message. For streaming, we accumulate text and yield the full text so far on each delta.

---

## Acceptance Criteria

1) GIVEN the ChatScreen mounts for the first time WHEN the adapter's `run()` is called THEN it calls `/api/interview/start` with the anonymous_id from localStorage

2) GIVEN the /start SSE stream sends a metadata event WHEN the adapter processes it THEN the session_id is stored (accessible for future /message calls)

3) GIVEN the /start SSE stream sends text-delta events WHEN the adapter processes them THEN it yields `{ content: [{ type: "text", text: accumulatedText }] }` progressively

4) GIVEN the /start SSE stream sends a text-done event WHEN the adapter processes it THEN the generator completes (returns)

5) GIVEN the /start SSE stream sends an error event WHEN the adapter processes it THEN it throws an Error with the error message

6) GIVEN the adapter's `run()` is called with an abortSignal WHEN the signal is aborted THEN the fetch request is cancelled

7) GIVEN `useWidgetChatRuntime(apiUrl)` is called WHEN apiUrl is a valid string THEN `useLocalRuntime` is initialized with the real adapter

8) GIVEN `ChatScreen` component WHEN it renders THEN it passes `config.apiUrl` to `useWidgetChatRuntime`

---

## Test Cases

### Test File

**Convention:** `widget/tests/slices/backend-widget-integration/slice-05-adapter-start-flow.test.ts`

### Unit Tests (Vitest)

<test_spec>
```typescript
// widget/tests/slices/backend-widget-integration/slice-05-adapter-start-flow.test.ts
import { describe, it, expect, vi, beforeEach } from 'vitest'

describe('ChatModelAdapter - Start Flow', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.restoreAllMocks()
  })

  it('should call /start with anonymous_id when no session exists', async () => {
    // Arrange: mock fetch returning SSE stream with metadata + text-delta + text-done
    // Act: call adapter.run() with empty messages
    // Assert: fetch called with /api/interview/start, body contains anonymous_id
  })

  it('should store session_id from metadata event', async () => {
    // Arrange: mock SSE stream with metadata event containing session_id
    // Act: iterate adapter.run()
    // Assert: session_id accessible (via getSessionId or similar)
  })

  it('should yield progressive text content from text-deltas', async () => {
    // Arrange: mock SSE stream: metadata, text-delta("Hal"), text-delta("lo!"), text-done
    // Act: collect all yields from adapter.run()
    // Assert: yields include { content: [{ type: "text", text: "Hal" }] }
    //         and { content: [{ type: "text", text: "Hallo!" }] }
  })

  it('should throw on SSE error event', async () => {
    // Arrange: mock SSE stream: metadata, error("LLM failed")
    // Act & Assert: adapter.run() throws Error("LLM failed")
  })

  it('should pass abortSignal to fetch', async () => {
    // Arrange: create AbortController, mock fetch
    // Act: call adapter.run() with abortSignal
    // Assert: fetch called with signal
  })

  it('should complete generator after text-done', async () => {
    // Arrange: mock SSE stream: metadata, text-delta, text-done
    // Act: collect all yields
    // Assert: generator.next() returns { done: true } after text-done
  })
})
```
</test_spec>

---

## Integration Contract (GATE 2 PFLICHT)

### Requires From Other Slices

| Slice | Resource | Type | Validation |
|-------|----------|------|------------|
| Slice 01 | `getOrCreateAnonymousId()` | Function | `() => string` |
| Slice 01 | `createApiClient()` | Function | `(apiUrl) => ApiClient` |
| Slice 01 | `ApiClient.startInterview()` | Method | `(anonymousId, options?) => Promise<Response>` |
| Slice 02 | `streamStart()` | Function | `(response) => AsyncGenerator<SSEEvent>` |

### Provides To Other Slices

| Resource | Type | Consumer | Interface |
|----------|------|----------|-----------|
| `createChatModelAdapter()` | Function | Slice 06 | `(apiClient, sessionRef) => ChatModelAdapter` |
| `useWidgetChatRuntime(apiUrl)` | Hook | ChatScreen | `(apiUrl: string \| null) => Runtime` |
| Session-ID ref | React Ref | Slice 06, 07 | `{ current: string \| null }` |

### Integration Validation Tasks

- [ ] Adapter yields @assistant-ui compatible format `{ content: [{ type: "text", text }] }`
- [ ] Session-ID stored and accessible for Slice 06 (message flow)
- [ ] ChatScreen passes apiUrl to hook
- [ ] AbortSignal propagated through entire chain

---

## Code Examples (MANDATORY - GATE 2 PFLICHT)

| Code Example | Section | Mandatory | Notes |
|--------------|---------|-----------|-------|
| `chat-runtime.ts` | lib/chat-runtime.ts | YES | Complete rewrite replacing dummy adapter |
| `ChatScreen.tsx` | screens/ChatScreen.tsx | YES | Pass apiUrl to hook |

### `widget/src/lib/chat-runtime.ts` (REWRITE)

```typescript
import { useLocalRuntime } from '@assistant-ui/react'
import type { ChatModelAdapter } from '@assistant-ui/react'
import { useRef, useMemo } from 'react'
import { getOrCreateAnonymousId } from './anonymous-id'
import { createApiClient } from './api-client'
import { streamStart } from './sse-parser'
import type { SSEEvent } from './types'

function createChatModelAdapter(
  apiUrl: string,
  sessionIdRef: React.MutableRefObject<string | null>
): ChatModelAdapter {
  const apiClient = createApiClient(apiUrl)

  return {
    async *run({ abortSignal }) {
      // If no session yet, this is a START flow
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
          // text-done: loop ends naturally
        }
        return
      }

      // MESSAGE flow handled by Slice 06
    }
  }
}

export function useWidgetChatRuntime(apiUrl: string | null) {
  const sessionIdRef = useRef<string | null>(null)

  const adapter = useMemo(() => {
    if (!apiUrl) {
      // Fallback: dummy adapter when no API URL configured
      return { async *run() { return } } as ChatModelAdapter
    }
    return createChatModelAdapter(apiUrl, sessionIdRef)
  }, [apiUrl])

  return useLocalRuntime(adapter)
}
```

### `widget/src/components/screens/ChatScreen.tsx` (MODIFY)

```typescript
import { AssistantRuntimeProvider } from '@assistant-ui/react'
import { useWidgetChatRuntime } from '../../lib/chat-runtime'
import { ChatThread } from '../chat/ChatThread'
import { ChatComposer } from '../chat/ChatComposer'
import type { WidgetConfig } from '../../config'

interface ChatScreenProps {
  config: WidgetConfig
}

export function ChatScreen({ config }: ChatScreenProps) {
  const runtime = useWidgetChatRuntime(config.apiUrl)  // Pass apiUrl

  return (
    <AssistantRuntimeProvider runtime={runtime}>
      <div className="flex flex-col h-full">
        <div className="flex-1 overflow-y-auto chat-thread">
          <ChatThread />
        </div>
        <div className="border-t border-gray-200">
          <ChatComposer placeholder={config.texts.composerPlaceholder} />
        </div>
      </div>
    </AssistantRuntimeProvider>
  )
}
```

---

## Deliverables (SCOPE SAFEGUARD)

<!-- DELIVERABLES_START -->
### Frontend
- [ ] `widget/src/lib/chat-runtime.ts` -- Rewrite: Replace dummy adapter with real ChatModelAdapter (start flow)
- [ ] `widget/src/components/screens/ChatScreen.tsx` -- Modify: Pass config.apiUrl to useWidgetChatRuntime

### Tests
- [ ] `widget/tests/slices/backend-widget-integration/slice-05-adapter-start-flow.test.ts` -- Unit tests for adapter start flow
<!-- DELIVERABLES_END -->

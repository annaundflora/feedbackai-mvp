# Slice 10: Implement Assistant-Message Rendering

> **Slice 10 von 11** for `Backend-Widget-Integration`
>
> | Navigation | |
> |------------|---|
> | **Vorheriger:** | `slice-09-loading-typing-indicators.md` |
> | **Nächster:** | `slice-11-e2e-integration-tests.md` |

---

## Metadata (for Orchestrator)

| Key | Value |
|-----|-------|
| **ID** | `slice-10-assistant-message-rendering` |
| **Test** | `cd widget && pnpm test tests/slices/backend-widget-integration/slice-10-assistant-message-rendering.test.ts` |
| **E2E** | `false` |
| **Dependencies** | `["slice-09-loading-typing-indicators"]` |

---

## Test-Strategy (for Orchestrator Pipeline)

| Key | Value |
|-----|-------|
| **Stack** | `typescript-vite-react` |
| **Test Command** | `cd widget && pnpm test tests/slices/backend-widget-integration/slice-10-assistant-message-rendering.test.ts` |
| **Integration Command** | `cd widget && pnpm test tests/slices/backend-widget-integration/slice-10-assistant-message-rendering.test.ts` |
| **Acceptance Command** | `cd widget && pnpm test tests/slices/backend-widget-integration/slice-10-assistant-message-rendering.test.ts` |
| **Start Command** | `cd widget && pnpm dev` |
| **Health Endpoint** | N/A |
| **Mocking Strategy** | `mock_external` (React testing-library) |

---

## Context & Goal

Currently `ChatThread.tsx` uses a single `ChatMessage` component for both user and assistant messages. This slice creates a dedicated `AssistantMessage` component with:

1. **Left-aligned layout** (vs user messages which are right-aligned)
2. **Grey bubble styling** (grey-100 background, grey-900 text)
3. **Optional avatar** (circle with "A" icon)
4. **Streaming-friendly rendering** (text appends progressively, no re-mount)
5. **Max 80% width**

The existing `ChatMessage` (Phase 2) handles user messages with right-aligned brand-color bubbles. We need to differentiate between user and assistant messages in the `ChatThread`.

**From wireframes.md:** Left-aligned, grey-100 background, grey-900 text, border-radius 12px, optional avatar (32px circle).

---

## Technical Implementation

### 1. Architecture Impact

| Layer | Changes |
|-------|---------|
| `widget/src/components/chat/AssistantMessage.tsx` | NEW - Left-aligned assistant message component |
| `widget/src/components/chat/ChatThread.tsx` | MODIFY - Use AssistantMessage for assistant, ChatMessage for user |
| `widget/src/components/chat/ChatMessage.tsx` | MODIFY (optional) - Ensure only user-message styling |

### 2. @assistant-ui Integration

`ThreadPrimitive.Messages` accepts a `components` prop:
```typescript
<ThreadPrimitive.Messages components={{
  UserMessage: ChatMessage,        // Existing (right-aligned, brand-color)
  AssistantMessage: AssistantMessage // NEW (left-aligned, grey)
}} />
```

The `MessagePrimitive.Content` component renders the message text automatically from @assistant-ui state.

---

## Acceptance Criteria

1) GIVEN an assistant message in the thread WHEN it renders THEN it is left-aligned with grey-100 background, grey-900 text, border-radius 12px

2) GIVEN an assistant message WHEN rendered THEN its max-width is 80% of the thread width

3) GIVEN an assistant message during streaming WHEN new text-deltas arrive THEN each delta appends to the existing message text AND the message container element retains the same DOM node (verified by stable key/ref)

4) GIVEN the ChatThread WHEN it renders messages THEN user messages use the existing ChatMessage (right-aligned, brand-color) and assistant messages use AssistantMessage (left-aligned, grey)

5) GIVEN an assistant message WHEN rendered THEN it displays an avatar on the left side (32px grey-200 circle with "A" text in grey-600) (grey circle or icon)

6) GIVEN multiple messages in the thread WHEN a new message appears THEN the thread auto-scrolls to the bottom

---

## Test Cases

### Test File

**Convention:** `widget/tests/slices/backend-widget-integration/slice-10-assistant-message-rendering.test.ts`

### Unit Tests (Vitest)

<test_spec>
```typescript
// widget/tests/slices/backend-widget-integration/slice-10-assistant-message-rendering.test.ts
import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'

describe('AssistantMessage', () => {
  it('should render with left-aligned styling', () => {
    // Render AssistantMessage with text
    // Assert: has left-alignment classes
  })

  it('should have grey-100 background and grey-900 text', () => {
    // Render AssistantMessage
    // Assert: bg-gray-100, text-gray-900 classes
  })

  it('should have max-width of 80%', () => {
    // Render AssistantMessage
    // Assert: max-w-[80%] class
  })

  it('should have border-radius 12px (rounded-xl)', () => {
    // Render AssistantMessage
    // Assert: rounded-xl class
  })

  it('should render avatar with 32px grey-200 circle and "A" text', () => {
    // Render AssistantMessage
    // Assert: avatar element present with w-8 h-8 rounded-full bg-gray-200, contains "A"
  })

  it('should append text on subsequent renders without changing container DOM node', () => {
    // Arrange: render AssistantMessage with initial text
    // Act: rerender with longer text (simulating streaming)
    // Assert: text updates, container element is same instance
  })
})

describe('ChatThread message differentiation', () => {
  it('should use AssistantMessage for assistant role', () => {
    // This tests that ThreadPrimitive.Messages gets correct component mapping
    // Assert: components prop includes AssistantMessage
  })
})
```
</test_spec>

---

## Integration Contract (GATE 2 PFLICHT)

### Requires From Other Slices

| Slice | Resource | Type | Validation |
|-------|----------|------|------------|
| Phase 2 | `ChatMessage` | Component | User message (right-aligned) |
| Phase 2 | `ChatThread` | Component | Thread container with @assistant-ui primitives |

### Provides To Other Slices

| Resource | Type | Consumer | Interface |
|----------|------|----------|-----------|
| `AssistantMessage` | Component | ChatThread | Used via @assistant-ui MessagePrimitive |

### Integration Validation Tasks

- [ ] AssistantMessage renders correctly in @assistant-ui thread
- [ ] User and assistant messages visually distinct
- [ ] Streaming text appends without flicker

---

## Code Examples (MANDATORY - GATE 2 PFLICHT)

| Code Example | Section | Mandatory | Notes |
|--------------|---------|-----------|-------|
| `AssistantMessage.tsx` | components/chat/ | YES | Left-aligned grey bubble |
| `ChatThread.tsx` update | components/chat/ | YES | Separate user/assistant components |

### `widget/src/components/chat/AssistantMessage.tsx`

```typescript
import { MessagePrimitive } from '@assistant-ui/react'

export function AssistantMessage() {
  return (
    <MessagePrimitive.Root className="flex items-start gap-2 py-1">
      {/* Avatar */}
      <div
        className="flex-shrink-0 w-8 h-8 rounded-full bg-gray-200 flex items-center justify-center"
        aria-hidden="true"
      >
        <span className="text-xs font-medium text-gray-600">A</span>
      </div>

      {/* Message Bubble */}
      <div className="max-w-[80%] bg-gray-100 text-gray-900 rounded-xl px-3 py-2 text-sm leading-relaxed">
        <MessagePrimitive.Content />
      </div>
    </MessagePrimitive.Root>
  )
}
```

### Updated `widget/src/components/chat/ChatThread.tsx`

```typescript
import { ThreadPrimitive } from '@assistant-ui/react'
import { ChatMessage } from './ChatMessage'
import { AssistantMessage } from './AssistantMessage'

export function ChatThread() {
  return (
    <ThreadPrimitive.Root className="h-full">
      <ThreadPrimitive.Empty>
        {/* ... existing empty state unchanged ... */}
      </ThreadPrimitive.Empty>

      <ThreadPrimitive.Viewport className="px-4 py-2">
        <ThreadPrimitive.Messages components={{
          UserMessage: ChatMessage,
          AssistantMessage: AssistantMessage
        }} />
      </ThreadPrimitive.Viewport>
    </ThreadPrimitive.Root>
  )
}
```

---

## Deliverables (SCOPE SAFEGUARD)

<!-- DELIVERABLES_START -->
### Frontend
- [ ] `widget/src/components/chat/AssistantMessage.tsx` -- Left-aligned assistant message with grey bubble, avatar, max 80% width
- [ ] `widget/src/components/chat/ChatThread.tsx` -- Update to use separate AssistantMessage component

### Tests
- [ ] `widget/tests/slices/backend-widget-integration/slice-10-assistant-message-rendering.test.ts` -- Component tests for AssistantMessage styling
<!-- DELIVERABLES_END -->

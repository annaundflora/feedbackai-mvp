# Slice 09: Implement Loading & Typing Indicators

> **Slice 9 von 11** for `Backend-Widget-Integration`
>
> | Navigation | |
> |------------|---|
> | **Vorheriger:** | `slice-08-error-handling.md` |
> | **Nächster:** | `slice-10-assistant-message-rendering.md` |

---

## Metadata (for Orchestrator)

| Key | Value |
|-----|-------|
| **ID** | `slice-09-loading-typing-indicators` |
| **Test** | `cd widget && pnpm test tests/slices/backend-widget-integration/slice-09-loading-typing-indicators.test.ts` |
| **E2E** | `false` |
| **Dependencies** | `["slice-08-error-handling"]` |

---

## Test-Strategy (for Orchestrator Pipeline)

| Key | Value |
|-----|-------|
| **Stack** | `typescript-vite-react` |
| **Test Command** | `cd widget && pnpm test tests/slices/backend-widget-integration/slice-09-loading-typing-indicators.test.ts` |
| **Integration Command** | `cd widget && pnpm test tests/slices/backend-widget-integration/slice-09-loading-typing-indicators.test.ts` |
| **Acceptance Command** | `cd widget && pnpm test tests/slices/backend-widget-integration/slice-09-loading-typing-indicators.test.ts` |
| **Start Command** | `cd widget && pnpm dev` |
| **Health Endpoint** | N/A |
| **Mocking Strategy** | `mock_external` (React testing-library) |

---

## Context & Goal

Visual feedback during async operations:

1. **LoadingIndicator** - Shown during CONNECTING state (after consent, before first SSE response). Displays "Verbinde..." with pulse animation.
2. **TypingIndicator** - Shown when assistant is generating a response (before first text-delta arrives). Displays animated dots "...".

Both indicators are rendered in the ChatThread area. They use @assistant-ui's streaming state to determine visibility.

**From wireframes.md:**
- LoadingIndicator: Center-aligned, "Verbinde..." with pulse animation (opacity 0.5 -> 1.0)
- TypingIndicator: Left-aligned as assistant message bubble, "..." with bounce animation

---

## Technical Implementation

### 1. Architecture Impact

| Layer | Changes |
|-------|---------|
| `widget/src/components/chat/LoadingIndicator.tsx` | NEW - "Verbinde..." pulse component |
| `widget/src/components/chat/TypingIndicator.tsx` | NEW - "..." bounce animation component |
| `widget/src/components/chat/ChatThread.tsx` | MODIFY - Show indicators based on @assistant-ui thread state |
| `widget/src/styles/widget.css` | MODIFY - Add keyframe animations for pulse and bounce |

### 2. When to Show

| Indicator | Condition | Hides When |
|-----------|-----------|------------|
| LoadingIndicator | Thread is empty AND runtime is running (isRunning=true) | First message appears in thread |
| TypingIndicator | Runtime is running AND at least one message exists | Handled by @assistant-ui (shows during streaming automatically) |

**Note:** `@assistant-ui/react` may handle the typing indicator natively via its streaming state. We need to check if `ThreadPrimitive` has built-in loading states. If so, we only need the LoadingIndicator for the initial connect state.

### 3. Animation Keyframes

```css
/* Pulse for LoadingIndicator */
@keyframes feedbackai-pulse {
  0%, 100% { opacity: 0.5; }
  50% { opacity: 1; }
}

/* Bounce for TypingIndicator dots */
@keyframes feedbackai-bounce {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-4px); }
}
```

---

## Acceptance Criteria

1) GIVEN the user just clicked "Los geht's" WHEN the /start request is in progress THEN the LoadingIndicator ("Verbinde...") is shown centered in the thread area with pulse animation

2) GIVEN the LoadingIndicator is visible WHEN the first assistant message text-delta arrives THEN the LoadingIndicator disappears and the message appears

3) GIVEN the user sent a message WHEN the /message request is streaming THEN the TypingIndicator ("...") appears as a temporary assistant message with bounce animation

4) GIVEN the TypingIndicator is visible WHEN the first text-delta of the response arrives THEN the TypingIndicator is replaced by the actual assistant message text

5) GIVEN either indicator is visible WHEN the Composer is rendered THEN it is in disabled state (greyed out)

6) GIVEN the user has `prefers-reduced-motion: reduce` WHEN indicators are shown THEN animations are disabled (static display)

7) GIVEN the LoadingIndicator WHEN rendered THEN it has appropriate aria-label for screen readers

---

## Test Cases

### Test File

**Convention:** `widget/tests/slices/backend-widget-integration/slice-09-loading-typing-indicators.test.ts`

### Unit Tests (Vitest)

<test_spec>
```typescript
// widget/tests/slices/backend-widget-integration/slice-09-loading-typing-indicators.test.ts
import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'

describe('LoadingIndicator', () => {
  it('should render "Verbinde..." text', () => {
    // Render LoadingIndicator
    // Assert: "Verbinde..." visible
  })

  it('should have pulse animation class', () => {
    // Render LoadingIndicator
    // Assert: element has animation class
  })

  it('should have aria-label for accessibility', () => {
    // Render LoadingIndicator
    // Assert: aria-label="Verbinde mit Server" or similar
  })
})

describe('TypingIndicator', () => {
  it('should render three dots', () => {
    // Render TypingIndicator
    // Assert: three dot elements visible
  })

  it('should have bounce animation class', () => {
    // Render TypingIndicator
    // Assert: dots have animation classes with staggered delays
  })

  it('should be styled as assistant message bubble (left-aligned, grey)', () => {
    // Render TypingIndicator
    // Assert: has grey-100 background, left-aligned styling
  })
})

describe('Indicator Transitions', () => {
  it('should hide LoadingIndicator when first message appears in thread', () => {
    // Arrange: render ChatThread with LoadingIndicator visible (isRunning=true, empty thread)
    // Act: simulate first message arriving (thread becomes non-empty)
    // Assert: LoadingIndicator is no longer in the DOM
  })

  it('should hide TypingIndicator when assistant message text starts rendering', () => {
    // Arrange: render ChatThread with TypingIndicator visible (isRunning=true, thread has messages)
    // Act: simulate assistant message content appearing (streaming text-delta)
    // Assert: TypingIndicator is no longer in the DOM, message text is visible
  })
})
```
</test_spec>

---

## Integration Contract (GATE 2 PFLICHT)

### Requires From Other Slices

| Slice | Resource | Type | Validation |
|-------|----------|------|------------|
| Slice 05/06 | @assistant-ui thread state | Runtime State | isRunning, messages count |

### Provides To Other Slices

| Resource | Type | Consumer | Interface |
|----------|------|----------|-----------|
| `LoadingIndicator` | Component | ChatThread | No props (self-contained) |
| `TypingIndicator` | Component | ChatThread | No props (self-contained) |

### Integration Validation Tasks

- [ ] LoadingIndicator shows during initial connect
- [ ] TypingIndicator shows during assistant streaming
- [ ] Both disappear when content arrives
- [ ] prefers-reduced-motion respected

---

## Code Examples (MANDATORY - GATE 2 PFLICHT)

| Code Example | Section | Mandatory | Notes |
|--------------|---------|-----------|-------|
| `LoadingIndicator.tsx` | components/chat/ | YES | Pulse animation component |
| `TypingIndicator.tsx` | components/chat/ | YES | Bounce dots component |

### `widget/src/components/chat/LoadingIndicator.tsx`

```typescript
export function LoadingIndicator() {
  return (
    <div
      className="flex flex-col items-center justify-center py-8"
      role="status"
      aria-label="Verbinde mit Server"
    >
      <div className="animate-[feedbackai-pulse_1.5s_ease-in-out_infinite] text-gray-500 text-sm">
        Verbinde...
      </div>
    </div>
  )
}
```

### `widget/src/components/chat/TypingIndicator.tsx`

```typescript
export function TypingIndicator() {
  return (
    <div className="flex items-start gap-2 px-4 py-2" aria-label="Antwort wird generiert">
      <div className="bg-gray-100 rounded-xl px-4 py-3 flex gap-1">
        {[0, 1, 2].map((i) => (
          <span
            key={i}
            className="w-2 h-2 bg-gray-400 rounded-full animate-[feedbackai-bounce_1s_ease-in-out_infinite] motion-reduce:animate-none"
            style={{ animationDelay: `${i * 0.2}s` }}
          />
        ))}
      </div>
    </div>
  )
}
```

### CSS Additions to `widget/src/styles/widget.css`

```css
@keyframes feedbackai-pulse {
  0%, 100% { opacity: 0.5; }
  50% { opacity: 1; }
}

@keyframes feedbackai-bounce {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-4px); }
}
```

---

## Deliverables (SCOPE SAFEGUARD)

<!-- DELIVERABLES_START -->
### Frontend
- [ ] `widget/src/components/chat/LoadingIndicator.tsx` -- Loading indicator ("Verbinde...") with pulse animation
- [ ] `widget/src/components/chat/TypingIndicator.tsx` -- Typing indicator (animated dots) with bounce animation
- [ ] `widget/src/components/chat/ChatThread.tsx` -- Integrate indicators based on thread state
- [ ] `widget/src/styles/widget.css` -- Add keyframe animations (feedbackai-pulse, feedbackai-bounce)

### Tests
- [ ] `widget/tests/slices/backend-widget-integration/slice-09-loading-typing-indicators.test.ts` -- Component tests for both indicators
<!-- DELIVERABLES_END -->

# Slice 08: Implement Error-Handling with ErrorDisplay Component

> **Slice 8 von 11** for `Backend-Widget-Integration`
>
> | Navigation | |
> |------------|---|
> | **Vorheriger:** | `slice-07-interview-end-logic.md` |
> | **Nächster:** | `slice-09-loading-typing-indicators.md` |

---

## Metadata (for Orchestrator)

| Key | Value |
|-----|-------|
| **ID** | `slice-08-error-handling` |
| **Test** | `cd widget && pnpm test tests/slices/backend-widget-integration/slice-08-error-handling.test.ts` |
| **E2E** | `false` |
| **Dependencies** | `["slice-07-interview-end-logic"]` |

---

## Test-Strategy (for Orchestrator Pipeline)

| Key | Value |
|-----|-------|
| **Stack** | `typescript-vite-react` |
| **Test Command** | `cd widget && pnpm test tests/slices/backend-widget-integration/slice-08-error-handling.test.ts` |
| **Integration Command** | `cd widget && pnpm test tests/slices/backend-widget-integration/slice-08-error-handling.test.ts` |
| **Acceptance Command** | `cd widget && pnpm test tests/slices/backend-widget-integration/slice-08-error-handling.test.ts` |
| **Start Command** | `cd widget && pnpm dev` |
| **Health Endpoint** | N/A |
| **Mocking Strategy** | `mock_external` (React testing-library for component tests) |

---

## Context & Goal

Errors from API calls (network, timeout, 404, 409, 500, SSE errors) need to be displayed to the user with appropriate messages and retry actions.

This slice implements:
1. **ErrorDisplay component** - Red box below messages with icon, message, and action button
2. **Error classification** - Map ApiError status codes to user-facing German messages
3. **Retry logic** - "Erneut versuchen" button re-triggers the failed action
4. **"Neu starten" logic** - For session expired (404), reset to consent screen

**From wireframes.md:** Red-50 background, red-700 border, warning icon, error message, retry button.

---

## Technical Implementation

### 1. Architecture Impact

| Layer | Changes |
|-------|---------|
| `widget/src/components/chat/ErrorDisplay.tsx` | NEW - Error display component |
| `widget/src/lib/error-utils.ts` | NEW - Error classification and message mapping |
| `widget/src/components/screens/ChatScreen.tsx` | MODIFY - Add error state and ErrorDisplay |

### 2. Error Classification

| Error Source | Status | User Message (DE) | Action |
|--------------|--------|-------------------|--------|
| Network failure | 0 | "Verbindung fehlgeschlagen. Bitte Netzwerk prüfen und erneut versuchen." | Retry |
| Timeout | 0 (AbortError) | "Zeitüberschreitung. Server antwortet nicht." | Retry |
| Session expired | 404 | "Sitzung abgelaufen." | "Neu starten" (-> Consent) |
| Session completed | 409 | "Interview bereits beendet." | Auto-redirect to ThankYou |
| Server error | 500 | "Ein Fehler ist aufgetreten. Bitte später versuchen." | Retry |
| SSE error event | - | Backend message displayed directly | Retry |
| Invalid JSON | - | "Datenformat-Fehler." | Retry |
| Config error | - | "Konfigurationsfehler. Bitte Administrator kontaktieren." | None |

### 3. Data Flow

```
[API call throws Error/ApiError]
  |
[classifyError(error) -> { message, action, status }]
  |
[Set error state in ChatScreen]
  |
[ErrorDisplay renders with message + action button]
  |
[User clicks Retry -> clear error, re-trigger action]
  |--- OR ---
[User clicks "Neu starten" -> dispatch GO_TO_CONSENT equivalent]
```

---

## Acceptance Criteria

1) GIVEN a network error occurs WHEN the ErrorDisplay renders THEN it shows "Verbindung fehlgeschlagen..." with a "Erneut versuchen" button

2) GIVEN a 404 error (session expired) WHEN the ErrorDisplay renders THEN it shows "Sitzung abgelaufen." with a "Neu starten" button

3) GIVEN a 409 error (session completed) WHEN the error is detected THEN the screen transitions to ThankYou automatically

4) GIVEN a 500 server error WHEN the ErrorDisplay renders THEN it shows "Ein Fehler ist aufgetreten..." with a "Erneut versuchen" button

5) GIVEN an ErrorDisplay is visible WHEN the user clicks "Erneut versuchen" THEN the error is cleared and the failed action is retried

6) GIVEN an ErrorDisplay with "Neu starten" WHEN the user clicks it THEN the session is cleared and the screen resets to consent

7) GIVEN the ErrorDisplay component WHEN it renders THEN it has red-50 background, red-700 border, warning icon, accessible ARIA attributes

8) GIVEN an error occurs WHEN ErrorDisplay is shown THEN the Composer is disabled

---

## Test Cases

### Test File

**Convention:** `widget/tests/slices/backend-widget-integration/slice-08-error-handling.test.ts`

### Unit Tests (Vitest)

<test_spec>
```typescript
// widget/tests/slices/backend-widget-integration/slice-08-error-handling.test.ts
import { describe, it, expect } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'

describe('classifyError', () => {
  it('should classify network error with retry action', () => {
    // Input: TypeError("Failed to fetch")
    // Assert: { message: "Verbindung fehlgeschlagen...", action: 'retry' }
  })

  it('should classify 404 as session expired with restart action', () => {
    // Input: ApiError("Session not found", 404)
    // Assert: { message: "Sitzung abgelaufen.", action: 'restart' }
  })

  it('should classify 409 as session completed with redirect action', () => {
    // Input: ApiError("Session already completed", 409)
    // Assert: { action: 'redirect_thankyou' }
  })

  it('should classify 500 as server error with retry action', () => {
    // Input: ApiError("Internal error", 500)
    // Assert: { message: "Ein Fehler ist aufgetreten...", action: 'retry' }
  })

  it('should classify AbortError as timeout', () => {
    // Input: DOMException("signal is aborted", "AbortError")
    // Assert: { message: "Zeitüberschreitung...", action: 'retry' }
  })
})

describe('ErrorDisplay Component', () => {
  it('should render error message and retry button', () => {
    // Render ErrorDisplay with message and onRetry
    // Assert: message visible, "Erneut versuchen" button visible
  })

  it('should render "Neu starten" button for restart action', () => {
    // Render ErrorDisplay with action='restart', onRestart callback
    // Assert: "Neu starten" button visible
  })

  it('should call onRetry when retry button clicked', () => {
    // Render with onRetry spy
    // Act: click retry button
    // Assert: onRetry called
  })

  it('should call onRestart when restart button clicked', () => {
    // Render with onRestart spy
    // Act: click restart button
    // Assert: onRestart called
  })

  it('should have correct styling (red background, border)', () => {
    // Render ErrorDisplay
    // Assert: has classes for red-50 bg, red-700 border
  })

  it('should have aria-live="polite" for screen readers', () => {
    // Render ErrorDisplay
    // Assert: has aria-live="polite" or role="alert"
  })
})
```
</test_spec>

---

## Integration Contract (GATE 2 PFLICHT)

### Requires From Other Slices

| Slice | Resource | Type | Validation |
|-------|----------|------|------------|
| Slice 01 | `ApiError` class | Class | Has `status` property |
| Slice 07 | `InterviewControls` | Interface | `endInterview()`, `hasActiveSession()` |

### Provides To Other Slices

| Resource | Type | Consumer | Interface |
|----------|------|----------|-----------|
| `ErrorDisplay` | Component | ChatScreen | Props: `{ error, onRetry, onRestart }` |
| `classifyError()` | Function | ChatScreen | `(error: unknown) => ClassifiedError` |

### Integration Validation Tasks

- [ ] ErrorDisplay renders in ChatScreen when error state is set
- [ ] Retry clears error and re-triggers failed action
- [ ] "Neu starten" resets to consent screen
- [ ] 409 auto-redirects to ThankYou

---

## Code Examples (MANDATORY - GATE 2 PFLICHT)

| Code Example | Section | Mandatory | Notes |
|--------------|---------|-----------|-------|
| `error-utils.ts` | lib/error-utils.ts | YES | classifyError function |
| `ErrorDisplay.tsx` | components/chat/ErrorDisplay.tsx | YES | Error display component |

### `widget/src/lib/error-utils.ts`

```typescript
import { ApiError } from './types'

export type ErrorAction = 'retry' | 'restart' | 'redirect_thankyou' | 'none'

export interface ClassifiedError {
  message: string
  action: ErrorAction
  status?: number
}

export function classifyError(error: unknown): ClassifiedError {
  if (error instanceof ApiError) {
    switch (error.status) {
      case 404:
        return { message: 'Sitzung abgelaufen.', action: 'restart', status: 404 }
      case 409:
        return { message: 'Interview bereits beendet.', action: 'redirect_thankyou', status: 409 }
      default:
        return { message: 'Ein Fehler ist aufgetreten. Bitte später versuchen.', action: 'retry', status: error.status }
    }
  }

  if (error instanceof DOMException && error.name === 'AbortError') {
    return { message: 'Zeitüberschreitung. Server antwortet nicht.', action: 'retry' }
  }

  if (error instanceof TypeError && error.message.includes('fetch')) {
    return { message: 'Verbindung fehlgeschlagen. Bitte Netzwerk prüfen und erneut versuchen.', action: 'retry' }
  }

  return { message: 'Ein unerwarteter Fehler ist aufgetreten.', action: 'retry' }
}
```

### `widget/src/components/chat/ErrorDisplay.tsx`

```typescript
import type { ErrorAction } from '../../lib/error-utils'

interface ErrorDisplayProps {
  message: string
  action: ErrorAction
  onRetry?: () => void
  onRestart?: () => void
}

export function ErrorDisplay({ message, action, onRetry, onRestart }: ErrorDisplayProps) {
  return (
    <div
      role="alert"
      className="mx-4 my-2 p-4 rounded-lg border border-red-700 bg-red-50"
    >
      <div className="flex items-start gap-3">
        <svg
          className="w-5 h-5 text-red-700 flex-shrink-0 mt-0.5"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={2}
          aria-hidden="true"
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        <div className="flex-1">
          <p className="text-sm font-medium text-red-900">{message}</p>
          <div className="mt-3">
            {action === 'retry' && onRetry && (
              <button
                onClick={onRetry}
                className="text-sm font-medium text-red-700 border border-red-700 rounded-md px-3 py-1.5 hover:bg-red-100 transition-colors focus-visible:ring-2 focus-visible:ring-red-500 focus-visible:ring-offset-2"
              >
                Erneut versuchen
              </button>
            )}
            {action === 'restart' && onRestart && (
              <button
                onClick={onRestart}
                className="text-sm font-medium text-red-700 border border-red-700 rounded-md px-3 py-1.5 hover:bg-red-100 transition-colors focus-visible:ring-2 focus-visible:ring-red-500 focus-visible:ring-offset-2"
              >
                Neu starten
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
```

---

## Deliverables (SCOPE SAFEGUARD)

<!-- DELIVERABLES_START -->
### Frontend
- [ ] `widget/src/lib/error-utils.ts` -- Error classification (classifyError)
- [ ] `widget/src/components/chat/ErrorDisplay.tsx` -- Error display component with retry/restart buttons
- [ ] `widget/src/components/screens/ChatScreen.tsx` -- Integrate ErrorDisplay with error state

### Tests
- [ ] `widget/tests/slices/backend-widget-integration/slice-08-error-handling.test.ts` -- Tests for error classification + ErrorDisplay component
<!-- DELIVERABLES_END -->

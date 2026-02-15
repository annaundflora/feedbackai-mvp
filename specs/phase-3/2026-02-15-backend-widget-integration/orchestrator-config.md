# Orchestrator Configuration: Backend-Widget-Integration

**Integration Map:** `integration-map.md`
**E2E Checklist:** `e2e-checklist.md`
**Generated:** 2026-02-15

---

## Pre-Implementation Gates

```yaml
pre_checks:
  - name: "Gate 1: Architecture Compliance"
    file: "specs/phase-3/2026-02-15-backend-widget-integration/architecture.md"
    required: "Architecture document exists and is complete"

  - name: "Gate 2: All Slices Approved"
    files: "specs/phase-3/2026-02-15-backend-widget-integration/slices/compliance-slice-*.md"
    required: "ALL Verdict == APPROVED"
    status: "11/11 APPROVED"

  - name: "Gate 3: Integration Map Valid"
    file: "specs/phase-3/2026-02-15-backend-widget-integration/integration-map.md"
    required: "Missing Inputs == 0, Orphaned Outputs == 0, Discovery Coverage == 100%"
    status: "READY FOR ORCHESTRATION"
```

---

## Implementation Order

Based on dependency analysis from integration-map.md:

| Order | Slice | Name | Depends On | Parallel? |
|-------|-------|------|------------|-----------|
| 1 | 01 | Anonymous-ID + API-Client | -- | No (foundation) |
| 2 | 02 | SSE-Client /start | Slice 01 | No |
| 3 | 03 | SSE-Client /message | Slice 01, 02 | Yes with Slice 04 |
| 3 | 04 | Interview-End /end | Slice 01 | Yes with Slice 03 |
| 4 | 05 | Adapter Start-Flow | Slice 01, 02 | No (critical integration) |
| 5 | 06 | Adapter Message-Flow | Slice 03, 05 | No |
| 6 | 07 | Interview-End Logic | Slice 04, 06 | No |
| 7 | 08 | Error-Handling | Slice 07 | No |
| 8 | 09 | Loading & Typing Indicators | Slice 08 | No |
| 9 | 10 | Assistant-Message Rendering | Slice 09 | No |
| 10 | 11 | E2E Integration Tests | Slices 01-10 | No (final validation) |

**Recommended implementation sequence (from discovery.md):**

```
1. Slice 01: Anonymous-ID + API-Client (Foundation)
2. Slice 02: SSE-Client /start (SSE infrastructure)
3. Slice 05: Adapter Start-Flow (First visible integration)
4. Slice 03: SSE-Client /message (Extends SSE for /message)
5. Slice 06: Adapter Message-Flow (Chat loop works)
6. Slice 04: Interview-End /end (API for summary)
7. Slice 07: Interview-End Logic (Full E2E flow)
8. Slice 08: Error-Handling (Robustness)
9. Slice 09: Loading & Typing Indicators (UX)
10. Slice 10: Assistant-Message Rendering (Visual polish)
11. Slice 11: E2E Integration Tests (Final validation)
```

---

## Slice Execution Details

### For each Slice, the Orchestrator MUST:

#### 1. Read the Slice Spec

```yaml
read_spec:
  file: "specs/phase-3/2026-02-15-backend-widget-integration/slices/slice-{NN}-{name}.md"
  extract:
    - Deliverables (DELIVERABLES_START/END markers)
    - Code Examples (MANDATORY section)
    - Acceptance Criteria
    - Test file path and test command
```

#### 2. Implement Deliverables

```yaml
implement:
  - Create/Modify each file listed in DELIVERABLES section
  - Follow Code Examples exactly (they are MANDATORY, not suggestions)
  - Respect SCOPE SAFEGUARD: Only touch files listed in deliverables
```

#### 3. Run Tests

```yaml
test_commands:
  slice-01: "cd widget && pnpm test tests/slices/backend-widget-integration/slice-01-anonymous-id-api-client.test.ts"
  slice-02: "cd widget && pnpm test tests/slices/backend-widget-integration/slice-02-sse-client-start.test.ts"
  slice-03: "cd widget && pnpm test tests/slices/backend-widget-integration/slice-03-sse-client-message.test.ts"
  slice-04: "cd widget && pnpm test tests/slices/backend-widget-integration/slice-04-interview-end.test.ts"
  slice-05: "cd widget && pnpm test tests/slices/backend-widget-integration/slice-05-adapter-start-flow.test.ts"
  slice-06: "cd widget && pnpm test tests/slices/backend-widget-integration/slice-06-adapter-message-flow.test.ts"
  slice-07: "cd widget && pnpm test tests/slices/backend-widget-integration/slice-07-interview-end-logic.test.ts"
  slice-08: "cd widget && pnpm test tests/slices/backend-widget-integration/slice-08-error-handling.test.ts"
  slice-09: "cd widget && pnpm test tests/slices/backend-widget-integration/slice-09-loading-typing-indicators.test.ts"
  slice-10: "cd widget && pnpm test tests/slices/backend-widget-integration/slice-10-assistant-message-rendering.test.ts"
  slice-11: "cd widget && pnpm test tests/slices/backend-widget-integration/slice-11-e2e-integration.test.ts"
```

---

## Post-Slice Validation

FOR each completed slice:

```yaml
validation_steps:
  - step: "Deliverables Check"
    action: "Verify all files listed between DELIVERABLES_START and DELIVERABLES_END exist"
    fail_action: "Create missing files"

  - step: "Unit Tests"
    action: "Run test command from slice Metadata section"
    fail_action: "Fix implementation until tests pass"

  - step: "TypeScript Check"
    action: "cd widget && pnpm tsc --noEmit"
    fail_action: "Fix type errors"

  - step: "Integration Points"
    action: "Verify outputs from this slice are importable by dependent slices"
    reference: "integration-map.md -> Connections table"
    fail_action: "Fix exports/interfaces"
```

---

## File Modification Tracking

### Files Created (NEW)

| File | Created By | Modified By |
|------|------------|-------------|
| `widget/src/lib/types.ts` | Slice 01 | -- |
| `widget/src/lib/anonymous-id.ts` | Slice 01 | -- |
| `widget/src/lib/api-client.ts` | Slice 01 | Slice 04 |
| `widget/src/lib/sse-parser.ts` | Slice 02 | Slice 03 |
| `widget/src/lib/error-utils.ts` | Slice 08 | -- |
| `widget/src/components/chat/ErrorDisplay.tsx` | Slice 08 | -- |
| `widget/src/components/chat/LoadingIndicator.tsx` | Slice 09 | -- |
| `widget/src/components/chat/TypingIndicator.tsx` | Slice 09 | -- |
| `widget/src/components/chat/AssistantMessage.tsx` | Slice 10 | -- |

### Files Modified (EXISTING)

| File | Modified By Slices | Key Changes |
|------|-------------------|-------------|
| `widget/src/lib/chat-runtime.ts` | Slice 05, 06, 07 | Rewrite dummy adapter -> real adapter + controls |
| `widget/src/components/screens/ChatScreen.tsx` | Slice 05, 07, 08 | Pass apiUrl, add error state, integrate ErrorDisplay |
| `widget/src/main.tsx` | Slice 07 | Wire handleClosePanel to interview end logic |
| `widget/src/components/chat/ChatThread.tsx` | Slice 09, 10 | Add indicators + AssistantMessage component mapping |
| `widget/src/styles/widget.css` | Slice 09 | Add keyframe animations |

### Test Files Created

| File | By Slice |
|------|----------|
| `widget/tests/slices/backend-widget-integration/slice-01-anonymous-id-api-client.test.ts` | Slice 01 |
| `widget/tests/slices/backend-widget-integration/slice-02-sse-client-start.test.ts` | Slice 02 |
| `widget/tests/slices/backend-widget-integration/slice-03-sse-client-message.test.ts` | Slice 03 |
| `widget/tests/slices/backend-widget-integration/slice-04-interview-end.test.ts` | Slice 04 |
| `widget/tests/slices/backend-widget-integration/slice-05-adapter-start-flow.test.ts` | Slice 05 |
| `widget/tests/slices/backend-widget-integration/slice-06-adapter-message-flow.test.ts` | Slice 06 |
| `widget/tests/slices/backend-widget-integration/slice-07-interview-end-logic.test.ts` | Slice 07 |
| `widget/tests/slices/backend-widget-integration/slice-08-error-handling.test.ts` | Slice 08 |
| `widget/tests/slices/backend-widget-integration/slice-09-loading-typing-indicators.test.ts` | Slice 09 |
| `widget/tests/slices/backend-widget-integration/slice-10-assistant-message-rendering.test.ts` | Slice 10 |
| `widget/tests/slices/backend-widget-integration/slice-11-e2e-integration.test.ts` | Slice 11 |
| `widget/tests/slices/backend-widget-integration/helpers/mock-sse.ts` | Slice 11 |

---

## E2E Validation

AFTER all slices completed:

```yaml
e2e_validation:
  - step: "Run all slice tests"
    action: "cd widget && pnpm test tests/slices/backend-widget-integration/"
    required: "ALL tests pass"

  - step: "TypeScript full check"
    action: "cd widget && pnpm tsc --noEmit"
    required: "0 errors"

  - step: "Build check"
    action: "cd widget && pnpm build"
    required: "Build succeeds"

  - step: "Execute e2e-checklist.md"
    action: "Verify each item in e2e-checklist.md manually or via Slice 11 tests"

  - step: "FOR each failing check"
    actions:
      - "Identify responsible slice from Integration Map"
      - "Create fix task with slice reference"
      - "Re-run affected slice tests"

  - step: "Final Approval"
    condition: "ALL checks in e2e-checklist.md PASS"
    output: "Feature READY for merge"
```

---

## Rollback Strategy

IF implementation fails:

```yaml
rollback:
  - condition: "Slice N fails and cannot be fixed"
    action: "Revert Slice N changes only (git restore files from deliverables list)"
    note: "Prior slices are stable library code with no UI changes (Slices 01-04)"

  - condition: "Integration fails between slices"
    action: "Review integration-map.md -> Connections for the failing connection"
    note: "Most likely cause: type mismatch or missing export"

  - condition: "Adapter integration fails (Slice 05/06)"
    action: "Fall back to dummyChatModelAdapter (Phase 2)"
    note: "Widget remains functional with dummy responses"

  - condition: "Build fails after all slices"
    action: "Check Vite build config, CSS imports, TypeScript strict mode"
    note: "Run: cd widget && pnpm build 2>&1 | head -50"
```

---

## Monitoring

During implementation:

| Metric | Alert Threshold |
|--------|-----------------|
| Slice completion time | > 2x estimate (single slice should be < 30 min) |
| Test failures | > 0 blocking |
| Deliverable missing | Any file from DELIVERABLES not created |
| Integration test fail | Any (indicates broken connection between slices) |
| TypeScript errors | > 0 after each slice |
| Build failure | Any (after Slice 05+) |

# Orchestrator Configuration: Widget-Shell

**Integration Map:** `integration-map.md`
**E2E Checklist:** `e2e-checklist.md`
**Generated:** 2026-02-15
**Feature:** Phase 2 - Widget-Shell

---

## Pre-Implementation Gates

```yaml
pre_checks:
  - name: "Gate 1: Architecture Compliance"
    file: "specs/phase-2/2026-02-15-widget-shell/compliance-architecture.md"
    required: "Verdict == APPROVED"
    status: "✅ APPROVED"

  - name: "Gate 2: All Slices Approved"
    files:
      - "specs/phase-2/2026-02-15-widget-shell/slices/compliance-slice-01.md"
      - "specs/phase-2/2026-02-15-widget-shell/slices/compliance-slice-02.md"
      - "specs/phase-2/2026-02-15-widget-shell/slices/compliance-slice-03.md"
      - "specs/phase-2/2026-02-15-widget-shell/slices/compliance-slice-04.md"
    required: "ALL Verdict == APPROVED"
    status: "✅ ALL APPROVED"

  - name: "Gate 3: Integration Map Valid"
    file: "specs/phase-2/2026-02-15-widget-shell/integration-map.md"
    required:
      - "Missing Inputs == 0"
      - "Orphaned Outputs == 0"
      - "Deliverable-Consumer Gaps == 0"
      - "Discovery Coverage == 100%"
    status: "✅ VALID (0 missing, 0 orphaned, 0 gaps, 100% coverage)"
```

**Gate Status Summary:**
- ✅ Gate 1: Architecture APPROVED
- ✅ Gate 2: All 4 Slices APPROVED
- ✅ Gate 3: Integration Map VALID (Ready for Orchestration)

**Decision:** PROCEED TO IMPLEMENTATION

---

## Implementation Order

Based on dependency analysis from `integration-map.md`:

| Order | Slice | Name | Depends On | Parallel? | Estimated Duration |
|-------|-------|------|------------|-----------|-------------------|
| 1 | 01 | Vite + Build Setup | - | No (foundation) | 2-4 hours |
| 2 | 02 | Floating Button + Panel Shell | Slice 01 | No (depends on 01) | 3-5 hours |
| 3 | 03 | Screens + State Machine | Slice 01, 02 | No (depends on 01, 02) | 4-6 hours |
| 4 | 04 | @assistant-ui Chat-UI | Slice 01, 02, 03 | No (depends on 01, 02, 03) | 4-6 hours |

**Total Estimated Duration:** 13-21 hours (sequential implementation required due to dependencies)

**Rationale for Sequential Order:**
- **Slice 01** provides foundational build config, types, and CSS scoping → MUST be first
- **Slice 02** depends on Slice 01 outputs (WidgetConfig, widget.css, build setup) → MUST be second
- **Slice 03** depends on Slice 01 (config, types) and Slice 02 (Panel, Button) → MUST be third
- **Slice 04** depends on all previous slices (config, UI shell, state machine) → MUST be last

**Parallel Execution:** NOT POSSIBLE in this feature (linear dependency chain)

---

## Slice Implementation Details

### Slice 01: Vite + Build Setup

**File:** `specs/phase-2/2026-02-15-widget-shell/slices/slice-01-vite-build-setup.md`

**Dependencies:** None (foundation)

**Key Deliverables:**
- `widget/vite.config.ts` - IIFE lib mode build
- `widget/tsconfig.json` - TypeScript config
- `widget/src/main.tsx` - IIFE Entry Point
- `widget/src/config.ts` - Data-Attribute Parser + Types
- `widget/src/styles/widget.css` - Tailwind v4 CSS-First Config
- `widget/test.html` - Test page
- `widget/dist/widget.js` - Build output

**Critical Outputs for Next Slices:**
- `WidgetConfig` Type (consumed by Slice 02, 03, 04)
- `parseConfig()` Function (consumed by Slice 02, 03, 04 via main.tsx)
- `widget.css` (extended by Slice 02, 03, 04)

**Implementation Notes:**
- All code examples in slice doc are MANDATORY deliverables
- Build must produce single `widget.js` file (IIFE format)
- CSS scoping via `.feedbackai-widget` container is critical

**Test Command:**
```bash
cd widget && npm run build && node -e "const fs=require('fs'); const stat=fs.statSync('dist/widget.js'); if(!stat.isFile()) throw new Error('widget.js not found'); console.log('✓ Build successful');"
```

---

### Slice 02: Floating Button + Panel Shell

**File:** `specs/phase-2/2026-02-15-widget-shell/slices/slice-02-floating-button-panel-shell.md`

**Dependencies:** Slice 01

**Key Deliverables:**
- `widget/src/components/FloatingButton.tsx`
- `widget/src/components/Panel.tsx`
- `widget/src/components/PanelHeader.tsx`
- `widget/src/components/PanelBody.tsx`
- `widget/src/components/icons/ChatBubbleIcon.tsx`
- `widget/src/components/icons/XIcon.tsx`
- `widget/src/main.tsx` (Updated with FloatingButton + Panel)
- `widget/src/styles/widget.css` (Updated with new tokens + keyframes)
- `widget/test.html` (Updated with Slice 2 tests)

**Critical Outputs for Next Slices:**
- `FloatingButton` Component (consumed by Slice 03)
- `Panel` Component (consumed by Slice 03)
- `panelOpen` State (migrated to useReducer in Slice 03)
- Tailwind Tokens (`--z-index-*`, `--panel-*`, `--transition-slide`)

**Implementation Notes:**
- FloatingButton must have `visible={!panelOpen}` logic
- Panel must support children prop for ScreenRouter (Slice 03)
- Mobile Fullscreen: `max-md:` classes for <=768px

**Test Command:**
```bash
cd widget && npm run build && node -e "const fs=require('fs'); const html=fs.readFileSync('test.html','utf-8'); if(!html.includes('FloatingButton')) throw new Error('FloatingButton component missing');"
```

---

### Slice 03: Screens + State Machine

**File:** `specs/phase-2/2026-02-15-widget-shell/slices/slice-03-screens-state-machine.md`

**Dependencies:** Slice 01, Slice 02

**Key Deliverables:**
- `widget/src/reducer.ts` - Widget State Machine (Reducer + Actions + Types)
- `widget/src/components/screens/ConsentScreen.tsx`
- `widget/src/components/screens/ChatScreen.tsx` (Placeholder, replaced in Slice 04)
- `widget/src/components/screens/ThankYouScreen.tsx`
- `widget/src/main.tsx` (Updated with useReducer + ScreenRouter)
- `widget/src/styles/widget.css` (Optional: Screen Animations + prefers-reduced-motion)
- `widget/test.html` (Updated with Screen tests + Dev Helper)

**Critical Outputs for Next Slices:**
- `ChatScreen` Placeholder (replaced by Slice 04)
- `WidgetState` Type (consumed by Slice 04)
- `WidgetAction` Type (consumed by Slice 04)
- `ScreenRouter` Component (routes to ChatScreen with config prop)

**Implementation Notes:**
- State Machine: 2 dimensions (`panelOpen` boolean + `screen` enum)
- 5 Actions: `OPEN_PANEL`, `CLOSE_PANEL`, `GO_TO_CHAT`, `GO_TO_THANKYOU`, `CLOSE_AND_RESET`
- Auto-Close Timer in ThankYouScreen: 5s delay, must cleanup on unmount
- ChatScreen Placeholder: Icon + Text only, replaced in Slice 04

**Test Command:**
```bash
cd widget && npm run build && node -e "const fs=require('fs'); const html=fs.readFileSync('test.html','utf-8'); if(!html.includes('ConsentScreen') || !html.includes('ThankYouScreen')) throw new Error('Screen components missing');"
```

---

### Slice 04: @assistant-ui Chat-UI

**File:** `specs/phase-2/2026-02-15-widget-shell/slices/slice-04-assistant-ui-chat.md`

**Dependencies:** Slice 01, Slice 02, Slice 03

**Key Deliverables:**
- `widget/src/lib/chat-runtime.ts` - Dummy LocalRuntime + ChatModelAdapter
- `widget/src/components/chat/ChatThread.tsx`
- `widget/src/components/chat/ChatMessage.tsx`
- `widget/src/components/chat/ChatComposer.tsx`
- `widget/src/components/screens/ChatScreen.tsx` (Updated, replaces Slice 03 Placeholder)
- `widget/src/main.tsx` (Updated ScreenRouter to pass config to ChatScreen)
- `widget/src/styles/widget.css` (Updated with Chat-specific styles)
- `widget/test.html` (Final update with Chat-UI tests)

**Critical Outputs:**
- `ChatScreen` (Final version with @assistant-ui Primitives)
- `useWidgetChatRuntime()` Hook (Phase 3: replace Dummy-Adapter)

**Implementation Notes:**
- Dummy-Adapter returns nothing (no Assistant messages in Phase 2)
- Chat-UI must render without errors (ThreadWelcome, Composer)
- Message Bubbles: User right (blue), Assistant left (grey + Avatar)
- Phase 3 Ready: Only Adapter needs replacement, rest stays

**Test Command:**
```bash
cd widget && npm run build && node -e "const fs=require('fs'); const html=fs.readFileSync('test.html','utf-8'); if(!html.includes('@assistant-ui') || !html.includes('chat-ui')) throw new Error('Chat-UI components missing');"
```

---

## Post-Slice Validation

FOR each completed slice:

```yaml
validation_steps:
  - step: "Deliverables Check"
    action: "Verify all files in DELIVERABLES_START/END exist"
    command: |
      # Example for Slice 01
      test -f widget/vite.config.ts || echo "❌ Missing: vite.config.ts"
      test -f widget/tsconfig.json || echo "❌ Missing: tsconfig.json"
      test -f widget/src/main.tsx || echo "❌ Missing: main.tsx"
      test -f widget/src/config.ts || echo "❌ Missing: config.ts"
      test -f widget/src/styles/widget.css || echo "❌ Missing: widget.css"
      test -f widget/test.html || echo "❌ Missing: test.html"
      test -f widget/dist/widget.js || echo "❌ Missing: dist/widget.js (run npm run build)"

  - step: "Build Test"
    action: "Run test command from slice Metadata section"
    command: "cd widget && npm run build"
    expected: "Exit code 0, widget.js created"

  - step: "Integration Test"
    action: "Run integration command from slice Test-Strategy"
    command: "node -e \"const fs=require('fs'); const stat=fs.statSync('widget/dist/widget.js'); console.log('Bundle size:', (stat.size/1024).toFixed(2), 'KB');\""
    expected: "Bundle size printed, no errors"

  - step: "Acceptance Test"
    action: "Run acceptance command from slice Test-Strategy"
    command: "node -e \"const fs=require('fs'); const stat=fs.statSync('widget/dist/widget.js'); if(stat.size>500000) console.warn('⚠ Bundle >500KB');\""
    expected: "Warning if >500KB, otherwise pass"

  - step: "Integration Points Validation"
    action: "Verify outputs accessible by dependent slices"
    reference: "integration-map.md → Connections"
    validation:
      - "Check WidgetConfig Type exported (Slice 01 → 02, 03, 04)"
      - "Check parseConfig() Function exported (Slice 01 → 02, 03, 04)"
      - "Check FloatingButton Component exported (Slice 02 → 03, 04)"
      - "Check Panel Component exported (Slice 02 → 03, 04)"
      - "Check WidgetState Type exported (Slice 03 → 04)"
      - "Check ScreenRouter passes config to ChatScreen (Slice 03 → 04)"
```

---

## E2E Validation

AFTER all slices completed:

```yaml
e2e_validation:
  - step: "Execute e2e-checklist.md"
    action: "Manual test execution"
    file: "specs/phase-2/2026-02-15-widget-shell/e2e-checklist.md"
    tests:
      - "Flow 1: First-Time User Journey (11 steps)"
      - "Flow 2: Panel Close and State Persistence (4 steps)"
      - "Flow 3: ThankYou Manual Close and Reset (2 steps)"
      - "Edge Cases (9 tests)"
      - "Cross-Slice Integration Points (9 tests)"
      - "Accessibility Tests (3 tests)"
      - "Performance Tests (3 tests)"
      - "CSS Isolation Tests (3 tests)"
    total_tests: 32

  - step: "FOR each failing check"
    actions:
      - "Identify responsible slice from E2E Checklist"
      - "Reference integration-map.md to find affected connections"
      - "Create fix task with slice reference and connection ID"
      - "Re-run affected slice tests (build + integration + acceptance)"
      - "Re-run E2E Checklist after fixes"

  - step: "Final Approval"
    condition: "ALL checks in e2e-checklist.md PASS"
    output: "Feature READY for merge"
    actions:
      - "Update Integration Map status to 'E2E Validated'"
      - "Tag commit: 'phase-2-widget-shell-complete'"
      - "Prepare Phase 3 planning (Backend-Anbindung)"
```

---

## Rollback Strategy

IF implementation fails:

```yaml
rollback:
  - scenario: "Slice N fails (build/test errors)"
    condition: "Build test or Integration test fails for Slice N"
    action: "Revert Slice N changes only"
    command: |
      # Example for Slice 03
      git log --oneline --grep="slice-03" -n 5
      git revert <commit-sha>
    note: "Dependencies (Slice 01, 02) are stable, no cascade revert needed"

  - scenario: "Integration fails (cross-slice dependencies)"
    condition: "Integration Point test fails in e2e-checklist.md"
    action: "Review integration-map.md for affected connections"
    steps:
      - "Identify Producer Slice (FROM) and Consumer Slice (TO)"
      - "Check if Producer Output matches Consumer Input interface"
      - "If interface mismatch: Update Slice spec and re-implement"
      - "If logic error: Fix code in responsible slice"
    note: "May need slice spec updates if Interface was under-specified"

  - scenario: "E2E fails (entire feature broken)"
    condition: "Multiple E2E tests fail, feature unusable"
    action: "Full feature rollback, return to planning"
    steps:
      - "Revert all 4 slices in reverse order (04 → 03 → 02 → 01)"
      - "Review Gate 3 Integration Map for missed dependencies"
      - "Review Slice specs for under-specified interfaces"
      - "Re-run Gate 2 Compliance on updated specs"
      - "Restart implementation from Slice 01"

  - scenario: "Bundle size too large (>500KB)"
    condition: "Acceptance test warns bundle >500KB ungzipped"
    action: "Optimize bundle size"
    steps:
      - "Analyze bundle with `vite-plugin-visualizer`"
      - "Check if @assistant-ui/react can be tree-shaken further"
      - "Check if Tailwind CSS can be purged more aggressively"
      - "Consider lazy-loading Slice 04 Chat-UI (Phase 3 optimization)"
    note: "Target <200KB gzipped, Accept <500KB ungzipped in Phase 2"
```

---

## Monitoring

During implementation:

| Metric | Alert Threshold | Action |
|--------|-----------------|--------|
| Slice completion time | > 2x estimate | Review complexity, may need to split slice further |
| Build test failures | > 0 blocking | Stop implementation, fix build errors before proceeding |
| Deliverable missing | Any file from DELIVERABLES_START/END | Agent must complete all deliverables before stopping |
| Integration test fail | Any connection in integration-map.md fails | Review Producer/Consumer interfaces, may need spec update |
| E2E test fail | > 3 failing tests | Review entire feature implementation, may need rollback |
| Bundle size | > 500KB ungzipped | Warning only in Phase 2, must optimize in Phase 3 |
| Console errors | > 0 errors in browser console | Fix errors before marking slice as done |
| Memory leaks | Timer cleanup not working | Review useEffect cleanup in ThankYouScreen (Slice 03) |

---

## Success Criteria

Feature is READY FOR MERGE when:

```yaml
success_criteria:
  gates:
    - name: "Gate 1: Architecture"
      status: "✅ APPROVED"
    - name: "Gate 2: All Slices"
      status: "✅ ALL 4 SLICES APPROVED"
    - name: "Gate 3: Integration Map"
      status: "✅ VALID (0 missing, 0 orphaned, 0 gaps, 100% coverage)"

  implementation:
    - name: "All Slices Implemented"
      slices:
        - "Slice 01: ✅ All deliverables exist, build test passes"
        - "Slice 02: ✅ All deliverables exist, build test passes"
        - "Slice 03: ✅ All deliverables exist, build test passes"
        - "Slice 04: ✅ All deliverables exist, build test passes"

  validation:
    - name: "E2E Checklist Passed"
      tests_passed: "32/32"
      blocking_issues: 0
      warnings: "Acceptable (bundle size warning OK in Phase 2)"

  quality:
    - name: "No Console Errors"
      browser_console: "0 errors"
    - name: "No Memory Leaks"
      timers_cleaned: "Yes (ThankYouScreen useEffect cleanup verified)"
    - name: "Bundle Size Acceptable"
      size: "<500KB ungzipped (Target: <200KB gzipped in production)"

  documentation:
    - name: "Integration Map Updated"
      status: "E2E Validated"
    - name: "Commit Tagged"
      tag: "phase-2-widget-shell-complete"
```

---

## Phase 3 Transition Checklist

After Phase 2 completion, prepare for Phase 3:

```yaml
phase_3_preparation:
  - task: "Review Phase 2 Widget Shell"
    items:
      - "Widget UI is complete and functional"
      - "State Machine works correctly (2-dimension model)"
      - "Chat-UI renders with Dummy-Adapter"
      - "All Discovery requirements covered (100%)"

  - task: "Identify Phase 3 Changes"
    items:
      - "Replace Dummy-Adapter with SSE-Backend-Adapter (Slice 04)"
      - "Backend Integration: `/api/interview/{start,message,end}` endpoints"
      - "Add GO_TO_THANKYOU trigger on Backend Interview-End event"
      - "No changes needed in Slice 01, 02, 03 (foundation stable)"

  - task: "Update Architecture for Phase 3"
    items:
      - "Add Backend API integration to architecture.md"
      - "Add SSE Streaming section"
      - "Update Security section (API authentication)"
      - "Document Phase 2 → Phase 3 migration path"

  - task: "Plan Phase 3 Discovery"
    items:
      - "Define Backend API contract (SSE event format)"
      - "Define Interview flow (start → message loop → end)"
      - "Define Error handling (Backend failures, Network issues)"
      - "Define Phase 3 slices (likely 1-2 slices only)"
```

---

## Notes

- **Sequential Implementation:** All slices MUST be implemented in order (01 → 02 → 03 → 04) due to linear dependency chain.
- **No Parallel Execution:** Dependencies prevent parallel slice implementation in this feature.
- **Gate 3 Status:** READY FOR ORCHESTRATION (all pre-checks passed).
- **Phase 2 Scope:** Pure frontend, no backend connection. Dummy-Adapter returns nothing.
- **Phase 3 Readiness:** Only `dummyChatModelAdapter` needs replacement. Rest of widget stays unchanged.
- **Bundle Size:** Accept <500KB ungzipped in Phase 2. Optimize in Phase 3 if needed.
- **Manual ThankYou Trigger:** In Phase 2, ThankYou screen triggered via DevTools (`dispatch({ type: 'GO_TO_THANKYOU' })`). Phase 3: automatic Backend trigger.

---

## Orchestrator Commands Summary

**Pre-Implementation:**
```bash
# Verify all gates passed
cat specs/phase-2/2026-02-15-widget-shell/compliance-architecture.md | grep "Verdict:"
cat specs/phase-2/2026-02-15-widget-shell/slices/compliance-slice-*.md | grep "Verdict:"
cat specs/phase-2/2026-02-15-widget-shell/integration-map.md | grep "Verdict:"
```

**Implementation Loop:**
```bash
# For each slice (01 → 02 → 03 → 04)
SLICE_FILE="specs/phase-2/2026-02-15-widget-shell/slices/slice-0X-name.md"

# 1. Implement slice (Agent executes)
# Agent reads $SLICE_FILE and implements all deliverables

# 2. Validate deliverables
grep -A 100 "DELIVERABLES_START" $SLICE_FILE | grep -B 100 "DELIVERABLES_END" | grep "- \[ \]" | while read line; do
  FILE=$(echo $line | sed 's/.*`\(.*\)`.*/\1/')
  test -f "$FILE" && echo "✅ $FILE" || echo "❌ MISSING: $FILE"
done

# 3. Run build test
cd widget && npm run build

# 4. Run integration test (from slice Test-Strategy)
# (varies per slice, see slice Metadata "Test" field)

# 5. Verify outputs accessible
# (check exports, imports work for next slice)

# 6. Proceed to next slice
```

**Post-Implementation:**
```bash
# Execute E2E Checklist
# (Manual test execution, 32 tests)

# If all pass:
git tag phase-2-widget-shell-complete
git push --tags

# Prepare Phase 3
echo "Phase 2 Complete. Ready for Backend Integration (Phase 3)."
```

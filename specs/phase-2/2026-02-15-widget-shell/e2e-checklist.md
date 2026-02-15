# E2E Checklist: Widget-Shell

**Integration Map:** `integration-map.md`
**Generated:** 2026-02-15
**Feature:** Phase 2 - Widget-Shell

---

## Pre-Conditions

- [x] All slices APPROVED (Gate 2)
  - [x] Slice 01: Vite Build Setup - APPROVED
  - [x] Slice 02: Floating Button + Panel Shell - APPROVED
  - [x] Slice 03: Screens + State Machine - APPROVED
  - [x] Slice 04: @assistant-ui Chat-UI - APPROVED
- [x] Architecture APPROVED (Gate 1)
- [x] Integration Map has no MISSING INPUTS (0 missing inputs)
- [x] Integration Map has no ORPHANED OUTPUTS (0 orphaned outputs)
- [x] Integration Map has no DELIVERABLE-CONSUMER GAPS (0 gaps)
- [x] Discovery Coverage 100% (40/40 elements)

---

## Happy Path Tests

### Flow 1: First-Time User Journey (Consent → Chat → ThankYou)

**Test ID:** E2E-01
**Preconditions:**
- Widget embedded in host page via script tag
- Host page loaded successfully
- No previous widget state (fresh load)

**Steps:**

1. [ ] **Slice 01 - Widget Loads:**
   - **Action:** Load host page with widget script tag
   - **Expected:** Widget script executes, singleton check passes, container `.feedbackai-widget` created in DOM
   - **Verify:** Console shows "FeedbackAI Widget mounted {lang: 'de', apiUrl: null, ...}"
   - **Responsible Slice:** Slice 01

2. [ ] **Slice 02 - Floating Button Visible:**
   - **Action:** Page fully loaded
   - **Expected:** Floating Button visible at bottom-right (16px offset), Chat-Bubble Icon displayed
   - **Verify:** Element with class containing `floating-button` visible, z-index 9999
   - **Responsible Slice:** Slice 02

3. [ ] **Slice 02 - Open Panel:**
   - **Action:** Click Floating Button
   - **Expected:** Panel slides up (300ms animation), Panel visible, Floating Button disappears
   - **Verify:** Panel element with `role="dialog"` visible, `panelOpen=true` state
   - **Responsible Slice:** Slice 02

4. [ ] **Slice 03 - Consent Screen Displayed:**
   - **Action:** Panel opened (from step 3)
   - **Expected:** Consent Screen visible with Headline "Ihr Feedback zählt!", Body text, CTA Button "Los geht's"
   - **Verify:** ConsentScreen component rendered, all texts from WidgetConfig.texts displayed
   - **Responsible Slice:** Slice 03

5. [ ] **Slice 03 - Transition to Chat:**
   - **Action:** Click "Los geht's" Button
   - **Expected:** Consent Screen replaced by Chat Screen, no page reload
   - **Verify:** `screen=chat` state, ChatScreen component rendered
   - **Responsible Slice:** Slice 03

6. [ ] **Slice 04 - Chat UI Displayed:**
   - **Action:** Chat Screen rendered (from step 5)
   - **Expected:** ThreadWelcome visible ("Bereit für Ihr Feedback"), Chat-Icon displayed, Composer Input at bottom
   - **Verify:** ChatThread and ChatComposer components rendered, Placeholder "Nachricht eingeben..." visible
   - **Responsible Slice:** Slice 04

7. [ ] **Slice 04 - Send Message:**
   - **Action:** Type "Test Nachricht" in Composer, press Enter
   - **Expected:** User Message appears in Thread (right-aligned, blue bubble), Input field cleared
   - **Verify:** ThreadMessages contains User Message, Slide-In animation (200ms)
   - **Responsible Slice:** Slice 04

8. [ ] **Slice 04 - No Assistant Response (Phase 2):**
   - **Action:** Wait after sending message
   - **Expected:** No Assistant response (Dummy-Adapter returns nothing)
   - **Verify:** No Assistant Message in Thread, no typing indicator
   - **Responsible Slice:** Slice 04

9. [ ] **Slice 03 - Simulate ThankYou (Manual Trigger):**
   - **Action:** Open Browser DevTools Console, dispatch: `dispatch({ type: 'GO_TO_THANKYOU' })`
   - **Expected:** ThankYou Screen displayed, Success Icon (Checkmark), Headline "Vielen Dank!", Auto-close hint
   - **Verify:** ThankYouScreen component rendered, Timer starts (5s)
   - **Responsible Slice:** Slice 03
   - **Note:** In Phase 3, this will be triggered automatically by Backend Interview-End event

10. [ ] **Slice 03 - Auto-Close and Reset:**
    - **Action:** Wait 5 seconds after ThankYou Screen
    - **Expected:** Panel closes automatically (Slide-Down animation), Floating Button appears
    - **Verify:** `panelOpen=false`, `screen=consent` (Reset), Button visible again
    - **Responsible Slice:** Slice 03

11. [ ] **Slice 03 - Reopen after Reset:**
    - **Action:** Click Floating Button again
    - **Expected:** Panel opens, Consent Screen displayed (not Chat or ThankYou)
    - **Verify:** `screen=consent`, fresh start
    - **Responsible Slice:** Slice 03

---

### Flow 2: Panel Close and State Persistence

**Test ID:** E2E-02
**Preconditions:**
- Widget loaded
- User completed steps 1-7 from Flow 1 (Chat Screen with User Messages)

**Steps:**

1. [ ] **Slice 02 - Close Panel (X-Button):**
   - **Action:** Click X-Button in Panel Header
   - **Expected:** Panel closes (Slide-Down 300ms), Floating Button appears
   - **Verify:** `panelOpen=false`, `screen=chat` (unchanged)
   - **Responsible Slice:** Slice 02, Slice 03 (Reducer CLOSE_PANEL action)

2. [ ] **Slice 03 - Reopen Panel (State Preserved):**
   - **Action:** Click Floating Button
   - **Expected:** Panel opens, Chat Screen visible with previous messages
   - **Verify:** `panelOpen=true`, `screen=chat` (preserved), ThreadMessages still contains User Messages
   - **Responsible Slice:** Slice 03

3. [ ] **Slice 02 - Close Panel Again:**
   - **Action:** Click X-Button
   - **Expected:** Panel closes, Floating Button appears
   - **Verify:** `panelOpen=false`, `screen=chat` (still preserved)
   - **Responsible Slice:** Slice 02

4. [ ] **Slice 03 - Reopen and Verify Messages Persist:**
   - **Action:** Click Floating Button
   - **Expected:** Panel opens, Chat Screen visible, Messages still present
   - **Verify:** ThreadMessages contains all previously sent messages
   - **Responsible Slice:** Slice 03, Slice 04 (Chat State persists)

---

### Flow 3: ThankYou Manual Close and Reset

**Test ID:** E2E-03
**Preconditions:**
- Widget loaded
- User is on ThankYou Screen (from Flow 1 Step 9)

**Steps:**

1. [ ] **Slice 03 - Manual Close Before Auto-Close:**
   - **Action:** Click X-Button on ThankYou Screen (before 5s timer expires)
   - **Expected:** Panel closes immediately, Floating Button appears
   - **Verify:** `panelOpen=false`, `screen=consent` (Reset), Auto-close timer cleared
   - **Responsible Slice:** Slice 03 (Reducer CLOSE_AND_RESET action, useEffect cleanup)

2. [ ] **Slice 03 - Reopen after Manual Close:**
   - **Action:** Click Floating Button
   - **Expected:** Panel opens, Consent Screen displayed (Reset confirmed)
   - **Verify:** `screen=consent`, no Chat messages from previous session
   - **Responsible Slice:** Slice 03

---

## Edge Cases

### Error Handling

**Test ID:** E2E-EDGE-01 - Duplicate Script Tag**
- [ ] **Scenario:** Host page includes widget script tag twice
- [ ] **Action:** Load page with two `<script src="widget.js"></script>` tags
- [ ] **Expected:** Only one widget instance mounts, Console warning: "FeedbackAI Widget already mounted"
- [ ] **Responsible Slice:** Slice 01

**Test ID:** E2E-EDGE-02 - Invalid data-lang Attribute**
- [ ] **Scenario:** Script tag has `data-lang="fr"` (unsupported)
- [ ] **Action:** Load page with `<script src="widget.js" data-lang="fr"></script>`
- [ ] **Expected:** Widget falls back to German (default), UI texts in German
- [ ] **Responsible Slice:** Slice 01

**Test ID:** E2E-EDGE-03 - Missing Script Tag**
- [ ] **Scenario:** `widget.js` script tag removed after widget mount
- [ ] **Action:** Mount widget, then remove script tag from DOM
- [ ] **Expected:** Widget continues to function (already mounted)
- [ ] **Responsible Slice:** Slice 01

---

### State Transitions

**Test ID:** E2E-EDGE-04 - Rapid Button Clicks**
- [ ] **Scenario:** User clicks Floating Button multiple times rapidly
- [ ] **Action:** Click Floating Button 5 times in 1 second
- [ ] **Expected:** Panel opens once, no duplicate panels, state stable
- [ ] **Responsible Slice:** Slice 02

**Test ID:** E2E-EDGE-05 - Multiple Screen Transitions**
- [ ] **Scenario:** User navigates Consent → Chat → Close → Reopen → Chat → ThankYou → Close → Reopen → Consent
- [ ] **Action:** Execute full flow multiple times
- [ ] **Expected:** State transitions are correct at each step, no memory leaks
- [ ] **Responsible Slice:** Slice 03

---

### Boundary Conditions

**Test ID:** E2E-EDGE-06 - Mobile Viewport (<=768px)**
- [ ] **Scenario:** Widget on mobile viewport
- [ ] **Action:** Resize browser to 375px width (iPhone SE size)
- [ ] **Expected:** Panel is Fullscreen (100vw x 100vh), no rounded corners, Button Touch Target ≥44px
- [ ] **Responsible Slice:** Slice 02

**Test ID:** E2E-EDGE-07 - Desktop Large Viewport (>1920px)**
- [ ] **Scenario:** Widget on large desktop screen
- [ ] **Action:** Resize browser to 2560px width
- [ ] **Expected:** Panel remains ~400x600px (not fullscreen), positioned bottom-right with 16px offset
- [ ] **Responsible Slice:** Slice 02

**Test ID:** E2E-EDGE-08 - Long Message Text**
- [ ] **Scenario:** User sends very long message (>500 characters)
- [ ] **Action:** Type 500+ character message in Composer, send
- [ ] **Expected:** Message Bubble wraps text (whitespace-pre-wrap), max-w-[80%], scrollbar appears
- [ ] **Responsible Slice:** Slice 04

**Test ID:** E2E-EDGE-09 - Many Messages (>10)**
- [ ] **Scenario:** User sends 15+ messages
- [ ] **Action:** Send 15 messages in Chat
- [ ] **Expected:** Thread becomes scrollable, Custom Scrollbar visible, no performance issues
- [ ] **Responsible Slice:** Slice 04

---

## Cross-Slice Integration Points

| # | Integration Point | Slices | How to Verify |
|---|-------------------|--------|---------------|
| 1 | WidgetConfig Propagation | 01 → 02, 03, 04 | UI texts from config visible in all screens (Consent, Chat, ThankYou) |
| 2 | Panel + FloatingButton Interaction | 02 → 03 | Panel opens/closes correctly on Button/X-Button click, Button visibility toggles |
| 3 | Screen Router + Reducer | 03 (internal) | All screen transitions work (Consent → Chat → ThankYou), state preserved/reset as expected |
| 4 | ChatScreen Replacement | 03 → 04 | Slice 03 ChatScreen placeholder replaced with Slice 04 @assistant-ui integration |
| 5 | ScreenRouter + ChatScreen Config | 03 → 04 | Composer placeholder text from WidgetConfig.texts.composerPlaceholder displayed |
| 6 | Tailwind Tokens Inheritance | 01 → 02 → 03 → 04 | All components use shared tokens (--color-brand, --panel-padding, --transition-slide) |
| 7 | State Machine Actions | 03 (Reducer) | All 5 actions (OPEN_PANEL, CLOSE_PANEL, GO_TO_CHAT, GO_TO_THANKYOU, CLOSE_AND_RESET) work correctly |
| 8 | Auto-Close Timer Cleanup | 03 (ThankYouScreen) | No memory leaks, timer cleared on unmount or manual close |
| 9 | LocalRuntime + Dummy-Adapter | 04 (ChatScreen) | Chat renders without errors, Dummy-Adapter returns nothing (no Assistant messages) |

---

## Accessibility Tests

**Test ID:** E2E-A11Y-01 - Keyboard Navigation**
- [ ] **Action:** Use only keyboard (Tab, Enter, Space, Shift+Enter)
- [ ] **Expected:**
  - [ ] Tab → Floating Button focused (Focus Ring visible)
  - [ ] Enter/Space → Panel opens
  - [ ] Tab → Consent CTA focused
  - [ ] Enter → Chat Screen
  - [ ] Tab → Composer Input focused
  - [ ] Type + Enter → Message sent
  - [ ] Tab → X-Button focused
  - [ ] Enter → Panel closes
- [ ] **Responsible Slices:** Slice 02 (Button/Panel), Slice 03 (Screens), Slice 04 (Chat)

**Test ID:** E2E-A11Y-02 - Screen Reader (NVDA/JAWS)**
- [ ] **Action:** Navigate widget with screen reader
- [ ] **Expected:**
  - [ ] Floating Button announces: "Feedback geben, Button"
  - [ ] Panel announces: "Dialog"
  - [ ] Consent CTA announces: "Los geht's, Button"
  - [ ] Chat Composer Input announces: "Nachricht eingeben..."
  - [ ] X-Button announces: "Panel schliessen, Button"
- [ ] **Responsible Slices:** Slice 02, Slice 03, Slice 04

**Test ID:** E2E-A11Y-03 - Reduced Motion Support**
- [ ] **Action:** Enable prefers-reduced-motion (Browser DevTools → Rendering → Emulate)
- [ ] **Expected:**
  - [ ] Panel Slide-Up/Down animations instant or minimal (<1ms)
  - [ ] Message Slide-In animations disabled (instant)
  - [ ] No visible animation delays
- [ ] **Responsible Slices:** Slice 02 (Panel), Slice 04 (Messages)

---

## Performance Tests

**Test ID:** E2E-PERF-01 - Bundle Size**
- [ ] **Action:** Build widget (`npm run build`)
- [ ] **Expected:** `widget/dist/widget.js` file size <500KB ungzipped (Target: <200KB gzipped)
- [ ] **Verify:** `stat widget/dist/widget.js` or `ls -lh widget/dist/widget.js`
- [ ] **Responsible Slices:** All (Build output)

**Test ID:** E2E-PERF-02 - Load Time**
- [ ] **Action:** Load host page with widget, measure time to Floating Button visible
- [ ] **Expected:** <100ms from script execution to Button render
- [ ] **Verify:** Browser DevTools Performance tab
- [ ] **Responsible Slices:** Slice 01, Slice 02

**Test ID:** E2E-PERF-03 - Animation Performance**
- [ ] **Action:** Open/close Panel multiple times, check FPS
- [ ] **Expected:** 60fps during Slide-Up/Down animations (transform/opacity GPU-accelerated)
- [ ] **Verify:** Chrome DevTools → Rendering → Frame Rendering Stats
- [ ] **Responsible Slices:** Slice 02

---

## CSS Isolation Tests

**Test ID:** E2E-CSS-01 - Widget Styles Don't Leak**
- [ ] **Action:** Inspect host page styles before/after widget mount
- [ ] **Expected:** No new global styles, all widget styles scoped under `.feedbackai-widget`
- [ ] **Verify:** DevTools → Elements → Computed styles on host page elements unchanged
- [ ] **Responsible Slice:** Slice 01

**Test ID:** E2E-CSS-02 - Host Styles Don't Affect Widget**
- [ ] **Action:** Host page has conflicting global styles (e.g., `button { color: red; }`)
- [ ] **Expected:** Widget buttons unaffected (use widget-scoped styles)
- [ ] **Verify:** Widget buttons retain correct colors (brand color for CTA)
- [ ] **Responsible Slice:** Slice 01

**Test ID:** E2E-CSS-03 - z-index Hierarchy**
- [ ] **Action:** Host page has high z-index elements (e.g., z-index: 10000)
- [ ] **Expected:** Widget Panel still visible above host elements (Panel z-index: 10000, Button: 9999)
- [ ] **Verify:** Panel not obscured by host page elements
- [ ] **Responsible Slice:** Slice 02

---

## Sign-Off

| Tester | Date | Result | Notes |
|--------|------|--------|-------|
| [Name] | [Date] | ✅ PASS / ❌ FAIL | [Any observations or issues] |

**Test Execution Log:**
- Total Tests: 32 (Happy Path: 3 flows, Edge Cases: 9, Integration Points: 9, A11Y: 3, Performance: 3, CSS: 3, Keyboard: 2)
- Passed: __/32
- Failed: __/32
- Blocked: __/32

**Blocking Issues Found:**
- [ ] None / [List blocking issues]

**Warnings Found:**
- [ ] None / [List warnings]

**Ready for Production:**
- [ ] ✅ YES - All tests passed, no blocking issues
- [ ] ❌ NO - Blocking issues found, requires fixes

---

## Post-E2E Actions

**If ALL TESTS PASS:**
1. [ ] Update Integration Map status to "E2E Validated"
2. [ ] Proceed to Phase 3 Planning (Backend-Anbindung)
3. [ ] Tag commit with `phase-2-widget-shell-complete`

**If TESTS FAIL:**
1. [ ] Identify responsible slice from failed test
2. [ ] Create fix task with slice reference
3. [ ] Re-run affected slice tests (unit + integration)
4. [ ] Re-run E2E Checklist after fixes
5. [ ] Repeat until all tests pass

---

## Notes

- **Phase 2 Scope:** Widget is pure frontend, no backend connection. Dummy-Adapter in Slice 04 returns nothing.
- **Phase 3 Integration:** Only `dummyChatModelAdapter` needs replacement with SSE-Backend-Adapter. All other slices remain unchanged.
- **Manual ThankYou Trigger:** In Phase 2, ThankYou screen must be triggered manually via DevTools (dispatch GO_TO_THANKYOU action). Phase 3 will trigger automatically via Backend Interview-End event.
- **Test Environment:** Use `widget/test.html` as host page for manual tests. Automated tests (Playwright) can be added in Phase 3+.

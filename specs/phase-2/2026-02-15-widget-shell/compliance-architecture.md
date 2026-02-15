# Gate 1: Architecture Compliance Report

**Gepruefte Architecture:** `specs/phase-2/2026-02-15-widget-shell/architecture.md`
**Pruefdatum:** 2026-02-15
**Discovery:** `specs/phase-2/2026-02-15-widget-shell/discovery.md`
**Wireframes:** `specs/phase-2/2026-02-15-widget-shell/wireframes.md`

---

## Summary

| Status | Count |
|--------|-------|
| Pass | 32 |
| Warning | 2 |
| Blocking | 0 |

**Verdict:** APPROVED

---

## A) Feature Mapping

### Discovery Features -> Architecture

| Discovery Feature | Architecture Section | API/Interface | Client Logic | Status |
|-------------------|---------------------|---------------|--------------|--------|
| Vite + React + TypeScript IIFE-Build | Technology Decisions, Constraints | Script-Tag Embed API | `mountWidget` entry point | Pass |
| Floating Button (round, fixed bottom-right) | Component Tree, Constraints | -- | `<FloatingButton>` component | Pass |
| Chat-Panel (~400x600px Desktop, Fullscreen Mobile) | Component Tree, Constraints | -- | `<Panel>` component, CSS media query | Pass |
| State Machine (panelOpen + screen) | Server Logic > State Machine | -- | `widgetReducer` via useReducer | Pass |
| Consent-Screen (Headline + Intro + CTA) | Component Tree | -- | `<ConsentScreen>` component | Pass |
| Chat-Screen mit @assistant-ui/react | Component Tree, Integrations | -- | `<ChatScreen>` with Thread/Composer primitives | Pass |
| Danke-Screen (Auto-Close, Reset) | Component Tree, Client-Side Logic | -- | `<ThankYouScreen>`, `autoCloseTimer` | Pass |
| Scoped Styling (.feedbackai-widget) | Security > CSS Isolation, Constraints | -- | CSS namespace, reset styles | Pass |
| Slide-Up Animation (300ms) | Technology Decisions | -- | CSS transitions transform+opacity | Pass |
| X-Button (close panel, screen preserved) | State Machine > CLOSE_PANEL | -- | `dispatch(CLOSE_PANEL)` | Pass |
| Data-Attribute Konfiguration | Widget Embed API | `data-api-url`, `data-lang` | `configParser` module | Pass |
| Konfigurierbare UI-Texte (Default: Deutsch) | WidgetTexts DTO | -- | Config layer with defaults | Pass |

### State Machine Transitions

| Discovery Transition | Architecture Action | Effect | Status |
|---------------------|---------------------|--------|--------|
| Click Floating Button -> Panel opens | `OPEN_PANEL` | `panelOpen = true` | Pass |
| Click CTA -> Chat screen | `GO_TO_CHAT` | `screen = "chat"` | Pass |
| Interview ends -> Thank you | `GO_TO_THANKYOU` | `screen = "thankyou"` | Pass |
| Click X -> Panel closes, screen preserved | `CLOSE_PANEL` | `panelOpen = false`, screen unchanged | Pass |
| Auto-close after 5s -> Reset | `CLOSE_AND_RESET` | `panelOpen = false`, `screen = "consent"` | Pass |
| X on Thank-you -> Reset | `CLOSE_AND_RESET` | `panelOpen = false`, `screen = "consent"` | Pass |

---

## B) Constraint Mapping

| Constraint | Source | Wireframe Ref | Architecture | Status |
|------------|--------|---------------|--------------|--------|
| Panel ~400x600px Desktop | Discovery: Scope line 33 | Panel Container wireframe | Constraints table: "~400x600px Desktop" | Pass |
| Fullscreen Mobile <=768px | Discovery: Business Rules line 222 | Mobile wireframe | Constraints: CSS media query | Pass |
| Floating Button 48-56px | Discovery: UI Layout line 111 | Floating Button wireframe annotation 1 | Component Tree: `<FloatingButton>` | Pass |
| Position fixed bottom-right 16px | Discovery: UI Layout line 107 | Wireframe spacing annotations | Constraints: implied in Component Layer | Pass |
| Slide-Up/Down 300ms | Discovery: Transitions lines 199-204 | Panel State Variations | Technology Decisions: CSS transitions 300ms | Pass |
| z-index management | Discovery: Business Rules line 220-221 | -- | Security > CSS Isolation: Button 9999, Panel 10000 | Pass |
| Single widget.js IIFE | Discovery: Scope line 31 | -- | Constraints: Vite lib mode + rollupOptions | Pass |
| No CSS leaking | Discovery: Business Rules line 218 | -- | Security > CSS Isolation: `.feedbackai-widget` scoped | Pass |
| No host CSS interference | Discovery: Business Rules line 219 | -- | Security > CSS Isolation: CSS reset within container | Pass |
| Widget singleton per page | Discovery: Business Rules line 217 | -- | Constraints: Script-tag duplicate detection | Pass |
| Auto-close timer ~5s | Discovery: Business Rules line 223 | Danke wireframe closing state | Client Logic: `autoCloseTimer` module (5s) | Pass |
| CTA full-width | Discovery: UI Layout line 133 | Consent wireframe annotation 3 | Component Layer (implied in `<ConsentScreen>`) | Pass |
| Composer open in Phase 2 | Discovery: Q&A #17 | Chat wireframe annotation 2 | Integrations: LocalRuntime + dummy adapter | Pass |
| Screen persistence on close | Discovery: Business Rules line 224 | Flow diagram | State Machine: CLOSE_PANEL keeps screen | Pass |
| Danke reset to consent | Discovery: Business Rules line 225 | Flow diagram | State Machine: CLOSE_AND_RESET | Pass |
| Configurable texts | Discovery: Business Rules line 226 | Wireframe annotations "configurable" | API: WidgetTexts DTO with defaults | Pass |

---

## C) Realistic Data Check

### Codebase Evidence

```
# Existing patterns in backend (for reference, Phase 2 is pure frontend):
- anonymous_id: str, max_length=255 (backend/app/api/schemas.py)
- session_id: UUID format string (36 chars)
- message: str, max_length=10000

# widget/package.json dependencies (measured):
- @assistant-ui/react: 0.7.91 (architecture says "v0.7.91" -- MATCH)
- react: 19.2.4 (architecture says "React 19" -- MATCH)
- vite: 6.4.1 (architecture says "Vite 6" -- MATCH)
- tailwindcss: 4.1.18 (architecture says "Tailwind CSS v4" -- MATCH)
- typescript: 5.9.3 (architecture says "TypeScript 5.7" -- MINOR MISMATCH, 5.9 installed)

# widget/src/: Confirmed empty (greenfield)
# widget/vite.config.ts: Does not exist yet (greenfield, to be created in Slice 1)
```

### Version Verification

| Dependency | Architecture Claim | Installed Version | Status |
|------------|-------------------|-------------------|--------|
| @assistant-ui/react | v0.7.91 | 0.7.91 | Pass |
| React | 19 | 19.2.4 | Pass |
| Vite | 6 | 6.4.1 | Pass |
| Tailwind CSS | v4 | 4.1.18 | Pass |
| TypeScript | 5.7 | 5.9.3 | Warning -- architecture says "5.7", installed is "5.9.3". Non-breaking, compatible. |

### Data Type Verdicts (Client-Side Types)

Phase 2 is pure frontend with no database. The "data types" to validate are TypeScript types in the client-side config and state.

| Field | Architecture Type | Evidence | Verdict | Notes |
|-------|-------------------|----------|---------|-------|
| `WidgetConfig.apiUrl` | `string \| null` | Backend URLs are standard HTTP URLs (< 2048 chars). Phase 2: null. | Pass | Correct for optional URL. |
| `WidgetConfig.lang` | `"de" \| "en"` | Enum with 2 values, fallback to "de" | Pass | Properly constrained union type. |
| `WidgetConfig.texts` | `WidgetTexts` object | 7 string fields with German defaults | Pass | All defaults are short strings (< 100 chars). |
| `WidgetState.panelOpen` | `boolean` | Two states: true/false | Pass | Correct. |
| `WidgetState.screen` | `enum: "consent" \| "chat" \| "thankyou"` | Three states matching state machine | Pass | Matches all Discovery states. |
| `WidgetAction` | Union of 5 action types | OPEN_PANEL, CLOSE_PANEL, GO_TO_CHAT, GO_TO_THANKYOU, CLOSE_AND_RESET | Pass | Covers all Discovery transitions. |
| `data-api-url` | Optional URL string | Standard URL attribute. Phase 2: ignored. | Pass | Correct. |
| `data-lang` | `"de"` or `"en"` or empty | Allowlist validation with fallback | Pass | Correct. |

---

## D) External Dependencies

| Dependency | Rate Limits | Auth | Errors | Timeout | Status |
|------------|-------------|------|--------|---------|--------|
| @assistant-ui/react (npm) | N/A (bundled) | N/A | N/A | N/A | Pass -- bundled at build time |
| Tailwind CSS v4 (npm) | N/A (build tool) | N/A | N/A | N/A | Pass -- build-time only |
| Vite 6 (npm) | N/A (build tool) | N/A | N/A | N/A | Pass -- build-time only |
| React 19 (npm) | N/A (bundled) | N/A | N/A | N/A | Pass -- bundled in widget.js |

> Phase 2 has NO runtime external API calls. All dependencies are bundled at build time. No rate limits, auth, or timeouts apply.

---

## E) Architecture Template Completeness Check

| Section | Present | Filled | Status |
|---------|---------|--------|--------|
| Problem & Solution | Yes | Yes | Pass |
| Scope & Boundaries (In/Out) | Yes | Yes | Pass |
| API Design | Yes | Yes (Script-Tag interface, no REST) | Pass |
| Database Schema | Yes | Yes (N/A documented) | Pass |
| Server Logic | Yes | Yes (N/A documented, client logic detailed) | Pass |
| Client-Side Logic | Yes | Yes (4 modules) | Pass |
| Business Logic Flow | Yes | Yes (full flow diagram) | Pass |
| State Machine | Yes | Yes (2 dimensions, 5 actions) | Pass |
| Validation Rules | Yes | Yes (data-api-url, data-lang) | Pass |
| Security | Yes | Yes (Auth, Data Protection, Input Validation, CSS Isolation) | Pass |
| Architecture Layers | Yes | Yes (6 layers) | Pass |
| Component Tree | Yes | Yes (full tree diagram) | Pass |
| Data Flow | Yes | Yes (flow diagram) | Pass |
| Error Handling Strategy | Yes | Yes (4 error types) | Pass |
| Constraints & Integrations | Yes | Yes (7 constraints, 5 integrations) | Pass |
| Quality Attributes (NFRs) | Yes | Yes (7 attributes with targets) | Pass |
| Risks & Assumptions | Yes | Yes (5 assumptions, 6 risks) | Pass |
| Technology Decisions | Yes | Yes (8 choices, 6 trade-offs) | Pass |
| Open Questions | Yes | Yes (2 questions with decisions) | Pass |
| Research Log | Yes | Yes (8 findings) | Pass |
| Q&A Log | Yes | Yes (8 Q&As) | Pass |

---

## Warnings

### Warning 1: TypeScript Version Mismatch (Minor)

**Category:** Dependency
**Severity:** Warning (non-blocking)

**Architecture says:**
> TypeScript 5.7 -- Already in package.json, type safety

**Evidence:**
Installed version is TypeScript 5.9.3 (package.json specifies `^5.7.0`, which resolves to 5.9.3).

**Impact:**
None. TypeScript 5.9 is backward-compatible with 5.7. The architecture version reference is the minimum version from package.json, not the resolved version.

**Recommendation:**
Update architecture Research Log entry to say "TypeScript 5.x" or "TypeScript ^5.7" to avoid confusion.

### Warning 2: Discovery Q&A #1 vs Architecture Q&A #5 Discrepancy on react-ui

**Category:** Consistency
**Severity:** Warning (non-blocking)

**Discovery says (Q&A #12):**
> react-ui als Basis, dann an Widget-Theme anpassen

**Architecture says (Open Question #1 Decision):**
> Primitives only -- full styling control, smaller bundle

**Impact:**
The architecture made a deliberate decision to NOT use react-ui (styled components) and instead use primitives-only. This is documented in Architecture Open Question #1 and Q&A #5. The Discovery Q&A #12 reflects an earlier recommendation that was overridden during architecture phase based on the finding that react-ui is not installed and the deprecated styled components in react package are not recommended.

**Recommendation:**
No action needed for architecture. The Discovery Q&A reflects the question state at discovery time. Architecture Q&A #5 and #7 clarify the final decision (primitives only + dummy adapter). If desired, add a note in discovery Q&A #12 that decision was revised in architecture phase.

---

## Blocking Issues

None.

---

## Recommendations

1. **[Warning]** Update TypeScript version reference in architecture from "5.7" to "^5.7 (resolved: 5.9.3)" for accuracy.
2. **[Warning]** Consider adding a note to Discovery Q&A #12 that the react-ui decision was revised to "primitives only" in the architecture phase.
3. **[Info]** The architecture is well-structured for a pure-frontend phase. All N/A sections (Database, Server Logic, Rate Limits) are explicitly documented as not applicable, which is correct.

---

## Verdict

**Status:** APPROVED

**Blocking Issues:** 0
**Warnings:** 2

**Next Steps:**
- [ ] Proceed to implementation (Slice 1: Vite + Build Setup)
- [ ] Optionally address warnings (non-blocking)

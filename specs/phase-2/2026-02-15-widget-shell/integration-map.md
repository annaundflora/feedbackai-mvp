# Integration Map: Widget-Shell

**Generated:** 2026-02-15
**Slices:** 4
**Connections:** 12
**Discovery Coverage:** 100%

---

## Dependency Graph (Visual)

```
┌─────────────────────────┐
│  Slice 01: Vite Build   │ ← Foundation
│  Setup                  │
└─────────────────────────┘
             │
             │ (WidgetConfig, parseConfig, widget.css, IIFE Build)
             │
             ▼
┌─────────────────────────┐
│  Slice 02: Floating     │
│  Button + Panel Shell   │
└─────────────────────────┘
             │
             │ (FloatingButton, Panel, PanelHeader, panelOpen State)
             │
             ▼
┌─────────────────────────┐
│  Slice 03: Screens +    │
│  State Machine          │
└─────────────────────────┘
             │
             │ (ChatScreen Placeholder, WidgetState, WidgetAction)
             │
             ▼
┌─────────────────────────┐
│  Slice 04: @assistant-  │
│  ui Chat-UI             │
└─────────────────────────┘
```

**Dependency Flow:**
- **Slice 01** → Slice 02, 03, 04 (Build Foundation, Config, Styles)
- **Slice 02** → Slice 03, 04 (UI Shell, Panel Container)
- **Slice 03** → Slice 04 (State Machine, ChatScreen Placeholder)

---

## Nodes

### Slice 01: Vite + Build Setup

| Field | Value |
|-------|-------|
| Status | ✅ APPROVED |
| Dependencies | None (Foundation) |
| Outputs | WidgetConfig, parseConfig(), widget.css, IIFE Build |

**Inputs:**

| Input | Source | Validation |
|-------|--------|------------|
| — | — | No dependencies |

**Outputs:**

| Output | Type | Consumers |
|--------|------|-----------|
| `WidgetConfig` Type | TypeScript Interface | Slice 02, 03, 04 |
| `parseConfig()` Function | `(scriptTag: HTMLScriptElement) => WidgetConfig` | Slice 02, 03, 04 (via main.tsx) |
| `widget.css` | Tailwind v4 CSS-First Config | Slice 02, 03, 04 |
| `Widget` Root Component | React Component | Slice 02 (extends with UI) |
| `widget.js` Build Output | IIFE Bundle | All Slices (single file output) |

---

### Slice 02: Floating Button + Panel Shell

| Field | Value |
|-------|-------|
| Status | ✅ APPROVED |
| Dependencies | Slice 01 |
| Outputs | FloatingButton, Panel, PanelHeader, panelOpen State, Tailwind Tokens |

**Inputs:**

| Input | Source | Validation |
|-------|--------|------------|
| `WidgetConfig` Type | Slice 01 | ✅ Type has `texts.panelTitle` field |
| `parseConfig()` Function | Slice 01 | ✅ Returns config with texts |
| `widget.css` | Slice 01 | ✅ Scoped utilities available |
| IIFE Build | Slice 01 | ✅ `widget.js` builds successfully |

**Outputs:**

| Output | Type | Consumers |
|--------|------|-----------|
| `FloatingButton` Component | `{ onClick: () => void, visible: boolean }` | Slice 03 (via main.tsx) |
| `Panel` Component | `{ open: boolean, onClose: () => void, title: string, children: ReactNode }` | Slice 03 (via main.tsx) |
| `PanelHeader` Component | Internal | Used by Panel component |
| `PanelBody` Component | Container | Slice 03 (Screen-Router) |
| `panelOpen` State | State Variable | Slice 03 (migrated to useReducer) |
| Tailwind Tokens | CSS Custom Props | All Slices (`--z-index-*`, `--panel-*`, `--transition-slide`) |

---

### Slice 03: Screens + State Machine

| Field | Value |
|-------|-------|
| Status | ✅ APPROVED |
| Dependencies | Slice 01, Slice 02 |
| Outputs | ConsentScreen, ChatScreen (Placeholder), ThankYouScreen, widgetReducer, ScreenRouter |

**Inputs:**

| Input | Source | Validation |
|-------|--------|------------|
| `WidgetConfig` Type | Slice 01 | ✅ Type has `texts` field with all screen texts |
| `parseConfig()` Function | Slice 01 | ✅ Returns config with screen texts |
| `Panel` Component | Slice 02 | ✅ Accepts `children` prop |
| `FloatingButton` Component | Slice 02 | ✅ Accepts `visible` prop |
| Tailwind Tokens | Slice 02 | ✅ `--transition-slide`, `--panel-padding` available |

**Outputs:**

| Output | Type | Consumers |
|--------|------|-----------|
| `ConsentScreen` Component | `{ headline, body, ctaLabel, onAccept }` | Internal (ScreenRouter) |
| `ChatScreen` Component | `{}` (Placeholder) | Slice 04 (replaces with @assistant-ui) |
| `ThankYouScreen` Component | `{ headline, body, onAutoClose, autoCloseDelay? }` | Internal (ScreenRouter) |
| `widgetReducer` | Reducer Function | Internal (Widget in main.tsx) |
| `WidgetState` Type | `{ panelOpen: boolean, screen: WidgetScreen }` | Slice 04 |
| `WidgetAction` Type | Union of 5 action types | Slice 04, Phase 3 |
| State Machine Pattern | Architecture Pattern | Phase 3 (Backend events trigger GO_TO_THANKYOU) |

---

### Slice 04: @assistant-ui Chat-UI

| Field | Value |
|-------|-------|
| Status | ✅ APPROVED |
| Dependencies | Slice 01, Slice 02, Slice 03 |
| Outputs | ChatScreen (Updated), ChatThread, ChatComposer, ChatMessage, useWidgetChatRuntime |

**Inputs:**

| Input | Source | Validation |
|-------|--------|------------|
| `WidgetConfig` Type | Slice 01 | ✅ Type has `texts.composerPlaceholder` field |
| `parseConfig()` Function | Slice 01 | ✅ Returns config with composerPlaceholder text |
| `Panel` Component | Slice 02 | ✅ Accepts ChatScreen as children |
| Tailwind Tokens | Slice 02 | ✅ `--color-brand`, `--chat-padding` available |
| `ChatScreen` Component | Slice 03 | ✅ Placeholder exists, replaced in Slice 04 |
| `ScreenRouter` Component | Slice 03 | ✅ Routes to ChatScreen with config prop |

**Outputs:**

| Output | Type | Consumers |
|--------|------|-----------|
| `ChatScreen` (Updated) | `{ config: WidgetConfig }` | ScreenRouter (Slice 03) |
| `ChatThread` Component | No props (internal) | ChatScreen |
| `ChatComposer` Component | `{ placeholder?: string }` | ChatScreen |
| `ChatMessage` Component | `{ message: {...} }` | ThreadMessages (via @assistant-ui) |
| `useWidgetChatRuntime()` Hook | Returns LocalRuntime instance | ChatScreen |
| Chat-UI Styles | CSS (Message bubbles, Composer, Scrollbar) | All Chat Components |

---

## Connections

| # | From | To | Resource | Type | Status |
|---|------|-----|----------|------|--------|
| 1 | Slice 01 | Slice 02 | WidgetConfig | Type | ✅ |
| 2 | Slice 01 | Slice 02 | parseConfig() | Function | ✅ |
| 3 | Slice 01 | Slice 02 | widget.css | Tailwind Config | ✅ |
| 4 | Slice 02 | Slice 03 | Panel | Component | ✅ |
| 5 | Slice 02 | Slice 03 | FloatingButton | Component | ✅ |
| 6 | Slice 02 | Slice 03 | Tailwind Tokens | CSS Custom Props | ✅ |
| 7 | Slice 01 | Slice 03 | WidgetConfig | Type | ✅ |
| 8 | Slice 03 | Slice 04 | ChatScreen Placeholder | Component | ✅ (Replaced) |
| 9 | Slice 03 | Slice 04 | WidgetState Type | Type | ✅ |
| 10 | Slice 01 | Slice 04 | WidgetConfig | Type | ✅ |
| 11 | Slice 02 | Slice 04 | Panel | Component | ✅ |
| 12 | Slice 02 | Slice 04 | Tailwind Tokens | CSS Custom Props | ✅ |

---

## Validation Results

### ✅ Valid Connections: 12

All declared dependencies have matching outputs:
- Slice 01 provides foundation (Config, Styles, Build) → Consumed by all slices ✅
- Slice 02 provides UI Shell (Panel, Button, Tokens) → Consumed by Slice 03, 04 ✅
- Slice 03 provides State Machine + Screens → Consumed by Slice 04 ✅

### ⚠️ Orphaned Outputs: 0

All outputs have consumers:
- **Slice 01:** All outputs consumed by Slice 02, 03, 04 ✅
- **Slice 02:** All outputs consumed by Slice 03, 04 ✅
- **Slice 03:** ConsentScreen, ThankYouScreen are final UI (mounted via ScreenRouter), ChatScreen replaced by Slice 04 ✅
- **Slice 04:** All outputs are final Chat-UI (mounted via ScreenRouter) ✅

### ❌ Missing Inputs: 0

All inputs have valid sources:
- **Slice 01:** No dependencies (foundation) ✅
- **Slice 02:** All inputs from Slice 01 ✅
- **Slice 03:** All inputs from Slice 01, 02 ✅
- **Slice 04:** All inputs from Slice 01, 02, 03 ✅

### ❌ Deliverable-Consumer Gaps: 0

All components have mount points:

| Component | Defined In | Consumer Page | Page In Deliverables? | Status |
|-----------|------------|---------------|-----------------------|--------|
| `FloatingButton` | Slice 02 | `main.tsx` (Widget Component) | ✅ Yes (Slice 02 deliverable) | ✅ |
| `Panel` | Slice 02 | `main.tsx` (Widget Component) | ✅ Yes (Slice 02 deliverable) | ✅ |
| `ConsentScreen` | Slice 03 | `main.tsx` (ScreenRouter) | ✅ Yes (Slice 03 deliverable) | ✅ |
| `ChatScreen` (Placeholder) | Slice 03 | `main.tsx` (ScreenRouter) | ✅ Yes (Slice 03 deliverable) | ✅ |
| `ThankYouScreen` | Slice 03 | `main.tsx` (ScreenRouter) | ✅ Yes (Slice 03 deliverable) | ✅ |
| `ChatScreen` (Updated) | Slice 04 | `main.tsx` (ScreenRouter) | ✅ Yes (Slice 04 deliverable) | ✅ |
| `ChatThread` | Slice 04 | `ChatScreen.tsx` | ✅ Yes (Slice 04 deliverable) | ✅ |
| `ChatComposer` | Slice 04 | `ChatScreen.tsx` | ✅ Yes (Slice 04 deliverable) | ✅ |
| `ChatMessage` | Slice 04 | `ChatThread.tsx` | ✅ Yes (Slice 04 deliverable) | ✅ |

**Analysis:** All components have explicit mount points. No orphaned components. All consumer pages (main.tsx, ChatScreen.tsx, ChatThread.tsx) are in respective slice deliverables.

---

## Discovery Traceability

### UI Components Coverage

| Discovery Element | Type | Location | Covered In | Status |
|-------------------|------|----------|------------|--------|
| `floating-button` | Button | Fixed bottom-right | Slice 02: `FloatingButton.tsx` | ✅ |
| `panel` | Container | Fixed bottom-right / Fullscreen | Slice 02: `Panel.tsx` | ✅ |
| `panel-header` | Header | Panel Top | Slice 02: `PanelHeader.tsx` | ✅ |
| `close-button` | Button | Panel Header rechts | Slice 02: `PanelHeader.tsx` (X-Button) | ✅ |
| `consent-cta` | Button | Consent Screen unten | Slice 03: `ConsentScreen.tsx` | ✅ |
| `chat-thread` | @assistant-ui Thread | Chat Screen | Slice 04: `ChatThread.tsx` | ✅ |
| `chat-composer` | @assistant-ui Composer | Chat Screen unten | Slice 04: `ChatComposer.tsx` | ✅ |

**UI Coverage:** 7/7 (100%)

---

### State Machine Coverage

| State | Required UI | Available Actions | Covered In | Status |
|-------|-------------|-------------------|------------|--------|
| `panelOpen=false, screen=consent` | Nur Floating Button sichtbar | Floating Button klicken | Slice 02 (panelOpen State), Slice 03 (screen State) | ✅ |
| `panelOpen=false, screen=chat` | Nur Floating Button sichtbar | Floating Button klicken | Slice 02 (panelOpen State), Slice 03 (screen State) | ✅ |
| `panelOpen=false, screen=thankyou` | Nur Floating Button sichtbar | Floating Button klicken | Slice 02 (panelOpen State), Slice 03 (screen State) | ✅ |
| `panelOpen=true, screen=consent` | Panel offen, Consent-Screen | "Los geht's" klicken, X-Button klicken | Slice 03: `ConsentScreen.tsx` + reducer | ✅ |
| `panelOpen=true, screen=chat` | Panel offen, Chat-Screen | Nachrichten senden (Phase 3), X-Button klicken | Slice 04: `ChatScreen.tsx` + reducer | ✅ |
| `panelOpen=true, screen=thankyou` | Panel offen, Danke-Screen | X-Button klicken, wartet auf Auto-Close | Slice 03: `ThankYouScreen.tsx` + reducer | ✅ |

**State Coverage:** 6/6 (100%)

---

### Transitions Coverage

| From | Trigger | To | Covered In | Status |
|------|---------|-----|------------|--------|
| `panelOpen=false, any screen` | `floating-button` → click | `panelOpen=true` (screen unveraendert) | Slice 02: FloatingButton onClick → OPEN_PANEL | ✅ |
| `panelOpen=true, screen=consent` | `consent-cta` → click | `screen=chat` (panelOpen bleibt true) | Slice 03: ConsentScreen onAccept → GO_TO_CHAT | ✅ |
| `panelOpen=true, any screen` | `close-button` → click | `panelOpen=false` (screen unveraendert) | Slice 02: PanelHeader onClose → CLOSE_PANEL | ✅ |
| `panelOpen=true, screen=chat` | Interview endet (Phase 3+) | `screen=thankyou` | Slice 03: Reducer GO_TO_THANKYOU (Phase 3 trigger) | ✅ |
| `panelOpen=true, screen=thankyou` | Auto-Timer (5s) | `panelOpen=false, screen=consent` (Reset) | Slice 03: ThankYouScreen useEffect → CLOSE_AND_RESET | ✅ |
| `panelOpen=true, screen=thankyou` | `close-button` → click | `panelOpen=false, screen=consent` (Reset) | Slice 03: Reducer CLOSE_AND_RESET | ✅ |

**Transitions Coverage:** 6/6 (100%)

---

### Business Rules Coverage

| Rule | Covered In | Status |
|------|------------|--------|
| Widget darf nur einmal pro Page instanziiert werden (Script-Tag Duplikat-Check) | Slice 01: main.tsx Singleton check | ✅ |
| CSS darf nicht in Host-Page leaken (Scoped Container `.feedbackai-widget`) | Slice 01: widget.css Scoping | ✅ |
| Host-Page CSS darf Widget nicht beeinflussen (Reset-Styles innerhalb des Containers) | Slice 01: widget.css Reset (all: initial) | ✅ |
| Floating Button z-index muss hoch genug sein (z-index: 9999+) | Slice 02: FloatingButton z-[9999] | ✅ |
| Panel z-index muss ueber Floating Button liegen | Slice 02: Panel z-[10000] | ✅ |
| Mobile Breakpoint: <= 768px -> Fullscreen | Slice 02: Panel max-md: classes | ✅ |
| Auto-Close Timer auf Danke-Screen: ~5 Sekunden, danach Reset auf `consent` | Slice 03: ThankYouScreen useEffect Timer → CLOSE_AND_RESET | ✅ |
| Screen-Persistenz: Beim Schliessen (X-Button) und Wieder-Oeffnen bleibt der aktuelle screen erhalten | Slice 03: Reducer CLOSE_PANEL (screen unveraendert) | ✅ |
| Danke-Reset: Nach Auto-Close oder X-Button auf Danke-Screen wird screen auf `consent` zurueckgesetzt | Slice 03: Reducer CLOSE_AND_RESET (both panelOpen + screen) | ✅ |
| UI-Texte konfigurierbar ueber Script-Data-Attribute oder Config-Objekt (Default: Deutsch) | Slice 01: parseConfig() + WidgetTexts | ✅ |

**Business Rules Coverage:** 10/10 (100%)

---

### Data Fields Coverage

| Field | Required | Covered In | Status |
|-------|----------|------------|--------|
| `data-api-url` | No | Slice 01: parseConfig() (line 344) | ✅ |
| `data-lang` | No | Slice 01: parseConfig() (line 345) | ✅ |
| `panelOpen` | Internal | Slice 02: useState → Slice 03: useReducer (WidgetState) | ✅ |
| `screen` | Internal | Slice 03: useReducer (WidgetState.screen) | ✅ |
| `texts.panelTitle` | Internal | Slice 01: WidgetTexts, used in Slice 02: Panel | ✅ |
| `texts.consentHeadline` | Internal | Slice 01: WidgetTexts, used in Slice 03: ConsentScreen | ✅ |
| `texts.consentBody` | Internal | Slice 01: WidgetTexts, used in Slice 03: ConsentScreen | ✅ |
| `texts.consentCta` | Internal | Slice 01: WidgetTexts, used in Slice 03: ConsentScreen | ✅ |
| `texts.thankYouHeadline` | Internal | Slice 01: WidgetTexts, used in Slice 03: ThankYouScreen | ✅ |
| `texts.thankYouBody` | Internal | Slice 01: WidgetTexts, used in Slice 03: ThankYouScreen | ✅ |
| `texts.composerPlaceholder` | Internal | Slice 01: WidgetTexts, used in Slice 04: ChatComposer | ✅ |

**Data Coverage:** 11/11 (100%)

---

**Discovery Coverage:** 40/40 (100%)

---

## Summary

| Metric | Value |
|--------|-------|
| Total Slices | 4 |
| Total Connections | 12 |
| Valid Connections | 12 |
| Orphaned Outputs | 0 |
| Missing Inputs | 0 |
| Deliverable-Consumer Gaps | 0 |
| Discovery Coverage | 100% (40/40) |

**Verdict:** ✅ READY FOR ORCHESTRATION

**Rationale:**
- All 4 slices are APPROVED (Gate 2)
- All dependencies have valid sources (0 missing inputs)
- All outputs have consumers or are final UI (0 orphaned outputs)
- All components have mount points (0 deliverable-consumer gaps)
- Discovery traceability is complete:
  - UI Components: 7/7 (100%)
  - State Machine: 6/6 (100%)
  - Transitions: 6/6 (100%)
  - Business Rules: 10/10 (100%)
  - Data Fields: 11/11 (100%)

**Dependency Flow Validation:**
- ✅ Linear dependency chain with no circular dependencies
- ✅ Foundation-first order (Build → UI Shell → State → Integration)
- ✅ All cross-slice resources explicitly documented
- ✅ All Integration Contracts fulfilled

**Phase 3 Readiness:**
- ✅ State Machine ready for Backend events (GO_TO_THANKYOU trigger)
- ✅ LocalRuntime with Dummy-Adapter (Phase 3: replace with SSE-Adapter)
- ✅ Chat-UI primitives integrated and ready

---

## Next Steps

1. ✅ **Gate 3 Passed** - Integration Map validated
2. ➡️ **Execute E2E Checklist** - Validate end-to-end flows
3. ➡️ **Orchestrator Execution** - Implement slices in order (Slice 01 → 02 → 03 → 04)
4. ➡️ **Post-Implementation Validation** - Verify all deliverables and integration points
5. ➡️ **Phase 3 Preparation** - Ready for Backend-Anbindung (SSE-Streaming)

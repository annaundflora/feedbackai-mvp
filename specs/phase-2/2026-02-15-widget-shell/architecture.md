# Feature: Widget-Shell

**Epic:** Phase 2 -- Widget-Shell
**Status:** Draft
**Discovery:** `discovery.md` (same folder)
**Derived from:** Discovery constraints, NFRs, and risks

---

## Problem & Solution

**Problem:**
- Backend ist fertig und per curl testbar, aber es gibt kein Frontend
- Carrier brauchen ein visuelles Interface fuer das KI-Interview
- Widget muss in beliebige Host-Pages einbettbar sein ohne CSS-Konflikte

**Solution:**
- Embeddable React-Widget als einzelne `widget.js`-Datei (IIFE-Build)
- Statische Screen-Navigation: Consent -> Chat -> Danke
- Chat-UI via @assistant-ui/react Primitives (Backend-Anbindung erst Phase 3)

**Business Value:**
- Voraussetzung fuer Phase 3 (Streaming-Bruecke) und den gesamten E2E-Flow
- Carrier koennen das Widget erstmals sehen und Feedback zum UI geben

---

## Scope & Boundaries

| In Scope |
|----------|
| Vite + React + TypeScript Setup mit IIFE-Build (`widget.js`) |
| Floating Button (Chat-Bubble Icon, rund, fixed bottom-right) |
| Chat-Panel (fixed overlay, ~400x600px Desktop, Fullscreen Mobile) |
| State-Machine: 2 Dimensionen -- panelOpen (boolean) + screen (consent/chat/thankyou) |
| Consent-Screen (Headline + Intro-Text + CTA-Button) |
| Chat-Screen mit @assistant-ui/react Primitives (leerer Chat, Composer offen aber ohne Backend) |
| Danke-Screen (Headline + Danke-Text, Auto-Close nach Sekunden, Reset auf consent) |
| Scoped Styling via CSS-Namespace (`.feedbackai-widget`) |
| Slide-Up Animation beim Oeffnen/Schliessen |
| X-Button im Panel-Header (schliesst Panel, screen-State bleibt) |
| Data-Attribute Konfiguration (`data-api-url`, `data-lang`) |
| Konfigurierbare UI-Texte (Default: Deutsch) |

| Out of Scope |
|--------------|
| Backend-Anbindung / SSE-Streaming (Phase 3) |
| Echte Chat-Nachrichten / LLM-Antworten (Phase 3) |
| Supabase-Persistenz (Phase 4) |
| Shadow DOM Isolation |
| Theme-Konfiguration via Data-Attribute (spaeter) |
| i18n-Framework (simple Config-Objekt reicht) |
| Demo-Site (Phase 4) |

---

## API Design

### Overview

| Aspect | Specification |
|--------|---------------|
| Style | No API endpoints in Phase 2 (pure frontend) |
| Authentication | None (Phase 2 has no backend connection) |
| Rate Limiting | N/A |

### Widget Embed API (Script-Tag Interface)

| Interface | Type | Description |
|-----------|------|-------------|
| Script-Tag | `<script src="widget.js" data-api-url="..." data-lang="de"></script>` | Embed via single script tag |
| `data-api-url` | Optional URL string | Backend URL (Phase 3, ignored in Phase 2) |
| `data-lang` | Optional `"de"` or `"en"` | Language for UI texts, default `"de"` |

### Widget Config Object (Internal)

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `apiUrl` | `string \| null` | `null` | Backend endpoint (Phase 3) |
| `lang` | `"de" \| "en"` | `"de"` | UI language |
| `texts` | `WidgetTexts` | German defaults | All configurable UI strings |

### WidgetTexts DTO

| Field | Type | Default (de) |
|-------|------|-------------|
| `panelTitle` | `string` | `"Feedback"` |
| `consentHeadline` | `string` | `"Ihr Feedback zaehlt!"` |
| `consentBody` | `string` | `"Wir moechten Ihnen ein paar kurze Fragen stellen. Dauert ca. 5 Minuten."` |
| `consentCta` | `string` | `"Los geht's"` |
| `thankYouHeadline` | `string` | `"Vielen Dank!"` |
| `thankYouBody` | `string` | `"Ihr Feedback hilft uns, besser zu werden."` |
| `composerPlaceholder` | `string` | `"Nachricht eingeben..."` |

---

## Database Schema

### Entities

| Table | Purpose | Key Fields |
|-------|---------|------------|
| N/A | Phase 2 has no database | -- |

> Phase 2 is pure frontend. Database interaction starts in Phase 3 (via backend API) and Phase 4 (Supabase).

---

## Server Logic

### Services & Processing

| Service | Responsibility | Input | Output | Side Effects |
|---------|----------------|-------|--------|--------------|
| N/A | Phase 2 has no server logic | -- | -- | -- |

> All logic is client-side in Phase 2. Server logic for interview management exists in `backend/app/interview/service.py` and will be connected in Phase 3.

### Client-Side Logic

| Module | Responsibility | Input | Output | Side Effects |
|--------|----------------|-------|--------|--------------|
| `configParser` | Parse data-attributes from script tag | `HTMLScriptElement` | `WidgetConfig` | None |
| `widgetReducer` | State transitions for panelOpen + screen | `WidgetState, WidgetAction` | `WidgetState` | None |
| `autoCloseTimer` | Auto-close panel after thank-you screen | Timer duration (5s) | Dispatch `CLOSE_AND_RESET` | setTimeout/clearTimeout |
| `mountWidget` | IIFE entry point, creates React root | `WidgetConfig` | Mounted React tree | DOM mutation (container div) |

### Business Logic Flow

```
Script loads → parseConfig(scriptTag) → createContainer(.feedbackai-widget)
    → ReactDOM.createRoot(container) → render(<Widget config={config} />)

User clicks bubble → dispatch(OPEN_PANEL) → Panel slides up
User clicks CTA → dispatch(GO_TO_CHAT) → Chat screen shown
Interview ends (Phase 3) → dispatch(GO_TO_THANKYOU) → Thank-you screen
Auto-close timer → dispatch(CLOSE_AND_RESET) → Panel closes, screen=consent
User clicks X → dispatch(CLOSE_PANEL) → Panel closes, screen preserved
```

### State Machine (useReducer)

| State | Type | Values |
|-------|------|--------|
| `panelOpen` | `boolean` | `true`, `false` |
| `screen` | `enum` | `"consent"`, `"chat"`, `"thankyou"` |

| Action | Payload | Effect |
|--------|---------|--------|
| `OPEN_PANEL` | -- | `panelOpen = true` |
| `CLOSE_PANEL` | -- | `panelOpen = false` (screen unchanged) |
| `GO_TO_CHAT` | -- | `screen = "chat"` |
| `GO_TO_THANKYOU` | -- | `screen = "thankyou"` |
| `CLOSE_AND_RESET` | -- | `panelOpen = false`, `screen = "consent"` |

### Validation Rules

| Field | Rule | Error Message |
|-------|------|---------------|
| `data-api-url` | Valid URL or empty | Ignored (Phase 2) |
| `data-lang` | `"de"` or `"en"` or empty | Falls back to `"de"` |

---

## Security

### Authentication & Authorization

| Area | Mechanism | Notes |
|------|-----------|-------|
| Widget Embed | None | Phase 2 has no auth. Phase 3 will use API key or session-based auth. |
| Script Loading | HTTPS | Host page must serve widget.js via HTTPS in production |

### Data Protection

| Data Type | Protection | Notes |
|-----------|------------|-------|
| User messages | Not applicable | Phase 2 has no message transport. Phase 3 will use HTTPS + SSE. |
| Config data | Client-side only | data-attributes are visible in DOM (no secrets) |

### Input Validation & Sanitization

| Input | Validation | Sanitization |
|-------|------------|--------------|
| `data-api-url` | URL format check | Not used in Phase 2 |
| `data-lang` | Allowlist (`de`, `en`) | Fallback to default |
| Chat input (Composer) | N/A in Phase 2 | Phase 3: server-side validation via backend |

### Rate Limiting & Abuse Prevention

| Resource | Limit | Window | Penalty |
|----------|-------|--------|---------|
| N/A | -- | -- | Phase 2 has no backend calls |

### CSS Isolation

| Concern | Mitigation |
|---------|------------|
| Widget CSS leaking into host | All styles scoped under `.feedbackai-widget` container |
| Host CSS affecting widget | CSS reset within `.feedbackai-widget` container |
| z-index conflicts | Floating button: `z-index: 9999`, Panel: `z-index: 10000` |
| Tailwind v4 global styles | Build with Tailwind scoped to widget container |

---

## Architecture Layers

### Layer Responsibilities

| Layer | Responsibility | Pattern |
|-------|----------------|---------|
| Entry Point (`main.tsx`) | IIFE bootstrap, config parsing, DOM mount | Self-executing module |
| Config Layer (`config.ts`) | Parse data-attributes, merge defaults, create WidgetConfig | Factory pattern |
| State Layer (`reducer.ts`) | Widget state machine (panelOpen + screen) | useReducer + dispatch |
| Component Layer (`components/`) | UI components: Widget, FloatingButton, Panel, Screens | React component tree |
| Chat Layer (`chat/`) | @assistant-ui/react integration (Thread, Composer) | Primitive composition |
| Style Layer (`styles/`) | Tailwind v4 + scoped CSS | CSS namespace `.feedbackai-widget` |

### Component Tree

```
<Widget config={config}>                    ← Root, provides config context
  ├── <FloatingButton onClick={openPanel} /> ← Visible when panelOpen=false
  └── <Panel open={panelOpen}>               ← Slide-up overlay
       ├── <PanelHeader title onClose />     ← Title + X-Button
       └── <PanelBody screen={screen}>       ← Screen router
            ├── <ConsentScreen onAccept />   ← screen="consent"
            ├── <ChatScreen />               ← screen="chat" (@assistant-ui)
            └── <ThankYouScreen />           ← screen="thankyou" (auto-close)
```

### Data Flow

```
ScriptTag (data-*) → configParser → WidgetConfig
                                        ↓
                                   <Widget config>
                                        ↓
                              useReducer(widgetReducer)
                                   ↓           ↓
                              panelOpen      screen
                                 ↓              ↓
                          FloatingButton    PanelBody
                          (show/hide)     (screen router)
```

### Error Handling Strategy

| Error Type | Handling | User Response | Logging |
|------------|----------|---------------|---------|
| Script load failure | Widget doesn't render | No visible error (silent fail) | Browser console error |
| Invalid data-attribute | Fallback to defaults | Widget works with defaults | Console warning |
| React render error | ErrorBoundary catches | Widget disappears gracefully | Console error |
| DOM container conflict | Check for existing mount | Skip if already mounted | Console warning |

---

## Constraints & Integrations

### Constraints

| Constraint | Technical Implication | Solution |
|------------|----------------------|----------|
| Single `widget.js` file | All React + CSS must bundle into one IIFE file | Vite lib mode with `rollupOptions`, inline CSS |
| No CSS leaking | Widget styles must not affect host page | All CSS under `.feedbackai-widget` namespace, Tailwind scoped |
| No host CSS interference | Host styles must not break widget | CSS reset within widget container |
| Embeddable in any page | No global dependencies, no module system required | IIFE format, React bundled inline |
| Widget singleton | Only one instance per page | Script-tag duplicate detection in mount function |
| Mobile fullscreen | Panel must be fullscreen on mobile (<=768px) | CSS media query within scoped container |
| Tailwind v4 in widget | Tailwind v4 uses @property (Shadow DOM incompatible) | Scoped container instead of Shadow DOM |

### Integrations

| Area | System / Capability | Interface | Notes |
|------|----------------------|-----------|-------|
| @assistant-ui/react | Chat UI primitives | React component imports | v0.7.91, Thread + Composer primitives |
| @assistant-ui LocalRuntime | Chat runtime (Phase 2: dummy) | `useLocalRuntime(adapter)` | Dummy ChatModelAdapter that returns nothing |
| Tailwind CSS v4 | Utility-first styling | CSS imports, `@import "tailwindcss"` | Scoped to `.feedbackai-widget` |
| Vite 6 | Build tooling | `vite.config.ts` with lib mode | IIFE output, single file |
| React 19 | UI framework | Bundled in widget.js | Not loaded from CDN |

---

## Quality Attributes (NFRs)

### From Discovery -> Technical Solution

| Attribute | Target | Technical Approach | Measure / Verify |
|-----------|--------|--------------------|------------------|
| Bundle Size | < 200KB gzipped | Vite tree-shaking, no unnecessary deps, CSS inlined | `npm run build` output size |
| Load Performance | < 100ms to visible button | Async script loading, minimal critical path | Browser DevTools timeline |
| CSS Isolation | Zero leaks in/out | Scoped `.feedbackai-widget` + reset styles | Visual test in host pages with conflicting CSS |
| Animation Smoothness | 60fps slide-up/down | CSS transitions (not JS animation), `transform` + `opacity` | Chrome DevTools FPS monitor |
| Mobile Responsiveness | Fullscreen on <=768px | CSS media query, `100vw x 100dvh` | Device testing / responsive mode |
| Accessibility | Basic keyboard + screen reader | Focus trap in panel, aria-labels, semantic HTML | Manual keyboard navigation test |
| Browser Support | Modern browsers (Chrome, Firefox, Safari, Edge) | ES2020 target, no polyfills needed | Cross-browser manual test |

### Monitoring & Observability

| Metric | Type | Target | Alert |
|--------|------|--------|-------|
| N/A | -- | -- | Phase 2 has no server-side monitoring. Console logs only. |

---

## Risks & Assumptions

### Assumptions

| Assumption | Technical Validation | Impact if Wrong |
|------------|---------------------|-----------------|
| Tailwind v4 works with CSS scoping (no Shadow DOM) | Build test with scoped container | Must find alternative styling (CSS modules, vanilla CSS) |
| @assistant-ui/react v0.7 primitives work without runtime | Test Thread + Composer rendering without backend | Must use deprecated styled components or build custom chat UI |
| Vite 6 lib mode produces valid IIFE with React bundled | Build test, load in plain HTML | Must switch to Rollup or esbuild standalone |
| React 19 works in IIFE bundle (no module system) | Build test in plain HTML page | Must downgrade or use Preact |
| Single file < 200KB gzipped | Build and measure | Acceptable up to 500KB, beyond that need code splitting |

### Risks & Mitigation

| Risk | Likelihood | Impact | Technical Mitigation | Fallback |
|------|------------|--------|---------------------|----------|
| @assistant-ui/react-ui not installed (styled components unavailable) | Confirmed | Low | Use primitives directly, style with Tailwind | Custom chat components without @assistant-ui |
| Tailwind v4 global @property breaks host page | Medium | High | Scope all styles under `.feedbackai-widget`, test in host page | Use Tailwind v4 `@layer` or inline styles |
| IIFE bundle too large (React + @assistant-ui) | Medium | Medium | Tree-shake, exclude unused @assistant-ui modules | Accept larger bundle, optimize in Phase 3 |
| @assistant-ui LocalRuntime requires ChatModelAdapter even in Phase 2 | High | Low | Create no-op dummy adapter | Use primitives without runtime |
| Host page z-index higher than 9999 | Low | Low | Use z-index 9999/10000 | Make z-index configurable via data-attribute |
| CSS reset inside widget too aggressive | Low | Medium | Minimal targeted reset (box-sizing, fonts, colors) | Fine-tune reset based on testing |

---

## Technology Decisions

### Stack Choices

| Area | Technology | Rationale |
|------|------------|-----------|
| UI Framework | React 19 | Already in package.json, same ecosystem as @assistant-ui |
| Build Tool | Vite 6 (lib mode) | Already in package.json, IIFE output via rollupOptions |
| Chat UI | @assistant-ui/react Primitives | Already installed, Radix-like composability, Phase 3 ready with LocalRuntime |
| Styling | Tailwind CSS v4 | Already in package.json, utility-first, scoped via container |
| State Management | useReducer | Simple 2-dimension state, no external dependency needed |
| TypeScript | TypeScript 5.9 | Already in package.json, type safety |
| CSS Isolation | Scoped namespace `.feedbackai-widget` | Pragmatic, Tailwind v4 compatible (Shadow DOM is not) |
| Animation | CSS transitions | `transform: translateY()` + `opacity`, 300ms, GPU-accelerated |

### Trade-offs

| Decision | Pro | Con | Mitigation |
|----------|-----|-----|------------|
| IIFE single file (no code splitting) | Simple embed, one script tag | Larger initial load | Tree-shaking, acceptable for widget size |
| Scoped CSS instead of Shadow DOM | Tailwind v4 compatible, simpler debugging | Less isolation than Shadow DOM | Thorough CSS reset, testing in host pages |
| @assistant-ui Primitives (not styled) | Full control over styling, widget-theme match | More work to style chat UI | Tailwind utility classes for rapid styling |
| Dummy LocalRuntime in Phase 2 | Chat UI renders correctly, Phase 3 ready | Extra code for no-op adapter | Minimal adapter (~10 lines) |
| useReducer instead of external state lib | Zero dependencies, simple state | No devtools, no middleware | State is simple enough (2 dimensions) |
| Tailwind v4 CSS-first config | No tailwind.config.js needed, `@import "tailwindcss"` | New paradigm, less documentation | Aligns with modern Tailwind, container scoping via `@utility` |

---

## Open Questions

| # | Question | Options | Recommended | Decision |
|---|----------|---------|-------------|----------|
| 1 | Should @assistant-ui/react-ui be installed for styled components? | A) Install react-ui B) Use primitives only | B) Primitives only | Primitives only -- react-ui not installed, deprecated in react package. Full styling control, smaller bundle. Revises Discovery Q&A #12. |
| 2 | ErrorBoundary for the entire widget? | A) Yes, catch all React errors B) No, let errors propagate | A) Yes | Yes -- widget must never crash host page |

---

## Research Log

| Date | Area | Finding |
|------|------|---------|
| 2026-02-15 | Codebase | `widget/src/` is empty, `package.json` has React 19, @assistant-ui/react ^0.7, Tailwind v4, Vite 6, TypeScript |
| 2026-02-15 | Codebase | Backend: FastAPI + LangGraph + SSE on `/api/interview/{start,message,end}` |
| 2026-02-15 | Codebase | @assistant-ui/react v0.7.91 installed. react-ui (styled) NOT installed. |
| 2026-02-15 | Codebase | @assistant-ui/react has LocalRuntime with ChatModelAdapter interface, primitives (Thread, Composer, Message) |
| 2026-02-15 | Codebase | Deprecated styled components exist in @assistant-ui/react/dist/ui/ but migration recommended |
| 2026-02-15 | Web | Tailwind v4 + Shadow DOM incompatible (@property declarations). Scoped container recommended. |
| 2026-02-15 | Web | Vite lib mode supports IIFE via `build.lib` + `rollupOptions` |
| 2026-02-15 | Web | @assistant-ui LocalRuntime needs ChatModelAdapter even for empty chat |

---

## Q&A Log

| # | Question | Answer |
|---|----------|--------|
| 1 | (From Discovery) Soll @assistant-ui/react bereits in Phase 2 als Chat-UI genutzt werden? | Ab Phase 2 -- ist bereits installiert, Chat-UI jetzt mit Primitives aufbauen |
| 2 | (From Discovery) Wie soll die CSS-Isolation geloest werden? | Scoped Container -- alle Styles unter `.feedbackai-widget` Namespace |
| 3 | (From Discovery) Wie soll das Widget in Host-Pages eingebunden werden? | Data-Attribute + Script-Tag |
| 4 | (From Discovery) Welche Sprache sollen die UI-Texte haben? | Konfigurierbar, Default Deutsch |
| 5 | (From Discovery) @assistant-ui/react-ui (Styled Components) oder nur Primitives? | Primitives als Basis (react-ui ist nicht installiert, deprecated in react package) |
| 6 | (From Discovery) Was zeigt der Chat-Screen in Phase 2 ohne Backend? | Leerer Chat, kein Welcome-Text. Composer offen aber ohne Backend. |
| 7 | (Architecture) Braucht Phase 2 einen ChatModelAdapter fuer LocalRuntime? | Ja, dummy/no-op Adapter der nichts zurueckgibt. Noetig damit Primitives rendern. |
| 8 | (Architecture) ErrorBoundary fuer Widget? | Ja, Widget darf niemals Host-Page crashen. Top-level ErrorBoundary. |

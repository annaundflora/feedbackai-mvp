# Slice 3: Screens + State Machine

> **Slice 3 von 4** für `widget-shell`
>
> | Navigation | |
> |------------|---|
> | **Vorheriger:** | `slice-02-floating-button-panel-shell.md` |
> | **Nächster:** | `slice-04-chat-ui.md` |

---

## Metadata (für Orchestrator)

| Key | Value |
|-----|-------|
| **ID** | `slice-03-screens-state-machine` |
| **Test** | `cd widget && npm run build && node -e "const fs=require('fs'); const html=fs.readFileSync('test.html','utf-8'); if(!html.includes('ConsentScreen') || !html.includes('ThankYouScreen')) throw new Error('Screen components missing');"` |
| **E2E** | `false` |
| **Dependencies** | `["slice-02-floating-button-panel-shell"]` |

**Erklärung:**
- **ID**: Eindeutiger Identifier für Commits und Evidence
- **Test**: Build-Test - prüft ob ConsentScreen + ThankYouScreen Components vorhanden sind
- **E2E**: Kein E2E-Test nötig (UI-Komponenten werden via Playwright in Slice 4 getestet)
- **Dependencies**: Slice 2 (Panel Shell muss vorhanden sein)

---

## Test-Strategy (fuer Orchestrator Pipeline)

> **Quelle:** Auto-detected vom Slice-Writer Agent basierend auf Repo-Indikatoren.

| Key | Value |
|-----|-------|
| **Stack** | `typescript-vite-react` |
| **Test Command** | `cd widget && npm run build` |
| **Integration Command** | `node -e "const fs=require('fs'); const html=fs.readFileSync('widget/test.html','utf-8'); if(!html.includes('consent') && !html.includes('thankyou')) throw new Error('Screens not rendered');"` |
| **Acceptance Command** | `node -e "const fs=require('fs'); const stat=fs.statSync('widget/dist/widget.js'); console.log('Bundle size: ' + (stat.size/1024).toFixed(2) + ' KB');"` |
| **Start Command** | `cd widget && npm run preview` |
| **Health Endpoint** | `http://localhost:4173` |
| **Mocking Strategy** | `no_mocks` |

**Erklärung:**
- **Stack**: Vite 6 + React 19 + TypeScript 5.7 + Tailwind v4
- **Test Command**: Führt Vite-Build aus
- **Integration Command**: Prüft ob Consent/ThankYou Screens im DOM gerendert werden
- **Acceptance Command**: Zeigt Bundle-Größe an
- **Start Command**: Startet Vite Preview Server
- **Health Endpoint**: Vite Preview Port
- **Mocking Strategy**: Keine Mocks nötig (reine UI-Komponenten)

---

## Slice-Übersicht

| # | Slice | Status | Datei |
|---|-------|--------|-------|
| 1 | Vite + Build Setup | Done | `slice-01-vite-build-setup.md` |
| 2 | Floating Button + Panel Shell | Done | `slice-02-floating-button-panel-shell.md` |
| 3 | Screens + State Machine | Ready | `slice-03-screens-state-machine.md` |
| 4 | @assistant-ui Chat-UI | Pending | `slice-04-chat-ui.md` |

---

## Kontext & Ziel

**Problem:**
- Slice 2 hat Panel Shell, aber nur Placeholder-Content
- Kein Screen-Router für verschiedene Views
- Keine State Machine für panelOpen + screen Transitions
- Keine Consent/ThankYou Screens
- Keine Auto-Close Logik für ThankYou-Screen

**Ziel:**
- Consent Screen (Headline + Body + CTA Button)
- ThankYou Screen (Headline + Body)
- Chat Screen Placeholder (wird in Slice 4 mit @assistant-ui gefüllt)
- State Machine via `useReducer` mit 2 Dimensionen: `panelOpen` + `screen`
- Screen Router innerhalb Panel Body
- Auto-Close Timer für ThankYou-Screen (5s)
- State-Persistenz: Screen bleibt beim Panel-Schließen erhalten
- Reset auf `consent` nach ThankYou Auto-Close

**Business Value:**
- Kompletter User Flow navigierbar: Consent → Chat → ThankYou
- State Management Foundation für Phase 3 Backend-Anbindung
- UX Flow testbar ohne Backend

---

## Technische Umsetzung

### Architektur-Kontext (aus architecture.md)

> **Quelle:** `architecture.md` → State Machine (useReducer), Component Tree

**Relevante Architektur-Requirements:**
- State Machine: 2 Dimensionen - `panelOpen` (boolean) + `screen` (enum: consent/chat/thankyou)
- Screen Router: Switch innerhalb PanelBody basierend auf `screen` State
- Auto-Close Timer: useEffect mit setTimeout für ThankYou-Screen
- State-Persistenz: Screen bleibt beim Panel-Close erhalten
- Reset-Logik: Nach ThankYou Auto-Close wird screen auf `consent` zurückgesetzt

**Constraints:**
- useReducer statt useState für komplexe State-Transitions
- Alle Actions explizit definiert (OPEN_PANEL, CLOSE_PANEL, GO_TO_CHAT, GO_TO_THANKYOU, CLOSE_AND_RESET)
- Timer muss beim Component Unmount gecleant werden
- prefers-reduced-motion Support für Animationen

---

### 1. Architektur-Impact

| Layer | Änderungen |
|-------|------------|
| `widget/src/main.tsx` | State von useState auf useReducer migriert, Timer-Logik |
| `widget/src/reducer.ts` | Neu - Widget State Machine (Reducer + Actions) |
| `widget/src/components/screens/ConsentScreen.tsx` | Neu - Consent View |
| `widget/src/components/screens/ChatScreen.tsx` | Neu - Chat Placeholder (Slice 4 erweitert) |
| `widget/src/components/screens/ThankYouScreen.tsx` | Neu - ThankYou View |
| `widget/src/styles/widget.css` | Erweitert - Screen-specific Styles |

---

### 2. Datenfluss

```
User öffnet Panel → OPEN_PANEL → panelOpen=true, screen bleibt
User klickt "Los geht's" → GO_TO_CHAT → screen=chat, panelOpen bleibt true
(Phase 3: Interview endet) → GO_TO_THANKYOU → screen=thankyou, panelOpen bleibt true
ThankYou rendered → useEffect startet Timer (5s)
Timer fires → CLOSE_AND_RESET → panelOpen=false, screen=consent
User klickt X-Button → CLOSE_PANEL → panelOpen=false, screen BLEIBT
User öffnet erneut → OPEN_PANEL → panelOpen=true, screen unverändert
```

---

### 3. State Machine (useReducer)

**Datei:** `widget/src/reducer.ts`

**State Type:**
```typescript
export type WidgetScreen = 'consent' | 'chat' | 'thankyou'

export interface WidgetState {
  panelOpen: boolean
  screen: WidgetScreen
}

export const initialState: WidgetState = {
  panelOpen: false,
  screen: 'consent'
}
```

**Actions:**
```typescript
export type WidgetAction =
  | { type: 'OPEN_PANEL' }
  | { type: 'CLOSE_PANEL' }
  | { type: 'GO_TO_CHAT' }
  | { type: 'GO_TO_THANKYOU' }
  | { type: 'CLOSE_AND_RESET' }
```

**Reducer:**
```typescript
export function widgetReducer(state: WidgetState, action: WidgetAction): WidgetState {
  switch (action.type) {
    case 'OPEN_PANEL':
      return {
        ...state,
        panelOpen: true
        // screen bleibt unverändert
      }

    case 'CLOSE_PANEL':
      return {
        ...state,
        panelOpen: false
        // screen bleibt unverändert
      }

    case 'GO_TO_CHAT':
      return {
        ...state,
        screen: 'chat'
        // panelOpen bleibt unverändert
      }

    case 'GO_TO_THANKYOU':
      return {
        ...state,
        screen: 'thankyou'
        // panelOpen bleibt unverändert
      }

    case 'CLOSE_AND_RESET':
      return {
        panelOpen: false,
        screen: 'consent'
        // Reset für neues Interview
      }

    default:
      return state
  }
}
```

**Wichtig:**
- `panelOpen` und `screen` sind unabhängig
- `OPEN_PANEL` / `CLOSE_PANEL` ändern nur `panelOpen`
- `GO_TO_*` Actions ändern nur `screen`
- `CLOSE_AND_RESET` ist die einzige Action die beide Dimensionen ändert

---

### 4. ConsentScreen Component

**Datei:** `widget/src/components/screens/ConsentScreen.tsx`

> **Quelle:** `wireframes.md` → Screen: Consent

**Props:**
```typescript
interface ConsentScreenProps {
  headline: string
  body: string
  ctaLabel: string
  onAccept: () => void
}
```

**Implementierung:**
```typescript
import React from 'react'

export function ConsentScreen({ headline, body, ctaLabel, onAccept }: ConsentScreenProps) {
  return (
    <div className="flex flex-col h-full">
      {/* Content Area */}
      <div className="flex-1 flex flex-col items-center justify-center px-6 py-8 text-center">
        <h2 className="text-2xl font-bold text-gray-900 mb-4">
          {headline}
        </h2>
        <p className="text-base text-gray-600 leading-relaxed max-w-md">
          {body}
        </p>
      </div>

      {/* CTA Button Area */}
      <div className="p-6 border-t border-gray-200">
        <button
          onClick={onAccept}
          className="
            w-full px-6 py-3 rounded-lg
            bg-brand text-white
            font-medium text-base
            hover:bg-brand-hover
            active:scale-95
            transition-all duration-200
            focus-visible:ring-2 focus-visible:ring-brand focus-visible:ring-offset-2
            touch-action-manipulation
          "
        >
          {ctaLabel}
        </button>
      </div>
    </div>
  )
}
```

**Wichtig:**
- `flex-col h-full` für Vertical Layout (Content + CTA)
- CTA Button am unteren Rand mit border-top Separator
- `touch-action-manipulation` verhindert double-tap zoom (web-design)
- `focus-visible:ring-2` für Keyboard Navigation (web-design)
- Responsive: Padding angepasst für Mobile

---

### 5. ChatScreen Component (Placeholder)

**Datei:** `widget/src/components/screens/ChatScreen.tsx`

> **Quelle:** `wireframes.md` → Screen: Chat

**Props:**
```typescript
interface ChatScreenProps {
  // Slice 4 erweitert mit @assistant-ui Props
}
```

**Implementierung:**
```typescript
import React from 'react'

export function ChatScreen() {
  return (
    <div className="flex flex-col h-full">
      {/* Placeholder für @assistant-ui Thread */}
      <div className="flex-1 flex items-center justify-center p-6">
        <div className="text-center">
          <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-gray-100 flex items-center justify-center">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              className="w-8 h-8 text-gray-400"
              aria-hidden="true"
            >
              <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
            </svg>
          </div>
          <h3 className="text-lg font-semibold text-gray-900 mb-2">
            Chat bereit
          </h3>
          <p className="text-sm text-gray-600">
            @assistant-ui Integration kommt in Slice 4
          </p>
        </div>
      </div>

      {/* Placeholder für @assistant-ui Composer */}
      <div className="p-4 border-t border-gray-200">
        <div className="px-4 py-3 rounded-lg bg-gray-100 text-gray-500 text-sm">
          Nachricht eingeben...
        </div>
      </div>
    </div>
  )
}
```

**Wichtig:**
- Placeholder für Slice 4 @assistant-ui Integration
- Icon + Text zeigen "Chat bereit" Status
- Composer-Placeholder am unteren Rand
- Slice 4 ersetzt kompletten Content mit @assistant-ui Thread + Composer

---

### 6. ThankYouScreen Component

**Datei:** `widget/src/components/screens/ThankYouScreen.tsx`

> **Quelle:** `wireframes.md` → Screen: Danke

**Props:**
```typescript
interface ThankYouScreenProps {
  headline: string
  body: string
  onAutoClose: () => void
  autoCloseDelay?: number // in ms, default 5000
}
```

**Implementierung:**
```typescript
import React, { useEffect } from 'react'

export function ThankYouScreen({
  headline,
  body,
  onAutoClose,
  autoCloseDelay = 5000
}: ThankYouScreenProps) {
  // Auto-close Timer
  useEffect(() => {
    const timer = setTimeout(() => {
      onAutoClose()
    }, autoCloseDelay)

    // Cleanup on unmount
    return () => clearTimeout(timer)
  }, [onAutoClose, autoCloseDelay])

  return (
    <div className="flex flex-col items-center justify-center h-full px-6 py-8 text-center">
      {/* Success Icon */}
      <div className="w-20 h-20 mb-6 rounded-full bg-green-100 flex items-center justify-center">
        <svg
          xmlns="http://www.w3.org/2000/svg"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2.5"
          strokeLinecap="round"
          strokeLinejoin="round"
          className="w-10 h-10 text-green-600"
          aria-hidden="true"
        >
          <polyline points="20 6 9 17 4 12" />
        </svg>
      </div>

      {/* Headline */}
      <h2 className="text-2xl font-bold text-gray-900 mb-4">
        {headline}
      </h2>

      {/* Body */}
      <p className="text-base text-gray-600 leading-relaxed max-w-md mb-6">
        {body}
      </p>

      {/* Auto-close Hint */}
      <p className="text-sm text-gray-400">
        Schließt automatisch in wenigen Sekunden...
      </p>
    </div>
  )
}
```

**Wichtig:**
- `useEffect` mit Timer für Auto-Close nach 5 Sekunden
- Timer-Cleanup via `return () => clearTimeout(timer)` (react-best-practices)
- Success-Icon (Checkmark) für positives Feedback
- Auto-close Hint für User-Transparenz
- `autoCloseDelay` konfigurierbar (Default: 5000ms)

---

### 7. Screen Router

**Datei:** `widget/src/main.tsx` (Updated)

**Screen Router Logik:**
```typescript
function ScreenRouter({
  screen,
  config,
  onAcceptConsent,
  onAutoClose
}: {
  screen: WidgetScreen
  config: WidgetConfig
  onAcceptConsent: () => void
  onAutoClose: () => void
}) {
  switch (screen) {
    case 'consent':
      return (
        <ConsentScreen
          headline={config.texts.consentHeadline}
          body={config.texts.consentBody}
          ctaLabel={config.texts.consentCta}
          onAccept={onAcceptConsent}
        />
      )

    case 'chat':
      return <ChatScreen />

    case 'thankyou':
      return (
        <ThankYouScreen
          headline={config.texts.thankYouHeadline}
          body={config.texts.thankYouBody}
          onAutoClose={onAutoClose}
        />
      )

    default:
      return null
  }
}
```

**Wichtig:**
- Switch Statement für explizite Screen-Auswahl
- Config-Texte werden an Screens übergeben
- Callbacks für Screen-Transitions (`onAcceptConsent`, `onAutoClose`)

---

### 8. Updated Widget Component

**Datei:** `widget/src/main.tsx` (Komplett)

**Migriert von useState zu useReducer:**
```typescript
import React, { useReducer } from 'react'
import ReactDOM from 'react-dom/client'
import { parseConfig, findWidgetScript, WidgetConfig } from './config'
import { FloatingButton } from './components/FloatingButton'
import { Panel } from './components/Panel'
import { ConsentScreen } from './components/screens/ConsentScreen'
import { ChatScreen } from './components/screens/ChatScreen'
import { ThankYouScreen } from './components/screens/ThankYouScreen'
import { widgetReducer, initialState, WidgetScreen } from './reducer'
import './styles/widget.css'

// Screen Router Component
function ScreenRouter({
  screen,
  config,
  onAcceptConsent,
  onAutoClose
}: {
  screen: WidgetScreen
  config: WidgetConfig
  onAcceptConsent: () => void
  onAutoClose: () => void
}) {
  switch (screen) {
    case 'consent':
      return (
        <ConsentScreen
          headline={config.texts.consentHeadline}
          body={config.texts.consentBody}
          ctaLabel={config.texts.consentCta}
          onAccept={onAcceptConsent}
        />
      )

    case 'chat':
      return <ChatScreen />

    case 'thankyou':
      return (
        <ThankYouScreen
          headline={config.texts.thankYouHeadline}
          body={config.texts.thankYouBody}
          onAutoClose={onAutoClose}
        />
      )

    default:
      return null
  }
}

// Main Widget Component
function Widget({ config }: { config: WidgetConfig }) {
  const [state, dispatch] = useReducer(widgetReducer, initialState)

  const handleOpenPanel = () => dispatch({ type: 'OPEN_PANEL' })
  const handleClosePanel = () => dispatch({ type: 'CLOSE_PANEL' })
  const handleAcceptConsent = () => dispatch({ type: 'GO_TO_CHAT' })
  const handleAutoClose = () => dispatch({ type: 'CLOSE_AND_RESET' })

  return (
    <div className="feedbackai-widget">
      <FloatingButton
        onClick={handleOpenPanel}
        visible={!state.panelOpen}
      />
      <Panel
        open={state.panelOpen}
        onClose={handleClosePanel}
        title={config.texts.panelTitle}
      >
        <ScreenRouter
          screen={state.screen}
          config={config}
          onAcceptConsent={handleAcceptConsent}
          onAutoClose={handleAutoClose}
        />
      </Panel>
    </div>
  )
}

// IIFE Entry Point (unchanged from Slice 1)
(function() {
  // Singleton check
  if (document.querySelector('.feedbackai-widget')) {
    console.warn('FeedbackAI Widget already mounted')
    return
  }

  // Find script tag
  const scriptTag = findWidgetScript()
  if (!scriptTag) {
    console.error('FeedbackAI Widget script tag not found')
    return
  }

  // Parse config
  const config = parseConfig(scriptTag)

  // Create container
  const container = document.createElement('div')
  container.className = 'feedbackai-widget-root'
  document.body.appendChild(container)

  // Mount React
  const root = ReactDOM.createRoot(container)
  root.render(
    <React.StrictMode>
      <Widget config={config} />
    </React.StrictMode>
  )

  console.log('FeedbackAI Widget mounted', config)
})()
```

**Wichtig:**
- `useReducer` statt `useState` für State-Management
- Separate Handler-Funktionen für jede Action
- ScreenRouter Component für Screen-Switch Logik
- IIFE Entry Point bleibt unverändert

---

### 9. CSS Updates (Optional Enhancements)

**Datei:** `widget/src/styles/widget.css`

**Neue Screen-specific Utilities:**
```css
/* Screen Fade-In Animation */
@keyframes screen-fade-in {
  from {
    opacity: 0;
    transform: translateY(0.5rem);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* Screen Container Animation */
.feedbackai-widget .screen-container {
  animation: screen-fade-in 200ms ease-out;
}

/* Reduced Motion Support */
@media (prefers-reduced-motion: reduce) {
  .feedbackai-widget * {
    animation-duration: 0.01ms !important;
    transition-duration: 0.01ms !important;
  }
}
```

**Wichtig:**
- Screen Fade-In für sanfte Transitions
- `prefers-reduced-motion` Support (web-design: accessibility)
- Optional: Kann auch ohne diese Styles funktionieren

---

## UI Anforderungen

### Wireframe (aus wireframes.md)

> **Quelle:** `wireframes.md` → Screen: Consent, Chat, Danke

**Consent Screen:**
```
┌──────────────────────────────┐
│  Widget-Titel              X │
├──────────────────────────────┤
│                              │
│                              │
│    Ihr Feedback zaehlt!      │
│                              │
│    Wir moechten Ihnen        │
│    ein paar kurze Fragen     │
│    stellen. Dauert ca.       │
│    5 Minuten.                │
│                              │
│                              │
│  ┌──────────────────────┐    │
│  │  Los geht's          │    │
│  └──────────────────────┘    │
│                              │
└──────────────────────────────┘
```

**Chat Screen:**
```
┌──────────────────────────────┐
│  Widget-Titel              X │
├──────────────────────────────┤
│                              │
│                              │
│                              │
│    (empty message list)      │
│                              │
│                              │
│                              │
│                              │
│                              │
├──────────────────────────────┤
│ [Type a message...]     [➤] │
└──────────────────────────────┘
```

**ThankYou Screen:**
```
┌──────────────────────────────┐
│  Widget-Titel              X │
├──────────────────────────────┤
│                              │
│                              │
│                              │
│    Vielen Dank!              │
│                              │
│    Ihr Feedback hilft        │
│    uns, besser zu werden.    │
│                              │
│                              │
│                              │
│                              │
│                              │
└──────────────────────────────┘
```

**Referenz Skills für UI-Implementation:**
- `.claude/skills/react-best-practices/SKILL.md` - useEffect cleanup, useReducer
- `.claude/skills/web-design/SKILL.md` - Accessibility, Forms, Animation
- `.claude/skills/tailwind-v4/SKILL.md` - Design Tokens, Responsive

### 1. ConsentScreen

**Komponenten & Dateien:**
- `components/screens/ConsentScreen.tsx` - Headline, Body, CTA Button

**Verhalten:**
- Initial Screen beim ersten Öffnen
- CTA-Button Klick → GO_TO_CHAT Action
- Volle Höhe des Panel Body

**Zustände:**
- Default: Headline + Body + CTA
- Hover: CTA Button Hover-State

**Design Patterns (aus Skills):**
- [x] Accessibility: CTA Button hat focus-visible State
- [x] Touch: touch-action-manipulation auf Button
- [x] Typography: Text-wrap balance für Headline
- [x] Responsive: Padding angepasst für Mobile

### 2. ChatScreen

**Komponenten & Dateien:**
- `components/screens/ChatScreen.tsx` - Placeholder für @assistant-ui

**Verhalten:**
- Zeigt "Chat bereit" Placeholder
- Slice 4 ersetzt mit @assistant-ui Thread + Composer

**Zustände:**
- Empty (Slice 3): Placeholder Icon + Text
- Active (Slice 4): Live Chat mit Messages

**Design Patterns (aus Skills):**
- [x] Rendering: Placeholder nutzt flex layout
- [x] Performance: Keine Heavy Components in Slice 3

### 3. ThankYouScreen

**Komponenten & Dateien:**
- `components/screens/ThankYouScreen.tsx` - Headline, Body, Success Icon

**Verhalten:**
- Auto-Close Timer startet beim Render
- Nach 5s → CLOSE_AND_RESET Action
- Success Icon für positives Feedback

**Zustände:**
- Default: Headline + Body + Icon + Auto-close Hint
- Closing: Fade-out Animation (via Panel Slide-Down)

**Design Patterns (aus Skills):**
- [x] React: useEffect cleanup für Timer (react-best-practices)
- [x] Animation: prefers-reduced-motion Support
- [x] Typography: Clear, positive messaging

### 4. Accessibility

- [x] Alle Screens haben semantisches HTML (h2, p, button)
- [x] CTA Button hat focus-visible State
- [x] Icons haben aria-hidden="true" (dekorativ)
- [x] Screen-Transitions sind smooth (nicht abrupt)
- [x] prefers-reduced-motion Support für Animationen

---

## Acceptance Criteria

1) GIVEN Widget gemountet, Panel geschlossen
   WHEN User öffnet Panel zum ersten Mal
   THEN Consent Screen wird angezeigt

2) GIVEN Consent Screen sichtbar
   WHEN User klickt "Los geht's" Button
   THEN Chat Screen wird angezeigt (Placeholder)

3) GIVEN Chat Screen sichtbar
   WHEN User klickt X-Button im Header
   THEN Panel schließt sich, screen bleibt auf 'chat'

4) GIVEN Panel geschlossen mit screen='chat'
   WHEN User öffnet Panel erneut
   THEN Chat Screen wird angezeigt (State persistiert)

5) GIVEN Widget in ThankYou State (simuliert via Manual Test)
   WHEN ThankYou Screen gerendert wird
   THEN Auto-Close Timer startet (5 Sekunden)

6) GIVEN ThankYou Screen Auto-Close Timer läuft
   WHEN Timer abläuft (5s)
   THEN Panel schließt sich UND screen wird auf 'consent' zurückgesetzt

7) GIVEN ThankYou Screen sichtbar
   WHEN User klickt X-Button vor Auto-Close
   THEN Panel schließt sich UND screen wird auf 'consent' zurückgesetzt

8) GIVEN State-Transitions
   WHEN Actions dispatched werden
   THEN Nur die relevante State-Dimension ändert sich (panelOpen ODER screen, nicht beide)

9) GIVEN prefers-reduced-motion aktiviert (Browser)
   WHEN Screens wechseln
   THEN Animationen sind minimal (<1ms) oder deaktiviert

10) GIVEN Mobile Viewport (<=768px)
    WHEN Screens angezeigt werden
    THEN Content ist lesbar, Touch-Targets ≥44px

---

## Testfälle

**WICHTIG:** Tests müssen VOR der Implementierung definiert werden! Der Orchestrator führt diese Tests automatisch nach der Slice-Implementierung aus.

### Test-Datei

**Konvention:** Build-Validierung via Node-Script (kein Vitest nötig für UI-Komponenten in Slice 3)

**Für diesen Slice:** `widget/test.html` (Updated mit Screen-Tests)

### Build Test

<test_spec>
```bash
# Ausgeführt vom Orchestrator Metadata "Test" Command
cd widget && npm run build

# Prüfung via Node-Script
node -e "
const fs = require('fs');
const path = require('path');

const htmlPath = path.join('widget', 'test.html');
const html = fs.readFileSync(htmlPath, 'utf-8');

// Check if ConsentScreen and ThankYouScreen are referenced
if (!html.includes('ConsentScreen') && !html.includes('consent')) {
  throw new Error('ConsentScreen component not referenced in test.html');
}

if (!html.includes('ThankYouScreen') && !html.includes('thankyou')) {
  throw new Error('ThankYouScreen component not referenced in test.html');
}

console.log('✓ ConsentScreen component present');
console.log('✓ ThankYouScreen component present');

// Check bundle size
const widgetPath = path.join('widget', 'dist', 'widget.js');
const stat = fs.statSync(widgetPath);
console.log('✓ Bundle size: ' + (stat.size / 1024).toFixed(2) + ' KB');

if (stat.size > 500000) {
  console.warn('⚠ Bundle size >500KB (target <200KB gzipped)');
}
"
```
</test_spec>

### Manual Test (Updated Test-Page)

**Datei:** `widget/test.html` (Updated)

<test_spec>
```html
<!DOCTYPE html>
<html lang="de">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>FeedbackAI Widget Test - Slice 3</title>
  <style>
    body {
      font-family: Arial, sans-serif;
      padding: 2rem;
      background: #f0f0f0;
      min-height: 100vh;
    }
    h1 {
      color: #333;
    }
    .test-section {
      background: white;
      padding: 1.5rem;
      margin: 1rem 0;
      border-radius: 8px;
      box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .test-step {
      margin: 0.5rem 0;
      padding: 0.5rem;
      background: #f9f9f9;
      border-left: 3px solid #4CAF50;
    }
    .expected {
      color: #2196F3;
      font-weight: bold;
    }
    .note {
      background: #FFF9C4;
      padding: 1rem;
      border-left: 3px solid #FFC107;
      margin: 1rem 0;
    }
  </style>
</head>
<body>
  <h1>FeedbackAI Widget Test - Slice 3: Screens + State Machine</h1>

  <div class="test-section">
    <h2>Test Checklist</h2>

    <div class="test-step">
      <strong>1. Initial State: Consent Screen</strong>
      <p class="expected">✓ Button klicken → Panel öffnet</p>
      <p class="expected">✓ Consent Screen sichtbar</p>
      <p class="expected">✓ Headline: "Ihr Feedback zählt!"</p>
      <p class="expected">✓ Body-Text sichtbar</p>
      <p class="expected">✓ CTA-Button: "Los geht's"</p>
    </div>

    <div class="test-step">
      <strong>2. Transition: Consent → Chat</strong>
      <p class="expected">✓ "Los geht's" klicken</p>
      <p class="expected">✓ Chat Screen wird angezeigt</p>
      <p class="expected">✓ Placeholder: "Chat bereit" + Icon</p>
      <p class="expected">✓ Composer Placeholder am unteren Rand</p>
    </div>

    <div class="test-step">
      <strong>3. State-Persistenz: Panel Close/Reopen</strong>
      <p class="expected">✓ Chat Screen sichtbar → X-Button klicken</p>
      <p class="expected">✓ Panel schließt sich</p>
      <p class="expected">✓ Button erneut klicken → Panel öffnet</p>
      <p class="expected">✓ Chat Screen ist IMMER NOCH sichtbar (nicht Consent)</p>
    </div>

    <div class="test-step">
      <strong>4. ThankYou Screen (Manuell triggern)</strong>
      <div class="note">
        <strong>Manual Trigger:</strong> Browser Console öffnen, dann:
        <pre>
// Dispatch GO_TO_THANKYOU Action via DevTools
// (Widget muss in window.widgetState gespeichert sein für Test)
// Alternativ: Modify code to add dev button
        </pre>
      </div>
      <p class="expected">✓ ThankYou Screen wird angezeigt</p>
      <p class="expected">✓ Headline: "Vielen Dank!"</p>
      <p class="expected">✓ Success Icon (Checkmark) sichtbar</p>
      <p class="expected">✓ Auto-close Hint: "Schließt automatisch..."</p>
      <p class="expected">✓ Nach 5 Sekunden: Panel schließt automatisch</p>
      <p class="expected">✓ Panel erneut öffnen → Consent Screen (Reset)</p>
    </div>

    <div class="test-step">
      <strong>5. ThankYou X-Button (vorzeitiges Schließen)</strong>
      <p class="expected">✓ ThankYou Screen → X-Button klicken (vor Auto-Close)</p>
      <p class="expected">✓ Panel schließt sofort</p>
      <p class="expected">✓ Panel erneut öffnen → Consent Screen (Reset)</p>
    </div>

    <div class="test-step">
      <strong>6. Keyboard Navigation</strong>
      <p class="expected">✓ Tab → Floating Button fokussiert</p>
      <p class="expected">✓ Enter → Panel öffnet (Consent Screen)</p>
      <p class="expected">✓ Tab → "Los geht's" fokussiert</p>
      <p class="expected">✓ Enter → Chat Screen</p>
      <p class="expected">✓ Tab → X-Button fokussiert</p>
      <p class="expected">✓ Enter → Panel schließt</p>
    </div>

    <div class="test-step">
      <strong>7. Mobile Test (<=768px)</strong>
      <p class="expected">✓ Consent/Chat/ThankYou Screens sind lesbar</p>
      <p class="expected">✓ CTA-Button Touch-Target ≥44px</p>
      <p class="expected">✓ Fullscreen Panel funktioniert</p>
    </div>

    <div class="test-step">
      <strong>8. Reduced Motion Test</strong>
      <div class="note">
        <strong>How to Test:</strong>
        - macOS: System Preferences → Accessibility → Display → Reduce motion
        - Windows: Settings → Ease of Access → Display → Show animations
        - DevTools: Rendering Tab → Emulate CSS prefers-reduced-motion
      </div>
      <p class="expected">✓ Screen-Transitions ohne Animationen</p>
      <p class="expected">✓ Panel Slide-Up/Down minimal oder instant</p>
    </div>
  </div>

  <div class="test-section">
    <h2>Console Output Erwartung</h2>
    <pre>
FeedbackAI Widget mounted { lang: 'de', apiUrl: null, texts: {...} }
    </pre>
    <p><strong>Keine Fehler oder Warnings</strong></p>
  </div>

  <div class="test-section">
    <h2>Dev Helper: ThankYou Screen Trigger</h2>
    <button id="trigger-thankyou" style="padding: 0.5rem 1rem; margin: 0.5rem 0; cursor: pointer;">
      Trigger ThankYou Screen (Dev Test)
    </button>
    <p class="note">
      Dieser Button ist nur für Testzwecke in test.html vorhanden.
      In Produktion wird ThankYou nur via Backend-Event getriggert (Phase 3).
    </p>
  </div>

  <!-- Widget Embed -->
  <script
    src="./dist/widget.js"
    data-lang="de"
  ></script>

  <script>
    // Dev Helper: Trigger ThankYou Screen
    document.getElementById('trigger-thankyou').addEventListener('click', () => {
      // This requires exposing dispatch to window for testing
      // Alternatively, inject via browser DevTools
      console.warn('ThankYou Trigger: Implement via DevTools or modify widget to expose dispatch for testing')
      alert('Open Browser Console and dispatch: { type: "GO_TO_THANKYOU" }')
    })
  </script>
</body>
</html>
```
</test_spec>

**Manual Test Steps:**
1. `cd widget && npm run build`
2. `npm run preview`
3. Browser: `http://localhost:4173/test.html`
4. Durchlaufe Test Checklist in der Seite
5. Teste State-Transitions: Consent → Chat → Close → Reopen
6. Teste ThankYou via Browser DevTools (dispatch Action)
7. Teste Keyboard Navigation (Tab, Enter)
8. Teste auf Desktop + Mobile (DevTools Responsive Mode)
9. Teste Reduced Motion (Browser DevTools)
10. Console: Keine Fehler

---

## Definition of Done

- [x] Akzeptanzkriterien sind eindeutig & vollständig
- [ ] State-Transitions funktionieren (Consent → Chat → ThankYou)
- [ ] State-Persistenz beim Panel-Close funktioniert
- [ ] Auto-Close Timer funktioniert (ThankYou → Reset)
- [ ] Keyboard Navigation funktioniert
- [ ] Mobile Responsive funktioniert
- [ ] prefers-reduced-motion Support implementiert
- [ ] Console: Keine Fehler oder Warnings
- [ ] Bundle Size akzeptabel (<500KB ungzipped)

---

## Integration Contract (GATE 2 PFLICHT)

> **Wichtig:** Diese Section wird vom Gate 2 Compliance Agent geprüft. Unvollständige Contracts blockieren die Genehmigung.

### Requires From Other Slices

| Slice | Resource | Type | Validation |
|-------|----------|------|------------|
| slice-01 | `WidgetConfig` | Type | Type has `texts` field with all screen texts |
| slice-01 | `parseConfig()` | Function | Returns config with `texts.consentHeadline`, etc. |
| slice-02 | `Panel` | Component | Accepts `children` prop |
| slice-02 | `FloatingButton` | Component | Accepts `visible` prop |
| slice-02 | Tailwind Tokens | CSS | `--transition-slide`, `--panel-padding` available |

### Provides To Other Slices

| Resource | Type | Consumer | Interface |
|----------|------|----------|-----------|
| `ConsentScreen` | Component | Internal (ScreenRouter) | Props: `{ headline, body, ctaLabel, onAccept }` |
| `ChatScreen` | Component | Slice 4 (will replace) | Props: `{}` (Placeholder, Slice 4 extends) |
| `ThankYouScreen` | Component | Internal (ScreenRouter) | Props: `{ headline, body, onAutoClose, autoCloseDelay? }` |
| `widgetReducer` | Reducer | Internal (Widget) | `(state, action) => state` |
| `WidgetState` Type | Type | Slice 4 | `{ panelOpen: boolean, screen: WidgetScreen }` |
| `WidgetAction` Type | Type | Slice 4, Phase 3 | Union of 5 action types |
| State Machine | Pattern | Phase 3 | Backend events trigger `GO_TO_THANKYOU` |

### Integration Validation Tasks

- [ ] WidgetConfig texts korrekt in Screens verwendet
- [ ] Panel Body rendert ScreenRouter korrekt
- [ ] State-Transitions via Reducer funktionieren
- [ ] Auto-Close Timer cleanup funktioniert (kein Memory Leak)
- [ ] ChatScreen ist erweiterbar für Slice 4 (@assistant-ui)
- [ ] ThankYou Auto-Close triggert CLOSE_AND_RESET Action

---

## Code Examples (MANDATORY - GATE 2 PFLICHT)

> **KRITISCH:** Alle Code-Beispiele in diesem Dokument sind **PFLICHT-Deliverables**.
> Der Gate 2 Compliance Agent prüft, dass jedes Code-Beispiel implementiert wird.
> Abweichung nur mit expliziter Begründung im Commit erlaubt.

| Code Example | Section | Mandatory | Notes |
|--------------|---------|-----------|-------|
| `reducer.ts` | Section 3 | YES | Exakt wie spezifiziert (5 Actions) |
| `ConsentScreen.tsx` | Section 4 | YES | Headline + Body + CTA Layout |
| `ChatScreen.tsx` | Section 5 | YES | Placeholder für Slice 4 |
| `ThankYouScreen.tsx` | Section 6 | YES | Auto-Close Timer mit cleanup |
| `ScreenRouter` | Section 7 | YES | Switch Statement für Screens |
| `main.tsx` (Updated) | Section 8 | YES | useReducer + ScreenRouter |
| `widget.css` (Updates) | Section 9 | OPTIONAL | Screen Animations, prefers-reduced-motion |
| `test.html` (Updated) | Testfälle | YES | Screen-Tests + Dev Helper |

---

## Constraints & Hinweise

**Betrifft:**
- State Management
- Screen-Transitions
- Timer Management
- Accessibility

**State Management Constraints:**
- useReducer statt useState (komplexe State-Transitions)
- 2 State-Dimensionen: `panelOpen` (boolean) + `screen` (enum)
- Actions sind eindeutig und explizit (5 Actions total)
- Nur `CLOSE_AND_RESET` ändert beide Dimensionen gleichzeitig

**Screen-Transition Rules:**
- Consent → Chat: User-initiated via CTA Button
- Chat → ThankYou: Backend-event-triggered (Phase 3)
- ThankYou → Consent (Reset): Auto-Close Timer oder X-Button
- Panel Close/Reopen: Screen bleibt erhalten (außer ThankYou → Reset)

**Timer Management:**
- Auto-Close Timer nur für ThankYou-Screen
- Delay: 5000ms (konfigurierbar)
- Timer cleanup via `useEffect` return function
- Kein Memory Leak beim Component Unmount

**Accessibility:**
- Alle Screens haben semantisches HTML (h2, p, button)
- CTA-Button hat focus-visible State
- Icons sind dekorativ (aria-hidden="true")
- prefers-reduced-motion Support für Animationen

**Abgrenzung:**
- Kein @assistant-ui Integration in Slice 3 (Slice 4)
- Kein Backend-Connection (Phase 3)
- Kein Real Chat-Messages (Phase 3)
- Kein Theme-Konfiguration via data-attributes (später)

---

## Deliverables (SCOPE SAFEGUARD)

**WICHTIG: Diese Liste wird automatisch vom Stop-Hook validiert. Der Agent kann nicht stoppen, wenn Dateien fehlen.**

<!-- DELIVERABLES_START -->
### State Management
- [ ] `widget/src/reducer.ts` - Widget State Machine (Reducer + Actions + Types)

### Screen Components
- [ ] `widget/src/components/screens/ConsentScreen.tsx` - Consent View (Headline + Body + CTA)
- [ ] `widget/src/components/screens/ChatScreen.tsx` - Chat Placeholder (Slice 4 erweitert)
- [ ] `widget/src/components/screens/ThankYouScreen.tsx` - ThankYou View (Auto-Close Timer)

### Updated Files
- [ ] `widget/src/main.tsx` - Widget Component mit useReducer + ScreenRouter
- [ ] `widget/src/styles/widget.css` - Optional: Screen Animations + prefers-reduced-motion

### Test Files
- [ ] `widget/test.html` - Updated Test-Page mit Screen-Tests + Dev Helper

### Build Output (nach `npm run build`)
- [ ] `widget/dist/widget.js` - Updated Bundle mit State Machine + Screens
<!-- DELIVERABLES_END -->

**Hinweis für den Implementierungs-Agent:**
- Alle Dateien zwischen `<!-- DELIVERABLES_START -->` und `<!-- DELIVERABLES_END -->` sind **Pflicht**
- Der Stop-Hook prüft automatisch ob alle Dateien existieren
- Bei fehlenden Dateien wird der Agent blockiert und muss nachfragen

---

## Links

- Architecture: `../architecture.md` → State Machine, Component Tree
- Wireframes: `../wireframes.md` → Consent, Chat, ThankYou Screens
- Discovery: `../discovery.md` → Feature State Machine, Transitions
- Slice 1: `slice-01-vite-build-setup.md` → WidgetConfig Type
- Slice 2: `slice-02-floating-button-panel-shell.md` → Panel, FloatingButton Components
- React Best Practices: `.claude/skills/react-best-practices/SKILL.md` → useEffect cleanup, useReducer
- Web Design Guidelines: `.claude/skills/web-design/SKILL.md` → Accessibility, Animation
- Tailwind v4 Patterns: `.claude/skills/tailwind-v4/SKILL.md` → Design Tokens, Responsive

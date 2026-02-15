# Slice 2: Floating Button + Panel Shell

> **Slice 2 von 4** für `widget-shell`
>
> | Navigation | |
> |------------|---|
> | **Vorheriger:** | `slice-01-vite-build-setup.md` |
> | **Nächster:** | `slice-03-screens-state-machine.md` |

---

## Metadata (für Orchestrator)

| Key | Value |
|-----|-------|
| **ID** | `slice-02-floating-button-panel-shell` |
| **Test** | `cd widget && npm run build && node -e "const fs=require('fs'); const html=fs.readFileSync('test.html','utf-8'); if(!html.includes('FloatingButton')) throw new Error('FloatingButton component missing');"` |
| **E2E** | `false` |
| **Dependencies** | `["slice-01-vite-build-setup"]` |

**Erklärung:**
- **ID**: Eindeutiger Identifier für Commits und Evidence
- **Test**: Build-Test - prüft ob FloatingButton Component im Build vorhanden ist
- **E2E**: Kein E2E-Test nötig (UI-Komponenten werden via Playwright in Slice 4 getestet)
- **Dependencies**: Slice 1 (Build Setup muss vorhanden sein)

---

## Test-Strategy (fuer Orchestrator Pipeline)

> **Quelle:** Auto-detected vom Slice-Writer Agent basierend auf Repo-Indikatoren.

| Key | Value |
|-----|-------|
| **Stack** | `typescript-vite-react` |
| **Test Command** | `cd widget && npm run build` |
| **Integration Command** | `node -e "const fs=require('fs'); const html=fs.readFileSync('widget/test.html','utf-8'); if(!html.includes('floating-button')) throw new Error('FloatingButton not rendered');"` |
| **Acceptance Command** | `node -e "const fs=require('fs'); const stat=fs.statSync('widget/dist/widget.js'); console.log('Bundle size: ' + (stat.size/1024).toFixed(2) + ' KB');"` |
| **Start Command** | `cd widget && npm run preview` |
| **Health Endpoint** | `http://localhost:4173` |
| **Mocking Strategy** | `no_mocks` |

**Erklärung:**
- **Stack**: Vite 6 + React 19 + TypeScript 5.7 + Tailwind v4
- **Test Command**: Führt Vite-Build aus
- **Integration Command**: Prüft ob FloatingButton im DOM gerendert wird
- **Acceptance Command**: Zeigt Bundle-Größe an
- **Start Command**: Startet Vite Preview Server
- **Health Endpoint**: Vite Preview Port
- **Mocking Strategy**: Keine Mocks nötig (reine UI-Komponenten)

---

## Slice-Übersicht

| # | Slice | Status | Datei |
|---|-------|--------|-------|
| 1 | Vite + Build Setup | Done | `slice-01-vite-build-setup.md` |
| 2 | Floating Button + Panel Shell | Ready | `slice-02-floating-button-panel-shell.md` |
| 3 | Screens + State Machine | Pending | `slice-03-screens-state-machine.md` |
| 4 | @assistant-ui Chat-UI | Pending | `slice-04-chat-ui.md` |

---

## Kontext & Ziel

**Problem:**
- Slice 1 hat Build-Setup, aber nur Placeholder-Widget
- Kein sichtbares UI für User
- Kein Floating Button zum Öffnen
- Kein Panel-Container für Screens

**Ziel:**
- Floating Button (Chat-Bubble Icon, rund, fixed bottom-right)
- Panel Container (Header, X-Button, Body)
- Slide-Up/Down Animation beim Öffnen/Schließen
- Mobile Fullscreen (<=768px)
- Basic State: `panelOpen` boolean via useState
- CSS-Scoped Styling via Tailwind v4

**Business Value:**
- Erstes sichtbares Widget-UI
- Foundation für alle Screen-Komponenten (Slice 3)
- UX-Grundgerüst für User-Interaktion

---

## Technische Umsetzung

### Architektur-Kontext (aus architecture.md)

> **Quelle:** `architecture.md` → Component Tree, Architecture Layers

**Relevante Architektur-Requirements:**
- Component Tree: `<Widget>` → `<FloatingButton>` + `<Panel>`
- Panel Sublayer: `<PanelHeader>` + `<PanelBody>`
- Scoped Styling: `.feedbackai-widget` Container-Namespace
- Animation: Slide-Up/Down via CSS transitions (300ms)
- Responsive: Mobile Fullscreen (<=768px)

**Constraints:**
- z-index Management: Button (9999), Panel (10000)
- No Layout Shifts: Panel fixed position
- Touch-friendly: Tap targets ≥44px
- Accessibility: Focus states, aria-labels, keyboard navigation

---

### 1. Architektur-Impact

| Layer | Änderungen |
|-------|------------|
| `widget/src/main.tsx` | Widget Component erweitert mit FloatingButton + Panel |
| `widget/src/components/FloatingButton.tsx` | Neu - Runder Button mit Chat-Icon |
| `widget/src/components/Panel.tsx` | Neu - Container mit Header/Body |
| `widget/src/components/PanelHeader.tsx` | Neu - Titel + Close-Button |
| `widget/src/components/PanelBody.tsx` | Neu - Content-Container (Placeholder für Screens) |
| `widget/src/components/icons/ChatBubbleIcon.tsx` | Neu - SVG-Icon für Button |
| `widget/src/components/icons/XIcon.tsx` | Neu - SVG-Icon für Close-Button |
| `widget/src/styles/widget.css` | Erweitert - Animation Keyframes, z-index Tokens |

---

### 2. Datenfluss

```
User klickt Floating Button
  ↓
onClick() → setPanelOpen(true)
  ↓
Panel Component erhält open={true}
  ↓
Panel slide-up Animation (300ms)
  ↓
Panel sichtbar, Button hidden

User klickt X-Button
  ↓
onClose() → setPanelOpen(false)
  ↓
Panel Component erhält open={false}
  ↓
Panel slide-down Animation (300ms)
  ↓
Panel hidden, Button visible
```

---

### 3. State-Management (Widget Component)

**Datei:** `widget/src/main.tsx`

**State:**
```typescript
const [panelOpen, setPanelOpen] = useState(false)
```

**Actions:**
```typescript
const openPanel = () => setPanelOpen(true)
const closePanel = () => setPanelOpen(false)
```

**Wichtig:**
- Single state dimension: `panelOpen` boolean
- Screen-State kommt in Slice 3 (useReducer mit screen enum)
- Slice 2 fokussiert auf Panel-Öffnen/Schließen

---

### 4. Tailwind v4 Design Tokens

**Datei:** `widget/src/styles/widget.css`

**Neue Tokens:**
```css
@theme {
  /* z-index Hierarchy */
  --z-index-floating-button: 9999;
  --z-index-panel: 10000;

  /* Panel Sizing */
  --panel-width: 24rem; /* 384px */
  --panel-height: 37.5rem; /* 600px */
  --panel-border-radius: 1rem;

  /* Spacing */
  --panel-padding: 1rem;

  /* Animation */
  --transition-slide: 300ms cubic-bezier(0.4, 0, 0.2, 1);

  /* Shadows */
  --shadow-floating-button: 0 4px 12px rgba(0, 0, 0, 0.15);
  --shadow-panel: 0 8px 32px rgba(0, 0, 0, 0.12);

  /* Mobile Breakpoint */
  --breakpoint-mobile: 768px;
}
```

**Animation Keyframes:**
```css
@keyframes slide-up {
  from {
    opacity: 0;
    transform: translateY(1rem);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes slide-down {
  from {
    opacity: 1;
    transform: translateY(0);
  }
  to {
    opacity: 0;
    transform: translateY(1rem);
  }
}

@keyframes fade-in {
  from { opacity: 0; }
  to { opacity: 1; }
}

@keyframes fade-out {
  from { opacity: 1; }
  to { opacity: 0; }
}
```

---

### 5. FloatingButton Component

**Datei:** `widget/src/components/FloatingButton.tsx`

**Props:**
```typescript
interface FloatingButtonProps {
  onClick: () => void
  visible: boolean
}
```

**Implementierung:**
```typescript
import React from 'react'
import { ChatBubbleIcon } from './icons/ChatBubbleIcon'

export function FloatingButton({ onClick, visible }: FloatingButtonProps) {
  if (!visible) return null

  return (
    <button
      onClick={onClick}
      aria-label="Feedback geben"
      className="
        fixed bottom-4 right-4
        w-14 h-14 rounded-full
        bg-brand hover:bg-brand-hover
        shadow-floating-button
        flex items-center justify-center
        transition-all duration-200
        hover:scale-110 active:scale-95
        touch-action-manipulation
        focus-visible:ring-2 focus-visible:ring-brand focus-visible:ring-offset-2
        z-[9999]
      "
      style={{
        animation: visible ? 'fade-in 200ms ease-out' : 'fade-out 200ms ease-in'
      }}
    >
      <ChatBubbleIcon className="w-6 h-6 text-white" />
    </button>
  )
}
```

**Wichtig:**
- `aria-label` für Screen Reader (web-design: Icon-only buttons)
- `touch-action-manipulation` verhindert double-tap zoom (web-design)
- `focus-visible` für Keyboard Navigation (web-design)
- Hover/Active Scale Animation (react-best-practices: rendering-performance)
- `z-[9999]` für z-index Hierarchie

---

### 6. Panel Component

**Datei:** `widget/src/components/Panel.tsx`

**Props:**
```typescript
interface PanelProps {
  open: boolean
  onClose: () => void
  title: string
  children: React.ReactNode
}
```

**Implementierung:**
```typescript
import React from 'react'
import { PanelHeader } from './PanelHeader'

export function Panel({ open, onClose, title, children }: PanelProps) {
  if (!open) return null

  return (
    <div
      className="
        fixed bottom-4 right-4
        w-[var(--panel-width)] h-[var(--panel-height)]
        bg-white rounded-[var(--panel-border-radius)]
        shadow-panel
        flex flex-col
        z-[10000]

        /* Mobile Fullscreen */
        max-md:fixed max-md:inset-0
        max-md:w-full max-md:h-full
        max-md:rounded-none
        max-md:bottom-0 max-md:right-0
      "
      style={{
        animation: 'slide-up var(--transition-slide)'
      }}
      role="dialog"
      aria-modal="true"
      aria-labelledby="panel-title"
    >
      <PanelHeader title={title} onClose={onClose} />
      <div className="flex-1 overflow-y-auto p-[var(--panel-padding)]">
        {children}
      </div>
    </div>
  )
}
```

**Wichtig:**
- `role="dialog"` + `aria-modal="true"` für Accessibility (web-design)
- Mobile Fullscreen via `max-md:` Modifier (Tailwind v4)
- `flex-1 overflow-y-auto` für scrollbaren Body
- CSS Custom Properties für Sizing (`var(--panel-width)`)

---

### 7. PanelHeader Component

**Datei:** `widget/src/components/PanelHeader.tsx`

**Props:**
```typescript
interface PanelHeaderProps {
  title: string
  onClose: () => void
}
```

**Implementierung:**
```typescript
import React from 'react'
import { XIcon } from './icons/XIcon'

export function PanelHeader({ title, onClose }: PanelHeaderProps) {
  return (
    <header
      className="
        flex items-center justify-between
        px-[var(--panel-padding)] py-4
        border-b border-gray-200
      "
    >
      <h2
        id="panel-title"
        className="text-lg font-semibold text-gray-900"
      >
        {title}
      </h2>
      <button
        onClick={onClose}
        aria-label="Panel schließen"
        className="
          w-8 h-8 rounded-lg
          flex items-center justify-center
          hover:bg-gray-100
          transition-colors
          focus-visible:ring-2 focus-visible:ring-gray-500
          touch-action-manipulation
        "
      >
        <XIcon className="w-5 h-5 text-gray-500" />
      </button>
    </header>
  )
}
```

**Wichtig:**
- `id="panel-title"` für `aria-labelledby` Referenz im Panel
- X-Button mit `aria-label` (web-design: Icon-only buttons)
- Touch Target ≥32px (44px recommended) (web-design)

---

### 8. PanelBody Component

**Datei:** `widget/src/components/PanelBody.tsx`

**Props:**
```typescript
interface PanelBodyProps {
  children: React.ReactNode
}
```

**Implementierung:**
```typescript
import React from 'react'

export function PanelBody({ children }: PanelBodyProps) {
  return (
    <div className="flex-1 overflow-y-auto p-[var(--panel-padding)]">
      {children}
    </div>
  )
}
```

**Wichtig:**
- Placeholder für Slice 3 (Screens werden hier eingesetzt)
- `overflow-y-auto` für lange Inhalte
- Padding via CSS Custom Property

---

### 9. Icon Components

**Datei:** `widget/src/components/icons/ChatBubbleIcon.tsx`

```typescript
import React from 'react'

export function ChatBubbleIcon({ className }: { className?: string }) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      aria-hidden="true"
    >
      <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
    </svg>
  )
}
```

**Datei:** `widget/src/components/icons/XIcon.tsx`

```typescript
import React from 'react'

export function XIcon({ className }: { className?: string }) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      aria-hidden="true"
    >
      <line x1="18" y1="6" x2="6" y2="18" />
      <line x1="6" y1="6" x2="18" y2="18" />
    </svg>
  )
}
```

**Wichtig:**
- `aria-hidden="true"` da Icons dekorativ sind (Button hat `aria-label`)
- `currentColor` für Farb-Vererbung via `text-*` Klassen
- Simple Lucide-Icons (keine externe Library nötig)

---

### 10. Updated Widget Component

**Datei:** `widget/src/main.tsx`

**Updated Implementierung:**
```typescript
import React, { useState } from 'react'
import ReactDOM from 'react-dom/client'
import { parseConfig, findWidgetScript } from './config'
import { FloatingButton } from './components/FloatingButton'
import { Panel } from './components/Panel'
import './styles/widget.css'

function Widget({ config }: { config: ReturnType<typeof parseConfig> }) {
  const [panelOpen, setPanelOpen] = useState(false)

  return (
    <div className="feedbackai-widget">
      <FloatingButton
        onClick={() => setPanelOpen(true)}
        visible={!panelOpen}
      />
      <Panel
        open={panelOpen}
        onClose={() => setPanelOpen(false)}
        title={config.texts.panelTitle}
      >
        {/* Placeholder Content - Slice 3 wird Screens hier einsetzen */}
        <div className="flex items-center justify-center h-full">
          <div className="text-center">
            <h3 className="text-lg font-semibold text-gray-900 mb-2">
              Panel Content
            </h3>
            <p className="text-sm text-gray-600">
              Screens kommen in Slice 3
            </p>
          </div>
        </div>
      </Panel>
    </div>
  )
}

// IIFE Entry Point (unchanged)
(function() {
  // ... (identical to Slice 1)
})()
```

**Wichtig:**
- Single state: `panelOpen` (Slice 3 erweitert mit `screen` enum)
- FloatingButton verschwindet wenn Panel offen (`visible={!panelOpen}`)
- Panel Content ist Placeholder (Slice 3 fügt Screen-Router ein)

---

## Acceptance Criteria

1) GIVEN Widget gemountet
   WHEN panelOpen=false
   THEN Floating Button ist sichtbar am bottom-right

2) GIVEN Floating Button sichtbar
   WHEN User klickt Button
   THEN Panel gleitet hoch (Slide-Up Animation 300ms)

3) GIVEN Panel offen
   WHEN Animation abgeschlossen
   THEN Panel ist vollständig sichtbar, Floating Button versteckt

4) GIVEN Panel offen
   WHEN User klickt X-Button im Header
   THEN Panel gleitet runter (Slide-Down Animation 300ms), Floating Button erscheint

5) GIVEN Desktop Viewport (>768px)
   WHEN Panel offen
   THEN Panel ist ~400x600px, fixed bottom-right

6) GIVEN Mobile Viewport (<=768px)
   WHEN Panel offen
   THEN Panel ist Fullscreen (100vw x 100vh)

7) GIVEN Floating Button
   WHEN Keyboard Focus (Tab)
   THEN Focus Ring sichtbar (focus-visible:ring-2)

8) GIVEN Floating Button fokussiert
   WHEN User drückt Enter/Space
   THEN Panel öffnet sich

9) GIVEN Panel Header X-Button
   WHEN Keyboard Focus
   THEN Focus Ring sichtbar

10) GIVEN Panel Header X-Button fokussiert
    WHEN User drückt Enter/Space
    THEN Panel schließt sich

---

## Testfälle

### Test-Datei

**Konvention:** Build-Validierung via Node-Script (kein Vitest nötig für UI-Komponenten in Slice 2)

**Für diesen Slice:** `widget/test.html` (Updated mit FloatingButton Test)

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

// Check if FloatingButton is in test.html
if (!html.includes('floating-button') && !html.includes('FloatingButton')) {
  throw new Error('FloatingButton component not referenced in test.html');
}

console.log('✓ FloatingButton component present');

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
  <title>FeedbackAI Widget Test - Slice 2</title>
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
  </style>
</head>
<body>
  <h1>FeedbackAI Widget Test - Slice 2</h1>

  <div class="test-section">
    <h2>Test Checklist</h2>

    <div class="test-step">
      <strong>1. Floating Button Sichtbar</strong>
      <p class="expected">✓ Runder Button am bottom-right (16px Abstand)</p>
      <p class="expected">✓ Chat-Bubble Icon sichtbar</p>
      <p class="expected">✓ Hover: Leichte Scale-Animation</p>
    </div>

    <div class="test-step">
      <strong>2. Button Klick → Panel Öffnen</strong>
      <p class="expected">✓ Panel gleitet hoch (Slide-Up 300ms)</p>
      <p class="expected">✓ Floating Button verschwindet</p>
      <p class="expected">✓ Panel-Header sichtbar mit Titel + X-Button</p>
    </div>

    <div class="test-step">
      <strong>3. Panel Offen (Desktop)</strong>
      <p class="expected">✓ Panel ~400x600px, bottom-right</p>
      <p class="expected">✓ Abgerundete Ecken, Shadow</p>
      <p class="expected">✓ Placeholder Content: "Panel Content"</p>
    </div>

    <div class="test-step">
      <strong>4. X-Button Klick → Panel Schließen</strong>
      <p class="expected">✓ Panel gleitet runter (Slide-Down 300ms)</p>
      <p class="expected">✓ Floating Button erscheint wieder</p>
    </div>

    <div class="test-step">
      <strong>5. Mobile Test (<=768px)</strong>
      <p class="expected">✓ Panel ist Fullscreen (100vw x 100vh)</p>
      <p class="expected">✓ Keine Ecken-Rundung auf Mobile</p>
    </div>

    <div class="test-step">
      <strong>6. Keyboard Navigation</strong>
      <p class="expected">✓ Tab → Floating Button: Focus Ring sichtbar</p>
      <p class="expected">✓ Enter/Space → Panel öffnet</p>
      <p class="expected">✓ Tab → X-Button: Focus Ring sichtbar</p>
      <p class="expected">✓ Enter/Space → Panel schließt</p>
    </div>

    <div class="test-step">
      <strong>7. Touch Test (Mobile)</strong>
      <p class="expected">✓ Button Tap → Panel öffnet</p>
      <p class="expected">✓ Kein double-tap zoom (touch-action)</p>
      <p class="expected">✓ X-Button Tap → Panel schließt</p>
    </div>
  </div>

  <div class="test-section">
    <h2>Console Output Erwartung</h2>
    <pre>
FeedbackAI Widget mounted { lang: 'de', apiUrl: null, texts: {...} }
    </pre>
  </div>

  <!-- Widget Embed -->
  <script
    src="./dist/widget.js"
    data-lang="de"
  ></script>
</body>
</html>
```
</test_spec>

**Manual Test Steps:**
1. `cd widget && npm run build`
2. `npm run preview`
3. Browser: `http://localhost:4173/test.html`
4. Durchlaufe Test Checklist in der Seite
5. Teste auf Desktop (>768px)
6. Teste auf Mobile via DevTools Responsive Mode (<=768px)
7. Teste Keyboard Navigation (Tab, Enter, Escape)
8. Console: Keine Fehler, nur "FeedbackAI Widget mounted"

---

## Integration Contract (GATE 2 PFLICHT)

### Requires From Other Slices

| Slice | Resource | Type | Validation |
|-------|----------|------|------------|
| slice-01 | `WidgetConfig` | Type | Type available with `texts.panelTitle` field |
| slice-01 | `parseConfig()` | Function | Returns config with texts |
| slice-01 | `widget.css` | Tailwind Config | Scoped utilities available |
| slice-01 | IIFE Build | Build Output | `widget.js` builds successfully |

### Provides To Other Slices

| Resource | Type | Consumer | Interface |
|----------|------|----------|-----------|
| `FloatingButton` | Component | Slice 3 | Props: `{ onClick: () => void, visible: boolean }` |
| `Panel` | Component | Slice 3 | Props: `{ open: boolean, onClose: () => void, title: string, children: ReactNode }` |
| `PanelHeader` | Component | Internal | Used by Panel component |
| `PanelBody` | Component | Slice 3 | Container für Screen-Router |
| `panelOpen` State | State Variable | Slice 3 | Will be migrated to useReducer |
| Tailwind Tokens | CSS Custom Props | All Slices | `--z-index-*`, `--panel-*`, `--transition-slide` |

### Integration Validation Tasks

- [ ] `WidgetConfig.texts.panelTitle` korrekt verwendet in Panel
- [ ] FloatingButton versteckt wenn `panelOpen=true`
- [ ] Panel rendert wenn `open=true`
- [ ] Animations korrekt (Slide-Up/Down 300ms)
- [ ] Mobile Fullscreen funktioniert (<=768px)
- [ ] z-index Hierarchie korrekt (Button: 9999, Panel: 10000)

---

## Code Examples (MANDATORY - GATE 2 PFLICHT)

> **KRITISCH:** Alle Code-Beispiele in diesem Dokument sind **PFLICHT-Deliverables**.

| Code Example | Section | Mandatory | Notes |
|--------------|---------|-----------|-------|
| `FloatingButton.tsx` | Section 5 | YES | Exakt wie spezifiziert |
| `Panel.tsx` | Section 6 | YES | Mobile Fullscreen via `max-md:` |
| `PanelHeader.tsx` | Section 7 | YES | Titel + X-Button |
| `PanelBody.tsx` | Section 8 | YES | Placeholder für Screens |
| `ChatBubbleIcon.tsx` | Section 9 | YES | SVG Icon |
| `XIcon.tsx` | Section 9 | YES | SVG Icon |
| `main.tsx` (Updated) | Section 10 | YES | Widget mit FloatingButton + Panel |
| `widget.css` (Updated) | Section 4 | YES | Neue Tokens + Keyframes |
| `test.html` (Updated) | Testfälle | YES | Test-Page mit Checklist |

---

## Constraints & Hinweise

**Betrifft:**
- UI-Komponenten
- CSS Animations
- Responsive Design
- Accessibility

**UI Constraints:**
- Floating Button:
  - Durchmesser: 56px (Desktop), 48px (Mobile minimum)
  - Position: fixed, bottom-right, 16px Abstand
  - z-index: 9999
  - Touch Target: ≥44px (Web Design Guidelines)

- Panel Container:
  - Desktop: ~400x600px, fixed bottom-right, 16px Abstand
  - Mobile: Fullscreen (100vw x 100dvh)
  - z-index: 10000 (höher als Button)
  - Border Radius: 16px (Desktop), 0 (Mobile)

**Animation Constraints:**
- Slide-Up/Down: 300ms cubic-bezier(0.4, 0, 0.2, 1)
- Fade-In/Out: 200ms ease-out/in
- Nur `transform` + `opacity` animieren (GPU-accelerated)
- `prefers-reduced-motion` Support (wird in Slice 3 implementiert)

**Accessibility:**
- Alle Icon-only buttons haben `aria-label`
- Panel hat `role="dialog"` + `aria-modal="true"`
- Focus-visible States für alle interaktiven Elemente
- Keyboard Navigation (Tab, Enter, Space, Escape)

**Abgrenzung:**
- Kein Screen-Content in Slice 2 (nur Placeholder)
- Kein State Machine (kommt in Slice 3 mit useReducer)
- Keine @assistant-ui Integration (Slice 4)
- Kein Backend-Connection (Phase 3)

---

## Deliverables (SCOPE SAFEGUARD)

**WICHTIG: Diese Liste wird automatisch vom Stop-Hook validiert.**

<!-- DELIVERABLES_START -->
### Components
- [ ] `widget/src/components/FloatingButton.tsx` - Runder Button mit Chat-Icon
- [ ] `widget/src/components/Panel.tsx` - Container mit Header/Body
- [ ] `widget/src/components/PanelHeader.tsx` - Titel + X-Button
- [ ] `widget/src/components/PanelBody.tsx` - Content-Container (Placeholder)

### Icons
- [ ] `widget/src/components/icons/ChatBubbleIcon.tsx` - SVG Chat-Bubble Icon
- [ ] `widget/src/components/icons/XIcon.tsx` - SVG X-Icon

### Updated Files
- [ ] `widget/src/main.tsx` - Widget Component mit FloatingButton + Panel State
- [ ] `widget/src/styles/widget.css` - Neue Tokens + Animation Keyframes

### Test Files
- [ ] `widget/test.html` - Updated Test-Page mit Slice 2 Test-Checklist

### Build Output (nach `npm run build`)
- [ ] `widget/dist/widget.js` - Updated Bundle mit UI-Komponenten
<!-- DELIVERABLES_END -->

**Hinweis für den Implementierungs-Agent:**
- Alle Dateien zwischen `<!-- DELIVERABLES_START -->` und `<!-- DELIVERABLES_END -->` sind **Pflicht**
- Der Stop-Hook prüft automatisch ob alle Dateien existieren
- Bei fehlenden Dateien wird der Agent blockiert und muss nachfragen

---

## Links

- Architecture: `../architecture.md` → Component Tree, Architecture Layers
- Wireframes: `../wireframes.md` → Floating Button, Panel Container
- Discovery: `../discovery.md` → UI Components & States
- Slice 1: `slice-01-vite-build-setup.md` → Build Config, WidgetConfig
- React Best Practices: `.claude/skills/react-best-practices/SKILL.md`
- Web Design Guidelines: `.claude/skills/web-design/SKILL.md`
- Tailwind v4 Patterns: `.claude/skills/tailwind-v4/SKILL.md`

# Slice 1: Vite + Build Setup

> **Slice 1 von 4** für `widget-shell`
>
> | Navigation | |
> |------------|---|
> | **Vorheriger:** | — |
> | **Nächster:** | `slice-02-floating-button-panel.md` |

---

## Metadata (für Orchestrator)

| Key | Value |
|-----|-------|
| **ID** | `slice-01-vite-build-setup` |
| **Test** | `cd widget && npm run build && node -e "const fs=require('fs'); const stat=fs.statSync('dist/widget.js'); if(!stat.isFile()) throw new Error('widget.js not found'); console.log('✓ Build successful');"` |
| **E2E** | `false` |
| **Dependencies** | `[]` |

**Erklärung:**
- **ID**: Eindeutiger Identifier für Commits und Evidence
- **Test**: Build-Test - prüft ob `widget.js` erfolgreich gebaut wird
- **E2E**: Kein E2E-Test nötig (Build-Validierung via Node-Script)
- **Dependencies**: Keine - Slice 1 ist das Fundament

---

## Test-Strategy (fuer Orchestrator Pipeline)

> **Quelle:** Auto-detected vom Slice-Writer Agent basierend auf Repo-Indikatoren.

| Key | Value |
|-----|-------|
| **Stack** | `typescript-vite-react` |
| **Test Command** | `cd widget && npm run build` |
| **Integration Command** | `node -e "const fs=require('fs'); const exists=fs.existsSync('widget/dist/widget.js'); if(!exists) throw new Error('Build output missing');"` |
| **Acceptance Command** | `node -e "const fs=require('fs'); const stat=fs.statSync('widget/dist/widget.js'); if(stat.size>500000) console.warn('Warning: Bundle >500KB');"` |
| **Start Command** | `cd widget && npm run preview` |
| **Health Endpoint** | `http://localhost:4173` |
| **Mocking Strategy** | `no_mocks` |

**Erklärung:**
- **Stack**: Vite 6 + React 19 + TypeScript 5.7 + Tailwind v4
- **Test Command**: Führt Vite-Build aus
- **Integration Command**: Prüft ob `widget.js` existiert
- **Acceptance Command**: Warnt wenn Bundle >500KB (Target: <200KB gzipped)
- **Start Command**: Startet Vite Preview Server
- **Health Endpoint**: Vite Preview Port
- **Mocking Strategy**: Keine Mocks nötig (Build-Validierung)

---

## Slice-Übersicht

| # | Slice | Status | Datei |
|---|-------|--------|-------|
| 1 | Vite + Build Setup | Ready | `slice-01-vite-build-setup.md` |
| 2 | Floating Button + Panel Shell | Pending | `slice-02-floating-button-panel.md` |
| 3 | Screens + State Machine | Pending | `slice-03-screens-state-machine.md` |
| 4 | @assistant-ui Chat-UI | Pending | `slice-04-chat-ui.md` |

---

## Kontext & Ziel

**Problem:**
- `widget/src/` ist leer
- Keine Build-Konfiguration vorhanden (`vite.config.ts`, `tsconfig.json`)
- Tailwind v4 nicht konfiguriert
- Kein IIFE-Build für Widget-Embed
- Keine CSS-Scoping-Strategie

**Ziel:**
- Vollständige Vite + TypeScript + Tailwind v4 Build-Pipeline
- IIFE-Build erzeugt einzelne `widget.js`-Datei (React + CSS inline)
- CSS-Scoping via `.feedbackai-widget` Container-Namespace
- Data-Attribute Parsing-Funktion für Script-Tag-Konfiguration
- Build-Output testbar via Plain-HTML Test-Page

**Business Value:**
- Fundament für alle weiteren Slices
- Widget kann als einzelnes Script in Host-Pages eingebunden werden
- CSS-Isolation verhindert Konflikte mit Host-Page

---

## Technische Umsetzung

### Architektur-Kontext (aus architecture.md)

> **Quelle:** `architecture.md` → Architecture Layers, Constraints

**Relevante Architektur-Requirements:**
- IIFE-Build: Einzelne `widget.js` mit React + CSS inline
- CSS-Scoping: `.feedbackai-widget` Container-Namespace
- Tailwind v4: CSS-First Config mit `@theme`
- Data-Attribute Parsing: `data-api-url`, `data-lang`
- No Global Dependencies: Widget muss ohne Module-System funktionieren

**Constraints:**
- Vite lib mode mit `rollupOptions` für IIFE-Format
- CSS inline (kein separates CSS-File)
- React 19 bundled (nicht als externes CDN)
- Tailwind v4 scoped auf `.feedbackai-widget`

---

### 1. Architektur-Impact

| Layer | Änderungen |
|-------|------------|
| `widget/vite.config.ts` | Neu - Lib mode, IIFE, CSS inline |
| `widget/tsconfig.json` | Neu - TypeScript config |
| `widget/src/main.tsx` | Neu - IIFE Entry Point, Config Parser |
| `widget/src/styles/widget.css` | Neu - Tailwind v4 CSS-First Config |
| `widget/src/config.ts` | Neu - Data-Attribute Parser, WidgetConfig Type |
| `widget/dist/widget.js` | Build Output - Single File IIFE |

---

### 2. Datenfluss

```
Script-Tag mit data-* attributes
  ↓
main.tsx (IIFE Auto-Execute)
  ↓
parseConfig(scriptTag) → WidgetConfig
  ↓
createContainer('.feedbackai-widget')
  ↓
ReactDOM.createRoot(container).render(<Widget config={config} />)
```

---

### 3. Vite Config (IIFE Build)

**Datei:** `widget/vite.config.ts`

**Ziel:**
- Lib mode mit IIFE-Format
- Entry: `src/main.tsx`
- Output: Single File `widget.js` (CSS inline)
- React bundled (nicht external)

**Config:**
```typescript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  build: {
    lib: {
      entry: path.resolve(__dirname, 'src/main.tsx'),
      name: 'FeedbackAIWidget',
      formats: ['iife'],
      fileName: () => 'widget.js'
    },
    rollupOptions: {
      output: {
        inlineDynamicImports: true,
        // CSS wird automatisch inline in widget.js
      }
    },
    cssCodeSplit: false,
    minify: 'terser',
    sourcemap: false
  }
})
```

**Wichtig:**
- `formats: ['iife']` - Erzeugt selbst-ausführenden Code
- `inlineDynamicImports: true` - Keine Code-Splits
- `cssCodeSplit: false` - CSS inline in JS
- React nicht als `external` - wird bundled

---

### 4. TypeScript Config

**Datei:** `widget/tsconfig.json`

**Ziel:**
- React 19 JSX Transform
- ES2020 Target (Modern Browsers)
- Strict Type Checking

**Config:**
```json
{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,

    /* Bundler mode */
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "isolatedModules": true,
    "moduleDetection": "force",
    "noEmit": true,
    "jsx": "react-jsx",

    /* Linting */
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true
  },
  "include": ["src"]
}
```

---

### 5. Tailwind v4 CSS-First Config

**Datei:** `widget/src/styles/widget.css`

**Ziel:**
- Tailwind v4 CSS-First Config mit `@theme`
- Scoped zu `.feedbackai-widget` Container
- Design Tokens für Widget-Theme

**CSS:**
```css
@import "tailwindcss";

/* Tailwind v4 Design Tokens */
@theme {
  /* Colors */
  --color-brand: oklch(0.55 0.15 240);
  --color-brand-hover: oklch(0.45 0.15 240);
  --color-text: oklch(0.2 0 0);
  --color-text-secondary: oklch(0.45 0 0);
  --color-bg: oklch(1 0 0);
  --color-border: oklch(0.9 0 0);

  /* Spacing */
  --spacing-panel: 1rem;

  /* Shadows */
  --shadow-panel: 0 4px 16px rgba(0, 0, 0, 0.12);

  /* Animations */
  --transition-slide: 300ms ease-out;
}

/* CSS Reset + Scoping */
.feedbackai-widget {
  /* Reset */
  all: initial;
  box-sizing: border-box;
  font-family: system-ui, -apple-system, sans-serif;
  font-size: 16px;
  line-height: 1.5;
  color: var(--color-text);

  /* Ensure children inherit reset */
  * {
    box-sizing: border-box;
  }
}

/* Scope all Tailwind utilities to widget container */
@layer utilities {
  .feedbackai-widget .btn {
    @apply px-4 py-2 rounded-lg font-medium transition-colors;
  }

  .feedbackai-widget .btn-primary {
    @apply bg-brand text-white hover:bg-brand-hover;
  }
}
```

**Wichtig:**
- `.feedbackai-widget` als Root-Container
- `all: initial` für komplettes CSS-Reset
- Tailwind utilities scoped auf `.feedbackai-widget`

---

### 6. Data-Attribute Config Parser

**Datei:** `widget/src/config.ts`

**Ziel:**
- Parse `data-api-url` und `data-lang` vom Script-Tag
- Merge mit Defaults
- Type-Safe WidgetConfig

**Types:**
```typescript
export type WidgetLang = 'de' | 'en'

export interface WidgetTexts {
  panelTitle: string
  consentHeadline: string
  consentBody: string
  consentCta: string
  thankYouHeadline: string
  thankYouBody: string
  composerPlaceholder: string
}

export interface WidgetConfig {
  apiUrl: string | null
  lang: WidgetLang
  texts: WidgetTexts
}
```

**Parser:**
```typescript
const DEFAULT_TEXTS_DE: WidgetTexts = {
  panelTitle: 'Feedback',
  consentHeadline: 'Ihr Feedback zählt!',
  consentBody: 'Wir möchten Ihnen ein paar kurze Fragen stellen. Dauert ca. 5 Minuten.',
  consentCta: 'Los geht\'s',
  thankYouHeadline: 'Vielen Dank!',
  thankYouBody: 'Ihr Feedback hilft uns, besser zu werden.',
  composerPlaceholder: 'Nachricht eingeben...'
}

const DEFAULT_TEXTS_EN: WidgetTexts = {
  panelTitle: 'Feedback',
  consentHeadline: 'Your Feedback Matters!',
  consentBody: 'We\'d like to ask you a few quick questions. Takes about 5 minutes.',
  consentCta: 'Let\'s start',
  thankYouHeadline: 'Thank You!',
  thankYouBody: 'Your feedback helps us improve.',
  composerPlaceholder: 'Type a message...'
}

export function parseConfig(scriptTag: HTMLScriptElement): WidgetConfig {
  const apiUrl = scriptTag.getAttribute('data-api-url') || null
  const lang = (scriptTag.getAttribute('data-lang') || 'de') as WidgetLang

  // Fallback to de if invalid lang
  const validLang: WidgetLang = ['de', 'en'].includes(lang) ? lang : 'de'

  const texts = validLang === 'en' ? DEFAULT_TEXTS_EN : DEFAULT_TEXTS_DE

  return {
    apiUrl,
    lang: validLang,
    texts
  }
}

export function findWidgetScript(): HTMLScriptElement | null {
  const scripts = document.querySelectorAll('script[src*="widget.js"]')
  return scripts.length > 0 ? (scripts[0] as HTMLScriptElement) : null
}
```

**Wichtig:**
- `findWidgetScript()` findet eigenes Script-Tag via `src*="widget.js"`
- `parseConfig()` liest data-attributes
- Fallback zu Deutsch bei ungültiger `data-lang`

---

### 7. IIFE Entry Point

**Datei:** `widget/src/main.tsx`

**Ziel:**
- IIFE Auto-Execute beim Script-Load
- Container `.feedbackai-widget` erstellen
- React Root mounten
- Widget singleton (nur einmal mounten)

**Code:**
```typescript
import React from 'react'
import ReactDOM from 'react-dom/client'
import { parseConfig, findWidgetScript } from './config'
import './styles/widget.css'

// Placeholder Widget Component (Slice 2 wird echte UI bauen)
function Widget({ config }: { config: ReturnType<typeof parseConfig> }) {
  return (
    <div className="feedbackai-widget">
      <div className="p-4 bg-white rounded shadow">
        <h2>FeedbackAI Widget</h2>
        <p>Language: {config.lang}</p>
        <p>API URL: {config.apiUrl || 'Not set'}</p>
      </div>
    </div>
  )
}

// IIFE Entry Point
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
- IIFE `(function() { ... })()` führt sich selbst aus
- Singleton check via `.feedbackai-widget` Existenz
- Container wird an `document.body` angehängt
- Placeholder Widget (Slice 2 ersetzt das mit echtem UI)

---

## Acceptance Criteria

1) GIVEN `npm run build` ausgeführt
   WHEN Build erfolgreich
   THEN `widget/dist/widget.js` existiert als einzelne Datei

2) GIVEN `widget.js` in Plain-HTML Test-Page mit `<script src="widget.js"></script>`
   WHEN Page geladen
   THEN Widget-Container `.feedbackai-widget` ist im DOM sichtbar

3) GIVEN Script-Tag mit `data-lang="en"`
   WHEN Widget gemountet
   THEN Widget zeigt englische UI-Texte

4) GIVEN Script-Tag mit `data-api-url="https://api.example.com"`
   WHEN Widget gemountet
   THEN Config enthält API-URL

5) GIVEN Script-Tag ohne data-attributes
   WHEN Widget gemountet
   THEN Defaults werden verwendet (lang=de, apiUrl=null)

6) GIVEN `widget.js` zweimal eingebunden
   WHEN Page geladen
   THEN Nur eine Widget-Instanz wird gemountet, Console-Warning erscheint

7) GIVEN Tailwind-Klassen im Widget
   WHEN Widget gerendert
   THEN Styles sind scoped auf `.feedbackai-widget` Container (kein Leak in Host-Page)

---

## Testfälle

### Test-Datei

**Konvention:** Build-Validierung via Node-Script (kein Vitest nötig für Build-Test)

**Für diesen Slice:** `widget/test.html` (Plain-HTML Test-Page)

### Build Test

<test_spec>
```bash
# Ausgeführt vom Orchestrator Metadata "Test" Command
cd widget && npm run build

# Prüfung via Node-Script
node -e "
const fs = require('fs');
const path = require('path');

const widgetPath = path.join('widget', 'dist', 'widget.js');

if (!fs.existsSync(widgetPath)) {
  throw new Error('widget.js not found in dist/');
}

const stat = fs.statSync(widgetPath);
console.log('✓ widget.js exists (' + (stat.size / 1024).toFixed(2) + ' KB)');

if (stat.size > 500000) {
  console.warn('⚠ Bundle size >500KB (target <200KB gzipped)');
}
"
```
</test_spec>

### Manual Test (Plain-HTML Test-Page)

**Datei:** `widget/test.html`

<test_spec>
```html
<!DOCTYPE html>
<html lang="de">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>FeedbackAI Widget Test</title>
  <style>
    body {
      font-family: Arial, sans-serif;
      padding: 2rem;
      background: #f0f0f0;
    }
    h1 {
      color: #333;
    }
  </style>
</head>
<body>
  <h1>FeedbackAI Widget Test Page</h1>
  <p>Das Widget sollte unten rechts erscheinen.</p>

  <!-- Widget Embed -->
  <script
    src="./dist/widget.js"
    data-api-url="https://api.example.com"
    data-lang="de"
  ></script>
</body>
</html>
```
</test_spec>

**Manual Test Steps:**
1. `cd widget && npm run build`
2. `npm run preview` oder `python -m http.server 8000`
3. Browser: `http://localhost:4173/test.html`
4. Erwartung: Widget-Container `.feedbackai-widget` sichtbar
5. Console: "FeedbackAI Widget mounted {lang: 'de', apiUrl: 'https://api.example.com'}"
6. Inspect Element: Tailwind-Klassen unter `.feedbackai-widget` Container

---

## Integration Contract (GATE 2 PFLICHT)

### Requires From Other Slices

| Slice | Resource | Type | Validation |
|-------|----------|------|------------|
| — | — | — | Keine Dependencies (Slice 1 ist Foundation) |

### Provides To Other Slices

| Resource | Type | Consumer | Interface |
|----------|------|----------|-----------|
| `WidgetConfig` | Type | Slice 2, 3, 4 | `{ apiUrl: string \| null, lang: WidgetLang, texts: WidgetTexts }` |
| `parseConfig()` | Function | Slice 2 | `(scriptTag: HTMLScriptElement) => WidgetConfig` |
| `widget.css` | Tailwind Config | Slice 2, 3, 4 | Scoped Tailwind utilities |
| `Widget` Root Component | Component | Slice 2 | Props: `{ config: WidgetConfig }` |
| IIFE Build Output | File | All Slices | `widget/dist/widget.js` (single file) |

### Integration Validation Tasks

- [ ] `WidgetConfig` Type exportiert und verwendbar
- [ ] `parseConfig()` korrekt getestet (data-attributes → Config)
- [ ] Tailwind utilities scoped auf `.feedbackai-widget`
- [ ] IIFE Build erzeugt single file `widget.js`
- [ ] Test-Page kann Widget laden und mounten

---

## Code Examples (MANDATORY - GATE 2 PFLICHT)

> **KRITISCH:** Alle Code-Beispiele in diesem Dokument sind **PFLICHT-Deliverables**.

| Code Example | Section | Mandatory | Notes |
|--------------|---------|-----------|-------|
| `vite.config.ts` | Section 3 | YES | IIFE lib mode exakt wie spezifiziert |
| `tsconfig.json` | Section 4 | YES | React 19 JSX Transform |
| `widget.css` | Section 5 | YES | Tailwind v4 CSS-First Config |
| `config.ts` | Section 6 | YES | Data-Attribute Parser |
| `main.tsx` | Section 7 | YES | IIFE Entry Point |
| `test.html` | Testfälle | YES | Plain-HTML Test-Page |

---

## Constraints & Hinweise

**Betrifft:**
- Vite Build Pipeline
- CSS Isolation
- Data-Attribute Parsing

**Build Constraints:**
- Single File Output (`widget.js`)
- CSS inline (kein separates CSS-File)
- React bundled (nicht external)
- IIFE Format (selbst-ausführend)
- Minified + Tree-Shaken
- Target: <200KB gzipped (Accept: <500KB ungzipped)

**CSS Isolation:**
- Alle Styles unter `.feedbackai-widget` Namespace
- CSS Reset mit `all: initial`
- Tailwind scoped auf Widget Container
- Keine globalen @property Declarations (Tailwind v4 Issue)

**Data-Attribute Konventionen:**
- `data-api-url`: Optional, Backend URL (Phase 3)
- `data-lang`: Optional, `de` oder `en` (Default: `de`)
- Weitere data-attributes in späteren Phasen (Theme, etc.)

**Abgrenzung:**
- Kein UI in Slice 1 (nur Placeholder Widget)
- Kein State Management (Slice 3)
- Keine @assistant-ui Integration (Slice 4)
- Kein Backend-Connection (Phase 3)

---

## Deliverables (SCOPE SAFEGUARD)

**WICHTIG: Diese Liste wird automatisch vom Stop-Hook validiert.**

<!-- DELIVERABLES_START -->
### Build Config
- [ ] `widget/vite.config.ts` - Vite lib mode IIFE build
- [ ] `widget/tsconfig.json` - TypeScript config
- [ ] `widget/package.json` - Scripts updated (build, dev, preview)

### Source Files
- [ ] `widget/src/main.tsx` - IIFE Entry Point
- [ ] `widget/src/config.ts` - Data-Attribute Parser + Types
- [ ] `widget/src/styles/widget.css` - Tailwind v4 CSS-First Config

### Test Files
- [ ] `widget/test.html` - Plain-HTML Test-Page

### Build Output (nach `npm run build`)
- [ ] `widget/dist/widget.js` - Single File IIFE Bundle
<!-- DELIVERABLES_END -->

**Hinweis für den Implementierungs-Agent:**
- Alle Dateien zwischen `<!-- DELIVERABLES_START -->` und `<!-- DELIVERABLES_END -->` sind **Pflicht**
- Der Stop-Hook prüft automatisch ob alle Dateien existieren
- Bei fehlenden Dateien wird der Agent blockiert und muss nachfragen

---

## Links

- Architecture: `../architecture.md`
- Discovery: `../discovery.md`
- Tailwind v4 Skill: `.claude/skills/tailwind-v4/SKILL.md`
- Vite Docs: https://vitejs.dev/guide/build.html#library-mode
- React 19 Docs: https://react.dev/

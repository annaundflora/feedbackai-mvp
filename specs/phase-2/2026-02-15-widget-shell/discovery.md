# Feature: Widget-Shell

**Epic:** Phase 2 -- Widget-Shell
**Status:** Ready
**Wireframes:** `wireframes.md` (optional, same folder)

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

## Current State Reference

> Greenfield -- keine bestehende Widget-Funktionalitaet.

Vorhanden:
- `widget/package.json` mit React 19, @assistant-ui/react ^0.7, Tailwind v4, Vite 6, TypeScript
- `widget/node_modules/` installiert
- `widget/src/` existiert, ist aber leer
- Kein `vite.config.ts`, kein `tsconfig.json`, kein Tailwind-Config

---

## UI Patterns

### Reused Patterns

| Pattern Type | Component | Usage in this Feature |
|--------------|-----------|----------------------|
| -- | -- | Greenfield, keine bestehenden Patterns |

### New Patterns

| Pattern Type | Description | Rationale |
|--------------|-------------|-----------|
| Floating Action Button | Runder Button fixed bottom-right mit Chat-Bubble Icon | Standard-Pattern fuer embeddable Chat-Widgets |
| Overlay Panel | Fixed-positioned Panel mit Header/Body/Footer | Container fuer alle Widget-Screens |
| Screen Router | State-basierter Screen-Switch innerhalb des Panels | Consent/Chat/Danke als separate Views |
| @assistant-ui Primitives | Thread, MessageList, Composer aus @assistant-ui/react | Chat-UI Foundation, wird in Phase 3 mit Runtime verbunden |

---

## User Flow

1. **Host-Page laedt** -> Widget-Script wird ausgefuehrt -> Floating Button erscheint (bottom-right)
2. **Carrier klickt Floating Button** -> Panel gleitet hoch (Slide-Up, 300ms) -> Consent-Screen sichtbar
3. **Carrier liest Consent-Text** -> Klickt "Los geht's" -> Chat-Screen sichtbar
4. **Carrier sieht Chat-UI** -> (Phase 2: leerer Chat mit Composer, Phase 3: Interview startet)
5. **Interview endet** (Phase 3+) -> Danke-Screen wird angezeigt
6. **Danke-Screen** -> Nach ~5 Sekunden schliesst sich das Panel automatisch -> screen wird auf `consent` zurueckgesetzt
7. **Jederzeit: X-Button** -> Panel schliesst sich (panelOpen=false), screen bleibt -> Erneutes Oeffnen zeigt letzten Screen
8. **Nach Danke + Reopen** -> Consent-Screen (neues Interview, Backend liefert Kontext via Summary-Injection in Phase 3)

**Error Paths:**
- Script-Load-Fehler -> Widget rendert sich nicht (kein sichtbarer Fehler fuer User)
- Floating Button nicht sichtbar (z.B. hinter anderem Element) -> z-index Management

---

## UI Layout & Context

### Screen: Floating Button
**Position:** Fixed, bottom-right (16px Abstand)
**When:** Immer sichtbar wenn Panel geschlossen ist

**Layout:**
- Runder Button (48-56px Durchmesser)
- Chat-Bubble SVG-Icon (weiss auf dunklem Hintergrund)
- Hover-State: leichte Scale-Animation
- Verschwindet wenn Panel offen ist

### Screen: Panel Container
**Position:** Fixed, bottom-right (16px Abstand), Desktop ~400x600px
**When:** `panelOpen = true`

**Layout:**
- Header: Widget-Titel (links) + X-Button (rechts)
- Body: Wechselnder Content je nach State (Consent/Chat/Danke)
- Abgerundete Ecken, leichter Shadow
- Mobile: Fullscreen (100vw x 100vh)

### Screen: Consent
**Position:** Panel Body
**When:** `screen = consent`

**Layout:**
- Headline: "Ihr Feedback zaehlt!"
- Intro-Text: "Wir moechten Ihnen ein paar kurze Fragen stellen. Dauert ca. 5 Minuten."
- CTA-Button: "Los geht's" (volle Breite, unten im Panel)

### Screen: Chat
**Position:** Panel Body
**When:** `screen = chat`

**Layout:**
- @assistant-ui/react Thread-Primitives
- Nachrichtenliste (scrollbar, Phase 2: leer)
- Composer/Input-Feld am unteren Rand (Phase 2: sichtbar und offen, ohne Backend-Anbindung)

### Screen: Danke
**Position:** Panel Body
**When:** `screen = thankyou`

**Layout:**
- Headline: "Vielen Dank!"
- Text: "Ihr Feedback hilft uns, besser zu werden."
- Auto-Close: Panel schliesst sich nach ~5 Sekunden automatisch

---

## UI Components & States

| Element | Type | Location | States | Behavior |
|---------|------|----------|--------|----------|
| `floating-button` | Button | Fixed bottom-right | `visible`, `hidden` | Klick oeffnet Panel. Versteckt wenn Panel offen. |
| `panel` | Container | Fixed bottom-right / Fullscreen | `open`, `closed` | Slide-Up ein, Slide-Down aus. 300ms Transition. |
| `panel-header` | Header | Panel Top | -- | Zeigt Titel + X-Button |
| `close-button` | Button | Panel Header rechts | `default`, `hover` | Klick schliesst Panel, State bleibt |
| `consent-cta` | Button | Consent Screen unten | `default`, `hover`, `active` | Klick wechselt zu Chat-State |
| `chat-thread` | @assistant-ui Thread | Chat Screen | `empty`, `active` | Phase 2: leer. Phase 3: Live-Chat |
| `chat-composer` | @assistant-ui Composer | Chat Screen unten | `empty`, `typing` | Phase 2: sichtbar und offen (ohne Backend). Phase 3: funktional angebunden |

---

## Feature State Machine

### 2-Dimensionen-Modell

Das Widget hat **zwei unabhaengige State-Dimensionen**:

| Dimension | Typ | Werte | Beschreibung |
|-----------|-----|-------|--------------|
| `panelOpen` | boolean | `true`, `false` | Ob das Panel sichtbar ist |
| `screen` | enum | `consent`, `chat`, `thankyou` | Welcher Screen im Panel angezeigt wird |

> **Wichtig:** `panelOpen` und `screen` sind unabhaengig. Das Panel kann geschlossen sein (`panelOpen=false`) waehrend `screen=chat` ist. Beim erneuten Oeffnen wird der aktuelle `screen` angezeigt.

### States Overview

| panelOpen | screen | UI | Available Actions |
|-----------|--------|----|-------------------|
| `false` | `consent` | Nur Floating Button sichtbar | Floating Button klicken |
| `false` | `chat` | Nur Floating Button sichtbar | Floating Button klicken |
| `false` | `thankyou` | Nur Floating Button sichtbar | Floating Button klicken |
| `true` | `consent` | Panel offen, Consent-Screen | "Los geht's" klicken, X-Button klicken |
| `true` | `chat` | Panel offen, Chat-Screen | Nachrichten senden (Phase 3), X-Button klicken |
| `true` | `thankyou` | Panel offen, Danke-Screen | X-Button klicken, wartet auf Auto-Close |

> **Rule:** Different UI or different actions = separate state

### Transitions

| panelOpen | screen | Trigger | UI Feedback | Next panelOpen | Next screen | Business Rules |
|-----------|--------|---------|-------------|----------------|-------------|----------------|
| `false` | any | `floating-button` -> click | Panel Slide-Up (300ms), Button verschwindet | `true` | unveraendert | Zeigt aktuellen screen |
| `true` | `consent` | `consent-cta` -> click | Consent-Screen wird durch Chat ersetzt | `true` | `chat` | -- |
| `true` | any | `close-button` -> click | Panel Slide-Down (300ms), Button erscheint | `false` | unveraendert | screen bleibt erhalten |
| `true` | `chat` | Interview endet (Phase 3+) | Chat wird durch Danke ersetzt | `true` | `thankyou` | -- |
| `true` | `thankyou` | Auto-Timer (5s) | Panel Slide-Down (300ms), Button erscheint | `false` | `consent` | **Reset:** screen wird auf `consent` zurueckgesetzt fuer naechstes Interview |
| `true` | `thankyou` | `close-button` -> click | Panel Slide-Down (300ms), Button erscheint | `false` | `consent` | **Reset:** screen wird auf `consent` zurueckgesetzt fuer naechstes Interview |

### Initial State

| Dimension | Wert |
|-----------|------|
| `panelOpen` | `false` |
| `screen` | `consent` |

---

## Business Rules

- Widget darf nur einmal pro Page instanziiert werden (Script-Tag Duplikat-Check)
- CSS darf nicht in Host-Page leaken (Scoped Container `.feedbackai-widget`)
- Host-Page CSS darf Widget nicht beeinflussen (Reset-Styles innerhalb des Containers)
- Floating Button z-index muss hoch genug sein (z-index: 9999+)
- Panel z-index muss ueber Floating Button liegen
- Mobile Breakpoint: <= 768px -> Fullscreen
- Auto-Close Timer auf Danke-Screen: ~5 Sekunden, danach Reset auf `consent`
- Screen-Persistenz: Beim Schliessen (X-Button) und Wieder-Oeffnen bleibt der aktuelle screen erhalten
- Danke-Reset: Nach Auto-Close oder X-Button auf Danke-Screen wird screen auf `consent` zurueckgesetzt (neues Interview moeglich, Backend liefert Kontext via Summary-Injection in Phase 3)
- UI-Texte konfigurierbar ueber Script-Data-Attribute oder Config-Objekt (Default: Deutsch)

---

## Data

| Field | Required | Validation | Notes |
|-------|----------|------------|-------|
| `data-api-url` | No | Valid URL | Backend-URL, erst in Phase 3 relevant |
| `data-lang` | No | `de` oder `en` | Default: `de` |
| `panelOpen` | Internal | Boolean | Ob Panel sichtbar ist. useReducer-basiert |
| `screen` | Internal | Enum: `consent`, `chat`, `thankyou` | Aktueller Screen im Panel. Unabhaengig von panelOpen |

---

## Implementation Slices

> Testable, deployable increments. Each slice delivers user-value.

### Dependencies

```
Slice 1 (Setup) -> Slice 2 (Button + Panel) -> Slice 3 (Screens + State Machine)
                                                    |
                                              Slice 4 (Chat-UI)
```

### Slices

| # | Name | Scope | Testability | Dependencies |
|---|------|-------|-------------|--------------|
| 1 | Vite + Build Setup | vite.config.ts, tsconfig.json, Tailwind v4, IIFE-Build, Scoped CSS, Data-Attribute Parsing | `npm run build` erzeugt einzelne `widget.js`. Script-Tag in Test-HTML laedtWidget. | -- |
| 2 | Floating Button + Panel Shell | Floating Button (Icon, Position), Panel Container (Header, X-Button, Body), Slide-Up/Down Animation, Mobile Fullscreen | Button klicken oeffnet/schliesst Panel. Responsive Test. | Slice 1 |
| 3 | Screens + State Machine | Consent-Screen, Danke-Screen, State Machine (`useReducer`), Screen-Transitions, Auto-Close Timer, State-Persistenz bei Close/Reopen | Navigation: Consent -> Chat (leer) -> Danke. Close + Reopen zeigt letzten Screen. | Slice 2 |
| 4 | @assistant-ui Chat-UI | @assistant-ui/react Primitives einbinden (Thread, Composer), Leerer Chat mit offenem Composer, Styling an Widget-Theme anpassen | Chat-Screen zeigt gestylte UI mit leerem Thread und Eingabefeld. Kein Backend noetig. | Slice 3 |

### Recommended Order

1. **Slice 1:** Vite + Build Setup -- Fundament, ohne das nichts laeuft
2. **Slice 2:** Floating Button + Panel Shell -- Sichtbares Ergebnis, UX-Grundgeruest
3. **Slice 3:** Screens + State Machine -- Kompletter Flow navigierbar
4. **Slice 4:** @assistant-ui Chat-UI -- Chat-UI Integration, Vorbereitung fuer Phase 3

---

## Context & Research

### Similar Patterns in Codebase
| Feature | Location | Relevant because |
|---------|----------|------------------|
| -- | -- | Greenfield, keine aehnlichen Patterns |

### Web Research
| Source | Finding |
|--------|---------|
| makerkit.dev | Embeddable React Widgets: Shadow DOM + Rollup IIFE ist Standard. Shadow DOM hat Tailwind v4 Issues (@property). |
| stackoverflow.com | Vite IIFE-Build via `rollupOptions` mit `banner/footer` oder `build.lib` moeglich |
| assistant-ui.com | LocalRuntime fuer Custom Backends. Styled Components in `@assistant-ui/react-ui`. Primitives wie Radix. |
| reddit.com/r/reactjs | Tailwind v4 Styles in Shadow DOM problematisch. @property Declarations funktionieren nicht. |
| assistant-ui npm | React 19, Tailwind v4 offiziell unterstuetzt. Custom Backend via Adapter. |

---

## Open Questions

| # | Question | Options | Recommended | Decision |
|---|----------|---------|-------------|----------|
| 1 | Soll `@assistant-ui/react-ui` (Styled Components) oder nur Primitives verwendet werden? | A) react-ui (fertige Styles) B) Nur Primitives (custom Styles) | A) react-ui als Basis | react-ui als Basis, dann an Widget-Theme anpassen |
| 2 | Wie soll der Chat-Screen in Phase 2 ohne Backend aussehen? | A) Welcome-Message B) Leerer Chat C) Kein Text | C) Kein Text | Leerer Chat -- kein Welcome-Text. Composer offen (wird in Phase 3 angebunden). |
| 3 | Phase 2 + 3 zusammenfassen oder getrennt? | A) Getrennt B) Zusammen | A) Getrennt | Getrennt lassen -- Phase 2 statisch, Phase 3 Backend-Anbindung |

---

## Research Log

| Date | Area | Finding |
|------|------|---------|
| 2026-02-15 | Web | Vite IIFE-Build: `build.lib` mit format `iife` oder `rollupOptions` banner/footer |
| 2026-02-15 | Web | Shadow DOM + Tailwind v4: Problematisch wegen @property. Scoped Container empfohlen. |
| 2026-02-15 | Web | @assistant-ui/react: LocalRuntime fuer Custom Backends, Primitives fuer Chat-UI |
| 2026-02-15 | Web | Embeddable Widget Standard: Data-Attribute + Script-Tag (Intercom-Pattern) |
| 2026-02-15 | Codebase | widget/src/ ist leer, package.json hat Dependencies, kein Build-Config vorhanden |
| 2026-02-15 | Codebase | Backend komplett (FastAPI, LangGraph, SSE, Supabase) -- kein Widget-Code |

---

## Q&A Log

| # | Question | Answer |
|---|----------|--------|
| 1 | Soll @assistant-ui/react bereits in Phase 2 als Chat-UI genutzt werden, oder erst in Phase 3? | Ab Phase 2 -- ist bereits installiert, Chat-UI jetzt mit Primitives aufbauen, in Phase 3 nur noch Runtime anbinden |
| 2 | Wie soll die CSS-Isolation geloest werden? | Scoped Container -- alle Styles unter `.feedbackai-widget` Namespace. Pragmatisch, Tailwind-kompatibel. |
| 3 | Wie soll das Widget in Host-Pages eingebunden werden? | Data-Attribute + Script-Tag -- konfigurierbar und einfach in jeder App einbindbar |
| 4 | Welche Sprache sollen die UI-Texte haben? | Konfigurierbar, Default Deutsch |
| 5 | Was soll auf dem Consent-Screen stehen? | Kurz + direkt: Headline + 1-2 Saetze + CTA-Button |
| 6 | Was soll auf dem Danke-Screen stehen? | Minimalistisch: Headline + kurzer Satz, Auto-Close nach Sekunden |
| 7 | Soll der Floating Button Text oder Icon haben? | Icon (Chat-Bubble), rund, bottom-right |
| 8 | Wie soll sich das Widget auf Mobile verhalten? | Fullscreen-Overlay |
| 9 | Welches Theme/Farbe? | Neutral/Grau -- weisser Hintergrund, graue/schwarze Akzente |
| 10 | Animation beim Oeffnen/Schliessen? | Slide-Up (300ms) |
| 11 | Close-Verhalten? | X-Button im Header, State bleibt beim Schliessen erhalten |
| 12 | @assistant-ui/react-ui (Styled Components) oder nur Primitives? | react-ui als Basis, dann an Widget-Theme anpassen |
| 13 | Was zeigt der Chat-Screen in Phase 2 ohne Backend? | Leerer Chat, kein Welcome-Text. Composer offen aber ohne Backend. |
| 14 | Phase 2 + Phase 3 zusammenfassen? | Getrennt lassen -- Phase 2 statisches Widget, Phase 3 Backend-Anbindung |
| 15 | Soll die State Machine als flacher State oder 2 Dimensionen modelliert werden? | 2 Dimensionen: panelOpen (boolean) + screen (consent/chat/thankyou) -- klarer fuer Architecture-Agent |
| 16 | Was passiert nach Danke-Screen Auto-Close wenn User erneut oeffnet? | Reset auf consent -- neues Interview. Backend liefert Kontext via Summary-Injection (Phase 3). |
| 17 | Composer in Phase 2: disabled, hidden oder offen? | Offen lassen -- wird in Phase 3 angebunden. Kein User wird es in Phase 2 nutzen. |

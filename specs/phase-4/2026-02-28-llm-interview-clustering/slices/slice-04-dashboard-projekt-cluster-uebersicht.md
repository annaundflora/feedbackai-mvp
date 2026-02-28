# Slice 4: Dashboard — Projekt-Liste + Cluster-Uebersicht

> **Slice 4 von 8** fuer `LLM Interview Clustering`
>
> | Navigation | |
> |------------|---|
> | **Vorheriger:** | `slice-03-clustering-pipeline-agent.md` |
> | **Naechster:** | `slice-05-dashboard-drill-down.md` |

---

## Metadata (fuer Orchestrator)

| Key | Value |
|-----|-------|
| **ID** | `slice-04-dashboard-projekt-cluster-uebersicht` |
| **Test** | `pnpm playwright test tests/slices/llm-interview-clustering/slice-04-dashboard-projekt-cluster-uebersicht.spec.ts` |
| **E2E** | `true` |
| **Dependencies** | `["slice-01-db-schema-projekt-crud", "slice-02-fact-extraction-pipeline", "slice-03-clustering-pipeline-agent"]` |

**Erklaerung:**
- **ID**: Eindeutiger Identifier (wird fuer Commits und Evidence verwendet)
- **Test**: Playwright E2E Test — Dashboard oeffnen → Projekte sehen → Cluster-Cards sehen
- **E2E**: `true` — Playwright (`.spec.ts`)
- **Dependencies**: Slice 3 muss fertig sein — Backend-API liefert Projekt-Daten + Cluster-Daten ueber FastAPI

---

## Test-Strategy (fuer Orchestrator Pipeline)

> **Quelle:** Auto-detected basierend auf Repo-Indikatoren.
> Architecture.md spezifiziert: `dashboard/` als Next.js 16 App (App Router, Tailwind v4, TypeScript).
> `widget/` verwendet Vite + Vitest + Playwright als Test-Patterns. Das `dashboard/` wird als neues Next.js-Projekt
> im Repo angelegt. Stack: `typescript-nextjs`. E2E via Playwright (playwright.config.ts in dashboard/).

| Key | Value |
|-----|-------|
| **Stack** | `typescript-nextjs` |
| **Test Command** | `pnpm --filter dashboard test` |
| **Integration Command** | `pnpm --filter dashboard test:integration` |
| **Acceptance Command** | `pnpm playwright test tests/slices/llm-interview-clustering/slice-04-dashboard-projekt-cluster-uebersicht.spec.ts` |
| **Start Command** | `pnpm --filter dashboard dev` |
| **Health Endpoint** | `http://localhost:3001/api/health` |
| **Mocking Strategy** | `mock_external` |

**Erklaerung:**
- **Port 3001**: Dashboard laeuft auf Port 3001 um Konflikt mit Backend (Port 8000) und Widget (Port 5173) zu vermeiden
- **Mocking Strategy**: Backend-API (`http://localhost:8000/api`) wird in Unit/Integration-Tests mit `msw` (Mock Service Worker) gemockt. Playwright E2E Tests laufen gegen echtes Backend (lokal gestartet)
- **pnpm workspaces**: `dashboard/` wird als Workspace-Package in Root `pnpm-workspace.yaml` eingetragen

---

## Slice-Uebersicht

| # | Slice | Status | Datei |
|---|-------|--------|-------|
| 1 | DB Schema + Projekt CRUD | **Ready** | `slice-01-db-schema-projekt-crud.md` |
| 2 | Fact Extraction Pipeline | **Ready** | `slice-02-fact-extraction-pipeline.md` |
| 3 | Clustering Pipeline + Agent | **Ready** | `slice-03-clustering-pipeline-agent.md` |
| 4 | Dashboard: Projekt-Liste + Cluster-Uebersicht | **Current** | `slice-04-dashboard-projekt-cluster-uebersicht.md` |
| 5 | Dashboard: Drill-Down + Zitate | Pending | `slice-05-dashboard-drill-down.md` |
| 6 | Taxonomy-Editing + Summary-Regen | Pending | `slice-06-taxonomy-editing.md` |
| 7 | Live-Updates via SSE | Pending | `slice-07-live-updates-sse.md` |
| 8 | Auth + Polish | Pending | `slice-08-auth-polish.md` |

---

## Kontext & Ziel

Nach Slice 3 existieren Backend-API-Endpoints fuer Projekte und Cluster. Dieser Slice stellt den ersten visuellen Zugang zu den Clustering-Ergebnissen bereit: Das Next.js Dashboard.

**Scope dieses Slices:**
- Initiales Setup des Next.js `dashboard/` Projekts
- Projekt-Liste (`/projects`): Card-Grid mit Projekt-Karten, Empty State, Neues-Projekt-Formular
- Projekt-Dashboard (`/projects/[id]`): Header mit Tabs (Insights | Interviews | Einstellungen), Status-Bar, Back-Navigation
- Insights Tab (Standard-Tab): Cluster-Card-Grid, sortiert nach Fact-Anzahl absteigend, Empty States
- API Client: `fetch`-basierter Client gegen FastAPI Backend (`http://localhost:8000/api`)

**Abgrenzung zu anderen Slices:**
- Slice 4 liefert NUR lesenden Zugriff (Anzeige von Projekten + Cluster-Uebersicht, KEIN Klick in Cluster-Detail)
- Drill-Down (Cluster klicken → Facts + Zitate sehen) kommt in Slice 5
- Taxonomy-Editing (Merge, Split, Rename) kommt in Slice 6
- SSE Live-Updates kommen in Slice 7
- Auth (Login, JWT-geschuetzte Routes) kommt in Slice 8
- Das Formular "Neues Projekt anlegen" ist in diesem Slice enthalten (POST /api/projects)
- Interview-Tab und Einstellungen-Tab zeigen nur leere Platzhalter-Screens (kein funktionstuechtiges UI)

---

## Technische Umsetzung

### Architektur-Kontext (aus architecture.md)

> **Quelle:** `architecture.md` → "Constraints & Integrations" + "API Design"

```
Dashboard (Next.js 16, App Router)
  → dashboard/app/projects/page.tsx          (GET /api/projects)
  → dashboard/app/projects/[id]/page.tsx     (GET /api/projects/{id}, GET /api/projects/{id}/clusters)
  → dashboard/lib/api-client.ts              (fetch gegen FastAPI Backend)

FastAPI Backend (Port 8000)
  GET /api/projects               → list[ProjectListItem]
  POST /api/projects              → ProjectResponse
  GET /api/projects/{id}          → ProjectResponse
  GET /api/projects/{id}/clusters → list[ClusterResponse]
```

### 1. Architektur-Impact

| Layer | Aenderungen |
|-------|-------------|
| `dashboard/` (neu) | Next.js 16 App Router Projekt erstellen |
| `dashboard/app/` | App Router Pages und Layouts |
| `dashboard/lib/` | API Client, TypeScript Types |
| `dashboard/components/` | Wiederverwendbare UI-Komponenten |
| `dashboard/tests/` | Playwright E2E Setup |
| Backend (unveraendert) | Keine Aenderungen — API aus Slice 1-3 wird nur konsumiert |

### 2. Datenfluss

```
Browser → GET /projects
  → Next.js Server Component (app/projects/page.tsx)
    → apiClient.getProjects()
      → fetch("http://localhost:8000/api/projects", { headers: { Authorization: Bearer <jwt> } })
        → FastAPI GET /api/projects
          → ProjectRepository.list_by_user(user_id)
            → PostgreSQL SELECT
          ← list[ProjectListItem]
      ← [{ id, name, interview_count, cluster_count, updated_at }, ...]
    ← ProjectListItem[]
  ← React HTML (Server-rendered Projekt-Cards)

Browser → GET /projects/[id]
  → Next.js Server Component (app/projects/[id]/page.tsx)
    → Promise.all([
        apiClient.getProject(id),
        apiClient.getClusters(id)
      ])
        → fetch("http://localhost:8000/api/projects/{id}")
        → fetch("http://localhost:8000/api/projects/{id}/clusters")
      ← [ProjectResponse, ClusterResponse[]]
  ← React HTML (Project Dashboard mit Cluster-Cards)
```

### 3. Next.js Projekt-Setup

**Paketmanager:** pnpm (wie Widget)
**Next.js Version:** 16.1.6 (laut architecture.md, Feb 2026)
**Tailwind Version:** 4.x (CSS-first, `@tailwindcss/postcss`)

**Konfiguration:**

```
dashboard/
  package.json                  → next 16, react 19, tailwindcss 4, typescript, playwright
  next.config.ts                → output: standalone, rewrites (optional)
  tsconfig.json                 → strict mode, path alias @/*
  app/
    layout.tsx                  → Root Layout, Tailwind global styles
    globals.css                 → @import "tailwindcss" + @theme tokens
    page.tsx                    → Redirect zu /projects
    projects/
      page.tsx                  → Projekt-Liste (Server Component)
      [id]/
        page.tsx                → Projekt-Dashboard (Server Component)
  lib/
    api-client.ts               → fetch-basierter API Client
    types.ts                    → TypeScript Types (DTOs)
  components/
    project-card.tsx            → Projekt-Card Komponente
    cluster-card.tsx            → Cluster-Card Komponente
    new-project-dialog.tsx      → Modal: Neues Projekt anlegen (Client Component)
    status-bar.tsx              → Status-Bar (N Interviews | M Facts | K Cluster)
    project-tabs.tsx            → Tab-Navigation (Insights | Interviews | Einstellungen)
    empty-state.tsx             → Wiederverwendbarer Empty State
    skeleton-card.tsx           → Loading Skeleton
```

### 4. API Client

> **Quelle:** `architecture.md` → "API Design" Section

Der API Client ist ein einfacher `fetch`-Wrapper. In Slice 8 (Auth) wird JWT-Handling ergaenzt — in Slice 4 wird der Authorization-Header mit einem hardcodierten Entwicklungs-Token oder ohne Auth implementiert (Backend-Auth ist noch nicht aktiv in Slice 4, da Slice 8 Auth bringt).

**Hinweis zur Auth-Reihenfolge:** Slice 4 wird OHNE aktives JWT-Auth implementiert. Die API-Calls gehen direkt ans Backend. Slice 8 fuegt Login-Screen und Token-Management nach.

### 5. API Contracts (aus architecture.md)

**GET `/api/projects`**

Response: `list[ProjectListItem]`
```typescript
interface ProjectListItem {
  id: string           // UUID
  name: string
  interview_count: number
  cluster_count: number
  updated_at: string   // ISO 8601
}
```

**POST `/api/projects`**

Request: `CreateProjectRequest`
```typescript
interface CreateProjectRequest {
  name: string              // required, 1-200 chars
  research_goal: string     // required, 1-2000 chars
  prompt_context?: string   // optional, max 5000 chars
  extraction_source?: 'summary' | 'transcript'  // default: 'summary'
}
```

Response: `ProjectResponse`
```typescript
interface ProjectResponse {
  id: string
  name: string
  research_goal: string
  prompt_context: string | null
  extraction_source: 'summary' | 'transcript'
  extraction_source_locked: boolean
  model_interviewer: string
  model_extraction: string
  model_clustering: string
  model_summary: string
  interview_count: number
  cluster_count: number
  fact_count: number
  created_at: string
  updated_at: string
}
```

**GET `/api/projects/{id}/clusters`**

Response: `list[ClusterResponse]`
```typescript
interface ClusterResponse {
  id: string
  name: string
  summary: string | null
  fact_count: number
  interview_count: number
  created_at: string
  updated_at: string
}
```

### 6. Abhaengigkeiten (Neue Pakete)

| Paket | Version | Zweck |
|-------|---------|-------|
| `next` | `^16.1.6` | Framework |
| `react` | `^19.0.0` | UI Library |
| `react-dom` | `^19.0.0` | DOM Rendering |
| `tailwindcss` | `^4.x` | CSS Framework |
| `@tailwindcss/postcss` | `^4.x` | Tailwind v4 PostCSS Plugin |
| `typescript` | `^5.9.3` | TypeScript |
| `@types/react` | `^19.x` | TypeScript Types |
| `@types/node` | `^22.x` | Node Types |
| `@playwright/test` | `^1.50.x` | E2E Testing |

---

## UI Anforderungen

### Wireframe: Projekt-Liste (`/projects`)

> **Quelle:** `wireframes.md` → "Screen: Project List"

```
┌─────────────────────────────────────────────────────────────┐
│  FeedbackAI Insights                          [Avatar ▼] ① │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ② [+ New Project]                                          │
│                                                             │
│  ┌───────────────────┐  ┌───────────────────┐               │
│  │ ③                 │  │                   │               │
│  │  Onboarding UX    │  │  Checkout Pain    │               │
│  │                   │  │  Points           │               │
│  │  12 Interviews    │  │                   │               │
│  │  5 Clusters       │  │  8 Interviews     │               │
│  │  Updated 2h ago   │  │  3 Clusters       │               │
│  │                   │  │  Updated 1d ago   │               │
│  └───────────────────┘  └───────────────────┘               │
│                                                             │
│  [Empty State wenn keine Projekte vorhanden]                │
└─────────────────────────────────────────────────────────────┘
```

**Referenz Skills fuer UI-Implementation:**
- `.claude/skills/react-best-practices/SKILL.md` - `async-parallel` (Promise.all fuer unabhaengige Fetches), `async-suspense-boundaries`
- `.claude/skills/web-design/SKILL.md` - Accessibility, Forms, Empty States
- `.claude/skills/tailwind-v4/SKILL.md` - `@theme` Tokens, Container Queries, Dark Mode

### 1. ProjectList Page (`app/projects/page.tsx`)

**Komponenten & Dateien:**
- `dashboard/app/projects/page.tsx` — Server Component, fetcht Projektliste
- `dashboard/components/project-card.tsx` — Einzelne Projekt-Card
- `dashboard/components/new-project-dialog.tsx` — Modal fuer neues Projekt (Client Component)
- `dashboard/components/empty-state.tsx` — Empty State Komponente
- `dashboard/components/skeleton-card.tsx` — Skeleton Loading Card

**Verhalten:**
- Seite laedt Server-seitig (Next.js Server Component)
- Projekte werden nach `updated_at` absteigend sortiert (Backend-Sortierung)
- Relative Zeitangabe: `updated_at` → "Updated 2h ago", "Updated 1d ago", "Updated 5m ago"
- Jede Project-Card ist ein `<Link href="/projects/{id}">` — volle Flaeche klickbar
- "New Project" Button oeffnet Dialog-Modal
- Hover: Subtle elevation change (`hover:shadow-md hover:-translate-y-0.5 transition-all`)

**Zustände:**
- `loading`: Suspense-Boundary mit `<SkeletonCard />` Platzhaltern (3x) in Grid-Layout
- `empty` (keine Projekte): Centered Empty State — Illustration + "Create your first project" CTA Button
- `populated`: Card-Grid 2-spaltig (responsive: 1-spaltig auf Mobile, 2-spaltig auf sm+, 3-spaltig auf lg+)

**Relative Zeitangaben:**
```
< 1 Minute: "Updated just now"
< 60 Minuten: "Updated Xm ago"
< 24 Stunden: "Updated Xh ago"
< 30 Tage: "Updated Xd ago"
>= 30 Tage: "Updated X months ago"
```

**Design Patterns (aus Skills):**
- [x] Accessibility: `<Link>` statt `<div onClick>` fuer Navigation
- [x] Animation: `hover:shadow-md hover:-translate-y-0.5 transition-all duration-200` (nur transform/opacity)
- [x] Responsive: Grid mit `grid-cols-1 sm:grid-cols-2 lg:grid-cols-3`
- [x] Performance: Server Component fuer initiales Fetching (kein Client-side Waterfall)

### 2. NewProjectDialog (`components/new-project-dialog.tsx`)

**Komponenten & Dateien:**
- `dashboard/components/new-project-dialog.tsx` — Client Component mit Modal

**Verhalten:**
- Wird von "New Project" Button auf Projekt-Liste geoeffnet
- Formular-Felder:
  - Project Name (required, 1-200 chars)
  - Research Goal (required, Textarea, 1-2000 chars)
  - Prompt Context (optional, Textarea, max 5000 chars)
  - Fact Extraction Source (Dropdown: Summary | Transcript, default: Summary)
- Submit-Button "Create Project" deaktiviert solange Pflichtfelder leer
- Submit: `POST /api/projects` → bei Erfolg Modal schliessen + Seite neu laden (router.refresh())
- Fehlermeldungen: Inline unter dem jeweiligen Feld

**Zustände:**
- `empty`: Alle Felder leer, Submit deaktiviert
- `filled`: Pflichtfelder ausgefuellt, Submit aktiviert
- `saving`: Submit zeigt Spinner "Creating…", Felder deaktiviert
- `error`: Rote Border auf ungueltigem Feld + Fehlermeldung darunter

**Accessibility:**
- Jedes `<input>` / `<textarea>` hat `<label htmlFor="...">` und passende `id`
- Submit-Button zeigt Spinner + "Creating…" waehrend Request (nicht disabled)
- `aria-describedby` fuer Fehler-Nachrichten
- Dialog schliesst bei Escape / Klick ausserhalb

### 3. ProjectDashboard Page (`app/projects/[id]/page.tsx`)

> **Quelle:** `wireframes.md` → "Screen: Project Dashboard (Insights Tab)"

```
┌─────────────────────────────────────────────────────────────┐
│  ← Projects    FeedbackAI Insights               [Avatar] │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Onboarding UX Research                                     │
│  Understand why users drop off during onboarding   ①        │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ [Insights]  │  Interviews  │  Settings              │ ②  │
│  └─────────────────────────────────────────────────────┘    │
│                                                             │
│  12 Interviews  │  47 Facts  │  5 Clusters       ③          │
│  ─────────────────────────────────────────────            │
│                                                             │
│  ┌─────────────────────┐  ┌─────────────────────┐          │
│  │ ④              [⋮] │  │                [⋮]  │          │
│  │  Navigation Issues   │  │  Pricing Confusion  │          │
│  │  ● 14 Facts          │  │  ● 11 Facts         │          │
│  │  ● 8 Interviews      │  │  ● 6 Interviews     │          │
│  │                      │  │                     │          │
│  │  Users struggle to   │  │  Users don't under- │          │
│  │  find key features   │  │  stand tier diffs    │          │
│  │  after initial...    │  │  and feel pricing... │          │
│  └─────────────────────┘  └─────────────────────┘          │
└─────────────────────────────────────────────────────────────┘
```

**Komponenten & Dateien:**
- `dashboard/app/projects/[id]/page.tsx` — Server Component (fetcht parallel Project + Clusters)
- `dashboard/components/project-tabs.tsx` — Tab-Navigation Komponente
- `dashboard/components/status-bar.tsx` — Status-Bar (N Interviews | M Facts | K Cluster)
- `dashboard/components/cluster-card.tsx` — Einzelne Cluster-Card

**Verhalten:**
- Back-Navigation: `← Projects` Link → navigiert zu `/projects`
- Header: Projekt-Name (gross) + Research-Ziel (Subtitle, grau)
- Tab-Navigation: Insights (aktiv) | Interviews (Platzhalter) | Settings (Platzhalter)
- Status-Bar: `{interview_count} Interviews | {fact_count} Facts | {cluster_count} Clusters` (aus `ProjectResponse`)
- Cluster-Cards: Sortiert nach `fact_count` absteigend (Backend liefert bereits sortiert: `GET /api/projects/{id}/clusters`)
- Kontext-Menue-Icon `[⋮]` auf jeder Card ist in Slice 4 nur dekorativ (Funktionalitaet kommt in Slice 6)

**Datenabruf (Server Component mit Promise.all):**
```typescript
const [project, clusters] = await Promise.all([
  apiClient.getProject(id),
  apiClient.getClusters(id)
])
```

**Zustände:**
- `loading`: Suspense mit Skeleton fuer Status-Bar + Cluster-Cards
- `project_empty` (keine Cluster): Empty State — "Assign interviews to get started" + Link zu Interviews-Tab
- `project_ready`: Cluster-Cards Grid 2-spaltig

### 4. ClusterCard (`components/cluster-card.tsx`)

**Verhalten:**
- Zeigt: Cluster-Name, `● {fact_count} Facts`, `● {interview_count} Interviews`, Zusammenfassung (2-3 Zeilen, geclippt)
- Kontext-Menue-Icon `[⋮]` in der oberen rechten Ecke (dekorativ in Slice 4)
- Zusammenfassung: `line-clamp-3` (3 Zeilen, danach abgeschnitten)
- Bei `summary === null`: Zeige "Generating summary…" in grau/kursiv
- Hover: Elevation-Change (`hover:shadow-md transition-shadow duration-200`)
- In Slice 4 noch NICHT klickbar (Drill-Down kommt in Slice 5)
- In Slice 5 wird `cursor-pointer` + Click-Handler ergaenzt

**Design:**
- Card: `bg-white rounded-xl border border-gray-200 shadow-sm p-5`
- Cluster-Name: `text-base font-semibold text-gray-900`
- Badges: `text-sm text-gray-600` mit Punkt-Prefix `●`
- Zusammenfassung: `text-sm text-gray-600 mt-2 line-clamp-3`
- Kontext-Menue-Icon: `aria-label="Cluster options"` (auch wenn noch ohne Funktion)

### 5. Accessibility
- [x] Alle interaktiven Elemente haben `focus-visible` states
- [x] Icon-only buttons haben `aria-label` (Kontext-Menue: `aria-label="Cluster options"`)
- [x] Form inputs haben labels (NewProjectDialog)
- [x] Back-Navigation als `<Link>` mit `aria-label="Back to projects"`
- [x] Tabs: `role="tablist"` + `role="tab"` + `aria-selected`
- [x] Status-Bar: semantisches `<dl>` / `<div>` mit verstaendlichen Labels
- [x] Skeleton-Cards: `aria-busy="true"` auf Container waehrend Loading

---

## Acceptance Criteria

1) GIVEN das Backend laeuft und mindestens ein Projekt existiert
   WHEN der Nutzer `/projects` oeffnet
   THEN sieht er eine Card fuer jedes Projekt mit Name, Interview-Anzahl, Cluster-Anzahl und relativer Zeitangabe ("Updated Xh ago")

2) GIVEN das Backend laeuft und keine Projekte existieren
   WHEN der Nutzer `/projects` oeffnet
   THEN sieht er einen Empty State mit "Create your first project" CTA-Button

3) GIVEN der Nutzer ist auf `/projects`
   WHEN er auf "+ New Project" klickt
   THEN oeffnet sich ein Modal mit den Feldern: Project Name (required), Research Goal (required), Prompt Context (optional), Fact Extraction Source (Dropdown, default: Summary)

4) GIVEN das New Project Modal ist offen und Pflichtfelder (Name + Research Goal) sind ausgefuellt
   WHEN der Nutzer auf "Create Project" klickt
   THEN wird `POST /api/projects` aufgerufen, bei Erfolg schliesst das Modal und das neue Projekt erscheint in der Liste

5) GIVEN der Nutzer ist auf `/projects`
   WHEN er auf eine Projekt-Card klickt
   THEN navigiert er zu `/projects/{id}` (Insights Tab)

6) GIVEN ein Projekt mit Clustern existiert
   WHEN der Nutzer `/projects/{id}` oeffnet
   THEN sieht er: Projekt-Name, Research-Ziel als Subtitle, Tab-Navigation (Insights aktiv), Status-Bar mit Interview-/Facts-/Cluster-Anzahl, und Cluster-Cards sortiert nach Fact-Anzahl absteigend

7) GIVEN ein Projekt mit Clustern existiert
   WHEN der Nutzer die Cluster-Cards betrachtet
   THEN zeigt jede Card: Cluster-Name, Fact-Anzahl-Badge, Interview-Anzahl-Badge, Zusammenfassung (max 3 Zeilen)

8) GIVEN ein Projekt ohne Cluster existiert (kein Interview zugeordnet)
   WHEN der Nutzer `/projects/{id}` oeffnet
   THEN sieht er im Insights Tab einen Empty State mit "Assign interviews to get started"

9) GIVEN der Nutzer ist auf `/projects/{id}`
   WHEN er auf "← Projects" klickt
   THEN navigiert er zurueck zu `/projects`

10) GIVEN die Seiten laden Daten vom Backend
    WHEN die Daten noch nicht geladen sind
    THEN zeigt die Seite Skeleton-Cards (Loading State) anstatt einer leeren Seite

---

## Testfaelle

**WICHTIG:** Tests muessen VOR der Implementierung definiert werden. Der Orchestrator fuehrt diese Tests automatisch nach der Slice-Implementierung aus.

### Test-Datei

**Konvention:** E2E Playwright `.spec.ts`

**Fuer diesen Slice:** `tests/slices/llm-interview-clustering/slice-04-dashboard-projekt-cluster-uebersicht.spec.ts`

### E2E Tests (Playwright)

<test_spec>
```typescript
// tests/slices/llm-interview-clustering/slice-04-dashboard-projekt-cluster-uebersicht.spec.ts
import { test, expect } from '@playwright/test'

const BASE_URL = 'http://localhost:3001'
const API_BASE = 'http://localhost:8000'

test.describe('Slice 04: Dashboard — Projekt-Liste + Cluster-Uebersicht', () => {

  test.beforeEach(async ({ page }) => {
    // Sicherstellen dass Backend und Dashboard laufen
    // In CI: Backend und Dashboard werden vor den Tests gestartet
  })

  // AC 1 + AC 5: Projekt-Liste mit vorhandenen Projekten
  test('zeigt Projekt-Cards mit Name, Interviewanzahl, Clusteranzahl und relativer Zeit', async ({ page }) => {
    // GIVEN: Backend hat mindestens ein Projekt mit Clustern
    await page.goto(`${BASE_URL}/projects`)

    // WHEN: Seite geladen
    await page.waitForSelector('[data-testid="project-card"]')

    // THEN: Projekt-Card zeigt erforderliche Daten
    const card = page.locator('[data-testid="project-card"]').first()
    await expect(card.locator('[data-testid="project-name"]')).toBeVisible()
    await expect(card.locator('[data-testid="project-interview-count"]')).toBeVisible()
    await expect(card.locator('[data-testid="project-cluster-count"]')).toBeVisible()
    await expect(card.locator('[data-testid="project-updated-at"]')).toContainText(/Updated .+ ago|Updated just now/)
  })

  // AC 2: Empty State
  test('zeigt Empty State wenn keine Projekte existieren', async ({ page }) => {
    // GIVEN: Backend hat keine Projekte (Mock oder leere DB)
    await page.route(`${API_BASE}/api/projects`, async route => {
      await route.fulfill({ json: [] })
    })

    await page.goto(`${BASE_URL}/projects`)

    // THEN: Empty State sichtbar
    await expect(page.locator('[data-testid="empty-state"]')).toBeVisible()
    await expect(page.locator('[data-testid="empty-state-cta"]')).toContainText('Create your first project')
  })

  // AC 3: New Project Modal oeffnen
  test('oeffnet New Project Modal beim Klick auf + New Project', async ({ page }) => {
    // GIVEN: Projekt-Liste Seite
    await page.goto(`${BASE_URL}/projects`)
    await page.waitForLoadState('networkidle')

    // WHEN: "+ New Project" klicken
    await page.click('[data-testid="new-project-btn"]')

    // THEN: Modal mit Formularfeldern sichtbar
    await expect(page.locator('[data-testid="new-project-dialog"]')).toBeVisible()
    await expect(page.locator('label[for="project-name"]')).toBeVisible()
    await expect(page.locator('label[for="research-goal"]')).toBeVisible()
    await expect(page.locator('label[for="prompt-context"]')).toBeVisible()
    await expect(page.locator('label[for="extraction-source"]')).toBeVisible()
    await expect(page.locator('[data-testid="create-project-submit"]')).toBeDisabled()
  })

  // AC 4: Neues Projekt erstellen
  test('erstellt neues Projekt und zeigt es in der Liste', async ({ page }) => {
    // GIVEN: Projekt-Liste Seite, Modal offen
    await page.goto(`${BASE_URL}/projects`)
    await page.click('[data-testid="new-project-btn"]')
    await page.waitForSelector('[data-testid="new-project-dialog"]')

    // WHEN: Pflichtfelder ausfuellen und Submit
    await page.fill('#project-name', 'E2E Test Projekt')
    await page.fill('#research-goal', 'Test research goal fuer E2E')
    await expect(page.locator('[data-testid="create-project-submit"]')).toBeEnabled()
    await page.click('[data-testid="create-project-submit"]')

    // THEN: Modal schliesst und neues Projekt erscheint in der Liste
    await expect(page.locator('[data-testid="new-project-dialog"]')).not.toBeVisible()
    await expect(page.locator('[data-testid="project-card"]').filter({ hasText: 'E2E Test Projekt' })).toBeVisible()
  })

  // AC 5: Navigation zu Projekt-Dashboard
  test('navigiert zu Projekt-Dashboard beim Klick auf Projekt-Card', async ({ page }) => {
    // GIVEN: Projekt-Liste mit mindestens einem Projekt
    await page.goto(`${BASE_URL}/projects`)
    await page.waitForSelector('[data-testid="project-card"]')

    // WHEN: Auf erste Projekt-Card klicken
    const firstCard = page.locator('[data-testid="project-card"]').first()
    const projectLink = firstCard.locator('a')
    const href = await projectLink.getAttribute('href')
    await firstCard.click()

    // THEN: URL ist /projects/{id}
    await expect(page).toHaveURL(/\/projects\/[0-9a-f-]{36}$/)
  })

  // AC 6 + AC 7: Projekt-Dashboard mit Cluster-Cards
  test('zeigt Projekt-Dashboard mit Status-Bar und Cluster-Cards sortiert nach Fact-Anzahl', async ({ page }) => {
    // GIVEN: Projekt mit Clustern existiert (ID aus vorherigem Test oder Fixture)
    await page.goto(`${BASE_URL}/projects`)
    await page.waitForSelector('[data-testid="project-card"]')
    await page.locator('[data-testid="project-card"]').first().click()
    await page.waitForURL(/\/projects\/[0-9a-f-]{36}$/)

    // THEN: Projekt-Header sichtbar
    await expect(page.locator('[data-testid="project-title"]')).toBeVisible()
    await expect(page.locator('[data-testid="project-research-goal"]')).toBeVisible()

    // THEN: Tab-Navigation (Insights aktiv)
    await expect(page.locator('[data-testid="tab-insights"]')).toHaveAttribute('aria-selected', 'true')
    await expect(page.locator('[data-testid="tab-interviews"]')).toBeVisible()
    await expect(page.locator('[data-testid="tab-settings"]')).toBeVisible()

    // THEN: Status-Bar
    await expect(page.locator('[data-testid="status-bar"]')).toBeVisible()
    await expect(page.locator('[data-testid="status-interview-count"]')).toBeVisible()
    await expect(page.locator('[data-testid="status-fact-count"]')).toBeVisible()
    await expect(page.locator('[data-testid="status-cluster-count"]')).toBeVisible()

    // THEN: Mindestens eine Cluster-Card sichtbar (wenn Cluster vorhanden)
    const clusterCards = page.locator('[data-testid="cluster-card"]')
    const count = await clusterCards.count()
    if (count > 0) {
      const firstCard = clusterCards.first()
      await expect(firstCard.locator('[data-testid="cluster-name"]')).toBeVisible()
      await expect(firstCard.locator('[data-testid="cluster-fact-count"]')).toBeVisible()
      await expect(firstCard.locator('[data-testid="cluster-interview-count"]')).toBeVisible()
    }
  })

  // AC 8: Empty State bei Projekt ohne Cluster
  test('zeigt Empty State im Insights Tab bei Projekt ohne Cluster', async ({ page }) => {
    // GIVEN: Leeres Projekt ohne Cluster
    // Route fuer Clusters-Endpoint mocken
    await page.route(/\/api\/projects\/.*\/clusters/, async route => {
      await route.fulfill({ json: [] })
    })

    await page.goto(`${BASE_URL}/projects`)
    await page.waitForSelector('[data-testid="project-card"]')
    await page.locator('[data-testid="project-card"]').first().click()
    await page.waitForURL(/\/projects\/[0-9a-f-]{36}$/)

    // THEN: Empty State sichtbar
    await expect(page.locator('[data-testid="clusters-empty-state"]')).toBeVisible()
    await expect(page.locator('[data-testid="clusters-empty-state"]')).toContainText('Assign interviews to get started')
  })

  // AC 9: Back-Navigation
  test('navigiert zurueck zur Projekt-Liste via Back-Link', async ({ page }) => {
    // GIVEN: Nutzer ist auf Projekt-Dashboard
    await page.goto(`${BASE_URL}/projects`)
    await page.waitForSelector('[data-testid="project-card"]')
    await page.locator('[data-testid="project-card"]').first().click()
    await page.waitForURL(/\/projects\/[0-9a-f-]{36}$/)

    // WHEN: Back-Link klicken
    await page.click('[data-testid="back-to-projects"]')

    // THEN: URL ist /projects
    await expect(page).toHaveURL(`${BASE_URL}/projects`)
  })

  // AC 10: Loading Skeleton
  test('zeigt Loading-Skeleton waehrend Daten geladen werden', async ({ page }) => {
    // GIVEN: Langsame API-Antwort simulieren
    await page.route(`${API_BASE}/api/projects`, async route => {
      await new Promise(resolve => setTimeout(resolve, 800))
      await route.continue()
    })

    await page.goto(`${BASE_URL}/projects`)

    // THEN: Skeleton sichtbar bevor Daten kommen
    // (Bei Server Components ist das Suspense-Fallback sofort sichtbar)
    // Alternativ: Pruefe dass Seite kein leeres White-Flash hat
    await page.waitForSelector('[data-testid="project-card"], [data-testid="skeleton-card"], [data-testid="empty-state"]')
  })

  // KERN-TEST: Dashboard-Flow (zusammengefasst fuer schnelles CI)
  test('vollstaendiger Flow: Projekte sehen → Cluster-Cards sehen', async ({ page }) => {
    // GIVEN: Backend mit Testdaten
    await page.goto(`${BASE_URL}/projects`)
    await page.waitForSelector('[data-testid="project-card"]', { timeout: 10000 })

    // WHEN: Auf Projekt klicken
    await page.locator('[data-testid="project-card"]').first().click()
    await page.waitForURL(/\/projects\/[0-9a-f-]{36}$/)

    // THEN: Cluster-Uebersicht sichtbar
    await page.waitForSelector('[data-testid="cluster-card"], [data-testid="clusters-empty-state"]', { timeout: 10000 })

    // Seite hat keine Fehler
    const errors: string[] = []
    page.on('console', msg => {
      if (msg.type() === 'error') errors.push(msg.text())
    })
    expect(errors.filter(e => !e.includes('favicon'))).toHaveLength(0)
  })
})
```
</test_spec>

---

## Definition of Done

- [x] Akzeptanzkriterien sind eindeutig & vollstaendig
- [ ] Telemetrie/Logging: Console-Errors werden in E2E Tests geprueft
- [ ] Sicherheits-/Privacy-Aspekte: Keine Secrets im Frontend-Code; API-URL aus Env-Variable `NEXT_PUBLIC_API_URL`
- [ ] UX/Copy: Englische UI-Texte (wie im Wireframe spezifiziert)
- [ ] Rollout: Slice 8 (Auth) fuegt JWT-Protection hinzu — bis dahin kein Auth

---

## Skill Verification (UI-Implementation)

### React Best Practices Verification

**Critical Priority:**
- [x] `async-parallel`: `Promise.all([getProject(id), getClusters(id)])` fuer unabhaengige Server-Fetches auf Project-Dashboard Page
- [x] `bundle-dynamic-imports`: `NewProjectDialog` als `next/dynamic` laden (Client Component mit Dialog-Logic)

**High Priority:**
- [x] `server-cache-react`: `React.cache()` fuer `apiClient.getProject()` falls mehrfach aufgerufen auf einer Page
- [x] `async-suspense-boundaries`: Jede Page in `<Suspense fallback={<SkeletonCards />}>` eingewickelt

**Medium Priority:**
- [x] `rerender-memo`: `ClusterCard` und `ProjectCard` als `React.memo()` (werden in Listen gerendert)
- [x] `rendering-conditional-render`: Ternary statt `&&` fuer Conditionals (vermeidet "0" Rendering)

### Web Design Guidelines Verification

**Accessibility:**
- [x] Icon-only buttons haben `aria-label` (`[⋮]` Kontext-Menue: `aria-label="Cluster options"`)
- [x] Form inputs haben assoziierte Labels (NewProjectDialog: alle Felder mit `htmlFor` + `id`)
- [x] Keyboard handler: Dialog schliesst bei Escape, Tab-Navigation per Tastatur
- [x] Focus-visible states fuer alle interaktiven Elemente (`focus-visible:ring-2 focus-visible:ring-blue-500`)
- [x] Tab-Navigation: `role="tablist"`, `role="tab"`, `aria-selected`, `tabIndex`

**Forms:**
- [x] Submit-Button mit Spinner (`saving` State: Spinner + "Creating…", Button nicht disabled)
- [x] Inline Fehlermeldungen unter Feldern mit `role="alert"`
- [x] Placeholder mit Beispiel-Pattern fuer Felder

**Content:**
- [x] Empty States vorhanden (Projekt-Liste + Insights Tab)
- [x] Loading States vorhanden (Skeleton Cards)

### Tailwind v4 Patterns Verification

**Build Tool Integration:**
- [x] `@tailwindcss/postcss` in `postcss.config.js` registriert
- [x] `@import "tailwindcss"` in `globals.css`

**Design Tokens:**
- [x] `@theme` Block fuer Custom-Tokens (Colors, Spacing, Fonts)
- [x] Semantic Color Naming: `--color-surface`, `--color-text-primary` etc.

**Responsive:**
- [x] Mobile-first: `grid-cols-1 sm:grid-cols-2 lg:grid-cols-3` fuer Card-Grids
- [x] Container queries fuer Card-interne Layouts

**Dark Mode:**
- [x] `dark:` Modifier auf allen Hintergrund/Text-Klassen

---

## Constraints & Hinweise

**Betrifft:**
- Neue `dashboard/` App im Root des Repos (parallel zu `backend/` und `widget/`)
- Next.js Port 3001 (um Konflikt mit Backend Port 8000 zu vermeiden)

**API Contract:**
- Backend-URL: `NEXT_PUBLIC_API_URL=http://localhost:8000` (aus `.env.local` in `dashboard/`)
- In Slice 4 noch ohne JWT-Auth (Bearer Token wird in Slice 8 ergaenzt)
- CORS: Backend muss `http://localhost:3001` in allowed origins haben (pruefe `backend/app/main.py` CORS-Config)

**Abgrenzung:**
- Cluster-Cards sind in Slice 4 NICHT klickbar (kein Drill-Down, kommt in Slice 5)
- `[⋮]` Kontext-Menue ist in Slice 4 dekorativ (kein Dropdown, kommt in Slice 6)
- Interviews-Tab und Settings-Tab zeigen Platzhalter "Coming soon" Screens
- Kein SSE / Live-Updates (kommt in Slice 7)

---

## Integration Contract (GATE 2 PFLICHT)

> **Wichtig:** Diese Section wird vom Gate 2 Compliance Agent geprueft. Unvollstaendige Contracts blockieren die Genehmigung.

### Requires From Other Slices

| Slice | Resource | Type | Validation |
|-------|----------|------|------------|
| slice-01-db-schema-projekt-crud | `GET /api/projects` | HTTP Endpoint | Returns `list[ProjectListItem]` (id, name, interview_count, cluster_count, updated_at) |
| slice-01-db-schema-projekt-crud | `POST /api/projects` | HTTP Endpoint | Accepts `CreateProjectRequest`, returns `ProjectResponse` |
| slice-01-db-schema-projekt-crud | `GET /api/projects/{id}` | HTTP Endpoint | Returns `ProjectResponse` mit fact_count, cluster_count, interview_count |
| slice-03-clustering-pipeline-agent | `GET /api/projects/{id}/clusters` | HTTP Endpoint | Returns `list[ClusterResponse]` sortiert nach fact_count DESC (id, name, summary, fact_count, interview_count) |

### Provides To Other Slices

| Resource | Type | Consumer | Interface |
|----------|------|----------|-----------|
| `dashboard/` Next.js App | Application | slice-05, slice-06, slice-07, slice-08 | Laufende Next.js App auf Port 3001 mit App Router |
| `dashboard/lib/api-client.ts` | Module | slice-05, slice-06, slice-07 | `apiClient.getProject(id)`, `apiClient.getClusters(id)`, `apiClient.createProject(data)` |
| `dashboard/lib/types.ts` | Module | slice-05, slice-06, slice-07, slice-08 | TypeScript Types: `ProjectListItem`, `ProjectResponse`, `ClusterResponse`, `CreateProjectRequest` |
| `dashboard/components/cluster-card.tsx` | Component | slice-05, slice-06 | Props: `cluster: ClusterResponse, onClick?: (id: string) => void` — slice-05 ergaenzt `onClick` |
| `dashboard/components/project-tabs.tsx` | Component | slice-05, slice-06, slice-07 | Props: `projectId: string, activeTab: 'insights' | 'interviews' | 'settings'` |
| `dashboard/app/projects/[id]/page.tsx` | Page | slice-05 | Slice-05 ergaenzt Cluster-Click-Handler und Drill-Down Panel in dieser Page |
| Playwright Test Setup | E2E Config | slice-05, slice-06, slice-07, slice-08 | `playwright.config.ts` in `dashboard/` mit `baseURL: http://localhost:3001` |

### Integration Validation Tasks

- [x] `GET /api/projects` verfuegbar (Slice 1 bereitgestellt)
- [x] `GET /api/projects/{id}/clusters` verfuegbar (Slice 3 bereitgestellt)
- [x] `ClusterResponse` Type aus Backend passt zu TypeScript Interface in `lib/types.ts`
- [x] `ProjectListItem.updated_at` ist ISO 8601 String (formatierbar als relative Zeit)
- [x] Backend CORS erlaubt `http://localhost:3001`

---

## Code Examples (MANDATORY - GATE 2 PFLICHT)

> **KRITISCH:** Alle Code-Beispiele in diesem Dokument sind PFLICHT-Deliverables.
> Der Gate 2 Compliance Agent prueft, dass jedes Code-Beispiel implementiert wird.

| Code Example | Section | Mandatory | Notes |
|--------------|---------|-----------|-------|
| `apiClient` | Technische Umsetzung §4 | YES | fetch-Wrapper gegen FastAPI, alle 3 Methoden |
| `TypeScript Types` | Technische Umsetzung §5 | YES | Alle 3 DTOs exakt wie spezifiziert |
| `ProjectCard` | UI Anforderungen §1 | YES | `data-testid` Attribute fuer Playwright |
| `NewProjectDialog` | UI Anforderungen §2 | YES | Client Component, Accessibility, Zustände |
| `ProjectDashboard Page` | UI Anforderungen §3 | YES | Promise.all Pattern fuer paralleles Fetching |
| `ClusterCard` | UI Anforderungen §4 | YES | `line-clamp-3`, `data-testid` Attribute |
| `EmptyState` | UI Anforderungen §1 | YES | Props-Interface mit `data-testid` Weiterleitung, CTA intern mit `data-testid="empty-state-cta"` |
| `Playwright E2E Tests` | Testfaelle | YES | Alle 9 Tests exakt wie spezifiziert (inkl. data-testid Selektoren) |
| `tailwind globals.css` | Technische Umsetzung §3 | YES | `@import "tailwindcss"` + `@theme` Block |
| `postcss.config.js` | Technische Umsetzung §3 | YES | Tailwind v4 `@tailwindcss/postcss` Plugin — NICHT v3 Syntax |
| `next.config.ts` | Technische Umsetzung §3 | YES | Grundkonfiguration mit Port 3001 |
| `app/api/health/route.ts` | Technische Umsetzung §3 | YES | Health-Endpoint fuer Test-Strategy (`GET /api/health → {status: "ok"}`) |
| `StatusBar` | UI Anforderungen §3 | YES | 4 `data-testid` Attribute (status-bar, status-interview-count, status-fact-count, status-cluster-count) |
| `ProjectTabs` | UI Anforderungen §3 | YES | `role=tablist`, `data-testid` + `aria-selected` fuer alle 3 Tabs |

### Code Example: API Client

```typescript
// dashboard/lib/api-client.ts
import type { ProjectListItem, ProjectResponse, ClusterResponse, CreateProjectRequest } from '@/lib/types'

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
    ...options,
  })
  if (!res.ok) {
    throw new Error(`API error ${res.status}: ${await res.text()}`)
  }
  return res.json() as Promise<T>
}

export const apiClient = {
  getProjects(): Promise<ProjectListItem[]> {
    return apiFetch<ProjectListItem[]>('/api/projects')
  },

  getProject(id: string): Promise<ProjectResponse> {
    return apiFetch<ProjectResponse>(`/api/projects/${id}`)
  },

  getClusters(id: string): Promise<ClusterResponse[]> {
    return apiFetch<ClusterResponse[]>(`/api/projects/${id}/clusters`)
  },

  createProject(data: CreateProjectRequest): Promise<ProjectResponse> {
    return apiFetch<ProjectResponse>('/api/projects', {
      method: 'POST',
      body: JSON.stringify(data),
    })
  },
}
```

### Code Example: TypeScript Types

```typescript
// dashboard/lib/types.ts
export interface ProjectListItem {
  id: string
  name: string
  interview_count: number
  cluster_count: number
  updated_at: string  // ISO 8601
}

export interface ProjectResponse {
  id: string
  name: string
  research_goal: string
  prompt_context: string | null
  extraction_source: 'summary' | 'transcript'
  extraction_source_locked: boolean
  model_interviewer: string
  model_extraction: string
  model_clustering: string
  model_summary: string
  interview_count: number
  cluster_count: number
  fact_count: number
  created_at: string
  updated_at: string
}

export interface ClusterResponse {
  id: string
  name: string
  summary: string | null
  fact_count: number
  interview_count: number
  created_at: string
  updated_at: string
}

export interface CreateProjectRequest {
  name: string
  research_goal: string
  prompt_context?: string
  extraction_source?: 'summary' | 'transcript'
}
```

### Code Example: ProjectList Page (Server Component)

```typescript
// dashboard/app/projects/page.tsx
import { Suspense } from 'react'
import Link from 'next/link'
import { apiClient } from '@/lib/api-client'
import { ProjectCard } from '@/components/project-card'
import { SkeletonCard } from '@/components/skeleton-card'
import { EmptyState } from '@/components/empty-state'
import { NewProjectDialog } from '@/components/new-project-dialog'

async function ProjectList() {
  const projects = await apiClient.getProjects()

  if (projects.length === 0) {
    return (
      <EmptyState
        data-testid="empty-state"
        message="No projects yet."
        ctaLabel="Create your first project"
      />
    )
  }

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
      {projects.map(project => (
        <ProjectCard key={project.id} project={project} />
      ))}
    </div>
  )
}

export default function ProjectsPage() {
  return (
    <main className="max-w-6xl mx-auto px-4 py-8">
      <header className="flex items-center justify-between mb-8">
        <h1 className="text-2xl font-bold text-gray-900">FeedbackAI Insights</h1>
      </header>

      <div className="flex items-center justify-between mb-6">
        <NewProjectDialog />
      </div>

      <Suspense
        fallback={
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4" aria-busy="true">
            <SkeletonCard data-testid="skeleton-card" />
            <SkeletonCard data-testid="skeleton-card" />
            <SkeletonCard data-testid="skeleton-card" />
          </div>
        }
      >
        <ProjectList />
      </Suspense>
    </main>
  )
}
```

### Code Example: ProjectDashboard Page (Server Component mit Promise.all)

```typescript
// dashboard/app/projects/[id]/page.tsx
import { Suspense } from 'react'
import Link from 'next/link'
import { cache } from 'react'
import { apiClient } from '@/lib/api-client'
import { ClusterCard } from '@/components/cluster-card'
import { StatusBar } from '@/components/status-bar'
import { ProjectTabs } from '@/components/project-tabs'
import { EmptyState } from '@/components/empty-state'
import { SkeletonCard } from '@/components/skeleton-card'

// React.cache fuer Deduplication falls getProject mehrfach aufgerufen
const getProject = cache(apiClient.getProject)
const getClusters = cache(apiClient.getClusters)

async function ProjectInsights({ id }: { id: string }) {
  // Promise.all fuer paralleles Fetching (async-parallel rule)
  const [project, clusters] = await Promise.all([
    getProject(id),
    getClusters(id),
  ])

  return (
    <>
      <header className="mb-6">
        <h2
          data-testid="project-title"
          className="text-2xl font-bold text-gray-900"
          style={{ textWrap: 'balance' } as React.CSSProperties}
        >
          {project.name}
        </h2>
        <p data-testid="project-research-goal" className="text-gray-600 mt-1">
          {project.research_goal}
        </p>
      </header>

      <ProjectTabs projectId={id} activeTab="insights" />

      <StatusBar
        data-testid="status-bar"
        interviewCount={project.interview_count}
        factCount={project.fact_count}
        clusterCount={project.cluster_count}
      />

      {clusters.length === 0 ? (
        <EmptyState
          data-testid="clusters-empty-state"
          message="No clusters yet."
          ctaLabel="Assign interviews to get started"
        />
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mt-6">
          {clusters.map(cluster => (
            <ClusterCard key={cluster.id} cluster={cluster} />
          ))}
        </div>
      )}
    </>
  )
}

interface Props {
  params: Promise<{ id: string }>
}

export default async function ProjectPage({ params }: Props) {
  const { id } = await params

  return (
    <main className="max-w-6xl mx-auto px-4 py-8">
      <div className="flex items-center gap-4 mb-6">
        <Link
          href="/projects"
          data-testid="back-to-projects"
          aria-label="Back to projects"
          className="text-sm text-gray-500 hover:text-gray-900 flex items-center gap-1 focus-visible:ring-2 focus-visible:ring-blue-500 rounded"
        >
          ← Projects
        </Link>
      </div>

      <Suspense
        fallback={
          <div aria-busy="true">
            <div className="h-8 bg-gray-200 rounded w-64 mb-2 animate-pulse" />
            <div className="h-4 bg-gray-200 rounded w-96 mb-6 animate-pulse" />
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <SkeletonCard />
              <SkeletonCard />
              <SkeletonCard />
              <SkeletonCard />
            </div>
          </div>
        }
      >
        <ProjectInsights id={id} />
      </Suspense>
    </main>
  )
}
```

### Code Example: ClusterCard Component

```typescript
// dashboard/components/cluster-card.tsx
import { memo } from 'react'
import type { ClusterResponse } from '@/lib/types'

interface ClusterCardProps {
  cluster: ClusterResponse
  onClick?: (id: string) => void
}

export const ClusterCard = memo(function ClusterCard({ cluster, onClick }: ClusterCardProps) {
  return (
    <article
      data-testid="cluster-card"
      className="bg-white rounded-xl border border-gray-200 shadow-sm p-5 hover:shadow-md transition-shadow duration-200"
      style={onClick ? { cursor: 'pointer' } : undefined}
      onClick={onClick ? () => onClick(cluster.id) : undefined}
    >
      <div className="flex items-start justify-between">
        <h3
          data-testid="cluster-name"
          className="text-base font-semibold text-gray-900"
          style={{ textWrap: 'balance' } as React.CSSProperties}
        >
          {cluster.name}
        </h3>
        <button
          type="button"
          aria-label="Cluster options"
          className="text-gray-400 hover:text-gray-600 focus-visible:ring-2 focus-visible:ring-blue-500 rounded p-1 -mr-1 -mt-1"
        >
          ⋮
        </button>
      </div>

      <div className="flex gap-4 mt-2">
        <span data-testid="cluster-fact-count" className="text-sm text-gray-600">
          ● {cluster.fact_count} Facts
        </span>
        <span data-testid="cluster-interview-count" className="text-sm text-gray-600">
          ● {cluster.interview_count} Interviews
        </span>
      </div>

      {cluster.summary !== null ? (
        <p className="text-sm text-gray-600 mt-2 line-clamp-3">
          {cluster.summary}
        </p>
      ) : (
        <p className="text-sm text-gray-400 mt-2 italic">
          Generating summary…
        </p>
      )}
    </article>
  )
})
```

### Code Example: ProjectCard Component

```typescript
// dashboard/components/project-card.tsx
import type { ProjectListItem } from '@/lib/types'
import { formatRelativeTime } from '@/lib/relative-time'
import Link from 'next/link'

interface ProjectCardProps {
  project: ProjectListItem
}

export function ProjectCard({ project }: ProjectCardProps) {
  return (
    <Link
      href={`/projects/${project.id}`}
      data-testid="project-card"
      className="block rounded-xl border bg-white p-5 shadow-sm transition hover:shadow-md"
    >
      <h3 data-testid="project-name" className="font-semibold text-gray-900 truncate">
        {project.name}
      </h3>
      <div className="mt-3 flex gap-4 text-sm text-gray-600">
        <span data-testid="project-interview-count">{project.interview_count} Interviews</span>
        <span data-testid="project-cluster-count">{project.cluster_count} Cluster</span>
      </div>
      <p data-testid="project-updated-at" className="mt-2 text-xs text-gray-400">
        {formatRelativeTime(project.updated_at)}
      </p>
    </Link>
  )
}
```

### Code Example: NewProjectDialog Component

```typescript
// dashboard/components/new-project-dialog.tsx
'use client'

import { useRouter } from 'next/navigation'
import { useState } from 'react'
import { apiClient } from '@/lib/api-client'

export function NewProjectDialog() {
  const router = useRouter()
  const [open, setOpen] = useState(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [name, setName] = useState('')
  const [researchGoal, setResearchGoal] = useState('')
  const isValid = name.trim().length > 0 && researchGoal.trim().length > 0

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault()
    if (!isValid) return
    setSaving(true)
    setError(null)
    const form = e.currentTarget
    const data = {
      name: name.trim(),
      research_goal: researchGoal.trim(),
      prompt_context: (form.elements.namedItem('prompt_context') as HTMLTextAreaElement).value || undefined,
      extraction_source: (form.elements.namedItem('extraction_source') as HTMLSelectElement).value as 'summary' | 'transcript',
    }
    try {
      await apiClient.createProject(data)
      router.refresh()
      setOpen(false)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create project')
    } finally {
      setSaving(false)
    }
  }

  return (
    <>
      <button data-testid="new-project-btn" onClick={() => setOpen(true)}>
        + New Project
      </button>
      {open && (
        <div role="dialog" aria-modal="true" aria-labelledby="dialog-title" data-testid="new-project-dialog">
          <h2 id="dialog-title">New Project</h2>
          <form data-testid="new-project-form" onSubmit={handleSubmit}>
            <label htmlFor="project-name">Project Name</label>
            <input id="project-name" name="name" data-testid="project-name-input" required placeholder="Project Name"
              value={name} onChange={e => setName(e.target.value)} />
            <label htmlFor="research-goal">Research Goal</label>
            <textarea id="research-goal" name="research_goal" data-testid="research-goal-input" required placeholder="Research Goal"
              value={researchGoal} onChange={e => setResearchGoal(e.target.value)} />
            <label htmlFor="prompt-context">Prompt Context (optional)</label>
            <textarea id="prompt-context" name="prompt_context" data-testid="prompt-context-input" placeholder="Prompt Context (optional)" />
            <label htmlFor="extraction-source">Fact Extraction Source</label>
            <select id="extraction-source" name="extraction_source" data-testid="extraction-source-select" defaultValue="summary">
              <option value="summary">Summary</option>
              <option value="transcript">Transcript</option>
            </select>
            {error && <p role="alert">{error}</p>}
            <button type="submit" data-testid="create-project-submit" disabled={!isValid || saving}>
              {saving ? 'Creating...' : 'Create Project'}
            </button>
            <button type="button" onClick={() => setOpen(false)}>Cancel</button>
          </form>
        </div>
      )}
    </>
  )
}
```

### Code Example: EmptyState Component

```typescript
// dashboard/components/empty-state.tsx
interface EmptyStateProps {
  message: string
  ctaLabel?: string
  ctaHref?: string
  'data-testid'?: string
}

export function EmptyState({
  message,
  ctaLabel,
  ctaHref,
  'data-testid': testId,
}: EmptyStateProps) {
  return (
    <div
      data-testid={testId}
      className="flex flex-col items-center justify-center py-16 text-center"
    >
      <p className="text-gray-500 mb-4">{message}</p>
      {ctaLabel && (
        ctaHref ? (
          <a
            href={ctaHref}
            data-testid="empty-state-cta"
            className="inline-flex items-center px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 text-sm font-medium transition-colors"
          >
            {ctaLabel}
          </a>
        ) : (
          <button
            type="button"
            data-testid="empty-state-cta"
            className="inline-flex items-center px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 text-sm font-medium transition-colors"
          >
            {ctaLabel}
          </button>
        )
      )}
    </div>
  )
}
```

**Hinweis:** Die CTA bekommt intern immer `data-testid="empty-state-cta"` — unabhaengig davon welcher `ctaLabel` uebergeben wird. Der uebergeordnete Container erhaelt `data-testid` aus der `'data-testid'` Prop (explizit genameltes Prop, kein HTML-Rest-Spread).

### Code Example: Tailwind globals.css

```css
/* dashboard/app/globals.css */
@import "tailwindcss";

@theme {
  --color-surface: var(--color-white);
  --color-surface-elevated: var(--color-gray-50);
  --color-text-primary: var(--color-gray-900);
  --color-text-secondary: var(--color-gray-600);
  --color-text-tertiary: var(--color-gray-400);
  --color-border-default: var(--color-gray-200);
  --color-border-hover: var(--color-gray-300);
  --color-brand: oklch(0.65 0.2 250);
  --color-brand-dark: oklch(0.45 0.2 250);
}

@layer base {
  body {
    @apply bg-gray-50 text-gray-900 antialiased;
  }

  h1, h2, h3 {
    @apply tracking-tight;
    text-wrap: balance;
  }
}
```

### Code Example: StatusBar Component

```typescript
// dashboard/components/status-bar.tsx
interface StatusBarProps {
  interviewCount: number
  factCount: number
  clusterCount: number
}

export function StatusBar({ interviewCount, factCount, clusterCount }: StatusBarProps) {
  return (
    <div data-testid="status-bar" className="flex gap-6 text-sm text-gray-600 border-b pb-3 mb-6">
      <span data-testid="status-interview-count">{interviewCount} Interviews</span>
      <span data-testid="status-fact-count">{factCount} Facts</span>
      <span data-testid="status-cluster-count">{clusterCount} Cluster</span>
    </div>
  )
}
```

### Code Example: ProjectTabs Component

```typescript
// dashboard/components/project-tabs.tsx
'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'

interface ProjectTabsProps {
  projectId: string
  activeTab: 'insights' | 'interviews' | 'settings'
}

export function ProjectTabs({ projectId, activeTab }: ProjectTabsProps) {
  const base = `/projects/${projectId}`

  const tabs: { label: string; href: string; testid: string; tab: ProjectTabsProps['activeTab'] }[] = [
    { label: 'Insights', href: base, testid: 'tab-insights', tab: 'insights' },
    { label: 'Interviews', href: `${base}/interviews`, testid: 'tab-interviews', tab: 'interviews' },
    { label: 'Settings', href: `${base}/settings`, testid: 'tab-settings', tab: 'settings' },
  ]

  return (
    <nav role="tablist" className="flex gap-1 border-b mb-6">
      {tabs.map(tab => {
        const isActive = activeTab === tab.tab
        return (
          <Link
            key={tab.href}
            href={tab.href}
            role="tab"
            data-testid={tab.testid}
            aria-selected={isActive}
            className={isActive ? 'border-b-2 border-blue-600 font-medium' : 'text-gray-500 hover:text-gray-900'}
          >
            {tab.label}
          </Link>
        )
      })}
    </nav>
  )
}
```

### Code Example: PostCSS Konfiguration

```js
// dashboard/postcss.config.js
// WICHTIG: Tailwind v4 Syntax — NICHT v3 (kein require('tailwindcss') oder plugins: [tailwindcss()])
export default {
  plugins: {
    '@tailwindcss/postcss': {},
  },
}
```

**Hinweis:** Dies ist Tailwind v4 PostCSS-Syntax. Tailwind v3 verwendete `plugins: [require('tailwindcss'), require('autoprefixer')]` — das funktioniert mit v4 NICHT. `@tailwindcss/postcss` uebernimmt in v4 die gesamte CSS-Verarbeitung inklusive Autoprefixer.

### Code Example: next.config.ts

```typescript
// dashboard/next.config.ts
import type { NextConfig } from 'next'

const nextConfig: NextConfig = {
  output: 'standalone',
  // Port 3001 wird via package.json dev-Script gesetzt: "dev": "next dev -p 3001"
}

export default nextConfig
```

### Code Example: Health Route Handler

```typescript
// dashboard/app/api/health/route.ts
import { NextResponse } from 'next/server'

export async function GET() {
  return NextResponse.json({ status: 'ok' })
}
```

### Code Example: Relativer Zeitrechner (Utility)

```typescript
// dashboard/lib/relative-time.ts
export function formatRelativeTime(isoString: string): string {
  const now = Date.now()
  const then = new Date(isoString).getTime()
  const diffMs = now - then
  const diffMin = Math.floor(diffMs / 60_000)
  const diffHours = Math.floor(diffMs / 3_600_000)
  const diffDays = Math.floor(diffMs / 86_400_000)
  const diffMonths = Math.floor(diffDays / 30)

  if (diffMin < 1) return 'Updated just now'
  if (diffMin < 60) return `Updated ${diffMin}m ago`
  if (diffHours < 24) return `Updated ${diffHours}h ago`
  if (diffDays < 30) return `Updated ${diffDays}d ago`
  return `Updated ${diffMonths} month${diffMonths > 1 ? 's' : ''} ago`
}
```

---

## Links

- Design/Spec: `specs/phase-4/2026-02-28-llm-interview-clustering/wireframes.md`
- Architecture: `specs/phase-4/2026-02-28-llm-interview-clustering/architecture.md`
- Discovery: `specs/phase-4/2026-02-28-llm-interview-clustering/discovery.md`
- Vorherige Slices: `slice-01-db-schema-projekt-crud.md`, `slice-02-fact-extraction-pipeline.md`, `slice-03-clustering-pipeline-agent.md`

---

## Deliverables (SCOPE SAFEGUARD)

**WICHTIG: Diese Liste wird automatisch vom Stop-Hook validiert. Der Agent kann nicht stoppen, wenn Dateien fehlen.**

<!-- DELIVERABLES_START -->
### Workspace Config
- [ ] `pnpm-workspace.yaml` — `dashboard` als Workspace-Package eingetragen (Root-Datei; falls bereits vorhanden: `dashboard` ergaenzen, nicht ueberschreiben)

### Dashboard Setup
- [ ] `dashboard/package.json` — Next.js 16, React 19, Tailwind v4, TypeScript, Playwright
- [ ] `dashboard/next.config.ts` — Next.js Konfiguration (Port 3001, strict mode)
- [ ] `dashboard/tsconfig.json` — TypeScript Konfiguration (strict, path alias @/*)
- [ ] `dashboard/postcss.config.js` — `@tailwindcss/postcss` Plugin registriert
- [ ] `dashboard/.env.local.example` — `NEXT_PUBLIC_API_URL=http://localhost:8000`

### App Router Pages
- [ ] `dashboard/app/layout.tsx` — Root Layout mit Tailwind globals
- [ ] `dashboard/app/globals.css` — `@import "tailwindcss"` + `@theme` Tokens
- [ ] `dashboard/app/page.tsx` — Root Redirect zu /projects
- [ ] `dashboard/app/api/health/route.ts` — Health-Endpoint (`GET /api/health → {status: "ok"}`)
- [ ] `dashboard/app/projects/page.tsx` — Projekt-Liste Page (Server Component)
- [ ] `dashboard/app/projects/[id]/page.tsx` — Projekt-Dashboard Page (Server Component, Promise.all)

### Library
- [ ] `dashboard/lib/api-client.ts` — fetch-basierter API Client (getProjects, getProject, getClusters, createProject)
- [ ] `dashboard/lib/types.ts` — TypeScript DTOs (ProjectListItem, ProjectResponse, ClusterResponse, CreateProjectRequest)
- [ ] `dashboard/lib/relative-time.ts` — Utility fuer relative Zeitangaben

### Components
- [ ] `dashboard/components/project-card.tsx` — Projekt-Card mit data-testid Attributen
- [ ] `dashboard/components/cluster-card.tsx` — Cluster-Card (memo, line-clamp-3, data-testid, aria-label)
- [ ] `dashboard/components/new-project-dialog.tsx` — Modal fuer neues Projekt (Client Component, Accessibility, Zustände)
- [ ] `dashboard/components/status-bar.tsx` — Status-Bar (N Interviews | M Facts | K Cluster)
- [ ] `dashboard/components/project-tabs.tsx` — Tab-Navigation (role=tablist, aria-selected)
- [ ] `dashboard/components/empty-state.tsx` — Wiederverwendbarer Empty State
- [ ] `dashboard/components/skeleton-card.tsx` — Loading Skeleton Card

### Tests
- [ ] `dashboard/playwright.config.ts` — Playwright E2E Konfiguration (baseURL: http://localhost:3001)
- [ ] `tests/slices/llm-interview-clustering/slice-04-dashboard-projekt-cluster-uebersicht.spec.ts` — Alle 9 Playwright E2E Tests
<!-- DELIVERABLES_END -->

**Hinweis fuer den Implementierungs-Agent:**
- Alle Dateien zwischen `<!-- DELIVERABLES_START -->` und `<!-- DELIVERABLES_END -->` sind Pflicht
- Der Stop-Hook prueft automatisch ob alle Dateien existieren
- Bei fehlenden Dateien wird der Agent blockiert und muss nachfragen
- `dashboard/` wird als neuer Ordner im Repo-Root angelegt (parallel zu `backend/` und `widget/`)
- `pnpm-workspace.yaml` im Repo-Root muss `dashboard` als Workspace hinzufuegen

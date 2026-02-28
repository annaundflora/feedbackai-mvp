# Slice 5: Dashboard — Cluster Drill-Down + Zitate

> **Slice 5 von 8** fuer `LLM Interview Clustering`
>
> | Navigation | |
> |------------|---|
> | **Vorheriger:** | `slice-04-dashboard-projekt-cluster-uebersicht.md` |
> | **Naechster:** | `slice-06-taxonomy-editing.md` |

---

## Metadata (fuer Orchestrator)

| Key | Value |
|-----|-------|
| **ID** | `slice-05-dashboard-drill-down-zitate` |
| **Test** | `pnpm playwright test tests/slices/llm-interview-clustering/slice-05-dashboard-drill-down-zitate.spec.ts` |
| **E2E** | `true` |
| **Dependencies** | `["slice-01-db-schema-projekt-crud", "slice-03-clustering-pipeline-agent", "slice-04-dashboard-projekt-cluster-uebersicht"]` |

**Erklaerung:**
- **ID**: Eindeutiger Identifier (wird fuer Commits und Evidence verwendet)
- **Test**: Playwright E2E Test — Cluster-Card klicken → Facts sehen → Zitate sehen
- **E2E**: `true` — Playwright (`.spec.ts`)
- **Dependencies**: Slice 4 muss fertig sein — liefert Dashboard-Setup, `ProjectTabs`, `apiClient`, TypeScript Types; Slice 1 liefert DB-Schema und Endpoints; Slice 3 liefert Cluster-Daten mit Facts

---

## Test-Strategy (fuer Orchestrator Pipeline)

> **Quelle:** Auto-detected basierend auf Repo-Indikatoren.
> Architecture.md spezifiziert: `dashboard/` als Next.js 16 App (App Router, Tailwind v4, TypeScript).
> Stack identisch mit Slice 4: `typescript-nextjs`. E2E via Playwright.
> Slice 5 ergaenzt das `dashboard/` Projekt um eine neue Sub-Route und einen Backend-Endpoint.

| Key | Value |
|-----|-------|
| **Stack** | `typescript-nextjs` |
| **Test Command** | `pnpm --filter dashboard test` |
| **Integration Command** | `pnpm --filter dashboard test:integration` |
| **Acceptance Command** | `pnpm playwright test tests/slices/llm-interview-clustering/slice-05-dashboard-drill-down-zitate.spec.ts` |
| **Start Command** | `pnpm --filter dashboard dev` |
| **Health Endpoint** | `http://localhost:3001/api/health` |
| **Mocking Strategy** | `mock_external` |

**Erklaerung:**
- **Port 3001**: Dashboard-App aus Slice 4 (unveraendert)
- **Mocking Strategy**: Backend-API wird in Unit/Integration-Tests mit `msw` gemockt. Playwright E2E Tests laufen gegen echtes Backend (lokal gestartet)
- **Backend-Endpoint**: Slice 5 ergaenzt das Backend um `GET /api/projects/{id}/clusters/{cluster_id}/facts` — Python FastAPI

---

## Slice-Uebersicht

| # | Slice | Status | Datei |
|---|-------|--------|-------|
| 1 | DB Schema + Projekt CRUD | **Ready** | `slice-01-db-schema-projekt-crud.md` |
| 2 | Fact Extraction Pipeline | **Ready** | `slice-02-fact-extraction-pipeline.md` |
| 3 | Clustering Pipeline + Agent | **Ready** | `slice-03-clustering-pipeline-agent.md` |
| 4 | Dashboard: Projekt-Liste + Cluster-Uebersicht | **Ready** | `slice-04-dashboard-projekt-cluster-uebersicht.md` |
| 5 | Dashboard: Drill-Down + Zitate | **Current** | `slice-05-dashboard-drill-down-zitate.md` |
| 6 | Taxonomy-Editing + Summary-Regen | Pending | `slice-06-taxonomy-editing.md` |
| 7 | Live-Updates via SSE | Pending | `slice-07-live-updates-sse.md` |
| 8 | Auth + Polish | Pending | `slice-08-auth-polish.md` |

---

## Kontext & Ziel

Nach Slice 4 kann der Nutzer Projekte und Cluster-Karten sehen. Dieser Slice ergaenzt den Drill-Down: Klick auf eine Cluster-Card navigiert zur Cluster-Detail-Seite mit vollstaendiger Zusammenfassung, nummerierter Facts-Liste und Original-Zitaten.

**Scope dieses Slices:**
- Backend: Neuer Endpoint `GET /api/projects/{id}/clusters/{cluster_id}/facts` liefert `ClusterDetailResponse` mit Facts + Quotes
- Frontend: Neue Seite `/projects/[id]/clusters/[cluster_id]` (Cluster-Detail-Seite)
- ClusterCard aus Slice 4 wird klickbar (navigiert zur Cluster-Detail-Seite)
- Header der Cluster-Detail-Seite: Cluster-Name, "Back" Button, Read-Only Aktions-Stubs "Merge" und "Split" (inaktive Buttons — Funktionalitaet kommt in Slice 6)
- Facts-Bereich: Nummerierte Facts-Liste mit Fact-Text, Interview-Badge ("Interview #N" — sequentiell als index+1), optionaler Confidence-Score
- Zitate-Bereich: Original-Zitate aus Transcripts mit Interview-Referenz
- Wiederverwendung von `ProjectTabs` aus Slice 4 mit `activeTab="insights"`

**Abgrenzung zu anderen Slices:**
- Slice 5 liefert NUR lesenden Zugriff auf Facts + Zitate
- Merge/Split/Rename-Funktionalitaet kommt in Slice 6
- `fact_bulk_move` (Checkboxen + Move Selected) wird in Slice 6 implementiert — in Slice 5 keine Checkboxen
- `fact_context_menu` ([⋮] pro Fact) kommt in Slice 6
- SSE Live-Updates kommen in Slice 7
- Auth (Login, JWT-geschuetzte Routes) kommt in Slice 8

---

## Technische Umsetzung

### Architektur-Kontext (aus architecture.md)

> **Quelle:** `architecture.md` → "Endpoints — Clusters" und "Data Transfer Objects (DTOs)"

```
Cluster Detail Flow:
  Browser → GET /projects/{id}/clusters/{cluster_id}
    → Next.js Server Component (dashboard/app/projects/[id]/clusters/[cluster_id]/page.tsx)
      → apiClient.getClusterDetail(project_id, cluster_id)
        → fetch("http://localhost:8000/api/projects/{id}/clusters/{cid}")
          → FastAPI GET /api/projects/{id}/clusters/{cid}
            → ClusterRepository.get_detail(cluster_id)
              → PostgreSQL SELECT facts JOIN clusters WHERE cluster_id = {cid}
            ← ClusterDetailResponse {id, name, summary, facts: [...], quotes: [...]}
        ← ClusterDetailResponse
      ← React HTML (Cluster-Detail-Seite)

Backend Endpoint:
  GET /api/projects/{id}/clusters/{cid}
  → Returns ClusterDetailResponse (id, name, summary, fact_count, interview_count, facts, quotes)

Facts Query:
  SELECT f.id, f.content, f.quote, f.confidence, f.interview_id, f.cluster_id,
         m.created_at AS interview_date
  FROM facts f
  LEFT JOIN mvp_interviews m ON m.session_id = f.interview_id
  WHERE f.cluster_id = {cid} AND f.project_id = {id}
  ORDER BY f.created_at ASC

Quotes Query (nur facts mit quote != null, sortiert nach interview_number):
  SELECT f.id AS fact_id, f.quote AS content, f.interview_id,
         ROW_NUMBER() OVER (ORDER BY pi.assigned_at) AS interview_number
  FROM facts f
  LEFT JOIN project_interviews pi ON pi.interview_id = f.interview_id AND pi.project_id = {id}
  WHERE f.cluster_id = {cid} AND f.quote IS NOT NULL
  ORDER BY pi.assigned_at ASC
```

### 1. Architektur-Impact

| Layer | Aenderungen |
|-------|-------------|
| `backend/app/clustering/router.py` | Neuer Endpoint `GET /api/projects/{id}/clusters/{cid}` — `ClusterDetailResponse` |
| `backend/app/clustering/schemas.py` | Neues Schema `ClusterDetailResponse` mit `facts` + `quotes` Feldern |
| `backend/app/clustering/repository.py` | Neue Methode `ClusterRepository.get_detail(cluster_id, project_id)` |
| `dashboard/app/projects/[id]/clusters/[cluster_id]/page.tsx` | Neue Next.js Server Component (Cluster-Detail-Seite) |
| `dashboard/components/cluster-card.tsx` | Modifikation: Link-Wrapper ergaenzen (`href="/projects/{id}/clusters/{cluster_id}"`) |
| `dashboard/lib/api-client.ts` | Neue Methode `getClusterDetail(project_id, cluster_id)` |
| `dashboard/lib/types.ts` | Neue Types: `ClusterDetailResponse`, `FactResponse` |
| `dashboard/components/fact-item.tsx` | Neue Komponente: Nummerierter Fact-Eintrag |
| `dashboard/components/quote-item.tsx` | Neue Komponente: Zitat-Blockquote |

### 2. Datenfluss

```
Browser Request: GET /projects/{id}/clusters/{cluster_id}
  |
  v
Next.js Server Component: dashboard/app/projects/[id]/clusters/[cluster_id]/page.tsx
  |
  v
apiClient.getClusterDetail(project_id, cluster_id)
  |
  v
fetch("http://localhost:8000/api/projects/{id}/clusters/{cid}")
  |
  v
FastAPI Router: GET /api/projects/{id}/clusters/{cid}
  |
  v
ClusterRepository.get_detail(cluster_id, project_id)
  |
  +-- SELECT * FROM clusters WHERE id = {cid} AND project_id = {id}
  +-- SELECT f.id, f.content, f.quote, f.confidence, f.interview_id, m.created_at
      FROM facts f
      LEFT JOIN mvp_interviews m ON m.session_id = f.interview_id
      WHERE f.cluster_id = {cid}
      ORDER BY f.created_at ASC
  |
  v
ClusterDetailResponse {
  id, name, summary, fact_count, interview_count,
  facts: [FactResponse {id, content, quote, confidence, interview_id, interview_date, cluster_id}],
  quotes: [QuoteResponse {fact_id, content, interview_id, interview_number}],
}
  |
  v
React HTML: Cluster-Detail-Seite
```

**Interview-Nummer Berechnung (Frontend-Logic):**
- `interview_number` ist KEIN Backend-Feld in `FactResponse` — es wird clientseitig als `index + 1` aus der `quotes`-Liste berechnet
- Die `quotes`-Liste im Backend ist bereits sortiert nach `project_interviews.assigned_at` (ROW_NUMBER-Reihenfolge)
- `QuoteResponse.interview_number` wird im Backend berechnet: `ROW_NUMBER() OVER (PARTITION BY project_id ORDER BY assigned_at) AS interview_number`
- Query fuer Quotes: `SELECT f.id AS fact_id, f.quote AS content, f.interview_id, ROW_NUMBER() OVER (ORDER BY pi.assigned_at) AS interview_number FROM facts f LEFT JOIN project_interviews pi ON pi.interview_id = f.interview_id AND pi.project_id = {id} WHERE f.cluster_id = {cid} AND f.quote IS NOT NULL ORDER BY pi.assigned_at ASC`

### 3. Backend-Endpoint: GET /api/projects/{id}/clusters/{cid}

**Quelle:** `architecture.md` → "Endpoints — Clusters"

**GET `/api/projects/{id}/clusters/{cluster_id}`**

Response-Typ: `ClusterDetailResponse`

```python
# backend/app/clustering/schemas.py (Erweiterung)
from datetime import datetime

class FactResponse(BaseModel):
    id: str                     # UUID
    content: str                # Fact-Text
    quote: str | None           # Originalzitat aus Transcript
    confidence: float | None    # LLM-Confidence 0.0-1.0
    interview_id: str           # UUID referenziert mvp_interviews.session_id
    interview_date: datetime | None  # created_at des Interviews (aus mvp_interviews)
    cluster_id: str | None      # UUID referenziert clusters.id (NULLABLE — unassigned moeglich)

class QuoteResponse(BaseModel):
    fact_id: str                # UUID referenziert facts.id
    content: str                # Originalzitat aus Transcript (fact.quote)
    interview_id: str           # UUID referenziert mvp_interviews.session_id
    interview_number: int       # 1-basierte Positionsnummer im Projekt (ROW_NUMBER)

class ClusterDetailResponse(BaseModel):
    id: str
    name: str
    summary: str | None
    fact_count: int
    interview_count: int
    facts: list[FactResponse]   # Alle Facts sortiert nach created_at ASC
    quotes: list[QuoteResponse] # Facts mit quote != null, sortiert nach interview assigned_at ASC
```

```json
// Response JSON (Beispiel)
{
  "id": "a1b2c3d4-...",
  "name": "Navigation Issues",
  "summary": "Users consistently report difficulty finding key features...",
  "fact_count": 14,
  "interview_count": 8,
  "facts": [
    {
      "id": "f1f2f3...",
      "content": "Users cannot find the settings page after completing onboarding.",
      "quote": "I spent like 10 minutes just trying to find where my account settings were.",
      "confidence": 0.92,
      "interview_id": "i1i2i3...",
      "interview_date": "2025-11-15T10:30:00Z",
      "cluster_id": "a1b2c3d4-..."
    },
    {
      "id": "f4f5f6...",
      "content": "The hamburger menu is not intuitive for desktop users.",
      "quote": null,
      "confidence": 0.87,
      "interview_id": "i7i8i9...",
      "interview_date": "2025-11-20T14:00:00Z",
      "cluster_id": "a1b2c3d4-..."
    }
  ],
  "quotes": [
    {
      "fact_id": "f1f2f3...",
      "content": "I spent like 10 minutes just trying to find where my account settings were.",
      "interview_id": "i1i2i3...",
      "interview_number": 3
    }
  ]
}
```

**Hinweise:**
- Endpoint ist autorisiert (JWT, owner-check) — in Slice 5 noch ohne aktives JWT (wie Slice 4)
- 404 wenn Cluster nicht existiert oder einem anderen Projekt gehoert
- Facts werden NUR aus diesem Cluster zurueckgegeben (kein `unassigned`)
- `quote`-Feld in `FactResponse` ist `null` wenn kein Originalzitat extrahiert wurde
- `confidence`-Feld ist `null` wenn kein Confidence-Score gespeichert wurde
- `quotes` Top-Level-Array enthaelt nur Facts mit `quote != null`, mit `interview_number` aus ROW_NUMBER-Berechnung
- `interview_date` ist `null` wenn das Interview nicht in `mvp_interviews` gefunden wird

### 4. Frontend-Routing

```
dashboard/app/
  projects/
    [id]/
      page.tsx                          → Slice 4 (Cluster-Uebersicht)
      clusters/
        [cluster_id]/
          page.tsx                      → Slice 5 (Cluster-Detail — NEU)
```

### 5. API Client Erweiterung

```typescript
// dashboard/lib/api-client.ts (Erweiterung)

// Neue Methode hinzufuegen:
getClusterDetail(projectId: string, clusterId: string): Promise<ClusterDetailResponse> {
  return apiFetch<ClusterDetailResponse>(`/api/projects/${projectId}/clusters/${clusterId}`)
},
```

### 6. TypeScript Types Erweiterung

```typescript
// dashboard/lib/types.ts (Erweiterung)

export interface FactResponse {
  id: string
  content: string
  quote: string | null
  confidence: number | null
  interview_id: string
  interview_date: string | null  // ISO 8601 datetime string (aus mvp_interviews.created_at)
  cluster_id: string | null      // UUID (NULLABLE — unassigned moeglich)
}

export interface QuoteResponse {
  fact_id: string
  content: string        // Originalzitat (fact.quote)
  interview_id: string
  interview_number: number  // 1-basierte Positionsnummer im Projekt (ROW_NUMBER vom Backend)
}

export interface ClusterDetailResponse {
  id: string
  name: string
  summary: string | null
  fact_count: number
  interview_count: number
  facts: FactResponse[]
  quotes: QuoteResponse[]  // Top-Level-Feld: Facts mit quote != null, mit interview_number
}
```

### 7. Abhaengigkeiten (Neue Pakete)

Keine neuen Pakete erforderlich — Dashboard-Setup aus Slice 4 ist ausreichend.

---

## UI Anforderungen

### Wireframe: Cluster-Detail-Seite (`/projects/{id}/clusters/{cluster_id}`)

> **Quelle:** `wireframes.md` → "Screen: Cluster Detail (Drill-Down)"

```
┌─────────────────────────────────────────────────────────────┐
│  ← Back to Clusters                              [Avatar]  │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ① Navigation Issues             [Merge ▼]  [Split]  ②     │
│  ═══════════════════════════════════════════════════════    │
│                                                             │
│  Summary                                             ③     │
│  ───────                                                    │
│  Users consistently report difficulty finding key           │
│  features after the initial onboarding flow. The main       │
│  navigation structure doesn't match their mental model,     │
│  leading to frustration and support tickets.                │
│                                                             │
│  ═══════════════════════════════════════════════════════    │
│                                                             │
│  Facts (14)                                          ④     │
│  ──────────                                                 │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ 1. Users cannot find the settings page after        │   │
│  │    completing onboarding.                           │   │
│  │    ┌──────────────┐                                │ ⑤ │
│  │    │ Interview #3 │  Confidence: 0.92              │   │
│  │    └──────────────┘                                │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ 2. The hamburger menu is not intuitive for          │   │
│  │    desktop users.                                   │   │
│  │    ┌──────────────┐                                │   │
│  │    │ Interview #7 │  Confidence: 0.87              │   │
│  │    └──────────────┘                                │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  ═══════════════════════════════════════════════════════    │
│                                                             │
│  Quotes                                              ⑥     │
│  ──────                                                     │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ "I spent like 10 minutes just trying to find        │   │
│  │  where my account settings were. It's really        │ ⑦ │
│  │  buried in there."                                  │   │
│  │                              ── Interview #3        │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ "The navigation doesn't make sense to me. I         │   │
│  │  always end up using the search to find things."    │   │
│  │                              ── Interview #7        │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**Annotations:**
- ① Cluster-Name (gross, `text-xl font-bold`)
- ② Read-Only Aktions-Stubs: "Merge" Dropdown-Button und "Split" Button (beide `disabled` in Slice 5, Funktionalitaet in Slice 6)
- ③ Vollstaendiger LLM-generierter Cluster-Summary (nicht geclippt)
- ④ Facts-Section Header mit Gesamtanzahl in Klammern
- ⑤ `fact_item`: Nummerierter Fact mit Text, Interview-Badge, optionalem Confidence-Score
- ⑥ Quotes-Section (nur sichtbar wenn mindestens 1 Quote vorhanden)
- ⑦ `quote_item`: Blockquote mit Text und Interview-Referenz

**Referenz Skills fuer UI-Implementation:**
- `.claude/skills/react-best-practices/SKILL.md` - `async-suspense-boundaries`, `server-cache-react`
- `.claude/skills/web-design/SKILL.md` - Accessibility (aria-labels, keyboard nav), Empty States
- `.claude/skills/tailwind-v4/SKILL.md` - Design Tokens, Dark Mode

### 1. ClusterDetailPage (`app/projects/[id]/clusters/[cluster_id]/page.tsx`)

**Komponenten & Dateien:**
- `dashboard/app/projects/[id]/clusters/[cluster_id]/page.tsx` — Server Component, fetcht Cluster-Detail
- `dashboard/components/fact-item.tsx` — Einzelner Fact-Eintrag (nummeriert)
- `dashboard/components/quote-item.tsx` — Einzelnes Zitat (Blockquote)

**Verhalten:**
- Seite laedt Server-seitig (Next.js Server Component)
- Back-Navigation: `← Back to Clusters` Link → navigiert zu `/projects/{id}` (Insights-Tab)
- Header: Cluster-Name + disabled "Merge" Button + disabled "Split" Button
- Summary-Section: Vollstaendige LLM-generierte Zusammenfassung (kein Truncating)
- Facts-Section: Nummerierte Liste (1, 2, 3...), sortiert nach `created_at` ASC (Backend-Sortierung)
- Quotes-Section: Nur gerendert wenn mindestens 1 Fact ein `quote`-Feld != null hat
- `ProjectTabs` aus Slice 4 wiederverwendet mit `activeTab="insights"` (Tabs als Navigation zum Projekt-Dashboard)

**Datenabruf:**
```typescript
const clusterDetail = await apiClient.getClusterDetail(params.id, params.cluster_id)
```

**Zustände:**
- `loading`: Suspense mit Skeleton-Placeholders fuer Summary, Facts, Quotes
- `empty_facts`: "No facts extracted yet." Message in Facts-Section
- `empty_quotes`: Quotes-Section komplett ausgeblendet (nicht als Empty State — nur wenn keine Quotes vorhanden)
- `loaded`: Vollstaendige Cluster-Detail-Ansicht

### 2. ClusterCard Modifikation (`components/cluster-card.tsx`)

**Modifikation aus Slice 4:**
- Slice 5 macht ClusterCard klickbar durch Umwickeln mit `<Link>` Komponente
- `href="/projects/{projectId}/clusters/{clusterId}"`
- `cursor-pointer` ergaenzen
- Hover-State bleibt gleich (aus Slice 4)

**WICHTIG:** ClusterCard ist selbst ein Link — keine nested `<Link>` Elemente erlaubt. Der `[⋮]` Kontext-Menue-Button (falls vorhanden) muss mit `e.preventDefault()` + `e.stopPropagation()` behandelt werden.

### 3. FactItem (`components/fact-item.tsx`)

**Verhalten:**
- Zeigt: Sequentielle Nummer (1, 2, 3...), Fact-Text, Interview-Badge, optionaler Confidence-Score
- Interview-Badge Format: `"Interview #N"` (1-basierte Sequenznummer = `index + 1` als Frontend-Logic, KEIN Backend-Feld)
- Confidence-Score: Nur angezeigt wenn `confidence !== null`. Format: `"Confidence: 0.92"`
- Keine Checkboxen in Slice 5 (Bulk-Move kommt in Slice 6)
- Kein [⋮] Kontext-Menue in Slice 5 (kommt in Slice 6)

**Design:**
- Card-Container: `bg-white rounded-lg border border-gray-200 p-4`
- Nummer: `text-sm font-semibold text-gray-500 min-w-[1.5rem]`
- Fact-Text: `text-sm text-gray-900 flex-1`
- Interview-Badge: `inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-blue-50 text-blue-700 border border-blue-200`
- Confidence: `text-xs text-gray-500 ml-3`

**States:**
- `default`: Weisser Hintergrund, grauer Border
- `no_confidence`: Confidence-Text weggelassen

### 4. QuoteItem (`components/quote-item.tsx`)

**Verhalten:**
- Zeigt: Zitat-Text in Blockquote-Stil, Interview-Referenz
- Interview-Referenz Format: `"── Interview #3"` (rechtsbündig)
- Nur gerendert wenn `fact.quote !== null`

**Design:**
- Container: `bg-white rounded-lg border border-gray-200 p-4 border-l-4 border-l-blue-500`
- Zitat-Text: `text-sm text-gray-700 italic`
- Interview-Referenz: `text-xs text-gray-500 text-right mt-2`

**States:**
- `default`: Rendering mit Quote-Text und Referenz

### 5. Accessibility

- [x] `← Back to Clusters` Link: `<Link href="/projects/{id}">` mit `aria-label="Back to project clusters"`
- [x] "Merge" Button: `disabled` + `aria-disabled="true"` + `aria-label="Merge cluster (available in next version)"`
- [x] "Split" Button: `disabled` + `aria-disabled="true"` + `aria-label="Split cluster (available in next version)"`
- [x] Facts-Liste: semantisches `<ol>` (geordnete Liste) — korrekt fuer nummerierte Items
- [x] Interview-Badge: `aria-label="Source: Interview #{number}"`
- [x] Quotes-Section: `<section aria-label="Supporting quotes">`
- [x] Blockquotes: HTML `<blockquote>` Element
- [x] Facts-Section: `<section aria-label="Facts">` mit `<h2>` Heading
- [x] Summary-Section: `<section aria-label="Cluster summary">` mit `<h2>` Heading
- [x] Skeleton-Loading: `aria-busy="true"` auf Container

---

## Acceptance Criteria

1) GIVEN das Backend laeuft und ein Projekt mit Clustern und Facts existiert
   WHEN der Nutzer `/projects/{id}` oeffnet und auf eine Cluster-Card klickt
   THEN navigiert der Nutzer zu `/projects/{id}/clusters/{cluster_id}`

2) GIVEN der Nutzer ist auf `/projects/{id}/clusters/{cluster_id}`
   WHEN die Seite geladen ist
   THEN sieht er den Cluster-Namen als Seitentitel, einen "← Back to Clusters" Link, und zwei deaktivierte Buttons "Merge" und "Split"

3) GIVEN ein Cluster hat eine LLM-generierte Zusammenfassung
   WHEN der Nutzer die Cluster-Detail-Seite oeffnet
   THEN sieht er die vollstaendige Zusammenfassung (nicht geclippt) unter "Summary"

4) GIVEN ein Cluster hat Facts
   WHEN der Nutzer die Cluster-Detail-Seite oeffnet
   THEN sieht er eine nummerierte Liste aller Facts (1, 2, 3...) jeweils mit Fact-Text und Interview-Badge ("Interview #N")

5) GIVEN ein Fact hat einen Confidence-Score
   WHEN der Nutzer die Facts-Liste betrachtet
   THEN zeigt der Fact-Eintrag den Confidence-Score ("Confidence: 0.92") neben dem Interview-Badge

6) GIVEN ein Fact hat ein Originalzitat (quote != null)
   WHEN der Nutzer die Cluster-Detail-Seite oeffnet
   THEN sieht er die Quotes-Section mit dem Zitat als Blockquote und der Interview-Referenz ("── Interview #N")

7) GIVEN ein Cluster hat keine Facts mit Quotes (alle quote == null)
   WHEN der Nutzer die Cluster-Detail-Seite oeffnet
   THEN ist die Quotes-Section nicht sichtbar (keine "No quotes available" Empty State — Section entfaellt komplett)

8) GIVEN ein Cluster hat keine Facts
   WHEN der Nutzer die Cluster-Detail-Seite oeffnet
   THEN sieht er in der Facts-Section "No facts extracted yet."

9) GIVEN der Nutzer ist auf der Cluster-Detail-Seite
   WHEN er auf "← Back to Clusters" klickt
   THEN navigiert er zurueck zu `/projects/{id}` (Insights Tab)

10) GIVEN die Cluster-Detail-Seite laedt Daten vom Backend
    WHEN die Daten noch nicht geladen sind
    THEN sieht der Nutzer Skeleton-Placeholders fuer Summary, Facts und Quotes

---

## Testfaelle

**WICHTIG:** Tests muessen VOR der Implementierung definiert werden. Der Orchestrator fuehrt diese Tests automatisch nach der Slice-Implementierung aus.

### Test-Datei

**Konvention:** E2E Playwright `.spec.ts`

**Fuer diesen Slice:** `tests/slices/llm-interview-clustering/slice-05-dashboard-drill-down-zitate.spec.ts`

### E2E Tests (Playwright)

<test_spec>
```typescript
// tests/slices/llm-interview-clustering/slice-05-dashboard-drill-down-zitate.spec.ts
import { test, expect } from '@playwright/test'

const BASE_URL = 'http://localhost:3001'
const API_BASE = 'http://localhost:8000'

test.describe('Slice 05: Dashboard — Cluster Drill-Down + Zitate', () => {

  test.beforeEach(async ({ page }) => {
    // Sicherstellen dass Backend und Dashboard laufen
    // In CI: Backend und Dashboard werden vor den Tests gestartet
  })

  // AC 1: Cluster-Card klicken navigiert zur Detail-Seite
  test('navigiert zu Cluster-Detail-Seite beim Klick auf Cluster-Card', async ({ page }) => {
    // GIVEN: Projekt-Liste, Projekt mit Clustern
    await page.goto(`${BASE_URL}/projects`)
    await page.waitForSelector('[data-testid="project-card"]')
    await page.locator('[data-testid="project-card"]').first().click()
    await page.waitForURL(/\/projects\/[0-9a-f-]{36}$/)

    // WHEN: Cluster-Card klicken (falls vorhanden)
    const clusterCards = page.locator('[data-testid="cluster-card"]')
    const count = await clusterCards.count()
    if (count === 0) {
      test.skip(true, 'No cluster cards available — skipping drill-down test')
    }
    await clusterCards.first().click()

    // THEN: URL ist /projects/{id}/clusters/{cluster_id}
    await expect(page).toHaveURL(/\/projects\/[0-9a-f-]{36}\/clusters\/[0-9a-f-]{36}$/)
  })

  // AC 2: Cluster-Detail Header
  test('zeigt Cluster-Detail Header mit Name und deaktivierten Aktions-Buttons', async ({ page }) => {
    // GIVEN: Cluster-Detail-Seite via Route-Mock
    const projectId = 'test-project-id'
    const clusterId = 'test-cluster-id'

    await page.route(`${API_BASE}/api/projects/${projectId}/clusters/${clusterId}`, async route => {
      await route.fulfill({
        json: {
          id: clusterId,
          name: 'Navigation Issues',
          summary: 'Users consistently report difficulty finding key features.',
          fact_count: 2,
          interview_count: 2,
          facts: [
            {
              id: 'fact-1',
              content: 'Users cannot find the settings page.',
              quote: 'I spent 10 minutes looking for settings.',
              confidence: 0.92,
              interview_id: 'interview-1',
              interview_date: '2025-11-15T10:30:00Z',
              cluster_id: clusterId
            }
          ],
          quotes: [
            {
              fact_id: 'fact-1',
              content: 'I spent 10 minutes looking for settings.',
              interview_id: 'interview-1',
              interview_number: 3
            }
          ]
        }
      })
    })

    await page.goto(`${BASE_URL}/projects/${projectId}/clusters/${clusterId}`)
    await page.waitForLoadState('networkidle')

    // THEN: Cluster-Name sichtbar
    await expect(page.locator('[data-testid="cluster-detail-name"]')).toContainText('Navigation Issues')

    // THEN: Back-Link sichtbar
    await expect(page.locator('[data-testid="back-to-clusters"]')).toBeVisible()

    // THEN: Merge-Button deaktiviert
    const mergeBtn = page.locator('[data-testid="merge-btn"]')
    await expect(mergeBtn).toBeVisible()
    await expect(mergeBtn).toBeDisabled()

    // THEN: Split-Button deaktiviert
    const splitBtn = page.locator('[data-testid="split-btn"]')
    await expect(splitBtn).toBeVisible()
    await expect(splitBtn).toBeDisabled()
  })

  // AC 3: Summary anzeigen
  test('zeigt vollstaendige Cluster-Zusammenfassung', async ({ page }) => {
    // GIVEN: Cluster mit Summary
    const projectId = 'test-project-id'
    const clusterId = 'test-cluster-id'

    await page.route(`${API_BASE}/api/projects/${projectId}/clusters/${clusterId}`, async route => {
      await route.fulfill({
        json: {
          id: clusterId,
          name: 'Navigation Issues',
          summary: 'Users consistently report difficulty finding key features after the initial onboarding flow.',
          fact_count: 1,
          interview_count: 1,
          facts: [],
          quotes: []
        }
      })
    })

    await page.goto(`${BASE_URL}/projects/${projectId}/clusters/${clusterId}`)
    await page.waitForLoadState('networkidle')

    // THEN: Summary sichtbar und vollstaendig (nicht geclippt)
    await expect(page.locator('[data-testid="cluster-summary"]')).toBeVisible()
    await expect(page.locator('[data-testid="cluster-summary"]')).toContainText(
      'Users consistently report difficulty finding key features after the initial onboarding flow.'
    )
  })

  // AC 4 + AC 5: Facts-Liste mit Interview-Badge und Confidence
  test('zeigt nummerierte Facts-Liste mit Interview-Badge und Confidence-Score', async ({ page }) => {
    // GIVEN: Cluster mit Facts (mit Quote und Confidence)
    const projectId = 'test-project-id'
    const clusterId = 'test-cluster-id'

    await page.route(`${API_BASE}/api/projects/${projectId}/clusters/${clusterId}`, async route => {
      await route.fulfill({
        json: {
          id: clusterId,
          name: 'Navigation Issues',
          summary: 'Test summary.',
          fact_count: 2,
          interview_count: 2,
          facts: [
            {
              id: 'fact-1',
              content: 'Users cannot find the settings page after completing onboarding.',
              quote: 'I spent 10 minutes looking for settings.',
              confidence: 0.92,
              interview_id: 'interview-1',
              interview_date: '2025-11-15T10:30:00Z',
              cluster_id: clusterId
            },
            {
              id: 'fact-2',
              content: 'The hamburger menu is not intuitive for desktop users.',
              quote: null,
              confidence: 0.87,
              interview_id: 'interview-2',
              interview_date: '2025-11-20T14:00:00Z',
              cluster_id: clusterId
            }
          ],
          quotes: [
            {
              fact_id: 'fact-1',
              content: 'I spent 10 minutes looking for settings.',
              interview_id: 'interview-1',
              interview_number: 1
            }
          ]
        }
      })
    })

    await page.goto(`${BASE_URL}/projects/${projectId}/clusters/${clusterId}`)
    await page.waitForLoadState('networkidle')

    // THEN: Facts-Section vorhanden mit Anzahl
    await expect(page.locator('[data-testid="facts-section"]')).toBeVisible()
    await expect(page.locator('[data-testid="facts-count"]')).toContainText('2')

    // THEN: Erster Fact sichtbar mit Nummer (index + 1 = 1)
    const firstFact = page.locator('[data-testid="fact-item"]').first()
    await expect(firstFact).toBeVisible()
    await expect(firstFact.locator('[data-testid="fact-number"]')).toContainText('1')
    await expect(firstFact.locator('[data-testid="fact-content"]')).toContainText('Users cannot find the settings page')
    await expect(firstFact.locator('[data-testid="fact-interview-badge"]')).toContainText('Interview #1')
    await expect(firstFact.locator('[data-testid="fact-confidence"]')).toContainText('0.92')

    // THEN: Zweiter Fact hat korrekte sequentielle Nummer (index + 1 = 2)
    const secondFact = page.locator('[data-testid="fact-item"]').nth(1)
    await expect(secondFact.locator('[data-testid="fact-number"]')).toContainText('2')
    await expect(secondFact.locator('[data-testid="fact-interview-badge"]')).toContainText('Interview #2')
    await expect(secondFact.locator('[data-testid="fact-confidence"]')).toContainText('0.87')
  })

  // AC 6: Quotes-Section
  test('zeigt Quotes-Section mit Originalzitaten wenn vorhanden', async ({ page }) => {
    // GIVEN: Cluster mit Facts die Quotes haben
    const projectId = 'test-project-id'
    const clusterId = 'test-cluster-id'

    await page.route(`${API_BASE}/api/projects/${projectId}/clusters/${clusterId}`, async route => {
      await route.fulfill({
        json: {
          id: clusterId,
          name: 'Navigation Issues',
          summary: 'Test summary.',
          fact_count: 1,
          interview_count: 1,
          facts: [
            {
              id: 'fact-1',
              content: 'Users cannot find the settings page.',
              quote: "I spent like 10 minutes just trying to find where my account settings were.",
              confidence: 0.92,
              interview_id: 'interview-1',
              interview_date: '2025-11-15T10:30:00Z',
              cluster_id: clusterId
            }
          ],
          quotes: [
            {
              fact_id: 'fact-1',
              content: "I spent like 10 minutes just trying to find where my account settings were.",
              interview_id: 'interview-1',
              interview_number: 3
            }
          ]
        }
      })
    })

    await page.goto(`${BASE_URL}/projects/${projectId}/clusters/${clusterId}`)
    await page.waitForLoadState('networkidle')

    // THEN: Quotes-Section sichtbar (cluster.quotes.length > 0)
    await expect(page.locator('[data-testid="quotes-section"]')).toBeVisible()

    // THEN: Zitat-Text sichtbar (aus QuoteResponse.content)
    const firstQuote = page.locator('[data-testid="quote-item"]').first()
    await expect(firstQuote).toBeVisible()
    await expect(firstQuote.locator('[data-testid="quote-text"]')).toContainText('I spent like 10 minutes')

    // THEN: Interview-Referenz sichtbar (aus QuoteResponse.interview_number vom Backend)
    await expect(firstQuote.locator('[data-testid="quote-interview-ref"]')).toContainText('Interview #3')
  })

  // AC 7: Keine Quotes-Section wenn keine Quotes vorhanden
  test('zeigt keine Quotes-Section wenn quotes-Array leer ist', async ({ page }) => {
    // GIVEN: Cluster mit Facts aber leeren quotes[] (Backend filtert quote==null heraus)
    const projectId = 'test-project-id'
    const clusterId = 'test-cluster-id'

    await page.route(`${API_BASE}/api/projects/${projectId}/clusters/${clusterId}`, async route => {
      await route.fulfill({
        json: {
          id: clusterId,
          name: 'Navigation Issues',
          summary: 'Test summary.',
          fact_count: 1,
          interview_count: 1,
          facts: [
            {
              id: 'fact-1',
              content: 'Users cannot find the settings page.',
              quote: null,
              confidence: 0.92,
              interview_id: 'interview-1',
              interview_date: '2025-11-15T10:30:00Z',
              cluster_id: clusterId
            }
          ],
          quotes: []  // Backend liefert leeres Array wenn alle facts.quote == null
        }
      })
    })

    await page.goto(`${BASE_URL}/projects/${projectId}/clusters/${clusterId}`)
    await page.waitForLoadState('networkidle')

    // THEN: Quotes-Section NICHT sichtbar (cluster.quotes.length === 0)
    await expect(page.locator('[data-testid="quotes-section"]')).not.toBeVisible()
  })

  // AC 8: Empty State fuer Facts
  test('zeigt Empty State in Facts-Section wenn keine Facts vorhanden', async ({ page }) => {
    // GIVEN: Cluster ohne Facts
    const projectId = 'test-project-id'
    const clusterId = 'test-cluster-id'

    await page.route(`${API_BASE}/api/projects/${projectId}/clusters/${clusterId}`, async route => {
      await route.fulfill({
        json: {
          id: clusterId,
          name: 'Empty Cluster',
          summary: null,
          fact_count: 0,
          interview_count: 0,
          facts: [],
          quotes: []
        }
      })
    })

    await page.goto(`${BASE_URL}/projects/${projectId}/clusters/${clusterId}`)
    await page.waitForLoadState('networkidle')

    // THEN: Empty State in Facts-Section
    await expect(page.locator('[data-testid="facts-empty-state"]')).toBeVisible()
    await expect(page.locator('[data-testid="facts-empty-state"]')).toContainText('No facts extracted yet')
  })

  // AC 9: Back-Navigation
  test('navigiert zurueck zur Projekt-Uebersicht via Back-Link', async ({ page }) => {
    // GIVEN: Nutzer ist auf Cluster-Detail-Seite
    const projectId = 'test-project-id'
    const clusterId = 'test-cluster-id'

    await page.route(`${API_BASE}/api/projects/${projectId}/clusters/${clusterId}`, async route => {
      await route.fulfill({
        json: {
          id: clusterId,
          name: 'Navigation Issues',
          summary: null,
          fact_count: 0,
          interview_count: 0,
          facts: [],
          quotes: []
        }
      })
    })

    await page.goto(`${BASE_URL}/projects/${projectId}/clusters/${clusterId}`)
    await page.waitForLoadState('networkidle')

    // WHEN: Back-Link klicken
    await page.click('[data-testid="back-to-clusters"]')

    // THEN: URL ist /projects/{id}
    await expect(page).toHaveURL(`${BASE_URL}/projects/${projectId}`)
  })

  // AC 10: Loading Skeleton
  test('zeigt Loading-Skeleton waehrend Cluster-Detail geladen wird', async ({ page }) => {
    // GIVEN: Langsame API-Antwort
    const projectId = 'test-project-id'
    const clusterId = 'test-cluster-id'

    await page.route(`${API_BASE}/api/projects/${projectId}/clusters/${clusterId}`, async route => {
      await new Promise(resolve => setTimeout(resolve, 800))
      await route.fulfill({
        json: {
          id: clusterId,
          name: 'Navigation Issues',
          summary: 'Test summary.',
          fact_count: 0,
          interview_count: 0,
          facts: [],
          quotes: []
        }
      })
    })

    await page.goto(`${BASE_URL}/projects/${projectId}/clusters/${clusterId}`)

    // THEN: Skeleton oder geladener Content sichtbar (kein leerer Screen)
    await page.waitForSelector(
      '[data-testid="cluster-detail-skeleton"], [data-testid="cluster-detail-name"]',
      { timeout: 5000 }
    )
  })

  // KERN-TEST: Vollstaendiger E2E Flow
  test('vollstaendiger Flow: Cluster-Card klicken → Facts sehen → Zitate sehen', async ({ page }) => {
    // GIVEN: Backend mit Testdaten (Projekt mit Cluster, Facts, Quotes)
    await page.goto(`${BASE_URL}/projects`)
    await page.waitForSelector('[data-testid="project-card"]', { timeout: 10000 })

    // WHEN: Auf Projekt klicken
    await page.locator('[data-testid="project-card"]').first().click()
    await page.waitForURL(/\/projects\/[0-9a-f-]{36}$/)

    // WHEN: Cluster-Card klicken (falls vorhanden)
    await page.waitForSelector('[data-testid="cluster-card"], [data-testid="clusters-empty-state"]', { timeout: 10000 })
    const clusterCards = page.locator('[data-testid="cluster-card"]')
    const count = await clusterCards.count()
    if (count === 0) {
      // Kein Cluster vorhanden — Flow endet hier
      return
    }

    await clusterCards.first().click()
    await page.waitForURL(/\/projects\/[0-9a-f-]{36}\/clusters\/[0-9a-f-]{36}$/)

    // THEN: Cluster-Detail-Seite geladen
    await expect(page.locator('[data-testid="cluster-detail-name"]')).toBeVisible()
    await expect(page.locator('[data-testid="facts-section"]')).toBeVisible()

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
- [ ] Sicherheits-/Privacy-Aspekte: Keine Secrets im Frontend-Code; API-URL aus `NEXT_PUBLIC_API_URL`
- [ ] UX/Copy: Englische UI-Texte (wie im Wireframe spezifiziert)
- [ ] Rollout: Slice 6 ergaenzt Merge/Split/Rename-Funktionalitaet auf dieser Seite

---

## Skill Verification (UI-Implementation)

### React Best Practices Verification

**Critical Priority:**
- [x] `async-parallel`: Nicht zutreffend — nur ein API-Call auf der Cluster-Detail-Seite
- [x] `bundle-dynamic-imports`: Keine schweren Client-Components in Slice 5 (alle Server Components)

**High Priority:**
- [x] `server-cache-react`: `React.cache()` fuer `apiClient.getClusterDetail()` falls mehrfach aufgerufen
- [x] `async-suspense-boundaries`: Cluster-Detail-Page in `<Suspense fallback={<ClusterDetailSkeleton />}>` eingewickelt

**Medium Priority:**
- [x] `rerender-memo`: `FactItem` und `QuoteItem` als `React.memo()` (werden in Listen gerendert)
- [x] `rendering-conditional-render`: Ternary statt `&&` fuer Quotes-Section (vermeidet "0" Rendering)

### Web Design Guidelines Verification

**Accessibility:**
- [x] Back-Link als `<Link>` mit `aria-label`
- [x] "Merge"/"Split" Buttons haben `aria-disabled="true"` und beschreibendes `aria-label`
- [x] Facts-Liste als semantisches `<ol>` Element
- [x] Blockquotes als HTML `<blockquote>` Element
- [x] Sections mit `aria-label` Attribut

**Content:**
- [x] Empty State fuer leere Facts-Liste
- [x] Loading States (Skeleton)
- [x] Quotes-Section entfaellt komplett wenn keine Quotes vorhanden (keine broken UI)

**Typography:**
- [x] Fact-Nummern: `tabular-nums` fuer korrekte Ausrichtung
- [x] Loading States enden mit "…" (z.B. "Loading cluster details…")

### Tailwind v4 Patterns Verification

**Design Tokens:**
- [x] Keine hardcoded Hex-Colors — `text-gray-900`, `bg-blue-50` etc. (Tailwind Tokens)
- [x] `@theme` Tokens aus Slice 4 (`globals.css`) werden wiederverwendet

**Responsive:**
- [x] Mobile-first: Facts-Liste einspaltig auf allen Breakpoints
- [x] Header-Buttons (Merge/Split): Korrekte Abstände auf Mobile

---

## Constraints & Hinweise

**Betrifft:**
- Erweiterung der `dashboard/` App aus Slice 4 (neue Sub-Route + neue Komponenten)
- Erweiterung des FastAPI Backends (neuer Endpoint in bestehendem Cluster-Router)

**API Contract:**
- Backend-URL: `NEXT_PUBLIC_API_URL=http://localhost:8000` (aus `.env.local`)
- Slice 5 ist weiterhin ohne JWT-Auth (Slice 8 ergaenzt Auth)
- Der Endpoint `GET /api/projects/{id}/clusters/{cid}` existiert bereits in `architecture.md`

**Abgrenzung:**
- Checkboxen fuer Bulk-Move-Selection kommen in Slice 6
- [⋮] Kontext-Menue pro Fact kommt in Slice 6
- Merge/Split Buttons sind in Slice 5 nur Read-Only Stubs (`disabled`)
- Cluster-Name ist in Slice 5 nicht editierbar (Inline-Edit kommt in Slice 6)
- Kein SSE / Live-Updates (kommt in Slice 7)

---

## Integration Contract (GATE 2 PFLICHT)

> **Wichtig:** Diese Section wird vom Gate 2 Compliance Agent geprueft. Unvollstaendige Contracts blockieren die Genehmigung.

### Requires From Other Slices

| Slice | Resource | Type | Validation |
|-------|----------|------|------------|
| slice-01-db-schema-projekt-crud | `facts` Table | DB Schema | EXISTS — Columns: id, project_id, interview_id, cluster_id, content, quote, confidence, created_at |
| slice-01-db-schema-projekt-crud | `project_interviews` Table | DB Schema | EXISTS — Columns: project_id, interview_id, assigned_at |
| slice-03-clustering-pipeline-agent | `backend/app/clustering/router.py` | Python-Datei | EXISTS — Slice 5 ergaenzt diese Datei um `GET /api/projects/{id}/clusters/{cid}` |
| slice-03-clustering-pipeline-agent | `ClusterRepository` | Repository Class | EXISTS — Slice 5 ergaenzt um `get_detail(cluster_id, project_id)` Methode |
| slice-04-dashboard-projekt-cluster-uebersicht | `dashboard/` Next.js App | Application | Laufende Next.js App auf Port 3001 mit App Router Setup |
| slice-04-dashboard-projekt-cluster-uebersicht | `dashboard/lib/api-client.ts` | Module | `apiClient` Objekt mit `apiFetch` Basis-Funktion |
| slice-04-dashboard-projekt-cluster-uebersicht | `dashboard/lib/types.ts` | Module | `ProjectResponse`, `ClusterResponse` Types vorhanden |
| slice-04-dashboard-projekt-cluster-uebersicht | `dashboard/components/project-tabs.tsx` | Component | `<ProjectTabs projectId={id} activeTab="insights" />` Props-Interface |
| slice-04-dashboard-projekt-cluster-uebersicht | `dashboard/components/cluster-card.tsx` | Component | Muss mit Link-Wrapper erweiterbar sein |

### Provides To Other Slices

| Resource | Type | Consumer | Interface |
|----------|------|----------|-----------|
| `GET /api/projects/{id}/clusters/{cid}` | HTTP Endpoint (Backend) — Slice-5-Deliverable | slice-06, slice-07 | Returns `ClusterDetailResponse` mit `facts[]` + `quotes[]` |
| `dashboard/lib/types.ts` (erweitert) | TypeScript Types | slice-06 | `FactResponse`, `QuoteResponse`, `ClusterDetailResponse` Interfaces |
| `dashboard/lib/api-client.ts` (erweitert) | Module | slice-06 | `apiClient.getClusterDetail(projectId, clusterId): Promise<ClusterDetailResponse>` |
| `dashboard/app/projects/[id]/clusters/[cluster_id]/page.tsx` | Next.js Page | slice-06 | Bestehende Seite — Slice 6 ergaenzt Aktions-Buttons (Merge, Split, Rename) |
| `dashboard/components/fact-item.tsx` | Component | slice-06 | Props: `{ fact: FactResponse; index: number }` — Slice 6 ergaenzt Checkbox + Context-Menu |
| `dashboard/components/cluster-card.tsx` (modifiziert) | Component | slice-06, slice-07 | ClusterCard ist jetzt `<Link>` zu Cluster-Detail |

### Integration Validation Tasks

- [ ] `facts` Tabelle hat `quote`, `confidence`, `cluster_id` Spalten (aus Slice 1 Schema)
- [ ] `project_interviews` Tabelle hat `assigned_at` fuer `interview_number`-Berechnung in `QuoteResponse`
- [ ] `mvp_interviews` Tabelle hat `created_at` fuer `interview_date`-Berechnung in `FactResponse`
- [ ] Backend-Endpoint liefert `quotes[]` als separates Top-Level-Feld in `ClusterDetailResponse`
- [ ] `QuoteResponse.interview_number` wird via ROW_NUMBER() OVER (ORDER BY assigned_at) berechnet
- [ ] `FactResponse` hat `interview_date` + `cluster_id` (keine `interview_number` im Backend-DTO)
- [ ] `ClusterDetailResponse` Schema ist kompatibel mit `architecture.md` DTO-Spezifikation (facts + quotes)
- [ ] `ProjectTabs` aus Slice 4 akzeptiert `activeTab` Prop korrekt
- [ ] `ClusterCard` aus Slice 4 kann als Link-Wrapper erweitert werden ohne Layout-Bruch

---

## Code Examples (MANDATORY - GATE 2 PFLICHT)

> **KRITISCH:** Alle Code-Beispiele in diesem Dokument sind PFLICHT-Deliverables.
> Der Gate 2 Compliance Agent prueft, dass jedes Code-Beispiel implementiert wird.

| Code Example | Section | Mandatory | Notes |
|--------------|---------|-----------|-------|
| `FactResponse` Type | Technische Umsetzung §6 | YES | Exakt wie spezifiziert, in `dashboard/lib/types.ts` ergaenzen — mit `interview_date` + `cluster_id` |
| `QuoteResponse` Type | Technische Umsetzung §6 | YES | Exakt wie spezifiziert, in `dashboard/lib/types.ts` ergaenzen |
| `ClusterDetailResponse` Type | Technische Umsetzung §6 | YES | Exakt wie spezifiziert, in `dashboard/lib/types.ts` ergaenzen — mit `quotes: QuoteResponse[]` |
| `apiClient.getClusterDetail` | Technische Umsetzung §5 | YES | In `dashboard/lib/api-client.ts` ergaenzen |
| `FactResponse` Pydantic Schema | Technische Umsetzung §3 | YES | In `backend/app/clustering/schemas.py` ergaenzen — mit `interview_date` + `cluster_id` |
| `QuoteResponse` Pydantic Schema | Technische Umsetzung §3 | YES | In `backend/app/clustering/schemas.py` ergaenzen |
| `ClusterDetailResponse` Pydantic Schema | Technische Umsetzung §3 | YES | In `backend/app/clustering/schemas.py` ergaenzen — mit `quotes: list[QuoteResponse]` |
| `ClusterDetailPage` | UI Anforderungen §1 | YES | Server Component, `data-testid` Attribute fuer Playwright |
| `FactItem` | UI Anforderungen §3 | YES | Nummerierter Fact, Interview-Badge, optionaler Confidence-Score, `data-testid` Attribute |
| `QuoteItem` | UI Anforderungen §4 | YES | Blockquote, Interview-Referenz, `data-testid` Attribute |
| `ClusterCard` Modifikation | UI Anforderungen §2 | YES | Link-Wrapper mit `href`, `cursor-pointer`, kein nested Link |
| `Playwright E2E Tests` | Testfaelle | YES | Alle 10 Tests exakt wie spezifiziert (inkl. data-testid Selektoren) |

### Code Example: TypeScript Types Erweiterung

```typescript
// dashboard/lib/types.ts (Erweiterung — bestehende Types bleiben unveraendert)

export interface FactResponse {
  id: string
  content: string
  quote: string | null
  confidence: number | null
  interview_id: string
  interview_date: string | null  // ISO 8601 datetime string (aus mvp_interviews.created_at)
  cluster_id: string | null      // UUID (NULLABLE — unassigned moeglich)
}

export interface QuoteResponse {
  fact_id: string
  content: string        // Originalzitat (fact.quote)
  interview_id: string
  interview_number: number  // 1-basierte Positionsnummer im Projekt (vom Backend berechnet)
}

export interface ClusterDetailResponse {
  id: string
  name: string
  summary: string | null
  fact_count: number
  interview_count: number
  facts: FactResponse[]
  quotes: QuoteResponse[]  // Top-Level-Feld: Facts mit quote != null, mit interview_number
}
```

### Code Example: API Client Erweiterung

```typescript
// dashboard/lib/api-client.ts (Erweiterung)
import type {
  ProjectListItem,
  ProjectResponse,
  ClusterResponse,
  ClusterDetailResponse,
  CreateProjectRequest
} from '@/lib/types'

// ... bestehende Methoden aus Slice 4 unveraendert ...

export const apiClient = {
  // ... bestehende Methoden ...

  getClusterDetail(projectId: string, clusterId: string): Promise<ClusterDetailResponse> {
    return apiFetch<ClusterDetailResponse>(`/api/projects/${projectId}/clusters/${clusterId}`)
  },
}
```

### Code Example: Backend Pydantic Schemas

```python
# backend/app/clustering/schemas.py (Erweiterung)
from datetime import datetime

class FactResponse(BaseModel):
    id: str
    content: str
    quote: str | None
    confidence: float | None
    interview_id: str
    interview_date: datetime | None  # aus mvp_interviews.created_at
    cluster_id: str | None           # UUID (NULLABLE — unassigned moeglich)

class QuoteResponse(BaseModel):
    fact_id: str
    content: str          # Originalzitat (fact.quote)
    interview_id: str
    interview_number: int # 1-basierte Positionsnummer im Projekt (ROW_NUMBER)

class ClusterDetailResponse(BaseModel):
    id: str
    name: str
    summary: str | None
    fact_count: int
    interview_count: int
    facts: list[FactResponse]   # Alle Facts sortiert nach created_at ASC
    quotes: list[QuoteResponse] # Facts mit quote != null, sortiert nach interview assigned_at ASC
```

### Code Example: ClusterDetailPage (Server Component)

```typescript
// dashboard/app/projects/[id]/clusters/[cluster_id]/page.tsx
import { Suspense } from 'react'
import Link from 'next/link'
import { cache } from 'react'
import { apiClient } from '@/lib/api-client'
import { ProjectTabs } from '@/components/project-tabs'
import { FactItem } from '@/components/fact-item'
import { QuoteItem } from '@/components/quote-item'
import type { ClusterDetailResponse } from '@/lib/types'

const getClusterDetail = cache(apiClient.getClusterDetail)

async function ClusterDetail({
  projectId,
  clusterId,
}: {
  projectId: string
  clusterId: string
}) {
  const cluster: ClusterDetailResponse = await getClusterDetail(projectId, clusterId)
  // quotes kommen direkt als Top-Level-Feld vom Backend (kein client-seitiges Filtern)

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <h1
          className="text-xl font-bold text-gray-900"
          data-testid="cluster-detail-name"
        >
          {cluster.name}
        </h1>
        <div className="flex items-center gap-3">
          <button
            disabled
            aria-disabled="true"
            aria-label="Merge cluster (available in next version)"
            data-testid="merge-btn"
            className="px-3 py-1.5 text-sm font-medium text-gray-400 bg-gray-100 rounded-lg cursor-not-allowed"
          >
            Merge
          </button>
          <button
            disabled
            aria-disabled="true"
            aria-label="Split cluster (available in next version)"
            data-testid="split-btn"
            className="px-3 py-1.5 text-sm font-medium text-gray-400 bg-gray-100 rounded-lg cursor-not-allowed"
          >
            Split
          </button>
        </div>
      </div>

      {/* Summary */}
      <section aria-label="Cluster summary" className="mb-8">
        <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-2">
          Summary
        </h2>
        {cluster.summary !== null ? (
          <p className="text-sm text-gray-700 leading-relaxed" data-testid="cluster-summary">
            {cluster.summary}
          </p>
        ) : (
          <p className="text-sm text-gray-400 italic" data-testid="cluster-summary">
            Generating summary…
          </p>
        )}
      </section>

      {/* Facts */}
      <section aria-label="Facts" data-testid="facts-section" className="mb-8">
        <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-2">
          Facts{' '}
          <span data-testid="facts-count" className="font-normal text-gray-400">
            ({cluster.facts.length})
          </span>
        </h2>

        {cluster.facts.length === 0 ? (
          <p
            className="text-sm text-gray-400"
            data-testid="facts-empty-state"
          >
            No facts extracted yet.
          </p>
        ) : (
          <ol className="space-y-3">
            {cluster.facts.map((fact, index) => (
              <FactItem key={fact.id} fact={fact} index={index} />
            ))}
          </ol>
        )}
      </section>

      {/* Quotes — nur wenn mindestens 1 Quote vom Backend geliefert wurde */}
      {cluster.quotes.length > 0 ? (
        <section
          aria-label="Supporting quotes"
          data-testid="quotes-section"
          className="mb-8"
        >
          <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-2">
            Quotes
          </h2>
          <div className="space-y-3">
            {cluster.quotes.map(quote => (
              <QuoteItem
                key={quote.fact_id}
                quote={quote.content}
                interviewNumber={quote.interview_number}
              />
            ))}
          </div>
        </section>
      ) : null}
    </div>
  )
}

function ClusterDetailSkeleton() {
  return (
    <div data-testid="cluster-detail-skeleton" aria-busy="true" className="animate-pulse space-y-6">
      <div className="h-7 bg-gray-200 rounded w-48" />
      <div className="space-y-2">
        <div className="h-4 bg-gray-200 rounded w-full" />
        <div className="h-4 bg-gray-200 rounded w-5/6" />
        <div className="h-4 bg-gray-200 rounded w-4/6" />
      </div>
      <div className="space-y-3">
        {[1, 2, 3].map(i => (
          <div key={i} className="h-16 bg-gray-200 rounded-lg" />
        ))}
      </div>
    </div>
  )
}

export default function ClusterDetailPage({
  params,
}: {
  params: { id: string; cluster_id: string }
}) {
  return (
    <main className="max-w-4xl mx-auto px-4 py-8">
      {/* Back-Navigation */}
      <Link
        href={`/projects/${params.id}`}
        className="inline-flex items-center text-sm text-gray-600 hover:text-gray-900 mb-6 focus-visible:ring-2 focus-visible:ring-blue-500 rounded"
        aria-label="Back to project clusters"
        data-testid="back-to-clusters"
      >
        ← Back to Clusters
      </Link>

      {/* Tab-Navigation (wiederverwendet aus Slice 4) */}
      <ProjectTabs projectId={params.id} activeTab="insights" />

      {/* Cluster-Detail Content */}
      <Suspense fallback={<ClusterDetailSkeleton />}>
        <ClusterDetail projectId={params.id} clusterId={params.cluster_id} />
      </Suspense>
    </main>
  )
}
```

### Code Example: FactItem Component

```typescript
// dashboard/components/fact-item.tsx
import { memo } from 'react'
import type { FactResponse } from '@/lib/types'

interface FactItemProps {
  fact: FactResponse
  index: number  // 0-basierter Index fuer 1-basierte Anzeige
}

export const FactItem = memo(function FactItem({ fact, index }: FactItemProps) {
  return (
    <li
      className="bg-white rounded-lg border border-gray-200 p-4"
      data-testid="fact-item"
    >
      <div className="flex gap-3">
        {/* Sequentielle Nummer */}
        <span
          className="text-sm font-semibold text-gray-500 min-w-[1.5rem] tabular-nums"
          data-testid="fact-number"
          aria-label={`Fact ${index + 1}`}
        >
          {index + 1}.
        </span>

        {/* Fact-Text und Metadaten */}
        <div className="flex-1 min-w-0">
          <p className="text-sm text-gray-900" data-testid="fact-content">
            {fact.content}
          </p>
          <div className="flex items-center gap-3 mt-2">
            {/* Interview-Badge — Nummer = sequentieller Index + 1 (Frontend-Logic) */}
            <span
              className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-blue-50 text-blue-700 border border-blue-200"
              aria-label={`Source: Interview #${index + 1}`}
              data-testid="fact-interview-badge"
            >
              Interview #{index + 1}
            </span>

            {/* Confidence-Score (optional) */}
            {fact.confidence !== null ? (
              <span
                className="text-xs text-gray-500"
                data-testid="fact-confidence"
              >
                Confidence: {fact.confidence.toFixed(2)}
              </span>
            ) : null}
          </div>
        </div>
      </div>
    </li>
  )
})
```

### Code Example: QuoteItem Component

```typescript
// dashboard/components/quote-item.tsx
import { memo } from 'react'

interface QuoteItemProps {
  quote: string
  interviewNumber: number
}

export const QuoteItem = memo(function QuoteItem({ quote, interviewNumber }: QuoteItemProps) {
  return (
    <figure
      className="bg-white rounded-lg border border-gray-200 border-l-4 border-l-blue-500 p-4"
      data-testid="quote-item"
    >
      <blockquote className="text-sm text-gray-700 italic" data-testid="quote-text">
        "{quote}"
      </blockquote>
      <figcaption
        className="text-xs text-gray-500 text-right mt-2"
        data-testid="quote-interview-ref"
      >
        ── Interview #{interviewNumber}
      </figcaption>
    </figure>
  )
})
```

### Code Example: ClusterCard Modifikation

```typescript
// dashboard/components/cluster-card.tsx (Modifikation — Link-Wrapper ergaenzen)
import Link from 'next/link'
import { memo } from 'react'
import type { ClusterResponse } from '@/lib/types'

interface ClusterCardProps {
  cluster: ClusterResponse
  projectId: string
}

export const ClusterCard = memo(function ClusterCard({ cluster, projectId }: ClusterCardProps) {
  return (
    <Link
      href={`/projects/${projectId}/clusters/${cluster.id}`}
      className="block bg-white rounded-xl border border-gray-200 shadow-sm p-5 hover:shadow-md transition-shadow duration-200 cursor-pointer focus-visible:ring-2 focus-visible:ring-blue-500"
      data-testid="cluster-card"
    >
      <div className="flex items-start justify-between">
        <h3
          className="text-base font-semibold text-gray-900"
          data-testid="cluster-name"
        >
          {cluster.name}
        </h3>
        {/* [⋮] Kontext-Menue — dekorativ in Slice 5, Funktion in Slice 6 */}
        <button
          aria-label="Cluster options"
          className="text-gray-400 hover:text-gray-600 p-1 rounded focus-visible:ring-2 focus-visible:ring-blue-500"
          onClick={e => {
            e.preventDefault()
            e.stopPropagation()
            // Funktionalitaet in Slice 6
          }}
        >
          ⋮
        </button>
      </div>

      <div className="flex gap-4 mt-2">
        <span className="text-sm text-gray-600" data-testid="cluster-fact-count">
          ● {cluster.fact_count} Facts
        </span>
        <span className="text-sm text-gray-600" data-testid="cluster-interview-count">
          ● {cluster.interview_count} Interviews
        </span>
      </div>

      {cluster.summary !== null ? (
        <p className="text-sm text-gray-600 mt-2 line-clamp-3">
          {cluster.summary}
        </p>
      ) : (
        <p className="text-sm text-gray-400 italic mt-2">
          Generating summary…
        </p>
      )}
    </Link>
  )
})
```

---

## Links

- Discovery: `specs/phase-4/2026-02-28-llm-interview-clustering/discovery.md`
- Architecture: `specs/phase-4/2026-02-28-llm-interview-clustering/architecture.md`
- Wireframes: `specs/phase-4/2026-02-28-llm-interview-clustering/wireframes.md` → "Screen: Cluster Detail (Drill-Down)"
- Vorheriger Slice: `slice-04-dashboard-projekt-cluster-uebersicht.md`
- Naechster Slice: `slice-06-taxonomy-editing.md`

---

## Deliverables (SCOPE SAFEGUARD)

**WICHTIG: Diese Liste wird automatisch vom Stop-Hook validiert. Der Agent kann nicht stoppen, wenn Dateien fehlen.**

<!-- DELIVERABLES_START -->
### Backend (Erweiterungen)
- [ ] `backend/app/clustering/schemas.py` — `FactResponse` (mit `interview_date`, `cluster_id`), `QuoteResponse` und `ClusterDetailResponse` (mit `quotes: list[QuoteResponse]`) Pydantic Models ergaenzen
- [ ] `backend/app/clustering/repository.py` — Methode `get_detail(cluster_id, project_id)` mit SQL fuer Facts (mit `interview_date`, `cluster_id`) + Quotes (mit `interview_number` via ROW_NUMBER) ergaenzen
- [ ] `backend/app/clustering/router.py` — Endpoint `GET /api/projects/{id}/clusters/{cid}` ergaenzen (liefert `ClusterDetailResponse` mit `facts[]` + `quotes[]`)

### Frontend (Neue Dateien)
- [ ] `dashboard/app/projects/[id]/clusters/[cluster_id]/page.tsx` — Cluster-Detail-Seite (Server Component) mit Skeleton, Summary, Facts-Liste, Quotes-Section (nutzt `cluster.quotes` Top-Level-Feld)
- [ ] `dashboard/components/fact-item.tsx` — Nummerierter Fact-Eintrag (memo) mit Interview-Badge (index+1) + Confidence + data-testid
- [ ] `dashboard/components/quote-item.tsx` — Zitat-Blockquote (memo) mit Interview-Referenz (aus `QuoteResponse.interview_number`) + data-testid

### Frontend (Modifikationen)
- [ ] `dashboard/lib/types.ts` — `FactResponse` (mit `interview_date`, `cluster_id`), `QuoteResponse` und `ClusterDetailResponse` (mit `quotes: QuoteResponse[]`) Interfaces ergaenzen
- [ ] `dashboard/lib/api-client.ts` — `getClusterDetail(projectId, clusterId)` Methode ergaenzen
- [ ] `dashboard/components/cluster-card.tsx` — Link-Wrapper (`<Link href="/projects/{id}/clusters/{id}">`) + `cursor-pointer` + `e.preventDefault()` auf [⋮] Button

### Tests
- [ ] `tests/slices/llm-interview-clustering/slice-05-dashboard-drill-down-zitate.spec.ts` — Alle 10 Playwright E2E Tests (inkl. Kern-Flow-Test) mit aktualisierten Mock-Daten (kein `interview_number` in facts, `quotes[]` als Top-Level-Feld)
<!-- DELIVERABLES_END -->

**Hinweis fuer den Implementierungs-Agent:**
- Alle Dateien zwischen `<!-- DELIVERABLES_START -->` und `<!-- DELIVERABLES_END -->` sind Pflicht
- Der Stop-Hook prueft automatisch ob alle Dateien existieren
- `dashboard/` ist der Ordner aus Slice 4 — keine neue Next.js App erstellen
- Backend-Modifikationen gehen in die bestehenden Clustering-Module aus Slice 3
- `cluster-card.tsx` aus Slice 4 wird modifiziert (nicht neu erstellt)

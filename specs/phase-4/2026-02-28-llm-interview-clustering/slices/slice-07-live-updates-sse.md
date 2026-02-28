# Slice 7: Live-Updates via SSE

> **Slice 7 von 8** fuer `LLM Interview Clustering`
>
> | Navigation | |
> |------------|---|
> | **Vorheriger:** | `slice-06-taxonomy-editing.md` |
> | **Naechster:** | `slice-08-auth-polish.md` |

---

## Metadata (fuer Orchestrator)

| Key | Value |
|-----|-------|
| **ID** | `slice-07-live-updates-sse` |
| **Test** | `pnpm --filter dashboard test tests/slices/llm-interview-clustering/slice-07-live-updates-sse.test.ts` |
| **E2E** | `false` |
| **Dependencies** | `["slice-02-fact-extraction-pipeline", "slice-03-clustering-pipeline-agent", "slice-04-dashboard-projekt-cluster-uebersicht"]` |

**Erklaerung:**
- **ID**: Eindeutiger Identifier (wird fuer Commits und Evidence verwendet)
- **Test**: Vitest Unit Tests fuer Hook und React-Komponenten (kein Playwright E2E — SSE-Updates werden via Mock getestet)
- **E2E**: `false` — Vitest (`.test.ts`)
- **Dependencies**: Slice 2 (`SseEventBus` Singleton + `fact_extracted` Events), Slice 3 (`ClusteringService` publiziert `clustering_started/completed/failed/progress` Events), Slice 4 (Dashboard-App, `StatusBar`, `ProjectTabs`, `ClusterCard`)

---

## Test-Strategy (fuer Orchestrator Pipeline)

> **Quelle:** Auto-detected basierend auf Repo-Indikatoren.
> Architecture.md spezifiziert: `dashboard/` als Next.js 16 App (App Router, Tailwind v4, TypeScript).
> Stack: `typescript-nextjs`. Unit Tests via Vitest (matching Widget-Pattern).

| Key | Value |
|-----|-------|
| **Stack** | `typescript-nextjs` |
| **Test Command** | `pnpm --filter dashboard test tests/slices/llm-interview-clustering/slice-07-live-updates-sse.test.ts` |
| **Integration Command** | `pnpm --filter dashboard test:integration` |
| **Acceptance Command** | `pnpm --filter dashboard test tests/slices/llm-interview-clustering/slice-07-live-updates-sse.test.ts --reporter=verbose` |
| **Start Command** | `pnpm dev` |
| **Health Endpoint** | `http://localhost:3000/api/health` |
| **Mocking Strategy** | `mock_external` |

**Erklaerung:**
- **Mocking Strategy:** `EventSource` wird via `vi.stubGlobal('EventSource', MockEventSource)` gemockt. Backend-SSE-Stream wird NICHT benoetigt. `router.refresh()` wird als `vi.fn()` gemockt.
- **Backend-Tests:** SSE-Route (`backend/app/api/sse_routes.py`) wird separat via pytest getestet (kein neues pytest-File noetig, da nur Route-Registrierung).

---

## Slice-Uebersicht

| # | Slice | Status | Datei |
|---|-------|--------|-------|
| 1 | DB Schema + Projekt CRUD | **Ready** | `slice-01-db-schema-projekt-crud.md` |
| 2 | Fact Extraction Pipeline | **Ready** | `slice-02-fact-extraction-pipeline.md` |
| 3 | Clustering Pipeline + Agent | **Ready** | `slice-03-clustering-pipeline-agent.md` |
| 4 | Dashboard: Projekt-Liste + Cluster-Uebersicht | **Ready** | `slice-04-dashboard-projekt-cluster-uebersicht.md` |
| 5 | Dashboard: Drill-Down + Zitate | **Ready** | `slice-05-dashboard-drill-down.md` |
| 6 | Taxonomy-Editing + Summary-Regen | **Ready** | `slice-06-taxonomy-editing.md` |
| 7 | Live-Updates via SSE | **Ready** | `slice-07-live-updates-sse.md` |
| 8 | Auth + Polish | Pending | `slice-08-auth-polish.md` |

---

## Kontext & Ziel

Das Dashboard zeigt aktuell statische Snapshots — nach einem Interview-Ende aktualisiert sich die Seite nicht automatisch. Dieser Slice verbindet das Backend-SSE-System (bereits in Slice 2 implementiert via `SseEventBus`) mit dem Next.js Dashboard und macht alle Clustering-Pipeline-Events sichtbar.

**Was dieser Slice liefert:**

1. `GET /api/projects/{id}/events` — SSE-Endpoint der den `SseEventBus` Singleton konsumiert (`EventSourceResponse` via `sse_starlette`)
2. `useProjectEvents(projectId)` React Hook — EventSource-Verbindung mit auto-reconnect und cleanup
3. `live_update_badge` — Pulsierender Dot auf `ClusterCard` wenn neuer Fact hinzugefuegt wird (3s Animation)
4. `StatusBar` Live-Counter — Interview/Fact/Cluster-Zaehler aktualisieren sich ohne Reload
5. Progress Indicator — "Analyzing... 47/52 interviews" mit Live-Counter im Insights-Tab (nur sichtbar waehrend Clustering)
6. Dashboard auto-refresh via `router.refresh()` nach `clustering_completed`
7. Toast-Notification bei `clustering_failed`

**Abgrenzung zu anderen Slices:**
- Slice 7 implementiert NUR die SSE-Verbindung und Frontend-Reaktion — keine neue Backend-Geschaeftslogik
- `SseEventBus` kommt aus Slice 2 (unveraendert)
- `ClusteringService` publiziert Events bereits in Slice 3 (unveraendert)
- Dashboard-Grundstruktur (`StatusBar`, `ClusterCard`, `ProjectTabs`) kommt aus Slice 4

---

## Technische Umsetzung

### Architektur-Kontext (aus architecture.md)

> **Quelle:** `architecture.md` → API Design → Endpoints — Pipeline & Events + Architecture Layers → Event Bus + Security → SSE Auth

```
GET /api/projects/{id}/events  →  SSE stream  (Auth: JWT in query param ?token=<jwt>)

Architecture Layer: Event Bus (app/clustering/events.py)
  - In-memory asyncio.Queue pub/sub per project
  - SseEventBus.subscribe(project_id) → Queue
  - SseEventBus.unsubscribe(project_id, queue) → cleanup
  - SseEventBus.publish(project_id, event_type, data) → sendet an alle Subscriber

Security: JWT in query param da EventSource keine Headers unterstuetzt
  ?token=<jwt>  →  verifiziert via get_current_user_from_token dependency

SSE Event Types (aus architecture.md):
  fact_extracted      → {interview_id, fact_count}
  clustering_started  → {mode: "incremental"|"full"}
  clustering_updated  → {clusters: [{id, name, fact_count}]}
  clustering_completed→ {cluster_count, fact_count}
  clustering_failed   → {error, unassigned_count}
  suggestion          → {type: "merge"|"split", source_cluster_id, ...}
  summary_updated     → {cluster_id}

Zusaetzlich fuer Slice 7 (Progress):
  clustering_progress → {interview_id, step: "extracting"|"assigning"|"validating"|"summarizing", completed, total}
```

### 1. Architektur-Impact

| Layer | Aenderungen |
|-------|-------------|
| `backend/app/api/sse_routes.py` | **Neu:** `GET /api/projects/{id}/events` — EventSourceResponse via `sse_starlette` |
| `backend/app/clustering/events.py` | **Unveraendert** (aus Slice 2): `SseEventBus` Singleton |
| `backend/app/clustering/service.py` | **Erweitert:** `clustering_progress` Events in Pipeline-Schritten publizieren |
| `backend/app/main.py` | **Erweitert:** `sse_router` registrieren (falls noch nicht von Slice 2 erfolgt) |
| `dashboard/hooks/useProjectEvents.ts` | **Neu:** React Hook fuer EventSource-Verbindung |
| `dashboard/components/ClusterCard.tsx` | **Erweitert:** `live_update_badge` (pulsierender Dot, 3s Animation) |
| `dashboard/components/StatusBar.tsx` | **Erweitert:** Live-Counter Updates via Hook |
| `dashboard/components/ProgressIndicator.tsx` | **Neu:** "Analyzing... N/M interviews" Progress-Anzeige |
| `dashboard/app/projects/[id]/page.tsx` | **Erweitert:** `useProjectEvents` einbinden, `router.refresh()` bei `clustering_completed`, Toast bei `clustering_failed` |

### 2. Datenfluss

```
Backend:
ClusteringService.process_interview()
  → SseEventBus.publish(project_id, "fact_extracted", {interview_id, fact_count})
  → SseEventBus.publish(project_id, "clustering_started", {mode: "incremental"})
  → SseEventBus.publish(project_id, "clustering_progress", {step, completed, total})  [NEU]
  → SseEventBus.publish(project_id, "clustering_completed", {cluster_count, fact_count})
  → (or) SseEventBus.publish(project_id, "clustering_failed", {error, unassigned_count})

SSE Endpoint (sse_routes.py):
GET /api/projects/{id}/events?token=<jwt>
  → JWT validieren (get_current_user_from_token)
  → Owner-Check: project.user_id == current_user.id
  → queue = event_bus.subscribe(project_id)
  → EventSourceResponse(generator)
    → generator: yield queue.get() as SSE event
    → cleanup: event_bus.unsubscribe(project_id, queue)

Frontend:
useProjectEvents(projectId)
  → new EventSource(`/api/projects/${projectId}/events?token=${token}`)
  → onmessage: parse JSON → dispatch to callbacks
  → onerror: reconnect mit exponential backoff (1s, 2s, 4s, max 30s)
  → cleanup: eventSource.close() in useEffect return

Dashboard Page (projects/[id]/page.tsx):
  useProjectEvents(projectId, {
    onFactExtracted: (data) → ClusterCard animiert live_update_badge
    onClusteringStarted: (data) → ProgressIndicator einblenden
    onClusteringProgress: (data) → ProgressIndicator Counter aktualisieren
    onClusteringCompleted: (data) → router.refresh() + ProgressIndicator ausblenden
    onClusteringFailed: (data) → toast.error(...) + ProgressIndicator ausblenden
    onSummaryUpdated: (data) → router.refresh()
  })
```

### 3. SSE-Endpoint (Backend)

```python
# backend/app/api/sse_routes.py

from fastapi import APIRouter, Depends, HTTPException, Query
from sse_starlette.sse import EventSourceResponse
import asyncio
import json

from app.clustering.events import SseEventBus
from app.api.dependencies import get_sse_event_bus, get_project_service
from app.auth.middleware import get_current_user_from_token

router = APIRouter()


@router.get("/api/projects/{project_id}/events")
async def project_events(
    project_id: str,
    token: str = Query(..., description="JWT token (EventSource cannot send headers)"),
    event_bus: SseEventBus = Depends(get_sse_event_bus),
    project_service = Depends(get_project_service),
    current_user = Depends(get_current_user_from_token),
) -> EventSourceResponse:
    """SSE-Stream fuer Live-Updates eines Projekts.

    Auth: JWT via ?token= Query-Parameter (EventSource supports no headers).
    Owner-Check: Project muss dem aktuellen User gehoeren.

    Events (gemaess architecture.md SSE Event Types):
    - fact_extracted: {interview_id, fact_count}
    - clustering_started: {mode: "incremental"|"full"}
    - clustering_progress: {interview_id, step, completed, total}
    - clustering_updated: {clusters: [{id, name, fact_count}]}
    - clustering_completed: {cluster_count, fact_count}
    - clustering_failed: {error, unassigned_count}
    - suggestion: {type, source_cluster_id, ...}
    - summary_updated: {cluster_id}
    """
    # Owner-Check
    project = await project_service.get_by_id(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    if str(project["user_id"]) != str(current_user["id"]):
        raise HTTPException(status_code=403, detail="Access denied")

    queue = event_bus.subscribe(project_id)

    async def event_generator():
        try:
            # Heartbeat alle 30s damit Proxy/Load-Balancer Verbindung offen haelt
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=30.0)
                    yield {
                        "event": event["type"],
                        "data": json.dumps({k: v for k, v in event.items() if k != "type"}),
                    }
                except asyncio.TimeoutError:
                    # Heartbeat — leeres Comment-Event (SSE spec: lines starting with ":")
                    yield {"comment": "heartbeat"}
        finally:
            event_bus.unsubscribe(project_id, queue)

    return EventSourceResponse(event_generator())
```

### 4. ClusteringService — clustering_progress Events

> **Quelle:** `architecture.md` → Server Logic → Business Logic Flows → Incremental Clustering

```python
# backend/app/clustering/service.py — Erweiterung fuer clustering_progress

# In process_interview() nach jedem LangGraph-Node-Abschluss:
await self._event_bus.publish(
    project_id=project_id,
    event_type="clustering_progress",
    data={
        "interview_id": interview_id,
        "step": "extracting",   # "assigning" | "validating" | "summarizing"
        "completed": completed_interviews,
        "total": total_interviews,
    },
)
```

**Steps:**
| Step | Zeitpunkt | completed/total Bedeutung |
|------|-----------|--------------------------|
| `"extracting"` | Nach `fact_extracted` Event | Anzahl verarbeiteter Interviews / Gesamt |
| `"assigning"` | Waehrend `assign_facts` Node | Anzahl zugewiesener Facts / Gesamt |
| `"validating"` | Waehrend `validate_quality` Node | Aktuelle Iteration / max_iterations (3) |
| `"summarizing"` | Waehrend `generate_summaries` Node | Anzahl generierter Summaries / Gesamt-Cluster |

### 5. useProjectEvents Hook

```typescript
// dashboard/hooks/useProjectEvents.ts
"use client";

import { useEffect, useRef, useCallback } from "react";

export type SseEventType =
  | "fact_extracted"
  | "clustering_started"
  | "clustering_progress"
  // clustering_updated intentionally omitted in Slice 7:
  // router.refresh() after clustering_completed fetches fresh cluster data server-side.
  // clustering_updated (granular card updates) is deferred to post-MVP optimization.
  | "clustering_completed"
  | "clustering_failed"
  | "summary_updated";

export interface FactExtractedData {
  interview_id: string;
  fact_count: number;
}

export interface ClusteringStartedData {
  mode: "incremental" | "full";
}

export interface ClusteringProgressData {
  interview_id: string;
  step: "extracting" | "assigning" | "validating" | "summarizing";
  completed: number;
  total: number;
}

export interface ClusteringCompletedData {
  cluster_count: number;
  fact_count: number;
}

export interface ClusteringFailedData {
  error: string;
  unassigned_count: number;
}

export interface SummaryUpdatedData {
  cluster_id: string;
}

export interface UseProjectEventsCallbacks {
  onFactExtracted?: (data: FactExtractedData) => void;
  onClusteringStarted?: (data: ClusteringStartedData) => void;
  onClusteringProgress?: (data: ClusteringProgressData) => void;
  onClusteringCompleted?: (data: ClusteringCompletedData) => void;
  onClusteringFailed?: (data: ClusteringFailedData) => void;
  onSummaryUpdated?: (data: SummaryUpdatedData) => void;
}

export function useProjectEvents(
  projectId: string,
  token: string,
  callbacks: UseProjectEventsCallbacks,
): void {
  // Store callbacks in ref to avoid re-connecting on every render (rerender-use-ref-transient-values)
  const callbacksRef = useRef(callbacks);
  callbacksRef.current = callbacks;

  const reconnectDelayRef = useRef(1000);
  const esRef = useRef<EventSource | null>(null);

  const connect = useCallback(() => {
    if (esRef.current) {
      esRef.current.close();
    }

    const url = `/api/projects/${projectId}/events?token=${encodeURIComponent(token)}`;
    const es = new EventSource(url);
    esRef.current = es;

    const handleEvent = (eventType: SseEventType) => (e: MessageEvent) => {
      try {
        const data = JSON.parse(e.data);
        const cb = callbacksRef.current;
        switch (eventType) {
          case "fact_extracted":
            cb.onFactExtracted?.(data as FactExtractedData);
            break;
          case "clustering_started":
            cb.onClusteringStarted?.(data as ClusteringStartedData);
            break;
          case "clustering_progress":
            cb.onClusteringProgress?.(data as ClusteringProgressData);
            break;
          case "clustering_completed":
            cb.onClusteringCompleted?.(data as ClusteringCompletedData);
            break;
          case "clustering_failed":
            cb.onClusteringFailed?.(data as ClusteringFailedData);
            break;
          case "summary_updated":
            cb.onSummaryUpdated?.(data as SummaryUpdatedData);
            break;
        }
        // Reset reconnect delay on successful message
        reconnectDelayRef.current = 1000;
      } catch {
        // Malformed JSON — ignore, keep connection open
      }
    };

    const eventTypes: SseEventType[] = [
      "fact_extracted",
      "clustering_started",
      "clustering_progress",
      "clustering_completed",
      "clustering_failed",
      "summary_updated",
    ];
    eventTypes.forEach((type) => {
      es.addEventListener(type, handleEvent(type));
    });

    es.onerror = () => {
      es.close();
      esRef.current = null;
      // Exponential backoff: 1s, 2s, 4s, ... max 30s
      const delay = Math.min(reconnectDelayRef.current, 30_000);
      reconnectDelayRef.current = Math.min(delay * 2, 30_000);
      setTimeout(connect, delay);
    };
  }, [projectId, token]);

  useEffect(() => {
    connect();
    return () => {
      esRef.current?.close();
      esRef.current = null;
    };
  }, [connect]);
}
```

### 6. live_update_badge — ClusterCard Erweiterung

> **Quelle:** `wireframes.md` → Screen: Project Dashboard (Insights Tab) → Annotation ⑧ `live_update_badge`

```typescript
// dashboard/components/ClusterCard.tsx — Erweiterung

"use client";

import { useState, useEffect, memo } from "react";
import type { ClusterResponse } from "@/types/api";

interface ClusterCardProps {
  cluster: ClusterResponse;
  hasLiveUpdate?: boolean;   // Gesetzt wenn fact_extracted fuer diesen Cluster
  onClick: () => void;
}

// live_update_badge: pulsierender Dot (3s Animation, dann ausblenden)
// Wireframe Annotation ⑧: "Pulse animation on cluster card when new fact is added (not shown at rest)"
export const ClusterCard = memo(function ClusterCard({
  cluster,
  hasLiveUpdate = false,
  onClick,
}: ClusterCardProps) {
  const [showBadge, setShowBadge] = useState(false);

  useEffect(() => {
    if (hasLiveUpdate) {
      setShowBadge(true);
      const timer = setTimeout(() => setShowBadge(false), 3000);
      return () => clearTimeout(timer);
    }
  }, [hasLiveUpdate]);

  return (
    <div
      role="button"
      tabIndex={0}
      aria-label={`Cluster: ${cluster.name}, ${cluster.fact_count} facts`}
      data-testid="cluster-card"
      onClick={onClick}
      onKeyDown={(e) => e.key === "Enter" && onClick()}
      className="
        relative p-4 bg-white dark:bg-gray-900
        rounded-xl border border-gray-200 dark:border-gray-700
        shadow-sm hover:shadow-md hover:-translate-y-0.5
        transition-all duration-200 cursor-pointer
        focus-visible:ring-2 focus-visible:ring-blue-500
        touch-action-manipulation
      "
    >
      {/* live_update_badge: pulsierender Dot — nur sichtbar waehrend 3s Animation */}
      {showBadge && (
        <span
          aria-label="New fact added"
          aria-live="polite"
          data-testid="live-update-badge"
          className="
            absolute top-3 right-3
            w-2.5 h-2.5 rounded-full bg-blue-500
            animate-pulse
          "
        />
      )}

      <div className="flex items-start justify-between gap-2 mb-2">
        <h3
          data-testid="cluster-card-name"
          className="font-semibold text-gray-900 dark:text-gray-100 text-wrap-balance"
        >
          {cluster.name}
        </h3>
      </div>

      <div className="flex gap-4 text-sm text-gray-600 dark:text-gray-400 mb-3 tabular-nums">
        <span data-testid="cluster-fact-count">{cluster.fact_count} Facts</span>
        <span>{cluster.interview_count} Interviews</span>
      </div>

      {cluster.summary && (
        <p className="text-sm text-gray-600 dark:text-gray-400 line-clamp-3">
          {cluster.summary}
        </p>
      )}
    </div>
  );
});
```

### 7. ProgressIndicator

> **Quelle:** `wireframes.md` → Screen: Project Dashboard (Insights Tab) → Annotation ④ `progress_bar`

```typescript
// dashboard/components/ProgressIndicator.tsx

interface ProgressIndicatorProps {
  step: "extracting" | "assigning" | "validating" | "summarizing";
  completed: number;
  total: number;
}

const STEP_LABELS: Record<ProgressIndicatorProps["step"], string> = {
  extracting: "Extracting facts",
  assigning: "Assigning to clusters",
  validating: "Validating quality",
  summarizing: "Generating summaries",
};

export function ProgressIndicator({ step, completed, total }: ProgressIndicatorProps) {
  const pct = total > 0 ? Math.round((completed / total) * 100) : 0;
  const label = `${STEP_LABELS[step]}... ${completed}/${total}`;

  return (
    <div
      role="status"
      aria-live="polite"
      aria-label={label}
      data-testid="progress-indicator"
      className="mb-4"
    >
      <div className="flex justify-between text-sm text-gray-600 dark:text-gray-400 mb-1">
        <span data-testid="progress-label">{label}</span>
        <span data-testid="progress-pct" className="tabular-nums">{pct}%</span>
      </div>
      <div
        role="progressbar"
        aria-valuenow={pct}
        aria-valuemin={0}
        aria-valuemax={100}
        className="h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden"
      >
        <div
          data-testid="progress-bar-fill"
          className="h-full bg-blue-500 rounded-full transition-[width] duration-300 ease-out"
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}
```

### 8. StatusBar — Live-Counter Updates

```typescript
// dashboard/components/StatusBar.tsx — Erweiterung

interface StatusBarProps {
  interviewCount: number;
  factCount: number;
  clusterCount: number;
}

// Live-Updates: Counts werden als Props von der Page uebergeben.
// Page haelt lokalen State (optimistic) und aktualisiert via useProjectEvents.
export function StatusBar({ interviewCount, factCount, clusterCount }: StatusBarProps) {
  return (
    <div
      data-testid="status-bar"
      className="flex gap-6 text-sm text-gray-600 dark:text-gray-400 py-3 border-b border-gray-200 dark:border-gray-700 tabular-nums"
    >
      <span data-testid="interview-count">
        <strong className="text-gray-900 dark:text-gray-100">{interviewCount}</strong> Interviews
      </span>
      <span data-testid="fact-count">
        <strong className="text-gray-900 dark:text-gray-100">{factCount}</strong> Facts
      </span>
      <span data-testid="cluster-count">
        <strong className="text-gray-900 dark:text-gray-100">{clusterCount}</strong> Clusters
      </span>
    </div>
  );
}
```

### 9. Dashboard Page — SSE Integration

```typescript
// dashboard/app/projects/[id]/page.tsx — Erweiterung (Client Component Teil)

"use client";

import { useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { useProjectEvents } from "@/hooks/useProjectEvents";
import { ProgressIndicator } from "@/components/ProgressIndicator";
import { toast } from "@/components/Toast";
import type { ClusteringProgressData } from "@/hooks/useProjectEvents";

interface ProjectPageClientProps {
  projectId: string;
  token: string;
  initialInterviewCount: number;
  initialFactCount: number;
  initialClusterCount: number;
  clusters: Array<{ id: string; name: string; fact_count: number; interview_count: number; summary: string | null }>;
}

export function ProjectPageClient({
  projectId,
  token,
  initialInterviewCount,
  initialFactCount,
  initialClusterCount,
  clusters,
}: ProjectPageClientProps) {
  const router = useRouter();

  const [progress, setProgress] = useState<ClusteringProgressData | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [liveUpdateClusterIds, setLiveUpdateClusterIds] = useState<Set<string>>(new Set());

  const [factCount, setFactCount] = useState(initialFactCount);
  const [clusterCount, setClusterCount] = useState(initialClusterCount);

  const handleFactExtracted = useCallback(
    (data: { interview_id: string; fact_count: number }) => {
      // Optimistic counter update — exakte Counts kommen via router.refresh()
      setFactCount((prev) => prev + data.fact_count);
      // Trigger live_update_badge on all cluster cards (fact not yet assigned to cluster)
      setLiveUpdateClusterIds(new Set(['*']));
      setTimeout(() => setLiveUpdateClusterIds(new Set()), 3000);
    },
    [],
  );

  const handleClusteringStarted = useCallback(() => {
    setIsProcessing(true);
  }, []);

  const handleClusteringProgress = useCallback((data: ClusteringProgressData) => {
    setProgress(data);
  }, []);

  const handleClusteringCompleted = useCallback(
    (data: { cluster_count: number; fact_count: number }) => {
      setIsProcessing(false);
      setProgress(null);
      setClusterCount(data.cluster_count);
      setFactCount(data.fact_count);
      // Server-side refresh fuer exakte Daten (Next.js App Router)
      router.refresh();
    },
    [router],
  );

  const handleClusteringFailed = useCallback(
    (data: { error: string; unassigned_count: number }) => {
      setIsProcessing(false);
      setProgress(null);
      toast.error(
        `Clustering failed: ${data.unassigned_count} facts could not be assigned. Check the Insights tab.`,
      );
    },
    [],
  );

  const handleSummaryUpdated = useCallback(() => {
    router.refresh();
  }, [router]);

  useProjectEvents(projectId, token, {
    onFactExtracted: handleFactExtracted,
    onClusteringStarted: handleClusteringStarted,
    onClusteringProgress: handleClusteringProgress,
    onClusteringCompleted: handleClusteringCompleted,
    onClusteringFailed: handleClusteringFailed,
    onSummaryUpdated: handleSummaryUpdated,
  });

  // '*' wildcard = pulse all cards (fact not yet assigned to a specific cluster)
  const anyLiveUpdate = liveUpdateClusterIds.has('*');

  return (
    <>
      {isProcessing && progress && (
        <ProgressIndicator
          step={progress.step}
          completed={progress.completed}
          total={progress.total}
        />
      )}
      {clusters.map((cluster) => (
        <ClusterCard
          key={cluster.id}
          cluster={cluster}
          hasLiveUpdate={anyLiveUpdate || liveUpdateClusterIds.has(cluster.id)}
        />
      ))}
    </>
  );
}
```

### N. API-Contracts

**GET `/api/projects/{project_id}/events`**

**Response:** `EventSourceResponse` (SSE stream, `text/event-stream`)

```
event: fact_extracted
data: {"interview_id": "uuid", "fact_count": 5}

event: clustering_started
data: {"mode": "incremental"}

event: clustering_progress
data: {"interview_id": "uuid", "step": "assigning", "completed": 3, "total": 10}

event: clustering_completed
data: {"cluster_count": 5, "fact_count": 47}

event: clustering_failed
data: {"error": "LLM timeout after 3 retries", "unassigned_count": 3}

event: summary_updated
data: {"cluster_id": "uuid"}

: heartbeat
```

**Auth:** `?token=<jwt>` Query-Parameter (EventSource unterstuetzt keine HTTP-Headers)

**Status Codes:**
- `200 OK` — SSE stream gestartet
- `401 Unauthorized` — JWT invalid oder fehlend
- `403 Forbidden` — Projekt gehoert nicht dem aktuellen User
- `404 Not Found` — Projekt nicht gefunden

### N+1. Abhaengigkeiten

- Bestehend: `sse-starlette==3.2.0` (bereits in requirements.txt)
- Bestehend: `SseEventBus` (aus Slice 2: `backend/app/clustering/events.py`)
- Bestehend: Next.js 16.1.6 (aus Slice 4)
- Bestehend: Tailwind CSS v4 (aus Slice 4)
- Neu: Kein neues Package erforderlich — `EventSource` ist native Browser-API

### N+2. Wiederverwendete Code-Bausteine

| Funktion/Klasse | Datei | Rueckgabetyp | Wichtige Hinweise |
|-----------------|-------|-------------|-------------------|
| `SseEventBus.subscribe()` | `backend/app/clustering/events.py` | `asyncio.Queue` | Singleton via `get_sse_event_bus()` DI |
| `SseEventBus.unsubscribe()` | `backend/app/clustering/events.py` | `None` | MUSS im `finally`-Block aufgerufen werden |
| `get_current_user_from_token()` | `backend/app/auth/middleware.py` | `dict` (User) | Nimmt `token` als Parameter (nicht `Authorization`-Header) |
| `router.refresh()` | Next.js App Router | `void` | Revalidiert Server-Component-Daten ohne Full-Reload |

---

## Integrations-Checkliste

### 1. State-Integration
- [ ] `liveUpdateClusterIds` State korrekt in Page-Client-Component definiert
- [ ] `progress` State Reset nach `clustering_completed` und `clustering_failed`
- [ ] Keine Race Conditions: `router.refresh()` nur einmal pro Event (nicht bei jedem Progress-Event)

### 2. SSE-Integration
- [ ] SSE-Verbindung wird bei Komponenten-Unmount via `eventSource.close()` bereinigt
- [ ] Reconnect-Logik mit exponential backoff implementiert
- [ ] Heartbeat-Events (`:heartbeat`) werden ignoriert (kein Event-Handler)
- [ ] JWT-Token wird als Query-Parameter uebergeben (NICHT im Authorization-Header)

### 3. LLM-Integration
- [ ] Keine LLM-Calls in Slice 7 — nur SSE-Weiterleitung bestehender Events

### 4. Datenbank-Integration
- [ ] Keine DB-Aenderungen in Slice 7

### 5. Utility-Funktionen
- [ ] `useCallback` fuer alle Event-Handler (vermeidet Hook-Re-Registrierung)
- [ ] `useRef` fuer `callbacks` Objekt im Hook (vermeidet EventSource-Reconnect bei Render)

### 6. Feature-Aktivierung
- [ ] `sse_router` in `backend/app/main.py` registriert
- [ ] `useProjectEvents` wird in `dashboard/app/projects/[id]/page.tsx` aufgerufen
- [ ] `live_update_badge` wird durch `hasLiveUpdate` Prop gesteuert (von Page-Client weitergegeben)

### 7. Datenfluss-Vollstaendigkeit
- [ ] Optimistic UI: `factCount` und `clusterCount` werden bei Events sofort aktualisiert
- [ ] Exakte Daten: `router.refresh()` nach `clustering_completed` holt Server-seitige Counts
- [ ] Error State: `clustering_failed` zeigt Toast und blendet Progress aus

---

## UI Anforderungen

### Wireframe (aus wireframes.md)

> **Quelle:** `wireframes.md` → Screen: Project Dashboard (Insights Tab) → Annotations ③ ④ ⑧ ⑪

```
┌─────────────────────────────────────────────────────────────┐
│  Onboarding UX Research                                     │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ [Insights]  │  Interviews  │  Settings               │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                             │
│  12 Interviews  │  47 Facts  │  5 Clusters       ③         │
│  ─────────────────────────────────────                     │
│                                                             │
│  ████████████████████░░░░░  Assigning... 47/52 facts  ④    │
│                                                             │
│  ┌──────────────────────┐  ┌──────────────────────┐        │
│  │                  [⋮] │  │ ● (live badge)   [⋮] │  ⑧    │
│  │  Navigation Issues   │  │  Pricing Confusion    │        │
│  │  14 Facts            │  │  11 Facts             │        │
│  └──────────────────────┘  └──────────────────────┘        │
│                                                             │
│  ⑪ ❌ Clustering failed: 3 facts could not be assigned.    │
│     [Assign manually]  [Retry]                              │
│                                                             │
└─────────────────────────────────────────────────────────────┘

③ StatusBar: Live-Counter (tabular-nums, kein Reload noetig)
④ ProgressIndicator: Nur sichtbar waehrend clustering laeuft
   Format: "{step_label}... {completed}/{total}"
⑧ live_update_badge: Pulsierender blauer Dot, 3s sichtbar
⑪ clustering_error_banner: Toast-Notification bei clustering_failed
```

**Referenz Skills fuer UI-Implementation:**
- `.claude/skills/react-best-practices/SKILL.md` — `rerender-use-ref-transient-values` (callbacks in ref)
- `.claude/skills/web-design/SKILL.md` — `aria-live` fuer async Updates, Animation mit `prefers-reduced-motion`
- `.claude/skills/tailwind-v4/SKILL.md` — `tabular-nums` fuer Zaehler, `animate-pulse` fuer live badge

### 1. ProgressIndicator

**Komponenten & Dateien:**
- `dashboard/components/ProgressIndicator.tsx` — Progress-Anzeige mit Schritt-Label und Fortschrittsbalken

**Verhalten:**
- Nur sichtbar wenn `isProcessing === true` (waehrend Clustering-Pipeline)
- Step-Label wechselt mit jedem `clustering_progress` Event
- Fortschrittsbalken animiert smooth (`transition-[width] duration-300`)
- Automatisch ausgeblendet nach `clustering_completed` oder `clustering_failed`

**Zustaende:**
- Hidden: `isProcessing === false`
- Active: Fortschrittsbalken mit aktuellem Schritt und Zaehler
- Kein separater Error-Zustand (Error kommt via Toast)

**Design Patterns:**
- [x] Accessibility: `role="progressbar"` mit `aria-valuenow/min/max`, `aria-live="polite"` auf Container
- [x] Animation: Nur `width` Transition (CSS-Eigenschaft, kein Layout-Trigger wegen `overflow-hidden`)
- [x] Responsive: Full-width, kein responsive Breakpoint noetig

### 2. live_update_badge (ClusterCard Erweiterung)

**Komponenten & Dateien:**
- `dashboard/components/ClusterCard.tsx` — Erweiterung um `hasLiveUpdate` Prop und Badge-State

**Verhalten:**
- Badge erscheint sofort wenn `hasLiveUpdate` Prop sich von `false` auf `true` aendert
- Badge bleibt 3 Sekunden sichtbar (via `setTimeout`)
- Badge blendet sich automatisch aus nach 3s
- Mehrfache Updates verlängern NICHT die Anzeigedauer (letzter Update-Zeitpunkt gewinnt)

**Zustaende:**
- `showBadge === false` — Dot nicht sichtbar (kein DOM-Element, kein Layout-Impact)
- `showBadge === true` — Blauer pulsierender Dot (`animate-pulse`)

**Design Patterns:**
- [x] Accessibility: `aria-label="New fact added"` + `aria-live="polite"` auf Badge
- [x] Animation: `animate-pulse` verwendet `opacity` + `transform` (GPU-optimiert)
- [x] Reduced Motion: `@media (prefers-reduced-motion: reduce)` blendet `animate-pulse` aus (Tailwind built-in)

### 3. StatusBar Live-Updates

**Komponenten & Dateien:**
- `dashboard/components/StatusBar.tsx` — Props-basierte Anzeige (unveraendert)
- `dashboard/app/projects/[id]/page.tsx` — haelt State, leitet Updates via Props weiter

**Verhalten:**
- Optimistic update: `factCount` sofort bei `fact_extracted` erhoehen
- Exakte Synchronisation: `router.refresh()` nach `clustering_completed`

### 4. Toast-Notification bei clustering_failed

**Komponenten & Dateien:**
- `dashboard/components/Toast.tsx` — Toast-System (muss in Slice 4 oder hier implementiert sein)
- Aufgerufen via `toast.error(message)` in `ProjectPageClient`

**Verhalten:**
- Toast erscheint oben rechts (oder unten je nach Design-System)
- Fehlermeldung: `"Clustering failed: N facts could not be assigned. Check the Insights tab."`
- Auto-dismiss nach 8s (Fehler-Toasts laenger sichtbar als Success)
- Kein Screenshot-Test noetig — Unit-Test prueft dass `toast.error` aufgerufen wird

### 5. Accessibility
- [x] `ProgressIndicator`: `role="progressbar"`, `aria-live="polite"` auf Status-Container
- [x] `live_update_badge`: `aria-label="New fact added"`, `aria-live="polite"`
- [x] `StatusBar`: Statische Labels, kein ARIA noetig (Werte sind visuelle Zahlen mit Kontext-Text)
- [x] Toast: `role="alert"` fuer Fehler-Toasts (sofortige Ankuendigung via Screen Reader)

---

## Acceptance Criteria

1) GIVEN a clustering pipeline is running for a project
   WHEN the `ClusteringService` publishes a `clustering_progress` event
   THEN the `ProgressIndicator` component in the Insights tab shows the current step label and completed/total counter, updated in real time without page reload

2) GIVEN a clustering pipeline completes successfully
   WHEN the `ClusteringService` publishes a `clustering_completed` event
   THEN the `ProgressIndicator` disappears, the `StatusBar` counters update to the new values, and `router.refresh()` is called to load the latest cluster data

3) GIVEN a clustering pipeline fails after 3 retries
   WHEN the `ClusteringService` publishes a `clustering_failed` event
   THEN the `ProgressIndicator` disappears and a toast error notification appears with the message about unassigned facts

4) GIVEN a new fact is extracted for a project
   WHEN the `FactExtractionService` publishes a `fact_extracted` event containing an `interview_id`
   THEN the corresponding `ClusterCard` shows a pulsing blue dot (`live_update_badge`) for 3 seconds and then automatically hides it

5) GIVEN the SSE connection drops (network error)
   WHEN the `EventSource.onerror` callback fires
   THEN the `useProjectEvents` hook automatically reconnects with exponential backoff (1s, 2s, 4s, max 30s)

6) GIVEN a user navigates away from the project dashboard
   WHEN the React component unmounts
   THEN the `EventSource` connection is closed (no memory leak) via `useEffect` cleanup

7) GIVEN a `summary_updated` event is received
   WHEN a cluster summary is regenerated after a merge/split operation
   THEN `router.refresh()` is called to load the updated summary text in the cluster cards

---

## Testfaelle

### Test-Datei

`tests/slices/llm-interview-clustering/slice-07-live-updates-sse.test.ts`

### Unit Tests (Vitest)

<test_spec>
```typescript
// dashboard/tests/slices/llm-interview-clustering/slice-07-live-updates-sse.test.ts
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { render, screen } from "@testing-library/react";
import { useProjectEvents } from "@/hooks/useProjectEvents";
import { ProgressIndicator } from "@/components/ProgressIndicator";
import { ClusterCard } from "@/components/ClusterCard";

// Mock EventSource
class MockEventSource {
  static instances: MockEventSource[] = [];
  url: string;
  onerror: ((e: Event) => void) | null = null;
  private listeners: Map<string, ((e: MessageEvent) => void)[]> = new Map();

  constructor(url: string) {
    this.url = url;
    MockEventSource.instances.push(this);
  }

  addEventListener(type: string, handler: (e: MessageEvent) => void): void {
    if (!this.listeners.has(type)) {
      this.listeners.set(type, []);
    }
    this.listeners.get(type)!.push(handler);
  }

  dispatchEvent(type: string, data: object): void {
    const handlers = this.listeners.get(type) ?? [];
    const event = { data: JSON.stringify(data) } as MessageEvent;
    handlers.forEach((h) => h(event));
  }

  close = vi.fn();
}

describe("useProjectEvents", () => {
  beforeEach(() => {
    MockEventSource.instances = [];
    vi.stubGlobal("EventSource", MockEventSource);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("should connect to SSE endpoint with correct URL", () => {
    const { unmount } = renderHook(() =>
      useProjectEvents("proj-123", "test-token", {}),
    );

    expect(MockEventSource.instances).toHaveLength(1);
    expect(MockEventSource.instances[0].url).toContain("/api/projects/proj-123/events");
    expect(MockEventSource.instances[0].url).toContain("token=test-token");

    unmount();
  });

  it("should call onClusteringProgress when clustering_progress event received", () => {
    const onClusteringProgress = vi.fn();

    renderHook(() =>
      useProjectEvents("proj-123", "test-token", { onClusteringProgress }),
    );

    const es = MockEventSource.instances[0];
    act(() => {
      es.dispatchEvent("clustering_progress", {
        interview_id: "iv-1",
        step: "assigning",
        completed: 3,
        total: 10,
      });
    });

    expect(onClusteringProgress).toHaveBeenCalledWith({
      interview_id: "iv-1",
      step: "assigning",
      completed: 3,
      total: 10,
    });
  });

  it("should call onClusteringCompleted when clustering_completed event received", () => {
    const onClusteringCompleted = vi.fn();

    renderHook(() =>
      useProjectEvents("proj-123", "test-token", { onClusteringCompleted }),
    );

    const es = MockEventSource.instances[0];
    act(() => {
      es.dispatchEvent("clustering_completed", {
        cluster_count: 5,
        fact_count: 47,
      });
    });

    expect(onClusteringCompleted).toHaveBeenCalledWith({
      cluster_count: 5,
      fact_count: 47,
    });
  });

  it("should call onClusteringFailed when clustering_failed event received", () => {
    const onClusteringFailed = vi.fn();

    renderHook(() =>
      useProjectEvents("proj-123", "test-token", { onClusteringFailed }),
    );

    const es = MockEventSource.instances[0];
    act(() => {
      es.dispatchEvent("clustering_failed", {
        error: "LLM timeout",
        unassigned_count: 3,
      });
    });

    expect(onClusteringFailed).toHaveBeenCalledWith({
      error: "LLM timeout",
      unassigned_count: 3,
    });
  });

  it("should reconnect with delay on onerror", async () => {
    vi.useFakeTimers();
    const { unmount } = renderHook(() =>
      useProjectEvents("proj-123", "test-token", {}),
    );

    const es = MockEventSource.instances[0];
    act(() => {
      es.onerror?.(new Event("error"));
    });

    expect(es.close).toHaveBeenCalled();

    // After 1s initial delay, reconnect
    await act(async () => {
      vi.advanceTimersByTime(1000);
    });

    expect(MockEventSource.instances).toHaveLength(2);

    unmount();
    vi.useRealTimers();
  });

  it("should close EventSource on unmount", () => {
    const { unmount } = renderHook(() =>
      useProjectEvents("proj-123", "test-token", {}),
    );

    const es = MockEventSource.instances[0];
    unmount();

    expect(es.close).toHaveBeenCalled();
  });
});

describe("ProgressIndicator", () => {
  it("should render step label with completed/total counter", () => {
    render(
      <ProgressIndicator step="assigning" completed={3} total={10} />,
    );

    expect(screen.getByTestId("progress-label")).toHaveTextContent(
      "Assigning to clusters... 3/10",
    );
  });

  it("should show correct percentage", () => {
    render(
      <ProgressIndicator step="extracting" completed={5} total={10} />,
    );

    expect(screen.getByTestId("progress-pct")).toHaveTextContent("50%");
    const bar = screen.getByTestId("progress-bar-fill");
    expect(bar).toHaveStyle({ width: "50%" });
  });

  it("should have progressbar role with aria attributes", () => {
    render(
      <ProgressIndicator step="validating" completed={2} total={3} />,
    );

    const progressbar = screen.getByRole("progressbar");
    expect(progressbar).toHaveAttribute("aria-valuenow", "67");
    expect(progressbar).toHaveAttribute("aria-valuemin", "0");
    expect(progressbar).toHaveAttribute("aria-valuemax", "100");
  });

  it("should handle total=0 without division by zero", () => {
    render(
      <ProgressIndicator step="extracting" completed={0} total={0} />,
    );

    expect(screen.getByTestId("progress-pct")).toHaveTextContent("0%");
  });
});

describe("ClusterCard live_update_badge", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  const mockCluster = {
    id: "cluster-1",
    name: "Navigation Issues",
    summary: "Users struggle with navigation.",
    fact_count: 14,
    interview_count: 8,
    created_at: "2026-02-28T00:00:00Z",
    updated_at: "2026-02-28T00:00:00Z",
  };

  it("should not show live_update_badge by default", () => {
    render(
      <ClusterCard
        cluster={mockCluster}
        hasLiveUpdate={false}
        onClick={vi.fn()}
      />,
    );

    expect(screen.queryByTestId("live-update-badge")).not.toBeInTheDocument();
  });

  it("should show live_update_badge when hasLiveUpdate is true", () => {
    render(
      <ClusterCard
        cluster={mockCluster}
        hasLiveUpdate={true}
        onClick={vi.fn()}
      />,
    );

    expect(screen.getByTestId("live-update-badge")).toBeInTheDocument();
  });

  it("should hide live_update_badge after 3 seconds", () => {
    const { rerender } = render(
      <ClusterCard
        cluster={mockCluster}
        hasLiveUpdate={false}
        onClick={vi.fn()}
      />,
    );

    rerender(
      <ClusterCard
        cluster={mockCluster}
        hasLiveUpdate={true}
        onClick={vi.fn()}
      />,
    );

    expect(screen.getByTestId("live-update-badge")).toBeInTheDocument();

    act(() => {
      vi.advanceTimersByTime(3000);
    });

    expect(screen.queryByTestId("live-update-badge")).not.toBeInTheDocument();
  });

  it("should display cluster name and fact count", () => {
    render(
      <ClusterCard
        cluster={mockCluster}
        hasLiveUpdate={false}
        onClick={vi.fn()}
      />,
    );

    expect(screen.getByTestId("cluster-card-name")).toHaveTextContent("Navigation Issues");
    expect(screen.getByTestId("cluster-fact-count")).toHaveTextContent("14 Facts");
  });

  it("should call onClick when Enter key pressed (keyboard accessibility)", () => {
    const onClick = vi.fn();
    render(
      <ClusterCard cluster={mockCluster} hasLiveUpdate={false} onClick={onClick} />,
    );

    const card = screen.getByTestId("cluster-card");
    card.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter", bubbles: true }));

    expect(onClick).toHaveBeenCalled();
  });
});
```
</test_spec>

---

## Definition of Done

- [x] Akzeptanzkriterien sind eindeutig und vollstaendig
- [ ] Logging: SSE-Verbindungen werden geloggt (`logger.info("SSE client connected/disconnected for project {project_id}")`)
- [ ] Security: JWT-Validierung im SSE-Endpoint (Owner-Check) — EventSource-Verbindung wird bei 401/403 sofort geschlossen
- [ ] UX/Copy: Progress-Labels auf Englisch (`"Extracting facts..."`, `"Assigning to clusters..."`, etc.)
- [ ] Rollout: Kein Feature-Flag noetig — SSE-Endpoint ist additive Erweiterung ohne Breaking Changes

---

## Skill Verification (UI-Implementation)

### React Best Practices Verification

**Critical Priority:**
- [x] `async-parallel`: Kein paralleles Fetching noetig — SSE ist event-driven
- [x] `bundle-dynamic-imports`: `ProgressIndicator` und `ClusterCard` sind leichtgewichtig — kein lazy loading noetig

**High Priority:**
- [x] `server-cache-react`: `router.refresh()` triggert Server-Component-Revalidierung
- [x] `async-suspense-boundaries`: SSE-Hook ist Client-only — keine Suspense noetig

**Medium Priority:**
- [x] `rerender-memo`: `ClusterCard` ist in `memo()` gewrapped
- [x] `rerender-use-ref-transient-values`: `callbacksRef` und `reconnectDelayRef` in `useRef` (kein Re-Connect bei Render)
- [x] `rerender-dependencies`: `useEffect` in `useProjectEvents` haengt nur von `connect` ab (stabile Callback-Referenz)

### Web Design Guidelines Verification

**Accessibility:**
- [x] `live_update_badge` hat `aria-label="New fact added"` und `aria-live="polite"`
- [x] `ProgressIndicator` hat `role="progressbar"` mit `aria-valuenow/min/max`
- [x] Toast-Fehler hat `role="alert"` fuer sofortige Screen-Reader-Ankuendigung
- [x] `ClusterCard` ist via Keyboard (`Enter`) bedienbar mit `focus-visible` Ring

**Animation & Motion:**
- [x] `animate-pulse` respektiert `prefers-reduced-motion: reduce` (Tailwind built-in)
- [x] Fortschrittsbalken animiert nur `width` (kein Layout-Trigger ausser `overflow-hidden` Container)

**Touch & Mobile:**
- [x] `touch-action-manipulation` auf `ClusterCard` (verhindert double-tap zoom)

### Tailwind v4 Patterns Verification

**Design Tokens:**
- [x] Keine hardcoded Hex-Werte — alle Farben via Tailwind-Utilities
- [x] `tabular-nums` fuer StatusBar-Zaehler (Alignment bei wechselnden Zahlen)
- [x] `dark:` Modifier fuer Dark Mode in allen Komponenten

**Responsive:**
- [x] `ProgressIndicator` ist full-width (kein Breakpoint noetig)
- [x] `ClusterCard` ist unabhaengig von Container-Breite

---

## Constraints & Hinweise

**Betrifft:**
- Backend `sse_routes.py`: EventSource-Auth via Query-Parameter (nicht Header) — dies ist ein SSE-Protokoll-Constraint
- Frontend `useProjectEvents`: Token muss als Prop uebergeben werden (aus Server-Component gelesen, nicht localStorage) — Auth-Integration kommt in Slice 8

**API Contract:**
- SSE-Verbindung muss `?token=<jwt>` enthalten (architecture.md: "SSE Auth: JWT in query param since EventSource doesn't support headers")
- Heartbeat alle 30s via `: heartbeat` Comment (Proxy-Kompatibilitaet)
- `clustering_progress` Event ist NEU in diesem Slice (nicht in architecture.md SSE-Tabelle) — wird in `SseEventBus.publish()` hinzugefuegt

**Abgrenzung:**
- Slice 7 liest JWT-Token noch aus einer temporaeren Quelle (Props/Context) — finale Auth-Integration (Login-Guard, Token-Storage) kommt in Slice 8
- `Toast.tsx` Komponente: Falls noch nicht in Slice 4-6 implementiert, muss sie hier als minimal-Implementation erstellt werden

---

## Integration Contract (GATE 2 PFLICHT)

> **Wichtig:** Diese Section wird vom Gate 2 Compliance Agent geprueft. Unvollstaendige Contracts blockieren die Genehmigung.

### Requires From Other Slices

| Slice | Resource | Type | Validation |
|-------|----------|------|------------|
| `slice-02-fact-extraction-pipeline` | `SseEventBus` | Singleton Class | `subscribe()`, `unsubscribe()`, `publish()` Methoden vorhanden |
| `slice-02-fact-extraction-pipeline` | `fact_extracted` SSE Event | Event Type | `{interview_id: str, fact_count: int}` |
| `slice-03-clustering-pipeline-agent` | `clustering_started` SSE Event | Event Type | `{mode: "incremental"|"full"}` |
| `slice-03-clustering-pipeline-agent` | `clustering_completed` SSE Event | Event Type | `{cluster_count: int, fact_count: int}` |
| `slice-03-clustering-pipeline-agent` | `clustering_failed` SSE Event | Event Type | `{error: str, unassigned_count: int}` |
| `slice-03-clustering-pipeline-agent` | `summary_updated` SSE Event | Event Type | `{cluster_id: str}` |
| `slice-04-dashboard-projekt-cluster-uebersicht` | `ClusterCard` Component | React Component | Akzeptiert `hasLiveUpdate?: boolean` Prop (Erweiterung) |
| `slice-04-dashboard-projekt-cluster-uebersicht` | `StatusBar` Component | React Component | Akzeptiert `interviewCount`, `factCount`, `clusterCount` Props |
| `slice-04-dashboard-projekt-cluster-uebersicht` | `ProjectTabs` Component | React Component | Insights Tab enthaelt `progress_indicator` und `cluster_grid` |

### Provides To Other Slices

| Resource | Type | Consumer | Interface |
|----------|------|----------|-----------|
| `GET /api/projects/{id}/events` | SSE Endpoint | `slice-08-auth-polish` | Auth via `?token=<jwt>`, Owner-Check, `EventSourceResponse` |
| `useProjectEvents()` | React Hook | `slice-08-auth-polish` (Token-Quelle aendert sich) | `(projectId: string, token: string, callbacks: UseProjectEventsCallbacks) => void` |
| `ProgressIndicator` | React Component | — | `(step, completed, total) => JSX.Element` |
| `live_update_badge` State | ClusterCard Extension | — | `hasLiveUpdate?: boolean` Prop auf `ClusterCard` |

### Integration Validation Tasks

- [ ] `SseEventBus.subscribe()` gibt `asyncio.Queue` zurueck (Slice 2 Contract)
- [ ] `SseEventBus.unsubscribe()` wird in `finally`-Block aufgerufen (kein Queue-Leak)
- [ ] `clustering_progress` Event-Typ wird in `ClusteringService` (Slice 3) publiziert
- [ ] JWT in Query-Parameter `?token=` wird von `get_current_user_from_token` Dependency akzeptiert
- [ ] `ClusterCard` in Slice 4 akzeptiert `hasLiveUpdate?: boolean` Prop (Mount-Point Check)

---

## Code Examples (MANDATORY - GATE 2 PFLICHT)

> **KRITISCH:** Alle Code-Beispiele in diesem Dokument sind **PFLICHT-Deliverables**.
> Der Gate 2 Compliance Agent prueft, dass jedes Code-Beispiel implementiert wird.

| Code Example | Section | Mandatory | Notes |
|--------------|---------|-----------|-------|
| `project_events()` Route Handler | Section 3 | YES | Exakt wie spezifiziert: JWT via Query-Param, Owner-Check, Heartbeat |
| `useProjectEvents()` Hook | Section 5 | YES | Alle 6 Event-Types, exponential backoff, cleanup |
| `ClusterCard` mit `live_update_badge` | Section 6 | YES | `hasLiveUpdate` Prop, 3s Timer, `animate-pulse` |
| `ProgressIndicator` | Section 7 | YES | `role="progressbar"`, `aria-valuenow`, Step-Labels |
| `StatusBar` | Section 8 | YES | `tabular-nums`, `data-testid` Attribute |
| `ProjectPageClient` | Section 9 | YES | Alle SSE-Callbacks, `router.refresh()`, Toast |

### SSE-Endpoint (`project_events` Route Handler)

Bereits vollstaendig spezifiziert in Section 3 (`backend/app/api/sse_routes.py`).

**Pflicht-Aspekte:**
- JWT via `token: str = Query(...)` — kein Authorization-Header
- Owner-Check vor Queue-Subscription
- `asyncio.wait_for(queue.get(), timeout=30.0)` fuer Heartbeat
- `event_bus.unsubscribe(project_id, queue)` im `finally`-Block

### `useProjectEvents` Hook

Bereits vollstaendig spezifiziert in Section 5 (`dashboard/hooks/useProjectEvents.ts`).

**Pflicht-Aspekte:**
- `callbacksRef = useRef(callbacks)` — verhindert EventSource-Reconnect bei Render
- `reconnectDelayRef` mit `Math.min(delay * 2, 30_000)` — exponential backoff, max 30s
- `es.close()` in `useEffect` cleanup — kein Memory-Leak
- Alle 6 Event-Types als `addEventListener` (NICHT `onmessage` — Named Events brauchen `addEventListener`)

### `ClusterCard` mit `live_update_badge`

Bereits vollstaendig spezifiziert in Section 6 (`dashboard/components/ClusterCard.tsx`).

**Pflicht-Aspekte:**
- `memo()` Wrapping fuer Performance
- `setTimeout(..., 3000)` in `useEffect` mit Cleanup (`clearTimeout`)
- `data-testid="live-update-badge"` fuer Tests
- `animate-pulse` (Tailwind — respektiert `prefers-reduced-motion`)

### `ProgressIndicator`

Bereits vollstaendig spezifiziert in Section 7 (`dashboard/components/ProgressIndicator.tsx`).

**Pflicht-Aspekte:**
- `role="progressbar"` mit `aria-valuenow`, `aria-valuemin`, `aria-valuemax`
- `aria-live="polite"` auf aeusserstem Container
- `data-testid` Attribute auf Label, Prozentzahl, Balken-Fill
- `Math.round((completed / total) * 100)` — kein NaN wenn `total === 0`

### `StatusBar`

Bereits vollstaendig spezifiziert in Section 8 (`dashboard/components/StatusBar.tsx`).

**Pflicht-Aspekte:**
- `tabular-nums` CSS-Klasse fuer numerische Werte
- `data-testid` Attribute fuer Tests

### `ProjectPageClient`

Bereits vollstaendig spezifiziert in Section 9 (`dashboard/app/projects/[id]/page.tsx`).

**Pflicht-Aspekte:**
- `useCallback` fuer alle Event-Handler
- `router.refresh()` NUR bei `clustering_completed` und `summary_updated` (NICHT bei `clustering_progress`)
- `toast.error(...)` bei `clustering_failed` mit Fehlertext
- Optimistic `factCount`/`clusterCount` State-Updates

---

## Links

- Discovery: `specs/phase-4/2026-02-28-llm-interview-clustering/discovery.md`
- Architecture: `specs/phase-4/2026-02-28-llm-interview-clustering/architecture.md`
- Wireframes: `specs/phase-4/2026-02-28-llm-interview-clustering/wireframes.md`
- Slice 2 (SseEventBus): `specs/phase-4/2026-02-28-llm-interview-clustering/slices/slice-02-fact-extraction-pipeline.md`
- Slice 3 (ClusteringService Events): `specs/phase-4/2026-02-28-llm-interview-clustering/slices/slice-03-clustering-pipeline-agent.md`
- Slice 4 (Dashboard-App): `specs/phase-4/2026-02-28-llm-interview-clustering/slices/slice-04-dashboard-projekt-cluster-uebersicht.md`
- SSE Spec (MDN): https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events/Using_server-sent_events

---

## Deliverables (SCOPE SAFEGUARD)

**WICHTIG: Diese Liste wird automatisch vom Stop-Hook validiert. Der Agent kann nicht stoppen, wenn Dateien fehlen.**

<!-- DELIVERABLES_START -->
### Backend

- [ ] `backend/app/api/sse_routes.py` — `GET /api/projects/{id}/events` SSE-Endpoint mit JWT Query-Param Auth und Owner-Check
- [ ] `backend/app/clustering/service.py` — Erweiterung: `clustering_progress` Events in Pipeline-Schritten publizieren

### Frontend

- [ ] `dashboard/hooks/useProjectEvents.ts` — React Hook: EventSource, alle 6 Event-Types, auto-reconnect, cleanup
- [ ] `dashboard/components/ClusterCard.tsx` — Erweiterung: `hasLiveUpdate` Prop, `live_update_badge` mit 3s Timer und `animate-pulse`
- [ ] `dashboard/components/ProgressIndicator.tsx` — Progress-Anzeige mit Schritt-Label, Fortschrittsbalken, ARIA-Attribute
- [ ] `dashboard/components/StatusBar.tsx` — Live-Counter mit `tabular-nums` und `data-testid` Attributen
- [ ] `dashboard/app/projects/[id]/page.tsx` — Erweiterung: `ProjectPageClient` mit `useProjectEvents`, `router.refresh()`, Toast

### Tests

- [ ] `dashboard/tests/slices/llm-interview-clustering/slice-07-live-updates-sse.test.ts` — Vitest Unit Tests fuer Hook, ProgressIndicator, ClusterCard Badge
<!-- DELIVERABLES_END -->

**Hinweis fuer den Implementierungs-Agent:**
- Alle Dateien zwischen `<!-- DELIVERABLES_START -->` und `<!-- DELIVERABLES_END -->` sind **Pflicht**
- Der Stop-Hook prueft automatisch ob alle Dateien existieren
- Bei fehlenden Dateien wird der Agent blockiert und muss nachfragen

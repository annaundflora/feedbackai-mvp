# Integration Map: LLM Interview Clustering

**Generated:** 2026-02-28
**Slices:** 8
**Connections:** 34
**Status:** All 8 slices APPROVED

---

## Dependency Graph (Visual)

```
┌─────────────────────────────────┐
│  Slice 01: DB Schema + CRUD     │  (Foundation — no dependencies)
└─────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────┐
│  Slice 02: Fact Extraction      │  depends: Slice 01
└─────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────┐
│  Slice 03: Clustering Agent     │  depends: Slice 01, 02
└─────────────────────────────────┘
        │           │
        ▼           ▼
┌───────────┐  ┌───────────┐
│ Slice 04  │  │           │
│ Dashboard │  │           │
│ Proj+Clus │  │           │
└───────────┘  │           │
     │  │      │           │
     │  └──────┼───────────┼──────────────┐
     ▼          ▼           │              │
┌───────────┐  │           │              │
│ Slice 05  │  │           │              │
│ Drill-Down│  │           │              │
│ + Quotes  │  │           │              │
└───────────┘  │           │              │
     │          │           │              │
     ▼          ▼           ▼              │
┌──────────────────────────────┐          │
│  Slice 06: Taxonomy Editing  │ depends: 01,03,05
│  + Summary Regen             │          │
└──────────────────────────────┘          │
               │                          │
               ▼                          │
┌─────────────────────────────────┐       │
│  Slice 07: Live-Updates SSE     │ depends: 02,03,04
└─────────────────────────────────┘       │
               │                          │
               ▼                          │
┌─────────────────────────────────────────┘
│  Slice 08: Auth + Polish        │ depends: 01,04,07
└─────────────────────────────────┘
```

**Simplified linear dependency chain:**
```
01 → 02 → 03 → 04 → 05 → 06 → 07 → 08
              ↘    ↗ (Slice 04 also depends on 03)
               07 (also depends on 02, 03, 04)
               08 (also depends on 01, 04, 07)
```

---

## Nodes

### Slice 01: DB Schema + Projekt CRUD

| Field | Value |
|-------|-------|
| Status | APPROVED |
| Dependencies | None |
| Outputs | DB tables (6), Repositories (2), Services (2), DTOs (6+) |

**Inputs:**

| Input | Source | Validation |
|-------|--------|------------|
| None | — | N/A |

**Outputs:**

| Output | Type | Consumers |
|--------|------|-----------|
| `users` table | PostgreSQL schema | Slice 08 |
| `projects` table | PostgreSQL schema | Slice 02, 03, 04, 05, 06, 07, 08 |
| `project_interviews` table | PostgreSQL schema | Slice 02, 04, 08 |
| `clusters` table | PostgreSQL schema | Slice 03, 04, 05, 06, 07 |
| `facts` table | PostgreSQL schema | Slice 02, 03, 05, 06 |
| `cluster_suggestions` table | PostgreSQL schema | Slice 03, 06 |
| `ProjectRepository` | Python class | Slice 02, 03 |
| `InterviewAssignmentRepository` | Python class | Slice 02 |
| `ProjectService` | Python class | Slice 08 |
| `InterviewAssignmentService` | Python class | Slice 07 |
| `ProjectResponse` DTO | Pydantic schema | Slice 04, 06, 08 |
| `ProjectListItem` DTO | Pydantic schema | Slice 04 |
| `InterviewAssignment` DTO | Pydantic schema | Slice 02, 08 |
| `AvailableInterview` DTO | Pydantic schema | Slice 08 |
| `GET/POST /api/projects` endpoints | FastAPI router | Slice 04, 08 |
| `GET/PUT/DELETE /api/projects/{id}` endpoints | FastAPI router | Slice 04, 06, 08 |
| `POST /api/projects/{id}/interviews` endpoint | FastAPI router | Slice 08 |
| `GET /api/projects/{id}/interviews/available` endpoint | FastAPI router | Slice 08 |

---

### Slice 02: Fact Extraction Pipeline

| Field | Value |
|-------|-------|
| Status | APPROVED |
| Dependencies | Slice 01 |
| Outputs | FactExtractionService, FactRepository, SseEventBus, retry endpoint |

**Inputs:**

| Input | Source | Validation |
|-------|--------|------------|
| `projects` table (project_id, research_goal, extraction_source, model_extraction, prompt_context) | Slice 01 | APPROVED |
| `project_interviews` table (extraction_status, clustering_status) | Slice 01 | APPROVED |
| `facts` table (schema for inserts) | Slice 01 | APPROVED |
| `InterviewAssignmentRepository` | Slice 01 | APPROVED |
| `InterviewAssignment` DTO | Slice 01 | APPROVED |

**Outputs:**

| Output | Type | Consumers |
|--------|------|-----------|
| `FactExtractionService` (with `clustering_service` DI param) | Python class | Slice 03 (via DI trigger) |
| `FactRepository` (save_facts, get_facts_for_interview, get_facts_for_project) | Python class | Slice 03, 05 |
| `SseEventBus` (subscribe, unsubscribe, publish) | Python class (singleton) | Slice 03, 07 |
| `fact_extracted` SSE event `{interview_id, fact_count}` | SSE event type | Slice 07 |
| `extraction_status` DB state (pending/running/completed/failed) | DB field | Slice 04, 08 |
| `POST /api/projects/{id}/interviews/{iid}/retry` | FastAPI endpoint | Slice 08 (UI retry_btn) |
| `InterviewService.end()` hook extension | Python code | Internal (triggers extraction) |

---

### Slice 03: Clustering Pipeline + LangGraph Agent

| Field | Value |
|-------|-------|
| Status | APPROVED |
| Dependencies | Slice 01, Slice 02 |
| Outputs | ClusteringService, ClusterRepository, ClusterSuggestionRepository, SSE events, recluster endpoint |

**Inputs:**

| Input | Source | Validation |
|-------|--------|------------|
| `projects` table (research_goal, model_clustering, model_summary) | Slice 01 | APPROVED |
| `clusters` table (all fields) | Slice 01 | APPROVED |
| `facts` table (id, cluster_id nullable, content) | Slice 01 | APPROVED |
| `cluster_suggestions` table (all fields) | Slice 01 | APPROVED |
| `project_interviews.clustering_status` | Slice 01 | APPROVED |
| `ProjectRepository.get_by_id()` | Slice 01 | APPROVED |
| `InterviewAssignmentRepository.find_by_interview_id()` | Slice 01 | APPROVED |
| `FactRepository.get_facts_for_interview()` | Slice 02 | APPROVED |
| `FactRepository.get_facts_for_project()` | Slice 02 | APPROVED |
| `FactExtractionService` with `clustering_service` DI param | Slice 02 | APPROVED |
| `SseEventBus.publish()` (singleton) | Slice 02 | APPROVED |

**Outputs:**

| Output | Type | Consumers |
|--------|------|-----------|
| `ClusteringService.process_interview()` | Python class method | Slice 04 (data), Slice 06, Slice 07 |
| `ClusteringService.full_recluster()` | Python class method | Slice 06 |
| `ClusterRepository` (list_for_project, get_by_id, create_clusters, update_summary, delete_all_for_project) | Python class | Slice 04, 05, 06 |
| `ClusterSuggestionRepository` (list_pending_for_project, update_status) | Python class | Slice 06 |
| `FactRepository.update_cluster_assignments()` (extended) | Python method | Slice 06 |
| `FactRepository.reset_cluster_assignments_for_project()` (extended) | Python method | Internal (full recluster) |
| `clusters` table populated with data | DB state | Slice 04 |
| `cluster_suggestions` table populated | DB state | Slice 06 |
| `clustering_started` SSE event `{mode}` | SSE event type | Slice 07 |
| `clustering_updated` SSE event `{clusters}` | SSE event type | Slice 07 |
| `clustering_completed` SSE event `{cluster_count, fact_count}` | SSE event type | Slice 07 |
| `clustering_failed` SSE event `{error, unassigned_count}` | SSE event type | Slice 04, Slice 07 |
| `suggestion` SSE event `{type, source_cluster_id, ...}` | SSE event type | Slice 06, Slice 07 |
| `summary_updated` SSE event `{cluster_id}` | SSE event type | Slice 07 |
| `POST /api/projects/{id}/clustering/recluster` | FastAPI endpoint | Slice 06 |
| `GET /api/projects/{id}/clustering/status` | FastAPI endpoint | Slice 04 (progress indicator) |
| `InterviewAssignmentRepository.update_clustering_status()` (extended) | Python method | Internal |
| `InterviewAssignmentRepository.get_all_for_project()` (extended) | Python method | Internal |
| `SummaryGenerationService.regenerate_for_cluster()` | Python method | Slice 06 |

---

### Slice 04: Dashboard — Projekt-Liste + Cluster-Uebersicht

| Field | Value |
|-------|-------|
| Status | APPROVED |
| Dependencies | Slice 01, 02, 03 |
| Outputs | Next.js dashboard app, API client, TypeScript types, page files, components |

**Inputs:**

| Input | Source | Validation |
|-------|--------|------------|
| `GET /api/projects` | Slice 01 | APPROVED |
| `POST /api/projects` | Slice 01 | APPROVED |
| `GET /api/projects/{id}` | Slice 01 | APPROVED |
| `GET /api/projects/{id}/clusters` | Slice 03 (ClusterRepository) | APPROVED |

**Outputs:**

| Output | Type | Consumers |
|--------|------|-----------|
| `dashboard/` Next.js App on port 3001 | Application shell | Slice 05, 06, 07, 08 |
| `dashboard/lib/api-client.ts` (apiFetch, getProjects, createProject, getProject, getClusters) | TypeScript module | Slice 05, 06, 07, 08 |
| `dashboard/lib/types.ts` (ProjectListItem, ProjectResponse, ClusterResponse, CreateProjectRequest) | TypeScript types | Slice 05, 06, 07, 08 |
| `dashboard/components/cluster-card.tsx` | React component | Slice 05, 06, 07 |
| `dashboard/components/project-tabs.tsx` | React component | Slice 05, 06, 07 |
| `dashboard/components/status-bar.tsx` | React component | Slice 07 |
| `dashboard/components/skeleton-card.tsx` | React component | Slice 08 |
| `dashboard/components/empty-state.tsx` | React component | Slice 08 |
| `dashboard/app/projects/page.tsx` | Next.js page | Slice 08 (extended) |
| `dashboard/app/projects/[id]/page.tsx` | Next.js page | Slice 05, 06, 07, 08 (extended) |
| `dashboard/playwright.config.ts` | Test configuration | Slice 05, 06, 07, 08 |

---

### Slice 05: Dashboard — Cluster Drill-Down + Zitate

| Field | Value |
|-------|-------|
| Status | APPROVED |
| Dependencies | Slice 01, 03, 04 |
| Outputs | Cluster detail page, FactItem, QuoteItem, backend detail endpoint, extended types/client |

**Inputs:**

| Input | Source | Validation |
|-------|--------|------------|
| `facts` table (all fields) | Slice 01 | APPROVED |
| `project_interviews` table (interview_id, assigned_at for ordering) | Slice 01 | APPROVED |
| `backend/app/clustering/router.py` (existing file to extend) | Slice 03 | APPROVED |
| `ClusterRepository` (existing class to extend with get_detail) | Slice 03 | APPROVED |
| `dashboard/` Next.js App on port 3001 | Slice 04 | APPROVED |
| `dashboard/lib/api-client.ts` (apiFetch) | Slice 04 | APPROVED |
| `dashboard/lib/types.ts` (ProjectResponse, ClusterResponse) | Slice 04 | APPROVED |
| `dashboard/components/project-tabs.tsx` | Slice 04 | APPROVED |
| `dashboard/components/cluster-card.tsx` | Slice 04 | APPROVED |

**Outputs:**

| Output | Type | Consumers |
|--------|------|-----------|
| `GET /api/projects/{id}/clusters/{cid}` (ClusterDetailResponse) | FastAPI endpoint | Slice 06, 07 |
| `FactResponse` TypeScript + Pydantic types | DTO | Slice 06 |
| `QuoteResponse` TypeScript + Pydantic types | DTO | Slice 06 |
| `ClusterDetailResponse` TypeScript + Pydantic types | DTO | Slice 06 |
| `dashboard/lib/api-client.ts` (extended: getClusterDetail) | TypeScript module | Slice 06 |
| `dashboard/app/projects/[id]/clusters/[cluster_id]/page.tsx` | Next.js page | Slice 06 (extended) |
| `dashboard/components/fact-item.tsx` | React component | Slice 06 |
| `dashboard/components/quote-item.tsx` | React component | Internal |
| `dashboard/components/cluster-card.tsx` (modified: Link wrapper) | React component | Slice 06, 07 |

---

### Slice 06: Taxonomy-Editing + Summary-Regenerierung

| Field | Value |
|-------|-------|
| Status | APPROVED |
| Dependencies | Slice 01, 03, 05 |
| Outputs | TaxonomyService, 11 backend endpoints, 9 frontend components, TypeScript types |

**Inputs:**

| Input | Source | Validation |
|-------|--------|------------|
| `clusters` table (all fields) | Slice 01 | APPROVED |
| `facts` table (all fields) | Slice 01 | APPROVED |
| `cluster_suggestions` table (all fields) | Slice 01 | APPROVED |
| `ClusteringService.full_recluster()` | Slice 03 | APPROVED |
| `SummaryGenerationService.regenerate_for_cluster()` | Slice 03 | APPROVED |
| `ClusterDetailResponse` (id, name, summary, fact_count, interview_count, facts, quotes) | Slice 05 | APPROVED |
| `FactResponse` TypeScript + Pydantic | Slice 05 | APPROVED |
| `ClusterDetailPage` with disabled Merge/Split buttons | Slice 05 | APPROVED |
| `dashboard/lib/api-client.ts` (apiFetch) | Slice 04 | APPROVED |
| `ClusterResponse` TypeScript type | Slice 04 | APPROVED |
| `ProjectResponse` TypeScript type | Slice 04 | APPROVED |

**Outputs:**

| Output | Type | Consumers |
|--------|------|-----------|
| `TaxonomyService` (rename, merge, undo_merge, preview_split, execute_split) | Python class | Internal (router) |
| Custom exceptions (ClusterNotFoundError, UndoExpiredError, etc.) | Python classes | Internal |
| `PUT /api/projects/{id}/clusters/{cid}` (rename) | FastAPI endpoint | Slice 08 |
| `POST /api/projects/{id}/clusters/merge` | FastAPI endpoint | Slice 08 |
| `POST /api/projects/{id}/clusters/merge/undo` | FastAPI endpoint | Slice 08 |
| `POST /api/projects/{id}/clusters/{cid}/split/preview` | FastAPI endpoint | Slice 08 |
| `POST /api/projects/{id}/clusters/{cid}/split` | FastAPI endpoint | Slice 08 |
| `PUT /api/projects/{id}/facts/{fid}` (move fact) | FastAPI endpoint | Slice 08 |
| `POST /api/projects/{id}/facts/bulk-move` | FastAPI endpoint | Slice 08 |
| `GET /api/projects/{id}/suggestions` | FastAPI endpoint | Slice 08 |
| `POST /api/projects/{id}/suggestions/{sid}/accept` | FastAPI endpoint | Slice 08 |
| `POST /api/projects/{id}/suggestions/{sid}/dismiss` | FastAPI endpoint | Slice 08 |
| `ClusterContextMenu` component | React component | Consumed in cluster-card.tsx (Slice 04 file) |
| `InlineRename` component | React component | Consumed in cluster-card.tsx + cluster detail page |
| `MergeDialog` component | React component | Consumed in projects/[id]/page.tsx |
| `SplitModal` component | React component | Consumed in clusters/[cluster_id]/page.tsx |
| `UndoToast` component | React component | Consumed in cluster detail page |
| `SuggestionBanner` component | React component | Consumed in projects/[id]/page.tsx |
| `RecalculateModal` component | React component | Consumed in projects/[id]/page.tsx |
| `BulkMoveBar` component | React component | Consumed in cluster detail + insights pages |
| `FactContextMenu` component | React component | Consumed in fact-item.tsx |
| 11 TypeScript types (RenameRequest, MergeRequest, etc.) | TypeScript types | Consumed in Slice 08 components |
| 11 API client methods | TypeScript functions | Internal (dashboard components) |
| `SuggestionResponse` TypeScript type | TypeScript type | Slice 07 (SSE updates) |
| `MergeResponse` TypeScript type | TypeScript type | Slice 07 (SSE updates) |

---

### Slice 07: Live-Updates via SSE

| Field | Value |
|-------|-------|
| Status | APPROVED |
| Dependencies | Slice 02, 03, 04 |
| Outputs | SSE backend endpoint, useProjectEvents hook, ProgressIndicator, extended ClusterCard/StatusBar |

**Inputs:**

| Input | Source | Validation |
|-------|--------|------------|
| `SseEventBus` singleton (subscribe, unsubscribe) | Slice 02 | APPROVED |
| `fact_extracted` event `{interview_id, fact_count}` | Slice 02 | APPROVED |
| `clustering_started` event `{mode}` | Slice 03 | APPROVED |
| `clustering_completed` event `{cluster_count, fact_count}` | Slice 03 | APPROVED |
| `clustering_failed` event `{error, unassigned_count}` | Slice 03 | APPROVED |
| `summary_updated` event `{cluster_id}` | Slice 03 | APPROVED |
| `ClusterCard` component (`hasLiveUpdate?: boolean` prop needed) | Slice 04 | APPROVED |
| `StatusBar` component | Slice 04 | APPROVED |
| `ProjectTabs` component | Slice 04 | APPROVED |
| `dashboard/app/projects/[id]/page.tsx` (to extend) | Slice 04 | APPROVED |

**Outputs:**

| Output | Type | Consumers |
|--------|------|-----------|
| `GET /api/projects/{id}/events` SSE endpoint | FastAPI endpoint | Slice 08 (auth integration) |
| `backend/app/api/sse_routes.py` | Python module | Slice 08 |
| `get_current_user_from_token()` dependency | Python function | Slice 08 (reused unchanged) |
| `useProjectEvents(projectId, token, callbacks)` hook | React hook | Slice 08 |
| `dashboard/hooks/useProjectEvents.ts` | TypeScript module | Slice 08 |
| `ProgressIndicator` component | React component | Consumed in projects/[id]/page.tsx |
| `ClusterCard` (extended: hasLiveUpdate prop + live_update_badge) | React component | Slice 08 (extended) |
| `StatusBar` (extended: live counters) | React component | Slice 08 (extended) |
| `dashboard/app/projects/[id]/page.tsx` (ProjectPageClient) | Next.js client component | Slice 08 (extended) |

---

### Slice 08: Auth + Polish

| Field | Value |
|-------|-------|
| Status | APPROVED |
| Dependencies | Slice 01, 04, 07 |
| Outputs | JWT auth system, middleware, login page, settings tab, interviews tab, polish components |

**Inputs:**

| Input | Source | Validation |
|-------|--------|------------|
| `users` table (id, email, password_hash, created_at) | Slice 01 | APPROVED |
| `projects` table (user_id FK for owner checks) | Slice 01 | APPROVED |
| `dashboard/lib/api-client.ts` (to extend with auth-aware apiFetch) | Slice 04 | APPROVED |
| `dashboard/app/projects/[id]/page.tsx` (to extend with token prop) | Slice 04 | APPROVED |
| `dashboard/components/EmptyState.tsx` (to extend with more variants) | Slice 04 | APPROVED |
| `dashboard/components/SkeletonCard.tsx` (to extend with more variants) | Slice 04 | APPROVED |
| `useProjectEvents(projectId, token, callbacks)` hook signature | Slice 07 | APPROVED |
| `get_current_user_from_token()` dependency | Slice 07 | APPROVED |
| `GET /api/projects/{id}/events` SSE endpoint | Slice 07 | APPROVED |

**Outputs:**

| Output | Type | Consumers |
|--------|------|-----------|
| `AuthService` (login, decode_token) | Python class | auth_routes.py |
| `get_current_user()` FastAPI dependency | Python function | All backend project/cluster routes |
| `get_current_user_from_token()` FastAPI dependency | Python function | SSE route (existing, from Slice 07) |
| `UserRepository` (get_by_email, get_by_id) | Python class | AuthService |
| `POST /api/auth/login` endpoint | FastAPI endpoint | LoginPage |
| `GET /api/auth/me` endpoint | FastAPI endpoint | Dashboard auth check |
| `middleware.ts` (Next.js route protection) | Next.js middleware | All /projects/* routes |
| `/api/auth/login` Route Handler | Next.js Route Handler | LoginPage |
| `/api/auth/logout` Route Handler | Next.js Route Handler | UserAvatar |
| `/api/proxy/[...path]` Route Handler | Next.js Route Handler | clientFetch (all Client Components) |
| `getAuthToken()` server helper | TypeScript function | Server Components |
| `apiFetch<T>()` (auth-aware, extended) | TypeScript function | Server Components |
| `clientFetch<T>()` (proxy-based, new) | TypeScript function | Client Components |
| `LoginPage` | Next.js page | End users |
| `UserAvatar` component | React component | App layout (all pages) |
| `ErrorBoundary` component | React component | Dashboard pages |
| `EmptyState` (extended: 4 variants) | React component | All tab sections |
| `SkeletonCard`/`SkeletonGrid` (extended) | React component | Loading states |
| `not-found.tsx` | Next.js page | Unknown routes |
| `dashboard/app/projects/[id]/settings/page.tsx` | Next.js page | Settings Tab |
| `SettingsForm`, `ModelConfigForm`, `DangerZone`, `ResetSourceModal` | React components | settings/page.tsx |
| `dashboard/app/projects/[id]/interviews/page.tsx` | Next.js page | Interviews Tab |
| `InterviewsTabClient`, `AssignInterviewsModal` | React components | interviews/page.tsx |
| JWT auth on ALL project/cluster endpoints (via Depends) | Security layer | All routes |

---

## Connections

| # | From | To | Resource | Type | Status |
|---|------|----|----------|------|--------|
| 1 | Slice 01 | Slice 02 | `projects` table (research_goal, extraction_source, model_extraction) | DB Schema | VALID |
| 2 | Slice 01 | Slice 02 | `project_interviews` table (extraction_status) | DB Schema | VALID |
| 3 | Slice 01 | Slice 02 | `facts` table (schema) | DB Schema | VALID |
| 4 | Slice 01 | Slice 02 | `InterviewAssignmentRepository` | Python class | VALID |
| 5 | Slice 01 | Slice 02 | `InterviewAssignment` DTO | Pydantic DTO | VALID |
| 6 | Slice 01 | Slice 03 | `projects`, `clusters`, `facts`, `cluster_suggestions` tables | DB Schema | VALID |
| 7 | Slice 01 | Slice 03 | `ProjectRepository.get_by_id()` | Python method | VALID |
| 8 | Slice 01 | Slice 03 | `project_interviews.clustering_status` | DB field | VALID |
| 9 | Slice 01 | Slice 04 | `GET/POST /api/projects`, `GET /api/projects/{id}` | FastAPI endpoints | VALID |
| 10 | Slice 01 | Slice 08 | `users` table | DB Schema | VALID |
| 11 | Slice 02 | Slice 03 | `FactRepository.get_facts_for_interview/project()` | Python methods | VALID |
| 12 | Slice 02 | Slice 03 | `FactExtractionService` (with `clustering_service` DI param) | Python class | VALID |
| 13 | Slice 02 | Slice 03 | `SseEventBus.publish()` | Python method | VALID |
| 14 | Slice 02 | Slice 07 | `SseEventBus` singleton (subscribe/unsubscribe) | Python class | VALID |
| 15 | Slice 02 | Slice 07 | `fact_extracted` SSE event `{interview_id, fact_count}` | SSE event | VALID |
| 16 | Slice 02 | Slice 08 | `POST /api/projects/{id}/interviews/{iid}/retry` endpoint | FastAPI endpoint | VALID |
| 17 | Slice 03 | Slice 04 | `clusters` table data (via GET /api/projects/{id}/clusters) | DB state + endpoint | VALID |
| 18 | Slice 03 | Slice 05 | `ClusterRepository` (to extend with get_detail) | Python class | VALID |
| 19 | Slice 03 | Slice 05 | `backend/app/clustering/router.py` (file to extend) | Python file | VALID |
| 20 | Slice 03 | Slice 06 | `ClusteringService.full_recluster()` | Python method | VALID |
| 21 | Slice 03 | Slice 06 | `SummaryGenerationService.regenerate_for_cluster()` | Python method | VALID |
| 22 | Slice 03 | Slice 07 | `clustering_started`, `clustering_completed`, `clustering_failed`, `summary_updated` SSE events | SSE events | VALID |
| 23 | Slice 04 | Slice 05 | `dashboard/` App, `api-client.ts`, `types.ts`, `cluster-card.tsx`, `project-tabs.tsx` | Next.js app + components | VALID |
| 24 | Slice 04 | Slice 06 | `apiFetch`, `ClusterResponse`, `ProjectResponse` types | TypeScript | VALID |
| 25 | Slice 04 | Slice 07 | `ClusterCard`, `StatusBar`, `ProjectTabs`, `projects/[id]/page.tsx` | React components + page | VALID |
| 26 | Slice 04 | Slice 08 | `api-client.ts`, `projects/[id]/page.tsx`, `EmptyState`, `SkeletonCard` | Files to extend | VALID |
| 27 | Slice 05 | Slice 06 | `GET /api/projects/{id}/clusters/{cid}` endpoint | FastAPI endpoint | VALID |
| 28 | Slice 05 | Slice 06 | `FactResponse`, `QuoteResponse`, `ClusterDetailResponse` types | TypeScript + Pydantic | VALID |
| 29 | Slice 05 | Slice 06 | `ClusterDetailPage` (with disabled Merge/Split buttons to activate) | Next.js page | VALID |
| 30 | Slice 05 | Slice 06 | `fact-item.tsx` component (to extend with context menu) | React component | VALID |
| 31 | Slice 06 | Slice 08 | All 11 taxonomy backend endpoints | FastAPI endpoints | VALID |
| 32 | Slice 06 | Slice 07 | `SuggestionResponse`, `MergeResponse` TypeScript types | TypeScript types | VALID |
| 33 | Slice 07 | Slice 08 | `GET /api/projects/{id}/events` SSE endpoint | FastAPI endpoint | VALID |
| 34 | Slice 07 | Slice 08 | `useProjectEvents(projectId, token, callbacks)` hook | React hook | VALID |

---

## Validation Results

### Valid Connections: 34

All 34 declared dependencies have matching outputs in approved source slices. No type mismatches detected.

### Orphaned Outputs: 0

All outputs are consumed by at least one downstream slice or represent final user-facing deliverables (pages, endpoints).

| Special Cases | Note |
|---------------|------|
| `FactRepository.reset_cluster_assignments_for_project()` | Internal use within Slice 03 full_recluster — not an orphan |
| `InterviewAssignmentRepository.get_all_for_project()` | Internal use within Slice 03 pipeline — not an orphan |
| `ProgressIndicator` component (Slice 07) | Final user-facing component, no downstream slice consumer — not an orphan |
| `QuoteItem` component (Slice 05) | Consumed internally within ClusterDetailPage in same slice — not an orphan |
| `not-found.tsx` (Slice 08) | Final deliverable, consumed by Next.js runtime — not an orphan |

### Missing Inputs: 0

Every declared input dependency has a matching output in an approved source slice.

### Deliverable-Consumer Gaps: 0

All components have valid mount points within their respective or previously defined page files.

| Connection | Mount Point | Status |
|-----------|-------------|--------|
| `ClusterContextMenu` (Slice 06) consumed in `cluster-card.tsx` | `cluster-card.tsx` is Slice 04 deliverable, Slice 06 modifies it | VALID |
| `InlineRename` (Slice 06) consumed in `cluster-card.tsx` and cluster detail page | Both files exist as prior deliverables | VALID |
| `MergeDialog`, `SuggestionBanner`, `RecalculateModal` consumed in `projects/[id]/page.tsx` | `projects/[id]/page.tsx` is Slice 04 deliverable, Slice 06 extends it | VALID |
| `SplitModal`, `UndoToast`, `BulkMoveBar`, `MergeDialog` consumed in `clusters/[cluster_id]/page.tsx` | `clusters/[cluster_id]/page.tsx` is Slice 05 deliverable, Slice 06 extends it | VALID |
| `FactContextMenu` consumed in `fact-item.tsx` | `fact-item.tsx` is Slice 05 deliverable, Slice 06 extends it | VALID |
| `ProgressIndicator` consumed in `projects/[id]/page.tsx` | `projects/[id]/page.tsx` is Slice 04 deliverable, Slice 07 extends it | VALID |
| `UserAvatar` consumed in app layout | Layout is part of Slice 04 dashboard app, Slice 08 extends it | VALID |
| `SettingsForm`, `ModelConfigForm`, `DangerZone` consumed in `settings/page.tsx` | `settings/page.tsx` is Slice 08 deliverable (new file) | VALID |
| `InterviewsTabClient` consumed in `interviews/page.tsx` | `interviews/page.tsx` is Slice 08 deliverable (new file) | VALID |

---

## Discovery Traceability

### UI Components Coverage

| Discovery Element | Type | Location | Covered In | Status |
|-------------------|------|----------|------------|--------|
| `project_card` | Card | Projekt-Liste | Slice 04 (ProjectCard component) | COVERED |
| `new_project_btn` | Button | Projekt-Liste Toolbar | Slice 04 (NewProjectDialog trigger) | COVERED |
| `project_form` | Form/Modal | Projekt-Liste | Slice 04 (NewProjectDialog) | COVERED |
| `cluster_card` | Card | Insights Tab | Slice 04 (ClusterCard component) | COVERED |
| `cluster_context_menu` | Dropdown | Cluster-Card | Slice 06 (ClusterContextMenu) | COVERED |
| `taxonomy_editor_rename` | Inline Input | Cluster-Card/Detail | Slice 06 (InlineRename) | COVERED |
| `merge_dialog` | Modal | Cluster-Card | Slice 06 (MergeDialog) | COVERED |
| `split_confirm` | Modal | Cluster-Card | Slice 06 (SplitModal Step 1+2) | COVERED |
| `fact_item` | List Item | Cluster-Detail | Slice 05 (FactItem) | COVERED |
| `quote_item` | Blockquote | Cluster-Detail | Slice 05 (QuoteItem) | COVERED |
| `progress_bar` | Status Bar | Insights Tab | Slice 07 (ProgressIndicator) | COVERED |
| `interview_assign_btn` | Button | Interviews Tab | Slice 08 (AssignInterviewsModal trigger) | COVERED |
| `interview_table` | Table | Interviews Tab | Slice 08 (InterviewsTabClient) | COVERED |
| `settings_form` | Form | Einstellungen Tab | Slice 08 (SettingsForm) | COVERED |
| `live_update_badge` | Badge/Dot | Cluster-Card | Slice 07 (ClusterCard hasLiveUpdate) | COVERED |
| `merge_suggestion` | Banner/Card | Insights Tab | Slice 06 (SuggestionBanner) | COVERED |
| `split_suggestion` | Banner/Card | Insights Tab | Slice 06 (SuggestionBanner) | COVERED |
| `recluster_btn` | Button | Insights Tab Toolbar | Slice 06 (RecalculateModal trigger) | COVERED |
| `recluster_confirm` | Modal | Insights Tab | Slice 06 (RecalculateModal) | COVERED |
| `model_config_form` | Form | Einstellungen Tab | Slice 08 (ModelConfigForm) | COVERED |

**UI Components Coverage: 20/20 (100%)**

### State Machine Coverage

| State | Required UI | Available Actions | Covered In | Status |
|-------|-------------|-------------------|------------|--------|
| `no_projects` | Leere Projekt-Liste, Empty State mit CTA | Projekt anlegen | Slice 04 (EmptyState + NewProjectDialog) | COVERED |
| `project_empty` | Projekt ohne Interviews, Empty State | Interviews zuordnen, Einstellungen | Slice 04 (empty clusters state), Slice 08 (Settings/Interviews tabs) | COVERED |
| `project_collecting` | Interviews zugeordnet, Clustering laeuft | Dashboard ansehen (mit Progress) | Slice 07 (ProgressIndicator, isProcessing state) | COVERED |
| `project_ready` | Alle Interviews analysiert, Cluster sichtbar | Dashboard ansehen, Drill-Down, Taxonomy bearbeiten | Slice 04 (ClusterCard grid), Slice 05 (drill-down), Slice 06 (editing) | COVERED |
| `project_updating` | Summary-Regen/Clustering laeuft | Dashboard ansehen (mit Update-Indicator), Read-Only fuer Taxonomy | Slice 07 (live_update_badge, progress) | COVERED |
| `cluster_detail` | Drill-Down in einen Cluster | Facts ansehen, Zitate ansehen, Umbenennen, Zurueck | Slice 05 (ClusterDetailPage) + Slice 06 (editing) | COVERED |
| `extraction_running` | Facts werden extrahiert | Warten (Progress) | Slice 02 (extraction_status='running') + Slice 07 (SSE) | COVERED |
| `extraction_failed` | Fact Extraction fehlgeschlagen, Retry-Button | Retry, Interview ueberspringen | Slice 02 (status='failed' + retry endpoint), Slice 08 (retry_btn in InterviewsTabClient) | COVERED |
| `clustering_running` | Facts werden Clustern zugeordnet | Warten (Progress) | Slice 03 (clustering_status='running') + Slice 07 (SSE) | COVERED |
| `clustering_failed` | Clustering fehlgeschlagen, Error-Banner | Retry, Facts manuell zuordnen | Slice 03 (status='failed'), Slice 07 (Toast), Slice 06 (manual fact moves) | COVERED |

**State Machine Coverage: 10/10 (100%)**

### Transitions Coverage

| From | Trigger | To | Covered In | Status |
|------|---------|-----|------------|--------|
| `no_projects` | Neues Projekt erstellen | `project_empty` | Slice 04 (NewProjectDialog POST + router.refresh) | COVERED |
| `project_empty` | Interviews zuordnen | `project_collecting` | Slice 08 (AssignInterviewsModal), Slice 02 (trigger pipeline) | COVERED |
| `project_empty` | Interview abgeschlossen via Widget | `project_collecting` | Slice 02 (InterviewService.end() hook) | COVERED |
| `project_collecting` | Alle Interviews analysiert | `project_ready` | Slice 07 (clustering_completed → router.refresh, ProgressIndicator hidden) | COVERED |
| `project_collecting` | Neues Interview kommt rein | `project_collecting` | Slice 07 (SSE counter update) | COVERED |
| `project_ready` | Cluster-Card klicken | `cluster_detail` | Slice 05 (ClusterCard as Link) | COVERED |
| `project_ready` | Neues Interview kommt rein | `project_updating` | Slice 07 (live_update_badge) | COVERED |
| `project_ready` | Taxonomy bearbeiten (Merge/Split/Rename) | `project_updating` | Slice 06 (TaxonomyService + Summary Regen) | COVERED |
| `project_updating` | Summary-Regen/Clustering abgeschlossen | `project_ready` | Slice 07 (summary_updated → router.refresh) | COVERED |
| `cluster_detail` | "Zurueck" klicken | `project_ready` | Slice 05 (Back-Link to /projects/{id}) | COVERED |
| `extraction_running` | Extraction erfolgreich | `clustering_running` | Slice 02 (extraction_status='completed'), Slice 03 (DI trigger) | COVERED |
| `extraction_running` | Extraction fehlgeschlagen (3x Retry) | `extraction_failed` | Slice 02 (max_retries=3, status='failed') | COVERED |
| `extraction_failed` | Retry klicken | `extraction_running` | Slice 02 (retry endpoint), Slice 08 (retry_btn UI) | COVERED |
| `clustering_running` | Clustering erfolgreich | `project_ready` | Slice 03 (status='completed'), Slice 07 (SSE clustering_completed) | COVERED |
| `clustering_running` | Clustering fehlgeschlagen (3x Retry) | `clustering_failed` | Slice 03 (max_retries=3, status='failed'), Slice 07 (SSE clustering_failed) | COVERED |

**Transitions Coverage: 15/15 (100%)**

### Business Rules Coverage

| Rule | Covered In | Status |
|------|------------|--------|
| Jedes Projekt hat genau ein Research-Ziel und Prompt-Kontext | Slice 01 (NOT NULL constraint + Pydantic validation) | COVERED |
| Fact-Extraction-Quelle konfigurierbar (Summary/Transcript) | Slice 01 (DB schema) + Slice 02 (process_interview logic) + Slice 08 (SettingsForm) | COVERED |
| Fact-Extraction-Quelle gesperrt nach ersten Facts | Slice 01 (extraction_source_locked logic) + Slice 08 (SettingsForm locked state + ResetSourceModal) | COVERED |
| Ein Interview kann nur einem Projekt zugeordnet werden | Slice 01 (UNIQUE constraint on project_interviews.interview_id + 409 response) | COVERED |
| Facts aus Interview-Text; ein Interview kann mehrere Facts | Slice 02 (list[ExtractedFact] return from extract()) | COVERED |
| Ein Fact gehoert zu genau einem Cluster (oder "unassigned") | Slice 01 (facts.cluster_id nullable FK) + Slice 03 (assignment logic) | COVERED |
| Cluster-Zusammenfassungen automatisch regeneriert bei Aenderung | Slice 06 (SummaryGenerationService.regenerate_for_cluster() nach Merge/Split) | COVERED |
| Cluster-Taxonomie waechst emergent (LLM-gesteuert) | Slice 03 (GENERATE_TAXONOMY_PROMPT + ASSIGN_FACTS_PROMPT) | COVERED |
| Bei Merge: Facts wandern, Quell-Cluster geloescht, Undo-Toast 30s | Slice 06 (TaxonomyService.merge() + undo_merge() + UndoToast) | COVERED |
| Bei Split: LLM teilt Facts in 2+ Sub-Cluster | Slice 06 (TaxonomyService.preview_split() + execute_split()) | COVERED |
| Rename loest KEIN Re-Clustering aus | Slice 06 (TaxonomyService.rename() only updates name, no pipeline trigger) | COVERED |
| Maximale Retry-Anzahl 3 (Extraction + Clustering) | Slice 02 (max_retries=3) + Slice 03 (clustering_max_retries=3) | COVERED |
| Clustering-Pipeline blockiert nicht Interview-Ausfuehrung | Slice 02 (asyncio.create_task fire-and-forget) | COVERED |
| Dashboard erfordert JWT Auth | Slice 07 (SSE auth) + Slice 08 (AuthService + middleware + Depends) | COVERED |
| Inkrementelles Clustering als Default | Slice 03 (mode="incremental" when clusters exist) | COVERED |
| Merge-Vorschlaege bei Aehnlichkeit > 80% | Slice 03 (clustering_merge_similarity_threshold=0.8) | COVERED |
| Split-Vorschlaege bei Cluster > 8 Facts | Slice 03 (SPLIT_SUGGESTION_THRESHOLD=8) | COVERED |
| Full Re-Cluster nur manuell (kein automatischer) | Slice 03 (POST /recluster endpoint only) + Slice 06 (RecalculateModal) | COVERED |
| User kann Facts zwischen Clustern verschieben | Slice 06 (PUT /facts/{fid} + POST /facts/bulk-move + FactContextMenu + BulkMoveBar) | COVERED |
| OpenRouter-Integration mit konfigurierbaren Model-Slugs | Slice 01 (model_* fields in DB) + Slice 08 (ModelConfigForm) | COVERED |
| Login Rate Limiting (5/min per IP) | Slice 08 (_check_rate_limit() in auth_routes.py, 429 response) | COVERED |
| bcrypt cost=12, JWT HS256, 24h lifetime | Slice 08 (AuthService, CryptContext, JWT settings) | COVERED |

**Business Rules Coverage: 22/22 (100%)**

### Data Fields Coverage

| Field | Required | Covered In | Status |
|-------|----------|------------|--------|
| `projects.id` (UUID) | Yes | Slice 01 | COVERED |
| `projects.name` (1-200 chars) | Yes | Slice 01 + Slice 04 + Slice 08 | COVERED |
| `projects.research_goal` (1-2000 chars) | Yes | Slice 01 + Slice 04 | COVERED |
| `projects.prompt_context` (max 5000 chars, optional) | No | Slice 01 + Slice 08 | COVERED |
| `projects.extraction_source` (enum: summary/transcript) | Yes | Slice 01 + Slice 02 + Slice 08 | COVERED |
| `projects.model_interviewer` | No | Slice 01 + Slice 08 | COVERED |
| `projects.model_extraction` | No | Slice 01 + Slice 02 + Slice 08 | COVERED |
| `projects.model_clustering` | No | Slice 01 + Slice 03 + Slice 08 | COVERED |
| `projects.model_summary` | No | Slice 01 + Slice 03 + Slice 08 | COVERED |
| `projects.created_at` | Yes | Slice 01 | COVERED |
| `projects.updated_at` | Yes | Slice 01 | COVERED |
| `projects.user_id` | Yes | Slice 01 + Slice 08 | COVERED |
| `clusters.id` (UUID) | Yes | Slice 01 | COVERED |
| `clusters.project_id` (FK) | Yes | Slice 01 | COVERED |
| `clusters.name` (1-200 chars) | Yes | Slice 01 + Slice 03 + Slice 06 | COVERED |
| `clusters.summary` (nullable) | No | Slice 01 + Slice 03 + Slice 05 + Slice 06 | COVERED |
| `clusters.fact_count` (denormalized) | Yes | Slice 01 + Slice 03 | COVERED |
| `clusters.interview_count` (denormalized) | Yes | Slice 01 + Slice 03 | COVERED |
| `clusters.created_at` | Yes | Slice 01 | COVERED |
| `clusters.updated_at` | Yes | Slice 01 | COVERED |
| `facts.id` (UUID) | Yes | Slice 01 | COVERED |
| `facts.project_id` (FK) | Yes | Slice 01 | COVERED |
| `facts.interview_id` (UUID, no FK) | Yes | Slice 01 + Slice 02 | COVERED |
| `facts.cluster_id` (nullable FK) | No | Slice 01 + Slice 02 + Slice 03 + Slice 06 | COVERED |
| `facts.content` (1-1000 chars) | Yes | Slice 01 + Slice 02 | COVERED |
| `facts.quote` (nullable) | No | Slice 01 + Slice 02 + Slice 05 | COVERED |
| `facts.confidence` (Float 0.0-1.0, nullable) | No | Slice 01 + Slice 02 + Slice 05 | COVERED |
| `facts.created_at` | Yes | Slice 01 | COVERED |
| `project_interviews.project_id` (FK) | Yes | Slice 01 | COVERED |
| `project_interviews.interview_id` (UNIQUE) | Yes | Slice 01 | COVERED |
| `project_interviews.extraction_status` (enum) | Yes | Slice 01 + Slice 02 | COVERED |
| `project_interviews.clustering_status` (enum) | Yes | Slice 01 + Slice 03 | COVERED |
| `project_interviews.assigned_at` | Yes | Slice 01 + Slice 05 (ordering) | COVERED |

**Data Fields Coverage: 33/33 (100%)**

---

## Discovery Coverage Summary

| Category | Covered | Total | Percentage |
|----------|---------|-------|------------|
| UI Components | 20 | 20 | 100% |
| State Machine States | 10 | 10 | 100% |
| Transitions | 15 | 15 | 100% |
| Business Rules | 22 | 22 | 100% |
| Data Fields | 33 | 33 | 100% |
| **TOTAL** | **100** | **100** | **100%** |

---

## Summary

| Metric | Value |
|--------|-------|
| Total Slices | 8 |
| All Slices APPROVED | Yes |
| Total Connections | 34 |
| Valid Connections | 34 |
| Orphaned Outputs | 0 |
| Missing Inputs | 0 |
| Deliverable-Consumer Gaps | 0 |
| Discovery Coverage | 100% |

**Verdict: READY FOR ORCHESTRATION**

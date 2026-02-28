# Orchestrator Configuration: LLM Interview Clustering

**Integration Map:** `integration-map.md`
**E2E Checklist:** `e2e-checklist.md`
**Generated:** 2026-02-28

---

## Pre-Implementation Gates

```yaml
pre_checks:
  - name: "Gate 1: Architecture Compliance"
    file: "specs/phase-4/2026-02-28-llm-interview-clustering/compliance-architecture.md"
    required: "Verdict == APPROVED"
    status: APPROVED

  - name: "Gate 2: All Slices Approved"
    files: "specs/phase-4/2026-02-28-llm-interview-clustering/slices/compliance-slice-*.md"
    required: "ALL Verdict == APPROVED"
    status:
      compliance-slice-01.md: APPROVED (54 Pass, 0 Blocking)
      compliance-slice-02.md: APPROVED (57 Pass, 0 Blocking)
      compliance-slice-03.md: APPROVED (58 Pass, 0 Blocking)
      compliance-slice-04.md: APPROVED (73 Pass, 0 Blocking)
      compliance-slice-05.md: APPROVED (67 Pass, 0 Blocking)
      compliance-slice-06.md: APPROVED (63 Pass, 0 Blocking)
      compliance-slice-07.md: APPROVED (52 Pass, 0 Blocking)
      compliance-slice-08.md: APPROVED (68 Pass, 0 Blocking)

  - name: "Gate 3: Integration Map Valid"
    file: "specs/phase-4/2026-02-28-llm-interview-clustering/integration-map.md"
    required: "Missing Inputs == 0 AND Deliverable-Consumer Gaps == 0"
    status:
      missing_inputs: 0
      orphaned_outputs: 0
      deliverable_consumer_gaps: 0
      discovery_coverage: "100% (100/100)"
      verdict: READY FOR ORCHESTRATION
```

---

## Implementation Order

Based on dependency analysis from `integration-map.md`:

| Order | Slice | Name | Depends On | Parallel With | Stack |
|-------|-------|------|------------|---------------|-------|
| 1 | slice-01 | DB Schema + Projekt CRUD | None | No (foundation) | python-fastapi |
| 2 | slice-02 | Fact Extraction Pipeline | slice-01 | No (serial) | python-fastapi |
| 3 | slice-03 | Clustering Pipeline + Agent | slice-01, slice-02 | No (serial) | python-fastapi |
| 4 | slice-04 | Dashboard: Projekt-Liste + Cluster-Uebersicht | slice-01, slice-02, slice-03 | No (first frontend slice) | typescript-nextjs |
| 5 | slice-05 | Dashboard: Drill-Down + Zitate | slice-01, slice-03, slice-04 | No (extends slice-04 files) | typescript-nextjs |
| 6 | slice-06 | Taxonomy-Editing + Summary-Regen | slice-01, slice-03, slice-05 | No (dual-stack: backend pytest + frontend Playwright) | python-fastapi + typescript-nextjs |
| 7 | slice-07 | Live-Updates via SSE | slice-02, slice-03, slice-04 | No (extends slice-04 files) | typescript-nextjs |
| 8 | slice-08 | Auth + Polish | slice-01, slice-04, slice-07 | No (final integration) | typescript-nextjs |

**Note on parallelism:** Slices 04 and 07 both depend on Slice 03. However, Slice 07 also depends on Slice 04 (extends its page files). Therefore strict serial order is required. Slices 05 and 07 could theoretically run in parallel as they both depend on Slice 04 but not on each other — however Slice 06 depends on Slice 05, making serial order simpler and safer.

---

## Post-Slice Validation

FOR each completed slice, execute the following validation steps in order:

```yaml
validation_steps:

  slice-01:
    deliverables_check:
      - "backend/app/clustering/schemas.py (Pydantic DTOs)"
      - "backend/app/clustering/router.py (ProjectRouter with 10 endpoints)"
      - "backend/app/projects/repository.py (ProjectRepository)"
      - "backend/app/projects/interview_assignment_repository.py"
      - "backend/app/projects/service.py (ProjectService)"
      - "backend/migrations/create_clustering_tables.sql (6 tables)"
      - "backend/tests/slices/llm-interview-clustering/test_slice_01_db_schema_projekt_crud.py"
    test_command: "python -m pytest backend/tests/slices/llm-interview-clustering/test_slice_01_db_schema_projekt_crud.py -v"
    acceptance_command: "python -m pytest backend/tests/slices/llm-interview-clustering/test_slice_01_db_schema_projekt_crud.py -v -k acceptance"
    integration_check:
      - "Run SQL migration against test DB"
      - "Verify 6 tables exist with correct schema"
      - "Verify all 10 API endpoints return correct status codes"
    gate_condition: "All pytest tests pass AND migration runs without errors"

  slice-02:
    deliverables_check:
      - "backend/app/clustering/extraction.py (FactExtractionService)"
      - "backend/app/clustering/fact_repository.py (FactRepository)"
      - "backend/app/clustering/events.py (SseEventBus)"
      - "backend/app/interview/service.py (modified: end() hook)"
      - "backend/app/clustering/router.py (extended: POST .../retry endpoint)"
      - "backend/app/projects/interview_assignment_service.py (retry method)"
      - "backend/app/config/settings.py (extended: 4 new fields)"
      - "backend/tests/slices/llm-interview-clustering/test_slice_02_fact_extraction_pipeline.py"
    test_command: "python -m pytest backend/tests/slices/llm-interview-clustering/test_slice_02_fact_extraction_pipeline.py -v"
    integration_check:
      - "Verify FactExtractionService.process_interview() runs without errors (mocked LLM)"
      - "Verify SseEventBus singleton is accessible"
      - "Verify POST .../retry returns 200 on failed interview"
    gate_condition: "All pytest tests pass"

  slice-03:
    deliverables_check:
      - "backend/app/clustering/service.py (ClusteringService)"
      - "backend/app/clustering/graph.py (ClusteringGraph + ClusteringState)"
      - "backend/app/clustering/cluster_repository.py (ClusterRepository)"
      - "backend/app/clustering/cluster_suggestion_repository.py"
      - "backend/app/clustering/prompts.py (6 prompt templates)"
      - "backend/app/clustering/router.py (extended: POST /recluster, GET /status)"
      - "backend/app/clustering/extraction.py (modified: clustering_service DI param)"
      - "backend/app/config/settings.py (extended: 5 more new fields)"
      - "backend/tests/slices/llm-interview-clustering/test_slice_03_clustering_pipeline_agent.py"
    test_command: "python -m pytest backend/tests/slices/llm-interview-clustering/test_slice_03_clustering_pipeline_agent.py -v"
    integration_check:
      - "Verify ClusteringGraph builds successfully (no LangGraph import errors)"
      - "Verify _route_after_validation returns correct strings for all cases"
      - "Verify POST /recluster returns 200 and 409 for concurrent call"
      - "Verify fact_extracted from Slice 02 triggers clustering_service.process_interview()"
    gate_condition: "All pytest tests pass"

  slice-04:
    deliverables_check:
      - "dashboard/package.json (Next.js 16 + dependencies)"
      - "dashboard/app/layout.tsx"
      - "dashboard/app/projects/page.tsx"
      - "dashboard/app/projects/[id]/page.tsx"
      - "dashboard/app/api/health/route.ts"
      - "dashboard/lib/api-client.ts"
      - "dashboard/lib/types.ts"
      - "dashboard/lib/relative-time.ts"
      - "dashboard/components/cluster-card.tsx"
      - "dashboard/components/project-card.tsx"
      - "dashboard/components/project-tabs.tsx"
      - "dashboard/components/new-project-dialog.tsx"
      - "dashboard/components/empty-state.tsx"
      - "dashboard/components/status-bar.tsx"
      - "dashboard/components/skeleton-card.tsx"
      - "dashboard/globals.css"
      - "dashboard/postcss.config.js"
      - "dashboard/next.config.ts"
      - "dashboard/playwright.config.ts"
      - "tests/slices/llm-interview-clustering/slice-04-dashboard-projekt-cluster-uebersicht.spec.ts"
    test_command: "pnpm --filter dashboard test"
    acceptance_command: "pnpm playwright test tests/slices/llm-interview-clustering/slice-04-dashboard-projekt-cluster-uebersicht.spec.ts"
    integration_check:
      - "GET http://localhost:3001/api/health returns {status: ok}"
      - "Navigate to /projects → project cards load from backend"
      - "Create new project via modal → project appears in list"
      - "Navigate to /projects/{id} → cluster cards load"
    gate_condition: "All Playwright E2E tests pass"

  slice-05:
    deliverables_check:
      - "backend/app/clustering/schemas.py (extended: FactResponse, QuoteResponse, ClusterDetailResponse)"
      - "backend/app/clustering/cluster_repository.py (extended: get_detail method)"
      - "backend/app/clustering/router.py (extended: GET /clusters/{cid})"
      - "dashboard/app/projects/[id]/clusters/[cluster_id]/page.tsx"
      - "dashboard/components/fact-item.tsx"
      - "dashboard/components/quote-item.tsx"
      - "dashboard/components/cluster-detail-skeleton.tsx"
      - "dashboard/components/cluster-card.tsx (modified: Link wrapper)"
      - "dashboard/lib/types.ts (extended: new types)"
      - "dashboard/lib/api-client.ts (extended: getClusterDetail)"
      - "tests/slices/llm-interview-clustering/slice-05-dashboard-drill-down-zitate.spec.ts"
    test_command: "pnpm --filter dashboard test"
    acceptance_command: "pnpm playwright test tests/slices/llm-interview-clustering/slice-05-dashboard-drill-down-zitate.spec.ts"
    integration_check:
      - "Click cluster card → navigates to /projects/{id}/clusters/{cluster_id}"
      - "Cluster detail page shows: name, summary, numbered facts, quotes section"
      - "Facts show Interview badge with correct number"
      - "Back link returns to /projects/{id}"
    gate_condition: "All Playwright E2E tests pass"

  slice-06:
    deliverables_check:
      - "backend/app/clustering/taxonomy_service.py (TaxonomyService)"
      - "backend/app/clustering/exceptions.py (4 custom exceptions)"
      - "backend/app/clustering/router.py (extended: 11 new endpoints)"
      - "backend/app/clustering/schemas.py (extended: 10 new DTOs)"
      - "dashboard/components/cluster-context-menu.tsx"
      - "dashboard/components/inline-rename.tsx"
      - "dashboard/components/merge-dialog.tsx"
      - "dashboard/components/undo-toast.tsx"
      - "dashboard/components/split-modal.tsx"
      - "dashboard/components/suggestion-banner.tsx"
      - "dashboard/components/recalculate-modal.tsx"
      - "dashboard/components/bulk-move-bar.tsx"
      - "dashboard/components/fact-context-menu.tsx"
      - "dashboard/app/projects/[id]/page.tsx (extended: SuggestionBanner, RecalculateModal, BulkMoveBar)"
      - "dashboard/app/projects/[id]/clusters/[cluster_id]/page.tsx (extended: InlineRename, MergeDialog, SplitModal, UndoToast, BulkMoveBar, FactContextMenu)"
      - "dashboard/lib/types.ts (extended: 11 new types)"
      - "dashboard/lib/client-api.ts (11 new API client methods)"
      - "backend/tests/slices/llm-interview-clustering/test_slice_06_taxonomy_service.py"
      - "tests/slices/llm-interview-clustering/slice-06-taxonomy-editing-summary-regen.spec.ts"
    test_command: "python -m pytest backend/tests/slices/llm-interview-clustering/test_slice_06_taxonomy_service.py -v"
    acceptance_command: "pnpm playwright test tests/slices/llm-interview-clustering/slice-06-taxonomy-editing-summary-regen.spec.ts"
    integration_check:
      - "Rename cluster via context menu → name updates, no re-clustering"
      - "Merge two clusters → facts combined, source deleted, Undo Toast appears"
      - "Undo merge within 30s → clusters restored"
      - "Split cluster → preview appears, confirm splits cluster into sub-clusters"
      - "Suggestion banner appears → dismiss or accept works"
      - "Recalculate button → confirmation modal → re-cluster triggers"
    gate_condition: "All pytest backend tests pass AND all Playwright E2E tests pass"

  slice-07:
    deliverables_check:
      - "backend/app/api/sse_routes.py (GET /api/projects/{id}/events SSE endpoint)"
      - "backend/app/main.py (modified: include sse_routes router)"
      - "backend/app/clustering/service.py (modified: publish clustering_progress events)"
      - "dashboard/hooks/useProjectEvents.ts"
      - "dashboard/components/progress-indicator.tsx"
      - "dashboard/components/cluster-card.tsx (extended: hasLiveUpdate prop + live_update_badge)"
      - "dashboard/components/status-bar.tsx (extended: live counter support)"
      - "dashboard/app/projects/[id]/page.tsx (extended: ProjectPageClient with SSE integration)"
      - "tests/slices/llm-interview-clustering/slice-07-live-updates-sse.test.ts"
    test_command: "pnpm --filter dashboard test tests/slices/llm-interview-clustering/slice-07-live-updates-sse.test.ts"
    integration_check:
      - "GET http://localhost:8000/api/projects/{id}/events returns 200 with text/event-stream content-type"
      - "ProgressIndicator renders step label + completed/total counter"
      - "useProjectEvents hook connects to SSE and dispatches callbacks"
      - "EventSource closes on component unmount (no memory leak)"
      - "Reconnect with exponential backoff on onerror"
    gate_condition: "All Vitest unit tests pass AND manual SSE connection test passes"

  slice-08:
    deliverables_check:
      - "backend/app/auth/service.py (AuthService)"
      - "backend/app/auth/middleware.py (get_current_user, get_current_user_from_token)"
      - "backend/app/auth/repository.py (UserRepository)"
      - "backend/app/api/auth_routes.py (POST /login, GET /me with rate limiting)"
      - "backend/app/main.py (modified: include auth_routes, add get_current_user to all project/cluster routes)"
      - "dashboard/middleware.ts"
      - "dashboard/app/login/page.tsx"
      - "dashboard/app/api/auth/login/route.ts"
      - "dashboard/app/api/auth/logout/route.ts"
      - "dashboard/app/api/proxy/[...path]/route.ts"
      - "dashboard/lib/auth.ts (getAuthToken)"
      - "dashboard/lib/api-client.ts (extended: apiFetch with auth)"
      - "dashboard/lib/client-api.ts (new: clientFetch via proxy)"
      - "dashboard/components/user-avatar.tsx"
      - "dashboard/components/error-boundary.tsx"
      - "dashboard/components/skeleton-card.tsx (extended: all 4 variants)"
      - "dashboard/components/empty-state.tsx (extended: all 4 variants)"
      - "dashboard/app/not-found.tsx"
      - "dashboard/app/projects/[id]/settings/page.tsx"
      - "dashboard/components/settings-form.tsx"
      - "dashboard/components/model-config-form.tsx"
      - "dashboard/components/danger-zone.tsx"
      - "dashboard/components/reset-source-modal.tsx"
      - "dashboard/app/projects/[id]/interviews/page.tsx"
      - "dashboard/components/interviews-tab-client.tsx"
      - "dashboard/components/assign-interviews-modal.tsx"
      - "dashboard/app/projects/[id]/page.tsx (extended: token prop for SSE)"
      - "tests/slices/llm-interview-clustering/slice-08-auth-polish.test.ts"
    test_command: "pnpm --filter dashboard test tests/slices/llm-interview-clustering/slice-08-auth-polish.test.ts"
    acceptance_command: "pnpm --filter dashboard test tests/slices/llm-interview-clustering/slice-08-auth-polish.test.ts --reporter=verbose"
    integration_check:
      - "Navigate to /projects without auth → redirect to /login"
      - "POST /api/auth/login with valid creds → 200 + auth_token cookie set"
      - "POST /api/auth/login with invalid creds → 401 + error message"
      - "POST /api/auth/login 6+ times in 1min → 429 rate limit"
      - "All /api/projects/* endpoints return 401 without JWT"
      - "All /api/projects/* endpoints return correct data with valid JWT"
      - "Settings Tab: save general settings → PUT /api/projects/{id} called"
      - "Settings Tab: delete project → DELETE /api/projects/{id} called + redirect"
      - "Interviews Tab: assign modal loads available interviews"
      - "Interviews Tab: retry button triggers POST .../retry for failed interviews"
    gate_condition: "All Vitest unit tests pass AND manual auth flow test passes"
```

---

## E2E Validation

AFTER all 8 slices completed:

```yaml
e2e_validation:
  - step: "Execute e2e-checklist.md"
    reference: "e2e-checklist.md"
    flows:
      - "Flow 1: Auth + Login"
      - "Flow 2: Projekt anlegen"
      - "Flow 3: Interviews Tab + Zuordnen"
      - "Flow 4: Live-Updates waehrend Pipeline"
      - "Flow 5: Cluster-Dashboard ansehen"
      - "Flow 6: Taxonomy bearbeiten — Umbenennen"
      - "Flow 7: Taxonomy bearbeiten — Mergen + Undo"
      - "Flow 8: Taxonomy bearbeiten — Splitten"
      - "Flow 9: Merge/Split Suggestions"
      - "Flow 10: Full Re-Cluster"
      - "Flow 11: Fact verschieben"
      - "Flow 12: Einstellungen Tab"
      - "All Edge Cases"

  - step: "Run all slice test commands"
    commands:
      - "python -m pytest backend/tests/slices/llm-interview-clustering/ -v"
      - "pnpm --filter dashboard test"
      - "pnpm playwright test tests/slices/llm-interview-clustering/"

  - step: "FOR each failing check"
    actions:
      - "Identify responsible slice from integration-map.md Connections table"
      - "Check slice spec for the failing component/endpoint"
      - "Create fix task referencing specific slice ID and AC number"
      - "Re-run affected slice tests after fix"

  - step: "Final Approval"
    condition: "ALL checks in e2e-checklist.md PASS AND all test commands succeed"
    output: "Feature READY for merge to main branch"
```

---

## Critical Implementation Notes

### Dependency Injection Chain (Slice 02 → Slice 03)

The FactExtractionService uses optional DI for ClusteringService. This must be wired correctly in the FastAPI app startup:

```python
# In app/main.py or dependency container:
clustering_service = ClusteringService(...)
fact_extraction_service = FactExtractionService(
    ...,
    clustering_service=clustering_service  # Must be set, not None
)
```

If `clustering_service` is None, extraction completes but clustering never triggers. This is a silent failure.

### SSE Auth Token Flow (Slice 07 → Slice 08)

The SSE endpoint uses JWT as a query parameter (not Authorization header, because EventSource API does not support custom headers). Slice 08 must:

1. Pass the `auth_token` cookie value to the frontend via `getAuthToken()` server helper
2. Pass token to `useProjectEvents(projectId, token, callbacks)` as 2nd parameter
3. Frontend appends `?token=<jwt>` to the EventSource URL

This chain must be intact. If token is undefined, SSE returns 401.

### HttpOnly Cookie + Client Components (Slice 08)

Client Components cannot read HttpOnly cookies directly. The proxy route handler solves this:

```
Client Component → clientFetch('/api/projects/...')
  → /api/proxy/[...path] (Route Handler, runs server-side)
  → reads auth_token cookie
  → forwards request to FastAPI with Authorization: Bearer header
```

If `clientFetch` is mistakenly replaced with direct FastAPI calls in Client Components, auth will fail silently (no Authorization header).

### Tailwind v4 CSS-first (Slice 04)

Dashboard uses Tailwind v4 with CSS-first configuration. Do NOT use v3 syntax:

```js
// WRONG (v3):
module.exports = { plugins: [require('tailwindcss')] }

// CORRECT (v4):
module.exports = { plugins: { '@tailwindcss/postcss': {} } }
```

globals.css must start with `@import "tailwindcss"` (not `@tailwind base/components/utilities`).

### Port Configuration

| Service | Port | Config |
|---------|------|--------|
| Backend (FastAPI) | 8000 | `uvicorn app.main:app --port 8000` |
| Dashboard (Next.js) | 3001 | `dashboard/package.json: "dev": "next dev -p 3001"` |
| Widget (if running) | 5173 | Existing, unchanged |

Note: Slice 07 compliance report mentions port 3000 in Health-Endpoint — use 3001 (established in Slice 04).

---

## Rollback Strategy

IF implementation fails:

```yaml
rollback:
  - condition: "Slice 01 fails (DB migration)"
    action: "Run DOWN migration to revert all 6 tables"
    note: "No other slices depend on code yet — safe rollback"
    command: "psql $DATABASE_URL -f backend/migrations/drop_clustering_tables.sql"

  - condition: "Slice 02 fails"
    action: "Remove extraction.py, fact_repository.py, events.py; revert interview/service.py"
    note: "Slice 01 DB tables remain — no harm"

  - condition: "Slice 03 fails"
    action: "Remove service.py, graph.py, cluster_repository.py, cluster_suggestion_repository.py, prompts.py"
    note: "Revert router.py and extraction.py extensions"

  - condition: "Slice 04 fails (Dashboard)"
    action: "Remove entire dashboard/ directory"
    note: "Backend slices 01-03 remain intact — backend can still be tested independently"

  - condition: "Slice 05 fails"
    action: "Revert cluster-card.tsx to Slice 04 version; remove fact-item.tsx, quote-item.tsx, clusters/[cluster_id]/page.tsx"
    note: "Revert backend router.py and cluster_repository.py extensions"

  - condition: "Slice 06 fails"
    action: "Remove taxonomy_service.py, exceptions.py; revert router.py; remove new frontend components"
    note: "Pages revert to Slice 05 versions (disabled Merge/Split buttons remain)"

  - condition: "Slice 07 fails"
    action: "Remove sse_routes.py, useProjectEvents.ts, ProgressIndicator.tsx; revert ClusterCard/StatusBar/page.tsx to Slice 05/06 versions"
    note: "Dashboard remains functional (static, no live updates)"

  - condition: "Slice 08 fails"
    action: "Remove auth/ module; remove middleware.ts; remove login page, settings/interviews pages; revert api-client.ts"
    note: "Dashboard remains accessible but unprotected (acceptable for dev/staging)"

  - condition: "Integration fails (post-implementation)"
    action: "Review integration-map.md Connections table for the failing connection; check both sides of the connection are implemented"
    note: "Most likely: DI wiring issue (slice-02 → slice-03) or SSE token flow (slice-07 → slice-08)"
```

---

## Monitoring

During implementation:

| Metric | Alert Threshold | Action |
|--------|-----------------|--------|
| Slice completion time | > 4 hours per slice | Review complexity, consider pair programming |
| Test failures | Any blocking failure | Stop, fix immediately, do not proceed to next slice |
| Deliverable missing | Any file from DELIVERABLES_START/END not created | Block slice sign-off |
| Integration test fail | Any failing cross-slice test | Identify connection from integration-map.md, fix both sides |
| SSE connection established | Not connected within 5s | Check CORS config in backend/app/main.py for http://localhost:3001 |
| Database migration error | Any SQL error | Check PostgreSQL version compatibility (gen_random_uuid() requires pgcrypto or PostgreSQL 13+) |

---

## Slice-Specific Implementation Hints

### Slice 01 — DB Schema

- Run migration as first step before any other code
- Verify `gen_random_uuid()` works: `SELECT gen_random_uuid()` in psql
- The `users` table must exist before any auth-related testing in Slice 08

### Slice 02 — Fact Extraction

- The `SseEventBus` must be a FastAPI singleton (registered via `app.state` or `Depends` with singleton scope)
- `InterviewService.end()` modification must be backward-compatible (clustering_service parameter is Optional)

### Slice 03 — Clustering Agent

- LangGraph `StateGraph` requires `langgraph` package in `backend/requirements.txt`
- MAX_CORRECTION_ITERATIONS = 3 is a constant, not a settings field
- The `_running_recluster: set[str]` in ClusteringService must be instance-level, not class-level

### Slice 04 — Dashboard Setup

- `pnpm workspace` setup requires `pnpm-workspace.yaml` at repo root listing `dashboard` as a package
- Tailwind v4 breaks on v3 `darkMode`, `content` config syntax — use pure CSS approach
- `params: Promise<{id: string}>` in page.tsx is Next.js 16 specific (must await params)

### Slice 05 — Drill-Down

- The `interview_number` for facts is computed via ROW_NUMBER in SQL, not stored in DB
- `cache(apiClient.getClusterDetail)` may have `this`-binding issues — use arrow function wrapper instead

### Slice 06 — Taxonomy

- `TaxonomyService` undo mechanism uses in-memory dict — data is lost on server restart (acceptable for MVP)
- Summary regeneration must run as `asyncio.create_task()` (fire-and-forget) to avoid blocking the HTTP response

### Slice 07 — SSE

- Heartbeat every 30s prevents proxy/load-balancer from closing idle connections
- `finally: event_bus.unsubscribe(project_id, queue)` is critical — prevents queue accumulation

### Slice 08 — Auth

- JWT secret must be set via environment variable `JWT_SECRET` (never hardcoded)
- Rate limiter uses in-memory dict — not suitable for multi-process deployments (acceptable for single-server MVP)
- `clientFetch` proxy pattern is mandatory for Client Components — direct FastAPI calls from browser will fail CORS + no auth header

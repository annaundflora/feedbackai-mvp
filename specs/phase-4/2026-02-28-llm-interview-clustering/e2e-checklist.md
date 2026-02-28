# E2E Checklist: LLM Interview Clustering

**Integration Map:** `integration-map.md`
**Generated:** 2026-02-28

---

## Pre-Conditions

- [x] All 8 slices APPROVED (Gate 2)
- [x] Architecture APPROVED (Gate 1)
- [x] Integration Map has no MISSING INPUTS (0 gaps)
- [ ] Backend running: `uvicorn app.main:app --host 0.0.0.0 --port 8000`
- [ ] Dashboard running: `pnpm --filter dashboard dev` (port 3001)
- [ ] Database migrated: all 6 tables exist (users, projects, project_interviews, clusters, facts, cluster_suggestions)
- [ ] At least one user created in `users` table (seeded manually or via admin script)
- [ ] OpenRouter API key configured in backend `.env`

---

## Flow 1: Auth + Login

### Pre-condition: Backend + Dashboard running, user exists in DB

1. [ ] Navigate to `http://localhost:3001/projects` without being logged in
2. [ ] Verify redirect to `/login?from=/projects` (middleware.ts)
3. [ ] Enter invalid credentials → verify error "Sign in failed. Please check your credentials." appears
4. [ ] Enter valid credentials → verify redirect to `/projects`
5. [ ] Verify user avatar with email initials appears in header
6. [ ] Click avatar → click "Log out" → verify redirect to `/login`
7. [ ] Verify `auth_token` cookie is deleted after logout
8. [ ] Verify direct navigation to `/projects` after logout redirects to `/login`

---

## Flow 2: Projekt anlegen (no_projects → project_empty)

### Pre-condition: Logged in, no projects exist

1. [ ] Navigate to `/projects` → verify empty state renders ("Create your first project" CTA)
2. [ ] Verify "Create Project" button is present (`data-testid="empty-state-cta"`)
3. [ ] Click "+ New Project" button → verify modal opens
4. [ ] Verify "Create Project" button in modal is disabled (both Name and Research Goal empty)
5. [ ] Fill in "Project Name" only → verify button still disabled
6. [ ] Fill in "Research Goal" → verify button becomes enabled
7. [ ] Click "Create Project" → verify "Creating..." loading state appears
8. [ ] Verify modal closes after success
9. [ ] Verify new project card appears in project list with correct name
10. [ ] Verify project card shows "0 interviews", "0 clusters", and relative time "Updated just now"
11. [ ] Click project card → verify navigation to `/projects/{id}`

---

## Flow 3: Interviews Tab + Zuordnen (project_empty → project_collecting)

### Pre-condition: Project exists, no interviews assigned, interviews exist in mvp_interviews

1. [ ] Navigate to project detail → verify "Insights" tab is active by default
2. [ ] Verify empty clusters state ("Assign interviews to get started")
3. [ ] Click "Interviews" tab → verify interview table renders (or empty state if none assigned)
4. [ ] Click "+ Assign Interviews" button → verify modal opens
5. [ ] Verify available interviews list loads (interviews not yet assigned to any project)
6. [ ] Select one or more interviews via checkboxes
7. [ ] Verify "X selected" counter updates
8. [ ] Click "Assign Selected" → verify "Assigning..." loading state
9. [ ] Verify modal closes after success
10. [ ] Verify assigned interviews appear in Interviews Tab table with "pending" status badges
11. [ ] Switch to "Insights" tab → verify progress bar appears ("Analyzing...")
12. [ ] Verify `extraction_status` changes to "running" then "analyzed" in Interviews Tab (polling or SSE update)

---

## Flow 4: Live-Updates (SSE) waehrend Fact Extraction + Clustering

### Pre-condition: Interview assigned and pipeline is actively running

1. [ ] On Insights Tab: verify ProgressIndicator shows step label and completed/total counter
2. [ ] Verify StatusBar counters update live (Facts count increases without page reload)
3. [ ] After pipeline completes: verify ProgressIndicator disappears
4. [ ] Verify Cluster-Cards appear in Insights Tab (grid layout, sorted by fact count descending)
5. [ ] Verify each Cluster-Card shows: name, fact count badge, interview count badge, summary preview (max 3 lines)
6. [ ] Verify `live_update_badge` (pulsing blue dot) appears on Cluster-Cards when new facts are added (3s animation then hides)
7. [ ] Verify StatusBar shows correct final counts (N interviews, M facts, K clusters)

---

## Flow 5: Cluster-Dashboard ansehen (project_ready)

### Pre-condition: Project has clusters

1. [ ] Navigate to `/projects/{id}` → verify Insights tab shows Cluster-Card grid
2. [ ] Verify cards sorted by fact count (highest first)
3. [ ] Verify Back-Navigation "← Projects" link navigates to `/projects`
4. [ ] Verify loading skeletons appear briefly while data loads
5. [ ] Click on a Cluster-Card → verify navigation to `/projects/{id}/clusters/{cluster_id}`
6. [ ] Verify Cluster Detail page shows: cluster name (large), Back link, disabled Merge/Split buttons (before Slice 6 activates them), full summary
7. [ ] Verify Facts section with numbered list (1, 2, 3...), Interview badges ("Interview #N"), optional Confidence scores
8. [ ] Verify Quotes section appears only if facts have quotes (hidden if all quotes are null)
9. [ ] Verify Back link returns to `/projects/{id}` (Insights tab)

---

## Flow 6: Taxonomy bearbeiten — Umbenennen

### Pre-condition: Project has clusters

1. [ ] On Insights Tab, click three-dot context menu icon on a Cluster-Card
2. [ ] Verify context menu opens with options: "Rename", "Merge with...", "Split"
3. [ ] Click "Rename" → verify inline input appears with current cluster name
4. [ ] Type new name → press Escape → verify name reverts to original
5. [ ] Type new name → press Enter → verify name updates immediately (optimistic)
6. [ ] Verify `PUT /api/projects/{id}/clusters/{cid}` was called with correct name
7. [ ] Verify NO re-clustering triggered after rename

---

## Flow 7: Taxonomy bearbeiten — Mergen + Undo

### Pre-condition: Project has at least 2 clusters

1. [ ] Open context menu on Cluster-Card → click "Merge with..."
2. [ ] Verify Merge Dialog opens with radio list of other clusters
3. [ ] Verify "Merge Clusters" button is disabled until a target is selected
4. [ ] Select target cluster → verify button becomes enabled
5. [ ] Verify warning text shows "All facts from [source] will be moved to [target]. Undo within 30 seconds."
6. [ ] Click "Merge Clusters" → verify "Merging..." loading state
7. [ ] Verify source cluster disappears from Insights Tab
8. [ ] Verify target cluster fact count increases (facts from source added)
9. [ ] Verify Undo Toast appears with 30-second countdown
10. [ ] Click "Undo" within 30s → verify source cluster is restored with original facts
11. [ ] Verify both cluster summaries are regenerated after undo
12. [ ] Test alternative: let Undo Toast expire → verify toast disappears without undo
13. [ ] Verify cluster summary of merged cluster is automatically regenerated (background task)

---

## Flow 8: Taxonomy bearbeiten — Splitten

### Pre-condition: Project has a cluster with multiple facts

1. [ ] Open context menu on Cluster-Card → click "Split"
2. [ ] Verify Split Modal opens at Step 1 (explanation + "Generate Preview" button)
3. [ ] Click "Cancel" → verify no changes made, modal closes
4. [ ] Re-open Split Modal → click "Generate Preview"
5. [ ] Verify "Analyzing..." spinner appears (LLM generating split preview)
6. [ ] Verify Step 2 appears with proposed sub-clusters: names, complete fact listings per sub-cluster
7. [ ] Review preview → click "Cancel" in Step 2 → verify original cluster unchanged
8. [ ] Re-trigger split → review preview → click "Confirm Split"
9. [ ] Verify original cluster is deleted
10. [ ] Verify new sub-clusters appear in Insights Tab with correct fact counts
11. [ ] Verify summaries are automatically generated for new sub-clusters

---

## Flow 9: Merge/Split Suggestions (LLM-generiert)

### Pre-condition: Pipeline ran and generated suggestions

1. [ ] On Insights Tab: verify Suggestion Banner(s) appear for pending merge/split suggestions
2. [ ] Verify banner shows proposed action and similarity score (for merge)
3. [ ] Click "Dismiss" on a Suggestion Banner → verify banner disappears
4. [ ] Click "Merge" or "Split" on another Suggestion Banner → verify action executes
5. [ ] Verify `POST /api/projects/{id}/suggestions/{sid}/accept` called
6. [ ] Verify `POST /api/projects/{id}/suggestions/{sid}/dismiss` called for dismissed suggestion

---

## Flow 10: Full Re-Cluster

### Pre-condition: Project has clusters

1. [ ] Click "Recalculate" button in Insights Tab toolbar
2. [ ] Verify RecalculateModal opens with impact summary (X clusters, Y facts will be reset)
3. [ ] Click "Cancel" → verify modal closes, no changes
4. [ ] Re-open modal → click "Recalculate All"
5. [ ] Verify `POST /api/projects/{id}/clustering/recluster` called
6. [ ] Verify all cluster assignments reset (facts become unassigned)
7. [ ] Verify progress indicator appears during re-cluster
8. [ ] Verify new cluster structure appears after completion
9. [ ] Attempt second re-cluster while first is running → verify 409 "already running" error

---

## Flow 11: Fact verschieben (einzeln + Bulk)

### Pre-condition: Project has clusters with facts in Cluster Detail

1. [ ] Navigate to Cluster Detail page
2. [ ] Click three-dot icon next to a Fact → verify Fact Context Menu opens
3. [ ] Verify options: "Move to [cluster]..." and "Mark as unassigned"
4. [ ] Click "Move to [cluster]..." → select target cluster → verify fact moves
5. [ ] Verify source cluster fact count decreases, target cluster fact count increases
6. [ ] Click "Mark as unassigned" on another fact → verify fact appears in Unassigned section
7. [ ] On Cluster Detail: check one or more fact checkboxes
8. [ ] Verify Bulk Move Bar appears ("Move selected to cluster" dropdown, visible only when >= 1 checkbox checked)
9. [ ] Select target cluster from dropdown → verify selected facts move in bulk
10. [ ] Verify Bulk Move Bar disappears when no checkboxes are selected

---

## Flow 12: Einstellungen Tab

### Pre-condition: Project exists with facts extracted

1. [ ] Navigate to project → click "Einstellungen" tab
2. [ ] Verify Settings form shows: Project Name, Research Goal, Prompt Context, Extraction Source dropdown
3. [ ] Verify "Save Changes" button is disabled when form is pristine (no changes)
4. [ ] Modify Project Name → verify "Save Changes" button enables
5. [ ] Click "Save Changes" → verify "Saving..." state, then confirmation
6. [ ] Verify `PUT /api/projects/{id}` called with correct data
7. [ ] Verify Extraction Source is locked (lock icon + "Reset & Change Source" link visible) when facts exist
8. [ ] Click "Reset & Change Source" → verify modal opens with new source dropdown and optional re-extract checkbox
9. [ ] Verify warning text: "will only affect future interviews. Existing facts remain unchanged."
10. [ ] Verify Model Config form shows 4 model slug inputs (Interviewer, Extraction, Clustering, Summary)
11. [ ] Modify a model slug → click model save button → verify `PUT /api/projects/{id}/models` called
12. [ ] Click "Delete Project" in Danger Zone → verify confirmation modal opens
13. [ ] Verify Delete button is disabled until exact project name is typed
14. [ ] Type project name → verify Delete button enables (red)
15. [ ] Click Delete → verify `DELETE /api/projects/{id}` called, redirect to `/projects`

---

## Edge Cases

### Error Handling

- [ ] LLM timeout during Fact Extraction (3x retry) → verify `extraction_status="failed"`, error badge in Interviews Tab, Retry button visible
- [ ] LLM timeout during Clustering (3x retry) → verify `clustering_status="failed"`, Toast notification in Dashboard
- [ ] Network error during SSE connection → verify auto-reconnect with exponential backoff (1s, 2s, 4s, max 30s)
- [ ] Navigate away from project dashboard → verify SSE EventSource connection closed (no memory leak)
- [ ] API call returns 401 (token expired) → verify redirect to `/login` for client-side fetch
- [ ] Navigate to non-existent project URL → verify custom 404 page with "Back to Projects" link
- [ ] Child component throws unhandled error → verify ErrorBoundary renders fallback with "Try again" button

### State Transitions

- [ ] `extraction_running` → `extraction_failed` (3 retries exhausted) → verify status badge changes in Interviews Tab
- [ ] `extraction_failed` → `extraction_running` (Retry click) → verify status returns to running state
- [ ] `clustering_running` → `clustering_failed` → verify Toast appears and ProgressIndicator hides
- [ ] `project_ready` → `project_updating` (new interview added) → verify live_update_badge appears
- [ ] `project_updating` → `project_ready` (summary regen complete) → verify update indicator disappears

### Boundary Conditions

- [ ] Cluster with 0 facts → verify empty state "No facts extracted yet." in drill-down
- [ ] Cluster with null summary → verify "Generating summary..." placeholder in ClusterCard
- [ ] All quotes null in a cluster → verify Quotes section completely hidden in Cluster Detail
- [ ] Interview with empty LLM response (0 facts extracted) → verify `extraction_status="completed"`, no facts saved
- [ ] Project with 100+ interviews → verify inkrementelles clustering runs correctly (not full re-cluster)
- [ ] Concurrent re-cluster attempt → verify 409 response and appropriate UI feedback
- [ ] Merge a cluster with itself → verify 400 error "Cannot merge cluster with itself"
- [ ] Split with < 2 sub-clusters in request → verify 400 validation error

---

## Cross-Slice Integration Points

| # | Integration Point | Slices | How to Verify |
|---|-------------------|--------|---------------|
| 1 | InterviewService.end() triggers Fact Extraction | Slice 02 ← backend interview service | Complete an interview via Widget → verify facts appear in DB |
| 2 | Fact Extraction triggers Clustering (DI chain) | Slice 02 → Slice 03 | Complete interview → verify clusters are created after extraction |
| 3 | SSE events flow from pipeline to Dashboard | Slice 02/03 → Slice 07 | Start extraction → verify ProgressIndicator updates live |
| 4 | Cluster data available for Dashboard rendering | Slice 03 → Slice 04 | Run clustering → navigate to Dashboard → verify Cluster-Cards |
| 5 | Cluster detail fetches facts from DB | Slice 01/02 → Slice 05 | Click cluster card → verify facts with correct interview references |
| 6 | TaxonomyService calls SummaryGenerationService | Slice 06 → Slice 03 | Perform merge → verify summary auto-regenerated |
| 7 | SSE token passed to useProjectEvents | Slice 07/08 | Log in → open project dashboard → verify SSE connection established |
| 8 | Auth middleware protects all routes | Slice 08 → all pages | Access any /projects/* URL without auth → verify redirect to /login |
| 9 | clientFetch proxy reads HttpOnly cookie server-side | Slice 08 | Client component action (save settings) → verify API call has correct Authorization header |
| 10 | extraction_source_locked enforced in UI | Slice 01 + Slice 08 | Create project → assign interviews → run extraction → go to Settings → verify source locked |

---

## Test Commands Reference

| Test Target | Command |
|-------------|---------|
| Slice 01 unit tests | `python -m pytest backend/tests/slices/llm-interview-clustering/test_slice_01_db_schema_projekt_crud.py -v` |
| Slice 02 unit tests | `python -m pytest backend/tests/slices/llm-interview-clustering/test_slice_02_fact_extraction_pipeline.py -v` |
| Slice 03 unit tests | `python -m pytest backend/tests/slices/llm-interview-clustering/test_slice_03_clustering_pipeline_agent.py -v` |
| Slice 04 E2E tests | `pnpm playwright test tests/slices/llm-interview-clustering/slice-04-dashboard-projekt-cluster-uebersicht.spec.ts` |
| Slice 05 E2E tests | `pnpm playwright test tests/slices/llm-interview-clustering/slice-05-dashboard-drill-down-zitate.spec.ts` |
| Slice 06 backend tests | `python -m pytest backend/tests/slices/llm-interview-clustering/test_slice_06_taxonomy_service.py -v` |
| Slice 06 E2E tests | `pnpm playwright test tests/slices/llm-interview-clustering/slice-06-taxonomy-editing-summary-regen.spec.ts` |
| Slice 07 unit tests | `pnpm --filter dashboard test tests/slices/llm-interview-clustering/slice-07-live-updates-sse.test.ts` |
| Slice 08 unit tests | `pnpm --filter dashboard test tests/slices/llm-interview-clustering/slice-08-auth-polish.test.ts` |
| All backend integration | `python -m pytest backend/tests/slices/llm-interview-clustering/ -v` |
| All frontend tests | `pnpm --filter dashboard test` |

---

## Sign-Off

| Tester | Date | Result |
|--------|------|--------|
| Orchestrator (automated) | TBD | Pending |
| Manual QA | TBD | Pending |

**Notes:**
- SSE-based flows require actual backend + frontend running simultaneously (cannot be fully mocked in isolation)
- Live-update badge 3s animation requires visual inspection or Playwright `waitForTimeout` assertions
- Port 3001 (Dashboard) must be explicitly configured when running `pnpm --filter dashboard dev`
- Backend E2E tests require real PostgreSQL (test DB) and OpenRouter mock or real API key

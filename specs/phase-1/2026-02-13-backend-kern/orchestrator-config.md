# Orchestrator Configuration: Backend-Kern

**Integration Map:** `integration-map.md`
**E2E Checklist:** `e2e-checklist.md`
**Generated:** 2026-02-13

---

## Pre-Implementation Gates

```yaml
pre_checks:
  - name: "Gate 1: Architecture Compliance"
    file: "compliance-architecture.md"
    required: "Verdict == APPROVED"

  - name: "Gate 2: All Slices Approved"
    files: "slices/compliance-slice-*.md"
    required: "ALL Verdict == APPROVED"
    count: 6

  - name: "Gate 3: Integration Map Valid"
    file: "integration-map.md"
    required: "Missing Inputs == 0, Deliverable-Consumer Gaps == 0, Discovery Coverage == 100%"
```

---

## Implementation Order

Based on dependency analysis from integration-map.md:

| Order | Slice | Name | Depends On | Parallel? |
|-------|-------|------|------------|-----------|
| 1 | 01 | App-Skeleton + DDD-Struktur | -- | No (foundation) |
| 2 | 02 | LangGraph Interview-Graph | Slice 01 | No (core logic) |
| 3 | 03 | SSE-Streaming Endpoints | Slice 01, 02 | No (needs Graph) |
| 4 | 04 | Supabase-Persistenz | Slice 01, 03 | No (needs Service) |
| 5 | 05 | Summary-Generierung + Injection | Slice 02, 04 | No (needs Repository + Graph) |
| 6 | 06 | Session-Timeout + Auto-Summary | Slice 03, 04, 05 | No (needs all above) |

**Parallelisierung:** Keine Parallelisierung moeglich -- strikt sequentielle Dependency-Chain.

**Begruendung:** Jeder Slice erweitert Dateien des vorherigen Slices (MODIFY-Pattern). Slice 03 erweitert Slice 02 Output, Slice 04 erweitert Slice 03 Output, etc. Parallele Implementierung wuerde zu Merge-Konflikten fuehren.

---

## Slice Specifications

### Slice 01: App-Skeleton + DDD-Struktur

```yaml
spec: "slices/slice-01-app-skeleton.md"
compliance: "slices/compliance-slice-01.md"
key_deliverables:
  - "backend/app/main.py"
  - "backend/app/config/settings.py"
  - "backend/app/interview/__init__.py"
  - "backend/app/interview/prompt.py"
  - "backend/app/insights/__init__.py"
  - "backend/app/config/__init__.py"
  - "backend/app/api/__init__.py"
  - "backend/app/db/__init__.py"
  - "backend/.env.example"
validation:
  - "GET /health returns 200 with {status: ok}"
  - "Settings loads all ENV vars with defaults"
  - "DDD folder structure exists"
  - "CORS configured for localhost:3000"
```

### Slice 02: LangGraph Interview-Graph

```yaml
spec: "slices/slice-02-langgraph-interview.md"
compliance: "slices/compliance-slice-02.md"
key_deliverables:
  - "backend/app/interview/graph.py"
  - "backend/app/interview/state.py"
  - "backend/app/interview/prompt.py (MODIFY)"
validation:
  - "InterviewGraph(settings) instantiable"
  - "graph.ainvoke() returns AI response"
  - "graph.astream() yields chunks"
  - "graph.get_history() returns message list"
  - "MemorySaver persists conversation across calls"
  - "PromptAssembler.build() returns system prompt string"
```

### Slice 03: SSE-Streaming Endpoints

```yaml
spec: "slices/slice-03-sse-streaming.md"
compliance: "slices/compliance-slice-03.md"
key_deliverables:
  - "backend/app/interview/service.py"
  - "backend/app/api/routes.py"
  - "backend/app/api/schemas.py"
  - "backend/app/api/dependencies.py"
  - "backend/app/main.py (MODIFY)"
validation:
  - "POST /api/interview/start returns SSE stream + session_id"
  - "POST /api/interview/message returns SSE stream with AI response"
  - "POST /api/interview/end returns JSON with summary placeholder + message_count"
  - "Invalid session_id returns 404"
  - "Empty message returns 400"
  - "Already completed session returns 409"
```

### Slice 04: Supabase-Persistenz

```yaml
spec: "slices/slice-04-supabase-persistenz.md"
compliance: "slices/compliance-slice-04.md"
key_deliverables:
  - "backend/app/db/supabase.py"
  - "backend/app/interview/repository.py"
  - "backend/supabase/migrations/001_create_interviews.sql"
  - "backend/app/interview/service.py (MODIFY)"
  - "backend/app/api/dependencies.py (MODIFY)"
validation:
  - "Supabase Client singleton works"
  - "create_session() inserts row in interviews table"
  - "complete_session() updates status, transcript, summary, completed_at"
  - "increment_message_count() updates message_count + updated_at"
  - "get_recent_summaries() returns last N summaries for anonymous_id"
  - "DB errors are non-blocking (logged, not thrown to client)"
```

### Slice 05: Summary-Generierung + Injection

```yaml
spec: "slices/slice-05-summary-injection.md"
compliance: "slices/compliance-slice-05.md"
key_deliverables:
  - "backend/app/insights/summary.py"
  - "backend/app/interview/graph.py (MODIFY)"
  - "backend/app/interview/service.py (MODIFY)"
  - "backend/app/api/dependencies.py (MODIFY)"
validation:
  - "SummaryService.generate() returns bullet-list string"
  - "POST /end returns real summary (not placeholder)"
  - "Summary saved to Supabase interviews.summary"
  - "POST /start loads last 3 summaries for anonymous_id"
  - "System-Prompt contains injected summaries"
  - "Empty history returns fallback summary"
  - "LLM failure returns fallback summary, session still completed"
```

### Slice 06: Session-Timeout + Auto-Summary

```yaml
spec: "slices/slice-06-session-timeout.md"
compliance: "slices/compliance-slice-06.md"
key_deliverables:
  - "backend/app/interview/timeout.py"
  - "backend/app/interview/service.py (MODIFY)"
  - "backend/app/api/dependencies.py (MODIFY)"
  - "backend/app/main.py (MODIFY)"
validation:
  - "TimeoutManager.register() creates asyncio.Task"
  - "TimeoutManager.reset() restarts timer"
  - "TimeoutManager.cancel() prevents timeout"
  - "TimeoutManager.cancel_all() clears all tasks"
  - "Timeout fires _handle_timeout after SESSION_TIMEOUT_SECONDS"
  - "_handle_timeout generates summary + saves to DB with status=completed_timeout"
  - "Summary failure at timeout: summary=None, session still completed_timeout"
  - "Server shutdown calls cancel_all()"
```

---

## Post-Slice Validation

FOR each completed slice:

```yaml
validation_steps:
  - step: "Deliverables Check"
    action: "Verify all files listed in DELIVERABLES_START/END section exist on disk"
    fail_action: "Report missing file, do not proceed to next slice"

  - step: "Unit Tests"
    action: "Run: pytest backend/tests/slices/backend-kern/test_slice_{NN}_*.py -v"
    fail_action: "Fix failing tests before proceeding"

  - step: "Integration Points"
    action: "Verify outputs accessible by dependent slices (check imports, types, signatures)"
    reference: "integration-map.md -> Connections table"
    fail_action: "Fix interface mismatch"

  - step: "Linting"
    action: "Run: ruff check backend/app/ --select E,F,I"
    fail_action: "Fix lint errors"

  - step: "Type Check"
    action: "Verify Pydantic models, function signatures match spec"
    fail_action: "Fix type mismatches"
```

---

## E2E Validation

AFTER all slices completed:

```yaml
e2e_validation:
  - step: "Run all unit tests"
    command: "pytest backend/tests/slices/backend-kern/ -v --tb=short"
    expected: "All tests pass"

  - step: "Start server"
    command: "cd backend && uvicorn app.main:app --port 8000"
    expected: "Server starts without errors, health check returns 200"

  - step: "Execute e2e-checklist.md"
    substeps:
      - "Happy Path Flow 1: Complete Interview"
      - "Happy Path Flow 2: Summary Injection"
      - "Happy Path Flow 3: New User without Summaries"
      - "Happy Path Flow 4: Session Timeout"
      - "Error Handling scenarios"
      - "State Transitions"
      - "Boundary Conditions"

  - step: "FOR each failing check"
    actions:
      - "Identify responsible slice from Integration Map"
      - "Create fix task with slice reference"
      - "Re-run affected slice tests"
      - "Re-run E2E check"

  - step: "Final Approval"
    condition: "ALL checks in e2e-checklist.md PASS"
    output: "Feature READY for merge"
```

---

## Rollback Strategy

IF implementation fails:

```yaml
rollback:
  - condition: "Slice 01 fails"
    action: "Revert all Slice 01 files"
    impact: "No other slices affected (foundation)"

  - condition: "Slice 02 fails"
    action: "Revert Slice 02 files (graph.py, state.py, prompt.py changes)"
    impact: "Slice 01 remains stable"

  - condition: "Slice 03 fails"
    action: "Revert Slice 03 files (service.py, routes.py, schemas.py, dependencies.py, main.py changes)"
    impact: "Slice 01-02 remain stable"

  - condition: "Slice 04 fails"
    action: "Revert Slice 04 files (supabase.py, repository.py, migration, service.py MODIFYs, dependencies.py MODIFYs)"
    impact: "Slice 01-03 remain stable (API works without DB)"

  - condition: "Slice 05 fails"
    action: "Revert Slice 05 files (summary.py, graph.py MODIFYs, service.py MODIFYs, dependencies.py MODIFYs)"
    impact: "Slice 01-04 remain stable (Interview works with placeholder summary)"

  - condition: "Slice 06 fails"
    action: "Revert Slice 06 files (timeout.py, service.py MODIFYs, dependencies.py MODIFYs, main.py MODIFYs)"
    impact: "Slice 01-05 remain stable (Interview works without timeout management)"

  - condition: "Integration fails"
    action: "Review integration-map.md for interface mismatches"
    note: "Most likely cause: function signature mismatch between slices"
```

---

## Monitoring

During implementation:

| Metric | Alert Threshold |
|--------|-----------------|
| Slice completion time | > 2x estimate |
| Test failures per slice | > 0 blocking |
| Deliverable missing | Any file from DELIVERABLES list |
| Integration test fail | Any cross-slice import or type error |
| Lint errors | > 0 (E, F, I categories) |

---

## Estimated Effort

| Slice | Estimated Effort | Complexity |
|-------|-----------------|------------|
| 01 App-Skeleton | Low | Boilerplate + Config |
| 02 LangGraph Graph | Medium | Core LLM integration |
| 03 SSE-Streaming | Medium | SSE + Service Layer |
| 04 Supabase-Persistenz | Medium | DB + Migration + DI |
| 05 Summary-Injection | Medium-High | LLM Call + Prompt Assembly + DI |
| 06 Session-Timeout | Medium | asyncio Tasks + Error Handling |

**Total:** 6 slices, strictly sequential, no parallelization possible.

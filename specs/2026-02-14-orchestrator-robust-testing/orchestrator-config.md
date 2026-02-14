# Orchestrator Configuration: Lean Testing Pipeline for Agentic Development

**Integration Map:** `integration-map.md`
**E2E Checklist:** `e2e-checklist.md`
**Generated:** 2026-02-14

---

## Pre-Implementation Gates

```yaml
pre_checks:
  - name: "Gate 1: Architecture Compliance"
    file: "compliance-architecture.md"
    required: "Verdict == APPROVED"
    notes: "Architecture defines all Agent Interfaces, State Machine, Evidence Format, Stack-Detection Matrix"

  - name: "Gate 2: All Slices Approved"
    files:
      - "compliance-slice-01.md"
      - "compliance-slice-02.md"
      - "compliance-slice-03.md"
      - "compliance-slice-04.md"
    required: "ALL Verdict == APPROVED"
    notes: "All 4 slices passed inhaltliche Pruefung by Gate 2 agent"

  - name: "Gate 3: Integration Map Valid"
    file: "integration-map.md"
    required: "Verdict == READY FOR ORCHESTRATION"
    conditions:
      - "Missing Inputs == 0"
      - "Deliverable-Consumer Gaps == 0"
      - "Discovery Coverage == 100%"
    notes: "All dependencies satisfied, no orphaned outputs, full traceability"
```

---

## Implementation Order

Based on dependency analysis from integration-map.md:

| Order | Slice | Name | Depends On | Parallel? | Wave |
|-------|-------|------|------------|-----------|------|
| 1 | slice-01-test-writer-enhancement | Test-Writer Agent Enhancement | -- | No (foundation) | 1 |
| 2 | slice-02-test-validator-agent | Test-Validator Agent | slice-01 | Yes with slice-04 | 2 |
| 2 | slice-04-planner-gate-improvements | Planner & Gate Improvements | slice-01 | Yes with slice-02 | 2 |
| 3 | slice-03-orchestrator-pipeline | Orchestrator Pipeline | slice-01, slice-02 (implicitly slice-04) | No (integration) | 3 |

**Rationale:**
- **Wave 1 (Slice 01):** Foundation slice, no dependencies. Must run first.
- **Wave 2 (Slices 02 + 04):** Both depend only on Slice 01. Can run in parallel.
  - Slice 02: Test-Validator Agent (consumes Test-File-Naming from Slice 01)
  - Slice 04: Planner & Gate Improvements (consumes Stack-Detection Matrix from Slice 01)
- **Wave 3 (Slice 03):** Orchestrator Pipeline (consumes Agent Definitions from Slices 01, 02 and Test-Strategy format from Slice 04). Must run last.

**Parallelization Config:**
```yaml
waves:
  - id: 1
    slices:
      - id: slice-01-test-writer-enhancement
        parallel: false
  - id: 2
    slices:
      - id: slice-02-test-validator-agent
        parallel: true
      - id: slice-04-planner-gate-improvements
        parallel: true
  - id: 3
    slices:
      - id: slice-03-orchestrator-pipeline
        parallel: false
```

---

## Post-Slice Validation

FOR each completed slice:

```yaml
validation_steps:
  - step: "1. Deliverables Check"
    action: "Verify all files in DELIVERABLES_START...DELIVERABLES_END exist"
    reference: "slice-{NN}-{name}.md DELIVERABLES section"

  - step: "2. Unit Tests"
    action: "Task(test-validator) with mode: slice_validation"
    input:
      - "Test-Paths: tests/unit/, tests/integration/, tests/acceptance/"
      - "Previous-Slice-Tests: [all completed slice test paths]"
      - "Mode: slice_validation"
      - "Working-Directory: backend"
    expected_output: "overall_status: passed"

  - step: "3. Integration Points Verification"
    action: "Verify outputs accessible by dependent slices"
    reference: "integration-map.md → Connections table"
    examples:
      - "Slice 01 provides Test-Writer Agent Definition → Verify .claude/agents/test-writer.md exists and has JSON Output Contract section"
      - "Slice 02 provides Test-Validator Agent Definition → Verify .claude/agents/test-validator.md exists and has all 5 stages"
      - "Slice 03 provides Orchestrator Command → Verify .claude/commands/orchestrate.md exists and has 4-Sub-Agent-Steps"
      - "Slice 04 provides plan-spec Template with Test-Strategy → Verify .claude/templates/plan-spec.md has Test-Strategy section with 7 fields"

  - step: "4. Smoke Test"
    action: "Part of test-validator Stage 4"
    expected_output:
      - "stages.smoke.app_started: true"
      - "stages.smoke.health_status: 200"
      - "stages.smoke.startup_duration_ms: < 30000"

  - step: "5. Regression Test"
    action: "Part of test-validator Stage 5"
    expected_output:
      - "stages.regression.exit_code: 0"
      - "stages.regression.slices_tested: [all previous slice IDs]"
```

---

## E2E Validation

AFTER all slices completed:

```yaml
e2e_validation:
  - step: "Execute e2e-checklist.md"
    action: "Manual execution of all Happy Path and Edge Case scenarios"
    reference: "e2e-checklist.md"

  - step: "Cross-Slice Integration Points"
    action: "Verify all 10 integration points from e2e-checklist.md"
    critical_points:
      - "Test-Writer Agent Definition consumed by Orchestrator (Slice 01 → Slice 03)"
      - "Test-Validator Agent Definition consumed by Orchestrator (Slice 02 → Slice 03)"
      - "Test-File-Naming Convention used by Test-Validator (Slice 01 → Slice 02)"
      - "Stack-Detection Matrix consistency (Slice 01 → Slice 04)"
      - "Orchestrator Pipeline consumes Test-Strategy Metadata (Slice 03 → Slice 04)"
      - "Evidence Format used by all slices (Slice 03 → All)"
      - "JSON Output Contracts parsed by Orchestrator (Slices 01, 02 → Slice 03)"
      - "Stage-Skip-Semantik used by Orchestrator (Slice 02 → Slice 03)"
      - "Slice-Implementer JSON Contract with commit_hash (Slice 03)"
      - "plan-spec Template with Test-Strategy (Slice 04 → Future)"

  - step: "Discovery Traceability Validation"
    action: "Verify 100% coverage from integration-map.md"
    checks:
      - "State Machine Coverage: 9/9 states"
      - "Transitions Coverage: 16/16 transitions"
      - "Business Rules Coverage: 17/17 rules"
      - "Data Fields Coverage: 40/40 fields"

  - step: "FOR each failing check"
    actions:
      - "Identify responsible slice from Integration Map"
      - "Create fix task with slice reference"
      - "Re-run affected slice tests"

  - step: "Final Approval"
    condition: "ALL checks in e2e-checklist.md PASS"
    output: "Feature READY for merge"
```

---

## Rollback Strategy

IF implementation fails:

```yaml
rollback:
  - condition: "Slice N fails (Implementer or Test-Writer returns status: failed)"
    action: "HARD STOP - Spec problem, not auto-fixable"
    recovery: "Review slice-{N}-{name}.md for unclear requirements or missing architecture details"
    note: "Dependencies are stable, no rollback needed"

  - condition: "Slice N validation fails (Test-Validator returns overall_status: failed, retries < 3)"
    action: "Task(debugger) fixes code → Re-validate"
    recovery: "Automatic via Retry Loop (max 3 retries)"
    note: "Debugger fixes code, not tests (tests are Ground Truth)"

  - condition: "Slice N validation fails after 3 retries"
    action: "HARD STOP - Manual intervention required"
    recovery: "Review test failures, identify root cause, fix manually, then resume orchestration"
    note: "State saved in .orchestrator-state.json, resume possible"

  - condition: "Integration test fails (cross-slice dependency)"
    action: "Review integration-map.md for gaps"
    recovery: "Identify which Output is missing or incorrect, fix responsible slice"
    note: "May need slice spec updates if Output Contract is incomplete"

  - condition: "JSON Parse Failure (any sub-agent)"
    action: "HARD STOP - Agent definition error"
    recovery: "Review agent .md file for JSON Output Contract section, ensure letzten ```json``` block is valid"
    note: "No retry, fix agent definition and restart from failed slice"

  - condition: "Final Validation fails (Lint, Type, Build, Full Smoke, Full Regression)"
    action: "Task(debugger) fixes → Re-validate (max 3 retries)"
    recovery: "Automatic via Retry Loop"
    note: "If 3 retries exhausted: HARD STOP, manual fix required"
```

---

## Monitoring

During implementation:

| Metric | Alert Threshold | Source | Action |
|--------|----------------|--------|--------|
| Slice completion time | > 2x estimate (estimate: 30 min per slice) | Orchestrator timestamps | Investigate bottleneck (slow tests? complex code?) |
| Test failures | > 0 blocking | Test-Validator output | Debugger auto-fix, monitor retry count |
| Retry count | >= 2 | Orchestrator state | Warning: approaching max retries |
| Retry count | == 3 | Orchestrator state | HARD STOP imminent, prepare manual intervention |
| Deliverable missing | Any | Deliverables Check | HARD STOP, review slice spec Deliverables section |
| Integration test fail | Any | Test-Validator Regression stage | Debugger auto-fix, may indicate breaking change |
| Smoke test timeout | > 30s | Test-Validator Smoke stage | Check for port conflicts, hanging processes |
| AC-Coverage | < 100% | Test-Writer output | HARD STOP, review slice spec ACs for completeness |
| JSON Parse Failure | Any | Orchestrator JSON-Parsing helper | HARD STOP, fix agent definition |

---

## Feature-Specific Notes

### Agent Infrastructure Considerations

This feature modifies Agent Definitions and Command files, NOT application code. Special considerations:

1. **No Database Migrations:** All changes are in `.claude/` directory, no DB changes
2. **No API Changes:** No HTTP endpoints, only Agent-to-Agent JSON contracts
3. **No UI Changes:** Agent Infrastructure, no frontend components
4. **Markdown Validation Tests:** Acceptance tests validate Markdown file structure, not executable code
5. **Health Endpoint:** Existing `GET /health` endpoint must remain functional throughout (backend/app/main.py)

### Stack-Detection Dependency

This feature introduces Stack-Detection across multiple agents:
- Test-Writer (Slice 01)
- Test-Validator (Slice 02)
- Slice-Writer (Slice 04)

**Critical:** All three agents MUST use identical Stack-Detection Matrix (defined in architecture.md Lines 293-299):
- Python/FastAPI (pyproject.toml + fastapi)
- Python/FastAPI (requirements.txt + fastapi)
- Python/Django (pyproject.toml + django)
- TypeScript/Next.js (package.json + next)
- TypeScript/Express (package.json + express)
- Go (go.mod)

**Verification:** Cross-check Stack-Detection tables in all three agent definitions during implementation.

### JSON Output Contracts

All sub-agents MUST return JSON in letzten ```json``` block. Orchestrator has no fallback if format is wrong.

**Critical Contracts:**
- Slice-Implementer: `{ status, files_changed, commit_hash, notes }` (commit_hash, not commit_message!)
- Test-Writer: `{ status, test_files, test_count{unit,integration,acceptance}, ac_coverage{total,covered,missing}, commit_hash }`
- Test-Validator: `{ overall_status, stages{unit,integration,acceptance,smoke,regression}, failed_stage?, error_output? }`
- Debugger: `{ status, root_cause, files_changed, commit_hash }` (no changes, existing debugger.md)

### Evidence Format

All slices produce evidence with NEW format (Slice 03 defines this):
```json
{
  "feature": "orchestrator-robust-testing",
  "slice": "slice-{NN}-{name}",
  "timestamp": "ISO 8601",
  "status": "completed | failed",
  "implementation": { ... },
  "tests": { ... },
  "validation": { ... },
  "retries": 0
}
```

Old evidence format (only `unit_test` section) is REPLACED.

### Smoke Test Requirements

- Health-Endpoint MUST return HTTP 200 within 30 seconds
- Health-Endpoint MUST NOT require external services (no DB check, no API check)
- Existing health endpoint: `backend/app/main.py` Line 40: `@app.get("/health")` returns `{"status": "ok"}`
- Smoke Test MUST kill app process after check (no orphan processes)

### Regression Test Requirements

- ALLE vorherigen Slice-Tests werden re-run (no smart selection in MVP)
- Regression failures indicate breaking changes → Debugger must fix
- First slice has no regression (slices_tested: [])

---

## Success Criteria

Feature is considered successfully implemented when:

- [ ] All 4 slices have status: completed in evidence files
- [ ] All 40 acceptance tests pass (8 + 9 + 13 + 10)
- [ ] Full Regression passes (all 40 tests from all slices)
- [ ] Final Validation passes (Lint, Type, Build, Full Smoke, Full Regression)
- [ ] Integration Map verified: 8 connections valid, 0 missing inputs, 0 gaps
- [ ] E2E Checklist: All Happy Path scenarios executed successfully
- [ ] E2E Checklist: All Edge Cases handled correctly
- [ ] Discovery Traceability: 100% coverage (9 states, 16 transitions, 17 rules, 40 fields)
- [ ] No HARD STOP occurred (or if occurred, was manually resolved and orchestration resumed)
- [ ] Feature branch ready for PR to main

---

## Post-Implementation Actions

After successful orchestration:

1. **Merge Strategy:**
   - Create PR: `feature/orchestrator-robust-testing` → `main`
   - PR Description: Link to `specs/2026-02-14-orchestrator-robust-testing/` folder
   - Include evidence files in PR description (links to `.claude/evidence/orchestrator-robust-testing/*.json`)
   - Include integration-map.md and e2e-checklist.md sign-off

2. **Validation Before Merge:**
   - Re-run Full Regression on main branch (ensure no conflicts with other features)
   - Smoke Test on main branch
   - Verify no existing features broken

3. **Documentation Updates:**
   - Update `.claude/README.md` if exists (document new 4-Sub-Agent-Pipeline)
   - Update Agent Index if exists (list all agents with brief descriptions)

4. **Next Steps:**
   - This feature enables robust testing for ALL future features
   - Next features can use enhanced test-writer.md, test-validator.md, orchestrate.md
   - Gate 2 now performs inhaltliche Pruefung (catches low-quality ACs early)
   - Planner now generates Test-Strategy Metadata automatically

---

## Contact & Escalation

| Issue Type | Contact | Escalation Path |
|------------|---------|-----------------|
| Spec Ambiguity | Review `specs/2026-02-14-orchestrator-robust-testing/discovery.md` Q&A Log | Ask User via AskUserQuestion |
| Architecture Violation | Review `architecture.md` | HARD STOP, fix spec |
| Integration Gap | Review `integration-map.md` Validation Results | Fix responsible slice |
| Test Failure (> 3 retries) | Review `e2e-checklist.md` Edge Cases | Manual debugging, analyze error_output |
| Agent Definition Error | Review `.claude/agents/{agent-name}.md` | Fix agent definition, restart from failed slice |

---

## Appendix: File Manifest

All files involved in this feature implementation:

### Modified Files (7)
1. `.claude/agents/test-writer.md` (Slice 01) - Enhanced with AC-generation and stack-detection
2. `.claude/agents/test-validator.md` (Slice 02) - NEW FILE, created in this feature
3. `.claude/commands/orchestrate.md` (Slice 03) - Completely replaced with 4-Sub-Agent-Pipeline
4. `.claude/agents/slice-implementer.md` (Slice 03) - Modified: removed "Tests schreiben" rule, added "NUR Code" rule
5. `.claude/agents/slice-writer.md` (Slice 04) - Enhanced with stack-detection and Test-Strategy generation
6. `.claude/agents/slice-compliance.md` (Slice 04) - Modified: replaced Template-Compliance with Inhaltliche Pruefung
7. `.claude/templates/plan-spec.md` (Slice 04) - Modified: added Test-Strategy section with 7 fields

### New Test Files (4)
1. `tests/acceptance/test_slice_01_test_writer_enhancement.py` - 8 tests
2. `tests/acceptance/test_slice_02_test_validator_agent.py` - 9 tests
3. `tests/acceptance/test_slice_03_orchestrator_pipeline.py` - 13 tests
4. `tests/acceptance/test_slice_04_planner_gate_improvements.py` - 10 tests

### Evidence Files (5)
1. `.claude/evidence/orchestrator-robust-testing/slice-01.json`
2. `.claude/evidence/orchestrator-robust-testing/slice-02.json`
3. `.claude/evidence/orchestrator-robust-testing/slice-03.json`
4. `.claude/evidence/orchestrator-robust-testing/slice-04.json`
5. `.claude/evidence/orchestrator-robust-testing/feature.json` (final validation)

### State File (1)
1. `specs/2026-02-14-orchestrator-robust-testing/.orchestrator-state.json`

**Total Files Modified/Created:** 17

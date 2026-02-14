# E2E Checklist: Lean Testing Pipeline for Agentic Development

**Integration Map:** `integration-map.md`
**Generated:** 2026-02-14

---

## Pre-Conditions

- [ ] All slices APPROVED (Gate 2)
  - [ ] `slices/compliance-slice-01.md` → Verdict: APPROVED
  - [ ] `slices/compliance-slice-02.md` → Verdict: APPROVED
  - [ ] `slices/compliance-slice-03.md` → Verdict: APPROVED
  - [ ] `slices/compliance-slice-04.md` → Verdict: APPROVED
- [ ] Architecture APPROVED (Gate 1)
  - [ ] `architecture.md` exists and defines all Agent Interfaces, State Machine, Evidence Format
- [ ] Integration Map has no MISSING INPUTS
  - [ ] `integration-map.md` → Verdict: READY FOR ORCHESTRATION

---

## Happy Path Tests

### Flow 1: Slice 01 Implementation (Test-Writer Enhancement)

**Pre-Condition:** Repo has existing test-writer.md

1. [ ] **Slice 01 - Implementer:** Reads existing `.claude/agents/test-writer.md`
2. [ ] **Slice 01 - Implementer:** Extends agent with Stack-Detection Section (Lines 500-511 in spec)
3. [ ] **Slice 01 - Implementer:** Extends agent with AC-Test-Generation Section (Lines 520-634 in spec)
4. [ ] **Slice 01 - Implementer:** Extends agent with JSON Output Contract Section (Lines 568-602 in spec)
5. [ ] **Slice 01 - Implementer:** Commits with `feat(slice-01): Enhance test-writer with AC-generation and stack-detection`
6. [ ] **Slice 01 - Test-Writer:** Creates `tests/acceptance/test_slice_01_test_writer_enhancement.py` with 8 AC tests
7. [ ] **Slice 01 - Test-Writer:** Commits with `test(slice-01): Add acceptance tests for test-writer enhancement`
8. [ ] **Slice 01 - Test-Validator:** Runs Unit Tests → 0 tests (no unit tests for markdown file)
9. [ ] **Slice 01 - Test-Validator:** Runs Integration Tests → 0 tests (no integration tests for markdown file)
10. [ ] **Slice 01 - Test-Validator:** Runs Acceptance Tests → 8 passed (validates markdown structure)
11. [ ] **Slice 01 - Test-Validator:** Smoke Test → App starts, health returns 200
12. [ ] **Slice 01 - Test-Validator:** Regression → No previous slices, 0 tests
13. [ ] **Slice 01 - Evidence:** Saved to `.claude/evidence/orchestrator-robust-testing/slice-01.json` with all sections

**Expected Result:** Slice 01 complete, Test-Writer agent enhanced with AC-generation and stack-detection

---

### Flow 2: Slice 02 Implementation (Test-Validator Agent)

**Pre-Condition:** Slice 01 complete, test-writer.md enhanced

1. [ ] **Slice 02 - Implementer:** Creates `.claude/agents/test-validator.md` (new file)
2. [ ] **Slice 02 - Implementer:** Adds Stack-Detection Matrix (identical to test-writer.md)
3. [ ] **Slice 02 - Implementer:** Adds 5 Test Stages (Unit, Integration, Acceptance, Smoke, Regression)
4. [ ] **Slice 02 - Implementer:** Adds Smoke Test logic (Start, Poll 30s, Check 200, Kill PID)
5. [ ] **Slice 02 - Implementer:** Adds JSON Output Contract with all stage fields
6. [ ] **Slice 02 - Implementer:** Commits with `feat(slice-02): Add test-validator agent`
7. [ ] **Slice 02 - Test-Writer:** Uses Test-File-Naming Convention from Slice 01 (tests/acceptance/)
8. [ ] **Slice 02 - Test-Writer:** Creates `tests/acceptance/test_slice_02_test_validator_agent.py` with 9 AC tests
9. [ ] **Slice 02 - Test-Writer:** Commits with `test(slice-02): Add acceptance tests for test-validator agent`
10. [ ] **Slice 02 - Test-Validator:** Runs Acceptance Tests → 9 passed (validates markdown structure)
11. [ ] **Slice 02 - Test-Validator:** Smoke Test → App starts, health returns 200
12. [ ] **Slice 02 - Test-Validator:** Regression → Runs Slice 01 tests → 8 passed
13. [ ] **Slice 02 - Evidence:** Saved with regression.slices_tested = ["slice-01"]

**Expected Result:** Slice 02 complete, Test-Validator agent created with 5-stage pipeline

---

### Flow 3: Slice 03 Implementation (Orchestrator Pipeline)

**Pre-Condition:** Slices 01 and 02 complete, test-writer.md and test-validator.md exist

1. [ ] **Slice 03 - Implementer:** Reads existing `.claude/commands/orchestrate.md`
2. [ ] **Slice 03 - Implementer:** Replaces entire file with new 4-Sub-Agent-Pipeline structure
3. [ ] **Slice 03 - Implementer:** Adds Pre-Impl Sanity Check (compliance-slice-*.md + APPROVED)
4. [ ] **Slice 03 - Implementer:** Adds JSON-Parsing Helper Function (parse_agent_json)
5. [ ] **Slice 03 - Implementer:** Adds 4 Steps: Task(implementer) → Task(test-writer) → Task(test-validator) → Task(debugger)
6. [ ] **Slice 03 - Implementer:** Adds Retry Loop with MAX_RETRIES = 3
7. [ ] **Slice 03 - Implementer:** Adds Evidence Format with implementation/tests/validation/retries sections
8. [ ] **Slice 03 - Implementer:** Modifies `.claude/agents/slice-implementer.md` (removes "Tests schreiben" rule)
9. [ ] **Slice 03 - Implementer:** Adds "NUR Code, KEINE Tests" rule to slice-implementer.md
10. [ ] **Slice 03 - Implementer:** Changes slice-implementer JSON contract (commit_message → commit_hash)
11. [ ] **Slice 03 - Implementer:** Commits with `feat(slice-03): Rebuild orchestrator pipeline with 4-sub-agent-steps`
12. [ ] **Slice 03 - Test-Writer:** Consumes Test-Writer Agent Definition from Slice 01 (can parse JSON output)
13. [ ] **Slice 03 - Test-Writer:** Consumes Test-Validator Agent Definition from Slice 02 (can parse JSON output)
14. [ ] **Slice 03 - Test-Writer:** Creates `tests/acceptance/test_slice_03_orchestrator_pipeline.py` with 13 AC tests
15. [ ] **Slice 03 - Test-Writer:** Commits with `test(slice-03): Add acceptance tests for orchestrator pipeline`
16. [ ] **Slice 03 - Test-Validator:** Runs Acceptance Tests → 13 passed (validates markdown structure + JSON contracts)
17. [ ] **Slice 03 - Test-Validator:** Smoke Test → App starts, health returns 200
18. [ ] **Slice 03 - Test-Validator:** Regression → Runs Slice 01+02 tests → 17 passed (8+9)
19. [ ] **Slice 03 - Evidence:** Saved with regression.slices_tested = ["slice-01", "slice-02"]

**Expected Result:** Slice 03 complete, Orchestrator rebuilt with 4-step pipeline, slice-implementer.md modified

---

### Flow 4: Slice 04 Implementation (Planner & Gate Improvements)

**Pre-Condition:** Slices 01, 02, 03 complete, orchestrator pipeline rebuilt

1. [ ] **Slice 04 - Implementer:** Reads existing `.claude/agents/slice-writer.md`
2. [ ] **Slice 04 - Implementer:** Adds Stack-Detection Section (uses same matrix as test-writer.md from Slice 01)
3. [ ] **Slice 04 - Implementer:** Adds Test-Strategy Metadata Generation Section
4. [ ] **Slice 04 - Implementer:** Extends Workflow Phase 2 with Stack-Detection as first step
5. [ ] **Slice 04 - Implementer:** Modifies `.claude/agents/slice-compliance.md`
6. [ ] **Slice 04 - Implementer:** Replaces "Template-Compliance" with "Inhaltliche Pruefung" (AC-Qualitaets-Check)
7. [ ] **Slice 04 - Implementer:** Adds Code Example Korrektheit Check (Types/Interfaces vs architecture.md)
8. [ ] **Slice 04 - Implementer:** Adds Test-Strategy Pruefung (Stack, Commands, Health-Endpoint)
9. [ ] **Slice 04 - Implementer:** Adds Max 1 Retry Rule to slice-compliance.md
10. [ ] **Slice 04 - Implementer:** Modifies `.claude/templates/plan-spec.md`
11. [ ] **Slice 04 - Implementer:** Adds Test-Strategy Section with 7 fields (after Metadata, before Slice-Uebersicht)
12. [ ] **Slice 04 - Implementer:** Commits with `feat(slice-04): Enhance planner with stack-detection and gate-2-improvements`
13. [ ] **Slice 04 - Test-Writer:** Uses Orchestrator Pipeline from Slice 03 (consumes Test-Strategy Metadata format)
14. [ ] **Slice 04 - Test-Writer:** Creates `tests/acceptance/test_slice_04_planner_gate_improvements.py` with 10 AC tests
15. [ ] **Slice 04 - Test-Writer:** Commits with `test(slice-04): Add acceptance tests for planner improvements`
16. [ ] **Slice 04 - Test-Validator:** Runs Acceptance Tests → 10 passed (validates markdown structure + Stack-Detection matrix)
17. [ ] **Slice 04 - Test-Validator:** Smoke Test → App starts, health returns 200
18. [ ] **Slice 04 - Test-Validator:** Regression → Runs Slice 01+02+03 tests → 30 passed (8+9+13)
19. [ ] **Slice 04 - Evidence:** Saved with regression.slices_tested = ["slice-01", "slice-02", "slice-03"]

**Expected Result:** Slice 04 complete, Planner enhanced with stack-detection and Gate 2 improved with inhaltliche pruefung

---

### Flow 5: Final Validation

**Pre-Condition:** All 4 slices complete

1. [ ] **Final Validation - Test-Validator (mode: final_validation):** Auto-Fix Lint → `ruff check --fix .`
2. [ ] **Final Validation - Test-Validator:** Lint Check → `ruff check .` → exit_code 0
3. [ ] **Final Validation - Test-Validator:** Type Check → `mypy .` → exit_code 0 (if configured)
4. [ ] **Final Validation - Test-Validator:** Build → `pip install -e .` → exit_code 0 (if setup.py exists)
5. [ ] **Final Validation - Test-Validator:** Full Smoke Test → App starts, health returns 200
6. [ ] **Final Validation - Test-Validator:** Full Regression → Runs ALL slice tests → 40 passed (8+9+13+10)
7. [ ] **Final Validation - Overall Status:** passed
8. [ ] **Final Evidence:** Feature-level evidence saved to `.claude/evidence/orchestrator-robust-testing/feature.json`
9. [ ] **State Machine:** current_state = "feature_complete"

**Expected Result:** Feature complete, all tests pass, feature ready for merge

---

## Edge Cases

### Error Handling

- [ ] **Implementer Failure:** If slice-implementer returns `status: failed` → HARD STOP (not auto-fixable, Spec problem)
- [ ] **Test-Writer Failure:** If test-writer returns `status: failed` → HARD STOP (Spec problem, unclear ACs)
- [ ] **AC-Coverage < 100%:** If test-writer returns `ac_coverage.total != ac_coverage.covered` → HARD STOP with missing AC-IDs
- [ ] **Validation Failure (Retry 1):** Debugger fixes code → Re-validate → passed
- [ ] **Validation Failure (Retry 2):** Debugger fixes code → Re-validate → passed
- [ ] **Validation Failure (Retry 3):** Debugger fixes code → Re-validate → failed → HARD STOP (3 retries exhausted)
- [ ] **JSON Parse Failure:** Any sub-agent returns non-JSON output → HARD STOP (no retry, agent definition error)
- [ ] **Smoke Test Timeout:** App does not respond within 30s → Stage failed → Debugger fixes (e.g., port conflict)
- [ ] **Regression Failure:** Previous slice test fails after new slice → Debugger fixes (breaking change detected)

### State Transitions

- [ ] **Pre-Check → Hard Stop:** Compliance files missing → Orchestrator stops with "Planner muss zuerst laufen"
- [ ] **Implementing → Hard Stop:** Implementer fails → State: hard_stop, no retry
- [ ] **Writing Tests → Hard Stop:** Test-Writer fails → State: hard_stop, no retry
- [ ] **Validating → Auto-Fixing:** Test-Validator reports failed → State: auto_fixing, retry_count++
- [ ] **Auto-Fixing → Validating:** Debugger returns status: fixed → State: validating, re-run tests
- [ ] **Auto-Fixing → Hard Stop:** Debugger returns status: unable_to_fix → State: hard_stop
- [ ] **Slice Complete → Implementing (next):** Evidence saved → State: implementing (next slice)
- [ ] **Last Slice Complete → Final Validation:** All slices done → State: final_validation
- [ ] **Final Validation → Feature Complete:** All tests pass → State: feature_complete

### Boundary Conditions

- [ ] **No Unit Tests:** Slice has no unit tests → Test-Validator reports `exit_code: 0`, `summary: "no tests found"`
- [ ] **No Integration Tests:** Slice has no integration tests → Test-Validator reports `exit_code: 0`, `summary: "no tests found"`
- [ ] **First Slice (No Regression):** No previous slices → Regression reports `exit_code: 0`, `slices_tested: []`, `summary: "No previous slices to test"`
- [ ] **Health-Endpoint does not exist:** Smoke Test fails → Debugger should add health endpoint (or skip smoke if not applicable)
- [ ] **Stack not recognized:** Slice-Writer/Test-Writer cannot detect stack → Falls back to AskUserQuestion
- [ ] **Max 3 Retries in Final Validation:** Final Validation fails 3 times → HARD STOP, manual intervention required

---

## Cross-Slice Integration Points

| # | Integration Point | Slices | How to Verify |
|---|-------------------|--------|---------------|
| 1 | Test-Writer Agent Definition consumed by Orchestrator | Slice 01 → Slice 03 | Orchestrator successfully invokes `Task(test-writer)` and parses JSON output |
| 2 | Test-Validator Agent Definition consumed by Orchestrator | Slice 02 → Slice 03 | Orchestrator successfully invokes `Task(test-validator)` and parses JSON output |
| 3 | Test-File-Naming Convention used by Test-Validator | Slice 01 → Slice 02 | Test-Validator finds tests in `tests/acceptance/test_{slice_id}.py` |
| 4 | Stack-Detection Matrix consistency across agents | Slice 01 → Slice 04 | slice-writer.md uses same matrix as test-writer.md (6 stacks, identical columns) |
| 5 | Orchestrator Pipeline consumes Test-Strategy Metadata | Slice 03 → Slice 04 | Orchestrator reads Test-Strategy from Slice-Specs and passes to test-validator |
| 6 | Evidence Format used by all slices | Slice 03 → All | Every slice produces evidence with implementation/tests/validation/retries sections |
| 7 | JSON Output Contracts parsed by Orchestrator | Slice 01, 02 → Slice 03 | Orchestrator successfully parses letzten ```json``` block from all agents |
| 8 | Stage-Skip-Semantik used by Orchestrator | Slice 02 → Slice 03 | When test-validator reports failed stage, subsequent stages have `exit_code: -1`, `summary: "skipped"` |
| 9 | Slice-Implementer JSON Contract (commit_hash) | Slice 03 | Orchestrator expects `commit_hash` (not `commit_message`) in implementer output |
| 10 | plan-spec Template with Test-Strategy consumed by slice-writer | Slice 04 → Future features | Future slice-writer invocations create slices with Test-Strategy section |

---

## Sign-Off

| Tester | Date | Result | Notes |
|--------|------|--------|-------|
| [Name] | [Date] | ✅ PASS / ❌ FAIL | |

**Test Environment:**
- Repository: feedbackai-mvp
- Branch: feature/orchestrator-robust-testing
- Python Version: 3.11+
- Test Framework: pytest
- Health Endpoint: GET http://localhost:8000/health

**Test Execution Summary:**
- Total Happy Path Steps: [Count after execution]
- Total Edge Cases: [Count after execution]
- Total Integration Points: 10
- Failed Steps: [List if any]
- Blockers: [List if any]

**Notes:**
[Any observations, issues found, or recommendations]

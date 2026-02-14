# Integration Map: Lean Testing Pipeline for Agentic Development

**Generated:** 2026-02-14
**Slices:** 4
**Connections:** 8
**Feature:** Orchestrator Robust Testing

---

## Dependency Graph (Visual)

```
┌─────────────────────────────────────────┐
│  Slice 01: Test-Writer Enhancement     │
│  - Agent Definition (.md)               │
│  - JSON Output Contract                 │
│  - Test-File-Naming Convention          │
│  - Stack-Detection Matrix               │
└─────────────────┬───────────────────────┘
                  │
         ┌────────┴────────┐
         │                 │
         ▼                 ▼
┌─────────────────┐  ┌─────────────────────────────────┐
│  Slice 02:      │  │  Slice 04: Planner & Gate      │
│  Test-Validator │  │  Improvements                    │
│  Agent          │  │  - slice-writer.md (Stack-Det)  │
│  - Agent Def    │  │  - slice-compliance.md (Gate 2) │
│  - JSON Output  │  │  - plan-spec Template           │
│  - Stage-Skip   │  │                                 │
└────────┬────────┘  └──────────────┬──────────────────┘
         │                          │
         └──────────┬───────────────┘
                    ▼
         ┌──────────────────────────────┐
         │  Slice 03: Orchestrator      │
         │  Pipeline                    │
         │  - orchestrate.md (4-Steps)  │
         │  - slice-implementer.md      │
         │  - Evidence Format           │
         │  - State Machine             │
         └──────────────────────────────┘
```

---

## Nodes

### Slice 01: Test-Writer Agent Enhancement

| Field | Value |
|-------|-------|
| Status | ✅ APPROVED |
| Dependencies | None |
| Outputs | 3 |
| File | `slices/slice-01-test-writer-enhancement.md` |
| Compliance | `slices/compliance-slice-01.md` |

**Inputs:**

| Input | Source | Validation |
|-------|--------|------------|
| -- | -- | No Dependencies (Foundation Slice) |

**Outputs:**

| Output | Type | Consumers |
|--------|------|-----------|
| Test-Writer Agent Definition | Agent (.md) | slice-02, slice-03 |
| JSON Output Contract | Datenformat | slice-03 |
| Test-File-Naming Convention | Konvention | slice-02 |
| Stack-Detection Matrix | Konvention | slice-04 |

---

### Slice 02: Test-Validator Agent

| Field | Value |
|-------|-------|
| Status | ✅ APPROVED |
| Dependencies | slice-01 |
| Outputs | 3 |
| File | `slices/slice-02-test-validator-agent.md` |
| Compliance | `slices/compliance-slice-02.md` |

**Inputs:**

| Input | Source | Validation |
|-------|--------|------------|
| Test-File-Naming Convention | Slice 01 | ✅ Test-Pfade folgen `tests/unit/`, `tests/integration/`, `tests/acceptance/` Pattern |
| AC-Test-Dateien | Slice 01 | ✅ Acceptance Tests existieren in `tests/acceptance/test_{slice_id}.py` |

**Outputs:**

| Output | Type | Consumers |
|--------|------|-----------|
| Test-Validator Agent Definition | Agent (.md) | slice-03 |
| JSON Output Contract | Datenformat | slice-03 |
| Stage-Skip-Semantik | Konvention | slice-03 |

---

### Slice 03: Orchestrator Pipeline

| Field | Value |
|-------|-------|
| Status | ✅ APPROVED |
| Dependencies | slice-01, slice-02 |
| Outputs | 4 |
| File | `slices/slice-03-orchestrator-pipeline.md` |
| Compliance | `slices/compliance-slice-03.md` |

**Inputs:**

| Input | Source | Validation |
|-------|--------|------------|
| Test-Writer Agent Definition | Slice 01 | ✅ Agent reagiert auf `Task(test-writer, prompt)` und liefert JSON Output Contract |
| Test-Writer JSON Output Contract | Slice 01 | ✅ `{ status, test_files, test_count, ac_coverage, commit_hash }` ist parsebar |
| Test-Validator Agent Definition | Slice 02 | ✅ Agent reagiert auf `Task(test-validator, prompt)` und liefert JSON Output Contract |
| Test-Validator JSON Output Contract | Slice 02 | ✅ `{ overall_status, stages, failed_stage?, error_output? }` ist parsebar |
| Stage-Skip-Semantik | Slice 02 | ✅ Bei Failure: nachfolgende Stages `exit_code: -1`, `summary: "skipped"` |

**Outputs:**

| Output | Type | Consumers |
|--------|------|-----------|
| Orchestrator Command | Command (.md) | slice-04, all features |
| Evidence-Format (erweitert) | Datenformat | all features |
| Slice-Implementer (angepasst) | Agent (.md) | all features |
| State-Machine | State-File (.json) | Resume-faehigkeit |

---

### Slice 04: Planner & Gate Improvements

| Field | Value |
|-------|-------|
| Status | ✅ APPROVED |
| Dependencies | slice-03, slice-01, slice-02 |
| Outputs | 3 |
| File | `slices/slice-04-planner-gate-improvements.md` |
| Compliance | `slices/compliance-slice-04.md` |

**Inputs:**

| Input | Source | Validation |
|-------|--------|------------|
| Orchestrator Pipeline | Slice 03 | ✅ Orchestrator konsumiert Test-Strategy Metadata aus Slice-Specs und gibt sie an Test-Writer/Test-Validator weiter |
| Stack-Detection Matrix | Slice 01 | ✅ Slice-Writer muss gleiche Detection-Matrix verwenden wie Test-Writer/Test-Validator |
| Test-Validator Input Format | Slice 02 | ✅ Test-Strategy Metadata (Commands, Health-Endpoint) muessen zum Test-Validator Input passen |

**Outputs:**

| Output | Type | Consumers |
|--------|------|-----------|
| Erweiterte Slice-Specs (mit Test-Strategy) | Datenformat | Orchestrator (Slice 03) |
| Inhaltlich gepruefter Gate 2 | Quality Gate | Planner Pipeline |
| plan-spec Template (mit Test-Strategy) | Template | Alle zukuenftigen Slice-Writer Aufrufe |

---

## Connections

| # | From | To | Resource | Type | Status |
|---|------|-----|----------|------|--------|
| 1 | Slice 01 | Slice 02 | Test-File-Naming Convention | Konvention | ✅ |
| 2 | Slice 01 | Slice 03 | Test-Writer Agent Definition | Agent (.md) | ✅ |
| 3 | Slice 01 | Slice 03 | JSON Output Contract (Test-Writer) | Datenformat | ✅ |
| 4 | Slice 01 | Slice 04 | Stack-Detection Matrix | Konvention | ✅ |
| 5 | Slice 02 | Slice 03 | Test-Validator Agent Definition | Agent (.md) | ✅ |
| 6 | Slice 02 | Slice 03 | JSON Output Contract (Test-Validator) | Datenformat | ✅ |
| 7 | Slice 02 | Slice 04 | Test-Validator Input Format | Datenformat | ✅ |
| 8 | Slice 03 | Slice 04 | Orchestrator Pipeline | Command (.md) | ✅ |

---

## Validation Results

### ✅ Valid Connections: 8

All declared dependencies have matching outputs. No missing connections found.

**Connection Details:**
- **Connection 1**: Slice 02 requires "Test-File-Naming Convention" from Slice 01 → Slice 01 provides it (Output: Test-File-Naming Convention)
- **Connection 2**: Slice 03 requires "Test-Writer Agent Definition" from Slice 01 → Slice 01 provides it (Output: Test-Writer Agent Definition)
- **Connection 3**: Slice 03 requires "Test-Writer JSON Output Contract" from Slice 01 → Slice 01 provides it (Output: JSON Output Contract)
- **Connection 4**: Slice 04 requires "Stack-Detection Matrix" from Slice 01 → Slice 01 provides it (Output: Stack-Detection Matrix)
- **Connection 5**: Slice 03 requires "Test-Validator Agent Definition" from Slice 02 → Slice 02 provides it (Output: Test-Validator Agent Definition)
- **Connection 6**: Slice 03 requires "Test-Validator JSON Output Contract" from Slice 02 → Slice 02 provides it (Output: JSON Output Contract)
- **Connection 7**: Slice 04 requires "Test-Validator Input Format" from Slice 02 → Slice 02 provides it (Output: JSON Output Contract mit Commands/Health-Endpoint)
- **Connection 8**: Slice 04 requires "Orchestrator Pipeline" from Slice 03 → Slice 03 provides it (Output: Orchestrator Command)

### ⚠️ Orphaned Outputs: 0

No orphaned outputs. All outputs are consumed by dependent slices or represent final user-facing deliverables.

| Output | Defined In | Consumers | Reason |
|--------|------------|-----------|--------|
| Evidence-Format (erweitert) | Slice 03 | All future features | Final deliverable for evidence storage |
| Slice-Implementer (angepasst) | Slice 03 | All future features | Final deliverable for slice implementation |
| State-Machine | Slice 03 | Resume-faehigkeit | Final deliverable for orchestrator state tracking |
| Inhaltlich gepruefter Gate 2 | Slice 04 | Planner Pipeline | Final deliverable for quality gates |
| plan-spec Template (mit Test-Strategy) | Slice 04 | All future Slice-Writer invocations | Final deliverable for slice specification template |

### ❌ Missing Inputs: 0

No missing inputs. All declared dependencies have matching outputs from earlier slices.

### ❌ Deliverable-Consumer Gaps: 0

All components and their consumer pages/files are present in deliverables.

**Analysis:**
This is an Agent Infrastructure feature with no UI components. All "consumers" are other agents or the orchestrator pipeline. Deliverable-Consumer-Traceability is satisfied through agent definitions and command files:

| Component | Defined In | Consumer Page/File | Page In Deliverables? | Status |
|-----------|------------|--------------------|-----------------------|--------|
| Test-Writer Agent | Slice 01 Deliverables | `.claude/agents/test-writer.md` | Yes (Slice 01) | ✅ |
| Test-Validator Agent | Slice 02 Deliverables | `.claude/agents/test-validator.md` | Yes (Slice 02) | ✅ |
| Orchestrator Command | Slice 03 Deliverables | `.claude/commands/orchestrate.md` | Yes (Slice 03) | ✅ |
| Slice-Implementer (modified) | Slice 03 Deliverables | `.claude/agents/slice-implementer.md` | Yes (Slice 03) | ✅ |
| Slice-Writer (modified) | Slice 04 Deliverables | `.claude/agents/slice-writer.md` | Yes (Slice 04) | ✅ |
| Slice-Compliance (modified) | Slice 04 Deliverables | `.claude/agents/slice-compliance.md` | Yes (Slice 04) | ✅ |
| plan-spec Template (modified) | Slice 04 Deliverables | `.claude/templates/plan-spec.md` | Yes (Slice 04) | ✅ |

---

## Discovery Traceability

### UI Components Coverage

**Status:** N/A (Agent Infrastructure, keine UI Components)

Discovery bestaetigt: "N/A -- Agent Infrastructure, keine UI-Komponenten." (discovery.md Line 134)

### State Machine Coverage

| State | Required UI | Available Actions | Covered In | Status |
|-------|-------------|-------------------|------------|--------|
| `pre_check` | -- | Pre-Impl Sanity Check | slice-03 (orchestrate.md Phase 1) | ✅ |
| `implementing` | -- | Task(slice-implementer) | slice-03 (orchestrate.md Step 1) | ✅ |
| `writing_tests` | -- | Task(test-writer) | slice-03 (orchestrate.md Step 2) | ✅ |
| `validating` | -- | Task(test-validator) | slice-03 (orchestrate.md Step 3) | ✅ |
| `auto_fixing` | -- | Task(debugger) | slice-03 (orchestrate.md Step 4 Retry Loop) | ✅ |
| `slice_complete` | -- | Evidence speichern | slice-03 (orchestrate.md Evidence Section) | ✅ |
| `hard_stop` | -- | HARD STOP mit Evidence | slice-03 (orchestrate.md HARD STOP Conditions) | ✅ |
| `final_validation` | -- | Task(test-validator, mode: final_validation) | slice-03 (orchestrate.md Phase 4) | ✅ |
| `feature_complete` | -- | Feature fertig | slice-03 (orchestrate.md Phase 5) | ✅ |

**State Machine Coverage:** 9/9 (100%)

### Transitions Coverage

| From | Trigger | To | Covered In | Status |
|------|---------|-----|------------|--------|
| `pre_check` | Compliance OK | `implementing` | slice-03 orchestrate.md | ✅ |
| `pre_check` | Compliance fehlt/FAILED | `hard_stop` | slice-03 orchestrate.md | ✅ |
| `implementing` | status: completed | `writing_tests` | slice-03 orchestrate.md | ✅ |
| `implementing` | status: failed | `hard_stop` | slice-03 orchestrate.md | ✅ |
| `writing_tests` | Tests + AC-Coverage 100% | `validating` | slice-03 orchestrate.md | ✅ |
| `writing_tests` | status: failed | `hard_stop` | slice-03 orchestrate.md | ✅ |
| `writing_tests` | AC-Coverage < 100% | `hard_stop` | slice-03 orchestrate.md | ✅ |
| `validating` | overall_status: passed | `slice_complete` | slice-03 orchestrate.md | ✅ |
| `validating` | overall_status: failed, retries < 3 | `auto_fixing` | slice-03 orchestrate.md | ✅ |
| `validating` | overall_status: failed, retries >= 3 | `hard_stop` | slice-03 orchestrate.md | ✅ |
| `auto_fixing` | status: fixed | `validating` | slice-03 orchestrate.md | ✅ |
| `auto_fixing` | status: unable_to_fix | `hard_stop` | slice-03 orchestrate.md | ✅ |
| `slice_complete` | Evidence saved | `implementing` (next) | slice-03 orchestrate.md | ✅ |
| letzter `slice_complete` | Alle Slices fertig | `final_validation` | slice-03 orchestrate.md | ✅ |
| `final_validation` | Alles gruen | `feature_complete` | slice-03 orchestrate.md | ✅ |
| `final_validation` | Failure, retries < 3 | `auto_fixing` | slice-03 orchestrate.md | ✅ |

**Transitions Coverage:** 16/16 (100%)

### Business Rules Coverage

| Rule | Covered In | Status |
|------|------------|--------|
| Rule 1: Implementer schreibt NUR Code, KEINE Tests | slice-03 (slice-implementer.md Anpassung) | ✅ |
| Rule 2: Test-Writer schreibt NUR Tests, KEINEN Feature-Code | slice-01 (test-writer.md Agent Definition) | ✅ |
| Rule 3: Debugger fixt primaer Code, Tests nur bei technischen Fehlern | slice-03 (orchestrate.md Prompt an Debugger) | ✅ |
| Rule 4: Orchestrator fuehrt KEINE Bash-Commands direkt aus | slice-03 (orchestrate.md No Direct Bash Rule) | ✅ |
| Rule 6: Exit Code ist Wahrheit (exit_code == 0 = BESTANDEN) | slice-02 (test-validator.md), slice-03 (orchestrate.md) | ✅ |
| Rule 7: 3 Retries, Re-Run ab fehlgeschlagenem Stage | slice-03 (orchestrate.md MAX_RETRIES = 3, Re-Run Logik) | ✅ |
| Rule 8: Evidence-Based (JSON pro Slice) | slice-03 (orchestrate.md Evidence Format) | ✅ |
| Rule 9: Auto-Detection ist Pflicht | slice-01 (test-writer.md Stack-Detection), slice-04 (slice-writer.md Stack-Detection) | ✅ |
| Rule 10: Test-Commands sind generiert, nicht konfiguriert | slice-04 (slice-writer.md Test-Strategy Metadata) | ✅ |
| Rule 11: 100% AC Coverage | slice-01 (test-writer.md AC-Coverage Check) | ✅ |
| Rule 12: App MUSS starten koennen (Smoke Test, 30s, Health-only) | slice-02 (test-validator.md Smoke Test) | ✅ |
| Rule 13: Regression Detection nach jedem Slice | slice-02 (test-validator.md Regression Run) | ✅ |
| Rule 14: Gate 2 prueft inhaltlich (AC-Qualitaet, Code Example Korrektheit), Max 1 Retry | slice-04 (slice-compliance.md Inhaltliche Pruefung) | ✅ |
| Rule 15: Gate 3 bleibt wie bisher mit 3 Retries | Stated in slice-04 (no changes to Gate 3) | ✅ |
| Rule 16: Wave-basierte Parallelisierung bleibt erhalten | slice-03 (orchestrate.md Wave-Based Implementation) | ✅ |
| Rule 17: Test-Dateien Konventionen | slice-01 (test-writer.md Test-File-Naming) | ✅ |
| Rule 18: Sub-Agent Output ist JSON im letzten Code-Block | slice-01 (test-writer.md), slice-02 (test-validator.md), slice-03 (orchestrate.md JSON-Parsing) | ✅ |

**Business Rules Coverage:** 17/17 (100%)

### Data Fields Coverage

| Field | Required | Covered In | Status |
|-------|----------|------------|--------|
| Implementer Output: status | Yes | slice-03 (slice-implementer.md JSON Contract) | ✅ |
| Implementer Output: files_changed | Yes | slice-03 (slice-implementer.md JSON Contract) | ✅ |
| Implementer Output: commit_hash | Yes | slice-03 (slice-implementer.md JSON Contract) | ✅ |
| Test-Writer Output: status | Yes | slice-01 (test-writer.md JSON Contract) | ✅ |
| Test-Writer Output: test_files | Yes | slice-01 (test-writer.md JSON Contract) | ✅ |
| Test-Writer Output: test_count.unit | Yes | slice-01 (test-writer.md JSON Contract) | ✅ |
| Test-Writer Output: test_count.integration | Yes | slice-01 (test-writer.md JSON Contract) | ✅ |
| Test-Writer Output: test_count.acceptance | Yes | slice-01 (test-writer.md JSON Contract) | ✅ |
| Test-Writer Output: ac_coverage.total | Yes | slice-01 (test-writer.md JSON Contract) | ✅ |
| Test-Writer Output: ac_coverage.covered | Yes | slice-01 (test-writer.md JSON Contract) | ✅ |
| Test-Writer Output: ac_coverage.missing | Yes | slice-01 (test-writer.md JSON Contract) | ✅ |
| Test-Validator Output: overall_status | Yes | slice-02 (test-validator.md JSON Contract) | ✅ |
| Test-Validator Output: stages.unit.exit_code | Yes | slice-02 (test-validator.md JSON Contract) | ✅ |
| Test-Validator Output: stages.unit.duration_ms | Yes | slice-02 (test-validator.md JSON Contract) | ✅ |
| Test-Validator Output: stages.unit.summary | Yes | slice-02 (test-validator.md JSON Contract) | ✅ |
| Test-Validator Output: stages.integration.* | Yes | slice-02 (test-validator.md JSON Contract) | ✅ |
| Test-Validator Output: stages.acceptance.* | Yes | slice-02 (test-validator.md JSON Contract) | ✅ |
| Test-Validator Output: stages.smoke.app_started | Yes | slice-02 (test-validator.md JSON Contract) | ✅ |
| Test-Validator Output: stages.smoke.health_status | Yes | slice-02 (test-validator.md JSON Contract) | ✅ |
| Test-Validator Output: stages.smoke.startup_duration_ms | Yes | slice-02 (test-validator.md JSON Contract) | ✅ |
| Test-Validator Output: stages.regression.exit_code | Yes | slice-02 (test-validator.md JSON Contract) | ✅ |
| Test-Validator Output: stages.regression.slices_tested | Yes | slice-02 (test-validator.md JSON Contract) | ✅ |
| Debugger Output: status | Yes | slice-03 (orchestrate.md references existing debugger) | ✅ |
| Debugger Output: root_cause | Yes | slice-03 (orchestrate.md references existing debugger) | ✅ |
| Debugger Output: files_changed | Yes | slice-03 (orchestrate.md references existing debugger) | ✅ |
| Evidence: feature | Yes | slice-03 (orchestrate.md Evidence Format) | ✅ |
| Evidence: slice | Yes | slice-03 (orchestrate.md Evidence Format) | ✅ |
| Evidence: timestamp | Yes | slice-03 (orchestrate.md Evidence Format) | ✅ |
| Evidence: status | Yes | slice-03 (orchestrate.md Evidence Format) | ✅ |
| Evidence: implementation | Yes | slice-03 (orchestrate.md Evidence Format) | ✅ |
| Evidence: tests | Yes | slice-03 (orchestrate.md Evidence Format) | ✅ |
| Evidence: validation | Yes | slice-03 (orchestrate.md Evidence Format) | ✅ |
| Evidence: retries | Yes | slice-03 (orchestrate.md Evidence Format) | ✅ |
| Test-Strategy: stack | Yes | slice-04 (plan-spec.md Template) | ✅ |
| Test-Strategy: test_command | Yes | slice-04 (plan-spec.md Template) | ✅ |
| Test-Strategy: integration_command | Yes | slice-04 (plan-spec.md Template) | ✅ |
| Test-Strategy: acceptance_command | Yes | slice-04 (plan-spec.md Template) | ✅ |
| Test-Strategy: start_command | Yes | slice-04 (plan-spec.md Template) | ✅ |
| Test-Strategy: health_endpoint | Yes | slice-04 (plan-spec.md Template) | ✅ |
| Test-Strategy: mocking_strategy | Yes | slice-04 (plan-spec.md Template) | ✅ |

**Data Fields Coverage:** 40/40 (100%)

**Discovery Coverage:** 100%

---

## Summary

| Metric | Value |
|--------|-------|
| Total Slices | 4 |
| Total Connections | 8 |
| Valid Connections | 8 |
| Orphaned Outputs | 0 |
| Missing Inputs | 0 |
| Deliverable-Consumer Gaps | 0 |
| Discovery Coverage | 100% |
| State Machine Coverage | 9/9 (100%) |
| Transitions Coverage | 16/16 (100%) |
| Business Rules Coverage | 17/17 (100%) |
| Data Fields Coverage | 40/40 (100%) |

**Verdict:** ✅ READY FOR ORCHESTRATION

**Quality Assessment:**
- All 4 slices are APPROVED by Gate 2
- All dependencies are satisfied with no missing connections
- No orphaned outputs (all outputs consumed or final deliverables)
- No deliverable-consumer gaps (all components traceable to deliverables)
- 100% discovery traceability (all states, transitions, rules, and data fields covered)
- Clean dependency chain: Slice 01 → Slices 02+04 → Slice 03 → Implementation

**Implementation Order:**
1. **Slice 01** (Test-Writer Enhancement) - Foundation, no dependencies
2. **Slice 02** (Test-Validator Agent) - Depends on Slice 01
3. **Slice 04** (Planner & Gate Improvements) - Can run parallel with Slice 02 (both depend only on Slice 01)
4. **Slice 03** (Orchestrator Pipeline) - Depends on Slices 01, 02 (implicitly also 04 for Test-Strategy consumption)

**Note:** Slices 02 and 04 CAN be implemented in parallel since they only share Slice 01 as a dependency.

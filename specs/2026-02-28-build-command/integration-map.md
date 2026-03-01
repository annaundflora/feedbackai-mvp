# Integration Map: /build Command - Unified Autonomous Feature Pipeline

**Generated:** 2026-03-01
**Slices:** 5
**Connections:** 6

---

## Dependency Graph (Visual)

```
┌─────────────────────────┐     ┌─────────────────────────┐
│  Slice 01               │     │  Slice 02               │
│  slice-plan-coordinator │     │  slice-impl-coordinator │
│  (No dependencies)      │     │  (No dependencies)      │
└───────────┬─────────────┘     └───────────┬─────────────┘
            │                               │
            │  provides Agent               │  provides Agent
            │  + JSON Contract              │  + JSON Contract
            │                               │  + Evidence JSON
            └──────────┐       ┌────────────┘
                       │       │
                       ▼       ▼
              ┌─────────────────────────┐
              │  Slice 03               │
              │  /build Command         │
              │  (Deps: 01, 02)         │
              └───────────┬─────────────┘
                          │
                          │  provides Command
                          │  + State Schema
                          ▼
              ┌─────────────────────────┐
              │  Slice 04               │
              │  Multi-Spec Support     │
              │  (Deps: 03)             │
              └─────────────────────────┘

┌─────────────────────────┐
│  Slice 05               │
│  Pattern-Dokumentation  │
│  (No dependencies)      │
│  (Parallel to all)      │
└─────────────────────────┘
```

---

## Nodes

### Slice 01: Slice-Plan-Coordinator Agent

| Field | Value |
|-------|-------|
| Status | APPROVED |
| Dependencies | None |
| Outputs | `slice-plan-coordinator` Agent, JSON Output Contract |

**Inputs:**

| Input | Source | Validation |
|-------|--------|------------|
| `slice-writer` Agent | External (existing, unchanged) | PASS |
| `slice-compliance` Agent | External (existing, unchanged) | PASS |

**Outputs:**

| Output | Type | Consumers |
|--------|------|-----------|
| `.claude/agents/slice-plan-coordinator.md` | Agent (Ebene 1) | Slice 03 |
| JSON Output Contract `{status, retries, slice_file, blocking_issues}` | Data Contract | Slice 03 |

---

### Slice 02: Slice-Impl-Coordinator Agent

| Field | Value |
|-------|-------|
| Status | APPROVED |
| Dependencies | None |
| Outputs | `slice-impl-coordinator` Agent, JSON Output Contract, Evidence JSON |

**Inputs:**

| Input | Source | Validation |
|-------|--------|------------|
| `slice-implementer` Agent | External (existing, unchanged) | PASS |
| `test-writer` Agent | External (existing, unchanged) | PASS |
| `test-validator` Agent | External (existing, unchanged) | PASS |
| `debugger` Agent | External (existing, unchanged) | PASS |

**Outputs:**

| Output | Type | Consumers |
|--------|------|-----------|
| `.claude/agents/slice-impl-coordinator.md` | Agent (Ebene 1) | Slice 03 |
| JSON Output Contract `{status, retries, evidence, error}` | Data Contract | Slice 03 |
| Evidence JSON File `.claude/evidence/{feature}/{slice_id}.json` | File Artifact | Slice 03 |

---

### Slice 03: /build Command

| Field | Value |
|-------|-------|
| Status | APPROVED |
| Dependencies | Slice 01, Slice 02 |
| Outputs | `/build` Command, `.build-state.json` Schema |

**Inputs:**

| Input | Source | Validation |
|-------|--------|------------|
| `slice-plan-coordinator` Agent | Slice 01 | PASS -- Slice 01 provides this as Agent (Ebene 1) |
| `slice-impl-coordinator` Agent | Slice 02 | PASS -- Slice 02 provides this as Agent (Ebene 1) |
| `integration-map` Agent | External (existing, unchanged) | PASS |
| `test-validator` Agent (mode=final_validation) | External (existing, unchanged) | PASS |
| `debugger` Agent | External (existing, unchanged) | PASS |

**Outputs:**

| Output | Type | Consumers |
|--------|------|-----------|
| `.claude/commands/build.md` | Command (Ebene 0) | Slice 04 |
| `.build-state.json` Schema | State File | Slice 04 |

---

### Slice 04: Multi-Spec Support

| Field | Value |
|-------|-------|
| Status | APPROVED |
| Dependencies | Slice 03 |
| Outputs | Multi-Spec `/build` Command (End-User) |

**Inputs:**

| Input | Source | Validation |
|-------|--------|------------|
| `/build` Command (`build.md`) | Slice 03 | PASS -- Slice 03 provides this as Command |
| `.build-state.json` Schema (`specs[]`, `current_spec_index`) | Slice 03 | PASS -- Schema defined in architecture.md, provided by Slice 03 |
| `slice-plan-coordinator` Agent | Slice 01 | PASS -- Unchanged, used per spec |
| `slice-impl-coordinator` Agent | Slice 02 | PASS -- Unchanged, used per spec |

**Outputs:**

| Output | Type | Consumers |
|--------|------|-----------|
| `.claude/commands/build.md` (Extended) | Command (Ebene 0) | End-User (Final) |
| Feature-Skip-Logik | Behavioral Contract | End-User (Final) |

---

### Slice 05: Pattern-Dokumentation

| Field | Value |
|-------|-------|
| Status | APPROVED |
| Dependencies | None |
| Outputs | `workflow-patterns.md` (Documentation) |

**Inputs:**

| Input | Source | Validation |
|-------|--------|------------|
| None (hard dependencies) | -- | PASS |
| `.claude/agents/slice-plan-coordinator.md` | Slice 01 (soft, non-blocking) | PASS |
| `.claude/agents/slice-impl-coordinator.md` | Slice 02 (soft, non-blocking) | PASS |
| `.claude/commands/build.md` | Slice 03 (soft, non-blocking) | PASS |

**Outputs:**

| Output | Type | Consumers |
|--------|------|-----------|
| `.claude/docs/workflow-patterns.md` | Documentation | Future Agents/Commands (Final) |
| Pattern-Katalog | Knowledge Base | Slice-Writer Agent (Future) |

---

## Connections

| # | From | To | Resource | Type | Status |
|---|------|-----|----------|------|--------|
| 1 | Slice 01 | Slice 03 | `slice-plan-coordinator` Agent | Agent (Ebene 1) | PASS |
| 2 | Slice 01 | Slice 03 | JSON Output Contract (plan) | Data Contract | PASS |
| 3 | Slice 02 | Slice 03 | `slice-impl-coordinator` Agent | Agent (Ebene 1) | PASS |
| 4 | Slice 02 | Slice 03 | JSON Output Contract (impl) + Evidence | Data Contract + File | PASS |
| 5 | Slice 03 | Slice 04 | `/build` Command | Command (Ebene 0) | PASS |
| 6 | Slice 03 | Slice 04 | `.build-state.json` Schema | State File | PASS |

---

## Validation Results

### PASS Valid Connections: 6

All declared dependencies have matching outputs. Every input for every slice has a corresponding producer that is APPROVED.

### Orphaned Outputs: 0

No orphaned outputs. All outputs are either consumed by a downstream slice or are final user-facing deliverables:

| Output | Defined In | Consumer | Classification |
|--------|------------|----------|----------------|
| Multi-Spec `/build` Command | Slice 04 | End-User | Final User-Facing |
| Feature-Skip-Logik | Slice 04 | End-User | Final User-Facing |
| `.claude/docs/workflow-patterns.md` | Slice 05 | Future Agents | Final User-Facing |

### Missing Inputs: 0

No missing inputs found. All dependencies are either:
- Provided by another slice in this feature (Slice 01 -> 03, Slice 02 -> 03, Slice 03 -> 04)
- External existing agents that are unchanged and out of scope

### Deliverable-Consumer Gaps: 0

| Component | Defined In | Consumer File | In Deliverables? | Status |
|-----------|------------|---------------|-------------------|--------|
| `slice-plan-coordinator.md` | Slice 01 | `.claude/commands/build.md` | Yes (Slice 03) | PASS |
| `slice-impl-coordinator.md` | Slice 02 | `.claude/commands/build.md` | Yes (Slice 03) | PASS |
| `build.md` (base) | Slice 03 | `.claude/commands/build.md` | Yes (Slice 04 extends) | PASS |

---

## Discovery Traceability

### UI Components Coverage

> N/A -- CLI-only feature. Discovery confirms "CLI-only, keine UI". No UI components to trace.

| Status |
|--------|
| PASS (N/A) |

### State Machine Coverage

| State | Required UI (Terminal Output) | Available Actions | Covered In | Status |
|-------|-------------------------------|-------------------|------------|--------|
| `init` | "Validating inputs..." | Validate, Resume Check | Slice 03 (Phase 1: Input Validation, Phase 2: State & Resume) | PASS |
| `planning_slice_N` | "Planning Slice N/M..." | Task(slice-plan-coordinator) | Slice 03 (Phase 4: Planning Phase), Slice 01 (Agent) | PASS |
| `gate_3` | "Gate 3: Integration Validation..." | Task(integration-map) | Slice 03 (Phase 5: Gate 3) | PASS |
| `implementing_slice_N` | "Implementing Slice N/M..." | Task(slice-impl-coordinator) | Slice 03 (Phase 6: Implementation), Slice 02 (Agent) | PASS |
| `final_validation` | "Final Validation..." | Task(test-validator) | Slice 03 (Phase 7: Final Validation) | PASS |
| `completing` | "Creating PR..." | Push, PR Create | Slice 03 (Phase 8: Completion) | PASS |
| `completed` | "Feature Complete!" | -- | Slice 03 (Phase 8: state.status = "completed") | PASS |
| `failed` | "HARD STOP: {reason}" | Resume | Slice 03 (HARD STOP conditions, Resume Logic) | PASS |

### Transitions Coverage

| From | Trigger | To | Covered In | Status |
|------|---------|-----|------------|--------|
| `init` | Input valid | `planning_slice_1` | Slice 03 AC-1 | PASS |
| `init` | State-File exists | `planning_slice_N` or `implementing_slice_N` | Slice 03 AC-13, AC-14 | PASS |
| `planning_slice_N` | Slice approved | `planning_slice_N+1` or `gate_3` | Slice 03 AC-4, AC-5, AC-6 | PASS |
| `planning_slice_N` | Max retries reached | `failed` | Slice 03 AC-12 | PASS |
| `gate_3` | Verdict: READY | `implementing_slice_1` | Slice 03 AC-7 | PASS |
| `gate_3` | Max retries reached | `failed` | Slice 03 AC-8 | PASS |
| `implementing_slice_N` | Evidence saved | `implementing_slice_N+1` or `final_validation` | Slice 03 AC-9, AC-10 | PASS |
| `implementing_slice_N` | Max retries reached | `failed` | Slice 03 AC-12 | PASS |
| `final_validation` | All passed | `completing` | Slice 03 AC-11 | PASS |
| `completing` | PR created | `completed` | Slice 03 AC-11 | PASS |

### Business Rules Coverage

| Rule | Covered In | Status |
|------|------------|--------|
| Max 9 Retries pro Slice (Planning + Implementation jeweils) | Slice 01 (MAX_RETRIES=9), Slice 02 (MAX_RETRIES=9), Slice 03 (Kritische Regeln #3) | PASS |
| Max 9 Retries fuer Gate 3 | Slice 03 (Phase 5: Gate 3 Loop) | PASS |
| Planning ist sequenziell (Integration Contracts) | Slice 03 (Phase 4: Sequential FOR loop) | PASS |
| Implementation folgt orchestrator-config.md Reihenfolge | Slice 03 (Phase 6: Wave-based, parses orchestrator-config.md) | PASS |
| Jeder Slice-Coordinator-Call gibt nur JSON zurueck (~300 Tokens) | Slice 01 (JSON Output Contract), Slice 02 (JSON Output Contract), Slice 03 (Kritische Regeln #5) | PASS |
| State wird nach JEDEM Schritt auf Disk geschrieben | Slice 03 (Kritische Regeln #4, Section 7: State-Update Pattern) | PASS |
| Bei Resume: Lese State-File und setze fort | Slice 03 (Section 6: Resume-Logik, AC-13, AC-14) | PASS |
| Multi-Spec: Features werden sequenziell verarbeitet | Slice 04 (Outer Loop, Constraints: "Keine parallele Feature-Verarbeitung") | PASS |
| Feature-Branch wird am Start erstellt, PR am Ende | Slice 03 (Phase 3: Git Branch, Phase 8: Completion) | PASS |

### Data Fields Coverage

| Field | Required | Covered In | Status |
|-------|----------|------------|--------|
| `specs` | Yes | Slice 03 (Section 3), Slice 04 (Section 3, AC-9) | PASS |
| `current_spec_index` | Yes | Slice 03 (Section 3), Slice 04 (Section 3, AC-9) | PASS |
| `status` | Yes | Slice 03 (Section 3, State-Update Pattern) | PASS |
| `phase` | Yes | Slice 03 (Section 3, State-Update Pattern) | PASS |
| `current_slice_index` | Yes | Slice 03 (Section 3, State-Update Pattern) | PASS |
| `total_slices` | Yes | Slice 03 (Section 3) | PASS |
| `slices` | Yes | Slice 03 (Section 3, State-Update Pattern) | PASS |
| `approved_slices` | Yes | Slice 03 (Section 3, Planning Phase) | PASS |
| `completed_slices` | Yes | Slice 03 (Section 3, Implementation Phase) | PASS |
| `failed_slices` | Yes | Slice 03 (Section 3, HARD STOP conditions) | PASS |
| `branch_name` | Yes | Slice 03 (Section 3, Phase 3: Git Branch) | PASS |
| `started_at` | Yes | Slice 03 (Section 3) | PASS |
| `last_updated` | Yes | Slice 03 (Section 3, AC-15) | PASS |
| `completed_at` | No | Slice 03 (Section 3, Phase 8) | PASS |

**Discovery Coverage:** 36/36 (100%)

---

## Summary

| Metric | Value |
|--------|-------|
| Total Slices | 5 |
| Total Connections | 6 |
| Valid Connections | 6 |
| Orphaned Outputs | 0 |
| Missing Inputs | 0 |
| Deliverable-Consumer Gaps | 0 |
| Discovery Coverage | 100% |

---

VERDICT: READY FOR ORCHESTRATION

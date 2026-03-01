# Feature: /build Command - Unified Autonomous Feature Pipeline

**Epic:** –
**Status:** Ready
**Discovery:** `discovery.md` (same folder)
**Wireframes:** – (CLI-only, keine UI)
**Derived from:** Discovery constraints, NFRs, and risks

---

## Problem & Solution

**Problem:**
- `/planner` und `/orchestrate` sind separate Commands mit manuellem Wechsel
- Bei 7+ Slices mit Retries füllt sich der Coordinator-Context (35.000-105.000 Tokens)
- Session-Compacting zerstört wichtigen State mitten im Lauf
- Skaliert nicht auf größere Arbeitspakete (mehrere Features)

**Solution:**
- Neuer `/build` Command der Planning + Execution in einem autonomen Loop vereint
- **Hierarchical Delegation Pattern:** Ultra-Lean Coordinator delegiert pro Slice an Coordinator-Sub-Agents
- Coordinator-Context bleibt bei ~5.000 Tokens statt 35.000-105.000

**Business Value:**
- Vollständig autonomer Feature-Build von Spec bis PR
- Skaliert auf 20+ Slices und stundenlange Runs ohne Context-Overflow
- Kein manueller Eingriff zwischen Planning und Implementation nötig

---

## Scope & Boundaries

| In Scope |
|----------|
| Neuer `/build` Command (`.claude/commands/build.md`) |
| Neuer `slice-plan-coordinator` Agent (`.claude/agents/slice-plan-coordinator.md`) |
| Neuer `slice-impl-coordinator` Agent (`.claude/agents/slice-impl-coordinator.md`) |
| Multi-Spec-Support (mehrere Features in einem Lauf) |
| State-on-Disk (`.build-state.json`) mit Resume-Support |
| Feature-Branch + Commits + PR-Erstellung |
| Dependency-Graph-basierte Reihenfolge |

| Out of Scope |
|--------------|
| Änderungen an bestehenden Sub-Agents (slice-writer, slice-compliance, slice-implementer, test-writer, test-validator, debugger, integration-map) |
| Änderungen an `/planner` oder `/orchestrate` Commands (bleiben parallel erhalten) |
| Parallele Slice-Verarbeitung in Planning-Phase (sequenziell wegen Integration Contracts) |
| Discovery/Wireframe/Architecture-Erstellung (Startpunkt ist fertige Spec) |

---

## API Design

> N/A — CLI Command, keine HTTP-APIs. Alle Interaktion erfolgt über Claude Code Task()-Calls und Dateisystem.

---

## Database Schema

> N/A — Kein Datenbank-Schema. State wird in JSON-Files auf Disk gespeichert.

### State-on-Disk: `.build-state.json`

| Field | Type | Required | Validation | Notes |
|-------|------|----------|------------|-------|
| `specs` | `string[]` | Yes | Non-empty array of valid spec paths | Multi-Spec Support |
| `current_spec_index` | `int` | Yes | `>= 0`, `< specs.length` | Index des aktuellen Features |
| `status` | `string` | Yes | `"in_progress"` / `"completed"` / `"failed"` | Globaler Status |
| `phase` | `string` | Yes | `"planning"` / `"gate_3"` / `"implementing"` / `"final_validation"` / `"completing"` | Aktuelle Phase |
| `current_slice_index` | `int` | Yes | `>= 0` | Aktueller Slice (0-based) |
| `total_slices` | `int` | Yes | `> 0` | Gesamtzahl Slices |
| `slices` | `object[]` | Yes | Array of Slice-Status-Objekte | Slice-Tracking |
| `slices[].number` | `int` | Yes | `> 0` | Slice-Nummer |
| `slices[].name` | `string` | Yes | Non-empty | Slice-Name/Slug |
| `slices[].plan_status` | `string` | Yes | `"pending"` / `"approved"` / `"retrying"` / `"failed"` | Planning-Status |
| `slices[].impl_status` | `string` | Yes | `"pending"` / `"completed"` / `"retrying"` / `"failed"` | Implementierung-Status |
| `slices[].plan_retries` | `int` | Yes | `0-9` | Planning Retry-Counter |
| `slices[].impl_retries` | `int` | Yes | `0-9` | Implementation Retry-Counter |
| `approved_slices` | `int[]` | Yes | Subset of slice numbers | Planning abgeschlossen |
| `completed_slices` | `int[]` | Yes | Subset of slice numbers | Implementation abgeschlossen |
| `failed_slices` | `int[]` | Yes | Subset of slice numbers | Fehlgeschlagene Slices |
| `gate3_retries` | `int` | Yes | `0-9` | Gate 3 Retry-Counter |
| `last_action` | `string` | Yes | Free text | Letzter Progress-Schritt (z.B. "Slice 3 approved", "Gate 3 APPROVED") |
| `branch_name` | `string` | Yes | Valid git branch name | Feature-Branch |
| `started_at` | `string` | Yes | ISO 8601 timestamp | Start-Zeitpunkt |
| `last_updated` | `string` | Yes | ISO 8601 timestamp | Letztes Update |
| `completed_at` | `string` | No | ISO 8601 timestamp | Ende-Zeitpunkt |
| `error` | `string` | No | Free text | Fehlergrund bei `"failed"` |

**Location:** `{spec_path}/.build-state.json`

**Kompatibilität mit bestehenden State-Files:**
- `.planner-state.json` und `.orchestrator-state.json` werden NICHT geschrieben
- `/build` nutzt ausschließlich `.build-state.json`
- Bestehende State-Files von `/planner` und `/orchestrate` bleiben unberührt

---

## Server Logic

> Adaptiert: "Agent Logic" statt "Server Logic" — keine HTTP-Services, sondern Agent-Orchestrierung.

### Agents & Processing

| Agent | Responsibility | Input | Output | Side Effects |
|-------|----------------|-------|--------|--------------|
| `/build` Command | Ultra-Lean Coordinator. Liest State, bestimmt nächsten Schritt, dispatcht Task()-Calls, schreibt State | spec_path(s), `.build-state.json` | `.build-state.json`, PR URL | Git branch, Git push, PR create |
| `slice-plan-coordinator` | Plant + validiert 1 Slice. Ruft slice-writer + slice-compliance auf. Retry-Loop (max 9) | spec_path, slice_number, previously_approved_slices | JSON: `{status, retries, slice_file}` | Writes `slices/slice-NN-slug.md`, `slices/compliance-slice-NN.md` |
| `slice-impl-coordinator` | Implementiert + testet 1 Slice. Ruft slice-implementer + test-writer + test-validator + debugger auf. Retry-Loop (max 9) | spec_path, slice_id, architecture_path, integration_map_path | JSON: `{status, evidence, retries}` | Writes code files, test files, git commits, `.claude/evidence/` |

### Business Logic Flow

```
/build {spec_path}
  │
  ├─ Input Validation
  │    ├─ discovery.md MUST exist
  │    ├─ architecture.md MUST exist
  │    └─ .build-state.json? → Resume or Init
  │
  ├─ Git Branch Create (if not resume)
  │    └─ feat/{feature-name}
  │
  ├─ Planning Phase (Sequential)
  │    FOR EACH Slice:
  │    │  Task(slice-plan-coordinator) → JSON
  │    │  ├─ status: "approved" → next slice, update state
  │    │  └─ status: "failed" → HARD STOP
  │    └─ State Update nach jedem Slice
  │
  ├─ Gate 3 (Integration Validation)
  │    Task(integration-map) → VERDICT
  │    ├─ READY → continue
  │    └─ GAPS FOUND → retry (max 9), then HARD STOP
  │
  ├─ Implementation Phase (Wave-based)
  │    Parse orchestrator-config.md → Waves
  │    FOR EACH Wave:
  │    │  FOR EACH Slice in Wave:
  │    │    Task(slice-impl-coordinator) → JSON
  │    │    ├─ status: "completed" → next slice, update state
  │    │    └─ status: "failed" → HARD STOP
  │    └─ State Update nach jedem Slice
  │
  ├─ Final Validation
  │    Task(test-validator, mode=final_validation) → JSON
  │    ├─ passed → continue
  │    └─ failed → Task(debugger) + retry (max 9)
  │
  └─ Completion
       ├─ Git push
       ├─ gh pr create
       └─ State: completed
```

### Slice-Plan-Coordinator Internal Flow

```
Input: spec_path, slice_number, approved_slices_context
  │
  ├─ Read discovery.md, architecture.md, wireframes.md (if exists)
  ├─ Read previously approved slices (for Integration Contracts)
  │
  ├─ retry_count = 0
  │  LOOP (max 9):
  │    ├─ Task(slice-writer) → slice-NN-slug.md
  │    ├─ Task(slice-compliance) → compliance-slice-NN.md
  │    ├─ Read VERDICT
  │    │  ├─ APPROVED → return {status: "approved", retries: N, slice_file: "..."}
  │    │  └─ FAILED → retry_count++, re-Task(slice-writer) with fix prompt
  │    └─ retry_count >= 9 → return {status: "failed", retries: 9, blocking_issues: [...]}
  │
  └─ Return JSON (~300 Tokens)
```

### Slice-Impl-Coordinator Internal Flow

```
Input: spec_path, slice_id, architecture_path, integration_map_path
  │
  ├─ Read slice spec, architecture, integration map
  │
  ├─ Task(slice-implementer) → JSON {status, files_changed, commit_hash}
  │  └─ status: "failed" → return {status: "failed", ...}
  │
  ├─ Task(test-writer) → JSON {status, test_files, ac_coverage}
  │  └─ ac_coverage not 100% → return {status: "failed", ...}
  │
  ├─ retry_count = 0
  │  LOOP (max 9):
  │    ├─ Task(test-validator, mode=slice_validation) → JSON {overall_status, stages}
  │    │  ├─ passed → break
  │    │  └─ failed → Task(debugger) → JSON {status, root_cause}
  │    │              ├─ "fixed" → retry_count++, re-validate
  │    │              └─ "unable_to_fix" → return {status: "failed", ...}
  │    └─ retry_count >= 9 → return {status: "failed", retries: 9}
  │
  ├─ Write evidence: .claude/evidence/{feature}/{slice_id}.json
  │
  └─ Return JSON (~300 Tokens):
     {status: "completed", evidence: {files_changed, test_count, retries}, commit_hash: "..."}
```

### JSON Output Contracts

**slice-plan-coordinator → /build:**

```json
{
  "status": "approved | failed",
  "retries": 2,
  "slice_file": "slices/slice-01-db-schema.md",
  "blocking_issues": []
}
```

**slice-impl-coordinator → /build:**

```json
{
  "status": "completed | failed",
  "retries": 1,
  "evidence": {
    "files_changed": ["backend/app/..."],
    "test_files": ["tests/..."],
    "test_count": 12,
    "commit_hash": "abc123"
  },
  "error": null
}
```

**integration-map → /build (existing contract, unchanged):**

```
VERDICT: READY FOR ORCHESTRATION
```
or
```
VERDICT: GAPS FOUND
MISSING_INPUTS: [...]
AFFECTED_SLICES: [...]
```

---

## Security

> N/A — Internes CLI-Tooling ohne externe Angriffsfläche.

- Keine User-Authentifizierung (Claude Code Session)
- Keine Netzwerk-Endpoints
- State-Files enthalten keine sensitiven Daten
- Git-Credentials werden von bestehender Git-Config verwaltet

---

## Architecture Layers

### Layer Responsibilities

| Layer | Responsibility | Pattern | Files |
|-------|----------------|---------|-------|
| Command (Ebene 0) | Ultra-Lean Coordinator. State-Machine, Dispatch, Resume | State-on-Disk + Hierarchical Delegation | `.claude/commands/build.md` |
| Coordinator-Agents (Ebene 1) | Frischer Context pro Slice. Orchestriert Worker-Agents | Fresh Context + Hard Gate | `.claude/agents/slice-plan-coordinator.md`, `.claude/agents/slice-impl-coordinator.md` |
| Worker-Agents (Ebene 2) | Bestehende Sub-Agents, unverändert | External Validation + JSON Output Contract | `slice-writer`, `slice-compliance`, `slice-implementer`, `test-writer`, `test-validator`, `debugger`, `integration-map` |

### 3-Tier Data Flow

```
/build Command (Ebene 0, ~5.000 Tokens Context)
  │
  │  Reads: .build-state.json, spec_path/discovery.md
  │  Writes: .build-state.json
  │  Receives: ~300 Token JSON per Task()-Call
  │
  ├── Task(slice-plan-coordinator)    [Ebene 1, eigener Context]
  │     │  Reads: discovery.md, architecture.md, wireframes.md, approved slices
  │     │  Writes: slices/slice-NN.md, slices/compliance-slice-NN.md
  │     │
  │     ├── Task(slice-writer)        [Ebene 2, eigener Context]
  │     └── Task(slice-compliance)    [Ebene 2, eigener Context]
  │
  ├── Task(integration-map)           [Ebene 1, eigener Context]
  │     │  Reads: all slices, architecture.md
  │     │  Writes: integration-map.md, e2e-checklist.md, orchestrator-config.md
  │
  └── Task(slice-impl-coordinator)    [Ebene 1, eigener Context]
        │  Reads: slice spec, architecture.md, integration-map.md
        │  Writes: code files, test files, evidence JSON
        │
        ├── Task(slice-implementer)   [Ebene 2, eigener Context]
        ├── Task(test-writer)         [Ebene 2, eigener Context]
        ├── Task(test-validator)      [Ebene 2, eigener Context]
        └── Task(debugger)            [Ebene 2, eigener Context]
```

### Error Handling Strategy

| Error Type | Handling | User Response | Recovery |
|------------|----------|---------------|----------|
| Input validation failure | Immediate STOP | "discovery.md or architecture.md missing" | Fix spec, re-run |
| Slice planning failed (9 retries) | HARD STOP, state=failed | "Slice N planning failed after 9 retries" | Manual fix, resume |
| Gate 3 failed (9 retries) | HARD STOP, state=failed | "Gate 3 failed after 9 retries" | Manual fix, resume |
| Slice implementation failed (9 retries) | HARD STOP, state=failed | "Slice N implementation failed after 9 retries" | Manual fix, resume |
| Final validation failed (9 retries) | HARD STOP, state=failed | "Final validation failed after 9 retries" | Manual fix, resume |
| JSON parse failure from sub-agent | HARD STOP | "Failed to parse JSON from {agent}" | Re-run (transient) |
| Git push/PR failure | HARD STOP, state=failed | "Git operation failed: {error}" | Fix git state, resume |

### Resume Logic

```
IF .build-state.json exists AND status == "in_progress":
  Read state
  Determine phase + current_slice_index
  Skip already approved/completed slices
  Continue from last incomplete step

IF .build-state.json exists AND status == "completed":
  Output "Build already completed for this spec"
  STOP

IF .build-state.json exists AND status == "failed":
  Output last error
  Ask: "Resume from failed step?"
  Continue from failed step
```

---

## Migration Map

> N/A — Keine bestehenden Dateien werden migriert. Nur neue Dateien erstellt:

| New File | Purpose |
|----------|---------|
| `.claude/commands/build.md` | /build Command Definition |
| `.claude/agents/slice-plan-coordinator.md` | Planning Coordinator Agent |
| `.claude/agents/slice-impl-coordinator.md` | Implementation Coordinator Agent |

---

## Constraints & Integrations

### Constraints

| Constraint | Technical Implication | Solution |
|------------|----------------------|----------|
| Context-Budget: Coordinator max ~5.000 Tokens | Nur JSON-Status empfangen, keine vollen Outputs | JSON Output Contract: ~300 Tokens pro Task()-Return |
| Sequenzielle Planning-Phase | Integration Contracts erfordern vorherige Slices als Context | `previously_approved_slices` als Liste an slice-plan-coordinator übergeben |
| State muss Crash-sicher sein | State-File muss nach jedem Schritt aktuell sein | Write `.build-state.json` nach JEDEM Task()-Call |
| Bestehende Agents unverändert | Keine Breaking Changes an Worker-Agents | Coordinator-Agents wrappen bestehende Agents |
| Multi-Spec sequential | Ein Feature nach dem anderen | `current_spec_index` im State tracken |

### Integrations

| Area | System / Capability | Interface | Version | Notes |
|------|----------------------|-----------|---------|-------|
| Slice Planning | `slice-writer` Agent | Task() → Markdown file on disk | Current (unchanged) | Ebene 2, aufgerufen von slice-plan-coordinator |
| Slice Compliance | `slice-compliance` Agent | Task() → Markdown file on disk, VERDICT line | Current (unchanged) | Gate 2, Ebene 2 |
| Integration Map | `integration-map` Agent | Task() → 3 Markdown files on disk, VERDICT line | Current (unchanged) | Gate 3, Ebene 1 (direkt von /build) |
| Implementation | `slice-implementer` Agent | Task() → JSON `{status, files_changed, commit_hash}` | Current (unchanged) | Ebene 2 |
| Test Writing | `test-writer` Agent | Task() → JSON `{status, test_files, ac_coverage}` | Current (unchanged) | Ebene 2 |
| Test Validation | `test-validator` Agent | Task() → JSON `{overall_status, stages}` | Current (unchanged) | Ebene 2, two modes: `slice_validation`, `final_validation` |
| Debugging | `debugger` Agent | Task() → JSON `{status, root_cause, files_changed}` | Current (unchanged) | Ebene 2, conditional |
| Git | Git CLI | Bash: `git checkout -b`, `git push -u` | System git | Branch create, push |
| GitHub | GitHub CLI (`gh`) | Bash: `gh pr create` | System gh | PR creation |
| State Persistence | Filesystem | JSON read/write | N/A | `.build-state.json` |
| Evidence | Filesystem | JSON write | N/A | `.claude/evidence/{feature}/` |

---

## Quality Attributes (NFRs)

### From Discovery → Technical Solution

| Attribute | Target | Technical Approach | Measure / Verify |
|-----------|--------|--------------------|------------------|
| Context-Effizienz | Coordinator < 5.000 Tokens | JSON Output Contracts (~300 Tokens pro Return). Keine Inhalte, nur Referenzen | Token-Count im Coordinator während Lauf prüfen |
| Skalierbarkeit | 20+ Slices ohne Context-Overflow | Hierarchical Delegation: 3-Tier statt 1-Tier | Testen mit 10+ Slice Feature |
| Autonomie | Kein manueller Eingriff nach Start | Full loop: Planning → Gates → Implementation → PR | Manueller End-to-End-Test |
| Resume-Fähigkeit | Fortsetzen nach Crash/Abbruch | State-on-Disk nach JEDEM Schritt | Kill-Test: Process während Lauf beenden, re-run |
| Fehler-Transparenz | Klare Fehlermeldungen bei HARD STOP | State-File enthält `error` Field. Terminal-Output zeigt Phase + Slice + Fehlergrund | Review bei manuellen Test-Runs |
| Multi-Feature-Support | Mehrere Specs in einem Lauf | `specs[]` Array + `current_spec_index`. Sequenzielle Verarbeitung | Testen mit 2+ Specs |

### Monitoring & Observability

| Metric | Type | Target | Output |
|--------|------|--------|--------|
| Slices approved/total | Counter | All approved | Terminal output pro Slice |
| Slices completed/total | Counter | All completed | Terminal output pro Slice |
| Retries per slice | Counter | < 3 average | Logged in `.build-state.json` |
| Total duration | Timer | Depends on feature size | `started_at` → `completed_at` |

---

## Risks & Assumptions

### Assumptions

| Assumption | Technical Validation | Impact if Wrong |
|------------|---------------------|-----------------|
| Task()-Calls können 3-Tier-Deep erfolgen (Command → Coordinator → Worker) | Claude Code unterstützt nested Task()-Calls | Fallback: Coordinator-Agents inlinen die Worker-Logik statt zu delegieren |
| JSON-Parsing der Sub-Agent-Outputs ist zuverlässig | Bestehende `/orchestrate` Erfahrung: "Find LAST ```json``` block" | Fallback: Retry + HARD STOP |
| Bestehende Sub-Agents funktionieren unverändert in neuem Context | Gleiche Task()-Interface, gleiche Inputs/Outputs | Kein Fallback nötig — Agents sind bereits getestet |
| `.build-state.json` wird nicht durch Session-Compacting korrumpiert | State ist auf Disk, nicht im Context | N/A — genau dafür ist State-on-Disk |
| Git Branch-Erstellung funktioniert immer | Standard git operation | Fallback: HARD STOP mit Fehler |

### Risks & Mitigation

| Risk | Likelihood | Impact | Technical Mitigation | Fallback |
|------|------------|--------|---------------------|----------|
| Nested Task()-Tiefe nicht unterstützt | Low | High | Testen mit 3-Tier in isoliertem Szenario | Coordinator-Agents flach implementieren (alle Worker-Calls inline) |
| Context-Overflow trotz Hierarchical Delegation | Low | High | JSON Contracts < 300 Tokens. Coordinator liest nur State-File + Spec-Metadata | Fallback auf `/planner` + `/orchestrate` separat |
| Slice-Plan-Coordinator verliert Integration Context | Medium | Medium | Alle approved Slices als Pfad-Liste übergeben, Coordinator liest sie | Coordinator bekommt Summary statt voller Slices |
| State-File Race Condition (concurrent writes) | Very Low | Low | Sequenzielle Verarbeitung, kein Parallelismus im Coordinator | N/A |
| Multi-Spec: Feature B hängt von Feature A ab | Low | Medium | Sequenzielle Feature-Verarbeitung, Feature A muss completed sein | User kann Reihenfolge der spec_paths steuern |
| Gate 3 Retry-Loop: Slice-Writer-Fix ändert andere Slices | Medium | Medium | Slice-Plan-Coordinator übergibt nur betroffene Slice-ID | HARD STOP bei unerwarteten Änderungen |

---

## Technology Decisions

### Stack Choices

| Area | Technology | Rationale |
|------|------------|-----------|
| Command Format | Claude Code Command (`.claude/commands/*.md`) | Bestehende Konvention im Projekt |
| Agent Format | Claude Code Agent (`.claude/agents/*.md`) | Bestehende Konvention im Projekt |
| State Format | JSON File (`.build-state.json`) | Konsistent mit `.planner-state.json`, `.orchestrator-state.json` |
| Sub-Agent Invocation | `Task()` Tool | Claude Code native, unterstützt Fresh Context Pattern |
| Git Operations | `git` CLI via Bash | Standard, kein Extra-Tooling nötig |
| PR Creation | `gh` CLI via Bash | Bereits im Projekt verwendet (`.claude/settings.local.json`) |

### Trade-offs

| Decision | Pro | Con | Mitigation |
|----------|-----|-----|------------|
| 3-Tier statt 1-Tier | Context-Budget 10x reduziert. Skaliert auf 20+ Slices | Mehr Task()-Calls, höhere Latenz pro Slice | Akzeptabel: Latenz ist nicht kritisch für autonome Runs |
| Sequenzielle Planning | Integration Contracts konsistent | Langsamer als parallel | Notwendig: Slices bauen aufeinander auf |
| JSON Contracts statt Markdown | Parserbar, kompakt | Weniger lesbar für Humans | State-File + Evidence sind die Human-Readable Artifacts |
| Eigener State-File statt Reuse | Kein Conflict mit bestehenden Workflows | Dritter State-File-Typ im Projekt | Klare Abgrenzung: `/build` nutzt nur `.build-state.json` |

---

## Open Questions

| # | Question | Options | Recommended | Decision |
|---|----------|---------|-------------|----------|
| – | – | – | – | Alle Fragen in Discovery geklärt |

---

## Research Log

| Date | Area | Finding |
|------|------|---------|
| 2026-03-01 | Codebase | `/planner` Command: State-on-Disk Pattern mit `.planner-state.json`, max 9 Retries pro Slice, sequenzielle Planning, Gate 2 + Gate 3 |
| 2026-03-01 | Codebase | `/orchestrate` Command: Wave-basierte Implementation, 4-Step Sub-Agent Pipeline (Implementer → Test-Writer → Test-Validator → Debugger), Evidence-on-Disk |
| 2026-03-01 | Codebase | JSON Parse Pattern: "Find LAST ```json``` block" — kritisch für reliable Agent-Output-Parsing |
| 2026-03-01 | Codebase | Bestehende Agent-Contracts: slice-implementer/test-writer/test-validator/debugger alle mit dokumentierten JSON Output Contracts |
| 2026-03-01 | Codebase | State-File Location: immer `{spec_path}/.*-state.json` — konsistent für `.build-state.json` |
| 2026-03-01 | Codebase | Evidence Location: `.claude/evidence/{feature_name}/{slice_id}.json` — neueres Format mit Feature-Subdirectory |
| 2026-03-01 | Codebase | integration-map Agent: VERDICT-based output (nicht JSON), 3 Output-Files (integration-map.md, e2e-checklist.md, orchestrator-config.md) |
| 2026-03-01 | Codebase | Git/GitHub: `gh pr create` bereits in Projekt verwendet, Branch-Naming Convention: `feat/{feature-name}` |

---

## Q&A Log

| # | Question | Answer |
|---|----------|--------|
| – | Alle Fragen wurden in der Discovery-Phase geklärt | Siehe discovery.md Q&A Log (12 Fragen) |

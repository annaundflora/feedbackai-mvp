# Feature: /build Command - Unified Autonomous Feature Pipeline

**Epic:** --
**Status:** Ready
**Wireframes:** -- (CLI-only, keine UI)

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
| Neuer `slice-plan-coordinator` Agent (plant + validiert 1 Slice) |
| Neuer `slice-impl-coordinator` Agent (implementiert + testet 1 Slice) |
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

## Current State Reference

> Bestehende Funktionalität die wiederverwendet wird (unverändert).

- `/planner` Command (`.claude/commands/planner.md`) - Slice Planning + Gate 2 + Gate 3
- `/orchestrate` Command (`.claude/commands/orchestrate.md`) - Slice Implementation + Test Pipeline
- Alle Sub-Agents unverändert:
  - `slice-writer` - Schreibt Slice-Specs
  - `slice-compliance` - Gate 2 Checks
  - `integration-map` - Gate 3 (Integration + E2E + Orchestrator-Config)
  - `slice-implementer` - Implementiert Code
  - `test-writer` - Schreibt Tests gegen ACs
  - `test-validator` - Führt Test-Pipeline aus
  - `debugger` - Fixt fehlgeschlagene Tests
- State-on-Disk Pattern (`.planner-state.json`, `.orchestrator-state.json`)
- Evidence Pattern (`.claude/evidence/`)
- JSON Output Contract Pattern (alle Sub-Agents)

---

## Identifizierte Workflow-Patterns

> Offizielle Benennungen der im Projekt verwendeten Patterns.

| # | Pattern-Name | Quelle | Beschreibung |
|---|-------------|--------|--------------|
| 1 | **Fresh Context Pattern** | [Anthropic Multi-Agent Research](https://www.anthropic.com/engineering/multi-agent-research-system) | Jeder Sub-Agent bekommt eigenen Task() mit frischem Context. Verhindert Context Pollution & Confirmation Bias |
| 2 | **External Validation Pattern** | [Anthropic Building Effective Agents](https://www.anthropic.com/research/building-effective-agents) | Orchestrator testet, nicht der Implementer. Exit Code ist Wahrheit |
| 3 | **Hard Gate Pattern** | Eigenes Pattern | Max N Retries, dann HARD STOP. Kein Weitermachen bei Fehlern |
| 4 | **Evidence-on-Disk Pattern** | [Anthropic Context Engineering](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents) | Ergebnisse persistent gespeichert (`.claude/evidence/`). Entspricht "External Artifact Systems" |
| 5 | **State-on-Disk Pattern** | [Anthropic Long-Running Harnesses](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents) | JSON State-File für Resume-Fähigkeit. Entspricht "Checkpointing" |
| 6 | **Diverge-Converge Pattern** | Design Thinking | Erst breit recherchieren, dann konvergieren auf Scope und Details |
| 7 | **Multi-Gate Pipeline Pattern** | Eigenes Pattern | Sequenzielle Qualitätsprüfungen (Gate 0-3) mit automatischem Fix-Loop |
| 8 | **Slice Architecture Pattern** | Eigenes Pattern | Feature zerlegt in testbare Slices mit Dependency-Graph |
| 9 | **Sub-Agent Pipeline Pattern** | Eigenes Pattern | Implementer -> Test-Writer -> Test-Validator -> Debugger pro Slice |
| 10 | **JSON Output Contract Pattern** | [Phil Schmid Context Engineering](https://www.philschmid.de/context-engineering-part-2) | Sub-Agents returnen strukturiertes JSON. Entspricht "Agent-as-a-Tool MapReduce" |
| 11 | **Spec-as-Contract Pattern** | Eigenes Pattern | Slice-Specs sind das verbindliche Interface zwischen Planning und Execution |
| 12 | **Integration Contract Pattern** | Eigenes Pattern | "Requires From" / "Provides To" zwischen Slices |
| 13 | **Hierarchical Delegation Pattern** | NEU | Ultra-Lean Coordinator delegiert Batches an Coordinator-Sub-Agents, die ihrerseits Worker-Sub-Agents aufrufen. 3 Ebenen: Coordinator -> Slice-Coordinator -> Worker |
| 14 | **Reference Handoff Pattern** | [Anthropic Multi-Agent Research](https://www.anthropic.com/engineering/multi-agent-research-system) | Sub-Agents schreiben auf Disk und übergeben nur Pfad-Referenzen statt Inhalte |
| 15 | **Incremental Progress Pattern** | [Anthropic Long-Running Harnesses](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents) | Ein Feature/Slice nach dem anderen, State nach jedem Schritt persistiert |

---

## User Flow

1. User ruft `/build {spec_path}` oder `/build {spec_path_1} {spec_path_2}` auf
2. Build-Coordinator validiert Input (discovery.md, architecture.md müssen existieren)
3. Build-Coordinator erstellt Feature-Branch
4. **Planning Phase:** Für jeden Slice sequenziell:
   - Task(slice-plan-coordinator) -> plant + validiert Slice -> returns JSON {status, retries}
5. **Gate 3:** Task(integration-map) -> Integration Validation -> returns JSON {verdict}
6. **Implementation Phase:** Für jeden Slice (Reihenfolge aus orchestrator-config.md, parallele Waves wenn definiert):
   - Task(slice-impl-coordinator) -> implementiert + testet Slice -> returns JSON {status, evidence}
7. **Final Validation:** Task(test-validator: final_validation) -> returns JSON {status}
8. **Completion:** Push + PR erstellen + Feature-Evidence

**Error Paths:**
- Slice Planning Failed nach max Retries -> HARD STOP, State gespeichert
- Gate 3 Failed nach max Retries -> HARD STOP
- Slice Implementation Failed nach max Retries -> HARD STOP
- Final Validation Failed nach max Retries -> HARD STOP
- Multi-Spec: Bei Feature-Failure wird zum nächsten Feature gesprungen (optional)

---

## Feature State Machine

### States Overview

| State | UI (Terminal Output) | Available Actions |
|-------|----------------------|-------------------|
| `init` | "Validating inputs..." | Validate, Resume Check |
| `planning_slice_N` | "Planning Slice N/M..." | Task(slice-plan-coordinator) |
| `gate_3` | "Gate 3: Integration Validation..." | Task(integration-map) |
| `implementing_slice_N` | "Implementing Slice N/M..." | Task(slice-impl-coordinator) |
| `final_validation` | "Final Validation..." | Task(test-validator) |
| `completing` | "Creating PR..." | Push, PR Create |
| `completed` | "Feature Complete!" | -- |
| `failed` | "HARD STOP: {reason}" | Resume |

### Transitions

| Current State | Trigger | UI Feedback | Next State | Business Rules |
|---------------|---------|-------------|------------|----------------|
| `init` | Input valid | "Inputs validated" | `planning_slice_1` | discovery.md + architecture.md MUST exist |
| `init` | State-File exists | "Resuming from Slice N" | `planning_slice_N` or `implementing_slice_N` | Lese `.build-state.json` |
| `planning_slice_N` | Slice approved | "Slice N APPROVED" | `planning_slice_N+1` or `gate_3` | State-File Update |
| `planning_slice_N` | Max retries reached | "HARD STOP" | `failed` | 9 Retries pro Slice |
| `gate_3` | Verdict: READY | "Gate 3 APPROVED" | `implementing_slice_1` | -- |
| `gate_3` | Max retries reached | "HARD STOP" | `failed` | 9 Retries |
| `implementing_slice_N` | Evidence saved | "Slice N COMPLETED" | `implementing_slice_N+1` or `final_validation` | State-File Update |
| `implementing_slice_N` | Max retries reached | "HARD STOP" | `failed` | 9 Retries |
| `final_validation` | All passed | "Validation PASSED" | `completing` | -- |
| `completing` | PR created | "Feature Complete! PR: #N" | `completed` | -- |

---

## Business Rules

- Max 9 Retries pro Slice (Planning + Implementation jeweils)
- Max 9 Retries für Gate 3
- Planning ist sequenziell (Integration Contracts erfordern vorherige Slices)
- Implementation folgt der `orchestrator-config.md` Reihenfolge (Dependency-basierte Waves, parallele Slices innerhalb einer Wave wenn so definiert)
- Jeder Slice-Coordinator-Call gibt nur JSON zurück (~300 Tokens)
- State wird nach JEDEM Schritt auf Disk geschrieben
- Bei Resume: Lese State-File und setze bei letztem Schritt fort
- Multi-Spec: Features werden sequenziell verarbeitet
- Feature-Branch wird am Start erstellt, PR am Ende

---

## Data

### .build-state.json

| Field | Required | Validation | Notes |
|-------|----------|------------|-------|
| `specs` | Yes | Array of spec-paths | Multi-Spec Support |
| `current_spec_index` | Yes | int >= 0 | Welches Feature gerade verarbeitet wird |
| `status` | Yes | "in_progress" / "completed" / "failed" | Global Status |
| `phase` | Yes | "planning" / "gate_3" / "implementing" / "final_validation" / "completing" | Aktuelle Phase |
| `current_slice_index` | Yes | int >= 0 | Aktueller Slice |
| `total_slices` | Yes | int > 0 | Gesamtzahl Slices |
| `slices` | Yes | Array of {number, name, plan_status, impl_status, retries} | Slice-Tracking |
| `approved_slices` | Yes | Array of slice IDs | Für Planning-Phase |
| `completed_slices` | Yes | Array of slice IDs | Für Implementation-Phase |
| `failed_slices` | Yes | Array of slice IDs | Fehlerhafte Slices |
| `branch_name` | Yes | string | Feature-Branch Name |
| `started_at` | Yes | ISO timestamp | Start-Zeitpunkt |
| `last_updated` | Yes | ISO timestamp | Letztes Update |
| `completed_at` | No | ISO timestamp | Ende-Zeitpunkt |

---

## Architektur: Hierarchical Delegation

### Context-Budget-Vergleich

| Szenario | Task-Calls im Coordinator | Tokens im Coordinator |
|----------|--------------------------|----------------------|
| **Heute (/planner):** 7 Slices | ~14-42 Calls | ~14.000-42.000 |
| **Heute (/orchestrate):** 7 Slices | ~21-63 Calls | ~21.000-63.000 |
| **Heute (beide):** 7 Slices | ~35-105 Calls | ~35.000-105.000 |
| **NEU (/build):** 7 Slices | ~16 Calls | ~5.000 |

### 3-Ebenen-Architektur

```
Ebene 0: /build Command (Ultra-Lean Coordinator)
         - Liest State-File
         - Bestimmt nächsten Schritt
         - Dispatcht Task()-Calls
         - Empfängt nur JSON-Status (~300 Tokens pro Call)
         - Schreibt State-File

Ebene 1: Coordinator-Agents (Frischer Context pro Slice)
         - slice-plan-coordinator: plant + validiert 1 Slice
         - slice-impl-coordinator: implementiert + testet 1 Slice
         - Rufen bestehende Sub-Agents auf (Ebene 2)
         - Returnen JSON-Summary

Ebene 2: Worker-Agents (Bestehende Sub-Agents, unverändert)
         - slice-writer, slice-compliance
         - slice-implementer, test-writer, test-validator, debugger
         - integration-map
```

### Datenfluss-Diagramm

```
/build (Coordinator ~5.000 Tokens)
  │
  │ Liest: specs/*/discovery.md → extrahiert Slice-Liste
  │
  │── FOR EACH Slice (sequenziell, Dependency-Order):
  │   │
  │   ├── Task(slice-plan-coordinator)    ← 300 Tokens zurück
  │   │     │
  │   │     ├── Task(slice-writer)        ← schreibt slices/slice-NN.md
  │   │     ├── Task(slice-compliance)    ← schreibt slices/compliance-slice-NN.md
  │   │     ├── IF FAILED: retry loop (max 9)
  │   │     └── Return: {status: "approved", retries: N}
  │   │
  │   └── State Update → .build-state.json
  │
  │── Task(integration-map: Gate 3)       ← 300 Tokens zurück
  │     └── schreibt: integration-map.md, e2e-checklist.md, orchestrator-config.md
  │
  │── FOR EACH Wave (aus orchestrator-config.md, parallele Slices möglich):
  │   │
  │   ├── Task(slice-impl-coordinator)    ← 300 Tokens zurück (pro Slice in Wave)
  │   │     │
  │   │     ├── Task(slice-implementer)   ← schreibt Code + Commit
  │   │     ├── Task(test-writer)         ← schreibt Tests + Commit
  │   │     ├── Task(test-validator)      ← führt Tests aus
  │   │     ├── IF FAILED: Task(debugger) + retry loop (max 9)
  │   │     └── Return: {status: "completed", evidence: {...}}
  │   │
  │   └── State Update → .build-state.json + .claude/evidence/
  │
  │── Task(test-validator: final_validation) ← 300 Tokens zurück
  │
  └── Push + PR erstellen
```

---

## Implementation Slices

### Dependencies

```
Slice 1 (slice-plan-coordinator Agent)
   |
Slice 2 (slice-impl-coordinator Agent)
   |
Slice 3 (/build Command)
   |
Slice 4 (Multi-Spec Support)
   |
Slice 5 (Pattern-Dokumentation)
```

### Slices

| # | Name | Scope | Testability | Dependencies |
|---|------|-------|-------------|--------------|
| 1 | slice-plan-coordinator Agent | Neuer Agent `.claude/agents/slice-plan-coordinator.md`. Plant + validiert 1 Slice via Task(slice-writer) + Task(slice-compliance). Retry-Loop. Returns JSON. | Manuell: Agent mit einem Slice aufrufen, prüfen ob slices/ + compliance/ erstellt werden | -- |
| 2 | slice-impl-coordinator Agent | Neuer Agent `.claude/agents/slice-impl-coordinator.md`. Implementiert + testet 1 Slice via Task(slice-implementer) + Task(test-writer) + Task(test-validator) + Task(debugger). Returns JSON. | Manuell: Agent mit einem Slice aufrufen, prüfen ob Code + Tests + Evidence erstellt werden | -- |
| 3 | /build Command | Neuer Command `.claude/commands/build.md`. Ultra-Lean Coordinator. State-Management. Dependency-Graph. Branch + PR. | Manuell: /build mit bekannter Spec ausführen | 1, 2 |
| 4 | Multi-Spec Support | Erweiterung von /build für `/build spec_a spec_b`. Sequenzielle Feature-Verarbeitung. | Manuell: /build mit 2 Specs aufrufen | 3 |
| 5 | Pattern-Dokumentation | Dokumentation aller Workflow-Patterns in `.claude/agents/` oder Memory | Review | -- |

### Recommended Order

1. **Slice 1:** slice-plan-coordinator Agent -- Grundbaustein für Planning-Phase
2. **Slice 2:** slice-impl-coordinator Agent -- Grundbaustein für Implementation-Phase
3. **Slice 3:** /build Command -- Verbindet alles
4. **Slice 4:** Multi-Spec Support -- Erweiterung
5. **Slice 5:** Pattern-Dokumentation -- Optional, Wissen sichern

---

## Context & Research

### Anthropic Best Practices (Recherche)

| Source | Finding |
|--------|---------|
| [Anthropic: Context Engineering](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents) | "Minimal but Sufficient" - nur die nötigsten Tokens laden. Sub-Agents returnen condensed summaries (1.000-2.000 Tokens), nicht volle Outputs |
| [Anthropic: Long-Running Harnesses](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents) | "Incremental Progress" - ein Feature/Slice nach dem anderen. State in JSON-File (stabiler als Markdown). Progress-File als Kontrollinstanz |
| [Anthropic: Multi-Agent Research](https://www.anthropic.com/engineering/multi-agent-research-system) | "Fresh Context + Reference Handoffs" - Sub-Agents speichern auf Disk, übergeben nur Referenzen. Lead Agent hält nur Strategie und Status |
| [Phil Schmid: Context Engineering](https://www.philschmid.de/context-engineering-part-2) | "Agent-as-a-Tool MapReduce" - Sub-Agents wie Funktionen mit JSON I/O. "Share memory by communicating, don't communicate by sharing memory" |
| [Emergent Mind: Planner-Executor](https://www.emergentmind.com/topics/planner-executor-agentic-framework) | "Executor intentionally stateless" - bekommt nur nötigen Context pro Step. Intern: Think -> Act -> Observe -> Repeat |

### Similar Patterns in Codebase

| Feature | Location | Relevant because |
|---------|----------|------------------|
| `/planner` Command | `.claude/commands/planner.md` | Bestehender Planning-Loop mit State-File und Gate 2+3 |
| `/orchestrate` Command | `.claude/commands/orchestrate.md` | Bestehender Implementation-Loop mit Sub-Agent Pipeline |
| `slice-planner-orchestrator` Agent | `.claude/agents/slice-planner-orchestrator.md` | Dokumentiert die Prinzipien (Fresh Context, Hard Gates) |
| Orchestrator Agent | `.claude/agents/orchestrator.md` | Dokumentiert das Sub-Agent Pipeline Pattern |

---

## Q&A Log

| # | Frage | Antwort |
|---|-------|---------|
| 1 | Soll die Discovery recherchieren oder willst du direkt die essenziellen Fragen beantworten? | Erst Recherche |
| 2 | Was ist der Scope dieser Discovery? Nur Planner + Orchestrator zusammenführen, oder auch den gesamten Workflow optimieren? | Fokus auf Planner + Orchestrator zusammenführen. Optimierungen für andere Teile optional |
| 3 | Was genau soll der zusammengeführte Command machen? Welcher Startpunkt? | Ab fertiger Spec (nach Gates). Planning (Slices + Gates) UND Execution (Implementierung + Tests) in einem Lauf |
| 4 | Was soll das Verhalten bei Fehlern sein? | Voll autonom (max Retries, dann HARD STOP). Kein User-Input während des Loops |
| 5 | Wo soll der neue Command leben? Und wie soll er heißen? | `/build` - Kurz, klar. /build {spec_path} |
| 6 | Sollen die alten Commands erhalten bleiben? | Parallel behalten. /planner und /orchestrate existieren weiterhin |
| 7 | Dein Kernproblem ist Context-Überfüllung. Was hast du beobachtet? | Bei langen Planner-Runs mit vielen Retries und 7+ Slices wird Context voll. Läuft 2-4h. Will zusätzlich Implementation und größere Arbeitspakete (mehrere Discoveries) |
| 8 | Welches Pattern soll /build verwenden? | Hierarchical Delegation. Aber so, dass der alte Workflow erhalten bleibt (Planner + Orchestrate weiterhin nutzbar) |
| 9 | Wie groß sollen die Waves (Batches) sein? | 1 Slice pro Coordinator-Call. Dependencies werden eingehalten |
| 10 | Sollen Slices parallel verarbeitet werden? | Planning: Sequenziell (Integration Contracts). Implementation: Wie in orchestrator-config.md definiert (Waves mit optionaler Parallelisierung) |
| 11 | Soll /build mehrere Specs verarbeiten können? | Ja, Multi-Spec-Support |
| 12 | Soll /build Feature-Branch + Push + PR machen? | Branch + Commits + PR (voller Lifecycle) |

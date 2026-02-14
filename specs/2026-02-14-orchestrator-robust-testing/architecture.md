# Architecture: Lean Testing Pipeline for Agentic Development

**Epic:** --
**Status:** Draft
**Discovery:** `discovery.md` (same folder)
**Derived from:** Discovery constraints, NFRs, and risks

---

## Problem & Solution

**Problem:**
- Orchestrator hat 1 von 9 Quality Gates effektiv (nur Unit Tests mit exit_code)
- Pre-Impl Gates definiert aber nie enforced
- Slice-Implementer schreibt Code UND Tests gleichzeitig -- Tests validieren den Code, nicht die Spec
- Keine Acceptance Tests, kein Smoke Test, keine Regression Detection
- Final Validation auf TypeScript hardcoded -- Python-Backend wird uebersprungen

**Solution:**
- Test-Writer als separater Agent mit Fresh Context -- schreibt Tests gegen Spec, nicht gegen eigenen Code
- Test-Validator Agent fuehrt alle Tests aus (Unit, Integration, Acceptance, Smoke, Regression)
- Orchestrator-Umbau -- delegiert ALLES an Sub-Agents, fuehrt selbst keine Bash-Commands aus
- Stack-agnostisch -- erkennt automatisch Framework, Test-Tool, Start-Command
- Test-Strategie im Planner -- Slice-Writer generiert Test-Strategy Metadata

**Business Value:**
- Hoehere Pass-Rate durch Acceptance Tests die gegen Spec validieren
- Fruehe Fehler-Erkennung durch Smoke + Regression nach jedem Slice
- Wiederverwendbar in jedem Repo (stack-agnostisch)
- Weniger Context Pollution durch Sub-Agent-Delegation

---

## Scope & Boundaries

| In Scope |
|----------|
| Test-Writer Agent erweitern -- AC-Test-Generation, stack-agnostisch, Acceptance Tests, AC-Coverage |
| Test-Validator Agent (NEU) -- Test-Ausfuehrung, Smoke Test, Regression, JSON-Output |
| Orchestrator-Umbau -- 4 Sub-Agent-Steps, Pre-Impl Sanity Check, 3 Retries |
| Slice-Implementer anpassen -- NUR Code, keine Tests |
| Stack-Detection -- Automatische Erkennung von Framework, Test-Tool, Start-Command |
| Planner Enhancement -- Test-Strategy Metadata in Slice-Spec |
| Gate 2 inhaltlich verbessern -- AC-Qualitaet statt Template-Checkboxen |

| Out of Scope |
|--------------|
| Performance/Load Testing |
| Security Testing (OWASP, Penetration) |
| Visual Regression Testing |
| Mutation Testing |
| Test-Flakiness-Detection |
| implement.md Agent (tot) |
| coding-standards-guardian (kein Mehrwert) |
| spec-scope-keeper (Test-Writer + ACs besser) |

---

## API Design

### Overview

| Aspect | Specification |
|--------|---------------|
| Style | Agent-to-Agent JSON Contracts (kein HTTP API) |
| Communication | Task Tool Invocations mit JSON Output |
| Validation | JSON-Parsing des letzten ```json``` Blocks im Agent-Output |

### Agent Interfaces (Input/Output Contracts)

Dies ist kein HTTP-API-Feature. Die "API" besteht aus Sub-Agent JSON-Contracts die der Orchestrator parsed.

#### Slice-Implementer Output Contract

| Field | Type | Required | Validation |
|-------|------|----------|------------|
| `status` | `"completed" \| "failed"` | Ja | Enum |
| `files_changed` | `string[]` | Ja | Relative Pfade |
| `commit_hash` | `string` | Ja | Git SHA |
| `notes` | `string` | Nein | Freitext |

#### Test-Writer Output Contract

| Field | Type | Required | Validation |
|-------|------|----------|------------|
| `status` | `"completed" \| "failed"` | Ja | Enum |
| `test_files` | `string[]` | Ja | Pfade zu Test-Dateien |
| `test_count.unit` | `number` | Ja | >= 0 |
| `test_count.integration` | `number` | Ja | >= 0 |
| `test_count.acceptance` | `number` | Ja | >= 0 |
| `ac_coverage.total` | `number` | Ja | Anzahl ACs in Spec |
| `ac_coverage.covered` | `number` | Ja | Anzahl ACs mit Test |
| `ac_coverage.missing` | `string[]` | Ja | Fehlende AC-IDs |
| `commit_hash` | `string` | Ja | Git SHA |

#### Test-Validator Output Contract

| Field | Type | Required | Validation |
|-------|------|----------|------------|
| `overall_status` | `"passed" \| "failed"` | Ja | Enum |
| `stages.unit.exit_code` | `number` | Ja | 0 = passed |
| `stages.unit.duration_ms` | `number` | Ja | > 0 |
| `stages.unit.summary` | `string` | Ja | z.B. "12 passed, 0 failed" |
| `stages.integration.exit_code` | `number` | Ja | 0 = passed |
| `stages.integration.summary` | `string` | Ja | -- |
| `stages.acceptance.exit_code` | `number` | Ja | 0 = passed |
| `stages.acceptance.summary` | `string` | Ja | -- |
| `stages.smoke.app_started` | `boolean` | Ja | App konnte starten |
| `stages.smoke.health_status` | `number` | Ja | HTTP Status (200 = ok) |
| `stages.smoke.startup_duration_ms` | `number` | Ja | Max 30000ms |
| `stages.regression.exit_code` | `number` | Ja | 0 = passed |
| `stages.regression.slices_tested` | `string[]` | Ja | Vorherige Slice-IDs |
| `failed_stage` | `string` | Wenn failed | Stage-Name |
| `error_output` | `string` | Wenn failed | Stderr/Stdout |

#### Debugger Output Contract

| Field | Type | Required | Validation |
|-------|------|----------|------------|
| `status` | `"fixed" \| "unable_to_fix"` | Ja | Enum |
| `root_cause` | `string` | Ja | Kurze Beschreibung |
| `files_changed` | `string[]` | Ja | Pfade |
| `commit_hash` | `string` | Wenn fixed | Git SHA |

---

## Database Schema

**N/A** -- Agent Infrastructure Feature. Keine Datenbank-Aenderungen.

Persistenz erfolgt ueber:
- Agent-Definitionen: `.claude/agents/*.md` (Markdown)
- Orchestrator State: `{spec_path}/.orchestrator-state.json` (JSON)
- Evidence: `.claude/evidence/{feature_name}/*.json` (JSON)

---

## Server Logic

### Services & Processing

Da dies Agent Infrastructure ist, sind die "Services" die Agent-Definitionen und ihre Verantwortlichkeiten:

| Agent | Responsibility | Input | Output | Side Effects |
|-------|----------------|-------|--------|--------------|
| **Slice-Implementer** | Code schreiben (NUR Code, KEINE Tests) | Slice-Spec, Architecture, Integration-Map | `{ status, files_changed, commit_hash }` | Git Commit |
| **Test-Writer** | Tests schreiben gegen Spec (nicht gegen Code) | Slice-Spec (ACs), files_changed, Test-Strategy | `{ test_files, test_count, ac_coverage, commit_hash }` | Git Commit |
| **Test-Validator** (NEU) | Tests ausfuehren, Smoke, Regression | Test-Commands, Start-Command, Health-Endpoint, Previous Slice Tests | `{ stages, regression, overall_status }` | Keine (read-only) |
| **Debugger** | Fehler analysieren und fixen | Failed Stage Output, Slice-Spec, geaenderte Dateien | `{ status, root_cause, files_changed, commit_hash }` | Git Commit |
| **Orchestrator** | Koordination aller Sub-Agents | orchestrator-config.md, Slice-Specs | State-File, Evidence-Files | State-Updates |

### Orchestrator Pipeline Flow

```
Pre-Impl Sanity Check
  ↓
FOR each Slice:
  ↓
  Task(slice-implementer) → Code
  ↓
  Task(test-writer) → Tests
  ↓
  Task(test-validator) → Validate (Unit → Integration → Acceptance → Smoke → Regression)
  ↓
  IF failed: Task(debugger) → Fix → Re-validate (max 3x)
  ↓
  Evidence speichern
  ↓
Final Validation (Lint → Type Check → Build → Full Smoke → Full Regression)
```

### Agent Invocation Rules

| Rule | Description |
|------|-------------|
| Fresh Context | Jeder Sub-Agent bekommt eigenen Context (kein Context Pollution) |
| JSON Contract | Output muss letzter ```json``` Block sein, Orchestrator parsed diesen |
| Parse Failure | Bei JSON-Parse-Failure: HARD STOP |
| No Direct Bash | Orchestrator fuehrt KEINE Bash-Commands direkt aus (delegiert an Test-Validator) |
| Exit Code Truth | `exit_code == 0` = PASSED, alles andere = FAILED |

---

## Security

### Authentication & Authorization

**N/A** -- Agent Infrastructure. Keine User-Authentication.

| Area | Mechanism | Notes |
|------|-----------|-------|
| Agent Invocation | Task Tool Permission System | Claude Code Permission Mode |
| File Access | Sandbox Restrictions | Agents koennen nur im Repo lesen/schreiben |
| Bash Execution | User Approval | Destruktive Commands brauchen Approval |

### Data Protection

| Data Type | Protection | Notes |
|-----------|------------|-------|
| Evidence Files | Local-only | Keine Secrets in Evidence |
| Agent Outputs | In-Memory | Werden nicht persistiert (nur Evidence-Extrakt) |
| State File | Local-only | Enthaelt keine sensiblen Daten |

### Input Validation & Sanitization

| Input | Validation | Sanitization |
|-------|------------|--------------|
| Agent JSON Output | JSON.parse des letzten ```json``` Blocks | Bei Parse-Failure: HARD STOP |
| Test Exit Code | Integer Check | 0 = passed, != 0 = failed |
| File Paths | Relative zum Repo-Root | Keine absoluten Pfade |

---

## Architecture Layers

### Layer Responsibilities

| Layer | Responsibility | Pattern | Files |
|-------|----------------|---------|-------|
| **Orchestrator** (Command) | Pipeline-Koordination, State-Management, Evidence | Orchestrator-Workers | `.claude/commands/orchestrate.md` |
| **Sub-Agents** (Agents) | Spezialisierte Aufgaben mit Fresh Context | Specialized Workers | `.claude/agents/{name}.md` |
| **Templates** | Spec-Formate, Output-Strukturen | Template Pattern | `.claude/templates/*.md` |
| **Evidence Store** | Nachweisbare Test-Ergebnisse | Append-only Log | `.claude/evidence/{feature}/` |
| **State Store** | Resume-faehiger Orchestrator State | State Machine | `{spec_path}/.orchestrator-state.json` |

### Data Flow

```
orchestrator-config.md → Orchestrator
                           ↓
                    [Pre-Impl Check]
                           ↓
              ┌────────────┴────────────┐
              ↓                         ↓
    Slice-Spec + Architecture     Integration-Map
              ↓                         ↓
              └────────────┬────────────┘
                           ↓
                  Task(slice-implementer)
                      ↓ { files_changed }
                  Task(test-writer)
                      ↓ { test_files, ac_coverage }
                  Task(test-validator)
                      ↓ { stages, overall_status }
                           ↓
              ┌────── passed? ──────┐
              ↓                     ↓
         Evidence Store      Task(debugger)
                                    ↓
                             Re-validate (max 3x)
```

### Error Handling Strategy

| Error Type | Handling | Recovery | Limit |
|------------|----------|----------|-------|
| Test Failure | Debugger Sub-Agent | Auto-fix + Re-validate | 3 Retries |
| JSON Parse Failure | HARD STOP | Manuelles Eingreifen | Kein Retry |
| Implementer Failure | HARD STOP | Spec-Problem | Kein Retry |
| Test-Writer Failure | HARD STOP | Spec-Problem (unklare ACs) | Kein Retry |
| AC-Coverage < 100% | HARD STOP | Fehlende ACs in Spec | Kein Retry |
| Smoke Timeout (>30s) | Stage Failure | Debugger fixt | 3 Retries |
| Regression Failure | Stage Failure | Debugger fixt | 3 Retries |

---

## Constraints & Integrations

### Constraints

| Constraint | Technical Implication | Solution |
|------------|----------------------|----------|
| Stack-agnostisch | Keine hardcoded Commands (pytest, vitest, etc.) | Stack-Detection Matrix + generierte Commands |
| Fresh Context Pattern | Sub-Agents sehen nicht den Orchestrator-Context | Task Tool mit vollstaendigem Prompt |
| Exit Code als Wahrheit | Keine Interpretation von Test-Output (67% != passed) | `exit_code == 0` ist einzige Wahrheit |
| Implementer/Tester Trennung | Implementer darf KEINE Tests schreiben | Enforcement in Agent-Definition |
| Tests als Ground Truth | Debugger fixt Code, NICHT Tests | Enforcement in Debugger-Prompt (Ausnahme: technische Test-Fehler) |
| Agent Output JSON | Letzter ```json``` Block wird geparsed | Strikte Format-Anforderung in Agent-Prompts |
| Health-Endpoint ohne externe Services | Smoke Test muss auch ohne DB/APIs funktionieren | Health-Endpoint prueft nur App-Start, nicht Dependencies |

### Integrations

| Area | System / Capability | Interface | Notes |
|------|----------------------|-----------|-------|
| Task Tool | Claude Code Sub-Agent System | `Task(subagent_type, prompt)` | Fresh Context per Invocation |
| Bash Tool | Shell Command Execution | `Bash(command)` | Fuer Test-Validator (via Sub-Agent) |
| Git | Version Control | `git commit`, `git add` | Atomic Commits per Agent-Step |
| File System | Evidence + State | `Read()`, `Write()` | JSON Files |
| Health Endpoint | App Smoke Test | HTTP GET | Stack-abhaengige URL |

### Stack-Detection Matrix

| Indicator File | Stack | Test Framework | Test Command Pattern | Start Command | Health Endpoint |
|----------------|-------|---------------|---------------------|---------------|-----------------|
| `pyproject.toml` + fastapi dep | Python/FastAPI | pytest | `python -m pytest {path} -v` | `uvicorn app.main:app --host 0.0.0.0 --port 8000` | `http://localhost:8000/health` |
| `requirements.txt` + fastapi | Python/FastAPI | pytest | `python -m pytest {path} -v` | `uvicorn app.main:app --host 0.0.0.0 --port 8000` | `http://localhost:8000/health` |
| `package.json` + next dep | TypeScript/Next.js | vitest + playwright | `pnpm test {path}` | `pnpm dev` | `http://localhost:3000/api/health` |
| `package.json` + express dep | TypeScript/Express | vitest | `pnpm test {path}` | `node server.js` | `http://localhost:3000/health` |
| `go.mod` | Go | go test | `go test {path}` | `go run .` | `http://localhost:8080/health` |

---

## Quality Attributes (NFRs)

### From Discovery -> Technical Solution

| Attribute | Target | Technical Approach | Measure / Verify |
|-----------|--------|--------------------|------------------|
| Reliability | Hoehere Pass-Rate als IST-Zustand (1/9 Gates) | 5 Test-Stages (Unit, Integration, Acceptance, Smoke, Regression) + 3 Retries | Evidence JSON: `overall_status: passed` Rate |
| Stack-Agnostik | Funktioniert in jedem Repo | Stack-Detection Matrix, generierte Commands, keine hardcoded Tools | Manuell: Pipeline in Python-Repo UND Node-Repo testen |
| Context Pollution Prevention | Orchestrator bleibt schlank ueber lange Sessions | ALLE Ausfuehrung via Sub-Agents (Fresh Context) | Orchestrator fuehrt 0 Bash-Commands direkt aus |
| Resume-Faehigkeit | Pipeline kann nach Failure/Abbruch fortgesetzt werden | `.orchestrator-state.json` mit completed_slices, current_wave | Manuell: /orchestrate nach HARD STOP fortsetzen |
| Nachweisbarkeit | Jeder Test-Run dokumentiert | Evidence JSON pro Slice + Feature-Complete | Evidence-Dateien existieren in `.claude/evidence/` |
| Spec-Treue | Tests validieren Spec, nicht Code | Test-Writer liest Spec (ACs), nicht Implementer-Code | AC-Coverage Report: `ac_coverage.total == ac_coverage.covered` |

### Monitoring & Observability

| Metric | Type | Target | Where |
|--------|------|--------|-------|
| `overall_status` per Slice | Pass/Fail | 100% passed | Evidence JSON |
| `ac_coverage` per Slice | Ratio | 100% (total == covered) | Test-Writer Output |
| `retries` per Slice | Counter | < 3 (avg < 1) | Evidence JSON |
| `stages.smoke.startup_duration_ms` | Duration | < 30000ms | Test-Validator Output |
| `stages.regression.slices_tested` | List | Alle vorherigen Slices | Test-Validator Output |

---

## Risks & Assumptions

### Assumptions

| Assumption | Technical Validation | Impact if Wrong |
|------------|---------------------|-----------------|
| Health-Endpoint existiert in jedem Projekt | Stack-Detection prueft auf `/health` Route | Smoke Test schlaegt fehl → Slice-Writer muss Health-Route als Deliverable aufnehmen |
| Sub-Agents returnen valides JSON | Strikte Prompt-Anforderung + JSON-Parse Check | HARD STOP bei Parse-Failure |
| Debugger kann async/sync Mismatches fixen | Evidence: 4/4 in Backend-Kern | Mehr Retries noetig oder manuelles Eingreifen |
| AC Coverage ist messbar | Test-Writer zaehlt ACs aus Spec und Tests | Falls ACs unzaehlbar: manuelle Coverage |
| App startet innerhalb 30s | Timeout im Smoke Test | Timeout erhoehen oder Background-Start |

### Risks & Mitigation

| Risk | Likelihood | Impact | Technical Mitigation | Fallback |
|------|------------|--------|---------------------|----------|
| Test-Writer generiert nicht-lauffaehige Tests | Medium | Medium | Test-Validator erkennt (exit_code != 0) → Debugger fixt | HARD STOP nach 3 Retries |
| Smoke Test false-positive (App startet aber ist broken) | Low | Low | Smoke prueft nur Start + Health (nicht Business-Logik) | Acceptance Tests fangen Business-Bugs |
| Regression Tests zu langsam bei vielen Slices | Low | Medium | Aktuell alle re-run (MVP) | Spaeter: Smart Selection (nur betroffene Tests) |
| Stack-Detection erkennt Stack nicht | Low | High | Fallback: Slice-Writer fragt User via AskUserQuestion | Manuelles Eintragen der Commands |
| Context Pollution trotz Fresh Context | Low | Medium | Sub-Agent Prompts enthalten nur relevante Infos | Prompt-Laenge begrenzen |
| JSON-Parse des Agent-Outputs schlaegt fehl | Medium | High | Strikte Anforderung im Prompt + Beispiel-JSON | HARD STOP |

---

## Technology Decisions

### Stack Choices

| Area | Technology | Rationale |
|------|------------|-----------|
| Agent Definitions | Markdown Files (`.claude/agents/*.md`) | Bestehende Konvention, Claude Code nativ |
| Command Definitions | Markdown Files (`.claude/commands/*.md`) | Bestehende Konvention |
| State Persistence | JSON Files | Einfach, menschenlesbar, Git-versionierbar |
| Evidence Store | JSON Files pro Slice | Nachweisbar, auditierbar |
| Test Execution | Bash via Sub-Agent | Stack-agnostisch, Exit Code als Ground Truth |
| Health Check | HTTP GET auf Stack-abhaengige URL | Universell, keine Dependencies |

### Trade-offs

| Decision | Pro | Con | Mitigation |
|----------|-----|-----|------------|
| Alle Tests re-run (Regression) | Sicher, einfach, keine Luecken | Langsam bei vielen Slices | Smart Selection als spaetere Optimierung |
| Test-Validator als eigener Agent | Fresh Context, kein Pollution | Mehr Agent-Overhead | Minimal: Agent ist lightweight (nur Bash) |
| Implementer darf keine Tests schreiben | Tests validieren Spec, nicht Code | Implementer hat Context den Test-Writer nicht hat | Test-Writer bekommt `files_changed` Liste |
| 3 Retries (statt 2) | Mehr Stages = mehr Fehlerpotenzial | Laengere Laufzeit bei Failures | HARD STOP nach 3 begrenzt Dauer |
| JSON im letzten Code-Block | Einfaches Parsing, backward-compatible | Fragil bei unerwarteten Outputs | Strikte Prompt-Anforderung + Parse-Failure = HARD STOP |
| Health-Endpoint ohne DB-Check | Smoke Test funktioniert ohne externe Services | Missed DB-Connection-Bugs | Integration Tests decken DB ab |
| Auto-fix Lint vor Blocking Check | Weniger False Positives | Automatische Code-Aenderungen | Nur formatierbare Issues (ruff --fix, eslint --fix) |

---

## Agent Definitions (Aenderungen)

### Geaenderte Agents

| Agent | Datei | Aenderung | Slice |
|-------|-------|-----------|-------|
| test-writer | `.claude/agents/test-writer.md` | AC-Generation aus GIVEN/WHEN/THEN, stack-agnostisch, Acceptance Tests, Test-File-Naming (`tests/acceptance/test_{slice_id}.py`), AC-Coverage-Report | 1 |
| slice-implementer | `.claude/agents/slice-implementer.md` | "Tests schreiben" Regeln entfernen, NUR Code. JSON Output Contract anpassen | 3 |
| debugger | `.claude/agents/debugger.md` | Keine Aenderung | -- |

### Neue Agents

| Agent | Datei | Verantwortung | Slice |
|-------|-------|---------------|-------|
| test-validator | `.claude/agents/test-validator.md` | Test-Ausfuehrung aller Stages, Smoke Test, Regression Run, JSON-Output | 2 |

### Geaenderte Commands

| Command | Datei | Aenderung | Slice |
|---------|-------|-----------|-------|
| orchestrate | `.claude/commands/orchestrate.md` | 4 Sub-Agent-Steps, Pre-Impl Sanity Check, JSON-Parsing, 3 Retries, kein direktes Bash | 3 |

### Geaenderte Templates

| Template | Datei | Aenderung | Slice |
|----------|-------|-----------|-------|
| plan-spec | `.claude/templates/plan-spec.md` | Test-Strategy Metadata Section hinzufuegen | 4 |

### Geaenderte Planner/Gate Agents

| Agent | Datei | Aenderung | Slice |
|-------|-------|-----------|-------|
| slice-writer | `.claude/agents/slice-writer.md` | Stack-Detection, Test-Strategy Metadata generieren | 4 |
| slice-compliance | `.claude/agents/slice-compliance.md` | Inhaltliche Pruefung (AC-Qualitaet, Code Example Korrektheit) statt Template-Checkboxen, Max 1 Retry | 4 |

---

## Orchestrator State Machine (Erweitert)

### States

| State | Description | Entry Condition |
|-------|-------------|-----------------|
| `pre_check` | Compliance-Files pruefen | Orchestrator Start |
| `implementing` | Slice-Implementer schreibt Code | Pre-Check passed |
| `writing_tests` | Test-Writer schreibt Tests | Implementer completed |
| `validating` | Test-Validator fuehrt Tests aus | Test-Writer completed |
| `auto_fixing` | Debugger analysiert + fixt | Validation failed, retries < 3 |
| `slice_complete` | Evidence gespeichert | Validation passed |
| `hard_stop` | 3x failed oder Parse-Error | Retries erschoepft |
| `final_validation` | Lint + Type + Build + Full Smoke + Full Regression | Alle Slices complete |
| `feature_complete` | Alles gruen | Final Validation passed |

### Transitions

| From | Trigger | To | Rules |
|------|---------|-----|-------|
| `pre_check` | Compliance OK | `implementing` | Quick Sanity, kein Full Re-Run |
| `pre_check` | Compliance fehlt/FAILED | `hard_stop` | "Planner muss zuerst laufen" |
| `implementing` | status: completed | `writing_tests` | Implementer darf KEINE Tests schreiben |
| `implementing` | status: failed | `hard_stop` | Nicht auto-fixbar |
| `writing_tests` | Tests + AC-Coverage 100% | `validating` | -- |
| `writing_tests` | status: failed | `hard_stop` | Spec-Problem |
| `writing_tests` | AC-Coverage < 100% | `hard_stop` | Fehlende ACs klaeren |
| `validating` | overall_status: passed | `slice_complete` | Alle Stages gruen |
| `validating` | overall_status: failed, retries < 3 | `auto_fixing` | -- |
| `validating` | overall_status: failed, retries >= 3 | `hard_stop` | HARD STOP mit Evidence |
| `auto_fixing` | status: fixed | `validating` | Re-run ab fehlgeschlagenem Stage |
| `auto_fixing` | status: unable_to_fix | `hard_stop` | Manuell noetig |
| `slice_complete` | Evidence saved | `implementing` (naechster) | -- |
| letzter `slice_complete` | Alle Slices fertig | `final_validation` | -- |
| `final_validation` | Alles gruen | `feature_complete` | -- |
| `final_validation` | Failure, retries < 3 | `auto_fixing` | -- |

---

## Evidence Format (Erweitert)

### Per-Slice Evidence

```json
{
  "feature": "{feature_name}",
  "slice": "{slice_id}",
  "timestamp": "ISO 8601",
  "status": "completed | failed",
  "implementation": {
    "status": "completed",
    "files_changed": ["..."],
    "commit_hash": "abc123"
  },
  "tests": {
    "status": "completed",
    "test_files": ["..."],
    "test_count": { "unit": 5, "integration": 2, "acceptance": 3 },
    "ac_coverage": { "total": 3, "covered": 3, "missing": [] },
    "commit_hash": "def456"
  },
  "validation": {
    "overall_status": "passed",
    "stages": {
      "unit": { "exit_code": 0, "duration_ms": 1200, "summary": "5 passed" },
      "integration": { "exit_code": 0, "duration_ms": 3400, "summary": "2 passed" },
      "acceptance": { "exit_code": 0, "duration_ms": 2100, "summary": "3 passed" },
      "smoke": { "app_started": true, "health_status": 200, "startup_duration_ms": 4500 },
      "regression": { "exit_code": 0, "slices_tested": ["slice-01", "slice-02"] }
    }
  },
  "retries": 0
}
```

---

## Test-Strategy Metadata (Slice-Writer Output)

### Format (in Slice-Spec Metadata Section)

| Key | Value | Description |
|-----|-------|-------------|
| `stack` | Auto-detected | z.B. "python-fastapi", "typescript-nextjs" |
| `test_command` | Generated | Unit Test Command (z.B. `python -m pytest tests/unit/... -v`) |
| `integration_command` | Generated | Integration Test Command |
| `acceptance_command` | Generated | Acceptance Test Command |
| `start_command` | Generated | App Start Command |
| `health_endpoint` | Generated | Health-Check URL |
| `mocking_strategy` | Determined | `mock_external`, `no_mocks`, `test_containers` |

### Test-File Conventions

| Test Type | Path Pattern (Python) | Path Pattern (TypeScript) |
|-----------|----------------------|--------------------------|
| Unit | `tests/unit/test_{module}.py` | `tests/unit/{module}.test.ts` |
| Integration | `tests/integration/test_{module}.py` | `tests/integration/{module}.test.ts` |
| Acceptance | `tests/acceptance/test_{slice_id}.py` | `tests/acceptance/{slice_id}.test.ts` |
| Slice (Legacy) | `tests/slices/{feature}/test_{slice_id}.py` | `tests/slices/{feature}/{slice_id}.test.ts` |

---

## Final Validation (Stack-agnostisch)

### Validation Steps

| Step | Python | TypeScript | Blocking |
|------|--------|------------|----------|
| Auto-fix Lint | `ruff check --fix .` | `pnpm eslint --fix .` | Pre-step |
| Lint Check | `ruff check .` | `pnpm lint` | Ja (nach Auto-fix) |
| Type Check | `mypy .` (falls konfiguriert) | `pnpm tsc --noEmit` | Ja |
| Build | `pip install -e .` (falls setup.py) | `pnpm build` | Ja |
| Full Smoke | Start App + Health Check | Start App + Health Check | Ja |
| Full Regression | Alle Slice-Tests re-run | Alle Slice-Tests re-run | Ja |

---

## Open Questions

| # | Question | Options | Recommended | Decision |
|---|----------|---------|-------------|----------|
| -- | Alle offenen Fragen in Discovery geklaert | -- | -- | -- |

---

## Research Log

| Date | Area | Finding |
|------|------|---------|
| 2026-02-14 | Codebase | Orchestrator: 1/9 effektive Gates, nur Unit Tests |
| 2026-02-14 | Codebase | Pre-Impl Gates definiert aber nie enforced |
| 2026-02-14 | Codebase | Backend-Kern: 183 Tests, 4 Retries, Debugger 4/4 gefixt |
| 2026-02-14 | Codebase | Health-Endpoint existiert: `GET /health` → `{"status": "ok"}` (kein DB-Check) |
| 2026-02-14 | Codebase | Slice-Implementer schreibt aktuell Code + Tests (Regel "Tests schreiben" in Zeile 39) |
| 2026-02-14 | Codebase | Evidence-Format existiert: `.claude/evidence/backend-kern/slice-{NN}.json` |
| 2026-02-14 | Codebase | State-File existiert: `.orchestrator-state.json` |
| 2026-02-14 | Codebase | conftest.py ist leer -- Opportunity fuer zentrale Test-Fixtures |
| 2026-02-14 | Codebase | Test-Struktur: `backend/tests/slices/backend-kern/test_slice_{NN}_*.py` |
| 2026-02-14 | Codebase | Orchestrator fuehrt Tests direkt via Bash aus (Phase 3 Step 2) |
| 2026-02-14 | Codebase | Final Validation hardcoded: `pnpm lint`, `pnpm tsc --noEmit`, `pnpm build` |
| 2026-02-14 | Codebase | Debugger Agent funktioniert gut, keine Aenderung noetig |
| 2026-02-14 | Codebase | 25 Agent-Definitionen, 16 Command-Definitionen |
| 2026-02-14 | Git | Commit-Pattern: `feat(slice-NN):`, `fix(slice-NN):`, `chore:` |
| 2026-02-14 | Web | Anthropic: Fresh Context Sub-Agents, Ground Truth = Exit Code |
| 2026-02-14 | Web | app.build: Smoke Checks liefern meisten Reliability-Lift |

---

## Q&A Log

| # | Question | Answer |
|---|----------|--------|
| 1-13 | Siehe Discovery Q&A Log | Alle Fragen dort dokumentiert und entschieden |

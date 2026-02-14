# Feature: Lean Testing Pipeline for Agentic Development

**Epic:** --
**Status:** Draft
**Wireframes:** N/A (Agent Infrastructure, keine UI)

---

## Problem & Solution

**Problem:**
- Orchestrator hat **1 von 9 Quality Gates effektiv** (nur Unit Tests mit exit_code)
- Pre-Impl Gates (Architecture, Slice Compliance, Integration Map) sind definiert aber **werden nie enforced**
- Slice-Implementer schreibt Code UND Tests gleichzeitig -- Tests validieren den Code, nicht die Spec
- **Keine Acceptance Tests** -- GIVEN/WHEN/THEN in Slice-Specs werden nie zu ausfuehrbaren Tests
- **Kein Smoke Test** -- niemand prueft ob die App nach einem Slice noch startet
- **Keine Regression Detection** -- nach Slice 4 weiss niemand ob Slice 1-3 noch funktionieren
- Final Validation ist auf TypeScript hardcoded (Lint/Type/Build) -- **Python-Backend wird uebersprungen**
- Ergebnis: Qualitaet haengt vom Zufall ab, nicht vom Prozess

**Solution:**
- **Test-Writer als separater Agent** mit Fresh Context -- schreibt Tests gegen Spec, nicht gegen eigenen Code
- **Test-Validator Agent** fuehrt alle Tests aus (Unit, Integration, Acceptance, Smoke, Regression) -- kein Context Pollution im Orchestrator
- **Orchestrator-Umbau** -- delegiert ALLES an Sub-Agents, fuehrt selbst keine Bash-Commands aus
- **Stack-agnostisch** -- erkennt automatisch Framework, Test-Tool, Start-Command
- **Test-Strategie im Planner** -- Slice-Writer generiert Test-Strategy Metadata

**Business Value:**
- **Spuerbar hoehere Pass-Rate** durch Acceptance Tests die gegen Spec validieren
- **Fruehe Fehler-Erkennung** durch Smoke + Regression nach jedem Slice
- **Wiederverwendbar** -- Agent-Definitionen arbeiten in JEDEM Repo (stack-agnostisch)
- **Weniger Context Pollution** -- Orchestrator bleibt schlank durch Sub-Agent-Delegation

---

## Scope & Boundaries

| In Scope |
|----------|
| **Test-Writer Agent erweitern** -- Acceptance Test Generation aus GIVEN/WHEN/THEN, stack-agnostische Test-Templates |
| **Test-Validator Agent** (NEU) -- Fuehrt Tests aus, Smoke Test, Regression Run, strukturierter Evidence-Output |
| **Orchestrator-Umbau** -- 4 Sub-Agent-Steps statt direkter Bash, Pre-Impl Sanity Check |
| **Slice-Implementer anpassen** -- Schreibt NUR Code, keine Tests mehr |
| **Stack-Detection** -- Automatische Erkennung von Framework, Test-Tool, Start-Command |
| **Planner Enhancement** -- Test-Strategy Metadata in Slice-Spec Template |
| **Gate 2 (Slice Compliance) inhaltlich verbessern** -- Fokus auf AC-Qualitaet statt Template-Checkboxen |

| Out of Scope |
|--------------|
| Performance/Load Testing |
| Security Testing (OWASP, Penetration) |
| Visual Regression Testing |
| Mutation Testing |
| Test-Flakiness-Detection |
| implement.md Agent (tot, wird nicht beruecksichtigt) |
| coding-standards-guardian (kein bewiesener Mehrwert) |
| spec-scope-keeper (Test-Writer + ACs erfuellen den Zweck besser) |

---

## Current State Reference

> Existing functionality that will be reused (unchanged). NOT documented again in detail sections below.

- **Debugger Agent** (`.claude/agents/debugger.md`) -- funktioniert, keine Aenderung noetig. Hat 4/4 Retries in Backend-Kern erfolgreich gefixt.
- **Wave-basierte Parallelisierung** -- Slices innerhalb einer Wave parallel, zwischen Waves sequenziell. Bleibt erhalten.
- **Evidence-Struktur** (`.claude/evidence/{feature_name}/`) -- Speicherort und Grundformat bleiben bestehen (wird erweitert, nicht ersetzt).
- **Slice-Spec Format** -- GIVEN/WHEN/THEN Acceptance Criteria in Slice-Specs. Backend-Kern hat gute ACs produziert ohne zusaetzliche Instructions.
- **Gate 1 (Architecture Compliance)** -- Definiert, wird weiterhin als Pre-Impl Check referenziert.
- **Gate 3 (Integration Map)** -- Bleibt wie bisher mit 3 Retries.
- **Orchestrator State-Tracking** (`.orchestrator-state.json`) -- State-File-Mechanismus bleibt, Inhalte werden erweitert.

> Greenfield-Anteil: Test-Validator Agent (komplett neu), Acceptance Test Generation, Smoke Test, Regression Detection.

---

## User Flow

### Flow 1: Planning Phase (Test-Strategie im Planner)

1. **Slice-Writer erstellt Slice-Spec** (wie bisher, mit GIVEN/WHEN/THEN ACs)
2. Slice-Writer **erkennt Stack** (package.json? pyproject.toml? requirements.txt?)
3. Slice-Writer **generiert Test-Strategy Metadata:**
   - `test_command` (Unit Tests)
   - `integration_command` (Integration Tests)
   - `acceptance_command` (Acceptance Tests)
   - `start_command` (App starten)
   - `health_endpoint` (Health-Check URL)
   - `mocking_strategy` (mock_external, no_mocks, etc.)
4. **Gate 2 prueft inhaltlich:** Sind ACs testbar? Sind Test-Commands vollstaendig? Passen Code Examples zur Architecture?

### Flow 2: Implementation Phase (pro Slice im Orchestrator)

1. **Orchestrator prueft Pre-Impl** (Compliance-Files vorhanden + APPROVED?)
2. **Task(slice-implementer)** schreibt NUR Code (keine Tests!)
   - Input: Slice-Spec, Architecture, Integration-Map
   - Output: `{ status, files_changed, commit_hash }`
3. **Task(test-writer)** schreibt alle Tests gegen Spec
   - Input: Slice-Spec (ACs), files_changed, Test-Strategy (Metadata)
   - Output: `{ test_files, test_count, ac_coverage, commit_hash }`
4. **Task(test-validator)** fuehrt alles aus
   - Input: Test-Commands, Start-Command, Health-Endpoint, Previous Slice Test-Paths
   - Output: `{ stages{unit,integration,acceptance,smoke}, regression, overall_status }`
5. **Bei Failure:** Task(debugger) analysiert + fixt → Orchestrator re-ruft Task(test-validator)
6. **3x failed bei irgendeinem Stage:** HARD STOP

### Flow 3: Retry-Loop (bei Test-Failure)

1. Test-Validator meldet `overall_status: failed` mit Stage-Details
2. Orchestrator ruft **Task(debugger)** auf:
   - Input: Failed Stage Output, Exit Code, Slice-Spec, geaenderte Dateien
   - Output: `{ root_cause, files_changed, commit_hash }`
3. Orchestrator re-ruft **Task(test-validator)** (gleiche Inputs)
4. Max 3 Retries pro Slice, dann HARD STOP

### Flow 4: Final Validation (nach allen Slices)

1. **Task(test-validator)** mit erweitertem Scope:
   - Lint (stack-abhaengig: ruff/eslint)
   - Type Check (stack-abhaengig: mypy/tsc)
   - Build (stack-abhaengig: pip install/pnpm build)
   - Full Smoke Test (App starten, ALLE Endpoints pruefen)
   - Full Regression (ALLE Slice-Tests re-run)

**Error Paths:**
- Test-Writer generiert ungueltige Tests → Validator erkennt (exit_code != 0) → Debugger fixt
- App startet nicht (Import-Error, fehlende ENV) → Validator Smoke erkennt → Debugger fixt
- Regression (alter Slice bricht) → Validator Regression erkennt → Debugger fixt oder HARD STOP

---

## UI Layout & Context

**N/A** -- Agent Infrastructure, keine UI-Komponenten.

---

## UI Components & States

**N/A** -- Keine UI-Interaktion.

---

## Feature State Machine

### States Overview

| State | Beschreibung | Available Actions |
|-------|--------------|-------------------|
| `pre_check` | Orchestrator prueft Pre-Impl Gates | -- |
| `implementing` | Slice-Implementer schreibt Code (NUR Code) | -- |
| `writing_tests` | Test-Writer schreibt Tests gegen Spec | -- |
| `validating` | Test-Validator fuehrt Tests aus (Unit, Integration, Acceptance, Smoke, Regression) | -- |
| `auto_fixing` | Debugger analysiert Failure + fixt Code | -- |
| `slice_complete` | Alle Tests gruen, Evidence gespeichert | Save Evidence, Next Slice |
| `hard_stop` | 3x failed bei einem Slice | Manuell fixen, dann Resume |
| `final_validation` | Lint + Type + Build + Full Smoke + Full Regression | -- |
| `feature_complete` | Alles gruen, Feature fertig | Push, PR |

### Transitions

| Current State | Trigger | Next State | Business Rules |
|---------------|---------|------------|----------------|
| `pre_check` | Compliance-Files vorhanden + APPROVED | `implementing` | Quick Sanity Check, kein Full Re-Run |
| `pre_check` | Compliance-Files fehlen oder FAILED | `hard_stop` | "Planner muss zuerst laufen" |
| `implementing` | Implementer returnt `status: completed` | `writing_tests` | Implementer darf KEINE Tests schreiben |
| `writing_tests` | Test-Writer returnt Tests + AC-Coverage | `validating` | AC-Coverage muss 100% sein |
| `validating` | `overall_status: passed` | `slice_complete` | Alle Stages gruen (Unit, Integration, Acceptance, Smoke) |
| `validating` | `overall_status: failed` | `auto_fixing` | Retry-Count < 3 |
| `validating` | `overall_status: failed`, Retry >= 3 | `hard_stop` | HARD STOP mit Evidence |
| `implementing` | Implementer returnt `status: failed` | `hard_stop` | Implementer-Failure ist nicht auto-fixbar (Spec-Problem oder fundamentaler Fehler) |
| `writing_tests` | Test-Writer returnt `status: failed` | `hard_stop` | Test-Writer-Failure deutet auf Spec-Problem hin (unklare ACs, fehlende Imports) |
| `writing_tests` | AC-Coverage < 100% | `hard_stop` | Fehlende ACs muessen in der Spec geklaert werden, nicht im Code |
| `auto_fixing` | Debugger returnt `status: fixed` | `validating` | Re-run ab dem fehlgeschlagenen Stage (inkl. nachfolgende Stages, da Fix andere Stages beeinflussen kann) |
| `auto_fixing` | Debugger returnt `status: unable_to_fix` | `hard_stop` | Manuelles Eingreifen noetig |
| `slice_complete` | Evidence saved + Commit | `implementing` (naechster Slice) | -- |
| letzter Slice `slice_complete` | Alle Slices fertig | `final_validation` | -- |
| `final_validation` | Alles gruen | `feature_complete` | -- |
| `final_validation` | Failure | `auto_fixing` | Retry-Count < 3 |

---

## Business Rules

### Agent-Separation Rules

1. **Implementer schreibt NUR Code, KEINE Tests**
   - Test-Writer ist der EINZIGE Agent der Tests schreibt
   - Verhindert dass Tests den Code validieren statt die Spec

2. **Test-Writer schreibt NUR Tests, KEINEN Feature-Code**
   - Strikte Trennung Code vs. Tests
   - Test-Writer liest Spec (ACs) + Code (Imports/Signaturen), schreibt Tests dagegen

3. **Debugger fixt primaer Code, Tests nur bei technischen Fehlern**
   - Tests sind Ground Truth (abgeleitet aus Spec-ACs)
   - Bei Failure: **Code anpassen**, nicht Tests fachlich aufweichen
   - **Ausnahme:** Debugger darf Tests fixen bei technischen Fehlern (falsche Import-Pfade, Syntax-Fehler, async/sync Mismatch im Mock-Setup)
   - **Verboten:** Test-Assertions aendern, erwartete Werte anpassen, Tests auskommentieren

4. **Orchestrator fuehrt KEINE Bash-Commands direkt aus**
   - Alle Ausfuehrungen via Sub-Agents (Fresh Context, kein Context Pollution)
   - Orchestrator koordiniert nur, delegiert alles

### Test-Typ-Definitionen

5. **Drei Test-Typen mit klarer Abgrenzung**
   - **Unit Tests:** Isolierte Logik, alle Dependencies gemockt (DB, APIs, Services). Schnell, deterministisch. Validieren: interne Logik, Berechnungen, Validierung, Error Handling.
   - **Integration Tests:** Testen Zusammenspiel mehrerer Komponenten mit echten Dependencies (Test-DB, lokale Services). Validieren: DB-Queries, API-Routing, Middleware-Chain, Serialisierung.
   - **Acceptance Tests:** Abgeleitet aus GIVEN/WHEN/THEN in Slice-Specs. Testen fachliche Anforderungen End-to-End (via API-Call, nicht UI). Validieren: Business Rules, User Flows, Daten-Integritaet.

### Test Execution Rules

6. **Exit Code ist Wahrheit**
   - `exit_code == 0` = BESTANDEN
   - `exit_code != 0` = FEHLGESCHLAGEN (auch bei "67% bestehen")

7. **Auto-Fix + 3 Retries**
   - Bei Failure → Debugger analysiert + fixt → Re-run
   - Max 3 Retries pro Slice (Erhoehung von 2 auf 3 gegenueber IST-Zustand, weil mehr Stages = mehr Fehlerpotenzial)
   - Nach 3 Retries: HARD STOP mit Evidence
   - **Re-Run Scope:** Ab dem fehlgeschlagenen Stage inkl. aller nachfolgenden Stages (Fix kann andere Stages beeinflussen)

8. **Evidence-Based**
   - Jeder Test-Run → JSON Evidence (nachweisbar)
   - Exit Code, Output Summary, Duration, AC-Coverage
   - **Speicherort:** `.claude/evidence/{feature_name}/` (wie bisher)

### Stack-Detection Rules

9. **Auto-Detection ist Pflicht**
   - Agent MUSS Stack erkennen (nicht hardcoded)
   - Indicators: package.json, requirements.txt, pyproject.toml, Gemfile, pom.xml, etc.
   - Fallback: Agent fragt User via AskUserQuestion

10. **Test-Commands sind generiert, nicht konfiguriert**
   - Slice-Writer generiert Commands basierend auf erkanntem Stack
   - Kein manuelles Eintragen von `pytest -m unit tests/...`

### Acceptance Test Rules

11. **100% AC Coverage**
    - Jede GIVEN/WHEN/THEN in Slice-Spec MUSS einen Test haben
    - Test-Writer prueft Coverage und reportet `ac_coverage`

### Smoke Test Rules

12. **App MUSS starten koennen (Smoke Test)**
    - Test-Validator startet App mit erkanntem Start-Command
    - Health-Check Endpoint muss `200 OK` returnen
    - **Health-Endpoint MUSS ohne externe Services funktionieren** (kein DB-Check, kein API-Check)
    - **Timeout:** Max 30 Sekunden bis Health-Endpoint antwortet (danach Failure)
    - Smoke Test prueft Import-Chain + Konfiguration, NICHT Business-Logik

### Regression Rules

13. **Regression Detection nach jedem Slice**
    - Nach jedem Slice: ALLE vorherigen Slice-Tests re-run
    - Bei Regression: Debugger fixt oder HARD STOP

### Planner Gate Rules

14. **Gate 2 (Slice Compliance) prueft inhaltlich**
    - Fokus auf: Sind ACs testbar und spezifisch? Passen Code Examples zur Architecture?
    - NICHT: "Existiert Section X?" (Template-Checkbox)
    - Max 1 Retry (statt 3)

15. **Gate 3 (Integration Map) bleibt wie bisher**
    - 3 Retries gerechtfertigt (komplexer Cross-Slice Check)

### Parallel Execution Rules

16. **Wave-basierte Parallelisierung bleibt erhalten**
    - Slices innerhalb einer Wave KOENNEN parallel laufen (wenn `parallel: true` in orchestrator-config)
    - Slices zwischen Waves sind IMMER sequenziell
    - Test-Validator laeuft immer NACH allen Slices einer Wave

### Test-File Rules

17. **Test-Dateien Konventionen**
    - Unit + Integration Tests: `tests/unit/test_{module}.py` bzw. `tests/integration/test_{module}.py`
    - Acceptance Tests: `tests/acceptance/test_{slice_id}.py` (1 Datei pro Slice, direkt aus ACs abgeleitet)
    - Test-Writer benennt Dateien, Orchestrator trackt sie fuer Regression

### Agent Data-Transfer Rules

18. **Sub-Agent Output ist JSON im letzten Code-Block**
    - Jeder Sub-Agent returnt ein JSON-Objekt als letztes in seinem Output
    - Orchestrator parsed den letzten ```json``` Block aus dem Agent-Output
    - Bei Parse-Failure: HARD STOP (Agent hat unerwartetes Format geliefert)

---

## Data

### Agent-Interfaces (Input/Output Contracts)

#### Implementer Output

| Field | Required | Validation | Notes |
|-------|----------|------------|-------|
| `status` | Ja | `completed` oder `failed` | -- |
| `files_changed` | Ja | Liste von Dateipfaden | Relative zum Repo-Root |
| `commit_hash` | Ja | Git SHA | Commit mit `feat(slice-id): ...` |
| `notes` | Nein | String | Hinweise fuer Orchestrator |

#### Test-Writer Output

| Field | Required | Validation | Notes |
|-------|----------|------------|-------|
| `status` | Ja | `completed` oder `failed` | -- |
| `test_files` | Ja | Liste von Test-Dateipfaden | -- |
| `test_count.unit` | Ja | >= 0 | Anzahl Unit Tests |
| `test_count.integration` | Ja | >= 0 | Anzahl Integration Tests |
| `test_count.acceptance` | Ja | >= 0 | Anzahl Acceptance Tests |
| `ac_coverage.total` | Ja | Anzahl ACs in Spec | -- |
| `ac_coverage.covered` | Ja | Anzahl ACs mit Test | Ziel: total == covered |
| `ac_coverage.missing` | Ja | Liste fehlender ACs | Muss leer sein |
| `commit_hash` | Ja | Git SHA | Commit mit `test(slice-id): ...` |

#### Test-Validator Output

| Field | Required | Validation | Notes |
|-------|----------|------------|-------|
| `overall_status` | Ja | `passed` oder `failed` | -- |
| `stages.unit.exit_code` | Ja | 0 = passed | -- |
| `stages.unit.duration_ms` | Ja | > 0 | -- |
| `stages.unit.summary` | Ja | String | z.B. "12 passed, 0 failed" |
| `stages.integration.exit_code` | Ja | 0 = passed | -- |
| `stages.acceptance.exit_code` | Ja | 0 = passed | -- |
| `stages.smoke.app_started` | Ja | Boolean | App konnte gestartet werden |
| `stages.smoke.health_status` | Ja | HTTP Status Code | 200 = healthy |
| `stages.smoke.startup_duration_ms` | Ja | > 0 | Zeit bis Health-Endpoint antwortet (max 30000ms) |
| `stages.regression.exit_code` | Ja | 0 = passed | -- |
| `stages.regression.slices_tested` | Ja | Liste von Slice-IDs | Alle vorherigen Slices |
| `failed_stage` | Wenn failed | Stage-Name | Welcher Stage fehlgeschlagen |
| `error_output` | Wenn failed | String | Stderr/Stdout des fehlgeschlagenen Stages |

#### Debugger Output

| Field | Required | Validation | Notes |
|-------|----------|------------|-------|
| `status` | Ja | `fixed` oder `unable_to_fix` | -- |
| `root_cause` | Ja | String | Kurze Beschreibung der Ursache |
| `files_changed` | Ja | Liste von Dateipfaden | -- |
| `commit_hash` | Wenn fixed | Git SHA | Commit mit `fix(slice-id): ...` |

### Stack-Detection Matrix

| Indicator | Stack | Test Framework | Start Command | Health Endpoint |
|-----------|-------|---------------|---------------|-----------------|
| `pyproject.toml` + `fastapi` | Python/FastAPI | pytest | `uvicorn app.main:app` | `http://localhost:8000/health` |
| `requirements.txt` + `fastapi` | Python/FastAPI | pytest | `uvicorn app.main:app` | `http://localhost:8000/health` |
| `pyproject.toml` + `django` | Python/Django | pytest | `python manage.py runserver` | `http://localhost:8000/health` |
| `package.json` + `next` | TypeScript/Next.js | vitest + playwright | `pnpm dev` | `http://localhost:3000/api/health` |
| `package.json` + `express` | TypeScript/Express | vitest | `node server.js` | `http://localhost:3000/health` |
| `Gemfile` + `rails` | Ruby/Rails | rspec | `rails server` | `http://localhost:3000/up` |
| `pom.xml` | Java/Spring | junit | `mvn spring-boot:run` | `http://localhost:8080/actuator/health` |
| `go.mod` | Go | go test | `go run .` | `http://localhost:8080/health` |

### Evidence Format (Output pro Slice-Validation)

| Field | Required | Notes |
|-------|----------|-------|
| `feature` | Ja | Feature-Name |
| `slice` | Ja | Slice-ID |
| `timestamp` | Ja | ISO 8601 |
| `status` | Ja | `completed` oder `failed` |
| `implementation` | Ja | Implementer Output |
| `tests` | Ja | Test-Writer Output |
| `validation` | Ja | Test-Validator Output |
| `retries` | Ja | Anzahl Debugger-Retries |

---

## Implementation Slices

### Dependencies

```
Slice 1 (Test-Writer Enhancement)
    │
    ▼
Slice 2 (Test-Validator Agent) ← NEU
    │
    ▼
Slice 3 (Orchestrator Pipeline) ← Kern-Umbau
    │
    ▼
Slice 4 (Planner & Gate Improvements)
```

### Slices

| # | Name | Scope | Testbarkeit | Abhaengigkeiten |
|---|------|-------|-------------|-----------------|
| 1 | **Test-Writer Agent Enhancement** | test-writer.md erweitern: AC-Test-Generation aus GIVEN/WHEN/THEN, stack-agnostische Templates, Unit + Integration + Acceptance Tests, AC-Coverage-Report, Test-File-Naming (tests/acceptance/test_{slice_id}.py) | Agent gegen Backend-Kern Slice-Specs testen: schreibt er lauffaehige Tests mit 100% AC-Coverage? | -- |
| 2 | **Test-Validator Agent** (NEU) | Agent-Definition (.claude/agents/test-validator.md): Fuehrt alle Tests aus, Smoke Test (App starten + Health-Check, 30s Timeout, Health-Endpoint ohne externe Services), Regression Run (ALLE vorherige Slice-Tests), strukturierter JSON-Output, Auto-Fix Lint (ruff --fix / eslint --fix) | Agent gegen laufende FastAPI-App testen: fuehrt er Tests aus, erkennt er Health-Status, meldet er Regression? | Slice 1 |
| 3 | **Orchestrator Pipeline** | orchestrate.md umbauen: 4 Sub-Agent-Steps (Implementer → Test-Writer → Validator → Debugger), Pre-Impl Sanity Check (Compliance-Files), Evidence-Format erweitern, slice-implementer.md anpassen (Tests schreiben entfernen), JSON-Parsing fuer Agent-Outputs, 3 Retries (statt 2), Re-Run ab fehlgeschlagenem Stage | Orchestrator gegen Backend-Kern re-run testen: laeuft die neue Pipeline End-to-End? | Slice 1, 2 |
| 4 | **Planner & Gate Improvements** | Gate 2 (Slice Compliance) inhaltlich verbessern: AC-Qualitaet + Code Example Korrektheit statt Template-Checkboxen, Max 1 Retry. Slice-Writer: Test-Strategy Metadata generieren. plan-spec Template: Test-Strategy Section hinzufuegen. | Planner gegen neues Feature testen: generiert er Test-Strategy Metadata? Prueft Gate 2 inhaltlich? | Slice 3 |

### Empfohlene Reihenfolge

1. **Slice 1: Test-Writer Enhancement** -- Foundation: Ohne verbesserten Test-Writer keine AC-Tests
2. **Slice 2: Test-Validator Agent** -- Fuehrt Tests aus, Smoke, Regression. Braucht Test-Writer Output.
3. **Slice 3: Orchestrator Pipeline** -- Kern-Umbau: Neue Sub-Agent-Pipeline, JSON-Parsing, Retry-Logik
4. **Slice 4: Planner & Gate Improvements** -- Planner-Erweiterungen, Gate 2 inhaltlich verbessern

---

## Context & Research

### IST-Zustand Analyse (Quality Gates)

| Gate | Blocking | Hooked | Effektiv | Befund |
|------|----------|--------|----------|--------|
| Pre-Impl: Architecture Compliance | Ja | NEIN | NEIN | Definiert in Config, Orchestrator liest es nie |
| Pre-Impl: Slice Approvals | Ja | NEIN | NEIN | Compliance-Files werden nie geprueft |
| Pre-Impl: Integration Map | Ja | NEIN | NEIN | Als OPTIONAL markiert, nur Warning |
| **Unit Tests** | **Ja** | **JA** | **JA** | Einziger effektiver Gate. 183/183 Tests in Backend-Kern |
| E2E Tests | Ja | Dormant | Nein | Nie konfiguriert/aktiviert |
| Lint | Nein | Ja | Schwach | Non-blocking, Warnings passieren |
| Type Check | Ja | Ja | N/A | Nur fuer TypeScript |
| Build | Ja | Ja | N/A | Nur fuer TypeScript |
| Consumer-File-Check | Nein | Ja | Schwach | Non-blocking, nur Warning |

### Evidence aus Backend-Kern (6 Slices)

| Slice | Unit Tests | Retries | Fehler-Typ |
|-------|-----------|---------|------------|
| 01 App-Skeleton | 22 passed | 0 | -- |
| 02 LangGraph | 23 passed | 0 | -- |
| 03 SSE-Streaming | 39 passed | 1 | async/sync Mocking |
| 04 Supabase | 28 passed | 1 | async/sync Mocking |
| 05 Summary | 37 passed | 1 | async/sync Mocking |
| 06 Timeout | 34 passed | 1 | async/sync Mocking |
| **Total** | **183 passed** | **4 Retries** | Debugger hat alle 4 gefixt |

### Bestehende Agents (Aenderungsbedarf)

| Agent | Datei | Aenderung | Slice |
|-------|-------|-----------|-------|
| test-writer | `.claude/agents/test-writer.md` | AC-Generation, stack-agnostisch, Acceptance Tests, Test-File-Naming | 1 |
| test-validator (NEU) | `.claude/agents/test-validator.md` | Neue Agent-Definition: Test-Ausfuehrung, Smoke, Regression, JSON-Output | 2 |
| slice-implementer | `.claude/agents/slice-implementer.md` | "Tests schreiben" entfernen, NUR Code | 3 |
| orchestrate | `.claude/commands/orchestrate.md` | Kompletter Umbau: 4 Sub-Agent-Steps, JSON-Parsing, 3 Retries, Re-Run-Scope | 3 |
| debugger | `.claude/agents/debugger.md` | Keine Aenderung (funktioniert) | -- |
| planner | `.claude/commands/planner.md` | Gate 2 inhaltlich verbessern (AC-Qualitaet, Code Example Korrektheit) | 4 |
| slice-writer | `.claude/agents/slice-writer.md` | Test-Strategy Metadata generieren | 4 |
| plan-spec Template | `.claude/templates/plan-spec.md` | Test-Strategy Section hinzufuegen | 4 |

### Web Research

| Source | Finding | Validiert |
|--------|---------|-----------|
| TestSprite Benchmarks (eigene Daten) | 93% Pass-Rate mit Test-Suite vs. 42% ohne | Ja, aber eigene Benchmarks |
| Anthropic: Building Effective Agents | Ground Truth = Exit Code, Orchestrator-Workers Pattern, Evaluator-Optimizer Loop | Ja (Architektur-Patterns, keine Test-Pipeline-Vorschrift) |
| Anthropic: Effective Harnesses | Sub-Agents mit Fresh Context fuer lange Sessions | Ja |
| AugmentCode: Spec-Driven Development | 87.2% Accuracy mit Specs vs. 19.36% ohne | Ja |
| GitHub Spec Kit | Spec → Plan → Tasks → Implement (4-Phase Workflow) | Ja |
| app.build Research (300 App-Generations) | Lightweight Smoke Checks liefern meisten Reliability-Lift | Ja |
| SWE-bench Analysis | Kein klarer Nachweis dass Implementer/Tester-Trennung Outcomes verbessert | Teilweise |
| Tricentis: Agentic Testing 2026 | 85% weniger Manual Effort mit Agentic Testing | Ja |

### Eliminierte Gates (mit Begruendung)

| Gate | Warum eliminiert |
|------|-----------------|
| Non-blocking Lint | Kein Mehrwert als Warning. Wenn blocking, dann im Final Validation. |
| Consumer-File-Check | Zu noisy, niedriges Signal. Integration Map + Tests fangen das besser. |
| coding-standards-guardian | War nur in totem implement.md. Kein bewiesener Mehrwert. |
| spec-scope-keeper | War nur in totem implement.md. Test-Writer + AC-Tests erfuellen den Zweck besser. |
| Gate 2 Template-Checkboxen | "Existiert Section X?" hat nie was gefangen. LLMs schreiben immer alle Sections. |

---

## Open Questions

| # | Question | Options | Recommended | Decision |
|---|----------|---------|-------------|----------|
| 1 | Wie handhabt Test-Validator externe Services (DB, APIs) beim Smoke Test? | A) Testcontainers B) Test-Schema C) Mocks D) Health-only | D) Health-only | **D) Smoke Test prueft NUR ob App startet + Health-Endpoint antwortet (HTTP 200). Health-Endpoint muss OHNE externe Services funktionieren (kein DB-Check, kein API-Check). Prueft Import-Chain + Konfiguration. Business-Logik wird durch Unit/Integration/Acceptance Tests abgedeckt.** |
| 2 | Soll Regression alle vorherigen Tests re-run oder nur die, deren Dateien sich geaendert haben? | A) Alle (sicher) B) Smart Selection (schneller) | A) Alle | **A) Alle vorherigen Slice-Tests re-run. MVP-Ansatz: sicher, einfach, kein Risiko durch transitive Dependencies. Smart Selection als spaetere Optimierung.** |
| 3 | Soll Lint in Final Validation blocking oder non-blocking sein? | A) Blocking B) Non-blocking C) Auto-fix + blocking | C) Auto-fix + blocking | **C) Erst Auto-fix (ruff --fix / eslint --fix), dann Check. Wenn Auto-fix nicht alles loest → blocking (HARD STOP). Debugger fixt verbleibende Lint-Fehler.** |

---

## Research Log

| Date | Area | Finding |
|------|------|---------|
| 2026-02-14 | Codebase | Orchestrator hat 1/9 effektive Gates (nur Unit Tests) |
| 2026-02-14 | Codebase | Pre-Impl Gates definiert aber nie enforced |
| 2026-02-14 | Codebase | Backend-Kern: 183 Tests, 4 Retries, Debugger hat alle gefixt |
| 2026-02-14 | Codebase | implement.md Agent wird nie benutzt (tot) |
| 2026-02-14 | Codebase | slice-implementer schreibt Code + Tests gleichzeitig |
| 2026-02-14 | Codebase | conftest.py ist leer -- Opportunity fuer zentrale Test-Fixtures |
| 2026-02-14 | Web | TestSprite: 93% vs 42% (eigene Benchmarks, nicht unabhaengig) |
| 2026-02-14 | Web | Anthropic: Fresh Context Sub-Agents fuer lange Sessions |
| 2026-02-14 | Web | AugmentCode: 87.2% Accuracy mit Specs |
| 2026-02-14 | Web | app.build: Smoke Checks liefern meisten Reliability-Lift |
| 2026-02-14 | Web | SWE-bench: Implementer/Tester-Trennung nicht klar bewiesen |
| 2026-02-14 | Web | ATDD/Spec-Driven ist Industriestandard 2025-2026 |

---

## Q&A Log

| # | Frage | Antwort |
|---|-------|---------|
| 1 | Soll die Discovery komplett neu geschrieben werden mit klarem Delta zum Status Quo? | Erst Q&A, dann entscheiden. User wollte offene Punkte zuerst klaeren. |
| 2 | Was genau fehlt am bestehenden Orchestrator? Was funktioniert nicht? | implement.md wird gar nicht benutzt, nur /orchestrate. Bestehende Quality Gates scheinen nicht alle wirksam. Ziel: Workflow der sinnvolle Teile behaelt und Testing komplett neu definiert. Prinzip: Sub-Agents mit Fresh Context. |
| 3 | Wie soll die Discovery aufgebaut werden? (Pragmatisch Fix+Extend / Ambitioniert / Hybrid) | Fokus auf neues Testing-Konzept. Vorschlagen was wertstiftend ist und was eliminiert werden soll. Aktuell wirkt es over-engineered -- Gates werden definiert aber nicht benutzt und bringen keine spuerbare Qualitaet. |
| 4 | Soll implement.md beruecksichtigt werden? | Tot, ignorieren. Nur /orchestrate ist der Workflow. |
| 5 | Wie sollen Test-Sub-Agents aufgeteilt werden? | Smoke und Regression als eigene Sub-Agents (nicht Bash im Orchestrator) wegen Context Pollution ueber lange Sessions. |
| 6 | Stack-agnostisch oder projekt-spezifisch? | Stack-agnostisch. User hat MEHRERE Projekte. |
| 7 | Wie soll das Planner-Template fuer ACs verbessert werden? | Bleibt wie es ist. Backend-Kern hat gute ACs produziert ohne zusaetzliche Instructions. |
| 8 | Tests in der Planning Phase (executable) oder Implementation Phase? | Test-STRATEGIE im Planner, Test-CODE in der Implementation Phase. Tests muessen echten Code importieren. |
| 9 | Gate 2 vereinfachen oder eliminieren? | Vereinfachen: Inhaltliche Pruefung (AC-Qualitaet, Code Example Korrektheit) statt Template-Checkboxen. Max 1 Retry. |
| 10 | Wie handhabt Test-Validator externe Services beim Smoke Test? | Smoke Test prueft NUR ob App startet + Health-Endpoint antwortet (HTTP 200). Health-Endpoint muss OHNE externe Services funktionieren. Max 30s Timeout. |
| 11 | Regression: Alle Tests re-run oder Smart Selection? | Alle vorherigen Slice-Tests re-run (MVP). Smart Selection als spaetere Optimierung. |
| 12 | Lint in Final Validation blocking? | Auto-fix erst (ruff --fix / eslint --fix), dann Check. Verbleibende Fehler sind blocking. |
| 13 | Soll Slice 3 aufgeteilt werden? | Ja, in 2 Slices: Slice 3 (Orchestrator Pipeline Kern-Umbau) + Slice 4 (Planner/Gate Improvements). |

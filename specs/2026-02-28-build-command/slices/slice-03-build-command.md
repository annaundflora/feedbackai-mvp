# Slice 3: /build Command erstellen

> **Slice 3 von 5** fuer `build-command`
>
> | Navigation | |
> |------------|---|
> | **Vorheriger:** | `slice-02-slice-impl-coordinator.md` |
> | **Naechster:** | `slice-04-multi-spec-support.md` |

---

## Metadata (fuer Orchestrator)

| Key | Value |
|-----|-------|
| **ID** | `slice-03-build-command` |
| **Test** | `N/A (manueller Test - Command-Datei)` |
| **E2E** | `false` |
| **Dependencies** | `["slice-01-slice-plan-coordinator", "slice-02-slice-impl-coordinator"]` |

---

## Test-Strategy (fuer Orchestrator Pipeline)

> **Quelle:** Auto-detected basierend auf Repo-Indikatoren. Dashboard nutzt Next.js + Vitest + Playwright.
> Dieser Slice erstellt eine Command-Markdown-Datei, keine ausfuehrbaren Code-Dateien.

| Key | Value |
|-----|-------|
| **Stack** | `claude-code-command` (Markdown Command Definition) |
| **Test Command** | `N/A` (Command-Datei, kein ausfuehrbarer Code) |
| **Integration Command** | `N/A` |
| **Acceptance Command** | `Manuell: /build mit bekannter Spec ausfuehren, pruefen ob Planning + Gate 3 + Implementation + PR durchlaeuft` |
| **Start Command** | `N/A` |
| **Health Endpoint** | `N/A` |
| **Mocking Strategy** | `no_mocks` |

---

## Slice-Uebersicht

| # | Slice | Status | Datei |
|---|-------|--------|-------|
| 1 | slice-plan-coordinator Agent | Ready | `slice-01-slice-plan-coordinator.md` |
| 2 | slice-impl-coordinator Agent | Ready | `slice-02-slice-impl-coordinator.md` |
| 3 | **/build Command** | Ready | `slice-03-build-command.md` |
| 4 | Multi-Spec Support | Pending | `slice-04-multi-spec-support.md` |
| 5 | Pattern-Dokumentation | Pending | `slice-05-pattern-dokumentation.md` |

---

## Kontext & Ziel

Der `/build` Command ist der Ultra-Lean Coordinator (Ebene 0), der Planning + Gate 3 + Implementation + Final Validation + PR-Erstellung in einem autonomen Loop ausfuehrt. Er delegiert die eigentliche Arbeit an Ebene-1-Coordinator-Agents (`slice-plan-coordinator`, `slice-impl-coordinator`) und empfaengt nur kompakte JSON-Ergebnisse (~300 Tokens pro Call).

**Problem:** `/planner` und `/orchestrate` sind separate Commands mit manuellem Wechsel. Bei 7+ Slices mit Retries fuellt sich der Coordinator-Context (35.000-105.000 Tokens). Session-Compacting zerstoert wichtigen State mitten im Lauf.

**Loesung:** Der `/build` Command vereint Planning + Execution in einem Loop. Durch Hierarchical Delegation bleibt der Coordinator-Context bei ~5.000 Tokens. State-on-Disk (`.build-state.json`) ermoeglicht Resume nach Crash/Abbruch.

---

## Technische Umsetzung

### Architektur-Kontext (aus architecture.md)

> **Quelle:** `architecture.md` -> "Architecture Layers", "Business Logic Flow", "State-on-Disk", "Error Handling Strategy", "Resume Logic"

```
/build Command (Ebene 0, ~5.000 Tokens Context)
  |
  +-- Input Validation (discovery.md + architecture.md MUST exist)
  +-- Git Branch Create: feat/{feature-name}
  |
  +-- Planning Phase (Sequential)
  |   FOR EACH Slice:
  |     Task(slice-plan-coordinator) -> JSON {status, retries, slice_file}
  |     Update .build-state.json
  |
  +-- Gate 3: Task(integration-map) -> VERDICT
  |   READY -> continue
  |   GAPS FOUND -> retry (max 9)
  |
  +-- Implementation Phase (Wave-based)
  |   Parse orchestrator-config.md -> Waves
  |   FOR EACH Wave -> FOR EACH Slice:
  |     Task(slice-impl-coordinator) -> JSON {status, evidence, retries}
  |     Update .build-state.json
  |
  +-- Final Validation: Task(test-validator, mode=final_validation)
  |   passed -> continue
  |   failed -> Task(debugger) + retry (max 9)
  |
  +-- Completion: git push + gh pr create
```

### 1. Architektur-Impact

| Layer | Aenderungen |
|-------|------------|
| `.claude/commands/` | Neue Datei `build.md` |

### 2. Datenfluss

```
Input: $ARGUMENTS (spec_path, z.B. "specs/2026-02-28-build-command")
  |
  v
Phase 1: Input Validation
  |  Pruefe: {spec_path}/discovery.md EXISTS
  |  Pruefe: {spec_path}/architecture.md EXISTS
  |  Pruefe: {spec_path}/.build-state.json? -> Resume or Init
  |
  v
Phase 2: Git Branch (if not resume)
  |  git checkout -b feat/{feature-name}
  |
  v
Phase 3: State Initialization
  |  Extrahiere Slice-Liste aus discovery.md "## Implementation Slices"
  |  Schreibe initiale .build-state.json
  |
  v
Phase 4: Planning Phase (Sequential)
  |  FOR i = 0 to total_slices-1:
  |    Task(slice-plan-coordinator) -> JSON ~300 Tokens
  |    Parse JSON (letzter ```json``` Block)
  |    IF status == "approved": update state, continue
  |    IF status == "failed": HARD STOP
  |
  v
Phase 5: Gate 3 (Integration Validation)
  |  Task(integration-map) -> Reads VERDICT from output files
  |  IF "VERDICT: READY FOR ORCHESTRATION": continue
  |  IF "VERDICT: GAPS FOUND": retry (max 9), then HARD STOP
  |
  v
Phase 6: Implementation Phase (Wave-based)
  |  Parse orchestrator-config.md -> Waves
  |  FOR EACH Wave:
  |    FOR EACH Slice in Wave:
  |      Task(slice-impl-coordinator) -> JSON ~300 Tokens
  |      Parse JSON (letzter ```json``` Block)
  |      IF status == "completed": update state, continue
  |      IF status == "failed": HARD STOP
  |
  v
Phase 7: Final Validation
  |  Task(test-validator, mode=final_validation) -> JSON
  |  IF overall_status == "passed": continue
  |  IF overall_status == "failed":
  |    Task(debugger) -> retry (max 9)
  |    Re-validate after each fix
  |
  v
Phase 8: Completion
  |  git push -u origin feat/{feature-name}
  |  gh pr create --title "feat: {feature-name}" --body "..."
  |  Update state: status = "completed", completed_at = now()
  |
  v
Output: "Feature Complete! PR: #{pr_number}"
```

### 3. State-Aenderungen: `.build-state.json`

```json
{
  "specs": ["specs/2026-02-28-build-command"],
  "current_spec_index": 0,
  "status": "in_progress",
  "phase": "planning",
  "current_slice_index": 0,
  "total_slices": 5,
  "slices": [
    {
      "number": 1,
      "name": "slice-plan-coordinator",
      "plan_status": "pending",
      "impl_status": "pending",
      "plan_retries": 0,
      "impl_retries": 0
    }
  ],
  "approved_slices": [],
  "completed_slices": [],
  "failed_slices": [],
  "gate3_retries": 0,
  "last_action": "Initialized",
  "branch_name": "feat/build-command",
  "started_at": "2026-03-01T10:00:00Z",
  "last_updated": "2026-03-01T10:00:00Z",
  "completed_at": null,
  "error": null
}
```

**Location:** `{spec_path}/.build-state.json`

### 4. Command-Prompt-Struktur

Der Command MUSS folgende Sections enthalten:

1. **YAML Frontmatter** - description
2. **Kritische Regeln** - Autonomer Betrieb, JSON-Parsing, 9 Retries, HARD STOP
3. **Phase 1: Input-Validierung** - Spec-Path validieren, Required Files pruefen
4. **Phase 2: State & Resume** - `.build-state.json` lesen/erstellen, Resume-Logik
5. **Phase 3: Git Branch** - `feat/{feature-name}` Branch erstellen
6. **Phase 4: Planning Phase** - Sequenziell Task(slice-plan-coordinator) pro Slice
7. **Phase 5: Gate 3** - Task(integration-map), VERDICT pruefen, Retry-Loop
8. **Phase 6: Implementation Phase** - Wave-basiert Task(slice-impl-coordinator) pro Slice
9. **Phase 7: Final Validation** - Task(test-validator, mode=final_validation), Debugger bei Fehler
10. **Phase 8: Completion** - Git push, PR erstellen, State abschliessen

### 5. Task()-Call Prompts (KRITISCH)

#### Slice-Plan-Coordinator Prompt:

```
Plane und validiere Slice {slice_number}: {slice_name}

## Input
- spec_path: {spec_path}
- slice_number: {slice_number}
- slice_name: {slice_name}
- slice_description: {slice_description}
- slice_dependencies: {slice_dependencies}
- approved_slices_paths: {approved_slices_paths}

## Anweisungen
1. Lies discovery.md, architecture.md, wireframes.md (falls vorhanden)
2. Lies vorherige genehmigte Slices fuer Integration Contract Kontext
3. Rufe Task(slice-writer) auf um den Slice zu erstellen
4. Rufe Task(slice-compliance) auf um den Slice zu validieren
5. Bei VERDICT: FAILED -> Retry mit Fix-Prompt (max 9 Retries)
6. Gib am Ende ein JSON zurueck

## Output
Gib am Ende ein JSON zurueck:
```json
{
  "status": "approved | failed",
  "retries": 0,
  "slice_file": "slices/slice-01-slug.md",
  "blocking_issues": []
}
```
```

#### Integration-Map Prompt (Gate 3):

```
Erstelle Integration Map + E2E Checklist + Orchestrator Config.

## Input
- spec_path: {spec_path}
- Alle Slices: {spec_path}/slices/slice-*.md
- Architecture: {spec_path}/architecture.md

## Output
Schreibe drei Dateien:
1. {spec_path}/integration-map.md
2. {spec_path}/e2e-checklist.md
3. {spec_path}/orchestrator-config.md

Am Ende MUSS stehen:
VERDICT: READY FOR ORCHESTRATION
oder
VERDICT: GAPS FOUND
MISSING_INPUTS: [...]
AFFECTED_SLICES: [...]
```

#### Gate 3 Retry Prompt (bei GAPS FOUND):

```
Fixe Integration Gaps in Slices.

## Gaps
{gaps_from_integration_map}

## Betroffene Slices
{affected_slices}

## Anweisungen
1. Lies die Integration-Map mit den identifizierten Gaps
2. Fixe die betroffenen Slice-Specs
3. Fuehre anschliessend Integration-Map erneut aus

Am Ende MUSS stehen:
VERDICT: READY FOR ORCHESTRATION oder VERDICT: GAPS FOUND
```

#### Slice-Impl-Coordinator Prompt:

```
Implementiere und teste Slice: {slice_id}

## Input
- spec_path: {spec_path}
- slice_id: {slice_id}
- slice_file: {spec_path}/slices/{slice_file}
- architecture_path: {spec_path}/architecture.md
- integration_map_path: {spec_path}/integration-map.md

## Anweisungen
1. Lies die Slice-Spec, Architecture und Integration-Map
2. Rufe Task(slice-implementer) auf
3. Rufe Task(test-writer) auf
4. Rufe Task(test-validator) auf
5. Bei Test-Failure: Task(debugger) + Re-Validate (max 9 Retries)
6. Schreibe Evidence nach .claude/evidence/
7. Gib am Ende ein JSON zurueck

## Output
Gib am Ende ein JSON zurueck:
```json
{
  "status": "completed | failed",
  "retries": 0,
  "evidence": {
    "files_changed": [],
    "test_files": [],
    "test_count": 0,
    "commit_hash": "abc123"
  },
  "error": null
}
```
```

#### Test-Validator Final Validation Prompt:

```
Fuehre Final Validation fuer das gesamte Feature aus.

## Mode
final_validation

## Input
- spec_path: {spec_path}
- Alle Slice-Specs: {spec_path}/slices/slice-*.md

## Anweisungen
1. Lies die Test-Strategy aus den Slice-Specs
2. Fuehre ALLE Tests aus (Unit, Integration, Acceptance, Smoke)
3. Gib strukturiertes JSON zurueck

## Output
```json
{
  "overall_status": "passed | failed",
  "stages": {
    "unit": {"status": "passed | failed", "test_count": 0, "failed_count": 0},
    "integration": {"status": "passed | failed", "test_count": 0, "failed_count": 0},
    "acceptance": {"status": "passed | failed", "test_count": 0, "failed_count": 0},
    "smoke": {"status": "passed | failed", "app_started": true, "health_status": 200}
  },
  "error_output": null
}
```
```

#### Debugger Prompt (Final Validation Failure):

```
Debugge fehlgeschlagene Final Validation.

## Fehlgeschlagene Test-Ausgabe
{error_output_from_test_validator}

## Input
- spec_path: {spec_path}
- Architecture: {spec_path}/architecture.md

## Anweisungen
1. Analysiere die Fehlerausgabe
2. Formuliere eine Hypothese
3. Fixe den Root Cause
4. Committe den Fix

## Output
```json
{
  "status": "fixed | unable_to_fix",
  "root_cause": "Beschreibung",
  "files_changed": []
}
```
```

### 6. Resume-Logik (KRITISCH)

```
IF .build-state.json EXISTS:
  state = Read(.build-state.json)

  IF state.status == "completed":
    OUTPUT: "Build bereits abgeschlossen fuer diese Spec."
    STOP

  IF state.status == "failed":
    OUTPUT: "Letzter Build fehlgeschlagen: {state.error}"
    OUTPUT: "Setze fort ab Phase {state.phase}, Slice {state.current_slice_index}..."
    # Reset status to in_progress
    state.status = "in_progress"
    state.error = null
    Write(.build-state.json, state)
    SKIP to state.phase at state.current_slice_index

  IF state.status == "in_progress":
    OUTPUT: "Fortsetzen von Phase {state.phase}, Slice {state.current_slice_index}..."
    SKIP to state.phase at state.current_slice_index

IF .build-state.json NOT EXISTS:
  # Fresh Start
  Initialize state
  Write(.build-state.json, state)
```

### 7. State-Update-Pattern (nach JEDEM Task()-Call)

```
# Nach jedem Task()-Call:
state.last_updated = now()
state.last_action = "{Beschreibung des letzten Schritts}"

# Bei Planning:
state.phase = "planning"
state.current_slice_index = i
state.slices[i].plan_status = "approved" | "failed"
state.slices[i].plan_retries = N
IF approved: state.approved_slices.push(slice_number)

# Bei Gate 3:
state.phase = "gate_3"
state.gate3_retries = N

# Bei Implementation:
state.phase = "implementing"
state.current_slice_index = i
state.slices[i].impl_status = "completed" | "failed"
state.slices[i].impl_retries = N
IF completed: state.completed_slices.push(slice_number)

# Bei Final Validation:
state.phase = "final_validation"

# Bei Completion:
state.phase = "completing"
state.status = "completed"
state.completed_at = now()

# Bei Fehler:
state.status = "failed"
state.error = "{Fehlerbeschreibung}"
IF slice failed: state.failed_slices.push(slice_number)

Write(.build-state.json, state)
```

### 8. HARD STOP Bedingungen

| Bedingung | Fehler-Output | State-Update |
|-----------|---------------|-------------|
| discovery.md fehlt | "STOP: discovery.md fehlt. Zuerst /discovery ausfuehren." | N/A (kein State erstellt) |
| architecture.md fehlt | "STOP: architecture.md fehlt. Zuerst /architecture ausfuehren." | N/A (kein State erstellt) |
| Slice Planning failed nach 9 Retries | "HARD STOP: Slice {N} Planning fehlgeschlagen nach 9 Retries" | status=failed, error="{...}" |
| Gate 3 failed nach 9 Retries | "HARD STOP: Gate 3 fehlgeschlagen nach 9 Retries" | status=failed, error="{...}" |
| Slice Implementation failed nach 9 Retries | "HARD STOP: Slice {N} Implementation fehlgeschlagen nach 9 Retries" | status=failed, error="{...}" |
| Final Validation failed nach 9 Retries | "HARD STOP: Final Validation fehlgeschlagen nach 9 Retries" | status=failed, error="{...}" |
| JSON Parse Failure von Sub-Agent | "HARD STOP: JSON Parse Failure von {agent_name}" | status=failed, error="{...}" |
| Git Push/PR Failure | "HARD STOP: Git Operation fehlgeschlagen: {error}" | status=failed, error="{...}" |

### 9. JSON-Parsing-Pattern

```
# Pattern: "Find LAST ```json``` block" aus Sub-Agent-Output
#
# 1. Suche im Task()-Output nach dem LETZTEN ```json ... ``` Block
# 2. Parse diesen Block als JSON
# 3. Bei Parse-Failure: HARD STOP
#
# Dieses Pattern ist identisch mit dem bestehenden /orchestrate Command
```

### 10. Git-Operationen

```
# Branch erstellen (Phase 3):
Bash("git checkout -b feat/{feature-name}")
# feature-name = letztes Pfad-Segment des spec_path (z.B. "build-command")

# Push (Phase 8):
Bash("git push -u origin feat/{feature-name}")

# PR erstellen (Phase 8):
Bash("gh pr create --title 'feat: {feature-name}' --body '{pr_body}'")
# pr_body enthaelt: Feature-Name, Anzahl Slices, Zusammenfassung der Aenderungen
```

### 11. Wiederverwendete Code-Bausteine

| Pattern | Quelle | Wiederverwendung |
|---------|--------|-----------------|
| Input-Validierung (discovery.md + architecture.md) | `.claude/commands/planner.md` Phase 1 | Identische Pruefung |
| State-on-Disk Pattern | `.claude/commands/planner.md` Phase 2 | Aehnlich, aber `.build-state.json` statt `.planner-state.json` |
| Resume-Logik | `.claude/commands/planner.md` Phase 2 | Identisches Pattern |
| JSON-Parsing Pattern | `.claude/commands/orchestrate.md` | "Find LAST ```json``` block" |
| Slice-Liste extrahieren | `.claude/commands/planner.md` Phase 2 | Aus discovery.md "## Implementation Slices" |
| Wave-Parsing | `.claude/commands/orchestrate.md` Phase 1 | Aus orchestrator-config.md |
| Git Branch + PR | Neues Pattern | Neu fuer `/build` |
| HARD STOP Pattern | `.claude/commands/planner.md` + `.claude/commands/orchestrate.md` | Max 9 Retries, State schreiben, STOP |

---

## Acceptance Criteria

1) GIVEN ein spec_path mit discovery.md und architecture.md
   WHEN der /build Command mit dem spec_path aufgerufen wird
   THEN validiert der Command dass discovery.md und architecture.md existieren und erstellt eine `.build-state.json` mit status "in_progress"

2) GIVEN ein spec_path ohne discovery.md
   WHEN der /build Command aufgerufen wird
   THEN gibt der Command "STOP: discovery.md fehlt" aus und stoppt sofort ohne State-Datei zu erstellen

3) GIVEN ein frischer Start ohne .build-state.json
   WHEN der /build Command den Feature-Branch erstellt
   THEN wird ein Git-Branch `feat/{feature-name}` erstellt wobei feature-name das letzte Pfad-Segment des spec_path ist (z.B. "build-command" fuer "specs/2026-02-28-build-command")

4) GIVEN die Planning-Phase ist aktiv und es gibt 5 Slices in der discovery.md
   WHEN der Command den ersten Slice plant
   THEN ruft er Task(slice-plan-coordinator) auf mit spec_path, slice_number=1, slice_name, slice_description und approved_slices_paths=[] und schreibt nach dem JSON-Ergebnis die .build-state.json mit phase="planning" und current_slice_index=0

5) GIVEN Slice 1 ist approved (plan_status="approved")
   WHEN der Command den zweiten Slice plant
   THEN enthaelt der Task()-Call an slice-plan-coordinator die approved_slices_paths mit dem Pfad zu Slice 1

6) GIVEN alle Slices sind in der Planning-Phase approved
   WHEN der Command Gate 3 ausfuehrt
   THEN ruft er Task(integration-map) auf und liest das VERDICT aus den Output-Dateien

7) GIVEN das Gate-3-VERDICT ist "READY FOR ORCHESTRATION"
   WHEN der Command die Implementation-Phase beginnt
   THEN parst er orchestrator-config.md in Waves und startet mit der ersten Wave

8) GIVEN das Gate-3-VERDICT ist "GAPS FOUND"
   WHEN der Command einen Retry ausfuehrt
   THEN ruft er erneut den Planning-Fix auf mit den identifizierten Gaps und fuehrt danach Gate 3 erneut aus (max 9 Retries)

9) GIVEN eine Wave mit 2 Slices (z.B. Slice 1 und Slice 2)
   WHEN der Command die Implementation-Phase ausfuehrt
   THEN ruft er Task(slice-impl-coordinator) sequenziell fuer jeden Slice in der Wave auf und updated .build-state.json nach jedem Call

10) GIVEN alle Slices sind implementiert (impl_status="completed")
    WHEN der Command Final Validation ausfuehrt
    THEN ruft er Task(test-validator, mode=final_validation) auf

11) GIVEN die Final Validation ist bestanden (overall_status="passed")
    WHEN der Command die Completion-Phase ausfuehrt
    THEN fuehrt er `git push -u origin feat/{feature-name}` und `gh pr create` aus und setzt state.status auf "completed"

12) GIVEN ein Slice-Plan-Coordinator gibt JSON mit status="failed" zurueck
    WHEN der Command die Antwort parst
    THEN setzt er den State auf status="failed", schreibt die .build-state.json und stoppt mit "HARD STOP: Slice {N} Planning fehlgeschlagen"

13) GIVEN eine bestehende .build-state.json mit status="in_progress" und phase="implementing" und current_slice_index=2
    WHEN der /build Command erneut aufgerufen wird (Resume)
    THEN ueberspringt er die Planning-Phase und Gate 3 und setzt die Implementation bei Slice-Index 2 fort

14) GIVEN eine bestehende .build-state.json mit status="failed"
    WHEN der /build Command erneut aufgerufen wird
    THEN gibt er den letzten Fehler aus, setzt status zurueck auf "in_progress" und setzt beim fehlgeschlagenen Schritt fort

15) GIVEN die .build-state.json wird nach einem Task()-Call geschrieben
    WHEN ein beliebiger Task()-Call abgeschlossen ist
    THEN enthaelt die .build-state.json die aktuellen Werte fuer last_updated und last_action

---

## Testfaelle

### Test-Datei

**Konvention:** Manuelle Tests - Command-Datei erzeugt keinen ausfuehrbaren Code.

### Manuelle Tests

1. **Happy Path End-to-End:** /build mit einer einfachen Spec (z.B. 2-3 Slices) ausfuehren.
   - Erwartung: Planning-Phase durchlaeuft alle Slices, Gate 3 wird bestanden, Implementation-Phase durchlaeuft alle Waves, Final Validation bestanden, PR wird erstellt. .build-state.json hat status="completed".

2. **Input Validation - Missing discovery.md:** /build mit einem Pfad ohne discovery.md aufrufen.
   - Erwartung: Sofortiger STOP mit Fehlermeldung. Keine .build-state.json erstellt.

3. **Input Validation - Missing architecture.md:** /build mit einem Pfad ohne architecture.md aufrufen.
   - Erwartung: Sofortiger STOP mit Fehlermeldung. Keine .build-state.json erstellt.

4. **Resume nach Planning-Phase:** /build starten, nach 2 von 5 Slices abbrechen. Erneut /build aufrufen.
   - Erwartung: Command liest .build-state.json, erkennt phase="planning" und current_slice_index=2, setzt bei Slice 3 fort.

5. **Resume nach Failed State:** /build ausfuehren das bei Gate 3 fehlschlaegt. Erneut /build aufrufen.
   - Erwartung: Command zeigt letzten Fehler an, setzt status zurueck auf "in_progress", setzt bei Gate 3 fort.

6. **HARD STOP bei Slice Planning Failure:** /build mit einer Spec die einen unplanbaren Slice hat (Edge Case).
   - Erwartung: Nach max Retries des slice-plan-coordinator stoppt der Command mit status="failed" und error Message.

7. **State nach jedem Step:** /build ausfuehren und .build-state.json nach jedem Task()-Call pruefen.
   - Erwartung: last_updated und last_action sind nach jedem Step aktualisiert.

8. **Git Branch + PR:** /build erfolgreich durchlaufen lassen.
   - Erwartung: Git-Branch feat/{feature-name} existiert, PR wurde erstellt.

9. **Already Completed:** /build mit einer Spec aufrufen die bereits status="completed" hat.
   - Erwartung: Command gibt "Build bereits abgeschlossen" aus und stoppt.

---

## Definition of Done

- [x] Akzeptanzkriterien sind eindeutig & vollstaendig
- [x] Command-Datei folgt bestehendem Command-Format (YAML Frontmatter)
- [x] Alle Task()-Call-Prompts sind definiert
- [x] State-on-Disk Schema vollstaendig definiert (konsistent mit architecture.md)
- [x] Resume-Logik abgedeckt (3 Faelle: in_progress, failed, completed)
- [x] HARD STOP Bedingungen vollstaendig definiert (8 Faelle)
- [x] JSON-Parsing Pattern dokumentiert
- [x] Git-Operationen definiert (Branch, Push, PR)

---

## Integration Contract (GATE 2 PFLICHT)

### Requires From Other Slices

| Slice | Resource | Type | Validation |
|-------|----------|------|------------|
| slice-01-slice-plan-coordinator | `slice-plan-coordinator` Agent | Agent (Ebene 1) | Task()-Aufruf returniert JSON `{status, retries, slice_file, blocking_issues}` |
| slice-02-slice-impl-coordinator | `slice-impl-coordinator` Agent | Agent (Ebene 1) | Task()-Aufruf returniert JSON `{status, retries, evidence, error}` |

**Externe Abhaengigkeiten (bestehende, unveraenderte Agents):**

| Agent | Resource | Type | Validation |
|-------|----------|------|------------|
| `integration-map` | Task()-Aufruf | Agent (Ebene 1) | Schreibt integration-map.md, e2e-checklist.md, orchestrator-config.md. VERDICT-Zeile im Output |
| `test-validator` | Task()-Aufruf (mode=final_validation) | Agent (Ebene 2) | Returniert JSON `{overall_status, stages, error_output}` |
| `debugger` | Task()-Aufruf | Agent (Ebene 2) | Returniert JSON `{status, root_cause, files_changed}` |

### Provides To Other Slices

| Resource | Type | Consumer | Interface |
|----------|------|----------|-----------|
| `/build` Command | Command (Ebene 0) | Slice 4 (Multi-Spec Support) | `$ARGUMENTS` -> spec_path, State-on-Disk `.build-state.json` |
| `.build-state.json` | State File | Slice 4 (Multi-Spec Support) | JSON Schema wie in architecture.md Section "State-on-Disk" definiert |

### Integration Validation Tasks

- [ ] `slice-plan-coordinator` Agent existiert und returniert JSON im definierten Format
- [ ] `slice-impl-coordinator` Agent existiert und returniert JSON im definierten Format
- [ ] `integration-map` Agent existiert und ist unveraendert aufrufbar (VERDICT-basierter Output)
- [ ] `test-validator` Agent existiert und unterstuetzt mode=final_validation
- [ ] `debugger` Agent existiert und ist unveraendert aufrufbar
- [ ] JSON Output aller Sub-Agents kann mit "Find LAST ```json``` block" Pattern geparst werden
- [ ] `.build-state.json` Schema ist konsistent mit architecture.md "State-on-Disk" Section
- [ ] Git-Operationen (`git checkout -b`, `git push -u`, `gh pr create`) funktionieren im Projekt-Setup

---

## Code Examples (MANDATORY - GATE 2 PFLICHT)

> **KRITISCH:** Alle Code-Beispiele in diesem Dokument sind **PFLICHT-Deliverables**.
> Der Gate 2 Compliance Agent prueft, dass jedes Code-Beispiel implementiert wird.

| Code Example | Section | Mandatory | Notes |
|--------------|---------|-----------|-------|
| Command YAML Frontmatter | Command-Datei Header | YES | Description |
| Kritische Regeln Block | Command-Datei Intro | YES | 5 fundamentale Regeln |
| Phase 1: Input-Validierung | Command-Datei | YES | discovery.md + architecture.md Pruefung |
| Phase 2: State & Resume Logik | Command-Datei | YES | 3 Faelle: in_progress, failed, completed |
| Phase 3: Git Branch | Command-Datei | YES | feat/{feature-name} Branch |
| Phase 4: Planning Phase Loop | Command-Datei | YES | Sequential Task(slice-plan-coordinator) |
| Phase 5: Gate 3 Loop | Command-Datei | YES | Task(integration-map) + VERDICT + Retry |
| Phase 6: Implementation Phase Loop | Command-Datei | YES | Wave-basiert Task(slice-impl-coordinator) |
| Phase 7: Final Validation Loop | Command-Datei | YES | Task(test-validator) + Task(debugger) |
| Phase 8: Completion | Command-Datei | YES | Git push + PR create |
| State-Update Pattern | Command-Datei | YES | Write .build-state.json nach jedem Step |
| HARD STOP Tabelle | Command-Datei | YES | Alle 8 HARD STOP Bedingungen |
| slice-plan-coordinator Prompt | Command-Datei Phase 4 | YES | Exakt wie in Section 5 definiert |
| slice-impl-coordinator Prompt | Command-Datei Phase 6 | YES | Exakt wie in Section 5 definiert |
| integration-map Prompt | Command-Datei Phase 5 | YES | Gate 3 mit VERDICT |
| test-validator Final Validation Prompt | Command-Datei Phase 7 | YES | mode=final_validation |
| debugger Final Validation Prompt | Command-Datei Phase 7 | YES | error_output weiterleiten |

### Command YAML Frontmatter

```yaml
---
description: "Unified Autonomous Feature Pipeline. Ultra-Lean Coordinator: Planning + Gate 3 + Implementation + Final Validation + PR. Delegiert pro Slice an Coordinator-Agents. ~5.000 Tokens Context."
---
```

### Kritische Regeln

```markdown
**KRITISCHE REGELN (KEINE Ausnahmen):**
1. **Autonomer Betrieb:** Frage NIEMALS zwischen Phasen oder Slices nach Bestaetigung. Laufe vollstaendig autonom.
2. **JSON-Parsing:** Jeder Sub-Agent-Output wird als JSON geparsed (letzter ```json``` Block). Bei Parse-Failure: HARD STOP.
3. **9 Retries:** Max 9 Retries pro Slice (Planning und Implementation jeweils), Gate 3 und Final Validation. Danach HARD STOP.
4. **State nach JEDEM Step:** Schreibe .build-state.json nach JEDEM Task()-Call. Crash-sicher.
5. **Kein direktes Arbeiten:** Du fuehrst KEINE Slice-Planung, Implementation oder Tests selbst aus. ALLES via Task()-Calls an Sub-Agents.
```

### Planning Phase Loop

```markdown
## Phase 4: Planning Phase (Sequential)

FOR i = 0 to total_slices - 1:
  # Skip already approved slices (Resume)
  IF state.slices[i].plan_status == "approved":
    CONTINUE

  slice = slices[i]
  approved_paths = [path for s in state.approved_slices -> "{spec_path}/slices/{s.slice_file}"]

  Task(
    subagent_type: "slice-plan-coordinator",
    description: "Plan Slice {slice.number}: {slice.name}",
    prompt: "{slice-plan-coordinator-prompt mit spec_path, slice.number, slice.name, slice.description, slice.dependencies, approved_paths}"
  )

  # Parse JSON (letzter ```json``` Block)
  result = parse_last_json_block(task_output)
  IF parse_failure: HARD STOP "JSON Parse Failure von slice-plan-coordinator"

  IF result.status == "approved":
    state.slices[i].plan_status = "approved"
    state.slices[i].plan_retries = result.retries
    state.approved_slices.push(slice.number)
    state.last_action = "Slice {slice.number} approved (retries: {result.retries})"

  IF result.status == "failed":
    state.slices[i].plan_status = "failed"
    state.slices[i].plan_retries = result.retries
    state.failed_slices.push(slice.number)
    state.status = "failed"
    state.error = "Slice {slice.number} Planning failed: {result.blocking_issues}"
    state.last_action = "HARD STOP: Slice {slice.number} planning failed"
    Write(.build-state.json, state)
    HARD STOP

  state.current_slice_index = i + 1
  state.last_updated = now()
  Write(.build-state.json, state)
```

### Gate 3 Loop

```markdown
## Phase 5: Gate 3 (Integration Validation)

state.phase = "gate_3"
state.last_action = "Gate 3: Integration Validation gestartet"
Write(.build-state.json, state)

gate3_retries = state.gate3_retries

WHILE gate3_retries < 9:

  Task(
    subagent_type: "integration-map",
    description: "Gate 3: Integration Validation",
    prompt: "{integration-map-prompt}"
  )

  # Lese VERDICT aus integration-map.md oder orchestrator-config.md
  verdict_content = Read({spec_path}/integration-map.md)

  IF verdict_content CONTAINS "VERDICT: READY FOR ORCHESTRATION":
    state.last_action = "Gate 3 APPROVED"
    state.last_updated = now()
    Write(.build-state.json, state)
    BREAK -> Phase 6

  IF verdict_content CONTAINS "VERDICT: GAPS FOUND":
    gate3_retries++
    state.gate3_retries = gate3_retries
    state.last_action = "Gate 3 GAPS FOUND (retry {gate3_retries}/9)"
    state.last_updated = now()
    Write(.build-state.json, state)

    IF gate3_retries >= 9:
      state.status = "failed"
      state.error = "Gate 3 failed after 9 retries"
      state.last_action = "HARD STOP: Gate 3 failed"
      Write(.build-state.json, state)
      HARD STOP

    # Retry: Fix gaps via slice-plan-coordinator for affected slices
    # Parse AFFECTED_SLICES from verdict
    FOR EACH affected_slice IN affected_slices:
      Task(
        subagent_type: "slice-plan-coordinator",
        description: "Fix Slice {affected_slice} for Gate 3",
        prompt: "{fix-prompt mit gaps}"
      )

    CONTINUE (re-run integration-map)
```

### Implementation Phase Loop

```markdown
## Phase 6: Implementation Phase (Wave-based)

state.phase = "implementing"
Write(.build-state.json, state)

# Parse orchestrator-config.md -> Waves
waves = parse_waves(Read({spec_path}/orchestrator-config.md))

FOR EACH wave IN waves:
  FOR EACH slice IN wave.slices:
    slice_index = find_index(state.slices, slice.id)

    # Skip already completed slices (Resume)
    IF state.slices[slice_index].impl_status == "completed":
      CONTINUE

    Task(
      subagent_type: "slice-impl-coordinator",
      description: "Implement Slice {slice.id}",
      prompt: "{slice-impl-coordinator-prompt mit spec_path, slice.id, slice.file, architecture_path, integration_map_path}"
    )

    # Parse JSON (letzter ```json``` Block)
    result = parse_last_json_block(task_output)
    IF parse_failure: HARD STOP "JSON Parse Failure von slice-impl-coordinator"

    IF result.status == "completed":
      state.slices[slice_index].impl_status = "completed"
      state.slices[slice_index].impl_retries = result.retries
      state.completed_slices.push(slice.number)
      state.last_action = "Slice {slice.id} completed (retries: {result.retries})"

    IF result.status == "failed":
      state.slices[slice_index].impl_status = "failed"
      state.slices[slice_index].impl_retries = result.retries
      state.failed_slices.push(slice.number)
      state.status = "failed"
      state.error = "Slice {slice.id} Implementation failed: {result.error}"
      state.last_action = "HARD STOP: Slice {slice.id} implementation failed"
      Write(.build-state.json, state)
      HARD STOP

    state.current_slice_index = slice_index + 1
    state.last_updated = now()
    Write(.build-state.json, state)
```

### Final Validation + Completion

```markdown
## Phase 7: Final Validation

state.phase = "final_validation"
state.last_action = "Final Validation gestartet"
Write(.build-state.json, state)

final_retries = 0

WHILE final_retries < 9:

  Task(
    subagent_type: "test-validator",
    description: "Final Validation",
    prompt: "{test-validator-final-prompt mit mode=final_validation}"
  )

  result = parse_last_json_block(task_output)
  IF parse_failure: HARD STOP "JSON Parse Failure von test-validator"

  IF result.overall_status == "passed":
    state.last_action = "Final Validation PASSED"
    state.last_updated = now()
    Write(.build-state.json, state)
    BREAK -> Phase 8

  IF result.overall_status == "failed":
    final_retries++
    state.last_action = "Final Validation FAILED (retry {final_retries}/9)"
    Write(.build-state.json, state)

    IF final_retries >= 9:
      state.status = "failed"
      state.error = "Final Validation failed after 9 retries"
      Write(.build-state.json, state)
      HARD STOP

    # Debug
    Task(
      subagent_type: "debugger",
      description: "Debug Final Validation",
      prompt: "{debugger-prompt mit result.error_output}"
    )

    debug_result = parse_last_json_block(task_output)

    IF debug_result.status == "unable_to_fix":
      state.status = "failed"
      state.error = "Debugger unable to fix Final Validation failure"
      Write(.build-state.json, state)
      HARD STOP

    CONTINUE (re-validate)

## Phase 8: Completion

state.phase = "completing"
state.last_action = "Completion: Git push + PR"
Write(.build-state.json, state)

Bash("git push -u origin {state.branch_name}")
IF exit_code != 0:
  state.status = "failed"
  state.error = "Git push failed"
  Write(.build-state.json, state)
  HARD STOP

pr_result = Bash("gh pr create --title 'feat: {feature_name}' --body '## Feature: {feature_name}\n\nSlices: {state.total_slices}\nCompleted: {state.completed_slices.length}\n\nAutonomously built with /build command.'")
IF exit_code != 0:
  state.status = "failed"
  state.error = "PR creation failed"
  Write(.build-state.json, state)
  HARD STOP

state.status = "completed"
state.completed_at = now()
state.last_action = "Feature Complete! PR erstellt."
Write(.build-state.json, state)

OUTPUT: "Feature Complete! PR: {pr_url}"
```

---

## Constraints & Hinweise

**Betrifft:**
- Nur die Datei `.claude/commands/build.md`
- Keine Aenderungen an bestehenden Agents oder Commands

**Command-Format:**
- YAML Frontmatter mit `description`
- Markdown-Body mit Pseudocode-Logik (kein ausfuehrbarer Code)
- Identisches Format wie bestehende Commands (z.B. `.claude/commands/planner.md`, `.claude/commands/orchestrate.md`)

**Abgrenzung:**
- Dieser Command verarbeitet EINE Spec (Single-Spec). Multi-Spec-Support kommt in Slice 4
- Der Command fuehrt KEINE Slice-Planung, Implementation oder Tests selbst aus - alles via Task()-Calls
- Bestehende Commands (`/planner`, `/orchestrate`) bleiben unveraendert und parallel nutzbar
- State-File ist `.build-state.json` (NICHT `.planner-state.json` oder `.orchestrator-state.json`)
- `/build` liest/schreibt NUR `.build-state.json`, keine Interaktion mit bestehenden State-Files

**Context-Budget:**
- Coordinator-Context MUSS unter ~5.000 Tokens bleiben
- Empfaengt nur JSON-Status (~300 Tokens pro Task()-Call)
- Keine Slice-Inhalte, keine Compliance-Reports, keine Code-Snippets im Coordinator-Context
- Nur Pfad-Referenzen und Status-JSONs

---

## Deliverables (SCOPE SAFEGUARD)

**WICHTIG: Diese Liste wird automatisch vom Stop-Hook validiert. Der Agent kann nicht stoppen, wenn Dateien fehlen.**

<!-- DELIVERABLES_START -->
### Command-Datei
- [ ] `.claude/commands/build.md` -- Neuer /build Command: Ultra-Lean Coordinator fuer autonomen Feature-Build von Spec bis PR mit State-on-Disk, Resume-Support, Hierarchical Delegation an slice-plan-coordinator und slice-impl-coordinator, Gate 3 Integration Validation, Final Validation und Git Branch + PR

### Tests
- [ ] Manuelle Validierung: /build mit einer bekannten Spec ausfuehren und pruefen ob Planning + Gate 3 + Implementation + Final Validation + PR durchlaeuft und .build-state.json korrekt aktualisiert wird
<!-- DELIVERABLES_END -->

**Hinweis fuer den Implementierungs-Agent:**
- Alle Dateien zwischen `<!-- DELIVERABLES_START -->` und `<!-- DELIVERABLES_END -->` sind **Pflicht**
- Der Stop-Hook prueft automatisch ob alle Dateien existieren
- Bei fehlenden Dateien wird der Agent blockiert und muss nachfragen

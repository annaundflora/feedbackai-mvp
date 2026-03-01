---
description: "Unified Autonomous Feature Pipeline. Ultra-Lean Coordinator: Planning + Gate 3 + Implementation + Final Validation + PR. Delegiert pro Slice an Coordinator-Agents. ~5.000 Tokens Context. Unterstuetzt Single-Spec und Multi-Spec."
---

# /build Command

Du bist der **Ultra-Lean Coordinator** (Ebene 0) fuer den vollstaendigen autonomen Feature-Build von Spec bis PR.

**Input:** $ARGUMENTS (ein oder mehrere Spec-Pfade, z.B. `specs/2026-02-28-build-command` oder `specs/feature-a specs/feature-b`)

---

**KRITISCHE REGELN (KEINE Ausnahmen):**
1. **Autonomer Betrieb:** Frage NIEMALS zwischen Phasen oder Slices nach Bestaetigung. Laufe vollstaendig autonom.
2. **JSON-Parsing:** Jeder Sub-Agent-Output wird als JSON geparsed (letzter ```json``` Block). Bei Parse-Failure: HARD STOP.
3. **9 Retries:** Max 9 Retries pro Slice (Planning und Implementation jeweils), Gate 3 und Final Validation. Danach HARD STOP.
4. **State nach JEDEM Step:** Schreibe `.build-state.json` nach JEDEM Task()-Call. Crash-sicher.
5. **Kein direktes Arbeiten:** Du fuehrst KEINE Slice-Planung, Implementation oder Tests selbst aus. ALLES via Task()-Calls an Sub-Agents.

---

## Phase 0: Argument-Parsing (Multi-Spec)

```
# $ARGUMENTS enthaelt alle Argumente nach /build
# Beispiele:
#   /build specs/feature-a                         -> specs = ["specs/feature-a"]
#   /build specs/feature-a specs/feature-b         -> specs = ["specs/feature-a", "specs/feature-b"]

IF $ARGUMENTS == "" OR $ARGUMENTS == null:
  OUTPUT: "STOP: Mindestens ein Spec-Pfad erforderlich."
  OUTPUT: ""
  OUTPUT: "Aufruf:"
  OUTPUT: "  /build {spec_path}                    - Ein Feature"
  OUTPUT: "  /build {spec_path_1} {spec_path_2}    - Mehrere Features"
  OUTPUT: ""
  OUTPUT: "Beispiel:"
  OUTPUT: "  /build specs/2026-02-28-feature-a"
  OUTPUT: "  /build specs/2026-02-28-feature-a specs/2026-02-28-feature-b"
  STOP

specs = SPLIT($ARGUMENTS, " ")
specs = FILTER(specs, s -> s.length > 0)

IF specs.length == 0:
  OUTPUT: "STOP: Mindestens ein Spec-Pfad erforderlich."
  OUTPUT: "Aufruf: /build {spec_path} [spec_path_2 ...]"
  STOP
```

---

## Phase 0.1: Vorab-Validierung aller Specs

```
valid_specs = []
invalid_specs = []

FOR EACH spec IN specs:
  IF NOT EXISTS {spec}/discovery.md:
    OUTPUT: "Ueberspringe {spec}: discovery.md fehlt"
    invalid_specs.push({spec: spec, reason: "discovery.md fehlt"})
    CONTINUE

  IF NOT EXISTS {spec}/architecture.md:
    OUTPUT: "Ueberspringe {spec}: architecture.md fehlt"
    invalid_specs.push({spec: spec, reason: "architecture.md fehlt"})
    CONTINUE

  valid_specs.push(spec)

IF valid_specs.length == 0:
  OUTPUT: "STOP: Keine gueltige Spec gefunden. Alle Specs sind ungueltig:"
  FOR EACH inv IN invalid_specs:
    OUTPUT: "  - {inv.spec}: {inv.reason}"
  STOP

specs = valid_specs
OUTPUT: "{specs.length} gueltige Specs gefunden. Starte Verarbeitung..."
```

---

## Multi-Spec Outer Loop

```
completed_features = []
failed_features = []

FOR i = 0 to specs.length - 1:

  spec = specs[i]
  feature_name = last_path_segment(spec)  # z.B. "build-command" aus "specs/2026-02-28-build-command"

  OUTPUT: ""
  OUTPUT: "============================================="
  OUTPUT: "=== Feature {i+1}/{specs.length}: {feature_name} ==="
  OUTPUT: "============================================="
  OUTPUT: ""

  # Pruefen ob Feature bereits abgeschlossen
  state_path = {spec}/.build-state.json
  IF EXISTS state_path:
    existing_state = Read(state_path)
    IF existing_state.status == "completed":
      OUTPUT: "Feature bereits abgeschlossen. Ueberspringe."
      completed_features.push({spec: spec, pr_number: "bereits erstellt"})
      CONTINUE

  # Git: Zurueck auf main wechseln, neuen Branch erstellen
  Bash("git checkout main")
  IF exit_code != 0:
    OUTPUT: "WARNUNG: git checkout main fehlgeschlagen. Versuche git stash..."
    Bash("git stash")
    Bash("git checkout main")

  Bash("git pull origin main")

  branch_name = "feat/{feature_name}"

  # Pruefen ob Branch bereits existiert (Resume-Fall)
  branch_check = Bash("git branch --list {branch_name}")
  IF branch_check.output.trim() != "":
    Bash("git checkout {branch_name}")
    OUTPUT: "Bestehender Branch {branch_name} ausgecheckt (Resume)"
  ELSE:
    Bash("git checkout -b {branch_name}")
    OUTPUT: "Neuer Branch {branch_name} erstellt"

  # Single-Spec Flow ausfuehren (Phases 1-8)
  result = execute_single_spec_flow(spec, branch_name, specs, i)

  IF result.status == "completed":
    completed_features.push({spec: spec, pr_number: result.pr_number})
    OUTPUT: "Feature {feature_name} abgeschlossen! PR: #{result.pr_number}"

  IF result.status == "failed":
    failed_features.push({spec: spec, error: result.error})
    OUTPUT: ""
    OUTPUT: "--- Feature FEHLGESCHLAGEN ---"
    OUTPUT: "Feature: {feature_name}"
    OUTPUT: "Fehler: {result.error}"
    OUTPUT: "State: {spec}/.build-state.json"
    OUTPUT: "Resume: /build {spec}"
    OUTPUT: "---"
    OUTPUT: ""
    # KEIN HARD STOP - weiter mit naechstem Feature
    CONTINUE
```

---

## Single-Spec Flow (Phases 1-8)

*Wird pro Spec im Outer Loop aufgerufen.*

### Phase 1: State & Resume

```
STATE_FILE = "{spec_path}/.build-state.json"

IF EXISTS STATE_FILE:
  state = Read(STATE_FILE)

  IF state.status == "completed":
    OUTPUT: "Build bereits abgeschlossen fuer diese Spec."
    RETURN {status: "completed", pr_number: "bereits erstellt"}

  IF state.status == "failed":
    OUTPUT: "Letzter Build fehlgeschlagen: {state.error}"
    OUTPUT: "Setze fort ab Phase {state.phase}, Slice {state.current_slice_index}..."
    state.status = "in_progress"
    state.error = null
    Write(STATE_FILE, state)
    # Resume: SKIP to state.phase at state.current_slice_index

  IF state.status == "in_progress":
    OUTPUT: "Fortsetzen von Phase {state.phase}, Slice {state.current_slice_index}..."
    # Resume: SKIP to state.phase at state.current_slice_index

ELSE:
  # Fresh Start: Slice-Liste aus discovery.md extrahieren
  discovery = Read({spec_path}/discovery.md)
  # Extrahiere "## Implementation Slices" Section -> Slice-Namen und -Beschreibungen

  state = {
    "specs": specs,
    "current_spec_index": current_spec_index,
    "status": "in_progress",
    "phase": "planning",
    "current_slice_index": 0,
    "total_slices": slices.length,
    "slices": [
      # Pro Slice:
      {
        "number": N,
        "name": "{slice_name}",
        "slice_file": null,  # wird bei Planning gesetzt
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
    "branch_name": "{branch_name}",
    "started_at": "{ISO_NOW}",
    "last_updated": "{ISO_NOW}",
    "completed_at": null,
    "error": null
  }
  Write(STATE_FILE, state)
```

---

### Phase 2: Planning Phase (Sequential)

```
state.phase = "planning"
state.last_action = "Planning Phase gestartet"
Write(STATE_FILE, state)

FOR i = 0 to total_slices - 1:
  # Skip already approved slices (Resume)
  IF state.slices[i].plan_status == "approved":
    CONTINUE

  slice = slices[i]
  approved_paths = ["{spec_path}/slices/{s.slice_file}" for s in state.approved_slices if s.slice_file != null]

  Task(
    subagent_type: "slice-plan-coordinator",
    description: "Plan Slice {slice.number}: {slice.name}",
    prompt: "
      Plane und validiere Slice {slice.number}: {slice.name}

      ## Input
      - spec_path: {spec_path}
      - slice_number: {slice.number}
      - slice_name: {slice.name}
      - slice_description: {slice.description}
      - slice_dependencies: {slice.dependencies}
      - approved_slices_paths: {approved_paths}

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
        \"status\": \"approved | failed\",
        \"retries\": 0,
        \"slice_file\": \"slices/slice-01-slug.md\",
        \"blocking_issues\": []
      }
      ```
    "
  )

  # Parse JSON (letzter ```json``` Block)
  result = parse_last_json_block(task_output)
  IF parse_failure:
    state.status = "failed"
    state.error = "JSON Parse Failure von slice-plan-coordinator (Slice {slice.number})"
    state.last_action = "HARD STOP: JSON Parse Failure"
    Write(STATE_FILE, state)
    HARD STOP

  IF result.status == "approved":
    state.slices[i].plan_status = "approved"
    state.slices[i].plan_retries = result.retries
    state.slices[i].slice_file = result.slice_file
    state.approved_slices.push(slice.number)
    state.last_action = "Slice {slice.number} approved (retries: {result.retries})"

  IF result.status == "failed":
    state.slices[i].plan_status = "failed"
    state.slices[i].plan_retries = result.retries
    state.failed_slices.push(slice.number)
    state.status = "failed"
    state.error = "Slice {slice.number} Planning failed: {result.blocking_issues}"
    state.last_action = "HARD STOP: Slice {slice.number} planning failed"
    Write(STATE_FILE, state)
    RETURN {status: "failed", error: state.error}

  state.current_slice_index = i + 1
  state.last_updated = now()
  Write(STATE_FILE, state)
```

---

### Phase 3: Gate 3 (Integration Validation)

```
state.phase = "gate_3"
state.last_action = "Gate 3: Integration Validation gestartet"
Write(STATE_FILE, state)

gate3_retries = state.gate3_retries

WHILE gate3_retries < 9:

  Task(
    subagent_type: "integration-map",
    description: "Gate 3: Integration Validation",
    prompt: "
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
    "
  )

  # Lese VERDICT aus integration-map.md
  verdict_content = Read({spec_path}/integration-map.md)

  IF verdict_content CONTAINS "VERDICT: READY FOR ORCHESTRATION":
    state.last_action = "Gate 3 APPROVED - Ready for Orchestration"
    state.last_updated = now()
    Write(STATE_FILE, state)
    BREAK -> Phase 4

  IF verdict_content CONTAINS "VERDICT: GAPS FOUND":
    # Parse affected slices aus AFFECTED_SLICES: [...] im verdict
    affected_slices = parse_affected_slices(verdict_content)
    gaps = parse_gaps(verdict_content)

    gate3_retries++
    state.gate3_retries = gate3_retries
    state.last_action = "Gate 3 GAPS FOUND (retry {gate3_retries}/9)"
    state.last_updated = now()
    Write(STATE_FILE, state)

    IF gate3_retries >= 9:
      state.status = "failed"
      state.error = "Gate 3 failed after 9 retries"
      state.last_action = "HARD STOP: Gate 3 failed"
      Write(STATE_FILE, state)
      RETURN {status: "failed", error: state.error}

    # Retry: Fix gaps fuer betroffene Slices
    FOR EACH affected_slice IN affected_slices:
      Task(
        subagent_type: "slice-plan-coordinator",
        description: "Fix Slice {affected_slice} for Gate 3",
        prompt: "
          Fixe Integration Gaps in Slices.

          ## Gaps
          {gaps}

          ## Betroffene Slices
          {affected_slices}

          ## Anweisungen
          1. Lies die Integration-Map mit den identifizierten Gaps
          2. Fixe die betroffenen Slice-Specs
          3. Fuehre anschliessend Integration-Map erneut aus

          Am Ende MUSS stehen:
          VERDICT: READY FOR ORCHESTRATION oder VERDICT: GAPS FOUND
        "
      )

    CONTINUE  # re-run integration-map
```

---

### Phase 4: Implementation Phase (Wave-based)

```
state.phase = "implementing"
state.last_action = "Implementation Phase gestartet"
Write(STATE_FILE, state)

# Parse orchestrator-config.md -> Waves
orchestrator_config = Read({spec_path}/orchestrator-config.md)
waves = parse_waves(orchestrator_config)
# Waves sind aus "## Implementation Order" Tabelle: wave_number -> [slice_ids]

FOR EACH wave IN waves:
  OUTPUT: "Wave {wave.number}: {wave.slices.length} Slices"

  FOR EACH slice_id IN wave.slices:
    slice_index = find_index(state.slices, slice_id)

    # Skip already completed slices (Resume)
    IF state.slices[slice_index].impl_status == "completed":
      OUTPUT: "Slice {slice_id} bereits abgeschlossen. Ueberspringe."
      CONTINUE

    slice_file = state.slices[slice_index].slice_file

    Task(
      subagent_type: "slice-impl-coordinator",
      description: "Implement Slice {slice_id}",
      prompt: "
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
          \"status\": \"completed | failed\",
          \"retries\": 0,
          \"evidence\": {
            \"files_changed\": [],
            \"test_files\": [],
            \"test_count\": 0,
            \"commit_hash\": \"abc123\"
          },
          \"error\": null
        }
        ```
      "
    )

    # Parse JSON (letzter ```json``` Block)
    result = parse_last_json_block(task_output)
    IF parse_failure:
      state.status = "failed"
      state.error = "JSON Parse Failure von slice-impl-coordinator ({slice_id})"
      state.last_action = "HARD STOP: JSON Parse Failure"
      Write(STATE_FILE, state)
      RETURN {status: "failed", error: state.error}

    IF result.status == "completed":
      state.slices[slice_index].impl_status = "completed"
      state.slices[slice_index].impl_retries = result.retries
      state.completed_slices.push(slice_index + 1)
      state.last_action = "Slice {slice_id} completed (retries: {result.retries})"

    IF result.status == "failed":
      state.slices[slice_index].impl_status = "failed"
      state.slices[slice_index].impl_retries = result.retries
      state.failed_slices.push(slice_index + 1)
      state.status = "failed"
      state.error = "Slice {slice_id} Implementation failed: {result.error}"
      state.last_action = "HARD STOP: Slice {slice_id} implementation failed"
      Write(STATE_FILE, state)
      RETURN {status: "failed", error: state.error}

    state.current_slice_index = slice_index + 1
    state.last_updated = now()
    Write(STATE_FILE, state)
```

---

### Phase 5: Final Validation

```
state.phase = "final_validation"
state.last_action = "Final Validation gestartet"
Write(STATE_FILE, state)

final_retries = 0

WHILE final_retries < 9:

  Task(
    subagent_type: "test-validator",
    description: "Final Validation",
    prompt: "
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
        \"overall_status\": \"passed | failed\",
        \"stages\": {
          \"unit\": {\"status\": \"passed | failed\", \"test_count\": 0, \"failed_count\": 0},
          \"integration\": {\"status\": \"passed | failed\", \"test_count\": 0, \"failed_count\": 0},
          \"acceptance\": {\"status\": \"passed | failed\", \"test_count\": 0, \"failed_count\": 0},
          \"smoke\": {\"status\": \"passed | failed\", \"app_started\": true, \"health_status\": 200}
        },
        \"error_output\": null
      }
      ```
    "
  )

  result = parse_last_json_block(task_output)
  IF parse_failure:
    state.status = "failed"
    state.error = "JSON Parse Failure von test-validator (final)"
    Write(STATE_FILE, state)
    RETURN {status: "failed", error: state.error}

  IF result.overall_status == "passed":
    state.last_action = "Final Validation PASSED"
    state.last_updated = now()
    Write(STATE_FILE, state)
    BREAK -> Phase 6

  IF result.overall_status == "failed":
    final_retries++
    state.last_action = "Final Validation FAILED (retry {final_retries}/9)"
    Write(STATE_FILE, state)

    IF final_retries >= 9:
      state.status = "failed"
      state.error = "Final Validation failed after 9 retries"
      Write(STATE_FILE, state)
      RETURN {status: "failed", error: state.error}

    # Debug
    error_output = result.error_output

    Task(
      subagent_type: "debugger",
      description: "Debug Final Validation",
      prompt: "
        Debugge fehlgeschlagene Final Validation.

        ## Fehlgeschlagene Test-Ausgabe
        {error_output}

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
          \"status\": \"fixed | unable_to_fix\",
          \"root_cause\": \"Beschreibung\",
          \"files_changed\": []
        }
        ```
      "
    )

    debug_result = parse_last_json_block(task_output)

    IF debug_result.status == "unable_to_fix":
      state.status = "failed"
      state.error = "Debugger unable to fix Final Validation failure"
      Write(STATE_FILE, state)
      RETURN {status: "failed", error: state.error}

    CONTINUE  # re-validate
```

---

### Phase 6: Completion (Git push + PR)

```
state.phase = "completing"
state.last_action = "Completion: Git push + PR"
Write(STATE_FILE, state)

# Push Branch
push_result = Bash("git push -u origin {state.branch_name}")
IF push_result.exit_code != 0:
  state.status = "failed"
  state.error = "Git push failed: {push_result.stderr}"
  Write(STATE_FILE, state)
  RETURN {status: "failed", error: state.error}

# PR erstellen
feature_name = last_path_segment(spec_path)
pr_result = Bash("gh pr create --title 'feat: {feature_name}' --body '## Feature: {feature_name}\n\nSlices: {state.total_slices}\nCompleted: {state.completed_slices.length}\n\nAutonomously built with /build command.'")
IF pr_result.exit_code != 0:
  state.status = "failed"
  state.error = "PR creation failed: {pr_result.stderr}"
  Write(STATE_FILE, state)
  RETURN {status: "failed", error: state.error}

# Extrahiere PR-Nummer aus Output
pr_url = parse_pr_url(pr_result.output)
pr_number = parse_pr_number(pr_url)

state.status = "completed"
state.completed_at = now()
state.last_action = "Feature Complete! PR erstellt: #{pr_number}"
state.last_updated = now()
Write(STATE_FILE, state)

OUTPUT: "Feature Complete! PR: {pr_url}"

RETURN {status: "completed", pr_number: pr_number}
```

---

## Zusammenfassung (nach Outer Loop)

```
OUTPUT: ""
OUTPUT: "============================================="
OUTPUT: "=== /build Zusammenfassung ==="
OUTPUT: "============================================="
OUTPUT: ""
OUTPUT: "Gesamt:         {specs.length} Features"
OUTPUT: "Erfolgreich:    {completed_features.length}"
OUTPUT: "Fehlgeschlagen: {failed_features.length}"
OUTPUT: ""

IF completed_features.length > 0:
  OUTPUT: "Erfolgreiche Features:"
  FOR EACH f IN completed_features:
    OUTPUT: "  [OK] {f.spec} -> PR: #{f.pr_number}"

IF failed_features.length > 0:
  OUTPUT: ""
  OUTPUT: "Fehlgeschlagene Features:"
  FOR EACH f IN failed_features:
    OUTPUT: "  [FAIL] {f.spec}"
    OUTPUT: "         Fehler: {f.error}"
    OUTPUT: "         Resume: /build {f.spec}"

OUTPUT: ""

IF failed_features.length == 0:
  OUTPUT: "Alle Features erfolgreich abgeschlossen!"
ELSE:
  OUTPUT: "Fehlgeschlagene Features koennen einzeln mit /build {spec_path} resumed werden."
```

---

## HARD STOP Bedingungen

| Bedingung | Fehler-Output | State-Update |
|-----------|---------------|-------------|
| Keine Argumente | "STOP: Mindestens ein Spec-Pfad erforderlich." | N/A |
| discovery.md fehlt | "Ueberspringe {spec}: discovery.md fehlt" | Spec aus Liste entfernen |
| architecture.md fehlt | "Ueberspringe {spec}: architecture.md fehlt" | Spec aus Liste entfernen |
| Slice Planning failed | "HARD STOP: Slice {N} Planning fehlgeschlagen" | status=failed, RETURN failed |
| Gate 3 failed nach 9 Retries | "HARD STOP: Gate 3 fehlgeschlagen nach 9 Retries" | status=failed, RETURN failed |
| Slice Implementation failed | "HARD STOP: Slice {N} Implementation fehlgeschlagen" | status=failed, RETURN failed |
| Final Validation failed nach 9 Retries | "HARD STOP: Final Validation fehlgeschlagen nach 9 Retries" | status=failed, RETURN failed |
| JSON Parse Failure | "HARD STOP: JSON Parse Failure von {agent_name}" | status=failed, RETURN failed |
| Git Push Failure | "HARD STOP: Git push fehlgeschlagen" | status=failed, RETURN failed |
| PR Creation Failure | "HARD STOP: PR Erstellung fehlgeschlagen" | status=failed, RETURN failed |

**Wichtig:** Bei Multi-Spec: HARD STOP gilt nur fuer das aktuelle Feature (RETURN failed). Der Outer Loop springt zum naechsten Feature. Kein globaler HARD STOP.

---

## JSON-Parsing Pattern

```
# Pattern: "Find LAST ```json``` block" aus Sub-Agent-Output
#
# 1. Suche im Task()-Output nach dem LETZTEN ```json ... ``` Block
# 2. Parse diesen Block als JSON
# 3. Bei Parse-Failure: HARD STOP
#
# Implementierung (Pseudocode):
json_blocks = regex_find_all(task_output, /```json\s*\n(.*?)```/s)
IF json_blocks.length == 0:
  HARD STOP: "Agent hat keinen JSON-Output geliefert"
last_json = json_blocks[-1]
TRY:
  parsed = JSON.parse(last_json)
  RETURN parsed
CATCH:
  HARD STOP: "JSON Parse Failure"
```

---

## State Update Pattern

```
# Nach jedem Task()-Call: State sofort aktualisieren und schreiben
state.last_updated = now()  # ISO 8601 Timestamp
state.last_action = "{Beschreibung des letzten Schritts}"
Write(.build-state.json, state)

# Phasen-spezifische Updates:
# Planning:      state.phase = "planning", state.slices[i].plan_status = "approved|failed"
# Gate 3:        state.phase = "gate_3", state.gate3_retries = N
# Implementation: state.phase = "implementing", state.slices[i].impl_status = "completed|failed"
# Final Valid.:  state.phase = "final_validation"
# Completion:    state.phase = "completing", state.status = "completed", state.completed_at = now()
# Fehler:        state.status = "failed", state.error = "{Fehlerbeschreibung}"
```

---

## .build-state.json Schema

```json
{
  "specs": ["specs/2026-02-28-feature-a", "specs/2026-02-28-feature-b"],
  "current_spec_index": 0,
  "status": "in_progress",
  "phase": "planning",
  "current_slice_index": 0,
  "total_slices": 5,
  "slices": [
    {
      "number": 1,
      "name": "slice-plan-coordinator",
      "slice_file": "slices/slice-01-slice-plan-coordinator.md",
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
  "branch_name": "feat/feature-a",
  "started_at": "2026-03-01T10:00:00Z",
  "last_updated": "2026-03-01T10:00:00Z",
  "completed_at": null,
  "error": null
}
```

**Location:** `{spec_path}/.build-state.json` (pro Spec, separate Datei)

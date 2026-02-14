---
description: "Feature-Orchestrator mit External Validation. Implementiert Features wave-by-wave mit Task Tool, externer Test-Validierung und State-Tracking. Basiert auf Anthropic 'Building Effective Agents' Patterns."
---

# Orchestrate Feature Implementation

Du orchestrierst die **Implementierung** eines Features slice-by-slice mit **External Validation**.

**KRITISCHE REGELN (KEINE Ausnahmen):**
1. **Autonomer Betrieb:** Frage NIEMALS zwischen Waves oder Slices nach Bestätigung. Führe ALLE Waves/Slices aus bis fertig oder HARD STOP.
2. **Exit Code ist Wahrheit:** `exit_code != 0` = FEHLGESCHLAGEN. Immer. Auch wenn "einige Tests bestehen". 67% ist NICHT ausreichend. 99% ist NICHT ausreichend. NUR `exit_code == 0` bedeutet BESTANDEN.
3. **Retry-Loop ist Pflicht:** Bei `exit_code != 0` MUSS der Retry-Loop durchlaufen werden (auto_install → debugger → re-run). Du darfst diesen Loop NIEMALS überspringen oder einen Slice trotz Failure als "completed" markieren.

**Input:** $ARGUMENTS (Spec-Pfad, z.B. `specs/2026-01-28-pin-erstellung`)

---

## Phase 1: Input-Validierung & Config-Parsing

```
1. Prüfe ob $ARGUMENTS einen Spec-Pfad enthält
2. Falls kein Argument: Suche neuestes specs/*/orchestrator-config.md und frage via AskUserQuestion

3. Validiere dass ALLE Required Outputs existieren (BLOCKING):

REQUIRED (Planner muss vorher gelaufen sein):
├── {spec_path}/orchestrator-config.md    → Wave-Definitions, Slice-Metadaten
└── {spec_path}/slices/
    ├── slice-*.md                        → Slice-Specs
    └── compliance-slice-*.md             → Gate 2 Approvals

OPTIONAL (für QA, nicht für Orchestrierung):
├── {spec_path}/integration-map.md        → Für Phase 4 Consumer-File-Check
└── {spec_path}/e2e-checklist.md          → Für /qa-manual nach Implementierung

IF ANY REQUIRED MISSING:
  OUTPUT: "❌ STOP: Planner-Outputs fehlen. Zuerst /planner {spec_path} ausführen."
  HARD STOP

4. Parse orchestrator-config.md:
   - waves[] mit slice-ids, parallel-flag, validation-commands
   - slice_definitions mit ID, spec_file, test_command, e2e_command, dependencies
   - success_criteria

spec_path = [ermittelter Spec-Ordner]
feature_name = [aus orchestrator-config.md]
```

---

## Phase 2: Setup & State Management

```
STATE_FILE = "{spec_path}/.orchestrator-state.json"
EVIDENCE_DIR = ".claude/evidence/{feature_name}/"

# ─────────────────────────────────────────────────────────
# Step 1: Check for existing state (Resume Support)
# ─────────────────────────────────────────────────────────

IF EXISTS STATE_FILE:
  state = Read(STATE_FILE)

  IF state.status == "completed":
    OUTPUT: "✅ Implementierung bereits abgeschlossen. Für Neustart: Lösche {STATE_FILE}"
    STOP

  IF state.status == "in_progress":
    OUTPUT: "
    ═══════════════════════════════════════════════════════════
    🔄 RESUME: Fortsetzen bei Wave {state.current_wave}, Slice {state.current_slice}
    ═══════════════════════════════════════════════════════════
    Bereits implementiert: {state.completed_slices}
    Letzter Status: {state.last_action}
    "
    # Setze Variablen aus State
    current_wave_index = state.current_wave_index
    completed_slices = state.completed_slices
    SKIP to Phase 3 at current_wave_index

# ─────────────────────────────────────────────────────────
# Step 2: Fresh Start
# ─────────────────────────────────────────────────────────

1. Erstelle Evidence-Ordner:
   mkdir -p {EVIDENCE_DIR}

2. Erstelle oder wechsle zu Feature-Branch:
   git checkout -b feature/{feature_name} || git checkout feature/{feature_name}

# ─────────────────────────────────────────────────────────
# Step 3: Initialize State
# ─────────────────────────────────────────────────────────

state = {
  "spec_path": spec_path,
  "feature_name": feature_name,
  "status": "in_progress",
  "started_at": ISO_TIMESTAMP,
  "total_waves": len(waves),
  "total_slices": len(slices),
  "current_wave_index": 0,
  "current_slice_id": null,
  "waves": [
    { "number": 1, "name": "Foundation", "slices": ["slice-01-db-schema"], "status": "pending" },
    ...
  ],
  "completed_slices": [],
  "failed_slices": [],
  "evidence_files": [],
  "last_action": "Initialized",
  "last_updated": ISO_TIMESTAMP
}

Write(STATE_FILE, JSON.stringify(state, indent=2))
OUTPUT: "📊 State initialisiert: {STATE_FILE}"
```

---

## Helper: Auto-Install Missing Dependencies

```
FUNCTION auto_install_missing_deps(error_output):
  # Patterns für fehlende Module (Node, Webpack, Vite/Vitest, pnpm):
  #   - Cannot find module 'xxx'
  #   - Module not found.*'xxx'
  #   - Failed to resolve import "xxx"
  #   - Cannot find package 'xxx'
  #   - ERR_MODULE_NOT_FOUND.*'xxx'
  missing_modules = regex_extract_all(error_output, /Cannot find module '([^']+)'|Module not found.*'([^']+)'|Failed to resolve import ["']([^"']+)["']|Cannot find package '([^']+)'|ERR_MODULE_NOT_FOUND.*'([^']+)'/)

  IF missing_modules.length > 0:
    OUTPUT: "📦 Auto-Installing fehlende Dependencies: {missing_modules.join(', ')}"
    Bash("pnpm add -D {missing_modules.join(' ')}")
    RETURN true  # Retry empfohlen

  RETURN false  # Kein Dependency-Problem
```

---

## Phase 3: Wave-Based Implementation (KRITISCH!)

**WICHTIG: DU führst die Task Calls und Validierungen aus, NICHT ein anderer Agent!**

```
FOR each wave IN waves (in order):

  OUTPUT: "
  ╔═══════════════════════════════════════════════════════════╗
  ║  WAVE {wave.number}/{total_waves}: {wave.name}            ║
  ║  Slices: {wave.slices.join(', ')}                         ║
  ║  Parallel: {wave.parallel}                                ║
  ╚═══════════════════════════════════════════════════════════╝
  "

  # ─── State Update: Enter Wave ───
  state.current_wave_index = wave.index
  state.waves[wave.index].status = "in_progress"
  state.last_action = "Starting Wave {wave.number}"
  Write(STATE_FILE, JSON.stringify(state, indent=2))

  # ─────────────────────────────────────────────────────────
  # Implementiere alle Slices dieser Wave
  # ─────────────────────────────────────────────────────────

  FOR each slice_id IN wave.slices:
    slice_config = slice_definitions[slice_id]

    OUTPUT: "
    ───────────────────────────────────────────────────────────
    📦 SLICE: {slice_id}
    Spec: {slice_config.spec_file}
    Dependencies: {slice_config.dependencies}
    ───────────────────────────────────────────────────────────
    "

    # ─── State Update: Start Slice ───
    state.current_slice_id = slice_id
    state.last_action = "Implementing {slice_id}"
    Write(STATE_FILE, JSON.stringify(state, indent=2))

    # ─────────────────────────────────────────────────────────
    # Step 1: Sub-Agent für Implementation (FRESH CONTEXT!)
    # ─────────────────────────────────────────────────────────

    implementation_result = Task(
      subagent_type: "slice-implementer",
      description: "Implement {slice_id}",
      prompt: "
        Du bist ein fokussierter Slice-Implementer.

        ## DEIN EINZIGER AUFTRAG
        Implementiere exakt diesen Slice: {slice_id}

        ## INPUT-DATEIEN (MUSS gelesen werden)
        1. Slice-Spec: {slice_config.spec_file}
        2. Compliance-Report: {slice_config.compliance_file}
        3. Architecture: {spec_path}/architecture.md (für Kontext)
        4. Integration-Map: {spec_path}/integration-map.md (für Contracts)

        ## DELIVERABLES (aus Slice-Spec zwischen DELIVERABLES_START/END)
        Implementiere ALLE aufgeführten Deliverables.

        ## INTEGRATION CONTRACT (aus Integration-Map)
        - Requires From: {integration_map[slice_id].requires_from}
        - Provides To: {integration_map[slice_id].provides_to}

        Stelle sicher, dass alle 'Provides To' Interfaces korrekt implementiert sind!

        ## CODE EXAMPLES (aus Slice-Spec)
        Die Slice-Spec enthält Code Examples. Nutze diese als Vorlage.

        ## REGELN
        1. Lies die Slice-Spec vollständig
        2. Implementiere NUR was dort steht - KEIN Scope Creep
        3. Schreibe Tests wie in der Spec definiert
        4. Committe mit: git add -A && git commit -m 'feat({slice_id}): {kurze Beschreibung}'

        ## VERBOTEN
        - Zusätzliche Features (Scope Creep)
        - Tests selbst ausführen (macht der Orchestrator)
        - Andere Slices anfassen
        - Fake UUIDs in Tests - nutze echte DB Records

        ## ERWARTETER OUTPUT (als letztes)
        ```json
        {
          'status': 'completed',
          'files_changed': ['pfad/zu/datei1.ts', ...],
          'commit_hash': 'abc123',
          'notes': 'Optional: Hinweise'
        }
        ```
      "
    )

    # ─────────────────────────────────────────────────────────
    # Step 2: EXTERNAL VALIDATION (DU führst aus!)
    # ─────────────────────────────────────────────────────────
    #
    # ABSOLUTE REGEL: exit_code != 0 bedeutet FEHLGESCHLAGEN.
    # Es gibt KEINE Ausnahmen. "67% Tests bestehen" ist NICHT ausreichend.
    # Du darfst NIEMALS einen Slice als "completed" markieren wenn Tests fehlschlagen.
    # Bei exit_code != 0 MUSS der Retry-Loop durchlaufen werden.
    #

    OUTPUT: "🧪 External Validation: {slice_config.test_command}"

    # Unit Tests
    test_result = Bash(
      command: slice_config.test_command,
      description: "Run unit tests for {slice_id}"
    )

    # ─── Unit Test Retry Loop (max 2 Retries) ───
    MAX_RETRIES = 2
    retry_count = 0

    WHILE test_result.exit_code != 0 AND retry_count < MAX_RETRIES:
      retry_count += 1
      OUTPUT: "⚠️ Unit Tests fehlgeschlagen (Retry {retry_count}/{MAX_RETRIES})"

      # Step A: Check for missing dependencies first
      IF auto_install_missing_deps(test_result.output):
        OUTPUT: "📦 Dependencies installiert - Re-run Tests..."
        test_result = Bash(slice_config.test_command)
        CONTINUE  # Re-evaluate WHILE condition

      # Step B: Fix-Agent aufrufen
      OUTPUT: "🔧 Debugger-Agent analysiert Fehler..."
      fix_result = Task(
        subagent_type: "debugger",
        description: "Fix {slice_id} test failure",
        prompt: "
          Unit Tests für {slice_id} sind fehlgeschlagen.

          ## Fehler-Output
          Command: {slice_config.test_command}
          Exit Code: {test_result.exit_code}
          Output:
          {test_result.output}

          ## Kontext
          - Slice-Spec: {slice_config.spec_file}
          - Geänderte Dateien: {implementation_result.files_changed}

          ## Auftrag
          1. Analysiere den Fehler
          2. Finde die Root Cause
          3. Fixe den Code (NICHT die Tests aufweichen!)
          4. Committe mit: git commit -m 'fix({slice_id}): {kurze Beschreibung}'
        "
      )

      # Step C: Re-run Tests
      test_result = Bash(slice_config.test_command)

    # Nach max Retries immer noch fehlgeschlagen → HARD STOP
    IF test_result.exit_code != 0:
      state.failed_slices.append({
        "slice_id": slice_id,
        "phase": "unit_test",
        "exit_code": test_result.exit_code,
        "output": test_result.output,
        "retries_attempted": retry_count
      })
      state.last_action = "FAILED: {slice_id} unit tests (after {retry_count} retries)"
      Write(STATE_FILE, JSON.stringify(state, indent=2))

      evidence = {
        "feature": feature_name,
        "slice": slice_id,
        "timestamp": ISO_TIMESTAMP,
        "status": "failed",
        "phase": "unit_test",
        "retries_attempted": retry_count,
        "validation": {
          "command": slice_config.test_command,
          "exit_code": test_result.exit_code,
          "output": test_result.output
        }
      }
      Write("{EVIDENCE_DIR}/{slice_id}.json", JSON.stringify(evidence, indent=2))
      state.evidence_files.append("{EVIDENCE_DIR}/{slice_id}.json")

      OUTPUT: "
      ╔════════════════════════════════════════════════════════════╗
      ║  ❌ HARD STOP: {slice_id} Unit Tests fehlgeschlagen        ║
      ╠════════════════════════════════════════════════════════════╣
      ║                                                            ║
      ║  Command: {slice_config.test_command}                      ║
      ║  Exit Code: {test_result.exit_code}                        ║
      ║  Retries: {retry_count}/{MAX_RETRIES} erschöpft            ║
      ║                                                            ║
      ║  Output:                                                   ║
      ║  {test_result.output (truncated)}                          ║
      ║                                                            ║
      ║  Evidence: {EVIDENCE_DIR}/{slice_id}.json                  ║
      ║  State: {STATE_FILE}                                       ║
      ║                                                            ║
      ║  Nächste Schritte:                                         ║
      ║  1. Fehler manuell analysieren und fixen                   ║
      ║  2. /orchestrate {spec_path} erneut starten (Resume)       ║
      ║                                                            ║
      ╚════════════════════════════════════════════════════════════╝
      "
      HARD STOP

    OUTPUT: "✅ Unit Tests passed"

    # ─── E2E Test Retry Loop (falls erforderlich) ───
    IF slice_config.e2e_required AND slice_config.e2e_command:
      OUTPUT: "🎭 E2E Validation: {slice_config.e2e_command}"

      e2e_result = Bash(
        command: slice_config.e2e_command,
        description: "Run E2E tests for {slice_id}"
      )

      e2e_retry_count = 0
      WHILE e2e_result.exit_code != 0 AND e2e_retry_count < MAX_RETRIES:
        e2e_retry_count += 1
        OUTPUT: "⚠️ E2E Tests fehlgeschlagen (Retry {e2e_retry_count}/{MAX_RETRIES})"

        IF auto_install_missing_deps(e2e_result.output):
          OUTPUT: "📦 Dependencies installiert - Re-run E2E..."
          e2e_result = Bash(slice_config.e2e_command)
          CONTINUE

        OUTPUT: "🔧 Debugger-Agent analysiert E2E-Fehler..."
        fix_result = Task(
          subagent_type: "debugger",
          description: "Fix {slice_id} E2E test failure",
          prompt: "
            E2E Tests für {slice_id} sind fehlgeschlagen.

            ## Fehler-Output
            Command: {slice_config.e2e_command}
            Exit Code: {e2e_result.exit_code}
            Output:
            {e2e_result.output}

            ## Kontext
            - Slice-Spec: {slice_config.spec_file}
            - Geänderte Dateien: {implementation_result.files_changed}

            ## Auftrag
            1. Analysiere den E2E-Fehler
            2. Finde die Root Cause
            3. Fixe den Code (NICHT die Tests aufweichen!)
            4. Committe mit: git commit -m 'fix({slice_id}): {kurze Beschreibung}'
          "
        )

        e2e_result = Bash(slice_config.e2e_command)

      IF e2e_result.exit_code != 0:
        state.failed_slices.append({
          "slice_id": slice_id,
          "phase": "e2e_test",
          "exit_code": e2e_result.exit_code,
          "output": e2e_result.output,
          "retries_attempted": e2e_retry_count
        })
        state.last_action = "FAILED: {slice_id} E2E tests (after {e2e_retry_count} retries)"
        Write(STATE_FILE, JSON.stringify(state, indent=2))
        Write("{EVIDENCE_DIR}/{slice_id}.json", evidence_with_e2e_failure...)
        OUTPUT HARD STOP (same format as unit tests, with E2E details)...
        HARD STOP

      OUTPUT: "✅ E2E Tests passed"

    # ─────────────────────────────────────────────────────────
    # Step 3: Evidence & State Update
    # ─────────────────────────────────────────────────────────

    evidence = {
      "feature": feature_name,
      "slice": slice_id,
      "timestamp": ISO_TIMESTAMP,
      "status": "completed",
      "implementation": implementation_result,
      "validation": {
        "unit_test": { "command": slice_config.test_command, "exit_code": 0 },
        "e2e_test": { "command": slice_config.e2e_command, "exit_code": 0 } (if applicable)
      },
      "can_proceed": true
    }
    Write("{EVIDENCE_DIR}/{slice_id}.json", JSON.stringify(evidence, indent=2))

    # ─── State Update: Slice Completed ───
    state.completed_slices.append(slice_id)
    state.evidence_files.append("{EVIDENCE_DIR}/{slice_id}.json")
    state.last_action = "Completed {slice_id}"
    Write(STATE_FILE, JSON.stringify(state, indent=2))

    OUTPUT: "✅ Slice {slice_id} COMPLETED"

  # END FOR each slice

  # ─── State Update: Wave Completed ───
  state.waves[wave.index].status = "completed"
  state.last_action = "Wave {wave.number} completed"
  Write(STATE_FILE, JSON.stringify(state, indent=2))

  OUTPUT: "
  ───────────────────────────────────────────────────────────
  ✅ WAVE {wave.number} COMPLETED
  Slices: {wave.slices.join(', ')}
  ───────────────────────────────────────────────────────────
  "

# END FOR each wave
```

---

## Phase 4: Final Validation

```
OUTPUT: "
═══════════════════════════════════════════════════════════
🏁 PHASE 4: Final Validation
═══════════════════════════════════════════════════════════
"

# ─────────────────────────────────────────────────────────
# Step 1: Lint Check
# ─────────────────────────────────────────────────────────

OUTPUT: "🔍 Running lint check..."
lint_result = Bash("pnpm lint")

IF lint_result.exit_code != 0:
  OUTPUT: "⚠️ Lint warnings/errors found (non-blocking)"
  # Nicht HARD STOP - nur Warning

# ─────────────────────────────────────────────────────────
# Step 2: Type Check
# ─────────────────────────────────────────────────────────

OUTPUT: "🔍 Running type check..."
type_result = Bash("pnpm tsc --noEmit")

MAX_FINAL_RETRIES = 2
type_retry_count = 0

WHILE type_result.exit_code != 0 AND type_retry_count < MAX_FINAL_RETRIES:
  type_retry_count += 1
  OUTPUT: "⚠️ TypeScript Errors (Retry {type_retry_count}/{MAX_FINAL_RETRIES})"

  auto_install_missing_deps(type_result.output)

  OUTPUT: "🔧 Debugger-Agent fixt TypeScript-Fehler..."
  fix_result = Task(
    subagent_type: "debugger",
    description: "Fix TypeScript errors",
    prompt: "
      TypeScript-Check (pnpm tsc --noEmit) ist fehlgeschlagen.

      ## Fehler-Output
      {type_result.output}

      ## Kontext
      Feature: {feature_name}
      Implementierte Slices: {state.completed_slices}

      ## Auftrag
      1. Analysiere die TypeScript-Fehler
      2. Fixe alle Type Errors
      3. Committe mit: git commit -m 'fix: resolve TypeScript errors'
    "
  )

  type_result = Bash("pnpm tsc --noEmit")

IF type_result.exit_code != 0:
  state.status = "failed"
  state.last_action = "TypeScript errors (after {type_retry_count} retries)"
  Write(STATE_FILE, ...)

  OUTPUT: "
  ╔════════════════════════════════════════════════════════════╗
  ║  ❌ TypeScript Errors gefunden                             ║
  ╠════════════════════════════════════════════════════════════╣
  ║  Retries: {type_retry_count}/{MAX_FINAL_RETRIES} erschöpft ║
  ║  {type_result.output}                                      ║
  ╚════════════════════════════════════════════════════════════╝
  "
  HARD STOP

OUTPUT: "✅ Type check passed"

# ─────────────────────────────────────────────────────────
# Step 3: Build Check (mit Retry)
# ─────────────────────────────────────────────────────────

OUTPUT: "🔍 Running build check..."
build_result = Bash("pnpm build")

build_retry_count = 0
WHILE build_result.exit_code != 0 AND build_retry_count < MAX_FINAL_RETRIES:
  build_retry_count += 1
  OUTPUT: "⚠️ Build fehlgeschlagen (Retry {build_retry_count}/{MAX_FINAL_RETRIES})"

  auto_install_missing_deps(build_result.output)

  OUTPUT: "🔧 Debugger-Agent fixt Build-Fehler..."
  fix_result = Task(
    subagent_type: "debugger",
    description: "Fix build errors",
    prompt: "
      Build (pnpm build) ist fehlgeschlagen.

      ## Fehler-Output
      {build_result.output}

      ## Kontext
      Feature: {feature_name}
      Implementierte Slices: {state.completed_slices}

      ## Auftrag
      1. Analysiere die Build-Fehler
      2. Fixe die Ursache
      3. Committe mit: git commit -m 'fix: resolve build errors'
    "
  )

  build_result = Bash("pnpm build")

IF build_result.exit_code != 0:
  state.status = "failed"
  state.last_action = "Build failed (after {build_retry_count} retries)"
  Write(STATE_FILE, ...)
  HARD STOP

OUTPUT: "✅ Build successful"

# ─────────────────────────────────────────────────────────
# Step 4: Consumer-File-Check (Dead Component Prevention)
# ─────────────────────────────────────────────────────────

# Prüfe ob Consumer Files tatsächlich modifiziert wurden.
# Lese integration-map.md falls vorhanden, extrahiere "Consumer File Modifications".
# Falls integration-map.md nicht existiert: überspringe diesen Check.

IF EXISTS {spec_path}/integration-map.md:
  OUTPUT: "🔍 Consumer-File-Check..."
  consumer_files = parse_consumer_files_from(integration-map.md)
  # z.B. ["app/jobs/[id]/page.tsx", "components/header.tsx"]

  changed_files = Bash("git diff --name-only main...HEAD")

  FOR each consumer_file IN consumer_files:
    IF consumer_file NOT IN changed_files:
      OUTPUT: "⚠️ WARNUNG: {consumer_file} wurde nicht modifiziert — mögliche Dead Component!"

  # Non-blocking: nur Warnung, kein HARD STOP

# ─────────────────────────────────────────────────────────
# Step 5: All E2E Tests (Cross-Slice Flows)
# ─────────────────────────────────────────────────────────

OUTPUT: "🎭 Running all E2E tests..."
all_e2e_result = Bash("pnpm test tests/slices/{feature_name}/*.spec.ts")

IF all_e2e_result.exit_code != 0:
  OUTPUT: "⚠️ Some E2E tests failed"
  # Nicht HARD STOP - User entscheidet
```

---

## Phase 5: Completion

```
# ─── State Update: Completed ───
state.status = "completed"
state.completed_at = ISO_TIMESTAMP
state.last_action = "Feature implementation completed"
Write(STATE_FILE, JSON.stringify(state, indent=2))

# Feature Evidence erstellen
feature_evidence = {
  "feature": feature_name,
  "status": "completed",
  "started_at": state.started_at,
  "completed_at": state.completed_at,
  "slices_implemented": state.completed_slices,
  "evidence_files": state.evidence_files,
  "branch": "feature/{feature_name}",
  "validation": {
    "lint": "passed",
    "types": "passed",
    "build": "passed",
    "e2e": "passed"
  }
}
Write("{EVIDENCE_DIR}/feature-complete.json", JSON.stringify(feature_evidence, indent=2))

OUTPUT: "
╔════════════════════════════════════════════════════════════╗
║  ✅ FEATURE IMPLEMENTATION COMPLETE                        ║
╠════════════════════════════════════════════════════════════╣
║                                                            ║
║  Feature: {feature_name}                                   ║
║  Slices: {state.completed_slices.length}/{state.total_slices} ║
║  Branch: feature/{feature_name}                            ║
║                                                            ║
║  Evidence:                                                 ║
║  {EVIDENCE_DIR}/                                           ║
║                                                            ║
║  State: {STATE_FILE} (status: completed)                   ║
║                                                            ║
║  Nächste Schritte:                                         ║
║  1. git push -u origin feature/{feature_name}              ║
║  2. PR erstellen                                           ║
║  3. Manual Smoke Test                                      ║
║                                                            ║
╚════════════════════════════════════════════════════════════╝
"
```

---

## Output

Nach erfolgreichem Durchlauf:

```
{spec_path}/
├── .orchestrator-state.json              # State Tracking ✓
├── orchestrator-config.md                # Input (Required)
├── integration-map.md                    # Optional (Phase 4 Consumer-Check)
├── e2e-checklist.md                      # Optional (für /qa-manual)
└── slices/
    ├── slice-01-*.md
    └── ...

.claude/evidence/{feature_name}/
├── slice-01-db-schema.json               # Per-Slice Evidence ✓
├── slice-02-pinterest-api.json           # Per-Slice Evidence ✓
├── ...
└── feature-complete.json                 # Feature Evidence ✓
```

---

## State File Format

Die `.orchestrator-state.json` ermöglicht Resume und Audit:

```json
{
  "spec_path": "specs/2026-01-28-pin-erstellung",
  "feature_name": "pin-erstellung",
  "status": "in_progress",
  "started_at": "2026-02-01T10:00:00Z",
  "total_waves": 5,
  "total_slices": 6,
  "current_wave_index": 2,
  "current_slice_id": "slice-03-ai-content",
  "waves": [
    { "number": 1, "name": "Foundation", "slices": ["slice-01-db-schema"], "status": "completed" },
    { "number": 2, "name": "API Layer", "slices": ["slice-02-pinterest-api", "slice-03-ai-content"], "status": "in_progress" }
  ],
  "completed_slices": ["slice-01-db-schema", "slice-02-pinterest-api"],
  "failed_slices": [],
  "evidence_files": [
    ".claude/evidence/pin-erstellung/slice-01-db-schema.json",
    ".claude/evidence/pin-erstellung/slice-02-pinterest-api.json"
  ],
  "last_action": "Implementing slice-03-ai-content",
  "last_updated": "2026-02-01T11:30:00Z"
}
```

**Status Values:**
| Status | Bedeutung |
|--------|-----------|
| `in_progress` | Implementation läuft, Resume möglich |
| `completed` | Alle Slices + Final Validation passed |
| `failed` | HARD STOP bei Test-Failure |

---

## Wichtig: External Validation Pattern

**KRITISCH:** DU führst alle Tests aus, NICHT der Sub-Agent!

| Was | Wer macht es | Warum |
|-----|--------------|-------|
| Code schreiben | Sub-Agent (Task) | Fresh Context, fokussiert |
| Tests ausführen | DU (Bash) | Ground Truth, Exit Code ist Wahrheit |
| Evidence speichern | DU | Nachweisbarkeit |
| State aktualisieren | DU | Resume-Fähigkeit |

**Quelle:** Anthropic "Ground Truth from Environment" - Exit Code als einzige Wahrheit

---

## Referenzen

- Slice Implementer: `.claude/agents/slice-implementer.md`
- Orchestrator Config (REQUIRED): `{spec_path}/orchestrator-config.md`
- Integration Map (OPTIONAL, Phase 4): `{spec_path}/integration-map.md`
- E2E Checklist (für /qa-manual): `{spec_path}/e2e-checklist.md`
- Evidence Store: `.claude/evidence/{feature_name}/`

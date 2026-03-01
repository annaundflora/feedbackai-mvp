# Slice 2: Slice-Impl-Coordinator Agent erstellen

> **Slice 2 von 5** fuer `build-command`
>
> | Navigation | |
> |------------|---|
> | **Vorheriger:** | `slice-01-slice-plan-coordinator.md` |
> | **Naechster:** | `slice-03-build-command.md` |

---

## Metadata (fuer Orchestrator)

| Key | Value |
|-----|-------|
| **ID** | `slice-02-slice-impl-coordinator` |
| **Test** | `N/A (manueller Test - Agent-Datei)` |
| **E2E** | `false` |
| **Dependencies** | `[]` |

---

## Test-Strategy (fuer Orchestrator Pipeline)

> **Quelle:** Auto-detected basierend auf Repo-Indikatoren. Dashboard nutzt Next.js + Vitest + Playwright.
> Dieser Slice erstellt eine Agent-Markdown-Datei, keine ausfuehrbaren Code-Dateien.

| Key | Value |
|-----|-------|
| **Stack** | `claude-code-agent` (Markdown Agent Definition) |
| **Test Command** | `N/A` (Agent-Datei, kein ausfuehrbarer Code) |
| **Integration Command** | `N/A` |
| **Acceptance Command** | `Manuell: Agent mit einem Slice aufrufen, pruefen ob Code + Tests + Evidence erstellt werden` |
| **Start Command** | `N/A` |
| **Health Endpoint** | `N/A` |
| **Mocking Strategy** | `no_mocks` |

---

## Slice-Uebersicht

| # | Slice | Status | Datei |
|---|-------|--------|-------|
| 1 | slice-plan-coordinator Agent | Ready | `slice-01-slice-plan-coordinator.md` |
| 2 | **slice-impl-coordinator Agent** | Ready | `slice-02-slice-impl-coordinator.md` |
| 3 | /build Command | Pending | `slice-03-build-command.md` |
| 4 | Multi-Spec Support | Pending | `slice-04-multi-spec-support.md` |
| 5 | Pattern-Dokumentation | Pending | `slice-05-pattern-dokumentation.md` |

---

## Kontext & Ziel

Der `/build` Command braucht einen Ebene-1-Coordinator-Agent der pro Slice die Implementierung, Test-Erstellung, Test-Validierung und Debugging uebernimmt. Dieser Agent wird vom `/build` Command per `Task()` aufgerufen und bekommt einen frischen Context pro Slice (Fresh Context Pattern).

**Problem:** Der bisherige `/orchestrate` Command fuehrt alle 4 Sub-Agent-Steps (Implementer, Test-Writer, Test-Validator, Debugger) selbst aus. Bei 7+ Slices mit Retries fuellt sich der Coordinator-Context (21.000-63.000 Tokens).

**Loesung:** Der `slice-impl-coordinator` Agent uebernimmt die gesamte Sub-Agent-Pipeline fuer EINEN Slice. Der `/build` Command ruft ihn nur noch mit `Task()` auf und empfaengt ein kompaktes JSON-Ergebnis (~300 Tokens).

---

## Technische Umsetzung

### Architektur-Kontext (aus architecture.md)

> **Quelle:** `architecture.md` -> "Architecture Layers", "Slice-Impl-Coordinator Internal Flow"

```
/build Command (Ebene 0, ~5.000 Tokens Context)
  |
  +-- Task(slice-impl-coordinator)    [Ebene 1, eigener Context]
        |
        +-- Task(slice-implementer)   [Ebene 2, eigener Context]
        +-- Task(test-writer)         [Ebene 2, eigener Context]
        +-- Task(test-validator)      [Ebene 2, eigener Context]
        +-- Task(debugger)            [Ebene 2, eigener Context]  (conditional)
        +-- Return: {status: "completed", evidence: {...}}
```

### 1. Architektur-Impact

| Layer | Aenderungen |
|-------|------------|
| `.claude/agents/` | Neue Datei `slice-impl-coordinator.md` |

### 2. Datenfluss

```
Input: spec_path, slice_id, architecture_path, integration_map_path
  |
  v
Read: slice spec, architecture.md, integration-map.md
  |
  v
Step 1: Task(slice-implementer)
  |  -> JSON {status, files_changed, commit_hash}
  |  -> status: "failed" -> sofort return {status: "failed"}
  |
  v
Step 2: Task(test-writer)
  |  -> JSON {status, test_files, ac_coverage}
  |  -> ac_coverage != 100% -> return {status: "failed"}
  |
  v
LOOP (max 9 Retries):
  |
  +-- Step 3: Task(test-validator, mode=slice_validation)
  |     -> JSON {overall_status, stages}
  |     -> overall_status: "passed" -> break loop
  |
  +-- Step 4 (bei failure): Task(debugger)
  |     -> JSON {status, root_cause, files_changed}
  |     -> status: "unable_to_fix" -> return {status: "failed"}
  |     -> status: "fixed" -> retry_count++, re-validate
  |
  v
Write Evidence: .claude/evidence/{feature}/{slice_id}.json
  |
  v
Return JSON:
  {
    "status": "completed" | "failed",
    "retries": N,
    "evidence": {
      "files_changed": ["..."],
      "test_files": ["..."],
      "test_count": 12,
      "commit_hash": "abc123"
    },
    "error": null | "Fehlerbeschreibung"
  }
```

### 3. JSON Output Contract

Der Agent MUSS am Ende seiner Ausfuehrung exakt dieses JSON zurueckgeben:

**Erfolg:**

```json
{
  "status": "completed",
  "retries": 1,
  "evidence": {
    "files_changed": ["backend/app/api/endpoints.py", "backend/app/models.py"],
    "test_files": ["tests/slices/feature/slice-02-api.test.ts"],
    "test_count": 12,
    "commit_hash": "abc123def"
  },
  "error": null
}
```

**Fehlschlag (Implementierung fehlgeschlagen):**

```json
{
  "status": "failed",
  "retries": 0,
  "evidence": {
    "files_changed": [],
    "test_files": [],
    "test_count": 0,
    "commit_hash": null
  },
  "error": "slice-implementer returned status: failed"
}
```

**Fehlschlag (Test-Coverage unvollstaendig):**

```json
{
  "status": "failed",
  "retries": 0,
  "evidence": {
    "files_changed": ["backend/app/api/endpoints.py"],
    "test_files": ["tests/slices/feature/slice-02-api.test.ts"],
    "test_count": 8,
    "commit_hash": "abc123def"
  },
  "error": "test-writer ac_coverage: 80%, required: 100%"
}
```

**Fehlschlag (Max Retries / Debugger unable_to_fix):**

```json
{
  "status": "failed",
  "retries": 9,
  "evidence": {
    "files_changed": ["backend/app/api/endpoints.py"],
    "test_files": ["tests/slices/feature/slice-02-api.test.ts"],
    "test_count": 12,
    "commit_hash": "abc123def"
  },
  "error": "debugger: unable_to_fix after 9 retries"
}
```

### 4. Agent-Prompt-Struktur

Der Agent MUSS folgende Sections enthalten:

1. **YAML Frontmatter** - name, description, tools
2. **Rolle** - Beschreibung als Slice-Impl-Coordinator
3. **Input-Parsing** - Wie der Prompt vom `/build` Command geparst wird
4. **Phase 1: Dokumente laden** - Liest slice spec, architecture, integration-map
5. **Phase 2: Implementation** - Task(slice-implementer) mit korrektem Prompt
6. **Phase 3: Test-Erstellung** - Task(test-writer) mit korrektem Prompt
7. **Phase 4: Validation Loop** - Task(test-validator) + Task(debugger) Retry-Loop
8. **Phase 5: Evidence schreiben** - Evidence JSON auf Disk speichern
9. **Phase 6: JSON Output** - Strukturiertes JSON zurueckgeben

### 5. Task()-Call Prompts (KRITISCH)

#### Slice-Implementer Prompt:

```
Implementiere Slice: {slice_id}

## Input-Dateien (MUSS gelesen werden)
- Slice-Spec: {spec_path}/slices/{slice_file}
- Architecture: {architecture_path}
- Integration-Map: {integration_map_path}

## Anweisungen
1. Lies die Slice-Spec vollstaendig
2. Lies architecture.md fuer technische Vorgaben
3. Lies integration-map.md fuer Abhaengigkeiten
4. Implementiere ALLE Deliverables aus der Slice-Spec
5. Committe alle Aenderungen mit Message: "feat({slice_id}): {kurze Beschreibung}"

## Output
Gib am Ende ein JSON zurueck:
```json
{
  "status": "completed | failed",
  "files_changed": ["pfad/zur/datei.ts"],
  "commit_hash": "abc123"
}
```
```

#### Test-Writer Prompt:

```
Schreibe Tests fuer Slice: {slice_id}

## Input-Dateien (MUSS gelesen werden)
- Slice-Spec: {spec_path}/slices/{slice_file}
- Architecture: {architecture_path}

## Anweisungen
1. Lies die Slice-Spec vollstaendig (Acceptance Criteria + Testfaelle Section)
2. Lies die Test-Strategy Section fuer Stack und Commands
3. Schreibe Tests fuer ALLE Acceptance Criteria
4. ac_coverage MUSS 100% sein
5. Committe alle Test-Dateien

## Output
Gib am Ende ein JSON zurueck:
```json
{
  "status": "completed | failed",
  "test_files": ["tests/slices/feature/slice-02.test.ts"],
  "ac_coverage": 100
}
```
```

#### Test-Validator Prompt:

```
Validiere Tests fuer Slice: {slice_id}

## Mode
slice_validation

## Input-Dateien (MUSS gelesen werden)
- Slice-Spec: {spec_path}/slices/{slice_file}

## Anweisungen
1. Lies die Test-Strategy Section der Slice-Spec
2. Fuehre alle Test-Stages aus (Unit, Integration, Acceptance, Smoke)
3. Gib strukturiertes JSON zurueck

## Output
Gib am Ende ein JSON zurueck:
```json
{
  "overall_status": "passed | failed",
  "stages": {
    "unit": {"status": "passed | failed | skipped", "test_count": 12, "failed_count": 0},
    "integration": {"status": "passed | failed | skipped", "test_count": 0, "failed_count": 0},
    "acceptance": {"status": "passed | failed | skipped", "test_count": 5, "failed_count": 0},
    "smoke": {"status": "passed | failed | skipped", "app_started": true, "health_status": 200}
  },
  "error_output": null
}
```
```

#### Debugger Prompt:

```
Debugge fehlgeschlagene Tests fuer Slice: {slice_id}

## Fehlgeschlagene Test-Ausgabe
{error_output_from_test_validator}

## Input-Dateien (MUSS gelesen werden)
- Slice-Spec: {spec_path}/slices/{slice_file}
- Architecture: {architecture_path}

## Anweisungen
1. Analysiere die Fehlerausgabe
2. Formuliere eine Hypothese
3. Instrumentiere den Code fuer Beweise
4. Fixe den Root Cause
5. Committe den Fix

## Output
Gib am Ende ein JSON zurueck:
```json
{
  "status": "fixed | unable_to_fix",
  "root_cause": "Beschreibung des Root Cause",
  "files_changed": ["pfad/zur/datei.ts"]
}
```
```

### 6. Wiederverwendete Code-Bausteine

| Pattern | Quelle | Wiederverwendung |
|---------|--------|-----------------|
| Task(slice-implementer) Prompt-Format | `.claude/commands/orchestrate.md` Phase 2 | Exakt gleicher Prompt, nur von Agent statt Command aufgerufen |
| Task(test-writer) Prompt-Format | `.claude/commands/orchestrate.md` Phase 2 | Exakt gleicher Prompt |
| Task(test-validator) Prompt-Format | `.claude/commands/orchestrate.md` Phase 2 | Exakt gleicher Prompt |
| Task(debugger) Prompt-Format | `.claude/commands/orchestrate.md` Phase 2 | Exakt gleicher Prompt |
| JSON-Parsing Pattern | `.claude/commands/orchestrate.md` | "Find LAST ```json``` block" |
| Fresh Context Pattern | `.claude/commands/orchestrate.md` | Jeder Task()-Call bekommt frischen Context |
| Evidence-on-Disk Pattern | `.claude/commands/orchestrate.md` | Evidence JSON nach `.claude/evidence/` schreiben |

### 7. Evidence-Datei Format

```json
{
  "slice_id": "slice-02-api-integration",
  "status": "completed",
  "retries": 1,
  "files_changed": ["backend/app/api/endpoints.py", "backend/app/models.py"],
  "test_files": ["tests/slices/feature/slice-02-api.test.ts"],
  "test_count": 12,
  "commit_hash": "abc123def",
  "stages": {
    "unit": {"status": "passed", "test_count": 8, "failed_count": 0},
    "integration": {"status": "passed", "test_count": 4, "failed_count": 0},
    "acceptance": {"status": "skipped", "test_count": 0, "failed_count": 0},
    "smoke": {"status": "passed", "app_started": true, "health_status": 200}
  },
  "timestamp": "2026-03-01T14:30:00Z"
}
```

**Pfad:** `.claude/evidence/{feature_name}/{slice_id}.json`

Beispiel: `.claude/evidence/build-command/slice-02-slice-impl-coordinator.json`

---

## Acceptance Criteria

1) GIVEN ein spec_path mit einer genehmigten Slice-Spec und architecture.md und integration-map.md
   WHEN der slice-impl-coordinator mit slice_id und den Dateipfaden aufgerufen wird
   THEN ruft der Agent Task(slice-implementer) auf mit dem korrekten Prompt der spec_path, slice_file, architecture_path und integration_map_path enthaelt

2) GIVEN ein erfolgreicher Task(slice-implementer) mit status "completed"
   WHEN der Agent die JSON-Antwort parst
   THEN ruft der Agent Task(test-writer) auf mit dem korrekten Prompt der die Slice-Spec und Architecture referenziert

3) GIVEN ein Task(slice-implementer) mit status "failed"
   WHEN der Agent die JSON-Antwort parst
   THEN gibt der Agent sofort JSON zurueck mit `{"status": "failed", "error": "slice-implementer returned status: failed"}`

4) GIVEN ein Task(test-writer) mit ac_coverage < 100%
   WHEN der Agent die JSON-Antwort parst
   THEN gibt der Agent sofort JSON zurueck mit `{"status": "failed", "error": "test-writer ac_coverage: {N}%, required: 100%"}`

5) GIVEN ein erfolgreicher Task(test-writer) mit ac_coverage = 100%
   WHEN der Agent die JSON-Antwort parst
   THEN ruft der Agent Task(test-validator, mode=slice_validation) auf

6) GIVEN ein Task(test-validator) mit overall_status "passed"
   WHEN der Agent die JSON-Antwort parst
   THEN schreibt der Agent die Evidence-Datei nach `.claude/evidence/{feature}/{slice_id}.json` und gibt JSON mit `{"status": "completed"}` zurueck

7) GIVEN ein Task(test-validator) mit overall_status "failed"
   WHEN der Agent die JSON-Antwort parst
   THEN ruft der Agent Task(debugger) auf mit der error_output aus dem test-validator

8) GIVEN ein Task(debugger) mit status "fixed"
   WHEN der retry_count < 9
   THEN ruft der Agent Task(test-validator) erneut auf (Re-Validate nach Debug-Fix)

9) GIVEN ein Task(debugger) mit status "unable_to_fix"
   WHEN der Agent die JSON-Antwort parst
   THEN gibt der Agent sofort JSON zurueck mit `{"status": "failed", "error": "debugger: unable_to_fix"}`

10) GIVEN wiederholte Test-Failures und Debug-Fixes
    WHEN der retry_count >= 9 erreicht wird
    THEN gibt der Agent JSON zurueck mit `{"status": "failed", "retries": 9, "error": "max retries exceeded"}`

11) GIVEN ein erfolgreich abgeschlossener Slice
    WHEN der Agent die Evidence-Datei schreibt
    THEN enthaelt die Evidence-Datei alle Felder: slice_id, status, retries, files_changed, test_files, test_count, commit_hash, stages, timestamp

---

## Testfaelle

### Test-Datei

**Konvention:** Manuelle Tests - Agent-Datei erzeugt keinen ausfuehrbaren Code.

### Manuelle Tests

1. **Happy Path:** Agent mit einem einfachen Slice aufrufen (z.B. DB-Schema Slice).
   - Erwartung: Task(slice-implementer) wird aufgerufen, Task(test-writer) wird aufgerufen, Task(test-validator) wird aufgerufen, alle bestehen, Evidence-Datei wird geschrieben, JSON mit `"status": "completed"` wird zurueckgegeben.

2. **Impl Failure:** Agent mit einem Slice aufrufen bei dem die Implementierung fehlschlaegt.
   - Erwartung: Task(slice-implementer) gibt `"status": "failed"` zurueck, Agent gibt sofort `{"status": "failed", "error": "slice-implementer returned status: failed"}` zurueck. Kein Test-Writer oder Validator wird aufgerufen.

3. **Test Failure + Debug Fix:** Agent mit einem Slice aufrufen bei dem Tests fehlschlagen.
   - Erwartung: Task(test-validator) gibt `"overall_status": "failed"` zurueck, Task(debugger) wird aufgerufen, debugger gibt `"fixed"` zurueck, Task(test-validator) wird erneut aufgerufen, Tests bestehen, Evidence wird geschrieben.

4. **Max Retries:** Agent mit einem Slice aufrufen bei dem Tests wiederholt fehlschlagen.
   - Erwartung: Nach 9 Retry-Zyklen (debugger + re-validate) gibt Agent `{"status": "failed", "retries": 9}` zurueck.

5. **Debugger Unable to Fix:** Agent mit einem Slice aufrufen bei dem der Debugger den Fehler nicht beheben kann.
   - Erwartung: Task(debugger) gibt `"unable_to_fix"` zurueck, Agent gibt sofort `{"status": "failed", "error": "debugger: unable_to_fix"}` zurueck.

6. **AC Coverage Check:** Agent mit einem Slice aufrufen bei dem test-writer nur 80% AC Coverage erreicht.
   - Erwartung: Agent gibt sofort `{"status": "failed", "error": "test-writer ac_coverage: 80%, required: 100%"}` zurueck. Kein Test-Validator wird aufgerufen.

7. **Evidence-Datei:** Nach erfolgreichem Durchlauf pruefen ob `.claude/evidence/{feature}/{slice_id}.json` existiert und alle Pflichtfelder enthaelt.

---

## Definition of Done

- [x] Akzeptanzkriterien sind eindeutig & vollstaendig
- [x] Agent-Datei folgt bestehendem Agent-Format (YAML Frontmatter)
- [x] Task()-Call-Prompts sind identisch mit bestehendem orchestrate.md Pattern
- [x] JSON Output Contract ist definiert und konsistent mit architecture.md
- [x] Retry-Logik mit max 9 Versuchen implementiert
- [x] Evidence-on-Disk Pattern dokumentiert

---

## Integration Contract (GATE 2 PFLICHT)

### Requires From Other Slices

| Slice | Resource | Type | Validation |
|-------|----------|------|------------|
| -- | Keine Abhaengigkeiten | -- | -- |

**Externe Abhaengigkeiten (bestehende, unveraenderte Agents):**

| Agent | Resource | Type | Validation |
|-------|----------|------|------------|
| `slice-implementer` | Task()-Aufruf | Agent (Ebene 2) | Schreibt Code-Dateien, committet, returniert JSON `{status, files_changed, commit_hash}` |
| `test-writer` | Task()-Aufruf | Agent (Ebene 2) | Schreibt Test-Dateien, returniert JSON `{status, test_files, ac_coverage}` |
| `test-validator` | Task()-Aufruf | Agent (Ebene 2) | Fuehrt Tests aus, returniert JSON `{overall_status, stages, error_output}` |
| `debugger` | Task()-Aufruf | Agent (Ebene 2) | Analysiert + fixt Fehler, returniert JSON `{status, root_cause, files_changed}` |

### Provides To Other Slices

| Resource | Type | Consumer | Interface |
|----------|------|----------|-----------|
| `slice-impl-coordinator` Agent | Agent (Ebene 1) | Slice 3 (`/build` Command) | `Task(subagent_type: "slice-impl-coordinator")` -> JSON `{status, retries, evidence, error}` |
| JSON Output Contract | Data Contract | Slice 3 (`/build` Command) | `{"status": "completed\|failed", "retries": int, "evidence": {...}, "error": string\|null}` |
| Evidence JSON File | File Artifact | Slice 3 (`/build` Command) | `.claude/evidence/{feature}/{slice_id}.json` |

### Integration Validation Tasks

- [ ] `slice-implementer` Agent existiert und ist unveraendert aufrufbar
- [ ] `test-writer` Agent existiert und ist unveraendert aufrufbar
- [ ] `test-validator` Agent existiert und ist unveraendert aufrufbar (mode=slice_validation)
- [ ] `debugger` Agent existiert und ist unveraendert aufrufbar
- [ ] JSON Output kann vom `/build` Command geparst werden (Pattern: "Find LAST ```json``` block")
- [ ] Prompts an alle Sub-Agents sind kompatibel mit deren erwarteten Inputs
- [ ] Evidence-Pfad `.claude/evidence/{feature}/{slice_id}.json` ist konsistent mit bestehendem Evidence-Pattern

---

## Code Examples (MANDATORY - GATE 2 PFLICHT)

> **KRITISCH:** Alle Code-Beispiele in diesem Dokument sind **PFLICHT-Deliverables**.
> Der Gate 2 Compliance Agent prueft, dass jedes Code-Beispiel implementiert wird.

| Code Example | Section | Mandatory | Notes |
|--------------|---------|-----------|-------|
| Agent YAML Frontmatter | Agent-Datei Header | YES | Name, Description, Tools |
| 4-Step Pipeline + Retry-Loop Pseudocode | Agent-Datei Core Logic | YES | Impl -> Test-Writer -> Validator -> Debugger, Max 9 Retries |
| JSON Output Block | Agent-Datei Abschluss | YES | Exakt wie Output Contract definiert |
| slice-implementer Prompt | Agent-Datei Phase 2 | YES | Identisch mit orchestrate.md Pattern |
| test-writer Prompt | Agent-Datei Phase 3 | YES | Identisch mit orchestrate.md Pattern |
| test-validator Prompt | Agent-Datei Phase 4 | YES | Mode: slice_validation |
| debugger Prompt | Agent-Datei Phase 4 | YES | Enthaelt error_output aus test-validator |
| Evidence JSON Format | Agent-Datei Phase 5 | YES | Alle Pflichtfelder vorhanden |

### Agent YAML Frontmatter

```yaml
---
name: slice-impl-coordinator
description: "Ebene-1 Coordinator: Implementiert + testet 1 Slice via Task(slice-implementer) + Task(test-writer) + Task(test-validator) + Task(debugger). Retry-Loop (max 9). Returns JSON."
tools: Read, Write, Glob, Grep, Task
---
```

### Agent Core Logic (4-Step Pipeline + Retry-Loop)

```markdown
## Phase 1: Dokumente laden

1. Lies die Slice-Spec: {spec_path}/slices/{slice_file}
2. Lies architecture.md: {architecture_path}
3. Lies integration-map.md: {integration_map_path}
4. Extrahiere slice_id aus Metadata Section der Slice-Spec
5. Extrahiere feature_name aus spec_path (letztes Pfad-Segment)

## Phase 2: Implementation

Task(
  subagent_type: "slice-implementer",
  description: "Implement Slice {slice_id}",
  prompt: "{implementer-prompt}"
)

Parse JSON-Antwort (letzter ```json``` Block).

IF status == "failed":
  GOTO Phase 6: Return {status: "failed", error: "slice-implementer returned status: failed"}

Speichere: files_changed, commit_hash

## Phase 3: Test-Erstellung

Task(
  subagent_type: "test-writer",
  description: "Write Tests for {slice_id}",
  prompt: "{test-writer-prompt}"
)

Parse JSON-Antwort (letzter ```json``` Block).

IF ac_coverage < 100:
  GOTO Phase 6: Return {status: "failed", error: "test-writer ac_coverage: {N}%, required: 100%"}

Speichere: test_files, test_count (= Anzahl test_files oder aus ac_coverage)

## Phase 4: Validation + Debug Loop

MAX_RETRIES = 9
retry_count = 0

WHILE retry_count < MAX_RETRIES:

  # Step 1: Validate
  Task(
    subagent_type: "test-validator",
    description: "Validate Tests for {slice_id}",
    prompt: "{test-validator-prompt mit mode=slice_validation}"
  )

  Parse JSON-Antwort (letzter ```json``` Block).

  IF overall_status == "passed":
    Speichere: stages
    GOTO Phase 5: Evidence schreiben

  # Step 2: Debug
  error_output = JSON.error_output

  Task(
    subagent_type: "debugger",
    description: "Debug {slice_id}",
    prompt: "{debugger-prompt mit error_output}"
  )

  Parse JSON-Antwort (letzter ```json``` Block).

  IF status == "unable_to_fix":
    GOTO Phase 6: Return {status: "failed", error: "debugger: unable_to_fix"}

  IF status == "fixed":
    Merge files_changed mit debugger.files_changed
    retry_count++
    CONTINUE (re-validate)

# Max Retries erreicht
GOTO Phase 6: Return {status: "failed", retries: 9, error: "max retries exceeded"}

## Phase 5: Evidence schreiben

evidence_path = .claude/evidence/{feature_name}/{slice_id}.json

Write(evidence_path, {
  "slice_id": "{slice_id}",
  "status": "completed",
  "retries": retry_count,
  "files_changed": files_changed,
  "test_files": test_files,
  "test_count": test_count,
  "commit_hash": commit_hash,
  "stages": stages,
  "timestamp": "{ISO 8601 now}"
})

## Phase 6: JSON Output

Am Ende deiner Ausfuehrung gibst du EXAKT dieses JSON zurueck:

\```json
{
  "status": "completed",
  "retries": 0,
  "evidence": {
    "files_changed": ["..."],
    "test_files": ["..."],
    "test_count": 12,
    "commit_hash": "abc123"
  },
  "error": null
}
\```

KRITISCH: Das JSON MUSS das LETZTE Code-Block in deiner Antwort sein.
Der /build Command parst es mit dem Pattern "Find LAST ```json``` block".
```

---

## Constraints & Hinweise

**Betrifft:**
- Nur die Datei `.claude/agents/slice-impl-coordinator.md`
- Keine Aenderungen an bestehenden Agents oder Commands

**Agent-Format:**
- YAML Frontmatter mit `name`, `description`, `tools`
- Markdown-Body mit Pseudocode-Logik (kein ausfuehrbarer Code)
- Identisches Format wie bestehende Agents (z.B. `.claude/agents/slice-implementer.md`)

**Abgrenzung:**
- Dieser Agent implementiert EINEN Slice, nicht alle Slices
- Die Slice-Reihenfolge und Gesamtsteuerung liegt beim `/build` Command (Slice 3)
- Bestehende Sub-Agents (slice-implementer, test-writer, test-validator, debugger) bleiben unveraendert
- Kein State-File schreiben (das macht der `/build` Command)
- Evidence-Datei wird von DIESEM Agent geschrieben (nicht vom `/build` Command)

**Fehler-Eskalation:**
- JSON Parse Failure bei Sub-Agent-Output: Sofort return `{status: "failed", error: "JSON parse failure from {agent_name}"}`
- Unerwartete Fehler: Sofort return `{status: "failed", error: "Unexpected error: {description}"}`

---

## Deliverables (SCOPE SAFEGUARD)

**WICHTIG: Diese Liste wird automatisch vom Stop-Hook validiert. Der Agent kann nicht stoppen, wenn Dateien fehlen.**

<!-- DELIVERABLES_START -->
### Agent-Datei
- [ ] `.claude/agents/slice-impl-coordinator.md` -- Neuer Ebene-1 Coordinator Agent fuer Implementation + Testing eines einzelnen Slices mit 4-Step Sub-Agent Pipeline und Retry-Loop

### Tests
- [ ] Manuelle Validierung: Agent mit einem Test-Slice aufrufen und pruefen ob Code-Dateien, Test-Dateien und Evidence-JSON erstellt werden und JSON-Output korrekt ist
<!-- DELIVERABLES_END -->

**Hinweis fuer den Implementierungs-Agent:**
- Alle Dateien zwischen `<!-- DELIVERABLES_START -->` und `<!-- DELIVERABLES_END -->` sind **Pflicht**
- Der Stop-Hook prueft automatisch ob alle Dateien existieren
- Bei fehlenden Dateien wird der Agent blockiert und muss nachfragen

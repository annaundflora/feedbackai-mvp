# Slice 3: Orchestrator Pipeline komplett umbauen

> **Slice 3 von 4** fuer `Lean Testing Pipeline`
>
> | Navigation | |
> |------------|---|
> | **Vorheriger:** | `slice-02-test-validator-agent.md` |
> | **Naechster:** | `slice-04-planner-gates.md` |

---

## Metadata (fuer Orchestrator)

| Key | Value |
|-----|-------|
| **ID** | `slice-03-orchestrator-pipeline` |
| **Test** | `cd backend && python -m pytest tests/acceptance/test_slice_03_orchestrator_pipeline.py -v` |
| **E2E** | `false` |
| **Dependencies** | `["slice-01-test-writer-enhancement", "slice-02-test-validator-agent"]` |

---

## Slice-Uebersicht

| # | Slice | Status | Datei |
|---|-------|--------|-------|
| 1 | Test-Writer Agent Enhancement | Ready | `slice-01-test-writer-enhancement.md` |
| 2 | Test-Validator Agent | Ready | `slice-02-test-validator-agent.md` |
| 3 | Orchestrator Pipeline | Ready | `slice-03-orchestrator-pipeline.md` |
| 4 | Planner & Gate Improvements | Pending | `slice-04-planner-gates.md` |

---

## Kontext & Ziel

Der bestehende Orchestrator (`.claude/commands/orchestrate.md`) hat folgende Defizite:

1. **Direkte Bash-Ausfuehrung** -- Orchestrator fuehrt Tests selbst via `Bash()` aus (Context Pollution, Rule 4 Verstoss)
2. **Nur 1 von 9 Quality Gates effektiv** -- Nur Unit Tests mit exit_code, keine Acceptance/Smoke/Regression
3. **2 Retries statt 3** -- Weniger Retry-Budget fuer mehr Stages
4. **TypeScript hardcoded** -- Final Validation nutzt `pnpm lint`, `pnpm tsc --noEmit`, `pnpm build` (Python wird uebersprungen)
5. **Implementer schreibt Tests** -- Zeile 39 in slice-implementer.md: "Tests schreiben" (Rule 1 Verstoss)
6. **Kein Pre-Impl Sanity Check** -- Compliance-Files werden nie geprueft
7. **Evidence-Format unvollstaendig** -- Nur `unit_test` Sektion, keine `tests`/`validation` Sektionen
8. **Kein Re-Run ab fehlgeschlagenem Stage** -- Bei Retry wird komplett von vorne gestartet

Dieser Slice:
- **Ersetzt** `orchestrate.md` komplett mit 4-Sub-Agent-Pipeline
- **Modifiziert** `slice-implementer.md` (Tests-Regel entfernen, JSON Output anpassen)
- Fuehrt Pre-Impl Sanity Check ein
- Nutzt JSON-Parsing fuer alle Agent-Outputs
- Erhoet Retries auf 3
- Ermoeglicht Re-Run ab fehlgeschlagenem Stage
- Macht Final Validation stack-agnostisch

---

## Technische Umsetzung

### Architektur-Kontext (aus architecture.md)

> **Quelle:** `architecture.md` -> Orchestrator Pipeline Flow, Agent Invocation Rules, State Machine, Evidence Format, Final Validation

```
Pre-Impl Sanity Check
  |
  v
FOR each Slice:
  Task(slice-implementer) -> Code
  Task(test-writer) -> Tests
  Task(test-validator) -> Validate (Unit -> Integration -> Acceptance -> Smoke -> Regression)
  IF failed: Task(debugger) -> Fix -> Re-validate (max 3x)
  Evidence speichern
  |
  v
Final Validation (Lint -> Type Check -> Build -> Full Smoke -> Full Regression)
```

### 1. Architektur-Impact

| Layer | Aenderungen |
|-------|------------|
| `.claude/commands/orchestrate.md` | Komplett-Ersetzung: 4 Sub-Agent-Steps, Pre-Impl Check, JSON-Parsing, 3 Retries, stack-agnostisch |
| `.claude/agents/slice-implementer.md` | Modification: Tests-Regeln entfernen, JSON Output Contract anpassen |

### 2. Datenfluss (Neue Pipeline pro Slice)

```
Orchestrator Start
  |
  v
[Pre-Impl Sanity Check]
  |-- Pruefe: {spec_path}/slices/compliance-slice-*.md existieren + APPROVED
  |-- Bei Fehler: HARD STOP "Planner muss zuerst laufen"
  |
  v
FOR EACH Slice:
  |
  v
[Step 1: Task(slice-implementer)]
  Input: Slice-Spec, Architecture, Integration-Map
  Output JSON: { status, files_changed, commit_hash, notes }
  |-- Parse letzten ```json``` Block
  |-- status == "failed" -> HARD STOP
  |
  v
[Step 2: Task(test-writer)]
  Input: Slice-Spec (ACs), files_changed, Test-Strategy Metadata
  Output JSON: { status, test_files, test_count, ac_coverage, commit_hash }
  |-- Parse letzten ```json``` Block
  |-- status == "failed" -> HARD STOP
  |-- ac_coverage.total != ac_coverage.covered -> HARD STOP
  |
  v
[Step 3: Task(test-validator)]
  Input: Test-Paths, Previous-Slice-Tests, Mode, Working-Directory
  Output JSON: { overall_status, stages, failed_stage?, error_output? }
  |-- Parse letzten ```json``` Block
  |-- overall_status == "passed" -> Evidence speichern -> Naechster Slice
  |-- overall_status == "failed" -> Retry Loop
  |
  v
[Retry Loop (max 3x)]
  |
  v
[Step 4: Task(debugger)]
  Input: Failed Stage Output, Slice-Spec, geaenderte Dateien
  Output JSON: { status, root_cause, files_changed, commit_hash }
  |-- status == "fixed" -> Re-run Task(test-validator) ab fehlgeschlagenem Stage
  |-- status == "unable_to_fix" -> HARD STOP
  |
  v
[Evidence speichern] -> Naechster Slice
  |
  v
[Final Validation]
  Task(test-validator) mit mode: final_validation
  |-- Lint (Auto-Fix + Check)
  |-- Type Check
  |-- Build
  |-- Full Smoke
  |-- Full Regression
```

### 3. Orchestrate.md: Komplett-Ersetzung

Der bestehende Orchestrator wird komplett ersetzt. Die neue Version hat folgende Phasen:

#### Phase 1: Input-Validierung & Config-Parsing (ANGEPASST)

Identisch zum bisherigen, PLUS:
- Pre-Impl Sanity Check: Pruefe ob `compliance-slice-*.md` Dateien existieren und APPROVED enthalten
- Bei fehlenden/nicht-approvedten Compliance-Files: HARD STOP

#### Phase 2: Setup & State Management (ERWEITERT)

State-Machine bekommt neue States gemaess architecture.md:
- `pre_check`, `implementing`, `writing_tests`, `validating`, `auto_fixing`, `slice_complete`, `hard_stop`, `final_validation`, `feature_complete`

State-File erhaelt neue Felder:
- `current_state`: Aktueller State der State-Machine (statt nur `current_slice_id`)
- `retry_count`: Anzahl Retries fuer aktuellen Slice
- `failed_stage`: Zuletzt fehlgeschlagener Stage (fuer Re-Run ab Stage)

#### Phase 3: Wave-Based Implementation (KOMPLETT NEU)

Die Kernlogik wird komplett ersetzt. Statt 2 Steps (Implement + Bash-Test) gibt es jetzt 4 Sub-Agent-Steps:

**Step 1: Task(slice-implementer) -> Code**
- Prompt enthaelt: Slice-Spec, Architecture, Integration-Map
- Implementer schreibt NUR Code, KEINE Tests
- Output wird als JSON geparsed
- Bei `status: failed` -> HARD STOP

**Step 2: Task(test-writer) -> Tests**
- Prompt enthaelt: Slice-Spec (ACs), files_changed aus Step 1, Test-Strategy Metadata
- Test-Writer schreibt Tests gegen Spec
- Output wird als JSON geparsed
- Bei `status: failed` oder `ac_coverage.total != ac_coverage.covered` -> HARD STOP

**Step 3: Task(test-validator) -> Validate**
- Prompt enthaelt: Test-Paths, Previous-Slice-Tests, Mode="slice_validation", Working-Directory
- Validator fuehrt alle Stages aus (Unit -> Integration -> Acceptance -> Smoke -> Regression)
- Output wird als JSON geparsed
- Bei `overall_status: passed` -> Evidence speichern, naechster Slice
- Bei `overall_status: failed` -> Retry Loop

**Step 4 (nur bei Failure): Task(debugger) -> Fix**
- Prompt enthaelt: Failed Stage Output, Slice-Spec, geaenderte Dateien, failed_stage
- Debugger analysiert und fixt Code (NICHT Tests, ausser technische Fehler)
- Output wird als JSON geparsed
- Bei `status: fixed` -> Re-run Task(test-validator) (mit gleichen Inputs, ab fehlgeschlagenem Stage)
- Bei `status: unable_to_fix` -> HARD STOP
- Max 3 Retries pro Slice

#### Phase 4: Final Validation (KOMPLETT NEU)

Statt hardcoded `pnpm lint/tsc/build`:
- Task(test-validator) mit `mode: final_validation`
- Test-Validator erkennt Stack automatisch und fuehrt passende Commands aus
- Bei Failure: Task(debugger) -> Fix -> Re-validate (max 3 Retries)

#### Phase 5: Completion (ERWEITERT)

Evidence-Format erhaelt neue Sektionen:
- `implementation`: Implementer Output
- `tests`: Test-Writer Output (test_files, test_count, ac_coverage)
- `validation`: Test-Validator Output (stages mit unit, integration, acceptance, smoke, regression)
- `retries`: Anzahl Debugger-Retries

### 4. JSON-Parsing Logik

Jeder Sub-Agent-Output wird nach dem gleichen Pattern geparsed:

```
1. Agent-Output (String) erhalten
2. Suche den LETZTEN ```json``` Block im Output
3. Extrahiere den JSON-String zwischen ``` Markern
4. JSON.parse()
5. Bei Parse-Failure: HARD STOP mit Fehler-Details
6. Validiere erwartete Felder (status, files_changed, etc.)
7. Bei fehlenden Pflichtfeldern: HARD STOP
```

**KRITISCH:** Bei JSON-Parse-Failure gibt es KEIN Retry. Es ist ein HARD STOP weil der Agent unerwartetes Format geliefert hat.

### 5. Re-Run ab fehlgeschlagenem Stage

Nach einem Debugger-Fix wird der Test-Validator nicht komplett von vorne gestartet, sondern ab dem fehlgeschlagenen Stage:

```
Beispiel: Acceptance Stage fehlgeschlagen
1. Debugger fixt Code
2. Test-Validator Re-Run:
   - Unit: Re-run (Fix kann Unit-Tests beeinflussen)
   - Integration: Re-run (Fix kann Integration beeinflussen)
   - Acceptance: Re-run (war fehlgeschlagen)
   - Smoke: Re-run
   - Regression: Re-run
```

**Vereinfachung:** Da ein Fix jeden Stage beeinflussen kann, werden ALLE Stages ab dem fehlgeschlagenen Stage re-run. In der Praxis bedeutet das: Der Test-Validator wird komplett neu aufgerufen, erhaelt aber den Hinweis `re_run_from: "{failed_stage}"` im Prompt.

### 6. slice-implementer.md Anpassungen

Die folgenden Aenderungen werden am bestehenden Slice-Implementer vorgenommen:

| Zeile/Section | Aktuell | Neu | Typ |
|---------------|---------|-----|-----|
| Regeln-Tabelle, Zeile 39 | `Tests schreiben -- Wie in der Spec definiert` | ENTFERNEN | DELETE |
| Workflow, Schritt 6 | `Schreibe Tests (falls in Spec)` | ENTFERNEN | DELETE |
| Erlaubt-Section | `Tests schreiben (aber nicht ausfuehren)` | ENTFERNEN | DELETE |
| Tests-Section (Implementierungs-Guidelines) | TypeScript Test-Beispiele | ENTFERNEN (komplett) | DELETE |
| Neue Regel | -- | `Du schreibst NUR Code, KEINE Tests. Der Test-Writer Agent uebernimmt Tests.` | ADD |
| JSON Output Contract | `{ status, files_changed, commit_message, notes }` | `{ status, files_changed, commit_hash, notes }` (commit_message -> commit_hash) | MODIFY |
| Orchestrator Prompt | Zeile 3: "Schreibe Tests wie in der Spec definiert" | ENTFERNEN | DELETE |

#### Neuer JSON Output Contract fuer Slice-Implementer:

```json
{
  "status": "completed",
  "files_changed": [
    "backend/app/service/auth.py",
    "backend/app/api/routes/auth.py"
  ],
  "commit_hash": "abc123def456",
  "notes": "Optional: Hinweise fuer den Orchestrator"
}
```

Bei Fehler:

```json
{
  "status": "failed",
  "files_changed": [],
  "commit_hash": "",
  "notes": "Beschreibung des Problems"
}
```

### 7. State Machine Implementation

Die State-Machine wird in der `.orchestrator-state.json` getrackt:

```json
{
  "spec_path": "specs/2026-02-14-orchestrator-robust-testing",
  "feature_name": "orchestrator-robust-testing",
  "status": "in_progress",
  "current_state": "validating",
  "current_slice_id": "slice-02-test-validator-agent",
  "retry_count": 1,
  "failed_stage": "acceptance",
  "waves": [...],
  "completed_slices": ["slice-01-test-writer-enhancement"],
  "evidence_files": [...]
}
```

State-Transitions (aus architecture.md):

| From | Trigger | To |
|------|---------|-----|
| `pre_check` | Compliance OK | `implementing` |
| `pre_check` | Compliance fehlt/FAILED | `hard_stop` |
| `implementing` | status: completed | `writing_tests` |
| `implementing` | status: failed | `hard_stop` |
| `writing_tests` | Tests + AC-Coverage 100% | `validating` |
| `writing_tests` | status: failed | `hard_stop` |
| `writing_tests` | AC-Coverage < 100% | `hard_stop` |
| `validating` | overall_status: passed | `slice_complete` |
| `validating` | overall_status: failed, retries < 3 | `auto_fixing` |
| `validating` | overall_status: failed, retries >= 3 | `hard_stop` |
| `auto_fixing` | status: fixed | `validating` |
| `auto_fixing` | status: unable_to_fix | `hard_stop` |
| `slice_complete` | Evidence saved | `implementing` (naechster Slice) |
| letzter `slice_complete` | Alle Slices fertig | `final_validation` |
| `final_validation` | Alles gruen | `feature_complete` |
| `final_validation` | Failure, retries < 3 | `auto_fixing` |

### 8. Evidence-Format (Erweitert)

Jeder Slice produziert ein Evidence-File in `.claude/evidence/{feature_name}/{slice_id}.json`:

```json
{
  "feature": "orchestrator-robust-testing",
  "slice": "slice-02-test-validator-agent",
  "timestamp": "2026-02-14T15:30:00Z",
  "status": "completed",
  "implementation": {
    "status": "completed",
    "files_changed": [".claude/agents/test-validator.md"],
    "commit_hash": "abc123"
  },
  "tests": {
    "status": "completed",
    "test_files": ["tests/acceptance/test_slice_02_test_validator_agent.py"],
    "test_count": { "unit": 0, "integration": 0, "acceptance": 9 },
    "ac_coverage": { "total": 9, "covered": 9, "missing": [] },
    "commit_hash": "def456"
  },
  "validation": {
    "overall_status": "passed",
    "stages": {
      "unit": { "exit_code": 0, "duration_ms": 0, "summary": "no tests found (directory does not exist)" },
      "integration": { "exit_code": 0, "duration_ms": 0, "summary": "no tests found (directory does not exist)" },
      "acceptance": { "exit_code": 0, "duration_ms": 2100, "summary": "9 passed, 0 failed" },
      "smoke": { "app_started": true, "health_status": 200, "startup_duration_ms": 4500 },
      "regression": { "exit_code": 0, "slices_tested": ["slice-01"] }
    }
  },
  "retries": 0
}
```

### 9. HARD STOP Conditions

| Condition | Phase | Recovery |
|-----------|-------|----------|
| Compliance-Files fehlen/FAILED | Pre-Check | `/planner` ausfuehren |
| Implementer `status: failed` | Step 1 | Spec ueberarbeiten |
| Test-Writer `status: failed` | Step 2 | ACs in Spec klaeren |
| AC-Coverage < 100% | Step 2 | Fehlende ACs in Spec ergaenzen |
| JSON Parse Failure | Jeder Step | Agent-Definition pruefen |
| Debugger `status: unable_to_fix` | Step 4 | Manuelles Eingreifen |
| 3 Retries erschoepft | Retry Loop | Manuelles Eingreifen, dann Resume |
| Final Validation 3x failed | Final | Manuelles Eingreifen |

### 10. Wave-basierte Parallelisierung

Bleibt erhalten wie bisher:
- Slices innerhalb einer Wave KOENNEN parallel laufen (`parallel: true` in orchestrator-config)
- Slices zwischen Waves sind IMMER sequenziell
- Jeder Slice durchlaeuft die 4-Step-Pipeline unabhaengig

### 11. "No Direct Bash" Rule

Der neue Orchestrator fuehrt KEINE Bash-Commands direkt aus:

| Aktuell (ALT) | Neu |
|----------------|-----|
| `Bash("python -m pytest ...")` im Orchestrator | `Task(test-validator, ...)` |
| `Bash("pnpm lint")` im Orchestrator | `Task(test-validator, mode: final_validation)` |
| `Bash("pnpm tsc --noEmit")` im Orchestrator | `Task(test-validator, mode: final_validation)` |
| `Bash("pnpm build")` im Orchestrator | `Task(test-validator, mode: final_validation)` |
| `Bash("git diff --name-only ...")` im Orchestrator | Entfaellt (Consumer-File-Check entfernt, Integration Map + Tests fangen das) |

**Ausnahmen die bleiben:**
- `mkdir -p` fuer Evidence-Ordner (kein Test/Validation)
- `git checkout -b` fuer Feature-Branch (kein Test/Validation)
- `Read()`/`Write()` fuer State/Evidence Files (kein Bash)

---

## Constraints & Hinweise

**Betrifft:**
- `.claude/commands/orchestrate.md` -- Komplett-Ersetzung
- `.claude/agents/slice-implementer.md` -- Modification (Tests-Regeln entfernen)

**Business Rules (aus Discovery):**
- Rule 1: Implementer schreibt NUR Code, KEINE Tests
- Rule 3: Debugger fixt primaer Code, Tests nur bei technischen Fehlern
- Rule 4: Orchestrator fuehrt KEINE Bash-Commands direkt aus
- Rule 6: Exit Code ist Wahrheit (`exit_code == 0` = BESTANDEN)
- Rule 7: 3 Retries, Re-Run ab fehlgeschlagenem Stage
- Rule 8: Evidence-Based (JSON pro Slice)
- Rule 16: Wave-basierte Parallelisierung bleibt erhalten
- Rule 18: Sub-Agent Output ist JSON im letzten Code-Block

**Abgrenzung:**
- Dieser Slice aendert NICHT den Test-Writer Agent (Slice 1)
- Dieser Slice aendert NICHT den Test-Validator Agent (Slice 2)
- Dieser Slice aendert NICHT den Debugger Agent (funktioniert, keine Aenderung noetig)
- Dieser Slice aendert NICHT das plan-spec Template (Slice 4)
- Dieser Slice aendert NICHT den Planner/Gate 2 (Slice 4)

---

## Integration Contract (GATE 2 PFLICHT)

### Requires From Other Slices

| Slice | Resource | Type | Validation |
|-------|----------|------|------------|
| slice-01-test-writer-enhancement | Test-Writer Agent Definition | Agent (.md) | Agent reagiert auf `Task(test-writer, prompt)` und liefert JSON Output Contract |
| slice-01-test-writer-enhancement | JSON Output Contract | Datenformat | `{ status, test_files, test_count, ac_coverage, commit_hash }` ist parsebar |
| slice-02-test-validator-agent | Test-Validator Agent Definition | Agent (.md) | Agent reagiert auf `Task(test-validator, prompt)` und liefert JSON Output Contract |
| slice-02-test-validator-agent | JSON Output Contract | Datenformat | `{ overall_status, stages, failed_stage?, error_output? }` ist parsebar |
| slice-02-test-validator-agent | Stage-Skip-Semantik | Konvention | Bei Failure: nachfolgende Stages `exit_code: -1`, `summary: "skipped"` |

### Provides To Other Slices

| Resource | Type | Consumer | Interface |
|----------|------|----------|-----------|
| Orchestrator Command | Command (.md) | Slice 4 (Planner) | `/orchestrate {spec_path}` startet Pipeline |
| Evidence-Format (erweitert) | Datenformat | Alle nachfolgenden Features | `{ implementation, tests, validation, retries }` JSON pro Slice |
| Slice-Implementer (angepasst) | Agent (.md) | Alle nachfolgenden Features | Implementer schreibt NUR Code, liefert `{ status, files_changed, commit_hash, notes }` |
| State-Machine | State-File (.json) | Resume-Faehigkeit | `{ current_state, retry_count, failed_stage }` |

### Integration Validation Tasks

- [ ] Orchestrator-Command parseable (Markdown mit korrektem Frontmatter)
- [ ] 4 Sub-Agent-Steps korrekt definiert (Implementer, Test-Writer, Test-Validator, Debugger)
- [ ] JSON-Parsing-Logik fuer alle 4 Agent-Outputs dokumentiert
- [ ] Evidence-Format stimmt mit architecture.md ueberein
- [ ] State-Machine-Transitions stimmen mit architecture.md ueberein
- [ ] Slice-Implementer JSON Output Contract angepasst (commit_message -> commit_hash)
- [ ] Tests-Regeln aus Slice-Implementer entfernt

---

## Acceptance Criteria

1) GIVEN der neue Orchestrator wird gestartet
   WHEN er die Pre-Impl Sanity Check ausfuehrt
   THEN prueft er ob `{spec_path}/slices/compliance-slice-*.md` Dateien existieren und den String "APPROVED" enthalten, und bei Fehlen stoppt er mit HARD STOP und der Nachricht "Planner muss zuerst laufen"

2) GIVEN der Orchestrator implementiert einen Slice
   WHEN er den Slice-Implementer aufruft
   THEN ruft er `Task(slice-implementer)` auf mit Slice-Spec, Architecture und Integration-Map als Input, und der Implementer-Prompt enthaelt KEINE Anweisung Tests zu schreiben

3) GIVEN der Orchestrator hat den Implementer-Output erhalten
   WHEN er den Test-Writer aufruft
   THEN ruft er `Task(test-writer)` auf mit Slice-Spec (ACs), `files_changed` aus dem Implementer-Output und Test-Strategy Metadata als Input

4) GIVEN der Orchestrator hat den Test-Writer-Output erhalten
   WHEN er die Tests validiert
   THEN ruft er `Task(test-validator)` auf mit den Test-Paths, Previous-Slice-Tests und `mode: slice_validation` als Input

5) GIVEN der Test-Validator meldet `overall_status: failed` und der Retry-Count ist kleiner als 3
   WHEN der Orchestrator den Retry-Loop startet
   THEN ruft er `Task(debugger)` auf mit dem Failed Stage Output, der Slice-Spec und den geaenderten Dateien, und bei `status: fixed` re-ruft er `Task(test-validator)` mit den gleichen Inputs

6) GIVEN der Retry-Count hat 3 erreicht und der Test-Validator meldet immer noch `overall_status: failed`
   WHEN der Orchestrator das Ergebnis verarbeitet
   THEN stoppt er mit HARD STOP, speichert Evidence mit `status: failed` und `retries: 3`, und gibt die Nachricht "3 Retries erschoepft" aus

7) GIVEN alle Slices sind erfolgreich implementiert und validiert
   WHEN der Orchestrator die Final Validation startet
   THEN ruft er `Task(test-validator)` auf mit `mode: final_validation` (kein direktes `Bash("pnpm lint")`, `Bash("pnpm tsc")` oder `Bash("pnpm build")`)

8) GIVEN ein Sub-Agent liefert seinen Output
   WHEN der Orchestrator den Output parsed
   THEN extrahiert er den LETZTEN ```json``` Block aus dem Agent-Output, parsed ihn als JSON, und bei Parse-Failure stoppt er mit HARD STOP (kein Retry)

9) GIVEN der Test-Writer meldet `ac_coverage.total != ac_coverage.covered`
   WHEN der Orchestrator das Ergebnis verarbeitet
   THEN stoppt er mit HARD STOP und gibt die fehlenden AC-IDs (`ac_coverage.missing`) in der Fehlermeldung aus

10) GIVEN ein Slice wurde erfolgreich validiert (alle Stages passed)
    WHEN der Orchestrator Evidence speichert
    THEN enthaelt die Evidence-Datei die Sektionen `implementation` (aus Implementer-Output), `tests` (aus Test-Writer-Output mit test_files, test_count, ac_coverage), `validation` (aus Test-Validator-Output mit stages), und `retries` (Anzahl Debugger-Retries)

11) GIVEN der bestehende Slice-Implementer Agent
    WHEN die Modification angewendet wird
    THEN enthaelt die Agent-Definition KEINE Regel "Tests schreiben", KEINEN Workflow-Schritt "Schreibe Tests", und KEINEN Erlaubt-Eintrag "Tests schreiben", und stattdessen die Regel "Du schreibst NUR Code, KEINE Tests. Der Test-Writer Agent uebernimmt Tests."

12) GIVEN der angepasste Slice-Implementer Agent
    WHEN er seinen Output liefert
    THEN hat der JSON Output Contract die Felder `status`, `files_changed`, `commit_hash` und `notes` (NICHT `commit_message`)

13) GIVEN der Orchestrator
    WHEN er die gesamte Pipeline durchlaeuft
    THEN fuehrt er zu KEINEM Zeitpunkt direkt `Bash()` fuer Tests, Lint, Type-Check oder Build aus (alles via Sub-Agents)

---

## Testfaelle

### Test-Datei

`tests/acceptance/test_slice_03_orchestrator_pipeline.py`

**Hinweis:** Da dieser Slice Markdown-Dateien (Command + Agent-Definition) aendert und keinen ausfuehrbaren Code, sind die Tests Validierungen der Markdown-Dateien auf strukturelle Korrektheit und Vollstaendigkeit.

<test_spec>
```python
# tests/acceptance/test_slice_03_orchestrator_pipeline.py
"""
Acceptance Tests fuer Slice 03: Orchestrator Pipeline.

Validiert dass orchestrate.md und slice-implementer.md
korrekt umgebaut/angepasst wurden.
"""
import pytest
from pathlib import Path
import re
import json

ORCHESTRATE_FILE = Path(".claude/commands/orchestrate.md")
IMPLEMENTER_FILE = Path(".claude/agents/slice-implementer.md")


@pytest.fixture
def orchestrate_content():
    """Liest den Orchestrator-Command-Inhalt."""
    assert ORCHESTRATE_FILE.exists(), f"Orchestrator-Datei {ORCHESTRATE_FILE} existiert nicht"
    return ORCHESTRATE_FILE.read_text(encoding="utf-8")


@pytest.fixture
def implementer_content():
    """Liest den Slice-Implementer Agent-Inhalt."""
    assert IMPLEMENTER_FILE.exists(), f"Implementer-Datei {IMPLEMENTER_FILE} existiert nicht"
    return IMPLEMENTER_FILE.read_text(encoding="utf-8")


class TestPreImplSanityCheck:
    """AC-1: Pre-Impl Sanity Check prueft Compliance-Files."""

    @pytest.mark.acceptance
    def test_ac_1_pre_impl_sanity_check(self, orchestrate_content):
        """AC-1: GIVEN Orchestrator startet WHEN Pre-Impl Check THEN prueft compliance-slice-*.md und APPROVED."""
        content_lower = orchestrate_content.lower()
        assert "compliance" in content_lower, \
            "Orchestrator muss Compliance-Files pruefen"
        assert "approved" in content_lower, \
            "Orchestrator muss auf APPROVED-Status pruefen"
        assert "hard stop" in content_lower or "hard_stop" in content_lower, \
            "Orchestrator muss HARD STOP bei fehlenden Compliance-Files definieren"
        assert "planner" in content_lower, \
            "Orchestrator muss auf Planner-Ausfuehrung hinweisen bei fehlendem Check"


class TestImplementerNoTests:
    """AC-2: Implementer-Prompt enthaelt keine Test-Anweisung."""

    @pytest.mark.acceptance
    def test_ac_2_implementer_prompt_no_tests(self, orchestrate_content):
        """AC-2: GIVEN Orchestrator ruft Implementer auf WHEN Prompt gebaut THEN keine Test-Anweisung."""
        # Suche den Implementer Task-Prompt im Orchestrator
        assert "task(slice-implementer)" in orchestrate_content.lower() or \
               "task(implementer)" in orchestrate_content.lower() or \
               "subagent_type" in orchestrate_content.lower(), \
            "Orchestrator muss Task(slice-implementer) aufrufen"
        # Die alte Regel "Schreibe Tests wie in der Spec definiert" darf NICHT mehr im Implementer-Prompt stehen
        # Pruefung erfolgt in implementer_content (AC-11)


class TestTestWriterInvocation:
    """AC-3: Orchestrator ruft Test-Writer mit korrekten Inputs auf."""

    @pytest.mark.acceptance
    def test_ac_3_test_writer_invocation(self, orchestrate_content):
        """AC-3: GIVEN Implementer fertig WHEN Test-Writer aufgerufen THEN mit files_changed und ACs."""
        content_lower = orchestrate_content.lower()
        assert "test-writer" in content_lower or "test_writer" in content_lower, \
            "Orchestrator muss Task(test-writer) aufrufen"
        assert "files_changed" in orchestrate_content, \
            "Orchestrator muss files_changed an Test-Writer weitergeben"
        assert "acceptance criteria" in content_lower or "ac" in content_lower or "given" in content_lower, \
            "Orchestrator muss ACs/Spec an Test-Writer weitergeben"


class TestTestValidatorInvocation:
    """AC-4: Orchestrator ruft Test-Validator mit korrekten Inputs auf."""

    @pytest.mark.acceptance
    def test_ac_4_test_validator_invocation(self, orchestrate_content):
        """AC-4: GIVEN Test-Writer fertig WHEN Validation THEN Task(test-validator) mit mode slice_validation."""
        content_lower = orchestrate_content.lower()
        assert "test-validator" in content_lower or "test_validator" in content_lower, \
            "Orchestrator muss Task(test-validator) aufrufen"
        assert "slice_validation" in orchestrate_content, \
            "Orchestrator muss mode: slice_validation an Test-Validator geben"


class TestRetryLoopWith3Retries:
    """AC-5, AC-6: Retry-Loop mit Debugger und max 3 Retries."""

    @pytest.mark.acceptance
    def test_ac_5_debugger_on_failure(self, orchestrate_content):
        """AC-5: GIVEN Validation failed, retries < 3 WHEN Retry THEN Task(debugger) aufgerufen."""
        content_lower = orchestrate_content.lower()
        assert "debugger" in content_lower, \
            "Orchestrator muss Task(debugger) bei Failure aufrufen"
        assert "failed_stage" in orchestrate_content or "failed stage" in content_lower, \
            "Orchestrator muss failed_stage an Debugger weitergeben"

    @pytest.mark.acceptance
    def test_ac_6_max_3_retries(self, orchestrate_content):
        """AC-6: GIVEN 3 Retries erschoepft WHEN immer noch failed THEN HARD STOP mit Evidence."""
        assert "3" in orchestrate_content, \
            "Orchestrator muss 3 als Max-Retry-Limit definieren"
        # Pruefe dass es NICHT mehr 2 als Max ist (alter Wert)
        # Suche nach MAX_RETRIES = 3 oder aehnlich
        assert re.search(r'(?:max_retries|MAX_RETRIES|max.*retries).*3', orchestrate_content, re.IGNORECASE), \
            "Orchestrator muss MAX_RETRIES = 3 definieren (nicht 2)"


class TestFinalValidationViaSubAgent:
    """AC-7: Final Validation via Task(test-validator), kein direktes Bash."""

    @pytest.mark.acceptance
    def test_ac_7_final_validation_via_agent(self, orchestrate_content):
        """AC-7: GIVEN alle Slices fertig WHEN Final Validation THEN Task(test-validator) mit final_validation."""
        assert "final_validation" in orchestrate_content, \
            "Orchestrator muss mode: final_validation an Test-Validator geben"
        # Pruefe dass KEIN direktes Bash("pnpm lint") oder Bash("pnpm tsc") mehr existiert
        assert 'Bash("pnpm lint")' not in orchestrate_content and \
               'Bash("pnpm tsc' not in orchestrate_content and \
               'Bash("pnpm build")' not in orchestrate_content, \
            "Orchestrator darf KEINE direkten Bash-Commands fuer Lint/Type/Build ausfuehren"


class TestJSONParsing:
    """AC-8: JSON-Parsing des letzten ```json``` Blocks."""

    @pytest.mark.acceptance
    def test_ac_8_json_parsing_logic(self, orchestrate_content):
        """AC-8: GIVEN Agent Output WHEN Parsing THEN letzter json Block extrahiert, bei Failure HARD STOP."""
        content_lower = orchestrate_content.lower()
        assert "json" in content_lower, \
            "Orchestrator muss JSON-Parsing beschreiben"
        assert "parse" in content_lower, \
            "Orchestrator muss JSON-Parse-Logik beschreiben"
        assert "hard stop" in content_lower or "hard_stop" in content_lower, \
            "Orchestrator muss HARD STOP bei Parse-Failure definieren"


class TestACCoverageCheck:
    """AC-9: AC-Coverage < 100% fuehrt zu HARD STOP."""

    @pytest.mark.acceptance
    def test_ac_9_ac_coverage_hard_stop(self, orchestrate_content):
        """AC-9: GIVEN ac_coverage.total != covered WHEN Orchestrator verarbeitet THEN HARD STOP."""
        assert "ac_coverage" in orchestrate_content, \
            "Orchestrator muss ac_coverage pruefen"
        assert "missing" in orchestrate_content, \
            "Orchestrator muss fehlende ACs (missing) in Fehlermeldung ausgeben"


class TestEvidenceFormat:
    """AC-10: Evidence enthaelt implementation, tests, validation, retries."""

    @pytest.mark.acceptance
    def test_ac_10_evidence_format(self, orchestrate_content):
        """AC-10: GIVEN Slice validiert WHEN Evidence gespeichert THEN implementation + tests + validation + retries."""
        assert "implementation" in orchestrate_content, \
            "Evidence muss implementation Sektion enthalten"
        assert "tests" in orchestrate_content, \
            "Evidence muss tests Sektion enthalten"
        assert "validation" in orchestrate_content, \
            "Evidence muss validation Sektion enthalten"
        assert "retries" in orchestrate_content, \
            "Evidence muss retries Feld enthalten"
        # Pruefe auf erweiterte Felder
        assert "test_count" in orchestrate_content or "test_files" in orchestrate_content, \
            "Evidence muss test_count oder test_files aus Test-Writer enthalten"
        assert "ac_coverage" in orchestrate_content, \
            "Evidence muss ac_coverage aus Test-Writer enthalten"
        assert "stages" in orchestrate_content, \
            "Evidence muss stages aus Test-Validator enthalten"


class TestImplementerNoTestsRule:
    """AC-11: Slice-Implementer hat keine Tests-Regel mehr."""

    @pytest.mark.acceptance
    def test_ac_11_implementer_no_tests_rule(self, implementer_content):
        """AC-11: GIVEN Implementer Agent WHEN Definition gelesen THEN keine 'Tests schreiben' Regel."""
        # Die alten Regeln duerfen NICHT mehr enthalten sein
        assert "Tests schreiben" not in implementer_content or \
               "KEINE Tests" in implementer_content, \
            "Implementer darf keine Regel 'Tests schreiben' mehr haben (nur 'KEINE Tests')"
        assert "Schreibe Tests" not in implementer_content or \
               "KEINE Tests" in implementer_content, \
            "Implementer darf keinen Workflow-Schritt 'Schreibe Tests' mehr haben"
        # Die neue Regel MUSS enthalten sein
        content_lower = implementer_content.lower()
        assert "nur code" in content_lower or "keine tests" in content_lower, \
            "Implementer muss klarstellen: NUR Code, KEINE Tests"


class TestImplementerJSONContract:
    """AC-12: Implementer JSON Output hat commit_hash statt commit_message."""

    @pytest.mark.acceptance
    def test_ac_12_implementer_json_contract(self, implementer_content):
        """AC-12: GIVEN Implementer Output THEN JSON hat status, files_changed, commit_hash, notes."""
        json_blocks = re.findall(r'```json\s*\n(.*?)```', implementer_content, re.DOTALL)
        assert len(json_blocks) > 0, "Implementer muss JSON Output Contract enthalten"

        contract_found = False
        for block in json_blocks:
            try:
                parsed = json.loads(block.strip())
                if "status" in parsed and "files_changed" in parsed:
                    contract_found = True
                    assert "commit_hash" in parsed, \
                        "JSON Contract muss commit_hash enthalten (nicht commit_message)"
                    break
            except json.JSONDecodeError:
                continue

        assert contract_found, "Implementer muss JSON Output Contract mit status und files_changed enthalten"


class TestNoDirectBash:
    """AC-13: Orchestrator fuehrt keine direkten Bash-Commands fuer Tests/Lint/Build aus."""

    @pytest.mark.acceptance
    def test_ac_13_no_direct_bash(self, orchestrate_content):
        """AC-13: GIVEN Orchestrator WHEN Pipeline laeuft THEN kein direktes Bash fuer Tests/Lint/Build."""
        # Pruefe dass alte direkte Bash-Aufrufe nicht mehr existieren
        assert 'Bash(slice_config.test_command' not in orchestrate_content, \
            "Orchestrator darf Tests nicht direkt via Bash ausfuehren"
        assert 'Bash("pnpm lint")' not in orchestrate_content, \
            "Orchestrator darf Lint nicht direkt via Bash ausfuehren"
        assert 'Bash("pnpm tsc' not in orchestrate_content, \
            "Orchestrator darf Type-Check nicht direkt via Bash ausfuehren"
        assert 'Bash("pnpm build")' not in orchestrate_content, \
            "Orchestrator darf Build nicht direkt via Bash ausfuehren"
```
</test_spec>

---

## Code Examples (MANDATORY - GATE 2 PFLICHT)

> **KRITISCH:** Alle Code-Beispiele in diesem Dokument sind **PFLICHT-Deliverables**.
> Der Gate 2 Compliance Agent prueft, dass jedes Code-Beispiel implementiert wird.
> Abweichung nur mit expliziter Begruendung im Commit erlaubt.

| Code Example | Section | Mandatory | Notes |
|--------------|---------|-----------|-------|
| Orchestrate.md Komplett-Ersetzung | Technische Umsetzung 3 | YES | Neue Orchestrator-Command mit 4 Sub-Agent-Steps |
| Slice-Implementer JSON Output Contract | Technische Umsetzung 6 | YES | Neues JSON-Format mit commit_hash statt commit_message |
| Evidence-Format (erweitert) | Technische Umsetzung 8 | YES | JSON mit implementation + tests + validation + retries |
| State-Machine Transitions | Technische Umsetzung 7 | YES | Tabelle mit allen State-Transitions |
| JSON-Parsing Logik | Technische Umsetzung 4 | YES | Pattern fuer letzten json Block extrahieren |
| HARD STOP Conditions | Technische Umsetzung 9 | YES | Tabelle mit allen HARD STOP Szenarien |

### Orchestrate.md: Vollstaendige Command-Definition

Der Implementer MUSS die bestehende `orchestrate.md` komplett ersetzen mit folgender Struktur:

```markdown
---
description: "Feature-Orchestrator mit Sub-Agent Pipeline. Implementiert Features wave-by-wave mit 4 Sub-Agent-Steps (Implementer -> Test-Writer -> Test-Validator -> Debugger), JSON-Parsing, 3 Retries und stack-agnostischer Final Validation."
---

# Orchestrate Feature Implementation

Du orchestrierst die Implementierung eines Features slice-by-slice mit Sub-Agent Pipeline.

**KRITISCHE REGELN (KEINE Ausnahmen):**
1. **Autonomer Betrieb:** Frage NIEMALS zwischen Waves oder Slices nach Bestaetigung.
2. **Exit Code ist Wahrheit:** exit_code != 0 = FEHLGESCHLAGEN. Immer.
3. **Kein direktes Bash:** Du fuehrst KEINE Tests, Lint, Type-Check oder Build direkt aus. ALLES via Sub-Agents.
4. **JSON-Parsing:** Jeder Sub-Agent-Output wird als JSON geparsed (letzter ```json``` Block). Bei Parse-Failure: HARD STOP.
5. **3 Retries:** Max 3 Debugger-Retries pro Slice. Danach HARD STOP.

**Input:** $ARGUMENTS (Spec-Pfad)

---

## Phase 1: Input-Validierung & Pre-Impl Sanity Check

1. Pruefe ob $ARGUMENTS einen Spec-Pfad enthaelt
2. Falls kein Argument: Suche neuestes specs/*/orchestrator-config.md

3. Validiere Required Outputs:
   REQUIRED:
   - {spec_path}/orchestrator-config.md
   - {spec_path}/slices/slice-*.md
   - {spec_path}/slices/compliance-slice-*.md (MUSS "APPROVED" enthalten)

   IF ANY REQUIRED MISSING OR NOT APPROVED:
     HARD STOP: "Planner muss zuerst laufen."

4. Parse orchestrator-config.md

---

## Phase 2: Setup & State Management

[State-File mit erweiterten Feldern: current_state, retry_count, failed_stage]
[Resume-Support wie bisher]

---

## Helper: JSON-Parsing

FUNCTION parse_agent_json(agent_output):
  # Finde den LETZTEN ```json``` Block
  json_blocks = regex_find_all(agent_output, /```json\s*\n(.*?)```/s)
  IF json_blocks.length == 0:
    HARD STOP: "Agent hat keinen JSON-Output geliefert"
  last_json = json_blocks[-1]
  TRY:
    parsed = JSON.parse(last_json)
    RETURN parsed
  CATCH:
    HARD STOP: "JSON Parse Failure"

---

## Phase 3: Wave-Based Implementation

FOR each wave IN waves:
  FOR each slice_id IN wave.slices:

    # ── Step 1: Task(slice-implementer) → Code ──
    state.current_state = "implementing"
    Write(STATE_FILE, state)

    impl_result = Task(
      subagent_type: "slice-implementer",
      prompt: "
        Implementiere {slice_id}.
        Slice-Spec: {spec_file}
        Architecture: {architecture_file}
        Integration-Map: {integration_map_file}

        REGELN:
        1. Lies die Slice-Spec vollstaendig
        2. Implementiere NUR was dort steht
        3. Du schreibst NUR Code, KEINE Tests. Der Test-Writer Agent uebernimmt Tests.
        4. Committe mit: git add -A && git commit -m 'feat({slice_id}): ...'
      "
    )

    impl_json = parse_agent_json(impl_result)
    IF impl_json.status == "failed":
      HARD STOP: "Implementer failed: {impl_json.notes}"

    # ── Step 2: Task(test-writer) → Tests ──
    state.current_state = "writing_tests"
    Write(STATE_FILE, state)

    test_writer_result = Task(
      subagent_type: "test-writer",
      prompt: "
        Schreibe Tests fuer {slice_id}.
        Slice-Spec (ACs): {spec_file}
        Geaenderte Dateien: {impl_json.files_changed}
        Schreibe Tests gegen die Spec-ACs, nicht gegen den Code.
      "
    )

    tw_json = parse_agent_json(test_writer_result)
    IF tw_json.status == "failed":
      HARD STOP: "Test-Writer failed: Spec-Problem"
    IF tw_json.ac_coverage.total != tw_json.ac_coverage.covered:
      HARD STOP: "AC-Coverage nicht 100%. Fehlend: {tw_json.ac_coverage.missing}"

    # ── Step 3: Task(test-validator) → Validate ──
    state.current_state = "validating"
    state.retry_count = 0
    Write(STATE_FILE, state)

    validator_result = Task(
      subagent_type: "test-validator",
      prompt: "
        Validiere {slice_id}.
        Mode: slice_validation
        Test-Paths: {tw_json.test_files}
        Previous-Slice-Tests: {get_previous_test_paths(completed_slices)}
        Working-Directory: {working_dir}
      "
    )

    val_json = parse_agent_json(validator_result)

    # ── Step 4: Retry Loop (max 3x) ──
    MAX_RETRIES = 3
    WHILE val_json.overall_status == "failed" AND state.retry_count < MAX_RETRIES:
      state.retry_count += 1
      state.current_state = "auto_fixing"
      state.failed_stage = val_json.failed_stage
      Write(STATE_FILE, state)

      fix_result = Task(
        subagent_type: "debugger",
        prompt: "
          Tests fuer {slice_id} sind fehlgeschlagen.
          Failed Stage: {val_json.failed_stage}
          Error Output: {val_json.error_output}
          Slice-Spec: {spec_file}
          Geaenderte Dateien: {impl_json.files_changed}
          Fixe den Code (NICHT die Tests aufweichen!).
        "
      )

      fix_json = parse_agent_json(fix_result)
      IF fix_json.status == "unable_to_fix":
        HARD STOP: "Debugger unable to fix: {fix_json.root_cause}"

      # Re-validate
      state.current_state = "validating"
      Write(STATE_FILE, state)

      validator_result = Task(
        subagent_type: "test-validator",
        prompt: "
          Re-Validiere {slice_id} nach Fix.
          Mode: slice_validation
          Test-Paths: {tw_json.test_files}
          Previous-Slice-Tests: {get_previous_test_paths(completed_slices)}
          Working-Directory: {working_dir}
        "
      )
      val_json = parse_agent_json(validator_result)

    IF val_json.overall_status == "failed":
      HARD STOP: "3 Retries erschoepft fuer {slice_id}"

    # ── Evidence speichern ──
    state.current_state = "slice_complete"
    evidence = {
      "feature": feature_name,
      "slice": slice_id,
      "timestamp": ISO_TIMESTAMP,
      "status": "completed",
      "implementation": impl_json,
      "tests": tw_json,
      "validation": val_json,
      "retries": state.retry_count
    }
    Write("{EVIDENCE_DIR}/{slice_id}.json", evidence)

---

## Phase 4: Final Validation

state.current_state = "final_validation"
Write(STATE_FILE, state)

final_result = Task(
  subagent_type: "test-validator",
  prompt: "
    Final Validation fuer Feature {feature_name}.
    Mode: final_validation
    Previous-Slice-Tests: {get_all_test_paths(completed_slices)}
    Working-Directory: {working_dir}
  "
)

final_json = parse_agent_json(final_result)

# Retry bei Failure (max 3x)
final_retry = 0
WHILE final_json.overall_status == "failed" AND final_retry < MAX_RETRIES:
  final_retry += 1
  fix_result = Task(subagent_type: "debugger", ...)
  fix_json = parse_agent_json(fix_result)
  IF fix_json.status == "unable_to_fix": HARD STOP
  final_result = Task(subagent_type: "test-validator", mode: final_validation, ...)
  final_json = parse_agent_json(final_result)

IF final_json.overall_status == "failed":
  HARD STOP: "Final Validation fehlgeschlagen nach 3 Retries"

---

## Phase 5: Completion

state.current_state = "feature_complete"
[Feature Evidence, Branch Info, Naechste Schritte]
```

### Slice-Implementer: Angepasste Agent-Definition

Der Implementer MUSS die bestehende `slice-implementer.md` so modifizieren:

**Entfernte Regeln:**
- Regeln-Tabelle: "Tests schreiben -- Wie in der Spec definiert" -> ENTFERNT
- Workflow Schritt 6: "Schreibe Tests (falls in Spec)" -> ENTFERNT
- Erlaubt-Section: "Tests schreiben (aber nicht ausfuehren)" -> ENTFERNT
- Tests-Section unter Implementierungs-Guidelines -> ENTFERNT

**Neue Regel (in Regeln-Tabelle):**
```markdown
| **NUR Code, KEINE Tests** | Du schreibst NUR Code, KEINE Tests. Der Test-Writer Agent uebernimmt Tests. |
```

**Neuer JSON Output Contract:**
```json
{
  "status": "completed",
  "files_changed": ["pfad/zu/datei1.py", "pfad/zu/datei2.py"],
  "commit_hash": "abc123def456",
  "notes": "Optional: Hinweise fuer den Orchestrator"
}
```

---

## Deliverables (SCOPE SAFEGUARD)

<!-- DELIVERABLES_START -->
### Command-Definition
- [ ] `.claude/commands/orchestrate.md` -- Komplett-Ersetzung: 4 Sub-Agent-Steps (Implementer -> Test-Writer -> Test-Validator -> Debugger), Pre-Impl Sanity Check, JSON-Parsing, 3 Retries, Re-Run ab fehlgeschlagenem Stage, stack-agnostische Final Validation, erweitertes Evidence-Format, State-Machine mit neuen States

### Agent-Definition
- [ ] `.claude/agents/slice-implementer.md` -- Modification: "Tests schreiben" Regeln entfernen, neue Regel "NUR Code, KEINE Tests", JSON Output Contract anpassen (commit_hash statt commit_message), Tests-Section unter Implementierungs-Guidelines entfernen

### Tests
- [ ] `tests/acceptance/test_slice_03_orchestrator_pipeline.py` -- Acceptance Tests die pruefen ob orchestrate.md und slice-implementer.md korrekt umgebaut/angepasst wurden
<!-- DELIVERABLES_END -->

---

## Definition of Done

- [x] Akzeptanzkriterien sind eindeutig und vollstaendig (13 ACs im GIVEN/WHEN/THEN Format)
- [x] 4 Sub-Agent-Steps definiert (Implementer, Test-Writer, Test-Validator, Debugger)
- [x] Pre-Impl Sanity Check definiert (Compliance-Files + APPROVED)
- [x] JSON-Parsing-Logik dokumentiert (letzter ```json``` Block)
- [x] 3 Retries definiert (statt 2)
- [x] Re-Run ab fehlgeschlagenem Stage dokumentiert
- [x] Evidence-Format erweitert (implementation + tests + validation + retries)
- [x] Final Validation stack-agnostisch (via Test-Validator, kein direktes Bash)
- [x] State-Machine-Transitions dokumentiert (aus architecture.md)
- [x] Slice-Implementer Anpassungen dokumentiert (Tests entfernen, JSON Contract)
- [x] "No Direct Bash" Rule enforced
- [ ] Rollout: orchestrate.md ersetzt, slice-implementer.md modifiziert

---

## Links

- Bestehender Orchestrator: `.claude/commands/orchestrate.md`
- Bestehender Implementer: `.claude/agents/slice-implementer.md`
- Architecture: `specs/2026-02-14-orchestrator-robust-testing/architecture.md`
- Discovery: `specs/2026-02-14-orchestrator-robust-testing/discovery.md`
- Slice 1 (Test-Writer): `specs/2026-02-14-orchestrator-robust-testing/slices/slice-01-test-writer-enhancement.md`
- Slice 2 (Test-Validator): `specs/2026-02-14-orchestrator-robust-testing/slices/slice-02-test-validator-agent.md`
- Evidence-Format Referenz: `.claude/evidence/backend-kern/slice-01.json`

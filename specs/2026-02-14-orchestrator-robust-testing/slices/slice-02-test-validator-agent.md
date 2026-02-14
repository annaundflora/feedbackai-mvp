# Slice 2: Test-Validator Agent erstellen

> **Slice 2 von 4** fuer `Lean Testing Pipeline`
>
> | Navigation | |
> |------------|---|
> | **Vorheriger:** | `slice-01-test-writer-enhancement.md` |
> | **Naechster:** | `slice-03-orchestrator-pipeline.md` |

---

## Metadata (fuer Orchestrator)

| Key | Value |
|-----|-------|
| **ID** | `slice-02-test-validator-agent` |
| **Test** | `cd backend && python -m pytest tests/acceptance/test_slice_02_test_validator_agent.py -v` |
| **E2E** | `false` |
| **Dependencies** | `["slice-01-test-writer-enhancement"]` |

---

## Slice-Uebersicht

| # | Slice | Status | Datei |
|---|-------|--------|-------|
| 1 | Test-Writer Agent Enhancement | Ready | `slice-01-test-writer-enhancement.md` |
| 2 | Test-Validator Agent | Ready | `slice-02-test-validator-agent.md` |
| 3 | Orchestrator Pipeline | Pending | `slice-03-orchestrator-pipeline.md` |
| 4 | Planner & Gate Improvements | Pending | `slice-04-planner-gates.md` |

---

## Kontext & Ziel

Der Orchestrator fuehrt aktuell Tests direkt via Bash-Commands aus (Rule 4 Verstoss). Das fuehrt zu Context Pollution ueber lange Sessions. Es gibt keinen Smoke Test (App starten + Health-Check), keine Regression Detection (vorherige Slice-Tests re-run), und kein strukturiertes Evidence-Format.

Dieser Slice erstellt einen **neuen Agent** (`.claude/agents/test-validator.md`) der:

1. **ALLE Tests ausfuehrt** -- Unit, Integration, Acceptance (in dieser Reihenfolge)
2. **Smoke Test** -- App starten, Health-Check ausfuehren, App stoppen (30s Timeout)
3. **Regression Run** -- ALLE vorherigen Slice-Tests re-run
4. **Auto-Fix Lint** -- `ruff --fix` / `eslint --fix` vor dem Lint-Check
5. **Strukturierten JSON-Output** liefert -- Stages mit exit_code, duration_ms, summary
6. **Stack-agnostisch** arbeitet -- erkennt Framework, generiert Commands automatisch

---

## Technische Umsetzung

### Architektur-Kontext (aus architecture.md)

> **Quelle:** `architecture.md` -> Agent Definitions (Test-Validator), Test-Validator Output Contract, Stack-Detection Matrix, Orchestrator Pipeline Flow

```
Orchestrator
  |
  v
Task(test-validator)
  Input: Test-Commands, Start-Command, Health-Endpoint, Previous Slice Test-Paths
  |
  v
  Stage 1: Unit Tests       -> exit_code, duration_ms, summary
  Stage 2: Integration Tests -> exit_code, duration_ms, summary
  Stage 3: Acceptance Tests  -> exit_code, duration_ms, summary
  Stage 4: Smoke Test        -> app_started, health_status, startup_duration_ms
  Stage 5: Regression        -> exit_code, slices_tested
  |
  v
Output: { overall_status, stages, failed_stage?, error_output? }
```

### 1. Architektur-Impact

| Layer | Aenderungen |
|-------|------------|
| `.claude/agents/test-validator.md` | Neue Agent-Definition (Greenfield) |

### 2. Datenfluss

```
Orchestrator Input (Prompt mit allen Parametern)
  |
  v
[Stack-Detection] -- pyproject.toml/package.json/go.mod lesen -> Framework bestimmen
  |
  v
[Stage 1: Unit Tests] -- Bash: `python -m pytest tests/unit/ -v` (oder Stack-aequivalent)
  |-- exit_code, duration_ms, summary
  |-- Bei exit_code != 0: Abbruch, failed_stage = "unit", error_output = stderr
  |
  v
[Stage 2: Integration Tests] -- Bash: `python -m pytest tests/integration/ -v`
  |-- exit_code, duration_ms, summary
  |-- Bei exit_code != 0: Abbruch, failed_stage = "integration", error_output = stderr
  |
  v
[Stage 3: Acceptance Tests] -- Bash: `python -m pytest tests/acceptance/ -v`
  |-- exit_code, duration_ms, summary
  |-- Bei exit_code != 0: Abbruch, failed_stage = "acceptance", error_output = stderr
  |
  v
[Stage 4: Smoke Test]
  |-- App starten: `uvicorn app.main:app --host 0.0.0.0 --port 8000 &`
  |-- Warte bis Health-Endpoint antwortet (max 30s Polling, 1s Interval)
  |-- Health-Check: `curl http://localhost:8000/health`
  |-- App stoppen: PID kill
  |-- Bei Timeout oder health_status != 200: Abbruch, failed_stage = "smoke"
  |
  v
[Stage 5: Regression] -- Alle vorherigen Slice-Tests re-run
  |-- Bash: `python -m pytest {previous_test_path_1} {previous_test_path_2} ... -v`
  |-- exit_code, slices_tested
  |-- Bei exit_code != 0: Abbruch, failed_stage = "regression"
  |
  v
[Auto-Fix Lint] (nur bei Final Validation)
  |-- `ruff check --fix .` (Python) oder `pnpm eslint --fix .` (TypeScript)
  |-- Dann: `ruff check .` (blocking)
  |
  v
[JSON Output] -- Letzter ```json``` Block
```

### 3. Agent-Definition: Sections

#### 3.1 Agent-Rolle und Scope

Der Agent:
- Fuehrt ALLE Test-Stages sequenziell aus
- Nutzt Bash-Tool fuer Command-Execution
- Fuehrt KEINEN Code-Fix durch (das ist Aufgabe des Debuggers)
- Ist read-only gegenueber der Codebase (Ausnahme: Auto-Fix Lint)
- Liefert strukturierten JSON-Output

#### 3.2 Stack-Detection

Identisch mit Slice 1 (Test-Writer), nutzt gleiche Detection-Matrix:

| Indicator File | Stack | Test Framework | Test Command | Start Command | Health Endpoint |
|----------------|-------|---------------|-------------|---------------|-----------------|
| `pyproject.toml` + fastapi dep | Python/FastAPI | pytest | `python -m pytest {path} -v` | `uvicorn app.main:app --host 0.0.0.0 --port 8000` | `http://localhost:8000/health` |
| `requirements.txt` + fastapi | Python/FastAPI | pytest | `python -m pytest {path} -v` | `uvicorn app.main:app --host 0.0.0.0 --port 8000` | `http://localhost:8000/health` |
| `package.json` + next dep | TypeScript/Next.js | vitest + playwright | `pnpm test {path}` | `pnpm dev` | `http://localhost:3000/api/health` |
| `package.json` + express dep | TypeScript/Express | vitest | `pnpm test {path}` | `node server.js` | `http://localhost:3000/health` |
| `go.mod` | Go | go test | `go test {path}` | `go run .` | `http://localhost:8080/health` |

#### 3.3 Test-Execution-Stages (Sequenziell)

**Reihenfolge ist PFLICHT.** Bei Stage-Failure: Abbruch + Rueckgabe des fehlgeschlagenen Stages.

| Stage | Command Pattern (Python) | Success Criteria | Output Fields |
|-------|-------------------------|-----------------|---------------|
| 1. Unit | `python -m pytest tests/unit/ -v` | exit_code == 0 | exit_code, duration_ms, summary |
| 2. Integration | `python -m pytest tests/integration/ -v` | exit_code == 0 | exit_code, duration_ms, summary |
| 3. Acceptance | `python -m pytest tests/acceptance/ -v` | exit_code == 0 | exit_code, duration_ms, summary |
| 4. Smoke | App starten + Health-Check | health_status == 200 innerhalb 30s | app_started, health_status, startup_duration_ms |
| 5. Regression | `python -m pytest {all_previous_test_paths} -v` | exit_code == 0 | exit_code, slices_tested |

#### 3.4 Smoke Test Details

```
1. Stack-Detection: Start-Command und Health-Endpoint bestimmen
2. App starten im Hintergrund:
   - Python: `uvicorn app.main:app --host 0.0.0.0 --port 8000 &`
   - TypeScript: `pnpm dev &` oder `node server.js &`
   - PID merken fuer spaeteres Kill
3. Health-Polling:
   - Alle 1 Sekunde: `curl -s -o /dev/null -w "%{http_code}" {health_endpoint}`
   - Timeout: 30 Sekunden
   - Erfolg: HTTP 200
4. App stoppen:
   - `kill {PID}` (SIGTERM)
   - Warte 5s, dann `kill -9 {PID}` (SIGKILL) falls noch laufend
5. Output:
   - app_started: true/false (konnte der Prozess gestartet werden?)
   - health_status: HTTP Status Code (200 = ok, 0 = keine Antwort)
   - startup_duration_ms: Zeit von Start bis erste 200-Antwort
```

**KRITISCH:** Health-Endpoint MUSS ohne externe Services funktionieren. Das bestehende `GET /health` Endpoint in `backend/app/main.py` returniert `{"status": "ok"}` ohne DB-Check -- das ist korrekt.

#### 3.5 Regression Run Details

```
1. Orchestrator liefert Liste der vorherigen Slice-Test-Pfade im Prompt
   Beispiel: ["tests/slices/backend-kern/test_slice_01_*.py", "tests/slices/backend-kern/test_slice_02_*.py"]
2. Agent fuehrt ALLE Tests zusammen aus:
   `python -m pytest tests/slices/backend-kern/test_slice_01_*.py tests/slices/backend-kern/test_slice_02_*.py -v`
3. Output:
   - exit_code: 0 = alle bestanden, != 0 = Regression
   - slices_tested: ["slice-01", "slice-02"] (aus den Pfaden abgeleitet)
4. Falls keine vorherigen Slices existieren (erster Slice):
   - exit_code: 0
   - slices_tested: []
   - summary: "No previous slices to test"
```

#### 3.6 Auto-Fix Lint (nur bei Final Validation)

```
1. Agent erkennt Stack (Python: ruff, TypeScript: eslint)
2. Auto-Fix:
   - Python: `ruff check --fix .`
   - TypeScript: `pnpm eslint --fix .`
3. Lint-Check (blocking):
   - Python: `ruff check .`
   - TypeScript: `pnpm lint`
4. Bei exit_code != 0 nach Auto-Fix: Failure (Debugger muss fixen)
```

**WICHTIG:** Auto-Fix Lint laeuft nur bei Final Validation (Orchestrator gibt `mode: final_validation` mit). Bei normaler Slice-Validation wird Lint NICHT ausgefuehrt.

#### 3.7 JSON Output Contract

Der letzte Code-Block im Agent-Output MUSS dieses Format haben:

```json
{
  "overall_status": "passed",
  "stages": {
    "unit": {
      "exit_code": 0,
      "duration_ms": 1200,
      "summary": "12 passed, 0 failed"
    },
    "integration": {
      "exit_code": 0,
      "duration_ms": 3400,
      "summary": "5 passed, 0 failed"
    },
    "acceptance": {
      "exit_code": 0,
      "duration_ms": 2100,
      "summary": "3 passed, 0 failed"
    },
    "smoke": {
      "app_started": true,
      "health_status": 200,
      "startup_duration_ms": 4500
    },
    "regression": {
      "exit_code": 0,
      "slices_tested": ["slice-01", "slice-02"]
    }
  }
}
```

Bei Failure:

```json
{
  "overall_status": "failed",
  "stages": {
    "unit": {
      "exit_code": 0,
      "duration_ms": 1200,
      "summary": "12 passed, 0 failed"
    },
    "integration": {
      "exit_code": 1,
      "duration_ms": 2800,
      "summary": "3 passed, 2 failed"
    },
    "acceptance": {
      "exit_code": -1,
      "duration_ms": 0,
      "summary": "skipped (previous stage failed)"
    },
    "smoke": {
      "app_started": false,
      "health_status": 0,
      "startup_duration_ms": 0
    },
    "regression": {
      "exit_code": -1,
      "slices_tested": []
    }
  },
  "failed_stage": "integration",
  "error_output": "FAILED tests/integration/test_auth_api.py::test_login - AssertionError: expected 200 got 401"
}
```

#### 3.8 Stage-Skip-Semantik

Wenn ein Stage fehlschlaegt, werden ALLE nachfolgenden Stages uebersprungen:
- `exit_code`: -1 (nicht ausgefuehrt)
- `duration_ms`: 0
- `summary`: "skipped (previous stage failed)"
- Smoke: `app_started: false`, `health_status: 0`, `startup_duration_ms: 0`
- Regression: `slices_tested: []`

#### 3.9 Test-Verzeichnis-Fallback

Falls ein Test-Verzeichnis nicht existiert (z.B. `tests/unit/` ist leer oder fehlt):
- Stage wird als "passed" gewertet mit `exit_code: 0`
- `summary`: "no tests found (directory does not exist)"
- `duration_ms`: 0
- Pipeline laeuft weiter mit naechstem Stage

### 4. Final Validation Mode

Bei Final Validation (`mode: final_validation` im Prompt) fuehrt der Agent zusaetzlich aus:

| Step | Command (Python) | Command (TypeScript) | Blocking |
|------|-----------------|---------------------|----------|
| Auto-Fix Lint | `ruff check --fix .` | `pnpm eslint --fix .` | Pre-Step |
| Lint Check | `ruff check .` | `pnpm lint` | Ja |
| Type Check | `mypy .` (falls konfiguriert) | `pnpm tsc --noEmit` | Ja |
| Build | `pip install -e .` (falls setup.py) | `pnpm build` | Ja |
| Full Smoke | Start App + Health Check | Start App + Health Check | Ja |
| Full Regression | ALLE Slice-Tests re-run | ALLE Slice-Tests re-run | Ja |

---

## Constraints & Hinweise

**Betrifft:**
- Ausschliesslich `.claude/agents/test-validator.md` -- eine einzige neue Markdown-Datei

**Agent Execution Rules:**
- Exit Code ist Wahrheit: `exit_code == 0` = BESTANDEN (Rule 6)
- Agent fuehrt KEINE Code-Fixes durch -- das ist Aufgabe des Debuggers
- Agent ist read-only gegenueber der Codebase (Ausnahme: Auto-Fix Lint bei Final Validation)
- Alle Commands via Bash-Tool ausfuehren (Rule 4)
- Sub-Agent Output ist JSON im letzten Code-Block (Rule 18)

**Abgrenzung:**
- Dieser Slice aendert KEINE anderen Agents (test-writer, slice-implementer, orchestrate, debugger)
- Dieser Slice aendert NICHT den Orchestrator -- das ist Aufgabe von Slice 3
- Dieser Slice erstellt KEINEN Feature-Code -- nur eine Agent-Definition (.md)

---

## Integration Contract (GATE 2 PFLICHT)

### Requires From Other Slices

| Slice | Resource | Type | Validation |
|-------|----------|------|------------|
| slice-01-test-writer-enhancement | Test-File-Naming Konvention | Konvention | Test-Pfade folgen `tests/unit/`, `tests/integration/`, `tests/acceptance/` Pattern |
| slice-01-test-writer-enhancement | AC-Test-Dateien | Dateien | Acceptance Tests existieren in `tests/acceptance/test_{slice_id}.py` |

### Provides To Other Slices

| Resource | Type | Consumer | Interface |
|----------|------|----------|-----------|
| Test-Validator Agent Definition | Agent (.md) | Slice 3 (Orchestrator) | Agent wird via `Task(test-validator, prompt)` aufgerufen |
| JSON Output Contract | Datenformat | Slice 3 (Orchestrator) | `{ overall_status, stages{unit,integration,acceptance,smoke,regression}, failed_stage?, error_output? }` |
| Stage-Skip-Semantik | Konvention | Slice 3 (Orchestrator) | Bei Stage-Failure: nachfolgende Stages haben `exit_code: -1`, `summary: "skipped"` |

### Integration Validation Tasks

- [ ] Agent-Definition ist syntaktisch korrekt (Frontmatter + Markdown)
- [ ] JSON Output Contract ist vollstaendig definiert (alle Felder aus architecture.md)
- [ ] Stack-Detection Matrix deckt Python und TypeScript ab
- [ ] Smoke Test Ablauf ist vollstaendig beschrieben (Start, Poll, Check, Kill)
- [ ] Stage-Reihenfolge stimmt mit architecture.md ueberein (Unit -> Integration -> Acceptance -> Smoke -> Regression)
- [ ] Regression-Input-Format ist dokumentiert (Liste vorheriger Test-Pfade)

---

## Acceptance Criteria

1) GIVEN der Test-Validator Agent wird mit Test-Pfaden aufgerufen
   WHEN er die Unit Tests ausfuehrt
   THEN nutzt er den erkannten Stack-Test-Command (z.B. `python -m pytest tests/unit/ -v`) und reportet exit_code, duration_ms und summary

2) GIVEN der Test-Validator Agent hat alle 5 Stages (Unit, Integration, Acceptance, Smoke, Regression) erfolgreich durchlaufen
   WHEN er seinen Output liefert
   THEN ist `overall_status: "passed"` und alle Stages haben `exit_code: 0` (bzw. `health_status: 200` beim Smoke)

3) GIVEN der Test-Validator Agent fuehrt den Smoke Test aus
   WHEN er die App startet und den Health-Endpoint abfragt
   THEN pollt er maximal 30 Sekunden lang alle 1 Sekunde `GET /health`, erwartet HTTP 200, und stoppt die App danach (Kill PID)

4) GIVEN der Test-Validator Agent fuehrt den Regression Run aus und erhaelt eine Liste vorheriger Slice-Test-Pfade
   WHEN er die Regression Tests ausfuehrt
   THEN re-runt er ALLE angegebenen Test-Pfade und reportet exit_code und slices_tested

5) GIVEN der Test-Validator Agent und ein Stage schlaegt fehl (exit_code != 0)
   WHEN er die weiteren Stages verarbeitet
   THEN werden ALLE nachfolgenden Stages uebersprungen (exit_code: -1, summary: "skipped") und overall_status ist "failed" mit failed_stage und error_output

6) GIVEN der Test-Validator Agent wird in einem Python/FastAPI Repo aufgerufen (erkennbar an `pyproject.toml` mit fastapi Dependency)
   WHEN er den Stack erkennt
   THEN verwendet er pytest, `uvicorn app.main:app` als Start-Command und `http://localhost:8000/health` als Health-Endpoint

7) GIVEN der Test-Validator Agent hat seine Validation abgeschlossen
   WHEN er den Output liefert
   THEN ist der letzte Code-Block im Output ein valides JSON-Objekt mit den Feldern: `overall_status`, `stages.unit` (mit exit_code, duration_ms, summary), `stages.integration`, `stages.acceptance`, `stages.smoke` (mit app_started, health_status, startup_duration_ms), `stages.regression` (mit exit_code, slices_tested)

8) GIVEN der Test-Validator Agent wird im Final Validation Mode aufgerufen
   WHEN er Lint ausfuehrt
   THEN fuehrt er zuerst Auto-Fix (`ruff check --fix .` bei Python) aus und dann den Lint-Check (`ruff check .`), wobei verbleibende Lint-Fehler als Failure gemeldet werden

9) GIVEN der Test-Validator Agent und ein Test-Verzeichnis existiert nicht (z.B. `tests/integration/` fehlt)
   WHEN er den zugehoerigen Stage ausfuehrt
   THEN wertet er den Stage als "passed" mit exit_code 0 und summary "no tests found (directory does not exist)"

---

## Testfaelle

### Test-Datei

`tests/acceptance/test_slice_02_test_validator_agent.py`

**Hinweis:** Da dieser Slice eine Agent-Definition (Markdown) erstellt und keinen ausfuehrbaren Code, sind die Tests Validierungen der Agent-Definition selbst. Die Tests pruefen die Markdown-Datei auf strukturelle Korrektheit und Vollstaendigkeit.

<test_spec>
```python
# tests/acceptance/test_slice_02_test_validator_agent.py
"""
Acceptance Tests fuer Slice 02: Test-Validator Agent.

Validiert dass die Agent-Definition (.claude/agents/test-validator.md)
alle erforderlichen Sections und Inhalte enthaelt.
"""
import pytest
from pathlib import Path
import re
import json

AGENT_FILE = Path(".claude/agents/test-validator.md")


@pytest.fixture
def agent_content():
    """Liest den Test-Validator Agent-Inhalt."""
    assert AGENT_FILE.exists(), f"Agent-Datei {AGENT_FILE} existiert nicht"
    return AGENT_FILE.read_text(encoding="utf-8")


class TestUnitTestExecution:
    """AC-1: Agent fuehrt Unit Tests aus mit korrektem Reporting."""

    @pytest.mark.acceptance
    def test_ac_1_unit_test_execution(self, agent_content):
        """AC-1: GIVEN Test-Pfade WHEN Unit Tests ausgefuehrt THEN exit_code, duration_ms, summary reportet."""
        assert "unit" in agent_content.lower(), \
            "Agent-Definition muss Unit Test Stage enthalten"
        assert "exit_code" in agent_content, \
            "Agent-Definition muss exit_code als Output-Feld definieren"
        assert "duration_ms" in agent_content, \
            "Agent-Definition muss duration_ms als Output-Feld definieren"
        assert "summary" in agent_content, \
            "Agent-Definition muss summary als Output-Feld definieren"
        assert "python -m pytest" in agent_content, \
            "Agent-Definition muss pytest-Command fuer Python enthalten"


class TestOverallStatusPassed:
    """AC-2: overall_status ist passed wenn alle Stages erfolgreich."""

    @pytest.mark.acceptance
    def test_ac_2_overall_status_logic(self, agent_content):
        """AC-2: GIVEN alle 5 Stages erfolgreich WHEN Output THEN overall_status passed."""
        assert "overall_status" in agent_content, \
            "Agent-Definition muss overall_status definieren"
        assert '"passed"' in agent_content, \
            "Agent-Definition muss 'passed' als moeglichen Status definieren"
        assert '"failed"' in agent_content, \
            "Agent-Definition muss 'failed' als moeglichen Status definieren"
        # Pruefe dass alle 5 Stages definiert sind
        for stage in ["unit", "integration", "acceptance", "smoke", "regression"]:
            assert f'"{stage}"' in agent_content or f"stages.{stage}" in agent_content or f"Stage" in agent_content, \
                f"Agent-Definition muss Stage '{stage}' definieren"


class TestSmokeTest:
    """AC-3: Smoke Test mit App-Start, Health-Polling, Kill."""

    @pytest.mark.acceptance
    def test_ac_3_smoke_test_definition(self, agent_content):
        """AC-3: GIVEN App gestartet WHEN Health-Endpoint abgefragt THEN 30s Polling, HTTP 200, Kill PID."""
        assert "health" in agent_content.lower(), \
            "Agent-Definition muss Health-Check beschreiben"
        assert "30" in agent_content, \
            "Agent-Definition muss 30 Sekunden Timeout definieren"
        assert "kill" in agent_content.lower() or "stop" in agent_content.lower(), \
            "Agent-Definition muss App-Stopp beschreiben (Kill PID)"
        assert "app_started" in agent_content, \
            "Agent-Definition muss app_started als Output-Feld definieren"
        assert "health_status" in agent_content, \
            "Agent-Definition muss health_status als Output-Feld definieren"
        assert "startup_duration_ms" in agent_content, \
            "Agent-Definition muss startup_duration_ms als Output-Feld definieren"
        assert "200" in agent_content, \
            "Agent-Definition muss HTTP 200 als Erfolgs-Kriterium definieren"


class TestRegressionRun:
    """AC-4: Regression Run mit allen vorherigen Slice-Tests."""

    @pytest.mark.acceptance
    def test_ac_4_regression_run(self, agent_content):
        """AC-4: GIVEN vorherige Slice-Test-Pfade WHEN Regression THEN alle re-run mit slices_tested."""
        assert "regression" in agent_content.lower(), \
            "Agent-Definition muss Regression Stage beschreiben"
        assert "slices_tested" in agent_content, \
            "Agent-Definition muss slices_tested als Output-Feld definieren"
        # Pruefen dass vorherige Tests re-run werden
        assert "previous" in agent_content.lower() or "vorherig" in agent_content.lower(), \
            "Agent-Definition muss beschreiben dass vorherige Slice-Tests re-run werden"


class TestStageSkipOnFailure:
    """AC-5: Bei Stage-Failure werden nachfolgende Stages uebersprungen."""

    @pytest.mark.acceptance
    def test_ac_5_stage_skip_semantik(self, agent_content):
        """AC-5: GIVEN Stage fehlgeschlagen WHEN weitere Stages THEN skip mit exit_code -1."""
        assert "skip" in agent_content.lower() or "uebersprungen" in agent_content.lower() or "abbruch" in agent_content.lower(), \
            "Agent-Definition muss Stage-Skip-Verhalten bei Failure beschreiben"
        assert "failed_stage" in agent_content, \
            "Agent-Definition muss failed_stage als Output-Feld definieren"
        assert "error_output" in agent_content, \
            "Agent-Definition muss error_output als Output-Feld definieren"


class TestStackDetection:
    """AC-6: Stack-Detection fuer Python/FastAPI."""

    @pytest.mark.acceptance
    def test_ac_6_python_stack_detection(self, agent_content):
        """AC-6: GIVEN Python/FastAPI Repo WHEN Stack erkannt THEN pytest + uvicorn + localhost:8000/health."""
        assert "pyproject.toml" in agent_content, \
            "Agent-Definition muss pyproject.toml als Stack-Indicator enthalten"
        assert "uvicorn" in agent_content, \
            "Agent-Definition muss uvicorn als Start-Command fuer FastAPI enthalten"
        assert "localhost:8000/health" in agent_content or "localhost:8000" in agent_content, \
            "Agent-Definition muss Health-Endpoint fuer FastAPI enthalten"
        assert "pytest" in agent_content, \
            "Agent-Definition muss pytest als Test-Framework fuer Python enthalten"


class TestJSONOutputContract:
    """AC-7: JSON Output Contract ist vollstaendig definiert."""

    @pytest.mark.acceptance
    def test_ac_7_json_output_contract(self, agent_content):
        """AC-7: GIVEN Validation abgeschlossen WHEN Output THEN valides JSON mit allen Pflichtfeldern."""
        json_blocks = re.findall(r'```json\s*\n(.*?)```', agent_content, re.DOTALL)
        assert len(json_blocks) > 0, "Agent-Definition muss mindestens einen JSON-Block enthalten"

        contract_found = False
        for block in json_blocks:
            try:
                parsed = json.loads(block.strip())
                if "overall_status" in parsed and "stages" in parsed:
                    contract_found = True
                    stages = parsed["stages"]
                    # Pruefe alle Stage-Felder
                    assert "unit" in stages, "stages muss 'unit' enthalten"
                    assert "integration" in stages, "stages muss 'integration' enthalten"
                    assert "acceptance" in stages, "stages muss 'acceptance' enthalten"
                    assert "smoke" in stages, "stages muss 'smoke' enthalten"
                    assert "regression" in stages, "stages muss 'regression' enthalten"
                    # Pruefe Unit-Stage-Felder
                    assert "exit_code" in stages["unit"], "unit muss exit_code enthalten"
                    assert "duration_ms" in stages["unit"], "unit muss duration_ms enthalten"
                    assert "summary" in stages["unit"], "unit muss summary enthalten"
                    # Pruefe Integration-Stage-Felder
                    assert "exit_code" in stages["integration"], "integration muss exit_code enthalten"
                    assert "duration_ms" in stages["integration"], "integration muss duration_ms enthalten"
                    assert "summary" in stages["integration"], "integration muss summary enthalten"
                    # Pruefe Acceptance-Stage-Felder
                    assert "exit_code" in stages["acceptance"], "acceptance muss exit_code enthalten"
                    assert "duration_ms" in stages["acceptance"], "acceptance muss duration_ms enthalten"
                    assert "summary" in stages["acceptance"], "acceptance muss summary enthalten"
                    # Pruefe Smoke-Stage-Felder
                    assert "app_started" in stages["smoke"], "smoke muss app_started enthalten"
                    assert "health_status" in stages["smoke"], "smoke muss health_status enthalten"
                    assert "startup_duration_ms" in stages["smoke"], "smoke muss startup_duration_ms enthalten"
                    # Pruefe Regression-Stage-Felder
                    assert "exit_code" in stages["regression"], "regression muss exit_code enthalten"
                    assert "slices_tested" in stages["regression"], "regression muss slices_tested enthalten"
                    break
            except json.JSONDecodeError:
                continue

        assert contract_found, "Agent-Definition muss JSON Output Contract mit overall_status und stages enthalten"


class TestAutoFixLint:
    """AC-8: Auto-Fix Lint bei Final Validation."""

    @pytest.mark.acceptance
    def test_ac_8_auto_fix_lint(self, agent_content):
        """AC-8: GIVEN Final Validation WHEN Lint THEN Auto-Fix zuerst, dann Check."""
        assert "ruff" in agent_content, \
            "Agent-Definition muss ruff fuer Python Lint enthalten"
        assert "--fix" in agent_content, \
            "Agent-Definition muss --fix fuer Auto-Fix enthalten"
        assert "final" in agent_content.lower() or "final_validation" in agent_content, \
            "Agent-Definition muss Final Validation Mode beschreiben"


class TestMissingDirectoryFallback:
    """AC-9: Fehlendes Test-Verzeichnis wird als passed gewertet."""

    @pytest.mark.acceptance
    def test_ac_9_missing_directory_fallback(self, agent_content):
        """AC-9: GIVEN Test-Verzeichnis fehlt WHEN Stage ausgefuehrt THEN passed mit 'no tests found'."""
        content_lower = agent_content.lower()
        assert "no tests found" in content_lower or "directory does not exist" in content_lower or "nicht existiert" in content_lower, \
            "Agent-Definition muss Fallback-Verhalten fuer fehlende Test-Verzeichnisse beschreiben"
```
</test_spec>

---

## Code Examples (MANDATORY - GATE 2 PFLICHT)

> **KRITISCH:** Alle Code-Beispiele in diesem Dokument sind **PFLICHT-Deliverables**.
> Der Gate 2 Compliance Agent prueft, dass jedes Code-Beispiel implementiert wird.
> Abweichung nur mit expliziter Begruendung im Commit erlaubt.

| Code Example | Section | Mandatory | Notes |
|--------------|---------|-----------|-------|
| Vollstaendige Agent-Definition (test-validator.md) | Technische Umsetzung 3.1-3.9 | YES | Neue Agent-Datei mit allen Sections |
| Stack-Detection Matrix | Technische Umsetzung 3.2 | YES | Tabelle mit Indicator Files, Start-Commands, Health-Endpoints |
| Smoke Test Ablauf | Technische Umsetzung 3.4 | YES | Start, Poll, Check, Kill Sequenz |
| JSON Output Contract (passed) | Technische Umsetzung 3.7 | YES | Vollstaendiges JSON mit allen Stages |
| JSON Output Contract (failed) | Technische Umsetzung 3.7 | YES | JSON mit failed_stage und error_output |
| Stage-Skip-Semantik | Technische Umsetzung 3.8 | YES | Verhalten bei uebersprungenen Stages |
| Final Validation Steps | Technische Umsetzung 4 | YES | Lint Auto-Fix + Type Check + Build |

### Agent-Definition: Vollstaendiger Inhalt fuer `.claude/agents/test-validator.md`

Der Implementer MUSS die Agent-Datei mit folgender Struktur erstellen:

```markdown
---
name: test-validator
description: Executes all test stages (Unit, Integration, Acceptance, Smoke, Regression). Stack-agnostic with auto-detection. Returns structured JSON evidence for Orchestrator. Read-only except for lint auto-fix.
tools: Bash, Read, Glob, Grep
---

Du bist ein spezialisierter Test-Validator Agent. Du fuehrst Tests aus und reportest Ergebnisse. Du fixst KEINEN Code -- das ist Aufgabe des Debuggers. Du bist read-only gegenueber der Codebase (Ausnahme: Auto-Fix Lint bei Final Validation).

---

## Fundamentale Regeln

1. **Exit Code ist Wahrheit** -- exit_code == 0 = BESTANDEN, alles andere = FEHLGESCHLAGEN
2. **KEIN Code-Fix** -- Du fuehrst nur aus und reportest, du fixst nichts
3. **Sequenzielle Stages** -- Unit -> Integration -> Acceptance -> Smoke -> Regression (Abbruch bei Failure)
4. **Stack-agnostisch** -- Erkenne den Stack automatisch, verwende KEINE hardcoded Commands
5. **JSON Output Contract** -- Dein letzter Output MUSS ein ```json``` Block mit dem definierten Contract sein
6. **App MUSS gestoppt werden** -- Nach Smoke Test: App IMMER stoppen (Kill PID), auch bei Failure

---

## Input (vom Orchestrator)

Du erhaeltst:

| Input | Beschreibung | Pflicht |
|-------|--------------|---------|
| Slice-ID | z.B. "slice-03-business-logic" | Ja |
| Test-Paths | Pfade zu Test-Verzeichnissen (unit, integration, acceptance) | Ja |
| Previous-Slice-Tests | Pfade zu Tests vorheriger Slices (fuer Regression) | Ja |
| Mode | "slice_validation" oder "final_validation" | Ja |
| Working-Directory | z.B. "backend" | Ja |

---

## Workflow

### Phase 1: Stack Detection

Erkenne den Stack anhand von Indicator-Dateien:

| Indicator File | Stack | Test Framework | Test Command | Start Command | Health Endpoint |
|----------------|-------|---------------|-------------|---------------|-----------------|
| pyproject.toml + fastapi | Python/FastAPI | pytest | python -m pytest {path} -v | uvicorn app.main:app --host 0.0.0.0 --port 8000 | http://localhost:8000/health |
| requirements.txt + fastapi | Python/FastAPI | pytest | python -m pytest {path} -v | uvicorn app.main:app --host 0.0.0.0 --port 8000 | http://localhost:8000/health |
| package.json + next | TypeScript/Next.js | vitest + playwright | pnpm test {path} | pnpm dev | http://localhost:3000/api/health |
| package.json + express | TypeScript/Express | vitest | pnpm test {path} | node server.js | http://localhost:3000/health |
| go.mod | Go | go test | go test {path} | go run . | http://localhost:8080/health |

### Phase 2: Test Execution (Sequenziell)

Fuehre Stages in dieser Reihenfolge aus. Bei Failure: ABBRUCH, alle nachfolgenden Stages = skipped.

#### Stage 1: Unit Tests
- Command: `{test_command} tests/unit/ -v`
- Falls Verzeichnis nicht existiert: exit_code 0, summary "no tests found (directory does not exist)"
- Messe duration_ms (Start bis Ende)
- Parse summary aus Test-Output (z.B. "12 passed, 0 failed")

#### Stage 2: Integration Tests
- Command: `{test_command} tests/integration/ -v`
- Falls Verzeichnis nicht existiert: exit_code 0, summary "no tests found (directory does not exist)"
- Messe duration_ms (Start bis Ende)
- Parse summary aus Test-Output (z.B. "5 passed, 0 failed")
- Output fields: exit_code, duration_ms, summary

#### Stage 3: Acceptance Tests
- Command: `{test_command} tests/acceptance/ -v`
- Falls Verzeichnis nicht existiert: exit_code 0, summary "no tests found (directory does not exist)"
- Messe duration_ms (Start bis Ende)
- Parse summary aus Test-Output (z.B. "3 passed, 0 failed")
- Output fields: exit_code, duration_ms, summary

#### Stage 4: Smoke Test
1. App starten im Hintergrund: `{start_command} &`
2. PID merken
3. Polling-Loop: Alle 1 Sekunde `curl -s -o /dev/null -w "%{http_code}" {health_endpoint}`
4. Timeout: 30 Sekunden
5. Erfolg: HTTP Status 200
6. App stoppen: `kill {PID}`, nach 5s `kill -9 {PID}` falls noch laufend

#### Stage 5: Regression
- Command: `{test_command} {all_previous_test_paths} -v`
- Falls keine vorherigen Tests: exit_code 0, slices_tested [], summary "No previous slices to test"

### Phase 3: Final Validation (nur bei mode: final_validation)

Zusaetzliche Steps VOR den Test-Stages:
1. Auto-Fix Lint: `ruff check --fix .` (Python) / `pnpm eslint --fix .` (TypeScript)
2. Lint Check: `ruff check .` (Python) / `pnpm lint` (TypeScript)
3. Type Check: `mypy .` (Python, falls konfiguriert) / `pnpm tsc --noEmit` (TypeScript)
4. Build: `pip install -e .` (Python, falls setup.py) / `pnpm build` (TypeScript)

### Phase 4: JSON Output

Dein LETZTER Output MUSS ein ```json``` Block sein mit dem Output Contract.

---

## Verzeichnis-Fallback

Falls ein Test-Verzeichnis nicht existiert:
- Stage als "passed" werten mit exit_code: 0
- summary: "no tests found (directory does not exist)"
- duration_ms: 0
- Pipeline laeuft weiter

---

## Stage-Skip bei Failure

Wenn ein Stage fehlschlaegt:
- ALLE nachfolgenden Stages werden uebersprungen
- Uebersprungene Stages: exit_code: -1, duration_ms: 0, summary: "skipped (previous stage failed)"
- Smoke: app_started: false, health_status: 0, startup_duration_ms: 0
- Regression: exit_code: -1, slices_tested: []
- overall_status: "failed"
- failed_stage: Name des fehlgeschlagenen Stages
- error_output: Stderr/Stdout des fehlgeschlagenen Stages (max 2000 Zeichen)
```

---

## Deliverables (SCOPE SAFEGUARD)

<!-- DELIVERABLES_START -->
### Agent-Definition
- [ ] `.claude/agents/test-validator.md` -- Neue Agent-Definition mit Stack-Detection, 5 Test-Stages, Smoke Test, Regression Run, Auto-Fix Lint, JSON Output Contract, Stage-Skip-Semantik, Final Validation Mode

### Tests
- [ ] `tests/acceptance/test_slice_02_test_validator_agent.py` -- Acceptance Tests die pruefen ob die Agent-Definition alle erforderlichen Sections enthaelt
<!-- DELIVERABLES_END -->

---

## Definition of Done

- [x] Akzeptanzkriterien sind eindeutig und vollstaendig (9 ACs im GIVEN/WHEN/THEN Format)
- [x] JSON Output Contract definiert (passed + failed Varianten)
- [x] Stack-Detection Matrix definiert (Python, TypeScript, Go)
- [x] Smoke Test Ablauf vollstaendig beschrieben (Start, Poll, Check, Kill)
- [x] Regression Run Ablauf definiert (alle vorherigen Tests re-run)
- [x] Stage-Skip-Semantik dokumentiert
- [x] Final Validation Mode definiert (Lint, Type, Build)
- [x] Verzeichnis-Fallback dokumentiert
- [ ] Rollout: Agent-Definition erstellt als `.claude/agents/test-validator.md`

---

## Links

- Architecture: `specs/2026-02-14-orchestrator-robust-testing/architecture.md`
- Discovery: `specs/2026-02-14-orchestrator-robust-testing/discovery.md`
- Vorheriger Slice: `specs/2026-02-14-orchestrator-robust-testing/slices/slice-01-test-writer-enhancement.md`
- Bestehender Health-Endpoint: `backend/app/main.py` (Zeile 40: `@app.get("/health")`)
- Evidence-Format Referenz: `.claude/evidence/backend-kern/slice-01.json`

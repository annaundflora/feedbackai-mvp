# Slice 1: Test-Writer Agent um AC-Generation und Stack-Erkennung erweitern

> **Slice 1 von 4** fuer `Lean Testing Pipeline`
>
> | Navigation | |
> |------------|---|
> | **Vorheriger:** | -- |
> | **Naechster:** | `slice-02-test-validator.md` |

---

## Metadata (fuer Orchestrator)

| Key | Value |
|-----|-------|
| **ID** | `slice-01-test-writer-enhancement` |
| **Test** | `cd backend && python -m pytest tests/acceptance/test_slice_01_test_writer_enhancement.py -v` |
| **E2E** | `false` |
| **Dependencies** | `[]` |

---

## Slice-Uebersicht

| # | Slice | Status | Datei |
|---|-------|--------|-------|
| 1 | Test-Writer Agent Enhancement | Ready | `slice-01-test-writer-enhancement.md` |
| 2 | Test-Validator Agent | Pending | `slice-02-test-validator.md` |
| 3 | Orchestrator Pipeline | Pending | `slice-03-orchestrator-pipeline.md` |
| 4 | Planner & Gate Improvements | Pending | `slice-04-planner-gates.md` |

---

## Kontext & Ziel

Der aktuelle Test-Writer Agent (`.claude/agents/test-writer.md`) ist ein generischer Test-Engineer der Tests fuer vorhandenen Code schreibt. Er hat folgende Defizite:

1. **Keine AC-Test-Generation** -- GIVEN/WHEN/THEN Acceptance Criteria in Slice-Specs werden nicht systematisch zu Acceptance Tests konvertiert
2. **Hardcoded Stacks** -- Agent kennt nur Python/pytest und TypeScript/Vitest, erkennt Stack nicht automatisch
3. **Keine Test-Typ-Trennung** -- Keine klare Unterscheidung zwischen Unit, Integration und Acceptance Tests
4. **Kein AC-Coverage-Report** -- Keine strukturierte Ausgabe welche ACs Tests haben und welche fehlen
5. **Keine standardisierte Test-File-Naming** -- Tests landen in beliebigen Ordnern statt in `tests/unit/`, `tests/integration/`, `tests/acceptance/`
6. **Kein JSON Output Contract** -- Orchestrator kann Output nicht maschinell parsen

Dieser Slice erweitert den Test-Writer Agent um alle diese Faehigkeiten. Der Agent wird modifiziert, nicht neu geschrieben -- bestehende Patterns (Mocking, Fixtures, Qualitaets-Checkliste) bleiben erhalten.

---

## Technische Umsetzung

### Architektur-Kontext (aus architecture.md)

> **Quelle:** `architecture.md` -> Agent Definitions, Test-Writer Output Contract, Stack-Detection Matrix, Test-File Conventions

```
Orchestrator
  |
  v
Task(test-writer)
  Input: Slice-Spec (ACs), files_changed, Test-Strategy Metadata
  |
  v
  1. Stack erkennen (pyproject.toml? package.json?)
  2. ACs aus Slice-Spec extrahieren
  3. Tests generieren (Unit + Integration + Acceptance)
  4. AC-Coverage berechnen
  5. JSON Output Contract returnen
  |
  v
Output: { status, test_files, test_count, ac_coverage, commit_hash }
```

### 1. Architektur-Impact

| Layer | Aenderungen |
|-------|------------|
| `.claude/agents/test-writer.md` | Komplette Erweiterung: AC-Generation, Stack-Detection, JSON Output Contract, Test-File-Naming |

### 2. Datenfluss

```
Slice-Spec (.md Datei)
  |
  v
[AC-Extraktion] -- Alle GIVEN/WHEN/THEN parsen, IDs zuweisen (AC-1, AC-2, ...)
  |
  v
[Stack-Detection] -- pyproject.toml/package.json/go.mod lesen -> Test-Framework bestimmen
  |
  v
[Test-Generation]
  |-- Unit Tests:       tests/unit/test_{module}.py       (isoliert, alle Deps gemockt)
  |-- Integration Tests: tests/integration/test_{module}.py (echte Deps)
  |-- Acceptance Tests:  tests/acceptance/test_{slice_id}.py (1:1 aus ACs)
  |
  v
[AC-Coverage-Berechnung] -- total ACs vs. covered ACs
  |
  v
[Git Commit] -- test(slice-id): Add tests for {slice-name}
  |
  v
[JSON Output] -- Letzter ```json``` Block im Agent-Output
```

### 3. Agent-Definition: Neue Sections

Die folgenden Sections werden zur bestehenden `test-writer.md` **hinzugefuegt** oder **ersetzt**:

#### 3.1 Agent-Rolle und Scope (ERSETZT)

Der Agent bekommt eine neue Rollendefinition die klarstellt:
- Er schreibt Tests **gegen die Spec**, nicht gegen den Code
- Er schreibt **NUR Tests**, keinen Feature-Code
- Er muss **100% AC-Coverage** erreichen
- Er muss einen **JSON Output Contract** liefern

#### 3.2 Stack-Detection (NEU)

Der Agent erkennt den Stack automatisch anhand von Indicator-Dateien:

| Indicator File | Stack | Test Framework | Test Command Pattern |
|----------------|-------|---------------|---------------------|
| `pyproject.toml` + fastapi dep | Python/FastAPI | pytest | `python -m pytest {path} -v` |
| `requirements.txt` + fastapi | Python/FastAPI | pytest | `python -m pytest {path} -v` |
| `package.json` + next dep | TypeScript/Next.js | vitest | `pnpm test {path}` |
| `package.json` + express dep | TypeScript/Express | vitest | `pnpm test {path}` |
| `go.mod` | Go | go test | `go test {path}` |

#### 3.3 AC-Test-Generation (NEU)

Fuer jede GIVEN/WHEN/THEN in der Slice-Spec wird ein Acceptance Test generiert:

```
Spec AC:
  1) GIVEN ein neuer User
     WHEN er sich registriert
     THEN wird ein Account erstellt

Generierter Test (Python):
  @pytest.mark.acceptance
  def test_ac_1_account_creation(self):
      """AC-1: GIVEN ein neuer User WHEN er sich registriert THEN wird ein Account erstellt."""
      # Arrange (GIVEN)
      ...
      # Act (WHEN)
      ...
      # Assert (THEN)
      ...
```

#### 3.4 Test-File-Naming (NEU)

| Test Type | Python Path | TypeScript Path |
|-----------|-------------|-----------------|
| Unit | `tests/unit/test_{module}.py` | `tests/unit/{module}.test.ts` |
| Integration | `tests/integration/test_{module}.py` | `tests/integration/{module}.test.ts` |
| Acceptance | `tests/acceptance/test_{slice_id}.py` | `tests/acceptance/{slice_id}.test.ts` |

#### 3.5 AC-Coverage-Report (NEU)

Der Agent zaehlt alle ACs in der Spec und gleicht sie mit generierten Tests ab:
- `ac_coverage.total`: Anzahl GIVEN/WHEN/THEN Bloecke in der Spec
- `ac_coverage.covered`: Anzahl ACs die einen Test haben
- `ac_coverage.missing`: Liste der AC-IDs ohne Test (muss leer sein)

#### 3.6 JSON Output Contract (NEU)

Der letzte Code-Block im Agent-Output muss dieses JSON-Format haben:

```json
{
  "status": "completed",
  "test_files": [
    "tests/unit/test_auth_service.py",
    "tests/integration/test_auth_api.py",
    "tests/acceptance/test_slice_01_app_skeleton.py"
  ],
  "test_count": {
    "unit": 5,
    "integration": 2,
    "acceptance": 3
  },
  "ac_coverage": {
    "total": 3,
    "covered": 3,
    "missing": []
  },
  "commit_hash": "abc123def456"
}
```

### 4. Delta zum bestehenden Agent

| Section | Aenderung | Typ |
|---------|-----------|-----|
| Frontmatter (name, description) | Description erweitern um AC-Generation und Stack-Detection | MODIFY |
| Rollendefinition (Zeile 7) | Neue Rolle: Tests gegen Spec, nicht gegen Code. NUR Tests, kein Feature-Code | REPLACE |
| Scope (Input/Output) | Input: Slice-Spec + files_changed + Test-Strategy. Output: JSON Contract | REPLACE |
| Expertise Section | Stack-agnostisch machen, Stack-Detection Matrix einfuegen | REPLACE |
| Kernverantwortung | AC-Extraktion, 3 Test-Typen, Coverage-Report hinzufuegen | REPLACE |
| Test-Struktur | Acceptance Test Beispiele hinzufuegen, Test-File-Naming aktualisieren | EXTEND |
| Test-Kategorien | Acceptance als dritte Kategorie, pytest.mark.acceptance | EXTEND |
| Mocking-Patterns | Bleiben erhalten (unveraendert) | KEEP |
| Test-Ausfuehrung | Stack-agnostische Commands statt hardcoded | REPLACE |
| Qualitaets-Checkliste | AC-Coverage-Check hinzufuegen | EXTEND |
| FeedbackAI-spezifische Patterns | Bleiben erhalten (unveraendert) | KEEP |
| JSON Output Contract | Komplett neue Section am Ende | ADD |

---

## Constraints & Hinweise

**Betrifft:**
- Ausschliesslich `.claude/agents/test-writer.md` -- eine einzige Markdown-Datei

**Agent Separation Rule:**
- Test-Writer schreibt NUR Tests, KEINEN Feature-Code (Rule 2 aus Discovery)
- Tests sind Ground Truth -- Debugger fixt Code, NICHT Tests (Rule 3)

**Abgrenzung:**
- Dieser Slice aendert KEINE anderen Agents (slice-implementer, orchestrate, debugger)
- Dieser Slice fuehrt KEINE Tests aus -- das ist Aufgabe des Test-Validator (Slice 2)
- Dieser Slice aendert KEIN Template -- das ist Aufgabe von Slice 4

---

## Integration Contract (GATE 2 PFLICHT)

### Requires From Other Slices

| Slice | Resource | Type | Validation |
|-------|----------|------|------------|
| -- | -- | -- | -- |

Keine Dependencies. Slice 1 ist unabhaengig.

### Provides To Other Slices

| Resource | Type | Consumer | Interface |
|----------|------|----------|-----------|
| Test-Writer Agent Definition | Agent (.md) | Slice 2 (Test-Validator), Slice 3 (Orchestrator) | Agent wird via `Task(test-writer, prompt)` aufgerufen |
| JSON Output Contract | Datenformat | Slice 3 (Orchestrator) | `{ status, test_files, test_count{unit,integration,acceptance}, ac_coverage{total,covered,missing}, commit_hash }` |
| Test-File-Naming Konvention | Konvention | Slice 2 (Test-Validator) | `tests/acceptance/test_{slice_id}.py` bzw. `tests/acceptance/{slice_id}.test.ts` |

### Integration Validation Tasks

- [ ] Agent-Definition ist syntaktisch korrekt (Frontmatter + Markdown)
- [ ] JSON Output Contract ist vollstaendig definiert (alle Felder aus architecture.md)
- [ ] Stack-Detection Matrix deckt Python und TypeScript ab
- [ ] Test-File-Naming stimmt mit architecture.md ueberein

---

## Acceptance Criteria

1) GIVEN der Test-Writer Agent wird mit einer Slice-Spec aufgerufen die 3 GIVEN/WHEN/THEN Acceptance Criteria enthaelt
   WHEN der Agent die Tests generiert
   THEN existieren mindestens 3 Acceptance Tests (einer pro AC) in `tests/acceptance/test_{slice_id}.py`

2) GIVEN der Test-Writer Agent wird in einem Python/FastAPI Repo aufgerufen (erkennbar an `pyproject.toml` mit fastapi Dependency)
   WHEN der Agent den Stack erkennt
   THEN verwendet er pytest als Test-Framework und `python -m pytest {path} -v` als Test-Command

3) GIVEN der Test-Writer Agent wird in einem TypeScript/Next.js Repo aufgerufen (erkennbar an `package.json` mit next Dependency)
   WHEN der Agent den Stack erkennt
   THEN verwendet er vitest als Test-Framework und `pnpm test {path}` als Test-Command

4) GIVEN der Test-Writer Agent hat Tests generiert
   WHEN er seinen Output liefert
   THEN ist der letzte Code-Block im Output ein valides JSON-Objekt mit den Feldern: `status`, `test_files`, `test_count` (mit `unit`, `integration`, `acceptance`), `ac_coverage` (mit `total`, `covered`, `missing`), `commit_hash`

5) GIVEN der Test-Writer Agent hat alle ACs der Slice-Spec abgedeckt
   WHEN er den AC-Coverage-Report erstellt
   THEN ist `ac_coverage.total == ac_coverage.covered` und `ac_coverage.missing` ist ein leeres Array

6) GIVEN der Test-Writer Agent generiert Tests
   WHEN er die Test-Dateien benennt
   THEN folgen die Pfade der Konvention: Unit in `tests/unit/test_{module}.py`, Integration in `tests/integration/test_{module}.py`, Acceptance in `tests/acceptance/test_{slice_id}.py` (Python) bzw. `tests/unit/{module}.test.ts`, `tests/integration/{module}.test.ts`, `tests/acceptance/{slice_id}.test.ts` (TypeScript)

7) GIVEN der Test-Writer Agent
   WHEN er Tests schreibt
   THEN schreibt er ausschliesslich Test-Code und KEINEN Feature-Code (keine neuen Module, keine neuen Endpoints, keine Business-Logik)

8) GIVEN der Test-Writer Agent generiert Acceptance Tests
   WHEN ein AC lautet "GIVEN X WHEN Y THEN Z"
   THEN hat der generierte Test einen Docstring/Kommentar der die AC-ID und den originalen GIVEN/WHEN/THEN Text enthaelt

---

## Testfaelle

### Test-Datei

`tests/acceptance/test_slice_01_test_writer_enhancement.py`

**Hinweis:** Da dieser Slice eine Agent-Definition (Markdown) aendert und keinen ausfuehrbaren Code, sind die "Tests" Validierungen der Agent-Definition selbst. Die Tests pruefen die Markdown-Datei auf strukturelle Korrektheit und Vollstaendigkeit.

<test_spec>
```python
# tests/acceptance/test_slice_01_test_writer_enhancement.py
"""
Acceptance Tests fuer Slice 01: Test-Writer Agent Enhancement.

Validiert dass die Agent-Definition (.claude/agents/test-writer.md)
alle erforderlichen Sections und Inhalte enthaelt.
"""
import pytest
from pathlib import Path
import re
import json

AGENT_FILE = Path(".claude/agents/test-writer.md")


@pytest.fixture
def agent_content():
    """Liest den Test-Writer Agent-Inhalt."""
    assert AGENT_FILE.exists(), f"Agent-Datei {AGENT_FILE} existiert nicht"
    return AGENT_FILE.read_text(encoding="utf-8")


class TestACGeneration:
    """AC-1: Agent-Definition enthaelt AC-Test-Generation Anweisungen."""

    @pytest.mark.acceptance
    def test_ac_1_acceptance_test_generation_section(self, agent_content):
        """AC-1: GIVEN Slice-Spec mit GIVEN/WHEN/THEN ACs WHEN Agent Tests generiert THEN existieren Acceptance Tests."""
        assert "GIVEN" in agent_content and "WHEN" in agent_content and "THEN" in agent_content, \
            "Agent-Definition muss Anweisungen fuer GIVEN/WHEN/THEN AC-Extraktion enthalten"
        assert "acceptance" in agent_content.lower(), \
            "Agent-Definition muss 'acceptance' Tests als Konzept enthalten"
        assert "tests/acceptance/" in agent_content, \
            "Agent-Definition muss Pfad tests/acceptance/ referenzieren"


class TestStackDetection:
    """AC-2, AC-3: Stack-Detection fuer Python und TypeScript."""

    @pytest.mark.acceptance
    def test_ac_2_python_stack_detection(self, agent_content):
        """AC-2: GIVEN Python/FastAPI Repo WHEN Stack erkannt THEN pytest als Framework."""
        assert "pyproject.toml" in agent_content, \
            "Agent-Definition muss pyproject.toml als Stack-Indicator enthalten"
        assert "pytest" in agent_content, \
            "Agent-Definition muss pytest als Test-Framework fuer Python enthalten"
        assert "python -m pytest" in agent_content, \
            "Agent-Definition muss 'python -m pytest' als Test-Command enthalten"

    @pytest.mark.acceptance
    def test_ac_3_typescript_stack_detection(self, agent_content):
        """AC-3: GIVEN TypeScript/Next.js Repo WHEN Stack erkannt THEN vitest als Framework."""
        assert "package.json" in agent_content, \
            "Agent-Definition muss package.json als Stack-Indicator enthalten"
        assert "vitest" in agent_content, \
            "Agent-Definition muss vitest als Test-Framework fuer TypeScript enthalten"


class TestJSONOutputContract:
    """AC-4: JSON Output Contract ist definiert."""

    @pytest.mark.acceptance
    def test_ac_4_json_output_contract_defined(self, agent_content):
        """AC-4: GIVEN Tests generiert WHEN Output geliefert THEN valides JSON mit allen Pflichtfeldern."""
        # Pruefe dass ein JSON-Beispiel mit allen Pflichtfeldern existiert
        json_blocks = re.findall(r'```json\s*\n(.*?)```', agent_content, re.DOTALL)
        assert len(json_blocks) > 0, "Agent-Definition muss mindestens einen JSON-Block enthalten"

        # Finde den Output Contract JSON-Block
        contract_found = False
        for block in json_blocks:
            try:
                parsed = json.loads(block.strip())
                if all(key in parsed for key in ["status", "test_files", "test_count", "ac_coverage", "commit_hash"]):
                    contract_found = True
                    # Pruefe Unterfelder
                    assert "unit" in parsed["test_count"], "test_count muss 'unit' enthalten"
                    assert "integration" in parsed["test_count"], "test_count muss 'integration' enthalten"
                    assert "acceptance" in parsed["test_count"], "test_count muss 'acceptance' enthalten"
                    assert "total" in parsed["ac_coverage"], "ac_coverage muss 'total' enthalten"
                    assert "covered" in parsed["ac_coverage"], "ac_coverage muss 'covered' enthalten"
                    assert "missing" in parsed["ac_coverage"], "ac_coverage muss 'missing' enthalten"
                    break
            except json.JSONDecodeError:
                continue

        assert contract_found, "Agent-Definition muss JSON Output Contract mit allen Pflichtfeldern enthalten"


class TestACCoverage:
    """AC-5: AC-Coverage-Report Konzept ist definiert."""

    @pytest.mark.acceptance
    def test_ac_5_ac_coverage_report(self, agent_content):
        """AC-5: GIVEN alle ACs abgedeckt WHEN Coverage-Report THEN total == covered und missing leer."""
        assert "ac_coverage" in agent_content, \
            "Agent-Definition muss ac_coverage Konzept enthalten"
        assert "100%" in agent_content or "total == covered" in agent_content or "total" in agent_content, \
            "Agent-Definition muss 100% AC-Coverage als Ziel definieren"
        assert "missing" in agent_content, \
            "Agent-Definition muss 'missing' ACs tracken"


class TestFileNaming:
    """AC-6: Test-File-Naming Konventionen."""

    @pytest.mark.acceptance
    def test_ac_6_file_naming_conventions(self, agent_content):
        """AC-6: GIVEN Tests generiert WHEN Dateien benannt THEN folgen sie der Konvention."""
        # Python conventions
        assert "tests/unit/test_" in agent_content, \
            "Agent-Definition muss Python Unit-Test Pfad-Pattern enthalten"
        assert "tests/integration/test_" in agent_content, \
            "Agent-Definition muss Python Integration-Test Pfad-Pattern enthalten"
        assert "tests/acceptance/test_" in agent_content, \
            "Agent-Definition muss Python Acceptance-Test Pfad-Pattern enthalten"
        # TypeScript conventions
        assert ".test.ts" in agent_content, \
            "Agent-Definition muss TypeScript Test-Datei-Endung enthalten"


class TestNoFeatureCode:
    """AC-7: Agent schreibt NUR Tests."""

    @pytest.mark.acceptance
    def test_ac_7_no_feature_code_rule(self, agent_content):
        """AC-7: GIVEN Test-Writer WHEN Tests schreibt THEN NUR Test-Code, KEIN Feature-Code."""
        content_lower = agent_content.lower()
        assert "nur tests" in content_lower or "only tests" in content_lower or "keinen feature-code" in content_lower, \
            "Agent-Definition muss explizit klarstellen: NUR Tests, KEIN Feature-Code"


class TestACDocstring:
    """AC-8: Tests enthalten AC-ID und GIVEN/WHEN/THEN im Docstring."""

    @pytest.mark.acceptance
    def test_ac_8_docstring_with_ac_reference(self, agent_content):
        """AC-8: GIVEN Acceptance Test WHEN generiert THEN Docstring enthaelt AC-ID und GIVEN/WHEN/THEN."""
        # Pruefe dass die Agent-Definition ein Beispiel zeigt wo AC-ID im Docstring steht
        assert "AC-" in agent_content or "ac_" in agent_content or "ac-" in agent_content, \
            "Agent-Definition muss AC-ID Referenzierung in Tests dokumentieren"
```
</test_spec>

---

## Code Examples (MANDATORY - GATE 2 PFLICHT)

> **KRITISCH:** Alle Code-Beispiele in diesem Dokument sind **PFLICHT-Deliverables**.
> Der Gate 2 Compliance Agent prueft, dass jedes Code-Beispiel implementiert wird.
> Abweichung nur mit expliziter Begruendung im Commit erlaubt.

| Code Example | Section | Mandatory | Notes |
|--------------|---------|-----------|-------|
| Erweiterte Agent-Definition (test-writer.md) | Technische Umsetzung 3.1-3.6 | YES | Alle neuen Sections muessen in der Agent-Datei enthalten sein |
| Stack-Detection Matrix | Technische Umsetzung 3.2 | YES | Tabelle mit Indicator Files und zugehoerigen Frameworks |
| AC-Test-Generation Beispiel | Technische Umsetzung 3.3 | YES | Zeigt wie GIVEN/WHEN/THEN zu pytest/vitest Tests werden |
| Test-File-Naming Konvention | Technische Umsetzung 3.4 | YES | Pfad-Patterns fuer alle 3 Test-Typen |
| JSON Output Contract | Technische Umsetzung 3.6 | YES | Vollstaendiges JSON-Beispiel mit allen Pflichtfeldern |

### Agent-Definition: Vollstaendiger Inhalt fuer `.claude/agents/test-writer.md`

Der Implementer MUSS die Agent-Datei so umschreiben, dass sie folgende Struktur hat (bestehende Mocking-Patterns und FeedbackAI-spezifische Patterns bleiben erhalten):

```markdown
---
name: test-writer
description: Writes tests against Slice-Spec Acceptance Criteria. Supports Python/pytest, TypeScript/vitest, Go/go-test. Generates Unit, Integration, and Acceptance tests with 100% AC coverage. Returns JSON output contract for Orchestrator.
model: opus
---

Du bist ein spezialisierter Test-Writer Agent. Du schreibst Tests **gegen die Spec (Acceptance Criteria)**, NICHT gegen den Code. Du schreibst **ausschliesslich Tests** -- KEINEN Feature-Code, KEINE neuen Module, KEINE Business-Logik.

---

## Fundamentale Regeln

1. **NUR Tests schreiben** -- Kein Feature-Code, keine neuen Endpoints, keine Business-Logik
2. **Tests gegen Spec** -- Deine Quelle sind die GIVEN/WHEN/THEN ACs in der Slice-Spec, nicht der Implementierungs-Code
3. **100% AC Coverage** -- Jede GIVEN/WHEN/THEN MUSS einen Acceptance Test haben
4. **Stack-agnostisch** -- Erkenne den Stack automatisch, verwende KEINE hardcoded Commands
5. **JSON Output Contract** -- Dein letzter Output MUSS ein ```json``` Block mit dem definierten Contract sein

---

## Input (vom Orchestrator)

Du erhaeltst:

| Input | Beschreibung | Pflicht |
|-------|--------------|---------|
| Slice-Spec | Markdown mit Acceptance Criteria (GIVEN/WHEN/THEN) | Ja |
| files_changed | Liste der vom Implementer geaenderten Dateien | Ja |
| Test-Strategy Metadata | Stack, Test-Commands, Mocking-Strategy | Optional (Fallback: Auto-Detection) |

---

## Workflow

### Phase 1: Stack Detection

Erkenne den Stack anhand von Indicator-Dateien im Repo-Root:

| Indicator File | Stack | Test Framework | Test Command Pattern |
|----------------|-------|---------------|---------------------|
| `pyproject.toml` + fastapi dep | Python/FastAPI | pytest | `python -m pytest {path} -v` |
| `requirements.txt` + fastapi | Python/FastAPI | pytest | `python -m pytest {path} -v` |
| `package.json` + next dep | TypeScript/Next.js | vitest | `pnpm test {path}` |
| `package.json` + express dep | TypeScript/Express | vitest | `pnpm test {path}` |
| `go.mod` | Go | go test | `go test {path}` |

Falls kein Stack erkannt wird: Fehler melden und `status: failed` returnen.

### Phase 2: AC-Extraktion

1. Lies die Slice-Spec
2. Finde alle GIVEN/WHEN/THEN Bloecke in der "Acceptance Criteria" Section
3. Nummeriere sie als AC-1, AC-2, AC-3, ...
4. Merke dir die Gesamtzahl (= `ac_coverage.total`)

### Phase 3: Test-Generation

Generiere drei Arten von Tests:

#### Unit Tests (tests/unit/)

- Isolierte Logik-Tests
- ALLE Dependencies gemockt (DB, APIs, Services)
- Schnell, deterministisch
- Validieren: interne Logik, Berechnungen, Validierung, Error Handling

#### Integration Tests (tests/integration/)

- Testen Zusammenspiel mehrerer Komponenten
- Echte Dependencies wo moeglich (Test-DB, lokale Services)
- Validieren: DB-Queries, API-Routing, Middleware-Chain, Serialisierung

#### Acceptance Tests (tests/acceptance/)

- **1:1 Ableitung aus GIVEN/WHEN/THEN**
- Eine Test-Datei pro Slice: `test_{slice_id}.py` (Python) oder `{slice_id}.test.ts` (TypeScript)
- Jeder Test hat Docstring/Kommentar mit AC-ID und originalem GIVEN/WHEN/THEN Text
- Testen fachliche Anforderungen via API-Call (nicht UI)

### Phase 4: Test-File Naming

| Test Type | Python Path | TypeScript Path |
|-----------|-------------|-----------------|
| Unit | `tests/unit/test_{module}.py` | `tests/unit/{module}.test.ts` |
| Integration | `tests/integration/test_{module}.py` | `tests/integration/{module}.test.ts` |
| Acceptance | `tests/acceptance/test_{slice_id}.py` | `tests/acceptance/{slice_id}.test.ts` |

### Phase 5: AC-Coverage Check

Zaehle:
- `total`: Anzahl GIVEN/WHEN/THEN in der Spec
- `covered`: Anzahl ACs die einen Test haben
- `missing`: Liste der AC-IDs ohne Test

**KRITISCH:** `total` MUSS gleich `covered` sein. Wenn nicht: Fehlende Tests ergaenzen!

### Phase 6: Git Commit

Committe alle Test-Dateien mit: `test({slice_id}): Add tests for {slice_name}`

### Phase 7: JSON Output

Dein LETZTER Output MUSS ein ```json``` Block sein:

```json
{
  "status": "completed",
  "test_files": [
    "tests/unit/test_auth_service.py",
    "tests/integration/test_auth_api.py",
    "tests/acceptance/test_slice_01_app_skeleton.py"
  ],
  "test_count": {
    "unit": 5,
    "integration": 2,
    "acceptance": 3
  },
  "ac_coverage": {
    "total": 3,
    "covered": 3,
    "missing": []
  },
  "commit_hash": "abc123def456"
}
```

Bei Fehler:

```json
{
  "status": "failed",
  "test_files": [],
  "test_count": { "unit": 0, "integration": 0, "acceptance": 0 },
  "ac_coverage": { "total": 0, "covered": 0, "missing": [] },
  "commit_hash": ""
}
```

---

## Test-Struktur Beispiele

### Python/pytest: Acceptance Test

```python
"""
Acceptance Tests fuer {Slice-Name}.
Abgeleitet aus GIVEN/WHEN/THEN Acceptance Criteria in der Slice-Spec.
"""
import pytest

class TestSliceAcceptance:
    """Acceptance Tests - 1:1 aus Slice-Spec ACs."""

    @pytest.mark.acceptance
    def test_ac_1_description(self):
        """AC-1: GIVEN {Vorbedingung} WHEN {Aktion} THEN {Ergebnis}."""
        # Arrange (GIVEN)
        ...
        # Act (WHEN)
        ...
        # Assert (THEN)
        ...

    @pytest.mark.acceptance
    def test_ac_2_description(self):
        """AC-2: GIVEN {Vorbedingung} WHEN {Aktion} THEN {Ergebnis}."""
        ...
```

### TypeScript/vitest: Acceptance Test

```typescript
/**
 * Acceptance Tests fuer {Slice-Name}.
 * Abgeleitet aus GIVEN/WHEN/THEN Acceptance Criteria in der Slice-Spec.
 */
import { describe, it, expect } from 'vitest'

describe('{Slice-Name} Acceptance', () => {
  it('AC-1: GIVEN {Vorbedingung} WHEN {Aktion} THEN {Ergebnis}', async () => {
    // Arrange (GIVEN)
    // Act (WHEN)
    // Assert (THEN)
  })

  it('AC-2: GIVEN {Vorbedingung} WHEN {Aktion} THEN {Ergebnis}', async () => {
    // ...
  })
})
```

---

## Test-Kategorien

| Kategorie | Python Marker | TypeScript | Scope |
|-----------|--------------|------------|-------|
| **Unit** | `@pytest.mark.unit` | `describe('unit')` | Isolierte Logik, alle Deps gemockt |
| **Integration** | `@pytest.mark.integration` | `describe('integration')` | Mit DB/Services |
| **Acceptance** | `@pytest.mark.acceptance` | `describe('acceptance')` | 1:1 aus GIVEN/WHEN/THEN |

---

## Qualitaets-Checkliste

Vor Abschluss pruefen:

- [ ] **AC-Coverage 100%** -- Jede GIVEN/WHEN/THEN hat einen Test
- [ ] **Test-File-Naming** -- Dateien folgen der Konvention (unit/integration/acceptance)
- [ ] **Docstrings** -- Acceptance Tests enthalten AC-ID und Original-Text
- [ ] **Stack erkannt** -- Test-Framework passt zum Repo
- [ ] **Kein Feature-Code** -- Nur Test-Dateien geschrieben
- [ ] **JSON Output** -- Letzter Block ist valides JSON mit allen Pflichtfeldern
- [ ] **Git Commit** -- Tests committed mit `test({slice_id}):` Prefix
- [ ] **Isolation** -- Tests unabhaengig voneinander
- [ ] **Readability** -- Test-Namen beschreiben Verhalten
```

---

## Deliverables (SCOPE SAFEGUARD)

<!-- DELIVERABLES_START -->
### Agent-Definition
- [ ] `.claude/agents/test-writer.md` -- Erweiterte Agent-Definition mit AC-Generation, Stack-Detection, JSON Output Contract, Test-File-Naming, AC-Coverage-Report (Modification der bestehenden Datei)

### Tests
- [ ] `tests/acceptance/test_slice_01_test_writer_enhancement.py` -- Acceptance Tests die pruefen ob die Agent-Definition alle erforderlichen Sections enthaelt
<!-- DELIVERABLES_END -->

---

## Definition of Done

- [x] Akzeptanzkriterien sind eindeutig und vollstaendig (8 ACs im GIVEN/WHEN/THEN Format)
- [x] JSON Output Contract definiert und dokumentiert
- [x] Stack-Detection Matrix definiert (Python, TypeScript, Go)
- [x] Test-File-Naming Konvention definiert (unit, integration, acceptance)
- [x] AC-Coverage Konzept definiert (total, covered, missing)
- [x] Agent-Separation Rule enforced (NUR Tests, KEIN Feature-Code)
- [ ] Rollout: Agent-Definition ersetzt bestehende test-writer.md

---

## Links

- Bestehender Agent: `.claude/agents/test-writer.md`
- Architecture: `specs/2026-02-14-orchestrator-robust-testing/architecture.md`
- Discovery: `specs/2026-02-14-orchestrator-robust-testing/discovery.md`
- Backend-Kern Slice-Specs (Referenz fuer ACs): `specs/phase-1/2026-02-13-backend-kern/slices/`

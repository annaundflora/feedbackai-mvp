# Slice 4: Planner und Gate 2 inhaltlich verbessern

> **Slice 4 von 4** fuer `Lean Testing Pipeline`
>
> | Navigation | |
> |------------|---|
> | **Vorheriger:** | `slice-03-orchestrator-pipeline.md` |
> | **Naechster:** | -- |

---

## Metadata (fuer Orchestrator)

| Key | Value |
|-----|-------|
| **ID** | `slice-04-planner-gate-improvements` |
| **Test** | `cd backend && python -m pytest tests/acceptance/test_slice_04_planner_gate_improvements.py -v` |
| **E2E** | `false` |
| **Dependencies** | `["slice-03-orchestrator-pipeline"]` |

---

## Slice-Uebersicht

| # | Slice | Status | Datei |
|---|-------|--------|-------|
| 1 | Test-Writer Agent Enhancement | Ready | `slice-01-test-writer-enhancement.md` |
| 2 | Test-Validator Agent | Ready | `slice-02-test-validator-agent.md` |
| 3 | Orchestrator Pipeline | Ready | `slice-03-orchestrator-pipeline.md` |
| 4 | Planner & Gate Improvements | Ready | `slice-04-planner-gate-improvements.md` |

---

## Kontext & Ziel

Drei bestehende Dateien muessen angepasst werden, damit die Lean Testing Pipeline vollstaendig ist:

1. **Gate 2 (slice-compliance.md)** prueft aktuell nur ob Template-Sections existieren ("Existiert Section X?" = Template-Checkbox). LLMs schreiben immer alle Sections -- das hat nie was gefangen. Stattdessen muss Gate 2 **inhaltlich** pruefen: Sind ACs testbar und spezifisch genug fuer den Test-Writer? Passen Code Examples zur Architecture? Stimmen Agent Output Contracts (JSON-Felder, Typen)? Zusaetzlich wird Max Retry von 3 auf 1 reduziert (Business Rule 14).

2. **Slice-Writer (slice-writer.md)** erkennt aktuell den Stack nicht automatisch und generiert keine Test-Strategy Metadata. Er muss erweitert werden um Stack-Detection (anhand Indicator-Dateien wie `pyproject.toml`, `package.json`) und um die Generierung von Test-Strategy Metadata in jeder Slice-Spec (stack, test_command, integration_command, acceptance_command, start_command, health_endpoint, mocking_strategy).

3. **plan-spec Template (plan-spec.md)** hat keine Test-Strategy Section. Diese muss als neue Pflicht-Section hinzugefuegt werden, damit der Slice-Writer weiss wo er die Test-Strategy Metadata hinschreiben soll und Gate 2 sie pruefen kann.

---

## Technische Umsetzung

### Architektur-Kontext (aus architecture.md)

> **Quelle:** `architecture.md` -> Test-Strategy Metadata, Stack-Detection Matrix, Agent Definitions (Geaenderte Planner/Gate Agents), Geaenderte Templates

```
Planner (Slice-Writer Agent)
  |
  v
Stack-Detection: pyproject.toml? package.json? go.mod?
  |
  v
Test-Strategy Metadata generieren:
  - stack: "python-fastapi"
  - test_command: "python -m pytest tests/unit/ -v"
  - integration_command: "python -m pytest tests/integration/ -v"
  - acceptance_command: "python -m pytest tests/acceptance/ -v"
  - start_command: "uvicorn app.main:app --host 0.0.0.0 --port 8000"
  - health_endpoint: "http://localhost:8000/health"
  - mocking_strategy: "mock_external"
  |
  v
In Slice-Spec (plan-spec Template) -> Test-Strategy Section
  |
  v
Gate 2 (slice-compliance.md) prueft INHALTLICH:
  - Sind ACs testbar? (GIVEN/WHEN/THEN mit konkreten Werten)
  - Passen Code Examples zur Architecture?
  - Stimmt Test-Strategy mit erkanntem Stack?
  - Sind Agent Output Contracts korrekt (JSON-Felder, Typen)?
```

### 1. Architektur-Impact

| Layer | Aenderungen |
|-------|------------|
| `.claude/agents/slice-writer.md` | Modification: Stack-Detection Section, Test-Strategy Metadata Generierung |
| `.claude/agents/slice-compliance.md` | Modification: Inhaltliche Pruefung statt Template-Checkboxen, Max 1 Retry |
| `.claude/templates/plan-spec.md` | Modification: Test-Strategy Section als neue Pflicht-Section |

### 2. Datenfluss

```
Codebase Indicator-Dateien (pyproject.toml, package.json, go.mod)
  |
  v
[Slice-Writer: Stack-Detection]
  |-- Liest Indicator-Dateien im Repo-Root
  |-- Bestimmt Stack anhand Detection-Matrix
  |
  v
[Slice-Writer: Test-Strategy Metadata]
  |-- Generiert Commands basierend auf Stack
  |-- Schreibt Metadata in die Slice-Spec (Test-Strategy Section)
  |
  v
[Gate 2: Inhaltliche Pruefung]
  |-- Prueft AC-Qualitaet: Sind ACs testbar? Spezifisch genug fuer Test-Writer?
  |-- Prueft Code Examples: Passen sie zur Architecture?
  |-- Prueft Test-Strategy: Stimmt Stack? Sind Commands vollstaendig?
  |-- Prueft Agent Output Contracts: JSON-Felder und Typen korrekt?
  |-- Max 1 Retry bei FAILED
  |
  v
APPROVED / FAILED (max 1 Retry)
```

### 3. slice-writer.md Aenderungen

#### 3.1 Stack-Detection (NEU)

Neue Section im Slice-Writer Agent, die VOR dem Schreiben des Slices ausgefuehrt wird:

```markdown
## Stack-Detection (PFLICHT vor Slice-Write)

Erkenne den Stack automatisch anhand von Indicator-Dateien im Repo:

1. Lies das Repo-Root-Verzeichnis
2. Pruefe auf Indicator-Dateien:

| Indicator File | Stack | Test Framework | Test Command | Start Command | Health Endpoint |
|----------------|-------|---------------|-------------|---------------|-----------------|
| `pyproject.toml` + fastapi dep | python-fastapi | pytest | `python -m pytest {path} -v` | `uvicorn app.main:app --host 0.0.0.0 --port 8000` | `http://localhost:8000/health` |
| `requirements.txt` + fastapi | python-fastapi | pytest | `python -m pytest {path} -v` | `uvicorn app.main:app --host 0.0.0.0 --port 8000` | `http://localhost:8000/health` |
| `pyproject.toml` + django dep | python-django | pytest | `python -m pytest {path} -v` | `python manage.py runserver` | `http://localhost:8000/health` |
| `package.json` + next dep | typescript-nextjs | vitest + playwright | `pnpm test {path}` | `pnpm dev` | `http://localhost:3000/api/health` |
| `package.json` + express dep | typescript-express | vitest | `pnpm test {path}` | `node server.js` | `http://localhost:3000/health` |
| `go.mod` | go | go test | `go test {path}` | `go run .` | `http://localhost:8080/health` |

3. Falls kein Stack erkannt: Frage User via AskUserQuestion
4. Verwende den erkannten Stack fuer Test-Strategy Metadata
```

#### 3.2 Test-Strategy Metadata Generierung (NEU)

Neue Section im Slice-Writer Agent, die in jeden Slice eine Test-Strategy Section einfuegt:

```markdown
## Test-Strategy Metadata (PFLICHT in jeder Slice-Spec)

Generiere fuer jeden Slice die Test-Strategy Metadata basierend auf dem erkannten Stack:

| Key | Value | Description |
|-----|-------|-------------|
| `stack` | Auto-detected | z.B. "python-fastapi", "typescript-nextjs" |
| `test_command` | Generated | Unit Test Command (z.B. `python -m pytest tests/unit/ -v`) |
| `integration_command` | Generated | Integration Test Command |
| `acceptance_command` | Generated | Acceptance Test Command |
| `start_command` | Generated | App Start Command |
| `health_endpoint` | Generated | Health-Check URL |
| `mocking_strategy` | Determined | `mock_external`, `no_mocks`, `test_containers` |

Die Metadata wird in die "Test-Strategy" Section der Slice-Spec geschrieben (gemaess plan-spec Template).

Mocking-Strategy Regeln:
- `mock_external`: Default. Externe APIs/Services werden gemockt (Unit + Acceptance Tests)
- `no_mocks`: Kein Mocking noetig (reine Business-Logik ohne Dependencies)
- `test_containers`: Integration Tests mit echten Services (Docker)
```

#### 3.3 Delta zum bestehenden Agent

| Section | Aenderung | Typ |
|---------|-----------|-----|
| Workflow Phase 2 (Codebase-Recherche) | Stack-Detection als ersten Schritt hinzufuegen | EXTEND |
| Workflow Phase 3 (Slice schreiben) | Test-Strategy Metadata als Pflicht-Output hinzufuegen | EXTEND |
| Pflicht-Sections | Test-Strategy Section als 7. Pflicht-Section hinzufuegen | EXTEND |
| Qualitaets-Checkliste | Test-Strategy Checkliste hinzufuegen | EXTEND |
| Stack-Detection Section | Komplett neue Section nach Workflow | ADD |
| Test-Strategy Metadata Section | Komplett neue Section nach Stack-Detection | ADD |
| Fundamentale Regeln | Stack-Detection als Regel hinzufuegen | EXTEND |

### 4. slice-compliance.md Aenderungen

#### 4.1 Inhaltliche Pruefung statt Template-Checkboxen (ERSETZT)

Die bisherige "Template-Compliance" Section (Phase 2, Check 0) wird ERSETZT durch inhaltliche Pruefung:

```markdown
## Inhaltliche Pruefung (ERSETZT Template-Checkboxen)

### AC-Qualitaets-Check (NEU - wichtigster Check)

Pruefe JEDES Acceptance Criterion:

| Qualitaets-Merkmal | Pruef-Frage | Blocking wenn |
|---------------------|-------------|---------------|
| **Testbarkeit** | Kann der Test-Writer hieraus einen automatisierten Test schreiben? | AC ist vage ("System funktioniert korrekt") |
| **Spezifitaet** | Enthaelt das AC konkrete Werte, Status-Codes, Fehlermeldungen? | AC hat keine konkreten Werte ("sollte erfolgreich sein") |
| **GIVEN Vollstaendigkeit** | Ist die Vorbedingung praezise genug um sie im Test aufzubauen? | GIVEN ist unklar ("GIVEN ein User") statt ("GIVEN ein User mit Rolle admin") |
| **WHEN Eindeutigkeit** | Ist die Aktion eindeutig ausfuehrbar? | WHEN beschreibt mehrere Aktionen gleichzeitig |
| **THEN Messbarkeit** | Ist das Ergebnis maschinell pruefbar (exit_code, HTTP Status, JSON-Feld)? | THEN ist subjektiv ("UI sieht gut aus") |

### Code Example Korrektheit (NEU)

Pruefe JEDES Code Example gegen die Architecture:

| Pruef-Aspekt | Was pruefen | Blocking wenn |
|--------------|-------------|---------------|
| **Types/Interfaces** | Stimmen die Types im Code Example mit architecture.md ueberein? | Feld-Namen, Typen oder Required/Optional stimmen nicht |
| **Import-Pfade** | Sind die Import-Pfade realistisch? | Import-Pfade referenzieren nicht-existierende Module |
| **Funktions-Signaturen** | Stimmen Parameter und Return-Types? | Signatur weicht von Architecture ab |
| **Agent Output Contract** | Stimmen JSON-Felder und Typen mit architecture.md Agent Interfaces ueberein? | Fehlende Pflichtfelder, falsche Typen |

### Test-Strategy Pruefung (NEU)

Pruefe die Test-Strategy Section:

| Pruef-Aspekt | Was pruefen | Blocking wenn |
|--------------|-------------|---------------|
| **Stack korrekt** | Stimmt der erkannte Stack mit den Repo-Indikatoren ueberein? | Stack ist falsch oder fehlt |
| **Commands vollstaendig** | Sind alle 3 Test-Commands (unit, integration, acceptance) definiert? | Ein Command fehlt |
| **Start-Command** | Passt der Start-Command zum erkannten Stack? | Start-Command passt nicht zum Stack |
| **Health-Endpoint** | Passt der Health-Endpoint zum erkannten Stack? | Health-Endpoint passt nicht zum Stack |
| **Mocking-Strategy** | Ist eine Mocking-Strategy definiert? | Mocking-Strategy fehlt |
```

#### 4.2 Max 1 Retry (AENDERUNG)

Bisher hatte Gate 2 implizit 3 Retries (wie alle Gates). Neu: Max 1 Retry.

Dies wird durch eine explizite Regel in der Agent-Definition erzwungen:

```markdown
## Retry-Regel

**Max 1 Retry.** Wenn der Slice nach einem Fix-Versuch immer noch FAILED ist, wird der Planner HARD-STOPped.
Begruendung: Gate 2 prueft Spec-Qualitaet. Wenn 2 Versuche nicht reichen, muss der User die Spec ueberarbeiten.
```

#### 4.3 Beibehaltene Checks

Folgende bestehende Checks bleiben erhalten (sie pruefen bereits inhaltlich):
- A) Architecture Compliance (Schema, API, Security)
- B) Wireframe Compliance (UI Elements, States, Visual Specs)
- C) Integration Contract Check (Inputs, Outputs, Consumer-Deliverable-Traceability, AC-Deliverable-Konsistenz)
- D) Code Example Compliance (wird VERSCHAERFT durch 4.1)
- E) Test Coverage Check
- F) Discovery Compliance

#### 4.4 Entfernte/Ersetzte Checks

| Bisheriger Check | Aenderung | Begruendung |
|------------------|-----------|-------------|
| Check 0: Template-Compliance (6 Pattern-Suchen) | ERSETZT durch inhaltliche AC-Qualitaets-Check | LLMs schreiben immer alle Sections. "Existiert Section X?" hat nie was gefangen. |

#### 4.5 Delta zum bestehenden Agent

| Section | Aenderung | Typ |
|---------|-----------|-----|
| Phase 2, Check 0 (Template-Compliance) | Ersetzt durch AC-Qualitaets-Check + Code Example Korrektheit + Test-Strategy Pruefung | REPLACE |
| Phase 2, Check D (Code Example Compliance) | Verschaerft: Agent Output Contract Pruefung hinzufuegen | EXTEND |
| Output Format, Section 0 | Template-Compliance Tabelle ersetzen durch Inhaltliche Pruefung Report | REPLACE |
| Retry-Regel | Neue Section: Max 1 Retry (explizit) | ADD |
| Zweck/Beschreibung | Fokus auf "inhaltliche Pruefung" statt "Template-Checkboxen" | MODIFY |

### 5. plan-spec.md Aenderungen

#### 5.1 Test-Strategy Section (NEU)

Neue Pflicht-Section im Template, eingefuegt nach "Metadata" und vor "Slice-Uebersicht":

```markdown
## Test-Strategy (fuer Orchestrator Pipeline)

> **Quelle:** Auto-detected vom Slice-Writer Agent basierend auf Repo-Indikatoren.
> Diese Section wird vom Test-Writer und Test-Validator konsumiert.

| Key | Value |
|-----|-------|
| **Stack** | `{auto-detected}` |
| **Test Command** | `{unit test command}` |
| **Integration Command** | `{integration test command}` |
| **Acceptance Command** | `{acceptance test command}` |
| **Start Command** | `{app start command}` |
| **Health Endpoint** | `{health check URL}` |
| **Mocking Strategy** | `{mock_external / no_mocks / test_containers}` |

**Erklaerung:**
- **Stack**: Automatisch erkannter Tech-Stack (z.B. "python-fastapi", "typescript-nextjs")
- **Test Command**: Command fuer Unit Tests (z.B. `python -m pytest tests/unit/ -v`)
- **Integration Command**: Command fuer Integration Tests
- **Acceptance Command**: Command fuer Acceptance Tests
- **Start Command**: Command um die App zu starten (fuer Smoke Test)
- **Health Endpoint**: URL fuer Health-Check (Smoke Test)
- **Mocking Strategy**: Mocking-Ansatz fuer Tests
```

#### 5.2 Metadata Erlaeuterung erweitern

Die bestehende "Erklaerung" unter Metadata erhaelt einen Verweis auf die Test-Strategy Section:

```markdown
- **Test-Strategy**: Siehe nachfolgende "Test-Strategy" Section fuer stack-spezifische Test-Commands
```

#### 5.3 Delta zum bestehenden Template

| Section | Aenderung | Typ |
|---------|-----------|-----|
| Nach Metadata, vor Slice-Uebersicht | Test-Strategy Section einfuegen | ADD |
| Metadata Erklaerung | Verweis auf Test-Strategy Section | EXTEND |

---

## Constraints & Hinweise

**Betrifft:**
- `.claude/agents/slice-writer.md` -- Modification (Stack-Detection, Test-Strategy Metadata)
- `.claude/agents/slice-compliance.md` -- Modification (Inhaltliche Pruefung, Max 1 Retry)
- `.claude/templates/plan-spec.md` -- Modification (Test-Strategy Section)

**Business Rules (aus Discovery):**
- Rule 9: Auto-Detection ist Pflicht (Stack erkennen, nicht hardcoded)
- Rule 10: Test-Commands sind generiert, nicht konfiguriert
- Rule 14: Gate 2 prueft inhaltlich (AC-Qualitaet, Code Example Korrektheit), Max 1 Retry
- Rule 15: Gate 3 bleibt wie bisher mit 3 Retries

**Abgrenzung:**
- Dieser Slice aendert NICHT den Test-Writer Agent (Slice 1)
- Dieser Slice aendert NICHT den Test-Validator Agent (Slice 2)
- Dieser Slice aendert NICHT den Orchestrator (Slice 3)
- Dieser Slice aendert NICHT den Debugger Agent
- Dieser Slice aendert NICHT den Slice-Implementer Agent

---

## Integration Contract (GATE 2 PFLICHT)

### Requires From Other Slices

| Slice | Resource | Type | Validation |
|-------|----------|------|------------|
| slice-03-orchestrator-pipeline | Orchestrator Pipeline | Command (.md) | Orchestrator konsumiert Test-Strategy Metadata aus Slice-Specs und gibt sie an Test-Writer/Test-Validator weiter |
| slice-01-test-writer-enhancement | Stack-Detection Matrix | Konvention | Slice-Writer muss gleiche Detection-Matrix verwenden wie Test-Writer/Test-Validator |
| slice-02-test-validator-agent | Test-Validator Input Format | Datenformat | Test-Strategy Metadata (Commands, Health-Endpoint) muessen zum Test-Validator Input passen |

### Provides To Other Slices

| Resource | Type | Consumer | Interface |
|----------|------|----------|-----------|
| Erweiterte Slice-Specs (mit Test-Strategy) | Datenformat | Orchestrator (Slice 3) | Slice-Specs enthalten Test-Strategy Section mit stack, test_command, integration_command, acceptance_command, start_command, health_endpoint, mocking_strategy |
| Inhaltlich gepruefter Gate 2 | Quality Gate | Planner Pipeline | Gate 2 prueft AC-Qualitaet, Code Example Korrektheit, Test-Strategy Vollstaendigkeit |
| plan-spec Template (mit Test-Strategy) | Template | Alle zukuenftigen Slice-Writer Aufrufe | Template enthaelt Test-Strategy Pflicht-Section |

### Integration Validation Tasks

- [ ] Stack-Detection Matrix in slice-writer.md stimmt mit architecture.md Stack-Detection Matrix ueberein
- [ ] Test-Strategy Metadata Felder stimmen mit architecture.md Test-Strategy Metadata Format ueberein
- [ ] plan-spec Template Test-Strategy Section hat alle 7 Felder (stack, test_command, integration_command, acceptance_command, start_command, health_endpoint, mocking_strategy)
- [ ] Gate 2 prueft Test-Strategy Section inhaltlich (nicht nur Existenz)
- [ ] Gate 2 Max 1 Retry ist explizit definiert

---

## Acceptance Criteria

1) GIVEN der Slice-Writer Agent wird aufgerufen um einen Slice zu schreiben
   WHEN er das Repo analysiert und `pyproject.toml` mit fastapi Dependency findet
   THEN erkennt er den Stack als "python-fastapi" und generiert die passenden Test-Commands (`python -m pytest tests/unit/ -v`, `python -m pytest tests/integration/ -v`, `python -m pytest tests/acceptance/ -v`), Start-Command (`uvicorn app.main:app --host 0.0.0.0 --port 8000`) und Health-Endpoint (`http://localhost:8000/health`)

2) GIVEN der Slice-Writer Agent wird aufgerufen um einen Slice zu schreiben
   WHEN er das Repo analysiert und `package.json` mit next Dependency findet
   THEN erkennt er den Stack als "typescript-nextjs" und generiert die passenden Test-Commands (`pnpm test tests/unit/`, `pnpm test tests/integration/`, `pnpm test tests/acceptance/`), Start-Command (`pnpm dev`) und Health-Endpoint (`http://localhost:3000/api/health`)

3) GIVEN der Slice-Writer Agent hat den Stack erkannt
   WHEN er eine Slice-Spec schreibt
   THEN enthaelt die Slice-Spec eine "Test-Strategy" Section mit den 7 Pflichtfeldern: stack, test_command, integration_command, acceptance_command, start_command, health_endpoint, mocking_strategy

4) GIVEN der Gate 2 Compliance Agent prueft einen Slice mit dem AC "GIVEN ein User WHEN er klickt THEN funktioniert es"
   WHEN er die AC-Qualitaet bewertet
   THEN markiert er dieses AC als BLOCKING weil es nicht testbar ist (keine konkreten Werte, kein messbares Ergebnis) und gibt eine konkrete Verbesserung an (z.B. "THEN wird HTTP 200 mit `{"status": "ok"}` zurueckgegeben")

5) GIVEN der Gate 2 Compliance Agent prueft einen Slice mit Code Examples
   WHEN ein Code Example einen Type verwendet der nicht in architecture.md definiert ist
   THEN markiert er dies als BLOCKING mit Verweis auf den korrekten Type aus architecture.md

6) GIVEN der Gate 2 Compliance Agent prueft einen Slice mit Test-Strategy Section
   WHEN der Stack "python-fastapi" ist aber der Start-Command "pnpm dev" enthaelt
   THEN markiert er dies als BLOCKING weil der Start-Command nicht zum erkannten Stack passt

7) GIVEN der Gate 2 Compliance Agent hat einen Slice als FAILED markiert und der Slice-Writer hat einen Fix-Versuch gemacht
   WHEN der Slice nach dem Fix immer noch FAILED ist
   THEN stoppt der Planner mit HARD STOP (Max 1 Retry, kein zweiter Fix-Versuch) und meldet dem User dass die Spec ueberarbeitet werden muss

8) GIVEN das plan-spec Template
   WHEN ein Slice-Writer es verwendet
   THEN enthaelt es eine "Test-Strategy" Section nach der Metadata Section mit den Feldern stack, test_command, integration_command, acceptance_command, start_command, health_endpoint und mocking_strategy

9) GIVEN der Slice-Writer Agent und kein Stack-Indicator wird im Repo gefunden
   WHEN er den Stack erkennen soll
   THEN fragt er den User via AskUserQuestion nach dem Stack (Fallback, kein hardcoded Default)

10) GIVEN der Gate 2 Compliance Agent prueft einen Slice dessen Code Example einen JSON Output Contract enthaelt
    WHEN die JSON-Felder nicht mit den in architecture.md definierten Agent Interfaces uebereinstimmen (z.B. fehlendes Pflichtfeld `ac_coverage`)
    THEN markiert er dies als BLOCKING mit Auflistung der fehlenden/falschen Felder

---

## Testfaelle

### Test-Datei

`tests/acceptance/test_slice_04_planner_gate_improvements.py`

**Hinweis:** Da dieser Slice drei Markdown-Dateien (2 Agent-Definitionen + 1 Template) aendert und keinen ausfuehrbaren Code, sind die Tests Validierungen der Markdown-Dateien auf strukturelle Korrektheit und inhaltliche Vollstaendigkeit.

<test_spec>
```python
# tests/acceptance/test_slice_04_planner_gate_improvements.py
"""
Acceptance Tests fuer Slice 04: Planner & Gate Improvements.

Validiert dass slice-writer.md, slice-compliance.md und plan-spec.md
korrekt erweitert/angepasst wurden.
"""
import pytest
from pathlib import Path

SLICE_WRITER_FILE = Path(".claude/agents/slice-writer.md")
SLICE_COMPLIANCE_FILE = Path(".claude/agents/slice-compliance.md")
PLAN_SPEC_FILE = Path(".claude/templates/plan-spec.md")


@pytest.fixture
def slice_writer_content():
    """Liest den Slice-Writer Agent-Inhalt."""
    assert SLICE_WRITER_FILE.exists(), f"Agent-Datei {SLICE_WRITER_FILE} existiert nicht"
    return SLICE_WRITER_FILE.read_text(encoding="utf-8")


@pytest.fixture
def compliance_content():
    """Liest den Slice-Compliance Agent-Inhalt."""
    assert SLICE_COMPLIANCE_FILE.exists(), f"Agent-Datei {SLICE_COMPLIANCE_FILE} existiert nicht"
    return SLICE_COMPLIANCE_FILE.read_text(encoding="utf-8")


@pytest.fixture
def plan_spec_content():
    """Liest das plan-spec Template."""
    assert PLAN_SPEC_FILE.exists(), f"Template-Datei {PLAN_SPEC_FILE} existiert nicht"
    return PLAN_SPEC_FILE.read_text(encoding="utf-8")


class TestStackDetectionPythonFastAPI:
    """AC-1: Stack-Detection fuer Python/FastAPI."""

    @pytest.mark.acceptance
    def test_ac_1_python_fastapi_detection(self, slice_writer_content):
        """AC-1: GIVEN pyproject.toml + fastapi WHEN Stack erkannt THEN python-fastapi mit korrekten Commands."""
        assert "pyproject.toml" in slice_writer_content, \
            "Slice-Writer muss pyproject.toml als Stack-Indicator enthalten"
        assert "fastapi" in slice_writer_content.lower(), \
            "Slice-Writer muss fastapi als Dependency-Indicator enthalten"
        assert "python-fastapi" in slice_writer_content, \
            "Slice-Writer muss 'python-fastapi' als Stack-Bezeichnung enthalten"
        assert "python -m pytest" in slice_writer_content, \
            "Slice-Writer muss pytest Test-Command fuer Python enthalten"
        assert "uvicorn" in slice_writer_content, \
            "Slice-Writer muss uvicorn Start-Command fuer FastAPI enthalten"
        assert "localhost:8000/health" in slice_writer_content, \
            "Slice-Writer muss Health-Endpoint fuer FastAPI enthalten"


class TestStackDetectionTypeScript:
    """AC-2: Stack-Detection fuer TypeScript/Next.js."""

    @pytest.mark.acceptance
    def test_ac_2_typescript_nextjs_detection(self, slice_writer_content):
        """AC-2: GIVEN package.json + next WHEN Stack erkannt THEN typescript-nextjs mit korrekten Commands."""
        assert "package.json" in slice_writer_content, \
            "Slice-Writer muss package.json als Stack-Indicator enthalten"
        assert "typescript-nextjs" in slice_writer_content, \
            "Slice-Writer muss 'typescript-nextjs' als Stack-Bezeichnung enthalten"
        assert "pnpm test" in slice_writer_content or "pnpm vitest" in slice_writer_content, \
            "Slice-Writer muss pnpm Test-Command fuer TypeScript enthalten"
        assert "pnpm dev" in slice_writer_content, \
            "Slice-Writer muss pnpm dev Start-Command fuer Next.js enthalten"
        assert "localhost:3000" in slice_writer_content, \
            "Slice-Writer muss Health-Endpoint fuer Next.js enthalten"


class TestTestStrategyInSliceSpec:
    """AC-3: Test-Strategy Section in Slice-Spec."""

    @pytest.mark.acceptance
    def test_ac_3_test_strategy_metadata_fields(self, slice_writer_content):
        """AC-3: GIVEN Stack erkannt WHEN Slice geschrieben THEN Test-Strategy mit 7 Pflichtfeldern."""
        assert "test-strategy" in slice_writer_content.lower() or "test_strategy" in slice_writer_content.lower() or "Test-Strategy" in slice_writer_content, \
            "Slice-Writer muss Test-Strategy als Konzept enthalten"
        # Pruefe alle 7 Pflichtfelder
        for field in ["stack", "test_command", "integration_command", "acceptance_command", "start_command", "health_endpoint", "mocking_strategy"]:
            assert field in slice_writer_content, \
                f"Slice-Writer muss Feld '{field}' in Test-Strategy Metadata definieren"


class TestGate2ACQuality:
    """AC-4: Gate 2 prueft AC-Qualitaet inhaltlich."""

    @pytest.mark.acceptance
    def test_ac_4_ac_quality_check(self, compliance_content):
        """AC-4: GIVEN vages AC WHEN Gate 2 prueft THEN BLOCKING weil nicht testbar."""
        content_lower = compliance_content.lower()
        assert "testbar" in content_lower or "testable" in content_lower, \
            "Gate 2 muss ACs auf Testbarkeit pruefen"
        assert "spezifisch" in content_lower or "konkret" in content_lower or "specific" in content_lower, \
            "Gate 2 muss ACs auf Spezifitaet pruefen"
        assert "messbar" in content_lower or "measurable" in content_lower or "maschinell" in content_lower, \
            "Gate 2 muss ACs auf Messbarkeit pruefen"
        # Pruefe dass die alte Template-Checkbox-Methode ersetzt wurde
        assert "inhaltlich" in content_lower or "ac-qualit" in content_lower, \
            "Gate 2 muss auf inhaltliche Pruefung umgestellt sein"


class TestGate2CodeExampleKorrektheit:
    """AC-5: Gate 2 prueft Code Examples gegen Architecture."""

    @pytest.mark.acceptance
    def test_ac_5_code_example_architecture_check(self, compliance_content):
        """AC-5: GIVEN Code Example mit falschem Type WHEN Gate 2 prueft THEN BLOCKING."""
        content_lower = compliance_content.lower()
        assert "architecture" in content_lower, \
            "Gate 2 muss Code Examples gegen Architecture pruefen"
        assert "type" in content_lower or "interface" in content_lower, \
            "Gate 2 muss Types/Interfaces in Code Examples pruefen"
        assert "import" in content_lower or "signatur" in content_lower or "signature" in content_lower, \
            "Gate 2 muss Import-Pfade oder Funktions-Signaturen pruefen"


class TestGate2TestStrategyCheck:
    """AC-6: Gate 2 prueft Test-Strategy Konsistenz."""

    @pytest.mark.acceptance
    def test_ac_6_test_strategy_consistency(self, compliance_content):
        """AC-6: GIVEN Stack python-fastapi aber Start-Command pnpm dev WHEN Gate 2 prueft THEN BLOCKING."""
        content_lower = compliance_content.lower()
        assert "test-strategy" in content_lower or "test_strategy" in content_lower or "test strategy" in content_lower, \
            "Gate 2 muss Test-Strategy Section pruefen"
        assert "stack" in content_lower, \
            "Gate 2 muss Stack-Konsistenz pruefen"
        assert "command" in content_lower, \
            "Gate 2 muss Commands auf Konsistenz mit Stack pruefen"


class TestGate2MaxOneRetry:
    """AC-7: Gate 2 hat Max 1 Retry."""

    @pytest.mark.acceptance
    def test_ac_7_max_one_retry(self, compliance_content):
        """AC-7: GIVEN Slice nach Fix immer noch FAILED WHEN Gate 2 THEN HARD STOP (Max 1 Retry)."""
        content_lower = compliance_content.lower()
        assert "1 retry" in content_lower or "max 1" in content_lower or "einen retry" in content_lower or "1 fix" in content_lower, \
            "Gate 2 muss Max 1 Retry explizit definieren"
        # Stelle sicher dass es NICHT 3 Retries hat
        assert "3 retries" not in content_lower or "gate 3" in content_lower, \
            "Gate 2 darf NICHT 3 Retries haben (das ist Gate 3)"


class TestPlanSpecTestStrategySection:
    """AC-8: plan-spec Template enthaelt Test-Strategy Section."""

    @pytest.mark.acceptance
    def test_ac_8_template_test_strategy(self, plan_spec_content):
        """AC-8: GIVEN plan-spec Template WHEN Slice-Writer nutzt es THEN Test-Strategy Section vorhanden."""
        assert "Test-Strategy" in plan_spec_content or "test-strategy" in plan_spec_content.lower(), \
            "plan-spec Template muss Test-Strategy Section enthalten"
        # Pruefe alle 7 Felder im Template
        for field in ["Stack", "Test Command", "Integration Command", "Acceptance Command", "Start Command", "Health Endpoint", "Mocking Strategy"]:
            assert field in plan_spec_content, \
                f"plan-spec Template muss Feld '{field}' in Test-Strategy Section enthalten"


class TestStackDetectionFallback:
    """AC-9: Fallback bei unbekanntem Stack."""

    @pytest.mark.acceptance
    def test_ac_9_fallback_ask_user(self, slice_writer_content):
        """AC-9: GIVEN kein Stack-Indicator WHEN Stack-Detection THEN AskUserQuestion Fallback."""
        content_lower = slice_writer_content.lower()
        assert "askuserquestion" in content_lower or "ask" in content_lower or "frag" in content_lower, \
            "Slice-Writer muss Fallback haben wenn kein Stack erkannt wird (User fragen)"
        assert "fallback" in content_lower or "nicht erkannt" in content_lower or "kein stack" in content_lower, \
            "Slice-Writer muss den Fallback-Fall beschreiben"


class TestGate2AgentOutputContract:
    """AC-10: Gate 2 prueft Agent Output Contracts."""

    @pytest.mark.acceptance
    def test_ac_10_agent_output_contract_check(self, compliance_content):
        """AC-10: GIVEN Code Example mit JSON Output Contract WHEN Felder fehlen THEN BLOCKING."""
        content_lower = compliance_content.lower()
        assert "json" in content_lower, \
            "Gate 2 muss JSON Output Contracts pruefen"
        assert "output contract" in content_lower or "agent output" in content_lower or "pflichtfeld" in content_lower or "agent interface" in content_lower, \
            "Gate 2 muss Agent Output Contract Felder pruefen"
```
</test_spec>

---

## Code Examples (MANDATORY - GATE 2 PFLICHT)

> **KRITISCH:** Alle Code-Beispiele in diesem Dokument sind **PFLICHT-Deliverables**.
> Der Gate 2 Compliance Agent prueft, dass jedes Code-Beispiel implementiert wird.
> Abweichung nur mit expliziter Begruendung im Commit erlaubt.

| Code Example | Section | Mandatory | Notes |
|--------------|---------|-----------|-------|
| Stack-Detection Matrix (slice-writer.md) | Technische Umsetzung 3.1 | YES | Tabelle mit 6 Stack-Indikatoren |
| Test-Strategy Metadata Format (slice-writer.md) | Technische Umsetzung 3.2 | YES | 7-Felder-Tabelle mit Erklaerung |
| AC-Qualitaets-Check (slice-compliance.md) | Technische Umsetzung 4.1 | YES | Tabelle mit 5 Qualitaets-Merkmalen |
| Code Example Korrektheit Check (slice-compliance.md) | Technische Umsetzung 4.1 | YES | Tabelle mit 4 Pruef-Aspekten |
| Test-Strategy Pruefung (slice-compliance.md) | Technische Umsetzung 4.1 | YES | Tabelle mit 5 Pruef-Aspekten |
| Max 1 Retry Regel (slice-compliance.md) | Technische Umsetzung 4.2 | YES | Explizite Retry-Regel |
| Test-Strategy Template Section (plan-spec.md) | Technische Umsetzung 5.1 | YES | 7-Felder-Tabelle mit Erklaerung im Template |

### slice-writer.md: Stack-Detection Section

Der Implementer MUSS die folgende Section in `slice-writer.md` einfuegen:

```markdown
## Stack-Detection (PFLICHT vor Slice-Write)

Erkenne den Stack automatisch anhand von Indicator-Dateien im Repo:

1. Lies das Repo-Root-Verzeichnis mit `Glob("*")` und `Glob("*/package.json")`
2. Pruefe auf Indicator-Dateien:

| Indicator File | Stack | Test Framework | Test Command | Start Command | Health Endpoint |
|----------------|-------|---------------|-------------|---------------|-----------------|
| `pyproject.toml` + fastapi dep | python-fastapi | pytest | `python -m pytest {path} -v` | `uvicorn app.main:app --host 0.0.0.0 --port 8000` | `http://localhost:8000/health` |
| `requirements.txt` + fastapi | python-fastapi | pytest | `python -m pytest {path} -v` | `uvicorn app.main:app --host 0.0.0.0 --port 8000` | `http://localhost:8000/health` |
| `pyproject.toml` + django dep | python-django | pytest | `python -m pytest {path} -v` | `python manage.py runserver` | `http://localhost:8000/health` |
| `package.json` + next dep | typescript-nextjs | vitest + playwright | `pnpm test {path}` | `pnpm dev` | `http://localhost:3000/api/health` |
| `package.json` + express dep | typescript-express | vitest | `pnpm test {path}` | `node server.js` | `http://localhost:3000/health` |
| `go.mod` | go | go test | `go test {path}` | `go run .` | `http://localhost:8080/health` |

3. Falls kein Stack erkannt: Frage User via AskUserQuestion nach dem Stack
4. Verwende den erkannten Stack fuer Test-Strategy Metadata in der Slice-Spec
```

### slice-writer.md: Test-Strategy Metadata Section

Der Implementer MUSS die folgende Section in `slice-writer.md` einfuegen:

```markdown
## Test-Strategy Metadata (PFLICHT in jeder Slice-Spec)

Generiere fuer jeden Slice die Test-Strategy Metadata basierend auf dem erkannten Stack.
Schreibe diese in die "Test-Strategy" Section der Slice-Spec:

| Key | Value | Description |
|-----|-------|-------------|
| `stack` | Auto-detected | z.B. "python-fastapi", "typescript-nextjs" |
| `test_command` | Generated | Unit Test Command |
| `integration_command` | Generated | Integration Test Command |
| `acceptance_command` | Generated | Acceptance Test Command |
| `start_command` | Generated | App Start Command |
| `health_endpoint` | Generated | Health-Check URL |
| `mocking_strategy` | Determined | `mock_external`, `no_mocks`, `test_containers` |

Mocking-Strategy Regeln:
- `mock_external`: Default. Externe APIs/Services werden gemockt
- `no_mocks`: Kein Mocking noetig (reine Business-Logik)
- `test_containers`: Integration Tests mit echten Services (Docker)
```

### slice-compliance.md: Inhaltliche Pruefung

Der Implementer MUSS die Template-Compliance Section in `slice-compliance.md` ERSETZEN durch:

```markdown
#### 0) Inhaltliche Pruefung (ERSETZT Template-Checkboxen)

**KRITISCH: Fokus auf INHALT, nicht auf Template-Existenz.**

##### AC-Qualitaets-Check

Pruefe JEDES Acceptance Criterion:

| Qualitaets-Merkmal | Pruef-Frage | Blocking wenn |
|---------------------|-------------|---------------|
| **Testbarkeit** | Kann der Test-Writer hieraus einen automatisierten Test schreiben? | AC ist vage ("System funktioniert korrekt") |
| **Spezifitaet** | Enthaelt das AC konkrete Werte, Status-Codes, Fehlermeldungen? | AC hat keine konkreten Werte ("sollte erfolgreich sein") |
| **GIVEN Vollstaendigkeit** | Ist die Vorbedingung praezise genug um sie im Test aufzubauen? | GIVEN ist unklar |
| **WHEN Eindeutigkeit** | Ist die Aktion eindeutig ausfuehrbar? | WHEN beschreibt mehrere Aktionen |
| **THEN Messbarkeit** | Ist das Ergebnis maschinell pruefbar? | THEN ist subjektiv |

##### Code Example Korrektheit

Pruefe JEDES Code Example gegen die Architecture:

| Pruef-Aspekt | Was pruefen | Blocking wenn |
|--------------|-------------|---------------|
| **Types/Interfaces** | Stimmen Types mit architecture.md ueberein? | Feld-Namen oder Typen stimmen nicht |
| **Import-Pfade** | Sind Import-Pfade realistisch? | Referenzieren nicht-existierende Module |
| **Funktions-Signaturen** | Stimmen Parameter und Return-Types? | Signatur weicht von Architecture ab |
| **Agent Output Contract** | Stimmen JSON-Felder mit architecture.md Agent Interfaces ueberein? | Fehlende Pflichtfelder |

##### Test-Strategy Pruefung

Pruefe die Test-Strategy Section:

| Pruef-Aspekt | Was pruefen | Blocking wenn |
|--------------|-------------|---------------|
| **Stack korrekt** | Stimmt Stack mit Repo-Indikatoren ueberein? | Stack falsch oder fehlt |
| **Commands vollstaendig** | Sind alle 3 Test-Commands definiert? | Ein Command fehlt |
| **Start-Command** | Passt zum erkannten Stack? | Start-Command passt nicht |
| **Health-Endpoint** | Passt zum erkannten Stack? | Health-Endpoint passt nicht |
| **Mocking-Strategy** | Ist definiert? | Fehlt |
```

### slice-compliance.md: Retry-Regel

Der Implementer MUSS die folgende Section in `slice-compliance.md` einfuegen:

```markdown
## Retry-Regel

**Max 1 Retry.** Wenn der Slice nach einem Fix-Versuch immer noch FAILED ist, wird der Planner HARD-STOPped.
Begruendung: Gate 2 prueft Spec-Qualitaet. Wenn 2 Versuche nicht reichen, muss der User die Spec ueberarbeiten.
```

### plan-spec.md: Test-Strategy Section

Der Implementer MUSS die folgende Section in `plan-spec.md` einfuegen (nach Metadata, vor Slice-Uebersicht):

```markdown
## Test-Strategy (fuer Orchestrator Pipeline)

> **Quelle:** Auto-detected vom Slice-Writer Agent basierend auf Repo-Indikatoren.
> Diese Section wird vom Test-Writer und Test-Validator konsumiert.

| Key | Value |
|-----|-------|
| **Stack** | `{auto-detected}` |
| **Test Command** | `{unit test command}` |
| **Integration Command** | `{integration test command}` |
| **Acceptance Command** | `{acceptance test command}` |
| **Start Command** | `{app start command}` |
| **Health Endpoint** | `{health check URL}` |
| **Mocking Strategy** | `{mock_external / no_mocks / test_containers}` |

**Erklaerung:**
- **Stack**: Automatisch erkannter Tech-Stack (z.B. "python-fastapi", "typescript-nextjs")
- **Test Command**: Command fuer Unit Tests (z.B. `python -m pytest tests/unit/ -v`)
- **Integration Command**: Command fuer Integration Tests
- **Acceptance Command**: Command fuer Acceptance Tests
- **Start Command**: Command um die App zu starten (fuer Smoke Test)
- **Health Endpoint**: URL fuer Health-Check (Smoke Test)
- **Mocking Strategy**: Mocking-Ansatz fuer Tests
```

---

## Deliverables (SCOPE SAFEGUARD)

<!-- DELIVERABLES_START -->
### Agent-Definitionen
- [ ] `.claude/agents/slice-writer.md` -- Modification: Stack-Detection Section (6-Zeilen-Tabelle mit Indicator-Files), Test-Strategy Metadata Generierung (7-Felder-Format), Pflicht-Section und Qualitaets-Checkliste erweitert, Fundamentale Regeln erweitert
- [ ] `.claude/agents/slice-compliance.md` -- Modification: Template-Compliance (Check 0) ersetzen durch inhaltliche AC-Qualitaets-Check + Code Example Korrektheit + Test-Strategy Pruefung, Max 1 Retry Regel, Output-Format Section 0 anpassen

### Template
- [ ] `.claude/templates/plan-spec.md` -- Modification: Test-Strategy Section nach Metadata einfuegen (7-Felder-Tabelle mit Erklaerung), Metadata-Erklaerung erweitern

### Tests
- [ ] `tests/acceptance/test_slice_04_planner_gate_improvements.py` -- Acceptance Tests die pruefen ob slice-writer.md, slice-compliance.md und plan-spec.md korrekt erweitert/angepasst wurden
<!-- DELIVERABLES_END -->

---

## Definition of Done

- [x] Akzeptanzkriterien sind eindeutig und vollstaendig (10 ACs im GIVEN/WHEN/THEN Format)
- [x] Stack-Detection Matrix definiert (6 Stacks: Python/FastAPI, Python/Django, TypeScript/Next.js, TypeScript/Express, Go)
- [x] Test-Strategy Metadata Format definiert (7 Felder)
- [x] Gate 2 inhaltliche Pruefung definiert (AC-Qualitaet, Code Example Korrektheit, Test-Strategy Konsistenz, Agent Output Contracts)
- [x] Max 1 Retry fuer Gate 2 explizit definiert
- [x] plan-spec Template Test-Strategy Section definiert
- [x] Delta zu allen 3 bestehenden Dateien dokumentiert
- [ ] Rollout: slice-writer.md erweitert, slice-compliance.md angepasst, plan-spec.md erweitert

---

## Links

- Bestehender Slice-Writer: `.claude/agents/slice-writer.md`
- Bestehender Gate 2: `.claude/agents/slice-compliance.md`
- Bestehendes Template: `.claude/templates/plan-spec.md`
- Architecture: `specs/2026-02-14-orchestrator-robust-testing/architecture.md`
- Discovery: `specs/2026-02-14-orchestrator-robust-testing/discovery.md`
- Slice 1 (Test-Writer): `specs/2026-02-14-orchestrator-robust-testing/slices/slice-01-test-writer-enhancement.md`
- Slice 2 (Test-Validator): `specs/2026-02-14-orchestrator-robust-testing/slices/slice-02-test-validator-agent.md`
- Slice 3 (Orchestrator): `specs/2026-02-14-orchestrator-robust-testing/slices/slice-03-orchestrator-pipeline.md`

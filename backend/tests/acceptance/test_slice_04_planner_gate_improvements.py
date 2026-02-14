# tests/acceptance/test_slice_04_planner_gate_improvements.py
"""
Acceptance Tests fuer Slice 04: Planner & Gate Improvements.

Validiert dass slice-writer.md, slice-compliance.md und plan-spec.md
korrekt erweitert/angepasst wurden.
"""
import pytest
from pathlib import Path

SLICE_WRITER_FILE = Path(__file__).parent.parent.parent.parent / ".claude" / "agents" / "slice-writer.md"
SLICE_COMPLIANCE_FILE = Path(__file__).parent.parent.parent.parent / ".claude" / "agents" / "slice-compliance.md"
PLAN_SPEC_FILE = Path(__file__).parent.parent.parent.parent / ".claude" / "templates" / "plan-spec.md"


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

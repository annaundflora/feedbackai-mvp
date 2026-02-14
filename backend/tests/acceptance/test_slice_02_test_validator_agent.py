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

AGENT_FILE = Path(__file__).parent.parent.parent.parent / ".claude" / "agents" / "test-validator.md"


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
            assert f'"{stage}"' in agent_content or f"stages.{stage}" in agent_content or "Stage" in agent_content, \
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

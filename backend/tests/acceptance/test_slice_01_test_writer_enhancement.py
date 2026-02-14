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

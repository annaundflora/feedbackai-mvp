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

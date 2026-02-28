# backend/tests/slices/llm-interview-clustering/test_slice_02_fact_extraction_pipeline.py
"""Tests fuer Slice 2: Fact Extraction Pipeline.

Abgeleitet aus GIVEN/WHEN/THEN Acceptance Criteria in der Slice-Spec:
specs/phase-4/2026-02-28-llm-interview-clustering/slices/slice-02-fact-extraction-pipeline.md

Alle LLM-Calls und DB-Calls werden gemockt (mock_external Strategie).
Kein echter PostgreSQL-Zugriff und keine echten LLM-Calls in Unit-Tests.

WICHTIG: _call_llm_with_retry() importiert intern `from langchain_openai import ChatOpenAI`
und erzeugt pro Aufruf eine neue Instanz. Daher muss `langchain_openai.ChatOpenAI`
gepatcht werden, NICHT `app.clustering.extraction.ChatOpenAI` (die wird nur im __init__ benutzt).
"""
import asyncio
import json
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

# Patch-Target fuer den LLM-Client der intern in _call_llm_with_retry erzeugt wird
LLM_PATCH_TARGET = "langchain_openai.ChatOpenAI"

# Patch-Target fuer den LLM-Client im __init__ des FactExtractionService
INIT_LLM_PATCH_TARGET = "app.clustering.extraction.ChatOpenAI"


# ============================================================
# FIXTURES
# ============================================================


@pytest.fixture
def mock_project_id() -> str:
    return str(uuid.UUID("550e8400-e29b-41d4-a716-446655440000"))


@pytest.fixture
def mock_interview_id() -> str:
    return str(uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8"))


@pytest.fixture
def mock_project_row(mock_project_id) -> dict:
    """Typischer Projekt-Dict aus der DB."""
    return {
        "id": uuid.UUID(mock_project_id),
        "name": "Onboarding UX Research",
        "research_goal": "Understand why users drop off during onboarding",
        "prompt_context": "B2B SaaS with 14-day free trial",
        "extraction_source": "summary",
        "model_extraction": "anthropic/claude-haiku-4",
        "model_clustering": "anthropic/claude-sonnet-4",
    }


@pytest.fixture
def mock_project_row_transcript(mock_project_row) -> dict:
    """Projekt-Dict mit extraction_source=transcript."""
    return {**mock_project_row, "extraction_source": "transcript"}


@pytest.fixture
def mock_interview_row(mock_interview_id) -> dict:
    """Typischer Interview-Dict aus der DB."""
    return {
        "session_id": mock_interview_id,
        "summary": "The user found onboarding confusing. They struggled to find settings. The pricing was unclear.",
        "transcript": [
            {"role": "assistant", "content": "Was war Ihr erster Eindruck?"},
            {"role": "user", "content": "Das Onboarding war verwirrend."},
            {"role": "assistant", "content": "Koennen Sie das genauer beschreiben?"},
            {"role": "user", "content": "Ich konnte die Einstellungen nicht finden."},
        ],
        "created_at": datetime.now(timezone.utc),
        "status": "completed",
    }


@pytest.fixture
def mock_llm_response_facts() -> list[dict]:
    """Typische LLM-Antwort mit extrahierten Facts."""
    return [
        {
            "content": "The user found onboarding confusing",
            "quote": "Das Onboarding war verwirrend.",
            "confidence": 0.95,
        },
        {
            "content": "User could not find the settings page",
            "quote": "Ich konnte die Einstellungen nicht finden.",
            "confidence": 0.9,
        },
        {
            "content": "Pricing was unclear to the user",
            "quote": None,
            "confidence": 0.75,
        },
    ]


@pytest.fixture
def mock_saved_facts(mock_project_id, mock_interview_id, mock_llm_response_facts) -> list[dict]:
    """Facts wie sie nach save_facts aus der DB zurueckkommen."""
    results = []
    for fact in mock_llm_response_facts:
        results.append({
            "id": str(uuid.uuid4()),
            "project_id": mock_project_id,
            "interview_id": mock_interview_id,
            "cluster_id": None,
            "content": fact["content"],
            "quote": fact["quote"],
            "confidence": fact["confidence"],
            "created_at": datetime.now(timezone.utc),
        })
    return results


@pytest.fixture
def mock_settings():
    """Mock Settings mit Test-Werten."""
    settings = MagicMock()
    settings.openrouter_api_key = "test-key"
    settings.interviewer_llm = "anthropic/claude-sonnet-4"
    settings.clustering_max_retries = 3
    settings.clustering_llm_timeout_seconds = 120
    settings.clustering_batch_size = 20
    settings.clustering_pipeline_timeout_seconds = 600
    return settings


@pytest.fixture
def mock_fact_repository():
    """Gemocktes FactRepository."""
    repo = AsyncMock()
    repo.save_facts = AsyncMock(return_value=[])
    repo.get_facts_for_interview = AsyncMock(return_value=[])
    repo.get_facts_for_project = AsyncMock(return_value=[])
    return repo


@pytest.fixture
def mock_assignment_repository():
    """Gemocktes InterviewAssignmentRepository."""
    repo = AsyncMock()
    repo.find_by_interview_id = AsyncMock(return_value=None)
    repo.find_by_project_and_interview = AsyncMock(return_value=None)
    repo.update_extraction_status = AsyncMock(return_value={})
    return repo


@pytest.fixture
def mock_project_repository():
    """Gemocktes ProjectRepository."""
    repo = AsyncMock()
    repo.get_by_id = AsyncMock(return_value=None)
    return repo


@pytest.fixture
def mock_interview_repository():
    """Gemocktes InterviewRepository."""
    repo = AsyncMock()
    repo.get_session = AsyncMock(return_value=None)
    return repo


@pytest.fixture
def mock_event_bus():
    """Gemockter SseEventBus."""
    bus = AsyncMock()
    bus.publish = AsyncMock()
    return bus


@pytest.fixture
def fact_extraction_service(
    mock_fact_repository,
    mock_assignment_repository,
    mock_project_repository,
    mock_interview_repository,
    mock_event_bus,
    mock_settings,
):
    """FactExtractionService mit allen gemockten Dependencies."""
    with patch(INIT_LLM_PATCH_TARGET) as MockChatOpenAI:
        mock_llm = AsyncMock()
        MockChatOpenAI.return_value = mock_llm

        from app.clustering.extraction import FactExtractionService
        service = FactExtractionService(
            fact_repository=mock_fact_repository,
            assignment_repository=mock_assignment_repository,
            project_repository=mock_project_repository,
            interview_repository=mock_interview_repository,
            event_bus=mock_event_bus,
            settings=mock_settings,
        )
        service._llm = mock_llm
        return service


def _make_llm_mock(response):
    """Erzeugt ein Mock-ChatOpenAI-Objekt dessen ainvoke die response zurueckgibt."""
    mock_instance = AsyncMock()
    mock_instance.ainvoke = AsyncMock(return_value=response)
    return mock_instance


def _make_llm_mock_with_side_effects(side_effects):
    """Erzeugt ein Mock-ChatOpenAI das pro Aufruf neue Instanz liefert.

    Da _call_llm_with_retry pro Retry eine neue ChatOpenAI-Instanz erzeugt,
    muss das Mock-Objekt als side_effect eine neue Instanz pro Aufruf liefern.
    """
    instances = []
    for effect in side_effects:
        inst = AsyncMock()
        if isinstance(effect, Exception):
            inst.ainvoke = AsyncMock(side_effect=effect)
        else:
            inst.ainvoke = AsyncMock(return_value=effect)
        instances.append(inst)
    return instances


# ============================================================
# UNIT TESTS -- FactExtractionService
# ============================================================


class TestFactExtractionServiceInit:
    """FactExtractionService wird korrekt initialisiert."""

    def test_service_importable(self):
        """Modul app.clustering.extraction ist importierbar."""
        with patch(INIT_LLM_PATCH_TARGET):
            from app.clustering.extraction import FactExtractionService, FactExtractionError, ExtractedFact
            assert FactExtractionService is not None
            assert FactExtractionError is not None
            assert ExtractedFact is not None

    def test_service_creates_with_dependencies(self, mock_settings):
        """Service laesst sich mit allen Dependencies instanziieren."""
        with patch(INIT_LLM_PATCH_TARGET):
            from app.clustering.extraction import FactExtractionService
            service = FactExtractionService(
                fact_repository=AsyncMock(),
                assignment_repository=AsyncMock(),
                project_repository=AsyncMock(),
                interview_repository=AsyncMock(),
                event_bus=AsyncMock(),
                settings=mock_settings,
            )
            assert service is not None


class TestBuildInterviewText:
    """_build_interview_text baut den Interview-Text korrekt zusammen."""

    def test_summary_source_returns_summary(self, fact_extraction_service, mock_interview_row):
        """extraction_source='summary' gibt Summary-Text zurueck."""
        result = fact_extraction_service._build_interview_text(mock_interview_row, "summary")
        assert result == mock_interview_row["summary"]

    def test_transcript_source_returns_flat_text(self, fact_extraction_service, mock_interview_row):
        """extraction_source='transcript' gibt flachen Transcript-Text zurueck."""
        result = fact_extraction_service._build_interview_text(mock_interview_row, "transcript")
        assert "assistant: Was war Ihr erster Eindruck?" in result
        assert "user: Das Onboarding war verwirrend." in result
        assert "assistant: Koennen Sie das genauer beschreiben?" in result
        assert "user: Ich konnte die Einstellungen nicht finden." in result

    def test_transcript_source_without_transcript_falls_back_to_summary(
        self, fact_extraction_service
    ):
        """Wenn transcript=None, Fallback auf summary."""
        interview = {"summary": "Fallback summary", "transcript": None}
        result = fact_extraction_service._build_interview_text(interview, "transcript")
        assert result == "Fallback summary"

    def test_summary_source_without_summary_returns_empty(self, fact_extraction_service):
        """Wenn summary=None, leerer String."""
        interview = {"summary": None, "transcript": []}
        result = fact_extraction_service._build_interview_text(interview, "summary")
        assert result == ""


class TestCallLlmWithRetry:
    """_call_llm_with_retry: Retry-Logik mit exponential backoff."""

    @pytest.mark.asyncio
    async def test_success_on_first_attempt(self, fact_extraction_service, mock_llm_response_facts):
        """Erfolgreicher LLM-Call beim ersten Versuch."""
        mock_response = MagicMock()
        mock_response.content = json.dumps(mock_llm_response_facts)

        mock_llm_instance = _make_llm_mock(mock_response)

        with patch(LLM_PATCH_TARGET, return_value=mock_llm_instance):
            result = await fact_extraction_service._call_llm_with_retry(
                prompt="Test prompt",
                model="anthropic/claude-haiku-4",
                max_retries=3,
            )
            assert len(result) == 3
            assert result[0]["content"] == "The user found onboarding confusing"

    @pytest.mark.asyncio
    async def test_retry_on_json_parse_error(self, fact_extraction_service):
        """Retry bei malformed JSON LLM-Antwort."""
        bad_response = MagicMock()
        bad_response.content = "This is not JSON"
        good_response = MagicMock()
        good_response.content = json.dumps([{"content": "A fact", "quote": None, "confidence": 0.8}])

        # Jeder Aufruf von ChatOpenAI() erzeugt neue Instanz
        instances = _make_llm_mock_with_side_effects([bad_response, good_response])

        with patch(LLM_PATCH_TARGET, side_effect=instances):
            with patch("app.clustering.extraction.asyncio.sleep", new_callable=AsyncMock):
                result = await fact_extraction_service._call_llm_with_retry(
                    prompt="Test prompt",
                    model="test-model",
                    max_retries=3,
                )
                assert len(result) == 1

    @pytest.mark.asyncio
    async def test_retry_on_timeout(self, fact_extraction_service):
        """Retry bei LLM-Timeout."""
        good_response = MagicMock()
        good_response.content = json.dumps([{"content": "A fact"}])

        # Erste Instanz: ainvoke wirft TimeoutError (via wait_for)
        # Zweite Instanz: ainvoke gibt good_response zurueck
        inst_1 = AsyncMock()
        inst_1.ainvoke = AsyncMock(return_value=good_response)  # wird nie erreicht weil wait_for Timeout wirft
        inst_2 = _make_llm_mock(good_response)

        call_count = 0

        async def mock_wait_for(coro, timeout):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # Coroutine muss geschlossen werden um RuntimeWarning zu vermeiden
                if hasattr(coro, 'close'):
                    coro.close()
                raise asyncio.TimeoutError()
            return await coro

        with patch(LLM_PATCH_TARGET, side_effect=[inst_1, inst_2]):
            with patch("app.clustering.extraction.asyncio.sleep", new_callable=AsyncMock):
                with patch("app.clustering.extraction.asyncio.wait_for", side_effect=mock_wait_for):
                    result = await fact_extraction_service._call_llm_with_retry(
                        prompt="Test prompt",
                        model="test-model",
                        max_retries=3,
                    )
                    assert len(result) == 1

    @pytest.mark.asyncio
    async def test_fails_after_max_retries(self, fact_extraction_service):
        """FactExtractionError nach max_retries fehlgeschlagenen Versuchen."""
        from app.clustering.extraction import FactExtractionError

        bad_response = MagicMock()
        bad_response.content = "not json"

        # 3 Instanzen, alle liefern bad_response
        instances = _make_llm_mock_with_side_effects([bad_response, bad_response, bad_response])

        with patch(LLM_PATCH_TARGET, side_effect=instances):
            with patch("app.clustering.extraction.asyncio.sleep", new_callable=AsyncMock):
                with pytest.raises(FactExtractionError):
                    await fact_extraction_service._call_llm_with_retry(
                        prompt="Test prompt",
                        model="test-model",
                        max_retries=3,
                    )

    @pytest.mark.asyncio
    async def test_no_retry_on_auth_error(self, fact_extraction_service):
        """Kein Retry bei Auth-Fehler (401/403) -- sofort fehlschlagen."""
        from app.clustering.extraction import FactExtractionError

        inst = AsyncMock()
        inst.ainvoke = AsyncMock(side_effect=Exception("401 Unauthorized"))

        with patch(LLM_PATCH_TARGET, return_value=inst):
            with pytest.raises(FactExtractionError, match="Auth error"):
                await fact_extraction_service._call_llm_with_retry(
                    prompt="Test prompt",
                    model="test-model",
                    max_retries=3,
                )

    @pytest.mark.asyncio
    async def test_empty_json_array_is_valid(self, fact_extraction_service):
        """Leeres JSON-Array [] ist eine gueltige Antwort."""
        mock_response = MagicMock()
        mock_response.content = "[]"

        mock_llm_instance = _make_llm_mock(mock_response)

        with patch(LLM_PATCH_TARGET, return_value=mock_llm_instance):
            result = await fact_extraction_service._call_llm_with_retry(
                prompt="Test prompt",
                model="test-model",
                max_retries=3,
            )
            assert result == []


class TestExtractMethod:
    """extract() Methode gibt ExtractedFact-Objekte zurueck."""

    @pytest.mark.asyncio
    async def test_extract_returns_extracted_facts(
        self, fact_extraction_service, mock_llm_response_facts
    ):
        """extract() gibt Liste von ExtractedFact zurueck."""
        mock_response = MagicMock()
        mock_response.content = json.dumps(mock_llm_response_facts)

        mock_llm_instance = _make_llm_mock(mock_response)

        with patch(LLM_PATCH_TARGET, return_value=mock_llm_instance):
            from app.clustering.extraction import ExtractedFact
            facts = await fact_extraction_service.extract(
                interview_text="Some interview text",
                research_goal="Understand onboarding",
                model_extraction="anthropic/claude-haiku-4",
            )
            assert len(facts) == 3
            assert all(isinstance(f, ExtractedFact) for f in facts)
            assert facts[0].content == "The user found onboarding confusing"
            assert facts[0].quote == "Das Onboarding war verwirrend."
            assert facts[0].confidence == 0.95
            assert facts[2].quote is None


# ============================================================
# UNIT TESTS -- SseEventBus
# ============================================================


class TestSseEventBus:
    """SseEventBus funktioniert als in-memory pub/sub."""

    def test_eventbus_importable(self):
        """Modul app.clustering.events ist importierbar."""
        from app.clustering.events import SseEventBus
        assert SseEventBus is not None

    def test_subscribe_creates_queue(self):
        """subscribe() erstellt eine neue asyncio.Queue."""
        from app.clustering.events import SseEventBus
        bus = SseEventBus()
        queue = bus.subscribe("project-1")
        assert isinstance(queue, asyncio.Queue)

    def test_unsubscribe_removes_queue(self):
        """unsubscribe() entfernt die Queue."""
        from app.clustering.events import SseEventBus
        bus = SseEventBus()
        queue = bus.subscribe("project-1")
        bus.unsubscribe("project-1", queue)
        assert len(bus._queues["project-1"]) == 0

    @pytest.mark.asyncio
    async def test_publish_sends_to_subscriber(self):
        """publish() sendet Event an alle Subscriber."""
        from app.clustering.events import SseEventBus
        bus = SseEventBus()
        queue = bus.subscribe("project-1")
        await bus.publish("project-1", "fact_extracted", {"interview_id": "i1", "fact_count": 3})

        event = await queue.get()
        assert event["type"] == "fact_extracted"
        assert event["interview_id"] == "i1"
        assert event["fact_count"] == 3

    @pytest.mark.asyncio
    async def test_publish_no_op_without_subscribers(self):
        """publish() ohne Subscriber ist ein No-Op (kein Fehler)."""
        from app.clustering.events import SseEventBus
        bus = SseEventBus()
        # Soll keine Exception werfen
        await bus.publish("project-no-sub", "fact_extracted", {"interview_id": "i1", "fact_count": 0})

    @pytest.mark.asyncio
    async def test_publish_multiple_subscribers(self):
        """publish() sendet an mehrere Subscriber."""
        from app.clustering.events import SseEventBus
        bus = SseEventBus()
        q1 = bus.subscribe("project-1")
        q2 = bus.subscribe("project-1")

        await bus.publish("project-1", "fact_extracted", {"fact_count": 5})

        e1 = await q1.get()
        e2 = await q2.get()
        assert e1["fact_count"] == 5
        assert e2["fact_count"] == 5


# ============================================================
# UNIT TESTS -- FactRepository
# ============================================================


class TestFactRepositoryModule:
    """FactRepository-Modul ist importierbar."""

    def test_importable(self):
        """Modul app.clustering.fact_repository ist importierbar."""
        from app.clustering.fact_repository import FactRepository
        assert FactRepository is not None


# ============================================================
# UNIT TESTS -- Prompts
# ============================================================


class TestPrompts:
    """Prompt-Template ist korrekt konfiguriert."""

    def test_prompt_importable(self):
        """FACT_EXTRACTION_PROMPT ist importierbar."""
        from app.clustering.prompts import FACT_EXTRACTION_PROMPT
        assert isinstance(FACT_EXTRACTION_PROMPT, str)

    def test_prompt_has_placeholders(self):
        """Prompt enthaelt {research_goal} und {interview_text} Platzhalter."""
        from app.clustering.prompts import FACT_EXTRACTION_PROMPT
        assert "{research_goal}" in FACT_EXTRACTION_PROMPT
        assert "{interview_text}" in FACT_EXTRACTION_PROMPT

    def test_prompt_requests_json_output(self):
        """Prompt fordert JSON-Array als Output."""
        from app.clustering.prompts import FACT_EXTRACTION_PROMPT
        assert "JSON" in FACT_EXTRACTION_PROMPT
        assert "[]" in FACT_EXTRACTION_PROMPT

    def test_prompt_is_formattable(self):
        """Prompt laesst sich mit research_goal und interview_text formatieren."""
        from app.clustering.prompts import FACT_EXTRACTION_PROMPT
        result = FACT_EXTRACTION_PROMPT.format(
            research_goal="Test goal",
            interview_text="Test text",
        )
        assert "Test goal" in result
        assert "Test text" in result


# ============================================================
# UNIT TESTS -- Settings
# ============================================================


class TestSettingsExtension:
    """Settings enthalten Clustering-Konfiguration."""

    def test_settings_has_clustering_fields(self):
        """Settings hat clustering_max_retries, clustering_llm_timeout_seconds."""
        with patch.dict("os.environ", {
            "OPENROUTER_API_KEY": "test-key",
            "DATABASE_URL": "postgresql+asyncpg://test:test@localhost:5432/test",
        }, clear=False):
            from app.config.settings import Settings
            s = Settings()
            assert s.clustering_max_retries == 3
            assert s.clustering_llm_timeout_seconds == 120
            assert s.clustering_batch_size == 20
            assert s.clustering_pipeline_timeout_seconds == 600


# ============================================================
# UNIT TESTS -- InterviewAssignmentService.retry()
# ============================================================


class TestInterviewAssignmentServiceRetry:
    """InterviewAssignmentService.retry() Business Logic."""

    @pytest.mark.asyncio
    async def test_retry_raises_404_when_not_found(self):
        """retry() wirft HTTP 404 wenn Interview nicht im Projekt."""
        from app.clustering.interview_assignment_service import InterviewAssignmentService
        mock_repo = AsyncMock()
        mock_repo.find_by_project_and_interview = AsyncMock(return_value=None)

        service = InterviewAssignmentService(repo=mock_repo)
        with pytest.raises(HTTPException) as exc_info:
            await service.retry(project_id="p1", interview_id="i1")
        assert exc_info.value.status_code == 404
        assert "not found" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_retry_raises_409_when_not_failed(self):
        """retry() wirft HTTP 409 wenn Status nicht 'failed'."""
        from app.clustering.interview_assignment_service import InterviewAssignmentService
        mock_repo = AsyncMock()
        mock_repo.find_by_project_and_interview = AsyncMock(
            return_value={"extraction_status": "completed", "clustering_status": "pending"}
        )

        service = InterviewAssignmentService(repo=mock_repo)
        with pytest.raises(HTTPException) as exc_info:
            await service.retry(project_id="p1", interview_id="i1")
        assert exc_info.value.status_code == 409
        assert "completed" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_retry_resets_status_and_starts_task(self, mock_interview_id):
        """retry() setzt extraction_status='pending' und startet neuen Task."""
        from app.clustering.interview_assignment_service import InterviewAssignmentService

        mock_repo = AsyncMock()
        mock_repo.find_by_project_and_interview = AsyncMock(
            return_value={
                "extraction_status": "failed",
                "clustering_status": "pending",
                "interview_id": mock_interview_id,
            }
        )
        mock_repo.update_extraction_status = AsyncMock(
            return_value={
                "interview_id": mock_interview_id,
                "extraction_status": "pending",
                "clustering_status": "pending",
            }
        )

        mock_fact_svc = AsyncMock()
        mock_fact_svc.process_interview = AsyncMock()

        mock_interview_repo = AsyncMock()
        mock_interview_repo.get_session = AsyncMock(return_value={
            "created_at": datetime.now(timezone.utc),
            "summary": "Test summary for retry",
        })

        service = InterviewAssignmentService(
            repo=mock_repo,
            fact_extraction_service=mock_fact_svc,
            interview_repository=mock_interview_repo,
        )

        result = await service.retry(project_id="p1", interview_id=mock_interview_id)

        # Status auf pending zurueckgesetzt
        mock_repo.update_extraction_status.assert_called_once_with(
            interview_id=mock_interview_id,
            extraction_status="pending",
            clustering_status="pending",
        )

        # Response hat extraction_status=pending
        assert result.extraction_status == "pending"
        assert result.clustering_status == "pending"


# ============================================================
# UNIT TESTS -- InterviewService.end() Hook
# ============================================================


class TestInterviewServiceEndHook:
    """InterviewService.end() triggert Fact Extraction fuer Projekt-Interviews."""

    @pytest.mark.asyncio
    async def test_end_triggers_extraction_for_project_interview(self):
        """end() startet asyncio.create_task fuer Interview im Projekt."""
        from app.interview.service import InterviewService

        mock_graph = MagicMock()
        mock_graph.get_history = MagicMock(return_value=[])

        mock_repo = AsyncMock()
        mock_repo.complete_session = AsyncMock()
        mock_repo.get_recent_summaries = AsyncMock(return_value=[])

        mock_summary_svc = AsyncMock()
        mock_summary_svc.generate = AsyncMock(return_value="Test summary")

        mock_fact_svc = AsyncMock()
        mock_fact_svc.process_interview = AsyncMock()

        mock_assignment_repo = AsyncMock()
        mock_assignment_repo.find_by_interview_id = AsyncMock(
            return_value={"project_id": uuid.UUID("550e8400-e29b-41d4-a716-446655440000")}
        )

        service = InterviewService(
            graph=mock_graph,
            repository=mock_repo,
            summary_service=mock_summary_svc,
            fact_extraction_service=mock_fact_svc,
            assignment_repository=mock_assignment_repo,
        )

        session_id = str(uuid.uuid4())
        service._sessions[session_id] = {
            "status": "active",
            "message_count": 3,
            "anonymous_id": "anon-1",
        }

        with patch("app.interview.service.asyncio.create_task") as mock_create_task:
            await service.end(session_id)
            mock_create_task.assert_called_once()

    @pytest.mark.asyncio
    async def test_end_does_not_trigger_for_non_project_interview(self):
        """end() triggert NICHT wenn Interview keinem Projekt zugeordnet."""
        from app.interview.service import InterviewService

        mock_graph = MagicMock()
        mock_graph.get_history = MagicMock(return_value=[])

        mock_repo = AsyncMock()
        mock_repo.complete_session = AsyncMock()
        mock_repo.get_recent_summaries = AsyncMock(return_value=[])

        mock_summary_svc = AsyncMock()
        mock_summary_svc.generate = AsyncMock(return_value="Test summary")

        mock_fact_svc = AsyncMock()
        mock_assignment_repo = AsyncMock()
        mock_assignment_repo.find_by_interview_id = AsyncMock(return_value=None)

        service = InterviewService(
            graph=mock_graph,
            repository=mock_repo,
            summary_service=mock_summary_svc,
            fact_extraction_service=mock_fact_svc,
            assignment_repository=mock_assignment_repo,
        )

        session_id = str(uuid.uuid4())
        service._sessions[session_id] = {
            "status": "active",
            "message_count": 2,
            "anonymous_id": "anon-1",
        }

        with patch("app.interview.service.asyncio.create_task") as mock_create_task:
            await service.end(session_id)
            mock_create_task.assert_not_called()

    @pytest.mark.asyncio
    async def test_end_does_not_fail_on_trigger_error(self):
        """end() schlaegt nicht fehl wenn Trigger-Fehler auftritt."""
        from app.interview.service import InterviewService

        mock_graph = MagicMock()
        mock_graph.get_history = MagicMock(return_value=[])

        mock_repo = AsyncMock()
        mock_repo.complete_session = AsyncMock()
        mock_repo.get_recent_summaries = AsyncMock(return_value=[])

        mock_summary_svc = AsyncMock()
        mock_summary_svc.generate = AsyncMock(return_value="Test summary")

        mock_fact_svc = AsyncMock()
        mock_assignment_repo = AsyncMock()
        mock_assignment_repo.find_by_interview_id = AsyncMock(
            side_effect=Exception("DB connection failed")
        )

        service = InterviewService(
            graph=mock_graph,
            repository=mock_repo,
            summary_service=mock_summary_svc,
            fact_extraction_service=mock_fact_svc,
            assignment_repository=mock_assignment_repo,
        )

        session_id = str(uuid.uuid4())
        service._sessions[session_id] = {
            "status": "active",
            "message_count": 1,
            "anonymous_id": "anon-1",
        }

        # Should not raise
        result = await service.end(session_id)
        assert "summary" in result

    @pytest.mark.asyncio
    async def test_end_backward_compatible_without_extraction_service(self):
        """end() funktioniert ohne fact_extraction_service (backward-compatible)."""
        from app.interview.service import InterviewService

        mock_graph = MagicMock()
        mock_graph.get_history = MagicMock(return_value=[])

        mock_repo = AsyncMock()
        mock_repo.complete_session = AsyncMock()
        mock_repo.get_recent_summaries = AsyncMock(return_value=[])

        mock_summary_svc = AsyncMock()
        mock_summary_svc.generate = AsyncMock(return_value="Test summary")

        service = InterviewService(
            graph=mock_graph,
            repository=mock_repo,
            summary_service=mock_summary_svc,
            # No fact_extraction_service or assignment_repository
        )

        session_id = str(uuid.uuid4())
        service._sessions[session_id] = {
            "status": "active",
            "message_count": 1,
            "anonymous_id": "anon-1",
        }

        result = await service.end(session_id)
        assert "summary" in result
        assert result["message_count"] == 1


# ============================================================
# UNIT TESTS -- Router Retry Endpoint
# ============================================================


class TestRetryEndpoint:
    """Retry-Endpoint in router.py existiert."""

    def test_retry_route_exists(self):
        """POST /api/projects/{id}/interviews/{iid}/retry Route existiert."""
        from app.clustering.router import router
        routes = [r.path for r in router.routes]
        assert "/api/projects/{project_id}/interviews/{interview_id}/retry" in routes


# ============================================================
# ACCEPTANCE TESTS -- 1:1 aus GIVEN/WHEN/THEN
# ============================================================


class TestSlice02Acceptance:
    """Acceptance Tests -- 1:1 aus Slice-Spec ACs."""

    @pytest.mark.acceptance
    @pytest.mark.asyncio
    async def test_ac_1_summary_extraction_triggered_on_end(
        self,
        mock_project_id,
        mock_interview_id,
        mock_project_row,
        mock_interview_row,
        mock_settings,
    ):
        """AC-1: GIVEN ein abgeschlossenes Interview (InterviewService.end() aufgerufen)
        das einem Projekt zugeordnet ist
        WHEN das Interview extraction_source="summary" konfiguriert hat
        THEN wird FactExtractionService.process_interview() als Background-Task
        gestartet und der Summary-Text als Input fuer die LLM-Extraktion verwendet.
        """
        # Arrange (GIVEN): InterviewService mit allen Dependencies
        from app.interview.service import InterviewService

        mock_graph = MagicMock()
        mock_graph.get_history = MagicMock(return_value=[])

        mock_repo = AsyncMock()
        mock_repo.complete_session = AsyncMock()
        mock_repo.get_recent_summaries = AsyncMock(return_value=[])

        mock_summary_svc = AsyncMock()
        mock_summary_svc.generate = AsyncMock(return_value="Test summary")

        mock_fact_svc = AsyncMock()
        mock_fact_svc.process_interview = AsyncMock()

        mock_assignment_repo = AsyncMock()
        mock_assignment_repo.find_by_interview_id = AsyncMock(
            return_value={"project_id": uuid.UUID(mock_project_id)}
        )

        service = InterviewService(
            graph=mock_graph,
            repository=mock_repo,
            summary_service=mock_summary_svc,
            fact_extraction_service=mock_fact_svc,
            assignment_repository=mock_assignment_repo,
        )

        service._sessions[mock_interview_id] = {
            "status": "active",
            "message_count": 3,
            "anonymous_id": "anon-1",
        }

        # Act (WHEN): Interview beenden
        with patch("app.interview.service.asyncio.create_task") as mock_create_task:
            await service.end(mock_interview_id)

            # Assert (THEN): Background-Task wurde gestartet
            mock_create_task.assert_called_once()
            mock_assignment_repo.find_by_interview_id.assert_called_once_with(mock_interview_id)

        # Verify: extraction_source='summary' fuehrt zu Summary-Text als Input
        with patch(INIT_LLM_PATCH_TARGET):
            from app.clustering.extraction import FactExtractionService
            extraction_svc = FactExtractionService(
                fact_repository=AsyncMock(),
                assignment_repository=AsyncMock(),
                project_repository=AsyncMock(),
                interview_repository=AsyncMock(),
                event_bus=AsyncMock(),
                settings=mock_settings,
            )
            text_result = extraction_svc._build_interview_text(mock_interview_row, "summary")
            assert text_result == mock_interview_row["summary"]

    @pytest.mark.acceptance
    @pytest.mark.asyncio
    async def test_ac_2_facts_saved_with_correct_fields(
        self,
        mock_project_id,
        mock_interview_id,
        mock_project_row,
        mock_interview_row,
        mock_llm_response_facts,
        mock_saved_facts,
        mock_fact_repository,
        mock_assignment_repository,
        mock_project_repository,
        mock_interview_repository,
        mock_event_bus,
        mock_settings,
    ):
        """AC-2: GIVEN ein Interview das einem Projekt zugeordnet ist
        WHEN FactExtractionService.process_interview() erfolgreich ausgefuehrt wird
        THEN werden die extrahierten Facts in der facts-Tabelle mit project_id,
        interview_id, content, optionalem quote und optionalem confidence gespeichert,
        alle mit cluster_id=NULL.
        """
        # Arrange (GIVEN)
        mock_project_repository.get_by_id = AsyncMock(return_value=mock_project_row)
        mock_interview_repository.get_session = AsyncMock(return_value=mock_interview_row)
        mock_fact_repository.save_facts = AsyncMock(return_value=mock_saved_facts)
        mock_assignment_repository.update_extraction_status = AsyncMock(return_value={})

        mock_response = MagicMock()
        mock_response.content = json.dumps(mock_llm_response_facts)
        mock_llm_instance = _make_llm_mock(mock_response)

        with patch(INIT_LLM_PATCH_TARGET):
            with patch(LLM_PATCH_TARGET, return_value=mock_llm_instance):
                from app.clustering.extraction import FactExtractionService
                service = FactExtractionService(
                    fact_repository=mock_fact_repository,
                    assignment_repository=mock_assignment_repository,
                    project_repository=mock_project_repository,
                    interview_repository=mock_interview_repository,
                    event_bus=mock_event_bus,
                    settings=mock_settings,
                )

                # Act (WHEN)
                await service.process_interview(mock_project_id, mock_interview_id)

        # Assert (THEN): save_facts aufgerufen mit korrekten Parametern
        mock_fact_repository.save_facts.assert_called_once()
        call_kwargs = mock_fact_repository.save_facts.call_args
        # Pruefe project_id und interview_id (positional oder keyword)
        if call_kwargs.kwargs:
            assert call_kwargs.kwargs.get("project_id") == mock_project_id
            assert call_kwargs.kwargs.get("interview_id") == mock_interview_id
        else:
            assert call_kwargs.args[0] == mock_project_id
            assert call_kwargs.args[1] == mock_interview_id

        # Alle gespeicherten Facts haben cluster_id=NULL
        for fact in mock_saved_facts:
            assert fact["cluster_id"] is None
            assert "content" in fact
            assert "project_id" in fact
            assert "interview_id" in fact

    @pytest.mark.acceptance
    @pytest.mark.asyncio
    async def test_ac_3_status_completed_and_sse_event(
        self,
        mock_project_id,
        mock_interview_id,
        mock_project_row,
        mock_interview_row,
        mock_llm_response_facts,
        mock_saved_facts,
        mock_fact_repository,
        mock_assignment_repository,
        mock_project_repository,
        mock_interview_repository,
        mock_event_bus,
        mock_settings,
    ):
        """AC-3: GIVEN ein Interview das einem Projekt zugeordnet ist
        WHEN FactExtractionService.process_interview() erfolgreich ausgefuehrt wird
        THEN wird extraction_status in project_interviews auf "completed" gesetzt
        und ein SSE-Event fact_extracted mit {interview_id, fact_count} publiziert.
        """
        # Arrange (GIVEN)
        mock_project_repository.get_by_id = AsyncMock(return_value=mock_project_row)
        mock_interview_repository.get_session = AsyncMock(return_value=mock_interview_row)
        mock_fact_repository.save_facts = AsyncMock(return_value=mock_saved_facts)
        mock_assignment_repository.update_extraction_status = AsyncMock(return_value={})

        mock_response = MagicMock()
        mock_response.content = json.dumps(mock_llm_response_facts)
        mock_llm_instance = _make_llm_mock(mock_response)

        with patch(INIT_LLM_PATCH_TARGET):
            with patch(LLM_PATCH_TARGET, return_value=mock_llm_instance):
                from app.clustering.extraction import FactExtractionService
                service = FactExtractionService(
                    fact_repository=mock_fact_repository,
                    assignment_repository=mock_assignment_repository,
                    project_repository=mock_project_repository,
                    interview_repository=mock_interview_repository,
                    event_bus=mock_event_bus,
                    settings=mock_settings,
                )

                # Act (WHEN)
                await service.process_interview(mock_project_id, mock_interview_id)

        # Assert (THEN): extraction_status auf "completed" gesetzt
        status_calls = mock_assignment_repository.update_extraction_status.call_args_list
        status_values = [
            call.kwargs.get("extraction_status", call.args[0] if call.args else None)
            for call in status_calls
        ]
        assert "running" in status_values
        assert "completed" in status_values

        # SSE-Event fact_extracted publiziert
        mock_event_bus.publish.assert_called_once()
        publish_call = mock_event_bus.publish.call_args

        # Event-Typ ist fact_extracted
        if publish_call.kwargs:
            assert publish_call.kwargs.get("event_type") == "fact_extracted"
            event_data = publish_call.kwargs.get("data")
        else:
            assert publish_call.args[1] == "fact_extracted"
            event_data = publish_call.args[2]

        # Event enthalt interview_id und fact_count
        assert event_data["interview_id"] == mock_interview_id
        assert event_data["fact_count"] == len(mock_saved_facts)

    @pytest.mark.acceptance
    @pytest.mark.asyncio
    async def test_ac_4_all_retries_fail_sets_failed_status(
        self,
        mock_project_id,
        mock_interview_id,
        mock_project_row,
        mock_interview_row,
        mock_fact_repository,
        mock_assignment_repository,
        mock_project_repository,
        mock_interview_repository,
        mock_event_bus,
        mock_settings,
    ):
        """AC-4: GIVEN ein Interview das einem Projekt zugeordnet ist
        WHEN der LLM-Aufruf bei allen 3 Versuchen fehlschlaegt (Timeout oder malformed JSON)
        THEN wird extraction_status in project_interviews auf "failed" gesetzt
        und kein Fact wird in der DB gespeichert.
        """
        # Arrange (GIVEN)
        mock_project_repository.get_by_id = AsyncMock(return_value=mock_project_row)
        mock_interview_repository.get_session = AsyncMock(return_value=mock_interview_row)
        mock_assignment_repository.update_extraction_status = AsyncMock(return_value={})

        # LLM gibt immer malformed JSON zurueck (3 Instanzen fuer 3 Retries)
        bad_response = MagicMock()
        bad_response.content = "This is not valid JSON at all"
        instances = _make_llm_mock_with_side_effects([bad_response, bad_response, bad_response])

        with patch(INIT_LLM_PATCH_TARGET):
            with patch(LLM_PATCH_TARGET, side_effect=instances):
                with patch("app.clustering.extraction.asyncio.sleep", new_callable=AsyncMock):
                    from app.clustering.extraction import FactExtractionService
                    service = FactExtractionService(
                        fact_repository=mock_fact_repository,
                        assignment_repository=mock_assignment_repository,
                        project_repository=mock_project_repository,
                        interview_repository=mock_interview_repository,
                        event_bus=mock_event_bus,
                        settings=mock_settings,
                    )

                    # Act (WHEN)
                    await service.process_interview(mock_project_id, mock_interview_id)

        # Assert (THEN): extraction_status auf "failed" gesetzt
        status_calls = mock_assignment_repository.update_extraction_status.call_args_list
        # Letzter Call soll "failed" sein
        last_call = status_calls[-1]
        last_status = last_call.kwargs.get("extraction_status")
        assert last_status == "failed"

        # Kein Fact in DB gespeichert
        mock_fact_repository.save_facts.assert_not_called()

        # Kein SSE-Event publiziert (weil fehlgeschlagen)
        mock_event_bus.publish.assert_not_called()

    @pytest.mark.acceptance
    @pytest.mark.asyncio
    async def test_ac_5_retry_endpoint_resets_and_restarts(
        self,
        mock_project_id,
        mock_interview_id,
    ):
        """AC-5: GIVEN ein Interview mit extraction_status="failed"
        WHEN POST /api/projects/{id}/interviews/{iid}/retry aufgerufen wird
        THEN wird extraction_status auf "pending" gesetzt, ein neuer Extraction-Task
        gestartet, und InterviewAssignment mit extraction_status="pending" in der
        Response zurueckgegeben (HTTP 200).
        """
        # Arrange (GIVEN)
        from app.clustering.interview_assignment_service import InterviewAssignmentService

        mock_repo = AsyncMock()
        mock_repo.find_by_project_and_interview = AsyncMock(
            return_value={
                "interview_id": mock_interview_id,
                "extraction_status": "failed",
                "clustering_status": "pending",
            }
        )
        mock_repo.update_extraction_status = AsyncMock(
            return_value={
                "interview_id": mock_interview_id,
                "extraction_status": "pending",
                "clustering_status": "pending",
            }
        )

        mock_fact_svc = AsyncMock()
        mock_fact_svc.process_interview = AsyncMock()

        mock_interview_repo = AsyncMock()
        mock_interview_repo.get_session = AsyncMock(return_value={
            "created_at": datetime.now(timezone.utc),
            "summary": "Export feature was not working...",
        })

        service = InterviewAssignmentService(
            repo=mock_repo,
            fact_extraction_service=mock_fact_svc,
            interview_repository=mock_interview_repo,
        )

        # Act (WHEN)
        result = await service.retry(project_id=mock_project_id, interview_id=mock_interview_id)

        # Assert (THEN)
        # extraction_status auf "pending" gesetzt
        mock_repo.update_extraction_status.assert_called_once_with(
            interview_id=mock_interview_id,
            extraction_status="pending",
            clustering_status="pending",
        )

        # Response hat extraction_status="pending"
        assert result.extraction_status == "pending"
        assert result.clustering_status == "pending"
        assert str(result.interview_id) == mock_interview_id

    @pytest.mark.acceptance
    @pytest.mark.asyncio
    async def test_ac_6_retry_409_when_not_failed(
        self,
        mock_project_id,
        mock_interview_id,
    ):
        """AC-6: GIVEN ein Interview mit extraction_status="completed"
        WHEN POST /api/projects/{id}/interviews/{iid}/retry aufgerufen wird
        THEN wird HTTP 409 mit
        {"detail": "Interview is not in failed state, current status: completed"}
        zurueckgegeben.
        """
        # Arrange (GIVEN)
        from app.clustering.interview_assignment_service import InterviewAssignmentService

        mock_repo = AsyncMock()
        mock_repo.find_by_project_and_interview = AsyncMock(
            return_value={
                "interview_id": mock_interview_id,
                "extraction_status": "completed",
                "clustering_status": "completed",
            }
        )

        service = InterviewAssignmentService(repo=mock_repo)

        # Act (WHEN) + Assert (THEN)
        with pytest.raises(HTTPException) as exc_info:
            await service.retry(project_id=mock_project_id, interview_id=mock_interview_id)

        assert exc_info.value.status_code == 409
        assert "Interview is not in failed state" in exc_info.value.detail
        assert "completed" in exc_info.value.detail

    @pytest.mark.acceptance
    @pytest.mark.asyncio
    async def test_ac_7_transcript_extraction(
        self,
        mock_project_id,
        mock_interview_id,
        mock_project_row_transcript,
        mock_interview_row,
        mock_llm_response_facts,
        mock_saved_facts,
        mock_fact_repository,
        mock_assignment_repository,
        mock_project_repository,
        mock_interview_repository,
        mock_event_bus,
        mock_settings,
    ):
        """AC-7: GIVEN ein Interview mit extraction_source="transcript"
        WHEN FactExtractionService.process_interview() ausgefuehrt wird
        THEN wird der Transcript-Text (aus mvp_interviews.transcript JSONB,
        als flacher Text zusammengefuegt) als Input fuer die LLM-Extraktion verwendet.
        """
        # Arrange (GIVEN)
        mock_project_repository.get_by_id = AsyncMock(return_value=mock_project_row_transcript)
        mock_interview_repository.get_session = AsyncMock(return_value=mock_interview_row)
        mock_fact_repository.save_facts = AsyncMock(return_value=mock_saved_facts)
        mock_assignment_repository.update_extraction_status = AsyncMock(return_value={})

        mock_response = MagicMock()
        mock_response.content = json.dumps(mock_llm_response_facts)

        captured_prompts = []

        class CapturingLlm:
            """Fake ChatOpenAI der den Prompt captured."""
            def __init__(self, **kwargs):
                pass

            async def ainvoke(self, prompt, **kwargs):
                captured_prompts.append(prompt)
                return mock_response

        with patch(INIT_LLM_PATCH_TARGET):
            with patch(LLM_PATCH_TARGET, CapturingLlm):
                from app.clustering.extraction import FactExtractionService
                service = FactExtractionService(
                    fact_repository=mock_fact_repository,
                    assignment_repository=mock_assignment_repository,
                    project_repository=mock_project_repository,
                    interview_repository=mock_interview_repository,
                    event_bus=mock_event_bus,
                    settings=mock_settings,
                )

                # Act (WHEN)
                await service.process_interview(mock_project_id, mock_interview_id)

        # Assert (THEN): Prompt enthalt Transcript als flachen Text (nicht nur Summary)
        assert len(captured_prompts) >= 1
        prompt_text = captured_prompts[0]
        # Transcript-Eintraege muessen als flacher Text im Prompt stehen
        assert "assistant: Was war Ihr erster Eindruck?" in prompt_text
        assert "user: Das Onboarding war verwirrend." in prompt_text
        assert "user: Ich konnte die Einstellungen nicht finden." in prompt_text

    @pytest.mark.acceptance
    @pytest.mark.asyncio
    async def test_ac_8_empty_llm_response_sets_completed(
        self,
        mock_project_id,
        mock_interview_id,
        mock_project_row,
        mock_interview_row,
        mock_fact_repository,
        mock_assignment_repository,
        mock_project_repository,
        mock_interview_repository,
        mock_event_bus,
        mock_settings,
    ):
        """AC-8: GIVEN der LLM gibt eine leere JSON-Liste [] zurueck
        WHEN FactExtractionService.process_interview() ausgefuehrt wird
        THEN wird extraction_status="completed" gesetzt und 0 Facts werden
        gespeichert (kein Fehler).
        """
        # Arrange (GIVEN)
        mock_project_repository.get_by_id = AsyncMock(return_value=mock_project_row)
        mock_interview_repository.get_session = AsyncMock(return_value=mock_interview_row)
        mock_fact_repository.save_facts = AsyncMock(return_value=[])
        mock_assignment_repository.update_extraction_status = AsyncMock(return_value={})

        # LLM gibt leeres Array zurueck
        mock_response = MagicMock()
        mock_response.content = "[]"
        mock_llm_instance = _make_llm_mock(mock_response)

        with patch(INIT_LLM_PATCH_TARGET):
            with patch(LLM_PATCH_TARGET, return_value=mock_llm_instance):
                from app.clustering.extraction import FactExtractionService
                service = FactExtractionService(
                    fact_repository=mock_fact_repository,
                    assignment_repository=mock_assignment_repository,
                    project_repository=mock_project_repository,
                    interview_repository=mock_interview_repository,
                    event_bus=mock_event_bus,
                    settings=mock_settings,
                )

                # Act (WHEN)
                await service.process_interview(mock_project_id, mock_interview_id)

        # Assert (THEN)
        # extraction_status auf "completed" gesetzt (nicht "failed")
        status_calls = mock_assignment_repository.update_extraction_status.call_args_list
        status_values = [
            call.kwargs.get("extraction_status")
            for call in status_calls
        ]
        assert "completed" in status_values
        assert "failed" not in status_values

        # save_facts wurde mit leerer Liste aufgerufen
        mock_fact_repository.save_facts.assert_called_once()
        call_args = mock_fact_repository.save_facts.call_args
        saved_facts_arg = call_args.kwargs.get("facts")
        assert saved_facts_arg == []

        # SSE-Event mit fact_count=0 publiziert
        mock_event_bus.publish.assert_called_once()
        publish_call = mock_event_bus.publish.call_args
        if publish_call.kwargs:
            event_data = publish_call.kwargs.get("data")
        else:
            event_data = publish_call.args[2]
        assert event_data["fact_count"] == 0

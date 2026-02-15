# backend/tests/slices/backend-kern/test_slice_05_summary_injection.py
import pytest
import json
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from langchain_core.messages import HumanMessage, AIMessage, AIMessageChunk


# -- Fixtures --

@pytest.fixture
def mock_settings():
    """Mock Settings mit Test-Werten."""
    settings = MagicMock()
    settings.openrouter_api_key = "test-key"
    settings.interviewer_llm = "test-model"
    settings.interviewer_temperature = 1.0
    settings.interviewer_max_tokens = 4000
    settings.llm_timeout_seconds = 30
    settings.db_timeout_seconds = 10
    settings.supabase_url = "https://test.supabase.co"
    settings.supabase_key = "test-supabase-key"
    return settings


@pytest.fixture
def mock_llm_summary_response():
    """Mock LLM-Antwort fuer Summary-Generierung."""
    return AIMessage(
        content="- User findet das Bidding frustrierend\n"
                "- Preise sind intransparent\n"
                "- User wuenscht sich mehr Transparenz"
    )


@pytest.fixture
def sample_history():
    """Beispiel-Conversation-History."""
    return [
        AIMessage(content="Hallo! Was beschaeftigt dich bei Zipmend?"),
        HumanMessage(content="Das Bidding ist total frustrierend"),
        AIMessage(content="Was genau findest du am Bidding frustrierend?"),
        HumanMessage(content="Die Preise sind komplett intransparent"),
        AIMessage(content="Kannst du ein konkretes Beispiel nennen?"),
        HumanMessage(content="Ja, letztens hatte ich eine Sendung und wusste nicht warum der Preis so hoch war"),
    ]


@pytest.fixture
def summary_service(mock_settings, mock_llm_summary_response):
    """SummaryService mit gemocktem LLM."""
    with patch("app.insights.summary.ChatOpenAI") as MockChatOpenAI:
        mock_llm = AsyncMock()
        mock_llm.ainvoke = AsyncMock(return_value=mock_llm_summary_response)
        MockChatOpenAI.return_value = mock_llm

        from app.insights.summary import SummaryService
        service = SummaryService(settings=mock_settings)
        service._llm = mock_llm
        return service


@pytest.fixture
def mock_graph():
    """Mock InterviewGraph mit set_summaries Methode."""
    graph = AsyncMock()
    graph._current_summaries = []

    def mock_set_summaries(summaries):
        graph._current_summaries = summaries or []

    graph.set_summaries = mock_set_summaries

    async def mock_astream(messages, session_id):
        chunks = [
            (AIMessageChunk(content="Hallo"), {"langgraph_node": "interviewer"}),
            (AIMessageChunk(content="! Wie geht es?"), {"langgraph_node": "interviewer"}),
        ]
        for chunk in chunks:
            yield chunk

    graph.astream = mock_astream
    # WICHTIG: get_history ist synchron, nicht async! Nutze MagicMock, nicht AsyncMock.return_value
    graph.get_history = MagicMock(return_value=[
        HumanMessage(content="Das Bidding nervt"),
        AIMessage(content="Was genau findest du frustrierend?"),
    ])
    return graph


@pytest.fixture
def mock_repository():
    """Mock InterviewRepository."""
    repo = AsyncMock()
    repo.create_session.return_value = {"session_id": "test-session", "status": "active"}
    repo.complete_session.return_value = {"session_id": "test-session", "status": "completed"}
    repo.increment_message_count.return_value = None
    repo.get_recent_summaries.return_value = []
    return repo


@pytest.fixture
def mock_summary_service(mock_llm_summary_response):
    """Mock SummaryService."""
    service = AsyncMock()
    service.generate.return_value = (
        "- User findet das Bidding frustrierend\n"
        "- Preise sind intransparent\n"
        "- User wuenscht sich mehr Transparenz"
    )
    return service


# -- SummaryService --

class TestSummaryServiceInit:
    """AC 10: SummaryService Konfiguration."""

    def test_summary_service_uses_openrouter(self, mock_settings):
        """AC 10: SummaryService nutzt OpenRouter."""
        with patch("app.insights.summary.ChatOpenAI") as MockChatOpenAI:
            MockChatOpenAI.return_value = MagicMock()
            from app.insights.summary import SummaryService
            SummaryService(settings=mock_settings)

            MockChatOpenAI.assert_called_once()
            call_kwargs = MockChatOpenAI.call_args[1]
            assert call_kwargs["base_url"] == "https://openrouter.ai/api/v1"

    def test_summary_service_uses_low_temperature(self, mock_settings):
        """AC 10: SummaryService nutzt temperature=0.3."""
        with patch("app.insights.summary.ChatOpenAI") as MockChatOpenAI:
            MockChatOpenAI.return_value = MagicMock()
            from app.insights.summary import SummaryService
            SummaryService(settings=mock_settings)

            call_kwargs = MockChatOpenAI.call_args[1]
            assert call_kwargs["temperature"] == 0.3

    def test_summary_service_uses_max_tokens_2000(self, mock_settings):
        """AC 10: SummaryService nutzt max_tokens=2000."""
        with patch("app.insights.summary.ChatOpenAI") as MockChatOpenAI:
            MockChatOpenAI.return_value = MagicMock()
            from app.insights.summary import SummaryService
            SummaryService(settings=mock_settings)

            call_kwargs = MockChatOpenAI.call_args[1]
            assert call_kwargs["max_tokens"] == 2000


class TestSummaryServiceGenerate:
    """AC 1, 6, 7: Summary-Generierung."""

    @pytest.mark.asyncio
    async def test_generate_returns_summary_string(self, summary_service, sample_history):
        """AC 1: generate() gibt einen Summary-String zurueck."""
        result = await summary_service.generate(sample_history)
        assert isinstance(result, str)
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_generate_calls_llm(self, summary_service, sample_history):
        """generate() ruft den LLM auf."""
        await summary_service.generate(sample_history)
        summary_service._llm.ainvoke.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_empty_history_returns_fallback(self, summary_service):
        """AC 7: Leere History gibt Fallback-Summary ohne LLM-Call."""
        result = await summary_service.generate([])
        assert result == "- Keine Inhalte im Interview"
        summary_service._llm.ainvoke.assert_not_called()

    @pytest.mark.asyncio
    async def test_generate_summary_contains_bullet_points(self, summary_service, sample_history):
        """AC 6: Summary enthaelt Bullet-Punkte mit '- '."""
        result = await summary_service.generate(sample_history)
        lines = [line for line in result.split("\n") if line.strip()]
        for line in lines:
            assert line.strip().startswith("- "), f"Line does not start with '- ': {line}"


class TestSummaryServiceFormatting:
    """SummaryService._format_messages_for_summary."""

    def test_format_messages_includes_roles(self):
        """Messages werden mit Interviewer/User Rollen formatiert."""
        from app.insights.summary import SummaryService
        messages = [
            AIMessage(content="Frage?"),
            HumanMessage(content="Antwort."),
        ]
        result = SummaryService._format_messages_for_summary(messages)
        assert "Interviewer: Frage?" in result
        assert "User: Antwort." in result

    def test_format_messages_empty_list(self):
        """Leere Liste ergibt leeren String."""
        from app.insights.summary import SummaryService
        result = SummaryService._format_messages_for_summary([])
        assert result == ""

    def test_format_messages_skips_empty_content(self):
        """Messages ohne Content werden uebersprungen."""
        from app.insights.summary import SummaryService
        messages = [
            AIMessage(content=""),
            HumanMessage(content="Test"),
        ]
        result = SummaryService._format_messages_for_summary(messages)
        assert "Interviewer" not in result
        assert "User: Test" in result


class TestSummaryServiceTimeout:
    """AC 8: Summary-LLM-Timeout wird korrekt behandelt."""

    @pytest.mark.asyncio
    async def test_timeout_raises_error(self, mock_settings):
        """AC 8: TimeoutError bei langsamem LLM."""
        with patch("app.insights.summary.ChatOpenAI") as MockChatOpenAI:
            async def slow_invoke(*args, **kwargs):
                await asyncio.sleep(100)
                return AIMessage(content="Zu spaet")

            mock_llm = AsyncMock()
            mock_llm.ainvoke = slow_invoke
            MockChatOpenAI.return_value = mock_llm

            mock_settings.llm_timeout_seconds = 0.1

            from app.insights.summary import SummaryService
            service = SummaryService(settings=mock_settings)
            service._llm = mock_llm

            with pytest.raises(asyncio.TimeoutError):
                await service.generate([
                    HumanMessage(content="Test"),
                    AIMessage(content="Antwort"),
                ])


# -- InterviewGraph set_summaries --

class TestInterviewGraphSummaries:
    """InterviewGraph akzeptiert Summaries."""

    def test_graph_has_set_summaries_method(self):
        """InterviewGraph hat set_summaries() Methode."""
        with patch("app.interview.graph.ChatOpenAI"):
            with patch.dict("os.environ", {
                "OPENROUTER_API_KEY": "test",
                "SUPABASE_URL": "https://test.supabase.co",
                "SUPABASE_KEY": "test-key",
            }, clear=False):
                from app.config.settings import Settings
                from app.interview.graph import InterviewGraph
                settings = Settings()
                graph = InterviewGraph(settings=settings)
                assert hasattr(graph, "set_summaries")
                assert callable(graph.set_summaries)

    def test_set_summaries_stores_summaries(self):
        """set_summaries() speichert die Summaries."""
        with patch("app.interview.graph.ChatOpenAI"):
            with patch.dict("os.environ", {
                "OPENROUTER_API_KEY": "test",
                "SUPABASE_URL": "https://test.supabase.co",
                "SUPABASE_KEY": "test-key",
            }, clear=False):
                from app.config.settings import Settings
                from app.interview.graph import InterviewGraph
                settings = Settings()
                graph = InterviewGraph(settings=settings)
                summaries = ["Summary 1", "Summary 2"]
                graph.set_summaries(summaries)
                assert graph._current_summaries == summaries

    def test_set_summaries_with_none(self):
        """set_summaries(None) setzt leere Liste."""
        with patch("app.interview.graph.ChatOpenAI"):
            with patch.dict("os.environ", {
                "OPENROUTER_API_KEY": "test",
                "SUPABASE_URL": "https://test.supabase.co",
                "SUPABASE_KEY": "test-key",
            }, clear=False):
                from app.config.settings import Settings
                from app.interview.graph import InterviewGraph
                settings = Settings()
                graph = InterviewGraph(settings=settings)
                graph.set_summaries(None)
                assert graph._current_summaries == []

    def test_graph_has_current_summaries_attribute(self):
        """InterviewGraph hat _current_summaries Attribut."""
        with patch("app.interview.graph.ChatOpenAI"):
            with patch.dict("os.environ", {
                "OPENROUTER_API_KEY": "test",
                "SUPABASE_URL": "https://test.supabase.co",
                "SUPABASE_KEY": "test-key",
            }, clear=False):
                from app.config.settings import Settings
                from app.interview.graph import InterviewGraph
                settings = Settings()
                graph = InterviewGraph(settings=settings)
                assert hasattr(graph, "_current_summaries")
                assert graph._current_summaries == []


# -- InterviewService Summary-Integration --

class TestInterviewServiceSummaryEnd:
    """AC 1, 2, 8: InterviewService.end() nutzt SummaryService."""

    @pytest.mark.asyncio
    async def test_end_calls_summary_service(self, mock_graph, mock_repository, mock_summary_service):
        """AC 1: end() ruft SummaryService.generate() auf."""
        from app.interview.service import InterviewService
        service = InterviewService(
            graph=mock_graph,
            repository=mock_repository,
            summary_service=mock_summary_service,
        )

        # Session starten
        async for _ in service.start("test-user"):
            pass
        session_id = list(service._sessions.keys())[0]

        # Session beenden
        await service.end(session_id)

        mock_summary_service.generate.assert_called_once()

    @pytest.mark.asyncio
    async def test_end_returns_real_summary(self, mock_graph, mock_repository, mock_summary_service):
        """AC 1: end() gibt echte Summary zurueck (nicht Placeholder)."""
        from app.interview.service import InterviewService
        service = InterviewService(
            graph=mock_graph,
            repository=mock_repository,
            summary_service=mock_summary_service,
        )

        async for _ in service.start("test-user"):
            pass
        session_id = list(service._sessions.keys())[0]

        result = await service.end(session_id)
        assert "Bidding frustrierend" in result["summary"]
        assert "noch nicht implementiert" not in result["summary"]

    @pytest.mark.asyncio
    async def test_end_saves_real_summary_to_db(self, mock_graph, mock_repository, mock_summary_service):
        """AC 2: Echte Summary wird in DB gespeichert."""
        from app.interview.service import InterviewService
        service = InterviewService(
            graph=mock_graph,
            repository=mock_repository,
            summary_service=mock_summary_service,
        )

        async for _ in service.start("test-user"):
            pass
        session_id = list(service._sessions.keys())[0]

        await service.end(session_id)

        mock_repository.complete_session.assert_called_once()
        call_kwargs = mock_repository.complete_session.call_args[1]
        assert "Bidding frustrierend" in call_kwargs["summary"]

    @pytest.mark.asyncio
    async def test_end_handles_summary_failure(self, mock_graph, mock_repository):
        """AC 8: Summary-Fehler fuehrt zu Fallback, Interview wird trotzdem completed."""
        failing_summary_service = AsyncMock()
        failing_summary_service.generate.side_effect = Exception("LLM unavailable")

        from app.interview.service import InterviewService
        service = InterviewService(
            graph=mock_graph,
            repository=mock_repository,
            summary_service=failing_summary_service,
        )

        async for _ in service.start("test-user"):
            pass
        session_id = list(service._sessions.keys())[0]

        result = await service.end(session_id)
        assert result["summary"] == "Summary-Generierung fehlgeschlagen"
        assert service._sessions[session_id]["status"] == "completed"

    @pytest.mark.asyncio
    async def test_end_handles_timeout_failure(self, mock_graph, mock_repository):
        """AC 8: Timeout fuehrt zu Fallback-Summary."""
        timeout_summary_service = AsyncMock()
        timeout_summary_service.generate.side_effect = asyncio.TimeoutError()

        from app.interview.service import InterviewService
        service = InterviewService(
            graph=mock_graph,
            repository=mock_repository,
            summary_service=timeout_summary_service,
        )

        async for _ in service.start("test-user"):
            pass
        session_id = list(service._sessions.keys())[0]

        result = await service.end(session_id)
        assert result["summary"] == "Summary-Generierung fehlgeschlagen"
        assert service._sessions[session_id]["status"] == "completed"

    @pytest.mark.asyncio
    async def test_end_without_summary_service_uses_fallback(self, mock_graph, mock_repository):
        """Service ohne SummaryService gibt Fallback-Summary."""
        from app.interview.service import InterviewService
        service = InterviewService(
            graph=mock_graph,
            repository=mock_repository,
            summary_service=None,
        )

        async for _ in service.start("test-user"):
            pass
        session_id = list(service._sessions.keys())[0]

        result = await service.end(session_id)
        assert result["summary"] == "Keine Summary verfuegbar"


class TestInterviewServiceSummaryInjection:
    """AC 3, 4, 5, 9: InterviewService.start() injiziert Summaries."""

    @pytest.mark.asyncio
    async def test_start_loads_recent_summaries(self, mock_graph, mock_repository, mock_summary_service):
        """AC 3: start() ruft repository.get_recent_summaries() auf."""
        mock_repository.get_recent_summaries.return_value = [
            "- User findet Bidding frustrierend",
        ]

        from app.interview.service import InterviewService
        service = InterviewService(
            graph=mock_graph,
            repository=mock_repository,
            summary_service=mock_summary_service,
        )

        async for _ in service.start("test-user"):
            pass

        mock_repository.get_recent_summaries.assert_called_once_with(
            "test-user", limit=3
        )

    @pytest.mark.asyncio
    async def test_start_sets_summaries_on_graph(self, mock_graph, mock_repository, mock_summary_service):
        """AC 3: start() setzt Summaries auf dem Graph."""
        previous_summaries = [
            "- User findet Bidding frustrierend",
            "- Preise sind intransparent",
        ]
        mock_repository.get_recent_summaries.return_value = previous_summaries

        from app.interview.service import InterviewService
        service = InterviewService(
            graph=mock_graph,
            repository=mock_repository,
            summary_service=mock_summary_service,
        )

        async for _ in service.start("test-user"):
            pass

        assert mock_graph._current_summaries == previous_summaries

    @pytest.mark.asyncio
    async def test_start_no_previous_summaries(self, mock_graph, mock_repository, mock_summary_service):
        """AC 5: Ohne vorherige Summaries wird leere Liste gesetzt."""
        mock_repository.get_recent_summaries.return_value = []

        from app.interview.service import InterviewService
        service = InterviewService(
            graph=mock_graph,
            repository=mock_repository,
            summary_service=mock_summary_service,
        )

        async for _ in service.start("new-user"):
            pass

        assert mock_graph._current_summaries == []

    @pytest.mark.asyncio
    async def test_start_limits_summaries_to_3(self, mock_graph, mock_repository, mock_summary_service):
        """AC 4: get_recent_summaries wird mit limit=3 aufgerufen."""
        mock_repository.get_recent_summaries.return_value = []

        from app.interview.service import InterviewService
        service = InterviewService(
            graph=mock_graph,
            repository=mock_repository,
            summary_service=mock_summary_service,
        )

        async for _ in service.start("test-user"):
            pass

        mock_repository.get_recent_summaries.assert_called_once_with(
            "test-user", limit=3
        )

    @pytest.mark.asyncio
    async def test_start_handles_db_error_for_summaries(self, mock_graph, mock_repository, mock_summary_service):
        """AC 9: DB-Fehler bei Summary-Loading blockiert nicht den Start."""
        mock_repository.get_recent_summaries.side_effect = Exception("DB connection refused")

        from app.interview.service import InterviewService
        service = InterviewService(
            graph=mock_graph,
            repository=mock_repository,
            summary_service=mock_summary_service,
        )

        events = []
        async for event_data in service.start("test-user"):
            events.append(json.loads(event_data))

        # Interview wurde trotzdem gestartet
        metadata = [e for e in events if e.get("type") == "metadata"]
        assert len(metadata) == 1

        # Leere Summaries als Fallback
        assert mock_graph._current_summaries == []

    @pytest.mark.asyncio
    async def test_start_without_repository_no_summaries(self, mock_graph, mock_summary_service):
        """Ohne Repository werden keine Summaries geladen."""
        from app.interview.service import InterviewService
        service = InterviewService(
            graph=mock_graph,
            repository=None,
            summary_service=mock_summary_service,
        )

        async for _ in service.start("test-user"):
            pass

        assert mock_graph._current_summaries == []


# -- PromptAssembler Integration (Regression) --

class TestPromptAssemblerIntegration:
    """Regression: PromptAssembler.build() funktioniert weiterhin korrekt mit Summaries."""

    def test_build_with_real_summaries(self):
        """PromptAssembler.build() injiziert echte Summaries korrekt."""
        from app.interview.prompt import PromptAssembler, SYSTEM_PROMPT
        summaries = [
            "- User findet Bidding frustrierend\n- Preise sind intransparent",
            "- Onboarding war verwirrend\n- UI ist zu komplex",
            "- User wuenscht sich bessere Dokumentation",
        ]
        result = PromptAssembler.build(summaries=summaries)
        assert SYSTEM_PROMPT in result
        assert "KONTEXT AUS VORHERIGEN GESPRAECHEN" in result
        assert "Gespraech 1" in result
        assert "Gespraech 2" in result
        assert "Gespraech 3" in result
        assert "Bidding frustrierend" in result
        assert "Onboarding war verwirrend" in result
        assert "bessere Dokumentation" in result


# -- SUMMARY_PROMPT --

class TestSummaryPrompt:
    """Summary-Prompt Template ist korrekt definiert."""

    def test_summary_prompt_exists(self):
        """SUMMARY_PROMPT ist definiert."""
        from app.insights.summary import SUMMARY_PROMPT
        assert isinstance(SUMMARY_PROMPT, str)
        assert len(SUMMARY_PROMPT) > 0

    def test_summary_prompt_has_transcript_placeholder(self):
        """SUMMARY_PROMPT hat {transcript} Placeholder."""
        from app.insights.summary import SUMMARY_PROMPT
        assert "{transcript}" in SUMMARY_PROMPT

    def test_summary_prompt_mentions_bullet_format(self):
        """SUMMARY_PROMPT erwaaehnt Bullet-Format."""
        from app.insights.summary import SUMMARY_PROMPT
        assert "- " in SUMMARY_PROMPT


# -- Dependency Injection --

class TestDependencyInjection:
    """InterviewService akzeptiert summary_service Parameter."""

    def test_service_accepts_summary_service(self):
        """InterviewService Constructor hat summary_service Parameter."""
        import inspect
        from app.interview.service import InterviewService
        sig = inspect.signature(InterviewService.__init__)
        assert "summary_service" in sig.parameters

    def test_service_summary_service_is_optional(self):
        """summary_service Parameter ist optional (Default: None)."""
        import inspect
        from app.interview.service import InterviewService
        sig = inspect.signature(InterviewService.__init__)
        param = sig.parameters["summary_service"]
        assert param.default is None


# -- Modul-Existenz --

class TestModuleStructure:
    """Alle neuen/geaenderten Dateien existieren und sind importierbar."""

    def test_summary_service_importable(self):
        """insights/summary.py ist importierbar."""
        from app.insights.summary import SummaryService, SUMMARY_PROMPT
        assert SummaryService is not None
        assert SUMMARY_PROMPT is not None

    def test_summary_service_has_generate_method(self):
        """SummaryService hat generate() Methode."""
        from app.insights.summary import SummaryService
        assert hasattr(SummaryService, "generate")

    def test_summary_service_has_format_method(self):
        """SummaryService hat _format_messages_for_summary() Methode."""
        from app.insights.summary import SummaryService
        assert hasattr(SummaryService, "_format_messages_for_summary")

    def test_graph_has_set_summaries(self):
        """InterviewGraph hat set_summaries() Methode."""
        with patch("app.interview.graph.ChatOpenAI"):
            from app.interview.graph import InterviewGraph
            assert hasattr(InterviewGraph, "set_summaries")

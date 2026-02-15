# backend/tests/slices/backend-kern/test_slice_06_session_timeout.py
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
from langchain_core.messages import HumanMessage, AIMessage, AIMessageChunk


# -- Fixtures --

@pytest.fixture
def mock_callback():
    """Mock async Callback fuer TimeoutManager."""
    return AsyncMock()


@pytest.fixture
def timeout_manager(mock_callback):
    """TimeoutManager mit kurzem Timeout fuer Tests."""
    from app.interview.timeout import TimeoutManager
    return TimeoutManager(
        timeout_seconds=1,
        on_timeout_callback=mock_callback,
    )


@pytest.fixture
def fast_timeout_manager(mock_callback):
    """TimeoutManager mit sehr kurzem Timeout (0.1s) fuer schnelle Tests."""
    from app.interview.timeout import TimeoutManager
    return TimeoutManager(
        timeout_seconds=0.1,
        on_timeout_callback=mock_callback,
    )


@pytest.fixture
def mock_graph():
    """Mock InterviewGraph."""
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
    # get_history is synchronous, so we use MagicMock instead of relying on AsyncMock
    graph.get_history = MagicMock(return_value=[
        AIMessage(content="Hallo! Was beschaeftigt dich?"),
        HumanMessage(content="Das Bidding nervt"),
        AIMessage(content="Was genau findest du frustrierend?"),
    ])
    return graph


@pytest.fixture
def mock_repository():
    """Mock InterviewRepository."""
    repo = AsyncMock()
    repo.create_session.return_value = {"session_id": "test-session", "status": "active"}
    repo.complete_session.return_value = {"session_id": "test-session", "status": "completed_timeout"}
    repo.increment_message_count.return_value = None
    repo.get_recent_summaries.return_value = []
    return repo


@pytest.fixture
def mock_summary_service():
    """Mock SummaryService."""
    service = AsyncMock()
    service.generate.return_value = (
        "- User findet das Bidding frustrierend\n"
        "- Preise sind intransparent"
    )
    return service


# -- TimeoutManager: register/reset/cancel --

class TestTimeoutManagerRegister:
    """AC 8: register() erstellt asyncio.Task."""

    @pytest.mark.asyncio
    async def test_register_creates_task(self, timeout_manager):
        """AC 8: register() erstellt einen Task fuer die Session."""
        timeout_manager.register("session-1")
        assert timeout_manager.active_count == 1

        # Cleanup
        timeout_manager.cancel_all()

    @pytest.mark.asyncio
    async def test_register_replaces_existing_task(self, timeout_manager):
        """register() ersetzt bestehenden Task."""
        timeout_manager.register("session-1")
        timeout_manager.register("session-1")
        assert timeout_manager.active_count == 1

        # Cleanup
        timeout_manager.cancel_all()

    @pytest.mark.asyncio
    async def test_register_multiple_sessions(self, timeout_manager):
        """AC 6: Mehrere Sessions koennen parallel registriert werden."""
        timeout_manager.register("session-1")
        timeout_manager.register("session-2")
        timeout_manager.register("session-3")
        assert timeout_manager.active_count == 3

        # Cleanup
        timeout_manager.cancel_all()


class TestTimeoutManagerReset:
    """AC 3: reset() setzt Timer zurueck."""

    @pytest.mark.asyncio
    async def test_reset_restarts_timer(self, fast_timeout_manager, mock_callback):
        """AC 3: reset() startet den Timer neu."""
        fast_timeout_manager.register("session-1")
        await asyncio.sleep(0.05)  # Halbe Zeit warten
        fast_timeout_manager.reset("session-1")
        await asyncio.sleep(0.05)  # Nochmal halbe Zeit -- waere ohne Reset getimed out

        # Sollte noch NICHT getimed out sein (Timer wurde zurueckgesetzt)
        mock_callback.assert_not_called()

        # Cleanup
        fast_timeout_manager.cancel_all()

    @pytest.mark.asyncio
    async def test_reset_unknown_session_creates_new(self, timeout_manager):
        """reset() auf unbekannte Session erstellt neuen Timer."""
        timeout_manager.reset("new-session")
        assert timeout_manager.active_count == 1

        # Cleanup
        timeout_manager.cancel_all()


class TestTimeoutManagerCancel:
    """AC 4: cancel() cancelt Timer."""

    @pytest.mark.asyncio
    async def test_cancel_removes_task(self, timeout_manager):
        """AC 4: cancel() entfernt den Task."""
        timeout_manager.register("session-1")
        assert timeout_manager.active_count == 1

        timeout_manager.cancel("session-1")
        # Task cleanup happens async, give it a moment
        await asyncio.sleep(0.01)
        assert timeout_manager.active_count == 0

    @pytest.mark.asyncio
    async def test_cancel_unknown_session_no_error(self, timeout_manager):
        """cancel() auf unbekannte Session wirft keinen Fehler."""
        timeout_manager.cancel("nonexistent")  # Kein Error

    @pytest.mark.asyncio
    async def test_cancel_prevents_timeout(self, fast_timeout_manager, mock_callback):
        """AC 4: cancel() verhindert dass der Timeout feuert."""
        fast_timeout_manager.register("session-1")
        fast_timeout_manager.cancel("session-1")
        await asyncio.sleep(0.2)  # Laenger als Timeout warten

        mock_callback.assert_not_called()


class TestTimeoutManagerCancelAll:
    """AC 7: cancel_all() cancelt alle Timer."""

    @pytest.mark.asyncio
    async def test_cancel_all_clears_tasks(self, timeout_manager):
        """AC 7: cancel_all() entfernt alle Tasks."""
        timeout_manager.register("session-1")
        timeout_manager.register("session-2")
        timeout_manager.register("session-3")
        assert timeout_manager.active_count == 3

        timeout_manager.cancel_all()
        await asyncio.sleep(0.01)
        assert timeout_manager.active_count == 0

    @pytest.mark.asyncio
    async def test_cancel_all_empty_no_error(self, timeout_manager):
        """cancel_all() ohne aktive Tasks wirft keinen Fehler."""
        timeout_manager.cancel_all()  # Kein Error


# -- TimeoutManager: Timeout-Callback --

class TestTimeoutCallback:
    """AC 1, 2, 6: Timeout feuert Callback."""

    @pytest.mark.asyncio
    async def test_timeout_fires_callback(self, fast_timeout_manager, mock_callback):
        """AC 1: Nach timeout_seconds wird der Callback aufgerufen."""
        fast_timeout_manager.register("session-1")
        await asyncio.sleep(0.2)  # Laenger als 0.1s Timeout warten

        mock_callback.assert_called_once_with("session-1")

    @pytest.mark.asyncio
    async def test_timeout_fires_only_for_timed_out_session(self, mock_callback):
        """AC 6: Timeout feuert nur fuer die betroffene Session."""
        from app.interview.timeout import TimeoutManager

        # Zwei Manager mit verschiedenen Timeouts simulieren via einen Manager
        manager = TimeoutManager(
            timeout_seconds=0.1,
            on_timeout_callback=mock_callback,
        )
        manager.register("session-fast")

        # session-fast soll nach 0.1s timen out, session-slow wird sofort gecancelt
        manager2 = TimeoutManager(
            timeout_seconds=10,
            on_timeout_callback=mock_callback,
        )
        manager2.register("session-slow")

        await asyncio.sleep(0.2)

        # Nur session-fast sollte getimed out sein
        mock_callback.assert_called_once_with("session-fast")

        # Cleanup
        manager2.cancel_all()

    @pytest.mark.asyncio
    async def test_timeout_removes_task_after_firing(self, fast_timeout_manager, mock_callback):
        """Task wird nach dem Feuern entfernt."""
        fast_timeout_manager.register("session-1")
        await asyncio.sleep(0.2)

        assert fast_timeout_manager.active_count == 0


class TestTimeoutCallbackErrors:
    """AC 5: Fehler im Callback werden abgefangen."""

    @pytest.mark.asyncio
    async def test_callback_error_is_caught(self):
        """Fehler im Callback fuehrt nicht zum Absturz."""
        from app.interview.timeout import TimeoutManager

        failing_callback = AsyncMock(side_effect=Exception("Callback failed"))
        manager = TimeoutManager(
            timeout_seconds=0.1,
            on_timeout_callback=failing_callback,
        )
        manager.register("session-1")
        await asyncio.sleep(0.2)

        # Callback wurde aufgerufen, aber Fehler wurde abgefangen
        failing_callback.assert_called_once()
        assert manager.active_count == 0  # Task wurde trotzdem aufgeraeumt


# -- InterviewService mit TimeoutManager --

class TestInterviewServiceTimeoutIntegration:
    """AC 1, 3, 4: InterviewService nutzt TimeoutManager."""

    @pytest.mark.asyncio
    async def test_start_registers_timeout(self, mock_graph, mock_repository, mock_summary_service):
        """AC 1 (indirekt): start() registriert Timeout."""
        from app.interview.service import InterviewService
        from app.interview.timeout import TimeoutManager

        timeout_callback = AsyncMock()
        timeout_manager = TimeoutManager(
            timeout_seconds=60,
            on_timeout_callback=timeout_callback,
        )

        service = InterviewService(
            graph=mock_graph,
            repository=mock_repository,
            summary_service=mock_summary_service,
            timeout_manager=timeout_manager,
        )

        async for _ in service.start("test-user"):
            pass

        assert timeout_manager.active_count == 1

        # Cleanup
        timeout_manager.cancel_all()

    @pytest.mark.asyncio
    async def test_message_resets_timeout(self, mock_graph, mock_repository, mock_summary_service):
        """AC 3: message() setzt Timeout zurueck."""
        from app.interview.service import InterviewService
        from app.interview.timeout import TimeoutManager

        timeout_callback = AsyncMock()
        timeout_manager = TimeoutManager(
            timeout_seconds=60,
            on_timeout_callback=timeout_callback,
        )

        service = InterviewService(
            graph=mock_graph,
            repository=mock_repository,
            summary_service=mock_summary_service,
            timeout_manager=timeout_manager,
        )

        async for _ in service.start("test-user"):
            pass
        session_id = list(service._sessions.keys())[0]

        # Message senden -> Timeout wird zurueckgesetzt
        async for _ in service.message(session_id, "Test"):
            pass

        # Timeout-Timer existiert noch
        assert timeout_manager.active_count == 1

        # Cleanup
        timeout_manager.cancel_all()

    @pytest.mark.asyncio
    async def test_end_cancels_timeout(self, mock_graph, mock_repository, mock_summary_service):
        """AC 4: end() cancelt Timeout."""
        from app.interview.service import InterviewService
        from app.interview.timeout import TimeoutManager

        timeout_callback = AsyncMock()
        timeout_manager = TimeoutManager(
            timeout_seconds=60,
            on_timeout_callback=timeout_callback,
        )

        service = InterviewService(
            graph=mock_graph,
            repository=mock_repository,
            summary_service=mock_summary_service,
            timeout_manager=timeout_manager,
        )

        async for _ in service.start("test-user"):
            pass
        session_id = list(service._sessions.keys())[0]

        await service.end(session_id)

        await asyncio.sleep(0.01)
        assert timeout_manager.active_count == 0

    @pytest.mark.asyncio
    async def test_service_works_without_timeout_manager(self, mock_graph, mock_repository, mock_summary_service):
        """Service funktioniert auch ohne TimeoutManager (timeout_manager=None)."""
        from app.interview.service import InterviewService
        service = InterviewService(
            graph=mock_graph,
            repository=mock_repository,
            summary_service=mock_summary_service,
            timeout_manager=None,
        )

        async for _ in service.start("test-user"):
            pass
        session_id = list(service._sessions.keys())[0]

        async for _ in service.message(session_id, "Test"):
            pass

        result = await service.end(session_id)
        assert "summary" in result


# -- InterviewService._handle_timeout --

class TestHandleTimeout:
    """AC 1, 2, 5, 9, 10: _handle_timeout Callback."""

    @pytest.mark.asyncio
    async def test_handle_timeout_completes_session(self, mock_graph, mock_repository, mock_summary_service):
        """AC 1: _handle_timeout setzt Status auf completed_timeout."""
        from app.interview.service import InterviewService
        service = InterviewService(
            graph=mock_graph,
            repository=mock_repository,
            summary_service=mock_summary_service,
        )

        # Session manuell erstellen
        service._sessions["test-session"] = {
            "status": "active",
            "anonymous_id": "user-1",
            "message_count": 2,
        }

        await service._handle_timeout("test-session")

        assert service._sessions["test-session"]["status"] == "completed_timeout"

    @pytest.mark.asyncio
    async def test_handle_timeout_generates_summary(self, mock_graph, mock_repository, mock_summary_service):
        """AC 2: _handle_timeout generiert Summary via SummaryService."""
        from app.interview.service import InterviewService
        service = InterviewService(
            graph=mock_graph,
            repository=mock_repository,
            summary_service=mock_summary_service,
        )

        service._sessions["test-session"] = {
            "status": "active",
            "anonymous_id": "user-1",
            "message_count": 1,
        }

        await service._handle_timeout("test-session")

        mock_summary_service.generate.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_timeout_saves_to_db(self, mock_graph, mock_repository, mock_summary_service):
        """AC 1: _handle_timeout speichert in DB mit status=completed_timeout."""
        from app.interview.service import InterviewService
        service = InterviewService(
            graph=mock_graph,
            repository=mock_repository,
            summary_service=mock_summary_service,
        )

        service._sessions["test-session"] = {
            "status": "active",
            "anonymous_id": "user-1",
            "message_count": 1,
        }

        await service._handle_timeout("test-session")

        mock_repository.complete_session.assert_called_once()
        call_kwargs = mock_repository.complete_session.call_args[1]
        assert call_kwargs["session_id"] == "test-session"
        assert call_kwargs["status"] == "completed_timeout"
        assert isinstance(call_kwargs["transcript"], list)

    @pytest.mark.asyncio
    async def test_handle_timeout_saves_transcript_format(self, mock_graph, mock_repository, mock_summary_service):
        """AC 10: Transcript Format ist identisch zu /end."""
        from app.interview.service import InterviewService
        service = InterviewService(
            graph=mock_graph,
            repository=mock_repository,
            summary_service=mock_summary_service,
        )

        service._sessions["test-session"] = {
            "status": "active",
            "anonymous_id": "user-1",
            "message_count": 1,
        }

        await service._handle_timeout("test-session")

        call_kwargs = mock_repository.complete_session.call_args[1]
        transcript = call_kwargs["transcript"]
        for entry in transcript:
            assert "role" in entry
            assert "content" in entry
            assert entry["role"] in ("user", "assistant")

    @pytest.mark.asyncio
    async def test_handle_timeout_summary_failure_still_completes(self, mock_graph, mock_repository):
        """AC 5: Summary-Fehler fuehrt zu summary=None, Session wird trotzdem completed_timeout."""
        failing_summary = AsyncMock()
        failing_summary.generate.side_effect = Exception("LLM unavailable")

        from app.interview.service import InterviewService
        service = InterviewService(
            graph=mock_graph,
            repository=mock_repository,
            summary_service=failing_summary,
        )

        service._sessions["test-session"] = {
            "status": "active",
            "anonymous_id": "user-1",
            "message_count": 0,
        }

        await service._handle_timeout("test-session")

        # Session ist trotzdem als completed_timeout markiert
        assert service._sessions["test-session"]["status"] == "completed_timeout"
        # DB-Call wurde mit summary=None aufgerufen
        call_kwargs = mock_repository.complete_session.call_args[1]
        assert call_kwargs["summary"] is None
        assert call_kwargs["status"] == "completed_timeout"

    @pytest.mark.asyncio
    async def test_handle_timeout_ignores_already_completed(self, mock_graph, mock_repository, mock_summary_service):
        """AC 9: Timeout auf bereits beendete Session wird ignoriert."""
        from app.interview.service import InterviewService
        service = InterviewService(
            graph=mock_graph,
            repository=mock_repository,
            summary_service=mock_summary_service,
        )

        service._sessions["test-session"] = {
            "status": "completed",
            "anonymous_id": "user-1",
            "message_count": 1,
        }

        await service._handle_timeout("test-session")

        # Kein DB-Call, kein Summary-Call
        mock_summary_service.generate.assert_not_called()
        mock_repository.complete_session.assert_not_called()

    @pytest.mark.asyncio
    async def test_handle_timeout_ignores_unknown_session(self, mock_graph, mock_repository, mock_summary_service):
        """AC 9: Timeout auf unbekannte Session wird ignoriert."""
        from app.interview.service import InterviewService
        service = InterviewService(
            graph=mock_graph,
            repository=mock_repository,
            summary_service=mock_summary_service,
        )

        await service._handle_timeout("unknown-session")

        mock_summary_service.generate.assert_not_called()
        mock_repository.complete_session.assert_not_called()

    @pytest.mark.asyncio
    async def test_handle_timeout_db_error_still_updates_memory(self, mock_graph, mock_summary_service):
        """DB-Fehler bei Timeout aktualisiert trotzdem In-Memory Status."""
        failing_repo = AsyncMock()
        failing_repo.complete_session.side_effect = Exception("DB connection refused")

        from app.interview.service import InterviewService
        service = InterviewService(
            graph=mock_graph,
            repository=failing_repo,
            summary_service=mock_summary_service,
        )

        service._sessions["test-session"] = {
            "status": "active",
            "anonymous_id": "user-1",
            "message_count": 0,
        }

        await service._handle_timeout("test-session")

        # In-Memory Status wurde trotzdem aktualisiert
        assert service._sessions["test-session"]["status"] == "completed_timeout"


# -- End-to-End: Timeout fires Auto-Summary --

class TestEndToEndTimeout:
    """AC 1, 2: Vollstaendiger Timeout-Flow mit kurzem Timer."""

    @pytest.mark.asyncio
    async def test_full_timeout_flow(self, mock_graph, mock_repository, mock_summary_service):
        """AC 1 + AC 2: Session starten, warten, Auto-Summary + completed_timeout."""
        from app.interview.service import InterviewService
        from app.interview.timeout import TimeoutManager

        service = InterviewService(
            graph=mock_graph,
            repository=mock_repository,
            summary_service=mock_summary_service,
        )

        timeout_manager = TimeoutManager(
            timeout_seconds=0.1,
            on_timeout_callback=service._handle_timeout,
        )
        service._timeout_manager = timeout_manager

        # Session starten
        async for _ in service.start("test-user"):
            pass
        session_id = list(service._sessions.keys())[0]

        # Warten bis Timeout feuert
        await asyncio.sleep(0.3)

        # Session sollte als completed_timeout markiert sein
        assert service._sessions[session_id]["status"] == "completed_timeout"

        # DB-Call mit completed_timeout
        mock_repository.complete_session.assert_called_once()
        call_kwargs = mock_repository.complete_session.call_args[1]
        assert call_kwargs["status"] == "completed_timeout"

        # Summary wurde generiert
        mock_summary_service.generate.assert_called_once()

    @pytest.mark.asyncio
    async def test_message_prevents_timeout(self, mock_graph, mock_repository, mock_summary_service):
        """AC 3: message() setzt Timer zurueck, verhindert Timeout."""
        from app.interview.service import InterviewService
        from app.interview.timeout import TimeoutManager

        service = InterviewService(
            graph=mock_graph,
            repository=mock_repository,
            summary_service=mock_summary_service,
        )

        timeout_manager = TimeoutManager(
            timeout_seconds=0.2,
            on_timeout_callback=service._handle_timeout,
        )
        service._timeout_manager = timeout_manager

        # Session starten
        async for _ in service.start("test-user"):
            pass
        session_id = list(service._sessions.keys())[0]

        # Vor Timeout eine Message senden (bei 0.1s von 0.2s)
        await asyncio.sleep(0.1)
        async for _ in service.message(session_id, "Noch da"):
            pass

        # Nochmal 0.1s warten -- waere ohne Reset getimed out
        await asyncio.sleep(0.1)

        # Session sollte noch aktiv sein
        assert service._sessions[session_id]["status"] == "active"

        # Cleanup
        timeout_manager.cancel_all()


# -- Dependency Injection --

class TestDependencyInjection:
    """InterviewService akzeptiert timeout_manager Parameter."""

    def test_service_accepts_timeout_manager(self):
        """InterviewService Constructor hat timeout_manager Parameter."""
        import inspect
        from app.interview.service import InterviewService
        sig = inspect.signature(InterviewService.__init__)
        assert "timeout_manager" in sig.parameters

    def test_service_timeout_manager_is_optional(self):
        """timeout_manager Parameter ist optional (Default: None)."""
        import inspect
        from app.interview.service import InterviewService
        sig = inspect.signature(InterviewService.__init__)
        param = sig.parameters["timeout_manager"]
        assert param.default is None


# -- Modul-Existenz --

class TestModuleStructure:
    """Alle neuen/geaenderten Dateien existieren und sind importierbar."""

    def test_timeout_module_importable(self):
        """interview/timeout.py ist importierbar."""
        from app.interview.timeout import TimeoutManager
        assert TimeoutManager is not None

    def test_timeout_manager_has_required_methods(self):
        """TimeoutManager hat alle erforderlichen Methoden."""
        from app.interview.timeout import TimeoutManager
        assert hasattr(TimeoutManager, "register")
        assert hasattr(TimeoutManager, "reset")
        assert hasattr(TimeoutManager, "cancel")
        assert hasattr(TimeoutManager, "cancel_all")

    def test_timeout_manager_has_active_count(self):
        """TimeoutManager hat active_count Property."""
        from app.interview.timeout import TimeoutManager
        assert hasattr(TimeoutManager, "active_count")

    def test_service_has_handle_timeout(self):
        """InterviewService hat _handle_timeout Methode."""
        from app.interview.service import InterviewService
        assert hasattr(InterviewService, "_handle_timeout")

# backend/tests/slices/backend-kern/test_slice_04_supabase_persistenz.py
import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from langchain_core.messages import HumanMessage, AIMessage


# -- Fixtures --

@pytest.fixture
def mock_settings():
    """Mock Settings mit Test-Werten."""
    settings = MagicMock()
    settings.supabase_url = "https://test.supabase.co"
    settings.supabase_key = "test-key"
    settings.db_timeout_seconds = 10
    settings.openrouter_api_key = "test-key"
    settings.interviewer_llm = "test-model"
    settings.interviewer_temperature = 1.0
    settings.interviewer_max_tokens = 4000
    settings.llm_timeout_seconds = 30
    return settings


@pytest.fixture
def mock_supabase_client():
    """Mock Supabase Client mit chainable API."""
    client = MagicMock()

    # Chainable mock fuer table().insert().execute() etc.
    def create_chain_mock(return_data=None):
        """Erstellt einen chainable Mock der execute() mit data zurueckgibt."""
        mock = MagicMock()
        response = MagicMock()
        response.data = return_data or []

        # Jede Methode gibt denselben Mock zurueck (chaining)
        mock.insert.return_value = mock
        mock.select.return_value = mock
        mock.update.return_value = mock
        mock.delete.return_value = mock
        mock.eq.return_value = mock
        mock.in_.return_value = mock
        mock.not_ = mock
        mock.is_.return_value = mock
        mock.order.return_value = mock
        mock.limit.return_value = mock
        mock.execute.return_value = response
        return mock

    client._chain_mock = create_chain_mock
    chain = create_chain_mock([{
        "id": "test-uuid",
        "session_id": "test-session",
        "anonymous_id": "test-user",
        "status": "active",
        "transcript": None,
        "summary": None,
        "message_count": 0,
        "created_at": "2026-02-13T10:00:00+00:00",
        "updated_at": "2026-02-13T10:00:00+00:00",
        "completed_at": None,
    }])
    client.table.return_value = chain
    return client


@pytest.fixture
def repository(mock_supabase_client, mock_settings):
    """InterviewRepository mit gemocktem Supabase Client."""
    from app.interview.repository import InterviewRepository
    return InterviewRepository(
        supabase_client=mock_supabase_client,
        settings=mock_settings,
    )


@pytest.fixture
def mock_graph():
    """Mock InterviewGraph."""
    from langchain_core.messages import AIMessageChunk

    graph = AsyncMock()

    async def mock_astream(messages, session_id):
        chunks = [
            (AIMessageChunk(content="Hallo"), {"langgraph_node": "interviewer"}),
            (AIMessageChunk(content="! Wie geht es?"), {"langgraph_node": "interviewer"}),
        ]
        for chunk in chunks:
            yield chunk

    graph.astream = mock_astream
    graph.get_history.return_value = [
        HumanMessage(content="Das Bidding nervt"),
        AIMessage(content="Was genau findest du frustrierend?"),
    ]
    return graph


@pytest.fixture
def mock_repository():
    """Mock InterviewRepository."""
    repo = AsyncMock()
    repo.create_session.return_value = {"session_id": "test-session", "status": "active"}
    repo.complete_session.return_value = {"session_id": "test-session", "status": "completed"}
    repo.increment_message_count.return_value = None
    repo.update_timestamp.return_value = None
    repo.get_recent_summaries.return_value = []
    return repo


# -- Supabase Client Singleton --

class TestSupabaseClientSingleton:
    """AC 7: Supabase Client ist ein Singleton."""

    def test_get_client_returns_same_instance(self, mock_settings):
        """AC 7: Mehrfache Aufrufe geben dieselbe Instanz zurueck."""
        from app.db.supabase import reset_supabase_client

        reset_supabase_client()
        with patch("app.db.supabase.create_client") as mock_create:
            mock_client = MagicMock()
            mock_create.return_value = mock_client

            from app.db.supabase import get_supabase_client
            client1 = get_supabase_client(mock_settings)
            client2 = get_supabase_client(mock_settings)

            assert client1 is client2
            mock_create.assert_called_once()

        reset_supabase_client()

    def test_reset_clears_singleton(self, mock_settings):
        """reset_supabase_client setzt den Singleton zurueck."""
        from app.db.supabase import get_supabase_client, reset_supabase_client

        reset_supabase_client()
        with patch("app.db.supabase.create_client") as mock_create:
            mock_create.return_value = MagicMock()

            client1 = get_supabase_client(mock_settings)
            reset_supabase_client()
            client2 = get_supabase_client(mock_settings)

            assert client1 is not client2
            assert mock_create.call_count == 2

        reset_supabase_client()


# -- InterviewRepository --

class TestRepositoryCreateSession:
    """AC 1 + AC 8: create_session fuegt Row in DB ein."""

    @pytest.mark.asyncio
    async def test_create_session_inserts_row(self, repository, mock_supabase_client):
        """AC 1: create_session erstellt eine Row mit korrekten Daten."""
        result = await repository.create_session("sess-123", "user-abc")

        mock_supabase_client.table.assert_called_with("interviews")
        assert result is not None

    @pytest.mark.asyncio
    async def test_create_session_sets_status_active(self, repository, mock_supabase_client):
        """AC 1: Neue Session hat status='active'."""
        await repository.create_session("sess-123", "user-abc")

        # Pruefen dass insert mit status="active" aufgerufen wurde
        chain = mock_supabase_client.table.return_value
        insert_call = chain.insert.call_args
        assert insert_call is not None
        insert_data = insert_call[0][0]
        assert insert_data["status"] == "active"
        assert insert_data["session_id"] == "sess-123"
        assert insert_data["anonymous_id"] == "user-abc"
        assert insert_data["message_count"] == 0


class TestRepositoryGetSession:
    """AC 9: get_session liest Session aus DB."""

    @pytest.mark.asyncio
    async def test_get_session_returns_row(self, repository):
        """AC 9: Existierende Session wird als Dict zurueckgegeben."""
        result = await repository.get_session("test-session")
        assert result is not None
        assert result["session_id"] == "test-session"

    @pytest.mark.asyncio
    async def test_get_session_returns_none_for_unknown(self, repository, mock_supabase_client):
        """get_session gibt None fuer unbekannte session_id zurueck."""
        # Leere Antwort simulieren
        chain = mock_supabase_client._chain_mock(return_data=[])
        mock_supabase_client.table.return_value = chain

        result = await repository.get_session("unknown-session")
        assert result is None


class TestRepositoryCompleteSession:
    """AC 3 + AC 4: complete_session speichert Transkript und Summary."""

    @pytest.mark.asyncio
    async def test_complete_session_updates_row(self, repository, mock_supabase_client):
        """AC 3: complete_session aktualisiert status, transcript, summary."""
        transcript = [
            {"role": "user", "content": "Das Bidding nervt"},
            {"role": "assistant", "content": "Was genau?"},
        ]
        await repository.complete_session(
            session_id="sess-123",
            transcript=transcript,
            summary="Test Summary",
            message_count=1,
        )

        chain = mock_supabase_client.table.return_value
        update_call = chain.update.call_args
        assert update_call is not None
        update_data = update_call[0][0]
        assert update_data["status"] == "completed"
        assert update_data["transcript"] == transcript
        assert update_data["summary"] == "Test Summary"
        assert update_data["message_count"] == 1
        assert "completed_at" in update_data
        assert "updated_at" in update_data

    @pytest.mark.asyncio
    async def test_complete_session_with_timeout_status(self, repository, mock_supabase_client):
        """complete_session akzeptiert status='completed_timeout'."""
        await repository.complete_session(
            session_id="sess-123",
            transcript=[],
            summary="Timeout Summary",
            message_count=0,
            status="completed_timeout",
        )

        chain = mock_supabase_client.table.return_value
        update_data = chain.update.call_args[0][0]
        assert update_data["status"] == "completed_timeout"


class TestRepositoryGetRecentSummaries:
    """AC 5 + AC 6: get_recent_summaries laedt Summaries."""

    @pytest.mark.asyncio
    async def test_get_recent_summaries_returns_strings(self, repository, mock_supabase_client):
        """AC 5: Summaries werden als Liste von Strings zurueckgegeben."""
        chain = mock_supabase_client._chain_mock(return_data=[
            {"summary": "Summary 1"},
            {"summary": "Summary 2"},
            {"summary": "Summary 3"},
        ])
        mock_supabase_client.table.return_value = chain

        result = await repository.get_recent_summaries("user-abc", limit=3)
        assert result == ["Summary 1", "Summary 2", "Summary 3"]

    @pytest.mark.asyncio
    async def test_get_recent_summaries_empty(self, repository, mock_supabase_client):
        """AC 6: Leere Liste wenn keine Summaries existieren."""
        chain = mock_supabase_client._chain_mock(return_data=[])
        mock_supabase_client.table.return_value = chain

        result = await repository.get_recent_summaries("new-user")
        assert result == []

    @pytest.mark.asyncio
    async def test_get_recent_summaries_respects_limit(self, repository, mock_supabase_client):
        """AC 5: limit Parameter wird beachtet."""
        await repository.get_recent_summaries("user-abc", limit=5)

        chain = mock_supabase_client.table.return_value
        chain.limit.assert_called_with(5)


class TestRepositoryIncrementMessageCount:
    """AC 2: message_count wird inkrementiert."""

    @pytest.mark.asyncio
    async def test_increment_message_count(self, repository, mock_supabase_client):
        """AC 2: message_count wird um 1 erhoeht."""
        await repository.increment_message_count("test-session")

        chain = mock_supabase_client.table.return_value
        # get_session + update werden aufgerufen
        assert chain.execute.call_count >= 1


# -- InterviewService mit Repository --

class TestInterviewServiceWithRepository:
    """AC 1, 2, 3, 10: InterviewService nutzt Repository."""

    @pytest.mark.asyncio
    async def test_start_calls_repository_create(self, mock_graph, mock_repository):
        """AC 1: start() ruft repository.create_session() auf."""
        from app.interview.service import InterviewService
        service = InterviewService(graph=mock_graph, repository=mock_repository)

        events = []
        async for event_data in service.start("test-user"):
            events.append(json.loads(event_data))

        mock_repository.create_session.assert_called_once()
        call_args = mock_repository.create_session.call_args
        assert call_args[1].get("anonymous_id", call_args[0][1] if len(call_args[0]) > 1 else None) == "test-user" or "test-user" in str(call_args)

    @pytest.mark.asyncio
    async def test_message_calls_repository_increment(self, mock_graph, mock_repository):
        """AC 2: message() ruft repository.increment_message_count() auf."""
        from app.interview.service import InterviewService
        service = InterviewService(graph=mock_graph, repository=mock_repository)

        # Session starten
        async for _ in service.start("test-user"):
            pass
        session_id = list(service._sessions.keys())[0]

        # Nachricht senden
        async for _ in service.message(session_id, "Test"):
            pass

        mock_repository.increment_message_count.assert_called_once_with(session_id)

    @pytest.mark.asyncio
    async def test_end_calls_repository_complete(self, mock_graph, mock_repository):
        """AC 3: end() ruft repository.complete_session() auf."""
        from app.interview.service import InterviewService
        service = InterviewService(graph=mock_graph, repository=mock_repository)

        # Session starten
        async for _ in service.start("test-user"):
            pass
        session_id = list(service._sessions.keys())[0]

        # Session beenden
        result = await service.end(session_id)

        mock_repository.complete_session.assert_called_once()
        call_kwargs = mock_repository.complete_session.call_args[1]
        assert call_kwargs["session_id"] == session_id
        assert isinstance(call_kwargs["transcript"], list)
        assert isinstance(call_kwargs["summary"], str)
        assert isinstance(call_kwargs["message_count"], int)

    @pytest.mark.asyncio
    async def test_service_works_without_repository(self, mock_graph):
        """AC 10: Service funktioniert auch ohne Repository (repository=None)."""
        from app.interview.service import InterviewService
        service = InterviewService(graph=mock_graph, repository=None)

        # Session starten
        events = []
        async for event_data in service.start("test-user"):
            events.append(json.loads(event_data))

        session_id = list(service._sessions.keys())[0]

        # Nachricht senden
        async for _ in service.message(session_id, "Test"):
            pass

        # Session beenden
        result = await service.end(session_id)
        assert "summary" in result
        assert "message_count" in result

    @pytest.mark.asyncio
    async def test_service_handles_db_error_gracefully(self, mock_graph):
        """AC 10: DB-Fehler werden geloggt aber nicht propagiert."""
        from app.interview.service import InterviewService

        failing_repo = AsyncMock()
        failing_repo.create_session.side_effect = Exception("DB connection refused")
        failing_repo.complete_session.side_effect = Exception("DB connection refused")
        failing_repo.increment_message_count.side_effect = Exception("DB connection refused")

        service = InterviewService(graph=mock_graph, repository=failing_repo)

        # Start soll trotz DB-Fehler funktionieren
        events = []
        async for event_data in service.start("test-user"):
            events.append(json.loads(event_data))

        metadata = [e for e in events if e.get("type") == "metadata"]
        assert len(metadata) == 1  # Session wurde erstellt

        session_id = list(service._sessions.keys())[0]

        # Message soll trotz DB-Fehler funktionieren
        msg_events = []
        async for event_data in service.message(session_id, "Test"):
            msg_events.append(json.loads(event_data))

        text_done = [e for e in msg_events if e.get("type") == "text-done"]
        assert len(text_done) == 1  # Streaming hat funktioniert

        # End soll trotz DB-Fehler funktionieren
        result = await service.end(session_id)
        assert "summary" in result


# -- Transcript Formatting --

class TestTranscriptFormatting:
    """AC 4: Transkript wird im korrekten JSONB-Format formatiert."""

    def test_format_transcript_human_and_ai(self):
        """AC 4: Messages werden zu {role, content} Dicts konvertiert."""
        from app.interview.service import InterviewService
        messages = [
            HumanMessage(content="Das Bidding nervt"),
            AIMessage(content="Was genau findest du frustrierend?"),
            HumanMessage(content="Die Preise sind intransparent"),
            AIMessage(content="Kannst du ein Beispiel nennen?"),
        ]
        result = InterviewService._format_transcript(messages)
        assert len(result) == 4
        assert result[0] == {"role": "user", "content": "Das Bidding nervt"}
        assert result[1] == {"role": "assistant", "content": "Was genau findest du frustrierend?"}
        assert result[2] == {"role": "user", "content": "Die Preise sind intransparent"}
        assert result[3] == {"role": "assistant", "content": "Kannst du ein Beispiel nennen?"}

    def test_format_transcript_empty(self):
        """Leere Message-Liste ergibt leeres Transkript."""
        from app.interview.service import InterviewService
        result = InterviewService._format_transcript([])
        assert result == []

    def test_format_transcript_is_json_serializable(self):
        """Transkript ist JSON-serialisierbar (JSONB-kompatibel)."""
        from app.interview.service import InterviewService
        messages = [
            HumanMessage(content="Test"),
            AIMessage(content="Antwort"),
        ]
        result = InterviewService._format_transcript(messages)
        serialized = json.dumps(result)
        deserialized = json.loads(serialized)
        assert deserialized == result


# -- SQL Migration --

class TestSQLMigration:
    """AC 11: Migration Script existiert und ist syntaktisch korrekt."""

    MIGRATION_PATH = "backend/migrations/001_create_interviews.sql"

    def test_migration_file_exists(self):
        """AC 11: Migration Script existiert."""
        from pathlib import Path
        migration = Path(__file__).resolve().parents[3] / "migrations" / "001_create_interviews.sql"
        assert migration.exists(), f"Migration file not found: {migration}"

    def test_migration_contains_create_table(self):
        """AC 11: Migration enthaelt CREATE TABLE."""
        from pathlib import Path
        migration = Path(__file__).resolve().parents[3] / "migrations" / "001_create_interviews.sql"
        content = migration.read_text(encoding="utf-8")
        assert "CREATE TABLE" in content
        assert "interviews" in content

    def test_migration_contains_all_columns(self):
        """AC 11: Alle Spalten aus architecture.md sind definiert."""
        from pathlib import Path
        migration = Path(__file__).resolve().parents[3] / "migrations" / "001_create_interviews.sql"
        content = migration.read_text(encoding="utf-8")
        required_columns = [
            "id", "anonymous_id", "session_id", "status",
            "transcript", "summary", "message_count",
            "created_at", "updated_at", "completed_at",
        ]
        for col in required_columns:
            assert col in content, f"Column '{col}' not found in migration"

    def test_migration_contains_indexes(self):
        """AC 11: Indexes auf anonymous_id, session_id und status existieren."""
        from pathlib import Path
        migration = Path(__file__).resolve().parents[3] / "migrations" / "001_create_interviews.sql"
        content = migration.read_text(encoding="utf-8")
        assert "idx_interviews_anonymous_id" in content
        assert "idx_interviews_session_id" in content
        assert "idx_interviews_status" in content

    def test_migration_contains_status_check(self):
        """Status CHECK Constraint ist definiert."""
        from pathlib import Path
        migration = Path(__file__).resolve().parents[3] / "migrations" / "001_create_interviews.sql"
        content = migration.read_text(encoding="utf-8")
        assert "active" in content
        assert "completed" in content
        assert "completed_timeout" in content


# -- Modul-Existenz --

class TestModuleStructure:
    """Alle neuen Dateien existieren und sind importierbar."""

    def test_supabase_module_importable(self):
        """db/supabase.py ist importierbar."""
        from app.db.supabase import get_supabase_client, reset_supabase_client
        assert get_supabase_client is not None
        assert reset_supabase_client is not None

    def test_repository_module_importable(self):
        """interview/repository.py ist importierbar."""
        from app.interview.repository import InterviewRepository
        assert InterviewRepository is not None

    def test_service_accepts_repository(self):
        """InterviewService akzeptiert repository Parameter."""
        import inspect
        from app.interview.service import InterviewService
        sig = inspect.signature(InterviewService.__init__)
        assert "repository" in sig.parameters

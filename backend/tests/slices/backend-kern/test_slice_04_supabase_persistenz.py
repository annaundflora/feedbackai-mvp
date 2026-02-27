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
    settings.database_url = "postgresql+asyncpg://feedbackai:feedbackai_dev@localhost:5432/feedbackai"
    settings.async_database_url = "postgresql+asyncpg://feedbackai:feedbackai_dev@localhost:5432/feedbackai"
    settings.db_echo = False
    settings.db_pool_size = 5
    settings.db_max_overflow = 10
    settings.db_timeout_seconds = 10
    settings.openrouter_api_key = "test-key"
    settings.interviewer_llm = "test-model"
    settings.interviewer_temperature = 1.0
    settings.interviewer_max_tokens = 4000
    settings.llm_timeout_seconds = 30
    return settings


@pytest.fixture
def mock_session_factory():
    """Mock async_sessionmaker that returns a mock AsyncSession."""
    session = AsyncMock()

    # Default: single row result
    default_row = {
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
    }

    # Mock result object
    mock_result = MagicMock()
    mock_mappings = MagicMock()
    mock_mappings.first.return_value = default_row
    mock_mappings.all.return_value = [default_row]
    mock_result.mappings.return_value = mock_mappings

    session.execute = AsyncMock(return_value=mock_result)
    session.commit = AsyncMock()

    # async context manager
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=False)

    factory = MagicMock()
    factory.return_value = session
    factory._mock_session = session
    factory._mock_result = mock_result
    factory._mock_mappings = mock_mappings
    return factory


@pytest.fixture
def repository(mock_session_factory):
    """InterviewRepository mit gemockter SessionFactory."""
    from app.interview.repository import InterviewRepository
    return InterviewRepository(session_factory=mock_session_factory)


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
    # get_history ist synchron in der echten Implementierung
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
    repo.update_timestamp.return_value = None
    repo.get_recent_summaries.return_value = []
    return repo


# -- DB Session Singleton --

class TestDBSessionSingleton:
    """AC 7: DB Session Factory ist ein Singleton."""

    def test_get_session_factory_returns_same_instance(self, mock_settings):
        """AC 7: Mehrfache Aufrufe geben dieselbe Instanz zurueck."""
        from app.db.session import reset_db

        reset_db()
        with patch("app.db.session.create_async_engine") as mock_create:
            mock_engine = MagicMock()
            mock_create.return_value = mock_engine

            from app.db.session import get_session_factory
            factory1 = get_session_factory(mock_settings)
            factory2 = get_session_factory(mock_settings)

            assert factory1 is factory2
            mock_create.assert_called_once()

        reset_db()

    def test_reset_clears_singleton(self, mock_settings):
        """reset_db setzt den Singleton zurueck."""
        from app.db.session import get_session_factory, reset_db

        reset_db()
        with patch("app.db.session.create_async_engine") as mock_create:
            mock_create.side_effect = [MagicMock(), MagicMock()]

            factory1 = get_session_factory(mock_settings)
            reset_db()
            factory2 = get_session_factory(mock_settings)

            assert factory1 is not factory2
            assert mock_create.call_count == 2

        reset_db()


# -- InterviewRepository --

class TestRepositoryCreateSession:
    """AC 1 + AC 8: create_session fuegt Row in DB ein."""

    @pytest.mark.asyncio
    async def test_create_session_inserts_row(self, repository, mock_session_factory):
        """AC 1: create_session erstellt eine Row mit korrekten Daten."""
        result = await repository.create_session("sess-123", "user-abc")

        session = mock_session_factory._mock_session
        session.execute.assert_called_once()
        session.commit.assert_called_once()
        assert result is not None

    @pytest.mark.asyncio
    async def test_create_session_sets_status_active(self, repository, mock_session_factory):
        """AC 1: Neue Session hat status='active'."""
        await repository.create_session("sess-123", "user-abc")

        session = mock_session_factory._mock_session
        call_args = session.execute.call_args
        params = call_args[0][1]  # second positional arg = params dict
        assert params["status"] == "active"
        assert params["session_id"] == "sess-123"
        assert params["anonymous_id"] == "user-abc"
        assert params["message_count"] == 0


class TestRepositoryGetSession:
    """AC 9: get_session liest Session aus DB."""

    @pytest.mark.asyncio
    async def test_get_session_returns_row(self, repository):
        """AC 9: Existierende Session wird als Dict zurueckgegeben."""
        result = await repository.get_session("test-session")
        assert result is not None
        assert result["session_id"] == "test-session"

    @pytest.mark.asyncio
    async def test_get_session_returns_none_for_unknown(self, repository, mock_session_factory):
        """get_session gibt None fuer unbekannte session_id zurueck."""
        mock_session_factory._mock_mappings.first.return_value = None

        result = await repository.get_session("unknown-session")
        assert result is None


class TestRepositoryCompleteSession:
    """AC 3 + AC 4: complete_session speichert Transkript und Summary."""

    @pytest.mark.asyncio
    async def test_complete_session_updates_row(self, repository, mock_session_factory):
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

        session = mock_session_factory._mock_session
        session.execute.assert_called_once()
        session.commit.assert_called_once()
        params = session.execute.call_args[0][1]
        assert params["status"] == "completed"
        assert params["transcript"] == json.dumps(transcript)
        assert params["summary"] == "Test Summary"
        assert params["message_count"] == 1
        assert "completed_at" in params
        assert "updated_at" in params

    @pytest.mark.asyncio
    async def test_complete_session_with_timeout_status(self, repository, mock_session_factory):
        """complete_session akzeptiert status='completed_timeout'."""
        await repository.complete_session(
            session_id="sess-123",
            transcript=[],
            summary="Timeout Summary",
            message_count=0,
            status="completed_timeout",
        )

        session = mock_session_factory._mock_session
        params = session.execute.call_args[0][1]
        assert params["status"] == "completed_timeout"


class TestRepositoryGetRecentSummaries:
    """AC 5 + AC 6: get_recent_summaries laedt Summaries."""

    @pytest.mark.asyncio
    async def test_get_recent_summaries_returns_strings(self, repository, mock_session_factory):
        """AC 5: Summaries werden als Liste von Strings zurueckgegeben."""
        mock_session_factory._mock_mappings.all.return_value = [
            {"summary": "Summary 1"},
            {"summary": "Summary 2"},
            {"summary": "Summary 3"},
        ]

        result = await repository.get_recent_summaries("user-abc", limit=3)
        assert result == ["Summary 1", "Summary 2", "Summary 3"]

    @pytest.mark.asyncio
    async def test_get_recent_summaries_empty(self, repository, mock_session_factory):
        """AC 6: Leere Liste wenn keine Summaries existieren."""
        mock_session_factory._mock_mappings.all.return_value = []

        result = await repository.get_recent_summaries("new-user")
        assert result == []

    @pytest.mark.asyncio
    async def test_get_recent_summaries_respects_limit(self, repository, mock_session_factory):
        """AC 5: limit Parameter wird beachtet."""
        mock_session_factory._mock_mappings.all.return_value = []
        await repository.get_recent_summaries("user-abc", limit=5)

        session = mock_session_factory._mock_session
        params = session.execute.call_args[0][1]
        assert params["limit"] == 5


class TestRepositoryIncrementMessageCount:
    """AC 2: message_count wird inkrementiert."""

    @pytest.mark.asyncio
    async def test_increment_message_count(self, repository, mock_session_factory):
        """AC 2: message_count wird atomar um 1 erhoeht."""
        await repository.increment_message_count("test-session")

        session = mock_session_factory._mock_session
        session.execute.assert_called_once()
        session.commit.assert_called_once()
        # Verify the SQL contains atomic increment
        sql_text = str(session.execute.call_args[0][0].text)
        assert "message_count + 1" in sql_text


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
        await service.end(session_id)

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
        assert "idx_mvp_interviews_anonymous_id" in content
        assert "idx_mvp_interviews_session_id" in content
        assert "idx_mvp_interviews_status" in content

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

    def test_session_module_importable(self):
        """db/session.py ist importierbar."""
        from app.db.session import get_session_factory, reset_db
        assert get_session_factory is not None
        assert reset_db is not None

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

"""Shared fixtures for integration tests."""

import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessageChunk, AIMessage, HumanMessage


@pytest.fixture(autouse=True)
def reset_service_singleton():
    """Resets the InterviewService singleton before each test."""
    from app.api.dependencies import reset_interview_service

    reset_interview_service()
    yield
    reset_interview_service()


@pytest.fixture
def mock_graph():
    """Mock InterviewGraph for testing without actual LLM calls."""
    graph = AsyncMock()

    async def mock_astream(messages, session_id):
        """Mock streaming response."""
        chunks = [
            (AIMessageChunk(content="Hallo"), {"langgraph_node": "interviewer"}),
            (AIMessageChunk(content="! Wie"), {"langgraph_node": "interviewer"}),
            (AIMessageChunk(content=" geht es dir?"), {"langgraph_node": "interviewer"}),
        ]
        for chunk in chunks:
            yield chunk

    graph.astream = mock_astream
    graph.get_history = MagicMock(
        return_value=[
            HumanMessage(content="Test"),
            AIMessage(content="Antwort"),
        ]
    )
    graph.set_summaries = MagicMock(return_value=None)
    return graph


@pytest.fixture
def mock_repository():
    """Mock InterviewRepository for testing without actual DB calls."""
    repo = AsyncMock()
    repo.create_session = AsyncMock(return_value=None)
    repo.increment_message_count = AsyncMock(return_value=None)
    repo.complete_session = AsyncMock(return_value=None)
    repo.get_recent_summaries = AsyncMock(return_value=[])
    return repo


@pytest.fixture
def mock_summary_service():
    """Mock SummaryService for testing without actual LLM calls."""
    service = AsyncMock()
    service.generate = AsyncMock(
        return_value="- User mentioned frustration with bidding\n- Wants simpler process"
    )
    return service


@pytest.fixture
def client(mock_graph, mock_repository, mock_summary_service):
    """TestClient with mocked dependencies."""
    with patch.dict(
        "os.environ",
        {
            "OPENROUTER_API_KEY": "test-key",
            "DATABASE_URL": "postgresql+asyncpg://feedbackai:feedbackai_dev@localhost:5432/feedbackai",
            "SESSION_TIMEOUT_SECONDS": "60",
        },
        clear=False,
    ):
        from app.interview.service import InterviewService
        from app.interview.timeout import TimeoutManager
        from app.api import dependencies

        # Create service with all mocked dependencies
        service = InterviewService(
            graph=mock_graph,
            repository=mock_repository,
            summary_service=mock_summary_service,
        )

        # Create TimeoutManager with the service's timeout handler
        timeout_manager = TimeoutManager(
            timeout_seconds=60,
            on_timeout_callback=service._handle_timeout,
        )
        service._timeout_manager = timeout_manager

        dependencies._interview_service = service

        from app.main import app

        with TestClient(app) as c:
            yield c


@pytest.fixture
def real_client():
    """TestClient with real dependencies (for full integration tests)."""
    with patch.dict(
        "os.environ",
        {
            "OPENROUTER_API_KEY": os.getenv("OPENROUTER_API_KEY", "test-key"),
            "DATABASE_URL": os.getenv("DATABASE_URL", "postgresql+asyncpg://feedbackai:feedbackai_dev@localhost:5432/feedbackai"),
            "SESSION_TIMEOUT_SECONDS": "5",  # Short timeout for tests
        },
        clear=False,
    ):
        from app.main import app

        with TestClient(app) as c:
            yield c


@pytest.fixture
def service(mock_graph, mock_repository, mock_summary_service):
    """Get InterviewService instance for direct testing."""
    from app.interview.service import InterviewService
    from app.interview.timeout import TimeoutManager

    service = InterviewService(
        graph=mock_graph,
        repository=mock_repository,
        summary_service=mock_summary_service,
    )

    timeout_manager = TimeoutManager(
        timeout_seconds=60,
        on_timeout_callback=service._handle_timeout,
    )
    service._timeout_manager = timeout_manager

    return service

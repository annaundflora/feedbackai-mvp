"""Tests for Slice 03: SSE-Streaming Endpoints."""

import pytest
import json
import re
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessageChunk, AIMessage, HumanMessage


# -- Fixtures --


@pytest.fixture(autouse=True)
def reset_service_singleton():
    """Resets the InterviewService singleton before each test."""
    from app.api.dependencies import reset_interview_service

    reset_interview_service()
    yield
    reset_interview_service()


@pytest.fixture
def mock_graph():
    """Mock InterviewGraph that streams predefined chunks."""
    graph = AsyncMock()

    async def mock_astream(messages, session_id):
        chunks = [
            (AIMessageChunk(content="Hallo"), {"langgraph_node": "interviewer"}),
            (AIMessageChunk(content="! Wie"), {"langgraph_node": "interviewer"}),
            (AIMessageChunk(content=" geht es dir?"), {"langgraph_node": "interviewer"}),
        ]
        for chunk in chunks:
            yield chunk

    graph.astream = mock_astream
    graph.get_history.return_value = [
        HumanMessage(content="Test"),
        AIMessage(content="Antwort"),
    ]
    return graph


@pytest.fixture
def client(mock_graph):
    """TestClient with mocked InterviewService."""
    with patch.dict(
        "os.environ",
        {
            "OPENROUTER_API_KEY": "test-key",
            "SUPABASE_URL": "https://test.supabase.co",
            "SUPABASE_KEY": "test-supabase-key",
        },
        clear=False,
    ):
        from app.interview.service import InterviewService
        from app.api import dependencies

        service = InterviewService(graph=mock_graph)
        dependencies._interview_service = service

        from app.main import app

        with TestClient(app) as c:
            yield c


def parse_sse_events(response_text: str) -> list[dict]:
    """Parses SSE response text into a list of events."""
    events = []
    for line in response_text.strip().split("\n"):
        line = line.strip()
        if line.startswith("data: "):
            data_str = line[6:]
            try:
                events.append(json.loads(data_str))
            except json.JSONDecodeError:
                pass
    return events


# -- POST /api/interview/start --


class TestStartInterview:
    """AC 1, 6, 9, 11: POST /api/interview/start."""

    def test_start_returns_sse_stream(self, client):
        """AC 1: Start returns SSE stream."""
        response = client.post(
            "/api/interview/start",
            json={"anonymous_id": "test-user-1"},
        )
        assert response.status_code == 200
        assert "text/event-stream" in response.headers.get("content-type", "")

    def test_start_stream_contains_text_delta(self, client):
        """AC 1: Stream contains text-delta events."""
        response = client.post(
            "/api/interview/start",
            json={"anonymous_id": "test-user-1"},
        )
        events = parse_sse_events(response.text)
        text_deltas = [e for e in events if e.get("type") == "text-delta"]
        assert len(text_deltas) >= 1
        assert "content" in text_deltas[0]

    def test_start_stream_contains_text_done(self, client):
        """AC 1: Stream contains text-done event."""
        response = client.post(
            "/api/interview/start",
            json={"anonymous_id": "test-user-1"},
        )
        events = parse_sse_events(response.text)
        text_done = [e for e in events if e.get("type") == "text-done"]
        assert len(text_done) == 1

    def test_start_stream_contains_metadata_with_session_id(self, client):
        """AC 1: Stream contains metadata event with UUID session_id."""
        response = client.post(
            "/api/interview/start",
            json={"anonymous_id": "test-user-1"},
        )
        events = parse_sse_events(response.text)
        metadata = [e for e in events if e.get("type") == "metadata"]
        assert len(metadata) == 1
        session_id = metadata[0]["session_id"]
        uuid_pattern = re.compile(
            r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
            re.IGNORECASE,
        )
        assert uuid_pattern.match(session_id)

    def test_start_empty_anonymous_id_returns_422(self, client):
        """AC 6: Empty anonymous_id returns 422."""
        response = client.post(
            "/api/interview/start",
            json={"anonymous_id": ""},
        )
        assert response.status_code == 422

    def test_start_missing_anonymous_id_returns_422(self, client):
        """AC 6: Missing anonymous_id returns 422."""
        response = client.post(
            "/api/interview/start",
            json={},
        )
        assert response.status_code == 422

    def test_start_different_users_get_different_sessions(self, client):
        """AC 11: Different users get different session_ids."""
        resp1 = client.post(
            "/api/interview/start",
            json={"anonymous_id": "user-a"},
        )
        resp2 = client.post(
            "/api/interview/start",
            json={"anonymous_id": "user-b"},
        )
        events1 = parse_sse_events(resp1.text)
        events2 = parse_sse_events(resp2.text)
        meta1 = [e for e in events1 if e.get("type") == "metadata"][0]
        meta2 = [e for e in events2 if e.get("type") == "metadata"][0]
        assert meta1["session_id"] != meta2["session_id"]

    def test_start_llm_error_sends_sse_error_event(self, client, mock_graph):
        """AC 9: LLM error is sent as SSE error event."""

        # Configure mock_graph.astream to raise Exception
        async def failing_astream(messages, session_id):
            raise Exception("LLM unavailable")
            yield  # make it a generator

        mock_graph.astream = failing_astream

        response = client.post(
            "/api/interview/start",
            json={"anonymous_id": "test-user-1"},
        )
        events = parse_sse_events(response.text)
        error_events = [e for e in events if e.get("type") == "error"]
        assert len(error_events) >= 1
        assert "message" in error_events[0]
        assert "LLM unavailable" in error_events[0]["message"]


# -- POST /api/interview/message --


class TestSendMessage:
    """AC 2, 4, 5, 7, 8, 10: POST /api/interview/message."""

    def _start_session(self, client) -> str:
        """Helper function: starts session and returns session_id."""
        response = client.post(
            "/api/interview/start",
            json={"anonymous_id": "test-user"},
        )
        events = parse_sse_events(response.text)
        metadata = [e for e in events if e.get("type") == "metadata"][0]
        return metadata["session_id"]

    def test_message_returns_sse_stream(self, client):
        """AC 2: Message returns SSE stream."""
        session_id = self._start_session(client)
        response = client.post(
            "/api/interview/message",
            json={"session_id": session_id, "message": "Test Nachricht"},
        )
        assert response.status_code == 200
        assert "text/event-stream" in response.headers.get("content-type", "")

    def test_message_stream_contains_text_delta_and_done(self, client):
        """AC 2: Stream contains text-delta and text-done."""
        session_id = self._start_session(client)
        response = client.post(
            "/api/interview/message",
            json={"session_id": session_id, "message": "Das Bidding nervt"},
        )
        events = parse_sse_events(response.text)
        text_deltas = [e for e in events if e.get("type") == "text-delta"]
        text_done = [e for e in events if e.get("type") == "text-done"]
        assert len(text_deltas) >= 1
        assert len(text_done) == 1

    def test_message_unknown_session_returns_404(self, client):
        """AC 4: Unknown session_id returns 404."""
        response = client.post(
            "/api/interview/message",
            json={
                "session_id": "00000000-0000-0000-0000-000000000000",
                "message": "Test",
            },
        )
        assert response.status_code == 404
        body = response.json()
        assert body["error"] == "Session not found"

    def test_message_completed_session_returns_409(self, client):
        """AC 5: Completed session returns 409."""
        session_id = self._start_session(client)
        # End session
        client.post(
            "/api/interview/end",
            json={"session_id": session_id},
        )
        # Send message again
        response = client.post(
            "/api/interview/message",
            json={"session_id": session_id, "message": "Nochmal"},
        )
        assert response.status_code == 409
        body = response.json()
        assert body["error"] == "Session already completed"

    def test_message_invalid_uuid_returns_422(self, client):
        """AC 7: Invalid UUID returns 422."""
        response = client.post(
            "/api/interview/message",
            json={"session_id": "not-a-uuid", "message": "Test"},
        )
        assert response.status_code == 422

    def test_message_empty_message_returns_422(self, client):
        """AC 8: Empty message returns 422."""
        session_id = self._start_session(client)
        response = client.post(
            "/api/interview/message",
            json={"session_id": session_id, "message": ""},
        )
        assert response.status_code == 422

    def test_message_too_long_returns_422(self, client):
        """AC 8: Too long message (>10000 characters) returns 422."""
        session_id = self._start_session(client)
        response = client.post(
            "/api/interview/message",
            json={"session_id": session_id, "message": "x" * 10001},
        )
        assert response.status_code == 422

    def test_message_increments_count(self, client):
        """AC 10: message_count is incremented."""
        session_id = self._start_session(client)
        # Send two messages
        client.post(
            "/api/interview/message",
            json={"session_id": session_id, "message": "Erste"},
        )
        client.post(
            "/api/interview/message",
            json={"session_id": session_id, "message": "Zweite"},
        )
        # End session -> check message_count
        response = client.post(
            "/api/interview/end",
            json={"session_id": session_id},
        )
        body = response.json()
        assert body["message_count"] == 2


# -- POST /api/interview/end --


class TestEndInterview:
    """AC 3, 4, 5: POST /api/interview/end."""

    def _start_session(self, client) -> str:
        """Helper function: starts session and returns session_id."""
        response = client.post(
            "/api/interview/start",
            json={"anonymous_id": "test-user"},
        )
        events = parse_sse_events(response.text)
        metadata = [e for e in events if e.get("type") == "metadata"][0]
        return metadata["session_id"]

    def test_end_returns_json_with_summary(self, client):
        """AC 3: End returns JSON with summary."""
        session_id = self._start_session(client)
        response = client.post(
            "/api/interview/end",
            json={"session_id": session_id},
        )
        assert response.status_code == 200
        body = response.json()
        assert "summary" in body
        assert isinstance(body["summary"], str)
        assert len(body["summary"]) > 0

    def test_end_returns_message_count(self, client):
        """AC 3: End returns message_count."""
        session_id = self._start_session(client)
        response = client.post(
            "/api/interview/end",
            json={"session_id": session_id},
        )
        body = response.json()
        assert "message_count" in body
        assert isinstance(body["message_count"], int)

    def test_end_unknown_session_returns_404(self, client):
        """AC 4: Unknown session_id returns 404."""
        response = client.post(
            "/api/interview/end",
            json={"session_id": "00000000-0000-0000-0000-000000000000"},
        )
        assert response.status_code == 404

    def test_end_already_completed_returns_409(self, client):
        """AC 5: Already completed session returns 409."""
        session_id = self._start_session(client)
        client.post(
            "/api/interview/end",
            json={"session_id": session_id},
        )
        response = client.post(
            "/api/interview/end",
            json={"session_id": session_id},
        )
        assert response.status_code == 409


# -- Pydantic DTOs --


class TestSchemas:
    """DTO validation."""

    def test_start_request_strips_whitespace(self):
        """anonymous_id is trimmed."""
        from app.api.schemas import StartRequest

        req = StartRequest(anonymous_id="  test-user  ")
        assert req.anonymous_id == "test-user"

    def test_message_request_validates_uuid(self):
        """session_id must have UUID format."""
        from app.api.schemas import MessageRequest

        with pytest.raises(Exception):
            MessageRequest(session_id="not-a-uuid", message="Test")

    def test_message_request_accepts_valid_uuid(self):
        """Valid UUID is accepted."""
        from app.api.schemas import MessageRequest

        req = MessageRequest(
            session_id="a1b2c3d4-e5f6-7890-abcd-ef1234567890",
            message="Test",
        )
        assert req.session_id == "a1b2c3d4-e5f6-7890-abcd-ef1234567890"

    def test_message_request_strips_message_whitespace(self):
        """message is trimmed."""
        from app.api.schemas import MessageRequest

        req = MessageRequest(
            session_id="a1b2c3d4-e5f6-7890-abcd-ef1234567890",
            message="  Test Nachricht  ",
        )
        assert req.message == "Test Nachricht"

    def test_end_response_model(self):
        """EndResponse has correct fields."""
        from app.api.schemas import EndResponse

        resp = EndResponse(summary="Test Summary", message_count=5)
        assert resp.summary == "Test Summary"
        assert resp.message_count == 5

    def test_error_response_model(self):
        """ErrorResponse has correct fields."""
        from app.api.schemas import ErrorResponse

        resp = ErrorResponse(error="Test Error", detail="Details")
        assert resp.error == "Test Error"
        assert resp.detail == "Details"

    def test_error_response_optional_detail(self):
        """ErrorResponse detail is optional."""
        from app.api.schemas import ErrorResponse

        resp = ErrorResponse(error="Test Error")
        assert resp.detail is None


# -- InterviewService --


class TestInterviewService:
    """Service logic tests."""

    @pytest.mark.asyncio
    async def test_start_creates_session(self, mock_graph):
        """start() creates a new session."""
        from app.interview.service import InterviewService

        service = InterviewService(graph=mock_graph)
        events = []
        async for event_data in service.start("test-user"):
            events.append(json.loads(event_data))
        metadata = [e for e in events if e.get("type") == "metadata"]
        assert len(metadata) == 1
        session_id = metadata[0]["session_id"]
        assert session_id in service._sessions
        assert service._sessions[session_id]["status"] == "active"

    @pytest.mark.asyncio
    async def test_validate_session_not_found(self, mock_graph):
        """_validate_session raises SessionNotFoundError."""
        from app.interview.service import InterviewService, SessionNotFoundError

        service = InterviewService(graph=mock_graph)
        with pytest.raises(SessionNotFoundError):
            service._validate_session("nonexistent-id")

    @pytest.mark.asyncio
    async def test_validate_session_already_completed(self, mock_graph):
        """_validate_session raises SessionAlreadyCompletedError."""
        from app.interview.service import InterviewService, SessionAlreadyCompletedError

        service = InterviewService(graph=mock_graph)
        # Manually create and end session
        service._sessions["test-id"] = {"status": "completed"}
        with pytest.raises(SessionAlreadyCompletedError):
            service._validate_session("test-id")

    @pytest.mark.asyncio
    async def test_end_returns_placeholder_summary(self, mock_graph):
        """end() returns placeholder summary."""
        from app.interview.service import InterviewService

        service = InterviewService(graph=mock_graph)
        # Start session
        async for _ in service.start("test-user"):
            pass
        session_id = list(service._sessions.keys())[0]
        result = await service.end(session_id)
        assert "summary" in result
        assert "message_count" in result
        assert service._sessions[session_id]["status"] == "completed"


# -- SSE Wire Format --


class TestSSEWireFormat:
    """SSE data format validation."""

    def test_text_delta_format(self):
        """text-delta events have type and content."""
        event = json.loads('{"type": "text-delta", "content": "Hallo"}')
        assert event["type"] == "text-delta"
        assert event["content"] == "Hallo"

    def test_text_done_format(self):
        """text-done events have only type."""
        event = json.loads('{"type": "text-done"}')
        assert event["type"] == "text-done"

    def test_metadata_format(self):
        """metadata events have type and session_id."""
        event = json.loads('{"type": "metadata", "session_id": "test-uuid"}')
        assert event["type"] == "metadata"
        assert event["session_id"] == "test-uuid"

    def test_error_format(self):
        """error events have type and message."""
        event = json.loads('{"type": "error", "message": "LLM unavailable"}')
        assert event["type"] == "error"
        assert event["message"] == "LLM unavailable"


# -- Module Existence --


class TestModuleStructure:
    """All new files exist and are importable."""

    def test_schemas_importable(self):
        """api/schemas.py is importable."""
        from app.api.schemas import (
            StartRequest,
            MessageRequest,
            EndRequest,
            EndResponse,
            ErrorResponse,
        )

        assert StartRequest is not None
        assert MessageRequest is not None
        assert EndRequest is not None
        assert EndResponse is not None
        assert ErrorResponse is not None

    def test_routes_importable(self):
        """api/routes.py is importable."""
        from app.api.routes import router

        assert router is not None

    def test_dependencies_importable(self):
        """api/dependencies.py is importable."""
        from app.api.dependencies import get_interview_service, reset_interview_service

        assert get_interview_service is not None
        assert reset_interview_service is not None

    def test_service_importable(self):
        """interview/service.py is importable."""
        from app.interview.service import (
            InterviewService,
            SessionNotFoundError,
            SessionAlreadyCompletedError,
        )

        assert InterviewService is not None
        assert SessionNotFoundError is not None
        assert SessionAlreadyCompletedError is not None

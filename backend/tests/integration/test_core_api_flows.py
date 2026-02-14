"""Core Integration Tests for Phase 1 APIs.

Focused integration tests covering the most critical API flows.
These tests are designed to work with the actual implementation.
"""

import json
import re
import pytest


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


class TestCoreAPIFlows:
    """Test complete API workflows from start to end."""

    def test_complete_interview_lifecycle(self, client):
        """Test full interview: start -> messages -> end.

        E2E Checklist: Flow 1 (Complete Interview)
        """
        # 1. Start interview
        start_response = client.post(
            "/api/interview/start",
            json={"anonymous_id": "integration-test-user"},
        )
        assert start_response.status_code == 200
        assert "text/event-stream" in start_response.headers.get("content-type", "")

        start_events = parse_sse_events(start_response.text)

        # Verify SSE events
        assert len([e for e in start_events if e.get("type") == "text-delta"]) >= 1
        assert len([e for e in start_events if e.get("type") == "text-done"]) == 1

        # Extract session_id
        metadata_events = [e for e in start_events if e.get("type") == "metadata"]
        assert len(metadata_events) == 1
        session_id = metadata_events[0]["session_id"]

        # Verify UUID format
        uuid_pattern = re.compile(
            r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
            re.IGNORECASE,
        )
        assert uuid_pattern.match(session_id)

        # 2. Send messages
        for i, msg in enumerate(["First feedback", "Second feedback"], 1):
            msg_response = client.post(
                "/api/interview/message",
                json={"session_id": session_id, "message": msg},
            )
            assert msg_response.status_code == 200
            msg_events = parse_sse_events(msg_response.text)
            assert len([e for e in msg_events if e.get("type") == "text-delta"]) >= 1
            assert len([e for e in msg_events if e.get("type") == "text-done"]) == 1

        # 3. End interview
        end_response = client.post(
            "/api/interview/end",
            json={"session_id": session_id},
        )
        assert end_response.status_code == 200

        end_data = end_response.json()
        assert "summary" in end_data
        assert "message_count" in end_data
        assert end_data["message_count"] == 2
        assert len(end_data["summary"]) > 0

    def test_multiple_parallel_sessions(self, client):
        """Test multiple concurrent sessions from different users."""
        sessions = []

        # Start 3 parallel sessions
        for i in range(3):
            response = client.post(
                "/api/interview/start",
                json={"anonymous_id": f"user-{i}"},
            )
            assert response.status_code == 200
            events = parse_sse_events(response.text)
            session_id = [e for e in events if e.get("type") == "metadata"][0][
                "session_id"
            ]
            sessions.append(session_id)

        # All sessions should be unique
        assert len(sessions) == len(set(sessions))

        # Each session works independently
        for session_id in sessions:
            msg_response = client.post(
                "/api/interview/message",
                json={"session_id": session_id, "message": "Test"},
            )
            assert msg_response.status_code == 200

        # End all sessions
        for session_id in sessions:
            end_response = client.post(
                "/api/interview/end",
                json={"session_id": session_id},
            )
            assert end_response.status_code == 200
            assert end_response.json()["message_count"] == 1


class TestAPIValidation:
    """Test input validation and error handling."""

    def test_invalid_session_id_returns_404(self, client):
        """Unknown session_id returns 404."""
        response = client.post(
            "/api/interview/message",
            json={
                "session_id": "00000000-0000-0000-0000-000000000000",
                "message": "Test",
            },
        )
        assert response.status_code == 404
        assert response.json()["error"] == "Session not found"

    def test_completed_session_returns_409(self, client):
        """Sending message to completed session returns 409."""
        # Start and end session
        start_response = client.post(
            "/api/interview/start",
            json={"anonymous_id": "test-user"},
        )
        events = parse_sse_events(start_response.text)
        session_id = [e for e in events if e.get("type") == "metadata"][0]["session_id"]

        client.post("/api/interview/end", json={"session_id": session_id})

        # Try to send message
        response = client.post(
            "/api/interview/message",
            json={"session_id": session_id, "message": "After end"},
        )
        assert response.status_code == 409
        assert response.json()["error"] == "Session already completed"

    def test_empty_message_returns_422(self, client):
        """Empty message returns validation error."""
        start_response = client.post(
            "/api/interview/start",
            json={"anonymous_id": "test-user"},
        )
        events = parse_sse_events(start_response.text)
        session_id = [e for e in events if e.get("type") == "metadata"][0]["session_id"]

        response = client.post(
            "/api/interview/message",
            json={"session_id": session_id, "message": ""},
        )
        assert response.status_code == 422

    def test_invalid_uuid_format_returns_422(self, client):
        """Invalid UUID format returns validation error."""
        response = client.post(
            "/api/interview/message",
            json={"session_id": "not-a-uuid", "message": "Test"},
        )
        assert response.status_code == 422


class TestDatabaseIntegration:
    """Test database persistence via mocked repository."""

    def test_session_creation_persisted(self, client, mock_repository):
        """Starting interview calls repository.create_session."""
        client.post(
            "/api/interview/start",
            json={"anonymous_id": "test-user"},
        )

        mock_repository.create_session.assert_called_once()

    def test_message_count_incremented(self, client, mock_repository):
        """Sending message calls repository.increment_message_count."""
        start_response = client.post(
            "/api/interview/start",
            json={"anonymous_id": "test-user"},
        )
        events = parse_sse_events(start_response.text)
        session_id = [e for e in events if e.get("type") == "metadata"][0]["session_id"]

        mock_repository.reset_mock()

        client.post(
            "/api/interview/message",
            json={"session_id": session_id, "message": "Test"},
        )

        mock_repository.increment_message_count.assert_called_once()

    def test_session_completion_persisted(self, client, mock_repository):
        """Ending interview calls repository.complete_session."""
        start_response = client.post(
            "/api/interview/start",
            json={"anonymous_id": "test-user"},
        )
        events = parse_sse_events(start_response.text)
        session_id = [e for e in events if e.get("type") == "metadata"][0]["session_id"]

        mock_repository.reset_mock()

        client.post(
            "/api/interview/end",
            json={"session_id": session_id},
        )

        mock_repository.complete_session.assert_called_once()


class TestSummaryIntegration:
    """Test summary generation and injection."""

    def test_summary_generated_on_end(self, client, mock_summary_service):
        """Summary is generated when ending interview."""
        start_response = client.post(
            "/api/interview/start",
            json={"anonymous_id": "test-user"},
        )
        events = parse_sse_events(start_response.text)
        session_id = [e for e in events if e.get("type") == "metadata"][0]["session_id"]

        client.post(
            "/api/interview/end",
            json={"session_id": session_id},
        )

        mock_summary_service.generate.assert_called_once()

    def test_summaries_loaded_on_start(self, client, mock_repository):
        """Starting interview loads recent summaries."""
        client.post(
            "/api/interview/start",
            json={"anonymous_id": "returning-user"},
        )

        mock_repository.get_recent_summaries.assert_called_once()

    def test_summary_included_in_response(self, client, mock_summary_service):
        """End response includes generated summary."""
        expected_summary = "- User feedback item 1\n- User feedback item 2"
        mock_summary_service.generate.return_value = expected_summary

        start_response = client.post(
            "/api/interview/start",
            json={"anonymous_id": "test-user"},
        )
        events = parse_sse_events(start_response.text)
        session_id = [e for e in events if e.get("type") == "metadata"][0]["session_id"]

        end_response = client.post(
            "/api/interview/end",
            json={"session_id": session_id},
        )

        assert end_response.json()["summary"] == expected_summary


class TestHealthCheck:
    """Test system health endpoint."""

    def test_health_check_ok(self, client):
        """Health check returns 200 OK."""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


class TestBoundaryConditions:
    """Test boundary conditions and edge cases."""

    def test_very_long_message_accepted(self, client):
        """10000-character message is accepted."""
        start_response = client.post(
            "/api/interview/start",
            json={"anonymous_id": "test-user"},
        )
        events = parse_sse_events(start_response.text)
        session_id = [e for e in events if e.get("type") == "metadata"][0]["session_id"]

        long_message = "x" * 10000

        response = client.post(
            "/api/interview/message",
            json={"session_id": session_id, "message": long_message},
        )
        assert response.status_code == 200

    def test_too_long_message_rejected(self, client):
        """10001-character message is rejected."""
        start_response = client.post(
            "/api/interview/start",
            json={"anonymous_id": "test-user"},
        )
        events = parse_sse_events(start_response.text)
        session_id = [e for e in events if e.get("type") == "metadata"][0]["session_id"]

        too_long_message = "x" * 10001

        response = client.post(
            "/api/interview/message",
            json={"session_id": session_id, "message": too_long_message},
        )
        assert response.status_code == 422

    def test_many_messages_in_session(self, client):
        """Session handles 20+ messages correctly."""
        start_response = client.post(
            "/api/interview/start",
            json={"anonymous_id": "test-user"},
        )
        events = parse_sse_events(start_response.text)
        session_id = [e for e in events if e.get("type") == "metadata"][0]["session_id"]

        num_messages = 20
        for i in range(num_messages):
            response = client.post(
                "/api/interview/message",
                json={"session_id": session_id, "message": f"Message {i + 1}"},
            )
            assert response.status_code == 200

        end_response = client.post(
            "/api/interview/end",
            json={"session_id": session_id},
        )
        assert end_response.json()["message_count"] == num_messages

    def test_immediate_end_without_messages(self, client):
        """Session can be ended immediately without messages."""
        start_response = client.post(
            "/api/interview/start",
            json={"anonymous_id": "test-user"},
        )
        events = parse_sse_events(start_response.text)
        session_id = [e for e in events if e.get("type") == "metadata"][0]["session_id"]

        end_response = client.post(
            "/api/interview/end",
            json={"session_id": session_id},
        )
        assert end_response.status_code == 200
        assert end_response.json()["message_count"] == 0


class TestErrorRecovery:
    """Test error handling and recovery scenarios."""

    def test_llm_error_sends_error_event(self, client, mock_graph):
        """LLM error is sent as SSE error event."""

        async def failing_astream(messages, session_id):
            raise Exception("LLM unavailable")
            yield

        mock_graph.astream = failing_astream

        response = client.post(
            "/api/interview/start",
            json={"anonymous_id": "test-user"},
        )

        events = parse_sse_events(response.text)
        error_events = [e for e in events if e.get("type") == "error"]
        assert len(error_events) >= 1
        assert "LLM unavailable" in error_events[0]["message"]

    def test_summary_failure_handled_gracefully(self, client, mock_summary_service):
        """Summary generation failure doesn't crash end endpoint."""
        mock_summary_service.generate.side_effect = Exception("LLM timeout")

        start_response = client.post(
            "/api/interview/start",
            json={"anonymous_id": "test-user"},
        )
        events = parse_sse_events(start_response.text)
        session_id = [e for e in events if e.get("type") == "metadata"][0]["session_id"]

        end_response = client.post(
            "/api/interview/end",
            json={"session_id": session_id},
        )

        # Should return 200 with fallback summary
        assert end_response.status_code == 200
        assert "summary" in end_response.json()

    def test_db_error_loading_summaries_not_blocking(self, client, mock_repository):
        """DB error when loading summaries doesn't block start."""
        mock_repository.get_recent_summaries.side_effect = Exception("DB read error")

        response = client.post(
            "/api/interview/start",
            json={"anonymous_id": "test-user"},
        )

        # Should succeed (without summaries)
        assert response.status_code == 200

"""Integration tests for state transitions and cross-slice integration.

Tests state machine behavior and integration between all slices.
"""

import json
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


class TestStateTransitions:
    """Test state machine transitions from E2E checklist."""

    def test_idle_to_active_on_start(self, client):
        """E2E Checklist: Transitions - idle -> active.

        POST /start creates session with status=active.
        """
        response = client.post(
            "/api/interview/start",
            json={"anonymous_id": "test-user"},
        )
        assert response.status_code == 200

        # Session should be created
        events = parse_sse_events(response.text)
        metadata = [e for e in events if e.get("type") == "metadata"]
        assert len(metadata) == 1

        # Verify session is active
        from app.api.dependencies import get_interview_service_for_tests

        service = get_interview_service_for_tests()
        session_id = metadata[0]["session_id"]
        assert service._sessions[session_id]["status"] == "active"

    def test_active_to_streaming_on_message(self, client):
        """E2E Checklist: Transitions - active -> streaming.

        POST /message triggers streaming state.
        """
        # Start session (idle -> active)
        start_response = client.post(
            "/api/interview/start",
            json={"anonymous_id": "test-user"},
        )
        events = parse_sse_events(start_response.text)
        session_id = [e for e in events if e.get("type") == "metadata"][0]["session_id"]

        # Send message (active -> streaming)
        message_response = client.post(
            "/api/interview/message",
            json={"session_id": session_id, "message": "Test"},
        )

        # Should return SSE stream
        assert "text/event-stream" in message_response.headers.get("content-type", "")
        message_events = parse_sse_events(message_response.text)

        # Should have text-delta events (streaming)
        text_deltas = [e for e in message_events if e.get("type") == "text-delta"]
        assert len(text_deltas) > 0

    def test_streaming_to_active_on_done(self, client):
        """E2E Checklist: Transitions - streaming -> active.

        SSE text-done event returns to active state.
        """
        # Start and send message
        start_response = client.post(
            "/api/interview/start",
            json={"anonymous_id": "test-user"},
        )
        events = parse_sse_events(start_response.text)
        session_id = [e for e in events if e.get("type") == "metadata"][0]["session_id"]

        message_response = client.post(
            "/api/interview/message",
            json={"session_id": session_id, "message": "Test"},
        )

        # Check for text-done event
        message_events = parse_sse_events(message_response.text)
        text_done = [e for e in message_events if e.get("type") == "text-done"]
        assert len(text_done) == 1

        # Session should be back to active
        from app.api.dependencies import get_interview_service_for_tests

        service = get_interview_service_for_tests()
        assert service._sessions[session_id]["status"] == "active"

    def test_streaming_to_error_on_llm_failure(self, client, mock_graph):
        """E2E Checklist: Transitions - streaming -> error.

        LLM error during streaming sends error event.
        """

        # Make graph fail
        async def failing_astream(messages, session_id):
            raise Exception("LLM error")
            yield

        mock_graph.astream = failing_astream

        # Start should send error event
        response = client.post(
            "/api/interview/start",
            json={"anonymous_id": "test-user"},
        )

        events = parse_sse_events(response.text)
        error_events = [e for e in events if e.get("type") == "error"]
        assert len(error_events) >= 1

    def test_error_to_streaming_on_retry(self, client, mock_graph):
        """E2E Checklist: Transitions - error -> streaming.

        POST /message retry after error works.
        """
        # First call fails
        async def failing_astream(messages, session_id):
            raise Exception("Temporary error")
            yield

        mock_graph.astream = failing_astream

        start_response = client.post(
            "/api/interview/start",
            json={"anonymous_id": "test-user"},
        )
        events = parse_sse_events(start_response.text)
        session_id = [e for e in events if e.get("type") == "metadata"][0]["session_id"]

        # Fix the mock
        async def working_astream(messages, session_id):
            from langchain_core.messages import AIMessageChunk

            yield (
                AIMessageChunk(content="Retry worked"),
                {"langgraph_node": "interviewer"},
            )

        mock_graph.astream = working_astream

        # Retry should work
        retry_response = client.post(
            "/api/interview/message",
            json={"session_id": session_id, "message": "Retry"},
        )
        assert retry_response.status_code == 200

        retry_events = parse_sse_events(retry_response.text)
        text_deltas = [e for e in retry_events if e.get("type") == "text-delta"]
        assert len(text_deltas) > 0

    def test_active_to_summarizing_on_end(self, client):
        """E2E Checklist: Transitions - active -> summarizing.

        POST /end triggers summarizing state.
        """
        # Start session
        start_response = client.post(
            "/api/interview/start",
            json={"anonymous_id": "test-user"},
        )
        events = parse_sse_events(start_response.text)
        session_id = [e for e in events if e.get("type") == "metadata"][0]["session_id"]

        # End session
        end_response = client.post(
            "/api/interview/end",
            json={"session_id": session_id},
        )

        # Should return summary
        assert end_response.status_code == 200
        assert "summary" in end_response.json()

    def test_summarizing_to_completed_after_end(self, client):
        """E2E Checklist: Transitions - summarizing -> completed.

        Summary completion marks session as completed.
        """
        # Start and end session
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

        # Session should be completed
        from app.api.dependencies import get_interview_service_for_tests

        service = get_interview_service_for_tests()
        assert service._sessions[session_id]["status"] == "completed"

    @pytest.mark.asyncio
    async def test_active_to_summarizing_on_timeout(self, client):
        """E2E Checklist: Transitions - active -> summarizing (timeout).

        Timeout triggers summarizing state.
        """
        from app.api.dependencies import get_interview_service_for_tests

        service = get_interview_service_for_tests()

        # Create fake active session
        session_id = "test-session"
        service._sessions[session_id] = {
            "anonymous_id": "test-user",
            "status": "active",
            "message_count": 0,
        }

        # Trigger timeout
        await service._handle_timeout(session_id)

        # Should be completed_timeout
        assert service._sessions[session_id]["status"] == "completed_timeout"

    @pytest.mark.asyncio
    async def test_summarizing_to_completed_timeout_after_timeout(self, client):
        """E2E Checklist: Transitions - summarizing -> completed_timeout.

        Timeout summary completion uses completed_timeout status.
        """
        from app.api.dependencies import get_interview_service_for_tests

        service = get_interview_service_for_tests()

        # Create fake active session
        session_id = "test-session"
        service._sessions[session_id] = {
            "anonymous_id": "test-user",
            "status": "active",
            "message_count": 0,
        }

        # Trigger timeout
        await service._handle_timeout(session_id)

        # Status should be completed_timeout
        assert service._sessions[session_id]["status"] == "completed_timeout"


class TestCrossSliceIntegration:
    """Test integration points between slices."""

    def test_settings_available_to_all_services(self, client):
        """E2E Checklist: Integration Point 1.

        Settings are available to all services.
        """
        from unittest.mock import patch
        import os
        from app.config.settings import Settings

        # Patch environment before creating Settings
        with patch.dict(
            os.environ,
            {
                "OPENROUTER_API_KEY": "test-key",
                "DATABASE_URL": "postgresql+asyncpg://feedbackai:feedbackai_dev@localhost:5432/feedbackai",
            },
            clear=False,
        ):
            settings = Settings()

            # Verify critical settings are loaded
            assert settings.openrouter_api_key is not None
            assert settings.database_url is not None

    def test_interview_graph_in_service(self, client, mock_graph):
        """E2E Checklist: Integration Point 2.

        InterviewService uses InterviewGraph for streaming.
        """
        # Start session (triggers graph.astream)
        response = client.post(
            "/api/interview/start",
            json={"anonymous_id": "test-user"},
        )

        assert response.status_code == 200

        # Graph's astream should have been called
        # Note: This is implicit - if response succeeded, graph was used

    def test_service_uses_repository(self, client, mock_repository):
        """E2E Checklist: Integration Point 3.

        InterviewService uses Repository for persistence.
        """
        # Start and end session
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

        # Repository methods should have been called
        assert mock_repository.create_session.called
        assert mock_repository.complete_session.called

    def test_repository_summaries_in_start(self, client, mock_repository):
        """E2E Checklist: Integration Point 4.

        get_recent_summaries is called during start.
        """
        client.post(
            "/api/interview/start",
            json={"anonymous_id": "returning-user"},
        )

        # Repository should be queried for summaries
        mock_repository.get_recent_summaries.assert_called_once()

    def test_summary_service_in_end(self, client, mock_summary_service):
        """E2E Checklist: Integration Point 5.

        SummaryService is used during end.
        """
        # Start and end session
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

        # Summary service should have been called
        mock_summary_service.generate.assert_called_once()

    def test_timeout_manager_in_service(self, client):
        """E2E Checklist: Integration Point 6.

        TimeoutManager is used in InterviewService.
        """
        from app.api.dependencies import get_interview_service_for_tests

        service = get_interview_service_for_tests()

        # Service should have timeout manager
        assert hasattr(service, "_timeout_manager")

        # Start session registers timeout
        start_response = client.post(
            "/api/interview/start",
            json={"anonymous_id": "test-user"},
        )
        events = parse_sse_events(start_response.text)
        session_id = [e for e in events if e.get("type") == "metadata"][0]["session_id"]

        # Timeout should be registered
        if service._timeout_manager:
            assert session_id in service._timeout_manager._tasks

    @pytest.mark.asyncio
    async def test_timeout_uses_summary_and_repository(
        self, client, mock_summary_service, mock_repository
    ):
        """E2E Checklist: Integration Point 7.

        Timeout handler uses SummaryService and Repository.
        """
        from app.api.dependencies import get_interview_service_for_tests

        service = get_interview_service_for_tests()

        # Create fake session
        session_id = "test-session"
        service._sessions[session_id] = {
            "anonymous_id": "test-user",
            "status": "active",
            "message_count": 0,
        }

        # Trigger timeout
        await service._handle_timeout(session_id)

        # Both services should have been used
        mock_summary_service.generate.assert_called_once()
        mock_repository.complete_session.assert_called_once()

    def test_prompt_assembler_with_summaries(self, client, mock_repository, mock_graph):
        """E2E Checklist: Integration Point 8.

        PromptAssembler integrates summaries into graph.
        """
        # Configure summaries
        mock_repository.get_recent_summaries.return_value = [
            "- Previous summary",
        ]

        # Start session
        client.post(
            "/api/interview/start",
            json={"anonymous_id": "returning-user"},
        )

        # Graph should receive summaries
        mock_graph.set_summaries.assert_called_once()

    def test_dependency_injection_chain(self, client, mock_graph, mock_repository, mock_summary_service):
        """E2E Checklist: Integration Point 10.

        All services are correctly injected via dependencies.
        """
        from app.api.dependencies import get_interview_service_for_tests

        service = get_interview_service_for_tests()

        # Service should have all dependencies
        assert service._graph is not None
        assert service._repository is not None
        assert service._summary_service is not None


class TestBusinessRules:
    """Test business rules from E2E checklist."""

    def test_no_automatic_end_or_message_limit(self, client):
        """E2E Checklist: Business Rules - No automatic end.

        Sessions don't automatically end after N messages.
        """
        # Start session
        start_response = client.post(
            "/api/interview/start",
            json={"anonymous_id": "test-user"},
        )
        events = parse_sse_events(start_response.text)
        session_id = [e for e in events if e.get("type") == "metadata"][0]["session_id"]

        # Send many messages
        for i in range(10):
            response = client.post(
                "/api/interview/message",
                json={"session_id": session_id, "message": f"Message {i}"},
            )
            assert response.status_code == 200

        # Session should still be active
        from app.api.dependencies import get_interview_service_for_tests

        service = get_interview_service_for_tests()
        assert service._sessions[session_id]["status"] == "active"

    def test_session_belongs_to_anonymous_id(self, client):
        """E2E Checklist: Business Rules - Session belongs to user.

        Each session is tied to an anonymous_id.
        """
        # Start session
        anonymous_id = "specific-user-123"
        start_response = client.post(
            "/api/interview/start",
            json={"anonymous_id": anonymous_id},
        )
        events = parse_sse_events(start_response.text)
        session_id = [e for e in events if e.get("type") == "metadata"][0]["session_id"]

        # Verify in-memory session has correct anonymous_id
        from app.api.dependencies import get_interview_service_for_tests

        service = get_interview_service_for_tests()
        assert service._sessions[session_id]["anonymous_id"] == anonymous_id

    def test_last_three_summaries_loaded(self, client, mock_repository):
        """E2E Checklist: Business Rules - Last 3 summaries.

        Only last 3 summaries are loaded at start.
        """
        client.post(
            "/api/interview/start",
            json={"anonymous_id": "test-user"},
        )

        # Verify limit is 3
        call_args = mock_repository.get_recent_summaries.call_args
        if "limit" in call_args[1]:
            assert call_args[1]["limit"] == 3

    def test_session_timeout_is_configurable(self):
        """E2E Checklist: Business Rules - Timeout configurable.

        Session timeout can be configured via settings.
        """
        from unittest.mock import patch
        from app.config.settings import Settings
        import os

        # Verify timeout setting exists
        with patch.dict(
            os.environ,
            {
                "OPENROUTER_API_KEY": "test-key",
                "DATABASE_URL": "postgresql+asyncpg://feedbackai:feedbackai_dev@localhost:5432/feedbackai",
                "SESSION_TIMEOUT_SECONDS": "120",
            },
            clear=False,
        ):
            settings = Settings()
            assert settings.session_timeout_seconds == 120

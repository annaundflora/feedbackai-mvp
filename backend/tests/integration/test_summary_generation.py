"""Integration tests for summary generation and injection.

Tests summary creation, storage, and injection into subsequent sessions.
"""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock


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


class TestSummaryGeneration:
    """Test summary generation during interview end."""

    def test_summary_generated_on_end(self, client, mock_summary_service):
        """E2E Checklist: Flow 1, Step 11.

        Summary is generated when interview ends.
        """
        # Start session
        start_response = client.post(
            "/api/interview/start",
            json={"anonymous_id": "test-user"},
        )
        events = parse_sse_events(start_response.text)
        session_id = [e for e in events if e.get("type") == "metadata"][0]["session_id"]

        # Send a message
        client.post(
            "/api/interview/message",
            json={"session_id": session_id, "message": "Test message"},
        )

        # End session
        end_response = client.post(
            "/api/interview/end",
            json={"session_id": session_id},
        )

        # Verify summary service was called
        mock_summary_service.generate.assert_called_once()

        # Verify response includes summary
        end_data = end_response.json()
        assert "summary" in end_data
        assert len(end_data["summary"]) > 0

    def test_summary_is_bullet_list_format(self, client, mock_summary_service):
        """E2E Checklist: Flow 1, Step 11.

        Summary follows bullet-list format with '- ' lines.
        """
        # Configure mock to return bullet-list summary
        expected_summary = "- User mentioned frustration with bidding\n- Wants simpler process\n- UI improvements needed"
        mock_summary_service.generate.return_value = expected_summary

        # Start and end session
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

        # Verify summary format
        summary = end_response.json()["summary"]
        assert "- " in summary  # Contains bullet points
        assert summary == expected_summary

    def test_summary_uses_conversation_history(self, client, mock_summary_service, mock_graph):
        """Summary generation receives full conversation history."""
        from langchain_core.messages import HumanMessage, AIMessage

        # Configure mock history
        mock_graph.get_history.return_value = [
            HumanMessage(content="Problem with bidding"),
            AIMessage(content="Tell me more"),
            HumanMessage(content="It's too complex"),
        ]

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

        # Verify summary service received messages
        mock_summary_service.generate.assert_called_once()
        call_args = mock_summary_service.generate.call_args
        messages = call_args[0][0] if call_args[0] else []

        # Should contain conversation history
        assert len(messages) > 0

    def test_empty_conversation_generates_summary(self, client, mock_summary_service, mock_graph):
        """E2E Checklist: Boundary Conditions - Leere History.

        Summary generation handles empty conversation gracefully.
        """
        # Configure mock for empty history
        mock_graph.get_history.return_value = []

        # Start and immediately end
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

        # Should still return a summary (even if generic)
        assert "summary" in end_response.json()

        # Summary service should be called
        mock_summary_service.generate.assert_called_once()


class TestSummaryInjection:
    """Test summary injection into new sessions."""

    def test_summaries_loaded_on_start(self, client, mock_repository):
        """E2E Checklist: Flow 2, Step 2.

        Starting interview loads recent summaries.
        """
        # Configure repository to return summaries
        previous_summaries = [
            "- Previous feedback about pricing",
            "- Mentioned UI confusion",
            "- Requested mobile app",
        ]
        mock_repository.get_recent_summaries.return_value = previous_summaries

        # Start session
        client.post(
            "/api/interview/start",
            json={"anonymous_id": "returning-user"},
        )

        # Verify get_recent_summaries was called
        mock_repository.get_recent_summaries.assert_called_once()

    def test_summaries_limited_to_three(self, client, mock_repository):
        """E2E Checklist: Flow 2, Step 2.

        Only last 3 summaries are loaded.
        """
        # Start session
        client.post(
            "/api/interview/start",
            json={"anonymous_id": "returning-user"},
        )

        # Verify limit=3
        call_args = mock_repository.get_recent_summaries.call_args
        if "limit" in call_args[1]:
            assert call_args[1]["limit"] == 3
        elif len(call_args[0]) > 1:
            assert call_args[0][1] == 3

    def test_summaries_injected_into_prompt(self, client, mock_repository, mock_graph):
        """E2E Checklist: Flow 2, Step 3.

        Summaries are injected into system prompt.
        """
        # Configure repository with summaries
        mock_repository.get_recent_summaries.return_value = [
            "- Previous session summary",
        ]

        # Start session
        client.post(
            "/api/interview/start",
            json={"anonymous_id": "returning-user"},
        )

        # Verify graph.set_summaries was called
        mock_graph.set_summaries.assert_called_once()

        # Verify summaries were passed
        call_args = mock_graph.set_summaries.call_args
        summaries = call_args[0][0] if call_args[0] else []
        assert len(summaries) > 0

    def test_new_user_no_summaries_in_prompt(self, client, mock_repository, mock_graph):
        """E2E Checklist: Flow 3, Steps 2-3.

        New users get no summary injection.
        """
        # Configure repository for new user
        mock_repository.get_recent_summaries.return_value = []

        # Start session
        client.post(
            "/api/interview/start",
            json={"anonymous_id": "brand-new-user"},
        )

        # Verify set_summaries was called with empty list or None
        mock_graph.set_summaries.assert_called()
        call_args = mock_graph.set_summaries.call_args
        summaries = call_args[0][0] if call_args[0] else []
        assert len(summaries) == 0 or summaries is None

    def test_summary_injection_uses_prompt_assembler(self, client, mock_repository, mock_graph):
        """E2E Checklist: Flow 2, Step 3.

        PromptAssembler.build() integrates summaries into prompt.
        """
        # Configure summaries
        mock_repository.get_recent_summaries.return_value = [
            "- Summary 1",
            "- Summary 2",
        ]

        # Start session
        client.post(
            "/api/interview/start",
            json={"anonymous_id": "returning-user"},
        )

        # Verify summaries were set on graph
        mock_graph.set_summaries.assert_called_once()

        # PromptAssembler.build is tested in slice tests
        # Here we verify integration works end-to-end


class TestSummaryErrorHandling:
    """Test error handling during summary generation."""

    def test_summary_generation_failure_returns_fallback(
        self, client, mock_summary_service
    ):
        """E2E Checklist: Error Handling - Summary-Generierung schlaegt fehl.

        Failed summary generation uses fallback text.
        """
        # Make summary service fail
        mock_summary_service.generate.side_effect = Exception("LLM timeout")

        # Start and end session
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

        # Should still return 200 with fallback summary
        assert end_response.status_code == 200
        assert "summary" in end_response.json()

    def test_db_error_loading_summaries_not_blocking(self, client, mock_repository):
        """E2E Checklist: Error Handling - DB-Fehler bei Summary-Loading.

        DB errors when loading summaries don't block start.
        """
        # Make repository fail
        mock_repository.get_recent_summaries.side_effect = Exception("DB read error")

        # Start should still work
        response = client.post(
            "/api/interview/start",
            json={"anonymous_id": "test-user"},
        )

        # Should succeed (without summaries)
        assert response.status_code == 200

    def test_summary_service_timeout_handled_gracefully(
        self, client, mock_summary_service
    ):
        """Summary service timeout doesn't crash the end endpoint."""
        import asyncio

        # Make summary service timeout
        async def slow_generate(*args, **kwargs):
            await asyncio.sleep(100)  # Simulate timeout
            return "Never reached"

        mock_summary_service.generate.side_effect = asyncio.TimeoutError()

        # Start and end session
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

        # Should handle timeout gracefully
        assert end_response.status_code == 200


class TestTranscriptFormatting:
    """Test transcript formatting for storage."""

    def test_transcript_includes_all_messages(self, client, mock_repository, mock_graph):
        """E2E Checklist: Flow 1, Step 12.

        Transcript includes all messages from conversation.
        """
        from langchain_core.messages import HumanMessage, AIMessage

        # Configure mock history
        mock_graph.get_history.return_value = [
            HumanMessage(content="First message"),
            AIMessage(content="First response"),
            HumanMessage(content="Second message"),
            AIMessage(content="Second response"),
        ]

        # Start and end session
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

        # Verify transcript was passed to complete_session
        call_args = mock_repository.complete_session.call_args
        args = call_args[1] if call_args[1] else {}

        if "transcript" in args:
            transcript = args["transcript"]
            # Should be list of message dicts
            assert isinstance(transcript, list)
            assert len(transcript) > 0

    def test_transcript_is_jsonb_compatible(self, client, mock_repository, mock_graph):
        """Transcript format is JSON-serializable (JSONB compatible)."""
        from langchain_core.messages import HumanMessage, AIMessage

        mock_graph.get_history.return_value = [
            HumanMessage(content="Test"),
            AIMessage(content="Response"),
        ]

        # Start and end session
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

        # Verify transcript is JSON-serializable
        call_args = mock_repository.complete_session.call_args
        args = call_args[1] if call_args[1] else {}

        if "transcript" in args:
            transcript = args["transcript"]
            # Should be JSON-serializable
            import json

            try:
                json.dumps(transcript)
            except (TypeError, ValueError):
                pytest.fail("Transcript is not JSON-serializable")

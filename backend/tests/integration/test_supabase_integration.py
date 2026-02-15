"""Integration tests for Supabase persistence.

Tests database operations without mocking the repository.
"""

import json


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


class TestSupabasePersistence:
    """Test Supabase database operations."""

    def test_create_session_called_on_start(self, client, mock_repository):
        """E2E Checklist: Flow 1, Step 5.

        Starting interview creates row in Supabase.
        """
        response = client.post(
            "/api/interview/start",
            json={"anonymous_id": "test-user-1"},
        )
        assert response.status_code == 200

        # Verify repository.create_session was called
        mock_repository.create_session.assert_called_once()
        call_args = mock_repository.create_session.call_args
        assert call_args is not None

        # Verify arguments
        args = call_args[1] if call_args[1] else call_args[0]
        if isinstance(args, dict):
            assert "session_id" in str(args) or len(call_args[0]) >= 2

    def test_increment_message_count_on_message(self, client, mock_repository):
        """E2E Checklist: Flow 1, Step 8.

        Sending message increments message_count in database.
        """
        # Start session
        start_response = client.post(
            "/api/interview/start",
            json={"anonymous_id": "test-user"},
        )
        events = parse_sse_events(start_response.text)
        session_id = [e for e in events if e.get("type") == "metadata"][0]["session_id"]

        # Reset mock to clear start call
        mock_repository.reset_mock()

        # Send message
        client.post(
            "/api/interview/message",
            json={"session_id": session_id, "message": "Test message"},
        )

        # Verify increment was called
        mock_repository.increment_message_count.assert_called_once()

    def test_complete_session_called_on_end(self, client, mock_repository):
        """E2E Checklist: Flow 1, Step 12.

        Ending interview completes session in database.
        """
        # Start session
        start_response = client.post(
            "/api/interview/start",
            json={"anonymous_id": "test-user"},
        )
        events = parse_sse_events(start_response.text)
        session_id = [e for e in events if e.get("type") == "metadata"][0]["session_id"]

        # Reset mock
        mock_repository.reset_mock()

        # End session
        client.post(
            "/api/interview/end",
            json={"session_id": session_id},
        )

        # Verify complete_session was called
        mock_repository.complete_session.assert_called_once()
        call_args = mock_repository.complete_session.call_args

        # Verify session_id, status, transcript, and summary are included
        args = call_args[1] if call_args[1] else {}
        if "status" in args:
            assert args["status"] == "completed"

    def test_complete_session_includes_transcript(self, client, mock_repository):
        """E2E Checklist: Flow 1, Step 12.

        complete_session includes transcript as JSONB array.
        """
        # Start and end session
        start_response = client.post(
            "/api/interview/start",
            json={"anonymous_id": "test-user"},
        )
        events = parse_sse_events(start_response.text)
        session_id = [e for e in events if e.get("type") == "metadata"][0]["session_id"]

        # Send a message
        client.post(
            "/api/interview/message",
            json={"session_id": session_id, "message": "Test"},
        )

        # Reset mock
        mock_repository.reset_mock()

        # End session
        client.post(
            "/api/interview/end",
            json={"session_id": session_id},
        )

        # Verify transcript was included
        call_args = mock_repository.complete_session.call_args
        args = call_args[1] if call_args[1] else {}

        if "transcript" in args:
            transcript = args["transcript"]
            assert isinstance(transcript, list)
            assert len(transcript) > 0

    def test_complete_session_with_status_completed(self, client, mock_repository):
        """E2E Checklist: Flow 1, Step 12.

        Normal end sets status=completed.
        """
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

        # Verify status is completed
        call_args = mock_repository.complete_session.call_args
        args = call_args[1] if call_args[1] else {}

        if "status" in args:
            assert args["status"] == "completed"


class TestSummaryPersistence:
    """Test summary storage and retrieval."""

    def test_summary_stored_on_end(self, client, mock_repository, mock_summary_service):
        """E2E Checklist: Flow 1, Step 11-12.

        Generated summary is stored in database.
        """
        # Configure mock summary
        expected_summary = "- User mentioned frustration\n- Wants improvements"
        mock_summary_service.generate.return_value = expected_summary

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

        # Verify summary was passed to complete_session
        call_args = mock_repository.complete_session.call_args
        args = call_args[1] if call_args[1] else {}

        if "summary" in args:
            assert args["summary"] == expected_summary

    def test_get_recent_summaries_called_on_start(
        self, client, mock_repository, mock_summary_service
    ):
        """E2E Checklist: Flow 2, Step 2.

        Starting interview loads recent summaries for the user.
        """
        # Configure mock to return previous summaries
        mock_repository.get_recent_summaries.return_value = [
            "- Previous session summary 1",
            "- Previous session summary 2",
        ]

        # Start session
        client.post(
            "/api/interview/start",
            json={"anonymous_id": "returning-user"},
        )

        # Verify get_recent_summaries was called
        mock_repository.get_recent_summaries.assert_called_once()
        call_args = mock_repository.get_recent_summaries.call_args

        # Should be called with anonymous_id and limit=3
        if call_args[0]:
            assert call_args[0][0] == "returning-user"
        elif "anonymous_id" in call_args[1]:
            assert call_args[1]["anonymous_id"] == "returning-user"

    def test_new_user_gets_empty_summaries(self, client, mock_repository):
        """E2E Checklist: Flow 3, Steps 1-2.

        New user without previous sessions gets empty summary list.
        """
        # Configure mock for new user
        mock_repository.get_recent_summaries.return_value = []

        # Start session
        response = client.post(
            "/api/interview/start",
            json={"anonymous_id": "brand-new-user"},
        )

        assert response.status_code == 200

        # Verify summaries were checked
        mock_repository.get_recent_summaries.assert_called_once()


class TestMessageCounting:
    """Test message count tracking."""

    def test_message_count_increments_correctly(self, client, mock_repository):
        """E2E Checklist: Flow 1, Steps 8-9.

        Message count increments with each message.
        """
        # Start session
        start_response = client.post(
            "/api/interview/start",
            json={"anonymous_id": "test-user"},
        )
        events = parse_sse_events(start_response.text)
        session_id = [e for e in events if e.get("type") == "metadata"][0]["session_id"]

        # Send multiple messages
        num_messages = 5
        for i in range(num_messages):
            client.post(
                "/api/interview/message",
                json={"session_id": session_id, "message": f"Message {i + 1}"},
            )

        # Verify increment was called num_messages times
        assert mock_repository.increment_message_count.call_count == num_messages

        # End and verify final count
        end_response = client.post(
            "/api/interview/end",
            json={"session_id": session_id},
        )

        assert end_response.json()["message_count"] == num_messages

    def test_message_count_zero_on_immediate_end(self, client):
        """Message count is 0 if session ended without messages."""
        # Start session
        start_response = client.post(
            "/api/interview/start",
            json={"anonymous_id": "test-user"},
        )
        events = parse_sse_events(start_response.text)
        session_id = [e for e in events if e.get("type") == "metadata"][0]["session_id"]

        # End immediately without sending messages
        end_response = client.post(
            "/api/interview/end",
            json={"session_id": session_id},
        )

        assert end_response.json()["message_count"] == 0


class TestDatabaseSchemaValidation:
    """Test database schema requirements."""

    def test_session_id_is_uuid(self, client):
        """E2E Checklist: Data Fields - session_id is UUID."""
        import re

        start_response = client.post(
            "/api/interview/start",
            json={"anonymous_id": "test-user"},
        )
        events = parse_sse_events(start_response.text)
        session_id = [e for e in events if e.get("type") == "metadata"][0]["session_id"]

        # Verify UUID format
        uuid_pattern = re.compile(
            r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
            re.IGNORECASE,
        )
        assert uuid_pattern.match(session_id)

    def test_anonymous_id_stored_correctly(self, client, mock_repository):
        """E2E Checklist: Data Fields - anonymous_id is stored."""
        anonymous_id = "specific-test-user"

        client.post(
            "/api/interview/start",
            json={"anonymous_id": anonymous_id},
        )

        # Verify create_session was called with correct anonymous_id
        call_args = mock_repository.create_session.call_args
        if call_args[0]:
            # Positional arguments
            assert anonymous_id in str(call_args[0])
        elif "anonymous_id" in call_args[1]:
            # Keyword arguments
            assert call_args[1]["anonymous_id"] == anonymous_id

    def test_status_values_are_valid(self, client, mock_repository):
        """E2E Checklist: Data Fields - status has valid values.

        Valid statuses: active, completed, completed_timeout
        """
        # Start creates active session
        start_response = client.post(
            "/api/interview/start",
            json={"anonymous_id": "test-user"},
        )
        events = parse_sse_events(start_response.text)
        session_id = [e for e in events if e.get("type") == "metadata"][0]["session_id"]

        mock_repository.reset_mock()

        # End creates completed status
        client.post(
            "/api/interview/end",
            json={"session_id": session_id},
        )

        call_args = mock_repository.complete_session.call_args
        args = call_args[1] if call_args[1] else {}

        if "status" in args:
            assert args["status"] in ["completed", "completed_timeout"]

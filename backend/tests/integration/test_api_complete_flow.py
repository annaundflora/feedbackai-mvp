"""Integration tests for complete API flows.

Tests the full interview lifecycle: start -> message -> end
"""

import json
import re


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


class TestCompleteInterviewFlow:
    """Test complete interview lifecycle: Start -> Message -> End."""

    def test_happy_path_single_message(self, client):
        """Flow 1: Complete interview with one message.

        E2E Checklist: Flow 1, Steps 3-12
        """
        # Step 1: Start interview
        start_response = client.post(
            "/api/interview/start",
            json={"anonymous_id": "test-user-1"},
        )
        assert start_response.status_code == 200
        assert "text/event-stream" in start_response.headers.get("content-type", "")

        # Parse SSE events
        start_events = parse_sse_events(start_response.text)

        # Verify text-delta events
        text_deltas = [e for e in start_events if e.get("type") == "text-delta"]
        assert len(text_deltas) >= 1

        # Verify text-done event
        text_done = [e for e in start_events if e.get("type") == "text-done"]
        assert len(text_done) == 1

        # Extract session_id from metadata
        metadata = [e for e in start_events if e.get("type") == "metadata"]
        assert len(metadata) == 1
        session_id = metadata[0]["session_id"]

        # Verify session_id is UUID
        uuid_pattern = re.compile(
            r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
            re.IGNORECASE,
        )
        assert uuid_pattern.match(session_id)

        # Step 2: Send a message
        message_response = client.post(
            "/api/interview/message",
            json={
                "session_id": session_id,
                "message": "Das Bidding ist frustrierend",
            },
        )
        assert message_response.status_code == 200
        assert "text/event-stream" in message_response.headers.get("content-type", "")

        # Parse message response
        message_events = parse_sse_events(message_response.text)
        assert len([e for e in message_events if e.get("type") == "text-delta"]) >= 1
        assert len([e for e in message_events if e.get("type") == "text-done"]) == 1

        # Step 3: End interview
        end_response = client.post(
            "/api/interview/end",
            json={"session_id": session_id},
        )
        assert end_response.status_code == 200

        end_data = end_response.json()
        assert "summary" in end_data
        assert "message_count" in end_data
        assert isinstance(end_data["summary"], str)
        assert len(end_data["summary"]) > 0
        assert end_data["message_count"] == 1

    def test_happy_path_multiple_messages(self, client):
        """Flow 1: Complete interview with multiple messages.

        E2E Checklist: Flow 1, Steps 9-12
        """
        # Start interview
        start_response = client.post(
            "/api/interview/start",
            json={"anonymous_id": "test-user-2"},
        )
        start_events = parse_sse_events(start_response.text)
        metadata = [e for e in start_events if e.get("type") == "metadata"][0]
        session_id = metadata["session_id"]

        # Send multiple messages
        messages = [
            "Das Bidding ist frustrierend",
            "Ich wünsche mir einen einfacheren Prozess",
            "Die UI könnte intuitiver sein",
        ]

        for msg in messages:
            response = client.post(
                "/api/interview/message",
                json={"session_id": session_id, "message": msg},
            )
            assert response.status_code == 200

        # End interview
        end_response = client.post(
            "/api/interview/end",
            json={"session_id": session_id},
        )
        assert end_response.status_code == 200

        end_data = end_response.json()
        assert end_data["message_count"] == 3

    def test_parallel_sessions_different_users(self, client):
        """E2E Checklist: Boundary Conditions - Parallele Sessions.

        Multiple users can have concurrent sessions without interference.
        """
        # Start three parallel sessions
        sessions = []
        for i in range(3):
            response = client.post(
                "/api/interview/start",
                json={"anonymous_id": f"user-{i}"},
            )
            events = parse_sse_events(response.text)
            metadata = [e for e in events if e.get("type") == "metadata"][0]
            sessions.append(metadata["session_id"])

        # Verify all sessions are unique
        assert len(sessions) == len(set(sessions))

        # Send messages to each session
        for session_id in sessions:
            response = client.post(
                "/api/interview/message",
                json={"session_id": session_id, "message": "Test message"},
            )
            assert response.status_code == 200

        # End all sessions
        for session_id in sessions:
            response = client.post(
                "/api/interview/end",
                json={"session_id": session_id},
            )
            assert response.status_code == 200
            assert response.json()["message_count"] == 1

    def test_same_user_multiple_sessions(self, client):
        """Same user can have multiple sequential sessions."""
        anonymous_id = "repeat-user"

        # First session
        start1 = client.post(
            "/api/interview/start",
            json={"anonymous_id": anonymous_id},
        )
        events1 = parse_sse_events(start1.text)
        session_id_1 = [e for e in events1 if e.get("type") == "metadata"][0][
            "session_id"
        ]

        # End first session
        client.post("/api/interview/end", json={"session_id": session_id_1})

        # Second session for same user
        start2 = client.post(
            "/api/interview/start",
            json={"anonymous_id": anonymous_id},
        )
        events2 = parse_sse_events(start2.text)
        session_id_2 = [e for e in events2 if e.get("type") == "metadata"][0][
            "session_id"
        ]

        # Sessions should be different
        assert session_id_1 != session_id_2

    def test_very_long_message(self, client):
        """E2E Checklist: Boundary Conditions - Sehr lange Nachricht.

        10000-character message is processed correctly.
        """
        # Start session
        start_response = client.post(
            "/api/interview/start",
            json={"anonymous_id": "long-message-user"},
        )
        events = parse_sse_events(start_response.text)
        session_id = [e for e in events if e.get("type") == "metadata"][0]["session_id"]

        # Send very long message (max allowed is 10000)
        long_message = "x" * 10000

        response = client.post(
            "/api/interview/message",
            json={"session_id": session_id, "message": long_message},
        )
        assert response.status_code == 200

        # Verify message was processed
        events = parse_sse_events(response.text)
        assert len([e for e in events if e.get("type") == "text-delta"]) >= 1

    def test_many_messages_in_session(self, client):
        """E2E Checklist: Boundary Conditions - Viele Messages.

        Session with 20+ messages works correctly.
        """
        # Start session
        start_response = client.post(
            "/api/interview/start",
            json={"anonymous_id": "chatty-user"},
        )
        events = parse_sse_events(start_response.text)
        session_id = [e for e in events if e.get("type") == "metadata"][0]["session_id"]

        # Send 20 messages
        num_messages = 20
        for i in range(num_messages):
            response = client.post(
                "/api/interview/message",
                json={"session_id": session_id, "message": f"Message {i + 1}"},
            )
            assert response.status_code == 200

        # End and verify count
        end_response = client.post(
            "/api/interview/end",
            json={"session_id": session_id},
        )
        assert end_response.status_code == 200
        assert end_response.json()["message_count"] == num_messages


class TestHealthCheck:
    """Test health check endpoint."""

    def test_health_check_returns_ok(self, client):
        """E2E Checklist: Flow 1, Step 1 - Health check returns 200."""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

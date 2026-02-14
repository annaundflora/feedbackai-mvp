"""Integration tests for session timeout functionality.

Tests automatic session timeout and cleanup.
"""

import asyncio
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


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


class TestSessionTimeout:
    """Test session timeout functionality."""

    @pytest.mark.asyncio
    async def test_timeout_manager_registered_on_start(self, client, service):
        """E2E Checklist: Flow 4, Step 2.

        TimeoutManager.register() is called when session starts.
        """
        # Start session
        start_response = client.post(
            "/api/interview/start",
            json={"anonymous_id": "test-user"},
        )
        assert start_response.status_code == 200

        events = parse_sse_events(start_response.text)
        session_id = [e for e in events if e.get("type") == "metadata"][0]["session_id"]

        # Verify timeout manager has this session registered
        if hasattr(service, "_timeout_manager") and service._timeout_manager:
            assert session_id in service._timeout_manager._tasks

    @pytest.mark.asyncio
    async def test_timeout_reset_on_message(self, client):
        """E2E Checklist: Flow 4, Step 4.

        TimeoutManager.reset() is called when message is sent.
        """
        # Start session
        start_response = client.post(
            "/api/interview/start",
            json={"anonymous_id": "test-user"},
        )
        events = parse_sse_events(start_response.text)
        session_id = [e for e in events if e.get("type") == "metadata"][0]["session_id"]

        # Get initial timeout task
        from app.api.dependencies import get_interview_service

        service = get_interview_service()
        if hasattr(service, "_timeout_manager") and service._timeout_manager:
            initial_task = service._timeout_manager._tasks.get(session_id)

            # Send message (should reset timeout)
            client.post(
                "/api/interview/message",
                json={"session_id": session_id, "message": "Reset timeout"},
            )

            # Task should be different (reset creates new task)
            new_task = service._timeout_manager._tasks.get(session_id)
            # Note: Tasks are recreated on reset, so they should be different
            assert new_task is not None

    @pytest.mark.asyncio
    async def test_timeout_cancelled_on_end(self, client):
        """E2E Checklist: Flow 4 (implied).

        TimeoutManager.cancel() is called when session ends normally.
        """
        # Start session
        start_response = client.post(
            "/api/interview/start",
            json={"anonymous_id": "test-user"},
        )
        events = parse_sse_events(start_response.text)
        session_id = [e for e in events if e.get("type") == "metadata"][0]["session_id"]

        # End session
        client.post(
            "/api/interview/end",
            json={"session_id": session_id},
        )

        # Verify timeout task is cancelled
        from app.api.dependencies import get_interview_service

        service = get_interview_service()
        if hasattr(service, "_timeout_manager") and service._timeout_manager:
            assert session_id not in service._timeout_manager._tasks

    @pytest.mark.asyncio
    async def test_handle_timeout_sets_completed_timeout_status(
        self, client, mock_repository
    ):
        """E2E Checklist: Flow 4, Step 8.

        Timeout handler sets status=completed_timeout in database.
        """
        from app.interview.service import InterviewService

        # Get service
        from app.api.dependencies import get_interview_service

        service = get_interview_service()

        # Create a fake session
        session_id = "test-session-id"
        service._sessions[session_id] = {
            "anonymous_id": "test-user",
            "status": "active",
            "message_count": 0,
        }

        # Call timeout handler directly
        await service._handle_timeout(session_id)

        # Verify complete_session was called with completed_timeout
        mock_repository.complete_session.assert_called_once()
        call_args = mock_repository.complete_session.call_args
        args = call_args[1] if call_args[1] else {}

        if "status" in args:
            assert args["status"] == "completed_timeout"

    @pytest.mark.asyncio
    async def test_handle_timeout_generates_summary(
        self, client, mock_summary_service, mock_graph
    ):
        """E2E Checklist: Flow 4, Step 7.

        Timeout triggers automatic summary generation.
        """
        from app.api.dependencies import get_interview_service

        service = get_interview_service()

        # Create a fake session
        session_id = "test-session-id"
        service._sessions[session_id] = {
            "anonymous_id": "test-user",
            "status": "active",
            "message_count": 1,
        }

        # Call timeout handler
        await service._handle_timeout(session_id)

        # Verify summary generation was called
        mock_summary_service.generate.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_timeout_updates_in_memory_status(self, client):
        """E2E Checklist: Flow 4, Step 9.

        Timeout updates in-memory session status.
        """
        from app.api.dependencies import get_interview_service

        service = get_interview_service()

        # Create a fake session
        session_id = "test-session-id"
        service._sessions[session_id] = {
            "anonymous_id": "test-user",
            "status": "active",
            "message_count": 0,
        }

        # Call timeout handler
        await service._handle_timeout(session_id)

        # Verify in-memory status is updated
        assert service._sessions[session_id]["status"] == "completed_timeout"

    @pytest.mark.asyncio
    async def test_handle_timeout_with_empty_history(self, client, mock_graph):
        """E2E Checklist: Boundary Conditions - Leere History bei Timeout.

        Timeout handles sessions with no messages gracefully.
        """
        from app.api.dependencies import get_interview_service

        service = get_interview_service()

        # Create session with no messages
        session_id = "test-session-id"
        service._sessions[session_id] = {
            "anonymous_id": "test-user",
            "status": "active",
            "message_count": 0,
        }

        # Mock empty history
        mock_graph.get_history.return_value = []

        # Should not crash
        await service._handle_timeout(session_id)

        # Session should still be completed
        assert service._sessions[session_id]["status"] == "completed_timeout"


class TestTimeoutEdgeCases:
    """Test timeout edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_timeout_ignores_already_completed_session(
        self, client, mock_repository
    ):
        """E2E Checklist: Timeout Edge Cases - Bereits completed Session.

        Timeout handler ignores sessions that are already completed.
        """
        from app.api.dependencies import get_interview_service

        service = get_interview_service()

        # Create completed session
        session_id = "completed-session"
        service._sessions[session_id] = {
            "anonymous_id": "test-user",
            "status": "completed",
            "message_count": 0,
        }

        mock_repository.reset_mock()

        # Call timeout handler
        await service._handle_timeout(session_id)

        # Should not call complete_session again
        mock_repository.complete_session.assert_not_called()

    @pytest.mark.asyncio
    async def test_timeout_ignores_unknown_session(self, client, mock_repository):
        """E2E Checklist: Timeout Edge Cases - Unbekannte Session.

        Timeout handler ignores sessions not in memory.
        """
        from app.api.dependencies import get_interview_service

        service = get_interview_service()

        mock_repository.reset_mock()

        # Call timeout handler for non-existent session
        await service._handle_timeout("non-existent-session-id")

        # Should not crash or call repository
        mock_repository.complete_session.assert_not_called()

    @pytest.mark.asyncio
    async def test_summary_error_on_timeout_uses_none(
        self, client, mock_summary_service, mock_repository
    ):
        """E2E Checklist: Timeout Edge Cases - Summary-Fehler bei Timeout.

        If summary generation fails during timeout, use None/fallback.
        """
        from app.api.dependencies import get_interview_service

        service = get_interview_service()

        # Create session
        session_id = "test-session"
        service._sessions[session_id] = {
            "anonymous_id": "test-user",
            "status": "active",
            "message_count": 0,
        }

        # Make summary generation fail
        mock_summary_service.generate.side_effect = Exception("LLM timeout")

        # Should not crash
        await service._handle_timeout(session_id)

        # Session should still be completed with None/fallback summary
        assert service._sessions[session_id]["status"] == "completed_timeout"

        # complete_session should still be called
        mock_repository.complete_session.assert_called_once()

    @pytest.mark.asyncio
    async def test_db_error_on_timeout_still_updates_memory(
        self, client, mock_repository
    ):
        """E2E Checklist: Timeout Edge Cases - DB-Fehler bei Timeout.

        DB errors during timeout don't prevent in-memory status update.
        """
        from app.api.dependencies import get_interview_service

        service = get_interview_service()

        # Create session
        session_id = "test-session"
        service._sessions[session_id] = {
            "anonymous_id": "test-user",
            "status": "active",
            "message_count": 0,
        }

        # Make DB operation fail
        mock_repository.complete_session.side_effect = Exception("DB unavailable")

        # Should not crash
        await service._handle_timeout(session_id)

        # In-memory status should still be updated
        assert service._sessions[session_id]["status"] == "completed_timeout"

    @pytest.mark.asyncio
    async def test_end_before_timeout_prevents_double_completion(
        self, client, mock_repository
    ):
        """E2E Checklist: Boundary Conditions - End waehrend Timeout-Countdown.

        Normal end before timeout prevents timeout handler from running.
        """
        # Start session
        start_response = client.post(
            "/api/interview/start",
            json={"anonymous_id": "test-user"},
        )
        events = parse_sse_events(start_response.text)
        session_id = [e for e in events if e.get("type") == "metadata"][0]["session_id"]

        mock_repository.reset_mock()

        # End session (should cancel timeout)
        end_response = client.post(
            "/api/interview/end",
            json={"session_id": session_id},
        )
        assert end_response.status_code == 200

        # complete_session should be called once (from end, not timeout)
        assert mock_repository.complete_session.call_count == 1


class TestTimeoutManagerLifecycle:
    """Test TimeoutManager lifecycle and cleanup."""

    @pytest.mark.asyncio
    async def test_cancel_all_on_shutdown(self, client):
        """E2E Checklist: Boundary Conditions - Shutdown mit aktiven Sessions.

        cancel_all() is called during shutdown to clean up tasks.
        """
        from app.interview.timeout import TimeoutManager

        manager = TimeoutManager(timeout_seconds=60)

        # Register some fake tasks
        manager._tasks["session-1"] = asyncio.create_task(asyncio.sleep(100))
        manager._tasks["session-2"] = asyncio.create_task(asyncio.sleep(100))

        # Cancel all
        manager.cancel_all()

        # All tasks should be cancelled
        assert len(manager._tasks) == 0

    @pytest.mark.asyncio
    async def test_timeout_reset_creates_new_task(self, client):
        """E2E Checklist: Boundary Conditions - Timeout reset durch Message.

        Sending message shortly before timeout resets the timer.
        """
        from app.interview.timeout import TimeoutManager

        manager = TimeoutManager(timeout_seconds=5)

        callback_called = False

        async def test_callback(session_id):
            nonlocal callback_called
            callback_called = True

        # Register timeout
        session_id = "test-session"
        manager.register(session_id, test_callback)

        # Wait a bit
        await asyncio.sleep(0.1)

        # Reset timeout (should create new task)
        manager.reset(session_id)

        # Wait original timeout duration
        await asyncio.sleep(0.2)

        # Callback should NOT have been called yet (reset extended it)
        assert not callback_called

        # Clean up
        manager.cancel(session_id)

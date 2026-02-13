"""InterviewService -- orchestrates interview lifecycle."""

import uuid
import json
from datetime import datetime, timezone
from typing import AsyncGenerator

from langchain_core.messages import HumanMessage, AIMessageChunk

from app.interview.graph import InterviewGraph


class SessionNotFoundError(Exception):
    """Session ID does not exist."""

    pass


class SessionAlreadyCompletedError(Exception):
    """Session has already been completed."""

    pass


class InterviewService:
    """Orchestrates the interview lifecycle.

    Session management via in-memory dict (will be replaced by Supabase in Slice 4).
    """

    def __init__(self, graph: InterviewGraph) -> None:
        self._graph = graph
        self._sessions: dict[str, dict] = {}

    async def start(self, anonymous_id: str) -> AsyncGenerator[str, None]:
        """Starts a new interview.

        1. Creates session_id (UUID)
        2. Registers session in-memory
        3. Streams opening question via graph
        4. Sends metadata with session_id

        Args:
            anonymous_id: Client-generated user ID.

        Yields:
            SSE-formatted JSON strings (text-delta, text-done, metadata).
        """
        session_id = str(uuid.uuid4())
        self._sessions[session_id] = {
            "status": "active",
            "anonymous_id": anonymous_id,
            "message_count": 0,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        try:
            async for sse_line in self._stream_graph(
                messages=[],
                session_id=session_id,
            ):
                yield sse_line

            # After text-done: send metadata with session_id
            yield json.dumps({"type": "metadata", "session_id": session_id})
        except Exception as e:
            yield json.dumps({"type": "error", "message": str(e)})

    async def message(self, session_id: str, message: str) -> AsyncGenerator[str, None]:
        """Processes a user message and streams the response.

        1. Validates session (exists, status=active)
        2. Streams response via graph
        3. Increments message_count

        Args:
            session_id: Session UUID.
            message: User message.

        Yields:
            SSE-formatted JSON strings (text-delta, text-done).

        Raises:
            SessionNotFoundError: Session does not exist.
            SessionAlreadyCompletedError: Session has already been completed.
        """
        self._validate_session(session_id)

        try:
            async for sse_line in self._stream_graph(
                messages=[HumanMessage(content=message)],
                session_id=session_id,
            ):
                yield sse_line

            self._sessions[session_id]["message_count"] += 1
        except (SessionNotFoundError, SessionAlreadyCompletedError):
            raise
        except Exception as e:
            yield json.dumps({"type": "error", "message": str(e)})

    async def end(self, session_id: str) -> dict:
        """Ends an interview.

        1. Validates session (exists, status=active)
        2. Reads history from graph
        3. Sets status to "completed"
        4. Returns placeholder summary (real summary in Slice 5)

        Args:
            session_id: Session UUID.

        Returns:
            Dict with summary and message_count.

        Raises:
            SessionNotFoundError: Session does not exist.
            SessionAlreadyCompletedError: Session has already been completed.
        """
        self._validate_session(session_id)

        message_count = self._sessions[session_id]["message_count"]
        self._sessions[session_id]["status"] = "completed"

        return {
            "summary": "Summary-Generierung noch nicht implementiert (Slice 5)",
            "message_count": message_count,
        }

    async def _stream_graph(
        self,
        messages: list,
        session_id: str,
    ) -> AsyncGenerator[str, None]:
        """Streams graph output as SSE-formatted JSON strings.

        Filters only AIMessageChunks with content (no metadata chunks).

        Args:
            messages: Input messages for the graph.
            session_id: Session UUID (thread_id for MemorySaver).

        Yields:
            SSE-formatted JSON strings.
        """
        async for chunk, metadata in self._graph.astream(
            messages=messages,
            session_id=session_id,
        ):
            # Only stream AIMessageChunks with content
            if isinstance(chunk, AIMessageChunk) and chunk.content:
                yield json.dumps({"type": "text-delta", "content": chunk.content})

        # Stream completed
        yield json.dumps({"type": "text-done"})

    def _validate_session(self, session_id: str) -> None:
        """Checks if session exists and is active.

        Args:
            session_id: Session UUID.

        Raises:
            SessionNotFoundError: Session does not exist.
            SessionAlreadyCompletedError: Session is no longer active.
        """
        if session_id not in self._sessions:
            raise SessionNotFoundError(f"Session not found: {session_id}")

        if self._sessions[session_id]["status"] != "active":
            raise SessionAlreadyCompletedError(f"Session already completed: {session_id}")

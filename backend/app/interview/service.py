"""InterviewService -- orchestrates interview lifecycle."""

import uuid
import json
import logging
from datetime import datetime, timezone
from typing import AsyncGenerator

from langchain_core.messages import HumanMessage, AIMessage, AIMessageChunk

from app.interview.graph import InterviewGraph
from app.interview.repository import InterviewRepository


logger = logging.getLogger(__name__)


class SessionNotFoundError(Exception):
    """Session ID does not exist."""

    pass


class SessionAlreadyCompletedError(Exception):
    """Session has already been completed."""

    pass


class InterviewService:
    """Orchestrates the interview lifecycle.

    Session management via in-memory dict (cache) + Supabase (source of truth).
    """

    def __init__(
        self,
        graph: InterviewGraph,
        repository: InterviewRepository | None = None,
    ) -> None:
        self._graph = graph
        self._repository = repository
        self._sessions: dict[str, dict] = {}

    async def start(self, anonymous_id: str) -> AsyncGenerator[str, None]:
        """Starts a new interview.

        1. Creates session_id (UUID)
        2. Registers session in-memory
        3. Creates session in Supabase
        4. Streams opening question via graph
        5. Sends metadata with session_id

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

        # DB-Insert (non-blocking, errors are logged but don't block)
        if self._repository:
            try:
                await self._repository.create_session(session_id, anonymous_id)
            except Exception as e:
                logger.error(f"DB create_session failed for {session_id}: {e}")

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
        3. Increments message_count (in-memory + DB)

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

            # DB message_count + timestamp update
            if self._repository:
                try:
                    await self._repository.increment_message_count(session_id)
                except Exception as e:
                    logger.error(f"DB increment_message_count failed for {session_id}: {e}")
        except (SessionNotFoundError, SessionAlreadyCompletedError):
            raise
        except Exception as e:
            yield json.dumps({"type": "error", "message": str(e)})

    async def end(self, session_id: str) -> dict:
        """Ends an interview.

        1. Validates session (exists, status=active)
        2. Reads history from graph
        3. Formats transcript as JSONB
        4. Saves transcript + placeholder summary in Supabase
        5. Sets status to "completed"

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

        # Read transcript from graph history and format
        history = self._graph.get_history(session_id)
        transcript = self._format_transcript(history)

        placeholder_summary = "Summary-Generierung noch nicht implementiert (Slice 5)"

        # DB-Update: Save transcript + summary
        if self._repository:
            try:
                await self._repository.complete_session(
                    session_id=session_id,
                    transcript=transcript,
                    summary=placeholder_summary,
                    message_count=message_count,
                )
            except Exception as e:
                logger.error(f"DB complete_session failed for {session_id}: {e}")

        self._sessions[session_id]["status"] = "completed"

        return {
            "summary": placeholder_summary,
            "message_count": message_count,
        }

    @staticmethod
    def _format_transcript(messages: list) -> list[dict[str, str]]:
        """Converts LangChain messages to JSONB-compatible format.

        Args:
            messages: List of LangChain message objects.

        Returns:
            List of {role, content} dicts for JSONB storage.
        """
        transcript = []
        for msg in messages:
            if isinstance(msg, HumanMessage):
                transcript.append({"role": "user", "content": msg.content})
            elif isinstance(msg, AIMessage):
                transcript.append({"role": "assistant", "content": msg.content})
        return transcript

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

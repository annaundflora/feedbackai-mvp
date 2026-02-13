"""FastAPI dependency injection for services."""

from fastapi import Request

from app.config.settings import Settings
from app.interview.graph import InterviewGraph
from app.interview.service import InterviewService


_interview_service: InterviewService | None = None


def get_interview_service(request: Request) -> InterviewService:
    """FastAPI dependency for InterviewService (Singleton).

    Creates InterviewService + InterviewGraph on first call.
    Uses app.state.settings from Slice 1 lifespan.
    """
    global _interview_service
    if _interview_service is None:
        settings: Settings = request.app.state.settings
        graph = InterviewGraph(settings=settings)
        _interview_service = InterviewService(graph=graph)
    return _interview_service


def reset_interview_service() -> None:
    """Resets the singleton (for tests)."""
    global _interview_service
    _interview_service = None

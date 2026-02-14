"""FastAPI dependency injection for services."""

from fastapi import Request

from app.config.settings import Settings
from app.db.supabase import get_supabase_client
from app.insights.summary import SummaryService
from app.interview.graph import InterviewGraph
from app.interview.repository import InterviewRepository
from app.interview.service import InterviewService
from app.interview.timeout import TimeoutManager

_interview_service: InterviewService | None = None


def get_interview_service(request: Request) -> InterviewService:
    """FastAPI dependency for InterviewService (Singleton).

    Creates InterviewService + InterviewGraph + InterviewRepository on first call.
    Uses app.state.settings from Slice 1 lifespan.
    """
    global _interview_service
    if _interview_service is None:
        settings: Settings = request.app.state.settings
        graph = InterviewGraph(settings=settings)
        supabase_client = get_supabase_client(settings)
        repository = InterviewRepository(
            supabase_client=supabase_client,
            settings=settings,
        )
        summary_service = SummaryService(settings=settings)

        # InterviewService zuerst ohne TimeoutManager erstellen
        service = InterviewService(
            graph=graph,
            repository=repository,
            summary_service=summary_service,
        )

        # TimeoutManager mit dem Service-Callback erstellen
        timeout_manager = TimeoutManager(
            timeout_seconds=settings.session_timeout_seconds,
            on_timeout_callback=service._handle_timeout,
        )
        service._timeout_manager = timeout_manager

        # Auf app.state speichern fuer Lifespan-Cleanup
        request.app.state.timeout_manager = timeout_manager

        _interview_service = service
    return _interview_service


def reset_interview_service() -> None:
    """Resets the singleton (for tests)."""
    global _interview_service
    _interview_service = None


def get_interview_service_for_tests() -> InterviewService | None:
    """Get the current InterviewService singleton (for tests only).

    Returns None if no service has been created yet.
    """
    return _interview_service

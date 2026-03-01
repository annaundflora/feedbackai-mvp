"""FastAPI dependency injection for services."""

from fastapi import Request

from app.clustering.events import SseEventBus
from app.clustering.extraction import FactExtractionService
from app.clustering.fact_repository import FactRepository
from app.clustering.interview_assignment_repository import InterviewAssignmentRepository
from app.config.settings import Settings
from app.db.session import get_session_factory
from app.insights.summary import SummaryService
from app.interview.graph import InterviewGraph
from app.interview.repository import InterviewRepository
from app.interview.service import InterviewService
from app.interview.timeout import TimeoutManager

_interview_service: InterviewService | None = None
_sse_event_bus: SseEventBus | None = None
_fact_extraction_service: FactExtractionService | None = None


def get_sse_event_bus(request: Request) -> SseEventBus:
    """FastAPI dependency fuer SseEventBus (Singleton).

    SseEventBus wird als Singleton gehalten, damit alle Services
    und der SSE-Endpoint die gleiche Instanz verwenden.

    Bevorzugt app.state.event_bus (gesetzt im Lifespan) fuer korrekte Singleton-Semantik.
    Faellt zurueck auf globale Variable fuer Tests ohne Lifespan.
    """
    global _sse_event_bus
    # Bevorzuge app.state.event_bus (vom Lifespan gesetzt) -- gleiche Instanz wie ClusteringService
    event_bus = getattr(request.app.state, "event_bus", None)
    if event_bus is not None:
        return event_bus
    # Fallback: Globale Variable (fuer Tests ohne Lifespan)
    if _sse_event_bus is None:
        _sse_event_bus = SseEventBus()
        request.app.state.event_bus = _sse_event_bus
    return _sse_event_bus


def get_fact_extraction_service(request: Request) -> FactExtractionService:
    """FastAPI dependency fuer FactExtractionService (Singleton).

    Erstellt FactExtractionService mit allen Abhaengigkeiten.
    """
    global _fact_extraction_service
    if _fact_extraction_service is None:
        settings: Settings = request.app.state.settings
        session_factory = get_session_factory(settings)

        fact_repository = FactRepository(session_factory=session_factory)
        assignment_repository = InterviewAssignmentRepository(session_factory=session_factory)
        interview_repository = InterviewRepository(session_factory=session_factory)

        from app.clustering.project_repository import ProjectRepository
        project_repository = ProjectRepository(session_factory=session_factory)

        event_bus = get_sse_event_bus(request)

        _fact_extraction_service = FactExtractionService(
            fact_repository=fact_repository,
            assignment_repository=assignment_repository,
            project_repository=project_repository,
            interview_repository=interview_repository,
            event_bus=event_bus,
            settings=settings,
        )
        request.app.state.fact_extraction_service = _fact_extraction_service

    return _fact_extraction_service


def get_interview_service(request: Request) -> InterviewService:
    """FastAPI dependency for InterviewService (Singleton).

    Creates InterviewService + InterviewGraph + InterviewRepository on first call.
    Uses app.state.settings from Slice 1 lifespan.
    """
    global _interview_service
    if _interview_service is None:
        settings: Settings = request.app.state.settings
        graph = InterviewGraph(settings=settings)
        session_factory = get_session_factory(settings)
        repository = InterviewRepository(session_factory=session_factory)
        summary_service = SummaryService(settings=settings)

        # Slice 2: InterviewAssignmentRepository fuer Clustering-Trigger
        assignment_repository = InterviewAssignmentRepository(session_factory=session_factory)

        # Slice 2: FactExtractionService fuer Clustering-Trigger
        fact_extraction_svc = get_fact_extraction_service(request)

        # InterviewService zuerst ohne TimeoutManager erstellen
        service = InterviewService(
            graph=graph,
            repository=repository,
            summary_service=summary_service,
            fact_extraction_service=fact_extraction_svc,
            assignment_repository=assignment_repository,
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


def reset_all_singletons() -> None:
    """Resets all singletons (for tests)."""
    global _interview_service, _sse_event_bus, _fact_extraction_service
    _interview_service = None
    _sse_event_bus = None
    _fact_extraction_service = None


def get_interview_service_for_tests() -> InterviewService | None:
    """Get the current InterviewService singleton (for tests only).

    Returns None if no service has been created yet.
    """
    return _interview_service

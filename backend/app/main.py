"""FeedbackAI Backend -- FastAPI Application."""

import logging
import logging.config
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Debug-Logging fuer Clustering-Module (sichtbar in Uvicorn stdout)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logging.getLogger("app.clustering").setLevel(logging.DEBUG)

from app.api.auth_routes import router as auth_router
from app.api.routes import router as interview_router
from app.api.sse_routes import router as sse_router
from app.clustering.cluster_repository import ClusterRepository
from app.clustering.cluster_suggestion_repository import ClusterSuggestionRepository
from app.clustering.events import SseEventBus
from app.clustering.extraction import FactExtractionService
from app.clustering.fact_repository import FactRepository
from app.clustering.graph import ClusteringGraph
from app.clustering.interview_assignment_repository import InterviewAssignmentRepository
from app.clustering.models import run_migration
from app.clustering.project_repository import ProjectRepository
from app.clustering.router import router as clustering_router
from app.clustering.service import ClusteringService
from app.config.settings import Settings
from app.db.session import dispose_engine, get_session_factory

# Load .env into os.environ so LangChain/LangSmith SDK can read LANGSMITH_* vars
load_dotenv(dotenv_path="../.env", override=False)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager -- startup and shutdown logic."""
    # Startup
    settings = Settings()
    app.state.settings = settings

    # DB-Migration fuer Clustering-Tabellen ausfuehren (idempotent)
    session_factory = get_session_factory(settings)
    await run_migration(session_factory)

    # Singleton Services initialisieren
    event_bus = SseEventBus()
    app.state.event_bus = event_bus

    fact_repo = FactRepository(session_factory=session_factory)
    assignment_repo = InterviewAssignmentRepository(session_factory=session_factory)
    project_repo = ProjectRepository(session_factory=session_factory)
    cluster_repo = ClusterRepository(session_factory=session_factory)
    suggestion_repo = ClusterSuggestionRepository(session_factory=session_factory)

    # ClusteringGraph und ClusteringService initialisieren (Slice 3)
    clustering_graph = ClusteringGraph(settings=settings)
    clustering_service = ClusteringService(
        clustering_graph=clustering_graph,
        cluster_repository=cluster_repo,
        cluster_suggestion_repository=suggestion_repo,
        fact_repository=fact_repo,
        assignment_repository=assignment_repo,
        project_repository=project_repo,
        event_bus=event_bus,
        settings=settings,
    )
    app.state.clustering_service = clustering_service

    # FactExtractionService mit ClusteringService DI initialisieren (Slice 2 + 3)
    from app.interview.repository import InterviewRepository
    interview_repo = InterviewRepository(session_factory=session_factory)

    fact_extraction_service = FactExtractionService(
        fact_repository=fact_repo,
        assignment_repository=assignment_repo,
        project_repository=project_repo,
        interview_repository=interview_repo,
        event_bus=event_bus,
        settings=settings,
        clustering_service=clustering_service,
    )
    app.state.fact_extraction_service = fact_extraction_service

    yield
    # Shutdown: Alle Timeout-Tasks canceln
    timeout_manager = getattr(app.state, "timeout_manager", None)
    if timeout_manager:
        timeout_manager.cancel_all()
    # DB-Engine schliessen
    await dispose_engine()


app = FastAPI(
    title="FeedbackAI Backend",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # MVP: allow all origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok"}


app.include_router(auth_router)
app.include_router(interview_router)
app.include_router(clustering_router)
app.include_router(sse_router)

"""FeedbackAI Backend -- FastAPI Application."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router as interview_router
from app.config.settings import Settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager -- startup and shutdown logic."""
    # Startup
    settings = Settings()
    app.state.settings = settings
    yield
    # Shutdown: Alle Timeout-Tasks canceln
    timeout_manager = getattr(app.state, "timeout_manager", None)
    if timeout_manager:
        timeout_manager.cancel_all()


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


app.include_router(interview_router)

"""Pydantic Settings -- type-safe .env configuration."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # OpenRouter
    openrouter_api_key: str

    # Interviewer Config
    interviewer_llm: str = "anthropic/claude-sonnet-4.5"
    interviewer_temperature: float = 1.0
    interviewer_max_tokens: int = 4000

    # Session
    session_timeout_seconds: int = 60

    # Timeouts
    llm_timeout_seconds: int = 30
    db_timeout_seconds: int = 10

    # PostgreSQL
    database_url: str
    db_echo: bool = False
    db_pool_size: int = 5
    db_max_overflow: int = 10

    # LangSmith (optional)
    langsmith_tracing: bool = True
    langsmith_endpoint: str = "https://eu.api.smith.langchain.com"
    langsmith_api_key: str = ""
    langsmith_project: str = "FeedbackAI"

    # Clustering Pipeline (Slice 2)
    clustering_max_retries: int = 3
    clustering_llm_timeout_seconds: int = 120
    clustering_batch_size: int = 20
    clustering_pipeline_timeout_seconds: int = 600

    # ClusteringGraph Defaults (Slice 3)
    clustering_model_default: str = "anthropic/claude-sonnet-4"
    summary_model_default: str = "anthropic/claude-haiku-4"
    clustering_split_threshold: int = 8          # Facts/Cluster -> Split-Suggestion
    clustering_merge_similarity_threshold: float = 0.8  # 80% -> Merge-Suggestion
    clustering_taxonomy_batch_size: int = 20     # Facts pro Batch bei generate_taxonomy

    @property
    def async_database_url(self) -> str:
        """Konvertiert postgresql:// zu postgresql+asyncpg:// fuer async Engine."""
        url = self.database_url
        if url.startswith("postgresql://"):
            return url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return url

    model_config = {
        "env_file": "../.env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",  # Allow extra fields in .env that are not defined in Settings
    }

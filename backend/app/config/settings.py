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

    # Supabase
    supabase_url: str
    supabase_key: str

    # LangSmith (optional)
    langsmith_tracing: bool = True
    langsmith_endpoint: str = "https://eu.api.smith.langchain.com"
    langsmith_api_key: str = ""
    langsmith_project: str = "FeedbackAI"

    model_config = {
        "env_file": "../.env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",  # Allow extra fields in .env that are not defined in Settings
    }

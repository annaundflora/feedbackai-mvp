# backend/tests/slices/backend-kern/test_slice_01_app_skeleton.py
import pytest
from pathlib import Path
from unittest.mock import patch
from fastapi.testclient import TestClient


# -- Health Check --

class TestHealthCheck:
    """AC 1: GET /health gibt 200 mit {"status": "ok"} zurueck."""

    def test_health_returns_200(self, client: TestClient):
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_returns_status_ok(self, client: TestClient):
        response = client.get("/health")
        assert response.json() == {"status": "ok"}


# -- Settings --

class TestSettings:
    """AC 2 + AC 3: Pydantic Settings laden und validieren."""

    def test_settings_loads_from_env(self):
        """AC 2: Settings laden alle Pflicht-Variablen."""
        with patch.dict("os.environ", {
            "OPENROUTER_API_KEY": "test-key",
            "SUPABASE_URL": "https://test.supabase.co",
            "SUPABASE_KEY": "test-supabase-key",
        }, clear=False):
            from app.config.settings import Settings
            settings = Settings()
            assert settings.openrouter_api_key == "test-key"
            assert settings.supabase_url == "https://test.supabase.co"
            assert settings.supabase_key == "test-supabase-key"

    def test_settings_default_values(self):
        """AC 2: Default-Werte sind korrekt gesetzt."""
        with patch.dict("os.environ", {
            "OPENROUTER_API_KEY": "test-key",
            "SUPABASE_URL": "https://test.supabase.co",
            "SUPABASE_KEY": "test-supabase-key",
        }, clear=False):
            from app.config.settings import Settings
            settings = Settings()
            assert settings.interviewer_llm == "anthropic/claude-sonnet-4.5"
            assert settings.interviewer_temperature == 1.0
            assert settings.interviewer_max_tokens == 4000
            assert settings.session_timeout_seconds == 60
            assert settings.llm_timeout_seconds == 30
            assert settings.db_timeout_seconds == 10
            assert settings.langsmith_project == "FeedbackAI"

    def test_settings_missing_required_raises_error(self):
        """AC 3: Fehlende Pflicht-Variablen werfen ValidationError."""
        from pydantic import ValidationError
        from app.config.settings import Settings
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(ValidationError):
                Settings()


# -- DDD-Ordnerstruktur --

class TestDDDStructure:
    """AC 4 + AC 5 + AC 6: DDD Vertical Slices Ordnerstruktur."""

    BACKEND_APP = Path(__file__).resolve().parents[3] / "app"

    def test_interview_package_exists(self):
        """AC 4: interview/ Bounded Context existiert."""
        assert (self.BACKEND_APP / "interview" / "__init__.py").exists()

    def test_insights_package_exists(self):
        """AC 4: insights/ Bounded Context existiert."""
        assert (self.BACKEND_APP / "insights" / "__init__.py").exists()

    def test_config_package_exists(self):
        """AC 4: config/ Bounded Context existiert."""
        assert (self.BACKEND_APP / "config" / "__init__.py").exists()

    def test_db_package_exists(self):
        """AC 4: db/ Shared Infrastructure existiert."""
        assert (self.BACKEND_APP / "db" / "__init__.py").exists()

    def test_api_package_exists(self):
        """AC 4: api/ Transport Layer existiert."""
        assert (self.BACKEND_APP / "api" / "__init__.py").exists()

    def test_context_jsons_in_config(self):
        """AC 5: Context-JSONs liegen unter config/context/."""
        context_dir = self.BACKEND_APP / "config" / "context"
        assert (context_dir / "company.json").exists()
        assert (context_dir / "product.json").exists()
        assert (context_dir / "scenario_pain_point_discovery.json").exists()
        assert (context_dir / "scenario_satisfaction_research.json").exists()

    def test_old_graph_folder_removed(self):
        """AC 6: Alter graph/ Ordner existiert nicht mehr."""
        assert not (self.BACKEND_APP / "graph").exists()

    def test_old_context_folder_removed(self):
        """AC 6: Alter context/ Ordner existiert nicht mehr."""
        assert not (self.BACKEND_APP / "context").exists()

    def test_prompt_in_interview_package(self):
        """AC 7: prompt.py liegt unter interview/."""
        assert (self.BACKEND_APP / "interview" / "prompt.py").exists()


# -- CORS --

class TestCORS:
    """AC 10: CORS-Middleware ist aktiv."""

    def test_cors_allows_cross_origin(self, client: TestClient):
        response = client.options(
            "/health",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert "access-control-allow-origin" in response.headers


# -- Widget Cleanup --

class TestWidgetCleanup:
    """AC 8: Widget package.json bereinigt."""

    WIDGET_PKG = Path(__file__).resolve().parents[4] / "widget" / "package.json"

    def test_ai_sdk_removed(self):
        """AC 8: 'ai' nicht mehr in dependencies."""
        import json
        pkg = json.loads(self.WIDGET_PKG.read_text(encoding="utf-8"))
        deps = pkg.get("dependencies", {})
        assert "ai" not in deps
        assert "@ai-sdk/react" not in deps

    def test_assistant_ui_still_present(self):
        """AC 8: '@assistant-ui/react' ist weiterhin vorhanden."""
        import json
        pkg = json.loads(self.WIDGET_PKG.read_text(encoding="utf-8"))
        deps = pkg.get("dependencies", {})
        assert "@assistant-ui/react" in deps


# -- .env.example --

class TestEnvExample:
    """AC 9: .env.example aktualisiert."""

    ENV_EXAMPLE = Path(__file__).resolve().parents[4] / ".env.example"

    def test_supabase_url_present(self):
        content = self.ENV_EXAMPLE.read_text(encoding="utf-8")
        assert "SUPABASE_URL=" in content

    def test_supabase_key_present(self):
        content = self.ENV_EXAMPLE.read_text(encoding="utf-8")
        assert "SUPABASE_KEY=" in content

    def test_database_url_removed(self):
        content = self.ENV_EXAMPLE.read_text(encoding="utf-8")
        assert "DATABASE_URL=" not in content

    def test_timeout_vars_present(self):
        content = self.ENV_EXAMPLE.read_text(encoding="utf-8")
        assert "LLM_TIMEOUT_SECONDS=" in content
        assert "DB_TIMEOUT_SECONDS=" in content


# -- requirements.txt --

class TestRequirements:
    """AC 11: pydantic-settings in requirements.txt."""

    REQ_TXT = Path(__file__).resolve().parents[3] / "requirements.txt"

    def test_pydantic_settings_present(self):
        content = self.REQ_TXT.read_text(encoding="utf-8")
        assert "pydantic-settings" in content


# -- Fixtures --

@pytest.fixture
def client():
    """TestClient mit gemockten Settings (kein .env noetig)."""
    with patch.dict("os.environ", {
        "OPENROUTER_API_KEY": "test-key",
        "SUPABASE_URL": "https://test.supabase.co",
        "SUPABASE_KEY": "test-supabase-key",
    }, clear=False):
        from app.main import app
        with TestClient(app) as c:
            yield c

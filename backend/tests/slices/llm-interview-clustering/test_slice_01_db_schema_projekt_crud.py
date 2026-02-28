# backend/tests/slices/llm-interview-clustering/test_slice_01_db_schema_projekt_crud.py
"""Tests fuer Slice 1: DB Schema + Projekt CRUD.

Abgeleitet aus GIVEN/WHEN/THEN Acceptance Criteria in der Slice-Spec:
specs/phase-4/2026-02-28-llm-interview-clustering/slices/slice-01-db-schema-projekt-crud.md

Alle DB-Calls werden gemockt (mock_external Strategie).
Kein echter PostgreSQL-Zugriff in Unit-Tests.
"""
import asyncio
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException


# ============================================================
# FIXTURES
# ============================================================


@pytest.fixture
def mock_project_id() -> str:
    return str(uuid.UUID("550e8400-e29b-41d4-a716-446655440000"))


@pytest.fixture
def mock_user_id() -> str:
    return "00000000-0000-0000-0000-000000000001"


@pytest.fixture
def mock_project_row(mock_project_id, mock_user_id) -> dict:
    """Typischer DB-Row fuer ein Projekt."""
    now = datetime.now(timezone.utc)
    return {
        "id": uuid.UUID(mock_project_id),
        "user_id": uuid.UUID(mock_user_id),
        "name": "Onboarding UX Research",
        "research_goal": "Understand why users drop off during onboarding",
        "prompt_context": "B2B SaaS with 14-day free trial",
        "extraction_source": "summary",
        "model_interviewer": "anthropic/claude-sonnet-4",
        "model_extraction": "anthropic/claude-haiku-4",
        "model_clustering": "anthropic/claude-sonnet-4",
        "model_summary": "anthropic/claude-haiku-4",
        "created_at": now,
        "updated_at": now,
    }


@pytest.fixture
def mock_project_repository():
    """Gemocktes ProjectRepository."""
    repo = AsyncMock()
    return repo


@pytest.fixture
def mock_interview_assignment_repository():
    """Gemocktes InterviewAssignmentRepository."""
    repo = AsyncMock()
    return repo


def _run(coro):
    """Helper: fuehrt eine Coroutine synchron aus."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# ============================================================
# AC-1: Projekt erstellen
# ============================================================


class TestCreateProject:
    """AC-1: GIVEN ein neues Projekt mit name, research_goal und Standard-extraction_source
    WHEN POST /api/projects aufgerufen wird
    THEN wird ein Projekt in der DB angelegt und ProjectResponse mit id, allen Feldern,
    interview_count=0, cluster_count=0, fact_count=0, extraction_source_locked=false
    zurueckgegeben (HTTP 201)."""

    def test_ac1_create_project_returns_complete_response(
        self,
        mock_project_repository,
        mock_project_row,
        mock_user_id,
    ):
        """AC-1: GIVEN name + research_goal + Standard-extraction_source
        WHEN POST /api/projects
        THEN ProjectResponse mit id, allen Feldern, counts=0, locked=false (HTTP 201)."""
        mock_project_repository.create = AsyncMock(return_value=mock_project_row)
        mock_project_repository.get_fact_count = AsyncMock(return_value=0)

        from app.clustering.project_service import ProjectService
        from app.clustering.schemas import CreateProjectRequest

        service = ProjectService(repo=mock_project_repository)
        request = CreateProjectRequest(
            name="Onboarding UX Research",
            research_goal="Understand why users drop off during onboarding",
            prompt_context="B2B SaaS with 14-day free trial",
        )

        result = _run(service.create(request, user_id=mock_user_id))

        # ProjectResponse hat id
        assert result.id == uuid.UUID("550e8400-e29b-41d4-a716-446655440000")
        # Alle Felder korrekt
        assert result.name == "Onboarding UX Research"
        assert result.research_goal == "Understand why users drop off during onboarding"
        assert result.prompt_context == "B2B SaaS with 14-day free trial"
        assert result.extraction_source == "summary"
        # Model-Defaults
        assert result.model_interviewer == "anthropic/claude-sonnet-4"
        assert result.model_extraction == "anthropic/claude-haiku-4"
        assert result.model_clustering == "anthropic/claude-sonnet-4"
        assert result.model_summary == "anthropic/claude-haiku-4"
        # Zaehler alle 0
        assert result.interview_count == 0
        assert result.cluster_count == 0
        assert result.fact_count == 0
        # locked=false bei Neuanlage
        assert result.extraction_source_locked is False
        # Timestamps vorhanden
        assert result.created_at is not None
        assert result.updated_at is not None
        # DB-Call passiert
        mock_project_repository.create.assert_called_once()

    def test_ac1_create_project_validates_required_fields(self):
        """AC-1 (Validierung): GIVEN fehlendes research_goal
        WHEN CreateProjectRequest erstellt
        THEN ValidationError."""
        from pydantic import ValidationError

        from app.clustering.schemas import CreateProjectRequest

        with pytest.raises(ValidationError):
            CreateProjectRequest(name="Test")  # research_goal fehlt

    def test_ac1_create_project_validates_name_length(self):
        """AC-1 (Validierung): GIVEN name mit 201 Zeichen
        WHEN CreateProjectRequest erstellt
        THEN ValidationError."""
        from pydantic import ValidationError

        from app.clustering.schemas import CreateProjectRequest

        with pytest.raises(ValidationError):
            CreateProjectRequest(
                name="x" * 201,
                research_goal="Test goal",
            )

    def test_ac1_create_project_validates_research_goal_length(self):
        """AC-1 (Validierung): GIVEN research_goal mit 2001 Zeichen
        WHEN CreateProjectRequest erstellt
        THEN ValidationError."""
        from pydantic import ValidationError

        from app.clustering.schemas import CreateProjectRequest

        with pytest.raises(ValidationError):
            CreateProjectRequest(
                name="Test",
                research_goal="x" * 2001,
            )

    def test_ac1_create_project_default_extraction_source(self):
        """AC-1: GIVEN kein extraction_source angegeben
        WHEN CreateProjectRequest erstellt
        THEN default 'summary'."""
        from app.clustering.schemas import CreateProjectRequest

        request = CreateProjectRequest(
            name="Test",
            research_goal="Test goal",
        )
        assert request.extraction_source == "summary"

    def test_ac1_create_project_validates_extraction_source_enum(self):
        """AC-1 (Validierung): GIVEN ungueltiger extraction_source-Wert
        WHEN CreateProjectRequest erstellt
        THEN ValidationError."""
        from pydantic import ValidationError

        from app.clustering.schemas import CreateProjectRequest

        with pytest.raises(ValidationError):
            CreateProjectRequest(
                name="Test",
                research_goal="Test goal",
                extraction_source="invalid_value",
            )

    def test_ac1_create_project_accepts_transcript_source(self):
        """AC-1: GIVEN extraction_source='transcript'
        WHEN CreateProjectRequest erstellt
        THEN akzeptiert."""
        from app.clustering.schemas import CreateProjectRequest

        request = CreateProjectRequest(
            name="Test",
            research_goal="Test goal",
            extraction_source="transcript",
        )
        assert request.extraction_source == "transcript"

    def test_ac1_create_project_optional_prompt_context(self):
        """AC-1: GIVEN kein prompt_context
        WHEN CreateProjectRequest erstellt
        THEN prompt_context=None."""
        from app.clustering.schemas import CreateProjectRequest

        request = CreateProjectRequest(
            name="Test",
            research_goal="Test goal",
        )
        assert request.prompt_context is None


# ============================================================
# AC-2: Projekt lesen (einzeln)
# ============================================================


class TestGetProject:
    """AC-2: GIVEN ein existierendes Projekt
    WHEN GET /api/projects/{id} aufgerufen wird
    THEN werden alle Felder inkl. aggregierter Zaehler (interview_count, cluster_count,
    fact_count) korrekt zurueckgegeben (HTTP 200)."""

    def test_ac2_get_project_returns_all_fields_with_counts(
        self,
        mock_project_repository,
        mock_project_row,
        mock_project_id,
        mock_user_id,
    ):
        """AC-2: GIVEN existierendes Projekt
        WHEN GET /api/projects/{id}
        THEN alle Felder inkl. aggregierter Zaehler korrekt zurueckgegeben."""
        mock_project_repository.get_by_id = AsyncMock(return_value=mock_project_row)
        mock_project_repository.get_interview_count = AsyncMock(return_value=3)
        mock_project_repository.get_cluster_count = AsyncMock(return_value=2)
        mock_project_repository.get_fact_count = AsyncMock(return_value=7)

        from app.clustering.project_service import ProjectService

        service = ProjectService(repo=mock_project_repository)

        result = _run(service.get(project_id=mock_project_id, user_id=mock_user_id))

        # Alle Felder pruefen
        assert result.id == uuid.UUID(mock_project_id)
        assert result.name == "Onboarding UX Research"
        assert result.research_goal == "Understand why users drop off during onboarding"
        assert result.prompt_context == "B2B SaaS with 14-day free trial"
        assert result.extraction_source == "summary"
        assert result.model_interviewer == "anthropic/claude-sonnet-4"
        assert result.model_extraction == "anthropic/claude-haiku-4"
        assert result.model_clustering == "anthropic/claude-sonnet-4"
        assert result.model_summary == "anthropic/claude-haiku-4"
        assert result.created_at is not None
        assert result.updated_at is not None
        # Aggregierte Zaehler
        assert result.interview_count == 3
        assert result.cluster_count == 2
        assert result.fact_count == 7

    def test_ac2_extraction_source_locked_when_facts_exist(
        self,
        mock_project_repository,
        mock_project_row,
        mock_project_id,
        mock_user_id,
    ):
        """AC-2 (Ableitung): GIVEN Projekt mit fact_count > 0
        WHEN GET /api/projects/{id}
        THEN extraction_source_locked = True."""
        mock_project_repository.get_by_id = AsyncMock(return_value=mock_project_row)
        mock_project_repository.get_interview_count = AsyncMock(return_value=1)
        mock_project_repository.get_cluster_count = AsyncMock(return_value=0)
        mock_project_repository.get_fact_count = AsyncMock(return_value=5)

        from app.clustering.project_service import ProjectService

        service = ProjectService(repo=mock_project_repository)

        result = _run(service.get(project_id=mock_project_id, user_id=mock_user_id))

        assert result.extraction_source_locked is True

    def test_ac2_extraction_source_unlocked_when_no_facts(
        self,
        mock_project_repository,
        mock_project_row,
        mock_project_id,
        mock_user_id,
    ):
        """AC-2 (Ableitung): GIVEN Projekt mit fact_count == 0
        WHEN GET /api/projects/{id}
        THEN extraction_source_locked = False."""
        mock_project_repository.get_by_id = AsyncMock(return_value=mock_project_row)
        mock_project_repository.get_interview_count = AsyncMock(return_value=2)
        mock_project_repository.get_cluster_count = AsyncMock(return_value=1)
        mock_project_repository.get_fact_count = AsyncMock(return_value=0)

        from app.clustering.project_service import ProjectService

        service = ProjectService(repo=mock_project_repository)

        result = _run(service.get(project_id=mock_project_id, user_id=mock_user_id))

        assert result.extraction_source_locked is False


# ============================================================
# AC-3: Projekte auflisten
# ============================================================


class TestListProjects:
    """AC-3: GIVEN mehrere Projekte des Users
    WHEN GET /api/projects aufgerufen wird
    THEN werden alle Projekte als list[ProjectListItem] sortiert nach updated_at
    absteigend zurueckgegeben."""

    def test_ac3_list_projects_sorted_by_updated_at_desc(
        self,
        mock_project_repository,
        mock_user_id,
    ):
        """AC-3: GIVEN mehrere Projekte
        WHEN GET /api/projects
        THEN sortiert nach updated_at desc als list[ProjectListItem]."""
        now = datetime.now(timezone.utc)
        project_rows = [
            {
                "id": uuid.uuid4(),
                "name": "Neueres Projekt",
                "interview_count": 0,
                "cluster_count": 0,
                "updated_at": now,
            },
            {
                "id": uuid.uuid4(),
                "name": "Aelteres Projekt",
                "interview_count": 2,
                "cluster_count": 1,
                "updated_at": now - timedelta(hours=2),
            },
        ]
        mock_project_repository.list_by_user = AsyncMock(return_value=project_rows)

        from app.clustering.project_service import ProjectService

        service = ProjectService(repo=mock_project_repository)

        results = _run(service.list(user_id=mock_user_id))

        assert len(results) == 2
        assert results[0].name == "Neueres Projekt"
        assert results[1].name == "Aelteres Projekt"
        # Sortierung: neueres zuerst
        assert results[0].updated_at > results[1].updated_at

    def test_ac3_list_projects_returns_project_list_item_fields(
        self,
        mock_project_repository,
        mock_user_id,
    ):
        """AC-3: GIVEN existierende Projekte
        WHEN GET /api/projects
        THEN ProjectListItem hat id, name, interview_count, cluster_count, updated_at."""
        now = datetime.now(timezone.utc)
        project_id = uuid.uuid4()
        project_rows = [
            {
                "id": project_id,
                "name": "Test Projekt",
                "interview_count": 5,
                "cluster_count": 3,
                "updated_at": now,
            },
        ]
        mock_project_repository.list_by_user = AsyncMock(return_value=project_rows)

        from app.clustering.project_service import ProjectService

        service = ProjectService(repo=mock_project_repository)

        results = _run(service.list(user_id=mock_user_id))

        assert len(results) == 1
        item = results[0]
        assert item.id == project_id
        assert item.name == "Test Projekt"
        assert item.interview_count == 5
        assert item.cluster_count == 3
        assert item.updated_at == now

    def test_ac3_list_projects_empty_returns_empty_list(
        self,
        mock_project_repository,
        mock_user_id,
    ):
        """AC-3: GIVEN keine Projekte
        WHEN GET /api/projects
        THEN leere Liste."""
        mock_project_repository.list_by_user = AsyncMock(return_value=[])

        from app.clustering.project_service import ProjectService

        service = ProjectService(repo=mock_project_repository)

        results = _run(service.list(user_id=mock_user_id))

        assert results == []


# ============================================================
# AC-4: Projekt aktualisieren (PATCH-Semantik via PUT)
# ============================================================


class TestUpdateProject:
    """AC-4: GIVEN ein Projekt mit veraenderbaren Feldern (name, research_goal, prompt_context)
    WHEN PUT /api/projects/{id} mit teilweisen Aenderungen aufgerufen wird
    THEN werden nur die gesendeten Felder aktualisiert, updated_at wird gesetzt,
    unveraenderte Felder bleiben unveraendert (HTTP 200)."""

    def test_ac4_update_project_partial_fields_only_name(
        self,
        mock_project_repository,
        mock_project_row,
        mock_project_id,
        mock_user_id,
    ):
        """AC-4: GIVEN nur name im Request
        WHEN PUT /api/projects/{id}
        THEN nur name geaendert, andere Felder unveraendert."""
        updated_row = {**mock_project_row, "name": "Neuer Name"}
        mock_project_repository.update = AsyncMock(return_value=updated_row)
        mock_project_repository.get_fact_count = AsyncMock(return_value=0)
        mock_project_repository.get_interview_count = AsyncMock(return_value=0)
        mock_project_repository.get_cluster_count = AsyncMock(return_value=0)

        from app.clustering.project_service import ProjectService
        from app.clustering.schemas import UpdateProjectRequest

        service = ProjectService(repo=mock_project_repository)
        request = UpdateProjectRequest(name="Neuer Name")

        result = _run(
            service.update(
                project_id=mock_project_id,
                user_id=mock_user_id,
                request=request,
            )
        )

        assert result.name == "Neuer Name"
        # Unveraenderte Felder
        assert result.research_goal == mock_project_row["research_goal"]
        assert result.prompt_context == mock_project_row["prompt_context"]
        assert result.extraction_source == mock_project_row["extraction_source"]

    def test_ac4_update_project_partial_fields_only_research_goal(
        self,
        mock_project_repository,
        mock_project_row,
        mock_project_id,
        mock_user_id,
    ):
        """AC-4: GIVEN nur research_goal im Request
        WHEN PUT /api/projects/{id}
        THEN nur research_goal geaendert, andere Felder unveraendert."""
        updated_row = {**mock_project_row, "research_goal": "Neues Ziel"}
        mock_project_repository.update = AsyncMock(return_value=updated_row)
        mock_project_repository.get_fact_count = AsyncMock(return_value=0)
        mock_project_repository.get_interview_count = AsyncMock(return_value=0)
        mock_project_repository.get_cluster_count = AsyncMock(return_value=0)

        from app.clustering.project_service import ProjectService
        from app.clustering.schemas import UpdateProjectRequest

        service = ProjectService(repo=mock_project_repository)
        request = UpdateProjectRequest(research_goal="Neues Ziel")

        result = _run(
            service.update(
                project_id=mock_project_id,
                user_id=mock_user_id,
                request=request,
            )
        )

        assert result.research_goal == "Neues Ziel"
        assert result.name == mock_project_row["name"]  # unveraendert

    def test_ac4_update_project_not_found_raises_404(
        self,
        mock_project_repository,
        mock_project_id,
        mock_user_id,
    ):
        """AC-4 (Fehlerfall): GIVEN nicht-existierendes Projekt
        WHEN PUT /api/projects/{id}
        THEN HTTP 404."""
        mock_project_repository.update = AsyncMock(return_value=None)

        from app.clustering.project_service import ProjectService
        from app.clustering.schemas import UpdateProjectRequest

        service = ProjectService(repo=mock_project_repository)
        request = UpdateProjectRequest(name="Neuer Name")

        with pytest.raises(HTTPException) as exc_info:
            _run(
                service.update(
                    project_id=mock_project_id,
                    user_id=mock_user_id,
                    request=request,
                )
            )
        assert exc_info.value.status_code == 404

    def test_ac4_update_project_request_all_fields_optional(self):
        """AC-4 (Validierung): UpdateProjectRequest erlaubt alle Felder als None (PATCH-Semantik)."""
        from app.clustering.schemas import UpdateProjectRequest

        request = UpdateProjectRequest()
        assert request.name is None
        assert request.research_goal is None
        assert request.prompt_context is None


# ============================================================
# AC-5: Extraction-Source aendern
# ============================================================


class TestChangeExtractionSource:
    """AC-5: GIVEN ein Projekt ohne zugeordnete Facts
    WHEN PUT /api/projects/{id}/extraction-source mit neuer extraction_source aufgerufen wird
    THEN wird die neue Source gespeichert, extraction_source_locked=false bleibt erhalten
    (HTTP 200)."""

    def test_ac5_change_extraction_source_without_facts(
        self,
        mock_project_repository,
        mock_project_row,
        mock_project_id,
        mock_user_id,
    ):
        """AC-5: GIVEN Projekt ohne Facts
        WHEN PUT /api/projects/{id}/extraction-source mit 'transcript'
        THEN neue Source gespeichert, extraction_source_locked=False."""
        updated_row = {**mock_project_row, "extraction_source": "transcript"}
        mock_project_repository.update = AsyncMock(return_value=updated_row)
        mock_project_repository.get_fact_count = AsyncMock(return_value=0)
        mock_project_repository.get_interview_count = AsyncMock(return_value=0)
        mock_project_repository.get_cluster_count = AsyncMock(return_value=0)

        from app.clustering.project_service import ProjectService
        from app.clustering.schemas import ChangeSourceRequest

        service = ProjectService(repo=mock_project_repository)
        request = ChangeSourceRequest(extraction_source="transcript", re_extract=False)

        result = _run(
            service.change_extraction_source(
                project_id=mock_project_id,
                user_id=mock_user_id,
                request=request,
            )
        )

        assert result.extraction_source == "transcript"
        assert result.extraction_source_locked is False

    def test_ac5_change_extraction_source_to_summary(
        self,
        mock_project_repository,
        mock_project_row,
        mock_project_id,
        mock_user_id,
    ):
        """AC-5: GIVEN Projekt mit extraction_source='transcript' ohne Facts
        WHEN PUT /api/projects/{id}/extraction-source mit 'summary'
        THEN Source auf 'summary' geaendert."""
        updated_row = {**mock_project_row, "extraction_source": "summary"}
        mock_project_repository.update = AsyncMock(return_value=updated_row)
        mock_project_repository.get_fact_count = AsyncMock(return_value=0)
        mock_project_repository.get_interview_count = AsyncMock(return_value=0)
        mock_project_repository.get_cluster_count = AsyncMock(return_value=0)

        from app.clustering.project_service import ProjectService
        from app.clustering.schemas import ChangeSourceRequest

        service = ProjectService(repo=mock_project_repository)
        request = ChangeSourceRequest(extraction_source="summary", re_extract=False)

        result = _run(
            service.change_extraction_source(
                project_id=mock_project_id,
                user_id=mock_user_id,
                request=request,
            )
        )

        assert result.extraction_source == "summary"

    def test_ac5_change_extraction_source_not_found_raises_404(
        self,
        mock_project_repository,
        mock_project_id,
        mock_user_id,
    ):
        """AC-5 (Fehlerfall): GIVEN nicht-existierendes Projekt
        WHEN PUT /api/projects/{id}/extraction-source
        THEN HTTP 404."""
        mock_project_repository.update = AsyncMock(return_value=None)

        from app.clustering.project_service import ProjectService
        from app.clustering.schemas import ChangeSourceRequest

        service = ProjectService(repo=mock_project_repository)
        request = ChangeSourceRequest(extraction_source="transcript", re_extract=False)

        with pytest.raises(HTTPException) as exc_info:
            _run(
                service.change_extraction_source(
                    project_id=mock_project_id,
                    user_id=mock_user_id,
                    request=request,
                )
            )
        assert exc_info.value.status_code == 404

    def test_ac5_change_source_request_validates_enum(self):
        """AC-5 (Validierung): GIVEN ungueltiger extraction_source-Wert
        WHEN ChangeSourceRequest erstellt
        THEN ValidationError."""
        from pydantic import ValidationError

        from app.clustering.schemas import ChangeSourceRequest

        with pytest.raises(ValidationError):
            ChangeSourceRequest(extraction_source="invalid_source", re_extract=False)

    def test_ac5_change_source_request_re_extract_defaults_false(self):
        """AC-5 (Validierung): GIVEN kein re_extract angegeben
        WHEN ChangeSourceRequest erstellt
        THEN re_extract=False."""
        from app.clustering.schemas import ChangeSourceRequest

        request = ChangeSourceRequest(extraction_source="summary")
        assert request.re_extract is False


# ============================================================
# AC-6: Projekt loeschen
# ============================================================


class TestDeleteProject:
    """AC-6: GIVEN ein Projekt das dem aktuellen User gehoert
    WHEN DELETE /api/projects/{id} aufgerufen wird
    THEN wird das Projekt und alle zugehoerigen Daten (project_interviews, clusters,
    facts, cluster_suggestions) geloescht (HTTP 204)."""

    def test_ac6_delete_project_calls_repository(
        self,
        mock_project_repository,
        mock_project_id,
        mock_user_id,
    ):
        """AC-6: GIVEN existierendes Projekt
        WHEN DELETE /api/projects/{id}
        THEN repository.delete() aufgerufen mit project_id und user_id."""
        mock_project_repository.delete = AsyncMock(return_value=True)

        from app.clustering.project_service import ProjectService

        service = ProjectService(repo=mock_project_repository)

        _run(service.delete(project_id=mock_project_id, user_id=mock_user_id))

        mock_project_repository.delete.assert_called_once_with(
            project_id=mock_project_id,
            user_id=mock_user_id,
        )

    def test_ac6_delete_nonexistent_project_raises_404(
        self,
        mock_project_repository,
        mock_project_id,
        mock_user_id,
    ):
        """AC-6 (Fehlerfall): GIVEN nicht-existierendes Projekt
        WHEN DELETE /api/projects/{id}
        THEN HTTP 404 mit 'Project not found'."""
        mock_project_repository.delete = AsyncMock(return_value=False)

        from app.clustering.project_service import ProjectService

        service = ProjectService(repo=mock_project_repository)

        with pytest.raises(HTTPException) as exc_info:
            _run(service.delete(project_id=mock_project_id, user_id=mock_user_id))
        assert exc_info.value.status_code == 404
        assert exc_info.value.detail == "Project not found"

    def test_ac6_delete_project_returns_none(
        self,
        mock_project_repository,
        mock_project_id,
        mock_user_id,
    ):
        """AC-6: GIVEN existierendes Projekt
        WHEN DELETE
        THEN service.delete() gibt None zurueck (kein Response-Body, HTTP 204)."""
        mock_project_repository.delete = AsyncMock(return_value=True)

        from app.clustering.project_service import ProjectService

        service = ProjectService(repo=mock_project_repository)

        result = _run(service.delete(project_id=mock_project_id, user_id=mock_user_id))

        assert result is None


# ============================================================
# AC-7: Projekt nicht gefunden (404)
# ============================================================


class TestProjectNotFound:
    """AC-7: GIVEN ein nicht-existierendes Projekt
    WHEN GET /api/projects/{id} aufgerufen wird
    THEN wird HTTP 404 mit {"detail": "Project not found"} zurueckgegeben."""

    def test_ac7_get_project_not_found_raises_404(
        self,
        mock_project_repository,
        mock_project_id,
        mock_user_id,
    ):
        """AC-7: GIVEN nicht-existierendes Projekt
        WHEN GET /api/projects/{id}
        THEN HTTP 404."""
        mock_project_repository.get_by_id = AsyncMock(return_value=None)

        from app.clustering.project_service import ProjectService

        service = ProjectService(repo=mock_project_repository)

        with pytest.raises(HTTPException) as exc_info:
            _run(service.get(project_id=mock_project_id, user_id=mock_user_id))
        assert exc_info.value.status_code == 404

    def test_ac7_get_project_not_found_detail_message(
        self,
        mock_project_repository,
        mock_project_id,
        mock_user_id,
    ):
        """AC-7: GIVEN nicht-existierendes Projekt
        WHEN GET /api/projects/{id}
        THEN detail = 'Project not found'."""
        mock_project_repository.get_by_id = AsyncMock(return_value=None)

        from app.clustering.project_service import ProjectService

        service = ProjectService(repo=mock_project_repository)

        with pytest.raises(HTTPException) as exc_info:
            _run(service.get(project_id=mock_project_id, user_id=mock_user_id))
        assert exc_info.value.detail == "Project not found"


# ============================================================
# AC-8: Verfuegbare Interviews auflisten
# ============================================================


class TestListAvailableInterviews:
    """AC-8: GIVEN verfuegbare Interviews in mvp_interviews die noch keinem Projekt
    zugeordnet sind
    WHEN GET /api/projects/{id}/interviews/available aufgerufen wird
    THEN werden diese Interviews als list[AvailableInterview] zurueckgegeben."""

    def test_ac8_list_available_returns_unassigned_interviews(
        self,
        mock_interview_assignment_repository,
    ):
        """AC-8: GIVEN verfuegbare Interviews
        WHEN GET /api/projects/{id}/interviews/available
        THEN list[AvailableInterview] zurueckgegeben."""
        now = datetime.now(timezone.utc)
        session_id = uuid.uuid4()
        mock_interview_assignment_repository.list_available = AsyncMock(
            return_value=[
                {
                    "session_id": session_id,
                    "created_at": now,
                    "summary_preview": "Unassigned interview summary...",
                },
            ]
        )

        from app.clustering.interview_assignment_service import InterviewAssignmentService

        service = InterviewAssignmentService(repo=mock_interview_assignment_repository)

        results = _run(
            service.list_available(user_id="00000000-0000-0000-0000-000000000001")
        )

        assert len(results) == 1
        # Alle AvailableInterview-Felder pruefen
        assert results[0].session_id == session_id
        assert results[0].created_at == now
        assert results[0].summary_preview == "Unassigned interview summary..."

    def test_ac8_list_available_returns_empty_when_all_assigned(
        self,
        mock_interview_assignment_repository,
    ):
        """AC-8: GIVEN keine verfuegbaren Interviews (alle zugeordnet)
        WHEN GET /api/projects/{id}/interviews/available
        THEN leere Liste."""
        mock_interview_assignment_repository.list_available = AsyncMock(
            return_value=[]
        )

        from app.clustering.interview_assignment_service import InterviewAssignmentService

        service = InterviewAssignmentService(repo=mock_interview_assignment_repository)

        results = _run(
            service.list_available(user_id="00000000-0000-0000-0000-000000000001")
        )

        assert results == []

    def test_ac8_list_available_returns_multiple_interviews(
        self,
        mock_interview_assignment_repository,
    ):
        """AC-8: GIVEN mehrere verfuegbare Interviews
        WHEN GET /api/projects/{id}/interviews/available
        THEN alle zurueckgegeben."""
        now = datetime.now(timezone.utc)
        mock_interview_assignment_repository.list_available = AsyncMock(
            return_value=[
                {
                    "session_id": uuid.uuid4(),
                    "created_at": now,
                    "summary_preview": "Interview A...",
                },
                {
                    "session_id": uuid.uuid4(),
                    "created_at": now - timedelta(hours=1),
                    "summary_preview": "Interview B...",
                },
                {
                    "session_id": uuid.uuid4(),
                    "created_at": now - timedelta(hours=2),
                    "summary_preview": None,
                },
            ]
        )

        from app.clustering.interview_assignment_service import InterviewAssignmentService

        service = InterviewAssignmentService(repo=mock_interview_assignment_repository)

        results = _run(
            service.list_available(user_id="00000000-0000-0000-0000-000000000001")
        )

        assert len(results) == 3
        assert results[2].summary_preview is None  # nullable


# ============================================================
# AC-9: Interview-Zuordnung
# ============================================================


class TestAssignInterviews:
    """AC-9: GIVEN eine Liste von interview_ids aus mvp_interviews
    WHEN POST /api/projects/{id}/interviews aufgerufen wird
    THEN werden die Interviews dem Projekt zugeordnet (Zeilen in project_interviews
    mit extraction_status=pending, clustering_status=pending) und als
    list[InterviewAssignment] zurueckgegeben (HTTP 201)."""

    def test_ac9_assign_interviews_creates_rows_with_pending_status(
        self,
        mock_interview_assignment_repository,
        mock_project_id,
    ):
        """AC-9: GIVEN gueltige interview_ids
        WHEN POST /api/projects/{id}/interviews
        THEN project_interviews Zeilen mit extraction_status=pending,
        clustering_status=pending und list[InterviewAssignment] zurueckgegeben."""
        interview_id_1 = uuid.uuid4()
        interview_id_2 = uuid.uuid4()
        now = datetime.now(timezone.utc)

        mock_interview_assignment_repository.assign_interviews = AsyncMock(
            return_value=[
                {
                    "interview_id": interview_id_1,
                    "date": now,
                    "summary_preview": "User had issues with navigation...",
                    "fact_count": 0,
                    "extraction_status": "pending",
                    "clustering_status": "pending",
                },
                {
                    "interview_id": interview_id_2,
                    "date": now - timedelta(hours=1),
                    "summary_preview": "Pricing was confusing...",
                    "fact_count": 0,
                    "extraction_status": "pending",
                    "clustering_status": "pending",
                },
            ]
        )

        from app.clustering.interview_assignment_service import InterviewAssignmentService
        from app.clustering.schemas import AssignRequest

        service = InterviewAssignmentService(repo=mock_interview_assignment_repository)
        request = AssignRequest(interview_ids=[interview_id_1, interview_id_2])

        results = _run(service.assign(project_id=mock_project_id, request=request))

        assert len(results) == 2
        # Alle InterviewAssignment-Felder pruefen
        assert results[0].interview_id == interview_id_1
        assert results[0].date == now
        assert results[0].summary_preview == "User had issues with navigation..."
        assert results[0].fact_count == 0
        assert results[0].extraction_status == "pending"
        assert results[0].clustering_status == "pending"
        # Zweites Interview
        assert results[1].interview_id == interview_id_2
        assert results[1].extraction_status == "pending"
        assert results[1].clustering_status == "pending"

    def test_ac9_assign_interviews_calls_repository(
        self,
        mock_interview_assignment_repository,
        mock_project_id,
    ):
        """AC-9: GIVEN interview_ids
        WHEN POST /api/projects/{id}/interviews
        THEN repository.assign_interviews aufgerufen mit korrekten Parametern."""
        interview_id = uuid.uuid4()
        now = datetime.now(timezone.utc)

        mock_interview_assignment_repository.assign_interviews = AsyncMock(
            return_value=[
                {
                    "interview_id": interview_id,
                    "date": now,
                    "summary_preview": "Test...",
                    "fact_count": 0,
                    "extraction_status": "pending",
                    "clustering_status": "pending",
                },
            ]
        )

        from app.clustering.interview_assignment_service import InterviewAssignmentService
        from app.clustering.schemas import AssignRequest

        service = InterviewAssignmentService(repo=mock_interview_assignment_repository)
        request = AssignRequest(interview_ids=[interview_id])

        _run(service.assign(project_id=mock_project_id, request=request))

        mock_interview_assignment_repository.assign_interviews.assert_called_once_with(
            project_id=mock_project_id,
            interview_ids=[str(interview_id)],
        )

    def test_ac9_assign_request_requires_at_least_one_id(self):
        """AC-9 (Validierung): GIVEN leere interview_ids
        WHEN AssignRequest erstellt
        THEN ValidationError (min_length=1)."""
        from pydantic import ValidationError

        from app.clustering.schemas import AssignRequest

        with pytest.raises(ValidationError):
            AssignRequest(interview_ids=[])


# ============================================================
# AC-10: Interview bereits zugeordnet (409)
# ============================================================


class TestAssignInterviewConflict:
    """AC-10: GIVEN ein Interview das bereits einem anderen Projekt zugeordnet ist
    WHEN POST /api/projects/{id}/interviews mit dieser interview_id aufgerufen wird
    THEN wird HTTP 409 mit Fehlerdetail zurueckgegeben und kein Datensatz angelegt."""

    def test_ac10_assign_already_assigned_interview_raises_409(
        self,
        mock_interview_assignment_repository,
        mock_project_id,
    ):
        """AC-10: GIVEN bereits zugeordnetes Interview
        WHEN POST /api/projects/{id}/interviews
        THEN HTTP 409."""
        conflicting_id = uuid.uuid4()
        mock_interview_assignment_repository.assign_interviews = AsyncMock(
            side_effect=HTTPException(
                status_code=409,
                detail=f"Interview {conflicting_id} already assigned to another project",
            )
        )

        from app.clustering.interview_assignment_service import InterviewAssignmentService
        from app.clustering.schemas import AssignRequest

        service = InterviewAssignmentService(repo=mock_interview_assignment_repository)
        request = AssignRequest(interview_ids=[conflicting_id])

        with pytest.raises(HTTPException) as exc_info:
            _run(service.assign(project_id=mock_project_id, request=request))
        assert exc_info.value.status_code == 409

    def test_ac10_409_error_contains_interview_id_in_detail(
        self,
        mock_interview_assignment_repository,
        mock_project_id,
    ):
        """AC-10: GIVEN bereits zugeordnetes Interview
        WHEN POST /api/projects/{id}/interviews
        THEN Fehlerdetail enthaelt Interview-ID."""
        conflicting_id = uuid.uuid4()
        mock_interview_assignment_repository.assign_interviews = AsyncMock(
            side_effect=HTTPException(
                status_code=409,
                detail=f"Interview {conflicting_id} already assigned to another project",
            )
        )

        from app.clustering.interview_assignment_service import InterviewAssignmentService
        from app.clustering.schemas import AssignRequest

        service = InterviewAssignmentService(repo=mock_interview_assignment_repository)
        request = AssignRequest(interview_ids=[conflicting_id])

        with pytest.raises(HTTPException) as exc_info:
            _run(service.assign(project_id=mock_project_id, request=request))
        assert str(conflicting_id) in exc_info.value.detail
        assert "already assigned" in exc_info.value.detail


# ============================================================
# Zusaetzliche Unit-Tests: Schema-Validierung
# ============================================================


class TestSchemaValidation:
    """Unit-Tests fuer Pydantic Schema-Validierung."""

    def test_project_response_schema_has_all_required_fields(self):
        """ProjectResponse hat alle Felder aus der Spec."""
        from app.clustering.schemas import ProjectResponse

        now = datetime.now(timezone.utc)
        response = ProjectResponse(
            id=uuid.uuid4(),
            name="Test",
            research_goal="Test goal",
            prompt_context=None,
            extraction_source="summary",
            extraction_source_locked=False,
            model_interviewer="anthropic/claude-sonnet-4",
            model_extraction="anthropic/claude-haiku-4",
            model_clustering="anthropic/claude-sonnet-4",
            model_summary="anthropic/claude-haiku-4",
            interview_count=0,
            cluster_count=0,
            fact_count=0,
            created_at=now,
            updated_at=now,
        )
        assert response.id is not None
        assert response.extraction_source_locked is False

    def test_project_list_item_schema_has_all_required_fields(self):
        """ProjectListItem hat id, name, interview_count, cluster_count, updated_at."""
        from app.clustering.schemas import ProjectListItem

        now = datetime.now(timezone.utc)
        item = ProjectListItem(
            id=uuid.uuid4(),
            name="Test",
            interview_count=5,
            cluster_count=3,
            updated_at=now,
        )
        assert item.interview_count == 5
        assert item.cluster_count == 3

    def test_interview_assignment_schema_has_all_required_fields(self):
        """InterviewAssignment hat interview_id, date, summary_preview, fact_count,
        extraction_status, clustering_status."""
        from app.clustering.schemas import InterviewAssignment

        now = datetime.now(timezone.utc)
        assignment = InterviewAssignment(
            interview_id=uuid.uuid4(),
            date=now,
            summary_preview="Test...",
            fact_count=0,
            extraction_status="pending",
            clustering_status="pending",
        )
        assert assignment.extraction_status == "pending"
        assert assignment.clustering_status == "pending"
        assert assignment.fact_count == 0

    def test_available_interview_schema_has_all_required_fields(self):
        """AvailableInterview hat session_id, created_at, summary_preview."""
        from app.clustering.schemas import AvailableInterview

        now = datetime.now(timezone.utc)
        available = AvailableInterview(
            session_id=uuid.uuid4(),
            created_at=now,
            summary_preview=None,
        )
        assert available.summary_preview is None

    def test_update_models_request_all_fields_optional(self):
        """UpdateModelsRequest erlaubt alle Felder als None."""
        from app.clustering.schemas import UpdateModelsRequest

        request = UpdateModelsRequest()
        assert request.model_interviewer is None
        assert request.model_extraction is None
        assert request.model_clustering is None
        assert request.model_summary is None

    def test_update_models_request_partial_fields(self):
        """UpdateModelsRequest akzeptiert nur teilweise Felder."""
        from app.clustering.schemas import UpdateModelsRequest

        request = UpdateModelsRequest(model_interviewer="openai/gpt-4o")
        assert request.model_interviewer == "openai/gpt-4o"
        assert request.model_extraction is None


# ============================================================
# Zusaetzliche Unit-Tests: UpdateModels Service
# ============================================================


class TestUpdateModels:
    """PUT /api/projects/{id}/models aktualisiert model_* Felder."""

    def test_update_models_changes_model_fields(
        self,
        mock_project_repository,
        mock_project_row,
        mock_project_id,
        mock_user_id,
    ):
        """GIVEN neue model_* Werte
        WHEN update_models aufgerufen
        THEN Model-Felder geaendert."""
        updated_row = {
            **mock_project_row,
            "model_interviewer": "openai/gpt-4o",
        }
        mock_project_repository.update = AsyncMock(return_value=updated_row)
        mock_project_repository.get_fact_count = AsyncMock(return_value=0)
        mock_project_repository.get_interview_count = AsyncMock(return_value=0)
        mock_project_repository.get_cluster_count = AsyncMock(return_value=0)

        from app.clustering.project_service import ProjectService
        from app.clustering.schemas import UpdateModelsRequest

        service = ProjectService(repo=mock_project_repository)
        request = UpdateModelsRequest(model_interviewer="openai/gpt-4o")

        result = _run(
            service.update_models(
                project_id=mock_project_id,
                user_id=mock_user_id,
                request=request,
            )
        )

        assert result.model_interviewer == "openai/gpt-4o"

    def test_update_models_not_found_raises_404(
        self,
        mock_project_repository,
        mock_project_id,
        mock_user_id,
    ):
        """GIVEN nicht-existierendes Projekt
        WHEN update_models aufgerufen
        THEN HTTP 404."""
        mock_project_repository.update = AsyncMock(return_value=None)

        from app.clustering.project_service import ProjectService
        from app.clustering.schemas import UpdateModelsRequest

        service = ProjectService(repo=mock_project_repository)
        request = UpdateModelsRequest(model_interviewer="openai/gpt-4o")

        with pytest.raises(HTTPException) as exc_info:
            _run(
                service.update_models(
                    project_id=mock_project_id,
                    user_id=mock_user_id,
                    request=request,
                )
            )
        assert exc_info.value.status_code == 404


# ============================================================
# Zusaetzliche Unit-Tests: ListAssigned Interviews
# ============================================================


class TestListAssignedInterviews:
    """GET /api/projects/{id}/interviews listet zugeordnete Interviews."""

    def test_list_assigned_returns_interview_assignments(
        self,
        mock_interview_assignment_repository,
        mock_project_id,
    ):
        """GIVEN zugeordnete Interviews
        WHEN list_assigned aufgerufen
        THEN list[InterviewAssignment] zurueckgegeben."""
        now = datetime.now(timezone.utc)
        interview_id = uuid.uuid4()
        mock_interview_assignment_repository.list_assigned = AsyncMock(
            return_value=[
                {
                    "interview_id": interview_id,
                    "date": now,
                    "summary_preview": "Test interview...",
                    "fact_count": 3,
                    "extraction_status": "completed",
                    "clustering_status": "pending",
                },
            ]
        )

        from app.clustering.interview_assignment_service import InterviewAssignmentService

        service = InterviewAssignmentService(repo=mock_interview_assignment_repository)

        results = _run(service.list_assigned(project_id=mock_project_id))

        assert len(results) == 1
        assert results[0].interview_id == interview_id
        assert results[0].fact_count == 3
        assert results[0].extraction_status == "completed"
        assert results[0].clustering_status == "pending"
        assert results[0].summary_preview == "Test interview..."

    def test_list_assigned_returns_empty_for_no_interviews(
        self,
        mock_interview_assignment_repository,
        mock_project_id,
    ):
        """GIVEN keine zugeordneten Interviews
        WHEN list_assigned aufgerufen
        THEN leere Liste."""
        mock_interview_assignment_repository.list_assigned = AsyncMock(return_value=[])

        from app.clustering.interview_assignment_service import InterviewAssignmentService

        service = InterviewAssignmentService(repo=mock_interview_assignment_repository)

        results = _run(service.list_assigned(project_id=mock_project_id))

        assert results == []


# ============================================================
# Zusaetzliche Unit-Tests: DB-Schema / Migration
# ============================================================


class TestDBMigration:
    """Prueft, dass das Migration-Script existiert und alle Tabellen definiert."""

    MIGRATION_FILE = (
        Path(__file__).resolve().parents[3] / "migrations" / "002_create_clustering_tables.sql"
    )

    def test_migration_file_exists(self):
        """Migration-Script existiert."""
        assert self.MIGRATION_FILE.exists(), (
            f"Migration file not found: {self.MIGRATION_FILE}"
        )

    def test_migration_creates_users_table(self):
        """Migration erstellt users Tabelle."""
        content = self.MIGRATION_FILE.read_text(encoding="utf-8")
        assert "CREATE TABLE IF NOT EXISTS users" in content

    def test_migration_creates_projects_table(self):
        """Migration erstellt projects Tabelle."""
        content = self.MIGRATION_FILE.read_text(encoding="utf-8")
        assert "CREATE TABLE IF NOT EXISTS projects" in content

    def test_migration_creates_project_interviews_table(self):
        """Migration erstellt project_interviews Tabelle."""
        content = self.MIGRATION_FILE.read_text(encoding="utf-8")
        assert "CREATE TABLE IF NOT EXISTS project_interviews" in content

    def test_migration_creates_clusters_table(self):
        """Migration erstellt clusters Tabelle."""
        content = self.MIGRATION_FILE.read_text(encoding="utf-8")
        assert "CREATE TABLE IF NOT EXISTS clusters" in content

    def test_migration_creates_facts_table(self):
        """Migration erstellt facts Tabelle."""
        content = self.MIGRATION_FILE.read_text(encoding="utf-8")
        assert "CREATE TABLE IF NOT EXISTS facts" in content

    def test_migration_creates_cluster_suggestions_table(self):
        """Migration erstellt cluster_suggestions Tabelle."""
        content = self.MIGRATION_FILE.read_text(encoding="utf-8")
        assert "CREATE TABLE IF NOT EXISTS cluster_suggestions" in content

    def test_migration_interview_id_unique_constraint(self):
        """project_interviews.interview_id hat UNIQUE-Constraint."""
        content = self.MIGRATION_FILE.read_text(encoding="utf-8")
        assert "interview_id        UUID        NOT NULL UNIQUE" in content

    def test_migration_facts_cluster_id_nullable(self):
        """facts.cluster_id ist nullable (REFERENCES ohne NOT NULL) in facts Tabelle."""
        content = self.MIGRATION_FILE.read_text(encoding="utf-8")
        # Extrahiere nur den facts-Tabellen-Block
        facts_start = content.find("CREATE TABLE IF NOT EXISTS facts")
        assert facts_start != -1, "facts table not found in migration"
        facts_end = content.find(");", facts_start)
        facts_block = content[facts_start:facts_end]
        # cluster_id in facts Tabelle ist nullable (kein NOT NULL)
        facts_lines = facts_block.split("\n")
        for line in facts_lines:
            if "cluster_id" in line:
                assert "NOT NULL" not in line, (
                    "facts.cluster_id should be NULLABLE (unassigned facts)"
                )
                break
        else:
            pytest.fail("cluster_id column not found in facts table")

    def test_migration_cascade_deletes_on_projects(self):
        """CASCADE-Deletes auf projects definiert."""
        content = self.MIGRATION_FILE.read_text(encoding="utf-8")
        assert "ON DELETE CASCADE" in content


# ============================================================
# Zusaetzliche Unit-Tests: Modul-Struktur
# ============================================================


class TestClusteringModuleStructure:
    """Prueft, dass das clustering-Modul korrekt aufgebaut ist."""

    APP_DIR = Path(__file__).resolve().parents[3] / "app" / "clustering"

    def test_clustering_init_exists(self):
        """clustering/__init__.py existiert."""
        assert (self.APP_DIR / "__init__.py").exists()

    def test_clustering_models_exists(self):
        """clustering/models.py existiert."""
        assert (self.APP_DIR / "models.py").exists()

    def test_clustering_schemas_exists(self):
        """clustering/schemas.py existiert."""
        assert (self.APP_DIR / "schemas.py").exists()

    def test_clustering_project_repository_exists(self):
        """clustering/project_repository.py existiert."""
        assert (self.APP_DIR / "project_repository.py").exists()

    def test_clustering_interview_assignment_repository_exists(self):
        """clustering/interview_assignment_repository.py existiert."""
        assert (self.APP_DIR / "interview_assignment_repository.py").exists()

    def test_clustering_project_service_exists(self):
        """clustering/project_service.py existiert."""
        assert (self.APP_DIR / "project_service.py").exists()

    def test_clustering_interview_assignment_service_exists(self):
        """clustering/interview_assignment_service.py existiert."""
        assert (self.APP_DIR / "interview_assignment_service.py").exists()

    def test_clustering_router_exists(self):
        """clustering/router.py existiert."""
        assert (self.APP_DIR / "router.py").exists()


# ============================================================
# Zusaetzliche Unit-Tests: Router-Registrierung
# ============================================================


class TestRouterRegistration:
    """Prueft, dass der clustering Router in main.py registriert ist."""

    def test_clustering_router_registered_in_main(self):
        """clustering router wird in app/main.py inkludiert."""
        main_file = (
            Path(__file__).resolve().parents[3] / "app" / "main.py"
        )
        content = main_file.read_text(encoding="utf-8")
        assert "clustering" in content, (
            "clustering router muss in main.py registriert sein"
        )

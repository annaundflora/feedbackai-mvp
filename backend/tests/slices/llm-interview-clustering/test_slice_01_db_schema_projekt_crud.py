# backend/tests/slices/llm-interview-clustering/test_slice_01_db_schema_projekt_crud.py
"""Tests fuer Slice 1: DB Schema + Projekt CRUD.

Alle DB-Calls werden gemockt (mock_external Strategie).
Kein echter PostgreSQL-Zugriff in Unit-Tests.
"""
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient


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


# ============================================================
# AC 1: Projekt erstellen
# ============================================================

class TestCreateProject:
    """AC 1: POST /api/projects erstellt Projekt und gibt ProjectResponse zurueck."""

    def test_create_project_returns_201(
        self,
        mock_project_repository,
        mock_project_row,
        mock_user_id,
    ):
        """GIVEN name + research_goal WHEN POST /api/projects THEN HTTP 201"""
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

        import asyncio
        result = asyncio.get_event_loop().run_until_complete(
            service.create(request, user_id=mock_user_id)
        )

        assert result.name == "Onboarding UX Research"
        assert result.interview_count == 0
        assert result.cluster_count == 0
        assert result.fact_count == 0
        assert result.extraction_source_locked is False
        mock_project_repository.create.assert_called_once()

    def test_create_project_validates_required_fields(self):
        """GIVEN fehlendes research_goal WHEN CreateProjectRequest erstellt THEN ValidationError"""
        from pydantic import ValidationError
        from app.clustering.schemas import CreateProjectRequest

        with pytest.raises(ValidationError):
            CreateProjectRequest(name="Test")  # research_goal fehlt

    def test_create_project_validates_name_length(self):
        """GIVEN name mit 201 Zeichen WHEN Validation THEN ValidationError"""
        from pydantic import ValidationError
        from app.clustering.schemas import CreateProjectRequest

        with pytest.raises(ValidationError):
            CreateProjectRequest(
                name="x" * 201,
                research_goal="Test goal",
            )

    def test_create_project_default_extraction_source(self):
        """GIVEN kein extraction_source WHEN CreateProjectRequest THEN default 'summary'"""
        from app.clustering.schemas import CreateProjectRequest

        request = CreateProjectRequest(
            name="Test",
            research_goal="Test goal",
        )
        assert request.extraction_source == "summary"


# ============================================================
# AC 2: Projekt lesen (einzeln)
# ============================================================

class TestGetProject:
    """AC 2: GET /api/projects/{id} gibt vollstaendige ProjectResponse zurueck."""

    def test_get_project_returns_aggregated_counts(
        self,
        mock_project_repository,
        mock_project_row,
        mock_project_id,
        mock_user_id,
    ):
        """GIVEN existierendes Projekt WHEN GET /api/projects/{id} THEN korrekte Zaehler"""
        mock_project_repository.get_by_id = AsyncMock(return_value=mock_project_row)
        mock_project_repository.get_interview_count = AsyncMock(return_value=3)
        mock_project_repository.get_cluster_count = AsyncMock(return_value=2)
        mock_project_repository.get_fact_count = AsyncMock(return_value=7)

        from app.clustering.project_service import ProjectService

        service = ProjectService(repo=mock_project_repository)

        import asyncio
        result = asyncio.get_event_loop().run_until_complete(
            service.get(project_id=mock_project_id, user_id=mock_user_id)
        )

        assert result.interview_count == 3
        assert result.cluster_count == 2
        assert result.fact_count == 7

    def test_get_project_extraction_source_locked_when_facts_exist(
        self,
        mock_project_repository,
        mock_project_row,
        mock_project_id,
        mock_user_id,
    ):
        """GIVEN Projekt mit facts>0 WHEN GET THEN extraction_source_locked=True"""
        mock_project_repository.get_by_id = AsyncMock(return_value=mock_project_row)
        mock_project_repository.get_interview_count = AsyncMock(return_value=1)
        mock_project_repository.get_cluster_count = AsyncMock(return_value=0)
        mock_project_repository.get_fact_count = AsyncMock(return_value=5)  # facts > 0

        from app.clustering.project_service import ProjectService

        service = ProjectService(repo=mock_project_repository)

        import asyncio
        result = asyncio.get_event_loop().run_until_complete(
            service.get(project_id=mock_project_id, user_id=mock_user_id)
        )

        assert result.extraction_source_locked is True

    def test_get_project_not_found_raises_404(
        self,
        mock_project_repository,
        mock_project_id,
        mock_user_id,
    ):
        """GIVEN nicht-existierendes Projekt WHEN GET THEN HTTP 404"""
        mock_project_repository.get_by_id = AsyncMock(return_value=None)

        from app.clustering.project_service import ProjectService
        from fastapi import HTTPException

        service = ProjectService(repo=mock_project_repository)

        import asyncio
        with pytest.raises(HTTPException) as exc_info:
            asyncio.get_event_loop().run_until_complete(
                service.get(project_id=mock_project_id, user_id=mock_user_id)
            )
        assert exc_info.value.status_code == 404


# ============================================================
# AC 3: Projekte auflisten
# ============================================================

class TestListProjects:
    """AC 3: GET /api/projects gibt sortierte list[ProjectListItem] zurueck."""

    def test_list_projects_sorted_by_updated_at_desc(
        self,
        mock_project_repository,
        mock_user_id,
    ):
        """GIVEN mehrere Projekte WHEN GET /api/projects THEN sortiert nach updated_at desc"""
        from datetime import timedelta

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

        import asyncio
        results = asyncio.get_event_loop().run_until_complete(
            service.list(user_id=mock_user_id)
        )

        assert len(results) == 2
        assert results[0].name == "Neueres Projekt"
        assert results[1].name == "Aelteres Projekt"


# ============================================================
# AC 4: Projekt aktualisieren (PATCH-Semantik via PUT)
# ============================================================

class TestUpdateProject:
    """AC 4: PUT /api/projects/{id} aktualisiert nur gesendete Felder."""

    def test_update_project_partial_fields(
        self,
        mock_project_repository,
        mock_project_row,
        mock_project_id,
        mock_user_id,
    ):
        """GIVEN nur name im Request WHEN PUT THEN nur name geaendert, andere Felder unveraendert"""
        updated_row = {**mock_project_row, "name": "Neuer Name"}
        mock_project_repository.update = AsyncMock(return_value=updated_row)
        mock_project_repository.get_fact_count = AsyncMock(return_value=0)
        mock_project_repository.get_interview_count = AsyncMock(return_value=0)
        mock_project_repository.get_cluster_count = AsyncMock(return_value=0)

        from app.clustering.project_service import ProjectService
        from app.clustering.schemas import UpdateProjectRequest

        service = ProjectService(repo=mock_project_repository)
        request = UpdateProjectRequest(name="Neuer Name")

        import asyncio
        result = asyncio.get_event_loop().run_until_complete(
            service.update(
                project_id=mock_project_id,
                user_id=mock_user_id,
                request=request,
            )
        )

        assert result.name == "Neuer Name"
        assert result.research_goal == mock_project_row["research_goal"]  # unveraendert


# ============================================================
# AC 6: Projekt loeschen
# ============================================================

class TestDeleteProject:
    """AC 6: DELETE /api/projects/{id} loescht Projekt und gibt 204 zurueck."""

    def test_delete_project_calls_repository(
        self,
        mock_project_repository,
        mock_project_id,
        mock_user_id,
    ):
        """GIVEN existierendes Projekt WHEN DELETE THEN repository.delete() aufgerufen"""
        mock_project_repository.delete = AsyncMock(return_value=True)

        from app.clustering.project_service import ProjectService

        service = ProjectService(repo=mock_project_repository)

        import asyncio
        asyncio.get_event_loop().run_until_complete(
            service.delete(project_id=mock_project_id, user_id=mock_user_id)
        )

        mock_project_repository.delete.assert_called_once_with(
            project_id=mock_project_id,
            user_id=mock_user_id,
        )

    def test_delete_nonexistent_project_raises_404(
        self,
        mock_project_repository,
        mock_project_id,
        mock_user_id,
    ):
        """GIVEN nicht-existierendes Projekt WHEN DELETE THEN HTTP 404"""
        mock_project_repository.delete = AsyncMock(return_value=False)

        from app.clustering.project_service import ProjectService
        from fastapi import HTTPException

        service = ProjectService(repo=mock_project_repository)

        import asyncio
        with pytest.raises(HTTPException) as exc_info:
            asyncio.get_event_loop().run_until_complete(
                service.delete(project_id=mock_project_id, user_id=mock_user_id)
            )
        assert exc_info.value.status_code == 404


# ============================================================
# AC 9 + AC 10: Interview-Zuordnung
# ============================================================

class TestAssignInterviews:
    """AC 9/10: POST /api/projects/{id}/interviews ordnet Interviews zu."""

    def test_assign_interviews_creates_project_interview_rows(
        self,
        mock_interview_assignment_repository,
        mock_project_id,
    ):
        """GIVEN gueltige interview_ids WHEN POST /interviews THEN project_interviews Zeilen angelegt"""
        interview_id_1 = uuid.uuid4()
        interview_id_2 = uuid.uuid4()
        now = datetime.now(timezone.utc)

        mock_interview_assignment_repository.assign_interviews = AsyncMock(
            return_value=[
                {
                    "interview_id": interview_id_1,
                    "date": now,
                    "summary_preview": "User had issues...",
                    "fact_count": 0,
                    "extraction_status": "pending",
                    "clustering_status": "pending",
                },
                {
                    "interview_id": interview_id_2,
                    "date": now,
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

        import asyncio
        results = asyncio.get_event_loop().run_until_complete(
            service.assign(project_id=mock_project_id, request=request)
        )

        assert len(results) == 2
        assert all(r.extraction_status == "pending" for r in results)
        assert all(r.clustering_status == "pending" for r in results)

    def test_assign_already_assigned_interview_raises_409(
        self,
        mock_interview_assignment_repository,
        mock_project_id,
    ):
        """GIVEN bereits zugeordnetes Interview WHEN POST /interviews THEN HTTP 409"""
        from fastapi import HTTPException

        mock_interview_assignment_repository.assign_interviews = AsyncMock(
            side_effect=HTTPException(
                status_code=409,
                detail=f"Interview {uuid.uuid4()} already assigned to another project",
            )
        )

        from app.clustering.interview_assignment_service import InterviewAssignmentService
        from app.clustering.schemas import AssignRequest

        service = InterviewAssignmentService(repo=mock_interview_assignment_repository)
        request = AssignRequest(interview_ids=[uuid.uuid4()])

        import asyncio
        with pytest.raises(HTTPException) as exc_info:
            asyncio.get_event_loop().run_until_complete(
                service.assign(project_id=mock_project_id, request=request)
            )
        assert exc_info.value.status_code == 409


# ============================================================
# AC 8: Verfuegbare Interviews auflisten
# ============================================================

class TestListAvailableInterviews:
    """AC 8: GET /api/projects/{id}/interviews/available"""

    def test_list_available_excludes_assigned_interviews(
        self,
        mock_interview_assignment_repository,
    ):
        """GIVEN bereits zugeordnete Interviews WHEN GET /available THEN diese nicht enthalten"""
        now = datetime.now(timezone.utc)
        mock_interview_assignment_repository.list_available = AsyncMock(
            return_value=[
                {
                    "session_id": uuid.uuid4(),
                    "created_at": now,
                    "summary_preview": "Unassigned interview summary...",
                },
            ]
        )

        from app.clustering.interview_assignment_service import InterviewAssignmentService

        service = InterviewAssignmentService(repo=mock_interview_assignment_repository)

        import asyncio
        results = asyncio.get_event_loop().run_until_complete(
            service.list_available(user_id="00000000-0000-0000-0000-000000000001")
        )

        assert len(results) == 1
        assert results[0].summary_preview == "Unassigned interview summary..."


# ============================================================
# AC 5: Extraction-Source aendern
# ============================================================

class TestChangeExtractionSource:
    """AC 5: PUT /api/projects/{id}/extraction-source aendert Quelle wenn keine Facts vorhanden."""

    def test_change_extraction_source_without_facts(
        self,
        mock_project_repository,
        mock_project_row,
        mock_project_id,
        mock_user_id,
    ):
        """GIVEN Projekt ohne Facts WHEN PUT /extraction-source THEN neue Source gespeichert, locked=False"""
        updated_row = {**mock_project_row, "extraction_source": "transcript"}
        mock_project_repository.update = AsyncMock(return_value=updated_row)
        mock_project_repository.get_fact_count = AsyncMock(return_value=0)
        mock_project_repository.get_interview_count = AsyncMock(return_value=0)
        mock_project_repository.get_cluster_count = AsyncMock(return_value=0)

        from app.clustering.project_service import ProjectService
        from app.clustering.schemas import ChangeSourceRequest

        service = ProjectService(repo=mock_project_repository)
        request = ChangeSourceRequest(extraction_source="transcript", re_extract=False)

        import asyncio
        result = asyncio.get_event_loop().run_until_complete(
            service.change_extraction_source(
                project_id=mock_project_id,
                user_id=mock_user_id,
                request=request,
            )
        )

        assert result.extraction_source == "transcript"
        assert result.extraction_source_locked is False

"""FastAPI Router fuer Projekt-CRUD, Interview-Zuordnung und Fact Extraction Retry.

Implementiert 11 Endpunkte:
  - 7 Projekt-CRUD Endpunkte
  - 3 Interview-Assignment Endpunkte
  - 1 Retry-Endpunkt (Slice 2)
"""
from fastapi import APIRouter, Depends, Query, Request, Response

from app.clustering.interview_assignment_repository import InterviewAssignmentRepository
from app.clustering.interview_assignment_service import InterviewAssignmentService
from app.clustering.project_repository import ProjectRepository
from app.clustering.project_service import ProjectService
from app.clustering.schemas import (
    AssignRequest,
    AvailableInterview,
    ChangeSourceRequest,
    CreateProjectRequest,
    InterviewAssignment,
    ProjectListItem,
    ProjectResponse,
    UpdateModelsRequest,
    UpdateProjectRequest,
)
from app.config.settings import Settings
from app.db.session import get_session_factory

router = APIRouter(prefix="/api", tags=["clustering"])


# --- Dependency Factories ---


def get_project_service(request: Request) -> ProjectService:
    """FastAPI Dependency fuer ProjectService."""
    settings: Settings = request.app.state.settings
    session_factory = get_session_factory(settings)
    repo = ProjectRepository(session_factory=session_factory)
    return ProjectService(repo=repo)


def get_assignment_service(request: Request) -> InterviewAssignmentService:
    """FastAPI Dependency fuer InterviewAssignmentService."""
    settings: Settings = request.app.state.settings
    session_factory = get_session_factory(settings)
    repo = InterviewAssignmentRepository(session_factory=session_factory)

    # Slice 2: FactExtractionService fuer retry()
    fact_extraction_svc = getattr(request.app.state, "fact_extraction_service", None)

    # Slice 2: InterviewRepository fuer retry() response details
    from app.interview.repository import InterviewRepository
    interview_repo = InterviewRepository(session_factory=session_factory)

    return InterviewAssignmentService(
        repo=repo,
        interview_repository=interview_repo,
        fact_extraction_service=fact_extraction_svc,
    )


# ============================================================
# Projekt-CRUD Endpunkte (7)
# ============================================================


@router.post("/projects", status_code=201, response_model=ProjectResponse)
async def create_project(
    body: CreateProjectRequest,
    user_id: str = Query(default="00000000-0000-0000-0000-000000000001"),  # Slice 1 Stub
    service: ProjectService = Depends(get_project_service),
) -> ProjectResponse:
    """Erstellt ein neues Projekt.

    POST /api/projects
    Response 201: ProjectResponse
    """
    return await service.create(request=body, user_id=user_id)


@router.get("/projects", response_model=list[ProjectListItem])
async def list_projects(
    user_id: str = Query(default="00000000-0000-0000-0000-000000000001"),  # Slice 1 Stub
    service: ProjectService = Depends(get_project_service),
) -> list[ProjectListItem]:
    """Listet alle Projekte des Users.

    GET /api/projects
    Response 200: list[ProjectListItem] sortiert nach updated_at desc
    """
    return await service.list(user_id=user_id)


@router.get("/projects/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: str,
    user_id: str = Query(default="00000000-0000-0000-0000-000000000001"),  # Slice 1 Stub
    service: ProjectService = Depends(get_project_service),
) -> ProjectResponse:
    """Laedt ein einzelnes Projekt mit aggregierten Zaehlern.

    GET /api/projects/{id}
    Response 200: ProjectResponse
    Response 404: Project not found
    """
    return await service.get(project_id=project_id, user_id=user_id)


@router.put("/projects/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: str,
    body: UpdateProjectRequest,
    user_id: str = Query(default="00000000-0000-0000-0000-000000000001"),  # Slice 1 Stub
    service: ProjectService = Depends(get_project_service),
) -> ProjectResponse:
    """Aktualisiert Projektfelder (PATCH-Semantik via PUT).

    PUT /api/projects/{id}
    Response 200: ProjectResponse
    Response 404: Project not found
    """
    return await service.update(
        project_id=project_id, user_id=user_id, request=body
    )


@router.put("/projects/{project_id}/models", response_model=ProjectResponse)
async def update_project_models(
    project_id: str,
    body: UpdateModelsRequest,
    user_id: str = Query(default="00000000-0000-0000-0000-000000000001"),  # Slice 1 Stub
    service: ProjectService = Depends(get_project_service),
) -> ProjectResponse:
    """Aktualisiert Model-Slugs des Projekts.

    PUT /api/projects/{id}/models
    Response 200: ProjectResponse
    Response 404: Project not found
    """
    return await service.update_models(
        project_id=project_id, user_id=user_id, request=body
    )


@router.put("/projects/{project_id}/extraction-source", response_model=ProjectResponse)
async def change_extraction_source(
    project_id: str,
    body: ChangeSourceRequest,
    user_id: str = Query(default="00000000-0000-0000-0000-000000000001"),  # Slice 1 Stub
    service: ProjectService = Depends(get_project_service),
) -> ProjectResponse:
    """Aendert die Extraction-Source (summary oder transcript).

    PUT /api/projects/{id}/extraction-source
    Response 200: ProjectResponse
    Response 404: Project not found

    Note: re_extract-Trigger wird in Slice 2 implementiert.
    """
    return await service.change_extraction_source(
        project_id=project_id, user_id=user_id, request=body
    )


@router.delete("/projects/{project_id}", status_code=204)
async def delete_project(
    project_id: str,
    user_id: str = Query(default="00000000-0000-0000-0000-000000000001"),  # Slice 1 Stub
    service: ProjectService = Depends(get_project_service),
) -> Response:
    """Loescht ein Projekt mit allen zugehoerigen Daten (CASCADE).

    DELETE /api/projects/{id}
    Response 204: No Content
    Response 404: Project not found
    """
    await service.delete(project_id=project_id, user_id=user_id)
    return Response(status_code=204)


# ============================================================
# Interview-Assignment Endpunkte (3)
# ============================================================


@router.get(
    "/projects/{project_id}/interviews",
    response_model=list[InterviewAssignment],
)
async def list_assigned_interviews(
    project_id: str,
    service: InterviewAssignmentService = Depends(get_assignment_service),
) -> list[InterviewAssignment]:
    """Listet alle einem Projekt zugeordneten Interviews.

    GET /api/projects/{id}/interviews
    Response 200: list[InterviewAssignment]
    """
    return await service.list_assigned(project_id=project_id)


@router.get(
    "/projects/{project_id}/interviews/available",
    response_model=list[AvailableInterview],
)
async def list_available_interviews(
    project_id: str,
    user_id: str = Query(default="00000000-0000-0000-0000-000000000001"),  # Slice 1 Stub
    service: InterviewAssignmentService = Depends(get_assignment_service),
) -> list[AvailableInterview]:
    """Listet alle verfuegbaren (noch nicht zugeordneten) Interviews.

    GET /api/projects/{id}/interviews/available
    Response 200: list[AvailableInterview]
    """
    return await service.list_available(user_id=user_id)


@router.post(
    "/projects/{project_id}/interviews",
    status_code=201,
    response_model=list[InterviewAssignment],
)
async def assign_interviews(
    project_id: str,
    body: AssignRequest,
    service: InterviewAssignmentService = Depends(get_assignment_service),
) -> list[InterviewAssignment]:
    """Ordnet Interviews einem Projekt zu.

    POST /api/projects/{id}/interviews
    Response 201: list[InterviewAssignment]
    Response 409: Interview bereits zugeordnet
    """
    return await service.assign(project_id=project_id, request=body)


# ============================================================
# Fact Extraction Retry Endpoint (Slice 2)
# ============================================================


@router.post(
    "/projects/{project_id}/interviews/{interview_id}/retry",
    response_model=InterviewAssignment,
)
async def retry_interview_extraction(
    project_id: str,
    interview_id: str,
    service: InterviewAssignmentService = Depends(get_assignment_service),
) -> InterviewAssignment:
    """Setzt extraction_status auf 'pending' und startet Extraction-Task neu.

    POST /api/projects/{id}/interviews/{iid}/retry

    Nur erlaubt wenn aktueller Status == 'failed'.

    Response 200: InterviewAssignment mit extraction_status='pending'
    Response 404: Interview nicht in Projekt
    Response 409: Status ist nicht 'failed'
    """
    return await service.retry(
        project_id=project_id,
        interview_id=interview_id,
    )

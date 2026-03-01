"""FastAPI Router fuer Projekt-CRUD, Interview-Zuordnung, Fact Extraction Retry
und Clustering Pipeline.

Implementiert 14 Endpunkte (Slices 1-5) + 11 neue Endpunkte (Slice 6):
  - 7 Projekt-CRUD Endpunkte
  - 3 Interview-Assignment Endpunkte
  - 1 Retry-Endpunkt (Slice 2)
  - 1 Cluster-List Endpunkt (Slice 3)
  - 1 Recluster-Endpunkt (Slice 3)
  - 1 Status-Endpunkt (Slice 3)
  - 1 Cluster-Detail Endpunkt (Slice 5)
  - 11 Taxonomy-Editing Endpunkte (Slice 6):
    PUT /projects/{id}/clusters/{cid}         -- Rename
    POST /projects/{id}/clusters/merge        -- Merge
    POST /projects/{id}/clusters/merge/undo   -- Undo Merge
    POST /projects/{id}/clusters/{cid}/split/preview  -- Split Preview
    POST /projects/{id}/clusters/{cid}/split  -- Execute Split
    PUT /projects/{id}/facts/{fid}            -- Move single Fact
    POST /projects/{id}/facts/bulk-move       -- Bulk Move Facts
    GET /projects/{id}/suggestions            -- List Suggestions
    POST /projects/{id}/suggestions/{sid}/accept   -- Accept Suggestion
    POST /projects/{id}/suggestions/{sid}/dismiss  -- Dismiss Suggestion
    POST /projects/{id}/clustering/recluster  -- Full Re-Cluster (bereits in Slice 3)
"""
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request, Response

from app.clustering.cluster_repository import ClusterRepository
from app.clustering.cluster_suggestion_repository import ClusterSuggestionRepository
from app.clustering.exceptions import (
    ClusterNotFoundError,
    MergeConflictError,
    SplitValidationError,
    UndoExpiredError,
)
from app.clustering.fact_repository import FactRepository
from app.clustering.interview_assignment_repository import InterviewAssignmentRepository
from app.clustering.interview_assignment_service import InterviewAssignmentService
from app.clustering.project_repository import ProjectRepository
from app.clustering.project_service import ProjectService
from app.clustering.schemas import (
    AssignRequest,
    AvailableInterview,
    BulkMoveRequest,
    ChangeSourceRequest,
    ClusterDetailResponse,
    ClusterResponse,
    CreateProjectRequest,
    FactResponse,
    InterviewAssignment,
    MergeRequest,
    MergeResponse,
    MoveFactRequest,
    PipelineStatus,
    ProjectListItem,
    ProjectResponse,
    QuoteResponse,
    ReclusterStarted,
    RenameRequest,
    SplitConfirmRequest,
    SplitPreviewResponse,
    SuggestionResponse,
    UndoMergeRequest,
    UpdateModelsRequest,
    UpdateProjectRequest,
)
from app.clustering.taxonomy_service import SummaryGenerationService, TaxonomyService
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


# ============================================================
# Clustering Pipeline Endpunkte (Slice 3)
# ============================================================


def get_cluster_repository(request: Request) -> ClusterRepository:
    """FastAPI Dependency fuer ClusterRepository."""
    settings: Settings = request.app.state.settings
    session_factory = get_session_factory(settings)
    return ClusterRepository(session_factory=session_factory)


def get_fact_repository(request: Request) -> FactRepository:
    """FastAPI Dependency fuer FactRepository."""
    settings: Settings = request.app.state.settings
    session_factory = get_session_factory(settings)
    return FactRepository(session_factory=session_factory)


def get_suggestion_repository(request: Request) -> ClusterSuggestionRepository:
    """FastAPI Dependency fuer ClusterSuggestionRepository."""
    settings: Settings = request.app.state.settings
    session_factory = get_session_factory(settings)
    return ClusterSuggestionRepository(session_factory=session_factory)


def get_taxonomy_service(request: Request) -> TaxonomyService:
    """FastAPI Dependency fuer TaxonomyService.

    TaxonomyService ist stateful (haelt _undo_store in-memory).
    Wird als Singleton aus app.state gelesen falls vorhanden,
    sonst neu instantiiert (fuer Tests).
    """
    taxonomy_svc = getattr(request.app.state, "taxonomy_service", None)
    if taxonomy_svc is not None:
        return taxonomy_svc

    settings: Settings = request.app.state.settings
    session_factory = get_session_factory(settings)
    cluster_repo = ClusterRepository(session_factory=session_factory)
    fact_repo = FactRepository(session_factory=session_factory)
    summary_service = SummaryGenerationService(settings=settings)
    return TaxonomyService(
        cluster_repo=cluster_repo,
        fact_repo=fact_repo,
        summary_service=summary_service,
    )


def get_clustering_service(request: Request):
    """FastAPI Dependency fuer ClusteringService (Singleton aus app.state)."""
    service = getattr(request.app.state, "clustering_service", None)
    if service is None:
        raise HTTPException(
            status_code=503,
            detail="Clustering service not available",
        )
    return service


@router.get(
    "/projects/{project_id}/clusters",
    response_model=list[ClusterResponse],
)
async def list_clusters(
    project_id: str,
    cluster_repo: ClusterRepository = Depends(get_cluster_repository),
) -> list[ClusterResponse]:
    """Listet alle Cluster eines Projekts.

    GET /api/projects/{id}/clusters
    Response 200: list[ClusterResponse] sortiert nach fact_count DESC
    """
    clusters = await cluster_repo.list_for_project(project_id=project_id)
    return clusters


@router.post(
    "/projects/{project_id}/clustering/recluster",
    response_model=ReclusterStarted,
)
async def trigger_full_recluster(
    project_id: str,
    background_tasks: BackgroundTasks,
    clustering_service=Depends(get_clustering_service),
) -> ReclusterStarted:
    """Loescht alle Cluster und startet vollstaendiges Re-Clustering.

    Destruktiv: Alle bestehenden Cluster-Zuordnungen werden geloescht.
    Facts bleiben erhalten.

    Gibt sofort 200 zurueck (Recluster laeuft asynchron als Background-Task).
    Falls Recluster bereits laeuft: 409 Conflict.

    POST /api/projects/{id}/clustering/recluster
    Response 200: ReclusterStarted
    Response 404: Projekt nicht gefunden
    Response 409: Re-Cluster laeuft bereits
    """
    # Pruefe ob ein Recluster bereits laeuft (synchron, bevor Background-Task gestartet wird)
    if project_id in clustering_service._running_recluster:
        raise HTTPException(
            status_code=409,
            detail="Full re-cluster already running for this project",
        )

    # Starte Full-Recluster als FastAPI BackgroundTask (fire-and-forget)
    # Verwendet BackgroundTasks statt asyncio.create_task(), um Kompatibilitaet
    # mit TestClient (ASGI sync adapter) sicherzustellen und Event-Loop-Deadlocks
    # unter Python 3.13 zu vermeiden.
    background_tasks.add_task(clustering_service.full_recluster, project_id=project_id)

    return ReclusterStarted(
        status="started",
        message=f"Full re-cluster started for project {project_id}",
        project_id=project_id,
    )


@router.get(
    "/projects/{project_id}/clustering/status",
    response_model=PipelineStatus,
)
async def get_clustering_status(
    project_id: str,
    clustering_service=Depends(get_clustering_service),
) -> PipelineStatus:
    """Gibt den aktuellen Status der Clustering-Pipeline zurueck.

    GET /api/projects/{id}/clustering/status
    Response 200: PipelineStatus
    """
    # Pruefe ob ein Full-Recluster laeuft
    is_running = project_id in clustering_service._running_recluster

    if is_running:
        return PipelineStatus(
            status="running",
            mode="full",
            progress=None,
            current_step=None,
        )

    return PipelineStatus(
        status="idle",
        mode=None,
        progress=None,
        current_step=None,
    )


# ============================================================
# Cluster Detail Endpoint (Slice 5)
# ============================================================


@router.get(
    "/projects/{project_id}/clusters/{cluster_id}",
    response_model=ClusterDetailResponse,
)
async def get_cluster_detail(
    project_id: str,
    cluster_id: str,
    cluster_repo: ClusterRepository = Depends(get_cluster_repository),
) -> ClusterDetailResponse:
    """Laedt Cluster-Detail mit allen Facts und Originalzitaten.

    GET /api/projects/{id}/clusters/{cid}
    Response 200: ClusterDetailResponse (id, name, summary, fact_count, interview_count, facts, quotes)
    Response 404: Cluster nicht gefunden oder gehoert nicht zu diesem Projekt
    """
    detail = await cluster_repo.get_detail(
        cluster_id=cluster_id,
        project_id=project_id,
    )

    if detail is None:
        raise HTTPException(
            status_code=404,
            detail="Cluster not found",
        )

    facts = [
        FactResponse(
            id=str(f["id"]),
            content=f["content"],
            quote=f.get("quote"),
            confidence=f.get("confidence"),
            interview_id=str(f["interview_id"]),
            interview_date=f.get("interview_date"),
            cluster_id=str(f["cluster_id"]) if f.get("cluster_id") else None,
        )
        for f in detail["facts"]
    ]

    quotes = [
        QuoteResponse(
            fact_id=str(q["fact_id"]),
            content=q["content"],
            interview_id=str(q["interview_id"]),
            interview_number=int(q["interview_number"]),
        )
        for q in detail["quotes"]
    ]

    return ClusterDetailResponse(
        id=str(detail["id"]),
        name=detail["name"],
        summary=detail.get("summary"),
        fact_count=detail["fact_count"],
        interview_count=detail["interview_count"],
        facts=facts,
        quotes=quotes,
    )


# ============================================================
# Taxonomy-Editing Endpunkte (Slice 6)
# ============================================================


@router.put(
    "/projects/{project_id}/clusters/{cluster_id}",
    response_model=ClusterResponse,
)
async def rename_cluster(
    project_id: str,
    cluster_id: str,
    body: RenameRequest,
    taxonomy_service: TaxonomyService = Depends(get_taxonomy_service),
) -> ClusterResponse:
    """Benennt einen Cluster um (kein Summary-Regen, kein Re-Clustering).

    PUT /api/projects/{id}/clusters/{cid}
    Response 200: ClusterResponse (umbenannt)
    Response 404: Cluster nicht gefunden
    """
    try:
        return await taxonomy_service.rename(
            project_id=project_id,
            cluster_id=cluster_id,
            name=body.name,
        )
    except ClusterNotFoundError:
        raise HTTPException(status_code=404, detail="Cluster not found")


@router.post(
    "/projects/{project_id}/clusters/merge",
    response_model=MergeResponse,
)
async def merge_clusters(
    project_id: str,
    body: MergeRequest,
    taxonomy_service: TaxonomyService = Depends(get_taxonomy_service),
) -> MergeResponse:
    """Merged zwei Cluster: verschiebt Facts von Source nach Target, loescht Source.

    30-Sekunden Undo-Fenster via undo_id.
    Summary-Regen laeuft als Background-Task.

    POST /api/projects/{id}/clusters/merge
    Response 200: MergeResponse (merged_cluster, undo_id, undo_expires_at)
    Response 400: source == target
    Response 404: Cluster nicht gefunden
    """
    try:
        return await taxonomy_service.merge(
            project_id=project_id,
            source_id=body.source_cluster_id,
            target_id=body.target_cluster_id,
        )
    except MergeConflictError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ClusterNotFoundError:
        raise HTTPException(status_code=404, detail="Cluster not found")


@router.post(
    "/projects/{project_id}/clusters/merge/undo",
    response_model=ClusterResponse,
)
async def undo_merge(
    project_id: str,
    body: UndoMergeRequest,
    taxonomy_service: TaxonomyService = Depends(get_taxonomy_service),
) -> ClusterResponse:
    """Macht einen Merge rueckgaengig (innerhalb 30 Sekunden nach Merge).

    POST /api/projects/{id}/clusters/merge/undo
    Response 200: ClusterResponse (wiederhergestellter Source-Cluster)
    Response 409: Undo-Fenster abgelaufen oder ungueltige undo_id
    """
    try:
        return await taxonomy_service.undo_merge(
            project_id=project_id,
            undo_id=body.undo_id,
        )
    except UndoExpiredError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.post(
    "/projects/{project_id}/clusters/{cluster_id}/split/preview",
    response_model=SplitPreviewResponse,
)
async def preview_split(
    project_id: str,
    cluster_id: str,
    taxonomy_service: TaxonomyService = Depends(get_taxonomy_service),
) -> SplitPreviewResponse:
    """LLM analysiert Cluster und schlaegt Sub-Cluster vor.

    KEINE DB-Aenderungen.

    POST /api/projects/{id}/clusters/{cid}/split/preview
    Response 200: SplitPreviewResponse (subclusters mit vollstaendiger Fact-Liste)
    Response 404: Cluster nicht gefunden
    """
    try:
        return await taxonomy_service.preview_split(
            project_id=project_id,
            cluster_id=cluster_id,
        )
    except ClusterNotFoundError:
        raise HTTPException(status_code=404, detail="Cluster not found")


@router.post(
    "/projects/{project_id}/clusters/{cluster_id}/split",
    response_model=list[ClusterResponse],
)
async def execute_split(
    project_id: str,
    cluster_id: str,
    body: SplitConfirmRequest,
    taxonomy_service: TaxonomyService = Depends(get_taxonomy_service),
) -> list[ClusterResponse]:
    """Fuehrt den Split aus: neue Cluster anlegen, Original loeschen.

    Summary-Regen laeuft als Background-Task pro neuen Cluster.

    POST /api/projects/{id}/clusters/{cid}/split
    Response 200: list[ClusterResponse] (neue Sub-Cluster)
    Response 400: Validierungsfehler (< 2 Sub-Cluster, Facts nicht vollstaendig zugeordnet)
    Response 404: Cluster nicht gefunden
    """
    try:
        return await taxonomy_service.execute_split(
            project_id=project_id,
            cluster_id=cluster_id,
            subclusters=[sc.model_dump() for sc in body.subclusters],
        )
    except SplitValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ClusterNotFoundError:
        raise HTTPException(status_code=404, detail="Cluster not found")


@router.put(
    "/projects/{project_id}/facts/{fact_id}",
    response_model=FactResponse,
)
async def move_fact(
    project_id: str,
    fact_id: str,
    body: MoveFactRequest,
    fact_repo: FactRepository = Depends(get_fact_repository),
    cluster_repo: ClusterRepository = Depends(get_cluster_repository),
) -> FactResponse:
    """Verschiebt einen einzelnen Fact zu einem anderen Cluster (oder unassigned=null).

    Aktualisiert Counts auf altem und neuem Cluster.

    PUT /api/projects/{id}/facts/{fid}
    Response 200: FactResponse (verschobener Fact)
    Response 404: Fact nicht gefunden
    """
    updated = await fact_repo.move_single(
        fact_id=fact_id,
        target_cluster_id=body.cluster_id,
        project_id=project_id,
    )

    if updated is None:
        raise HTTPException(status_code=404, detail="Fact not found")

    # Counts fuer neues Cluster aktualisieren
    if body.cluster_id:
        await cluster_repo.recalculate_counts(
            project_id=project_id, cluster_id=body.cluster_id
        )

    return FactResponse(
        id=str(updated["id"]),
        content=updated["content"],
        quote=updated.get("quote"),
        confidence=updated.get("confidence"),
        interview_id=str(updated["interview_id"]),
        interview_date=updated.get("interview_date"),
        cluster_id=str(updated["cluster_id"]) if updated.get("cluster_id") else None,
    )


@router.post(
    "/projects/{project_id}/facts/bulk-move",
    response_model=list[FactResponse],
)
async def bulk_move_facts(
    project_id: str,
    body: BulkMoveRequest,
    fact_repo: FactRepository = Depends(get_fact_repository),
    cluster_repo: ClusterRepository = Depends(get_cluster_repository),
) -> list[FactResponse]:
    """Verschiebt mehrere Facts zu einem Cluster (oder unassigned=null).

    POST /api/projects/{id}/facts/bulk-move
    Response 200: list[FactResponse] (verschobene Facts)
    """
    await fact_repo.move_bulk(
        fact_ids=body.fact_ids,
        target_cluster_id=body.target_cluster_id,
        project_id=project_id,
    )

    # Counts aktualisieren fuer Ziel-Cluster
    if body.target_cluster_id:
        await cluster_repo.recalculate_counts(
            project_id=project_id, cluster_id=body.target_cluster_id
        )

    # Alle gemovelten Facts zurueckgeben (aus Ziel-Cluster oder unassigned)
    if body.target_cluster_id:
        all_moved = await fact_repo.get_by_cluster(
            cluster_id=body.target_cluster_id, project_id=project_id
        )
    else:
        all_moved = await fact_repo.get_unassigned(project_id=project_id)

    fact_id_set = set(body.fact_ids)
    return [
        FactResponse(
            id=str(f["id"]),
            content=f["content"],
            quote=f.get("quote"),
            confidence=f.get("confidence"),
            interview_id=str(f["interview_id"]),
            interview_date=f.get("interview_date"),
            cluster_id=str(f["cluster_id"]) if f.get("cluster_id") else None,
        )
        for f in all_moved
        if str(f["id"]) in fact_id_set
    ]


@router.get(
    "/projects/{project_id}/suggestions",
    response_model=list[SuggestionResponse],
)
async def list_suggestions(
    project_id: str,
    suggestion_repo: ClusterSuggestionRepository = Depends(get_suggestion_repository),
    cluster_repo: ClusterRepository = Depends(get_cluster_repository),
) -> list[SuggestionResponse]:
    """Laedt alle aktiven (pending) Merge/Split-Vorschlaege fuer ein Projekt.

    GET /api/projects/{id}/suggestions
    Response 200: list[SuggestionResponse]
    """
    suggestions = await suggestion_repo.list_pending_for_project(project_id=project_id)

    # Cluster-Namen ergaenzen (denormalisiert fuer Frontend)
    result = []
    for sug in suggestions:
        source_cluster_id = str(sug.get("source_cluster_id", ""))
        target_cluster_id = str(sug.get("target_cluster_id", "")) if sug.get("target_cluster_id") else None

        source_cluster = await cluster_repo.get_by_id(
            cluster_id=source_cluster_id, project_id=project_id
        )
        target_cluster = (
            await cluster_repo.get_by_id(cluster_id=target_cluster_id, project_id=project_id)
            if target_cluster_id
            else None
        )

        proposed_data = sug.get("proposed_data")
        if isinstance(proposed_data, str):
            import json as _json
            try:
                proposed_data = _json.loads(proposed_data)
            except Exception:
                proposed_data = None

        result.append(
            SuggestionResponse(
                id=str(sug["id"]),
                type=sug["type"],
                source_cluster_id=source_cluster_id,
                source_cluster_name=source_cluster["name"] if source_cluster else source_cluster_id,
                target_cluster_id=target_cluster_id,
                target_cluster_name=target_cluster["name"] if target_cluster else None,
                similarity_score=sug.get("similarity_score"),
                proposed_data=proposed_data,
                status=sug.get("status", "pending"),
                created_at=str(sug.get("created_at", "")),
            )
        )

    return result


@router.post(
    "/projects/{project_id}/suggestions/{suggestion_id}/accept",
    status_code=200,
)
async def accept_suggestion(
    project_id: str,
    suggestion_id: str,
    suggestion_repo: ClusterSuggestionRepository = Depends(get_suggestion_repository),
) -> dict:
    """Akzeptiert einen Merge/Split-Vorschlag (setzt Status auf 'accepted').

    Der eigentliche Merge/Split wird nicht automatisch ausgefuehrt --
    der Client ruft separate Merge/Split-Endpoints auf.

    POST /api/projects/{id}/suggestions/{sid}/accept
    Response 200: {"status": "accepted"}
    """
    await suggestion_repo.update_status(
        suggestion_id=suggestion_id,
        status="accepted",
    )
    return {"status": "accepted"}


@router.post(
    "/projects/{project_id}/suggestions/{suggestion_id}/dismiss",
    status_code=200,
)
async def dismiss_suggestion(
    project_id: str,
    suggestion_id: str,
    suggestion_repo: ClusterSuggestionRepository = Depends(get_suggestion_repository),
) -> dict:
    """Verwirft einen Merge/Split-Vorschlag (setzt Status auf 'dismissed').

    POST /api/projects/{id}/suggestions/{sid}/dismiss
    Response 200: {"status": "dismissed"}
    """
    await suggestion_repo.update_status(
        suggestion_id=suggestion_id,
        status="dismissed",
    )
    return {"status": "dismissed"}

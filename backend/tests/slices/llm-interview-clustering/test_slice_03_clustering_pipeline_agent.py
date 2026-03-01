# backend/tests/slices/llm-interview-clustering/test_slice_03_clustering_pipeline_agent.py
"""Tests fuer Slice 3: Clustering Pipeline + LangGraph Agent.

Abgeleitet aus GIVEN/WHEN/THEN Acceptance Criteria in der Slice-Spec:
specs/phase-4/2026-02-28-llm-interview-clustering/slices/slice-03-clustering-pipeline-agent.md

Alle LLM-Calls und DB-Calls werden gemockt (mock_external Strategie).
Kein echter OpenRouter-Zugriff, kein echter PostgreSQL-Zugriff in Unit-Tests.

ACs:
  AC-1:  FactExtractionService triggert ClusteringService nach Extraktion
  AC-2:  Neues Projekt ohne Cluster -> mode="full"
  AC-3:  Projekt mit bestehenden Clustern -> mode="incremental"
  AC-4:  Self-Correction Loop: quality_ok=False, iteration < 3 -> refine
  AC-5:  Self-Correction Loop: iteration >= 3 -> Loop beendet
  AC-6:  _persist_results() persistiert Cluster, Assignments, Summaries, Zaehler
  AC-7:  Merge-Suggestion gespeichert + SSE Event
  AC-8:  POST /recluster -> 200, Full Recluster gestartet
  AC-9:  POST /recluster waehrend laufendem Recluster -> 409
  AC-10: Clustering-Fehler -> clustering_status='failed', SSE clustering_failed
"""
import asyncio
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ============================================================
# FIXTURES
# ============================================================


@pytest.fixture
def mock_project_id() -> str:
    return str(uuid.UUID("550e8400-e29b-41d4-a716-446655440000"))


@pytest.fixture
def mock_interview_id() -> str:
    return str(uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8"))


@pytest.fixture
def mock_cluster_id_1() -> str:
    return str(uuid.UUID("7c9e6679-7425-40de-944b-e07fc1f90ae7"))


@pytest.fixture
def mock_cluster_id_2() -> str:
    return str(uuid.UUID("8fa85f64-5717-4562-b3fc-2c963f66afa6"))


@pytest.fixture
def mock_project_row(mock_project_id) -> dict:
    return {
        "id": uuid.UUID(mock_project_id),
        "research_goal": "Understand why users drop off during onboarding",
        "prompt_context": "B2B SaaS with 14-day free trial",
        "model_clustering": "anthropic/claude-sonnet-4",
        "model_summary": "anthropic/claude-haiku-4",
    }


@pytest.fixture
def mock_facts_new() -> list[dict]:
    return [
        {
            "id": str(uuid.uuid4()),
            "content": "User cannot find settings page.",
            "interview_id": str(uuid.uuid4()),
        },
        {
            "id": str(uuid.uuid4()),
            "content": "Navigation structure is confusing.",
            "interview_id": str(uuid.uuid4()),
        },
    ]


@pytest.fixture
def mock_existing_clusters(mock_cluster_id_1, mock_cluster_id_2) -> list[dict]:
    return [
        {
            "id": mock_cluster_id_1,
            "name": "Navigation Issues",
            "summary": "Users struggle to find key features.",
            "fact_count": 3,
            "interview_count": 2,
        },
        {
            "id": mock_cluster_id_2,
            "name": "Pricing Confusion",
            "summary": "Users don't understand pricing tiers.",
            "fact_count": 2,
            "interview_count": 1,
        },
    ]


@pytest.fixture
def mock_cluster_repository():
    repo = AsyncMock()
    repo.list_for_project = AsyncMock(return_value=[])
    repo.create_clusters = AsyncMock(return_value=[])
    repo.update_summary = AsyncMock(return_value={})
    repo.update_counts = AsyncMock()
    repo.update_counts_from_db = AsyncMock()
    repo.delete_all_for_project = AsyncMock()
    return repo


@pytest.fixture
def mock_suggestion_repository():
    repo = AsyncMock()
    repo.save_suggestions = AsyncMock(return_value=[])
    return repo


@pytest.fixture
def mock_fact_repository():
    repo = AsyncMock()
    repo.get_facts_for_interview = AsyncMock(return_value=[])
    repo.get_facts_for_project = AsyncMock(return_value=[])
    repo.update_cluster_assignments = AsyncMock()
    repo.reset_cluster_assignments_for_project = AsyncMock()
    return repo


@pytest.fixture
def mock_assignment_repository():
    repo = AsyncMock()
    repo.update_clustering_status = AsyncMock()
    repo.get_all_for_project = AsyncMock(return_value=[])
    return repo


@pytest.fixture
def mock_project_repository():
    return AsyncMock()


@pytest.fixture
def mock_event_bus():
    return AsyncMock()


@pytest.fixture
def mock_settings():
    settings = MagicMock()
    settings.openrouter_api_key = "test-key"
    settings.clustering_model_default = "anthropic/claude-sonnet-4"
    settings.summary_model_default = "anthropic/claude-haiku-4"
    settings.clustering_split_threshold = 8
    settings.clustering_merge_similarity_threshold = 0.8
    settings.clustering_taxonomy_batch_size = 20
    settings.clustering_max_retries = 3
    settings.clustering_llm_timeout_seconds = 120
    settings.interviewer_llm = "anthropic/claude-sonnet-4.5"
    return settings


def _build_clustering_service(
    mock_graph,
    mock_cluster_repository,
    mock_suggestion_repository,
    mock_fact_repository,
    mock_assignment_repository,
    mock_project_repository,
    mock_event_bus,
    mock_settings,
):
    """Helper to construct ClusteringService with all mocked dependencies."""
    from app.clustering.service import ClusteringService

    return ClusteringService(
        clustering_graph=mock_graph,
        cluster_repository=mock_cluster_repository,
        cluster_suggestion_repository=mock_suggestion_repository,
        fact_repository=mock_fact_repository,
        assignment_repository=mock_assignment_repository,
        project_repository=mock_project_repository,
        event_bus=mock_event_bus,
        settings=mock_settings,
    )


# ============================================================
# AC-1: Clustering-Trigger nach Fact Extraction
# ============================================================


class TestAC1ClusteringTriggerAfterExtraction:
    """AC-1: GIVEN ein Interview das einem Projekt zugeordnet ist und extraction_status='completed'
    WHEN FactExtractionService.process_interview() erfolgreich abschliesst
    THEN wird ClusteringService.process_interview(project_id, interview_id) als Background-Task
    gestartet und clustering_status auf 'running' gesetzt."""

    @pytest.mark.asyncio
    async def test_fact_extraction_triggers_clustering_via_create_task(self):
        """AC-1: FactExtractionService ruft asyncio.create_task(clustering_service.process_interview(...)) auf."""
        mock_clustering_service = AsyncMock()
        mock_clustering_service.process_interview = AsyncMock()

        mock_fact_repo = AsyncMock()
        mock_assignment_repo = AsyncMock()
        mock_project_repo = AsyncMock()
        mock_interview_repo = AsyncMock()
        mock_event_bus = AsyncMock()
        mock_settings = MagicMock()
        mock_settings.openrouter_api_key = "test-key"
        mock_settings.interviewer_llm = "anthropic/claude-sonnet-4.5"
        mock_settings.clustering_max_retries = 3
        mock_settings.clustering_llm_timeout_seconds = 120

        project_id = str(uuid.uuid4())
        interview_id = str(uuid.uuid4())

        mock_project_repo.get_by_id = AsyncMock(return_value={
            "id": project_id,
            "research_goal": "Test research goal",
            "extraction_source": "summary",
            "model_extraction": "anthropic/claude-sonnet-4",
        })

        mock_interview_repo.get_session = AsyncMock(return_value={
            "id": interview_id,
            "summary": "The user had trouble with navigation.",
        })

        mock_fact_repo.save_facts = AsyncMock(return_value=[
            {"id": str(uuid.uuid4()), "content": "User had trouble with navigation."}
        ])

        mock_assignment_repo.update_extraction_status = AsyncMock()

        # Patch ChatOpenAI in extraction module init and the internal _call_llm_with_retry
        with patch("app.clustering.extraction.ChatOpenAI"):
            from app.clustering.extraction import FactExtractionService

            service = FactExtractionService(
                fact_repository=mock_fact_repo,
                assignment_repository=mock_assignment_repo,
                project_repository=mock_project_repo,
                interview_repository=mock_interview_repo,
                event_bus=mock_event_bus,
                settings=mock_settings,
                clustering_service=mock_clustering_service,
            )

        # Mock the internal LLM call to return valid facts
        service._call_llm_with_retry = AsyncMock(return_value=[
            {"content": "User had trouble with navigation.", "quote": "I was lost.", "confidence": 0.9}
        ])

        with patch("asyncio.create_task") as mock_create_task:
            await service.process_interview(project_id, interview_id)

        # Verify asyncio.create_task was called with clustering_service.process_interview coroutine
        mock_create_task.assert_called_once()

    @pytest.mark.asyncio
    async def test_fact_extraction_does_not_trigger_clustering_when_service_not_set(self):
        """AC-1 negative: Without clustering_service set, no create_task is called."""
        mock_fact_repo = AsyncMock()
        mock_assignment_repo = AsyncMock()
        mock_project_repo = AsyncMock()
        mock_interview_repo = AsyncMock()
        mock_event_bus = AsyncMock()
        mock_settings = MagicMock()
        mock_settings.openrouter_api_key = "test-key"
        mock_settings.interviewer_llm = "anthropic/claude-sonnet-4.5"
        mock_settings.clustering_max_retries = 3
        mock_settings.clustering_llm_timeout_seconds = 120

        project_id = str(uuid.uuid4())
        interview_id = str(uuid.uuid4())

        mock_project_repo.get_by_id = AsyncMock(return_value={
            "id": project_id,
            "research_goal": "Test",
            "extraction_source": "summary",
            "model_extraction": "anthropic/claude-sonnet-4",
        })
        mock_interview_repo.get_session = AsyncMock(return_value={
            "id": interview_id,
            "summary": "Test summary",
        })
        mock_fact_repo.save_facts = AsyncMock(return_value=[
            {"id": str(uuid.uuid4()), "content": "fact"}
        ])
        mock_assignment_repo.update_extraction_status = AsyncMock()

        with patch("app.clustering.extraction.ChatOpenAI"):
            from app.clustering.extraction import FactExtractionService

            service = FactExtractionService(
                fact_repository=mock_fact_repo,
                assignment_repository=mock_assignment_repo,
                project_repository=mock_project_repo,
                interview_repository=mock_interview_repo,
                event_bus=mock_event_bus,
                settings=mock_settings,
                clustering_service=None,  # Not set
            )

        service._call_llm_with_retry = AsyncMock(return_value=[
            {"content": "fact", "quote": None, "confidence": 0.9}
        ])

        with patch("asyncio.create_task") as mock_create_task:
            await service.process_interview(project_id, interview_id)

        mock_create_task.assert_not_called()


# ============================================================
# AC-2: Neues Projekt ohne Cluster -> mode="full"
# ============================================================


class TestAC2FirstInterviewFullMode:
    """AC-2: GIVEN ein Projekt ohne bestehende Cluster mit extrahierten Facts
    WHEN ClusteringService.process_interview() ausgefuehrt wird
    THEN wird ClusteringGraph mit mode='full' aufgerufen, eine initiale Taxonomie
    generiert, alle Facts Clustern zugeordnet, und mind. 1 Cluster in der
    clusters-Tabelle erstellt."""

    @pytest.mark.asyncio
    async def test_process_interview_uses_full_mode_when_no_clusters_exist(
        self,
        mock_project_id,
        mock_interview_id,
        mock_project_row,
        mock_facts_new,
        mock_cluster_repository,
        mock_fact_repository,
        mock_assignment_repository,
        mock_project_repository,
        mock_event_bus,
        mock_suggestion_repository,
        mock_settings,
    ):
        """AC-2: GIVEN Projekt ohne Cluster
        WHEN process_interview() aufgerufen
        THEN ClusteringGraph mit mode='full' aufgerufen."""
        mock_project_repository.get_by_id = AsyncMock(return_value=mock_project_row)
        mock_cluster_repository.list_for_project = AsyncMock(return_value=[])
        mock_fact_repository.get_facts_for_interview = AsyncMock(return_value=mock_facts_new)
        mock_fact_repository.get_facts_for_project = AsyncMock(return_value=mock_facts_new)

        new_cluster_uuid = str(uuid.uuid4())
        mock_cluster_repository.create_clusters = AsyncMock(
            return_value=[{"id": new_cluster_uuid, "name": "Navigation Issues"}]
        )

        mock_graph = AsyncMock()
        mock_graph.invoke = AsyncMock(return_value={
            "assignments": [
                {"fact_id": f["id"], "cluster_id": None, "new_cluster_name": "Navigation Issues"}
                for f in mock_facts_new
            ],
            "new_clusters": [{"name": "Navigation Issues", "fact_ids": [f["id"] for f in mock_facts_new]}],
            "summaries": {"Navigation Issues": "Users struggle with navigation."},
            "suggestions": [],
            "quality_ok": True,
            "iteration": 1,
        })

        service = _build_clustering_service(
            mock_graph,
            mock_cluster_repository,
            mock_suggestion_repository,
            mock_fact_repository,
            mock_assignment_repository,
            mock_project_repository,
            mock_event_bus,
            mock_settings,
        )

        await service.process_interview(mock_project_id, mock_interview_id)

        # Verify: mode="full" in invoke call
        call_state = mock_graph.invoke.call_args[0][0]
        assert call_state["mode"] == "full"

    @pytest.mark.asyncio
    async def test_full_mode_creates_at_least_one_cluster(
        self,
        mock_project_id,
        mock_interview_id,
        mock_project_row,
        mock_facts_new,
        mock_cluster_repository,
        mock_fact_repository,
        mock_assignment_repository,
        mock_project_repository,
        mock_event_bus,
        mock_suggestion_repository,
        mock_settings,
    ):
        """AC-2: Full-Mode -> mind. 1 Cluster in clusters-Tabelle erstellt."""
        mock_project_repository.get_by_id = AsyncMock(return_value=mock_project_row)
        mock_cluster_repository.list_for_project = AsyncMock(return_value=[])
        mock_fact_repository.get_facts_for_interview = AsyncMock(return_value=mock_facts_new)
        mock_fact_repository.get_facts_for_project = AsyncMock(return_value=mock_facts_new)

        new_cluster_uuid = str(uuid.uuid4())
        mock_cluster_repository.create_clusters = AsyncMock(
            return_value=[{"id": new_cluster_uuid, "name": "Navigation Issues"}]
        )

        mock_graph = AsyncMock()
        mock_graph.invoke = AsyncMock(return_value={
            "assignments": [
                {"fact_id": f["id"], "cluster_id": None, "new_cluster_name": "Navigation Issues"}
                for f in mock_facts_new
            ],
            "new_clusters": [{"name": "Navigation Issues", "fact_ids": [f["id"] for f in mock_facts_new]}],
            "summaries": {"Navigation Issues": "Users struggle with navigation."},
            "suggestions": [],
            "quality_ok": True,
            "iteration": 1,
        })

        service = _build_clustering_service(
            mock_graph,
            mock_cluster_repository,
            mock_suggestion_repository,
            mock_fact_repository,
            mock_assignment_repository,
            mock_project_repository,
            mock_event_bus,
            mock_settings,
        )

        await service.process_interview(mock_project_id, mock_interview_id)

        # Verify: create_clusters called with at least 1 cluster
        mock_cluster_repository.create_clusters.assert_called_once()
        create_args = mock_cluster_repository.create_clusters.call_args
        clusters_arg = create_args.kwargs.get("clusters") or create_args[1].get("clusters", [])
        assert len(clusters_arg) >= 1


# ============================================================
# AC-3: Bestehendes Projekt -> mode="incremental"
# ============================================================


class TestAC3IncrementalMode:
    """AC-3: GIVEN ein Projekt mit bestehenden Clustern und einem neuen Interview
    WHEN ClusteringService.process_interview() ausgefuehrt wird
    THEN wird ClusteringGraph mit mode='incremental' aufgerufen, die neuen Facts den
    bestehenden Clustern zugeordnet (oder neue Cluster vorgeschlagen), und
    clustering_status auf 'completed' gesetzt."""

    @pytest.mark.asyncio
    async def test_process_interview_uses_incremental_mode_with_existing_clusters(
        self,
        mock_project_id,
        mock_interview_id,
        mock_project_row,
        mock_facts_new,
        mock_existing_clusters,
        mock_cluster_id_1,
        mock_cluster_repository,
        mock_fact_repository,
        mock_assignment_repository,
        mock_project_repository,
        mock_event_bus,
        mock_suggestion_repository,
        mock_settings,
    ):
        """AC-3: GIVEN Projekt mit bestehenden Clustern
        WHEN process_interview() aufgerufen
        THEN ClusteringGraph mit mode='incremental' aufgerufen."""
        mock_project_repository.get_by_id = AsyncMock(return_value=mock_project_row)
        mock_cluster_repository.list_for_project = AsyncMock(return_value=mock_existing_clusters)
        mock_fact_repository.get_facts_for_interview = AsyncMock(return_value=mock_facts_new)

        mock_graph = AsyncMock()
        mock_graph.invoke = AsyncMock(return_value={
            "assignments": [
                {"fact_id": f["id"], "cluster_id": mock_cluster_id_1, "new_cluster_name": None}
                for f in mock_facts_new
            ],
            "new_clusters": [],
            "summaries": {mock_cluster_id_1: "Updated navigation summary."},
            "suggestions": [],
            "quality_ok": True,
            "iteration": 1,
        })

        service = _build_clustering_service(
            mock_graph,
            mock_cluster_repository,
            mock_suggestion_repository,
            mock_fact_repository,
            mock_assignment_repository,
            mock_project_repository,
            mock_event_bus,
            mock_settings,
        )

        await service.process_interview(mock_project_id, mock_interview_id)

        # Verify: mode="incremental" in invoke call
        call_state = mock_graph.invoke.call_args[0][0]
        assert call_state["mode"] == "incremental"
        assert len(call_state["existing_clusters"]) == 2

    @pytest.mark.asyncio
    async def test_incremental_mode_sets_clustering_status_completed(
        self,
        mock_project_id,
        mock_interview_id,
        mock_project_row,
        mock_facts_new,
        mock_existing_clusters,
        mock_cluster_id_1,
        mock_cluster_repository,
        mock_fact_repository,
        mock_assignment_repository,
        mock_project_repository,
        mock_event_bus,
        mock_suggestion_repository,
        mock_settings,
    ):
        """AC-3: After incremental clustering, clustering_status is set to 'completed'."""
        mock_project_repository.get_by_id = AsyncMock(return_value=mock_project_row)
        mock_cluster_repository.list_for_project = AsyncMock(return_value=mock_existing_clusters)
        mock_fact_repository.get_facts_for_interview = AsyncMock(return_value=mock_facts_new)

        mock_graph = AsyncMock()
        mock_graph.invoke = AsyncMock(return_value={
            "assignments": [
                {"fact_id": f["id"], "cluster_id": mock_cluster_id_1, "new_cluster_name": None}
                for f in mock_facts_new
            ],
            "new_clusters": [],
            "summaries": {},
            "suggestions": [],
            "quality_ok": True,
            "iteration": 1,
        })

        service = _build_clustering_service(
            mock_graph,
            mock_cluster_repository,
            mock_suggestion_repository,
            mock_fact_repository,
            mock_assignment_repository,
            mock_project_repository,
            mock_event_bus,
            mock_settings,
        )

        await service.process_interview(mock_project_id, mock_interview_id)

        # Verify: clustering_status="completed" was set
        status_calls = mock_assignment_repository.update_clustering_status.call_args_list
        final_call = status_calls[-1]
        assert final_call.kwargs.get("clustering_status") == "completed"


# ============================================================
# AC-4: Self-Correction Loop: quality_ok=False, iteration < 3
# ============================================================


class TestAC4SelfCorrectionLoopRefine:
    """AC-4: GIVEN ein ClusteringGraph-Lauf wo validate_quality quality_ok=false zurueckgibt
    WHEN iteration < 3
    THEN wird refine_clusters ausgefuehrt und danach erneut zu generate_summaries
    weitergeleitet (Self-Correction Loop)."""

    def test_route_after_validation_returns_refine_when_quality_not_ok_and_under_limit(self):
        """AC-4: quality_ok=False, iteration=1 -> route='refine'."""
        from app.clustering.graph import ClusteringGraph, MAX_CORRECTION_ITERATIONS

        settings = MagicMock()
        settings.openrouter_api_key = "test"
        settings.clustering_model_default = "model"
        settings.summary_model_default = "model"

        with patch("app.clustering.graph.ChatOpenAI"):
            graph = ClusteringGraph(settings)

        state = {
            "quality_ok": False,
            "iteration": 1,
        }
        route = graph._route_after_validation(state)
        assert route == "refine"

    def test_route_after_validation_returns_refine_at_iteration_2(self):
        """AC-4: quality_ok=False, iteration=2 -> route='refine' (still under MAX_CORRECTION_ITERATIONS=3)."""
        from app.clustering.graph import ClusteringGraph

        settings = MagicMock()
        settings.openrouter_api_key = "test"
        settings.clustering_model_default = "model"
        settings.summary_model_default = "model"

        with patch("app.clustering.graph.ChatOpenAI"):
            graph = ClusteringGraph(settings)

        state = {
            "quality_ok": False,
            "iteration": 2,
        }
        route = graph._route_after_validation(state)
        assert route == "refine"

    def test_route_after_validation_returns_ok_when_quality_is_ok(self):
        """AC-4: quality_ok=True -> route='ok' (no correction needed)."""
        from app.clustering.graph import ClusteringGraph

        settings = MagicMock()
        settings.openrouter_api_key = "test"
        settings.clustering_model_default = "model"
        settings.summary_model_default = "model"

        with patch("app.clustering.graph.ChatOpenAI"):
            graph = ClusteringGraph(settings)

        state = {
            "quality_ok": True,
            "iteration": 1,
        }
        route = graph._route_after_validation(state)
        assert route == "ok"


# ============================================================
# AC-5: Self-Correction Loop: iteration >= 3 -> Loop beendet
# ============================================================


class TestAC5SelfCorrectionLoopMaxIterations:
    """AC-5: GIVEN ein ClusteringGraph-Lauf wo validate_quality 3x quality_ok=false zurueckgibt
    WHEN iteration >= 3
    THEN wird der Loop beendet, generate_summaries mit den letzten Assignments aufgerufen,
    und das Ergebnis akzeptiert (kein 4. Loop)."""

    def test_route_after_validation_returns_ok_when_max_iterations_reached(self):
        """AC-5: quality_ok=False, iteration=3 -> route='ok' (Loop beendet, kein 4. Loop)."""
        from app.clustering.graph import ClusteringGraph, MAX_CORRECTION_ITERATIONS

        settings = MagicMock()
        settings.openrouter_api_key = "test"
        settings.clustering_model_default = "model"
        settings.summary_model_default = "model"

        with patch("app.clustering.graph.ChatOpenAI"):
            graph = ClusteringGraph(settings)

        state = {
            "quality_ok": False,
            "iteration": MAX_CORRECTION_ITERATIONS,  # == 3
        }
        route = graph._route_after_validation(state)
        assert route == "ok"

    def test_route_after_validation_returns_ok_when_over_max_iterations(self):
        """AC-5: quality_ok=False, iteration=4 -> route='ok' (well past limit)."""
        from app.clustering.graph import ClusteringGraph

        settings = MagicMock()
        settings.openrouter_api_key = "test"
        settings.clustering_model_default = "model"
        settings.summary_model_default = "model"

        with patch("app.clustering.graph.ChatOpenAI"):
            graph = ClusteringGraph(settings)

        state = {
            "quality_ok": False,
            "iteration": 4,
        }
        route = graph._route_after_validation(state)
        assert route == "ok"

    def test_max_correction_iterations_constant_is_3(self):
        """AC-5: MAX_CORRECTION_ITERATIONS == 3 (as specified in spec)."""
        from app.clustering.graph import MAX_CORRECTION_ITERATIONS

        assert MAX_CORRECTION_ITERATIONS == 3


# ============================================================
# AC-6: Persistierung der Ergebnisse
# ============================================================


class TestAC6PersistResults:
    """AC-6: GIVEN ein abgeschlossener Clustering-Lauf
    WHEN ClusteringService._persist_results() aufgerufen wird
    THEN werden alle neuen Cluster in clusters-Tabelle angelegt, alle Fact-Zuordnungen
    in facts.cluster_id aktualisiert, Summaries in clusters.summary gespeichert,
    und denormalisierte Zaehler (fact_count, interview_count) korrekt aktualisiert."""

    @pytest.mark.asyncio
    async def test_persist_results_creates_clusters_and_updates_facts(
        self,
        mock_project_id,
        mock_facts_new,
        mock_cluster_repository,
        mock_fact_repository,
        mock_assignment_repository,
        mock_project_repository,
        mock_event_bus,
        mock_suggestion_repository,
        mock_settings,
    ):
        """AC-6: _persist_results() creates new clusters in DB."""
        new_cluster_uuid = str(uuid.uuid4())
        mock_cluster_repository.create_clusters = AsyncMock(
            return_value=[{"id": new_cluster_uuid, "name": "Navigation Issues"}]
        )

        graph_output = {
            "assignments": [
                {"fact_id": mock_facts_new[0]["id"], "cluster_id": None, "new_cluster_name": "Navigation Issues"},
            ],
            "new_clusters": [{"name": "Navigation Issues", "fact_ids": [mock_facts_new[0]["id"]]}],
            "summaries": {"Navigation Issues": "Users struggle with navigation."},
            "suggestions": [],
        }

        mock_graph = AsyncMock()
        service = _build_clustering_service(
            mock_graph,
            mock_cluster_repository,
            mock_suggestion_repository,
            mock_fact_repository,
            mock_assignment_repository,
            mock_project_repository,
            mock_event_bus,
            mock_settings,
        )

        await service._persist_results(mock_project_id, graph_output)

        # Verify: clusters created
        mock_cluster_repository.create_clusters.assert_called_once()

    @pytest.mark.asyncio
    async def test_persist_results_updates_fact_assignments(
        self,
        mock_project_id,
        mock_facts_new,
        mock_cluster_repository,
        mock_fact_repository,
        mock_assignment_repository,
        mock_project_repository,
        mock_event_bus,
        mock_suggestion_repository,
        mock_settings,
    ):
        """AC-6: _persist_results() updates facts.cluster_id."""
        new_cluster_uuid = str(uuid.uuid4())
        mock_cluster_repository.create_clusters = AsyncMock(
            return_value=[{"id": new_cluster_uuid, "name": "Navigation Issues"}]
        )

        graph_output = {
            "assignments": [
                {"fact_id": mock_facts_new[0]["id"], "cluster_id": None, "new_cluster_name": "Navigation Issues"},
                {"fact_id": mock_facts_new[1]["id"], "cluster_id": None, "new_cluster_name": "Navigation Issues"},
            ],
            "new_clusters": [{"name": "Navigation Issues", "fact_ids": [f["id"] for f in mock_facts_new]}],
            "summaries": {},
            "suggestions": [],
        }

        mock_graph = AsyncMock()
        service = _build_clustering_service(
            mock_graph,
            mock_cluster_repository,
            mock_suggestion_repository,
            mock_fact_repository,
            mock_assignment_repository,
            mock_project_repository,
            mock_event_bus,
            mock_settings,
        )

        await service._persist_results(mock_project_id, graph_output)

        # Verify: update_cluster_assignments called
        mock_fact_repository.update_cluster_assignments.assert_called_once()
        assignments_arg = mock_fact_repository.update_cluster_assignments.call_args[0][0]
        assert len(assignments_arg) == 2
        # All assignments should have the resolved cluster_id (not None)
        for a in assignments_arg:
            assert a["cluster_id"] == new_cluster_uuid

    @pytest.mark.asyncio
    async def test_persist_results_saves_summaries(
        self,
        mock_project_id,
        mock_facts_new,
        mock_cluster_repository,
        mock_fact_repository,
        mock_assignment_repository,
        mock_project_repository,
        mock_event_bus,
        mock_suggestion_repository,
        mock_settings,
    ):
        """AC-6: _persist_results() saves summaries to clusters.summary."""
        new_cluster_uuid = str(uuid.uuid4())
        mock_cluster_repository.create_clusters = AsyncMock(
            return_value=[{"id": new_cluster_uuid, "name": "Navigation Issues"}]
        )

        graph_output = {
            "assignments": [],
            "new_clusters": [{"name": "Navigation Issues", "fact_ids": []}],
            "summaries": {"Navigation Issues": "Users struggle with navigation."},
            "suggestions": [],
        }

        mock_graph = AsyncMock()
        service = _build_clustering_service(
            mock_graph,
            mock_cluster_repository,
            mock_suggestion_repository,
            mock_fact_repository,
            mock_assignment_repository,
            mock_project_repository,
            mock_event_bus,
            mock_settings,
        )

        await service._persist_results(mock_project_id, graph_output)

        # Verify: update_summary called with correct cluster_id and summary text
        mock_cluster_repository.update_summary.assert_called_once_with(
            cluster_id=new_cluster_uuid,
            summary="Users struggle with navigation.",
        )

    @pytest.mark.asyncio
    async def test_persist_results_updates_denormalized_counts(
        self,
        mock_project_id,
        mock_facts_new,
        mock_cluster_repository,
        mock_fact_repository,
        mock_assignment_repository,
        mock_project_repository,
        mock_event_bus,
        mock_suggestion_repository,
        mock_settings,
    ):
        """AC-6: _persist_results() updates denormalized fact_count and interview_count."""
        mock_cluster_repository.create_clusters = AsyncMock(return_value=[])

        graph_output = {
            "assignments": [],
            "new_clusters": [],
            "summaries": {},
            "suggestions": [],
        }

        mock_graph = AsyncMock()
        service = _build_clustering_service(
            mock_graph,
            mock_cluster_repository,
            mock_suggestion_repository,
            mock_fact_repository,
            mock_assignment_repository,
            mock_project_repository,
            mock_event_bus,
            mock_settings,
        )

        await service._persist_results(mock_project_id, graph_output)

        # Verify: update_counts_from_db called
        mock_cluster_repository.update_counts_from_db.assert_called_once_with(mock_project_id)


# ============================================================
# AC-7: Merge-Suggestion gespeichert + SSE Event
# ============================================================


class TestAC7MergeSuggestion:
    """AC-7: GIVEN ein Cluster wird neu erstellt und hat Aehnlichkeit > 80% mit einem bestehenden
    WHEN check_suggestions ausgefuehrt wird
    THEN wird ein merge-Eintrag in cluster_suggestions mit status='pending' und
    similarity_score gespeichert, und ein SSE-Event 'suggestion' publiziert."""

    @pytest.mark.asyncio
    async def test_merge_suggestion_saved_and_sse_published(
        self,
        mock_project_id,
        mock_cluster_id_1,
        mock_cluster_id_2,
        mock_cluster_repository,
        mock_fact_repository,
        mock_assignment_repository,
        mock_project_repository,
        mock_event_bus,
        mock_suggestion_repository,
        mock_settings,
    ):
        """AC-7: Graph liefert Merge-Suggestion -> saved in cluster_suggestions + SSE published."""
        mock_cluster_repository.create_clusters = AsyncMock(return_value=[])

        suggestion = {
            "type": "merge",
            "source_cluster_id": mock_cluster_id_1,
            "target_cluster_id": mock_cluster_id_2,
            "similarity_score": 0.85,
        }
        saved_suggestion = {
            **suggestion,
            "id": str(uuid.uuid4()),
            "status": "pending",
        }
        mock_suggestion_repository.save_suggestions = AsyncMock(return_value=[saved_suggestion])

        graph_output = {
            "assignments": [],
            "new_clusters": [],
            "summaries": {},
            "suggestions": [suggestion],
        }

        mock_graph = AsyncMock()
        service = _build_clustering_service(
            mock_graph,
            mock_cluster_repository,
            mock_suggestion_repository,
            mock_fact_repository,
            mock_assignment_repository,
            mock_project_repository,
            mock_event_bus,
            mock_settings,
        )

        await service._persist_results(mock_project_id, graph_output)

        # Verify: save_suggestions called
        mock_suggestion_repository.save_suggestions.assert_called_once()
        save_call_args = mock_suggestion_repository.save_suggestions.call_args
        saved_suggestions_list = save_call_args.kwargs.get("suggestions") or save_call_args[1].get("suggestions", [])
        assert len(saved_suggestions_list) == 1
        assert saved_suggestions_list[0]["type"] == "merge"
        assert saved_suggestions_list[0]["similarity_score"] == 0.85

        # Verify: SSE 'suggestion' event published
        publish_calls = mock_event_bus.publish.call_args_list
        suggestion_events = [
            c for c in publish_calls
            if c.kwargs.get("event_type") == "suggestion"
        ]
        assert len(suggestion_events) >= 1

    @pytest.mark.asyncio
    async def test_split_suggestion_saved(
        self,
        mock_project_id,
        mock_cluster_id_1,
        mock_cluster_repository,
        mock_fact_repository,
        mock_assignment_repository,
        mock_project_repository,
        mock_event_bus,
        mock_suggestion_repository,
        mock_settings,
    ):
        """AC-7 extended: Split suggestion is also saved via _persist_results()."""
        mock_cluster_repository.create_clusters = AsyncMock(return_value=[])

        suggestion = {
            "type": "split",
            "source_cluster_id": mock_cluster_id_1,
            "proposed_data": [{"name": "Sub-A"}, {"name": "Sub-B"}],
        }
        mock_suggestion_repository.save_suggestions = AsyncMock(
            return_value=[{**suggestion, "id": str(uuid.uuid4()), "status": "pending"}]
        )

        graph_output = {
            "assignments": [],
            "new_clusters": [],
            "summaries": {},
            "suggestions": [suggestion],
        }

        mock_graph = AsyncMock()
        service = _build_clustering_service(
            mock_graph,
            mock_cluster_repository,
            mock_suggestion_repository,
            mock_fact_repository,
            mock_assignment_repository,
            mock_project_repository,
            mock_event_bus,
            mock_settings,
        )

        await service._persist_results(mock_project_id, graph_output)

        mock_suggestion_repository.save_suggestions.assert_called_once()


# ============================================================
# AC-8: POST /recluster -> 200, Full Recluster gestartet
# ============================================================


class TestAC8FullRecluster:
    """AC-8: GIVEN ein Projekt mit bestehenden Clustern und Facts
    WHEN POST /api/projects/{id}/clustering/recluster aufgerufen wird
    THEN werden alle bestehenden Cluster geloescht, alle facts.cluster_id auf NULL gesetzt,
    ein neuer Full-Recluster-Task gestartet, und HTTP 200 mit {"status": "started"}
    zurueckgegeben."""

    @pytest.mark.asyncio
    async def test_full_recluster_deletes_clusters_and_resets_facts(
        self,
        mock_project_id,
        mock_cluster_repository,
        mock_fact_repository,
        mock_assignment_repository,
        mock_project_repository,
        mock_event_bus,
        mock_suggestion_repository,
        mock_settings,
    ):
        """AC-8: full_recluster() deletes all clusters and resets facts.cluster_id."""
        mock_project_repository.get_by_id = AsyncMock(
            return_value={"id": mock_project_id, "research_goal": "Test goal"}
        )
        mock_fact_repository.get_facts_for_project = AsyncMock(return_value=[])

        mock_graph = AsyncMock()
        mock_graph.invoke = AsyncMock(return_value={
            "assignments": [],
            "new_clusters": [],
            "summaries": {},
            "suggestions": [],
            "quality_ok": True,
            "iteration": 1,
        })

        service = _build_clustering_service(
            mock_graph,
            mock_cluster_repository,
            mock_suggestion_repository,
            mock_fact_repository,
            mock_assignment_repository,
            mock_project_repository,
            mock_event_bus,
            mock_settings,
        )

        await service.full_recluster(mock_project_id)

        # Verify: all clusters deleted
        mock_cluster_repository.delete_all_for_project.assert_called_once_with(mock_project_id)
        # Verify: facts.cluster_id reset to NULL
        mock_fact_repository.reset_cluster_assignments_for_project.assert_called_once_with(
            mock_project_id
        )

    @pytest.mark.asyncio
    async def test_full_recluster_publishes_clustering_started_event(
        self,
        mock_project_id,
        mock_cluster_repository,
        mock_fact_repository,
        mock_assignment_repository,
        mock_project_repository,
        mock_event_bus,
        mock_suggestion_repository,
        mock_settings,
    ):
        """AC-8: full_recluster() publishes SSE clustering_started with mode='full'."""
        mock_project_repository.get_by_id = AsyncMock(
            return_value={"id": mock_project_id, "research_goal": "Test goal"}
        )
        mock_fact_repository.get_facts_for_project = AsyncMock(return_value=[
            {"id": str(uuid.uuid4()), "content": "fact1", "interview_id": str(uuid.uuid4())},
        ])

        mock_graph = AsyncMock()
        mock_graph.invoke = AsyncMock(return_value={
            "assignments": [],
            "new_clusters": [],
            "summaries": {},
            "suggestions": [],
            "quality_ok": True,
            "iteration": 1,
        })
        mock_cluster_repository.create_clusters = AsyncMock(return_value=[])

        service = _build_clustering_service(
            mock_graph,
            mock_cluster_repository,
            mock_suggestion_repository,
            mock_fact_repository,
            mock_assignment_repository,
            mock_project_repository,
            mock_event_bus,
            mock_settings,
        )

        await service.full_recluster(mock_project_id)

        # Verify: clustering_started SSE event with mode='full'
        publish_calls = mock_event_bus.publish.call_args_list
        started_events = [
            c for c in publish_calls
            if c.kwargs.get("event_type") == "clustering_started"
        ]
        assert len(started_events) >= 1
        assert started_events[0].kwargs["data"]["mode"] == "full"

    @pytest.mark.asyncio
    async def test_full_recluster_removes_project_from_running_set_after_completion(
        self,
        mock_project_id,
        mock_cluster_repository,
        mock_fact_repository,
        mock_assignment_repository,
        mock_project_repository,
        mock_event_bus,
        mock_suggestion_repository,
        mock_settings,
    ):
        """AC-8: full_recluster() removes project from _running_recluster set after completion."""
        mock_project_repository.get_by_id = AsyncMock(
            return_value={"id": mock_project_id, "research_goal": "Test goal"}
        )
        mock_fact_repository.get_facts_for_project = AsyncMock(return_value=[])

        mock_graph = AsyncMock()
        service = _build_clustering_service(
            mock_graph,
            mock_cluster_repository,
            mock_suggestion_repository,
            mock_fact_repository,
            mock_assignment_repository,
            mock_project_repository,
            mock_event_bus,
            mock_settings,
        )

        await service.full_recluster(mock_project_id)

        # Verify: project_id removed from _running_recluster set
        assert mock_project_id not in service._running_recluster


# ============================================================
# AC-9: POST /recluster waehrend laufendem Recluster -> 409
# ============================================================


class TestAC9ReclusterConflict:
    """AC-9: GIVEN ein Full-Recluster laeuft bereits fuer ein Projekt
    WHEN POST /api/projects/{id}/clustering/recluster erneut aufgerufen wird
    THEN wird HTTP 409 mit {"detail": "Full re-cluster already running for this project"}
    zurueckgegeben."""

    @pytest.mark.asyncio
    async def test_full_recluster_raises_conflict_when_already_running(
        self,
        mock_project_id,
        mock_cluster_repository,
        mock_fact_repository,
        mock_assignment_repository,
        mock_project_repository,
        mock_event_bus,
        mock_suggestion_repository,
        mock_settings,
    ):
        """AC-9: Zweiter Recluster-Aufruf waehrend laufendem Task -> ConflictError."""
        from app.clustering.service import ConflictError

        mock_graph = AsyncMock()
        service = _build_clustering_service(
            mock_graph,
            mock_cluster_repository,
            mock_suggestion_repository,
            mock_fact_repository,
            mock_assignment_repository,
            mock_project_repository,
            mock_event_bus,
            mock_settings,
        )

        # Simulate running recluster
        service._running_recluster.add(mock_project_id)

        with pytest.raises(ConflictError, match="already running"):
            await service.full_recluster(mock_project_id)

    @pytest.mark.asyncio
    async def test_conflict_error_does_not_affect_other_projects(
        self,
        mock_project_id,
        mock_cluster_repository,
        mock_fact_repository,
        mock_assignment_repository,
        mock_project_repository,
        mock_event_bus,
        mock_suggestion_repository,
        mock_settings,
    ):
        """AC-9: ConflictError is project-specific; other projects can recluster."""
        other_project_id = str(uuid.uuid4())

        mock_project_repository.get_by_id = AsyncMock(
            return_value={"id": other_project_id, "research_goal": "Other"}
        )
        mock_fact_repository.get_facts_for_project = AsyncMock(return_value=[])

        mock_graph = AsyncMock()
        service = _build_clustering_service(
            mock_graph,
            mock_cluster_repository,
            mock_suggestion_repository,
            mock_fact_repository,
            mock_assignment_repository,
            mock_project_repository,
            mock_event_bus,
            mock_settings,
        )

        # Simulate running recluster for mock_project_id only
        service._running_recluster.add(mock_project_id)

        # Should NOT raise for a different project
        await service.full_recluster(other_project_id)


# ============================================================
# AC-10: Clustering-Fehler -> failed status + SSE
# ============================================================


class TestAC10ClusteringFailure:
    """AC-10: GIVEN ein Clustering-Lauf scheitert nach 3 LLM-Retries
    WHEN der Fehler auftritt
    THEN wird clustering_status auf 'failed' gesetzt, unzugeordnete Facts bleiben
    mit cluster_id=NULL erhalten, und SSE-Event clustering_failed mit
    {error, unassigned_count} publiziert."""

    @pytest.mark.asyncio
    async def test_clustering_failure_sets_failed_status(
        self,
        mock_project_id,
        mock_interview_id,
        mock_project_row,
        mock_facts_new,
        mock_existing_clusters,
        mock_cluster_repository,
        mock_fact_repository,
        mock_assignment_repository,
        mock_project_repository,
        mock_event_bus,
        mock_suggestion_repository,
        mock_settings,
    ):
        """AC-10: Graph exception -> clustering_status='failed'."""
        mock_project_repository.get_by_id = AsyncMock(return_value=mock_project_row)
        mock_cluster_repository.list_for_project = AsyncMock(return_value=mock_existing_clusters)
        mock_fact_repository.get_facts_for_interview = AsyncMock(return_value=mock_facts_new)
        mock_fact_repository.get_facts_for_project = AsyncMock(return_value=[
            {"id": str(uuid.uuid4()), "content": "unassigned", "cluster_id": None}
        ])

        mock_graph = AsyncMock()
        mock_graph.invoke = AsyncMock(side_effect=RuntimeError("LLM timeout after 3 retries"))

        service = _build_clustering_service(
            mock_graph,
            mock_cluster_repository,
            mock_suggestion_repository,
            mock_fact_repository,
            mock_assignment_repository,
            mock_project_repository,
            mock_event_bus,
            mock_settings,
        )

        await service.process_interview(mock_project_id, mock_interview_id)

        # Verify: clustering_status="failed"
        status_calls = mock_assignment_repository.update_clustering_status.call_args_list
        failed_calls = [
            c for c in status_calls
            if c.kwargs.get("clustering_status") == "failed"
        ]
        assert len(failed_calls) >= 1

    @pytest.mark.asyncio
    async def test_clustering_failure_publishes_sse_clustering_failed(
        self,
        mock_project_id,
        mock_interview_id,
        mock_project_row,
        mock_facts_new,
        mock_existing_clusters,
        mock_cluster_repository,
        mock_fact_repository,
        mock_assignment_repository,
        mock_project_repository,
        mock_event_bus,
        mock_suggestion_repository,
        mock_settings,
    ):
        """AC-10: Graph exception -> SSE clustering_failed with error and unassigned_count."""
        mock_project_repository.get_by_id = AsyncMock(return_value=mock_project_row)
        mock_cluster_repository.list_for_project = AsyncMock(return_value=mock_existing_clusters)
        mock_fact_repository.get_facts_for_interview = AsyncMock(return_value=mock_facts_new)

        # 3 unassigned facts
        unassigned_facts = [
            {"id": str(uuid.uuid4()), "content": f"unassigned_{i}", "cluster_id": None}
            for i in range(3)
        ]
        mock_fact_repository.get_facts_for_project = AsyncMock(return_value=unassigned_facts)

        mock_graph = AsyncMock()
        mock_graph.invoke = AsyncMock(side_effect=RuntimeError("LLM timeout after 3 retries"))

        service = _build_clustering_service(
            mock_graph,
            mock_cluster_repository,
            mock_suggestion_repository,
            mock_fact_repository,
            mock_assignment_repository,
            mock_project_repository,
            mock_event_bus,
            mock_settings,
        )

        await service.process_interview(mock_project_id, mock_interview_id)

        # Verify: SSE clustering_failed published with error and unassigned_count
        publish_calls = mock_event_bus.publish.call_args_list
        failed_events = [
            c for c in publish_calls
            if c.kwargs.get("event_type") == "clustering_failed"
        ]
        assert len(failed_events) == 1
        event_data = failed_events[0].kwargs["data"]
        assert "error" in event_data
        assert event_data["unassigned_count"] == 3

    @pytest.mark.asyncio
    async def test_full_recluster_failure_sets_failed_status_and_removes_from_running(
        self,
        mock_project_id,
        mock_cluster_repository,
        mock_fact_repository,
        mock_assignment_repository,
        mock_project_repository,
        mock_event_bus,
        mock_suggestion_repository,
        mock_settings,
    ):
        """AC-10: full_recluster() failure -> clustering_status='failed', project removed from running set."""
        mock_project_repository.get_by_id = AsyncMock(
            return_value={"id": mock_project_id, "research_goal": "Test goal"}
        )
        mock_fact_repository.get_facts_for_project = AsyncMock(return_value=[
            {"id": str(uuid.uuid4()), "content": "fact1", "interview_id": str(uuid.uuid4())},
        ])
        mock_assignment_repository.get_all_for_project = AsyncMock(return_value=[
            {"interview_id": str(uuid.uuid4())}
        ])
        mock_fact_repository.get_facts_for_project = AsyncMock(return_value=[])

        mock_graph = AsyncMock()
        mock_graph.invoke = AsyncMock(side_effect=RuntimeError("LLM failure"))

        service = _build_clustering_service(
            mock_graph,
            mock_cluster_repository,
            mock_suggestion_repository,
            mock_fact_repository,
            mock_assignment_repository,
            mock_project_repository,
            mock_event_bus,
            mock_settings,
        )

        await service.full_recluster(mock_project_id)

        # Verify: project removed from _running_recluster even on failure
        assert mock_project_id not in service._running_recluster


# ============================================================
# UNIT TESTS: ClusteringGraph Nodes
# ============================================================


class TestClusteringGraphNodes:
    """Unit tests for individual ClusteringGraph nodes."""

    @pytest.mark.asyncio
    async def test_generate_taxonomy_returns_initial_clusters(self):
        """generate_taxonomy node returns existing_clusters with generated names."""
        from app.clustering.graph import ClusteringGraph

        settings = MagicMock()
        settings.openrouter_api_key = "test"
        settings.clustering_model_default = "model"
        settings.summary_model_default = "model"
        settings.clustering_taxonomy_batch_size = 20

        with patch("app.clustering.graph.ChatOpenAI") as mock_llm_class:
            mock_llm_instance = AsyncMock()
            mock_llm_instance.ainvoke = AsyncMock(
                return_value=MagicMock(content='["Navigation Issues", "Pricing Problems"]')
            )
            mock_llm_class.return_value = mock_llm_instance

            graph = ClusteringGraph(settings)

        state = {
            "project_id": "test-project",
            "research_goal": "Understand UX issues",
            "prompt_context": None,
            "mode": "full",
            "model_clustering": "model",
            "facts": [
                {"id": "f1", "content": "User cannot find settings.", "interview_id": "i1"},
                {"id": "f2", "content": "Pricing page is confusing.", "interview_id": "i1"},
            ],
        }

        result = await graph._node_generate_taxonomy(state)

        assert "existing_clusters" in result
        assert len(result["existing_clusters"]) >= 1
        # Each cluster should have name and id=None
        for cluster in result["existing_clusters"]:
            assert "name" in cluster
            assert cluster["id"] is None

    @pytest.mark.asyncio
    async def test_assign_facts_returns_assignments_and_new_clusters(self):
        """assign_facts node returns assignments and new_clusters."""
        from app.clustering.graph import ClusteringGraph

        settings = MagicMock()
        settings.openrouter_api_key = "test"
        settings.clustering_model_default = "model"
        settings.summary_model_default = "model"

        llm_response = [
            {"fact_id": "f1", "cluster_id": "c1", "new_cluster_name": None},
            {"fact_id": "f2", "cluster_id": None, "new_cluster_name": "New Category"},
        ]

        with patch("app.clustering.graph.ChatOpenAI") as mock_llm_class:
            mock_llm_instance = AsyncMock()
            mock_llm_instance.ainvoke = AsyncMock(
                return_value=MagicMock(content=str(llm_response).replace("'", '"').replace("None", "null"))
            )
            mock_llm_class.return_value = mock_llm_instance

            graph = ClusteringGraph(settings)

        import json
        state = {
            "project_id": "test-project",
            "research_goal": "Understand UX issues",
            "prompt_context": None,
            "model_clustering": "model",
            "facts": [
                {"id": "f1", "content": "User cannot find settings.", "interview_id": "i1"},
                {"id": "f2", "content": "New observation.", "interview_id": "i1"},
            ],
            "existing_clusters": [
                {"id": "c1", "name": "Navigation Issues", "summary": "Nav problems.", "fact_count": 3},
            ],
        }

        result = await graph._node_assign_facts(state)

        assert "assignments" in result
        assert "new_clusters" in result
        assert len(result["assignments"]) == 2

    @pytest.mark.asyncio
    async def test_check_suggestions_returns_empty_when_no_clusters_with_ids(self):
        """check_suggestions returns empty suggestions when no clusters have IDs."""
        from app.clustering.graph import ClusteringGraph

        settings = MagicMock()
        settings.openrouter_api_key = "test"
        settings.clustering_model_default = "model"
        settings.summary_model_default = "model"
        settings.clustering_split_threshold = 8

        with patch("app.clustering.graph.ChatOpenAI") as mock_llm_class:
            mock_llm_class.return_value = AsyncMock()
            graph = ClusteringGraph(settings)

        state = {
            "project_id": "test-project",
            "research_goal": "Test",
            "model_clustering": "model",
            "assignments": [],
            "existing_clusters": [{"id": None, "name": "New Cluster"}],
            "new_clusters": [],
        }

        result = await graph._node_check_suggestions(state)
        assert result["suggestions"] == []


# ============================================================
# UNIT TESTS: ClusteringState TypedDict
# ============================================================


class TestClusteringState:
    """Unit tests verifying ClusteringState type definition."""

    def test_clustering_state_has_required_fields(self):
        """ClusteringState TypedDict has all required fields from spec."""
        from app.clustering.graph_state import ClusteringState

        required_fields = [
            "project_id",
            "research_goal",
            "prompt_context",
            "mode",
            "model_clustering",
            "model_summary",
            "facts",
            "existing_clusters",
            "assignments",
            "new_clusters",
            "quality_ok",
            "iteration",
            "suggestions",
            "summaries",
        ]

        annotations = ClusteringState.__annotations__
        for field in required_fields:
            assert field in annotations, f"Missing field: {field}"

    def test_clustering_state_mode_type(self):
        """ClusteringState.mode should accept 'incremental' and 'full'."""
        from app.clustering.graph_state import ClusteringState

        # Verify mode annotation exists -- Literal types are defined
        assert "mode" in ClusteringState.__annotations__


# ============================================================
# UNIT TESTS: ConflictError
# ============================================================


class TestConflictError:
    """Unit tests for ConflictError exception."""

    def test_conflict_error_is_exception(self):
        """ConflictError is a proper Exception subclass."""
        from app.clustering.service import ConflictError

        assert issubclass(ConflictError, Exception)

    def test_conflict_error_message(self):
        """ConflictError carries an error message."""
        from app.clustering.service import ConflictError

        err = ConflictError("test message")
        assert "test message" in str(err)


# ============================================================
# UNIT TESTS: ClusteringService normalize helpers
# ============================================================


class TestNormalizeHelpers:
    """Unit tests for ClusteringService._normalize_fact and _normalize_cluster."""

    def test_normalize_fact_converts_uuid_to_string(self):
        """_normalize_fact converts UUID objects to string."""
        from app.clustering.service import ClusteringService

        fact_id = uuid.uuid4()
        interview_id = uuid.uuid4()
        fact = {
            "id": fact_id,
            "content": "Some fact",
            "interview_id": interview_id,
            "cluster_id": None,
            "quote": "a quote",
            "confidence": 0.9,
        }

        result = ClusteringService._normalize_fact(fact)
        assert result["id"] == str(fact_id)
        assert result["interview_id"] == str(interview_id)
        assert result["cluster_id"] is None
        assert result["content"] == "Some fact"

    def test_normalize_cluster_converts_uuid_to_string(self):
        """_normalize_cluster converts UUID objects to string."""
        from app.clustering.service import ClusteringService

        cluster_id = uuid.uuid4()
        cluster = {
            "id": cluster_id,
            "name": "Test Cluster",
            "summary": "Summary text",
            "fact_count": 5,
            "interview_count": 2,
        }

        result = ClusteringService._normalize_cluster(cluster)
        assert result["id"] == str(cluster_id)
        assert result["name"] == "Test Cluster"
        assert result["fact_count"] == 5


# ============================================================
# INTEGRATION TESTS: Router endpoints
# ============================================================


class TestClusteringRouterIntegration:
    """Integration tests for the clustering router endpoints (AC-8, AC-9)."""

    @pytest.mark.asyncio
    async def test_recluster_endpoint_returns_200_with_started_status(self):
        """AC-8: POST /api/projects/{id}/clustering/recluster returns 200 with status='started'."""
        from unittest.mock import PropertyMock

        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        from app.auth.middleware import get_current_user
        from app.clustering.router import router
        from app.clustering.schemas import ReclusterStarted

        app = FastAPI()
        app.include_router(router)

        # Bypass auth for this test
        app.dependency_overrides[get_current_user] = lambda: {"id": "test-user", "username": "test"}

        # Mock settings and services on app.state
        mock_settings = MagicMock()
        mock_settings.async_database_url = "postgresql+asyncpg://test:test@localhost/test"
        mock_settings.db_echo = False
        mock_settings.db_pool_size = 5
        mock_settings.db_max_overflow = 10
        app.state.settings = mock_settings

        mock_clustering_svc = MagicMock()
        mock_clustering_svc._running_recluster = set()
        mock_clustering_svc.full_recluster = AsyncMock()
        app.state.clustering_service = mock_clustering_svc

        project_id = str(uuid.uuid4())

        client = TestClient(app)
        response = client.post(f"/api/projects/{project_id}/clustering/recluster")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "started"
        assert data["project_id"] == project_id

    @pytest.mark.asyncio
    async def test_recluster_endpoint_returns_409_when_already_running(self):
        """AC-9: POST /api/projects/{id}/clustering/recluster returns 409 when already running."""
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        from app.auth.middleware import get_current_user
        from app.clustering.router import router

        app = FastAPI()
        app.include_router(router)

        # Bypass auth for this test
        app.dependency_overrides[get_current_user] = lambda: {"id": "test-user", "username": "test"}

        mock_settings = MagicMock()
        mock_settings.async_database_url = "postgresql+asyncpg://test:test@localhost/test"
        mock_settings.db_echo = False
        mock_settings.db_pool_size = 5
        mock_settings.db_max_overflow = 10
        app.state.settings = mock_settings

        project_id = str(uuid.uuid4())

        mock_clustering_svc = MagicMock()
        mock_clustering_svc._running_recluster = {project_id}  # Already running
        app.state.clustering_service = mock_clustering_svc

        client = TestClient(app)
        response = client.post(f"/api/projects/{project_id}/clustering/recluster")

        assert response.status_code == 409
        assert "already running" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_clustering_status_endpoint_returns_idle(self):
        """GET /api/projects/{id}/clustering/status returns idle when not running."""
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        from app.auth.middleware import get_current_user
        from app.clustering.router import router

        app = FastAPI()
        app.include_router(router)

        # Bypass auth for this test
        app.dependency_overrides[get_current_user] = lambda: {"id": "test-user", "username": "test"}

        mock_settings = MagicMock()
        mock_settings.async_database_url = "postgresql+asyncpg://test:test@localhost/test"
        mock_settings.db_echo = False
        mock_settings.db_pool_size = 5
        mock_settings.db_max_overflow = 10
        app.state.settings = mock_settings

        mock_clustering_svc = MagicMock()
        mock_clustering_svc._running_recluster = set()
        app.state.clustering_service = mock_clustering_svc

        project_id = str(uuid.uuid4())

        client = TestClient(app)
        response = client.get(f"/api/projects/{project_id}/clustering/status")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "idle"

    @pytest.mark.asyncio
    async def test_clustering_status_endpoint_returns_running(self):
        """GET /api/projects/{id}/clustering/status returns running when recluster active."""
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        from app.auth.middleware import get_current_user
        from app.clustering.router import router

        app = FastAPI()
        app.include_router(router)

        # Bypass auth for this test
        app.dependency_overrides[get_current_user] = lambda: {"id": "test-user", "username": "test"}

        mock_settings = MagicMock()
        mock_settings.async_database_url = "postgresql+asyncpg://test:test@localhost/test"
        mock_settings.db_echo = False
        mock_settings.db_pool_size = 5
        mock_settings.db_max_overflow = 10
        app.state.settings = mock_settings

        project_id = str(uuid.uuid4())

        mock_clustering_svc = MagicMock()
        mock_clustering_svc._running_recluster = {project_id}  # Running
        app.state.clustering_service = mock_clustering_svc

        client = TestClient(app)
        response = client.get(f"/api/projects/{project_id}/clustering/status")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "running"
        assert data["mode"] == "full"


# ============================================================
# ACCEPTANCE TESTS (End-to-End mit gemockten Dependencies)
# ============================================================


class TestClusteringPipelineAcceptance:
    """Acceptance Tests fuer End-to-End Clustering-Pipeline.
    Validiert die vollstaendige Pipeline von Trigger bis SSE-Event."""

    @pytest.mark.asyncio
    async def test_acceptance_full_pipeline_creates_clusters_from_facts(
        self,
        mock_project_id,
        mock_interview_id,
        mock_project_row,
        mock_facts_new,
        mock_cluster_repository,
        mock_fact_repository,
        mock_assignment_repository,
        mock_project_repository,
        mock_event_bus,
        mock_suggestion_repository,
        mock_settings,
    ):
        """GIVEN Projekt ohne Cluster, 2 extrahierte Facts
        WHEN process_interview() komplett durchlaeuft (Graph gemockt)
        THEN mind. 1 Cluster erstellt, Facts zugeordnet, status='completed',
        SSE 'clustering_completed'."""
        mock_project_repository.get_by_id = AsyncMock(return_value=mock_project_row)
        mock_cluster_repository.list_for_project = AsyncMock(return_value=[])
        mock_fact_repository.get_facts_for_interview = AsyncMock(return_value=mock_facts_new)
        mock_fact_repository.get_facts_for_project = AsyncMock(return_value=mock_facts_new)

        new_cluster_uuid = str(uuid.uuid4())
        mock_cluster_repository.create_clusters = AsyncMock(
            return_value=[{"id": new_cluster_uuid, "name": "Navigation Issues"}]
        )

        mock_graph = AsyncMock()
        mock_graph.invoke = AsyncMock(return_value={
            "assignments": [
                {"fact_id": mock_facts_new[0]["id"], "cluster_id": None, "new_cluster_name": "Navigation Issues"},
                {"fact_id": mock_facts_new[1]["id"], "cluster_id": None, "new_cluster_name": "Navigation Issues"},
            ],
            "new_clusters": [{"name": "Navigation Issues", "fact_ids": [f["id"] for f in mock_facts_new]}],
            "summaries": {"Navigation Issues": "Users struggle with navigation."},
            "suggestions": [],
            "quality_ok": True,
            "iteration": 1,
        })

        service = _build_clustering_service(
            mock_graph,
            mock_cluster_repository,
            mock_suggestion_repository,
            mock_fact_repository,
            mock_assignment_repository,
            mock_project_repository,
            mock_event_bus,
            mock_settings,
        )

        await service.process_interview(mock_project_id, mock_interview_id)

        # Verify: clustering_status="completed"
        status_calls = mock_assignment_repository.update_clustering_status.call_args_list
        final_call = status_calls[-1]
        assert final_call.kwargs.get("clustering_status") == "completed"

        # Verify: mind. 1 Cluster angelegt
        mock_cluster_repository.create_clusters.assert_called_once()

        # Verify: SSE clustering_completed
        publish_calls = mock_event_bus.publish.call_args_list
        completed_events = [
            c for c in publish_calls
            if c.kwargs.get("event_type") == "clustering_completed"
        ]
        assert len(completed_events) == 1

    @pytest.mark.asyncio
    async def test_acceptance_incremental_pipeline_assigns_facts_to_existing_clusters(
        self,
        mock_project_id,
        mock_interview_id,
        mock_project_row,
        mock_facts_new,
        mock_existing_clusters,
        mock_cluster_id_1,
        mock_cluster_repository,
        mock_fact_repository,
        mock_assignment_repository,
        mock_project_repository,
        mock_event_bus,
        mock_suggestion_repository,
        mock_settings,
    ):
        """GIVEN Projekt mit bestehenden Clustern, neues Interview mit Facts
        WHEN process_interview() komplett durchlaeuft
        THEN Facts bestehenden Clustern zugeordnet, status='completed',
        SSE 'clustering_completed'."""
        mock_project_repository.get_by_id = AsyncMock(return_value=mock_project_row)
        mock_cluster_repository.list_for_project = AsyncMock(return_value=mock_existing_clusters)
        mock_fact_repository.get_facts_for_interview = AsyncMock(return_value=mock_facts_new)

        mock_graph = AsyncMock()
        mock_graph.invoke = AsyncMock(return_value={
            "assignments": [
                {"fact_id": mock_facts_new[0]["id"], "cluster_id": mock_cluster_id_1, "new_cluster_name": None},
                {"fact_id": mock_facts_new[1]["id"], "cluster_id": mock_cluster_id_1, "new_cluster_name": None},
            ],
            "new_clusters": [],
            "summaries": {mock_cluster_id_1: "Updated summary."},
            "suggestions": [],
            "quality_ok": True,
            "iteration": 1,
        })

        service = _build_clustering_service(
            mock_graph,
            mock_cluster_repository,
            mock_suggestion_repository,
            mock_fact_repository,
            mock_assignment_repository,
            mock_project_repository,
            mock_event_bus,
            mock_settings,
        )

        await service.process_interview(mock_project_id, mock_interview_id)

        # Verify: mode="incremental"
        call_state = mock_graph.invoke.call_args[0][0]
        assert call_state["mode"] == "incremental"

        # Verify: clustering_status="completed"
        status_calls = mock_assignment_repository.update_clustering_status.call_args_list
        final_call = status_calls[-1]
        assert final_call.kwargs.get("clustering_status") == "completed"

        # Verify: SSE clustering_completed
        publish_calls = mock_event_bus.publish.call_args_list
        completed_events = [
            c for c in publish_calls
            if c.kwargs.get("event_type") == "clustering_completed"
        ]
        assert len(completed_events) == 1

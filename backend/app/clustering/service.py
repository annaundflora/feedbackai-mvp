"""ClusteringService -- Orchestriert die Clustering-Pipeline.

Wird direkt von FactExtractionService via Dependency-Injection aufgerufen
(DI-Trigger: FactExtractionService._clustering_service.process_interview via asyncio.create_task).
Schreibt Ergebnisse in DB via Repositories.
Publiziert clustering_started, clustering_completed, clustering_failed Events.

Pattern: Identisch mit FactExtractionService aus Slice 2.
Background-Tasks via asyncio.create_task().
"""
import asyncio
import logging
from typing import Any

from app.clustering.cluster_repository import ClusterRepository
from app.clustering.cluster_suggestion_repository import ClusterSuggestionRepository
from app.clustering.events import SseEventBus
from app.clustering.fact_repository import FactRepository
from app.clustering.graph import ClusteringGraph
from app.clustering.graph_state import ClusteringState
from app.clustering.interview_assignment_repository import InterviewAssignmentRepository
from app.clustering.project_repository import ProjectRepository

logger = logging.getLogger(__name__)

SPLIT_SUGGESTION_THRESHOLD = 8  # Facts je Cluster -> Split-Vorschlag


class ConflictError(Exception):
    """Raised when a recluster operation is already running for the project."""

    pass


class ClusteringService:
    """Orchestriert die Clustering-Pipeline (inkrementell + Full Re-Cluster).

    Wird direkt von FactExtractionService via Dependency-Injection aufgerufen
    (DI-Trigger: FactExtractionService._clustering_service.process_interview via asyncio.create_task).
    Schreibt Ergebnisse in DB via Repositories.
    Publiziert clustering_started, clustering_completed, clustering_failed Events.

    Pattern: Identisch mit FactExtractionService aus Slice 2.
    Background-Tasks via asyncio.create_task().
    """

    def __init__(
        self,
        clustering_graph: ClusteringGraph,
        cluster_repository: ClusterRepository,
        cluster_suggestion_repository: ClusterSuggestionRepository,
        fact_repository: FactRepository,
        assignment_repository: InterviewAssignmentRepository,
        project_repository: ProjectRepository,
        event_bus: SseEventBus,
        settings: Any,
    ) -> None:
        self._graph = clustering_graph
        self._cluster_repo = cluster_repository
        self._suggestion_repo = cluster_suggestion_repository
        self._fact_repo = fact_repository
        self._assignment_repo = assignment_repository
        self._project_repo = project_repository
        self._event_bus = event_bus
        self._settings = settings
        # Laufende Full-Recluster-Tasks pro Projekt (verhindert parallele Laeufe: 409)
        # Instance-level set (NICHT class-level)
        self._running_recluster: set[str] = set()
        # Per-project Lock: serialisiert process_interview Aufrufe damit
        # nicht alle gleichzeitig existing_clusters_count=0 sehen und
        # jeweils eigene Cluster erstellen (Race Condition Fix)
        self._project_locks: dict[str, asyncio.Lock] = {}

    def _get_project_lock(self, project_id: str) -> asyncio.Lock:
        """Gibt den per-project Lock zurueck (erstellt ihn lazy)."""
        if project_id not in self._project_locks:
            self._project_locks[project_id] = asyncio.Lock()
        return self._project_locks[project_id]

    async def process_interview(
        self,
        project_id: str,
        interview_id: str,
    ) -> None:
        """Orchestriert inkrementelles Clustering nach Fact Extraction.

        Wird von FactExtractionService nach erfolgreicher Extraktion aufgerufen.
        Laeuft als asyncio.create_task() (non-blocking).

        Verwendet per-project Lock um Race Conditions zu vermeiden:
        Ohne Lock sehen alle gleichzeitigen Tasks existing_clusters_count=0
        und erstellen jeweils eigene Cluster-Sets (N Interviews -> N*K Cluster).

        Logik:
        - Bestehende Cluster laden
        - Falls keine Cluster vorhanden -> mode="full" (Erstes Interview des Projekts)
        - Sonst -> mode="incremental"
        - ClusteringGraph ausfuehren
        - Ergebnisse persistieren
        - clustering_status aktualisieren
        - SSE-Events publizieren
        """
        import time as _time
        _start_ts = _time.monotonic()
        logger.info(f"[process_interview] START interview={interview_id} project={project_id}")

        lock = self._get_project_lock(project_id)
        async with lock:
            await self._process_interview_locked(project_id, interview_id, _start_ts)

    async def _process_interview_locked(
        self,
        project_id: str,
        interview_id: str,
        _start_ts: float,
    ) -> None:
        """Interne Implementierung von process_interview (unter Lock)."""
        import time as _time

        try:
            # Projekt-Konfiguration laden
            project = await self._project_repo.get_by_id_internal(project_id)
            if not project:
                logger.error(f"Project {project_id} not found for clustering")
                return

            research_goal = project.get("research_goal", "")
            prompt_context = project.get("prompt_context")
            model_clustering = project.get("model_clustering") or getattr(
                self._settings, "clustering_model_default", "anthropic/claude-sonnet-4"
            )
            model_summary = project.get("model_summary") or getattr(
                self._settings, "summary_model_default", "anthropic/claude-haiku-4"
            )

            # clustering_status -> "running"
            await self._assignment_repo.update_clustering_status(
                interview_id=interview_id,
                clustering_status="running",
            )

            # Bestehende Cluster laden
            existing_clusters = await self._cluster_repo.list_for_project(project_id)
            logger.debug(
                f"[process_interview] interview={interview_id} | "
                f"existing_clusters_count={len(existing_clusters)} | "
                f"cluster_ids={[str(c.get('id','?')) for c in existing_clusters[:5]]}"
            )

            # Facts des Interviews laden
            new_facts = await self._fact_repo.get_facts_for_interview(project_id, interview_id)
            logger.debug(
                f"[process_interview] interview={interview_id} | "
                f"new_facts_count={len(new_facts)}"
            )

            if not new_facts:
                logger.warning(f"No facts found for interview {interview_id}, skipping clustering")
                await self._assignment_repo.update_clustering_status(
                    interview_id=interview_id,
                    clustering_status="completed",
                )
                return

            # Mode bestimmen: full wenn keine Cluster vorhanden, sonst incremental
            if len(existing_clusters) == 0:
                mode = "full"
                # Alle Facts des Projekts laden fuer Full-Modus
                facts = await self._fact_repo.get_facts_for_project(project_id)
                # Konvertiere Row-Dicts zu str-Keys
                facts = [self._normalize_fact(f) for f in facts]
                logger.info(
                    f"[process_interview] interview={interview_id} | mode=full | "
                    f"total_project_facts={len(facts)} | "
                    f"(serialized via per-project lock)"
                )
            else:
                mode = "incremental"
                facts = [self._normalize_fact(f) for f in new_facts]
                existing_clusters = [self._normalize_cluster(c) for c in existing_clusters]
                logger.info(
                    f"[process_interview] interview={interview_id} | mode=incremental | "
                    f"new_facts={len(facts)} | existing_clusters={len(existing_clusters)}"
                )

            # SSE: clustering_started
            await self._event_bus.publish(
                project_id=project_id,
                event_type="clustering_started",
                data={"mode": mode},
            )

            # SSE: clustering_progress (extracting step)
            # Zaehle wie viele Interviews bereits geclustert wurden
            all_assignments = await self._assignment_repo.get_all_for_project(project_id)
            completed_interviews = sum(
                1 for a in all_assignments
                if a.get("clustering_status") in ("completed", "running")
            )
            total_interviews = len(all_assignments)
            await self._event_bus.publish(
                project_id=project_id,
                event_type="clustering_progress",
                data={
                    "interview_id": interview_id,
                    "step": "extracting",
                    "completed": max(0, completed_interviews - 1),
                    "total": total_interviews,
                },
            )

            # Initialzustand fuer ClusteringGraph
            initial_state: ClusteringState = {
                "project_id": project_id,
                "research_goal": research_goal,
                "prompt_context": prompt_context,
                "mode": mode,
                "model_clustering": model_clustering,
                "model_summary": model_summary,
                "facts": facts,
                "existing_clusters": existing_clusters if mode == "incremental" else [],
                "assignments": [],
                "new_clusters": [],
                "quality_ok": False,
                "iteration": 0,
                "suggestions": [],
                "summaries": {},
            }

            # SSE: clustering_progress (assigning step)
            await self._event_bus.publish(
                project_id=project_id,
                event_type="clustering_progress",
                data={
                    "interview_id": interview_id,
                    "step": "assigning",
                    "completed": len(facts),
                    "total": len(facts),
                },
            )

            # ClusteringGraph ausfuehren
            graph_output = await self._graph.invoke(initial_state)

            # SSE: clustering_progress (summarizing step)
            new_clusters_count = len(graph_output.get("new_clusters", []))
            await self._event_bus.publish(
                project_id=project_id,
                event_type="clustering_progress",
                data={
                    "interview_id": interview_id,
                    "step": "summarizing",
                    "completed": 0,
                    "total": new_clusters_count,
                },
            )

            # Ergebnisse persistieren
            await self._persist_results(
                project_id=project_id,
                graph_output=graph_output,
                interview_id=interview_id,
            )

            # clustering_status -> "completed"
            await self._assignment_repo.update_clustering_status(
                interview_id=interview_id,
                clustering_status="completed",
            )

            # Cluster-Daten fuer SSE laden
            updated_clusters = await self._cluster_repo.list_for_project(project_id)
            cluster_count = len(updated_clusters)
            fact_count = sum(c.get("fact_count", 0) for c in updated_clusters)

            # SSE: clustering_updated
            await self._event_bus.publish(
                project_id=project_id,
                event_type="clustering_updated",
                data={
                    "clusters": [
                        {
                            "id": str(c.get("id", "")),
                            "name": c.get("name", ""),
                            "fact_count": c.get("fact_count", 0),
                        }
                        for c in updated_clusters
                    ]
                },
            )

            # SSE: clustering_completed
            await self._event_bus.publish(
                project_id=project_id,
                event_type="clustering_completed",
                data={
                    "cluster_count": cluster_count,
                    "fact_count": fact_count,
                },
            )

            _elapsed = _time.monotonic() - _start_ts
            logger.info(
                f"[process_interview] DONE interview={interview_id} | "
                f"elapsed={_elapsed:.1f}s | {cluster_count} clusters | {fact_count} total facts"
            )

        except Exception as e:
            logger.error(f"Clustering failed for interview {interview_id}: {e}", exc_info=True)

            # clustering_status -> "failed"
            try:
                await self._assignment_repo.update_clustering_status(
                    interview_id=interview_id,
                    clustering_status="failed",
                )
            except Exception as status_err:
                logger.error(f"Failed to update clustering status to 'failed': {status_err}")

            # Unzugewiesene Facts zaehlen
            try:
                unassigned_facts = await self._fact_repo.get_facts_for_project(
                    project_id, unassigned_only=True
                )
                unassigned_count = len(unassigned_facts)
            except Exception:
                unassigned_count = 0

            # SSE: clustering_failed
            try:
                await self._event_bus.publish(
                    project_id=project_id,
                    event_type="clustering_failed",
                    data={
                        "error": str(e),
                        "unassigned_count": unassigned_count,
                    },
                )
            except Exception as sse_err:
                logger.error(f"Failed to publish clustering_failed SSE event: {sse_err}")

    async def full_recluster(
        self,
        project_id: str,
    ) -> None:
        """Fuehrt vollstaendiges Re-Clustering durch (destruktiv).

        - Loescht alle bestehenden Cluster und setzt facts.cluster_id = NULL
        - Ladet alle Facts des Projekts
        - ClusteringGraph mit mode="full" ausfuehren
        - Ergebnisse persistieren

        Raises:
            ConflictError: Wenn bereits ein Full-Recluster fuer dieses Projekt laeuft.
        """
        if project_id in self._running_recluster:
            raise ConflictError(f"Full re-cluster already running for project {project_id}")

        self._running_recluster.add(project_id)
        logger.info(f"Full re-cluster started for project {project_id}")

        try:
            # Projekt-Konfiguration laden
            project = await self._project_repo.get_by_id_internal(project_id)
            if not project:
                logger.error(f"Project {project_id} not found for full re-cluster")
                return

            research_goal = project.get("research_goal", "")
            prompt_context = project.get("prompt_context")
            model_clustering = project.get("model_clustering") or getattr(
                self._settings, "clustering_model_default", "anthropic/claude-sonnet-4"
            )
            model_summary = project.get("model_summary") or getattr(
                self._settings, "summary_model_default", "anthropic/claude-haiku-4"
            )

            # Alle Interviews auf clustering_status="running" setzen
            all_assignments = await self._assignment_repo.get_all_for_project(project_id)
            for assignment in all_assignments:
                interview_id = assignment.get("interview_id")
                if interview_id:
                    await self._assignment_repo.update_clustering_status(
                        interview_id=str(interview_id),
                        clustering_status="running",
                    )

            # [1] Alle Cluster loeschen, facts.cluster_id = NULL
            await self._cluster_repo.delete_all_for_project(project_id)
            await self._fact_repo.reset_cluster_assignments_for_project(project_id)

            # SSE: clustering_started(mode="full")
            await self._event_bus.publish(
                project_id=project_id,
                event_type="clustering_started",
                data={"mode": "full"},
            )

            # [2] Alle Facts des Projekts laden
            all_facts = await self._fact_repo.get_facts_for_project(project_id)
            facts = [self._normalize_fact(f) for f in all_facts]

            if not facts:
                logger.warning(f"No facts found for project {project_id}, skipping full re-cluster")
                # Alle Interviews auf "completed" setzen
                for assignment in all_assignments:
                    interview_id = assignment.get("interview_id")
                    if interview_id:
                        await self._assignment_repo.update_clustering_status(
                            interview_id=str(interview_id),
                            clustering_status="completed",
                        )
                return

            # SSE: clustering_progress (assigning step) -- zeigt ProgressIndicator im Frontend
            await self._event_bus.publish(
                project_id=project_id,
                event_type="clustering_progress",
                data={
                    "step": "assigning",
                    "completed": 0,
                    "total": len(facts),
                },
            )

            # [3] ClusteringGraph mit mode="full" ausfuehren
            initial_state: ClusteringState = {
                "project_id": project_id,
                "research_goal": research_goal,
                "prompt_context": prompt_context,
                "mode": "full",
                "model_clustering": model_clustering,
                "model_summary": model_summary,
                "facts": facts,
                "existing_clusters": [],
                "assignments": [],
                "new_clusters": [],
                "quality_ok": False,
                "iteration": 0,
                "suggestions": [],
                "summaries": {},
            }

            graph_output = await self._graph.invoke(initial_state)

            # SSE: clustering_progress (summarizing step)
            new_clusters_count = len(graph_output.get("new_clusters", []))
            await self._event_bus.publish(
                project_id=project_id,
                event_type="clustering_progress",
                data={
                    "step": "summarizing",
                    "completed": 0,
                    "total": new_clusters_count,
                },
            )

            # [4] Ergebnisse persistieren
            await self._persist_results(
                project_id=project_id,
                graph_output=graph_output,
                interview_id=None,
            )

            # Alle Interviews auf "completed" setzen
            for assignment in all_assignments:
                interview_id = assignment.get("interview_id")
                if interview_id:
                    await self._assignment_repo.update_clustering_status(
                        interview_id=str(interview_id),
                        clustering_status="completed",
                    )

            # Cluster-Daten fuer SSE laden
            updated_clusters = await self._cluster_repo.list_for_project(project_id)
            cluster_count = len(updated_clusters)
            fact_count = sum(c.get("fact_count", 0) for c in updated_clusters)

            # SSE: clustering_completed
            await self._event_bus.publish(
                project_id=project_id,
                event_type="clustering_completed",
                data={
                    "cluster_count": cluster_count,
                    "fact_count": fact_count,
                },
            )

            logger.info(
                f"Full re-cluster completed for project {project_id}: "
                f"{cluster_count} clusters, {fact_count} facts"
            )

        except Exception as e:
            logger.error(f"Full re-cluster failed for project {project_id}: {e}", exc_info=True)

            # Alle Interviews auf "failed" setzen
            try:
                all_assignments = await self._assignment_repo.get_all_for_project(project_id)
                for assignment in all_assignments:
                    interview_id = assignment.get("interview_id")
                    if interview_id:
                        await self._assignment_repo.update_clustering_status(
                            interview_id=str(interview_id),
                            clustering_status="failed",
                        )
            except Exception as status_err:
                logger.error(f"Failed to update clustering status to 'failed': {status_err}")

            # Unzugewiesene Facts zaehlen
            try:
                unassigned_facts = await self._fact_repo.get_facts_for_project(
                    project_id, unassigned_only=True
                )
                unassigned_count = len(unassigned_facts)
            except Exception:
                unassigned_count = 0

            # SSE: clustering_failed
            try:
                await self._event_bus.publish(
                    project_id=project_id,
                    event_type="clustering_failed",
                    data={
                        "error": str(e),
                        "unassigned_count": unassigned_count,
                    },
                )
            except Exception as sse_err:
                logger.error(f"Failed to publish clustering_failed SSE event: {sse_err}")

        finally:
            # Immer aus _running_recluster entfernen (Erfolg oder Fehler)
            self._running_recluster.discard(project_id)

    async def _persist_results(
        self,
        project_id: str,
        graph_output: ClusteringState,
        interview_id: str | None = None,
    ) -> None:
        """Persistiert Graph-Output in DB.

        1. Neue Cluster anlegen (INSERT INTO clusters)
        2. Fact-Zuordnungen aktualisieren (UPDATE facts SET cluster_id)
        3. Summaries aktualisieren (UPDATE clusters SET summary)
        4. Denormalisierte Zaehler aktualisieren (fact_count, interview_count)
        5. Merge/Split-Suggestions speichern
        """
        assignments = graph_output.get("assignments", [])
        new_clusters_raw = graph_output.get("new_clusters", [])
        summaries = graph_output.get("summaries", {})
        suggestions = graph_output.get("suggestions", [])

        logger.debug(
            f"[_persist_results] project={project_id} interview={interview_id} | "
            f"raw_assignments={len(assignments)} | new_clusters_raw={len(new_clusters_raw)} | "
            f"new_cluster_names={[nc.get('name','?') for nc in new_clusters_raw]}"
        )

        # Assignments aufschlüsseln: wie viele gehen zu existing vs. new clusters
        assignments_to_existing = [a for a in assignments if a.get("cluster_id") and not a.get("new_cluster_name")]
        assignments_to_new = [a for a in assignments if a.get("new_cluster_name")]
        assignments_without_cluster = [a for a in assignments if not a.get("cluster_id") and not a.get("new_cluster_name")]
        logger.debug(
            f"[_persist_results] assignments breakdown: "
            f"to_existing={len(assignments_to_existing)} | "
            f"to_new_cluster={len(assignments_to_new)} | "
            f"without_cluster={len(assignments_without_cluster)}"
        )

        # 1. Neue Cluster anlegen und UUID-Mapping aufbauen
        # name -> UUID Mapping fuer neue Cluster
        name_to_cluster_id: dict[str, str] = {}

        if new_clusters_raw:
            created_clusters = await self._cluster_repo.create_clusters(
                project_id=project_id,
                clusters=new_clusters_raw,
            )
            for created in created_clusters:
                name = created.get("name", "")
                cluster_id = str(created.get("id", ""))
                if name and cluster_id:
                    name_to_cluster_id[name] = cluster_id

        # 2. Assignments aufloesen: new_cluster_name -> cluster_id
        import uuid as _uuid
        resolved_assignments = []
        for assignment in assignments:
            fact_id = assignment.get("fact_id")
            cluster_id = assignment.get("cluster_id")
            new_cluster_name = assignment.get("new_cluster_name")

            if not fact_id:
                continue

            # LLM halluziniert manchmal Integer-IDs ("253", "369") statt UUIDs
            # Solche ungueltige fact_ids wuerden einen PostgreSQL-Fehler verursachen
            try:
                _uuid.UUID(str(fact_id))
            except (ValueError, AttributeError):
                logger.warning(f"Skipping assignment with non-UUID fact_id: {fact_id!r}")
                continue

            # new_cluster_name -> echte cluster_id aufloesen
            if cluster_id is None and new_cluster_name:
                cluster_id = name_to_cluster_id.get(new_cluster_name)
            elif cluster_id is not None:
                # Pruefen ob cluster_id eine valide UUID ist
                try:
                    _uuid.UUID(str(cluster_id))
                except ValueError:
                    # LLM hat Cluster-Namen statt UUID zurueckgegeben -> als Name aufloesen
                    resolved = name_to_cluster_id.get(str(cluster_id))
                    if resolved is None and new_cluster_name:
                        resolved = name_to_cluster_id.get(new_cluster_name)
                    if resolved is None:
                        logger.warning(f"Cannot resolve cluster_id '{cluster_id}' to UUID, skipping assignment for fact {fact_id}")
                    cluster_id = resolved

            resolved_assignments.append({
                "fact_id": str(fact_id),
                "cluster_id": str(cluster_id) if cluster_id else None,
            })

        skipped = len(assignments) - len(resolved_assignments)
        logger.debug(
            f"[_persist_results] resolved_assignments={len(resolved_assignments)} | "
            f"skipped={skipped} | "
            f"name_to_cluster_id={name_to_cluster_id}"
        )
        if resolved_assignments:
            logger.debug(
                f"[_persist_results] sample resolved_assignments (first 5): "
                f"{resolved_assignments[:5]}"
            )

        # Fact-Zuordnungen in DB aktualisieren
        if resolved_assignments:
            await self._fact_repo.update_cluster_assignments(resolved_assignments)

        # 3. Summaries aktualisieren
        for key, summary_text in summaries.items():
            # Key kann UUID sein (bestehende Cluster) oder Name (neue Cluster)
            cluster_id = None

            # Pruefe ob es eine UUID ist (bestehender Cluster)
            try:
                import uuid
                uuid.UUID(str(key))
                cluster_id = str(key)
            except ValueError:
                # Key ist ein Name -> neu angelegten Cluster-ID nachschlagen
                cluster_id = name_to_cluster_id.get(key)

            if cluster_id and summary_text:
                try:
                    await self._cluster_repo.update_summary(
                        cluster_id=cluster_id,
                        summary=summary_text,
                    )
                except Exception as e:
                    logger.warning(f"Failed to update summary for cluster {cluster_id}: {e}")

        # 4. Denormalisierte Zaehler aktualisieren
        await self._cluster_repo.update_counts_from_db(project_id)

        # 5. Suggestions speichern und SSE-Events publizieren
        if suggestions:
            saved_suggestions = await self._suggestion_repo.save_suggestions(
                project_id=project_id,
                suggestions=suggestions,
            )

            # SSE-Event fuer jede Suggestion
            for suggestion in saved_suggestions:
                try:
                    await self._event_bus.publish(
                        project_id=project_id,
                        event_type="suggestion",
                        data={
                            "type": suggestion.get("type"),
                            "source_cluster_id": str(suggestion.get("source_cluster_id", "")),
                            "target_cluster_id": str(suggestion.get("target_cluster_id", "")) if suggestion.get("target_cluster_id") else None,
                            "similarity_score": suggestion.get("similarity_score"),
                        },
                    )
                except Exception as sse_err:
                    logger.warning(f"Failed to publish suggestion SSE event: {sse_err}")

        logger.info(
            f"Persisted results for project {project_id}: "
            f"{len(name_to_cluster_id)} new clusters, "
            f"{len(resolved_assignments)} fact assignments, "
            f"{len(summaries)} summaries, "
            f"{len(suggestions)} suggestions"
        )

    async def _update_counts(self, project_id: str) -> None:
        """Aktualisiert denormalisierte fact_count und interview_count in clusters.

        Wird nach jeder Persistierung aufgerufen.
        Verwendet COUNT-Queries gegen facts-Tabelle.
        """
        await self._cluster_repo.update_counts_from_db(project_id)

    @staticmethod
    def _normalize_fact(fact: dict) -> dict:
        """Normalisiert einen Fact-Dict (konvertiert UUID-Objekte zu Strings)."""
        return {
            "id": str(fact.get("id", "")),
            "content": fact.get("content", ""),
            "interview_id": str(fact.get("interview_id", "")),
            "cluster_id": str(fact.get("cluster_id", "")) if fact.get("cluster_id") else None,
            "quote": fact.get("quote"),
            "confidence": fact.get("confidence"),
        }

    @staticmethod
    def _normalize_cluster(cluster: dict) -> dict:
        """Normalisiert einen Cluster-Dict (konvertiert UUID-Objekte zu Strings)."""
        return {
            "id": str(cluster.get("id", "")),
            "name": cluster.get("name", ""),
            "summary": cluster.get("summary"),
            "fact_count": cluster.get("fact_count", 0),
            "interview_count": cluster.get("interview_count", 0),
        }

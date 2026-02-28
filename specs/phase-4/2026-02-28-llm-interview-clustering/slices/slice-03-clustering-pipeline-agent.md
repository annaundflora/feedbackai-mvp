# Slice 3: Clustering Pipeline + LangGraph Agent

> **Slice 3 von 8** fuer `LLM Interview Clustering`
>
> | Navigation | |
> |------------|---|
> | **Vorheriger:** | `slice-02-fact-extraction-pipeline.md` |
> | **Naechster:** | `slice-04-dashboard-projekt-liste.md` |

---

## Metadata (fuer Orchestrator)

| Key | Value |
|-----|-------|
| **ID** | `slice-03-clustering-pipeline-agent` |
| **Test** | `python -m pytest backend/tests/slices/llm-interview-clustering/test_slice_03_clustering_pipeline_agent.py -v` |
| **E2E** | `false` |
| **Dependencies** | `["slice-01-db-schema-projekt-crud", "slice-02-fact-extraction-pipeline"]` |

**Erklaerung:**
- **ID**: Eindeutiger Identifier (wird fuer Commits und Evidence verwendet)
- **Test**: Exakter Befehl den der Orchestrator nach Implementierung ausfuehrt
- **E2E**: `false` — pytest Unit/Integration-Tests (kein Playwright)
- **Dependencies**: Slice 1 (DB-Tabellen `projects`, `clusters`, `facts`, `project_interviews`, `ProjectRepository`), Slice 2 (`SseEventBus`, `FactRepository`, `FactExtractionService` mit DI-Trigger via optionalem `clustering_service` Parameter)

---

## Test-Strategy (fuer Orchestrator Pipeline)

> **Quelle:** Auto-detected basierend auf Repo-Indikatoren.
> `backend/requirements.txt` enthaelt `fastapi` + `uvicorn` → Stack: `python-fastapi`.
> LangGraph bereits in requirements.txt (via `langgraph`). Pattern von `backend/app/interview/graph.py` wiederverwendet.

| Key | Value |
|-----|-------|
| **Stack** | `python-fastapi` |
| **Test Command** | `python -m pytest backend/tests/slices/llm-interview-clustering/test_slice_03_clustering_pipeline_agent.py -v` |
| **Integration Command** | `python -m pytest backend/tests/slices/llm-interview-clustering/ -v` |
| **Acceptance Command** | `python -m pytest backend/tests/slices/llm-interview-clustering/test_slice_03_clustering_pipeline_agent.py -v -k "acceptance"` |
| **Start Command** | `uvicorn app.main:app --host 0.0.0.0 --port 8000` |
| **Health Endpoint** | `http://localhost:8000/health` |
| **Mocking Strategy** | `mock_external` |

**Erklaerung:**
- **Mocking Strategy:** Alle OpenRouter LLM-Calls werden mit `AsyncMock` gemockt. Alle DB-Calls werden mit `AsyncMock` gemockt. Kein echter PostgreSQL-Zugriff und keine echten LLM-Calls in Unit-Tests.
- **Integration Tests:** Verwenden FastAPI `TestClient` + gemockte DB-Sessions + gemockte LLM-Clients.

---

## Slice-Uebersicht

| # | Slice | Status | Datei |
|---|-------|--------|-------|
| 1 | DB Schema + Projekt CRUD | **Ready** | `slice-01-db-schema-projekt-crud.md` |
| 2 | Fact Extraction Pipeline | **Ready** | `slice-02-fact-extraction-pipeline.md` |
| 3 | Clustering Pipeline + Agent | **Ready** | `slice-03-clustering-pipeline-agent.md` |
| 4 | Dashboard: Projekt-Liste + Cluster-Uebersicht | Pending | `slice-04-dashboard-projekt-liste.md` |
| 5 | Dashboard: Drill-Down + Zitate | Pending | `slice-05-dashboard-drill-down.md` |
| 6 | Taxonomy-Editing + Summary-Regen | Pending | `slice-06-taxonomy-editing.md` |
| 7 | Live-Updates via SSE | Pending | `slice-07-live-updates-sse.md` |
| 8 | Auth + Polish | Pending | `slice-08-auth-polish.md` |

---

## Kontext & Ziel

Nach erfolgreicher Fact Extraction (Slice 2 publiziert `fact_extracted`-Event) muessen die extrahierten Facts thematisch geclustert werden. Dieser Slice implementiert:

1. `ClusteringGraph` — LangGraph StateGraph (TNT-LLM + GoalEx + Clio Hybrid)
2. `ClusteringService` — Orchestriert Pipeline (inkrementell + Full Re-Cluster), wird direkt von `FactExtractionService` via Dependency-Injection aufgerufen
3. `ClusterRepository` — CRUD auf `clusters`-Tabelle + Denormalisierung der Zaehler
4. `ClusterSuggestionRepository` — CRUD auf `cluster_suggestions`-Tabelle
5. `POST /api/projects/{id}/clustering/recluster` — Full Re-Cluster Endpoint
6. `GET /api/projects/{id}/clustering/status` — Pipeline-Status Endpoint
7. `clustering_status` Tracking in `project_interviews`
8. Merge/Split Suggestions in `cluster_suggestions`-Tabelle

**Abgrenzung zu anderen Slices:**
- Slice 3 implementiert NUR Backend-Clustering-Logik (keine Dashboard-UI)
- Taxonomy-Editing (Merge/Split/Rename via User-Aktion) kommt in Slice 6
- SSE-Streaming zum Dashboard kommt in Slice 7 (SSE-Events werden hier bereits publiziert)
- Full Re-Cluster wird als Endpoint bereitgestellt, das UI-Modal (`recluster_confirm`) kommt in Slice 6
- `ClusteringGraph` ist Pure Computation — kein DB-Zugriff direkt im Graph, Persistenz uebernimmt `ClusteringService`

---

## Technische Umsetzung

### Architektur-Kontext (aus architecture.md)

> **Quelle:** `architecture.md` → Server Logic → Business Logic Flows → Incremental Clustering + Full Re-Cluster + LangGraph ClusteringGraph Design

```
Incremental Clustering (nach Fact Extraction):
  FactExtractionService._clustering_service.process_interview(project_id, interview_id)  [via asyncio.create_task, DI-Trigger]
      → ClusteringService.process_interview(project_id, interview_id)
          → [1] ClusterRepository.list_for_project(project_id) → existing clusters
          → [2] FactRepository.get_facts_for_interview(project_id, interview_id) → new facts
          → [3] ClusteringGraph.invoke(mode="incremental", facts, existing_clusters, research_goal)
              → assign_facts node (LLM)
              → validate_quality node (LLM)
              → refine_clusters node (LLM, max 3 loops)
              → generate_summaries node (LLM)
              → check_suggestions node (LLM)
          → [4] ClusteringService._persist_results(project_id, graph_output)
          → [5] clustering_status → "completed" in project_interviews
          → SSE: clustering_completed

Full Re-Cluster (manueller Trigger):
  POST /api/projects/{id}/clustering/recluster
      → ClusteringService.full_recluster(project_id)
          → [1] Delete all clusters, reset all fact.cluster_id to NULL
          → SSE: clustering_started(mode="full")
          → [2] FactRepository.get_facts_for_project(project_id) → all facts
          → [3] ClusteringGraph.invoke(mode="full", all_facts, research_goal)
              → generate_taxonomy node (LLM, mini-batches von 20)
              → assign_facts node (LLM)
              → validate_quality node (LLM)
              → refine_clusters node (LLM, max 3 loops)
              → generate_summaries node (LLM)
              → check_suggestions node (LLM)
          → [4] ClusteringService._persist_results(project_id, graph_output)
          → SSE: clustering_completed
```

### 1. Architektur-Impact

| Layer | Aenderungen |
|-------|-------------|
| `backend/app/clustering/graph.py` | **Neu:** `ClusteringGraph` — LangGraph StateGraph mit 6 Nodes |
| `backend/app/clustering/graph_state.py` | **Neu:** `ClusteringState` TypedDict |
| `backend/app/clustering/service.py` | **Neu:** `ClusteringService` — Orchestrierung, DI-Trigger via FactExtractionService, Persistenz |
| `backend/app/clustering/cluster_repository.py` | **Neu:** `ClusterRepository` — CRUD `clusters` |
| `backend/app/clustering/cluster_suggestion_repository.py` | **Neu:** `ClusterSuggestionRepository` — CRUD `cluster_suggestions` |
| `backend/app/clustering/prompts.py` | **Erweitert:** Clustering-Prompts (assign_facts, validate_quality, refine_clusters, generate_summaries, check_suggestions, generate_taxonomy) |
| `backend/app/clustering/router.py` | **Erweitert:** Recluster-Endpoint + Status-Endpoint |
| `backend/app/clustering/schemas.py` | **Erweitert:** `ReclusterStarted`, `PipelineStatus`, `ClusterResponse` DTOs |
| `backend/app/api/dependencies.py` | **Erweitert:** `get_clustering_service()`, `get_cluster_repository()` Singletons |
| `backend/app/clustering/extraction.py` | **Erweitert:** Nach `fact_extracted`-Event: Clustering-Trigger |

### 2. Datenfluss

```
FactExtractionService ruft asyncio.create_task(clustering_service.process_interview(...)) auf (DI-Trigger, kein Event-Bus-Subscribe)
  |
  v
ClusteringService.process_interview(project_id, interview_id)  [Background Task via create_task]
  |
  v
InterviewAssignmentRepository.update_clustering_status("running")
  |
  v
ClusterRepository.list_for_project(project_id) → existing_clusters: list[dict]
  |
  v
FactRepository.get_facts_for_interview(project_id, interview_id) → new_facts: list[dict]
  |
  v [Mode-Check]
len(existing_clusters) == 0?
  |-- Ja  → ClusteringGraph.invoke(mode="full", all_facts, research_goal)
  |-- Nein → ClusteringGraph.invoke(mode="incremental", new_facts, existing_clusters, research_goal)
  |
  v [Graph-Output]
assignments: list[{fact_id, cluster_id | new_cluster_name}]
new_clusters: list[{name, fact_ids}]
summaries: dict[cluster_id → summary_text]
suggestions: list[{type, source_cluster_id, target_cluster_id?, similarity_score?}]
  |
  v
ClusteringService._persist_results(project_id, assignments, new_clusters, summaries, suggestions)
  → ClusterRepository.create_clusters(new_clusters) → new cluster UUIDs
  → FactRepository.update_cluster_assignments(assignments) → bulk UPDATE facts.cluster_id
  → ClusterRepository.update_summaries(summaries)
  → ClusterRepository.update_counts(project_id) → UPDATE fact_count, interview_count
  → ClusterSuggestionRepository.save_suggestions(project_id, suggestions)
  |
  v
InterviewAssignmentRepository.update_clustering_status("completed")
  |
  v
SseEventBus.publish(project_id, "clustering_completed", {cluster_count, fact_count})
```

### 3. ClusteringState TypedDict

```python
# backend/app/clustering/graph_state.py

from typing import Literal, TypedDict


class ClusteringState(TypedDict):
    """State fuer den ClusteringGraph LangGraph StateGraph.

    Folgt dem Pattern aus backend/app/interview/graph.py (InterviewGraph).
    """
    project_id: str
    research_goal: str
    prompt_context: str | None
    mode: Literal["incremental", "full"]
    model_clustering: str       # OpenRouter model slug (z.B. "anthropic/claude-sonnet-4")
    model_summary: str          # OpenRouter model slug (z.B. "anthropic/claude-haiku-4")
    facts: list[dict]           # {id, content, interview_id} — Facts die verarbeitet werden
    existing_clusters: list[dict]  # {id, name, summary} — Bestehende Cluster aus DB
    assignments: list[dict]     # {fact_id, cluster_id: str|None, new_cluster_name: str|None}
    new_clusters: list[dict]    # {name, fact_ids: list[str]}
    quality_ok: bool            # Ergebnis von validate_quality
    iteration: int              # Anzahl Correction-Loops (max 3)
    suggestions: list[dict]     # [{type: "merge"|"split", source_cluster_id, target_cluster_id?, similarity_score?, proposed_data?}]
    summaries: dict[str, str]   # {cluster_id: summary_text} oder {new_cluster_name: summary_text}
```

### 4. ClusteringGraph — Nodes

```python
# backend/app/clustering/graph.py

import logging
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI

from app.clustering.graph_state import ClusteringState
from app.clustering.prompts import (
    GENERATE_TAXONOMY_PROMPT,
    ASSIGN_FACTS_PROMPT,
    VALIDATE_QUALITY_PROMPT,
    REFINE_CLUSTERS_PROMPT,
    GENERATE_SUMMARIES_PROMPT,
    CHECK_SUGGESTIONS_PROMPT,
)

logger = logging.getLogger(__name__)

MAX_CORRECTION_ITERATIONS = 3


class ClusteringGraph:
    """LangGraph StateGraph fuer Clustering-Pipeline.

    Implementiert TNT-LLM + GoalEx + Clio Hybrid:
    - generate_taxonomy: Initiale Taxonomie aus allen Facts (mode=full)
    - assign_facts: Facts zu Clustern zuordnen (incremental + full)
    - validate_quality: Qualitaet der Zuordnungen pruefen
    - refine_clusters: Korrektur bei Qualitaetsproblemen (max 3 Loops)
    - generate_summaries: Cluster-Zusammenfassungen generieren
    - check_suggestions: Merge/Split-Vorschlaege generieren

    Folgt dem Pattern aus backend/app/interview/graph.py:
    StateGraph(ClusteringState) + ChatOpenAI(base_url=openrouter)
    """

    def __init__(self, settings) -> None:
        self._settings = settings
        # LLM-Client fuer Clustering (model wird pro Node-Call aus State gelesen)
        self._llm_clustering = ChatOpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=settings.openrouter_api_key,
            model=settings.clustering_model_default,
            temperature=0.0,
        )
        # LLM-Client fuer Summary (leichteres Modell)
        self._llm_summary = ChatOpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=settings.openrouter_api_key,
            model=settings.summary_model_default,
            temperature=0.0,
        )
        self._graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        """Baut den StateGraph auf."""
        graph = StateGraph(ClusteringState)

        # Nodes registrieren
        graph.add_node("generate_taxonomy", self._node_generate_taxonomy)
        graph.add_node("assign_facts", self._node_assign_facts)
        graph.add_node("validate_quality", self._node_validate_quality)
        graph.add_node("refine_clusters", self._node_refine_clusters)
        graph.add_node("generate_summaries", self._node_generate_summaries)
        graph.add_node("check_suggestions", self._node_check_suggestions)

        # Entry-Point: mode-abhaengig
        graph.set_conditional_entry_point(
            lambda state: "generate_taxonomy" if state["mode"] == "full" else "assign_facts",
            {
                "generate_taxonomy": "generate_taxonomy",
                "assign_facts": "assign_facts",
            }
        )

        # Edges
        graph.add_edge("generate_taxonomy", "assign_facts")
        graph.add_conditional_edges(
            "validate_quality",
            self._route_after_validation,
            {
                "refine": "refine_clusters",
                "ok": "generate_summaries",
            }
        )
        graph.add_edge("assign_facts", "validate_quality")
        graph.add_edge("refine_clusters", "generate_summaries")
        graph.add_edge("generate_summaries", "check_suggestions")
        graph.add_edge("check_suggestions", END)

        return graph.compile()

    def _route_after_validation(self, state: ClusteringState) -> str:
        """Routing nach validate_quality: 'refine' oder 'ok'."""
        if state["quality_ok"] or state["iteration"] >= MAX_CORRECTION_ITERATIONS:
            return "ok"
        return "refine"

    async def _node_generate_taxonomy(self, state: ClusteringState) -> dict:
        """Node: Initiale Taxonomie aus allen Facts generieren (mode=full).

        TNT-LLM Pattern: Mini-Batches (20 Facts/Batch) → LLM generiert
        Cluster-Namen → deduplizieren → initiale Taxonomie.

        Input:  state["facts"] — alle Facts des Projekts
        Output: state["existing_clusters"] = [{id: None, name: "...", summary: None}]
        """
        ...

    async def _node_assign_facts(self, state: ClusteringState) -> dict:
        """Node: Facts zu Clustern zuordnen (GoalEx Pattern).

        LLM sieht: facts + existing_clusters + research_goal + prompt_context
        LLM Output: assignments (fact_id → cluster_id oder new_cluster_name)

        Input:  state["facts"], state["existing_clusters"], state["research_goal"]
        Output: state["assignments"], state["new_clusters"]
        """
        ...

    async def _node_validate_quality(self, state: ClusteringState) -> dict:
        """Node: Qualitaet der Zuordnungen validieren.

        LLM prueft: Kohaerenz der Cluster, Groessen-Balance, Themen-Ueberlappung.

        Input:  state["assignments"], state["existing_clusters"], state["new_clusters"]
        Output: state["quality_ok"] (bool), state["iteration"] += 1
        """
        ...

    async def _node_refine_clusters(self, state: ClusteringState) -> dict:
        """Node: Zuordnungen korrigieren (Self-Correction Loop).

        LLM korrigiert Zuordnungen basierend auf Qualitaets-Issues.
        Wird max MAX_CORRECTION_ITERATIONS mal ausgefuehrt.

        Input:  state["assignments"], state["new_clusters"] (mit Issues-Kontext)
        Output: state["assignments"] (korrigiert), state["new_clusters"] (korrigiert)
        """
        ...

    async def _node_generate_summaries(self, state: ClusteringState) -> dict:
        """Node: Cluster-Zusammenfassungen generieren.

        Leichteres Modell (model_summary) pro Cluster.
        Sammelt alle Facts eines Clusters → LLM generiert Zusammenfassung.

        Input:  state["assignments"], state["existing_clusters"], state["new_clusters"]
        Output: state["summaries"] = {cluster_id_or_name: summary_text}
        """
        ...

    async def _node_check_suggestions(self, state: ClusteringState) -> dict:
        """Node: Merge/Split-Vorschlaege generieren.

        Merge-Vorschlaege: LLM prueft Aehnlichkeit der Cluster (>80% → Vorschlag).
        Split-Vorschlaege: Cluster mit >8 Facts → LLM prueft auf Sub-Themen.

        Input:  state["assignments"], state["existing_clusters"], state["new_clusters"]
        Output: state["suggestions"]
        """
        ...

    async def invoke(self, initial_state: ClusteringState) -> ClusteringState:
        """Fuehrt den Clustering-Graph aus.

        Args:
            initial_state: Initialzustand mit project_id, facts, research_goal, mode etc.

        Returns:
            Finaler State nach Graph-Ausfuehrung (assignments, summaries, suggestions).
        """
        return await self._graph.ainvoke(initial_state)
```

### 5. ClusteringService

```python
# backend/app/clustering/service.py

import asyncio
import logging
from typing import Any

from app.clustering.graph import ClusteringGraph
from app.clustering.graph_state import ClusteringState
from app.clustering.cluster_repository import ClusterRepository
from app.clustering.cluster_suggestion_repository import ClusterSuggestionRepository
from app.clustering.fact_repository import FactRepository
from app.clustering.interview_assignment_repository import InterviewAssignmentRepository
from app.projects.repository import ProjectRepository
from app.clustering.events import SseEventBus

logger = logging.getLogger(__name__)

SPLIT_SUGGESTION_THRESHOLD = 8  # Facts je Cluster → Split-Vorschlag


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
        self._running_recluster: set[str] = set()

    async def process_interview(
        self,
        project_id: str,
        interview_id: str,
    ) -> None:
        """Orchestriert inkrementelles Clustering nach Fact Extraction.

        Wird von FactExtractionService nach erfolgreicher Extraktion aufgerufen.
        Laeuft als asyncio.create_task() (non-blocking).

        Logik:
        - Bestehende Cluster laden
        - Falls keine Cluster vorhanden → mode="full" (Erstes Interview des Projekts)
        - Sonst → mode="incremental"
        - ClusteringGraph ausfuehren
        - Ergebnisse persistieren
        - clustering_status aktualisieren
        - SSE-Events publizieren
        """
        ...

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
        ...

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
        ...

    async def _update_counts(self, project_id: str) -> None:
        """Aktualisiert denormalisierte fact_count und interview_count in clusters.

        Wird nach jeder Persistierung aufgerufen.
        Verwendet COUNT-Queries gegen facts-Tabelle.
        """
        ...
```

### 6. ClusterRepository

```python
# backend/app/clustering/cluster_repository.py

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


class ClusterRepository:
    """Repository fuer clusters-Tabelle.

    Folgt exakt dem Pattern von InterviewRepository:
    Raw SQL + SQLAlchemy async + text()
    """

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def list_for_project(
        self,
        project_id: str,
    ) -> list[dict]:
        """Laedt alle Cluster eines Projekts.

        Returns:
            Liste von {id, name, summary, fact_count, interview_count, created_at, updated_at}.
            Sortiert nach fact_count DESC.
        """
        ...

    async def create_clusters(
        self,
        project_id: str,
        clusters: list[dict],
    ) -> list[dict]:
        """Legt neue Cluster an.

        Args:
            project_id: UUID als String.
            clusters: Liste von {name} oder {name, fact_ids}.

        Returns:
            Liste der neu angelegten Cluster als Dicts (inkl. id).
        """
        ...

    async def update_summary(
        self,
        cluster_id: str,
        summary: str,
    ) -> dict:
        """Aktualisiert die Summary eines Clusters."""
        ...

    async def update_counts(
        self,
        cluster_id: str,
        fact_count: int,
        interview_count: int,
    ) -> None:
        """Aktualisiert denormalisierte Zaehler."""
        ...

    async def delete_all_for_project(
        self,
        project_id: str,
    ) -> None:
        """Loescht alle Cluster eines Projekts (fuer Full Re-Cluster).

        ON DELETE CASCADE loescht auch facts.cluster_id Referenzen (SET NULL).
        """
        ...

    async def get_by_id(
        self,
        cluster_id: str,
        project_id: str,
    ) -> dict | None:
        """Laedt einen Cluster per ID (mit Projekt-Pruefung fuer Security)."""
        ...
```

### 7. ClusterSuggestionRepository

```python
# backend/app/clustering/cluster_suggestion_repository.py

class ClusterSuggestionRepository:
    """Repository fuer cluster_suggestions-Tabelle.

    Speichert LLM-generierte Merge/Split-Vorschlaege.
    Status: 'pending' | 'accepted' | 'dismissed'
    """

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def save_suggestions(
        self,
        project_id: str,
        suggestions: list[dict],
    ) -> list[dict]:
        """Speichert neue Suggestions.

        Args:
            suggestions: Liste von {type, source_cluster_id, target_cluster_id?,
                         similarity_score?, proposed_data?}.

        Vorhandene 'pending' Suggestions fuer denselben source_cluster_id werden
        vorher geloescht (kein Duplikat-Spam).
        """
        ...

    async def list_pending_for_project(
        self,
        project_id: str,
    ) -> list[dict]:
        """Laedt alle offenen Suggestions eines Projekts (status='pending').

        Returns:
            Liste von {id, type, source_cluster_id, target_cluster_id?,
            similarity_score?, proposed_data?, created_at}.
        """
        ...

    async def update_status(
        self,
        suggestion_id: str,
        status: str,  # 'accepted' | 'dismissed'
    ) -> dict:
        """Setzt Status einer Suggestion."""
        ...
```

### 8. Clustering-Prompts

```python
# backend/app/clustering/prompts.py — Erweiterung fuer Slice 3

# --- GENERATE TAXONOMY PROMPT (mode=full, Mini-Batch) ---

GENERATE_TAXONOMY_PROMPT = """You are a qualitative research analyst. Your task is to generate a thematic taxonomy from user interview data.

Research Goal: {research_goal}
{prompt_context_section}

Below are atomic facts extracted from user interviews. Analyze them and propose a set of thematic clusters.

Facts (batch {batch_number} of {total_batches}):
{facts_text}

Already proposed clusters from previous batches:
{existing_taxonomy}

Propose new cluster names that are:
- Directly relevant to the research goal
- Distinct from already proposed clusters (merge with existing if too similar)
- Named with 2-5 words, specific and descriptive
- Not more than 8 clusters total across all batches

Return ONLY a valid JSON array of cluster names. No preamble.

Format: ["Cluster Name 1", "Cluster Name 2", ...]"""


# --- ASSIGN FACTS PROMPT (incremental + full) ---

ASSIGN_FACTS_PROMPT = """You are a qualitative research analyst. Assign each fact to the most appropriate cluster.

Research Goal: {research_goal}
{prompt_context_section}

Available Clusters:
{clusters_text}

Facts to assign:
{facts_text}

For each fact, assign it to exactly one cluster. If no existing cluster fits well (similarity < 60%), propose a new cluster name.

Return ONLY a valid JSON array. No preamble.

Format:
[
  {{"fact_id": "uuid", "cluster_id": "existing-cluster-uuid", "new_cluster_name": null}},
  {{"fact_id": "uuid", "cluster_id": null, "new_cluster_name": "New Cluster Name"}},
  ...
]"""


# --- VALIDATE QUALITY PROMPT ---

VALIDATE_QUALITY_PROMPT = """You are a quality reviewer for qualitative research clustering.

Research Goal: {research_goal}

Current cluster assignments:
{cluster_summary_text}

Evaluate the clustering quality:
1. Are facts within each cluster thematically coherent?
2. Are there obvious duplicates between clusters?
3. Is the cluster size distribution reasonable (no cluster with >60% of all facts)?
4. Are assignments aligned with the research goal?

Return ONLY a valid JSON object. No preamble.

Format:
{{
  "quality_ok": true | false,
  "issues": ["Issue description 1", "Issue description 2"]
}}

If quality_ok is true, issues should be an empty list."""


# --- REFINE CLUSTERS PROMPT ---

REFINE_CLUSTERS_PROMPT = """You are a qualitative research analyst. Refine the cluster assignments based on quality issues.

Research Goal: {research_goal}

Quality Issues identified:
{issues_text}

Current assignments (to refine):
{cluster_summary_text}

Provide corrected assignments for facts that need to be moved. Only include facts that need to change.

Return ONLY a valid JSON array of corrections. No preamble.

Format:
[
  {{"fact_id": "uuid", "cluster_id": "target-cluster-uuid", "new_cluster_name": null}},
  ...
]"""


# --- GENERATE SUMMARIES PROMPT ---

GENERATE_SUMMARIES_PROMPT = """You are a qualitative research analyst. Write a concise summary for a thematic cluster.

Research Goal: {research_goal}

Cluster Name: {cluster_name}

Facts in this cluster:
{facts_text}

Write a 2-4 sentence summary that:
- Captures the main theme across all facts
- Is written from the user's perspective
- Highlights the most significant pattern
- Is relevant to the research goal

Return ONLY the summary text. No preamble, no quotes."""


# --- CHECK SUGGESTIONS PROMPT ---

CHECK_SUGGESTIONS_PROMPT = """You are a qualitative research analyst. Check if any clusters should be merged or split.

Research Goal: {research_goal}

Current clusters with fact counts and summaries:
{clusters_text}

Check for:
1. MERGE opportunities: Clusters that are semantically very similar (>80% overlap in themes)
2. SPLIT opportunities: Clusters with many facts (>{split_threshold}) that contain distinct sub-themes

Return ONLY a valid JSON array. Return empty array [] if no suggestions. No preamble.

Format:
[
  {{
    "type": "merge",
    "source_cluster_id": "uuid",
    "target_cluster_id": "uuid",
    "similarity_score": 0.85,
    "reason": "Brief explanation"
  }},
  {{
    "type": "split",
    "source_cluster_id": "uuid",
    "proposed_subclusters": ["Subcluster Name 1", "Subcluster Name 2"],
    "reason": "Brief explanation"
  }}
]"""
```

### 9. Recluster-Endpoint + Status-Endpoint

> **Quelle:** `architecture.md` → Endpoints — Pipeline & Events

**POST `/api/projects/{id}/clustering/recluster`**

**Response-Typ:** `ReclusterStarted`

```python
# backend/app/clustering/router.py — Recluster-Endpoint (NEU in Slice 3)

@router.post("/api/projects/{project_id}/clustering/recluster")
async def trigger_full_recluster(
    project_id: str,
    clustering_service: ClusteringService = Depends(get_clustering_service),
) -> ReclusterStarted:
    """Loescht alle Cluster und startet vollstaendiges Re-Clustering.

    Destruktiv: Alle bestehenden Cluster-Zuordnungen werden geloescht.
    Facts bleiben erhalten.

    Gibt sofort 200 zurueck (Recluster laeuft asynchron als Background-Task).
    Falls Recluster bereits laeuft: 409 Conflict.
    """
    ...
```

```python
# DTOs fuer Recluster-Endpoints

class ReclusterStarted(BaseModel):
    """Response fuer POST /recluster."""
    status: str = "started"
    message: str  # "Full re-cluster started for project {id}"
    project_id: str
```

```json
// POST /api/projects/{id}/clustering/recluster — Response 200 OK
{
  "status": "started",
  "message": "Full re-cluster started for project 550e8400-e29b-41d4-a716-446655440000",
  "project_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**Fehler-Responses:**

| Code | Wann | Body |
|------|------|------|
| 404 | Projekt nicht gefunden | `{"detail": "Project not found"}` |
| 409 | Re-Cluster laeuft bereits | `{"detail": "Full re-cluster already running for this project"}` |

---

**GET `/api/projects/{id}/clustering/status`**

**Response-Typ:** `PipelineStatus`

```python
# DTOs fuer Status-Endpoint

class PipelineStatus(BaseModel):
    """Response fuer GET /clustering/status."""
    status: str              # "idle" | "running"
    mode: str | None         # "incremental" | "full" | None
    progress: dict | None    # {"total": int, "completed": int} | None
    current_step: str | None # z.B. "assign_facts" | "generate_summaries" | None
```

```json
// GET /api/projects/{id}/clustering/status — laufend
{
  "status": "running",
  "mode": "full",
  "progress": {"total": 47, "completed": 23},
  "current_step": "assign_facts"
}

// GET /api/projects/{id}/clustering/status — idle
{
  "status": "idle",
  "mode": null,
  "progress": null,
  "current_step": null
}
```

### 10. FactRepository-Erweiterungen

```python
# backend/app/clustering/fact_repository.py — Erweiterungen fuer Slice 3

async def update_cluster_assignments(
    self,
    assignments: list[dict],
) -> None:
    """Aktualisiert cluster_id fuer eine Liste von Facts.

    Args:
        assignments: Liste von {fact_id: str, cluster_id: str | None}.
                     cluster_id=None → unassigned.

    Verwendet Bulk-UPDATE mit CASE-Statement fuer Performance.
    """
    ...

async def reset_cluster_assignments_for_project(
    self,
    project_id: str,
) -> None:
    """Setzt alle facts.cluster_id = NULL fuer ein Projekt (Full Re-Cluster).

    UPDATE facts SET cluster_id = NULL WHERE project_id = :project_id
    """
    ...
```

### 11. InterviewAssignmentRepository-Erweiterungen

```python
# backend/app/clustering/interview_assignment_repository.py — Erweiterungen fuer Slice 3

async def update_clustering_status(
    self,
    interview_id: str,
    clustering_status: str,  # 'pending' | 'running' | 'completed' | 'failed'
) -> dict:
    """Aktualisiert clustering_status in project_interviews.

    Args:
        interview_id: UUID als String.
        clustering_status: Neuer Status.

    Returns:
        Aktualisierter DB-Row als Dict.
    """
    ...

async def get_all_for_project(
    self,
    project_id: str,
) -> list[dict]:
    """Laedt alle Zuordnungen eines Projekts (fuer Status-Aggregation)."""
    ...
```

### 12. FactExtractionService-Erweiterung (Clustering-Trigger)

```python
# backend/app/clustering/extraction.py — Erweiterung nach erfolgreichem Fact-Save

    async def process_interview(self, project_id: str, interview_id: str) -> None:
        # ... (bestehende Logik aus Slice 2: Extraktion, Status-Update, SSE fact_extracted) ...

        # NEU in Slice 3: Clustering-Trigger nach erfolgreicher Extraktion
        if self._clustering_service:
            asyncio.create_task(
                self._clustering_service.process_interview(project_id, interview_id)
            )
            logger.info(f"Clustering triggered for interview {interview_id} in project {project_id}")
```

**WICHTIG:**
- `FactExtractionService.__init__()` erhaelt optionalen Parameter `clustering_service: ClusteringService | None = None` (gespeichert als `self._clustering_service`)
- Rueckwaertskompatibel: Wenn `clustering_service` nicht gesetzt, kein Trigger (kein Breaking Change fuer Slice-2-Tests)
- Der Trigger ist `fire-and-forget` via `asyncio.create_task()` — kein Warten auf Clustering-Ergebnis

### 13. Settings-Erweiterung

```python
# backend/app/config/settings.py — Neue Felder fuer Clustering-Graph

class Settings(BaseSettings):
    # ... (bestehende Felder + Slice-2-Felder unveraendert) ...

    # ClusteringGraph Defaults (NEU in Slice 3)
    clustering_model_default: str = "anthropic/claude-sonnet-4"
    summary_model_default: str = "anthropic/claude-haiku-4"
    clustering_split_threshold: int = 8  # Facts/Cluster → Split-Suggestion
    clustering_merge_similarity_threshold: float = 0.8  # 80% → Merge-Suggestion
    clustering_taxonomy_batch_size: int = 20  # Facts pro Batch bei generate_taxonomy
```

### 14. Abhaengigkeiten

- **Bestehend (wiederverwendet aus Slice 1 + 2):**
  - `backend/app/clustering/fact_repository.py` — `FactRepository` (Slice 2)
  - `backend/app/clustering/events.py` — `SseEventBus` (Slice 2)
  - `backend/app/projects/repository.py` — `ProjectRepository` (Slice 1, gemaess architecture.md)
  - `backend/app/clustering/interview_assignment_repository.py` — `InterviewAssignmentRepository` (Slice 1+2)
  - `backend/app/clustering/extraction.py` — `FactExtractionService` (Slice 2, wird erweitert)
  - `backend/app/api/dependencies.py` — Dependency-Injection-Pattern (Slice 1)
  - `backend/app/config/settings.py` — Settings-Singleton (Slice 1+2)
  - `langchain_openai.ChatOpenAI` — bereits in requirements.txt
  - `langgraph.graph.StateGraph` — bereits in requirements.txt

- **Neu (kein neues externes Paket noetig):**
  - `backend/app/clustering/graph.py` — `ClusteringGraph`
  - `backend/app/clustering/graph_state.py` — `ClusteringState` TypedDict
  - `backend/app/clustering/service.py` — `ClusteringService`
  - `backend/app/clustering/cluster_repository.py` — `ClusterRepository`
  - `backend/app/clustering/cluster_suggestion_repository.py` — `ClusterSuggestionRepository`

---

## Integrations-Checkliste

### 1. LangGraph-Integration
- [ ] `ClusteringGraph._build_graph()` registriert alle 6 Nodes korrekt
- [ ] `set_conditional_entry_point()` wechselt korrekt zwischen `generate_taxonomy` (full) und `assign_facts` (incremental)
- [ ] `_route_after_validation()` gibt "refine" wenn `!quality_ok && iteration < 3`, sonst "ok"
- [ ] `refine_clusters` nach max 3 Iterationen immer zu `generate_summaries` → kein Endlos-Loop
- [ ] `ClusteringGraph.invoke()` gibt finalen `ClusteringState` zurueck

### 2. Clustering-Trigger-Integration
- [ ] `FactExtractionService.process_interview()` ruft `asyncio.create_task(clustering_service.process_interview(...))` nach erfolgreicher Extraktion
- [ ] Trigger ist `fire-and-forget` — Interview-Ende blockiert nicht auf Clustering
- [ ] `FactExtractionService` bleibt rueckwaertskompatibel (kein Breaking Change fuer Slice-2-Tests)
- [ ] `ClusteringService.process_interview()` erkennt "erstes Interview" (kein Cluster vorhanden) → mode="full"

### 3. DB-Integration
- [ ] `ClusterRepository.create_clusters()` gibt neue UUIDs zurueck (fuer Assignments)
- [ ] `FactRepository.update_cluster_assignments()` Bulk-UPDATE mit Korrektheit (alle fact_ids existieren im Projekt)
- [ ] `ClusterRepository.delete_all_for_project()` loescht Cluster, facts.cluster_id wird via ON DELETE SET NULL auf NULL gesetzt
- [ ] `ClusterRepository.update_counts()` berechnet fact_count und interview_count korrekt (COUNT DISTINCT)
- [ ] `ClusterSuggestionRepository.save_suggestions()` loescht vorhandene 'pending' Suggestions fuer denselben source_cluster_id vor Insert

### 4. clustering_status Tracking
- [ ] Status-Uebergaenge korrekt: `pending` → `running` → `completed` | `failed`
- [ ] Alle Interviews eines Projekts werden bei Full-Recluster auf `clustering_status="running"` gesetzt
- [ ] Bei Fehler: `clustering_status="failed"`, SSE `clustering_failed` wird publiziert

### 5. Full-Recluster-Schutz
- [ ] `_running_recluster: set[str]` verhindert parallele Full-Recluster pro Projekt
- [ ] `POST /recluster` gibt 409 wenn `project_id in _running_recluster`
- [ ] Nach Abschluss (Erfolg oder Fehler) wird `project_id` aus `_running_recluster` entfernt

### 6. SSE-Events
- [ ] `clustering_started` mit `{mode: "incremental"|"full"}` bei Pipeline-Start
- [ ] `clustering_updated` mit `{clusters: [{id, name, fact_count}]}` nach Persistierung
- [ ] `clustering_completed` mit `{cluster_count, fact_count}` bei Erfolg
- [ ] `clustering_failed` mit `{error, unassigned_count}` bei Fehler
- [ ] `suggestion` mit `{type, source_cluster_id, ...}` fuer jede Suggestion

### 7. Datenfluss-Vollstaendigkeit
- [ ] `graph_output["new_clusters"]` werden in DB angelegt, UUIDs zurueck in `assignments` eingepflegt
- [ ] Denormalisierte Zaehler (`fact_count`, `interview_count`) nach jeder Persistierung aktualisiert
- [ ] `summaries` dict kann sowohl UUID-Keys (bestehende Cluster) als auch Name-Keys (neue Cluster) enthalten

---

## UI Anforderungen

Dieser Slice hat keine neuen Frontend-Komponenten. Die Clustering-Backend-Logik wird spaeter von folgenden UI-Komponenten konsumiert:

- `progress_bar` (Insights Tab) — zeigt Clustering-Fortschritt — kommt in Slice 7
- `cluster_card` (Insights Tab) — zeigt Cluster-Cards — kommt in Slice 4
- `recluster_btn` + `recluster_confirm` Modal — triggert `POST /recluster` — UI kommt in Slice 6
- `merge_suggestion` + `split_suggestion` Banners — zeigt `cluster_suggestions` — kommt in Slice 6
- `clustering_error_banner` (Insights Tab) — kommt in Slice 4

**Wireframe-Referenz (aus wireframes.md — Project Dashboard Insights Tab):**

```
│  ④ ████████████████████░░░░░  Analyzing... 47/52 Facts
│
│  ⑤ ┌─────────────────────────────────────────────────┐
│    │ ⚡ Suggestion: Merge "Login Issues" with         │
│    │    "Auth Problems" (82% similar)                 │
│    │                        [Dismiss]  [Merge]        │
│    └─────────────────────────────────────────────────┘
│
│                                       ⑥ [Recalculate ↻]
```

Die SSE-Events (`clustering_started`, `clustering_updated`, `clustering_completed`, `suggestion`) werden in diesem Slice publiziert. Das Dashboard empfaengt sie erst ab Slice 7 (SSE-Streaming-Endpoint).

---

## Acceptance Criteria

1) GIVEN ein Interview das einem Projekt zugeordnet ist und `extraction_status="completed"` hat
   WHEN `FactExtractionService.process_interview()` erfolgreich abschliesst
   THEN wird `ClusteringService.process_interview(project_id, interview_id)` als Background-Task gestartet und `clustering_status` auf `"running"` gesetzt

2) GIVEN ein Projekt ohne bestehende Cluster mit extrahierten Facts
   WHEN `ClusteringService.process_interview()` ausgefuehrt wird
   THEN wird `ClusteringGraph` mit `mode="full"` aufgerufen, eine initiale Taxonomie generiert, alle Facts Clustern zugeordnet, und mind. 1 Cluster in der `clusters`-Tabelle erstellt

3) GIVEN ein Projekt mit bestehenden Clustern und einem neuen Interview
   WHEN `ClusteringService.process_interview()` ausgefuehrt wird
   THEN wird `ClusteringGraph` mit `mode="incremental"` aufgerufen, die neuen Facts den bestehenden Clustern zugeordnet (oder neue Cluster vorgeschlagen), und `clustering_status` auf `"completed"` gesetzt

4) GIVEN ein ClusteringGraph-Lauf wo `validate_quality` quality_ok=false zurueckgibt
   WHEN `iteration < 3`
   THEN wird `refine_clusters` ausgefuehrt und danach erneut zu `generate_summaries` weitergeleitet (Self-Correction Loop)

5) GIVEN ein ClusteringGraph-Lauf wo `validate_quality` 3x quality_ok=false zurueckgibt
   WHEN `iteration >= 3`
   THEN wird der Loop beendet, `generate_summaries` mit den letzten Assignments aufgerufen, und das Ergebnis akzeptiert (kein 4. Loop)

6) GIVEN ein abgeschlossener Clustering-Lauf
   WHEN `ClusteringService._persist_results()` aufgerufen wird
   THEN werden alle neuen Cluster in `clusters`-Tabelle angelegt, alle Fact-Zuordnungen in `facts.cluster_id` aktualisiert, Summaries in `clusters.summary` gespeichert, und denormalisierte Zaehler (`fact_count`, `interview_count`) korrekt aktualisiert

7) GIVEN ein Cluster wird neu erstellt und hat Aehnlichkeit > 80% mit einem bestehenden Cluster
   WHEN `check_suggestions` ausgefuehrt wird
   THEN wird ein `merge`-Eintrag in `cluster_suggestions` mit `status="pending"` und `similarity_score` gespeichert, und ein SSE-Event `suggestion` publiziert

8) GIVEN ein Projekt mit bestehenden Clustern und Facts
   WHEN `POST /api/projects/{id}/clustering/recluster` aufgerufen wird
   THEN werden alle bestehenden Cluster geloescht, alle `facts.cluster_id` auf NULL gesetzt, ein neuer Full-Recluster-Task gestartet, und HTTP 200 mit `{"status": "started"}` zurueckgegeben

9) GIVEN ein Full-Recluster laeuft bereits fuer ein Projekt
   WHEN `POST /api/projects/{id}/clustering/recluster` erneut aufgerufen wird
   THEN wird HTTP 409 mit `{"detail": "Full re-cluster already running for this project"}` zurueckgegeben

10) GIVEN ein Clustering-Lauf scheitert nach 3 LLM-Retries
    WHEN der Fehler auftritt
    THEN wird `clustering_status` auf `"failed"` gesetzt, unzugeordnete Facts bleiben mit `cluster_id=NULL` erhalten, und SSE-Event `clustering_failed` mit `{error, unassigned_count}` publiziert

---

## Testfaelle

**WICHTIG:** Tests muessen VOR der Implementierung definiert werden. Der Orchestrator fuehrt diese Tests automatisch nach der Slice-Implementierung aus.

### Test-Datei

`backend/tests/slices/llm-interview-clustering/test_slice_03_clustering_pipeline_agent.py`

<test_spec>
```python
# backend/tests/slices/llm-interview-clustering/test_slice_03_clustering_pipeline_agent.py
"""Tests fuer Slice 3: Clustering Pipeline + LangGraph Agent.

Alle LLM-Calls und DB-Calls werden gemockt (mock_external Strategie).
Kein echter OpenRouter-Zugriff, kein echter PostgreSQL-Zugriff in Unit-Tests.
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
        {"id": str(uuid.uuid4()), "content": "User cannot find settings page.", "interview_id": str(uuid.uuid4())},
        {"id": str(uuid.uuid4()), "content": "Navigation structure is confusing.", "interview_id": str(uuid.uuid4())},
    ]


@pytest.fixture
def mock_existing_clusters(mock_cluster_id_1, mock_cluster_id_2) -> list[dict]:
    return [
        {"id": mock_cluster_id_1, "name": "Navigation Issues", "summary": "Users struggle to find key features."},
        {"id": mock_cluster_id_2, "name": "Pricing Confusion", "summary": "Users don't understand pricing tiers."},
    ]


@pytest.fixture
def mock_cluster_repository():
    return AsyncMock()


@pytest.fixture
def mock_suggestion_repository():
    return AsyncMock()


@pytest.fixture
def mock_fact_repository():
    return AsyncMock()


@pytest.fixture
def mock_assignment_repository():
    return AsyncMock()


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
    return settings


# ============================================================
# AC 2: Neues Projekt ohne Cluster → mode="full"
# ============================================================

class TestClusteringServiceFirstInterview:
    """AC 2: Erster Clustering-Lauf (keine bestehenden Cluster) → mode='full'."""

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
        """GIVEN Projekt ohne Cluster
        WHEN process_interview() aufgerufen
        THEN ClusteringGraph mit mode='full' aufgerufen"""
        mock_project_repository.get_by_id = AsyncMock(return_value=mock_project_row)
        mock_cluster_repository.list_for_project = AsyncMock(return_value=[])  # Keine Cluster
        mock_fact_repository.get_facts_for_interview = AsyncMock(return_value=mock_facts_new)
        mock_assignment_repository.update_clustering_status = AsyncMock()

        mock_graph = AsyncMock()
        mock_graph.invoke = AsyncMock(return_value={
            "assignments": [{"fact_id": f["id"], "cluster_id": None, "new_cluster_name": "Navigation Issues"} for f in mock_facts_new],
            "new_clusters": [{"name": "Navigation Issues", "fact_ids": [f["id"] for f in mock_facts_new]}],
            "summaries": {"Navigation Issues": "Users struggle with navigation."},
            "suggestions": [],
            "quality_ok": True,
            "iteration": 1,
        })

        from app.clustering.service import ClusteringService
        service = ClusteringService(
            clustering_graph=mock_graph,
            cluster_repository=mock_cluster_repository,
            cluster_suggestion_repository=mock_suggestion_repository,
            fact_repository=mock_fact_repository,
            assignment_repository=mock_assignment_repository,
            project_repository=mock_project_repository,
            event_bus=mock_event_bus,
            settings=mock_settings,
        )

        await service.process_interview(mock_project_id, mock_interview_id)

        # Verify: mode="full" in invoke call
        call_state = mock_graph.invoke.call_args[0][0]
        assert call_state["mode"] == "full"


# ============================================================
# AC 3: Bestehendes Projekt → mode="incremental"
# ============================================================

class TestClusteringServiceIncrementalMode:
    """AC 3: Inkrementelles Clustering bei bestehenden Clustern."""

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
        """GIVEN Projekt mit bestehenden Clustern
        WHEN process_interview() aufgerufen
        THEN ClusteringGraph mit mode='incremental' aufgerufen"""
        mock_project_repository.get_by_id = AsyncMock(return_value=mock_project_row)
        mock_cluster_repository.list_for_project = AsyncMock(return_value=mock_existing_clusters)
        mock_fact_repository.get_facts_for_interview = AsyncMock(return_value=mock_facts_new)
        mock_assignment_repository.update_clustering_status = AsyncMock()

        mock_graph = AsyncMock()
        mock_graph.invoke = AsyncMock(return_value={
            "assignments": [{"fact_id": f["id"], "cluster_id": mock_cluster_id_1, "new_cluster_name": None} for f in mock_facts_new],
            "new_clusters": [],
            "summaries": {mock_cluster_id_1: "Updated navigation summary."},
            "suggestions": [],
            "quality_ok": True,
            "iteration": 1,
        })

        from app.clustering.service import ClusteringService
        service = ClusteringService(
            clustering_graph=mock_graph,
            cluster_repository=mock_cluster_repository,
            cluster_suggestion_repository=mock_suggestion_repository,
            fact_repository=mock_fact_repository,
            assignment_repository=mock_assignment_repository,
            project_repository=mock_project_repository,
            event_bus=mock_event_bus,
            settings=mock_settings,
        )

        await service.process_interview(mock_project_id, mock_interview_id)

        call_state = mock_graph.invoke.call_args[0][0]
        assert call_state["mode"] == "incremental"
        assert len(call_state["existing_clusters"]) == 2


# ============================================================
# AC 4 + 5: Self-Correction Loop (max 3 Iterationen)
# ============================================================

class TestClusteringGraphSelfCorrectionLoop:
    """AC 4+5: Self-Correction Loop laeuft max 3x."""

    def test_route_after_validation_returns_refine_when_quality_not_ok_and_under_limit(self):
        """AC 4: quality_ok=False, iteration=1 → route='refine'."""
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

    def test_route_after_validation_returns_ok_when_max_iterations_reached(self):
        """AC 5: quality_ok=False, iteration=3 → route='ok' (Loop beendet)."""
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

    def test_route_after_validation_returns_ok_when_quality_is_ok(self):
        """AC 4: quality_ok=True → route='ok' (kein weiterer Loop)."""
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
# AC 6: Persistierung der Ergebnisse
# ============================================================

class TestClusteringServicePersistence:
    """AC 6: _persist_results() persistiert alle Ergebnisse korrekt."""

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
        """GIVEN Graph-Output mit neuen Clustern und Assignments
        WHEN _persist_results() aufgerufen
        THEN Cluster in DB, Fact-Assignments aktualisiert, Zaehler upgedated"""
        new_cluster_uuid = str(uuid.uuid4())
        mock_cluster_repository.create_clusters = AsyncMock(
            return_value=[{"id": new_cluster_uuid, "name": "Navigation Issues"}]
        )
        mock_cluster_repository.update_summary = AsyncMock()
        mock_cluster_repository.update_counts = AsyncMock()
        mock_fact_repository.update_cluster_assignments = AsyncMock()
        mock_suggestion_repository.save_suggestions = AsyncMock(return_value=[])

        graph_output = {
            "assignments": [
                {"fact_id": mock_facts_new[0]["id"], "cluster_id": None, "new_cluster_name": "Navigation Issues"},
            ],
            "new_clusters": [{"name": "Navigation Issues", "fact_ids": [mock_facts_new[0]["id"]]}],
            "summaries": {"Navigation Issues": "Users struggle with navigation."},
            "suggestions": [],
        }

        mock_graph = AsyncMock()
        from app.clustering.service import ClusteringService
        service = ClusteringService(
            clustering_graph=mock_graph,
            cluster_repository=mock_cluster_repository,
            cluster_suggestion_repository=mock_suggestion_repository,
            fact_repository=mock_fact_repository,
            assignment_repository=mock_assignment_repository,
            project_repository=mock_project_repository,
            event_bus=mock_event_bus,
            settings=mock_settings,
        )

        await service._persist_results(mock_project_id, graph_output)

        mock_cluster_repository.create_clusters.assert_called_once()
        mock_fact_repository.update_cluster_assignments.assert_called_once()
        mock_cluster_repository.update_summary.assert_called_once()


# ============================================================
# AC 7: Merge-Suggestion gespeichert
# ============================================================

class TestMergeSuggestion:
    """AC 7: Merge-Suggestion wird in cluster_suggestions gespeichert."""

    @pytest.mark.asyncio
    async def test_merge_suggestion_saved_when_similarity_above_threshold(
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
        """GIVEN Graph liefert Merge-Suggestion mit similarity > 0.8
        WHEN _persist_results() aufgerufen
        THEN Suggestion in cluster_suggestions mit status='pending' gespeichert
             und SSE 'suggestion' Event publiziert"""
        mock_cluster_repository.create_clusters = AsyncMock(return_value=[])
        mock_cluster_repository.update_summary = AsyncMock()
        mock_cluster_repository.update_counts = AsyncMock()
        mock_fact_repository.update_cluster_assignments = AsyncMock()

        suggestion = {
            "type": "merge",
            "source_cluster_id": mock_cluster_id_1,
            "target_cluster_id": mock_cluster_id_2,
            "similarity_score": 0.85,
        }
        mock_suggestion_repository.save_suggestions = AsyncMock(return_value=[{**suggestion, "id": str(uuid.uuid4()), "status": "pending"}])

        graph_output = {
            "assignments": [],
            "new_clusters": [],
            "summaries": {},
            "suggestions": [suggestion],
        }

        mock_graph = AsyncMock()
        from app.clustering.service import ClusteringService
        service = ClusteringService(
            clustering_graph=mock_graph,
            cluster_repository=mock_cluster_repository,
            cluster_suggestion_repository=mock_suggestion_repository,
            fact_repository=mock_fact_repository,
            assignment_repository=mock_assignment_repository,
            project_repository=mock_project_repository,
            event_bus=mock_event_bus,
            settings=mock_settings,
        )

        await service._persist_results(mock_project_id, graph_output)

        mock_suggestion_repository.save_suggestions.assert_called_once()
        mock_event_bus.publish.assert_called()
        # Verify SSE event type
        publish_call_args = mock_event_bus.publish.call_args_list
        suggestion_events = [c for c in publish_call_args if c[0][1] == "suggestion"]
        assert len(suggestion_events) >= 1


# ============================================================
# AC 8 + 9: Full Recluster Endpoint
# ============================================================

class TestFullReclusterEndpoint:
    """AC 8+9: POST /clustering/recluster Endpoint."""

    @pytest.mark.asyncio
    async def test_full_recluster_starts_background_task_and_returns_200(
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
        """AC 8: POST /recluster → 200, Task gestartet, Cluster geloescht"""
        mock_project_repository.get_by_id = AsyncMock(return_value={"id": mock_project_id, "research_goal": "Test"})
        mock_cluster_repository.delete_all_for_project = AsyncMock()
        mock_fact_repository.reset_cluster_assignments_for_project = AsyncMock()
        mock_fact_repository.get_facts_for_project = AsyncMock(return_value=[])

        mock_graph = AsyncMock()
        mock_graph.invoke = AsyncMock(return_value={
            "assignments": [], "new_clusters": [], "summaries": {}, "suggestions": [], "quality_ok": True, "iteration": 1,
        })

        from app.clustering.service import ClusteringService
        service = ClusteringService(
            clustering_graph=mock_graph,
            cluster_repository=mock_cluster_repository,
            cluster_suggestion_repository=mock_suggestion_repository,
            fact_repository=mock_fact_repository,
            assignment_repository=mock_assignment_repository,
            project_repository=mock_project_repository,
            event_bus=mock_event_bus,
            settings=mock_settings,
        )

        result = await service.full_recluster(mock_project_id)

        mock_cluster_repository.delete_all_for_project.assert_called_once_with(mock_project_id)
        mock_fact_repository.reset_cluster_assignments_for_project.assert_called_once_with(mock_project_id)

    @pytest.mark.asyncio
    async def test_full_recluster_returns_conflict_when_already_running(
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
        """AC 9: Zweiter /recluster-Aufruf waehrend laufendem Task → ConflictError"""
        mock_graph = AsyncMock()
        from app.clustering.service import ClusteringService, ConflictError
        service = ClusteringService(
            clustering_graph=mock_graph,
            cluster_repository=mock_cluster_repository,
            cluster_suggestion_repository=mock_suggestion_repository,
            fact_repository=mock_fact_repository,
            assignment_repository=mock_assignment_repository,
            project_repository=mock_project_repository,
            event_bus=mock_event_bus,
            settings=mock_settings,
        )

        # Manuell als laufend markieren
        service._running_recluster.add(mock_project_id)

        with pytest.raises(ConflictError):
            await service.full_recluster(mock_project_id)


# ============================================================
# AC 10: Fehlerbehandlung
# ============================================================

class TestClusteringFailure:
    """AC 10: Clustering-Fehler → clustering_status='failed', SSE-Event."""

    @pytest.mark.asyncio
    async def test_clustering_failure_sets_failed_status_and_publishes_sse(
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
        """GIVEN ClusteringGraph wirft Exception
        WHEN process_interview() ausgefuehrt
        THEN clustering_status='failed', SSE clustering_failed mit unassigned_count"""
        mock_project_repository.get_by_id = AsyncMock(return_value=mock_project_row)
        mock_cluster_repository.list_for_project = AsyncMock(return_value=mock_existing_clusters)
        mock_fact_repository.get_facts_for_interview = AsyncMock(return_value=mock_facts_new)
        mock_assignment_repository.update_clustering_status = AsyncMock()

        mock_graph = AsyncMock()
        mock_graph.invoke = AsyncMock(side_effect=RuntimeError("LLM timeout after 3 retries"))

        from app.clustering.service import ClusteringService
        service = ClusteringService(
            clustering_graph=mock_graph,
            cluster_repository=mock_cluster_repository,
            cluster_suggestion_repository=mock_suggestion_repository,
            fact_repository=mock_fact_repository,
            assignment_repository=mock_assignment_repository,
            project_repository=mock_project_repository,
            event_bus=mock_event_bus,
            settings=mock_settings,
        )

        await service.process_interview(mock_project_id, mock_interview_id)

        # Verify: clustering_status="failed"
        mock_assignment_repository.update_clustering_status.assert_called_with(
            mock_interview_id, "failed"
        )
        # Verify: SSE clustering_failed publiziert
        publish_calls = mock_event_bus.publish.call_args_list
        failed_events = [c for c in publish_calls if c[0][1] == "clustering_failed"]
        assert len(failed_events) == 1


# ============================================================
# AC 1: Clustering-Trigger nach Fact Extraction
# ============================================================

class TestClusteringTriggerAfterExtraction:
    """AC 1: FactExtractionService triggert ClusteringService nach Extraktion."""

    @pytest.mark.asyncio
    async def test_fact_extraction_triggers_clustering_when_service_set(self):
        """GIVEN FactExtractionService hat _clustering_service gesetzt
        WHEN process_interview() erfolgreich abschliesst (gemockt)
        THEN asyncio.create_task(clustering_service.process_interview(...)) aufgerufen"""
        mock_clustering_service = AsyncMock()
        mock_clustering_service.process_interview = AsyncMock()

        from app.clustering.extraction import FactExtractionService

        mock_fact_repo = AsyncMock()
        mock_assignment_repo = AsyncMock()
        mock_event_bus = AsyncMock()
        mock_settings = MagicMock()
        mock_settings.openrouter_api_key = "test-key"
        mock_settings.extraction_model_default = "anthropic/claude-haiku-4"

        service = FactExtractionService(
            fact_repository=mock_fact_repo,
            assignment_repository=mock_assignment_repo,
            event_bus=mock_event_bus,
            settings=mock_settings,
            clustering_service=mock_clustering_service,
        )

        project_id = str(uuid.uuid4())
        interview_id = str(uuid.uuid4())

        # Interne Extraktion mocken: LLM-Call ueberspringen
        service._extract_facts_via_llm = AsyncMock(return_value=[
            {"content": "User cannot find settings page.", "quote": "I can't find it."}
        ])
        mock_fact_repo.save_facts = AsyncMock(return_value=[
            {"id": str(uuid.uuid4()), "content": "User cannot find settings page."}
        ])
        mock_assignment_repo.update_extraction_status = AsyncMock()
        mock_assignment_repo.get_interview_source = AsyncMock(return_value={
            "interview_id": interview_id,
            "project_id": project_id,
            "extraction_source": "summary",
        })

        with patch("asyncio.create_task") as mock_create_task:
            await service.process_interview(project_id, interview_id)

        mock_create_task.assert_called_once()
        # Argument muss eine Coroutine von clustering_service.process_interview sein
        call_args = mock_create_task.call_args[0][0]
        # Coroutine-Name pruefen
        assert "process_interview" in call_args.__qualname__


# ============================================================
# ACCEPTANCE TESTS (fuer Orchestrator)
# ============================================================

class TestClusteringPipelineAcceptance:
    """Acceptance Tests fuer End-to-End Clustering-Pipeline."""

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
        THEN mind. 1 Cluster erstellt, Facts zugeordnet, status='completed', SSE 'clustering_completed'"""
        mock_project_repository.get_by_id = AsyncMock(return_value=mock_project_row)
        mock_cluster_repository.list_for_project = AsyncMock(return_value=[])
        mock_fact_repository.get_facts_for_interview = AsyncMock(return_value=mock_facts_new)
        mock_assignment_repository.update_clustering_status = AsyncMock()

        new_cluster_uuid = str(uuid.uuid4())
        mock_cluster_repository.create_clusters = AsyncMock(
            return_value=[{"id": new_cluster_uuid, "name": "Navigation Issues"}]
        )
        mock_cluster_repository.update_summary = AsyncMock()
        mock_cluster_repository.update_counts = AsyncMock()
        mock_fact_repository.update_cluster_assignments = AsyncMock()
        mock_suggestion_repository.save_suggestions = AsyncMock(return_value=[])

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

        from app.clustering.service import ClusteringService
        service = ClusteringService(
            clustering_graph=mock_graph,
            cluster_repository=mock_cluster_repository,
            cluster_suggestion_repository=mock_suggestion_repository,
            fact_repository=mock_fact_repository,
            assignment_repository=mock_assignment_repository,
            project_repository=mock_project_repository,
            event_bus=mock_event_bus,
            settings=mock_settings,
        )

        await service.process_interview(mock_project_id, mock_interview_id)

        # Ergebnis: clustering_status="completed"
        mock_assignment_repository.update_clustering_status.assert_called_with(
            mock_interview_id, "completed"
        )
        # Ergebnis: mind. 1 Cluster angelegt
        mock_cluster_repository.create_clusters.assert_called_once()
        # Ergebnis: SSE clustering_completed
        publish_calls = mock_event_bus.publish.call_args_list
        completed_events = [c for c in publish_calls if c[0][1] == "clustering_completed"]
        assert len(completed_events) == 1
```
</test_spec>

---

## Definition of Done

- [x] Akzeptanzkriterien sind eindeutig & vollstaendig
- [ ] Telemetrie/Logging: Alle Node-Aufrufe geloggt mit `logger.info(f"[ClusteringGraph] Node {node_name} started/completed")`
- [ ] Sicherheits-/Privacy-Aspekte: Keine PII in Logs (kein Quotetext, kein Transcript-Inhalt)
- [ ] Rollout-/Rollback-Plan: Falls Clustering fehlschlaegt, bleiben Facts erhalten (`cluster_id=NULL`), kein Datenverlust

---

## Constraints & Hinweise

**Betrifft:**
- `backend/app/clustering/` Modul (alle neuen Dateien hier)
- `backend/app/clustering/extraction.py` wird rueckwaertskompatibel erweitert
- Kein neues externes Python-Paket noetig (`langgraph`, `langchain_openai` bereits installiert)

**API Contract:**
- `POST /api/projects/{id}/clustering/recluster` gibt sofort `200` zurueck (Recluster laeuft async)
- `GET /api/projects/{id}/clustering/status` ist lese-only (kein State-Seiteneffekt)
- Alle Cluster-Endpoints aus architecture.md (`GET /clusters`, `GET /clusters/{cid}`, etc.) kommen in **Slice 6** (Taxonomy-Editing)

**Abgrenzung:**
- Cluster-CRUD (Rename, Merge, Split via User-Aktion) → **Slice 6**
- Dashboard-Frontend (Cluster-Cards, Progress-Bar) → **Slice 4**
- SSE-Streaming-Endpoint (`GET /events`) → **Slice 7**
- Auth-Middleware fuer alle Endpoints → **Slice 8** (hier: kein Auth-Check, Stub)

---

## Integration Contract (GATE 2 PFLICHT)

> **Wichtig:** Diese Section wird vom Gate 2 Compliance Agent geprueft. Unvollstaendige Contracts blockieren die Genehmigung.

### Requires From Other Slices

| Slice | Resource | Type | Validation |
|-------|----------|------|------------|
| slice-01 | `projects` Tabelle | DB Schema | EXISTS: `id`, `research_goal`, `model_clustering`, `model_summary` |
| slice-01 | `clusters` Tabelle | DB Schema | EXISTS: `id`, `project_id`, `name`, `summary`, `fact_count`, `interview_count` |
| slice-01 | `facts` Tabelle | DB Schema | EXISTS: `id`, `cluster_id` (nullable), `project_id`, `interview_id`, `content` |
| slice-01 | `cluster_suggestions` Tabelle | DB Schema | EXISTS: `id`, `project_id`, `type`, `source_cluster_id`, `status` |
| slice-01 | `project_interviews` Tabelle | DB Schema | EXISTS: `clustering_status` Spalte |
| slice-01 | `ProjectRepository` | Class | Method: `get_by_id(project_id) → dict` |
| slice-01 | `InterviewAssignmentRepository` | Class | Method: `find_by_interview_id() → dict|None` |
| slice-02 | `FactRepository` | Class | Methods: `get_facts_for_interview()`, `get_facts_for_project()` |
| slice-02 | `FactExtractionService` | Class | Erweitert via optionalen `clustering_service` Parameter (gespeichert als `self._clustering_service`) |
| slice-02 | `SseEventBus` | Class | Method: `publish()` (Singleton) — nur fuer Outbound-Events, kein subscribe() fuer Clustering-Trigger |

### Provides To Other Slices

| Resource | Type | Consumer | Interface |
|----------|------|----------|-----------|
| `ClusteringService` | Class | slice-04, slice-06, slice-07 | `process_interview(project_id, interview_id) → None` (async) |
| `ClusteringService.full_recluster()` | Method | slice-06 (UI-Trigger) | `(project_id: str) → None` (async) |
| `ClusterRepository` | Class | slice-04, slice-05, slice-06 | `list_for_project()`, `get_by_id()`, `create_clusters()`, `update_summary()`, `delete_all_for_project()` |
| `ClusterSuggestionRepository` | Class | slice-06 | `list_pending_for_project()`, `update_status()` |
| `FactRepository.update_cluster_assignments()` | Method | slice-06 | `(assignments: list[dict]) → None` |
| `FactRepository.reset_cluster_assignments_for_project()` | Method | Intern (Full Re-Cluster) | `(project_id: str) → None` |
| `clusters`-Tabelle mit Daten | DB State | slice-04 (Dashboard) | `list_for_project(project_id)` liefert Cluster-Cards-Daten |
| `cluster_suggestions`-Tabelle | DB State | slice-06 | `list_pending_for_project()` fuer Suggestions-Banners |
| `clustering_started` SSE-Event | Event | slice-07 | Data: `{mode: "incremental"|"full"}` |
| `clustering_updated` SSE-Event | Event | slice-07 | Data: `{clusters: [{id, name, fact_count}]}` |
| `clustering_completed` SSE-Event | Event | slice-07 | Data: `{cluster_count, fact_count}` |
| `clustering_failed` SSE-Event | Event | slice-04, slice-07 | Data: `{error, unassigned_count}` |
| `suggestion` SSE-Event | Event | slice-06, slice-07 | Data: `{type, source_cluster_id, target_cluster_id?, similarity_score?}` |
| `POST /api/projects/{id}/clustering/recluster` | REST Endpoint | slice-06 (UI) | Response: `ReclusterStarted` |
| `GET /api/projects/{id}/clustering/status` | REST Endpoint | slice-04 (Dashboard Progress) | Response: `PipelineStatus` |

### Integration Validation Tasks

- [ ] `FactExtractionService(clustering_service=...)` Parameter akzeptiert und Trigger implementiert
- [ ] `ClusterRepository.list_for_project()` gibt korrekte Datenstruktur fuer Dashboard-Slice-04 zurueck
- [ ] `SseEventBus`-Singleton ist identisch mit Slice-2-Instanz (kein zweites Instanz)
- [ ] `clustering_status` Tracking konsistent mit `extraction_status` Pattern aus Slice 2

---

## Code Examples (MANDATORY - GATE 2 PFLICHT)

> **KRITISCH:** Alle Code-Beispiele in diesem Dokument sind **PFLICHT-Deliverables**.
> Der Gate 2 Compliance Agent prueft, dass jedes Code-Beispiel implementiert wird.
> Abweichung nur mit expliziter Begruendung im Commit erlaubt.

| Code Example | Section | Mandatory | Notes |
|--------------|---------|-----------|-------|
| `ClusteringState` TypedDict | Section 3 | YES | Exakt diese Felder, TypedDict |
| `ClusteringGraph._build_graph()` | Section 4 | YES | Alle 6 Nodes, conditional entry point |
| `ClusteringGraph._route_after_validation()` | Section 4 | YES | MAX_CORRECTION_ITERATIONS = 3 |
| `ConflictError` Exception-Klasse | Section 5 | YES | In `service.py` definiert, vor `ClusteringService` |
| `ClusteringService.__init__()` | Section 5 | YES | Alle 8 Parameter, `_running_recluster: set[str]` |
| `ClusteringService.process_interview()` | Section 5 | YES | mode-Detection, Background-Task Pattern |
| `ClusterRepository` (alle Methoden) | Section 6 | YES | Raw SQL + SQLAlchemy async Pattern |
| `ClusterSuggestionRepository` (alle Methoden) | Section 7 | YES | save_suggestions loescht vorhandene pending |
| `GENERATE_TAXONOMY_PROMPT` | Section 8 | YES | Mini-Batch-Parameter (`batch_number`, `total_batches`) |
| `ASSIGN_FACTS_PROMPT` | Section 8 | YES | GoalEx-Pattern mit `research_goal` |
| `VALIDATE_QUALITY_PROMPT` | Section 8 | YES | JSON Output mit `quality_ok` + `issues` |
| `REFINE_CLUSTERS_PROMPT` | Section 8 | YES | Corrections-Only Format |
| `GENERATE_SUMMARIES_PROMPT` | Section 8 | YES | Pro-Cluster, `model_summary` Modell |
| `CHECK_SUGGESTIONS_PROMPT` | Section 8 | YES | `split_threshold` Parameter |
| `ReclusterStarted` Pydantic DTO | Section 9 | YES | `status`, `message`, `project_id` |
| `PipelineStatus` Pydantic DTO | Section 9 | YES | `status`, `mode`, `progress`, `current_step` |
| `FactRepository.update_cluster_assignments()` | Section 10 | YES | Bulk-UPDATE Interface |
| `FactRepository.reset_cluster_assignments_for_project()` | Section 10 | YES | `UPDATE facts SET cluster_id = NULL` |
| `InterviewAssignmentRepository.update_clustering_status()` | Section 11 | YES | Separate von `update_extraction_status` |
| `FactExtractionService` Clustering-Trigger | Section 12 | YES | `fire-and-forget` via `asyncio.create_task()` |
| Settings-Felder fuer ClusteringGraph | Section 13 | YES | Alle 5 neuen Felder in `Settings` |

---

## Links

- Design/Spec: `specs/phase-4/2026-02-28-llm-interview-clustering/architecture.md` → LangGraph ClusteringGraph Design
- Discovery: `specs/phase-4/2026-02-28-llm-interview-clustering/discovery.md` → Clustering-Architektur Konzept
- Referenz-Pattern: `backend/app/interview/graph.py` (InterviewGraph — gleicher StateGraph-Pattern)
- Vorheriger Slice: `slice-02-fact-extraction-pipeline.md` (SseEventBus, FactRepository, Trigger-Punkt)
- Forschungsquellen: TNT-LLM (arXiv 2403.12173), GoalEx (arXiv 2305.13749), Anthropic Clio

---

## Deliverables (SCOPE SAFEGUARD)

**WICHTIG: Diese Liste wird automatisch vom Stop-Hook validiert. Der Agent kann nicht stoppen, wenn Dateien fehlen.**

<!-- DELIVERABLES_START -->
### Backend

- [ ] `backend/app/clustering/graph_state.py` — `ClusteringState` TypedDict mit allen Feldern
- [ ] `backend/app/clustering/graph.py` — `ClusteringGraph` LangGraph StateGraph mit 6 Nodes und Self-Correction Loop
- [ ] `backend/app/clustering/service.py` — `ConflictError` Exception-Klasse + `ClusteringService` mit `process_interview()`, `full_recluster()`, `_persist_results()`, `_update_counts()` (importierbar: `from app.clustering.service import ClusteringService, ConflictError`)
- [ ] `backend/app/clustering/cluster_repository.py` — `ClusterRepository` mit allen CRUD-Methoden
- [ ] `backend/app/clustering/cluster_suggestion_repository.py` — `ClusterSuggestionRepository` mit `save_suggestions()`, `list_pending_for_project()`, `update_status()`
- [ ] `backend/app/clustering/prompts.py` — Erweitert um 6 neue Prompt-Templates (GENERATE_TAXONOMY, ASSIGN_FACTS, VALIDATE_QUALITY, REFINE_CLUSTERS, GENERATE_SUMMARIES, CHECK_SUGGESTIONS)
- [ ] `backend/app/clustering/schemas.py` — Erweitert um `ReclusterStarted`, `PipelineStatus` Pydantic DTOs
- [ ] `backend/app/clustering/router.py` — Erweitert um `POST /api/projects/{id}/clustering/recluster` und `GET /api/projects/{id}/clustering/status`
- [ ] `backend/app/clustering/extraction.py` — Erweitert um optionalen `clustering_service` Parameter (gespeichert als `self._clustering_service`) und Clustering-Trigger nach erfolgreicher Extraktion
- [ ] `backend/app/clustering/fact_repository.py` — Erweitert um `update_cluster_assignments()` und `reset_cluster_assignments_for_project()`
- [ ] `backend/app/clustering/interview_assignment_repository.py` — Erweitert um `update_clustering_status()` und `get_all_for_project()`
- [ ] `backend/app/api/dependencies.py` — Erweitert um `get_clustering_service()`, `get_cluster_repository()`, `get_cluster_suggestion_repository()` Singletons
- [ ] `backend/app/config/settings.py` — Erweitert um 5 neue ClusteringGraph-Felder

### Frontend

_(kein Frontend in diesem Slice)_

### Tests

- [ ] `backend/tests/slices/llm-interview-clustering/test_slice_03_clustering_pipeline_agent.py` — Alle Testfaelle fuer AC 1-10
<!-- DELIVERABLES_END -->

**Hinweis fuer den Implementierungs-Agent:**
- Alle Dateien zwischen `<!-- DELIVERABLES_START -->` und `<!-- DELIVERABLES_END -->` sind **Pflicht**
- Der Stop-Hook prueft automatisch ob alle Dateien existieren
- Bei fehlenden Dateien wird der Agent blockiert und muss nachfragen

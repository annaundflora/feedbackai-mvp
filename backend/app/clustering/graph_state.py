"""ClusteringState -- TypedDict fuer den ClusteringGraph LangGraph StateGraph.

Folgt dem Pattern aus backend/app/interview/graph.py (InterviewGraph).
"""
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

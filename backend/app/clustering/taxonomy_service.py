"""TaxonomyService + SummaryGenerationService fuer Taxonomy-Editing (Slice 6).

TaxonomyService:
  - rename(): Cluster umbenennen (kein Summary-Regen, kein Re-Clustering)
  - merge(): Alle Facts aus Source in Target verschieben, Source loeschen, 30s Undo-Fenster
  - undo_merge(): Merge rueckgaengig machen (innerhalb 30s)
  - preview_split(): LLM analysiert Cluster und schlaegt Sub-Cluster vor (KEIN DB-Write)
  - execute_split(): Split durchfuehren, Original-Cluster loeschen, neue anlegen

SummaryGenerationService:
  - regenerate_for_cluster(): Summary eines einzelnen Clusters neu generieren
  - propose_split(): LLM-Vorschlag fuer Sub-Cluster (Preview ohne DB-Write)

Undo-Mechanismus: In-Memory dict (_undo_store) mit 30s TTL.
Bei Server-Neustart gehen Undo-Records verloren (MVP akzeptabel).
"""
import asyncio
import json
import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from langchain_openai import ChatOpenAI

from app.clustering.cluster_repository import ClusterRepository
from app.clustering.exceptions import (
    ClusterNotFoundError,
    MergeConflictError,
    SplitValidationError,
    UndoExpiredError,
)
from app.clustering.fact_repository import FactRepository
from app.clustering.schemas import (
    ClusterResponse,
    FactResponse,
    MergeResponse,
    SplitPreviewResponse,
    SplitPreviewSubcluster,
)

logger = logging.getLogger(__name__)

SPLIT_PREVIEW_PROMPT = """You are a qualitative research analyst. Analyze the facts in this cluster and propose how to split it into 2-4 meaningful sub-clusters.

Cluster Name: {cluster_name}

Facts in this cluster:
{facts_text}

Propose sub-clusters where each sub-cluster has a distinct theme. Each fact must appear in exactly one sub-cluster.

Return ONLY a valid JSON array. No preamble, no explanation.

Format:
[
  {{
    "name": "Sub-Cluster Name 1",
    "fact_ids": ["uuid1", "uuid2", ...]
  }},
  {{
    "name": "Sub-Cluster Name 2",
    "fact_ids": ["uuid3", "uuid4", ...]
  }}
]"""

REGENERATE_SUMMARY_PROMPT = """You are a qualitative research analyst. Write a concise summary for a thematic cluster.

Cluster Name: {cluster_name}

Facts in this cluster:
{facts_text}

Write a 2-4 sentence summary that:
- Captures the main theme across all facts
- Is written from the user's perspective
- Highlights the most significant pattern

Return ONLY the summary text. No preamble, no quotes."""


class SummaryGenerationService:
    """Generiert und regeneriert Cluster-Summaries via LLM.

    Wird von TaxonomyService nach Merge/Split aufgerufen (fire-and-forget).
    """

    def __init__(self, settings: Any) -> None:
        self._settings = settings

    def _get_llm(self) -> ChatOpenAI:
        """Gibt LLM-Client fuer Summary-Generierung zurueck."""
        model = getattr(self._settings, "summary_model_default", "anthropic/claude-haiku-4")
        return ChatOpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=self._settings.openrouter_api_key,
            model=model,
            temperature=0.0,
        )

    def _format_facts_text(self, facts: list[dict]) -> str:
        """Formatiert Facts als lesbaren Text fuer Prompts."""
        lines = []
        for i, fact in enumerate(facts, 1):
            fact_id = str(fact.get("id", "unknown"))
            content = fact.get("content", "")
            lines.append(f"{i}. [ID: {fact_id}] {content}")
        return "\n".join(lines)

    def _parse_json_response(self, content: str, expected_type: type) -> list | dict:
        """Parst JSON-Response vom LLM mit Fallback."""
        import re

        if isinstance(content, list):
            content = "".join(str(c) for c in content)

        try:
            parsed = json.loads(content)
            if isinstance(parsed, expected_type):
                return parsed
        except (json.JSONDecodeError, ValueError):
            pass

        json_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", content)
        if json_match:
            try:
                parsed = json.loads(json_match.group(1).strip())
                if isinstance(parsed, expected_type):
                    return parsed
            except (json.JSONDecodeError, ValueError):
                pass

        if expected_type == list:
            array_match = re.search(r"\[[\s\S]*\]", content)
            if array_match:
                try:
                    parsed = json.loads(array_match.group(0))
                    if isinstance(parsed, list):
                        return parsed
                except (json.JSONDecodeError, ValueError):
                    pass
            return []
        else:
            obj_match = re.search(r"\{[\s\S]*\}", content)
            if obj_match:
                try:
                    parsed = json.loads(obj_match.group(0))
                    if isinstance(parsed, dict):
                        return parsed
                except (json.JSONDecodeError, ValueError):
                    pass
            return {}

    async def regenerate_for_cluster(
        self,
        project_id: str,
        cluster_id: str,
        cluster_repo: ClusterRepository | None = None,
        fact_repo: FactRepository | None = None,
    ) -> None:
        """Regeneriert die Summary eines einzelnen Clusters.

        Laeuft als Background-Task (fire-and-forget aus Sicht des Callers).
        Schreibt direkt in DB via cluster_repo.update_summary().

        Args:
            project_id: Projekt-UUID.
            cluster_id: Cluster-UUID.
            cluster_repo: Optionales ClusterRepository (fuer DI in TaxonomyService).
            fact_repo: Optionales FactRepository (fuer DI in TaxonomyService).
        """
        if cluster_repo is None or fact_repo is None:
            logger.warning(
                f"regenerate_for_cluster called without repos for cluster {cluster_id} -- skipping"
            )
            return

        try:
            cluster = await cluster_repo.get_by_id(cluster_id=cluster_id, project_id=project_id)
            if cluster is None:
                logger.warning(f"regenerate_for_cluster: cluster {cluster_id} not found")
                return

            facts = await fact_repo.get_by_cluster(cluster_id=cluster_id, project_id=project_id)
            if not facts:
                logger.info(f"regenerate_for_cluster: no facts for cluster {cluster_id}, skipping")
                return

            cluster_name = cluster.get("name", "")
            facts_text = self._format_facts_text(facts)
            prompt = REGENERATE_SUMMARY_PROMPT.format(
                cluster_name=cluster_name,
                facts_text=facts_text,
            )

            llm = self._get_llm()
            response = await llm.ainvoke(prompt)
            content = response.content
            if isinstance(content, list):
                content = "".join(str(c) for c in content)
            summary = content.strip()

            await cluster_repo.update_summary(cluster_id=cluster_id, summary=summary)
            logger.info(f"regenerate_for_cluster: summary updated for cluster {cluster_id}")

        except Exception as e:
            logger.error(f"regenerate_for_cluster failed for cluster {cluster_id}: {e}", exc_info=True)

    async def propose_split(
        self,
        cluster_name: str,
        facts: list[dict],
        project_id: str,
    ) -> list[dict]:
        """LLM schlaegt Sub-Cluster fuer Split-Preview vor.

        KEINE DB-Schreiboperation.

        Returns:
            Liste von {name, facts} Dicts.
        """
        facts_text = self._format_facts_text(facts)
        prompt = SPLIT_PREVIEW_PROMPT.format(
            cluster_name=cluster_name,
            facts_text=facts_text,
        )

        try:
            llm = self._get_llm()
            response = await llm.ainvoke(prompt)
            content = response.content
            raw_subclusters = self._parse_json_response(content, list)

            # Facts per ID mappen fuer Lookup
            facts_by_id = {str(f.get("id", "")): f for f in facts}

            result = []
            for sc in raw_subclusters:
                if not isinstance(sc, dict):
                    continue
                name = sc.get("name", "")
                fact_ids = sc.get("fact_ids", [])
                if not name:
                    continue
                sc_facts = [facts_by_id[fid] for fid in fact_ids if fid in facts_by_id]
                result.append({"name": name, "facts": sc_facts})

            if len(result) >= 2:
                return result

            # Fallback: 2 gleichmaessige Haelften
            logger.warning(f"propose_split: LLM returned <2 subclusters, using fallback split")
            mid = max(1, len(facts) // 2)
            return [
                {"name": f"{cluster_name} (Part 1)", "facts": facts[:mid]},
                {"name": f"{cluster_name} (Part 2)", "facts": facts[mid:]},
            ]

        except Exception as e:
            logger.error(f"propose_split LLM call failed: {e}", exc_info=True)
            mid = max(1, len(facts) // 2)
            return [
                {"name": f"{cluster_name} (Part 1)", "facts": facts[:mid]},
                {"name": f"{cluster_name} (Part 2)", "facts": facts[mid:]},
            ]


class TaxonomyService:
    """Service fuer Taxonomy-Editing: Rename, Merge, Split, Fact-Move.

    Undo-Mechanismus: In-Memory dict (_undo_store), 30s TTL.
    Bei Server-Neustart gehen Undo-Records verloren (MVP akzeptabel).
    """

    def __init__(
        self,
        cluster_repo: ClusterRepository,
        fact_repo: FactRepository,
        summary_service: SummaryGenerationService,
    ) -> None:
        self._cluster_repo = cluster_repo
        self._fact_repo = fact_repo
        self._summary_service = summary_service
        self._undo_store: dict[str, dict[str, Any]] = {}  # In-memory, keyed by undo_id

    async def rename(
        self, project_id: str, cluster_id: str, name: str
    ) -> ClusterResponse:
        """Benennt einen Cluster um.

        Kein Summary-Regen, kein Re-Clustering.
        """
        cluster = await self._cluster_repo.update_name(
            project_id=project_id,
            cluster_id=cluster_id,
            name=name,
        )
        if cluster is None:
            raise ClusterNotFoundError(cluster_id)
        return ClusterResponse.model_validate(cluster)

    async def merge(
        self,
        project_id: str,
        source_id: str,
        target_id: str,
    ) -> MergeResponse:
        """Verschiebt alle Facts von Source nach Target, loescht Source, 30s Undo-Fenster.

        [1] Validierung
        [2] Snapshot fuer Undo erstellen
        [3] Undo-Record in Memory speichern (30s TTL)
        [4] Facts verschieben
        [5] Source-Cluster loeschen
        [6] Counts aktualisieren
        [7] Summary-Regen als Background-Task
        """
        if source_id == target_id:
            raise MergeConflictError("Cannot merge cluster with itself")

        source = await self._cluster_repo.get_by_id(project_id=project_id, cluster_id=source_id)
        target = await self._cluster_repo.get_by_id(project_id=project_id, cluster_id=target_id)

        if source is None:
            raise ClusterNotFoundError(source_id)
        if target is None:
            raise ClusterNotFoundError(target_id)

        # Snapshot fuer Undo
        source_facts = await self._fact_repo.get_by_cluster(
            cluster_id=source_id, project_id=project_id
        )
        undo_id = str(uuid.uuid4())
        undo_expires_at = datetime.now(timezone.utc) + timedelta(seconds=30)

        self._undo_store[undo_id] = {
            "source_cluster": {
                "id": str(source["id"]),
                "name": source["name"],
                "project_id": project_id,
            },
            "source_fact_ids": [str(f["id"]) for f in source_facts],
            "target_id": target_id,
            "expires_at": undo_expires_at,
        }

        # Async expire nach 30s (via asyncio.create_task fuer Background-Cleanup)
        asyncio.create_task(self._expire_undo(undo_id, 30))

        # Facts verschieben
        await self._fact_repo.move_bulk(
            fact_ids=[str(f["id"]) for f in source_facts],
            target_cluster_id=target_id,
            project_id=project_id,
        )

        # Source-Cluster loeschen
        await self._cluster_repo.delete(project_id=project_id, cluster_id=source_id)

        # Counts aktualisieren
        merged = await self._cluster_repo.recalculate_counts(
            project_id=project_id, cluster_id=target_id
        )

        # Summary Background-Task (wird nach HTTP-Response ausgefuehrt)
        asyncio.create_task(
            self._summary_service.regenerate_for_cluster(
                project_id=project_id,
                cluster_id=target_id,
                cluster_repo=self._cluster_repo,
                fact_repo=self._fact_repo,
            )
        )

        return MergeResponse(
            merged_cluster=ClusterResponse.model_validate(merged),
            undo_id=undo_id,
            undo_expires_at=undo_expires_at.isoformat(),
        )

    async def undo_merge(
        self,
        project_id: str,
        undo_id: str,
    ) -> ClusterResponse:
        """Stellt Source-Cluster aus Undo-Snapshot wieder her (innerhalb 30s).

        [1] Undo-Record validieren (existiert + nicht abgelaufen)
        [2] Source-Cluster neu anlegen
        [3] Facts zurueckverschieben
        [4] Counts fuer beide Cluster aktualisieren
        [5] Summary-Regen fuer beide als Background-Task
        """
        record = self._undo_store.get(undo_id)
        if record is None:
            raise UndoExpiredError("Undo window expired or invalid undo_id")

        if datetime.now(timezone.utc) > record["expires_at"]:
            del self._undo_store[undo_id]
            raise UndoExpiredError("Undo window expired")

        source_info = record["source_cluster"]
        fact_ids = record["source_fact_ids"]
        target_id = record["target_id"]

        # Source-Cluster wiederherstellen
        restored = await self._cluster_repo.create(
            project_id=project_id,
            name=source_info["name"],
        )
        restored_id = str(restored["id"])

        # Facts zurueckverschieben
        await self._fact_repo.move_bulk(
            fact_ids=fact_ids,
            target_cluster_id=restored_id,
            project_id=project_id,
        )

        # Counts aktualisieren
        await self._cluster_repo.recalculate_counts(
            project_id=project_id, cluster_id=restored_id
        )
        await self._cluster_repo.recalculate_counts(
            project_id=project_id, cluster_id=target_id
        )

        # Summaries fuer beide Cluster Background-Task
        asyncio.create_task(
            self._summary_service.regenerate_for_cluster(
                project_id=project_id,
                cluster_id=restored_id,
                cluster_repo=self._cluster_repo,
                fact_repo=self._fact_repo,
            )
        )
        asyncio.create_task(
            self._summary_service.regenerate_for_cluster(
                project_id=project_id,
                cluster_id=target_id,
                cluster_repo=self._cluster_repo,
                fact_repo=self._fact_repo,
            )
        )

        del self._undo_store[undo_id]

        result = await self._cluster_repo.get_by_id(
            project_id=project_id, cluster_id=restored_id
        )
        return ClusterResponse.model_validate(result)

    async def preview_split(
        self,
        project_id: str,
        cluster_id: str,
    ) -> SplitPreviewResponse:
        """LLM schlaegt Sub-Cluster vor.

        KEINE DB-Schreiboperation.
        """
        cluster = await self._cluster_repo.get_by_id(
            project_id=project_id, cluster_id=cluster_id
        )
        if cluster is None:
            raise ClusterNotFoundError(cluster_id)

        facts = await self._fact_repo.get_by_cluster(
            cluster_id=cluster_id, project_id=project_id
        )

        subclusters = await self._summary_service.propose_split(
            cluster_name=cluster["name"],
            facts=facts,
            project_id=project_id,
        )

        return SplitPreviewResponse(
            subclusters=[
                SplitPreviewSubcluster(
                    name=sc["name"],
                    fact_count=len(sc["facts"]),
                    facts=[
                        FactResponse(
                            id=str(f["id"]),
                            content=f["content"],
                            quote=f.get("quote"),
                            confidence=f.get("confidence"),
                            interview_id=str(f["interview_id"]),
                            interview_date=f.get("interview_date"),
                            cluster_id=str(f["cluster_id"]) if f.get("cluster_id") else None,
                        )
                        for f in sc["facts"]
                    ],
                )
                for sc in subclusters
            ]
        )

    async def execute_split(
        self,
        project_id: str,
        cluster_id: str,
        subclusters: list[dict],
    ) -> list[ClusterResponse]:
        """Fuehrt den Split durch.

        [1] Validierung: alle fact_ids gehoeren zu original cluster, min 2 subclusters
        [2] Neue Cluster anlegen
        [3] Facts zu neuen Clustern verschieben
        [4] Original-Cluster loeschen
        [5] Counts aktualisieren
        [6] Summary-Regen fuer neue Cluster als Background-Task
        """
        original = await self._cluster_repo.get_by_id(
            project_id=project_id, cluster_id=cluster_id
        )
        if original is None:
            raise ClusterNotFoundError(cluster_id)

        if len(subclusters) < 2:
            raise SplitValidationError("Split must produce at least 2 clusters")

        # Validierung: alle fact_ids muessen zu original cluster gehoeren
        all_original_facts = await self._fact_repo.get_by_cluster(
            cluster_id=cluster_id, project_id=project_id
        )
        all_original_fact_ids: set[str] = {str(f["id"]) for f in all_original_facts}

        submitted_fact_ids: set[str] = set()
        for sc in subclusters:
            for fid in sc.get("fact_ids", []):
                submitted_fact_ids.add(str(fid))

        if submitted_fact_ids != all_original_fact_ids:
            raise SplitValidationError(
                "All facts must be assigned to exactly one subcluster"
            )

        new_clusters = []
        for sc in subclusters:
            new_cluster = await self._cluster_repo.create(
                project_id=project_id,
                name=sc["name"],
            )
            new_cluster_id = str(new_cluster["id"])

            await self._fact_repo.move_bulk(
                fact_ids=[str(fid) for fid in sc.get("fact_ids", [])],
                target_cluster_id=new_cluster_id,
                project_id=project_id,
            )

            updated = await self._cluster_repo.recalculate_counts(
                project_id=project_id, cluster_id=new_cluster_id
            )
            new_clusters.append(updated)

            asyncio.create_task(
                self._summary_service.regenerate_for_cluster(
                    project_id=project_id,
                    cluster_id=new_cluster_id,
                    cluster_repo=self._cluster_repo,
                    fact_repo=self._fact_repo,
                )
            )

        # Original-Cluster loeschen
        await self._cluster_repo.delete(project_id=project_id, cluster_id=cluster_id)

        return [ClusterResponse.model_validate(c) for c in new_clusters]

    async def _expire_undo(self, undo_id: str, delay_seconds: int) -> None:
        """Entfernt Undo-Record nach delay_seconds aus dem Store."""
        await asyncio.sleep(delay_seconds)
        self._undo_store.pop(undo_id, None)

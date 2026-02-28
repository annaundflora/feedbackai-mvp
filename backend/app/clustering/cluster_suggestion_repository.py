"""ClusterSuggestionRepository -- CRUD fuer die cluster_suggestions-Tabelle.

Speichert LLM-generierte Merge/Split-Vorschlaege.
Status: 'pending' | 'accepted' | 'dismissed'
"""
import json
import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

logger = logging.getLogger(__name__)


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
        if not suggestions:
            return []

        results = []
        now = datetime.now(timezone.utc)

        async with self._session_factory() as session:
            for suggestion in suggestions:
                source_cluster_id = suggestion.get("source_cluster_id")
                if not source_cluster_id:
                    continue

                # Vorhandene 'pending' Suggestions fuer denselben source_cluster_id loeschen
                await session.execute(
                    text(
                        "DELETE FROM cluster_suggestions "
                        "WHERE source_cluster_id = :source_cluster_id AND status = 'pending'"
                    ),
                    {"source_cluster_id": source_cluster_id},
                )

                suggestion_id = str(uuid.uuid4())
                suggestion_type = suggestion.get("type", "merge")
                target_cluster_id = suggestion.get("target_cluster_id")
                similarity_score = suggestion.get("similarity_score")
                proposed_data = suggestion.get("proposed_data") or suggestion.get("proposed_subclusters")

                # proposed_data als JSON speichern wenn es kein String ist
                if proposed_data is not None and not isinstance(proposed_data, str):
                    proposed_data = json.dumps(proposed_data)

                result = await session.execute(
                    text(
                        "INSERT INTO cluster_suggestions "
                        "(id, project_id, type, source_cluster_id, target_cluster_id, "
                        "similarity_score, proposed_data, status, created_at) "
                        "VALUES (:id, :project_id, :type, :source_cluster_id, :target_cluster_id, "
                        ":similarity_score, :proposed_data, 'pending', :created_at) "
                        "RETURNING id, project_id, type, source_cluster_id, target_cluster_id, "
                        "similarity_score, proposed_data, status, created_at"
                    ),
                    {
                        "id": suggestion_id,
                        "project_id": project_id,
                        "type": suggestion_type,
                        "source_cluster_id": source_cluster_id,
                        "target_cluster_id": target_cluster_id,
                        "similarity_score": similarity_score,
                        "proposed_data": proposed_data,
                        "created_at": now,
                    },
                )
                row = result.mappings().first()
                if row:
                    results.append(dict(row))

            await session.commit()

        logger.info(f"Saved {len(results)} suggestions for project {project_id}")
        return results

    async def list_pending_for_project(
        self,
        project_id: str,
    ) -> list[dict]:
        """Laedt alle offenen Suggestions eines Projekts (status='pending').

        Returns:
            Liste von {id, type, source_cluster_id, target_cluster_id?,
            similarity_score?, proposed_data?, created_at}.
        """
        async with self._session_factory() as session:
            result = await session.execute(
                text(
                    "SELECT id, project_id, type, source_cluster_id, target_cluster_id, "
                    "similarity_score, proposed_data, status, created_at "
                    "FROM cluster_suggestions "
                    "WHERE project_id = :project_id AND status = 'pending' "
                    "ORDER BY created_at DESC"
                ),
                {"project_id": project_id},
            )
            rows = result.mappings().all()
            return [dict(row) for row in rows]

    async def update_status(
        self,
        suggestion_id: str,
        status: str,  # 'accepted' | 'dismissed'
    ) -> dict:
        """Setzt Status einer Suggestion."""
        async with self._session_factory() as session:
            result = await session.execute(
                text(
                    "UPDATE cluster_suggestions "
                    "SET status = :status "
                    "WHERE id = :suggestion_id "
                    "RETURNING id, project_id, type, source_cluster_id, target_cluster_id, "
                    "similarity_score, proposed_data, status, created_at"
                ),
                {
                    "suggestion_id": suggestion_id,
                    "status": status,
                },
            )
            await session.commit()
            row = result.mappings().first()
            return dict(row) if row else {}

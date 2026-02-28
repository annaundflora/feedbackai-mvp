"""FactRepository -- CRUD fuer die facts-Tabelle.

Folgt exakt dem Pattern von InterviewRepository:
Raw SQL + SQLAlchemy async + text()
"""
import logging
from datetime import datetime, timezone

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

logger = logging.getLogger(__name__)


class FactRepository:
    """Repository fuer die facts-Tabelle.

    Kapselt alle DB-Operationen via SQLAlchemy async mit Raw SQL.
    Facts werden mit cluster_id=NULL (unassigned) gespeichert.
    """

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def save_facts(
        self,
        project_id: str,
        interview_id: str,
        facts: list[dict],
    ) -> list[dict]:
        """Speichert extrahierte Facts in der DB.

        Alle Facts werden mit cluster_id=NULL (unassigned) gespeichert.
        Atomare Operation: alle-oder-keine Speicherung pro Interview.

        Args:
            project_id: UUID als String.
            interview_id: UUID als String (referenziert mvp_interviews.session_id).
            facts: Liste von {content, quote, confidence} Dicts.

        Returns:
            Liste der gespeicherten Facts als Dicts (inkl. id, created_at).
        """
        if not facts:
            return []

        results = []
        now = datetime.now(timezone.utc)

        async with self._session_factory() as session:
            for fact in facts:
                content = fact.get("content", "")
                if not content:
                    continue

                # Werte bereinigen
                quote = fact.get("quote")
                confidence = fact.get("confidence")

                # Sicherstellen dass confidence ein Float ist
                if confidence is not None:
                    try:
                        confidence = float(confidence)
                        if not (0.0 <= confidence <= 1.0):
                            confidence = None
                    except (TypeError, ValueError):
                        confidence = None

                result = await session.execute(
                    text(
                        "INSERT INTO facts "
                        "(project_id, interview_id, cluster_id, content, quote, confidence, created_at) "
                        "VALUES (:project_id, :interview_id, NULL, :content, :quote, :confidence, :created_at) "
                        "RETURNING id, project_id, interview_id, cluster_id, content, quote, confidence, created_at"
                    ),
                    {
                        "project_id": project_id,
                        "interview_id": interview_id,
                        "content": content[:1000],  # Max 1000 Zeichen gemaess Schema
                        "quote": quote[:500] if quote else None,  # Max 500 Zeichen
                        "confidence": confidence,
                        "created_at": now,
                    },
                )
                row = result.mappings().first()
                if row:
                    results.append(dict(row))

            await session.commit()

        logger.info(f"Saved {len(results)} facts for interview {interview_id} in project {project_id}")
        return results

    async def get_facts_for_interview(
        self,
        project_id: str,
        interview_id: str,
    ) -> list[dict]:
        """Laedt alle Facts fuer ein Interview in einem Projekt.

        Args:
            project_id: UUID als String.
            interview_id: UUID als String.

        Returns:
            Liste von Fact-Dicts sortiert nach created_at.
        """
        async with self._session_factory() as session:
            result = await session.execute(
                text(
                    "SELECT id, project_id, interview_id, cluster_id, content, quote, confidence, created_at "
                    "FROM facts "
                    "WHERE project_id = :project_id AND interview_id = :interview_id "
                    "ORDER BY created_at ASC"
                ),
                {
                    "project_id": project_id,
                    "interview_id": interview_id,
                },
            )
            rows = result.mappings().all()
            return [dict(row) for row in rows]

    async def get_facts_for_project(
        self,
        project_id: str,
        cluster_id: str | None = None,
        unassigned_only: bool = False,
    ) -> list[dict]:
        """Laedt alle Facts fuer ein Projekt mit optionalem Filter.

        Args:
            project_id: UUID als String.
            cluster_id: Optional. Falls gesetzt, nur Facts dieses Clusters.
            unassigned_only: Falls True, nur Facts mit cluster_id=NULL.

        Returns:
            Liste von Fact-Dicts.
        """
        async with self._session_factory() as session:
            if cluster_id is not None:
                result = await session.execute(
                    text(
                        "SELECT id, project_id, interview_id, cluster_id, content, quote, confidence, created_at "
                        "FROM facts "
                        "WHERE project_id = :project_id AND cluster_id = :cluster_id "
                        "ORDER BY created_at ASC"
                    ),
                    {
                        "project_id": project_id,
                        "cluster_id": cluster_id,
                    },
                )
            elif unassigned_only:
                result = await session.execute(
                    text(
                        "SELECT id, project_id, interview_id, cluster_id, content, quote, confidence, created_at "
                        "FROM facts "
                        "WHERE project_id = :project_id AND cluster_id IS NULL "
                        "ORDER BY created_at ASC"
                    ),
                    {"project_id": project_id},
                )
            else:
                result = await session.execute(
                    text(
                        "SELECT id, project_id, interview_id, cluster_id, content, quote, confidence, created_at "
                        "FROM facts "
                        "WHERE project_id = :project_id "
                        "ORDER BY created_at ASC"
                    ),
                    {"project_id": project_id},
                )

            rows = result.mappings().all()
            return [dict(row) for row in rows]

    async def update_cluster_assignments(
        self,
        assignments: list[dict],
    ) -> None:
        """Aktualisiert cluster_id fuer eine Liste von Facts.

        Args:
            assignments: Liste von {fact_id: str, cluster_id: str | None}.
                         cluster_id=None -> unassigned.

        Verwendet einzelne UPDATE-Statements fuer Korrektheit.
        """
        if not assignments:
            return

        async with self._session_factory() as session:
            for assignment in assignments:
                fact_id = assignment.get("fact_id")
                cluster_id = assignment.get("cluster_id")

                if not fact_id:
                    continue

                await session.execute(
                    text(
                        "UPDATE facts "
                        "SET cluster_id = :cluster_id "
                        "WHERE id = :fact_id"
                    ),
                    {
                        "fact_id": str(fact_id),
                        "cluster_id": str(cluster_id) if cluster_id else None,
                    },
                )

            await session.commit()

        logger.info(f"Updated cluster assignments for {len(assignments)} facts")

    async def reset_cluster_assignments_for_project(
        self,
        project_id: str,
    ) -> None:
        """Setzt alle facts.cluster_id = NULL fuer ein Projekt (Full Re-Cluster).

        UPDATE facts SET cluster_id = NULL WHERE project_id = :project_id
        """
        async with self._session_factory() as session:
            result = await session.execute(
                text(
                    "UPDATE facts SET cluster_id = NULL WHERE project_id = :project_id"
                ),
                {"project_id": project_id},
            )
            await session.commit()
            updated_count = result.rowcount

        logger.info(f"Reset cluster assignments for {updated_count} facts in project {project_id}")

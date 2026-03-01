"""ClusterRepository -- CRUD fuer die clusters-Tabelle.

Folgt exakt dem Pattern von InterviewRepository:
Raw SQL + SQLAlchemy async + text()
"""
import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

logger = logging.getLogger(__name__)


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
        async with self._session_factory() as session:
            result = await session.execute(
                text(
                    "SELECT id, project_id, name, summary, fact_count, interview_count, "
                    "created_at, updated_at "
                    "FROM clusters "
                    "WHERE project_id = :project_id "
                    "ORDER BY fact_count DESC, created_at ASC"
                ),
                {"project_id": project_id},
            )
            rows = result.mappings().all()
            return [dict(row) for row in rows]

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
        if not clusters:
            return []

        results = []
        now = datetime.now(timezone.utc)

        async with self._session_factory() as session:
            for cluster in clusters:
                name = cluster.get("name", "")
                if not name:
                    continue

                cluster_id = str(uuid.uuid4())
                result = await session.execute(
                    text(
                        "INSERT INTO clusters "
                        "(id, project_id, name, summary, fact_count, interview_count, created_at, updated_at) "
                        "VALUES (:id, :project_id, :name, NULL, 0, 0, :created_at, :updated_at) "
                        "RETURNING id, project_id, name, summary, fact_count, interview_count, created_at, updated_at"
                    ),
                    {
                        "id": cluster_id,
                        "project_id": project_id,
                        "name": name[:200],
                        "created_at": now,
                        "updated_at": now,
                    },
                )
                row = result.mappings().first()
                if row:
                    row_dict = dict(row)
                    # Preserve fact_ids from input for mapping in service
                    if "fact_ids" in cluster:
                        row_dict["fact_ids"] = cluster["fact_ids"]
                    results.append(row_dict)

            await session.commit()

        logger.info(f"Created {len(results)} clusters for project {project_id}")
        return results

    async def update_summary(
        self,
        cluster_id: str,
        summary: str,
    ) -> dict:
        """Aktualisiert die Summary eines Clusters."""
        now = datetime.now(timezone.utc)
        async with self._session_factory() as session:
            result = await session.execute(
                text(
                    "UPDATE clusters "
                    "SET summary = :summary, updated_at = :updated_at "
                    "WHERE id = :cluster_id "
                    "RETURNING id, project_id, name, summary, fact_count, interview_count, created_at, updated_at"
                ),
                {
                    "cluster_id": cluster_id,
                    "summary": summary,
                    "updated_at": now,
                },
            )
            await session.commit()
            row = result.mappings().first()
            return dict(row) if row else {}

    async def update_counts(
        self,
        cluster_id: str,
        fact_count: int,
        interview_count: int,
    ) -> None:
        """Aktualisiert denormalisierte Zaehler."""
        now = datetime.now(timezone.utc)
        async with self._session_factory() as session:
            await session.execute(
                text(
                    "UPDATE clusters "
                    "SET fact_count = :fact_count, interview_count = :interview_count, "
                    "updated_at = :updated_at "
                    "WHERE id = :cluster_id"
                ),
                {
                    "cluster_id": cluster_id,
                    "fact_count": fact_count,
                    "interview_count": interview_count,
                    "updated_at": now,
                },
            )
            await session.commit()

    async def update_counts_from_db(self, project_id: str) -> None:
        """Berechnet und aktualisiert alle fact_count und interview_count fuer ein Projekt.

        Verwendet COUNT-Queries gegen facts-Tabelle.
        Wird nach jeder Persistierung aufgerufen.
        """
        now = datetime.now(timezone.utc)
        async with self._session_factory() as session:
            # Aktualisiere fact_count und interview_count fuer alle Cluster des Projekts
            await session.execute(
                text(
                    "UPDATE clusters c "
                    "SET "
                    "  fact_count = (SELECT COUNT(*) FROM facts f WHERE f.cluster_id = c.id), "
                    "  interview_count = (SELECT COUNT(DISTINCT f.interview_id) FROM facts f WHERE f.cluster_id = c.id), "
                    "  updated_at = :updated_at "
                    "WHERE c.project_id = :project_id"
                ),
                {
                    "project_id": project_id,
                    "updated_at": now,
                },
            )
            await session.commit()
        logger.debug(f"Updated counts for all clusters in project {project_id}")

    async def delete_all_for_project(
        self,
        project_id: str,
    ) -> None:
        """Loescht alle Cluster eines Projekts (fuer Full Re-Cluster).

        ON DELETE CASCADE loescht auch facts.cluster_id Referenzen (SET NULL).
        """
        async with self._session_factory() as session:
            result = await session.execute(
                text(
                    "DELETE FROM clusters WHERE project_id = :project_id"
                ),
                {"project_id": project_id},
            )
            await session.commit()
            deleted_count = result.rowcount
        logger.info(f"Deleted {deleted_count} clusters for project {project_id}")

    async def get_by_id(
        self,
        cluster_id: str,
        project_id: str,
    ) -> dict | None:
        """Laedt einen Cluster per ID (mit Projekt-Pruefung fuer Security)."""
        async with self._session_factory() as session:
            result = await session.execute(
                text(
                    "SELECT id, project_id, name, summary, fact_count, interview_count, "
                    "created_at, updated_at "
                    "FROM clusters "
                    "WHERE id = :cluster_id AND project_id = :project_id"
                ),
                {
                    "cluster_id": cluster_id,
                    "project_id": project_id,
                },
            )
            row = result.mappings().first()
            return dict(row) if row else None

    async def update_name(
        self,
        project_id: str,
        cluster_id: str,
        name: str,
    ) -> dict | None:
        """Benennt einen Cluster um.

        Returns:
            Aktualisiertes Cluster-Dict oder None wenn nicht gefunden.
        """
        now = datetime.now(timezone.utc)
        async with self._session_factory() as session:
            result = await session.execute(
                text(
                    "UPDATE clusters "
                    "SET name = :name, updated_at = :updated_at "
                    "WHERE id = :cluster_id AND project_id = :project_id "
                    "RETURNING id, project_id, name, summary, fact_count, interview_count, created_at, updated_at"
                ),
                {
                    "cluster_id": cluster_id,
                    "project_id": project_id,
                    "name": name[:200],
                    "updated_at": now,
                },
            )
            await session.commit()
            row = result.mappings().first()
            return dict(row) if row else None

    async def delete(
        self,
        project_id: str,
        cluster_id: str,
    ) -> None:
        """Loescht einen einzelnen Cluster (für Merge/Split).

        ON DELETE SET NULL setzt facts.cluster_id = NULL fuer verwaiste Facts.
        """
        async with self._session_factory() as session:
            await session.execute(
                text(
                    "DELETE FROM clusters WHERE id = :cluster_id AND project_id = :project_id"
                ),
                {
                    "cluster_id": cluster_id,
                    "project_id": project_id,
                },
            )
            await session.commit()
        logger.info(f"Deleted cluster {cluster_id} in project {project_id}")

    async def create(
        self,
        project_id: str,
        name: str,
    ) -> dict:
        """Legt einen neuen Cluster an und gibt ihn zurueck.

        Returns:
            Neuer Cluster als Dict (inkl. id).
        """
        now = datetime.now(timezone.utc)
        cluster_id = str(uuid.uuid4())
        async with self._session_factory() as session:
            result = await session.execute(
                text(
                    "INSERT INTO clusters "
                    "(id, project_id, name, summary, fact_count, interview_count, created_at, updated_at) "
                    "VALUES (:id, :project_id, :name, NULL, 0, 0, :created_at, :updated_at) "
                    "RETURNING id, project_id, name, summary, fact_count, interview_count, created_at, updated_at"
                ),
                {
                    "id": cluster_id,
                    "project_id": project_id,
                    "name": name[:200],
                    "created_at": now,
                    "updated_at": now,
                },
            )
            await session.commit()
            row = result.mappings().first()
            return dict(row) if row else {"id": cluster_id, "name": name, "project_id": project_id}

    async def recalculate_counts(
        self,
        project_id: str,
        cluster_id: str,
    ) -> dict:
        """Berechnet fact_count und interview_count eines Clusters neu via DB-Query.

        Returns:
            Aktualisiertes Cluster-Dict.
        """
        now = datetime.now(timezone.utc)
        async with self._session_factory() as session:
            result = await session.execute(
                text(
                    "UPDATE clusters c "
                    "SET "
                    "  fact_count = (SELECT COUNT(*) FROM facts f WHERE f.cluster_id = c.id), "
                    "  interview_count = (SELECT COUNT(DISTINCT f.interview_id) FROM facts f WHERE f.cluster_id = c.id), "
                    "  updated_at = :updated_at "
                    "WHERE c.id = :cluster_id AND c.project_id = :project_id "
                    "RETURNING id, project_id, name, summary, fact_count, interview_count, created_at, updated_at"
                ),
                {
                    "cluster_id": cluster_id,
                    "project_id": project_id,
                    "updated_at": now,
                },
            )
            await session.commit()
            row = result.mappings().first()
            return dict(row) if row else {}

    async def get_detail(
        self,
        cluster_id: str,
        project_id: str,
    ) -> dict | None:
        """Laedt Cluster-Detail mit Facts und Quotes.

        Returns:
            Dict mit Cluster-Feldern + facts (list) + quotes (list).
            None wenn Cluster nicht gefunden oder nicht zu diesem Projekt gehoert.
        """
        async with self._session_factory() as session:
            # 1. Cluster laden (mit Projekt-Pruefung fuer Security)
            cluster_result = await session.execute(
                text(
                    "SELECT id, project_id, name, summary, fact_count, interview_count, "
                    "created_at, updated_at "
                    "FROM clusters "
                    "WHERE id = :cluster_id AND project_id = :project_id"
                ),
                {
                    "cluster_id": cluster_id,
                    "project_id": project_id,
                },
            )
            cluster_row = cluster_result.mappings().first()
            if cluster_row is None:
                return None

            cluster = dict(cluster_row)

            # 2. Facts laden (sortiert nach created_at ASC)
            facts_result = await session.execute(
                text(
                    "SELECT f.id, f.content, f.quote, f.confidence, "
                    "f.interview_id, f.cluster_id, "
                    "m.created_at AS interview_date "
                    "FROM facts f "
                    "LEFT JOIN mvp_interviews m ON m.session_id = f.interview_id "
                    "WHERE f.cluster_id = :cluster_id AND f.project_id = :project_id "
                    "ORDER BY f.created_at ASC"
                ),
                {
                    "cluster_id": cluster_id,
                    "project_id": project_id,
                },
            )
            facts_rows = facts_result.mappings().all()
            cluster["facts"] = [dict(row) for row in facts_rows]

            # 3. Quotes laden (Facts mit quote != null, mit ROW_NUMBER fuer interview_number)
            quotes_result = await session.execute(
                text(
                    "SELECT f.id AS fact_id, f.quote AS content, f.interview_id, "
                    "ROW_NUMBER() OVER (ORDER BY pi.assigned_at) AS interview_number "
                    "FROM facts f "
                    "LEFT JOIN project_interviews pi "
                    "  ON pi.interview_id = f.interview_id AND pi.project_id = :project_id "
                    "WHERE f.cluster_id = :cluster_id AND f.quote IS NOT NULL "
                    "ORDER BY pi.assigned_at ASC"
                ),
                {
                    "cluster_id": cluster_id,
                    "project_id": project_id,
                },
            )
            quotes_rows = quotes_result.mappings().all()
            cluster["quotes"] = [dict(row) for row in quotes_rows]

        return cluster

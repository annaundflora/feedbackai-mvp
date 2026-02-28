"""ProjectRepository -- CRUD fuer projects-Tabelle.

Folgt dem Pattern aus InterviewRepository (Raw SQL + SQLAlchemy async).
"""
from datetime import datetime, timezone

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


class ProjectRepository:
    """Repository fuer die projects-Tabelle.

    Kapselt alle DB-Operationen via SQLAlchemy async mit Raw SQL.
    """

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def create(self, data: dict) -> dict:
        """INSERT INTO projects ... RETURNING *

        Args:
            data: dict mit user_id, name, research_goal, prompt_context,
                  extraction_source, model_* Feldern

        Returns:
            dict mit allen Spalten des angelegten Projekts
        """
        async with self._session_factory() as session:
            result = await session.execute(
                text(
                    "INSERT INTO projects "
                    "(user_id, name, research_goal, prompt_context, extraction_source, "
                    " model_interviewer, model_extraction, model_clustering, model_summary) "
                    "VALUES "
                    "(:user_id, :name, :research_goal, :prompt_context, :extraction_source, "
                    " :model_interviewer, :model_extraction, :model_clustering, :model_summary) "
                    "RETURNING *"
                ),
                data,
            )
            await session.commit()
            row = result.mappings().first()
            return dict(row) if row else {}

    async def get_by_id(self, project_id: str, user_id: str) -> dict | None:
        """SELECT * FROM projects WHERE id = :id AND user_id = :user_id

        Filtert immer auf user_id (kein Cross-User-Access).

        Args:
            project_id: UUID des Projekts
            user_id: UUID des anfragenden Users

        Returns:
            dict mit Projektdaten oder None wenn nicht gefunden
        """
        async with self._session_factory() as session:
            result = await session.execute(
                text(
                    "SELECT * FROM projects "
                    "WHERE id = :project_id AND user_id = :user_id"
                ),
                {"project_id": project_id, "user_id": user_id},
            )
            row = result.mappings().first()
            return dict(row) if row else None

    async def list_by_user(self, user_id: str) -> list[dict]:
        """SELECT mit aggregierten Zaehlern sortiert nach updated_at desc.

        Args:
            user_id: UUID des Users

        Returns:
            list[dict] mit Projektdaten inkl. interview_count, cluster_count
        """
        async with self._session_factory() as session:
            result = await session.execute(
                text(
                    "SELECT "
                    "  p.id, p.name, p.updated_at, "
                    "  (SELECT COUNT(*) FROM project_interviews pi WHERE pi.project_id = p.id) AS interview_count, "
                    "  (SELECT COUNT(*) FROM clusters c WHERE c.project_id = p.id) AS cluster_count "
                    "FROM projects p "
                    "WHERE p.user_id = :user_id "
                    "ORDER BY p.updated_at DESC"
                ),
                {"user_id": user_id},
            )
            rows = result.mappings().all()
            return [dict(row) for row in rows]

    async def update(self, project_id: str, user_id: str, data: dict) -> dict | None:
        """UPDATE projects SET ... WHERE id = :id AND user_id = :user_id RETURNING *

        Aktualisiert nur die in data enthaltenen Felder.
        Setzt updated_at automatisch.

        Args:
            project_id: UUID des Projekts
            user_id: UUID des Users (fuer Zugriffsschutz)
            data: dict mit zu aenderenden Feldern

        Returns:
            dict mit aktualisierten Projektdaten oder None wenn nicht gefunden
        """
        if not data:
            return await self.get_by_id(project_id, user_id)

        now = datetime.now(timezone.utc)
        data["updated_at"] = now
        data["project_id"] = project_id
        data["user_id"] = user_id

        set_clauses = ", ".join(
            f"{key} = :{key}" for key in data if key not in ("project_id", "user_id")
        )

        async with self._session_factory() as session:
            result = await session.execute(
                text(
                    f"UPDATE projects SET {set_clauses} "
                    "WHERE id = :project_id AND user_id = :user_id "
                    "RETURNING *"
                ),
                data,
            )
            await session.commit()
            row = result.mappings().first()
            return dict(row) if row else None

    async def delete(self, project_id: str, user_id: str) -> bool:
        """DELETE FROM projects WHERE id = :id AND user_id = :user_id

        CASCADE loescht alle abhaengigen Daten (project_interviews, clusters, facts,
        cluster_suggestions).

        Args:
            project_id: UUID des Projekts
            user_id: UUID des Users (fuer Zugriffsschutz)

        Returns:
            True wenn geloescht, False wenn nicht gefunden
        """
        async with self._session_factory() as session:
            result = await session.execute(
                text(
                    "DELETE FROM projects "
                    "WHERE id = :project_id AND user_id = :user_id "
                    "RETURNING id"
                ),
                {"project_id": project_id, "user_id": user_id},
            )
            await session.commit()
            row = result.mappings().first()
            return row is not None

    async def get_fact_count(self, project_id: str) -> int:
        """SELECT COUNT(*) FROM facts WHERE project_id = :project_id

        Args:
            project_id: UUID des Projekts

        Returns:
            Anzahl Facts fuer dieses Projekt
        """
        async with self._session_factory() as session:
            result = await session.execute(
                text("SELECT COUNT(*) AS cnt FROM facts WHERE project_id = :project_id"),
                {"project_id": project_id},
            )
            row = result.mappings().first()
            return int(row["cnt"]) if row else 0

    async def get_interview_count(self, project_id: str) -> int:
        """SELECT COUNT(*) FROM project_interviews WHERE project_id = :project_id

        Args:
            project_id: UUID des Projekts

        Returns:
            Anzahl zugeordneter Interviews
        """
        async with self._session_factory() as session:
            result = await session.execute(
                text(
                    "SELECT COUNT(*) AS cnt FROM project_interviews "
                    "WHERE project_id = :project_id"
                ),
                {"project_id": project_id},
            )
            row = result.mappings().first()
            return int(row["cnt"]) if row else 0

    async def get_cluster_count(self, project_id: str) -> int:
        """SELECT COUNT(*) FROM clusters WHERE project_id = :project_id

        Args:
            project_id: UUID des Projekts

        Returns:
            Anzahl Cluster fuer dieses Projekt
        """
        async with self._session_factory() as session:
            result = await session.execute(
                text(
                    "SELECT COUNT(*) AS cnt FROM clusters "
                    "WHERE project_id = :project_id"
                ),
                {"project_id": project_id},
            )
            row = result.mappings().first()
            return int(row["cnt"]) if row else 0

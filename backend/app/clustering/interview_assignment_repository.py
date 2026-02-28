"""InterviewAssignmentRepository -- CRUD fuer project_interviews-Tabelle.

Folgt dem Pattern aus InterviewRepository (Raw SQL + SQLAlchemy async).
"""
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from fastapi import HTTPException


class InterviewAssignmentRepository:
    """Repository fuer die project_interviews-Tabelle.

    Kapselt alle DB-Operationen via SQLAlchemy async mit Raw SQL.
    Joined auf mvp_interviews fuer date + summary_preview.
    """

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def assign_interviews(
        self, project_id: str, interview_ids: list[str]
    ) -> list[dict]:
        """INSERT INTO project_interviews ... RETURNING * (mit JOIN auf mvp_interviews).

        Bei UNIQUE-Konflikt auf interview_id: HTTP 409 Conflict.

        Args:
            project_id: UUID des Projekts
            interview_ids: Liste von Interview-UUIDs die zugeordnet werden sollen

        Returns:
            list[dict] mit den neu angelegten Zuordnungen inkl. interview-Details

        Raises:
            HTTPException 409: Wenn ein Interview bereits einem anderen Projekt zugeordnet ist
        """
        results = []
        async with self._session_factory() as session:
            for interview_id in interview_ids:
                # Pruefe ob bereits zugeordnet
                check_result = await session.execute(
                    text(
                        "SELECT project_id FROM project_interviews "
                        "WHERE interview_id = :interview_id"
                    ),
                    {"interview_id": str(interview_id)},
                )
                existing = check_result.mappings().first()
                if existing:
                    raise HTTPException(
                        status_code=409,
                        detail=f"Interview {interview_id} already assigned to another project",
                    )

                # Einfuegen
                await session.execute(
                    text(
                        "INSERT INTO project_interviews "
                        "(project_id, interview_id, extraction_status, clustering_status) "
                        "VALUES (:project_id, :interview_id, 'pending', 'pending')"
                    ),
                    {
                        "project_id": str(project_id),
                        "interview_id": str(interview_id),
                    },
                )

            await session.commit()

            # Lade die zugeordneten Interviews mit Details aus mvp_interviews
            for interview_id in interview_ids:
                detail_result = await session.execute(
                    text(
                        "SELECT "
                        "  pi.interview_id, "
                        "  COALESCE(mi.created_at, pi.assigned_at) AS date, "
                        "  LEFT(mi.summary, 200) AS summary_preview, "
                        "  (SELECT COUNT(*) FROM facts f WHERE f.interview_id = pi.interview_id) AS fact_count, "
                        "  pi.extraction_status, "
                        "  pi.clustering_status "
                        "FROM project_interviews pi "
                        "LEFT JOIN mvp_interviews mi ON mi.session_id = pi.interview_id "
                        "WHERE pi.project_id = :project_id AND pi.interview_id = :interview_id"
                    ),
                    {
                        "project_id": str(project_id),
                        "interview_id": str(interview_id),
                    },
                )
                row = detail_result.mappings().first()
                if row:
                    results.append(dict(row))

        return results

    async def list_assigned(self, project_id: str) -> list[dict]:
        """SELECT mit JOIN auf mvp_interviews fuer date + summary_preview.

        Args:
            project_id: UUID des Projekts

        Returns:
            list[dict] mit zugeordneten Interviews inkl. Status und Vorschau
        """
        async with self._session_factory() as session:
            result = await session.execute(
                text(
                    "SELECT "
                    "  pi.interview_id, "
                    "  COALESCE(mi.created_at, pi.assigned_at) AS date, "
                    "  LEFT(mi.summary, 200) AS summary_preview, "
                    "  (SELECT COUNT(*) FROM facts f WHERE f.interview_id = pi.interview_id) AS fact_count, "
                    "  pi.extraction_status, "
                    "  pi.clustering_status "
                    "FROM project_interviews pi "
                    "LEFT JOIN mvp_interviews mi ON mi.session_id = pi.interview_id "
                    "WHERE pi.project_id = :project_id "
                    "ORDER BY pi.assigned_at DESC"
                ),
                {"project_id": project_id},
            )
            rows = result.mappings().all()
            return [dict(row) for row in rows]

    async def list_available(self, user_id: str) -> list[dict]:
        """SELECT aus mvp_interviews wo session_id NICHT in project_interviews.

        Gibt Interviews zurueck die noch keinem Projekt zugeordnet wurden.

        Args:
            user_id: UUID des Users (fuer zukuenftige Filterung)

        Returns:
            list[dict] mit verfuegbaren Interviews (session_id, created_at, summary_preview)
        """
        async with self._session_factory() as session:
            result = await session.execute(
                text(
                    "SELECT "
                    "  mi.session_id, "
                    "  mi.created_at, "
                    "  LEFT(mi.summary, 200) AS summary_preview "
                    "FROM mvp_interviews mi "
                    "WHERE mi.session_id NOT IN ("
                    "  SELECT pi.interview_id FROM project_interviews pi"
                    ") "
                    "AND mi.status IN ('completed', 'completed_timeout') "
                    "ORDER BY mi.created_at DESC"
                ),
                {},
            )
            rows = result.mappings().all()
            return [dict(row) for row in rows]

    async def find_by_interview_id(self, interview_id: str) -> dict | None:
        """SELECT * FROM project_interviews WHERE interview_id = :interview_id.

        Wird von InterviewService.end() aufgerufen um zu pruefen ob Interview
        einem Projekt zugeordnet ist.

        Args:
            interview_id: UUID des Interviews

        Returns:
            dict mit {project_id, interview_id, extraction_status, clustering_status}
            oder None wenn Interview keinem Projekt zugeordnet.
        """
        async with self._session_factory() as session:
            result = await session.execute(
                text(
                    "SELECT * FROM project_interviews "
                    "WHERE interview_id = :interview_id"
                ),
                {"interview_id": interview_id},
            )
            row = result.mappings().first()
            return dict(row) if row else None

    async def find_by_project_and_interview(
        self, project_id: str, interview_id: str
    ) -> dict | None:
        """SELECT * FROM project_interviews WHERE project_id = ... AND interview_id = ...

        Fuer Retry-Endpoint: Prueft ob Interview in spezifischem Projekt.

        Args:
            project_id: UUID des Projekts als String.
            interview_id: UUID des Interviews als String.

        Returns:
            dict mit Zuordnungsdaten oder None wenn nicht gefunden.
        """
        async with self._session_factory() as session:
            result = await session.execute(
                text(
                    "SELECT * FROM project_interviews "
                    "WHERE project_id = :project_id AND interview_id = :interview_id"
                ),
                {
                    "project_id": project_id,
                    "interview_id": interview_id,
                },
            )
            row = result.mappings().first()
            return dict(row) if row else None

    async def update_extraction_status(
        self,
        interview_id: str,
        extraction_status: str,
        clustering_status: str | None = None,
    ) -> dict:
        """Aktualisiert extraction_status (und optional clustering_status).

        Status-Uebergaenge: pending -> running -> completed | failed

        Args:
            interview_id: UUID als String.
            extraction_status: Neuer Status ('pending' | 'running' | 'completed' | 'failed').
            clustering_status: Falls nicht None, wird clustering_status ebenfalls gesetzt.

        Returns:
            Aktualisierter DB-Row als Dict.
        """
        async with self._session_factory() as session:
            if clustering_status is not None:
                result = await session.execute(
                    text(
                        "UPDATE project_interviews "
                        "SET extraction_status = :extraction_status, "
                        "    clustering_status = :clustering_status "
                        "WHERE interview_id = :interview_id "
                        "RETURNING *"
                    ),
                    {
                        "interview_id": interview_id,
                        "extraction_status": extraction_status,
                        "clustering_status": clustering_status,
                    },
                )
            else:
                result = await session.execute(
                    text(
                        "UPDATE project_interviews "
                        "SET extraction_status = :extraction_status "
                        "WHERE interview_id = :interview_id "
                        "RETURNING *"
                    ),
                    {
                        "interview_id": interview_id,
                        "extraction_status": extraction_status,
                    },
                )
            await session.commit()
            row = result.mappings().first()
            return dict(row) if row else {}

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
        async with self._session_factory() as session:
            result = await session.execute(
                text(
                    "UPDATE project_interviews "
                    "SET clustering_status = :clustering_status "
                    "WHERE interview_id = :interview_id "
                    "RETURNING *"
                ),
                {
                    "interview_id": interview_id,
                    "clustering_status": clustering_status,
                },
            )
            await session.commit()
            row = result.mappings().first()
            return dict(row) if row else {}

    async def get_all_for_project(
        self,
        project_id: str,
    ) -> list[dict]:
        """Laedt alle Zuordnungen eines Projekts (fuer Status-Aggregation)."""
        async with self._session_factory() as session:
            result = await session.execute(
                text(
                    "SELECT project_id, interview_id, extraction_status, clustering_status, assigned_at "
                    "FROM project_interviews "
                    "WHERE project_id = :project_id "
                    "ORDER BY assigned_at ASC"
                ),
                {"project_id": project_id},
            )
            rows = result.mappings().all()
            return [dict(row) for row in rows]

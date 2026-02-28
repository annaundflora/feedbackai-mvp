"""InterviewAssignmentService -- Geschaeftslogik fuer Interview-Zuordnung.

Kapselt die Interaktion zwischen Router und InterviewAssignmentRepository.
"""
from app.clustering.interview_assignment_repository import InterviewAssignmentRepository
from app.clustering.schemas import AssignRequest, AvailableInterview, InterviewAssignment


class InterviewAssignmentService:
    """Service fuer Interview-Zuordnung zu Projekten.

    Implementiert Geschaeftslogik fuer Interview-Assignment-Endpunkte.
    """

    def __init__(self, repo: InterviewAssignmentRepository) -> None:
        self._repo = repo

    async def assign(
        self, project_id: str, request: AssignRequest
    ) -> list[InterviewAssignment]:
        """Ordnet Interviews einem Projekt zu.

        Speichert Zuordnung in project_interviews Tabelle.
        Bei bereits zugeordneten Interviews: HTTP 409.

        Args:
            project_id: UUID des Projekts
            request: AssignRequest mit interview_ids Liste

        Returns:
            list[InterviewAssignment] der neu zugeordneten Interviews

        Raises:
            HTTPException 409: Wenn ein Interview bereits zugeordnet ist
        """
        interview_ids = [str(iid) for iid in request.interview_ids]
        rows = await self._repo.assign_interviews(
            project_id=project_id,
            interview_ids=interview_ids,
        )
        return [
            InterviewAssignment(
                interview_id=row["interview_id"],
                date=row["date"],
                summary_preview=row.get("summary_preview"),
                fact_count=int(row.get("fact_count", 0)),
                extraction_status=row["extraction_status"],
                clustering_status=row["clustering_status"],
            )
            for row in rows
        ]

    async def list_assigned(self, project_id: str) -> list[InterviewAssignment]:
        """Listet alle einem Projekt zugeordneten Interviews.

        Args:
            project_id: UUID des Projekts

        Returns:
            list[InterviewAssignment] sortiert nach assigned_at desc
        """
        rows = await self._repo.list_assigned(project_id=project_id)
        return [
            InterviewAssignment(
                interview_id=row["interview_id"],
                date=row["date"],
                summary_preview=row.get("summary_preview"),
                fact_count=int(row.get("fact_count", 0)),
                extraction_status=row["extraction_status"],
                clustering_status=row["clustering_status"],
            )
            for row in rows
        ]

    async def list_available(self, user_id: str) -> list[AvailableInterview]:
        """Listet alle verfuegbaren (noch nicht zugeordneten) Interviews.

        Args:
            user_id: UUID des Users (fuer zukuenftige Filterung)

        Returns:
            list[AvailableInterview] sortiert nach created_at desc
        """
        rows = await self._repo.list_available(user_id=user_id)
        return [
            AvailableInterview(
                session_id=row["session_id"],
                created_at=row["created_at"],
                summary_preview=row.get("summary_preview"),
            )
            for row in rows
        ]

"""InterviewAssignmentService -- Geschaeftslogik fuer Interview-Zuordnung.

Kapselt die Interaktion zwischen Router und InterviewAssignmentRepository.
"""
import asyncio
import logging
from typing import Any

from fastapi import HTTPException

from app.clustering.interview_assignment_repository import InterviewAssignmentRepository
from app.clustering.schemas import AssignRequest, AvailableInterview, InterviewAssignment

logger = logging.getLogger(__name__)


class InterviewAssignmentService:
    """Service fuer Interview-Zuordnung zu Projekten.

    Implementiert Geschaeftslogik fuer Interview-Assignment-Endpunkte.
    """

    def __init__(
        self,
        repo: InterviewAssignmentRepository | None = None,
        repository: InterviewAssignmentRepository | None = None,
        interview_repository: Any = None,
        fact_extraction_service: Any = None,
    ) -> None:
        # Backward-compatible: akzeptiert 'repo' (bisherige Nutzung) oder 'repository' (neue Tests)
        self._repo = repo if repo is not None else repository
        self._interview_repository = interview_repository
        self._fact_extraction_service = fact_extraction_service

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
        if self._fact_extraction_service is not None:
            for interview_id in interview_ids:
                asyncio.create_task(
                    self._fact_extraction_service.process_interview(
                        project_id=project_id,
                        interview_id=interview_id,
                    )
                )
                logger.info(f"Assign: Fact extraction task started for interview {interview_id} in project {project_id}")
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

    async def retry(
        self,
        project_id: str,
        interview_id: str,
    ) -> InterviewAssignment:
        """Startet Fact Extraction fuer ein fehlgeschlagenes Interview neu.

        Business Rules:
        - extraction_status muss 'failed' sein (sonst: 409 Conflict)
        - Setzt extraction_status + clustering_status auf 'pending'
        - Startet asyncio.create_task(fact_extraction_service.process_interview(...))
        - Gibt aktualisierte InterviewAssignment zurueck

        Args:
            project_id: UUID des Projekts als String.
            interview_id: UUID des Interviews als String.

        Returns:
            InterviewAssignment mit extraction_status="pending".

        Raises:
            HTTPException(404): Wenn Interview nicht in Projekt gefunden.
            HTTPException(409): Wenn Status nicht 'failed'.
        """
        # Zuordnung laden
        assignment = await self._repo.find_by_project_and_interview(
            project_id=project_id,
            interview_id=interview_id,
        )

        if assignment is None:
            raise HTTPException(
                status_code=404,
                detail="Interview not found in project",
            )

        current_status = str(assignment.get("extraction_status", ""))
        if current_status != "failed":
            raise HTTPException(
                status_code=409,
                detail=f"Interview is not in failed state, current status: {current_status}",
            )

        # Status zuruecksetzen auf 'pending'
        updated = await self._repo.update_extraction_status(
            interview_id=interview_id,
            extraction_status="pending",
            clustering_status="pending",
        )

        # Background-Task starten
        if self._fact_extraction_service is not None:
            asyncio.create_task(
                self._fact_extraction_service.process_interview(
                    project_id=project_id,
                    interview_id=interview_id,
                )
            )
            logger.info(f"Retry: Fact extraction task restarted for interview {interview_id} in project {project_id}")

        # Interview-Details fuer Response laden (date, summary_preview, fact_count)
        interview_data = None
        if self._interview_repository is not None:
            try:
                interview_data = await self._interview_repository.get_session(interview_id)
            except Exception as e:
                logger.warning(f"Could not load interview details for retry response: {e}")

        import datetime as dt
        date = dt.datetime.now(dt.timezone.utc)
        summary_preview = None
        if interview_data:
            date = interview_data.get("created_at", date)
            summary = interview_data.get("summary", "")
            if summary:
                summary_preview = summary[:200]

        return InterviewAssignment(
            interview_id=str(updated.get("interview_id", interview_id)),
            date=date,
            summary_preview=summary_preview,
            fact_count=0,
            extraction_status=str(updated.get("extraction_status", "pending")),
            clustering_status=str(updated.get("clustering_status", "pending")),
        )

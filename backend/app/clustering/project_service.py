"""ProjectService -- Geschaeftslogik fuer Projekt-CRUD.

Kapselt die Interaktion zwischen Router und ProjectRepository.
"""
from fastapi import HTTPException

from app.clustering.project_repository import ProjectRepository
from app.clustering.schemas import (
    ChangeSourceRequest,
    CreateProjectRequest,
    ProjectListItem,
    ProjectResponse,
    UpdateModelsRequest,
    UpdateProjectRequest,
)


class ProjectService:
    """Service fuer Projekt-Verwaltung.

    Implementiert Geschaeftslogik fuer alle Projekt-Endpunkte.
    """

    def __init__(self, repo: ProjectRepository) -> None:
        self._repo = repo

    async def create(
        self, request: CreateProjectRequest, user_id: str
    ) -> ProjectResponse:
        """Erstellt neues Projekt und gibt ProjectResponse zurueck.

        Args:
            request: CreateProjectRequest mit Projektdaten
            user_id: UUID des Users der das Projekt anlegt

        Returns:
            ProjectResponse mit allen Feldern und Zaehlern (alle 0 bei Neuanlage)
        """
        data = {
            "user_id": user_id,
            "name": request.name,
            "research_goal": request.research_goal,
            "prompt_context": request.prompt_context,
            "extraction_source": request.extraction_source,
            "model_interviewer": "anthropic/claude-sonnet-4",
            "model_extraction": "anthropic/claude-haiku-4",
            "model_clustering": "anthropic/claude-sonnet-4",
            "model_summary": "anthropic/claude-haiku-4",
        }
        row = await self._repo.create(data)
        project_id = str(row["id"])

        return ProjectResponse(
            id=row["id"],
            name=row["name"],
            research_goal=row["research_goal"],
            prompt_context=row.get("prompt_context"),
            extraction_source=row["extraction_source"],
            extraction_source_locked=False,  # Neu: keine Facts vorhanden
            model_interviewer=row["model_interviewer"],
            model_extraction=row["model_extraction"],
            model_clustering=row["model_clustering"],
            model_summary=row["model_summary"],
            interview_count=0,
            cluster_count=0,
            fact_count=0,
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    async def list(self, user_id: str) -> list[ProjectListItem]:
        """Listet Projekte des Users, sortiert nach updated_at desc.

        Args:
            user_id: UUID des Users

        Returns:
            list[ProjectListItem] sortiert nach updated_at absteigend
        """
        rows = await self._repo.list_by_user(user_id)
        return [
            ProjectListItem(
                id=row["id"],
                name=row["name"],
                interview_count=int(row.get("interview_count", 0)),
                cluster_count=int(row.get("cluster_count", 0)),
                updated_at=row["updated_at"],
            )
            for row in rows
        ]

    async def get(self, project_id: str, user_id: str) -> ProjectResponse:
        """Laedt Projekt mit aggregierten Zaehlern.

        extraction_source_locked = fact_count > 0

        Args:
            project_id: UUID des Projekts
            user_id: UUID des Users

        Returns:
            ProjectResponse mit aktuellen Zaehlern

        Raises:
            HTTPException 404: Wenn Projekt nicht gefunden oder nicht diesem User gehoert
        """
        row = await self._repo.get_by_id(project_id, user_id)
        if row is None:
            raise HTTPException(status_code=404, detail="Project not found")

        interview_count = await self._repo.get_interview_count(project_id)
        cluster_count = await self._repo.get_cluster_count(project_id)
        fact_count = await self._repo.get_fact_count(project_id)

        return ProjectResponse(
            id=row["id"],
            name=row["name"],
            research_goal=row["research_goal"],
            prompt_context=row.get("prompt_context"),
            extraction_source=row["extraction_source"],
            extraction_source_locked=fact_count > 0,
            model_interviewer=row["model_interviewer"],
            model_extraction=row["model_extraction"],
            model_clustering=row["model_clustering"],
            model_summary=row["model_summary"],
            interview_count=interview_count,
            cluster_count=cluster_count,
            fact_count=fact_count,
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    async def update(
        self,
        project_id: str,
        user_id: str,
        request: UpdateProjectRequest,
    ) -> ProjectResponse:
        """Aktualisiert name/research_goal/prompt_context, setzt updated_at.

        Nur gesendete (nicht-None) Felder werden aktualisiert (PATCH-Semantik via PUT).

        Args:
            project_id: UUID des Projekts
            user_id: UUID des Users
            request: UpdateProjectRequest mit zu aendernden Feldern

        Returns:
            ProjectResponse mit aktualisierten Daten

        Raises:
            HTTPException 404: Wenn Projekt nicht gefunden
        """
        data = {}
        if request.name is not None:
            data["name"] = request.name
        if request.research_goal is not None:
            data["research_goal"] = request.research_goal
        if request.prompt_context is not None:
            data["prompt_context"] = request.prompt_context

        row = await self._repo.update(project_id, user_id, data)
        if row is None:
            raise HTTPException(status_code=404, detail="Project not found")

        interview_count = await self._repo.get_interview_count(project_id)
        cluster_count = await self._repo.get_cluster_count(project_id)
        fact_count = await self._repo.get_fact_count(project_id)

        return ProjectResponse(
            id=row["id"],
            name=row["name"],
            research_goal=row["research_goal"],
            prompt_context=row.get("prompt_context"),
            extraction_source=row["extraction_source"],
            extraction_source_locked=fact_count > 0,
            model_interviewer=row["model_interviewer"],
            model_extraction=row["model_extraction"],
            model_clustering=row["model_clustering"],
            model_summary=row["model_summary"],
            interview_count=interview_count,
            cluster_count=cluster_count,
            fact_count=fact_count,
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    async def update_models(
        self,
        project_id: str,
        user_id: str,
        request: UpdateModelsRequest,
    ) -> ProjectResponse:
        """Aktualisiert model_* Felder.

        Args:
            project_id: UUID des Projekts
            user_id: UUID des Users
            request: UpdateModelsRequest mit zu aendernden Model-Slugs

        Returns:
            ProjectResponse mit aktualisierten Model-Daten

        Raises:
            HTTPException 404: Wenn Projekt nicht gefunden
        """
        data = {}
        if request.model_interviewer is not None:
            data["model_interviewer"] = request.model_interviewer
        if request.model_extraction is not None:
            data["model_extraction"] = request.model_extraction
        if request.model_clustering is not None:
            data["model_clustering"] = request.model_clustering
        if request.model_summary is not None:
            data["model_summary"] = request.model_summary

        row = await self._repo.update(project_id, user_id, data)
        if row is None:
            raise HTTPException(status_code=404, detail="Project not found")

        interview_count = await self._repo.get_interview_count(project_id)
        cluster_count = await self._repo.get_cluster_count(project_id)
        fact_count = await self._repo.get_fact_count(project_id)

        return ProjectResponse(
            id=row["id"],
            name=row["name"],
            research_goal=row["research_goal"],
            prompt_context=row.get("prompt_context"),
            extraction_source=row["extraction_source"],
            extraction_source_locked=fact_count > 0,
            model_interviewer=row["model_interviewer"],
            model_extraction=row["model_extraction"],
            model_clustering=row["model_clustering"],
            model_summary=row["model_summary"],
            interview_count=interview_count,
            cluster_count=cluster_count,
            fact_count=fact_count,
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    async def change_extraction_source(
        self,
        project_id: str,
        user_id: str,
        request: ChangeSourceRequest,
    ) -> ProjectResponse:
        """Aendert extraction_source.

        re_extract wird in Slice 2 verarbeitet (hier: gespeichert, kein Trigger).

        Args:
            project_id: UUID des Projekts
            user_id: UUID des Users
            request: ChangeSourceRequest mit neuer extraction_source

        Returns:
            ProjectResponse mit aktualisierter extraction_source

        Raises:
            HTTPException 404: Wenn Projekt nicht gefunden
        """
        data = {"extraction_source": request.extraction_source}
        row = await self._repo.update(project_id, user_id, data)
        if row is None:
            raise HTTPException(status_code=404, detail="Project not found")

        interview_count = await self._repo.get_interview_count(project_id)
        cluster_count = await self._repo.get_cluster_count(project_id)
        fact_count = await self._repo.get_fact_count(project_id)

        return ProjectResponse(
            id=row["id"],
            name=row["name"],
            research_goal=row["research_goal"],
            prompt_context=row.get("prompt_context"),
            extraction_source=row["extraction_source"],
            extraction_source_locked=fact_count > 0,
            model_interviewer=row["model_interviewer"],
            model_extraction=row["model_extraction"],
            model_clustering=row["model_clustering"],
            model_summary=row["model_summary"],
            interview_count=interview_count,
            cluster_count=cluster_count,
            fact_count=fact_count,
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    async def delete(self, project_id: str, user_id: str) -> None:
        """Loescht Projekt (CASCADE: alle project_interviews, clusters, facts).

        Args:
            project_id: UUID des Projekts
            user_id: UUID des Users

        Raises:
            HTTPException 404: Wenn Projekt nicht gefunden oder nicht diesem User gehoert
        """
        deleted = await self._repo.delete(project_id=project_id, user_id=user_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Project not found")

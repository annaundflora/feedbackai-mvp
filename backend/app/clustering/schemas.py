"""Pydantic DTOs fuer das Clustering-Modul.

Alle Request- und Response-Schemas fuer Projekt-CRUD
und Interview-Zuordnung.
"""
import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


# --- Request DTOs ---


class CreateProjectRequest(BaseModel):
    """Request-DTO fuer POST /api/projects."""

    name: str = Field(..., min_length=1, max_length=200)
    research_goal: str = Field(..., min_length=1, max_length=2000)
    prompt_context: str | None = Field(None, max_length=5000)
    extraction_source: Literal["summary", "transcript"] = "summary"


class UpdateProjectRequest(BaseModel):
    """Request-DTO fuer PUT /api/projects/{id}.

    Alle Felder optional (PATCH-Semantik via PUT).
    """

    name: str | None = Field(None, min_length=1, max_length=200)
    research_goal: str | None = Field(None, min_length=1, max_length=2000)
    prompt_context: str | None = Field(None, max_length=5000)


class UpdateModelsRequest(BaseModel):
    """Request-DTO fuer PUT /api/projects/{id}/models."""

    model_interviewer: str | None = None
    model_extraction: str | None = None
    model_clustering: str | None = None
    model_summary: str | None = None


class ChangeSourceRequest(BaseModel):
    """Request-DTO fuer PUT /api/projects/{id}/extraction-source."""

    extraction_source: Literal["summary", "transcript"]
    re_extract: bool = False


class AssignRequest(BaseModel):
    """Request-DTO fuer POST /api/projects/{id}/interviews."""

    interview_ids: list[uuid.UUID] = Field(..., min_length=1)


# --- Response DTOs ---


class ProjectResponse(BaseModel):
    """Response-DTO fuer einzelnes Projekt mit allen Details."""

    id: uuid.UUID
    name: str
    research_goal: str
    prompt_context: str | None
    extraction_source: str
    extraction_source_locked: bool  # True wenn facts bereits existieren
    model_interviewer: str
    model_extraction: str
    model_clustering: str
    model_summary: str
    interview_count: int
    cluster_count: int
    fact_count: int
    created_at: datetime
    updated_at: datetime


class ProjectListItem(BaseModel):
    """Response-DTO fuer Projekt in der Projektliste."""

    id: uuid.UUID
    name: str
    interview_count: int
    cluster_count: int
    updated_at: datetime


class InterviewAssignment(BaseModel):
    """Response-DTO fuer zugeordnetes Interview."""

    interview_id: uuid.UUID
    date: datetime
    summary_preview: str | None
    fact_count: int
    extraction_status: str
    clustering_status: str


class AvailableInterview(BaseModel):
    """Response-DTO fuer verfuegbare (noch nicht zugeordnete) Interviews."""

    session_id: uuid.UUID
    created_at: datetime
    summary_preview: str | None


# --- Clustering Pipeline DTOs (Slice 3) ---


class ReclusterStarted(BaseModel):
    """Response fuer POST /recluster."""

    status: str = "started"
    message: str  # "Full re-cluster started for project {id}"
    project_id: str


class PipelineStatus(BaseModel):
    """Response fuer GET /clustering/status."""

    status: str              # "idle" | "running"
    mode: str | None         # "incremental" | "full" | None
    progress: dict | None    # {"total": int, "completed": int} | None
    current_step: str | None  # z.B. "assign_facts" | "generate_summaries" | None


class ClusterResponse(BaseModel):
    """Response-DTO fuer einen Cluster."""

    id: uuid.UUID
    project_id: uuid.UUID
    name: str
    summary: str | None
    fact_count: int
    interview_count: int
    created_at: datetime
    updated_at: datetime

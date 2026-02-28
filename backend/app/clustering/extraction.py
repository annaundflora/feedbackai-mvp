"""FactExtractionService -- LLM-basierte Extraktion atomarer Facts via OpenRouter.

Folgt Clio-Pattern (Facet Extraction): Strukturierte JSON-Ausgabe,
ein Fact = eine atomare Aussage des Interviewten.

Retry-Strategie: max_retries=3, exponential backoff (1s, 2s, 4s).
"""
import asyncio
import json
import logging
from dataclasses import dataclass
from typing import Any

from langchain_openai import ChatOpenAI

from app.clustering.events import SseEventBus
from app.clustering.fact_repository import FactRepository
from app.clustering.interview_assignment_repository import InterviewAssignmentRepository
from app.clustering.prompts import FACT_EXTRACTION_PROMPT

logger = logging.getLogger(__name__)


class FactExtractionError(Exception):
    """Wird geworfen nach max_retries fehlgeschlagenen LLM-Versuchen."""

    pass


@dataclass
class ExtractedFact:
    """Rohdaten eines vom LLM extrahierten Facts."""

    content: str             # Atomare Aussage, 1-1000 Zeichen
    quote: str | None        # Relevantes Originalzitat aus Transcript
    confidence: float | None  # LLM-Confidence 0.0-1.0


class FactExtractionService:
    """Extrahiert atomare Facts aus Interview-Text via LLM (OpenRouter).

    Folgt Clio-Pattern (Facet Extraction): Strukturierte JSON-Ausgabe,
    ein Fact = eine atomare Aussage des Interviewten.

    Verwendet ChatOpenAI(base_url=...) — identisch mit InterviewGraph-Pattern
    aus backend/app/interview/graph.py. LLM-Client wird intern instanziiert.

    Retry-Strategie: max_retries=3, exponential backoff (1s, 2s, 4s).
    """

    def __init__(
        self,
        fact_repository: FactRepository,
        assignment_repository: InterviewAssignmentRepository,
        project_repository: Any,          # ProjectRepository (app.clustering.project_repository)
        interview_repository: Any,        # InterviewRepository (app.interview.repository)
        event_bus: SseEventBus,
        settings: Any,                    # app.config.settings.Settings
        clustering_service: Any = None,   # Optional: ClusteringService (Slice 3 DI param)
    ) -> None:
        self._fact_repository = fact_repository
        self._assignment_repository = assignment_repository
        self._project_repository = project_repository
        self._interview_repository = interview_repository
        self._event_bus = event_bus
        self._settings = settings
        self._clustering_service = clustering_service

        # LLM-Client intern instanziieren — identisch mit InterviewGraph-Pattern
        # (backend/app/interview/graph.py: ChatOpenAI(base_url=..., api_key=settings.openrouter_api_key, ...))
        self._llm = ChatOpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=settings.openrouter_api_key,
            model=settings.interviewer_llm,  # Default; wird pro Call mit model_extraction ueberschrieben
            temperature=0.0,
        )

    async def process_interview(
        self,
        project_id: str,
        interview_id: str,
    ) -> None:
        """Orchestriert die komplette Fact-Extraction fuer ein Interview.

        1. Project-Konfiguration laden (extraction_source, research_goal, model_extraction)
        2. extraction_status -> "running"
        3. Interview-Text laden (summary oder transcript)
        4. LLM-Extraktion mit Retry (max 3x)
        5. Facts in DB speichern
        6. extraction_status -> "completed" oder "failed"
        7. SSE-Event publizieren

        Args:
            project_id: UUID des Projekts als String.
            interview_id: UUID des Interviews als String.
        """
        logger.info(f"Fact extraction started for interview {interview_id} in project {project_id}")

        try:
            # 1. Projekt-Konfiguration laden
            project = await self._project_repository.get_by_id(project_id)
            if not project:
                logger.error(f"Project {project_id} not found for fact extraction")
                return

            extraction_source = project.get("extraction_source", "summary")
            research_goal = project.get("research_goal", "")
            model_extraction = project.get("model_extraction") or self._settings.interviewer_llm

            # 2. extraction_status -> "running"
            await self._assignment_repository.update_extraction_status(
                interview_id=interview_id,
                extraction_status="running",
            )

            # 3. Interview-Text laden
            interview = await self._interview_repository.get_session(interview_id)
            if not interview:
                logger.error(f"Interview {interview_id} not found in DB")
                await self._assignment_repository.update_extraction_status(
                    interview_id=interview_id,
                    extraction_status="failed",
                )
                return

            interview_text = self._build_interview_text(interview, extraction_source)

            # 4. LLM-Extraktion mit Retry
            max_retries = getattr(self._settings, "clustering_max_retries", 3)
            prompt = FACT_EXTRACTION_PROMPT.format(
                research_goal=research_goal,
                interview_text=interview_text,
            )

            raw_facts = await self._call_llm_with_retry(
                prompt=prompt,
                model=model_extraction,
                max_retries=max_retries,
            )

            # 5. Facts in DB speichern
            saved_facts = await self._fact_repository.save_facts(
                project_id=project_id,
                interview_id=interview_id,
                facts=raw_facts,
            )
            fact_count = len(saved_facts)

            # 6. extraction_status -> "completed"
            await self._assignment_repository.update_extraction_status(
                interview_id=interview_id,
                extraction_status="completed",
            )

            logger.info(f"Fact extraction completed for interview {interview_id}: {fact_count} facts saved")

            # 7. SSE-Event publizieren
            await self._event_bus.publish(
                project_id=project_id,
                event_type="fact_extracted",
                data={
                    "interview_id": interview_id,
                    "fact_count": fact_count,
                },
            )

            # Clustering-Trigger (Slice 3 DI-Injection)
            if self._clustering_service is not None:
                asyncio.create_task(
                    self._clustering_service.process_interview(
                        project_id=project_id,
                        interview_id=interview_id,
                    )
                )

        except FactExtractionError as e:
            logger.error(f"Fact extraction failed for interview {interview_id}: {e}")
            try:
                await self._assignment_repository.update_extraction_status(
                    interview_id=interview_id,
                    extraction_status="failed",
                )
            except Exception as status_err:
                logger.error(f"Failed to update extraction status to 'failed' for {interview_id}: {status_err}")

        except Exception as e:
            logger.error(f"Unexpected error during fact extraction for interview {interview_id}: {e}")
            try:
                await self._assignment_repository.update_extraction_status(
                    interview_id=interview_id,
                    extraction_status="failed",
                )
            except Exception as status_err:
                logger.error(f"Failed to update extraction status to 'failed' for {interview_id}: {status_err}")

    def _build_interview_text(self, interview: dict, extraction_source: str) -> str:
        """Baut den Interview-Text basierend auf der Extraction Source.

        Args:
            interview: Interview-Dict aus der DB.
            extraction_source: "summary" oder "transcript".

        Returns:
            Text-String der als LLM-Input verwendet wird.
        """
        if extraction_source == "transcript":
            transcript = interview.get("transcript")
            if transcript and isinstance(transcript, list):
                # Transcript als JSONB-Liste -> flacher Text
                lines = []
                for entry in transcript:
                    role = entry.get("role", "unknown")
                    content = entry.get("content", "")
                    lines.append(f"{role}: {content}")
                return "\n".join(lines)
            # Fallback: summary
            return interview.get("summary") or ""
        else:
            # Default: summary
            return interview.get("summary") or ""

    async def extract(
        self,
        interview_text: str,
        research_goal: str,
        model_extraction: str,
    ) -> list[ExtractedFact]:
        """Extrahiert atomare Facts via LLM.

        Args:
            interview_text: Summary-Text oder Transcript-Text.
            research_goal: Lenkender Kontext fuer Extraktion.
            model_extraction: OpenRouter Model-Slug.

        Returns:
            Liste von ExtractedFact-Objekten.

        Raises:
            FactExtractionError: Nach max_retries fehlgeschlagenen LLM-Versuchen.
        """
        max_retries = getattr(self._settings, "clustering_max_retries", 3)
        prompt = FACT_EXTRACTION_PROMPT.format(
            research_goal=research_goal,
            interview_text=interview_text,
        )

        raw_facts = await self._call_llm_with_retry(
            prompt=prompt,
            model=model_extraction,
            max_retries=max_retries,
        )

        return [
            ExtractedFact(
                content=f.get("content", ""),
                quote=f.get("quote"),
                confidence=f.get("confidence"),
            )
            for f in raw_facts
            if f.get("content")
        ]

    async def _call_llm_with_retry(
        self,
        prompt: str,
        model: str,
        max_retries: int = 3,
    ) -> list[dict]:
        """Ruft OpenRouter-LLM auf mit exponential backoff Retry.

        Retry bei:
        - asyncio.TimeoutError (timeout nach settings.clustering_llm_timeout_seconds)
        - JSON-Parse-Fehler (malformed LLM response)

        Kein Retry bei:
        - 401/403 (Auth-Fehler) -- sofort fehlschlagen

        Args:
            prompt: Vollstaendiger Prompt-String.
            model: OpenRouter Model-Slug.
            max_retries: Maximale Anzahl Versuche. Default: 3.

        Returns:
            Geparste JSON-Liste der extrahierten Facts.

        Raises:
            FactExtractionError: Nach max_retries fehlgeschlagenen Versuchen.
        """
        timeout_seconds = getattr(self._settings, "clustering_llm_timeout_seconds", 120)
        last_error: Exception | None = None

        for attempt in range(max_retries):
            try:
                # LLM mit spezifischem Modell aufrufen
                llm_with_model = self._llm.with_config(
                    configurable={"model": model}
                ) if hasattr(self._llm, "with_config") else self._llm

                # Eigene ChatOpenAI-Instanz mit ueberschriebenem Modell
                from langchain_openai import ChatOpenAI as _ChatOpenAI
                llm = _ChatOpenAI(
                    base_url="https://openrouter.ai/api/v1",
                    api_key=self._settings.openrouter_api_key,
                    model=model,
                    temperature=0.0,
                )

                # Async invoke mit Timeout
                response = await asyncio.wait_for(
                    llm.ainvoke(prompt),
                    timeout=timeout_seconds,
                )

                content = response.content
                if isinstance(content, list):
                    content = "".join(str(c) for c in content)

                # JSON-Parse
                facts = json.loads(content)
                if not isinstance(facts, list):
                    raise ValueError(f"Expected JSON array, got: {type(facts)}")

                logger.info(f"LLM extraction successful on attempt {attempt + 1}, got {len(facts)} facts")
                return facts

            except asyncio.TimeoutError as e:
                last_error = e
                logger.warning(f"LLM timeout on attempt {attempt + 1}/{max_retries} for model {model}")

            except json.JSONDecodeError as e:
                last_error = e
                logger.warning(f"JSON parse error on attempt {attempt + 1}/{max_retries}: {e}")

            except ValueError as e:
                last_error = e
                logger.warning(f"Invalid LLM response format on attempt {attempt + 1}/{max_retries}: {e}")

            except Exception as e:
                # Pruefe ob Auth-Fehler (401/403) -- sofort fehlschlagen
                error_str = str(e).lower()
                if "401" in error_str or "403" in error_str or "unauthorized" in error_str or "forbidden" in error_str:
                    logger.error(f"Auth error during LLM call (no retry): {e}")
                    raise FactExtractionError(f"Auth error: {e}") from e

                last_error = e
                logger.warning(f"LLM call failed on attempt {attempt + 1}/{max_retries}: {e}")

            # Exponential backoff: 1s, 2s, 4s (nach letztem fehlgeschlagenen Versuch nicht warten)
            if attempt < max_retries - 1:
                wait_seconds = 2 ** attempt  # 1, 2, 4 Sekunden
                logger.debug(f"Waiting {wait_seconds}s before retry {attempt + 2}")
                await asyncio.sleep(wait_seconds)

        raise FactExtractionError(
            f"LLM extraction failed after {max_retries} retries. Last error: {last_error}"
        )

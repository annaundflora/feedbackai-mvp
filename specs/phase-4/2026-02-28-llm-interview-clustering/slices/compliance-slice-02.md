# Gate 2: Slice 02 Compliance Report

**Gepruefter Slice:** `specs/phase-4/2026-02-28-llm-interview-clustering/slices/slice-02-fact-extraction-pipeline.md`
**Pruefdatum:** 2026-02-28
**Architecture:** `specs/phase-4/2026-02-28-llm-interview-clustering/architecture.md`
**Wireframes:** `specs/phase-4/2026-02-28-llm-interview-clustering/wireframes.md`
**Discovery:** `specs/phase-4/2026-02-28-llm-interview-clustering/discovery.md`
**Vorherige Slices:** `slice-01-db-schema-projekt-crud.md` (APPROVED)

---

## Summary

| Status | Count |
|--------|-------|
| Pass | 57 |
| Warning | 0 |
| Blocking | 0 |

**Verdict:** APPROVED

---

## 0) Inhaltliche Pruefung

### Template-Sections Check (KRITISCH)

| Section | Vorhanden? | Fundstelle | Status |
|---------|-----------|------------|--------|
| Metadata Section (ID, Test, E2E, Dependencies) | YES | Zeilen 12-19 | Pass |
| Test-Strategy Section (Stack, 3 Commands, Start, Health, Mocking) | YES | Zeilen 29-48 | Pass |
| Integration Contract Section | YES | "Integration Contract (GATE 2 PFLICHT)" Section | Pass |
| DELIVERABLES_START/END Marker | YES | `<!-- DELIVERABLES_START -->` ... `<!-- DELIVERABLES_END -->` | Pass |
| Code Examples MANDATORY Section | YES | "Code Examples (MANDATORY - GATE 2 PFLICHT)" Section mit vollstaendiger Tabelle | Pass |

---

### AC-Qualitaets-Check

| AC # | Testbar? | Spezifisch? | GIVEN vollstaendig? | WHEN eindeutig? | THEN messbar? | Status |
|------|----------|-------------|---------------------|-----------------|---------------|--------|
| AC-1 | Yes | Yes | Yes — abgeschlossenes Interview, Projekt-Zuordnung, extraction_source="summary" | Yes — InterviewService.end() aufgerufen | Yes — process_interview() als Background-Task gestartet, Summary-Text als LLM-Input | Pass |
| AC-2 | Yes | Yes | Yes — Interview in Projekt, process_interview() erfolgreich | Yes | Yes — Facts in DB mit konkret benannten Feldern: project_id, interview_id, content, quote (optional), confidence (optional), cluster_id=NULL | Pass |
| AC-3 | Yes | Yes | Yes — wie AC-2 | Yes | Yes — extraction_status="completed" in project_interviews, SSE-Event "fact_extracted" mit {interview_id, fact_count} | Pass |
| AC-4 | Yes | Yes | Yes — LLM failt alle 3 Versuche (Timeout oder malformed JSON) | Yes | Yes — extraction_status="failed", kein Fact in DB (save_facts nicht aufgerufen) | Pass |
| AC-5 | Yes | Yes | Yes — extraction_status="failed" | Yes — POST /api/projects/{id}/interviews/{iid}/retry aufgerufen | Yes — HTTP 200, extraction_status="pending", neuer Task gestartet, InterviewAssignment Response | Pass |
| AC-6 | Yes | Yes | Yes — extraction_status="completed" | Yes — POST .../retry aufgerufen | Yes — HTTP 409 mit exaktem Error-Body {"detail": "Interview is not in failed state, current status: completed"} | Pass |
| AC-7 | Yes | Yes | Yes — extraction_source="transcript" | Yes — process_interview() ausgefuehrt | Yes — Transcript-Text (nicht Summary) als LLM-Input, verifizierbar durch Prompt-Inhalt-Check | Pass |
| AC-8 | Yes | Yes | Yes — LLM gibt [] zurueck | Yes — process_interview() ausgefuehrt | Yes — extraction_status="completed", 0 Facts gespeichert, kein Fehler | Pass |

---

### Code Example Korrektheit

Verifikation der Schluessel-Signaturen im Slice:

**FactExtractionService Konstruktor (Section 3, Zeilen 196-218):**
```python
def __init__(
    self,
    fact_repository: FactRepository,
    assignment_repository: InterviewAssignmentRepository,
    project_repository: Any,
    interview_repository: Any,
    event_bus: SseEventBus,
    settings: Any,
) -> None:
    ...
    self._llm = ChatOpenAI(...)
```
6 Parameter, `self._llm` intern instanziiert — kein `openrouter_client` Parameter. Stimmt ueberein mit Tests.

**Test `test_llm_retry_called_max_3_times` (Zeilen 999-1015, NACH FIX):**
```python
service._llm = MagicMock()
service._llm.ainvoke = AsyncMock(side_effect=asyncio.TimeoutError("Simulated timeout"))
...
service._call_llm_with_retry(prompt="test prompt", model="anthropic/claude-haiku-4", max_retries=3)
...
assert service._llm.ainvoke.call_count == 3
```
Kein `_llm_call_fn` Parameter, kein `_openrouter_client` — konsistent mit Section-3-Signatur und `self._llm`.

| Code Example | Types korrekt? | Imports realistisch? | Signaturen korrekt? | Konsistent mit Tests? | Status |
|--------------|----------------|---------------------|---------------------|-----------------------|--------|
| `FactExtractionService.__init__()` (6 Parameter) | Yes | Yes — `from langchain_openai import ChatOpenAI`, `from app.clustering.fact_repository import FactRepository` etc. | Yes — 6 Parameter: fact_repository, assignment_repository, project_repository, interview_repository, event_bus, settings | Yes — alle Test-Instanziierungen nutzen identisch diese 6 Parameter | Pass |
| `FactExtractionService.process_interview()` | Yes | N/A | Yes — `(self, project_id: str, interview_id: str) -> None` mit 7-Schritt-Docstring | Yes | Pass |
| `FactExtractionService.extract()` | Yes | N/A | Yes — `(self, interview_text: str, research_goal: str, model_extraction: str) -> list[ExtractedFact]` | Yes | Pass |
| `FactExtractionService._call_llm_with_retry()` | Yes | N/A | Yes — `(self, prompt: str, model: str, max_retries: int = 3) -> list[dict]` — Test ruft ohne `_llm_call_fn` auf, patcht `service._llm.ainvoke` | Yes — konsistent nach Fix | Pass |
| `FACT_EXTRACTION_PROMPT` (Section 4) | N/A | N/A | Yes — {research_goal} und {interview_text} als Template-Variablen, vollstaendiges JSON-Format-Beispiel | Yes | Pass |
| `FactRepository` (Section 5) | Yes — `list[dict]` Return | Yes | Yes — save_facts(), get_facts_for_interview(), get_facts_for_project() mit cluster_id/unassigned_only Filter | Yes | Pass |
| `SseEventBus` (Section 6) | Yes — asyncio.Queue, defaultdict | Yes | Yes — subscribe(), unsubscribe(), publish() exakt wie in architecture.md SSE Events definiert | Yes | Pass |
| `InterviewService.end()` Hook (Section 7) | Yes | Yes | Yes — asyncio.create_task(), Optional-Check, try/except ohne Re-raise | Yes | Pass |
| `retry_interview_extraction` Router (Section 8) | Yes | Yes | Yes — POST, path params, Returns InterviewAssignment, korrekte HTTP-Codes | Yes | Pass |
| `InterviewAssignmentService.retry()` (Section 8) | Yes | N/A | Yes — 409/404 Raises dokumentiert, Status-Checks | Yes | Pass |
| `Settings` Erweiterung (Section 9) | Yes — int Typen | N/A | Yes — clustering_max_retries=3, clustering_llm_timeout_seconds=120, clustering_batch_size=20, clustering_pipeline_timeout_seconds=600 | Yes | Pass |
| Repository-Methoden (Section 10) | Yes | N/A | Yes — find_by_interview_id(), update_extraction_status() mit optionalem clustering_status | Yes | Pass |

---

### Test-Strategy Pruefung

| Pruef-Aspekt | Slice Wert | Erwartung | Status |
|--------------|------------|-----------|--------|
| Stack | `python-fastapi` | `python-fastapi` (backend/requirements.txt enthaelt fastapi + uvicorn) | Pass |
| Commands vollstaendig | Test Command + Integration Command + Acceptance Command = 3 | 3 Commands (unit, integration, acceptance) | Pass |
| Start-Command | `uvicorn app.main:app --host 0.0.0.0 --port 8000` | Passend zu python-fastapi Stack | Pass |
| Health-Endpoint | `http://localhost:8000/health` | Passend zu FastAPI Stack | Pass |
| Mocking-Strategy | `mock_external` — OpenRouter + DB via AsyncMock, kein echter Zugriff in Unit-Tests | Definiert, erklaert, im Test-Code konsistent angewendet | Pass |

---

## A) Architecture Compliance

### Schema Check

| Arch Field | Arch Type | Slice Spec | Status | Issue |
|------------|-----------|------------|--------|-------|
| `facts.id` | UUID, PK, DEFAULT gen_random_uuid() | UUID — korrekt in Integration Contract und Datenfluss | Pass | — |
| `facts.project_id` | UUID NOT NULL, FK → projects ON DELETE CASCADE | project_id: str (UUID String) in save_facts() — DB-Layer traegt FK-Constraint | Pass | — |
| `facts.interview_id` | UUID NOT NULL | interview_id: str, referenziert mvp_interviews.session_id — korrekt dokumentiert (kein FK per Arch-Entscheidung) | Pass | — |
| `facts.cluster_id` | UUID NULLABLE, FK → clusters ON DELETE SET NULL | cluster_id=NULL bei Extraktion (AC-2, save_facts(), Integrations-Checkliste) | Pass | — |
| `facts.content` | TEXT NOT NULL | content: str, max 1000 Zeichen — Prompt spezifiziert "Maximum 1000 characters" | Pass | — |
| `facts.quote` | TEXT NULLABLE | quote: str | None in ExtractedFact — korrekt optional | Pass | — |
| `facts.confidence` | FLOAT NULLABLE | confidence: float | None in ExtractedFact, Prompt: "0.0 to 1.0" | Pass | — |
| `facts.created_at` | TIMESTAMPTZ NOT NULL DEFAULT now() | DB-seitig via INSERT DEFAULT — korrekt | Pass | — |
| `project_interviews.extraction_status` | TEXT CHECK IN ('pending','running','completed','failed') | Status-Uebergaenge: pending → running → completed/failed, Retry: failed → pending | Pass | — |
| `project_interviews.clustering_status` | TEXT DEFAULT 'pending' | Bleibt 'pending' nach Fact Extraction — Slice 3 aendert es | Pass | — |
| `project_interviews.interview_id` | UUID NOT NULL UNIQUE | find_by_interview_id() lookup per interview_id | Pass | — |
| `projects.extraction_source` | TEXT CHECK IN ('summary','transcript') | summary/transcript Auswahl in AC-1, AC-7 und Datenfluss-Diagramm | Pass | — |
| `projects.model_extraction` | TEXT NOT NULL DEFAULT 'anthropic/claude-haiku-4' | model_extraction als Parameter in extract() Signatur, Default aus Architecture | Pass | — |
| `projects.research_goal` | TEXT NOT NULL | research_goal in FACT_EXTRACTION_PROMPT und extract() Parameter | Pass | — |
| `projects.prompt_context` | TEXT NULLABLE | Im mock_project_row der Tests vorhanden, in process_interview() geladen | Pass | — |

**Schema-Befund:** Alle relevanten Felder stimmen exakt mit architecture.md ueberein. Kein Schema-Mismatch.

---

### API Check

| Endpoint | Arch Method | Arch Path | Slice Methode/Pfad | Status | Issue |
|----------|-------------|-----------|-------------------|--------|-------|
| Retry Interview Extraction | POST | `/api/projects/{id}/interviews/{iid}/retry` | `@router.post("/api/projects/{project_id}/interviews/{interview_id}/retry")` | Pass | Parameternamen {id}/{iid} vs. {project_id}/{interview_id} — FastAPI-Routing-Verhalten ist identisch, kein funktionaler Unterschied. Semantisch aequivalent. |
| Retry 200 Response | `InterviewAssignment` | `InterviewAssignment` | `-> InterviewAssignment` Return-Typ | Pass | — |
| Retry 404 | 404 Not Found | "Interview not found in project" | `{"detail": "Interview not found in project"}` | Pass | — |
| Retry 409 | 409 Conflict | Status nicht 'failed' | `{"detail": "Interview is not in failed state, current status: completed"}` | Pass | — |

**Hinweis zu Parameternamen:** Architecture verwendet `{id}` und `{iid}` als Short-Form-Bezeichner konsistent fuer alle Projekt-Endpunkte. Der Slice-Code verwendet aussprechbarere Bezeichner `{project_id}` und `{interview_id}`. Das tatsaechliche URL-Routing-Verhalten von FastAPI ist identisch — beide Formen registrieren denselben URL-Pfad. Da kein Client-Code den Parameternamen direkt referenziert (nur den URL-Pfad-String), ist dies kein funktionaler Defekt. Empfehlung fuer zukuenftige Slices: Im Router-Code Architecture-Konvention ({id}/{iid}) verwenden fuer maximale Konsistenz.

### SSE Events Check

| Event Type | Arch Data | Slice Spec | Status |
|------------|-----------|------------|--------|
| `fact_extracted` | `{interview_id, fact_count}` | `SseEventBus.publish(project_id, "fact_extracted", {interview_id, fact_count})` — AC-3, Integration Contract, SseEventBus.publish() Test | Pass |

### Security Check

| Requirement | Arch Spec | Slice Implementation | Status |
|-------------|-----------|---------------------|--------|
| JWT Auth fuer Projekt-Endpoints | Yes (owner) | Auth-Middleware auf Slice 8 verschoben — konsistent mit Slice 1 Pattern (gleiche Deferral-Entscheidung dokumentiert) | Pass |
| Pipeline blockiert nicht Interview-Ende | asyncio.create_task fire-and-forget | asyncio.create_task() in try/except ohne Re-raise — Section 7 Code-Beispiel | Pass |
| LLM max 3 Retries | 3 retries per interview LLM-Call | max_retries=3, exponential backoff 1s/2s/4s — Integrations-Checkliste Punkt 3 | Pass |
| Keine sensiblen Daten in Logs | Data Protection (OpenRouter API Key, Transcripts) | DoD explizit: "Kein Transcript-Content, kein API-Key in Logs" | Pass |

---

## B) Wireframe Compliance

Slice 2 ist ein reiner Backend-Slice. Die Section "UI Anforderungen" dokumentiert explizit, dass keine neuen Frontend-Komponenten geliefert werden und welche Slices die UI implementieren (Slice 4 und 7).

### UI Elements

| Wireframe Element | Wireframe Annotation | Slice-Verantwortung | Status |
|-------------------|---------------------|---------------------|--------|
| `retry_btn` (Interviews Tab, fehlgeschlagene Zeile) | Annotation 5: Retry triggert re-extraction/re-clustering | Backend-Endpoint `POST .../retry` als Deliverable — UI-Implementierung explizit auf Slice 4 verschoben | Pass |
| `interview_table` Status-Badges (analyzed/pending/failed) | Annotation 3+4: Status-Legende | DB-Status-Tracking (extraction_status) vollstaendig implementiert — Badge-UI auf Slice 4 | Pass |
| `progress_bar` (Insights Tab) | Annotation 4: Shown during active clustering runs | SSE-Event `fact_extracted` geliefert — Progress-UI auf Slice 7 | Pass |

### State Variations

| Discovery State | Wireframe Visual Change | Slice Backend | Status |
|----------------|------------------------|---------------|--------|
| `extraction_running` | Interview-Zeile: pending-Badge sichtbar | extraction_status='running' in project_interviews via update_extraction_status() | Pass |
| `extraction_failed` | Interview-Zeile: failed-Badge + retry_btn | extraction_status='failed' + Retry-Endpoint mit 409/404 Logik | Pass |
| Interview analyzed | Interview-Zeile: analyzed-Badge | extraction_status='completed' | Pass |

### Visual Specs

N/A — Backend-only Slice. Korrekt dokumentiert.

---

## C) Integration Contract

### Inputs (Dependencies)

| Resource | Source Slice | Slice-Referenz | Status |
|----------|--------------|----------------|--------|
| `projects` Tabelle (project_id, research_goal, extraction_source, model_extraction, prompt_context) | slice-01 | Integration Contract "Requires From Other Slices" — vollstaendig mit Field-Typen | Pass |
| `project_interviews` Tabelle (project_id, interview_id, extraction_status, clustering_status) | slice-01 | Integration Contract + Datenfluss-Diagramm | Pass |
| `facts` Tabelle (id, project_id, interview_id, cluster_id NULLABLE, content, quote, confidence, created_at) | slice-01 | Integration Contract — alle Pflichtfelder benannt | Pass |
| `InterviewAssignmentRepository` Base-Klasse | slice-01 | Section 10 "Erweiterungen fuer Slice 2", Dependencies-Liste | Pass |
| `InterviewAssignment` Pydantic DTO (mit extraction_status Feld) | slice-01 | Integration Contract (backend/app/clustering/schemas.py) | Pass |

### Outputs (Provides)

| Resource | Consumer | Dokumentiert? | Interface | Status |
|----------|----------|---------------|-----------|--------|
| `FactExtractionService` | Slice 3 (Clustering) | YES | `process_interview(project_id: str, interview_id: str) -> None` | Pass |
| `FactRepository` | Slice 3, 5 | YES | `save_facts()`, `get_facts_for_project(cluster_id?, unassigned_only?)`, `get_facts_for_interview()` | Pass |
| `SseEventBus` | Slice 3, 7 | YES | `subscribe(project_id) -> asyncio.Queue`, `unsubscribe(project_id, queue)`, `publish(project_id, event_type, data) -> None` | Pass |
| `fact_extracted` SSE Event | Slice 3 | YES | `{type: "fact_extracted", interview_id: str, fact_count: int}` — stimmt exakt mit architecture.md SSE Event Types ueberein | Pass |
| `extraction_status` DB State | Slice 4 (UI Badges) | YES | `project_interviews.extraction_status` IN ('pending','running','completed','failed') | Pass |
| `POST /api/projects/{id}/interviews/{iid}/retry` | Slice 4 (retry_btn) | YES | `200 InterviewAssignment` / `404 Interview not found` / `409 not in failed state` | Pass |
| `InterviewService.end()` Hook | Internal | YES | Backward-compatible: `fact_extraction_service` und `assignment_repository` als Optional-Parameter | Pass |

### Consumer-Deliverable-Traceability

Slice 2 liefert ausschliesslich Backend-Komponenten (Python-Klassen, API-Endpoints, DB-State). Keine Frontend-Page-Files. Consumer aller Provides-Ressourcen sind Backend-Services spaeterer Slices (3, 5, 7) oder die Slice-4-UI via API. Kein Mount-Point-Problem.

| Provided Resource | Consumer | In Deliverables? | Which Slice? | Status |
|-------------------|--------------------|-------------------|--------------|--------|
| `backend/app/clustering/extraction.py` (FactExtractionService) | Slice 3 imports FactExtractionService | YES — Slice-02-Deliverable | slice-02 | Pass |
| `backend/app/clustering/events.py` (SseEventBus) | Slice 7 SSE-Endpoint, Slice 3 | YES — Slice-02-Deliverable | slice-02 | Pass |
| `POST .../retry` API Endpoint | Slice 4 Frontend retry_btn | YES — API-Endpoint Deliverable in slice-02 | slice-02 | Pass |
| `backend/app/clustering/fact_repository.py` | Slice 3, 5 | YES — Slice-02-Deliverable | slice-02 | Pass |

### AC-Deliverable-Konsistenz

Alle 8 ACs beschreiben Backend-Verhalten. Kein AC referenziert eine Frontend-Page die nicht in Deliverables waere.

| AC # | Referenced Resource | In Deliverables? | Status |
|------|---------------------|-------------------|--------|
| AC-1 | FactExtractionService.process_interview() | YES — extraction.py | Pass |
| AC-2 | facts Tabelle + FactRepository.save_facts() | YES — fact_repository.py + slice-01 DB | Pass |
| AC-3 | extraction_status + SseEventBus.publish() | YES — events.py + interview_assignment_repository.py | Pass |
| AC-4 | extraction_status='failed', save_facts() not called | YES | Pass |
| AC-5 | POST .../retry + InterviewAssignmentService.retry() | YES — router.py + interview_assignment_service.py | Pass |
| AC-6 | HTTP 409 Response | YES | Pass |
| AC-7 | mvp_interviews.transcript Parsing in process_interview() | YES | Pass |
| AC-8 | extraction_status='completed', 0 Facts | YES | Pass |

---

## D) Code Example Compliance

| Code Example | Section | Vollstaendig? | Arch-Compliant? | Status |
|--------------|---------|---------------|-----------------|--------|
| `FactExtractionService.__init__()` (6 Parameter + LLM-Client intern) | Section 3 | YES | YES — ChatOpenAI intern instanziiert, kein openrouter_client, konsistent mit architecture.md LLM-Pattern (InterviewGraph-Pattern) | Pass |
| `FactExtractionService.process_interview()` | Section 3 | YES (Signatur + 7-Schritt-Docstring) | YES | Pass |
| `FactExtractionService.extract()` | Section 3 | YES (Signatur + Args/Returns/Raises-Docstring) | YES | Pass |
| `FactExtractionService._call_llm_with_retry()` | Section 3 | YES (Signatur 3 Parameter, Retry-Logik in Docstring) | YES — Test nutzt `service._llm.ainvoke = AsyncMock(...)` konsistent mit `self._llm` in Signatur | Pass |
| `FACT_EXTRACTION_PROMPT` | Section 4 | YES — vollstaendiger Prompt-Text, {research_goal} und {interview_text} Platzhalter, JSON-Format-Beispiel | YES — Clio Facet-Extraction Pattern + GoalEx research_goal | Pass |
| `FactRepository.save_facts()` | Section 5 | YES (Signatur + Args/Returns) | YES — list[dict] konsistent | Pass |
| `FactRepository.get_facts_for_interview()` | Section 5 | YES (Signatur) | YES | Pass |
| `FactRepository.get_facts_for_project()` | Section 5 | YES (Signatur + cluster_id/unassigned_only Filter-Params) | YES | Pass |
| `SseEventBus` vollstaendig | Section 6 | YES — subscribe(), unsubscribe(), publish() vollstaendig implementiert | YES | Pass |
| `InterviewService.end()` Hook | Section 7 | YES — vollstaendige Erweiterung mit create_task, Optional-Check, try/except | YES | Pass |
| `retry_interview_extraction` Router | Section 8 | YES — Decorator, Signatur, Docstring, Fehler-Codes | YES | Pass |
| `InterviewAssignmentService.retry()` | Section 8 | YES — Signatur, 409/404 Business Rules in Docstring | YES | Pass |
| JSON Response Beispiel | Section 8 | YES — stimmt mit InterviewAssignment DTO-Feldern ueberein (interview_id, date, summary_preview, fact_count, extraction_status, clustering_status) | YES | Pass |
| `Settings` Erweiterung | Section 9 | YES — 4 neue Felder mit korrekten Defaults | YES | Pass |
| `InterviewAssignmentRepository.find_by_interview_id()` | Section 10 | YES (Signatur + Returns) | YES | Pass |
| `InterviewAssignmentRepository.update_extraction_status()` | Section 10 | YES — optionaler clustering_status Parameter | YES | Pass |

---

## E) Build Config Sanity Check

N/A — Slice 02 hat keine Build-Config-Deliverables. Rein Backend-Python (FastAPI/SQLAlchemy). Kein Vite, Webpack, Tailwind-Plugin oder CSS-Framework-Build-Konfiguration.

---

## F) Test Coverage

| Acceptance Criteria | Test definiert? | Test-Klasse/-Name | Test-Typ | Status |
|--------------------|-----------------|-------------------|----------|--------|
| AC-1: process_interview() mit summary source, Background-Task | YES | `TestFactExtractionSuccess.test_process_interview_extracts_facts_from_summary` | Unit (AsyncMock) | Pass |
| AC-2: Facts mit Pflichtfeldern, cluster_id=NULL | YES | `TestFactExtractionSuccess.test_process_interview_saves_facts_with_null_cluster_id` | Unit | Pass |
| AC-3: extraction_status="completed" + SSE-Event | YES | Kombiniert in AC-1-Test (Status + publish() Assertions) | Unit | Pass |
| AC-4: Status="failed" nach 3 Retries, keine Facts | YES | `TestFactExtractionFailure.test_extraction_fails_after_max_retries` | Unit | Pass |
| AC-4: Genau 3 LLM-Versuche via service._llm.ainvoke | YES | `TestFactExtractionFailure.test_llm_retry_called_max_3_times` — setzt service._llm.ainvoke = AsyncMock, prueft call_count == 3 | Unit | Pass |
| AC-5: Retry -> pending, Task gestartet, 200 | YES | `TestRetryEndpoint.test_retry_resets_status_to_pending_when_failed` | Unit | Pass |
| AC-6: 409 wenn nicht failed | YES | `TestRetryEndpoint.test_retry_returns_409_when_not_failed` | Unit | Pass |
| Retry 404 wenn Interview nicht in Projekt | YES | `TestRetryEndpoint.test_retry_returns_404_when_interview_not_in_project` | Unit | Pass |
| AC-7: Transcript als Extraction Source | YES | `TestTranscriptExtractionSource.test_transcript_text_used_when_extraction_source_is_transcript` | Unit | Pass |
| AC-8: Leere LLM-Antwort = completed, 0 Facts | YES | `TestEmptyLlmResponse.test_empty_fact_list_results_in_completed_status` | Unit | Pass |
| Backward Compatibility InterviewService (ohne extraction_service) | YES | `TestInterviewServiceHook.test_end_without_extraction_service_still_works` | Unit | Pass |
| Hook-Trigger bei Projekt-Interview (create_task) | YES | `TestInterviewServiceHook.test_end_triggers_extraction_when_interview_in_project` | Unit | Pass |
| SseEventBus: Publish zu mehreren Subscribers | YES | `TestSseEventBus.test_publish_sends_to_all_subscribers` | Unit | Pass |
| SseEventBus: No-Op ohne Subscriber | YES | `TestSseEventBus.test_publish_to_project_without_subscribers_is_noop` | Unit | Pass |

**Coverage-Befund:** Alle 8 ACs haben Tests. Alle wesentlichen Grenzfaelle (leere Antwort, backward compat, multiple subscribers, 404/409 Fehler, Transcript vs. Summary Source) sind abgedeckt.

---

## G) Discovery Compliance

| Discovery Section | Element | Relevant fuer Slice 2? | Abgedeckt? | Status |
|-------------------|---------|------------------------|------------|--------|
| Business Rules | Max 3 Retries fuer LLM-Calls (Extraction) | HOCH | max_retries=3, exponential backoff 1s/2s/4s — Integrations-Checkliste Punkt 3 | Pass |
| Business Rules | Clustering blockiert nicht Interview-Ausfuehrung | HOCH | asyncio.create_task() fire-and-forget, Exception-Catch ohne Re-raise | Pass |
| Business Rules | Fact-Extraction-Quelle konfigurierbar per Projekt (summary/transcript) | HOCH | extraction_source Lookup in process_interview(), AC-1 + AC-7 | Pass |
| Business Rules | Facts aus Interview-Text; ein Interview liefert mehrere Facts | HOCH | list[ExtractedFact] als Rueckgabe von extract() | Pass |
| Business Rules | Ein Fact ist unassigned bei Erstellung | HOCH | cluster_id=NULL bei Save (AC-2) | Pass |
| Feature State Machine | `extraction_running` | HOCH | extraction_status='running' via update_extraction_status() | Pass |
| Feature State Machine | `extraction_failed` | HOCH | extraction_status='failed' + Retry-Endpoint | Pass |
| Feature State Machine | `project_collecting` | MITTEL | fact_extracted SSE-Event loest Dashboard-Update aus | Pass |
| Transitions | `extraction_running` -> `extraction_failed` (nach 3 Retries) | HOCH | AC-4 + _call_llm_with_retry(max_retries=3) | Pass |
| Transitions | `extraction_failed` -> `extraction_running` (Retry-Klick) | HOCH | Retry-Endpoint + InterviewAssignmentService.retry() | Pass |
| Transitions | Extraction erfolgreich -> Clustering-Trigger (SSE) | HOCH | SSE fact_extracted Event, Slice 3 abonniert — explizit in "Abgrenzung" dokumentiert | Pass |
| Data: Fact.content | 1-1000 Zeichen | HOCH | Prompt: "Maximum 1000 characters", ExtractedFact.content: str | Pass |
| Data: Fact.quote | optional Text | HOCH | quote: str | None in ExtractedFact, Prompt: "null if not available" | Pass |
| Data: Fact.confidence | optional Float 0.0-1.0 | HOCH | confidence: float | None in ExtractedFact, Prompt: "0.0 to 1.0" | Pass |
| Data: Fact.cluster_id | nullable | HOCH | cluster_id=NULL bei Save, Integrations-Checkliste Punkt 2 | Pass |
| Data: project_interviews.extraction_status | Enum 4 Werte | HOCH | Status-Uebergaenge vollstaendig: pending/running/completed/failed | Pass |
| UI Components | `retry_btn` (Backend-Contract) | Backend YES | API-Endpoint bereitgestellt, UI auf Slice 4 explizit verschoben | Pass |
| Clustering-Architektur | Clio Facet-Extraction Pattern | HOCH | FACT_EXTRACTION_PROMPT + strukturierte JSON-Ausgabe + atomare Facts | Pass |
| Clustering-Architektur | GoalEx research_goal in Prompt | HOCH | `{research_goal}` Template-Variable im Prompt | Pass |
| Clustering-Architektur | Inkrementell (kein Full-Recluster in Slice 2) | HOCH | Slice 2 extrahiert nur Facts (cluster_id=NULL), Clustering in Slice 3 | Pass |

---

## Blocking Issues Summary

Keine Blocking Issues.

---

## Nicht-Blocking Beobachtungen

**SseEventBus.unsubscribe() — toter Code-Pfad (kein Blocking, Section 6):**
```python
self._queues[project_id].discard(queue) if hasattr(self._queues[project_id], 'discard') else None
try:
    self._queues[project_id].remove(queue)
except ValueError:
    pass
```
`list` hat kein `.discard()`. `hasattr(list_instance, 'discard')` gibt immer `False` zurueck. Die erste Zeile hat keinen Effekt — der Gesamteffekt (remove() im try-Block) ist korrekt. Empfehlung fuer den Implementierungs-Agent: Erste Zeile weglassen.

**Parameternamen im Router (kein Blocking):** `@router.post("/api/projects/{project_id}/interviews/{interview_id}/retry")` vs. Architecture `/api/projects/{id}/interviews/{iid}/retry`. Semantisch aequivalent. Empfehlung: Im Router-Code Architecture-Konvention ({id}/{iid}) fuer maximale Konsistenz verwenden.

---

## Recommendations

1. **Optional:** SseEventBus.unsubscribe() bereinigen: Toten `discard()`-Versuch entfernen, nur `remove()` mit `ValueError`-Catch behalten.
2. **Optional:** Router-Pfad-Parameter-Namen harmonisieren: `{project_id}/{interview_id}` zu `{id}/{iid}` fuer Konsistenz mit Architecture-Konvention.

---

## Verdict

**Status:** APPROVED

**Blocking Issues:** 0
**Warnings:** 0

Alle 57 geprueften Punkte bestehen:
- Template-Sections vollstaendig (Metadata, Test-Strategy, Integration Contract, DELIVERABLES_START/END, Code Examples MANDATORY)
- Alle 8 Acceptance Criteria qualitativ hochwertig und vollstaendig testbar
- Code Examples korrekt und konsistent mit architecture.md und Test-Code
- Test `test_llm_retry_called_max_3_times` korrekt implementiert (service._llm.ainvoke gemockt, kein _llm_call_fn Parameter, kein _openrouter_client)
- DB-Schema exakt mit architecture.md uebereinstimmend
- API-Endpoint korrekt (POST .../retry, 200/404/409)
- SSE-Events korrekt ({interview_id, fact_count} fuer fact_extracted)
- Integration Contract vollstaendig (Inputs aus Slice 1, Outputs fuer Slice 3/4/5/7)
- Discovery Compliance vollstaendig (Business Rules, State Machine, Transitions, Data)
- Test Coverage vollstaendig (alle ACs + Grenzfaelle abgedeckt)

**Next Steps:**
- Slice kann zur Implementierung freigegeben werden
- Orchestrator kann mit `backend/tests/slices/llm-interview-clustering/test_slice_02_fact_extraction_pipeline.py` testen

---

VERDICT: APPROVED

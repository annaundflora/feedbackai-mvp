# Bug: assign() startet keine Fact Extraction → Interviews bleiben dauerhaft "pending"

**Entdeckt:** 2026-03-01
**Status:** ✅ Gefixt
**Priority:** 🔴 Kritisch
**Location:** `backend/app/clustering/interview_assignment_service.py:35-68`

---

## Problembeschreibung

Wenn Interviews einem Projekt manuell zugeordnet werden (`POST /api/projects/{id}/interviews/assign`), bleibt `extraction_status` dauerhaft auf `pending`. Es werden weder Fact-Extraction-Tasks gestartet noch LLM-Aufrufe ausgelöst.

Die gesamte Clustering-Pipeline (Extraction → Clustering → Cluster-Karten) bleibt still, ohne Fehler im Log.

## Reproduktion

1. Interviews in `mvp_interviews` seeden (summary/transcript vorhanden)
2. Projekt anlegen
3. Interviews über UI → "Assign Interviews" Modal zuordnen
4. → Status in der Interviews-Tabelle: `pending` (korrekt nach Zuordnung)
5. → Warten… Status bleibt `pending`
6. → OpenRouter: keine Aufrufe, LangSmith: keine Runs
7. → Keine Backend-Logs über Extraction-Start

## Root Cause

`InterviewAssignmentService.assign()` (Zeile 35-68) speichert die Zuordnung in der DB, ruft aber **nie** `self._fact_extraction_service.process_interview()` auf:

```python
# backend/app/clustering/interview_assignment_service.py:35-68 — FEHLT der Trigger:
async def assign(self, project_id: str, request: AssignRequest) -> list[InterviewAssignment]:
    interview_ids = [str(iid) for iid in request.interview_ids]
    rows = await self._repo.assign_interviews(...)
    return [InterviewAssignment(...) for row in rows]
    # ← kein Aufruf von self._fact_extraction_service.process_interview()
```

Vergleich mit `retry()` (Zeile 162-168) — das MACHT den Trigger korrekt:

```python
if self._fact_extraction_service is not None:
    asyncio.create_task(
        self._fact_extraction_service.process_interview(
            project_id=project_id,
            interview_id=interview_id,
        )
    )
```

Die Extraction wird nur in `InterviewService.end()` (Live-Interview-Hook) und `retry()` getriggert — nicht bei manuellem Assignment über die API.

## Erwartetes Verhalten

- Nach `assign()`: Für jedes neu zugeordnete Interview startet ein Background-Task für `FactExtractionService.process_interview()`
- `extraction_status` wechselt von `pending` → `processing` → `done` (oder `failed`)
- LLM-Aufrufe erscheinen in OpenRouter / LangSmith

## Tatsächliches Verhalten

- Nach `assign()`: Status bleibt permanent `pending`
- Kein Task, kein LLM-Aufruf, kein Log
- UI zeigt alle Interviews mit `pending`-Badge, keine Fortschrittsänderung

## Fix-Vorschlag

In `assign()` nach dem Speichern der Rows einen Background-Task pro Interview starten:

```python
async def assign(self, project_id: str, request: AssignRequest) -> list[InterviewAssignment]:
    interview_ids = [str(iid) for iid in request.interview_ids]
    rows = await self._repo.assign_interviews(
        project_id=project_id,
        interview_ids=interview_ids,
    )
    # Extraction für jedes neu zugeordnete Interview starten
    if self._fact_extraction_service is not None:
        for interview_id in interview_ids:
            asyncio.create_task(
                self._fact_extraction_service.process_interview(
                    project_id=project_id,
                    interview_id=interview_id,
                )
            )
            logger.info(f"Assign: Fact extraction task started for interview {interview_id}")
    return [InterviewAssignment(...) for row in rows]
```

## Nächste Schritte

1. [ ] `assign()` um Extraction-Loop erweitern (gleiche Pattern wie `retry()`)
2. [ ] Test: Nach assign() erscheint mindestens 1 Extraction-Task im Log
3. [ ] Test: Status wechselt von `pending` → `processing` → `done`

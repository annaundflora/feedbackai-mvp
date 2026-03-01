# Bug: ClusteringService ruft get_by_id ohne user_id auf → Recluster crasht

**Entdeckt:** 2026-03-01
**Status:** ✅ Gefixt
**Priority:** 🔴 Hoch
**Location:** `backend/app/clustering/service.py:93` + `service.py:318`

---

## Problembeschreibung

`ClusteringService.process_interview()` (Zeile 93) und `ClusteringService.full_recluster()` (Zeile 318) rufen `ProjectRepository.get_by_id(project_id)` auf. Die Methode erfordert aber **zwei** Argumente: `get_by_id(project_id, user_id)`.

Das führt zu einem `TypeError` im Hintergrund-Task — der Recluster schlägt still fehl.

## Backend-Fehler (aus Server-Log)

```
Full re-cluster failed for project 36d19cd5-...:
ProjectRepository.get_by_id() missing 1 required positional argument: 'user_id'

Traceback:
  File "backend/app/clustering/service.py", line 318, in full_recluster
    project = await self._project_repo.get_by_id(project_id)
TypeError: ProjectRepository.get_by_id() missing 1 required positional argument: 'user_id'
```

## Reproduktion

1. Projekt mit zugeordnetem Interview anlegen
2. "Recalculate" Button klicken → `POST /api/projects/{id}/clustering/recluster` → 200 OK
3. → Backend-Log zeigt sofort den TypeError
4. Clustering startet nie, keine Cluster werden erstellt

## Erwartetes Verhalten

- `full_recluster()` lädt das Projekt erfolgreich und startet den Clustering-Prozess
- Clustering-Pipeline läuft durch, neue Cluster werden erstellt

## Tatsächliches Verhalten

- `get_by_id()` wirft `TypeError` → Recluster bricht ab
- HTTP 200 wird trotzdem zurückgegeben (BackgroundTask hat schon gestartet)
- Kein Cluster wird erstellt, keine Fehlermeldung im UI

## Root Cause

`ProjectRepository.get_by_id()` wurde in Slice 08 um den `user_id` Parameter erweitert (zur Cross-User-Isolation). `ClusteringService` (Slice 03) wurde nicht angepasst und ruft die Methode noch mit nur einem Argument auf.

```python
# backend/app/clustering/project_repository.py
async def get_by_id(self, project_id: str, user_id: str) -> dict | None:
    # Filtert auf user_id für Cross-User-Isolation

# backend/app/clustering/service.py:93 + 318 — FALSCH:
project = await self._project_repo.get_by_id(project_id)  # fehlt user_id!
```

## Fix-Vorschlag

**Option A (empfohlen):** `get_by_id_internal(project_id)` ohne user_id-Filter für interne Service-Aufrufe hinzufügen:
```python
async def get_by_id_internal(self, project_id: str) -> dict | None:
    """Interne Nutzung: kein User-Filter (für Background-Tasks)."""
    result = await self._db.execute(
        text("SELECT * FROM projects WHERE id = :id"),
        {"id": UUID(project_id)},
    )
    ...
```

**Option B:** `user_id` durch den ganzen Call-Stack durchreichen (komplex).

## Test-Evidenz

- `backend/app/clustering/service.py:93` — `process_interview()` Call
- `backend/app/clustering/service.py:318` — `full_recluster()` Call
- `backend/app/clustering/project_repository.py` — Methode erfordert `user_id`
- Backend-Log: TypeError bei jedem Clustering-Trigger

## Nächste Schritte

1. [ ] `get_by_id_internal()` in `ProjectRepository` hinzufügen (ohne user_id-Filter)
2. [ ] Beide Aufrufe in `service.py` (Zeile 93 + 318) auf `get_by_id_internal()` umstellen
3. [ ] Test: Recluster erfolgreich durchläuft (ohne TypeError)
4. [ ] Prüfen ob `process_interview()` auch betroffen ist (Zeile 93)

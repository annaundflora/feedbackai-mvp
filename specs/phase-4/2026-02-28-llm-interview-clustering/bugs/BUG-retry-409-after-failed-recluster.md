# Bug: Retry gibt 409 obwohl Interview-Status "failed" zeigt

**Entdeckt:** 2026-03-01
**Status:** ✅ Gefixt (via Bug #2 Fix)
**Priority:** 🟡 Mittel
**Location:** `backend/app/clustering/service.py:318` (Cascade aus BUG-clustering-service-missing-user-id)

---

## Problembeschreibung

Nach dem Klick auf "Retry" bei einem Interview mit "failed" Badge gibt die API `409 Conflict` zurück. Der User kann das Interview nicht neu starten.

## Reproduktion

1. Interview wird zugeordnet → Extraction schlägt fehl → Status: `failed`
2. User löst Recluster aus (manuell oder automatisch)
3. Recluster setzt alle Interview-Statuses auf `pending` **bevor er crasht** (Bug #3)
4. In der DB: `extraction_status = 'pending'`
5. Im UI: Noch cached/stale → zeigt `failed`
6. User klickt "Retry" → Backend sieht `pending` → 409 "Interview is not in failed state"

## Root Cause

Cascading Bug aus `BUG-clustering-service-missing-user-id.md`:

1. `full_recluster()` resettet alle Assignments auf `pending` (korrekt)
2. Dann crasht `get_by_id()` mit TypeError
3. Interview bleibt in `pending` Zustand ohne laufenden Task
4. Retry-Endpoint lehnt `pending` mit 409 ab
5. UI cached den alten `failed` Status → User ist verwirrt

## Backend-Log

```
POST /api/projects/{id}/clustering/recluster HTTP/1.1" 200 OK
Full re-cluster failed: ProjectRepository.get_by_id() missing 1 required positional argument: 'user_id'
POST /api/projects/{id}/interviews/{id}/retry HTTP/1.1" 409 Conflict  (3x)
```

## Erwartetes Verhalten

- Retry bei `failed` Interview → 200 OK, Status wird auf `pending` gesetzt, Task startet
- Stale Status im UI → wird nach Retry aktualisiert

## Tatsächliches Verhalten

- Retry → 409 (weil Status nach fehlerhaftem Recluster auf `pending` hängt)
- User kann Interview nicht neu starten

## Abhängigkeit

Wird durch Fix von `BUG-clustering-service-missing-user-id.md` gelöst.
Zusätzlich sollte der Retry-Endpoint auch `pending` (ohne laufenden Task) akzeptieren,
oder das UI regelmäßig den Status vom Backend abrufen (kein Stale-State).

## Nächste Schritte

1. [ ] Zuerst Bug #3 fixen (user_id in ClusteringService)
2. [ ] Nach Fix: Retry bei einem "wirklich failed" Interview testen
3. [ ] Optional: Retry-Endpoint auch für `pending` ohne laufenden Task erlauben

# Bug: Recalculate ohne visuelles Feedback (kein ProgressIndicator)

**Entdeckt:** 2026-03-01
**Status:** ✅ Gefixt
**Priority:** 🟡 Mittel
**Location:** `backend/app/clustering/service.py:full_recluster()`

---

## Problembeschreibung

Wenn der User "Recalculate" klickt, läuft `full_recluster` im Hintergrund — manchmal mehrere Minuten. Die UI zeigt dabei **keinerlei Feedback**: kein Spinner, kein ProgressIndicator, keine Statusmeldung.

## Reproduktion

1. Projekt mit mehreren Interviews öffnen
2. "Recalculate" Button klicken
3. → UI friert nicht, aber zeigt auch nichts an (kein ProgressIndicator)
4. Nach Minuten erscheinen die neuen Cluster

## Root Cause

`full_recluster` sendet nur:
- `clustering_started` (vor dem Graph-Invoke)
- `clustering_completed` (nach allem)

**Kein** `clustering_progress` Event dazwischen.

Der Frontend `ProgressIndicator` rendert nur wenn `isProcessing && progress !== null`. `isProcessing` wird via `clustering_started` auf `true` gesetzt, aber `progress` bleibt `null` da kein `clustering_progress` Event kommt.

Vergleich: `process_interview` schickt korrekt 3 Progress-Events (extracting, assigning, summarizing).

## Fix

Zwei `clustering_progress` Events in `full_recluster` eingefügt:

1. **Vor** dem Graph-Invoke: `step: "assigning", completed: 0, total: len(facts)` → macht `progress` non-null → ProgressIndicator erscheint
2. **Nach** dem Graph-Invoke (vor persist): `step: "summarizing", completed: 0, total: new_clusters_count`

```python
# SSE: clustering_progress (assigning step) -- zeigt ProgressIndicator im Frontend
await self._event_bus.publish(
    project_id=project_id,
    event_type="clustering_progress",
    data={"step": "assigning", "completed": 0, "total": len(facts)},
)

graph_output = await self._graph.invoke(initial_state)

# SSE: clustering_progress (summarizing step)
new_clusters_count = len(graph_output.get("new_clusters", []))
await self._event_bus.publish(
    project_id=project_id,
    event_type="clustering_progress",
    data={"step": "summarizing", "completed": 0, "total": new_clusters_count},
)
```

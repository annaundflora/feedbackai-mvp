# Bug: LLM gibt Cluster-Name statt UUID als cluster_id zurück → DB-Fehler

**Entdeckt:** 2026-03-01
**Status:** ✅ Gefixt
**Priority:** 🔴 Kritisch
**Location:** `backend/app/clustering/service.py:502-518` + `graph.py:144-156` + `prompts.py:67`

---

## Problembeschreibung

Beim Full-Recluster gibt das LLM im `assign_facts`-Node `cluster_id = "Lack of Post-Bid Feedback"` zurück (Cluster-Name statt UUID). Der Code verwendet diesen String direkt in `UPDATE facts SET cluster_id = $1` → DB-Fehler.

## Backend-Fehler

```
Full re-cluster failed for project 36d19cd5-...:
invalid input for query argument $1: 'Lack of Post-Bid Feedback'
(invalid UUID: length must be between 32..36 characters, got 25)
[SQL: UPDATE facts SET cluster_id = $1 WHERE id = $2]
[parameters: ('Lack of Post-Bid Feedback', '50f61b78-...')]
```

## Root Cause

1. `generate_taxonomy` erstellt Cluster mit `id=None`
2. `_format_clusters_text()` formatierte `[None] Lack of Post-Bid Feedback` im Prompt
3. LLM sah `[None]` als nicht-UUID und gab den Cluster-Namen als `cluster_id` zurück
4. `_persist_results()` prüfte nur `cluster_id is None` → Name wurde direkt in DB geschrieben

## Fix

1. `_format_clusters_text()`: Cluster ohne UUID werden jetzt als `[NEW] ClusterName` formatiert
2. `ASSIGN_FACTS_PROMPT`: Explizite Anweisung — `[id:UUID]` → UUID als cluster_id, `[NEW]` → null + new_cluster_name
3. `_persist_results()`: Defensiver Fallback — wenn cluster_id keine valide UUID ist, über `name_to_cluster_id` auflösen

## Nächste Schritte

- [x] `_format_clusters_text()` gefixt (graph.py)
- [x] `ASSIGN_FACTS_PROMPT` aktualisiert (prompts.py)
- [x] `_persist_results()` UUID-Validierung + Fallback (service.py)

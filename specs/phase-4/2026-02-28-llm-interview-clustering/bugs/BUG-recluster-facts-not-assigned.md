# Bug: Recalculate erstellt Cluster aber keine Facts assigned

**Entdeckt:** 2026-03-01
**Status:** ✅ Gefixt
**Priority:** 🔴 Hoch
**Location:** `backend/app/clustering/service.py:_persist_results()`

---

## Problembeschreibung

Nach einem `full_recluster` werden Cluster in der DB erstellt, aber **keine Facts** werden den Clustern zugewiesen. Die Cluster erscheinen leer (0 Facts, 0 Interviews).

## Reproduktion

1. Projekt mit bestehenden Interviews und Clustern öffnen
2. "Recalculate" klicken → warten bis fertig
3. → Neue Cluster sichtbar, aber alle leer (fact_count = 0)

## Root Cause

Das LLM halluziniert gelegentlich **Integer-IDs** statt UUIDs als `fact_id` in den `assignments`:

```
assignments:
  - fact_id: "253"           # ← kein UUID!
    cluster_id: null
    new_cluster_name: "Pain Points & Barriers"
  - fact_id: "369"           # ← kein UUID!
    cluster_id: null
    new_cluster_name: "Workarounds"
```

`update_cluster_assignments` führt `UPDATE facts SET cluster_id = ... WHERE id = '253'` aus. PostgreSQL wirft daraufhin `invalid input syntax for type uuid: "253"` — was den gesamten Session-Commit abbricht.

**Timing:** `create_clusters` (Schritt 1) läuft erfolgreich BEVOR der Fehler auftritt. Daher: Cluster werden erstellt, aber Facts bleiben unzugewiesen.

## LangSmith Evidence

LangSmith Trace zeigt `quality_ok: false, iteration: 1` (Korrektur-Loop aktiv), bei dem das LLM Integer-IDs für Facts halluziniert.

## Fix

UUID-Validierung der `fact_id` vor der Verarbeitung in `_persist_results`:

```python
# LLM halluziniert manchmal Integer-IDs ("253", "369") statt UUIDs
# Solche ungueltige fact_ids wuerden einen PostgreSQL-Fehler verursachen
try:
    _uuid.UUID(str(fact_id))
except (ValueError, AttributeError):
    logger.warning(f"Skipping assignment with non-UUID fact_id: {fact_id!r}")
    continue
```

Ungültige `fact_ids` werden übersprungen (geloggt), der Rest der Assignments wird normal verarbeitet.

## Nächste Schritte

- [ ] LLM-Prompt für den Correction-Agent anpassen, um Integer-IDs zu verhindern (Prompt Engineering)
- [ ] Test: `_persist_results` mit gemischten valid/invalid fact_ids

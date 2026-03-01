# Feature: Cluster Quality Classification & Suggestion Auto-Execute

**Epic:** Phase 4 - LLM Interview Clustering
**Status:** Ready
**Wireframes:** --

---

## Problem & Solution

**Problem:**
- 4/13 Cluster haben nur 1 Fact aus 1 Interview -- keine echte Cross-Interview-Validierung
- 6/13 Cluster basieren auf nur 1 Interview -- Einzelbeobachtungen statt validierte Patterns
- Accepted Merge-Suggestions (3 Stk) werden nicht ausgefuehrt -- Accept setzt nur DB-Status, kein Merge

**Solution:**
- 2-Achsen-Klassifikation: Status (emerging/confirmed) + Prioritaet (critical/high/medium/low)
- Dynamisch berechnet aus `interview_count` relativ zu Total-Interviews
- Accept-Suggestion fuehrt Merge/Split direkt aus via bestehender TaxonomyService-Logik

**Business Value:**
- Researcher sieht sofort welche Themen validiert vs. anekdotisch sind
- Prioritaet zeigt Schwere/Verbreitung eines Themas
- 1-Click Suggestion-Handling statt manueller Merge nach Accept

---

## Scope & Boundaries

| In Scope |
|----------|
| Cluster-Status (emerging/confirmed) dynamisch berechnet |
| Cluster-Prioritaet (critical/high/medium/low) dynamisch berechnet |
| Thresholds pro Projekt konfigurierbar (projects-Tabelle) |
| API-Response erweitert: ClusterResponse bekommt `status` + `priority` Felder |
| Accept-Suggestion fuehrt Merge/Split automatisch aus |
| Error-Handling: Suggestion wird auto-dismissed bei Fehler (404/409) |

| Out of Scope |
|--------------|
| Frontend/Dashboard UI-Aenderungen (separates Feature) |
| Prompt-Optimierung fuer bessere Cluster-Qualitaet |
| Neues DB-Feld fuer Status/Prioritaet (dynamisch berechnet) |
| Filter/Sort nach Status oder Prioritaet im API (spaeter) |

---

## Current State Reference

- ClusterResponse Schema existiert (`backend/app/clustering/schemas.py`)
- TaxonomyService.merge() existiert und funktioniert (`backend/app/clustering/taxonomy_service.py`)
- TaxonomyService.execute_split() existiert und funktioniert
- Accept-Endpoint setzt nur Status (`router.py:843-861`)
- `clusters.fact_count` und `clusters.interview_count` sind denormalisiert und aktuell
- `project_interviews`-Tabelle trackt alle zugewiesenen Interviews pro Projekt

---

## User Flow

### Flow 1: Cluster-Liste mit Status + Prioritaet

1. User ruft `GET /api/projects/{id}/clusters` auf
2. API berechnet pro Cluster: Status + Prioritaet
3. Response enthaelt `status: "emerging" | "confirmed"` und `priority: "critical" | "high" | "medium" | "low"`

### Flow 2: Suggestion Accept mit Auto-Execute

1. User ruft `POST /api/projects/{id}/suggestions/{sid}/accept` auf
2. API liest Suggestion (type, source_cluster_id, target_cluster_id)
3. Bei type="merge": API ruft TaxonomyService.merge(source_id, target_id) auf
4. Bei type="split": API ruft TaxonomyService.execute_split() auf mit proposed_data
5. Suggestion-Status wird auf "accepted" gesetzt
6. Response enthaelt Merge/Split-Ergebnis

**Error Paths:**
- Cluster wurde zwischenzeitlich geloescht -> 404 + Suggestion auto-dismissed
- Merge-Conflict (source==target) -> 400 + Suggestion auto-dismissed
- Split-Validation-Error -> 400 + Suggestion auto-dismissed

---

## Business Rules

### Status-Klassifikation

- `emerging`: Cluster hat Facts aus < N verschiedenen Interviews (Einzelbeobachtung)
- `confirmed`: Cluster hat Facts aus >= N verschiedenen Interviews (validiertes Pattern)
- N = `cluster_confirmed_threshold` (Default: 2, pro Projekt konfigurierbar)

### Prioritaet-Klassifikation

- Berechnet als: `interview_count / total_project_interviews * 100`
- Thresholds (pro Projekt konfigurierbar):

| Interview-Anteil | Prioritaet | Bedeutung |
|-----------------|-----------|-----------|
| >= `priority_critical_pct` (Default: 50%) | `critical` | Mehr als Haelfte betroffen |
| >= `priority_high_pct` (Default: 25%) | `high` | Jeder Vierte betroffen |
| >= `priority_medium_pct` (Default: 10%) | `medium` | Signifikantes Muster |
| < `priority_medium_pct` | `low` | Vereinzelt |

### Auto-Execute Rules

- Merge: Source-Facts werden zu Target verschoben, Source-Cluster geloescht
- Split: Nur wenn proposed_data vorhanden (type="split" Suggestions haben subclusters in proposed_data)
- Bei jedem Fehler: Suggestion-Status -> "dismissed", Error-Response an Client

---

## Data

### Neue Felder: projects-Tabelle

| Field | Required | Validation | Default | Notes |
|-------|----------|------------|---------|-------|
| `cluster_confirmed_threshold` | No | Integer >= 2 | 2 | Min. Interviews fuer "confirmed" |
| `priority_critical_pct` | No | Float 0.0-1.0 | 0.5 | >= 50% -> critical |
| `priority_high_pct` | No | Float 0.0-1.0 | 0.25 | >= 25% -> high |
| `priority_medium_pct` | No | Float 0.0-1.0 | 0.1 | >= 10% -> medium |

### Erweiterte Response-Felder: ClusterResponse

| Field | Type | Notes |
|-------|------|-------|
| `status` | `"emerging" \| "confirmed"` | Dynamisch berechnet |
| `priority` | `"critical" \| "high" \| "medium" \| "low"` | Dynamisch berechnet |

### Accept-Response (Merge)

| Field | Type | Notes |
|-------|------|-------|
| `status` | `"accepted"` | Suggestion-Status |
| `merged_cluster` | ClusterResponse | Ergebnis des Merge |
| `undo_id` | string | 30-Sekunden Undo-Fenster |

### Accept-Response (Split)

| Field | Type | Notes |
|-------|------|-------|
| `status` | `"accepted"` | Suggestion-Status |
| `new_clusters` | list[ClusterResponse] | Neue Sub-Cluster |

---

## Implementation Slices

### Dependencies

```
Slice 1 -> Slice 2
Slice 1 -> Slice 3
```

### Slices

| # | Name | Scope | Testability | Dependencies |
|---|------|-------|-------------|--------------|
| 1 | DB Migration + Project Settings | Migration: 4 neue Felder auf projects. ProjectService/Schema erweitern. | Unit-Test: CRUD mit neuen Feldern | -- |
| 2 | Cluster Status + Priority Berechnung | Berechnungslogik + ClusterResponse erweitern + API-Integration | Unit-Test: Berechnung mit verschiedenen Datensaetzen. Integration: GET /clusters gibt status+priority zurueck | Slice 1 |
| 3 | Suggestion Auto-Execute | Accept-Endpoint ruft TaxonomyService.merge/split auf. Error-Handling mit auto-dismiss. | Integration-Test: Accept -> Merge ausgefuehrt. Accept mit geloeschtem Cluster -> 404 + dismissed | Slice 1 |

### Recommended Order

1. **Slice 1:** DB Migration + Project Settings -- Basis fuer beide Features
2. **Slice 2:** Cluster Status + Priority -- Wertvollstes Feature, gibt sofort bessere Uebersicht
3. **Slice 3:** Suggestion Auto-Execute -- Convenience-Feature, nutzt bestehende Merge/Split-Logik

---

## Context & Research

### Codebase Analysis (2026-03-01)

| Area | Finding |
|------|---------|
| DB: 103 Interviews, 10 zugewiesen, 48 Facts, 13 Cluster | 4 Cluster mit 1 Fact/1 Interview |
| Clustering Pipeline | Alle 10 Interviews: clustering_status=failed (Bug, gefixt) |
| Merge Suggestions | 3 accepted, nicht ausgefuehrt -- by design (Frontend muss separaten Merge-Call machen) |
| Accept-Endpoint | `router.py:843-861` -- setzt nur Status, kein Auto-Execute |
| TaxonomyService.merge | Funktioniert: verschiebt Facts, loescht Source, generiert Summary |
| ClusterRepository.update_counts_from_db | Berechnet fact_count + interview_count via SQL COUNT |
| project_interviews.interview_id | Referenziert mvp_interviews.session_id (nicht .id) -- kein FK-Constraint |

---

## Q&A Log

| # | Question | Answer |
|---|----------|--------|
| 1 | Wie sollen 1-Fact-Cluster behandelt werden? Optionen: Minimum-Threshold (loeschen), Soft-Label "Emerging Themes", Prompt-Optimierung | Soft-Label "Emerging Themes" -- Cluster bleiben erhalten, werden aber als emerging markiert |
| 2 | Wie soll Accept Suggestion funktionieren? 2-Step (Accept + manueller Merge) vs Auto-Execute | Auto-Execute bei Accept -- 1-Click Loesung, ruft TaxonomyService.merge/split direkt auf |
| 3 | Ab wann ist ein Cluster "confirmed"? Optionen: >=2 Facts UND >=2 Interviews, >=2 Facts, >=3 Facts UND >=2 Interviews | Mindestens 2 Interviews (Interview-Count basiert, nicht Fact-Count). Plus relatives Prioritaets-Modell fuer Schwere-Einschaetzung |
| 4 | 2-Achsen-Modell (Status + Prioritaet) oder nur Status? | 2-Achsen: Status (emerging/confirmed absolut) + Prioritaet (critical/high/medium/low relativ) |
| 5 | Thresholds global in Settings oder pro Projekt? | Pro Projekt konfigurierbar (projects-Tabelle). Auch der Emerging/Confirmed Threshold |
| 6 | Error-Handling bei Auto-Execute Merge wenn Cluster geloescht? Suggestion pending lassen vs dismissed? | Suggestion auf "dismissed" setzen + Error-Response (404/409) |

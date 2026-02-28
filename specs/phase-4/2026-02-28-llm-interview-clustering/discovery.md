# Feature: LLM Interview Clustering

**Epic:** Insights Pipeline (Dashboard + Clustering)
**Status:** Draft
**Research:** `research-llm-clustering.md` (detaillierte Quellen + Code-Patterns)

---

## Problem & Solution

**Problem:**
- Interviews werden gefuehrt, Summaries generiert — aber es gibt keine Moeglichkeit, Muster ueber mehrere Interviews hinweg zu erkennen
- Bei 100+ Interviews pro Projekt ist manuelle Auswertung nicht skalierbar
- Ohne Clustering kein geschlossener Feedback-to-Decision Loop (Vision: "Dashboard das Muster sichtbar macht")

**Solution:**
- LLM-basierte Clustering-Pipeline die automatisch nach jedem abgeschlossenen Interview Facts extrahiert und thematisch clustert
- Agentic Self-Correction Pattern (LangGraph) fuer Qualitaetssicherung der Cluster
- Projekt-basiertes Scoping: Jedes Projekt hat eigenes Research-Ziel, Prompt-Kontext und eigene Taxonomie
- Dashboard mit Card-basierter Cluster-Uebersicht, Drill-Down zu Facts und Original-Zitaten

**Business Value:**
- Schliesst den Feedback-to-Decision Loop: Interviews fuehren → Muster erkennen → Entscheidungen treffen
- Skaliert von 1 auf 100+ Interviews pro Projekt ohne manuellen Aufwand
- Keine teuren Vektordatenbanken oder HDBSCAN noetig — pure LLM-Intelligenz

---

## Scope & Boundaries

| In Scope |
|----------|
| Projekt-Management: CRUD fuer Projekte mit Research-Ziel + Prompt-Kontext |
| Interview-Zuordnung zu Projekten (manuell oder via Widget-Config) |
| Fact Extraction Pipeline: Atomare Facts aus Summaries ODER Transcripts (konfigurierbar) |
| LLM-basiertes Clustering: TNT-LLM-inspirierte 2-Phasen Taxonomie-Generierung + Zuweisung |
| Agentic Self-Correction: LangGraph-Loop mit Validierung der Cluster-Qualitaet |
| Automatisches Clustering nach jedem abgeschlossenen Interview |
| Automatische Summary-Regenerierung nach Taxonomy-Aenderungen (Merge/Split) |
| Dashboard: Card-basierte Cluster-Uebersicht mit Zaehlern |
| Dashboard: Cluster-Zusammenfassungen (LLM-generiert) |
| Dashboard: Drill-Down zu Facts pro Cluster mit Quell-Interview |
| Dashboard: Zitate/Belege aus Original-Transcripts |
| Dashboard: Taxonomy bearbeiten (Cluster umbenennen, mergen, splitten) |
| Live-Updates im Dashboard via SSE |
| JWT Auth fuer Dashboard-Zugang (Email/Passwort, python-jose + passlib) |
| Dashboard als neuer `dashboard/` Ordner im bestehenden Repo |

| In Scope (neu: Research-Ergebnisse) |
|--------------------------------------|
| OpenRouter-Integration: User konfiguriert Model-Slug pro Aufgabe (Interviewer, Extraction, Clustering) |
| Inkrementelles Clustering: Neues Interview → Facts zuordnen, NICHT alles neu clustern |
| LLM-gesteuerte Merge/Split-Vorschlaege nach inkrementellem Clustering (User-Approval) |
| Manueller "Neu berechnen" Button fuer Full Re-Cluster |
| Volle Cluster-Kontrolle: User kann Cluster umbenennen, mergen, splitten |
| API Endpoint fuer Export (REST, fuer Integration in Jira, Notion, etc.) |

| Out of Scope |
|--------------|
| Cross-Projekt Clustering (uebergreifende Analyse) |
| Vektordatenbanken / Embeddings / HDBSCAN |
| Voice-Transkription |
| Email-Einladungen |
| CSV/PDF Export (nur API Endpoint in V1) |
| Nutzer-Rollen / Team-Management |
| Session Recordings / Clarity Integration |
| Hierarchisches Clustering (Themen > Sub-Themen) — flach fuer MVP |

---

## Current State Reference

> Existing functionality that will be reused (unchanged).

- `InterviewService.end()` generiert Summary + Transcript und speichert in `mvp_interviews` — **Hook-Point fuer Clustering-Trigger**
- `SummaryService` generiert Bullet-Listen aus Transcripts via OpenRouter LLM — Summary-Format ist Clustering-Input
- `InterviewRepository` CRUD fuer `mvp_interviews` Tabelle — Transcript (JSONB) + Summary (TEXT) als Datenquelle
- `InterviewGraph` LangGraph StateGraph mit MemorySaver + SSE-Streaming — Pattern wird fuer Clustering-Graph wiederverwendet
- SSE-Streaming Pattern (`sse_starlette`) fuer Real-Time Delivery — wird fuer Dashboard Live-Updates wiederverwendet
- OpenRouter als LLM-Gateway — wird fuer Clustering-LLM-Calls wiederverwendet
- PostgreSQL/SQLAlchemy async als Datenbank — wird um neue Tabellen erweitert

---

## UI Patterns

### Reused Patterns

| Pattern Type | Component | Usage in this Feature |
|--------------|-----------|----------------------|
| SSE Event Streaming | `sse_starlette` (Backend) | Live-Updates fuer Dashboard (neue Cluster, Fortschritt) |
| LangGraph StateGraph | `InterviewGraph` Pattern | Clustering-Agent Graph mit Self-Correction Loop |

### New Patterns

| Pattern Type | Description | Rationale |
|--------------|-------------|-----------|
| Dashboard SPA | Next.js / React Single-Page App im `dashboard/` Ordner | Separater Client fuer Admin/Researcher, Widget ist Enduser-facing |
| Card Grid | Card-basierte Cluster-Uebersicht mit Badge-Zaehlern | Standard-Pattern fuer Ueberblick mit Drill-Down |
| Drill-Down Panel | Seitliches Panel oder Detail-Seite fuer Facts + Zitate | Zwei-Ebenen-Navigation: Cluster → Facts → Zitate |
| Inline Taxonomy Editor | Cluster umbenennen, mergen, splitten direkt in der Uebersicht | Schnelle Iteration ohne separate Seite |
| Progress Indicator | "Analyse laeuft... 47/52 Interviews" mit Live-Counter | Feedback bei langen Clustering-Laeufen (100+ Interviews) |

---

## User Flow

### Flow 1: Projekt anlegen

1. User oeffnet Dashboard → sieht Projekt-Liste (leer oder mit bestehenden Projekten)
2. User klickt "Neues Projekt" → Formular erscheint
3. User gibt ein: Projektname, Research-Ziel (Freitext), Prompt-Kontext fuer Interviewer (Freitext), Fact-Extraction-Quelle (Summary oder Transcript)
4. System erstellt Projekt → Projekt erscheint in der Liste
5. User sieht leeres Projekt-Dashboard ("Noch keine Interviews zugeordnet")

### Flow 2: Interviews zuordnen

1. User oeffnet Projekt → Tab "Interviews"
2. User sieht Liste der nicht-zugeordneten Interviews (aus `mvp_interviews`)
3. User waehlt Interviews aus → klickt "Zuordnen"
4. System ordnet Interviews dem Projekt zu
5. **Automatisch:** Clustering-Pipeline startet fuer jedes zugeordnete Interview

**Alternative:** Interview wird automatisch zugeordnet wenn Widget mit `project_id` konfiguriert ist.

### Flow 3: Inkrementelles Clustering (nach Interview-Ende)

1. Interview wird abgeschlossen → `InterviewService.end()` speichert Summary + Transcript
2. **Trigger:** System erkennt neues abgeschlossenes Interview im Projekt
3. **Phase 1 — Fact Extraction:** LLM (model_extraction) extrahiert atomare Facts aus Summary (oder Transcript)
4. **Phase 2 — Inkrementelle Zuweisung:** LLM (model_clustering) ordnet neue Facts bestehenden Clustern zu, unter Beruecksichtigung von research_goal. Falls kein Cluster passt → neuer Cluster vorgeschlagen
5. **Phase 3 — Self-Correction:** LLM validiert: Sind die Zuordnungen sinnvoll? Cluster-Qualitaet OK? Max 3 Loops
6. **Phase 4 — Merge/Split Check:** Bei neuem Cluster: Aehnlichkeits-Check. Bei grossem Cluster: Sub-Themen-Check → Suggestions generieren
7. **Phase 5 — Zusammenfassung:** LLM (model_summary) generiert/aktualisiert Cluster-Zusammenfassungen
8. Dashboard aktualisiert sich live (SSE): Neue Facts, Zaehler, ggf. Merge/Split-Suggestions

### Flow 3b: Full Re-Cluster (manuell)

1. User klickt "Neu berechnen" im Insights-Tab
2. System zeigt Warnung: "Alle bestehenden Zuordnungen werden zurueckgesetzt"
3. User bestaetigt → alle Cluster-Zuordnungen werden geloescht (Facts bleiben erhalten)
4. Komplette TNT-LLM Pipeline: Alle Facts → Mini-Batches → Taxonomie generieren → Zuweisen → Self-Correction → Summaries
5. Dashboard zeigt Progress: "Analysiere... 47/52 Facts"
6. Ergebnis: Komplett neue Cluster-Struktur

### Flow 4: Cluster-Dashboard ansehen

1. User oeffnet Projekt → Tab "Insights" (Standard-Tab)
2. User sieht Card-Grid: Jede Card = ein Cluster mit Name, Fact-Anzahl, Interview-Anzahl, Zusammenfassung (Vorschau)
3. User klickt auf Cluster-Card → Drill-Down oeffnet sich
4. User sieht: Vollstaendige Zusammenfassung, Liste aller Facts (mit Quell-Interview), Relevante Zitate aus Transcripts
5. User kann zurueck zur Uebersicht navigieren

### Flow 5: Taxonomy bearbeiten

1. User klickt auf Cluster-Card → Kontextmenue: "Umbenennen", "Mergen mit...", "Splitten"
2. **Umbenennen:** User gibt neuen Namen ein → System speichert
3. **Mergen:** User waehlt zweiten Cluster → System kombiniert Facts → Cluster-Summary wird automatisch regeneriert
4. **Splitten (2-Schritt-Verfahren):** User klickt "Split" → LLM generiert Preview der vorgeschlagenen Sub-Cluster (Name, Fact-Anzahl, komplette Fact-Auflistung pro Sub-Cluster) → User prueft Preview und bestaetigt oder bricht ab → Bei Bestaetigung: Facts werden aufgeteilt, Cluster-Summaries werden automatisch generiert
5. Nach jeder Aenderung: Automatische Summary-Regenerierung der betroffenen Cluster (kein Re-Clustering der Facts)

**Error Paths:**
- LLM-Timeout bei Fact Extraction → Retry (max 3x), danach Status "extraction_failed" fuer dieses Interview
- LLM-Timeout bei Clustering → Retry (max 3x), danach Status "clustering_failed", Facts bleiben "unassigned"
- Keine Interviews im Projekt → Dashboard zeigt Empty State
- Alle Facts einem Cluster zugeordnet → Warnung: "Taxonomie moeglicherweise zu grob"

---

## UI Layout & Context

### Screen: Projekt-Liste

**Position:** Dashboard Hauptseite (`/projects`)
**When:** Nach Login

**Layout:**
- Header: App-Name "FeedbackAI Insights" + User-Avatar/Logout
- Toolbar: "Neues Projekt" Button
- Grid: Projekt-Cards (Name, Interview-Anzahl, Cluster-Anzahl, letztes Update als relative Zeitangabe z.B. "Updated 2h ago")
- Empty State: Illustration + "Erstes Projekt anlegen" CTA

### Screen: Projekt-Dashboard (Insights Tab)

**Position:** Projekt-Detail (`/projects/{id}`)
**When:** User oeffnet ein Projekt

**Layout:**
- Header: Projekt-Name, Research-Ziel (Subtitle), Tabs: "Insights" | "Interviews" | "Einstellungen"
- Status-Bar: "N Interviews | M Facts | K Cluster" + optional Progress-Indicator
- Back-Navigation: "< Projects" Pfeil im Header auf allen Projekt-Detail-Screens
- Card-Grid: Cluster-Cards in 2-Spalten Grid (responsive, single-column auf mobil), sortiert nach Fact-Anzahl (absteigend)
  - Jede Card: Cluster-Name, Fact-Anzahl Badge, Interview-Anzahl Badge, Zusammenfassung (2-3 Zeilen Vorschau), Kontextmenue-Icon
- Unassigned-Bereich: Facts ohne Cluster (falls vorhanden)

### Screen: Cluster-Detail (Drill-Down)

**Position:** Slide-Over Panel oder Unterseite (`/projects/{id}/clusters/{cluster_id}`)
**When:** User klickt auf Cluster-Card

**Layout:**
- Header: Cluster-Name (editierbar), "Zurueck" Button, Aktionen (Mergen, Splitten)
- Zusammenfassung: Vollstaendiger LLM-generierter Text
- Facts-Liste: Sequentiell nummerierte atomare Facts (1, 2, 3...), jeweils mit:
  - Fact-Text
  - Quell-Interview (Link/Badge: "Interview #7")
  - Confidence-Score (optional)
- Zitate-Bereich: Relevante Originalzitate aus Transcripts, jeweils mit Interview-Referenz

### Screen: Projekt-Interviews Tab

**Position:** Projekt-Detail → Tab "Interviews"
**When:** User wechselt zum Interviews-Tab

**Layout:**
- Toolbar: "Interviews zuordnen" Button, Filter (Status, Datum)
- Interview-Zuordnung via Modal-Overlay mit Checkbox-Liste (ID, Datum, Summary-Vorschau). Multi-Select + "Zuordnen" Button
- Tabelle: Interview-Liste (ID, Datum, Summary-Vorschau, Facts-Anzahl, Clustering-Status)
- Status-Badges: "analysiert", "ausstehend", "fehlgeschlagen"

### Screen: Projekt-Einstellungen Tab

**Position:** Projekt-Detail → Tab "Einstellungen"
**When:** User wechselt zum Einstellungen-Tab

**Layout:**
- Formular: Projektname, Research-Ziel, Prompt-Kontext (Textarea), Fact-Extraction-Quelle (Dropdown: Summary/Transcript)
- Zwei separate "Save Changes" Buttons: einer fuer General-Settings, einer fuer Model-Configuration
- Model-Konfiguration (OpenRouter): Model-Slug pro Aufgabe (Interviewer, Fact Extraction, Clustering, Summary)
- Danger Zone: "Projekt loeschen" Button mit Bestaetigung (User muss Projektnamen eintippen)

---

## UI Components & States

| Element | Type | Location | States | Behavior |
|---------|------|----------|--------|----------|
| `project_card` | Card | Projekt-Liste | `default`, `hover`, `loading` | Klick → navigiert zu Projekt-Dashboard |
| `new_project_btn` | Button | Projekt-Liste Toolbar | `default`, `disabled` | Klick → oeffnet Projekt-Formular |
| `project_form` | Form/Modal | Projekt-Liste | `empty`, `filled`, `saving`, `error` | Submit → erstellt Projekt |
| `cluster_card` | Card | Insights Tab | `default`, `hover`, `updating` (Live-Update Animation) | Klick → oeffnet Drill-Down |
| `cluster_context_menu` | Dropdown | Cluster-Card | `closed`, `open` | Optionen: Umbenennen, Mergen, Splitten |
| `taxonomy_editor_rename` | Inline Input | Cluster-Card/Detail | `display`, `editing`, `saving` | Enter → speichert, Escape → abbrechen |
| `merge_dialog` | Modal | Cluster-Card | `closed`, `open`, `merging` | Cluster-Auswahl → Bestaetigung → Merge |
| `split_confirm` | Modal | Cluster-Card | `closed`, `open`, `splitting` | Bestaetigung → LLM-Split → Summary-Regenerierung |
| `fact_item` | List Item | Cluster-Detail | `default`, `highlighted` | Zeigt Fact-Text + Interview-Badge |
| `quote_item` | Blockquote | Cluster-Detail | `default`, `expanded` | Zeigt Originalzitat + Interview-Referenz |
| `progress_bar` | Status Bar | Insights Tab | `hidden`, `active`, `complete` | Zeigt Clustering-Fortschritt bei Batch |
| `interview_assign_btn` | Button | Interviews Tab | `default`, `loading`, `success` | Bulk-Zuordnung von Interviews |
| `interview_table` | Table | Interviews Tab | `empty`, `populated`, `loading` | Sortier- und filterbar |
| `settings_form` | Form | Einstellungen Tab | `pristine`, `dirty`, `saving`, `saved` | Auto-Save oder expliziter Save-Button |
| `live_update_badge` | Badge/Dot | Cluster-Card | `hidden`, `pulse` | Animiert wenn neuer Fact hinzugefuegt |
| `merge_suggestion` | Banner/Card | Insights Tab | `hidden`, `visible`, `accepted`, `dismissed` | LLM schlaegt Merge vor, User akzeptiert oder verwirft |
| `split_suggestion` | Banner/Card | Insights Tab | `hidden`, `visible`, `accepted`, `dismissed` | LLM schlaegt Split vor, User akzeptiert oder verwirft |
| `recluster_btn` | Button | Insights Tab Toolbar | `default`, `loading`, `disabled` | Manueller Full Re-Cluster Trigger |
| `recluster_confirm` | Modal | Insights Tab | `closed`, `open`, `recalculating` | Warnung + Impact-Summary vor Full Re-Cluster |
| `model_config_form` | Form | Einstellungen Tab | `pristine`, `dirty`, `saving` | OpenRouter Model-Slug pro Aufgabe konfigurieren |

---

## Feature State Machine

### States Overview

| State | UI | Available Actions |
|-------|----|--------------------|
| `no_projects` | Leere Projekt-Liste, Empty State mit CTA | Projekt anlegen |
| `project_empty` | Projekt ohne Interviews, Empty State | Interviews zuordnen, Einstellungen bearbeiten |
| `project_collecting` | Interviews zugeordnet, Clustering laeuft | Dashboard ansehen (mit Progress), Interviews zuordnen |
| `project_ready` | Alle Interviews analysiert, Cluster sichtbar | Dashboard ansehen, Drill-Down, Taxonomy bearbeiten |
| `project_updating` | Clustering (neues Interview) oder Summary-Regenerierung (nach Taxonomy-Edit) laeuft | Dashboard ansehen (mit Update-Indicator), Read-Only fuer Taxonomy |
| `cluster_detail` | Drill-Down in einen Cluster | Facts ansehen, Zitate ansehen, Umbenennen, Zurueck |
| `extraction_running` | Facts werden aus einem Interview extrahiert | Warten (Progress im Dashboard) |
| `extraction_failed` | Fact Extraction fehlgeschlagen. Error-Badge am Interview in Interviews-Tab mit Retry-Button. | Retry (Retry-Button in Interview-Zeile), Interview ueberspringen (entfernt Interview aus Pipeline, Facts bleiben erhalten) |
| `clustering_running` | Facts werden Clustern zugeordnet | Warten (Progress im Dashboard) |
| `clustering_failed` | Clustering fehlgeschlagen. Error-Banner im Insights-Tab zeigt Anzahl unzugeordneter Facts + Retry-Option. | Retry (Banner-Button im Insights-Tab), Facts manuell zuordnen |

### Transitions

| Current State | Trigger | UI Feedback | Next State | Business Rules |
|---------------|---------|-------------|------------|----------------|
| `no_projects` | "Neues Projekt" klicken → Formular ausfuellen → Submit | Projekt-Card erscheint in Liste | `project_empty` | Projektname required, Research-Ziel required |
| `project_empty` | Interviews zuordnen | Progress-Bar erscheint | `project_collecting` | Min. 1 Interview zum Zuordnen |
| `project_empty` | Interview abgeschlossen (via Widget mit project_id) | Progress-Bar erscheint | `project_collecting` | Interview muss Summary haben |
| `project_collecting` | Alle Interviews analysiert | Progress-Bar verschwindet, Cluster-Cards erscheinen | `project_ready` | -- |
| `project_collecting` | Neues Interview kommt rein | Zaehler aktualisiert, Progress aktualisiert | `project_collecting` | -- |
| `project_ready` | Cluster-Card klicken | Drill-Down Panel oeffnet sich | `cluster_detail` | -- |
| `project_ready` | Neues Interview kommt rein | Update-Indicator auf betroffenen Cluster-Cards | `project_updating` | -- |
| `project_ready` | Taxonomy bearbeiten (Merge/Split/Rename) | Summary-Regenerierung Progress | `project_updating` | Rename erfordert keine Summary-Regenerierung |
| `project_updating` | Summary-Regenerierung/Clustering abgeschlossen | Cards aktualisieren sich, Update-Indicator verschwindet | `project_ready` | -- |
| `cluster_detail` | "Zurueck" klicken | Drill-Down schliesst | `project_ready` | -- |
| `extraction_running` | Extraction erfolgreich | Facts erscheinen im Cluster | `clustering_running` | -- |
| `extraction_running` | Extraction fehlgeschlagen (3x Retry) | Error-Badge am Interview | `extraction_failed` | Max 3 Retries |
| `extraction_failed` | "Retry" klicken | Progress-Bar | `extraction_running` | -- |
| `clustering_running` | Clustering erfolgreich | Cluster-Cards aktualisieren sich | `project_ready` | -- |
| `clustering_running` | Clustering fehlgeschlagen (3x Retry) | Error-Hinweis, Facts als "unassigned" | `clustering_failed` | Facts bleiben erhalten, nur Zuordnung fehlt |

---

## Business Rules

- Jedes Projekt hat genau ein Research-Ziel und einen Prompt-Kontext
- Fact-Extraction-Quelle (Summary oder Transcript) ist pro Projekt konfigurierbar
- Fact-Extraction-Quelle wird gesperrt sobald erste Facts extrahiert wurden. Aenderung nur ueber "Reset & Change Source" Flow moeglich, der explizit darauf hinweist dass bestehende Facts mit der alten Quelle extrahiert wurden und bei Bedarf ein Full Re-Extract ausgeloest werden kann
- Ein Interview kann nur einem Projekt zugeordnet werden
- Facts werden aus dem Interview-Text extrahiert; ein Interview kann mehrere Facts liefern
- Ein Fact gehoert zu genau einem Cluster (oder "unassigned")
- Cluster-Zusammenfassungen werden automatisch (re-)generiert wenn sich der Cluster-Inhalt aendert
- Cluster-Taxonomie waechst emergent — LLM entscheidet basierend auf Daten, nicht vordefinierte Kategorien
- Bei Merge: Alle Facts des Quell-Clusters wandern zum Ziel-Cluster, Quell-Cluster wird geloescht. Nach erfolgreichem Merge erscheint Undo-Toast ("Clusters merged. [Undo - 30s]") der den Merge innerhalb von 30 Sekunden rueckgaengig machen kann
- Bei Split: LLM teilt Facts des Clusters in 2+ Sub-Cluster auf
- Rename loest KEIN Re-Clustering aus
- Maximale Retry-Anzahl fuer LLM-Calls: 3 (Extraction + Clustering)
- Clustering-Pipeline blockiert nicht die Interview-Ausfuehrung (async, Background-Task)
- Dashboard erfordert JWT Auth (Email/Passwort Login, python-jose + passlib)

### Re-Clustering Strategie (Entscheidung: Hybrid mit Suggestions)

- **Inkrementell (Default):** Neues Interview → Facts extrahieren → gegen bestehende Cluster pruefen → zuordnen ODER neuen Cluster vorschlagen
- **Merge-Vorschlaege:** Nach jedem neuen Cluster prueft LLM Aehnlichkeit zu bestehenden Clustern → Merge-Suggestion im Dashboard (User entscheidet)
- **Split-Vorschlaege:** Wenn Cluster > N Facts (z.B. 8+), prueft LLM auf Sub-Themen → Split-Suggestion im Dashboard (User entscheidet)
- **Full Re-Cluster:** Manueller "Neu berechnen" Button als Fallback. Loescht alle Zuordnungen, fuehrt komplette TNT-LLM Pipeline neu aus
- **Kein automatisches Full Re-Cluster** — nur inkrementell + Suggestions

### LLM Model-Konfiguration (Entscheidung: OpenRouter mit konfigurierbaren Slugs)

- Alle LLM-Calls gehen ueber OpenRouter
- User konfiguriert Model-Slug pro Aufgabe im Projekt-Einstellungen Tab
- Empfohlene Defaults:

| Aufgabe | Default Model-Slug | Begruendung |
|---------|-------------------|-------------|
| Interviewer | `anthropic/claude-sonnet-4` | Empathie, Gespraechsfuehrung |
| Fact Extraction | `anthropic/claude-haiku-4` | Schnell, guenstig, strukturierte Extraktion |
| Clustering / Taxonomy | `anthropic/claude-sonnet-4` | Semantisches Verstaendnis, Goal-Alignment |
| Summary Generation | `anthropic/claude-haiku-4` | Zusammenfassung ist einfacher Task |

### Cluster-Editing (Entscheidung: Volle Kontrolle)

- User kann Cluster umbenennen (inline edit)
- User kann Cluster mergen (zwei auswaehlen → kombinieren)
- User kann Cluster splitten (LLM teilt in Sub-Cluster)
- User kann Facts zwischen Clustern verschieben (Kontextmenue pro Fact mit "Move to [Cluster]..." und "Mark as unassigned", Checkbox-Selektion fuer Bulk Move)
- Alle manuellen Aenderungen sind persistent

---

## Data

### Projekt

| Field | Required | Validation | Notes |
|-------|----------|------------|-------|
| `id` | Yes | UUID, auto-generated | Primary Key |
| `name` | Yes | 1-200 Zeichen, nicht leer | Anzeigename |
| `research_goal` | Yes | 1-2000 Zeichen | Freitext, lenkt LLM-Clustering implizit |
| `prompt_context` | No | Max 5000 Zeichen | Optionaler Kontext fuer Interviewer-Agent |
| `extraction_source` | Yes | Enum: "summary", "transcript" | Default: "summary" |
| `model_interviewer` | No | String, OpenRouter Model-Slug | Default: "anthropic/claude-sonnet-4" |
| `model_extraction` | No | String, OpenRouter Model-Slug | Default: "anthropic/claude-haiku-4" |
| `model_clustering` | No | String, OpenRouter Model-Slug | Default: "anthropic/claude-sonnet-4" |
| `model_summary` | No | String, OpenRouter Model-Slug | Default: "anthropic/claude-haiku-4" |
| `created_at` | Yes | Timestamp, auto | -- |
| `updated_at` | Yes | Timestamp, auto | -- |
| `user_id` | Yes | UUID, JWT Auth (aus Token) | Projekt-Ersteller |

### Cluster (Taxonomy)

| Field | Required | Validation | Notes |
|-------|----------|------------|-------|
| `id` | Yes | UUID, auto-generated | Primary Key |
| `project_id` | Yes | FK → Projekt | -- |
| `name` | Yes | 1-200 Zeichen | LLM-generiert oder manuell editiert |
| `summary` | No | Text | LLM-generierte Zusammenfassung |
| `fact_count` | Yes | Integer >= 0 | Denormalisiert fuer schnelle Anzeige |
| `interview_count` | Yes | Integer >= 0 | Denormalisiert: Anzahl unterschiedlicher Quell-Interviews |
| `created_at` | Yes | Timestamp, auto | -- |
| `updated_at` | Yes | Timestamp, auto | -- |

### Fact

| Field | Required | Validation | Notes |
|-------|----------|------------|-------|
| `id` | Yes | UUID, auto-generated | Primary Key |
| `project_id` | Yes | FK → Projekt | -- |
| `interview_id` | Yes | FK → mvp_interviews.session_id | Quell-Interview |
| `cluster_id` | No | FK → Cluster, nullable | Null = "unassigned" |
| `content` | Yes | 1-1000 Zeichen | Atomare Aussage |
| `quote` | No | Text | Relevantes Originalzitat aus Transcript |
| `confidence` | No | Float 0.0-1.0 | LLM-Confidence fuer Cluster-Zuordnung |
| `created_at` | Yes | Timestamp, auto | -- |

### Projekt-Interview-Zuordnung

| Field | Required | Validation | Notes |
|-------|----------|------------|-------|
| `project_id` | Yes | FK → Projekt | -- |
| `interview_id` | Yes | FK → mvp_interviews.session_id | -- |
| `extraction_status` | Yes | Enum: "pending", "running", "completed", "failed" | -- |
| `clustering_status` | Yes | Enum: "pending", "running", "completed", "failed" | -- |
| `assigned_at` | Yes | Timestamp | -- |

---

## Implementation Slices

> Testbare, deploybare Inkremente. Jeder Slice liefert User-Value.

### Dependencies

```
Slice 1 (DB + Projekt CRUD)
   |
Slice 2 (Fact Extraction Pipeline)
   |
Slice 3 (Clustering Pipeline + LangGraph Agent)
   |
   +--→ Slice 4 (Dashboard: Projekt-Liste + Cluster-Uebersicht)
   |
   +--→ Slice 5 (Dashboard: Drill-Down + Zitate)
   |
Slice 6 (Taxonomy-Editing + Re-Clustering)
   |
Slice 7 (Live-Updates via SSE)
   |
Slice 8 (Auth + Polish)
```

### Slices

| # | Name | Scope | Testability | Dependencies |
|---|------|-------|-------------|--------------|
| 1 | DB Schema + Projekt CRUD | Neue Tabellen (projects, clusters, facts, project_interviews), Projekt-API (CRUD) | API-Tests: Projekt erstellen/lesen/updaten/loeschen, Interview zuordnen | -- |
| 2 | Fact Extraction Pipeline | LLM-basierte Fact Extraction aus Summary/Transcript, Speicherung in DB, Trigger nach Interview-Ende | Test: Interview abschliessen → Facts in DB, Facts-Inhalt pruefen | Slice 1 |
| 3 | Clustering Pipeline + Agent | LangGraph Clustering-Agent: Taxonomie generieren, Facts zuordnen, Self-Correction Loop, Cluster-Zusammenfassungen | Test: Facts vorhanden → Cluster entstehen, Zuordnungen sinnvoll, Zusammenfassungen generiert | Slice 2 |
| 4 | Dashboard: Projekt-Liste + Cluster-Uebersicht | Next.js App, Projekt-Liste, Cluster-Card-Grid, Zaehler, Zusammenfassungs-Vorschau | E2E: Dashboard oeffnen → Projekte sehen → Cluster-Cards sehen | Slice 3 |
| 5 | Dashboard: Drill-Down + Zitate | Cluster-Detail mit Facts-Liste, Interview-Referenzen, Original-Zitate aus Transcripts | E2E: Cluster klicken → Facts sehen → Zitate sehen | Slice 4 |
| 6 | Taxonomy-Editing + Summary-Regen | Cluster umbenennen, mergen, splitten; automatische Summary-Regenerierung nach Merge/Split | Test: Cluster mergen → Facts kombiniert, neue Zusammenfassung; Cluster splitten → Sub-Cluster entstehen | Slice 5 |
| 7 | Live-Updates via SSE | Dashboard SSE-Verbindung, Echtzeit-Updates bei neuen Facts/Clustern, Progress-Indicator | Test: Interview abschliessen → Dashboard aktualisiert sich automatisch ohne Reload | Slice 4 |
| 8 | Auth + Polish | JWT Auth Integration (python-jose + passlib), Login-Screen, geschuetzte Routes, Error Handling, Loading States | Test: Unautorisierter Zugriff blockiert, Login funktioniert, Fehler werden angezeigt | Slice 7 |

### Recommended Order

1. **Slice 1:** DB Schema + Projekt CRUD — Fundament fuer alle weiteren Slices
2. **Slice 2:** Fact Extraction Pipeline — Erster sichtbarer Wert: Interview → Facts
3. **Slice 3:** Clustering Pipeline + Agent — Kernlogik: Facts → thematische Cluster
4. **Slice 4:** Dashboard: Cluster-Uebersicht — Erster visueller Zugang zu Insights
5. **Slice 5:** Dashboard: Drill-Down — Tiefe: Facts + Zitate sichtbar
6. **Slice 6:** Taxonomy-Editing — User-Kontrolle ueber Cluster-Struktur
7. **Slice 7:** Live-Updates — Real-Time Experience
8. **Slice 8:** Auth + Polish — Production-Ready

---

## Clustering-Architektur (Konzept)

### Pipeline-Uebersicht

```
Interview abgeschlossen
    |
    v
[1] Fact Extraction (LLM)
    Summary/Transcript → Atomare Facts
    |
    v
[2] Taxonomy Check
    Existierende Cluster vorhanden?
    |-- Nein → [2a] Taxonomy Generation (LLM generiert initiale Cluster)
    |-- Ja  → [2b] Fact Assignment (LLM ordnet Facts zu bestehenden Clustern)
    |           ggf. neue Cluster vorschlagen
    |
    v
[3] Self-Correction (LLM)
    "Sind diese Zuordnungen sinnvoll?"
    "Gibt es Cluster die gemergt/gesplittet werden sollten?"
    |-- Nein → Zurueck zu [2b] mit Korrektur-Hinweis
    |-- Ja  → Weiter
    |
    v
[4] Summary Generation (LLM)
    Cluster-Zusammenfassungen (re-)generieren
    |
    v
[5] Persist + Notify
    Facts + Cluster in DB speichern
    SSE-Event an Dashboard senden
```

### TNT-LLM + GoalEx + Clio Hybrid Ansatz

**Phase 1 — Taxonomie-Generierung (bei neuem Projekt oder wenigen Interviews):**
- LLM liest alle bisherigen Summaries/Facts + research_goal (GoalEx Pattern)
- LLM schlaegt initiale Themen-Taxonomie vor, zielgerichtet auf Research-Frage
- Taxonomie wird gespeichert

**Phase 2 — Inkrementelle Zuweisung (bei jedem neuen Interview):**
- Neue Facts werden extrahiert (Clio Facet-Extraction Pattern)
- LLM sieht bestehende Taxonomie + neue Facts + research_goal
- LLM ordnet zu ODER schlaegt neues Thema vor
- Bei neuem Cluster: LLM prueft Aehnlichkeit zu bestehenden → Merge-Suggestion
- Bei grossem Cluster (>8 Facts): LLM prueft auf Sub-Themen → Split-Suggestion
- Suggestions werden im Dashboard angezeigt, User entscheidet

**Phase 3 — Full Re-Cluster (manuell, on-demand):**
- User klickt "Neu berechnen" Button
- Alle Cluster-Zuordnungen werden geloescht
- Komplette TNT-LLM Pipeline laeuft: Summarize → Batch → Taxonomy → Classify
- Sinnvoll nach vielen manuellen Aenderungen oder Richtungswechsel im Research-Ziel

### LangGraph Agent-Loop (Self-Correction)

```
START → extract_facts → assign_to_clusters → validate_quality
                                                |
                                    +-----------+----------+
                                    |                      |
                              quality_ok            quality_issues
                                    |                      |
                                    v                      v
                            generate_summaries    refine_clusters
                                    |                      |
                                    v                      |
                                  END  <-------------------+
```

- `validate_quality`: LLM prueft Cluster-Kohaerenz, Groessen-Balance, Themen-Ueberlappung
- `refine_clusters`: LLM korrigiert Zuordnungen, schlaegt Merges/Splits vor
- Max 3 Correction-Loops, danach Ergebnis akzeptieren

---

## Context & Research

### Similar Patterns in Codebase

| Feature | Location | Relevant because |
|---------|----------|------------------|
| LangGraph Interview Graph | `backend/app/interview/graph.py` | Gleicher Graph-Pattern fuer Clustering Agent |
| SSE Streaming | `backend/app/api/routes.py` | Gleiches Pattern fuer Dashboard Live-Updates |
| SummaryService | `backend/app/insights/summary.py` | Summary-Format ist Clustering-Input |
| InterviewRepository | `backend/app/interview/repository.py` | Repository-Pattern fuer neue Tabellen |
| OpenRouter LLM Config | `backend/app/config/settings.py` | LLM-Gateway fuer Clustering-Calls |

### Web Research (Deep Dive — Details in `research-llm-clustering.md`)

| Source | Finding | Relevanz |
|--------|---------|----------|
| **TNT-LLM (Microsoft, KDD 2024)** [arXiv](https://arxiv.org/abs/2403.12173) | 2-Phasen-Framework: LLM summarisiert → generiert Taxonomie iterativ → klassifiziert. Tiered LLM (GPT-4 fuer Taxonomy, GPT-3.5 fuer Summary). Offizielles [LangGraph Tutorial](https://github.com/langchain-ai/langgraph/blob/main/docs/docs/tutorials/tnt-llm/tnt-llm.ipynb) mit StateGraph Code. | HOCH — Direktes Vorbild fuer unsere Pipeline |
| **"Text Clustering as Classification" (SIGIR-AP 2025)** [arXiv](https://arxiv.org/html/2410.00927v1) | Reframed Clustering als Classification: LLM generiert Labels in Mini-Batches → merged aehnliche Labels → klassifiziert jeden Text. JSON-Output. +12% vs. Embedding-basiert. [Code](https://github.com/ECNU-Text-Computing/Text-Clustering-via-LLM). | HOCH — Einfachster Ansatz, passt zu unserem Fact-Assignment |
| **GoalEx (EMNLP 2023)** [arXiv](https://arxiv.org/abs/2305.13749) | Goal-Driven Clustering: User gibt Ziel vor ("Cluster by reason for dissatisfaction"), LLM clustert zielgerichtet. Propose-Assign-Select Pattern. [Code](https://github.com/ZihanWangKi/GoalEx). | HOCH — Unser `research_goal` ist exakt dieses Pattern |
| **Anthropic Clio (Dez 2024)** [Paper](https://www.anthropic.com/research/clio) | 4-Stufen: Facet Extraction → Semantic Clustering → Cluster Description → Hierarchy. Claude macht alles. 94% Accuracy bei 20k Conversations. [OpenClio](https://github.com/Phylliida/OpenClio). | SEHR HOCH — Produktions-Beweis bei Millionen Conversations |
| **Anthropic Interviewer (Dez 2025)** | Claude-powered Qualitative-Research-Tool. Plant Fragen, fuehrt 10-15 Min Gespraeche, clustert Themen fuer Analysten. 1.250 Professionals interviewt. | SEHR HOCH — Validiert Interview→Clustering Workflow |
| **k-LLMmeans (2025)** [arXiv](https://arxiv.org/abs/2502.09667) | Summary-als-Zentroid + Mini-Batch fuer Streaming. 205k Posts mit nur 3.850 LLM-Calls. LLM-Kosten skalieren NICHT mit Dataset-Groesse. | MITTEL — Bestaetigt inkrementelles Clustering Pattern |
| **Few-Shot Clustering (MIT Press)** [Paper](https://direct.mit.edu/tacl/article/doi/10.1162/tacl_a_00648/120476) | 3 Integrations-Ebenen: Pre-Clustering (Input anreichern), During (Pairwise Oracle), Post (Self-Correction). | MITTEL — Unser Self-Correction Loop = Post-Clustering Pattern |
| **Chris Ellis Blog** [Blog](https://www.chrisellis.dev/articles/comparing-llm-based-vs-traditional-clustering-for-support-conversations) | LLM-basierte Clustering uebertrifft klassische Algorithmen bei semantischer Kohaerenz. Trade-Off: Skalierbarkeit vs. Qualitaet. | KONTEXT — Bestaetigt unsere Architektur-Entscheidung |
| **Microsoft ISE: Customer Feedback** [DevBlog](https://devblogs.microsoft.com/ise/insights_generation_from_customer_feedback_using_llms/) | Produktions-Case fuer LLM-basierte Feedback-Analyse. Iteratives Prompt-Refinement. | KONTEXT — Validiert LLM-Feedback-Analyse Ansatz |

### Architektur-Entscheidung (basierend auf Research)

**Gewaehlter Ansatz: TNT-LLM + Clio + GoalEx Hybrid**

| Aspekt | Pattern-Quelle | Wie wir es nutzen |
|--------|---------------|-------------------|
| Iterative Taxonomy Generation | TNT-LLM | Mini-Batch-Verarbeitung, LangGraph StateGraph |
| Facet/Fact Extraction | Clio | Structured Extraction pro Interview |
| Goal-Driven Assignment | GoalEx | `research_goal` steuert Clustering-Perspektive |
| Self-Correction Loop | Few-Shot Clustering | LangGraph-Loop mit max 3 Iterationen |
| Streaming/Inkrementell | k-LLMmeans | Neues Interview → inkrementelle Zuordnung |
| Tiered LLM | TNT-LLM + OpenRouter | Haiku fuer Extraction, Sonnet fuer Clustering |

---

## Open Questions (alle resolved)

| # | Question | Options | Recommended | Decision |
|---|----------|---------|-------------|----------|
| 1 | Welches LLM-Modell fuer Fact Extraction vs. Clustering? | A) Gleiches Modell B) Differenziert C) Konfigurierbar | C) Konfigurierbar | **OpenRouter-Integration. User konfiguriert Model-Slug pro Aufgabe (Interviewer, Extraction, Clustering, Summary).** |
| 2 | Hierarchisches Clustering? Themen > Sub-Themen? | A) Flach B) 2 Ebenen | A) Flach fuer MVP | **Flach (eine Ebene). Hierarchie ggf. spaeter.** |
| 3 | Wie wird Re-Clustering getriggert? | A) Nach jedem Interview B) Alle N Interviews C) Manuell | Hybrid | **Inkrementell (Default) + LLM Merge/Split-Vorschlaege (User-Approval) + manueller Full Re-Cluster Button.** |
| 4 | Dashboard Frontend-Framework? | A) Next.js B) Vite + React C) Astro | A) Next.js | **Next.js (Ecosystem, SSR).** |
| 5 | Soll der Prompt-Kontext des Projekts auch das Clustering beeinflussen? | A) Nur Interviewer B) Beides | B) Beides | **Beides. research_goal + prompt_context fliessen in Clustering-Prompts ein (GoalEx Pattern).** |
| 6 | Soll der User Cluster manuell bearbeiten koennen? | A) Read-Only B) Leichtgewichtig C) Volle Kontrolle | C) Volle Kontrolle | **Volle Kontrolle: Umbenennen, Mergen, Splitten, Facts verschieben.** |
| 7 | Welche Export-Optionen in V1? | A) CSV B) PDF C) API D) Kein Export | C) API | **REST API Endpoint fuer Integration (Jira, Notion, etc.). Kein CSV/PDF in V1.** |

---

## Research Log

| Date | Area | Finding |
|------|------|---------|
| 2026-02-28 | Codebase | Insights-Domain hat nur `summary.py`. Kein Clustering existiert. Greenfield. |
| 2026-02-28 | Codebase | LangGraph + SSE + OpenRouter Pattern existieren und koennen wiederverwendet werden. |
| 2026-02-28 | Codebase | `mvp_interviews` hat transcript (JSONB) + summary (TEXT). Daten-Basis vorhanden. |
| 2026-02-28 | Codebase | `InterviewService.end()` ist der Hook-Point fuer Clustering-Trigger. |
| 2026-02-28 | Web | TNT-LLM (Microsoft): State-of-the-art fuer LLM-basiertes Clustering ohne Vektoren. |
| 2026-02-28 | Web | "Text Clustering as Classification" Paper: Reframes Clustering als Classification-Task. |
| 2026-02-28 | Web | k-LLMmeans: Streaming-native Clustering mit Summary-als-Zentroid. Kosteneffizient. |
| 2026-02-28 | Web | Dial-In LLM: >95% Alignment mit menschlichem Urteil bei Intent-Clustering. |
| 2026-02-28 | Web | QualIT (Amazon): 2-stufiges Clustering mit Halluzinations-Check. |
| 2026-02-28 | Web | Enterpret (Notion): Produktions-Referenz fuer automatische Feedback-Kategorisierung. |
| 2026-02-28 | Web | GoalEx (EMNLP 2023): Goal-Driven Clustering — User gibt Ziel vor, LLM clustert zielgerichtet. Propose-Assign-Select Pattern. |
| 2026-02-28 | Web | Anthropic Clio: 4-Stufen Pipeline (Facet Extraction → Clustering → Description → Hierarchy). 94% Accuracy. OpenClio verfuegbar. |
| 2026-02-28 | Web | Anthropic Interviewer: Claude-powered Qualitative-Research-Tool. Interview → Theme Clustering Pipeline validiert. |
| 2026-02-28 | Web | Few-Shot Clustering (MIT Press): 3 LLM-Integrations-Ebenen (Pre/During/Post-Clustering). Post = Self-Correction. |
| 2026-02-28 | Web | LangGraph TNT-LLM Notebook: Offizieller Code mit StateGraph, TaxonomyGenerationState, iterativer Refinement-Loop. |
| 2026-02-28 | Decision | LLM-Modelle: OpenRouter mit konfigurierbaren Model-Slugs pro Aufgabe. |
| 2026-02-28 | Decision | Re-Clustering: Hybrid (inkrementell + LLM Merge/Split-Vorschlaege + manueller Full Re-Cluster). |
| 2026-02-28 | Decision | Cluster-Editing: Volle Kontrolle (Rename, Merge, Split, Facts verschieben). |
| 2026-02-28 | Decision | Export: REST API Endpoint in V1, kein CSV/PDF. |
| 2026-02-28 | Decision | Architektur: TNT-LLM + Clio + GoalEx Hybrid mit LangGraph Self-Correction Loop. |

---

## Q&A Log

| # | Question | Answer |
|---|----------|--------|
| 1 | Soll ich zuerst eine umfassende Recherche durchfuehren oder direkt Q&A starten? | Recherche zuerst, dann gezielte Fragen. |
| 2 | Was ist die Clustering-Basis: Summaries, Transcripts oder beides? | Beides (Hybrid): Summaries fuer Clustering, Transcripts fuer Drill-Down/Zitate. |
| 3 | Welcher Clustering-Ansatz: Direct LLM, TNT-LLM, Fact-First, oder Hybrid? | B+C Hybrid: TNT-LLM Style Themen-Clustering + Fact-First Pipeline. Zwei Ebenen: Themen > Facts. |
| 4 | Wann soll das Clustering laufen? Nach jedem Interview, manuell, oder hybrid? | Nach jedem Interview automatisch. |
| 5 | Soll Clustering pro Produkt, Cross-Product, oder beides laufen? | Pro Projekt/Kampagne. User kann Projekte mit Research-Ziel und Prompt-Kontext anlegen. |
| 6 | Soll die Taxonomie emergent sein oder User-definiert? | Emergent durch LLM, aber im Rahmen des Projekt-Research-Ziels. Projekt definiert Rahmen, LLM clustert frei. |
| 7 | Darf das LLM neue Themen vorschlagen? | Ja — LLM clustert frei, Taxonomie waechst emergent. |
| 8 | Woher sollen atomare Facts extrahiert werden? | Konfigurierbar pro Projekt: Summary oder Transcript. Muss testbar sein. |
| 9 | Was soll das Clustering-Ergebnis enthalten? | Alles: Themen-Uebersicht mit Zaehlern, Cluster-Zusammenfassungen, Facts pro Cluster (Drill-Down), Zitate/Belege aus Transcripts. |
| 10 | Welches Agentic Pattern fuer die Clustering-Pipeline? | Agentic mit Self-Correction (LangGraph-Loop: Extract → Cluster → Validate → ggf. Re-Cluster). |
| 11 | Was ist der MVP-Scope? | Pipeline + Dashboard (nicht nur Backend). |
| 12 | Wo lebt das Dashboard? | Im bestehenden feedbackai-mvp Repo als neuer Ordner. |
| 13 | Wie soll die Cluster-Uebersicht im Dashboard aussehen? | Card-based: Cluster-Cards mit Name, Zaehler, Zusammenfassung. Klick → Drill-Down. |
| 14 | Welche Projekt-Management-Funktionen gehoeren zum MVP-Scope? | Alle: Projekt erstellen, Interview-Zuordnung, Cluster-Dashboard, Taxonomy bearbeiten. |
| 15 | Soll nach Taxonomy-Bearbeitung automatisch re-clustered werden? | Nur Summary-Regenerierung. Facts werden bei Merge/Split direkt verschoben, Summaries automatisch neu generiert. Kein erneuter Clustering-Durchlauf. |
| 16 | Wie wird das Dashboard geschuetzt? | JWT Auth (Email/Passwort, python-jose + passlib). Codebase hat Supabase entfernt (commit 9e71eca), JWT_SECRET bereits konfiguriert. |
| 17 | Wie tief soll die Discovery gehen? | Detailliert (alle Sections + Wireframes + Edge Cases). |
| 18 | Wieviele Interviews pro Projekt erwartet? | Gross (100+). Beeinflusst Pipeline: Batching + inkrementelles Clustering noetig. |
| 19 | Sollen Clustering-Ergebnisse in Echtzeit im Dashboard erscheinen? | Ja, Live-Updates via SSE. |
| 20 | Scope-Check: Ist Pipeline + Dashboard + Projekt-Mgmt + Live-Updates als EIN Feature realistisch? | Ja, gehoert alles zusammen. |
| 21 | Sollen unterschiedliche LLM-Modelle pro Aufgabe verwendet werden? | OpenRouter-Integration. User konfiguriert Model-Slug pro Aufgabe (Interviewer, Extraction, Clustering, Summary). |
| 22 | Wann soll Re-Clustering ausgeloest werden? | Inkrementell als Default + LLM Merge/Split-Vorschlaege (User-Approval) + manueller Full Re-Cluster Button. |
| 23 | Soll der User Cluster manuell bearbeiten koennen? | Volle Kontrolle: Umbenennen, Mergen, Splitten, Facts verschieben. |
| 24 | Welche Export-Optionen braucht V1? | REST API Endpoint fuer Integration (Jira, Notion, etc.). Kein CSV/PDF in V1. |
| 25 | Werden bei inkrementellem Clustering alle Daten neu geclustert? | Nein. Nur neue Facts werden zugeordnet. Merge/Split-Vorschlaege kommen automatisch, User entscheidet. Full Re-Cluster nur manuell. |

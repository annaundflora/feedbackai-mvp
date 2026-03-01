---
title: "Discovery: Insights Pipeline (Fact Extraction + Clustering)"
created: 2026-03-01
status: Draft
---

# Feature: Insights Pipeline (Fact Extraction + Clustering)

**Epic:** Phase 8 -- Dashboard + Insights (Roadmap)
**Status:** Draft
**Wireframes:** -- (Backend-only, kein UI in diesem Scope)

---

## Problem & Solution

**Problem:**
- Interviews erzeugen Bullet-Summaries, aber keine strukturierten, durchsuchbaren Erkenntnisse
- Muster ueber mehrere Interviews hinweg sind unsichtbar (welche Pain Points tauchen wiederholt auf?)
- Product Owner muss manuell durch Summaries lesen, um Trends zu erkennen
- Keine automatische Priorisierung: "10 User sagen Suche ist kaputt" vs. "1 User will Dark Mode"

**Solution:**
- Automatische Extraktion atomarer Facts aus Interview-Transkripten
- Embedding-basiertes Clustering der Facts zu thematischen Gruppen
- LLM-generierte, menschenlesbare Cluster-Labels
- Inkrementelle Verarbeitung: neue Interviews fuettern bestehende Cluster

**Business Value:**
- Schliesst den Feedback-to-Decision Loop (Vision Phase 8)
- Quantifiziert qualitative Erkenntnisse ("12 von 30 Interviews nennen Suchprobleme")
- Ermoeglicht datengestuetzte Produktentscheidungen statt Bauchgefuehl

---

## Scope & Boundaries

| In Scope |
|----------|
| Fact Extraction: Interview-Transkript → atomare Fact-Objekte |
| Fact Embedding: Jeder Fact bekommt einen Embedding-Vektor |
| Clustering: Facts werden zu thematischen Clustern gruppiert |
| Cluster Labeling: LLM generiert menschenlesbare Labels pro Cluster |
| Inkrementelle Verarbeitung: Neue Facts werden bestehenden Clustern zugeordnet oder bilden neue |
| DB-Persistenz: Facts, Embeddings, Cluster in PostgreSQL |
| API-Endpoints: Cluster abrufen, Facts pro Cluster listen |
| CLI/Admin-Trigger: Clustering manuell ausloesen |

| Out of Scope |
|--------------|
| Dashboard-UI (eigene Phase, konsumiert diese API) |
| Echtzeit-Streaming der Clustering-Ergebnisse |
| Multi-Produkt-Trennung (kommt mit Phase 6 Multi-Context) |
| Voice-Transkription (Phase 9) |
| Fact-Editing durch User (spaeter) |
| Hierarchische Cluster (Theme > Sub-Theme, spaeter) |

---

## Current State Reference

- `app/insights/summary.py`: SummaryService generiert Bullet-Summaries aus Transkripten (max 10 Punkte)
- `mvp_interviews`-Tabelle: Speichert `transcript` (JSONB) und `summary` (TEXT)
- OpenRouter LLM-Integration via `langchain_openai.ChatOpenAI`
- SQLAlchemy async mit Raw SQL (Repository-Pattern)
- Bullet-Summary-Prompt extrahiert bereits "konkretes Fact, Pain Point, Wunsch oder Erkenntnis"

---

## User Flow

1. Interview wird abgeschlossen -> `InterviewService.end()` speichert Transkript + Summary
2. System triggert Fact Extraction fuer das neue Interview (async, nach Completion)
3. FactExtractionService extrahiert atomare Facts aus dem Transkript
4. Jeder Fact wird embedded (Embedding-Modell via OpenRouter oder dediziert)
5. Neue Facts werden gegen bestehende Cluster-Centroids verglichen
6. Facts ueber Schwellwert -> zugeordnet zu bestehendem Cluster
7. Facts unter Schwellwert -> in "unassigned" Buffer
8. Periodisch (oder manuell): Re-Clustering mit unassigned Facts
9. Betroffene Cluster bekommen neue LLM-generierte Labels
10. API liefert Cluster-Liste mit Labels, Fact-Count, Top-Facts

**Error Paths:**
- LLM-Timeout bei Fact Extraction -> Retry mit Backoff, max 3 Versuche
- Embedding-API nicht erreichbar -> Facts ohne Embedding in Queue, spaeter nachholen
- Zu wenige Facts fuer Clustering (<5) -> Kein Clustering, nur Fact-Liste anzeigen

---

## Business Rules

- Jeder Fact gehoert zu genau einem Interview (Quelle nachverfolgbar)
- Ein Fact gehoert zu maximal einem Cluster (keine Mehrfachzuordnung)
- Cluster-Labels werden bei jeder Aenderung der Cluster-Zusammensetzung neu generiert
- Minimum 3 Facts pro Cluster (sonst bleibt Cluster im "unassigned" Status)
- Facts aus `completed` und `completed_timeout` Interviews werden extrahiert
- Bereits extrahierte Interviews werden nicht nochmal verarbeitet (Idempotenz)
- Cluster mit 0 Facts nach Re-Clustering werden geloescht

---

## Data

### Fact

| Field | Required | Validation | Notes |
|-------|----------|------------|-------|
| `id` | Yes | UUID | PK |
| `interview_id` | Yes | FK -> mvp_interviews.id | Quelle |
| `text` | Yes | 1-1000 Zeichen | Atomare Aussage |
| `category` | Yes | enum: pain_point, wish, behavior, insight | LLM-klassifiziert |
| `embedding` | Yes | vector(1536) oder vector(384) | Abhaengig vom Embedding-Modell |
| `cluster_id` | No | FK -> mvp_clusters.id | NULL = unassigned |
| `created_at` | Yes | Timestamp | Extraktionszeitpunkt |

### Cluster

| Field | Required | Validation | Notes |
|-------|----------|------------|-------|
| `id` | Yes | UUID | PK |
| `label` | Yes | 1-200 Zeichen | LLM-generiert |
| `description` | No | 1-500 Zeichen | LLM-generiert, detaillierter |
| `centroid_embedding` | Yes | vector(1536) oder vector(384) | Embedding des Label-Texts |
| `fact_count` | Yes | >= 0 | Denormalisiert fuer schnelle Queries |
| `created_at` | Yes | Timestamp | |
| `updated_at` | Yes | Timestamp | Letzte Aenderung |

### Clustering Run

| Field | Required | Validation | Notes |
|-------|----------|------------|-------|
| `id` | Yes | UUID | PK |
| `status` | Yes | enum: running, completed, failed | |
| `facts_processed` | Yes | int | |
| `clusters_created` | Yes | int | |
| `clusters_updated` | Yes | int | |
| `started_at` | Yes | Timestamp | |
| `completed_at` | No | Timestamp | |
| `error` | No | Text | Falls failed |

---

## Feature State Machine

### States Overview

| State | Beschreibung | Trigger |
|-------|-------------|---------|
| `no_facts` | Noch keine Facts extrahiert | Initial |
| `facts_only` | Facts vorhanden, aber <5 fuer Clustering | Fact Extraction |
| `clustered` | Facts in Clustern gruppiert | Clustering Run |
| `stale` | Neue unzugeordnete Facts vorhanden, Re-Clustering empfohlen | Neue Interview-Completion |

### Transitions

| Current State | Trigger | Next State |
|---------------|---------|------------|
| `no_facts` | Interview completed + Fact Extraction | `facts_only` oder `clustered` |
| `facts_only` | Fact Count >= 5 + Clustering Run | `clustered` |
| `clustered` | Neue Facts zugeordnet (ueber Schwellwert) | `clustered` |
| `clustered` | Neue Facts nicht zugeordnet (unter Schwellwert) | `stale` |
| `stale` | Re-Clustering Run | `clustered` |

---

## Implementation Slices

### Dependencies

```
Slice 1 (Fact Extraction) -> Slice 2 (Embedding) -> Slice 3 (Clustering)
                                                         |
                                                    Slice 4 (Incremental)
                                                         |
                                                    Slice 5 (API)
```

### Slices

| # | Name | Scope | Testability | Dependencies |
|---|------|-------|-------------|--------------|
| 1 | Fact Extraction | DB-Schema (facts, clusters, runs), FactExtractionService, LLM-Prompt, Repository | Unit: Mock-LLM gibt Facts zurueck. Integration: Echtes Transkript -> strukturierte Facts | -- |
| 2 | Fact Embedding | EmbeddingService, pgvector Extension, Embedding-Spalte in facts-Tabelle | Unit: Mock-Embedding. Integration: Text -> Vektor -> DB gespeichert | Slice 1 |
| 3 | Clustering + Labeling | ClusteringService (Agglomerative/Affinity Propagation), LLM-Labeling, Cluster-Repository | Unit: Vordefinierte Embeddings -> erwartete Cluster. Integration: 20+ Facts -> sinnvolle Cluster mit Labels | Slice 2 |
| 4 | Incremental Assignment | Cosine-Similarity gegen Centroids, Schwellwert-Logik, Re-Clustering Trigger | Unit: Neuer Fact -> zugeordnet oder unassigned. Integration: Neues Interview -> Facts fliessen in bestehende Cluster | Slice 3 |
| 5 | API Endpoints | GET /clusters, GET /clusters/:id/facts, POST /clustering/run | Unit: Route-Tests. Integration: E2E Clustering -> API -> JSON-Response | Slice 3 |

### Recommended Order

1. **Slice 1:** Fact Extraction -- Basis: ohne Facts kein Clustering
2. **Slice 2:** Fact Embedding -- Voraussetzung fuer jede Aehnlichkeitsberechnung
3. **Slice 3:** Clustering + Labeling -- Kernfunktion: Facts -> thematische Cluster
4. **Slice 4:** Incremental Assignment -- Live-Betrieb: neue Interviews fliessen automatisch ein
5. **Slice 5:** API Endpoints -- Dashboard-Ready: Daten sind von aussen abrufbar

---

## Context & Research

### Similar Patterns in Codebase

| Feature | Location | Relevant because |
|---------|----------|------------------|
| SummaryService | `app/insights/summary.py` | LLM-Call-Pattern, Prompt-Struktur, OpenRouter-Integration |
| InterviewRepository | `app/interview/repository.py` | Repository-Pattern mit Raw SQL, async Sessions |
| PromptAssembler | `app/interview/prompt.py` | Prompt-Templating, Context-Injection |

### Web Research

| Source | Finding |
|--------|---------|
| [k-LLMmeans (arXiv:2502.09667)](https://arxiv.org/abs/2502.09667) | Summary-as-Centroid: LLM-generierte Summaries als Cluster-Zentren, Mini-Batch-Streaming-Variante fuer inkrementelle Verarbeitung |
| [LLM-MemCluster (arXiv:2511.15424)](https://arxiv.org/abs/2511.15424) | SOTA Single-Pass Clustering, dynamische Cluster-Erstellung, aber teuer (1 LLM-Call pro Fact) |
| [TnT-LLM (arXiv:2403.12173)](https://arxiv.org/abs/2403.12173) | Microsoft: Taxonomie-Generierung + leichtgewichtiger Klassifizierer, gut fuer Produktion |
| [GoalEx (arXiv:2305.13749)](https://arxiv.org/abs/2305.13749) | Zielgerichtetes Clustering mit Natural-Language-Goals, keine k-Vorgabe noetig |
| [BERTopic](https://maartengr.github.io/BERTopic/) | Reife Library: UMAP + HDBSCAN + c-TF-IDF, aber schwach bei kleinen Datasets (<500) |
| [QualIT (arXiv:2409.15626)](https://arxiv.org/html/2409.15626) | Amazon: Key-Phrase-Extraction -> Embedding -> Clustering, speziell fuer qualitatives Feedback |

### Empfohlener Ansatz: Hybrid

Kombination der besten Ideen:
1. **Embed + Cluster** (scikit-learn: Agglomerative Clustering, kein k noetig) -- schnell, deterministisch
2. **LLM-Labeling** (GoalEx-inspiriert: zielgerichtete Labels) -- interpretierbar, actionable
3. **Inkrementell** (k-LLMmeans Mini-Batch: Cosine-Similarity gegen Summary-Centroids) -- neue Facts fliessen ein
4. **LLM-Kosten**: ~10-30 Calls pro Clustering-Run (nur fuer Labels), nicht pro Fact

---

## Open Questions

| # | Question | Options | Recommended | Decision |
|---|----------|---------|-------------|----------|
| 1 | Embedding-Modell? | A) OpenAI text-embedding-3-small (1536d, via OpenRouter) B) all-MiniLM-L6-v2 (384d, lokal) C) Cohere embed-v3 (1024d, via API) | A) OpenAI via OpenRouter -- konsistent mit bestehendem LLM-Setup, keine neue Infrastruktur | -- |
| 2 | Vektor-Storage? | A) pgvector Extension in bestehendem PostgreSQL B) Separate Vektor-DB (Qdrant, Pinecone) | A) pgvector -- kein neuer Service, Hunderte Facts brauchen keine spezialisierte Vektor-DB | -- |
| 3 | Clustering-Algorithmus? | A) Agglomerative Clustering (Dendrogram, Distance-Threshold) B) Affinity Propagation (auto-k) C) HDBSCAN | A) Agglomerative -- robust bei kleinen Datasets, konfigurierbarer Threshold, deterministisch | -- |
| 4 | Fact-Extraction-Trigger? | A) Synchron bei Interview-End B) Async Background-Task nach Interview-End C) Manueller Batch-Trigger | B) Async -- blockiert nicht den /end Endpoint, aber verarbeitet zeitnah | -- |
| 5 | Fact-Kategorien? | A) pain_point, wish, behavior, insight B) problem, feature_request, positive, neutral C) Keine Kategorien, nur Text | A) pain_point, wish, behavior, insight -- deckt UX-Research-Taxonomie ab | -- |

---

## Research Log

| Date | Area | Finding |
|------|------|---------|
| 2026-03-01 | Web | 7 Clustering-Ansaetze verglichen (k-LLMmeans, MemCluster, TnT-LLM, GoalEx, TCC, BERTopic, QualIT) |
| 2026-03-01 | Web | Hybrid-Ansatz (Embed+Cluster+LLM-Label) optimal fuer unsere Skala (Hunderte Facts) |
| 2026-03-01 | Codebase | SummaryService extrahiert bereits semi-strukturierte Bullets -- gute Basis fuer Fact Extraction |
| 2026-03-01 | Codebase | Repository-Pattern mit Raw SQL + async Sessions etabliert -- Facts/Clusters folgen demselben Pattern |
| 2026-03-01 | Web | pgvector Extension fuer PostgreSQL unterstuetzt Cosine-Similarity-Suche nativ |

---

## Q&A Log

| # | Question | Answer |
|---|----------|--------|
| 1 | Warum nicht BERTopic? | HDBSCAN braucht Dichte-Schaetzung, funktioniert schlecht bei <500 Datenpunkten. Unsere Skala: Hunderte Facts. Agglomerative Clustering ist robuster. |
| 2 | Warum nicht reines LLM-Clustering (MemCluster)? | Jeder Fact braucht einen LLM-Call -> bei 500 Facts = 500 Calls. Unser Hybrid: 500 Embedding-Calls (billig) + 20 LLM-Calls (Labels). Faktor 25x guenstiger. |
| 3 | Warum Summary-as-Centroid statt Mean-Embedding? | k-LLMmeans Paper zeigt: LLM-Summary-Embedding als Centroid ist semantisch praeziser als arithmetisches Mittel der Member-Embeddings. Filtert Noise, fokussiert auf Kernthema. |

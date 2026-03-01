---
title: "Architecture: Insights Pipeline (Fact Extraction + Clustering)"
created: 2026-03-01
status: Draft
---

# Feature: Insights Pipeline (Fact Extraction + Clustering)

**Epic:** Phase 8 -- Dashboard + Insights
**Status:** Draft
**Discovery:** `discovery.md` (same folder)
**Derived from:** Discovery constraints, research on 7 LLM clustering approaches

---

## Problem & Solution

**Problem:**
- Interview-Summaries sind unstrukturiert, nicht durchsuchbar, nicht aggregierbar
- Muster ueber Interviews hinweg unsichtbar

**Solution:**
- Automatische Fact Extraction + Embedding + Clustering + LLM-Labeling
- Hybrid-Ansatz: Embedding-basiert (billig, schnell) + LLM (nur fuer Labels)

**Business Value:**
- Quantifiziert qualitative Erkenntnisse, schliesst Feedback-to-Decision Loop

---

## Scope & Boundaries

| In Scope |
|----------|
| Fact Extraction Service + DB Schema |
| Embedding Service (OpenRouter/OpenAI) |
| Clustering Service (Agglomerative + LLM-Labeling) |
| Incremental Assignment (neue Facts -> bestehende Cluster) |
| REST API fuer Cluster/Fact Zugriff |
| DB Migrations (facts, clusters, clustering_runs) |

| Out of Scope |
|--------------|
| Dashboard-UI |
| Multi-Produkt-Trennung |
| Hierarchische Cluster |
| Fact-Editing |

---

## API Design

### Overview

| Aspect | Specification |
|--------|---------------|
| Style | REST (konsistent mit bestehendem Interview-API) |
| Authentication | Keine (MVP, wie bestehende Endpoints) |
| Rate Limiting | Keine (MVP) |
| Base Path | `/api/insights` |

### Endpoints

| Method | Path | Request | Response | Business Logic |
|--------|------|---------|----------|----------------|
| POST | `/api/insights/extract/{interview_id}` | -- | `ExtractResponse` | Extrahiert Facts aus einem Interview |
| POST | `/api/insights/extract/batch` | `BatchExtractRequest` | `BatchExtractResponse` | Extrahiert Facts aus allen noch nicht verarbeiteten Interviews |
| POST | `/api/insights/clustering/run` | `ClusteringRunRequest` | `ClusteringRunResponse` | Fuehrt Clustering ueber alle Facts aus |
| GET | `/api/insights/clusters` | Query: `?min_facts=1` | `ClusterListResponse` | Listet alle Cluster mit Labels und Fact-Counts |
| GET | `/api/insights/clusters/{cluster_id}` | -- | `ClusterDetailResponse` | Cluster-Details mit allen zugehoerigen Facts |
| GET | `/api/insights/facts` | Query: `?cluster_id=X&category=Y&unassigned=true` | `FactListResponse` | Facts filtern und listen |
| GET | `/api/insights/stats` | -- | `StatsResponse` | Uebersicht: Total Facts, Clusters, unassigned, letzte Runs |

### Data Transfer Objects (DTOs)

| DTO | Fields | Notes |
|-----|--------|-------|
| `ExtractResponse` | `interview_id`, `facts_extracted: int`, `facts: list[FactDTO]` | |
| `BatchExtractRequest` | `limit: int = 50` | Max Interviews pro Batch |
| `BatchExtractResponse` | `interviews_processed: int`, `total_facts_extracted: int` | |
| `ClusteringRunRequest` | `distance_threshold: float = 0.35`, `force_recluster: bool = false` | |
| `ClusteringRunResponse` | `run_id`, `status`, `clusters_created`, `clusters_updated`, `facts_processed` | |
| `ClusterDTO` | `id`, `label`, `description`, `fact_count`, `top_facts: list[FactDTO]`, `created_at`, `updated_at` | `top_facts`: 5 repraesentativste |
| `FactDTO` | `id`, `text`, `category`, `interview_id`, `cluster_id`, `created_at` | |
| `StatsResponse` | `total_facts`, `total_clusters`, `unassigned_facts`, `last_extraction_at`, `last_clustering_at` | |

---

## Database Schema

### Prerequisites

- PostgreSQL `pgvector` Extension muss installiert sein
- `CREATE EXTENSION IF NOT EXISTS vector;` in Migration

### Entities

| Table | Purpose | Key Fields |
|-------|---------|------------|
| `mvp_facts` | Atomare Fakten aus Interviews | id, interview_id, text, category, embedding |
| `mvp_clusters` | Thematische Cluster | id, label, description, centroid_embedding |
| `mvp_clustering_runs` | Audit-Log der Clustering-Laeufe | id, status, facts_processed, clusters_created |

### Schema Details

#### Table: `mvp_facts`

| Column | Type | Constraints | Index |
|--------|------|-------------|-------|
| `id` | UUID | PK, DEFAULT gen_random_uuid() | Yes (PK) |
| `interview_id` | UUID | NOT NULL, FK -> mvp_interviews.id | Yes |
| `text` | TEXT | NOT NULL, CHECK length 1-1000 | No |
| `category` | TEXT | NOT NULL, CHECK IN ('pain_point', 'wish', 'behavior', 'insight') | Yes |
| `embedding` | vector(1536) | NULL (wird async gefuellt) | Yes (ivfflat oder hnsw) |
| `cluster_id` | UUID | NULL, FK -> mvp_clusters.id | Yes |
| `created_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | No |

#### Table: `mvp_clusters`

| Column | Type | Constraints | Index |
|--------|------|-------------|-------|
| `id` | UUID | PK, DEFAULT gen_random_uuid() | Yes (PK) |
| `label` | TEXT | NOT NULL | No |
| `description` | TEXT | NULL | No |
| `centroid_embedding` | vector(1536) | NOT NULL | Yes (ivfflat oder hnsw) |
| `fact_count` | INTEGER | NOT NULL, DEFAULT 0 | No |
| `created_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | No |
| `updated_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | No |

#### Table: `mvp_clustering_runs`

| Column | Type | Constraints | Index |
|--------|------|-------------|-------|
| `id` | UUID | PK, DEFAULT gen_random_uuid() | Yes (PK) |
| `status` | TEXT | NOT NULL, CHECK IN ('running', 'completed', 'failed') | Yes |
| `distance_threshold` | FLOAT | NOT NULL | No |
| `facts_processed` | INTEGER | NOT NULL, DEFAULT 0 | No |
| `clusters_created` | INTEGER | NOT NULL, DEFAULT 0 | No |
| `clusters_updated` | INTEGER | NOT NULL, DEFAULT 0 | No |
| `started_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | No |
| `completed_at` | TIMESTAMPTZ | NULL | No |
| `error` | TEXT | NULL | No |

### Relationships

| From | To | Relationship | Cascade |
|------|-----|--------------|---------|
| `mvp_facts` | `mvp_interviews` | N:1 (many facts per interview) | ON DELETE CASCADE |
| `mvp_facts` | `mvp_clusters` | N:1 (many facts per cluster) | ON DELETE SET NULL |

---

## Server Logic

### Services & Processing

| Service | Responsibility | Input | Output | Side Effects |
|---------|----------------|-------|--------|--------------|
| `FactExtractionService` | Extrahiert atomare Facts aus Transkript via LLM | interview_id oder messages | list[Fact] | DB: INSERT mvp_facts |
| `EmbeddingService` | Erzeugt Embedding-Vektoren fuer Texte | list[str] | list[vector] | Keine (pure function + API Call) |
| `ClusteringService` | Fuehrt Clustering ueber alle Facts aus | distance_threshold | ClusteringResult | DB: INSERT/UPDATE mvp_clusters, UPDATE mvp_facts.cluster_id |
| `IncrementalAssigner` | Ordnet neue Facts bestehenden Clustern zu | list[Fact] (mit Embeddings) | AssignmentResult | DB: UPDATE mvp_facts.cluster_id |
| `ClusterLabeler` | Generiert Labels fuer Cluster via LLM | cluster_id, member_facts | label, description | DB: UPDATE mvp_clusters.label |

### Business Logic Flow

#### Fact Extraction (Post-Interview)

```
Interview completed
    -> FactExtractionService.extract(interview_id)
        -> Repository: load transcript from mvp_interviews
        -> LLM Call: extract atomic facts (structured output)
        -> Parse JSON response into Fact objects
        -> EmbeddingService.embed(fact_texts)
        -> Repository: INSERT facts with embeddings
        -> Return: list[FactDTO]
```

#### Full Clustering Run

```
POST /clustering/run
    -> ClusteringService.run(distance_threshold)
        -> Repository: load ALL facts with embeddings
        -> scikit-learn: AgglomerativeClustering(
              metric='cosine',
              linkage='average',
              distance_threshold=0.35,
              n_clusters=None
           )
        -> For each resulting cluster:
            -> Select representative facts (closest to cluster mean)
            -> ClusterLabeler.label(representative_facts)
            -> EmbeddingService.embed(label_text) -> centroid_embedding
            -> Repository: INSERT/UPDATE mvp_clusters
        -> Repository: UPDATE mvp_facts.cluster_id
        -> Repository: INSERT mvp_clustering_runs (audit)
        -> Return: ClusteringRunResponse
```

#### Incremental Assignment (New Facts)

```
New facts extracted (post-interview)
    -> IncrementalAssigner.assign(new_facts)
        -> Repository: load cluster centroids (centroid_embedding)
        -> For each new fact:
            -> Cosine similarity vs all centroids
            -> If max_similarity > ASSIGNMENT_THRESHOLD (0.65):
                -> Assign to best cluster
                -> Repository: UPDATE mvp_facts.cluster_id
            -> Else:
                -> Leave unassigned (cluster_id = NULL)
        -> If unassigned_count > RECLUSTER_THRESHOLD (10):
            -> Flag system as "stale"
        -> Return: AssignmentResult(assigned, unassigned)
```

### Fact Extraction Prompt

```
Du bist ein Analyst der Interview-Transkripte in atomare Fakten zerlegt.

Extrahiere aus dem folgenden Interview-Transkript alle einzelnen Fakten,
Pain Points, Wuensche und Verhaltensbeobachtungen.

Regeln:
- Jeder Fakt ist ein eigenstaendiger Satz
- Formuliere in der dritten Person ("User findet...", "User wuenscht...")
- Nur konkrete Aussagen, keine Interpretationen
- Keine Duplikate
- Kategorisiere jeden Fakt: pain_point | wish | behavior | insight

Ausgabe als JSON-Array:
[
  {"text": "User findet die Suchfunktion unuebersichtlich", "category": "pain_point"},
  {"text": "User wuenscht sich eine Filteroption nach Fahrzeugtyp", "category": "wish"},
  ...
]

Transkript:
{transcript}
```

### Cluster Labeling Prompt

```
Du bist ein UX-Research-Analyst der thematische Cluster benennt.

Die folgenden Fakten gehoeren zu einem thematischen Cluster aus User-Interviews.
Erstelle ein praeznantes Label und eine kurze Beschreibung fuer diesen Cluster.

Regeln:
- Label: Max 5 Woerter, beschreibt das Kernthema
- Beschreibung: 1-2 Saetze, fasst die Gemeinsamkeit der Fakten zusammen
- Fokus auf das Problem/Thema, nicht auf die Loesung
- Deutsche Sprache

Fakten in diesem Cluster:
{facts}

Ausgabe als JSON:
{"label": "...", "description": "..."}
```

---

## Architecture Layers

### Layer Responsibilities

| Layer | Responsibility | Pattern |
|-------|----------------|---------|
| `app/api/insights_routes.py` | HTTP Endpoints, Request/Response Mapping | Router (FastAPI) |
| `app/insights/extraction.py` | Fact Extraction via LLM | Service |
| `app/insights/embedding.py` | Text -> Embedding Vektor | Service |
| `app/insights/clustering.py` | Clustering Algorithmus + Orchestration | Service |
| `app/insights/labeling.py` | Cluster Label Generation via LLM | Service |
| `app/insights/assigner.py` | Incremental Fact -> Cluster Assignment | Service |
| `app/insights/repository.py` | CRUD fuer facts, clusters, runs | Repository |

### Data Flow

```
[Interview completed]
    |
    v
FactExtractionService --LLM--> atomic facts
    |
    v
EmbeddingService --API--> fact embeddings
    |
    v
InsightsRepository --> mvp_facts (DB)
    |
    v
IncrementalAssigner --> assign to existing clusters (if any)
    |
    v
[Manual/Periodic Trigger]
    |
    v
ClusteringService --scikit-learn--> cluster assignments
    |
    v
ClusterLabeler --LLM--> human-readable labels
    |
    v
EmbeddingService --> centroid embeddings (summary-as-centroid)
    |
    v
InsightsRepository --> mvp_clusters (DB)
```

### Error Handling Strategy

| Error Type | Handling | User Response | Logging |
|------------|----------|---------------|---------|
| LLM Timeout (extraction) | Retry 3x mit Backoff (2s, 4s, 8s) | 503 "Extraction temporarily unavailable" | Warning log |
| LLM Parse Error (invalid JSON) | Retry mit vereinfachtem Prompt, dann fail | 500 "Extraction failed" | Error log + raw response |
| Embedding API Error | Facts ohne Embedding speichern, spaeter nachholen | 200 mit Warning in Response | Warning log |
| Too Few Facts (<5) | Kein Clustering, nur Facts speichern | 200 mit `clusters_created: 0` | Info log |
| Clustering Algorithm Error | Run als "failed" markieren | 500 mit run_id fuer Debugging | Error log + stack trace |
| DB Error | Standard SQLAlchemy Error Handling | 500 | Error log |

---

## Security

### Input Validation & Sanitization

| Input | Validation | Sanitization |
|-------|------------|--------------|
| `interview_id` (path param) | UUID format | -- |
| `cluster_id` (path param) | UUID format | -- |
| `distance_threshold` (body) | float, 0.1 - 0.9 | Clamp to range |
| `limit` (query) | int, 1-100 | Default 50 |
| LLM Response (facts) | JSON Schema validation, text length check | Strip HTML/scripts from fact text |

### Data Protection

| Data Type | Protection | Notes |
|-----------|------------|-------|
| Fact text | Derived from anonymized interviews | Keine PII (anonymous_id, nicht User-Name) |
| Embeddings | Numerische Vektoren | Keine direkte Rueckfuehrbarkeit auf Text |

---

## Constraints & Integrations

### Constraints

| Constraint | Technical Implication | Solution |
|------------|----------------------|----------|
| pgvector muss installiert sein | Neue DB-Extension noetig | Migration: `CREATE EXTENSION IF NOT EXISTS vector` |
| OpenRouter Budget | Embedding-Calls kosten Geld | Batch-Embedding (max 100 Texte pro Call), Caching |
| Agglomerative Clustering ist O(n^2) | Skaliert bis ~10.000 Facts | Ausreichend fuer MVP (Hunderte-Tausende Facts) |
| Kein GPU noetig | scikit-learn CPU-basiert | Clustering < 1s fuer 1000 Facts |

### Integrations

| Area | System | Interface | Notes |
|------|--------|-----------|-------|
| LLM (Extraction, Labeling) | OpenRouter | REST API via langchain_openai.ChatOpenAI | Bestehendes Setup, temperature=0.3 |
| Embedding | OpenRouter oder OpenAI direkt | REST API | Modell: text-embedding-3-small (1536d) |
| Clustering | scikit-learn | Python Library | AgglomerativeClustering, cosine_similarity |
| Vector Storage | PostgreSQL + pgvector | SQL mit vector-Operatoren | `<=>` fuer Cosine Distance |
| Existing DB | mvp_interviews | FK Relationship | facts.interview_id -> interviews.id |

---

## Quality Attributes (NFRs)

### From Discovery -> Technical Solution

| Attribute | Target | Technical Approach | Measure |
|-----------|--------|--------------------|---------|
| Extraction Latency | < 15s pro Interview | Async LLM Call, kein Blocking des /end Endpoints | Logging: extraction_duration_ms |
| Clustering Latency | < 30s fuer 1000 Facts | scikit-learn in-memory, keine DB waehrend Compute | Logging: clustering_duration_ms |
| Embedding Latency | < 5s fuer 50 Facts (Batch) | Batch-API-Call, nicht einzeln | Logging: embedding_duration_ms |
| LLM Cost | < $0.10 pro Clustering-Run | Nur Labels (20-30 Calls), nicht pro Fact | LangSmith: Token-Tracking |
| Idempotenz | Re-Extraction aendert nichts | Check: interview already extracted (FK lookup) | Test: double-extract = same facts |
| Determinismus | Gleiche Facts = gleiche Cluster | AgglomerativeClustering ist deterministisch | Test: re-run = same result |

---

## Technology Decisions

### Stack Choices

| Area | Technology | Rationale |
|------|------------|-----------|
| Embedding | OpenAI text-embedding-3-small via OpenRouter | Konsistent mit bestehendem LLM-Setup, gute Qualitaet, 1536d |
| Vector Storage | pgvector (PostgreSQL Extension) | Kein neuer Service, ausreichend fuer MVP-Skala |
| Clustering | scikit-learn AgglomerativeClustering | Kein k noetig (distance_threshold), deterministisch, robust bei kleinen Datasets |
| LLM (Extraction/Labeling) | Claude Sonnet 4.5 via OpenRouter | Bestehendes Setup, gute JSON-Ausgabe |
| Similarity | scikit-learn cosine_similarity | Standard, schnell, CPU-only |

### Trade-offs

| Decision | Pro | Con | Mitigation |
|----------|-----|-----|------------|
| Agglomerative statt HDBSCAN | Deterministisch, robust bei <500 Facts, kein k noetig | O(n^2) Speicher, nicht fuer >10k Facts | Fuer MVP ausreichend, spaeter HDBSCAN oder Mini-Batch wenn noetig |
| pgvector statt Qdrant/Pinecone | Kein neuer Service, SQL-basiert, konsistent | Weniger Features (kein Filtering, kein Sharding) | Fuer Hunderte-Tausende Vektoren ausreichend |
| Summary-as-Centroid statt Mean-Embedding | Semantisch praeziser, filtert Noise, interpretierbar | Extra LLM-Call pro Cluster | LLM-Call ist guenstig, Qualitaetsgewinn rechtfertigt Kosten |
| Async Post-Interview statt Sync | /end Endpoint bleibt schnell, User wartet nicht | Eventual Consistency (Facts spaeter verfuegbar) | Fuer Dashboard-Use-Case akzeptabel |
| Flat Clusters statt Hierarchisch | Einfacher zu implementieren und verstehen | Weniger Ausdruck (kein "Navigation > Suche > Filterung") | Hierarchie als spaeteres Upgrade (Out of Scope) |

---

## Risks & Assumptions

### Assumptions

| Assumption | Technical Validation | Impact if Wrong |
|------------|---------------------|-----------------|
| pgvector ist auf dem PostgreSQL-Server installierbar | Migration testen | Fallback: Embeddings als JSONB-Array speichern, Similarity in Python berechnen |
| OpenRouter unterstuetzt Embedding-API | API-Docs pruefen, ggf. direkt OpenAI nutzen | Zweiten API-Key konfigurieren |
| Agglomerative Clustering konvergiert fuer Interview-Facts | Test mit 20-50 echten Facts | Schwellwert anpassen, ggf. HDBSCAN als Fallback |
| LLM gibt valides JSON fuer Fact Extraction zurueck | Structured Output / JSON Mode nutzen | Retry mit vereinfachtem Prompt, Regex-Fallback-Parser |
| 10-30 Cluster sind ausreichend fuer MVP-Skala | Review mit Product Owner nach erstem Lauf | Threshold anpassen (kleiner = mehr Cluster) |

### Risks & Mitigation

| Risk | Likelihood | Impact | Technical Mitigation | Fallback |
|------|------------|--------|---------------------|----------|
| LLM extrahiert zu viele/zu wenige Facts | Medium | Medium | Prompt iterieren, Max/Min-Regeln im Prompt | Manuelle Review + Re-Extraction |
| Cluster sind semantisch unsinnig | Low | High | Distanz-Schwellwert tunen, LLM-Labels als Plausibilitaets-Check | Product Owner reviewed Cluster, Schwellwert anpassen |
| pgvector Performance bei Vektorsuche | Low | Low | HNSW-Index ab >1000 Vektoren | ivfflat-Index als Alternative |
| OpenRouter Embedding-Kosten explodieren | Low | Medium | Batch-Calls, Caching, nur neue Facts embedden | Wechsel zu lokalem Modell (all-MiniLM) |
| Clustering dauert zu lange (>60s) | Low | Medium | Profiling, ggf. Pre-Filter auf aktive Cluster | Mini-Batch Variante implementieren |

---

## New File Structure

```
backend/app/insights/
    __init__.py          (exists)
    summary.py           (exists -- unchanged)
    extraction.py        (NEW -- FactExtractionService)
    embedding.py         (NEW -- EmbeddingService)
    clustering.py        (NEW -- ClusteringService)
    labeling.py          (NEW -- ClusterLabeler)
    assigner.py          (NEW -- IncrementalAssigner)
    repository.py        (NEW -- InsightsRepository: facts, clusters, runs)

backend/app/api/
    insights_routes.py   (NEW -- /api/insights/* endpoints)
    insights_schemas.py  (NEW -- Pydantic DTOs)

backend/migrations/
    002_create_facts_clusters.sql  (NEW -- pgvector, tables, indexes)
```

---

## Open Questions

| # | Question | Options | Recommended | Decision |
|---|----------|---------|-------------|----------|
| 1 | Soll Extraction automatisch nach Interview-End laufen? | A) Ja, async Background-Task B) Nein, nur manuell/batch | A) Async -- zeitnah, kein manueller Aufwand | -- |
| 2 | Welcher HNSW Index-Typ fuer pgvector? | A) ivfflat (schneller Build) B) hnsw (schnellere Queries) | B) HNSW -- Queries sind haeufiger als Inserts | -- |
| 3 | Wie viele representative Facts pro Cluster fuer Labeling? | A) 5 B) 10 C) Alle (wenn <20) | B) 10 -- genug Kontext ohne zu viele Tokens | -- |

---

## Research Log

| Date | Area | Finding |
|------|------|---------|
| 2026-03-01 | Web | k-LLMmeans Paper: Summary-as-Centroid outperforms mean-embedding, Mini-Batch variant enables streaming |
| 2026-03-01 | Web | LLM-MemCluster: SOTA accuracy but O(n) LLM calls, nicht kosteneffizient fuer uns |
| 2026-03-01 | Web | pgvector: HNSW-Index unterstuetzt Cosine Distance nativ, `vector <=> vector` Operator |
| 2026-03-01 | Web | scikit-learn AgglomerativeClustering: `distance_threshold` Parameter eliminiert k-Vorgabe |
| 2026-03-01 | Codebase | SummaryService nutzt temperature=0.3 -- selbes Pattern fuer Extraction/Labeling |
| 2026-03-01 | Codebase | Repository-Pattern mit Raw SQL ist Standard -- InsightsRepository folgt demselben Muster |

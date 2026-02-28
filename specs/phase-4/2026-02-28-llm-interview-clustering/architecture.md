# Feature: LLM Interview Clustering

**Epic:** Insights Pipeline (Dashboard + Clustering)
**Status:** Draft
**Discovery:** `discovery.md` (same folder)
**Derived from:** Discovery constraints, NFRs, and risks

---

## Problem & Solution

**Problem:**
- Interviews werden gefuehrt, Summaries generiert — aber keine Moeglichkeit, Muster ueber mehrere Interviews hinweg zu erkennen
- Bei 100+ Interviews pro Projekt ist manuelle Auswertung nicht skalierbar
- Ohne Clustering kein geschlossener Feedback-to-Decision Loop

**Solution:**
- LLM-basierte Clustering-Pipeline (TNT-LLM + Clio + GoalEx Hybrid)
- LangGraph StateGraph mit Self-Correction Loop
- Projekt-basiertes Scoping mit eigenem Research-Ziel und Taxonomie
- Dashboard (Next.js) mit Card-basierter Cluster-Uebersicht und Drill-Down

**Business Value:**
- Schliesst den Feedback-to-Decision Loop
- Skaliert von 1 auf 100+ Interviews ohne manuellen Aufwand
- Keine Vektordatenbanken noetig — pure LLM-Intelligenz

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
| Dashboard: Card-basierte Cluster-Uebersicht, Drill-Down, Taxonomy-Editing |
| Live-Updates im Dashboard via SSE |
| JWT Auth fuer Dashboard-Zugang |
| Inkrementelles Clustering + manuelle Full Re-Cluster Option |
| REST API Export Endpoint |

| Out of Scope |
|--------------|
| Cross-Projekt Clustering |
| Vektordatenbanken / Embeddings / HDBSCAN |
| Voice-Transkription |
| Email-Einladungen |
| CSV/PDF Export (nur API Endpoint in V1) |
| Nutzer-Rollen / Team-Management |
| Session Recordings / Clarity Integration |
| Hierarchisches Clustering (flach fuer MVP) |

---

## API Design

### Overview

| Aspect | Specification |
|--------|---------------|
| Style | REST (JSON) |
| Base URL | `/api` (same FastAPI app) |
| Authentication | JWT Bearer token (`Authorization: Bearer <token>`) |
| Rate Limiting | None for MVP (single-user) |
| Versioning | None for MVP |

### Endpoints — Auth

| Method | Path | Request | Response | Auth | Business Logic |
|--------|------|---------|----------|------|----------------|
| POST | `/api/auth/register` | `RegisterRequest` | `AuthResponse` | No | Create user, hash password, return JWT |
| POST | `/api/auth/login` | `LoginRequest` | `AuthResponse` | No | Validate credentials, return JWT |
| GET | `/api/auth/me` | — | `UserResponse` | Yes | Return current user from JWT |

### Endpoints — Projects

| Method | Path | Request | Response | Auth | Business Logic |
|--------|------|---------|----------|------|----------------|
| POST | `/api/projects` | `CreateProjectRequest` | `ProjectResponse` | Yes | Create project owned by current user |
| GET | `/api/projects` | — | `list[ProjectListItem]` | Yes | List user's projects, sorted by updated_at desc |
| GET | `/api/projects/{id}` | — | `ProjectResponse` | Yes (owner) | Project with aggregated counts |
| PUT | `/api/projects/{id}` | `UpdateProjectRequest` | `ProjectResponse` | Yes (owner) | Update general settings |
| PUT | `/api/projects/{id}/models` | `UpdateModelsRequest` | `ProjectResponse` | Yes (owner) | Update model configuration |
| PUT | `/api/projects/{id}/extraction-source` | `ChangeSourceRequest` | `ProjectResponse` | Yes (owner) | Change source, optionally re-extract |
| DELETE | `/api/projects/{id}` | — | `204 No Content` | Yes (owner) | Cascade delete all project data |

### Endpoints — Interview Assignment

| Method | Path | Request | Response | Auth | Business Logic |
|--------|------|---------|----------|------|----------------|
| GET | `/api/projects/{id}/interviews` | — | `list[InterviewAssignment]` | Yes (owner) | List assigned interviews with status |
| GET | `/api/projects/{id}/interviews/available` | — | `list[AvailableInterview]` | Yes (owner) | Interviews not in any project |
| POST | `/api/projects/{id}/interviews` | `AssignRequest` | `list[InterviewAssignment]` | Yes (owner) | Assign interviews, trigger pipeline |
| POST | `/api/projects/{id}/interviews/{iid}/retry` | — | `InterviewAssignment` | Yes (owner) | Retry failed extraction/clustering |

### Endpoints — Clusters

| Method | Path | Request | Response | Auth | Business Logic |
|--------|------|---------|----------|------|----------------|
| GET | `/api/projects/{id}/clusters` | — | `list[ClusterResponse]` | Yes (owner) | List clusters, sorted by fact_count desc |
| GET | `/api/projects/{id}/clusters/{cid}` | — | `ClusterDetailResponse` | Yes (owner) | Cluster with facts + quotes |
| PUT | `/api/projects/{id}/clusters/{cid}` | `RenameRequest` | `ClusterResponse` | Yes (owner) | Rename (no re-clustering) |
| POST | `/api/projects/{id}/clusters/merge` | `MergeRequest` | `MergeResponse` | Yes (owner) | Move facts, delete source, undo window |
| POST | `/api/projects/{id}/clusters/merge/undo` | `UndoMergeRequest` | `ClusterResponse` | Yes (owner) | Restore within 30s window |
| POST | `/api/projects/{id}/clusters/{cid}/split/preview` | — | `SplitPreviewResponse` | Yes (owner) | LLM proposes sub-clusters |
| POST | `/api/projects/{id}/clusters/{cid}/split` | `SplitConfirmRequest` | `list[ClusterResponse]` | Yes (owner) | Execute split as previewed |

### Endpoints — Facts

| Method | Path | Request | Response | Auth | Business Logic |
|--------|------|---------|----------|------|----------------|
| GET | `/api/projects/{id}/facts` | Query: `cluster_id?`, `unassigned?` | `list[FactResponse]` | Yes (owner) | Facts with optional filter |
| PUT | `/api/projects/{id}/facts/{fid}` | `MoveFactRequest` | `FactResponse` | Yes (owner) | Move fact to cluster (null=unassigned) |
| POST | `/api/projects/{id}/facts/bulk-move` | `BulkMoveRequest` | `list[FactResponse]` | Yes (owner) | Move multiple facts |

### Endpoints — Suggestions

| Method | Path | Request | Response | Auth | Business Logic |
|--------|------|---------|----------|------|----------------|
| GET | `/api/projects/{id}/suggestions` | — | `list[SuggestionResponse]` | Yes (owner) | List active suggestions (status='pending') |
| POST | `/api/projects/{id}/suggestions/{sid}/accept` | — | `204 No Content` | Yes (owner) | Accept suggestion, execute merge/split |
| POST | `/api/projects/{id}/suggestions/{sid}/dismiss` | — | `204 No Content` | Yes (owner) | Dismiss suggestion (status='dismissed') |

### Endpoints — Pipeline & Events

| Method | Path | Request | Response | Auth | Business Logic |
|--------|------|---------|----------|------|----------------|
| POST | `/api/projects/{id}/clustering/recluster` | — | `ReclusterStarted` | Yes (owner) | Full re-cluster (destructive) |
| GET | `/api/projects/{id}/clustering/status` | — | `PipelineStatus` | Yes (owner) | Current pipeline progress |
| GET | `/api/projects/{id}/events` | — | SSE stream | Yes (owner) | Live updates for dashboard |
| GET | `/api/projects/{id}/export` | — | `ExportResponse` | Yes (owner) | Full project data export |

### Data Transfer Objects (DTOs)

| DTO | Fields | Validation | Notes |
|-----|--------|------------|-------|
| `RegisterRequest` | email, password | email format; password min 8 chars | — |
| `LoginRequest` | email, password | email format; password not empty | — |
| `AuthResponse` | access_token, token_type, user | — | token_type = "bearer" |
| `UserResponse` | id, email, created_at | — | — |
| `CreateProjectRequest` | name, research_goal, prompt_context?, extraction_source? | name 1-200; research_goal 1-2000; prompt_context max 5000; extraction_source enum | Default extraction_source = "summary" |
| `UpdateProjectRequest` | name?, research_goal?, prompt_context? | Same as create, all optional | — |
| `UpdateModelsRequest` | model_interviewer?, model_extraction?, model_clustering?, model_summary? | OpenRouter slug format `provider/model-name` | — |
| `ChangeSourceRequest` | extraction_source, re_extract? | enum; bool default false | re_extract triggers full re-extraction |
| `ProjectResponse` | id, name, research_goal, prompt_context, extraction_source, extraction_source_locked, model_*, interview_count, cluster_count, fact_count, created_at, updated_at | — | extraction_source_locked = derived (facts exist) |
| `ProjectListItem` | id, name, interview_count, cluster_count, updated_at | — | For project list cards |
| `AssignRequest` | interview_ids | list[UUID], min 1 | — |
| `InterviewAssignment` | interview_id, date, summary_preview, fact_count, extraction_status, clustering_status | — | summary_preview = first 200 chars |
| `AvailableInterview` | session_id, created_at, summary_preview | — | Interviews not in any project |
| `ClusterResponse` | id, name, summary, fact_count, interview_count, created_at, updated_at | — | — |
| `ClusterDetailResponse` | id, name, summary, fact_count, interview_count, facts, quotes | — | Includes nested facts + quotes |
| `FactResponse` | id, content, quote, confidence, interview_id, interview_date, cluster_id | — | — |
| `RenameRequest` | name | 1-200 chars | — |
| `MergeRequest` | source_cluster_id, target_cluster_id | Both UUID, must be different, same project | — |
| `MergeResponse` | merged_cluster, undo_id, undo_expires_at | — | 30s undo window |
| `UndoMergeRequest` | undo_id | UUID | Must be within 30s |
| `SplitPreviewResponse` | subclusters: list[{name, fact_count, facts}] | — | LLM-proposed split |
| `SplitConfirmRequest` | subclusters: list[{name, fact_ids}] | Min 2 subclusters; all fact_ids must belong to original cluster | — |
| `MoveFactRequest` | cluster_id | UUID or null | null = move to unassigned |
| `BulkMoveRequest` | fact_ids, target_cluster_id? | list[UUID] min 1; null = unassigned | — |
| `SuggestionResponse` | id, type, source_cluster_id, source_cluster_name, target_cluster_id, target_cluster_name, similarity_score, proposed_data, status, created_at | — | type: 'merge'\|'split'; status: 'pending'\|'accepted'\|'dismissed' |
| `PipelineStatus` | status, mode?, progress?, current_step? | status: idle/running; mode: incremental/full/null | progress: {total, completed} |
| `ExportResponse` | project, clusters, unassigned_facts, exported_at | — | Full JSON export |

### SSE Event Types

| Event Type | Data | When |
|------------|------|------|
| `fact_extracted` | `{interview_id, fact_count}` | After fact extraction completes for an interview |
| `clustering_started` | `{mode: "incremental"\|"full"}` | Pipeline starts |
| `clustering_updated` | `{clusters: [{id, name, fact_count}]}` | Cluster assignments changed |
| `clustering_completed` | `{cluster_count, fact_count}` | Pipeline finished successfully |
| `clustering_failed` | `{error, unassigned_count}` | Pipeline failed after retries |
| `suggestion` | `{type: "merge"\|"split", source_cluster_id, ...}` | LLM suggests merge/split |
| `summary_updated` | `{cluster_id}` | Cluster summary regenerated |

---

## Database Schema

### Entities

| Table | Purpose | Key Fields |
|-------|---------|------------|
| `users` | Dashboard user accounts | id, email, password_hash |
| `projects` | Research projects with clustering config | id, name, research_goal, user_id |
| `project_interviews` | Interview-to-project assignments | project_id, interview_id, extraction/clustering status |
| `clusters` | Thematic clusters per project | id, project_id, name, summary |
| `facts` | Atomare Facts extracted from interviews | id, project_id, interview_id, cluster_id, content |
| `cluster_suggestions` | LLM-generated merge/split suggestions | id, project_id, type, status |
| `mvp_interviews` | Existing interview table (unchanged) | session_id, transcript, summary |

### Schema Details

**Table: `users`**

| Column | Type | Constraints | Index |
|--------|------|-------------|-------|
| `id` | UUID | PK, DEFAULT gen_random_uuid() | Yes (PK) |
| `email` | TEXT | NOT NULL, UNIQUE | Yes (UNIQUE) |
| `password_hash` | TEXT | NOT NULL | No |
| `created_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | No |

**Table: `projects`**

| Column | Type | Constraints | Index |
|--------|------|-------------|-------|
| `id` | UUID | PK, DEFAULT gen_random_uuid() | Yes (PK) |
| `user_id` | UUID | NOT NULL, FK → users.id | Yes |
| `name` | TEXT | NOT NULL | No |
| `research_goal` | TEXT | NOT NULL | No |
| `prompt_context` | TEXT | NULLABLE | No |
| `extraction_source` | TEXT | NOT NULL, DEFAULT 'summary', CHECK IN ('summary', 'transcript') | No |
| `model_interviewer` | TEXT | NOT NULL, DEFAULT 'anthropic/claude-sonnet-4' | No |
| `model_extraction` | TEXT | NOT NULL, DEFAULT 'anthropic/claude-haiku-4' | No |
| `model_clustering` | TEXT | NOT NULL, DEFAULT 'anthropic/claude-sonnet-4' | No |
| `model_summary` | TEXT | NOT NULL, DEFAULT 'anthropic/claude-haiku-4' | No |
| `created_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | No |
| `updated_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | No |

**Table: `project_interviews`**

| Column | Type | Constraints | Index |
|--------|------|-------------|-------|
| `project_id` | UUID | NOT NULL, FK → projects.id ON DELETE CASCADE | Yes (PK part) |
| `interview_id` | UUID | NOT NULL, UNIQUE | Yes (UNIQUE) |
| `extraction_status` | TEXT | NOT NULL, DEFAULT 'pending', CHECK IN ('pending', 'running', 'completed', 'failed') | No |
| `clustering_status` | TEXT | NOT NULL, DEFAULT 'pending', CHECK IN ('pending', 'running', 'completed', 'failed') | No |
| `assigned_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | No |
| PK: `(project_id, interview_id)` | | | |

**Table: `clusters`**

| Column | Type | Constraints | Index |
|--------|------|-------------|-------|
| `id` | UUID | PK, DEFAULT gen_random_uuid() | Yes (PK) |
| `project_id` | UUID | NOT NULL, FK → projects.id ON DELETE CASCADE | Yes |
| `name` | TEXT | NOT NULL | No |
| `summary` | TEXT | NULLABLE | No |
| `fact_count` | INTEGER | NOT NULL, DEFAULT 0 | No |
| `interview_count` | INTEGER | NOT NULL, DEFAULT 0 | No |
| `created_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | No |
| `updated_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | No |

**Table: `facts`**

| Column | Type | Constraints | Index |
|--------|------|-------------|-------|
| `id` | UUID | PK, DEFAULT gen_random_uuid() | Yes (PK) |
| `project_id` | UUID | NOT NULL, FK → projects.id ON DELETE CASCADE | Yes |
| `interview_id` | UUID | NOT NULL | Yes |
| `cluster_id` | UUID | NULLABLE, FK → clusters.id ON DELETE SET NULL | Yes |
| `content` | TEXT | NOT NULL | No |
| `quote` | TEXT | NULLABLE | No |
| `confidence` | FLOAT | NULLABLE | No |
| `created_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | No |

**Table: `cluster_suggestions`**

| Column | Type | Constraints | Index |
|--------|------|-------------|-------|
| `id` | UUID | PK, DEFAULT gen_random_uuid() | Yes (PK) |
| `project_id` | UUID | NOT NULL, FK → projects.id ON DELETE CASCADE | Yes |
| `type` | TEXT | NOT NULL, CHECK IN ('merge', 'split') | No |
| `source_cluster_id` | UUID | NOT NULL, FK → clusters.id ON DELETE CASCADE | No |
| `target_cluster_id` | UUID | NULLABLE, FK → clusters.id ON DELETE CASCADE | No |
| `similarity_score` | FLOAT | NULLABLE | No |
| `proposed_data` | JSONB | NULLABLE | No |
| `status` | TEXT | NOT NULL, DEFAULT 'pending', CHECK IN ('pending', 'accepted', 'dismissed') | No |
| `created_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | No |

### Relationships

| From | To | Relationship | Cascade |
|------|-----|--------------|---------|
| `projects` | `users` | N:1 (many projects per user) | RESTRICT on delete |
| `project_interviews` | `projects` | N:1 | CASCADE on delete |
| `project_interviews.interview_id` | `mvp_interviews.session_id` | N:1 (logical, no FK) | — (cross-concern reference) |
| `clusters` | `projects` | N:1 | CASCADE on delete |
| `facts` | `projects` | N:1 | CASCADE on delete |
| `facts` | `clusters` | N:1 (nullable) | SET NULL on delete |
| `cluster_suggestions` | `projects` | N:1 | CASCADE on delete |
| `cluster_suggestions` | `clusters` | N:1 (source) | CASCADE on delete |

**Note on `interview_id`:** `project_interviews.interview_id` and `facts.interview_id` reference `mvp_interviews.session_id` logically, but no FK constraint is enforced. This keeps the existing `mvp_interviews` table decoupled. Application-level validation ensures referential integrity.

**Note on `project_interviews.interview_id` UNIQUE:** Enforces "one interview can only belong to one project" business rule at DB level.

---

## Server Logic

### Services & Processing

| Service | Responsibility | Input | Output | Side Effects |
|---------|----------------|-------|--------|--------------|
| `AuthService` | JWT token management, password hashing | Credentials | JWT token | User row in DB |
| `ProjectService` | Project CRUD, count aggregation | DTOs | Project data | DB writes, cascade deletes |
| `InterviewAssignmentService` | Assign/unassign interviews, list available | Project ID + interview IDs | Assignment records | DB writes, triggers pipeline |
| `FactExtractionService` | Extract atomic facts from interview text via LLM | Interview text, research_goal | List of facts | DB writes (facts), SSE events |
| `ClusteringService` | Orchestrate clustering pipeline (incremental + full) | Project ID, mode | Cluster assignments | DB writes, SSE events, suggestions |
| `ClusteringGraph` | LangGraph StateGraph: assign, validate, refine | Facts + clusters + research_goal | Assignments + new clusters | None (pure computation) |
| `TaxonomyService` | Merge, split, rename operations | Cluster IDs, parameters | Updated clusters | DB writes, summary regeneration |
| `SummaryGenerationService` | Generate/regenerate cluster summaries via LLM | Cluster facts, research_goal | Summary text | DB writes |
| `SseEventBus` | Publish/subscribe SSE events per project | Events | — | Event delivery to subscribers |
| `ExportService` | Compile full project data for API export | Project ID | ExportResponse | None (read-only) |

### Business Logic Flows

**Incremental Clustering (after interview completion):**

```
InterviewService.end()
    → Event: interview_completed(project_id, interview_id)
    → ClusteringService.process_interview(project_id, interview_id)
        → [1] FactExtractionService.extract(interview_text, research_goal, model_extraction)
            → LLM call → parse JSON → save facts to DB
            → SSE: fact_extracted
        → [2] ClusteringGraph.invoke(mode="incremental", facts, existing_clusters, research_goal)
            → assign_facts node: LLM assigns new facts to existing clusters or proposes new
            → validate_quality node: LLM reviews assignments
            → refine_clusters node: LLM corrects (if needed, max 3 loops)
            → generate_summaries node: LLM regenerates affected cluster summaries
            → check_suggestions node: LLM checks for merge/split opportunities
        → [3] Save assignments + clusters + summaries to DB
        → [4] Update denormalized counts (fact_count, interview_count)
        → SSE: clustering_completed
```

**Full Re-Cluster (manual trigger):**

```
POST /api/projects/{id}/clustering/recluster
    → ClusteringService.full_recluster(project_id)
        → [1] Delete all clusters, reset all fact.cluster_id to NULL
        → SSE: clustering_started(mode="full")
        → [2] Load all facts for project
        → [3] ClusteringGraph.invoke(mode="full", all_facts, research_goal)
            → generate_taxonomy node: Mini-batch facts → LLM generates initial taxonomy
            → assign_facts node: LLM classifies all facts against taxonomy
            → validate_quality node: LLM reviews
            → refine_clusters node: (if needed, max 3 loops)
            → generate_summaries node: All cluster summaries
        → [4] Save new clusters + assignments + summaries to DB
        → SSE: clustering_completed
```

**Merge Cluster (with undo):**

```
POST /api/projects/{id}/clusters/merge
    → TaxonomyService.merge(source_id, target_id)
        → [1] Move all facts from source to target
        → [2] Store undo record in memory (30s TTL)
        → [3] Delete source cluster
        → [4] Regenerate target summary (background)
        → [5] Update denormalized counts
        → Return: merged_cluster + undo_id + undo_expires_at

POST /api/projects/{id}/clusters/merge/undo (within 30s)
    → TaxonomyService.undo_merge(undo_id)
        → [1] Restore source cluster from undo record
        → [2] Move facts back to source
        → [3] Regenerate both summaries (background)
```

**Split Cluster (two-step):**

```
POST /api/projects/{id}/clusters/{cid}/split/preview
    → TaxonomyService.preview_split(cluster_id)
        → LLM analyzes facts → proposes sub-clusters
        → Return: proposed sub-clusters with fact assignments

POST /api/projects/{id}/clusters/{cid}/split
    → TaxonomyService.execute_split(cluster_id, subclusters)
        → [1] Create new clusters from proposal
        → [2] Reassign facts to new clusters
        → [3] Delete original cluster
        → [4] Generate summaries for new clusters (background)
        → [5] Update denormalized counts
```

### LangGraph ClusteringGraph Design

**State:**

```
ClusteringState(TypedDict):
    project_id: str
    research_goal: str
    prompt_context: str | None
    mode: Literal["incremental", "full"]
    model_clustering: str           # OpenRouter model slug
    model_summary: str              # OpenRouter model slug
    facts: list[dict]               # {id, content, interview_id}
    existing_clusters: list[dict]   # {id, name, summary}
    assignments: list[dict]         # {fact_id, cluster_id | new_cluster_name}
    new_clusters: list[dict]        # {name, fact_ids}
    quality_ok: bool
    iteration: int
    suggestions: list[dict]         # merge/split suggestions
    summaries: dict[str, str]       # cluster_id → summary
```

**Graph:**

```
                    ┌─────────────────────────────────────────────────┐
                    │              ClusteringGraph                     │
                    │                                                  │
  mode="full" ───► │  generate_taxonomy ──► assign_facts              │
                    │                         │                        │
  mode="incr" ───► │  ──────────────────► assign_facts               │
                    │                         │                        │
                    │                    validate_quality              │
                    │                    /            \                │
                    │              quality_ok    quality_issues         │
                    │                 │            (iteration<3)       │
                    │                 │               │                │
                    │                 │         refine_clusters ──┐    │
                    │                 │                           │    │
                    │                 ▼                           │    │
                    │          generate_summaries ◄───────────────┘    │
                    │                 │                                │
                    │           check_suggestions                      │
                    │                 │                                │
                    │                END                               │
                    └─────────────────────────────────────────────────┘
```

**Node Responsibilities:**

| Node | LLM Call | Input | Output |
|------|----------|-------|--------|
| `generate_taxonomy` | model_clustering | All facts in mini-batches (20/batch) + research_goal | Initial cluster names + descriptions |
| `assign_facts` | model_clustering | Facts + existing clusters + research_goal + prompt_context | Assignments (fact→cluster), new cluster proposals |
| `validate_quality` | model_clustering | Current assignments + cluster contents | quality_ok flag, issue list |
| `refine_clusters` | model_clustering | Assignments + issues from validation | Corrected assignments |
| `generate_summaries` | model_summary | Facts per cluster + research_goal | Summary text per cluster |
| `check_suggestions` | model_clustering | All clusters with fact counts | Merge suggestions (similarity>80%), split suggestions (clusters>8 facts) |

### Validation Rules

| Field | Rule | Error |
|-------|------|-------|
| `project.name` | 1-200 chars, not empty (Pydantic) | "Name must be 1-200 characters" |
| `project.research_goal` | 1-2000 chars, not empty | "Research goal must be 1-2000 characters" |
| `project.prompt_context` | Max 5000 chars | "Prompt context must be max 5000 characters" |
| `project.extraction_source` | "summary" or "transcript" | "Invalid extraction source" |
| `project.model_*` | Non-empty string | "Model slug required" |
| `cluster.name` | 1-200 chars (Pydantic, truncate LLM output if needed) | "Cluster name must be 1-200 characters" |
| `merge: source != target` | Different cluster IDs | "Cannot merge cluster with itself" |
| `merge: same project` | Both clusters in same project | "Clusters must belong to same project" |
| `split: min 2 subclusters` | At least 2 in proposal | "Split must produce at least 2 clusters" |
| `split: all facts covered` | All fact_ids from original cluster | "All facts must be assigned to a subcluster" |
| `assign interview: not in project` | interview_id not in project_interviews | "Interview already assigned to a project" |
| `extraction_source change` | Only via /extraction-source endpoint | "Use extraction-source endpoint to change" |

---

## Security

### Authentication & Authorization

| Area | Mechanism | Notes |
|------|-----------|-------|
| Dashboard Login | JWT Bearer token (HS256) | `JWT_SECRET` from env, `JWT_ALGORITHM=HS256` |
| Token Lifetime | 24h access token | No refresh token for MVP |
| Password Storage | bcrypt hash | `passlib[bcrypt]` |
| Resource Access | Owner-only check | Each project query filtered by `user_id = current_user.id` |
| Interview API | No auth (unchanged) | Widget endpoints remain public (anonymous_id) |
| SSE Auth | JWT in query param | `?token=<jwt>` since EventSource doesn't support headers |

### Data Protection

| Data Type | Protection | Notes |
|-----------|------------|-------|
| Password | bcrypt hash (cost=12) | Never stored or returned in plaintext |
| JWT Secret | Environment variable | Not in code, not in DB |
| Interview Transcripts | Not duplicated | Facts reference interview_id, quotes are excerpts only |
| OpenRouter API Key | Shared env variable | Same key for all users (single-tenant MVP) |

### Input Validation & Sanitization

| Input | Validation | Sanitization |
|-------|------------|--------------|
| All string fields | Pydantic schema with min/max length | `.strip()` whitespace |
| UUID fields | Pydantic UUID type validation | — |
| Email | Pydantic EmailStr | Lowercase normalization |
| LLM responses | JSON schema validation | Fallback to raw text if malformed |
| OpenRouter model slugs | Non-empty string check | — |

### Rate Limiting & Abuse Prevention

| Resource | Limit | Window | Penalty |
|----------|-------|--------|---------|
| Login attempts | 5 | per minute per IP | 429 |
| Full re-cluster | 1 concurrent | per project | 409 (conflict) |
| LLM calls (extraction) | 3 retries | per interview | Status "failed" |
| LLM calls (clustering) | 3 retries | per pipeline run | Status "failed", facts unassigned |

---

## Architecture Layers

### Layer Responsibilities

| Layer | Responsibility | Pattern |
|-------|----------------|---------|
| Routes (`app/api/*_routes.py`) | HTTP handling, request validation, auth check | FastAPI Router |
| Auth Middleware (`app/auth/middleware.py`) | JWT extraction + validation | FastAPI Dependency |
| Services (`app/projects/service.py`, `app/clustering/service.py`) | Business logic, orchestration, event publishing | Service pattern |
| LangGraph (`app/clustering/graph.py`) | LLM orchestration with self-correction loop | StateGraph pattern |
| Repositories (`app/*/repository.py`) | Data access, raw SQL queries | Repository pattern (existing) |
| Event Bus (`app/clustering/events.py`) | SSE pub/sub per project | In-memory asyncio.Queue |
| Background Tasks | Pipeline execution (non-blocking) | asyncio.create_task (existing pattern) |

### Data Flow

```
┌──────────┐     ┌──────────────┐     ┌──────────────┐     ┌───────────┐
│ Dashboard │────▶│ FastAPI Route │────▶│   Service    │────▶│Repository │
│ (Next.js) │◀───│  + Auth MW    │◀───│              │◀───│  (raw SQL) │
└──────────┘     └──────────────┘     └──────────────┘     └───────────┘
     ▲                                       │                    │
     │ SSE                                   ▼                    ▼
     │                              ┌──────────────┐     ┌───────────┐
     └──────────────────────────────│  SSE Event   │     │PostgreSQL │
                                    │    Bus       │     │           │
                                    └──────────────┘     └───────────┘
                                           ▲
                                           │
                                    ┌──────────────┐     ┌───────────┐
                                    │  Clustering   │────▶│ OpenRouter│
                                    │  Graph (LG)  │◀───│  (LLM)    │
                                    └──────────────┘     └───────────┘
```

**Interview → Clustering Trigger:**

```
Widget → POST /api/interview/end
    → InterviewService.end()
        → Saves transcript + summary to mvp_interviews
        → Checks if interview is in a project (project_interviews lookup)
        → If yes: asyncio.create_task(ClusteringService.process_interview(...))
```

### Error Handling Strategy

| Error Type | Handling | User Response | Logging |
|------------|----------|---------------|---------|
| Validation (400) | Pydantic validation error | Field-level error messages | Debug |
| Not Found (404) | Resource lookup returns None | "Resource not found" | Info |
| Unauthorized (401) | JWT invalid/expired | "Authentication required" | Warning |
| Forbidden (403) | Owner check fails | "Access denied" | Warning |
| Conflict (409) | Duplicate assignment, concurrent recluster | Specific conflict message | Info |
| LLM Timeout | asyncio.wait_for timeout | Pipeline status "failed" + SSE event | Error |
| LLM Malformed Response | JSON parse error | Retry (up to 3x), then "failed" | Error |
| DB Error | SQLAlchemy exception | 500 "Internal error" | Error + alert |

---

## Migration Map

> Existing files that need modification to integrate clustering.

| Existing File | Current Pattern | Target Pattern | Specific Changes |
|---|---|---|---|
| `backend/app/interview/service.py` | `end()` saves transcript + summary, returns result | `end()` additionally checks project assignment and triggers clustering pipeline | Add: after `complete_session()`, lookup `project_interviews` by interview_id. If found, call `asyncio.create_task(clustering_service.process_interview(project_id, interview_id))` |
| `backend/app/config/settings.py` | Settings for interviewer LLM + DB + LangSmith | Extended with clustering pipeline + auth settings | Add: `clustering_max_retries: int = 3`, `clustering_batch_size: int = 20`, `clustering_llm_timeout_seconds: int = 120`, `clustering_pipeline_timeout_seconds: int = 600`, `jwt_secret: str` (already exists in env), `jwt_algorithm: str = "HS256"` (already exists in env) |
| `backend/app/api/dependencies.py` | Singleton `_interview_service` | Extended with new service singletons | Add: `get_project_service()`, `get_clustering_service()`, `get_auth_service()`, `get_sse_event_bus()` following existing singleton pattern |
| `backend/app/main.py` | Registers `interview_router` only | Registers additional routers | Add: `app.include_router(project_router)`, `app.include_router(cluster_router)`, `app.include_router(auth_router)`, `app.include_router(sse_router)` |
| `backend/requirements.txt` | Core dependencies (unpinned) | Extended with auth deps + version pinning | Add: `python-jose[cryptography]==3.3.0`, `passlib[bcrypt]==1.7.4`. Pin existing: `fastapi==0.133.1`, `langgraph==1.0.9`, `sse-starlette==3.2.0` |
| `.env.example` | Template for environment variables | Extended with clustering + auth env vars | Add: `JWT_SECRET=<generate-random-secret>`, `JWT_ALGORITHM=HS256`, `CLUSTERING_MAX_RETRIES=3`, `CLUSTERING_BATCH_SIZE=20`, `CLUSTERING_LLM_TIMEOUT_SECONDS=120`, `CLUSTERING_PIPELINE_TIMEOUT_SECONDS=600` |

### New Files

| New File | Purpose |
|----------|---------|
| `backend/migrations/002_create_clustering_tables.sql` | DDL for users, projects, clusters, facts, project_interviews, cluster_suggestions |
| `backend/app/auth/service.py` | AuthService: register, login, verify JWT |
| `backend/app/auth/middleware.py` | JWT dependency for protected routes |
| `backend/app/api/auth_routes.py` | Auth endpoints (register, login, me) |
| `backend/app/api/project_routes.py` | Project CRUD + interview assignment endpoints |
| `backend/app/api/cluster_routes.py` | Cluster, fact, merge/split endpoints |
| `backend/app/api/sse_routes.py` | SSE event stream endpoint |
| `backend/app/projects/service.py` | ProjectService |
| `backend/app/projects/repository.py` | ProjectRepository |
| `backend/app/clustering/service.py` | ClusteringService (pipeline orchestrator) |
| `backend/app/clustering/graph.py` | ClusteringGraph (LangGraph StateGraph) |
| `backend/app/clustering/extraction.py` | FactExtractionService |
| `backend/app/clustering/taxonomy.py` | TaxonomyService (merge/split/rename) |
| `backend/app/clustering/summaries.py` | SummaryGenerationService (cluster summaries) |
| `backend/app/clustering/prompts.py` | LLM prompt templates for clustering |
| `backend/app/clustering/events.py` | SseEventBus (in-memory pub/sub) |
| `dashboard/` | Next.js 16 application (complete new frontend) |

---

## Constraints & Integrations

### Constraints

| Constraint (from Discovery) | Technical Implication | Solution |
|------------|----------------------|----------|
| 100+ Interviews pro Projekt | LLM calls must scale; no full-batch processing | Mini-batch processing (20 facts/batch), incremental clustering (not full re-cluster on every interview) |
| Clustering blockiert nicht Interview-Ausfuehrung | Pipeline must be async/background | `asyncio.create_task()` for pipeline, matching existing TimeoutManager pattern |
| Ein Interview nur einem Projekt zugeordnet | Unique constraint needed | `UNIQUE(interview_id)` on `project_interviews` table |
| Extraction Source gesperrt nach ersten Facts | Application-level lock needed | Derived check: `COUNT(facts WHERE project_id) > 0` → source locked. Change only via explicit endpoint with confirmation |
| Max 3 Retries fuer LLM-Calls | Circuit breaker for LLM failures | Retry counter in pipeline state, status "failed" after 3 attempts |
| Clustering LLM Timeout separate from Interview Timeout | Clustering calls process larger payloads than single interview turns | `clustering_llm_timeout_seconds=120` (vs `llm_timeout_seconds=30` for interviewer); `clustering_pipeline_timeout_seconds=600` for entire pipeline |
| Rename loest kein Re-Clustering aus | Differentiate rename from structural changes | `PUT /clusters/{id}` only updates name field, no pipeline trigger |
| Merge-Undo innerhalb 30 Sekunden | Temporary state storage needed | In-memory dict with TTL (matching existing `self._sessions` pattern in InterviewService) |
| Flaches Clustering (keine Hierarchie) | Single cluster level only | `facts.cluster_id` → `clusters.id` (one level, no parent_cluster_id) |

### Integrations

| Area | System / Capability | Interface | Version | Notes |
|------|----------------------|-----------|---------|-------|
| LLM Gateway | OpenRouter | REST API via `langchain-openai.ChatOpenAI(base_url=...)` | API v1 (stable) | Same pattern as existing InterviewGraph |
| LLM Orchestration | LangGraph | `StateGraph`, `MemorySaver`, conditional edges | 1.0.9 (PyPI, Feb 2026) | Existing dependency, extends with multi-node graph |
| LLM Bindings | langchain-openai | `ChatOpenAI` class | Existing in requirements.txt | Reused for all LLM calls |
| Database | PostgreSQL | SQLAlchemy async + asyncpg | SQLAlchemy 2.0.47, asyncpg (existing) | Same DB, new tables, raw SQL pattern |
| SSE Streaming | sse-starlette | `EventSourceResponse` | 3.2.0 (PyPI, Jan 2026) | Existing dependency, new SSE endpoint for dashboard |
| Web Framework | FastAPI | Routers, dependencies, Pydantic schemas | 0.133.1 (PyPI, Feb 2026) | Existing, add new routers |
| Dashboard Frontend | Next.js | App Router, Server Components | 16.1.6 (npm, Feb 2026) | New application in `dashboard/` folder |
| Dashboard Styling | Tailwind CSS | CSS-first configuration (v4) | 4.1.18 (existing in widget) | Reuse design tokens from widget |
| Dashboard Language | TypeScript | Strict mode | 5.9.3 (existing in widget) | — |
| Dashboard React | React | Server + Client Components | 19.x (bundled with Next.js 16) | — |
| Auth Tokens | python-jose | JWT encode/decode (HS256) | 3.3.0 (PyPI) | New dependency |
| Password Hashing | passlib | bcrypt hashing | 1.7.4 (PyPI) | New dependency |
| Docker | PostgreSQL 16 Alpine | docker-compose.yml | 16-alpine (existing) | No changes, same DB |
| Tracing | LangSmith | Automatic trace collection | Existing env config | Clustering traces in same project |

---

## Quality Attributes (NFRs)

### From Discovery → Technical Solution

| Attribute | Target | Technical Approach | Measure / Verify |
|-----------|--------|--------------------|------------------|
| Pipeline Latency | Incremental: <30s per interview; Full re-cluster: <5min for 100 interviews | Incremental = only new facts; mini-batch (20/batch); async background task; `clustering_llm_timeout_seconds=120` per LLM call; `clustering_pipeline_timeout_seconds=600` total | Measure with LangSmith traces, SSE progress events |
| Scalability | 100+ interviews per project | Mini-batch processing, incremental-only by default, denormalized counts | Load test with 100 interviews |
| Reliability | Pipeline failures don't lose data | Facts saved before clustering; failed status with retry; self-correction loop | Integration tests for failure scenarios |
| Responsiveness | Dashboard feels live | SSE events for every pipeline state change; optimistic UI updates | E2E test: interview end → dashboard update <5s |
| Data Integrity | No orphaned facts, correct counts | DB cascades, denormalized count recalculation after each operation | SQL constraints + count reconciliation job |
| LLM Quality | Coherent clusters, meaningful summaries | Self-correction loop (max 3 iterations), goal-driven prompts (GoalEx pattern) | Manual review of cluster quality |
| Cost Efficiency | Minimize LLM token usage | Tiered models (Haiku for extraction/summary, Sonnet for clustering); incremental over full | Track token usage per pipeline run via LangSmith |

### Monitoring & Observability

| Metric | Type | Target | Alert |
|--------|------|--------|-------|
| Pipeline duration (incremental) | Histogram | < 30s p95 | > 60s |
| Pipeline duration (full recluster) | Histogram | < 5min p95 | > 10min |
| LLM call failures | Counter | < 5% | > 10% in 5min window |
| Clustering quality (self-correction loops) | Gauge | < 2 avg iterations | Consistently hitting 3 (max) |
| Unassigned facts ratio | Gauge | < 5% | > 20% |
| SSE connection count | Gauge | — | — (informational) |

---

## Risks & Assumptions

### Assumptions

| Assumption | Technical Validation | Impact if Wrong |
|------------|---------------------|-----------------|
| OpenRouter supports all configured model slugs | Validate slug on project save (HEAD call or test invoke) | LLM calls fail; fallback to default slug |
| LLM produces valid JSON for fact extraction and clustering | JSON schema validation + retry on parse failure | Pipeline fails after 3 retries; facts stay unassigned |
| Incremental clustering maintains quality at scale | Self-correction loop catches degradation; merge/split suggestions compensate | Quality degrades; user uses manual full re-cluster |
| 30s is sufficient for merge undo decision | UX research suggests 10-30s for undo windows | User misses undo window; must manually recreate cluster |
| Single-process asyncio is sufficient for MVP | Pipeline runs as asyncio.create_task in same process | Under heavy load, pipeline blocks event loop; migrate to Celery/ARQ |
| Next.js 16 App Router is stable for dashboard | Released Oct 2025, 4 months in production | Fallback to Pages Router or Vite+React |

### Risks & Mitigation

| Risk | Likelihood | Impact | Technical Mitigation | Fallback |
|------|------------|--------|---------------------|----------|
| LLM hallucination in clustering | Medium | Medium | Self-correction loop; goal-driven prompts; user can manually reassign | User manually moves facts between clusters |
| Pipeline timeout on large projects (100+ interviews) | Medium | High | Mini-batch processing; incremental-only default; progress indicator | Increase timeout; reduce batch size; split into multiple runs |
| LLM cost explosion | Low | Medium | Tiered models (Haiku for cheap tasks); incremental over full; track costs via LangSmith | Switch to cheaper models; limit re-cluster frequency |
| SSE connection drops | Medium | Low | Client-side reconnect with exponential backoff; dashboard also fetches via REST | Polling fallback (refresh button) |
| Concurrent pipeline conflicts | Low | Medium | One pipeline per project at a time (mutex via status check) | Queue additional requests, reject with 409 |
| JWT secret compromise | Low | High | Secret in env variable only; bcrypt for passwords | Rotate JWT_SECRET, invalidate all tokens |
| Discovery says "Supabase Auth" but codebase migrated from Supabase | — | — | Use JWT-based auth (JWT_SECRET already configured, Supabase removed) | If Supabase Auth needed later, add as external auth provider |

---

## Technology Decisions

### Stack Choices

| Area | Technology | Rationale |
|------|------------|-----------|
| Dashboard Frontend | Next.js 16 (App Router) | Discovery decision Q4; SSR support; React ecosystem; Vercel deployment option |
| Dashboard Styling | Tailwind CSS 4 | Existing in widget; design token reuse; CSS-first config |
| Backend API | FastAPI (existing) | Same app, new routers; async-first matches pipeline needs |
| LLM Orchestration | LangGraph StateGraph | Existing pattern (InterviewGraph); supports conditional edges for self-correction loop |
| Background Tasks | asyncio.create_task | Existing pattern (TimeoutManager); sufficient for single-instance MVP |
| Auth | JWT (python-jose + passlib) | JWT_SECRET already configured in env; simpler than external auth service |
| Database | PostgreSQL (existing) | Same instance, new tables; no new infrastructure |
| SSE | sse-starlette (existing) | Existing dependency; EventSourceResponse pattern proven |
| Data Access | Raw SQL via SQLAlchemy text() | Existing pattern (InterviewRepository); no ORM overhead |

### Trade-offs

| Decision | Pro | Con | Mitigation |
|----------|-----|-----|------------|
| JWT auth instead of Supabase Auth | Simpler; no external dependency; already configured | No social login; no built-in password reset | Add password reset in later phase; social login out of MVP scope |
| asyncio.create_task instead of Celery | Zero new infrastructure; matches existing patterns | Single-process; no task persistence across restarts | Migrate to ARQ/Celery if scaling needed; pipeline is idempotent (re-run safe) |
| Incremental clustering as default | Fast (<30s); cost-efficient; good UX | Quality may drift over time | Self-correction loop; merge/split suggestions; manual full re-cluster as escape hatch |
| In-memory merge undo (30s TTL) | Simple; no DB overhead for temporary state | Lost on server restart | 30s window is short; restart unlikely in that window; cluster data still in DB |
| No FK from facts/project_interviews to mvp_interviews | Keeps existing table decoupled | No DB-level referential integrity for interview_id | Application-level validation; interviews are immutable after completion |
| Denormalized counts on clusters | Fast reads for dashboard (no COUNT queries) | Must be kept in sync | Update counts in same transaction as fact changes; reconciliation check on project load |
| Next.js separate app (not monorepo) | Clear separation; independent deployment; own node_modules | Two build processes; potential version drift | Shared Tailwind design tokens; dashboard is consumer of backend API only |

---

## Open Questions

| # | Question | Options | Recommended | Decision |
|---|----------|---------|-------------|----------|
| 1 | Auth: JWT (already configured) vs Supabase Auth (Discovery says)? | A) JWT B) Supabase Auth C) Both | A) JWT | **JWT — codebase migrated from Supabase (commit 9e71eca). JWT_SECRET already in env. Simpler for MVP.** |
| 2 | Dashboard deployment: Same origin as backend or separate? | A) Same origin (FastAPI serves static) B) Separate (Next.js standalone) | B) Separate | **Separate — Next.js has own dev server + build. CORS configured for dashboard origin.** |
| 3 | Pipeline state: In-memory only or persist to DB? | A) In-memory B) DB table C) Redis | A) In-memory | **In-memory (asyncio.create_task). Pipeline is idempotent. If interrupted, re-run.** |

---

## Context & Research

### Codebase Evidence

| Pattern | Location | Reuse Strategy |
|---------|----------|----------------|
| LangGraph StateGraph | `backend/app/interview/graph.py` | Copy pattern: StateGraph + nodes + conditional_edges. Extend with multi-node graph for clustering |
| SSE Streaming | `backend/app/api/routes.py` | Same EventSourceResponse pattern. Add project-scoped SSE endpoint |
| OpenRouter LLM | `backend/app/interview/graph.py` (ChatOpenAI) | Same ChatOpenAI(base_url="openrouter") pattern. Per-project model slug from DB |
| Repository (raw SQL) | `backend/app/interview/repository.py` | Same async_sessionmaker + text() + mappings() pattern for new repositories |
| Service orchestration | `backend/app/interview/service.py` | Same pattern: service orchestrates repo + graph + side effects |
| Singleton DI | `backend/app/api/dependencies.py` | Extend with new service singletons |
| Background tasks | `backend/app/interview/timeout.py` | Same asyncio.create_task pattern for pipeline execution |
| Prompt assembly | `backend/app/interview/prompt.py` | Same pattern: template + dynamic context injection |
| Settings | `backend/app/config/settings.py` | Extend BaseSettings with new fields |

### Research Sources (from `research-llm-clustering.md`)

| Source | Pattern Used |
|--------|-------------|
| TNT-LLM (Microsoft, KDD 2024) | Mini-batch taxonomy generation, tiered LLM, LangGraph StateGraph |
| GoalEx (EMNLP 2023) | Goal-driven clustering via `research_goal` parameter |
| Anthropic Clio | Facet/fact extraction pattern, production validation at scale |
| "Text Clustering as Classification" (SIGIR-AP 2025) | Reframe clustering as classification against generated taxonomy |
| Few-Shot Clustering (MIT Press) | Self-correction loop (post-clustering validation) |
| k-LLMmeans (2025) | Incremental/streaming clustering pattern |

---

## Research Log

| Date | Area | Finding |
|------|------|---------|
| 2026-02-28 | Codebase | LangGraph InterviewGraph uses single-node StateGraph with MemorySaver. Clustering needs multi-node graph with conditional edges. |
| 2026-02-28 | Codebase | Repository pattern uses raw SQL with `text()` — no SQLAlchemy ORM models. New tables follow same pattern. |
| 2026-02-28 | Codebase | SSE uses `EventSourceResponse` from sse-starlette. Dashboard needs project-scoped SSE with pub/sub. |
| 2026-02-28 | Codebase | InterviewService.end() is the hook point. Add project_interviews lookup + clustering trigger. |
| 2026-02-28 | Codebase | `JWT_SECRET` and `JWT_ALGORITHM` already in .env — confirms JWT auth intention despite Supabase migration. |
| 2026-02-28 | Codebase | No dashboard/ or frontend/ folder exists. Greenfield for Next.js app. |
| 2026-02-28 | Codebase | Widget uses React 19 + Tailwind 4 + TypeScript 5.9. Dashboard can share design tokens. |
| 2026-02-28 | Codebase | Background tasks via asyncio.create_task (TimeoutManager pattern). Sufficient for MVP pipeline. |
| 2026-02-28 | Versions | Next.js 16.1.6 (Feb 2026), LangGraph 1.0.9, FastAPI 0.133.1, SQLAlchemy 2.0.47, sse-starlette 3.2.0 |
| 2026-02-28 | Versions | python-jose 3.3.0 (JWT), passlib 1.7.4 (bcrypt) — new dependencies for auth |

---

## Q&A Log

| # | Question | Answer |
|---|----------|--------|
| 1 | All Discovery open questions already resolved? | Yes — all 7 questions in Discovery have decisions (OpenRouter config, flat clustering, hybrid re-clustering, Next.js, volle Kontrolle, REST API export). No additional Q&A needed. |
| 2 | Auth approach: Supabase Auth (Discovery) vs JWT (codebase evidence)? | JWT — codebase migrated from Supabase (commit 9e71eca). JWT_SECRET already configured. User bestaetigte JWT. Discovery aktualisiert (6 Stellen). |
| 3 | Background processing: asyncio vs Celery? | asyncio.create_task — matches existing TimeoutManager pattern. No new infrastructure for MVP. |
| 4 | Was passiert nach Merge/Split — Re-Clustering oder nur Summary-Regenerierung? | Nur Summary-Regenerierung. Facts werden bei Merge/Split direkt verschoben. Danach werden Cluster-Summaries neu generiert. Kein erneuter Clustering-Durchlauf. Discovery aktualisiert (3 Stellen). |

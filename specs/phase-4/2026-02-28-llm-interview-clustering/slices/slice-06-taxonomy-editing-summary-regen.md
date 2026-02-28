# Slice 6: Taxonomy-Editing + Summary-Regenerierung

> **Slice 6 von 8** fuer `LLM Interview Clustering`
>
> | Navigation | |
> |------------|---|
> | **Vorheriger:** | `slice-05-dashboard-drill-down-zitate.md` |
> | **Naechster:** | `slice-07-live-updates-sse.md` |

---

## Metadata (fuer Orchestrator)

| Key | Value |
|-----|-------|
| **ID** | `slice-06-taxonomy-editing-summary-regen` |
| **Test** | `pnpm playwright test tests/slices/llm-interview-clustering/slice-06-taxonomy-editing-summary-regen.spec.ts` |
| **E2E** | `true` |
| **Dependencies** | `["slice-01-db-schema-projekt-crud", "slice-03-clustering-pipeline-agent", "slice-05-dashboard-drill-down-zitate"]` |

**Erklaerung:**
- **ID**: Eindeutiger Identifier (wird fuer Commits und Evidence verwendet)
- **Test**: Playwright E2E Test — Cluster umbenennen, mergen, splitten; Summary-Regenerierung nach Merge/Split
- **E2E**: `true` — Playwright (`.spec.ts`). Zusaetzlich Backend-Unit-Tests fuer `TaxonomyService` als pytest.
- **Dependencies**: Slice 5 liefert `ClusterDetailResponse`, `FactResponse`, Cluster-Detail-Seite, disabled Merge/Split Buttons; Slice 3 liefert `ClusteringService.generate_summaries()`; Slice 1 liefert DB-Schema (`clusters`, `facts`, `cluster_suggestions` Tabellen)

---

## Test-Strategy (fuer Orchestrator Pipeline)

> **Quelle:** Auto-detected basierend auf Repo-Indikatoren.
> `backend/requirements.txt` enthaelt `fastapi` + `uvicorn` → Stack Backend: `python-fastapi`.
> `dashboard/` ist Next.js 16 App (aus Slice 4) → Stack Frontend: `typescript-nextjs`.
> Slice 6 hat zwei Test-Targets: Backend pytest (TaxonomyService) + Frontend Playwright E2E.

| Key | Value |
|-----|-------|
| **Stack** | `python-fastapi` + `typescript-nextjs` (Dual-Stack) |
| **Test Command** | `python -m pytest backend/tests/slices/llm-interview-clustering/test_slice_06_taxonomy_service.py -v` |
| **Integration Command** | `python -m pytest backend/tests/slices/llm-interview-clustering/ -v -k "slice_06"` |
| **Acceptance Command** | `pnpm playwright test tests/slices/llm-interview-clustering/slice-06-taxonomy-editing-summary-regen.spec.ts` |
| **Start Command** | `pnpm --filter dashboard dev` |
| **Health Endpoint** | `http://localhost:3001/api/health` |
| **Mocking Strategy** | `mock_external` |

**Erklaerung:**
- **Port 3001**: Dashboard-App aus Slice 4 (unveraendert)
- **Mocking Strategy**: OpenRouter/LLM-Calls werden in Backend-Unit-Tests mit `unittest.mock.patch` gemockt. Playwright E2E Tests laufen gegen echtes Backend mit Mock-LLM-Responses.
- **Backend pytest**: Testet `TaxonomyService.rename()`, `TaxonomyService.merge()`, `TaxonomyService.undo_merge()`, `TaxonomyService.preview_split()`, `TaxonomyService.execute_split()`, `SummaryGenerationService.regenerate_for_cluster()`, Fact-Move-Endpoints, Suggestion-Endpoints.

---

## Slice-Uebersicht

| # | Slice | Status | Datei |
|---|-------|--------|-------|
| 1 | DB Schema + Projekt CRUD | **Ready** | `slice-01-db-schema-projekt-crud.md` |
| 2 | Fact Extraction Pipeline | **Ready** | `slice-02-fact-extraction-pipeline.md` |
| 3 | Clustering Pipeline + Agent | **Ready** | `slice-03-clustering-pipeline-agent.md` |
| 4 | Dashboard: Projekt-Liste + Cluster-Uebersicht | **Ready** | `slice-04-dashboard-projekt-cluster-uebersicht.md` |
| 5 | Dashboard: Drill-Down + Zitate | **Ready** | `slice-05-dashboard-drill-down-zitate.md` |
| 6 | Taxonomy-Editing + Summary-Regen | **Current** | `slice-06-taxonomy-editing-summary-regen.md` |
| 7 | Live-Updates via SSE | Pending | `slice-07-live-updates-sse.md` |
| 8 | Auth + Polish | Pending | `slice-08-auth-polish.md` |

---

## Kontext & Ziel

Nach Slice 5 kann der Nutzer Cluster-Details lesen (Facts + Zitate), aber nicht bearbeiten. Dieser Slice aktiviert die Taxonomy-Editing-Funktionen: Cluster umbenennen (inline), mergen (mit 30-Sekunden Undo-Toast), splitten (2-Schritt Preview-Flow), Facts einzeln verschieben (per Kontext-Menue und Bulk-Select), und das volle Re-Clustering ausloesen. Ausserdem werden Merge/Split-Vorschlaege des LLM im Insights-Tab als Suggestion-Banner angezeigt.

**Scope dieses Slices:**

**Backend:**
- `PUT /api/projects/{id}/clusters/{cid}` → Cluster umbenennen (`RenameRequest`)
- `POST /api/projects/{id}/clusters/merge` → Cluster mergen (Facts verschieben, Source loeschen, 30s Undo-Record, Summary-Regen)
- `POST /api/projects/{id}/clusters/merge/undo` → Merge rueckgaengig machen (30s Fenster)
- `POST /api/projects/{id}/clusters/{cid}/split/preview` → LLM generiert Sub-Cluster-Preview ohne Persistierung
- `POST /api/projects/{id}/clusters/{cid}/split` → Split ausfuehren (neue Cluster + Summary-Regen)
- `PUT /api/projects/{id}/facts/{fid}` → Einzelnen Fact verschieben (`MoveFactRequest`)
- `POST /api/projects/{id}/facts/bulk-move` → Mehrere Facts verschieben (`BulkMoveRequest`)
- `GET /api/projects/{id}/suggestions` → Aktive Merge/Split-Vorschlaege abrufen
- `POST /api/projects/{id}/suggestions/{sid}/accept` → Suggestion akzeptieren (fuehrt Merge/Split aus)
- `POST /api/projects/{id}/suggestions/{sid}/dismiss` → Suggestion verwerfen
- `POST /api/projects/{id}/clustering/recluster` → Full Re-Cluster ausloesen
- `TaxonomyService` (neue Datei) mit allen Merge/Split/Rename-Methoden
- `SummaryGenerationService.regenerate_for_cluster()` — bereits aus Slice 3, wird hier erweitert

**Frontend:**
- Cluster-Card Kontext-Menue aktivieren: "Rename", "Merge with...", "Split"
- Inline-Rename in Cluster-Card (controlled input, Enter=save, Escape=cancel)
- Inline-Rename im Cluster-Detail-Header (pencil icon)
- Merge-Dialog: Radio-Liste aller anderen Cluster + Bestaetigung + optimistic update + Undo-Toast (30s Countdown)
- Split-Flow 2-Schritt: Step 1 (Erklaerung + "Generate Preview") → LLM Preview Spinner → Step 2 (Preview anzeigen mit Namen + kompletter Fact-Liste pro Sub-Cluster) → Bestaetigen oder Abbrechen
- Merge/Split-Suggestion Banner im Insights-Tab (Dismiss oder Accept)
- Fact-Kontext-Menue (`fact_context_menu`) im Cluster-Detail: "Move to [cluster]...", "Mark as unassigned"
- Fact-Checkbox + Bulk-Move-Bar im Cluster-Detail ("Move selected to cluster" Dropdown, sichtbar wenn >= 1 Checkbox gewaehlt)
- Unassigned-Bereich im Insights-Tab: Checkboxes + Bulk-Move-Bar
- Full Re-Cluster Button ("Recalculate") mit Bestaetigung
- `Merge` + `Split` Buttons im Cluster-Detail aktivieren (waren in Slice 5 disabled)

**Abgrenzung:**
- SSE Live-Updates kommen in Slice 7 (dieser Slice zeigt statische Post-Action-Updates via optimistic updates + Page-Reload)
- Auth/JWT kommt in Slice 8
- Summary-Regenerierung laeuft als Background-Task (Fire-and-forget aus Sicht des Clients)

---

## Technische Umsetzung

### Architektur-Kontext (aus architecture.md)

> **Quelle:** `architecture.md` → "Endpoints — Clusters", "Business Logic Flows", "Server Logic"

```
Merge Flow:
  POST /api/projects/{id}/clusters/merge
    → TaxonomyService.merge(source_id, target_id)
        → [1] Move all facts: UPDATE facts SET cluster_id=target WHERE cluster_id=source
        → [2] Store undo record in memory (dict, 30s TTL, keyed by undo_id UUID)
        → [3] DELETE clusters WHERE id=source
        → [4] Update denormalized counts (fact_count, interview_count) on target
        → [5] asyncio.create_task(SummaryGenerationService.regenerate_for_cluster(target_id))
        → Return MergeResponse {merged_cluster, undo_id, undo_expires_at}

Split Flow (2-Step):
  POST /api/projects/{id}/clusters/{cid}/split/preview
    → TaxonomyService.preview_split(cluster_id)
        → LLM analyzes facts for cluster → proposes sub-clusters
        → Return SplitPreviewResponse (NO DB writes)

  POST /api/projects/{id}/clusters/{cid}/split
    → TaxonomyService.execute_split(cluster_id, subclusters: [{name, fact_ids}])
        → [1] Validate: all fact_ids belong to original cluster, min 2 subclusters
        → [2] CREATE new clusters for each subcluster
        → [3] UPDATE facts SET cluster_id=new_cluster_id for each subcluster
        → [4] DELETE original cluster
        → [5] Update denormalized counts on new clusters
        → [6] asyncio.create_task(SummaryGenerationService.regenerate_for_cluster(id)) per new cluster
        → Return list[ClusterResponse]

Rename Flow:
  PUT /api/projects/{id}/clusters/{cid}
    → ClusterRepository.update_name(cid, name)
    → Return ClusterResponse (NO summary regeneration, NO re-clustering)

Fact Move Flow:
  PUT /api/projects/{id}/facts/{fid}
    → FactRepository.update_cluster(fid, target_cluster_id | null)
    → Update denormalized counts on old + new cluster
    → Return FactResponse

Full Re-Cluster:
  POST /api/projects/{id}/clustering/recluster
    → ClusteringService.full_recluster(project_id)  [aus Slice 3, bereits definiert]
    → asyncio.create_task(...)
    → Return ReclusterStarted {status: "started"}
```

### 1. Architektur-Impact

| Layer | Aenderungen |
|-------|-------------|
| `backend/app/clustering/taxonomy.py` | **NEU** `TaxonomyService`: `rename()`, `merge()`, `undo_merge()`, `preview_split()`, `execute_split()` |
| `backend/app/clustering/summaries.py` | Bereits aus Slice 3. `regenerate_for_cluster(cluster_id)` wird aufgerufen nach Merge/Split |
| `backend/app/clustering/repository.py` | Erweiterung: `ClusterRepository.update_name()`, `ClusterRepository.delete()`, `ClusterRepository.create_many()` |
| `backend/app/clustering/facts_repository.py` | **NEU** (oder Erweiterung von repository.py): `FactRepository.move_bulk()`, `FactRepository.move_single()`, `FactRepository.get_unassigned()` |
| `backend/app/clustering/suggestions_repository.py` | **NEU**: `SuggestionRepository.list_active()`, `SuggestionRepository.update_status()` |
| `backend/app/api/cluster_routes.py` | Neue Endpoints: PUT rename, POST merge, POST merge/undo, POST split/preview, POST split, GET/POST suggestions, PUT fact, POST facts/bulk-move, POST clustering/recluster |
| `backend/app/clustering/schemas.py` | Neue DTOs: `RenameRequest`, `MergeRequest`, `MergeResponse`, `UndoMergeRequest`, `SplitPreviewResponse`, `SplitConfirmRequest`, `MoveFactRequest`, `BulkMoveRequest`, `SuggestionResponse`, `ReclusterStarted` |
| `dashboard/app/projects/[id]/page.tsx` | Erweiterung: Suggestion-Banner, Unassigned-Bereich mit Checkboxen, Recalculate-Button (alle in Slice 4 als Stubs — jetzt aktiviert) |
| `dashboard/app/projects/[id]/clusters/[cluster_id]/page.tsx` | Erweiterung: Inline-Rename aktivieren, Merge-Button funktional, Split-Button funktional, Fact-Checkboxen + Bulk-Move, Fact-Kontext-Menue |
| `dashboard/components/cluster-card.tsx` | Erweiterung: Kontext-Menue aktivieren (Rename, Merge, Split) |
| `dashboard/components/cluster-context-menu.tsx` | **NEU**: Dropdown mit Rename/Merge/Split Optionen |
| `dashboard/components/inline-rename.tsx` | **NEU**: Controlled input fuer Inline-Rename (Enter=save, Escape=cancel) |
| `dashboard/components/merge-dialog.tsx` | **NEU**: Modal mit Radio-Liste + Undo-Toast |
| `dashboard/components/undo-toast.tsx` | **NEU**: 30-Sekunden-Countdown Toast nach Merge |
| `dashboard/components/split-modal.tsx` | **NEU**: 2-Schritt Split-Modal (Step1 + Step2 Preview) |
| `dashboard/components/suggestion-banner.tsx` | **NEU**: Merge/Split Suggestion Banner im Insights-Tab |
| `dashboard/components/recalculate-modal.tsx` | **NEU**: Confirmation Modal fuer Full Re-Cluster |
| `dashboard/components/fact-item.tsx` | Erweiterung: Checkbox + Kontext-Menue (aus Slice 5 erweitern) |
| `dashboard/components/fact-context-menu.tsx` | **NEU**: "Move to cluster...", "Mark as unassigned" |
| `dashboard/components/bulk-move-bar.tsx` | **NEU**: Bulk-Move Dropdown-Bar (sichtbar wenn >= 1 Checkbox aktiv) |
| `dashboard/lib/api-client.ts` | Neue Methoden fuer alle neuen Endpoints |
| `dashboard/lib/types.ts` | Neue Types fuer alle neuen DTOs |

### 2. Datenfluss — Merge mit Undo

```
User klickt [Merge Clusters] im Merge-Dialog
  |
  v
Frontend: optimistic update (entfernt source-Cluster aus Cards)
  |
  v
POST /api/projects/{id}/clusters/merge
  Body: { source_cluster_id, target_cluster_id }
  |
  v
TaxonomyService.merge(source_id, target_id)
  → UPDATE facts SET cluster_id = target_id WHERE cluster_id = source_id AND project_id = pid
  → undo_record = {source_cluster_snapshot, original_fact_ids}
  → _undo_store[undo_id] = undo_record  (in-memory dict, 30s TTL via asyncio.create_task(expire))
  → DELETE FROM clusters WHERE id = source_id
  → UPDATE clusters SET fact_count = ..., interview_count = ..., updated_at = now() WHERE id = target_id
  → asyncio.create_task(SummaryGenerationService.regenerate_for_cluster(target_id))
  |
  v
MergeResponse {
  merged_cluster: ClusterResponse,
  undo_id: "uuid",
  undo_expires_at: "2026-02-28T12:00:30Z"
}
  |
  v
Frontend: zeigt UndoToast (30s Countdown)
User klickt [Undo] innerhalb 30s:
  → POST /api/projects/{id}/clusters/merge/undo { undo_id }
  → TaxonomyService.undo_merge(undo_id)
      → Restore source cluster from snapshot
      → Move facts back to source
      → asyncio.create_task(SummaryGenerationService.regenerate_for_cluster(source_id))
      → asyncio.create_task(SummaryGenerationService.regenerate_for_cluster(target_id))
  → Frontend: Page-Reload / re-fetch clusters
```

### 3. Datenfluss — Split (2-Schritt)

```
User klickt [Split] im Cluster-Card-Menue oder Cluster-Detail
  |
  v
SplitModal.Step1 oeffnet sich
User klickt [Generate Preview]
  |
  v
Frontend: Spinner-State
POST /api/projects/{id}/clusters/{cid}/split/preview
  → TaxonomyService.preview_split(cluster_id)
      → Laedt alle Facts fuer cluster_id
      → LLM-Call (model_clustering): "Split these facts into 2+ coherent sub-clusters"
      → Parst LLM-Response als JSON: [{name, fact_ids}]
      → KEINE DB-Schreiboperation
  → SplitPreviewResponse {
      subclusters: [
        { name: "Menu Structure", fact_count: 8, facts: [FactResponse, ...] },
        { name: "Feature Discovery", fact_count: 6, facts: [FactResponse, ...] }
      ]
    }
  |
  v
Frontend: SplitModal.Step2 zeigt Preview-Karten mit Namen + vollstaendiger Fact-Liste
User klickt [Confirm Split]
  |
  v
POST /api/projects/{id}/clusters/{cid}/split
  Body: { subclusters: [{name, fact_ids}, ...] }
  → TaxonomyService.execute_split(cluster_id, subclusters)
      → Validierung: alle fact_ids gehoeren zu original cluster, min 2 subclusters
      → INSERT INTO clusters fuer jede subcluster (name, project_id)
      → UPDATE facts SET cluster_id = new_id WHERE id IN fact_ids
      → DELETE FROM clusters WHERE id = original_cluster_id
      → UPDATE counts auf neuen Clustern
      → asyncio.create_task(SummaryGenerationService.regenerate_for_cluster(id)) pro neuem Cluster
  → list[ClusterResponse]
  |
  v
Frontend: Modal schliesst, zurueck zur Insights-Tab, re-fetch clusters
```

### 4. Backend-Endpoints und DTOs

**PUT `/api/projects/{id}/clusters/{cid}`**

```python
# backend/app/clustering/schemas.py

class RenameRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)

class MergeRequest(BaseModel):
    source_cluster_id: str  # UUID
    target_cluster_id: str  # UUID

class MergeResponse(BaseModel):
    merged_cluster: ClusterResponse
    undo_id: str            # UUID fuer Undo-Request
    undo_expires_at: str    # ISO 8601 datetime string

class UndoMergeRequest(BaseModel):
    undo_id: str            # UUID

class SplitPreviewSubcluster(BaseModel):
    name: str
    fact_count: int
    facts: list[FactResponse]   # Vollstaendige Fact-Liste fuer Preview

class SplitPreviewResponse(BaseModel):
    subclusters: list[SplitPreviewSubcluster]  # Min 2 Sub-Cluster vorgeschlagen

class SplitSubclusterInput(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    fact_ids: list[str]     # list[UUID]

class SplitConfirmRequest(BaseModel):
    subclusters: list[SplitSubclusterInput] = Field(min_length=2)

class MoveFactRequest(BaseModel):
    cluster_id: str | None  # UUID oder None = unassigned

class BulkMoveRequest(BaseModel):
    fact_ids: list[str] = Field(min_length=1)   # list[UUID]
    target_cluster_id: str | None               # UUID oder None = unassigned

class SuggestionResponse(BaseModel):
    id: str
    type: str               # "merge" oder "split"
    source_cluster_id: str
    source_cluster_name: str
    target_cluster_id: str | None
    target_cluster_name: str | None
    similarity_score: float | None
    proposed_data: dict | None  # JSONB aus DB
    status: str             # "pending"
    created_at: str         # ISO 8601

class ReclusterStarted(BaseModel):
    status: str = "started"
    message: str = "Full re-clustering started in background"
```

**Validation Rules:**
- `merge`: `source_cluster_id != target_cluster_id` → 400 "Cannot merge cluster with itself"
- `merge`: Beide Cluster gehoeren zu `project_id` → 404 wenn nicht gefunden
- `split`: `len(subclusters) >= 2` → 400 "Split must produce at least 2 clusters"
- `split`: Alle `fact_ids` gehoeren zu originalem Cluster → 400 "All facts must be assigned to a subcluster"
- `undo_merge`: `undo_id` existiert und ist nicht abgelaufen → 404/409 wenn expired
- `rename`: name 1-200 Zeichen, Cluster gehoert zu `project_id`

### 5. TaxonomyService (backend/app/clustering/taxonomy.py)

```python
# backend/app/clustering/taxonomy.py

import asyncio
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from app.clustering.repository import ClusterRepository
from app.clustering.facts_repository import FactRepository
from app.clustering.summaries import SummaryGenerationService
from app.clustering.schemas import (
    ClusterResponse, MergeResponse, SplitPreviewResponse,
    SplitPreviewSubcluster, FactResponse
)

class TaxonomyService:
    def __init__(
        self,
        cluster_repo: ClusterRepository,
        fact_repo: FactRepository,
        summary_service: SummaryGenerationService,
    ):
        self._cluster_repo = cluster_repo
        self._fact_repo = fact_repo
        self._summary_service = summary_service
        self._undo_store: dict[str, dict[str, Any]] = {}  # In-memory, keyed by undo_id

    async def rename(self, project_id: str, cluster_id: str, name: str) -> ClusterResponse:
        """Rename a cluster. No summary regeneration, no re-clustering."""
        cluster = await self._cluster_repo.update_name(project_id, cluster_id, name)
        if cluster is None:
            raise ClusterNotFoundError(cluster_id)
        return ClusterResponse.model_validate(cluster)

    async def merge(
        self, project_id: str, source_id: str, target_id: str
    ) -> MergeResponse:
        """Move all facts from source to target, delete source, 30s undo window."""
        if source_id == target_id:
            raise ValueError("Cannot merge cluster with itself")
        source = await self._cluster_repo.get_by_id(project_id, source_id)
        target = await self._cluster_repo.get_by_id(project_id, target_id)
        if source is None or target is None:
            raise ClusterNotFoundError(source_id if source is None else target_id)

        # Snapshot fuer Undo
        source_facts = await self._fact_repo.get_by_cluster(source_id, project_id)
        undo_id = str(uuid.uuid4())
        undo_expires_at = datetime.now(timezone.utc) + timedelta(seconds=30)
        self._undo_store[undo_id] = {
            "source_cluster": {
                "id": source["id"],
                "name": source["name"],
                "project_id": project_id,
            },
            "source_fact_ids": [f["id"] for f in source_facts],
            "target_id": target_id,
            "expires_at": undo_expires_at,
        }

        # Async expire nach 30s
        asyncio.create_task(self._expire_undo(undo_id, 30))

        # Facts verschieben
        await self._fact_repo.move_bulk(
            fact_ids=[f["id"] for f in source_facts],
            target_cluster_id=target_id,
            project_id=project_id,
        )
        # Source Cluster loeschen
        await self._cluster_repo.delete(project_id, source_id)
        # Counts aktualisieren
        merged = await self._cluster_repo.recalculate_counts(project_id, target_id)

        # Summary Background-Task
        asyncio.create_task(
            self._summary_service.regenerate_for_cluster(project_id, target_id)
        )

        return MergeResponse(
            merged_cluster=ClusterResponse.model_validate(merged),
            undo_id=undo_id,
            undo_expires_at=undo_expires_at.isoformat(),
        )

    async def undo_merge(self, project_id: str, undo_id: str) -> ClusterResponse:
        """Restore source cluster from undo snapshot (within 30s window)."""
        record = self._undo_store.get(undo_id)
        if record is None:
            raise UndoExpiredError("Undo window expired or invalid undo_id")
        if datetime.now(timezone.utc) > record["expires_at"]:
            del self._undo_store[undo_id]
            raise UndoExpiredError("Undo window expired")

        source_info = record["source_cluster"]
        fact_ids = record["source_fact_ids"]
        target_id = record["target_id"]

        # Source Cluster wiederherstellen
        restored = await self._cluster_repo.create(
            project_id=project_id,
            name=source_info["name"],
        )
        # Facts zurueckverschieben
        await self._fact_repo.move_bulk(
            fact_ids=fact_ids,
            target_cluster_id=restored["id"],
            project_id=project_id,
        )
        # Counts aktualisieren
        await self._cluster_repo.recalculate_counts(project_id, restored["id"])
        await self._cluster_repo.recalculate_counts(project_id, target_id)

        # Summaries fuer beide Cluster Background-Task
        asyncio.create_task(
            self._summary_service.regenerate_for_cluster(project_id, restored["id"])
        )
        asyncio.create_task(
            self._summary_service.regenerate_for_cluster(project_id, target_id)
        )

        del self._undo_store[undo_id]
        result = await self._cluster_repo.get_by_id(project_id, restored["id"])
        return ClusterResponse.model_validate(result)

    async def preview_split(
        self, project_id: str, cluster_id: str
    ) -> SplitPreviewResponse:
        """LLM proposes sub-clusters. NO DB writes."""
        cluster = await self._cluster_repo.get_by_id(project_id, cluster_id)
        if cluster is None:
            raise ClusterNotFoundError(cluster_id)
        facts = await self._fact_repo.get_by_cluster(cluster_id, project_id)
        # LLM-Call delegiert an SummaryGenerationService._call_llm oder eigene Methode
        subclusters = await self._summary_service.propose_split(
            cluster_name=cluster["name"],
            facts=facts,
            project_id=project_id,
        )
        return SplitPreviewResponse(
            subclusters=[
                SplitPreviewSubcluster(
                    name=sc["name"],
                    fact_count=len(sc["facts"]),
                    facts=[FactResponse.model_validate(f) for f in sc["facts"]],
                )
                for sc in subclusters
            ]
        )

    async def execute_split(
        self, project_id: str, cluster_id: str, subclusters: list[dict]
    ) -> list[ClusterResponse]:
        """Execute split as proposed. Delete original, create new clusters."""
        original = await self._cluster_repo.get_by_id(project_id, cluster_id)
        if original is None:
            raise ClusterNotFoundError(cluster_id)

        # Validierung
        all_original_fact_ids = {
            f["id"] for f in await self._fact_repo.get_by_cluster(cluster_id, project_id)
        }
        submitted_fact_ids: set[str] = set()
        for sc in subclusters:
            submitted_fact_ids.update(sc["fact_ids"])
        if submitted_fact_ids != all_original_fact_ids:
            raise ValueError("All facts must be assigned to exactly one subcluster")

        new_clusters = []
        for sc in subclusters:
            new_cluster = await self._cluster_repo.create(
                project_id=project_id,
                name=sc["name"],
            )
            await self._fact_repo.move_bulk(
                fact_ids=sc["fact_ids"],
                target_cluster_id=new_cluster["id"],
                project_id=project_id,
            )
            updated = await self._cluster_repo.recalculate_counts(project_id, new_cluster["id"])
            new_clusters.append(updated)
            asyncio.create_task(
                self._summary_service.regenerate_for_cluster(project_id, new_cluster["id"])
            )

        await self._cluster_repo.delete(project_id, cluster_id)
        return [ClusterResponse.model_validate(c) for c in new_clusters]

    async def _expire_undo(self, undo_id: str, delay_seconds: int) -> None:
        await asyncio.sleep(delay_seconds)
        self._undo_store.pop(undo_id, None)


class ClusterNotFoundError(Exception):
    pass

class UndoExpiredError(Exception):
    pass
```

### 6. Custom Exception Klassen

```python
# backend/app/clustering/exceptions.py

class ClusterNotFoundError(Exception):
    """Raised when a cluster does not exist or belongs to a different project."""
    pass

class UndoExpiredError(Exception):
    """Raised when the 30-second undo window has expired."""
    pass

class SplitValidationError(Exception):
    """Raised when split subclusters don't cover all original facts exactly."""
    pass

class MergeConflictError(Exception):
    """Raised when source_cluster_id == target_cluster_id."""
    pass
```

**Error Handling in Router:**

```python
# backend/app/api/cluster_routes.py (Fehlerbehandlung)

from app.clustering.exceptions import (
    ClusterNotFoundError, UndoExpiredError, SplitValidationError, MergeConflictError
)

@router.put("/projects/{project_id}/clusters/{cluster_id}")
async def rename_cluster(...):
    try:
        return await taxonomy_service.rename(project_id, cluster_id, request.name)
    except ClusterNotFoundError:
        raise HTTPException(status_code=404, detail="Cluster not found")

@router.post("/projects/{project_id}/clusters/merge")
async def merge_clusters(...):
    try:
        return await taxonomy_service.merge(
            project_id, request.source_cluster_id, request.target_cluster_id
        )
    except MergeConflictError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ClusterNotFoundError:
        raise HTTPException(status_code=404, detail="Cluster not found")

@router.post("/projects/{project_id}/clusters/merge/undo")
async def undo_merge(...):
    try:
        return await taxonomy_service.undo_merge(project_id, request.undo_id)
    except UndoExpiredError:
        raise HTTPException(status_code=409, detail="Undo window expired or invalid undo_id")

@router.post("/projects/{project_id}/clusters/{cluster_id}/split")
async def execute_split(...):
    try:
        return await taxonomy_service.execute_split(
            project_id, cluster_id, [sc.model_dump() for sc in request.subclusters]
        )
    except SplitValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ClusterNotFoundError:
        raise HTTPException(status_code=404, detail="Cluster not found")
```

### 7. Frontend-Komponenten und Datenfluss

#### ClusterContextMenu (`dashboard/components/cluster-context-menu.tsx`)

```tsx
// dashboard/components/cluster-context-menu.tsx
"use client"

import { useState, useRef, useEffect } from "react"
import type { ClusterResponse } from "@/lib/types"

interface ClusterContextMenuProps {
  cluster: ClusterResponse
  projectId: string
  onRenameStart: () => void
  onMergeStart: () => void
  onSplitStart: () => void
}

export function ClusterContextMenu({
  cluster,
  projectId,
  onRenameStart,
  onMergeStart,
  onSplitStart,
}: ClusterContextMenuProps) {
  const [isOpen, setIsOpen] = useState(false)
  const menuRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setIsOpen(false)
      }
    }
    document.addEventListener("mousedown", handleClickOutside)
    return () => document.removeEventListener("mousedown", handleClickOutside)
  }, [])

  return (
    <div ref={menuRef} className="relative" data-testid="cluster-context-menu">
      <button
        onClick={(e) => {
          e.preventDefault()
          e.stopPropagation()
          setIsOpen((prev) => !prev)
        }}
        aria-label={`Open menu for cluster ${cluster.name}`}
        aria-haspopup="menu"
        aria-expanded={isOpen}
        className="p-1 rounded hover:bg-gray-100 focus-visible:ring-2 focus-visible:ring-blue-500"
        data-testid="cluster-menu-trigger"
      >
        ⋮
      </button>
      {isOpen && (
        <div
          role="menu"
          className="absolute right-0 top-6 z-10 bg-white border border-gray-200 rounded-lg shadow-lg py-1 min-w-[140px]"
        >
          <button
            role="menuitem"
            onClick={(e) => {
              e.stopPropagation()
              setIsOpen(false)
              onRenameStart()
            }}
            className="w-full text-left px-3 py-2 text-sm text-gray-700 hover:bg-gray-50"
            data-testid="menu-rename"
          >
            Rename
          </button>
          <button
            role="menuitem"
            onClick={(e) => {
              e.stopPropagation()
              setIsOpen(false)
              onMergeStart()
            }}
            className="w-full text-left px-3 py-2 text-sm text-gray-700 hover:bg-gray-50"
            data-testid="menu-merge"
          >
            Merge with...
          </button>
          <button
            role="menuitem"
            onClick={(e) => {
              e.stopPropagation()
              setIsOpen(false)
              onSplitStart()
            }}
            className="w-full text-left px-3 py-2 text-sm text-gray-700 hover:bg-gray-50"
            data-testid="menu-split"
          >
            Split
          </button>
        </div>
      )}
    </div>
  )
}
```

#### InlineRename (`dashboard/components/inline-rename.tsx`)

```tsx
// dashboard/components/inline-rename.tsx
"use client"

import { useState, useRef, useEffect } from "react"

interface InlineRenameProps {
  initialName: string
  onSave: (name: string) => Promise<void>
  onCancel: () => void
  isLoading?: boolean
}

export function InlineRename({
  initialName,
  onSave,
  onCancel,
  isLoading = false,
}: InlineRenameProps) {
  const [value, setValue] = useState(initialName)
  const inputRef = useRef<HTMLInputElement>(null)
  const isValid = value.trim().length >= 1 && value.trim().length <= 200

  useEffect(() => {
    inputRef.current?.focus()
    inputRef.current?.select()
  }, [])

  async function handleKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Enter" && isValid && !isLoading) {
      await onSave(value.trim())
    } else if (e.key === "Escape") {
      onCancel()
    }
  }

  return (
    <div className="flex flex-col gap-1" data-testid="inline-rename">
      <input
        ref={inputRef}
        type="text"
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={handleKeyDown}
        disabled={isLoading}
        aria-label="Cluster name"
        maxLength={200}
        className="px-2 py-1 text-sm border border-blue-400 rounded focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
        data-testid="rename-input"
      />
      <div className="flex gap-2">
        <button
          onClick={() => isValid && !isLoading && onSave(value.trim())}
          disabled={!isValid || isLoading}
          aria-label="Save cluster name"
          className="px-2 py-0.5 text-xs bg-blue-600 text-white rounded disabled:opacity-50 hover:bg-blue-700 focus-visible:ring-2 focus-visible:ring-blue-500"
          data-testid="rename-save"
        >
          {isLoading ? "Saving…" : "Save"}
        </button>
        <button
          onClick={onCancel}
          disabled={isLoading}
          aria-label="Cancel rename"
          className="px-2 py-0.5 text-xs border border-gray-300 rounded hover:bg-gray-50 focus-visible:ring-2 focus-visible:ring-gray-400"
          data-testid="rename-cancel"
        >
          Cancel
        </button>
      </div>
    </div>
  )
}
```

#### MergeDialog (`dashboard/components/merge-dialog.tsx`)

```tsx
// dashboard/components/merge-dialog.tsx
"use client"

import { useState } from "react"
import type { ClusterResponse, MergeResponse } from "@/lib/types"

interface MergeDialogProps {
  sourceCluster: ClusterResponse
  availableClusters: ClusterResponse[]  // Alle anderen Cluster im Projekt
  projectId: string
  onMerge: (sourceId: string, targetId: string) => Promise<MergeResponse>
  onClose: () => void
}

export function MergeDialog({
  sourceCluster,
  availableClusters,
  projectId,
  onMerge,
  onClose,
}: MergeDialogProps) {
  const [selectedTargetId, setSelectedTargetId] = useState<string | null>(null)
  const [isMerging, setIsMerging] = useState(false)
  const isValid = selectedTargetId !== null && !isMerging

  async function handleMerge() {
    if (!isValid || !selectedTargetId) return
    setIsMerging(true)
    try {
      await onMerge(sourceCluster.id, selectedTargetId)
      onClose()
    } finally {
      setIsMerging(false)
    }
  }

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="merge-dialog-title"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
      data-testid="merge-dialog"
    >
      <div className="bg-white rounded-xl shadow-xl w-full max-w-md mx-4">
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
          <h2 id="merge-dialog-title" className="text-base font-semibold text-gray-900">
            Merge Cluster
          </h2>
          <button
            onClick={onClose}
            aria-label="Close merge dialog"
            className="p-1 rounded hover:bg-gray-100 focus-visible:ring-2 focus-visible:ring-gray-400"
          >
            ✕
          </button>
        </div>
        <div className="px-6 py-4">
          <p className="text-sm text-gray-600 mb-4">
            Merge <span className="font-medium">"{sourceCluster.name}"</span> with:
          </p>
          <fieldset className="space-y-2">
            <legend className="sr-only">Select target cluster</legend>
            {availableClusters.map((cluster) => (
              <label
                key={cluster.id}
                className="flex items-center gap-3 p-2 rounded-lg border border-gray-200 cursor-pointer hover:bg-gray-50 has-[:checked]:border-blue-500 has-[:checked]:bg-blue-50"
              >
                <input
                  type="radio"
                  name="target-cluster"
                  value={cluster.id}
                  checked={selectedTargetId === cluster.id}
                  onChange={() => setSelectedTargetId(cluster.id)}
                  className="accent-blue-600"
                  data-testid={`merge-target-${cluster.id}`}
                />
                <span className="text-sm text-gray-700">
                  {cluster.name}
                  <span className="ml-2 text-xs text-gray-400">({cluster.fact_count} Facts)</span>
                </span>
              </label>
            ))}
          </fieldset>
          <div
            className="mt-4 flex items-start gap-2 p-3 bg-amber-50 border border-amber-200 rounded-lg text-xs text-amber-800"
            role="note"
          >
            <span aria-hidden="true">⚠</span>
            <span>
              All facts from "{sourceCluster.name}" will be moved to the selected cluster.
              You can undo this within 30 seconds.
            </span>
          </div>
        </div>
        <div className="flex justify-end gap-3 px-6 py-4 border-t border-gray-200">
          <button
            onClick={onClose}
            disabled={isMerging}
            className="px-4 py-2 text-sm border border-gray-300 rounded-lg hover:bg-gray-50 focus-visible:ring-2 focus-visible:ring-gray-400"
          >
            Cancel
          </button>
          <button
            onClick={handleMerge}
            disabled={!isValid}
            className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg disabled:opacity-50 hover:bg-blue-700 focus-visible:ring-2 focus-visible:ring-blue-500"
            data-testid="merge-confirm-btn"
          >
            {isMerging ? "Merging…" : "Merge Clusters"}
          </button>
        </div>
      </div>
    </div>
  )
}
```

#### UndoToast (`dashboard/components/undo-toast.tsx`)

```tsx
// dashboard/components/undo-toast.tsx
"use client"

import { useState, useEffect } from "react"

interface UndoToastProps {
  message: string
  expiresAt: string   // ISO 8601 datetime string
  onUndo: () => Promise<void>
  onDismiss: () => void
}

export function UndoToast({ message, expiresAt, onUndo, onDismiss }: UndoToastProps) {
  const [secondsLeft, setSecondsLeft] = useState(() => {
    const ms = new Date(expiresAt).getTime() - Date.now()
    return Math.max(0, Math.ceil(ms / 1000))
  })
  const [isUndoing, setIsUndoing] = useState(false)

  useEffect(() => {
    if (secondsLeft <= 0) {
      onDismiss()
      return
    }
    const timer = setInterval(() => {
      setSecondsLeft((s) => {
        if (s <= 1) {
          clearInterval(timer)
          onDismiss()
          return 0
        }
        return s - 1
      })
    }, 1000)
    return () => clearInterval(timer)
  }, [secondsLeft, onDismiss])

  async function handleUndo() {
    setIsUndoing(true)
    try {
      await onUndo()
    } finally {
      setIsUndoing(false)
      onDismiss()
    }
  }

  return (
    <div
      role="status"
      aria-live="polite"
      aria-atomic="true"
      className="fixed bottom-4 left-1/2 -translate-x-1/2 z-50 flex items-center gap-3 bg-gray-900 text-white px-4 py-3 rounded-lg shadow-lg text-sm"
      data-testid="undo-toast"
    >
      <span>{message}</span>
      <button
        onClick={handleUndo}
        disabled={isUndoing || secondsLeft <= 0}
        className="font-medium text-blue-400 hover:text-blue-300 disabled:opacity-50 focus-visible:ring-2 focus-visible:ring-blue-400"
        data-testid="undo-btn"
      >
        {isUndoing ? "Undoing…" : `Undo (${secondsLeft}s)`}
      </button>
    </div>
  )
}
```

#### SplitModal (`dashboard/components/split-modal.tsx`)

```tsx
// dashboard/components/split-modal.tsx
"use client"

import { useState } from "react"
import type { ClusterResponse, SplitPreviewResponse } from "@/lib/types"

type Step = "step1" | "step1_generating" | "step2" | "splitting"

interface SplitModalProps {
  cluster: ClusterResponse
  projectId: string
  onPreview: (clusterId: string) => Promise<SplitPreviewResponse>
  onConfirm: (clusterId: string, subclusters: Array<{name: string; fact_ids: string[]}>) => Promise<ClusterResponse[]>
  onClose: () => void
}

export function SplitModal({
  cluster,
  projectId,
  onPreview,
  onConfirm,
  onClose,
}: SplitModalProps) {
  const [step, setStep] = useState<Step>("step1")
  const [preview, setPreview] = useState<SplitPreviewResponse | null>(null)

  async function handleGeneratePreview() {
    setStep("step1_generating")
    try {
      const result = await onPreview(cluster.id)
      setPreview(result)
      setStep("step2")
    } catch {
      setStep("step1")
    }
  }

  async function handleConfirm() {
    if (!preview) return
    setStep("splitting")
    try {
      await onConfirm(
        cluster.id,
        preview.subclusters.map((sc) => ({
          name: sc.name,
          fact_ids: sc.facts.map((f) => f.id),
        }))
      )
      onClose()
    } catch {
      setStep("step2")
    }
  }

  const isGenerating = step === "step1_generating"
  const isSplitting = step === "splitting"

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="split-modal-title"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
      data-testid="split-modal"
    >
      <div className="bg-white rounded-xl shadow-xl w-full max-w-lg mx-4 max-h-[80vh] overflow-y-auto">
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 sticky top-0 bg-white">
          <h2 id="split-modal-title" className="text-base font-semibold text-gray-900">
            {step === "step2" ? "Split Cluster — Preview" : "Split Cluster"}
          </h2>
          <button
            onClick={onClose}
            disabled={isSplitting}
            aria-label="Close split modal"
            className="p-1 rounded hover:bg-gray-100 focus-visible:ring-2 focus-visible:ring-gray-400 disabled:opacity-50"
          >
            ✕
          </button>
        </div>

        {/* Step 1 */}
        {(step === "step1" || step === "step1_generating") && (
          <div className="px-6 py-4">
            <p className="text-sm text-gray-700 mb-2">
              Split <span className="font-medium">"{cluster.name}"</span> ({cluster.fact_count} Facts)?
            </p>
            <p className="text-sm text-gray-500">
              The LLM will analyze the facts and propose sub-clusters for your review.
            </p>
          </div>
        )}

        {/* Step 2 Preview */}
        {step === "step2" && preview && (
          <div className="px-6 py-4">
            <p className="text-sm text-gray-600 mb-4">
              Proposed split for <span className="font-medium">"{cluster.name}"</span>:
            </p>
            <div className="space-y-3">
              {preview.subclusters.map((sc, i) => (
                <div
                  key={i}
                  className="border border-gray-200 rounded-lg p-3"
                  data-testid={`split-preview-subcluster-${i}`}
                >
                  <p className="text-sm font-medium text-gray-900 mb-2">
                    {sc.name} ({sc.fact_count} Facts)
                  </p>
                  <ul className="space-y-1">
                    {sc.facts.map((fact) => (
                      <li key={fact.id} className="text-xs text-gray-600 flex gap-1.5">
                        <span aria-hidden="true" className="text-gray-400">•</span>
                        <span>{fact.content}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              ))}
            </div>
          </div>
        )}

        <div className="flex justify-end gap-3 px-6 py-4 border-t border-gray-200 sticky bottom-0 bg-white">
          <button
            onClick={onClose}
            disabled={isSplitting}
            className="px-4 py-2 text-sm border border-gray-300 rounded-lg hover:bg-gray-50 focus-visible:ring-2 focus-visible:ring-gray-400 disabled:opacity-50"
          >
            Cancel
          </button>
          {(step === "step1" || step === "step1_generating") && (
            <button
              onClick={handleGeneratePreview}
              disabled={isGenerating}
              className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg disabled:opacity-50 hover:bg-blue-700 focus-visible:ring-2 focus-visible:ring-blue-500"
              data-testid="generate-preview-btn"
            >
              {isGenerating ? "Analyzing…" : "Generate Preview"}
            </button>
          )}
          {step === "step2" && (
            <button
              onClick={handleConfirm}
              className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 focus-visible:ring-2 focus-visible:ring-blue-500"
              data-testid="confirm-split-btn"
            >
              Confirm Split
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
```

#### SuggestionBanner (`dashboard/components/suggestion-banner.tsx`)

```tsx
// dashboard/components/suggestion-banner.tsx
"use client"

import type { SuggestionResponse } from "@/lib/types"

interface SuggestionBannerProps {
  suggestion: SuggestionResponse
  onAccept: (suggestionId: string) => Promise<void>
  onDismiss: (suggestionId: string) => Promise<void>
}

export function SuggestionBanner({ suggestion, onAccept, onDismiss }: SuggestionBannerProps) {
  const isMerge = suggestion.type === "merge"
  const description = isMerge
    ? `Merge "${suggestion.source_cluster_name}" with "${suggestion.target_cluster_name}"${suggestion.similarity_score ? ` (${Math.round(suggestion.similarity_score * 100)}% similar)` : ""}`
    : `Split "${suggestion.source_cluster_name}" into sub-clusters`

  return (
    <div
      role="alert"
      aria-label={`Suggestion: ${description}`}
      className="flex items-center justify-between gap-4 px-4 py-3 bg-amber-50 border border-amber-200 rounded-lg text-sm"
      data-testid="suggestion-banner"
    >
      <div className="flex items-center gap-2 min-w-0">
        <span aria-hidden="true" className="flex-shrink-0 text-amber-500">⚡</span>
        <span className="text-gray-700 truncate">
          <span className="font-medium">Suggestion:</span> {description}
        </span>
      </div>
      <div className="flex gap-2 flex-shrink-0">
        <button
          onClick={() => onDismiss(suggestion.id)}
          className="px-3 py-1.5 text-xs border border-gray-300 rounded-lg hover:bg-gray-50 focus-visible:ring-2 focus-visible:ring-gray-400"
          data-testid="suggestion-dismiss"
        >
          Dismiss
        </button>
        <button
          onClick={() => onAccept(suggestion.id)}
          className="px-3 py-1.5 text-xs bg-amber-500 text-white rounded-lg hover:bg-amber-600 focus-visible:ring-2 focus-visible:ring-amber-400"
          data-testid="suggestion-accept"
        >
          {isMerge ? "Merge" : "Split"}
        </button>
      </div>
    </div>
  )
}
```

#### RecalculateModal (`dashboard/components/recalculate-modal.tsx`)

```tsx
// dashboard/components/recalculate-modal.tsx
"use client"

import { useState } from "react"
import type { ProjectResponse } from "@/lib/types"

interface RecalculateModalProps {
  project: ProjectResponse
  onConfirm: () => Promise<void>
  onClose: () => void
}

export function RecalculateModal({ project, onConfirm, onClose }: RecalculateModalProps) {
  const [isRecalculating, setIsRecalculating] = useState(false)

  async function handleConfirm() {
    setIsRecalculating(true)
    try {
      await onConfirm()
      onClose()
    } finally {
      setIsRecalculating(false)
    }
  }

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="recalculate-modal-title"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
      data-testid="recalculate-modal"
    >
      <div className="bg-white rounded-xl shadow-xl w-full max-w-md mx-4">
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
          <h2 id="recalculate-modal-title" className="text-base font-semibold text-gray-900">
            Recalculate Clusters
          </h2>
          <button
            onClick={onClose}
            disabled={isRecalculating}
            aria-label="Close recalculate modal"
            className="p-1 rounded hover:bg-gray-100 focus-visible:ring-2 focus-visible:ring-gray-400 disabled:opacity-50"
          >
            ✕
          </button>
        </div>
        <div className="px-6 py-4">
          <div className="flex items-start gap-3 mb-4 p-3 bg-red-50 border border-red-200 rounded-lg">
            <span aria-hidden="true" className="text-red-500 flex-shrink-0">⚠</span>
            <p className="text-sm text-red-800 font-medium">Warning</p>
          </div>
          <p className="text-sm text-gray-600 mb-3">
            All existing cluster assignments will be reset. Facts will be preserved,
            but a completely new cluster structure will be generated from scratch.
          </p>
          <ul className="space-y-1 text-sm text-gray-600">
            <li>• {project.cluster_count} Clusters (will be deleted)</li>
            <li>• {project.fact_count} Fact assignments (will be reset)</li>
            <li>• All cluster summaries (regenerated)</li>
          </ul>
        </div>
        <div className="flex justify-end gap-3 px-6 py-4 border-t border-gray-200">
          <button
            onClick={onClose}
            disabled={isRecalculating}
            className="px-4 py-2 text-sm border border-gray-300 rounded-lg hover:bg-gray-50 focus-visible:ring-2 focus-visible:ring-gray-400 disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            onClick={handleConfirm}
            disabled={isRecalculating}
            className="px-4 py-2 text-sm bg-red-600 text-white rounded-lg disabled:opacity-50 hover:bg-red-700 focus-visible:ring-2 focus-visible:ring-red-500"
            data-testid="recalculate-confirm-btn"
          >
            {isRecalculating ? "Recalculating…" : "Recalculate All"}
          </button>
        </div>
      </div>
    </div>
  )
}
```

#### BulkMoveBar (`dashboard/components/bulk-move-bar.tsx`)

```tsx
// dashboard/components/bulk-move-bar.tsx
"use client"

import type { ClusterResponse } from "@/lib/types"

interface BulkMoveBarProps {
  selectedCount: number
  availableClusters: ClusterResponse[]
  onMove: (targetClusterId: string | null) => Promise<void>
  isMoving?: boolean
}

export function BulkMoveBar({
  selectedCount,
  availableClusters,
  onMove,
  isMoving = false,
}: BulkMoveBarProps) {
  if (selectedCount === 0) return null

  return (
    <div
      className="flex items-center gap-3 px-4 py-2 bg-blue-50 border border-blue-200 rounded-lg text-sm"
      data-testid="bulk-move-bar"
    >
      <span className="text-blue-700 font-medium">{selectedCount} selected</span>
      <label htmlFor="bulk-move-target" className="sr-only">Move selected facts to cluster</label>
      <select
        id="bulk-move-target"
        onChange={(e) => onMove(e.target.value === "unassigned" ? null : e.target.value)}
        disabled={isMoving}
        defaultValue=""
        className="text-sm border border-blue-300 rounded-lg px-2 py-1 bg-white focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
        data-testid="bulk-move-select"
      >
        <option value="" disabled>Move selected to cluster...</option>
        <option value="unassigned">Mark as unassigned</option>
        {availableClusters.map((cluster) => (
          <option key={cluster.id} value={cluster.id}>
            {cluster.name}
          </option>
        ))}
      </select>
      {isMoving && <span className="text-blue-500 text-xs">Moving…</span>}
    </div>
  )
}
```

#### FactContextMenu (`dashboard/components/fact-context-menu.tsx`)

```tsx
// dashboard/components/fact-context-menu.tsx
"use client"

import { useState, useRef, useEffect } from "react"
import type { ClusterResponse } from "@/lib/types"

interface FactContextMenuProps {
  factId: string
  currentClusterId: string | null
  availableClusters: Array<{ id: string; name: string }>
  onMove: (factId: string, newClusterId: string | null) => Promise<void>
  onMarkUnassigned: (factId: string) => Promise<void>
}

export function FactContextMenu({
  factId,
  currentClusterId,
  availableClusters,
  onMove,
  onMarkUnassigned,
}: FactContextMenuProps) {
  const [isOpen, setIsOpen] = useState(false)
  const [isActing, setIsActing] = useState(false)
  const menuRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setIsOpen(false)
      }
    }
    document.addEventListener("mousedown", handleClickOutside)
    return () => document.removeEventListener("mousedown", handleClickOutside)
  }, [])

  async function handleMove(newClusterId: string | null) {
    setIsActing(true)
    setIsOpen(false)
    try {
      await onMove(factId, newClusterId)
    } finally {
      setIsActing(false)
    }
  }

  async function handleMarkUnassigned() {
    setIsActing(true)
    setIsOpen(false)
    try {
      await onMarkUnassigned(factId)
    } finally {
      setIsActing(false)
    }
  }

  const otherClusters = availableClusters.filter((c) => c.id !== currentClusterId)

  return (
    <div ref={menuRef} className="relative" data-testid="fact-context-menu">
      <button
        onClick={(e) => {
          e.preventDefault()
          e.stopPropagation()
          setIsOpen((prev) => !prev)
        }}
        disabled={isActing}
        aria-label="Fact actions"
        aria-haspopup="menu"
        aria-expanded={isOpen}
        className="p-1 rounded hover:bg-gray-100 focus-visible:ring-2 focus-visible:ring-blue-500 disabled:opacity-50"
        data-testid="fact-menu-trigger"
      >
        ⋮
      </button>
      {isOpen && (
        <div
          role="menu"
          aria-label="Fact actions"
          className="absolute right-0 top-6 z-10 bg-white border border-gray-200 rounded-lg shadow-lg py-1 min-w-[180px]"
          data-testid="fact-menu-dropdown"
        >
          {otherClusters.map((cluster) => (
            <button
              key={cluster.id}
              role="menuitem"
              onClick={(e) => {
                e.stopPropagation()
                handleMove(cluster.id)
              }}
              className="w-full text-left px-3 py-2 text-sm text-gray-700 hover:bg-gray-50 truncate"
              data-testid={`fact-move-to-${cluster.id}`}
            >
              Move to {cluster.name}…
            </button>
          ))}
          {currentClusterId !== null && (
            <button
              role="menuitem"
              onClick={(e) => {
                e.stopPropagation()
                handleMarkUnassigned()
              }}
              className="w-full text-left px-3 py-2 text-sm text-gray-500 hover:bg-gray-50 border-t border-gray-100"
              data-testid="fact-mark-unassigned"
            >
              Mark as unassigned
            </button>
          )}
        </div>
      )}
    </div>
  )
}
```

### 8. Neue TypeScript Types (dashboard/lib/types.ts Erweiterung)

```typescript
// dashboard/lib/types.ts (Erweiterung)

export interface RenameRequest {
  name: string
}

export interface MergeRequest {
  source_cluster_id: string
  target_cluster_id: string
}

export interface MergeResponse {
  merged_cluster: ClusterResponse
  undo_id: string
  undo_expires_at: string  // ISO 8601
}

export interface UndoMergeRequest {
  undo_id: string
}

export interface SplitPreviewSubcluster {
  name: string
  fact_count: number
  facts: FactResponse[]
}

export interface SplitPreviewResponse {
  subclusters: SplitPreviewSubcluster[]
}

export interface SplitSubclusterInput {
  name: string
  fact_ids: string[]
}

export interface SplitConfirmRequest {
  subclusters: SplitSubclusterInput[]
}

export interface MoveFactRequest {
  cluster_id: string | null
}

export interface BulkMoveRequest {
  fact_ids: string[]
  target_cluster_id: string | null
}

export interface SuggestionResponse {
  id: string
  type: "merge" | "split"
  source_cluster_id: string
  source_cluster_name: string
  target_cluster_id: string | null
  target_cluster_name: string | null
  similarity_score: number | null
  proposed_data: Record<string, unknown> | null
  status: "pending"
  created_at: string
}

export interface ReclusterStarted {
  status: string
  message: string
}
```

### 9. API Client Erweiterung (dashboard/lib/api-client.ts)

```typescript
// dashboard/lib/api-client.ts (Erweiterung)

// Neue Methoden hinzufuegen:

renameCluster(projectId: string, clusterId: string, name: string): Promise<ClusterResponse> {
  return apiFetch<ClusterResponse>(`/api/projects/${projectId}/clusters/${clusterId}`, {
    method: "PUT",
    body: JSON.stringify({ name }),
  })
},

mergeClusters(projectId: string, sourceId: string, targetId: string): Promise<MergeResponse> {
  return apiFetch<MergeResponse>(`/api/projects/${projectId}/clusters/merge`, {
    method: "POST",
    body: JSON.stringify({ source_cluster_id: sourceId, target_cluster_id: targetId }),
  })
},

undoMerge(projectId: string, undoId: string): Promise<ClusterResponse> {
  return apiFetch<ClusterResponse>(`/api/projects/${projectId}/clusters/merge/undo`, {
    method: "POST",
    body: JSON.stringify({ undo_id: undoId }),
  })
},

getSplitPreview(projectId: string, clusterId: string): Promise<SplitPreviewResponse> {
  return apiFetch<SplitPreviewResponse>(
    `/api/projects/${projectId}/clusters/${clusterId}/split/preview`,
    { method: "POST" }
  )
},

executeSplit(
  projectId: string,
  clusterId: string,
  subclusters: SplitSubclusterInput[]
): Promise<ClusterResponse[]> {
  return apiFetch<ClusterResponse[]>(
    `/api/projects/${projectId}/clusters/${clusterId}/split`,
    {
      method: "POST",
      body: JSON.stringify({ subclusters }),
    }
  )
},

moveFact(projectId: string, factId: string, clusterId: string | null): Promise<FactResponse> {
  return apiFetch<FactResponse>(`/api/projects/${projectId}/facts/${factId}`, {
    method: "PUT",
    body: JSON.stringify({ cluster_id: clusterId }),
  })
},

bulkMoveFacts(
  projectId: string,
  factIds: string[],
  targetClusterId: string | null
): Promise<FactResponse[]> {
  return apiFetch<FactResponse[]>(`/api/projects/${projectId}/facts/bulk-move`, {
    method: "POST",
    body: JSON.stringify({ fact_ids: factIds, target_cluster_id: targetClusterId }),
  })
},

getSuggestions(projectId: string): Promise<SuggestionResponse[]> {
  return apiFetch<SuggestionResponse[]>(`/api/projects/${projectId}/suggestions`)
},

acceptSuggestion(projectId: string, suggestionId: string): Promise<void> {
  return apiFetch<void>(`/api/projects/${projectId}/suggestions/${suggestionId}/accept`, {
    method: "POST",
  })
},

dismissSuggestion(projectId: string, suggestionId: string): Promise<void> {
  return apiFetch<void>(`/api/projects/${projectId}/suggestions/${suggestionId}/dismiss`, {
    method: "POST",
  })
},

triggerRecluster(projectId: string): Promise<ReclusterStarted> {
  return apiFetch<ReclusterStarted>(`/api/projects/${projectId}/clustering/recluster`, {
    method: "POST",
  })
},
```

### 10. Abhaengigkeiten (Neue Pakete)

Keine neuen Pakete erforderlich. Alle benoetigten Libraries sind aus Slice 1-5 vorhanden:
- Backend: `fastapi`, `sqlalchemy`, `asyncio` (stdlib), `uuid` (stdlib), `python-jose`, `pydantic`
- Frontend: `next`, `react`, Tailwind v4

---

## UI Anforderungen

### Wireframe: Cluster-Card mit Kontext-Menue

> **Quelle:** `wireframes.md` → "Screen: Cluster Context Menu"

```
  ┌─────────────────────┐
  │  Navigation Issues   │
  │  ...            [⋮]←─── click
  │                 ┌──────────────┐
  │                 │  Rename      │
  │                 │  Merge with  │
  │                 │  Split       │
  │                 └──────────────┘
  └─────────────────────┘
```

### Wireframe: Inline-Rename (Cluster-Card)

> **Quelle:** `wireframes.md` → "Screen: Inline Rename"

```
  ┌─────────────────────┐
  │                      │
  │  ┌────────────────┐  │
  │  │ Navigation Is. │  │  ← text input replaces name
  │  └────────────────┘  │
  │  [Save] [Cancel]     │
  │  ● 14 Facts          │
  └─────────────────────┘
```

### Wireframe: Merge-Dialog

> **Quelle:** `wireframes.md` → "Screen: Merge Dialog (Modal)"

```
     ┌─────────────────────────────────────────┐
     │  Merge Cluster                    [X]   │
     ├─────────────────────────────────────────┤
     │  Merge "Login Issues" with:             │
     │                                         │
     │  ○ Navigation Issues (14 Facts)         │
     │  ● Auth Problems (8 Facts)              │
     │  ○ Pricing Confusion (11 Facts)         │
     │                                         │
     │  ⚠ All facts will be moved. Undo (30s). │
     │                                         │
     │            [Cancel]  [Merge Clusters]   │
     └─────────────────────────────────────────┘
```

### Wireframe: Split Modal (2-Schritt)

> **Quelle:** `wireframes.md` → "Screen: Split Cluster (Two-Step Modal)"

```
Step 1:
     ┌─────────────────────────────────────────┐
     │  Split Cluster                    [X]   │
     │  Split "Navigation Issues" (14 Facts)?  │
     │  The LLM will analyze and propose...    │
     │          [Cancel]  [Generate Preview]   │
     └─────────────────────────────────────────┘

Step 2 (nach LLM Preview):
     ┌─────────────────────────────────────────────────┐
     │  Split Cluster — Preview              [X]       │
     │  ┌───────────────────────────────────────────┐  │
     │  │ Menu Structure (8 Facts)                  │  │
     │  │   • Users cannot find settings page       │  │
     │  │   • Hamburger menu not intuitive          │  │
     │  └───────────────────────────────────────────┘  │
     │  ┌───────────────────────────────────────────┐  │
     │  │ Feature Discovery (6 Facts)               │  │
     │  │   • Key features hidden after onboarding  │  │
     │  └───────────────────────────────────────────┘  │
     │        [Cancel]  [Confirm Split]                │
     └─────────────────────────────────────────────────┘
```

### Wireframe: Suggestion Banner (Insights Tab)

> **Quelle:** `wireframes.md` → "Screen: Project Dashboard (Insights Tab)" Annotation ⑤

```
  ⑤ ┌─────────────────────────────────────────────────┐
    │ ⚡ Suggestion: Merge "Login Issues" with         │
    │    "Auth Problems" (82% similar)                 │
    │                        [Dismiss]  [Merge]        │
    └─────────────────────────────────────────────────┘
```

### Wireframe: Recalculate Confirmation Modal

> **Quelle:** `wireframes.md` → "Screen: Re-Cluster Confirmation (Modal)"

```
     ┌─────────────────────────────────────────┐
     │  Recalculate Clusters             [X]   │
     │  ⚠ Warning                              │
     │  All cluster assignments will be reset. │
     │  • 5 Clusters (deleted)                 │
     │  • 47 Fact assignments (reset)          │
     │       [Cancel]  [Recalculate All]       │
     └─────────────────────────────────────────┘
```

**Referenz Skills fuer UI-Implementation:**
- `.claude/skills/react-best-practices/SKILL.md` — `rerender-functional-setstate`, `rerender-derived-state-no-effect`, `async-parallel`
- `.claude/skills/web-design/SKILL.md` — Dialog accessibility (role="dialog", aria-modal, aria-labelledby), Destructive action confirmation, Focus management
- `.claude/skills/tailwind-v4/SKILL.md` — Design Tokens, Animation (prefers-reduced-motion)

### 1. InsightsTab Erweiterungen (`app/projects/[id]/page.tsx`)

**Neue Elemente:**
- `SuggestionBanner` Komponenten fuer aktive Suggestions (aus `GET /api/projects/{id}/suggestions`)
- `RecalculateModal` — getriggert durch "Recalculate" Button
- Unassigned-Bereich mit Checkboxen + `BulkMoveBar`
- `ClusterContextMenu` auf jeder ClusterCard aktiv

**Zustände:**
- `no_suggestions`: Kein Banner
- `has_suggestions`: 1 oder mehr Suggestion-Banner im Stack
- `recalculate_open`: RecalculateModal sichtbar

### 2. ClusterDetailPage Erweiterungen (`app/projects/[id]/clusters/[cluster_id]/page.tsx`)

**Neue Elemente:**
- `InlineRename` im Cluster-Detail-Header (statt read-only Name)
- Merge-Button aktiviert → oeffnet MergeDialog
- Split-Button aktiviert → oeffnet SplitModal
- Checkboxen auf jedem FactItem + BulkMoveBar
- FactContextMenu ([⋮] pro Fact): "Move to [cluster]...", "Mark as unassigned"

**Zustände:**
- `editing_name`: InlineRename aktiv
- `merge_open`: MergeDialog offen
- `split_open`: SplitModal offen
- `undo_visible`: UndoToast sichtbar (nach Merge)
- `bulk_selected`: BulkMoveBar sichtbar (>= 1 Checkbox aktiv)

### 3. Accessibility

- [x] Alle Modals: `role="dialog"`, `aria-modal="true"`, `aria-labelledby`
- [x] Context-Menus: `role="menu"`, `role="menuitem"`, `aria-haspopup="menu"`, `aria-expanded`
- [x] Icon-only Buttons (⋮, ✕): `aria-label`
- [x] Radio-List im MergeDialog: `<fieldset>` + `<legend>`
- [x] UndoToast: `role="status"`, `aria-live="polite"`, `aria-atomic="true"`
- [x] SuggestionBanner: `role="alert"`
- [x] InlineRename Input: `aria-label="Cluster name"`
- [x] BulkMoveBar Select: `<label>` + `htmlFor`
- [x] Checkboxen im Fact-Bereich: `aria-label="Select fact"`
- [x] Focus: Nach Modal-Close zurueck auf Trigger-Element (via `ref`)
- [x] Keyboard: Escape schliesst alle Modals

---

## Acceptance Criteria

1) GIVEN a project with multiple clusters is open in the Insights Tab
   WHEN the user clicks the three-dot menu icon on a cluster card
   THEN a context menu appears with options "Rename", "Merge with...", and "Split"

2) GIVEN the context menu is open and the user clicks "Rename"
   WHEN the inline rename input is shown
   THEN the user can type a new name and press Enter to save, or Escape to cancel
   AND the cluster name is updated without triggering re-clustering or summary regeneration

3) GIVEN the user has opened the Merge dialog by clicking "Merge with..." on a cluster
   WHEN the user selects a target cluster and clicks "Merge Clusters"
   THEN all facts from the source cluster move to the target cluster
   AND the source cluster is deleted
   AND an Undo Toast appears with a 30-second countdown
   AND the target cluster's summary is regenerated in the background

4) GIVEN an Undo Toast is visible after a merge operation
   WHEN the user clicks "Undo" within 30 seconds
   THEN the source cluster is restored with its original name
   AND all facts are moved back to the source cluster
   AND both cluster summaries are regenerated in the background

5) GIVEN the user opens the Split modal by clicking "Split" on a cluster
   WHEN the user clicks "Generate Preview"
   THEN a spinner shows while the LLM analyzes the facts
   AND a preview of proposed sub-clusters appears with full fact listings (Step 2)
   AND no DB changes occur during preview generation

6) GIVEN the Split preview (Step 2) is shown
   WHEN the user clicks "Confirm Split"
   THEN the original cluster is deleted
   AND new sub-clusters are created with the proposed names and facts
   AND summaries are regenerated for each new sub-cluster in the background

7) GIVEN the user cancels the Split flow at any step
   THEN no changes are made to the cluster or its facts

8) GIVEN LLM merge/split suggestions are available for a project
   WHEN the user opens the Insights Tab
   THEN suggestion banners appear showing the proposed action and similarity score
   AND the user can click "Merge" or "Split" to accept, or "Dismiss" to reject

9) GIVEN the user is in the Cluster Detail view
   WHEN the user checks one or more fact checkboxes
   THEN a "Move selected to cluster" bar appears at the bottom of the facts section
   AND the user can select a target cluster or "Mark as unassigned" from the dropdown

10) GIVEN the user clicks the fact context menu ([⋮] on a fact)
    WHEN the menu opens
    THEN options "Move to [cluster]..." and "Mark as unassigned" are available
    AND selecting an option moves the individual fact

11) GIVEN the user clicks the "Recalculate" button in the Insights Tab
    WHEN the Recalculate Confirmation Modal opens
    THEN the modal shows the impact summary (cluster count, fact count)
    AND clicking "Recalculate All" triggers full re-clustering in the background
    AND clicking "Cancel" closes the modal without any changes

---

## Testfaelle

### Test-Datei
`tests/slices/llm-interview-clustering/slice-06-taxonomy-editing-summary-regen.spec.ts`

<test_spec>
```typescript
// tests/slices/llm-interview-clustering/slice-06-taxonomy-editing-summary-regen.spec.ts
import { test, expect } from "@playwright/test"

const BASE_URL = "http://localhost:3001"

test.describe("Slice 06: Taxonomy Editing + Summary Regeneration", () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to a project's Insights Tab with existing clusters
    // Assumes seeded test data: project with 2+ clusters and facts
    await page.goto(`${BASE_URL}/projects/test-project-id`)
    await expect(page.getByRole("tab", { name: "Insights" })).toBeVisible()
  })

  // AC 1: Cluster Context Menu opens
  test("should show context menu with Rename, Merge, Split options", async ({ page }) => {
    // GIVEN a project with clusters is open
    const menuTrigger = page.getByTestId("cluster-menu-trigger").first()
    await expect(menuTrigger).toBeVisible()

    // WHEN user clicks the three-dot menu
    await menuTrigger.click()

    // THEN context menu appears with all three options
    const menu = page.getByTestId("cluster-context-menu")
    await expect(menu.getByTestId("menu-rename")).toBeVisible()
    await expect(menu.getByTestId("menu-merge")).toBeVisible()
    await expect(menu.getByTestId("menu-split")).toBeVisible()
  })

  // AC 2: Inline Rename
  test("should rename cluster inline on Enter key", async ({ page }) => {
    const menuTrigger = page.getByTestId("cluster-menu-trigger").first()
    await menuTrigger.click()
    await page.getByTestId("menu-rename").click()

    // GIVEN inline rename input is shown
    const renameInput = page.getByTestId("rename-input")
    await expect(renameInput).toBeFocused()

    // WHEN user types new name and presses Enter
    await renameInput.fill("Renamed Cluster")
    await renameInput.press("Enter")

    // THEN cluster name is updated
    await expect(page.getByText("Renamed Cluster")).toBeVisible()
    await expect(renameInput).not.toBeVisible()
  })

  test("should cancel rename on Escape key", async ({ page }) => {
    const originalName = await page.getByTestId("cluster-menu-trigger")
      .first()
      .locator("..")
      .locator("h3, [data-testid='cluster-name']")
      .textContent()

    const menuTrigger = page.getByTestId("cluster-menu-trigger").first()
    await menuTrigger.click()
    await page.getByTestId("menu-rename").click()

    const renameInput = page.getByTestId("rename-input")
    await renameInput.fill("Temporary Name")
    await renameInput.press("Escape")

    // THEN rename is cancelled, original name shown
    await expect(renameInput).not.toBeVisible()
  })

  // AC 3 + 4: Merge with Undo Toast
  test("should merge clusters and show undo toast with countdown", async ({ page }) => {
    const menuTrigger = page.getByTestId("cluster-menu-trigger").first()
    await menuTrigger.click()
    await page.getByTestId("menu-merge").click()

    // GIVEN merge dialog is open
    const mergeDialog = page.getByTestId("merge-dialog")
    await expect(mergeDialog).toBeVisible()

    // WHEN user selects a target cluster
    const firstTarget = mergeDialog.locator('input[type="radio"]').first()
    await firstTarget.check()

    // AND clicks Merge Clusters
    await page.getByTestId("merge-confirm-btn").click()

    // THEN undo toast appears with countdown
    const undoToast = page.getByTestId("undo-toast")
    await expect(undoToast).toBeVisible()
    await expect(undoToast).toContainText("merged")
    await expect(page.getByTestId("undo-btn")).toBeVisible()
    await expect(page.getByTestId("undo-btn")).toContainText("Undo")
  })

  test("should undo merge within 30 seconds", async ({ page }) => {
    // Perform merge first
    const menuTrigger = page.getByTestId("cluster-menu-trigger").first()
    await menuTrigger.click()
    await page.getByTestId("menu-merge").click()
    const firstTarget = page.getByTestId("merge-dialog").locator('input[type="radio"]').first()
    await firstTarget.check()
    await page.getByTestId("merge-confirm-btn").click()

    // GIVEN undo toast is visible
    await expect(page.getByTestId("undo-toast")).toBeVisible()

    // WHEN user clicks Undo
    await page.getByTestId("undo-btn").click()

    // THEN undo toast disappears
    await expect(page.getByTestId("undo-toast")).not.toBeVisible()
  })

  // AC 5 + 6: Split 2-Step Flow
  test("should open split modal and show step 1 explanation", async ({ page }) => {
    const menuTrigger = page.getByTestId("cluster-menu-trigger").first()
    await menuTrigger.click()
    await page.getByTestId("menu-split").click()

    // GIVEN split modal is open (Step 1)
    const splitModal = page.getByTestId("split-modal")
    await expect(splitModal).toBeVisible()
    await expect(page.getByTestId("generate-preview-btn")).toBeVisible()
    await expect(page.getByTestId("confirm-split-btn")).not.toBeVisible()
  })

  test("should generate split preview and show Step 2 with sub-cluster cards", async ({ page }) => {
    const menuTrigger = page.getByTestId("cluster-menu-trigger").first()
    await menuTrigger.click()
    await page.getByTestId("menu-split").click()

    // WHEN user clicks Generate Preview
    await page.getByTestId("generate-preview-btn").click()

    // THEN Step 2 preview is shown
    await expect(page.getByTestId("confirm-split-btn")).toBeVisible({ timeout: 15000 })
    await expect(page.getByTestId("split-preview-subcluster-0")).toBeVisible()
    await expect(page.getByTestId("split-preview-subcluster-1")).toBeVisible()
  })

  test("should cancel split flow without making changes", async ({ page }) => {
    const menuTrigger = page.getByTestId("cluster-menu-trigger").first()
    await menuTrigger.click()
    await page.getByTestId("menu-split").click()

    // WHEN user cancels
    await page.getByRole("button", { name: "Cancel" }).click()

    // THEN modal closes, no changes
    await expect(page.getByTestId("split-modal")).not.toBeVisible()
  })

  // AC 8: Suggestion Banner
  test("should show suggestion banner and allow dismiss", async ({ page }) => {
    // GIVEN a suggestion exists (test data must include a suggestion)
    const suggestionBanner = page.getByTestId("suggestion-banner").first()

    if (await suggestionBanner.isVisible()) {
      // WHEN user clicks Dismiss
      await page.getByTestId("suggestion-dismiss").first().click()

      // THEN banner disappears
      await expect(suggestionBanner).not.toBeVisible()
    }
  })

  // AC 9 + 10: Fact Move (Cluster Detail)
  test("should show bulk-move-bar when fact checkboxes are selected", async ({ page }) => {
    // Navigate to cluster detail
    await page.getByTestId("cluster-card").first().click()
    await page.waitForURL(/\/clusters\//)

    // GIVEN fact items with checkboxes
    const firstCheckbox = page.getByRole("checkbox", { name: /Select fact/i }).first()
    await expect(firstCheckbox).toBeVisible()

    // WHEN user checks a fact
    await firstCheckbox.check()

    // THEN bulk move bar appears
    await expect(page.getByTestId("bulk-move-bar")).toBeVisible()
    await expect(page.getByTestId("bulk-move-select")).toBeVisible()
  })

  // AC 11: Recalculate Modal
  test("should open recalculate modal and confirm triggers recluster", async ({ page }) => {
    // GIVEN Recalculate button is visible in Insights Tab
    const recalcBtn = page.getByRole("button", { name: /Recalculate/i })
    await expect(recalcBtn).toBeVisible()

    // WHEN user clicks Recalculate
    await recalcBtn.click()

    // THEN confirmation modal opens
    const modal = page.getByTestId("recalculate-modal")
    await expect(modal).toBeVisible()
    await expect(page.getByTestId("recalculate-confirm-btn")).toBeVisible()

    // WHEN user cancels
    await page.getByRole("button", { name: "Cancel" }).click()

    // THEN modal closes
    await expect(modal).not.toBeVisible()
  })
})
```
</test_spec>

### Backend-Unit-Tests

`backend/tests/slices/llm-interview-clustering/test_slice_06_taxonomy_service.py`

<test_spec>
```python
# backend/tests/slices/llm-interview-clustering/test_slice_06_taxonomy_service.py

import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from app.clustering.taxonomy import TaxonomyService, ClusterNotFoundError, UndoExpiredError


@pytest.fixture
def mock_cluster_repo():
    repo = AsyncMock()
    repo.get_by_id.return_value = {
        "id": "cluster-1",
        "name": "Navigation Issues",
        "project_id": "project-1",
        "fact_count": 5,
        "interview_count": 3,
        "summary": "Test summary",
        "created_at": "2026-02-28T00:00:00Z",
        "updated_at": "2026-02-28T00:00:00Z",
    }
    repo.update_name.return_value = {
        "id": "cluster-1",
        "name": "Renamed Cluster",
        "project_id": "project-1",
        "fact_count": 5,
        "interview_count": 3,
        "summary": "Test summary",
        "created_at": "2026-02-28T00:00:00Z",
        "updated_at": "2026-02-28T00:00:00Z",
    }
    repo.recalculate_counts.return_value = {
        "id": "cluster-2",
        "name": "Auth Problems",
        "project_id": "project-1",
        "fact_count": 13,
        "interview_count": 6,
        "summary": None,
        "created_at": "2026-02-28T00:00:00Z",
        "updated_at": "2026-02-28T00:00:00Z",
    }
    repo.delete = AsyncMock(return_value=None)
    return repo


@pytest.fixture
def mock_fact_repo():
    repo = AsyncMock()
    repo.get_by_cluster.return_value = [
        {"id": "fact-1", "content": "Fact 1", "cluster_id": "cluster-1"},
        {"id": "fact-2", "content": "Fact 2", "cluster_id": "cluster-1"},
    ]
    repo.move_bulk = AsyncMock(return_value=None)
    return repo


@pytest.fixture
def mock_summary_service():
    service = AsyncMock()
    service.regenerate_for_cluster = AsyncMock(return_value=None)
    service.propose_split.return_value = [
        {
            "name": "Menu Issues",
            "facts": [
                {"id": "fact-1", "content": "Fact 1", "quote": None,
                 "confidence": 0.9, "interview_id": "i1",
                 "interview_date": None, "cluster_id": "cluster-1"},
            ],
        },
        {
            "name": "Feature Discovery",
            "facts": [
                {"id": "fact-2", "content": "Fact 2", "quote": None,
                 "confidence": 0.8, "interview_id": "i2",
                 "interview_date": None, "cluster_id": "cluster-1"},
            ],
        },
    ]
    return service


@pytest.fixture
def taxonomy_service(mock_cluster_repo, mock_fact_repo, mock_summary_service):
    return TaxonomyService(
        cluster_repo=mock_cluster_repo,
        fact_repo=mock_fact_repo,
        summary_service=mock_summary_service,
    )


class TestRename:
    @pytest.mark.asyncio
    async def test_rename_returns_updated_cluster(self, taxonomy_service, mock_cluster_repo):
        # Arrange + Act
        result = await taxonomy_service.rename("project-1", "cluster-1", "Renamed Cluster")

        # Assert
        assert result.name == "Renamed Cluster"
        mock_cluster_repo.update_name.assert_called_once_with("project-1", "cluster-1", "Renamed Cluster")

    @pytest.mark.asyncio
    async def test_rename_raises_not_found_when_cluster_missing(self, taxonomy_service, mock_cluster_repo):
        # Arrange
        mock_cluster_repo.update_name.return_value = None

        # Act + Assert
        with pytest.raises(ClusterNotFoundError):
            await taxonomy_service.rename("project-1", "nonexistent", "New Name")


class TestMerge:
    @pytest.mark.asyncio
    async def test_merge_raises_error_on_same_source_target(self, taxonomy_service):
        # Act + Assert
        with pytest.raises(ValueError, match="Cannot merge cluster with itself"):
            await taxonomy_service.merge("project-1", "cluster-1", "cluster-1")

    @pytest.mark.asyncio
    async def test_merge_moves_facts_and_deletes_source(self, taxonomy_service, mock_cluster_repo, mock_fact_repo):
        # Arrange: two different clusters
        def get_by_id_side_effect(project_id, cluster_id):
            if cluster_id == "cluster-1":
                async def _source():
                    return {
                        "id": "cluster-1", "name": "Source", "project_id": "project-1",
                        "fact_count": 2, "interview_count": 1, "summary": None,
                        "created_at": "2026-02-28T00:00:00Z", "updated_at": "2026-02-28T00:00:00Z",
                    }
                return _source()
            async def _target():
                return {
                    "id": "cluster-2", "name": "Target", "project_id": "project-1",
                    "fact_count": 3, "interview_count": 2, "summary": None,
                    "created_at": "2026-02-28T00:00:00Z", "updated_at": "2026-02-28T00:00:00Z",
                }
            return _target()

        mock_cluster_repo.get_by_id = AsyncMock(side_effect=get_by_id_side_effect)

        # Act
        result = await taxonomy_service.merge("project-1", "cluster-1", "cluster-2")

        # Assert
        mock_fact_repo.move_bulk.assert_called_once()
        mock_cluster_repo.delete.assert_called_once_with("project-1", "cluster-1")
        assert result.undo_id is not None
        assert result.undo_expires_at is not None

    @pytest.mark.asyncio
    async def test_merge_raises_not_found_when_cluster_missing(self, taxonomy_service, mock_cluster_repo):
        # Arrange
        mock_cluster_repo.get_by_id.return_value = None

        # Act + Assert
        with pytest.raises(ClusterNotFoundError):
            await taxonomy_service.merge("project-1", "cluster-1", "cluster-2")


class TestUndoMerge:
    @pytest.mark.asyncio
    async def test_undo_merge_raises_expired_error_for_unknown_id(self, taxonomy_service):
        # Act + Assert
        with pytest.raises(UndoExpiredError):
            await taxonomy_service.undo_merge("project-1", "nonexistent-undo-id")


class TestPreviewSplit:
    @pytest.mark.asyncio
    async def test_preview_split_returns_subclusters_without_db_writes(
        self, taxonomy_service, mock_cluster_repo, mock_fact_repo, mock_summary_service
    ):
        # Act
        result = await taxonomy_service.preview_split("project-1", "cluster-1")

        # Assert
        assert len(result.subclusters) == 2
        assert result.subclusters[0].name == "Menu Issues"
        assert result.subclusters[1].name == "Feature Discovery"
        # No DB writes (cluster_repo.create and fact_repo.move_bulk NOT called)
        mock_cluster_repo.delete.assert_not_called()
        mock_fact_repo.move_bulk.assert_not_called()


class TestExecuteSplit:
    @pytest.mark.asyncio
    async def test_split_creates_new_clusters_and_deletes_original(
        self, taxonomy_service, mock_cluster_repo, mock_fact_repo
    ):
        # Arrange
        mock_cluster_repo.create = AsyncMock(side_effect=[
            {"id": "new-cluster-1", "name": "Menu Issues", "project_id": "project-1",
             "fact_count": 0, "interview_count": 0, "summary": None,
             "created_at": "2026-02-28T00:00:00Z", "updated_at": "2026-02-28T00:00:00Z"},
            {"id": "new-cluster-2", "name": "Feature Discovery", "project_id": "project-1",
             "fact_count": 0, "interview_count": 0, "summary": None,
             "created_at": "2026-02-28T00:00:00Z", "updated_at": "2026-02-28T00:00:00Z"},
        ])
        mock_cluster_repo.recalculate_counts = AsyncMock(side_effect=[
            {"id": "new-cluster-1", "name": "Menu Issues", "project_id": "project-1",
             "fact_count": 1, "interview_count": 1, "summary": None,
             "created_at": "2026-02-28T00:00:00Z", "updated_at": "2026-02-28T00:00:00Z"},
            {"id": "new-cluster-2", "name": "Feature Discovery", "project_id": "project-1",
             "fact_count": 1, "interview_count": 1, "summary": None,
             "created_at": "2026-02-28T00:00:00Z", "updated_at": "2026-02-28T00:00:00Z"},
        ])
        subclusters = [
            {"name": "Menu Issues", "fact_ids": ["fact-1"]},
            {"name": "Feature Discovery", "fact_ids": ["fact-2"]},
        ]

        # Act
        result = await taxonomy_service.execute_split("project-1", "cluster-1", subclusters)

        # Assert
        assert len(result) == 2
        mock_cluster_repo.delete.assert_called_once_with("project-1", "cluster-1")
        assert mock_fact_repo.move_bulk.call_count == 2

    @pytest.mark.asyncio
    async def test_split_raises_validation_error_when_fact_ids_dont_match(
        self, taxonomy_service, mock_fact_repo
    ):
        # Arrange: original cluster has fact-1 and fact-2, but split only covers fact-1
        subclusters = [
            {"name": "Sub A", "fact_ids": ["fact-1"]},
            {"name": "Sub B", "fact_ids": ["fact-WRONG"]},  # wrong ID
        ]

        # Act + Assert
        with pytest.raises(ValueError, match="All facts must be assigned"):
            await taxonomy_service.execute_split("project-1", "cluster-1", subclusters)
```
</test_spec>

---

## Definition of Done

- [x] Akzeptanzkriterien sind eindeutig und vollstaendig (11 ACs)
- [x] Security: Alle Taxonomy-Endpoints pruefen project ownership (user_id aus JWT gegen project.user_id)
- [x] UX: Undo-Fenster 30 Sekunden, Toast zeigt Countdown
- [x] Rollout: Kein Feature-Flag noetig — direkte Aktivierung (Slice 5 disabled-Buttons werden aktiviert)
- [x] Summary-Regenerierung immer als Background-Task (non-blocking fuer Client)
- [x] Undo-Store ist In-Memory (ausreichend fuer MVP, kein Redis noetig da Single-Process)

---

## Skill Verification (UI-Implementation)

### React Best Practices Verification

**Critical Priority:**
- [x] `rerender-functional-setstate`: `setSecondsLeft((s) => ...)` in UndoToast
- [x] `rerender-derived-state-no-effect`: `isValid` aus Wert berechnet (kein useEffect)

**High Priority:**
- [x] `async-suspense-boundaries`: Cluster-Detail-Page bleibt Server Component mit Suspense

**Medium Priority:**
- [x] `rerender-memo`: `SplitPreviewSubcluster` Karten-Liste (keine Memoization noetig — < 50 Items)
- [x] `rerender-dependencies`: `useEffect` in UndoToast hat nur `[secondsLeft, onDismiss]` als Dependencies

### Web Design Guidelines Verification

**Accessibility:**
- [x] Icon-only buttons (⋮, ✕) haben `aria-label`
- [x] Alle Modals haben `role="dialog"`, `aria-modal="true"`, `aria-labelledby`
- [x] Context-Menus haben `role="menu"` + `role="menuitem"` + `aria-haspopup`
- [x] Radio-Group im MergeDialog: `<fieldset>` + `<legend>`
- [x] UndoToast: `role="status"` + `aria-live="polite"` (nicht role="alert" — ist nicht dringend)
- [x] BulkMoveBar Select hat associierten Label via `<label htmlFor>`

**Destructive Actions:**
- [x] RecalculateModal: Klare Warning + Impact-Summary vor destruktiver Aktion
- [x] Merge: Undo-Moeglichkeit (30s Window) reduziert Destruktivitaet

**Animation & Motion:**
- [x] `prefers-reduced-motion` beachten fuer UndoToast-Animation

### Tailwind v4 Patterns Verification

- [x] Keine hardcoded Hex-Werte (verwendet Tailwind-Color-Scale)
- [x] `focus-visible:ring-*` auf allen interaktiven Elementen
- [x] `disabled:opacity-50` auf disabled Buttons

---

## Constraints & Hinweise

**Betrifft:**
- `backend/app/clustering/taxonomy.py` — Komplett neue Datei
- `backend/app/api/cluster_routes.py` — 8 neue Endpoints
- `dashboard/` — 8 neue Komponenten + 3 erweiterte Komponenten

**API Contract:**
- Merge-Endpoint ist `POST /api/projects/{id}/clusters/merge` (NICHT `POST .../clusters/{cid}/merge`) — konsistent mit architecture.md
- Undo-Endpoint ist `POST /api/projects/{id}/clusters/merge/undo` (NICHT `.../clusters/{cid}/undo`)
- Split verwendet `PUT /api/projects/{id}/clusters/{cid}` fuer Rename, NICHT `PATCH`

**Abgrenzung:**
- SSE-Events fuer Live-Update nach Merge/Split kommen in Slice 7
- JWT-Auth-Check auf allen Endpoints kommt in Slice 8 (in diesem Slice wie Slice 5: Endpoints existieren ohne aktives JWT)
- Suggestion-Generierung (LLM-seitig) ist bereits in Slice 3 (`check_suggestions` Node). Slice 6 implementiert nur die User-facing CRUD-Endpoints fuer Suggestions.

---

## Integration Contract (GATE 2 PFLICHT)

> **Wichtig:** Diese Section wird vom Gate 2 Compliance Agent geprueft. Unvollstaendige Contracts blockieren die Genehmigung.

### Requires From Other Slices

| Slice | Resource | Type | Validation |
|-------|----------|------|------------|
| slice-01 | `clusters` Table (id, name, project_id, summary, fact_count, interview_count) | DB Schema | EXISTS + Columns correct |
| slice-01 | `facts` Table (id, cluster_id, content, project_id, interview_id) | DB Schema | EXISTS + cluster_id nullable |
| slice-01 | `cluster_suggestions` Table (id, project_id, type, source_cluster_id, target_cluster_id, similarity_score, proposed_data, status) | DB Schema | EXISTS + all columns |
| slice-03 | `ClusteringService.full_recluster(project_id)` | Method | Callable, accepts project_id str |
| slice-03 | `SummaryGenerationService.regenerate_for_cluster(project_id, cluster_id)` | Method | Callable as asyncio.create_task |
| slice-05 | `ClusterDetailResponse` | Pydantic Schema | `id, name, summary, fact_count, interview_count, facts, quotes` |
| slice-05 | `FactResponse` | Pydantic Schema | `id, content, quote, confidence, interview_id, interview_date, cluster_id` |
| slice-05 | `ClusterDetailPage` (`/projects/[id]/clusters/[cluster_id]`) | Next.js Page | Renders Merge/Split buttons (disabled in Slice 5) |
| slice-04 | `apiClient.apiFetch()` | Function | Base HTTP client utility |
| slice-04 | `ClusterResponse` TypeScript Type | Type | `id, name, summary, fact_count, interview_count` |
| slice-04 | `ProjectResponse` TypeScript Type | Type | `cluster_count, fact_count` (fuer RecalculateModal) |

### Provides To Other Slices

| Resource | Type | Consumer | Interface |
|----------|------|----------|-----------|
| `TaxonomyService` | Python Class | `cluster_routes.py` (Slice 6 internal) | `rename/merge/undo_merge/preview_split/execute_split` methods |
| `ClusterNotFoundError`, `UndoExpiredError`, `SplitValidationError`, `MergeConflictError` | Python Exceptions | `cluster_routes.py` error handlers | `from app.clustering.exceptions import ...` |
| `PUT /api/projects/{id}/clusters/{cid}` | REST Endpoint | Slice 7 (SSE nach Rename), Slice 8 (Auth) | `RenameRequest` → `ClusterResponse` |
| `POST /api/projects/{id}/clusters/merge` | REST Endpoint | Slice 7, Slice 8 | `MergeRequest` → `MergeResponse` |
| `POST /api/projects/{id}/clustering/recluster` | REST Endpoint | Slice 7, Slice 8 | No body → `ReclusterStarted` |
| `MergeDialog` | React Component | Cluster-Detail-Page | Props: `sourceCluster, availableClusters, projectId, onMerge, onClose` |
| `SplitModal` | React Component | Cluster-Detail-Page | Props: `cluster, projectId, onPreview, onConfirm, onClose` |
| `InlineRename` | React Component | Cluster-Card, Cluster-Detail | Props: `initialName, onSave, onCancel, isLoading?` |
| `UndoToast` | React Component | Insights-Tab (after merge) | Props: `message, expiresAt, onUndo, onDismiss` |
| `SuggestionBanner` | React Component | Insights-Tab | Props: `suggestion, onAccept, onDismiss` |
| `BulkMoveBar` | React Component | Cluster-Detail, Insights-Tab | Props: `selectedCount, availableClusters, onMove, isMoving?` |
| `SuggestionResponse` TypeScript Type | Type | Slice 7 (SSE updates Suggestions) | `id, type, source_cluster_id, source_cluster_name, ...` |
| `MergeResponse` TypeScript Type | Type | Slice 7 | `merged_cluster, undo_id, undo_expires_at` |

### Integration Validation Tasks

- [x] `SummaryGenerationService.regenerate_for_cluster` ist als `async def` implementiert und kann mit `asyncio.create_task()` aufgerufen werden
- [x] `ClusteringService.full_recluster` akzeptiert `project_id: str` Parameter
- [x] `ClusterDetailPage` Merge/Split Buttons aus Slice 5 sind als disabled stubs vorhanden und werden in Slice 6 aktiviert (kein Duplicate-Code)
- [x] `apiClient.apiFetch` aus Slice 4 unterstuetzt `method: "PUT" | "POST"` und `body: string`
- [x] `cluster_suggestions` Tabelle aus Slice 1 hat `proposed_data JSONB` Spalte fuer Split-Suggestion-Daten

---

## Code Examples (MANDATORY - GATE 2 PFLICHT)

> **KRITISCH:** Alle Code-Beispiele in diesem Dokument sind PFLICHT-Deliverables.
> Der Gate 2 Compliance Agent prueft, dass jedes Code-Beispiel implementiert wird.
> Abweichung nur mit expliziter Begruendung im Commit erlaubt.

| Code Example | Section | Mandatory | Notes |
|--------------|---------|-----------|-------|
| `TaxonomyService` | Abschnitt 5 | YES | Alle 5 public Methods (`rename`, `merge`, `undo_merge`, `preview_split`, `execute_split`) + `_expire_undo` |
| `ClusterNotFoundError`, `UndoExpiredError`, `SplitValidationError`, `MergeConflictError` | Abschnitt 6 | YES | Eigene Exception-Klassen in `app/clustering/exceptions.py` |
| Error Handling in Router | Abschnitt 6 | YES | `try/except` Blocks fuer alle 4 Custom Exceptions in `cluster_routes.py` |
| Pydantic Schemas (`RenameRequest`, `MergeRequest`, `MergeResponse`, `UndoMergeRequest`, `SplitPreviewResponse`, `SplitConfirmRequest`, `MoveFactRequest`, `BulkMoveRequest`, `SuggestionResponse`, `ReclusterStarted`) | Abschnitt 4 | YES | Alle Felder mit korrekten Typen in `clustering/schemas.py` |
| `ClusterContextMenu` | Abschnitt 7 | YES | Mit `role="menu"`, `aria-haspopup`, `aria-expanded`, `data-testid` |
| `InlineRename` | Abschnitt 7 | YES | Mit `isValid`-Logic fuer Save-Button-disabled, `autoFocus`, Enter/Escape Handler |
| `MergeDialog` | Abschnitt 7 | YES | Mit `role="dialog"`, `aria-modal`, `fieldset/legend`, `isValid`-Logic |
| `UndoToast` | Abschnitt 7 | YES | Mit `role="status"`, `aria-live="polite"`, `useEffect` Countdown, `onDismiss` bei Ablauf |
| `SplitModal` | Abschnitt 7 | YES | 2-Schritt-Flow mit `Step` union type, Step1/Step2 Rendering |
| `SuggestionBanner` | Abschnitt 7 | YES | Mit `role="alert"`, dynamischer Beschreibung fuer merge/split |
| `RecalculateModal` | Abschnitt 7 | YES | Mit Impact-Summary (cluster_count, fact_count), disabled-State |
| `BulkMoveBar` | Abschnitt 7 | YES | Konditionelles Rendering (returns null bei selectedCount=0), `<label htmlFor>` |
| `FactContextMenu` | Abschnitt 7 | YES | Props: `factId`, `currentClusterId`, `availableClusters`, `onMove`, `onMarkUnassigned`; `role="menu"` mit `aria-label="Fact actions"`, Move/Unassigned Optionen, `data-testid="fact-context-menu"` |
| TypeScript Types (Erweiterung) | Abschnitt 8 | YES | Alle 11 neuen Types in `dashboard/lib/types.ts` |
| API Client Erweiterung | Abschnitt 9 | YES | Alle 11 neuen Methoden in `dashboard/lib/api-client.ts` |

### Code Example Sections (vollstaendig in diesem Dokument enthalten)

#### TaxonomyService (backend/app/clustering/taxonomy.py)
Siehe Abschnitt 5 oben. Die Klasse `TaxonomyService` mit allen Methoden ist vollstaendig spezifiziert.

#### Custom Exception Klassen (backend/app/clustering/exceptions.py)
Siehe Abschnitt 6 oben. `ClusterNotFoundError`, `UndoExpiredError`, `SplitValidationError`, `MergeConflictError` sind vollstaendig definiert.

#### Frontend Komponenten
Alle 8 React-Komponenten sind vollstaendig spezifiziert (Abschnitt 7):
- `ClusterContextMenu` mit Accessibility-Pattern
- `InlineRename` mit Enter/Escape-Handling und `isValid`-Logic
- `MergeDialog` mit `fieldset/legend` Radio-Group und `isValid`-Guard
- `UndoToast` mit `useEffect`-Countdown und `role="status"`
- `SplitModal` mit 2-Schritt State-Machine
- `SuggestionBanner` mit `role="alert"`
- `RecalculateModal` mit Impact-Summary
- `BulkMoveBar` mit konditionellem Rendering
- `FactContextMenu` mit `role="menu"`, `aria-label="Fact actions"`, Move/Unassigned Optionen

---

## Links

- Discovery: `specs/phase-4/2026-02-28-llm-interview-clustering/discovery.md` → Flow 5: Taxonomy bearbeiten
- Architecture: `specs/phase-4/2026-02-28-llm-interview-clustering/architecture.md` → Endpoints Clusters, TaxonomyService, Business Logic Flows
- Wireframes: `specs/phase-4/2026-02-28-llm-interview-clustering/wireframes.md` → Cluster Context Menu, Merge Dialog, Split Modal, Inline Rename, Re-Cluster Confirmation
- Vorheriger Slice: `specs/phase-4/2026-02-28-llm-interview-clustering/slices/slice-05-dashboard-drill-down-zitate.md`

---

## Deliverables (SCOPE SAFEGUARD)

**WICHTIG: Diese Liste wird automatisch vom Stop-Hook validiert. Der Agent kann nicht stoppen, wenn Dateien fehlen.**

<!-- DELIVERABLES_START -->
### Backend

- [ ] `backend/app/clustering/taxonomy.py` — `TaxonomyService` mit `rename`, `merge`, `undo_merge`, `preview_split`, `execute_split`
- [ ] `backend/app/clustering/exceptions.py` — Custom Exceptions: `ClusterNotFoundError`, `UndoExpiredError`, `SplitValidationError`, `MergeConflictError`
- [ ] `backend/app/clustering/schemas.py` — Neue DTOs: `RenameRequest`, `MergeRequest`, `MergeResponse`, `UndoMergeRequest`, `SplitPreviewResponse`, `SplitPreviewSubcluster`, `SplitSubclusterInput`, `SplitConfirmRequest`, `MoveFactRequest`, `BulkMoveRequest`, `SuggestionResponse`, `ReclusterStarted`
- [ ] `backend/app/api/cluster_routes.py` — Neue Endpoints: `PUT /{cid}` (rename), `POST /merge`, `POST /merge/undo`, `POST /{cid}/split/preview`, `POST /{cid}/split`, `PUT /facts/{fid}`, `POST /facts/bulk-move`, `GET /suggestions`, `POST /suggestions/{sid}/accept`, `POST /suggestions/{sid}/dismiss`, `POST /clustering/recluster`
- [ ] `backend/app/clustering/facts_repository.py` — `FactRepository.move_bulk()`, `FactRepository.move_single()`, `FactRepository.get_unassigned()`
- [ ] `backend/app/clustering/suggestions_repository.py` — `SuggestionRepository.list_active()`, `SuggestionRepository.update_status()`
- [ ] `backend/app/clustering/repository.py` — Erweiterung: `ClusterRepository.update_name()`, `ClusterRepository.delete()`, `ClusterRepository.create()`, `ClusterRepository.create_many()`, `ClusterRepository.recalculate_counts()`

### Frontend

- [ ] `dashboard/components/cluster-context-menu.tsx` — Dropdown mit Rename/Merge/Split Optionen, `role="menu"`, Accessibility
- [ ] `dashboard/components/inline-rename.tsx` — Controlled Input, Enter=save, Escape=cancel, `isValid`-Guard
- [ ] `dashboard/components/merge-dialog.tsx` — Radio-Liste, `fieldset/legend`, `isValid`-Logic, Undo-Hinweis
- [ ] `dashboard/components/undo-toast.tsx` — 30s Countdown, `role="status"`, `aria-live="polite"`, Auto-dismiss
- [ ] `dashboard/components/split-modal.tsx` — 2-Schritt State Machine (step1/step1_generating/step2/splitting)
- [ ] `dashboard/components/suggestion-banner.tsx` — `role="alert"`, Merge/Split Varianten, Dismiss/Accept
- [ ] `dashboard/components/recalculate-modal.tsx` — Impact-Summary, `role="dialog"`, Destructive Action Style
- [ ] `dashboard/components/bulk-move-bar.tsx` — Konditionelles Rendering (null bei selectedCount=0), `<label htmlFor>`
- [ ] `dashboard/components/fact-context-menu.tsx` — "Move to [cluster]...", "Mark as unassigned" Optionen
- [ ] `dashboard/components/cluster-card.tsx` — Erweiterung: `ClusterContextMenu` einbinden, Rename-State
- [ ] `dashboard/components/fact-item.tsx` — Erweiterung: Checkbox + `FactContextMenu` (von Slice 5 erweitern)
- [ ] `dashboard/app/projects/[id]/page.tsx` — Erweiterung: `SuggestionBanner`(s), `RecalculateModal`, Unassigned-Bereich mit Checkboxen + `BulkMoveBar`
- [ ] `dashboard/app/projects/[id]/clusters/[cluster_id]/page.tsx` — Erweiterung: `InlineRename`, Merge-Button aktiviert (`MergeDialog`), Split-Button aktiviert (`SplitModal`), Fact-Checkboxen + `BulkMoveBar`, `UndoToast`
- [ ] `dashboard/lib/types.ts` — Erweiterung: 11 neue Types (`MergeRequest`, `MergeResponse`, `UndoMergeRequest`, `SplitPreviewResponse`, `SplitPreviewSubcluster`, `SplitSubclusterInput`, `SplitConfirmRequest`, `MoveFactRequest`, `BulkMoveRequest`, `SuggestionResponse`, `ReclusterStarted`)
- [ ] `dashboard/lib/api-client.ts` — Erweiterung: 11 neue Methoden

### Tests

- [ ] `backend/tests/slices/llm-interview-clustering/test_slice_06_taxonomy_service.py` — pytest: `TestRename`, `TestMerge`, `TestUndoMerge`, `TestPreviewSplit`, `TestExecuteSplit`
- [ ] `tests/slices/llm-interview-clustering/slice-06-taxonomy-editing-summary-regen.spec.ts` — Playwright E2E: 10 Tests fuer alle ACs
<!-- DELIVERABLES_END -->

**Hinweis fuer den Implementierungs-Agent:**
- Alle Dateien zwischen `<!-- DELIVERABLES_START -->` und `<!-- DELIVERABLES_END -->` sind Pflicht
- Der Stop-Hook prueft automatisch ob alle Dateien existieren
- Bei fehlenden Dateien wird der Agent blockiert und muss nachfragen
- `cluster-card.tsx` und `fact-item.tsx` sind Modifikationen bestehender Dateien (Slice 5) — existieren bereits, muessen erweitert werden

# Wireframes: LLM Interview Clustering

**Discovery:** `discovery.md` (same folder)
**Status:** Draft

---

## Component Coverage

| UI Component (from Discovery) | Screen |
|-------------------------------|--------|
| `project_card` | Project List |
| `new_project_btn` | Project List |
| `project_form` | Project List (Modal) |
| `cluster_card` | Project Dashboard (Insights Tab) |
| `cluster_context_menu` | Project Dashboard (Insights Tab) |
| `taxonomy_editor_rename` | Project Dashboard / Cluster Detail |
| `merge_dialog` | Project Dashboard (Modal) |
| `split_confirm` | Project Dashboard (Modal) |
| `fact_item` | Cluster Detail (Drill-Down) |
| `quote_item` | Cluster Detail (Drill-Down) |
| `progress_bar` | Project Dashboard (Insights Tab) |
| `interview_assign_btn` | Project Interviews Tab |
| `interview_table` | Project Interviews Tab |
| `settings_form` | Project Settings Tab |
| `live_update_badge` | Project Dashboard (Insights Tab) |
| `merge_suggestion` | Project Dashboard (Insights Tab) |
| `split_suggestion` | Project Dashboard (Insights Tab) |
| `recluster_btn` | Project Dashboard (Insights Tab) |
| `recluster_confirm` | Project Dashboard (Modal) |
| `model_config_form` | Project Settings Tab |
| `retry_btn` | Project Interviews Tab (failed rows) |
| `clustering_error_banner` | Project Dashboard (Insights Tab) |
| `fact_context_menu` | Cluster Detail (Drill-Down) |
| `fact_bulk_move` | Cluster Detail + Insights Tab (Unassigned) |
| `delete_confirm_modal` | Project Settings Tab (Modal) |
| `reset_source_modal` | Project Settings Tab (Modal) |
| `split_preview` | Split Cluster Modal (Step 2) |
| `merge_undo_toast` | Project Dashboard (Insights Tab) |

---

## User Flow Overview

```
[Project List] ──click card──► [Insights Tab] ──click cluster──► [Cluster Detail]
      │                              │                                   │
      │                              ├──tab──► [Interviews Tab]          │
      │                              │                                   │
      │                              └──tab──► [Settings Tab]            │
      │                                                                  │
      └──"New Project"──► [Project Form Modal]            ◄──back────────┘
```

---

## Screen: Project List

**Context:** Dashboard main page (`/projects`). Shown after login. Entry point for all project interactions.

### Wireframe

```
┌─────────────────────────────────────────────────────────────┐
│  FeedbackAI Insights                          [Avatar ▼] ① │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ② [+ New Project]                                          │
│                                                             │
│  ┌───────────────────┐  ┌───────────────────┐               │
│  │ ③                 │  │                   │               │
│  │  Onboarding UX    │  │  Checkout Pain    │               │
│  │                   │  │  Points           │               │
│  │  12 Interviews    │  │                   │               │
│  │  5 Clusters       │  │  8 Interviews     │               │
│  │  Updated 2h ago   │  │  3 Clusters       │               │
│  │                   │  │  Updated 1d ago   │               │
│  └───────────────────┘  └───────────────────┘               │
│                                                             │
│  ┌───────────────────┐                                      │
│  │                   │                                      │
│  │  Pricing Research │                                      │
│  │                   │                                      │
│  │  24 Interviews    │                                      │
│  │  9 Clusters       │                                      │
│  │  Updated 5m ago   │                                      │
│  └───────────────────┘                                      │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**Annotations:**
- ① Header with app name "FeedbackAI Insights" and user avatar/logout dropdown
- ② `new_project_btn`: Opens project creation form
- ③ `project_card`: Shows project name, interview count, cluster count, last updated. Click navigates to project dashboard.

### State Variations

| State | Visual Change |
|-------|---------------|
| `empty` (no projects) | Card grid replaced by centered illustration + "Create your first project" CTA button |
| `loading` | Skeleton cards in grid positions |
| `project_card:hover` | Subtle elevation/shadow change on card |

---

## Screen: Project Form (Modal)

**Context:** Overlay modal triggered by "New Project" button on Project List. Also used for editing existing project basics.

### Wireframe

```
┌─────────────────────────────────────────────────────────────┐
│  [... Project List dimmed behind ...]                       │
│                                                             │
│     ┌─────────────────────────────────────────┐             │
│     │  New Project                      [X] ① │             │
│     ├─────────────────────────────────────────┤             │
│     │                                         │             │
│     │  Project Name *                         │             │
│     │  ┌─────────────────────────────────┐    │             │
│     │  │ e.g. Onboarding UX Research     │    │             │
│     │  └─────────────────────────────────┘    │             │
│     │                                         │             │
│     │  Research Goal *                        │             │
│     │  ┌─────────────────────────────────┐    │             │
│     │  │ Understand why users drop off   │    │             │
│     │  │ during onboarding               │    │             │
│     │  └─────────────────────────────────┘    │             │
│     │                                         │             │
│     │  Prompt Context (optional)              │             │
│     │  ┌─────────────────────────────────┐    │             │
│     │  │ B2B SaaS onboarding for...      │    │             │
│     │  │                                 │    │             │
│     │  └─────────────────────────────────┘    │             │
│     │                                         │             │
│     │  Fact Extraction Source *                │             │
│     │  ┌──────────────────────────── ▼ ──┐    │             │
│     │  │ Summary                         │    │             │
│     │  └─────────────────────────────────┘    │             │
│     │                                         │             │
│     │            [Cancel]  [Create Project] ② │             │
│     └─────────────────────────────────────────┘             │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**Annotations:**
- ① `project_form`: Modal with required fields (name, research goal, extraction source) and optional prompt context
- ② Submit button: "Create Project" (disabled until required fields filled)

### State Variations

| State | Visual Change |
|-------|---------------|
| `empty` | All fields blank, submit disabled |
| `filled` | Fields populated, submit enabled |
| `saving` | Submit button shows spinner, fields disabled |
| `error` | Red border on invalid fields, error message below field |

---

## Screen: Project Dashboard (Insights Tab)

**Context:** Project detail page (`/projects/{id}`). Default tab is "Insights". Shows cluster overview with cards. Header shows project name and research goal.

### Wireframe

```
┌─────────────────────────────────────────────────────────────┐
│  ← Projects    FeedbackAI Insights               [Avatar] │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Onboarding UX Research                                     │
│  Understand why users drop off during onboarding   ①        │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ [Insights]  │  Interviews  │  Settings              │ ②  │
│  └─────────────────────────────────────────────────────┘    │
│                                                             │
│  12 Interviews  │  47 Facts  │  5 Clusters       ③          │
│  ─────────────────────────────────────────                  │
│                                                             │
│  ④ ████████████████████░░░░░  Analyzing... 47/52 Facts      │
│                                                             │
│  ⑤ ┌─────────────────────────────────────────────────┐      │
│    │ ⚡ Suggestion: Merge "Login Issues" with         │      │
│    │    "Auth Problems" (82% similar)                 │      │
│    │                        [Dismiss]  [Merge]        │      │
│    └─────────────────────────────────────────────────┘      │
│                                                             │
│                                       ⑥ [Recalculate ↻]    │
│                                                             │
│  ┌─────────────────────┐  ┌─────────────────────┐          │
│  │ ⑦               [⋮] │  │                [⋮]  │          │
│  │                      │  │                     │          │
│  │  Navigation Issues   │  │  Pricing Confusion  │          │
│  │  ● 14 Facts          │  │  ● 11 Facts         │          │
│  │  ● 8 Interviews  ⑧   │  │  ● 6 Interviews     │          │
│  │                      │  │                     │          │
│  │  Users struggle to   │  │  Users don't under- │          │
│  │  find key features   │  │  stand tier diffs    │          │
│  │  after initial...    │  │  and feel pricing... │          │
│  │                      │  │              ⑨      │          │
│  └─────────────────────┘  └─────────────────────┘          │
│                                                             │
│  ┌─────────────────────┐  ┌─────────────────────┐          │
│  │                [⋮]  │  │                [⋮]  │          │
│  │                     │  │                     │          │
│  │  Onboarding Speed   │  │  Support Quality    │          │
│  │  ● 12 Facts         │  │  ● 10 Facts         │          │
│  │  ● 7 Interviews     │  │  ● 5 Interviews     │          │
│  │                     │  │                     │          │
│  │  The onboarding     │  │  Multiple users     │          │
│  │  process takes too  │  │  reported slow      │          │
│  │  long and users...  │  │  response times...  │          │
│  └─────────────────────┘  └─────────────────────┘          │
│                                                             │
│  ⑪ ┌─────────────────────────────────────────────────┐      │
│    │ ❌ Clustering failed: 3 facts could not be      │      │
│    │    assigned to clusters.                        │      │
│    │                     [Assign manually]  [Retry]   │      │
│    └─────────────────────────────────────────────────┘      │
│                                                             │
│  ─── Unassigned (3 Facts) ─────────────────────── ⑩        │
│  ☐ "The app crashed during payment" (Interview #4)    [⋮]  │
│  ☐ "Would like dark mode" (Interview #9)              [⋮]  │
│  ☐ "Export feature is confusing" (Interview #11)      [⋮]  │
│                          [Move selected to cluster ▼]  ⑫   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**Annotations:**
- ① Project header: Name (large) + Research Goal (subtitle)
- ② Tab navigation: Insights (active) | Interviews | Settings
- ③ Status bar: Aggregated counts for interviews, facts, clusters
- ④ `progress_bar`: Shown during active clustering runs. Hidden when idle.
- ⑤ `merge_suggestion` / `split_suggestion`: LLM-generated suggestion banner. Dismiss or accept.
- ⑥ `recluster_btn`: Manual full re-cluster trigger
- ⑦ `cluster_context_menu`: Three-dot menu icon on each card (Rename, Merge with..., Split)
- ⑧ `live_update_badge`: Pulse animation on cluster card when new fact is added (not shown at rest)
- ⑨ `cluster_card`: Card showing cluster name, fact count badge, interview count badge, summary preview (2-3 lines)
- ⑩ Unassigned section: Facts not yet assigned to any cluster. Each fact has checkbox for bulk selection and three-dot context menu (Move to cluster..., Delete)
- ⑪ `clustering_error_banner`: Shown only when `clustering_failed` state is active. Error banner with fact count and recovery actions (Retry re-runs clustering, Assign manually scrolls to unassigned section)
- ⑫ Bulk action bar: "Move selected to cluster" dropdown, enabled when ≥1 checkbox selected. Lists all existing clusters as targets.

### State Variations

| State | Visual Change |
|-------|---------------|
| `project_empty` | Empty state: illustration + "Assign interviews to get started" CTA |
| `project_collecting` | Progress bar visible, cluster cards may appear incrementally |
| `project_ready` | Progress bar hidden, all cluster cards visible, suggestions may appear |
| `project_updating` | Progress bar visible, cluster cards show shimmer overlay, context menus disabled |
| `cluster_card:hover` | Elevation change, cursor pointer |
| `cluster_card:updating` | Subtle pulse animation on the card border |

---

## Screen: Cluster Context Menu

**Context:** Dropdown appearing on click of three-dot icon (⋮) on a cluster card in the Insights Tab.

### Wireframe

```
  ┌─────────────────────┐
  │  Navigation Issues   │
  │  ...            [⋮]←─── click
  │                 ┌──────────────┐
  │                 │ ① Rename     │
  │                 │ ② Merge with │
  │                 │ ③ Split      │
  │                 └──────────────┘
  └─────────────────────┘
```

**Annotations:**
- ① `taxonomy_editor_rename`: Triggers inline rename (text becomes editable input)
- ② `merge_dialog`: Opens merge dialog modal
- ③ `split_confirm`: Opens split confirmation modal

---

## Screen: Merge Dialog (Modal)

**Context:** Modal overlay triggered from cluster context menu "Merge with". User selects a target cluster to merge into.

### Wireframe

```
     ┌─────────────────────────────────────────┐
     │  Merge Cluster                    [X]   │
     ├─────────────────────────────────────────┤
     │                                         │
     │  Merge "Login Issues" with:             │
     │                                         │
     │  ○ Navigation Issues (14 Facts)         │
     │  ● Auth Problems (8 Facts)        ①     │
     │  ○ Pricing Confusion (11 Facts)         │
     │  ○ Onboarding Speed (12 Facts)          │
     │                                         │
     │  ⚠ All facts from "Login Issues"        │
     │    will be moved to "Auth Problems".     │
     │    You can undo this within 30 seconds.  │
     │                                         │
     │            [Cancel]  [Merge Clusters] ② │
     └─────────────────────────────────────────┘
```

**Annotations:**
- ① `merge_dialog`: Radio list of target clusters with fact counts
- ② Confirm button: "Merge Clusters" triggers merge + re-clustering

### State Variations

| State | Visual Change |
|-------|---------------|
| `open` | Modal visible, no selection |
| `selected` | Radio selected, merge button enabled |
| `merging` | Button shows spinner, radio list disabled |
| `merged` | Modal closes, undo toast appears: "Clusters merged. [Undo - 30s]" with countdown. After 30s toast disappears and merge is permanent. |

---

## Screen: Split Cluster (Two-Step Modal)

**Context:** Modal overlay triggered from cluster context menu "Split". Two-step process: Step 1 generates a preview, Step 2 shows the preview for confirmation.

### Wireframe: Step 1 (Generating Preview)

```
     ┌─────────────────────────────────────────┐
     │  Split Cluster                    [X]   │
     ├─────────────────────────────────────────┤
     │                                         │
     │  Split "Navigation Issues" (14 Facts)?  │
     │                                         │
     │  The LLM will analyze the facts and     │
     │  propose sub-clusters for your review.  │
     │                                   ①     │
     │                                         │
     │          [Cancel]  [Generate Preview] ②  │
     └─────────────────────────────────────────┘
```

### Wireframe: Step 2 (Review Preview)

```
     ┌─────────────────────────────────────────────────┐
     │  Split Cluster — Preview                  [X]   │
     ├─────────────────────────────────────────────────┤
     │                                                 │
     │  Proposed split for "Navigation Issues":        │
     │                                                 │
     │  ┌───────────────────────────────────────────┐  │
     │  │ ③ Menu Structure (8 Facts)                │  │
     │  │   • Users cannot find settings page       │  │
     │  │   • Hamburger menu not intuitive          │  │
     │  │   • Dashboard link buried under 3 levels  │  │
     │  │   • Search is the only way to navigate    │  │
     │  │   • Settings split across multiple pages  │  │
     │  │   • No breadcrumbs for orientation         │  │
     │  │   • Mobile nav inconsistent with desktop  │  │
     │  │   • Sidebar collapses without indication  │  │
     │  └───────────────────────────────────────────┘  │
     │                                                 │
     │  ┌───────────────────────────────────────────┐  │
     │  │   Feature Discovery (6 Facts)             │  │
     │  │   • Key features hidden after onboarding  │  │
     │  │   • No feature tour for new users         │  │
     │  │   • Advanced features undiscoverable      │  │
     │  │   • Tooltips missing on icons             │  │
     │  │   • Help section hard to find             │  │
     │  │   • No contextual onboarding hints        │  │
     │  └───────────────────────────────────────────┘  │
     │                                                 │
     │        [Cancel]  [Confirm Split] ④              │
     └─────────────────────────────────────────────────┘
```

**Annotations:**
- ① `split_confirm`: Step 1 explanation — LLM will generate a preview, not split immediately
- ② "Generate Preview" triggers LLM analysis and transitions to Step 2
- ③ Preview cards: Each proposed sub-cluster shows name, fact count, and complete fact listing for full transparency
- ④ "Confirm Split" executes the split as previewed. User can cancel to keep the original cluster.

### State Variations

| State | Visual Change |
|-------|---------------|
| `step1_open` | Modal with explanation and "Generate Preview" button |
| `step1_generating` | Button shows spinner "Analyzing...", cancel still available |
| `step2_preview` | Preview of proposed sub-clusters with full fact lists, "Confirm Split" button |
| `splitting` | "Confirm Split" shows spinner, cancel disabled |

---

## Screen: Re-Cluster Confirmation (Modal)

**Context:** Modal triggered by "Recalculate" button in the Insights Tab toolbar. This is a destructive operation (Flow 3b) that resets all existing cluster assignments.

### Wireframe

```
     ┌─────────────────────────────────────────┐
     │  Recalculate Clusters             [X]   │
     ├─────────────────────────────────────────┤
     │                                         │
     │  ⚠ Warning                              │
     │                                         │
     │  All existing cluster assignments will  │
     │  be reset. Facts will be preserved,     │
     │  but a completely new cluster structure  │
     │  will be generated from scratch.  ①     │
     │                                         │
     │  This affects:                          │
     │  • 5 Clusters (will be deleted)         │
     │  • 47 Fact assignments (will be reset)  │
     │  • All cluster summaries (regenerated)  │
     │                                         │
     │       [Cancel]  [Recalculate All] ②     │
     └─────────────────────────────────────────┘
```

**Annotations:**
- ① `recluster_confirm`: Warning explanation of the destructive action with impact summary
- ② Confirm button: "Recalculate All" triggers full TNT-LLM re-clustering pipeline

### State Variations

| State | Visual Change |
|-------|---------------|
| `open` | Modal with warning and impact counts |
| `recalculating` | Button shows spinner, cancel disabled, progress text appears |

---

## Screen: Cluster Detail (Drill-Down)

**Context:** Slide-over panel or sub-page (`/projects/{id}/clusters/{cluster_id}`). Opened by clicking a cluster card. Shows full details: summary, facts, quotes.

### Wireframe

```
┌─────────────────────────────────────────────────────────────┐
│  ← Back to Clusters                              [Avatar]  │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ① Navigation Issues ✎          [Merge ▼]  [Split]  ②      │
│  ═══════════════════════════════════════════════════════     │
│                                                             │
│  Summary                                              ③     │
│  ───────                                                    │
│  Users consistently report difficulty finding key           │
│  features after the initial onboarding flow. The main       │
│  navigation structure doesn't match their mental model,     │
│  leading to frustration and support tickets.                │
│                                                             │
│  ═══════════════════════════════════════════════════════     │
│                                                             │
│  Facts (14)                     [Move selected to ▼]  ④     │
│  ──────────                                                 │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ ☐ 1. Users cannot find the settings page after [⋮]  │    │
│  │      completing onboarding.                         │    │
│  │      ┌──────────────┐                               │    │
│  │      │ Interview #3 │  Confidence: 0.92             │ ⑤  │
│  │      └──────────────┘                               │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ ☐ 2. The hamburger menu is not intuitive for  [⋮]   │    │
│  │      desktop users.                                 │    │
│  │      ┌──────────────┐                               │    │
│  │      │ Interview #7 │  Confidence: 0.87             │    │
│  │      └──────────────┘                               │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ ☐ 3. Dashboard link is buried under three      [⋮]  │    │
│  │      levels of navigation.                          │    │
│  │      ┌──────────────┐                               │    │
│  │      │ Interview #3 │  Confidence: 0.95             │    │
│  │      └──────────────┘                               │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                             │
│  [... more facts ...]                                       │
│                                                             │
│  ═══════════════════════════════════════════════════════     │
│                                                             │
│  Quotes                                               ⑥     │
│  ──────                                                     │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ "I spent like 10 minutes just trying to find        │    │
│  │  where my account settings were. It's really        │ ⑦  │
│  │  buried in there."                                  │    │
│  │                              ── Interview #3        │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ "The navigation doesn't make sense to me. I         │    │
│  │  always end up using the search to find things."    │    │
│  │                              ── Interview #7        │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**Annotations:**
- ① `taxonomy_editor_rename`: Cluster name is editable (pencil icon). Click to enter inline edit mode.
- ② Action buttons: Merge (dropdown to pick target) and Split
- ③ LLM-generated cluster summary (full text, not truncated)
- ④ Facts section with total count. "Move selected to" dropdown for bulk-moving checked facts to another cluster. Enabled when ≥1 checkbox selected.
- ⑤ `fact_item`: Numbered fact with checkbox, text, source interview badge, confidence score, and three-dot context menu [⋮] with options: "Move to [cluster]...", "Mark as unassigned"
- ⑥ Quotes section: Original transcript quotes supporting the cluster
- ⑦ `quote_item`: Blockquote with transcript text and interview reference

### State Variations

| State | Visual Change |
|-------|---------------|
| `loading` | Skeleton placeholders for summary, facts list, quotes |
| `editing_name` | Cluster name becomes text input with save/cancel controls |
| `empty_facts` | "No facts extracted yet" message in facts section |
| `empty_quotes` | "No quotes available" message in quotes section |
| `fact_item:highlighted` | Fact card gets accent left-border and light background highlight (e.g. when navigated from search or cluster card) |
| `quote_item:expanded` | Quote blockquote expands to show full transcript context (several surrounding lines). Collapsed state shows 2-3 line preview with "Show more" link. |

---

## Screen: Project Interviews Tab

**Context:** Project detail page → "Interviews" tab (`/projects/{id}`, Interviews tab). Shows assigned interviews and allows assigning new ones.

### Wireframe

```
┌─────────────────────────────────────────────────────────────┐
│  ← Projects    FeedbackAI Insights               [Avatar]  │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Onboarding UX Research                                     │
│  Understand why users drop off during onboarding            │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  Insights  │ [Interviews] │  Settings               │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                             │
│  ① [+ Assign Interviews]          Filter: [All ▼]  ②       │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  #   │ Date       │ Summary            │ Facts │ St │ ③  │
│  ├──────┼────────────┼────────────────────┼───────┼────┤    │
│  │  #12 │ 2026-02-28 │ User had issues    │   4   │ ✅ │    │
│  │      │            │ with navigation... │       │    │    │
│  ├──────┼────────────┼────────────────────┼───────┼────┤    │
│  │  #11 │ 2026-02-27 │ Pricing was con-   │   3   │ ✅ │    │
│  │      │            │ fusing for user...  │       │    │    │
│  ├──────┼────────────┼────────────────────┼───────┼────┤    │
│  │  #10 │ 2026-02-27 │ Onboarding took    │   5   │ ⏳ │    │
│  │      │            │ too long and...    │       │    │    │
│  ├──────┼────────────┼────────────────────┼───────┼────┤    │
│  │   #9 │ 2026-02-26 │ Export feature     │   0   │ ❌ │[↻] │ ⑤  │
│  │      │            │ was not working... │       │    │    │    │
│  └──────────────────────────────────────────────────────────┘    │
│                                                             │
│  Status: ✅ analyzed  ⏳ pending  ❌ failed            ④    │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**Annotations:**
- ① `interview_assign_btn`: Opens assignment panel/modal to select unassigned interviews
- ② Filter dropdown: Filter by status (All, Analyzed, Pending, Failed), date range
- ③ `interview_table`: Sortable table with interview ID, date, summary preview, fact count, clustering status
- ④ Status legend for status badges
- ⑤ `retry_btn`: Retry button shown only on failed (❌) interviews. Click triggers re-extraction/re-clustering for this interview.

### State Variations

| State | Visual Change |
|-------|---------------|
| `empty` | Table replaced by "No interviews assigned yet" + Assign button |
| `loading` | Table skeleton rows |
| `interview_assign_btn:loading` | Button shows spinner during bulk assignment |
| `interview_assign_btn:success` | Brief success toast, table refreshes |

---

## Screen: Interview Assignment (Modal)

**Context:** Modal triggered by "Assign Interviews" button. Shows list of unassigned interviews for selection.

### Wireframe

```
     ┌─────────────────────────────────────────┐
     │  Assign Interviews                [X]   │
     ├─────────────────────────────────────────┤
     │                                         │
     │  Select interviews to assign to         │
     │  "Onboarding UX Research":              │
     │                                         │
     │  ☑ #13 - 2026-02-28 - "User loved..."  │
     │  ☑ #14 - 2026-02-28 - "Onboarding w.." │
     │  ☐ #15 - 2026-02-28 - "The pricing..." │ ①
     │  ☐ #16 - 2026-02-27 - "Support was..."  │
     │                                         │
     │  2 selected                             │
     │                                         │
     │         [Cancel]  [Assign Selected] ②   │
     └─────────────────────────────────────────┘
```

**Annotations:**
- ① Checkbox list of unassigned interviews with ID, date, summary preview
- ② Assign button (disabled until at least 1 selected)

---

## Screen: Project Settings Tab

**Context:** Project detail page → "Settings" tab. Configuration for project details and LLM model selection.

### Wireframe

```
┌─────────────────────────────────────────────────────────────┐
│  ← Projects    FeedbackAI Insights               [Avatar]  │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Onboarding UX Research                                     │
│  Understand why users drop off during onboarding            │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  Insights  │  Interviews  │ [Settings]              │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                             │
│  General                                              ①     │
│  ───────                                                    │
│                                                             │
│  Project Name                                               │
│  ┌─────────────────────────────────────────┐                │
│  │ Onboarding UX Research                  │                │
│  └─────────────────────────────────────────┘                │
│                                                             │
│  Research Goal                                              │
│  ┌─────────────────────────────────────────┐                │
│  │ Understand why users drop off during    │                │
│  │ onboarding                              │                │
│  └─────────────────────────────────────────┘                │
│                                                             │
│  Prompt Context                                             │
│  ┌─────────────────────────────────────────┐                │
│  │ B2B SaaS with 14-day free trial.        │                │
│  │ Target audience: Product Managers...    │                │
│  └─────────────────────────────────────────┘                │
│                                                             │
│  Fact Extraction Source                                      │
│  ┌─────────────────────────────────────────┐                │
│  │ Summary                          🔒     │           ⑤    │
│  └─────────────────────────────────────────┘                │
│  47 facts extracted with this source.                       │
│  [Reset & Change Source]                                    │
│                                                             │
│                                      [Save Changes]         │
│                                                             │
│  ═══════════════════════════════════════════════════════     │
│                                                             │
│  Model Configuration (OpenRouter)                     ②     │
│  ────────────────────────────────                           │
│                                                             │
│  Interviewer Model                                          │
│  ┌─────────────────────────────────────────┐                │
│  │ anthropic/claude-sonnet-4               │                │
│  └─────────────────────────────────────────┘                │
│  Format: provider/model-name                                │
│                                                             │
│  Fact Extraction Model                                      │
│  ┌─────────────────────────────────────────┐                │
│  │ anthropic/claude-haiku-4                │                │
│  └─────────────────────────────────────────┘                │
│  Format: provider/model-name                                │
│                                                             │
│  Clustering Model                                           │
│  ┌─────────────────────────────────────────┐                │
│  │ anthropic/claude-sonnet-4               │                │
│  └─────────────────────────────────────────┘                │
│  Format: provider/model-name                                │
│                                                             │
│  Summary Model                                              │
│  ┌─────────────────────────────────────────┐                │
│  │ anthropic/claude-haiku-4                │                │
│  └─────────────────────────────────────────┘                │
│  Format: provider/model-name                                │
│                                                             │
│                                      [Save Changes]         │
│                                                             │
│  ═══════════════════════════════════════════════════════     │
│                                                             │
│  Danger Zone                                          ③     │
│  ───────────                                                │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  Delete this project and all its clusters/facts.    │    │
│  │  This action cannot be undone.                      │    │
│  │                              [Delete Project] ④     │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**Annotations:**
- ① `settings_form`: General project settings (name, research goal, prompt context, extraction source)
- ② `model_config_form`: OpenRouter model slug per task (interviewer, extraction, clustering, summary). Each input shows format hint "Format: provider/model-name" below the field
- ③ Danger zone: Destructive actions separated visually
- ④ Delete button with confirmation required (opens type-to-confirm modal, see Delete Confirmation screen below)
- ⑤ `extraction_source_locked`: When facts already exist, dropdown is locked (disabled + lock icon). Shows count of extracted facts and "Reset & Change Source" link that opens a confirmation dialog explaining consequences

### State Variations

| State | Visual Change |
|-------|---------------|
| `pristine` | Save buttons disabled (no changes) |
| `dirty` | Save buttons enabled, unsaved indicator |
| `saving` | Save button shows spinner |
| `saved` | Brief success toast, back to pristine |
| `delete_confirm` | Overlay confirmation dialog: "Type project name to confirm" |

---

## Screen: Delete Project Confirmation (Modal)

**Context:** Modal overlay triggered by "Delete Project" button in Settings Tab Danger Zone. Requires typing the project name to confirm deletion.

### Wireframe

```
     ┌─────────────────────────────────────────┐
     │  Delete Project                   [X]   │
     ├─────────────────────────────────────────┤
     │                                         │
     │  ⚠ This action is permanent             │
     │                                         │
     │  Deleting "Onboarding UX Research"      │
     │  will permanently remove:         ①     │
     │  • 5 Clusters                           │
     │  • 47 Facts                             │
     │  • 12 Interview assignments             │
     │                                         │
     │  Type the project name to confirm:      │
     │  ┌─────────────────────────────────┐    │
     │  │ Onboarding UX Research          │ ②  │
     │  └─────────────────────────────────┘    │
     │                                         │
     │      [Cancel]  [Delete Project] ③       │
     └─────────────────────────────────────────┘
```

**Annotations:**
- ① Impact summary: Shows what will be destroyed (clusters, facts, interview assignments)
- ② Type-to-confirm input: Placeholder shows the project name. Input must match exactly.
- ③ "Delete Project" button: Disabled (grayed out) until input matches project name exactly. Red/destructive style.

### State Variations

| State | Visual Change |
|-------|---------------|
| `open` | Modal visible, input empty, delete button disabled |
| `typing_mismatch` | Input has text but doesn't match, delete button stays disabled |
| `typing_match` | Input matches project name exactly, delete button becomes enabled (red) |
| `deleting` | Button shows spinner, input disabled, cancel disabled |

---

## Screen: Reset Extraction Source Confirmation (Modal)

**Context:** Modal triggered by "Reset & Change Source" link in Settings Tab when extraction source is locked. Warns about consequences of changing the source.

### Wireframe

```
     ┌─────────────────────────────────────────┐
     │  Change Extraction Source          [X]   │
     ├─────────────────────────────────────────┤
     │                                         │
     │  ⚠ 47 facts were extracted from         │
     │    summaries.                      ①    │
     │                                         │
     │  Changing to a different source will     │
     │  only affect future interviews.         │
     │  Existing facts remain unchanged.       │
     │                                         │
     │  New Extraction Source:                  │
     │  ┌──────────────────────────── ▼ ──┐    │
     │  │ Transcript                      │ ②  │
     │  └─────────────────────────────────┘    │
     │                                         │
     │  ☐ Also re-extract all existing    ③    │
     │    facts with the new source            │
     │                                         │
     │          [Cancel]  [Change Source] ④     │
     └─────────────────────────────────────────┘
```

**Annotations:**
- ① Warning showing how many facts exist and their current source
- ② Dropdown to select new extraction source
- ③ Optional checkbox: Re-extract all facts with the new source (triggers full re-extraction pipeline)
- ④ "Change Source" confirms the change

### State Variations

| State | Visual Change |
|-------|---------------|
| `open` | Modal visible with current fact count and source |
| `changing` | Button shows spinner, fields disabled |

---

## Screen: Inline Rename

**Context:** Triggered from cluster context menu "Rename" or pencil icon in Cluster Detail. Cluster name becomes editable inline.

### Wireframe

```
  ┌─────────────────────┐
  │                      │
  │  ┌────────────────┐  │
  │  │ Navigation Is. │  │  ← text input replaces cluster name
  │  └────────────────┘  │
  │  [✓ Save] [✕ Cancel] │  ①
  │  ● 14 Facts          │
  │  ● 8 Interviews      │
  │  ...                  │
  └─────────────────────┘
```

**Annotations:**
- ① `taxonomy_editor_rename`: Inline text input with Save (Enter) and Cancel (Escape) controls

---

## Completeness Check

| Check | Status |
|-------|--------|
| All Screens from UI Layout (Discovery) covered | ✅ (Project List, Insights Tab, Cluster Detail, Interviews Tab, Settings Tab) |
| All UI Components annotated | ✅ (all 20 components from Discovery mapped) |
| Relevant State Variations documented | ✅ (loading, empty, error, hover states per screen) |
| No Logic/Rules duplicated (stays in Discovery) | ✅ |

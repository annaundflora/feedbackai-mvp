<!-- AGENT_DEF_LOADED: ux-expert-review-de-v1 -->

# UX Expert Review: LLM Interview Clustering

**Feature:** LLM Interview Clustering (Insights Pipeline)
**Reviewed:** Discovery + Wireframes (2026-02-28)
**Reviewer:** Senior UX Expert (Agent)

---

## Summary

**Verdict:** CHANGES_REQUESTED

The design concept is strategically sound -- it closes the feedback-to-decision loop with a well-researched clustering pipeline. The information architecture (Project List > Insights/Interviews/Settings tabs > Cluster Drill-Down) follows established patterns. The decision to use incremental clustering with user-controlled merge/split is the right call for this domain.

However, there are several usability gaps that will cause real user friction: missing error recovery paths in wireframes, an unresolvable state for `clustering_failed`, a destructive settings change with no safeguard, and an unclear interaction model for moving facts between clusters.

| ID | Title | Severity |
|----|-------|----------|
| F-1 | `clustering_failed` state has no recovery path in wireframes | Critical |
| F-2 | Changing `extraction_source` silently invalidates existing facts | Critical |
| F-3 | "Move fact to another cluster" has no defined interaction | Improvement |
| F-4 | Delete project confirmation lacks type-to-confirm in wireframe | Improvement |
| F-5 | No undo/rollback for merge operations | Improvement |
| F-6 | Split result is invisible before commit | Improvement |
| F-7 | Unassigned facts section has no bulk actions | Suggestion |
| F-8 | Model slug inputs have no validation feedback | Suggestion |

**Totals:** 2 Critical, 4 Improvement, 2 Suggestion

---

## Workflow Analysis

### State Machine Walk-Through

I traced every state transition defined in Discovery (lines 263-296). The primary happy path is clean:

```
no_projects -> project_empty -> project_collecting -> project_ready -> cluster_detail
```

Back-navigation is well defined: Cluster Detail has "Back to Clusters", Project Dashboard has "< Projects". Tab switching is implicit and standard.

### Identified Dead Ends

**1. `clustering_failed` -- No UI recovery in wireframes**

Discovery defines the state and a "Retry" action (line 276, 296), but no wireframe shows where this retry control lives or what it looks like. The Interviews Tab wireframe shows `failed` status badges but no actionable retry mechanism. The user sees a red X and is stuck.

**2. `extraction_failed` -- Partially covered**

Discovery mentions "Retry, Interview ueberspringen" (line 274), but the wireframe only shows a status badge. There is no "Skip" button or "Retry" button visible in the Interview Table wireframe.

### Concurrent State Concern

Discovery states that `project_updating` locks taxonomy editing to read-only (line 271: "Read-Only fuer Taxonomy"). The wireframe shows "context menus disabled" in the `project_updating` state variation (wireframes line 239). This is well-handled. However, there is no indication of *why* menus are disabled -- the user sees a grayed-out menu with no explanation.

---

## Findings

### Finding F-1: `clustering_failed` state has no recovery path in wireframes

**Severity:** Critical
**Category:** Workflow / Lücke

**Problem:**
When clustering fails after 3 retries, the user sees facts marked as "unassigned" and some kind of error hint -- but there is no actionable UI element to retry, skip, or manually assign these facts. The user is stuck in a dead-end state with no way to recover without understanding the system internals.

**Context:**
> **From Discovery (line 274-276):**
> ```
> | `extraction_failed` | Fact Extraction fehlgeschlagen | Retry, Interview ueberspringen |
> | `clustering_failed` | Clustering fehlgeschlagen | Retry |
> ```
>
> **From Wireframe:**
> The Interviews Tab (wireframe lines 499-517) shows status badges (checkmark, hourglass, X) but no retry controls. The Insights Tab wireframe shows no error state at all -- only the progress bar, suggestion banners, and cluster cards.

**Impact:**
Users who encounter a clustering failure (e.g., LLM timeout, rate limiting) cannot recover. They must wait for developer intervention or guess that "Recalculate All" might fix it. For a system processing 100+ interviews, occasional failures are expected, not exceptional.

**Recommendation:**
1. Add a "Retry" action to the failed interview row in the Interviews Tab (e.g., a retry icon button in the status column).
2. For `clustering_failed`: Show a banner in the Insights Tab similar to merge/split suggestions: "3 facts could not be assigned. [Retry] [Assign manually]"
3. Define what "Interview ueberspringen" (skip interview) means in the UI -- is it a button? Does it remove the interview from the project?

**Affects:**
- [x] Wireframe change needed
- [x] Discovery change needed (clarify "skip" action)

---

### Finding F-2: Changing `extraction_source` silently invalidates existing facts

**Severity:** Critical
**Category:** Usability / Error Prevention

**Problem:**
The Settings Tab allows changing the `extraction_source` from "Summary" to "Transcript" (or vice versa) at any time via a simple dropdown + Save. If a project already has extracted facts from summaries, switching to transcripts renders all existing facts conceptually inconsistent -- they were extracted from a different source than future facts will be. There is no warning, confirmation, or explanation of the consequences.

**Context:**
> **From Discovery (line 113):**
> ```
> User gibt ein: Projektname, Research-Ziel (Freitext), Prompt-Kontext fuer Interviewer (Freitext), Fact-Extraction-Quelle (Summary oder Transcript)
> ```
>
> **From Discovery (line 303):**
> ```
> Fact-Extraction-Quelle (Summary oder Transcript) ist pro Projekt konfigurierbar
> ```
>
> **From Wireframe (Settings Tab, lines 606-609):**
> ```
> Fact Extraction Source
> [Summary  v]
> ```
> No warning, no impact summary, standard form field.

**Impact:**
A user who changes this setting mid-project will have a mixed-source fact pool without knowing it. Clustering quality degrades silently because summary-derived facts and transcript-derived facts have different granularity and style. This violates error prevention -- the system should protect the user from an action whose consequences are non-obvious and potentially destructive.

**Recommendation:**
1. If facts already exist: Show a confirmation dialog explaining the impact: "47 facts were extracted from summaries. Changing to transcript extraction will only affect future interviews. Existing facts remain unchanged. To re-extract all facts, use 'Recalculate All'."
2. Alternatively, disable the dropdown once facts exist and offer a "Reset & Change Source" flow that explicitly includes re-extraction.

**Affects:**
- [x] Wireframe change needed (add confirmation dialog or disable logic)
- [x] Discovery change needed (add business rule for source-change behavior)

---

### Finding F-3: "Move fact to another cluster" has no defined interaction

**Severity:** Improvement
**Category:** Lücke / Inkonsistenz

**Problem:**
Discovery explicitly states full cluster control including the ability to move facts between clusters (line 342: "User kann Interviews zwischen Clustern verschieben (Drag & Drop oder Kontextmenue)"). However, no wireframe shows this interaction. The Cluster Detail screen shows facts as a read-only list. There is no drag handle, no context menu on facts, and no "Move to..." action anywhere.

**Context:**
> **From Discovery (line 342):**
> ```
> User kann Interviews zwischen Clustern verschieben (Drag & Drop oder Kontextmenue)
> ```
> Note: The text says "Interviews" but contextually means "Facts" (since facts are the atomic unit assigned to clusters, not interviews).
>
> **From Wireframe (Cluster Detail, lines 409-432):**
> Facts are displayed as numbered list items with text, interview badge, and confidence score. No interactive controls on individual facts.

**Impact:**
Users who want to correct a misclassified fact have no way to do so. They would need to split/merge entire clusters as a workaround, which is a sledgehammer for a precision task. This creates frustration for power users who understand their data better than the LLM.

**Recommendation:**
1. Add a context menu (or three-dot icon) to each `fact_item` with options: "Move to [cluster]..." and "Mark as unassigned".
2. Alternatively, add a drag-and-drop interaction in a dedicated "Organize" view.
3. Also clarify the Discovery text -- it says "Interviews" but means "Facts".

**Affects:**
- [x] Wireframe change needed (add fact-level actions)
- [x] Discovery change needed (clarify "Interviews" vs "Facts" in line 342)

---

### Finding F-4: Delete project confirmation lacks type-to-confirm in wireframe

**Severity:** Improvement
**Category:** Usability / Error Prevention

**Problem:**
Discovery specifies that project deletion requires the user to type the project name to confirm (line 230: "User muss Projektnamen eintippen"). The wireframe's Settings Tab shows a `delete_confirm` state variation (line 667: "Type project name to confirm") but no wireframe visualizes this dialog. Given that deletion destroys all clusters, facts, and interview assignments irreversibly, the confirmation pattern must be clearly specified and visualized.

**Context:**
> **From Discovery (line 230):**
> ```
> Danger Zone: "Projekt loeschen" Button mit Bestaetigung (User muss Projektnamen eintippen)
> ```
>
> **From Wireframe (Settings Tab state variations, line 667):**
> ```
> | `delete_confirm` | Overlay confirmation dialog: "Type project name to confirm" |
> ```
> But no wireframe screen shows this dialog.

**Impact:**
Without a wireframe, the implementation of this critical safety dialog is left to developer interpretation. The type-to-confirm pattern has specific UX requirements (matching logic, submit button disabled until match, clear instructions) that should not be ambiguous.

**Recommendation:**
Add a wireframe for the delete confirmation modal, similar to the existing Recalculate Confirmation wireframe. Include: warning text, input field with placeholder showing the project name, disabled submit button until input matches, and a clear Cancel option.

**Affects:**
- [x] Wireframe change needed

---

### Finding F-5: No undo/rollback for merge operations

**Severity:** Improvement
**Category:** Usability / User Control

**Problem:**
Merging two clusters is a one-way operation with significant consequences: all facts from the source cluster are permanently moved, the source cluster is deleted, and re-clustering runs automatically. Discovery defines merge behavior (line 309) but provides no undo mechanism. The merge dialog warns about the action but once confirmed, the only "undo" would be a full re-cluster -- which also destroys all other manual curation.

**Context:**
> **From Discovery (line 309):**
> ```
> Bei Merge: Alle Facts des Quell-Clusters wandern zum Ziel-Cluster, Quell-Cluster wird geloescht
> ```
>
> **From Wireframe (Merge Dialog, lines 288-290):**
> ```
> All facts from "Login Issues" will be moved to "Auth Problems".
> This triggers re-clustering.
> ```

**Impact:**
A user who accidentally merges the wrong clusters has no recovery path other than "Recalculate All", which destroys all their curation work. For a tool where manual taxonomy refinement is a core workflow, this is a meaningful friction point. Users will be hesitant to experiment with merges.

**Recommendation:**
1. Add an "Undo" toast notification after merge completion (e.g., "Clusters merged. [Undo - 30s]") that can restore the previous state within a time window.
2. If undo is too complex for MVP: at minimum, make the merge dialog more explicit about irreversibility ("This cannot be undone") and require selecting the target cluster before enabling the button.

**Affects:**
- [x] Wireframe change needed (add undo toast or stronger warning)
- [ ] Discovery change needed

---

### Finding F-6: Split result is invisible before commit

**Severity:** Improvement
**Category:** Usability / Visibility

**Problem:**
The split operation asks the user to confirm a blind action: "The LLM will analyze the facts and create sub-clusters automatically." The user clicks "Split Cluster" without knowing how many sub-clusters will be created, what they will be named, or how facts will be distributed. This is a high-stakes decision made with zero preview.

**Context:**
> **From Wireframe (Split Confirmation, lines 321-328):**
> ```
> Split "Navigation Issues" (14 Facts)?
>
> The LLM will analyze the facts and
> create sub-clusters automatically.
> This may take a moment.
> ```

**Impact:**
Users cannot make an informed decision about whether to split. A cluster with 14 facts might split into 2 sensible sub-clusters or 7 trivial ones. Without a preview, users either avoid splitting (feature underuse) or split and are surprised by the result (requiring manual cleanup).

**Recommendation:**
Consider a two-step split flow:
1. Step 1: User clicks "Split" -> LLM generates a preview of proposed sub-clusters (names + fact counts).
2. Step 2: User reviews the preview and confirms or cancels.

This matches the pattern already established for merge/split *suggestions* in the Insights Tab, where the LLM proposes and the user decides. Apply the same principle to manual splits.

**Affects:**
- [x] Wireframe change needed (add preview step)
- [x] Discovery change needed (add split preview to Flow 5)

---

### Finding F-7: Unassigned facts section has no bulk actions

**Severity:** Suggestion
**Category:** Usability / Flexibility

**Problem:**
The Insights Tab wireframe shows unassigned facts as a flat list at the bottom of the page. Each item shows the fact text and interview reference, but there is no way to act on them -- no checkboxes, no "assign to cluster" action, no drag-and-drop targets. For a small number of unassigned facts this is acceptable, but the concept allows for significant numbers of unassigned facts (e.g., after a full re-cluster or when clustering fails).

**Context:**
> **From Wireframe (Insights Tab, lines 212-215):**
> ```
> --- Unassigned (3 Facts) ---
> * "The app crashed during payment" (Interview #4)
> * "Would like dark mode" (Interview #9)
> * "Export feature is confusing" (Interview #11)
> ```
> No interactive controls on unassigned facts.

**Impact:**
Power users managing large projects cannot efficiently organize unassigned facts. They must rely on the LLM to eventually assign them (through re-clustering) rather than having the option to manually curate.

**Recommendation:**
Add checkboxes to unassigned facts with a "Move to cluster..." dropdown action. This complements Finding F-3 (fact-level actions) and creates a consistent interaction model for manual fact assignment.

**Affects:**
- [x] Wireframe change needed
- [ ] Discovery change needed

---

### Finding F-8: Model slug inputs have no validation feedback

**Severity:** Suggestion
**Category:** Usability / Error Prevention

**Problem:**
The Settings Tab shows four free-text inputs for OpenRouter model slugs (e.g., `anthropic/claude-sonnet-4`). These are raw strings with no validation feedback. A user who types a non-existent model slug (typo, deprecated model, wrong format) will only discover the error when the next pipeline run fails -- potentially hours later.

**Context:**
> **From Wireframe (Settings Tab, lines 618-636):**
> Model configuration shows plain text inputs with example values.
>
> **From Discovery (lines 326-335):**
> ```
> User konfiguriert Model-Slug pro Aufgabe im Projekt-Einstellungen Tab
> ```
> No validation rules defined for model slugs.

**Impact:**
Users who misconfigure model slugs will experience silent failures in the background pipeline. The connection between "I changed a setting in Settings" and "my clustering broke" is not obvious, especially since clustering runs asynchronously.

**Recommendation:**
1. Add inline validation that checks the model slug format (e.g., `provider/model-name` pattern).
2. Optionally, fetch available models from OpenRouter on focus and offer an autocomplete dropdown.
3. At minimum: show an inline hint with the expected format (e.g., "Format: provider/model-name").

**Affects:**
- [x] Wireframe change needed (add format hint or validation state)
- [ ] Discovery change needed

---

## Scalability & Risks

### Data Volume at Scale

The concept targets 100+ interviews per project. At ~5 facts per interview, that is 500+ facts in a single cluster grid view. The wireframe shows a 2-column card grid sorted by fact count. This will work well up to ~20 clusters. Beyond that, the grid becomes a long scrolling page with no search, filter, or sort controls.

**Risk:** Projects with many fine-grained clusters (e.g., 30+) become hard to navigate. Consider adding a search/filter bar above the cluster grid in a future iteration.

### Suggestion Fatigue

The merge/split suggestion banners appear in the Insights Tab after each incremental clustering run. With frequent interview activity, users may receive multiple suggestions per day. The wireframe shows suggestions as prominent banners that push cluster cards down.

**Risk:** Users develop "banner blindness" and start dismissing suggestions without reading them. Consider collapsing suggestions into a notification badge/counter that expands on click, rather than inline banners.

### SSE Connection Stability

The dashboard relies on SSE for live updates. SSE connections are unidirectional and can drop silently on mobile networks, proxy timeouts, or sleep/wake cycles. Discovery does not define reconnection behavior or stale-state detection.

**Risk:** Users see stale data without knowing it. The existing SSE pattern in the widget codebase (`widget/src/lib/sse-parser.ts`) handles widget-specific reconnection, but the dashboard is a separate Next.js SPA and will need its own reconnection logic with visual staleness indicators.

---

## Strategic Assessment

### Right Solution for the Problem

Yes. The core concept -- LLM-based clustering with user-controlled taxonomy -- is the right approach for qualitative research analysis at scale. The research backing (TNT-LLM, Clio, GoalEx) is thorough and well-applied. The decision to use incremental clustering with merge/split suggestions strikes the right balance between automation and user control.

### Information Architecture

The three-tab structure (Insights / Interviews / Settings) is clean and maps well to the user's mental model:
- **Insights** = "What did I learn?" (primary task)
- **Interviews** = "What data do I have?" (management)
- **Settings** = "How does it work?" (configuration)

The drill-down from Cluster Card to Cluster Detail follows established patterns. The back-navigation is well-defined.

### Innovation vs. Convention Balance

The concept leans appropriately on convention (card grids, tab navigation, context menus, modals) for the UI layer while innovating on the pipeline layer (LLM-driven clustering, self-correction loops). This is the right balance -- the UI should be predictable so users can focus on the novel value proposition (automated insight extraction).

---

## Positive Highlights

1. **Merge/Split Suggestions as first-class UI elements** -- The pattern of LLM-proposing and user-deciding is excellent. It keeps the human in the loop without making them do the analytical work.

2. **Recalculate confirmation with impact summary** -- The wireframe shows affected cluster and fact counts before a destructive re-cluster. This is genuinely helpful for informed decision-making.

3. **Progress indicator with fact-level granularity** -- "Analyzing... 47/52 Facts" gives precise feedback during long-running operations. Much better than a generic spinner.

4. **Clean separation of concerns** -- The dashboard is a separate SPA from the interview widget, which is the right architectural decision for different user personas (researcher vs. interviewee).

5. **Inline rename** -- Allowing cluster rename directly in the card/detail view without a modal is efficient for a frequent micro-task.

---

## Verdict

**CHANGES_REQUESTED**

The concept is strategically well-designed and demonstrates strong product thinking. However, 2 Critical findings must be addressed before implementation:

1. **F-1:** The `clustering_failed` and `extraction_failed` states need visible recovery controls in the wireframes. Without them, users hit dead ends on a system that is expected to occasionally fail.

2. **F-2:** Changing the extraction source mid-project is a silently destructive action that needs a safeguard (confirmation dialog or locked-after-first-use pattern).

Additionally, the 4 Improvement findings address meaningful usability gaps that should be resolved before implementation begins, particularly F-3 (fact-level movement) which is a feature explicitly promised in Discovery but absent from wireframes.

### Recommended Next Steps

1. Add error recovery wireframes for failed states (F-1)
2. Add extraction source change safeguard to Discovery + Wireframe (F-2)
3. Design fact-level actions (move, reassign) in Cluster Detail wireframe (F-3)
4. Add delete project confirmation wireframe (F-4)
5. Decide on merge undo strategy (F-5)
6. Consider split preview flow (F-6)

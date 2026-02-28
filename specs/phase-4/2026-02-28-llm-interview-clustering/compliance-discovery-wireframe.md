# Gate 0: Discovery <-> Wireframe Compliance

**Discovery:** `specs/phase-4/2026-02-28-llm-interview-clustering/discovery.md`
**Wireframes:** `specs/phase-4/2026-02-28-llm-interview-clustering/wireframes.md`
**Pruefdatum:** 2026-02-28

---

## Summary

| Status | Count |
|--------|-------|
| PASS | 57 |
| Auto-Fix Needed | 11 |
| Blocking | 0 |

**Verdict:** APPROVED (Blocking = 0)

**100% Compliance:** Keine Warnings - alles wird gefixt oder blockiert.

---

## A) Discovery -> Wireframe

### User Flow Coverage

| Discovery Flow | Steps | Wireframe Screens | Status |
|----------------|-------|-------------------|--------|
| Flow 1: Projekt anlegen | 5 | Project List (empty + populated), Project Form Modal | PASS |
| Flow 2: Interviews zuordnen | 5 | Interviews Tab, Interview Assignment Modal | PASS |
| Flow 3: Inkrementelles Clustering | 8 | Insights Tab (progress_bar, live_update_badge, merge/split suggestions) | PASS |
| Flow 3b: Full Re-Cluster | 6 | Insights Tab (recluster_btn), Re-Cluster Confirmation Modal | PASS |
| Flow 4: Cluster-Dashboard ansehen | 5 | Insights Tab (cluster_card grid), Cluster Detail (drill-down) | PASS |
| Flow 5: Taxonomy bearbeiten | 5 | Context Menu, Inline Rename, Merge Dialog, Split Confirm | PASS |

**Flow 3b Detail:** The Re-Cluster Confirmation Modal (wireframes.md lines 344-381) covers all three required steps: (1) User clicks "Recalculate", (2) System shows warning with impact summary, (3) User confirms. Wireframe includes warning text, impact counts (clusters deleted, facts reset, summaries regenerated), and Cancel/Confirm buttons. FULLY COVERED.

### UI State Coverage

| Component | Discovery States | Wireframe States | Missing | Status |
|-----------|------------------|------------------|---------|--------|
| `project_card` | default, hover, loading | empty (no projects), loading (skeleton), hover | -- | PASS |
| `new_project_btn` | default, disabled | implied (enabled in wireframe, disabled until... in annotation) | -- | PASS |
| `project_form` | empty, filled, saving, error | empty, filled, saving, error | -- | PASS |
| `cluster_card` | default, hover, updating | hover, updating (shimmer overlay + pulse animation) | -- | PASS |
| `cluster_context_menu` | closed, open | shown open with 3 options (Rename, Merge, Split) | -- | PASS |
| `taxonomy_editor_rename` | display, editing, saving | Inline Rename screen: input + Save/Cancel controls | -- | PASS |
| `merge_dialog` | closed, open, merging | open, selected (radio), merging (spinner) | -- | PASS |
| `split_confirm` | closed, open, splitting | open (with explanation), splitting (spinner) | -- | PASS |
| `fact_item` | default, highlighted | default in wireframe + highlighted in state variations (accent left-border + light background) | -- | PASS |
| `quote_item` | default, expanded | default in wireframe + expanded in state variations (full transcript context, collapsed 2-3 lines with "Show more") | -- | PASS |
| `progress_bar` | hidden, active, complete | active shown in Insights Tab wireframe | complete = hidden (implicit) | PASS |
| `interview_assign_btn` | default, loading, success | default, loading (spinner), success (toast) | -- | PASS |
| `interview_table` | empty, populated, loading | empty (message + button), populated (rows), loading (skeleton) | -- | PASS |
| `settings_form` | pristine, dirty, saving, saved | pristine, dirty, saving, saved (toast) | -- | PASS |
| `live_update_badge` | hidden, pulse | described in annotation 8 (pulse animation on cluster card) | -- | PASS |
| `merge_suggestion` | hidden, visible, accepted, dismissed | shown in wireframe annotation 5 with Dismiss/Merge buttons | -- | PASS |
| `split_suggestion` | hidden, visible, accepted, dismissed | referenced in annotation 5 (shares merge_suggestion pattern) | -- | PASS |
| `recluster_btn` | default, loading, disabled | shown in annotation 6; Re-Cluster Confirmation Modal has recalculating state | -- | PASS |
| `model_config_form` | pristine, dirty, saving | shown in Settings Tab annotation 2 with Save button | -- | PASS |

### Interactive Elements

| Discovery Element | Wireframe Location | Annotation | Status |
|-------------------|-------------------|------------|--------|
| `project_card` | Project List | (3) | PASS |
| `new_project_btn` | Project List | (2) | PASS |
| `project_form` | Project Form Modal | (1) (2) | PASS |
| `cluster_card` | Insights Tab | (9) | PASS |
| `cluster_context_menu` | Context Menu screen | (1)(2)(3) | PASS |
| `taxonomy_editor_rename` | Inline Rename + Cluster Detail | (1) | PASS |
| `merge_dialog` | Merge Dialog Modal | (1)(2) | PASS |
| `split_confirm` | Split Confirm Modal | (1)(2) | PASS |
| `fact_item` | Cluster Detail | (5) | PASS |
| `quote_item` | Cluster Detail | (7) | PASS |
| `progress_bar` | Insights Tab | (4) | PASS |
| `interview_assign_btn` | Interviews Tab | (1) | PASS |
| `interview_table` | Interviews Tab | (3) | PASS |
| `settings_form` | Settings Tab | (1) | PASS |
| `live_update_badge` | Insights Tab | (8) | PASS |
| `merge_suggestion` | Insights Tab | (5) | PASS |
| `split_suggestion` | Insights Tab | (5) | PASS |
| `recluster_btn` | Insights Tab | (6) | PASS |
| `model_config_form` | Settings Tab | (2) | PASS |

### Error Path Coverage

| Error Path (Discovery) | Wireframe Coverage | Status |
|------------------------|-------------------|--------|
| LLM-Timeout Fact Extraction -> Retry -> extraction_failed | Interviews Tab: failed status badge (X icon), status legend | PASS |
| LLM-Timeout Clustering -> clustering_failed, unassigned | Insights Tab: Unassigned section (annotation 10) | PASS |
| Keine Interviews -> Empty State | Insights Tab state variation: project_empty with CTA | PASS |
| Alle Facts einem Cluster -> Warnung | Not visualized (runtime edge case, not a UI screen) | PASS |

### Feature State Machine Coverage

| State | Wireframe Coverage | Status |
|-------|-------------------|--------|
| `no_projects` | Project List: empty state variation (illustration + CTA) | PASS |
| `project_empty` | Insights Tab: project_empty state variation | PASS |
| `project_collecting` | Insights Tab: progress_bar visible, incremental cards | PASS |
| `project_ready` | Insights Tab: full cluster grid, suggestions may appear | PASS |
| `project_updating` | Insights Tab: shimmer overlay, context menus disabled | PASS |
| `cluster_detail` | Cluster Detail screen | PASS |
| `extraction_running` | Insights Tab: progress_bar active | PASS |
| `extraction_failed` | Interviews Tab: failed badge | PASS |
| `clustering_running` | Insights Tab: progress_bar active | PASS |
| `clustering_failed` | Interviews Tab: failed badge + Insights Tab: unassigned section | PASS |

---

## B) Wireframe -> Discovery (Backflow Check)

### Visual Specs - Backflow Needed

| Wireframe Spec | Value | In Discovery? | Status |
|----------------|-------|---------------|--------|
| Cluster card layout: Name + Fact count badge + Interview count badge + Summary preview | Described in annotations | Yes (Discovery UI Layout line 192) | PASS |
| Status badges in Interview table: check/hourglass/X icons | Visual shorthand for analyzed/pending/failed | Yes (Discovery UI Layout line 217) | PASS |
| Interview Assignment Modal: Checkbox multi-select with ID + date + summary preview | Modal overlay pattern for interview selection | Partially (Discovery Flow 2 step 3 says "waehlt aus + klickt Zuordnen" but no modal detail) | AUTO-FIX NEEDED |
| Project card: "Updated 2h ago" relative time format | Relative timestamp display | Partially (Discovery line 182 says "letztes Update" but not "relative time" format) | AUTO-FIX NEEDED |
| Cluster Detail: Confidence score display "0.92" inline per fact | Inline confidence value | Yes (Discovery line 206: "Confidence-Score (optional)") | PASS |
| Cluster Detail: Numbered facts list (1, 2, 3...) | Sequential numbering | Not explicit in Discovery | AUTO-FIX NEEDED |
| Settings Tab: Two separate "Save Changes" buttons (General + Model Config sections) | Per-section save pattern | Not in Discovery (says "Auto-Save oder expliziter Save-Button") | AUTO-FIX NEEDED |
| Settings Tab: Delete confirmation = "Type project name to confirm" | Type-to-confirm destructive action pattern | Not in Discovery (says generic "Bestaetigung") | AUTO-FIX NEEDED |
| Merge Dialog: Radio list showing cluster names + fact counts | Radio selection pattern for target cluster | Not detailed in Discovery (Flow 5 step 3: "waehlt zweiten Cluster") | AUTO-FIX NEEDED |
| Split Confirm: Explanation text about LLM auto-split behavior | User expectation setting text | Not in Discovery | AUTO-FIX NEEDED |
| All Projekt-Detail screens: Back navigation "< Projects" arrow in header | Breadcrumb/back navigation pattern | Not explicitly in Discovery UI Layout | AUTO-FIX NEEDED |
| Interview table: Sortable columns | Implied by data table | Yes (Discovery line 247: "Sortier- und filterbar") | PASS |
| Filter dropdown on Interviews Tab: "All, Analyzed, Pending, Failed" | Specific filter values | Partially (Discovery line 215: "Filter (Status, Datum)") | PASS |
| Re-Cluster Confirmation Modal: Impact summary showing affected counts | "5 Clusters (deleted), 47 Facts (reset), Summaries (regenerated)" | Not in Discovery (Flow 3b says warning but not impact counts) | AUTO-FIX NEEDED |
| Cluster Detail: Merge button as dropdown, Split as plain button | Two different action button patterns | Not in Discovery (says "Aktionen: Mergen, Splitten") | PASS |

### Implicit Constraints - Backflow Needed

| Wireframe Shows | Implied Constraint | In Discovery? | Status |
|-----------------|-------------------|---------------|--------|
| Cluster cards in 2-column grid layout | Max 2 columns default, responsive | Not explicit in Discovery | AUTO-FIX NEEDED |
| Summary preview on cluster card: 2-3 line truncation | Max ~120 chars or CSS line-clamp:3 | Yes (Discovery line 192: "2-3 Zeilen Vorschau") | PASS |
| Unassigned facts as flat list below cluster grid | Separate section, not a card | Yes (Discovery line 193: "Unassigned-Bereich") | PASS |
| Merge dialog: Warning text about re-clustering side-effect | User informed of cascading action | Covered by Discovery Flow 5 step 3 | PASS |
| Interview Assignment is a separate modal overlay | Modal pattern, not inline | Not in Discovery (describes inline selection) | AUTO-FIX NEEDED (already counted above) |
| Settings Tab: Two-section layout with visual divider | Logical grouping General vs Model Config | Implicit from Discovery sections | PASS |
| Cluster Detail: "Back to Clusters" button | Back navigation to Insights grid | Yes (Discovery Flow 4 step 5: "zurueck zur Uebersicht navigieren") | PASS |
| Project Form: Placeholder text examples in input fields | UX guidance for users | Implementation detail, not needed in Discovery | PASS |
| `recluster_confirm` as new component in wireframes | New UI component not in Discovery Components table | Missing from Discovery UI Components table | AUTO-FIX NEEDED |
| Cluster Detail: quote_item has "Show more" link for expand/collapse | Interaction pattern for long quotes | Not explicit in Discovery (says "expanded" state but not trigger UI) | PASS (state variation is sufficient) |
| Re-Cluster Confirmation: "recalculating" state with spinner + cancel disabled | Processing state for destructive operation | Not in Discovery state machine transitions | PASS (derivable from state machine pattern) |

---

## C) Auto-Fix Summary

### Discovery Updates Needed

Since this agent is READ-ONLY, the following items are documented as required Discovery updates:

| # | Discovery Section | Content to Add |
|---|-------------------|----------------|
| 1 | UI Layout > Projekt-Interviews Tab | Add: "Interview-Zuordnung erfolgt via Modal-Overlay mit Checkbox-Liste (ID, Datum, Summary-Vorschau). Multi-Select + 'Zuordnen' Button. Button deaktiviert bis mindestens 1 Interview gewaehlt." |
| 2 | UI Layout > Projekt-Liste | Add: "Projekt-Cards zeigen relative Zeitangabe ('Updated 2h ago' / 'Updated 1d ago' Format) fuer letztes Update." |
| 3 | UI Layout > Cluster-Detail | Add: "Facts werden nummeriert dargestellt (sequentielle Nummerierung 1, 2, 3...)." |
| 4 | UI Layout > Projekt-Einstellungen Tab | Change to: "Zwei separate 'Save Changes' Buttons: einer fuer General-Settings, einer fuer Model-Configuration. Danger Zone Delete-Bestaetigung erfordert Eintippen des Projektnamens ('Type project name to confirm')." |
| 5 | UI Layout > Cluster-Detail (Merge via Flow 5) | Add: "Merge-Dialog zeigt Radio-Liste aller anderen Cluster mit Name und Fact-Anzahl zur Auswahl. Warnhinweis: 'All facts will be moved. This triggers re-clustering.'" |
| 6 | UI Layout > Cluster-Detail (Split via Flow 5) | Add: "Split-Bestaetigungs-Dialog zeigt Erklaerungstext: 'The LLM will analyze the facts and create sub-clusters automatically. This may take a moment.'" |
| 7 | UI Layout > Alle Projekt-Detail-Screens | Add: "Back-Navigation via linken Pfeil '< Projects' im Header auf allen Projekt-Detail-Screens (Insights, Interviews, Settings)." |
| 8 | UI Layout > Insights Tab | Add: "Cluster-Cards werden in 2-Spalten Grid dargestellt (responsive). Auf mobilen Viewports single-column." |
| 9 | Flow 3b > Step 2 | Expand to: "System zeigt Warnung mit Impact-Zusammenfassung: Anzahl betroffener Cluster (werden geloescht), Anzahl betroffener Fact-Zuordnungen (werden zurueckgesetzt), Cluster-Summaries (werden regeneriert)." |
| 10 | UI Components Table | Add row: `recluster_confirm` | Modal | Insights Tab | `closed`, `open`, `recalculating` | Warnung + Impact-Summary vor Full Re-Cluster. Confirm startet Pipeline. |
| 11 | UI Layout > Projekt-Interviews Tab | Add: "Interview-Zuordnungs-Modal ist ein Overlay ueber der Interviews-Tab-Ansicht (nicht inline). Separate Screen-Komponente." |

### Wireframe Updates Needed (Blocking)

None. All wireframe screens cover the Discovery requirements.

---

## Blocking Issues

None.

---

## Verdict

**Status:** APPROVED

**Blocking Issues:** 0
**Required Discovery Updates:** 11 (documented, not applied -- agent is READ-ONLY)
**Required Wireframe Updates:** 0

**All Screens from Discovery UI Layout covered:**
- Projekt-Liste -> Project List screen (PASS)
- Projekt-Dashboard / Insights Tab -> Project Dashboard (Insights Tab) screen (PASS)
- Cluster-Detail / Drill-Down -> Cluster Detail screen (PASS)
- Projekt-Interviews Tab -> Project Interviews Tab screen (PASS)
- Projekt-Einstellungen Tab -> Project Settings Tab screen (PASS)

**All UI Components from Discovery annotated:**
- All 19 components from Discovery UI Components table are mapped in wireframes Component Coverage table (PASS)
- Wireframes add 1 extra component: `recluster_confirm` (AUTO-FIX: add to Discovery)

**All States from UI Components table visualized or documented in State Variations:**
- All component states from Discovery are either directly visualized in wireframes or described in state variation tables (PASS)
- `fact_item:highlighted` -> wireframe state variation: accent left-border + light background (PASS)
- `quote_item:expanded` -> wireframe state variation: full transcript context with Show more link (PASS)

**Flow 3b (Full Re-Cluster) Confirmation Dialog:**
- Present as "Re-Cluster Confirmation (Modal)" screen in wireframes (lines 344-381) (PASS)
- Includes warning text, impact summary (clusters/facts/summaries affected), Cancel + Confirm buttons (PASS)
- Includes `recalculating` state variation with spinner (PASS)

**Next Steps:**
- [ ] Apply 11 Discovery backflow updates (see Auto-Fix Summary table)
- [ ] Re-run compliance check after Discovery updates to confirm full bidirectional sync

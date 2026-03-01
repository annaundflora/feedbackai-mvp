# E2E Checklist: /build Command - Unified Autonomous Feature Pipeline

**Integration Map:** `integration-map.md`
**Generated:** 2026-03-01

---

## Pre-Conditions

- [x] All slices APPROVED (Gate 2) -- 5/5 slices approved
- [x] Architecture APPROVED (Gate 1)
- [x] Integration Map has no MISSING INPUTS -- 0 missing inputs

---

## Happy Path Tests

### Flow 1: Single-Spec Full Build (Discovery User Flow Steps 1-8)

1. [ ] **Slice 01:** `slice-plan-coordinator` Agent existiert unter `.claude/agents/slice-plan-coordinator.md`
2. [ ] **Slice 01:** Agent hat YAML Frontmatter mit `name: slice-plan-coordinator`, `tools: Read, Write, Glob, Grep, Task`
3. [ ] **Slice 01:** Agent ruft Task(slice-writer) auf und erstellt `slices/slice-NN-slug.md`
4. [ ] **Slice 01:** Agent ruft Task(slice-compliance) auf und erstellt `slices/compliance-slice-NN.md`
5. [ ] **Slice 01:** Agent gibt JSON zurueck mit `{status: "approved", retries: N, slice_file: "...", blocking_issues: []}`
6. [ ] **Slice 02:** `slice-impl-coordinator` Agent existiert unter `.claude/agents/slice-impl-coordinator.md`
7. [ ] **Slice 02:** Agent hat YAML Frontmatter mit `name: slice-impl-coordinator`, `tools: Read, Write, Glob, Grep, Task`
8. [ ] **Slice 02:** Agent ruft Task(slice-implementer) -> Task(test-writer) -> Task(test-validator) sequenziell auf
9. [ ] **Slice 02:** Agent schreibt Evidence nach `.claude/evidence/{feature}/{slice_id}.json`
10. [ ] **Slice 02:** Agent gibt JSON zurueck mit `{status: "completed", retries: N, evidence: {...}, error: null}`
11. [ ] **Slice 03:** `/build` Command existiert unter `.claude/commands/build.md`
12. [ ] **Slice 03:** Command validiert Input: discovery.md + architecture.md muessen existieren
13. [ ] **Slice 03:** Command erstellt Git Branch `feat/{feature-name}`
14. [ ] **Slice 03:** Command fuehrt Planning Phase sequenziell aus (Task(slice-plan-coordinator) pro Slice)
15. [ ] **Slice 03:** Command fuehrt Gate 3 aus (Task(integration-map))
16. [ ] **Slice 03:** Command fuehrt Implementation Phase wave-basiert aus (Task(slice-impl-coordinator) pro Slice)
17. [ ] **Slice 03:** Command fuehrt Final Validation aus (Task(test-validator, mode=final_validation))
18. [ ] **Slice 03:** Command fuehrt Completion aus (git push + gh pr create)
19. [ ] **Slice 03:** `.build-state.json` hat status="completed" und completed_at ist gesetzt

### Flow 2: Multi-Spec Build (Discovery User Flow + Multi-Spec Extension)

20. [ ] **Slice 04:** `/build spec_a spec_b` parst zu `specs = ["spec_a", "spec_b"]`
21. [ ] **Slice 04:** Vorab-Validierung prueft alle Specs auf discovery.md + architecture.md
22. [ ] **Slice 04:** Feature A durchlaeuft vollstaendigen Single-Spec Flow (Steps 12-19)
23. [ ] **Slice 04:** Command wechselt zurueck auf main-Branch nach Feature A
24. [ ] **Slice 04:** Feature B startet auf neuem Branch `feat/{feature-b-name}`
25. [ ] **Slice 04:** Feature B durchlaeuft vollstaendigen Single-Spec Flow
26. [ ] **Slice 04:** Zusammenfassung zeigt "Erfolgreich: 2" mit PR-Links

### Flow 3: Pattern Documentation

27. [ ] **Slice 05:** `.claude/docs/workflow-patterns.md` existiert
28. [ ] **Slice 05:** Dokument enthaelt exakt 15 Pattern-Eintraege
29. [ ] **Slice 05:** Jedes Pattern hat: Name, Quelle, Kategorie, "Verwendet in", Problem, Loesung, Konsequenzen, Implementierungshinweise, Beispiel
30. [ ] **Slice 05:** Kategorien-Uebersicht mit 5 Kategorien vorhanden
31. [ ] **Slice 05:** Quick-Reference-Tabelle mit allen 15 Patterns vorhanden
32. [ ] **Slice 05:** Keine TODOs, Platzhalter oder "..." im Dokument

---

## Edge Cases

### Error Handling

- [ ] **Slice 03 AC-2:** Missing discovery.md -> "STOP: discovery.md fehlt" und keine .build-state.json erstellt
- [ ] **Slice 03 AC-2:** Missing architecture.md -> "STOP: architecture.md fehlt" und keine .build-state.json erstellt
- [ ] **Slice 01 AC-5:** Slice Planning failed nach 9 Retries -> JSON `{status: "failed", retries: 9, blocking_issues: [...]}`
- [ ] **Slice 02 AC-3:** Slice-Implementer returns status "failed" -> sofort `{status: "failed", error: "slice-implementer returned status: failed"}`
- [ ] **Slice 02 AC-4:** Test-Writer ac_coverage < 100% -> sofort `{status: "failed", error: "test-writer ac_coverage: N%, required: 100%"}`
- [ ] **Slice 02 AC-9:** Debugger returns "unable_to_fix" -> sofort `{status: "failed", error: "debugger: unable_to_fix"}`
- [ ] **Slice 02 AC-10:** Test Validation failed nach 9 Retries -> `{status: "failed", retries: 9, error: "max retries exceeded"}`
- [ ] **Slice 03 AC-12:** Sub-Agent JSON status="failed" -> HARD STOP mit state.status="failed"
- [ ] **Slice 03 AC-8:** Gate 3 VERDICT "GAPS FOUND" -> retry (max 9), then HARD STOP
- [ ] **Slice 03:** JSON Parse Failure von Sub-Agent -> HARD STOP
- [ ] **Slice 03:** Git Push/PR Failure -> HARD STOP mit Fehlermeldung
- [ ] **Slice 04 AC-10:** `/build` ohne Argumente -> "STOP: Mindestens ein Spec-Pfad erforderlich"
- [ ] **Slice 04 AC-4:** Ungueltige Spec in Multi-Spec -> "Ueberspringe {spec}: discovery.md fehlt" und weiter mit gueltigen Specs
- [ ] **Slice 04 AC-6:** Feature-Failure in Multi-Spec -> Feature als failed markiert, springt zum naechsten Feature (kein HARD STOP fuer gesamten Run)

### State Transitions

- [ ] `init` -> `planning_slice_1` (Input valid, fresh start)
- [ ] `init` -> `planning_slice_N` (Resume from in_progress planning state)
- [ ] `init` -> `implementing_slice_N` (Resume from in_progress implementing state)
- [ ] `planning_slice_N` -> `planning_slice_N+1` (Slice approved)
- [ ] `planning_slice_N` -> `gate_3` (Last slice approved)
- [ ] `planning_slice_N` -> `failed` (Max retries reached)
- [ ] `gate_3` -> `implementing_slice_1` (VERDICT: READY FOR ORCHESTRATION)
- [ ] `gate_3` -> `failed` (Max retries reached)
- [ ] `implementing_slice_N` -> `implementing_slice_N+1` (Slice completed)
- [ ] `implementing_slice_N` -> `final_validation` (Last slice completed)
- [ ] `implementing_slice_N` -> `failed` (Max retries reached)
- [ ] `final_validation` -> `completing` (All tests passed)
- [ ] `final_validation` -> `failed` (Max retries + debugger unable_to_fix)
- [ ] `completing` -> `completed` (PR created)

### Boundary Conditions

- [ ] Single Slice Feature: /build with spec that has only 1 slice -> Planning + Gate 3 + Implementation all work
- [ ] Resume after Planning Phase crash: .build-state.json exists with phase="planning" -> resumes at correct slice
- [ ] Resume after Implementation Phase crash: .build-state.json exists with phase="implementing" -> resumes at correct slice
- [ ] Resume after Failed State: .build-state.json with status="failed" -> shows error, resets to in_progress, resumes
- [ ] Already Completed: .build-state.json with status="completed" -> "Build bereits abgeschlossen" and STOP
- [ ] Multi-Spec with already completed Feature: Feature A completed -> skips A, processes B
- [ ] Single-Spec backwards compatibility: `/build spec_a` behaves identical to Slice 03 single-spec mode

---

## Cross-Slice Integration Points

| # | Integration Point | Slices | How to Verify |
|---|-------------------|--------|---------------|
| 1 | slice-plan-coordinator -> /build JSON Contract | 01 -> 03 | Verify JSON `{status, retries, slice_file, blocking_issues}` is parseable by /build "Find LAST json block" pattern |
| 2 | slice-impl-coordinator -> /build JSON Contract | 02 -> 03 | Verify JSON `{status, retries, evidence, error}` is parseable by /build "Find LAST json block" pattern |
| 3 | slice-plan-coordinator approved_slices_paths | 01 -> 03 | Verify /build passes approved_slices_paths list to slice-plan-coordinator for Integration Contract context |
| 4 | /build -> Multi-Spec Outer Loop | 03 -> 04 | Verify Multi-Spec extends build.md without breaking Single-Spec behavior |
| 5 | .build-state.json Schema Consistency | 03 -> 04 | Verify `specs[]` and `current_spec_index` fields work in both single and multi-spec modes |
| 6 | Git Branch Isolation | 03 -> 04 | Verify each feature gets own branch, checkout main between features |
| 7 | Evidence Path Convention | 02 -> 03 | Verify `.claude/evidence/{feature}/{slice_id}.json` path is consistent between Agent and Command |
| 8 | Pattern Documentation References | 05 -> (01,02,03) | Verify "Verwendet in" references in workflow-patterns.md point to existing files from Slices 01-03 |

---

## Sign-Off

| Tester | Date | Result |
|--------|------|--------|
| | | |

**Notes:**
All tests are manual as all deliverables are Markdown agent/command definitions, not executable code. Testing requires invoking the agents/commands through Claude Code Task() calls.

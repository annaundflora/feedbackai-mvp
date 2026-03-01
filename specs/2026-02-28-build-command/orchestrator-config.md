# Orchestrator Configuration: /build Command - Unified Autonomous Feature Pipeline

**Integration Map:** `integration-map.md`
**E2E Checklist:** `e2e-checklist.md`
**Generated:** 2026-03-01

---

## Pre-Implementation Gates

```yaml
pre_checks:
  - name: "Gate 1: Architecture Compliance"
    file: "compliance-architecture.md"
    required: "Verdict == APPROVED"

  - name: "Gate 2: All Slices Approved"
    files: "compliance-slice-*.md"
    required: "ALL Verdict == APPROVED"
    status: "5/5 APPROVED"

  - name: "Gate 3: Integration Map Valid"
    file: "integration-map.md"
    required: "Missing Inputs == 0"
    status: "0 Missing Inputs, 0 Gaps"
```

---

## Implementation Order

Based on dependency analysis:

| Order | Slice | Name | Depends On | Parallel? |
|-------|-------|------|------------|-----------|
| 1 | 01 | slice-plan-coordinator Agent | -- | Yes with 02, 05 |
| 1 | 02 | slice-impl-coordinator Agent | -- | Yes with 01, 05 |
| 1 | 05 | Pattern-Dokumentation | -- | Yes with 01, 02 |
| 2 | 03 | /build Command | 01, 02 | No (depends on Wave 1) |
| 3 | 04 | Multi-Spec Support | 03 | No (depends on Wave 2) |

### Wave Details

**Wave 1 (Foundation -- no dependencies, parallel):**
- Slice 01: `slice-plan-coordinator` Agent -> `.claude/agents/slice-plan-coordinator.md`
- Slice 02: `slice-impl-coordinator` Agent -> `.claude/agents/slice-impl-coordinator.md`
- Slice 05: Pattern-Dokumentation -> `.claude/docs/workflow-patterns.md`

**Wave 2 (Core Command -- depends on Slice 01 + 02):**
- Slice 03: `/build` Command -> `.claude/commands/build.md`

**Wave 3 (Extension -- depends on Slice 03):**
- Slice 04: Multi-Spec Support -> `.claude/commands/build.md` (extend)

---

## Post-Slice Validation

FOR each completed slice:

```yaml
validation_steps:
  - step: "Deliverables Check"
    action: "Verify all files in DELIVERABLES_START exist"
    details:
      slice-01: ".claude/agents/slice-plan-coordinator.md"
      slice-02: ".claude/agents/slice-impl-coordinator.md"
      slice-03: ".claude/commands/build.md"
      slice-04: ".claude/commands/build.md (extended with multi-spec)"
      slice-05: ".claude/docs/workflow-patterns.md"

  - step: "Unit Tests"
    action: "Run tests defined in slice"
    details: "All slices have manual tests only (Markdown agent/command definitions)"

  - step: "Integration Points"
    action: "Verify outputs accessible by dependent slices"
    reference: "integration-map.md -> Connections"
    checks:
      - "After Slice 01: Verify .claude/agents/slice-plan-coordinator.md exists and has YAML Frontmatter"
      - "After Slice 02: Verify .claude/agents/slice-impl-coordinator.md exists and has YAML Frontmatter"
      - "After Slice 03: Verify .claude/commands/build.md exists and contains all 8 Phases"
      - "After Slice 04: Verify .claude/commands/build.md contains Multi-Spec Outer Loop"
      - "After Slice 05: Verify .claude/docs/workflow-patterns.md has 15 patterns"
```

---

## E2E Validation

AFTER all slices completed:

```yaml
e2e_validation:
  - step: "Execute e2e-checklist.md"

  - step: "FOR each failing check"
    actions:
      - "Identify responsible slice from Integration Map"
      - "Create fix task with slice reference"
      - "Re-run affected slice tests"

  - step: "Final Approval"
    condition: "ALL checks in e2e-checklist.md PASS"
    output: "Feature READY for merge"
```

---

## Rollback Strategy

IF implementation fails:

```yaml
rollback:
  - condition: "Slice 01 or 02 fails (Foundation)"
    action: "Revert agent file only"
    note: "No downstream dependencies affected yet"

  - condition: "Slice 03 fails (Core Command)"
    action: "Revert .claude/commands/build.md"
    note: "Slices 01+02 are stable, can be kept"

  - condition: "Slice 04 fails (Multi-Spec Extension)"
    action: "Revert multi-spec additions to build.md"
    note: "Single-spec /build from Slice 03 remains functional"

  - condition: "Slice 05 fails (Documentation)"
    action: "Revert .claude/docs/workflow-patterns.md"
    note: "No other slices depend on this"

  - condition: "Integration fails"
    action: "Review integration-map.md for gaps"
    note: "May need slice spec updates"
```

---

## Monitoring

During implementation:

| Metric | Alert Threshold |
|--------|-----------------|
| Slice completion time | > 2x estimate |
| Test failures | > 0 blocking |
| Deliverable missing | Any |
| Integration test fail | Any |

---

## Implementation Notes

### Special Considerations

1. **All deliverables are Markdown files:** No compilation, no build steps. Validation is structural (file exists, has required sections).

2. **Slice 04 modifies Slice 03 output:** The `/build` command file `.claude/commands/build.md` is created in Slice 03 and extended in Slice 04. The implementer for Slice 04 MUST read the existing file first.

3. **Slice 05 can run in parallel with Wave 1:** Pattern documentation has no hard dependencies. "Verwendet in" references to files from Slices 01-03 can be written preemptively (those files will exist after their respective slices complete).

4. **No automated tests:** All slices produce Markdown agent/command definitions. Manual testing via Task() invocation is the validation method. The E2E checklist provides the manual test plan.

# Slice 1: Slice-Plan-Coordinator Agent erstellen

> **Slice 1 von 5** fuer `build-command`
>
> | Navigation | |
> |------------|---|
> | **Vorheriger:** | -- |
> | **Naechster:** | `slice-02-slice-impl-coordinator.md` |

---

## Metadata (fuer Orchestrator)

| Key | Value |
|-----|-------|
| **ID** | `slice-01-slice-plan-coordinator` |
| **Test** | `N/A (manueller Test - Agent-Datei)` |
| **E2E** | `false` |
| **Dependencies** | `[]` |

---

## Test-Strategy (fuer Orchestrator Pipeline)

> **Quelle:** Auto-detected basierend auf Repo-Indikatoren. Dashboard nutzt Next.js + Vitest + Playwright.
> Dieser Slice erstellt eine Agent-Markdown-Datei, keine ausfuehrbaren Code-Dateien.

| Key | Value |
|-----|-------|
| **Stack** | `claude-code-agent` (Markdown Agent Definition) |
| **Test Command** | `N/A` (Agent-Datei, kein ausfuehrbarer Code) |
| **Integration Command** | `N/A` |
| **Acceptance Command** | `Manuell: Agent mit einem Slice aufrufen, pruefen ob slices/ + compliance/ erstellt werden` |
| **Start Command** | `N/A` |
| **Health Endpoint** | `N/A` |
| **Mocking Strategy** | `no_mocks` |

---

## Slice-Uebersicht

| # | Slice | Status | Datei |
|---|-------|--------|-------|
| 1 | **slice-plan-coordinator Agent** | Ready | `slice-01-slice-plan-coordinator.md` |
| 2 | slice-impl-coordinator Agent | Pending | `slice-02-slice-impl-coordinator.md` |
| 3 | /build Command | Pending | `slice-03-build-command.md` |
| 4 | Multi-Spec Support | Pending | `slice-04-multi-spec-support.md` |
| 5 | Pattern-Dokumentation | Pending | `slice-05-pattern-dokumentation.md` |

---

## Kontext & Ziel

Der `/build` Command braucht einen Ebene-1-Coordinator-Agent der pro Slice das Planning und die Compliance-Validierung uebernimmt. Dieser Agent wird vom `/build` Command per `Task()` aufgerufen und bekommt einen frischen Context pro Slice (Fresh Context Pattern).

**Problem:** Der bisherige `/planner` Command fuehrt alle Task()-Calls selbst aus. Bei 7+ Slices mit Retries fuellt sich der Coordinator-Context (35.000-105.000 Tokens).

**Loesung:** Der `slice-plan-coordinator` Agent uebernimmt die Retry-Loop fuer EINEN Slice. Der `/build` Command ruft ihn nur noch mit `Task()` auf und empfaengt ein kompaktes JSON-Ergebnis (~300 Tokens).

---

## Technische Umsetzung

### Architektur-Kontext (aus architecture.md)

> **Quelle:** `architecture.md` -> "Architecture Layers", "Slice-Plan-Coordinator Internal Flow"

```
/build Command (Ebene 0, ~5.000 Tokens Context)
  |
  +-- Task(slice-plan-coordinator)    [Ebene 1, eigener Context]
  |     |
  |     +-- Task(slice-writer)        [Ebene 2, eigener Context]
  |     +-- Task(slice-compliance)    [Ebene 2, eigener Context]
  |     +-- IF FAILED: retry loop (max 9)
  |     +-- Return: {status: "approved", retries: N, slice_file: "..."}
```

### 1. Architektur-Impact

| Layer | Aenderungen |
|-------|------------|
| `.claude/agents/` | Neue Datei `slice-plan-coordinator.md` |

### 2. Datenfluss

```
Input: spec_path, slice_number, slice_name, slice_description, slice_dependencies, approved_slices_paths
  |
  v
Read: discovery.md, architecture.md, wireframes.md (if exists)
Read: previously approved slices (for Integration Contracts)
  |
  v
LOOP (max 9 Retries):
  |
  +-- Task(slice-writer) -> schreibt slices/slice-NN-slug.md
  |
  +-- Task(slice-compliance) -> schreibt slices/compliance-slice-NN.md
  |
  +-- Read VERDICT from compliance report
  |     |
  |     +-- APPROVED -> break loop
  |     +-- FAILED -> extract blocking_issues, retry with fix prompt
  |
  v
Return JSON:
  {
    "status": "approved" | "failed",
    "retries": N,
    "slice_file": "slices/slice-NN-slug.md",
    "blocking_issues": []
  }
```

### 3. JSON Output Contract

Der Agent MUSS am Ende seiner Ausfuehrung exakt dieses JSON zurueckgeben:

```json
{
  "status": "approved",
  "retries": 2,
  "slice_file": "slices/slice-01-db-schema.md",
  "blocking_issues": []
}
```

Oder bei Fehlschlag:

```json
{
  "status": "failed",
  "retries": 9,
  "slice_file": "slices/slice-01-db-schema.md",
  "blocking_issues": [
    "AC-3 fehlt GIVEN/WHEN/THEN Format",
    "Integration Contract: provides publishPin() aber Signatur fehlt"
  ]
}
```

### 4. Agent-Prompt-Struktur

Der Agent MUSS folgende Sections enthalten:

1. **YAML Frontmatter** - name, description, tools
2. **Rolle** - Beschreibung als Slice-Plan-Coordinator
3. **Input-Parsing** - Wie der Prompt vom `/build` Command geparst wird
4. **Phase 1: Dokumente laden** - Liest discovery, architecture, wireframes, approved slices
5. **Phase 2: Slice-Writer aufrufen** - Task(slice-writer) mit korrektem Prompt
6. **Phase 3: Compliance Check** - Task(slice-compliance) mit korrektem Prompt
7. **Phase 4: Verdict pruefen** - APPROVED vs FAILED
8. **Phase 5: Retry-Loop** - Fix-Prompt bei FAILED, max 9 Retries
9. **Phase 6: JSON Output** - Strukturiertes JSON zurueckgeben

### 5. Task()-Call Prompts (KRITISCH)

#### Slice-Writer Prompt (Erst-Erstellung):

```
Erstelle Slice {slice_number}: {slice_name}

## Input-Dateien (MUSS gelesen werden)
- {spec_path}/architecture.md
- {spec_path}/wireframes.md (falls vorhanden)
- {spec_path}/discovery.md (fuer Kontext)
- Vorherige genehmigte Slices: {approved_slices_paths}

## Slice-Anforderungen
{slice_description}
Dependencies: {slice_dependencies}

## Output
Schreibe: {spec_path}/slices/slice-{NN}-{slug}.md

## KRITISCH - Template-Pflicht
Lies .claude/templates/plan-spec.md und stelle sicher:
- Metadata Section mit ID, Test, E2E, Dependencies
- Integration Contract Section (PFLICHT!)
- Code Examples MANDATORY Section
- DELIVERABLES_START/END Marker
- Alle ACs im GIVEN/WHEN/THEN Format
```

#### Slice-Writer Prompt (Fix-Versuch):

```
FIX Slice {slice_number}: {slice_name}

## Compliance-Fehler (MUSS gefixt werden)
Lies: {spec_path}/slices/compliance-slice-{NN}.md

## Blocking Issues
{blocking_issues_summary}

## Anweisungen
1. Lies den Compliance-Report vollstaendig
2. Fixe ALLE Blocking Issues
3. Aktualisiere: {spec_path}/slices/slice-{NN}-{slug}.md
```

#### Slice-Compliance Prompt:

```
Pruefe Slice Compliance.

## Zu pruefender Slice
{spec_path}/slices/slice-{NN}-{slug}.md

## Referenz-Dokumente
- {spec_path}/architecture.md
- {spec_path}/wireframes.md
- Vorherige genehmigte Slices: {approved_slices_paths}

## Output
Schreibe: {spec_path}/slices/compliance-slice-{NN}.md

## KRITISCH - Template-Compliance pruefen!
Pruefe ob diese Sections existieren:
- [ ] Metadata Section (ID, Test, E2E, Dependencies)
- [ ] Integration Contract Section
- [ ] DELIVERABLES_START/END Marker
- [ ] Code Examples MANDATORY Section
FEHLENDE SECTIONS = BLOCKING ISSUE!

Am Ende MUSS stehen:
VERDICT: APPROVED oder VERDICT: FAILED

Falls FAILED, liste alle BLOCKING_ISSUES auf.
```

### 6. Wiederverwendete Code-Bausteine

| Pattern | Quelle | Wiederverwendung |
|---------|--------|-----------------|
| Task(slice-writer) Prompt-Format | `.claude/commands/planner.md` Phase 3 | Exakt gleicher Prompt, nur von Agent statt Command aufgerufen |
| Task(slice-compliance) Prompt-Format | `.claude/commands/planner.md` Phase 3 | Exakt gleicher Prompt |
| Verdict-Parsing | `.claude/commands/planner.md` Phase 3 Step 4 | `VERDICT: APPROVED` / `VERDICT: FAILED` String-Matching |
| Blocking Issues Extraction | `.claude/commands/planner.md` Phase 3 | Extrahiere Issues aus Compliance-Report |
| Fresh Context Pattern | `.claude/commands/planner.md` | Jeder Task()-Call bekommt frischen Context |

---

## Acceptance Criteria

1) GIVEN ein spec_path mit discovery.md und architecture.md
   WHEN der slice-plan-coordinator mit slice_number=1 und einer gultigen slice_description aufgerufen wird
   THEN erstellt der Agent die Datei `{spec_path}/slices/slice-01-{slug}.md` via Task(slice-writer)

2) GIVEN eine erstellte Slice-Datei
   WHEN der Agent Task(slice-compliance) ausfuehrt
   THEN wird die Datei `{spec_path}/slices/compliance-slice-01.md` erstellt

3) GIVEN ein Compliance-Report mit "VERDICT: APPROVED"
   WHEN der Agent das Verdict liest
   THEN gibt der Agent JSON zurueck mit `{"status": "approved", "retries": 0, "slice_file": "slices/slice-01-{slug}.md", "blocking_issues": []}`

4) GIVEN ein Compliance-Report mit "VERDICT: FAILED" und Blocking Issues
   WHEN der Agent das Verdict liest
   THEN ruft der Agent Task(slice-writer) erneut auf mit einem Fix-Prompt der die Blocking Issues enthaelt

5) GIVEN ein Compliance-Report mit "VERDICT: FAILED" nach 9 Retries
   WHEN der retry_count >= 9 erreicht wird
   THEN gibt der Agent JSON zurueck mit `{"status": "failed", "retries": 9, "slice_file": "slices/slice-01-{slug}.md", "blocking_issues": ["..."]}`

6) GIVEN approved_slices_paths mit Pfaden zu vorherigen genehmigten Slices
   WHEN der Agent Task(slice-writer) aufruft
   THEN werden die approved_slices_paths im Prompt an den slice-writer uebergeben (Integration Contract Kontext)

7) GIVEN ein Fix-Versuch nach VERDICT: FAILED
   WHEN der Agent Task(slice-writer) mit Fix-Prompt aufruft
   THEN referenziert der Fix-Prompt die Compliance-Datei `{spec_path}/slices/compliance-slice-{NN}.md` und listet die blocking_issues_summary auf

---

## Testfaelle

### Test-Datei

**Konvention:** Manuelle Tests - Agent-Datei erzeugt keinen ausfuehrbaren Code.

### Manuelle Tests

1. **Happy Path:** Agent mit einem einfachen Slice aufrufen (z.B. DB-Schema Slice).
   - Erwartung: `slices/slice-01-{slug}.md` wird erstellt, `slices/compliance-slice-01.md` wird erstellt, JSON mit `"status": "approved"` wird zurueckgegeben.

2. **Retry Path:** Agent mit einem absichtlich unvollstaendigen Slice aufrufen (z.B. fehlende Integration Contract Section).
   - Erwartung: Compliance Report mit VERDICT: FAILED, Agent ruft slice-writer erneut auf mit Fix-Prompt, zweiter Versuch wird APPROVED.

3. **Max Retries:** Agent mit einem Slice aufrufen der nie die Compliance passiert (Edge Case).
   - Erwartung: Nach 9 Retries gibt Agent JSON mit `"status": "failed"` und `"blocking_issues"` zurueck.

4. **Integration Context:** Agent mit approved_slices_paths aufrufen.
   - Erwartung: slice-writer-Prompt enthaelt die Pfade zu vorherigen Slices.

---

## Definition of Done

- [x] Akzeptanzkriterien sind eindeutig & vollstaendig
- [x] Agent-Datei folgt bestehendem Agent-Format (YAML Frontmatter)
- [x] Task()-Call-Prompts sind identisch mit bestehendem planner.md Pattern
- [x] JSON Output Contract ist definiert und konsistent mit architecture.md
- [x] Retry-Logik mit max 9 Versuchen implementiert

---

## Integration Contract (GATE 2 PFLICHT)

### Requires From Other Slices

| Slice | Resource | Type | Validation |
|-------|----------|------|------------|
| -- | Keine Abhaengigkeiten | -- | -- |

**Externe Abhaengigkeiten (bestehende, unveraenderte Agents):**

| Agent | Resource | Type | Validation |
|-------|----------|------|------------|
| `slice-writer` | Task()-Aufruf | Agent (Ebene 2) | Erstellt `slices/slice-NN-slug.md` |
| `slice-compliance` | Task()-Aufruf | Agent (Ebene 2) | Erstellt `slices/compliance-slice-NN.md`, enthaelt VERDICT Zeile |

### Provides To Other Slices

| Resource | Type | Consumer | Interface |
|----------|------|----------|-----------|
| `slice-plan-coordinator` Agent | Agent (Ebene 1) | Slice 3 (`/build` Command) | `Task(subagent_type: "slice-plan-coordinator")` -> JSON `{status, retries, slice_file, blocking_issues}` |
| JSON Output Contract | Data Contract | Slice 3 (`/build` Command) | `{"status": "approved\|failed", "retries": int, "slice_file": string, "blocking_issues": string[]}` |

### Integration Validation Tasks

- [ ] `slice-writer` Agent existiert und ist unveraendert aufrufbar
- [ ] `slice-compliance` Agent existiert und ist unveraendert aufrufbar
- [ ] JSON Output kann vom `/build` Command geparst werden (Pattern: "Find LAST ```json``` block")
- [ ] Prompts an slice-writer und slice-compliance sind kompatibel mit deren erwarteten Inputs

---

## Code Examples (MANDATORY - GATE 2 PFLICHT)

> **KRITISCH:** Alle Code-Beispiele in diesem Dokument sind **PFLICHT-Deliverables**.
> Der Gate 2 Compliance Agent prueft, dass jedes Code-Beispiel implementiert wird.

| Code Example | Section | Mandatory | Notes |
|--------------|---------|-----------|-------|
| Agent YAML Frontmatter | Agent-Datei Header | YES | Name, Description, Tools |
| Retry-Loop Pseudocode | Agent-Datei Core Logic | YES | Max 9 Retries, VERDICT-Parsing |
| JSON Output Block | Agent-Datei Abschluss | YES | Exakt wie Output Contract definiert |
| slice-writer Prompt (Erst-Erstellung) | Agent-Datei Phase 2 | YES | Identisch mit planner.md Pattern |
| slice-writer Prompt (Fix-Versuch) | Agent-Datei Phase 5 | YES | Referenziert Compliance-Report |
| slice-compliance Prompt | Agent-Datei Phase 3 | YES | Identisch mit planner.md Pattern |

### Agent YAML Frontmatter

```yaml
---
name: slice-plan-coordinator
description: "Ebene-1 Coordinator: Plant + validiert 1 Slice via Task(slice-writer) + Task(slice-compliance). Retry-Loop (max 9). Returns JSON."
tools: Read, Write, Glob, Grep, Task
---
```

### Agent Core Logic (Retry-Loop)

```markdown
## Phase 2: Planning Loop

MAX_RETRIES = 9
retry_count = 0

WHILE retry_count < MAX_RETRIES:

  # Step 1: Slice erstellen (oder fixen)
  IF retry_count == 0:
    Task(
      subagent_type: "slice-writer",
      description: "Write Slice {slice_number}",
      prompt: "{erst-erstellungs-prompt}"
    )
  ELSE:
    Task(
      subagent_type: "slice-writer",
      description: "Fix Slice {slice_number}",
      prompt: "{fix-prompt mit blocking_issues}"
    )

  # Step 2: Validation Checkpoint
  IF NOT EXISTS {spec_path}/slices/slice-{NN}-*.md:
    retry_count++
    CONTINUE

  # Step 3: Gate 2 Compliance
  Task(
    subagent_type: "slice-compliance",
    description: "Gate 2 Check Slice {slice_number}",
    prompt: "{compliance-prompt}"
  )

  # Step 4: Verdict pruefen
  compliance_report = Read({spec_path}/slices/compliance-slice-{NN}.md)

  IF compliance_report CONTAINS "VERDICT: APPROVED":
    RETURN JSON: {"status": "approved", "retries": retry_count, "slice_file": "...", "blocking_issues": []}

  IF compliance_report CONTAINS "VERDICT: FAILED":
    blocking_issues = extract_blocking_issues(compliance_report)
    retry_count++

    IF retry_count >= MAX_RETRIES:
      RETURN JSON: {"status": "failed", "retries": 9, "slice_file": "...", "blocking_issues": [...]}

# Should not reach here
RETURN JSON: {"status": "failed", "retries": MAX_RETRIES, "slice_file": "...", "blocking_issues": ["Unexpected loop exit"]}
```

### JSON Output Format

```markdown
## Phase 3: JSON Output

Am Ende deiner Ausfuehrung gibst du EXAKT dieses JSON zurueck:

\```json
{
  "status": "approved",
  "retries": 0,
  "slice_file": "slices/slice-01-db-schema.md",
  "blocking_issues": []
}
\```

KRITISCH: Das JSON MUSS das LETZTE Code-Block in deiner Antwort sein.
Der /build Command parst es mit dem Pattern "Find LAST ```json``` block".
```

---

## Constraints & Hinweise

**Betrifft:**
- Nur die Datei `.claude/agents/slice-plan-coordinator.md`
- Keine Aenderungen an bestehenden Agents oder Commands

**Agent-Format:**
- YAML Frontmatter mit `name`, `description`, `tools`
- Markdown-Body mit Pseudocode-Logik (kein ausfuehrbarer Code)
- Identisches Format wie bestehende Agents (z.B. `.claude/agents/slice-compliance.md`)

**Abgrenzung:**
- Dieser Agent plant EINEN Slice, nicht alle Slices
- Die Slice-Reihenfolge und Gesamtsteuerung liegt beim `/build` Command (Slice 3)
- Bestehende Sub-Agents (slice-writer, slice-compliance) bleiben unveraendert

---

## Deliverables (SCOPE SAFEGUARD)

**WICHTIG: Diese Liste wird automatisch vom Stop-Hook validiert. Der Agent kann nicht stoppen, wenn Dateien fehlen.**

<!-- DELIVERABLES_START -->
### Agent-Datei
- [ ] `.claude/agents/slice-plan-coordinator.md` -- Neuer Ebene-1 Coordinator Agent fuer Planning + Validation eines einzelnen Slices

### Tests
- [ ] Manuelle Validierung: Agent mit einem Test-Slice aufrufen und pruefen ob `slices/` und `compliance/` Dateien erstellt werden und JSON-Output korrekt ist
<!-- DELIVERABLES_END -->

**Hinweis fuer den Implementierungs-Agent:**
- Alle Dateien zwischen `<!-- DELIVERABLES_START -->` und `<!-- DELIVERABLES_END -->` sind **Pflicht**
- Der Stop-Hook prueft automatisch ob alle Dateien existieren
- Bei fehlenden Dateien wird der Agent blockiert und muss nachfragen

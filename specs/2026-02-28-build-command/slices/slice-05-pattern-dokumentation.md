# Slice 5: Workflow-Patterns dokumentieren

> **Slice 5 von 5** fuer `build-command`
>
> | Navigation | |
> |------------|---|
> | **Vorheriger:** | `slice-04-multi-spec-support.md` |
> | **Naechster:** | -- |

---

## Metadata (fuer Orchestrator)

| Key | Value |
|-----|-------|
| **ID** | `slice-05-pattern-dokumentation` |
| **Test** | `N/A (Review - Dokumentations-Datei)` |
| **E2E** | `false` |
| **Dependencies** | `[]` |

---

## Test-Strategy (fuer Orchestrator Pipeline)

> **Quelle:** Auto-detected basierend auf Repo-Indikatoren. Dieser Slice erstellt eine Dokumentations-Markdown-Datei, keinen ausfuehrbaren Code.

| Key | Value |
|-----|-------|
| **Stack** | `documentation` (Markdown Dokumentation) |
| **Test Command** | `N/A` (Dokumentation, kein ausfuehrbarer Code) |
| **Integration Command** | `N/A` |
| **Acceptance Command** | `Manuell: Pruefe ob .claude/docs/workflow-patterns.md existiert und alle 15 Patterns enthaelt` |
| **Start Command** | `N/A` |
| **Health Endpoint** | `N/A` |
| **Mocking Strategy** | `no_mocks` |

---

## Slice-Uebersicht

| # | Slice | Status | Datei |
|---|-------|--------|-------|
| 1 | slice-plan-coordinator Agent | Done | `slice-01-slice-plan-coordinator.md` |
| 2 | slice-impl-coordinator Agent | Done | `slice-02-slice-impl-coordinator.md` |
| 3 | /build Command | Done | `slice-03-build-command.md` |
| 4 | Multi-Spec Support | Done | `slice-04-multi-spec-support.md` |
| 5 | **Pattern-Dokumentation** | Ready | `slice-05-pattern-dokumentation.md` |

---

## Kontext & Ziel

Die 15 identifizierten Workflow-Patterns sind aktuell ueber verschiedene Quellen verstreut: discovery.md, architecture.md, bestehende Agent-Dateien und Commands. Es gibt keine zentrale, durchsuchbare Referenz. Neue Agents oder Commands muessen die Patterns aus mehreren Dateien zusammensuchen.

**Problem:** Workflow-Patterns sind nicht konsolidiert dokumentiert. Wissen ist implizit in Agent-Dateien und Commands verteilt. Bei neuen Features muss der Entwickler (oder Agent) die Patterns selbst identifizieren.

**Loesung:** Eine zentrale Pattern-Referenz unter `.claude/docs/workflow-patterns.md` die alle 15 Patterns mit Name, Beschreibung, Quelle, Anwendungsbeispiel und Implementierungshinweisen dokumentiert.

---

## Technische Umsetzung

### Architektur-Kontext (aus architecture.md)

> **Quelle:** `architecture.md` -> "Architecture Layers", `discovery.md` -> "Identifizierte Workflow-Patterns"

```
.claude/
  +-- agents/          <- Bestehende Agents (verwenden Patterns implizit)
  +-- commands/         <- Bestehende Commands (verwenden Patterns implizit)
  +-- docs/             <- NEU: Zentrale Dokumentation
  |     +-- workflow-patterns.md  <- NEU: Pattern-Referenz
  +-- templates/        <- Bestehende Templates
  +-- skills/           <- Bestehende Skills
```

### 1. Architektur-Impact

| Layer | Aenderungen |
|-------|------------|
| `.claude/docs/` | Neues Verzeichnis + Datei `workflow-patterns.md` |

### 2. Datenfluss

```
Input: 15 Patterns aus discovery.md + Codebase-Recherche
  |
  v
Recherche: Bestehende Agent-/Command-Dateien auf Pattern-Verwendung pruefen
  |
  v
Konsolidierung: Alle Patterns mit einheitlichem Format dokumentieren
  |
  v
Output: .claude/docs/workflow-patterns.md
```

### 3. Pattern-Katalog (alle 15 Patterns)

Jedes Pattern MUSS mit folgendem Format dokumentiert werden:

```
### Pattern N: {Pattern-Name}

**Quelle:** {Externer Link oder "Eigenes Pattern"}
**Kategorie:** {Context Management | Quality Assurance | Architecture | Data Flow | Orchestration}
**Verwendet in:** {Liste von Agent-/Command-Dateien die dieses Pattern nutzen}

**Problem:** {Welches Problem loest das Pattern?}
**Loesung:** {Wie loest das Pattern das Problem?}
**Konsequenzen:** {Trade-offs und Auswirkungen}

**Implementierungshinweise:**
- {Konkrete Anwendungsregel 1}
- {Konkrete Anwendungsregel 2}

**Beispiel:**
{Konkretes Beispiel aus der Codebase}
```

### 4. Die 15 Patterns mit Zuordnung

| # | Pattern-Name | Kategorie | Verwendet in |
|---|-------------|-----------|-------------|
| 1 | Fresh Context Pattern | Context Management | Alle Task()-Calls in planner.md, orchestrate.md, build.md, slice-plan-coordinator.md, slice-impl-coordinator.md |
| 2 | External Validation Pattern | Quality Assurance | orchestrate.md (test-validator prueft, nicht implementer), build.md |
| 3 | Hard Gate Pattern | Quality Assurance | planner.md (Gate 2, Gate 3), orchestrate.md, build.md (max 9 Retries) |
| 4 | Evidence-on-Disk Pattern | Data Flow | orchestrate.md (.claude/evidence/), slice-impl-coordinator.md |
| 5 | State-on-Disk Pattern | Data Flow | planner.md (.planner-state.json), orchestrate.md (.orchestrator-state.json), build.md (.build-state.json) |
| 6 | Diverge-Converge Pattern | Architecture | discovery.md (breite Recherche -> konvergieren auf Scope) |
| 7 | Multi-Gate Pipeline Pattern | Quality Assurance | planner.md (Gate 0 -> Gate 1 -> Gate 2 -> Gate 3) |
| 8 | Slice Architecture Pattern | Architecture | Alle Specs (Feature -> testbare Slices mit Dependency-Graph) |
| 9 | Sub-Agent Pipeline Pattern | Orchestration | orchestrate.md (Implementer -> Test-Writer -> Test-Validator -> Debugger), slice-impl-coordinator.md |
| 10 | JSON Output Contract Pattern | Data Flow | Alle Sub-Agents (slice-implementer, test-writer, test-validator, debugger), slice-plan-coordinator, slice-impl-coordinator |
| 11 | Spec-as-Contract Pattern | Architecture | Slice-Specs sind verbindliches Interface zwischen Planning und Execution |
| 12 | Integration Contract Pattern | Architecture | Alle Slice-Specs ("Requires From" / "Provides To" Sections) |
| 13 | Hierarchical Delegation Pattern | Orchestration | build.md (Ebene 0 -> Ebene 1 -> Ebene 2) |
| 14 | Reference Handoff Pattern | Data Flow | Alle Sub-Agents (schreiben auf Disk, uebergeben nur Pfade) |
| 15 | Incremental Progress Pattern | Orchestration | planner.md, orchestrate.md, build.md (ein Slice nach dem anderen, State nach jedem Schritt) |

### 5. Kategorien-Uebersicht

| Kategorie | Patterns | Beschreibung |
|-----------|----------|-------------|
| Context Management | 1 (Fresh Context) | Wie Context-Pollution und -Overflow vermieden wird |
| Quality Assurance | 2, 3, 7 (External Validation, Hard Gate, Multi-Gate Pipeline) | Wie Qualitaet sichergestellt wird |
| Architecture | 6, 8, 11, 12 (Diverge-Converge, Slice Architecture, Spec-as-Contract, Integration Contract) | Wie Features strukturiert werden |
| Data Flow | 4, 5, 10, 14 (Evidence-on-Disk, State-on-Disk, JSON Output Contract, Reference Handoff) | Wie Daten zwischen Agents fliessen |
| Orchestration | 9, 13, 15 (Sub-Agent Pipeline, Hierarchical Delegation, Incremental Progress) | Wie Agents koordiniert werden |

### 6. Wiederverwendete Code-Bausteine

| Pattern | Quelle | Wiederverwendung |
|---------|--------|-----------------|
| Pattern-Liste | `discovery.md` -> "Identifizierte Workflow-Patterns" | Alle 15 Patterns mit Namen und Quellen |
| Pattern-Verwendung in Agents | `.claude/agents/*.md` | Grep nach Pattern-Anwendungen |
| Pattern-Verwendung in Commands | `.claude/commands/*.md` | Grep nach Pattern-Anwendungen |
| Anthropic Best Practices Links | `discovery.md` -> "Context & Research" | Externe Quellen-Links |

---

## Acceptance Criteria

1) GIVEN die Datei `.claude/docs/workflow-patterns.md` existiert nicht
   WHEN der Implementierungs-Agent diesen Slice umsetzt
   THEN wird das Verzeichnis `.claude/docs/` erstellt und die Datei `workflow-patterns.md` darin angelegt

2) GIVEN die Datei `workflow-patterns.md` ist erstellt
   WHEN ein Reviewer die Datei oeffnet
   THEN enthaelt sie exakt 15 Pattern-Eintraege, jeweils mit Name, Quelle, Kategorie, "Verwendet in", Problem, Loesung, Konsequenzen, Implementierungshinweisen und Beispiel

3) GIVEN ein neuer Agent oder Command soll erstellt werden
   WHEN der Entwickler oder Agent die Pattern-Referenz konsultiert
   THEN findet er zu jedem Pattern konkrete Implementierungshinweise und Beispiele aus der bestehenden Codebase

4) GIVEN die Pattern-Referenz listet "Verwendet in" fuer jedes Pattern
   WHEN die Angaben geprueft werden
   THEN referenzieren die "Verwendet in"-Eintraege ausschliesslich tatsaechlich existierende Dateien unter `.claude/agents/` oder `.claude/commands/`

5) GIVEN die Pattern-Referenz enthaelt eine Kategorien-Uebersicht
   WHEN ein Reviewer die Kategorien prueft
   THEN sind alle 15 Patterns einer der 5 Kategorien zugeordnet: Context Management, Quality Assurance, Architecture, Data Flow, Orchestration

6) GIVEN die Pattern-Referenz enthaelt externe Quellen-Links
   WHEN die Links geprueft werden
   THEN verweisen sie auf die korrekten Anthropic Research-Seiten und Phil Schmid Blog-Posts wie in discovery.md dokumentiert

7) GIVEN Pattern 13 "Hierarchical Delegation Pattern"
   WHEN der Eintrag geprueft wird
   THEN beschreibt er die 3-Ebenen-Architektur (Ebene 0: /build, Ebene 1: Coordinator-Agents, Ebene 2: Worker-Agents) und referenziert `.claude/commands/build.md`, `.claude/agents/slice-plan-coordinator.md` und `.claude/agents/slice-impl-coordinator.md`

8) GIVEN das Dokument ist vollstaendig
   WHEN nach Platzhaltern oder TODOs gesucht wird
   THEN enthaelt das Dokument keine TODOs, KLAEREN-Marker oder "..." Platzhalter

---

## Testfaelle

### Test-Datei

**Konvention:** Manuelle Review-Tests - Dokumentation erzeugt keinen ausfuehrbaren Code.

### Manuelle Tests

1. **Vollstaendigkeit:** Oeffne `.claude/docs/workflow-patterns.md` und zaehle die Pattern-Eintraege.
   - Erwartung: Exakt 15 Patterns mit allen Pflichtfeldern (Name, Quelle, Kategorie, Verwendet in, Problem, Loesung, Konsequenzen, Implementierungshinweise, Beispiel).

2. **Korrektheit der "Verwendet in"-Referenzen:** Pruefe fuer jedes Pattern ob die referenzierten Dateien existieren.
   - Erwartung: Alle referenzierten `.claude/agents/*.md` und `.claude/commands/*.md` Dateien existieren tatsaechlich.

3. **Kategorien-Zuordnung:** Pruefe ob alle 15 Patterns einer Kategorie zugeordnet sind.
   - Erwartung: Keine Pattern ohne Kategorie. Jedes Pattern gehoert zu genau einer der 5 Kategorien.

4. **Externe Links:** Pruefe ob die Quellen-Links gueltig sind.
   - Erwartung: Links zu Anthropic Engineering Blog und Phil Schmid Blog sind korrekt.

5. **Keine Platzhalter:** Suche nach "TODO", "KLAEREN", "...", "TBD" im Dokument.
   - Erwartung: Keine Platzhalter gefunden.

6. **Konsistenz mit Discovery:** Vergleiche Pattern-Namen und -Beschreibungen mit `discovery.md` -> "Identifizierte Workflow-Patterns".
   - Erwartung: Alle 15 Patterns aus Discovery sind enthalten. Namen stimmen ueberein.

7. **Hierarchical Delegation:** Pruefe ob Pattern 13 die neue 3-Ebenen-Architektur korrekt beschreibt.
   - Erwartung: Beschreibt Ebene 0 (/build), Ebene 1 (Coordinator-Agents), Ebene 2 (Worker-Agents) mit konkreten Datei-Referenzen.

---

## Definition of Done

- [x] Akzeptanzkriterien sind eindeutig & vollstaendig
- [x] Alle 15 Patterns aus Discovery sind identifiziert und zugeordnet
- [x] Einheitliches Dokumentationsformat fuer alle Patterns definiert
- [x] Kategorisierung in 5 Bereiche festgelegt
- [x] "Verwendet in"-Referenzen auf bestehende Codebase-Dateien vorbereitet

---

## Integration Contract (GATE 2 PFLICHT)

### Requires From Other Slices

| Slice | Resource | Type | Validation |
|-------|----------|------|------------|
| -- | Keine harten Abhaengigkeiten | -- | -- |

**Hinweis:** Dieser Slice kann parallel zu allen anderen Slices laufen. Die "Verwendet in"-Referenzen fuer die neuen Dateien aus Slice 1-4 (`slice-plan-coordinator.md`, `slice-impl-coordinator.md`, `build.md`) werden beim Schreiben der Dokumentation beruecksichtigt, sind aber keine blockierende Abhaengigkeit. Sollten die Dateien noch nicht existieren, werden die Referenzen trotzdem korrekt dokumentiert (die Dateien werden durch Slice 1-4 erstellt).

**Inhaltliche Abhaengigkeiten (nicht-blockierend, fuer vollstaendige Dokumentation):**

| Slice | Resource | Type | Hinweis |
|-------|----------|------|---------|
| slice-01 | `.claude/agents/slice-plan-coordinator.md` | Agent-Datei | Wird in "Verwendet in" referenziert fuer Patterns 1, 3, 10, 13, 14 |
| slice-02 | `.claude/agents/slice-impl-coordinator.md` | Agent-Datei | Wird in "Verwendet in" referenziert fuer Patterns 1, 3, 4, 9, 10, 13, 14 |
| slice-03 | `.claude/commands/build.md` | Command-Datei | Wird in "Verwendet in" referenziert fuer Patterns 1, 3, 5, 7, 10, 13, 15 |

### Provides To Other Slices

| Resource | Type | Consumer | Interface |
|----------|------|----------|-----------|
| `.claude/docs/workflow-patterns.md` | Dokumentation | Zukuenftige Agents/Commands | Lesbare Markdown-Referenz, durchsuchbar via Grep |
| Pattern-Katalog | Wissensbasis | Slice-Writer Agent | Kann Pattern-Referenzen in neue Slice-Specs einbauen |

### Integration Validation Tasks

- [ ] Verzeichnis `.claude/docs/` existiert oder wird erstellt
- [ ] Datei `.claude/docs/workflow-patterns.md` enthaelt alle 15 Patterns
- [ ] "Verwendet in"-Referenzen verweisen auf existierende oder durch andere Slices erstellte Dateien
- [ ] Keine zirkulaeren Abhaengigkeiten (Dokumentation referenziert Agents, Agents referenzieren nicht zurueck)

---

## Code Examples (MANDATORY - GATE 2 PFLICHT)

> **KRITISCH:** Alle Code-Beispiele in diesem Dokument sind **PFLICHT-Deliverables**.
> Der Gate 2 Compliance Agent prueft, dass jedes Code-Beispiel implementiert wird.

| Code Example | Section | Mandatory | Notes |
|--------------|---------|-----------|-------|
| Dokument-Header | workflow-patterns.md Kopf | YES | Titel, Einleitung, Kategorien-Uebersicht |
| Pattern-Entry Format | Pro Pattern | YES | Alle 15 Patterns im einheitlichen Format |
| Kategorien-Uebersichtstabelle | workflow-patterns.md | YES | 5 Kategorien mit zugeordneten Patterns |
| Quick-Reference-Tabelle | workflow-patterns.md Ende | YES | Alle 15 Patterns in kompakter Uebersicht |

### Dokument-Header

```markdown
# Workflow-Patterns Referenz

> Zentrale Dokumentation aller 15 identifizierten Workflow-Patterns im feedbackai-mvp Projekt.
> Diese Patterns bilden die Grundlage fuer alle Agent- und Command-Definitionen.

## Kategorien

| Kategorie | Patterns | Fokus |
|-----------|----------|-------|
| Context Management | Fresh Context | Context-Pollution und -Overflow vermeiden |
| Quality Assurance | External Validation, Hard Gate, Multi-Gate Pipeline | Qualitaet automatisiert sicherstellen |
| Architecture | Diverge-Converge, Slice Architecture, Spec-as-Contract, Integration Contract | Feature-Strukturierung und Interfaces |
| Data Flow | Evidence-on-Disk, State-on-Disk, JSON Output Contract, Reference Handoff | Datenaustausch zwischen Agents |
| Orchestration | Sub-Agent Pipeline, Hierarchical Delegation, Incremental Progress | Agent-Koordinierung und -Steuerung |

---
```

### Pattern-Entry Format (Beispiel: Fresh Context Pattern)

```markdown
### Pattern 1: Fresh Context Pattern

**Quelle:** [Anthropic Multi-Agent Research](https://www.anthropic.com/engineering/multi-agent-research-system)
**Kategorie:** Context Management
**Verwendet in:**
- `.claude/commands/planner.md` -- Task()-Calls an slice-writer, slice-compliance
- `.claude/commands/orchestrate.md` -- Task()-Calls an slice-implementer, test-writer, test-validator, debugger
- `.claude/commands/build.md` -- Task()-Calls an slice-plan-coordinator, slice-impl-coordinator, integration-map
- `.claude/agents/slice-plan-coordinator.md` -- Task()-Calls an slice-writer, slice-compliance
- `.claude/agents/slice-impl-coordinator.md` -- Task()-Calls an slice-implementer, test-writer, test-validator, debugger

**Problem:** Wenn ein Orchestrator mehrere Sub-Agent-Aufrufe im selben Context ausfuehrt, akkumulieren sich die Outputs. Bei 7+ Slices mit Retries erreicht der Context 35.000-105.000 Tokens. Das fuehrt zu Context Pollution (irrelevante Informationen beeinflussen spaetere Entscheidungen) und Confirmation Bias (Agent wiederholt fruehere Fehler).

**Loesung:** Jeder Sub-Agent wird ueber `Task()` mit einem voellig frischen Context aufgerufen. Der Sub-Agent erhaelt nur die fuer seine Aufgabe notwendigen Informationen (Pfade zu Dateien, spezifische Anweisungen). Der Orchestrator erhaelt nur ein kompaktes JSON-Ergebnis zurueck (~300 Tokens).

**Konsequenzen:**
- Pro: Kein Context-Overflow, keine Cross-Contamination zwischen Slices
- Pro: Sub-Agent kann die volle Context-Groesse fuer seine Aufgabe nutzen
- Con: Hoehere Latenz durch Task()-Call Overhead
- Con: Sub-Agent hat keinen Zugriff auf vorherige Interaktionen

**Implementierungshinweise:**
- Uebergib Sub-Agents NUR Dateipfade, nicht Dateiinhalte
- Der Sub-Agent liest die Dateien selbst mit Read()
- Rueckgabe NUR als strukturiertes JSON (~300 Tokens)
- Keine "Zusammenfassungen" von vorherigen Schritten im Prompt

**Beispiel:**
```
# Im /build Command:
Task(
  subagent_type: "slice-plan-coordinator",
  prompt: "Plane Slice 3. spec_path: specs/feature-x. approved_slices: [slices/slice-01.md, slices/slice-02.md]"
)
# -> Coordinator bekommt frischen Context
# -> Liest Dateien selbst
# -> Returniert: {"status": "approved", "retries": 1, "slice_file": "slices/slice-03.md"}
```
```

### Kategorien-Uebersichtstabelle

```markdown
## Pattern-Kategorien

### Context Management (1 Pattern)
Patterns die sicherstellen, dass Agent-Contexts nicht ueberlaufen oder verschmutzt werden.

### Quality Assurance (3 Patterns)
Patterns die automatisierte Qualitaetspruefungen erzwingen.

### Architecture (4 Patterns)
Patterns die die Strukturierung von Features und deren Interfaces definieren.

### Data Flow (4 Patterns)
Patterns die den Datenaustausch zwischen Agents und deren Persistierung regeln.

### Orchestration (3 Patterns)
Patterns die die Koordinierung und Reihenfolge von Agent-Aufrufen steuern.
```

### Quick-Reference-Tabelle

```markdown
## Quick Reference

| # | Pattern | Kategorie | Kernregel | Primaere Quelle |
|---|---------|-----------|-----------|-----------------|
| 1 | Fresh Context | Context Mgmt | Jeder Task()-Call = frischer Context | Anthropic Multi-Agent |
| 2 | External Validation | QA | Orchestrator testet, nicht Implementer | Anthropic Effective Agents |
| 3 | Hard Gate | QA | Max N Retries, dann HARD STOP | Eigenes Pattern |
| 4 | Evidence-on-Disk | Data Flow | Ergebnisse persistent in .claude/evidence/ | Anthropic Context Engineering |
| 5 | State-on-Disk | Data Flow | JSON State-File fuer Resume | Anthropic Long-Running Harnesses |
| 6 | Diverge-Converge | Architecture | Erst breit, dann fokussiert | Design Thinking |
| 7 | Multi-Gate Pipeline | QA | Sequenzielle Gates (0-3) | Eigenes Pattern |
| 8 | Slice Architecture | Architecture | Feature -> testbare Slices + Dependency-Graph | Eigenes Pattern |
| 9 | Sub-Agent Pipeline | Orchestration | Impl -> Test-Writer -> Validator -> Debugger | Eigenes Pattern |
| 10 | JSON Output Contract | Data Flow | Sub-Agents returnen strukturiertes JSON | Phil Schmid Context Engineering |
| 11 | Spec-as-Contract | Architecture | Slice-Specs = verbindliches Interface | Eigenes Pattern |
| 12 | Integration Contract | Architecture | "Requires From" / "Provides To" | Eigenes Pattern |
| 13 | Hierarchical Delegation | Orchestration | 3-Ebenen: Coordinator -> Slice-Coord -> Worker | Eigenes Pattern (NEU) |
| 14 | Reference Handoff | Data Flow | Nur Pfade uebergeben, nicht Inhalte | Anthropic Multi-Agent |
| 15 | Incremental Progress | Orchestration | Ein Slice nach dem anderen, State nach jedem Schritt | Anthropic Long-Running Harnesses |
```

---

## Constraints & Hinweise

**Betrifft:**
- Neues Verzeichnis `.claude/docs/` und neue Datei `workflow-patterns.md`
- Keine Aenderungen an bestehenden Agents, Commands oder Templates

**Dokumentationsformat:**
- Einheitliches Format fuer alle 15 Patterns (siehe Code Examples)
- Markdown-Datei, durchsuchbar via Grep
- Keine eingebetteten Code-Dateien, nur Markdown-Beispiele

**Abgrenzung:**
- Dieses Slice dokumentiert NUR bestehende Patterns, es fuehrt KEINE neuen Patterns ein
- Die Dokumentation ist eine REFERENZ, kein Tutorial
- Keine Aenderungen an bestehenden Agent-Dateien (z.B. keine "Pattern: XY" Kommentare einfuegen)
- Die "Verwendet in"-Referenzen sind informativ, keine erzwungenen Imports

**Quellen-Treue:**
- Pattern-Namen MUESSEN exakt mit discovery.md uebereinstimmen
- Externe Quellen-Links MUESSEN die URLs aus discovery.md verwenden
- Eigene Patterns MUESSEN als "Eigenes Pattern" gekennzeichnet sein

---

## Deliverables (SCOPE SAFEGUARD)

**WICHTIG: Diese Liste wird automatisch vom Stop-Hook validiert. Der Agent kann nicht stoppen, wenn Dateien fehlen.**

<!-- DELIVERABLES_START -->
### Dokumentation
- [ ] `.claude/docs/workflow-patterns.md` -- Zentrale Pattern-Referenz mit allen 15 Workflow-Patterns, jeweils dokumentiert mit Name, Quelle, Kategorie, "Verwendet in", Problem, Loesung, Konsequenzen, Implementierungshinweisen und Beispiel. Enthaelt Kategorien-Uebersicht und Quick-Reference-Tabelle.

### Tests
- [ ] Manuelle Validierung: Pruefe ob `.claude/docs/workflow-patterns.md` existiert, exakt 15 Patterns enthaelt, alle "Verwendet in"-Referenzen auf existierende Dateien zeigen, keine TODOs/Platzhalter enthalten sind und Pattern-Namen mit discovery.md uebereinstimmen
<!-- DELIVERABLES_END -->

**Hinweis fuer den Implementierungs-Agent:**
- Alle Dateien zwischen `<!-- DELIVERABLES_START -->` und `<!-- DELIVERABLES_END -->` sind **Pflicht**
- Der Stop-Hook prueft automatisch ob alle Dateien existieren
- Bei fehlenden Dateien wird der Agent blockiert und muss nachfragen

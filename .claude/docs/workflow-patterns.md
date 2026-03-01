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

---

## Pattern 1: Fresh Context Pattern

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

---

## Pattern 2: External Validation Pattern

**Quelle:** [Anthropic Building Effective Agents](https://www.anthropic.com/research/building-effective-agents)
**Kategorie:** Quality Assurance
**Verwendet in:**
- `.claude/commands/orchestrate.md` -- test-validator prueft, nicht der implementer
- `.claude/commands/build.md` -- Task(test-validator) nach Task(slice-impl-coordinator)
- `.claude/agents/slice-impl-coordinator.md` -- Step 3: Task(test-validator) prueft Task(slice-implementer) Output

**Problem:** Wenn der Agent der Code implementiert auch seine eigenen Tests validiert, entsteht ein Interessenkonflikt. Der Implementer hat Confirmation Bias und uebersieht systematisch die gleichen Fehler.

**Loesung:** Ein separater, unabhaengiger Validator-Agent ueberprueft die Arbeit des Implementers. Der Orchestrator fungiert als Schiedsrichter. Exit Code des Validators ist die einzige Wahrheit.

**Konsequenzen:**
- Pro: Unabhaengige Pruefung verhindert Selbst-Validierung
- Pro: Klare Rollentrennung: Implementer schreibt, Validator prueft
- Con: Zusaetzlicher Task()-Call-Overhead

**Implementierungshinweise:**
- Exit Code != 0 = FEHLGESCHLAGEN (keine Ausnahmen)
- Der Implementer ruft NIEMALS Tests selbst aus
- Validator bekommt nur den Test-Pfad und Slice-Spec, keinen Implementation-Context

**Beispiel:**
```
# RICHTIG: Validator prueft Implementer-Output
Task(slice-implementer) -> Code schreiben
Task(test-validator) -> Tests ausfuehren und Ergebnis bewerten

# FALSCH: Implementer validiert sich selbst
Task(slice-implementer) -> Code schreiben UND Tests ausfuehren
```

---

## Pattern 3: Hard Gate Pattern

**Quelle:** Eigenes Pattern
**Kategorie:** Quality Assurance
**Verwendet in:**
- `.claude/commands/planner.md` -- Gate 2 (pro Slice), Gate 3 (Integration Map)
- `.claude/commands/orchestrate.md` -- Max 9 Retries pro Slice
- `.claude/commands/build.md` -- Max 9 Retries pro Phase (Planning, Gate 3, Impl, Final Validation)
- `.claude/agents/slice-plan-coordinator.md` -- MAX_RETRIES = 9 im Planning Loop
- `.claude/agents/slice-impl-coordinator.md` -- MAX_RETRIES = 9 im Validation Loop

**Problem:** Ohne harte Grenzen koennen Agents in endlosen Retry-Schleifen stecken oder bei Fehlern stillschweigend weitermachen. Das fuehrt zu inkonsistentem State und schwer debugbaren Problemen.

**Loesung:** Jede kritische Operation hat ein Maximum von N Retries (typisch: 9). Nach N Retries wird sofort gestoppt (HARD STOP) und der Fehler im State gespeichert. Kein stilles Weitermachen.

**Konsequenzen:**
- Pro: Vorhersagbares Verhalten, keine endlosen Loops
- Pro: Fehler werden sichtbar gemacht statt ignoriert
- Con: Bei echten transienten Fehlern koennte ein hoehereres Limit besser sein

**Implementierungshinweise:**
- MAX_RETRIES = 9 ist der Projektstandard
- Bei HARD STOP: State immer zuerst schreiben, dann stoppen
- Fehlermeldung muss den aktuellen Retry-Count enthalten
- HARD STOP gilt nur fuer den aktuellen Slice, nicht den gesamten Build-Run

**Beispiel:**
```
MAX_RETRIES = 9
retry_count = 0

WHILE retry_count < MAX_RETRIES:
  result = Task(...)
  IF result.status == "passed": BREAK
  retry_count++

IF retry_count >= MAX_RETRIES:
  Write(state_file, {status: "failed", error: "Max retries exceeded"})
  HARD STOP: "Failed after 9 retries"
```

---

## Pattern 4: Evidence-on-Disk Pattern

**Quelle:** [Anthropic Context Engineering](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)
**Kategorie:** Data Flow
**Verwendet in:**
- `.claude/commands/orchestrate.md` -- `.claude/evidence/{feature}/{slice_id}.json` nach jedem Slice
- `.claude/agents/slice-impl-coordinator.md` -- Phase 5: Evidence schreiben nach erfolgreichem Slice

**Problem:** Sub-Agent-Ergebnisse (welche Dateien geaendert, welche Tests geschrieben, Commit-Hash) existieren nur im Context des Coordinators. Bei Context-Compacting oder Session-Crash gehen diese Informationen verloren.

**Loesung:** Jedes Slice-Ergebnis wird sofort nach Abschluss als strukturierte JSON-Datei auf Disk geschrieben. Der Coordinator liest diese Datei spaeter falls noetig statt den Output im Context zu halten.

**Konsequenzen:**
- Pro: Crash-sicher, Evidence bleibt erhalten
- Pro: Evidence ist auditierbar und nachvollziehbar
- Con: Viele kleine JSON-Dateien auf Disk

**Implementierungshinweise:**
- Pfad-Konvention: `.claude/evidence/{feature_name}/{slice_id}.json`
- Immer ALLE relevanten Felder schreiben (slice_id, status, retries, files_changed, test_files, test_count, commit_hash, stages, timestamp)
- Evidence nach Phase 5 (Validation bestanden), nicht vorher

**Beispiel:**
```json
{
  "slice_id": "slice-02-api-integration",
  "status": "completed",
  "retries": 1,
  "files_changed": ["backend/app/api/endpoints.py"],
  "test_files": ["tests/slices/feature/slice-02.test.ts"],
  "test_count": 12,
  "commit_hash": "abc123def",
  "stages": {"unit": {"status": "passed", "test_count": 12, "failed_count": 0}},
  "timestamp": "2026-03-01T14:30:00Z"
}
```

---

## Pattern 5: State-on-Disk Pattern

**Quelle:** [Anthropic Long-Running Harnesses](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents)
**Kategorie:** Data Flow
**Verwendet in:**
- `.claude/commands/planner.md` -- `.planner-state.json` fuer Resume nach Unterbrechung
- `.claude/commands/orchestrate.md` -- `.orchestrator-state.json`
- `.claude/commands/build.md` -- `.build-state.json` nach JEDEM Task()-Call

**Problem:** Long-Running Agent-Sessions koennen durch Context-Compacting, Timeouts oder Nutzer-Unterbrechungen abgebrochen werden. Der gesamte Fortschritt geht verloren und der Build muss von vorne beginnen.

**Loesung:** Der Coordinator-State wird nach JEDEM Schritt als JSON-Datei auf Disk geschrieben. Beim naechsten Start liest der Command die State-Datei und setzt ab dem letzten erfolgreichen Schritt fort.

**Konsequenzen:**
- Pro: Resume-faehig nach jeder Unterbrechung
- Pro: State ist immer konsistent (keine Partial-Updates)
- Con: Viele Write()-Calls verlangsamen den Run leicht

**Implementierungshinweise:**
- State-Datei IMMER vor dem ersten Task()-Call initialisieren
- Nach JEDEM Task()-Call: `last_updated` und `last_action` aktualisieren
- Resume-Logik: `in_progress` -> weitermachen, `failed` -> Fehler zeigen + weitermachen, `completed` -> stoppen
- State-Datei liegt bei `{spec_path}/.build-state.json` (pro Spec, pro Command-Typ)

**Beispiel:**
```json
{
  "status": "in_progress",
  "phase": "implementing",
  "current_slice_index": 2,
  "last_action": "Slice 2 completed",
  "last_updated": "2026-03-01T14:30:00Z"
}
```

---

## Pattern 6: Diverge-Converge Pattern

**Quelle:** Design Thinking
**Kategorie:** Architecture
**Verwendet in:**
- `.claude/commands/discovery.md` -- Erst breite Recherche (diverge), dann Scope-Definition (converge)
- `.claude/agents/discovery.md` -- Q&A-Session divergiert, dann konvergiert auf Discovery-Dokument

**Problem:** Features werden oft zu frueh und zu eng definiert. Wichtige Anforderungen und Constraints werden erst spaet entdeckt, wenn der Implementation-Aufwand fuer Aenderungen bereits hoch ist.

**Loesung:** Die Discovery-Phase startet mit breiter Recherche (divergieren) und konvergiert dann auf einen klar definierten Scope, Flows und Feature States. Erst nach der Konvergenz wird mit der technischen Architektur begonnen.

**Konsequenzen:**
- Pro: Wichtige Anforderungen werden fruehzeitig entdeckt
- Pro: Scope-Creep wird durch explizite Konvergenz verhindert
- Con: Discovery-Phase braucht mehr Zeit als direktes Implementieren

**Implementierungshinweise:**
- Diverge-Phase: Moeglichst viele User-Flows, States und Edge Cases sammeln
- Converge-Phase: Explizit Out-of-Scope markieren was nicht in diesem Feature ist
- Discovery-Dokument ist das Ergebnis der Konvergenz, nicht der Divergenz

**Beispiel:**
```
Discovery-Session:
DIVERGE: "Was koennte alles in einem /build Command sein?"
  - Planning, Orchestration, Testing, PRs, Deployment, Monitoring, ...

CONVERGE: "/build Scope ist: Planning + Gate 3 + Impl + Final Validation + PR"
  - Out of Scope: Deployment, Monitoring, Slack-Notifications
```

---

## Pattern 7: Multi-Gate Pipeline Pattern

**Quelle:** Eigenes Pattern
**Kategorie:** Quality Assurance
**Verwendet in:**
- `.claude/commands/planner.md` -- Gate 0 (Discovery+Wireframe), Gate 1 (Architecture), Gate 2 (pro Slice), Gate 3 (Integration Map)
- `.claude/commands/build.md` -- Gate 2 (implizit via slice-plan-coordinator), Gate 3 (integration-map)

**Problem:** Ein einzelner Validierungsschritt am Ende ist zu spaet. Fehler in der Architektur oder Slice-Specs werden erst bei der Implementierung entdeckt und sind dann teuer zu korrigieren.

**Loesung:** Sequenzielle, aufeinander aufbauende Qualitaets-Gates (0-3). Jedes Gate prueft einen anderen Aspekt. Bei Gate-Failure gibt es einen Fix-Loop (max 9 Retries). Erst wenn alle Gates bestanden sind, beginnt die Implementierung.

**Konsequenzen:**
- Pro: Fehler werden fruehzeitig entdeckt und korrigiert
- Pro: Jedes Gate hat einen klar definierten Pruefbereich
- Con: Mehr Vorlaufzeit vor der Implementierung

**Implementierungshinweise:**
- Gate 0: Discovery <-> Wireframe Konsistenz
- Gate 1: Architecture Compliance (technische Korrektheit)
- Gate 2: Pro Slice - Template + Integration Contract + Code Examples
- Gate 3: Integration Map (alle Slice-Outputs konsistent verknuepft?)

**Beispiel:**
```
Gate 0: Discovery & Wireframe Compliance  -> APPROVED
Gate 1: Architecture Compliance           -> APPROVED
Gate 2: Slice N Compliance (pro Slice)    -> APPROVED
Gate 3: Integration Map                   -> VERDICT: READY FOR ORCHESTRATION
Implementierung beginnt
```

---

## Pattern 8: Slice Architecture Pattern

**Quelle:** Eigenes Pattern
**Kategorie:** Architecture
**Verwendet in:**
- Alle Feature-Specs unter `specs/` -- Feature wird in testbare Slices zerlegt
- `.claude/commands/planner.md` -- Erstellt Slice-Files pro Slice
- `.claude/commands/build.md` -- Iteriert ueber Slices sequenziell

**Problem:** Features sind oft zu gross um sie in einem einzigen Schritt zu implementieren. Grosse Batches haben hohe Fehlerwahrscheinlichkeit und sind schwer zu debuggen.

**Loesung:** Jedes Feature wird in kleine, testbare Slices zerlegt. Jeder Slice hat klare Deliverables, Acceptance Criteria und Integration Contracts. Slices koennen abhaengig voneinander sein (Dependency-Graph).

**Konsequenzen:**
- Pro: Jeder Slice ist isoliert testbar
- Pro: Fehler sind einem Slice zuzuordnen
- Con: Slice-Grenzen muessen sorgfaeltig definiert werden

**Implementierungshinweise:**
- Jeder Slice hat DELIVERABLES_START/END Marker
- Jeder Slice hat GIVEN/WHEN/THEN Acceptance Criteria
- Jeder Slice hat Integration Contract (Requires From / Provides To)
- Slice-Dependencies bestimmen die Implementierungs-Reihenfolge (Waves)

**Beispiel:**
```
Feature: User Authentication
  Slice 1: Datenbank-Schema (keine Dependencies)
  Slice 2: Backend-API (abhaengig von Slice 1)
  Slice 3: Frontend-Login-Form (abhaengig von Slice 2)
  Slice 4: JWT-Middleware (abhaengig von Slice 2)
```

---

## Pattern 9: Sub-Agent Pipeline Pattern

**Quelle:** Eigenes Pattern
**Kategorie:** Orchestration
**Verwendet in:**
- `.claude/commands/orchestrate.md` -- Impl -> Test-Writer -> Test-Validator -> Debugger
- `.claude/agents/slice-impl-coordinator.md` -- Identische 4-Step Pipeline

**Problem:** Ein einzelner generalistischer Agent der Code schreibt, testet und debuggt, hat zu viele Verantwortlichkeiten. Context-Pollution fuehrt zu schlechten Entscheidungen in spaeten Phasen.

**Loesung:** Eine Pipeline aus 4 spezialisierten Agents: Jeder Agent hat eine klare Verantwortung. Output eines Agents ist Input des naechsten. Jeder Agent bekommt frischen Context (kombiniert mit Fresh Context Pattern).

**Konsequenzen:**
- Pro: Klare Spezialisierung, kein Context-Ueberlauf
- Pro: Jeder Agent kann unabhaengig verbessert werden
- Con: 4x Task()-Call Overhead pro Slice

**Implementierungshinweise:**
- Reihenfolge ist immer: Implementer -> Test-Writer -> Test-Validator -> Debugger
- Debugger wird nur bei Test-Failure aufgerufen
- Nach Debugger: erneuter Test-Validator-Aufruf (Re-Validate)

**Beispiel:**
```
Task(slice-implementer) -> {status: "completed", files_changed: [...], commit_hash: "abc"}
Task(test-writer)       -> {status: "completed", test_files: [...], ac_coverage: 100}
Task(test-validator)    -> {overall_status: "failed", error_output: "..."}
Task(debugger)          -> {status: "fixed", root_cause: "...", files_changed: [...]}
Task(test-validator)    -> {overall_status: "passed", stages: {...}}
```

---

## Pattern 10: JSON Output Contract Pattern

**Quelle:** [Phil Schmid Context Engineering](https://www.philschmid.de/context-engineering-part-2)
**Kategorie:** Data Flow
**Verwendet in:**
- `.claude/agents/slice-implementer.md` -- Output: `{status, files_changed, commit_hash}`
- `.claude/agents/test-writer.md` -- Output: `{status, test_files, ac_coverage}`
- `.claude/agents/test-validator.md` -- Output: `{overall_status, stages, error_output}`
- `.claude/agents/debugger.md` -- Output: `{status, root_cause, files_changed}`
- `.claude/agents/slice-plan-coordinator.md` -- Output: `{status, retries, slice_file, blocking_issues}`
- `.claude/agents/slice-impl-coordinator.md` -- Output: `{status, retries, evidence, error}`
- `.claude/commands/build.md` -- Parst alle Sub-Agent-Outputs als JSON

**Problem:** Wenn Sub-Agents ihre Ergebnisse als unstrukturierten Text zurueckgeben, muss der Orchestrator aufwendig parsen. Kleine Textunterschiede fuehren zu Parse-Fehlern.

**Loesung:** Jeder Sub-Agent gibt am Ende seiner Ausfuehrung EXAKT einen JSON-Block zurueck. Der Orchestrator sucht den LETZTEN `json` Code-Block und parst ihn. Das JSON-Schema ist pro Agent-Typ fest definiert.

**Konsequenzen:**
- Pro: Zuverlaessiges, maschinenlesbares Output-Format
- Pro: Schema-Validierung moeglich
- Con: Agent muss Disziplin halten um JSON IMMER als letzten Block zu setzen

**Implementierungshinweise:**
- "Find LAST `json` block" Pattern: Suche den letzten `json`-Code-Block in der Antwort
- Bei Parse-Failure: HARD STOP (kein stilles Weitermachen)
- JSON-Schema ist im Agent-PROMPT vorgegeben (Copy-Paste aus Agent-Definition)
- Keine optionalen Felder -- alle Felder sind immer gesetzt (null statt fehlendem Feld)

**Beispiel:**
```
# Orchestrator sucht:
json_blocks = regex_find_all(agent_output, /```json\s*\n(.*?)```/s)
last_json = json_blocks[-1]
parsed = JSON.parse(last_json)
```

---

## Pattern 11: Spec-as-Contract Pattern

**Quelle:** Eigenes Pattern
**Kategorie:** Architecture
**Verwendet in:**
- Alle Slice-Specs unter `specs/*/slices/` -- Specs sind das Interface zwischen Planning und Execution
- `.claude/agents/slice-implementer.md` -- Implementiert was in der Spec steht, nichts mehr
- `.claude/agents/test-writer.md` -- Schreibt Tests gegen die Spec-ACs, nicht gegen den Code

**Problem:** Ohne verbindliche Spec-Definition weicht die Implementierung von den Anforderungen ab. Test-Writer schreibt Tests gegen den Code statt gegen die Anforderungen.

**Loesung:** Die Slice-Spec ist das verbindliche Interface zwischen Planning (slice-plan-coordinator) und Execution (slice-impl-coordinator). Implementer und Test-Writer lesen NUR die Spec, nicht den jeweils anderen Output.

**Konsequenzen:**
- Pro: Implementierung und Tests sind entkoppelt
- Pro: Gate 2 stellt sicher dass die Spec korrekt ist bevor Implementierung beginnt
- Con: Erfordert sorgfaeltig geschriebene Specs

**Implementierungshinweise:**
- DELIVERABLES_START/END Marker sind der verbindliche Scope fuer den Implementer
- GIVEN/WHEN/THEN ACs sind der verbindliche Scope fuer den Test-Writer
- Integration Contract Section ist der verbindliche Interface-Vertrag zwischen Slices

**Beispiel:**
```
Slice-Spec:
  DELIVERABLES_START
  - backend/app/api/users.py  (Implementer liest das)
  DELIVERABLES_END

  AC-1: GIVEN ... WHEN ... THEN ... (Test-Writer liest das)
  Integration Contract: Provides createUser() (Slice 3 verlasst sich darauf)
```

---

## Pattern 12: Integration Contract Pattern

**Quelle:** Eigenes Pattern
**Kategorie:** Architecture
**Verwendet in:**
- Alle Slice-Specs unter `specs/*/slices/` -- "Requires From" / "Provides To" Sections
- `.claude/commands/planner.md` -- Gate 3 prueft Integration Contracts via integration-map
- `.claude/commands/build.md` -- Gate 3: Task(integration-map) validiert alle Contracts

**Problem:** Slices werden isoliert entwickelt. Interfaces zwischen Slices (welche Funktion exportiert Slice 2 fuer Slice 3?) werden informell oder gar nicht dokumentiert. Integrationsfehler entstehen erst bei der Implementierung.

**Loesung:** Jeder Slice dokumentiert explizit was er benoetigt ("Requires From") und was er bereitstellt ("Provides To"). Gate 3 prueft ob alle Requires-From korrekt einem Provides-To zugeordnet sind.

**Konsequenzen:**
- Pro: Integration-Probleme werden vor der Implementierung entdeckt
- Pro: Slice-Writer hat Context ueber vorherige Slices via `approved_slices_paths`
- Con: Erfordert Disziplin beim Schreiben der Contracts

**Implementierungshinweise:**
- "Requires From" listet: Slice-ID, Resource-Name, Typ, Validation-Methode
- "Provides To" listet: Resource-Name, Typ, Consumer-Slice, Interface-Definition
- Gate 3 (integration-map Agent) validiert die Konsistenz aller Contracts

**Beispiel:**
```
Slice 3 Integration Contract:
  Requires From:
    - slice-01: slice-plan-coordinator Agent
    - slice-02: slice-impl-coordinator Agent
  Provides To:
    - slice-04: /build Command (build.md) mit .build-state.json Schema
```

---

## Pattern 13: Hierarchical Delegation Pattern

**Quelle:** Eigenes Pattern (NEU in /build Command)
**Kategorie:** Orchestration
**Verwendet in:**
- `.claude/commands/build.md` -- Ebene 0 Coordinator delegiert an Ebene 1 Coordinator-Agents
- `.claude/agents/slice-plan-coordinator.md` -- Ebene 1 delegiert an Ebene 2 Worker-Agents
- `.claude/agents/slice-impl-coordinator.md` -- Ebene 1 delegiert an Ebene 2 Worker-Agents

**Problem:** Ein flaches Orchestrator-System bei dem der Coordinator alle Sub-Agent-Calls direkt ausfuehrt, akkumuliert bei 7+ Slices mit Retries 35.000-105.000 Tokens im Coordinator-Context. Session-Compacting zerstoert wichtigen State.

**Loesung:** 3-Ebenen-Hierarchie:
- **Ebene 0** (`/build` Command): Ultra-Lean Coordinator (~5.000 Tokens). Ruft nur Ebene-1-Agents auf. Bekommt nur JSON-Status (~300 Tokens pro Call).
- **Ebene 1** (slice-plan-coordinator, slice-impl-coordinator): Pro-Slice-Coordinator. Uebernimmt die Retry-Loop fuer EINEN Slice. Ruft Ebene-2-Worker-Agents auf.
- **Ebene 2** (slice-writer, slice-compliance, slice-implementer, test-writer, test-validator, debugger): Spezialisierte Worker-Agents. Fuehren die eigentliche Arbeit durch.

**Konsequenzen:**
- Pro: Coordinator-Context bleibt konstant klein (~5.000 Tokens)
- Pro: Jede Ebene hat klare Verantwortlichkeit und Scope
- Con: Mehr Komplexitaet durch zusaetzliche Abstraktionsebene

**Implementierungshinweise:**
- Ebene 0 ruft NUR Ebene-1-Agents auf, niemals Ebene-2 direkt
- Ebene 1 bekommt frischen Context per Task()-Call
- Ebene 1 gibt nur JSON (~300 Tokens) zurueck, keine langen Reports
- Ebene 2 arbeitet voellig isoliert, kennt andere Ebenen nicht

**Beispiel:**
```
/build Command (Ebene 0, ~5.000 Tokens):
  Task(slice-plan-coordinator) -> JSON {status: "approved", retries: 1}
  Task(slice-impl-coordinator) -> JSON {status: "completed", retries: 0}

slice-plan-coordinator (Ebene 1, frischer Context):
  Task(slice-writer) -> Slice-Datei erstellt
  Task(slice-compliance) -> Compliance geprueft
  RETURN JSON

slice-impl-coordinator (Ebene 1, frischer Context):
  Task(slice-implementer) -> Code geschrieben
  Task(test-writer) -> Tests geschrieben
  Task(test-validator) -> Tests validiert
  RETURN JSON
```

---

## Pattern 14: Reference Handoff Pattern

**Quelle:** [Anthropic Multi-Agent Research](https://www.anthropic.com/engineering/multi-agent-research-system)
**Kategorie:** Data Flow
**Verwendet in:**
- `.claude/commands/build.md` -- Uebergibt nur Pfade an Coordinator-Agents
- `.claude/agents/slice-plan-coordinator.md` -- Uebergibt nur Pfade an slice-writer, slice-compliance
- `.claude/agents/slice-impl-coordinator.md` -- Uebergibt nur Pfade an slice-implementer, test-writer, etc.

**Problem:** Wenn Dateiinhalte direkt in Prompts eingebettet werden ("hier ist der Inhalt von architecture.md: ..."), wird der Coordinator-Context schnell gross. Bei 5+ Slices mit grossen Specs kann der Context das Limit ueberschreiten.

**Loesung:** Sub-Agents bekommen nur Pfad-Referenzen zu den Dateien, die sie benoetigen. Der Sub-Agent liest die Dateien selbst mit Read(). Nur die Ergebnisse (JSON ~300 Tokens) fliessen zurueck zum Orchestrator.

**Konsequenzen:**
- Pro: Coordinator-Context bleibt minimal
- Pro: Sub-Agent kann die volle Datei lesen (nicht truncated)
- Con: Sub-Agent braucht Read-Zugriff auf alle referenzierten Dateien

**Implementierungshinweise:**
- Uebergib im Prompt: `slice_file: {spec_path}/slices/slice-01-name.md`
- NICHT: `slice_content: "# Slice 1\n\n## Metadata..."`
- Sub-Agent liest die Datei selbst: `Read({slice_file})`

**Beispiel:**
```
# RICHTIG: Nur Pfad uebergeben
Task(slice-implementer, prompt: "Slice-Spec: specs/feature/slices/slice-01.md")
# Sub-Agent liest die Datei selbst

# FALSCH: Inhalt einbetten
Task(slice-implementer, prompt: "Slice-Content: [gesamter 500-Zeilen Slice-Text hier]")
```

---

## Pattern 15: Incremental Progress Pattern

**Quelle:** [Anthropic Long-Running Harnesses](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents)
**Kategorie:** Orchestration
**Verwendet in:**
- `.claude/commands/planner.md` -- Ein Slice nach dem anderen, State nach jedem Slice
- `.claude/commands/orchestrate.md` -- Wave-basiert, State nach jedem Slice
- `.claude/commands/build.md` -- Sequenziell, State nach JEDEM Task()-Call

**Problem:** Wenn ein Long-Running Agent alle Slices in einem einzigen grossen Batch verarbeitet, gibt es bei Unterbrechung oder Fehler keinen sicheren Resume-Punkt. Der gesamte Build muss neu gestartet werden.

**Loesung:** Features werden sequenziell Slice fuer Slice verarbeitet. Nach jedem erfolgreichen Schritt wird der State persistiert. Bei Unterbrechung kann der Build ab dem letzten erfolgreichen Schritt fortgesetzt werden.

**Konsequenzen:**
- Pro: Jeder Schritt ist ein moeglicher Resume-Punkt
- Pro: Fehler sind einem spezifischen Slice zuordenbar
- Con: Sequenzielle Verarbeitung ist langsamer als parallele (ausser bei unabhaengigen Slices in der gleichen Wave)

**Implementierungshinweise:**
- State nach JEDEM Task()-Call schreiben (nicht nur am Ende)
- Resume-Logik prueft `plan_status` und `impl_status` pro Slice
- Bereits abgeschlossene Slices werden beim Resume uebersprungen (CONTINUE)
- Waves erlauben parallele Verarbeitung unabhaengiger Slices (innerhalb einer Wave)

**Beispiel:**
```
FOR EACH slice IN slices:
  IF state.slices[i].plan_status == "approved":
    CONTINUE  # Resume: ueberspringen

  result = Task(slice-plan-coordinator, ...)
  state.slices[i].plan_status = result.status
  state.last_updated = now()
  Write(.build-state.json, state)  # Immer sofort persistieren
```

---

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

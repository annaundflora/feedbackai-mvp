# Slice 4: Multi-Spec Support fuer /build Command

> **Slice 4 von 5** fuer `build-command`
>
> | Navigation | |
> |------------|---|
> | **Vorheriger:** | `slice-03-build-command.md` |
> | **Naechster:** | `slice-05-pattern-dokumentation.md` |

---

## Metadata (fuer Orchestrator)

| Key | Value |
|-----|-------|
| **ID** | `slice-04-multi-spec-support` |
| **Test** | `N/A (manueller Test - Command-Datei-Erweiterung)` |
| **E2E** | `false` |
| **Dependencies** | `["slice-03-build-command"]` |

---

## Test-Strategy (fuer Orchestrator Pipeline)

> **Quelle:** Auto-detected basierend auf Repo-Indikatoren. Dieser Slice erweitert eine Command-Markdown-Datei, keine ausfuehrbaren Code-Dateien.

| Key | Value |
|-----|-------|
| **Stack** | `claude-code-command` (Markdown Command Erweiterung) |
| **Test Command** | `N/A` (Command-Datei, kein ausfuehrbarer Code) |
| **Integration Command** | `N/A` |
| **Acceptance Command** | `Manuell: /build spec_path_1 spec_path_2 ausfuehren, pruefen ob beide Features sequenziell verarbeitet werden mit jeweils eigenem Branch + PR` |
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
| 4 | **Multi-Spec Support** | Ready | `slice-04-multi-spec-support.md` |
| 5 | Pattern-Dokumentation | Pending | `slice-05-pattern-dokumentation.md` |

---

## Kontext & Ziel

Der `/build` Command aus Slice 3 verarbeitet eine einzelne Spec (`/build spec_path`). Dieser Slice erweitert den Command um Multi-Spec-Support: `/build spec_path_1 spec_path_2 ...`. Mehrere Features werden sequenziell verarbeitet, jedes Feature bekommt einen eigenen Branch und PR. Bei Feature-Failure gibt es die Option zum naechsten Feature zu springen.

**Problem:** Bei groesseren Arbeitspaketen (z.B. Phase 4 mit 3 Features) muss der User `/build` dreimal manuell aufrufen. Kein uebergreifender Fortschritt sichtbar.

**Loesung:** `/build` akzeptiert mehrere spec_paths als Argumente. Ein aeusserer Loop iteriert ueber die Specs. Pro Spec wird der bestehende Single-Spec-Flow (Planning -> Gate 3 -> Implementation -> Final Validation -> PR) durchlaufen. State-File pro Spec: `{spec_path}/.build-state.json`.

---

## Technische Umsetzung

### Architektur-Kontext (aus architecture.md)

> **Quelle:** `architecture.md` -> "State-on-Disk", "Constraints" (Multi-Spec sequential), "Quality Attributes" (Multi-Feature-Support)

```
/build spec_a spec_b spec_c
  |
  +-- Outer Loop: FOR EACH spec IN specs[]
  |     |
  |     +-- spec = specs[current_spec_index]
  |     +-- Inner Flow (identisch mit Slice 3 Single-Spec):
  |     |     Input Validation -> Git Branch -> Planning -> Gate 3
  |     |     -> Implementation -> Final Validation -> PR
  |     +-- State-File: {spec}/.build-state.json (PRO SPEC)
  |     +-- Bei Failure: Option zum naechsten Spec springen
  |     |
  |     +-- current_spec_index++
  |
  +-- Output: "All {N} Features completed!"
```

### 1. Architektur-Impact

| Layer | Aenderungen |
|-------|------------|
| `.claude/commands/build.md` | Erweiterung: Multi-Spec Outer Loop, Argument-Parsing fuer mehrere Specs, Feature-Skip bei Failure |

### 2. Datenfluss

```
Input: $ARGUMENTS (spec_path_1 spec_path_2 ... spec_path_N)
  |
  v
Phase 0: Argument-Parsing
  |  Parse $ARGUMENTS -> specs[] Array
  |  IF nur 1 Argument: specs = [spec_path_1] (Rueckwaertskompatibel)
  |  IF mehrere Argumente: specs = [spec_path_1, spec_path_2, ...]
  |
  v
Phase 0.1: Alle Specs vorab validieren
  |  FOR EACH spec IN specs[]:
  |    Pruefe: {spec}/discovery.md EXISTS
  |    Pruefe: {spec}/architecture.md EXISTS
  |    IF fehlt: OUTPUT Fehler, entferne Spec aus Liste
  |  IF specs[] leer: STOP "Keine gueltige Spec gefunden"
  |
  v
Outer Loop: FOR i = 0 to specs.length - 1:
  |
  |  spec = specs[i]
  |  OUTPUT: "=== Feature {i+1}/{specs.length}: {spec} ==="
  |
  |  # State-File pro Spec pruefen
  |  state_path = {spec}/.build-state.json
  |  IF state EXISTS AND status == "completed":
  |    OUTPUT: "Feature bereits abgeschlossen. Ueberspringe."
  |    CONTINUE
  |
  |  # State initialisieren/laden (mit specs[] und current_spec_index)
  |  state.specs = specs
  |  state.current_spec_index = i
  |
  |  # Inner Flow (identisch mit Slice 3):
  |  +-- Git Branch: feat/{feature-name}
  |  +-- Planning Phase
  |  +-- Gate 3
  |  +-- Implementation Phase
  |  +-- Final Validation
  |  +-- Completion (Push + PR)
  |
  |  IF Feature FAILED:
  |    OUTPUT: "Feature {spec} fehlgeschlagen: {error}"
  |    OUTPUT: "Springe zum naechsten Feature..."
  |    CONTINUE (naechstes Feature)
  |
  |  IF Feature COMPLETED:
  |    OUTPUT: "Feature {spec} abgeschlossen! PR: #{pr_number}"
  |
  v
Output: "=== Zusammenfassung ==="
  |  "Erfolgreich: {N} von {total} Features"
  |  "Fehlgeschlagen: {M} Features"
  |  Liste aller PRs
```

### 3. State-Aenderungen: `.build-state.json`

Die bestehenden State-Felder `specs` und `current_spec_index` aus dem architecture.md Schema werden jetzt aktiv genutzt:

```json
{
  "specs": ["specs/2026-02-28-feature-a", "specs/2026-02-28-feature-b"],
  "current_spec_index": 1,
  "status": "in_progress",
  "phase": "planning",
  "current_slice_index": 0,
  "total_slices": 3,
  "slices": [],
  "approved_slices": [],
  "completed_slices": [],
  "failed_slices": [],
  "gate3_retries": 0,
  "last_action": "Feature 2/2 gestartet: specs/2026-02-28-feature-b",
  "branch_name": "feat/feature-b",
  "started_at": "2026-03-01T10:00:00Z",
  "last_updated": "2026-03-01T11:30:00Z",
  "completed_at": null,
  "error": null
}
```

**Wichtig:** Jede Spec hat ihre EIGENE `.build-state.json` unter `{spec_path}/.build-state.json`. Der Outer Loop wechselt zwischen State-Files.

### 4. Argument-Parsing

```
# $ARGUMENTS enthaelt alle Argumente nach /build
# Beispiele:
#   /build specs/feature-a                         -> specs = ["specs/feature-a"]
#   /build specs/feature-a specs/feature-b         -> specs = ["specs/feature-a", "specs/feature-b"]
#   /build specs/feature-a specs/feature-b specs/c -> specs = ["specs/feature-a", "specs/feature-b", "specs/c"]

specs = SPLIT($ARGUMENTS, " ")
# Trimme Leerzeichen, entferne leere Eintraege
specs = FILTER(specs, s -> s.length > 0)
```

### 5. Feature-Skip bei Failure

```
# Aus Discovery: "Bei Feature-Failure: Option zum naechsten Feature zu springen (optional)"
#
# Implementierung: Bei Feature-Failure NICHT HARD STOP fuer den gesamten /build Run,
# sondern nur fuer das aktuelle Feature. Springe zum naechsten Feature.
#
# State des fehlgeschlagenen Features bleibt in {spec_path}/.build-state.json
# mit status="failed" erhalten fuer spaeteres Resume.

IF feature_failed:
  failed_features.push({spec: spec, error: state.error})
  OUTPUT: "Feature {spec} fehlgeschlagen: {state.error}"
  OUTPUT: "State gespeichert in {spec}/.build-state.json fuer spaeteres Resume"
  OUTPUT: "Springe zum naechsten Feature..."
  # Kein HARD STOP - weiter mit naechstem Feature
```

### 6. Zusammenfassung am Ende

```
# Nach dem Outer Loop: Zusammenfassung ausgeben

OUTPUT: ""
OUTPUT: "=== /build Zusammenfassung ==="
OUTPUT: "Gesamt: {specs.length} Features"
OUTPUT: "Erfolgreich: {completed_features.length}"
OUTPUT: "Fehlgeschlagen: {failed_features.length}"
OUTPUT: ""

FOR EACH completed IN completed_features:
  OUTPUT: "  [OK] {completed.spec} -> PR: #{completed.pr_number}"

FOR EACH failed IN failed_features:
  OUTPUT: "  [FAIL] {failed.spec} -> {failed.error}"
  OUTPUT: "         Resume: /build {failed.spec}"

IF failed_features.length == 0:
  OUTPUT: ""
  OUTPUT: "Alle Features erfolgreich abgeschlossen!"
```

### 7. Git-Branch-Isolation

```
# Jedes Feature bekommt seinen eigenen Branch.
# Vor dem Start eines neuen Features: zurueck auf main/develop wechseln.

# Vor jedem Feature:
Bash("git checkout main")  # oder develop, je nach Projekt-Convention
Bash("git pull origin main")

# Dann wie in Slice 3:
Bash("git checkout -b feat/{feature-name}")
```

### 8. Wiederverwendete Code-Bausteine

| Pattern | Quelle | Wiederverwendung |
|---------|--------|-----------------|
| Single-Spec Flow (Planning -> Gate 3 -> Impl -> Validation -> PR) | Slice 3 `build.md` | Identischer Inner Flow, nur in Outer Loop gewrapped |
| State-on-Disk Pattern | Slice 3 `build.md` | Pro Spec eigenes State-File |
| Input-Validierung | Slice 3 `build.md` | Erweitert um Batch-Validierung aller Specs vorab |
| Resume-Logik | Slice 3 `build.md` | Pro Spec individuell (bereits completed Features werden uebersprungen) |
| HARD STOP Pattern | Slice 3 `build.md` | Nur pro Feature, nicht fuer den gesamten Multi-Spec-Run |
| `specs[]` und `current_spec_index` State-Felder | `architecture.md` State Schema | Bereits im Schema definiert, jetzt aktiv genutzt |

---

## Acceptance Criteria

1) GIVEN der /build Command wird mit zwei Spec-Pfaden aufgerufen (`/build spec_a spec_b`)
   WHEN der Command die Argumente parst
   THEN erstellt er ein `specs[]` Array mit beiden Pfaden: `["spec_a", "spec_b"]`

2) GIVEN der /build Command wird mit nur einem Spec-Pfad aufgerufen (`/build spec_a`)
   WHEN der Command die Argumente parst
   THEN erstellt er ein `specs[]` Array mit einem Eintrag: `["spec_a"]` und verhaelt sich identisch zum Single-Spec-Modus aus Slice 3 (Rueckwaertskompatibilitaet)

3) GIVEN der /build Command hat ein `specs[]` Array mit 3 Specs
   WHEN der Command die Vorab-Validierung durchfuehrt
   THEN prueft er fuer JEDE Spec ob `discovery.md` und `architecture.md` existieren und entfernt ungueltige Specs aus der Liste

4) GIVEN eine Vorab-Validierung ergibt dass spec_b keine discovery.md hat
   WHEN der Command die Validierung abschliesst
   THEN gibt er "Ueberspringe spec_b: discovery.md fehlt" aus und verarbeitet nur die verbleibenden gueltigen Specs

5) GIVEN das Feature spec_a wurde erfolgreich abgeschlossen (PR erstellt)
   WHEN der Command zum naechsten Feature spec_b wechselt
   THEN wechselt er zurueck auf den main-Branch, erstellt einen neuen Branch `feat/{feature-b-name}` und beginnt den vollstaendigen Single-Spec-Flow fuer spec_b

6) GIVEN das Feature spec_a ist fehlgeschlagen (z.B. Slice Planning failed nach 9 Retries)
   WHEN der Command den Fehler registriert
   THEN speichert er den Fehler in `{spec_a}/.build-state.json` mit status="failed", gibt eine Fehlermeldung aus und springt zum naechsten Feature spec_b (kein HARD STOP fuer den gesamten Run)

7) GIVEN alle Features sind verarbeitet (einige erfolgreich, einige fehlgeschlagen)
   WHEN der Command den Outer Loop abschliesst
   THEN gibt er eine Zusammenfassung aus: Anzahl erfolgreicher Features, Anzahl fehlgeschlagener Features, PR-Links fuer erfolgreiche Features, Resume-Hinweise fuer fehlgeschlagene Features

8) GIVEN der /build Command wird mit mehreren Specs aufgerufen und spec_a hat bereits status="completed" in `{spec_a}/.build-state.json`
   WHEN der Command den Outer Loop fuer spec_a erreicht
   THEN gibt er "Feature bereits abgeschlossen. Ueberspringe." aus und springt direkt zu spec_b

9) GIVEN das Feature spec_a wird verarbeitet
   WHEN der Command die `.build-state.json` fuer spec_a schreibt
   THEN enthaelt die State-Datei `specs: ["spec_a", "spec_b"]` und `current_spec_index: 0` (bei spec_a) bzw. `current_spec_index: 1` (bei spec_b)

10) GIVEN der /build Command wird ohne Argumente aufgerufen (`/build`)
    WHEN der Command die Argumente parst
    THEN gibt er "STOP: Mindestens ein Spec-Pfad erforderlich. Aufruf: /build {spec_path} [spec_path_2 ...]" aus und stoppt

---

## Testfaelle

### Test-Datei

**Konvention:** Manuelle Tests - Command-Datei-Erweiterung erzeugt keinen ausfuehrbaren Code.

### Manuelle Tests

1. **Single-Spec Rueckwaertskompatibilitaet:** /build mit nur einem Spec-Pfad aufrufen.
   - Erwartung: Verhaelt sich identisch zum Single-Spec-Modus aus Slice 3. `specs[]` enthaelt einen Eintrag.

2. **Multi-Spec Happy Path:** /build mit 2 gueltigen Specs aufrufen.
   - Erwartung: Feature A wird vollstaendig verarbeitet (Planning -> PR). Danach Feature B. Am Ende Zusammenfassung mit 2 PRs.

3. **Multi-Spec mit ungueltigem Spec:** /build mit 3 Specs aufrufen, wobei Spec 2 keine discovery.md hat.
   - Erwartung: Vorab-Validierung meldet "Ueberspringe spec_2: discovery.md fehlt". Spec 1 und Spec 3 werden verarbeitet.

4. **Feature-Skip bei Failure:** /build mit 2 Specs aufrufen, wobei Feature 1 in der Planning-Phase fehlschlaegt.
   - Erwartung: Feature 1 wird als "failed" markiert. Command springt zu Feature 2. Feature 2 wird normal verarbeitet. Zusammenfassung zeigt 1 erfolgreich, 1 fehlgeschlagen.

5. **Bereits abgeschlossenes Feature:** /build mit 2 Specs aufrufen, wobei Feature 1 bereits status="completed" in seiner .build-state.json hat.
   - Erwartung: Feature 1 wird uebersprungen mit Meldung "Feature bereits abgeschlossen". Feature 2 wird normal verarbeitet.

6. **Git Branch Isolation:** /build mit 2 Specs aufrufen.
   - Erwartung: Feature A laeuft auf Branch `feat/feature-a`. Vor Feature B wechselt Command zurueck auf main und erstellt `feat/feature-b`.

7. **Leerer Aufruf:** /build ohne Argumente aufrufen.
   - Erwartung: Fehlermeldung "Mindestens ein Spec-Pfad erforderlich" und STOP.

8. **Zusammenfassung:** /build mit 3 Specs aufrufen (2 erfolgreich, 1 fehlgeschlagen).
   - Erwartung: Zusammenfassung zeigt "Erfolgreich: 2", "Fehlgeschlagen: 1" mit PR-Links und Resume-Hinweis.

---

## Definition of Done

- [x] Akzeptanzkriterien sind eindeutig & vollstaendig
- [x] Rueckwaertskompatibilitaet mit Single-Spec-Modus sichergestellt
- [x] Feature-Skip bei Failure definiert (kein HARD STOP fuer gesamten Run)
- [x] Git Branch Isolation zwischen Features spezifiziert
- [x] Zusammenfassung am Ende definiert
- [x] State-Schema konsistent mit architecture.md (`specs[]`, `current_spec_index`)

---

## Integration Contract (GATE 2 PFLICHT)

### Requires From Other Slices

| Slice | Resource | Type | Validation |
|-------|----------|------|------------|
| slice-03-build-command | `/build` Command (`build.md`) | Command-Datei | Existiert mit Single-Spec-Flow (Phases 1-8) |
| slice-03-build-command | `.build-state.json` Schema | State File | Enthaelt `specs[]` und `current_spec_index` Felder (bereits im Schema definiert) |
| slice-01-slice-plan-coordinator | `slice-plan-coordinator` Agent | Agent (Ebene 1) | Unveraendert, wird pro Spec aufgerufen |
| slice-02-slice-impl-coordinator | `slice-impl-coordinator` Agent | Agent (Ebene 1) | Unveraendert, wird pro Spec aufgerufen |

### Provides To Other Slices

| Resource | Type | Consumer | Interface |
|----------|------|----------|-----------|
| Multi-Spec `/build` Command | Command-Erweiterung | End-User | `/build spec_a spec_b ...` -> sequenzielle Verarbeitung mit je eigenem Branch + PR |
| Feature-Skip-Logik | Behavioral Contract | End-User | Bei Feature-Failure wird zum naechsten Feature gesprungen statt HARD STOP |

### Integration Validation Tasks

- [ ] `/build` Command aus Slice 3 existiert und enthaelt Single-Spec-Flow
- [ ] `.build-state.json` Schema enthaelt `specs[]` und `current_spec_index` Felder
- [ ] Argument-Parsing von `$ARGUMENTS` kann mehrere Space-separierte Pfade verarbeiten
- [ ] Git-Checkout zurueck auf main zwischen Features funktioniert
- [ ] Pro Spec wird eine separate `.build-state.json` geschrieben (unter `{spec_path}/`)
- [ ] Single-Spec-Aufruf (`/build spec_a`) bleibt vollstaendig rueckwaertskompatibel

---

## Code Examples (MANDATORY - GATE 2 PFLICHT)

> **KRITISCH:** Alle Code-Beispiele in diesem Dokument sind **PFLICHT-Deliverables**.
> Der Gate 2 Compliance Agent prueft, dass jedes Code-Beispiel implementiert wird.

| Code Example | Section | Mandatory | Notes |
|--------------|---------|-----------|-------|
| Argument-Parsing Block | Phase 0 | YES | $ARGUMENTS -> specs[] Array |
| Vorab-Validierung Block | Phase 0.1 | YES | Alle Specs pruefen, ungueltige entfernen |
| Outer Loop Block | Hauptlogik | YES | FOR EACH spec mit Feature-Skip |
| Git Branch Isolation Block | Vor jedem Feature | YES | Checkout main, neuen Branch erstellen |
| Feature-Skip Block | Bei Failure | YES | CONTINUE statt HARD STOP |
| Zusammenfassung Block | Nach Outer Loop | YES | Erfolg/Fehler-Statistik, PR-Links |
| Leerer-Aufruf-Check Block | Phase 0 | YES | Fehlermeldung bei fehlendem Argument |

### Argument-Parsing

```markdown
## Phase 0: Argument-Parsing (Multi-Spec)

# $ARGUMENTS enthaelt alle Argumente nach /build
# Beispiele:
#   /build specs/feature-a                         -> specs = ["specs/feature-a"]
#   /build specs/feature-a specs/feature-b         -> specs = ["specs/feature-a", "specs/feature-b"]

specs = SPLIT($ARGUMENTS, " ")
specs = FILTER(specs, s -> s.length > 0)

IF specs.length == 0:
  OUTPUT: "STOP: Mindestens ein Spec-Pfad erforderlich."
  OUTPUT: "Aufruf: /build {spec_path} [spec_path_2 ...]"
  STOP
```

### Vorab-Validierung

```markdown
## Phase 0.1: Vorab-Validierung aller Specs

valid_specs = []
invalid_specs = []

FOR EACH spec IN specs:
  IF NOT EXISTS {spec}/discovery.md:
    OUTPUT: "Ueberspringe {spec}: discovery.md fehlt"
    invalid_specs.push({spec: spec, reason: "discovery.md fehlt"})
    CONTINUE

  IF NOT EXISTS {spec}/architecture.md:
    OUTPUT: "Ueberspringe {spec}: architecture.md fehlt"
    invalid_specs.push({spec: spec, reason: "architecture.md fehlt"})
    CONTINUE

  valid_specs.push(spec)

IF valid_specs.length == 0:
  OUTPUT: "STOP: Keine gueltige Spec gefunden. Alle Specs sind ungueltig:"
  FOR EACH inv IN invalid_specs:
    OUTPUT: "  - {inv.spec}: {inv.reason}"
  STOP

specs = valid_specs
OUTPUT: "{specs.length} gueltige Specs gefunden. Starte Verarbeitung..."
```

### Outer Loop (Multi-Spec)

```markdown
## Multi-Spec Outer Loop

completed_features = []
failed_features = []

FOR i = 0 to specs.length - 1:

  spec = specs[i]
  feature_name = last_path_segment(spec)  # z.B. "build-command"

  OUTPUT: ""
  OUTPUT: "============================================="
  OUTPUT: "=== Feature {i+1}/{specs.length}: {feature_name} ==="
  OUTPUT: "============================================="
  OUTPUT: ""

  # Pruefen ob Feature bereits abgeschlossen
  state_path = {spec}/.build-state.json
  IF EXISTS state_path:
    existing_state = Read(state_path)
    IF existing_state.status == "completed":
      OUTPUT: "Feature bereits abgeschlossen. Ueberspringe."
      completed_features.push({spec: spec, pr_number: "bereits erstellt"})
      CONTINUE

  # Git: Zurueck auf main, neuen Branch erstellen
  Bash("git checkout main")
  Bash("git pull origin main")
  branch_name = "feat/{feature_name}"
  Bash("git checkout -b {branch_name}")

  # Single-Spec Flow ausfuehren (Phases 1-8 aus Slice 3)
  # State initialisieren mit Multi-Spec Feldern:
  state.specs = specs
  state.current_spec_index = i
  # ... restliche State-Felder wie in Slice 3 ...

  # Inner Flow: Planning -> Gate 3 -> Implementation -> Final Validation -> PR
  # (identisch mit Slice 3, nur state.specs und state.current_spec_index gesetzt)

  result = execute_single_spec_flow(spec, state)

  IF result.status == "completed":
    completed_features.push({spec: spec, pr_number: result.pr_number})
    OUTPUT: "Feature {feature_name} abgeschlossen! PR: #{result.pr_number}"

  IF result.status == "failed":
    failed_features.push({spec: spec, error: result.error})
    OUTPUT: "Feature {feature_name} fehlgeschlagen: {result.error}"
    OUTPUT: "State gespeichert in {spec}/.build-state.json fuer spaeteres Resume"
    OUTPUT: "Springe zum naechsten Feature..."
    # KEIN HARD STOP - weiter mit naechstem Feature
    CONTINUE
```

### Git Branch Isolation

```markdown
## Git Branch Isolation (vor jedem Feature)

# Vor Start eines neuen Features:
# 1. Zurueck auf main wechseln (sauberer Ausgangspunkt)
# 2. Aktuellen Stand pullen
# 3. Neuen Feature-Branch erstellen

Bash("git checkout main")
IF exit_code != 0:
  OUTPUT: "WARNUNG: git checkout main fehlgeschlagen. Versuche git stash..."
  Bash("git stash")
  Bash("git checkout main")

Bash("git pull origin main")

feature_name = last_path_segment(spec)
branch_name = "feat/{feature_name}"

# Pruefen ob Branch bereits existiert (Resume-Fall)
branch_exists = Bash("git branch --list {branch_name}")
IF branch_exists:
  Bash("git checkout {branch_name}")
  OUTPUT: "Bestehender Branch {branch_name} ausgecheckt (Resume)"
ELSE:
  Bash("git checkout -b {branch_name}")
  OUTPUT: "Neuer Branch {branch_name} erstellt"
```

### Feature-Skip bei Failure

```markdown
## Feature-Skip bei Failure

# Bei Feature-Failure: NICHT den gesamten /build Run stoppen.
# Stattdessen: Fehler loggen, State speichern, zum naechsten Feature springen.

IF feature_result.status == "failed":
  # State ist bereits in {spec}/.build-state.json gespeichert (von Inner Flow)
  failed_features.push({
    spec: spec,
    error: feature_result.error,
    state_path: "{spec}/.build-state.json"
  })

  OUTPUT: ""
  OUTPUT: "--- Feature FEHLGESCHLAGEN ---"
  OUTPUT: "Feature: {feature_name}"
  OUTPUT: "Fehler: {feature_result.error}"
  OUTPUT: "State: {spec}/.build-state.json"
  OUTPUT: "Resume: /build {spec}"
  OUTPUT: "---"
  OUTPUT: ""

  # Weiter mit naechstem Feature (kein HARD STOP)
  CONTINUE
```

### Zusammenfassung

```markdown
## Zusammenfassung (nach Outer Loop)

OUTPUT: ""
OUTPUT: "============================================="
OUTPUT: "=== /build Zusammenfassung ==="
OUTPUT: "============================================="
OUTPUT: ""
OUTPUT: "Gesamt:        {specs.length} Features"
OUTPUT: "Erfolgreich:   {completed_features.length}"
OUTPUT: "Fehlgeschlagen: {failed_features.length}"
OUTPUT: ""

IF completed_features.length > 0:
  OUTPUT: "Erfolgreiche Features:"
  FOR EACH f IN completed_features:
    OUTPUT: "  [OK] {f.spec} -> PR: #{f.pr_number}"

IF failed_features.length > 0:
  OUTPUT: ""
  OUTPUT: "Fehlgeschlagene Features:"
  FOR EACH f IN failed_features:
    OUTPUT: "  [FAIL] {f.spec}"
    OUTPUT: "         Fehler: {f.error}"
    OUTPUT: "         Resume: /build {f.spec}"

OUTPUT: ""

IF failed_features.length == 0:
  OUTPUT: "Alle Features erfolgreich abgeschlossen!"
ELSE:
  OUTPUT: "Fehlgeschlagene Features koennen einzeln mit /build {spec_path} resumed werden."
```

### Leerer-Aufruf-Check

```markdown
## Leerer-Aufruf-Check

IF $ARGUMENTS == "" OR $ARGUMENTS == null:
  OUTPUT: "STOP: Mindestens ein Spec-Pfad erforderlich."
  OUTPUT: ""
  OUTPUT: "Aufruf:"
  OUTPUT: "  /build {spec_path}                    - Ein Feature"
  OUTPUT: "  /build {spec_path_1} {spec_path_2}    - Mehrere Features"
  OUTPUT: ""
  OUTPUT: "Beispiel:"
  OUTPUT: "  /build specs/2026-02-28-feature-a"
  OUTPUT: "  /build specs/2026-02-28-feature-a specs/2026-02-28-feature-b"
  STOP
```

---

## Constraints & Hinweise

**Betrifft:**
- Erweiterung der Datei `.claude/commands/build.md` (erstellt in Slice 3)
- Keine Aenderungen an Coordinator-Agents oder Worker-Agents

**Rueckwaertskompatibilitaet:**
- Single-Spec-Aufruf (`/build spec_a`) MUSS identisch zu Slice 3 funktionieren
- `specs[]` Array mit einem Element verhalt sich wie Single-Spec-Modus
- Kein Breaking Change am bestehenden Verhalten

**State-File-Isolation:**
- Jede Spec hat ihr EIGENES State-File: `{spec_path}/.build-state.json`
- Kein globales Multi-Spec State-File
- `specs[]` und `current_spec_index` im State dienen nur der Dokumentation, nicht der uebergreifenden Steuerung
- Steuerung erfolgt ueber den Outer Loop im Command selbst

**Feature-Failure-Verhalten:**
- Bei Feature-Failure wird zum naechsten Feature gesprungen (KEIN HARD STOP fuer den gesamten Run)
- Das fehlgeschlagene Feature kann spaeter einzeln mit `/build {spec_path}` resumed werden
- Grund: Discovery sagt "optional" fuer Feature-Skip bei Failure

**Abgrenzung:**
- Keine parallele Feature-Verarbeitung (sequenziell, wie in architecture.md definiert)
- Keine Feature-Dependencies (Feature B haengt nicht von Feature A ab - jedes Feature ist unabhaengig)
- Keine gemeinsamen Branches (jedes Feature bekommt eigenen Branch + PR)

---

## Deliverables (SCOPE SAFEGUARD)

**WICHTIG: Diese Liste wird automatisch vom Stop-Hook validiert. Der Agent kann nicht stoppen, wenn Dateien fehlen.**

<!-- DELIVERABLES_START -->
### Command-Datei
- [ ] `.claude/commands/build.md` -- Erweiterung des bestehenden /build Commands um Multi-Spec Support: Argument-Parsing fuer mehrere Spec-Pfade, Vorab-Validierung aller Specs, Outer Loop mit sequenzieller Feature-Verarbeitung, Git Branch Isolation zwischen Features, Feature-Skip bei Failure, Zusammenfassung am Ende

### Tests
- [ ] Manuelle Validierung: /build mit 2 Spec-Pfaden ausfuehren und pruefen ob beide Features sequenziell verarbeitet werden mit jeweils eigenem Branch und PR, Feature-Skip bei Failure funktioniert und Zusammenfassung korrekt ausgegeben wird
<!-- DELIVERABLES_END -->

**Hinweis fuer den Implementierungs-Agent:**
- Alle Dateien zwischen `<!-- DELIVERABLES_START -->` und `<!-- DELIVERABLES_END -->` sind **Pflicht**
- Der Stop-Hook prueft automatisch ob alle Dateien existieren
- Bei fehlenden Dateien wird der Agent blockiert und muss nachfragen

# Agentic Workflow Patterns für Claude Code
## Research: Autonomisierung & Skalierung auf 10h+ Quality Output

---

## 1. Dein aktueller Pain Point: Discovery ist manuell

Du beschreibst ein typisches Muster: **Discovery ist der Engpass**, danach könnte theoretisch alles automatisiert laufen. Das deckt sich mit dem, was Anthropic selbst empfiehlt – die erfolgreichsten Implementierungen nutzen einfache, zusammensetzbare Patterns statt komplexer Frameworks.

Die gute Nachricht: Für jeden Teil deines Workflows gibt es erprobte Patterns zur Autonomisierung.

---

## 2. Die 5 Kern-Patterns (Anthropic's eigene Taxonomie)

Anthropic identifiziert fünf fundamentale Patterns, die sich kombinieren lassen:

### 2.1 Prompt Chaining (Sequenziell)
Aufgabe wird in feste Schritte zerlegt, jeder LLM-Call verarbeitet den Output des vorherigen. Zwischen den Schritten können programmatische "Gates" eingefügt werden.

**Wann nutzen:** Klar trennbare Teilaufgaben, bei denen Genauigkeit wichtiger ist als Latenz.

**Für dich relevant bei:** Discovery → Plan → Implement → Verify Pipelines.

### 2.2 Routing / Klassifikation
Inputs werden klassifiziert und an spezialisierte Downstream-Prozesse weitergeleitet. Einfache Fragen → Haiku, komplexe → Opus.

**Für dich relevant bei:** Automatische Kategorisierung von Tasks (Bug-Fix vs. Feature vs. Refactor).

### 2.3 Parallelisierung & Voting
Mehrere LLM-Calls gleichzeitig, entweder für unabhängige Subtasks ("Sectioning") oder für höhere Konfidenz ("Voting").

**Für dich das wichtigste Pattern für Qualität** – siehe Abschnitt 4.

### 2.4 Orchestrator-Workers
Ein zentraler LLM zerlegt Tasks dynamisch und delegiert an Worker. Im Gegensatz zur Parallelisierung sind die Subtasks nicht vordefiniert, sondern werden zur Laufzeit bestimmt.

**Für dich relevant bei:** Große, unvorhersehbare Tasks (10h+ Pakete).

### 2.5 Evaluator-Optimizer (Self-Reflection)
Ein LLM generiert, ein anderer gibt iteratives Feedback. Loop läuft, bis Qualitätskriterien erfüllt sind.

**Für dich das wichtigste Pattern für Autonomie** – siehe Abschnitt 3.

---

## 3. Self-Reflection im Detail

### 3.1 Einfache Self-Reflection
Der Agent evaluiert seinen eigenen Output vor der Finalisierung:

```
Generate → Review eigenes Ergebnis → Fehler/Lücken identifizieren → Verbessern → Wiederholen
```

**Drei bewährte Feedback-Typen (Anthropic):**

1. **Rules-based Feedback:** Linting, Type-Checking, Schema-Validierung. TypeScript generieren statt JavaScript, weil das zusätzliche Feedback-Layer liefert.
2. **Contextual Validation:** Z.B. prüfen ob eine generierte E-Mail-Adresse valide ist, ob der User schon mal mit dem Empfänger kommuniziert hat.
3. **Visual Feedback:** Screenshots von gerendertem HTML über Playwright MCP, verschiedene Viewport-Größen testen.

### 3.2 Evaluator-Optimizer Loop
Zwei getrennte Rollen:

```
Generator-Agent → Output → Evaluator-Agent → Feedback → Generator-Agent → ...
```

Der Evaluator hat klare Bewertungskriterien und gibt strukturiertes Feedback. Der Generator verbessert basierend auf dem Feedback. Loop endet wenn Kriterien erfüllt sind oder Max-Iterationen erreicht.

**Analogie:** Entspricht dem menschlichen iterativen Schreibprozess – Entwurf, Review, Überarbeitung.

### 3.3 Tool-gestützte Verification
Über reine LLM-Selbstreflexion hinaus:

- Code durch Unit-Tests laufen lassen
- Web-Suche für Faktencheck
- Linter/Formatter für Code-Qualität
- Browser-Automation für E2E-Tests
- SonarQube für Quality Gates (Claude Code + SonarQube MCP existiert bereits)

**Anthropic's Key Insight:** Feedback-Loops verbessern die Qualität des Endergebnisses um Faktor 2–3.

---

## 4. Voting & Consensus Patterns

### 4.1 Self-Consistency Sampling
Gleicher Prompt, gleiches Model, mehrfach mit höherer Temperature ausführen. Verschiedene Reasoning-Pfade, aber wenn die Mehrheit zum gleichen Ergebnis kommt → hohe Konfidenz.

### 4.2 Prompt Ensembles
Gleiche Frage, verschiedene Prompt-Variationen. Prüft ob die Antwort konsistent bleibt unabhängig von der Formulierung.

### 4.3 Majority Voting
3+ Agents generieren unabhängig Antworten. Die Antwort, die mindestens 2 Agents teilen, wird gewählt.

### 4.4 Judge Agent
Ein separater Agent evaluiert die Argumente und entscheidet. Der "Richter"-LLM bekommt den gesamten Transcript und wählt die überzeugendste Antwort.

### 4.5 Multi-Agent Debate
Mehrere Agents schlagen Antworten vor und kritisieren gegenseitig ihre Reasoning. Signifikante Verbesserung bei mathematischem Reasoning und Reduktion von Halluzinationen nachgewiesen.

**Praktische Umsetzung in Claude Code:**
```
# Pseudo-Workflow
Task → 3x parallele Claude-Subagents (verschiedene Approaches)
     → Judge-Agent vergleicht Ergebnisse
     → Bestes Ergebnis wird weiterverwendet
```

---

## 5. Discovery automatisieren

Discovery ist dein größter manueller Engpass. Hier sind Ansätze zur Automatisierung:

### 5.1 CLAUDE.md als akkumuliertes Wissen
Statt jedes Mal neu zu discovern: Erkenntnisse in CLAUDE.md festhalten. Claude liest hierarchisch:
- `~/.claude/CLAUDE.md` (global)
- Projekt-Root `CLAUDE.md`
- Verzeichnis-spezifische `CLAUDE.md`

**Strategie:** Nach jeder manuellen Discovery die Ergebnisse in CLAUDE.md schreiben. Über Zeit wird die Discovery immer schneller.

### 5.2 Plan Mode als automatisierte Discovery
Plan Mode (Shift+Tab) ist read-only: Claude analysiert die gesamte Codebase, stellt Fragen, erstellt einen Implementation Plan – ohne Dateien zu ändern. Der Explore-Subagent (Haiku-powered) durchsucht dabei effizient die Codebase.

**Workflow:**
```
1. Plan Mode aktivieren
2. Claude durchsucht Codebase automatisch
3. Claude erstellt Implementation Plan
4. Du reviewst/korrigierst den Plan (5 min statt 2h Discovery)
5. Claude implementiert basierend auf approvedtem Plan
```

### 5.3 Automated Discovery Pipeline
Eine formalisierte Discovery als eigener Agent-Step:

```
Discovery-Agent:
  1. Lies CLAUDE.md und alle README.md
  2. Analysiere Projektstruktur (Verzeichnisse, Konfigdateien)
  3. Finde relevante Dateien für den Task (Grep, Glob)
  4. Analysiere Dependencies und Import-Chains
  5. Identifiziere bestehende Patterns und Conventions
  6. Erstelle strukturiertes Discovery-Dokument
  7. → Output: discovery.md mit Context für Implementation
```

### 5.4 Skills als wiederverwendbare Discovery-Templates
Claude Code Skills (levnikolaevich/claude-code-skills auf GitHub) bieten vorgefertigte Workflows, die den gesamten Lifecycle abdecken – von Research/Discovery über Epic Planning, Task Breakdown, Implementation, Testing bis zu Code Review und Quality Gates.

---

## 6. Skalierung auf 10h+ autonome Arbeit

### 6.1 Das Two-Agent Harness Pattern (Anthropic)
Anthropic empfiehlt für lange Sessions ein Zwei-Agenten-System:

1. **Initializer Agent:** Einmalig – erstellt `init.sh`, `claude-progress.txt`, initialen Git-Commit
2. **Coding Agent:** Iterativ – arbeitet in Sessions, liest Progress-File, macht inkrementelle Fortschritte

**Session-Initialisierung (jede Session):**
```
1. Git Logs und Progress-File lesen
2. Feature-Liste reviewen
3. Basic E2E-Tests laufen lassen
4. Erst dann neue Arbeit beginnen
```

Verhindert das häufigste Problem: "Premature victory declaration" – der Agent behauptet fertig zu sein, ist es aber nicht.

### 6.2 Feature List als Steuerungsmechanismus
JSON-basiertes Feature-Registry mit Status-Tracking:

```json
{
  "features": [
    {
      "name": "User Authentication",
      "steps": ["DB Schema", "API Endpoints", "Frontend Forms"],
      "passes": false
    }
  ]
}
```

Agent darf nur das `passes`-Feld ändern – keine Features löschen oder umbenennen. Erzwingt inkrementelles, nachvollziehbares Arbeiten.

### 6.3 Parallel Worktrees für Throughput
Git Worktrees ermöglichen parallele Claude-Sessions ohne Konflikte:

```bash
claude --worktree feature-auth    # Session 1: Authentication
claude --worktree feature-search  # Session 2: Search
claude --worktree bugfix-login    # Session 3: Login Bug
```

**Anthropic's eigener Creator läuft so:** 5 lokale Sessions + 5–10 auf der Website parallel. Jede in eigenem Worktree.

**Tools dafür:**
- **ccpm** (GitHub): Project Management mit GitHub Issues + Git Worktrees für parallele Agent-Execution
- **Parallel Code** (GitHub): GUI + automatische Worktree-Isolation + Multi-Agent-Orchestration
- **Claude Code Agent Teams** (experimentell): Ein Session als Team-Lead, koordiniert Teammates in eigenen Context Windows

### 6.4 Quality Gates als Automation Boundary
```
Code generieren → Lint → Type-Check → Unit-Tests → E2E-Tests → SonarQube Scan
     ↓ Fehler?                                                        ↓ Fehler?
     → Fix & Retry                                              → Fix & Re-Scan
```

Agents refactoren autonom bis alle Quality Gates passen. Erst wenn SonarQube keine Bugs oder Code Smells mehr findet, ist ein Feature "done".

---

## 7. Empfohlener Workflow: Discovery → Full Automation

Basierend auf der Research, hier ein konkreter Stufenplan:

### Stufe 1: Discovery semi-automatisieren (sofort umsetzbar)
- CLAUDE.md mit Projekt-Konventionen pflegen
- Plan Mode für jede neue Task nutzen
- Discovery-Ergebnisse systematisch festhalten

### Stufe 2: Self-Reflection einbauen (niedrige Komplexität)
- Jeder Output durchläuft einen Evaluator-Optimizer Loop
- Tools als Feedback: Linter, Tests, Type-Checker
- Mindestens 1 Verification-Schritt vor "Done"

### Stufe 3: Voting für kritische Entscheidungen (mittlere Komplexität)
- Architektur-Entscheidungen: 3 parallele Agents, Judge wählt
- Code-Review: Mehrere Agents reviewen unabhängig
- Besonders wertvoll bei Design-Entscheidungen wo es kein "richtig/falsch" gibt

### Stufe 4: Orchestrator-Worker für 10h+ Pakete (hohe Komplexität)
- Orchestrator zerlegt Epic in Tasks
- Workers implementieren parallel in Worktrees
- Quality Gates als automatische Checkpoints
- Progress-File als Handoff-Mechanismus zwischen Sessions

### Stufe 5: Full Autonomy Loop
```
Input: Epic/Feature Description
  ↓
Discovery Agent (automatisch, liest CLAUDE.md + Codebase)
  ↓
Planning Agent (zerlegt in Tasks, definiert Quality Criteria)
  ↓
Orchestrator (delegiert an Worker-Agents in Worktrees)
  ↓
Worker Agents (implementieren parallel, Self-Reflection Loops)
  ↓
Evaluator Agent (Voting auf kritische Entscheidungen)
  ↓
Quality Gate Agent (Tests, Lint, SonarQube)
  ↓
Merge Agent (PRs erstellen, Worktrees zusammenführen)
  ↓
Output: Fertiges, getestetes Feature mit PR
```

---

## 8. Konkrete Tools & Frameworks

| Tool | Zweck | Link |
|------|-------|------|
| Claude Code Agent Teams | Offizielle Multi-Agent-Koordination | Experimentelles Feature in Claude Code |
| ccpm | Project Management + Worktree Orchestration | github.com/automazeio/ccpm |
| Parallel Code | GUI für parallele Agents | github.com/johannesjo/parallel-code |
| ccswarm | Multi-Agent Orchestration | github.com/nwiizo/ccswarm |
| Ruflo | Agent Orchestration Platform | github.com/ruvnet/ruflo |
| Chief | Task-basierte Workflows für große Projekte | CLI Tool |
| claude-code-skills | Production-ready Skills für den ganzen Lifecycle | github.com/levnikolaevich/claude-code-skills |

---

## 9. Key Takeaways

1. **Starte einfach.** Anthropic betont: Die erfolgreichsten Implementierungen nutzen simple, zusammensetzbare Patterns – keine komplexen Frameworks.

2. **Feedback-Loops sind der größte Hebel.** Tools als Feedback (Tests, Linter) verbessern Qualität um Faktor 2–3. Das ist der einfachste Weg zu mehr Autonomie.

3. **Discovery lässt sich durch CLAUDE.md + Plan Mode um 80% reduzieren.** Akkumuliertes Wissen + automatische Codebase-Analyse ersetzen die meiste manuelle Arbeit.

4. **Voting lohnt sich vor allem für Architektur-Entscheidungen**, nicht für jede Code-Zeile. Selektiv einsetzen.

5. **Für 10h+ Pakete ist das Two-Agent Harness Pattern entscheidend:** Progress-File, Feature-Liste, und Session-Initialisierung verhindern, dass der Agent den Faden verliert.

6. **Parallel Worktrees multiplizieren den Throughput**, aber du brauchst einen Orchestrator der die Arbeit sinnvoll aufteilt.

---

*Erstellt am 28. Februar 2026. Quellen: Anthropic Research, GitHub Communities, Industrie-Analysen.*

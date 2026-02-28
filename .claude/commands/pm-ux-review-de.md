---
description: "Führt UX Expert Review manuell aus. Automatisches Versioning falls Review bereits existiert."
---

# UX Expert Review (Manuell)

Führt einen Senior UX Expert Review für bestehende Discovery + Wireframes aus.

**Input:** $ARGUMENTS (Spec-Ordner, z.B. `specs/2026-02-03-feature-name`)

---

## Phase 1: Input-Validierung

1. Prüfe ob `$ARGUMENTS` einen Spec-Pfad enthält
2. Falls kein Argument: Suche neuestes `specs/*/wireframes.md` und frage via AskUserQuestion
3. Validiere dass `discovery.md` ODER `discovery-lean.md` existiert
4. Validiere dass `wireframes.md` existiert
5. Falls nicht: STOP mit Hinweis "Discovery und Wireframes müssen existieren"

**Spec-Pfad ermitteln:** Extrahiere den Ordnerpfad aus $ARGUMENTS

---

## Phase 2: Versioning-Check (automatisch)

**Nutze Glob um existierende Reviews zu finden:**

```bash
# Suche nach existierenden Reviews
Glob: {spec_path}/checks/ux-expert-review*.md
```

**Bestimme nächste Version:**
1. Falls KEINE Reviews existieren → Version = "" (kein Suffix)
2. Falls `ux-expert-review.md` existiert ABER keine v2/v3/... → Version = "2"
3. Falls v2, v3, ... existieren → Finde höchste Nummer N → Version = N+1

**Beispiele:**
```
Existiert: nichts
→ Erstelle: ux-expert-review.md

Existiert: ux-expert-review.md
→ Erstelle: ux-expert-review-v2.md

Existiert: ux-expert-review.md, ux-expert-review-v2.md
→ Erstelle: ux-expert-review-v3.md
```

---

## Phase 3: UX Expert Review ausführen (Sub-Agent)

**Starte Review als Sub-Agent via Task Tool:**

```
Task tool:
  subagent_type: "general-purpose"
  description: "UX Expert Review v{version}"
  prompt: |
    Lies und befolge diese beiden Dateien:
    1. Agent-Definition (Rolle + Expertise): .claude/pm/agents/ux-expert-review-de.md
    2. Output-Template (Struktur + Format): .claude/pm/templates/ux-expert-review-template.md

    Führe den UX Expert Review durch für: {spec_path}

    Input:
    - {discovery_file}
    - {spec_path}/wireframes.md

    Output:
    - {report_file}
```

**Report-Dateiname:**
- `{spec_path}/checks/ux-expert-review.md` (wenn version="")
- `{spec_path}/checks/ux-expert-review-v{N}.md` (wenn version="2", "3", ...)

**Warte auf Sub-Agent Completion, dann weiter zu Phase 4.**

---

## Phase 4: Findings präsentieren

**Nach erfolgreichem Review:**

1. Lies `{spec_path}/checks/{REVIEW_FILE}`
2. Extrahiere Verdict aus Summary Section
3. Zeige Zusammenfassung:
   ```
   ✅ UX Expert Review abgeschlossen!

   Datei: {REVIEW_FILE}
   Verdict: APPROVED / CHANGES_REQUESTED

   - 🔴 X Critical
   - 🟡 Y Improvement
   - 💡 Z Suggestion
   ```
4. Extrahiere alle Findings (F-1, F-2, ...) aus "## Findings" Section
5. Präsentiere JEDES Finding via AskUserQuestion (siehe Format unten)
6. **NACH allen Findings: Mandatory PM-Review-Frage** (siehe unten)

---

## AskUserQuestion Format (Terminal-optimiert)

```json
{
  "questions": [{
    "header": "F-{N} {Severity}",
    "question": "Finding F-{N}: {Titel} ({Severity})\n\n{Problem-Text}\n\nKontext aus Discovery:\n{Discovery-Zitat}\n\nKontext aus Wireframe:\n{Wireframe-Zitat}\n\nEmpfehlung:\n{Empfehlungs-Text}\n\nAuswirkung: {Auswirkungs-Text}\n\nBetrifft: {Wireframe/Discovery/Beides}",
    "multiSelect": false,
    "options": [
      {
        "label": "Umsetzen",
        "description": "Discovery + Wireframe anpassen wie empfohlen"
      },
      {
        "label": "Merken für später",
        "description": "Im Report belassen, Tech Spec klärt Details"
      },
      {
        "label": "Ablehnen",
        "description": "Finding ignorieren - aktuelle Lösung OK"
      }
    ]
  }]
}
```

**Formatierungs-Regeln:**
- KEINE Markdown `**bold**` Syntax (wird im Terminal nicht gerendert)
- Abschnitt-Header als Plaintext: "Problem:", "Kontext aus Discovery:", etc.
- Doppelte Zeilenumbrüche `\n\n` zwischen Sections
- Nur Struktur durch Whitespace

---

## Mandatory PM-Review-Frage

**NACH allen Findings präsentieren:**

```json
{
  "questions": [{
    "header": "PM Review",
    "question": "Gibt es Punkte aus deinem manuellen Review, die ich berücksichtigen soll?\n\nFalls du Discovery/Wireframes selbst geprüft hast und zusätzliche Findings hast (Lücken, Inkonsistenzen, fehlende Use Cases), kannst du sie hier beschreiben.",
    "multiSelect": false,
    "options": [
      {
        "label": "Ja, ich habe Anmerkungen",
        "description": "Freitext: Beschreibe deine Findings"
      },
      {
        "label": "Nein, alles abgedeckt",
        "description": "Nur UX Expert Findings umsetzen"
      }
    ]
  }]
}
```

**Falls "Ja, ich habe Anmerkungen":**
- User gibt Freitext ein mit eigenen Findings
- Frage zurück: "Soll ich diese Punkte jetzt umsetzen oder nur zur Kenntnis nehmen?"
- Falls "Umsetzen" → Behandle wie UX Expert Finding (Read vor Edit, dann umsetzen)

---

## Phase 5: Findings umsetzen (optional)

Wenn Findings mit "Umsetzen" beantwortet werden:

1. Prüfe "Betrifft"-Flag: Wireframe/Discovery/Beides
2. **KRITISCH - Read vor Edit:**
   - Falls Discovery betroffen: Read `{spec_path}/discovery.md` + Template
   - Falls Wireframe betroffen: Read `{spec_path}/wireframes.md` + Template
3. Führe empfohlene Änderungen durch (Edit Tool mit exaktem Match)
4. Frage: "Soll ein erneutes UX Review durchgeführt werden nach den Änderungen?"

### Wenn User Recherche anfordert (via "Type something")

**Falls User schreibt:** "Prüfe Pattern im Code", "Recherchiere andere UX Patterns", "Schaue dir X an vor Entscheidung", etc.

**Workflow (KRITISCH):**

1. **Recherche durchführen:**
   - Nutze Glob/Grep/Read wie vom User angefordert
   - Sammle alle relevanten Erkenntnisse

2. **Ergebnisse präsentieren via AskUserQuestion:**
   ```json
   {
     "questions": [{
       "header": "Recherche",
       "question": "Recherche abgeschlossen:\n\n{Recherche-Ergebnisse}\n\nEmpfohlene Änderung:\n{Konkrete Änderung}\n\nSoll ich diese Änderung durchführen?",
       "multiSelect": false,
       "options": [
         {"label": "Ja, umsetzen", "description": "Änderung durchführen"},
         {"label": "Anpassen", "description": "Freitext: Gewünschte Anpassung"},
         {"label": "Ablehnen", "description": "Keine Änderung"}
       ]
     }]
   }
   ```

3. **ERST NACH Freigabe:** Änderung durchführen

**REGEL:** NIEMALS nach Recherche direkt Dokumente ändern ohne erneute Freigabe.

---

## Output

Nach erfolgreichem Durchlauf:

```
{spec_path}/
├── discovery.md         # (ggf. nach Findings aktualisiert)
├── wireframes.md        # (ggf. nach Findings aktualisiert)
└── checks/
    ├── ux-expert-review.md        # Erstes Review
    ├── ux-expert-review-v2.md     # Zweites Review (falls neu)
    └── ux-expert-review-v3.md     # Drittes Review (falls neu)
```

---

## Beispiel-Aufrufe

```bash
# Neuestes Spec finden und reviewen
/pm-ux-review-de

# Spezifisches Spec reviewen
/pm-ux-review-de specs/2026-02-03-holiday-management

# Pfad mit @ notation
/pm-ux-review-de @specs/2026-02-03-holiday-management
```

---

## Unterschied zu pm-wireframe-de

| Command | Wann nutzen |
|---------|-------------|
| `/pm-wireframe-de` | Wireframes ERSTELLEN + automatisches Review |
| `/pm-ux-review-de` | Manuelles Review NACH Änderungen oder für zweite Meinung |

---

## Nächste Schritte

Nach erfolgreichem Review:
- Falls APPROVED → `/pm-translations-de {spec_path}`
- Falls CHANGES_REQUESTED + Findings umgesetzt → Erneutes Review mit `/pm-ux-review-de`

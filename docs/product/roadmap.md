---
title: Zipmend FeedbackAI MVP -- Roadmap
created: 2026-02-12
updated: 2026-02-14
status: active
---

# Roadmap: Zipmend FeedbackAI MVP

## Aktueller Stand

**Phase:** 2 -- Widget-Shell
**Status:** als naechstes
**Letztes Check-in:** 2026-02-14

### Wo stehe ich?
Phase 0 (Fundament) und Phase 1 (Backend-Kern) sind abgeschlossen. Backend laeuft mit FastAPI + LangGraph, SSE-Streaming, Supabase-Persistenz, Summary-Generierung und Session-Timeout. Naechster Schritt: Widget-Shell aufbauen (React + Vite), danach Streaming-Bruecke.

## Aktuelle Prioritaeten

### P1: Phase 2 -- Widget-Shell (NAECHSTES)

**Warum jetzt?** Backend ist fertig und per curl testbar. Das Widget ist die naechste Voraussetzung fuer Phase 3 (Streaming-Bruecke). Ohne Widget keine Integration.

**Tasks:**
1. [ ] 2.1 Vite + React Setup, IIFE-Build (`widget.js`)
2. [ ] 2.2 Floating Button (fixed bottom-right, "Feedback geben")
3. [ ] 2.3 Chat-Panel (fixed overlay, ~400x600px, mobile fullscreen)
4. [ ] 2.4 State-Machine: Consent -> Chat -> Danke
5. [ ] 2.5 Consent-Screen (Intro-Text + "Los geht's"-Button)
6. [ ] 2.6 Danke-Screen (statisch)
7. [ ] 2.7 Scoped Styling (kein CSS-Leak in Host-Page)

### P2: Phase 3 -- Streaming-Bruecke (DANACH)

**Warum danach?** Braucht Backend (done) + Widget. Erfahrungsgemaess der trickigste Teil (SSE-Kompatibilitaet).

### Risiko

SSE-Kompatibilitaet FastAPI ↔ @assistant-ui/react (Phase 3). SSE-Endpoint ist bereits im Vercel AI SDK-Format gebaut.

---

## Vision

Ein Link, den ein Zipmend-Carrier anklicken kann, ein KI-Interview durchlaeuft, und Zusammenfassung + Transkript landen in Supabase.

## Erfolgskriterien

- [ ] Widget oeffnet sich sauber in der Carrier View (oder Test-Page)
- [ ] Interview fuehlt sich natuerlich an (Selbsttest bestanden)
- [ ] Keine dummen / kontextlosen Fragen
- [ ] Zusammenfassung ist in Supabase und brauchbar
- [ ] Widget funktioniert auf Mobile und Desktop
- [ ] Erster Carrier hat das Widget gesehen

---

## Phasen

### Phase 0 -- Fundament

**Status:** done (2026-02-12)
**Ziel:** Repo steht, Dependencies installierbar, Context-Dateien vorhanden.

| Task | Beschreibung |
|------|-------------|
| 0.1 | Git init, `.gitignore`, `.env.example` |
| 0.2 | Ordnerstruktur anlegen (`backend/`, `widget/`, `demo-site/`) |
| 0.3 | Backend Dependencies installieren (`requirements.txt`) |
| 0.4 | Widget Dependencies installieren (`package.json`) |
| 0.5 | Context-JSONs aus `feedbackai-app` kopieren (company, product, scenario) |
| 0.6 | Interviewer-Prompt aus `feedbackai-app` adaptieren |

**Done when:** `pip install -r requirements.txt` und `npm install` laufen durch. Context-Dateien liegen in `backend/app/context/`.

---

### Phase 1 -- Backend-Kern

**Status:** done (2026-02-14)
**Ziel:** Komplettes Interview per curl durchspielbar.
**Abhaengigkeit:** Phase 0

| Task | Beschreibung |
|------|-------------|
| 1.1 | FastAPI App-Skeleton (`main.py`, `config.py`, CORS) |
| 1.2 | LangGraph 1-Node Graph: Interviewer mit System-Prompt + History |
| 1.3 | Conditional Edge: `message_count > 10` oder Exit-Signal |
| 1.4 | End-Node: Zusammenfassung via separatem LLM-Call |
| 1.5 | MemorySaver als Checkpointer |
| 1.6 | API Endpoints: `POST /api/interview/start`, `/message`, `/end` |
| 1.7 | curl-Test: Start -> 3-4 Messages -> End -> Summary zurueck |

**Done when:** `curl`-basiertes Interview funktioniert Ende-zu-Ende mit sinnvollen Antworten.

---

### Phase 2 -- Widget-Shell

**Status:** pending
**Ziel:** Widget rendert sich, zeigt statische Screens.
**Abhaengigkeit:** Phase 0 (kann parallel zu Phase 1 starten)

| Task | Beschreibung |
|------|-------------|
| 2.1 | Vite + React Setup, IIFE-Build konfigurieren (`widget.js`) |
| 2.2 | Floating Button (fixed bottom-right, "Feedback geben") |
| 2.3 | Chat-Panel (fixed overlay, ~400x600px, mobile fullscreen) |
| 2.4 | State-Machine: Consent -> Chat -> Danke |
| 2.5 | Consent-Screen (Intro-Text + "Los geht's"-Button) |
| 2.6 | Danke-Screen (statisch) |
| 2.7 | Scoped Styling (kein CSS-Leak in Host-Page) |

**Done when:** Widget oeffnet sich per Klick, Consent -> leerer Chat -> Danke navigierbar. Kein Backend noetig.

---

### Phase 3 -- Streaming-Bruecke

**Status:** pending
**Ziel:** Widget und Backend kommunizieren, Antworten werden gestreamt.
**Abhaengigkeit:** Phase 1 + Phase 2

| Task | Beschreibung |
|------|-------------|
| 3.1 | FastAPI SSE-Endpoint im Vercel AI SDK-kompatiblen Format |
| 3.2 | `sse-starlette` Integration, LangGraph-Output -> SSE Chunks |
| 3.3 | `@assistant-ui/react` Thread mit Custom Runtime -> Backend |
| 3.4 | Streaming testen: Nachricht senden -> Antwort kommt Chunk fuer Chunk |
| 3.5 | Fallback pruefen: falls SSE-Probleme, Polling als Alternative |

**Done when:** Nachricht im Widget senden -> Antwort kommt gestreamt zurueck. Keine Verzoegerung bis komplette Antwort da ist.

**Risiko:** SSE-Format-Kompatibilitaet zwischen FastAPI und `useChat`/`@assistant-ui/react`. Erfahrungsgemaess der trickigste Teil. Budget extra Debugging-Zeit ein.

---

### Phase 4 -- E2E-Flow

**Status:** pending
**Ziel:** Kompletter Interview-Flow mit Persistenz.
**Abhaengigkeit:** Phase 3

| Task | Beschreibung |
|------|-------------|
| 4.1 | Interview-Ende im Widget erkennen (Backend-Signal -> Danke-Screen) |
| 4.2 | Supabase-Tabelle anlegen (`interviews`: id, session_id, created_at, transcript, summary, status) |
| 4.3 | DB-Insert am Interview-Ende (Transkript + Summary) |
| 4.4 | Demo-Site erstellen (`demo-site/index.html` mit Script-Tag) |
| 4.5 | Kompletter Flow testen: Consent -> 8-10 Nachrichten -> Ende -> Summary in Supabase |

**Done when:** Ein komplettes Interview laeuft durch und Transkript + Summary sind in Supabase sichtbar.

---

### Phase 5 -- Polish + Deploy

**Status:** pending
**Ziel:** Produktionsreif, Carrier kann den Link oeffnen.
**Abhaengigkeit:** Phase 4

| Task | Beschreibung |
|------|-------------|
| 5.1 | 3-4 Test-Interviews als Carrier durchspielen |
| 5.2 | Prompt iterieren basierend auf Testergebnissen |
| 5.3 | Mobile-Check (Fullscreen-Modus, Touch-Verhalten) |
| 5.4 | Deploy Backend (Railway oder Fly.io, Env-Vars) |
| 5.5 | Deploy Widget (Vercel oder CDN, Bundle hosten) |
| 5.6 | E2E live testen (deployed Widget -> deployed Backend -> Supabase) |
| 5.7 | Script-Tag in Zipmend Carrier View einbinden oder Link teilen |

**Done when:** Alle 6 Erfolgskriterien erfuellt. Ein Carrier kann den Link oeffnen und ein Interview durchlaufen.

---

## Kritischer Pfad

```
Phase 0 --> Phase 1 --> Phase 3 --> Phase 4 --> Phase 5
                  \       /
            Phase 2 ----+
```

Phase 2 (Widget-Shell) kann parallel zu Phase 1 starten. Phase 3 braucht beide.

---

## Post-MVP (nicht ausformuliert)

| Phase | Titel | Kern |
|-------|-------|------|
| 6 | Multi-Context | Dynamische Kontexte statt Hardcoding. Drei Produkte (Carrier View, Booking, Express Panel), zwei Szenarien. |
| 7 | Email-Einladungen | Token-basierte Interview-Links, gezielter Versand, Standalone Interview-Page. |
| 8 | Dashboard + Insights | Fact Extraction, LLM-Clustering, Insights pro Produkt und Cross-Product. |
| 9 | Voice | STT/TTS-Integration, Dual-Mode (Text/Voice), Audio-Streaming. |
| 10 | Session Context | Session Recordings (Clarity o.ae.) als Zusatzkontext fuer den Interviewer. |

Priorisierung: 6 → 7 → 8 → 9 → 10. Siehe `vision.md` fuer Begruendung.

---

## Erledigtes

| Datum | Was |
|-------|-----|
| 2026-02-12 | Phase 0: Repo-Struktur, Dependencies, Context-JSONs, Interviewer-Prompt |
| 2026-02-14 | Phase 1: Backend-Kern (FastAPI, LangGraph, SSE, Supabase, Summary, Timeout) -- 6 Slices |

## Naechste Roadmap-Session

**Wann:** Nach Abschluss Phase 2 (Widget-Shell navigierbar)
**Agenda:**
- Phase 3 Risiko: SSE-Kompatibilitaet Backend ↔ Widget validieren
- Phase 4 planen: E2E-Flow mit Supabase-Persistenz
- Prompt-Qualitaet bewerten (erstes echtes Interview)

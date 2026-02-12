# FeedbackAI – MVP Weekend Plan

## Ziel

Am Sonntagabend: ein Link, den ein Zipmend-Carrier anklicken kann, ein Interview durchläuft, und du hast Zusammenfassung + Transkript in Supabase.

---

## Scope: Was rein kommt

- **Chat-UI** (Next.js) – standalone Seite, clean, mobile-friendly
- **Interviewer-Agent** (LangGraph, minimal) – 1 Node: Interviewer mit Zipmend Carrier-Kontext
- **System-Prompt** – dein bestehender M0 Prompt, hardcoded für Zipmend Carrier View
- **Consent-Screen** – kurzer Intro-Text + "Los geht's"-Button vor dem Chat
- **Interview-Ende** – Agent erkennt natürliches Ende oder max. 10 User-Nachrichten → Danke-Screen
- **Post-Interview** – LLM-Zusammenfassung des Transkripts, gespeichert in Supabase
- **Deploy** – Vercel (Frontend) + ein Backend-Host (Railway/Fly.io/dein bestehender Server)

## Scope: Was NICHT rein kommt

- ~~Clustering / Insights / Dashboard~~
- ~~Safety Observer (alle drei)~~
- ~~Reviewer / Improver Self-Reflection Loop~~
- ~~Fact Extraction Pipeline~~
- ~~Embeddings / pgvector~~
- ~~Auth / Multi-User~~
- ~~Tag Manager / iframe~~
- ~~Voice~~
- ~~Dynamische UI-Components (Multiple Choice etc.)~~
- ~~Kontextpflege-UI (Company/Product Editor)~~

---

## Architektur

```
[Carrier View – Zipmend App]
       ↓
[Floating "Feedback"-Button unten rechts]
       ↓ (klick)
[Embedded Chat-Widget fährt hoch]  ←→  [FastAPI Backend]
                                              ↓
                                     [LangGraph – 1 Node]
                                     Interviewer mit System-Prompt
                                     (Zipmend Kontext hardcoded)
                                              ↓
                                     [LLM API – OpenAI/Anthropic]
                                              ↓
                                     [Response streamen an UI]
                                              ↓
                                     [Interview Ende erkannt]
                                              ↓
                                     [Zusammenfassung generieren]
                                              ↓
                                     [Supabase: Transkript + Summary speichern]
```

### Embedded Chat-Widget

Das Widget ist ein eigenständiges JS-Bundle, das per Script-Tag in jede Seite eingebunden wird:

```html
<script src="https://feedbackai-mvp.vercel.app/widget.js" data-project="zipmend-carrier"></script>
```

**Tech-Stack Widget:**
- **`@assistant-ui/react`** – fertige Chat-UI-Komponenten (Chat-Bubbles, Typing-Indicator, Auto-Scroll)
- **Vercel AI SDK (`ai` + `useChat`)** – Streaming-Hook, Message-State, Input-Handling
- **Vite** – Build zu einem einzelnen `widget.js` (IIFE Bundle)

Was es tut:
- Rendert einen Floating Button (unten rechts, "Feedback geben")
- Klick öffnet ein Chat-Panel (fixed position, ~400x600px)
- Chat-Panel enthält: Consent-Screen → Chat → Danke-Screen
- Kommuniziert direkt mit deinem FastAPI-Backend (CORS konfiguriert)
- Kein iframe – eigenes DOM-Element, eigenes Styling (scoped CSS oder Tailwind-Subset)
- Schließen/Minimieren jederzeit möglich

**Backend-Adapter für Vercel AI SDK Streaming:**
Der `useChat`-Hook erwartet ein bestimmtes Streaming-Format. Dein FastAPI-Backend braucht einen Endpoint, der im Vercel AI SDK-kompatiblen Format streamt (Server-Sent Events mit `data: {"content":"..."}` Chunks). Dafür einen dünnen Adapter in FastAPI, der die LangGraph-Antwort in das richtige SSE-Format wrapped.

## LangGraph – Minimal

```
START → interviewer → should_continue → interviewer (loop)
                                      → end_interview → END
```

Drei Nodes total:

1. **interviewer** – dein M0 System-Prompt + History → LLM-Call → Antwort
2. **should_continue** – Conditional Edge: max 10 User-Messages oder `continue_conversation=False`
3. **end_interview** – Danke-Nachricht + Flag zum Speichern

Kein Fan-Out, kein Fan-In, keine parallelen Observer, kein Reviewer.

---

## Samstag Vormittag: Backend

### S1: Neues Repo aufsetzen (30 min)

- Neues Repo, clean: `feedbackai-mvp/`
- Ordnerstruktur: `backend/` (FastAPI) + `widget/` (Vite + React)
- Backend `.env`: `OPENAI_API_KEY`, `SUPABASE_URL`, `SUPABASE_KEY`
- Backend Dependencies: `fastapi`, `langgraph`, `langchain-openai`, `supabase-py`, `uvicorn`, `sse-starlette`
- Widget Dependencies: `react`, `@assistant-ui/react`, `ai`, `@ai-sdk/react`, `vite`

### S2: LangGraph Minimal-Graph (1.5h)

- State: `messages`, `continue_conversation`, `message_count`
- Interviewer-Node: System-Prompt (hardcoded Zipmend Carrier) + messages → LLM-Call
- Conditional Edge: `message_count > 10` oder Exit-Signal → Ende
- End-Node: generiert Zusammenfassung via separatem LLM-Call
- Checkpointer: `MemorySaver` (kein Postgres-Checkpointer nötig für MVP)

### S3: FastAPI Endpoints (1h)

- `POST /api/interview/start` → erstellt Session, gibt erste Interviewer-Nachricht zurück
- `POST /api/interview/message` → nimmt User-Message, gibt Interviewer-Antwort zurück (Streaming optional, SSE nice-to-have)
- `POST /api/interview/end` → speichert Transkript + Summary in Supabase
- CORS für Frontend-Domain

### S4: Supabase Setup (30 min)

- Tabelle `interviews`: `id`, `session_id`, `created_at`, `transcript` (jsonb), `summary` (text), `status`
- Kein pgvector, keine Embeddings, kein Clustering
- Einfacher Insert am Interview-Ende

---

## Samstag Nachmittag: Frontend (Chat-Widget)

### S5: Widget-Bundle bauen (2.5h)

- Separates Verzeichnis: `widget/` (Vite + React)
- `npm install @assistant-ui/react ai @ai-sdk/react` 
- Build-Output: ein einzelnes `widget.js` (IIFE/UMD Bundle)
- **Chat-UI mit `@assistant-ui/react`:**
  - `<Thread>` Komponente als Kern (Messages, Input, Auto-Scroll out-of-the-box)
  - `<AssistantRuntimeProvider>` mit Custom Runtime, der auf deinen FastAPI-Endpoint zeigt
  - Styling anpassen: Farben, Größe, Font an Zipmend-Branding (CSS-Variablen)
- **Streaming via Vercel AI SDK:**
  - `useChat` Hook für Message-State + Streaming-Logik
  - Oder: `@assistant-ui/react` eigenen Runtime-Adapter nutzen (prüfen was einfacher ist)
- Drei Zustände wrappen: **Consent** → **Chat** (`<Thread>`) → **Danke**
- Floating Button: fixed bottom-right, klick toggled Chat-Panel
- Chat-Panel: fixed overlay (~400x600px), mobile fullscreen
- Scoped Styling (kein CSS-Leak in Host-Page)
- Config via `data-`Attribute auf dem Script-Tag (z.B. `data-project`, `data-lang`)

### S6: Backend-Streaming-Adapter (1h)

- FastAPI Endpoint `POST /api/chat` im Vercel AI SDK-kompatiblen Format
- LangGraph Interviewer-Node Antwort → SSE Stream mit `data:` Chunks
- Format: `useChat`-kompatibel (Text-Stream-Protocol oder Data-Stream-Protocol)
- Testen: `useChat({ api: "https://your-backend/api/chat" })` → Stream funktioniert
- CORS für Zipmend-Domain + localhost

### S6b: Integration in Carrier View (30 min)

- Script-Tag in Zipmend Carrier View einbinden (oder lokale Test-HTML)
- CORS im Backend für Zipmend-Domain freigeben
- Testen: Widget öffnet sich, Interview läuft, schließt sauber

---

## Sonntag Vormittag: Integration + Test

### S7: Selbsttest als Carrier (1.5h)

- Kompletten Flow durchspielen: Link öffnen → Consent → Interview → Ende
- Prüfen: Stellt der Agent sinnvolle Fragen zum Carrier-View?
- Prüfen: Folgt er den Anti-Leading-Regeln?
- Prüfen: Wird die Zusammenfassung gespeichert?
- System-Prompt iterieren basierend auf Testergebnissen

### S8: Prompt-Tuning (1h)

- Zipmend-Kontext im System-Prompt verfeinern
- Opening-Message testen: klingt sie natürlich für einen Carrier?
- Nachfrage-Qualität prüfen: geht der Agent tief genug?
- Edge Cases: Was passiert bei Ein-Wort-Antworten? Bei Off-Topic?

### S9: Deploy (1h)

- Widget-Bundle auf Vercel (oder CDN) hosten → `https://feedbackai-mvp.vercel.app/widget.js`
- Backend auf Railway / Fly.io
- Env-Variablen setzen
- Script-Tag in eine Test-Page einbinden, End-to-End testen

---

## Sonntag Nachmittag: Ready for Carrier

### S10: In Carrier View einbauen (30 min)

- Script-Tag in Zipmend Carrier View einbinden (Staging oder Production)
- Alternativ: Über Tag Manager deployen (falls vorhanden – ein Tag, kein Aufwand)
- Testen mit einem internen User
- Ersten echten Carrier drauf aufmerksam machen

---

## System-Prompt Anpassung

Dein M0-Prompt ist gut. Für das MVP diese Änderungen:

1. **Kontext hardcoden** – `{company_context}`, `{product_context}`, `{scenario_context}` durch echten Zipmend-Text ersetzen
2. **Scenario** – Fokus auf Carrier-Erfahrung: Bidding-Prozess, Transparenz, erste Wochen als neuer Carrier
3. **Sprache** – Prompt und Interview auf Deutsch (deine Carrier sprechen Deutsch) oder Englisch, je nach Carrier-Base
4. **Interview-Länge** – 8-10 Fragen, dann natürlich abschließen

---

## Erfolgskriterium Sonntagabend

- [ ] Widget öffnet sich sauber in der Carrier View (oder Test-Page)
- [ ] Interview fühlt sich natürlich an (Selbsttest bestanden)
- [ ] Keine dummen / kontextlosen Fragen
- [ ] Zusammenfassung ist in Supabase und brauchbar
- [ ] Widget funktioniert auf Mobile und Desktop
- [ ] Erster Carrier hat das Widget gesehen

---

## Danach (nicht dieses Wochenende)

- Clustering auf LLM-Basis (nächster Sprint)
- Fact Extraction nach Atomic Research
- Insights-Dashboard
- Kontextpflege-UI
- Voice-Interviews
- Multi-Tenant / Auth
- Den ganzen LangGraph-Stack wieder hochfahren, wenn du weißt was du brauchst
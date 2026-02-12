---
title: Zipmend MVP – Migrationsstrategie
created: 2026-02-12
---

# Zipmend MVP – Migrationsstrategie

## Strategie: Clean Start + Selective Reference

Neues Repo `E:\WebDev\feedbackai-mvp\` – frisch, kein Fork, kein History-Transfer.
Code wird neu geschrieben. Aus `feedbackai-app` werden nur Inhalte (Prompts, Kontexte) referenziert.

---

## Neue Repo-Struktur

```
feedbackai-mvp/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI App, CORS, Startup
│   │   ├── config.py            # Env vars (OPENAI_API_KEY, SUPABASE_URL, etc.)
│   │   ├── api/
│   │   │   └── interview.py     # POST /start, /message, /end
│   │   ├── graph/
│   │   │   ├── interviewer.py   # LangGraph 1-Node Graph
│   │   │   └── prompt.py        # Prompt-Loading + Context-Injection
│   │   ├── context/
│   │   │   ├── company.json     # Zipmend Company Context
│   │   │   ├── product.json     # Carrier View Product Context
│   │   │   └── scenario.json    # Hardcoded Carrier-Scenario
│   │   └── db.py                # Supabase Insert (Transkript + Summary)
│   ├── requirements.txt         # Minimal: ~10 Dependencies
│   ├── .env.example
│   └── Dockerfile               # Optional, für Railway/Fly.io
├── widget/
│   ├── src/
│   │   ├── main.tsx             # Entry: Mount Widget ins DOM
│   │   ├── Widget.tsx           # Floating Button + Chat Panel
│   │   ├── Chat.tsx             # @assistant-ui/react Thread
│   │   ├── Consent.tsx          # Consent Screen
│   │   └── Thanks.tsx           # Danke Screen
│   ├── index.html               # Dev-Entry (Vite)
│   ├── vite.config.ts           # IIFE Build → widget.js
│   ├── package.json
│   └── tsconfig.json
├── demo-site/
│   ├── index.html               # Dummy-Seite (simuliert Zipmend Carrier View)
│   └── README.md                # Anleitung: Script-Tag einbinden
├── .gitignore
├── .env.example
└── README.md
```

---

## Was aus feedbackai-app referenziert wird

### Direkt kopieren + anpassen

| Datei in feedbackai-app | Ziel in feedbackai-mvp | Anpassung |
|------------------------|------------------------|-----------|
| `backend/app/orchestration/prompts/prompt_interviewer.md` | `backend/app/graph/prompt.py` (als String eingebettet) | Placeholders durch Zipmend-Kontext ersetzen |
| `backend/app/orchestration/context/company_context.json` | `backend/app/context/company.json` | Bereits Zipmend - direkt nutzbar |
| `backend/app/orchestration/context/product_context.json` | `backend/app/context/product.json` | Bereits Carrier View - direkt nutzbar |

### Als Referenz lesen (nicht kopieren)

| Datei in feedbackai-app | Wofür | Was extrahieren |
|------------------------|-------|-----------------|
| `backend/app/orchestration/interviewer/nodes/interviewer.py` | LLM-Call-Pattern | Wie der Prompt an OpenAI geht, Fallback-Handling |
| `backend/app/database/connection.py` | Supabase-Connection | SSL-Mode-Pattern für Supabase URLs |
| `backend/app/core/config.py` | Env-Var-Loading | Settings-Pattern (aber vereinfacht) |
| `backend/app/orchestration/context/scenario_pain_point_discovery.json` | Scenario-Vorlage | Struktur als Basis fuer Zipmend-Carrier-Scenario |

### Nicht anfassen

- `dashboard/` - komplett ignorieren
- `backend/app/orchestration/interviewer/graph.py` - zu komplex, Graph wird trivial neu gebaut
- `backend/app/services/` - andere Architektur
- `backend/app/repositories/` - MVP braucht kein Repository-Pattern
- Alles mit Clustering, Embeddings, pgvector, Studio, Eval

---

## Minimale Dependencies

### Backend (requirements.txt)

```
fastapi
uvicorn[standard]
langgraph
langchain-openai
langchain-core
openai
psycopg[binary]
python-dotenv
httpx
sse-starlette
```

**Nicht dabei:** pgvector, hdbscan, scikit-learn, numpy, langfuse, datasets, transformers

### Widget (package.json)

```
react
react-dom
@assistant-ui/react
ai
@ai-sdk/react
tailwindcss
vite
```

---

## Demo-Site: Script-Einbindung

```html
<!DOCTYPE html>
<html lang="de">
<head>
    <title>Zipmend Carrier View (Demo)</title>
    <style>
        /* Minimales Carrier-View-Styling als Platzhalter */
        body { font-family: sans-serif; background: #f5f5f5; padding: 2rem; }
        h1 { color: #333; }
    </style>
</head>
<body>
    <h1>Carrier View (Demo)</h1>
    <p>Dies simuliert die Zipmend Carrier View. Das Chat-Widget erscheint unten rechts.</p>

    <!-- FeedbackAI Widget -->
    <script src="http://localhost:5173/widget.js" data-project="zipmend-carrier"></script>
</body>
</html>
```

Produktions-Einbindung (bei Zipmend):
```html
<script src="https://feedbackai-mvp.vercel.app/widget.js" data-project="zipmend-carrier"></script>
```

---

## Reihenfolge am Samstag

| Schritt | Was | Dauer |
|---------|-----|-------|
| 1 | Repo init, Ordnerstruktur, .gitignore, Dependencies | 30 min |
| 2 | Context-JSONs kopieren, Prompt adaptieren | 15 min |
| 3 | LangGraph 1-Node Graph + FastAPI Endpoints | 2h |
| 4 | Supabase Table + DB Insert | 30 min |
| 5 | Widget mit Vite + React aufsetzen | 2.5h |
| 6 | SSE Streaming-Adapter (Backend ↔ Widget) | 1h |
| 7 | Demo-Site + Integration testen | 30 min |

---

*Erstellt: 2026-02-12*

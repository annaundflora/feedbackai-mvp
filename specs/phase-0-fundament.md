---
title: Phase 0 -- Fundament
status: done
---

# Phase 0: Fundament

**Ziel:** Repo-Struktur steht, Dependencies installierbar, Context-Dateien am richtigen Ort.
**Done when:** `pip install -r requirements.txt` und `npm install` laufen durch.

---

## Entscheidungen

| # | Frage | Entscheidung |
|---|-------|-------------|
| 1 | Spec-Ordner | `specs/` -- kein `.planning/` |
| 2 | Context-Dateien | Aus Root nach `backend/app/context/` verschieben |
| 3 | Scenarios | Beide uebernehmen (pain_point_discovery + satisfaction_research) |
| 4 | Prompt | Hardcoded fuer MVP. Placeholders durch Zipmend-Text ersetzen in `prompt.py` |
| 5 | LLM-Provider | OpenRouter (Primary), Interviewer: `anthropic/claude-sonnet-4.5` |
| 6 | .env | Bestehende `.env` behalten, `.env.example` als Template |

---

## Tasks

- [x] **0.1 Git init** -- `git init`, `.gitignore` (Python + Node + .env)
- [x] **0.2 Ordnerstruktur** -- `backend/app/{api,graph,context}`, `widget/src/`, `demo-site/`
- [x] **0.3 Context-Dateien verschieben** -- `company_context.json`, `product_context.json`, `scenario_*.json` nach `backend/app/context/`
- [x] **0.4 Prompt verschieben** -- `prompt_interviewer.md` nach `backend/app/graph/prompt.py` (als Python-String, Placeholders durch Zipmend-Text ersetzen)
- [x] **0.5 Backend Dependencies** -- `requirements.txt` erstellen: fastapi, uvicorn, langgraph, langchain-openai, langchain-core, python-dotenv, httpx, sse-starlette, supabase
- [x] **0.6 Widget Dependencies** -- `package.json` erstellen: react, react-dom, @assistant-ui/react, ai, @ai-sdk/react, tailwindcss, vite
- [x] **0.7 .env.example** -- Template mit allen Variablen (ohne Werte)
- [x] **0.8 Validate** -- `pip install -r requirements.txt` + `npm install` laufen ohne Fehler

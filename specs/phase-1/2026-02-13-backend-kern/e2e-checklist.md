# E2E Checklist: Backend-Kern

**Integration Map:** `integration-map.md`
**Generated:** 2026-02-13

---

## Pre-Conditions

- [x] All slices APPROVED (Gate 2) -- 6/6 approved
- [x] Architecture APPROVED (Gate 1)
- [x] Integration Map has no MISSING INPUTS -- 0 gaps

---

## Happy Path Tests

### Flow 1: Komplettes Interview (Start -> Messages -> End)

1. [ ] **Slice 01:** Server starten: `uvicorn app.main:app --reload` -- Health-Check `GET /health` gibt 200 zurueck
2. [ ] **Slice 01:** Umgebungsvariablen geladen: Settings-Instanz hat `openrouter_api_key`, `supabase_url`, `supabase_key`
3. [ ] **Slice 03:** `POST /api/interview/start` mit `{"anonymous_id": "test-user-1"}` -- SSE-Stream mit Opening-Frage + `metadata`-Event mit `session_id`
4. [ ] **Slice 02:** Opening-Frage wird via LangGraph generiert (LLM-Call via OpenRouter, System-Prompt enthalten)
5. [ ] **Slice 04:** Interview-Row in Supabase `interviews` Tabelle mit status=`active`, anonymous_id=`test-user-1`
6. [ ] **Slice 03:** `POST /api/interview/message` mit `{"session_id": "...", "message": "Das Bidding ist frustrierend"}` -- SSE-Stream mit Interviewer-Antwort
7. [ ] **Slice 02:** LangGraph History enthaelt User-Nachricht + AI-Antwort (MemorySaver)
8. [ ] **Slice 04:** `message_count` in Supabase inkrementiert auf 1
9. [ ] **Slice 03:** Zweite Message senden -- SSE-Stream kommt, `message_count` wird 2
10. [ ] **Slice 03:** `POST /api/interview/end` mit `{"session_id": "..."}` -- JSON-Response mit `summary` (String) und `message_count` (2)
11. [ ] **Slice 05:** Summary ist echte Bullet-Liste (mit "- " Zeilen), nicht Placeholder
12. [ ] **Slice 04:** Supabase-Row: status=`completed`, transcript=JSONB Array, summary=Text, completed_at gesetzt

### Flow 2: Zweite Session mit Summary-Injection

1. [ ] **Slice 05:** `POST /api/interview/start` mit `{"anonymous_id": "test-user-1"}` (gleicher User wie Flow 1)
2. [ ] **Slice 05:** Start laedt letzte 3 Summaries via `get_recent_summaries(anonymous_id, limit=3)`
3. [ ] **Slice 05:** System-Prompt enthaelt injizierte Summary aus Flow 1 (via PromptAssembler.build)
4. [ ] **Slice 02:** LangGraph-Node nutzt erweiterten System-Prompt mit Summary-Kontext
5. [ ] **Slice 03:** Message senden und End ausfuehren -- funktioniert normal mit Summary-Kontext

### Flow 3: Erster User ohne vorherige Sessions

1. [ ] **Slice 05:** `POST /api/interview/start` mit `{"anonymous_id": "brand-new-user"}`
2. [ ] **Slice 05:** `get_recent_summaries` gibt leere Liste zurueck
3. [ ] **Slice 05:** PromptAssembler.build(summaries=None) -- kein Summary-Block im Prompt
4. [ ] **Slice 03:** Interview funktioniert normal ohne Summary-Kontext

### Flow 4: Session-Timeout mit Auto-Summary

1. [ ] **Slice 03:** `POST /api/interview/start` -- Session erstellt
2. [ ] **Slice 06:** TimeoutManager.register(session_id) aufgerufen
3. [ ] **Slice 03:** `POST /api/interview/message` -- Nachricht senden
4. [ ] **Slice 06:** TimeoutManager.reset(session_id) aufgerufen (Timer neugestartet)
5. [ ] **Slice 06:** Warten bis SESSION_TIMEOUT_SECONDS (Default: 60s) abgelaufen
6. [ ] **Slice 06:** `_handle_timeout` wird automatisch aufgerufen
7. [ ] **Slice 06:** Auto-Summary via SummaryService.generate() generiert
8. [ ] **Slice 06:** Supabase-Row: status=`completed_timeout`, transcript + summary gespeichert
9. [ ] **Slice 06:** In-Memory Session-Status auf completed_timeout gesetzt

---

## Edge Cases

### Error Handling

- [ ] **Ungueltige session_id:** `POST /api/interview/message` mit `{"session_id": "nicht-existent", "message": "test"}` -- 404 "Session not found"
- [ ] **Leere Nachricht:** `POST /api/interview/message` mit `{"session_id": "...", "message": ""}` -- 400 "Message cannot be empty"
- [ ] **Session bereits beendet:** `POST /api/interview/end` zweimal hintereinander -- 409 "Session already completed"
- [ ] **Message nach End:** `POST /api/interview/message` nach erfolgreichem End -- 409 "Session already completed"
- [ ] **LLM-Fehler (OpenRouter down):** SSE-Stream sendet `error`-Event, Session bleibt `active`, Retry moeglich
- [ ] **Summary-Generierung schlaegt fehl:** End-Response mit summary=Fallback-Text, Session trotzdem `completed`
- [ ] **DB-Fehler bei Persistenz:** Session-End funktioniert (In-Memory), DB-Fehler geloggt, nicht blockierend
- [ ] **DB-Fehler bei Summary-Loading:** Start funktioniert ohne Summaries, Fehler geloggt

### State Transitions

- [ ] `idle` -> `active` (POST /start mit anonymous_id)
- [ ] `active` -> `streaming` (POST /message mit Nachricht)
- [ ] `streaming` -> `active` (SSE text-done Event empfangen)
- [ ] `streaming` -> `error` (LLM-Fehler waehrend Stream)
- [ ] `active` -> `summarizing` (POST /end)
- [ ] `active` -> `summarizing` (Timeout nach SESSION_TIMEOUT_SECONDS)
- [ ] `summarizing` -> `completed` (Summary fertig nach /end)
- [ ] `summarizing` -> `completed_timeout` (Summary fertig nach Timeout)
- [ ] `error` -> `streaming` (POST /message Retry)

### Boundary Conditions

- [ ] **Sehr lange Nachricht:** 10000-Zeichen Message -- wird korrekt verarbeitet
- [ ] **Viele Messages in einer Session:** 50+ Nachrichten -- MemorySaver haelt History, message_count korrekt
- [ ] **Leere History bei Timeout:** Session gestartet aber keine Messages -- _handle_timeout behandelt leere History gracefully
- [ ] **Parallele Sessions:** 3 gleichzeitige Sessions mit verschiedenen anonymous_ids -- isoliert, keine Interferenz
- [ ] **Timeout reset durch Message:** Timer laeuft, Message kommt kurz vor Ablauf -- Timer wird korrekt zurueckgesetzt
- [ ] **End waehrend Timeout-Countdown:** End-Request vor Timeout-Ablauf -- TimeoutManager.cancel() verhindert doppelte Completion
- [ ] **Shutdown mit aktiven Sessions:** Server-Shutdown -- cancel_all() raeumt alle Timeout-Tasks auf

### Timeout-spezifische Edge Cases

- [ ] **Summary-Fehler bei Timeout:** SummaryService.generate() wirft Exception -- summary=None, Session trotzdem completed_timeout
- [ ] **DB-Fehler bei Timeout:** complete_session() wirft Exception -- In-Memory Status trotzdem aktualisiert
- [ ] **Timeout fuer bereits completed Session:** _handle_timeout ignoriert Sessions die nicht mehr active sind
- [ ] **Timeout fuer unbekannte Session:** _handle_timeout ignoriert Sessions die nicht in _sessions sind

---

## Cross-Slice Integration Points

| # | Integration Point | Slices | How to Verify |
|---|-------------------|--------|---------------|
| 1 | Settings -> alle Services | 01 -> 02, 03, 04, 05, 06 | Start Server, Settings-Werte in Logs pruefen |
| 2 | InterviewGraph in InterviewService | 02 -> 03 | POST /message -> SSE-Stream mit LLM-Antwort |
| 3 | InterviewService + Repository | 03 -> 04 | POST /end -> Row in Supabase pruefen |
| 4 | Repository.get_recent_summaries in start() | 04 -> 05 | Zweites Interview starten -> Prompt mit Summaries pruefen |
| 5 | SummaryService.generate in end() | 05 -> 03/04 | POST /end -> echte Summary in Response + DB |
| 6 | TimeoutManager in InterviewService | 06 -> 03 | Session starten, warten, DB-Eintrag pruefen |
| 7 | _handle_timeout -> SummaryService + Repository | 06 -> 05 + 04 | Timeout abwarten -> Summary + DB-Eintrag pruefen |
| 8 | PromptAssembler.build(summaries) in Graph | 02 -> 05 | Start mit existierenden Summaries -> LLM erhaelt Kontext |
| 9 | Lifespan Shutdown -> cancel_all() | 01 -> 06 | Server stoppen -> keine haengenden Tasks |
| 10 | DI Chain: get_interview_service() | 03 -> 04 -> 05 -> 06 | Alle Services korrekt injiziert und verfuegbar |

---

## Sign-Off

| Tester | Date | Result |
|--------|------|--------|
| -- | -- | -- |

**Notes:**
Alle Tests basieren auf curl-Interaktion (kein UI in Phase 1). SSE-Tests erfordern `curl -N` fuer Streaming.
SESSION_TIMEOUT_SECONDS sollte fuer Tests auf einen niedrigen Wert (z.B. 5s) gesetzt werden.

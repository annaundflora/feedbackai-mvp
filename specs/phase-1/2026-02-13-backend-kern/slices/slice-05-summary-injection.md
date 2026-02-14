# Slice 5: Summary-Generierung + Injection aufsetzen

> **Slice 5 von 6** fuer `Backend-Kern`
>
> | Navigation | |
> |------------|---|
> | **Vorheriger:** | `slice-04-supabase-persistenz.md` |
> | **Naechster:** | `slice-06-session-timeout.md` |

---

## Metadata (fuer Orchestrator)

| Key | Value |
|-----|-------|
| **ID** | `slice-05-summary-injection` |
| **Test** | `cd backend && python -m pytest tests/slices/backend-kern/test_slice_05_summary_injection.py -v` |
| **E2E** | `false` |
| **Dependencies** | `["slice-02-langgraph-interview", "slice-04-supabase-persistenz"]` |

---

## Slice-Uebersicht

| # | Slice | Status | Datei |
|---|-------|--------|-------|
| 1 | App-Skeleton + DDD-Struktur | Done | `slice-01-app-skeleton.md` |
| 2 | LangGraph Interview-Graph | Done | `slice-02-langgraph-interview.md` |
| 3 | SSE-Streaming Endpoints | Done | `slice-03-sse-streaming.md` |
| 4 | Supabase-Persistenz | Done | `slice-04-supabase-persistenz.md` |
| 5 | Summary-Generierung + Injection | Ready | `slice-05-summary-injection.md` |
| 6 | Session-Timeout + Auto-Summary | Pending | `slice-06-session-timeout.md` |

---

## Kontext & Ziel

Bis jetzt gibt `POST /api/interview/end` einen Placeholder-Summary-String zurueck (`"Summary-Generierung noch nicht implementiert (Slice 5)"`). Ausserdem wird beim Start eines neuen Interviews kein Kontext aus vorherigen Sessions geladen -- `PromptAssembler.build()` wird in `InterviewGraph._interviewer_node()` mit `summaries=[]` aufgerufen.

Dieser Slice schliesst beide Luecken:
1. **SummaryService** (`insights/summary.py`): Separater LLM-Call der die Conversation-History in eine Bullet-Summary verwandelt
2. **Integration in InterviewService.end()**: Echte Summary statt Placeholder -- Graph-History holen, SummaryService.generate() aufrufen, Repository.complete_session() mit echtem Summary
3. **Summary-Injection in InterviewService.start()**: Letzte 3 Summaries des anonymous_id via Repository.get_recent_summaries() laden und via PromptAssembler.build() in den System-Prompt injizieren
4. **InterviewGraph._interviewer_node()**: Muss Summaries als Parameter akzeptieren koennen (statt hardcoded `summaries=[]`)

**Aktuelle Probleme:**
1. `insights/summary.py` ist ein leerer `__init__.py` Ordner -- kein SummaryService existiert
2. `InterviewService.end()` gibt Placeholder-Summary zurueck statt echte LLM-generierte Summary
3. `InterviewService.start()` laedt keine vorherigen Summaries und injiziert sie nicht in den Prompt
4. `InterviewGraph._interviewer_node()` ruft `PromptAssembler.build(summaries=[])` hardcoded auf

---

## Technische Umsetzung

### Architektur-Kontext (aus architecture.md)

> **Quelle:** `architecture.md` -> Server Logic -> Business Logic Flow + Services & Processing

```
POST /start Flow (NACH diesem Slice):
  InterviewService.start(anonymous_id)
    -> repository.get_recent_summaries(anonymous_id, limit=3)
    -> PromptAssembler.build(summaries)
    -> graph.ainvoke_with_summaries(messages=[], session_id, summaries)
    -> SSE Stream + metadata

POST /end Flow (NACH diesem Slice):
  InterviewService.end(session_id)
    -> graph.get_history(session_id)
    -> SummaryService.generate(history)
    -> repository.complete_session(session_id, transcript, summary, message_count)
    -> EndResponse(summary, message_count)
```

### 1. Architektur-Impact

| Layer | Aenderungen |
|-------|-------------|
| `backend/app/insights/summary.py` | NEU: SummaryService mit generate()-Methode (LLM-Call via OpenRouter) |
| `backend/app/interview/service.py` | MODIFY: start() laedt Summaries und injiziert sie; end() ruft SummaryService statt Placeholder |
| `backend/app/interview/graph.py` | MODIFY: Interviewer-Node akzeptiert summaries-Parameter; neue Methode fuer Summary-aware Invocation |
| `backend/app/api/dependencies.py` | MODIFY: SummaryService erstellen und an InterviewService uebergeben |

### 2. Datenfluss

```
POST /api/interview/start {"anonymous_id": "user-1"}
  |
  v
InterviewService.start(anonymous_id)
  1. session_id = uuid4()
  2. sessions[session_id] = {status: "active", ...}
  3. repository.create_session(session_id, anonymous_id)
  4. summaries = repository.get_recent_summaries(anonymous_id, limit=3)  <-- NEU
  5. graph.set_summaries(summaries)                                       <-- NEU
  6. graph.astream(messages=[], session_id) -> SSE
  // Slice 6: TimeoutManager.register(session_id)
  7. yield metadata mit session_id
  |
  v
InterviewGraph._interviewer_node(state)
  1. system_prompt = PromptAssembler.build(summaries=self._current_summaries)  <-- NEU
  2. SystemMessage(system_prompt) + State["messages"] -> LLM
  3. Return AIMessage

---

POST /api/interview/end {"session_id": "uuid"}
  |
  v
InterviewService.end(session_id)
  1. _validate_session(session_id)
  // Slice 6: TimeoutManager.cancel(session_id)
  2. history = graph.get_history(session_id)
  3. transcript = _format_transcript(history)
  4. summary = await summary_service.generate(history)          <-- NEU (statt Placeholder)
  5. repository.complete_session(session_id, transcript, summary, message_count)
  6. sessions[session_id]["status"] = "completed"
  7. Return {summary, message_count}
```

### 3. SummaryService (insights/summary.py)

> **Quelle:** `architecture.md` -> Server Logic -> SummaryService

```python
# backend/app/insights/summary.py
"""SummaryService -- Generiert Bullet-Summary aus Interview-Transkript.

Separater LLM-Call via OpenRouter. Nutzt ein eigenes Summary-Prompt-Template.
"""
import asyncio
import logging

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, AnyMessage

from app.config.settings import Settings


logger = logging.getLogger(__name__)


SUMMARY_PROMPT = """\
Du bist ein Analyst der Feedback-Interviews zusammenfasst.

Erstelle eine praegnante Bullet-Liste mit den wichtigsten Erkenntnissen aus dem folgenden Interview-Transkript. Jeder Bullet-Punkt soll ein konkretes Fact, Pain Point, Wunsch oder eine Erkenntnis des Users enthalten.

Regeln:
- Maximal 10 Bullet-Punkte
- Jeder Punkt beginnt mit "- "
- Formuliere in der dritten Person ("User findet...", "User wuenscht sich...")
- Nur Fakten und konkrete Aussagen, keine Interpretationen
- Keine Wiederholungen
- Deutsche Sprache

Transkript:
{transcript}

Zusammenfassung:
"""


class SummaryService:
    """Generiert Bullet-Summaries aus Interview-Transkripten.

    Nutzt einen separaten LLM-Call via OpenRouter.
    Kann dasselbe oder ein anderes Modell als der Interviewer verwenden.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._llm = ChatOpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=settings.openrouter_api_key,
            model=settings.interviewer_llm,
            temperature=0.3,
            max_tokens=2000,
        )

    async def generate(self, messages: list[AnyMessage]) -> str:
        """Generiert eine Bullet-Summary aus der Conversation-History.

        Args:
            messages: Liste von LangChain Message-Objekten (HumanMessage, AIMessage).

        Returns:
            Summary als Bullet-Liste String.

        Raises:
            asyncio.TimeoutError: LLM-Call dauert laenger als LLM_TIMEOUT_SECONDS.
            Exception: LLM API Fehler.
        """
        transcript_text = self._format_messages_for_summary(messages)

        if not transcript_text.strip():
            return "- Keine Inhalte im Interview"

        prompt = SUMMARY_PROMPT.format(transcript=transcript_text)

        response = await asyncio.wait_for(
            self._llm.ainvoke([
                SystemMessage(content="Du bist ein praeziser Analyst."),
                HumanMessage(content=prompt),
            ]),
            timeout=self._settings.llm_timeout_seconds,
        )

        return response.content.strip()

    @staticmethod
    def _format_messages_for_summary(messages: list[AnyMessage]) -> str:
        """Formatiert LangChain Messages als lesbaren Transkript-Text.

        Args:
            messages: Liste von LangChain Message-Objekten.

        Returns:
            Formatierter Transkript-String.
        """
        lines = []
        for msg in messages:
            if hasattr(msg, "content") and msg.content:
                role = "Interviewer" if msg.type == "ai" else "User"
                lines.append(f"{role}: {msg.content}")
        return "\n\n".join(lines)
```

### 4. InterviewGraph Erweiterung (graph.py)

> **Quelle:** `architecture.md` -> Server Logic -> InterviewGraph + PromptAssembler

Die bestehende `InterviewGraph` aus Slice 2 wird erweitert:
- Neues Attribut `_current_summaries: list[str]` das vor einem Graph-Aufruf gesetzt werden kann
- `_interviewer_node()` nutzt `self._current_summaries` statt hardcoded `summaries=[]`
- Neue Methode `set_summaries()` zum Setzen der Summaries vor einem Aufruf

```python
# backend/app/interview/graph.py
# MODIFY: Bestehende Klasse erweitern

# Im __init__:
    self._current_summaries: list[str] = []

# Neue Methode:
    def set_summaries(self, summaries: list[str]) -> None:
        """Setzt die Summaries fuer den naechsten Graph-Aufruf.

        Wird von InterviewService.start() aufgerufen BEVOR der Graph
        invoked wird. Die Summaries werden dann in _interviewer_node()
        an PromptAssembler.build() weitergegeben.

        Args:
            summaries: Liste von Summary-Strings aus vorherigen Sessions.
        """
        self._current_summaries = summaries or []

# In _interviewer_node() AENDERN:
    async def _interviewer_node(self, state: InterviewState) -> dict:
        system_prompt = PromptAssembler.build(summaries=self._current_summaries)
        messages = [SystemMessage(content=system_prompt)] + state["messages"]

        response = await asyncio.wait_for(
            self._llm.ainvoke(messages),
            timeout=self._settings.llm_timeout_seconds,
        )

        return {"messages": [response]}
```

### 5. InterviewService Erweiterung (service.py)

> **Quelle:** `architecture.md` -> Server Logic -> Business Logic Flow

Die bestehende `InterviewService` aus Slice 4 wird erweitert:
- Constructor akzeptiert zusaetzlich einen `SummaryService`
- `start()` laedt vorherige Summaries und setzt sie auf dem Graph
- `end()` ruft `SummaryService.generate()` statt Placeholder

```python
# backend/app/interview/service.py
# MODIFY: Bestehende Klasse erweitern

# Neuer Import:
from app.insights.summary import SummaryService

# Constructor erweitern:
    def __init__(
        self,
        graph: InterviewGraph,
        repository: InterviewRepository | None = None,
        summary_service: SummaryService | None = None,
    ) -> None:
        self._graph = graph
        self._repository = repository
        self._summary_service = summary_service
        self._sessions: dict[str, dict] = {}

# In start() nach repository.create_session() EINFUEGEN:
        # Vorherige Summaries laden und in Prompt injizieren
        summaries: list[str] = []
        if self._repository:
            try:
                summaries = await self._repository.get_recent_summaries(
                    anonymous_id, limit=3
                )
            except Exception as e:
                logger.error(f"DB get_recent_summaries failed for {anonymous_id}: {e}")

        self._graph.set_summaries(summaries)

# In end() Placeholder-Summary ERSETZEN durch:
        # Echte Summary generieren
        summary = "Keine Summary verfuegbar"
        if self._summary_service:
            try:
                summary = await self._summary_service.generate(history)
            except Exception as e:
                logger.error(f"Summary generation failed for {session_id}: {e}")
                summary = "Summary-Generierung fehlgeschlagen"

        # AENDERN: summary statt placeholder_summary verwenden
        if self._repository:
            try:
                await self._repository.complete_session(
                    session_id=session_id,
                    transcript=transcript,
                    summary=summary,
                    message_count=message_count,
                )
            except Exception as e:
                logger.error(f"DB complete_session failed for {session_id}: {e}")

        self._sessions[session_id]["status"] = "completed"

        return {
            "summary": summary,
            "message_count": message_count,
        }
```

### 6. Dependency Injection Erweiterung (dependencies.py)

```python
# backend/app/api/dependencies.py
# MODIFY: SummaryService erstellen und injizieren

# Neuer Import:
from app.insights.summary import SummaryService

# In get_interview_service() AENDERN:
def get_interview_service(request: Request) -> InterviewService:
    global _interview_service
    if _interview_service is None:
        settings: Settings = request.app.state.settings
        graph = InterviewGraph(settings=settings)
        supabase_client = get_supabase_client(settings)
        repository = InterviewRepository(
            supabase_client=supabase_client,
            settings=settings,
        )
        summary_service = SummaryService(settings=settings)
        _interview_service = InterviewService(
            graph=graph,
            repository=repository,
            summary_service=summary_service,
        )
    return _interview_service
```

### 7. Externe Services/APIs

| Service | Zweck | Integration |
|---------|-------|-------------|
| OpenRouter | LLM-Provider fuer Summary-Generierung | `insights/summary.py` via `langchain-openai` ChatOpenAI |
| Supabase | Summary-Speicherung + Summary-Loading | `interview/repository.py` via `supabase-py` Client |

**Konfiguration:**
- `OPENROUTER_API_KEY`: API-Key (Pflicht, via Settings)
- `INTERVIEWER_LLM`: Model-ID fuer Summary-LLM, Default `anthropic/claude-sonnet-4.5` (via Settings)
- `LLM_TIMEOUT_SECONDS`: Timeout fuer Summary-LLM-Call, Default `30` (via Settings)

**Error Handling:**
- `asyncio.TimeoutError`: Summary-LLM-Call dauert laenger als `LLM_TIMEOUT_SECONDS` -> wird gefangen, Fallback-Summary "Summary-Generierung fehlgeschlagen"
- LLM API-Fehler -> wird gefangen und geloggt, Fallback-Summary
- DB-Fehler beim Summary-Loading -> wird gefangen und geloggt, leere Summary-Liste (kein Injection)

### 8. Abhaengigkeiten

- Bestehend: `langchain-openai`, `langchain-core` (bereits in requirements.txt)
- Bestehend: `supabase` (bereits in requirements.txt)
- Neu: Keine neuen Dependencies noetig

### 9. Wiederverwendete Code-Bausteine

| Funktion | Datei | Rueckgabetyp | Wichtige Hinweise |
|----------|-------|-------------|-------------------|
| `PromptAssembler.build()` | `app/interview/prompt.py` | `str` | Aus Slice 2: Akzeptiert `summaries: list[str]`, injiziert sie in System-Prompt |
| `SUMMARY_INJECTION_TEMPLATE` | `app/interview/prompt.py` | `str` | Aus Slice 2: Template fuer Kontext-Injection |
| `InterviewGraph` | `app/interview/graph.py` | Klasse | Aus Slice 2: Wird um `set_summaries()` erweitert |
| `InterviewGraph.get_history()` | `app/interview/graph.py` | `list[AnyMessage]` | Aus Slice 2: Liest Conversation-History |
| `InterviewRepository.get_recent_summaries()` | `app/interview/repository.py` | `list[str]` | Aus Slice 4: Laedt letzte 3 Summaries eines Users |
| `InterviewRepository.complete_session()` | `app/interview/repository.py` | `dict` | Aus Slice 4: Speichert Transkript + Summary |
| `InterviewService._format_transcript()` | `app/interview/service.py` | `list[dict]` | Aus Slice 4: Konvertiert Messages zu JSONB |
| `Settings` | `app/config/settings.py` | `Settings` | Aus Slice 1: openrouter_api_key, interviewer_llm, llm_timeout_seconds |

---

## Integrations-Checkliste (Pflicht bei Backend-Aenderungen)

### 1. State-Integration
- [x] Kein neuer State -- InterviewState (Slice 2) bleibt unveraendert
- [x] `_current_summaries` ist transient auf dem Graph (kein State-Feld)
- [x] Rueckgabetypen: Summary-String, Summary-Liste

### 2. LangGraph-Integration
- [x] `InterviewGraph._interviewer_node()` nutzt `self._current_summaries` statt hardcoded `[]`
- [x] `set_summaries()` wird VOR `astream()` aufgerufen
- [x] `get_history()` liefert Messages fuer Summary-Generierung

### 3. LLM-Integration
- [x] SummaryService nutzt eigenen ChatOpenAI-Call (OpenRouter)
- [x] Summary-Prompt ist definiert (SUMMARY_PROMPT)
- [x] Timeout via `asyncio.wait_for(llm_timeout_seconds)`

### 4. Datenbank-Integration
- [x] `repository.get_recent_summaries()` laedt vorherige Summaries (aus Slice 4 implementiert)
- [x] `repository.complete_session()` speichert echte Summary statt Placeholder
- [x] DB-Fehler sind non-blocking

### 5. Utility-Funktionen
- [x] PromptAssembler.build() aus Slice 2 wiederverwendet
- [x] SUMMARY_INJECTION_TEMPLATE aus Slice 2 wiederverwendet
- [x] InterviewRepository aus Slice 4 wiederverwendet

### 6. Feature-Aktivierung
- [x] SummaryService wird via Dependency Injection in InterviewService injiziert
- [x] Summary-Generierung automatisch bei `POST /end`
- [x] Summary-Injection automatisch bei `POST /start` wenn vorherige Sessions existieren

### 7. Datenfluss-Vollstaendigkeit
- [x] Input Summary-Generierung: `list[AnyMessage]` (Graph-History)
- [x] Transformation: Messages -> formatted transcript text -> LLM -> Bullet-Liste String
- [x] Output: Summary-String wird in DB gespeichert und in EndResponse zurueckgegeben
- [x] Input Summary-Injection: `anonymous_id` -> DB-Query -> `list[str]` -> PromptAssembler -> System-Prompt
- [x] Datenquelle: Supabase (vorherige Summaries), LLM (neue Summary)

---

## UI Anforderungen

Keine UI in diesem Slice (Backend-only).

---

## Acceptance Criteria

1) GIVEN ein laufendes Interview mit mindestens einer User-Nachricht
   WHEN das Interview via `POST /api/interview/end` beendet wird
   THEN wird eine echte LLM-generierte Bullet-Summary (nicht der Placeholder-String) in der EndResponse zurueckgegeben

2) GIVEN ein laufendes Interview das beendet wird
   WHEN die Summary in der Supabase `interviews`-Tabelle geprueft wird
   THEN enthaelt das `summary`-Feld die LLM-generierte Bullet-Summary (nicht "Summary-Generierung noch nicht implementiert")

3) GIVEN ein User mit `anonymous_id="user-1"` hat ein vorheriges abgeschlossenes Interview mit Summary in der DB
   WHEN derselbe User ein neues Interview via `POST /api/interview/start` startet
   THEN wird die vorherige Summary in den System-Prompt injiziert (via PromptAssembler.build())

4) GIVEN ein User hat 5 vorherige abgeschlossene Interviews mit Summaries
   WHEN ein neues Interview gestartet wird
   THEN werden nur die letzten 3 Summaries (sortiert nach completed_at DESC) in den Prompt injiziert

5) GIVEN ein User hat keine vorherigen Interviews
   WHEN ein neues Interview gestartet wird
   THEN wird der System-Prompt ohne Summary-Injection-Block zurueckgebaut (wie bisher)

6) GIVEN die SummaryService.generate() Methode wird mit einer Conversation-History aufgerufen
   WHEN die Summary generiert wird
   THEN beginnen die Bullet-Punkte mit "- " und enthalten konkrete Facts/Erkenntnisse aus dem Gespraech

7) GIVEN die SummaryService.generate() Methode wird mit einer leeren Message-Liste aufgerufen
   WHEN die Summary generiert wird
   THEN wird "- Keine Inhalte im Interview" zurueckgegeben (kein LLM-Call)

8) GIVEN der LLM-Call fuer die Summary-Generierung schlaegt fehl (Timeout oder API-Error)
   WHEN InterviewService.end() aufgerufen wird
   THEN wird ein Fallback-Summary "Summary-Generierung fehlgeschlagen" verwendet und das Interview wird trotzdem als "completed" markiert

9) GIVEN der DB-Call fuer get_recent_summaries() schlaegt fehl
   WHEN InterviewService.start() aufgerufen wird
   THEN wird das Interview trotzdem gestartet mit leerem Summary-Kontext (keine Injection)

10) GIVEN der SummaryService ist korrekt konfiguriert
    WHEN `SummaryService(settings)` instanziiert wird
    THEN nutzt er OpenRouter als LLM-Provider mit temperature=0.3 und max_tokens=2000

---

## Testfaelle

**WICHTIG:** Tests muessen VOR der Implementierung definiert werden! Der Orchestrator fuehrt diese Tests automatisch nach der Slice-Implementierung aus.

### Test-Datei

**Fuer diesen Slice:** `backend/tests/slices/backend-kern/test_slice_05_summary_injection.py`

### Unit Tests (pytest)

<test_spec>
```python
# backend/tests/slices/backend-kern/test_slice_05_summary_injection.py
import pytest
import json
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from langchain_core.messages import HumanMessage, AIMessage, AIMessageChunk, SystemMessage


# -- Fixtures --

@pytest.fixture
def mock_settings():
    """Mock Settings mit Test-Werten."""
    settings = MagicMock()
    settings.openrouter_api_key = "test-key"
    settings.interviewer_llm = "test-model"
    settings.interviewer_temperature = 1.0
    settings.interviewer_max_tokens = 4000
    settings.llm_timeout_seconds = 30
    settings.db_timeout_seconds = 10
    settings.supabase_url = "https://test.supabase.co"
    settings.supabase_key = "test-supabase-key"
    return settings


@pytest.fixture
def mock_llm_summary_response():
    """Mock LLM-Antwort fuer Summary-Generierung."""
    return AIMessage(
        content="- User findet das Bidding frustrierend\n"
                "- Preise sind intransparent\n"
                "- User wuenscht sich mehr Transparenz"
    )


@pytest.fixture
def sample_history():
    """Beispiel-Conversation-History."""
    return [
        AIMessage(content="Hallo! Was beschaeftigt dich bei Zipmend?"),
        HumanMessage(content="Das Bidding ist total frustrierend"),
        AIMessage(content="Was genau findest du am Bidding frustrierend?"),
        HumanMessage(content="Die Preise sind komplett intransparent"),
        AIMessage(content="Kannst du ein konkretes Beispiel nennen?"),
        HumanMessage(content="Ja, letztens hatte ich eine Sendung und wusste nicht warum der Preis so hoch war"),
    ]


@pytest.fixture
def summary_service(mock_settings, mock_llm_summary_response):
    """SummaryService mit gemocktem LLM."""
    with patch("app.insights.summary.ChatOpenAI") as MockChatOpenAI:
        mock_llm = AsyncMock()
        mock_llm.ainvoke = AsyncMock(return_value=mock_llm_summary_response)
        MockChatOpenAI.return_value = mock_llm

        from app.insights.summary import SummaryService
        service = SummaryService(settings=mock_settings)
        service._llm = mock_llm
        return service


@pytest.fixture
def mock_graph():
    """Mock InterviewGraph mit set_summaries Methode."""
    graph = AsyncMock()
    graph._current_summaries = []

    def mock_set_summaries(summaries):
        graph._current_summaries = summaries or []

    graph.set_summaries = mock_set_summaries

    async def mock_astream(messages, session_id):
        chunks = [
            (AIMessageChunk(content="Hallo"), {"langgraph_node": "interviewer"}),
            (AIMessageChunk(content="! Wie geht es?"), {"langgraph_node": "interviewer"}),
        ]
        for chunk in chunks:
            yield chunk

    graph.astream = mock_astream
    graph.get_history.return_value = [
        HumanMessage(content="Das Bidding nervt"),
        AIMessage(content="Was genau findest du frustrierend?"),
    ]
    return graph


@pytest.fixture
def mock_repository():
    """Mock InterviewRepository."""
    repo = AsyncMock()
    repo.create_session.return_value = {"session_id": "test-session", "status": "active"}
    repo.complete_session.return_value = {"session_id": "test-session", "status": "completed"}
    repo.increment_message_count.return_value = None
    repo.get_recent_summaries.return_value = []
    return repo


@pytest.fixture
def mock_summary_service(mock_llm_summary_response):
    """Mock SummaryService."""
    service = AsyncMock()
    service.generate.return_value = (
        "- User findet das Bidding frustrierend\n"
        "- Preise sind intransparent\n"
        "- User wuenscht sich mehr Transparenz"
    )
    return service


# -- SummaryService --

class TestSummaryServiceInit:
    """AC 10: SummaryService Konfiguration."""

    def test_summary_service_uses_openrouter(self, mock_settings):
        """AC 10: SummaryService nutzt OpenRouter."""
        with patch("app.insights.summary.ChatOpenAI") as MockChatOpenAI:
            MockChatOpenAI.return_value = MagicMock()
            from app.insights.summary import SummaryService
            SummaryService(settings=mock_settings)

            MockChatOpenAI.assert_called_once()
            call_kwargs = MockChatOpenAI.call_args[1]
            assert call_kwargs["base_url"] == "https://openrouter.ai/api/v1"

    def test_summary_service_uses_low_temperature(self, mock_settings):
        """AC 10: SummaryService nutzt temperature=0.3."""
        with patch("app.insights.summary.ChatOpenAI") as MockChatOpenAI:
            MockChatOpenAI.return_value = MagicMock()
            from app.insights.summary import SummaryService
            SummaryService(settings=mock_settings)

            call_kwargs = MockChatOpenAI.call_args[1]
            assert call_kwargs["temperature"] == 0.3

    def test_summary_service_uses_max_tokens_2000(self, mock_settings):
        """AC 10: SummaryService nutzt max_tokens=2000."""
        with patch("app.insights.summary.ChatOpenAI") as MockChatOpenAI:
            MockChatOpenAI.return_value = MagicMock()
            from app.insights.summary import SummaryService
            SummaryService(settings=mock_settings)

            call_kwargs = MockChatOpenAI.call_args[1]
            assert call_kwargs["max_tokens"] == 2000


class TestSummaryServiceGenerate:
    """AC 1, 6, 7: Summary-Generierung."""

    @pytest.mark.asyncio
    async def test_generate_returns_summary_string(self, summary_service, sample_history):
        """AC 1: generate() gibt einen Summary-String zurueck."""
        result = await summary_service.generate(sample_history)
        assert isinstance(result, str)
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_generate_calls_llm(self, summary_service, sample_history):
        """generate() ruft den LLM auf."""
        await summary_service.generate(sample_history)
        summary_service._llm.ainvoke.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_empty_history_returns_fallback(self, summary_service):
        """AC 7: Leere History gibt Fallback-Summary ohne LLM-Call."""
        result = await summary_service.generate([])
        assert result == "- Keine Inhalte im Interview"
        summary_service._llm.ainvoke.assert_not_called()

    @pytest.mark.asyncio
    async def test_generate_summary_contains_bullet_points(self, summary_service, sample_history):
        """AC 6: Summary enthaelt Bullet-Punkte mit '- '."""
        result = await summary_service.generate(sample_history)
        lines = [l for l in result.split("\n") if l.strip()]
        for line in lines:
            assert line.strip().startswith("- "), f"Line does not start with '- ': {line}"


class TestSummaryServiceFormatting:
    """SummaryService._format_messages_for_summary."""

    def test_format_messages_includes_roles(self):
        """Messages werden mit Interviewer/User Rollen formatiert."""
        from app.insights.summary import SummaryService
        messages = [
            AIMessage(content="Frage?"),
            HumanMessage(content="Antwort."),
        ]
        result = SummaryService._format_messages_for_summary(messages)
        assert "Interviewer: Frage?" in result
        assert "User: Antwort." in result

    def test_format_messages_empty_list(self):
        """Leere Liste ergibt leeren String."""
        from app.insights.summary import SummaryService
        result = SummaryService._format_messages_for_summary([])
        assert result == ""

    def test_format_messages_skips_empty_content(self):
        """Messages ohne Content werden uebersprungen."""
        from app.insights.summary import SummaryService
        messages = [
            AIMessage(content=""),
            HumanMessage(content="Test"),
        ]
        result = SummaryService._format_messages_for_summary(messages)
        assert "Interviewer" not in result
        assert "User: Test" in result


class TestSummaryServiceTimeout:
    """AC 8: Summary-LLM-Timeout wird korrekt behandelt."""

    @pytest.mark.asyncio
    async def test_timeout_raises_error(self, mock_settings):
        """AC 8: TimeoutError bei langsamem LLM."""
        with patch("app.insights.summary.ChatOpenAI") as MockChatOpenAI:
            async def slow_invoke(*args, **kwargs):
                await asyncio.sleep(100)
                return AIMessage(content="Zu spaet")

            mock_llm = AsyncMock()
            mock_llm.ainvoke = slow_invoke
            MockChatOpenAI.return_value = mock_llm

            mock_settings.llm_timeout_seconds = 0.1

            from app.insights.summary import SummaryService
            service = SummaryService(settings=mock_settings)
            service._llm = mock_llm

            with pytest.raises(asyncio.TimeoutError):
                await service.generate([
                    HumanMessage(content="Test"),
                    AIMessage(content="Antwort"),
                ])


# -- InterviewGraph set_summaries --

class TestInterviewGraphSummaries:
    """InterviewGraph akzeptiert Summaries."""

    def test_graph_has_set_summaries_method(self):
        """InterviewGraph hat set_summaries() Methode."""
        with patch("app.interview.graph.ChatOpenAI"):
            with patch.dict("os.environ", {
                "OPENROUTER_API_KEY": "test",
                "SUPABASE_URL": "https://test.supabase.co",
                "SUPABASE_KEY": "test-key",
            }, clear=False):
                from app.config.settings import Settings
                from app.interview.graph import InterviewGraph
                settings = Settings()
                graph = InterviewGraph(settings=settings)
                assert hasattr(graph, "set_summaries")
                assert callable(graph.set_summaries)

    def test_set_summaries_stores_summaries(self):
        """set_summaries() speichert die Summaries."""
        with patch("app.interview.graph.ChatOpenAI"):
            with patch.dict("os.environ", {
                "OPENROUTER_API_KEY": "test",
                "SUPABASE_URL": "https://test.supabase.co",
                "SUPABASE_KEY": "test-key",
            }, clear=False):
                from app.config.settings import Settings
                from app.interview.graph import InterviewGraph
                settings = Settings()
                graph = InterviewGraph(settings=settings)
                summaries = ["Summary 1", "Summary 2"]
                graph.set_summaries(summaries)
                assert graph._current_summaries == summaries

    def test_set_summaries_with_none(self):
        """set_summaries(None) setzt leere Liste."""
        with patch("app.interview.graph.ChatOpenAI"):
            with patch.dict("os.environ", {
                "OPENROUTER_API_KEY": "test",
                "SUPABASE_URL": "https://test.supabase.co",
                "SUPABASE_KEY": "test-key",
            }, clear=False):
                from app.config.settings import Settings
                from app.interview.graph import InterviewGraph
                settings = Settings()
                graph = InterviewGraph(settings=settings)
                graph.set_summaries(None)
                assert graph._current_summaries == []

    def test_graph_has_current_summaries_attribute(self):
        """InterviewGraph hat _current_summaries Attribut."""
        with patch("app.interview.graph.ChatOpenAI"):
            with patch.dict("os.environ", {
                "OPENROUTER_API_KEY": "test",
                "SUPABASE_URL": "https://test.supabase.co",
                "SUPABASE_KEY": "test-key",
            }, clear=False):
                from app.config.settings import Settings
                from app.interview.graph import InterviewGraph
                settings = Settings()
                graph = InterviewGraph(settings=settings)
                assert hasattr(graph, "_current_summaries")
                assert graph._current_summaries == []


# -- InterviewService Summary-Integration --

class TestInterviewServiceSummaryEnd:
    """AC 1, 2, 8: InterviewService.end() nutzt SummaryService."""

    @pytest.mark.asyncio
    async def test_end_calls_summary_service(self, mock_graph, mock_repository, mock_summary_service):
        """AC 1: end() ruft SummaryService.generate() auf."""
        from app.interview.service import InterviewService
        service = InterviewService(
            graph=mock_graph,
            repository=mock_repository,
            summary_service=mock_summary_service,
        )

        # Session starten
        async for _ in service.start("test-user"):
            pass
        session_id = list(service._sessions.keys())[0]

        # Session beenden
        result = await service.end(session_id)

        mock_summary_service.generate.assert_called_once()

    @pytest.mark.asyncio
    async def test_end_returns_real_summary(self, mock_graph, mock_repository, mock_summary_service):
        """AC 1: end() gibt echte Summary zurueck (nicht Placeholder)."""
        from app.interview.service import InterviewService
        service = InterviewService(
            graph=mock_graph,
            repository=mock_repository,
            summary_service=mock_summary_service,
        )

        async for _ in service.start("test-user"):
            pass
        session_id = list(service._sessions.keys())[0]

        result = await service.end(session_id)
        assert "Bidding frustrierend" in result["summary"]
        assert "noch nicht implementiert" not in result["summary"]

    @pytest.mark.asyncio
    async def test_end_saves_real_summary_to_db(self, mock_graph, mock_repository, mock_summary_service):
        """AC 2: Echte Summary wird in DB gespeichert."""
        from app.interview.service import InterviewService
        service = InterviewService(
            graph=mock_graph,
            repository=mock_repository,
            summary_service=mock_summary_service,
        )

        async for _ in service.start("test-user"):
            pass
        session_id = list(service._sessions.keys())[0]

        await service.end(session_id)

        mock_repository.complete_session.assert_called_once()
        call_kwargs = mock_repository.complete_session.call_args[1]
        assert "Bidding frustrierend" in call_kwargs["summary"]

    @pytest.mark.asyncio
    async def test_end_handles_summary_failure(self, mock_graph, mock_repository):
        """AC 8: Summary-Fehler fuehrt zu Fallback, Interview wird trotzdem completed."""
        failing_summary_service = AsyncMock()
        failing_summary_service.generate.side_effect = Exception("LLM unavailable")

        from app.interview.service import InterviewService
        service = InterviewService(
            graph=mock_graph,
            repository=mock_repository,
            summary_service=failing_summary_service,
        )

        async for _ in service.start("test-user"):
            pass
        session_id = list(service._sessions.keys())[0]

        result = await service.end(session_id)
        assert result["summary"] == "Summary-Generierung fehlgeschlagen"
        assert service._sessions[session_id]["status"] == "completed"

    @pytest.mark.asyncio
    async def test_end_handles_timeout_failure(self, mock_graph, mock_repository):
        """AC 8: Timeout fuehrt zu Fallback-Summary."""
        timeout_summary_service = AsyncMock()
        timeout_summary_service.generate.side_effect = asyncio.TimeoutError()

        from app.interview.service import InterviewService
        service = InterviewService(
            graph=mock_graph,
            repository=mock_repository,
            summary_service=timeout_summary_service,
        )

        async for _ in service.start("test-user"):
            pass
        session_id = list(service._sessions.keys())[0]

        result = await service.end(session_id)
        assert result["summary"] == "Summary-Generierung fehlgeschlagen"
        assert service._sessions[session_id]["status"] == "completed"

    @pytest.mark.asyncio
    async def test_end_without_summary_service_uses_fallback(self, mock_graph, mock_repository):
        """Service ohne SummaryService gibt Fallback-Summary."""
        from app.interview.service import InterviewService
        service = InterviewService(
            graph=mock_graph,
            repository=mock_repository,
            summary_service=None,
        )

        async for _ in service.start("test-user"):
            pass
        session_id = list(service._sessions.keys())[0]

        result = await service.end(session_id)
        assert result["summary"] == "Keine Summary verfuegbar"


class TestInterviewServiceSummaryInjection:
    """AC 3, 4, 5, 9: InterviewService.start() injiziert Summaries."""

    @pytest.mark.asyncio
    async def test_start_loads_recent_summaries(self, mock_graph, mock_repository, mock_summary_service):
        """AC 3: start() ruft repository.get_recent_summaries() auf."""
        mock_repository.get_recent_summaries.return_value = [
            "- User findet Bidding frustrierend",
        ]

        from app.interview.service import InterviewService
        service = InterviewService(
            graph=mock_graph,
            repository=mock_repository,
            summary_service=mock_summary_service,
        )

        async for _ in service.start("test-user"):
            pass

        mock_repository.get_recent_summaries.assert_called_once_with(
            "test-user", limit=3
        )

    @pytest.mark.asyncio
    async def test_start_sets_summaries_on_graph(self, mock_graph, mock_repository, mock_summary_service):
        """AC 3: start() setzt Summaries auf dem Graph."""
        previous_summaries = [
            "- User findet Bidding frustrierend",
            "- Preise sind intransparent",
        ]
        mock_repository.get_recent_summaries.return_value = previous_summaries

        from app.interview.service import InterviewService
        service = InterviewService(
            graph=mock_graph,
            repository=mock_repository,
            summary_service=mock_summary_service,
        )

        async for _ in service.start("test-user"):
            pass

        assert mock_graph._current_summaries == previous_summaries

    @pytest.mark.asyncio
    async def test_start_no_previous_summaries(self, mock_graph, mock_repository, mock_summary_service):
        """AC 5: Ohne vorherige Summaries wird leere Liste gesetzt."""
        mock_repository.get_recent_summaries.return_value = []

        from app.interview.service import InterviewService
        service = InterviewService(
            graph=mock_graph,
            repository=mock_repository,
            summary_service=mock_summary_service,
        )

        async for _ in service.start("new-user"):
            pass

        assert mock_graph._current_summaries == []

    @pytest.mark.asyncio
    async def test_start_limits_summaries_to_3(self, mock_graph, mock_repository, mock_summary_service):
        """AC 4: get_recent_summaries wird mit limit=3 aufgerufen."""
        mock_repository.get_recent_summaries.return_value = []

        from app.interview.service import InterviewService
        service = InterviewService(
            graph=mock_graph,
            repository=mock_repository,
            summary_service=mock_summary_service,
        )

        async for _ in service.start("test-user"):
            pass

        mock_repository.get_recent_summaries.assert_called_once_with(
            "test-user", limit=3
        )

    @pytest.mark.asyncio
    async def test_start_handles_db_error_for_summaries(self, mock_graph, mock_repository, mock_summary_service):
        """AC 9: DB-Fehler bei Summary-Loading blockiert nicht den Start."""
        mock_repository.get_recent_summaries.side_effect = Exception("DB connection refused")

        from app.interview.service import InterviewService
        service = InterviewService(
            graph=mock_graph,
            repository=mock_repository,
            summary_service=mock_summary_service,
        )

        events = []
        async for event_data in service.start("test-user"):
            events.append(json.loads(event_data))

        # Interview wurde trotzdem gestartet
        metadata = [e for e in events if e.get("type") == "metadata"]
        assert len(metadata) == 1

        # Leere Summaries als Fallback
        assert mock_graph._current_summaries == []

    @pytest.mark.asyncio
    async def test_start_without_repository_no_summaries(self, mock_graph, mock_summary_service):
        """Ohne Repository werden keine Summaries geladen."""
        from app.interview.service import InterviewService
        service = InterviewService(
            graph=mock_graph,
            repository=None,
            summary_service=mock_summary_service,
        )

        async for _ in service.start("test-user"):
            pass

        assert mock_graph._current_summaries == []


# -- PromptAssembler Integration (Regression) --

class TestPromptAssemblerIntegration:
    """Regression: PromptAssembler.build() funktioniert weiterhin korrekt mit Summaries."""

    def test_build_with_real_summaries(self):
        """PromptAssembler.build() injiziert echte Summaries korrekt."""
        from app.interview.prompt import PromptAssembler, SYSTEM_PROMPT
        summaries = [
            "- User findet Bidding frustrierend\n- Preise sind intransparent",
            "- Onboarding war verwirrend\n- UI ist zu komplex",
            "- User wuenscht sich bessere Dokumentation",
        ]
        result = PromptAssembler.build(summaries=summaries)
        assert SYSTEM_PROMPT in result
        assert "KONTEXT AUS VORHERIGEN GESPRAECHEN" in result
        assert "Gespraech 1" in result
        assert "Gespraech 2" in result
        assert "Gespraech 3" in result
        assert "Bidding frustrierend" in result
        assert "Onboarding war verwirrend" in result
        assert "bessere Dokumentation" in result


# -- SUMMARY_PROMPT --

class TestSummaryPrompt:
    """Summary-Prompt Template ist korrekt definiert."""

    def test_summary_prompt_exists(self):
        """SUMMARY_PROMPT ist definiert."""
        from app.insights.summary import SUMMARY_PROMPT
        assert isinstance(SUMMARY_PROMPT, str)
        assert len(SUMMARY_PROMPT) > 0

    def test_summary_prompt_has_transcript_placeholder(self):
        """SUMMARY_PROMPT hat {transcript} Placeholder."""
        from app.insights.summary import SUMMARY_PROMPT
        assert "{transcript}" in SUMMARY_PROMPT

    def test_summary_prompt_mentions_bullet_format(self):
        """SUMMARY_PROMPT erwaaehnt Bullet-Format."""
        from app.insights.summary import SUMMARY_PROMPT
        assert "- " in SUMMARY_PROMPT


# -- Dependency Injection --

class TestDependencyInjection:
    """InterviewService akzeptiert summary_service Parameter."""

    def test_service_accepts_summary_service(self):
        """InterviewService Constructor hat summary_service Parameter."""
        import inspect
        from app.interview.service import InterviewService
        sig = inspect.signature(InterviewService.__init__)
        assert "summary_service" in sig.parameters

    def test_service_summary_service_is_optional(self):
        """summary_service Parameter ist optional (Default: None)."""
        import inspect
        from app.interview.service import InterviewService
        sig = inspect.signature(InterviewService.__init__)
        param = sig.parameters["summary_service"]
        assert param.default is None


# -- Modul-Existenz --

class TestModuleStructure:
    """Alle neuen/geaenderten Dateien existieren und sind importierbar."""

    def test_summary_service_importable(self):
        """insights/summary.py ist importierbar."""
        from app.insights.summary import SummaryService, SUMMARY_PROMPT
        assert SummaryService is not None
        assert SUMMARY_PROMPT is not None

    def test_summary_service_has_generate_method(self):
        """SummaryService hat generate() Methode."""
        from app.insights.summary import SummaryService
        assert hasattr(SummaryService, "generate")

    def test_summary_service_has_format_method(self):
        """SummaryService hat _format_messages_for_summary() Methode."""
        from app.insights.summary import SummaryService
        assert hasattr(SummaryService, "_format_messages_for_summary")

    def test_graph_has_set_summaries(self):
        """InterviewGraph hat set_summaries() Methode."""
        with patch("app.interview.graph.ChatOpenAI"):
            from app.interview.graph import InterviewGraph
            assert hasattr(InterviewGraph, "set_summaries")
```
</test_spec>

### Manuelle Tests

1. Interview durchspielen und beenden -- Summary pruefen:
   ```bash
   # Start
   curl -N -X POST http://localhost:8000/api/interview/start \
     -H "Content-Type: application/json" \
     -d '{"anonymous_id": "test-user-1"}'

   # Message
   curl -N -X POST http://localhost:8000/api/interview/message \
     -H "Content-Type: application/json" \
     -d '{"session_id": "<id>", "message": "Das Bidding ist frustrierend, die Preise sind total intransparent"}'

   # End -> Echte Summary pruefen
   curl -X POST http://localhost:8000/api/interview/end \
     -H "Content-Type: application/json" \
     -d '{"session_id": "<id>"}'
   ```
   Erwartung: `summary` ist eine Bullet-Liste, nicht der Placeholder-String

2. Zweites Interview mit demselben anonymous_id starten -- Prompt-Injection pruefen:
   ```bash
   curl -N -X POST http://localhost:8000/api/interview/start \
     -H "Content-Type: application/json" \
     -d '{"anonymous_id": "test-user-1"}'
   ```
   Erwartung: Interviewer bezieht sich NICHT direkt auf alte Summaries (Prompt sagt "frage nicht direkt danach"), aber der Kontext ist im System-Prompt vorhanden (in LangSmith pruefbar)

---

## Definition of Done

- [x] Akzeptanzkriterien sind eindeutig & vollstaendig
- [x] Logging fuer Summary-Fehler und DB-Fehler definiert (logger.error)
- [x] Sicherheits-/Privacy-Aspekte bedacht (API-Key via .env, Summary-Inhalte in Supabase encrypted at rest)
- [x] Kein UI in diesem Slice
- [x] Kein Rollout/Rollback noetig

---

## Constraints & Hinweise

**Betrifft:**
- Dieser Slice schliesst die Summary-Luecke und aktiviert session-uebergreifenden Kontext
- SummaryService ist eigenstaendiger Service im `insights/` Bounded Context
- InterviewService orchestriert SummaryService, Graph und Repository

**API Contract:**
- `POST /api/interview/end` -> `EndResponse` mit echtem `summary` (Bullet-Liste) statt Placeholder
- `POST /api/interview/start` -> Unveraendertes SSE-Format, aber System-Prompt enthaelt ggf. vorherige Summaries
- Keine neuen API-Endpoints

**Abgrenzung:**
- Kein Timeout-Management (kommt in Slice 6)
- Kein anderes LLM-Modell fuer Summary (nutzt dasselbe INTERVIEWER_LLM aus Settings)
- Keine Konfigurierbarkeit des Summary-Prompts (hardcoded in diesem Slice)
- Summary-Format ist eine freie Bullet-Liste, kein strukturiertes JSON

---

## Integration Contract (GATE 2 PFLICHT)

### Requires From Other Slices

| Slice | Resource | Type | Validation |
|-------|----------|------|------------|
| slice-02-langgraph-interview | `InterviewGraph` | Klasse | `InterviewGraph(settings)` instanziierbar, `.get_history()`, `.astream()` verfuegbar |
| slice-02-langgraph-interview | `PromptAssembler.build()` | Statische Methode | `(summaries: list[str] \| None) -> str`, injiziert Summaries in System-Prompt |
| slice-02-langgraph-interview | `SUMMARY_INJECTION_TEMPLATE` | String-Konstante | Template fuer Kontext-Injection in `app/interview/prompt.py` |
| slice-04-supabase-persistenz | `InterviewRepository` | Klasse | `.get_recent_summaries(anonymous_id, limit)` -> `list[str]`, `.complete_session()` speichert echte Summary |
| slice-04-supabase-persistenz | `InterviewRepository.get_recent_summaries()` | Methode | `(anonymous_id: str, limit: int) -> list[str]` |
| slice-04-supabase-persistenz | `InterviewRepository.complete_session()` | Methode | `(session_id, transcript, summary, message_count, status) -> dict` |
| slice-04-supabase-persistenz | `InterviewService` | Klasse (erweitert) | Constructor akzeptiert `repository` Parameter |
| slice-01-app-skeleton | `Settings` | Pydantic BaseSettings | `openrouter_api_key`, `interviewer_llm`, `llm_timeout_seconds` |

### Provides To Other Slices

| Resource | Type | Consumer | Interface |
|----------|------|----------|-----------|
| `SummaryService` | Klasse | Slice 6 (Timeout Auto-Summary) | `SummaryService(settings) -> .generate(messages: list[AnyMessage]) -> str` |
| `SummaryService.generate()` | Async Methode | Slice 6 (TimeoutManager) | `(messages: list[AnyMessage]) -> str` (Bullet-Summary) |
| `InterviewGraph.set_summaries()` | Methode | Slice 6 (falls Summaries bei Timeout relevant) | `(summaries: list[str]) -> None` |

### Integration Validation Tasks

- [ ] `PromptAssembler.build()` aus Slice 2 akzeptiert `summaries` Parameter und injiziert korrekt
- [ ] `InterviewRepository.get_recent_summaries()` aus Slice 4 gibt `list[str]` zurueck
- [ ] `InterviewRepository.complete_session()` aus Slice 4 akzeptiert echten Summary-String
- [ ] `InterviewGraph.get_history()` aus Slice 2 gibt Messages fuer SummaryService zurueck
- [ ] `Settings` aus Slice 1 hat `openrouter_api_key`, `interviewer_llm`, `llm_timeout_seconds`
- [ ] `SummaryService.generate()` wird von Slice 6 (TimeoutManager) konsumiert

---

## Code Examples (MANDATORY - GATE 2 PFLICHT)

> **KRITISCH:** Alle Code-Beispiele in diesem Dokument sind **PFLICHT-Deliverables**.
> Der Gate 2 Compliance Agent prueft, dass jedes Code-Beispiel implementiert wird.
> Abweichung nur mit expliziter Begruendung im Commit erlaubt.

| Code Example | Section | Mandatory | Notes |
|--------------|---------|-----------|-------|
| `SummaryService` Klasse | Section 3 (SummaryService) | YES | `generate()`, `_format_messages_for_summary()`, `SUMMARY_PROMPT` |
| `InterviewGraph.set_summaries()` | Section 4 (InterviewGraph Erweiterung) | YES | Neue Methode + `_current_summaries` Attribut |
| `InterviewGraph._interviewer_node()` Aenderung | Section 4 (InterviewGraph Erweiterung) | YES | `self._current_summaries` statt hardcoded `summaries=[]` |
| `InterviewService.start()` Erweiterung | Section 5 (InterviewService Erweiterung) | YES | Summary-Loading + `graph.set_summaries()` |
| `InterviewService.end()` Erweiterung | Section 5 (InterviewService Erweiterung) | YES | `SummaryService.generate()` statt Placeholder |
| `get_interview_service()` Erweiterung | Section 6 (Dependency Injection) | YES | SummaryService erstellen und injizieren |

---

## Deliverables (SCOPE SAFEGUARD)

**WICHTIG: Diese Liste wird automatisch vom Stop-Hook validiert. Der Agent kann nicht stoppen, wenn Dateien fehlen.**

<!-- DELIVERABLES_START -->
### Backend
- [ ] `backend/app/insights/summary.py` -- SummaryService mit generate(), _format_messages_for_summary(), SUMMARY_PROMPT Konstante
- [ ] `backend/app/interview/graph.py` -- MODIFY: Neues Attribut _current_summaries, neue Methode set_summaries(), _interviewer_node() nutzt self._current_summaries statt hardcoded []
- [ ] `backend/app/interview/service.py` -- MODIFY: Constructor akzeptiert summary_service, start() laedt Summaries und ruft graph.set_summaries() auf, end() ruft SummaryService.generate() statt Placeholder
- [ ] `backend/app/api/dependencies.py` -- MODIFY: SummaryService erstellen und an InterviewService uebergeben

### Tests
- [ ] `backend/tests/slices/backend-kern/test_slice_05_summary_injection.py` -- pytest Tests fuer SummaryService (Init, generate, Timeout, Empty-History), InterviewGraph (set_summaries), InterviewService (Summary-End, Summary-Injection-Start, Fehlerbehandlung), PromptAssembler-Regression, Modul-Existenz
<!-- DELIVERABLES_END -->

**Hinweis fuer den Implementierungs-Agent:**
- Alle Dateien zwischen `<!-- DELIVERABLES_START -->` und `<!-- DELIVERABLES_END -->` sind **Pflicht**
- Der Stop-Hook prueft automatisch ob alle Dateien existieren
- Bei fehlenden Dateien wird der Agent blockiert und muss nachfragen

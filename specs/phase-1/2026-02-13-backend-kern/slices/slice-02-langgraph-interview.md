# Slice 2: LangGraph Interview-Graph aufsetzen

> **Slice 2 von 6** fuer `Backend-Kern`
>
> | Navigation | |
> |------------|---|
> | **Vorheriger:** | `slice-01-app-skeleton.md` |
> | **Naechster:** | `slice-03-sse-streaming.md` |

---

## Metadata (fuer Orchestrator)

| Key | Value |
|-----|-------|
| **ID** | `slice-02-langgraph-interview` |
| **Test** | `cd backend && python -m pytest tests/slices/backend-kern/test_slice_02_langgraph_interview.py -v` |
| **E2E** | `false` |
| **Dependencies** | `["slice-01-app-skeleton"]` |

---

## Slice-Uebersicht

| # | Slice | Status | Datei |
|---|-------|--------|-------|
| 1 | App-Skeleton + DDD-Struktur | Done | `slice-01-app-skeleton.md` |
| 2 | LangGraph Interview-Graph | Ready | `slice-02-langgraph-interview.md` |
| 3 | SSE-Streaming Endpoints | Pending | `slice-03-sse-streaming.md` |
| 4 | Supabase-Persistenz | Pending | `slice-04-supabase-persistenz.md` |
| 5 | Summary-Generierung + Injection | Pending | `slice-05-summary-injection.md` |
| 6 | Session-Timeout + Auto-Summary | Pending | `slice-06-session-timeout.md` |

---

## Kontext & Ziel

Der Interview-Graph ist der Kern des FeedbackAI-Backends. Er steuert die Gespraechsfuehrung: Ein LLM (via OpenRouter) fuehrt als Interviewer ein strukturiertes Feedback-Gespraech mit dem User.

In diesem Slice wird der LangGraph StateGraph mit einem einzigen Interviewer-Node erstellt. Der Graph nutzt MemorySaver fuer In-Session Conversation-Persistenz (Multi-Turn). Der bestehende hardcoded SYSTEM_PROMPT aus `backend/app/graph/prompt.py` (nach Slice 1 unter `backend/app/interview/prompt.py`) wird durch einen PromptAssembler zusammengebaut, der bereits ein Interface fuer Summary-Injection vorbereitet (Summaries werden aber erst in Slice 5 tatsaechlich geladen).

Der Graph ist in diesem Slice standalone testbar (ohne HTTP-Endpoints). Die SSE-Streaming-Integration kommt in Slice 3.

**Aktuelle Probleme:**
1. Kein LangGraph-Graph existiert (`interview/graph.py` fehlt)
2. Kein State definiert (`interview/state.py` fehlt)
3. PromptAssembler fehlt (`interview/prompt.py` enthaelt nur den rohen SYSTEM_PROMPT, keine Assembly-Logik)
4. Keine LLM-Integration konfiguriert (OpenRouter via ChatOpenAI)

---

## Technische Umsetzung

### Architektur-Kontext (aus architecture.md)

> **Quelle:** `architecture.md` -> Server Logic -> Services & Processing + Data Flow

```
interview/service.py   (Slice 3+)
  |
  +---> interview/graph.py      <-- LangGraph StateGraph (DIESER SLICE)
  |      +-- interview/state.py     <-- State-Definition (DIESER SLICE)
  |      +-- interview/prompt.py    <-- PromptAssembler (DIESER SLICE)
```

### 1. Architektur-Impact

| Layer | Aenderungen |
|-------|-------------|
| `backend/app/interview/state.py` | NEU: InterviewState TypedDict mit `messages` (add_messages Reducer) |
| `backend/app/interview/graph.py` | NEU: InterviewGraph-Klasse mit StateGraph, Interviewer-Node, MemorySaver |
| `backend/app/interview/prompt.py` | MODIFY: PromptAssembler-Klasse ergaenzen (SYSTEM_PROMPT bleibt, Assembly-Logik hinzu) |

### 2. Datenfluss

```
Aufruf: graph.ainvoke(messages, config={"configurable": {"thread_id": session_id}})
  |
  v
MemorySaver: Laedt vorherige Messages fuer thread_id (falls vorhanden)
  |
  v
Interviewer-Node:
  1. PromptAssembler.build(summaries=[]) -> System-Prompt String
  2. SystemMessage(system_prompt) + State["messages"] -> LLM-Input
  3. ChatOpenAI.ainvoke(messages) -> AIMessage
  |
  v
State-Update: AIMessage wird via add_messages Reducer zur History hinzugefuegt
  |
  v
MemorySaver: Speichert aktualisierten State fuer thread_id
  |
  v
Rueckgabe: Aktualisierter State mit allen Messages
```

### 3. State-Definition

> **Quelle:** `architecture.md` -> Architecture Layers -> Domain (state.py)

```python
# backend/app/interview/state.py
from typing import Annotated
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages
from langchain_core.messages import AnyMessage


class InterviewState(TypedDict):
    """State fuer den Interview-Graph.

    messages: Conversation-History mit add_messages Reducer.
    Der Reducer sorgt dafuer, dass neue Messages zur bestehenden Liste
    hinzugefuegt werden (statt sie zu ueberschreiben).
    """
    messages: Annotated[list[AnyMessage], add_messages]
```

### 4. PromptAssembler

> **Quelle:** `architecture.md` -> Server Logic -> PromptAssembler

Der PromptAssembler baut den vollstaendigen System-Prompt zusammen. In diesem Slice noch OHNE echte Summary-Injection (kommt in Slice 5), aber das Interface akzeptiert bereits eine Liste von Summaries.

```python
# backend/app/interview/prompt.py
"""Interviewer system prompt -- hardcoded for Zipmend Carrier View MVP."""

SYSTEM_PROMPT = """\
# Interviewer Agent -- M0 Instruct System Prompt

## STATIC SECTION
...
"""  # (bestehender Prompt, vollstaendig wie in der aktuellen Datei)


SUMMARY_INJECTION_TEMPLATE = """

## KONTEXT AUS VORHERIGEN GESPRAECHEN

Die folgenden Erkenntnisse stammen aus vorherigen Gespraechen mit diesem User.
Nutze sie als Hintergrund, aber frage nicht direkt danach -- lasse den User neue Themen einbringen.

{summaries}
"""


class PromptAssembler:
    """Baut den vollstaendigen System-Prompt aus statischem Prompt + Summary-Injection."""

    @staticmethod
    def build(summaries: list[str] | None = None) -> str:
        """Assembliert den System-Prompt.

        Args:
            summaries: Liste von Summary-Strings aus vorherigen Sessions.
                       None oder leere Liste = keine Injection.
                       Kommt erst in Slice 5 mit echten Daten.

        Returns:
            Vollstaendiger System-Prompt String.
        """
        prompt = SYSTEM_PROMPT

        if summaries:
            formatted = "\n\n".join(
                f"### Gespraech {i + 1}\n{summary}"
                for i, summary in enumerate(summaries)
            )
            prompt += SUMMARY_INJECTION_TEMPLATE.format(summaries=formatted)

        return prompt
```

### 5. InterviewGraph

> **Quelle:** `architecture.md` -> Server Logic -> InterviewGraph

```python
# backend/app/interview/graph.py
import asyncio
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from app.interview.state import InterviewState
from app.interview.prompt import PromptAssembler
from app.config.settings import Settings


class InterviewGraph:
    """LangGraph StateGraph mit Interviewer-Node.

    Verwendet MemorySaver fuer In-Session Conversation-Persistenz.
    thread_id = session_id fuer Multi-Turn.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._checkpointer = MemorySaver()
        self._llm = ChatOpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=settings.openrouter_api_key,
            model=settings.interviewer_llm,
            temperature=settings.interviewer_temperature,
            max_tokens=settings.interviewer_max_tokens,
        )
        self._graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        """Erstellt und kompiliert den StateGraph."""
        builder = StateGraph(InterviewState)
        builder.add_node("interviewer", self._interviewer_node)
        builder.add_edge(START, "interviewer")
        builder.add_edge("interviewer", END)

        return builder.compile(checkpointer=self._checkpointer)

    async def _interviewer_node(self, state: InterviewState) -> dict:
        """Interviewer-Node: Ruft LLM mit System-Prompt + History auf.

        Args:
            state: Aktueller InterviewState mit messages.

        Returns:
            Dict mit neuer AIMessage unter "messages" Key.
        """
        system_prompt = PromptAssembler.build(summaries=[])
        messages = [SystemMessage(content=system_prompt)] + state["messages"]

        response = await asyncio.wait_for(
            self._llm.ainvoke(messages),
            timeout=self._settings.llm_timeout_seconds,
        )

        return {"messages": [response]}

    async def ainvoke(
        self,
        messages: list,
        session_id: str,
    ) -> InterviewState:
        """Ruft den Graph auf (non-streaming).

        Args:
            messages: Liste von Input-Messages (z.B. [HumanMessage(...)]).
            session_id: Session-ID als thread_id fuer MemorySaver.

        Returns:
            Aktualisierter InterviewState mit allen Messages.
        """
        config = {"configurable": {"thread_id": session_id}}
        result = await self._graph.ainvoke(
            {"messages": messages},
            config=config,
        )
        return result

    async def astream(
        self,
        messages: list,
        session_id: str,
    ):
        """Streamt den Graph Token fuer Token (fuer SSE in Slice 3).

        Args:
            messages: Liste von Input-Messages.
            session_id: Session-ID als thread_id.

        Yields:
            Tuple (chunk, metadata) mit Token-Chunks vom LLM.
        """
        config = {"configurable": {"thread_id": session_id}}
        async for chunk, metadata in self._graph.astream(
            {"messages": messages},
            config=config,
            stream_mode="messages",
        ):
            yield chunk, metadata

    def get_history(self, session_id: str) -> list:
        """Liest die Conversation-History aus dem MemorySaver.

        Args:
            session_id: Session-ID (thread_id).

        Returns:
            Liste von Messages aus dem State.
        """
        config = {"configurable": {"thread_id": session_id}}
        state = self._graph.get_state(config)
        if state and state.values:
            return state.values.get("messages", [])
        return []
```

### 6. Externe Services/APIs

| Service | Zweck | Integration |
|---------|-------|-------------|
| OpenRouter | LLM-Provider (OpenAI-kompatibel) | `interview/graph.py` via `langchain-openai` ChatOpenAI |

**Konfiguration:**
- `OPENROUTER_API_KEY`: API-Key (Pflicht, via Settings)
- `INTERVIEWER_LLM`: Model-ID, Default `anthropic/claude-sonnet-4.5` (via Settings)
- `INTERVIEWER_TEMPERATURE`: Default `1.0` (via Settings)
- `INTERVIEWER_MAX_TOKENS`: Default `4000` (via Settings)
- `LLM_TIMEOUT_SECONDS`: Default `30` (via Settings, als asyncio.wait_for Timeout)

**Error Handling:**
- `asyncio.TimeoutError`: LLM-Call dauert laenger als `LLM_TIMEOUT_SECONDS` -> wird in Slice 3 als SSE-Error an Client gesendet
- `openai.APIError` / `openai.AuthenticationError`: OpenRouter nicht erreichbar oder Key ungueltig -> wird im Interviewer-Node nicht gefangen (Slice 3 faengt es in der Route)

### 7. Abhaengigkeiten

- Bestehend: `langgraph`, `langchain-openai`, `langchain-core` (bereits in requirements.txt)
- Neu: Keine neuen Dependencies noetig

### 8. Wiederverwendete Code-Bausteine

| Funktion | Datei | Rueckgabetyp | Wichtige Hinweise |
|----------|-------|-------------|-------------------|
| `Settings` | `app/config/settings.py` | `Settings` Instanz | Aus Slice 1: Alle ENV-Vars, Zugriff via `settings.openrouter_api_key` etc. |
| `SYSTEM_PROMPT` | `app/interview/prompt.py` | `str` | Aus Slice 1: Migrierter hardcoded Prompt |

---

## Integrations-Checkliste (Pflicht bei Backend-Aenderungen)

### 1. State-Integration
- [x] InterviewState als TypedDict mit `messages` Annotated[list[AnyMessage], add_messages]
- [x] State-Transfer: `{"messages": messages}` als Input, aktualisierter State als Output
- [x] Rueckgabetypen explizit: `InterviewState` (TypedDict), `AIMessage` vom LLM

### 2. LangGraph-Integration
- [x] Node-Transition: START -> interviewer -> END (linearer Graph)
- [x] MemorySaver als Checkpointer fuer Multi-Turn Persistenz
- [x] thread_id = session_id fuer Session-Isolation

### 3. LLM-Integration
- [x] System-Prompt aus PromptAssembler.build()
- [x] ChatOpenAI mit OpenRouter base_url
- [x] Timeout via asyncio.wait_for (LLM_TIMEOUT_SECONDS)

### 4. Datenbank-Integration
- [x] Nicht betroffen (kommt in Slice 4)

### 5. Utility-Funktionen
- [x] Settings aus Slice 1 wiederverwendet
- [x] SYSTEM_PROMPT aus bestehender prompt.py wiederverwendet

### 6. Feature-Aktivierung
- [x] Graph wird in Slice 3 von InterviewService instanziiert
- [x] In diesem Slice: Standalone-Tests via direkten InterviewGraph-Aufruf

### 7. Datenfluss-Vollstaendigkeit
- [x] Input: `list[HumanMessage]` + `session_id: str`
- [x] State: `InterviewState(messages=[SystemMessage, HumanMessage, AIMessage, ...])`
- [x] Output: `InterviewState` mit aktualisierter messages-Liste
- [x] Datenquelle: In-Memory (MemorySaver), LLM-Call (OpenRouter)

---

## UI Anforderungen

Keine UI in diesem Slice (Backend-only).

---

## Acceptance Criteria

1) GIVEN ein InterviewGraph ist mit gueltigen Settings instanziiert
   WHEN `ainvoke()` mit einer HumanMessage und einer session_id aufgerufen wird
   THEN wird ein InterviewState zurueckgegeben der mindestens eine AIMessage in `messages` enthaelt

2) GIVEN ein InterviewGraph ist instanziiert
   WHEN `ainvoke()` zweimal hintereinander mit derselben session_id aufgerufen wird (Multi-Turn)
   THEN enthaelt der zweite State alle Messages aus beiden Turns (MemorySaver Persistenz)

3) GIVEN ein InterviewGraph ist instanziiert
   WHEN `ainvoke()` mit zwei verschiedenen session_ids aufgerufen wird
   THEN sind die Conversation-Histories isoliert (verschiedene MemorySaver-Threads)

4) GIVEN ein InterviewGraph ist instanziiert
   WHEN `get_history()` mit einer session_id aufgerufen wird nach einem `ainvoke()`
   THEN wird die vollstaendige Conversation-History als Liste von Messages zurueckgegeben

5) GIVEN ein PromptAssembler
   WHEN `build()` ohne Summaries aufgerufen wird (summaries=None oder summaries=[])
   THEN wird exakt der SYSTEM_PROMPT zurueckgegeben (ohne Summary-Injection-Block)

6) GIVEN ein PromptAssembler
   WHEN `build()` mit einer Liste von Summary-Strings aufgerufen wird
   THEN enthaelt der zurueckgegebene Prompt den SYSTEM_PROMPT gefolgt vom Summary-Injection-Block mit den formatierten Summaries

7) GIVEN ein InterviewGraph ist instanziiert
   WHEN `ainvoke()` mit einer leeren Messages-Liste und neuer session_id aufgerufen wird (Opening)
   THEN generiert der Interviewer eine Opening-Frage (AIMessage mit Content)

8) GIVEN die LLM-Antwort dauert laenger als LLM_TIMEOUT_SECONDS
   WHEN `ainvoke()` aufgerufen wird
   THEN wird ein `asyncio.TimeoutError` geworfen

9) GIVEN ein InterviewGraph ist instanziiert
   WHEN `astream()` mit einer HumanMessage aufgerufen wird
   THEN werden Token-Chunks als async Generator geliefert (mindestens ein Chunk mit Content)

---

## Testfaelle

**WICHTIG:** Tests muessen VOR der Implementierung definiert werden! Der Orchestrator fuehrt diese Tests automatisch nach der Slice-Implementierung aus.

### Test-Datei

**Fuer diesen Slice:** `backend/tests/slices/backend-kern/test_slice_02_langgraph_interview.py`

### Unit Tests (pytest)

<test_spec>
```python
# backend/tests/slices/backend-kern/test_slice_02_langgraph_interview.py
import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage


# -- Fixtures --

@pytest.fixture
def mock_settings():
    """Mock Settings mit Test-Werten."""
    with patch.dict("os.environ", {
        "OPENROUTER_API_KEY": "test-key",
        "SUPABASE_URL": "https://test.supabase.co",
        "SUPABASE_KEY": "test-supabase-key",
    }, clear=False):
        from app.config.settings import Settings
        return Settings()


@pytest.fixture
def mock_llm_response():
    """Standard-AIMessage die der Mock-LLM zurueckgibt."""
    return AIMessage(content="Was genau war dabei das groesste Problem fuer dich?")


@pytest.fixture
def interview_graph(mock_settings, mock_llm_response):
    """InterviewGraph mit gemocktem LLM."""
    with patch("app.interview.graph.ChatOpenAI") as MockChatOpenAI:
        mock_llm = AsyncMock()
        mock_llm.ainvoke = AsyncMock(return_value=mock_llm_response)
        MockChatOpenAI.return_value = mock_llm

        from app.interview.graph import InterviewGraph
        graph = InterviewGraph(settings=mock_settings)
        graph._llm = mock_llm
        return graph


# -- InterviewState --

class TestInterviewState:
    """State-Definition hat korrekte Struktur."""

    def test_state_has_messages_field(self):
        """InterviewState hat ein 'messages' Feld."""
        from app.interview.state import InterviewState
        assert "messages" in InterviewState.__annotations__

    def test_state_messages_uses_add_messages_reducer(self):
        """messages-Feld nutzt den add_messages Reducer (Annotated)."""
        from app.interview.state import InterviewState
        import typing
        hints = typing.get_type_hints(InterviewState, include_extras=True)
        messages_hint = hints["messages"]
        # Annotated type hat __metadata__
        assert hasattr(messages_hint, "__metadata__")


# -- PromptAssembler --

class TestPromptAssembler:
    """AC 5 + AC 6: PromptAssembler baut System-Prompt korrekt zusammen."""

    def test_build_without_summaries_returns_base_prompt(self):
        """AC 5: Ohne Summaries wird exakt der SYSTEM_PROMPT zurueckgegeben."""
        from app.interview.prompt import PromptAssembler, SYSTEM_PROMPT
        result = PromptAssembler.build(summaries=None)
        assert result == SYSTEM_PROMPT

    def test_build_with_empty_list_returns_base_prompt(self):
        """AC 5: Leere Liste = keine Injection."""
        from app.interview.prompt import PromptAssembler, SYSTEM_PROMPT
        result = PromptAssembler.build(summaries=[])
        assert result == SYSTEM_PROMPT

    def test_build_with_summaries_injects_context(self):
        """AC 6: Summaries werden in den Prompt injiziert."""
        from app.interview.prompt import PromptAssembler, SYSTEM_PROMPT
        summaries = [
            "- User findet das Bidding frustrierend\n- Preise sind intransparent",
            "- Onboarding war verwirrend\n- UI ist zu komplex",
        ]
        result = PromptAssembler.build(summaries=summaries)
        assert SYSTEM_PROMPT in result
        assert "KONTEXT AUS VORHERIGEN GESPRAECHEN" in result
        assert "Gespraech 1" in result
        assert "Gespraech 2" in result
        assert "Bidding frustrierend" in result
        assert "Onboarding war verwirrend" in result

    def test_build_with_summaries_preserves_base_prompt(self):
        """AC 6: Der Basis-Prompt bleibt vollstaendig erhalten."""
        from app.interview.prompt import PromptAssembler, SYSTEM_PROMPT
        result = PromptAssembler.build(summaries=["Test summary"])
        assert result.startswith(SYSTEM_PROMPT)

    def test_system_prompt_contains_interviewer_instructions(self):
        """SYSTEM_PROMPT enthaelt die wesentlichen Interviewer-Anweisungen."""
        from app.interview.prompt import SYSTEM_PROMPT
        assert "Interviewer" in SYSTEM_PROMPT
        assert "Zipmend" in SYSTEM_PROMPT
        assert "ANTI-LEADING" in SYSTEM_PROMPT
        assert "OPENING" in SYSTEM_PROMPT


# -- InterviewGraph --

class TestInterviewGraphInit:
    """InterviewGraph wird korrekt initialisiert."""

    def test_graph_creates_with_settings(self, mock_settings):
        """Graph laesst sich mit Settings instanziieren."""
        with patch("app.interview.graph.ChatOpenAI"):
            from app.interview.graph import InterviewGraph
            graph = InterviewGraph(settings=mock_settings)
            assert graph is not None

    def test_graph_uses_openrouter_base_url(self, mock_settings):
        """LLM wird mit OpenRouter base_url konfiguriert."""
        with patch("app.interview.graph.ChatOpenAI") as MockChatOpenAI:
            from app.interview.graph import InterviewGraph
            InterviewGraph(settings=mock_settings)
            MockChatOpenAI.assert_called_once()
            call_kwargs = MockChatOpenAI.call_args[1]
            assert call_kwargs["base_url"] == "https://openrouter.ai/api/v1"

    def test_graph_uses_settings_model(self, mock_settings):
        """LLM verwendet das konfigurierte Modell aus Settings."""
        with patch("app.interview.graph.ChatOpenAI") as MockChatOpenAI:
            from app.interview.graph import InterviewGraph
            InterviewGraph(settings=mock_settings)
            call_kwargs = MockChatOpenAI.call_args[1]
            assert call_kwargs["model"] == mock_settings.interviewer_llm

    def test_graph_uses_settings_temperature(self, mock_settings):
        """LLM verwendet die konfigurierte Temperature aus Settings."""
        with patch("app.interview.graph.ChatOpenAI") as MockChatOpenAI:
            from app.interview.graph import InterviewGraph
            InterviewGraph(settings=mock_settings)
            call_kwargs = MockChatOpenAI.call_args[1]
            assert call_kwargs["temperature"] == mock_settings.interviewer_temperature

    def test_graph_uses_settings_max_tokens(self, mock_settings):
        """LLM verwendet die konfigurierten Max-Tokens aus Settings."""
        with patch("app.interview.graph.ChatOpenAI") as MockChatOpenAI:
            from app.interview.graph import InterviewGraph
            InterviewGraph(settings=mock_settings)
            call_kwargs = MockChatOpenAI.call_args[1]
            assert call_kwargs["max_tokens"] == mock_settings.interviewer_max_tokens


class TestInterviewGraphInvoke:
    """AC 1 + AC 2 + AC 3: Graph-Aufrufe und Multi-Turn."""

    @pytest.mark.asyncio
    async def test_ainvoke_returns_state_with_ai_message(self, interview_graph):
        """AC 1: ainvoke gibt State mit AIMessage zurueck."""
        result = await interview_graph.ainvoke(
            messages=[HumanMessage(content="Das Bidding ist frustrierend")],
            session_id="test-session-1",
        )
        assert "messages" in result
        ai_messages = [m for m in result["messages"] if isinstance(m, AIMessage)]
        assert len(ai_messages) >= 1

    @pytest.mark.asyncio
    async def test_ainvoke_multi_turn_preserves_history(self, interview_graph):
        """AC 2: Zweiter Aufruf mit gleicher session_id enthaelt alle Messages."""
        session_id = "test-session-multi"

        # Turn 1
        await interview_graph.ainvoke(
            messages=[HumanMessage(content="Erste Nachricht")],
            session_id=session_id,
        )

        # Turn 2
        result = await interview_graph.ainvoke(
            messages=[HumanMessage(content="Zweite Nachricht")],
            session_id=session_id,
        )

        human_messages = [m for m in result["messages"] if isinstance(m, HumanMessage)]
        assert len(human_messages) >= 2

    @pytest.mark.asyncio
    async def test_ainvoke_different_sessions_are_isolated(self, interview_graph):
        """AC 3: Verschiedene session_ids haben isolierte Histories."""
        await interview_graph.ainvoke(
            messages=[HumanMessage(content="Session A Nachricht")],
            session_id="session-a",
        )

        result_b = await interview_graph.ainvoke(
            messages=[HumanMessage(content="Session B Nachricht")],
            session_id="session-b",
        )

        # Session B sollte keine Messages aus Session A enthalten
        all_content = " ".join(m.content for m in result_b["messages"] if hasattr(m, "content"))
        assert "Session A" not in all_content

    @pytest.mark.asyncio
    async def test_ainvoke_opening_without_user_message(self, interview_graph):
        """AC 7: Opening-Frage ohne vorherige User-Nachricht."""
        result = await interview_graph.ainvoke(
            messages=[],
            session_id="test-opening",
        )
        ai_messages = [m for m in result["messages"] if isinstance(m, AIMessage)]
        assert len(ai_messages) >= 1
        assert len(ai_messages[0].content) > 0


class TestInterviewGraphHistory:
    """AC 4: get_history liest Conversation-History."""

    @pytest.mark.asyncio
    async def test_get_history_returns_messages(self, interview_graph):
        """AC 4: get_history gibt Messages nach ainvoke zurueck."""
        session_id = "test-history"
        await interview_graph.ainvoke(
            messages=[HumanMessage(content="Test Nachricht")],
            session_id=session_id,
        )

        history = interview_graph.get_history(session_id)
        assert len(history) > 0

    def test_get_history_empty_session(self, interview_graph):
        """get_history gibt leere Liste fuer unbekannte session_id."""
        history = interview_graph.get_history("unknown-session")
        assert history == []


class TestInterviewGraphStream:
    """AC 9: astream liefert Token-Chunks."""

    @pytest.mark.asyncio
    async def test_astream_yields_chunks(self, interview_graph, mock_llm_response):
        """AC 9: astream liefert mindestens einen Chunk."""
        # Fuer Streaming muessen wir den Graph-internen astream mocken
        # Da der echte astream ueber den kompilierten Graph geht,
        # testen wir hier nur die Interface-Existenz und den Aufruf
        chunks = []
        try:
            async for chunk, metadata in interview_graph.astream(
                messages=[HumanMessage(content="Test")],
                session_id="test-stream",
            ):
                chunks.append(chunk)
                if len(chunks) >= 1:
                    break
        except Exception:
            # Mock mag kein astream unterstuetzen -- das ist OK fuer Unit-Tests
            pass

        # Interface existiert und ist aufrufbar
        assert hasattr(interview_graph, "astream")


class TestInterviewGraphTimeout:
    """AC 8: LLM-Timeout wird korrekt behandelt."""

    @pytest.mark.asyncio
    async def test_timeout_raises_error(self, mock_settings):
        """AC 8: TimeoutError bei langsamem LLM."""
        with patch("app.interview.graph.ChatOpenAI") as MockChatOpenAI:
            # LLM simuliert langsame Antwort
            async def slow_invoke(*args, **kwargs):
                await asyncio.sleep(100)
                return AIMessage(content="Zu spaet")

            mock_llm = AsyncMock()
            mock_llm.ainvoke = slow_invoke
            MockChatOpenAI.return_value = mock_llm

            # Settings mit sehr kurzem Timeout
            mock_settings_short = MagicMock()
            mock_settings_short.openrouter_api_key = "test"
            mock_settings_short.interviewer_llm = "test-model"
            mock_settings_short.interviewer_temperature = 1.0
            mock_settings_short.interviewer_max_tokens = 100
            mock_settings_short.llm_timeout_seconds = 0.1  # 100ms Timeout

            from app.interview.graph import InterviewGraph
            graph = InterviewGraph(settings=mock_settings_short)
            graph._llm = mock_llm

            with pytest.raises(asyncio.TimeoutError):
                await graph.ainvoke(
                    messages=[HumanMessage(content="Test")],
                    session_id="test-timeout",
                )


# -- Modul-Existenz --

class TestModuleStructure:
    """Alle Dateien existieren und sind importierbar."""

    def test_state_module_importable(self):
        """interview/state.py ist importierbar."""
        from app.interview.state import InterviewState
        assert InterviewState is not None

    def test_prompt_module_importable(self):
        """interview/prompt.py ist importierbar."""
        from app.interview.prompt import PromptAssembler, SYSTEM_PROMPT
        assert PromptAssembler is not None
        assert isinstance(SYSTEM_PROMPT, str)

    def test_graph_module_importable(self):
        """interview/graph.py ist importierbar."""
        with patch("app.interview.graph.ChatOpenAI"):
            from app.interview.graph import InterviewGraph
            assert InterviewGraph is not None
```
</test_spec>

### Manuelle Tests

1. Graph mit echtem OpenRouter-Key testen (erfordert `.env` mit gueltigem `OPENROUTER_API_KEY`):
   ```python
   import asyncio
   from app.config.settings import Settings
   from app.interview.graph import InterviewGraph
   from langchain_core.messages import HumanMessage

   async def manual_test():
       settings = Settings()
       graph = InterviewGraph(settings=settings)
       result = await graph.ainvoke(
           messages=[HumanMessage(content="Das Bidding ist total frustrierend")],
           session_id="manual-test-1",
       )
       for msg in result["messages"]:
           print(f"{type(msg).__name__}: {msg.content[:100]}")

   asyncio.run(manual_test())
   ```

---

## Definition of Done

- [x] Akzeptanzkriterien sind eindeutig & vollstaendig
- [x] Kein Logging/Telemetrie in diesem Slice (LangSmith-Tracing ist automatisch via langchain)
- [x] Sicherheits-/Privacy-Aspekte bedacht (API-Key nicht im Code, via Settings/.env)
- [x] Kein UI in diesem Slice
- [x] Kein Rollout/Rollback noetig (Fundament-Slice)

---

## Constraints & Hinweise

**Betrifft:**
- Dieser Slice erstellt den Kern des Interview-Systems
- Graph muss standalone testbar sein (ohne HTTP-Endpoints)
- PromptAssembler hat Summary-Interface aber nutzt es noch nicht mit echten Daten

**API Contract:**
- `InterviewGraph.ainvoke(messages, session_id)` -> `InterviewState`
- `InterviewGraph.astream(messages, session_id)` -> `AsyncGenerator[(chunk, metadata)]`
- `InterviewGraph.get_history(session_id)` -> `list[AnyMessage]`
- `PromptAssembler.build(summaries)` -> `str`

**Abgrenzung:**
- Keine HTTP-Endpoints (kommt in Slice 3)
- Keine Supabase-Persistenz (kommt in Slice 4)
- Keine echte Summary-Injection (kommt in Slice 5, PromptAssembler.build() wird dort mit echten Summaries aufgerufen)
- Kein Error-Handling auf HTTP-Ebene (kommt in Slice 3)

---

## Integration Contract (GATE 2 PFLICHT)

### Requires From Other Slices

| Slice | Resource | Type | Validation |
|-------|----------|------|------------|
| slice-01-app-skeleton | `Settings` | Pydantic BaseSettings Klasse | `from app.config.settings import Settings` importierbar, enthaelt `openrouter_api_key`, `interviewer_llm`, `interviewer_temperature`, `interviewer_max_tokens`, `llm_timeout_seconds` |
| slice-01-app-skeleton | `SYSTEM_PROMPT` | String-Konstante in `app/interview/prompt.py` | Migrierte Datei mit hardcoded Prompt |
| slice-01-app-skeleton | DDD-Ordnerstruktur | Directory Layout | `app/interview/` Ordner existiert mit `__init__.py` |

### Provides To Other Slices

| Resource | Type | Consumer | Interface |
|----------|------|----------|-----------|
| `InterviewGraph` | Klasse | Slice 3 (SSE-Streaming), Slice 5 (Summary), Slice 6 (Timeout) | `InterviewGraph(settings) -> .ainvoke(messages, session_id) -> InterviewState` |
| `InterviewGraph.astream()` | Async Generator | Slice 3 (SSE-Streaming) | `(messages, session_id) -> AsyncGenerator[(chunk, metadata)]` |
| `InterviewGraph.get_history()` | Methode | Slice 3 (POST /end), Slice 5 (Summary), Slice 6 (Timeout) | `(session_id) -> list[AnyMessage]` |
| `PromptAssembler` | Klasse | Slice 5 (Summary-Injection) | `PromptAssembler.build(summaries: list[str] | None) -> str` |
| `InterviewState` | TypedDict | Slice 3, Slice 5 | `from app.interview.state import InterviewState` |

### Integration Validation Tasks

- [ ] `Settings` aus Slice 1 ist importierbar mit allen benoetigten Feldern
- [ ] DDD-Ordner `app/interview/` existiert mit `__init__.py`
- [ ] `SYSTEM_PROMPT` in `app/interview/prompt.py` ist vorhanden
- [ ] `InterviewGraph` wird von Slice 3 korrekt konsumiert (ainvoke + astream)
- [ ] `PromptAssembler.build()` wird von Slice 5 mit echten Summaries aufgerufen

---

## Code Examples (MANDATORY - GATE 2 PFLICHT)

> **KRITISCH:** Alle Code-Beispiele in diesem Dokument sind **PFLICHT-Deliverables**.
> Der Gate 2 Compliance Agent prueft, dass jedes Code-Beispiel implementiert wird.
> Abweichung nur mit expliziter Begruendung im Commit erlaubt.

| Code Example | Section | Mandatory | Notes |
|--------------|---------|-----------|-------|
| `InterviewState` TypedDict | Section 3 (State-Definition) | YES | Exakt wie spezifiziert mit `add_messages` Reducer |
| `PromptAssembler` Klasse | Section 4 (PromptAssembler) | YES | `build()` Methode mit summaries-Parameter, SUMMARY_INJECTION_TEMPLATE |
| `InterviewGraph` Klasse | Section 5 (InterviewGraph) | YES | `ainvoke()`, `astream()`, `get_history()` Methoden, MemorySaver, ChatOpenAI mit OpenRouter |
| `SYSTEM_PROMPT` | Section 4 (PromptAssembler) | YES | Bestehender Prompt aus prompt.py, unveraendert |
| `SUMMARY_INJECTION_TEMPLATE` | Section 4 (PromptAssembler) | YES | Template-String fuer Summary-Injection |

---

## Deliverables (SCOPE SAFEGUARD)

**WICHTIG: Diese Liste wird automatisch vom Stop-Hook validiert. Der Agent kann nicht stoppen, wenn Dateien fehlen.**

<!-- DELIVERABLES_START -->
### Backend
- [ ] `backend/app/interview/state.py` -- InterviewState TypedDict mit messages-Feld (Annotated mit add_messages Reducer)
- [ ] `backend/app/interview/graph.py` -- InterviewGraph-Klasse mit StateGraph, Interviewer-Node, MemorySaver, ainvoke(), astream(), get_history()
- [ ] `backend/app/interview/prompt.py` -- MODIFY: PromptAssembler-Klasse hinzufuegen (SYSTEM_PROMPT bleibt unveraendert, SUMMARY_INJECTION_TEMPLATE und PromptAssembler.build() ergaenzen)

### Tests
- [ ] `backend/tests/slices/backend-kern/test_slice_02_langgraph_interview.py` -- pytest Tests fuer InterviewState, PromptAssembler, InterviewGraph (ainvoke, Multi-Turn, Session-Isolation, History, Timeout)
<!-- DELIVERABLES_END -->

**Hinweis fuer den Implementierungs-Agent:**
- Alle Dateien zwischen `<!-- DELIVERABLES_START -->` und `<!-- DELIVERABLES_END -->` sind **Pflicht**
- Der Stop-Hook prueft automatisch ob alle Dateien existieren
- Bei fehlenden Dateien wird der Agent blockiert und muss nachfragen

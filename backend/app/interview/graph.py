"""LangGraph Interview StateGraph with Interviewer-Node."""

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
        self._current_summaries: list[str] = []
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
        system_prompt = PromptAssembler.build(summaries=self._current_summaries)
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

    def set_summaries(self, summaries: list[str]) -> None:
        """Setzt die Summaries fuer den naechsten Graph-Aufruf.

        Wird von InterviewService.start() aufgerufen BEVOR der Graph
        invoked wird. Die Summaries werden dann in _interviewer_node()
        an PromptAssembler.build() weitergegeben.

        Args:
            summaries: Liste von Summary-Strings aus vorherigen Sessions.
        """
        self._current_summaries = summaries or []

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

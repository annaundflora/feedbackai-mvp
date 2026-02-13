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

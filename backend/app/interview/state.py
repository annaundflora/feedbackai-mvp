"""Interview State definition for LangGraph StateGraph."""

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

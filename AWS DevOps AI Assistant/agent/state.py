from typing import TypedDict, List, Optional, Annotated
from langchain_core.messages import BaseMessage
import operator


class AgentState(TypedDict):
    """Shared state across all LangGraph nodes."""

    # Conversation messages (reducer: append)
    messages: Annotated[List[BaseMessage], operator.add]

    # Current user question
    question: str

    # Retrieved RAG context
    context: str
    sources: List[str]

    # Tool execution results
    tool_results: List[dict]

    # Final answer
    final_answer: Optional[str]

    # User/channel metadata
    user_id: str
    channel_id: str

    # Loop control
    iteration: int
    should_use_tools: bool

    history: str
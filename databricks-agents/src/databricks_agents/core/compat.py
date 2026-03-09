"""
Optional LangChain compatibility helpers.

Converts SDK types to LangChain message objects. This replaces the
``ResponsesAgent.prep_msgs_for_llm()`` method for agents that use LangChain.

Requires ``langchain-core`` — only import this module from agents that
already depend on LangChain.

Usage:
    from databricks_agents.core.compat import to_langchain_messages

    messages = to_langchain_messages(request)
    result = llm.invoke(messages)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, List

if TYPE_CHECKING:
    from langchain_core.messages import BaseMessage

from .types import AgentRequest, InputItem


def to_langchain_messages(request: AgentRequest) -> List[BaseMessage]:
    """
    Convert an AgentRequest into a list of LangChain BaseMessage objects.

    Maps roles: "user" -> HumanMessage, "assistant" -> AIMessage,
    "system" -> SystemMessage. Unknown roles default to HumanMessage.
    """
    from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

    _role_map = {
        "user": HumanMessage,
        "assistant": AIMessage,
        "system": SystemMessage,
    }

    messages: List[BaseMessage] = []
    for item in request.input:
        cls = _role_map.get(item.role, HumanMessage)
        messages.append(cls(content=item.content))

    return messages

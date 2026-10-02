"""LangGraph agent — normalize → (clarify?) → lookup → rank → explain → guardrail.

Compile lazy qua `get_agent()`: import module này KHÔNG chạy graph build, nên test
import được ngay cả khi chưa cấu hình LLM. `interface/backend` gọi qua
`agent_adapter.get_agent()` — lõi AI không import ngược lại web.
"""

from __future__ import annotations

import threading
from typing import Any

from langgraph.graph import END, START, StateGraph

from src.agents.nodes.clarify import clarify_node
from src.agents.nodes.explain import explain_node
from src.agents.nodes.guardrail import guardrail_node, needs_retry
from src.agents.nodes.lookup import lookup_node
from src.agents.nodes.normalize import normalize_node
from src.agents.nodes.rank import rank_node
from src.agents.state import AgentState

_lock = threading.Lock()
_agent: Any | None = None


def after_normalize(state: AgentState) -> str:
    if state.get("error"):
        return "error"
    if state.get("pending_clarifications"):
        return "clarify"
    return "lookup"


def after_guardrail(state: AgentState) -> str:
    return "explain" if needs_retry(state) == "explain" else END


async def error_node(state: AgentState) -> dict[str, Any]:
    return {
        "response": state.get("error", "Lỗi không xác định."),
        "guardrail_result": {"pass": True, "violations": [], "reason": "error_path"},
    }


def build_graph():
    graph = StateGraph(AgentState)
    graph.add_node("normalize", normalize_node)
    graph.add_node("clarify", clarify_node)
    graph.add_node("lookup", lookup_node)
    graph.add_node("rank", rank_node)
    graph.add_node("explain", explain_node)
    graph.add_node("guardrail", guardrail_node)
    graph.add_node("error", error_node)

    graph.add_edge(START, "normalize")
    graph.add_conditional_edges("normalize", after_normalize,
                                {"clarify": "clarify", "lookup": "lookup", "error": "error"})
    graph.add_edge("clarify", END)
    graph.add_edge("lookup", "rank")
    graph.add_edge("rank", "explain")
    graph.add_edge("explain", "guardrail")
    graph.add_conditional_edges("guardrail", after_guardrail, {"explain": "explain", END: END})
    graph.add_edge("error", END)

    return graph.compile()


def get_agent():
    """Lazy singleton — compile đúng một lần, không chạy lúc import."""
    global _agent
    if _agent is None:
        with _lock:
            if _agent is None:
                _agent = build_graph()
    return _agent

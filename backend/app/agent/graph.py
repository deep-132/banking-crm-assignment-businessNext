"""LangGraph wiring: an explicit state machine so each RM turn takes exactly
the path its intent requires, reusing cached state where possible instead of
re-running the full retrieval + scoring pipeline every time.
"""

from langgraph.graph import END, StateGraph

from app.agent import nodes
from app.agent.state import AgentState
from app.agent.supervisor import route


def _route_after_supervisor(state: AgentState) -> str:
    action = state["intent"]["action"]
    if action == "full_search":
        return "retrieve_and_score"
    if action == "refine":
        return "rank_and_select"
    if action == "explain":
        return "explain"
    return "clarify"


def build_graph():
    graph = StateGraph(AgentState)

    graph.add_node("supervisor", route)
    graph.add_node("retrieve_and_score", nodes.retrieve_and_score_node)
    graph.add_node("rank_and_select", nodes.rank_and_select_node)
    graph.add_node("generate_messages", nodes.generate_messages_node)
    graph.add_node("compose_response", nodes.compose_response_node)
    graph.add_node("explain", nodes.explain_node)
    graph.add_node("clarify", nodes.clarify_node)

    graph.set_entry_point("supervisor")

    graph.add_conditional_edges(
        "supervisor",
        _route_after_supervisor,
        {
            "retrieve_and_score": "retrieve_and_score",
            "rank_and_select": "rank_and_select",
            "explain": "explain",
            "clarify": "clarify",
        },
    )

    # full_search path: retrieve -> score -> rank -> messages -> compose
    graph.add_edge("retrieve_and_score", "rank_and_select")
    # both full_search and refine converge here: rank -> messages -> compose
    graph.add_edge("rank_and_select", "generate_messages")
    graph.add_edge("generate_messages", "compose_response")
    graph.add_edge("compose_response", END)

    graph.add_edge("explain", END)
    graph.add_edge("clarify", END)

    return graph.compile()


_compiled_graph = None


def get_agent_graph():
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_graph()
    return _compiled_graph

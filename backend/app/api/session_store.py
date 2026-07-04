"""In-memory session state store, keyed by session_id.

A local dict is enough for a take-home demo; the README documents swapping
this for Redis/a DB table so state survives backend restarts and scales
across multiple workers in production.
"""

from app.agent.state import AgentState

_sessions: dict[str, AgentState] = {}


def get_session(session_id: str) -> AgentState:
    if session_id not in _sessions:
        _sessions[session_id] = AgentState(
            session_id=session_id,
            chat_history=[],
            all_scored_records=[],
            top_customers=[],
            generated_messages={},
        )
    return _sessions[session_id]


def save_session(session_id: str, state: AgentState) -> None:
    _sessions[session_id] = state


def reset_all_sessions() -> None:
    _sessions.clear()

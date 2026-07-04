from typing import Any, Literal, TypedDict

IntentAction = Literal["full_search", "refine", "explain", "clarify"]


class Intent(TypedDict, total=False):
    action: IntentAction
    product_type: str
    city: str | None
    segment: str | None
    top_n: int
    target_customer_id: str | None
    clarification_question: str | None
    language_override: str | None


class AgentState(TypedDict, total=False):
    session_id: str
    chat_history: list[dict[str, str]]
    raw_query: str
    intent: Intent

    # Full scored universe from the most recent full_search — enables refine/
    # explain follow-ups to reuse work instead of re-querying the DB.
    all_scored_records: list[dict[str, Any]]

    top_customers: list[dict[str, Any]]
    generated_messages: dict[str, dict[str, str]]
    reply_text: str
    last_action: IntentAction | None

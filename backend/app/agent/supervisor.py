"""Supervisor/router node: turns the RM's free-text message into structured intent
and decides which pipeline path the graph should take next.
"""

import json
import logging

from app.agent.prompts import SUPERVISOR_SYSTEM_PROMPT, build_supervisor_user_prompt
from app.agent.state import AgentState, Intent
from app.llm_client import chat_completion

logger = logging.getLogger(__name__)

DEFAULT_INTENT: Intent = {
    "action": "full_search",
    "product_type": "personal_loan",
    "city": None,
    "segment": None,
    "top_n": 10,
    "target_customer_id": None,
    "clarification_question": None,
    "language_override": None,
}


def _parse_intent(raw: str) -> Intent:
    data = json.loads(raw)
    intent: Intent = {**DEFAULT_INTENT, **{k: v for k, v in data.items() if k in DEFAULT_INTENT}}
    if intent["action"] not in ("full_search", "refine", "explain", "clarify"):
        intent["action"] = "full_search"
    if not isinstance(intent.get("top_n"), int) or intent["top_n"] <= 0:
        intent["top_n"] = 10
    return intent


def route(state: AgentState) -> AgentState:
    has_prior_results = bool(state.get("all_scored_records"))
    chat_history = state.get("chat_history", [])

    try:
        raw = chat_completion(
            messages=[
                {"role": "system", "content": SUPERVISOR_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": build_supervisor_user_prompt(state["raw_query"], has_prior_results, chat_history),
                },
            ],
            temperature=0,
            response_format={"type": "json_object"},
        )
        intent = _parse_intent(raw)
    except Exception:
        logger.exception("Supervisor routing failed; falling back to a safe default intent.")
        intent = dict(DEFAULT_INTENT)
        if not has_prior_results:
            intent["action"] = "full_search"
        else:
            intent["action"] = "clarify"
            intent["clarification_question"] = (
                "I had trouble understanding that — could you rephrase what you'd like me to do "
                "with the current customer list?"
            )

    # An explain/refine action with nothing to work from can't be honored — degrade to clarify
    # rather than silently guessing.
    if intent["action"] in ("refine", "explain") and not has_prior_results:
        intent["action"] = "clarify"
        intent["clarification_question"] = (
            "I don't have a customer list in this session yet — what product and audience should I "
            "search for first?"
        )
    if intent["action"] == "explain" and not intent.get("target_customer_id"):
        intent["action"] = "clarify"
        intent["clarification_question"] = "Which customer would you like me to explain (name or customer ID)?"

    state["intent"] = intent
    return state

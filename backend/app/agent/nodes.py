"""Pipeline nodes. Each wraps a plain tool function from app/tools and only
touches the slice of AgentState it needs — this is what lets the graph route
around nodes (e.g. skip retrieval entirely on a "refine" turn).
"""

import logging

import pandas as pd

from app.agent.state import AgentState
from app.tools.customer_data import CustomerFilters, get_customers
from app.tools.explain import explain_selection
from app.tools.messaging import generate_whatsapp_message
from app.tools.recommend import check_eligibility_and_recommend
from app.tools.scoring import compute_hvc_score, estimate_conversion_probability

logger = logging.getLogger(__name__)

# Composite ranking weight: how much conversion likelihood matters vs. raw
# customer value when ordering the shortlist. Both are 0-100 scales.
COMPOSITE_WEIGHTS = {"hvc": 0.45, "conversion": 0.55}


def _sanitize_records(df: pd.DataFrame) -> list[dict]:
    """Converts a DataFrame to JSON-safe plain-Python records (no numpy scalars)."""
    return df.astype(object).where(pd.notnull(df), None).to_dict(orient="records")


def retrieve_and_score_node(state: AgentState) -> AgentState:
    """Full-search path: pulls the candidate universe and runs the scoring +
    recommendation pipeline over all of it, caching the result in
    `all_scored_records` for later refine/explain turns."""
    intent = state["intent"]
    filters = CustomerFilters(
        city=intent.get("city"),
        segment=intent.get("segment"),
        exclude_active_product_types=[intent["product_type"]],
    )
    customers_df = get_customers(filters)
    logger.info("retrieve_and_score_node: %d candidates after filters", len(customers_df))

    scored_df = compute_hvc_score(customers_df)
    scored_df = estimate_conversion_probability(scored_df, product_type=intent["product_type"])
    scored_df = check_eligibility_and_recommend(scored_df, product_type=intent["product_type"])

    scored_df = scored_df[scored_df["recommended_product"].notna()].copy()
    scored_df["composite_score"] = (
        COMPOSITE_WEIGHTS["hvc"] * scored_df["hvc_score"] + COMPOSITE_WEIGHTS["conversion"] * scored_df["conversion_score"]
    ).round(1)

    state["all_scored_records"] = _sanitize_records(scored_df)
    return state


def rank_and_select_node(state: AgentState) -> AgentState:
    """Selects the top-N from the cached scored universe, applying any
    additional in-memory filters from the current turn's intent (used on
    both full_search and refine paths)."""
    intent = state["intent"]
    records = state.get("all_scored_records", [])
    df = pd.DataFrame(records)

    if df.empty:
        state["top_customers"] = []
        return state

    if intent.get("city"):
        df = df[df["city"].str.lower() == intent["city"].lower()]
    if intent.get("segment"):
        df = df[df["segment"].str.lower() == intent["segment"].lower()]

    df = df.sort_values("composite_score", ascending=False).head(intent.get("top_n", 10))
    state["top_customers"] = _sanitize_records(df)
    return state


def generate_messages_node(state: AgentState) -> AgentState:
    intent = state["intent"]
    generated = dict(state.get("generated_messages", {}))

    for customer in state.get("top_customers", []):
        cid = customer["customer_id"]
        fact_sheet = {
            "customer_id": cid,
            "first_name": customer["name"].split(" ")[0],
            "preferred_language": intent.get("language_override") or customer.get("preferred_language"),
            "segment": customer.get("segment"),
            "recommended_product": customer.get("recommended_product"),
            "recommended_amount": customer.get("recommended_amount"),
            "recommended_rate": customer.get("recommended_rate"),
            "top_conversion_signal": _top_conversion_signal(customer.get("conversion_breakdown", {})),
        }
        result = generate_whatsapp_message(fact_sheet)
        generated[cid] = result

    state["generated_messages"] = generated
    return state


def _top_conversion_signal(breakdown: dict) -> str | None:
    met_signals = [key for key, detail in breakdown.items() if isinstance(detail, dict) and detail.get("met")]
    priority = ["loan_inquiry_signal", "recent_large_discretionary_spend", "salary_regularity", "low_debt_load"]
    for signal in priority:
        if signal in met_signals:
            return signal
    return None


def compose_response_node(state: AgentState) -> AgentState:
    top_customers = state.get("top_customers", [])
    messages = state.get("generated_messages", {})

    if not top_customers:
        state["reply_text"] = (
            "I couldn't find any customers matching that criteria who are eligible and don't "
            "already hold that product. Try widening the city/segment filters."
        )
        return state

    lines = [
        f"Found {len(top_customers)} customers ranked by value + conversion likelihood for "
        f"{state['intent']['product_type'].replace('_', ' ')}:",
        "",
    ]
    for c in top_customers:
        msg = messages.get(c["customer_id"], {}).get("message", "")
        lines.append(
            f"- {c['name']} ({c['customer_id']}, {c['city']}, {c['segment']}) — "
            f"HVC {c['hvc_score']}, conversion {c['conversion_score']}%, "
            f"recommend {c['recommended_product']} (Rs. {c['recommended_amount']:,.0f})"
        )
        if msg:
            lines.append(f"  WhatsApp draft: \"{msg}\"")
    state["reply_text"] = "\n".join(lines)
    return state


def explain_node(state: AgentState) -> AgentState:
    intent = state["intent"]
    target = intent.get("target_customer_id") or ""
    records = state.get("all_scored_records", [])

    match = next((r for r in records if r["customer_id"].lower() == target.lower()), None)
    if match is None:
        match = next((r for r in records if target.lower() in r["name"].lower()), None)

    if match is None:
        state["reply_text"] = (
            f"I couldn't find '{target}' in the current result set. It may not have matched the "
            "search/eligibility criteria used to build this list."
        )
        return state

    state["reply_text"] = explain_selection(match["customer_id"], records)
    return state


def clarify_node(state: AgentState) -> AgentState:
    state["reply_text"] = state["intent"].get(
        "clarification_question", "Could you clarify what you'd like me to do?"
    )
    return state

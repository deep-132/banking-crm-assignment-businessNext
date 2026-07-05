"""Executable spec: wires specs/personal-loan-outreach.feature to pytest-bdd
step definitions, so the Given/When/Then scenarios ARE the test suite, not
just documentation. Each @scenario below picks one scenario out of the
.feature file — scenarios not referenced here (e.g. "No customer qualifies",
"Generated outreach never invents facts") are intentionally left as
documentation-only for now; wire them the same way when they matter.
"""

import json

import pytest
from pytest_bdd import given, scenario, then, when

from app.agent.graph import get_agent_graph
from app.agent.state import AgentState
from app.tools.customer_data import get_products_held

FEATURE = "personal-loan-outreach.feature"


def _fake_chat_completion_factory(responses, call_log=None):
    calls = {"n": 0}

    def _fake(messages, temperature=0.3, response_format=None):
        if call_log is not None:
            call_log.append(messages)
        idx = min(calls["n"], len(responses) - 1)
        calls["n"] += 1
        return responses[idx]

    return _fake


def _intent_json(**overrides):
    base = {
        "action": "full_search",
        "product_type": "personal_loan",
        "city": None,
        "segment": None,
        "top_n": 10,
        "target_customer_id": None,
        "clarification_question": None,
        "language_override": None,
    }
    base.update(overrides)
    return json.dumps(base)


def _fresh_state() -> AgentState:
    return AgentState(
        session_id="bdd-session",
        chat_history=[],
        all_scored_records=[],
        top_customers=[],
        generated_messages={},
    )


@pytest.fixture
def context():
    """Mutable dict passed implicitly between steps of one scenario via closures below."""
    return {}


@given("the CRM database is seeded with synthetic customers, accounts, transactions, products held, loan offers, and interactions")
def seeded_db():
    # Satisfied by the session-scoped autouse fixture in tests/conftest.py.
    pass


# ---------------------------------------------------------------------------
# Scenario: RM discovers high-value customers likely to convert
# ---------------------------------------------------------------------------

@scenario(FEATURE, "RM discovers high-value customers likely to convert")
def test_full_search_scenario():
    pass


@given("the RM has not searched for anything yet in this session", target_fixture="session_state")
def no_prior_search():
    return _fresh_state()


@when("the RM asks to find high-value customers likely to convert for a personal loan and generate WhatsApp messages")
def ask_full_search(session_state, monkeypatch, context):
    monkeypatch.setattr(
        "app.agent.supervisor.chat_completion",
        _fake_chat_completion_factory([_intent_json(top_n=10)]),
    )
    monkeypatch.setattr(
        "app.tools.messaging.chat_completion",
        _fake_chat_completion_factory(["Hi, you're pre-approved for a personal loan!"]),
    )
    session_state["raw_query"] = (
        "Find high-value customers likely to convert for a personal loan this month "
        "and generate personalized WhatsApp messages"
    )
    context["result"] = get_agent_graph().invoke(session_state)


@then("the system returns a scored, ranked list of eligible customers")
def check_ranked_list(context):
    assert context["result"]["all_scored_records"]
    assert context["result"]["top_customers"]


@then("every returned customer excludes anyone who already holds an active personal loan")
def check_excludes_existing_loan_holders(context):
    # Checked against the full scored universe, not just the displayed top N —
    # the exclusion happens at retrieval time, so that's where a regression
    # would actually show up, regardless of which customers happen to rank
    # highest in a given seeded dataset.
    all_ids = [c["customer_id"] for c in context["result"]["all_scored_records"]]
    held = get_products_held(all_ids)
    active_personal_loans = held[(held["status"] == "active") & (held["product_type"] == "personal_loan")]
    assert active_personal_loans.empty, (
        f"found active personal-loan holders in the candidate universe: "
        f"{list(active_personal_loans['customer_id'])}"
    )


@then("every returned customer has a high-value score and a conversion score")
def check_scores_present(context):
    for c in context["result"]["top_customers"]:
        assert "hvc_score" in c and "conversion_score" in c


@then("every returned customer is matched to a recommended loan product and amount")
def check_recommendation_present(context):
    for c in context["result"]["top_customers"]:
        assert c.get("recommended_product")
        assert c.get("recommended_amount")


@then("every returned customer has a generated WhatsApp draft")
def check_whatsapp_draft_present(context):
    result = context["result"]
    for c in result["top_customers"]:
        assert result["generated_messages"].get(c["customer_id"], {}).get("message")


@then("the full scored candidate universe is cached for this session")
def check_universe_cached(context):
    assert len(context["result"]["all_scored_records"]) >= len(context["result"]["top_customers"])


# ---------------------------------------------------------------------------
# Scenario: RM narrows an existing result set
# ---------------------------------------------------------------------------

@scenario(FEATURE, "RM narrows an existing result set")
def test_refine_scenario():
    pass


@given("a full_search has already produced a cached scored universe in this session", target_fixture="session_state")
def prior_full_search(monkeypatch, context):
    monkeypatch.setattr(
        "app.agent.supervisor.chat_completion",
        _fake_chat_completion_factory([_intent_json(top_n=10)]),
    )
    monkeypatch.setattr(
        "app.tools.messaging.chat_completion",
        _fake_chat_completion_factory(["Hi, you're pre-approved for a personal loan!"]),
    )
    state = _fresh_state()
    state["raw_query"] = "Find high-value customers likely to convert for a personal loan"
    result = get_agent_graph().invoke(state)
    context["universe_size_before"] = len(result["all_scored_records"])
    return result


@when("the RM asks to narrow the results to a specific city and a smaller count")
def ask_refine(session_state, monkeypatch, context):
    monkeypatch.setattr(
        "app.agent.supervisor.chat_completion",
        _fake_chat_completion_factory([_intent_json(action="refine", top_n=3)]),
    )
    context["requested_count"] = 3
    session_state["raw_query"] = "Just show me the top 3 in Mumbai"
    context["result"] = get_agent_graph().invoke(session_state)


@then("the system re-ranks and re-filters the cached universe only")
def check_reranked(context):
    assert context["result"]["intent"]["action"] == "refine"


@then("the system does not recompute the scored universe")
def check_universe_unchanged(context):
    assert len(context["result"]["all_scored_records"]) == context["universe_size_before"]


@then("the number of returned customers does not exceed the requested count")
def check_count_bound(context):
    assert len(context["result"]["top_customers"]) <= context["requested_count"]


# ---------------------------------------------------------------------------
# Scenario: RM asks why a customer was selected
# ---------------------------------------------------------------------------

@scenario(FEATURE, "RM asks why a customer was selected")
def test_explain_scenario():
    pass


@when("the RM asks why that specific customer was selected")
def ask_explain(session_state, monkeypatch, context):
    target = session_state["all_scored_records"][0]["customer_id"]
    call_log = []
    monkeypatch.setattr(
        "app.agent.supervisor.chat_completion",
        _fake_chat_completion_factory([_intent_json(action="explain", target_customer_id=target)]),
    )
    monkeypatch.setattr(
        "app.tools.messaging.chat_completion",
        _fake_chat_completion_factory(["should not be called"], call_log=call_log),
    )
    context["messaging_call_log"] = call_log
    session_state["raw_query"] = f"Why was {target} picked?"
    context["result"] = get_agent_graph().invoke(session_state)


@then("the system returns the exact scoring breakdown already computed for that customer")
def check_breakdown_returned(context):
    assert context["result"]["intent"]["action"] == "explain"
    assert "HVC score" in context["result"]["reply_text"]


@then("the system makes no additional LLM call to answer")
def check_no_extra_llm_call(context):
    assert context["messaging_call_log"] == []


# ---------------------------------------------------------------------------
# Scenario: RM asks to explain a customer with no prior search
# ---------------------------------------------------------------------------

@scenario(FEATURE, "RM asks to explain a customer with no prior search")
def test_explain_without_prior_search_scenario():
    pass


@given("no full_search has been run yet in this session", target_fixture="session_state")
def no_full_search_yet():
    return _fresh_state()


@when("the RM asks the system to explain a customer")
def ask_explain_without_context(session_state, monkeypatch, context):
    monkeypatch.setattr(
        "app.agent.supervisor.chat_completion",
        _fake_chat_completion_factory([_intent_json(action="explain", target_customer_id="CUST-0001")]),
    )
    session_state["raw_query"] = "Why was CUST-0001 picked?"
    context["result"] = get_agent_graph().invoke(session_state)


@then("the system asks a clarifying question instead of guessing")
def check_asks_clarifying_question(context):
    assert context["result"]["intent"]["action"] == "clarify"
    assert context["result"]["reply_text"]


@then("the system does not invent a customer or a scoring rationale")
def check_no_invented_customer(context):
    assert context["result"]["top_customers"] == []
    assert context["result"]["all_scored_records"] == []


# ---------------------------------------------------------------------------
# Scenario: RM's request is ambiguous
# ---------------------------------------------------------------------------

@scenario(FEATURE, "RM's request is ambiguous")
def test_ambiguous_request_scenario():
    pass


@given("the RM's message does not contain enough information to choose a route confidently", target_fixture="session_state")
def ambiguous_message_state():
    return _fresh_state()


@when("the router cannot resolve an action")
def router_cannot_resolve(session_state, monkeypatch, context):
    question = "Could you tell me which product and audience you'd like me to search for?"
    monkeypatch.setattr(
        "app.agent.supervisor.chat_completion",
        _fake_chat_completion_factory([_intent_json(action="clarify", clarification_question=question)]),
    )
    context["expected_question"] = question
    session_state["raw_query"] = "do something useful"
    context["result"] = get_agent_graph().invoke(session_state)


@then("the system asks one specific clarifying question")
def check_specific_question(context):
    assert context["result"]["reply_text"] == context["expected_question"]


@then("the system takes no other action until the RM responds")
def check_no_other_action(context):
    assert context["result"]["top_customers"] == []
    assert context["result"]["all_scored_records"] == []

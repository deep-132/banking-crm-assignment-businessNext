import json

import pytest

from app.agent.graph import get_agent_graph
from app.agent.state import AgentState


@pytest.fixture
def fresh_state() -> AgentState:
    return AgentState(
        session_id="test-session",
        chat_history=[],
        all_scored_records=[],
        top_customers=[],
        generated_messages={},
    )


def _fake_chat_completion_factory(responses: list[str]):
    calls = {"n": 0}

    def _fake(messages, temperature=0.3, response_format=None):
        idx = min(calls["n"], len(responses) - 1)
        calls["n"] += 1
        return responses[idx]

    return _fake


def test_full_search_path_produces_ranked_customers(monkeypatch, fresh_state):
    supervisor_json = json.dumps(
        {
            "action": "full_search",
            "product_type": "personal_loan",
            "city": None,
            "segment": None,
            "top_n": 5,
            "target_customer_id": None,
            "clarification_question": None,
            "language_override": None,
        }
    )
    # First call is the supervisor; subsequent calls are per-customer message generation.
    monkeypatch.setattr(
        "app.agent.supervisor.chat_completion",
        _fake_chat_completion_factory([supervisor_json]),
    )
    monkeypatch.setattr(
        "app.tools.messaging.chat_completion",
        _fake_chat_completion_factory(["Hi there, you're pre-approved for a personal loan!"]),
    )

    fresh_state["raw_query"] = "Find high-value customers likely to convert for a personal loan this month"
    result = get_agent_graph().invoke(fresh_state)

    assert result["intent"]["action"] == "full_search"
    assert 0 < len(result["top_customers"]) <= 5
    assert result["all_scored_records"]
    assert "conversion" in result["reply_text"].lower()
    for c in result["top_customers"]:
        assert c["customer_id"] in result["generated_messages"]


def test_refine_reuses_cached_results_without_requerying(monkeypatch, fresh_state):
    supervisor_responses = [
        json.dumps(
            {
                "action": "full_search",
                "product_type": "personal_loan",
                "city": None,
                "segment": None,
                "top_n": 10,
                "target_customer_id": None,
                "clarification_question": None,
                "language_override": None,
            }
        ),
        json.dumps(
            {
                "action": "refine",
                "product_type": "personal_loan",
                "city": None,
                "segment": None,
                "top_n": 3,
                "target_customer_id": None,
                "clarification_question": None,
                "language_override": None,
            }
        ),
    ]
    monkeypatch.setattr(
        "app.agent.supervisor.chat_completion",
        _fake_chat_completion_factory(supervisor_responses),
    )
    monkeypatch.setattr(
        "app.tools.messaging.chat_completion",
        _fake_chat_completion_factory(["Hi there, you're pre-approved for a personal loan!"]),
    )

    fresh_state["raw_query"] = "Find high-value customers likely to convert for a personal loan"
    first_result = get_agent_graph().invoke(fresh_state)

    first_result["raw_query"] = "Just show me the top 3"
    second_result = get_agent_graph().invoke(first_result)

    assert second_result["intent"]["action"] == "refine"
    assert len(second_result["top_customers"]) <= 3
    # The cached universe should be unchanged in size by a pure refine.
    assert len(second_result["all_scored_records"]) == len(first_result["all_scored_records"])


def test_explain_without_prior_results_asks_to_clarify(monkeypatch, fresh_state):
    monkeypatch.setattr(
        "app.agent.supervisor.chat_completion",
        _fake_chat_completion_factory(
            [
                json.dumps(
                    {
                        "action": "explain",
                        "product_type": "personal_loan",
                        "city": None,
                        "segment": None,
                        "top_n": 10,
                        "target_customer_id": "CUST-0001",
                        "clarification_question": None,
                        "language_override": None,
                    }
                )
            ]
        ),
    )

    fresh_state["raw_query"] = "Why was CUST-0001 picked?"
    result = get_agent_graph().invoke(fresh_state)

    assert result["intent"]["action"] == "clarify"
    assert "don't have a customer list" in result["reply_text"]

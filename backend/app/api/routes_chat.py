import logging

from fastapi import APIRouter

from app.agent.graph import get_agent_graph
from app.api.session_store import get_session, reset_all_sessions, save_session
from app.db.database import reset_database
from app.db.seed_data import generate
from app.config import get_settings
from app.models.schemas import ChatRequest, ChatResponse, CustomerResult, SessionHistoryResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api")


def _to_customer_results(top_customers: list[dict], generated_messages: dict[str, dict]) -> list[CustomerResult]:
    results = []
    for c in top_customers:
        msg = generated_messages.get(c["customer_id"], {}).get("message")
        results.append(
            CustomerResult(
                customer_id=c["customer_id"],
                name=c["name"],
                city=c["city"],
                segment=c["segment"],
                hvc_score=c["hvc_score"],
                conversion_score=c["conversion_score"],
                composite_score=c["composite_score"],
                recommended_product=c.get("recommended_product"),
                recommended_amount=c.get("recommended_amount"),
                recommended_rate=c.get("recommended_rate"),
                whatsapp_message=msg,
                hvc_breakdown=c.get("hvc_breakdown"),
                conversion_breakdown=c.get("conversion_breakdown"),
            )
        )
    return results


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    state = get_session(request.session_id)
    state["raw_query"] = request.message
    state.setdefault("chat_history", []).append({"role": "rm", "content": request.message})

    graph = get_agent_graph()
    result_state = graph.invoke(state)

    reply_text = result_state.get("reply_text", "")
    result_state["chat_history"].append({"role": "agent", "content": reply_text})
    save_session(request.session_id, result_state)

    action = result_state["intent"]["action"]
    top_customers = result_state.get("top_customers", []) if action in ("full_search", "refine") else []
    customers = _to_customer_results(top_customers, result_state.get("generated_messages", {}))

    return ChatResponse(
        session_id=request.session_id,
        reply_text=reply_text,
        action=action,
        customers=customers,
    )


@router.get("/sessions/{session_id}", response_model=SessionHistoryResponse)
def get_session_history(session_id: str) -> SessionHistoryResponse:
    state = get_session(session_id)
    customers = _to_customer_results(state.get("top_customers", []), state.get("generated_messages", {}))
    return SessionHistoryResponse(
        session_id=session_id,
        chat_history=state.get("chat_history", []),
        last_customers=customers,
    )


@router.post("/admin/reseed")
def reseed() -> dict[str, str]:
    settings = get_settings()
    reset_database()
    generate(settings.seed_customer_count, settings.seed_random_state)
    reset_all_sessions()
    return {"status": "reseeded"}

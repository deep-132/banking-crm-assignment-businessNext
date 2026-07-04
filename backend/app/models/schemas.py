from typing import Any

from pydantic import BaseModel


class ChatRequest(BaseModel):
    session_id: str
    message: str


class CustomerResult(BaseModel):
    customer_id: str
    name: str
    city: str
    segment: str
    hvc_score: float
    conversion_score: float
    composite_score: float
    recommended_product: str | None = None
    recommended_amount: float | None = None
    recommended_rate: float | None = None
    whatsapp_message: str | None = None
    hvc_breakdown: dict[str, Any] | None = None
    conversion_breakdown: dict[str, Any] | None = None


class ChatResponse(BaseModel):
    session_id: str
    reply_text: str
    action: str
    customers: list[CustomerResult] = []


class SessionHistoryResponse(BaseModel):
    session_id: str
    chat_history: list[dict[str, str]]
    last_customers: list[CustomerResult] = []

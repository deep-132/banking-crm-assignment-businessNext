"""Personalized outreach generation tool.

Generates a WhatsApp-ready message per customer. To avoid hallucinated
personalization, the LLM is given a compact JSON "fact sheet" (only what the
data pipeline actually derived about this customer) and a system prompt that
forbids inventing anything not in that fact sheet — the model's job is
tone/phrasing/language, not fact invention.
"""

import json
import logging

from app.llm_client import chat_completion

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are drafting a short, warm WhatsApp outreach message on behalf of a bank \
Relationship Manager to an existing customer about a personal loan offer.

Rules:
- Use ONLY the facts provided in the customer fact sheet JSON. Never invent a name, amount, rate, \
  or life event that is not present in the fact sheet.
- Reference at most one concrete "reason" signal from the fact sheet (e.g. a recent large expense \
  category, or that they asked about loans) to make it feel personally relevant, without being \
  intrusive about their finances.
- Keep it under 60 words, friendly and professional, in the customer's preferred language if given \
  (default English).
- Include the recommended product name and amount, and invite them to reply or call their RM — do \
  not include a fake phone number or link.
- No emojis unless natural for the language/tone. Output plain text only, no markdown."""


def _build_user_prompt(customer_facts: dict) -> str:
    return (
        "Customer fact sheet (JSON):\n"
        f"{json.dumps(customer_facts, indent=2)}\n\n"
        "Write the WhatsApp message now."
    )


def _fallback_template(customer_facts: dict) -> str:
    """Deterministic fallback used only if the LLM call fails (e.g. missing "
    "Azure OpenAI credentials in a local dev environment) — logged loudly so "
    "it's never mistaken for the primary generation path."""
    name = customer_facts.get("first_name", "there")
    product = customer_facts.get("recommended_product", "a personal loan")
    amount = customer_facts.get("recommended_amount")
    amount_str = f" of up to Rs. {amount:,.0f}" if amount else ""
    return (
        f"Hi {name}, based on your relationship with us, you're pre-qualified for {product}"
        f"{amount_str}. Reply here if you'd like your RM to share the details."
    )


def generate_whatsapp_message(customer_facts: dict, temperature: float = 0.4) -> dict:
    """Returns {message, generation_mode} where generation_mode is 'llm' or 'fallback_template'."""
    try:
        content = chat_completion(
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": _build_user_prompt(customer_facts)},
            ],
            temperature=temperature,
        )
        if not content.strip():
            raise ValueError("Empty completion from Azure OpenAI")
        return {"message": content.strip(), "generation_mode": "llm"}
    except Exception:
        logger.exception(
            "Azure OpenAI message generation failed for customer %s; using fallback template.",
            customer_facts.get("customer_id"),
        )
        return {"message": _fallback_template(customer_facts), "generation_mode": "fallback_template"}

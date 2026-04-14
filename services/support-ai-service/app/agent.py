"""
AI Agent core — intent classification + response generation.
Uses OpenAI GPT when available, falls back to rule-based responses.
"""

import logging
import os
from typing import Any, Optional

from .knowledge_base import GOODBYES, GREETINGS, THANKS, search_kb

log = logging.getLogger(__name__)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# ── Intent types ──────────────────────────────────────────────────────────────
INTENT_GREETING = "greeting"
INTENT_THANKS = "thanks"
INTENT_GOODBYE = "goodbye"
INTENT_FAQ = "faq"
INTENT_TICKET = "ticket"
INTENT_HUMAN = "human"
INTENT_UNKNOWN = "unknown"


def classify_intent(message: str) -> str:
    m = message.lower().strip()

    if any(g in m for g in GREETINGS):
        return INTENT_GREETING
    if any(t in m for t in THANKS):
        return INTENT_THANKS
    if any(b in m for b in GOODBYES):
        return INTENT_GOODBYE
    if any(
        w in m
        for w in [
            "human",
            "agent",
            "person",
            "operator",
            "real person",
            "help me",
        ]
    ):
        return INTENT_HUMAN
    if any(
        w in m
        for w in [
            "ticket",
            "report",
            "bug",
            "create issue",
            "submit",
        ]
    ):
        return INTENT_TICKET

    hits = search_kb(m)
    if hits:
        return INTENT_FAQ

    return INTENT_UNKNOWN


def _call_llm(
    system_prompt: str, user_message: str, history: list[dict[str, Any]]
) -> str:
    """LLM adapter — uses OpenAI GPT-4o when available, falls back to static response."""
    if not OPENAI_API_KEY:
        return _static_fallback(user_message)
    try:
        import openai  # type: ignore[import-untyped]
        client = openai.OpenAI(api_key=OPENAI_API_KEY)
        messages = (
            [{"role": "system", "content": system_prompt}]
            + history[-10:]   # keep last 10 turns for context
            + [{"role": "user", "content": user_message}]
        )
        resp = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            max_tokens=512,
            temperature=0.4,
        )
        return resp.choices[0].message.content or _static_fallback(user_message)
    except Exception as exc:
        log.warning("OpenAI call failed in support agent: %s", exc)
        return _static_fallback(user_message)


def _static_fallback(user_message: str) -> str:
    return (
        "I understand your question. Based on our knowledge base, I recommend checking the relevant "
        "section in your dashboard. If this doesn't resolve the issue, I can create a support ticket "
        "for our team to investigate further. Is there anything else I can help with?"
    )


def generate_response(
    message: str,
    history: list[dict[str, Any]],
    user_email: Optional[str] = None,
) -> tuple[str, str]:
    """
    Returns (response_text, intent).
    """
    intent = classify_intent(message)

    if intent == INTENT_GREETING:
        name_part = f" {user_email.split('@')[0].capitalize()}" if user_email else ""
        return (
            f"Hello{name_part}! 👋 I'm the SelfMonitor support assistant. "
            "I can help with account questions, billing, bank connections, tax submissions, and more. "
            "What can I help you with today?",
            intent,
        )

    if intent == INTENT_THANKS:
        return (
            "You're welcome! 😊 Is there anything else I can help you with?",
            intent,
        )

    if intent == INTENT_GOODBYE:
        return (
            "Goodbye! If you ever need help again, I'm here 24/7. Have a great day! 👋",
            intent,
        )

    if intent == INTENT_HUMAN:
        return (
            "I'll connect you with a human agent right away. "
            "**Expected wait time: under 2 hours** (Mon–Fri, 9am–6pm UK time). "
            "Outside business hours, please submit a support ticket using the form "
            "below and we'll respond by the next business day.",
            intent,
        )

    if intent == INTENT_TICKET:
        return (
            "I can help you create a support ticket. Please use the **Submit a Ticket** form on this page. "
            "Fill in the category, priority, and a description — our team will respond within the SLA for your plan.",
            intent,
        )

    if intent == INTENT_FAQ:
        hits = search_kb(message, top_k=1)
        if hits:
            item = hits[0]
            answer = item["answer"]
            return (
                answer
                + "\n\nIs this what you were looking for? If not, feel free to ask "
                "a follow-up or create a support ticket.",
                intent,
            )

    # Unknown — try LLM
    system = (
        "You are a helpful customer support assistant for SelfMonitor"
        " — a UK FinTech app for self-employed individuals. "
        "Be concise, friendly, and accurate. If you don't know the answer, "
        "say so honestly and offer to create a ticket. "
        "Format responses with markdown for clarity."
    )
    response = _call_llm(system, message, history)
    return response, INTENT_UNKNOWN

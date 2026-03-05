"""
AI Agent core — intent classification + response generation.
Currently uses a rule-based mock. Replace `_call_llm()` with OpenAI/Anthropic call.
"""

import re
from typing import Optional

from .knowledge_base import FAQ, GOODBYES, GREETINGS, THANKS, search_kb

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
            "человек",
            "оператор",
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
            "зарегистрируйте",
            "заявку",
        ]
    ):
        return INTENT_TICKET

    hits = search_kb(m)
    if hits:
        return INTENT_FAQ

    return INTENT_UNKNOWN


def _call_llm(system_prompt: str, user_message: str, history: list[dict]) -> str:
    """
    LLM adapter — MOCK implementation.
    ------------------------------------
    To switch to OpenAI GPT-4o:
        import openai
        client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        messages = [{"role": "system", "content": system_prompt}] + history + [{"role": "user", "content": user_message}]
        resp = client.chat.completions.create(model="gpt-4o", messages=messages)
        return resp.choices[0].message.content

    To switch to Anthropic Claude:
        import anthropic
        client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        resp = client.messages.create(model="claude-3-5-sonnet-20241022", max_tokens=512,
                                      system=system_prompt,
                                      messages=history + [{"role": "user", "content": user_message}])
        return resp.content[0].text
    """
    # --- Mock: echo back a generic helpful message ---
    return (
        "I understand your question. Based on our knowledge base, I recommend checking the relevant "
        "section in your dashboard. If this doesn't resolve the issue, I can create a support ticket "
        "for our team to investigate further. Is there anything else I can help with?"
    )


def generate_response(
    message: str,
    history: list[dict],
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
            "Outside business hours, please submit a support ticket using the form below and we'll respond by the next business day.",
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
                + "\n\nIs this what you were looking for? If not, feel free to ask a follow-up or create a support ticket.",
                intent,
            )

    # Unknown — try LLM
    system = (
        "You are a helpful customer support assistant for SelfMonitor — a UK FinTech app for self-employed individuals. "
        "Be concise, friendly, and accurate. If you don't know the answer, say so honestly and offer to create a ticket. "
        "Format responses with markdown for clarity."
    )
    response = _call_llm(system, message, history)
    return response, INTENT_UNKNOWN

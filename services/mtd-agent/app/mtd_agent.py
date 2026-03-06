"""
MTD Agent — GPT-4 powered HMRC compliance advisor.

Reads pre-computed quarterly data from Redis (written by FinOps Monitor)
and generates human-readable explanations + submission guidance.

Port: 8022
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

import openai

log = logging.getLogger(__name__)

_LANGUAGE_NAMES: dict[str, str] = {
    "en": "English",
    "ru": "Russian",
    "de": "German",
    "fr": "French",
    "es": "Spanish",
    "it": "Italian",
    "pl": "Polish",
    "uk": "Ukrainian",
    "zh": "Chinese",
    "ar": "Arabic",
}


def _language_instruction(lang: str) -> str:
    """Return a GPT instruction to respond in the requested language."""
    if lang == "en":
        return ""
    name = _LANGUAGE_NAMES.get(lang, lang)
    return (
        f"\n\nIMPORTANT: You MUST respond entirely in {name}. "
        f"All explanations, numbers, and recommendations must be in {name}."
    )

OPENAI_API_KEY  = os.getenv("OPENAI_API_KEY", "")
FINOPS_REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")

_SYSTEM_PROMPT = """You are an expert UK tax advisor specializing in Making Tax Digital (MTD) for
Income Tax Self Assessment (ITSA). You help self-employed individuals understand their
quarterly tax obligations under HMRC's MTD ITSA rules that are mandatory from April 2026
for turnover above £50,000.

Always be:
- Accurate with UK tax law and HMRC deadlines
- Clear and jargon-free for non-accountants
- Proactive about upcoming deadlines
- Specific with figures from the user's actual data

MTD ITSA quarterly deadlines (UK tax year starts 6 April):
  Q1 (6 Apr – 5 Jul)  → submit by 5 August
  Q2 (6 Jul – 5 Oct)  → submit by 5 November
  Q3 (6 Oct – 5 Jan)  → submit by 5 February
  Q4 (6 Jan – 5 Apr)  → submit by 5 May

Threshold: £50,000 turnover from April 2026, £30,000 from April 2027.
"""


class MTDAgentResponse:
    def __init__(
        self,
        message: str,
        quarter: str,
        income: float,
        expenses: float,
        net_profit: float,
        mtd_required: bool,
        days_until_deadline: int,
        submission_deadline: str,
        action_required: bool,
        actions: list[str],
    ) -> None:
        self.message             = message
        self.quarter             = quarter
        self.income              = income
        self.expenses            = expenses
        self.net_profit          = net_profit
        self.mtd_required        = mtd_required
        self.days_until_deadline = days_until_deadline
        self.submission_deadline = submission_deadline
        self.action_required     = action_required
        self.actions             = actions

    def to_dict(self) -> dict:
        return {
            "message":             self.message,
            "quarter":             self.quarter,
            "income":              self.income,
            "expenses":            self.expenses,
            "net_profit":          self.net_profit,
            "mtd_required":        self.mtd_required,
            "days_until_deadline": self.days_until_deadline,
            "submission_deadline": self.submission_deadline,
            "action_required":     self.action_required,
            "actions":             self.actions,
        }


class MTDAgent:
    """GPT-4 powered MTD compliance advisor."""

    def __init__(self, redis_client: Any, openai_api_key: str = "") -> None:
        self._redis = redis_client
        # If caller explicitly provides a key (non-None), use it (even if empty).
        # Only fall back to the environment var when nothing was passed at all.
        resolved_key = openai_api_key if openai_api_key is not None else OPENAI_API_KEY
        self._openai = openai.AsyncOpenAI(api_key=resolved_key) if resolved_key else None

    # ── public API ────────────────────────────────────────────────────────────

    async def get_mtd_status(self, user_id: str, language: str = "en") -> MTDAgentResponse:
        """
        Get current quarter MTD status with GPT-4 explanation.
        Reads data from Redis (written by FinOps Monitor).
        """
        quarter_data = await self._fetch_quarter_data(user_id)
        income       = quarter_data.get("income", 0.0)
        expenses     = quarter_data.get("expenses", 0.0)
        net_profit   = round(float(income) - float(expenses), 2)
        mtd_required = float(income) >= 50_000.0
        days_left    = int(quarter_data.get("days_until_deadline", 0))
        deadline     = quarter_data.get("submission_deadline", "")
        quarter_label = quarter_data.get("quarter", "current quarter")
        status       = quarter_data.get("status", "accumulating")

        actions = self._determine_actions(
            income=float(income),
            mtd_required=mtd_required,
            days_left=days_left,
            status=status,
        )
        action_required = len(actions) > 0

        # Generate GPT-4 explanation if API key is available
        message = await self._generate_explanation(
            user_id=user_id,
            quarter=quarter_label,
            income=float(income),
            expenses=float(expenses),
            net_profit=net_profit,
            mtd_required=mtd_required,
            days_left=days_left,
            deadline=deadline,
            actions=actions,
            language=language,
        )

        return MTDAgentResponse(
            message=message,
            quarter=quarter_label,
            income=float(income),
            expenses=float(expenses),
            net_profit=net_profit,
            mtd_required=mtd_required,
            days_until_deadline=days_left,
            submission_deadline=deadline,
            action_required=action_required,
            actions=actions,
        )

    async def answer_question(self, user_id: str, question: str, language: str = "en") -> str:
        """Answer a free-form MTD question using GPT-4 + user context."""
        quarter_data = await self._fetch_quarter_data(user_id)
        context_json = json.dumps(quarter_data, default=str, indent=2)

        prompt = (
            f"User's current MTD data:\n{context_json}\n\n"
            f"User question: {question}"
            f"{_language_instruction(language)}"
        )
        return await self._call_openai(prompt)

    # ── helpers ───────────────────────────────────────────────────────────────

    async def _fetch_quarter_data(self, user_id: str) -> dict:
        """Read latest quarter context from Redis (written by finops-monitor)."""
        from datetime import date
        today = date.today()

        # Determine current tax year
        if today.month > 4 or (today.month == 4 and today.day >= 6):
            year = today.year
        else:
            year = today.year - 1

        # Determine quarter
        m = today.month
        if (today.month == 4 and today.day >= 6) or (5 <= m <= 7) or (m == 7 and today.day <= 5):
            q_num = "Q1"
        elif 7 <= m <= 10:
            q_num = "Q2"
        elif m >= 10 or m <= 1:
            q_num = "Q3"
        else:
            q_num = "Q4"

        tax_year_safe = f"{year}-{str(year + 1)[-2:]}"
        key = f"mtd:quarterly:{user_id}:{tax_year_safe}:{q_num}"
        raw  = await self._redis.hgetall(key)

        # Also get balance context
        balance_raw = await self._redis.hgetall(f"finops:balance:{user_id}")

        result = dict(raw)
        result["balance"] = dict(balance_raw)

        # Compute days_until_deadline if not present
        if "days_until_deadline" not in result:
            from datetime import date as _date
            deadlines = {"Q1": (8, 5), "Q2": (11, 5), "Q3": (2, 5), "Q4": (5, 5)}
            dm, dd = deadlines.get(q_num, (8, 5))
            dl_year = year + 1 if q_num == "Q3" else year
            if q_num in ("Q3", "Q4"):
                dl_year = year + 1
            deadline = _date(dl_year, dm, dd)
            result["days_until_deadline"] = (deadline - today).days
            result["submission_deadline"] = deadline.isoformat()

        tax_year_display = f"{year}/{str(year + 1)[-2:]}"
        result.setdefault("quarter", f"{q_num} {tax_year_display}")
        return result

    def _determine_actions(
        self,
        income: float,
        mtd_required: bool,
        days_left: int,
        status: str,
    ) -> list[str]:
        actions: list[str] = []
        if mtd_required and status != "submitted":
            if days_left <= 0:
                actions.append("URGENT: Submit quarterly MTD return to HMRC immediately — deadline passed!")
            elif days_left <= 7:
                actions.append(f"Submit MTD quarterly return within {days_left} days to avoid late penalty")
            elif days_left <= 30:
                actions.append(f"Prepare MTD quarterly return - due in {days_left} days")
            else:
                # Always surface an action when MTD is required, regardless of lead time
                actions.append(f"MTD quarterly return due in {days_left} days - keep records up to date")
        if not mtd_required and income > 40_000:
            actions.append(f"Turnover approaching £50k MTD threshold (currently £{income:,.0f})")
        return actions

    async def _generate_explanation(
        self,
        user_id: str,
        quarter: str,
        income: float,
        expenses: float,
        net_profit: float,
        mtd_required: bool,
        days_left: int,
        deadline: str,
        actions: list[str],
        language: str = "en",
    ) -> str:
        if self._openai is None:
            # Fallback: template-based explanation (no API key needed)
            return self._template_explanation(
                quarter, income, expenses, net_profit,
                mtd_required, days_left, deadline, actions,
            )

        prompt = (
            f"Provide a concise (3-4 sentences) MTD status update for a UK self-employed person.\n"
            f"Quarter: {quarter}\n"
            f"Income to date: £{income:,.2f}\n"
            f"Expenses to date: £{expenses:,.2f}\n"
            f"Net profit: £{net_profit:,.2f}\n"
            f"MTD required: {'Yes' if mtd_required else 'No'}\n"
            f"Days until submission deadline: {days_left}\n"
            f"Deadline: {deadline}\n"
            f"Required actions: {actions or 'None'}\n\n"
            f"Be specific, encouraging, and action-oriented."
            f"{_language_instruction(language)}"
        )
        return await self._call_openai(prompt)

    def _template_explanation(
        self,
        quarter: str,
        income: float,
        expenses: float,
        net_profit: float,
        mtd_required: bool,
        days_left: int,
        deadline: str,
        actions: list[str],
    ) -> str:
        lines = [
            f"**{quarter} MTD Status**",
            f"Income: £{income:,.2f} | Expenses: £{expenses:,.2f} | Net profit: £{net_profit:,.2f}",
        ]
        if mtd_required:
            lines.append(
                f"MTD ITSA filing is **required** (income ≥ £50,000). "
                f"Submission deadline: {deadline} ({days_left} days remaining)."
            )
        else:
            lines.append(
                f"MTD ITSA not yet required (income below £50,000 threshold). "
                f"Keep monitoring as turnover grows."
            )
        for a in actions:
            lines.append(f"⚠️ {a}")
        return "\n".join(lines)

    async def _call_openai(self, user_prompt: str) -> str:
        if self._openai is None:
            return user_prompt
        try:
            response = await self._openai.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=[
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                max_tokens=400,
                temperature=0.3,
            )
            return response.choices[0].message.content or ""
        except Exception as exc:
            log.error("OpenAI call failed: %s", exc)
            return f"Unable to generate explanation at this time. Raw data available via /mtd/{{}}/status."

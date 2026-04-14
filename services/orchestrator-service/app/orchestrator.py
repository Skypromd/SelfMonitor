"""
Master Orchestrator — 3-level multi-agent AI system.

Level 1: Tool layer  (microservices called as OpenAI tools)
Level 2: Specialist agents (Tax, Finance, Document, Support)
Level 3: Master orchestrator (this module)

Flow: user_message → decompose → parallel agent execution → aggregate → response
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from dataclasses import dataclass, field
from typing import Any

import httpx

log = logging.getLogger(__name__)

# ── Service URLs (docker-internal) ────────────────────────────────────────────
_BASE = {
    "tax":          os.getenv("TAX_ENGINE_URL",          "http://tax-engine:80"),
    "transactions": os.getenv("TRANSACTIONS_SERVICE_URL", "http://transactions-service:80"),
    "documents":    os.getenv("DOCUMENTS_SERVICE_URL",    "http://documents-service:80"),
    "integrations": os.getenv("INTEGRATIONS_SERVICE_URL", "http://integrations-service:80"),
    "support":      os.getenv("SUPPORT_AI_SERVICE_URL",   "http://support-ai-service:8020"),
    "advice":       os.getenv("ADVICE_SERVICE_URL",       "http://advice-service:80"),
    "invoices":     os.getenv("INVOICE_SERVICE_URL",      "http://invoice-service:80"),
    "categorize":   os.getenv("CATEGORIZATION_SERVICE_URL", "http://categorization-service:80"),
}

OPENAI_API_KEY  = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL    = os.getenv("ORCHESTRATOR_MODEL", "gpt-4o")
AGENT_TIMEOUT   = float(os.getenv("AGENT_TIMEOUT_SECONDS", "25"))

# Per-agent kill switch: set AGENT_DISABLED=tax,finance to disable those agents
_DISABLED_AGENTS: set[str] = set(
    os.getenv("AGENT_DISABLED", "").lower().split(",")
) - {""}


# ── Shared HTTP client ─────────────────────────────────────────────────────────

def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


async def _get(url: str, token: str, params: dict | None = None) -> Any:
    async with httpx.AsyncClient(timeout=AGENT_TIMEOUT) as client:
        r = await client.get(url, headers=_headers(token), params=params)
        r.raise_for_status()
        return r.json()


async def _post(url: str, token: str, body: dict) -> Any:
    async with httpx.AsyncClient(timeout=AGENT_TIMEOUT) as client:
        r = await client.post(url, headers=_headers(token), json=body)
        r.raise_for_status()
        return r.json()


# ── Data types ────────────────────────────────────────────────────────────────

@dataclass
class AgentResult:
    agent: str
    success: bool
    data: dict[str, Any]
    summary: str
    confidence: float          # 0.0 – 1.0
    actions_taken: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    elapsed_ms: int = 0


@dataclass
class OrchestratorResponse:
    response: str
    session_id: str
    agents_used: list[str]
    confidence: float
    actions_taken: list[str]
    warnings: list[str]
    agent_results: list[AgentResult]
    processing_time_ms: int


# ── Specialist Agents ──────────────────────────────────────────────────────────

class TaxAgent:
    name = "tax"

    async def run(self, task: str, token: str) -> AgentResult:
        t0 = time.monotonic()
        data: dict[str, Any] = {}
        actions: list[str] = []
        warnings: list[str] = []

        # Always calculate for current UK tax year
        import datetime
        today = datetime.date.today()
        if (today.month, today.day) >= (4, 6):
            start = f"{today.year}-04-06"
            end   = f"{today.year + 1}-04-05"
            year_label = f"{today.year}/{str(today.year + 1)[-2:]}"
        else:
            start = f"{today.year - 1}-04-06"
            end   = f"{today.year}-04-05"
            year_label = f"{today.year - 1}/{str(today.year)[-2:]}"

        try:
            calc = await _post(
                f"{_BASE['tax']}/calculate",
                token,
                {"start_date": start, "end_date": end, "jurisdiction": "UK"},
            )
            data["calculation"] = calc
            actions.append(f"Calculated tax for {year_label}")

            if calc.get("total_income", 0) == 0:
                warnings.append("No income transactions found for this tax year — connect your bank or add transactions.")

            mtd = calc.get("mtd_obligation", {})
            if mtd.get("reporting_required"):
                next_dl = mtd.get("next_deadline")
                if next_dl:
                    actions.append(f"MTD ITSA applies — next deadline {next_dl}")

        except Exception as exc:
            log.warning("TaxAgent calc failed: %s", exc)
            data["error"] = str(exc)
            warnings.append("Tax calculation unavailable — ensure transactions are imported.")

        summary = _build_tax_summary(data.get("calculation"), year_label, warnings)
        confidence = 0.9 if "calculation" in data and not data.get("error") else 0.3

        return AgentResult(
            agent=self.name,
            success="calculation" in data,
            data=data,
            summary=summary,
            confidence=confidence,
            actions_taken=actions,
            warnings=warnings,
            elapsed_ms=int((time.monotonic() - t0) * 1000),
        )


class FinanceAgent:
    name = "finance"

    async def run(self, task: str, token: str) -> AgentResult:
        t0 = time.monotonic()
        data: dict[str, Any] = {}
        actions: list[str] = []
        warnings: list[str] = []

        try:
            txns = await _get(f"{_BASE['transactions']}/transactions/me", token)
            data["transactions"] = txns
            actions.append(f"Loaded {len(txns)} transactions")

            total_income   = sum(t["amount"] for t in txns if t["amount"] > 0)
            total_expenses = sum(abs(t["amount"]) for t in txns if t["amount"] < 0
                                 and not t.get("provider_transaction_id", "").startswith("receipt-draft-"))
            uncategorised  = [t for t in txns if not t.get("category") and t["amount"] < 0
                              and not t.get("provider_transaction_id", "").startswith("receipt-draft-")]

            data["summary"] = {
                "total_income":   round(total_income, 2),
                "total_expenses": round(total_expenses, 2),
                "net_profit":     round(total_income - total_expenses, 2),
                "transaction_count": len(txns),
                "uncategorised_count": len(uncategorised),
            }

            if uncategorised:
                warnings.append(
                    f"{len(uncategorised)} transactions have no category. "
                    "Categorise them in the Transactions page to maximise deductible expenses."
                )

        except Exception as exc:
            log.warning("FinanceAgent transactions failed: %s", exc)
            data["error"] = str(exc)
            warnings.append("Could not load transaction data.")

        # Expense breakdown by category
        if "transactions" in data:
            by_cat: dict[str, float] = {}
            for t in data["transactions"]:
                if t["amount"] < 0 and t.get("category"):
                    cat = t["category"]
                    by_cat[cat] = round(by_cat.get(cat, 0) + abs(t["amount"]), 2)
            data["expenses_by_category"] = dict(
                sorted(by_cat.items(), key=lambda x: x[1], reverse=True)
            )

        summary = _build_finance_summary(data.get("summary"), data.get("expenses_by_category"), warnings)
        confidence = 0.88 if "summary" in data else 0.2

        return AgentResult(
            agent=self.name,
            success="summary" in data,
            data=data,
            summary=summary,
            confidence=confidence,
            actions_taken=actions,
            warnings=warnings,
            elapsed_ms=int((time.monotonic() - t0) * 1000),
        )


class DocumentAgent:
    name = "document"

    async def run(self, task: str, token: str) -> AgentResult:
        t0 = time.monotonic()
        data: dict[str, Any] = {}
        actions: list[str] = []
        warnings: list[str] = []

        # Check review queue and unmatched drafts in parallel
        try:
            review_task  = _get(f"{_BASE['documents']}/documents/review-queue?limit=25", token)
            unmatched_task = _get(
                f"{_BASE['transactions']}/transactions/receipt-drafts/unmatched?limit=25", token
            )
            review_result, unmatched_result = await asyncio.gather(
                review_task, unmatched_task, return_exceptions=True
            )

            if isinstance(review_result, dict):
                data["review_queue"] = review_result
                needs_review = review_result.get("total", 0)
                if needs_review:
                    warnings.append(
                        f"{needs_review} receipt{'s' if needs_review != 1 else ''} need OCR review "
                        "(extracted data may be incorrect — verify before submitting)."
                    )
                    actions.append(f"Found {needs_review} items in OCR review queue")

            if isinstance(unmatched_result, dict):
                data["unmatched_drafts"] = unmatched_result
                unmatched = unmatched_result.get("total", 0)
                if unmatched:
                    warnings.append(
                        f"{unmatched} receipt draft{'s' if unmatched != 1 else ''} not yet matched to a bank transaction. "
                        "Match them in Documents to confirm deductibility."
                    )
                    actions.append(f"Found {unmatched} unmatched receipt drafts")
                else:
                    actions.append("All receipts matched to bank transactions ✓")

        except Exception as exc:
            log.warning("DocumentAgent failed: %s", exc)
            data["error"] = str(exc)
            warnings.append("Could not check document status.")

        summary = _build_document_summary(data, warnings)
        confidence = 0.85 if "review_queue" in data or "unmatched_drafts" in data else 0.2

        return AgentResult(
            agent=self.name,
            success=bool(data and not data.get("error")),
            data=data,
            summary=summary,
            confidence=confidence,
            actions_taken=actions,
            warnings=warnings,
            elapsed_ms=int((time.monotonic() - t0) * 1000),
        )


class SupportAgent:
    name = "support"

    async def run(self, task: str, token: str) -> AgentResult:
        t0 = time.monotonic()
        return AgentResult(
            agent=self.name,
            success=True,
            data={"task": task},
            summary=(
                "For support questions, please use the Support section in the sidebar "
                "or ask the AI assistant directly. Our team responds within 2 hours (Mon–Fri, 9am–6pm UK)."
            ),
            confidence=0.7,
            actions_taken=["Routed to support channel"],
            warnings=[],
            elapsed_ms=int((time.monotonic() - t0) * 1000),
        )


# ── Summary builders ──────────────────────────────────────────────────────────

def _fmt(n: float) -> str:
    return f"£{abs(n):,.2f}"


def _build_tax_summary(calc: dict | None, year: str, warnings: list[str]) -> str:
    if not calc:
        return f"Tax calculation for {year} unavailable. " + (warnings[0] if warnings else "")
    parts = [f"**Tax Year {year}**"]
    parts.append(f"Income: {_fmt(calc.get('total_income', 0))}")
    parts.append(f"Expenses: {_fmt(calc.get('total_expenses', 0))}")
    parts.append(f"Net profit: {_fmt(calc.get('taxable_profit', 0))}")
    due = calc.get("estimated_tax_due", 0)
    parts.append(f"**Total tax & NI due: {_fmt(due)}**")
    if calc.get("payment_on_account_jan", 0) > 0:
        parts.append(
            f"Payments on Account: {_fmt(calc['payment_on_account_jan'])} × 2"
        )
    return "\n".join(parts)


def _build_finance_summary(summary: dict | None, by_cat: dict | None, warnings: list[str]) -> str:
    if not summary:
        return "Financial data unavailable."
    parts = [
        f"Income: {_fmt(summary['total_income'])}",
        f"Expenses: {_fmt(summary['total_expenses'])}",
        f"Net profit: {_fmt(summary['net_profit'])}",
        f"Transactions: {summary['transaction_count']}",
    ]
    if by_cat:
        top3 = list(by_cat.items())[:3]
        parts.append("Top expense categories: " + ", ".join(f"{k} {_fmt(v)}" for k, v in top3))
    return "  |  ".join(parts)


def _build_document_summary(data: dict, warnings: list[str]) -> str:
    parts = []
    rq = data.get("review_queue", {})
    ud = data.get("unmatched_drafts", {})
    needs_review = rq.get("total", 0)
    unmatched    = ud.get("total", 0)
    if needs_review == 0 and unmatched == 0:
        parts.append("All receipts reviewed and matched ✓")
    else:
        if needs_review:
            parts.append(f"{needs_review} receipt(s) need OCR review")
        if unmatched:
            parts.append(f"{unmatched} draft(s) pending bank match")
    return "; ".join(parts) if parts else "Document status checked."


# ── LLM helpers ───────────────────────────────────────────────────────────────

_INTENT_KEYWORDS = {
    "tax":      ["tax", "hmrc", "self assessment", "sa100", "nic", "national insurance",
                 "submit", "return", "deadline", "payment on account", "mtd"],
    "finance":  ["transaction", "income", "expense", "spending", "balance", "cash flow",
                 "invoice", "subscription", "budget", "profit"],
    "document": ["receipt", "scan", "ocr", "document", "upload", "unmatched", "review",
                 "match", "draft"],
    "support":  ["help", "error", "bug", "issue", "contact", "support", "problem"],
}


def _classify_intent(message: str) -> list[str]:
    """Fast keyword-based intent classifier → which agents to invoke."""
    lower = message.lower()
    agents = []
    for agent, keywords in _INTENT_KEYWORDS.items():
        if any(kw in lower for kw in keywords):
            agents.append(agent)
    # Default: tax + finance + document (full report mode)
    if not agents:
        agents = ["tax", "finance", "document"]
    return agents


async def _llm_aggregate(
    user_message: str,
    agent_results: list[AgentResult],
    warnings: list[str],
) -> str:
    """Use GPT-4o to synthesise agent results into a coherent response."""
    if not OPENAI_API_KEY or OPENAI_API_KEY in ("", "your-key-here"):
        return _fallback_aggregate(user_message, agent_results, warnings)

    try:
        from openai import AsyncOpenAI  # type: ignore[import-untyped]
        client = AsyncOpenAI(api_key=OPENAI_API_KEY)

        context_parts = []
        for r in agent_results:
            context_parts.append(f"[{r.agent.upper()} AGENT]\n{r.summary}")
        if warnings:
            context_parts.append("[WARNINGS]\n" + "\n".join(f"• {w}" for w in warnings))

        system = (
            "You are SelfMate, an expert AI financial advisor for UK self-employed individuals. "
            "You are powered by a multi-agent system. Synthesise the specialist agent results below "
            "into a clear, actionable response for the user. Be concise, use numbers, use £ for amounts. "
            "Format using markdown. Always end with 1–3 concrete next steps the user should take. "
            "IMPORTANT: You are providing general guidance, not regulated financial/legal advice."
        )

        resp = await client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": system},
                {"role": "user",   "content": f"User asked: {user_message}\n\nAgent data:\n" + "\n\n".join(context_parts)},
            ],
            max_tokens=800,
            temperature=0.3,
        )
        return resp.choices[0].message.content or _fallback_aggregate(user_message, agent_results, warnings)

    except Exception as exc:
        log.warning("LLM aggregate failed: %s", exc)
        return _fallback_aggregate(user_message, agent_results, warnings)


def _fallback_aggregate(
    user_message: str,
    agent_results: list[AgentResult],
    warnings: list[str],
) -> str:
    """Used when OpenAI is unavailable — structured static aggregation."""
    lines = ["Here's your financial summary:\n"]
    for r in agent_results:
        if r.success and r.summary:
            lines.append(r.summary)
    if warnings:
        lines.append("\n**Action required:**")
        for w in warnings:
            lines.append(f"• {w}")
    lines.append("\n**Next steps:** Visit Tax Return page → review warnings → submit to HMRC.")
    return "\n".join(lines)


# ── Master Orchestrator ───────────────────────────────────────────────────────

class MasterOrchestrator:
    """
    Level 3: decomposes user request → routes to specialist agents → aggregates.
    """

    def __init__(self) -> None:
        self._agents: dict[str, TaxAgent | FinanceAgent | DocumentAgent | SupportAgent] = {
            "tax":      TaxAgent(),
            "finance":  FinanceAgent(),
            "document": DocumentAgent(),
            "support":  SupportAgent(),
        }

    def agent_status(self) -> dict[str, bool]:
        return {name: name not in _DISABLED_AGENTS for name in self._agents}

    async def handle(
        self,
        user_message: str,
        token: str,
        session_id: str,
    ) -> OrchestratorResponse:
        t0 = time.monotonic()

        # 1. Intent classification (fast keyword route + optional LLM)
        target_agents = [
            a for a in _classify_intent(user_message)
            if a not in _DISABLED_AGENTS
        ]

        if not target_agents:
            target_agents = ["finance"]   # safe default

        log.info("Orchestrator routing to agents: %s", target_agents)

        # 2. Execute specialist agents in parallel
        agent_tasks = [
            self._agents[name].run(user_message, token)
            for name in target_agents
            if name in self._agents
        ]
        results: list[AgentResult] = await asyncio.gather(*agent_tasks)

        # 3. Collect all warnings
        all_warnings: list[str] = []
        for r in results:
            all_warnings.extend(r.warnings)
        all_warnings = list(dict.fromkeys(all_warnings))  # deduplicate, preserve order

        # 4. Aggregate with LLM
        response_text = await _llm_aggregate(user_message, results, all_warnings)

        # 5. Overall confidence = weighted average
        if results:
            confidence = sum(r.confidence for r in results) / len(results)
        else:
            confidence = 0.0

        all_actions = [a for r in results for a in r.actions_taken]

        return OrchestratorResponse(
            response=response_text,
            session_id=session_id,
            agents_used=[r.agent for r in results],
            confidence=round(confidence, 3),
            actions_taken=all_actions,
            warnings=all_warnings,
            agent_results=results,
            processing_time_ms=int((time.monotonic() - t0) * 1000),
        )

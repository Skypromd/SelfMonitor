"""
MTD ITSA quarterly report builder.

Builds, stores, and retrieves HMRC-compatible quarterly summary reports.
Report format follows the HMRC MTD Income Tax Self Assessment API spec:
  POST /individuals/self-assessment/income-tax/period-summaries/{nino}/{taxYear}

Redis key:  mtd:report:{user_id}:{tax_year}:{quarter_num}
            (JSON-encoded dict, 400-day TTL)
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

_REPORT_KEY_PREFIX = "mtd:report"
_REPORT_TTL_SECONDS = 400 * 24 * 3600   # 400 days


def _report_key(user_id: str, quarter_label: str, tax_year: str) -> str:
    """e.g. mtd:report:user123:2026-27:Q1"""
    safe_year = tax_year.replace("/", "-")
    q_num = quarter_label.split()[0]
    return f"{_REPORT_KEY_PREFIX}:{user_id}:{safe_year}:{q_num}"


# ── builder ──────────────────────────────────────────────────────────────────

def build_report(
    *,
    user_id: str,
    nino: str,               # National Insurance number
    utr: str,                # Unique Taxpayer Reference
    quarter_label: str,      # e.g. "Q1 2026/27"
    tax_year: str,           # e.g. "2026/27"
    period_start: str,       # ISO date string
    period_end: str,         # ISO date string
    submission_deadline: str,
    income_total: float,
    expenses_total: float,
    income_breakdown: dict | None = None,
    expenses_breakdown: dict | None = None,
) -> dict:
    """
    Construct an HMRC-compatible MTD quarterly summary report dict.

    income_breakdown / expenses_breakdown are optional dicts with
    category → amount mappings (e.g. {"turnover": 15000.00, ...}).
    """
    income_breakdown  = income_breakdown  or {"turnover": income_total}
    expenses_breakdown = expenses_breakdown or {
        "costOfGoods":            0.0,
        "cisPayments":            0.0,
        "allowableExpenses":      expenses_total,
    }

    net_profit = round(income_total - expenses_total, 2)
    tax_year_hmrc = _format_tax_year_for_hmrc(tax_year)  # "2026-27"

    report = {
        # Identifiers
        "user_id":           user_id,
        "nino":              nino,
        "utr":               utr,
        "quarter":           quarter_label,
        "tax_year":          tax_year,
        "tax_year_hmrc":     tax_year_hmrc,

        # Period
        "period_start":      period_start,
        "period_end":        period_end,
        "submission_deadline": submission_deadline,

        # Financials
        "income": {
            "total":     round(income_total, 2),
            **income_breakdown,
        },
        "expenses": {
            "total":     round(expenses_total, 2),
            **expenses_breakdown,
        },
        "net_profit": net_profit,

        # Metadata
        "status":       "draft",   # draft | ready | submitted
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "submitted_at": None,
        "hmrc_reference": None,    # populated on successful HMRC submission
    }
    return report


def _format_tax_year_for_hmrc(tax_year: str) -> str:
    """Convert '2026/27' → '2026-27' (HMRC API format)."""
    return tax_year.replace("/", "-")


# ── Redis persistence ─────────────────────────────────────────────────────────

async def save_report(redis_client: Any, report: dict) -> None:
    """Persist report JSON to Redis with TTL."""
    key = _report_key(
        report["user_id"],
        report["quarter"],
        report["tax_year"],
    )
    await redis_client.setex(key, _REPORT_TTL_SECONDS, json.dumps(report))


async def load_report(
    redis_client: Any,
    user_id: str,
    quarter_label: str,
    tax_year: str,
) -> dict | None:
    """Load a report from Redis; returns None if not found."""
    key = _report_key(user_id, quarter_label, tax_year)
    raw = await redis_client.get(key)
    if raw is None:
        return None
    return json.loads(raw)


async def mark_submitted(
    redis_client: Any,
    user_id: str,
    quarter_label: str,
    tax_year: str,
    hmrc_reference: str,
) -> dict | None:
    """Update an existing report as submitted and record the HMRC reference."""
    report = await load_report(redis_client, user_id, quarter_label, tax_year)
    if report is None:
        return None
    report["status"] = "submitted"
    report["submitted_at"] = datetime.now(timezone.utc).isoformat()
    report["hmrc_reference"] = hmrc_reference
    await save_report(redis_client, report)
    return report


# ── validation ───────────────────────────────────────────────────────────────

def validate_report(report: dict) -> list[str]:
    """
    Basic validation before HMRC submission.
    Returns a list of error strings (empty = valid).
    """
    errors: list[str] = []
    required = ["nino", "utr", "quarter", "period_start", "period_end"]
    for field in required:
        if not report.get(field):
            errors.append(f"Missing required field: {field}")

    if report.get("income", {}).get("total", 0) < 0:
        errors.append("Income total cannot be negative")

    if report.get("expenses", {}).get("total", 0) < 0:
        errors.append("Expenses total cannot be negative")

    return errors

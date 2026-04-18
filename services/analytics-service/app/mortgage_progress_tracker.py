"""
Mortgage journey timeline — informational progress only (not lending or advice).

Steps are derived from simple heuristics and optional user-reported fields.
"""

from __future__ import annotations

import math
from typing import Any, Literal

CreditFocus = Literal["unknown", "ok", "building"]
DebtsPriority = Literal["unknown", "managing", "reduce_first"]


def _months_span_from_dates(earliest_iso: str | None, latest_iso: str | None) -> int | None:
    if not earliest_iso or not latest_iso:
        return None
    try:
        from datetime import date

        def _parse(d: str) -> date:
            return date.fromisoformat(d[:10])

        a, b = _parse(earliest_iso), _parse(latest_iso)
        if b < a:
            a, b = b, a
        return max(0, (b - a).days // 30)
    except Exception:
        return None


def estimate_self_employed_years(months_bank_history: int | None) -> float | None:
    if months_bank_history is None or months_bank_history <= 0:
        return None
    return round(months_bank_history / 12.0, 1)


def build_mortgage_progress_timeline(
    *,
    credit_focus: CreditFocus = "unknown",
    deposit_saved_gbp: float | None = None,
    deposit_target_gbp: float | None = None,
    monthly_savings_gbp: float | None = None,
    debts_priority: DebtsPriority = "unknown",
    tax_return_filed: bool | None = None,
    self_employed_years_override: float | None = None,
    months_bank_history: int | None = None,
    document_count: int | None = None,
    mortgage_readiness_percent: int | None = None,
) -> dict[str, Any]:
    years_est = self_employed_years_override
    if years_est is None:
        years_est = estimate_self_employed_years(months_bank_history)

    credit_done = credit_focus == "ok"
    credit_detail = (
        "You indicated credit file is in good shape for planning."
        if credit_done
        else (
            "Focus on credit health (electoral roll, limits, payment history) — speak to a broker if unsure."
            if credit_focus == "building"
            else "Confirm your credit position with a broker before applying."
        )
    )

    dep_saved = deposit_saved_gbp if deposit_saved_gbp is not None else None
    dep_target = deposit_target_gbp if deposit_target_gbp is not None else None
    dep_ratio = None
    dep_done = False
    if dep_target and dep_target > 0 and dep_saved is not None:
        dep_ratio = min(1.0, max(0.0, dep_saved / dep_target))
        dep_done = dep_saved >= dep_target * 0.995
    dep_detail = (
        f"About {dep_ratio * 100:.0f}% of your deposit goal (£{dep_saved:,.0f} / £{dep_target:,.0f})."
        if dep_ratio is not None
        else "Set a deposit target and tracked savings in MyNetTax to monitor progress."
    )

    acc_done = False
    acc_detail = "Connect bank data or add trading history."
    if years_est is not None:
        acc_done = years_est >= 2.0 - 1e-6
        acc_detail = (
            f"~{years_est} years of records suggested from bank history."
            if years_est < 2
            else "At least ~2 years of self-employed records is a common lender ask — keep filings consistent."
        )
    elif months_bank_history is not None and months_bank_history >= 22:
        acc_done = True
        acc_detail = "Roughly 2 years of transaction history detected."

    tax_done = tax_return_filed is True
    tax_detail = (
        "SA302 / tax year evidence is part of most self-employed applications."
        if not tax_done
        else "You indicated your tax return is filed — keep SA302 / overviews ready."
    )

    debts_done = debts_priority != "reduce_first"
    debts_detail = (
        "Pay down high-interest debt where possible before a full application — illustrative planning only."
        if not debts_done
        else "Debt strategy looks manageable for planning — confirm with a broker."
    )

    read = max(0, min(100, int(mortgage_readiness_percent or 0)))
    pack_done = read >= 72
    pack_detail = (
        f"Mortgage pack readiness ~{read}% — upload and refresh checklist in Reports."
        if document_count is not None
        else f"Mortgage pack readiness ~{read}% — use document checklist and readiness tools."
    )
    if read >= 72:
        pack_detail = f"Readiness ~{read}% — review with a broker before submission."

    apply_done = read >= 92
    apply_detail = (
        "When your broker confirms, submit the formal mortgage application."
        if not apply_done
        else "Illustrative: high readiness — broker-led application stage."
    )

    raw_steps: list[dict[str, Any]] = [
        {
            "id": "credit",
            "title": "Credit profile",
            "detail": credit_detail,
            "done": credit_done,
        },
        {
            "id": "deposit",
            "title": "Save deposit",
            "detail": dep_detail,
            "done": dep_done,
            "progress_ratio": dep_ratio,
        },
        {
            "id": "accounts",
            "title": "Self-employed accounts (1–2 years)",
            "detail": acc_detail,
            "done": acc_done,
        },
        {
            "id": "tax_return",
            "title": "Tax return & SA302 evidence",
            "detail": tax_detail,
            "done": tax_done,
        },
        {
            "id": "debts",
            "title": "Manage debts",
            "detail": debts_detail,
            "done": debts_done,
        },
        {
            "id": "mortgage_pack",
            "title": "Prepare mortgage pack",
            "detail": pack_detail,
            "done": pack_done,
        },
        {
            "id": "apply",
            "title": "Apply (via broker)",
            "detail": apply_detail,
            "done": apply_done,
        },
    ]

    steps_out: list[dict[str, Any]] = []
    current_id: str | None = None
    seen_incomplete = False
    for s in raw_steps:
        if s["done"]:
            st = "completed"
        elif not seen_incomplete:
            st = "current"
            current_id = s["id"]
            seen_incomplete = True
        else:
            st = "upcoming"
        row = {**s, "status": st}
        row.setdefault("progress_ratio", None)
        steps_out.append(row)

    est_months: int | None = None
    est_note: str | None = None
    if (
        dep_target
        and dep_target > 0
        and dep_saved is not None
        and dep_saved < dep_target
        and monthly_savings_gbp
        and monthly_savings_gbp > 0
    ):
        gap = dep_target - dep_saved
        est_months = max(1, int(math.ceil(gap / monthly_savings_gbp)))
        est_note = (
            f"At ~£{monthly_savings_gbp:,.0f}/month saved, deposit gap may close in ~{est_months} month(s) "
            "(illustrative only)."
        )

    disclaimer = (
        "Timeline is for motivation and planning — not a lender timeline, offer, or regulated mortgage advice."
    )

    return {
        "steps": steps_out,
        "current_step_id": current_id,
        "signals": {
            "months_bank_history": months_bank_history,
            "document_count": document_count,
            "self_employed_years_estimate": years_est,
            "mortgage_readiness_percent": read,
            "deposit_progress_ratio": dep_ratio,
        },
        "estimated_months_to_deposit_goal": est_months,
        "estimated_timeline_note": est_note,
        "disclaimer": disclaimer,
    }


def merge_backend_signals(
    payload: dict[str, Any],
    *,
    transactions: list[dict[str, Any]] | None,
    documents: list[dict[str, Any]] | None,
) -> dict[str, Any]:
    """Fill missing months_bank_history / document_count from live services."""
    months = payload.get("months_bank_history")
    doc_n = payload.get("document_count")
    if transactions and months is None:
        dates = [t.get("date") for t in transactions if t.get("date")]
        if len(dates) >= 2:
            earliest = str(min(str(d) for d in dates))
            latest = str(max(str(d) for d in dates))
            months = _months_span_from_dates(earliest, latest)
    if documents is not None and doc_n is None:
        doc_n = len(documents)
    out = {**payload}
    if months is not None:
        out["months_bank_history"] = months
    if doc_n is not None:
        out["document_count"] = doc_n
    return out

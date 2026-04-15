"""
Regulatory Service — Single source of truth for UK tax rules, rates, and deadlines.

All agents and services fetch rates, thresholds and deadlines from here instead
of hardcoding them. When HMRC changes a rate, only the JSON data file is updated.

Endpoints:
  GET  /health
  GET  /rules/tax-year/{year}               — all rules for a tax year (e.g. "2025-26")
  GET  /rules/active                        — rules effective on ?date= (default: today)
  GET  /rules/mtd/threshold                 — MTD obligation check for income + year
  GET  /rules/deadlines                     — statutory deadlines for a tax year
  GET  /rules/rates/income-tax              — income tax bands + rates
  GET  /rules/rates/ni                      — National Insurance rates
  GET  /rules/rates/vat                     — VAT thresholds and rates
  GET  /rules/allowable-expenses            — full HMRC SA103F expense categories
  GET  /rules/changes                       — regulatory changes since a date
  POST /rules/analyze-user                  — AI: personalised impact analysis
  GET  /rules/versions                      — rule file versions and status
"""

from __future__ import annotations

import json
import logging
import os
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent / "data"
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")

# ── Tax year JSON files available ───────────────────────────────────────────
_RULE_FILES: Dict[str, str] = {
    "2024-25": "uk_tax_2024_25.json",
    "2025-26": "uk_tax_2025_26.json",
    "2026-27": "uk_tax_2026_27.json",
}

_rules_cache: Dict[str, Dict[str, Any]] = {}


def _load_rules(tax_year: str) -> Dict[str, Any]:
    if tax_year in _rules_cache:
        return _rules_cache[tax_year]
    filename = _RULE_FILES.get(tax_year)
    if not filename:
        raise HTTPException(status_code=404, detail=f"No rules found for tax year {tax_year!r}")
    path = DATA_DIR / filename
    if not path.exists():
        raise HTTPException(status_code=500, detail=f"Rule file missing: {filename}")
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    _rules_cache[tax_year] = data
    return data


def _tax_year_for_date(d: date) -> str:
    """Return the UK tax year string (e.g. '2025-26') for a given date."""
    if d >= date(d.year, 4, 6):
        return f"{d.year}-{str(d.year + 1)[2:]}"
    return f"{d.year - 1}-{str(d.year)[2:]}"


def _all_loaded_rules() -> List[Dict[str, Any]]:
    result = []
    for year in _RULE_FILES:
        try:
            result.append(_load_rules(year))
        except Exception:
            pass
    return result


# ── FastAPI app ──────────────────────────────────────────────────────────────

app = FastAPI(
    title="Regulatory Service",
    description="UK tax rules, rates, thresholds and deadlines — single source of truth",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Models ───────────────────────────────────────────────────────────────────

class MtdThresholdResponse(BaseModel):
    tax_year: str
    income: float
    mtd_required: bool
    threshold: Optional[float]
    mandatory_from: Optional[str]
    notes: str
    warning: Optional[str] = None


class UserAnalysisRequest(BaseModel):
    estimated_annual_income: float
    tax_year: str = "2025-26"
    has_student_loan: bool = False
    student_loan_plan: Optional[str] = None
    is_married: bool = False
    has_rental_income: bool = False
    has_dividends: bool = False
    additional_context: Optional[str] = None


class RuleChangeItem(BaseModel):
    area: str
    description: str
    impact: str
    affects: str
    action_required: Optional[str] = None


class RuleVersion(BaseModel):
    tax_year: str
    version: str
    status: str
    source: str
    effective_from: str
    effective_to: str


# ── Health ───────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    available_years = list(_RULE_FILES.keys())
    return {"status": "ok", "service": "regulatory-service", "available_tax_years": available_years}


# ── REG.3: Full rules for a tax year ─────────────────────────────────────────

@app.get("/rules/tax-year/{year}")
async def get_tax_year_rules(year: str) -> Dict[str, Any]:
    """
    Return complete UK tax rules for a given tax year.
    Format: '2025-26', '2024-25', '2026-27'
    """
    return _load_rules(year)


# ── REG.4: Rules active on a specific date ───────────────────────────────────

@app.get("/rules/active")
async def get_active_rules(
    date_str: Optional[str] = Query(None, alias="date", description="ISO date e.g. 2026-04-06")
) -> Dict[str, Any]:
    """Return the tax rules that are active on the given date (default: today)."""
    if date_str:
        try:
            d = date.fromisoformat(date_str)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid date format: {date_str!r}. Use YYYY-MM-DD.")
    else:
        d = date.today()

    tax_year = _tax_year_for_date(d)
    rules = _load_rules(tax_year)
    rules["_query_date"] = d.isoformat()
    rules["_resolved_tax_year"] = tax_year
    return rules


# ── REG.5: MTD obligation check ──────────────────────────────────────────────

@app.get("/rules/mtd/threshold", response_model=MtdThresholdResponse)
async def get_mtd_threshold(
    income: float = Query(..., description="Estimated annual trading income in GBP"),
    year: str = Query("2025-26", description="Tax year e.g. '2025-26'"),
) -> MtdThresholdResponse:
    """Check whether MTD ITSA applies for a given income level and tax year."""
    rules = _load_rules(year)
    mtd = rules.get("mtd_itsa", {})
    threshold = mtd.get("threshold")
    mandatory_from = mtd.get("mandatory_from")
    notes = mtd.get("notes", "")

    mtd_required = bool(threshold and income >= threshold and mandatory_from)

    # Forward-looking warning: check next year's threshold
    warning = None
    next_year_map = {"2024-25": "2025-26", "2025-26": "2026-27"}
    next_year = next_year_map.get(year)
    if next_year and not mtd_required:
        try:
            next_rules = _load_rules(next_year)
            next_threshold = next_rules.get("mtd_itsa", {}).get("threshold")
            next_mandatory = next_rules.get("mtd_itsa", {}).get("mandatory_from")
            if next_threshold and income >= next_threshold and next_mandatory:
                warning = (
                    f"MTD ITSA will be mandatory for you from {next_mandatory} "
                    f"(income £{income:,.0f} ≥ £{next_threshold:,} threshold for {next_year}). "
                    f"Prepare MTD-compatible software now."
                )
        except Exception:
            pass

    return MtdThresholdResponse(
        tax_year=year,
        income=income,
        mtd_required=mtd_required,
        threshold=threshold,
        mandatory_from=mandatory_from,
        notes=notes,
        warning=warning,
    )


# ── REG.6: Deadlines ─────────────────────────────────────────────────────────

@app.get("/rules/deadlines")
async def get_deadlines(
    year: str = Query("2025-26", description="Tax year e.g. '2025-26'"),
    type_filter: Optional[str] = Query(None, alias="type", description="Filter: deadline | payment | action | mtd_quarterly"),
) -> Dict[str, Any]:
    """Return all statutory deadlines for a tax year, optionally filtered by type."""
    rules = _load_rules(year)
    deadlines = rules.get("deadlines", [])
    if type_filter:
        deadlines = [d for d in deadlines if d.get("type") == type_filter]
    today = date.today().isoformat()
    for dl in deadlines:
        dl_date = dl.get("date", "")
        if dl_date:
            dl["days_until"] = (date.fromisoformat(dl_date) - date.today()).days
            dl["overdue"] = dl_date < today
    return {"tax_year": year, "deadlines": deadlines, "as_of": today}


# ── REG.7: Rates: income tax ─────────────────────────────────────────────────

@app.get("/rules/rates/income-tax")
async def get_income_tax_rates(
    year: str = Query("2025-26"),
) -> Dict[str, Any]:
    """Return income tax bands, rates, personal allowance for a tax year."""
    rules = _load_rules(year)
    return {
        "tax_year": year,
        "income_tax": rules.get("income_tax", {}),
    }


@app.get("/rules/rates/ni")
async def get_ni_rates(
    year: str = Query("2025-26"),
) -> Dict[str, Any]:
    """Return National Insurance rates (Class 2 and Class 4) for a tax year."""
    rules = _load_rules(year)
    return {
        "tax_year": year,
        "national_insurance": rules.get("national_insurance", {}),
    }


@app.get("/rules/rates/vat")
async def get_vat_rates(
    year: str = Query("2025-26"),
) -> Dict[str, Any]:
    """Return VAT thresholds and rates."""
    rules = _load_rules(year)
    return {
        "tax_year": year,
        "vat": rules.get("vat", {}),
    }


# ── REG.7: Allowable expenses ────────────────────────────────────────────────

@app.get("/rules/allowable-expenses")
async def get_allowable_expenses(
    year: str = Query("2025-26"),
) -> Dict[str, Any]:
    """
    Return full list of HMRC SA103F allowable expense categories
    with box numbers and descriptions.
    """
    rules = _load_rules(year)
    expenses = rules.get("allowable_expenses", {})
    # Also return the expense category codes as a flat list for easy use
    codes = [c["code"] for c in expenses.get("categories", [])]
    return {
        "tax_year": year,
        "allowable_expenses": expenses,
        "deductible_category_codes": codes,
    }


# ── Allowances ───────────────────────────────────────────────────────────────

@app.get("/rules/allowances")
async def get_allowances(year: str = Query("2025-26")) -> Dict[str, Any]:
    """Return all tax allowances: trading, dividend, capital gains, marriage, AIA."""
    rules = _load_rules(year)
    return {"tax_year": year, "allowances": rules.get("allowances", {})}


@app.get("/rules/student-loans")
async def get_student_loan_rates(year: str = Query("2025-26")) -> Dict[str, Any]:
    """Return student loan repayment thresholds and rates for all plans."""
    rules = _load_rules(year)
    return {"tax_year": year, "student_loans": rules.get("student_loans", {})}


# ── REG: Changes since a date ────────────────────────────────────────────────

@app.get("/rules/changes")
async def get_regulatory_changes(
    since: str = Query(..., description="ISO date e.g. '2025-01-01'"),
) -> Dict[str, Any]:
    """
    Return regulatory changes across all tax years since the given date.
    Useful for the admin Regulatory Dashboard and AI Regulatory Agent.
    """
    try:
        since_date = date.fromisoformat(since)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid date: {since!r}")

    changes: List[Dict[str, Any]] = []
    for rules in _all_loaded_rules():
        eff_from = rules.get("effective_from", "")
        if eff_from and date.fromisoformat(eff_from) >= since_date:
            for change in rules.get("regulatory_changes_from_prior_year", []):
                changes.append({
                    "tax_year": rules["tax_year"],
                    "effective_from": eff_from,
                    "status": rules.get("status"),
                    **change,
                })

    return {"since": since, "changes": changes, "total": len(changes)}


# ── REG.10: AI personalised analysis ─────────────────────────────────────────

@app.post("/rules/analyze-user")
async def analyze_user(req: UserAnalysisRequest) -> Dict[str, Any]:
    """
    AI-powered personalised regulatory impact analysis.
    Returns plain-language summary of what rules apply, what changes affect this user,
    and recommended actions.
    Falls back to rule-based analysis when OpenAI is not configured.
    """
    rules = _load_rules(req.tax_year)
    income_tax = rules.get("income_tax", {})
    ni = rules.get("national_insurance", {})
    mtd = rules.get("mtd_itsa", {})
    allowances = rules.get("allowances", {})
    deadlines = rules.get("deadlines", [])

    # Rule-based analysis (always runs)
    pa = income_tax.get("personal_allowance", 12570)
    bands = income_tax.get("bands", [])
    taper_threshold = income_tax.get("personal_allowance_taper_threshold", 100000)

    applicable_rules = []
    warnings = []
    actions = []

    # Determine tax bands applicable to this income
    taxable = max(0, req.estimated_annual_income - pa)
    if req.estimated_annual_income > taper_threshold:
        taper = min(pa, (req.estimated_annual_income - taper_threshold) / 2)
        taxable = max(0, req.estimated_annual_income - (pa - taper))
        warnings.append(
            f"Personal Allowance is tapered because your income exceeds £{taper_threshold:,}. "
            f"You lose £1 of allowance for every £2 over £{taper_threshold:,}."
        )

    estimated_tax = 0.0
    for band in bands:
        band_from = band.get("from", 0)
        band_to = band.get("to")
        rate = band.get("rate", 0)
        band_max = band_to if band_to else float("inf")
        taxable_in_band = max(0, min(taxable, band_max) - band_from)
        if taxable_in_band > 0:
            tax_in_band = taxable_in_band * rate
            estimated_tax += tax_in_band
            applicable_rules.append({
                "rule": f"{band['name'].title()} rate income tax",
                "rate": f"{int(rate * 100)}%",
                "on": f"£{taxable_in_band:,.0f}",
                "tax": f"£{tax_in_band:,.0f}",
            })

    # Class 4 NI
    class4 = ni.get("class_4", {})
    lpl = class4.get("lower_profits_limit", 12570)
    upl = class4.get("upper_profits_limit", 50270)
    main_rate = class4.get("main_rate", 0.06)
    add_rate = class4.get("additional_rate", 0.02)
    if req.estimated_annual_income > lpl:
        ni_main = min(req.estimated_annual_income - lpl, upl - lpl) * main_rate
        ni_add = max(0, req.estimated_annual_income - upl) * add_rate
        estimated_tax += ni_main + ni_add
        applicable_rules.append({
            "rule": "Class 4 NI",
            "rate": f"{int(main_rate * 100)}% / {int(add_rate * 100)}%",
            "on": f"£{req.estimated_annual_income:,.0f}",
            "tax": f"£{ni_main + ni_add:,.0f}",
        })

    # Class 2 NI
    class2 = ni.get("class_2", {})
    if req.estimated_annual_income >= class2.get("lower_profits_limit", 12570):
        class2_annual = class2.get("weekly_rate", 3.45) * 52
        estimated_tax += class2_annual
        applicable_rules.append({
            "rule": "Class 2 NI",
            "rate": f"£{class2.get('weekly_rate', 3.45)}/week",
            "on": "52 weeks",
            "tax": f"£{class2_annual:.2f}",
        })

    # MTD warning
    mtd_threshold = mtd.get("threshold")
    mtd_mandatory = mtd.get("mandatory_from")
    if mtd_threshold and req.estimated_annual_income >= mtd_threshold and mtd_mandatory:
        warnings.append(
            f"MTD ITSA is MANDATORY for you from {mtd_mandatory} "
            f"(income £{req.estimated_annual_income:,.0f} ≥ threshold £{mtd_threshold:,}). "
            "You must submit quarterly digital updates."
        )
        actions.append("Set up MTD-compatible accounting software before " + mtd_mandatory)
    elif mtd_threshold and req.estimated_annual_income >= mtd_threshold * 0.8:
        warnings.append(
            f"Your income is approaching the MTD ITSA threshold of £{mtd_threshold:,}. "
            f"If income grows you will need MTD compliance from {mtd_mandatory}."
        )

    # Student loan
    if req.has_student_loan and req.student_loan_plan:
        sl_data = rules.get("student_loans", {}).get(req.student_loan_plan, {})
        if sl_data:
            sl_threshold = sl_data.get("threshold", 0)
            sl_rate = sl_data.get("rate", 0.09)
            if req.estimated_annual_income > sl_threshold:
                sl_repayment = max(0, req.estimated_annual_income - sl_threshold) * sl_rate
                estimated_tax += sl_repayment
                applicable_rules.append({
                    "rule": f"Student Loan {req.student_loan_plan.replace('_', ' ').title()} repayment",
                    "rate": f"{int(sl_rate * 100)}%",
                    "on": f"£{max(0, req.estimated_annual_income - sl_threshold):,.0f} above threshold",
                    "tax": f"£{sl_repayment:,.0f}",
                })

    # Payments on Account
    payments_on_account = estimated_tax * 0.5
    if payments_on_account > 0:
        actions.append(
            f"Budget for Payments on Account: £{payments_on_account:,.0f} × 2 "
            "(31 Jan and 31 Jul next year)"
        )

    # Upcoming deadlines
    upcoming = [
        dl for dl in deadlines
        if not dl.get("overdue") and dl.get("date", "") >= date.today().isoformat()
    ]

    # Optionally enrich with AI narrative
    ai_summary = None
    if OPENAI_API_KEY:
        try:
            prompt = (
                f"You are a UK tax advisor. Summarise the tax situation for a self-employed person "
                f"with estimated annual income of £{req.estimated_annual_income:,.0f} in tax year {req.tax_year}. "
                f"Key facts: estimated total tax £{estimated_tax:,.0f}, "
                f"{'MTD required' if any('MANDATORY' in w for w in warnings) else 'MTD not yet required'}. "
                f"Give a 3-sentence plain-English summary including the most important action to take. "
                f"Be concise and practical."
            )
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
                    json={
                        "model": "gpt-4o-mini",
                        "messages": [{"role": "user", "content": prompt}],
                        "max_tokens": 200,
                    },
                )
                if resp.is_success:
                    ai_summary = resp.json()["choices"][0]["message"]["content"].strip()
        except Exception as exc:
            logger.warning("OpenAI call failed: %s", exc)

    return {
        "tax_year": req.tax_year,
        "estimated_annual_income": req.estimated_annual_income,
        "estimated_total_tax_and_ni": round(estimated_tax, 2),
        "estimated_effective_rate": round(estimated_tax / req.estimated_annual_income, 4) if req.estimated_annual_income > 0 else 0,
        "payments_on_account_each": round(payments_on_account, 2),
        "applicable_rules": applicable_rules,
        "warnings": warnings,
        "recommended_actions": actions,
        "upcoming_deadlines": upcoming[:4],
        "ai_summary": ai_summary,
        "mtd_required": bool(mtd_threshold and req.estimated_annual_income >= mtd_threshold),
    }


# ── Rule versions (admin dashboard) ─────────────────────────────────────────

@app.get("/rules/versions", response_model=List[RuleVersion])
async def get_rule_versions() -> List[RuleVersion]:
    """Return version and status of all loaded tax year rule files."""
    result = []
    for year, filename in _RULE_FILES.items():
        try:
            rules = _load_rules(year)
            result.append(RuleVersion(
                tax_year=year,
                version=rules.get("version", "unknown"),
                status=rules.get("status", "unknown"),
                source=rules.get("source", ""),
                effective_from=rules.get("effective_from", ""),
                effective_to=rules.get("effective_to", ""),
            ))
        except Exception:
            pass
    return result


# ── Available tax years ───────────────────────────────────────────────────────

@app.get("/rules/available-years")
async def get_available_years() -> Dict[str, Any]:
    """List all tax years with loaded rule files."""
    return {
        "available_years": list(_RULE_FILES.keys()),
        "current_tax_year": _tax_year_for_date(date.today()),
    }

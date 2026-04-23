import contextvars
import datetime
import logging
import os
import sys
import json
import time
from pathlib import Path
from typing import Any, List, Optional, Literal

import httpx
from fastapi import Depends, FastAPI, Header, HTTPException, Response, status
from jose import jwt as jose_jwt
from prometheus_client import CONTENT_TYPE_LATEST, Counter, generate_latest
from pydantic import BaseModel, Field

from .calculate_extended import (
    build_estimate_disclaimers,
    build_sa103_box_hints,
    expenses_with_trading_allowance,
    gift_aid_extend_basic_band,
    payments_on_account_each,
    rough_employee_class1_annual,
    student_loan_repayment_annual,
)
from .calculators import (
    UKSelfEmployedTaxResult,
    calculate_crypto_tax,
    calculate_dividend_tax,
    calculate_self_employed_tax,
)
from .telemetry import setup_telemetry

logger = logging.getLogger(__name__)

# --- Configuration ---
TRANSACTIONS_SERVICE_URL = os.getenv("TRANSACTIONS_SERVICE_URL", "http://localhost:8002/transactions/me")
INTEGRATIONS_SERVICE_URL = os.getenv("INTEGRATIONS_SERVICE_URL", "http://localhost:8010/integrations/hmrc/submit-tax-return")
MTD_QUARTERLY_INTEGRATIONS_SERVICE_URL = os.getenv(
    "MTD_QUARTERLY_INTEGRATIONS_SERVICE_URL",
    "http://localhost:8010/integrations/hmrc/mtd/quarterly-update",
)
CALENDAR_SERVICE_URL = os.getenv("CALENDAR_SERVICE_URL", "http://localhost:8015/events")
INVOICE_SERVICE_URL = os.getenv("INVOICE_SERVICE_URL", "http://invoice-service:80")
REGULATORY_SERVICE_URL = os.getenv("REGULATORY_SERVICE_URL", "http://regulatory-service:8025")
INTEGRATIONS_INTERNAL_BASE_URL = os.getenv(
    "INTEGRATIONS_INTERNAL_BASE_URL",
    "http://integrations-service:80",
).strip().rstrip("/")
COMPLIANCE_SERVICE_URL = (os.getenv("COMPLIANCE_SERVICE_URL") or "").strip()

# ── Regulatory rates: TTL cache from regulatory-service; merge with fallback. ─
_REGULATORY_RULES_CACHE: dict[str, tuple[float, dict[str, Any]]] = {}
_REGULATORY_TTL_SEC = float(os.environ.get("TAX_REGULATORY_RULES_CACHE_TTL", "120"))


async def _fetch_regulatory_rules(tax_year: str = "2025-26") -> tuple[dict[str, Any], str]:
    """Fetch tax rules from regulatory-service. Returns (rules, provenance) for client disclosure."""
    now = time.monotonic()
    ent = _REGULATORY_RULES_CACHE.get(tax_year)
    if ent is not None and (now - ent[0]) < _REGULATORY_TTL_SEC and ent[1]:
        return ent[1], "cache"
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(f"{REGULATORY_SERVICE_URL}/rules/tax-year/{tax_year}")
            if resp.is_success:
                data = resp.json()
                if not isinstance(data, dict):
                    return {}, "invalid_response"
                _REGULATORY_RULES_CACHE[tax_year] = (now, data)
                if data:
                    return data, "live"
                return {}, "empty_response"
    except Exception as exc:
        logger.warning("Could not reach regulatory-service (%s) — using cache or fallback.", exc)
    if ent is not None and ent[1]:
        return ent[1], "stale_cache"
    return {}, "fallback_defaults"

def _extract_rates(rules: dict[str, Any]) -> dict[str, Any]:
    """Extract flat rate values from regulatory-service response."""
    it = rules.get("income_tax", {})
    ni = rules.get("national_insurance", {})
    allowances = rules.get("allowances", {})
    bands = it.get("bands", [])
    band_map = {b["name"]: b for b in bands}
    c2 = ni.get("class_2", {})
    expenses = rules.get("allowable_expenses", {})
    expense_codes = {c["code"] for c in expenses.get("categories", [])}
    return {
        "personal_allowance": it.get("personal_allowance", 12570.0),
        "pa_taper_threshold": it.get("personal_allowance_taper_threshold", 100000.0),
        "pa_taper_rate": it.get("personal_allowance_taper_rate", 0.5),
        "basic_rate": band_map.get("basic", {}).get("rate", 0.20),
        "basic_rate_limit": band_map.get("basic", {}).get("to", 37700.0),
        "higher_rate": band_map.get("higher", {}).get("rate", 0.40),
        "higher_rate_limit": band_map.get("higher", {}).get("to", 125140.0),
        "additional_rate": band_map.get("additional", {}).get("rate", 0.45),
        "class2_weekly": c2.get("weekly_rate_voluntary", c2.get("weekly_rate", 3.45)),
        "class2_small_profits": c2.get("small_profits_threshold", 6725.0),
        "class2_lpl": c2.get("lower_profits_limit", 12570.0),
        "class4_lpl": ni.get("class_4", {}).get("lower_profits_limit", 12570.0),
        "class4_upl": ni.get("class_4", {}).get("upper_profits_limit", 50270.0),
        "class4_main": ni.get("class_4", {}).get("main_rate", 0.06),
        "class4_add": ni.get("class_4", {}).get("additional_rate", 0.02),
        "trading_allowance": allowances.get("trading_allowance", 1000.0),
        "expense_codes": expense_codes,
    }


def _default_income_tax_bands() -> list[dict[str, Any]]:
    return [
        {"name": "basic", "rate": 0.20, "from": 0, "to": 37700},
        {"name": "higher", "rate": 0.40, "from": 37700, "to": 125140},
        {"name": "additional", "rate": 0.45, "from": 125140, "to": None},
    ]


def _merge_rates_from_rules(rules: dict[str, Any]) -> dict[str, Any]:
    merged: dict[str, Any] = {**_FALLBACK_RATES}
    if not isinstance(rules, dict):
        rules = {}
    if rules:
        ext = _extract_rates(rules)
        for k, v in ext.items():
            if k == "expense_codes" and v:
                merged[k] = v
            elif k != "expense_codes" and v is not None:
                merged[k] = v
        it = rules.get("income_tax", {})
        merged["income_tax_bands"] = it.get("bands") or _default_income_tax_bands()
        merged["pa_taper_rate"] = float(it.get("personal_allowance_taper_rate", merged.get("pa_taper_rate", 0.5)))
        merged["class_2_block"] = rules.get("national_insurance", {}).get("class_2", {})
        alw = rules.get("allowances", {})
        merged["allowances_detail"] = alw
        merged["student_loans"] = rules.get("student_loans", {})
        merged["cgt_annual_exempt"] = float(alw.get("capital_gains_annual_exempt", 3000))
        merged["dividend_allowance_statutory"] = float(alw.get("dividend_allowance", 500))
        merged["aia_cap"] = float(alw.get("annual_investment_allowance", 1_000_000))
    else:
        merged["income_tax_bands"] = _default_income_tax_bands()
        merged["pa_taper_rate"] = 0.5
        merged["class_2_block"] = {}
        merged["allowances_detail"] = {}
        merged["student_loans"] = {}
        merged["cgt_annual_exempt"] = 3000.0
        merged["dividend_allowance_statutory"] = 500.0
        merged["aia_cap"] = 1_000_000.0
    return merged


def _uk_tax_year_label(d: datetime.date) -> str:
    if (d.month, d.day) >= (4, 6):
        y = d.year
    else:
        y = d.year - 1
    return f"{y}-{str(y + 1)[2:]}"


async def _rates_for_period_end(period_end: datetime.date) -> tuple[dict[str, Any], str]:
    ty = _uk_tax_year_label(period_end)
    rules, provenance = await _fetch_regulatory_rules(ty)
    return _merge_rates_from_rules(rules), provenance


async def _fetch_scottish_income_tax_bands(tax_year: str) -> list[dict[str, Any]] | None:
    try:
        async with httpx.AsyncClient(timeout=6.0) as client:
            resp = await client.get(
                f"{REGULATORY_SERVICE_URL}/rules/rates/scotland",
                params={"year": tax_year},
            )
            if not resp.is_success:
                return None
            data = resp.json()
            sit = data.get("scotland_income_tax") or {}
            bands = sit.get("bands")
            return bands if isinstance(bands, list) and bands else None
    except Exception as exc:
        logger.warning("Scotland rates fetch failed (%s); falling back to rUK bands.", exc)
    return None


def _personal_allowance_effective(total_income: float, rates: dict[str, Any], extra_pa: float = 0.0) -> float:
    pa = float(rates["personal_allowance"]) + float(extra_pa)
    thr = float(rates["pa_taper_threshold"])
    tr = float(rates.get("pa_taper_rate", 0.5))
    if total_income <= thr:
        return pa
    reduction = (total_income - thr) * tr
    return max(pa - reduction, 0.0)


def _income_tax_from_bands(taxable_after_pa: float, bands: list[dict[str, Any]]) -> tuple[float, float, float]:
    basic = higher = additional = 0.0
    for band in sorted(bands, key=lambda b: float(b["from"])):
        lo = float(band["from"])
        hi = float(band["to"]) if band.get("to") is not None else float("inf")
        rate = float(band["rate"])
        chunk = max(0.0, min(taxable_after_pa, hi) - lo)
        if chunk <= 0:
            continue
        amt = chunk * rate
        name = band.get("name", "")
        if name in ("starter", "basic", "intermediate"):
            basic += amt
        elif name == "higher":
            higher += amt
        elif name in ("additional", "advanced", "top"):
            additional += amt
        else:
            basic += amt
    return basic, higher, additional


def _class4_nic_from_rates(taxable_profit: float, rates: dict[str, Any]) -> float:
    lpl = float(rates["class4_lpl"])
    upl = float(rates["class4_upl"])
    if taxable_profit <= lpl:
        return 0.0
    main_band = max(min(taxable_profit, upl) - lpl, 0.0) * float(rates["class4_main"])
    add_band = max(taxable_profit - upl, 0.0) * float(rates["class4_add"])
    return main_band + add_band


def _class2_annual_from_rates(taxable_profit: float, rates: dict[str, Any]) -> float:
    c2 = rates.get("class_2_block") or {}
    mandatory = c2.get("mandatory_annual_cash_gbp_when_profits_ge_lower_limit")
    spt = float(c2.get("small_profits_threshold", rates["class2_small_profits"]))
    lpl = float(c2.get("lower_profits_limit", rates["class2_lpl"]))
    if mandatory is not None:
        if taxable_profit < spt or taxable_profit < lpl:
            return 0.0
        return float(mandatory)
    wk = float(c2.get("weekly_rate_voluntary", c2.get("weekly_rate", rates["class2_weekly"])))
    return wk * 52.0 if taxable_profit >= lpl else 0.0


def _deductible_categories_for_rates(rates: dict[str, Any]) -> set[str]:
    codes = rates.get("expense_codes") or set()
    if isinstance(codes, (list, tuple)):
        codes = set(codes)
    if not codes:
        return set(DEDUCTIBLE_EXPENSE_CATEGORIES)
    return set(DEDUCTIBLE_EXPENSE_CATEGORIES) | set(codes)

# Hardcoded fallback (2025/26) — used only when regulatory-service unreachable
_FALLBACK_RATES: dict[str, Any] = {
    "personal_allowance": 12_570.0,
    "pa_taper_threshold": 100_000.0,
    "pa_taper_rate": 0.5,
    "basic_rate": 0.20,
    "basic_rate_limit": 37_700.0,
    "higher_rate": 0.40,
    "higher_rate_limit": 125_140.0,
    "additional_rate": 0.45,
    "class2_weekly": 3.45,
    "class2_small_profits": 6_725.0,
    "class2_lpl": 12_570.0,
    "class4_lpl": 12_570.0,
    "class4_upl": 50_270.0,
    "class4_main": 0.06,
    "class4_add": 0.02,
    "trading_allowance": 1_000.0,
    "expense_codes": set(),
}

# Kept as fallback constants (also used in calculators.py which is standalone)
UK_PERSONAL_ALLOWANCE = 12_570.0
UK_BASIC_RATE_LIMIT = 37_700.0
UK_HIGHER_RATE_LIMIT = 125_140.0
UK_BASIC_TAX_RATE = 0.20
UK_HIGHER_TAX_RATE = 0.40
UK_ADDITIONAL_TAX_RATE = 0.45
UK_CLASS2_NI_ANNUAL = 179.40
UK_CLASS2_SMALL_PROFITS = 6_725.0
UK_CLASS4_NIC_LOWER_PROFITS_LIMIT = 12_570.0
UK_CLASS4_NIC_MAIN_RATE_UPPER_LIMIT = 50_270.0
UK_CLASS4_NIC_MAIN_RATE = 0.06
UK_CLASS4_NIC_ADDITIONAL_RATE = 0.02

# Full HMRC allowable expense categories (SA103F) — fallback, extended from regulatory-service
DEDUCTIBLE_EXPENSE_CATEGORIES = {
    "transport", "travel", "fuel", "mileage", "vehicle_mileage",
    "subscriptions", "office_supplies", "office_costs", "office", "stationery",
    "professional_fees", "legal", "accounting",
    "advertising", "marketing", "promotion",
    "insurance", "financial_costs",
    "utilities", "rent", "premises", "home_office", "use_of_home",
    "phone", "internet", "communication", "telephone",
    "training", "education", "courses",
    "equipment", "tools", "hardware", "software",
    "bank_charges", "financial_charges",
    "clothing", "uniform",
    "repairs", "maintenance",
    "staff_costs", "wages",
    "cost_of_goods", "materials", "stock", "stock_materials",
    "pension", "interest",
    "electric_vehicle", "health_safety",
}
DEFAULT_MTD_ITSA_RULES: list[dict[str, Any]] = [
    {
        "policy_code": "UK_MTD_ITSA_2026",
        "effective_from": "2026-04-06",
        "threshold": 50000.0,
        "reporting_cadence": "quarterly_updates_plus_final_declaration",
    },
    {
        "policy_code": "UK_MTD_ITSA_2027",
        "effective_from": "2027-04-06",
        "threshold": 30000.0,
        "reporting_cadence": "quarterly_updates_plus_final_declaration",
    },
    {
        "policy_code": "UK_MTD_ITSA_2028",
        "effective_from": "2028-04-06",
        "threshold": 20000.0,
        "reporting_cadence": "quarterly_updates_plus_final_declaration",
    },
]
MTD_ITSA_RULES_ENV = os.getenv("TAX_MTD_ITSA_RULES_JSON")
TAX_CALCULATIONS_TOTAL = Counter(
    "tax_calculations_total",
    "Total tax calculation attempts grouped by result.",
    labelnames=("result",),
)
TAX_SUBMISSIONS_TOTAL = Counter(
    "tax_submissions_total",
    "Total tax submission attempts grouped by result.",
    labelnames=("result",),
)

for parent in Path(__file__).resolve().parents:
    if (parent / "libs").exists():
        parent_str = str(parent)
        if parent_str not in sys.path:
            sys.path.append(parent_str)
        break

from libs.shared_auth.jwt_fastapi import build_jwt_auth_dependencies
from libs.shared_auth.plan_limits import PlanLimits, get_plan_limits, plan_limits_from_payload
from libs.shared_compliance.audit_client import post_audit_event
from libs.shared_http.retry import get_json_with_retry, post_json_with_retry
from libs.shared_mtd import build_mtd_self_employment_period_summary

get_bearer_token, get_current_user_id = build_jwt_auth_dependencies()

_CALCULATE_EMIT_COMPLIANCE_AUDIT: contextvars.ContextVar[bool] = contextvars.ContextVar(
    "tax_engine_calculate_emit_compliance_audit", default=True
)


async def _audit_tax_compliance_event(
    *,
    bearer_token: str,
    user_id: str,
    action: str,
    details: dict[str, Any],
) -> None:
    if not COMPLIANCE_SERVICE_URL:
        return
    ok = await post_audit_event(
        compliance_base_url=COMPLIANCE_SERVICE_URL,
        bearer_token=bearer_token,
        user_id=user_id,
        action=action,
        details=details,
    )
    if not ok:
        logger.warning("compliance audit not recorded action=%s user=%s", action, user_id)

app = FastAPI(
    title="Tax Engine Service",
    description="Calculates tax liabilities based on categorized transactions.",
    version="1.0.0"
)

# Instrument the app for OpenTelemetry
setup_telemetry(app)

# --- Models ---
class Transaction(BaseModel):
    date: datetime.date
    amount: float
    category: Optional[str] = None

class TaxCalculationRequest(BaseModel):
    start_date: datetime.date
    end_date: datetime.date
    jurisdiction: str
    region: Literal["england_wales", "scotland"] = "england_wales"
    use_trading_allowance: bool = False
    student_loan_plan: Optional[str] = None
    marriage_allowance_received_gbp: float = 0.0
    blind_persons_allowance_claimed: bool = False
    gross_pension_contributions_self_employed_gbp: float = 0.0
    annual_investment_allowance_claim_gbp: float = 0.0
    use_of_home_weeks_at_flat_rate: int = 0
    business_mileage_allowance_claim_gbp: float = 0.0
    savings_interest_gross_gbp: float = 0.0
    paye_gross_salary_in_period_gbp: float = 0.0
    paye_tax_paid_in_period_gbp: float = 0.0
    cis_suffered_in_period_gbp: float = 0.0
    cis_tax_credit_verified_gbp: float = 0.0
    cis_tax_credit_self_attested_gbp: float = 0.0
    unverified_cis_submit_acknowledged: bool = False
    hmrc_fraud_client_context: dict[str, Any] | None = Field(
        default=None,
        description="Forwarded to integrations-service as client_context for HMRC fraud prevention (web vs mobile).",
    )
    other_tax_credits_gbp: float = 0.0
    gift_aid_net_donations_gbp: float = 0.0
    dividend_income_gross_gbp: float = 0.0
    chargeable_gains_gbp: float = 0.0
    partnership_profit_share_gbp: float = 0.0
    losses_brought_forward_gbp: float = 0.0
    director_paye_gross_annual_gbp: float = 0.0
    is_non_uk_resident: bool = False

class TaxSummaryItem(BaseModel):
    category: str
    total_amount: float
    taxable_amount: float

class TaxCalculationResult(BaseModel):
    user_id: str
    start_date: datetime.date
    end_date: datetime.date
    total_income: float
    total_expenses: float
    taxable_profit: float
    personal_allowance_used: float
    pa_taper_reduction: float
    taxable_amount_after_allowance: float
    basic_rate_tax: float
    higher_rate_tax: float
    additional_rate_tax: float
    estimated_income_tax_due: float
    estimated_class2_nic_due: float
    estimated_class4_nic_due: float
    estimated_effective_tax_rate: float
    estimated_tax_due: float
    payment_on_account_jan: float
    payment_on_account_jul: float
    mtd_obligation: dict[str, Any]
    summary_by_category: List[TaxSummaryItem]
    student_loan_repayment_gbp: float = 0.0
    dividend_income_tax_gbp: float = 0.0
    capital_gains_tax_gbp: float = 0.0
    savings_income_included_gbp: float = 0.0
    paye_gross_included_gbp: float = 0.0
    paye_tax_credit_applied_gbp: float = 0.0
    cis_tax_credit_applied_gbp: float = 0.0
    cis_tax_credit_verified_gbp: float = 0.0
    cis_tax_credit_self_attested_gbp: float = 0.0
    cis_hmrc_submit_requires_unverified_ack: bool = False
    other_tax_credits_applied_gbp: float = 0.0
    gross_tax_before_credits_gbp: float = 0.0
    employee_ni_on_paye_estimate_gbp: float = 0.0
    income_tax_region: str = "england_wales"
    effective_allowable_expenses_gbp: float = 0.0
    breakdown: dict[str, Any] = Field(default_factory=dict)
    coverage_status: str = "complete"
    coverage: dict[str, Any] = Field(default_factory=dict)


class MTDPrepareResponse(BaseModel):
    calculation: TaxCalculationResult
    hmrc_period_summary_json: dict[str, Any]
    integrations_quarterly_payload: dict[str, Any] | None = None
    prepare_notes: List[str] = Field(default_factory=list)


class InternalAutoDraftQuarterlyRequest(BaseModel):
    user_id: str = Field(min_length=3, max_length=320)
    tax_year_start_year: int = Field(ge=2020, le=2045)
    quarter: Literal["Q1", "Q2", "Q3", "Q4"]


class InternalAutoDraftQuarterlyResponse(BaseModel):
    status: Literal["draft_created", "skipped"]
    reason: str | None = None
    draft_id: str | None = None


def _mint_finops_worker_bearer(user_id: str) -> str:
    now = datetime.datetime.now(datetime.UTC)
    exp = now + datetime.timedelta(minutes=15)
    secret = os.environ["AUTH_SECRET_KEY"].strip()
    payload: dict[str, Any] = {
        "sub": user_id,
        "plan": "business",
        "exp": int(exp.timestamp()),
        "iat": int(now.timestamp()),
    }
    return jose_jwt.encode(payload, secret, algorithm="HS256")


def _parse_iso_date(value: Any) -> datetime.date | None:
    if isinstance(value, datetime.date):
        return value
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return None
        try:
            return datetime.date.fromisoformat(stripped)
        except ValueError:
            return None
    return None


def _load_mtd_itsa_rules() -> list[dict[str, Any]]:
    if not MTD_ITSA_RULES_ENV:
        return list(DEFAULT_MTD_ITSA_RULES)
    try:
        payload = json.loads(MTD_ITSA_RULES_ENV)
    except json.JSONDecodeError:
        return list(DEFAULT_MTD_ITSA_RULES)
    if not isinstance(payload, list):
        return list(DEFAULT_MTD_ITSA_RULES)

    normalized: list[dict[str, Any]] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        policy_code = str(item.get("policy_code") or "").strip()
        effective_from = _parse_iso_date(item.get("effective_from"))
        threshold_value = item.get("threshold")
        cadence = str(item.get("reporting_cadence") or "").strip()
        if not policy_code or effective_from is None or cadence != "quarterly_updates_plus_final_declaration":
            continue
        try:
            threshold = float(threshold_value)
        except (TypeError, ValueError):
            continue
        if threshold <= 0:
            continue
        normalized.append(
            {
                "policy_code": policy_code,
                "effective_from": effective_from.isoformat(),
                "threshold": threshold,
                "reporting_cadence": cadence,
            }
        )
    return normalized if normalized else list(DEFAULT_MTD_ITSA_RULES)


def _uk_tax_year_bounds(reference_date: datetime.date) -> tuple[datetime.date, datetime.date]:
    if (reference_date.month, reference_date.day) >= (4, 6):
        start_year = reference_date.year
    else:
        start_year = reference_date.year - 1
    tax_year_start = datetime.date(start_year, 4, 6)
    tax_year_end = datetime.date(start_year + 1, 4, 5)
    return tax_year_start, tax_year_end


def _next_month_same_day(date_value: datetime.date) -> datetime.date:
    if date_value.month == 12:
        return datetime.date(date_value.year + 1, 1, date_value.day)
    return datetime.date(date_value.year, date_value.month + 1, date_value.day)


def _resolve_active_mtd_rule(tax_year_start: datetime.date) -> dict[str, Any] | None:
    rules = _load_mtd_itsa_rules()
    active_rule: dict[str, Any] | None = None
    for rule in rules:
        effective_from = _parse_iso_date(rule.get("effective_from"))
        if effective_from is None:
            continue
        if effective_from <= tax_year_start:
            if active_rule is None:
                active_rule = rule
                continue
            previous_effective = _parse_iso_date(active_rule.get("effective_from"))
            if previous_effective is None or effective_from > previous_effective:
                active_rule = rule
    return active_rule


def _build_quarterly_windows(
    tax_year_start: datetime.date,
    *,
    today: datetime.date,
) -> list[dict[str, str]]:
    year = tax_year_start.year
    quarter_rows = [
        ("Q1", datetime.date(year, 4, 6), datetime.date(year, 7, 5)),
        ("Q2", datetime.date(year, 7, 6), datetime.date(year, 10, 5)),
        ("Q3", datetime.date(year, 10, 6), datetime.date(year + 1, 1, 5)),
        ("Q4", datetime.date(year + 1, 1, 6), datetime.date(year + 1, 4, 5)),
    ]
    result: list[dict[str, str]] = []
    for label, period_start, period_end in quarter_rows:
        due_date = _next_month_same_day(period_end)
        if today > due_date:
            status_value = "overdue"
        elif today >= period_end:
            status_value = "due_now"
        else:
            status_value = "upcoming"
        result.append(
            {
                "quarter": label,
                "period_start": period_start.isoformat(),
                "period_end": period_end.isoformat(),
                "due_date": due_date.isoformat(),
                "status": status_value,
            }
        )
    return result


def _build_mtd_obligation(
    *,
    period_start: datetime.date,
    period_end: datetime.date,
    total_income: float,
    today: datetime.date,
) -> dict[str, Any]:
    tax_year_start, tax_year_end = _uk_tax_year_bounds(period_end)
    active_rule = _resolve_active_mtd_rule(tax_year_start)
    period_days = max((period_end - period_start).days + 1, 1)
    annualized_income_estimate = round((total_income * 365.0) / period_days, 2)
    notes: list[str] = []
    if period_days < 330:
        notes.append(
            "MTD threshold assessment is annualized because the selected period is shorter than a full tax year."
        )
    else:
        notes.append("MTD threshold assessment uses selected period income totals.")

    if active_rule is None:
        notes.append("No quarterly MTD ITSA policy is active for the selected tax year.")
        return {
            "tax_year_start": tax_year_start.isoformat(),
            "tax_year_end": tax_year_end.isoformat(),
            "policy_code": "UK_SELF_ASSESSMENT_ANNUAL_ONLY",
            "threshold": None,
            "qualifying_income_estimate": annualized_income_estimate,
            "reporting_required": False,
            "reporting_cadence": "annual_only",
            "quarterly_updates": [],
            "final_declaration_required": True,
            "next_deadline": None,
            "notes": notes,
        }

    threshold = float(active_rule.get("threshold") or 0.0)
    reporting_required = annualized_income_estimate > threshold
    quarterly_updates = (
        _build_quarterly_windows(tax_year_start, today=today)
        if reporting_required
        else []
    )
    next_deadline = None
    for row in quarterly_updates:
        due_date = _parse_iso_date(row.get("due_date"))
        if due_date is None:
            continue
        if due_date >= today:
            next_deadline = due_date.isoformat()
            break
    if reporting_required:
        notes.append(
            f"Estimated qualifying income {annualized_income_estimate:.2f} exceeds active threshold {threshold:.2f}."
        )
    else:
        notes.append(
            f"Estimated qualifying income {annualized_income_estimate:.2f} does not exceed active threshold {threshold:.2f}."
        )

    return {
        "tax_year_start": tax_year_start.isoformat(),
        "tax_year_end": tax_year_end.isoformat(),
        "policy_code": str(active_rule.get("policy_code") or "UK_MTD_ITSA"),
        "threshold": threshold,
        "qualifying_income_estimate": annualized_income_estimate,
        "reporting_required": reporting_required,
        "reporting_cadence": (
            "quarterly_updates_plus_final_declaration"
            if reporting_required
            else "annual_only"
        ),
        "quarterly_updates": quarterly_updates,
        "final_declaration_required": True,
        "next_deadline": next_deadline,
        "notes": notes,
    }


def _resolve_matching_mtd_quarter(
    *,
    period_start: datetime.date,
    period_end: datetime.date,
    mtd_obligation: dict[str, Any],
) -> dict[str, Any] | None:
    quarterly_updates = mtd_obligation.get("quarterly_updates")
    if not isinstance(quarterly_updates, list):
        return None
    for quarter in quarterly_updates:
        if not isinstance(quarter, dict):
            continue
        quarter_start = _parse_iso_date(quarter.get("period_start"))
        quarter_end = _parse_iso_date(quarter.get("period_end"))
        if quarter_start == period_start and quarter_end == period_end:
            return quarter
    return None


def _is_full_mtd_tax_year_submission(
    *,
    period_start: datetime.date,
    period_end: datetime.date,
    mtd_obligation: dict[str, Any],
) -> bool:
    tax_year_start = _parse_iso_date(mtd_obligation.get("tax_year_start"))
    tax_year_end = _parse_iso_date(mtd_obligation.get("tax_year_end"))
    return tax_year_start == period_start and tax_year_end == period_end


def _build_mtd_quarterly_submission_payload(
    *,
    user_id: str,
    request: "TaxCalculationRequest",
    calculation_result: "TaxCalculationResult",
    mtd_obligation: dict[str, Any],
    quarter_window: dict[str, Any],
) -> dict[str, Any]:
    category_summary = [
        item.model_dump() for item in calculation_result.summary_by_category
    ]
    payload: dict[str, Any] = {
        "submission_channel": "api",
        "correlation_id": f"tax-engine-{user_id}-{request.start_date.isoformat()}-{request.end_date.isoformat()}",
        "report": {
            "schema_version": "hmrc-mtd-itsa-quarterly-v1",
            "jurisdiction": "UK",
            "policy_code": str(mtd_obligation.get("policy_code") or "UK_MTD_ITSA"),
            "generated_at": datetime.datetime.now(datetime.UTC).isoformat(),
            "business": {
                "taxpayer_ref": user_id,
                "business_name": f"Sole trader account {user_id}",
                "accounting_method": "cash",
            },
            "period": {
                "tax_year_start": str(mtd_obligation.get("tax_year_start")),
                "tax_year_end": str(mtd_obligation.get("tax_year_end")),
                "quarter": str(quarter_window.get("quarter")),
                "period_start": request.start_date.isoformat(),
                "period_end": request.end_date.isoformat(),
                "due_date": str(quarter_window.get("due_date")),
            },
            "financials": {
                "turnover": round(calculation_result.total_income, 2),
                "allowable_expenses": round(calculation_result.total_expenses, 2),
                "taxable_profit": round(calculation_result.taxable_profit, 2),
                "estimated_tax_due": round(calculation_result.estimated_tax_due, 2),
                "currency": "GBP",
            },
            "category_summary": category_summary,
            "declaration": "true_and_complete",
            "cis_disclosure": {
                "credit_verified_gbp": round(calculation_result.cis_tax_credit_verified_gbp, 2),
                "credit_self_attested_unverified_gbp": round(
                    calculation_result.cis_tax_credit_self_attested_gbp, 2
                ),
            },
        },
    }
    if calculation_result.cis_tax_credit_self_attested_gbp > 0.01:
        payload["unverified_cis_submit_acknowledged"] = bool(request.unverified_cis_submit_acknowledged)
    if request.hmrc_fraud_client_context:
        payload["client_context"] = request.hmrc_fraud_client_context
    return payload


# --- Endpoints ---
def _add_calendar_months(d: datetime.date, delta: int) -> datetime.date:
    import calendar

    m = d.month - 1 + delta
    y = d.year + m // 12
    m = m % 12 + 1
    last = calendar.monthrange(y, m)[1]
    return datetime.date(y, m, min(d.day, last))


def _retention_cutoff(transaction_history_months: int, today: datetime.date) -> datetime.date:
    if transaction_history_months <= 0:
        return datetime.date(1970, 1, 1)
    return _add_calendar_months(today, -transaction_history_months)


def _coverage_for_period(
    requested_start: datetime.date,
    requested_end: datetime.date,
    retention_months: int,
    today: datetime.date | None = None,
) -> tuple[datetime.date, dict[str, Any], str]:
    today = today or datetime.date.today()
    cutoff = _retention_cutoff(retention_months, today)
    effective_start = max(requested_start, cutoff)
    status = "complete" if requested_start >= cutoff else "partial"
    meta: dict[str, Any] = {
        "status": status,
        "retention_months": retention_months,
        "retention_cutoff_date": cutoff.isoformat(),
        "requested_period_start": requested_start.isoformat(),
        "requested_period_end": requested_end.isoformat(),
        "effective_period_start": effective_start.isoformat(),
    }
    return effective_start, meta, status


def _txn_dict_min_date(transactions: list[dict], min_d: datetime.date) -> list[dict]:
    out: list[dict] = []
    for t in transactions:
        raw = t.get("date")
        if raw is None:
            continue
        if isinstance(raw, str):
            try:
                td = datetime.date.fromisoformat(raw[:10])
            except ValueError:
                continue
        elif isinstance(raw, datetime.date):
            td = raw
        else:
            continue
        if td >= min_d:
            out.append(t)
    return out


class PublicSelfEmployedEstimateRequest(BaseModel):
    gross_trading_income: float = Field(..., ge=0, le=10_000_000)
    allowable_expenses: float = Field(0.0, ge=0, le=10_000_000)
    use_trading_allowance: bool = False
    student_loan_plan: Optional[str] = None


class PublicSelfEmployedEstimateResponse(BaseModel):
    result: UKSelfEmployedTaxResult
    disclaimer: str
    tax_year_label: str = "2025/26"


_PUBLIC_SE_DISCLAIMER = (
    "Illustrative UK self-employment estimate using in-engine 2025/26-style bands and NI rules. "
    "Not tax or legal advice. For bank-linked MTD figures and filing, create an account."
)


@app.post("/public/self-employed-estimate", response_model=PublicSelfEmployedEstimateResponse)
async def public_self_employed_estimate(body: PublicSelfEmployedEstimateRequest):
    """No authentication: manual inputs only (SEO / lead magnet)."""
    if body.allowable_expenses > body.gross_trading_income + 0.01:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Allowable expenses cannot exceed gross trading income.",
        )
    result = calculate_self_employed_tax(
        gross_trading_income=body.gross_trading_income,
        allowable_expenses=body.allowable_expenses,
        use_trading_allowance=body.use_trading_allowance,
        student_loan_plan=body.student_loan_plan,
    )
    return PublicSelfEmployedEstimateResponse(
        result=result,
        disclaimer=_PUBLIC_SE_DISCLAIMER,
    )


@app.get("/metrics")
async def metrics() -> Response:
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.post("/calculate", response_model=TaxCalculationResult)
async def calculate_tax(
    request: TaxCalculationRequest,
    user_id: str = Depends(get_current_user_id),
    bearer_token: str = Depends(get_bearer_token),
    limits: PlanLimits = Depends(get_plan_limits),
):
    if request.start_date > request.end_date:
        TAX_CALCULATIONS_TOTAL.labels(result="validation_error").inc()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="End date cannot be before start date.")
    if request.jurisdiction != "UK":
        TAX_CALCULATIONS_TOTAL.labels(result="validation_error").inc()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only 'UK' jurisdiction is supported.")

    rates, regulatory_source = await _rates_for_period_end(request.end_date)
    deductible = _deductible_categories_for_rates(rates)

    # 1. Fetch all transactions for the user from the transactions-service
    try:
        headers = {"Authorization": f"Bearer {bearer_token}"}
        transactions_data = await get_json_with_retry(
            TRANSACTIONS_SERVICE_URL,
            headers=headers,
            timeout=10.0,
        )
        transactions = [Transaction(**t) for t in transactions_data]
    except httpx.HTTPError as exc:
        TAX_CALCULATIONS_TOTAL.labels(result="upstream_error").inc()
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Could not connect to transactions-service: {exc}",
        ) from exc

    effective_start, coverage_meta, coverage_status = _coverage_for_period(
        request.start_date,
        request.end_date,
        limits.transaction_history_months,
    )

    # 2. Filter transactions by date and calculate totals
    total_income = 0.0
    total_expenses = 0.0
    summary_map = {}

    for t in transactions:
        if effective_start <= t.date <= request.end_date:
            if t.amount > 0:
                total_income += t.amount
            elif (t.category or "") in deductible:
                total_expenses += abs(t.amount)

            category = t.category or "uncategorized"
            summary_map.setdefault(category, 0.0)
            summary_map[category] += t.amount

    allowances_detail = rates.get("allowances_detail") or {}
    tax_year = _uk_tax_year_label(request.end_date)
    home_weekly = float(allowances_detail.get("use_of_home_flat_rate_weekly", 6))
    use_home_amt = max(0, int(request.use_of_home_weeks_at_flat_rate)) * home_weekly
    mileage_amt = max(0.0, request.business_mileage_allowance_claim_gbp)
    deductible_pool = total_expenses + mileage_amt + use_home_amt
    ta_cap = float(rates.get("trading_allowance", 1000))
    effective_expenses = expenses_with_trading_allowance(
        total_income,
        deductible_pool,
        request.use_trading_allowance,
        ta_cap,
    )
    trading_core = total_income - effective_expenses
    profit_pre_partnership = trading_core + max(0.0, request.partnership_profit_share_gbp)
    aia_cap = float(rates.get("aia_cap", 1_000_000))
    aia_used = min(max(0.0, request.annual_investment_allowance_claim_gbp), aia_cap)
    pension = max(0.0, request.gross_pension_contributions_self_employed_gbp)
    profit_after_relief = profit_pre_partnership - pension - aia_used
    losses_bf = max(0.0, request.losses_brought_forward_gbp)
    se_basis = max(0.0, profit_after_relief - losses_bf)
    paye_gross = max(0.0, request.paye_gross_salary_in_period_gbp)
    savings = max(0.0, request.savings_interest_gross_gbp)
    taper_income = se_basis + paye_gross + savings
    ma_cap = float(allowances_detail.get("marriage_allowance_transfer", 1260))
    ma_recv = min(max(0.0, request.marriage_allowance_received_gbp), ma_cap)
    blind_add = (
        float(allowances_detail.get("blind_persons_allowance", 3130))
        if request.blind_persons_allowance_claimed
        else 0.0
    )
    extra_pa = ma_recv + blind_add
    pa_eff = _personal_allowance_effective(taper_income, rates, extra_pa)
    pa_nominal = float(rates["personal_allowance"]) + extra_pa
    pa_taper = pa_nominal - pa_eff
    personal_allowance_used = min(taper_income, pa_eff)
    taxable_amount_after_allowance = max(taper_income - pa_eff, 0.0)
    bands: list[dict[str, Any]] = list(rates.get("income_tax_bands") or _default_income_tax_bands())
    income_region: str = request.region
    scotland_fallback = False
    if request.region == "scotland":
        sb = await _fetch_scottish_income_tax_bands(tax_year)
        if sb:
            bands = sb
        else:
            scotland_fallback = True
    breakdown: dict[str, Any] = {"coverage": coverage_meta}
    if coverage_status == "partial":
        breakdown.setdefault("warnings", []).append(
            f"Partial data coverage: subscription retention is {limits.transaction_history_months} months; "
            f"transactions before {coverage_meta['retention_cutoff_date']} are excluded from this estimate."
        )
    if scotland_fallback:
        breakdown.setdefault("warnings", []).append(
            "Scottish income tax bands were unavailable; rUK bands were used for this estimate."
        )
    if request.gift_aid_net_donations_gbp > 0:
        if request.region == "england_wales":
            bands = gift_aid_extend_basic_band(bands, request.gift_aid_net_donations_gbp)
        else:
            breakdown.setdefault("notes", []).append(
                "Gift Aid basic-rate band extension is omitted for Scotland in this simplified model."
            )
    basic_tax, higher_tax, additional_tax = _income_tax_from_bands(taxable_amount_after_allowance, bands)
    estimated_income_tax = basic_tax + higher_tax + additional_tax
    estimated_class2_nic = _class2_annual_from_rates(se_basis, rates)
    estimated_class4_nic = _class4_nic_from_rates(se_basis, rates)
    sl_rules = rates.get("student_loans") or {}
    sl_repay = student_loan_repayment_annual(taper_income, request.student_loan_plan, sl_rules)
    div_tax = 0.0
    div_gross = max(0.0, request.dividend_income_gross_gbp)
    if div_gross > 0:
        br_w = float(rates["basic_rate_limit"])
        hr_top = float(rates["higher_rate_limit"])
        da = float(rates.get("dividend_allowance_statutory", 500))
        div_res = calculate_dividend_tax(
            div_gross,
            taper_income,
            personal_allowance=pa_eff,
            dividend_allowance=da,
            basic_band_width=br_w,
            higher_band_top=hr_top,
        )
        div_tax = float(div_res.total_dividend_tax)
    cgt = 0.0
    gains = max(0.0, request.chargeable_gains_gbp)
    if gains > 0:
        cg_res = calculate_crypto_tax(
            gains,
            0.0,
            taper_income,
            personal_allowance=pa_eff,
            annual_exempt_amount=float(rates.get("cgt_annual_exempt", 3000)),
            basic_band_width=float(rates["basic_rate_limit"]),
        )
        cgt = float(cg_res.total_cgt)
    emp_ni = 0.0
    if request.director_paye_gross_annual_gbp > 0:
        emp_ni = rough_employee_class1_annual(request.director_paye_gross_annual_gbp)
    paye_cred = max(0.0, request.paye_tax_paid_in_period_gbp)
    cis_v = max(0.0, request.cis_tax_credit_verified_gbp)
    cis_s = max(0.0, request.cis_tax_credit_self_attested_gbp)
    cis_leg = max(0.0, request.cis_suffered_in_period_gbp)
    legacy_cis_to_unverified = False
    legacy_cis_ignored = False
    if cis_v == 0.0 and cis_s == 0.0 and cis_leg > 0.0:
        cis_s = cis_leg
        legacy_cis_to_unverified = True
    elif cis_leg > 0.0:
        legacy_cis_ignored = True
    cis_cred = cis_v + cis_s
    cis_submit_ack_required = cis_s > 0.01
    other_cred = max(0.0, request.other_tax_credits_gbp)
    credits = paye_cred + cis_cred + other_cred
    gross_components = (
        estimated_income_tax
        + estimated_class2_nic
        + estimated_class4_nic
        + sl_repay
        + div_tax
        + cgt
        + emp_ni
    )
    estimated_tax = max(0.0, gross_components - credits)
    effective_tax_rate = (estimated_tax / taper_income) if taper_income > 0 else 0.0
    poa_each = payments_on_account_each(estimated_income_tax, estimated_class4_nic, sl_repay)
    summary_by_category = [
        TaxSummaryItem(category=cat, total_amount=round(amount, 2), taxable_amount=round(amount, 2))
        for cat, amount in summary_map.items()
    ]
    mtd_obligation = _build_mtd_obligation(
        period_start=request.start_date,
        period_end=request.end_date,
        total_income=total_income,
        today=datetime.date.today(),
    )
    if mtd_obligation.get("reporting_required"):
        mtd_obligation.setdefault("notes", []).append(
            "End of Period Statement (EOPS): required per income source when within MTD ITSA quarterly obligations."
        )
    if request.is_non_uk_resident:
        breakdown.setdefault("warnings", []).append(
            "Non-UK resident reporting is not modelled here; figures assume UK residency rules."
        )
    lf_applied = min(losses_bf, max(0.0, profit_after_relief))
    disclaimers = build_estimate_disclaimers(
        regulatory_source=regulatory_source,
        region=request.region,
        gift_aid_net_gbp=request.gift_aid_net_donations_gbp,
        savings_interest_gross_gbp=request.savings_interest_gross_gbp,
        dividend_income_gross_gbp=request.dividend_income_gross_gbp,
        chargeable_gains_gbp=request.chargeable_gains_gbp,
        is_non_uk_resident=request.is_non_uk_resident,
    )
    cis_labels: list[str] = []
    if cis_s > 0.01:
        cis_labels.append("UNVERIFIED")
    breakdown.update(
        {
            "trading_allowance_elected": request.use_trading_allowance,
            "use_of_home_flat_rate_gbp": round(use_home_amt, 2),
            "mileage_allowance_claim_gbp": round(mileage_amt, 2),
            "annual_investment_allowance_applied_gbp": round(aia_used, 2),
            "losses_brought_forward_applied_gbp": round(lf_applied, 2),
            "trading_net_before_partnership_gbp": round(trading_core, 2),
            "sa103_box_hints": build_sa103_box_hints([s.model_dump() for s in summary_by_category]),
            "tax_year": tax_year,
            "regulatory_rules_source": regulatory_source,
            "estimate_disclaimers": disclaimers,
            "cis_credits_breakdown": {
                "verified_gbp": round(cis_v, 2),
                "unverified_self_attested_gbp": round(cis_s, 2),
                "labels": cis_labels,
                "hmrc_submit_extra_confirm_required": cis_submit_ack_required,
                "legacy_cis_field_routed_to_unverified": legacy_cis_to_unverified,
                "legacy_cis_field_ignored_use_split_inputs": legacy_cis_ignored,
            },
        }
    )
    TAX_CALCULATIONS_TOTAL.labels(result="success").inc()
    if _CALCULATE_EMIT_COMPLIANCE_AUDIT.get():
        await _audit_tax_compliance_event(
            bearer_token=bearer_token,
            user_id=user_id,
            action="tax_calculate",
            details={
                "start_date": request.start_date.isoformat(),
                "end_date": request.end_date.isoformat(),
                "jurisdiction": request.jurisdiction,
                "estimated_tax_due": round(estimated_tax, 2),
            },
        )
    return TaxCalculationResult(
        user_id=user_id,
        start_date=request.start_date,
        end_date=request.end_date,
        total_income=round(total_income, 2),
        total_expenses=round(total_expenses, 2),
        taxable_profit=round(se_basis, 2),
        personal_allowance_used=round(personal_allowance_used, 2),
        pa_taper_reduction=round(pa_taper, 2),
        taxable_amount_after_allowance=round(taxable_amount_after_allowance, 2),
        basic_rate_tax=round(basic_tax, 2),
        higher_rate_tax=round(higher_tax, 2),
        additional_rate_tax=round(additional_tax, 2),
        estimated_income_tax_due=round(estimated_income_tax, 2),
        estimated_class2_nic_due=round(estimated_class2_nic, 2),
        estimated_class4_nic_due=round(estimated_class4_nic, 2),
        estimated_effective_tax_rate=round(effective_tax_rate, 4),
        estimated_tax_due=round(estimated_tax, 2),
        payment_on_account_jan=poa_each,
        payment_on_account_jul=poa_each,
        mtd_obligation=mtd_obligation,
        summary_by_category=summary_by_category,
        student_loan_repayment_gbp=round(sl_repay, 2),
        dividend_income_tax_gbp=round(div_tax, 2),
        capital_gains_tax_gbp=round(cgt, 2),
        savings_income_included_gbp=round(savings, 2),
        paye_gross_included_gbp=round(paye_gross, 2),
        paye_tax_credit_applied_gbp=round(paye_cred, 2),
        cis_tax_credit_applied_gbp=round(cis_cred, 2),
        cis_tax_credit_verified_gbp=round(cis_v, 2),
        cis_tax_credit_self_attested_gbp=round(cis_s, 2),
        cis_hmrc_submit_requires_unverified_ack=cis_submit_ack_required,
        other_tax_credits_applied_gbp=round(other_cred, 2),
        gross_tax_before_credits_gbp=round(gross_components, 2),
        employee_ni_on_paye_estimate_gbp=round(emp_ni, 2),
        income_tax_region=income_region,
        effective_allowable_expenses_gbp=round(effective_expenses, 2),
        breakdown=breakdown,
    )


@app.post("/mtd/prepare", response_model=MTDPrepareResponse)
async def mtd_prepare(
    request: TaxCalculationRequest,
    user_id: str = Depends(get_current_user_id),
    bearer_token: str = Depends(get_bearer_token),
    limits: PlanLimits = Depends(get_plan_limits),
):
    _tok = _CALCULATE_EMIT_COMPLIANCE_AUDIT.set(False)
    try:
        calculation_result = await calculate_tax(request, user_id, bearer_token, limits)
    finally:
        _CALCULATE_EMIT_COMPLIANCE_AUDIT.reset(_tok)
    mtd_obligation = (
        calculation_result.mtd_obligation
        if isinstance(calculation_result.mtd_obligation, dict)
        else {}
    )
    hmrc_period_summary_json = build_mtd_self_employment_period_summary(
        period_start_iso=request.start_date.isoformat(),
        period_end_iso=request.end_date.isoformat(),
        turnover=calculation_result.total_income,
        allowable_expenses=calculation_result.total_expenses,
    )
    integrations_quarterly_payload: dict[str, Any] | None = None
    prepare_notes: list[str] = []
    if bool(mtd_obligation.get("reporting_required")):
        quarter_window = _resolve_matching_mtd_quarter(
            period_start=request.start_date,
            period_end=request.end_date,
            mtd_obligation=mtd_obligation,
        )
        if quarter_window is not None:
            integrations_quarterly_payload = _build_mtd_quarterly_submission_payload(
                user_id=user_id,
                request=request,
                calculation_result=calculation_result,
                mtd_obligation=mtd_obligation,
                quarter_window=quarter_window,
            )
        elif not _is_full_mtd_tax_year_submission(
            period_start=request.start_date,
            period_end=request.end_date,
            mtd_obligation=mtd_obligation,
        ):
            prepare_notes.append(
                "MTD quarterly reporting is required, but the selected dates do not match "
                "a quarterly window or full tax year; adjust the period before submit."
            )
    await _audit_tax_compliance_event(
        bearer_token=bearer_token,
        user_id=user_id,
        action="tax_mtd_prepare",
        details={
            "start_date": request.start_date.isoformat(),
            "end_date": request.end_date.isoformat(),
            "jurisdiction": request.jurisdiction,
            "mtd_reporting_required": bool(mtd_obligation.get("reporting_required")),
            "has_integrations_quarterly_payload": integrations_quarterly_payload is not None,
            "estimated_tax_due": calculation_result.estimated_tax_due,
            "prepare_notes_count": len(prepare_notes),
        },
    )
    return MTDPrepareResponse(
        calculation=calculation_result,
        hmrc_period_summary_json=hmrc_period_summary_json,
        integrations_quarterly_payload=integrations_quarterly_payload,
        prepare_notes=prepare_notes,
    )


@app.post("/internal/mtd/auto-draft-quarterly", response_model=InternalAutoDraftQuarterlyResponse)
async def internal_mtd_auto_draft_quarterly(
    body: InternalAutoDraftQuarterlyRequest,
    x_internal_token: str | None = Header(default=None, alias="X-Internal-Token"),
):
    """Finops-scheduled: build quarterly MTD figures and persist integrations draft (no HMRC submit)."""
    secret = os.getenv("INTERNAL_SERVICE_SECRET", "").strip()
    if not secret:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="internal_calls_not_configured")
    if not x_internal_token or x_internal_token != secret:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden")

    qrow = next(
        (q for q in _quarter_dates(body.tax_year_start_year) if q.quarter == body.quarter),
        None,
    )
    if qrow is None:
        return InternalAutoDraftQuarterlyResponse(status="skipped", reason="invalid_quarter")

    ps = datetime.date.fromisoformat(qrow.period_start)
    pe = datetime.date.fromisoformat(qrow.period_end)
    limits = plan_limits_from_payload({"plan": "business"})
    request = TaxCalculationRequest(start_date=ps, end_date=pe, jurisdiction="UK")
    uid = body.user_id.strip()
    bearer = _mint_finops_worker_bearer(uid)
    _tok = _CALCULATE_EMIT_COMPLIANCE_AUDIT.set(False)
    try:
        calculation_result = await calculate_tax(request, uid, bearer, limits)
    except HTTPException as exc:
        detail = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
        return InternalAutoDraftQuarterlyResponse(status="skipped", reason=f"tax_calculation:{detail}")
    except Exception as exc:
        logger.warning("internal auto-draft calculate_tax failed: %s", exc)
        return InternalAutoDraftQuarterlyResponse(status="skipped", reason="tax_calculation_error")
    finally:
        _CALCULATE_EMIT_COMPLIANCE_AUDIT.reset(_tok)

    mtd_obligation = (
        calculation_result.mtd_obligation if isinstance(calculation_result.mtd_obligation, dict) else {}
    )
    if not bool(mtd_obligation.get("reporting_required")):
        return InternalAutoDraftQuarterlyResponse(status="skipped", reason="mtd_not_required")

    quarter_window = _resolve_matching_mtd_quarter(
        period_start=request.start_date,
        period_end=request.end_date,
        mtd_obligation=mtd_obligation,
    )
    if quarter_window is None:
        return InternalAutoDraftQuarterlyResponse(status="skipped", reason="no_matching_quarter_window")

    integrations_payload = _build_mtd_quarterly_submission_payload(
        user_id=uid,
        request=request,
        calculation_result=calculation_result,
        mtd_obligation=mtd_obligation,
        quarter_window=quarter_window,
    )
    report = integrations_payload.get("report")
    if not isinstance(report, dict):
        return InternalAutoDraftQuarterlyResponse(status="skipped", reason="no_report_payload")

    url = f"{INTEGRATIONS_INTERNAL_BASE_URL}/internal/hmrc/mtd/quarterly-update/draft"
    try:
        async with httpx.AsyncClient(timeout=45.0) as client:
            r = await client.post(
                url,
                headers={"X-Internal-Token": secret},
                json={"user_id": uid, "report": report},
            )
    except httpx.HTTPError as exc:
        logger.warning("internal auto-draft integrations call failed: %s", exc)
        return InternalAutoDraftQuarterlyResponse(status="skipped", reason="integrations_unreachable")

    if r.status_code not in (200, 201):
        text = (r.text or "")[:400]
        logger.warning("integrations draft returned %s: %s", r.status_code, text)
        return InternalAutoDraftQuarterlyResponse(
            status="skipped",
            reason=f"integrations_http_{r.status_code}",
        )

    try:
        resp_json = r.json()
    except Exception:
        resp_json = {}
    did = resp_json.get("draft_id")
    draft_id_str = str(did) if did is not None else None
    return InternalAutoDraftQuarterlyResponse(status="draft_created", draft_id=draft_id_str)


@app.post("/calculate-and-submit", status_code=status.HTTP_202_ACCEPTED)
async def calculate_and_submit_tax(
    request: TaxCalculationRequest,
    user_id: str = Depends(get_current_user_id),
    bearer_token: str = Depends(get_bearer_token),
    limits: PlanLimits = Depends(get_plan_limits),
):
    # This re-uses the logic from the calculate endpoint.
    # In a real app, this logic would be in a shared function.
    _tok = _CALCULATE_EMIT_COMPLIANCE_AUDIT.set(False)
    try:
        calculation_result = await calculate_tax(request, user_id, bearer_token, limits)
    finally:
        _CALCULATE_EMIT_COMPLIANCE_AUDIT.reset(_tok)

    # 5. Submit the calculated tax to the integrations service.
    # For compliant MTD quarterly windows we use a dedicated direct HMRC endpoint.
    try:
        headers = {"Authorization": f"Bearer {bearer_token}"}
        mtd_obligation = (
            calculation_result.mtd_obligation
            if isinstance(calculation_result.mtd_obligation, dict)
            else {}
        )
        submission_payload: dict[str, Any]
        submission_url = INTEGRATIONS_SERVICE_URL
        submission_mode = "annual_tax_return"
        is_mtd_reporting = bool(mtd_obligation.get("reporting_required"))
        quarter_window = _resolve_matching_mtd_quarter(
            period_start=request.start_date,
            period_end=request.end_date,
            mtd_obligation=mtd_obligation,
        )
        if is_mtd_reporting and quarter_window is not None:
            if calculation_result.cis_tax_credit_self_attested_gbp > 0.01 and not request.unverified_cis_submit_acknowledged:
                TAX_SUBMISSIONS_TOTAL.labels(result="validation_error").inc()
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        "UNVERIFIED CIS credits are included. Set unverified_cis_submit_acknowledged=true "
                        "only after the user explicitly accepts responsibility (variant B gate), or use verified CIS only."
                    ),
                )
            submission_payload = _build_mtd_quarterly_submission_payload(
                user_id=user_id,
                request=request,
                calculation_result=calculation_result,
                mtd_obligation=mtd_obligation,
                quarter_window=quarter_window,
            )
            submission_url = MTD_QUARTERLY_INTEGRATIONS_SERVICE_URL
            submission_mode = "mtd_quarterly_update"
        else:
            if is_mtd_reporting and not _is_full_mtd_tax_year_submission(
                period_start=request.start_date,
                period_end=request.end_date,
                mtd_obligation=mtd_obligation,
            ):
                TAX_SUBMISSIONS_TOTAL.labels(result="validation_error").inc()
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        "For MTD quarterly reporting, submission period must match an HMRC quarter "
                        "or the full tax year for final declaration."
                    ),
                )
            submission_payload = {
                "tax_period_start": request.start_date.isoformat(),
                "tax_period_end": request.end_date.isoformat(),
                "tax_due": calculation_result.estimated_tax_due,
            }
        submission_data = await post_json_with_retry(
            submission_url,
            headers=headers,
            json_body=submission_payload,
            timeout=15.0,
        )
    except httpx.HTTPError as exc:
        TAX_SUBMISSIONS_TOTAL.labels(result="upstream_error").inc()
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Could not connect to integrations-service: {exc}",
        ) from exc

    await _audit_tax_compliance_event(
        bearer_token=bearer_token,
        user_id=user_id,
        action="tax_calculate_and_submit",
        details={
            "start_date": request.start_date.isoformat(),
            "end_date": request.end_date.isoformat(),
            "submission_mode": submission_mode,
            "submission_id": submission_data.get("submission_id"),
            "estimated_tax_due": calculation_result.estimated_tax_due,
        },
    )

    # 6. Create a calendar event for the payment deadline
    try:
        # UK Self Assessment payment deadline is 31st Jan of the next year
        deadline_year = request.end_date.year + 1
        deadline = datetime.date(deadline_year, 1, 31)
        await post_json_with_retry(
            CALENDAR_SERVICE_URL,
            json_body={
                "user_id": user_id,
                "event_title": "UK Self Assessment Tax Payment Due",
                "event_date": deadline.isoformat(),
                "notes": (
                    f"Estimated tax due: £{calculation_result.estimated_tax_due}. "
                    f"Submission ID: {submission_data.get('submission_id')}"
                ),
            },
            expect_json=False,
        )
    except httpx.HTTPError:
        # This is a non-critical step, so we don't fail the whole request if it fails.
        logger.warning("Could not create calendar event.")

    # 7. Create quarterly MTD reminder events when quarterly updates are required.
    if bool(mtd_obligation.get("reporting_required")):
        quarterly_updates = mtd_obligation.get("quarterly_updates")
        if isinstance(quarterly_updates, list):
            for quarter in quarterly_updates:
                if not isinstance(quarter, dict):
                    continue
                quarter_label = str(quarter.get("quarter") or "").strip()
                due_date = str(quarter.get("due_date") or "").strip()
                if not quarter_label or not due_date:
                    continue
                try:
                    await post_json_with_retry(
                        CALENDAR_SERVICE_URL,
                        json_body={
                            "user_id": user_id,
                            "event_title": f"MTD ITSA quarterly update due ({quarter_label})",
                            "event_date": due_date,
                            "notes": (
                                f"Prepare and submit {quarter_label} quarterly update. "
                                f"Policy: {mtd_obligation.get('policy_code')}"
                            ),
                        },
                        expect_json=False,
                    )
                except httpx.HTTPError:
                    print(f"Warning: Could not create MTD calendar event for {quarter_label}.")


    TAX_SUBMISSIONS_TOTAL.labels(result="success").inc()
    return {
        "submission_id": submission_data.get("submission_id"),
        "message": "Tax return submission has been successfully initiated via integrations service.",
        "submission_mode": submission_mode,
        "mtd_obligation": calculation_result.mtd_obligation,
    }


from .calculators import (
    PAYETaxResult, calculate_paye,
    RentalTaxResult, calculate_rental_tax,
    CISTaxResult, calculate_cis,
    DividendTaxResult, calculate_dividend_tax,
    CryptoTaxResult, calculate_crypto_tax,
    UKSelfEmployedTaxResult, calculate_self_employed_tax,
)

@app.post("/calculators/paye", response_model=PAYETaxResult)
async def paye_calculator(gross_salary: float, tax_code: str = "1257L"):
    return calculate_paye(gross_salary, tax_code)

@app.post("/calculators/rental", response_model=RentalTaxResult)
async def rental_tax_calculator(
    rental_income: float,
    mortgage_interest: float = 0,
    repairs: float = 0,
    insurance: float = 0,
    letting_agent_fees: float = 0,
    other_expenses: float = 0,
    other_income: float = 0,
):
    return calculate_rental_tax(rental_income, mortgage_interest, repairs, insurance, letting_agent_fees, other_expenses, other_income)

@app.post("/calculators/cis", response_model=CISTaxResult)
async def cis_calculator(gross_payment: float, materials: float = 0, cis_rate: float = 20, other_expenses: float = 0):
    return calculate_cis(gross_payment, materials, cis_rate, other_expenses)

@app.post("/calculators/dividend", response_model=DividendTaxResult)
async def dividend_calculator(dividend_income: float, other_income: float = 0):
    return calculate_dividend_tax(dividend_income, other_income)

@app.post("/calculators/crypto", response_model=CryptoTaxResult)
async def crypto_tax_calculator(total_gains: float, total_losses: float = 0, other_income: float = 0):
    return calculate_crypto_tax(total_gains, total_losses, other_income)


class SelfEmployedCalcRequest(BaseModel):
    gross_trading_income: float
    allowable_expenses: float = 0.0
    pension_contributions: float = 0.0
    student_loan_plan: Optional[str] = None
    marriage_allowance_received: float = 0.0
    losses_brought_forward: float = 0.0
    use_trading_allowance: bool = False


@app.post("/calculators/self-employed", response_model=UKSelfEmployedTaxResult)
async def self_employed_calculator(req: SelfEmployedCalcRequest):
    """
    Full 2025/26 UK self-employed tax calculator.
    Covers: Income Tax (3 bands), PA taper, Class 2 & 4 NI,
    trading allowance, pension relief, student loan, payments on account.
    """
    return calculate_self_employed_tax(
        gross_trading_income=req.gross_trading_income,
        allowable_expenses=req.allowable_expenses,
        pension_contributions=req.pension_contributions,
        student_loan_plan=req.student_loan_plan,
        marriage_allowance_received=req.marriage_allowance_received,
        losses_brought_forward=req.losses_brought_forward,
        use_trading_allowance=req.use_trading_allowance,
    )


# === Auto-collect and prepare HMRC reports ===


class QuarterDates(BaseModel):
    quarter: str
    tax_year_start: str
    period_start: str
    period_end: str
    due_date: str


class AutoCollectedData(BaseModel):
    period_start: str
    period_end: str
    total_income: float
    income_breakdown: list[dict]
    total_expenses: float
    expense_breakdown: list[dict]
    invoice_income: float
    invoice_count: int
    transaction_count: int
    net_profit: float


class PreparedQuarterlyReport(BaseModel):
    status: str
    quarter: str
    tax_year: str
    collected_data: AutoCollectedData
    hmrc_periodic_update: dict
    estimated_tax: float
    message: str
    coverage_status: str = "complete"
    coverage: dict[str, Any] = Field(default_factory=dict)


class PreparedAnnualReport(BaseModel):
    status: str
    tax_year: str
    quarters: list[dict]
    total_income: float
    total_expenses: float
    total_allowances: float
    losses_brought_forward: float
    taxable_income: float
    income_tax: float
    ni_class2: float
    ni_class4: float
    total_tax_due: float
    hmrc_final_declaration: dict
    message: str
    coverage_status: str = "complete"
    coverage: dict[str, Any] = Field(default_factory=dict)


def _quarter_dates(tax_year_start_year: int) -> list[QuarterDates]:
    """Generate UK tax year quarter dates."""
    y = tax_year_start_year
    return [
        QuarterDates(quarter="Q1", tax_year_start=f"{y}-04-06", period_start=f"{y}-04-06", period_end=f"{y}-07-05", due_date=f"{y}-08-05"),
        QuarterDates(quarter="Q2", tax_year_start=f"{y}-04-06", period_start=f"{y}-07-06", period_end=f"{y}-10-05", due_date=f"{y}-11-05"),
        QuarterDates(quarter="Q3", tax_year_start=f"{y}-04-06", period_start=f"{y}-10-06", period_end=f"{y+1}-01-05", due_date=f"{y+1}-02-05"),
        QuarterDates(quarter="Q4", tax_year_start=f"{y}-04-06", period_start=f"{y+1}-01-06", period_end=f"{y+1}-04-05", due_date=f"{y+1}-05-05"),
    ]


async def _fetch_transactions(bearer_token: str, from_date: str, to_date: str) -> list[dict]:
    """Fetch user transactions for a date range."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                TRANSACTIONS_SERVICE_URL,
                headers={"Authorization": f"Bearer {bearer_token}"},
                params={"from_date": from_date, "to_date": to_date},
                timeout=15.0,
            )
            if response.status_code == 200:
                data = response.json()
                return data if isinstance(data, list) else []
    except Exception:
        pass
    return []


async def _fetch_invoice_income(bearer_token: str, from_date: str, to_date: str) -> dict:
    """Fetch invoice income summary for a date range."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{INVOICE_SERVICE_URL}/reports/summary",
                headers={"Authorization": f"Bearer {bearer_token}"},
                params={"start_date": from_date, "end_date": to_date},
                timeout=15.0,
            )
            if response.status_code == 200:
                return response.json()
    except Exception:
        pass
    return {"total_billed": 0, "total_collected": 0, "invoice_count": 0}


def _categorize_transactions(transactions: list[dict]) -> AutoCollectedData:
    """Categorize transactions into income and expenses with breakdowns."""
    income_by_category: dict[str, float] = {}
    expense_by_category: dict[str, float] = {}
    total_income = 0.0
    total_expenses = 0.0

    for t in transactions:
        amount = float(t.get("amount", 0))
        category = t.get("category", "uncategorized") or "uncategorized"

        if amount > 0:
            total_income += amount
            income_by_category[category] = income_by_category.get(category, 0) + amount
        elif amount < 0:
            abs_amount = abs(amount)
            total_expenses += abs_amount
            expense_by_category[category] = expense_by_category.get(category, 0) + abs_amount

    income_breakdown = [{"category": k, "amount": round(v, 2)} for k, v in sorted(income_by_category.items(), key=lambda x: -x[1])]
    expense_breakdown = [{"category": k, "amount": round(v, 2)} for k, v in sorted(expense_by_category.items(), key=lambda x: -x[1])]

    return AutoCollectedData(
        period_start="",
        period_end="",
        total_income=round(total_income, 2),
        income_breakdown=income_breakdown,
        total_expenses=round(total_expenses, 2),
        expense_breakdown=expense_breakdown,
        invoice_income=0,
        invoice_count=0,
        transaction_count=len(transactions),
        net_profit=round(total_income - total_expenses, 2),
    )


_HMRC_EXPENSE_MAP = {
    "fuel": "travelCosts",
    "transport": "travelCosts",
    "travel": "travelCosts",
    "mileage": "travelCosts",
    "vehicle_mileage": "travelCosts",
    "rent": "premisesRunningCosts",
    "utilities": "premisesRunningCosts",
    "premises": "premisesRunningCosts",
    "office_supplies": "adminCosts",
    "office_costs": "adminCosts",
    "office": "adminCosts",
    "stationery": "adminCosts",
    "home_office": "premisesRunningCosts",
    "use_of_home": "premisesRunningCosts",
    "advertising": "advertisingCosts",
    "marketing": "advertisingCosts",
    "professional_services": "professionalFees",
    "professional_fees": "professionalFees",
    "legal": "professionalFees",
    "accounting": "professionalFees",
    "staff_costs": "staffCosts",
    "wages": "staffCosts",
    "stock": "costOfGoods",
    "materials": "costOfGoods",
    "stock_materials": "costOfGoods",
    "cost_of_goods": "costOfGoods",
    "insurance": "other",
    "bank_charges": "other",
    "financial_costs": "other",
    "interest": "other",
    "subscriptions": "adminCosts",
    "equipment": "adminCosts",
    "training": "professionalFees",
    "clothing": "other",
    "uniform": "other",
    "repairs": "premisesRunningCosts",
    "maintenance": "premisesRunningCosts",
    "phone": "adminCosts",
    "internet": "adminCosts",
    "food_and_drink": "other",
    "groceries": "other",
    "health": "other",
    "tax": "other",
}


@app.post("/prepare/quarterly", response_model=PreparedQuarterlyReport)
async def prepare_quarterly_report(
    tax_year: int = 2025,
    quarter: str = "Q1",
    user_id: str = Depends(get_current_user_id),
    bearer_token: str = Depends(get_bearer_token),
    limits: PlanLimits = Depends(get_plan_limits),
):
    """
    Auto-collect data from transactions + invoices and prepare a quarterly HMRC report.
    Returns ready-to-review report. User must confirm before submission.
    """
    quarters = _quarter_dates(tax_year)
    q = next((q for q in quarters if q.quarter == quarter), None)
    if not q:
        raise HTTPException(status_code=400, detail=f"Invalid quarter: {quarter}. Use Q1, Q2, Q3, or Q4")

    ps = datetime.date.fromisoformat(q.period_start)
    pe = datetime.date.fromisoformat(q.period_end)
    effective_start, cov_meta, cov_status = _coverage_for_period(
        ps, pe, limits.transaction_history_months
    )
    transactions = await _fetch_transactions(bearer_token, q.period_start, q.period_end)
    transactions = _txn_dict_min_date(transactions, effective_start)
    collected = _categorize_transactions(transactions)
    collected.period_start = q.period_start
    collected.period_end = q.period_end

    invoice_data = await _fetch_invoice_income(bearer_token, q.period_start, q.period_end)
    collected.invoice_income = float(invoice_data.get("total_collected", 0))
    collected.invoice_count = int(invoice_data.get("invoice_count", 0))

    turnover = collected.total_income if collected.total_income > 0 else collected.invoice_income

    hmrc_expenses: dict[str, float] = {
        "costOfGoods": 0, "staffCosts": 0, "travelCosts": 0,
        "premisesRunningCosts": 0, "adminCosts": 0, "advertisingCosts": 0,
        "professionalFees": 0, "other": 0,
    }
    for item in collected.expense_breakdown:
        hmrc_field = _HMRC_EXPENSE_MAP.get(item["category"], "other")
        hmrc_expenses[hmrc_field] += item["amount"]

    hmrc_expenses = {k: round(v, 2) for k, v in hmrc_expenses.items()}

    hmrc_payload = {
        "periodDates": {
            "periodStartDate": q.period_start,
            "periodEndDate": q.period_end,
        },
        "periodIncome": {
            "turnover": round(turnover, 2),
            "other": 0,
        },
        "periodExpenses": hmrc_expenses,
    }

    rates, _ = await _rates_for_period_end(datetime.date.fromisoformat(q.period_end))
    annual_profit = max((turnover - collected.total_expenses) * 4, 0)
    pa = _personal_allowance_effective(annual_profit, rates)
    taxable = max(annual_profit - pa, 0)
    bands = rates.get("income_tax_bands") or _default_income_tax_bands()
    b, h, a = _income_tax_from_bands(taxable, bands)
    estimated_tax = round((b + h + a) / 4, 2)

    msg_tail = ""
    if cov_status == "partial":
        msg_tail = (
            f" Coverage: partial — data before {cov_meta['retention_cutoff_date']} excluded per plan retention."
        )

    return PreparedQuarterlyReport(
        status="ready_for_review",
        quarter=quarter,
        tax_year=f"{tax_year}/{tax_year + 1}",
        collected_data=collected,
        hmrc_periodic_update=hmrc_payload,
        estimated_tax=estimated_tax,
        message=f"Quarterly report for {quarter} ({q.period_start} to {q.period_end}) prepared. "
                f"Income: \u00a3{turnover:.2f}, Expenses: \u00a3{collected.total_expenses:.2f}, "
                f"Estimated quarterly tax: \u00a3{estimated_tax:.2f}. "
                f"Review and confirm to submit to HMRC.{msg_tail}",
        coverage_status=cov_status,
        coverage=cov_meta,
    )


@app.post("/prepare/annual", response_model=PreparedAnnualReport)
async def prepare_annual_report(
    tax_year: int = 2025,
    user_id: str = Depends(get_current_user_id),
    bearer_token: str = Depends(get_bearer_token),
    limits: PlanLimits = Depends(get_plan_limits),
):
    """
    Auto-collect full year data and prepare final declaration for HMRC.
    Returns ready-to-review report. User must confirm before submission.
    """
    start = f"{tax_year}-04-06"
    end = f"{tax_year + 1}-04-05"

    ps = datetime.date.fromisoformat(start)
    pe = datetime.date.fromisoformat(end)
    effective_start, cov_meta, cov_status = _coverage_for_period(
        ps, pe, limits.transaction_history_months
    )
    transactions = await _fetch_transactions(bearer_token, start, end)
    transactions = _txn_dict_min_date(transactions, effective_start)
    collected = _categorize_transactions(transactions)

    invoice_data = await _fetch_invoice_income(bearer_token, start, end)
    invoice_income = float(invoice_data.get("total_collected", 0))

    total_income = max(collected.total_income, invoice_income)
    total_expenses = collected.total_expenses

    rates, _ = await _rates_for_period_end(datetime.date.fromisoformat(end))
    profit = max(total_income - total_expenses, 0)
    pa = _personal_allowance_effective(profit, rates)
    taxable = max(profit - pa, 0)
    bands = rates.get("income_tax_bands") or _default_income_tax_bands()
    bt, ht, at = _income_tax_from_bands(taxable, bands)
    income_tax = bt + ht + at
    ni4 = _class4_nic_from_rates(profit, rates)
    ni2 = _class2_annual_from_rates(profit, rates)

    total_tax = round(income_tax + ni4 + ni2, 2)
    personal_allowance = round(pa, 2)

    hmrc_payload = {
        "tax_year_start": start,
        "tax_year_end": end,
        "total_income": round(total_income, 2),
        "total_expenses": round(total_expenses, 2),
        "total_allowances": personal_allowance,
        "loss_brought_forward": 0,
        "declaration": "true_and_complete",
    }

    quarter_summaries = []
    for q in _quarter_dates(tax_year):
        q_transactions = [t for t in transactions if q.period_start <= t.get("date", "") <= q.period_end]
        q_income = sum(float(t.get("amount", 0)) for t in q_transactions if float(t.get("amount", 0)) > 0)
        q_expenses = sum(abs(float(t.get("amount", 0))) for t in q_transactions if float(t.get("amount", 0)) < 0)
        quarter_summaries.append({
            "quarter": q.quarter,
            "period": f"{q.period_start} to {q.period_end}",
            "income": round(q_income, 2),
            "expenses": round(q_expenses, 2),
            "profit": round(q_income - q_expenses, 2),
        })

    msg_tail = ""
    if cov_status == "partial":
        msg_tail = (
            f" Coverage: partial — data before {cov_meta['retention_cutoff_date']} excluded per plan retention."
        )

    return PreparedAnnualReport(
        status="ready_for_review",
        tax_year=f"{tax_year}/{tax_year + 1}",
        quarters=quarter_summaries,
        total_income=round(total_income, 2),
        total_expenses=round(total_expenses, 2),
        total_allowances=personal_allowance,
        losses_brought_forward=0,
        taxable_income=round(taxable, 2),
        income_tax=round(income_tax, 2),
        ni_class2=ni2,
        ni_class4=round(ni4, 2),
        total_tax_due=total_tax,
        hmrc_final_declaration=hmrc_payload,
        message=f"Annual report for {tax_year}/{tax_year + 1} prepared. "
                f"Total income: \u00a3{total_income:.2f}, Expenses: \u00a3{total_expenses:.2f}, "
                f"Tax due: \u00a3{total_tax:.2f} (Income Tax: \u00a3{income_tax:.2f} + NI: \u00a3{ni4 + ni2:.2f}). "
                f"Review and confirm to submit to HMRC as Final Declaration.{msg_tail}",
        coverage_status=cov_status,
        coverage=cov_meta,
    )

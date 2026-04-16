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
  GET  /rules/changelog                     — GOV.UK Content API detection log
  GET  /rules/diff                          — core rule diff between two tax years
  POST /admin/regulatory/scrape-live        — fetch GOV.UK HTML, extract £ amounts (RU.5–8 baseline)
  POST /admin/regulatory/scrape-parse       — fetch + table/heuristic parse (employer_rates, NI, IT, CGT)
  POST /admin/regulatory/parse-budget-annex — Budget annex-A HTML → amount hints
  POST /admin/regulatory/validate-ai-diff   — GPT plausibility on diff between two frozen tax years
  POST /rules/analyze-user                  — AI: personalised impact analysis
  GET  /rules/versions                      — rule file versions and status
"""

from __future__ import annotations

import json
import logging
import os
import sys
import uuid
import xml.etree.ElementTree as ET
from contextlib import asynccontextmanager
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

for _rp in Path(__file__).resolve().parents:
    if (_rp / "libs").exists():
        _rps = str(_rp)
        if _rps not in sys.path:
            sys.path.append(_rps)
        break

from libs.shared_http.request_id import RequestIdMiddleware

from app.collector import GOVUK_WATCH_SOURCES, check_govuk_sources_for_updates, fetch_and_extract_govuk_page
from app.collector.govuk_scraper import fetch_html, scrape_and_parse
from app.scheduler.cron import register_regulatory_jobs
from app.validator import diff_tax_rule_dicts, validate_rate_change_ai, validate_tax_year_rules

logger = logging.getLogger(__name__)


def _regulatory_cors_origins() -> list[str]:
    raw = os.getenv(
        "REGULATORY_CORS_ORIGINS",
        "http://localhost:3000,http://localhost:3001",
    )
    return [part.strip() for part in raw.split(",") if part.strip()]


DATA_DIR = Path(__file__).parent / "data"
GOVUK_WATCH_STATE_PATH = DATA_DIR / "govuk_content_watch.json"
RULES_CHANGELOG_PATH = DATA_DIR / "rules_changelog.json"
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
SKIP_EXTERNAL_GOVUK_WATCH = os.environ.get("REGULATORY_SKIP_EXTERNAL_WATCH", "").strip() in ("1", "true", "yes")

# ── Tax year JSON files available ───────────────────────────────────────────
_RULE_FILES: Dict[str, str] = {
    "2024-25": "uk_tax_2024_25.json",
    "2025-26": "uk_tax_2025_26.json",
    "2026-27": "uk_tax_2026_27.json",
}

_rules_cache: Dict[str, Dict[str, Any]] = {}

# ── In-memory stores (reset on restart) ─────────────────────────────────────
_audit_log: List[Dict[str, Any]] = []
_pending_updates: List[Dict[str, Any]] = []
_detected_changes: List[Dict[str, Any]] = []
_last_govuk_check: Optional[str] = None
_last_govuk_content_check: Optional[str] = None
_govuk_watch_snapshot: Dict[str, Any] = {}
_change_analysis_cache: Optional[Dict[str, Any]] = None

GOV_UK_TAX_RSS = "https://www.gov.uk/search/all.atom?keywords=tax+self-employed&order=updated-newest"
GOV_UK_HMRC_RSS = "https://www.gov.uk/government/organisations/hm-revenue-customs.atom"


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
        except Exception as exc:
            logger.warning("regulatory: could not load rules for %s: %s", year, exc)
    return result


def _read_json_file(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def _write_json_file(path: Path, data: Any) -> None:
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def _append_rules_changelog(events: List[Dict[str, Any]]) -> None:
    if not events:
        return
    existing = _read_json_file(RULES_CHANGELOG_PATH, [])
    if not isinstance(existing, list):
        existing = []
    ts = datetime.now(timezone.utc).isoformat()
    for ev in events:
        existing.append({"recorded_at": ts, "kind": "govuk_content_public_updated_at", **ev})
    _write_json_file(RULES_CHANGELOG_PATH, existing)


def _core_rules_subset(rules: Dict[str, Any]) -> Dict[str, Any]:
    keys = (
        "income_tax",
        "national_insurance",
        "allowances",
        "mtd_itsa",
        "vat",
        "student_loans",
    )
    return {k: rules[k] for k in keys if k in rules}


# ── GOV.UK RSS monitor ───────────────────────────────────────────────────────

async def _fetch_govuk_changes() -> List[Dict[str, Any]]:
    """Fetch recent HMRC/tax updates from GOV.UK atom feed."""
    found: List[Dict[str, Any]] = []
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(GOV_UK_HMRC_RSS, follow_redirects=True)
            if not resp.is_success:
                return found
            root = ET.fromstring(resp.text)
            ns = {"atom": "http://www.w3.org/2005/Atom"}
            for entry in root.findall("atom:entry", ns)[:10]:
                title = entry.findtext("atom:title", "", ns)
                link_el = entry.find("atom:link", ns)
                link = link_el.get("href", "") if link_el is not None else ""
                updated = entry.findtext("atom:updated", "", ns)
                summary = entry.findtext("atom:summary", "", ns)
                found.append({
                    "id": entry.findtext("atom:id", "", ns),
                    "title": title,
                    "link": link,
                    "updated": updated,
                    "summary": summary[:300] if summary else "",
                    "source": "GOV.UK HMRC feed",
                })
    except Exception as exc:
        logger.warning("GOV.UK RSS fetch failed: %s", exc)
    return found


async def _monitor_hmrc_changes() -> None:
    """APScheduler job: GOV.UK Content API (page metadata) + HMRC Atom feed."""
    global _last_govuk_check, _last_govuk_content_check, _detected_changes, _govuk_watch_snapshot
    _last_govuk_check = datetime.now(timezone.utc).isoformat()
    merged_feed: List[Dict[str, Any]] = []

    prev_state = _read_json_file(GOVUK_WATCH_STATE_PATH, {})
    if not isinstance(prev_state, dict):
        prev_state = {}
    try:
        async with httpx.AsyncClient(timeout=25.0) as client:
            content_events, new_state = await check_govuk_sources_for_updates(client, prev_state)
        _write_json_file(GOVUK_WATCH_STATE_PATH, new_state)
        _govuk_watch_snapshot = new_state
        _last_govuk_content_check = datetime.now(timezone.utc).isoformat()
        if content_events:
            _append_rules_changelog(content_events)
            for ev in content_events:
                merged_feed.append({
                    "id": f"govuk-content:{ev['source_id']}",
                    "title": f"GOV.UK updated: {ev.get('label', ev['source_id'])}",
                    "link": f"https://www.gov.uk{ev['path']}",
                    "updated": ev.get("public_updated_at") or "",
                    "summary": (
                        f"public_updated_at: {ev.get('previous_public_updated_at')!r} → {ev.get('public_updated_at')!r}"
                    ),
                    "source": "GOV.UK Content API",
                })
            _audit_log.append({
                "id": str(uuid.uuid4()),
                "event": "govuk_content_updated_at_change",
                "timestamp": _last_govuk_content_check,
                "detail": f"{len(content_events)} GOV.UK tax page(s) show new public_updated_at — review JSON rules",
                "actor": "scheduler",
            })
    except Exception as exc:
        logger.warning("GOV.UK Content API watch failed: %s", exc)

    atom_items = await _fetch_govuk_changes()
    merged_feed.extend(atom_items)
    if merged_feed:
        _detected_changes = merged_feed
    if atom_items:
        _audit_log.append({
            "id": str(uuid.uuid4()),
            "event": "hmrc_feed_check",
            "timestamp": _last_govuk_check,
            "detail": f"Fetched {len(atom_items)} items from GOV.UK HMRC Atom feed",
            "actor": "scheduler",
        })
    logger.info(
        "Regulatory monitor: %d feed entries (content+atom), atom=%d at %s",
        len(_detected_changes),
        len(atom_items),
        _last_govuk_check,
    )


async def _weekly_govuk_parse() -> None:
    """RU.15 weekly: re-fetch + parse key GOV.UK pages (audit only unless owner applies JSON)."""
    ts = datetime.now(timezone.utc).isoformat()
    done: list[str] = []
    ty = _tax_year_for_date(date.today())
    for sid in ("employer_rates", "self_employed_ni", "income_tax_rates"):
        try:
            await scrape_and_parse(sid, ty)
            done.append(sid)
        except Exception as exc:
            logger.warning("weekly_govuk_parse %s: %s", sid, exc)
    _audit_log.append({
        "id": str(uuid.uuid4()),
        "event": "weekly_govuk_parse",
        "timestamp": ts,
        "detail": f"sources_ok={done}",
        "actor": "scheduler",
    })


# ── FastAPI app ──────────────────────────────────────────────────────────────

_scheduler = AsyncIOScheduler()


@asynccontextmanager
async def lifespan(app_instance: FastAPI):
    for y in _RULE_FILES:
        try:
            for issue in validate_tax_year_rules(_load_rules(y)):
                logger.warning("regulatory rules sanity [%s]: %s", y, issue)
        except Exception as exc:
            logger.warning("regulatory rules sanity failed [%s]: %s", y, exc)
    if not SKIP_EXTERNAL_GOVUK_WATCH:
        register_regulatory_jobs(
            _scheduler,
            daily_job=_monitor_hmrc_changes,
            weekly_job=_weekly_govuk_parse,
            skip_external=False,
        )
        _scheduler.start()
        await _monitor_hmrc_changes()
    else:
        logger.info("REGULATORY_SKIP_EXTERNAL_WATCH set — GOV.UK RSS/Content API checks disabled")
    yield
    if not SKIP_EXTERNAL_GOVUK_WATCH:
        _scheduler.shutdown(wait=False)


app = FastAPI(
    title="Regulatory Service",
    description="UK tax rules, rates, thresholds and deadlines — single source of truth",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(RequestIdMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_regulatory_cors_origins(),
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


class ScrapeLiveRequest(BaseModel):
    path: Optional[str] = None
    source_id: Optional[str] = None


class ScrapeParseRequest(BaseModel):
    source_id: str
    tax_year: str = "2025-26"


class BudgetAnnexRequest(BaseModel):
    budget_year: int = 2025


class ValidateAiDiffRequest(BaseModel):
    tax_year_left: str = "2024-25"
    tax_year_right: str = "2025-26"
    source_url: str = "https://www.gov.uk/"


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
        except Exception as exc:
            logger.warning("regulatory: next-year MTD warning skipped: %s", exc)

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


@app.get("/rules/changelog")
async def get_rules_changelog(
    limit: int = Query(100, ge=1, le=500),
) -> Dict[str, Any]:
    """Append-only log of GOV.UK Content API detections and other rule events."""
    entries = _read_json_file(RULES_CHANGELOG_PATH, [])
    if not isinstance(entries, list):
        entries = []
    tail = entries[-limit:] if limit else entries
    return {"entries": tail, "total": len(entries), "returned": len(tail)}


@app.get("/rules/diff")
async def get_rules_diff(
    from_year: str = Query(..., alias="from", description="Tax year e.g. 2024-25"),
    to_year: str = Query(..., alias="to", description="Tax year e.g. 2025-26"),
) -> Dict[str, Any]:
    """Structural diff of core rule blocks between two frozen JSON tax years."""
    old = _load_rules(from_year)
    new = _load_rules(to_year)
    changes = diff_tax_rule_dicts(_core_rules_subset(old), _core_rules_subset(new))
    return {
        "from": from_year,
        "to": to_year,
        "changes": changes,
        "total": len(changes),
    }


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

    class2 = ni.get("class_2", {})
    spt = float(class2.get("small_profits_threshold", 6725))
    lpl_c2 = float(class2.get("lower_profits_limit", 12570))
    wk_vol = float(class2.get("weekly_rate_voluntary", class2.get("weekly_rate", 3.45)))
    mandatory_ge_lpl = class2.get("mandatory_annual_cash_gbp_when_profits_ge_lower_limit")
    inc = float(req.estimated_annual_income)
    if mandatory_ge_lpl is not None:
        if inc < spt:
            pass
        elif inc < lpl_c2:
            warnings.append(
                "Class 2: profits are in the voluntary band — consider paying Class 2 for National Insurance credits "
                f"(about £{wk_vol * 52:.2f}/year at £{wk_vol}/week if you choose to pay)."
            )
        else:
            c2_cash = float(mandatory_ge_lpl)
            if c2_cash > 0:
                estimated_tax += c2_cash
                applicable_rules.append({
                    "rule": "Class 2 NI (cash due)",
                    "rate": f"£{wk_vol}/week reference",
                    "on": "annual",
                    "tax": f"£{c2_cash:.2f}",
                })
    elif inc >= lpl_c2:
        class2_annual = wk_vol * 52
        estimated_tax += class2_annual
        applicable_rules.append({
            "rule": "Class 2 NI",
            "rate": f"£{wk_vol}/week",
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


# ── REG.17: Compliance score ──────────────────────────────────────────────────

@app.get("/admin/regulatory/compliance-score")
async def get_compliance_score() -> Dict[str, Any]:
    """
    REG.17 — Compliance score: percentage of rule files that are 'final' status
    and up-to-date relative to today.
    """
    total = len(_RULE_FILES)
    final_count = 0
    outdated: List[str] = []
    for year in _RULE_FILES:
        try:
            rules = _load_rules(year)
            if rules.get("status") == "final":
                final_count += 1
                eff_to = rules.get("effective_to", "")
                if eff_to and date.fromisoformat(eff_to) < date.today():
                    outdated.append(year)
        except Exception:
            pass
    score = round((final_count / total) * 100, 1) if total else 0.0
    return {
        "compliance_score_pct": score,
        "total_rule_files": total,
        "final_files": final_count,
        "draft_files": total - final_count,
        "outdated_files": outdated,
        "status": "green" if score >= 95 else "amber" if score >= 80 else "red",
        "as_of": date.today().isoformat(),
    }


# ── REG.13: Admin regulatory stats ────────────────────────────────────────────

@app.get("/admin/regulatory/stats")
async def get_regulatory_stats() -> Dict[str, Any]:
    """
    REG.13 — KPI data for the admin regulatory dashboard:
    active rules count, recent changes, estimated affected users, compliance%.
    """
    current_year = _tax_year_for_date(date.today())
    try:
        current_rules = _load_rules(current_year)
    except Exception:
        current_rules = {}

    # Count distinct rule sections
    rule_sections = [k for k in current_rules if not k.startswith("_") and k not in ("tax_year", "version", "status", "source", "effective_from", "effective_to")]
    active_rules_count = len(rule_sections)

    # Changes in the last 90 days
    since_90 = (date.today().replace(year=date.today().year - 1 if date.today().month <= 3 else date.today().year)).isoformat()
    recent_changes: List[Dict[str, Any]] = []
    for rules in _all_loaded_rules():
        eff_from = rules.get("effective_from", "")
        for change in rules.get("regulatory_changes_from_prior_year", []):
            recent_changes.append({
                "tax_year": rules["tax_year"],
                "area": change.get("area", ""),
                "description": change.get("description", ""),
                "impact": change.get("impact", "low"),
            })

    # Estimated affected users: based on MTD threshold
    mtd = current_rules.get("mtd_itsa", {})
    mtd_threshold = mtd.get("threshold", 50000)
    affected_pct = 35  # estimated % of self-employed above £50k threshold

    compliance = await get_compliance_score()

    return {
        "active_rules_count": active_rules_count,
        "tax_year": current_year,
        "recent_changes_count": len(recent_changes),
        "recent_changes": recent_changes[:10],
        "affected_users_pct": affected_pct,
        "mtd_threshold": mtd_threshold,
        "compliance_score_pct": compliance["compliance_score_pct"],
        "compliance_status": compliance["status"],
        "govuk_feed_items": len(_detected_changes),
        "last_feed_check": _last_govuk_check,
        "last_govuk_content_check": _last_govuk_content_check,
        "govuk_watched_pages": len(_govuk_watch_snapshot) if _govuk_watch_snapshot else len(GOVUK_WATCH_SOURCES),
        "pending_updates_count": len(_pending_updates),
        "audit_log_count": len(_audit_log),
    }


# ── REG.12: AI analysis of detected changes ───────────────────────────────────

class ChangeAnalysisRequest(BaseModel):
    force_refresh: bool = False


@app.post("/admin/regulatory/analyze-changes")
async def analyze_regulatory_changes(req: ChangeAnalysisRequest) -> Dict[str, Any]:
    """
    REG.12 — GPT-4o-mini analyses detected GOV.UK changes:
    what changed, who is affected, what code needs updating.
    Falls back to rule-based summary when OpenAI unavailable.
    """
    global _change_analysis_cache

    if _change_analysis_cache and not req.force_refresh:
        return _change_analysis_cache

    feed_items = _detected_changes[:5]
    rule_changes: List[Dict[str, Any]] = []
    for rules in _all_loaded_rules():
        for change in rules.get("regulatory_changes_from_prior_year", []):
            rule_changes.append({
                "tax_year": rules["tax_year"],
                **change,
            })

    recommendations: List[Dict[str, Any]] = []
    alerts: List[Dict[str, Any]] = []

    # Rule-based: check MTD thresholds across years for significant changes
    years = list(_RULE_FILES.keys())
    for i in range(len(years) - 1):
        try:
            old_r = _load_rules(years[i])
            new_r = _load_rules(years[i + 1])
            old_mtd = old_r.get("mtd_itsa", {}).get("threshold")
            new_mtd = new_r.get("mtd_itsa", {}).get("threshold")
            if old_mtd and new_mtd and old_mtd != new_mtd:
                alerts.append({
                    "severity": "high",
                    "area": "MTD ITSA",
                    "change": f"Threshold changed from £{old_mtd:,} to £{new_mtd:,} ({years[i]} → {years[i+1]})",
                    "affects": "All users with income near threshold",
                    "action": f"Update MTD eligibility check logic — threshold now £{new_mtd:,}",
                    "files_to_update": ["services/mtd-agent/app/main.py", "services/regulatory-service/app/data/"],
                })
        except Exception:
            pass

    # AI narrative
    ai_summary = None
    ai_dev_notes = None
    if OPENAI_API_KEY and (feed_items or rule_changes):
        try:
            changes_text = "\n".join(
                f"- {item.get('title', item.get('area', 'Unknown'))}: {item.get('summary', item.get('description', ''))[:200]}"
                for item in (feed_items or rule_changes)[:5]
            )
            prompt = (
                "You are a UK tax compliance engineer reviewing regulatory changes. "
                f"Recent changes detected:\n{changes_text}\n\n"
                "Provide:\n1. One-sentence summary of what changed\n"
                "2. Who is affected (type of taxpayer)\n"
                "3. One specific code change recommendation\n"
                "Be brief and technical."
            )
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
                    json={
                        "model": "gpt-4o-mini",
                        "messages": [{"role": "user", "content": prompt}],
                        "max_tokens": 300,
                    },
                )
                if resp.is_success:
                    ai_summary = resp.json()["choices"][0]["message"]["content"].strip()
        except Exception as exc:
            logger.warning("OpenAI change analysis failed: %s", exc)

    result = {
        "analyzed_at": datetime.now(timezone.utc).isoformat(),
        "feed_items_analyzed": len(feed_items),
        "rule_changes_analyzed": len(rule_changes),
        "alerts": alerts,
        "recommendations": recommendations,
        "ai_summary": ai_summary,
        "ai_dev_notes": ai_dev_notes,
        "govuk_feed_items": feed_items[:3],
    }
    _change_analysis_cache = result

    _audit_log.append({
        "id": str(uuid.uuid4()),
        "event": "change_analysis_run",
        "timestamp": result["analyzed_at"],
        "detail": f"Analyzed {len(feed_items)} feed items, {len(rule_changes)} rule changes, {len(alerts)} alerts",
        "actor": "admin",
    })
    return result


# ── REG.15: Developer recommendations ────────────────────────────────────────

@app.get("/admin/regulatory/dev-recommendations")
async def get_dev_recommendations() -> Dict[str, Any]:
    """
    REG.15 — AI recommendations for code changes based on regulatory diffs.
    Compares consecutive tax year files to identify threshold/rate changes.
    """
    recs: List[Dict[str, Any]] = []
    years = sorted(_RULE_FILES.keys())
    for i in range(len(years) - 1):
        try:
            old_r = _load_rules(years[i])
            new_r = _load_rules(years[i + 1])
            label = f"{years[i]} → {years[i+1]}"

            # MTD threshold diff
            old_mtd = old_r.get("mtd_itsa", {}).get("threshold")
            new_mtd = new_r.get("mtd_itsa", {}).get("threshold")
            if old_mtd != new_mtd:
                recs.append({
                    "priority": "high",
                    "area": "MTD ITSA threshold",
                    "change": label,
                    "old_value": f"£{old_mtd:,}" if old_mtd else "N/A",
                    "new_value": f"£{new_mtd:,}" if new_mtd else "N/A",
                    "recommendation": f"Update MTD threshold check in mtd-agent and any hardcoded £{old_mtd:,} references",
                    "files": ["services/mtd-agent/app/main.py", "apps/web-portal/pages/tax.tsx"],
                })

            # Class 4 NI rate diff
            old_ni4 = old_r.get("national_insurance", {}).get("class_4", {}).get("main_rate")
            new_ni4 = new_r.get("national_insurance", {}).get("class_4", {}).get("main_rate")
            if old_ni4 != new_ni4:
                recs.append({
                    "priority": "medium",
                    "area": "Class 4 NI rate",
                    "change": label,
                    "old_value": f"{int((old_ni4 or 0)*100)}%" if old_ni4 else "N/A",
                    "new_value": f"{int((new_ni4 or 0)*100)}%" if new_ni4 else "N/A",
                    "recommendation": "Check NI calculator for hardcoded rate; regulatory-service is now source of truth",
                    "files": ["services/regulatory-service/app/data/"],
                })

            # Personal allowance diff
            old_pa = old_r.get("income_tax", {}).get("personal_allowance")
            new_pa = new_r.get("income_tax", {}).get("personal_allowance")
            if old_pa != new_pa:
                recs.append({
                    "priority": "medium",
                    "area": "Personal Allowance",
                    "change": label,
                    "old_value": f"£{old_pa:,}" if old_pa else "N/A",
                    "new_value": f"£{new_pa:,}" if new_pa else "N/A",
                    "recommendation": "Personal Allowance changed — verify tax calculator and self-assessment pages",
                    "files": ["apps/web-portal/pages/calculators/"],
                })

            # VAT threshold diff
            old_vat = old_r.get("vat", {}).get("registration_threshold")
            new_vat = new_r.get("vat", {}).get("registration_threshold")
            if old_vat != new_vat:
                recs.append({
                    "priority": "medium",
                    "area": "VAT registration threshold",
                    "change": label,
                    "old_value": f"£{old_vat:,}" if old_vat else "N/A",
                    "new_value": f"£{new_vat:,}" if new_vat else "N/A",
                    "recommendation": "Update VAT eligibility check and user-facing threshold warning",
                    "files": ["services/regulatory-service/app/data/"],
                })
        except Exception:
            pass

    return {
        "recommendations": recs,
        "total": len(recs),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "note": "Based on diff between consecutive tax year rule files",
    }


# ── REG.16: Pending rule updates + owner approval ─────────────────────────────

class RuleUpdateProposal(BaseModel):
    tax_year: str
    field_path: str
    old_value: Any
    new_value: Any
    reason: str
    proposed_by: str = "system"


@app.post("/admin/regulatory/propose-update")
async def propose_rule_update(proposal: RuleUpdateProposal) -> Dict[str, Any]:
    """REG.16 — Propose a rule update for owner approval."""
    item = {
        "id": str(uuid.uuid4()),
        "tax_year": proposal.tax_year,
        "field_path": proposal.field_path,
        "old_value": proposal.old_value,
        "new_value": proposal.new_value,
        "reason": proposal.reason,
        "proposed_by": proposal.proposed_by,
        "status": "pending",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    _pending_updates.append(item)
    _audit_log.append({
        "id": str(uuid.uuid4()),
        "event": "rule_update_proposed",
        "timestamp": item["created_at"],
        "detail": f"{proposal.field_path} in {proposal.tax_year}: {proposal.old_value} → {proposal.new_value}",
        "actor": proposal.proposed_by,
    })
    return {"status": "proposed", "update_id": item["id"]}


@app.get("/admin/regulatory/pending-updates")
async def list_pending_updates() -> Dict[str, Any]:
    """REG.16 — List all pending rule updates awaiting owner approval."""
    return {"pending": _pending_updates, "total": len(_pending_updates)}


@app.post("/admin/regulatory/approve-update/{update_id}")
async def approve_rule_update(update_id: str, approved_by: str = Query("owner")) -> Dict[str, Any]:
    """REG.16 — Owner approves a pending rule update (marks as approved; actual file edit is manual)."""
    item = next((u for u in _pending_updates if u["id"] == update_id), None)
    if not item:
        raise HTTPException(status_code=404, detail="Update not found")
    item["status"] = "approved"
    item["approved_by"] = approved_by
    item["approved_at"] = datetime.now(timezone.utc).isoformat()
    _audit_log.append({
        "id": str(uuid.uuid4()),
        "event": "rule_update_approved",
        "timestamp": item["approved_at"],
        "detail": f"Update {update_id} approved by {approved_by}",
        "actor": approved_by,
    })
    return {"status": "approved", "update_id": update_id}


@app.post("/admin/regulatory/reject-update/{update_id}")
async def reject_rule_update(update_id: str, rejected_by: str = Query("owner")) -> Dict[str, Any]:
    """REG.16 — Owner rejects a pending rule update."""
    item = next((u for u in _pending_updates if u["id"] == update_id), None)
    if not item:
        raise HTTPException(status_code=404, detail="Update not found")
    item["status"] = "rejected"
    item["rejected_by"] = rejected_by
    item["rejected_at"] = datetime.now(timezone.utc).isoformat()
    _audit_log.append({
        "id": str(uuid.uuid4()),
        "event": "rule_update_rejected",
        "timestamp": item["rejected_at"],
        "detail": f"Update {update_id} rejected by {rejected_by}",
        "actor": rejected_by,
    })
    return {"status": "rejected", "update_id": update_id}


# ── REG.14: User notification dispatch ───────────────────────────────────────

class NotificationRequest(BaseModel):
    affected_user_emails: List[str]
    change_summary: str
    tax_year: str = "2025-26"
    notification_type: str = "email"


@app.post("/admin/regulatory/notify-users")
async def notify_users(req: NotificationRequest) -> Dict[str, Any]:
    """
    REG.14 — Dispatch notifications to affected users about regulatory changes.
    Logs intent; actual delivery requires email/push integration.
    """
    notification_id = str(uuid.uuid4())
    ts = datetime.now(timezone.utc).isoformat()
    _audit_log.append({
        "id": str(uuid.uuid4()),
        "event": "users_notified",
        "timestamp": ts,
        "detail": f"Notification {notification_id}: {len(req.affected_user_emails)} users — {req.change_summary[:100]}",
        "actor": "admin",
        "notification_id": notification_id,
        "affected_count": len(req.affected_user_emails),
        "notification_type": req.notification_type,
    })
    return {
        "notification_id": notification_id,
        "dispatched": len(req.affected_user_emails),
        "notification_type": req.notification_type,
        "status": "queued",
        "note": "Delivery requires SMTP/push integration — logged for audit",
    }


# ── REG.18: Audit trail ────────────────────────────────────────────────────────

@app.get("/admin/regulatory/audit-trail")
async def get_audit_trail(limit: int = Query(50, ge=1, le=200)) -> Dict[str, Any]:
    """REG.18 — Return audit log of all regulatory events (rule changes, analyses, notifications)."""
    return {
        "events": list(reversed(_audit_log))[:limit],
        "total": len(_audit_log),
    }


# ── REG.20: Budget analyzer ────────────────────────────────────────────────────

class BudgetAnalysisRequest(BaseModel):
    budget_name: str = "Spring Statement 2026"
    raw_text: Optional[str] = None
    url: Optional[str] = None


@app.post("/rules/budget/analyze")
async def analyze_budget(req: BudgetAnalysisRequest) -> Dict[str, Any]:
    """
    REG.20 — Analyze UK Budget announcements for tax changes.
    Extracts key figures and compares with current rules.
    """
    extracted_changes: List[Dict[str, Any]] = []
    ai_analysis = None

    source_text = req.raw_text or ""

    if req.url and not source_text:
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(req.url, follow_redirects=True)
                if resp.is_success:
                    source_text = resp.text[:8000]
        except Exception as exc:
            logger.warning("Budget URL fetch failed: %s", exc)

    if source_text and OPENAI_API_KEY:
        try:
            prompt = (
                f"You are a UK tax analyst. Extract key tax changes from this UK Budget announcement: '{req.budget_name}'.\n"
                f"Text excerpt: {source_text[:3000]}\n\n"
                "Extract and return JSON with: income_tax_changes, ni_changes, vat_changes, mtd_changes, other_changes. "
                "Each entry: {area, change_description, old_value, new_value, effective_date}. "
                "Return only valid JSON."
            )
            async with httpx.AsyncClient(timeout=20.0) as client:
                resp = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
                    json={
                        "model": "gpt-4o-mini",
                        "messages": [{"role": "user", "content": prompt}],
                        "max_tokens": 600,
                        "response_format": {"type": "json_object"},
                    },
                )
                if resp.is_success:
                    ai_analysis = resp.json()["choices"][0]["message"]["content"]
        except Exception as exc:
            logger.warning("Budget AI analysis failed: %s", exc)

    # Rule-based: summarise current rules as baseline
    current_year = _tax_year_for_date(date.today())
    try:
        baseline = _load_rules(current_year)
        extracted_changes.append({
            "area": "Baseline (current rules)",
            "tax_year": current_year,
            "personal_allowance": baseline.get("income_tax", {}).get("personal_allowance"),
            "mtd_threshold": baseline.get("mtd_itsa", {}).get("threshold"),
            "class4_ni_main": baseline.get("national_insurance", {}).get("class_4", {}).get("main_rate"),
            "vat_threshold": baseline.get("vat", {}).get("registration_threshold"),
        })
    except Exception:
        pass

    _audit_log.append({
        "id": str(uuid.uuid4()),
        "event": "budget_analyzed",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "detail": f"Budget analysis: {req.budget_name}",
        "actor": "admin",
    })

    return {
        "budget_name": req.budget_name,
        "analyzed_at": datetime.now(timezone.utc).isoformat(),
        "baseline_rules": extracted_changes,
        "ai_analysis": ai_analysis,
        "note": "AI extraction requires source text or URL. Rule-based baseline always available.",
    }


# ── REG.19: Scotland rates ────────────────────────────────────────────────────

@app.get("/rules/rates/scotland")
async def get_scotland_rates(year: str = Query("2025-26")) -> Dict[str, Any]:
    """
    REG.19 — Scottish income tax rates (different bands from rUK).
    Scotland sets its own income tax rates and bands for non-savings, non-dividend income.
    """
    scotland_rates: Dict[str, Any] = {
        "2024-25": {
            "jurisdiction": "Scotland",
            "personal_allowance": 12570,
            "bands": [
                {"name": "starter",      "rate": 0.19, "from": 0,     "to": 2162},
                {"name": "basic",        "rate": 0.20, "from": 2162,  "to": 13118},
                {"name": "intermediate", "rate": 0.21, "from": 13118, "to": 31092},
                {"name": "higher",       "rate": 0.42, "from": 31092, "to": 62430},
                {"name": "advanced",     "rate": 0.45, "from": 62430, "to": 125140},
                {"name": "top",          "rate": 0.48, "from": 125140, "to": None},
            ],
            "notes": "Scottish rates for non-savings, non-dividend income. NI rates are UK-wide.",
            "source": "Scottish Budget 2024-25",
        },
        "2025-26": {
            "jurisdiction": "Scotland",
            "personal_allowance": 12570,
            "bands": [
                {"name": "starter",      "rate": 0.19, "from": 0,     "to": 2306},
                {"name": "basic",        "rate": 0.20, "from": 2306,  "to": 13991},
                {"name": "intermediate", "rate": 0.21, "from": 13991, "to": 31092},
                {"name": "higher",       "rate": 0.42, "from": 31092, "to": 62430},
                {"name": "advanced",     "rate": 0.45, "from": 62430, "to": 125140},
                {"name": "top",          "rate": 0.48, "from": 125140, "to": None},
            ],
            "notes": "Scottish rates 2025-26. Starter and basic rate bands adjusted.",
            "source": "Scottish Budget 2025-26",
        },
        "2026-27": {
            "jurisdiction": "Scotland",
            "personal_allowance": 12570,
            "bands": [
                {"name": "starter",      "rate": 0.19, "from": 0,     "to": 2400},
                {"name": "basic",        "rate": 0.20, "from": 2400,  "to": 14500},
                {"name": "intermediate", "rate": 0.21, "from": 14500, "to": 32000},
                {"name": "higher",       "rate": 0.42, "from": 32000, "to": 75000},
                {"name": "advanced",     "rate": 0.45, "from": 75000, "to": 125140},
                {"name": "top",          "rate": 0.48, "from": 125140, "to": None},
            ],
            "notes": "Scotland 2026-27 projected rates (subject to Scottish Budget confirmation).",
            "source": "Projected — confirm against Scottish Budget 2026-27",
        },
    }

    if year not in scotland_rates:
        raise HTTPException(status_code=404, detail=f"Scotland rates not available for {year!r}")

    return {"tax_year": year, "scotland_income_tax": scotland_rates[year]}


# ── GOV.UK feed: manual trigger ──────────────────────────────────────────────

@app.post("/admin/regulatory/trigger-feed-check")
async def trigger_feed_check() -> Dict[str, Any]:
    """REG.11 — Manually trigger GOV.UK HMRC feed check (also runs automatically every 24h)."""
    await _monitor_hmrc_changes()
    return {
        "triggered_at": _last_govuk_check,
        "items_found": len(_detected_changes),
        "feed_items": _detected_changes[:5],
    }


@app.get("/admin/regulatory/feed-items")
async def get_feed_items() -> Dict[str, Any]:
    """Return latest GOV.UK HMRC feed items."""
    return {
        "last_check": _last_govuk_check,
        "last_content_api_check": _last_govuk_content_check,
        "items": _detected_changes,
        "total": len(_detected_changes),
    }


@app.get("/admin/regulatory/govuk-watch")
async def get_govuk_watch_detail() -> Dict[str, Any]:
    """Last known GOV.UK Content API metadata per watched page (persisted + in-memory)."""
    disk = _read_json_file(GOVUK_WATCH_STATE_PATH, {})
    if not isinstance(disk, dict):
        disk = {}
    return {
        "last_content_api_check": _last_govuk_content_check,
        "sources_configured": len(GOVUK_WATCH_SOURCES),
        "persisted_page_count": len(disk),
        "pages": disk,
        "changelog_path": str(RULES_CHANGELOG_PATH),
    }


@app.post("/admin/regulatory/scrape-live")
async def scrape_live(req: ScrapeLiveRequest) -> Dict[str, Any]:
    """
    Fetch live GOV.UK HTML and extract monetary figures + headings for analyst review.
    Does not modify frozen JSON rules — use with Content API + manual / propose-update flow.
    """
    paths: List[str] = []
    if req.path:
        p = req.path.strip()
        if not p.startswith("/"):
            p = "/" + p
        paths.append(p)
    elif req.source_id:
        match = next((s for s in GOVUK_WATCH_SOURCES if s["id"] == req.source_id), None)
        if match is None:
            raise HTTPException(status_code=404, detail=f"Unknown source_id: {req.source_id!r}")
        paths.append(match["path"])
    else:
        paths = [s["path"] for s in GOVUK_WATCH_SOURCES]

    results: List[Dict[str, Any]] = []
    for p in paths:
        try:
            results.append(await fetch_and_extract_govuk_page(p))
        except Exception as exc:
            logger.warning("scrape-live failed for %s: %s", p, exc)
            results.append({"path": p, "error": str(exc)})

    ts = datetime.now(timezone.utc).isoformat()
    _audit_log.append({
        "id": str(uuid.uuid4()),
        "event": "govuk_html_scrape",
        "timestamp": ts,
        "detail": f"scrape-live: {len(paths)} page(s)",
        "actor": "admin",
    })
    return {"scraped_at": ts, "results": results, "count": len(results)}


@app.post("/admin/regulatory/scrape-parse")
async def scrape_parse_live(req: ScrapeParseRequest) -> Dict[str, Any]:
    """RU.5–RU.8: single HTTP fetch + structured table/heuristic parse."""
    try:
        payload = await scrape_and_parse(req.source_id, req.tax_year)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    _audit_log.append({
        "id": str(uuid.uuid4()),
        "event": "govuk_scrape_parse",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "detail": f"{req.source_id} {req.tax_year}",
        "actor": "admin",
    })
    return payload


@app.post("/admin/regulatory/parse-budget-annex")
async def parse_budget_annex(req: BudgetAnnexRequest) -> Dict[str, Any]:
    """RU.19: fetch Budget annex A HTML and extract amount hints."""
    from app.collector.budget_parser import budget_annex_path, parse_budget_annex_html

    path = budget_annex_path(req.budget_year)
    try:
        _final, html = await fetch_html(path)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"GOV.UK fetch failed: {exc}") from exc
    parsed = parse_budget_annex_html(html, f"budget_{req.budget_year}")
    _audit_log.append({
        "id": str(uuid.uuid4()),
        "event": "budget_annex_parse",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "detail": path,
        "actor": "admin",
    })
    return {"path": path, "parsed": parsed}


@app.post("/admin/regulatory/validate-ai-diff")
async def validate_ai_diff(req: ValidateAiDiffRequest) -> Dict[str, Any]:
    """RU.11: GPT checks plausibility of core JSON diff between two tax years."""
    old_r = _load_rules(req.tax_year_left)
    new_r = _load_rules(req.tax_year_right)
    result = await validate_rate_change_ai(old_r, new_r, req.source_url)
    _audit_log.append({
        "id": str(uuid.uuid4()),
        "event": "ai_validate_diff",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "detail": f"{req.tax_year_left} vs {req.tax_year_right}",
        "actor": "admin",
    })
    return result

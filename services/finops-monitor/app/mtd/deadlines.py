"""
MTD ITSA (Making Tax Digital for Income Tax Self Assessment) deadline calculator.

HMRC quarters (UK tax year starts 6 April):
  Q1: 6 Apr – 5 Jul   → submit by 5 Aug
  Q2: 6 Jul – 5 Oct   → submit by 5 Nov
  Q3: 6 Oct – 5 Jan   → submit by 5 Feb
  Q4: 6 Jan – 5 Apr   → submit by 5 May

Mandatory from April 2026:
  • Turnover > £50,000 → MTD ITSA required
  • Turnover > £30,000 → from April 2027
"""

from dataclasses import dataclass
from datetime import date


@dataclass
class MTDQuarter:
    label: str          # e.g. "Q1 2026/27"
    tax_year: str       # e.g. "2026/27"
    start: date
    end: date           # last day of the period (inclusive)
    submission_deadline: date


# ── helpers ──────────────────────────────────────────────────────────────────

def _tax_year_start(year: int) -> date:
    """6 April of *year* — beginning of UK tax year YYYY/(YY+1)."""
    return date(year, 4, 6)


def _quarters_for_tax_year(tax_year_start_year: int) -> list[MTDQuarter]:
    """Return all 4 MTD quarters for a given tax year."""
    ty_start = _tax_year_start(tax_year_start_year)
    ty_label = f"{tax_year_start_year}/{str(tax_year_start_year + 1)[-2:]}"

    # Q1: 6 Apr → 5 Jul
    q1_start = ty_start
    q1_end   = date(tax_year_start_year, 7, 5)
    q1_dead  = date(tax_year_start_year, 8, 5)

    # Q2: 6 Jul → 5 Oct
    q2_start = date(tax_year_start_year, 7, 6)
    q2_end   = date(tax_year_start_year, 10, 5)
    q2_dead  = date(tax_year_start_year, 11, 5)

    # Q3: 6 Oct → 5 Jan  (crosses year boundary)
    next_year = tax_year_start_year + 1
    q3_start = date(tax_year_start_year, 10, 6)
    q3_end   = date(next_year, 1, 5)
    q3_dead  = date(next_year, 2, 5)

    # Q4: 6 Jan → 5 Apr
    q4_start = date(next_year, 1, 6)
    q4_end   = date(next_year, 4, 5)
    q4_dead  = date(next_year, 5, 5)

    return [
        MTDQuarter(f"Q1 {ty_label}", ty_label, q1_start, q1_end, q1_dead),
        MTDQuarter(f"Q2 {ty_label}", ty_label, q2_start, q2_end, q2_dead),
        MTDQuarter(f"Q3 {ty_label}", ty_label, q3_start, q3_end, q3_dead),
        MTDQuarter(f"Q4 {ty_label}", ty_label, q4_start, q4_end, q4_dead),
    ]


# ── public API ────────────────────────────────────────────────────────────────

def get_current_quarter(reference: date | None = None) -> MTDQuarter:
    """Return the MTD quarter that contains *reference* (default: today)."""
    today = reference or date.today()

    # Check current tax year and next (in case we're near year boundary)
    for year_offset in range(-1, 3):
        candidate_year = today.year - 1 + year_offset
        for q in _quarters_for_tax_year(candidate_year):
            if q.start <= today <= q.end:
                return q

    raise ValueError(f"Could not determine quarter for date {today}")


def get_next_deadline(reference: date | None = None) -> MTDQuarter:
    """Return the next upcoming MTD quarter whose submission deadline has not passed."""
    today = reference or date.today()

    all_quarters: list[MTDQuarter] = []
    for year_offset in range(-1, 3):
        candidate_year = today.year - 1 + year_offset
        all_quarters.extend(_quarters_for_tax_year(candidate_year))

    # Sort by deadline and return the first that hasn't expired
    all_quarters.sort(key=lambda q: q.submission_deadline)
    for q in all_quarters:
        if q.submission_deadline >= today:
            return q

    raise ValueError("Could not find upcoming MTD deadline")


def days_until_deadline(reference: date | None = None) -> int:
    """Return number of days until the next submission deadline."""
    today = reference or date.today()
    q = get_next_deadline(today)
    return (q.submission_deadline - today).days


def is_mtd_required(annual_turnover: float) -> bool:
    """Check if MTD ITSA is mandatory for this turnover level (April 2026 rules)."""
    return annual_turnover >= 50_000.0


def get_warning_thresholds() -> list[int]:
    """Days-before-deadline at which we should alert the user."""
    return [30, 14, 7, 3, 1]

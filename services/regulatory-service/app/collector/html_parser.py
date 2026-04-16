"""
Parse GOV.UK HTML tables into structured rate hints (RU.5–RU.8 baseline).

GOV.UK markup changes over time; parsers are heuristic and return *hints* for
human review and AI validation — not a substitute for verifying against HMRC.
"""
from __future__ import annotations

import re
from typing import Any, Optional

from bs4 import BeautifulSoup, Tag

from .html_scraper import extract_monetary_values_from_text

_RATE_PCT = re.compile(r"(\d+(?:\.\d+)?)\s*%")
_MONEY_CELL = re.compile(r"£?\s*([\d,]+(?:\.\d{2})?)")


def find_table_by_header(soup: BeautifulSoup, header_substring: str) -> Optional[Tag]:
    needle = header_substring.lower()
    for table in soup.find_all("table"):
        texts: list[str] = []
        for th in table.find_all("th"):
            texts.append(th.get_text(" ", strip=True).lower())
        if texts and needle in " ".join(texts):
            return table
        cap = table.find("caption")
        if cap and needle in cap.get_text(" ", strip=True).lower():
            return table
    return None


def _parse_money(s: str) -> Optional[float]:
    s = s.strip().replace(",", "")
    m = _MONEY_CELL.search(s.replace("£", "£ "))
    if not m:
        return None
    try:
        return float(m.group(1).replace(",", ""))
    except ValueError:
        return None


def _table_to_matrix(table: Tag) -> list[list[str]]:
    rows: list[list[str]] = []
    for tr in table.find_all("tr"):
        cells = [c.get_text(" ", strip=True) for c in tr.find_all(["th", "td"])]
        if cells:
            rows.append(cells)
    return rows


def parse_tax_band_hints_from_paye_table(table: Tag) -> list[dict[str, Any]]:
    """Extract PAYE / income tax band rows where possible."""
    bands: list[dict[str, Any]] = []
    for row in _table_to_matrix(table)[1:]:
        if len(row) < 2:
            continue
        joined = " ".join(row).lower()
        mrate = _RATE_PCT.search(joined)
        rate = float(mrate.group(1)) / 100.0 if mrate else None
        money_vals = [_parse_money(c) for c in row if _parse_money(c) is not None]
        if rate is not None and money_vals:
            bands.append({"rate": rate, "money_cells_gbp": money_vals, "raw_row": row})
    return bands


def parse_student_loan_hints(table: Tag) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in _table_to_matrix(table)[1:]:
        if not row:
            continue
        label = row[0].lower()
        if "plan" not in label and "postgraduate" not in label and "postgrad" not in label:
            continue
        nums = [n for c in row[1:] if (n := _parse_money(c)) is not None]
        out.append({"label": row[0], "thresholds_gbp": nums, "raw": row})
    return out


def parse_employer_rates_html(html: str, tax_year: str) -> dict[str, Any]:
    soup = BeautifulSoup(html, "html.parser")
    paye_tbl = find_table_by_header(soup, "paye") or find_table_by_header(soup, "rate of tax")
    ni_tbl = find_table_by_header(soup, "class 1 national insurance")
    sl_tbl = find_table_by_header(soup, "student loan")
    text = soup.get_text(" ", strip=True)
    return {
        "tax_year": tax_year,
        "income_tax_hints": {
            "paye_table_found": paye_tbl is not None,
            "bands": parse_tax_band_hints_from_paye_table(paye_tbl) if paye_tbl else [],
        },
        "ni_class1_hints": {
            "table_found": ni_tbl is not None,
            "rows": _table_to_matrix(ni_tbl)[:25] if ni_tbl else [],
        },
        "student_loans_hints": {
            "table_found": sl_tbl is not None,
            "plans": parse_student_loan_hints(sl_tbl) if sl_tbl else [],
        },
        "amounts_gbp_sample": extract_monetary_values_from_text(text)[:80],
    }


def parse_self_employed_ni_html(html: str, tax_year: str) -> dict[str, Any]:
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(" ", strip=True)
    c2_tbl = find_table_by_header(soup, "class 2")
    c4_tbl = find_table_by_header(soup, "class 4")
    return {
        "tax_year": tax_year,
        "class_2_hints": {"table_found": c2_tbl is not None, "rows": _table_to_matrix(c2_tbl)[:20] if c2_tbl else []},
        "class_4_hints": {"table_found": c4_tbl is not None, "rows": _table_to_matrix(c4_tbl)[:20] if c4_tbl else []},
        "amounts_gbp_sample": extract_monetary_values_from_text(text)[:80],
        "rates_percent": [float(x.group(1)) / 100 for x in _RATE_PCT.finditer(text)][:12],
    }


def parse_income_tax_publication_html(html: str, tax_year: str) -> dict[str, Any]:
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(" ", strip=True)
    amounts = extract_monetary_values_from_text(text)
    return {
        "tax_year": tax_year,
        "personal_allowance_candidates": sorted({a for a in amounts if 10000 <= a <= 20000})[:5],
        "dividend_allowance_candidates": sorted({a for a in amounts if 0 <= a <= 2000})[:5],
        "amounts_gbp_sample": amounts[:100],
    }


def parse_cgt_rates_html(html: str, tax_year: str) -> dict[str, Any]:
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(" ", strip=True)
    amounts = extract_monetary_values_from_text(text)
    rates = [float(x.group(1)) / 100 for x in _RATE_PCT.finditer(text)]
    return {
        "tax_year": tax_year,
        "annual_exempt_candidates": sorted({a for a in amounts if 0 <= a <= 20000})[:5],
        "rate_fractions": rates[:8],
        "amounts_gbp_sample": amounts[:80],
    }


def parse_rates_collection_landing_html(html: str, tax_year: str) -> dict[str, Any]:
    soup = BeautifulSoup(html, "html.parser")
    links = [a.get("href", "") for a in soup.find_all("a", href=True) if "/guidance/" in a["href"] or "/government/" in a["href"]]
    return {"tax_year": tax_year, "related_links_sample": links[:40]}

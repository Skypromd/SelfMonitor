"""
Orchestrate GOV.UK HTML fetch + structured parse (RU.5–RU.8).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx
from bs4 import BeautifulSoup

from . import html_parser as hp
from .html_scraper import build_preview_from_html, extract_monetary_values_from_text
from .sources import GOVUK_WATCH_SOURCES


@dataclass(frozen=True)
class GovUkScrapeSource:
    id: str
    path: str
    parser: str


def employer_guidance_path(year_start: int) -> str:
    y1 = year_start + 1
    return f"/guidance/rates-and-thresholds-for-employers-{year_start}-to-{y1}"


GOVUK_SCRAPE_SOURCES: list[GovUkScrapeSource] = [
    GovUkScrapeSource("self_employed_ni", "/self-employed-national-insurance-rates", "se_ni"),
    GovUkScrapeSource(
        "income_tax_rates",
        "/government/publications/rates-and-allowances-income-tax/income-tax-rates-and-allowances-current-and-past",
        "income_tax_pub",
    ),
    GovUkScrapeSource("cgt_rates", "/capital-gains-tax-rates", "cgt"),
    GovUkScrapeSource(
        "rates_collection",
        "/government/collections/rates-and-allowances-hm-revenue-and-customs",
        "collection",
    ),
]


def _tax_year_start(tax_year: str) -> int:
    return int(tax_year.split("-")[0])


async def fetch_html(path: str, timeout: float = 25.0) -> tuple[str, str]:
    url = f"https://www.gov.uk{path}" if path.startswith("/") else path
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        r = await client.get(url)
        r.raise_for_status()
        return str(r.url), r.text


async def scrape_and_parse(
    source_id: str,
    tax_year: str = "2025-26",
    *,
    timeout: float = 25.0,
) -> dict[str, Any]:
    """Fetch once, then parse + build preview. employer_rates builds URL from tax_year."""
    y0 = _tax_year_start(tax_year)
    meta: dict[str, Any] = {"source_id": source_id, "tax_year": tax_year}

    if source_id == "employer_rates":
        path = employer_guidance_path(y0)
        final_url, html = await fetch_html(path, timeout=timeout)
        meta["path"] = path
        meta["parsed"] = hp.parse_employer_rates_html(html, tax_year)
        meta["raw_preview"] = build_preview_from_html(path, html, final_url)
        return meta

    match = next((s for s in GOVUK_SCRAPE_SOURCES if s.id == source_id), None)
    if match is not None:
        path = match.path
        final_url, html = await fetch_html(path, timeout=timeout)
        meta["path"] = path
        if match.parser == "se_ni":
            meta["parsed"] = hp.parse_self_employed_ni_html(html, tax_year)
        elif match.parser == "income_tax_pub":
            meta["parsed"] = hp.parse_income_tax_publication_html(html, tax_year)
        elif match.parser == "cgt":
            meta["parsed"] = hp.parse_cgt_rates_html(html, tax_year)
        elif match.parser == "collection":
            meta["parsed"] = hp.parse_rates_collection_landing_html(html, tax_year)
        else:
            meta["parsed"] = {}
        meta["raw_preview"] = build_preview_from_html(path, html, final_url)
        return meta

    watch = next((w for w in GOVUK_WATCH_SOURCES if w["id"] == source_id), None)
    if watch is None:
        raise ValueError(f"Unknown source_id: {source_id!r}")
    path = watch["path"]
    final_url, html = await fetch_html(path, timeout=timeout)
    meta["path"] = path
    text = BeautifulSoup(html, "html.parser").get_text(" ", strip=True)
    meta["parsed"] = {
        "tax_year": tax_year,
        "note": "generic_watch_source",
        "amounts_gbp_sample": extract_monetary_values_from_text(text)[:80],
    }
    meta["raw_preview"] = build_preview_from_html(path, html, final_url)
    return meta

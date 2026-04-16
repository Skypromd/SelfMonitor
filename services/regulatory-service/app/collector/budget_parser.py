"""Heuristic parse for Budget OOTLAR annex HTML (RU.19 baseline)."""
from __future__ import annotations

from typing import Any

from bs4 import BeautifulSoup

from .html_scraper import extract_monetary_values_from_text


def budget_annex_path(budget_year: int) -> str:
    return (
        f"/government/publications/budget-{budget_year}-overview-of-tax-legislation-and-rates-ootlar/"
        "annex-a-rates-and-allowances"
    )


def parse_budget_annex_html(html: str, budget_label: str = "budget_annex") -> dict[str, Any]:
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(" ", strip=True)
    return {
        "source": budget_label,
        "headings": [h.get_text(strip=True)[:200] for h in soup.find_all(["h1", "h2", "h3"])][:30],
        "amounts_gbp_sample": extract_monetary_values_from_text(text)[:150],
        "note": "Structured table mapping requires manual confirmation after each Budget HTML change.",
    }

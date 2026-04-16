from __future__ import annotations

from typing import Any, TypedDict


class GovUkWatchSource(TypedDict):
    id: str
    path: str
    label: str


GOVUK_WATCH_SOURCES: list[GovUkWatchSource] = [
    {
        "id": "employer_rates_2526",
        "path": "/guidance/rates-and-thresholds-for-employers-2025-to-2026",
        "label": "Employer PAYE / NI / student loan thresholds 2025–26",
    },
    {
        "id": "employer_rates_2425",
        "path": "/guidance/rates-and-thresholds-for-employers-2024-to-2025",
        "label": "Employer PAYE / NI / student loan thresholds 2024–25",
    },
    {
        "id": "self_employed_ni",
        "path": "/self-employed-national-insurance-rates",
        "label": "Self-employed Class 2 and Class 4 NI",
    },
    {
        "id": "income_tax_rates_publication",
        "path": "/government/publications/rates-and-allowances-income-tax/income-tax-rates-and-allowances-current-and-past",
        "label": "Income tax rates and allowances (publication hub)",
    },
    {
        "id": "rates_collections",
        "path": "/government/collections/rates-and-allowances-hm-revenue-and-customs",
        "label": "HMRC rates and allowances collection",
    },
    {
        "id": "cgt_rates",
        "path": "/capital-gains-tax-rates",
        "label": "Capital gains tax rates overview",
    },
]

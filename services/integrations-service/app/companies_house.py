"""
Companies House API integration — company registration and lookup.
API docs: https://developer.company-information.service.gov.uk/
Free API key: https://developer.company-information.service.gov.uk/manage-applications
"""
import os
from typing import Optional

import httpx
from pydantic import BaseModel

COMPANIES_HOUSE_API_KEY = os.getenv("COMPANIES_HOUSE_API_KEY", "")
COMPANIES_HOUSE_BASE_URL = "https://api.company-information.service.gov.uk"


class CompanySearchResult(BaseModel):
    company_number: str
    company_name: str
    company_status: str
    company_type: str
    date_of_creation: Optional[str] = None
    registered_office_address: Optional[dict] = None


class CompanyProfile(BaseModel):
    company_number: str
    company_name: str
    company_status: str
    type: str
    date_of_creation: Optional[str] = None
    sic_codes: list[str] = []
    registered_office_address: Optional[dict] = None
    accounts: Optional[dict] = None
    confirmation_statement: Optional[dict] = None


async def search_companies(query: str, items_per_page: int = 10) -> list[CompanySearchResult]:
    """Search Companies House for companies by name or number"""
    if not COMPANIES_HOUSE_API_KEY:
        return [CompanySearchResult(
            company_number="DEMO-12345678",
            company_name=f"{query} Ltd (demo mode — set COMPANIES_HOUSE_API_KEY)",
            company_status="active",
            company_type="ltd",
        )]

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{COMPANIES_HOUSE_BASE_URL}/search/companies",
            params={"q": query, "items_per_page": items_per_page},
            auth=(COMPANIES_HOUSE_API_KEY, ""),
            timeout=10.0,
        )
        response.raise_for_status()
        data = response.json()

    results = []
    for item in data.get("items", []):
        results.append(CompanySearchResult(
            company_number=item.get("company_number", ""),
            company_name=item.get("title", ""),
            company_status=item.get("company_status", ""),
            company_type=item.get("company_type", ""),
            date_of_creation=item.get("date_of_creation"),
            registered_office_address=item.get("registered_office_address"),
        ))
    return results


async def get_company_profile(company_number: str) -> Optional[CompanyProfile]:
    """Get detailed company profile from Companies House"""
    if not COMPANIES_HOUSE_API_KEY:
        return CompanyProfile(
            company_number=company_number,
            company_name=f"Demo Company {company_number}",
            company_status="active",
            type="ltd",
            sic_codes=["62020"],
        )

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{COMPANIES_HOUSE_BASE_URL}/company/{company_number}",
            auth=(COMPANIES_HOUSE_API_KEY, ""),
            timeout=10.0,
        )
        if response.status_code == 404:
            return None
        response.raise_for_status()
        data = response.json()

    return CompanyProfile(
        company_number=data.get("company_number", ""),
        company_name=data.get("company_name", ""),
        company_status=data.get("company_status", ""),
        type=data.get("type", ""),
        date_of_creation=data.get("date_of_creation"),
        sic_codes=data.get("sic_codes", []),
        registered_office_address=data.get("registered_office_address"),
        accounts=data.get("accounts"),
        confirmation_statement=data.get("confirmation_statement"),
    )

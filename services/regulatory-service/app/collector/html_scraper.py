from __future__ import annotations

import re
from typing import Any

import httpx
from bs4 import BeautifulSoup

_GBP_PATTERN = re.compile(r"£\s*([\d,]+(?:\.\d{2})?)")


def extract_monetary_values_from_text(text: str) -> list[float]:
    out: list[float] = []
    for m in _GBP_PATTERN.finditer(text):
        try:
            out.append(float(m.group(1).replace(",", "")))
        except ValueError:
            continue
    return out


def build_preview_from_html(path: str, html: str, final_url: str | None = None) -> dict[str, Any]:
    soup = BeautifulSoup(html, "html.parser")
    title: str | None = None
    og = soup.find("meta", property="og:title")
    if og and og.get("content"):
        title = og["content"].strip()
    if not title:
        t_el = soup.find("title")
        if t_el:
            title = t_el.get_text(strip=True)
    text = soup.get_text(" ", strip=True)
    amounts = extract_monetary_values_from_text(text)
    headings: list[str] = []
    for tag in soup.find_all(["h1", "h2", "h3"]):
        h = tag.get_text(strip=True)
        if h:
            headings.append(h[:240])
        if len(headings) >= 45:
            break
    return {
        "path": path,
        "url": final_url or "",
        "title": title,
        "headings": headings,
        "amounts_gbp_sample": amounts[:120],
        "amounts_parsed_total": len(amounts),
        "amounts_distinct_count": len(set(amounts)),
    }


async def fetch_and_extract_govuk_page(path: str, timeout: float = 25.0) -> dict[str, Any]:
    url = f"https://www.gov.uk{path}" if path.startswith("/") else path
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        final_url = str(resp.url)
        html = resp.text
    return build_preview_from_html(path, html, final_url)

"""GOV.UK regulatory content collection (metadata + future HTML parsers)."""

from .govuk_content_api import GovUkPageMeta, check_govuk_sources_for_updates
from .govuk_scraper import GOVUK_SCRAPE_SOURCES, employer_guidance_path, fetch_html, scrape_and_parse
from .html_scraper import build_preview_from_html, fetch_and_extract_govuk_page
from .sources import GOVUK_WATCH_SOURCES

__all__ = [
    "GOVUK_WATCH_SOURCES",
    "GOVUK_SCRAPE_SOURCES",
    "GovUkPageMeta",
    "build_preview_from_html",
    "check_govuk_sources_for_updates",
    "employer_guidance_path",
    "fetch_and_extract_govuk_page",
    "fetch_html",
    "scrape_and_parse",
]

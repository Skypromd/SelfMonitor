import os
import sys
import json

from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.main import CATALOG_ROOT, app

client = TestClient(app)


def test_list_supported_locales_contains_required_languages():
    response = client.get("/translations/locales")
    assert response.status_code == 200
    payload = response.json()
    codes = {item["code"] for item in payload}
    assert {"ru-RU", "uk-UA", "en-GB", "pl-PL", "ro-MD", "tr-TR", "hu-HU"}.issubset(codes)


def test_fallback_locale_returns_base_english_content():
    response = client.get("/translations/ru-RU/all")
    assert response.status_code == 200
    payload = response.json()
    assert payload["common"]["submit"] == "Submit"
    assert payload["nav"]["documents"] == "Documents"


def test_translated_locale_keeps_native_overrides():
    response = client.get("/translations/de-DE/all")
    assert response.status_code == 200
    payload = response.json()
    assert payload["common"]["submit"] == "Einreichen"
    assert payload["nav"]["documents"] == "Dokumente"


def test_unknown_locale_returns_not_found():
    response = client.get("/translations/es-ES/all")
    assert response.status_code == 404


def test_translation_health_reports_fallback_metrics():
    response = client.get("/translations/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["default_locale"] == "en-GB"
    assert payload["reference_total_keys"] > 0
    assert payload["summary"]["total_locales"] >= 7
    locale_rows = {item["code"]: item for item in payload["locales"]}
    assert "ru-RU" in locale_rows
    assert locale_rows["ru-RU"]["fallback_keys"] > 0
    assert locale_rows["ru-RU"]["estimated_fallback_hit_rate_percent"] > 0
    assert "en-GB" in locale_rows
    assert locale_rows["en-GB"]["fallback_keys"] == 0
    assert locale_rows["en-GB"]["estimated_fallback_hit_rate_percent"] == 0.0


def test_translation_health_includes_missing_key_samples():
    response = client.get("/translations/health")
    assert response.status_code == 200
    payload = response.json()
    locale_rows = {item["code"]: item for item in payload["locales"]}
    ru_row = locale_rows["ru-RU"]
    assert ru_row["missing_key_count"] >= len(ru_row["missing_key_samples"])
    assert all("." in key_name for key_name in ru_row["missing_key_samples"])


def test_external_catalog_files_are_present_and_used():
    locales_file = CATALOG_ROOT / "locales.json"
    de_catalog_file = CATALOG_ROOT / "translations" / "de-DE.json"
    assert locales_file.exists()
    assert de_catalog_file.exists()

    de_catalog = json.loads(de_catalog_file.read_text(encoding="utf-8"))
    response = client.get("/translations/de-DE/all")
    assert response.status_code == 200
    payload = response.json()
    assert payload["common"]["submit"] == de_catalog["common"]["submit"]


def test_locale_format_standards_for_supported_locale():
    response = client.get("/translations/en-GB/format-standards")
    assert response.status_code == 200
    payload = response.json()
    assert payload["locale"] == "en-GB"
    assert payload["default_currency"] == "GBP"
    assert payload["time_zone"] == "Europe/London"


def test_locale_format_standards_unknown_locale_returns_not_found():
    response = client.get("/translations/es-ES/format-standards")
    assert response.status_code == 404

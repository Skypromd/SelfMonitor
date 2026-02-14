import os
import sys

from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.main import app

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

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


# --- Health endpoint ---

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


# --- Get translations by component ---

def test_get_translations_valid_locale_and_component():
    response = client.get("/translations/en-GB/login")
    assert response.status_code == 200
    data = response.json()
    assert "title" in data
    assert data["title"] == "FinTech App"


def test_get_translations_common_component():
    response = client.get("/translations/en-GB/common")
    assert response.status_code == 200
    data = response.json()
    assert data["submit"] == "Submit"
    assert data["cancel"] == "Cancel"


def test_get_translations_german_locale():
    response = client.get("/translations/de-DE/login")
    assert response.status_code == 200
    data = response.json()
    assert data["login_button"] == "Anmelden"


def test_get_translations_german_common():
    response = client.get("/translations/de-DE/common")
    assert response.status_code == 200
    data = response.json()
    assert data["submit"] == "Einreichen"
    assert data["cancel"] == "Abbrechen"


def test_get_translations_unknown_locale():
    response = client.get("/translations/ja-JP/login")
    assert response.status_code == 404


def test_get_translations_unknown_component():
    response = client.get("/translations/en-GB/nonexistent")
    assert response.status_code == 404


def test_get_translations_both_unknown():
    response = client.get("/translations/xx-XX/zzz")
    assert response.status_code == 404


# --- Verify specific component data ---

def test_nav_translations_contain_expected_keys():
    response = client.get("/translations/en-GB/nav")
    assert response.status_code == 200
    data = response.json()
    for key in ["dashboard", "activity", "transactions", "documents", "reports", "marketplace", "profile"]:
        assert key in data, f"Missing nav key: {key}"


def test_dashboard_translations():
    response = client.get("/translations/en-GB/dashboard")
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Main Dashboard"


def test_documents_translations():
    response = client.get("/translations/en-GB/documents")
    assert response.status_code == 200
    data = response.json()
    assert "upload_title" in data
    assert "search_title" in data


def test_reports_translations():
    response = client.get("/translations/en-GB/reports")
    assert response.status_code == 200
    data = response.json()
    assert "mortgage_title" in data
    assert "generate_button" in data


# --- Ukrainian locale (uk-UA) ---

def test_get_translations_ukrainian_login():
    response = client.get("/translations/uk-UA/login")
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "FinTech App"
    assert data["login_button"] == "Увійти"
    assert data["register_button"] == "Реєстрація"


def test_get_translations_ukrainian_common():
    response = client.get("/translations/uk-UA/common")
    assert response.status_code == 200
    data = response.json()
    assert data["submit"] == "Надіслати"
    assert data["cancel"] == "Скасувати"
    assert data["save"] == "Зберегти"


def test_get_translations_ukrainian_nav():
    response = client.get("/translations/uk-UA/nav")
    assert response.status_code == 200
    data = response.json()
    assert data["dashboard"] == "Головна"
    assert data["documents"] == "Документи"
    assert data["reports"] == "Звіти"


def test_get_translations_ukrainian_documents():
    response = client.get("/translations/uk-UA/documents")
    assert response.status_code == 200
    data = response.json()
    assert data["upload_button"] == "Завантажити"
    assert data["search_button"] == "Шукати"
    assert data["all_documents_title"] == "Усі документи"


# --- 404 detail message ---

def test_404_detail_message_includes_locale_and_component():
    response = client.get("/translations/ja-JP/login")
    assert response.status_code == 404
    detail = response.json()["detail"]
    assert "ja-JP" in detail
    assert "login" in detail

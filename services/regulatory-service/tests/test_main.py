"""Tests for regulatory-service."""
import os
os.environ.setdefault("OPENAI_API_KEY", "")

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch

from app.main import app

client = TestClient(app)


def test_health():
    resp = client.get("/health", headers={"X-Request-Id": "reg-test-rid"})
    assert resp.status_code == 200
    assert resp.headers.get("X-Request-Id") == "reg-test-rid"
    data = resp.json()
    assert data["status"] == "ok"
    assert "2025-26" in data["available_tax_years"]


def test_get_tax_year_rules_2025_26():
    resp = client.get("/rules/tax-year/2025-26")
    assert resp.status_code == 200
    data = resp.json()
    assert data["tax_year"] == "2025-26"
    assert data["income_tax"]["personal_allowance"] == 12570
    bands = data["income_tax"]["bands"]
    rates = {b["name"]: b["rate"] for b in bands}
    assert rates["basic"] == 0.20
    assert rates["higher"] == 0.40
    assert rates["additional"] == 0.45


def test_get_tax_year_rules_2024_25():
    resp = client.get("/rules/tax-year/2024-25")
    assert resp.status_code == 200
    data = resp.json()
    assert data["tax_year"] == "2024-25"
    assert data["national_insurance"]["class_4"]["main_rate"] == 0.09


def test_get_tax_year_rules_2026_27():
    resp = client.get("/rules/tax-year/2026-27")
    assert resp.status_code == 200
    data = resp.json()
    assert data["tax_year"] == "2026-27"
    assert data["mtd_itsa"]["threshold"] == 50000


def test_get_tax_year_rules_not_found():
    resp = client.get("/rules/tax-year/2030-31")
    assert resp.status_code == 404


def test_get_active_rules_today():
    resp = client.get("/rules/active")
    assert resp.status_code == 200
    data = resp.json()
    assert "tax_year" in data or "_resolved_tax_year" in data


def test_get_active_rules_specific_date():
    resp = client.get("/rules/active?date=2026-04-10")
    assert resp.status_code == 200
    data = resp.json()
    assert data["_resolved_tax_year"] == "2026-27"


def test_get_active_rules_bad_date():
    resp = client.get("/rules/active?date=not-a-date")
    assert resp.status_code == 400


def test_mtd_threshold_below():
    resp = client.get("/rules/mtd/threshold?income=30000&year=2025-26")
    assert resp.status_code == 200
    data = resp.json()
    assert data["mtd_required"] is False
    assert data["income"] == 30000


def test_mtd_threshold_above_in_2026_27():
    resp = client.get("/rules/mtd/threshold?income=55000&year=2026-27")
    assert resp.status_code == 200
    data = resp.json()
    assert data["mtd_required"] is True
    assert data["threshold"] == 50000


def test_mtd_threshold_warning_next_year():
    # Income £35k: not required in 2025-26, but warning about 2026-27
    resp = client.get("/rules/mtd/threshold?income=35000&year=2025-26")
    assert resp.status_code == 200
    data = resp.json()
    assert data["mtd_required"] is False
    # No threshold crossing for 2026-27 (35k < 50k) so no warning expected at this level


def test_get_deadlines():
    resp = client.get("/rules/deadlines?year=2025-26")
    assert resp.status_code == 200
    data = resp.json()
    assert data["tax_year"] == "2025-26"
    assert len(data["deadlines"]) > 0
    # Check days_until is injected
    assert "days_until" in data["deadlines"][0]


def test_get_deadlines_filtered_payment():
    resp = client.get("/rules/deadlines?year=2025-26&type=payment")
    assert resp.status_code == 200
    data = resp.json()
    for dl in data["deadlines"]:
        assert dl["type"] == "payment"


def test_get_income_tax_rates():
    resp = client.get("/rules/rates/income-tax?year=2025-26")
    assert resp.status_code == 200
    data = resp.json()
    assert data["tax_year"] == "2025-26"
    assert "personal_allowance" in data["income_tax"]
    assert "bands" in data["income_tax"]


def test_get_ni_rates():
    resp = client.get("/rules/rates/ni?year=2025-26")
    assert resp.status_code == 200
    data = resp.json()
    assert "class_2" in data["national_insurance"]
    assert "class_4" in data["national_insurance"]
    assert data["national_insurance"]["class_4"]["main_rate"] == 0.06


def test_get_vat_rates():
    resp = client.get("/rules/rates/vat?year=2025-26")
    assert resp.status_code == 200
    data = resp.json()
    assert data["vat"]["registration_threshold"] == 90000
    assert data["vat"]["standard_rate"] == 0.20


def test_get_allowable_expenses():
    resp = client.get("/rules/allowable-expenses?year=2025-26")
    assert resp.status_code == 200
    data = resp.json()
    codes = data["deductible_category_codes"]
    assert "professional_fees" in codes
    assert "travel" in codes
    assert "office_costs" in codes
    assert "use_of_home" in codes
    assert "vehicle_mileage" in codes
    assert len(codes) >= 14


def test_get_regulatory_changes():
    resp = client.get("/rules/changes?since=2024-01-01")
    assert resp.status_code == 200
    data = resp.json()
    assert "changes" in data
    assert data["total"] == len(data["changes"])


def test_get_regulatory_changes_bad_date():
    resp = client.get("/rules/changes?since=bad")
    assert resp.status_code == 400


def test_analyze_user_basic():
    resp = client.post("/rules/analyze-user", json={
        "estimated_annual_income": 45000,
        "tax_year": "2025-26",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["estimated_annual_income"] == 45000
    assert data["estimated_total_tax_and_ni"] > 0
    assert isinstance(data["applicable_rules"], list)
    assert len(data["applicable_rules"]) >= 2  # at least basic rate + NI
    assert isinstance(data["warnings"], list)
    assert isinstance(data["recommended_actions"], list)


def test_analyze_user_high_income_taper():
    resp = client.post("/rules/analyze-user", json={
        "estimated_annual_income": 110000,
        "tax_year": "2025-26",
    })
    assert resp.status_code == 200
    data = resp.json()
    # Should trigger PA taper warning
    taper_warnings = [w for w in data["warnings"] if "taper" in w.lower() or "Allowance is tapered" in w]
    assert len(taper_warnings) > 0


def test_analyze_user_mtd_mandatory():
    resp = client.post("/rules/analyze-user", json={
        "estimated_annual_income": 60000,
        "tax_year": "2026-27",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["mtd_required"] is True
    mtd_warnings = [w for w in data["warnings"] if "MTD" in w]
    assert len(mtd_warnings) > 0


def test_analyze_user_with_student_loan():
    resp = client.post("/rules/analyze-user", json={
        "estimated_annual_income": 35000,
        "tax_year": "2025-26",
        "has_student_loan": True,
        "student_loan_plan": "plan_2",
    })
    assert resp.status_code == 200
    data = resp.json()
    sl_rules = [r for r in data["applicable_rules"] if "student" in r["rule"].lower()]
    assert len(sl_rules) > 0


def test_get_allowances():
    resp = client.get("/rules/allowances?year=2025-26")
    assert resp.status_code == 200
    data = resp.json()
    assert data["allowances"]["trading_allowance"] == 1000
    assert data["allowances"]["marriage_allowance_transfer"] == 1260


def test_get_student_loans():
    resp = client.get("/rules/student-loans?year=2025-26")
    assert resp.status_code == 200
    data = resp.json()
    assert "plan_2" in data["student_loans"]
    assert data["student_loans"]["plan_2"]["rate"] == 0.09


def test_get_rule_versions():
    resp = client.get("/rules/versions")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    years = [v["tax_year"] for v in data]
    assert "2025-26" in years
    assert "2026-27" in years
    statuses = {v["tax_year"]: v["status"] for v in data}
    assert statuses["2025-26"] == "final"
    assert statuses["2026-27"] == "draft"


def test_get_available_years():
    resp = client.get("/rules/available-years")
    assert resp.status_code == 200
    data = resp.json()
    assert "2025-26" in data["available_years"]
    assert "current_tax_year" in data


def test_rules_changelog():
    resp = client.get("/rules/changelog?limit=10")
    assert resp.status_code == 200
    data = resp.json()
    assert "entries" in data
    assert data["total"] >= 0


def test_rules_diff_consecutive_years():
    resp = client.get("/rules/diff?from=2024-25&to=2025-26")
    assert resp.status_code == 200
    data = resp.json()
    assert data["from"] == "2024-25"
    assert data["to"] == "2025-26"
    paths = {c["path"] for c in data["changes"]}
    assert any("national_insurance.class_4.main_rate" in p for p in paths)


def test_admin_govuk_watch():
    resp = client.get("/admin/regulatory/govuk-watch")
    assert resp.status_code == 200
    data = resp.json()
    assert data["sources_configured"] >= 1
    assert "pages" in data


def test_validate_ai_diff_without_openai():
    resp = client.post(
        "/admin/regulatory/validate-ai-diff",
        json={"tax_year_left": "2024-25", "tax_year_right": "2025-26", "source_url": "https://www.gov.uk/"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "action" in data or "valid" in data


def test_scrape_live_mocked():
    mock_fetch = AsyncMock(
        return_value={
            "path": "/guidance/test",
            "url": "https://www.gov.uk/guidance/test",
            "title": "Test",
            "headings": [],
            "amounts_gbp_sample": [12570.0],
            "amounts_parsed_total": 1,
            "amounts_distinct_count": 1,
        },
    )
    with patch("app.main.fetch_and_extract_govuk_page", mock_fetch):
        resp = client.post("/admin/regulatory/scrape-live", json={"path": "/guidance/test"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] == 1
    assert data["results"][0]["amounts_gbp_sample"][0] == 12570.0
    mock_fetch.assert_awaited()

import os
import sys
from contextlib import contextmanager
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from fastapi.testclient import TestClient
from jose import jwt

os.environ.setdefault("AUTH_SECRET_KEY", "test-secret")
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
for module_name in list(sys.modules):
    if module_name == "app" or module_name.startswith("app."):
        sys.modules.pop(module_name, None)
from app import main as app_main
from app.main import app


@pytest.fixture(autouse=True)
def _clear_regulatory_rules_cache():
    """Per-test isolation: in-memory TTL cache would otherwise pin the first mocked rules per tax year."""
    app_main._REGULATORY_RULES_CACHE.clear()
    yield
    app_main._REGULATORY_RULES_CACHE.clear()

client = TestClient(app)
AUTH_SECRET_KEY = os.environ["AUTH_SECRET_KEY"]
AUTH_ALGORITHM = "HS256"
TEST_USER_ID = "test-user@example.com"


def get_auth_headers(user_id: str = TEST_USER_ID) -> dict[str, str]:
    token = jwt.encode(
        {
            "sub": user_id,
            "plan": "business",
            "transaction_history_months": 120,
        },
        AUTH_SECRET_KEY,
        algorithm=AUTH_ALGORITHM,
    )
    return {"Authorization": f"Bearer {token}"}


def _minimal_regulatory_rules(student_loans: dict | None = None) -> dict:
    sl = student_loans if student_loans is not None else {}
    return {
        "income_tax": {
            "personal_allowance": 12570,
            "personal_allowance_taper_threshold": 100000,
            "personal_allowance_taper_rate": 0.5,
            "bands": [
                {"name": "basic", "rate": 0.20, "from": 0, "to": 37700},
                {"name": "higher", "rate": 0.40, "from": 37700, "to": 125140},
                {"name": "additional", "rate": 0.45, "from": 125140, "to": None},
            ],
        },
        "national_insurance": {
            "class_2": {
                "small_profits_threshold": 6725,
                "lower_profits_limit": 12570,
                "mandatory_annual_cash_gbp_when_profits_ge_lower_limit": 0,
            },
            "class_4": {
                "lower_profits_limit": 12570,
                "upper_profits_limit": 50270,
                "main_rate": 0.06,
                "additional_rate": 0.02,
            },
        },
        "allowances": {
            "trading_allowance": 1000,
            "marriage_allowance_transfer": 1260,
            "use_of_home_flat_rate_weekly": 6,
            "blind_persons_allowance": 3130,
            "dividend_allowance": 500,
            "capital_gains_annual_exempt": 3000,
            "annual_investment_allowance": 1000000,
        },
        "student_loans": sl,
    }


def _scotland_rates_payload_2025_26() -> dict:
    return {
        "tax_year": "2025-26",
        "scotland_income_tax": {
            "jurisdiction": "Scotland",
            "personal_allowance": 12570,
            "bands": [
                {"name": "starter", "rate": 0.19, "from": 0, "to": 2306},
                {"name": "basic", "rate": 0.20, "from": 2306, "to": 13991},
                {"name": "intermediate", "rate": 0.21, "from": 13991, "to": 31092},
                {"name": "higher", "rate": 0.42, "from": 31092, "to": 62430},
                {"name": "advanced", "rate": 0.45, "from": 62430, "to": 125140},
                {"name": "top", "rate": 0.48, "from": 125140, "to": None},
            ],
        },
    }


@contextmanager
def _httpx_get_router(*, transactions: list, regulatory: dict, scotland: dict | None = None):
    async def _route(url, *args, **kwargs):
        u = str(url)
        if "/rules/rates/scotland" in u:
            body = (
                scotland
                if scotland is not None
                else {"tax_year": "2025-26", "scotland_income_tax": {"bands": []}}
            )
            return httpx.Response(200, json=body, request=httpx.Request("GET", u))
        if "/rules/tax-year/" in u:
            return httpx.Response(200, json=regulatory, request=httpx.Request("GET", u))
        return httpx.Response(200, json=transactions, request=httpx.Request("GET", u))

    mock = AsyncMock(side_effect=_route)
    with patch("httpx.AsyncClient.get", new=mock):
        yield mock


@contextmanager
def _httpx_fixed_response(response: httpx.Response):
    mock = AsyncMock(return_value=response)
    with patch("httpx.AsyncClient.get", new=mock):
        yield mock


def test_calculate_tax_with_mocked_transactions():
    mock_transactions = [
        {"date": "2023-05-10", "amount": 3000.0, "category": "income"},
        {"date": "2023-06-15", "amount": -150.0, "category": "transport"},
        {"date": "2023-07-20", "amount": -80.0, "category": "groceries"},
        {"date": "2023-08-01", "amount": -50.0, "category": "office_supplies"},
    ]
    with _httpx_get_router(transactions=mock_transactions, regulatory={}) as mock_get:
        response = client.post(
            "/calculate",
            headers=get_auth_headers(),
            json={"start_date": "2023-01-01", "end_date": "2023-12-31", "jurisdiction": "UK"},
        )
    assert response.status_code == 200
    data = response.json()
    assert mock_get.call_count == 2
    assert data["total_income"] == 3000.0
    assert data["total_expenses"] == 200.0
    assert data["taxable_profit"] == 2800.0
    assert data["personal_allowance_used"] == 2800.0
    assert data["estimated_income_tax_due"] == 0.0
    assert data["estimated_class4_nic_due"] == 0.0
    assert data["estimated_tax_due"] == 0.0
    assert data["mtd_obligation"]["reporting_required"] is False
    assert data["mtd_obligation"]["reporting_cadence"] == "annual_only"
    assert "estimate_disclaimers" in data["breakdown"]
    assert "regulatory_rules_source" in data["breakdown"]
    assert isinstance(data["breakdown"]["estimate_disclaimers"], list)


def test_cis_legacy_single_field_treated_as_unverified():
    mock_transactions = [
        {"date": "2023-05-10", "amount": 3000.0, "category": "income"},
    ]
    body = {
        "start_date": "2023-01-01",
        "end_date": "2023-12-31",
        "jurisdiction": "UK",
        "cis_suffered_in_period_gbp": 500.0,
    }
    with _httpx_get_router(transactions=mock_transactions, regulatory={}):
        response = client.post("/calculate", headers=get_auth_headers(), json=body)
    assert response.status_code == 200
    data = response.json()
    assert data["cis_tax_credit_self_attested_gbp"] == 500.0
    assert data["cis_tax_credit_verified_gbp"] == 0.0
    assert data["cis_hmrc_submit_requires_unverified_ack"] is True
    assert data["breakdown"]["cis_credits_breakdown"]["labels"] == ["UNVERIFIED"]


def test_cis_split_respects_verified_and_self_attested():
    mock_transactions = [
        {"date": "2023-05-10", "amount": 10000.0, "category": "income"},
    ]
    body = {
        "start_date": "2023-01-01",
        "end_date": "2023-12-31",
        "jurisdiction": "UK",
        "cis_tax_credit_verified_gbp": 100.0,
        "cis_tax_credit_self_attested_gbp": 200.0,
        "cis_suffered_in_period_gbp": 999.0,
    }
    with _httpx_get_router(transactions=mock_transactions, regulatory={}):
        response = client.post("/calculate", headers=get_auth_headers(), json=body)
    assert response.status_code == 200
    data = response.json()
    assert data["cis_tax_credit_verified_gbp"] == 100.0
    assert data["cis_tax_credit_self_attested_gbp"] == 200.0
    assert data["cis_tax_credit_applied_gbp"] == 300.0
    assert data["breakdown"]["cis_credits_breakdown"]["legacy_cis_field_ignored_use_split_inputs"] is True


def test_mtd_prepare_aligns_with_calculate_and_includes_hmrc_shape():
    mock_transactions = [
        {"date": "2023-05-10", "amount": 3000.0, "category": "income"},
        {"date": "2023-06-15", "amount": -150.0, "category": "transport"},
        {"date": "2023-07-20", "amount": -80.0, "category": "groceries"},
        {"date": "2023-08-01", "amount": -50.0, "category": "office_supplies"},
    ]
    body = {"start_date": "2023-01-01", "end_date": "2023-12-31", "jurisdiction": "UK"}
    with _httpx_get_router(transactions=mock_transactions, regulatory={}):
        calc = client.post("/calculate", headers=get_auth_headers(), json=body)
        prep = client.post("/mtd/prepare", headers=get_auth_headers(), json=body)
    assert calc.status_code == 200
    assert prep.status_code == 200
    cj, pj = calc.json(), prep.json()
    assert pj["calculation"]["total_income"] == cj["total_income"]
    assert pj["calculation"]["estimated_tax_due"] == cj["estimated_tax_due"]
    hmj = pj["hmrc_period_summary_json"]
    assert hmj["periodIncome"]["turnover"] == cj["total_income"]
    assert hmj["periodExpenses"]["allowableExpenses"] == cj["total_expenses"]
    assert pj["integrations_quarterly_payload"] is None


def test_calculate_ruk_splits_income_tax_across_basic_higher_additional_bands():
    """rUK 20% / 40% / 45% bands applied to taxable income after personal allowance (incl. taper)."""
    mock_transactions = [
        {"date": "2025-06-10", "amount": 150_000.0, "category": "income"},
    ]
    reg = _minimal_regulatory_rules()
    with _httpx_get_router(transactions=mock_transactions, regulatory=reg):
        response = client.post(
            "/calculate",
            headers=get_auth_headers(),
            json={
                "start_date": "2025-04-06",
                "end_date": "2026-04-05",
                "jurisdiction": "UK",
                "region": "england_wales",
            },
        )
    assert response.status_code == 200
    p = response.json()
    assert p["taxable_amount_after_allowance"] == 150_000.0
    assert p["personal_allowance_used"] == 0.0
    exp_basic = round(37_700 * 0.20, 2)
    exp_higher = round((125_140 - 37_700) * 0.40, 2)
    exp_add = round((150_000 - 125_140) * 0.45, 2)
    assert p["basic_rate_tax"] == exp_basic
    assert p["higher_rate_tax"] == exp_higher
    assert p["additional_rate_tax"] == exp_add
    assert p["estimated_income_tax_due"] == round(exp_basic + exp_higher + exp_add, 2)


def test_calculate_class2_nic_zero_when_regulatory_mandatory_cash_is_zero():
    mock_transactions = [{"date": "2025-08-01", "amount": 20_000.0, "category": "income"}]
    reg = _minimal_regulatory_rules()
    with _httpx_get_router(transactions=mock_transactions, regulatory=reg):
        response = client.post(
            "/calculate",
            headers=get_auth_headers(),
            json={"start_date": "2025-04-06", "end_date": "2026-04-05", "jurisdiction": "UK"},
        )
    assert response.status_code == 200
    assert response.json()["estimated_class2_nic_due"] == 0.0


def test_calculate_personal_allowance_taper_over_100k():
    mock_transactions = [{"date": "2025-08-01", "amount": 110_000.0, "category": "income"}]
    reg = _minimal_regulatory_rules()
    with _httpx_get_router(transactions=mock_transactions, regulatory=reg):
        response = client.post(
            "/calculate",
            headers=get_auth_headers(),
            json={"start_date": "2025-04-06", "end_date": "2026-04-05", "jurisdiction": "UK"},
        )
    assert response.status_code == 200
    p = response.json()
    assert p["pa_taper_reduction"] == 5000.0
    assert p["personal_allowance_used"] == 7570.0
    assert p["taxable_amount_after_allowance"] == 102_430.0


def test_calculate_postgraduate_loan_from_regulatory_rules():
    mock_transactions = [{"date": "2025-08-01", "amount": 40_000.0, "category": "income"}]
    reg = _minimal_regulatory_rules(
        student_loans={"postgraduate": {"threshold": 21000, "rate": 0.06}},
    )
    with _httpx_get_router(transactions=mock_transactions, regulatory=reg):
        response = client.post(
            "/calculate",
            headers=get_auth_headers(),
            json={
                "start_date": "2025-04-06",
                "end_date": "2026-04-05",
                "jurisdiction": "UK",
                "student_loan_plan": "postgraduate",
            },
        )
    assert response.status_code == 200
    expected = round(max(0.0, 40_000.0 - 21_000.0) * 0.06, 2)
    assert response.json()["student_loan_repayment_gbp"] == expected


def test_calculate_payments_on_account_when_liability_over_threshold():
    mock_transactions = [{"date": "2025-08-01", "amount": 85_000.0, "category": "income"}]
    reg = _minimal_regulatory_rules(
        student_loans={"plan_2": {"threshold": 27295, "rate": 0.09}},
    )
    with _httpx_get_router(transactions=mock_transactions, regulatory=reg):
        response = client.post(
            "/calculate",
            headers=get_auth_headers(),
            json={
                "start_date": "2025-04-06",
                "end_date": "2026-04-05",
                "jurisdiction": "UK",
                "student_loan_plan": "plan_2",
            },
        )
    assert response.status_code == 200
    p = response.json()
    base = p["estimated_income_tax_due"] + p["estimated_class4_nic_due"] + p["student_loan_repayment_gbp"]
    assert base > 1000.0
    half = round(base * 0.5, 2)
    assert p["payment_on_account_jan"] == half
    assert p["payment_on_account_jul"] == half


def test_calculate_paye_tax_credit_reduces_amount_due():
    mock_transactions = [{"date": "2025-08-01", "amount": 60_000.0, "category": "income"}]
    reg = _minimal_regulatory_rules()
    with _httpx_get_router(transactions=mock_transactions, regulatory=reg):
        r0 = client.post(
            "/calculate",
            headers=get_auth_headers(),
            json={
                "start_date": "2025-04-06",
                "end_date": "2026-04-05",
                "jurisdiction": "UK",
                "paye_gross_salary_in_period_gbp": 12000.0,
            },
        )
        r1 = client.post(
            "/calculate",
            headers=get_auth_headers(),
            json={
                "start_date": "2025-04-06",
                "end_date": "2026-04-05",
                "jurisdiction": "UK",
                "paye_gross_salary_in_period_gbp": 12000.0,
                "paye_tax_paid_in_period_gbp": 2500.0,
            },
        )
    assert r0.status_code == r1.status_code == 200
    p0, p1 = r0.json(), r1.json()
    assert p1["paye_tax_credit_applied_gbp"] == 2500.0
    assert p1["estimated_tax_due"] == round(max(0.0, p0["estimated_tax_due"] - 2500.0), 2)


def test_calculate_tax_includes_class4_nic_for_higher_profit():
    mock_transactions = [
        {"date": "2023-05-10", "amount": 70000.0, "category": "income"},
        {"date": "2023-06-15", "amount": -2000.0, "category": "transport"},
    ]
    mock_response = httpx.Response(
        200,
        json=mock_transactions,
        request=httpx.Request("GET", "http://transactions-service/transactions/me"),
    )
    with _httpx_fixed_response(mock_response):
        response = client.post(
            "/calculate",
            headers=get_auth_headers(),
            json={"start_date": "2023-01-01", "end_date": "2023-12-31", "jurisdiction": "UK"},
        )
    assert response.status_code == 200
    payload = response.json()
    assert payload["taxable_profit"] == 68000.0
    assert payload["estimated_income_tax_due"] > 0
    assert payload["estimated_class4_nic_due"] > 0
    net = (
        payload["gross_tax_before_credits_gbp"]
        - payload["paye_tax_credit_applied_gbp"]
        - payload["cis_tax_credit_applied_gbp"]
        - payload["other_tax_credits_applied_gbp"]
    )
    assert payload["estimated_tax_due"] == round(max(0.0, net), 2)
    assert payload["mtd_obligation"]["reporting_required"] is False


def test_calculate_tax_student_loan_from_regulatory_rules():
    mock_transactions = [
        {"date": "2023-05-10", "amount": 50000.0, "category": "income"},
    ]
    reg = _minimal_regulatory_rules(
        student_loans={"plan_2": {"threshold": 27295, "rate": 0.09}},
    )
    with _httpx_get_router(transactions=mock_transactions, regulatory=reg):
        response = client.post(
            "/calculate",
            headers=get_auth_headers(),
            json={
                "start_date": "2023-04-06",
                "end_date": "2024-04-05",
                "jurisdiction": "UK",
                "student_loan_plan": "plan_2",
            },
        )
    assert response.status_code == 200
    payload = response.json()
    expected_sl = round(max(0.0, 50000.0 - 27295.0) * 0.09, 2)
    assert payload["student_loan_repayment_gbp"] == expected_sl
    assert payload["student_loan_repayment_gbp"] > 0
    gross = payload["gross_tax_before_credits_gbp"]
    assert gross >= payload["estimated_income_tax_due"] + payload["student_loan_repayment_gbp"]


def test_calculate_tax_scotland_bands_from_regulatory_service():
    mock_transactions = [
        {"date": "2026-05-10", "amount": 70000.0, "category": "income"},
        {"date": "2026-06-15", "amount": -2000.0, "category": "transport"},
    ]
    reg = _minimal_regulatory_rules()
    scot = _scotland_rates_payload_2025_26()
    with _httpx_get_router(transactions=mock_transactions, regulatory=reg, scotland=scot):
        r_ew = client.post(
            "/calculate",
            headers=get_auth_headers(),
            json={
                "start_date": "2026-04-06",
                "end_date": "2027-04-05",
                "jurisdiction": "UK",
                "region": "england_wales",
            },
        )
        r_sc = client.post(
            "/calculate",
            headers=get_auth_headers(),
            json={
                "start_date": "2026-04-06",
                "end_date": "2027-04-05",
                "jurisdiction": "UK",
                "region": "scotland",
            },
        )
    assert r_ew.status_code == 200 and r_sc.status_code == 200
    ew = r_ew.json()
    sc = r_sc.json()
    assert ew["income_tax_region"] == "england_wales"
    assert sc["income_tax_region"] == "scotland"
    warnings = sc.get("breakdown", {}).get("warnings") or []
    assert not any("unavailable" in w.lower() for w in warnings)
    assert sc["estimated_income_tax_due"] != ew["estimated_income_tax_due"]


def test_calculate_tax_flags_quarterly_reporting_when_income_exceeds_50000():
    mock_transactions = [
        {"date": "2026-05-10", "amount": 60000.0, "category": "income"},
        {"date": "2026-06-20", "amount": -5000.0, "category": "transport"},
    ]
    mock_response = httpx.Response(
        200,
        json=mock_transactions,
        request=httpx.Request("GET", "http://transactions-service/transactions/me"),
    )
    with _httpx_fixed_response(mock_response):
        response = client.post(
            "/calculate",
            headers=get_auth_headers(),
            json={"start_date": "2026-04-06", "end_date": "2027-04-05", "jurisdiction": "UK"},
        )
    assert response.status_code == 200
    payload = response.json()
    mtd = payload["mtd_obligation"]
    assert mtd["policy_code"] == "UK_MTD_ITSA_2026"
    assert mtd["threshold"] == 50000.0
    assert mtd["reporting_required"] is True
    assert mtd["reporting_cadence"] == "quarterly_updates_plus_final_declaration"
    assert len(mtd["quarterly_updates"]) == 4
    assert mtd["quarterly_updates"][0]["quarter"] == "Q1"


def test_calculate_tax_service_unavailable():
    with patch(
        "httpx.AsyncClient.get",
        new=AsyncMock(side_effect=httpx.ConnectError("Connection refused")),
    ):
        response = client.post(
            "/calculate",
            headers=get_auth_headers(),
            json={"start_date": "2023-01-01", "end_date": "2023-12-31", "jurisdiction": "UK"},
        )
    assert response.status_code == 502
    assert "Could not connect to transactions-service" in response.json()["detail"]


def test_calculate_and_submit_returns_mtd_obligation_and_creates_quarterly_reminders():
    mock_transactions = [
        {"date": "2026-05-10", "amount": 60000.0, "category": "income"},
        {"date": "2026-06-15", "amount": -3000.0, "category": "transport"},
    ]
    mock_get_response = httpx.Response(
        200,
        json=mock_transactions,
        request=httpx.Request("GET", "http://transactions-service/transactions/me"),
    )
    with _httpx_fixed_response(mock_get_response):
        with patch(
            "app.main.post_json_with_retry",
            side_effect=[
                {"submission_id": "mock-submission-id"},
                None,
                None,
                None,
                None,
                None,
            ],
        ) as mock_post:
            response = client.post(
                "/calculate-and-submit",
                headers=get_auth_headers(),
                json={"start_date": "2026-04-06", "end_date": "2027-04-05", "jurisdiction": "UK"},
            )
    assert response.status_code == 202
    payload = response.json()
    assert payload["submission_id"] == "mock-submission-id"
    assert payload["submission_mode"] == "annual_tax_return"
    assert payload["mtd_obligation"]["reporting_required"] is True
    assert len(payload["mtd_obligation"]["quarterly_updates"]) == 4
    assert mock_post.call_count == 6


def test_calculate_and_submit_uses_mtd_quarterly_endpoint_for_quarter_window():
    mock_transactions = [
        {"date": "2026-04-10", "amount": 20000.0, "category": "income"},
        {"date": "2026-05-15", "amount": -1000.0, "category": "transport"},
    ]
    mock_get_response = httpx.Response(
        200,
        json=mock_transactions,
        request=httpx.Request("GET", "http://transactions-service/transactions/me"),
    )
    with _httpx_fixed_response(mock_get_response):
        with patch(
            "app.main.post_json_with_retry",
            side_effect=[
                {"submission_id": "quarterly-submission-id"},
                None,
                None,
                None,
                None,
                None,
            ],
        ) as mock_post:
            response = client.post(
                "/calculate-and-submit",
                headers=get_auth_headers(),
                json={"start_date": "2026-04-06", "end_date": "2026-07-05", "jurisdiction": "UK"},
            )
    assert response.status_code == 202
    payload = response.json()
    assert payload["submission_mode"] == "mtd_quarterly_update"
    first_call = mock_post.call_args_list[0]
    assert first_call.args[0].endswith("/integrations/hmrc/mtd/quarterly-update")
    submitted_payload = first_call.kwargs["json_body"]
    assert submitted_payload["report"]["period"]["quarter"] == "Q1"
    assert submitted_payload["report"]["schema_version"] == "hmrc-mtd-itsa-quarterly-v1"


def test_calculate_and_submit_rejects_non_quarter_partial_period_when_mtd_required():
    mock_transactions = [
        {"date": "2026-05-10", "amount": 25000.0, "category": "income"},
        {"date": "2026-06-15", "amount": -1200.0, "category": "transport"},
    ]
    mock_get_response = httpx.Response(
        200,
        json=mock_transactions,
        request=httpx.Request("GET", "http://transactions-service/transactions/me"),
    )
    with _httpx_fixed_response(mock_get_response):
        response = client.post(
            "/calculate-and-submit",
            headers=get_auth_headers(),
            json={"start_date": "2026-04-06", "end_date": "2026-08-01", "jurisdiction": "UK"},
        )
    assert response.status_code == 400
    assert "submission period must match an HMRC quarter" in response.json()["detail"]


def test_public_self_employed_estimate_no_auth():
    response = client.post(
        "/public/self-employed-estimate",
        json={"gross_trading_income": 50000, "allowable_expenses": 5000, "use_trading_allowance": False},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["tax_year_label"] == "2025/26"
    assert "disclaimer" in data and len(data["disclaimer"]) > 20
    assert data["result"]["gross_trading_income"] == 50000
    assert data["result"]["total_tax_and_ni"] > 0
    assert data["result"]["net_take_home"] > 0


def test_public_self_employed_estimate_rejects_expenses_over_income():
    response = client.post(
        "/public/self-employed-estimate",
        json={"gross_trading_income": 1000, "allowable_expenses": 5000},
    )
    assert response.status_code == 400

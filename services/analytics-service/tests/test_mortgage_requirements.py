import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.mortgage_requirements import (
    MORTGAGE_TYPE_METADATA,
    build_mortgage_document_checklist,
)


def _codes(items: list[dict[str, str]]) -> set[str]:
    return {item["code"] for item in items}


def test_all_supported_mortgage_types_have_required_documents():
    for mortgage_type in MORTGAGE_TYPE_METADATA:
        checklist = build_mortgage_document_checklist(
            mortgage_type=mortgage_type,
            employment_profile="sole_trader",
            include_adverse_credit_pack=False,
        )
        required = checklist["required_documents"]
        assert len(required) > 0
        for item in required:
            assert item["code"]
            assert item["title"]
            assert item["reason"]


def test_buy_to_let_contains_rental_specific_documents():
    checklist = build_mortgage_document_checklist(
        mortgage_type="buy_to_let",
        employment_profile="sole_trader",
        include_adverse_credit_pack=False,
    )
    required_codes = _codes(checklist["required_documents"])
    assert "expected_rental_income" in required_codes
    assert "property_portfolio_schedule" in required_codes


def test_limited_company_director_profile_adds_company_evidence():
    checklist = build_mortgage_document_checklist(
        mortgage_type="remortgage",
        employment_profile="limited_company_director",
        include_adverse_credit_pack=False,
    )
    required_codes = _codes(checklist["required_documents"])
    assert "company_accounts_2y" in required_codes
    assert "dividend_vouchers" in required_codes


def test_include_adverse_credit_pack_adds_credit_explanation():
    checklist = build_mortgage_document_checklist(
        mortgage_type="first_time_buyer",
        employment_profile="sole_trader",
        include_adverse_credit_pack=True,
    )
    conditional_codes = _codes(checklist["conditional_documents"])
    assert "credit_issue_explanation" in conditional_codes


def test_unsupported_values_raise_error():
    try:
        build_mortgage_document_checklist(
            mortgage_type="unknown",
            employment_profile="sole_trader",
            include_adverse_credit_pack=False,
        )
        assert False, "Expected ValueError for unsupported mortgage type"
    except ValueError as exc:
        assert str(exc) == "unsupported_mortgage_type"

    try:
        build_mortgage_document_checklist(
            mortgage_type="first_time_buyer",
            employment_profile="unknown",
            include_adverse_credit_pack=False,
        )
        assert False, "Expected ValueError for unsupported employment profile"
    except ValueError as exc:
        assert str(exc) == "unsupported_employment_profile"

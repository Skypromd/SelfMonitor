import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.mortgage_requirements import (
    MORTGAGE_TYPE_METADATA,
    build_mortgage_readiness_assessment,
    build_mortgage_document_checklist,
    detect_document_codes_from_filenames,
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


def test_detect_document_codes_from_filenames_matches_expected_keywords():
    detected = detect_document_codes_from_filenames(
        [
            "Passport_scan.pdf",
            "latest_BANK_statement_March.pdf",
            "HMRC_SA302_2025.pdf",
            "right_to_buy_section_125_notice.pdf",
        ]
    )
    assert "photo_id" in detected
    assert "bank_statements_6m" in detected
    assert "sa302_2y" in detected
    assert "right_to_buy_notice" in detected


def test_build_mortgage_readiness_assessment_scores_and_missing_docs():
    checklist = build_mortgage_document_checklist(
        mortgage_type="first_time_buyer",
        employment_profile="sole_trader",
        include_adverse_credit_pack=True,
    )
    readiness = build_mortgage_readiness_assessment(
        checklist=checklist,
        uploaded_filenames=[
            "passport.pdf",
            "utility_bill_address.pdf",
            "sa302_2024.pdf",
            "tax_year_overview_2024.pdf",
        ],
    )
    assert readiness["uploaded_document_count"] == 4
    assert readiness["required_completion_percent"] < 100
    assert readiness["readiness_status"] in {"not_ready", "almost_ready", "ready_for_broker_review"}
    assert len(readiness["missing_required_documents"]) > 0
    assert len(readiness["next_actions"]) > 0


def test_build_mortgage_readiness_assessment_marks_ready_when_required_docs_present():
    checklist = build_mortgage_document_checklist(
        mortgage_type="first_time_buyer",
        employment_profile="sole_trader",
        include_adverse_credit_pack=False,
    )
    readiness = build_mortgage_readiness_assessment(
        checklist=checklist,
        uploaded_filenames=[
            "photo_id_passport.pdf",
            "utility_bill_proof_of_address.pdf",
            "bank_statement_april.pdf",
            "deposit_source_of_funds.pdf",
            "credit_commitment_summary.pdf",
            "sa302_2025.pdf",
            "tax_year_overview_2025.pdf",
            "gift_letter_signed.pdf",
        ],
    )
    assert readiness["required_completion_percent"] == 100.0
    assert readiness["readiness_status"] in {"almost_ready", "ready_for_broker_review"}

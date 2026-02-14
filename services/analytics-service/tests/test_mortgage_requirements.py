import os
import sys
import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.mortgage_requirements import (
    LENDER_PROFILE_METADATA,
    MORTGAGE_TYPE_METADATA,
    build_mortgage_evidence_quality_checks,
    build_mortgage_pack_index,
    build_mortgage_readiness_assessment,
    build_mortgage_readiness_matrix,
    build_mortgage_submission_gate,
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


def test_all_supported_lender_profiles_generate_valid_checklist():
    for lender_profile in LENDER_PROFILE_METADATA:
        checklist = build_mortgage_document_checklist(
            mortgage_type="first_time_buyer",
            employment_profile="sole_trader",
            include_adverse_credit_pack=False,
            lender_profile=lender_profile,
        )
        assert checklist["lender_profile"] == lender_profile
        assert checklist["lender_profile_label"]


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

    try:
        build_mortgage_document_checklist(
            mortgage_type="first_time_buyer",
            employment_profile="sole_trader",
            include_adverse_credit_pack=False,
            lender_profile="unknown",
        )
        assert False, "Expected ValueError for unsupported lender profile"
    except ValueError as exc:
        assert str(exc) == "unsupported_lender_profile"


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


def test_specialist_self_employed_profile_adds_profile_specific_documents():
    checklist = build_mortgage_document_checklist(
        mortgage_type="remortgage",
        employment_profile="sole_trader",
        include_adverse_credit_pack=False,
        lender_profile="specialist_self_employed",
    )
    required_codes = _codes(checklist["required_documents"])
    assert "business_bank_statements_12m" in required_codes
    assert "management_accounts_ytd" in required_codes


def test_build_mortgage_readiness_matrix_returns_all_types():
    matrix = build_mortgage_readiness_matrix(
        employment_profile="sole_trader",
        include_adverse_credit_pack=False,
        lender_profile="high_street_mainstream",
        uploaded_filenames=["passport.pdf", "bank_statement.pdf"],
    )
    assert matrix["total_mortgage_types"] == len(MORTGAGE_TYPE_METADATA)
    assert len(matrix["items"]) == len(MORTGAGE_TYPE_METADATA)
    assert matrix["overall_status"] in {"not_ready", "almost_ready", "ready_for_broker_review"}
    assert matrix["ready_for_broker_review_count"] + matrix["almost_ready_count"] + matrix["not_ready_count"] == len(
        MORTGAGE_TYPE_METADATA
    )


def test_build_mortgage_readiness_matrix_rejects_unsupported_profiles():
    try:
        build_mortgage_readiness_matrix(
            employment_profile="unknown",
            include_adverse_credit_pack=False,
            lender_profile="high_street_mainstream",
            uploaded_filenames=[],
        )
        assert False, "Expected ValueError for unsupported employment profile"
    except ValueError as exc:
        assert str(exc) == "unsupported_employment_profile"

    try:
        build_mortgage_readiness_matrix(
            employment_profile="sole_trader",
            include_adverse_credit_pack=False,
            lender_profile="unknown",
            uploaded_filenames=[],
        )
        assert False, "Expected ValueError for unsupported lender profile"
    except ValueError as exc:
        assert str(exc) == "unsupported_lender_profile"

    try:
        build_mortgage_readiness_matrix(
            employment_profile="sole_trader",
            include_adverse_credit_pack=False,
            lender_profile="high_street_mainstream",
            uploaded_filenames=[],
            mortgage_types=["first_time_buyer", "unknown"],
        )
        assert False, "Expected ValueError for unsupported mortgage type in matrix list"
    except ValueError as exc:
        assert str(exc) == "unsupported_mortgage_type"


def test_build_mortgage_pack_index_contains_evidence_map():
    checklist = build_mortgage_document_checklist(
        mortgage_type="remortgage",
        employment_profile="sole_trader",
        include_adverse_credit_pack=False,
        lender_profile="high_street_mainstream",
    )
    pack_index = build_mortgage_pack_index(
        checklist=checklist,
        uploaded_filenames=[
            "passport_photo_id.pdf",
            "bank_statement_may.pdf",
            "mortgage_statement_latest.pdf",
            "sa302_2025.pdf",
            "tax_year_overview_2025.pdf",
        ],
    )
    assert pack_index["uploaded_document_count"] == 5
    assert "photo_id" in pack_index["detected_document_codes"]
    required_evidence = pack_index["required_document_evidence"]
    assert any(item["code"] == "existing_mortgage_statement" and item["match_status"] == "matched" for item in required_evidence)
    assert any(item["match_status"] in {"matched", "missing"} for item in required_evidence)


def test_build_mortgage_evidence_quality_checks_flags_stale_period_and_low_ocr():
    quality = build_mortgage_evidence_quality_checks(
        uploaded_documents=[
            {
                "filename": "bank_statement_2024_01.pdf",
                "status": "completed",
                "uploaded_at": "2025-03-01T12:00:00Z",
                "extracted_data": {
                    "ocr_confidence": 0.4,
                    "needs_review": True,
                    "review_reason": "low_text_density",
                    "transaction_date": "2024-01-15",
                },
            }
        ],
        today=datetime.date(2026, 2, 1),
    )
    summary = quality["evidence_quality_summary"]
    issues = quality["evidence_quality_issues"]

    assert summary["total_issues"] >= 3
    assert summary["critical_count"] >= 1
    assert any(item["check_type"] == "unreadable_ocr" for item in issues)
    assert any(item["check_type"] == "staleness" for item in issues)
    assert any(item["check_type"] == "period_mismatch" for item in issues)


def test_build_mortgage_evidence_quality_checks_detects_name_mismatch():
    quality = build_mortgage_evidence_quality_checks(
        uploaded_documents=[
            {
                "filename": "passport_john_doe_scan.pdf",
                "status": "completed",
                "uploaded_at": "2026-01-20T12:00:00Z",
                "extracted_data": {"ocr_confidence": 0.95},
            }
        ],
        applicant_first_name="Alice",
        applicant_last_name="Smith",
        today=datetime.date(2026, 2, 1),
    )
    issues = quality["evidence_quality_issues"]
    assert any(item["check_type"] == "name_mismatch" for item in issues)


def test_build_mortgage_submission_gate_blocks_when_advisor_not_confirmed():
    gate = build_mortgage_submission_gate(
        readiness_status="ready_for_broker_review",
        evidence_quality_summary={"has_blockers": False},
        advisor_review_confirmed=False,
    )
    assert gate["advisor_review_required"] is True
    assert gate["broker_submission_allowed"] is False
    assert any("Advisor review confirmation" in blocker for blocker in gate["broker_submission_blockers"])


def test_build_mortgage_submission_gate_allows_when_all_conditions_pass():
    gate = build_mortgage_submission_gate(
        readiness_status="ready_for_broker_review",
        evidence_quality_summary={"has_blockers": False},
        advisor_review_confirmed=True,
    )
    assert gate["broker_submission_allowed"] is True
    assert gate["broker_submission_blockers"] == []

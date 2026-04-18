import datetime
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.ocr_pipeline import (
    build_text_excerpt,
    evaluate_ocr_quality,
    estimate_ocr_confidence,
    extract_total_amount,
    extract_transaction_date,
    extract_vat_from_text,
    infer_vendor_name,
    parse_analyze_expense_response,
)


def test_extract_total_amount_prefers_total_keyword_line():
    text = "\n".join(
        [
            "Tesco Business",
            "Item A 12.00",
            "VAT 2.40",
            "TOTAL £14.40",
            "Card paid 14.40",
        ]
    )
    assert extract_total_amount(text) == 14.4


def test_extract_transaction_date_supports_uk_day_month_year():
    text = "Receipt\nDate: 13/02/2026\nTOTAL 18.45"
    assert extract_transaction_date(text) == datetime.date(2026, 2, 13)


def test_extract_transaction_date_supports_text_month_format():
    text = "Invoice Date 7 Feb 2026\nTotal 42.00"
    assert extract_transaction_date(text) == datetime.date(2026, 2, 7)


def test_infer_vendor_name_from_ocr_text():
    text = "\n".join(["Trainline", "Receipt", "Date 2026-02-12", "Total 28.45"])
    assert infer_vendor_name(text=text, filename="trainline_receipt.pdf") == "Trainline"


def test_infer_vendor_name_falls_back_to_filename():
    assert infer_vendor_name(text="", filename="uber_business_receipt_scan.pdf") == "Uber Business"


def test_build_text_excerpt_truncates_long_text():
    long_text = "A" * 500
    excerpt = build_text_excerpt(long_text, limit=40)
    assert excerpt is not None
    assert len(excerpt) == 40
    assert excerpt.endswith("...")


def test_estimate_ocr_confidence_for_complete_extraction():
    confidence = estimate_ocr_confidence(
        text="Receipt text",
        total_amount=18.45,
        transaction_date=datetime.date(2026, 2, 13),
        vendor_name="Trainline",
    )
    assert confidence == 1.0


def test_evaluate_ocr_quality_requires_review_when_fields_missing():
    quality = evaluate_ocr_quality(
        text="Total 18.45",
        total_amount=18.45,
        transaction_date=None,
        vendor_name=None,
        threshold=0.75,
    )
    assert quality.needs_review is True
    assert quality.confidence < 0.75
    assert quality.reason == "missing_fields:transaction_date,vendor_name"


def test_evaluate_ocr_quality_marks_high_confidence_as_confirmed():
    quality = evaluate_ocr_quality(
        text="Trainline\nDate: 13/02/2026\nTOTAL 18.45",
        total_amount=18.45,
        transaction_date=datetime.date(2026, 2, 13),
        vendor_name="Trainline",
        threshold=0.75,
    )
    assert quality.needs_review is False
    assert quality.reason == "high_confidence"


def test_parse_analyze_expense_response_reads_summary_fields():
    response = {
        "Blocks": [
            {"BlockType": "LINE", "Text": "Coffee Shop Ltd"},
            {"BlockType": "LINE", "Text": "Total paid £14.40"},
        ],
        "ExpenseDocuments": [
            {
                "SummaryFields": [
                    {"Type": {"Text": "VENDOR_NAME"}, "ValueDetection": {"Text": "Coffee Shop Ltd"}},
                    {"Type": {"Text": "TOTAL"}, "ValueDetection": {"Text": "£14.40"}},
                    {"Type": {"Text": "VAT"}, "ValueDetection": {"Text": "£2.40"}},
                    {
                        "Type": {"Text": "INVOICE_RECEIPT_DATE"},
                        "ValueDetection": {"Text": "13/02/2026"},
                    },
                ]
            }
        ],
    }
    text, hints = parse_analyze_expense_response(response)
    assert "Coffee Shop Ltd" in text
    assert hints.vendor_name == "Coffee Shop Ltd"
    assert hints.total_amount == 14.4
    assert hints.vat_amount == 2.4
    assert hints.transaction_date == datetime.date(2026, 2, 13)


def test_extract_vat_from_text_finds_vat_line():
    text = "Items 12.00\nVAT £2.40\nTOTAL £14.40"
    assert extract_vat_from_text(text) == 2.4


def test_extract_vat_from_text_skips_net_subtotal_lines():
    text = "Net excluding VAT 12.00\nVAT £2.40"
    assert extract_vat_from_text(text) == 2.4


def test_estimate_ocr_confidence_bonus_for_vat():
    base = estimate_ocr_confidence(
        text="",
        total_amount=10.0,
        transaction_date=datetime.date(2026, 1, 1),
        vendor_name="Acme",
    )
    with_vat = estimate_ocr_confidence(
        text="",
        total_amount=10.0,
        transaction_date=datetime.date(2026, 1, 1),
        vendor_name="Acme",
        vat_amount=2.0,
    )
    assert base == 0.8
    assert with_vat == 0.85

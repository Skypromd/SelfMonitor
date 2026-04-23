import os
import sys

os.environ.setdefault("AUTH_SECRET_KEY", "test-secret-analytics-bundle")

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.main import (  # noqa: E402
    _hmrc_mortgage_document_excerpt,
    _tax_year_label_to_slash_param,
)


def test_tax_year_label_to_slash_param():
    assert _tax_year_label_to_slash_param("24-25") == "2024/2025"
    assert _tax_year_label_to_slash_param("") == "2025/2026"


def test_hmrc_mortgage_document_excerpt_filters_codes():
    pack_index = {
        "required_document_evidence": [
            {
                "code": "sa302_2y",
                "title": "SA302",
                "match_status": "matched",
                "matched_filenames": ["sa302_2024.pdf"],
                "reason": "r",
            },
            {
                "code": "photo_id",
                "title": "ID",
                "match_status": "missing",
                "matched_filenames": [],
                "reason": "x",
            },
        ],
        "conditional_document_evidence": [
            {
                "code": "tax_year_overviews_2y",
                "title": "TYO",
                "match_status": "missing",
                "matched_filenames": [],
                "reason": "m",
            }
        ],
    }
    out = _hmrc_mortgage_document_excerpt(pack_index)
    assert "disclaimer" in out
    assert len(out["items"]) == 2
    codes = {i["code"] for i in out["items"]}
    assert codes == {"sa302_2y", "tax_year_overviews_2y"}

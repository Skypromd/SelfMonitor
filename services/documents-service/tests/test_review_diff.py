import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.crud import _build_review_changes


def test_build_review_changes_tracks_before_after_values():
    before_data = {
        "vendor_name": "Tesco",
        "total_amount": 18.45,
        "transaction_date": "2026-02-13",
        "suggested_category": "office_supplies",
        "expense_article": "office_costs",
        "is_potentially_deductible": True,
    }
    after_data = {
        "vendor_name": "Tesco Stores UK",
        "total_amount": 19.10,
        "transaction_date": "2026-02-14",
        "suggested_category": "office_supplies",
        "expense_article": "office_costs",
        "is_potentially_deductible": True,
    }

    changes = _build_review_changes(before_data=before_data, after_data=after_data)

    assert changes["vendor_name"] == {"before": "Tesco", "after": "Tesco Stores UK"}
    assert changes["total_amount"] == {"before": 18.45, "after": 19.1}
    assert changes["transaction_date"] == {"before": "2026-02-13", "after": "2026-02-14"}
    assert "suggested_category" not in changes


def test_build_review_changes_normalizes_equivalent_values():
    before_data = {
        "total_amount": 18.4,
        "transaction_date": "2026-02-13T00:00:00+00:00",
    }
    after_data = {
        "total_amount": "18.40",
        "transaction_date": "2026-02-13",
    }

    changes = _build_review_changes(before_data=before_data, after_data=after_data)

    assert changes == {}


def test_build_review_changes_includes_auto_derived_fields():
    before_data = {
        "suggested_category": "transport",
        "expense_article": "travel_costs",
        "is_potentially_deductible": True,
    }
    after_data = {
        "suggested_category": "meals_and_entertainment",
        "expense_article": "staff_entertainment",
        "is_potentially_deductible": False,
    }

    changes = _build_review_changes(before_data=before_data, after_data=after_data)

    assert changes["suggested_category"]["before"] == "transport"
    assert changes["suggested_category"]["after"] == "meals_and_entertainment"
    assert changes["expense_article"]["before"] == "travel_costs"
    assert changes["expense_article"]["after"] == "staff_entertainment"
    assert changes["is_potentially_deductible"] == {"before": True, "after": False}

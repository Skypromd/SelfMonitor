"""Tests for shared_categories category_map module."""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from libs.shared_categories.category_map import (
    ALL_CATEGORIES,
    EXPENSE_CATEGORIES,
    INCOME_CATEGORIES,
    PERSONAL_CATEGORIES,
    export_digital_record_categories,
    get_category,
    get_hmrc_field,
    get_sa_box,
)


def test_all_categories_have_required_fields():
    for cat in ALL_CATEGORIES:
        assert cat.key, f"Category missing key: {cat}"
        assert cat.label, f"Category missing label: {cat.key}"
        assert cat.description, f"Category missing description: {cat.key}"


def test_income_categories_are_flagged():
    for cat in INCOME_CATEGORIES:
        assert cat.is_income is True, f"{cat.key} should be is_income=True"


def test_expense_categories_are_not_income():
    for cat in EXPENSE_CATEGORIES:
        assert cat.is_income is False, f"{cat.key} should be is_income=False"


def test_get_category_known_key():
    cat = get_category("income")
    assert cat is not None
    assert cat.key == "income"
    assert cat.mtd_field == "turnover"


def test_get_category_unknown_key():
    assert get_category("nonexistent_key_xyz") is None


def test_get_hmrc_field_income():
    assert get_hmrc_field("income") == "turnover"


def test_get_hmrc_field_expense():
    assert get_hmrc_field("office_supplies") == "officeAndAdminCosts"


def test_get_hmrc_field_unknown():
    assert get_hmrc_field("totally_unknown") is None


def test_get_sa_box_income():
    box = get_sa_box("income")
    assert box is not None
    assert "Box" in box


def test_groceries_not_deductible():
    cat = get_category("groceries")
    assert cat is not None
    assert cat.hmrc_sa_box is None
    assert cat.mtd_field is None
    assert cat.suspicious_warning is not None


def test_travel_has_not_advice_copy():
    cat = get_category("travel")
    assert cat is not None
    assert cat.not_advice_copy is not None
    assert len(cat.not_advice_copy) > 20


def test_export_digital_record_categories():
    records = export_digital_record_categories()
    assert isinstance(records, list)
    assert len(records) == len(ALL_CATEGORIES)
    for rec in records:
        assert "key" in rec
        assert "label" in rec
        assert "mtd_field" in rec
        assert "is_income" in rec


def test_no_duplicate_keys():
    keys = [c.key for c in ALL_CATEGORIES]
    assert len(keys) == len(set(keys)), "Duplicate category keys found"


def test_all_categories_combined_count():
    combined = INCOME_CATEGORIES + EXPENSE_CATEGORIES + PERSONAL_CATEGORIES
    assert len(combined) == len(ALL_CATEGORIES)

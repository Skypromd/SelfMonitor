"""UK self-employed category mapping — HMRC SA103 / MTD ITSA fields."""
from .category_map import (
    ALL_CATEGORIES,
    EXPENSE_CATEGORIES,
    INCOME_CATEGORIES,
    PERSONAL_CATEGORIES,
    Category,
    export_digital_record_categories,
    get_category,
    get_hmrc_field,
    get_sa_box,
)

__all__ = [
    "ALL_CATEGORIES",
    "EXPENSE_CATEGORIES",
    "INCOME_CATEGORIES",
    "PERSONAL_CATEGORIES",
    "Category",
    "export_digital_record_categories",
    "get_category",
    "get_hmrc_field",
    "get_sa_box",
]

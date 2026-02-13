import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.expense_classifier import suggest_category_from_keywords, to_expense_article


def test_keyword_classifier_detects_transport():
    assert suggest_category_from_keywords("Uber business trip to client office") == "transport"


def test_keyword_classifier_detects_subscriptions():
    assert suggest_category_from_keywords("Adobe subscription renewal") == "subscriptions"


def test_keyword_classifier_returns_none_for_unknown():
    assert suggest_category_from_keywords("Random merchant without known pattern") is None


def test_expense_article_mapping_for_deductible_category():
    assert to_expense_article("transport") == ("travel_costs", True)


def test_expense_article_mapping_for_non_deductible_category():
    assert to_expense_article("food_and_drink") == ("meals_and_entertainment", False)


def test_expense_article_mapping_for_missing_category():
    assert to_expense_article(None) == (None, None)

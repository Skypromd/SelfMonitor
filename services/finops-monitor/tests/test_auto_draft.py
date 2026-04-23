import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.mtd.auto_draft import parse_quarter_label_for_tax_engine


def test_parse_quarter_label_ok():
    assert parse_quarter_label_for_tax_engine("Q1 2026/27") == (2026, "Q1")
    assert parse_quarter_label_for_tax_engine("Q4 2025/26 ") == (2025, "Q4")


def test_parse_quarter_label_rejects_garbage():
    with pytest.raises(ValueError):
        parse_quarter_label_for_tax_engine("bad")

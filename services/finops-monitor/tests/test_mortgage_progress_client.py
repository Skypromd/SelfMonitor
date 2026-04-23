import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.marketing.mortgage_progress_client import parse_current_step_id_and_title


def test_parse_current_step():
    data = {
        "current_step_id": "deposit",
        "steps": [
            {"id": "credit", "title": "Credit", "status": "completed"},
            {"id": "deposit", "title": "Save deposit", "status": "current"},
        ],
    }
    assert parse_current_step_id_and_title(data) == ("deposit", "Save deposit")


def test_parse_missing_step():
    assert parse_current_step_id_and_title({}) == (None, None)

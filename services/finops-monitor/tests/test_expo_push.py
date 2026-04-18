import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.mtd.expo_push import validate_expo_push_token_format


def test_validate_expo_push_token_accepts_exponent_format():
    assert validate_expo_push_token_format("ExponentPushToken[abc123]")
    assert validate_expo_push_token_format("  ExponentPushToken[x]  ")


def test_validate_expo_push_token_rejects_garbage():
    assert not validate_expo_push_token_format("")
    assert not validate_expo_push_token_format("fcm:xxx")

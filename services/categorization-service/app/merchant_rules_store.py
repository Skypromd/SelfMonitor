import json
import os
import threading
from pathlib import Path
from typing import Optional

from .learn_store import learning_pattern

_LOCK = threading.Lock()
_MAX_RULES = 5000


def _merchant_path() -> Path:
    return Path(
        os.environ.get(
            "CATEGORIZATION_MERCHANT_RULES_PATH",
            "/tmp/categorization_merchant_rules.json",
        )
    )


def _load() -> dict[str, str]:
    path = _merchant_path()
    if not path.is_file():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            return {}
        return {str(k): str(v) for k, v in raw.items()}
    except Exception:
        return {}


def _save(data: dict[str, str]) -> None:
    path = _merchant_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def lookup_global_merchant_category(description: str) -> Optional[str]:
    desc_lower = description.lower().strip()
    with _LOCK:
        rules = dict(_load())
    best: Optional[str] = None
    best_len = 0
    for pattern, cat in rules.items():
        p = pattern.lower()
        if p in desc_lower and len(p) > best_len:
            best = cat
            best_len = len(p)
    return best


def upsert_global_merchant_rule(raw_pattern: str, category: str) -> Optional[str]:
    pattern = learning_pattern(raw_pattern)
    if len(pattern) < 2:
        return None
    with _LOCK:
        data = _load()
        data[pattern] = category
        if len(data) > _MAX_RULES:
            overflow = len(data) - _MAX_RULES
            for key in list(data.keys())[:overflow]:
                del data[key]
        _save(data)
    return pattern


def list_global_merchant_rules() -> dict[str, str]:
    with _LOCK:
        return dict(_load())

import json
import os
import re
import threading
from pathlib import Path
from typing import Optional

_LOCK = threading.Lock()

_MAX_PATTERNS_PER_USER = 400


def _learned_path() -> Path:
    return Path(os.environ.get("CATEGORIZATION_LEARNED_RULES_PATH", "/tmp/categorization_learned_rules.json"))


def learning_pattern(description: str) -> str:
    s = description.lower().strip()
    s = re.sub(r"[^a-z0-9]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    parts = s.split()
    while parts and parts[-1].isdigit():
        parts.pop()
    s = " ".join(parts)
    return (s[:80] if s else description.lower().strip()[:80]).strip()


def _load() -> dict[str, dict[str, str]]:
    path = _learned_path()
    if not path.is_file():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            return {}
        out: dict[str, dict[str, str]] = {}
        for uid, rules in raw.items():
            if isinstance(rules, dict):
                out[str(uid)] = {str(k): str(v) for k, v in rules.items()}
        return out
    except Exception:
        return {}


def _save(data: dict[str, dict[str, str]]) -> None:
    path = _learned_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def upsert_rule(user_id: str, description: str, category: str) -> Optional[str]:
    pattern = learning_pattern(description)
    if len(pattern) < 3:
        return None
    with _LOCK:
        data = _load()
        bucket = data.setdefault(user_id, {})
        bucket[pattern] = category
        if len(bucket) > _MAX_PATTERNS_PER_USER:
            for key in list(bucket.keys())[: len(bucket) - _MAX_PATTERNS_PER_USER]:
                del bucket[key]
        _save(data)
    return pattern


def lookup_user_category(user_id: str, description: str) -> Optional[str]:
    desc_lower = description.lower().strip()
    with _LOCK:
        rules = dict(_load().get(user_id, {}))
    best: Optional[str] = None
    best_len = 0
    for pattern, cat in rules.items():
        p = pattern.lower()
        if p in desc_lower and len(p) > best_len:
            best = cat
            best_len = len(p)
    return best

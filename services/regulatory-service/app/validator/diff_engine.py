from __future__ import annotations

from typing import Any


def _flatten(prefix: str, obj: Any, out: dict[str, Any]) -> None:
    if isinstance(obj, dict):
        for k, v in obj.items():
            _flatten(f"{prefix}.{k}" if prefix else str(k), v, out)
    elif isinstance(obj, list):
        out[prefix] = obj
    else:
        out[prefix] = obj


def diff_tax_rule_dicts(old: dict[str, Any], new: dict[str, Any]) -> list[dict[str, Any]]:
    """Shallow structural diff of leaf values between two rule payloads."""
    fo: dict[str, Any] = {}
    fn: dict[str, Any] = {}
    _flatten("", old, fo)
    _flatten("", new, fn)
    keys = sorted(set(fo) | set(fn))
    changes: list[dict[str, Any]] = []
    for k in keys:
        if fo.get(k) != fn.get(k):
            changes.append({"path": k, "old": fo.get(k), "new": fn.get(k)})
    return changes

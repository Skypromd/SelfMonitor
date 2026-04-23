"""
Emit a small CSV of merchant-pattern → category rows for offline ML prep (roadmap 1.2).

Reads the same JSON map as categorization-service (`CATEGORIZATION_MERCHANT_RULES_PATH`).
Usage:
  python scripts/export_categorization_training_sample.py --out training_merchants.csv --limit 5000
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from pathlib import Path


def _rules_path() -> Path:
    raw = os.environ.get("CATEGORIZATION_MERCHANT_RULES_PATH", "").strip()
    if raw:
        return Path(raw)
    repo = Path(__file__).resolve().parents[1]
    candidate = repo / "services" / "categorization-service" / "data" / "merchant_rules.json"
    if candidate.is_file():
        return candidate
    return Path("/tmp/categorization_merchant_rules.json")


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--out", type=Path, default=Path("categorization_merchant_training_sample.csv"))
    p.add_argument("--limit", type=int, default=5000, help="Max rows to write (after stable sort).")
    args = p.parse_args()

    path = _rules_path()
    if not path.is_file():
        print(f"No merchant rules file at {path}; set CATEGORIZATION_MERCHANT_RULES_PATH.", file=sys.stderr)
        return 1

    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"Failed to read JSON: {exc}", file=sys.stderr)
        return 1
    if not isinstance(raw, dict):
        print("Expected top-level JSON object {pattern: category}.", file=sys.stderr)
        return 1

    rows = sorted((str(k).strip(), str(v).strip()) for k, v in raw.items() if str(k).strip() and str(v).strip())
    rows = rows[: max(0, args.limit)]

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["merchant_pattern", "category_slug"])
        w.writerows(rows)

    print(f"Wrote {len(rows)} rows to {args.out.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

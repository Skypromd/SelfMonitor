"""Apply vetted JSON patches to frozen rule files (RU.12 — use only after owner approval)."""
from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def apply_json_patch_to_tax_year_file(
    data_dir: Path,
    filename: str,
    patch: dict[str, Any],
    *,
    backup: bool = True,
) -> Path:
    """
    Merge shallow patch into top-level keys of a tax year JSON file.
    Writes backup `filename.bak.<iso>` when backup=True.
    """
    path = data_dir / filename
    if not path.is_file():
        raise FileNotFoundError(path)
    if backup:
        bak = data_dir / f"{filename}.bak.{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
        shutil.copy2(path, bak)
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    for k, v in patch.items():
        if k in ("tax_year",) and v != data.get("tax_year"):
            raise ValueError("Refusing to change tax_year via patch")
        data[k] = v
    data["version"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H%M%SZ")
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")
    return path

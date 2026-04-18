#!/usr/bin/env python3
"""Walk repo and apply MyNetTax rebrand replacements with bundle ID guard."""
from __future__ import annotations

import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
THIS_FILE = Path(__file__).resolve()

EXTENSIONS = {
    ".tsx", ".ts", ".js", ".jsx", ".py", ".json", ".md", ".yaml", ".yml",
    ".html", ".txt", ".css", ".example", ".toml", ".graphql",
}

SKIP_DIRS = {
    "node_modules", ".git", "dist", "build", ".next", "__pycache__",
    ".venv", "venv", "target",
}

BUNDLE_GUARD = "__BUNDLE_ID_GUARD__"
BUNDLE_ORIGINAL = "com.selfmonitor.app"

ORDERED_REPLACEMENTS: list[tuple[str, str]] = [
    ("SelfMonitor", "MyNetTax"),
    ("selfmonitor.app", "mynettax.app"),
    ("selfmonitor.co.uk", "mynettax.co.uk"),
    ("selfmonitor.uk", "mynettax.co.uk"),
    ("selfmonitor.ai", "mynettax.com"),
    ("selfmonitor.com", "mynettax.com"),
    ("pay.selfmonitor", "pay.mynettax"),
    ("app.selfmonitor", "app.mynettax"),
    ("api.selfmonitor", "api.mynettax"),
    ("staging-api.selfmonitor", "staging-api.mynettax"),
    ("recommendations.selfmonitor", "recommendations.mynettax"),
    ("status.selfmonitor", "status.mynettax"),
    ("selfmonitor", "mynettax"),
]


def apply_transforms(text: str) -> str:
    s = text.replace(BUNDLE_ORIGINAL, BUNDLE_GUARD)
    for old, new in ORDERED_REPLACEMENTS:
        s = s.replace(old, new)
    s = s.replace(BUNDLE_GUARD, BUNDLE_ORIGINAL)
    return s


def iter_target_files(root: Path):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for name in filenames:
            p = (Path(dirpath) / name).resolve()
            if p == THIS_FILE:
                continue
            if p.suffix.lower() in EXTENSIONS:
                yield p


def main() -> None:
    changed: list[Path] = []
    for path in iter_target_files(REPO_ROOT):
        try:
            raw = path.read_bytes()
        except OSError as e:
            print(f"read error {path}: {e}", flush=True)
            continue
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            try:
                text = raw.decode("utf-8-sig")
            except UnicodeDecodeError:
                print(f"skip (not utf-8): {path}", flush=True)
                continue
        new_text = apply_transforms(text)
        if new_text != text:
            try:
                path.write_text(new_text, encoding="utf-8", newline="\n")
            except OSError as e:
                print(f"write error {path}: {e}", flush=True)
                continue
            changed.append(path)

    print(f"changed_files_count: {len(changed)}", flush=True)
    for p in changed[:40]:
        print(p, flush=True)
    if len(changed) > 40:
        print("...", flush=True)


if __name__ == "__main__":
    main()

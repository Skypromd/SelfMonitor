#!/usr/bin/env python3
"""Run release preflight smoke checks for critical user and billing flows."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


@dataclass(frozen=True)
class Check:
    id: str
    description: str
    command: list[str]


@dataclass(frozen=True)
class CheckResult:
    check_id: str
    description: str
    command: list[str]
    cwd: str
    duration_seconds: float
    exit_code: int
    started_at: str
    finished_at: str

    @property
    def passed(self) -> bool:
        return self.exit_code == 0


REPO_ROOT = Path(__file__).resolve().parents[1]


def _resolve_pytest_node_id(*, test_file: str, candidates: list[str]) -> str:
    """Pick the first existing pytest node id by inspecting the test file."""
    absolute_path = REPO_ROOT / test_file
    if not absolute_path.exists():
        return f"{test_file}::{candidates[0]}"
    try:
        contents = absolute_path.read_text(encoding="utf-8")
    except OSError:
        return f"{test_file}::{candidates[0]}"
    for candidate in candidates:
        if f"def {candidate}(" in contents:
            return f"{test_file}::{candidate}"
    return f"{test_file}::{candidates[0]}"


AUTH_LOGIN_SMOKE_NODE_ID = _resolve_pytest_node_id(
    test_file="services/auth-service/tests/test_main.py",
    candidates=[
        "test_login_and_get_me_returns_token_pair",
        "test_login_and_get_me",
    ],
)

BACKEND_CHECKS: list[Check] = [
    Check(
        id="auth_login",
        description="Auth login smoke",
        command=[
            "python3",
            "-m",
            "pytest",
            "-q",
            AUTH_LOGIN_SMOKE_NODE_ID,
        ],
    ),
    Check(
        id="profile_roundtrip",
        description="User profile create/get smoke",
        command=[
            "python3",
            "-m",
            "pytest",
            "-q",
            "services/user-profile-service/tests/test_main.py::test_create_and_get_profile",
        ],
    ),
    Check(
        id="transactions_import",
        description="Transactions import smoke",
        command=[
            "python3",
            "-m",
            "pytest",
            "-q",
            "services/transactions-service/tests/test_main.py::test_import_and_get_transactions",
        ],
    ),
    Check(
        id="consent_audit",
        description="Consent audit smoke",
        command=[
            "python3",
            "-m",
            "pytest",
            "-q",
            "services/consent-service/tests/test_main.py::test_record_consent_triggers_audit",
        ],
    ),
    Check(
        id="handoff_audit",
        description="Partner handoff audit smoke",
        command=[
            "python3",
            "-m",
            "pytest",
            "-q",
            "services/partner-registry/tests/test_main.py::test_handoff_triggers_audit",
        ],
    ),
    Check(
        id="invoice_lifecycle",
        description="Invoice generation/listing/detail smoke",
        command=[
            "python3",
            "-m",
            "pytest",
            "-q",
            "services/partner-registry/tests/test_main.py::test_generate_list_and_get_invoice",
        ],
    ),
    Check(
        id="invoice_exports",
        description="Invoice PDF and accounting CSV smoke",
        command=[
            "python3",
            "-m",
            "pytest",
            "-q",
            "services/partner-registry/tests/test_main.py::test_invoice_pdf_and_accounting_exports",
        ],
    ),
]

FRONTEND_CHECK = Check(
    id="web_build",
    description="Web portal production build",
    command=["npm", "run", "build"],
)

QUICK_IDS = {"auth_login", "transactions_import", "handoff_audit", "invoice_exports"}


def run_check(check: Check, *, cwd: Path) -> CheckResult:
    print(f"\n[preflight] {check.id}: {check.description}")
    print(f"[preflight] command: {' '.join(check.command)}")
    started = datetime.now(timezone.utc).isoformat()
    start_perf = time.perf_counter()
    completed = subprocess.run(check.command, cwd=str(cwd), check=False)
    duration_seconds = time.perf_counter() - start_perf
    finished = datetime.now(timezone.utc).isoformat()
    if completed.returncode == 0:
        print(f"[preflight] {check.id}: OK ({duration_seconds:.2f}s)")
    else:
        print(
            f"[preflight] {check.id}: FAILED ({completed.returncode}) "
            f"({duration_seconds:.2f}s)"
        )
    return CheckResult(
        check_id=check.id,
        description=check.description,
        command=check.command,
        cwd=str(cwd),
        duration_seconds=duration_seconds,
        exit_code=completed.returncode,
        started_at=started,
        finished_at=finished,
    )


def write_timing_snapshot(path: Path, results: list[CheckResult]) -> None:
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "check_count": len(results),
        "all_passed": all(result.passed for result in results),
        "total_duration_seconds": round(
            sum(result.duration_seconds for result in results), 4
        ),
        "checks": [
            {
                "id": result.check_id,
                "description": result.description,
                "command": result.command,
                "cwd": result.cwd,
                "duration_seconds": round(result.duration_seconds, 4),
                "exit_code": result.exit_code,
                "passed": result.passed,
                "started_at": result.started_at,
                "finished_at": result.finished_at,
            }
            for result in results
        ],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n")


def build_check_plan(
    *,
    quick: bool,
    only_ids: set[str],
    include_frontend: bool,
) -> list[tuple[Check, Path]]:
    selected_backend = BACKEND_CHECKS
    if quick:
        selected_backend = [check for check in BACKEND_CHECKS if check.id in QUICK_IDS]
    if only_ids:
        selected_backend = [check for check in selected_backend if check.id in only_ids]

    plan: list[tuple[Check, Path]] = [(check, REPO_ROOT) for check in selected_backend]
    if include_frontend and (not only_ids or FRONTEND_CHECK.id in only_ids):
        plan.append((FRONTEND_CHECK, REPO_ROOT / "apps" / "web-portal"))
    return plan


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Release preflight checker")
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Run a reduced set of critical smoke checks.",
    )
    parser.add_argument(
        "--include-frontend",
        action="store_true",
        help="Include web portal production build check.",
    )
    parser.add_argument(
        "--only",
        action="append",
        default=[],
        help="Run only selected check ID(s). Can be repeated.",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List available check IDs and exit.",
    )
    parser.add_argument(
        "--timings-json",
        default="",
        help="Write a timing snapshot JSON file to the given path.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    only_ids = set(args.only)

    all_ids = {check.id for check in BACKEND_CHECKS}
    all_ids.add(FRONTEND_CHECK.id)

    unknown_ids = only_ids.difference(all_ids)
    if unknown_ids:
        print(f"Unknown check ID(s): {', '.join(sorted(unknown_ids))}", file=sys.stderr)
        return 2

    if args.list:
        print("Available checks:")
        for check in BACKEND_CHECKS:
            print(f"- {check.id}: {check.description}")
        print(f"- {FRONTEND_CHECK.id}: {FRONTEND_CHECK.description}")
        return 0

    plan = build_check_plan(
        quick=args.quick,
        only_ids=only_ids,
        include_frontend=args.include_frontend,
    )
    if not plan:
        print("No checks selected; nothing to run.")
        return 0

    timing_results: list[CheckResult] = []
    timing_path = Path(args.timings_json).resolve() if args.timings_json else None

    for check, cwd in plan:
        check_result = run_check(check, cwd=cwd)
        timing_results.append(check_result)
        if check_result.exit_code != 0:
            if timing_path:
                write_timing_snapshot(timing_path, timing_results)
                print(f"[preflight] timing snapshot written: {timing_path}")
            return check_result.exit_code

    total_duration = sum(result.duration_seconds for result in timing_results)
    print(f"[preflight] total duration: {total_duration:.2f}s")
    if timing_path:
        write_timing_snapshot(timing_path, timing_results)
        print(f"[preflight] timing snapshot written: {timing_path}")

    print("\n[preflight] all selected checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

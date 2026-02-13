#!/usr/bin/env python3
"""Run release preflight smoke checks for critical user and billing flows."""

from __future__ import annotations

import argparse
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Check:
    id: str
    description: str
    command: list[str]


REPO_ROOT = Path(__file__).resolve().parents[1]

BACKEND_CHECKS: list[Check] = [
    Check(
        id="auth_login",
        description="Auth login smoke",
        command=[
            "python3",
            "-m",
            "pytest",
            "-q",
            "services/auth-service/tests/test_main.py::test_login_and_get_me",
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


def run_check(check: Check, *, cwd: Path) -> int:
    print(f"\n[preflight] {check.id}: {check.description}")
    print(f"[preflight] command: {' '.join(check.command)}")
    result = subprocess.run(check.command, cwd=str(cwd), check=False)
    if result.returncode == 0:
        print(f"[preflight] {check.id}: OK")
    else:
        print(f"[preflight] {check.id}: FAILED ({result.returncode})")
    return result.returncode


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

    for check, cwd in plan:
        exit_code = run_check(check, cwd=cwd)
        if exit_code != 0:
            return exit_code

    print("\n[preflight] all selected checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

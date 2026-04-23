#!/usr/bin/env python3
"""Print strong random values for Phase 0 / first deploy (.env). Do not commit output."""

from __future__ import annotations

import secrets


def main() -> None:
    print(
        "# Paste into .env (keep private). "
        "Equivalent: openssl rand -hex 32|64. See docs/GO_LIVE_CHECKLIST.md.\n"
    )
    print(f"POSTGRES_PASSWORD={secrets.token_hex(32)}")
    print(f"AUTH_SECRET_KEY={secrets.token_hex(64)}")
    print(f"VAULT_DEV_ROOT_TOKEN_ID={secrets.token_hex(32)}")
    print(f"INTERNAL_SERVICE_SECRET={secrets.token_hex(32)}")
    print(f"MINIO_ROOT_PASSWORD={secrets.token_hex(24)}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Writes a production env file from .env.example with every password and key
generated, so a first deploy never runs on the sample values the backend's
boot guard refuses.

Usage:
    python3 scripts/create_stack_env.py --domain https://cuisine.example.com \\
        --admin-mail you@example.com [--output .env]

The admin password is printed once; sign in with it and change it.
"""

import argparse
import re
import secrets
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--domain", required=True, help="public https:// URL")
    parser.add_argument("--admin-mail", required=True)
    parser.add_argument("--output", default=".env")
    parser.add_argument("--force", action="store_true", help="overwrite an existing file")
    args = parser.parse_args()

    if not args.domain.startswith("https://"):
        print("--domain must be an https:// URL", file=sys.stderr)
        return 1
    out = Path(args.output)
    if out.exists() and not args.force:
        print(f"{out} exists; pass --force to overwrite it", file=sys.stderr)
        return 1

    db_password = secrets.token_urlsafe(24)
    admin_password = secrets.token_urlsafe(12)
    values = {
        "DOMAIN": args.domain.rstrip("/"),
        "POSTGRES_PASSWORD": db_password,
        "DATABASE__URL": f"postgresql+psycopg://cuisine:{db_password}@postgres:5432/cuisine",
        "SECURITY__SECRET_KEY": secrets.token_hex(32),
        "SECURITY__ENCRYPTION_KEY": secrets.token_hex(32),
        "INIT__MAIL": args.admin_mail,
        "INIT__PASSWORD": admin_password,
    }
    text = (REPO_ROOT / ".env.example").read_text(encoding="utf-8")
    for key, value in values.items():
        text, count = re.subn(rf"^{re.escape(key)}=.*$", f"{key}={value}", text, flags=re.M)
        if count != 1:
            print(f"{key} not found exactly once in .env.example", file=sys.stderr)
            return 1
    out.write_text(text, encoding="utf-8")
    out.chmod(0o600)
    print(f"Wrote {out}. The first administrator signs in as 'admin' with: {admin_password}")
    print("Keep SECURITY__ENCRYPTION_KEY safe apart from the backups; a restore needs it.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

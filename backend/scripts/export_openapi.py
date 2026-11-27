"""
Writes the API contract to openapi/openapi.json, the snapshot the frontend
generates its types from (frontend/scripts/generate-api-types.ts). It is
committed, so a change to a route or schema shows up in review, and CI
fails when the snapshot and the code disagree.

Usage:
    poetry run python scripts/export_openapi.py           # (re)write the snapshot
    poetry run python scripts/export_openapi.py --check   # verify only, exit 1 on drift
"""

import os

# `cfg` validates its settings at import time, so the app needs them in the
# environment before it can be imported. Throwaway values do, since the
# export never connects to anything.
if not os.getenv("ENV_FILE"):
    os.environ.setdefault("DEBUG", "false")
    os.environ.setdefault("SECURITY__SECRET_KEY", "openapi-export-secret-key")
    os.environ.setdefault("SECURITY__ENCRYPTION_KEY", "openapi-export-encryption-key")
    os.environ.setdefault("DATABASE__URL", "sqlite:///./.openapi-export.db")
    os.environ.setdefault("REDIS__URL", "redis://localhost:6379/15")
    os.environ.setdefault("INIT__FULL_NAME", "OpenAPI Export")
    os.environ.setdefault("INIT__MAIL", "openapi-export@example.com")
    os.environ.setdefault("INIT__PASSWORD", "openapi-export-password")

# isort: split

import argparse
import difflib
import json
import sys
from pathlib import Path

from src.bootstrap.main import app

SNAPSHOT = Path(__file__).resolve().parent.parent / "openapi" / "openapi.json"
DIFF_LINE_LIMIT = 200


def render() -> str:
    spec = app.openapi()
    # The version changes with every release and is not part of the shape.
    spec["info"].pop("version", None)
    return json.dumps(spec, indent=2, ensure_ascii=False, sort_keys=False) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="verify only, exit 1 on drift")
    args = parser.parse_args()
    current = render()
    if args.check:
        stored = SNAPSHOT.read_text(encoding="utf-8") if SNAPSHOT.exists() else ""
        if stored == current:
            print(f"{SNAPSHOT.name} is up to date.")
            return 0
        diff = list(
            difflib.unified_diff(
                stored.splitlines(), current.splitlines(), "committed", "code", lineterm=""
            )
        )
        print("\n".join(diff[:DIFF_LINE_LIMIT]))
        print(f"\n{SNAPSHOT} is out of date. Run scripts/export_openapi.py.", file=sys.stderr)
        return 1
    SNAPSHOT.parent.mkdir(parents=True, exist_ok=True)
    SNAPSHOT.write_text(current, encoding="utf-8")
    print(f"Wrote {SNAPSHOT}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

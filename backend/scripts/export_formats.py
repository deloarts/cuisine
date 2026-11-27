"""
Writes the JSON Schema of every released exchange format version to
formats/<format>.v<version>.schema.json, and of every message of every
peering protocol version to formats/cuisine-peering.v<version>.<message>.schema.json.
The schemas are derived from the format dataclasses
(src/cookbook/application/services/formats/) and the protocol message
dataclasses (src/platform/application/services/peering_messages.py) and
committed, so a change to a format or a message shows up in review, and CI
fails when a schema and the code disagree. docs/reference/formats.md has
the rules.

Usage:
    poetry run python scripts/export_formats.py           # (re)write the schemas
    poetry run python scripts/export_formats.py --check   # verify only, exit 1 on drift
"""

import argparse
import difflib
import json
import sys
from pathlib import Path

from src.cookbook.application.services.formats.codec import json_schema
from src.cookbook.application.services.formats.specs import FORMATS
from src.platform.application.services.peering_messages import PROTOCOL_MESSAGES
from src.platform.application.services.peering_messages import PROTOCOL_NAME

TARGET = Path(__file__).resolve().parent.parent / "formats"
DIFF_LINE_LIMIT = 200


def render() -> dict[Path, str]:
    """The content of every schema file, by path."""
    files: dict[Path, str] = {}
    for spec in FORMATS:
        for version, document in sorted(spec.versions.items()):
            schema = json_schema(
                document,
                schema_id=f"urn:cuisine:format:{spec.name}:{version}",
                title=f"{spec.name} version {version}",
            )
            text = json.dumps(schema, indent=2, ensure_ascii=False) + "\n"
            files[TARGET / f"{spec.name}.v{version}.schema.json"] = text
    for version, messages in sorted(PROTOCOL_MESSAGES.items()):
        for message, root in sorted(messages.items()):
            schema = json_schema(
                root,
                schema_id=f"urn:cuisine:protocol:{PROTOCOL_NAME}:{version}:{message}",
                title=f"{PROTOCOL_NAME} version {version}: {message}",
            )
            text = json.dumps(schema, indent=2, ensure_ascii=False) + "\n"
            files[TARGET / f"{PROTOCOL_NAME}.v{version}.{message}.schema.json"] = text
    return files


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="verify only, exit 1 on drift")
    args = parser.parse_args()
    current = render()
    if args.check:
        stale = False
        for path, text in current.items():
            stored = path.read_text(encoding="utf-8") if path.exists() else ""
            if stored == text:
                continue
            stale = True
            diff = list(
                difflib.unified_diff(
                    stored.splitlines(), text.splitlines(), "committed", "code", lineterm=""
                )
            )
            print("\n".join(diff[:DIFF_LINE_LIMIT]))
            print(f"\n{path} is out of date.", file=sys.stderr)
        extra = sorted(set(TARGET.glob("*.schema.json")) - set(current))
        for path in extra:
            stale = True
            print(f"{path} belongs to no known format or protocol version.", file=sys.stderr)
        if stale:
            print("Run scripts/export_formats.py.", file=sys.stderr)
            return 1
        print(f"The {len(current)} format and protocol schemas are up to date.")
        return 0
    TARGET.mkdir(parents=True, exist_ok=True)
    for path, text in current.items():
        path.write_text(text, encoding="utf-8")
        print(f"Wrote {path}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

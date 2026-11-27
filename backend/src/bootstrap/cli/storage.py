"""
Moving stored file content between storage providers, run inside the
backend or maintenance container:

    python -m src.bootstrap.cli.storage status
    python -m src.bootstrap.cli.storage copy --to local [--from postgres]
    python -m src.bootstrap.cli.storage verify [--provider local]
    python -m src.bootstrap.cli.storage remove-source --from postgres

`copy` defaults its source to the active provider (STORAGE__PROVIDER).
After it, set STORAGE__PROVIDER to the target, restart, run `copy` again
with `--from` the old provider for files uploaded meanwhile, then
`remove-source`. The steps and their safety rules are in
docs/OPERATIONS.md section 2.2.
"""

import argparse
import asyncio
import sys

from src.platform.adapters.outbound.persistence.repositories.stored_file_repository import (
    SqlAlchemyStoredFileRepository,
)
from src.platform.adapters.outbound.persistence.session import SessionLocal
from src.platform.adapters.outbound.persistence.unit_of_work import SqlAlchemyUnitOfWork
from src.platform.adapters.outbound.storage.factory import PROVIDERS
from src.platform.adapters.outbound.storage.factory import content_store
from src.platform.application.use_cases.files.move_storage import MoveReport
from src.platform.application.use_cases.files.move_storage import MoveStorage
from src.platform.infrastructure.config.settings import cfg


def _print(report: MoveReport) -> int:
    print(
        f"files: {report.files}, copied: {report.copied}, already there: {report.skipped}, "
        f"removed: {report.removed}, problems: {len(report.problems)}"
    )
    for line in report.problems:
        print(f"  {line}", file=sys.stderr)
    return 0 if report.ok else 1


async def _run(args: argparse.Namespace) -> int:
    active = cfg.storage.provider
    async with SessionLocal() as db:
        move = MoveStorage(files=SqlAlchemyStoredFileRepository(db), uow=SqlAlchemyUnitOfWork(db))
        if args.command == "status":
            files = await SqlAlchemyStoredFileRepository(db).list_all()
            print(f"active provider: {active}, files: {len(files)}")
            return 0
        if args.command == "copy":
            source = args.source or active
            report = await move.copy(content_store(source, db), content_store(args.to, db))
            code = _print(report)
            if code == 0 and args.to != active:
                print(
                    f"Next: set STORAGE__PROVIDER={args.to}, restart, run copy again with "
                    f"--from {source} --to {args.to}, then remove-source --from {source}."
                )
            return code
        if args.command == "verify":
            return _print(await move.verify(content_store(args.provider or active, db)))
        report = await move.remove_source(content_store(args.source, db), content_store(active, db))
        return _print(report)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="storage")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("status")
    copy = sub.add_parser("copy")
    copy.add_argument("--to", required=True, choices=PROVIDERS)
    copy.add_argument("--from", dest="source", choices=PROVIDERS)
    verify = sub.add_parser("verify")
    verify.add_argument("--provider", choices=PROVIDERS)
    remove = sub.add_parser("remove-source")
    remove.add_argument("--from", dest="source", required=True, choices=PROVIDERS)
    args = parser.parse_args(argv)
    try:
        return asyncio.run(_run(args))
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())

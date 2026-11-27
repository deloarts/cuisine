#!/bin/sh
set -e

# Out-of-process CLI commands, dispatched before migrations run: recovery
# must work even when the schema is mid-upgrade. `maintenance` is the
# sidecar's command (docker-compose.yml, service "maintenance"): it never
# migrates and never touches the app, it just blocks so `docker compose
# exec` has somewhere to run `admin` from. Allowlisted explicitly; an
# arbitrary module name is never dispatched.
case "$1" in
  admin)
    shift
    exec python -m src.bootstrap.cli.admin "$@"
    ;;
  storage)
    shift
    exec python -m src.bootstrap.cli.storage "$@"
    ;;
  maintenance)
    exec sleep infinity
    ;;
esac

# Concurrent starts are safe: alembic/env.py holds an advisory lock while it
# migrates, so a second container waits and then finds nothing to do. The
# nightly backup sidecar is the way back from a migration gone wrong
# (docs/OPERATIONS.md).
alembic upgrade head

exec "$@"

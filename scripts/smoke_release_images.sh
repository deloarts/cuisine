#!/usr/bin/env bash
# Start the backend and frontend images the way an operator does, before
# they are published: the release docker-compose.yml with an empty Postgres
# and Redis, throwaway secrets and the two images pinned by the caller. The
# backend's entrypoint migrates the empty database, and the check passes
# once the backend answers /health and /ready with 200, reports the expected
# version on /api/v1/public/info, nginx accepts its configuration, and the
# frontend serves index.html and proxies /health, /ready and the API to the
# backend. The stack and its volumes are removed afterwards, also on
# failure, which prints the containers' logs first. Used by release.yml's
# smoke job; runs locally against any two images, a local build included.
#
# Usage: scripts/smoke_release_images.sh BACKEND_IMAGE FRONTEND_IMAGE [VERSION]
#
#   BACKEND_IMAGE, FRONTEND_IMAGE   image references, by digest in CI
#   VERSION                         the version the backend must report
#                                   (optional)
#   SMOKE_FRONTEND_PORT             host port of the frontend (default 18080)
#   SMOKE_TIMEOUT                   seconds the stack may take to become
#                                   healthy, migrations included (default 600)
#   SMOKE_PLATFORM                  linux/amd64 or linux/arm64: runs every
#                                   container of the stack as that platform
#                                   and checks the backend and frontend run
#                                   on it (default: the host's own; another
#                                   platform needs QEMU registered)
set -euo pipefail

USAGE="usage: smoke_release_images.sh BACKEND_IMAGE FRONTEND_IMAGE [VERSION]"
BACKEND_IMAGE="${1:?$USAGE}"
FRONTEND_IMAGE="${2:?$USAGE}"
EXPECTED_VERSION="${3:-}"
PORT="${SMOKE_FRONTEND_PORT:-18080}"
TIMEOUT="${SMOKE_TIMEOUT:-600}"
PLATFORM="${SMOKE_PLATFORM:-}"

# The machine name `uname -m` prints inside a container of the platform.
case "$PLATFORM" in
  "") EXPECTED_MACHINE="" ;;
  linux/amd64) EXPECTED_MACHINE=x86_64 ;;
  linux/arm64) EXPECTED_MACHINE=aarch64 ;;
  *)
    echo "::error::SMOKE_PLATFORM must be linux/amd64 or linux/arm64, not '$PLATFORM'." >&2
    exit 1
    ;;
esac
if [[ -n "$PLATFORM" ]]; then
  # Compose pulls and runs every service as this platform, Postgres and
  # Redis included, from the multi-platform images the compose file pins.
  export DOCKER_DEFAULT_PLATFORM="$PLATFORM"
fi

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK="$(mktemp -d)"
PROJECT="cuisine-smoke-$$"

fail() {
  echo "::error::$1" >&2
  exit 1
}

key() {
  openssl rand -hex 32
}

# No profile may start a sidecar (maintenance, cloudflared) in the smoke
# stack.
unset COMPOSE_PROFILES

# Every value is a throwaway one, made for this run only. The keys are
# distinct and long enough for the backend's boot guard, which refuses
# sample values and a non-https DOMAIN outside debug mode. The smoke test
# never relies on cookies or CORS, so the https DOMAIN need not be served.
db_password="$(key)"
cat >"$WORK/smoke.env" <<ENV
CUISINE_VERSION=smoke
FRONTEND_PORT=$PORT
DEBUG=false
DOMAIN=https://127.0.0.1:$PORT
LOG_LEVEL=INFO
DATABASE__URL=postgresql+psycopg://cuisine:$db_password@postgres:5432/cuisine
POSTGRES_USER=cuisine
POSTGRES_PASSWORD=$db_password
POSTGRES_DB=cuisine
REDIS__URL=redis://redis:6379/0
SECURITY__SECRET_KEY=$(key)
SECURITY__ENCRYPTION_KEY=$(key)
INIT__FULL_NAME=Smoke Test
INIT__MAIL=smoke@example.com
INIT__PASSWORD=$(key)
ENV

# The release compose file names the images by tag; this override pins the
# two images under test instead, so the stack runs exactly them.
cat >"$WORK/images.yml" <<YAML
services:
  backend:
    image: $BACKEND_IMAGE
  frontend:
    image: $FRONTEND_IMAGE
YAML

compose() {
  ENV_FILE="$WORK/smoke.env" docker compose \
    --project-name "$PROJECT" \
    --env-file "$WORK/smoke.env" \
    --file "$REPO_ROOT/docker-compose.yml" \
    --file "$WORK/images.yml" \
    "$@"
}

ok=false
cleanup() {
  if [[ "$ok" != true ]]; then
    echo "Smoke test failed; the stack's state and logs follow." >&2
    compose ps --all >&2 || true
    compose logs --no-color >&2 || true
  fi
  compose down --volumes --remove-orphans >/dev/null 2>&1 || true
  rm -rf "$WORK"
}
trap cleanup EXIT

echo "Starting $BACKEND_IMAGE and $FRONTEND_IMAGE on an empty database${PLATFORM:+ as $PLATFORM}."
compose up --detach --wait --wait-timeout "$TIMEOUT" ||
  fail "The stack did not become healthy within ${TIMEOUT}s."

if [[ -n "$EXPECTED_MACHINE" ]]; then
  for service in backend frontend; do
    machine="$(compose exec -T "$service" uname -m)" ||
      fail "Could not read the $service container's machine type."
    [[ "$machine" == "$EXPECTED_MACHINE" ]] ||
      fail "The $service container runs on $machine, not $EXPECTED_MACHINE ($PLATFORM)."
    echo "$service runs on $machine."
  done
fi

health="$(compose exec -T backend curl -fsS http://localhost:3000/health)" ||
  fail "The backend does not answer /health."
echo "backend /health: $health"

ready="$(compose exec -T backend curl -fsS http://localhost:3000/ready)" ||
  fail "The backend's /ready does not answer 200: $(compose exec -T backend curl -sS http://localhost:3000/ready || true)"
echo "backend /ready: $ready"

info="$(compose exec -T backend curl -fsS http://localhost:3000/api/v1/public/info)" ||
  fail "The backend does not answer /api/v1/public/info."
echo "backend /api/v1/public/info: $info"
if [[ -n "$EXPECTED_VERSION" && "$info" != *"\"version\":\"$EXPECTED_VERSION\""* ]]; then
  fail "The backend reports $info, not version $EXPECTED_VERSION."
fi

compose exec -T frontend nginx -t || fail "nginx refuses the frontend's configuration."

index="$(curl -fsS "http://127.0.0.1:$PORT/")" || fail "The frontend does not serve /."
[[ "$index" == *'<div id="app"></div>'* ]] || fail "The frontend's / is not the app's index.html."

curl -fsS "http://127.0.0.1:$PORT/health" >/dev/null || fail "The frontend does not proxy /health."
curl -fsS "http://127.0.0.1:$PORT/ready" >/dev/null || fail "The frontend does not proxy /ready."
curl -fsS "http://127.0.0.1:$PORT/api/v1/public/info" >/dev/null ||
  fail "The frontend does not proxy the API."

ok=true
echo "Smoke test passed."

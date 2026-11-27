# releasing and CI

The CI jobs, the release workflow, the GHCR retention workflow and the release scripts. The concept is in [RELEASING.md](../RELEASING.md); the GitHub settings these workflows rely on are in [releasing-github-setup.md](releasing-github-setup.md).

- [1 CI](#1-ci)
- [2 the release workflow](#2-the-release-workflow)
- [3 the GHCR retention workflow](#3-the-ghcr-retention-workflow)
- [4 scripts](#4-scripts)

## 1 CI

`.github/workflows/ci.yml` runs on every pull request and on pushes to `release/**`. A path filter skips the halves a change does not touch.

| Job | Runs |
| --- | ---- |
| `backend` | ruff check and format, mypy strict, the OpenAPI snapshot check, the format schema check ([formats.md section 7](formats.md#7-schema-files-and-golden-fixtures)), pytest in parallel with coverage |
| `backend-arm64` | pytest on linux/arm64: builds the backend Dockerfile's `dev` stage for arm64 under QEMU and runs the tests in it, mounted from the checkout. Slow under emulation, so it runs only on pushes to `release/**` and on the release PR |
| `backend-migrations` | `alembic upgrade head`, `alembic check` and `alembic downgrade base` on an empty Postgres 16 service |
| `frontend` | `npm ci`, type-check, lint, unit tests, i18n parity, the API types check, the build |
| `images` | builds both images for linux/amd64 and linux/arm64 (under QEMU) without pushing, so a broken Dockerfile or a dependency without an arm64 wheel fails the PR |
| `gitleaks` | a secret scan over the full history with the pinned, checksum-verified binary |

`images` is a matrix job, and a skipped matrix job reports a single `images` check instead of one per component, so the ruleset requires `images-verify`, which always runs and fails only when an image build failed or was cancelled. CodeQL is not a workflow of this repository; it runs through GitHub's default setup ([releasing-github-setup.md section 4](releasing-github-setup.md#4-code-security-and-dependency-updates)).

Every third-party action is pinned to a commit SHA with its version in a comment.

## 2 the release workflow

`.github/workflows/release.yml` runs when a pull request from `release/X.Y.Z` is merged into `main`:

1. `guard` checks out the merge commit and runs `scripts/check_release_version.sh X.Y.Z`: a `0.Y.Z` version, both version files carrying it, a CHANGELOG section, no existing tag.
2. `images` builds `backend` (target `prod`) and `frontend` from the merge commit for linux/amd64 and linux/arm64 and pushes them to `ghcr.io/<owner>/cuisine/<component>` under the candidate tag `sha-<commit>` only. Each tag is an image index listing both platforms, and a host pulls its own. arm64 builds under QEMU on the amd64 runner, since GitHub's arm64 runners are free only for public repositories; the frontend's build stage runs natively (`--platform=$BUILDPLATFORM`), because its output is the same static files on every platform.
3. `resolve` pins both candidates by the digest of their image index, so every later job acts on exactly the images that were built.
4. `smoke` runs `scripts/smoke_release_images.sh` against the two digests, once per platform: the release `docker-compose.yml` on an empty Postgres and Redis with throwaway secrets. The entrypoint must migrate the database, the backend must answer `/health` and `/ready` and report `X.Y.Z` on `/api/v1/public/info`, nginx must accept its configuration, and the frontend must serve the app and proxy `/health`, `/ready` and the API. The arm64 run sets `SMOKE_PLATFORM=linux/arm64`, which starts the whole stack as arm64 under QEMU and checks that the backend and frontend containers run on `aarch64`; it is slow, so it gets a longer `SMOKE_TIMEOUT`.
5. `tag` tags the merge commit `vX.Y.Z` and pushes the tag, only once the smoke test passed.
6. `publish` retags the tested digests as `vX.Y.Z`, `vX.Y` and `latest` with `docker buildx imagetools create --prefer-index=false` and checks that every tag names the tested digest.
7. `github-release` creates the release with the CHANGELOG section as its notes.

A failed smoke test publishes nothing and creates no tag. Fix the cause in a new pull request and release again; the failed candidate stays `sha-` only and the retention workflow removes it eventually.

The smoke test runs locally against any two images, a local build included: `scripts/smoke_release_images.sh <backend image> <frontend image> [version]`. `SMOKE_PLATFORM=linux/arm64` runs it as arm64, which needs QEMU registered with Docker on an x86-64 host (`docker run --privileged --rm tonistiigi/binfmt --install arm64`).

## 3 the GHCR retention workflow

`.github/workflows/ghcr-retention.yml` runs `scripts/ghcr_retention.sh` every Monday. It keeps the newest 30 versions per package whose tags all start with `sha-` and deletes the older ones, together with their platform and attestation manifests. A version that also carries a release tag is never deleted. Started by hand, it is a dry run unless that box is cleared. Deleting needs the Admin role for the repository on each package ([releasing-github-setup.md section 5](releasing-github-setup.md#5-packages)).

## 4 scripts

| Script | Does |
| ------ | ---- |
| `scripts/bump_version.sh X.Y.Z` | sets the version in `backend/pyproject.toml` and `frontend/package.json` (and its lock file) |
| `scripts/release_start.sh X.Y.Z` | branches, bumps, regenerates the API snapshot and types, opens the CHANGELOG section, commits and pushes |
| `scripts/check_release_version.sh X.Y.Z` | the release guard, shared by the workflow and `release_start.sh` |
| `scripts/smoke_release_images.sh BACKEND FRONTEND [VERSION]` | the release smoke test, shared by the workflow and local runs |
| `scripts/ghcr_retention.sh OWNER [PACKAGE...]` | deletes old `sha-` candidate images, used by the retention workflow |
| `scripts/create_stack_env.py` | writes a production env file with generated secrets |

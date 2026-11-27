# releasing

How Cuisine is versioned and released. The CI and workflow details are in [reference/releasing-ci.md](reference/releasing-ci.md), the GitHub settings that protect the flow in [reference/releasing-github-setup.md](reference/releasing-github-setup.md).

## 1 versioning

Backend and frontend share one version, `0.MINOR.PATCH`, kept in `backend/pyproject.toml` and `frontend/package.json`. A minor release may change the database schema and the API; a patch release only fixes. `scripts/bump_version.sh X.Y.Z` changes both version files together, never edit one alone.

## 2 the flow

Development is trunk based ([ADR 0003](adr/0003-trunk-based-release-flow.md)). Every change reaches `main` as a squash-merged pull request whose CI passed. A release is a pull request too:

1. `scripts/release_start.sh 0.2.0` branches `release/0.2.0` from an up-to-date `main`, bumps both versions, regenerates the OpenAPI snapshot and the frontend types, turns `[Unreleased]` in `CHANGELOG.md` into the version's section, commits and pushes.
2. Review the CHANGELOG section on the branch and open the pull request into `main`. When `backend/src/bootstrap/data/ingredients.yaml` changed since the last release, run `poetry run python scripts/build_base_ingredients.py --check` in `backend/` first: CI cannot, as it needs the FDC datasets, and the check catches a stale `ingredients.nutrition.json` and FDC foods whose description changed.
3. Merging it runs `.github/workflows/release.yml`: it checks the versions and the CHANGELOG once more, builds both images and pushes them to GHCR as a release candidate, starts the candidate on an empty database, and only when that smoke test passes tags the merge commit `v0.2.0`, publishes the tested images as `v0.2.0`, `v0.2` and `latest`, and creates the GitHub release from the CHANGELOG section.

## 3 the CHANGELOG

Every user-facing change adds a line under `[Unreleased]` in its own pull request, in the sections of [Keep a Changelog](https://keepachangelog.com/en/1.1.0/): Added, Changed, Fixed, Removed, Security. Write for the people who run an instance, not for developers. A release that bumps an exchange format version says so in its section, naming the format and both versions ([reference/formats.md](reference/formats.md)).

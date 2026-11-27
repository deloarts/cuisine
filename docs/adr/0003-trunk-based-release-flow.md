# 0003 trunk-based flow with release PRs that tag on merge

- Status: accepted
- Date: 2026-11-21

## context

Cuisine is developed mostly by one person, with a public repository and images on GHCR. A release has to bump two version files, regenerate the API snapshot and the frontend types, and turn the unreleased CHANGELOG entries into a section; doing that by hand on `main` invites a tag on a commit that never passed CI.

## decision

Like Glados, every change reaches `main` as a squash-merged pull request with green CI. A release is a pull request from `release/X.Y.Z`, prepared by `scripts/release_start.sh`. Merging it runs the release workflow, which checks the versions and the CHANGELOG, builds both images once under their commit tag, starts them together in a smoke test, and only then tags the merge commit, gives the tested images their version tags and creates the GitHub release. Backend and frontend share one `0.MINOR.PATCH` version.

## consequences

A tag always points at a reviewed commit whose tree passed CI, and the release notes are the CHANGELOG section. Unlike Glados, the images are built in the release workflow rather than promoted from CI candidates, which is simpler but means the published image is built once more from the same tree; the smoke test before tagging makes sure the published digests are the tested ones, and a failed smoke test leaves no tag behind.

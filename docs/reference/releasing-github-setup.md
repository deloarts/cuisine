# github repository setup

The exact GitHub settings, rulesets and package settings the release flow relies on. Everything here is configured by hand in the repository settings, and no workflow changes it. [RELEASING.md](../RELEASING.md) explains the flow these settings protect, and [releasing-ci.md](releasing-ci.md) the workflows they gate.

- [1 pull requests](#1-pull-requests)
- [2 actions](#2-actions)
- [3 rulesets](#3-rulesets)
  - [3.1 main](#31-main)
  - [3.2 release tags](#32-release-tags)
- [4 code security and dependency updates](#4-code-security-and-dependency-updates)
- [5 packages](#5-packages)
- [6 issue templates](#6-issue-templates)

## 1 pull requests

Settings → General → Pull Requests:

- *Allow merge commits* is off.
- *Allow squash merging* is on, with the default message "Pull request title and commit details". Squash is the only merge method, so every change and every release lands on `main` as one commit with a single parent, which the release workflow tags.
- *Allow rebase merging* is off.
- *Always suggest updating pull request branches* is on, which shows the "Update branch" button that release pull requests need.
- *Automatically delete head branches* is on.

## 2 actions

Settings → Actions → General:

- *Workflow permissions* is "Read repository contents and packages permissions". Jobs that write tags, releases, images or package deletions request it themselves.
- *Allow GitHub Actions to create and approve pull requests* is off.
- *Fork pull request workflows* require approval for all external contributors.

## 3 rulesets

Settings → Rules → Rulesets.

### 3.1 main

A branch ruleset targeting the default branch:

- It sets *Restrict deletions*, *Block force pushes*, *Require linear history* and *Require signed commits*. GitHub signs the squash commit of a pull request merged in the web interface, so the rule needs no signing key on any branch and only blocks commits that reach `main` another way.
- It sets *Require a pull request before merging* with 0 approvals and Squash as the only allowed merge method.
- It sets *Require status checks to pass* with *Require branches to be up to date before merging* enabled and the checks of `ci.yml`: `backend`, `backend-migrations`, `frontend`, `images-verify` and `gitleaks`. A check can only be picked once it has run at least once.
- A job the path filter skips reports as passed, so a change that only touches the frontend still satisfies `backend` and `backend-migrations`.
- The up-to-date requirement is what keeps a release branch from being merged behind `main`.

### 3.2 release tags

A tag ruleset named `release tags`, targeting `v*`:

- It sets *Restrict updates*, *Restrict deletions* and *Block force pushes*, with Repository admin as bypass.
- Creation stays unrestricted because the release workflow creates the tags.
- Release tags are immutable once pushed. If a release turns out to be wrong, the fix is a new patch, not touching the tag.

## 4 code security and dependency updates

- Settings → Code security has Dependabot alerts, secret scanning with push protection, and private vulnerability reporting on.
- CodeQL runs through GitHub's default setup (Settings → Code security → Code scanning → CodeQL analysis → Default), with the languages it detects: Python, JavaScript/TypeScript and GitHub Actions. The repository has no CodeQL workflow of its own; the default setup analyses every pull request into `main`, every push to it, and runs weekly.
- Dependabot security updates stay off and the repository has no `dependabot.yml`. Dependabot only raises alerts and never opens pull requests, and dependencies are updated by hand.

## 5 packages

- Pushed images land under the repository owner's GHCR packages, at `ghcr.io/<owner>/cuisine/backend` and `ghcr.io/<owner>/cuisine/frontend`.
- Each package's visibility is set once in its package settings and kept for every later tag. Both must be public, so a deployment pulls them without credentials. A container package that a workflow's first push creates usually starts out private even when the repository is public, so after the first release open each package's settings and change its visibility to public.
- `ghcr-retention.yml` deletes old `sha-<commit>` candidate versions with the workflow token ([releasing-ci.md section 3](releasing-ci.md#3-the-ghcr-retention-workflow)). The job asks for `packages: write`, but the token can delete a version only when the repository holds the Admin role on the package. Set it in each package's settings under *Manage Actions access* for `cuisine/backend` and `cuisine/frontend`. Admin includes the Write role the release jobs need to push.

## 6 issue templates

`.github/ISSUE_TEMPLATE/` holds two issue forms, a bug report labelled `bug` and a feature request labelled `enhancement`, both with the same list of areas. `config.yml` turns blank issues off and links to the private vulnerability report and the installation guide, so a vulnerability never starts as a public issue. When a new part of the app gets its own area, it is added to the list in both forms.

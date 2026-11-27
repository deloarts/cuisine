# architecture decision records

An ADR records one decision that shapes the code: the situation that forced it, what was decided, and what follows from it. ADRs explain why the code looks the way it does; the rules themselves live in [CONTRIBUTING.md](../CONTRIBUTING.md), [DEVELOPMENT.md](../DEVELOPMENT.md) and [reference/](../reference/README.md).

## index

| ADR | Title | Status |
| --- | ----- | ------ |
| [0001](0001-hexagonal-without-bounded-contexts.md) | Hexagonal layers without bounded contexts | accepted |
| [0002](0002-file-storage-providers.md) | File content goes to one of three storage providers, Postgres by default | accepted |
| [0003](0003-trunk-based-release-flow.md) | Trunk-based flow with release PRs that tag on merge | accepted |
| [0004](0004-secret-encryption-at-rest.md) | Encrypt readable secrets at rest with a dedicated key | accepted |
| [0005](0005-openvue-ui-library.md) | OpenVue as the UI component library | accepted |

## writing a new ADR

Write one when a change sets a rule others must follow, picks between real alternatives, or would surprise a reader of the code without its reason. Copy the template below into `NNNN-short-title.md` with the next free number, keep each section to one short paragraph, and add a row to the index. An accepted ADR is not rewritten; a later decision that replaces it gets its own ADR, and the old one's status becomes `superseded by NNNN`.

```markdown
# NNNN title as a short statement of the decision

- Status: proposed | accepted | superseded by NNNN
- Date: YYYY-MM-DD

## context

## decision

## consequences
```

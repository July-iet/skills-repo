# Agent Record System Template

Use these templates as compact starting points. Delete sections that do not apply.

## `AGENTS.md` Navigation Block

```markdown
## Agent Project Record

- Main index: `docs/agent/README.md`
- Project map: `docs/agent/project-map.md`
- Runtime and commands: `docs/agent/runtime.md`
- Shared contracts: `docs/agent/contracts.md`
- Workflows: `docs/agent/workflows.md`
- Decisions and risks: `docs/agent/decisions.md`
```

Keep project-specific coding rules above this block. Do not move full architecture notes into `AGENTS.md`.

## `docs/agent/README.md`

```markdown
# Agent Project Record

Last reviewed: YYYY-MM-DD
Review scope: Briefly state what was inspected.

## Project Summary

State what this project does in 3-5 sentences.

## Quick Navigation

| Need | Read |
|---|---|
| Module boundaries and entry points | `docs/agent/project-map.md` |
| Commands, runtime, generated files | `docs/agent/runtime.md` |
| APIs, routes, storage, headers, events | `docs/agent/contracts.md` |
| Common flows | `docs/agent/workflows.md` |
| Decisions, risks, open questions | `docs/agent/decisions.md` |

## Current Index Status

| Index | Status | Notes |
|---|---|---|
| CodeGraph | Unknown | Update after checking `.codegraph/` or project index tools. |
| Docs drift | Unknown | Update after comparing docs with source. |

## Agent Start Here

1. Read local `AGENTS.md`.
2. Read this file.
3. Open only the specific linked doc needed for the task.
4. Use source files as the final authority.
```

## `docs/agent/project-map.md`

```markdown
# Project Map

Last reviewed: YYYY-MM-DD

## Modules

| Area | Purpose | Entry Points | Notes |
|---|---|---|---|
| TBD | TBD | TBD | TBD |

## Important Source Paths

| Path | Why It Matters |
|---|---|
| TBD | TBD |

## Shared Utilities And State

| Item | Producer | Consumers | Compatibility Notes |
|---|---|---|---|
| TBD | TBD | TBD | TBD |
```

## `docs/agent/runtime.md`

```markdown
# Runtime And Commands

Last reviewed: YYYY-MM-DD

## Project Type

State framework, package manager, runtime, and deployment shape.

## Commands

| Task | Command | When To Run | Verified |
|---|---|---|---|
| Install | TBD | TBD | No |
| Build | TBD | TBD | No |
| Test | TBD | TBD | No |
| Dev server | TBD | TBD | No |

## Generated Or External Artifacts

| Artifact | Source | Update Rule |
|---|---|---|
| TBD | TBD | TBD |
```

## `docs/agent/contracts.md`

```markdown
# Contracts

Last reviewed: YYYY-MM-DD

## Routes And APIs

| Contract | Producer | Consumers | Compatibility Notes |
|---|---|---|---|
| TBD | TBD | TBD | TBD |

## Storage, Headers, Events, Globals

| Key Or Contract | Writes | Reads | Timing | Compatibility Notes |
|---|---|---|---|---|
| TBD | TBD | TBD | TBD | TBD |
```

## `docs/agent/workflows.md`

```markdown
# Workflows

Last reviewed: YYYY-MM-DD

## Flow Name

Entry point: `path/or/symbol`

Steps:

1. TBD
2. TBD

Verification:

- TBD
```

## `docs/agent/decisions.md`

```markdown
# Decisions And Risks

Last reviewed: YYYY-MM-DD

## Decisions

| Date | Decision | Reason | Impact |
|---|---|---|---|
| TBD | TBD | TBD | TBD |

## Known Risks

| Risk | Severity | Mitigation | Owner/Status |
|---|---|---|---|
| TBD | TBD | TBD | TBD |

## Open Questions

| Question | Why It Matters | How To Resolve |
|---|---|---|
| TBD | TBD | TBD |
```

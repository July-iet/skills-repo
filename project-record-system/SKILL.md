---
name: project-record-system
description: Initialize and maintain an agent-readable project record system for new or evolving repositories. Use when the user wants Codex or other agents to understand a new project, build or refresh repository documentation, create a stable docs/index system, initialize or update CodeGraph/project indexes, maintain AGENTS.md as a lightweight navigation file, or keep docs synchronized after code, architecture, workflow, route, storage, API, or shared utility changes.
---

# Project Record System

Use this skill to make a repository understandable to future agents. Treat the repo as the system of record: short navigation in `AGENTS.md`, durable knowledge in `docs/agent/`, and machine-verifiable indexes wherever the project supports them.

## Operating Principles

- Start by reading local project instructions, especially `AGENTS.md`, package/build files, route/module entry points, and existing docs.
- Keep `AGENTS.md` short. Use it as a map to the docs, not as the docs themselves.
- Store project knowledge in `docs/agent/` unless the project already has a clearly equivalent docs area.
- Prefer structural tools first: CodeGraph for symbols/call flows, `rg` for literal text, framework-native commands for generated indexes.
- Record facts that future agents cannot reliably infer from filenames: architecture boundaries, shared state, route/storage contracts, integration points, workflow steps, and known risks.
- Update docs during meaningful changes, not only after large rewrites.
- Preserve existing behavior. When a shared key, route, header, API contract, or utility behavior changes, record the producer, consumers, and compatibility decision.

## Modes

### Initialize

Use when entering a new project or when the repo lacks an agent-readable record system.

1. Read the nearest `AGENTS.md` files and existing docs.
2. Inspect project shape with CodeGraph when available; otherwise use `rg --files`, manifests, routes, and module entry points.
3. Identify the project type, major modules, shared state locations, APIs, storage keys, routes, build/test commands, and external integrations.
4. Initialize code indexing:
   - If `.codegraph/` exists, check index status and note stale files.
   - If `.codegraph/` is missing and the user explicitly asked to initialize indexing, follow local project rules for creating it.
   - If local instructions require confirmation before `codegraph init -i`, ask before running it.
5. Create or update the record system using `references/doc-system-template.md`.
6. Add or update `AGENTS.md` only with concise navigation, mandatory local rules, and links to `docs/agent/`.
7. Finish with a short table of files changed and a clear verification command or manual check.

### Update

Use after code changes, architecture changes, new modules, route/storage/API changes, dependency changes, or when the user asks agents to refresh project understanding.

1. Read the current `docs/agent/README.md` and relevant project files before editing docs.
2. Search both producers and consumers for changed shared behavior.
3. Update only the affected docs sections.
4. Refresh index/status entries: modules, routes, storage keys, commands, dependencies, open risks, and decision log.
5. Mark uncertain items as open questions instead of guessing.
6. Do a drift check: compare docs claims against source, manifests, routes, and public contracts touched by the task.
7. Report what changed, what remains uncertain, and how to verify.

## Record System Layout

Create the smallest useful set of files. Prefer these defaults:

- `docs/agent/README.md`: main index, project summary, navigation, last reviewed date.
- `docs/agent/project-map.md`: modules, entry points, ownership boundaries, important files.
- `docs/agent/runtime.md`: commands, environment, build/test conventions, generated artifacts.
- `docs/agent/contracts.md`: APIs, routes, storage keys, request headers, events, cross-project contracts.
- `docs/agent/workflows.md`: common user/system flows and where each flow enters code.
- `docs/agent/decisions.md`: durable decisions, tradeoffs, compatibility notes, known risks.

If the repo already has matching docs, reuse them and add a clear index rather than duplicating content.

## Documentation Rules

- Write compact docs that guide future agents to source files; do not paste large source excerpts.
- Include source paths and symbol names whenever possible.
- Prefer tables for indexes and contracts.
- Record verification status with dates and commands only when actually checked.
- Separate confirmed facts from assumptions.
- Keep stale or uncertain notes visible in `decisions.md` or an `Open Questions` section.
- Do not create reports, temporary files, or broad generated inventories unless the user asks for them.

## Templates

Read `references/doc-system-template.md` when creating a new record system or when a doc file needs a fresh section structure.

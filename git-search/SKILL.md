---
name: git-search
description: Search local Git repositories and produce a reusable structured commit summary JSON. Use when Codex needs to scan folders for commits by path, date range, month, author/committer keywords, branches, repository filters, or when downstream skills need normalized Git facts for performance reports, work-hour normalization, or other reporting workflows. Confirm missing or inferred scan parameters with the user before running the script.
---

# Skill: git-search

## Overview

Scan local Git repositories without changing their working trees and write a fixed-schema commit summary JSON. This skill is a data collection layer only.

## Boundaries

- Do not run `git fetch`, `git pull`, `git checkout`, or commands that change repositories.
- Do not generate performance prose or work-hour entries.
- Do not invent projects, branches, commit subjects, file counts, or code-line metrics.
- Keep API keys and secrets out of command lines, logs, output JSON, and reports.
- Do not run `scripts/git_search.py` until required inputs are explicit or the user has confirmed inferred values.

## Required Inputs and Confirmation Gate

Before running the script, identify these inputs:

- Repository roots: one or more `--root` folders to scan.
- Time range: either `--month` or both `--since` and `--before`. Resolve relative dates such as "today" to exact dates and timezone.
- Author filters: one or more `--author` keywords, unless the user explicitly asks for all authors.
- Output path: the `--output` JSON file path.

Also identify optional scope controls when relevant: `--recursive`, `--branch`, `--include-repo`, and `--exclude-repo`.

If any required input is missing, ask the user for it before using the skill. If you can infer a value from local context, previous messages, Git config, common workspace folders, or the current date, pause and confirm the full proposed query with the user before running the script. Include the exact roots, date range, author keywords, recursive setting, branch/repository filters, and output path in that confirmation.

Only skip confirmation when the user has already provided every required input explicitly in the current request or has explicitly approved the proposed query.

## Workflow

1. Extract explicit inputs from the user request.
2. Infer likely values only when helpful, then ask the user to confirm the complete query before running anything.
3. After confirmation, run `scripts/git_search.py`.
4. Use the generated JSON as input for `generate-report`, `normalize-work`, or other downstream skills.
5. If a repository fails a Git command, keep scanning other repositories and record the failure in `warnings`.

## Script Usage

```powershell
python C:\Users\dladmin\.agents\skills\git-search\scripts\git_search.py `
  --month 2026-05 `
  --root D:\Projects `
  --author 叶菁 --author yejing --author yejing@poweroak `
  --output D:\work\git_search_2026-05.json
```

Daily example:

```powershell
python C:\Users\dladmin\.agents\skills\git-search\scripts\git_search.py `
  --since 2026-06-04 `
  --before 2026-06-05 `
  --root D:\Projects `
  --author yejing `
  --output D:\work\git_search_2026-06-04.json
```

Useful options:

- `--root`: scan root. Repeat for multiple roots.
- `--month`: natural month in `YYYY-MM`.
- `--since` / `--before`: explicit left-closed, right-open range.
- `--author`: author or committer keyword. Repeat for multiple keywords.
- `--branch`: classified branch glob, for example `origin/develop` or `*feature*`.
- `--include-repo` / `--exclude-repo`: repository name globs.
- `--recursive`: find Git repositories recursively.
- `--output`: JSON output path.

## Output

See `references/git-search.schema.md`. Key fields are `query`, `totals`, `projectStats`, `branchStats`, `topicGroups`, `commits`, and `warnings`.

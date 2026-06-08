---
name: normalize-work
description: Normalize git-search commit summaries into work-hour diary entries for diary-helper. Use when Codex needs to turn local Git commits into project code, project name, work type, hours, content, review flags, and copyable JSON for importing into the PowerOak work-hour userscript.
---

# Skill: normalize-work

## Overview

Convert `git-search` JSON into work-hour entry candidates that `diary-helper` can import from the clipboard.

## Boundaries

- Do not scan Git; require `git-search` JSON as input.
- Do not submit work hours automatically.
- Do not invent project codes. Missing mappings must be marked `needsReview: true`.
- Keep the output compatible with `diary-helper` queue import.
- Keep generated `entries[*].hours` as numeric strings in 0.5-hour steps.
- Emit at most one `entries[*]` item per target work-hour project. When multiple commits or repositories map to the same project, merge their work content, sources, and hours into that single project entry.

## Workflow

1. Run `git-search` for the target day or time range.
2. Prepare or update a project mapping file. Start from `references/project-map.example.json`.
3. Run `scripts/normalize_work.py`.
4. Review entries with `needsReview: true` or missing project codes.
5. Copy the generated JSON and import it in the `diary-helper` panel.

## Hour Distribution Rules

- The default daily total is 8 hours. `--daily-hours` can override it, and `project-map.defaults.dailyHours` is a fallback when the CLI value is not set.
- Build exactly one work entry per mapped project. Repositories or commit groups that map to the same `projectCode` must stay merged and must not be split into multiple entries.
- A project's line weight is the sum of `insertions + deletions` from all its `git-search` commits.
- Distribute the daily total by each project's line-weight ratio, then round to the nearest 0.5 hour.
- Every emitted project entry must be at least 0.5 hour, and all emitted project entry hours must still add up to the daily total.
- If the constraints cannot both be true, fail loudly instead of inventing extra fallback hours.

Examples with the default 8-hour total:

- `XXXTBB-0126` has 100 changed lines and `SLP-048` has 700 changed lines: output `1` and `7`.
- `XXXTBB-0126` has 40 changed lines and `SLP-048` has 760 changed lines: output `0.5` and `7.5`.

## Script Usage

```powershell
python C:\Users\dladmin\.codex\skills\normalize-work\scripts\normalize_work.py `
  --input D:\work\git_search_2026-06-04.json `
  --project-map D:\work\project-map.json `
  --date 2026-06-04 `
  --daily-hours 8 `
  --output D:\work\work_entries_2026-06-04.json
```

## Import Flow

1. Open the target site's `添加日志` dialog.
2. Copy either the whole normalize-work JSON object or its `entries` array.
3. In the helper panel's `待填工时` section, click `从剪贴板导入`.
4. On an empty add-log dialog, the latest `diary-helper` script auto-applies the first queued entry; users can also click any queued entry manually.
5. Manually review and click the site's `确认`.
6. After confirmation, the script removes the filled queue entry.

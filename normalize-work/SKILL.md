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

## Workflow

1. Run `git-search` for the target day or time range.
2. Prepare or update a project mapping file. Start from `references/project-map.example.json`.
3. Run `scripts/normalize_work.py`.
4. Review entries with `needsReview: true` or missing project codes.
5. Copy the generated JSON and import it in the `diary-helper` panel.

## Script Usage

```powershell
python C:\Users\dladmin\.agents\skills\normalize-work\scripts\normalize_work.py `
  --input D:\work\git_search_2026-06-04.json `
  --project-map D:\work\project-map.json `
  --date 2026-06-04 `
  --daily-hours 8 `
  --output D:\work\work_entries_2026-06-04.json
```

## Import Flow

1. Open the target site's `添加日志` dialog.
2. In the helper panel, click `从剪贴板导入`.
3. Click an entry or `带入下一条`.
4. Manually review and click the site's `确认`.
5. After confirmation, the script removes the filled queue entry.

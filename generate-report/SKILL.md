---
name: generate-report
description: Generate performance-oriented Markdown reports from git-search JSON. Use when Codex needs to turn structured Git commit summaries into `git_stats.md`, monthly Git work summaries, factual summaries, KPI-oriented summaries, or materials for the performance workspace without re-scanning Git.
---

# Skill: generate-report

## Overview

Render a Markdown report from `git-search` JSON. This skill is the reporting layer; it does not scan Git repositories.

## Compatibility Goal

For `D:\Jing44\Code\performance`, output `git_stats.md` or `git_stats_N.md` under `data/months/{month}/input` so the backend can continue reading it as a material file.

## Workflow

1. Obtain a `git-search` JSON file.
2. Choose the output directory. For the performance workspace, prefer `D:\Jing44\Code\performance\data\months\{YYYY-MM}\input`.
3. Run `scripts/generate_report.py`.
4. Use the Markdown as performance input material or review it manually.

## Script Usage

```powershell
python C:\Users\dladmin\.agents\skills\generate-report\scripts\generate_report.py `
  --input D:\work\git_search_2026-05.json `
  --output-dir D:\Jing44\Code\performance\data\months\2026-05\input
```

Use AI only when explicitly requested:

```powershell
python C:\Users\dladmin\.agents\skills\generate-report\scripts\generate_report.py `
  --input D:\work\git_search_2026-05.json `
  --output-dir D:\Jing44\Code\performance\data\months\2026-05\input `
  --use-ai
```

## Rules

- Do not change numbers from `git-search` JSON.
- Do not invent business outcomes,上线结果, or user feedback.
- If `--use-ai` is set and the API key is missing, fail immediately.
- If `--use-ai` is not set, render a deterministic report from the JSON.

---
name: generate-git-report
description: 基于固定 Git 统计规则生成指定人员的月度工作 Markdown 报告。用于用户要求“汇总某人某月 Git 提交”“生成 Git 月报”“按 D:\\Projects 统计叶菁提交并输出 markdown”“总结 yejing@poweroak.net 的月度工作内容”等场景。优先复用本技能内置脚本、Prompt、Rules 和 Few-shot 样例，不重新设计统计口径。
---

# 技能：generate-git-report

## 概述

在固定搜索范围、固定作者匹配规则和固定统计规则下，扫描指定根目录中的 Git 仓库，汇总目标月份的提交记录，并生成包含提交明细、事实版总结、KPI 量化版总结和项目分布的 Markdown 月报。

本技能已自包含以下必要资源：

- `scripts/generate-monthly-report.ps1`
- `references/monthly-report.prompt.md`
- `references/monthly-report.rules.md`
- `references/monthly-report.examples.md`

## 快速判断

遇到以下需求时使用本技能：

- 生成指定人员某自然月的 Git 工作汇总
- 统计 `D:\Projects` 或其他固定目录下多个仓库的提交记录
- 按作者名、邮箱关键字筛选提交并输出 Markdown 月报
- 基于固定 Prompt / Rules / Few-shot 生成统一风格的工作总结

若用户只是查看现有月报内容，优先读取已有 `.md` 文件，不重新跑脚本。

## 工作流

按以下顺序执行：

1. 确认目标月份，格式必须为 `YYYY-MM`。
2. 确认扫描根目录、输出目录、作者关键字、是否启用 AI。
3. 优先复用本技能 `scripts/generate-monthly-report.ps1` 的现有参数和默认值。
4. 执行脚本，扫描根目录下一级 Git 仓库，排除 `auto-git`。
5. 让脚本基于 `--branches --remotes` 采集目标自然月的提交，并按 author/committer 关键字匹配目标人员。
6. 让脚本完成 commit 去重、主分支归类、文件数/新增行/删除行统计、主题归纳和项目聚合。
7. 若启用 AI，让脚本读取固定 Prompt、Rules、Few-shot 和统计 JSON，生成月报正文。
8. 输出 `git提交统计_YYYY-MM.md`，必要时再向用户摘录核心结论。

## 标准命令

在当前技能目录执行：

```powershell
.\scripts\generate-monthly-report.ps1 -Month "2026-05"
```

常见扩展参数：

```powershell
.\scripts\generate-monthly-report.ps1 `
  -Month "2026-05" `
  -RootPath "D:\Projects" `
  -OutputDir "." `
  -AuthorKeywords "叶菁", "yejing", "yejing@poweroak.net" `
  -UseAI:$true `
  -BaseUrl "https://api.deepseek.com" `
  -Model "deepseek-v4-pro" `
  -ApiKeyEnv "DEEPSEEK_API_KEY"
```

仅验证 Git 采集和统计流程时，关闭 AI：

```powershell
.\scripts\generate-monthly-report.ps1 -Month "2026-05" -UseAI:$false
```

## 输入

### 必填输入

- `Month`：目标月份，格式 `YYYY-MM`

### 可选输入

- `RootPath`：扫描根目录，默认 `D:\Projects`
- `OutputDir`：输出目录，默认 skill 根目录
- `AuthorKeywords`：作者关键字数组
- `UseAI`：是否启用 AI，默认开启
- `BaseUrl`：AI 接口地址
- `Model`：AI 模型名
- `ApiKeyEnv`：API Key 环境变量名，默认 `DEEPSEEK_API_KEY`

### 默认作者关键字

- `叶菁`
- `yejing`
- `yejing@poweroak`
- `310100519`
- `G310100519`

### 依赖输入

- 本地 Git 仓库数据
- 环境变量 `DEEPSEEK_API_KEY`
- 固定参考文件：
  - `references/monthly-report.prompt.md`
  - `references/monthly-report.rules.md`
  - `references/monthly-report.examples.md`

## 输出

主输出文件：

- `git提交统计_YYYY-MM.md`

输出结构固定为：

```markdown
# {YYYY} 年 {M} 月 Git 工作汇总

## 统计说明

## 第一部分：提交明细

## 第二部分：当月工作内容总结

### 事实版总结

### KPI 量化版总结

## 项目分布
```

不要对外输出大段中间 JSON。若用户需要解释统计来源，再摘要说明 `totals`、`project_stats`、`branch_stats`、`topic_groups`、`commit_items` 等字段用途。

## 统计口径

- 统计粒度是自然月，时间范围左闭右开
- 遍历本地分支和远程分支，即 `--branches --remotes`
- 同一项目内同一 commit 只统计一次
- 同一 commit 只归入一个主分支，优先远程分支，其次本地分支，最后默认分支兜底
- AI 只负责归纳文本，不负责改写统计值
- 输出中的提交次数、项目数、文件数、新增行数、删除行数必须直接使用脚本统计结果

## 错误处理

- 月份格式不合法：立即失败
- 根目录不存在或不可读：立即失败
- 某个仓库 Git 命令失败：跳过该仓库，继续处理其他仓库
- 缺少 API Key 且启用 AI：立即失败，只提示缺少环境变量，不输出 key
- AI 请求失败：立即失败，不伪造总结内容
- 关闭 AI：允许输出占位版 Markdown

## 限制

- 不执行 `git fetch --all`、`git pull`、`git checkout` 等会改动仓库状态的命令
- 不新增 Git 数据中不存在的项目、分支、需求、模块、结果或业务价值
- 不改写脚本已经统计出的数字
- 不在配置、日志、Prompt 或输出文档中写入 API Key、Token、密码等敏感信息
- 默认只扫描根目录下一级 Git 仓库；若需要递归扫描，先确认再改规则

## 参考文件

需要核对真实行为时，按以下顺序读取：

1. `scripts/generate-monthly-report.ps1`
2. `references/monthly-report.rules.md`
3. `references/monthly-report.prompt.md`
4. `references/monthly-report.examples.md`

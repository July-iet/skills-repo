import argparse
import json
import os
import urllib.request
from collections import defaultdict
from datetime import datetime
from pathlib import Path


def args():
    p = argparse.ArgumentParser(description="Generate Markdown report from git-search JSON.")
    p.add_argument("--input", required=True)
    p.add_argument("--output-dir", default=".")
    p.add_argument("--output-name", default="")
    p.add_argument("--use-ai", action="store_true")
    p.add_argument("--base-url", default="https://api.deepseek.com")
    p.add_argument("--model", default="deepseek-v4-pro")
    p.add_argument("--api-key-env", default="DEEPSEEK_API_KEY")
    return p.parse_args()


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def out_path(output_dir, output_name):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    if output_name:
        return output_dir / output_name
    i = 0
    while True:
        name = "git_stats.md" if i == 0 else f"git_stats_{i}.md"
        path = output_dir / name
        if not path.exists():
            return path
        i += 1


def label(data):
    query = data.get("query", {})
    return query.get("month") or query.get("since", "")[:7] or datetime.now().strftime("%Y-%m")


def esc(value):
    return str(value or "").replace("|", "\\|").replace("\r", " ").replace("\n", " ").strip()


def body(data):
    grouped = defaultdict(lambda: defaultdict(list))
    for item in data.get("commits", []):
        grouped[item.get("repo", "")][item.get("branch", "未识别分支")].append(item)
    lines = ["## 第一部分：提交明细", ""]
    for repo in sorted(grouped):
        lines += [f"### 项目：{repo}", ""]
        for branch in sorted(grouped[repo]):
            items = grouped[repo][branch]
            lines += [
                f"#### 分支：{branch}", "",
                "| Commit | 提交时间 | 提交信息 | 提交内容总结 |",
                "| --- | --- | --- | --- |",
            ]
            for item in items:
                lines.append(f"| `{item.get('shortHash', '')}` | {esc(item.get('commitTime'))} | {esc(item.get('subject'))} | {esc(item.get('summary'))} |")
            topics = "、".join(sorted({item.get("topic", "功能开发与细节优化") for item in items})[:4])
            lines += ["", f"本阶段主要在 `{branch}` 分支处理{topics}。", ""]
    totals = data.get("totals", {})
    projects = "、".join(i.get("repo", "") for i in data.get("projectStats", [])[:3]) or "相关项目"
    topics = "、".join(i.get("topic", "") for i in data.get("topicGroups", [])[:5]) or "功能开发与细节优化"
    total_lines = int(totals.get("insertions") or 0) + int(totals.get("deletions") or 0)
    lines += [
        "## 第二部分：当月工作内容总结", "",
        "### 事实版总结", "",
        f"{label(data)} 期间共在 {totals.get('repos', 0)} 个项目完成 {totals.get('commits', 0)} 次提交，工作重心集中在 {projects}。主要产出包括{topics}。", "",
        "### KPI 量化版总结", "",
        f"按交付量化，本次统计覆盖 {totals.get('repos', 0)} 个项目、{totals.get('commits', 0)} 次提交，累计触达 {totals.get('fileChanges', 0)} 次文件改动，覆盖 {totals.get('uniqueFiles', 0)} 个唯一文件，代码变更 {total_lines} 行（新增 {totals.get('insertions', 0)} / 删除 {totals.get('deletions', 0)}）。",
    ]
    return "\n".join(lines).rstrip() + "\n"


def ai_body(data, base_url, model, key_env):
    key = os.getenv(key_env)
    if not key:
        raise SystemExit(f"missing environment variable: {key_env}")
    skill = Path(__file__).resolve().parent.parent
    prompt = (skill / "references" / "monthly-report.prompt.md").read_text(encoding="utf-8")
    rules = (skill / "references" / "monthly-report.rules.md").read_text(encoding="utf-8")
    examples = (skill / "references" / "monthly-report.examples.md").read_text(encoding="utf-8")
    payload = json.dumps({
        "model": model,
        "temperature": 0.2,
        "messages": [
            {"role": "system", "content": "你必须严格遵守固定 Prompt、Rules 和 Few-shot 样例，只基于输入 JSON 生成 Markdown。"},
            {"role": "user", "content": f"以下是固定 Prompt：\n{prompt}\n\n以下是 Rules：\n{rules}\n\n以下是 Few-shot 样例：\n{examples}\n\n以下是本次 Git 统计 JSON：\n{json.dumps(data, ensure_ascii=False)}"},
        ],
    }, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        base_url.rstrip("/") + "/chat/completions",
        data=payload,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        result = json.loads(resp.read().decode("utf-8"))
    return result["choices"][0]["message"]["content"].strip() + "\n"


def header(data):
    m = label(data)
    try:
        dt = datetime.strptime(m + "-01", "%Y-%m-%d")
        title = f"# {dt.year} 年 {dt.month} 月 Git 工作汇总"
    except ValueError:
        title = f"# {m} Git 工作汇总"
    q = data.get("query", {})
    t = data.get("totals", {})
    return "\n".join([
        title, "", "## 统计说明", "",
        f"- 统计范围：`{'; '.join(q.get('roots') or [])}`，遍历 `{q.get('refScope', '--branches --remotes')}`。",
        f"- 统计时间：`{q.get('since', '')}` 至 `{q.get('before', '')}`。",
        f"- 作者匹配：`{' / '.join(q.get('authorKeywords') or [])}`。",
        f"- 结果概览：共命中 `{t.get('commits', 0)}` 次提交，覆盖 `{t.get('repos', 0)}` 个项目；新增 `{t.get('insertions', 0)}` 行，删除 `{t.get('deletions', 0)}` 行，涉及 `{t.get('uniqueFiles', 0)}` 个唯一文件。",
        "",
    ])


def distribution(data):
    lines = ["## 项目分布", "", "| 项目 | 提交次数 | 新增行数 | 删除行数 |", "| --- | ---: | ---: | ---: |"]
    for stat in data.get("projectStats", []):
        lines.append(f"| {esc(stat.get('repo'))} | {stat.get('commits', 0)} | {stat.get('insertions', 0)} | {stat.get('deletions', 0)} |")
    return "\n".join(lines) + "\n"


def main():
    a = args()
    data = load(a.input)
    report_body = ai_body(data, a.base_url, a.model, a.api_key_env) if a.use_ai else body(data)
    report = header(data) + report_body.rstrip() + "\n\n" + distribution(data)
    path = out_path(a.output_dir, a.output_name)
    path.write_text(report, encoding="utf-8")
    print(f"Report generated: {path}")


if __name__ == "__main__":
    main()

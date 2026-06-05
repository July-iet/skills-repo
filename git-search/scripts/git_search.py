import argparse
import fnmatch
import json
import subprocess
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

DEFAULT_AUTHORS = ["叶菁", "yejing", "yejing@poweroak", "310100519", "G310100519"]
DEFAULT_EXCLUDE_REPOS = ["auto-git"]
UTC8 = timezone(timedelta(hours=8))


def parse_args():
    parser = argparse.ArgumentParser(description="Search local Git repositories and output commit summary JSON.")
    parser.add_argument("--root", action="append", default=[])
    parser.add_argument("--month")
    parser.add_argument("--since")
    parser.add_argument("--before")
    parser.add_argument("--author", action="append", default=[])
    parser.add_argument("--branch", action="append", default=[])
    parser.add_argument("--include-repo", action="append", default=[])
    parser.add_argument("--exclude-repo", action="append", default=[])
    parser.add_argument("--recursive", action="store_true")
    parser.add_argument("--output", default="git_search.json")
    return parser.parse_args()


def parse_dt(value):
    text = str(value).strip()
    if len(text) == 10:
        return datetime.fromisoformat(text)
    return datetime.fromisoformat(text.replace("Z", "+00:00"))


def month_range(month):
    start = datetime.strptime(month + "-01", "%Y-%m-%d")
    year = start.year + (1 if start.month == 12 else 0)
    month = 1 if start.month == 12 else start.month + 1
    return start, datetime(year, month, 1)


def resolve_range(args):
    if args.month:
        if args.since or args.before:
            raise SystemExit("Use either --month or --since/--before.")
        return month_range(args.month)
    if not args.since or not args.before:
        raise SystemExit("Provide --month or both --since and --before.")
    return parse_dt(args.since), parse_dt(args.before)


def run_git(repo, args):
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or f"git exited {result.returncode}")
    return result.stdout.splitlines()


def matches_any(value, patterns):
    return not patterns or any(fnmatch.fnmatchcase(value, pattern) for pattern in patterns)


def find_repos(root, recursive, includes, excludes):
    root = Path(root).expanduser().resolve()
    if not root.exists():
        raise FileNotFoundError(str(root))
    if (root / ".git").exists():
        candidates = [root]
    elif recursive:
        candidates = [p.parent for p in root.rglob(".git") if p.is_dir()]
    else:
        candidates = [p for p in root.iterdir() if p.is_dir() and (p / ".git").exists()]
    repos = []
    for repo in candidates:
        if any(fnmatch.fnmatchcase(repo.name, pattern) for pattern in excludes):
            continue
        if not matches_any(repo.name, includes):
            continue
        repos.append(repo)
    return sorted(set(repos), key=lambda p: p.name.lower())


def author_matched(values, keywords):
    values = [str(value or "").lower() for value in values]
    return any(keyword.lower() in value for keyword in keywords for value in values)


def format_commit_time(value):
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC8)
    parsed = parsed.astimezone(UTC8)
    return parsed.strftime("%Y-%m-%d %H:%M:%S %z")[:-2] + ":" + parsed.strftime("%z")[-2:]


def commit_stats(repo, commit_hash):
    lines = run_git(repo, ["show", "--numstat", "--format=", "--no-renames", commit_hash])
    file_count = 0
    insertions = 0
    deletions = 0
    paths = []
    for line in lines:
        if not line.strip():
            continue
        parts = line.split("\t")
        if len(parts) < 3:
            continue
        file_count += 1
        if parts[0].isdigit():
            insertions += int(parts[0])
        if parts[1].isdigit():
            deletions += int(parts[1])
        paths.append(parts[2])
    return file_count, insertions, deletions, paths


def commit_branch(repo, commit_hash):
    try:
        refs = run_git(repo, ["branch", "--all", "--contains", commit_hash, "--format=%(refname)"])
    except RuntimeError:
        refs = []
    remotes = []
    locals_ = []
    for ref in refs:
        if ref.startswith("refs/remotes/") and not ref.endswith("/HEAD"):
            remotes.append(ref.removeprefix("refs/remotes/"))
        elif ref.startswith("refs/heads/"):
            locals_.append(ref.removeprefix("refs/heads/"))
    if remotes:
        return sorted(remotes)[0]
    if locals_:
        return sorted(locals_)[0]
    for branch in ["origin/develop", "origin/master", "origin/main", "develop", "master", "main"]:
        try:
            run_git(repo, ["rev-parse", "--verify", branch])
            return branch
        except RuntimeError:
            pass
    return "未识别分支"


def commit_topic(subject, paths):
    text = (subject + " " + " ".join(paths)).lower()
    if subject.lower().startswith("merge"):
        return "分支合并与代码同步"
    rules = [
        ("打包|发版|发布|dist|build", "版本打包与环境发布处理"),
        ("fix|修复|bug|报错|问题", "缺陷修复与稳定性处理"),
        ("国际化|i18n|文案|locale|locales", "国际化文案与界面展示优化"),
        ("权限|隐藏|字段|可见", "字段权限与页面可见性收敛"),
        ("订单审核|审批|拒绝原因", "订单审核流程与审批交互完善"),
        ("订单|支付|库存|客户", "订单模块字段、详情与交易信息完善"),
        ("流程|看板|待办|任务|需求", "流程配置与流程看板能力增强"),
        ("附件|下载|视频|icon|图标", "附件与下载链路优化"),
        ("样式|布局|弹窗|按钮|交互", "页面布局与交互优化"),
        ("发票|netsuite|sku|msku", "NetSuite 脚本与业务规则调整"),
    ]
    for pattern, topic in rules:
        if any(token in text for token in pattern.split("|")):
            return topic
    return "功能开发与细节优化"


def collect(repo, start, end, authors, branch_patterns, warnings):
    fmt = "%H%x1f%aI%x1f%an%x1f%ae%x1f%cn%x1f%ce%x1f%s"
    try:
        lines = run_git(repo, [
            "log", "--branches", "--remotes",
            f"--since={start:%Y-%m-%d %H:%M:%S}",
            f"--before={end:%Y-%m-%d %H:%M:%S}",
            f"--format={fmt}",
        ])
    except RuntimeError as exc:
        warnings.append({"repo": repo.name, "repoPath": str(repo), "message": str(exc)})
        return []
    out = []
    seen = set()
    for line in lines:
        parts = line.split("\x1f")
        if len(parts) < 7:
            continue
        h, dt, an, ae, cn, ce, subject = parts[:7]
        if h in seen:
            continue
        seen.add(h)
        if not author_matched([an, ae, cn, ce], authors):
            continue
        try:
            file_count, ins, dels, paths = commit_stats(repo, h)
            branch = commit_branch(repo, h)
        except RuntimeError as exc:
            warnings.append({"repo": repo.name, "repoPath": str(repo), "hash": h, "message": str(exc)})
            continue
        if branch_patterns and not matches_any(branch, branch_patterns):
            continue
        topic = commit_topic(subject, paths)
        commit_time = format_commit_time(dt)
        out.append({
            "repo": repo.name,
            "repoPath": str(repo),
            "branch": branch,
            "hash": h,
            "shortHash": h[:8],
            "commitTime": commit_time,
            "commitDate": commit_time[:10],
            "authorName": an,
            "authorEmail": ae,
            "committerName": cn,
            "committerEmail": ce,
            "subject": subject,
            "fileCount": file_count,
            "insertions": ins,
            "deletions": dels,
            "paths": paths,
            "topic": topic,
            "summary": f"{topic}（涉及 {file_count} 个文件，+{ins}/-{dels}）",
        })
    return out


def stats(commits):
    by_repo = defaultdict(list)
    by_branch = defaultdict(list)
    by_topic = defaultdict(list)
    for item in commits:
        by_repo[item["repo"]].append(item)
        by_branch[(item["repo"], item["branch"])].append(item)
        by_topic[item["topic"]].append(item)
    project_stats = [{
        "repo": repo,
        "commits": len(items),
        "insertions": sum(i["insertions"] for i in items),
        "deletions": sum(i["deletions"] for i in items),
        "fileChanges": sum(i["fileCount"] for i in items),
        "uniqueFiles": len({p for i in items for p in i["paths"]}),
        "activeDays": len({i["commitDate"] for i in items}),
    } for repo, items in by_repo.items()]
    branch_stats = [{
        "repo": repo,
        "branch": branch,
        "commits": len(items),
        "insertions": sum(i["insertions"] for i in items),
        "deletions": sum(i["deletions"] for i in items),
    } for (repo, branch), items in by_branch.items()]
    topic_groups = [{
        "topic": topic,
        "commits": len(items),
        "repos": sorted({i["repo"] for i in items}),
    } for topic, items in by_topic.items()]
    project_stats.sort(key=lambda i: (-i["commits"], i["repo"]))
    branch_stats.sort(key=lambda i: (i["repo"], i["branch"]))
    topic_groups.sort(key=lambda i: (-i["commits"], i["topic"]))
    totals = {
        "commits": len(commits),
        "repos": len(by_repo),
        "activeDays": len({i["commitDate"] for i in commits}),
        "fileChanges": sum(i["fileCount"] for i in commits),
        "uniqueFiles": len({p for i in commits for p in i["paths"]}),
        "insertions": sum(i["insertions"] for i in commits),
        "deletions": sum(i["deletions"] for i in commits),
    }
    return totals, project_stats, branch_stats, topic_groups


def main():
    args = parse_args()
    roots = args.root or [r"D:\Projects"]
    start, end = resolve_range(args)
    authors = args.author or DEFAULT_AUTHORS
    excludes = DEFAULT_EXCLUDE_REPOS + args.exclude_repo
    warnings = []
    repos = []
    for root in roots:
        try:
            repos.extend(find_repos(root, args.recursive, args.include_repo, excludes))
        except Exception as exc:
            warnings.append({"root": root, "message": str(exc)})
    commits = []
    for repo in sorted(set(repos), key=lambda p: str(p).lower()):
        print(f"Scanning {repo.name}...")
        commits.extend(collect(repo, start, end, authors, args.branch, warnings))
    commits.sort(key=lambda i: (i["repo"], i["branch"], i["commitTime"], i["hash"]))
    totals, project_stats, branch_stats, topic_groups = stats(commits)
    output = {
        "schemaVersion": 1,
        "generatedAt": datetime.now(UTC8).isoformat(timespec="seconds"),
        "query": {
            "roots": roots,
            "recursive": args.recursive,
            "since": start.strftime("%Y-%m-%d %H:%M:%S"),
            "before": end.strftime("%Y-%m-%d %H:%M:%S"),
            "month": args.month or "",
            "authorKeywords": authors,
            "branches": args.branch,
            "includeRepos": args.include_repo,
            "excludeRepos": excludes,
            "refScope": "--branches --remotes",
        },
        "totals": totals,
        "projectStats": project_stats,
        "branchStats": branch_stats,
        "topicGroups": topic_groups,
        "commits": commits,
        "warnings": warnings,
    }
    path = Path(args.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Git search generated: {path}")


if __name__ == "__main__":
    main()

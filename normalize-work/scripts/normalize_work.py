import argparse
import json
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

UTC8 = timezone(timedelta(hours=8))


def args():
    p = argparse.ArgumentParser(description="Normalize git-search JSON into work-hour diary entries.")
    p.add_argument("--input", required=True)
    p.add_argument("--project-map", required=True)
    p.add_argument("--date", default="")
    p.add_argument("--daily-hours", type=float, default=8.0)
    p.add_argument("--work-type", default="")
    p.add_argument("--output", default="work_entries.json")
    return p.parse_args()


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def text(value):
    return str(value or "").replace("\r", " ").replace("\n", " ").strip()


def fmt_hours(value):
    rounded = max(0.5, round(value * 2) / 2)
    return str(int(rounded)) if rounded.is_integer() else f"{rounded:.1f}"


def distribute(groups, daily_hours):
    if not groups:
        return {}
    weights = {key: max(1, len(items)) for key, items in groups.items()}
    total = sum(weights.values())
    hours = {key: max(0.5, round((daily_hours * weight / total) * 2) / 2) for key, weight in weights.items()}
    diff = round((daily_hours - sum(hours.values())) * 2) / 2
    ordered = sorted(hours, key=lambda key: (-weights[key], str(key)))
    while abs(diff) >= 0.5 and ordered:
        step = 0.5 if diff > 0 else -0.5
        for key in ordered:
            if hours[key] + step <= 0:
                continue
            hours[key] += step
            diff = round((diff - step) * 2) / 2
            if abs(diff) < 0.5:
                break
    return hours


def content(topic, commits):
    subjects = []
    for item in commits:
        subject = text(item.get("subject"))
        if subject and subject not in subjects:
            subjects.append(subject)
    if subjects:
        return f"{topic}：{'；'.join(subjects[:3])}"
    return topic or "处理相关开发工作"


def infer_date(commits, explicit):
    if explicit:
        return explicit
    dates = sorted({text(item.get("commitDate")) for item in commits if item.get("commitDate")})
    return dates[0] if dates else datetime.now(UTC8).date().isoformat()


def main():
    a = args()
    git_data = load(a.input)
    project_map = load(a.project_map)
    commits = git_data.get("commits", [])
    defaults = project_map.get("defaults", {})
    projects = project_map.get("projects", {})
    work_type = a.work_type or defaults.get("workType") or "正常"
    daily_hours = a.daily_hours or defaults.get("dailyHours") or 8
    groups = defaultdict(list)
    for item in commits:
        groups[(item.get("repo", ""), item.get("topic", "功能开发与细节优化"))].append(item)
    hours = distribute(groups, daily_hours)
    entries = []
    review = []
    for (repo, topic), items in sorted(groups.items(), key=lambda pair: (pair[0][0], pair[0][1])):
        mapping = projects.get(repo, {})
        project_code = text(mapping.get("projectCode") or defaults.get("unknownProjectCode") or "")
        entry = {
            "projectCode": project_code,
            "projectName": text(mapping.get("projectName") or repo),
            "workType": work_type,
            "hours": fmt_hours(hours.get((repo, topic), 0.5)),
            "content": content(topic, items),
            "needsReview": not bool(project_code),
            "sources": [f"{item.get('repo')} {item.get('shortHash')}" for item in items],
        }
        if entry["needsReview"]:
            entry["reviewReason"] = f"missing project mapping for repo: {repo}"
            review.append(entry)
        else:
            entries.append(entry)
    output = {
        "schemaVersion": 1,
        "generatedAt": datetime.now(UTC8).isoformat(timespec="seconds"),
        "date": infer_date(commits, a.date),
        "source": {"gitSearchInput": str(Path(a.input)), "commitCount": len(commits)},
        "entries": entries,
        "review": review,
    }
    path = Path(a.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Work entries generated: {path}")
    print(f"valid entries: {len(entries)}")
    print(f"review entries: {len(review)}")


if __name__ == "__main__":
    main()

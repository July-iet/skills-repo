import argparse
import json
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from math import floor
from pathlib import Path

UTC8 = timezone(timedelta(hours=8))
HOUR_STEP = 0.5


def args():
    p = argparse.ArgumentParser(description="Normalize git-search JSON into work-hour diary entries.")
    p.add_argument("--input", required=True)
    p.add_argument("--project-map", required=True)
    p.add_argument("--date", default="")
    p.add_argument("--daily-hours", type=float, default=None)
    p.add_argument("--work-type", default="")
    p.add_argument("--output", default="work_entries.json")
    return p.parse_args()


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def text(value):
    return str(value or "").replace("\r", " ").replace("\n", " ").strip()


def fmt_hours(value):
    rounded = max(HOUR_STEP, round(value / HOUR_STEP) * HOUR_STEP)
    return str(int(rounded)) if rounded.is_integer() else f"{rounded:.1f}"


def number(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0


def changed_lines(commit):
    return max(0, int(number(commit.get("insertions")) + number(commit.get("deletions"))))


def distribute(groups, daily_hours):
    if not groups:
        return {}
    total_units = daily_hours / HOUR_STEP
    if total_units != round(total_units):
        raise ValueError(f"daily-hours must be divisible by {HOUR_STEP}: {daily_hours}")
    total_units = int(round(total_units))
    if len(groups) > total_units:
        raise ValueError(f"too many project entries for {daily_hours} hours at {HOUR_STEP}h minimum step")
    weights = {key: sum(changed_lines(item) for item in items) for key, items in groups.items()}
    total_weight = sum(weights.values())
    if total_weight <= 0:
        raise ValueError("git-search input has no changed lines to distribute hours")

    raw_units = {key: total_units * weight / total_weight for key, weight in weights.items()}
    units = {key: max(1, int(floor(raw_units[key] + 0.5))) for key in groups}
    diff = total_units - sum(units.values())
    while diff:
        if diff > 0:
            ordered = sorted(groups, key=lambda key: (raw_units[key] - units[key], weights[key], str(key)), reverse=True)
            units[ordered[0]] += 1
            diff -= 1
            continue
        ordered = [key for key in sorted(groups, key=lambda key: (raw_units[key] - units[key], -weights[key], str(key))) if units[key] > 1]
        if not ordered:
            raise ValueError(f"cannot keep total hours at {daily_hours} with {HOUR_STEP}h minimum step")
        units[ordered[0]] -= 1
        diff += 1
    return {key: unit_count * HOUR_STEP for key, unit_count in units.items()}


def content(topic, commits):
    subjects = []
    for item in commits:
        subject = text(item.get("subject"))
        if subject and subject not in subjects:
            subjects.append(subject)
    if subjects:
        return f"{topic}：{'；'.join(subjects[:3])}"
    return topic or "处理相关开发工作"


def project_group_key(repo, mapping):
    project_code = text(mapping.get("projectCode"))
    project_name = text(mapping.get("projectName") or repo)
    return (project_code or f"__missing__:{repo}", project_code, project_name)


def group_topic(commits):
    topics = []
    for item in commits:
        topic = text(item.get("topic") or "功能开发与细节优化")
        if topic and topic not in topics:
            topics.append(topic)
    return "；".join(topics[:3]) or "功能开发与细节优化"


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
    daily_hours = a.daily_hours if a.daily_hours is not None else (number(defaults.get("dailyHours")) or 8)
    groups = defaultdict(list)
    group_meta = {}
    for item in commits:
        repo = item.get("repo", "")
        mapping = projects.get(repo, {})
        key = project_group_key(repo, mapping)
        groups[key].append(item)
        group_meta[key] = {
            "projectCode": key[1],
            "projectName": key[2],
            "missingRepos": sorted({entry.get("repo", "") for entry in groups[key] if not projects.get(entry.get("repo", ""), {}).get("projectCode")}),
        }
    hours = distribute(groups, daily_hours)
    entries = []
    review = []
    for key, items in sorted(groups.items(), key=lambda pair: (pair[0][1] or pair[0][0], pair[0][2])):
        meta = group_meta[key]
        project_code = text(meta["projectCode"] or defaults.get("unknownProjectCode") or "")
        topic = group_topic(items)
        entry = {
            "projectCode": project_code,
            "projectName": meta["projectName"],
            "workType": work_type,
            "hours": fmt_hours(hours.get(key, HOUR_STEP)),
            "content": content(topic, items),
            "needsReview": not bool(project_code),
            "sources": [f"{item.get('repo')} {item.get('shortHash')}" for item in items],
        }
        if entry["needsReview"]:
            entry["reviewReason"] = f"missing project mapping for repo: {', '.join(meta['missingRepos'])}"
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

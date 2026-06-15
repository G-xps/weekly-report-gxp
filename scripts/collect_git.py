#!/usr/bin/env python3
"""Collect git commits for a weekly report."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from datetime import date, datetime, timedelta
from pathlib import Path

from member_utils import load_members, resolve_member


TYPE_ALIASES = {
    "feat": "feat",
    "新增": "feat",
    "fix": "fix",
    "bug": "fix",
    "修复": "fix",
    "docs": "docs",
    "文档": "docs",
    "style": "style",
    "代码": "style",
    "refactor": "refactor",
    "重构": "refactor",
    "perf": "perf",
    "优化": "perf",
    "test": "test",
    "测试": "test",
    "chore": "chore",
    "运维": "chore",
    "build": "build",
    "构建": "build",
    "ci": "ci",
    "ci/cd": "ci",
}

COMMIT_RE = re.compile(
    r"^("
    + "|".join(re.escape(key) for key in sorted(TYPE_ALIASES, key=len, reverse=True))
    + r")(\(.+\))?\s*[:：]\s*",
    re.I,
)


def default_period() -> tuple[str, str]:
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    sunday = monday + timedelta(days=6)
    return monday.isoformat(), sunday.isoformat()


def classify(message: str) -> tuple[str, str]:
    match = COMMIT_RE.match(message)
    raw_type = match.group(1).lower() if match else ""
    commit_type = TYPE_ALIASES.get(raw_type, "other")
    title = COMMIT_RE.sub("", message).strip() or message.strip()
    return commit_type, title


def run_git_log(project_dir: Path, start: str, end: str) -> list[str]:
    if not (project_dir / ".git").exists():
        return []
    cmd = [
        "git",
        "-C",
        str(project_dir),
        "log",
        f"--since={start} 00:00:00",
        f"--until={end} 23:59:59",
        "--no-merges",
        "--pretty=format:%H%x1f%an%x1f%ae%x1f%ad%x1f%s",
        "--date=short",
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        return []
    return [line for line in result.stdout.splitlines() if line.strip()]


def collect(project_dir: Path, start: str, end: str, members_path: str | None) -> dict:
    members = load_members(members_path)
    commits = []
    for line in run_git_log(project_dir, start, end):
        parts = line.split("\x1f", 4)
        if len(parts) != 5:
            continue
        commit_hash, author, email, commit_date, message = parts
        commit_type, title = classify(message)
        member = resolve_member(email, members)
        if member == email:
            member = resolve_member(author, members)
        commits.append(
            {
                "hash": commit_hash[:8],
                "author": author,
                "email": email,
                "member": member or author,
                "date": commit_date,
                "type": commit_type,
                "title": title,
                "message": message,
            }
        )
    contributors = sorted({item["member"] for item in commits if item.get("member")})
    by_member = {
        member: {
            "commits": len([item for item in commits if item["member"] == member]),
            "features": len([item for item in commits if item["member"] == member and item["type"] == "feat"]),
            "fixes": len([item for item in commits if item["member"] == member and item["type"] == "fix"]),
        }
        for member in contributors
    }
    return {
        "period": {"start": start, "end": end},
        "commits": commits,
        "stats": {"total_commits": len(commits), "contributors": len(contributors)},
        "by_member": by_member,
    }


def main() -> None:
    start_default, end_default = default_period()
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-dir", default=".")
    parser.add_argument("--start", default=start_default)
    parser.add_argument("--end", default=end_default)
    parser.add_argument("--members-json")
    args = parser.parse_args()
    data = collect(Path(args.project_dir), args.start, args.end, args.members_json)
    print(json.dumps(data, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

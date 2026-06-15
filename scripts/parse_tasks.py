#!/usr/bin/env python3
"""Parse todo and issue files for weekly report tasks."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from member_utils import find_member_mentions, load_members, resolve_member


STATUS_HEADINGS = [
    ("completed", re.compile(r"#+\s*(已完成|完成|done|completed)", re.I)),
    ("in_progress", re.compile(r"#+\s*(进行中|处理中|in progress|processing|doing)", re.I)),
    ("pending", re.compile(r"#+\s*(待办|计划|todo|pending|plan)", re.I)),
]


def detect_owner(text: str, members: dict) -> str:
    owner_match = re.search(r"(负责人|owner|assignee)\s*[:：]\s*([@\w\u4e00-\u9fff.-]+)", text, re.I)
    if owner_match:
        return resolve_member(owner_match.group(2), members)
    mentions = find_member_mentions(text, members)
    return mentions[0] if mentions else ""


def clean_title(text: str) -> str:
    text = re.sub(r"(负责人|owner|assignee)\s*[:：]\s*[@\w\u4e00-\u9fff.-]+", "", text, flags=re.I)
    text = re.sub(r"@[\w\u4e00-\u9fff.-]+", "", text)
    return text.strip(" -:：")


def parse_markdown_file(path: Path, members: dict) -> list[dict]:
    status = "pending"
    tasks: list[dict] = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        for candidate, pattern in STATUS_HEADINGS:
            if pattern.match(line):
                status = candidate
                break
        match = re.match(r"^[-*]\s*\[([ xX~-])\]\s*(.+)$", line)
        if not match:
            continue
        marker, title = match.groups()
        item_status = "completed" if marker.lower() == "x" else status
        owner = detect_owner(title, members)
        tasks.append(
            {
                "title": clean_title(title),
                "owner": owner,
                "status": item_status,
                "source": str(path),
            }
        )
    return tasks


def parse_tasks_json(path: Path, members: dict) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    items = data.get("tasks", data if isinstance(data, list) else [])
    tasks: list[dict] = []
    for item in items:
        title = str(item.get("title", "")).strip()
        if not title:
            continue
        owner = resolve_member(item.get("owner") or item.get("assignee"), members)
        tasks.append(
            {
                "title": title,
                "owner": owner,
                "status": item.get("status", "pending"),
                "source": str(path),
            }
        )
    return tasks


def find_task_files(project_dir: Path) -> list[Path]:
    names = ["todo.md", "TODO.md", "issues.md", "ISSUES.md", "tasks.json"]
    files: list[Path] = []
    seen: set[str] = set()
    for name in names:
        path = project_dir / name
        if not path.exists():
            continue
        key = str(path.resolve()).lower()
        if key in seen:
            continue
        seen.add(key)
        files.append(path)
    return files


def parse(project_dir: Path, members_path: str | None) -> dict:
    members = load_members(members_path)
    tasks: list[dict] = []
    for path in find_task_files(project_dir):
        if path.suffix.lower() == ".json":
            tasks.extend(parse_tasks_json(path, members))
        else:
            tasks.extend(parse_markdown_file(path, members))
    grouped = {"completed": [], "in_progress": [], "pending": []}
    for task in tasks:
        grouped.setdefault(task["status"], []).append(task)
    return {"tasks": tasks, **grouped}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-dir", default=".")
    parser.add_argument("--members-json")
    args = parser.parse_args()
    print(json.dumps(parse(Path(args.project_dir), args.members_json), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

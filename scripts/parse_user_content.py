#!/usr/bin/env python3
"""Parse manual weekly report content files."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from member_utils import load_members, resolve_member


SECTION_FILES = {
    "problems": ["problems.json", "problems.md"],
    "growth": ["growth.json", "growth.md"],
    "knowledge": ["knowledge.json", "knowledge.md"],
    "risks": ["risks.json", "risks.md"],
    "next_plans": ["next-plans.json", "next-plans.md", "plans.json", "plans.md"],
}


def owner_from_text(text: str, members: dict) -> str:
    match = re.search(r"(负责人|owner)\s*[:：]\s*([@\w\u4e00-\u9fff.-]+)", text, re.I)
    if match:
        return resolve_member(match.group(2), members)
    mention = re.search(r"@([\w\u4e00-\u9fff.-]+)", text)
    if mention:
        return resolve_member(mention.group(1), members)
    return ""


def clean_text(text: str) -> str:
    text = re.sub(r"(负责人|owner)\s*[:：]\s*[@\w\u4e00-\u9fff.-]+", "", text, flags=re.I)
    text = re.sub(r"@[\w\u4e00-\u9fff.-]+", "", text)
    return text.strip(" -:：")


def normalize_item(section: str, item: Any, members: dict) -> dict:
    if isinstance(item, str):
        owner = owner_from_text(item, members)
        content = clean_text(item)
        if section == "next_plans":
            return {"content": content, "owner": owner}
        if section == "risks":
            return {"content": content, "level": "medium", "owner": owner}
        return {"title": content, "content": content, "owner": owner}
    if not isinstance(item, dict):
        return {}
    result = dict(item)
    owner = result.get("owner") or result.get("assignee") or result.get("member")
    result["owner"] = resolve_member(owner, members) if owner else owner_from_text(json.dumps(result, ensure_ascii=False), members)
    if section == "next_plans" and "content" not in result:
        result["content"] = result.get("title", "")
    if section == "risks":
        result.setdefault("level", "medium")
        result.setdefault("content", result.get("title", ""))
    return result


def parse_json_file(path: Path, section: str, members: dict) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    items = data.get(section, data if isinstance(data, list) else [])
    return [item for item in (normalize_item(section, raw, members) for raw in items) if item]


def parse_markdown_file(path: Path, section: str, members: dict) -> list[dict]:
    items: list[dict] = []
    current_title = ""
    current_lines: list[str] = []

    def flush() -> None:
        if not current_title and not current_lines:
            return
        body = "\n".join(current_lines).strip()
        raw = {"title": current_title, "content": body or current_title}
        owner = owner_from_text(f"{current_title}\n{body}", members)
        if owner:
            raw["owner"] = owner
        if section == "problems":
            raw.setdefault("description", body)
            raw.setdefault("type", "technical")
        elif section == "growth":
            raw.setdefault("category", current_title or "成长")
        elif section == "knowledge":
            raw.setdefault("resource", "")
        elif section == "risks":
            raw = {"level": "medium", "content": body or current_title, "owner": owner}
        elif section == "next_plans":
            raw = {"content": body or current_title, "owner": owner}
        items.append(normalize_item(section, raw, members))

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("## "):
            flush()
            current_title = line.lstrip("#").strip()
            current_lines = []
        elif re.match(r"^[-*]\s+", line) and section in {"risks", "next_plans"}:
            text = re.sub(r"^[-*]\s+", "", line)
            items.append(normalize_item(section, text, members))
        else:
            current_lines.append(line)
    flush()
    return [item for item in items if item]


def read_user_input(project_dir: Path, members: dict) -> dict:
    path = project_dir / "user-input.json"
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    for section in SECTION_FILES:
        if section in data and isinstance(data[section], list):
            data[section] = [normalize_item(section, item, members) for item in data[section]]
    return data


def parse(project_dir: Path, members_path: str | None) -> dict:
    members = load_members(members_path)
    result: dict[str, Any] = read_user_input(project_dir, members)
    for section, names in SECTION_FILES.items():
        if result.get(section):
            continue
        for name in names:
            path = project_dir / name
            if not path.exists():
                continue
            if path.suffix.lower() == ".json":
                result[section] = parse_json_file(path, section, members)
            else:
                result[section] = parse_markdown_file(path, section, members)
            break
        result.setdefault(section, [])
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-dir", default=".")
    parser.add_argument("--members-json")
    args = parser.parse_args()
    print(json.dumps(parse(Path(args.project_dir), args.members_json), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

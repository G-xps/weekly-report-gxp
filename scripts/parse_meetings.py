#!/usr/bin/env python3
"""Parse meeting notes and action items."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from member_utils import find_member_mentions, load_members, parse_member_list, resolve_member


def find_meeting_files(project_dir: Path) -> list[Path]:
    files: list[Path] = []
    root_note = project_dir / "meeting-notes.md"
    if root_note.exists():
        files.append(root_note)
    meetings_dir = project_dir / "meetings"
    if meetings_dir.exists():
        files.extend(sorted(meetings_dir.glob("*.md")))
    return files


def section_name(line: str) -> str:
    text = line.strip("# ").strip().lower()
    if any(token in text for token in ["结论", "decision", "decisions"]):
        return "decisions"
    if any(token in text for token in ["action", "行动", "待办"]):
        return "actions"
    if any(token in text for token in ["风险", "risk"]):
        return "risks"
    if any(token in text for token in ["纪要", "notes", "讨论"]):
        return "notes"
    return "notes"


def parse_file(path: Path, members: dict) -> dict:
    lines = path.read_text(encoding="utf-8").splitlines()
    topic = path.stem
    date = ""
    attendees: list[str] = []
    decisions: list[str] = []
    actions: list[dict] = []
    risks: list[str] = []
    notes: list[str] = []
    current = "notes"

    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("# "):
            topic = line.lstrip("#").strip()
            continue
        if line.startswith("##"):
            current = section_name(line)
            continue
        date_match = re.match(r"(日期|date)\s*[:：]\s*(.+)", line, re.I)
        if date_match:
            date = date_match.group(2).strip()
            continue
        attendee_match = re.match(r"(参会人|attendees?)\s*[:：]\s*(.+)", line, re.I)
        if attendee_match:
            attendees = parse_member_list(attendee_match.group(2), members)
            continue
        bullet_match = re.match(r"^[-*]\s*(?:\[([ xX])\]\s*)?(.+)$", line)
        if not bullet_match:
            continue
        marker, text = bullet_match.groups()
        if current == "actions":
            owners = find_member_mentions(text, members)
            actions.append(
                {
                    "title": re.sub(r"@[\w\u4e00-\u9fff.-]+", "", text).strip(),
                    "owners": owners,
                    "status": "completed" if marker and marker.lower() == "x" else "pending",
                    "meeting": topic,
                    "date": date,
                    "source": str(path),
                }
            )
        elif current == "decisions":
            decisions.append(text.strip())
        elif current == "risks":
            risks.append(text.strip())
        else:
            notes.append(text.strip())

    related_members = set(attendees)
    for action in actions:
        related_members.update(action.get("owners", []))
    for text in decisions + risks + notes:
        related_members.update(find_member_mentions(text, members))

    return {
        "topic": topic,
        "date": date,
        "attendees": attendees,
        "decisions": decisions,
        "actions": actions,
        "risks": risks,
        "notes": notes,
        "related_members": sorted(related_members),
        "source": str(path),
    }


def parse(project_dir: Path, members_path: str | None) -> dict:
    members = load_members(members_path)
    meetings = [parse_file(path, members) for path in find_meeting_files(project_dir)]
    return {"meetings": meetings}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-dir", default=".")
    parser.add_argument("--members-json")
    args = parser.parse_args()
    print(json.dumps(parse(Path(args.project_dir), args.members_json), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

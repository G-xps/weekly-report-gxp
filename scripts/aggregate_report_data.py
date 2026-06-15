#!/usr/bin/env python3
"""Aggregate collected sources into canonical weekly report JSON."""

from __future__ import annotations

import argparse
import json
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

from member_utils import load_members, parse_member_list, related_to_targets


def default_period() -> tuple[str, str]:
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    sunday = monday + timedelta(days=6)
    return monday.isoformat(), sunday.isoformat()


def read_json(path: str | None, fallback: Any) -> Any:
    if not path:
        return fallback
    file_path = Path(path)
    if not file_path.exists():
        return fallback
    return json.loads(file_path.read_text(encoding="utf-8"))


def item_owner(item: dict) -> str:
    return str(item.get("owner") or item.get("member") or "").strip()


def filter_owned(items: list[dict], member: str) -> list[dict]:
    return [item for item in items if item_owner(item) == member or not item_owner(item)]


def make_summary(member: str, commits: list[dict], tasks: list[dict], meetings: list[dict], manual_summary: str) -> str:
    if manual_summary:
        return manual_summary
    parts: list[str] = []
    if commits:
        parts.append(f"完成 {len(commits)} 次代码提交")
    completed = [task for task in tasks if task.get("status") == "completed"]
    if completed:
        parts.append(f"闭环 {len(completed)} 项任务")
    if meetings:
        parts.append(f"参与 {len(meetings)} 场会议并跟进行动项")
    if not parts:
        return f"{member} 本周暂无自动提取到的工作记录，可补充 user-input.json 完善周报。"
    return f"{member} 本周" + "，".join(parts) + "。"


def progress_from_commits(commits: list[dict]) -> list[dict]:
    type_label = {
        "feat": "feature",
        "fix": "fix",
        "refactor": "refactor",
        "perf": "perf",
        "docs": "docs",
        "test": "test",
        "chore": "chore",
    }
    return [
        {
            "title": commit.get("title", ""),
            "description": commit.get("message", ""),
            "type": type_label.get(commit.get("type"), commit.get("type", "other")),
            "status": "completed",
            "owner": commit.get("member", ""),
            "date": commit.get("date", ""),
            "source": "git",
        }
        for commit in commits
    ]


def related_meetings_for_member(meetings: list[dict], member: str) -> list[dict]:
    related = []
    for meeting in meetings:
        members = meeting.get("related_members", []) or meeting.get("attendees", [])
        if member in members:
            related.append(meeting)
    return related


def meeting_actions_for_member(meetings: list[dict], member: str) -> list[dict]:
    actions = []
    for meeting in meetings:
        for action in meeting.get("actions", []):
            owners = action.get("owners", [])
            if member in owners:
                actions.append(action)
    return actions


def list_for_member(items: list[dict], member: str) -> list[dict]:
    return [item for item in items if item_owner(item) in {"", member}]


def aggregate(args: argparse.Namespace) -> dict:
    start_default, end_default = default_period()
    start = args.start or start_default
    end = args.end or end_default
    members = load_members(args.members_json)
    target_members = parse_member_list(args.members or "", members)

    git_data = read_json(args.git_json, {"commits": [], "stats": {}})
    task_data = read_json(args.tasks_json, {"tasks": []})
    meeting_data = read_json(args.meetings_json, {"meetings": []})
    user_data = read_json(args.user_json, {})

    commits = git_data.get("commits", [])
    tasks = task_data.get("tasks", [])
    meetings = meeting_data.get("meetings", [])

    detected_members = []
    for source_name in [commit.get("member", "") for commit in commits] + [task.get("owner", "") for task in tasks]:
        if source_name and source_name not in detected_members:
            detected_members.append(source_name)
    for meeting in meetings:
        for source_name in meeting.get("related_members", []):
            if source_name and source_name not in detected_members:
                detected_members.append(source_name)
    if not target_members:
        target_members = detected_members or list(members.keys()) or ["团队"]

    manual_summary = str(user_data.get("summary", "")).strip()
    member_reports = []
    for member in target_members:
        member_commits = [commit for commit in commits if commit.get("member") == member]
        member_tasks = [task for task in tasks if task.get("owner") in {"", member}]
        member_meetings = related_meetings_for_member(meetings, member)
        member_actions = meeting_actions_for_member(meetings, member)
        member_decisions = [
            {"meeting": meeting.get("topic", ""), "content": decision, "date": meeting.get("date", "")}
            for meeting in member_meetings
            for decision in meeting.get("decisions", [])
        ]
        member_progress = progress_from_commits(member_commits)
        member_progress.extend(
            {
                "title": task.get("title", ""),
                "description": "任务完成" if task.get("status") == "completed" else "任务推进中",
                "type": "todo",
                "status": task.get("status", "pending"),
                "owner": member,
                "source": "task",
            }
            for task in member_tasks
            if task.get("status") in {"completed", "in_progress"}
        )
        completed_tasks = [task for task in member_tasks if task.get("status") == "completed"]
        in_progress_tasks = [task for task in member_tasks if task.get("status") == "in_progress"]
        member_reports.append(
            {
                "name": member,
                "summary": make_summary(member, member_commits, member_tasks, member_meetings, manual_summary if len(target_members) == 1 else ""),
                "git_progress": progress_from_commits(member_commits),
                "progress": member_progress,
                "tasks": member_tasks,
                "meeting_actions": member_actions,
                "meeting_decisions": member_decisions,
                "meetings": member_meetings,
                "problems": list_for_member(user_data.get("problems", []), member),
                "growth": list_for_member(user_data.get("growth", []), member),
                "knowledge": list_for_member(user_data.get("knowledge", []), member),
                "next_plans": list_for_member(user_data.get("next_plans", []), member),
                "risks": list_for_member(user_data.get("risks", []), member),
                "stats": {
                    "commits": len(member_commits),
                    "completed_tasks": len(completed_tasks),
                    "in_progress_tasks": len(in_progress_tasks),
                    "meetings": len(member_meetings),
                    "action_items": len(member_actions),
                },
            }
        )

    all_member_names = [report["name"] for report in member_reports]
    scoped_tasks = [task for task in tasks if related_to_targets(task.get("owner"), all_member_names)]
    scoped_meetings = [
        meeting
        for meeting in meetings
        if related_to_targets(meeting.get("related_members", []) or meeting.get("attendees", []), all_member_names)
    ]
    scoped_commits = [commit for commit in commits if commit.get("member") in all_member_names]
    scoped_actions = [
        action
        for meeting in scoped_meetings
        for action in meeting.get("actions", [])
        if related_to_targets(action.get("owners", []), all_member_names)
    ]
    report_type = "personal" if len(target_members) == 1 else "team"
    project_name = user_data.get("project_name") or args.project_name or Path(args.project_dir).resolve().name
    reporter = user_data.get("reporter") or ("、".join(target_members) if report_type == "personal" else "研发团队")
    period_label = f"{start} 至 {end}"
    week = datetime.fromisoformat(end).strftime("%G-W%V")

    return {
        "project": {
            "name": project_name,
            "period": period_label,
            "week": week,
            "reporter": reporter,
            "report_date": date.today().isoformat(),
            "report_type": report_type,
        },
        "target_members": target_members,
        "stats": {
            "commits": len(scoped_commits),
            "contributors": len({commit.get("member") for commit in scoped_commits if commit.get("member")}),
            "completed_tasks": len([task for task in scoped_tasks if task.get("status") == "completed"]),
            "in_progress_tasks": len([task for task in scoped_tasks if task.get("status") == "in_progress"]),
            "meetings": len(scoped_meetings),
            "action_items": len(scoped_actions),
        },
        "member_reports": member_reports,
        "team_context": {
            "important_decisions": [
                {"meeting": meeting.get("topic", ""), "content": decision, "date": meeting.get("date", "")}
                for meeting in scoped_meetings
                for decision in meeting.get("decisions", [])
            ],
            "risks": user_data.get("risks", [])
            + [
                {"level": "medium", "content": risk, "owner": ""}
                for meeting in scoped_meetings
                for risk in meeting.get("risks", [])
            ],
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-dir", default=".")
    parser.add_argument("--start")
    parser.add_argument("--end")
    parser.add_argument("--members")
    parser.add_argument("--members-json")
    parser.add_argument("--git-json")
    parser.add_argument("--tasks-json")
    parser.add_argument("--meetings-json")
    parser.add_argument("--user-json")
    parser.add_argument("--project-name")
    parser.add_argument("--output")
    args = parser.parse_args()
    result = aggregate(args)
    text = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()

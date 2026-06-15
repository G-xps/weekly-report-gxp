#!/usr/bin/env python3
"""Run the full weekly report pipeline."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent


def default_period() -> tuple[str, str]:
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    sunday = monday + timedelta(days=6)
    return monday.isoformat(), sunday.isoformat()


def safe_name(value: str) -> str:
    value = value.strip() or "team"
    value = re.sub(r"[\\/:*?\"<>|\s]+", "-", value)
    return value.strip("-") or "team"


def run_json(args: list[str]) -> dict:
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    result = subprocess.run(
        [sys.executable, *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=env,
        check=True,
    )
    return json.loads(result.stdout)


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    start_default, end_default = default_period()
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-dir", default=".")
    parser.add_argument("--output-dir", default="weekly-report-output")
    parser.add_argument("--members", help="Comma-separated target members, e.g. 小明,小红")
    parser.add_argument("--members-json")
    parser.add_argument("--start", default=start_default)
    parser.add_argument("--end", default=end_default)
    parser.add_argument("--project-name")
    parser.add_argument("--pdf", action="store_true")
    args = parser.parse_args()

    project_dir = Path(args.project_dir).resolve()
    output_dir = Path(args.output_dir).resolve()
    members_json = args.members_json
    if not members_json and (project_dir / "members.json").exists():
        members_json = str(project_dir / "members.json")

    git_data = run_json(
        [
            str(SCRIPT_DIR / "collect_git.py"),
            "--project-dir",
            str(project_dir),
            "--start",
            args.start,
            "--end",
            args.end,
            *(["--members-json", members_json] if members_json else []),
        ]
    )
    tasks_data = run_json(
        [
            str(SCRIPT_DIR / "parse_tasks.py"),
            "--project-dir",
            str(project_dir),
            *(["--members-json", members_json] if members_json else []),
        ]
    )
    meetings_data = run_json(
        [
            str(SCRIPT_DIR / "parse_meetings.py"),
            "--project-dir",
            str(project_dir),
            *(["--members-json", members_json] if members_json else []),
        ]
    )
    user_data = run_json(
        [
            str(SCRIPT_DIR / "parse_user_content.py"),
            "--project-dir",
            str(project_dir),
            *(["--members-json", members_json] if members_json else []),
        ]
    )

    intermediate_dir = output_dir / "_intermediate"
    git_json = intermediate_dir / "git.json"
    tasks_json = intermediate_dir / "tasks.json"
    meetings_json = intermediate_dir / "meetings.json"
    user_json = intermediate_dir / "user.json"
    write_json(git_json, git_data)
    write_json(tasks_json, tasks_data)
    write_json(meetings_json, meetings_data)
    write_json(user_json, user_data)

    report_data_path = output_dir / "report-data.json"
    aggregate_cmd = [
        str(SCRIPT_DIR / "aggregate_report_data.py"),
        "--project-dir",
        str(project_dir),
        "--start",
        args.start,
        "--end",
        args.end,
        "--git-json",
        str(git_json),
        "--tasks-json",
        str(tasks_json),
        "--meetings-json",
        str(meetings_json),
        "--user-json",
        str(user_json),
        "--output",
        str(report_data_path),
        *(["--members", args.members] if args.members else []),
        *(["--members-json", members_json] if members_json else []),
        *(["--project-name", args.project_name] if args.project_name else []),
    ]
    report_data = run_json(aggregate_cmd)

    target = "、".join(report_data.get("target_members", [])) if report_data.get("target_members") else "team"
    html_path = output_dir / f"weekly-report-{safe_name(target)}-{args.end}.html"
    subprocess.run(
        [
            sys.executable,
            str(SCRIPT_DIR / "render_report.py"),
            str(report_data_path),
            "--output",
            str(html_path),
            "--assets-dir",
            str(SKILL_DIR / "assets"),
        ],
        env={**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONDONTWRITEBYTECODE": "1"},
        check=True,
    )

    if args.pdf:
        subprocess.run(
            [sys.executable, str(SCRIPT_DIR / "export_pdf.py"), str(html_path)],
            env={**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONDONTWRITEBYTECODE": "1"},
            check=True,
        )

    print(json.dumps({"report_data": str(report_data_path), "html": str(html_path)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

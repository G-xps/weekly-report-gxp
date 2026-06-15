---
name: weekly-report-gxp
description: "Generate developer weekly reports for one person or a team from git commits, todo/issues, meeting notes, and user-provided report content. Use when the user asks to create a weekly report, specify a member such as 小明, summarize coding work plus meetings, or export a polished HTML/PDF weekly report."
---

# Weekly Report GXP

Generate developer weekly reports with member attribution. Prefer the deterministic scripts in `scripts/` and keep the report grounded in local project data.

## Workflow

1. Confirm or infer report period. Default to current Monday through Sunday.
2. Resolve target members. If the user specifies names, filter output to those members. If not, generate a team report.
3. Collect sources:
   - Git commits with `scripts/collect_git.py`.
   - Todo/issue files with `scripts/parse_tasks.py`.
   - Meeting notes with `scripts/parse_meetings.py`.
   - Manual content with `scripts/parse_user_content.py`.
4. Aggregate with `scripts/aggregate_report_data.py`.
5. Render HTML with `scripts/render_report.py` using `assets/styles.css`.
6. Export PDF with `scripts/export_pdf.py` when requested or expected. If Chrome is unavailable, provide the generated HTML and manual print instructions.

## Inputs

- `members.json`: maps real member names to git authors, emails, short names, and mention aliases.
- `todo.md`, `TODO.md`, `issues.md`, `ISSUES.md`, or `tasks.json`: task status and owners.
- `meeting-notes.md` or `meetings/*.md`: meeting attendees, decisions, risks, and action items.
- `problems.md/json`, `growth.md/json`, `knowledge.md/json`, `risks.md/json`, `next-plans.md/json`, or `user-input.json`: manual report content.

Read `references/input-formats.md` when creating or debugging input files. Read `references/data-schema.md` before changing aggregation or rendering. Read `references/report-sections.md` before changing report layout.

## Output

Write generated files under a user-specified output directory, or `weekly-report-output/` by default:

- `report-data.json`
- `weekly-report-<member-or-team>-<end-date>.html`
- Optional `weekly-report-<member-or-team>-<end-date>.pdf`

## Notes

- If the target project is not a git repository, continue with tasks, meetings, and manual content.
- Do not invent accomplishments. Use empty-state text when a section has no data.
- Preserve the user's Chinese names and wording in report content.

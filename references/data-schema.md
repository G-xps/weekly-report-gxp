# Data Schema

`aggregate_report_data.py` produces the canonical report JSON.

```json
{
  "project": {
    "name": "项目名",
    "period": "2026-06-08 至 2026-06-14",
    "week": "2026-W24",
    "reporter": "小明",
    "report_date": "2026-06-15",
    "report_type": "personal"
  },
  "target_members": ["小明"],
  "stats": {
    "commits": 6,
    "contributors": 1,
    "completed_tasks": 3,
    "in_progress_tasks": 2,
    "meetings": 2,
    "action_items": 4
  },
  "member_reports": [
    {
      "name": "小明",
      "summary": "本周主要完成登录链路优化。",
      "git_progress": [],
      "tasks": [],
      "meeting_actions": [],
      "meeting_decisions": [],
      "problems": [],
      "growth": [],
      "knowledge": [],
      "next_plans": [],
      "risks": [],
      "stats": {}
    }
  ],
  "team_context": {
    "important_decisions": [],
    "risks": []
  }
}
```

Rendering should consume only this schema. Parser-specific shapes should be normalized before rendering.

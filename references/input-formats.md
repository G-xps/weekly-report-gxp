# Input Formats

## members.json

Use this file to map git identities and meeting/task aliases to real names.

```json
{
  "members": [
    {
      "name": "小明",
      "aliases": ["xiaoming", "ming@example.com", "XM", "@小明"]
    },
    {
      "name": "小红",
      "aliases": ["xiaohong", "hong@example.com", "XH", "@小红"]
    }
  ]
}
```

If `members.json` is missing, scripts use the raw git author or detected mention as the member name.

## Git Commit Types

Git commits support both English Conventional Commits and the Chinese aliases below. The parser normalizes aliases to English types internally.

| English | Chinese alias | Meaning |
| --- | --- | --- |
| `feat` | `新增` | New feature, page, API, script, or capability |
| `fix` | `bug` / `修复` | Bug fix, exception fix, incorrect logic |
| `docs` | `文档` | README, instructions, comments, docs |
| `style` | `代码` | Formatting, whitespace, naming-only edits |
| `refactor` | `重构` | Code structure changes without behavior changes |
| `perf` | `优化` | Performance, memory, query, or speed optimization |
| `test` | `测试` | Add or update tests |
| `chore` | `运维` | Dependencies, config, tooling maintenance |
| `build` | `构建` | Build config, packaging, build dependencies |
| `ci` | `CI/CD` | GitHub Actions, pipelines, deployment automation |

Examples:

```text
feat: 新增指定人员生成周报功能
新增: 支持会议纪要 Action Items 解析
fix: 修复 Windows 中文路径显示问题
bug: 修复任务文件重复读取
文档: 补充输入格式说明
```

## Todo / Issue Markdown

Supported files: `todo.md`, `TODO.md`, `issues.md`, `ISSUES.md`.

```markdown
## 已完成
- [x] @小明 完成登录链路优化
- [x] 负责人：小红 补充异常场景测试

## 进行中
- [ ] @小明 接入 Redis 权限缓存

## 待办
- [ ] @小红 编写接口联调文档
```

Status is inferred from checkbox and current section. Owner is inferred from `@姓名`, `负责人：姓名`, or `owner: name`.

## tasks.json

```json
[
  {"title": "完成登录链路优化", "owner": "小明", "status": "completed"},
  {"title": "接入 Redis 权限缓存", "owner": "小明", "status": "in_progress"}
]
```

## Meeting Notes

Supported files: `meeting-notes.md` and `meetings/*.md`.

```markdown
# 技术方案讨论

日期：2026-06-12
参会人：小明、小红、张三

## 结论
- 采用 Redis 缓存用户权限数据

## Action Items
- [ ] @小明 完成 Redis 缓存接入
- [x] @小红 补充异常场景测试

## 风险
- 权限缓存一致性需要重点验证
```

The parser extracts topic, date, attendees, decisions, action items, and risks. A target member is related to a meeting when they are an attendee, mentioned in an action item, or mentioned in a note line.

## Manual Content

Use JSON files for precise data, or Markdown for quick writing:

- `problems.md/json`
- `growth.md/json`
- `knowledge.md/json`
- `risks.md/json`
- `next-plans.md/json`
- `user-input.json`

`user-input.json` may contain:

```json
{
  "project_name": "GXP",
  "reporter": "小明",
  "summary": "本周完成登录链路优化，并推进权限缓存方案。",
  "problems": [],
  "growth": [],
  "knowledge": [],
  "risks": [],
  "next_plans": []
}
```

#!/usr/bin/env python3
"""Render canonical report JSON into a slide-deck HTML report."""

from __future__ import annotations

import argparse
import html
import json
import shutil
from pathlib import Path
from typing import Any


def esc(value: Any) -> str:
    return html.escape(str(value or ""), quote=True)


def item_type_icon(item_type: str) -> str:
    return {
        "feature": "fa-star",
        "feat": "fa-star",
        "fix": "fa-wrench",
        "todo": "fa-tasks",
        "refactor": "fa-code-branch",
        "perf": "fa-gauge-high",
        "docs": "fa-file-lines",
        "test": "fa-vial",
    }.get(item_type, "fa-circle-dot")


def slide(content: str, extra_class: str = "") -> str:
    class_name = f"slide {extra_class}".strip()
    return f'<section class="{class_name}" data-slide>\n{content}\n</section>'


def section_title(index: str, eyebrow: str, title: str) -> str:
    return slide(
        f"""
        <span class="section-index">{esc(index)}</span>
        <p class="eyebrow">{esc(eyebrow)}</p>
        <h2>{esc(title)}</h2>
        """,
        "section-title",
    )


def empty_item(text: str) -> str:
    return f'<article class="report-item"><p>{esc(text)}</p></article>'


def render_progress(items: list[dict]) -> str:
    if not items:
        return empty_item("暂无自动提取到的开发进展。")
    cards = []
    for item in items[:12]:
        item_type = esc(item.get("type", "todo"))
        status = esc(item.get("status", "completed"))
        owner = item.get("owner", "")
        owner_html = f'<small><i class="fas fa-user-circle"></i>负责人：{esc(owner)}</small>' if owner else ""
        cards.append(
            f"""
            <article class="report-item {status}">
                <div class="item-topline">
                    <span class="item-type type-{item_type}"><i class="fas {item_type_icon(item_type)}"></i>{item_type}</span>
                    <h3>{esc(item.get("title"))}</h3>
                </div>
                <p>{esc(item.get("description") or item.get("content"))}</p>
                {owner_html}
            </article>
            """
        )
    return "\n".join(cards)


def render_tasks(tasks: list[dict]) -> str:
    if not tasks:
        return empty_item("暂无任务记录。")
    cards = []
    for task in tasks[:12]:
        status = esc(task.get("status", "pending"))
        owner = task.get("owner", "")
        cards.append(
            f"""
            <article class="report-item {status}">
                <div class="item-topline">
                    <span class="item-type type-todo"><i class="fas fa-tasks"></i>{status}</span>
                    <h3>{esc(task.get("title"))}</h3>
                </div>
                <p>{'负责人：' + esc(owner) if owner else '未标注负责人'}</p>
            </article>
            """
        )
    return "\n".join(cards)


def render_meetings(meetings: list[dict], actions: list[dict]) -> str:
    notes = []
    if meetings:
        for meeting in meetings[:6]:
            decision_text = "；".join(meeting.get("decisions", [])[:2]) or "记录会议参与与讨论内容。"
            notes.append(
                f"""
                <article class="note-item">
                    <strong>{esc(meeting.get("topic"))}</strong>
                    <p>{esc(meeting.get("date"))} · {esc(decision_text)}</p>
                </article>
                """
            )
    else:
        notes.append('<article class="note-item"><strong>暂无会议记录</strong><p>可补充 meeting-notes.md 或 meetings/*.md。</p></article>')

    action_cards = []
    if actions:
        for action in actions[:8]:
            action_cards.append(
                f"""
                <article class="note-item">
                    <strong>{esc(action.get("title"))}</strong>
                    <p>{esc(action.get("meeting"))} · {esc(action.get("status"))}</p>
                </article>
                """
            )
    else:
        action_cards.append('<article class="note-item"><strong>暂无 Action Items</strong><p>会议中未提取到分配给目标人员的行动项。</p></article>')

    return f"""
    <div class="note-panel">
        <h3><i class="fas fa-comments"></i>会议纪要</h3>
        {''.join(notes)}
    </div>
    <div class="note-panel">
        <h3><i class="fas fa-list-check"></i>Action Items</h3>
        {''.join(action_cards)}
    </div>
    """


def render_problems(items: list[dict]) -> str:
    if not items:
        return empty_item("暂无问题或阻塞记录。")
    cards = []
    for item in items[:8]:
        solution = item.get("solution", "")
        solution_html = f'<small><i class="fas fa-lightbulb"></i>解决方案：{esc(solution)}</small>' if solution else ""
        cards.append(
            f"""
            <article class="problem-item">
                <div class="item-topline">
                    <span class="problem-type">{esc(item.get("type", "issue"))}</span>
                    <h3>{esc(item.get("title") or item.get("content"))}</h3>
                </div>
                <p>{esc(item.get("description") or item.get("content"))}</p>
                {solution_html}
            </article>
            """
        )
    return "\n".join(cards)


def render_growth(items: list[dict]) -> str:
    if not items:
        return empty_item("暂无技术成长记录。")
    return "\n".join(
        f"""
        <article class="growth-item">
            <i class="fas fa-seedling"></i>
            <h3>{esc(item.get("category") or item.get("title"))}</h3>
            <p>{esc(item.get("content"))}</p>
            <small>{esc(item.get("impact"))}</small>
        </article>
        """
        for item in items[:8]
    )


def render_knowledge(items: list[dict]) -> str:
    if not items:
        return empty_item("暂无知识分享记录。")
    cards = []
    for item in items[:8]:
        resource = item.get("resource", "")
        resource_html = f'<a href="{esc(resource)}" target="_blank"><i class="fas fa-link"></i>{esc(resource)}</a>' if resource else ""
        cards.append(
            f"""
            <article class="knowledge-item">
                <h3>{esc(item.get("title"))}</h3>
                <p>{esc(item.get("content"))}</p>
                {resource_html}
            </article>
            """
        )
    return "\n".join(cards)


def render_risks(items: list[dict]) -> str:
    if not items:
        return '<li><span class="risk-level level-low">low</span><p>暂无风险记录。</p></li>'
    return "\n".join(
        f"""
        <li>
            <span class="risk-level level-{esc(item.get("level", "medium"))}">{esc(item.get("level", "medium"))}</span>
            <p>{esc(item.get("content"))}</p>
        </li>
        """
        for item in items[:10]
    )


def render_plans(items: list[dict]) -> str:
    if not items:
        return "<li>暂无下周计划，可补充 next-plans.md 或 user-input.json。</li>"
    return "\n".join(f"<li>{esc(item.get('content') or item.get('title'))}</li>" for item in items[:10])


def render_html(data: dict) -> str:
    project = data["project"]
    stats = data["stats"]
    report = data["member_reports"][0] if data.get("member_reports") else {"name": "团队", "summary": ""}
    all_progress = [item for member in data.get("member_reports", []) for item in member.get("progress", [])]
    all_tasks = [item for member in data.get("member_reports", []) for item in member.get("tasks", [])]
    all_meetings = [item for member in data.get("member_reports", []) for item in member.get("meetings", [])]
    all_actions = [item for member in data.get("member_reports", []) for item in member.get("meeting_actions", [])]
    all_problems = [item for member in data.get("member_reports", []) for item in member.get("problems", [])]
    all_growth = [item for member in data.get("member_reports", []) for item in member.get("growth", [])]
    all_knowledge = [item for member in data.get("member_reports", []) for item in member.get("knowledge", [])]
    all_plans = [item for member in data.get("member_reports", []) for item in member.get("next_plans", [])]
    all_risks = [item for member in data.get("member_reports", []) for item in member.get("risks", [])] + data.get("team_context", {}).get("risks", [])
    title = f"{project['name']} 周报"
    target = "、".join(data.get("target_members", [])) or project.get("reporter", "研发团队")

    slides = [
        slide(
            f"""
            <div class="cover-mark">Weekly Report</div>
            <div class="cover-content">
                <p class="kicker">项目周报</p>
                <h1>{esc(project['name'])}</h1>
                <div class="cover-meta">
                    <span><i class="fas fa-calendar-alt"></i>{esc(project['week'])}</span>
                    <span><i class="fas fa-user"></i>{esc(target)}</span>
                    <span><i class="fas fa-clock"></i>{esc(project['report_date'])}</span>
                </div>
            </div>
            """,
            "slide-cover is-active",
        ),
        slide(
            """
            <div class="slide-heading">
                <span class="eyebrow">00 / 汇报流程</span>
                <h2>本次周报将按这些部分展开</h2>
            </div>
            <div class="agenda-grid">
                <div class="agenda-card"><span>01</span>基本信息</div>
                <div class="agenda-card"><span>02</span>数据统计</div>
                <div class="agenda-card"><span>03</span>本周概览</div>
                <div class="agenda-card"><span>04</span>开发进展</div>
                <div class="agenda-card"><span>05</span>任务完成情况</div>
                <div class="agenda-card"><span>06</span>会议纪要与 Action Items</div>
                <div class="agenda-card"><span>07</span>问题处理</div>
                <div class="agenda-card"><span>08</span>风险与需协调事项</div>
                <div class="agenda-card agenda-card-wide"><span>09</span>技术成长 / 知识分享 / 下周计划</div>
            </div>
            """,
            "slide-agenda",
        ),
        section_title("01", "Basic Information", "基本信息"),
        slide(
            f"""
            <div class="slide-heading"><span class="eyebrow">01 / 基本信息</span><h2>汇报对象与周期</h2></div>
            <div class="info-board">
                <div class="info-item"><i class="fas fa-layer-group"></i><span>项目名称</span><strong>{esc(project['name'])}</strong></div>
                <div class="info-item"><i class="fas fa-calendar-week"></i><span>报告周期</span><strong>{esc(project['period'])}</strong></div>
                <div class="info-item"><i class="fas fa-user-check"></i><span>汇报人</span><strong>{esc(project['reporter'])}</strong></div>
                <div class="info-item"><i class="fas fa-file-signature"></i><span>报告日期</span><strong>{esc(project['report_date'])}</strong></div>
            </div>
            """
        ),
        section_title("02", "Data Statistics", "数据统计"),
        slide(
            f"""
            <div class="slide-heading"><span class="eyebrow">02 / 数据统计</span><h2>本周关键数字</h2></div>
            <div class="stats-grid">
                <div class="stat-card stat-card-primary"><i class="fas fa-code-commit"></i><span>本周提交</span><strong>{stats['commits']}</strong></div>
                <div class="stat-card stat-card-success"><i class="fas fa-users"></i><span>参与人数</span><strong>{stats['contributors']}</strong></div>
                <div class="stat-card stat-card-warning"><i class="fas fa-check-circle"></i><span>完成事项</span><strong>{stats['completed_tasks']}</strong></div>
                <div class="stat-card stat-card-info"><i class="fas fa-comments"></i><span>会议行动项</span><strong>{stats['action_items']}</strong></div>
            </div>
            """
        ),
        section_title("03", "Weekly Overview", "本周概览"),
        slide(
            f"""
            <div class="slide-heading"><span class="eyebrow">03 / 本周概览</span><h2>工作面概览</h2></div>
            <div class="overview-layout">
                <div class="overview-panel"><i class="fas fa-arrow-trend-up"></i><h3>推进重点</h3><p>{esc(report.get('summary'))}</p></div>
                <div class="overview-metrics">
                    <div><span>{stats['completed_tasks']}</span>已完成</div>
                    <div><span>{stats['in_progress_tasks']}</span>推进中</div>
                    <div><span>{stats['meetings']}</span>相关会议</div>
                </div>
            </div>
            """
        ),
        section_title("04", "Development Progress", "本周开发进展"),
        slide(f'<div class="slide-heading"><span class="eyebrow">04 / 开发进展</span><h2>功能、修复与待办推进</h2></div><div class="item-list">{render_progress(all_progress)}</div>'),
        section_title("05", "Task Completion", "任务完成情况"),
        slide(f'<div class="slide-heading"><span class="eyebrow">05 / 任务完成情况</span><h2>任务清单</h2></div><div class="item-list">{render_tasks(all_tasks)}</div>'),
        section_title("06", "Meetings & Action Items", "会议纪要与 Action Items"),
        slide(f'<div class="slide-heading"><span class="eyebrow">06 / 会议参与与行动项</span><h2>会议结论与后续动作</h2></div><div class="meeting-layout">{render_meetings(all_meetings, all_actions)}</div>'),
        section_title("07", "Issue Handling", "问题处理"),
        slide(f'<div class="slide-heading"><span class="eyebrow">07 / 问题与阻塞</span><h2>本周问题、处理方案与经验</h2></div><div class="item-list">{render_problems(all_problems)}</div>'),
        section_title("08", "Risks & Coordination", "风险与需协调事项"),
        slide(f'<div class="slide-heading"><span class="eyebrow">08 / 风险与需协调事项</span><h2>需要关注的风险点</h2></div><ul class="risk-list">{render_risks(all_risks)}</ul>'),
        section_title("09", "Growth & Sharing", "技术成长 / 知识分享"),
        slide(f'<div class="slide-heading"><span class="eyebrow">09 / 技术成长</span><h2>个人成长与沉淀</h2></div><div class="growth-grid">{render_growth(all_growth)}</div>'),
        slide(f'<div class="slide-heading"><span class="eyebrow">09 / 知识分享</span><h2>相关知识分享</h2></div><div class="knowledge-list">{render_knowledge(all_knowledge)}</div>'),
        section_title("10", "Next Week Plan", "下周计划"),
        slide(f'<div class="slide-heading"><span class="eyebrow">10 / 下周计划</span><h2>下一阶段工作安排</h2></div><ol class="plan-list">{render_plans(all_plans)}</ol>'),
    ]

    script = """
    <script>
        (function () {
            const deck = document.querySelector('[data-deck]');
            const track = document.querySelector('[data-slide-track]');
            const slides = Array.from(document.querySelectorAll('[data-slide]'));
            const prev = document.querySelector('[data-prev]');
            const next = document.querySelector('[data-next]');
            const current = document.querySelector('[data-current-page]');
            const total = document.querySelector('[data-total-pages]');
            const progress = document.querySelector('[data-progress-bar]');
            const pageInput = document.querySelector('[data-page-input]');
            const pageGrid = document.querySelector('[data-page-grid]');
            let index = 0;
            function getVisiblePageItems(currentPage, totalPages) {
                if (totalPages <= 7) return Array.from({ length: totalPages }, (_, itemIndex) => itemIndex + 1);
                if (currentPage <= 4) return [1, 2, 3, 4, 5, 'ellipsis', totalPages];
                if (currentPage >= totalPages - 3) return [1, 'ellipsis', totalPages - 4, totalPages - 3, totalPages - 2, totalPages - 1, totalPages];
                return [1, 'ellipsis-start', currentPage - 1, currentPage, currentPage + 1, 'ellipsis-end', totalPages];
            }
            function renderPageButtons() {
                const currentPage = index + 1;
                pageGrid.innerHTML = '';
                getVisiblePageItems(currentPage, slides.length).forEach((item) => {
                    if (typeof item !== 'number') {
                        const ellipsis = document.createElement('span');
                        ellipsis.className = 'page-ellipsis';
                        ellipsis.textContent = '...';
                        pageGrid.appendChild(ellipsis);
                        return;
                    }
                    const button = document.createElement('button');
                    button.type = 'button';
                    button.className = 'page-tile';
                    button.textContent = String(item);
                    button.classList.toggle('is-current', item === currentPage);
                    button.addEventListener('click', () => updateSlide(item - 1));
                    pageGrid.appendChild(button);
                });
            }
            function updateSlide(target) {
                index = Math.max(0, Math.min(target, slides.length - 1));
                track.style.transform = `translateX(-${index * 100}vw)`;
                slides.forEach((slide, slideIndex) => slide.classList.toggle('is-active', slideIndex === index));
                renderPageButtons();
                current.textContent = String(index + 1);
                total.textContent = String(slides.length);
                pageInput.value = String(index + 1);
                pageInput.max = String(slides.length);
                progress.style.width = `${((index + 1) / slides.length) * 100}%`;
                prev.disabled = index === 0;
                next.disabled = index === slides.length - 1;
            }
            prev.addEventListener('click', () => updateSlide(index - 1));
            next.addEventListener('click', () => updateSlide(index + 1));
            pageInput.addEventListener('keydown', (event) => {
                if (event.key !== 'Enter') return;
                updateSlide(Number(pageInput.value) - 1);
                pageInput.blur();
            });
            window.addEventListener('keydown', (event) => {
                if (document.activeElement === pageInput) return;
                if (event.key === 'ArrowLeft' || event.key === 'PageUp') updateSlide(index - 1);
                if (event.key === 'ArrowRight' || event.key === 'PageDown' || event.key === ' ') updateSlide(index + 1);
            });
            let touchStart = 0;
            deck.addEventListener('touchstart', (event) => { touchStart = event.changedTouches[0].clientX; }, { passive: true });
            deck.addEventListener('touchend', (event) => {
                const delta = event.changedTouches[0].clientX - touchStart;
                if (Math.abs(delta) > 50) updateSlide(index + (delta < 0 ? 1 : -1));
            }, { passive: true });
            updateSlide(0);
        })();
    </script>
    """
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{esc(title)}</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">
    <link rel="stylesheet" href="styles.css">
</head>
<body>
    <div class="deck-shell" data-deck>
        <div class="deck-progress" aria-hidden="true"><span data-progress-bar></span></div>
        <main class="slide-stage"><div class="slide-track" data-slide-track>{''.join(slides)}</div></main>
        <footer class="deck-controls" aria-label="幻灯片翻页控制">
            <label class="jump-control"><input type="number" min="1" value="1" data-page-input aria-label="输入页码后按回车跳转"></label>
            <button class="control-button" type="button" data-prev aria-label="上一页"><i class="fas fa-chevron-left"></i></button>
            <div class="page-grid" data-page-grid aria-label="页码列表"></div>
            <button class="control-button" type="button" data-next aria-label="下一页"><i class="fas fa-chevron-right"></i></button>
            <div class="page-count" aria-live="polite"><span data-current-page>1</span>/<span data-total-pages>1</span></div>
        </footer>
    </div>
    {script}
</body>
</html>
"""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("report_json")
    parser.add_argument("--output", required=True)
    parser.add_argument("--assets-dir", default=str(Path(__file__).resolve().parents[1] / "assets"))
    args = parser.parse_args()
    data = json.loads(Path(args.report_json).read_text(encoding="utf-8"))
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render_html(data), encoding="utf-8")
    styles = Path(args.assets_dir) / "styles.css"
    if styles.exists():
        shutil.copy2(styles, output.parent / "styles.css")
    print(f"HTML report generated: {output}")


if __name__ == "__main__":
    main()

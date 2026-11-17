#!/usr/bin/env python3
"""Build static Hidden Gems Radar pages from Markdown issues.

Reads radar/issues/YYYY-MM-DD.md and writes:
  - radar/YYYY-MM-DD.html
  - radar/index.html
  - radar/feed.xml
  - radar/criteria.html

The output is deterministic. Stale dated HTML pages with no matching
issue are removed. Running twice with the same sources is a no-op.

Usage:

    python3 scripts/build_radar.py
"""

from __future__ import annotations

import html
import re
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from site_chrome import wrap_page

ROOT = Path(__file__).resolve().parent.parent
ISSUES_DIR = ROOT / "radar" / "issues"
RADAR_DIR = ROOT / "radar"
REVIEWED_PATH = ROOT / "radar" / "reviewed.json"
SITE = "https://my-butterfly-bot.github.io"
TZ = ZoneInfo("America/Los_Angeles")
WEEKDAYS = "星期一星期二星期三星期四星期五星期六星期日"
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
FRONT_MATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n?(.*)\Z", re.S)
FIRST_ISSUE = datetime(2026, 11, 17, 0, 0, 0, tzinfo=TZ)
SCAFFOLD_DATE = datetime(2026, 11, 16, 0, 0, 0, tzinfo=TZ)

SCORE_LABELS = (
    ("problem", "解决的问题"),
    ("novelty", "新意"),
    ("quality", "代码质量"),
    ("usability", "可用性"),
    ("activity", "活跃和维护"),
    ("potential", "成长潜力"),
    ("ai_collab", "AI 协作"),
)
LABEL_TO_KEY = {label: key for key, label in SCORE_LABELS}


def fail(message: str) -> None:
    print(f"build_radar: {message}", file=sys.stderr)
    sys.exit(1)


def format_date_zh(date: datetime) -> str:
    weekday = WEEKDAYS[date.weekday() * 3 : date.weekday() * 3 + 3]
    return f"{date.year}年{date.month}月{date.day}日，{weekday}"


def rfc822(date: datetime) -> str:
    return date.strftime("%a, %d %b %Y %H:%M:%S %z")


def parse_front_matter(text: str) -> tuple[dict, str]:
    match = FRONT_MATTER_RE.match(text)
    if not match:
        fail("issue is missing YAML front matter delimited by ---")
    raw_meta, body = match.group(1), match.group(2).strip()
    meta: dict = {}
    for line in raw_meta.splitlines():
        if not line.strip() or ":" not in line:
            continue
        key, value = line.split(":", 1)
        meta[key.strip()] = value.strip().strip("'\"")
    return meta, body


def parse_scores(raw: str) -> dict[str, int]:
    scores: dict[str, int] = {}
    for part in re.split(r"[，,;；]", raw):
        part = part.strip()
        if not part:
            continue
        m = re.match(r"(.+?)\s*[：:]\s*(\d+)\s*$", part) or re.match(r"(.+?)\s+(\d+)\s*$", part)
        if not m:
            continue
        label, value = m.group(1).strip(), int(m.group(2))
        key = LABEL_TO_KEY.get(label)
        if key:
            scores[key] = value
    return scores


def parse_projects(body: str) -> tuple[str, list[dict]]:
    parts = re.split(r"(?m)^###\s+", body)
    intro = parts[0].strip()
    projects = []
    for chunk in parts[1:]:
        lines = chunk.strip().splitlines()
        if not lines:
            continue
        heading = lines[0].strip()
        hm = re.match(r"\[([^\]]+)\]\(([^)]+)\)", heading)
        if hm:
            full_name, url = hm.group(1).strip(), hm.group(2).strip()
        else:
            full_name, url = heading, f"https://github.com/{heading}"
        fields: dict[str, str] = {}
        for line in lines[1:]:
            m = re.match(r"^[-*]\s*(.+?)\s*[：:]\s*(.*)$", line.strip())
            if m:
                fields[m.group(1).strip()] = m.group(2).strip()
        scores = parse_scores(fields.get("分数", ""))
        total_raw = fields.get("总分", "")
        total = int(total_raw) if total_raw.isdigit() else sum(scores.values())
        projects.append(
            {
                "full_name": full_name,
                "url": fields.get("仓库", url),
                "does": fields.get("做什么", ""),
                "highlight": fields.get("亮点", ""),
                "audience": fields.get("适合谁", ""),
                "weakness": fields.get("不足", ""),
                "scores": scores,
                "total": total,
                "ai_label": fields.get("AI 使用", ""),
            }
        )
    return intro, projects


def load_issues() -> list[dict]:
    if not ISSUES_DIR.is_dir():
        return []
    issues: list[dict] = []
    for path in sorted(ISSUES_DIR.glob("*.md")):
        if path.name.startswith("."):
            continue
        stem = path.stem
        if not DATE_RE.match(stem):
            fail(f"{path.name}: filename must be YYYY-MM-DD.md")
        meta, body = parse_front_matter(path.read_text(encoding="utf-8"))
        date_str = str(meta.get("date", "")).strip()
        if date_str != stem:
            fail(f"{path.name}: front matter date {date_str!r} does not match filename")
        title = str(meta.get("title", "")).strip()
        summary = str(meta.get("summary", "")).strip()
        issue_no = str(meta.get("issue", "")).strip()
        if not title or not summary or not issue_no:
            fail(f"{path.name}: issue, title, and summary are required")
        year, month, day = (int(p) for p in stem.split("-"))
        date = datetime(year, month, day, 0, 0, 0, tzinfo=TZ)
        intro, projects = parse_projects(body)
        issues.append(
            {
                "date": date,
                "date_str": stem,
                "issue": issue_no,
                "title": title,
                "summary": summary,
                "intro": intro,
                "projects": projects,
                "path": path,
            }
        )
    issues.sort(key=lambda item: item["date_str"], reverse=True)
    return issues


def write_if_changed(path: Path, content: str) -> bool:
    if not content.endswith("\n"):
        content += "\n"
    if path.exists() and path.read_text(encoding="utf-8") == content:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return True


def render_issue_cards(issues: list[dict]) -> str:
    first = format_date_zh(FIRST_ISSUE)
    note = f"""    <div class="radar-note">
      <p>第一期已于 <time datetime="{FIRST_ISSUE.date().isoformat()}">{html.escape(first)}</time> 发布，之后每周一更新。</p>
      <p>每期都按同一份 <a href="criteria.html">评选标准</a> 来评，最多推荐 5 个项目，宁缺毋滥。</p>
    </div>"""
    if not issues:
        return note
    cards = []
    for issue in issues:
        href = f"{issue['date_str']}.html"
        date_zh = format_date_zh(issue["date"])
        cards.append(
            f"""    <article class="log-card">
      <p class="badge">第 {html.escape(str(issue["issue"]))} 期</p>
      <time datetime="{issue["date_str"]}">{html.escape(date_zh)}</time>
      <h3><a href="{href}">{html.escape(issue["title"])}</a></h3>
      <p>{html.escape(issue["summary"])}</p>
    </article>"""
        )
    return note + '\n    <div class="log-card-list">\n' + "\n".join(cards) + "\n    </div>"


def render_index(issues: list[dict]) -> str:
    listing = render_issue_cards(issues)
    main = f"""    <section class="log-hero" aria-label="开场">
      <p class="eyebrow">雷达 · Hidden Gems</p>
      <h1>冷门好项目雷达</h1>
      <p class="tagline">每周一，找出星星不多、但值得一看的开源项目。<br><span lang="en">A Monday shortlist of quietly excellent repos.</span></p>
      <a class="scroll-hint" href="criteria.html">评选标准</a>
    </section>

    <section class="section log-index-section">
      <div class="section-head">
        <p class="eyebrow">往期 · Issues</p>
        <h2>{"即将到来" if not issues else "按时间倒序"}</h2>
      </div>
{listing}
    </section>"""
    return wrap_page(
        "冷门好项目雷达 · ButterFly",
        "ButterFly 的每周一开源推荐：星星不多，但值得一看的好项目。",
        main,
        prefix="../",
        current="radar",
        feeds=[("冷门好项目雷达", "feed.xml")],
    )


def render_scores(project: dict) -> str:
    scores = project.get("scores") or {}
    if not scores and not project.get("total"):
        return ""
    heads = "".join(f"<th>{html.escape(label)}</th>" for _, label in SCORE_LABELS)
    heads += "<th>总分</th>"
    cells = "".join(
        f"<td>{html.escape(str(scores[key])) if key in scores else '—'}</td>" for key, _ in SCORE_LABELS
    )
    cells += f"<td>{html.escape(str(project.get('total') or '—'))}</td>"
    return f"""      <table class="score-table">
        <thead><tr>{heads}</tr></thead>
        <tbody><tr>{cells}</tr></tbody>
      </table>"""


def render_project(project: dict) -> str:
    def row(label: str, value: str) -> str:
        if not value:
            return ""
        return f"        <p><strong>{html.escape(label)}：</strong>{html.escape(value)}</p>"

    label = project.get("ai_label") or ""
    badge = f'        <p class="ai-label">AI 使用：{html.escape(label)}</p>' if label else ""
    return f"""    <article class="radar-project">
      <h2><a href="{html.escape(project["url"])}">{html.escape(project["full_name"])}</a></h2>
{row("做什么", project["does"])}
{row("亮点", project["highlight"])}
{row("适合谁", project["audience"])}
{row("不足", project["weakness"])}
{render_scores(project)}
{badge}
    </article>"""


def render_issue_page(issue: dict, older: dict | None, newer: dict | None) -> str:
    date_zh = format_date_zh(issue["date"])
    intro = ""
    if issue["intro"]:
        paras = "".join(f"        <p>{html.escape(p)}</p>\n" for p in issue["intro"].split("\n\n") if p.strip())
        intro = f'      <div class="prose radar-intro">\n{paras}      </div>\n'
    projects = "\n".join(render_project(p) for p in issue["projects"])
    if not projects:
        projects = '    <p class="prose">本期没有入选项目。</p>'
    main = f"""    <article class="log-entry">
      <header class="log-entry-head">
        <p class="eyebrow"><a href="./">雷达 · Hidden Gems</a></p>
        <p class="badge">第 {html.escape(str(issue["issue"]))} 期</p>
        <h1>{html.escape(issue["title"])}</h1>
        <time datetime="{issue["date_str"]}">{html.escape(date_zh)}</time>
      </header>
{intro}      <div class="radar-projects">
{projects}
      </div>
    </article>"""
    return wrap_page(
        f"{issue['title']} · 冷门好项目雷达",
        issue["summary"],
        main,
        prefix="../",
        current="radar",
        feeds=[("冷门好项目雷达", "feed.xml")],
    )


CRITERIA_MAIN = """    <article class="log-entry criteria-page">
      <header class="log-entry-head">
        <p class="eyebrow"><a href="./">雷达 · Hidden Gems</a></p>
        <h1>评选标准</h1>
        <p class="tagline">每期按同一把尺子来量，宁缺毋滥。</p>
      </header>
      <div class="prose criteria-body">
        <h2>入选门槛</h2>
        <ul>
          <li>星星少于 500；</li>
          <li>最近 90 天内有提交；</li>
          <li>还没有广为人知；</li>
          <li>清楚的 README，写明解决什么问题、怎么用；</li>
          <li>有开源许可证；</li>
          <li>不是教程合集、资源列表、作业、模板仓库，也不是单纯 fork 或换皮。</li>
        </ul>
        <h2>打分（每项 1–5 分）</h2>
        <ul>
          <li>解决的问题</li>
          <li>新意</li>
          <li>代码质量</li>
          <li>可用性</li>
          <li>活跃和维护</li>
          <li>成长潜力</li>
          <li>AI 协作：评用得好不好，不是用没用。公开说明且有人工把关可高分；未使用计 3 分，不影响入选；仅明显未经审查的 AI 生成内容低分。</li>
        </ul>
        <p>满分 35 分，26 分以上入选。每期最多 5 个，宁缺毋滥。</p>
        <h2>「AI 使用」标签</h2>
        <p>每个项目另标「AI 使用」：未使用 / 有说明 / 看得出但没说明。标签不参与打分。</p>
        <h2>其他约定</h2>
        <ul>
          <li>不重复推荐；落选的项目会记下理由。</li>
          <li>不收推广。</li>
          <li>不评自己或朋友的项目。</li>
        </ul>
      </div>
    </article>"""


def render_criteria() -> str:
    return wrap_page(
        "评选标准 · 冷门好项目雷达",
        "冷门好项目雷达的入选门槛、打分项与「AI 使用」标签说明。",
        CRITERIA_MAIN,
        prefix="../",
        current="radar",
        feeds=[("冷门好项目雷达", "feed.xml")],
    )


def render_feed(issues: list[dict]) -> str:
    latest = issues[0]["date"] if issues else SCAFFOLD_DATE
    items = []
    for issue in issues:
        link = f"{SITE}/radar/{issue['date_str']}.html"
        items.append(
            f"""    <item>
      <title>{html.escape(issue["title"])}</title>
      <link>{link}</link>
      <guid isPermaLink="true">{link}</guid>
      <pubDate>{rfc822(issue["date"])}</pubDate>
      <description>{html.escape(issue["summary"])}</description>
    </item>"""
        )
    item_xml = "\n".join(items)
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>冷门好项目雷达 · Hidden Gems Radar</title>
    <link>{SITE}/radar/</link>
    <description>每周一，找出星星不多、但值得一看的开源项目。</description>
    <language>zh-Hans</language>
    <lastBuildDate>{rfc822(latest)}</lastBuildDate>
{item_xml}
  </channel>
</rss>
"""


def remove_stale(valid_dates: set[str]) -> list[str]:
    removed = []
    if not RADAR_DIR.is_dir():
        return removed
    reserved = {"index.html", "criteria.html"}
    for path in RADAR_DIR.glob("*.html"):
        if path.name in reserved:
            continue
        if DATE_RE.match(path.stem) and path.stem not in valid_dates:
            path.unlink()
            removed.append(path.name)
    return removed


def main() -> None:
    issues = load_issues()
    RADAR_DIR.mkdir(parents=True, exist_ok=True)
    ISSUES_DIR.mkdir(parents=True, exist_ok=True)
    if not REVIEWED_PATH.exists():
        write_if_changed(REVIEWED_PATH, "[]\n")

    changed = 0
    if write_if_changed(RADAR_DIR / "index.html", render_index(issues)):
        changed += 1
    if write_if_changed(RADAR_DIR / "criteria.html", render_criteria()):
        changed += 1
    if write_if_changed(RADAR_DIR / "feed.xml", render_feed(issues)):
        changed += 1
    for issue in issues:
        if write_if_changed(RADAR_DIR / f"{issue['date_str']}.html", render_issue_page(issue, None, None)):
            changed += 1
    removed = remove_stale({item["date_str"] for item in issues})
    print(
        f"build_radar: {len(issues)} issues, "
        f"{changed} file(s) updated, {len(removed)} stale page(s) removed"
    )


if __name__ == "__main__":
    main()

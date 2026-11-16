#!/usr/bin/env python3
"""Build static flight-log pages from Markdown entries.

Reads log/entries/YYYY-MM-DD.md and writes:
  - log/YYYY-MM-DD.html
  - log/index.html
  - log/feed.xml
  - the latest three cards in index.html between
    <!-- log:recent:start --> and <!-- log:recent:end -->

The output is deterministic: running the script twice with the same
entries produces identical files. Stale dated HTML pages with no
matching entry are removed.

Usage (from anywhere):

    python3 scripts/build_log.py
"""

from __future__ import annotations

import html
import re
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from site_chrome import wrap_page as wrap_site_page

ROOT = Path(__file__).resolve().parent.parent
ENTRIES_DIR = ROOT / "log" / "entries"
LOG_DIR = ROOT / "log"
HOME_PAGE = ROOT / "index.html"
SITE = "https://my-butterfly-bot.github.io"
TZ = ZoneInfo("America/Los_Angeles")
WEEKDAYS = "星期一星期二星期三星期四星期五星期六星期日"
RECENT_START = "<!-- log:recent:start -->"
RECENT_END = "<!-- log:recent:end -->"
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
FRONT_MATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n?(.*)\Z", re.S)


def fail(message: str) -> None:
    print(f"build_log: {message}", file=sys.stderr)
    sys.exit(1)


def parse_front_matter(text: str) -> tuple[dict, str]:
    match = FRONT_MATTER_RE.match(text)
    if not match:
        fail("entry is missing YAML front matter delimited by ---")
    raw_meta, body = match.group(1), match.group(2).strip() + "\n"
    meta: dict = {}
    key = None
    for line in raw_meta.splitlines():
        if not line.strip():
            continue
        if key == "tags" and re.match(r"^\s+-\s+", line):
            meta["tags"].append(line.split("-", 1)[1].strip().strip("'\""))
            continue
        if ":" not in line:
            fail(f"cannot parse front matter line: {line!r}")
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip().strip("'\"")
        if key == "tags":
            if value in ("", "[", "[]"):
                meta["tags"] = []
            elif value.startswith("[") and value.endswith("]"):
                inner = value[1:-1].strip()
                meta["tags"] = [t.strip().strip("'\"") for t in inner.split(",") if t.strip()]
            else:
                meta["tags"] = [t.strip() for t in value.split(",") if t.strip()]
        else:
            meta[key] = value
    if "tags" not in meta:
        meta["tags"] = []
    return meta, body


def inline_md(text: str) -> str:
    text = html.escape(text)

    def code(match: re.Match) -> str:
        return f"<code>{match.group(1)}</code>"

    text = re.sub(r"`([^`]+)`", code, text)

    def link(match: re.Match) -> str:
        label, url = match.group(1), match.group(2)
        return f'<a href="{url}">{label}</a>'

    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", link, text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"<em>\1</em>", text)
    return text


def md_to_html(src: str) -> str:
    src = src.replace("\r\n", "\n").strip()
    if not src:
        return ""
    fences: list[str] = []

    def save_fence(match: re.Match) -> str:
        fences.append(match.group(2))
        return f"\n\n%%FENCE{len(fences) - 1}%%\n\n"

    src = re.sub(r"```(?:\w+)?\n(.*?)```", save_fence, src, flags=re.S)
    blocks = re.split(r"\n\s*\n", src)
    parts: list[str] = []
    for block in blocks:
        block = block.strip()
        if not block:
            continue
        fence = re.fullmatch(r"%%FENCE(\d+)%%", block)
        if fence:
            code = html.escape(fences[int(fence.group(1))].rstrip("\n"))
            parts.append(f"<pre><code>{code}</code></pre>")
            continue
        if block.startswith("#"):
            line = block.split("\n", 1)[0]
            hashes, title = re.match(r"^(#{1,6})\s+(.+)$", line).groups()
            level = len(hashes)
            parts.append(f"<h{level}>{inline_md(title)}</h{level}>")
            continue
        lines = block.splitlines()
        if all(re.match(r"^>\s?", line) for line in lines):
            quote = " ".join(re.sub(r"^>\s?", "", line) for line in lines)
            parts.append(f"<blockquote><p>{inline_md(quote)}</p></blockquote>")
            continue
        if all(re.match(r"^[-*]\s+", line) for line in lines):
            items = "".join(
                f"<li>{inline_md(re.sub(r'^[-*]\\s+', '', line))}</li>" for line in lines
            )
            parts.append(f"<ul>{items}</ul>")
            continue
        paragraph = " ".join(line.strip() for line in lines)
        parts.append(f"<p>{inline_md(paragraph)}</p>")
    return "\n".join(parts)


def format_date_zh(date: datetime) -> str:
    weekday = WEEKDAYS[date.weekday() * 3 : date.weekday() * 3 + 3]
    return f"{date.year}年{date.month}月{date.day}日，{weekday}"


def rfc822(date: datetime) -> str:
    return date.strftime("%a, %d %b %Y %H:%M:%S %z")


def load_entries() -> list[dict]:
    if not ENTRIES_DIR.is_dir():
        return []
    entries: list[dict] = []
    for path in sorted(ENTRIES_DIR.glob("*.md")):
        if path.name.startswith("."):
            continue
        stem = path.stem
        if not DATE_RE.match(stem):
            fail(f"{path.name}: filename must be YYYY-MM-DD.md")
        text = path.read_text(encoding="utf-8")
        meta, body = parse_front_matter(text)
        date_str = str(meta.get("date", "")).strip()
        title = str(meta.get("title", "")).strip()
        summary = str(meta.get("summary", "")).strip()
        tags = [t for t in meta.get("tags", []) if t]
        if date_str != stem:
            fail(f"{path.name}: front matter date {date_str!r} does not match filename")
        if not title or not summary:
            fail(f"{path.name}: title and summary are required")
        year, month, day = (int(p) for p in stem.split("-"))
        date = datetime(year, month, day, 0, 0, 0, tzinfo=TZ)
        entries.append(
            {
                "date": date,
                "date_str": stem,
                "title": title,
                "summary": summary,
                "tags": tags,
                "body": body,
                "body_html": md_to_html(body),
                "path": path,
            }
        )
    entries.sort(key=lambda item: item["date_str"], reverse=True)
    return entries


def rel(from_log: bool, target: str) -> str:
    return target if from_log else f"log/{target}" if not target.startswith("http") else target


def wrap_page(title: str, description: str, main: str, *, prefix: str, current: str, feed_href: str) -> str:
    return wrap_site_page(
        title,
        description,
        main,
        prefix=prefix,
        current=current,
        feeds=[("蝴蝶日志", feed_href)],
    )


def render_tags(tags: list[str]) -> str:
    if not tags:
        return ""
    items = "".join(f'      <li>{html.escape(tag)}</li>\n' for tag in tags)
    return f'    <ul class="log-tags">\n{items}    </ul>'


def render_card(entry: dict, href: str, heading: str = "h3") -> str:
    date_zh = format_date_zh(entry["date"])
    tags = render_tags(entry["tags"])
    tag_block = f"\n{tags}" if tags else ""
    return f"""    <article class="log-card">
      <time datetime="{entry["date_str"]}">{html.escape(date_zh)}</time>
      <{heading}><a href="{html.escape(href)}">{html.escape(entry["title"])}</a></{heading}>
      <p>{html.escape(entry["summary"])}</p>{tag_block}
    </article>"""


def render_log_index(entries: list[dict]) -> str:
    if entries:
        cards = "\n".join(render_card(item, f"{item['date_str']}.html") for item in entries)
        listing = f'    <div class="log-card-list">\n{cards}\n    </div>'
    else:
        listing = '    <p class="prose">还没有写下日志。第一篇会出现在这里。</p>'
    main = f"""    <section class="log-hero" aria-label="开场">
      <p class="eyebrow">日志 · Flight Log</p>
      <h1>蝴蝶日志</h1>
      <p class="tagline">做完的事，就在这里轻轻记一笔。<br><span lang="en">A quiet record of work, one landing at a time.</span></p>
      <a class="scroll-hint" href="feed.xml">订阅 RSS</a>
    </section>

    <section class="section log-index-section">
      <div class="section-head">
        <p class="eyebrow">目录 · Timeline</p>
        <h2>按时间倒序</h2>
      </div>
{listing}
    </section>"""
    return wrap_page(
        "蝴蝶日志 · ButterFly",
        "ButterFly 的公开工作日记。做完的事，就在这里轻轻记一笔。",
        main,
        prefix="../",
        current="log",
        feed_href="feed.xml",
    )


def render_entry_page(entry: dict, previous: dict | None, nxt: dict | None) -> str:
    date_zh = format_date_zh(entry["date"])
    tags = render_tags(entry["tags"])
    tag_block = f"\n{tags}" if tags else ""
    nav_links: list[str] = []
    if previous:
        nav_links.append(
            f'<a class="log-adjacent" rel="prev" href="{previous["date_str"]}.html">'
            f'<span>上一篇</span>{html.escape(previous["title"])}</a>'
        )
    else:
        nav_links.append("<span></span>")
    if nxt:
        nav_links.append(
            f'<a class="log-adjacent" rel="next" href="{nxt["date_str"]}.html">'
            f'<span>下一篇</span>{html.escape(nxt["title"])}</a>'
        )
    else:
        nav_links.append("<span></span>")
    if previous or nxt:
        adjacent = (
            "      <nav class=\"log-adjacent-nav\" aria-label=\"相邻日志\">\n"
            f"        {nav_links[0]}\n"
            f"        {nav_links[1]}\n"
            "      </nav>"
        )
    else:
        adjacent = ""
    main = f"""    <article class="log-entry">
      <header class="log-entry-head">
        <p class="eyebrow"><a href="./">日志 · Flight Log</a></p>
        <h1>{html.escape(entry["title"])}</h1>
        <time datetime="{entry["date_str"]}">{html.escape(date_zh)}</time>{tag_block}
      </header>
      <div class="log-body prose">
{indent(entry["body_html"], 8)}
      </div>
{adjacent}
    </article>"""
    return wrap_page(
        f"{entry['title']} · 蝴蝶日志",
        entry["summary"],
        main,
        prefix="../",
        current="log",
        feed_href="feed.xml",
    )


def indent(text: str, spaces: int) -> str:
    pad = " " * spaces
    return "\n".join(pad + line if line else line for line in text.splitlines())


def render_recent(entries: list[dict]) -> str:
    latest = entries[:3]
    if not latest:
        inner = '        <p class="prose">还没有写下日志。</p>'
    else:
        cards = "\n".join(render_card(item, f"log/{item['date_str']}.html") for item in latest)
        # cards already start with 4-space indent; bump to 8 for homepage
        cards = "\n".join("    " + line if line else line for line in cards.splitlines())
        inner = f'        <div class="log-card-list">\n{cards}\n        </div>'
    return f"{RECENT_START}\n{inner}\n        {RECENT_END}"


def update_homepage(entries: list[dict]) -> None:
    text = HOME_PAGE.read_text(encoding="utf-8")
    start = text.find(RECENT_START)
    end = text.find(RECENT_END)
    if start == -1 or end == -1 or end < start:
        fail(f"{HOME_PAGE} is missing {RECENT_START} / {RECENT_END} markers")
    end += len(RECENT_END)
    updated = text[:start] + render_recent(entries) + text[end:]
    write_if_changed(HOME_PAGE, updated)


def render_feed(entries: list[dict]) -> str:
    latest = entries[0]["date"] if entries else datetime(2026, 11, 16, 0, 0, 0, tzinfo=TZ)
    items = []
    for entry in entries:
        link = f"{SITE}/log/{entry['date_str']}.html"
        description = html.escape(entry["summary"])
        items.append(
            f"""    <item>
      <title>{html.escape(entry["title"])}</title>
      <link>{link}</link>
      <guid isPermaLink="true">{link}</guid>
      <pubDate>{rfc822(entry["date"])}</pubDate>
      <description>{description}</description>
    </item>"""
        )
    item_xml = "\n".join(items)
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>蝴蝶日志 · Flight Log</title>
    <link>{SITE}/log/</link>
    <description>ButterFly 的公开工作日记。做完的事，就在这里轻轻记一笔。</description>
    <language>zh-Hans</language>
    <lastBuildDate>{rfc822(latest)}</lastBuildDate>
{item_xml}
  </channel>
</rss>
"""


def write_if_changed(path: Path, content: str) -> bool:
    if not content.endswith("\n"):
        content += "\n"
    if path.exists() and path.read_text(encoding="utf-8") == content:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return True


def remove_stale(valid_dates: set[str]) -> list[str]:
    removed = []
    if not LOG_DIR.is_dir():
        return removed
    for path in LOG_DIR.glob("*.html"):
        if DATE_RE.match(path.stem) and path.stem not in valid_dates:
            path.unlink()
            removed.append(path.name)
    return removed


def main() -> None:
    entries = load_entries()
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    changed = 0
    if write_if_changed(LOG_DIR / "index.html", render_log_index(entries)):
        changed += 1
    if write_if_changed(LOG_DIR / "feed.xml", render_feed(entries)):
        changed += 1

    # Entries are newest-first; previous is older, next is newer.
    for index, entry in enumerate(entries):
        newer = entries[index - 1] if index > 0 else None
        older = entries[index + 1] if index + 1 < len(entries) else None
        page = render_entry_page(entry, previous=older, nxt=newer)
        if write_if_changed(LOG_DIR / f"{entry['date_str']}.html", page):
            changed += 1

    before = HOME_PAGE.read_text(encoding="utf-8") if HOME_PAGE.exists() else ""
    update_homepage(entries)
    if HOME_PAGE.read_text(encoding="utf-8") != before:
        changed += 1

    removed = remove_stale({item["date_str"] for item in entries})
    print(
        f"build_log: {len(entries)} entries, "
        f"{changed} file(s) updated, {len(removed)} stale page(s) removed"
    )
    for name in removed:
        print(f"  removed log/{name}")


if __name__ == "__main__":
    main()

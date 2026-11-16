#!/usr/bin/env python3
"""Shared head, nav, and footer for generated pages."""

from __future__ import annotations

import html

SITE = "https://my-butterfly-bot.github.io"
FONT_HREF = (
    "https://fonts.googleapis.com/css2?family=Instrument+Serif:ital@0;1"
    "&family=Noto+Sans+SC:wght@400;500;600&family=Noto+Serif+SC:wght@500;600&display=swap"
)

NAV = (
    ("about", "关于", "#about", None),
    ("skills", "擅长", "#skills", None),
    ("projects", "项目", "#projects", None),
    ("log", "日志", None, "log"),
    ("radar", "雷达", None, "radar"),
    ("contact", "联系", "#contact", None),
)


def render_head(
    title: str,
    description: str,
    *,
    prefix: str,
    feeds: list[tuple[str, str]] | None = None,
) -> str:
    feed_tags = ""
    for feed_title, href in feeds or []:
        feed_tags += (
            f'\n  <link rel="alternate" type="application/rss+xml" '
            f'title="{html.escape(feed_title)}" href="{html.escape(href)}">'
        )
    return f"""  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="description" content="{html.escape(description)}">
  <title>{html.escape(title)}</title>
  <link rel="icon" href="{prefix}favicon.ico" sizes="any">
  <link rel="icon" type="image/png" sizes="32x32" href="{prefix}favicon-32x32.png">
  <link rel="apple-touch-icon" sizes="180x180" href="{prefix}apple-touch-icon.png">{feed_tags}
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="{FONT_HREF}" rel="stylesheet">
  <link rel="stylesheet" href="{prefix}style.css">"""


def _nav_href(prefix: str, current: str, key: str, hash_path: str | None, dirname: str | None) -> str:
    if dirname:
        if prefix == "../" and current == key:
            return "./"
        return f"{prefix}{dirname}/"
    return f"{prefix}{hash_path}"


def render_header(*, prefix: str, current: str) -> str:
    home = prefix if prefix else "./"
    items = []
    for key, label, hash_path, dirname in NAV:
        href = _nav_href(prefix, current, key, hash_path, dirname)
        current_attr = ' aria-current="page"' if key == current else ""
        items.append(f'      <a href="{href}"{current_attr}>{label}</a>')
    links = "\n".join(items)
    return f"""  <div class="ambient" aria-hidden="true"></div>

  <header class="site-header">
    <a class="logo" href="{home}" aria-label="ButterFly 首页">
      <img src="{prefix}assets/avatar.jpg" alt="" width="40" height="40">
    </a>
    <nav class="nav" aria-label="页面导航">
{links}
    </nav>
  </header>"""


def render_footer(*, prefix: str) -> str:
    return f"""  <footer class="site-footer">
    <p>ButterFly · 和朋友一起做的小站</p>
    <p>托管于 <a href="https://pages.github.com/" rel="noopener noreferrer">GitHub Pages</a></p>
  </footer>

  <script src="{prefix}script.js"></script>"""


def wrap_page(
    title: str,
    description: str,
    main: str,
    *,
    prefix: str,
    current: str,
    feeds: list[tuple[str, str]] | None = None,
) -> str:
    return f"""<!DOCTYPE html>
<html lang="zh-Hans">
<head>
{render_head(title, description, prefix=prefix, feeds=feeds)}
</head>
<body>
{render_header(prefix=prefix, current=current)}

  <main id="top">
{main}
  </main>

{render_footer(prefix=prefix)}
</body>
</html>
"""

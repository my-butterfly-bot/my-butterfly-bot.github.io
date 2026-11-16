#!/usr/bin/env python3
"""List GitHub candidates for Hidden Gems Radar.

Uses the GitHub Search API with GITHUB_TOKEN_BUTTERFLY (per-command header only;
the token is never printed). Writes a JSON shortlist of about 25 repos to stdout,
or to --output if given.

Usage:

    python3 scripts/radar_candidates.py
    python3 scripts/radar_candidates.py -o /tmp/radar-candidates.json
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
REVIEWED_PATH = ROOT / "radar" / "reviewed.json"
TZ = ZoneInfo("America/Los_Angeles")
API = "https://api.github.com"
OWNER_EXCLUDED = "my-butterfly-bot"
EXCLUDE_WORDS = ("awesome", "tutorial", "course", "homework", "template", "dotfiles")
SHORTLIST = 25
SEARCH_PAGE = 100


def fail(message: str, code: int = 1) -> None:
    print(f"radar_candidates: {message}", file=sys.stderr)
    sys.exit(code)


def load_reviewed() -> set[str]:
    if not REVIEWED_PATH.exists():
        return set()
    data = json.loads(REVIEWED_PATH.read_text(encoding="utf-8") or "[]")
    return {item.get("full_name", "") for item in data if item.get("full_name")}


def request_json(path_or_url: str, token: str, params: dict | None = None) -> tuple[object, dict]:
    if path_or_url.startswith("http"):
        url = path_or_url
    else:
        url = API + path_or_url
    if params:
        url += ("&" if "?" in url else "?") + urllib.parse.urlencode(params)
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "butterfly-hidden-gems-radar",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            headers = {k.lower(): v for k, v in resp.headers.items()}
            return json.load(resp), headers
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", "replace")[:400]
        fail(f"GitHub API HTTP {exc.code} for {urllib.parse.urlsplit(url).path}: {body}")
    except urllib.error.URLError as exc:
        fail(f"GitHub API request failed: {exc.reason}")
    raise AssertionError("unreachable")


def is_excluded(repo: dict, reviewed: set[str]) -> bool:
    if repo.get("fork") or repo.get("archived"):
        return True
    if repo.get("owner", {}).get("login") == OWNER_EXCLUDED:
        return True
    full_name = repo.get("full_name") or ""
    if full_name in reviewed:
        return True
    if not repo.get("license"):
        return True
    hay = " ".join(
        [
            repo.get("name") or "",
            full_name,
            repo.get("description") or "",
            " ".join(repo.get("topics") or []),
        ]
    ).lower()
    return any(word in hay for word in EXCLUDE_WORDS)


def readme_length(full_name: str, token: str) -> int:
    try:
        data, _ = request_json(f"/repos/{full_name}/readme", token)
    except SystemExit:
        # request_json exits on any HTTP error; treat missing readme as 0
        # by using a lighter probe here instead.
        raise
    return int(data.get("size") or 0)


def readme_length_soft(full_name: str, token: str) -> int:
    url = API + f"/repos/{full_name}/readme"
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "butterfly-hidden-gems-radar",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.load(resp)
            return int(data.get("size") or 0)
    except urllib.error.HTTPError as exc:
        if exc.code in {404, 403}:
            return 0
        body = exc.read().decode("utf-8", "replace")[:400]
        fail(f"GitHub API HTTP {exc.code} for /repos/{full_name}/readme: {body}")
    except urllib.error.URLError as exc:
        fail(f"GitHub API request failed: {exc.reason}")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="List Hidden Gems Radar candidates.")
    parser.add_argument("-o", "--output", help="Write JSON to this file instead of stdout.")
    parser.add_argument(
        "-n",
        "--count",
        type=int,
        default=SHORTLIST,
        help="Shortlist size (default: 25).",
    )
    args = parser.parse_args()

    token = os.environ.get("GITHUB_TOKEN_BUTTERFLY", "")
    if not token:
        fail("GITHUB_TOKEN_BUTTERFLY is not set")

    today = datetime.now(TZ).date()
    pushed_since = (today - timedelta(days=90)).isoformat()
    created_since = (today - timedelta(days=365)).isoformat()
    query = (
        f"stars:20..499 pushed:>={pushed_since} created:>={created_since} "
        "fork:false archived:false"
    )

    data, _headers = request_json(
        "/search/repositories",
        token,
        params={"q": query, "sort": "updated", "order": "desc", "per_page": str(SEARCH_PAGE)},
    )
    reviewed = load_reviewed()
    filtered = [repo for repo in data.get("items") or [] if not is_excluded(repo, reviewed)]

    shortlist = []
    for repo in filtered[: args.count]:
        license_info = repo.get("license") or {}
        shortlist.append(
            {
                "full_name": repo.get("full_name"),
                "html_url": repo.get("html_url"),
                "stars": repo.get("stargazers_count"),
                "description": repo.get("description") or "",
                "language": repo.get("language"),
                "pushed_at": repo.get("pushed_at"),
                "created_at": repo.get("created_at"),
                "license": license_info.get("spdx_id") or license_info.get("name"),
                "readme_length": readme_length_soft(repo["full_name"], token),
            }
        )

    payload = {
        "date": today.isoformat(),
        "query": query,
        "search_total": data.get("total_count"),
        "filtered": len(filtered),
        "count": len(shortlist),
        "candidates": shortlist,
    }
    text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
        print(f"radar_candidates: wrote {len(shortlist)} candidates to {args.output}", file=sys.stderr)
    else:
        sys.stdout.write(text)


if __name__ == "__main__":
    main()

#!/usr/bin/env bash
# Rebuild the flight log, commit, and push to main.
# Usage (from the repository root or any directory):
#   bash scripts/publish_log.sh "Add flight log for YYYY-MM-DD"
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

python3 scripts/build_log.py

git add -- "log" "index.html" "scripts/build_log.py" "scripts/publish_log.sh"
# Include deletions of stale generated pages.
git add -u -- "log"

if git diff --cached --quiet; then
  echo "publish_log: no changes to publish."
  exit 0
fi

MSG="${1:-Update flight log}"
git -c user.name="ButterFly" -c user.email="357408157+my-butterfly-bot@users.noreply.github.com" commit -m "$MSG"

if [[ -z "${GITHUB_TOKEN_BUTTERFLY:-}" ]]; then
  echo "publish_log: committed locally, but GITHUB_TOKEN_BUTTERFLY is not set, so nothing was pushed." >&2
  exit 1
fi

GIT_TERMINAL_PROMPT=0 git -c credential.helper= push \
  "https://x-access-token:${GITHUB_TOKEN_BUTTERFLY}@github.com/my-butterfly-bot/my-butterfly-bot.github.io.git" \
  main

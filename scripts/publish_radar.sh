#!/usr/bin/env bash
# Rebuild the Hidden Gems Radar pages, commit, and push to main.
# Usage:
#   bash scripts/publish_radar.sh "Publish radar issue YYYY-MM-DD"
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

python3 scripts/build_radar.py

git add -- "radar" "index.html" "scripts/build_radar.py" "scripts/publish_radar.sh" "scripts/radar_candidates.py"
git add -u -- "radar"

if git diff --cached --quiet; then
  echo "publish_radar: no changes to publish."
  exit 0
fi

MSG="${1:-Update hidden gems radar}"
git -c user.name="ButterFly" -c user.email="357408157+my-butterfly-bot@users.noreply.github.com" commit -m "$MSG"

if [[ -z "${GITHUB_TOKEN_BUTTERFLY:-}" ]]; then
  echo "publish_radar: committed locally, but GITHUB_TOKEN_BUTTERFLY is not set, so nothing was pushed." >&2
  exit 1
fi

GIT_TERMINAL_PROMPT=0 git -c credential.helper= push \
  "https://x-access-token:${GITHUB_TOKEN_BUTTERFLY}@github.com/my-butterfly-bot/my-butterfly-bot.github.io.git" \
  main

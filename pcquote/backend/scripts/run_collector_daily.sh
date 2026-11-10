#!/bin/zsh
# Nightly collection with the Python collector (run by the LaunchAgent at 00:00 Asia/Seoul after cutover).
#   scripts/run_collector_daily.sh [--check] [--force]
set -eu
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$HOME/.local/bin"
export TZ="Asia/Seoul"
cd "$(dirname "$0")/.."
exec uv run python -m pcquote.collector daily "$@"

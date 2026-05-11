#!/usr/bin/env bash
# Redundant session-beacon writer — wired as a Stop hook so it fires after
# every assistant turn. Appends one line to docs/memory/.session-beacons.log
# containing: UTC timestamp, current commit SHA, and working-tree dirty/clean.
#
# Purpose: when SessionEnd's memory-keeper agent fails to fire (the failure
# mode that wiped daily notes for 12 of 14 projects across 2026-05-07 to
# 2026-05-10), the beacon log is the secondary trail proving the session
# happened and what state it left the repo in. Backfilling a missed daily
# note from git log + beacon log is bounded and mechanical.
#
# Design notes:
# - Worktree-safe: uses `git rev-parse --git-dir` instead of `[[ -d .git ]]`
#   because in worktrees `.git` is a file, not a directory.
# - Dedupes consecutive identical entries (same sha + same dirty/clean state)
#   to keep the log readable across long sessions where Stop fires N times
#   without state changes between turns.
# - Log is gitignored (see docs/memory/.gitignore) — local-only signal.

set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$repo_root"

# Worktree-safe git repo check.
git rev-parse --git-dir >/dev/null 2>&1 || exit 0
[[ -d docs/memory ]] || exit 0

log_file="docs/memory/.session-beacons.log"
ts=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
sha=$(git rev-parse --short HEAD 2>/dev/null || echo "no-sha")

# Single-call status check (no race between three subprocesses).
if [[ -z "$(git status --porcelain 2>/dev/null)" ]]; then
  state="clean"
else
  state="dirty"
fi

# Dedupe: skip if the last line has the same sha+state.
if [[ -f "$log_file" ]]; then
  last=$(tail -n 1 "$log_file" 2>/dev/null || true)
  if [[ -n "$last" ]] && echo "$last" | grep -q " ${sha} ${state}\$"; then
    exit 0
  fi
fi

echo "${ts} ${sha} ${state}" >> "$log_file"
exit 0

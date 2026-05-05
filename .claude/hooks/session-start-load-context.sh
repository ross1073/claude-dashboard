#!/usr/bin/env bash
# Auto-loads project brief and status into the Claude Code session
# as additional SessionStart context.
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$repo_root"

brief="docs/project-brief.md"
status="docs/status.md"

echo "## Project state (auto-loaded at session start)"
echo

echo "### Brief"
if [[ -f "$brief" ]]; then
  cat "$brief"
else
  echo "_(missing: $brief)_"
fi
echo

echo "### Status"
if [[ -f "$status" ]]; then
  cat "$status"
else
  echo "_(missing: $status)_"
fi
echo

echo "### Loaded at"
date -u +"%Y-%m-%dT%H:%M:%SZ"

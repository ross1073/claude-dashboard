#!/usr/bin/env bash
# Auto-loads user profile, project brief, recent daily notes, and current
# stage doc (if present) into the Claude Code session as additional
# SessionStart context.
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$repo_root"

user_md="$HOME/.claude/user.md"
brief="docs/project-brief.md"
memory_dir="docs/memory"
stage="docs/stage-current.md"

echo "## Project state (auto-loaded at session start)"
echo

echo "### Operator (user.md)"
if [[ -f "$user_md" ]]; then
  cat "$user_md"
else
  echo "_(missing: ~/.claude/user.md)_"
fi
echo

echo "### Brief"
if [[ -f "$brief" ]]; then
  cat "$brief"
else
  echo "_(missing: $brief)_"
fi
echo

echo "### Recent daily notes"
if [[ -d "$memory_dir" ]]; then
  # Two most recent dated notes (today + most recent prior date)
  recent=$(ls -1 "$memory_dir"/*.md 2>/dev/null | sort -r | head -2)
  if [[ -z "$recent" ]]; then
    echo "_(no entries in $memory_dir yet)_"
  else
    while IFS= read -r f; do
      [[ -z "$f" ]] && continue
      echo "#### $(basename "$f")"
      cat "$f"
      echo
    done <<< "$recent"
  fi
else
  echo "_(missing: $memory_dir)_"
fi
echo

echo "### Active stage"
if [[ -f "$stage" ]]; then
  cat "$stage"
else
  echo "None active."
fi
echo

echo "### Loaded at"
date -u +"%Y-%m-%dT%H:%M:%SZ"

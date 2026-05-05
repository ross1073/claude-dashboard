#!/usr/bin/env bash
# Dispatches the memory-keeper agent at SessionEnd to fold this
# session's decisions into docs/status.md. The hook is wired as
# type:agent in .claude/settings.json; this script is the
# command-mode fallback / explicit invocation path.
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$repo_root"

if command -v claude >/dev/null 2>&1; then
  claude --agent memory-keeper --print \
    "Run your standard SessionEnd update against docs/status.md." \
    2>/dev/null || true
fi

exit 0

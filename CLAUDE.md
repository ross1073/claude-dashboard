# Claude Dashboard

Personal dashboard that visualises Claude Code usage (local JSONL transcripts
in `~/.claude/projects/`) plus org-wide spend from the Anthropic Admin API.
Local-first Python launcher → static `web/` page → optional Netlify snapshot.

See `docs/project-brief.md` for layout, stack, and conventions.

## Memory system

The project brief and `docs/status.md` auto-load into context via a SessionStart hook (`.claude/hooks/session-start-load-context.sh`). Status updates are written by the SessionEnd memory-keeper agent (`.claude/agents/memory-keeper.md`) — it folds each session's decisions, closures, and new open items into `docs/status.md` directly. `/audit-brief` is the manual drift check that compares the brief against the codebase and writes a severity-tagged findings file under `docs/audits/`.

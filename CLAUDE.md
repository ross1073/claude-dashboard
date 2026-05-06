# Claude Dashboard

Personal dashboard that visualises Claude Code usage (local JSONL transcripts
in `~/.claude/projects/`) plus org-wide spend from the Anthropic Admin API.
Local-first Python launcher → static `web/` page → optional Netlify snapshot.

See `docs/project-brief.md` for layout, stack, and conventions.

## Memory system

The user profile (`~/.claude/user.md`), project brief, and the two most recent daily notes from `docs/memory/` auto-load into context via a SessionStart hook (`.claude/hooks/session-start-load-context.sh`); `docs/stage-current.md` loads too when present. Daily notes are written by the SessionEnd memory-keeper agent (`.claude/agents/memory-keeper.md`) — it appends a timestamped session block to `docs/memory/<YYYY-MM-DD>.md`, never overwriting prior days. The retired `docs/status.md` rolling file was migrated into the first dated note. `/audit-brief` is the manual drift check that compares the brief against the codebase and writes a severity-tagged findings file under `docs/audits/`.
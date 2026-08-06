# Claude Dashboard

Personal dashboard that visualises Claude Code usage (local JSONL transcripts
in `~/.claude/projects/`) plus org-wide spend from the Anthropic Admin API.
Local-first Python launcher → static `web/` page → optional Netlify snapshot.

See `docs/project-brief.md` for layout, stack, and conventions.

## Memory system

Context auto-loads at SessionStart via four **global** hooks, `~/.claude/hooks/project-context-load-1..4.sh` (1 = time anchor + `docs/stage-current.md`, 2 = `docs/project-brief.md`, 3 = the per-project `MEMORY.md` index, 4 = recent `docs/memory/` daily notes — two if both fit, else the newest); the user profile (`~/.claude/user.md`) comes from a separate global hook, `memory-load.sh`. The ~10,000-byte SessionStart cap is **per hook, not per session**, so each part holds itself under 9,000 bytes and truncates an oversized file with a marker naming it and its full size — the rest is still on disk, never dropped to a pointer. More context means adding a part, never growing one. The repo-local `.claude/hooks/session-start-load-context.sh` was retired 2026-07-30 (unregistered, kept on disk with a dated header); it had no budget logic at all. Daily notes are written by the SessionEnd memory-keeper agent (`.claude/agents/memory-keeper.md`) — it appends a timestamped session block to `docs/memory/<YYYY-MM-DD>.md`, never overwriting prior days. The retired `docs/status.md` rolling file was migrated into the first dated note. `/audit-brief` is the manual drift check that compares the brief against the codebase and writes a severity-tagged findings file under `docs/audits/`.


<!-- BRAIN-MANIFEST-START -->
## Brain library manifest

Generated 2026-08-06 by ~/projects/brain/scripts/manifest.py. Do not hand-edit — this block is regenerated in place. Read these with `/load`.

_No library files currently match Claude Dashboard by entity._

Library root: ~/projects/brain/
<!-- BRAIN-MANIFEST-END -->

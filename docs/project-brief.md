# Claude Dashboard — project brief

## What this project is

A personal, local-first dashboard for "looking inside Claude" — it visualises
Ross's Claude Code usage (every session JSONL in `~/.claude/projects/`) plus
org-wide spend pulled from the Anthropic Admin API. Read-only introspection:
how much, on what, at what cost, with what models, on which projects.

Runs as a Python launcher (`dashboard.py`) that walks the local JSONL
transcripts, computes ~20 widgets of stats into `web/data.json`, and serves
the static `web/` page on `http://localhost:8765`. The same `web/` directory
is published to Netlify by `refresh.sh` (driven by a LaunchAgent outside the
repo) so the snapshot can be read from a phone.

## How it's structured

```
dashboard.py                # entrypoint: collect → serve → open browser
collector/
  jsonl_parser.py           # walks ~/.claude/projects, parses session JSONL (with .cache/)
  aggregator.py             # computes per-widget data
  admin_api.py              # Anthropic Admin API client (org-wide spend)
  pricing.py                # per-model $/Mtoken table — bump when prices change
  collect.py                # orchestrator → web/data.json
web/
  index.html                # widget layout
  styles.css                # "Dark Arcade" theme
  app.js                    # Chart.js renderers (CDN)
  data.json                 # generated artifact (committed for Netlify)
.cache/                     # per-jsonl parse cache, gitignored
config.json                 # local Admin API key + prefs, gitignored
config.example.json         # template for config.json
refresh.sh                  # LaunchAgent target: collect + netlify deploy --prod
netlify.toml                # publish = "web", no build command
docs/
  project-brief.md          # this file
  stage-current.md          # active focus, auto-loaded into sessions
  memory/<YYYY-MM-DD>.md    # daily notes written by SessionEnd memory-keeper
.claude/
  agents/memory-keeper.md   # SessionEnd agent that appends daily notes
  commands/                 # /audit-brief, /audit-memory
  hooks/                    # SessionStart context loader, SessionEnd memory keeper, beacon
```

Stack:
- Python 3, standard library only — `urllib` for the Admin API, `http.server`
  for serving. `requirements.txt` exists as a marker; it installs nothing.
- Static frontend: HTML + CSS + JS, no framework, no build step. Chart.js
  loaded from CDN by `web/index.html`.
- Netlify for the public snapshot (`netlify.toml` publishes `web/`, no build).
- LaunchAgent (not in repo) drives `refresh.sh` for the auto-redeploy —
  UNKNOWN — needs Ross to fill in the exact schedule / plist path.

## Conventions

- No third-party Python deps. If something needs `pip install`, reconsider.
- Admin API key lives only in `config.json` (gitignored). Never written into
  `web/data.json` or any public artifact.
- Pricing changes: edit `collector/pricing.py`. Local cost numbers are
  estimates for the slices the Admin API doesn't itemise; the Admin panel
  itself shows real billed amounts.
- Two billing modes set in `config.json`: `subscription` (reframes tiles as
  API-equivalent value vs flat plan fee) or `api` (real per-request spend).
- `dashboard.py --no-collect` serves stale `web/data.json`; `--no-admin`
  skips the Admin API fetch; `--no-browser` for headless runs; `--port N`
  overrides the default 8765.
- Auto-refresh path is `refresh.sh` → `python3 -m collector.collect` →
  `netlify deploy --dir=web --prod --no-build`. The script's working
  directory is hard-coded.
- The JSONL parser caches per-file under `.cache/` keyed off file
  identity/mtime — invalidate the cache if you change parser semantics.
- `web/data.json` is the only contract between collector and frontend. New
  widgets need both a producer (in `aggregator.py`) and a consumer
  (in `app.js` + `index.html`).
- Netlify deploys publish `web/` exactly as it sits on disk, so
  `web/data.json` must exist and be current before deploy.
- The repo is small and personal. Keep it boring.

## Memory system

The user profile (`~/.claude/user.md`), project brief, and the two most recent daily notes from `docs/memory/` auto-load into context via a SessionStart hook (`.claude/hooks/session-start-load-context.sh`); `docs/stage-current.md` loads too when present. Daily notes are written by the SessionEnd memory-keeper agent (`.claude/agents/memory-keeper.md`) — it appends a timestamped session block to `docs/memory/<YYYY-MM-DD>.md`, never overwriting prior days. The retired `docs/status.md` rolling file was migrated into the first dated note. `/audit-brief` is the manual drift check that compares the brief against the codebase and writes a severity-tagged findings file under `docs/audits/`.

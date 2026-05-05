# Claude Dashboard — project brief

## Purpose

Personal dashboard for "looking inside Claude" — visualises Ross's Claude Code
usage (every session in `~/.claude/projects/**/*.jsonl`) plus org-wide spend
from the Anthropic Admin API. Read-only introspection: how much, on what, at
what cost, with what models, on which projects.

Local-first: a Python launcher walks the JSONL transcripts, computes ~20
widgets of stats, writes `web/data.json`, and serves a static page on
`http://localhost:8765`. The same `web/` directory is also published to
Netlify by `refresh.sh` on a twice-daily LaunchAgent so Ross can read the
snapshot from his phone.

## Stack

- Python 3, standard library only (no `requirements.txt` deps — `urllib` for
  the Admin API, `http.server` for serving). The `requirements.txt` file is a
  marker; it installs nothing.
- Static frontend: HTML + CSS + JS, no framework, no build step. Charts via
  Chart.js (loaded from CDN by `web/index.html`).
- Netlify for the public snapshot (`netlify.toml` publishes `web/`, no build).
- LaunchAgent (not in repo) drives `refresh.sh` for the auto-redeploy.

## Layout

```
dashboard.py                # entrypoint: collect → serve → open browser
collector/
  jsonl_parser.py           # walks ~/.claude/projects, parses session JSONL
  aggregator.py             # computes per-widget data
  admin_api.py              # Anthropic Admin API client (org-wide spend)
  pricing.py                # per-model $/Mtoken table — bump when prices change
  collect.py                # orchestrator → web/data.json
web/
  index.html                # widget layout
  styles.css                # "Dark Arcade" theme
  app.js                    # Chart.js renderers
  data.json                 # generated artifact (committed for Netlify)
.cache/                     # per-jsonl parse cache, gitignored
config.json                 # local Admin API key + prefs, gitignored
config.example.json         # template for config.json
refresh.sh                  # LaunchAgent target: collect + netlify deploy --prod
netlify.toml                # publish = "web", no build command
```

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
  skips the Admin API fetch; `--no-browser` for headless runs.
- Auto-refresh path is `refresh.sh` → `python3 -m collector.collect` →
  `netlify deploy --dir=web --prod --no-build`. That script's working
  directory is hard-coded.

## Things to know before editing

- The JSONL parser caches per-file under `.cache/` keyed off file
  identity/mtime — invalidate the cache if you change parser semantics.
- `web/data.json` is the only contract between collector and frontend. New
  widgets need both a producer (in `aggregator.py`) and a consumer
  (in `app.js` + `index.html`).
- Netlify deploys publish `web/` exactly as it sits on disk, so
  `web/data.json` must exist and be current before deploy.
- The repo is small and personal. Keep it boring.

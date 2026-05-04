# Claude Dashboard

A personal dashboard for "looking inside Claude" — visualizes your Claude Code
usage (every session in `~/.claude/projects/`) plus org-wide spend from the
Anthropic Admin API.

Runs locally as a static web page. Zero build step, no framework.

## Quick start

```bash
python dashboard.py
```

That's it. The script:

1. Walks `~/.claude/projects/**/*.jsonl` and computes ~20 widgets' worth of stats.
2. Starts `http.server` on `http://localhost:8765`.
3. Opens your browser.

Re-run any time to refresh.

## Optional: Anthropic Admin API

To unlock the org-wide spend panel ("Claude Code vs direct API", per-key usage):

1. Visit <https://console.anthropic.com/settings/admin-keys> and create an
   Admin API key (starts with `sk-ant-admin...`). Org owners only.
2. Copy `config.example.json` to `config.json` and paste the key:

   ```json
   { "admin_api_key": "sk-ant-admin-...", "admin_window_days": 90 }
   ```

3. Re-run `python dashboard.py`. The "API (org-wide)" section will now populate.

`config.json` is gitignored — the key never leaves your machine. To skip the
admin fetch on a particular run: `python dashboard.py --no-admin`.

## Useful flags

```bash
python dashboard.py --no-collect    # serve existing data.json, skip refresh
python dashboard.py --no-admin      # local logs only
python dashboard.py --no-browser    # don't auto-open
python dashboard.py --port 8000     # custom port
```

## Static export (view from your phone)

Everything in `web/` is static HTML/CSS/JS + the generated `data.json`. To
publish:

1. Run `python dashboard.py --no-browser` to generate fresh `data.json`.
2. Drag the `web/` folder onto <https://app.netlify.com/drop>.
3. Open the URL on your phone.

The exported snapshot is read-only. The Admin API key never appears in `web/` —
it lives only in your local `config.json`.

## Project layout

```
dashboard.py              # launcher
collector/
  jsonl_parser.py         # walks ~/.claude/projects, parses events
  aggregator.py           # computes per-widget data
  admin_api.py            # Anthropic Admin API client
  pricing.py              # per-model $/Mtoken table  ← update when prices change
  collect.py              # orchestrator → web/data.json
web/
  index.html              # widget layout
  styles.css              # Dark Arcade theme
  app.js                  # Chart.js renderers
  data.json               # generated
.cache/                   # per-jsonl-file parse cache (gitignored)
config.json               # admin API key + prefs (gitignored)
```

## Updating model prices

Anthropic occasionally adjusts prices. Edit `collector/pricing.py` to keep
local cost estimates accurate. (The Admin API panel shows the actual billed
amount — local estimates are for the parts the Admin API doesn't break down.)

## Why all this?

Curiosity. The data is sitting on your disk; this just visualizes it.

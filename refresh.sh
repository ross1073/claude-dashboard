#!/bin/bash
# Run by LaunchAgent twice daily: collect fresh data, redeploy to Netlify.
set -e
cd "/Users/rosswalker/projects/Claude Dashboard"

/usr/bin/env python3 -m collector.collect

/Users/rosswalker/.nvm/versions/node/v24.14.0/bin/netlify deploy \
  --dir=web --prod --no-build \
  --message="auto refresh $(date -u +%Y-%m-%dT%H:%MZ)"

"""Entry point. Run me to refresh data.json."""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

from .jsonl_parser import parse_all
from .aggregator import aggregate
from . import admin_api

ROOT = Path(__file__).resolve().parent.parent
WEB_DIR = ROOT / "web"
DATA_PATH = WEB_DIR / "data.json"
CACHE_DIR = ROOT / ".cache"
CONFIG_PATH = ROOT / "config.json"


def _print_progress(done: int, total: int):
    bar = int(done / max(total, 1) * 30)
    sys.stdout.write(f"\r  parsing logs  [{'█'*bar}{' '*(30-bar)}] {done}/{total}")
    sys.stdout.flush()


def load_config() -> dict:
    if not CONFIG_PATH.exists():
        return {}
    try:
        return json.loads(CONFIG_PATH.read_text())
    except Exception:
        return {}


def main(skip_admin: bool = False) -> Path:
    t0 = time.time()
    print("Claude Dashboard — collecting…")

    print("→ Local Claude Code logs")
    events = parse_all(CACHE_DIR, on_progress=_print_progress)
    print(f"\n  {len(events):,} events from local logs")

    print("→ Aggregating widgets")
    data = aggregate(events)

    cfg = load_config()
    admin_summary = None
    admin_error = None
    key = (cfg.get("admin_api_key") or "").strip()
    if key and not skip_admin:
        print("→ Anthropic Admin API")
        try:
            window = int(cfg.get("admin_window_days", 90))
            raw = admin_api.fetch(key, days=window)
            admin_summary = admin_api.summarize(raw)
            print(f"  fetched {window}-day usage + cost report")
        except Exception as e:
            admin_error = str(e)
            print(f"  ! admin API failed: {e}")
    elif not key:
        print("→ Skipping Admin API (no key in config.json)")

    data["admin"] = admin_summary
    data["admin_error"] = admin_error
    data["billing"] = {
        "mode": (cfg.get("billing_mode") or "api").lower(),
        "subscription_usd_per_month": float(cfg.get("subscription_usd_per_month", 0) or 0),
    }

    WEB_DIR.mkdir(parents=True, exist_ok=True)
    DATA_PATH.write_text(json.dumps(data, default=str))
    dt = time.time() - t0
    size_kb = DATA_PATH.stat().st_size / 1024
    print(f"✓ wrote {DATA_PATH.relative_to(ROOT)}  ({size_kb:.1f} KB) in {dt:.1f}s")
    return DATA_PATH


if __name__ == "__main__":
    main(skip_admin="--no-admin" in sys.argv)

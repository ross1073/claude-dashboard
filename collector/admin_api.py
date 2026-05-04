"""Anthropic Admin API client. Pulls usage and cost reports.

Reference: https://docs.anthropic.com/en/api/admin-api/usage-cost
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from urllib import request, parse, error
import json

BASE = "https://api.anthropic.com"
VERSION = "2023-06-01"


def _get(path: str, params: dict, key: str) -> dict:
    qs = parse.urlencode(params, doseq=True)
    url = f"{BASE}{path}?{qs}"
    req = request.Request(url, headers={
        "x-api-key": key,
        "anthropic-version": VERSION,
        "content-type": "application/json",
    })
    with request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _paginate(path: str, params: dict, key: str) -> list[dict]:
    out: list[dict] = []
    cursor = None
    while True:
        p = dict(params)
        if cursor:
            p["page"] = cursor
        try:
            d = _get(path, p, key)
        except error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Admin API {path} → {e.code}: {body}") from None
        items = d.get("data", [])
        out.extend(items)
        cursor = d.get("next_page")
        if not cursor:
            break
    return out


def fetch(api_key: str, days: int = 90) -> dict[str, Any]:
    """Pull usage + cost rollups for the last `days` days."""
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=days)
    iso = lambda d: d.strftime("%Y-%m-%dT%H:%M:%SZ")

    usage_params = {
        "starting_at": iso(start),
        "ending_at":   iso(end),
        "bucket_width": "1d",
        "limit": 1000,
    }
    cost_params = {
        "starting_at": iso(start),
        "ending_at":   iso(end),
        "bucket_width": "1d",
        "limit": 1000,
    }

    usage_buckets = _paginate("/v1/organizations/usage_report/messages", usage_params, api_key)
    cost_buckets  = _paginate("/v1/organizations/cost_report",            cost_params,  api_key)

    return {
        "fetched_at": iso(end),
        "window_days": days,
        "usage": usage_buckets,
        "cost": cost_buckets,
    }


def summarize(admin_data: dict) -> dict:
    """Reshape Admin API output into chart-ready series."""
    daily_cost: dict[str, float] = {}
    by_workspace: dict[str, float] = {}
    by_api_key: dict[str, float] = {}
    by_model: dict[str, float] = {}

    for bucket in admin_data.get("cost", []):
        day = bucket.get("starting_at", "")[:10]
        for r in bucket.get("results", []):
            amount = float((r.get("amount") or {}).get("amount", 0))
            daily_cost[day] = daily_cost.get(day, 0.0) + amount
            ws = r.get("workspace_id") or "default"
            by_workspace[ws] = by_workspace.get(ws, 0.0) + amount
            mk = r.get("model") or "unknown"
            by_model[mk] = by_model.get(mk, 0.0) + amount

    for bucket in admin_data.get("usage", []):
        for r in bucket.get("results", []):
            ak = r.get("api_key_id") or "unknown"
            tokens = int(r.get("uncached_input_tokens", 0)) \
                   + int(r.get("output_tokens", 0)) \
                   + int(r.get("cache_creation_input_tokens", 0)) \
                   + int(r.get("cache_read_input_tokens", 0))
            by_api_key[ak] = by_api_key.get(ak, 0) + tokens

    return {
        "fetched_at": admin_data.get("fetched_at"),
        "window_days": admin_data.get("window_days"),
        "daily_cost": [{"date": d, "cost": round(v, 4)} for d, v in sorted(daily_cost.items())],
        "by_workspace": by_workspace,
        "by_api_key": by_api_key,
        "by_model": by_model,
        "total_cost": round(sum(daily_cost.values()), 4),
    }

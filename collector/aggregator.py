"""Compute every widget's data structure from the flat event list."""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any


def _parse_ts(s: str) -> datetime | None:
    if not s:
        return None
    try:
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        return datetime.fromisoformat(s).astimezone(timezone.utc)
    except Exception:
        return None


def _day_key(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d")


def aggregate(events: list[dict]) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    today = _day_key(now)
    week_start = now - timedelta(days=7)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    daily_cost: dict[str, float] = defaultdict(float)
    daily_in: dict[str, int] = defaultdict(int)
    daily_out: dict[str, int] = defaultdict(int)
    daily_cache_read: dict[str, int] = defaultdict(int)
    daily_cache_create: dict[str, int] = defaultdict(int)

    cost_by_family: dict[str, float] = defaultdict(float)
    tokens_by_family: dict[str, int] = defaultdict(int)
    cost_by_project: dict[str, float] = defaultdict(float)
    cost_by_model_full: dict[str, float] = defaultdict(float)

    tool_counts: Counter = Counter()
    subagent_counts: Counter = Counter()
    error_count = 0
    error_by_tool: Counter = Counter()
    last_error_examples: list[dict] = []

    sessions: dict[str, dict] = {}
    skill_counts: Counter = Counter()
    user_prompt_lens: list[int] = []
    longest_prompt = 0

    activity_hour_day: Counter = Counter()  # (dow, hour) -> count of assistant messages

    spend_today = 0.0
    spend_week = 0.0
    spend_month = 0.0
    tokens_today_in = 0
    tokens_today_out = 0
    cache_read_today = 0
    cache_create_today = 0

    total_cost = 0.0
    total_in = 0
    total_out = 0
    total_cache_read = 0
    total_cache_create = 0

    SKILL_RE_NEEDLES = ("superpowers:", "skill:", "Skill:")  # crude

    for ev in events:
        ts = _parse_ts(ev.get("timestamp") or "")
        if not ts:
            continue
        d = _day_key(ts)
        cost = float(ev.get("cost_usd") or 0)
        in_t = int(ev.get("input_tokens") or 0)
        out_t = int(ev.get("output_tokens") or 0)
        cr_t = int(ev.get("cache_read_tokens") or 0)
        cw_t = int(ev.get("cache_create_tokens") or 0)
        family = ev.get("family") or "other"
        model = ev.get("model")
        project = ev.get("project") or "unknown"
        sid = ev.get("session_id") or "?"

        # Sessions index
        s = sessions.setdefault(sid, {
            "session_id": sid,
            "project": project,
            "first_ts": ev["timestamp"],
            "last_ts": ev["timestamp"],
            "cost": 0.0,
            "messages": 0,
            "tools": 0,
            "models": Counter(),
            "tokens_in": 0,
            "tokens_out": 0,
            "errors": 0,
            "git_branch": ev.get("git_branch"),
        })
        if ev["timestamp"] < s["first_ts"]:
            s["first_ts"] = ev["timestamp"]
        if ev["timestamp"] > s["last_ts"]:
            s["last_ts"] = ev["timestamp"]
        s["cost"] += cost
        s["tokens_in"] += in_t
        s["tokens_out"] += out_t
        if model:
            s["models"][model] += 1

        # Tallies that only apply to assistant turns with usage
        if ev.get("role") == "assistant" and (in_t or out_t or cr_t or cw_t):
            daily_cost[d] += cost
            daily_in[d] += in_t
            daily_out[d] += out_t
            daily_cache_read[d] += cr_t
            daily_cache_create[d] += cw_t

            cost_by_family[family] += cost
            tokens_by_family[family] += in_t + out_t
            cost_by_project[project] += cost
            if model:
                cost_by_model_full[model] += cost

            total_cost += cost
            total_in += in_t
            total_out += out_t
            total_cache_read += cr_t
            total_cache_create += cw_t

            if d == today:
                spend_today += cost
                tokens_today_in += in_t
                tokens_today_out += out_t
                cache_read_today += cr_t
                cache_create_today += cw_t
            if ts >= week_start:
                spend_week += cost
            if ts >= month_start:
                spend_month += cost

            activity_hour_day[(ts.weekday(), ts.hour)] += 1
            s["messages"] += 1

            for tn in (ev.get("tool_names") or []):
                tool_counts[tn] += 1
                s["tools"] += 1
                if tn == "Agent":
                    subagent_counts["Agent"] += 1
                if tn == "Skill":
                    skill_counts["(via Skill tool)"] += 1

            if ev.get("is_sidechain"):
                subagent_counts["sidechain"] += 1

        if ev.get("role") == "user":
            user_prompt_lens.append(int(ev.get("user_text_len") or 0))
            if (ev.get("user_text_len") or 0) > longest_prompt:
                longest_prompt = ev.get("user_text_len") or 0

        if ev.get("is_error"):
            error_count += 1
            s["errors"] += 1
            if ev.get("tool_name"):
                error_by_tool[ev["tool_name"]] += 1
            if len(last_error_examples) < 10:
                last_error_examples.append({
                    "session_id": sid, "project": project,
                    "timestamp": ev["timestamp"], "tool": ev.get("tool_name"),
                })

    # Build daily spend timeseries (last 90 days, dense)
    days = []
    for i in range(89, -1, -1):
        day = (now - timedelta(days=i)).strftime("%Y-%m-%d")
        days.append({
            "date": day,
            "cost": round(daily_cost.get(day, 0.0), 4),
            "input": daily_in.get(day, 0),
            "output": daily_out.get(day, 0),
            "cache_read": daily_cache_read.get(day, 0),
            "cache_create": daily_cache_create.get(day, 0),
        })

    # Burn rate: today's pace projected to month end
    days_in_month = (month_start.replace(month=month_start.month % 12 + 1, day=1) - timedelta(days=1)).day \
        if month_start.month != 12 else 31
    days_elapsed = max((now - month_start).days + (now.hour / 24), 1/24)
    projected_month = spend_month / days_elapsed * days_in_month

    # Recent sessions (50 most recent by last_ts)
    sess_list = list(sessions.values())
    for s in sess_list:
        s["model_top"] = s["models"].most_common(1)[0][0] if s["models"] else None
        s["models"] = dict(s["models"])
        ft = _parse_ts(s["first_ts"])
        lt = _parse_ts(s["last_ts"])
        s["duration_seconds"] = int((lt - ft).total_seconds()) if ft and lt else 0
    sess_list.sort(key=lambda x: x["last_ts"], reverse=True)
    recent = sess_list[:50]
    longest = sorted(sess_list, key=lambda x: x["duration_seconds"], reverse=True)[:10]
    most_expensive = sorted(sess_list, key=lambda x: x["cost"], reverse=True)[:10]

    # Personal records
    by_day_cost = defaultdict(float)
    by_day_msgs = defaultdict(int)
    for ev in events:
        ts = _parse_ts(ev.get("timestamp") or "")
        if not ts: continue
        if ev.get("role") == "assistant":
            by_day_cost[_day_key(ts)] += float(ev.get("cost_usd") or 0)
            by_day_msgs[_day_key(ts)] += 1
    most_expensive_day = max(by_day_cost.items(), key=lambda kv: kv[1], default=("—", 0.0))
    most_active_day = max(by_day_msgs.items(), key=lambda kv: kv[1], default=("—", 0))
    longest_session = longest[0] if longest else None

    # Activity heatmap (7x24)
    heatmap = [[activity_hour_day.get((dow, h), 0) for h in range(24)] for dow in range(7)]

    # Context window usage per session: max input_tokens across the session
    context_max_per_session = []
    for sid, s in sessions.items():
        max_in = 0
        # Use the rough proxy: max single-message input_tokens during session
        # (re-scan once; we already aggregated, so this is best-effort)
        # We'll just record total input_tokens for now in sess; richer per-msg
        # data would require keeping more state.
        max_in = s.get("tokens_in", 0)
        context_max_per_session.append(max_in)
    context_max_per_session.sort(reverse=True)

    # Avg / longest prompt
    avg_prompt = (sum(user_prompt_lens) / len(user_prompt_lens)) if user_prompt_lens else 0

    return {
        "generated_at": now.isoformat(),
        "totals": {
            "cost": round(total_cost, 4),
            "input_tokens": total_in,
            "output_tokens": total_out,
            "cache_read_tokens": total_cache_read,
            "cache_create_tokens": total_cache_create,
            "session_count": len(sessions),
            "event_count": len(events),
        },
        "spend_tiles": {
            "today": round(spend_today, 4),
            "week":  round(spend_week, 4),
            "month": round(spend_month, 4),
            "projected_month": round(projected_month, 4),
            "tokens_today_in": tokens_today_in,
            "tokens_today_out": tokens_today_out,
            "cache_read_today": cache_read_today,
            "cache_create_today": cache_create_today,
        },
        "daily": days,
        "cost_by_family": {k: round(v, 4) for k, v in cost_by_family.items()},
        "tokens_by_family": dict(tokens_by_family),
        "cost_by_model": {k: round(v, 4) for k, v in cost_by_model_full.items()},
        "cost_by_project": [
            {"project": k, "cost": round(v, 4)}
            for k, v in sorted(cost_by_project.items(), key=lambda kv: -kv[1])[:25]
        ],
        "tool_counts": dict(tool_counts.most_common(40)),
        "subagent_counts": dict(subagent_counts),
        "skill_counts": dict(skill_counts),
        "errors": {
            "count": error_count,
            "by_tool": dict(error_by_tool.most_common(10)),
            "recent_examples": last_error_examples,
        },
        "prompt_stats": {
            "count": len(user_prompt_lens),
            "avg_chars": round(avg_prompt, 1),
            "longest_chars": longest_prompt,
        },
        "recent_sessions": recent,
        "longest_sessions": longest,
        "most_expensive_sessions": most_expensive,
        "records": {
            "most_expensive_day": {"date": most_expensive_day[0], "cost": round(most_expensive_day[1], 4)},
            "most_active_day": {"date": most_active_day[0], "messages": most_active_day[1]},
            "longest_session": (
                {
                    "session_id": longest_session["session_id"],
                    "project": longest_session["project"],
                    "duration_seconds": longest_session["duration_seconds"],
                    "cost": round(longest_session["cost"], 4),
                } if longest_session else None
            ),
        },
        "activity_heatmap": heatmap,
        "context_distribution": {
            "p50": context_max_per_session[len(context_max_per_session)//2] if context_max_per_session else 0,
            "p90": context_max_per_session[int(len(context_max_per_session)*0.1)] if context_max_per_session else 0,
            "max": context_max_per_session[0] if context_max_per_session else 0,
        },
    }

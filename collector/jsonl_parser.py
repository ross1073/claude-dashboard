"""Walk ~/.claude/projects/**/*.jsonl and extract per-event records.

Each session log is parsed once and cached on disk by file mtime/size, so
re-runs are fast. The parser is forgiving: malformed lines are skipped with
a counter rather than aborting.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterator, Optional

from .pricing import cost_for, model_family

CLAUDE_HOME = Path.home() / ".claude" / "projects"


@dataclass
class Event:
    session_id: str
    project: str            # decoded cwd path
    timestamp: str          # ISO8601
    type: str               # "assistant", "user", "tool_result", "queue-operation", etc.
    role: Optional[str]     # for messages
    model: Optional[str]
    family: Optional[str]   # opus/sonnet/haiku
    input_tokens: int
    output_tokens: int
    cache_read_tokens: int
    cache_create_tokens: int
    cost_usd: float
    is_sidechain: bool
    is_error: bool
    tool_name: Optional[str]    # if assistant message contains tool_use blocks, first tool name
    tool_names: list            # all tool_use names in this message
    user_text_len: int          # chars in user prompt (0 for non-user)
    git_branch: Optional[str]


def _project_path(project_dir_name: str) -> str:
    """Claude Code encodes paths by replacing '/' with '-'. We can't perfectly
    reverse it (folders with '-' become ambiguous) but the leading '-Users-x'
    convention is fine to reverse.
    """
    if project_dir_name.startswith("-"):
        return "/" + project_dir_name[1:].replace("-", "/")
    return project_dir_name.replace("-", "/")


def _safe_int(d: dict, k: str) -> int:
    v = d.get(k, 0)
    return int(v) if isinstance(v, (int, float)) else 0


def _extract_tool_names(content) -> list:
    if not isinstance(content, list):
        return []
    return [b.get("name") for b in content
            if isinstance(b, dict) and b.get("type") == "tool_use" and b.get("name")]


def _user_text_len(content) -> int:
    if isinstance(content, str):
        return len(content)
    if isinstance(content, list):
        n = 0
        for b in content:
            if isinstance(b, dict) and b.get("type") == "text":
                n += len(b.get("text", "") or "")
            elif isinstance(b, str):
                n += len(b)
        return n
    return 0


def parse_line(raw: str, project: str) -> Optional[Event]:
    try:
        d = json.loads(raw)
    except Exception:
        return None
    if not isinstance(d, dict):
        return None

    typ = d.get("type", "")
    ts = d.get("timestamp", "")
    sid = d.get("sessionId", "") or d.get("session_id", "")
    is_side = bool(d.get("isSidechain", False))
    branch = d.get("gitBranch")

    msg = d.get("message") if isinstance(d.get("message"), dict) else {}
    role = msg.get("role")
    model = msg.get("model")
    usage = msg.get("usage") if isinstance(msg.get("usage"), dict) else {}
    content = msg.get("content")

    in_tok  = _safe_int(usage, "input_tokens")
    out_tok = _safe_int(usage, "output_tokens")
    cr_tok  = _safe_int(usage, "cache_read_input_tokens")
    cw_tok  = _safe_int(usage, "cache_creation_input_tokens")
    cost = cost_for(model, usage) if usage and model else 0.0

    is_err = False
    if typ == "user" and isinstance(content, list):
        # tool_result blocks ride inside user messages
        for b in content:
            if isinstance(b, dict) and b.get("type") == "tool_result" and b.get("is_error"):
                is_err = True
                break
    if msg.get("stop_reason") == "error":
        is_err = True

    tool_names = _extract_tool_names(content) if role == "assistant" else []
    user_len = _user_text_len(content) if role == "user" else 0

    return Event(
        session_id=sid,
        project=project,
        timestamp=ts,
        type=typ,
        role=role,
        model=model,
        family=model_family(model) if model else None,
        input_tokens=in_tok,
        output_tokens=out_tok,
        cache_read_tokens=cr_tok,
        cache_create_tokens=cw_tok,
        cost_usd=cost,
        is_sidechain=is_side,
        is_error=is_err,
        tool_name=tool_names[0] if tool_names else None,
        tool_names=tool_names,
        user_text_len=user_len,
        git_branch=branch,
    )


def iter_files(root: Path = CLAUDE_HOME) -> Iterator[Path]:
    if not root.exists():
        return
    for p in root.rglob("*.jsonl"):
        if p.is_file():
            yield p


def parse_file(path: Path) -> list[Event]:
    project = _project_path(path.parent.name)
    out: list[Event] = []
    try:
        with path.open("r", encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                ev = parse_line(line, project)
                if ev:
                    out.append(ev)
    except Exception:
        pass
    return out


def parse_all(cache_dir: Path, root: Path = CLAUDE_HOME, on_progress=None) -> list[dict]:
    """Parse every JSONL file under root, using a per-file cache keyed by
    (path, mtime, size). Returns a list of event dicts.
    """
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_index_path = cache_dir / "index.json"
    try:
        cache_index = json.loads(cache_index_path.read_text())
    except Exception:
        cache_index = {}

    new_index: dict = {}
    all_events: list[dict] = []
    files = list(iter_files(root))
    total = len(files)

    for i, f in enumerate(files):
        try:
            st = f.stat()
        except FileNotFoundError:
            continue
        key = str(f)
        sig = f"{st.st_mtime_ns}:{st.st_size}"
        cache_file = cache_dir / (str(abs(hash(key))) + ".json")

        cached = cache_index.get(key)
        if cached and cached.get("sig") == sig and cache_file.exists():
            try:
                events = json.loads(cache_file.read_text())
            except Exception:
                events = [asdict(e) for e in parse_file(f)]
                cache_file.write_text(json.dumps(events))
        else:
            events = [asdict(e) for e in parse_file(f)]
            cache_file.write_text(json.dumps(events))

        new_index[key] = {"sig": sig, "cache": cache_file.name, "count": len(events)}
        all_events.extend(events)

        if on_progress and (i % 25 == 0 or i == total - 1):
            on_progress(i + 1, total)

    # Garbage-collect stale cache files
    keep = {v["cache"] for v in new_index.values()}
    for stale in cache_dir.glob("*.json"):
        if stale.name == "index.json": continue
        if stale.name not in keep:
            try: stale.unlink()
            except OSError: pass

    cache_index_path.write_text(json.dumps(new_index))
    return all_events

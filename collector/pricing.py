"""Per-model pricing in USD per million tokens.

Update these when Anthropic changes prices. Used to estimate spend from local
Claude Code logs (Admin API gives the authoritative billed dollars).

Source: https://www.anthropic.com/pricing  (verify periodically)
"""

# (input, output, cache_read, cache_write_5m) per 1M tokens
PRICING = {
    # Claude 4 family
    "claude-opus-4":         (15.00, 75.00, 1.50, 18.75),
    "claude-opus-4-5":       (15.00, 75.00, 1.50, 18.75),
    "claude-opus-4-6":       (15.00, 75.00, 1.50, 18.75),
    "claude-opus-4-7":       (15.00, 75.00, 1.50, 18.75),
    "claude-sonnet-4":       ( 3.00, 15.00, 0.30,  3.75),
    "claude-sonnet-4-5":     ( 3.00, 15.00, 0.30,  3.75),
    "claude-sonnet-4-6":     ( 3.00, 15.00, 0.30,  3.75),
    "claude-haiku-4-5":      ( 1.00,  5.00, 0.10,  1.25),
    # Claude 3.x (legacy)
    "claude-3-5-sonnet":     ( 3.00, 15.00, 0.30,  3.75),
    "claude-3-5-haiku":      ( 0.80,  4.00, 0.08,  1.00),
    "claude-3-opus":         (15.00, 75.00, 1.50, 18.75),
}

DEFAULT = (3.00, 15.00, 0.30, 3.75)  # fall back to Sonnet-class pricing


def _normalize(model: str) -> str:
    """Strip date suffixes and bracketed tags so 'claude-opus-4-7-20251015[1m]'
    matches our table.
    """
    if not model:
        return ""
    m = model.lower()
    # strip [tags]
    if "[" in m:
        m = m.split("[", 1)[0]
    # strip trailing -YYYYMMDD or -YYYY-MM-DD style date suffixes
    parts = m.split("-")
    while parts and parts[-1].isdigit() and len(parts[-1]) >= 6:
        parts.pop()
    return "-".join(parts)


def cost_for(model: str, usage: dict) -> float:
    """Return estimated USD cost for one usage block."""
    key = _normalize(model)
    rates = PRICING.get(key)
    if rates is None:
        # try progressively shorter prefixes
        bits = key.split("-")
        for i in range(len(bits), 1, -1):
            cand = "-".join(bits[:i])
            if cand in PRICING:
                rates = PRICING[cand]
                break
    if rates is None:
        rates = DEFAULT

    inp, out, cr, cw = rates
    u = usage or {}
    return (
        u.get("input_tokens", 0)                * inp / 1_000_000
        + u.get("output_tokens", 0)             * out / 1_000_000
        + u.get("cache_read_input_tokens", 0)   * cr  / 1_000_000
        + u.get("cache_creation_input_tokens", 0) * cw / 1_000_000
    )


def model_family(model: str) -> str:
    """Return 'opus' / 'sonnet' / 'haiku' / 'other' for grouping."""
    if not model:
        return "other"
    m = model.lower()
    if "opus" in m: return "opus"
    if "sonnet" in m: return "sonnet"
    if "haiku" in m: return "haiku"
    return "other"

---
description: Drift-audit docs/project-brief.md against the codebase. Outputs a severity-tagged findings table at docs/audits/<YYYY-MM-DD>-brief-drift.md.
argument-hint: (no arguments)
---

You are running a drift audit against `docs/project-brief.md`.

## Your job

Walk every verifiable claim in `docs/project-brief.md` and check it against:

1. The repo itself (code, configs, schemas, tests, scripts, deploy artifacts).
2. Any local data stores referenced by the brief (read-only inspection).
3. The most recent `git log` to confirm "last verified" / "shipped 2026-MM-DD" claims.
4. External-system claims (third-party APIs, dashboards, hosted services) — flag as `unverifiable` with the venue noted, **don't guess**.

For each verifiable claim, decide one of:

- **passes** — claim matches reality.
- **dangerous** — wrong in a way that breaks something if acted on.
- **misleading** — wrong in a way that wastes a future reader's time.
- **stale** — was true at some point, no longer.
- **cosmetic** — pointer/filename detail slightly off but doesn't impair understanding.
- **unverifiable** — couldn't be confirmed from this session's vantage point.

## Output

Write findings to `docs/audits/<YYYY-MM-DD>-brief-drift.md` (UTC date). Structure:

1. Opening paragraph: what was audited, what commit of the brief, what could and couldn't be checked.
2. **Severity legend** section.
3. **Findings** table — columns: `#`, `Brief claim (line)`, `Reality`, `Severity`. Cite line numbers in `docs/project-brief.md` and file:line evidence.
4. **Notes — items worth a closer look** — per-finding prose for every non-`passes` item. Numbered to match.
5. **What I couldn't check** — explicit list of claims needing an external venue or that the harness blocked.
6. **What passes (compact list)** — one-line bullets grouped by topic.

## Guardrails

- Do not edit `docs/project-brief.md`. Audit only.
- Do not commit. Just write the audit file.
- Do not fabricate evidence. If you can't find something with `grep` / `Read`, mark `unverifiable` and say where to look.
- Do not skip claims because they "feel right." Assume nothing.
- Do not stop early. Aim for comprehensive coverage of load-bearing facts.

## Done

When finished, print: `[audit-brief] wrote docs/audits/<YYYY-MM-DD>-brief-drift.md — N passes, M misleading, K stale, J unverifiable`.

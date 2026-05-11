---
name: audit-memory
description: Audit whether daily notes are in sync with git activity. Lists days where commits landed but no daily note exists. Run anytime you suspect memory-keeper is silently failing.
---

You are auditing the memory health of this project. Do not write code; produce a single concise report.

## Steps

1. Read every dated note in `docs/memory/[0-9]*.md` and collect the set of dates that have a daily note.
2. Run `git log --since='30 days ago' --pretty='%cd' --date=short | sort -u` to get the set of dates where commits landed in the last 30 days.
3. Compute the diff: dates where commits exist but no daily note exists.
4. Read `docs/memory/.session-beacons.log` (if it exists) and list any beacon dates that don't have a daily note either — those are sessions that ran but never produced memory output.
5. Check the SessionEnd hook configuration in `.claude/settings.json` — is the agent-typed hook present? Is the prompt pointing at `docs/memory/`? Is the broken `status.md` reference (a legacy bug) still in the fallback script `.claude/hooks/session-end-memory-keeper.sh`?

## Report format

```
Memory audit — <project name> @ <UTC timestamp>

Daily notes present:    <count> spanning <earliest>..<latest>
Commits last 30d:       <count> on <N> distinct days
Beacon entries (if any): <count>

Missing daily notes (commits landed, no note):
  YYYY-MM-DD — N commits, top: <first-line of newest>
  ...

Beacon-only days (session ran, no commits, no note):
  YYYY-MM-DD — N beacons
  ...

Hook config:
  SessionEnd agent hook present:  yes/no
  Agent prompt targets docs/memory/: yes/no
  Fallback script status.md bug:  fixed/present
  Stop hook beacon enabled:       yes/no

Recommendation:
  <one-line: clean / backfill these dates / fix hook config>
```

If everything is in sync, the report is one line: `Memory audit clean — <N> notes match <N> commit-days, no gaps.`

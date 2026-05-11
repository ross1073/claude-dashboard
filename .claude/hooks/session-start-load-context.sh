#!/usr/bin/env bash
# Auto-loads user profile, project brief, recent daily notes, and current
# stage doc (if present) into the Claude Code session as additional
# SessionStart context.
#
# Also surfaces a LOUD WARNING when daily notes are stale relative to git
# activity OR within-day session activity (per the beacon log), so
# memory-keeper failures are detected immediately at the next session
# start rather than rotting silently.
#
# Date handling: all date math is in UTC to match the memory-keeper agent,
# which writes today's daily note keyed on `date -u +%Y-%m-%d`. A commit
# at 23:30 local-MDT lands on the next day in UTC, so we use the UTC
# committer date for the comparison.
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$repo_root"

user_md="$HOME/.claude/user.md"
brief="docs/project-brief.md"
memory_dir="docs/memory"
stage="docs/stage-current.md"
beacon_log="docs/memory/.session-beacons.log"

# ── memory-staleness check (loud) ───────────────────────────────────
staleness_warning=""
if [[ -d "$memory_dir" ]]; then
  latest_note=$(ls -1 "$memory_dir"/[0-9]*.md 2>/dev/null | sort | tail -1)
  if [[ -n "$latest_note" ]]; then
    latest_note_date=$(basename "$latest_note" .md)
    today=$(date -u +%Y-%m-%d)
    # Most recent commit date in UTC (matches memory-keeper's UTC date convention).
    latest_commit_date_utc=$(TZ=UTC git log -1 --format=%cd --date=format-local:%Y-%m-%d 2>/dev/null || echo "")

    # Case 1: a whole-day gap — commits after the latest note's date.
    if [[ -n "$latest_commit_date_utc" && "$latest_commit_date_utc" > "$latest_note_date" ]]; then
      missing_commits=$(TZ=UTC git log --since="${latest_note_date} 23:59:59 +0000" --oneline 2>/dev/null | wc -l | tr -d ' ')
      if [[ "$missing_commits" -gt 0 ]]; then
        staleness_warning="🚨 MEMORY STALE 🚨
Latest daily note: ${latest_note_date}
Latest commit:     ${latest_commit_date_utc} (UTC)
Commits since latest daily note: ${missing_commits}

The SessionEnd memory-keeper agent likely did NOT run after recent sessions.
Recovery: run 'git log --since=\"${latest_note_date}\"' and either backfill
the missing daily note(s) manually or invoke memory-keeper on this session."
      fi
    fi

    # Case 2: within-day staleness — today's daily note exists but the most
    # recent beacon-log entry is newer than the latest `## Session` header
    # inside today's note. This catches the case where a morning session
    # wrote its note, an afternoon session ran (per beacons), and the
    # afternoon's SessionEnd didn't fire.
    if [[ -z "$staleness_warning" && -f "$beacon_log" && "$latest_note_date" == "$today" ]]; then
      last_beacon_ts=$(tail -n 1 "$beacon_log" 2>/dev/null | awk '{print $1}')
      if [[ -n "$last_beacon_ts" ]]; then
        # Strip non-numeric chars to compare as integers (YYYYMMDDHHMMSS).
        beacon_num=$(echo "$last_beacon_ts" | tr -d -c '0-9' | cut -c1-14)
        # Most recent session header timestamp in the note (UTC ISO).
        last_session_ts=$(grep -oE '## Session [0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z' "$latest_note" 2>/dev/null | tail -n 1 | awk '{print $2}')
        if [[ -n "$last_session_ts" ]]; then
          session_num=$(echo "$last_session_ts" | tr -d -c '0-9' | cut -c1-14)
          # Beacon must be at least 10 minutes newer than the last session
          # header to avoid noise from beacons fired during the same session
          # that wrote the header.
          if [[ -n "$beacon_num" && -n "$session_num" && "$beacon_num" -gt "$session_num" ]]; then
            beacon_age_minutes=$(( ($(date -u +%s) - $(date -u -j -f '%Y-%m-%dT%H:%M:%SZ' "$last_beacon_ts" +%s 2>/dev/null || echo 0)) / 60 ))
            session_gap_minutes=$(( ($(date -u -j -f '%Y-%m-%dT%H:%M:%SZ' "$last_beacon_ts" +%s 2>/dev/null || echo 0) - $(date -u -j -f '%Y-%m-%dT%H:%M:%SZ' "$last_session_ts" +%s 2>/dev/null || echo 0)) / 60 ))
            if [[ "$session_gap_minutes" -gt 10 ]]; then
              staleness_warning="🚨 WITHIN-DAY MEMORY STALE 🚨
Today's daily note last session block: ${last_session_ts}
Most recent beacon (this/last session): ${last_beacon_ts}
Gap: ${session_gap_minutes} minutes

A later session ran but produced no daily-note block. SessionEnd likely
failed. Recovery: invoke memory-keeper to append a block for the missing
session before significant new work."
            fi
          fi
        elif [[ -n "$beacon_num" ]]; then
          # Note file exists today but has no ## Session header — corrupt.
          staleness_warning="🚨 TODAY'S NOTE HAS NO SESSION BLOCK 🚨
File ${latest_note} exists but contains no '## Session ...' header.
Beacon log shows session activity. Investigate."
        fi
      fi
    fi
  fi
fi

echo "## Project state (auto-loaded at session start)"
echo

if [[ -n "$staleness_warning" ]]; then
  echo "### ⚠️  MEMORY STALENESS WARNING"
  echo
  echo '```'
  echo "$staleness_warning"
  echo '```'
  echo
fi

echo "### Operator (user.md)"
if [[ -f "$user_md" ]]; then
  cat "$user_md"
else
  echo "_(missing: ~/.claude/user.md)_"
fi
echo

echo "### Brief"
if [[ -f "$brief" ]]; then
  cat "$brief"
else
  echo "_(missing: $brief)_"
fi
echo

echo "### Recent daily notes"
if [[ -d "$memory_dir" ]]; then
  recent=$(ls -1 "$memory_dir"/*.md 2>/dev/null | sort -r | head -2)
  if [[ -z "$recent" ]]; then
    echo "_(no entries in $memory_dir yet)_"
  else
    while IFS= read -r f; do
      [[ -z "$f" ]] && continue
      echo "#### $(basename "$f")"
      cat "$f"
      echo
    done <<< "$recent"
  fi
else
  echo "_(missing: $memory_dir)_"
fi
echo

echo "### Active stage"
if [[ -f "$stage" ]]; then
  cat "$stage"
else
  echo "None active."
fi
echo

echo "### Loaded at"
date -u +"%Y-%m-%dT%H:%M:%SZ"

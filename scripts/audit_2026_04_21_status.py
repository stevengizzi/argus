#!/usr/bin/env python3
"""Audit 2026-04-21 — Phase 3 status + CLAUDE.md Tests-line maintenance.

STRIPPED version: STAGE-LOG.md and CLOSEOUT.md generation removed because
the Work Journal conversation on Claude.ai is the primary operational log
and produces the final close-out.

Retained responsibilities:
  1. `--status`: print campaign progress from git log
  2. (default): update CLAUDE.md's "Tests:" line from the latest
     `audit(FIX-NN):` commit body, so downstream Claude Code sessions see
     the correct baseline when reading CLAUDE.md

Source of truth: git log, grepped for `audit(FIX-NN):` commits. The commit
message body carries `Test delta: <baseline> -> <new> (net +N / 0)` which
we parse to reconstruct the campaign's current test state.

Usage:
  python scripts/audit_2026_04_21_status.py              # update CLAUDE.md tests line
  python scripts/audit_2026_04_21_status.py --status     # print progress, exit
  python scripts/audit_2026_04_21_status.py --dry-run    # print what would change
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CLAUDE_MD = REPO_ROOT / "CLAUDE.md"

STAGE_MAP = {
    1: ["FIX-01", "FIX-11", "FIX-00", "FIX-15", "FIX-17", "FIX-20"],
    2: ["FIX-02", "FIX-03", "FIX-19", "FIX-12", "FIX-21"],
    3: ["FIX-04", "FIX-16", "FIX-14"],
    4: ["FIX-05", "FIX-18", "FIX-10"],
    5: ["FIX-06", "FIX-07"],
    6: ["FIX-08"],
    7: ["FIX-09"],
    8: ["FIX-13"],
}
STAGE_ARGUS = {1: "DOWN", 2: "DOWN", 3: "DOWN", 4: "DOWN",
               5: "DOWN", 6: "DOWN", 7: "DOWN", 8: "LIVE OK"}


def git_log_audit_commits() -> list[dict]:
    """Return commits matching 'audit(FIX-NN):' with sha, date, subject, body."""
    try:
        out = subprocess.check_output(
            ["git", "log", "--all", "--grep=^audit(FIX-",
             "--pretty=format:===COMMIT===%n%H%n%ai%n%s%n---BODY---%n%b%n===END==="],
            cwd=REPO_ROOT, text=True, stderr=subprocess.DEVNULL,
        )
    except subprocess.CalledProcessError:
        return []
    commits = []
    for chunk in out.split("===COMMIT===")[1:]:
        parts = chunk.split("---BODY---", 1)
        if len(parts) != 2:
            continue
        header = parts[0].strip().splitlines()
        if len(header) < 3:
            continue
        body = parts[1].split("===END===")[0].strip()
        commits.append({"sha": header[0].strip(), "date": header[1].strip(),
                        "subject": header[2].strip(), "body": body})
    return commits


def extract_session_id(subject: str) -> str | None:
    m = re.match(r"^audit\((FIX-\d{2})\):", subject)
    return m.group(1) if m else None


def extract_test_delta(body: str) -> tuple[int, int, int] | None:
    """Parse 'Test delta: 4933 -> 4937 (net +4)' → (baseline, post, delta)."""
    m = re.search(r"Test delta:\s*(\d+)\s*->\s*(\d+)\s*\(net\s*([+-]?\d+)", body)
    if not m:
        return None
    return int(m.group(1)), int(m.group(2)), int(m.group(3))


def collect_session_status() -> dict[str, list[dict]]:
    """Return {FIX-NN: [commits, newest first]}."""
    result: dict[str, list[dict]] = {s: [] for stage in STAGE_MAP.values() for s in stage}
    for c in git_log_audit_commits():
        sid = extract_session_id(c["subject"])
        if sid and sid in result:
            result[sid].append(c)
    for sid in result:
        result[sid].sort(key=lambda c: c["date"], reverse=True)
    return result


def latest_post_count(status: dict[str, list[dict]]) -> int | None:
    all_deltas = []
    for commits in status.values():
        for c in commits:
            d = extract_test_delta(c["body"])
            if d is not None:
                all_deltas.append((c["date"], d[1]))
    if not all_deltas:
        return None
    all_deltas.sort()
    return all_deltas[-1][1]


def update_claude_md_tests_line(new_post: int) -> tuple[bool, str]:
    if not CLAUDE_MD.exists():
        return False, f"CLAUDE.md not found at {CLAUDE_MD}"
    content = CLAUDE_MD.read_text()
    pattern = re.compile(r"^\*\*Tests:\*\*[^\n]*(?:\n(?!\n\*\*|\n##)[^\n]*)*", re.MULTILINE)
    if not pattern.search(content):
        return False, "Could not locate 'Tests:' line in CLAUDE.md — manual update required"
    new_line = (
        f"**Tests:** {new_post} passing (auto-maintained by "
        f"`scripts/audit_2026_04_21_status.py` from the most recent "
        f"`audit(FIX-NN):` commit during the Phase 3 audit campaign; baseline "
        f"at kickoff was 4,933 passed + 1 flake DEF-150 — see "
        f"`docs/audits/audit-2026-04-21/BASELINE.md`)."
    )
    new_content = pattern.sub(new_line, content, count=1)
    if new_content == content:
        return False, "No change needed (line already current)"
    CLAUDE_MD.write_text(new_content)
    return True, f"CLAUDE.md Tests line set to {new_post} passing"


def print_status(status: dict[str, list[dict]]) -> None:
    total = sum(len(v) for v in STAGE_MAP.values())
    completed = sum(1 for commits in status.values() if commits)
    pct = 100 * completed // total if total else 0
    print(f"Audit 2026-04-21 Phase 3 — {completed}/{total} sessions with commits ({pct}%)")
    print()
    for stage in sorted(STAGE_MAP):
        members = STAGE_MAP[stage]
        done = [m for m in members if status.get(m)]
        pending = [m for m in members if not status.get(m)]
        marker = "✅" if not pending else ("🟡" if done else "⏳")
        print(f"  Stage {stage} [{STAGE_ARGUS[stage]:8s}]: {marker}  {len(done)}/{len(members)}")
        for m in members:
            commits = status.get(m, [])
            if commits:
                c = commits[0]
                delta = extract_test_delta(c["body"])
                delta_s = f"net {delta[2]:+d}" if delta else "no test delta in body"
                print(f"     {m}  ✓ {c['sha'][:7]}  {delta_s}  ({c['date'][:10]})")
            else:
                print(f"     {m}  ⏳ pending")


def main():
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--status", action="store_true",
                        help="Print campaign progress and exit")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would change to CLAUDE.md, write nothing")
    args = parser.parse_args()

    status = collect_session_status()

    if args.status:
        print_status(status)
        return

    latest = latest_post_count(status)
    if latest is None:
        print("No audit(FIX-NN) commits found yet; CLAUDE.md Tests line unchanged.")
        return

    if args.dry_run:
        print(f"[dry-run] would set CLAUDE.md Tests line to: {latest} passing")
        return

    changed, msg = update_claude_md_tests_line(latest)
    print(f"{'✓' if changed else '·'} {msg}")


if __name__ == "__main__":
    main()

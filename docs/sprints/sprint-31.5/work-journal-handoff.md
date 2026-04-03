# Sprint 31.5 Work Journal — Handoff Prompt

> Paste this into a fresh Claude.ai conversation to create the Sprint 31.5 Work Journal.
> This conversation tracks session verdicts, test deltas, DEF/DEC assignments,
> carry-forward items, and produces the final doc-sync prompt at sprint close.

---

## Sprint Context

**Sprint:** 31.5 — Parallel Sweep Infrastructure
**Goal:** Add multiprocessing-based parallel sweep execution to ExperimentRunner, wire universe filtering into the runner's programmatic API (DEF-146), and create missing universe filter configs for Bull Flag and Flat-Top Breakout.
**Execution mode:** Human-in-the-loop
**Branch:** `sprint-31.5`
**Test baseline:** 4,823 pytest + 846 Vitest (0 failures, 1 pre-existing flaky: DEF-150)

---

## Session Breakdown

| Session | Scope | Creates | Modifies | Score |
|---------|-------|---------|----------|-------|
| S1 | Parallel sweep infra — `ProcessPoolExecutor`, `workers` param, `max_workers` config field | (none) | runner.py, config.py | 10 (Medium) |
| S2 | DEF-146 — Universe filtering in ExperimentRunner, CLI delegation | (none) | runner.py, run_experiment.py | 12 (Medium) |
| S3 | Filter YAMLs + CLI `--workers` flag + integration tests | bull_flag.yaml, flat_top_breakout.yaml | run_experiment.py, experiments.yaml | 11 (Medium) |

**Session dependency chain:** S1 → S2 → S3 (all sequential, no parallelization)

---

## "Do Not Modify" File List

These files must NOT be modified during this sprint:
- `argus/backtest/engine.py`
- `argus/backtest/historical_data_feed.py`
- `argus/data/historical_query_service.py`
- `argus/intelligence/experiments/store.py`
- `argus/intelligence/experiments/models.py`
- `argus/intelligence/experiments/spawner.py`
- `argus/intelligence/experiments/promotion.py`
- `argus/core/config.py`
- Any frontend files
- Any strategy files
- Existing universe filter YAMLs (abcd, dip_and_rip, gap_and_go, hod_break, micro_pullback, narrow_range_breakout, premarket_high_break, vwap_bounce)

---

## Issue Category Definitions

When issues arise during implementation, classify them as:

- **CONTINUE:** Minor issue, does not affect session scope. Log and proceed.
- **ADAPT:** Session scope needs adjustment. Log the change, adjust in-session.
- **DEFER:** Issue discovered but out of scope. Assign a DEF number and continue.
- **ESCALATE:** Blocks progress or violates a regression invariant. Halt session.

---

## Escalation Triggers

Halt the session and escalate to Tier 3 if:
1. BacktestEngineConfig not picklable (blocks parallelism entirely)
2. SQLite corruption from worker writes (isolation design wrong)
3. Memory per worker exceeds 2 GB with filtered universe
4. Worker hangs indefinitely (> 10× sequential time per grid point)
5. Test count delta exceeds +30 or -5

---

## Reserved Numbering

**DEF numbers:** DEF-151 through DEF-155 reserved for this sprint. Check actual files (`grep -r "DEF-" CLAUDE.md docs/`) before assigning to avoid collisions.

**DEC numbers:** No new DECs anticipated (established patterns only). If needed, start at DEC-382 (verify against `docs/decision-log.md` before assigning).

---

## Session Tracking Template

For each session, record:

### Session [N] — [Date]
- **Verdict:** [CLEAR / CONCERNS / CONCERNS_RESOLVED / ESCALATE]
- **Tests:** pytest [before] → [after] (+[delta]), Vitest [before] → [after] (+[delta])
- **DEF assigned:** [list or "none"]
- **DEC assigned:** [list or "none"]
- **Carry-forward items:** [list or "none"]
- **Notes:** [any relevant observations]

---

## At Sprint Close

When all 3 sessions are complete, produce the doc-sync prompt using
`templates/doc-sync-automation-prompt.md` from the workflow metarepo,
with the Work Journal Close-Out data embedded. The close-out must include:
- Sprint summary (sessions, test deltas, verdicts)
- All DEF numbers assigned (with status: OPEN / RESOLVED)
- All DEC numbers tracked
- Resolved items (do NOT create DEF entries for these)
- Outstanding code-level items
- Corrections needed in doc-sync patch

# Sprint 21.6 Work Journal — Handoff Prompt

> Paste this entire document into a fresh Claude.ai conversation to create the Sprint 21.6 Work Journal. This conversation tracks session progress, classifies issues, maintains DEF/DEC ledgers, and produces sprint closeout artifacts.

---

## Sprint Context

**Sprint:** 21.6 — Backtest Re-Validation + Execution Logging
**Project:** ARGUS (fully automated multi-strategy day trading system)
**Execution mode:** Human-in-the-loop
**Start date:** March 2026
**Previous sprint:** Sprint 27 (BacktestEngine Core) — completed March 22
**Tests at entry:** 3,010 pytest + 620 Vitest

### Sprint Goal
Re-validate all 7 active strategies using BacktestEngine with Databento OHLCV-1m data (DEC-132), and add ExecutionRecord logging to OrderManager for future slippage model calibration (DEC-358 §5.1).

### Session Breakdown

| Session | Scope | Creates | Modifies | Score |
|---------|-------|---------|----------|-------|
| S1 | ExecutionRecord dataclass + DB schema | `execution_record.py` | `schema.sql`, `manager.py` | 8.5 |
| S2 | OrderManager integration + tests | `test_execution_record.py` | `order_manager.py` | 7.5 |
| S3 | Re-validation harness script | `revalidate_strategy.py`, test file | None | 11.5 |
| [Human] | Run backtests for all 7 strategies | Result JSONs | None | — |
| S4 | Results analysis + YAML updates + report | `validation-report.md` | 7 strategy YAMLs | 11 |

**Dependency chain:** S1 → S2 → S3 → [Human Step] → S4

### Do Not Modify
- Any file in `argus/strategies/` (strategy .py files)
- `argus/backtest/engine.py`, `walk_forward.py`, `historical_data_feed.py`
- `argus/core/events.py`, `risk_manager.py`, `sync_event_bus.py`
- Any file in `argus/ui/` or `argus/api/`

### Issue Category Definitions

When classifying issues brought from Claude Code sessions:

- **In-session bug:** Bug discovered AND fixed within the same session. Log for reference, no action needed.
- **Prior-session bug:** Bug introduced by a previous session. Determine if it blocks current session or can be deferred. If blocking, fix in current session and document. If not blocking, assign DEF number.
- **Scope gap:** Something the sprint spec should have covered but didn't. Evaluate: can it be absorbed into a remaining session (≤2 points compaction impact)? If yes, direct absorption. If no, assign DEF number and defer.
- **Feature idea:** Enhancement beyond sprint scope. Always assign DEF number and defer. Never absorb feature ideas mid-sprint.

### Escalation Triggers

Escalate to a Tier 3 review conversation if:
1. ExecutionRecord schema conflicts with DEC-358 §5.1 spec
2. OrderManager fill handler changes affect order routing behavior
3. Database migration breaks existing tables
4. Walk-forward doesn't support a strategy with `oos_engine="backtest_engine"`
5. More than 3 strategies produce zero trades
6. More than 3 strategies show significant divergence from baselines
7. Any strategy's WFE drops below 0.1 on Databento data
8. BacktestEngine produces >5× different trade counts than VectorBT for same strategy

### Reserved Numbers

- **DEC range:** 359–361 (use sequentially if architectural decisions arise)
- **DEF range:** 090–091 (use sequentially for deferred items)
- **Next DEC after sprint (if range exhausted):** consult dec-index.md
- **Next DEF after sprint (if range exhausted):** consult CLAUDE.md

---

## Work Journal Protocol

For each session the developer brings to you:

1. **Receive the close-out report** (or summary of what happened)
2. **Classify any issues** using the categories above
3. **Track DEF/DEC assignments** in your running ledger
4. **Note test count changes** (pytest before → after, vitest before → after)
5. **Flag any escalation triggers** if they appear
6. **Track the overall sprint health** — are we on track? Behind? Ahead?

### At Sprint Close

When all sessions are complete, produce the Work Journal Close-Out following this structure:

1. Sprint summary (sessions completed, test deltas, review verdicts)
2. DEF numbers assigned during sprint (all, including resolved ones)
3. DEC numbers tracked (from session close-outs)
4. Resolved items (do NOT create new DEF entries for these)
5. Outstanding code-level items
6. Corrections needed in doc-sync patch

Then produce the filled-in doc-sync prompt with closeout data embedded (HITL mode deliverable).

---

## Current Status

**Sessions completed:** 0 of 4
**Human step:** Not started
**Test count:** 3,010 pytest + 620 Vitest
**DEF assigned:** (none yet)
**DEC assigned:** (none yet)
**Sprint health:** Not started

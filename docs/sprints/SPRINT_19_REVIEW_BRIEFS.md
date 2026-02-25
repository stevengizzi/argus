# Sprint 19 — Code Review Handoff Briefs

> Copy-paste these into new Claude.ai conversations to kick off each code review.

---

## Checkpoint 1 Handoff Brief (After Session 5)

```
# Sprint 19 Code Review — Checkpoint 1: Strategy + Integration

I'm building ARGUS, an automated multi-strategy day trading system. Sprint 19 adds VWAP Reclaim — the first mean-reversion strategy. Sessions 1-5 are complete. I need a code review before proceeding to backtesting.

**Repo:** https://github.com/stevengizzi/argus.git — please clone it and review the code directly.

**What changed in Sessions 1-5:**

NEW FILES:
- `argus/strategies/vwap_reclaim.py` — VwapReclaimStrategy class (mean-reversion, state machine)
- `config/strategies/vwap_reclaim.yaml` — default configuration
- `tests/strategies/test_vwap_reclaim.py` — unit tests
- `tests/test_integration_sprint19.py` — three-strategy integration tests

MODIFIED FILES:
- `argus/core/config.py` — added VwapReclaimConfig + load_vwap_reclaim_config()
- `argus/backtest/config.py` — added StrategyType.VWAP_RECLAIM
- `argus/main.py` — wired VwapReclaimStrategy into startup
- `argus/__init__.py` — updated exports

**Key design decisions to validate:**
1. VwapReclaimStrategy inherits directly from BaseStrategy (NOT OrbBaseStrategy). No shared logic with ORB family.
2. 5-state machine: WATCHING → ABOVE_VWAP → BELOW_VWAP → ENTERED/EXHAUSTED, with loop-back from BELOW_VWAP → ABOVE_VWAP when reclaim happens without volume confirmation.
3. Scanner reuse: uses same gap watchlist as ORB family.
4. Stop at pullback swing low (not VWAP — VWAP moves intraday).
5. T1=1.0R (50%), T2=2.0R (50%). 30-minute time stop.
6. Minimum risk floor: max(risk_per_share, entry_price × 0.003) to prevent oversizing on shallow pullbacks.
7. ALLOW_ALL duplicate stock policy with ORB family.

**Review checklist:**

STRATEGY LOGIC:
- [ ] State machine transitions are correct and complete
- [ ] All entry conditions checked in the right order
- [ ] Edge cases handled (VWAP not available, zero volume, boundary conditions)
- [ ] Position sizing with minimum risk floor is sound
- [ ] Signal construction matches Order Manager expectations (target_prices tuple, time_stop_seconds)
- [ ] Candle close (not intra-bar) used for VWAP crossover detection

ARCHITECTURE:
- [ ] Clean inheritance from BaseStrategy — no ORB assumptions leaking in
- [ ] DataService.get_indicator() usage pattern is correct (in-memory cache, no I/O concern)
- [ ] Time handling (UTC → ET conversion) follows established patterns
- [ ] Config validation (Pydantic Field constraints) covers edge cases
- [ ] main.py wiring follows the established ORB/Scalp pattern

TESTS:
- [ ] State machine transitions have full coverage
- [ ] Every entry rejection condition has a dedicated test
- [ ] Signal construction verified (stop, targets, time stop, shares)
- [ ] Edge cases tested (no VWAP, zero capital, boundary values)
- [ ] Integration tests cover three-strategy scenarios
- [ ] Integration tests cover the ORB → VWAP Reclaim sequential flow

CROSS-STRATEGY:
- [ ] ALLOW_ALL policy works correctly with three strategies
- [ ] Cross-strategy max_single_stock_pct (5%) enforced
- [ ] Orchestrator allocation splits correctly for 3 strategies
- [ ] Regime filtering applied per-strategy

**Context files to read (in order):**
1. `CLAUDE.md` — current project state
2. `argus/strategies/vwap_reclaim.py` — the main deliverable
3. `argus/core/config.py` — VwapReclaimConfig (search for "VwapReclaimConfig")
4. `tests/strategies/test_vwap_reclaim.py` — test coverage
5. `tests/test_integration_sprint19.py` — integration scenarios
6. `argus/main.py` — wiring changes
7. `argus/strategies/base_strategy.py` — interface being implemented
8. `argus/strategies/orb_base.py` — comparison (VWAP Reclaim should NOT look like this)
9. `argus/data/indicator_engine.py` — VWAP computation (already exists)

**Test count:** Should be ~1380+ pytest (1313 prior + ~65-75 new). Report actual count.

**Output format:**
1. List of issues found (Critical / Important / Minor)
2. Test coverage gaps
3. Architectural concerns
4. Suggested fixes (exact code if possible, for Session 11)
5. Decision log entries to draft (new DEC-NNN numbers — check current highest first)
```

---

## Checkpoint 2 Handoff Brief (After Session 10)

```
# Sprint 19 Code Review — Checkpoint 2: Full Sprint Review

I'm building ARGUS, an automated multi-strategy day trading system. Sprint 19 is nearly complete — Sessions 1-10 are done. This is the final review before polish and documentation.

**Repo:** https://github.com/stevengizzi/argus.git — please pull latest and review.

**What changed since Checkpoint 1 (Sessions 6-10):**

NEW FILES:
- `argus/backtest/vectorbt_vwap_reclaim.py` — VectorBT parameter sweep
- Watchlist sidebar components in `argus/ui/src/components/`

MODIFIED FILES:
- `argus/backtest/walk_forward.py` — added vwap_reclaim dispatch
- `argus/backtest/replay_harness.py` — added VwapReclaim to strategy factory
- `argus/backtest/config.py` — added VWAP Reclaim BacktestConfig fields
- `argus/api/dev_state.py` — added VWAP Reclaim mock data
- `argus/api/` — watchlist endpoint
- Dashboard page layout (sidebar integration)

**Checkpoint 1 issues (if any) and resolution status:**
[FILL IN: List issues from Checkpoint 1 and whether they've been addressed]

**Backtest results:**
[FILL IN: Paste VectorBT sweep summary and walk-forward results from Session 8]

**Review checklist:**

BACKTESTING:
- [ ] VWAP computation in vectorbt_vwap_reclaim.py matches IndicatorEngine
- [ ] State machine simulation matches VwapReclaimStrategy logic
- [ ] Gap filter correct (uses prev_close to day_open)
- [ ] Trade simulation (stop/target/time-stop/EOD) is correct
- [ ] Walk-forward dispatch maps parameters correctly
- [ ] Replay Harness strategy factory creates VwapReclaimStrategy correctly
- [ ] BacktestConfig fields have correct types and defaults
- [ ] Sweep results are reasonable (or documented as limited per DEC-132)

DEV MODE:
- [ ] Three strategies in allocation donut
- [ ] VWAP Reclaim positions with correct time ranges (10:00-12:00)
- [ ] VWAP Reclaim trades with realistic exit reasons
- [ ] Strategy card on System page
- [ ] Performance breakdown includes all three strategies
- [ ] SessionSummaryCard includes VWAP Reclaim

WATCHLIST SIDEBAR:
- [ ] Responsive at all breakpoints (phone, tablet, desktop)
- [ ] Collapse/expand animation smooth
- [ ] Strategy badges show correct strategies per symbol
- [ ] VWAP state dots show correct colors
- [ ] Mini sparklines render
- [ ] Same DOM structure regardless of state (Sprint 17.5 principle)
- [ ] Zustand persistence for collapse state

CROSS-CUTTING:
- [ ] All tests pass (pytest + Vitest)
- [ ] No regressions in ORB or Scalp functionality
- [ ] ruff lint clean
- [ ] Consistent code style with existing codebase

**Test count:** Should be ~1460+ pytest + ~10+ Vitest. Report actual.

**Output format:**
1. Issues found (Critical / Important / Minor)
2. Backtest methodology concerns
3. UI/UX feedback (from component code review, not visual — I'll provide screenshots separately)
4. Suggested fixes for Session 11
5. Draft ALL decision log entries for Sprint 19 (check current highest DEC number first)
6. Draft Project Knowledge update (Sprint 19 completion entry)
7. Any items to add to Risk Register or deferred items list
```

---

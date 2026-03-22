# Sprint 27: Adversarial Review Input Package

> Paste this into an Adversarial Review conversation, or review inline.
> This package contains everything needed to stress-test the Sprint 27 design.

---

## Sprint Summary

**Sprint 27: BacktestEngine Core** — Production-code backtesting engine running real strategy code against Databento OHLCV-1m historical data via synchronous event dispatch. Backend only, no UI. 6 sessions, ~80 tests.

## Documents to Review

The following spec-level artifacts have been generated and should be read in order:

1. `docs/sprints/sprint-27/design-summary.md`
2. `docs/sprints/sprint-27/sprint-spec.md`
3. `docs/sprints/sprint-27/spec-by-contradiction.md`
4. `docs/sprints/sprint-27/session-breakdown.md`
5. `docs/sprints/sprint-27/escalation-criteria.md`
6. `docs/sprints/sprint-27/regression-checklist.md`

## Architecture Context

### Current Backtesting Architecture (what exists)

ARGUS has two backtesting paths:

**VectorBT** — Fast vectorized parameter sweeps using NumPy arrays. Runs a mathematical approximation of strategy logic (not the actual production code). Known divergences with production behavior (e.g., ATR calculated from daily bars vs 1-minute bars, consolidation timing, state machine transitions). Good for coarse screening, not final validation. Files: `argus/backtest/vectorbt_*.py` (6 files).

**Replay Harness** — Runs actual production strategy code through the real async EventBus, IndicatorEngine, RiskManager, OrderManager, and SimulatedBroker. Maximum fidelity. Uses tick synthesis (DEC-053) for intra-bar fill simulation. Slow due to async overhead (asyncio.create_task per handler, locks, sleep(0) between bars). Files: `argus/backtest/replay_harness.py`, `backtest_data_service.py`.

**Walk-Forward** — Orchestrates VectorBT for in-sample optimization + Replay Harness for out-of-sample validation. File: `argus/backtest/walk_forward.py` (2,566 lines).

### Proposed Addition: BacktestEngine

A third backtesting path that bridges the gap: **real production code, but synchronous dispatch for speed.**

```
BacktestEngine
├── HistoricalDataFeed (Databento OHLCV-1m → Parquet cache → bar data)
├── SynchronousEventBus (direct await, no asyncio.create_task)
├── BacktestDataService (existing, reused as-is)
├── FixedClock (existing, reused as-is)
├── Strategy instance (real production class, all 7 types)
├── IndicatorEngine (real production code, via BacktestDataService)
├── RiskManager (real production logic)
├── OrderManager (real production logic)
├── SimulatedBroker (existing, reused as-is)
└── TradeLogger → SQLite → compute_metrics() (existing pipeline)
```

### Key Design Decisions to Stress-Test

**1. SynchronousEventBus as a separate class**

A new class (~40 lines) with the same subscribe/publish API but sequential dispatch. NOT a mode flag on the production EventBus.

- Same async method signatures (strategies are async, entire backtest runs in `asyncio.run()`)
- `publish()` awaits each handler directly in subscription order (no create_task)
- No asyncio.Lock (single-threaded, no contention)
- `drain()` is a no-op (all handlers complete within publish)

*Challenge:* Is there any scenario where the production EventBus's concurrent dispatch (handlers run as tasks) produces fundamentally different behavior than sequential dispatch? Could two handlers racing (e.g., strategy and risk manager both processing the same signal) cause divergent outcomes?

**2. Bar-level fill model (no tick synthesis)**

The Replay Harness synthesizes 4 ticks per bar (O→H→L→C or O→L→H→C) to determine intra-bar stop/target ordering. The BacktestEngine skips this and checks bracket orders against bar OHLC directly:

- If bar.low ≤ stop_price AND bar.high ≥ target_price → stop wins (worst-case-for-longs)
- If bar.low ≤ stop_price → stop triggered at stop_price
- If bar.high ≥ target_price → target triggered at target_price
- If time_stop condition met → close at bar.close, BUT check if stop also hit first
- EOD → close at bar.close, BUT check if stop also hit first

*Challenge:* Does the worst-case priority always hold? Consider: a bar opens at $100, drops to $95 (hitting stop at $97), then rallies to $105 (would have hit target at $103). Worst-case says stop triggered. But what if the bar opened at $100, rallied to $105 first, THEN dropped to $95? The worst-case model still says stop, but in reality the target was hit first. Is this acceptable conservatism, or does it systematically bias results?

*Challenge:* The Replay Harness tick synthesis uses the close vs open relationship to determine tick order: if close > open, ticks are O→L→H→C (bullish bar, dip then rally). If close < open, ticks are O→H→L→C (bearish bar, rally then dip). The BacktestEngine doesn't have this nuance. Does this matter for strategies that have tight stop/target ratios (e.g., ORB Scalp with 0.3R target)?

**3. Result equivalence as "directional, not identical"**

The sprint spec defines equivalence as: BacktestEngine should produce similar trade counts (within 20%) and same-sign gross P&L when run on identical data as the Replay Harness. Not trade-for-trade identical.

*Challenge:* Is 20% trade count divergence too loose? Too tight? What's the expected divergence from the fill model difference alone? If the divergence is consistently 30%, is that an architecture problem or a known consequence of bar-level fills?

**4. HistoricalDataFeed cost validation**

Every download calls `metadata.get_cost()` first. If cost > $0.00, the download is halted.

*Challenge:* What if `metadata.get_cost()` itself fails (network error, API change)? Should the default be fail-open (proceed with download) or fail-closed (halt)? The spec doesn't address this explicitly.

**5. Walk-forward integration — additive path**

The existing walk-forward uses Replay Harness for OOS windows. Sprint 27 adds BacktestEngine as an alternative, selected by a parameter. The existing path is untouched.

*Challenge:* The walk-forward's VectorBT IS optimization picks parameters, then the OOS engine validates them. If the OOS engine changes from Replay Harness to BacktestEngine, the WFE metric changes because the two engines produce different trade counts and P&L. Should WFE comparisons across engine types be flagged? Should the WalkForwardResult record which engine was used?

## Areas to Challenge

1. Is the SynchronousEventBus genuinely safe for all strategy types, or are there hidden concurrency assumptions in strategy code?
2. Does the bar-level fill model introduce systematic bias that would make BacktestEngine results misleading for strategy evaluation?
3. Are there strategies where the tick-synthesis vs bar-level difference is large enough to change go/no-go decisions?
4. Is the 20% trade count divergence tolerance appropriate, and should it be a configurable threshold?
5. Should the engine record metadata about its fill model (bar-level vs tick) alongside results, to prevent future confusion?
6. Is the session decomposition (6 sessions) appropriate, or could sessions be consolidated without exceeding compaction thresholds?

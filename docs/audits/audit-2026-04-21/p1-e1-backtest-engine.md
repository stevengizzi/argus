# Audit: Production Backtest Infrastructure

**Session:** P1-E1
**Date:** 2026-04-21
**Scope:** Read-only audit of `argus/backtest/engine.py` (2,389 LOC) and its direct dependencies — the Sprint 27 BacktestEngine pipeline that backs walk-forward OOS and the Sprint 32 ExperimentRunner pre-filter.
**Files examined:** 5 deep / 5 skimmed.

---

## Files Covered

### Deep-read
- [argus/backtest/engine.py](../../../argus/backtest/engine.py) — 2,389 LOC
- [argus/backtest/historical_data_feed.py](../../../argus/backtest/historical_data_feed.py) — 336 LOC
- [argus/backtest/backtest_data_service.py](../../../argus/backtest/backtest_data_service.py) — 292 LOC
- [argus/backtest/replay_harness.py](../../../argus/backtest/replay_harness.py) — 886 LOC (header + structure only; E2 covers deeper)
- [argus/backtest/scanner_simulator.py](../../../argus/backtest/scanner_simulator.py) — 270 LOC

### Skim
- [argus/backtest/config.py](../../../argus/backtest/config.py) — `BacktestEngineConfig`, `BacktestConfig`, `StrategyType` enum
- [argus/backtest/metrics.py](../../../argus/backtest/metrics.py) — `BacktestResult` + `compute_metrics`
- [argus/backtest/manifest.py](../../../argus/backtest/manifest.py) — Alpaca-era manifest (legacy)
- [argus/backtest/tick_synthesizer.py](../../../argus/backtest/tick_synthesizer.py) — Replay Harness helper
- [argus/backtest/data_fetcher.py](../../../argus/backtest/data_fetcher.py) — Alpaca/Databento fetcher CLI (legacy; see note in LOW)

### Cross-references (read for verification)
- [argus/core/sync_event_bus.py](../../../argus/core/sync_event_bus.py) — 87 LOC
- [argus/execution/order_manager.py](../../../argus/execution/order_manager.py) lines 282–330, 2696 (fingerprint registry)
- [argus/intelligence/counterfactual.py](../../../argus/intelligence/counterfactual.py) lines 460–555 (AMD-7 cross-check)
- [argus/intelligence/experiments/runner.py](../../../argus/intelligence/experiments/runner.py) lines 50–115 (StrategyType mapping + worker)
- [argus/main.py](../../../argus/main.py) lines 1094–1095 (live fingerprint registration)
- [argus/db/schema.sql](../../../argus/db/schema.sql) line 36 (`config_fingerprint` trade column)

---

## CRITICAL Findings

*None.* No active bugs, silent data loss, or safety-invariant violations found. BacktestEngine is offline-only; nothing it owns touches the live execution path directly. The shared `TheoreticalFillModel` (fill_model.py) and `exit_math.py` helpers are used by live + backtest but are pure functions and were read only at call-site level here (deeper review belongs to P1-A2/P1-C1).

---

## MEDIUM Findings

| # | File:Line | Finding | Impact | Suggested Fix | Safety |
|---|-----------|---------|--------|---------------|--------|
| M1 | [engine.py:1557–1571](../../../argus/backtest/engine.py#L1557-L1571) | **`_apply_config_overrides` silently mis-routes an unresolvable dot-path to a flat key.** The `for...else` correctly handles nested keys when every intermediate segment resolves to a dict. But on `break` (intermediate missing or not-a-dict), the fallback at line 1570 tests `if parts[-1] in config_dict` — the *outermost* dict — and sets it there. So `config_overrides = {"nonexistent.max_loss_per_trade_pct": 0.01}` will silently assign `config_dict["max_loss_per_trade_pct"] = 0.01` at the top level if a flat key with the same leaf name happens to exist. Grid sweeps composed automatically from `PatternParam.name` are almost always flat, so this is rarely exercised — but a typo in a hand-written override (`"risk_limit.x"` instead of `"risk_limits.x"`) is swallowed without a warning. | Silent misconfiguration during experiment sweeps. Worst case: a sweep runs with the wrong override shape and produces data that looks valid, poisoning downstream analysis. | Log a `logger.warning` when a key cannot be resolved at its stated depth; raise if `strict_overrides` config flag is set. Or simpler: drop the flat-key fallback entirely — if the caller wrote dots, honor them. | `safe-during-trading` |
| M2 | [engine.py:573](../../../argus/backtest/engine.py#L573) | **Per-bar dispatch uses `daily_bars.iterrows()`.** `.claude/rules/backtesting.md` bans `iterrows()` in VectorBT sweep hot paths but is silent on BacktestEngine. For a 24-symbol, 35-month run this is ~6M iterations × Pandas row overhead. Engine performance is acceptable today (≥5× Replay Harness per DEC), but as sweep breadth grows past Sprint 31B, this loop will dominate. Per-row work currently includes 2 tz conversions + `self._broker.set_price` + `feed_bar` + `_check_bracket_orders`. | Throughput ceiling on large sweeps. Each bar already pays the SyncEventBus + RiskManager + IndicatorEngine cost; removing `iterrows` would claw back a measurable fraction but not all of it. | Convert daily_bars to a dict of NumPy arrays (`timestamps`, `opens`, `highs`, ...) and index by integer. Keep the event dispatch loop but avoid per-row Series construction. Benchmark before/after; keep the change if >15% faster on a representative sweep. | `safe-during-trading` |
| M3 | [engine.py:795, 800, 862–863, 971–972](../../../argus/backtest/engine.py#L795) | **BacktestEngine reaches into `SimulatedBroker._pending_brackets` (5 call-sites).** The engine filters the private list by symbol + order_type to implement its bar-level fill model. This tightly couples two components and would silently break if `SimulatedBroker` renames or reshapes that list. The canonical way is a public accessor on the broker (e.g., `get_pending_brackets(symbol: str) -> list[Bracket]`). | Brittleness risk: any SimulatedBroker internal refactor would need to update 5 BacktestEngine sites. No runtime bug today. | Add `SimulatedBroker.get_pending_brackets(symbol, order_type=None)` (read-only) and migrate the 5 call-sites. | `safe-during-trading` (SimulatedBroker is offline-only; it's the broker used by Replay + BacktestEngine, never by live trading). |
| M4 | [engine.py:1619–1647](../../../argus/backtest/engine.py#L1619-L1647) | **`_supply_daily_reference_data` accesses `self._strategy._pattern` (private).** The PatternBasedStrategy's `_pattern` attribute is read to call `set_reference_data({"prior_closes": ...})`. This mirrors the live-side wiring pattern in main.py's Phase 9.5 and is intentional, but it's still cross-module private access. A public accessor on PatternBasedStrategy (e.g., `set_pattern_reference_data(data)`) would formalize the contract and keep `_pattern` truly private. | Same brittleness concern as M3 — works today, but a PatternBasedStrategy refactor would need to update both live + backtest wiring. | Add `PatternBasedStrategy.set_pattern_reference_data(data)` forwarder; update main.py and engine.py to use it. Low-risk single-line wrapper. | `weekend-only` (PatternBasedStrategy is production strategy code; any change must be paired with the live wiring and run a full suite). |
| M5 | [engine.py:1543–1546, docstring](../../../argus/backtest/engine.py#L1543-L1546) | **`_apply_config_overrides` docstring claims support for dot-separated keys but gives only a flat-key example.** Docstring example is `{"opening_range_minutes": 15}` — not `{"risk_limits.max_loss_per_trade_pct": 0.01}`. Combined with M1's silent-fallback bug, nothing in the surface docs warns a sweep author that a typo'd dot-path will be swallowed. | Developer ergonomics: someone tuning nested config may not realize the override was silently dropped. | Update docstring with a nested example and a note that dot-path parts must all exist as intermediate dicts. Or fold into M1's fix. | `safe-during-trading` |

---

## LOW Findings

| # | File:Line | Finding | Impact | Suggested Fix | Safety |
|---|-----------|---------|--------|---------------|--------|
| L1 | [engine.py:372](../../../argus/backtest/engine.py#L372) | **Cleanup tracker #1 confirmed — unreachable `else` branch in fingerprint registration ternary.** `strategy_id = self._strategy.strategy_id if self._strategy else self._config.strategy_id`. `self._strategy` was assigned at line 367 via `self._create_strategy(config_dir)`; `_create_strategy` returns a `BaseStrategy` or raises `ValueError` at line 1072 on unknown type. There is no execution path where line 372 runs with `self._strategy is None`. Similarly, the `self._order_manager is not None` guard at line 371 is unreachable-false — `_order_manager` was assigned at line 355 and its absence would have raised earlier. | Dead conditional. Zero runtime impact. Slight cognitive tax for readers. | Replace line 371–375 block with `if self._config.config_fingerprint:` and simplify line 372 to `strategy_id = self._strategy.strategy_id`. Keep the `DEF-153` comment. | `safe-during-trading` |
| L2 | [engine.py:1778–1784](../../../argus/backtest/engine.py#L1778-L1784) | **`_load_spy_daily_bars` computes `margin_start` with awkward inline conditional** (3-month lookback for SMA-50 warmup). The current form is correct but hard to read; `dateutil.relativedelta` or a simple month-arithmetic helper would be clearer. | Readability only. | Replace with `margin_start = (start_date.replace(day=1) - relativedelta(months=3))`. No dependency added — `python-dateutil` is already transitively pulled in. Or write a small `_subtract_months(d, n)` helper. | `safe-during-trading` |
| L3 | [engine.py:2081](../../../argus/backtest/engine.py#L2081) | **`_compute_execution_quality_adjustment` uses hardcoded `avg_entry_price = 50.0`** as the denominator for `slippage_per_share → bps` conversion, with a TODO to derive it from trade data. The resulting Sharpe adjustment is a first-order approximation and the magnitude is sensitive to this constant. Not a bug — the calibrated slippage model's confidence gates the output, and the doc-comment is honest — but the $50 midpoint can be off by 3× on a real basket (NVDA $900, GME $15). | Under-/over-attribution of execution_quality_adjustment. Downstream consumers (MultiObjectiveResult) treat this as annualized-Sharpe delta; a 3× error would materially shift a borderline promote/don't-promote decision. | Derive avg entry price from the trade log via `trade_logger.get_trades_by_date_range(...)` already called on line 1975. Use `sum(entry_price × shares) / sum(shares)` to weight. | `safe-during-trading` |
| L4 | [engine.py: no market_calendar import](../../../argus/backtest/engine.py) | **No explicit holiday filtering** — trading days are derived from whatever dates appear in the loaded Parquet data (`trading_date` column). Databento EQUS.MINI does not return bars on NYSE holidays, so the implicit filter is correct in practice. But the engine has no guardrail: if a corrupted cache somehow contained a holiday-dated bar, the engine would dutifully process it. `argus/core/market_calendar.py` exists for exactly this purpose and is used by live trading. | No active bug — depends on Databento's honoring of the NYSE calendar. Low but non-zero risk if a manual cache patch ever creates one. | Add a `market_calendar.is_market_holiday(d)` filter in `_load_data` after `self._trading_days = sorted(all_dates)` and drop holiday dates with a WARNING log. Belt-and-suspenders. | `safe-during-trading` |
| L5 | [backtest_data_service.py:42](../../../argus/backtest/backtest_data_service.py#L42) | **`BacktestDataService.__init__` is typed `event_bus: EventBus` but receives `SyncEventBus` in BacktestEngine** (engine.py:333 carries `# type: ignore[arg-type]`). The Replay Harness uses `EventBus`, the BacktestEngine uses `SyncEventBus`; both share this class. The concrete duck-typing works because both buses expose `publish(event)` and `subscribe(type, handler)` with compatible signatures. | Type-hint lie. Pylance users get false-positive errors when switching bus types. Four `# type: ignore[arg-type]` comments in engine.py (333, 349, 356, 424) are patching around this. | Introduce a small `Protocol` in `argus.core.event_bus` (`class EventBusProtocol(Protocol): def subscribe(...); async def publish(...)`) that both `EventBus` and `SyncEventBus` satisfy. Type `BacktestDataService.__init__`, `RiskManager.__init__`, and `OrderManager.__init__` against that Protocol. Remove the 4 `# type: ignore`s. | `weekend-only` (touches Risk Manager + Order Manager typing — production-path signatures) |
| L6 | [data_fetcher.py:1-640](../../../argus/backtest/data_fetcher.py) | **`argus/backtest/data_fetcher.py` imports `alpaca.data.*` at the module top.** BacktestEngine does not import `data_fetcher` — it uses HistoricalDataFeed instead. `data_fetcher` is kept alive for the legacy `python -m argus.backtest.data_fetcher --symbols ...` workflow (CLAUDE.md line 118) used when bootstrapping a Parquet cache from Alpaca. Not dead code in the strict sense, but worth flagging in the broader legacy-code conversation (see P1-E2's M5). | No runtime impact on production paths. Keeps Alpaca SDK in the dependency tree. | Re-assess as part of the larger walk-forward + VectorBT retirement conversation (P1-E2 M5). If `scripts/populate_historical_cache.py` + `HistoricalDataFeed.download()` fully cover the bootstrap case, `data_fetcher.py` is a candidate for deletion. | `safe-during-trading` |
| L7 | [scanner_simulator.py:225–270](../../../argus/backtest/scanner_simulator.py#L225) | **`ScannerSimulator._extract_daily_prices` re-computes `trading_date` from `timestamp`** even though `HistoricalDataFeed.load()` already attaches a `trading_date` column at [historical_data_feed.py:168-170](../../../argus/backtest/historical_data_feed.py#L168-L170). The scanner takes a raw `bar_data` dict and does the tz-localize + tz-convert dance a second time. | Mild inefficiency. Not a correctness issue (both computations produce the same ET date). | `ScannerSimulator._extract_daily_prices` could accept a pre-computed `trading_date` and skip the re-computation. Or assert that the column exists and use it directly. | `safe-during-trading` |

---

## COSMETIC Findings

| # | File:Line | Finding | Impact | Suggested Fix | Safety |
|---|-----------|---------|--------|---------------|--------|
| C1 | [engine.py:1027–1028, docstring](../../../argus/backtest/engine.py#L1027-L1028) | `_create_strategy` docstring says "Handles all 7 strategy types" but lists only 7 in the docstring while the actual dispatch covers **15** (the 5 standalone + 10 PatternModule). Docstring is stale since the Sprint 29/31A expansion. | Developer confusion. | Update docstring: "Handles all 15 strategy types — 5 standalone (ORB/scalp, VWAP Reclaim, Afternoon, R2G) + 10 PatternModule (Bull Flag, Flat Top, Dip & Rip, HOD Break, ABCD, Gap & Go, PM High Break, Micro Pullback, VWAP Bounce, Narrow Range)." | `safe-during-trading` |
| C2 | [engine.py:1041–1072](../../../argus/backtest/engine.py#L1041-L1072) | Long `if/elif` chain for 15 StrategyType values with trailing `else: raise ValueError`. A lookup dict (`{StrategyType.BULL_FLAG: self._create_bull_flag_strategy, ...}`) would be denser and `StrategyType` is already a StrEnum. | Readability + extensibility. Adding a 16th strategy means another `elif`. | Replace with `dispatch: dict[StrategyType, Callable[[Path], BaseStrategy]] = {...}; return dispatch[strategy_type](config_dir)` with a `KeyError` handler. | `safe-during-trading` |
| C3 | [engine.py:2189](../../../argus/backtest/engine.py#L2189) | `str(self._config.strategy_type)` is written to the `*.meta.json`. Since `StrategyType` is a `StrEnum`, `str(StrategyType.BULL_FLAG)` is `"bull_flag"` (the value), which is correct — but `StrategyType.BULL_FLAG.value` would be more explicit and robust against any future enum-repr changes. | None today. | Use `.value` explicitly. | `safe-during-trading` |
| C4 | [engine.py:398–420](../../../argus/backtest/engine.py#L398-L420) | Nested `getattr(getattr(getattr(self._strategy, "config", None), "risk_limits", None), "max_loss_per_trade_pct", 0.01)` — three-layer defensive `getattr`. This is legacy-sizing fallback for `share_count==0` signals. It works but is fragile and hard to read. All current strategies set `share_count=0` and all carry a config with `risk_limits`, so the two inner `getattr(... None)` defaults are essentially dead. | Readability. | Replace with a typed helper: `_legacy_max_loss_pct(strategy) -> float` that narrows via isinstance and returns 0.01 on miss. | `safe-during-trading` |
| C5 | [config.py:117–142](../../../argus/backtest/config.py#L117-L142) | `BacktestConfig` carries ~20 strategy-specific fields (`vwap_min_pullback_pct`, `consolidation_atr_ratio`, `r2g_min_gap_down_pct`, ...). `BacktestEngineConfig` does NOT carry these — overrides flow through `config_overrides: dict[str, Any]` instead. The divergence reflects that `BacktestConfig` (for ReplayHarness) predates the `config_overrides` pattern. Legacy surface area. | No active bug — `BacktestConfig` is the Replay Harness input, `BacktestEngineConfig` is the engine input, they are independent. Just sprawl. | Consider collapsing the strategy-specific fields on `BacktestConfig` into its own `config_overrides` dict when ReplayHarness and BacktestEngine converge (post-P1-E2 M5 — out of scope for fix-now). | `read-only-no-fix-needed` |

---

## Answered Audit Questions

### Q1 — Cleanup Tracker #1 (unreachable `else`)

**Confirmed.** [engine.py:372](../../../argus/backtest/engine.py#L372): `strategy_id = self._strategy.strategy_id if self._strategy else self._config.strategy_id`. Reachability proof:
- `self._strategy` is `None` only before line 367.
- Line 367: `self._strategy = self._create_strategy(config_dir)`.
- `_create_strategy` always returns a `BaseStrategy` subclass instance or raises `ValueError` at line 1072.
- Therefore, at line 372 `self._strategy` is guaranteed non-None, and the `else self._config.strategy_id` branch is unreachable.

Filed as **L1** above. Safety: `safe-during-trading` (dead conditional, zero runtime change).

### Q2 — DEF-143 Status

**Fully resolved.** All 10 PatternModule strategy factories in `_create_*_strategy()` use `build_pattern_from_config(config, "<pattern_name>")`:

| Pattern | File:Line | Status |
|---------|-----------|--------|
| Bull Flag | [engine.py:1243](../../../argus/backtest/engine.py#L1243) | ✅ factory |
| Flat Top | [engine.py:1274](../../../argus/backtest/engine.py#L1274) | ✅ factory |
| Dip & Rip | [engine.py:1305](../../../argus/backtest/engine.py#L1305) | ✅ factory |
| HOD Break | [engine.py:1336](../../../argus/backtest/engine.py#L1336) | ✅ factory |
| ABCD | [engine.py:1370](../../../argus/backtest/engine.py#L1370) | ✅ factory |
| Gap & Go | [engine.py:1404](../../../argus/backtest/engine.py#L1404) | ✅ factory |
| PM High Break | [engine.py:1439](../../../argus/backtest/engine.py#L1439) | ✅ factory |
| Micro Pullback | [engine.py:1470](../../../argus/backtest/engine.py#L1470) | ✅ factory |
| VWAP Bounce | [engine.py:1501](../../../argus/backtest/engine.py#L1501) | ✅ factory |
| Narrow Range | [engine.py:1532](../../../argus/backtest/engine.py#L1532) | ✅ factory |

CLAUDE.md and MEMORY.md already reflect this (Sprint 31A S1). **No new finding.** Audit simply confirms the status — `--params` sweeps correctly propagate detection parameters through the pattern constructor for all 10 patterns.

### Q3 — DEF-153 Status (config_fingerprint wiring)

**Resolved and correct.** The wiring at [engine.py:370–375](../../../argus/backtest/engine.py#L370-L375) correctly handles non-PatternModule cases:
1. **Non-PatternModule strategies called directly (CLI)** — `BacktestEngineConfig.config_fingerprint` defaults to `None`; the outer `if self._config.config_fingerprint` check short-circuits; nothing is registered; OrderManager's `_fingerprint_registry.get(strategy_id)` returns `None` when looked up at close-out time ([order_manager.py:2696](../../../argus/execution/order_manager.py#L2696)) — so the `config_fingerprint` column on the trade row is correctly `NULL`.
2. **Non-PatternModule strategies called via ExperimentRunner** — `fingerprint` is always computed from the merged param dict ([runner.py:113](../../../argus/intelligence/experiments/runner.py#L113)) and is registered; the trade row carries the correct fingerprint.
3. **PatternModule strategies** — identical behavior via factory-built pattern.

End-to-end chain validated: `BacktestEngineConfig.config_fingerprint` → `OrderManager._fingerprint_registry` → `Trade.config_fingerprint` column (`schema.sql:36`). The live path in [main.py:1094-1095](../../../argus/main.py#L1094-L1095) uses the same `getattr(..., None)` + `register_strategy_fingerprint` pattern, so live and backtest are symmetric.

The only nit is the unreachable ternary `else` (L1 above), which is a cleanup, not a correctness issue.

### Q4 — AMD-7 Bar-Processing Order

**Consistent across all three consumers.** Grep on `AMD-7` yields matching three-step comments in:

1. **BacktestEngine** ([engine.py:781, 806, 878](../../../argus/backtest/engine.py#L781)) — Step 1 prior-state effective stop, Step 2 evaluate exit, Step 3 update state for next bar.
2. **CounterfactualTracker** ([counterfactual.py:496, 536, 550](../../../argus/intelligence/counterfactual.py#L496)) — same three steps, identical comments.
3. **OrderManager** — no explicit `AMD-7` label, but the live tick path ([order_manager.py:738–765](../../../argus/execution/order_manager.py#L738)) updates watermark + trail in `on_tick`, and escalation runs in the poll loop ([order_manager.py:1553–1578](../../../argus/execution/order_manager.py#L1553)). This is **not identical** to BacktestEngine's per-bar escalation check — in live, escalation is time-based (polled async); in backtest, escalation is checked synchronously per bar. The live design is correct (escalation is wall-clock triggered), and backtest's per-bar check is a faithful simulation of the polled escalation (it catches the same phase transitions once per bar). No bug, but worth documenting for anyone who compares the two code paths.

**Recommendation:** Flag this timing-model divergence in P1-D1 (Counterfactual) or P1-C1 (Order Manager) findings for cross-reference. Currently only the inline `# escalation checked in poll loop` comment at [order_manager.py:765](../../../argus/execution/order_manager.py#L765) explains the split.

### Q4.2 — `_BacktestPosition` Fields

All 12 fields on `_BacktestPosition` are present and initialized:
- Required (5): `symbol`, `strategy_id`, `entry_price`, `entry_time`, `stop_price`, `high_watermark`
- Trail/escalation (6): `trail_active` (default False), `trail_stop_price` (0.0), `escalation_phase_index` (-1), `exit_config` (None), `atr_value` (None), `t1_filled` (False)

The 6 trail/escalation fields project-knowledge calls out are all present. Entry initialization via `_sync_bt_position` at [engine.py:658–692](../../../argus/backtest/engine.py#L658-L692) reads from `ManagedPosition` and invokes `compute_trailing_stop` for `activation == "immediate"`. Correct.

### Q5 — Cache Consumer Correctness

**BacktestEngine reads from the ORIGINAL cache exclusively.** Evidence:

| Location | Path | Reads |
|----------|------|-------|
| [engine.py:2258](../../../argus/backtest/engine.py#L2258) (CLI default) | `data/databento_cache` | `--cache-dir` default |
| [config.py:163](../../../argus/backtest/config.py#L163) | `data/databento_cache` | `BacktestEngineConfig.cache_dir` default |
| [engine.py:437](../../../argus/backtest/engine.py#L437) (auto-detect) | `self._config.cache_dir` | Walks directory |
| [engine.py:457](../../../argus/backtest/engine.py#L457) | `self._config.cache_dir` | `HistoricalDataFeed(cache_dir=...)` |
| [engine.py:1768, 1773](../../../argus/backtest/engine.py#L1768) | `self._config.cache_dir / "SPY"` | SPY daily aggregation for regime |
| [historical_data_feed.py:244](../../../argus/backtest/historical_data_feed.py#L244) | `{cache_dir}/{SYMBOL}/{YYYY-MM}.parquet` | Per-month file reads |

`HistoricalDataFeed.load()` reads per-month files — matches the original cache layout exactly. The consolidated cache (`{SYMBOL}/{SYMBOL}.parquet`) would silently miss data here: `_month_range()` at [historical_data_feed.py:209](../../../argus/backtest/historical_data_feed.py#L209) generates `(year, month)` pairs and `_parquet_path()` assembles `{cache_dir}/{SYMBOL}/{YYYY}-{MM}.parquet`; the consolidated cache has no such files, so every month iteration would fail to load any bars, producing zero-bar symbols without error.

**The operator invariant from Sprint 31.85 is correctly enforced by the code.** `HistoricalQueryService` (DuckDB) is the only consumer pointed at the consolidated cache, and `config/historical_query.yaml` is the only path that controls it. No cross-contamination possible without an operator mistake.

**One defensive gap:** nothing in `HistoricalDataFeed` validates that `cache_dir` contains per-month files rather than per-symbol files. If an operator mis-configured `BacktestEngineConfig.cache_dir` (or `scripts/run_experiment.py --cache-dir`) to point at the consolidated cache, the backtest would run silently with zero bars and produce an empty `BacktestResult`. Not a bug per se — same outcome as any empty cache — but a WARNING log when `_load_data` loads zero bars across all symbols would help.

Filed as an implicit observation rather than a finding. Consider: add `logger.warning` in `_load_data` if `len(self._trading_days) == 0` after load, naming the cache_dir and the requested date range.

### Q6 — SynchronousEventBus Usage

**Exclusively SyncEventBus.** [engine.py:306–307](../../../argus/backtest/engine.py#L306-L307) constructs `SyncEventBus()`; no fallback path to async `EventBus`. The SyncEventBus subscribes handlers in order, awaits them sequentially in `publish()`, and assigns monotonic sequence numbers via `replace(event, sequence=self._sequence)`. See [sync_event_bus.py:58–75](../../../argus/core/sync_event_bus.py#L58-L75). Semantically equivalent to the async bus minus the `asyncio.create_task` fan-out — subscribers still run in subscription order.

The 4 `# type: ignore[arg-type]` comments at [engine.py:333, 349, 356, 424](../../../argus/backtest/engine.py#L333) reflect the type-hint gap called out in **L5**.

### Q7 — Multi-Day Orchestration

**7.1 Session boundaries.** `_run_trading_day` sets clock to 9:25 AM ET (pre-market, [engine.py:543–549](../../../argus/backtest/engine.py#L543)), resets daily state, then iterates bars in timestamp order. The bar-level loop does not distinguish pre-market / intraday / EOD per-bar — strategies filter via their own operating windows. This is consistent with live-path behavior (where `AlpacaScanner` runs pre-market and strategies are time-gated).

**7.2 EOD flatten.** `eod_flatten` is called at [engine.py:612–621](../../../argus/backtest/engine.py#L612-L621) with clock set to `eod_flatten_time` (default 15:50 ET). It calls `OrderManager.eod_flatten()` — the production method. Pass 1 / Pass 2 semantics are inside OrderManager and are not duplicated here. ✓

**7.3 Holiday handling.** No explicit filter (see **L4**). Implicit via Parquet data coverage.

**7.4 DST.** Pre-market and EOD datetime constructions both use `tzinfo=ET` (ZoneInfo) then `.astimezone(UTC)` — no hardcoded offsets. DST-correct.

### Q8 — Scanner Simulator

**8.1 Data source.** [scanner_simulator.py:225–270](../../../argus/backtest/scanner_simulator.py#L225) — gap computation from the same Parquet bars as the strategy consumes (`(first_open_today - last_close_prev_day) / last_close_prev_day`). No external data source. Matches DEC-052.

**8.2 Universe filter.** **Does not match production UM logic.** Scanner uses hardcoded `min_gap_pct=0.02`, `min_price=10.0`, `max_price=500.0` defaults (or CLI overrides via `BacktestEngineConfig.scanner_*` fields). Production UM (`argus/data/universe_manager.py`) applies richer criteria (price, avg volume, market cap, sector exclusions, reference-data gating). This is **intentional simplification** per DEC-052 — Databento historical feed doesn't give the scanner pre-market volume patterns (DEF-007). Tradeoff is documented.

If an experiment wants to pre-filter by the production UM's universe, the path is `scripts/run_experiment.py --universe-filter {pattern}.yaml` (Sprint 31A.75 / 31.5), which resolves symbols via `HistoricalQueryService.validate_symbol_coverage` *before* the BacktestEngine CLI is invoked. This is architecturally sound but worth noting for anyone who wonders why `ScannerSimulator` doesn't consult the UM directly.

### Q9 — Risk Overrides (DEC-359)

`risk_overrides` dict on `BacktestEngineConfig` ([config.py:199–203](../../../argus/backtest/config.py#L199-L203)):
```python
risk_overrides: dict[str, Any] = Field(default_factory=lambda: {
    "account.min_position_risk_dollars": 1.0,
    "account.cash_reserve_pct": 0.05,
    "cross_strategy.max_single_stock_pct": 0.50,
})
```

Applied via `_load_risk_config` ([engine.py:1668–1677](../../../argus/backtest/engine.py#L1668)) — dot-separated key → `setattr(sub_config, field, value)` on the loaded RiskConfig. Production paths are unaffected: `risk_overrides` lives on `BacktestEngineConfig` only, never touches `main.py` or `config/risk_limits.yaml` at read time. Live loads the YAML directly; backtest loads YAML then applies its overrides on the in-memory copy. ✓ No leakage.

**9.2 Path validation.** Unknown override keys produce a `logger.warning` ("Unknown risk override key: %s"). Better than the silent fallback in `_apply_config_overrides` (M1). Consider symmetry: if `_apply_config_overrides` logged the same warning on unresolvable paths, M1 would be substantially mitigated.

### Q10 — StrategyType Enum & Pattern Factory

**10.1 `StrategyType` enum** — 15 values at [config.py:11–28](../../../argus/backtest/config.py#L11-L28): `ORB_BREAKOUT`, `ORB_SCALP`, `VWAP_RECLAIM`, `AFTERNOON_MOMENTUM`, `RED_TO_GREEN`, `BULL_FLAG`, `FLAT_TOP_BREAKOUT`, `DIP_AND_RIP`, `HOD_BREAK`, `ABCD`, `GAP_AND_GO`, `PREMARKET_HIGH_BREAK`, `MICRO_PULLBACK`, `VWAP_BOUNCE`, `NARROW_RANGE_BREAKOUT`. Matches the 15 current strategies.

**10.2 `_PATTERN_TO_STRATEGY_TYPE`** ([runner.py:54–70](../../../argus/intelligence/experiments/runner.py#L54-L70)) — 10 entries, covering all 10 PatternModule patterns. Complete. ABCD carries a DEF-122 performance note. Gap & Go / PM High Break carry the "reference-data" note pointing at `_supply_daily_reference_data`.

**10.3 `_supply_daily_reference_data`** ([engine.py:1619–1647](../../../argus/backtest/engine.py#L1619)) — correctly reads prior closes from `self._bar_data` (the original-cache DataFrame loaded by HistoricalDataFeed) via `_derive_prior_closes`. Same cache as the strategy consumes. ✓

**10.4 `_derive_prior_closes`** ([engine.py:1577–1617](../../../argus/backtest/engine.py#L1577)) — finds the prior trading day in `self._trading_days` (`day_idx - 1`) and returns the last bar's close. Returns `{}` when `day_idx == 0` (first day). Correct edge handling — first day has no prior close available.

### Q11 — Config Fingerprint Flow

End-to-end chain:

```
ExperimentRunner.run_sweep()
  ↓ compute_parameter_fingerprint(merged_params) → 16-char SHA256 prefix
  ↓ _run_single_backtest() worker args["fingerprint"] = fingerprint
  ↓ BacktestEngineConfig(config_fingerprint=fingerprint)
BacktestEngine._setup()
  ↓ register_strategy_fingerprint(strategy_id, fingerprint) on OrderManager
OrderManager._fingerprint_registry[strategy_id] = fingerprint
  ↓ (on trade close)
OrderManager._handle_close() reads _fingerprint_registry.get(position.strategy_id)
  ↓
Trade.config_fingerprint → TradeLogger → trades table (config_fingerprint TEXT column)
```

All links verified. Non-PatternModule path (direct CLI without a fingerprint): `config_fingerprint = None` → block skipped → registry defaults to `None` at lookup → trade row's `config_fingerprint = NULL`. Documented and handled.

---

## Positive Observations

1. **AMD-7 ordering is rigorously consistent** between BacktestEngine and CounterfactualTracker — same 3-step structure, same comment labels, same `evaluate_bar_exit` call. The divergence with live OrderManager (trail-in-tick, escalation-in-poll) is a correct design choice and is motivated — backtest has no wall-clock, so it folds escalation into the per-bar loop. Worth preserving.
2. **`SimulatedBroker + SyncEventBus` pairing in _setup** is clean and obvious: `SyncEventBus()` is explicit, `BacktestDataService(SyncEventBus)` bridges, `RiskManager` and `OrderManager` are passed the same bus. A reader new to the codebase can see "this is the sync backtest wiring" in ~30 lines. Sprint 27 stuck the landing here.
3. **Cache separation contract holds.** Every read from `self._config.cache_dir` in engine.py is a per-month file access through `HistoricalDataFeed` (with format `{YYYY-MM}.parquet`). There is no code path in the engine that would work with the consolidated cache layout, so the Sprint 31.85 invariant is enforced structurally, not just by convention.
4. **`_PATTERN_TO_STRATEGY_TYPE` mapping in experiments/runner.py carries inline operational notes** — the DEF-122 ABCD O(n³) warning and the Gap & Go / PM High Break reference-data note are right where a sweep author would look. This is the kind of narrated mapping that prevents accidents.
5. **DEF-153 non-PatternModule handling via `getattr(..., None)` + `register_strategy_fingerprint` with `fingerprint: str | None`** is symmetric between live (main.py:1094) and backtest (engine.py:370). Same pattern, same semantics. Future sprints that add strategy types don't need to revisit fingerprint wiring.
6. **`build_pattern_from_config()` completeness** — all 10 PatternModule factory methods in BacktestEngine use the factory (DEF-143 resolution is uniform across every pattern). Consistent enough that the 10 methods are near-identical boilerplate (a prime candidate for C2's dispatch-dict refactor).
7. **`risk_overrides` logs `Unknown risk override key: %s`** for unresolvable paths ([engine.py:1677](../../../argus/backtest/engine.py#L1677)). This is the right behavior, and it exposes the gap in M1 — the symmetric code in `_apply_config_overrides` should do the same.

---

## Statistics

- **Files deep-read:** 5 (engine.py, historical_data_feed.py, backtest_data_service.py, replay_harness.py (header), scanner_simulator.py)
- **Files skimmed:** 5 (config.py, metrics.py, manifest.py, tick_synthesizer.py, data_fetcher.py)
- **Cross-ref files opened:** 6 (sync_event_bus.py, order_manager.py slices, counterfactual.py slice, experiments/runner.py slice, main.py fingerprint block, db/schema.sql)
- **Total findings:** 17 (0 critical, 5 medium, 7 low, 5 cosmetic)
- **Safety distribution:**
  - `safe-during-trading`: 14
  - `weekend-only`: 2 (M4, L5 — both touch production strategy or event-bus typing)
  - `read-only-no-fix-needed`: 1 (C5 — BacktestConfig legacy fields)
  - `deferred-to-defs`: 0
- **Estimated Phase 3 fix effort:** 1 small session to bundle M1+M5 (override hygiene) + L1 (tracker #1) + C1/C2/C3/C4 (cosmetic polish) — all `safe-during-trading`, ~1hr total. M2 (iterrows perf) is a standalone benchmark-gated change (~45 min). M3 + L7 + L4 are small independent `safe-during-trading` touches (~15 min each). M4 + L5 are the only `weekend-only` touches, both small (~20 min each). DEF-143 and DEF-153 require no follow-on.

# Fix Session FIX-09-backtest-engine: argus/backtest — BacktestEngine, VectorBT, walk-forward

> Generated from audit Phase 2 on 2026-04-21. Paste into a fresh Claude Code session. This prompt is **standalone** — do not read other FIX-NN prompts.

## Scope

**Findings addressed:** 27
**Files touched:** `../../argus/backtest/backtest_data_service.py`, `../../argus/backtest/config.py`, `../../argus/backtest/data_fetcher.py`, `../../argus/backtest/engine.py`, `../../argus/backtest/report_generator.py`, `../../argus/backtest/scanner_simulator.py`, `../../argus/backtest/vectorbt_pattern.py`, `../../argus/backtest/vectorbt_red_to_green.py`, `../../argus/backtest/walk_forward.py`, `../../tests/backtest/test_vectorbt_data_loading.py`, `tests/backtest/test_walk_forward_engine.py`
**Safety tag:** `weekend-only`
**Theme:** BacktestEngine, VectorBT helpers, Replay Harness, walk-forward, and backtest data service findings.

## Pre-Session Verification (REQUIRED — do not skip)

### 1. Environment check

```bash
# Paper trading MUST be paused. No open positions. No active alerts.
./scripts/launch_monitor.sh status 2>/dev/null || echo "monitor offline (expected for weekend-only)"

# If paper trading is running, STOP before proceeding:
#   ./scripts/stop_live.sh
# Confirm zero open positions at IBKR paper account U24619949 via Command Center.
# This session MAY touch production paths. Do NOT run during market hours.
```

### 2. Baseline test run

```bash
python -m pytest --ignore=tests/test_main.py -n auto -q 2>&1 | tail -3
# Record PASS count here: __________ (baseline)
```

**Expected baseline as of the audit commit:** 4,934 pytest + 846 Vitest
(3 pre-existing failures: 2 date-decay DEF-163 + 1 flaky DEF-150).
If your baseline diverges, pause and investigate before proceeding.

### 3. Branch & workspace

Work directly on `main`. No audit branch. Commit at session end with the
exact message format in the "Commit" section below. If you are midway
through the session and need to stop, commit partial progress with a WIP
marker (`audit(FIX-09): WIP — <reason>`) rather than leaving
uncommitted changes.

## Implementation Order

Findings below are ordered to minimize file churn (edits to the same file are adjacent). Apply in this order:

1. Tests first where new behavior is added.
2. Code edits in the order listed in the Findings section (grouped by file).
3. Docs / audit-report back-annotation last.

**Per-file finding counts (edit hotspots):**

- `../../argus/backtest/engine.py`: 13 findings
- `../../argus/backtest/walk_forward.py`: 3 findings
- `tests/backtest/test_walk_forward_engine.py`: 3 findings
- `../../argus/backtest/backtest_data_service.py`: 1 finding
- `../../argus/backtest/config.py`: 1 finding
- `../../argus/backtest/data_fetcher.py`: 1 finding
- `../../argus/backtest/report_generator.py`: 1 finding
- `../../argus/backtest/scanner_simulator.py`: 1 finding
- `../../argus/backtest/vectorbt_pattern.py`: 1 finding
- `../../argus/backtest/vectorbt_red_to_green.py`: 1 finding
- `../../tests/backtest/test_vectorbt_data_loading.py`: 1 finding

## Findings to Fix

### Finding 1: `P1-E1-M01` [MEDIUM]

**File/line:** [engine.py:1557–1571](../../../argus/backtest/engine.py#L1557-L1571)
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> **`_apply_config_overrides` silently mis-routes an unresolvable dot-path to a flat key.** The `for...else` correctly handles nested keys when every intermediate segment resolves to a dict. But on `break` (intermediate missing or not-a-dict), the fallback at line 1570 tests `if parts[-1] in config_dict` — the *outermost* dict — and sets it there. So `config_overrides = {"nonexistent.max_loss_per_trade_pct": 0.01}` will silently assign `config_dict["max_loss_per_trade_pct"] = 0.01` at the top level if a flat key with the same leaf name happens to exist. Grid sweeps composed automatically from `PatternParam.name` are almost always flat, so this is rarely exercised — but a typo in a hand-written override (`"risk_limit.x"` instead of `"risk_limits.x"`) is swallowed without a warning.

**Impact:**

> Silent misconfiguration during experiment sweeps. Worst case: a sweep runs with the wrong override shape and produces data that looks valid, poisoning downstream analysis.

**Suggested fix:**

> Log a `logger.warning` when a key cannot be resolved at its stated depth; raise if `strict_overrides` config flag is set. Or simpler: drop the flat-key fallback entirely — if the caller wrote dots, honor them.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-09-backtest-engine**`.

### Finding 2: `P1-E1-M02` [MEDIUM]

**File/line:** [engine.py:573](../../../argus/backtest/engine.py#L573)
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> **Per-bar dispatch uses `daily_bars.iterrows()`.** `.claude/rules/backtesting.md` bans `iterrows()` in VectorBT sweep hot paths but is silent on BacktestEngine. For a 24-symbol, 35-month run this is ~6M iterations × Pandas row overhead. Engine performance is acceptable today (≥5× Replay Harness per DEC), but as sweep breadth grows past Sprint 31B, this loop will dominate. Per-row work currently includes 2 tz conversions + `self._broker.set_price` + `feed_bar` + `_check_bracket_orders`.

**Impact:**

> Throughput ceiling on large sweeps. Each bar already pays the SyncEventBus + RiskManager + IndicatorEngine cost; removing `iterrows` would claw back a measurable fraction but not all of it.

**Suggested fix:**

> Convert daily_bars to a dict of NumPy arrays (`timestamps`, `opens`, `highs`, ...) and index by integer. Keep the event dispatch loop but avoid per-row Series construction. Benchmark before/after; keep the change if >15% faster on a representative sweep.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-09-backtest-engine**`.

### Finding 3: `P1-E1-M03` [MEDIUM]

**File/line:** [engine.py:795, 800, 862–863, 971–972](../../../argus/backtest/engine.py#L795)
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> **BacktestEngine reaches into `SimulatedBroker._pending_brackets` (5 call-sites).** The engine filters the private list by symbol + order_type to implement its bar-level fill model. This tightly couples two components and would silently break if `SimulatedBroker` renames or reshapes that list. The canonical way is a public accessor on the broker (e.g., `get_pending_brackets(symbol: str) -> list[Bracket]`).

**Impact:**

> Brittleness risk: any SimulatedBroker internal refactor would need to update 5 BacktestEngine sites. No runtime bug today.

**Suggested fix:**

> Add `SimulatedBroker.get_pending_brackets(symbol, order_type=None)` (read-only) and migrate the 5 call-sites.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-09-backtest-engine**`.

### Finding 4: `P1-E1-M04` [MEDIUM]

**File/line:** [engine.py:1619–1647](../../../argus/backtest/engine.py#L1619-L1647)
**Safety:** `weekend-only`
**Action type:** Code change (`weekend-only`)

**Original finding:**

> **`_supply_daily_reference_data` accesses `self._strategy._pattern` (private).** The PatternBasedStrategy's `_pattern` attribute is read to call `set_reference_data({"prior_closes": ...})`. This mirrors the live-side wiring pattern in main.py's Phase 9.5 and is intentional, but it's still cross-module private access. A public accessor on PatternBasedStrategy (e.g., `set_pattern_reference_data(data)`) would formalize the contract and keep `_pattern` truly private.

**Impact:**

> Same brittleness concern as M3 — works today, but a PatternBasedStrategy refactor would need to update both live + backtest wiring.

**Suggested fix:**

> Add `PatternBasedStrategy.set_pattern_reference_data(data)` forwarder; update main.py and engine.py to use it. Low-risk single-line wrapper.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-09-backtest-engine**`.

### Finding 5: `P1-E1-M05` [MEDIUM]

**File/line:** [engine.py:1543–1546, docstring](../../../argus/backtest/engine.py#L1543-L1546)
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> **`_apply_config_overrides` docstring claims support for dot-separated keys but gives only a flat-key example.** Docstring example is `{"opening_range_minutes": 15}` — not `{"risk_limits.max_loss_per_trade_pct": 0.01}`. Combined with M1's silent-fallback bug, nothing in the surface docs warns a sweep author that a typo'd dot-path will be swallowed.

**Impact:**

> Developer ergonomics: someone tuning nested config may not realize the override was silently dropped.

**Suggested fix:**

> Update docstring with a nested example and a note that dot-path parts must all exist as intermediate dicts. Or fold into M1's fix.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-09-backtest-engine**`.

### Finding 6: `P1-E1-L01` [LOW]

**File/line:** [engine.py:372](../../../argus/backtest/engine.py#L372)
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> **Cleanup tracker #1 confirmed — unreachable `else` branch in fingerprint registration ternary.** `strategy_id = self._strategy.strategy_id if self._strategy else self._config.strategy_id`. `self._strategy` was assigned at line 367 via `self._create_strategy(config_dir)`; `_create_strategy` returns a `BaseStrategy` or raises `ValueError` at line 1072 on unknown type. There is no execution path where line 372 runs with `self._strategy is None`. Similarly, the `self._order_manager is not None` guard at line 371 is unreachable-false — `_order_manager` was assigned at line 355 and its absence would have raised earlier.

**Impact:**

> Dead conditional. Zero runtime impact. Slight cognitive tax for readers.

**Suggested fix:**

> Replace line 371–375 block with `if self._config.config_fingerprint:` and simplify line 372 to `strategy_id = self._strategy.strategy_id`. Keep the `DEF-153` comment.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-09-backtest-engine**`.

### Finding 7: `P1-E1-L02` [LOW]

**File/line:** [engine.py:1778–1784](../../../argus/backtest/engine.py#L1778-L1784)
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> **`_load_spy_daily_bars` computes `margin_start` with awkward inline conditional** (3-month lookback for SMA-50 warmup). The current form is correct but hard to read; `dateutil.relativedelta` or a simple month-arithmetic helper would be clearer.

**Impact:**

> Readability only.

**Suggested fix:**

> Replace with `margin_start = (start_date.replace(day=1) - relativedelta(months=3))`. No dependency added — `python-dateutil` is already transitively pulled in. Or write a small `_subtract_months(d, n)` helper.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-09-backtest-engine**`.

### Finding 8: `P1-E1-L03` [LOW]

**File/line:** [engine.py:2081](../../../argus/backtest/engine.py#L2081)
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> **`_compute_execution_quality_adjustment` uses hardcoded `avg_entry_price = 50.0`** as the denominator for `slippage_per_share → bps` conversion, with a TODO to derive it from trade data. The resulting Sharpe adjustment is a first-order approximation and the magnitude is sensitive to this constant. Not a bug — the calibrated slippage model's confidence gates the output, and the doc-comment is honest — but the $50 midpoint can be off by 3× on a real basket (NVDA $900, GME $15).

**Impact:**

> Under-/over-attribution of execution_quality_adjustment. Downstream consumers (MultiObjectiveResult) treat this as annualized-Sharpe delta; a 3× error would materially shift a borderline promote/don't-promote decision.

**Suggested fix:**

> Derive avg entry price from the trade log via `trade_logger.get_trades_by_date_range(...)` already called on line 1975. Use `sum(entry_price × shares) / sum(shares)` to weight.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-09-backtest-engine**`.

### Finding 9: `P1-E1-L04` [LOW]

**File/line:** [engine.py: no market_calendar import](../../../argus/backtest/engine.py)
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> **No explicit holiday filtering** — trading days are derived from whatever dates appear in the loaded Parquet data (`trading_date` column). Databento EQUS.MINI does not return bars on NYSE holidays, so the implicit filter is correct in practice. But the engine has no guardrail: if a corrupted cache somehow contained a holiday-dated bar, the engine would dutifully process it. `argus/core/market_calendar.py` exists for exactly this purpose and is used by live trading.

**Impact:**

> No active bug — depends on Databento's honoring of the NYSE calendar. Low but non-zero risk if a manual cache patch ever creates one.

**Suggested fix:**

> Add a `market_calendar.is_market_holiday(d)` filter in `_load_data` after `self._trading_days = sorted(all_dates)` and drop holiday dates with a WARNING log. Belt-and-suspenders.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-09-backtest-engine**`.

### Finding 10: `P1-E1-C01` [COSMETIC]

**File/line:** [engine.py:1027–1028, docstring](../../../argus/backtest/engine.py#L1027-L1028)
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> `_create_strategy` docstring says "Handles all 7 strategy types" but lists only 7 in the docstring while the actual dispatch covers **15** (the 5 standalone + 10 PatternModule). Docstring is stale since the Sprint 29/31A expansion.

**Impact:**

> Developer confusion.

**Suggested fix:**

> Update docstring: "Handles all 15 strategy types — 5 standalone (ORB/scalp, VWAP Reclaim, Afternoon, R2G) + 10 PatternModule (Bull Flag, Flat Top, Dip & Rip, HOD Break, ABCD, Gap & Go, PM High Break, Micro Pullback, VWAP Bounce, Narrow Range)."

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-09-backtest-engine**`.

### Finding 11: `P1-E1-C02` [COSMETIC]

**File/line:** [engine.py:1041–1072](../../../argus/backtest/engine.py#L1041-L1072)
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> Long `if/elif` chain for 15 StrategyType values with trailing `else: raise ValueError`. A lookup dict (`{StrategyType.BULL_FLAG: self._create_bull_flag_strategy, ...}`) would be denser and `StrategyType` is already a StrEnum.

**Impact:**

> Readability + extensibility. Adding a 16th strategy means another `elif`.

**Suggested fix:**

> Replace with `dispatch: dict[StrategyType, Callable[[Path], BaseStrategy]] = {...}; return dispatch[strategy_type](config_dir)` with a `KeyError` handler.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-09-backtest-engine**`.

### Finding 12: `P1-E1-C03` [COSMETIC]

**File/line:** [engine.py:2189](../../../argus/backtest/engine.py#L2189)
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> `str(self._config.strategy_type)` is written to the `*.meta.json`. Since `StrategyType` is a `StrEnum`, `str(StrategyType.BULL_FLAG)` is `"bull_flag"` (the value), which is correct — but `StrategyType.BULL_FLAG.value` would be more explicit and robust against any future enum-repr changes.

**Impact:**

> None today.

**Suggested fix:**

> Use `.value` explicitly.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-09-backtest-engine**`.

### Finding 13: `P1-E1-C04` [COSMETIC]

**File/line:** [engine.py:398–420](../../../argus/backtest/engine.py#L398-L420)
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> Nested `getattr(getattr(getattr(self._strategy, "config", None), "risk_limits", None), "max_loss_per_trade_pct", 0.01)` — three-layer defensive `getattr`. This is legacy-sizing fallback for `share_count==0` signals. It works but is fragile and hard to read. All current strategies set `share_count=0` and all carry a config with `risk_limits`, so the two inner `getattr(... None)` defaults are essentially dead.

**Impact:**

> Readability.

**Suggested fix:**

> Replace with a typed helper: `_legacy_max_loss_pct(strategy) -> float` that narrows via isinstance and returns 0.01 on miss.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-09-backtest-engine**`.

### Finding 14: `P1-E2-M03` [MEDIUM]

**File/line:** [argus/backtest/walk_forward.py:40-41](../../../argus/backtest/walk_forward.py#L40-L41) + R2G branch
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> **R2G walk-forward branch is unreachable via operational path.** `revalidate_strategy.py:42` has `_WALK_FORWARD_SUPPORTED = {"orb", "orb_scalp", "vwap_reclaim", "afternoon_momentum"}` — red_to_green is excluded. R2G can only be invoked via `python -m argus.backtest.walk_forward --strategy red_to_green`, which is not invoked anywhere. The import of `R2GSweepConfig` / `run_r2g_sweep` at the top of walk_forward.py is only kept alive because the R2G branch code still references them.

**Impact:**

> Dead branch inside an otherwise-live file. Removing the R2G branch would let vectorbt_red_to_green.py stop being walk_forward-imported, but it would still be needed for `load_symbol_data` via vectorbt_pattern.py — UNLESS M1 is adopted, in which case vectorbt_red_to_green.py would also lose its only remaining live consumer.

**Suggested fix:**

> Couple with M1 and M4: if PatternBacktester is deleted AND the R2G branch is excised from walk_forward.py, then vectorbt_red_to_green.py can itself be deleted (another ~1,025 LOC + ~573 test LOC). Defer this as a Phase 3 follow-on after M1 lands.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-09-backtest-engine**`.

### Finding 15: `P1-E2-M05` [MEDIUM]

**File/line:** [argus/backtest/walk_forward.py](../../../argus/backtest/walk_forward.py) (2,743 LOC)
**Safety:** `read-only-no-fix-needed`
**Action type:** Verify + audit-report annotation (no code change expected)

**Original finding:**

> **walk_forward.py is LIVE but surfaces a strategic question: is VectorBT-IS walk-forward still the right path, or should revalidate_strategy.py migrate fully to BacktestEngine for IS as well?** The IS path inside `run_fixed_params_walk_forward` invokes VectorBT `run_sweep` from 4 different files (`vectorbt_orb`, `vectorbt_orb_scalp`, `vectorbt_vwap_reclaim`, `vectorbt_afternoon_momentum`). The OOS path uses ReplayHarness (or BacktestEngine via `oos_engine="backtest_engine"`). If the IS path migrated to BacktestEngine (via `scripts/run_experiment.py` which already does sweeps via `ExperimentRunner` + `ProcessPoolExecutor`), then walk_forward.py + all 4 vectorbt_*.py files could collectively be retired.

**Impact:**

> This is a ~6,713 LOC retirement opportunity, plus ~4,108 LOC of related tests. Replacement requires: adding walk-forward windowing + WFE computation on top of ExperimentRunner. ExperimentStore already gives per-window SQLite persistence.

**Suggested fix:**

> Too large to fix-now. Open a new **DEF** entry: "Migrate walk-forward IS path from VectorBT to BacktestEngine (retire walk_forward.py + 4 vectorbt_*.py, DEC-149 supersede gate)." Priority: MEDIUM. Trigger: next sprint planning where validation tooling is on the agenda (likely Sprint 33+).

**Required steps for this finding:**
1. Re-read the original audit finding in-context (file + line).
2. Run a quick verification (grep, test, or inspection) to confirm
   the observation still holds. Record the verification command and
   output below.
3. If verified AND the "Suggested fix" above is purely observational
   (e.g. "note", "document", "no action"): back-annotate the audit
   report row with `~~description~~ **RESOLVED-VERIFIED FIX-09-backtest-engine**`
   and move on. Make no code change.
4. If verified AND the "Suggested fix" explicitly asks for a DEF
   entry or a small code change (e.g. "Open a new DEF entry",
   "Add a comment", "Remove the stub"): treat this finding as if it
   were tagged `deferred-to-defs` — apply the suggested fix AND add
   a DEF-NNN entry to CLAUDE.md (grep for the highest existing
   DEF-NNN and increment). Back-annotate as
   `**RESOLVED FIX-09-backtest-engine**` (not -VERIFIED, since a change was
   made). Reference the DEF ID in the commit bullet.
5. If the verification *contradicts* the finding (i.e. it is now a
   real bug that requires a larger fix than the suggested_fix
   anticipates): **STOP**, log a note here, and escalate to the
   operator rather than silently applying an invented fix.

### Finding 16: `P1-E2-C02` [COSMETIC]

**File/line:** [argus/backtest/walk_forward.py:526,1910](../../../argus/backtest/walk_forward.py#L526)
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> Two lazy in-function imports of `vectorbt_afternoon_momentum`. They duplicate the module-level import at line 36.

**Impact:**

> Minor duplication; likely an artifact from when the module was smaller.

**Suggested fix:**

> Remove the two lazy imports; the top-level import already satisfies them.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-09-backtest-engine**`.

### Finding 17: `P1-G1-M01` [MEDIUM]

**File/line:** [tests/backtest/test_walk_forward_engine.py:559-626](tests/backtest/test_walk_forward_engine.py#L559-L626)
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> **Timing-flaky test not tracked in DEF table.** `test_speed_benchmark` asserts `speed_ratio = replay_time / engine_time >= 3.0` with 10ms vs 50ms `asyncio.sleep()` delays. Under xdist worker contention (no-cov run at 138.9s) it failed; under coverage overhead (single-worker dominated, 191.6s) it passed. `testing.md` explicitly warns against sleep-bound tests >3s; this test's *assertion* is wall-clock-contention-bound even at 10ms.

**Impact:**

> Silent flake. Not in CLAUDE.md Known Issues list. Next operator CI run could produce a random red. Worse: it measures scheduler behavior, not the code's actual speedup.

**Suggested fix:**

> Either (a) replace the timing assertion with a functional assertion that both engines produce equal results on identical mocked inputs, or (b) increase the per-call delay to 100ms+ and loosen the ratio to 2.0x so scheduler jitter is dominated by the measured quantity. Open a DEF for the flake.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-09-backtest-engine**`.

### Finding 18: `P1-G2-M02` [MEDIUM]

**File/line:** [tests/backtest/test_walk_forward_engine.py:530-550](tests/backtest/test_walk_forward_engine.py#L530-L550)
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> **`test_divergence_documented` literally asserts nothing.** The body is `assert True, "<long doc message>"` — the test name implies behavior verification but the code is a docstring container. Silent failure mode #4.2 from the prompt: "Tests asserting nothing after setup (setup runs, no assertion — effectively a smoke test mislabeled as a unit test)." A reader scanning the test file sees `test_divergence_documented` in green and assumes coverage; there is none.

**Impact:**

> Produces false confidence. The comment explicitly calls this out ("# This test is intentionally documentary — it always passes"), but that intent is hidden inside the function — the pytest collector/reporter treats it as a real test.

**Suggested fix:**

> Either (a) delete the test and move the docstring into a module-level docstring or `docs/backtesting.md` block, or (b) replace with an `assert isinstance(BacktestEngine, type)` or similar structural check that at least fails if the documented class goes away, or (c) promote it to a real test that runs both engines on identical bars and asserts directional agreement.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-09-backtest-engine**`.

### Finding 19: `P1-G2-M03` [MEDIUM]

**File/line:** [tests/backtest/test_walk_forward_engine.py:558-626](tests/backtest/test_walk_forward_engine.py#L558-L626)
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> **`test_speed_benchmark` is tautological + flaky.** The mocks include hand-coded `asyncio.sleep(0.01)` and `asyncio.sleep(0.05)` delays; the assertion `speed_ratio >= 3.0` then measures the ratio of the mocked delays, not any production code behavior. P1-G1 M1 flagged the flake; this finding adds the tautology characterization. A refactor that replaces `BacktestEngine.run` with a genuinely slow implementation would not fail this test — it measures the mocks only.

**Impact:**

> Same as G1 M1 plus: the test cannot detect any real performance regression because the real engines are never exercised.

**Suggested fix:**

> Replace with a functional equivalence check: run both engines over identical 5-day mocked fixtures and assert same-sign P&L and trade-count-within-20% — same assertion used at [line 514-522](tests/backtest/test_walk_forward_engine.py#L514-L522) for a related test. Delete the mocked-delay speed assertion.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-09-backtest-engine**`.

### Finding 20: `P1-E1-L05` [LOW]

**File/line:** [backtest_data_service.py:42](../../../argus/backtest/backtest_data_service.py#L42)
**Safety:** `weekend-only`
**Action type:** Code change (`weekend-only`)

**Original finding:**

> **`BacktestDataService.__init__` is typed `event_bus: EventBus` but receives `SyncEventBus` in BacktestEngine** (engine.py:333 carries `# type: ignore[arg-type]`). The Replay Harness uses `EventBus`, the BacktestEngine uses `SyncEventBus`; both share this class. The concrete duck-typing works because both buses expose `publish(event)` and `subscribe(type, handler)` with compatible signatures.

**Impact:**

> Type-hint lie. Pylance users get false-positive errors when switching bus types. Four `# type: ignore[arg-type]` comments in engine.py (333, 349, 356, 424) are patching around this.

**Suggested fix:**

> Introduce a small `Protocol` in `argus.core.event_bus` (`class EventBusProtocol(Protocol): def subscribe(...); async def publish(...)`) that both `EventBus` and `SyncEventBus` satisfy. Type `BacktestDataService.__init__`, `RiskManager.__init__`, and `OrderManager.__init__` against that Protocol. Remove the 4 `# type: ignore`s.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-09-backtest-engine**`.

### Finding 21: `P1-E1-C05` [COSMETIC]

**File/line:** [config.py:117–142](../../../argus/backtest/config.py#L117-L142)
**Safety:** `read-only-no-fix-needed`
**Action type:** Verify + audit-report annotation (no code change expected)

**Original finding:**

> `BacktestConfig` carries ~20 strategy-specific fields (`vwap_min_pullback_pct`, `consolidation_atr_ratio`, `r2g_min_gap_down_pct`, ...). `BacktestEngineConfig` does NOT carry these — overrides flow through `config_overrides: dict[str, Any]` instead. The divergence reflects that `BacktestConfig` (for ReplayHarness) predates the `config_overrides` pattern. Legacy surface area.

**Impact:**

> No active bug — `BacktestConfig` is the Replay Harness input, `BacktestEngineConfig` is the engine input, they are independent. Just sprawl.

**Suggested fix:**

> Consider collapsing the strategy-specific fields on `BacktestConfig` into its own `config_overrides` dict when ReplayHarness and BacktestEngine converge (post-P1-E2 M5 — out of scope for fix-now).

**Required steps for this finding:**
1. Re-read the original audit finding in-context (file + line).
2. Run a quick verification (grep, test, or inspection) to confirm
   the observation still holds. Record the verification command and
   output below.
3. If verified AND the "Suggested fix" above is purely observational
   (e.g. "note", "document", "no action"): back-annotate the audit
   report row with `~~description~~ **RESOLVED-VERIFIED FIX-09-backtest-engine**`
   and move on. Make no code change.
4. If verified AND the "Suggested fix" explicitly asks for a DEF
   entry or a small code change (e.g. "Open a new DEF entry",
   "Add a comment", "Remove the stub"): treat this finding as if it
   were tagged `deferred-to-defs` — apply the suggested fix AND add
   a DEF-NNN entry to CLAUDE.md (grep for the highest existing
   DEF-NNN and increment). Back-annotate as
   `**RESOLVED FIX-09-backtest-engine**` (not -VERIFIED, since a change was
   made). Reference the DEF ID in the commit bullet.
5. If the verification *contradicts* the finding (i.e. it is now a
   real bug that requires a larger fix than the suggested_fix
   anticipates): **STOP**, log a note here, and escalate to the
   operator rather than silently applying an invented fix.

### Finding 22: `P1-E1-L06` [LOW]

**File/line:** [data_fetcher.py:1-640](../../../argus/backtest/data_fetcher.py)
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> **`argus/backtest/data_fetcher.py` imports `alpaca.data.*` at the module top.** BacktestEngine does not import `data_fetcher` — it uses HistoricalDataFeed instead. `data_fetcher` is kept alive for the legacy `python -m argus.backtest.data_fetcher --symbols ...` workflow (CLAUDE.md line 118) used when bootstrapping a Parquet cache from Alpaca. Not dead code in the strict sense, but worth flagging in the broader legacy-code conversation (see P1-E2's M5).

**Impact:**

> No runtime impact on production paths. Keeps Alpaca SDK in the dependency tree.

**Suggested fix:**

> Re-assess as part of the larger walk-forward + VectorBT retirement conversation (P1-E2 M5). If `scripts/populate_historical_cache.py` + `HistoricalDataFeed.download()` fully cover the bootstrap case, `data_fetcher.py` is a candidate for deletion.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-09-backtest-engine**`.

### Finding 23: `P1-E2-M02` [MEDIUM]

**File/line:** [argus/backtest/report_generator.py](../../../argus/backtest/report_generator.py) (entire file, 1,232 LOC)
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> **HTML report generator is likely dead.** No production import, no operational script calls it. Latest HTML artifacts in `reports/` are dated 2026-02-17 (pre-Sprint 27 BacktestEngine). Sprint 25.7 replaced session-end HTML with JSON debrief export (DEC-348); Sprint 27+ reporting flows through Command Center UI pages (Arena, Performance, Observatory). The CLI invocation is still documented at [CLAUDE.md:119](../../../CLAUDE.md#L119).

**Impact:**

> Retiring this file removes 1,232 production LOC + 578 test LOC. CLAUDE.md commands section needs 1 line removed.

**Suggested fix:**

> Phase 3: (a) confirm with Steven the HTML report is not part of any manual workflow; (b) delete `argus/backtest/report_generator.py` + `tests/backtest/test_report_generator.py`; (c) remove line 119 from CLAUDE.md commands; (d) optionally `git rm reports/orb_*.html` and add `reports/` to `.gitignore` if they are stale artifacts not worth keeping.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-09-backtest-engine**`.

### Finding 24: `P1-E1-L07` [LOW]

**File/line:** [scanner_simulator.py:225–270](../../../argus/backtest/scanner_simulator.py#L225)
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> **`ScannerSimulator._extract_daily_prices` re-computes `trading_date` from `timestamp`** even though `HistoricalDataFeed.load()` already attaches a `trading_date` column at [historical_data_feed.py:168-170](../../../argus/backtest/historical_data_feed.py#L168-L170). The scanner takes a raw `bar_data` dict and does the tz-localize + tz-convert dance a second time.

**Impact:**

> Mild inefficiency. Not a correctness issue (both computations produce the same ET date).

**Suggested fix:**

> `ScannerSimulator._extract_daily_prices` could accept a pre-computed `trading_date` and skip the re-computation. Or assert that the column exists and use it directly.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-09-backtest-engine**`.

### Finding 25: `P1-E2-M01` [MEDIUM]

**File/line:** [argus/backtest/vectorbt_pattern.py](../../../argus/backtest/vectorbt_pattern.py) (entire file, 1,057 LOC)
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> **PatternBacktester is effectively dead.** No production import, no operational script calls it. Directly superseded by BacktestEngine + ExperimentRunner (Sprint 32 pipeline) for pattern strategies — the only pattern-based validation path that actually runs via operational scripts is BacktestEngine-only through `revalidate_strategy.py` (bull_flag, flat_top_breakout, red_to_green all have `walk_forward: False` in [revalidate_all_strategies.py:57-62](../../../scripts/revalidate_all_strategies.py#L57-L62)). The Sprint 32 S3 "factory delegation" work (DEF-121) retrofitted the file for all 7 patterns but no consumer was ever wired.

**Impact:**

> Retiring this file removes 1,057 production LOC + 852 test LOC (2 files, ~50 tests). `_create_pattern_by_name` helper is a duplicate of the canonical factory in [`argus/strategies/patterns/factory.py::build_pattern_from_config`](../../../argus/strategies/patterns/factory.py).

**Suggested fix:**

> Phase 3: (a) confirm no one uses `python -m argus.backtest.vectorbt_pattern` operationally; (b) update [tests/test_runtime_wiring.py:134,163,276](../../../tests/test_runtime_wiring.py#L134) to call `build_pattern_from_config()` and `_load_pattern_config` replacement via the canonical factory instead; (c) delete `argus/backtest/vectorbt_pattern.py` + `tests/backtest/test_vectorbt_pattern.py`; (d) update [docs/roadmap.md:361,516,675](../../../docs/roadmap.md), project-knowledge.md, and CLAUDE.md MEMORY notes.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-09-backtest-engine**`.

### Finding 26: `P1-E2-M04` [MEDIUM]

**File/line:** [argus/backtest/vectorbt_red_to_green.py](../../../argus/backtest/vectorbt_red_to_green.py) (conditional on M1+M3)
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> **R2G VectorBT becomes deletable if M1 + M3 are adopted.** Today it is TRANSITIVELY LIVE via two thin threads: (a) the dead R2G branch in walk_forward.py (M3), (b) the `load_symbol_data` helper used by vectorbt_pattern.py (M1). Cut both and the file has no remaining consumers.

**Impact:**

> A 2nd-phase cleanup worth ~1,598 LOC once M1 + M3 are complete. Not standalone actionable — must chain.

**Suggested fix:**

> Mark as "Phase 3 follow-on" to M1.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-09-backtest-engine**`.

### Finding 27: `P1-E2-L03` [LOW]

**File/line:** [tests/backtest/test_vectorbt_data_loading.py](../../../tests/backtest/test_vectorbt_data_loading.py) (61 LOC)
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> Small test file that imports `load_symbol_data` from `vectorbt_orb.py`. Retained because vectorbt_orb is live. No immediate action.

**Impact:**

> If M5 + M1 + M3 all land, this test becomes obsolete.

**Suggested fix:**

> Part of the M5 cleanup bundle; not standalone.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-09-backtest-engine**`.

## Post-Session Verification (before commit)

### Full pytest suite

```bash
python -m pytest --ignore=tests/test_main.py -n auto -q 2>&1 | tail -3
# Record new PASS count here: __________
# Net delta: __________ (MUST be >= 0)
```

**Fail condition:** net delta < 0. If this happens:
1. DO NOT commit.
2. `git checkout .` to revert.
3. Re-triage: was the fix wrong, or did it collide with another finding?
4. If fix is correct but a test needed updating, apply test update as a
   SECOND commit after the fix — do not squash into the fix commit.

### Audit report back-annotation

For each resolved finding, update the row in the originating audit
report file (in `docs/audits/audit-2026-04-21/`) from:

```
| ... | description | ... |
```

to:

```
| ... | ~~description~~ **RESOLVED FIX-09-backtest-engine** | ... |
```

For `read-only-no-fix-needed` findings that were verified, use
`**RESOLVED-VERIFIED FIX-09-backtest-engine**` instead.

## Close-Out Report (REQUIRED — follows `workflow/claude/skills/close-out.md`)

Run the close-out skill now to produce the Tier 1 self-review report. Use
the EXACT procedure in `workflow/claude/skills/close-out.md`. Key fields
for this FIX session:

- **Sprint:** `audit-2026-04-21-phase-3`
- **Session:** `FIX-09` (full ID: `FIX-09-backtest-engine`)
- **Date:** today's ISO date

### Session-specific regression checks

Populate the close-out's `### Regression Checks` table with the following
campaign-level checks (all must PASS for a CLEAN self-assessment):

| Check | Result | Notes |
|-------|--------|-------|
| pytest net delta >= 0 against baseline 4,933 passed | | |
| DEF-150 flake remains the only pre-existing failure (no new regressions) | | |
| No file outside this session's declared Scope was modified | | |
| Every resolved finding back-annotated in audit report with `**RESOLVED FIX-09-backtest-engine**` | | |
| Every DEF closure recorded in CLAUDE.md | | |
| Every new DEF/DEC referenced in commit message bullets | | |
| `read-only-no-fix-needed` findings: verification output recorded OR DEF promoted | | |
| `deferred-to-defs` findings: fix applied AND DEF-NNN added to CLAUDE.md | | |

### Output format

Render the close-out inside a fenced markdown code block (triple backticks
with `markdown` language hint) bracketed by `---BEGIN-CLOSE-OUT---` /
`---END-CLOSE-OUT---` markers, followed by the `json:structured-closeout`
JSON appendix. Exact format per the close-out.md skill.

The operator will copy this block into the Work Journal conversation on
Claude.ai. Do NOT summarize or modify the format — the conversation parses
these blocks by structure.

### Self-assessment gate

Per close-out.md:
- **CLEAN:** all findings resolved, no unexpected decisions, all tests pass, all regression checks pass
- **MINOR_DEVIATIONS:** all findings addressed but minor judgment calls needed
- **FLAGGED:** any partial finding, test failures, regression check failures, scope exceeded, architectural concerns

**Proceed to the Commit section below UNLESS self-assessment is FLAGGED.**
If FLAGGED, pause. Surface the flag to the operator with a clear
description. Do not push. Wait for operator direction.

## Commit

```bash
git add <paths>
git commit -m "$(cat <<'COMMIT_EOF'
audit(FIX-09): backtest layer cleanup

Addresses audit findings:
- P1-E1-M01 [MEDIUM]: '_apply_config_overrides' silently mis-routes an unresolvable dot-path to a flat key
- P1-E1-M02 [MEDIUM]: Per-bar dispatch uses 'daily_bars
- P1-E1-M03 [MEDIUM]: BacktestEngine reaches into 'SimulatedBroker
- P1-E1-M04 [MEDIUM]: '_supply_daily_reference_data' accesses 'self
- P1-E1-M05 [MEDIUM]: '_apply_config_overrides' docstring claims support for dot-separated keys but gives only a flat-key example
- P1-E1-L01 [LOW]: Cleanup tracker #1 confirmed — unreachable 'else' branch in fingerprint registration ternary
- P1-E1-L02 [LOW]: '_load_spy_daily_bars' computes 'margin_start' with awkward inline conditional (3-month lookback for SMA-50 warmup)
- P1-E1-L03 [LOW]: '_compute_execution_quality_adjustment' uses hardcoded 'avg_entry_price = 50
- P1-E1-L04 [LOW]: No explicit holiday filtering — trading days are derived from whatever dates appear in the loaded Parquet data ('trading
- P1-E1-C01 [COSMETIC]: '_create_strategy' docstring says "Handles all 7 strategy types" but lists only 7 in the docstring while the actual disp
- P1-E1-C02 [COSMETIC]: Long 'if/elif' chain for 15 StrategyType values with trailing 'else: raise ValueError'
- P1-E1-C03 [COSMETIC]: 'str(self
- P1-E1-C04 [COSMETIC]: Nested 'getattr(getattr(getattr(self
- P1-E2-M03 [MEDIUM]: R2G walk-forward branch is unreachable via operational path
- P1-E2-M05 [MEDIUM]: walk_forward
- P1-E2-C02 [COSMETIC]: Two lazy in-function imports of 'vectorbt_afternoon_momentum'
- P1-G1-M01 [MEDIUM]: Timing-flaky test not tracked in DEF table
- P1-G2-M02 [MEDIUM]: 'test_divergence_documented' literally asserts nothing
- P1-G2-M03 [MEDIUM]: 'test_speed_benchmark' is tautological + flaky
- P1-E1-L05 [LOW]: 'BacktestDataService
- P1-E1-C05 [COSMETIC]: 'BacktestConfig' carries ~20 strategy-specific fields ('vwap_min_pullback_pct', 'consolidation_atr_ratio', 'r2g_min_gap_
- P1-E1-L06 [LOW]: 'argus/backtest/data_fetcher
- P1-E2-M02 [MEDIUM]: HTML report generator is likely dead
- P1-E1-L07 [LOW]: 'ScannerSimulator
- P1-E2-M01 [MEDIUM]: PatternBacktester is effectively dead
- P1-E2-M04 [MEDIUM]: R2G VectorBT becomes deletable if M1 + M3 are adopted
- P1-E2-L03 [LOW]: Small test file that imports 'load_symbol_data' from 'vectorbt_orb

Part of Phase 3 audit remediation. Audit commit: <paste-audit-commit-ref-here>.
Test delta: <baseline> -> <new> (net +N / 0).
COMMIT_EOF
)"
git push origin main
```

## Tier 2 Review (REQUIRED after commit — follows `workflow/claude/skills/review.md`)

After the commit above is pushed, invoke the Tier 2 reviewer in this same
session:

```
@reviewer

Please follow workflow/claude/skills/review.md to review the changes from
this session.

Inputs:
- **Session spec:** the Findings to Fix section of this FIX-NN prompt (FIX-09-backtest-engine)
- **Close-out report:** the ---BEGIN-CLOSE-OUT--- block produced before commit
- **Regression checklist:** the 8 campaign-level checks embedded in the close-out
- **Escalation criteria:** trigger ESCALATE verdict if ANY of:
  - any CRITICAL severity finding
  - pytest net delta < 0
  - scope boundary violation (file outside declared Scope modified)
  - different test failure surfaces (not the expected DEF-150 flake)
  - Rule-4 sensitive file touched without authorization
  - audit-report back-annotation missing or incorrect
  - (FIX-01 only) Step 1G fingerprint checkpoint failed before pipeline edits proceeded

Produce the ---BEGIN-REVIEW--- block with verdict CLEAR / CONCERNS /
ESCALATE, followed by the json:structured-verdict JSON appendix. Do NOT
modify any code.
```

The reviewer produces its report in the format specified by review.md
(fenced markdown block, `---BEGIN-REVIEW---` markers, structured JSON
verdict). The operator copies this block into the Work Journal conversation
alongside the close-out.

## Operator Handoff

After both close-out and review reports are produced, display to the operator:

1. **The close-out markdown block** (for Work Journal paste)
2. **The review markdown block** (for Work Journal paste)
3. **A one-line summary:** `Session FIX-09 complete. Close-out: {verdict}. Review: {verdict}. Commits: {SHAs}. Test delta: {baseline} -> {post} (net {±N}).`

The operator pastes (1) and (2) into the Work Journal Claude.ai
conversation. The summary line is for terminal visibility only.

## Definition of Done

- [ ] Every listed finding has been addressed (resolved, verified, or DEF-logged)
- [ ] Full pytest suite net delta >= 0
- [ ] No new pre-existing-failure regressions (DEF-150 flake is the only expected failure)
- [ ] Close-out report produced per `workflow/claude/skills/close-out.md` (`---BEGIN-CLOSE-OUT---` block + `json:structured-closeout` appendix)
- [ ] Self-assessment CLEAN or MINOR_DEVIATIONS (FLAGGED → pause and escalate before commit)
- [ ] Commit pushed to `main` with the exact message format above (unless FLAGGED)
- [ ] Tier 2 `@reviewer` subagent invoked per `workflow/claude/skills/review.md`; `---BEGIN-REVIEW---` block produced
- [ ] Close-out block + review block displayed to operator for Work Journal paste
- [ ] Audit report rows back-annotated with `**RESOLVED FIX-09-backtest-engine**`

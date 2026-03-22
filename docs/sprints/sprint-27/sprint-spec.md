# Sprint 27: BacktestEngine Core

## Goal
Build a production-code backtesting engine that runs real ARGUS strategy code against Databento OHLCV-1m historical data via synchronous event dispatch, achieving ≥5x speed over the Replay Harness. This is the foundation for all future backtest-driven research (re-validation, parameter sweeps, ensemble search). Backend only — no UI.

## Scope

### Deliverables
1. **SynchronousEventBus** (`argus/core/sync_event_bus.py`) — Sequential-dispatch event bus with the same subscribe/publish interface as the production EventBus but without asyncio task creation, locks, or pending sets. Keeps async method signatures (strategies are async).
2. **BacktestEngineConfig** (additions to `argus/backtest/config.py`) — Pydantic model for engine configuration. New StrategyType enum values for Bull Flag and Flat-Top Breakout.
3. **HistoricalDataFeed** (`argus/backtest/historical_data_feed.py`) — Downloads Databento OHLCV-1m via `timeseries.get_range()`, validates $0.00 cost via `metadata.get_cost()` before every download, caches as Parquet (one file per symbol-month in `data/databento_cache/`), supports incremental updates, converts to ARGUS normalized schema via existing `normalize_databento_df()`.
4. **BacktestEngine** (`argus/backtest/engine.py`) — Core engine that assembles production components (SyncEventBus, BacktestDataService, FixedClock, Strategy, RiskManager, OrderManager, SimulatedBroker), drives bar-by-bar loop per trading day, handles bar-level order fill simulation (no tick synthesis), daily state resets, EOD flatten, scanner simulation for watchlists. Outputs results via existing TradeLogger → SQLite → `compute_metrics()`.
5. **Walk-forward integration** — BacktestEngine as an alternative OOS validation engine in `walk_forward.py`, preserving the existing Replay Harness path.
6. **CLI entry point** — Command-line interface for running BacktestEngine backtests (`python -m argus.backtest.engine`).
7. **~80 new tests** — Unit, integration, and directional equivalence tests. All use mocked data, no live Databento API calls.

### Acceptance Criteria
1. **SynchronousEventBus:**
   - subscribe() registers handlers; publish() dispatches to all handlers sequentially via direct await
   - Monotonic sequence numbers assigned to events (same as production EventBus)
   - Error isolation: one handler exception does not prevent other handlers from executing
   - drain() is a no-op (all handlers complete synchronously within publish)
   - No asyncio.Lock, no asyncio.create_task, no asyncio.sleep(0)
2. **BacktestEngineConfig:**
   - Pydantic model validates all fields with sensible defaults
   - StrategyType enum includes all 7 strategy types (ORB_BREAKOUT, ORB_SCALP, VWAP_RECLAIM, AFTERNOON_MOMENTUM, RED_TO_GREEN, BULL_FLAG, FLAT_TOP_BREAKOUT)
   - Config includes engine_mode, data_source, cache_dir, verify_zero_cost, log_level fields
3. **HistoricalDataFeed:**
   - Downloads OHLCV-1m bars from Databento via `timeseries.get_range(schema="ohlcv-1m", dataset="EQUS.MINI")`
   - Calls `metadata.get_cost()` before every download; raises if cost > $0.00
   - Caches downloaded data as Parquet in `data/databento_cache/{SYMBOL}/{YYYY}-{MM}.parquet`
   - Second request for same symbol/month reads from cache, no API call
   - Incremental update: downloads only months not already cached
   - Produces normalized DataFrame with columns: timestamp (UTC-aware), open, high, low, close, volume
   - Handles empty data (symbol not found, no data in range) gracefully
   - **Fail-closed on cost validation failure (AR-3):** If `metadata.get_cost()` raises an exception (network error, API change), treat as non-zero cost — halt download and log clear message. `verify_zero_cost=False` bypasses all cost checking.
4. **BacktestEngine:**
   - Runs ORB Breakout on mocked 1-month OHLCV data → produces valid BacktestResult with trades
   - Runs all 7 strategy types without error
   - Strategy factory creates correct strategy instance from StrategyType + config YAML
   - PatternBasedStrategy wrapper correctly instantiated with PatternModule for Bull Flag and Flat-Top
   - Single-day bar loop: feeds bars chronologically, interleaves multiple symbols by timestamp, advances FixedClock per bar
   - Bar-level fill model: checks open bracket orders against bar OHLC with priority stop > target > time_stop > EOD
   - Multi-day loop: resets daily state (strategy, risk manager, order manager, data service) per day
   - Scanner simulation generates per-day watchlists from historical data
   - EOD flatten closes all positions at configured time
   - Results computed via existing compute_metrics() from TradeLogger data
   - **Engine metadata recorded (AR-1):** Output database includes metadata recording `engine_type: "backtest_engine"` and `fill_model: "bar_level_worst_case"`. Prevents confusion when comparing results across engine types.
   - **Known limitation documented (AR-2):** Bar-level fill model is least accurate for strategies with risk parameters smaller than the typical 1-minute bar range (e.g., ORB Scalp with 0.3R target). For these strategies, the Replay Harness with tick synthesis provides higher-fidelity results.
   - Speed: ≥5x faster than Replay Harness on equivalent data and strategy
5. **Walk-forward integration:**
   - New `engine` parameter (or equivalent) in walk-forward OOS execution selects BacktestEngine vs Replay Harness
   - Existing Replay Harness OOS path unchanged and still works
   - All existing walk_forward.py CLI modes produce identical output when using Replay Harness path
   - **Engine attribution recorded (AR-4):** `WindowResult` and `WalkForwardResult` include `oos_engine` field ("replay_harness" or "backtest_engine") so WFE results are always attributable to a specific engine. DEC-047 threshold recalibration deferred to Sprint 21.6.
6. **CLI:**
   - `python -m argus.backtest.engine --strategy orb --start 2024-01-01 --end 2024-06-30 --symbols AAPL,TSLA --cache-dir data/databento_cache`
   - Prints summary results to stdout
   - Exit code 0 on success, non-zero on failure

### Performance Benchmarks
| Metric | Target | Measurement Method |
|--------|--------|--------------------|
| Single-strategy, 20-symbol, 6-month run | ≤ 60 seconds | Timed CLI execution on development machine |
| Speed vs Replay Harness (same data) | ≥ 5x faster | Side-by-side benchmark with identical inputs |
| Databento download cost | $0.00 per query | `metadata.get_cost()` assertion before every download |
| Cache hit speed | < 2 seconds for 20 symbols, 6 months | Timed cache-only load (no API calls) |

### Config Changes
New `BacktestEngineConfig` model in `argus/backtest/config.py`:

| YAML/CLI Path | Pydantic Model | Field Name | Default |
|---------------|---------------|------------|---------|
| `--engine-mode` | `BacktestEngineConfig` | `engine_mode` | `"sync"` |
| `--data-source` | `BacktestEngineConfig` | `data_source` | `"databento"` |
| `--cache-dir` | `BacktestEngineConfig` | `cache_dir` | `Path("data/databento_cache")` |
| `--cost-check` / `--no-cost-check` | `BacktestEngineConfig` | `verify_zero_cost` | `True` |
| `--log-level` | `BacktestEngineConfig` | `log_level` | `"WARNING"` |

New StrategyType enum values (additive):

| Value | Enum Name |
|-------|-----------|
| `"bull_flag"` | `BULL_FLAG` |
| `"flat_top_breakout"` | `FLAT_TOP_BREAKOUT` |

No changes to system.yaml or system_live.yaml.

## Dependencies
- Sprint 26 complete (all 7 strategies implemented and tested) — ✅
- Databento Standard plan active with EQUS.MINI access — ✅
- Existing backtest infrastructure: BacktestDataService, SimulatedBroker, FixedClock, compute_metrics(), ScannerSimulator, IndicatorEngine — all unchanged and available
- Strategy configs: `config/strategies/*.yaml` for all 7 strategies

## Relevant Decisions
- DEC-047: Walk-forward validation mandatory, WFE > 0.3 — constrains walk-forward integration design
- DEC-053: Synthetic tick generation — BacktestEngine deliberately skips this for speed; bar-level fill model instead
- DEC-054: Fixed slippage model — reused in BacktestEngine via SimulatedBroker
- DEC-055: BacktestDataService step-driven — reused as-is
- DEC-056: Backtest database naming convention — BacktestEngine follows same convention
- DEC-120: OrbBaseStrategy ABC — shared by ORB Breakout and ORB Scalp
- DEC-132: Pre-Databento backtests provisional — BacktestEngine enables re-validation (Sprint 21.6)
- DEC-248: EQUS.MINI confirmed for data
- DEC-353: Historical data free on Standard plan — enables HistoricalDataFeed
- DEC-354: Phase 6 compression — BacktestEngine pulled forward to Sprint 27

## Relevant Risks
- RSK-022: IBKR Gateway nightly resets — not relevant (backtest mode, no live broker)
- New risk: Databento API rate limits on historical data downloads could slow HistoricalDataFeed. Mitigation: cache aggressively, download incrementally. Low probability — Standard plan allows reasonable historical query volume.

## Session Count Estimate
6 sessions estimated. The engine's component wiring (S3) and fill model (S4) are separated because correctness of the fill model is critical and deserves focused implementation attention. S1 and S2 are parallelizable. No frontend sessions, so no visual-review fix slots needed.

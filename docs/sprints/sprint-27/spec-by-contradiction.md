# Sprint 27: What This Sprint Does NOT Do

## Out of Scope
These items are related to the sprint goal but are explicitly excluded:

1. **Research Console UI (Sprint 31):** No frontend pages, components, or API endpoints for visualizing backtest results. The engine outputs to SQLite and stdout only.
2. **Multiprocessing / parallel sweep infrastructure (Sprint 32):** The engine runs one strategy × one parameter set × one symbol set per invocation. No worker pools, no parallel execution, no result aggregation across runs.
3. **Parameterized strategy templates (Sprint 32):** Strategies are instantiated from their existing YAML configs with optional overrides. No StrategyTemplate abstraction, no declared parameter ranges, no grid generation.
4. **Multi-strategy concurrent backtesting:** Each engine run executes exactly one strategy. Running multiple strategies simultaneously on the same data is out of scope.
5. **In-memory ResultsCollector (DEF-089):** Results flow through TradeLogger → SQLite → compute_metrics(). An in-memory fast path is deferred to Sprint 32 when parallel sweep I/O overhead matters.
6. **DEF-088 PatternParam structured type:** `get_default_params()` continues to return `dict[str, Any]`. Typed parameter metadata deferred to Sprint 32.
7. **Tick synthesis in BacktestEngine:** No synthetic tick generation (DEC-053 pattern). The engine uses bar-level OHLC for fill simulation. This is a deliberate speed/fidelity trade-off.
8. **Live Databento API calls in tests:** All tests use mocked data fixtures. No network calls during test execution.
9. **Quality Engine / NLP pipeline in backtest mode:** These bypass via `BrokerSource.SIMULATED` check. Backtest runs do not score setup quality or fetch catalysts.
10. **Modifications to the Replay Harness:** `replay_harness.py` is unchanged. The BacktestEngine is a parallel path, not a replacement.
11. **Modifications to VectorBT backends:** All `vectorbt_*.py` files are unchanged.

## Edge Cases to Reject
The implementation should NOT handle these cases in this sprint:

1. **Databento API returns non-zero cost for OHLCV-1m:** Raise an error and halt. Do not proceed with download. Log the cost amount for diagnosis.
2. **Strategy requires indicators not provided by IndicatorEngine:** Log a warning and return None from get_indicator(). Strategy handles None per its existing logic. Do not add new indicator types.
3. **Backtest date range extends before March 2023 (Databento EQUS.MINI start):** Raise a clear error with message indicating the earliest available date. Do not silently truncate.
4. **Symbol not found in Databento:** Log warning, skip symbol, continue with remaining symbols. Do not fail the entire run.
5. **BacktestDataService returns None for get_indicator() during early warm-up bars:** This is expected behavior (indicators need N bars of history). Strategy code already handles None. Do not add special warm-up logic in the engine.
6. **Concurrent backtest runs writing to the same cache directory:** Last-write-wins for Parquet cache files. No file locking. This is acceptable for V1 — parallel runs are out of scope.
7. **Strategy config YAML not found:** Raise FileNotFoundError with the expected path. Do not fall back to hardcoded defaults.

## Scope Boundaries
- Do NOT modify: `argus/core/event_bus.py`, `argus/backtest/replay_harness.py`, `argus/backtest/backtest_data_service.py`, `argus/backtest/vectorbt_*.py`, `argus/backtest/tick_synthesizer.py`, any file in `argus/strategies/`, any file in `argus/ui/`, any file in `argus/api/`, any file in `argus/ai/`, any file in `argus/intelligence/`
- Do NOT optimize: BacktestDataService indicator computation (it works, it's tested, performance is acceptable for V1). Do not attempt to make IndicatorEngine faster.
- Do NOT refactor: The existing BacktestConfig model structure. BacktestEngineConfig is a new model alongside it, not a refactor of it.
- Do NOT add: WebSocket endpoints, REST API routes, frontend components, database migrations to argus.db, new config sections in system.yaml or system_live.yaml

## Interaction Boundaries
- This sprint does NOT change the behavior of: production EventBus, production DataService, production startup sequence, any strategy's on_candle() logic, Risk Manager evaluation logic, Order Manager execution logic, SimulatedBroker fill logic
- This sprint does NOT affect: live trading, paper trading, Command Center, AI Copilot, Catalyst Pipeline, Quality Engine, Observatory, any existing test

## Deferred to Future Sprints
| Item | Target Sprint | DEF Reference |
|------|--------------|---------------|
| Research Console UI | Sprint 31 | — |
| Multiprocessing sweep infrastructure | Sprint 32 | — |
| Parameterized strategy templates | Sprint 32 | — |
| In-memory ResultsCollector | Sprint 32 | DEF-089 |
| PatternParam structured type | Sprint 32 | DEF-088 |
| Trade-for-trade equivalence with Replay Harness | Unscheduled | — (different fill models, understood divergence) |
| Cython/Rust hot path for inner loop | Post-revenue | — (only if multiprocessing insufficient) |

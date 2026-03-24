# Sprint 27.6, Session 6: Integration — V2 Compose + Orchestrator + main.py + RegimeHistoryStore

## Pre-Flight Checks
1. Read these files to load context:
   - `argus/core/regime.py` (RegimeVector, RegimeClassifierV2 shell from S1)
   - `argus/core/orchestrator.py` (reclassify_regime, _run_regime_recheck, run_pre_market)
   - `argus/main.py` (startup phases, _run_regime_reclassification task)
   - `argus/core/events.py` (RegimeChangeEvent)
   - `argus/core/config.py` (RegimeIntelligenceConfig, SystemConfig)
   - `argus/core/breadth.py` (BreadthCalculator from S2)
   - `argus/core/market_correlation.py` (MarketCorrelationTracker from S3)
   - `argus/core/sector_rotation.py` (SectorRotationAnalyzer from S4)
   - `argus/core/intraday_character.py` (IntradayCharacterDetector from S5)
2. Scoped test: `python -m pytest tests/core/ -x -q`
3. Verify branch

## Objective
Wire all calculators into RegimeClassifierV2's `compute_regime_vector()`. Integrate V2 with Orchestrator's `reclassify_regime()`. Set up startup in main.py (calculator creation, Event Bus subscriptions, concurrent pre-market). Add RegimeHistoryStore persistence. Enrich RegimeChangeEvent.

## Requirements

1. In `argus/core/regime.py` — complete `RegimeClassifierV2`:
   - `compute_regime_vector(indicators)`: Query each calculator for its snapshot, fill RegimeVector. None calculators → use defaults.
   - `async run_pre_market(fetch_daily_bars_fn, get_top_symbols_fn)`: Run `MarketCorrelationTracker.compute()` and `SectorRotationAnalyzer.fetch()` concurrently via `asyncio.gather()`.
   - `compute_regime_vector()` calls `regime_confidence` using real data from calculators.

2. Create `argus/core/regime_history.py` with class `RegimeHistoryStore`:
   - Constructor: `(db_path: str = "data/regime_history.db")`
   - `async def initialize(self) -> None`: Create table + indexes if not exist. Run 7-day retention cleanup.
   - `async def record(self, regime_vector: RegimeVector) -> None`: Fire-and-forget write. Try/except with rate-limited WARNING (1 per 60s).
   - `async def get_regime_history(self, trading_date: str) -> list[dict]`: All snapshots for date, chronological.
   - `async def get_regime_at_time(self, timestamp: datetime) -> dict | None`: Most recent at or before timestamp.
   - `async def get_regime_summary(self, trading_date: str) -> dict`: Dominant regime, transition count, avg confidence.
   - Schema per sprint spec §12. Separate DB: `data/regime_history.db`.

3. In `argus/core/events.py` — add to `RegimeChangeEvent`:
   - `regime_vector_summary: dict | None = None` (optional, backward compatible)

4. In `argus/core/orchestrator.py`:
   - Accept `regime_classifier_v2: RegimeClassifierV2 | None = None` and `regime_history: RegimeHistoryStore | None = None` in constructor
   - When V2 provided: `reclassify_regime()` calls `v2.compute_regime_vector(indicators)` after V1 classify. Enriches RegimeChangeEvent with `regime_vector_summary=vector.to_dict()`. Writes to history store (fire-and-forget).
   - When V2 is None: existing behavior unchanged.

5. In `argus/main.py`:
   - Config-gate check: if `regime_intelligence.enabled`:
     - Create BreadthCalculator, MarketCorrelationTracker, SectorRotationAnalyzer, IntradayCharacterDetector
     - Create RegimeClassifierV2 with all calculators
     - Create RegimeHistoryStore (if persist_history enabled), initialize it
     - After Databento connected: subscribe BreadthCalculator and IntradayCharacterDetector to CandleEvents via Event Bus
     - During pre-market: call `v2.run_pre_market()` (asyncio.gather for correlation + sector)
     - Pass V2 + history store to Orchestrator
   - If `regime_intelligence.enabled: false`: pass None to Orchestrator → V1 behavior.

## Constraints
- Do NOT modify: `evaluation.py`, `comparison.py`, `ensemble_evaluation.py`, `databento_data_service.py`, `strategies/*.py`
- RegimeChangeEvent `regime_vector_summary` must be Optional (existing consumers unchanged)
- Config-gate must be absolute: enabled=false → zero V2 code executes

## Test Targets
- New tests (~14) in `tests/core/test_regime_integration.py` and `tests/core/test_regime_history.py`:
  - V2 compose: all calculators → full RegimeVector
  - V2 compose: all calculators None → only trend+vol
  - V2 compose: individual dimension disabled → defaults
  - V2 delegates to V1 for primary_regime
  - Config-gate: enabled=false → V1 only
  - Orchestrator reclassify with V2
  - RegimeChangeEvent contains regime_vector_summary
  - Pre-market: run_pre_market executes concurrently (mock asyncio.gather)
  - RegimeHistoryStore: write + query by date
  - RegimeHistoryStore: query by timestamp
  - RegimeHistoryStore: fire-and-forget (mock write failure)
  - RegimeHistoryStore: 7-day retention
  - RegimeHistoryStore: config-gate (persist_history=false → no init)
  - BreadthCalculator + IntradayCharacterDetector Event Bus subscription verified
- Minimum: 14
- Test command: `python -m pytest tests/core/test_regime_integration.py tests/core/test_regime_history.py -x -q -v`

## Definition of Done
- [ ] V2 composition complete (all calculators → RegimeVector)
- [ ] RegimeHistoryStore with write/query/retention
- [ ] Orchestrator integration (V2 when enabled, V1 when disabled)
- [ ] main.py startup wiring with config-gate
- [ ] RegimeChangeEvent enriched
- [ ] Pre-market concurrent fetches
- [ ] 14+ tests passing
- [ ] Close-out: `docs/sprints/sprint-27.6/session-6-closeout.md`
- [ ] Tier 2 review via @reviewer

## Close-Out
After all work is complete, follow the close-out skill in `.claude/skills/close-out.md`.

The close-out report MUST include a structured JSON appendix at the end, fenced with ```json:structured-closeout. See the close-out skill for the full schema.

Write the close-out report to: `docs/sprints/sprint-27.6/session-6-closeout.md`

## Tier 2 Review (Mandatory — @reviewer Subagent)
1. Review context: `docs/sprints/sprint-27.6/review-context.md`
2. Close-out: `docs/sprints/sprint-27.6/session-6-closeout.md`
3. Test command: `python -m pytest tests/core/ -x -q -v`
4. Files NOT to modify: `evaluation.py`, `comparison.py`, `ensemble_evaluation.py`, `databento_data_service.py`, `strategies/*.py`

The @reviewer will produce its review report and write it to:
`docs/sprints/sprint-27.6/session-6-review.md`

## Session-Specific Review Focus
1. Verify config-gate is absolute (enabled=false → zero V2 instances, zero subscriptions, zero FMP calls)
2. Verify V2 delegates to V1 for primary_regime (no reimplementation)
3. Verify RegimeChangeEvent.regime_vector_summary is Optional (backward compat)
4. Verify RegimeHistoryStore fire-and-forget (write failures don't propagate)
5. Verify pre-market uses asyncio.gather (parallel, not sequential)
6. Verify Event Bus subscription for BreadthCalculator uses CandleEvent
7. Verify IntradayCharacterDetector filters for SPY candles only

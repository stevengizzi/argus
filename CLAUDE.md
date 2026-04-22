# ARGUS — Claude Code Context

> Dense, actionable context for Claude Code sessions. No history — see `docs/` for that.
> Last updated: April 21, 2026 (FIX-02 audit 2026-04-21 — overflow.yaml via DEC-384 standalone overlay)

## Active Sprint

**Active sprint: Audit Phase 3 remediation (`audit-2026-04-21`). FIX-00/15/17/20/01/11 landed; FIX-02 just landed; remaining FIX-NN sessions queued. 22 shadow variants still collecting CounterfactualTracker data. Next (production work): Sprint 31B (Research Console / Variant Factory).**

*Follow-on (Apr 21, 2026):* **FIX-01-catalyst-db-quality-pipeline** (audit 2026-04-21 Phase 3) — resolves DEF-082 + DEF-142 + P1-D1-C01/C02/L01 + H2-D01/D02/D03/DEAD05. `argus/main.py:1119` `CatalystStorage` now points at `catalyst.db` (12,114 catalysts) — `catalyst_quality` dimension no longer a constant 50.0. `load_config()` extended (DEC-384 / Option B) to deep-merge registered standalone `config/<name>.yaml` overlays over the system block with precedence standalone > live > base; `_STANDALONE_SYSTEM_OVERLAYS` is the extensible registry. `config/quality_engine.yaml` is now authoritative for weights + thresholds; `system.yaml` / `system_live.yaml` quality blocks untouched. `_score_historical_match()` hardened 50.0 → 0.0 (dormant stub). Scoring-context fingerprint infrastructure (`argus/intelligence/scoring_fingerprint.py`, `CounterfactualStore.scoring_fingerprint` column, `CounterfactualTracker` wiring, `PromotionEvaluator` optional filter) to cleanly separate pre-fix / post-fix shadow data. +11 FIX-01 regression guards (4 fingerprint, 1 catalyst path, 6 load_config merge). DEF-082 + DEF-142 ✅ RESOLVED. DEC-384 added. FIX-02 (overflow.yaml) subsequently landed as the first extension of `_STANDALONE_SYSTEM_OVERLAYS` — see next entry.

*Follow-on (Apr 21, 2026):* **FIX-02-config-drift-critical** (audit 2026-04-21 Phase 3) — resolves P1-D1-C03 (CRITICAL) + H2-D05 (MEDIUM), both the same root cause: `overflow.broker_capacity` divergence (overflow.yaml=50, system_live.yaml=30, runtime=30; Sprint 32.9 S3 intended 50). First extension of the DEC-384 registry: `("overflow", "overflow.yaml")` added to `_STANDALONE_SYSTEM_OVERLAYS` in `argus/core/config.py`. `config/overflow.yaml` flattened to bare-field shape (no `overflow:` wrapper) to match the registry convention established by `quality_engine.yaml`. `config/system.yaml` and `config/system_live.yaml` no longer carry an `overflow:` block — `overflow.yaml` is authoritative. Runtime `config.system.overflow.broker_capacity == 50`, closing the 20-position drift window against `risk_limits.yaml`'s `max_concurrent_positions: 50`. Stage 1 deferred pickup folded in: `load_config()` now emits a WARNING when a registered standalone overlay fails the `isinstance(overlay, dict)` check (previously silent skip). +3 FIX-02 regression guards (registry-contains-overflow, end-to-end merge, non-dict overlay warning); 2 direct-read test call sites updated (`tests/test_overflow_routing.py` method renamed _is_60 → _is_50 + key path; `tests/core/test_signal_cutoff.py` key path). No new DEFs, no new DECs (DEC-384 covers this extension).

*Follow-on (Apr 20, 2026):* **Sprint 31.85** (Parquet Cache Consolidation — impromptu, single session) — resolves DEF-161. `scripts/consolidate_parquet_cache.py` (758 lines, `ProcessPoolExecutor`, atomic `.tmp → rename`, non-bypassable row-count validation, DuckDB `--verify` benchmark harness); `tests/scripts/test_consolidate_parquet_cache.py` (15 new tests including `test_no_bypass_flag_exists` grep-guard and `test_original_cache_is_unmodified` mtime+size+inode snapshot); `docs/operations/parquet-cache-layout.md` (canonical Cache Separation table + operator handoff). Original cache (`data/databento_cache/`, ~983K monthly files) remains the read-only source of truth for `BacktestEngine`; consolidated cache (`data/databento_cache_consolidated/`, ~24K per-symbol files with embedded `symbol` column) is a derived artifact for `HistoricalQueryService`. `HistoricalQueryService`, `HistoricalQueryConfig`, and `config/historical_query.yaml` unmodified — operator repoints `cache_dir` post-consolidation. +15 pytest (4,919 → 4,934). No new DECs. DEF-161 ✅ RESOLVED. DEF-162 opened (monthly re-consolidation cron). DEF-163 opened (date-decay test hygiene batch). Tier 2 verdict: CLEAR.

*Follow-on (Apr 20, 2026):* **Sprint 31.75** (Sweep Infrastructure Hardening) — 4 code sessions, all CLEAR. S1: DEF-152 (GapAndGo min risk guard: `min_risk_per_share=0.10` + ATR-relative floor) + DEF-153 (BacktestEngine `config_fingerprint` wiring through OrderManager registry); +10 pytest. S2: DEF-154 (VWAP Bounce signal density rework: `min_approach_distance_pct`, `min_bounce_follow_through_bars`, `max_signals_per_symbol` cap, `min_prior_trend_bars` 10→15, `lookback_bars` 30→50); +10 pytest. S3a: DuckDB persistent mode (`persist_path` on HistoricalQueryConfig, `--persist-db`/`--rebuild` CLI flags, TABLE materialization in persistent mode); +6 pytest. S3b: `scripts/resolve_sweep_symbols.py`, `scripts/run_sweep_batch.sh`, `config/universe_filters/bull_flag_trend.yaml`, `scripts/analyze_sweeps.py` relocated; +15 pytest. S4 operational: `resolve_symbols_fast.py` (pyarrow-based, 41s for 24K symbols), discovered DuckDB VIEW/TABLE materialization gap (983K Parquet files too slow), pivoted from exhaustive grid sweeps to shadow-first validation. 18 shadow variants added across 8 patterns (22 total). DEF-152/153/154 ✅ RESOLVED. DEF-161 opened (DuckDB Parquet consolidation — resolved Sprint 31.85). DEC-382 (validation pipeline reframe — shadow-first model), DEC-383 (shadow variant fleet — 22 variants deployed).

*Follow-on (Apr 20, 2026):* **Sprint 31.8** — 4 impromptu sessions after 17-day absence (Costa Rica cold-start). S1: HistoricalQueryService init backgrounded (12 min blocking lifespan → `asyncio.to_thread`); `_wait_for_port()` gates health signal on port bind; `start_live.sh` post-startup probe; DEF-155/156 resolved, DEF-157 opened. S2: `evaluation.db` VACUUM (3.7 GB → 209 MB); close→sync VACUUM→reopen pattern; startup reclaim; DEF-157 resolved. S3: 3 independent duplicate-SELL root causes fixed (flatten timeout resubmit, startup cleanup, stop-fill race); DEF-158 resolved, DEF-160 opened. S4: `entry_price_known` column excludes reconstruction trades with 0.0 entry from analytics; DEF-159 resolved. +20 pytest (4,899→4,919). All Tier 2 verdicts CLEAR. No new DECs.

*Follow-on (Apr 3–5, 2026):* **DEF-151 Fix** (`default=str` added to `json.dumps(record.backtest_result)` in `store.py:193`; +1 pytest; commit 3a48bcf). **Sweep Impromptu** — universe-aware small-sample sweeps (24–50 symbols per pattern) across 9 patterns using Sprint 31.5 infra: 2 micro_pullback variants promotable, bull_flag + flat_top dead on tested universe, gap_and_go blocked by DEF-152 (stop-price bug), VWAP Bounce needs parameter rework (DEF-154). DEF-151 ✅ RESOLVED. DEF-152, DEF-153, DEF-154 opened.

Last completed sprint: **31.5 (Parallel Sweep Infrastructure, Apr 3, 2026)** — `ProcessPoolExecutor` parallel execution in ExperimentRunner (`workers` param on `run_sweep()`, module-level `_run_single_backtest()` worker function, in-main-process fingerprint dedup + store writes); `max_workers` on `ExperimentConfig` (default 4); `--workers` CLI flag on `run_experiment.py`; DEF-146 resolved (`universe_filter: UniverseFilterConfig | None` param on `run_sweep()`, `_resolve_universe_symbols()` private method, CLI delegation); 2 new universe filter YAMLs (`config/universe_filters/bull_flag.yaml`, `config/universe_filters/flat_top_breakout.yaml`); all 10 PatternModule patterns now have filter configs; `max_workers: 4` in `config/experiments.yaml`. +34 pytest. No new DECs. Tier 2 verdicts: S1 CONCERNS_RESOLVED, S2 CLEAR, S3 CLEAR.

Previous: **31A.75 (Sweep Tooling Impromptu, Apr 3, 2026)** — `--symbols` (comma-separated or @filepath) and `--universe-filter` (loads `config/universe_filters/{pattern}.yaml`, queries DuckDB via `validate_symbol_coverage()`) added to `scripts/run_experiment.py`. `UniverseFilterConfig` Pydantic model in `argus/intelligence/experiments/config.py` with `min_price`, `max_price`, `min_avg_volume`, `min_market_cap`, `max_market_cap`. Coverage validation gates sweep on Parquet data availability. DEF-145 resolved. +12 pytest (`tests/scripts/test_run_experiment_filters.py`). No new DECs. Tier 2 verdict: CLEAR.

Previous: **31A.5 (Historical Query Layer — DuckDB Phase 1, Apr 3, 2026)** — DuckDB-based read-only analytical query layer over Parquet cache. `HistoricalQueryService` (6 query methods, config-gated, lazy init, in-memory DuckDB, VIEW over Parquet), `HistoricalQueryConfig`, `config/historical_query.yaml`, `scripts/query_cache.py` (interactive CLI), `argus/api/routes/historical.py` (4 JWT-protected endpoints). `validate_symbol_coverage()` for ExperimentRunner pre-filter. +50 pytest. No new DECs. Tier 2 verdict: CLEAR. New dependency: `duckdb>=1.0,<2`.

Previous: **31A (Pattern Expansion III, Apr 3, 2026)** — DEF-143/144 resolved; PMH 0-trade fix (`lookback_bars` 30→400 + `min_detection_bars=10` + reference data wiring in main.py Phase 9.5); 3 new PatternModule strategies: Micro Pullback (10:00–14:00, EMA-based), VWAP Bounce (10:30–15:00, VWAP support), Narrow Range Breakout (10:00–15:00, volatility compression); parameter sweep across all 10 patterns (2 qualifying Dip-and-Rip variants, 8 non-qualifying). DEF-145 opened (universe-aware sweep tooling). +137 pytest. No new DECs.

### Roadmap Amendments Adopted (DEC-357, DEC-358)
Two roadmap amendments adopted March 23, 2026 adding 5 new sprint slots:
- **27.5** (Evaluation Framework): MultiObjectiveResult, EnsembleResult, Pareto dominance, tiered confidence
- **27.6** (Regime Intelligence): RegimeVector replaces MarketRegime enum, multi-dimensional
- **27.7** (Counterfactual Engine): Shadow position tracking for rejected signals, filter accuracy
- **32.5** (Experiment Registry + Promotion Pipeline): Partitioned SQLite registry, cohort-based promotion, simulated-paper screening, overnight experiment queue, kill switches, anti-fragility
- **33.5** (Adversarial Stress Testing): Historical crisis replay + synthetic stress scenarios as PromotionPipeline gate
Amendment docs: `docs/amendments/roadmap-amendment-experiment-infrastructure.md`, `docs/amendments/roadmap-amendment-intelligence-architecture.md`
Build track: ~~21.6~~ ✅ → ~~27.5~~ ✅ → ~~27.6~~ ✅ → ~~27.7~~ ✅ → ~~27.75~~ ✅ → ~~27.8~~ ✅ → ~~27.9~~ ✅ → ~~27.95~~ ✅ → ~~28~~ ✅ → ~~28.5~~ ✅ → ~~28.75~~ ✅ → ~~29~~ ✅ → ~~29.5~~ ✅ → ~~32~~ ✅ → ~~32.5~~ ✅ → ~~32.75~~ ✅ → ~~32.8~~ ✅ → ~~32.9~~ ✅ → ~~31A~~ ✅ → ~~31A.5~~ ✅ → ~~31A.75~~ ✅ → ~~31.5~~ ✅ → ~~31.75~~ ✅ → *(22 shadow variants collecting data)* → 30 → **31B (Research Console / Variant Factory)** → 33 → 33.5 → 34 → 35–41
DEC ranges reserved: 396–402 (33.5)
DEF items: DEF-129 (non-PatternModule variant support), DEF-130 (intraday parameter adaptation)
RSK items: RSK-049 (shadow variant throughput impact), RSK-050 (promotion oscillation)

### Known Issues
- **FMP Starter plan restriction:** FMP news endpoints return 403 on Starter plan ($22/mo). `fmp_news.enabled: false` in `system_live.yaml`. FMP circuit breaker (DEC-323) prevents spam if accidentally enabled.
- **Pre-existing xdist failures (DEF-048):** 4 test_main.py tests fail under `-n auto` (same `load_dotenv`/`AIConfig` race): `test_both_strategies_created`, `test_multi_strategy_health_status`, `test_candle_event_routing_subscribed`, `test_12_phase_startup_creates_orchestrator`. Pre-existing on clean HEAD. Priority: LOW.
- **Test isolation (DEF-049):** `test_orchestrator_uses_strategies_from_registry` fails when run in isolation but passes in full suite. Pre-existing.
- **Date-decay test failures (DEF-163):** 2 pre-existing tests embed hardcoded dates that decay as real time advances — `tests/analytics/test_def159_entry_price_known.py::test_get_todays_pnl_excludes_unrecoverable` (seeds bogus trade via `datetime.now()`, expects `pnl == 100.0`) and `tests/core/test_regime_vector_expansion.py::TestHistoryStoreMigration::test_history_store_migration` (reconfirmed decay despite Sprint 32.8 `now(UTC) - 1 day` fix — likely a second hardcoded constant). Batched fix deferred — same root-cause class as DEF-137. Priority: LOW.
- **Flaky sprint_runner test (DEF-150):** `tests/sprint_runner/test_notifications.py::TestReminderEscalation::test_check_reminder_sends_after_interval` — race condition under `-n auto`, passes in isolation. Reconfirmed pre-existing during Sprint 31.85. Priority: LOW.
- ~~**Startup zombie flatten queue not draining (DEF-139):**~~ RESOLVED Sprint 32.9 S1 — root cause was `getattr(pos, "qty", 0)` returning 0 (Position model uses `shares`). Fixed to `getattr(pos, "shares", 0)` in 4 locations.
- ~~**EOD flatten reports positions closed but broker retains them (DEF-140):**~~ RESOLVED Sprint 32.9 S1 — same `qty`/`shares` mismatch + fire-and-forget order submission. Added synchronous fill verification with asyncio.Event per symbol.

## Current State

- **Active sprint:** Between sprints. 22 shadow variants deployed via experiments.yaml. Parquet consolidation script delivered (Sprint 31.85); operator activation of consolidated cache pending. Next: Sprint 31B (Research Console / Variant Factory).
**Tests:** 4,934 pytest + 846 Vitest. Baseline at Phase 3 audit kickoff (2026-04-21): 4,933 passed, 1 failed. The 1 failure is `tests/sprint_runner/test_notifications.py::TestReminderEscalation::test_check_reminder_sends_after_interval` — intermittent, fails for the first 2 minutes of every hour due to `(minute - 2) % 60` arithmetic (NOT an xdist race, despite DEF-150's original label). Fix is FIX-13 finding P1-G1-M07, scheduled for Phase 3 Stage 8. Treat this one test as pre-existing through Stages 1–7; re-run it in isolation to confirm if post-session tests flag it.
- **Strategies:** 13 live + 2 shadow (15 total): live — ORB Breakout, ORB Scalp, VWAP Reclaim, Afternoon Momentum, Red-to-Green, Bull Flag, Dip-and-Rip, HOD Break, Gap-and-Go, Pre-Market High Break, Micro Pullback, VWAP Bounce, Narrow Range Breakout; shadow — Flat-Top Breakout, ABCD (demoted Sprint 32.9 S3 for optimization)
- **Experiment Variants:** 2 Dip-and-Rip variants in shadow mode (`strat_dip_and_rip__v2_tight_dip_quality`: Sharpe 1.996, WR 45.6%; `strat_dip_and_rip__v3_strict_volume`: Sharpe 2.628, WR 45.0%) — only qualifying variants from 10-pattern sweep (24-symbol momentum set, 2025); 8 non-qualifying patterns need universe-aware re-sweep (Sprint 31.5 infra complete, sweeps pending); `run_experiment.py` now supports `--symbols`/`--universe-filter`/`--workers` flags (Sprint 31A.75 + 31.5); parallel execution via `ProcessPoolExecutor`; `max_workers: 4`; all 10 PatternModule patterns have universe filter configs; configured in `config/experiments.yaml`
- **Infrastructure:** Databento EQUS.MINI (live) + IBKR paper trading (Account U24619949) + FMP Starter (scanning + reference data + daily bars for regime) + Finnhub (news + analyst recs) + Claude API (Copilot + Catalyst Classification) + Universe Manager (config-gated) + Catalyst Pipeline (config-gated) + Intelligence Polling Loop (config-gated) + Reference Data Cache + Quality Engine (config-gated) + Dynamic Position Sizer + Strategy Evaluation Telemetry (ring buffer + SQLite persistence) + Debrief Export (shutdown automation) + Evaluation Framework (MultiObjectiveResult, EnsembleResult, comparison API, slippage model) + Regime Intelligence (RegimeVector 11-field, 8 calculators, config-gated, Sprints 27.6 + 27.9) + VIX Data Service (yfinance daily VIX/SPX, 5 derived metrics, SQLite cache, config-gated, Sprint 27.9) + Counterfactual Engine (shadow position tracking, filter accuracy, shadow strategy mode, overflow routing, config-gated, Sprints 27.7 + 27.95) + Learning Loop V1 (OutcomeCollector, WeightAnalyzer, ThresholdAnalyzer, CorrelationAnalyzer, LearningService, ConfigProposalManager, LearningStore, config-gated, Sprint 28) + Exit Management (trailing stops ATR/percent/fixed, exit escalation, belt-and-suspenders, config-gated per strategy, Sprint 28.5) + ThrottledLogger (log rate-limiting, Sprint 27.75) + Paper trading config overrides (10x risk reduction, throttle disabled, $10 min risk floor, Sprint 27.75) + Broker-confirmed reconciliation (Sprint 27.95) + Overflow routing (config-gated, Sprint 27.95) + EOD flatten synchronous verification (Sprint 32.9) + Margin circuit breaker (IBKR Error 201, Sprint 32.9) + Pre-EOD signal cutoff 3:30 PM ET (config-gated, Sprint 32.9) + Experiment Pipeline (enabled: true, exercised end-to-end with 2 Dip-and-Rip variants configured in shadow, Sprint 32.9) + **NYSE Holiday Calendar** (`core/market_calendar.py`, Apr 3 hotfix) + **OHLCV-1m Observability** (per-gate drop counters + first-event sentinels + zero-candle escalation in DatabentoDataService, Apr 3 hotfix) + **Historical Query Service** (DuckDB read-only analytical layer over Parquet cache, config-gated, 6 query methods, 4 REST endpoints, CLI, Sprint 31A.5) + **Universe-Aware Sweep Flags** (`--symbols`/`--universe-filter` on `scripts/run_experiment.py`, `UniverseFilterConfig`, DuckDB coverage validation, Sprint 31A.75) + **Parallel Sweep Infrastructure** (`ProcessPoolExecutor` parallel execution in ExperimentRunner, `workers` param on `run_sweep()`, `max_workers` config on `ExperimentConfig` (default 4), `--workers` CLI flag, DEF-146 resolved, Sprint 31.5) + **Universe Filter YAMLs (all 10 patterns)** (`config/universe_filters/bull_flag.yaml`, `config/universe_filters/flat_top_breakout.yaml` added; all 10 PatternModule patterns now have filter configs, Sprint 31.5) + **Parquet Cache Consolidation Tooling** (`scripts/consolidate_parquet_cache.py` merges ~983K monthly files into ~24K per-symbol files with embedded `symbol` column, atomic `.tmp → rename` after non-bypassable row-count validation, `--verify`/`--verify-only` DuckDB benchmark harness, 60 GB disk preflight, `--resume`/`--force`/`--symbols`/`--dry-run` ergonomics; original cache remains read-only source of truth for `BacktestEngine`; operator-owned repoint of `config/historical_query.yaml` activates the consolidated cache for `HistoricalQueryService`, Sprint 31.85)
- **Frontend:** 10-page Command Center (Arena page added Sprint 32.75, Experiments page added Sprint 32.5, Shadow Trades tab added to Trade Log) + AI Copilot + Universe Status Card + Intelligence Brief View (all active), Tauri desktop + PWA mobile. Pages: Dashboard, Trade Log, Performance, The Arena, Orchestrator, Pattern Library, The Debrief, System, Observatory, Experiments. Keyboard shortcuts: 1–9 + 0 (0 = Experiments). All 15 strategies have unique colors, badges, single-letter identifiers.

## Project Structure

```
argus/
├── core/           # Orchestrator, Risk Manager, Portfolio, Event Bus, Regime Intelligence (breadth.py, market_correlation.py, sector_rotation.py, intraday_character.py, regime_history.py), TheoreticalFillModel (fill_model.py), Exit Math (exit_math.py), NYSE Holiday Calendar (market_calendar.py)
├── strategies/     # BaseStrategy, OrbBaseStrategy, 15 strategy implementations
│   └── patterns/   # PatternModule ABC, PatternParam, 10 patterns (BullFlag, FlatTop, DipAndRip, HODBreak, GapAndGo, ABCD, PreMarketHighBreak, MicroPullback, VwapBounce, NarrowRangeBreakout)
├── data/           # DataService (Databento/Alpaca/Replay/Backtest), Scanner, IndicatorEngine, UniverseManager, FMPReferenceClient, VIXDataService, HistoricalQueryService (DuckDB)
├── execution/      # Broker (IBKR/Alpaca/Simulated), Order Manager
├── analytics/      # Trade Logger, PerformanceCalculator, DebriefExport, Evaluation Framework
├── backtest/       # VectorBT helpers, Replay Harness, BacktestEngine (Sprint 27)
├── api/            # FastAPI REST + WebSocket, JWT auth
│   ├── routes/     # arena.py (GET /api/v1/arena/positions, GET /api/v1/arena/candles/{symbol}), market.py (GET /api/v1/market/status — no auth), historical.py (GET /api/v1/historical/symbols, /coverage, /bars/{symbol}, POST /validate-coverage)
│   └── websocket/  # ai_chat.py (WS streaming), arena_ws.py (/ws/v1/arena — 6 message types)
├── ui/             # React frontend (Vite + TypeScript + Tailwind v4)
│   └── features/
│       ├── copilot/  # CopilotPanel, ChatMessage, ActionCard
│       └── arena/    # ArenaPage, ArenaCard, ArenaControls, ArenaStatsBar, MiniChart, useArenaWebSocket, useArenaData
├── ai/             # Claude API integration (Sprint 22, active)
│   ├── client.py   # ClaudeClient (API wrapper, rate limiting, tool_use)
│   ├── config.py   # AIConfig (token budgets, TTLs, cost rates)
│   ├── prompts.py  # PromptManager (system prompt, guardrails)
│   ├── context.py  # SystemContextBuilder (per-page context)
│   ├── conversations.py  # ConversationManager (SQLite persistence)
│   ├── usage.py    # UsageTracker (per-call cost tracking)
│   ├── actions.py  # ActionManager (proposal lifecycle, TTL, re-check)
│   ├── executors.py # 5 ActionExecutors + ExecutorRegistry
│   ├── summary.py  # DailySummaryGenerator
│   ├── cache.py    # ResponseCache (TTL-based)
│   └── tools.py    # 5 tool_use definitions with JSON schemas
├── intelligence/   # CatalystPipeline, CatalystClassifier, CatalystStorage, BriefingGenerator, startup factory, polling loop (Sprints 23.5 + 23.6), SetupQualityEngine (quality_engine.py), DynamicPositionSizer (position_sizer.py) (Sprint 24)
│   └── learning/   # Learning Loop V1: OutcomeCollector, WeightAnalyzer, ThresholdAnalyzer, CorrelationAnalyzer, LearningService, ConfigProposalManager, LearningStore (Sprint 28)
├── utils/          # ThrottledLogger (Sprint 27.75)
├── config/         # system.yaml, system_live.yaml, strategies/*.yaml, regime.yaml, counterfactual.yaml, vix_regime.yaml, learning_loop.yaml, exit_management.yaml, historical_query.yaml
├── tests/          # pytest (backend) + Vitest (frontend)
├── docs/           # Decision log, sprint history, strategy specs, research reports
├── workflow/       # Metarepo submodule (protocols, templates, runner, universal rules)
└── .claude/        # rules/ (project-specific + universal→workflow), skills/→workflow, agents/→workflow
    └── rules/      # backtesting.md, trading-strategies.md, universal.md
```

## Commands

```bash
# Tests
python -m pytest --ignore=tests/test_main.py -n auto -q  # Full suite (~4,858 tests, ~114s with xdist)
python -m pytest tests/ -x               # Stop on first failure
python -m pytest tests/ -x -q            # Fail-fast, quiet
cd argus/ui && npx vitest run            # Frontend tests (~846)

# Trading engine
python -m argus.main                      # Start (paper trading default)
python -m argus.main --dry-run           # Connect and validate without trading
python -m argus.main --dev               # Dev mode (mock data, no external connections)
python -m argus.main --config system.yaml # Alpaca incubator mode (legacy)
python -m argus.main --config config/system_live.yaml  # Live mode (Databento + IBKR)

# Backtesting
python -m argus.backtest.data_fetcher --symbols TSLA,NVDA --start 2025-03-01 --end 2026-02-01
python -m argus.backtest.replay_harness --data-dir data/historical/1m --start 2025-06-01 --end 2025-12-31
python -m argus.backtest.vectorbt_orb --data-dir data/historical/1m --symbols TSLA,NVDA --start 2025-06-01 --end 2025-12-31
python -m argus.backtest.engine --symbols TSLA,NVDA --start 2025-06-01 --end 2025-12-31 --strategy orb_breakout
python -m argus.backtest.report_generator --db data/backtest_runs/run_xxx.db --output reports/orb_validation.html

# API & Frontend
python -m argus.api --dev                 # API server with mock data (password: "argus")
python -m argus.api.setup_password        # Generate password hash for production
cd argus/ui && npm install               # Install frontend dependencies
cd argus/ui && npm run dev               # Vite dev server
cd argus/ui && npm run build             # Production build

# Live operations
./scripts/start_live.sh [--with-ui]      # Start ARGUS (4 pre-flight checks, PID management)
./scripts/stop_live.sh                   # Graceful shutdown (SIGINT, 60s timeout, force kill)

# Validation & diagnostics
python scripts/diagnose_databento.py     # Databento EQUS.MINI capabilities
python scripts/test_session8_integration.py  # 13 integration checks
python scripts/test_session9_resilience.py   # 4 resilience checks
python scripts/test_time_stop_eod.py     # Time stop + EOD flatten (IBKR or mock)

# AI Layer
ANTHROPIC_API_KEY="sk-..." python -m argus.api --dev  # Run with AI enabled
python -m pytest tests/ai/ -x -q                       # AI module tests only

# Autonomous Sprint Runner (Sprint 23.2)
python scripts/sprint-runner.py --help                # Show all CLI options
python scripts/sprint-runner.py run path/to/sprint-package.yaml  # Execute sprint
python scripts/sprint-runner.py resume --run-dir path/to/run  # Resume from checkpoint

# Learning Loop (Sprint 28)
python scripts/run_learning_analysis.py               # Manual learning analysis
python scripts/run_learning_analysis.py --window-days 30  # Custom window
python scripts/run_learning_analysis.py --strategy-id orb_breakout  # Single strategy
python scripts/run_learning_analysis.py --dry-run     # Analyze without persisting
```

**Environment Variables:**
- `ANTHROPIC_API_KEY` — Required for AI Copilot. Gracefully disabled if unset.
- `ARGUS_JWT_SECRET` — Required for API authentication.
- `FMP_API_KEY` — Required for pre-market scanning.

## Code Style

- Type hints on ALL function signatures (parameters and return types)
- Docstrings on all public methods and classes (Google style)
- Abstract base classes (ABC) for all pluggable interfaces
- snake_case for files, functions, variables
- PascalCase for classes
- UPPER_SNAKE_CASE for constants
- All imports at top of file, grouped: stdlib → third-party → local
- No wildcard imports
- Max line length: 100 characters
- Use pathlib for file paths, not os.path
- Use dataclasses or Pydantic models for structured data, not raw dicts
- Prefer explicit over implicit — no magic

## Architectural Rules

### Event Bus
- FIFO per subscriber, monotonic sequence numbers (DEC-025)
- Sole streaming mechanism — no callbacks on DataService (DEC-029)
- Type-only subscription; filtering in handlers, not at bus level (DEC-033)

### Strategies
- Daily-stateful, session-stateless (DEC-028)
- Inherit from BaseStrategy (or proven family base like OrbBaseStrategy)
- ALLOW_ALL cross-strategy policy (DEC-121/160)
- Per-signal time stops via SignalEvent.time_stop_seconds (DEC-122)

### Risk & Execution
- Risk Manager: approve-with-modification for share reduction/target tightening only. NEVER modify stops or entry (DEC-027)
- Concentration limit: approve-with-modification, 0.25R floor (DEC-249)
- Atomic bracket orders: entry + stop + T1 + T2 submitted together (DEC-117)
- All stock positions close intraday. Long only for V1.
- NEVER place broker orders without passing through the Risk Manager
- ALL trades MUST be logged to the database with full metadata
- All market-hours time comparisons MUST convert UTC timestamps to ET first using `timestamp.astimezone(ZoneInfo("America/New_York"))`. NEVER compare `.timestamp.time()` directly against ET constants like `time(9, 30)`. (DEC-061)

### Data
- Databento EQUS.MINI primary (DEC-248). Prices fixed-point × 1e9 (DEC-243)
- Databento threading: callbacks on reader thread → `call_soon_threadsafe()` (DEC-088)
- Historical data has ~15min intraday lag (DEC-244), multi-day daily bar lag (DEC-247)
- IndicatorEngine shared by all DataService implementations (DEC-092)
- Universe Manager: config-gated (`universe_manager.enabled`), fail-closed on missing reference data (DEC-277)
- Fast-path discard in DatabentoDataService drops non-viable symbols before IndicatorEngine (Sprint 23)
- Strategy universe filters are declarative YAML only — never modify strategy Python code for filter changes

### Frontend
- React + TypeScript, TanStack Query, Zustand, Framer Motion
- Chart libraries: Lightweight Charts (financial), Recharts (analytics), D3 (custom viz) (DEC-104/215)
- Design north star: "Bloomberg Terminal meets modern fintech" (DEC-109)
- Responsive: <640px phone, 640–1023px tablet, ≥1024px desktop (DEC-105)
- Animation budget: <500ms, 60fps, never blocks interaction (DEC-110)
- No conditional skeleton/content swaps — always render same DOM structure (Sprint 17.5 lesson)

### Config & DB
- YAML → Pydantic BaseModel (not BaseSettings) (DEC-032)
- aiosqlite for async DB; TradeLogger is sole persistence interface (DEC-034)
- Trade IDs: ULIDs via python-ulid (DEC-026)
- Separate configs: system.yaml (Alpaca incubator), system_live.yaml (Databento + IBKR) (DEC-231)
- NEVER hardcode configuration values — always read from YAML config files
- Broker API keys and secrets NEVER in code or committed files — environment variables only
- FMP_API_KEY required for pre-market scanning (Sprint 21.7, DEC-258)

### Backtesting
- VectorBT: precompute+vectorize architecture MANDATORY (DEC-149)
- BacktestEngine (Sprint 27): production-code backtesting via SynchronousEventBus, bar-level fill model, Databento OHLCV-1m + Parquet cache; `to_multi_objective_result()` produces regime-tagged `MultiObjectiveResult` (Sprint 27.5); optional `slippage_model_path` on `BacktestEngineConfig` loads calibrated slippage model
- Walk-forward validation: WFE > 0.3 required (DEC-047); `oos_engine` parameter selects BacktestEngine vs Replay Harness
- Pre-Databento backtests are PROVISIONAL (DEC-132). PARTIALLY RESOLVED (Sprint 21.6) — pipeline proven end-to-end, Bull Flag validated, 6 strategies pending full-universe re-validation
- See `.claude/rules/backtesting.md` for detailed sweep rules

### API
- FastAPI in-process (Phase 12 startup) (DEC-099)
- Single-user JWT with bcrypt (DEC-102)
- WebSocket: curated event list, tick throttling (DEC-101)
- AppState dataclass → FastAPI Depends() injection (DEC-100)

## UI/UX Rules

- **Design principles (DEC-109):** Information over decoration. Ambient awareness. Progressive disclosure. Motion with purpose. Mobile as primary trading surface. Research lab aesthetics.
- **Animation library (DEC-110):** Framer Motion for page transitions + stagger. CSS transitions for hover/micro-interactions. Lightweight Charts native for chart animations. Budget: <500ms, 60fps, never blocks interaction.
- **Chart library stack (DEC-104, DEC-108):** Lightweight Charts (time-series) + Recharts (standard charts) + D3 (custom viz, sparingly) + Three.js r128 (Observatory Funnel/Radar 3D views, code-split via React.lazy).
- **UX Feature Backlog:** `docs/ui/ux-feature-backlog.md` — canonical inventory of all planned UI/UX enhancements. Reference when planning sprint UX scope. (DEC-106)
- **Responsive breakpoints:** 393px (iPhone SE/mini), 834px (iPad portrait), 1194px (iPad landscape), 1512px (MacBook Pro).
- **Mobile nav:** Bottom tab bar. Desktop/tablet: icon sidebar.
- **Frontend testing (DEC-130):** Vitest for React component tests. Config: `vitest.config.ts`. Pattern: `ComponentName.test.tsx` alongside component. Setup: `src/test/setup.ts`.
- **Positions UI state (DEC-129):** Display mode (table/timeline) and filter (all/open/closed) managed in Zustand store (`stores/positionsUI.ts`). Session-level — no localStorage.

## Testing

- pytest with pytest-asyncio for async tests
- Each module has a corresponding test file: `argus/core/risk_manager.py` → `tests/core/test_risk_manager.py`
- Test naming: `test_<what_it_does>_<expected_result>` (e.g., `test_signal_exceeding_daily_loss_is_rejected`)
- Mock external services (broker API, data feeds) in unit tests
- Integration tests use SimulatedBroker and ReplayDataService
- Aim for >90% coverage on core/ and strategies/

## Documentation Sync

Doc updates are handled by the doc-sync skill. See `.claude/skills/doc-sync.md` for the protocol.

## Deferred Items

Track items that are intentionally postponed. Each item has a trigger condition. When that condition is met during a session, surface the item proactively.

| ID | Item | Trigger | Context |
|----|------|---------|---------|
| ~~DEF-001~~ | ~~Inject clock/date provider into Risk Manager~~ | ~~Sprint 4 starts~~ | **DONE** Clock injection into Risk Manager + BaseStrategy is complete. |
| ~~DEF-002~~ | ~~Cash reserve basis: switch to start-of-day equity~~ | ~~Sprint 3~~ | **DONE** — Implemented in Sprint 3 (DEC-037). |
| ~~DEF-003~~ | ~~Replace datetime.utcnow() with datetime.now(UTC)~~ | ~~Sprint 3~~ | **DONE** — Fixed in events.py, trading.py, and tests. |
| ~~DEF-004~~ | ~~Discuss cash reserve calc with CPA before live trading~~ | ~~Phase 3 start~~ | **SUPERSEDED** (DEC-380): CPA consultation removed from all gates. Tax intelligence built into ARGUS as post-revenue automation. Cash reserve calculation addressed by Risk Manager existing logic. |
| ~~DEF-005~~ | ~~Move webhook URLs to .env (security)~~ | ~~Post paper trading validation~~ | **DONE** — HealthConfig now reads heartbeat_url_env and alert_webhook_url_env from config, resolves actual URLs from environment variables. |
| DEF-006 | Backtrader integration if Replay Harness too slow | Phase 2 Sprint 7 (if replay takes >1hr for 6mo data) | Backtrader dropped from Phase 2 (DEC-046). Reconsidered only if Replay Harness performance is insufficient for iterative parameter work. |
| DEF-007 | Pre-market data for scanner accuracy | Backtest results promising AND scanner accuracy becomes bottleneck for live-vs-backtest correlation | IEX feed (free tier) only provides regular hours. Scanner simulation computes gap from prev close → day open, which captures overnight moves but misses pre-market volume patterns. Resolution: download 1 month SIP data to validate scanner accuracy, consider SIP for all historical data if significant. |
| ~~DEF-008~~ | ~~Synthetic data e2e trade trigger test~~ | ~~Sprint 8~~ | **RESOLVED** — Root cause: timezone bug in OrbBreakout (DEC-061). After fix, harness produces 59 trades on 7 months of real data with relaxed max_range_atr_ratio. Additional fixes: fill price ($0.01 bug), trade logging (sync fill handling), data integrity (original stop, weighted exit price). 488 tests. |
| ~~DEF-009~~ | ~~VectorBT vs Replay Harness cross-validation~~ | ~~Sprint 9 starts~~ | **DONE** — `cross_validate_single_symbol()` implemented in walk_forward.py. Compares VectorBT trade count vs Replay Harness for matching params; VectorBT >= Replay is PASS (DEC-069). |
| ~~DEF-010~~ | ~~Remove `_simulate_trades_for_day_slow()`~~ | ~~Sprint 9 completes~~ | **DONE** — Legacy function removed from vectorbt_orb.py. Tests updated to use wrapper over vectorized functions (DEC-070). |
| DEF-011 | IQFeedDataService adapter | Forex strategy development starts OR breadth indicator integration starts | IQFeed provides forex and breadth indicators (advance/decline, TICK, TRIN) that neither Databento nor FMP provide. Benzinga news originally a draw but FMP covers news needs more cost-effectively (DEC-258/260). Build when a specific feature requires forex or breadth data. ~$160–250/month. |
| DEF-012 | Databento L2 depth activation | A strategy requires order book depth data for entry/exit decisions | MBP-10 schema available on Standard plan. DatabentoDataService designed for L2 from Sprint 12, but not activated until a strategy needs it. |
| ~~DEF-013~~ | ~~Extract shared IndicatorEngine from DataService implementations~~ | ~~Sprint 12.5~~ | **DONE** — `IndicatorEngine` class created in `argus/data/indicator_engine.py`. All four DataService implementations (AlpacaDataService, DatabentoDataService, ReplayDataService, BacktestDataService) now delegate to IndicatorEngine. 27 new tests, 685 total tests passing. DEC-092. |
| DEF-014 | SystemAlertEvent for dead data feed | Command Center MVP (Sprint 14–16) OR Health Monitor alerting built | `DatabentoDataService._run_with_reconnection()` logs `critical` when max retries exceeded but emits no Event Bus event. Add `SystemAlertEvent` (or similar) so Health Monitor and Command Center can react (red banner, push notification). Location: `argus/data/databento_data_service.py`. |
| ~~DEF-015~~ | ~~DatabentoScanner full-universe scanning~~ | — | **SUPERSEDED by DEC-263:** Full-universe strategy-specific monitoring architecture adopted. Sprint 23 implements Universe Manager with broad Databento subscription (3,000–5,000 symbols), full IndicatorEngine on all symbols, strategy-declared universe filters. |
| ~~DEF-016~~ | ~~Order Manager `place_bracket_order()` integration~~ | ~~Sprint 17~~ | **DONE** (Sprint 17, DEC-117). Order Manager uses `place_bracket_order()` for atomic entry+stop+T1+T2. ManagedPosition tracks bracket component IDs. SimulatedBroker + IBKRBroker validated. Known limitation: AlpacaBroker bracket child order fills don't route correctly — acceptable, Alpaca is incubator-only (DEC-086). |
| DEF-017 | Performance-weighted + correlation-adjusted allocation | 20+ days of multi-strategy live data available | V1 uses equal-weight. V2 shifts ±10% based on trailing Sharpe/drawdown. V3 adds CorrelationTracker cross-correlation penalty. CorrelationTracker infrastructure built in Sprint 17 (DEC-116). |
| ~~DEF-018~~ | ~~Real VIX data integration~~ | — | **PARTIALLY RESOLVED** (Sprint 27.9): VIXDataService ingests daily VIX/SPX from yfinance, 4 VIX calculators wired into RegimeClassifierV2. Provides daily VIX context (not real-time intraday). Real-time VIX requires IQFeed or CBOE Databento — deferred until a strategy needs intraday VIX granularity. |
| DEF-019 | Breadth indicator integration (advance/decline, TICK, TRIN) | IQFeed subscription activated | RegimeClassifier designed for breadth inputs but V1 uses SPY-only signals. IQFeed provides NYSE breadth data. ~$160–250/month. |
| DEF-020 | Cross-strategy sector exposure check (max_single_sector_pct) | IQFeed subscription activated OR fundamentals data source integrated | Risk Manager cross-strategy checks skip sector exposure in V1 — no sector classification data available (DEC-126). Requires SIC/GICS mapping per symbol. Single-stock cap (5%) provides concentration protection meanwhile. |
| DEF-021 | Sub-bar backtesting precision for ORB Scalp | Databento tick-level data available for backtesting OR Scalp paper trading results diverge significantly from backtests | Synthetic ticks give ~15s granularity per 1m bar (DEC-053). Scalp targets 30–120s holds — time stops shorter than 60s resolve at nearest bar boundary. Backtesting results are directional guidance, not exact P&L. |
| DEF-022 | VwapBaseStrategy ABC extraction | Second VWAP-based strategy designed (e.g., VWAP Fade) | No shared logic exists yet — VwapReclaimStrategy inherits directly from BaseStrategy (DEC-136). If a second VWAP variant is built, extract shared VWAP crossover tracking into a VwapBaseStrategy ABC. Follows the OrbBaseStrategy extraction pattern (DEC-120). |
| ~~DEF-023~~ | ~~Watchlist Endpoint Production Implementation~~ | — | **PARTIALLY RESOLVED** (Sprint 21.7): Watchlist endpoint now reads from `cached_watchlist` (scan_source, selection_reason populated). Remaining: current_price, sparkline, strategy state aggregation. |
| ~~DEF-024~~ | ~~Trailing Stop Mechanism~~ | — | **RESOLVED** (Sprint 28.5): Configurable per-strategy trailing stops (ATR/percent/fixed), partial profit-taking with trail on T1 remainder, time-based exit escalation. Implemented in Order Manager, BacktestEngine, and CounterfactualTracker. `config/exit_management.yaml` with per-strategy overrides. |
| DEF-025 | Shared Consolidation Base Class | Second consolidation-based strategy designed (e.g., Midday Range Breakout) | AfternoonMomentumStrategy inherits directly from BaseStrategy (DEC-152). If a second consolidation variant is built, extract shared midday range tracking into a ConsolidationBaseStrategy ABC. Follows the OrbBaseStrategy extraction pattern (DEC-120). |
| ~~DEF-026~~ | ~~FTS5 full-text search~~ | — | **RESOLVED** (DEC-200): LIKE queries shipped as V1 solution. FTS5 deferred to >10K entries. |
| ~~DEF-027~~ | ~~Journal trade linking UI~~ | — | **RESOLVED** (DEC-201): Full search UI with TradeSearchInput shipped in Sprint 21c. |
| DEF-028 | CalendarPnlView strategy filter | Performance Workbench implementation (DEC-229) OR user requests during paper trading | CalendarPnlView renders all-strategy aggregated P&L. Strategy-specific calendar filtering deferred because calendar needs a different data query path than other charts (daily aggregation by strategy). Low priority — user can already filter by strategy in Overview and Heatmaps tabs. |
| ~~DEF-029~~ | ~~Persist Live Candle Data to Database for Post-Session Replay~~ | — | **OBSOLETE** (audit 2026-04-21 P1-H4): Superseded by IntradayCandleStore (DEC-368, Sprint 27.65) + Arena candle endpoint (Sprint 32.75) + pre-market widening to 4:00 AM ET (Sprint 32.8). The "Bar data not available for this trade" symptom no longer applies — bars accessible via `/api/v1/arena/candles/{symbol}` and `IntradayCandleStore.get_bars()`. |
| ~~DEF-030~~ | ~~Live candlestick chart real-time updates~~ | — | **OBSOLETE** (audit 2026-04-21 P1-H4): Arena WebSocket `arena_candle` message type (Sprint 32.75) provides real-time candle push. If TradeChart-specific replay still lacks WS, that's a narrower DEF worth filing separately. |
| DEF-031 | Orders table persistence | When post-hoc order forensics needed beyond log analysis | Orders not persisted to DB, only completed trades. |
| DEF-032 | FMPScannerSource criteria_list filtering | Sprint 23.5 (NLP Catalyst) or Sprint 24 (Quality Engine) | `scan()` accepts `criteria_list` parameter but ignores it (documented in docstring). FMP endpoints are pre-filtered server-side; post-fetch filtering by strategy-specific criteria becomes meaningful when Quality Engine provides scoring criteria. |
| DEF-033 | Approve→Executed status transition is simulated with setTimeout(1500ms) in ChatMessage.tsx. Real execution status should be pushed via WebSocket (`{"type": "proposal_update", ...}`) after ActionExecutor completes. Requires: WS protocol extension (new message type), executor pipeline event emission, frontend WS handler update. Cosmetic-only impact — proposal is correctly marked `approved` in DB; only the UI status badge is faked. (NEEDS-INFO per audit P1-H4 — see docs/audits/audit-2026-04-21/p1-h4-def-triage.md) | Next UI polish pass or Sprint 23 if room. |
| ~~DEF-034~~ | ~~Pydantic serialization warnings on `review_verdict` field~~ | ~~Next sprint runner polish pass~~ | **RESOLVED** (audit 2026-04-21 FIX-20-sprint-runner): `model_config = ConfigDict(validate_assignment=True)` added to `SessionResult` in `workflow/runner/sprint_runner/state.py`. Raw-string assignments to `review_verdict` (from parsed review verdict payloads) are now coerced to `ReviewVerdict` enum on assignment, eliminating the `PydanticSerializationUnexpectedValue` warning at `model_dump_json()` time. +2 regression tests in `tests/sprint_runner/test_state.py::TestSessionResult`. |
| DEF-035 | FMP Premium Upgrade ($59/mo) | When batch-quote speed becomes a bottleneck | FMP Premium enables batch-quote endpoints (27 min → ~2 min load). Sprint 23.5 completed without upgrade — Finnhub free tier covers news needs. Priority: LOW. |
| ~~DEF-036~~ | ~~Stock-List Response Caching~~ | — | **RESOLVED** (Sprint 23.6): Reference data file cache with JSON persistence, per-symbol staleness, and incremental warm-up implemented (DEC-314). Reduces ~27 min to ~2–5 min. |
| DEF-037 | FMP API Key Redaction in Error Logs | Next cleanup sprint | FMP API URLs with API key appear in error logs. Should redact `apikey=XXX` before logging. Priority: MEDIUM. |
| DEF-038 | Fuzzy/Embedding-Based Catalyst Dedup | Sprint 28+ or when duplicate catalyst volume is high | Current semantic dedup uses (symbol, category, time_window) grouping (DEC-311). Embedding-based similarity matching would catch semantic duplicates with different headlines. Requires embedding model integration. Priority: LOW — rule-based dedup handles the common case. |
| DEF-039 | Runner Conformance Check Reliability Audit | When conformance_fallback_count consistently >2 per sprint run | Sprint 23.6 added conformance fallback tracking. If fallback counter shows frequent failures, investigate structured output parsing reliability and tighten the conformance check. Priority: LOW — monitoring only. |
| DEF-040 | Runner main.py Further Decomposition | Runner exceeds ~2,500 lines | Sprint 23.6 S5 extracted CLI helpers (~120 lines). main.py still 2,067 lines. Further extraction candidates: session execution loop, parallel session handling, notification logic. Priority: LOW. (NEEDS-INFO per audit P1-H4 — see docs/audits/audit-2026-04-21/p1-h4-def-triage.md) |
| ~~DEF-041~~ | ~~Frontend catalyst endpoint short-circuit~~ | ~~Sprint 23.9~~ | **CLOSED** (Sprint 23.9, DEC-329). `usePipelineStatus` hook gates catalyst/briefing TanStack queries on health endpoint pipeline component. Zero requests when pipeline inactive. |
| ~~DEF-043~~ | ~~/debrief/briefings endpoint 503 fix~~ | ~~Sprint 23.9~~ | **CLOSED** (Sprint 23.9). Root cause: `DebriefService` only initialized in `dev_state.py`, never in `server.py` lifespan. Fix: ~10 lines wiring `DebriefService(db)` in lifespan. Frontend empty state already existed. |
| ~~DEF-044~~ | ~~SPY intra-day regime re-evaluation~~ | — | **PARTIALLY RESOLVED** (Sprint 25.6, DEC-346): Periodic 300s regime reclassification task added. Regime now reclassified during market hours. Remaining: regime-aware strategy behavior (how should mid-session regime changes affect running strategies). |
| ~~DEF-045~~ | ~~SEC Edgar timeout test rewrite~~ | ~~Sprint 23.9~~ | **CLOSED** (Sprint 23.9). Rewrote to call `client.start()` with mocked CIK refresh, inspects `client._session.timeout`. Matches Finnhub/FMP pattern. |
| ~~DEF-046~~ | ~~test_main.py xdist failures (2 named tests)~~ | ~~Sprint 23.9~~ | **CLOSED** (Sprint 23.9). Root cause: `load_dotenv()` in `ArgusSystem.__init__()` re-loaded `.env` after monkeypatch, `AIConfig.auto_detect_enabled` overrode `enabled=False`. Fix: empty `ANTHROPIC_API_KEY` env var + explicit `ai: enabled: false`. 4 additional failures tracked as DEF-048. |
| DEF-047 | Bulk catalyst endpoint | Unscheduled | Consolidate per-symbol catalyst GET requests into single batch request. Currently one request per watchlist symbol when pipeline is active. Priority: LOW. |
| DEF-048 | Additional test_main.py xdist failures | Unscheduled | 4 more tests fail under `-n auto` (same `load_dotenv`/`AIConfig` race as DEF-046): `test_both_strategies_created`, `test_multi_strategy_health_status`, `test_candle_event_routing_subscribed`, `test_12_phase_startup_creates_orchestrator`. Pre-existing on clean HEAD. Same fix approach as DEF-046. Priority: LOW. |
| DEF-049 | test_orchestrator_uses_strategies_from_registry isolation failure | Unscheduled | `test_orchestrator_uses_strategies_from_registry` in tests/test_main.py fails when run in isolation but passes in full suite. Pre-existing test isolation issue. Discovered Sprint 24 S1. Priority: LOW. |
| ~~DEF-074~~ | ~~Dual regime recheck path consolidation~~ | — | **RESOLVED** (FIX-03, audit 2026-04-21): `main.py._run_regime_reclassification` method + `_regime_task` attribute + create_task call + shutdown-sweep entry all deleted. `Orchestrator._poll_loop` is sole regime-cadence owner. Two orphan tests in `tests/core/test_orchestrator.py` deleted; `tests/test_shutdown_tasks.py` fixture updated. |
| ~~DEF-050~~ | ~~Full ArgusSystem e2e integration test~~ | ~~Unscheduled~~ | **RESOLVED** (Sprint 24.1 S2): Full strategy → quality engine → sizer → RM integration test implemented. |
| ~~DEF-052~~ | ~~Dashboard quality cards interactivity~~ | ~~Unscheduled~~ | **RESOLVED** (Sprint 24.1 S4b + S4f): Tooltips, legend, and chart redesign completed. QualityDistributionCard donut removed (redundant with SignalQualityPanel histogram). |
| ~~DEF-053~~ | ~~Quality column in Dashboard tables~~ | ~~Unscheduled~~ | **RESOLVED** (Sprint 24.1 S4b): Quality column added to Dashboard Positions/Recent Trades tables. |
| ~~DEF-054~~ | ~~Orchestrator clickable signal rows~~ | ~~Unscheduled~~ | **RESOLVED** (Sprint 24.1 S4b): Clickable signal rows with SignalDetailPanel implemented. |
| ~~DEF-055~~ | ~~Orchestrator 3-column layout~~ | ~~Unscheduled~~ | **RESOLVED** (Sprint 24.1 S4a): Decision Log + Catalyst Alerts + Recent Signals combined into 3-column row. |
| ~~DEF-056~~ | ~~QualityOutcomeScatter page placement~~ | ~~Unscheduled~~ | **RESOLVED** (Sprint 24.1 S4a): Relocated from Debrief Quality tab to Performance Distribution tab. |
| ~~DEF-057~~ | ~~SEC EDGAR EFTS URL live validation~~ | ~~Unscheduled~~ | **RESOLVED** (Sprint 24.1 S2): URL works with User-Agent header. No code change needed. |
| ~~DEF-058~~ | ~~Trades DB quality columns~~ | ~~Unscheduled~~ | **RESOLVED** (Sprint 24.1 S1a): Quality grade/score wired through Order Manager → TradeLogger → DB schema. |
| ~~DEF-059~~ | ~~Pre-existing TypeScript build errors (22)~~ | ~~Unscheduled~~ | **RESOLVED** (Sprint 24.1 S3): All 22 TS build errors fixed. TS errors: 22 → 0. |
| ~~DEF-060~~ | ~~PROVISIONAL comment gap in system YAML quality sections~~ | ~~Unscheduled~~ | **RESOLVED** (Sprint 24.1 S1b): PROVISIONAL comments added to system.yaml/system_live.yaml quality sections. |
| ~~DEF-061~~ | ~~Quality API private attribute access~~ | ~~Unscheduled~~ | **RESOLVED** (Sprint 24.1 S1b): `@property` accessors added for `_db`/`_config` on SetupQualityEngine. |
| ~~DEF-062~~ | ~~QA seed script cleanup~~ | ~~Unscheduled~~ | **RESOLVED** (Sprint 24.1 S1b): Production guard added to `scripts/seed_quality_data.py`. |
| ~~DEF-063~~ | ~~Trust cache on startup (reference data)~~ | ~~Sprint 25.9~~ | **RESOLVED** (Sprint 25.9 S2, DEC-362): `trust_cache_on_startup: true` loads cached reference data immediately at startup, background asyncio task refreshes stale entries. |
| DEF-064 | Warm-up 78% failure rate on mid-session boot | Unscheduled | Databento historical API returns 422 for many symbols during lazy warm-up. 69–78% failure rate observed. Only affects mid-session boot (pre-market boot skips warm-up, DEC-316). Priority: LOW while pre-market boot is the normal path. |
| ~~DEF-075~~ | ~~`fetch_daily_bars()` via FMP for regime classification~~ | ~~Sprint 25.7~~ | **RESOLVED** (Sprint 25.7 S1): Implemented via FMP stable historical-price-eod endpoint. |
| ~~DEF-076~~ | ~~Health endpoint `last_data_received` always null~~ | ~~Sprint 25.7~~ | **RESOLVED** (Sprint 25.7 S1): `last_update` attribute added to DatabentoDataService, set in `_dispatch_record()`. |
| ~~DEF-077~~ | ~~Diagnostic logging when position sizer returns 0 shares~~ | ~~Sprint 25.7~~ | **RESOLVED** (Sprint 25.7 S1): Log now includes grade, score, allocated_capital, buying_power, entry, stop, risk_per_share. |
| ~~DEF-078~~ | ~~Rate-limit regime reclassification warnings~~ | ~~Sprint 25.7~~ | **RESOLVED** (Sprint 25.7 S1): Counter-based rate limiting — logs on 1st occurrence and every 6th. Resets on success. |
| ~~DEF-079~~ | ~~Automated debrief data export at shutdown~~ | ~~Sprint 25.7~~ | **RESOLVED** (Sprint 25.7 S1): `debrief_export.py` produces `logs/debrief_YYYYMMDD.json` during shutdown. |
| ~~DEF-080~~ | ~~VWAP Reclaim false suspension on zero trade history~~ | ~~Sprint 25.7~~ | **RESOLVED** (Sprint 25.7 S1): Early return `ThrottleAction.NONE` when both trades and daily_pnl are empty. |
| ~~DEF-081~~ | ~~Entry evaluation conditions_passed/conditions_total metadata~~ | ~~Sprint 25.7~~ | **RESOLVED** (Sprint 25.7 S1): Added to all ENTRY_EVALUATION calls in `_check_breakout_conditions()`. |
| ~~DEF-082~~ | ~~Quality engine `catalyst_quality` always 50.0 — root cause is CatalystStorage pointing at `argus.db` (empty) instead of `catalyst.db` (12,114 catalysts) per audit P1-D1 C1~~ | — | **RESOLVED** (audit 2026-04-21 FIX-01-catalyst-db-quality-pipeline). `argus/main.py:1119` now constructs `CatalystStorage` against `catalyst.db`. Regression guard: `tests/test_fix01_catalyst_db_path.py`. |
| ~~DEF-083~~ | ~~API auth 403→401~~ | ~~Sprint 25.8~~ | **RESOLVED** (Sprint 25.8, DEC-351): `HTTPBearer(auto_error=False)` + explicit 401. 35 tests fixed. |
| DEF-084 | Full test suite runtime optimization | Partially resolved | FMP rate limit configurable (454s→39s with xdist). Remaining slow tests: `test_stale_data_detection/recovery` (10s each). `slow` marker registered in pyproject.toml. Priority: LOW. |
| ~~DEF-088~~ | ~~PatternParam structured type for `get_default_params()`~~ | ~~Sprint 29 (DEC-378)~~ | **RESOLVED** (Sprint 29 S1–S2): `PatternParam` frozen dataclass with 8 fields (name, param_type, default, min_value, max_value, step, description, category). `get_default_params()` returns `list[PatternParam]`. All 7 PatternModule patterns retrofitted. PatternBacktester grid generation uses PatternParam ranges. |
| ~~DEF-089~~ | ~~In-memory ResultsCollector for parallel sweeps~~ | — | **OBSOLETE** (audit 2026-04-21 P1-H4): Sprint 31.5 `ProcessPoolExecutor` approach removed the contention this DEF was designed to solve. Main-process fingerprint dedup + ExperimentStore writes are sufficient; per-run SQLite databases were never built and are no longer needed. |
| ~~DEF-090~~ | ~~`execution_record.py` stores time_of_day in UTC, should be ET per DEC-061~~ | ~~Sprint 27.5~~ | **RESOLVED** (Sprint 27.5 cleanup): `.astimezone(_ET)` before strftime. |
| DEF-091 | Add public accessors on V1 RegimeClassifier for trend_score computation and vol thresholds; also VIXDataService._config and _update_task private accessor instances (V2/server/routes access private attributes) | Unscheduled | V2 RegimeClassifierV2 accesses V1 private attributes for trend/vol computation. Sprint 27.9 added 3 new instances: regime.py accesses VIXDataService._config, server.py accesses _update_task for shutdown, VIX routes access private attrs. Add public accessors. Priority: LOW. **PARTIALLY RESOLVED (FIX-11, 2026-04-21):** API side resolved — `Orchestrator.attach_vix_service()` + `regime_classifier_v2` property, `RegimeClassifierV2.attach_vix_service()` + `vol_phase_calc`/`vol_momentum_calc`/`term_structure_calc`/`vrp_calc` properties, `VIXDataService.shutdown()`. `server.py` and `routes/vix.py` now use public API. Remaining: V2 access to V1 `trend_score`/vol thresholds + `VIXDataService._config` read by `RegimeClassifierV2.__init__` — untouched. |
| DEF-092 | Unused Protocol types (BreadthCalculator, CorrelationCalculator, SectorRotationCalculator, IntradayCalculator) in regime.py — V2 switched to concrete types | Unscheduled | Sprint 27.6 S6 switched from Protocol types to concrete types; Protocol definitions remain unused. Remove when confirmed unnecessary. Priority: LOW. |
| ~~DEF-093~~ | ~~main.py duplicate orchestrator YAML load + `_latest_regime_vector` typing~~ | — | **RESOLVED** (FIX-03, audit 2026-04-21): triple-load collapsed — Phase 8.5 + Phase 9 both read `config.orchestrator` from `load_config()` output; `OrchestratorConfig` import removed from `main.py`. `Orchestrator._latest_regime_vector` typed `RegimeVector \| None` via `TYPE_CHECKING` import. |
| DEF-094 | ORB Scalp time-stop dominance | Unscheduled | March 24 session showed ~80% of scalp exits via 120s time-stop (vs target or stop). Parameters (120s window, 0.3R target) may need tuning after more session data. Track over 5+ sessions before adjusting. Priority: LOW. |
| DEF-095 | Submit-before-cancel bracket amendment pattern | Unscheduled | Currently cancel-then-resubmit creates brief sub-second unprotected window. For live trading hardening, consider submitting new bracket legs before cancelling old ones. Ref: Sprint 27.65 S2 review finding. Priority: MEDIUM. |
| DEF-096 | Protocol type for duck-typed candle store reference in PatternBasedStrategy | Unscheduled | Currently uses `object` + `hasattr()`. A Protocol type would restore type safety without circular imports. Ref: Sprint 27.65 S4 review finding. Priority: LOW. |
| ~~DEF-097~~ | ~~Schedule monthly cache update cron job~~ | — | **RESOLVED** (audit 2026-04-21 FIX-21-ops-cron): Paired with DEF-162 in `docs/live-operations.md` §12 Scheduled Maintenance Tasks. Chained cron runs `populate_historical_cache.py --update` then `consolidate_parquet_cache.py --resume` at 02:00 ET on the 2nd of each month. |
| ~~DEF-085~~ | ~~Close-position endpoint regression~~ | ~~Sprint 25.8~~ | **RESOLVED** (Sprint 25.8, DEC-352): Routes through `OrderManager.close_position()`. 5 new tests. |
| ~~DEF-086~~ | ~~WebSocket test hangs~~ | ~~Post-sprint~~ | **RESOLVED**: 8 tests rewrote to test bridge pipeline directly via send_queue, eliminating sync/async cross-thread hang. |
| ~~DEF-087~~ | ~~11 pre-existing test failures~~ | ~~Post-sprint~~ | **RESOLVED**: 4 vectorbt (NumPy 2.x dep upgrade), 1 data_fetcher (Pandas 2.x datetime precision), 4 e2e telemetry (hardcoded date + async flush), 2 integration sprint20 (regime-based allocation assertions). Zero production code changes. |
| DEF-098 | Trade count inconsistency between Dashboard cards (Daily P&L=96, Positions=53) | Unscheduled | Root cause: paper trading ghost positions — entry fills recorded as trades but bracket legs cancelled by IBKR, positions not resolved through normal close flow. Positions card counts from OrderManager state, P&L/Trades from TradeLogger. Fix depends on DEF-099 resolution. Priority: MEDIUM. (NEEDS-INFO per audit P1-H4 — see docs/audits/audit-2026-04-21/p1-h4-def-triage.md) |
| DEF-099 | Position reconciliation ghost positions in paper trading | Sprint 27.8 | **PARTIALLY RESOLVED** (Sprint 27.8 S1): Reconciliation auto-cleanup (config-gated `reconciliation.auto_cleanup_orphans`) generates synthetic close records for orphaned positions. Bracket exhaustion detection triggers flatten when all bracket legs cancelled. ExitReason.RECONCILIATION distinguishes synthetic from real exits. Monitor over 5+ sessions before marking fully resolved. |
| DEF-100 | IBKR paper trading repricing storm (error 399 spam) | Unscheduled | IBKR paper trading thin-book simulation reprices market orders repeatedly (~1/sec/symbol). Sprint 27.75 log throttling mitigates noise. Underlying issue is IBKR-paper-specific — live trading unaffected. Potential mitigations: limit orders for paper, fill timeout+resubmit. Priority: LOW-MEDIUM. |
| ~~DEF-101~~ | ~~Tests coupled to paper-trading config values~~ | ~~Sprint 27.8~~ | **RESOLVED** (Sprint 27.8 S1): `test_engine_sizing.py` reads YAML and asserts match (not hardcoded). `test_config.py` uses ordering invariant assertions. Tests now pass regardless of paper vs live config values. |
| ~~DEF-102~~ | ~~Trades page server-side stats computation~~ | — | **RESOLVED** (Sprint 28.75 S2, subsumed by DEF-117): Server-side `GET /api/v1/trades/stats` endpoint replaces client-side computation from paginated subset. |
| DEF-103 | yfinance reliability as unofficial scraping library | Unscheduled | yfinance is an unofficial Yahoo Finance scraper — no SLA, may break on Yahoo HTML/API changes. Mitigations: SQLite persistence cache (survives outage), staleness self-disable (`max_staleness_days=3`), optional FMP fallback (`fmp_fallback_enabled` flag), daily-only frequency (not real-time). Monitor for breakage over 5+ sessions. Priority: LOW. |
| DEF-104 | Dual ExitReason enums (`events.py` + `trading.py`) must be kept in sync | Unscheduled | Sprint 27.8 added RECONCILIATION to events.py but missed trading.py, causing 336 Pydantic validation errors. Consolidation candidate for future cleanup sprint. Priority: MEDIUM. |
| DEF-105 | Reconciliation trades inflate `total_trades` count | Unscheduled | Reconciliation closes are counted as BREAKEVEN trades, inflating Dashboard total_trades and Positions card counts. Related to DEF-098 (trade count inconsistency). Priority: LOW. |
| DEF-106 | `from_dict()` in `models.py` contains ~8 `assert` statements in production deserialization | Unscheduled | Same pattern as assert isinstance fixes done in S6cf-1 (config_proposal_manager.py, learning.py routes). Should be replaced with `if/raise` guards. Priority: LOW. Discovered: Sprint 28 S6cf-1 review (F2). |
| DEF-107 | Unused `raiseRec` destructured variable in `LearningInsightsPanel.tsx` line 388 | Unscheduled | The `raise` property is aliased as `raiseRec` (reserved word workaround) but never referenced — only `lowerProposal`/`raiseProposal` from the same destructuring are used. Harmless, cosmetic. Priority: LOW. Discovered: Sprint 28 S6cf-1 review (F4). |
| DEF-108 | R2G `_build_signal` sync limitation — emits `atr_value=None` | Unscheduled | Red-to-Green strategy's `_build_signal` is synchronous, so it emits `atr_value=None`. If R2G ever needs ATR-based trailing stops, the method or its caller would need refactoring. Currently uses percent fallback as designed. Priority: LOW. Discovered: Sprint 28.5 S3. (NEEDS-INFO per audit P1-H4 — see docs/audits/audit-2026-04-21/p1-h4-def-triage.md) |
| DEF-109 | V1 trailing stop config dead code on `OrderManagerConfig` | Unscheduled | Legacy `enable_trailing_stop` and `trailing_stop_atr_multiplier` fields on `OrderManagerConfig` are no longer referenced in `on_tick` after Sprint 28.5 replaced the V1 skeleton. Dead code. Priority: LOW. Discovered: Sprint 28.5 S4b. |
| DEF-110 | Exit reason misattribution on escalation-failure + trail-active positions | Unscheduled | In `_handle_flatten_fill`, exit reason is set to `TRAILING_STOP` based on `position.trail_active`. If escalation stop update fails (AMD-3) on a trail-active position, the flatten is logged as TRAILING_STOP rather than an escalation-related reason. Cosmetic — position closes correctly. Priority: LOW. Discovered: Sprint 28.5 S4b. |
| ~~DEF-111~~ | ~~Trail stops not firing in live session~~ | — | **RESOLVED** (Sprint 28.75 S1): Config timing — operator changed YAML mid-session; ARGUS loads at startup only. Code paths verified correct. Trail will be live on next session boot. |
| ~~DEF-112~~ | ~~Flatten-pending orders hang indefinitely~~ | — | **RESOLVED** (Sprint 28.75 S1): Added `flatten_pending_timeout_seconds` (120s) + `max_flatten_retries` (3) to OrderManagerConfig. Stale flatten orders cancelled and resubmitted. |
| ~~DEF-113~~ | ~~"flatten already pending" log spam (2,003/session)~~ | — | **RESOLVED** (Sprint 28.75 S1): ThrottledLogger, 60s per-symbol suppression. |
| ~~DEF-114~~ | ~~"IBKR portfolio snapshot missing" log spam~~ | — | **RESOLVED** (Sprint 28.75 S1): ThrottledLogger, 600s per-symbol suppression. |
| ~~DEF-115~~ | ~~Closed positions tab capped at 50~~ | — | **RESOLVED** (Sprint 28.75 S2): Limit increased to 250 (API max). Badge uses total_count. |
| ~~DEF-116~~ | ~~TodayStats win rate shows 0%~~ | — | **RESOLVED** (Sprint 28.75 S2): Frontend display logic: `winRate > 0` → `trades > 0`. Backend compute_metrics was correct. |
| ~~DEF-117~~ | ~~Trades page stats freeze + filter bug~~ | — | **RESOLVED** (Sprint 28.75 S2): New server-side `GET /api/v1/trades/stats` endpoint. refetchOnWindowFocus enabled. Subsumes DEF-102. |
| ~~DEF-118~~ | ~~Avg R missing from Trades page summary~~ | — | **RESOLVED** (Sprint 28.75 S2): Added to TradeStatsBar via stats endpoint. |
| ~~DEF-119~~ | ~~Open positions colored P&L + exit price~~ | — | **RESOLVED** (Sprint 28.75 S2): Current price colored green/red relative to entry. P&L column already existed. |
| ~~DEF-120~~ | ~~VixRegimeCard fills entire viewport~~ | — | **RESOLVED** (Sprint 28.75 S2): Removed h-full, wrapped in motion.div staggerItem on all layouts. |
| ~~DEF-121~~ | ~~PatternBacktester `_create_pattern_by_name()` — extend for Sprint 29 patterns~~ | ~~Sprint 32~~ | **RESOLVED** (Sprint 32 S3 — PatternBacktester supports all 7 patterns via factory delegation). |
| DEF-122 | ABCD swing detection O(n³) optimization | Sprint 32 (parameter sweeps at scale) | ABCDPattern swing detection iterates O(n³) over candle history. PatternBacktester full sweep times out. Needs precomputed swing cache or algorithmic optimization before Sprint 32 parameter sweeps. Priority: MEDIUM. |
| DEF-123 | `build_parameter_grid()` float accumulation cleanup | Sprint 31.5 (Parallel Sweep Infrastructure) | While-loop float addition mitigated by round(v,6) + dedup but should use integer-stepping or numpy.arange. Cosmetic. Priority: LOW. |
| ~~DEF-124~~ | ~~Pattern constructor params not wired from config YAML at runtime~~ | ~~Sprint 32~~ | **RESOLVED** (Sprint 32 — generic pattern factory `build_pattern_from_config()` wires YAML params into pattern constructors via PatternParam introspection at startup). |
| DEF-125 | Time-of-day signal conditioning | Sprint 32 (Parameterized Templates) | March 31 session data shows 10:00 AM hour is the worst-performing (-$6,906, 31.1% win rate) while 12:00+ is nearly breakeven. No strategy currently adjusts behavior based on time-of-day beyond operating window. Add time-of-day as a parameter dimension. |
| DEF-126 | Regime-strategy interaction profiles | Sprint 32.5 (Experiment Registry) | Per-strategy regime sensitivity tuning. Needs RegimeVector × strategy performance matrix. Each strategy should have its own regime sensitivity profile rather than treating all strategies equally within a regime. |
| DEF-127 | Virtual scrolling for trades table | Unscheduled | TradesPage limit raised from 250 to 1000 (Sprint 29.5 S3). Full virtual scrolling (react-virtual) deferred until 1000 becomes insufficient. |
| DEF-128 | IBKR error 404 root cause: multi-position qty divergence prevention | Sprint 30 | When Argus tracks multiple positions on the same symbol, IBKR merges them. Partial closes can cause qty mismatch. Sprint 29.5 S1 added re-query-qty fix; preventing the divergence in the first place is a deeper fix. |
| ~~DEF-131~~ | ~~Experiments + Counterfactual Visibility (API + UI)~~ | — | **RESOLVED** (Sprint 32.5 S5+S6+S6f+S7): 3 new REST endpoints (`/counterfactual/positions`, `/experiments/variants`, `/experiments/promotions`) + Shadow Trades tab on Trade Log + Experiments page as 9th Command Center page. |
| ~~DEF-132~~ | ~~Exit Parameters as Variant Dimensions~~ | — | **RESOLVED** (Sprint 32.5 S1+S2): `ExitSweepParam` Pydantic model, `exit_overrides` on `VariantDefinition`, fingerprint expansion, spawner `deep_update` wiring, runner exit grid cross-product. |
| ~~DEF-133~~ | ~~Adaptive Capital Intelligence Vision Document~~ | — | **RESOLVED** (Sprint 32.5 S8): `docs/architecture/allocation-intelligence-vision.md` — 9-section vision for replacing stacked guardrails with unified `AllocationIntelligence` service. Phase 1 (~Sprint 34–35), Phase 2 (~Sprint 38+). |
| ~~DEF-134~~ | ~~BacktestEngine strategy type support for all 7 PatternModule patterns~~ | — | **RESOLVED** (Sprint 32.5 S3+S4): `StrategyType` enum extended to all 7 patterns; `_supply_daily_reference_data()` added for GapAndGo/PreMarketHighBreak. All patterns runnable via `scripts/run_experiment.py`. |
| DEF-135 | Full visual verification of Shadow Trades tab + Experiments page with live data | Unscheduled | S6 visual items 2–5 (table styling, rejection badges, grade badges, P&L coloring) and S7 visual items 2–5 (variant table, promotion log, pattern comparison) untestable until counterfactual positions and experiment variants accumulate during paper trading. Verify after first week with `experiments.enabled=true`. |
| ~~DEF-136~~ | ~~GoalTracker.test.tsx — 3 pre-existing Vitest failures~~ | — | **RESOLVED** (Sprint 32.75): `vi.useFakeTimers` date mock applied; `getByText` ambiguity fixed with `getByTestId`. |
| ~~DEF-137~~ | ~~`test_history_store_migration` hardcoded date decay~~ | — | **RESOLVED** (Sprint 32.8): Replaced hardcoded `"2026-03-25"` with `datetime.now(UTC) - timedelta(days=1)` in `tests/core/test_regime_vector_expansion.py`. |
| ~~DEF-138~~ | ~~`ArenaPage.test.tsx` WebSocket mock missing~~ | — | **RESOLVED** (Sprint 32.8): `vi.mock` for `useArenaWebSocket` added to `ArenaPage.test.tsx`. `vitest.config.ts` `testTimeout`/`hookTimeout` set to 10s. |
| ~~DEF-139~~ | ~~Startup zombie flatten queue not draining at market open~~ | — | **RESOLVED** (Sprint 32.9 S1): Root cause: `getattr(pos, "qty", 0)` in 4 Order Manager paths always returned 0 (Position model uses `shares`). Fixed to `getattr(pos, "shares", 0)`. |
| ~~DEF-140~~ | ~~EOD flatten reports positions closed but broker retains them~~ | — | **RESOLVED** (Sprint 32.9 S1): Same `qty`/`shares` mismatch in Pass 2 + fire-and-forget submission. Fixed attribute + added synchronous fill verification with asyncio.Event per symbol (30s timeout, 1 retry). |
| ~~DEF-141~~ | ~~Intelligence polling crash: unbound `symbols` variable~~ | — | **RESOLVED** (Sprint 32.9 S2): `symbols: list[str] = []` initialization before conditional branch in `startup.py`. Added try/except with `exc_info=True` around polling loop body. |
| ~~DEF-142~~ | ~~Quality engine grade compression — all signals scoring B. Sprint 32.9 recalibration edited `config/quality_engine.yaml` but `load_config()` reads `system_live.yaml`, which still carries pre-recal values.~~ | — | **RESOLVED** (audit 2026-04-21 FIX-01-catalyst-db-quality-pipeline) via **Option B** (DEC-384). `load_config()` now deep-merges standalone `config/<name>.yaml` files over the system block with precedence standalone > live > base; `config/quality_engine.yaml` is authoritative. `_STANDALONE_SYSTEM_OVERLAYS` in `argus/core/config.py` is the extensible registry. Regression guard: `tests/test_fix01_load_config_merge.py` (6 tests). `_score_historical_match()` hardened to `return 0.0` so the dormant dimension cannot reintroduce grade compression if its weight is bumped. |
| ~~DEF-143~~ | ~~BacktestEngine pattern initialization ignores config_overrides~~ | — | **RESOLVED** (Sprint 31A S1): All 7 `_create_*_strategy()` methods now use `build_pattern_from_config()`. No-arg constructors removed; config_overrides flow to pattern detection params. |
| ~~DEF-144~~ | ~~Debrief export safety_summary incomplete~~ | — | **RESOLVED** (Sprint 31A S1+S3): OrderManager 6 new safety tracking attrs (`margin_circuit_breaker_open_time`, `reset_time`, `entries_blocked_count`, `eod_flatten_pass1_count`, `eod_flatten_pass2_count`, `signal_cutoff_skipped_count`) + `increment_signal_cutoff()`. `_export_safety_summary` reads new attrs via isinstance guards. S3 wired `increment_signal_cutoff()` in `_process_signal()` pre-EOD cutoff block. |
| ~~DEF-145~~ | ~~Sweep tooling: `--universe-filter` + `--symbols` flags + universe-aware re-sweep~~ | — | **RESOLVED** (Sprint 31A.75 S1): `--symbols` (comma-separated or @filepath) and `--universe-filter` (loads `config/universe_filters/{pattern}.yaml`, queries DuckDB via `validate_symbol_coverage()`) added to `scripts/run_experiment.py`. `UniverseFilterConfig` Pydantic model added to `argus/intelligence/experiments/config.py`. |
| DEF-150 | Time-of-day arithmetic bug in `test_check_reminder_sends_after_interval`: `(datetime.now(UTC).minute - 2) % 60` mis-computes to 58/59 when minute ∈ {0,1}, setting "last notification" in the future for the first 2 minutes of every hour. NOT an xdist race as previously characterized. | FIX-13-test-hygiene | Re-diagnosed by audit 2026-04-21 P1-G1 M7. Original "xdist race" characterization was incorrect. One-line fix: replace with `datetime.now(UTC) - timedelta(minutes=2)` in `tests/sprint_runner/test_notifications.py:313-315`. Priority: LOW. |
| ~~DEF-151~~ | ~~date objects not JSON-serializable in `ExperimentStore.save_experiment()` — `json.dumps(record.backtest_result)` fails on `datetime.date` objects from `MultiObjectiveResult.to_dict()`. 143 Night 1 sweep grid points computed but zero saved to ExperimentStore.~~ | — | **RESOLVED** (Apr 4, commit 3a48bcf): Added `default=str` to `json.dumps(record.backtest_result)` in `store.py:193`. Regression test added. |
| ~~DEF-152~~ | ~~gap_and_go stop-price bug~~ | — | **RESOLVED** (Sprint 31.75 S1): Added `min_risk_per_share` parameter (default $0.10) + ATR-relative floor (10% of ATR). Rejects signals where `entry - stop` is too small to produce meaningful R-multiples. New PatternParam for sweep grid. |
| ~~DEF-153~~ | ~~config_fingerprint NULL in BacktestEngine trades~~ | — | **RESOLVED** (Sprint 31.75 S1): Added `config_fingerprint` field to `BacktestEngineConfig`. `_setup()` registers fingerprint with OrderManager after strategy creation. `_run_single_backtest()` worker passes fingerprint from ExperimentRunner. Live pipeline unchanged. |
| ~~DEF-154~~ | ~~VWAP Bounce sweep axes inadequate~~ | — | **RESOLVED** (Sprint 31.75 S2): Added 4 signal density controls: `min_approach_distance_pct` (0.3%, filters oscillation noise), `min_bounce_follow_through_bars` (2, requires confirmation), `max_signals_per_symbol` (3/day session cap), `min_prior_trend_bars` raised 10→15. `lookback_bars` 30→50. Target density: 0.5–3 signals/symbol/day (was 2–22). |
| ~~DEF-146~~ | ~~DuckDB BacktestEngine pre-filter wiring (`validate_symbol_coverage()` in ExperimentRunner)~~ | — | **RESOLVED** (Sprint 31.5 S2): `universe_filter: UniverseFilterConfig \| None` param on `run_sweep()`; `_resolve_universe_symbols()` private method calls `validate_symbol_coverage(min_bars=100)`; CLI delegates universe filtering to runner. |
| DEF-147 | DuckDB Research Console backend | Sprint 31B | HistoricalQueryService can serve as backend for Research Console page SQL-based sweep visualization and heatmaps. Priority: LOW. |
| DEF-148 | FRED macro regime service (FredMacroService + RegimeVector expansion) | Sprint 34 | New `argus/data/fred_macro_service.py` following VIXDataService pattern. Daily pull from FRED API (`fredapi`, $0). `MacroSnapshot` dataclass: yield_spread_10y2y, fed_funds_rate, initial_claims, cpi_yoy, pce_yoy, consumer_sentiment. Derived regimes: YieldCurveRegime, EmploymentRegime, InflationRegime, macro_composite_score. RegimeVector 3-4 new Optional fields. Integration: BriefingGenerator, Observatory, BacktestEngine retroactive labeling, Allocation Intelligence. Priority: MEDIUM. |
| DEF-149 | FRED VIX backup source (VIXCLS fallback in VIXDataService) | Opportunistic | FRED VIXCLS series as fallback when yfinance is unavailable. Priority: LOW. |
| ~~DEF-155~~ | ~~Premature `api_server → healthy` signal in startup path~~ | — | **RESOLVED** (Impromptu Apr 20, 2026): `main.py` now polls port with `_wait_for_port()` (60s timeout) before marking healthy. Previously fired immediately after `asyncio.create_task(server.serve())`. |
| ~~DEF-156~~ | ~~`start_live.sh` lacks post-startup API health probe~~ | — | **RESOLVED** (Impromptu Apr 20, 2026): Added `curl` probe loop (15 retries × 1s) against `/api/v1/market/status`; exits non-zero and kills process on timeout. Also kills orphaned Vite processes on ports 5173–5175. |
| ~~DEF-157~~ | ~~`evaluation.db` exceeds 4 GB despite DEC-345 7-day retention — missing VACUUM~~ | — | **RESOLVED** (Impromptu Apr 20, 2026): Added VACUUM after retention DELETE in `EvaluationEventStore.cleanup_old_events()` (close→sync VACUUM→reopen pattern). Startup reclaim triggers VACUUM when file >500 MB AND freelist >50%. Observability: size/freelist logged at INFO on init, WARNING if >2 GB post-maintenance. Manual VACUUM confirmed: 3.7 GB → 209 MB. Secondary concern (36K events/min write volume) not addressed — observability only. |
| ~~DEF-158~~ | ~~Duplicate/excessive SELL orders causing positions to flip short (-2× original long)~~ | — | **RESOLVED** (Impromptu Apr 20, 2026): Three root causes: (1) `_check_flatten_pending_timeouts` resubmitted MARKET SELL while original order was still filling at IBKR (120s timeout < IBKR paper fill latency) — fix: query broker position before resubmitting, skip if already flat; (2) `_flatten_unknown_position` (startup cleanup) didn't cancel pre-existing bracket orders — fix: cancel all open orders for symbol before placing flatten SELL; (3) `_handle_stop_fill` didn't cancel concurrent flatten orders — fix: cancel pending flattens when stop fills. Also added stale-flatten cancellation in `_handle_flatten_fill`. +5 pytest. |
| ~~DEF-159~~ | ~~Reconstructed flatten trades logged with entry_price=0.00 as "wins"~~ | — | **RESOLVED** (Impromptu Apr 20, 2026): Added `entry_price_known` boolean column to trades table (default true). `_close_position()` sets `entry_price_known=False` when `entry_price == 0.0`. `compute_metrics()`, `get_todays_pnl()`, `get_todays_trade_count()`, and `get_daily_summary()` exclude trades with `entry_price_known=0`. Migration script retroactively marked 10 affected rows from the Apr 20 incident. +4 pytest. |
| DEF-160 | Shutdown race between bracket-cancel flatten and stop-retry path — during `reqGlobalCancel()` at shutdown, bracket exhaustion fires flatten while stop-retry path tries to re-place stops that were just cancelled. Produces misleading 'Emergency flattening' ERROR logs. Positions are correctly flattened; cosmetic only. | Unscheduled | May be partially subsumed by DEF-158 fix (stop-fill now cancels pending flattens). Priority: LOW. |
| ~~DEF-161~~ | ~~DuckDB Parquet consolidation needed — 983K individual Parquet files make DuckDB queries unusable~~ | — | **RESOLVED** (Sprint 31.85): `scripts/consolidate_parquet_cache.py` produces derived `data/databento_cache_consolidated/` (~24K per-symbol files with embedded `symbol` column). Non-bypassable row-count validation (`consolidated_row_count == sum(monthly_row_counts)`); atomic `.tmp → rename` only after validation passes; `--verify`/`--verify-only` runs DuckDB benchmark suite (Q1 COUNT DISTINCT, Q2 single-symbol range, Q3 batch coverage). Original cache untouched; `HistoricalQueryService`, `HistoricalQueryConfig`, `config/historical_query.yaml` unmodified — operator repoints `cache_dir` post-consolidation. See `docs/operations/parquet-cache-layout.md`. +15 pytest. |
| ~~DEF-162~~ | ~~Monthly re-consolidation cron scheduling for `scripts/consolidate_parquet_cache.py` — chains with the existing `scripts/populate_historical_cache.py --update` cron (DEF-097).~~ | — | **RESOLVED** (audit 2026-04-21 FIX-21-ops-cron): Paired with DEF-097 in `docs/live-operations.md` §12 Scheduled Maintenance Tasks. Chained cron runs `populate_historical_cache.py --update` then `consolidate_parquet_cache.py --resume` at 02:00 ET on the 2nd of each month, with `&&` ensuring consolidation only runs on successful population. |
| DEF-163 | Timezone-boundary bugs + hardcoded Vitest dates (NOT date-decay as previously characterized): (a) `test_get_todays_pnl_excludes_unrecoverable` writes `datetime.now(UTC)` but SQL filters by ET — fails 20:00-00:00 ET daily; (b) `test_history_store_migration` has a second hardcoded default at line 36 (Sprint 32.8 fix only touched the explicit override at line 302); (c) 4 Vitest files with hardcoded absolute dates per P1-F2 M9. | FIX-13-test-hygiene | Re-diagnosed by audit 2026-04-21 P1-G1 M5, M6 + P1-F2 M9. Three root causes, all trivially fixable. Batched into FIX-13-test-hygiene. Priority: LOW. |
| DEF-164 | Late-night ARGUS boot collides with after-hours auto-shutdown — during Sprint 31.85 operator activation on 2026-04-20 at 23:30 ET, ARGUS's time-based after-hours auto-shutdown fired at 23:32:55, approximately 51 seconds after HistoricalQueryService began schema discovery and before VIEW creation completed. The interrupted DuckDB VIEW creation caused the shutdown sequence to hang at 70% CPU / 40% memory until force-killed. Impact: any operator-initiated ARGUS start between ~22:30 ET and market open next day may fail to complete service init. Candidate fixes: (a) shutdown sequence waits for in-flight service init to complete, (b) auto-shutdown suppressed for N minutes after boot, (c) document "do not start ARGUS between 22:30 ET and pre-market" in `docs/live-operations.md`. | Unscheduled | Opened Sprint 31.85 operator activation (Phase 5/6). Priority: LOW. |
| DEF-165 | DuckDB connection close hangs when CREATE VIEW is interrupted — during the DEF-164 shutdown-mid-init sequence, `HistoricalQueryService.close()` (or equivalently the DuckDB connection teardown) hung indefinitely with the process at 70% CPU / 40% memory. Root cause likely in `HistoricalQueryService.close()` not cancelling in-flight DuckDB DDL before calling `conn.close()`, or in pyduckdb's connection-close behavior when a CREATE VIEW operation is mid-flight. Candidate fix: `HistoricalQueryService.close()` calls `conn.interrupt()` before `conn.close()`. | Unscheduled | Opened Sprint 31.85 operator activation (Phase 5/6). Priority: LOW (only manifests when shutdown coincides with service init, which DEF-164 already covers operationally). |
| DEF-166 | `test_speed_benchmark` flaky under pytest-cov (not previously tracked — surfaced by audit P1-G1 during coverage run) | Unscheduled | Opened by audit 2026-04-21 P1-H4. Not blocking; flag for next test-hygiene pass. Priority: LOW. |
| DEF-167 | Vitest hardcoded-date decay — `VitalsStrip.test.tsx:59`, `StrategyDecisionStream.test.tsx:30`, `useQuality.test.tsx:48`, `useArenaWebSocket.test.ts:72` embed absolute date strings in fixtures. Same root-cause class as pytest DEF-163. | FIX-11-backend-api (spot fix) + FIX-13-test-hygiene (scan) | **PARTIALLY RESOLVED** (FIX-11, 2026-04-21) — the four flagged files now use `new Date().toISOString()` at fixture-build time (Vitest equivalent of the pattern in `TradeStatsBar.test.tsx`). Scan for other offenders during FIX-13. Priority: LOW. |
| DEF-168 | `docs/architecture.md` API catalog is substantially drifted (≥10 mismatches audited 2026-04-21) — `/catalysts*` path wrong, non-existent `/catalysts/refresh`, wrong `/intelligence/briefings` path, AI POSTs that don't exist, wrong replay path, wrong arena-positions auth claim, entire Experiments/Watchlist/Controls/Trades-stats/Historical sections undocumented. | P1-H1a (context compression) | Opened by audit 2026-04-21 P1-F1-8 (FIX-11). A warning banner has been added in place pointing readers at the route modules; the correct fix is to mechanically regenerate the catalog by introspecting the FastAPI app. Priority: MEDIUM — AI assistants and new operators read the wrong contract. |
| DEF-169 | `--dev` mode retired (FIX-11). ARGUS's frontend dev loop now requires a full backend boot (`python -m argus.main`). `dev_state.py`, `argus/api/__main__.py`, `tests/api/test_dev_state_patterns.py`, `tests/api/test_dev_state_dashboard.py` deleted. The `_mock_watchlist` attribute monkey-patched onto AppState is now a test-only injection mechanism used by `tests/api/test_watchlist.py`; it is no longer a dev-mode sentinel in production code. `GET /trades/{id}/replay` is now 501 until DEF-029 lands. | Monitor | Opened by audit 2026-04-21 P1-F1-2 + P1-F1-10 + P1-F1-11 + P1-F1-22 (FIX-11). If a lightweight mock-data harness is ever needed again, build it against the same `TestClient` + Pydantic-fixture pattern tests use, not as a parallel AppState factory. Priority: INFORMATIONAL. |
| DEF-170 | VIX regime calculators stay None in production: `main.py:770` constructs `RegimeClassifierV2` without `vix_data_service` (falls through to no-VIX branch); `Orchestrator.attach_vix_service()` chains to `RegimeClassifierV2.attach_vix_service()` but the latter explicitly does NOT re-instantiate calculators (docstring confirms). `GET /vix/current` likely returns empty `vol_regime_phase` / `vol_regime_momentum` / `term_structure` / `vrp` classifications. Pre-existing; surfaced by FIX-11 L3 review observation on 2026-04-21. | FIX-05-core (natural scope) | Fix: either (a) construct `RegimeClassifierV2` after VIX service comes up (reorder in main.py), or (b) make `attach_vix_service()` re-instantiate the four calculators against the newly attached service. Verify by hitting `GET /vix/current` in a live boot and confirming non-None classifications. Priority: MEDIUM — production VIX regime intelligence currently inert. |
| DEF-171 | `tests/execution/test_ibkr_broker.py::TestIBKRBrokerBracketOrders::test_all_ulids_mapped_bidirectionally` xdist flake — fails intermittently when run via `pytest -n auto`, passes 100% in isolation. Observed 3 times during Sprint 31.9 Stage 1 review runs (FIX-20, FIX-01, FIX-11). Distinct from DEF-150 (time-of-day) and DEF-163 (date-decay). Likely test-ordering or shared-state issue. | FIX-13-test-hygiene (natural scope, already in campaign) | Run the test with `-p no:xdist` vs `-n auto` and diff the failure logs. Suspect: module-level state in ibkr_broker test fixtures that isn't reset between xdist workers. Priority: LOW (flake, not correctness). |
| DEF-172 | Duplicate `CatalystStorage` instances active concurrently in live mode (P1-D1-M13, audit 2026-04-21). Even after FIX-01 repointed both paths at `data/catalyst.db`, there are still two `aiosqlite.Connection` objects reading/writing the same file — one built by `main.py` for the quality pipeline (Phase 10.25), one built by `intelligence/startup.py` for the catalyst pipeline + API routes. WAL-protected but wasteful; the second connection's WAL checkpoints can delay the first's reads. The close-path asymmetry (leak) was addressed by FIX-03 (`_catalyst_storage.close()` now runs in `shutdown()` step 5a). | Future consolidation session touching both `main.py` and `argus/api/server.py` lifespan | Cleanest fix per audit: move the quality-pipeline init into `api/server.py` lifespan alongside the catalyst pipeline, with shared storage injected. FIX-03 declined the api/server.py edit per scope discipline (api module is FIX-11 territory, already closed). Priority: LOW — resource duplication only; correctness unaffected. |
| DEF-173 | `LearningStore.enforce_retention()` never called at boot or on any schedule (P1-D2-M03, audit 2026-04-21, FIX-03 partial resolution). ExperimentStore retention is now enforced in `main.py` at boot; `LearningStore` is instantiated inside `argus/api/server.py` lifespan and would need the same treatment there, but FIX-03 declined to touch `api/server.py` (FIX-11 scope, already closed). Result: `data/learning.db` still grows unbounded until a follow-on session wires `await learning_store.enforce_retention(learning_loop_config.report_retention_days)` into the lifespan alongside LearningStore creation. | Future follow-on touching `api/server.py` lifespan | Mirror the counterfactual + experiment pattern already in place. Priority: LOW — slow accretion, no active failure. |

## Reference

| Document | What It Covers |
|----------|---------------|
| `docs/decision-log.md` | All 383 DEC entries with full rationale (no new DECs in Sprints 32–31A.5, 31.8, or 31.85 — all design decisions followed established patterns) |
| `docs/dec-index.md` | Quick-reference index with status markers |
| `docs/sprint-history.md` | Complete sprint history (1–29.5 + 32–31A.5 + sub-sprints) |
| `docs/pre-live-transition-checklist.md` | Config + test values to restore before live trading |
| `docs/process-evolution.md` | Workflow evolution narrative |
| `docs/live-operations.md` | Live trading procedures |
| `docs/strategies/STRATEGY_*.md` | Per-strategy spec sheets |
| `docs/risk-register.md` | Active risks and assumptions |
| `docs/project-bible.md` | System vision and invariants |
| `docs/architecture.md` | Technical blueprint |
| `docs/roadmap.md` | Strategic vision + sprint queue (DEC-262) |
| `docs/sprint-campaign.md` | Operational sprint choreography |
| `docs/ui/ux-feature-backlog.md` | Planned UI/UX enhancements |
| `.claude/rules/` | Backtesting, trading-strategies, universal rules |
| `.claude/skills/doc-sync.md` | Documentation sync protocol |

# Audit: Config Consistency (YAML ↔ Pydantic)
**Session:** P1-H2
**Date:** 2026-04-21
**Scope:** Cross-reference every YAML under `config/` against every Pydantic config model to find silent drops, default divergences, and dead standalone YAMLs.
**Files examined:** 44 YAMLs (18 root + 15 strategies + 11 universe_filters) × 8 Pydantic modules (`argus/core/config.py` 1,751L, `argus/analytics/config.py` 29L, `argus/backtest/config.py` 218L, `argus/data/historical_query_config.py` 47L, `argus/data/vix_config.py` 201L, `argus/intelligence/config.py` 290L, `argus/intelligence/experiments/config.py` 81L, `argus/ai/config.py` 62L) + `argus/intelligence/learning/models.py` L:382-402 (LearningLoopConfig) + `argus/core/regime.py` L:300-341 (RegimeOperatingConditions dataclass).

---

## Summary

> **44 YAMLs × 9 Pydantic models → 9 silent-drop patterns, 5 default divergences, 7 functionally-dead YAMLs, 2 critical drift findings with live trading impact.**

- **Plan vs reality correction:** The audit prompt said "42 YAMLs … plan says 44 — this is already a discrepancy worth noting." **The plan was right: 44 YAMLs is the actual count.** `find config -name "*.yaml" -type f | wc -l` = 44. The "42" in the prompt was a mis-count of the root level (should be 18, not 17) and strategies (should be 15, not 13 — `afternoon_momentum.yaml` and `red_to_green.yaml` were missed).
- **The 3 missing profile YAMLs the plan asked about (`system_paper.yaml`, `system_backtest.yaml`, standalone `ai.yaml`/`ibkr.yaml`/`intelligence.yaml`) indeed do not exist.** All runtime profiling is done via `system.yaml` (Alpaca incubator) vs `system_live.yaml` (Databento + IBKR). Paper-trading overrides live inline in `system_live.yaml` (quality_engine.risk_tiers 10x-reduced, risk_limits.yaml daily_loss 1.0) and in `orchestrator.yaml` (consecutive_loss_throttle 999, suspension_sharpe -999). There is no dedicated paper config file — this is by design, but not documented anywhere.
- **Two findings merit immediate triage.** (1) `quality_engine.yaml` holds the Sprint 32.9 recalibration (weights → 0.375/0.0/0.275, thresholds → 72/66/…) but the **runtime path reads `config.system.quality_engine`** from the `quality_engine:` section of `system.yaml` / `system_live.yaml`, which STILL holds the pre-recalibration values (0.30/0.15/0.20, thresholds 90/80/70). If the Sprint 32.9 recalibration was meant to be live, it is not. (2) `experiments.yaml` is loaded as a raw dict in `main.py:846` and never passes through the `ExperimentConfig` Pydantic model — bypassing `extra="forbid"` and all field validation (the ExperimentConfig class is defined with `extra="forbid"` but that only fires if someone instantiates it, which production never does).
- **5 standalone YAMLs are functionally dead** in the sense that the file exists and is tested but **nothing in `argus/` loads it at runtime**. Operators editing them will see no effect on the running system. They are: `regime.yaml`, `vix_regime.yaml`, `counterfactual.yaml`, `overflow.yaml`, `learning_loop.yaml`. A sixth, `quality_engine.yaml`, is partially dead (only `ConfigProposalManager` reads/writes it, but the runtime `SetupQualityEngine` never re-reads after startup and its initial values come from `system.yaml`'s `quality_engine:` section instead). A seventh, `historical_query.yaml`, is also dead (`system.yaml` has its own `historical_query:` block).
- **Context for "dead" findings:** Sprint 27.9's `session-1b-impl.md` explicitly notes the pattern: *"config/vix_regime.yaml was a standalone file never loaded by load_config(). Added vix_regime: enabled: true to both system.yaml and system_live.yaml."* — but only the `enabled` key was inlined; all boundary parameters are still in the standalone file, which is still unread. This is a **recurring architectural drift**, not a one-off bug, and the project has **been burned by it at least three times** (Sprint 27.9 discovered it for VIX, Sprint 28.5 discovered it for exit management, and the current state shows it still alive for regime / counterfactual / overflow / learning_loop).

---

## Q1 — Main Mapping Table (YAML section → Pydantic model → status)

Status legend: **L** = Loaded at runtime (YAML consumed by some `argus/**/*.py` loader). **D** = Dead (file exists, no production loader calls it; tests may still load it). **P** = Partial (some keys routed to Pydantic, others loaded as raw dict). **INLINE** = section populates a sub-field on `SystemConfig` via the embedding `system.yaml` / `system_live.yaml`.

| YAML file | Top-level keys | Consumer in code | Pydantic model (if any) | Status |
|---|---|---|---|---|
| `system.yaml` | `timezone`, `market_open`, …, `ibkr`, `health`, `api`, `ai`, `universe_manager`, `catalyst`, `quality_engine`, `counterfactual`, `overflow`, `observatory`, `historical_query`, `vix_regime`, `reconciliation`, `startup`, `goals` | `load_config()` in `argus/core/config.py:1321` → `ArgusConfig.system = SystemConfig(**raw["system"])` | **`SystemConfig`** (`argus/core/config.py:375`) | **L** |
| `system_live.yaml` | same as system.yaml | same (alternative system file via `--config`) | same | **L** |
| `risk_limits.yaml` | `account`, `cross_strategy`, `pdt` | `load_config()` → `RiskConfig(**raw["risk"])` | **`RiskConfig`** (`core/config.py:463`) | **L** |
| `brokers.yaml` | `primary`, `alpaca`, `databento` | `load_config()` → `BrokerConfig(**raw["broker"])` | **`BrokerConfig`** (`core/config.py:601`) | **L** |
| `orchestrator.yaml` | `allocation_method`, `max_allocation_pct`, …, `signal_cutoff_enabled`, `orb_family_mutual_exclusion` | `load_config()` → `OrchestratorConfig(**raw["orchestrator"])`; also re-read at `main.py:739` for regime v2 | **`OrchestratorConfig`** (`core/config.py:609`) | **L** |
| `notifications.yaml` | `telegram`, `discord`, `email`, `push` | `load_config()` → `NotificationsConfig(**raw["notifications"])` | **`NotificationsConfig`** (`core/config.py:666`) | **L** |
| `order_manager.yaml` | `eod_flatten_time`, `stop_retry_max`, …, `margin_rejection_threshold` | `main.py:1041` `load_yaml_file()` → `OrderManagerConfig(**raw)` | **`OrderManagerConfig`** (`core/config.py:800`) | **L** |
| `scanner.yaml` | `scanner_type`, `static_symbols`, `fmp_scanner`, `alpaca_scanner`, `databento_scanner` | `main.py:322` raw dict → three `@dataclass`-flavored config classes (not Pydantic) | **`ScannerConfig`** (`core/config.py:788`) — **UNUSED** at runtime. `FMPScannerConfig` (`argus/data/fmp_scanner.py:27`) and `AlpacaScannerConfig` (`core/config.py:843`) and `DatabentoScannerConfig` (`argus/data/databento_scanner.py:34`) receive the sub-dicts directly. | **P** |
| `exit_management.yaml` | `trailing_stop`, `escalation` | `main.py:1056` → `ExitManagementConfig(**raw)` | **`ExitManagementConfig`** (`core/config.py:281`, `extra="forbid"`) | **L** |
| `quality_engine.yaml` | `enabled`, `weights`, `thresholds`, `risk_tiers`, `min_grade_to_trade` | `load_quality_engine_config()` (`intelligence/quality_engine.py:36`) — **not called at runtime**; `ConfigProposalManager` (`intelligence/learning/config_proposal_manager.py:52`) reads+writes at startup only | **`QualityEngineConfig`** (`intelligence/config.py:265`) | **D (runtime), L (ConfigProposalManager only)** |
| `counterfactual.yaml` | `counterfactual.enabled`, …, `eod_close_time` | **no production loader found**; `config.system.counterfactual` is populated from `system.yaml`'s `counterfactual:` section instead | **`CounterfactualConfig`** (`intelligence/config.py:234`) | **D** |
| `overflow.yaml` | `overflow.enabled`, `broker_capacity` | **no production loader found**; `config.system.overflow` populated from `system.yaml`'s `overflow:` section | **`OverflowConfig`** (`intelligence/config.py:250`) | **D** |
| `regime.yaml` | `enabled`, `persist_history`, `vix_calculators_enabled`, `breadth`, `correlation`, `sector_rotation`, `intraday` | **no production loader found**; `config.system.regime_intelligence` uses **only Pydantic defaults** because `system.yaml` / `system_live.yaml` have NO `regime_intelligence:` section | **`RegimeIntelligenceConfig`** (`core/config.py:160`) | **D** |
| `vix_regime.yaml` | `enabled`, `yahoo_symbol_vix`, …, `vol_regime_boundaries`, `term_structure_boundaries`, `vrp_boundaries` | **no production loader found**; `system.yaml`'s `vix_regime:` only sets `enabled: true` — all boundary sub-models use Pydantic defaults | **`VixRegimeConfig`** (`data/vix_config.py:143`) | **D** |
| `learning_loop.yaml` | `enabled`, `analysis_window_days`, `min_sample_count`, … | **no production loader found**; `system.yaml` has NO `learning_loop:` section → **uses Pydantic defaults only** | **`LearningLoopConfig`** (`intelligence/learning/models.py:382`) | **D** |
| `experiments.yaml` | `enabled`, `auto_promote`, `variants`, …, `exit_sweep_params` | `main.py:846` `load_yaml_file()` as **raw dict**, passed to `VariantSpawner(store, raw_dict)` and `PromotionEvaluator(config=raw_dict)` | **`ExperimentConfig`** (`intelligence/experiments/config.py:37`, `extra="forbid"`) — **NEVER INSTANTIATED in production** | **P (raw-dict only, Pydantic unused)** |
| `historical_query.yaml` | `historical_query.enabled`, `cache_dir`, `max_memory_mb`, `default_threads`, `persist_path` | **no production loader found**; `config.system.historical_query` populated from `system.yaml`'s `historical_query:` section | **`HistoricalQueryConfig`** (`data/historical_query_config.py:14`) | **D** |
| `backtest_universe.yaml` | `symbols` | `scripts/run_validation.py:23-34` only | — | **Scripts-only** |
| `strategies/abcd.yaml` | `strategy_id`, `name`, …, `pattern_class`, `allowed_regimes`, `universe_filter`, `exit_management`, `backtest_summary` | `main.py:602` → `load_abcd_config()` → `ABCDConfig(**raw)`. Additionally, `main.py:1063-1068` re-scans strategies dir to extract `exit_management:` blocks as raw dicts. | **`ABCDConfig`** (`core/config.py:1178`) (extends `StrategyConfig`, default `extra="ignore"`) | **L** |
| `strategies/afternoon_momentum.yaml` | ditto | `main.py` → `load_afternoon_momentum_config()` → `AfternoonMomentumConfig` | **`AfternoonMomentumConfig`** (`core/config.py:934`) | **L** |
| `strategies/bull_flag.yaml` | ditto | `main.py` → `load_bull_flag_config()` → `BullFlagConfig` | **`BullFlagConfig`** (`core/config.py:1012`) | **L** |
| `strategies/dip_and_rip.yaml` | ditto | `main.py` → `load_dip_and_rip_config()` → `DipAndRipConfig` | **`DipAndRipConfig`** (`core/config.py:1070`) | **L** |
| `strategies/flat_top_breakout.yaml` | ditto | `main.py` → `load_flat_top_breakout_config()` → `FlatTopBreakoutConfig` | **`FlatTopBreakoutConfig`** (`core/config.py:1042`) | **L** |
| `strategies/gap_and_go.yaml` | ditto | `main.py` → `load_gap_and_go_config()` → `GapAndGoConfig` | **`GapAndGoConfig`** (`core/config.py:1134`) | **L** |
| `strategies/hod_break.yaml` | ditto | `main.py` → `load_hod_break_config()` → `HODBreakConfig` | **`HODBreakConfig`** (`core/config.py:1101`) | **L** |
| `strategies/micro_pullback.yaml` | ditto | `main.py` → `load_micro_pullback_config()` → `MicroPullbackConfig` | **`MicroPullbackConfig`** (`core/config.py:1260`) | **L** |
| `strategies/narrow_range_breakout.yaml` | ditto | `main.py` → `load_narrow_range_breakout_config()` → `NarrowRangeBreakoutConfig` | **`NarrowRangeBreakoutConfig`** (`core/config.py:1636`) | **L** |
| `strategies/orb_breakout.yaml` | ditto | `main.py` → `load_orb_config()` → `OrbBreakoutConfig` | **`OrbBreakoutConfig`** (`core/config.py:863`) | **L** |
| `strategies/orb_scalp.yaml` | ditto | `main.py` → `load_orb_scalp_config()` → `OrbScalpConfig` | **`OrbScalpConfig`** (`core/config.py:881`) | **L** |
| `strategies/premarket_high_break.yaml` | ditto | `main.py` → `load_premarket_high_break_config()` → `PreMarketHighBreakConfig` | **`PreMarketHighBreakConfig`** (`core/config.py:1226`) | **L** |
| `strategies/red_to_green.yaml` | ditto | `main.py` → `load_red_to_green_config()` → `RedToGreenConfig` | **`RedToGreenConfig`** (`core/config.py:973`) | **L** |
| `strategies/vwap_bounce.yaml` | ditto | `main.py` → `load_vwap_bounce_config()` → `VwapBounceConfig` | **`VwapBounceConfig`** (`core/config.py:1598`) | **L** |
| `strategies/vwap_reclaim.yaml` | ditto | `main.py` → `load_vwap_reclaim_config()` → `VwapReclaimConfig` | **`VwapReclaimConfig`** (`core/config.py:899`) | **L** |
| `universe_filters/*.yaml` (×11) | `min_price`, `max_price`, `min_avg_volume`, `min_market_cap`, `max_market_cap` | `scripts/run_experiment.py:196`, `scripts/resolve_sweep_symbols.py:39`, `scripts/resolve_symbols_fast.py:32` only | **`UniverseFilterConfig`** (`intelligence/experiments/config.py`; different from the one in `core/config.py:319`) | **Scripts-only** |

---

## Q2 — Silent-Drop List (CRITICAL → LOW)

A "silent drop" is a YAML key that does not match any Pydantic field name, so Pydantic's default `extra="ignore"` behavior discards it at load time without any warning or error. Operators edit the key assuming it takes effect; it does not.

| # | Severity | YAML:line | Key | Expected Pydantic field (if any) | Impact |
|---|---|---|---|---|---|
| S-01 | **CRITICAL** | `config/strategies/abcd.yaml:33`, `bull_flag.yaml:32`, `flat_top_breakout.yaml:31`, `gap_and_go.yaml:35`, `hod_break.yaml:35`, `afternoon_momentum.yaml:39`, `vwap_reclaim.yaml:37`, `vwap_bounce.yaml:39`, `micro_pullback.yaml:37`, `narrow_range_breakout.yaml:36`, `premarket_high_break.yaml:35`, `dip_and_rip.yaml:37` (12 of 15 strategy YAMLs) | `benchmarks.min_sharpe` | `benchmarks.min_sharpe_ratio` (`PerformanceBenchmarks.min_sharpe_ratio` in `core/config.py:726`) | Every strategy benchmark gate that depends on Sharpe threshold is using the **Pydantic default (0.0)**, not the configured 0.3. The strategies `orb_breakout.yaml`, `orb_scalp.yaml`, `red_to_green.yaml` use the correct key — so 3 of 15 benchmark configs actually apply. The "min_sharpe: 0.3" in the other 12 is ignored. Benchmark enforcement is used by pipeline-stage promotion / demotion logic and by Performance page display. Paper-trading impact: cosmetic (thresholds are display-only during incubation). Live-trading impact: medium if these thresholds were to gate auto-promote / auto-demote decisions. |
| S-02 | **CRITICAL** | `config/experiments.yaml` (whole file) | `variants` nested dict values (per-variant `params.*`) | The `variants` dict is passed to `VariantSpawner` which reads `params` as raw dicts and writes them into per-variant `config_overrides`. `ExperimentConfig` Pydantic `variants: dict[str, list[dict[str, Any]]]` has no validation of variant param keys against the target pattern's config. | Operators can typo any parameter name in any variant definition (e.g. `min_gap_pct` instead of `min_gap_percent`) and the variant spawns with that value silently dropped by the pattern constructor's default-ignore. The 22-variant shadow fleet is currently collecting data; any typo'd param is invisible. **Recommend:** add a spawn-time validation pass that checks each `params.*` key against `get_pattern_class(pattern_name)(...).get_default_params()` field names, failing loudly on mismatch. |
| S-03 | HIGH | `config/strategies/abcd.yaml:36-48`, `bull_flag.yaml:35-51`, `flat_top_breakout.yaml:34-..`, all 15 strategy YAMLs (`backtest_summary:` block) | `data_source`, `universe_size`, `universe_note`, `avg_win_rate`, `avg_profit_factor`, `data_range`, `prior_baseline` (7 extra fields) | `BacktestSummaryConfig` (`core/config.py:730`) only defines `status`, `wfe_pnl`, `oos_sharpe`, `total_trades`, `data_months`, `last_run` | 7 of the ~13 fields written per strategy are silently dropped. Impact: the Strategy Library frontend card shows `status`, `oos_sharpe`, `total_trades`, `data_months`, `last_run` — so the extra fields are purely documentary. But the Strategy Library card code path reads `strategy.config.backtest_summary`, and if any future code reads `backtest_summary.data_source` (e.g. to filter provisional vs databento-validated), it will silently get None. |
| S-04 | MEDIUM | `config/experiments.yaml:77-78` | `backtest_start_date`, `backtest_end_date` (in YAML? NO — not present) and the sub-field `variants.*[].mode` (YAML uses `mode: "shadow"` → valid string, but `ExperimentConfig` model has no `mode` field on the list-element dict shape — the dict shape is `dict[str, Any]` so nothing validates). | `VariantDefinition`-equivalent dataclass does exist in `intelligence/experiments/spawner.py` but `ExperimentConfig.variants` uses `dict[str, Any]` as the value shape, bypassing it. | Variant spawning uses an internal validated type inside `spawner.py` but the YAML-to-raw-dict pipeline skips the outer check. Low operational impact today (spawner.py does validate internally), but the `extra="forbid"` promise at the config top level is broken. |
| S-05 | MEDIUM | `config/scanner.yaml:19-33` (`fmp_scanner` block) | `base_url` | `FMPScannerConfig` dataclass has `base_url: str = "https://financialmodelingprep.com/stable"` but scanner.yaml's `fmp_scanner:` section does not set it. | Uses default — NOT a drop, but worth noting: if operator intends to route through a proxy / staging endpoint, there's no config path exposed. |
| S-06 | MEDIUM | `config/scanner.yaml` top level | `fmp_scanner`, `alpaca_scanner`, `databento_scanner` (3 nested blocks) | `ScannerConfig` Pydantic model (`core/config.py:788`) only has `scanner_type` and `static_symbols`. The three nested blocks are silently dropped by Pydantic. | **The Pydantic `ScannerConfig` is not used at runtime** — `main.py:322` parses the raw dict directly — so this is not a hot-path bug. But `tests/core/test_config.py:189` tests `load_scanner_config(Path("config/scanner.yaml"))` through the Pydantic path; that test is guaranteed to strip the nested blocks without flagging. The `ScannerConfig` Pydantic class should either be deleted or extended to cover all three nested configs. |
| S-07 | MEDIUM | `config/system.yaml:44-45` / `config/system_live.yaml:180-181` (`startup:`) | `flatten_unknown_positions` (correct field) — but note: the `startup` field is declared **twice** in `system_live.yaml` (lines 180-181 and nowhere else — I was wrong; verified once). However `SystemConfig.startup: StartupConfig` wiring is fine. | No silent drop here — this one actually works. Marking LOW and removed from the list. | — |
| S-08 | MEDIUM | `config/strategies/abcd.yaml:36`, `hod_break.yaml`, `dip_and_rip.yaml`, `gap_and_go.yaml`, `premarket_high_break.yaml`, `micro_pullback.yaml`, `vwap_bounce.yaml`, `narrow_range_breakout.yaml` (the 10 PatternModule strategies) | `pattern_class: "ABCDPattern"` (only ABCD) | `ABCDConfig.pattern_class: str = Field(default="ABCDPattern")` at `core/config.py:1187` — **only defined on ABCDConfig**, not on other pattern strategies. | Not a silent drop on abcd.yaml (the field exists there). But if an operator adds `pattern_class:` to a non-ABCD strategy YAML, it is silently dropped because no other `*Config` has that field. The operator would have no feedback that pattern classes are NOT overrideable for non-ABCD strategies. |
| S-09 | LOW | `config/strategies/*.yaml` (13 of 15) | `# VIX regime dimensions: not yet constrained (match-any). Activate post-Sprint 28.` comment | — | No actual drops; comment indicates `operating_conditions:` is deliberately omitted. But this is a config-design debt signal: 13 strategies have no regime gating. |
| S-10 | LOW | `config/scanner.yaml:19-33` | `fmp_scanner.min_volume: 500000` | The `FMPScannerConfig` dataclass has `min_volume: int = 500_000` but it is annotated *"Reserved for future use (screener endpoint, Sprint 23+). Current FMP endpoints do not return volume data."* — so the value is accepted but has no effect downstream. | Cosmetic but confusing. Operator tunes min_volume to 1M; no filter changes. Recommend deleting the field until Sprint 23+ follows through. |

**Note on the mechanism:** All 9 Pydantic models audited use the Pydantic v2 default `model_config = ConfigDict(extra="ignore")` (i.e., they do NOT set `extra="forbid"` at class level) except: `ExitManagementConfig`, `TrailingStopConfig`, `ExitEscalationConfig`, `EscalationPhase` (all 4 in `core/config.py:281,231,263,250`) and `ExperimentConfig` (`intelligence/experiments/config.py:66`). That `extra="forbid"` on `ExperimentConfig` never actually fires because production never instantiates the model.

---

## Q3 — Default-Divergence Table

A "default divergence" is a key where the Pydantic default and the YAML-set value don't agree, AND there's ambiguity about which should win. Each row lists what actually happens.

| # | Field | Pydantic default | YAML value (system.yaml) | YAML value (system_live.yaml) | YAML value (standalone) | Which wins at runtime | Severity |
|---|---|---|---|---|---|---|---|
| D-01 | `quality_engine.weights.pattern_strength` | 0.30 | 0.30 | 0.30 | **0.375** (`quality_engine.yaml:18`) | **system.yaml's 0.30** wins (runtime reads `config.system.quality_engine`). The Sprint 32.9 recalibration in `quality_engine.yaml` is **dead**. | **CRITICAL** |
| D-02 | `quality_engine.weights.historical_match` | 0.15 | 0.15 | 0.15 | **0.0** (`quality_engine.yaml:21`) | system.yaml's 0.15 wins; historical_match still consuming 15% of grade weight despite being a constant 50 stub. **Grade compression DEF-142 is re-active**. | **CRITICAL** |
| D-03 | `quality_engine.thresholds.a_plus` | 90 | 90 | 90 | **72** (`quality_engine.yaml:28`) | system.yaml's 90 wins. Signals continue clustering in B grade (per DEF-142 original symptom). | **CRITICAL** |
| D-04 | `quality_engine.risk_tiers.a_plus` | `[0.02, 0.03]` | `[0.02, 0.03]` | `[0.002, 0.003]` (10x-reduced for paper) | `[0.002, 0.003]` matches system_live.yaml | system_live.yaml wins in live mode. quality_engine.yaml (paper-reduced) is dead and happens to match what system_live.yaml has. | MEDIUM (cosmetic alignment) |
| D-05 | `overflow.broker_capacity` | 30 | 30 | 30 | **50** (`overflow.yaml:7`) | system.yaml's 30 wins. Sprint 32.9 raised `risk_limits.yaml`'s `max_concurrent_positions: 50` but the overflow gate is still at 30 — **a 20-position window where brokers silently drop live signals to counterfactual tracking**. The standalone overflow.yaml has 50 (consistent with risk_limits.yaml), but it's dead. | HIGH |
| D-06 | `historical_query.cache_dir` | `"data/databento_cache"` | `"data/databento_cache"` | `"data/databento_cache"` | **`"data/databento_cache_consolidated"`** (`historical_query.yaml:3`) | system.yaml's non-consolidated path wins. The Sprint 31.85 consolidation script produced a consolidated cache, and the standalone historical_query.yaml correctly points there, but the operator has not yet repointed the section in system.yaml / system_live.yaml. **This is the "operator repoint pending" item in CLAUDE.md** — confirmed by this audit as still pending. | HIGH (but expected — operator is aware) |
| D-07 | `historical_query.persist_path` | `None` | not set (uses None) | not set (uses None) | `null` (`historical_query.yaml:6` — explicit null with comment "Set to data/historical_query.duckdb for persistent mode") | All three agree; in-memory mode. No divergence. | — |
| D-08 | `scanner.static_symbols` | `[]` | — | — | 8 symbols (AAPL, MSFT, NVDA, TSLA, AMD, AMZN, META, GOOGL) | scanner.yaml wins (used via `main.py:349`). No divergence — this is the hot path. | — |
| D-09 | `orchestrator.consecutive_loss_throttle` | 5 | — | — | **999** (`orchestrator.yaml:30` — paper-trading value with "restore to 5 before going live" comment) | orchestrator.yaml's 999 wins. Per-session expected. | — (paper-trading intentional) |
| D-10 | `risk_limits.account.daily_loss_limit_pct` | 0.03 | — | — | **1.0** (`risk_limits.yaml:3` — paper-trading value with "restore to 0.03 before live" comment) | risk_limits.yaml's 1.0 wins. | — (paper-trading intentional) |

---

## Q4 — Pydantic-Only Hidden Defaults (values live in code, no YAML representation)

These are values baked into Pydantic `Field(default=...)` that **never appear in any YAML**. Operators may not know they exist. Listed when the value has operational impact.

| # | Field | Model:line | Default | Operator-visible? | Impact |
|---|---|---|---|---|---|
| H-01 | `OrderManagerConfig.auto_shutdown_after_eod` | `core/config.py:821` | `True` | NOT in `order_manager.yaml` | If operator wants ARGUS to stay running after EOD (e.g. for overnight analysis), they must add the key themselves. This is the default behavior but not documented in the YAML. |
| H-02 | `OrderManagerConfig.auto_shutdown_delay_seconds` | `core/config.py:822` | 60 | NOT in `order_manager.yaml` | Same as H-01. |
| H-03 | `OrderManagerConfig.max_position_duration_minutes` | `core/config.py:814` | 120 | Partially (order_manager.yaml:20 has it) | order_manager.yaml duplicates the default. OK but brittle — if operator removes the key, behavior unchanged but apparent contract lost. |
| H-04 | `OrderManagerConfig.t1_position_pct` | `core/config.py:816` | 0.5 | Yes (order_manager.yaml:26) | OK. |
| H-05 | `AccountRiskConfig.min_position_risk_dollars` | `core/config.py:444` | 100.0 | Yes (risk_limits.yaml:12 — overridden to 10.0 for paper) | OK. |
| H-06 | `OrchestratorConfig.signal_cutoff_enabled` | `core/config.py:654` | True | Yes (orchestrator.yaml:91) | OK. |
| H-07 | `OrchestratorConfig.signal_cutoff_time` | `core/config.py:655` | "15:30" | Yes (orchestrator.yaml:92) | OK. |
| H-08 | `OrchestratorConfig.orb_family_mutual_exclusion` | `core/config.py:651` | True | Yes (orchestrator.yaml:83 — overridden to **false** for paper) | **Paper-trading override** — both ORB strategies fire on same symbol. Pre-live checklist item. |
| H-09 | `DatabentoConfig.enable_depth` | `core/config.py:513` | False | Yes (brokers.yaml:48) | L2 depth is gated; operator opt-in needed. OK. |
| H-10 | `ApiConfig.password_hash` | `core/config.py:300` | `""` | Yes — both system files set it (system.yaml blank, system_live.yaml has a bcrypt hash for "argus") | **HIGH-OPERATIONAL-IMPORTANCE hidden-ish default.** If operator boots with system.yaml (Alpaca incubator), password is empty and JWT login must be fixed before the UI works. |
| H-11 | `StrategyConfig.mode` | `core/config.py:753` | `"live"` | Yes (per-strategy) | Uses `str` not `StrategyMode` enum; mis-spellings (e.g. `"Shadow"` capitalized, or `"paper"`) would be silently accepted as mode. Since the shadow-routing branch in `_process_signal()` tests for the exact string `"shadow"`, any mis-spelling results in live routing. **MEDIUM risk.** |
| H-12 | `OverflowConfig.broker_capacity` | `intelligence/config.py:262` | 30 | Yes (system.yaml:177 = 30; system_live.yaml:177 = 30) | — but see D-05 above re: drift against `risk_limits.yaml`'s 50. |
| H-13 | `LearningLoopConfig.enabled` | `intelligence/learning/models.py:388` | True | **NOT populated** — no `learning_loop:` section in any system YAML. **Learning Loop is currently running with all Pydantic defaults** (30-day window, 30 min sample count, etc.) — not the values in `learning_loop.yaml`. | HIGH — see Q11 dead YAMLs. |
| H-14 | `CounterfactualConfig.retention_days` | `intelligence/config.py:245` | 90 | Yes (system.yaml:169, system_live.yaml:169) | OK. |
| H-15 | `RegimeIntelligenceConfig.breadth.min_symbols` | `core/config.py:112` | 50 | NOT populated (no `regime_intelligence:` in any system YAML). Standalone `regime.yaml` has it (50) but is dead. | Defaults luckily match — but the channel is broken. See Q11. |
| H-16 | `VixRegimeConfig.vol_regime_boundaries.calm_max_x` | `data/vix_config.py:78` | 1.0 | NOT populated — `system.yaml`'s `vix_regime:` section only sets `enabled: true`. All boundary values come from Pydantic defaults. Standalone `vix_regime.yaml` has the same values (1.0) but is dead. | Defaults match — works by coincidence. |

---

## Q5 — Config Consumer Mapping (one row per YAML)

"Phase" refers to `main.py` startup phases (1-12). "Consumer" is the `main.py` line or module path that first reads the file. "Pydantic validation" is whether the loader ultimately routes through a Pydantic model with field validation, or parses a raw dict.

| YAML | Phase | First consumer (file:line) | Pydantic validation | Cold-reload supported? |
|---|---|---|---|---|
| `system.yaml` / `system_live.yaml` | Phase 1 | `argus/core/config.py:1321` via CLI `--config` flag → `load_config()` | Yes — `ArgusConfig` validates all 5 sub-sections | No (constructor-only) |
| `risk_limits.yaml` | Phase 1 | Same `load_config()` | Yes | No |
| `brokers.yaml` | Phase 1 | Same | Yes | No |
| `orchestrator.yaml` | Phase 1 (and Phase 8.5 re-read for regime v2) | Same + `main.py:739` raw re-read | Yes | No |
| `notifications.yaml` | Phase 1 | Same | Yes | No |
| `order_manager.yaml` | Phase 10 | `main.py:1041` `load_yaml_file()` → `OrderManagerConfig(**raw)` | Yes | No |
| `scanner.yaml` | Phase 7 | `main.py:322` `load_yaml_file()` → raw dict → dispatch | **No Pydantic** — sub-dicts go to `@dataclass` configs (fmp/alpaca) or class with explicit `__init__` (databento) | No |
| `exit_management.yaml` | Phase 10 | `main.py:1056` → `ExitManagementConfig(**raw)` | Yes (`extra="forbid"`) | No |
| `quality_engine.yaml` | — (not read at runtime) | `ConfigProposalManager.__init__()` at `intelligence/learning/config_proposal_manager.py:52` — **for write-back only** | Yes on ConfigProposalManager startup parse; NOT used to configure the running `SetupQualityEngine` | N/A |
| `counterfactual.yaml` | — (not read) | nowhere | N/A | N/A |
| `overflow.yaml` | — (not read) | nowhere | N/A | N/A |
| `regime.yaml` | — (not read) | nowhere | N/A | N/A |
| `vix_regime.yaml` | — (not read) | nowhere | N/A | N/A |
| `learning_loop.yaml` | — (not read) | nowhere | N/A | N/A |
| `experiments.yaml` | Phase 9 | `main.py:846` `load_yaml_file()` → raw dict | **No Pydantic** — routed as raw dict to `VariantSpawner` and `PromotionEvaluator` | No |
| `historical_query.yaml` | — (not read) | nowhere | N/A | N/A |
| `backtest_universe.yaml` | — (not production) | `scripts/run_validation.py` only | `yaml.safe_load`, raw dict | — |
| `strategies/*.yaml` (15) | Phase 8 (per-strategy) | `main.py:535-712` via per-strategy `load_*_config()` → respective Pydantic `*Config` | Yes | No |
| `strategies/*.yaml` (15, `exit_management:` block re-scan) | Phase 10 | `main.py:1063-1068` raw dict extract | **No** — raw dict passed to OrderManager as per-strategy override | No |
| `universe_filters/*.yaml` (11) | — (not production) | `scripts/run_experiment.py:196`, `scripts/resolve_*.py` | Yes (`UniverseFilterConfig` in `intelligence/experiments/config.py`) | — |

---

## Q6 — Sprint 32.9 Consistency Checklist

Sprint 32.9 was recent, touched `quality_engine.yaml`, `experiments.yaml`, `orchestrator.yaml`, `order_manager.yaml`, `risk_limits.yaml`, `overflow.yaml`, `config/strategies/abcd.yaml`, and `config/strategies/flat_top_breakout.yaml`. Confirm each landed.

| Sprint 32.9 change | Target YAML | Target section | Landed? | Notes |
|---|---|---|---|---|
| Quality weight recalibration (pattern_strength → 0.375, historical_match → 0.0, volume_profile → 0.275) | `quality_engine.yaml` | `weights:` | YES in `quality_engine.yaml` | **BUT runtime uses `config/system_live.yaml` `quality_engine.weights:` which still has pre-Sprint values** (0.30 / 0.15 / 0.20). Sprint 32.9's weights are **not live** at runtime. See Finding D-01, D-02, D-03. |
| Quality threshold recalibration (a_plus: 72, etc., for actual 35–77 score range) | `quality_engine.yaml` | `thresholds:` | YES in `quality_engine.yaml` | **Same runtime-drift issue.** thresholds 90/80/70/60/50/40/30 remain in system.yaml/system_live.yaml. See D-03. |
| Experiments enabled | `experiments.yaml` | `enabled:` | YES (`experiments.yaml:3` = true) | OK. Drives `main.py:847` branch. |
| ABCD demoted to shadow | `strategies/abcd.yaml` | `mode:` | YES (line 5 = `mode: shadow`) | OK. |
| Flat-Top Breakout demoted to shadow | `strategies/flat_top_breakout.yaml` | `mode:` | YES (line 5 = `mode: shadow`) | OK. |
| Pre-EOD signal cutoff added | `orchestrator.yaml` | `signal_cutoff_enabled`, `signal_cutoff_time` | YES (lines 91-92) | OK. |
| `max_concurrent_positions: 50` | `risk_limits.yaml` | `account.max_concurrent_positions` | YES (line 6) | OK but **drifts against `overflow.yaml:7` (50)** vs `system.yaml / system_live.yaml:177` (30). See D-05. |
| EOD flatten sync verification | `order_manager.yaml` | `eod_flatten_timeout_seconds`, `eod_flatten_retry_rejected` | YES (lines 42, 44) | OK. |
| Margin circuit breaker | `order_manager.yaml` | `margin_rejection_threshold`, `margin_circuit_reset_positions` | YES (lines 48, 50) | OK. |

**Verdict:** 8 of 10 Sprint 32.9 config changes landed at runtime. **2 items (weights + thresholds) are silently dead due to the standalone-YAML drift pattern.** This is the **single most consequential finding in this session.**

---

## Q7 — Sprint 31A.5 + 31.85 Consistency Checklist

Sprint 31A.5 introduced `HistoricalQueryConfig` + `historical_query.yaml`. Sprint 31.85 added the consolidation script.

| Sprint change | Target YAML | Landed at runtime? | Notes |
|---|---|---|---|
| `HistoricalQueryConfig` Pydantic model | `data/historical_query_config.py` | YES — wired to `SystemConfig.historical_query` at `core/config.py:423` | OK. |
| `historical_query.yaml` file | `config/historical_query.yaml` | **NO — standalone file, not loaded at runtime** | `config.system.historical_query` populated from `system.yaml` / `system_live.yaml` `historical_query:` block instead. See Q11. |
| Config-gated in `api/server.py` | `argus/api/server.py:474` | YES | OK. |
| Consolidation script | `scripts/consolidate_parquet_cache.py` | YES (script) | N/A — not a runtime config. |
| **Cache repoint from `data/databento_cache` → `data/databento_cache_consolidated`** | `config/system.yaml:194` / `config/system_live.yaml:203` | **NOT DONE** (both point at `data/databento_cache`). The **standalone `historical_query.yaml:3` points at the consolidated cache** but is dead. | **This matches CLAUDE.md's "operator repoint pending" status** — confirmed unchanged as of audit time. |
| `duckdb>=1.0,<2` dependency | `pyproject.toml` | YES (verified in P1-I) | OK. |

**Verdict:** Cache repoint is the operator-owned step and is intentionally still pending. No code action needed. But the standalone `historical_query.yaml` creates confusion — an operator could edit it thinking they are repointing the cache and see no effect. Removing or renaming the file would prevent future operator error.

---

## Q8 — Sprint 27.9 VIX Config Drift Check

Sprint 27.9's closeout explicitly documented the pattern: *"config/vix_regime.yaml was a standalone file never loaded by load_config(). Added vix_regime: enabled: true to both system.yaml and system_live.yaml."* Confirm status.

| What `vix_regime.yaml` declares | What `system.yaml` / `system_live.yaml` declare | Actual runtime value | Drift? |
|---|---|---|---|
| `enabled: true` | `enabled: true` | True | No |
| `yahoo_symbol_vix: "^VIX"` | not set | "^VIX" (Pydantic default) | Coincidentally matches |
| `vol_short_window: 5` | not set | 5 (Pydantic default) | Coincidentally matches |
| `vol_regime_boundaries.calm_max_x: 1.0` | not set | 1.0 (Pydantic default) | Coincidentally matches |
| `vol_regime_boundaries.crisis_min_y: 0.85` | not set | 0.85 (Pydantic default) | Coincidentally matches |
| `term_structure_boundaries.contango_threshold: 1.0` | not set | 1.0 (Pydantic default) | Coincidentally matches |
| `vrp_boundaries.normal_max: 50.0` | not set | 50.0 (Pydantic default) | Coincidentally matches |

**Verdict:** No actual runtime drift today because Pydantic defaults happen to match vix_regime.yaml verbatim. **But the moment an operator edits a boundary in vix_regime.yaml, it will silently not apply.** This is a latent trap.

---

## Q9 — Orchestrator / Risk_Limits / Order_Manager Cross-Check

Highest-stakes trio. Verify per-field.

| Field | orchestrator.yaml | risk_limits.yaml | order_manager.yaml | system.yaml / system_live.yaml | Pydantic default | Effective value | Notes |
|---|---|---|---|---|---|---|---|
| Daily loss limit | — | `account.daily_loss_limit_pct: 1.0` (paper) | — | — | 0.03 | 1.0 | Paper override, intentional |
| Max concurrent positions (account) | — | `account.max_concurrent_positions: 50` | — | — | 10 | 50 | Sprint 32.9 change, effective |
| Overflow broker capacity | — | — | — | `overflow.broker_capacity: 30` | 30 | **30** | `overflow.yaml` standalone says 50 but is dead. See D-05 — this is a **20-position gap** between account-level limit (50) and overflow gate (30). |
| Signal cutoff | `signal_cutoff_enabled: true`, `signal_cutoff_time: "15:30"` | — | — | — | True, "15:30" | effective | OK |
| Consecutive loss throttle | `consecutive_loss_throttle: 999` | — | — | — | 5 | 999 | Paper override |
| Suspension Sharpe | `suspension_sharpe_threshold: -999.0` | — | — | — | 0.0 | -999 | Paper override |
| Throttler suspend enabled | `throttler_suspend_enabled: false` | — | — | — | True | False | Paper override |
| ORB family mutual exclusion | `orb_family_mutual_exclusion: false` | — | — | — | True | False | Paper override |
| EOD flatten time | — | — | `eod_flatten_time: "15:50"` | — | "15:50" | "15:50" | OK |
| EOD flatten fill-verification | — | — | `eod_flatten_timeout_seconds: 30`, `eod_flatten_retry_rejected: true` | — | 30, True | effective | Sprint 32.9 |
| Margin circuit breaker | — | — | `margin_rejection_threshold: 10`, `margin_circuit_reset_positions: 20` | — | 10, 20 | effective | Sprint 32.9 |
| Duplicate stock policy | — | `cross_strategy.duplicate_stock_policy: "priority_by_win_rate"` | — | — | `ALLOW_ALL` | `priority_by_win_rate` | **Note:** DEC-121/160 adopted `ALLOW_ALL` but `risk_limits.yaml` says `priority_by_win_rate`. **Possible regression.** Verify intent. |

### D-11 (HIGH) DuplicateStockPolicy runtime mismatch vs DEC-121/160

`risk_limits.yaml:17` sets `duplicate_stock_policy: "priority_by_win_rate"`. The project's recorded decision is `ALLOW_ALL` (CLAUDE.md line 189, DEC-121/160, `.claude/rules/trading-strategies.md`). The `CrossStrategyRiskConfig` Pydantic default is `ALLOW_ALL` (`core/config.py:452`). Runtime applies the YAML value (`priority_by_win_rate`). **This is a genuine policy inversion** — the default is the documented decision and the YAML overrides it. Needs either a YAML correction or a documented reason.

---

## Q10 — Paper-Trading Overrides (reframed: where do they live?)

The plan asked about `system_paper.yaml`. That file does not exist. Paper-trading overrides actually live **scattered across 6 files**:

| File | Paper-override key | Value | Live-trading value |
|---|---|---|---|
| `risk_limits.yaml:3-4` | `account.daily_loss_limit_pct`, `weekly_loss_limit_pct` | 1.0, 1.0 | 0.03, 0.05 |
| `risk_limits.yaml:12` | `account.min_position_risk_dollars` | 10.0 | 100.0 |
| `orchestrator.yaml:30` | `consecutive_loss_throttle` | 999 | 5 |
| `orchestrator.yaml:35` | `suspension_sharpe_threshold` | -999.0 | 0.0 |
| `orchestrator.yaml:40` | `suspension_drawdown_pct` | 0.50 | 0.15 |
| `orchestrator.yaml:46` | `throttler_suspend_enabled` | false | true |
| `orchestrator.yaml:83` | `orb_family_mutual_exclusion` | false | true |
| `system_live.yaml:138-144` (7 tiers) | `quality_engine.risk_tiers.*` | 10x-reduced | as in `system.yaml` |

**Observation:** The comment pattern "# PAPER TRADING: … Restore to X before going live" is used in 6 places but not consistently formatted. A single file (`config/system_paper.yaml`) or a documented checklist (`docs/pre-live-transition-checklist.md` — which DOES exist) is the right pattern. The current state requires an operator to know all 6 files to safely flip to live.

---

## Q11 — Dead YAMLs (operator-editable files with no runtime effect)

| # | File | Evidence of deadness | What operator must edit instead |
|---|---|---|---|
| DEAD-01 | `config/regime.yaml` | `grep -r "regime\.yaml\|regime_yaml" argus/` returns 0 production matches. `config.system.regime_intelligence` populated via `Field(default_factory=RegimeIntelligenceConfig)` because no `regime_intelligence:` key exists in any system YAML. Only `tests/core/test_regime.py:1220` loads it — purely for "test that the Pydantic model accepts this YAML" validation. | Add a `regime_intelligence:` section to `system.yaml` / `system_live.yaml` and mirror the values. |
| DEAD-02 | `config/vix_regime.yaml` | `grep -r "vix_regime\.yaml" argus/` returns only a docstring comment. System YAMLs have `vix_regime:` but only set `enabled: true`. All boundaries use Pydantic defaults. Sprint 27.9 closeout explicitly documents this discovery. | Expand `vix_regime:` sections in system YAMLs with all boundary values. |
| DEAD-03 | `config/counterfactual.yaml` | `grep -r "counterfactual\.yaml" argus/` returns 0. `config.system.counterfactual` populated from system.yaml's `counterfactual:` section. | N/A — system.yaml already has all fields. Just delete `counterfactual.yaml`. |
| DEAD-04 | `config/overflow.yaml` | `grep -r "overflow\.yaml" argus/` returns 0. Same pattern as DEAD-03. | N/A — already in system YAMLs. Delete overflow.yaml. |
| DEAD-05 | `config/learning_loop.yaml` | `grep -r "learning_loop\.yaml" argus/` returns 0. Neither `system.yaml` nor `system_live.yaml` has a `learning_loop:` section, so `SystemConfig.learning_loop` is 100% Pydantic defaults. | Add `learning_loop:` section to system YAMLs, OR add a runtime loader for `learning_loop.yaml`. |
| DEAD-06 | `config/historical_query.yaml` | `grep -r "historical_query\.yaml" argus/` returns 0. System YAMLs have their own `historical_query:` sections. | Either repoint cache_dir in system.yaml or delete historical_query.yaml. |
| DEAD-07 (partial) | `config/quality_engine.yaml` | `load_quality_engine_config()` exists but explicit docstring says "NOT used at runtime". `ConfigProposalManager` reads/writes it at startup for proposal validation, but the running `SetupQualityEngine` is instantiated from `config.system.quality_engine` = system.yaml. | For runtime: update system.yaml/system_live.yaml `quality_engine:` sections to match Sprint 32.9 recalibration. For proposal write-back: the file stays live. |
| DEAD-ADJACENT-1 | `config/backtest_universe.yaml` | Only consumed by `scripts/run_validation.py`. Not a runtime file. | — (scripts/ files are out of scope for this audit; flagging for completeness). |
| DEAD-ADJACENT-2 | `config/universe_filters/*.yaml` (11 files) | Only consumed by `scripts/run_experiment.py` and `scripts/resolve_*.py`. Not runtime. | — (scripts-only is expected for this layer). |

**Aggregate:** 6 truly-dead YAMLs + 1 partially-dead (`quality_engine.yaml`) + 12 scripts-only (`backtest_universe.yaml` + 11 `universe_filters/*.yaml`). Of the 44 YAMLs, **6 files (14%) are operator-editable-but-nothing-consumes-them.**

---

## Q12 — `bull_flag_trend.yaml` Wiring Verification

The prompt asked specifically to verify: "the project has explicitly been burned twice by standalone YAMLs that silently do nothing."

| Question | Answer |
|---|---|
| Does `config/universe_filters/bull_flag_trend.yaml` exist? | Yes (8 lines). |
| Is it loaded in production (`argus/`)? | **No.** `grep -rn "bull_flag_trend" argus/` returns 0. |
| Is it loaded in scripts? | Yes — `scripts/resolve_sweep_symbols.py:153` discovers all `config/universe_filters/*.yaml` via glob. |
| Is it a strategy YAML? | No — it's a universe filter for the existing `bull_flag` strategy. |
| What does it do? | Intended to A/B-test a trend-following universe ($20–300, 300K volume) vs the momentum universe ($10–500, 500K volume) for bull_flag backtests. |
| Any drift risk? | Low. This file is correctly placed for its actual purpose (sweep-tooling only). |

**Verdict:** `bull_flag_trend.yaml` is **not** a case of the "standalone YAML that silently does nothing" pattern — it's a script-only artifact and works as intended.

---

## Positive Observations

- **`ExitManagementConfig` uses `extra="forbid"`.** Only Pydantic model in the entire 9-model universe to do so. This is the right default for any config model that operators hand-edit. The exit management YAML will loudly fail on typos. Pattern should be replicated for `OrderManagerConfig`, `QualityEngineConfig`, `RegimeIntelligenceConfig`, and all 15 `StrategyConfig` subclasses.
- **Per-strategy exit_management override plumbing** at `main.py:1063-1068` is clean: it re-scans the strategies directory for a specific key and passes it as a separate raw dict to `OrderManager`. This pattern is preferable to hiding the override inside `StrategyConfig` where the base model's `extra="ignore"` would drop it.
- **`QualityEngineConfig.validate_weight_sum()` model validator** (`intelligence/config.py:132`) checks weights sum to 1.0 ± 0.001. This catches typos in the one place that matters. Pattern should be replicated for any YAML with multi-field invariants.
- **`QualityThresholdsConfig.validate_descending()` and `QualityRiskTiersConfig.validate_tiers()`** provide rich structural validation. Again, pattern should spread.
- **Paper-trading override comments** (`# PAPER TRADING: … Restore to X before going live`) exist in 6+ places. Not automated, not enforced, but a useful hygiene anchor. A `pre-live-transition-checklist.md` cross-reference would make these audit-able.
- **The `mode: live/shadow` field on StrategyConfig** (Sprint 27.7) provides the shadow-routing escape valve without requiring variant infrastructure. It's working as intended for ABCD and Flat-Top Breakout demotions (Sprint 32.9).
- **Strategy YAML factoring** — 15 strategies each with their own YAML, loaded via a dedicated `load_*_config()` function that maps to a strategy-specific Pydantic subclass. Verbose but surgical — no cross-strategy coupling. Good.

---

## Statistics

- **YAMLs examined:** 44 (18 root + 15 strategies + 11 universe_filters)
- **Pydantic modules examined:** 9 (`core/config.py` 1,751L, `analytics/config.py` 29L, `backtest/config.py` 218L, `data/historical_query_config.py` 47L, `data/vix_config.py` 201L, `intelligence/config.py` 290L, `intelligence/experiments/config.py` 81L, `ai/config.py` 62L, `intelligence/learning/models.py` L:382-402)
- **Pydantic model sub-classes and sub-configs audited:** ~60 (counting all sub-models like `BreadthConfig`, `VolRegimeBoundaries`, `QualityWeightsConfig`, each `StrategyConfig` subclass, etc.)
- **Total findings:** 23
  - CRITICAL: 5 (S-01, S-02, D-01, D-02, D-03 — the quality-engine recalibration drift is one root cause for D-01/02/03)
  - HIGH: 3 (D-05, D-06, D-11)
  - MEDIUM: 7 (S-03, S-04, S-05, S-06, S-08, S-10, H-10, H-11)
  - LOW: 2 (S-09, H-01/H-02/H-03)
  - DEAD-YAML findings: 6 primary (DEAD-01..06) + 1 partial (DEAD-07)
- **Safety distribution:**
  - `safe-during-trading`: DEAD-03, DEAD-04, DEAD-06 (file deletions, no loader touches them); S-09, S-10 (cosmetic); H-11 (add enum type, weekend-only actually — reclassify); 13 of the 15 `min_sharpe → min_sharpe_ratio` fixes (YAML-only, affects benchmark display only)
  - `weekend-only`: D-01 / D-02 / D-03 (touches Pydantic loading path or system.yaml quality_engine section → affects signal grading → position sizing), D-05 (overflow broker_capacity 30 → 50 alignment), D-06 (cache repoint — operator-owned), D-11 (DuplicateStockPolicy — touches Risk Manager decisions), S-02 (variant param validation — affects strategy signal generation), DEAD-01/02/05 (requires adding new section to system YAMLs that will be loaded by SystemConfig — safe technically but touches system boot)
  - `read-only-no-fix-needed`: Positive Observations, sprint-log entries
  - `deferred-to-defs`: S-01 (block of 12 strategy YAMLs — should become a batched cleanup DEF)
- **Estimated Phase 3 fix effort:** 3 sessions
  - **Session 1 (weekend-only, 1 hour):** D-01/02/03 — sync `quality_engine.yaml` values into `system.yaml` and `system_live.yaml` `quality_engine:` sections. Decide whether to delete `quality_engine.yaml` or keep for ConfigProposalManager. Test: signals get graded with new weights.
  - **Session 2 (weekend-only, 1.5 hours):** D-05, D-06, D-11, DEAD-01/02/05 — align `overflow.broker_capacity`, repoint `historical_query.cache_dir`, verify DuplicateStockPolicy intent, add `learning_loop:` / `regime_intelligence:` / full `vix_regime:` sections to system.yaml. Delete DEAD-03/04/06.
  - **Session 3 (safe-during-trading, 30 min):** S-01 (rename `min_sharpe → min_sharpe_ratio` in 12 strategy YAMLs), S-03 (trim unused `backtest_summary` fields OR extend `BacktestSummaryConfig`), S-06 (delete dead `ScannerConfig` Pydantic class and `load_scanner_config()` function + test), S-08 (decide whether `pattern_class` is meaningful on non-ABCD patterns; if not, remove `pattern_class: "ABCDPattern"` comment fixes).

**Context State:** GREEN — all 8 Pydantic modules and all 44 YAMLs read in full during this session, no compaction artifacts observed in outputs.

---

## Notes on the prompt's pre-gathered context

The prompt's inventory said "42 YAMLs". **The actual count is 44.** Specifically:
- Root level: 18 (not 17) — the prompt missed that root has 18 files.
- `strategies/`: 15 (not 13) — the prompt missed `afternoon_momentum.yaml` and `red_to_green.yaml`.
- `universe_filters/`: 11 — the prompt count was correct here.

The Pydantic-module inventory in the prompt was accurate for file count, though the "9-module" universe in this report includes `argus/intelligence/learning/models.py` (where `LearningLoopConfig` actually lives) which the prompt listed as the 8th module's separate module. Minor bookkeeping difference.

The prompt's prediction that "`config/system_paper.yaml`, `config/system_backtest.yaml`, `config/ai.yaml`, `config/ibkr.yaml`, `config/intelligence.yaml` — NOT found" is confirmed. Paper overrides live inline; AI/IBKR/intelligence live as sub-sections of `system.yaml` / `system_live.yaml`.

---

## FIX-01 Resolution (2026-04-21)

- **D-01** (`quality_engine.weights.pattern_strength`): **RESOLVED FIX-01-catalyst-db-quality-pipeline** via **Option B** (DEC-384). `config/quality_engine.yaml` now wins at runtime via `load_config()` overlay merge.
- **D-02** (`quality_engine.weights.historical_match`): **RESOLVED FIX-01-catalyst-db-quality-pipeline**. Overlay merge + stub hardened to `return 0.0` so the dimension is a strict no-op. Grade compression from this source cannot recur.
- **D-03** (`quality_engine.thresholds.a_plus`): **RESOLVED FIX-01-catalyst-db-quality-pipeline**. Runtime now reads threshold 72 from `quality_engine.yaml`.
- **DEAD05** (`quality_engine.yaml` dead): **RESOLVED FIX-01-catalyst-db-quality-pipeline** — file is now authoritative under Option B, not deleted. The "dead YAML" class of finding is the motivation behind DEC-384's extensible `_STANDALONE_SYSTEM_OVERLAYS` registry.

The companion `overflow.yaml` / `system_live.yaml` divergence (C3 / related D-0x rows in this report) is **RESOLVED FIX-02-config-drift-critical** — see FIX-02 Resolution section below.

## FIX-02 Resolution (2026-04-21)

- **D-05** (`overflow.broker_capacity` 30 vs 50 drift): **RESOLVED FIX-02-config-drift-critical** via the DEC-384 registry extension. `config/overflow.yaml` is flattened to bare-field shape and registered as the second `_STANDALONE_SYSTEM_OVERLAYS` entry; `config/system.yaml` and `config/system_live.yaml` no longer carry an `overflow:` block. Runtime now reads `broker_capacity: 50` from `overflow.yaml`, matching `risk_limits.yaml`'s `max_concurrent_positions: 50`. The 20-position drift window is closed.
- **DEAD-04** (`config/overflow.yaml` dead): **RESOLVED FIX-02-config-drift-critical** — file is now authoritative under Option B, not deleted. Same motivation as DEAD-05: the "dead YAML" class of finding is what `_STANDALONE_SYSTEM_OVERLAYS` exists to cure.

Stage 1 deferred pickup (FIX-01 review INFO): `load_config()` now emits a WARNING when a registered standalone overlay parses to a non-dict value (e.g., a YAML list); previously a silent skip. Regression test added alongside the FIX-02 guards in `tests/test_fix01_load_config_merge.py`.

## FIX-16 Resolution (2026-04-22)

The remaining 19 H2-* findings (2 CRITICAL + 14 MEDIUM + 3 LOW) addressed in a single Stage 3 session.

### Critical findings

- **S-01** (`benchmarks.min_sharpe` silently dropped in 12/15 strategy YAMLs): **RESOLVED FIX-16-config-consistency** — renamed to `min_sharpe_ratio` in 12 YAMLs (bull_flag, vwap_bounce, narrow_range_breakout, dip_and_rip, micro_pullback, afternoon_momentum, abcd, hod_break, flat_top_breakout, premarket_high_break, vwap_reclaim, gap_and_go); orb_breakout / orb_scalp / red_to_green were already correct. Parametrized regression test in `tests/core/test_config.py::TestStrategyBenchmarkMinSharpeRatioWires` (15 test cases + 1 grep-guard).
- **S-02** (variant params not validated against target pattern): **RESOLVED FIX-16-config-consistency** — `VariantSpawner._apply_variant_params` now explicitly validates each `params.*` key against `type(base_config).model_fields` (strategy configs do not use `extra="forbid"`, so unknown keys would otherwise be silently dropped). Both unknown keys and out-of-range values raise — caller logs ERROR and skips the variant rather than the prior silent collapse onto base defaults. Regression tests in `tests/intelligence/experiments/test_spawner.py::test_unknown_param_key_typo_is_rejected_not_silently_dropped` (typo case) + `::test_existing_experiments_yaml_has_no_typos_in_variant_params` (fleet sanity check — confirms zero typos exist in the live 22-variant fleet at this commit).
- **S-04** (variant list-element shape not validated): **RESOLVED FIX-16-config-consistency** — same VariantSpawner pass now rejects non-dict variant entries with a clear ERROR log instead of a deep AttributeError. Regression test `::test_non_dict_variant_entry_is_rejected`.

### Medium findings

- **S-03** (`backtest_summary` 7 extras silently dropped on all 15 YAMLs): **RESOLVED FIX-16-config-consistency** — `BacktestSummaryConfig` extended with `data_source`, `universe_size`, `universe_note`, `data_range`, `avg_win_rate`, `avg_profit_factor`, `prior_baseline` (all `Optional`). Documentary fields now survive the load.
- **S-06** (`ScannerConfig` Pydantic shim only modelled 2 of 5 keys; 3 nested provider blocks silently dropped): **RESOLVED FIX-16-config-consistency** — `ScannerConfig` class + `load_scanner_config()` deleted; production code in `main.py` already reads `scanner.yaml` directly and builds provider-specific configs. `tests/core/test_config.py::TestScannerConfig` removed.
- **S-08** (`pattern_class` field only on ABCDConfig — would be silently dropped on other patterns): **RESOLVED FIX-16-config-consistency** — `pattern_class` field removed from `ABCDConfig`. Pattern resolution now flows uniformly through `factory._resolve_pattern_name`'s class-name inference (`ABCDConfig` → `ABCDPattern`) for all 10 patterns.
- **H-10** (`api.password_hash` empty + `api.enabled=true` would silently break JWT login): **RESOLVED FIX-16-config-consistency** — `ApiConfig.validate_password_hash_set()` is called by `load_config()` and raises with a clear remediation message. Runtime check (not a `model_validator`) so `ApiConfig()` / `SystemConfig()` remain usable in tests. Dev hash added to `system.yaml` (mirrors `system_live.yaml`'s "argus" dev password) so the Alpaca-incubator profile boots cleanly. Regression tests in `tests/core/test_config.py::TestApiPasswordHashLoadTimeCheck` (6 cases).
- **H-11** (`StrategyConfig.mode` typed as `str` not `StrategyMode` — misspellings silently routed live): **RESOLVED-VERIFIED FIX-16-config-consistency** — already resolved by FIX-19 (`StrategyConfig.mode: StrategyMode = StrategyMode.LIVE` at `argus/core/config.py:777`). Pydantic validator now rejects `"Shadow"` and other misspellings. Verified via direct construction.
- **H-13 + DEAD-01** (`learning_loop.yaml` not wired into `load_config()` — operator tuning ignored): **RESOLVED FIX-16-config-consistency** — registered as `("learning_loop", "learning_loop.yaml")` in `_STANDALONE_SYSTEM_OVERLAYS`. File already had bare-field shape (no top-level wrapper).
- **H-15 + DEAD-02** (`regime.yaml` not wired — defaults luckily match standalone but the channel was broken): **RESOLVED FIX-16-config-consistency** — registered as `("regime_intelligence", "regime.yaml")` in `_STANDALONE_SYSTEM_OVERLAYS`. File already bare-field.
- **DEAD-03** (`overflow.yaml`): **RESOLVED-VERIFIED FIX-16-config-consistency** — already resolved by FIX-02 (see prior section).
- **DEAD-04** (`counterfactual.yaml`): **RESOLVED FIX-16-config-consistency** — file deleted. Values already authoritative in `system.yaml` / `system_live.yaml`'s `counterfactual:` block. Test fixture in `tests/intelligence/test_counterfactual_store.py::test_config_yaml_keys_match_pydantic_fields` redirected to read `system_live.yaml`.
- **DEAD-06** (`vix_regime.yaml`): **RESOLVED FIX-16-config-consistency** — registered as `("vix_regime", "vix_regime.yaml")` in `_STANDALONE_SYSTEM_OVERLAYS`. The 2-line `vix_regime: enabled: true` blocks were removed from `system.yaml` and `system_live.yaml` to avoid divergence with the standalone file (now authoritative).
- **D-06** (`cache_dir` divergence: `system.yaml` non-consolidated vs `historical_query.yaml` consolidated): **RESOLVED FIX-16-config-consistency** — `historical_query.yaml` flattened to bare-field shape and registered as `("historical_query", "historical_query.yaml")` in `_STANDALONE_SYSTEM_OVERLAYS`. `historical_query:` blocks removed from `system.yaml` and `system_live.yaml`. `cache_dir` kept at `data/databento_cache` (no runtime behavior change) — operator can repoint to `data/databento_cache_consolidated` post-Sprint-31.85 activation by editing the standalone file.

### Low findings

- **DEF-109** (V1 trailing stop fields dead post-Sprint 28.5): **RESOLVED FIX-16-config-consistency** — `enable_trailing_stop` and `trailing_stop_atr_multiplier` removed from `OrderManagerConfig`; AMD-10 deprecation-warning block removed from `main.py`; legacy fields removed from `config/order_manager.yaml`; `TestDeprecatedConfigWarning` test class removed (3 tests). Trailing stops live entirely in `config/exit_management.yaml` via `ExitManagementConfig` (Sprint 28.5).
- **S-09** (13 strategies have stale "Activate post-Sprint 28" TODO): **RESOLVED FIX-16-config-consistency** — comment replaced across 7 strategy YAMLs (the ones that carried it) with current-state guidance: VIX dimensions intentionally unconstrained, `allowed_regimes:` is the primary regime gate (FIX-19), per-strategy `operating_conditions:` block remains optional for VIX-tier filtering when needed.
- **S-10** (`fmp_scanner.min_volume` field always ignored): **RESOLVED FIX-16-config-consistency** — `min_volume` field removed from `FMPScannerConfig` dataclass and from `config/scanner.yaml`. Operator-tunable surface no longer suggests a volume filter that does not exist. Restore when FMP volume-aware endpoint integrated.

### New DEF / DEC items
None. All findings resolved in-scope. The DEC-384 `_STANDALONE_SYSTEM_OVERLAYS` registry was extended (4 new entries: learning_loop, regime_intelligence, vix_regime, historical_query) following the FIX-02 precedent — no new DEC needed for the extension.

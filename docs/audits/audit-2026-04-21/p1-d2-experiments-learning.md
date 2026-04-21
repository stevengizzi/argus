# Audit: Experiments + Learning Loop
**Session:** P1-D2
**Date:** 2026-04-21
**Scope:** `argus/intelligence/experiments/` (pipeline, runner, spawner, promotion, store) and `argus/intelligence/learning/` (service, config proposal manager, analyzers, outcome collector, store). Sprints 28, 31.5, 31.75, 31A.5, 31A.75, 32, 32.5 are the heavy contributors here.
**Files examined:** 6 deep / 8 skimmed

Deep-read (full file):
- `argus/intelligence/experiments/runner.py` (917L)
- `argus/intelligence/experiments/spawner.py` (336L)
- `argus/intelligence/experiments/promotion.py` (492L)
- `argus/intelligence/experiments/store.py` (838L) — DEF-151 fix site
- `argus/intelligence/learning/learning_service.py` (571L)
- `argus/intelligence/learning/config_proposal_manager.py` (468L)

Skimmed (interface + dead-code scan):
- `argus/intelligence/experiments/config.py` (82L)
- `argus/intelligence/experiments/models.py` (118L)
- `argus/intelligence/experiments/__init__.py` (22L)
- `argus/intelligence/learning/weight_analyzer.py` (496L)
- `argus/intelligence/learning/threshold_analyzer.py` (154L)
- `argus/intelligence/learning/correlation_analyzer.py` (227L)
- `argus/intelligence/learning/outcome_collector.py` (383L)
- `argus/intelligence/learning/learning_store.py` (584L)
- `argus/intelligence/learning/models.py` (486L)

Cross-referenced: `argus/strategies/patterns/factory.py` (P1-B), `argus/intelligence/counterfactual_store.py` (P1-D1 scope), `argus/main.py` phases 9 & session-end (P1-A1), `argus/execution/order_manager.py` exit-override path (P1-C1), `config/experiments.yaml`.

---

## Q1. Shadow Variant Fleet Validation (22 variants)

Confirmed against [config/experiments.yaml](config/experiments.yaml):

| Pattern | Variants | All `mode: shadow`? | ≤ `max_variants_per_pattern` (8)? |
|---------|---------:|:---:|:---:|
| dip_and_rip | 2 | yes | yes |
| micro_pullback | 2 | yes | yes |
| hod_break | 3 | yes | yes |
| gap_and_go | 3 | yes | yes |
| premarket_high_break | 2 | yes | yes |
| vwap_bounce | 2 | yes | yes |
| narrow_range_breakout | 2 | yes | yes |
| abcd | 2 | yes | yes |
| bull_flag | 2 | yes | yes |
| flat_top_breakout | 2 | yes | yes |
| **Total** | **22** | | |

All 10 PatternModule patterns present. `enabled: true`, `auto_promote: false`, `max_variants_per_pattern: 8`, `max_workers: 4`, `exit_sweep_params: null`. Parameter sanity-check against PatternParam ranges (sampled dip_and_rip, hod_break, micro_pullback): all declared variant values sit inside their respective `[min_value, max_value]` ranges. No variant uses `exit_overrides:` (relevant to M-01 below).

---

## Q2. Pattern Factory Integration (`_PATTERN_TO_STRATEGY_TYPE`)

[runner.py:54-70](argus/intelligence/experiments/runner.py#L54-L70) maps all **10** PatternModule patterns to `StrategyType` entries (bull_flag, flat_top_breakout, dip_and_rip, hod_break, abcd, gap_and_go, premarket_high_break, micro_pullback, vwap_bounce, narrow_range_breakout). DEF-134 resolution confirmed; Sprint 29/31A additions (micro_pullback/vwap_bounce/narrow_range_breakout) are wired. No dead pattern entries. The sequential path ([L581-L590](argus/execution/runner.py#L581-L590)) passes `config_overrides=detection_params` to `BacktestEngineConfig` (factory wiring happens inside `BacktestEngine._create_*_strategy` — see P1-C1/P1-B).

---

## Q3. DEF-151 Regression Guard

Grep for `json.dumps` across `argus/intelligence/` returned **10 call sites**. Audited each:

| File:Line | Payload type | `default=str`? | Safe? |
|-----------|--------------|:---:|:---:|
| experiments/store.py:191 | `record.parameters` (pattern dict, primitives only) | no | ✅ |
| experiments/store.py:193 | `record.backtest_result` (contains `date` via `MultiObjectiveResult.to_dict()`) | **yes** — DEF-151 fix | ✅ |
| experiments/store.py:395 | `variant.parameters` | no | ✅ |
| experiments/store.py:399 | `variant.exit_overrides` (dot-paths → floats) | no | ✅ |
| experiments/runner.py:891 | `_compute_fingerprint` canonical dict | yes (defensive) | ✅ |
| learning/learning_store.py:124 | `report.to_dict()` (pre-converted via `_convert_datetimes`) | no | ✅ (fragile — see L-01) |
| intelligence/storage.py:526 | briefings (out of scope) | — | — |
| intelligence/quality_engine.py:222 | `signal.signal_context` (primitives) | no | ✅ |
| intelligence/counterfactual_store.py:168-171 | `regime_vector_snapshot`, `signal_metadata` | yes | ✅ |

**Verdict: CLEAR.** No uncovered dataclass-containing-dates serialization. One latent risk catalogued below (L-01) around `_convert_datetimes` handling `datetime` only, not `date`.

---

## Q4. Parallel Sweep Wiring (Sprint 31.5)

- [runner.py:73-159](argus/intelligence/experiments/runner.py#L73-L159) `_run_single_backtest` is **module-level** (picklable), never imports ExperimentStore, never touches SQLite. Each exception is caught and returned as an error-shape dict (never raised past the subprocess boundary).
- Main-process-only responsibilities are preserved ([L394-L463](argus/intelligence/experiments/runner.py#L394-L463)): fingerprint dedup (`_store.get_by_fingerprint`), unsupported-pattern FAILED-record writes, all `save_experiment` calls in the `for coro in asyncio.as_completed(...)` loop.
- `workers: int = 1` default [runner.py:309](argus/intelligence/experiments/runner.py#L309) + `ExperimentConfig.max_workers: int = Field(default=4, ge=1, le=32)` [config.py:79](argus/intelligence/experiments/config.py#L79) + `--workers` CLI flag in `run_experiment.py`. Consistent.
- `_resolve_universe_symbols` closes `HistoricalQueryService` in `finally` ([L785-L786](argus/intelligence/experiments/runner.py#L785-L786)). DuckDB validation via `validate_symbol_coverage(..., min_bars=100)`. Dynamic filter fields are logged as skipped; static filters (price, volume) are applied via inline SQL. Date params are bound parameters, but **static filter values are inlined as f-string** (operator-controlled, Pydantic-validated — documented trade-off per Sprint 31.5 review).
- `workers > 1` branch ([L394-L520](argus/intelligence/experiments/runner.py#L394-L520)) handles `KeyboardInterrupt` → partial-results return + `cancel_futures=True`. See L-03 — broad `Exception` in the dispatch loop does **not** cleanly shut down the pool.

---

## Q5. Exit Override Infrastructure (Sprint 32.5 S2)

Partially wired. Two real gaps:

- **Spawner side (complete):** `_dotpath_to_nested` [spawner.py:41-62](argus/intelligence/experiments/spawner.py#L41-L62) converts flat dot-paths (`"trailing_stop.atr_multiplier": 2.5`) into nested dicts. Spawner computes a fingerprint that includes exit_overrides ([spawner.py:194-196](argus/intelligence/experiments/spawner.py#L194-L196)) and stores `variant_strategy._exit_overrides = exit_overrides_nested` on the strategy instance ([L259](argus/intelligence/experiments/spawner.py#L259)).
- **Main.py side (missing):** `strategy_exit_overrides` is built from `config/strategies/*.yaml` files at [main.py:1060-1068](argus/main.py#L1060-L1068), passed to `OrderManager(...)` at [L1074-L1086](argus/main.py#L1074-L1086), **before** variant spawning at [L841-L953](argus/main.py#L841-L953). Nothing downstream reads `variant_strategy._exit_overrides`, so a variant with `exit_overrides:` would silently receive the default exit config. No `register_exit_override` or equivalent method exists on OrderManager.

See M-01 below. (Currently no variant in experiments.yaml uses `exit_overrides`, so this is latent.)

---

## Q6. Retention Enforcement

`enforce_retention` exists on three stores:

| Store | Default retention | Called at runtime? |
|-------|-------------------|:---:|
| `counterfactual_store.py:422` | 90 days | **yes** — `main.py:1202` |
| `experiments/store.py:695` | 90 days | **no** |
| `learning/learning_store.py:215` | per `LearningLoopConfig.report_retention_days` (default 90) | **no** |

`ExperimentStore` and `LearningStore` retention methods are orphaned. See M-03.

---

## Q7. Promotion Evaluator

- Mode idempotency guards ([promotion.py:164-166, 273-275](argus/intelligence/experiments/promotion.py#L164-L166)) — already-live skips promotion; already-shadow skips demotion.
- PromotionEvent **persisted before** mode update ([L233-L235, L325-L327](argus/intelligence/experiments/promotion.py#L233-L235)) — atomic safety on crash.
- Hysteresis: demotion requires `days_since_last_promote >= promotion_min_shadow_days` ([L288-L298](argus/intelligence/experiments/promotion.py#L288-L298)). Uses `list_promotion_events` which returns newest-first; `next((e for e in past_events if e.action == "promote"), None)` picks the most recent promotion. Correct.
- Mode-change propagation to in-memory strategy via `matching.config.mode = promo_event.new_mode` ([main.py:2105](argus/main.py#L2105)). `StrategyConfig` is a non-frozen Pydantic BaseModel → mutation works; `_process_signal` reads `getattr(...config, 'mode', 'live')` at [main.py:1701-1704](argus/main.py#L1701-L1704). End-to-end path is intact.
- Gated by `experiments.auto_promote` which defaults to `false` in config; current `config/experiments.yaml` explicitly sets `auto_promote: false`.

---

## Q8. Learning Service Pipeline

- 13-step pipeline in `_execute_analysis` ([learning_service.py:196-288](argus/intelligence/learning/learning_service.py#L196-L288)): read YAML → collect → preamble → metrics → weight → regime → enrich → threshold → correlation → assemble → persist → supersede → propose → save. Each step fail-safe at the call level (stores log-and-swallow); no step breaks the pipeline silently past that boundary.
- Concurrent guard: `if self._running: raise RuntimeError(...)` → reset in `finally` ([L184-L194](argus/intelligence/learning/learning_service.py#L184-L194)). Correctly cleaned on any exception.
- Auto-trigger ([L93-L148](argus/intelligence/learning/learning_service.py#L93-L148)): Event Bus subscription on `SessionEndEvent`, zero-trade guard, `asyncio.wait_for(..., timeout=120)`, explicit catches for `TimeoutError`, `RuntimeError` (double-run guard), generic `Exception`. **Cannot delay shutdown.**
- Per-strategy metrics (`_compute_strategy_metrics` [L327-L416](argus/intelligence/learning/learning_service.py#L327-L416)): uses trade-sourced records when ≥ 5 available, falls back to combined. Sharpe only computed when ≥ 5 distinct ET trading days (annualised with `sqrt(252)` scaler).

---

## Q9. Config Proposal Manager Safety

- Startup YAML parse check ([L65-L95](argus/intelligence/learning/config_proposal_manager.py#L65-L95)) — `RuntimeError` if `quality_engine.yaml` is unparseable or fails Pydantic validation. Fails fast, does not swallow.
- Atomic write pattern ([L109-L141](argus/intelligence/learning/config_proposal_manager.py#L109-L141)): backup → `tempfile.mkstemp` in same directory (same filesystem, required for `os.rename` atomicity) → `os.rename`. Tempfile cleaned on exception.
- Cumulative drift guard ([L161-L183](argus/intelligence/learning/config_proposal_manager.py#L161-L183)) checked per-proposal. Documented edge case: multiple proposals in a batch use `current_value` from analysis time, not post-prior-proposal values — the in-code comment claims "conservative by design — drift may be overcounted, never undercounted."
- Pydantic validation of the **cumulative post-apply state** ([L199-L208](argus/intelligence/learning/config_proposal_manager.py#L199-L208)) — if any single proposal would break config, all stay APPROVED and nothing is written.
- Startup-only apply ([L143-L230](argus/intelligence/learning/config_proposal_manager.py#L143-L230)) — no mid-session call site.

See M-05 for an asymmetry in how redistribution drift is tracked (or not) in `config_change_history`.

---

## Q10. Outcome Collector & Analyzers

- Read-only: `OutcomeCollector` issues `aiosqlite.connect(...)` and only SELECTs. Both argus.db and counterfactual.db queries wrap in try/except-with-warn. `Path(...).exists()` gate avoids crashes on first boot.
- Source separation (Amendment 3): `_collect_trades` uses `source="trade"`, `_collect_counterfactual` uses `source="counterfactual"`. No crossover.
- `WeightAnalyzer._correlate_source` [weight_analyzer.py:154-210](argus/intelligence/learning/weight_analyzer.py#L154-L210): sample_size < 2 → INSUFFICIENT_DATA; zero-variance on scores or P&L → no correlation. `_normalize_weights` re-stitches to sum exactly 1.0.
- `ThresholdAnalyzer`: **two independent triggers** (missed > 0.40 → lower; correct < 0.50 → raise). See M-04 — when `missed > 0.50`, both fire and two contradictory `ConfigProposal` rows land in the DB with the same `field_path`.
- `CorrelationAnalyzer._compute_pearson` [correlation_analyzer.py:196-226](argus/intelligence/learning/correlation_analyzer.py#L196-L226): treats missing days as 0.0 P&L (union of both strategies' dates). `std == 0.0` → returns 0.0. Overlap count uses union (not intersection) — documented choice.

---

## CRITICAL Findings

| # | File:Line | Finding | Impact | Suggested Fix | Safety |
|---|-----------|---------|--------|---------------|--------|

(none)

## MEDIUM Findings

| # | File:Line | Finding | Impact | Suggested Fix | Safety |
|---|-----------|---------|--------|---------------|--------|
| M-01 | [spawner.py:259](argus/intelligence/experiments/spawner.py#L259), [main.py:841-953](argus/main.py#L841-L953), [main.py:1060-1086](argus/main.py#L1060-L1086) | Variant `_exit_overrides` set on strategy instance by spawner but **never wired to OrderManager**. `OrderManager._strategy_exit_overrides` is constructed from `config/strategies/*.yaml` files BEFORE variant spawning; no code path reads `variant_strategy._exit_overrides` and registers it. Any variant with `exit_overrides:` in experiments.yaml would silently get default exit config. | DEF-132 exit-override dimension is incomplete end-to-end. Currently latent — no variant uses `exit_overrides:` in `config/experiments.yaml`, so nothing is actively misconfigured. But the feature is documented as shipped in Sprint 32.5 and the first time someone sets `exit_overrides:` they'll get a silent failure. | Add a registration method on `OrderManager` (e.g. `register_strategy_exit_override(strategy_id, overrides)`) that also invalidates `_exit_config_cache[strategy_id]`. Call it from main.py for each spawned variant whose `_exit_overrides` is not None. Alternatively, fold variant exit overrides into `strategy_exit_overrides` before OrderManager construction (more invasive because spawning currently happens after OrderManager is built). | weekend-only |
| M-02 | [runner.py:878-894](argus/intelligence/experiments/runner.py#L878-L894) vs [factory.py:206-259](argus/strategies/patterns/factory.py#L206-L259) | Two different fingerprint schemes coexist. Runner hashes `{"detection_params": {...}, "exit_overrides": {...}}`; factory (used by spawner) hashes `{"detection": {...}, "exit": {...}}`. Same semantic content, **different SHA-256 output**. For the detection-only path both produce identical hashes (single-level dict, same keys), but as soon as `exit_sweep_params` are introduced in a sweep, the grid-sweep fingerprint for a config will NOT match the spawner-produced fingerprint for the identical variant. | Dedup between grid-sweep experiments and manual variants breaks when exit overrides are present. `get_by_fingerprint` would fail to find the manual variant's fingerprint in a sweep-result table and vice versa. Currently latent (no variants use exit_overrides, `exit_sweep_params: null`). | Unify both paths on `factory.compute_parameter_fingerprint`. Runner should build the canonical dict via the factory helper rather than ad-hoc. | weekend-only |
| M-03 | [experiments/store.py:695](argus/intelligence/experiments/store.py#L695), [learning/learning_store.py:215](argus/intelligence/learning/learning_store.py#L215), vs [main.py:1202](argus/main.py#L1202) | `enforce_retention` exists on `ExperimentStore` (90 days default) and `LearningStore` (90 days from `report_retention_days`) but is **never called at boot or on any schedule** in `argus/`. Only `counterfactual_store.enforce_retention` is wired. | `data/experiments.db` and `data/learning.db` grow unbounded. Over time, `list_experiments` and `list_reports` pagination degrades, and backups grow. No active failure, just slow accretion. | Call `experiment_store.enforce_retention(max_age_days=90)` and `learning_store.enforce_retention(learning_loop_config.report_retention_days)` in the relevant startup phases of `main.py`, mirroring the counterfactual pattern. | safe-during-trading |
| M-04 | [threshold_analyzer.py:115-151](argus/intelligence/learning/threshold_analyzer.py#L115-L151), [learning_service.py:509-532](argus/intelligence/learning/learning_service.py#L509-L532) | `ThresholdAnalyzer._analyze_grade` can append **both** a "lower" and a "raise" `ThresholdRecommendation` for the same grade. `missed_opportunity_rate + correct_rejection_rate = 1.0` always, so when `missed > 0.50` both triggers fire. `_generate_proposals` then emits two `ConfigProposal` rows with the same `field_path` (`thresholds.<grade>`), one with value `current - 5.0` and one with `current + 5.0`. If an operator approves both, `apply_pending` applies them sequentially — second overwrites first and the drift guard sees twice the delta. | Confusing operator UX (two contradictory proposals to review), and a subtle bug if both are approved. | Either (a) pick the stronger signal and emit exactly one recommendation per grade (e.g. `raise` when correct < 0.50, else `lower` when missed > 0.40); or (b) enforce at `apply_pending` that only one pending `thresholds.<grade>` proposal survives. Option (a) is cleaner. | safe-during-trading |
| M-05 | [config_proposal_manager.py:186-194, 424-452](argus/intelligence/learning/config_proposal_manager.py#L186-L194) | `_redistribute_weights` proportionally adjusts non-changed weight dimensions to maintain sum-to-1.0, but the **redistribution deltas are never recorded** in `config_change_history`. Only the explicitly-changed dimension is persisted via `record_change`. `get_cumulative_drift(dim, window)` therefore undercounts drift on redistributed dimensions. | Cumulative drift guard is evadable: repeatedly promote dim A up while dims B/C/D/E silently drift down via redistribution, and the guard never trips for B/C/D/E. Over months this could push the weight vector far from the initial anchor without operator awareness. | After applying each approved proposal, compute the actual delta for every redistributed dimension (compare pre- vs post-redistribution values) and call `record_change(..., source="learning_loop_redistribution", proposal_id=...)` for each. Drift guard then sees the full picture. | weekend-only |

## LOW Findings

| # | File:Line | Finding | Impact | Suggested Fix | Safety |
|---|-----------|---------|--------|---------------|--------|
| L-01 | [learning/models.py:409-423](argus/intelligence/learning/models.py#L409-L423) | `_convert_datetimes` in `LearningReport.to_dict()` converts `isinstance(val, datetime)` only. A `date` (not `datetime`) field would slip through and cause `json.dumps` to fail at `learning_store.py:124` (no `default=str` there). | Latent serialization crash if a future `LearningReport` / nested dataclass field uses `date`. No current failure — present dataclasses use `datetime` only. Same failure class as DEF-151. | Either widen the guard to `isinstance(val, (date, datetime))` (keep `datetime` first so `.isoformat()` picks the richer branch), or add `default=str` to the `json.dumps` call in `learning_store.save_report`. | safe-during-trading |
| L-02 | [promotion.py:365-413](argus/intelligence/experiments/promotion.py#L365-L413) | `_build_result_from_shadow` and `_count_shadow_trading_days` issue **two independent** `counterfactual_store.query(..., limit=1000)` calls per variant per pass. If a strategy has >1000 shadow positions, the two queries return the same 1000 rows (DESC order), so day-count and r_multiple-count remain consistent. But the second query is redundant I/O. | Minor DB I/O waste during promotion evaluation (N variants × 2 queries instead of N). No correctness issue today. | Query once, compute both R-multiple list and unique day count from the returned rows. Avoids the second round-trip and future-proofs against the two limits ever diverging. | safe-during-trading |
| L-03 | [runner.py:468-520](argus/intelligence/experiments/runner.py#L468-L520) | `workers > 1` branch catches `KeyboardInterrupt` and cleanly shuts down the executor with `cancel_futures=True`. A broad `Exception` raised inside `asyncio.as_completed(...)` (e.g. `aiosqlite.OperationalError` during `save_experiment`) would propagate past the try/else without `executor.shutdown(wait=False)`, leaving worker subprocesses running until the asyncio event loop exits. | Potential orphan subprocess on rare write-path exceptions during parallel sweeps. Not triggered during normal operation (fire-and-forget store swallows writes). | Convert the `else: executor.shutdown(wait=True)` into a `finally:` that always runs. Or wrap the executor in a `with ProcessPoolExecutor(...) as executor:` context manager (which handles shutdown on any exit path). | weekend-only |
| L-04 | [learning_service.py:93-104](argus/intelligence/learning/learning_service.py#L93-L104) | `register_auto_trigger` subscribes to `SessionEndEvent` with no teardown path — no `unsubscribe` call at shutdown. In practice both `LearningService` and `EventBus` live for the process lifetime, so this is not a leak today. Flag for visibility only; if `LearningService` ever becomes per-session (e.g. rebuilt on config reload), the subscription leaks across reloads. | No active bug. | If `LearningService` lifecycle ever changes, add an explicit unsubscribe in a `shutdown()` method. | read-only-no-fix-needed |
| L-05 | [experiments/store.py:765](argus/intelligence/experiments/store.py#L765) | `_row_to_experiment` coerces `int(row["shadow_trades"])` directly. Column is `NOT NULL DEFAULT 0` in the DDL, so new rows are safe. Pre-DDL rows (none exist in production) would raise. | Theoretical only — no schema drift risk in the current DB. | No action needed. | read-only-no-fix-needed |
| L-06 | [experiments/runner.py:394-520](argus/intelligence/experiments/runner.py#L394-L520) vs [L525-L640](argus/intelligence/experiments/runner.py#L525-L640) | Parallel and sequential sweep paths have significant code duplication — both handle unsupported-pattern FAILED records, both build `ExperimentRecord` with the same field set, both call `save_experiment` in the same shape. Two places to update if the record shape evolves. | Refactor risk, not a bug. | Extract a `_build_and_save_record(pattern_name, params, fingerprint, result, status, strategy_type, ...)` helper used by both paths. | safe-during-trading |
| L-07 | [learning_service.py:499](argus/intelligence/learning/learning_service.py#L499) | `rationale` f-string includes `rec.correlation_trade_source or rec.correlation_counterfactual_source` — if both are `None` this prints `None`. Rationale is human-facing only; cosmetic. | Rationale text on some proposals may show "correlation=None". | Format with a defensive `correlation_trade_source or correlation_counterfactual_source or 0.0`. | safe-during-trading |

## COSMETIC Findings

| # | File:Line | Finding | Impact | Suggested Fix | Safety |
|---|-----------|---------|--------|---------------|--------|
| C-01 | [runner.py:91-103](argus/intelligence/experiments/runner.py#L91-L103) | `_run_single_backtest` does heavy local aliasing (`_asyncio`, `_date`, `_Path`, `_BEConfig`, `_StrategyType`, `_BacktestEngine`) with `# noqa: PLC0415`. The comment in the exception fallback explains why (pickle/subprocess loading), but the aliasing style is noisy and duplicates the module-level imports that already exist. | Readability only. | Remove the aliasing, keep the explanatory comment, and let the noqa apply to the function import block rather than every statement. | safe-during-trading |
| C-02 | [config.py:70,80](argus/intelligence/experiments/config.py#L70-L80) | `ExperimentConfig.variants` is typed `dict[str, list[dict[str, Any]]]` — accepts any shape. Each variant_def is later validated inside the spawner, but invalid top-level keys (e.g. typo'd `varients:` → entire dict ignored) pass Pydantic because `variants` is the catch-all. `extra="forbid"` helps on keys, not on value shape. | Low-visibility config typos. | Define a `VariantConfig` Pydantic model (`variant_id: str`, `mode: Literal["live","shadow"]`, `params: dict[str, Any]`, `exit_overrides: dict[str, float] \| None = None`) and retype `variants: dict[str, list[VariantConfig]]`. | safe-during-trading |
| C-03 | [learning/__init__.py:1-42](argus/intelligence/learning/__init__.py#L1-L42) | `__init__.py` exports stores/service/models but **not** the three analyzers (`WeightAnalyzer`, `ThresholdAnalyzer`, `CorrelationAnalyzer`). Consumers (main.py, tests) import them by module path directly. Minor asymmetry. | Readability. | Add analyzers to `__all__` and the import list, or document why they're not public API. | read-only-no-fix-needed |
| C-04 | [promotion.py:118-128](argus/intelligence/experiments/promotion.py#L118-L128) | `_evaluate_for_promotion` hand-constructs a new `VariantDefinition` with `mode="live"` to append to the in-memory `live_variants` list after each promotion, duplicating every field. `VariantDefinition` is frozen, but `dataclasses.replace(shadow_variant, mode="live")` would be one line. | Readability. | Use `dataclasses.replace(shadow_variant, mode="live")`. | safe-during-trading |
| C-05 | [runner.py:244](argus/intelligence/experiments/runner.py#L244) | `combos = list(itertools.product(*[param_ranges[k] for k in keys]))` materialises the entire cartesian product twice (once as combos, once in the list comprehension that follows). For large grids (near `_GRID_CAP = 500`) this is a minor memory blip. | Negligible. | Iterate directly: `detection_grid = [dict(zip(keys, combo)) for combo in itertools.product(*(param_ranges[k] for k in keys))]`. | safe-during-trading |
| C-06 | [experiments/store.py:150-157](argus/intelligence/experiments/store.py#L150-L157) | Idempotent `ALTER TABLE variants ADD COLUMN exit_overrides TEXT` swallows a bare `except Exception: pass`. Works in practice (SQLite raises on duplicate column), but hides other failure modes (permissions, disk full). | Reviewability only. | Narrow to `except aiosqlite.OperationalError:` with a sanity check on the error message. | safe-during-trading |

---

## Positive Observations

1. **Fire-and-forget + rate-limited warnings pattern** (DEC-345) is applied consistently across ExperimentStore, LearningStore, CounterfactualStore. Each store holds `_last_warn_time` and re-uses `_rate_limited_warn(msg, *args)` on write failures. No handler crashes the caller.
2. **WAL journal mode** enabled on both `experiments.db` and `learning.db` at init. Matches DEC-345 pattern.
3. **Atomic YAML write** in `ConfigProposalManager._write_yaml_atomic` (backup → tempfile-in-same-dir → `os.rename`) — deliberate, correct implementation of the atomicity invariant. Tempfile cleaned on error path.
4. **Startup YAML parse check** in `ConfigProposalManager.__init__` — `RuntimeError` on unparseable or Pydantic-invalid `quality_engine.yaml`. No silent failure.
5. **Cumulative post-apply Pydantic validation** — `apply_pending` validates the ENTIRE post-application config as a unit before writing. If any single proposal would push total config invalid, NOTHING is written and all proposals stay APPROVED.
6. **PromotionEvent persisted BEFORE mode update** — if the process crashes between `save_promotion_event` and `update_variant_mode`, the event is recoverable and the next boot sees the intent.
7. **Idempotency guards** on `_evaluate_for_promotion` (`if shadow_variant.mode == "live": return None`) and `_evaluate_for_demotion` (`if live_variant.mode == "shadow": return None`). Safe to re-run.
8. **Hysteresis** on demotion (`days_since < min_shadow_days`) — prevents promote/demote thrash on short-term noise.
9. **Zero-trade and zero-counterfactual guard** on `LearningService._on_session_end` — doesn't generate empty reports on quiet days.
10. **120s timeout** on auto-triggered analysis — cannot delay shutdown.
11. **Double-run guard** on `LearningService.run_analysis` (`self._running`) with `finally`-reset. Correctly cleaned on any exception.
12. **Source separation (Amendment 3)** faithfully respected across all analyzers: trade vs counterfactual records are always separated and re-combined only when documented (e.g. weight correlation falls back to CF when trade < min_sample_count).
13. **Zero-variance guards** in `WeightAnalyzer._correlate_source` for both dimension scores and P&L outcomes — prevents `spearmanr` from returning NaN, `ConfidenceLevel.INSUFFICIENT_DATA` assigned.
14. **Weight normalization** in `WeightAnalyzer._normalize_weights` — recommended weights always sum to 1.0 exactly.
15. **Fingerprint dedup against base** in VariantSpawner — a variant whose params hash matches the base strategy's is skipped with a log line, not added as a duplicate.
16. **ValidationError isolation** in VariantSpawner — one invalid variant `ValidationError` skips that variant only, never aborts sibling spawns or base system startup.
17. **`_resolve_universe_symbols` resource cleanup** — `HistoricalQueryService.close()` in `finally` guarantees DuckDB connection release even on query failure.
18. **`ProcessPoolExecutor` main-process-only writes** — all `save_experiment` calls happen in the main process, eliminating the SQLite-parallel-writer foot-gun.
19. **Shadow variant fleet is coherent:** all 22 variants valid, all `mode: shadow`, all 10 patterns represented, `max_variants_per_pattern: 8` respected, `auto_promote: false` keeps promotion dormant until the operator flips it on — exactly the right posture for the current "22 shadow variants collecting data" phase.
20. **DEF-151 fix is complete AND defensive:** `json.dumps(record.backtest_result, default=str)` at store.py:193 is the single critical location, and a canonical-JSON fingerprint call (runner.py:891) also carries `default=str` even though it processes only primitives — cheap belt-and-suspenders that'll survive a future param type widening.

---

## Statistics

- Files deep-read: 6 (runner 917L, spawner 336L, promotion 492L, store 838L, learning_service 571L, config_proposal_manager 468L)
- Files skimmed: 9 (experiments: config, models, __init__; learning: weight_analyzer, threshold_analyzer, correlation_analyzer, outcome_collector, learning_store, models)
- Cross-references: `argus/strategies/patterns/factory.py`, `argus/intelligence/counterfactual_store.py`, `argus/main.py`, `argus/execution/order_manager.py`, `argus/data/historical_query_service.py`, `config/experiments.yaml`
- Total findings: **18** (0 critical, 5 medium, 7 low, 6 cosmetic)
- Safety distribution: 9 safe-during-trading / 5 weekend-only / 3 read-only-no-fix-needed / 1 deferred-to-defs candidate (M-01 is also tracked as an unopened DEF candidate — the unfinished Sprint 32.5 S2 wiring)
- Estimated Phase 3 fix effort: **~3 sessions** (one weekend-only for M-01+L-03 in main.py+OrderManager+runner.py, one weekend-only for M-02+M-05 in runner.py+config_proposal_manager.py, one safe-during-trading for M-03+M-04+L-01 in main.py+threshold_analyzer.py+models.py)

**Context State: GREEN** — session well within context limits; single pass over every listed file.

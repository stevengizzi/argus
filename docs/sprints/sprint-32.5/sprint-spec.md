# Sprint 32.5: Experiment Pipeline Completion + Visibility

## Goal

Close three critical gaps in the experiment pipeline (exit parameters as variant dimensions, BacktestEngine support for all 7 PatternModule patterns, and full operational visibility via API + UI) and document the Adaptive Capital Intelligence architectural vision. This sprint takes the experiment infrastructure from Sprint 32's "plumbing works" state to "operator can see, compare, and understand what the experiment pipeline is doing."

## Scope

### Deliverables

1. **DEF-132: Exit parameters as variant dimensions.** VariantDefinition expanded with `exit_overrides` field. Parameter fingerprint expanded to include exit params via namespaced canonical JSON (`{"detection": {...}, "exit": {...}}`). VariantSpawner applies exit overrides via `strategy_exit_overrides` deep merge. ExperimentRunner grid generation optionally includes exit dimensions. Config schema accepts exit sweep parameters.

2. **DEF-134: BacktestEngine support for all 7 PatternModule patterns.** The remaining 5 patterns (dip_and_rip, hod_break, abcd, gap_and_go, premarket_high_break) added to experiment runner's pattern mapping. BacktestEngine supplies reference data (prior close, PM high) for gap_and_go and premarket_high_break from Parquet OHLCV-1m historical feed. All 7 patterns can be swept via `scripts/run_experiment.py`.

3. **DEF-131: Experiments + counterfactual visibility.** Three new REST endpoints (counterfactual positions, experiment variants with status/metrics, promotion event history). Shadow Trades tab on Trade Log page showing all shadow/counterfactual positions with rejection metadata, theoretical P&L, MFE/MAE. Experiments Dashboard (9th page) with variant status table, promotion event log, and pattern-level comparison.

4. **DEF-133: Adaptive Capital Intelligence vision document.** Architecture vision document at `docs/architecture/allocation-intelligence-vision.md` covering problem statement, unified allocation intelligence design, 6 input dimensions, phased implementation roadmap, data requirements, architectural sketch, and relationship to existing components.

5. **Doc-sync.** All canonical documentation updated to reflect Sprint 32.5 changes.

### Acceptance Criteria

1. **DEF-132 (Exit params):**
   - `VariantDefinition` model accepts `exit_overrides: dict[str, Any] | None` field
   - `compute_parameter_fingerprint()` with exit_overrides=None produces identical hash to pre-expansion behavior (golden hash test)
   - Two variants with identical detection params but different exit_overrides produce different fingerprints
   - VariantSpawner applies exit_overrides to spawned strategy via existing deep_merge path
   - ExperimentRunner generates grid points that include exit parameter dimensions when configured
   - `config/experiments.yaml` loads without error both with and without exit_overrides fields

2. **DEF-134 (All 7 patterns):**
   - `scripts/run_experiment.py --pattern dip_and_rip` completes without error and produces BacktestResult with trades > 0
   - Same for hod_break, abcd, gap_and_go, premarket_high_break
   - bull_flag and flat_top_breakout continue to work identically (regression)
   - gap_and_go receives prior day close via set_reference_data() from BacktestEngine
   - premarket_high_break receives PM high via set_reference_data() from BacktestEngine
   - First day of data range for reference-data patterns logs warning and skips (no crash)

3. **DEF-131 (Visibility):**
   - `GET /api/v1/counterfactual/positions` returns shadow positions with filters (strategy, date range, rejection stage)
   - `GET /api/v1/experiments/variants` returns all variants with current mode, fingerprint, trade count, key metrics
   - `GET /api/v1/experiments/promotions` returns promotion/demotion event history
   - All 3 endpoints are JWT-protected and return 401 for unauthenticated requests
   - Trade Log page has a functioning "Shadow Trades" tab showing counterfactual positions
   - Shadow trades display: symbol, strategy/variant ID, entry/exit price, theoretical P&L, R-multiple, MFE/MAE, rejection reason, rejection stage, quality grade
   - Experiments page accessible from navigation, keyboard shortcut works
   - Experiments page shows: variant table with mode/fingerprint/metrics, promotion log, pattern comparison
   - Both pages handle empty state gracefully (no experiments run, no shadow trades)
   - `experiments.enabled: false` disables experiment-related UI elements (page still loads, shows disabled state)

4. **DEF-133 (Vision document):**
   - Document exists at `docs/architecture/allocation-intelligence-vision.md`
   - Contains all 9 sections specified in the planning handoff
   - Document is self-contained (readable without other context)

5. **Doc-sync:**
   - project-knowledge.md, CLAUDE.md, roadmap.md, sprint-history.md, decision-log.md, dec-index.md, architecture.md, sprint-campaign.md all updated

### Performance Benchmarks

| Metric | Target | Measurement Method |
|--------|--------|--------------------|
| `/api/v1/counterfactual/positions` response | < 500ms for 90-day query | Manual test with accumulated data |
| `/api/v1/experiments/variants` response | < 200ms | Manual test |
| Experiments page initial load | < 2s | Browser dev tools |
| ABCD backtest (1 symbol, 1 month) | < 60s | CLI timing (O(n³) accepted, just documented) |

### Config Changes

| YAML Path | Pydantic Model | Field Name | Type | Default |
|-----------|---------------|------------|------|---------|
| `experiments.yaml` → variant defs → `exit_overrides` | `VariantDefinition` | `exit_overrides` | `dict[str, Any] \| None` | `None` |
| `experiments.yaml` → `exit_sweep_params` | `ExperimentConfig` | `exit_sweep_params` | `list[ExitSweepParam] \| None` | `None` |

`ExperimentConfig` already has `extra="forbid"` — unrecognized keys raise ValidationError rather than being silently dropped.

## Dependencies

- Sprint 32 complete and merged to main (experiment pipeline infrastructure)
- Sprint 32 cleanup items applied (confirmed complete per handoff)
- Parquet historical cache available at `data/databento_cache` (for DEF-134 backtest tests)
- Git main branch up to date

## Relevant Decisions

- DEC-345: SQLite separation pattern (counterfactual.db, experiments.db) — new query methods follow this pattern
- DEC-359: BacktestEngine risk_overrides for single-strategy backtesting — reuse for new patterns
- DEC-300: Config-gating pattern (experiments.enabled) — UI degrades gracefully when disabled
- DEC-328: Test suite tiering — full suite at sprint entry and close-outs only
- DEC-342: Strategy observability patterns — frontend hooks and lazy-loading patterns
- Sprint 28.5: Exit management infrastructure (ExitManagementConfig, deep_update, strategy_exit_overrides) — DEF-132 leverages this
- Sprint 32: Pattern factory, ExperimentConfig extra="forbid", parameter fingerprint design — DEF-132 extends these

## Relevant Risks

- RSK-032 (ongoing): ABCD O(n³) swing detection makes backtesting slow. Accepted for this sprint; documented in DEF-122.
- Risk: PM candle availability in EQUS.MINI Parquet data may be sparse for some symbols/dates. Mitigation: graceful fallback (skip symbol-date with logged warning).
- Risk: CounterfactualStore query performance on 90+ days of accumulated data. Mitigation: add pagination to positions endpoint; defer complex aggregations to client-side.

## Session Count Estimate

8 sessions + 2 contingency (0.5 each). S1-S2 cover DEF-132, S3-S4 cover DEF-134, S5 covers API, S6-S7 cover UI (with S6f/S7f visual-review fix contingency), S8 covers vision doc + doc-sync. All sessions score ≤13 on compaction risk. Two parallel execution opportunities (S1∥S3, S6∥S7) available in HITL mode.

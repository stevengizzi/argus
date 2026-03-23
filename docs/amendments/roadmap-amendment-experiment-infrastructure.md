# ARGUS Roadmap Amendment Proposal: Experiment Infrastructure

> **Status:** Proposal — not yet adopted (v2 revision)
> **Author:** Claude.ai strategic planning conversation, March 23, 2026
> **Context:** Sprint 27 (BacktestEngine Core) complete. Autoresearch pattern analysis (March 13 conversation) identified that the roadmap builds evaluation capabilities late — optimization loops don't close until Sprint 40. This amendment inserts the connective tissue that turns individual capabilities into a self-improving system.
> **Roadmap version:** v2.0 (March 22, 2026)
> **Decision point:** Sprint 21.6 planning (immediate — next sprint)
> **v2 revision notes:** Redesigned for the full ARGUS vision — 1000+ hyper-specialized micro-strategies, ensemble-level evaluation, overnight autonomous operation, and cohort-based promotion. v1 was sound near-term infrastructure but would have required rearchitecture at Sprint 36+.

---

## 1. Executive Summary

ARGUS has the **execution primitives** for continuous improvement: BacktestEngine runs real strategy code against historical data, walk-forward validation gates overfitting, and the Quality Engine records every score-to-outcome pair. What's missing is the **experiment discipline** — the infrastructure that turns "I tried changing X" into a tracked, evaluated, statistically validated, automatically promoted-or-reverted decision.

Karpathy's autoresearch pattern works because it has three things: a way to evaluate changes (ELO), a way to track what was tried (git keep/revert), and a way to promote improvements automatically. ARGUS needs the trading-domain equivalents of all three, with additional safeguards for non-stationary environments, multi-objective optimization, and — critically — **ensemble-scale operation** where the evaluation unit is a cohort of strategies, not an individual strategy.

This proposal adds **two new sprints** at natural dependency boundaries:

| Sprint | Name | Placement | Duration | What It Enables |
|--------|------|-----------|----------|-----------------|
| **27.5** | Evaluation Framework | Between 21.6 and 28 | ~2–3 days | Multi-objective scoring, regime-conditional evaluation, Pareto dominance, ensemble evaluation, tiered confidence |
| **32.5** | Experiment Registry + Promotion Pipeline | Between 32 and 33 | ~4 days | Experiment tracking, cohort-based promotion, simulated-paper screening, overnight experiment queue, automated paper→live with kill switch |

**Net roadmap impact:** +6–7 days, but both sprints de-risk everything downstream and — more importantly — are designed for the full 1000+ micro-strategy vision from day one, avoiding a rearchitecture sprint at Phase 9.

### Design Principles

Three principles distinguish this from naive autoresearch:

1. **The ensemble is the unit of evaluation, not the individual strategy.** A hyper-specialized micro-strategy that trades 3 times per month cannot be individually validated. But 50 such strategies collectively generating 150 trades in 20 days? That's a meaningful sample. Evaluation and promotion operate at cohort level.

2. **The system improves around the clock.** US market hours are 3:30 PM – 11:00 PM SAST. The other 16.5 hours per day are compute time. The experiment queue and background worker are designed for overnight BacktestEngine sweeps from Sprint 32.5, even though the AI-driven hypothesis generation (Sprint 41) comes later.

3. **Validation speed scales with strategy specificity.** High-frequency strategies (50+ trades/month) get individual paper validation. Hyper-specialized strategies get ensemble-level validation via simulated-paper, then real paper at cohort level. Without this tiering, paper validation becomes a multi-year bottleneck that kills the entire vision.

---

## 2. The Problem: Open Loops + Scale Walls

### Open Loops (Same as v1)

The current roadmap builds components that generate data but don't close the feedback loop until much later:

| Component | Built In | Loop Closes In | Gap |
|-----------|----------|----------------|-----|
| Quality Engine (weight tuning) | Sprint 24 ✅ | Sprint 28 (Learning Loop) | 4 sprints — **acceptable** |
| BacktestEngine (evaluation) | Sprint 27 ✅ | Sprint 33 (Statistical Validation) | 6 sprints — **too late** |
| Strategy parameters (optimization) | Sprint 32 (Templates) | Sprint 34 (Systematic Search) | 2 sprints — **acceptable** |
| Experiment tracking | Never built explicitly | Sprint 40 (Continuous Discovery) assumes it | **Missing entirely** |
| Paper→live promotion | Manual forever | Sprint 40 (Learning Loop V2 mentions it) | **Missing entirely** |

### Scale Walls (New in v2)

Beyond open loops, the full vision hits concrete walls if infrastructure assumes individual-strategy evaluation:

| Wall | Where It Hits | Impact |
|------|---------------|--------|
| **Paper validation bottleneck** | Sprint 34+ (500+ candidates from systematic search) | At 5 concurrent × 20 days: 2,000+ trading days to validate. ~8 years. |
| **Minimum trade count kills specialization** | Sprint 34+ (hyper-specialized micro-strategies) | A strategy trading 3×/month needs 10+ months for 30-trade minimum per regime. |
| **No overnight compute** | Sprint 34+ (systematic search is compute-heavy) | Market hours needed for paper trading; BacktestEngine sweeps compete for the same time window. |
| **Individual promotion doesn't compose** | Sprint 38+ (ensemble orchestration) | Adding one strategy at a time to a 500-strategy ensemble can't measure interaction effects. |
| **Registry at millions of entries** | Sprint 34+ (500K+ parameter combinations per family) | SQLite single-table design degrades. Aggregate queries become expensive. |

---

## 3. Amendment A: Sprint 27.5 — Evaluation Framework

### Placement Rationale

**After Sprint 21.6** (Backtest Re-Validation): Sprint 21.6 is the first real BacktestEngine consumer. It will produce results for all 7 strategies. Those results need a structured representation — not ad-hoc Sharpe comparisons — to be useful for the Learning Loop that follows.

**Before Sprint 28** (Learning Loop V1): The Learning Loop's core job is evaluating whether Quality Engine weight changes are improvements. "Improvement" across Sharpe, max drawdown, profit factor, win rate, and regime stability simultaneously requires Pareto dominance logic. Building that *inside* Sprint 28 would bloat it; building it *before* Sprint 28 means the Learning Loop can focus on its actual job.

### Scope

#### 3.1 MultiObjectiveResult

A structured evaluation output that captures everything needed to compare two configurations:

```
MultiObjectiveResult:
    # Identity
    strategy_id: str
    parameter_hash: str        # Deterministic hash of config that produced this
    evaluation_date: datetime
    data_range: tuple[date, date]
    
    # Primary metrics (all must be present)
    sharpe_ratio: float
    max_drawdown_pct: float    # Negative number (e.g., -0.12 = 12% drawdown)
    profit_factor: float
    win_rate: float
    total_trades: int
    expectancy_per_trade: float
    
    # Regime breakdown (same metrics per regime)
    regime_results: dict[RegimeType, RegimeMetrics]
    
    # Statistical confidence
    p_value: float | None      # None until Sprint 33 adds FDR
    confidence_interval: tuple[float, float] | None
    confidence_tier: ConfidenceTier  # HIGH, MODERATE, LOW, ENSEMBLE_ONLY
    
    # Walk-forward
    wfe: float
    is_oos: bool               # True if these are out-of-sample results
```

This becomes the **universal currency** of evaluation. Every component that evaluates anything — BacktestEngine, Learning Loop, Systematic Search, Continuous Discovery — produces and consumes `MultiObjectiveResult`.

#### 3.2 Tiered Confidence Model

Not all strategies produce enough data for individual statistical validation. Instead of a flat minimum trade count that blocks hyper-specialized strategies entirely, evaluation confidence is tiered:

```
ConfidenceTier:
    HIGH           # 50+ trades total, 15+ trades in ≥3 regimes
                   # → Full individual Pareto comparison. Individual promotion eligible.

    MODERATE       # 30–49 trades total, 10+ trades in ≥2 regimes
                   # → Individual comparison with wider tolerance bands.
                   # → Individual promotion eligible with extended paper period (30 days).

    LOW            # 10–29 trades total
                   # → Individual metrics computed but NOT used for standalone comparison.
                   # → Ensemble contribution evaluation only. Cohort promotion only.

    ENSEMBLE_ONLY  # <10 trades total
                   # → No individual metrics meaningful.
                   # → Evaluated purely by marginal contribution to ensemble.
                   # → Cohort promotion only.
```

The tier is computed automatically from trade count and regime distribution. A hyper-specialized micro-strategy that fires 3 times per month lands in LOW or ENSEMBLE_ONLY — it can still be promoted, but only as part of a cohort where the ensemble's aggregate statistics provide the confidence.

This is the key insight: **you don't need to validate every neuron individually to know the brain works better.** You validate the ensemble.

#### 3.3 EnsembleResult

A first-class evaluation for a group of strategies operating together:

```
EnsembleResult:
    # Identity
    cohort_id: str
    strategy_ids: list[str]
    evaluation_date: datetime
    data_range: tuple[date, date]
    
    # Aggregate metrics (same shape as MultiObjectiveResult primary metrics)
    aggregate: MultiObjectiveResult     # Portfolio-level metrics
    
    # Ensemble-specific metrics
    diversification_ratio: float        # Portfolio vol / weighted sum of individual vols
                                        # >1.0 means diversification is helping
    marginal_contributions: dict[str, MarginalContribution]
        # Per strategy: what happens to ensemble Sharpe/drawdown if you remove it?
        # Strategies with negative marginal Sharpe are candidates for removal.
    
    tail_correlation: float             # Correlation during drawdowns (the dangerous kind)
    max_concurrent_drawdown: float      # Worst-case when multiple strategies draw down together
    capital_utilization: float          # Average % of capital deployed
    turnover_rate: float                # Annual turnover (affects commission cost)
    
    # Comparison
    baseline_ensemble: EnsembleResult | None  # The ensemble WITHOUT the new cohort
    improvement_verdict: ComparisonVerdict     # Does adding this cohort improve things?
```

`MarginalContribution` per strategy:
```
MarginalContribution:
    strategy_id: str
    marginal_sharpe: float        # Ensemble Sharpe with vs without this strategy
    marginal_drawdown: float      # Change in max drawdown
    correlation_to_ensemble: float # How redundant is this strategy?
    trade_count: int
    confidence_tier: ConfidenceTier
```

The key metric is `improvement_verdict`: does adding this cohort of strategies to the existing ensemble make things better? This is evaluated via Pareto dominance on the aggregate MultiObjectiveResult, plus ensemble-specific checks (diversification ratio didn't collapse, tail correlation didn't spike, no single strategy contributes >20% of ensemble P&L).

#### 3.4 Regime-Conditional Evaluation

Extend BacktestEngine to segment results by regime automatically:

- BacktestEngine already has access to the Orchestrator's regime classifier (SPY vol proxy).
- During a multi-day backtest run, tag each trading day with its regime classification.
- Produce per-regime `RegimeMetrics` alongside aggregate metrics.
- A strategy that shows Sharpe 2.5 aggregate but Sharpe -0.3 in high-vol regimes is not a good strategy — it's a fragile strategy that happens to have been tested mostly in favorable conditions.

Regime types (matching existing `RegimeClassifier` output): `TRENDING`, `MEAN_REVERTING`, `RANGE_BOUND`, `HIGH_VOLATILITY`, `LOW_VOLATILITY`.

#### 3.5 Comparison API

Utility functions consumed by Learning Loop and all downstream sprints:

**Individual comparison:**
- `compare(a: MultiObjectiveResult, b: MultiObjectiveResult) → ComparisonVerdict` — returns DOMINATES, DOMINATED, INCOMPARABLE, or INSUFFICIENT_DATA. Respects confidence tier: two ENSEMBLE_ONLY results always return INSUFFICIENT_DATA for individual comparison.
- `pareto_frontier(results: list[MultiObjectiveResult]) → list[MultiObjectiveResult]` — returns the non-dominated set. Filters to HIGH and MODERATE confidence only.
- `is_regime_robust(result: MultiObjectiveResult, min_regimes: int = 3) → bool` — checks that the result has positive expectancy in at least `min_regimes` regime types. Requires HIGH or MODERATE confidence.
- `soft_dominance(a, b, tolerance: dict[str, float]) → bool` — A is "better enough" if it improves on at least one metric by more than the tolerance and doesn't degrade any metric by more than the tolerance. Prevents the "everything is INCOMPARABLE" problem when strategies are close.

**Ensemble comparison:**
- `evaluate_cohort_addition(baseline_ensemble: EnsembleResult, candidate_strategies: list[MultiObjectiveResult]) → EnsembleResult` — simulates adding candidates to the ensemble and produces the resulting EnsembleResult with improvement_verdict.
- `marginal_contribution(ensemble: EnsembleResult, strategy_id: str) → MarginalContribution` — what happens to the ensemble if you remove this one strategy?
- `identify_deadweight(ensemble: EnsembleResult, threshold: float = 0.0) → list[str]` — strategies whose marginal Sharpe contribution is below threshold. Candidates for retirement.

**Formatting:**
- `format_comparison_report(a, b) → str` — human-readable comparison for CLI output and Copilot context.
- `format_ensemble_report(result: EnsembleResult) → str` — ensemble health summary.

### File Structure

```
argus/
├── analytics/
│   ├── evaluation.py          # MultiObjectiveResult, RegimeMetrics, ConfidenceTier, tiered logic
│   ├── ensemble_evaluation.py # EnsembleResult, MarginalContribution, cohort simulation
│   ├── comparison.py          # compare(), pareto_frontier(), soft_dominance(), ensemble comparisons
│   └── ...
├── backtest/
│   └── engine.py              # Modified: regime tagging during runs, produces MultiObjectiveResult
```

### Session Breakdown (Compaction Risk Scoring)

| Session | Scope | Files Created | Files Modified | Context Reads | Tests | Integration | Score |
|---------|-------|---------------|----------------|---------------|-------|-------------|-------|
| S1 | MultiObjectiveResult + RegimeMetrics + ConfidenceTier dataclasses, serialization, tier computation logic | 2 | 0 | 2 | 2 | 0 | **8** |
| S2 | Regime tagging in BacktestEngine + per-regime metrics aggregation | 0 | 2 (engine.py, config) | 3 | 2 | 1 | **10** |
| S3 | Individual comparison API: compare(), pareto_frontier(), soft_dominance(), is_regime_robust() | 1 | 1 | 2 | 3 | 0 | **9** |
| S4 | EnsembleResult + MarginalContribution + evaluate_cohort_addition() + identify_deadweight() | 1 | 1 | 3 | 2 | 1 | **10** |
| S5 | Integration tests (BacktestEngine → MultiObjectiveResult → ensemble evaluation round-trip) + CLI formatting | 0 | 2 | 2 | 3 | 2 | **11** |

All sessions ≤ 13. **Total: 5 sessions, ~2–3 days.**

### Tests: ~60 new

- Pareto dominance edge cases (ties, single metric, all identical)
- Confidence tier computation (boundary conditions for each tier)
- Regime tagging correctness (correct regime assigned per day)
- Individual comparison API (all 4 verdict types × all 4 confidence tiers)
- Soft dominance (tolerance band behavior, asymmetric tolerances)
- EnsembleResult construction (diversification ratio, marginal contribution signs)
- Cohort addition simulation (improvement vs degradation detection)
- Deadweight identification (positive, negative, zero marginal contribution)
- Serialization round-trip (SQLite storage for experiment registry in Sprint 32.5)
- Integration: BacktestEngine run → MultiObjectiveResult → ensemble evaluation

### Dependencies

- Sprint 27 (BacktestEngine) ✅ complete
- Sprint 21.6 (Re-Validation) — ideally complete first so we've seen real BacktestEngine output, but not strictly required
- No frontend work — this is pure backend infrastructure

### What This Does NOT Do

- No experiment tracking (Sprint 32.5)
- No FDR correction or p-values (Sprint 33 — the `p_value` field stays `None` until then)
- No UI (Research Console comes in Sprint 31)
- No automatic promotion (Sprint 32.5)
- No Learning Loop integration (Sprint 28 consumes this; this sprint just builds the framework)

---

## 4. Amendment B: Sprint 32.5 — Experiment Registry + Promotion Pipeline

### Placement Rationale

**After Sprint 32** (Parameterized Strategy Templates): Templates define the parameter space. The registry needs to know what parameters exist to track what was tried.

**Before Sprint 33** (Statistical Validation): Sprint 33 will run the first large-scale experiment (FDR framework). It needs somewhere to store and track the hundreds of thousands of candidates it evaluates. Building the registry *inside* Sprint 33 would bloat it and conflate infrastructure with the actual experiment.

### Scope

#### 4.1 ExperimentRegistry (Scale-Aware)

Persistent storage for every experiment ARGUS runs, designed for millions of entries from day one.

**Single experiment entry:**

```
Experiment:
    # Identity
    experiment_id: ULID
    batch_id: ULID              # Groups experiments from the same sweep/generation run
    cohort_id: ULID | None      # Assigned when experiments are grouped for promotion
    created_at: datetime
    
    # What changed
    experiment_type: ExperimentType  
        # PARAMETER_TWEAK, QUALITY_WEIGHT_ADJ, NEW_PATTERN,
        # ALLOCATION_RULE, SIGNAL_FILTER, REGIME_THRESHOLD
    strategy_family: str         # "orb", "vwap", "afmo", etc. — partition key
    strategy_id: str | None      # None for system-level experiments
    description: str             # "ORB Breakout: range_period 5→7"
    
    # Configuration diff
    baseline_config_hash: str
    candidate_config_hash: str
    config_diff: dict            # JSON diff of what changed
    
    # Individual evaluation
    result: MultiObjectiveResult
    confidence_tier: ConfidenceTier
    
    # Decision (individual or via cohort)
    decision: ExperimentDecision     # PROMOTED, REVERTED, PENDING_COHORT, PENDING_PAPER, PENDING_REVIEW
    decision_reason: str
    decided_at: datetime | None
    decided_by: str                  # "auto:pareto_dominant" | "auto:cohort_promoted" | 
                                     # "auto:kill_switch" | "human:steven"
```

**Storage design for scale:**

- **Partitioned by `(strategy_family, batch_id)`.** Each systematic search sweep writes to its own partition. Queries within a sweep are fast; cross-sweep queries use pre-computed aggregates.
- **Separate tables:** `experiments` (core metadata + decision), `experiment_results` (full MultiObjectiveResult JSON, keyed by experiment_id). This keeps the core table lightweight for status queries while full results are available on demand.
- **Pre-computed aggregate views:** Materialized on write via SQLite triggers.
  - `experiment_family_stats`: Per-family success rate, average improvement, experiment count.
  - `experiment_type_stats`: Per-type (PARAMETER_TWEAK, NEW_PATTERN, etc.) success rate. This is the meta-learning data source.
  - `experiment_batch_summary`: Per-batch best result, Pareto frontier size, promotion rate.
- **Archival policy:** Experiments older than 90 days with decision=REVERTED are moved to `experiments_archive` table. Aggregate stats are preserved. Full results are compressed.
- **Expected scale:** ~1M entries per systematic search sweep (Sprint 34+), ~10M total by Sprint 40. SQLite with proper indexing and partitioning handles this; if it doesn't, the partition-per-batch design makes migration to DuckDB straightforward.

#### 4.2 PromotionCohort

The primary unit of promotion is the **cohort**, not the individual experiment. This solves the paper validation bottleneck and enables ensemble-level evaluation.

```
PromotionCohort:
    # Identity
    cohort_id: ULID
    created_at: datetime
    
    # Contents
    experiment_ids: list[ULID]       # Experiments in this cohort
    strategy_ids: list[str]          # Strategies being added/modified
    cohort_type: CohortType
        # INDIVIDUAL           — Single experiment (backward-compatible with simple tweaks)
        # FAMILY_SWEEP         — Best candidates from a single-family systematic search
        # CROSS_FAMILY         — Candidates spanning multiple families
        # DISCOVERY_BATCH      — Overnight discovery pipeline output
    
    # Evaluation
    baseline_ensemble: EnsembleResult      # Current production ensemble WITHOUT these strategies
    candidate_ensemble: EnsembleResult     # Production ensemble WITH these strategies added
    improvement_verdict: ComparisonVerdict  # From evaluate_cohort_addition()
    
    # Promotion state
    stage: PromotionStage
    stage_history: list[StageTransition]   # Full audit trail
    
    # Simulated paper results (fast screening)
    simulated_paper_result: EnsembleResult | None
    simulated_paper_date_range: tuple[date, date] | None
    
    # Real paper results (final validation)
    paper_result: EnsembleResult | None
    paper_start_date: date | None
    paper_days_accumulated: int
    
    # Live monitoring
    live_start_date: date | None
    rolling_ensemble_result: EnsembleResult | None  # Updated daily
    underperformance_streak: int                     # Consecutive days below baseline
```

**Cohort formation rules:**
- Systematic search (Sprint 34+) produces a batch of candidates. The top N candidates from the Pareto frontier that collectively improve the ensemble are grouped into a cohort.
- Cohort size is configurable: default 20–50 strategies per cohort. Too small → cohort evaluation is noisy. Too large → revert cost is high.
- HIGH-confidence strategies may form INDIVIDUAL cohorts (size 1) for fast-track promotion.
- LOW and ENSEMBLE_ONLY strategies must be in a cohort of ≥10 for sufficient ensemble-level statistical power.

#### 4.3 PromotionPipeline (Cohort-Based)

```
Stage 1: BACKTEST_VALIDATED
    Gate: EnsembleResult shows improvement_verdict = DOMINATES or soft_dominance
          + no strategy has negative marginal_sharpe (deadweight check)
          + ensemble diversification_ratio ≥ 1.0 (adding strategies isn't concentrating risk)
          + all HIGH/MODERATE confidence strategies individually pass WFE > 0.3
    Auto-action: Queue for simulated paper
    
Stage 2: SIMULATED_PAPER
    Method: BacktestEngine on the most recent 20 trading days (data not used in 
            any training/selection). This takes minutes, not months.
    Gate: Simulated EnsembleResult confirms backtest-era improvement holds on recent data
          + Sharpe decay from backtest to simulated-paper < 50%
          + No strategy in cohort has catastrophic simulated-paper result (max drawdown > 2× backtest)
    Auto-action on PASS: Queue for real paper
    Auto-action on FAIL: Revert entire cohort, log per-strategy diagnostics
    Notification: ntfy.sh with simulated-paper summary
    
    WHY THIS STAGE EXISTS: It breaks the paper trading bottleneck. Simulated-paper
    filters out 80-90% of candidates in minutes. Only the survivors spend 20 real
    trading days in paper validation. At 500 candidates → 50 survivors → 2-3 cohorts
    → 2-3 concurrent paper slots × 20 days = 20 days total, not 8 years.
    
Stage 3: PAPER_ACTIVE
    Gate: Paper trading slot available (max 5 concurrent cohorts in paper)
    Auto-action: Deploy cohort config to paper environment
    Notification: ntfy.sh "Cohort COH-{id} ({n} strategies) deployed to paper: {description}"
    
Stage 4: PAPER_CONFIRMED (or REVERTED)
    Gate: Required paper days accumulated (configurable per cohort type):
          - INDIVIDUAL: 20 trading days
          - FAMILY_SWEEP: 15 trading days (ensemble provides statistical power)
          - CROSS_FAMILY: 20 trading days
          - DISCOVERY_BATCH: 15 trading days
    Evaluation: Compare paper EnsembleResult vs simulated-paper prediction
          + Paper EnsembleResult must show improvement vs current live baseline
          + Backtest-to-paper Sharpe decay < 40% (DEC-047 spirit)
          + No single strategy in cohort responsible for >30% of cohort P&L (concentration)
    Auto-action on PASS: Advance to live pending veto
    Auto-action on FAIL: Revert cohort, flag individual strategies for analysis
    Notification: ntfy.sh with full comparison report
    
Stage 5: LIVE_PENDING_VETO
    Gate: Configurable human veto window
          - INDIVIDUAL: 24 hours
          - FAMILY_SWEEP: 48 hours
          - CROSS_FAMILY: 72 hours
          - DISCOVERY_BATCH: 48 hours
    Notification: ntfy.sh "Cohort COH-{id} PASSED paper validation. 
                  Promoting to live in {veto_hours}h unless vetoed. {comparison_summary}"
    Human action: Reply "VETO COH-{id}" to block promotion
    Auto-action after veto window with no veto: Promote to live
    
Stage 6: LIVE_ACTIVE
    Continuous monitoring: Rolling 10-day EnsembleResult vs baseline
    Kill switch (cohort level): If rolling ensemble result is Pareto-dominated by 
                 baseline for 5 consecutive days → auto-revert entire cohort
    Kill switch (individual level): If any single strategy in cohort has marginal_sharpe 
                 < -0.5 for 10 consecutive days → remove that strategy, keep rest of cohort
    Notification on auto-revert: ntfy.sh "KILL SWITCH: Cohort COH-{id} reverted after 
                                 5-day ensemble underperformance. {comparison_summary}"
    Notification on individual removal: ntfy.sh "PRUNED: Strategy {id} removed from 
                                        Cohort COH-{id} (negative marginal Sharpe)"
    
Stage 7: STABLE (terminal success)
    Trigger: 30+ trading days in LIVE_ACTIVE without kill switch activation
    Cohort strategies are absorbed into the permanent ensemble.
    No longer tracked as experimental — they're production strategies.
    
Stage 8: REVERTED (terminal failure)
    Cohort archived with full history.
    Individual strategy diagnostics available for meta-learning.
    Strategies may be re-entered in future cohorts with different compositions.
```

**Individual promotion as special case:** A single parameter tweak with HIGH confidence can form an INDIVIDUAL cohort (size 1) and follow the same pipeline. The stages are identical; the evaluation just uses individual MultiObjectiveResult comparison instead of EnsembleResult. This maintains backward compatibility with simple improvements while the cohort path handles scale.

#### 4.4 ExperimentQueue + Background Worker

Designed for overnight autonomous operation from day one:

```
ExperimentQueue:
    # Queue entries
    queue: list[QueuedExperiment]
    
    # Worker state
    worker_status: WorkerStatus  # IDLE, RUNNING, PAUSED, ERROR
    current_experiment: ULID | None
    experiments_completed_today: int
    compute_time_today: timedelta

QueuedExperiment:
    experiment_id: ULID
    priority: int               # Lower = higher priority
    experiment_type: ExperimentType
    estimated_runtime: timedelta
    queued_at: datetime
    source: str                 # "learning_loop" | "systematic_search" | "discovery_pipeline" | "manual"
```

**Worker behavior:**
- During market hours (9:30 AM – 4:00 PM ET / 3:30 PM – 10:00 PM SAST): Worker is **paused**. CPU is reserved for live trading, data processing, and paper validation.
- During off-market hours (4:00 PM – 9:30 AM ET / 10:00 PM – 3:30 PM SAST): Worker processes the queue. Each item = one BacktestEngine run producing a MultiObjectiveResult.
- Priority ordering: `learning_loop` > `systematic_search` > `discovery_pipeline` > `manual`. Within same source, FIFO.
- The worker is a simple asyncio task that drains the queue. Sophisticated scheduling (parallelism, cloud burst) comes in Sprint 31 (Parallel Sweep Infrastructure). For now, sequential is fine — BacktestEngine on 7 strategies × 3 years × 1 parameter set takes ~2–5 minutes per run. At 5 min/run × 16.5 hours overnight = ~200 experiments per night. That's sufficient for Learning Loop and early systematic search.

**Why build this in Sprint 32.5 instead of Sprint 41:** The queue/worker pattern is simple infrastructure (~200 lines). But retrofitting it later means every intermediate sprint (33, 34, 35) builds its own ad-hoc approach to "run experiments in the background." Building the queue once means Sprint 33 (Statistical Validation) and Sprint 34 (Systematic Search) get overnight compute for free.

#### 4.5 Notification Integration

Extends the existing ntfy.sh integration (DEC-279) with experiment-specific channels:

- `argus-experiments`: All experiment lifecycle events — stage transitions, comparison summaries, veto windows, kill switch activations
- Messages are structured enough to be parseable (for future automation) but readable on a phone
- Veto mechanics: reply "VETO COH-{id}" to the veto notification. Checked via ntfy polling or a simple webhook endpoint.

#### 4.6 API Endpoints

```
# Experiment queries
GET  /api/v1/experiments                         # List (filterable by type, family, stage, batch, date)
GET  /api/v1/experiments/{id}                     # Full experiment detail
GET  /api/v1/experiments/{id}/comparison           # Side-by-side baseline vs candidate
GET  /api/v1/experiments/batch/{batch_id}          # All experiments in a batch
GET  /api/v1/experiments/batch/{batch_id}/frontier  # Pareto frontier for a batch

# Cohort management
GET  /api/v1/cohorts                              # List active cohorts
GET  /api/v1/cohorts/{id}                         # Full cohort detail with ensemble evaluation
GET  /api/v1/cohorts/{id}/ensemble                 # Current ensemble result
POST /api/v1/cohorts/{id}/veto                     # Human veto (Stage 5)
POST /api/v1/cohorts/{id}/force-revert             # Force revert at any stage
POST /api/v1/cohorts/{id}/remove-strategy/{sid}    # Remove one strategy from cohort

# Queue management  
GET  /api/v1/experiments/queue                     # Current queue state
POST /api/v1/experiments/queue/pause                # Pause worker
POST /api/v1/experiments/queue/resume               # Resume worker

# Meta-learning
GET  /api/v1/experiments/meta/success-rates         # Success rate by experiment type
GET  /api/v1/experiments/meta/family-stats           # Per-family aggregate statistics
GET  /api/v1/experiments/meta/improvement-trends     # Rolling improvement rate over time

# Promotion pipeline
GET  /api/v1/promotion/pipeline                     # All cohorts in pipeline by stage
GET  /api/v1/promotion/slots                        # Paper/live slot utilization
```

No frontend pages in this sprint — the Research Console (Sprint 31) and its evolution in Sprint 33+ will consume these endpoints. The Copilot (SystemContextBuilder) gains experiment context for natural language queries like "how are my experiments doing?" and "what's in the paper validation queue?"

### File Structure

```
argus/
├── analytics/
│   ├── experiment_registry.py     # ExperimentRegistry, Experiment model, partitioned SQLite
│   ├── experiment_queue.py        # ExperimentQueue, QueuedExperiment, background worker
│   ├── promotion_pipeline.py      # PromotionPipeline, PromotionCohort, stage gates
│   ├── promotion_config.py        # Pydantic models for experiment_pipeline.yaml
│   └── experiment_aggregates.py   # Pre-computed aggregate views, meta-learning queries
├── config/
│   └── experiment_pipeline.yaml   # Concurrency limits, veto windows, kill switch thresholds,
│                                  # cohort size defaults, worker schedule, archival policy
├── api/
│   └── experiment_routes.py       # REST endpoints (experiments, cohorts, queue, meta, pipeline)
├── intelligence/
│   └── learning.py                # Modified: Learning Loop V1 writes experiments to registry
```

### Session Breakdown (Compaction Risk Scoring)

| Session | Scope | Files Created | Files Modified | Context Reads | Tests | Integration | Score |
|---------|-------|---------------|----------------|---------------|-------|-------------|-------|
| S1 | Experiment model + ExperimentRegistry + partitioned SQLite schema + CRUD | 2 | 0 | 3 | 2 | 0 | **9** |
| S2 | Aggregate views (triggers + materialized stats) + meta-learning queries | 1 | 1 | 2 | 2 | 1 | **9** |
| S3 | PromotionCohort model + PromotionPipeline stages 1–2 (backtest → simulated paper) | 2 | 1 | 3 | 2 | 1 | **11** |
| S4 | Pipeline stages 3–5 (paper active → confirmed → veto window) + ntfy integration | 0 | 3 | 2 | 2 | 2 | **11** |
| S5 | Pipeline stages 6–8 (live active + kill switches + stable/reverted) | 0 | 2 | 2 | 2 | 2 | **10** |
| S6 | ExperimentQueue + background worker + market-hours-aware scheduling | 1 | 2 | 2 | 2 | 1 | **10** |
| S7 | API endpoints (experiments, cohorts, queue, meta, pipeline) + config wiring | 1 | 3 | 3 | 2 | 1 | **12** |
| S8 | Integration tests: full lifecycle (register → cohort → simulated paper → paper → promote → kill switch → revert) | 0 | 2 | 2 | 3 | 2 | **11** |

All sessions ≤ 13. **Total: 8 sessions, ~4 days.**

### Tests: ~90 new

- ExperimentRegistry CRUD + partitioned queries
- Aggregate view correctness (pre-computed stats match live queries)
- PromotionCohort formation rules (min/max size, confidence tier requirements)
- Pipeline stage gates (each stage, pass and fail paths, per cohort type)
- Simulated-paper screening (BacktestEngine on recent data → EnsembleResult)
- Kill switch activation (cohort-level: 5-day underperformance; individual-level: negative marginal Sharpe)
- Veto window mechanics (veto before expiry, auto-promote after expiry, force revert, per-type window durations)
- Concurrency limit enforcement (6th cohort blocked)
- ExperimentQueue ordering (priority, FIFO within priority)
- Background worker scheduling (pauses during market hours, resumes after)
- Notification formatting (stage transitions, veto requests, kill switch)
- API endpoint coverage
- Integration: Learning Loop → Registry → Cohort → Pipeline → ntfy full lifecycle

### Dependencies

- Sprint 27.5 (Evaluation Framework) — `MultiObjectiveResult`, `EnsembleResult`, and comparison API are consumed heavily
- Sprint 32 (Parameterized Templates) — templates define the parameter space that experiments vary
- Sprint 28 (Learning Loop V1) — retrofitted to write experiments to the registry (small modification)
- Existing ntfy.sh integration (DEC-279)
- Existing BacktestEngine (Sprint 27) — used for simulated-paper screening and queue processing

### What This Does NOT Do

- No Research Console UI for experiments or cohorts (Sprint 31 already planned; experiment views added incrementally)
- No automated experiment *generation* (Sprint 34 Systematic Search and Sprint 41 Continuous Discovery handle this — they produce QueuedExperiments, this sprint processes them)
- No FDR correction (Sprint 33 — but the registry stores p_values once Sprint 33 populates them)
- No meta-learning *automation* (the registry enables meta-learning queries and the aggregate views make them fast; automated "learn what kinds of experiments work" is a Sprint 40+ concern)
- No parallel BacktestEngine execution (Sprint 31 Parallel Sweep Infrastructure — the queue worker runs sequential for now, ~200 experiments/night, sufficient for Sprints 28–33)

---

## 5. Roadmap Impact

### Updated Build Track Queue

~~26~~ ✅ → ~~27~~ ✅ → **21.6** → **27.5 (NEW)** → 28 → 29–31 → 32 → **32.5 (NEW)** → 33 → 34 → 35–41

### Sprint Renumbering

No renumbering needed. The `.5` convention is established.

### Phase Boundary Changes

- **Phase 6** gains Sprint 27.5 (between 21.6 and 28). Net: +2–3 days.
- **Phase 7** gains Sprint 32.5 (between 32 and 33). Net: +4 days, but Sprint 33 scope decreases (eval framework + experiment storage already exist).
- Total roadmap extension: ~6–7 days. Recouped by de-risking Sprints 28, 33, 34, 40, and 41, and by avoiding a rearchitecture sprint at Phase 9.

### Summary Timeline (Revised)

| Phase | Sprints | Duration | Δ vs Current |
|-------|---------|----------|---|
| 6: Strategy Expansion | 21.6, **27.5**, 28, 29–31 | ~2.5–3.5 weeks | +2–3 days |
| 7: Infrastructure Unification | 32, **32.5** | ~1.5–2 weeks | +1–2 days (Sprint 33 shrinks, partially offsetting) |
| 8: Controlled Experiment | 33–35 | ~2–2.5 weeks | Potentially shorter (infra already built) |
| 9–10 | 36–41 | ~5.5–7.5 weeks | Potentially shorter (promotion pipeline already built) |

### What Changes in Existing Sprints

| Sprint | Change |
|--------|--------|
| **21.6** (Re-Validation) | No change. Produces ad-hoc results. Sprint 27.5 retroactively structures them. |
| **28** (Learning Loop V1) | Consumes `MultiObjectiveResult`, `EnsembleResult`, and comparison API from 27.5. Scope *decreases* — the PostTradeAnalyzer doesn't need to invent its own metrics framework. Writes experiments to registry once 32.5 exists (or to a local JSON log with same schema until then). |
| **31** (Parallel Sweep Infrastructure) | ExperimentQueue already exists. Sprint 31 upgrades the worker from sequential to multiprocessing. Queue semantics are unchanged. |
| **33** (Statistical Validation) | Scope *decreases significantly*. FDR correction and three-way split remain, but evaluation framework, experiment storage, and aggregate views already exist. Sprint 33 focuses purely on statistical methods. |
| **34** (ORB Systematic Search) | Writes every candidate to ExperimentRegistry. Best candidates auto-grouped into PromotionCohorts. Simulated-paper screens in minutes. Survivors enter real paper. The "UI experience during the experiment" section of the roadmap gains experiment lifecycle tracking and cohort pipeline visualization. Overnight BacktestEngine queue handles the compute. |
| **38** (Ensemble Orchestrator V2) | EnsembleResult and marginal contribution analysis already exist from 27.5. Orchestrator V2 consumes these directly — doesn't need to build its own ensemble evaluation. |
| **40** (Learning Loop V2) | Scope *decreases*. "Automatic retirement" is `identify_deadweight()` from 27.5 + kill switch from 32.5. "Automatic promotion" is the PromotionPipeline. Sprint 40 focuses on recalibration frequency, ensemble-level adaptation, and Synapse lifecycle visualization. |
| **41** (Continuous Discovery) | Generates experiments and writes them to ExperimentQueue. The registry and promotion pipeline handle everything downstream. Sprint 41 focuses on hypothesis generation (Claude API), overnight scheduling, and morning discovery briefs. |

---

## 6. Scale Analysis

### Paper Validation Throughput

**Without this amendment (current roadmap):**
- Sprint 34 produces ~200 validated candidates
- At 5 individual slots × 20 days each: 200/5 × 20 = 800 trading days ≈ 3.2 years
- Sprint 36–37 produces ~500 more: additional 2,000 trading days ≈ 8 years

**With this amendment:**
- Sprint 34 produces ~200 candidates
- Simulated-paper screens to ~30 survivors (minutes, not days)
- 30 strategies → 1–2 cohorts × 15–20 paper days = 15–20 trading days total
- Sprint 36–37 produces ~500 more → simulated-paper screens to ~80 → 2–4 cohorts × 15–20 days = ~40 trading days

**Net improvement: 3+ years → 2 months.**

### Overnight Compute Capacity

Sequential worker at ~5 min per BacktestEngine run × 16.5 off-market hours = **~200 experiments per night**.

| Sprint | Experiments Needed | Nights Required |
|--------|-------------------|-----------------|
| 28 (Learning Loop) | ~20–50 weight variations | <1 night |
| 33 (Statistical Validation) | ~500 FDR framework tests | 2–3 nights |
| 34 (ORB Systematic Search) | ~50,000 focused candidates | ~250 nights (needs Sprint 31 parallelism) |
| 36–37 (Cross-Family) | ~100,000+ | ~500 nights (definitely needs parallelism + cloud burst) |

Sprint 31 (Parallel Sweep Infrastructure) upgrades to multiprocessing — 8 cores × 200/night = **~1,600 experiments/night**. Cloud burst (32-core instance) = **~6,400/night** = Sprint 34's 50,000 in ~8 nights. This is feasible.

### Registry Scale

| Milestone | Experiment Count | Storage (est.) |
|-----------|-----------------|----------------|
| Sprint 28 (Learning Loop) | ~100 | <1 MB |
| Sprint 33 (Statistical Validation) | ~1,000 | ~5 MB |
| Sprint 34 (ORB Systematic Search) | ~50,000 | ~250 MB |
| Sprint 36–37 (Cross-Family) | ~200,000 | ~1 GB |
| Sprint 41 (Continuous Discovery, 6 months) | ~1,000,000+ | ~5 GB |

SQLite handles this with proper indexing and the partitioned design. The aggregate views keep query performance constant regardless of table size. If needed, DuckDB migration is straightforward (same partition scheme, analytical query engine).

---

## 7. The Autoresearch Mapping

| Autoresearch Concept | Chess Domain | ARGUS Equivalent | Sprint |
|---------------------|--------------|------------------|--------|
| Evaluation function | ELO rating | `MultiObjectiveResult` + `EnsembleResult` + Pareto dominance | **27.5** |
| Keep/revert decision | ELO improved → keep | `compare()` / `evaluate_cohort_addition()` → PROMOTED or REVERTED | **27.5** |
| Experiment log | Git history | `ExperimentRegistry` (partitioned, aggregate views) | **32.5** |
| Automated promotion | Immediate (single process) | `PromotionPipeline` (simulated paper → real paper → veto → live) | **32.5** |
| Kill switch | Revert if ELO drops | Cohort kill switch (5-day) + individual pruning (negative marginal Sharpe) | **32.5** |
| Background compute | Run games overnight | `ExperimentQueue` + market-hours-aware worker | **32.5** |
| Environment stationarity | Chess rules don't change | Regime-conditional evaluation + regime robustness check | **27.5** |
| Overfitting protection | N/A (chess is deterministic) | WFE > 0.3, confidence tiers, FDR (Sprint 33), simulated-paper screening | **27.5** + **32.5** + 33 |
| Scale | One model, one metric | 1000+ micro-strategies, ensemble-level evaluation, cohort promotion | **27.5** + **32.5** |
| Meta-learning | N/A | Experiment type success rates, per-family aggregate views | **32.5** (data), 40+ (automation) |

---

## 8. Decision Checklist

### For Sprint 21.6 Planning (Now)

- [ ] **Adopt Amendment A (Sprint 27.5)?** If yes, insert after 21.6 in the build queue.
- [ ] **Adopt Amendment B (Sprint 32.5)?** If yes, insert after Sprint 32. Can be decided later (Phase 7 planning) but flagging now for roadmap awareness.
- [ ] **Reserve DEC range.** Suggest DEC-357–375 for Sprint 27.5, DEC-376+ for 32.5.

### For Sprint 28 Planning

- [ ] Confirm Learning Loop V1 consumes `MultiObjectiveResult` and `EnsembleResult` from 27.5 rather than building ad-hoc evaluation.
- [ ] Decide: does Sprint 28 write to ExperimentRegistry? (If 32.5 doesn't exist yet, use a simple local JSON log with same schema for forward compatibility.)

### For Phase 7 Gate

- [ ] Confirm Sprint 32.5 scope. Adjust cohort sizes, veto windows, and kill switch thresholds based on paper trading experience.
- [ ] Review overnight compute capacity — is sequential worker sufficient for Sprint 33, or should Sprint 31 (Parallel Sweep) be prioritized?

---

## 9. Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Pareto dominance too conservative (most changes INCOMPARABLE) | Medium | Learning Loop can't distinguish improvements | `soft_dominance()` with configurable tolerance bands. Empirically tune tolerance after Sprint 28. |
| Kill switch triggers too aggressively in volatile markets | Medium | Good cohorts reverted prematurely | Regime-aware thresholds: relax during regime transitions. Track kill-switch-then-recovery rate in meta-learning. |
| Simulated-paper screening filters out good candidates | Medium | 20-day recent data may not represent all regimes | Run simulated-paper on multiple recent 20-day windows. Flag candidates that pass some windows but fail others for extended real-paper. |
| Ensemble evaluation masks individual strategy problems | Low-Medium | One toxic strategy hides behind ensemble improvement | Individual kill switch (negative marginal Sharpe for 10 days) catches this. Post-revert analysis decomposes cohort performance. |
| ExperimentQueue backlog grows faster than worker capacity | Medium at Sprint 34+ | Experiments take days/weeks to process | Sprint 31 (Parallel Sweep) is the mitigation. Queue has priority ordering to process highest-value experiments first. |
| Cohort composition effects (strategies interact) | Low | Strategy that works alone fails in ensemble, or vice versa | EnsembleResult captures interaction via `marginal_contributions` and `tail_correlation`. Cohort-level evaluation inherently tests interactions. |
| SQLite at 1M+ entries degrades | Low | Query latency increases | Partitioned design isolates hot data. Aggregate views are pre-computed. DuckDB migration path is clean. |

---

## 10. What This Makes Possible

With both amendments adopted, here's the ARGUS improvement loop at steady state (post-Sprint 34):

```
┌──────────────────────────────────────────────────────────────────────┐
│                    CONTINUOUS IMPROVEMENT LOOP                        │
│                                                                      │
│  OVERNIGHT (10 PM – 3:30 PM SAST)          MARKET HOURS (3:30-11 PM)│
│  ┌─────────────────────────────┐           ┌───────────────────────┐ │
│  │  ExperimentQueue processes: │           │  Live ensemble trades  │ │
│  │  • Parameter variations     │           │  Paper cohorts trade   │ │
│  │  • Weight adjustments       │           │  Kill switches monitor │ │
│  │  • New pattern candidates   │           │  Rolling results update│ │
│  │  • Discovery hypotheses     │           │  Veto notifications    │ │
│  │                             │           │  sent to phone         │ │
│  │  ~200/night (sequential)    │           │                        │ │
│  │  ~6,400/night (cloud burst) │           │                        │ │
│  └──────────┬──────────────────┘           └───────────┬───────────┘ │
│             │                                          │             │
│             ▼                                          ▼             │
│  ┌──────────────────────┐              ┌───────────────────────────┐ │
│  │  Evaluate             │              │  Monitor + Kill Switch    │ │
│  │  MultiObjectiveResult │              │  EnsembleResult vs        │ │
│  │  + regime breakdown   │              │  baseline (daily)         │ │
│  │  + confidence tier    │              │  Prune negative-marginal  │ │
│  └──────────┬────────────┘              │  strategies individually  │ │
│             │                           └───────────┬───────────────┘ │
│             ▼                                       │                │
│  ┌──────────────────────┐                           │                │
│  │  Register + Cohort   │◀──────────────────────────┘                │
│  │  ExperimentRegistry  │                                            │
│  │  (partitioned, agg   │──────────────────────────┐                 │
│  │   views, meta-learn) │                          │                 │
│  └──────────┬───────────┘                          ▼                 │
│             │                           ┌───────────────────────────┐ │
│             ▼                           │  Meta-Learn               │ │
│  ┌──────────────────────┐               │  "Parameter tweaks in ORB │ │
│  │  Promote Pipeline    │               │   family succeed 34% of   │ │
│  │  Simulated Paper     │               │   the time. New patterns  │ │
│  │  → Real Paper        │               │   succeed 12%. Focus on   │ │
│  │  → Veto Window       │               │   parameter tweaks."      │ │
│  │  → Live              │               └───────────────────────────┘ │
│  │  → Stable (absorbed) │                                            │
│  └──────────────────────┘                                            │
│                                                                      │
│  The system gets better at trading AND better at getting better.      │
└──────────────────────────────────────────────────────────────────────┘
```

Every component that generates candidates feeds into the same evaluation → registry → cohort → promotion pipeline. Hyper-specialized micro-strategies are validated at ensemble level. The system runs experiments while you sleep and sends you a notification when something's ready for your review. You veto or don't, and ARGUS keeps evolving.

This is autoresearch for trading — with ensemble-scale evaluation, multi-stage validation, regime conditioning, and the three safety layers (tiered confidence, simulated-paper screening, human veto) that financial markets demand.

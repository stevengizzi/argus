# ARGUS Roadmap Amendment Proposal: Intelligence Architecture

> **Status:** ADOPTED (partial) — Sprint 27.6 (RegimeVector) and Sprint 27.7 (Counterfactual Engine) shipped. Sprint 33.5 (Adversarial Stress Testing) PENDING; DEC 396–402 reserved. See DEC-358 for amendment ratification.
> **Adoption note:** Header status updated 2026-04-21 via audit FIX-15 back-annotation. Preserved in place (not archived) because this document contains fuller decision rationale than the terser sprint-history entries.
> **Author:** Claude.ai strategic planning conversation, March 23, 2026
> **Context:** Sprint 27 (BacktestEngine Core) complete. The Experiment Infrastructure amendment (companion document) builds the evaluate → track → promote loop. This amendment builds the **six intelligence layers** that feed that loop with high-quality data, protect it from tail risks, generate targeted hypotheses, and make the system stronger under stress.
> **Roadmap version:** v2.0 (March 22, 2026)
> **Companion:** `roadmap-amendment-experiment-infrastructure.md` (Sprints 27.5 + 32.5)
> **Decision point:** Dedicated strategic conversation (before Sprint 21.6 planning)

---

## 1. Executive Summary

The Experiment Infrastructure amendment gives ARGUS the discipline to evaluate and promote improvements. But discipline without intelligence is brute force — the system would run random experiments hoping to stumble on something better. This amendment adds the **six intelligence layers** that make experimentation targeted, evaluation accurate, and failure productive.

| # | Layer | What It Does | Sprint | Duration |
|---|-------|-------------|--------|----------|
| 1 | **Regime Intelligence** | Multi-factor regime vectors replace crude SPY-only classification | **27.6** (new) | ~3 days |
| 2 | **Counterfactual Engine** | Tracks theoretical outcomes of every rejected signal — learns from trades not taken | **27.7** (new) | ~2 days |
| 3 | **Execution Quality Feedback** | Measures real vs expected fills, feeds corrected slippage into BacktestEngine | Logging from **21.6**, feedback in **27.5** mod | ~0 days (additive) |
| 4 | **Adversarial Stress Testing** | Tests strategies against crisis scenarios, correlation spikes, liquidity droughts | **33.5** (new) | ~3 days |
| 5 | **Hypothesis Generation Design** | Architecture for 4 candidate generation methods — niche ID, mutation, literature mining, anomaly detection | Design doc at **32.5**, implementation **41** | ~0 days (design only) |
| 6 | **Anti-Fragility Integration** | Loss-driven queue priority, post-mortem automation, accelerated experimentation during drawdowns | Mods to **27.5** + **32.5** | ~0.5 days (additive) |

**New sprints:** 3 (27.6, 27.7, 33.5)
**Net roadmap extension:** ~8 days
**Combined with Experiment Infrastructure amendment:** ~14–15 days total extension

### Why These Six — Not More, Not Fewer

Each layer addresses a specific failure mode of the experiment loop:

| Without This Layer | The Experiment Loop... |
|-------------------|----------------------|
| Regime Intelligence | ...optimizes against wrong labels. A "trending" label on a choppy day means every evaluation that day is miscategorized. |
| Counterfactual Engine | ...learns from dozens of trades/day instead of hundreds of data points/day. 90% of learning signal is discarded. |
| Execution Quality | ...backtests with fantasy slippage. Strategies that look profitable in simulation lose money in reality. |
| Adversarial Stress Testing | ...promotes strategies that work in normal conditions but blow up in crises. |
| Hypothesis Generation Design | ...runs random experiments. Untargeted search in a vast parameter space is computationally wasteful. |
| Anti-Fragility | ...improves at a constant rate regardless of urgency. The system should improve fastest when it's performing worst. |

---

## 2. The Intelligence Architecture — How It Connects

```
                          DATA QUALITY FOUNDATION
                    ┌─────────────────────────────────┐
                    │     Regime Intelligence (27.6)   │
                    │  Multi-factor regime vectors     │
                    │  Breadth · Correlation · Sector  │
                    │  Volatility structure · Intraday │
                    └──────────┬──────────────────────┘
                               │ Accurate labels flow into ▼ everything
              ┌────────────────┼─────────────────────────┐
              ▼                ▼                          ▼
   ┌──────────────────┐ ┌────────────────┐  ┌──────────────────────┐
   │  Counterfactual   │ │ Execution      │  │  Adversarial         │
   │  Engine (27.7)    │ │ Quality (21.6+)│  │  Stress Testing      │
   │                   │ │                │  │  (33.5)              │
   │  "What would have │ │ "Are backtests │  │  "What kills this    │
   │   happened?"      │ │  realistic?"   │  │   in a crisis?"      │
   │                   │ │                │  │                      │
   │  Learns from the  │ │ Corrects the   │  │  Gates the promotion │
   │  90% of signals   │ │ simulation     │  │  pipeline            │
   │  we don't trade   │ │ accuracy gap   │  │                      │
   └────────┬─────────┘ └───────┬────────┘  └───────────┬──────────┘
            │                   │                        │
            │    More data      │  Better eval           │  Safety gate
            │    points         │  accuracy              │
            ▼                   ▼                        ▼
   ┌─────────────────────────────────────────────────────────────────┐
   │              Experiment Infrastructure (27.5 + 32.5)            │
   │  MultiObjectiveResult · EnsembleResult · ExperimentRegistry    │
   │  PromotionCohort · PromotionPipeline · ExperimentQueue         │
   └───────────────────────────┬─────────────────────────────────────┘
                               │
            ┌──────────────────┼──────────────────┐
            ▼                                     ▼
   ┌──────────────────────┐           ┌──────────────────────────┐
   │  Hypothesis           │           │  Anti-Fragility (32.5   │
   │  Generation (41)      │           │  integration)            │
   │                       │           │                          │
   │  Niche identification │           │  Loss-driven priority    │
   │  Pattern mutation     │           │  Post-mortem automation  │
   │  Literature mining    │           │  Drawdown acceleration   │
   │  Anomaly detection    │           │                          │
   │                       │           │  "Get better faster      │
   │  Designed at 32.5     │           │   when things are bad"   │
   │  Built at 41          │           │                          │
   └──────────────────────┘           └──────────────────────────┘
```

The architecture has a clear dependency flow: Regime Intelligence is foundational (everything downstream depends on accurate regime labels). Counterfactual Engine and Execution Quality improve data volume and data accuracy respectively. Adversarial Stress Testing adds a safety gate to the promotion pipeline. Hypothesis Generation and Anti-Fragility make the experiment loop smarter and more responsive.

---

## 3. Layer 1: Regime Intelligence — Sprint 27.6

### The Problem

The current `RegimeClassifier` (`argus/core/regime.py`) uses SPY-only indicators: price vs SMA-20/SMA-50, 20-day realized volatility, and 5-day ROC. It outputs a single `MarketRegime` enum from 5 categories.

This is inadequate for three reasons:

1. **Single-instrument blindness.** SPY can be flat while underneath, growth stocks are crashing and value stocks are rallying. Sector rotation is invisible to an SPY-only classifier. ARGUS strategies trade individual stocks, not SPY — the market regime for a tech-heavy watchlist is different from the market regime for healthcare.

2. **Scalar classification loses information.** A day classified as "BULLISH_TRENDING" could mean steady grind-up (good for momentum) or explosive rally after gap-up (good for ORB, bad for mean-reversion). The single label discards the nuance that strategies need.

3. **No intraday awareness.** Regime is computed from daily bars and reclassified every 300 seconds (DEC-346). But the character of a trading day is often apparent within the first 30 minutes. A strategy evaluating setups at 10:15 AM should know whether this is shaping up as a trending day or a chop day based on the opening action, not yesterday's close.

### The Solution: Regime Vectors

Replace the single `MarketRegime` enum with a **multi-dimensional `RegimeVector`** that captures the full state of the market environment:

```
RegimeVector:
    # Timestamp
    computed_at: datetime
    
    # Trend dimension (existing, upgraded)
    trend_score: float          # -1.0 (strong bear) to +1.0 (strong bull), continuous
    trend_conviction: float     # 0.0–1.0 (how confident is the trend signal?)
    
    # Volatility dimension (existing, upgraded)
    volatility_level: float     # Annualized realized vol (continuous, not bucketed)
    volatility_direction: float # -1.0 (falling) to +1.0 (rising) — vol term structure proxy
    
    # Breadth dimension (NEW)
    breadth_score: float        # -1.0 (narrow/declining) to +1.0 (broad/advancing)
    breadth_thrust: bool        # True if >80% of universe above 20-day MA (rare, bullish signal)
    
    # Correlation dimension (NEW)
    average_correlation: float  # 0.0–1.0 — mean pairwise correlation in trading universe
    correlation_regime: str     # "dispersed" (<0.3), "normal" (0.3–0.6), "concentrated" (>0.6)
    
    # Sector dimension (NEW)
    sector_rotation_phase: str  # "risk_on", "risk_off", "mixed", "transitioning"
    leading_sectors: list[str]  # Top 3 sectors by relative strength
    lagging_sectors: list[str]  # Bottom 3
    
    # Intraday dimension (NEW — computed from live data during market hours)
    opening_drive_strength: float | None   # First 5-min bar range / ATR. None pre-market.
    first_30min_range_ratio: float | None  # First 30-min range / expected daily range. None early.
    vwap_slope: float | None               # VWAP slope direction. Positive = trending up.
    intraday_character: str | None         # "trending", "choppy", "reversal", "breakout". None pre-market.
    
    # Composite (backward-compatible)
    primary_regime: MarketRegime    # Still computed for existing consumers
    regime_confidence: float        # 0.0–1.0 — how well does the single label capture reality?
```

**Backward compatibility:** Every existing consumer of `MarketRegime` continues to work — `RegimeVector.primary_regime` provides the same enum. But new consumers (Quality Engine, Learning Loop, experiment evaluation, micro-strategy operating windows) can use the full vector.

**Strategy operating windows as regime regions:** A hyper-specialized micro-strategy defines its operating conditions as a region in regime space, not a single regime label:

```yaml
# Example: ORB variant that only fires in specific conditions
operating_conditions:
  trend_score: [0.2, 1.0]           # Moderate to strong bullish
  volatility_level: [0.10, 0.25]    # Low-to-normal vol (not crisis)
  breadth_score: [0.0, 1.0]         # Neutral to broad participation
  average_correlation: [0.0, 0.5]   # Dispersed market (stock-picking works)
  intraday_character: ["trending"]   # Trending day character
```

This is what enables 1000 micro-strategies that each fire rarely but with high conviction. Each micro-strategy occupies a narrow niche in regime space. The regime vector tells each strategy whether it's in its niche.

### Data Sources

| Dimension | Source | Cost | Latency |
|-----------|--------|------|---------|
| Trend | SPY daily bars via FMP (existing) | $0 | Daily |
| Volatility level | SPY daily bars (existing) | $0 | Daily |
| Volatility direction | SPY 5-day vs 20-day realized vol ratio | $0 | Daily |
| Breadth | Computed from Databento feed: count symbols above/below 20-bar MA | $0 (existing sub) | Real-time |
| Correlation | Rolling 20-day pairwise correlation of top 50 Databento symbols | $0 (existing sub) | Daily (overnight compute) |
| Sector rotation | FMP sector performance endpoint (`/stable/sector-performance`) | $0 (existing plan) | Pre-market |
| Intraday character | Computed from live Databento candles: SPY first-bar range, VWAP slope | $0 (existing sub) | Real-time |

**Key insight:** No new data subscriptions required. Everything computes from existing Databento feed + FMP Starter plan. The breadth and intraday dimensions use the live Databento stream that's already flowing through the system.

### Implementation Approach

The current `RegimeClassifier` is clean and well-structured (327 lines). The upgrade path:

1. **`RegimeVector` dataclass** replaces `RegimeIndicators` as the primary output. `RegimeIndicators` remains as an internal intermediate (SPY-specific inputs).
2. **`BreadthCalculator`** — lightweight accumulator that tracks % of Databento symbols above their 20-bar rolling MA. Updated on each candle. Taps into the DatabentoDataService event stream *after* the fast-path discard (only viable symbols counted).
3. **`CorrelationTracker`** — maintains a rolling 20-day pairwise correlation matrix for the top N symbols by volume. Computed overnight (not real-time — too expensive). Stored in `data/regime_correlation.db`.
4. **`SectorRotationAnalyzer`** — fetches FMP sector performance during pre-market. Classifies rotation phase based on relative strength rankings.
5. **`IntradayCharacterDetector`** — analyzes first 5-min and first 30-min bars to classify intraday character. Updates at 9:35, 10:00, and 10:30 AM ET. Uses SPY candles from Databento.
6. **`RegimeClassifierV2`** — composes all of the above. Produces `RegimeVector`. Backward-compatible `classify()` method still returns `MarketRegime`.

### File Structure

```
argus/
├── core/
│   ├── regime.py              # Modified: RegimeClassifierV2, RegimeVector, backward-compatible
│   ├── breadth.py             # NEW: BreadthCalculator — live breadth from Databento stream
│   ├── correlation.py         # NEW: CorrelationTracker — overnight pairwise correlation
│   ├── sector_rotation.py     # NEW: SectorRotationAnalyzer — FMP sector performance
│   └── intraday_character.py  # NEW: IntradayCharacterDetector — first-bar analysis
├── config/
│   └── regime.yaml            # NEW: Regime Intelligence configuration
```

### Session Breakdown (Compaction Risk Scoring)

| Session | Scope | Files Created | Files Modified | Context Reads | Tests | Integration | Score |
|---------|-------|---------------|----------------|---------------|-------|-------------|-------|
| S1 | RegimeVector dataclass + backward-compatible RegimeClassifierV2 shell + config | 1 | 2 | 3 | 2 | 0 | **10** |
| S2 | BreadthCalculator + DatabentoDataService tap integration | 1 | 2 | 3 | 2 | 1 | **11** |
| S3 | CorrelationTracker + overnight compute task + SQLite persistence | 1 | 1 | 2 | 2 | 1 | **9** |
| S4 | SectorRotationAnalyzer (FMP) + IntradayCharacterDetector (SPY candles) | 2 | 1 | 2 | 2 | 1 | **10** |
| S5 | Full RegimeClassifierV2 integration: compose all dimensions into RegimeVector + Orchestrator wiring + strategy operating_conditions YAML support | 0 | 3 | 3 | 2 | 2 | **12** |
| S6 | Integration tests + Observatory regime dimension visualization (extend existing Session Vitals bar) | 0 | 2 | 2 | 3 | 2 | **11** |

All sessions ≤ 13. **Total: 6 sessions, ~3 days.**

### Tests: ~70 new

- RegimeVector construction and serialization
- Backward compatibility (RegimeClassifierV2.classify() returns same MarketRegime for same inputs)
- BreadthCalculator accumulation (add symbols, remove symbols, threshold crossings)
- CorrelationTracker (known correlation matrices, edge cases: single symbol, all identical)
- SectorRotationAnalyzer (risk-on detection, risk-off detection, transition)
- IntradayCharacterDetector (trending, choppy, reversal, breakout patterns from test candles)
- Full composition: all dimensions → RegimeVector → primary_regime derivation
- Operating conditions matching: strategy YAML region vs RegimeVector → active/inactive
- Integration: live Databento candles → BreadthCalculator → RegimeVector update

### Dependencies

- Sprint 27.5 (Evaluation Framework) — `RegimeMetrics` in `MultiObjectiveResult` will use RegimeVector dimensions. Ideally 27.5 is designed with RegimeVector in mind even if 27.6 builds it after.
- Databento feed (existing, no changes)
- FMP Starter plan (existing, sector performance endpoint)
- No frontend sprint — Observatory gains regime dimensions in session vitals (small addition in S6)

### What This Does NOT Do

- No VIX futures term structure (requires additional data subscription — deferred to post-revenue)
- No real-time correlation (computed overnight only — real-time would require O(N²) on every candle)
- No automatic strategy deactivation based on regime (the Orchestrator already handles allowed_regimes; this sprint enriches the data, not the decision logic)
- No machine-learned regime classifier (V2 is still rules-based; ML regime classification is a Sprint 40+ concern if the rules-based approach proves insufficient)

### What Changes in Sprint 27.5

If both amendments are adopted, Sprint 27.5's `RegimeMetrics` should be designed to store per-dimension breakdowns (breadth, correlation, sector) in addition to per-MarketRegime breakdowns. This is a schema design choice, not extra implementation — flag it in 27.5 planning as a forward-compatibility requirement.

---

## 4. Layer 2: Counterfactual Engine — Sprint 27.7

### The Problem

Every market day, ARGUS evaluates hundreds of potential setups. The Quality Engine scores them. The Risk Manager gates them. Most are rejected — wrong quality grade, wrong regime, concentration limits, insufficient volume. The signals that pass through and become trades generate learning data. **The signals that are rejected generate nothing.**

This is an enormous waste. The market doesn't stop just because ARGUS decided not to trade. The stock continues. The theoretical entry, stop, and target prices all get tested by the market. The outcome is observable — for free.

A concrete example: On a given day, ARGUS evaluates 300 setups. 12 pass all gates and become trades. 288 are rejected. Of those 288, the system learns nothing. But each of those 288 stocks continued trading. Each theoretical entry had a theoretical stop and target. Some would have hit target. Some would have been stopped out. Some would have been time-stopped at EOD.

**288 free data points per day vs 12 paid data points per day.** The Counterfactual Engine captures the 288.

### The Solution

**CounterfactualTracker** — a lightweight shadow position system that:

1. **Intercepts every rejected signal.** When the Quality Engine skips a C-grade setup, or the Risk Manager blocks for concentration, or a strategy evaluates conditions and fails on condition #38 — the Counterfactual Engine records the theoretical position (entry price, stop price, target price, time stop, rejection reason).

2. **Monitors the theoretical outcome.** Using the existing Databento candle stream (these symbols are already in the viable universe — the data is flowing), track whether the theoretical position would have hit target, stop, or time stop.

3. **Records the counterfactual outcome.** Link the outcome back to the rejection reason and all associated metadata (quality score, regime vector, strategy, conditions passed/failed).

4. **Computes filter accuracy metrics.** "Quality Engine C-grade rejection: 82% accuracy (82% of rejected C-grade setups would have lost money). Quality Engine B-grade rejection: 54% accuracy (only 54% of rejected B-grade setups would have lost money — the filter is too aggressive at B grade)."

### Integration Points

The Counterfactual Engine taps into two existing data flows:

**Signal rejection events** — already captured in three places:
- `EvaluationEvent` with type `SIGNAL_REJECTED` (strategy-level rejections with metadata)
- Risk Manager rejection logs (check 0 through PDT limit — see `risk_manager.py`)
- Quality Engine grade filtering in `main.py:_process_signal()` (quality_grade below minimum)

**Price monitoring** — the Databento feed already streams candles for all viable symbols. The CounterfactualTracker subscribes to candle events for symbols with active counterfactual positions. Since these symbols already passed universe filters, they're already in the Databento stream — no additional subscriptions needed.

### Counterfactual Position Lifecycle

```
1. OPENED (signal rejected)
   Record: symbol, strategy_id, rejection_reason, rejection_stage,
           theoretical_entry_price, theoretical_stop_price,
           theoretical_target_price, theoretical_time_stop,
           quality_score, quality_grade, regime_vector,
           conditions_passed, conditions_failed,
           timestamp

2. MONITORING (candles arriving)
   On each candle for this symbol:
   - Did low breach stop? → STOPPED_OUT
   - Did high breach target? → TARGET_HIT
   - Time stop reached? → TIME_STOPPED
   - EOD? → EOD_CLOSED (mark-to-market at close)
   Priority: stop > target > time_stop > EOD (same as BacktestEngine fill model)

3. CLOSED (outcome determined)
   Record: exit_price, exit_reason, theoretical_pnl, theoretical_r_multiple,
           duration, max_adverse_excursion, max_favorable_excursion

4. ANALYZED (linked back to rejection)
   Aggregated into filter accuracy metrics:
   - By rejection stage (quality_filter, risk_manager, strategy_condition)
   - By rejection reason (grade_too_low, concentration_limit, volume_insufficient, etc.)
   - By quality grade at rejection
   - By regime vector at rejection
   - By strategy
```

### Filter Accuracy Reports

The Learning Loop (Sprint 28) consumes counterfactual data to answer:

| Question | How Counterfactual Data Answers It |
|----------|----------------------------------|
| "Are Quality Engine weights correct?" | Compare actual outcomes of traded A-grade setups vs counterfactual outcomes of rejected B-grade setups. If B-grade counterfactuals outperform A-grade actuals, weights are wrong. |
| "Which condition is the weakest filter?" | For each strategy condition, compute the profit rate of setups rejected by that condition. The condition with the highest counterfactual profit rate is filtering out good trades. |
| "Is the Risk Manager too conservative?" | Counterfactual P&L of concentration-blocked signals. If consistently positive, the concentration limit is leaving money on the table. |
| "Which regime is undertrades?" | Aggregate counterfactual profit by regime vector region. Regions with high counterfactual profit and zero actual trades are underserved niches. |

That last question is what feeds the Hypothesis Generation pipeline (Layer 5). **Counterfactual data identifies regime niches where ARGUS should have traded but didn't.** These become targeted hypotheses for new micro-strategies.

### Capacity Considerations

With 300 setups evaluated and ~288 rejected per day, the tracker monitors ~288 counterfactual positions per day. Each closes by EOD (or sooner if stop/target hit). At 1-minute candles per symbol, that's ~288 × 390 = ~112,000 candle checks per day. This is trivial — the Databento stream is already delivering this data; the tracker just observes it.

At 1000+ micro-strategies with broader evaluation, counterfactual volume could reach ~2,000–5,000 per day. Still trivial for candle-level monitoring. Storage is ~1KB per counterfactual position (entry + exit + metadata), so ~5 MB/day, ~150 MB/month. SQLite handles this easily.

### File Structure

```
argus/
├── intelligence/
│   ├── counterfactual.py          # CounterfactualTracker, CounterfactualPosition, FilterAccuracy
│   ├── counterfactual_store.py    # SQLite persistence (data/counterfactual.db)
│   └── filter_accuracy.py         # Aggregate accuracy metrics, Learning Loop integration queries
├── config/
│   └── counterfactual.yaml        # Config-gated (counterfactual.enabled), retention policy
```

### Session Breakdown (Compaction Risk Scoring)

| Session | Scope | Files Created | Files Modified | Context Reads | Tests | Integration | Score |
|---------|-------|---------------|----------------|---------------|-------|-------------|-------|
| S1 | CounterfactualPosition model + CounterfactualTracker + rejection interception (Quality Engine + Risk Manager taps) | 2 | 2 | 3 | 2 | 1 | **12** |
| S2 | Price monitoring (candle subscription for tracked symbols) + theoretical exit logic + CounterfactualStore SQLite persistence | 1 | 1 | 2 | 2 | 1 | **9** |
| S3 | FilterAccuracy computation: per-stage, per-reason, per-grade, per-regime accuracy metrics + Learning Loop integration queries | 1 | 1 | 2 | 2 | 1 | **9** |
| S4 | Integration tests: full lifecycle (rejection → monitoring → close → accuracy computation) + config gating + API endpoint (GET /api/v1/counterfactual/accuracy) | 0 | 3 | 2 | 3 | 2 | **12** |

All sessions ≤ 13. **Total: 4 sessions, ~2 days.**

### Tests: ~50 new

- CounterfactualPosition lifecycle (opened → monitoring → each exit type)
- Fill priority (stop > target > time_stop > EOD — must match BacktestEngine)
- Rejection interception from each source (Quality Engine, Risk Manager check 0–9, strategy conditions)
- FilterAccuracy computation (known rejection set with known outcomes → verify accuracy %)
- Per-grade, per-stage, per-regime breakdowns
- Config gating (counterfactual.enabled: false → tracker does nothing)
- Storage: write, query by date, retention policy enforcement
- Integration: strategy evaluation → rejection → tracker picks up → candle arrives → position closes → accuracy updated

### Dependencies

- Sprint 27.5 (Evaluation Framework) — counterfactual outcomes feed into `MultiObjectiveResult` when comparing filter configurations
- Sprint 27.6 (Regime Intelligence) — counterfactual positions tagged with `RegimeVector` for regime-conditional filter accuracy
- Existing evaluation telemetry (Sprint 24.5) — `EvaluationEvent` with `SIGNAL_REJECTED` type
- Existing Risk Manager rejection logging
- Existing Databento candle stream (no new subscriptions)

### What This Does NOT Do

- No counterfactual tracking for signals that were never evaluated (e.g., symbols not in the viable universe). Only signals that entered the pipeline and were explicitly rejected are tracked.
- No automated filter adjustment (that's Learning Loop V1's job — the Counterfactual Engine provides the data, Sprint 28 acts on it)
- No real-time filter accuracy UI (API endpoint exposes it; Copilot context includes it; dedicated UI comes with Research Console in Sprint 31)

---

## 5. Layer 3: Execution Quality Feedback — Sprint Modifications

### The Problem

The BacktestEngine uses a fixed slippage model (DEC-054). Real execution has variable slippage depending on: time of day, order size relative to volume, bid-ask spread, network latency, and strategy type (momentum entries have worse fills than mean-reversion entries because you're buying into strength).

If the BacktestEngine overestimates fill quality, every `MultiObjectiveResult` is inflated. Strategies that pass Pareto dominance in backtest may fail in reality. The experiment infrastructure promotes strategies based on backtests that don't reflect real execution costs.

### The Solution: Measure and Feed Back

This is NOT a dedicated sprint. It's a set of small additions to existing sprints:

#### 5.1 Execution Quality Logging (Starting Sprint 21.6)

Add to `OrderManager` and `IBKRBroker`:

```
ExecutionRecord:
    order_id: ULID
    symbol: str
    strategy_id: str
    side: str                    # "BUY" or "SELL"
    
    # Expected (from signal)
    expected_fill_price: float   # The price when the signal was generated
    expected_slippage_bps: float # The slippage assumed in backtest
    
    # Actual (from broker)
    actual_fill_price: float
    actual_slippage_bps: float   # Computed: |actual - expected| / expected * 10000
    
    # Context
    time_of_day: time
    order_size_shares: int
    avg_daily_volume: int
    bid_ask_spread_bps: float | None  # From L1 data if available
    latency_ms: float | None          # Signal-to-fill round-trip
    
    # Computed
    slippage_vs_model: float     # actual_slippage - model_predicted_slippage
```

This is ~50 lines of additional logging code in `OrderManager.submit_order()` and the fill callback. Stored in `execution_records` table in `argus.db`.

#### 5.2 Slippage Model Calibration (Add to Sprint 27.5)

Once execution records accumulate (20+ trading days of paper data), compute:

```
StrategySlippageModel:
    strategy_id: str
    estimated_mean_slippage_bps: float     # Mean observed slippage
    estimated_std_slippage_bps: float      # Volatility of slippage
    time_of_day_adjustment: dict[str, float]  # "morning": +2bps, "afternoon": -1bps
    size_adjustment_slope: float           # Additional bps per $1000 order size
    sample_count: int
    last_calibrated: datetime
```

Add to `MultiObjectiveResult`:
```
    # Execution quality (None until calibration data exists)
    execution_quality_adjustment: float | None  
        # Expected Sharpe degradation when real slippage replaces model slippage
```

BacktestEngine gains an optional `slippage_model: StrategySlippageModel` parameter. When provided, uses calibrated slippage instead of fixed. When absent, falls back to fixed (backward-compatible).

#### 5.3 What This Costs

- Sprint 21.6: +1 session (add execution logging to OrderManager) — **could be absorbed into existing sessions if scope allows, or added as S7**
- Sprint 27.5: +0.5 sessions (add `execution_quality_adjustment` field to MultiObjectiveResult, add slippage model calibration utility) — **absorbed into S1 as additional fields**
- Ongoing: ~0 overhead. Logging is fire-and-forget. Calibration runs weekly as a batch job.

### Dependencies

- Paper trading active (execution records only accumulate during real broker interaction)
- Sprint 27.5 (Evaluation Framework) for `MultiObjectiveResult` integration

---

## 6. Layer 4: Adversarial Stress Testing — Sprint 33.5

### The Problem

Walk-forward validation (DEC-047) catches overfitting to normal historical data. Statistical validation (Sprint 33) adds FDR correction. But neither asks: **"What happens in the 1% worst-case scenario?"**

Markets have fat tails. Flash crashes, correlation spikes, liquidity droughts, overnight gap-downs through stops — these events are rare enough to be absent from most backtest periods but frequent enough to destroy a trading account. A system that optimizes for normal conditions and ignores tail risk is fragile.

The PromotionPipeline (Sprint 32.5) promotes cohorts that pass Pareto dominance and paper validation. Without stress testing, it could promote a cohort that looks great in normal markets but concentrates risk in a way that's catastrophic during a correlation spike.

### The Solution: Multi-Scenario Stress Testing

A stress testing framework that every promotion cohort must pass before advancing beyond Stage 2 (simulated paper).

#### 6.1 Historical Stress Scenarios

Replay the ensemble through known crisis periods:

| Scenario | Period | What It Tests |
|----------|--------|-------------|
| COVID crash | Feb 19 – Mar 23, 2020 | Rapid market crash. Do stops work? Does the kill switch fire? |
| Meme stock mania | Jan 25 – Feb 5, 2021 | Extreme vol in specific names. Does concentration limiting work? |
| SVB week | Mar 8 – Mar 15, 2023 | Sector-specific crisis. Does sector rotation awareness help? |
| Aug 2024 yen carry | Aug 1 – Aug 9, 2024 | Overnight gap-down, correlation spike. Does overnight risk get managed? |
| Treasury selloff | Oct 2023 | Rising rates impact on growth stocks. Does regime detection catch it? |

**Implementation:** BacktestEngine already supports date range specification. Stress testing = running the ensemble through these specific date ranges and checking:
- Max drawdown within scenario (hard limit: <15% per kill criteria)
- Kill switch response time (how many days before it fires?)
- Correlation spike detection (does the regime vector catch the correlation increase?)
- Recovery trajectory (how quickly does the ensemble recover after the crisis?)

#### 6.2 Synthetic Stress Scenarios

Generate artificial market conditions that may not appear in history:

- **Correlation spike:** Synthetically set all pairwise correlations to 0.9 and re-evaluate ensemble diversification ratio. If the Sharpe collapses below 1.0, the ensemble is diversification-dependent.
- **Liquidity drought:** Simulate 50% of orders failing to fill, with filled orders getting 3× normal slippage. Test: does the system gracefully degrade or does it accumulate unhedged risk?
- **Gap-through-stop:** For each open position, simulate an overnight gap that opens 2× the stop distance below entry. Test: what's the maximum single-day loss? Does it breach the 3% daily limit?
- **Multi-strategy simultaneous drawdown:** Force all strategies into their worst historical drawdown simultaneously (rather than the staggered drawdowns that normally occur). Test: aggregate worst-case.

**Implementation:** Synthetic scenarios modify the data or execution layer, then run the same BacktestEngine path. This is a thin simulation wrapper, not a new engine.

#### 6.3 StressTestResult

```
StressTestResult:
    scenario_name: str
    scenario_type: str          # "historical" or "synthetic"
    date_range: tuple[date, date] | None  # None for synthetic
    
    # Outcome
    max_drawdown_pct: float
    recovery_days: int | None   # None if didn't recover within scenario
    max_single_day_loss_pct: float
    kill_switch_fired: bool
    kill_switch_day: int | None # Day within scenario when it fired
    
    # Regime detection quality
    regime_transition_detected: bool
    regime_detection_lag_minutes: float | None
    
    # Risk containment
    daily_loss_limit_breached: bool
    concentration_limit_breached: bool
    worst_case_order_fill_rate: float
    
    # Verdict
    passed: bool                # All thresholds met
    failure_reasons: list[str]  # What failed, if anything
```

#### 6.4 Integration with PromotionPipeline

Stress testing becomes a gate between Stage 1 (BACKTEST_VALIDATED) and Stage 2 (SIMULATED_PAPER) in the PromotionPipeline:

```
Stage 1.5: STRESS_TESTED
    Method: Run cohort ensemble through all historical scenarios + all synthetic scenarios
    Gate: ALL scenarios must pass:
          - Max drawdown < 15% in any single scenario
          - Kill switch fires within 5 trading days in crash scenarios
          - No daily loss limit breach
          - Correlation spike Sharpe > 0.5 (system isn't solely diversification-dependent)
          - Gap-through-stop worst-case loss < 5%
    Auto-action on PASS: Advance to simulated paper
    Auto-action on FAIL: Revert cohort, log which scenarios failed
    Notification: ntfy.sh with stress test summary
```

This gate is cheap to run (a few BacktestEngine executions per scenario, minutes of compute) but catches catastrophic risks that Pareto dominance on normal data would miss.

### File Structure

```
argus/
├── analytics/
│   ├── stress_testing.py          # StressTestRunner, scenario definitions, synthetic generators
│   ├── stress_scenarios.py        # Historical scenario registry, synthetic scenario configs
│   └── stress_results.py          # StressTestResult, pass/fail logic, integration with PromotionPipeline
├── config/
│   └── stress_testing.yaml        # Scenario configs, thresholds, pass/fail criteria
```

### Session Breakdown (Compaction Risk Scoring)

| Session | Scope | Files Created | Files Modified | Context Reads | Tests | Integration | Score |
|---------|-------|---------------|----------------|---------------|-------|-------------|-------|
| S1 | StressTestResult model + historical scenario registry (5 defined scenarios with date ranges + expected behaviors) | 2 | 0 | 3 | 2 | 0 | **9** |
| S2 | StressTestRunner: historical scenario execution via BacktestEngine + pass/fail evaluation | 1 | 1 | 3 | 2 | 1 | **10** |
| S3 | Synthetic scenario generators: correlation spike, liquidity drought, gap-through-stop, simultaneous drawdown | 0 | 2 | 2 | 2 | 1 | **9** |
| S4 | PromotionPipeline integration: Stage 1.5 gate + ntfy notifications + config wiring | 0 | 3 | 3 | 2 | 2 | **12** |
| S5 | Integration tests: full stress test cycle, pass and fail paths, pipeline gate integration | 0 | 2 | 2 | 3 | 2 | **11** |

All sessions ≤ 13. **Total: 5 sessions, ~3 days.**

### Tests: ~55 new

- Historical scenario replay (known scenarios produce expected drawdowns)
- Synthetic scenario generation (correlation matrix manipulation, fill rate reduction)
- Pass/fail logic (boundary conditions on each threshold)
- PromotionPipeline gate (cohort passes stress → advances, cohort fails → reverts with reason)
- StressTestResult serialization and storage
- Integration: cohort registered → stress tested → pipeline advances or blocks

### Dependencies

- Sprint 32.5 (Experiment Registry + PromotionPipeline) — stress testing is a new gate in the pipeline
- Sprint 27.5 (Evaluation Framework) — BacktestEngine with MultiObjectiveResult for scenario evaluation
- Sprint 27.6 (Regime Intelligence) — regime transition detection quality is a stress test metric
- BacktestEngine (Sprint 27) — executes historical scenarios
- Databento historical data — **confirmed available** at $0 cost on Standard plan: XNAS.ITCH + XNYS.PILLAR provide OHLCV-1m back to May 2018, covering all 5 crisis scenarios. BacktestEngine's HistoricalDataFeed needs a mode to query exchange-specific datasets (XNAS.ITCH + XNYS.PILLAR) instead of EQUS.MINI for pre-March-2023 data — small addition in Sprint 33.5 S1 or S2.

### What This Does NOT Do

- No real-time stress monitoring during live trading (that's a future concern — monitoring portfolio VaR in real-time)
- No Monte Carlo simulation (synthetic scenarios are deterministic "what if" tests, not probabilistic distributions)
- No custom scenario builder UI (config YAML is sufficient; Research Console could add this later)
- No automatic scenario generation from market conditions (e.g., "today feels like a pre-crisis pattern" — that's ML territory)

---

## 7. Layer 5: Hypothesis Generation Design — Sprint 32.5 Design Document

### The Problem

Sprint 41 (Continuous Discovery Pipeline) is where ARGUS generates new strategy candidates autonomously. But "generate new strategies" is not a design — it's a wish. Without a concrete architecture for how hypotheses are generated, Sprint 41 planning will either (a) scope it too narrowly (only one generation method) or (b) waste time designing what should already be decided.

### The Solution: Design Now, Build at Sprint 41

During Sprint 32.5 planning, produce a design document (not code) that specifies the four hypothesis generation methods and their interfaces to the ExperimentQueue:

#### Method 1: Niche Identification (Data-Driven)

**Input:** Counterfactual Engine data (Layer 2) + Regime Intelligence (Layer 1).
**Logic:** Find regions in regime space where (a) counterfactual profit rate is high (>60%) and (b) no existing strategy operates.
**Output:** A regime region specification + suggested strategy family → ExperimentQueue as NEW_PATTERN.

*Example: "In regime region {breadth > 0.5, correlation < 0.3, intraday = trending, sector = technology}, 73% of rejected ORB setups would have been profitable. No existing ORB variant targets this region. Hypothesis: ORB variant with wider targets + tech sector filter."*

#### Method 2: Pattern Mutation (Genetic Algorithm)

**Input:** Existing strategy parameters from StrategyTemplate (Sprint 32) + ExperimentRegistry meta-learning data.
**Logic:** Take the top-performing parameter sets. Apply mutations (±10–30% on 1–3 parameters). Cross-over between high-performing variants (take entry params from A, exit params from B).
**Output:** Mutated parameter sets → ExperimentQueue as PARAMETER_TWEAK.

*This is closest to Karpathy's autoresearch — hill-climbing on parameter space. The key difference is that ARGUS uses ExperimentRegistry meta-learning to bias mutations toward parameter dimensions that have historically shown improvement (rather than uniform random mutation).*

#### Method 3: Literature Mining (AI-Driven)

**Input:** Trading literature, academic papers, fintwit threads (via web search or user-supplied documents).
**Logic:** Claude API extracts testable hypotheses from text. Translates them into PatternModule implementations (code generation). Each implementation is syntactically validated and unit-tested before entering the queue.
**Output:** New PatternModule Python files → ExperimentQueue as NEW_PATTERN.

*This is the most ambitious method and the last to be implemented. Requires Claude API code generation + automated testing. The PatternModule ABC (Sprint 26) makes this feasible — a new pattern is a well-defined interface (detect, score, get_default_params), not an arbitrary program.*

#### Method 4: Anomaly Detection (Statistical)

**Input:** ARGUS's own trade history + counterfactual data + regime data.
**Logic:** Statistical analysis of performance conditional on market microstructure features. Detect anomalies like "ORB Breakout win rate jumps to 85% on days when the pre-market gap is between 1–2% and volume is 2–3× average." These anomalies suggest conditions where existing strategies are particularly effective — candidate for a specialized micro-strategy variant.
**Output:** Feature condition + strategy family → ExperimentQueue as SIGNAL_FILTER.

#### Interface Specification

All four methods produce the same output type:

```
GeneratedHypothesis:
    source: HypothesisSource     # NICHE_ID, MUTATION, LITERATURE, ANOMALY
    description: str             # Human-readable explanation
    confidence: float            # 0.0–1.0 (how confident is the generator?)
    experiment_type: ExperimentType
    
    # For PARAMETER_TWEAK / SIGNAL_FILTER:
    strategy_id: str
    config_diff: dict
    
    # For NEW_PATTERN:
    pattern_module_code: str     # Python source code
    pattern_config: dict         # Default YAML config
    test_code: str               # Basic unit tests
    
    # Targeting info
    target_regime_region: dict | None  # Regime vector conditions where this should be tested
    expected_improvement: str          # "Higher Sharpe in low-vol trending" or similar
```

The design document specifies this interface + the contract between each generator and the ExperimentQueue. Sprint 41 implements the generators; the interface is stable from Sprint 32.5.

### Deliverable

A markdown design document committed to `docs/design/hypothesis-generation-architecture.md`. Not code. ~10–15 pages. Produced during Sprint 32.5 planning (same conversation, takes ~1 hour of planning time).

---

## 8. Layer 6: Anti-Fragility Integration — Sprint Modifications

### The Problem

A standard optimization system improves at a constant rate regardless of performance. ARGUS should improve **faster when it's losing money.** This is Taleb's anti-fragility principle: systems that get stronger from stress.

### The Solution: Behavioral Modifications to Existing Sprints

Anti-fragility is not a module — it's a set of behavioral rules baked into the experiment infrastructure.

#### 8.1 Loss-Driven Queue Priority (Add to Sprint 32.5)

Modify ExperimentQueue priority logic:

```python
def compute_priority(experiment: QueuedExperiment, system_state: SystemState) -> int:
    base_priority = SOURCE_PRIORITIES[experiment.source]
    
    # Anti-fragility multiplier: prioritize investigation when losing
    if system_state.rolling_10day_pnl < 0:
        drawdown_severity = abs(system_state.rolling_10day_pnl) / system_state.max_acceptable_drawdown
        # In drawdown → investigate failures first
        if experiment.experiment_type in (ExperimentType.SIGNAL_FILTER, ExperimentType.QUALITY_WEIGHT_ADJ):
            base_priority -= int(drawdown_severity * 10)  # Lower number = higher priority
    
    # During profitable periods → explore more aggressively
    if system_state.rolling_10day_pnl > 0 and system_state.rolling_sharpe > 2.0:
        if experiment.experiment_type == ExperimentType.NEW_PATTERN:
            base_priority -= 5  # Boost exploration when things are going well
    
    return max(1, base_priority)
```

When the system is in drawdown, experiments that **diagnose failures** (filter adjustments, weight recalibrations) jump to the front of the queue. When the system is performing well, experiments that **explore new territory** (new patterns) get priority. The system investigates when it's losing and explores when it's winning.

#### 8.2 Post-Mortem Automation (Add to Sprint 32.5)

When a PromotionCohort is reverted (kill switch or manual), automatically queue a batch of diagnostic experiments:

```python
def on_cohort_reverted(cohort: PromotionCohort, revert_reason: str):
    # 1. Which strategies in the cohort had negative marginal contribution?
    toxic_strategies = identify_deadweight(cohort.rolling_ensemble_result)
    
    # 2. What regime were we in when it failed?
    failure_regime = get_current_regime_vector()
    
    # 3. Queue diagnostic experiments
    for strategy_id in toxic_strategies:
        # Test: would the cohort have survived without this strategy?
        queue_experiment(
            type=ExperimentType.ALLOCATION_RULE,
            description=f"Post-mortem: cohort {cohort.id} without {strategy_id}",
            priority=1,  # Highest priority
            source="post_mortem"
        )
    
    # 4. Test: are other active cohorts vulnerable to the same regime?
    for active_cohort in get_active_cohorts():
        queue_experiment(
            type=ExperimentType.REGIME_THRESHOLD,
            description=f"Vulnerability check: cohort {active_cohort.id} in regime {failure_regime}",
            priority=2,
            source="post_mortem"
        )
    
    # 5. Log the post-mortem for meta-learning
    registry.record_post_mortem(cohort, toxic_strategies, failure_regime)
```

Every failure triggers an immediate investigation. The system doesn't just revert — it asks "why did this fail and is anything else about to fail for the same reason?"

#### 8.3 Drawdown-Accelerated Experimentation (Add to Sprint 32.5)

When the ensemble is in drawdown (rolling 10-day P&L negative):

- **Overnight compute allocation shifts.** Instead of 50% exploration / 50% optimization, shift to 20% exploration / 80% diagnostic optimization. The system focuses on understanding what's wrong rather than finding new things.
- **Counterfactual Engine analysis runs daily instead of weekly.** Filter accuracy metrics get recalculated every day during drawdown. If the quality filter became inaccurate due to a regime shift, this catches it immediately.
- **Kill switch monitoring frequency increases.** From daily EnsembleResult comparison to every 2 hours during market hours. Faster detection of degrading cohorts.

#### 8.4 Implementation Cost

These are behavioral modifications to Sprint 32.5, not a separate sprint. Estimated addition:

- Loss-driven priority: ~30 lines in `experiment_queue.py`. Absorbed into existing S6.
- Post-mortem automation: ~100 lines as a new function in `promotion_pipeline.py`. Adds ~0.5 sessions to Sprint 32.5 (extend S5 or add S5b).
- Drawdown acceleration: ~50 lines of conditional logic in the worker scheduler. Absorbed into existing S6.

**Net Sprint 32.5 impact: +0.5 sessions (S5 expanded or S5b added).** Total Sprint 32.5 sessions: 8 → 8.5 → round to 9.

---

## 9. Combined Roadmap Impact (Both Amendments)

### Updated Build Track Queue

```
~~26~~ ✅ → ~~27~~ ✅ →
  21.6 (Backtest Re-Validation) →
  27.5 (Evaluation Framework) →              ← Experiment Infrastructure amendment
  27.6 (Regime Intelligence) →               ← Intelligence Architecture amendment
  27.7 (Counterfactual Engine) →             ← Intelligence Architecture amendment
  28 (Learning Loop V1) →
  29–31 (Pattern Expansion + Short Selling + Research Console) →
  32 (Parameterized Templates) →
  32.5 (Experiment Registry + Promotion +    ← Experiment Infrastructure amendment
        Anti-Fragility + Hypothesis Design)    + Intelligence Architecture additions
  33 (Statistical Validation) →
  33.5 (Adversarial Stress Testing) →        ← Intelligence Architecture amendment
  34 (ORB Systematic Search) →
  35–41
```

### Phase Extension Summary

| Phase | New Sprints | Extension | Net Effect |
|-------|-------------|-----------|------------|
| **Phase 6** | 27.5, 27.6, 27.7 | +7–8 days | Learning Loop V1 becomes dramatically more effective (regime vectors, counterfactual data, proper evaluation framework). Without these, Sprint 28 optimizes against crude data. |
| **Phase 7** | 32.5 (expanded) | +4.5 days | Experiment Registry, Promotion Pipeline, anti-fragility, and hypothesis generation design all land before the first large-scale experiment. |
| **Phase 8** | 33.5 | +3 days | Stress testing gate prevents promoting fragile cohorts. Catches risks that backtest-era evaluation misses. |
| **Total** | 5 new sprint slots | **~14–15 days** | Avoids a larger rearchitecture cost at Phase 9. Every downstream sprint is de-risked. |

### Revised Summary Timeline

| Phase | Sprints | Duration | Δ vs Current Roadmap |
|-------|---------|----------|---------------------|
| 6: Strategy Expansion | 21.6, 27.5, 27.6, 27.7, 28, 29–31 | ~3.5–5 weeks | +7–8 days |
| 7: Infrastructure Unification | 32, 32.5 | ~2 weeks | +1.5 days (Sprint 33 shrinks) |
| 8: Controlled Experiment | 33, 33.5, 34, 35 | ~3 weeks | +3 days |
| 9–10 | 36–41 | ~5.5–7.5 weeks | Potentially shorter (infrastructure already built) |
| **Total** | | **~16–22 weeks** | +14–15 days vs current ~18 weeks |

### What Changes in Sprint 28 (Learning Loop V1) — With All Amendments

Sprint 28 becomes dramatically more powerful with the three preceding sprints:

| Without Amendments | With All Amendments |
|-------------------|-------------------|
| Learns from ~12 trades/day | Learns from ~12 trades + ~288 counterfactuals/day (**24× more data**) |
| Optimizes Quality Engine weights against 5 crude regime labels | Optimizes against multi-dimensional regime vectors (richer conditional analysis) |
| Uses ad-hoc evaluation metrics | Uses MultiObjectiveResult + EnsembleResult (standardized, Pareto-comparable) |
| Doesn't know which filters are too aggressive | Counterfactual accuracy data tells it exactly which filters to loosen/tighten |
| Can't identify regime niches with no strategy coverage | Counterfactual + regime data reveals underserved niches automatically |

The three preceding sprints don't just help Sprint 28 — they transform it from "basic weight tuning" to "intelligent system analysis with 24× the data and proper evaluation framework."

---

## 10. Decision Checklist

### For Strategic Conversation (Before Sprint Planning)

**Layer 1 — Regime Intelligence (Sprint 27.6):**
- [ ] Adopt, reject, or modify?
- [ ] If adopted: confirm data sources (all free/existing — no new costs)
- [ ] If adopted: confirm placement after 27.5 and before 27.7
- [ ] Flag to Sprint 27.5 planning: design RegimeMetrics for multi-dimensional regime vectors

**Layer 2 — Counterfactual Engine (Sprint 27.7):**
- [ ] Adopt, reject, or modify?
- [ ] If adopted: confirm placement after 27.6 and before 28
- [ ] Capacity concern: comfortable with ~288 shadow positions/day initially scaling to ~5,000?

**Layer 3 — Execution Quality (Sprint modifications):**
- [ ] Adopt, reject, or modify?
- [ ] If adopted: add execution logging task to Sprint 21.6 scope
- [ ] If adopted: add execution_quality_adjustment field to Sprint 27.5 MultiObjectiveResult

**Layer 4 — Adversarial Stress Testing (Sprint 33.5):**
- [ ] Adopt, reject, or modify?
- [ ] If adopted: confirm placement after Sprint 33 and before Sprint 34
- [ ] Note: Databento historical data **confirmed available** — XNAS.ITCH + XNYS.PILLAR provide OHLCV-1m back to May 2018 at $0 cost on Standard plan. All 5 crisis scenarios covered. Sprint 33.5 needs ~0.5 session to add exchange-specific HistoricalDataFeed mode.

**Layer 5 — Hypothesis Generation Design:**
- [ ] Adopt, reject, or modify?
- [ ] If adopted: produce design document during Sprint 32.5 planning conversation

**Layer 6 — Anti-Fragility Integration:**
- [ ] Adopt, reject, or modify?
- [ ] If adopted: expand Sprint 32.5 by ~0.5 sessions

**Combined:**
- [ ] Accept ~14–15 day total roadmap extension (both amendments)?
- [ ] Reserve DEC ranges for new sprints
- [ ] Commit both amendment documents to `docs/amendments/`

### For Sprint 21.6 Planning (After Strategic Conversation)

- [ ] If Execution Quality adopted: add execution logging to 21.6 session scope
- [ ] Confirm Sprint 21.6 scope is otherwise unchanged
- [ ] Plan Sprint 27.5 with forward-compatibility for RegimeVector (if 27.6 adopted)

---

## 11. Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Phase 6 becomes too infrastructure-heavy, delays paper trading feedback | Medium | 7–8 days of infrastructure before Learning Loop gets live data | All three new sprints (27.5, 27.6, 27.7) are backend-only with no frontend dependency. Paper trading continues running in parallel, accumulating data for Sprint 28. |
| Regime Intelligence adds complexity without proven value | Low-Medium | RegimeVector might not be more predictive than simple MarketRegime | Backward compatibility ensures no regression. RegimeVector dimensions can be individually disabled via config. If breadth adds nothing, turn it off. |
| Counterfactual tracking introduces subtle bugs in fill logic | Low | Shadow positions use different fill priority than BacktestEngine, producing misleading data | Mandate: fill priority must match BacktestEngine exactly (stop > target > time_stop > EOD). Shared fill-priority logic, not duplicated. |
| Stress test scenarios are historical and may not predict future crises | Medium | Next crisis may look nothing like COVID or SVB | Synthetic scenarios complement historical ones. Correlation spike + liquidity drought + gap-through-stop are structural risks, not historical replays. |
| Anti-fragility priority shift reduces exploration during drawdowns | Low | System becomes purely defensive when losing, misses recovery opportunities | 20/80 split (not 0/100) maintains minimum exploration. Priority shifts are gradual, not binary. |
| Combined 14–15 day extension delays live trading | Low-Medium | Each additional day is a day without income | Counter-argument: each additional day of infrastructure reduces the probability of catastrophic loss when live. The kill criteria exist precisely because going live prematurely is the highest-consequence risk in the entire project. |

---

## 12. Historical Data Availability — Confirmed

Historical data availability has been verified (March 23, 2026). All stress testing scenarios are fully covered at $0 additional cost on the Databento Standard plan.

### Databento Dataset Availability

| Dataset | OHLCV-1m Earliest | Latest | Notes |
|---------|-------------------|--------|-------|
| XNAS.ITCH | 2018-05-01 | 2026-03-23 | ~8 years of NASDAQ data |
| XNYS.PILLAR | 2018-05-01 | 2026-03-23 | ~8 years of NYSE data |
| EQUS.MINI | 2023-03-28 | 2026-03-21 | ~3 years — production feed, both exchanges combined |

**Key finding:** XNYS.TRADES does not exist — the correct NYSE dataset is **XNYS.PILLAR**. Exchange-specific datasets (XNAS.ITCH + XNYS.PILLAR) provide 8 years of history vs EQUS.MINI's 3 years, but require querying both exchanges separately and merging results.

**Cost verification:** SPY OHLCV-1m on XNAS.ITCH for a sample day in March 2020 returns $0.00 — included in Standard plan.

### Stress Scenario Coverage

| Scenario | Period | Dataset | Status |
|----------|--------|---------|--------|
| COVID crash | Feb–Mar 2020 | XNAS.ITCH + XNYS.PILLAR | ✅ Available |
| Meme stock mania | Jan–Feb 2021 | XNAS.ITCH + XNYS.PILLAR | ✅ Available |
| SVB week | Mar 2023 | XNAS.ITCH + XNYS.PILLAR (or EQUS.MINI) | ✅ Available |
| Yen carry unwind | Aug 2024 | Any dataset | ✅ Available |
| Treasury selloff | Oct 2023 | Any dataset | ✅ Available |

### Implementation Implication

BacktestEngine's `HistoricalDataFeed` currently queries EQUS.MINI (Sprint 27). For stress testing and richer walk-forward validation, it needs a mode that queries XNAS.ITCH + XNYS.PILLAR separately and merges the results. This is a small addition (~0.5 session) to Sprint 33.5 scope, or could be built earlier if the 8-year data range proves useful for Sprint 33 (Statistical Validation).

### Broader Impact: Phase 7 Gate Concern Resolved

The roadmap's Phase 7 Gate (Section 8) flags: *"Three-way splits across only 35 months of data may not provide enough statistical power."* With XNAS.ITCH + XNYS.PILLAR providing ~96 months of 1-minute data back to May 2018, this concern is substantially mitigated. The data purchase decision (DEC-353, deferred indefinitely) remains correct — free data is sufficient for the full roadmap through Phase 10.

---

## 13. What This Makes Possible — The Complete Picture

With both amendments adopted, ARGUS at Sprint 34 (first systematic search) has:

```
INTELLIGENCE ARCHITECTURE
├── Regime Intelligence (27.6)
│   └── Multi-factor regime vectors: trend, vol, breadth, correlation, sector, intraday
│       └── Every strategy has a precise regime niche, not a crude label
│
├── Counterfactual Engine (27.7)
│   └── Tracks outcomes of every rejected signal (~288/day → ~5,000/day at scale)
│       └── Knows exactly which filters are too tight, which regime niches are underserved
│
├── Execution Quality (21.6+)
│   └── Real vs expected fills measured on every trade
│       └── BacktestEngine uses calibrated slippage, not fantasy numbers
│
├── Evaluation Framework (27.5)
│   └── MultiObjectiveResult + EnsembleResult + Pareto dominance + tiered confidence
│       └── Universal currency for comparing any two configurations
│
├── Experiment Registry + Promotion Pipeline (32.5)
│   └── Every experiment tracked, cohort-based promotion, simulated-paper screening
│       └── Overnight queue processes ~200–6,400 experiments/night
│
├── Anti-Fragility (32.5)
│   └── Loss-driven priority, post-mortem automation, drawdown acceleration
│       └── System improves fastest when performance is worst
│
├── Adversarial Stress Testing (33.5)
│   └── Historical crisis replay + synthetic stress scenarios
│       └── No cohort reaches paper without surviving simulated crises
│
└── Hypothesis Generation Design (32.5 design doc)
    └── Niche ID + mutation + literature mining + anomaly detection
        └── Four targeted methods replace random parameter exploration
```

This is a system that:
- **Knows the market environment precisely** (regime vectors, not crude labels)
- **Learns from every signal, not just the ones it trades** (counterfactual engine)
- **Evaluates with realistic assumptions** (calibrated slippage from real execution data)
- **Compares improvements rigorously** (multi-objective Pareto dominance at ensemble level)
- **Tests against worst cases** (adversarial stress testing before promotion)
- **Tracks everything it tries** (experiment registry with meta-learning)
- **Promotes improvements safely** (simulated paper → real paper → veto window → kill switch)
- **Generates targeted hypotheses** (niche identification, not random exploration)
- **Gets stronger from failures** (anti-fragility in queue priority and post-mortem automation)
- **Runs experiments while you sleep** (overnight queue with market-hours awareness)

That's not just a trading system. That's a trading intelligence platform.

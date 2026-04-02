# Adaptive Capital Intelligence — Architectural Vision

> **Status:** Vision document (DEF-133). Not yet implemented.
> **Created:** April 1, 2026 (Sprint 32.5 Session 8)
> **Scope:** Long-range architectural direction for capital allocation. Phases 1–2 target Sprints 34–38+.
> **Background:** This document is self-contained. Familiarity with ARGUS is helpful but not required.

---

## 1. Problem Statement

ARGUS's current capital allocation model is a **stacked guardrail system**. When a strategy emits a signal, the following chain fires in sequence:

```
SignalEvent
  → Risk Manager  (does this violate hard limits?)
    → Quality Engine  (what grade is this setup?)
      → DynamicPositionSizer  (map grade → risk tier → shares)
        → Overflow Router  (is capital available?)
          → Orchestrator  (regime filtering)
            → Order Manager  (submit bracket)
```

Each layer asks the same question in a different form: **"Does this violate limits?"** The layers are independent. The Risk Manager doesn't know the Quality Engine's output. The DynamicPositionSizer doesn't know the portfolio's current correlation profile. The Overflow Router doesn't compare this opportunity against the three signals queued behind it.

This architecture has served ARGUS well through Phase 5 and Phase 7. It is correct, auditable, and safe. But it leaves a measurable edge on the table in two ways:

**1. The approve/reject binary wastes information.** An A+ setup in a strongly trending regime on a high-RVOL breakout gets the same share count as an A+ setup in a choppy regime on a borderline volume signal — because both pass the same quality threshold mapping to the same risk tier. The system knows more than it acts on.

**2. Sizing decisions are made without portfolio context.** Position size is computed per-signal in isolation. The system doesn't ask: "Given that I already have 40% of capital deployed in correlated momentum setups, what is the marginal risk of this new position?" It only checks that the concentration limit (5% per symbol) and daily risk cap haven't been breached.

The result is a system that prevents catastrophic mistakes but doesn't optimize capital deployment. At 12 strategies with largely correlated momentum setups, this limitation is minor. At 200+ micro-strategy variants firing simultaneously across diverse patterns, the compounding cost becomes material.

**The shift required:** From "does this violate limits?" to **"what is the optimal capital to deploy for this signal, given full system state?"**

---

## 2. Vision: AllocationIntelligence

The target architecture replaces the stacked guardrail chain with a single `AllocationIntelligence` service that produces a **continuous sizing recommendation** for every incoming signal.

```
SignalEvent
  → AllocationIntelligence  (full system state → optimal share count)
    → Hard Floor Enforcement  (non-overridable catastrophic protection)
      → Order Manager  (submit bracket)
```

`AllocationIntelligence` is not an optimizer in the academic sense — it doesn't solve a global portfolio optimization problem on every tick. It is a **sizing function** that takes the current system state and a candidate signal as inputs and returns a recommended share count with metadata (confidence, edge estimate, portfolio impact).

The key properties:

- **Continuous output.** Not "approved at 100 shares" or "rejected." Returns 0–N shares, where 0 is the functional equivalent of rejection. A low-confidence A-grade signal in a correlated portfolio might return 40 shares instead of the nominal 60. An exceptional setup in an uncorrelated regime might return 90.

- **Full state input.** Sees current positions, their correlations, pending signals, recent performance, regime state, experiment track records, and time of day.

- **Replaces the stacked chain.** The Risk Manager, Quality Engine, DynamicPositionSizer, and Overflow Router are absorbed into AllocationIntelligence. The Hard Floor (circuit breakers, non-overridable limits) remains independent and non-bypassable.

- **Auditable.** Every sizing decision emits a metadata payload explaining the recommendation — edge estimate, confidence, portfolio impact assessment, dominant factor. The Command Center surfaces this in the Orchestrator and Trades pages.

---

## 3. Six Input Dimensions

AllocationIntelligence synthesizes six dimensions of information. Each dimension contributes a weight to the final sizing output. The dimensions are composable — a weak signal on one dimension can be offset by a strong signal on another, or a hard limit on one can cap the output regardless of others.

### 3.1 Edge Estimation with Uncertainty

**Current state:** Quality grade (A+/A/B/C) mapped to a fixed risk tier via a lookup table. Grade is computed from 5 components (pattern strength, catalyst quality, volume profile, technical quality, regime alignment).

**Target state:** Kelly criterion-inspired sizing with explicit uncertainty quantification.

The Kelly fraction for a trade is: `f = (edge × win_rate - loss_rate) / risk_per_unit`. In practice, fractional Kelly (typically 25–50%) is used to account for estimation error.

The critical insight is that edge estimation is uncertain. A pattern with 30 live trades and 62% win rate has a very different confidence interval than the same pattern with 300 trades. AllocationIntelligence should:

- Estimate edge from the pattern's realized outcomes (Learning Loop data)
- Weight by sample size (30 trades → wide confidence interval → smaller Kelly fraction)
- Incorporate the experiment track record: a variant with 200 shadow trades and a Sharpe of 2.1 has a tighter edge estimate than a variant with 15 shadow trades
- Apply a discount when edge estimate comes from a different regime than the current one

The output is not a point estimate of win rate — it is a **posterior distribution** over edge, and the Kelly fraction is computed from that distribution's mean with variance-based shrinkage.

### 3.2 Portfolio-Level Risk in Real Time

**Current state:** Concentration limit (5% per symbol, 15% per sector when available) enforced as binary pass/fail. Correlation tracked via CorrelationTracker but not used in sizing.

**Target state:** Correlation and concentration as **continuous penalty functions**.

The marginal risk of a new position is not constant. Adding a Bull Flag signal on NVDA when TSLA and AMD are already open adds correlated exposure. Adding a Gap-and-Go on a biotech catalyst in a portfolio with no biotech exposure adds diversification.

AllocationIntelligence computes:
- Current portfolio correlation matrix (from CorrelationTracker, updated every 5 minutes)
- Incremental variance added by the candidate position
- Concentration load for the candidate symbol (existing + new)
- A **correlation penalty**: max(0, 1 - incremental_variance_contribution_ratio) that scales down recommended size as correlation increases

At full correlation (identical exposure already open), the penalty approaches 0 and the recommended size drops to the hard-floor minimum. At zero correlation (uncorrelated diversifying position), the penalty is 1 (no reduction).

### 3.3 Opportunity Cost

**Current state:** Capital is allocated first-come, first-served. The Overflow Router rejects signals when capital is exhausted. No comparison between competing signals occurs.

**Target state:** Capital allocation across competing signals.

When multiple signals are queued (e.g., 3 setups arrive in the same 30-second window), AllocationIntelligence should compare their edge-uncertainty distributions and allocate available capital to the highest-expected-value opportunities first.

This requires:
- A brief signal queue (configurable max age, e.g., 10 seconds)
- Comparative edge ranking across queued signals
- Proportional allocation among top-N signals based on relative edge
- Graceful handling of the single-signal case (no comparison needed, existing behavior)

This dimension is the most complex to implement correctly and is the last to be added (likely Phase 2 or later).

### 3.4 Temporal Awareness

**Current state:** Strategy operating windows (e.g., 9:30–10:30 AM for ORB) provide binary time gating. No continuous time-of-day adjustment exists.

**Target state:** Continuous time-of-day weighting.

Session data (captured in MFE/MAE tracking) reveals that ARGUS's strategies perform very differently by hour of day. The 10:00–10:30 AM window is materially weaker than the 9:30–10:00 AM breakout window. Midday (11:00 AM–2:00 PM) is near-breakeven for most momentum patterns.

AllocationIntelligence incorporates a **time-of-day multiplier** computed from rolling realized-edge estimates by hour, smoothed with a Gaussian kernel to avoid overfitting to specific clock times.

The multiplier is bounded: minimum 0.5 (half size at worst hours), maximum 1.2 (modest upsize at best hours). It does not override the operating window — a strategy that closes at 10:30 AM still closes at 10:30 AM. It adjusts sizing within the active window.

### 3.5 Self-Awareness of Recent Performance

**Current state:** Circuit breakers fire when daily loss limit (3%) or consecutive losses (configurable) are hit. No smooth drawdown response exists between normal operation and circuit breaker.

**Target state:** Smooth drawdown response that scales down sizing gradually before circuit breakers fire.

The circuit breakers are appropriate for catastrophic protection. But the system should also respond to adverse conditions **below** the circuit breaker threshold:

- After 3 consecutive losses, recommended size decreases by 20%
- After 5 consecutive losses, decreases by 40%
- After 10% of daily loss limit consumed, decrease by 10%
- After 25% consumed, decrease by 25%
- After 50% consumed, decrease by 50%
- At 75%, the system is effectively at minimum size for remaining trades

This creates a **progressive derisking curve** that transitions smoothly into the hard circuit breaker rather than being a binary cliff.

The Learning Loop provides the necessary input: consecutive losses, current day P&L, and rolling win rate over the last N trades.

### 3.6 Variant Track Record with Recency Weighting

**Current state:** Experiment Pipeline assigns shadow/live status based on Pareto dominance over a time window. Sizing does not distinguish between a pattern that has fired 200 times with a Sharpe of 2.1 vs. the same pattern that has fired 15 times with an uncertain Sharpe.

**Target state:** Recency-weighted track record as a sizing multiplier for experiment variants.

Each experiment variant has a track record accumulated via CounterfactualTracker (shadow mode) and live execution (live mode). AllocationIntelligence uses this track record to scale sizing:

- Variants with fewer than `min_track_record_trades` trades trade at minimum size regardless of quality score
- Variants with a maturing track record (50–200 trades) trade at a linearly scaled fraction of their nominal size
- Variants with a mature track record (200+ trades across multiple regime types) trade at full nominal size
- Recency weighting: trades in the last 20 sessions count 2x vs. trades from 60+ sessions ago (exponential decay)

This creates a natural "earned autonomy" model: new variants are constrained while accumulating evidence; proven variants get full allocation.

---

## 4. Phased Implementation Roadmap

### Phase 0 — Current State (Sprint 32, complete)

**Architecture:** Stacked guardrails (Risk Manager → Quality Engine → DynamicPositionSizer → Overflow Router → Orchestrator)

**Sizing model:** Grade-to-tier lookup table (C+=0.25%, B=0.75%, A=1.5%, A+=2.5% of allocated capital risk)

**Portfolio awareness:** None at sizing time. Post-hoc concentration check only.

**Experiment variants:** Equal nominal size to live strategies (same grade/tier lookup)

**Scope:** This phase is sufficient for Phase 5–6 validation (12 strategies, paper trading)

---

### Phase 1 — Kelly-Inspired Sizing with Uncertainty-Aware Edge (~Sprint 34–35)

**Objective:** Replace the grade-to-tier lookup with a principled edge estimate that incorporates sample size uncertainty and recency. Keep Risk Manager architecture intact.

**Changes from Phase 0:**
- Learning Loop → edge posterior computation: `(win_rate, trade_count, regime_distribution)` → `(mean_edge, edge_std)`
- DynamicPositionSizer enhanced: fractional Kelly using edge posterior, with variance-based shrinkage
- Drawdown response curve (Section 3.5): smooth derisking before circuit breakers
- Time-of-day multiplier (Section 3.4): rolling hourly edge estimates from session data
- Variant track record multiplier (Section 3.6): min-trades gate, linear scaling, recency weighting

**What remains unchanged:**
- Risk Manager structure (three-level gating: strategy → cross-strategy → account)
- Hard circuit breakers (non-overridable)
- Quality Engine components (pattern strength, catalyst, volume, regime)
- Overflow Router (capital availability check)

**Rationale:** Phase 1 delivers 60–70% of the allocation intelligence value with low architectural risk. It improves within the existing component boundaries rather than replacing them.

**Data requirements before Phase 1:**
- Minimum 200 live trades across all active strategies (to calibrate edge posteriors)
- Minimum 20 trading sessions (to calibrate time-of-day multipliers)
- Minimum 1 full regime cycle (trending → choppy → volatile) for regime-conditional edge estimates
- Learning Loop V1 producing reliable outcome correlations (Sprint 28 ✅ in place)

---

### Phase 2 — Full AllocationIntelligence (~Sprint 38+)

**Objective:** Replace the stacked guardrail chain with a unified AllocationIntelligence service. The service subsumes Risk Manager logic (strategy-level and cross-strategy checks), Quality Engine scoring, DynamicPositionSizer, and Overflow Router into a single callable that returns a recommended share count.

**Changes from Phase 1:**
- `AllocationIntelligence` class: takes `(signal, system_state)` → returns `AllocationRecommendation`
- `AllocationRecommendation`: `(shares, confidence, edge_estimate, portfolio_impact, dominant_factor, metadata)`
- Real-time portfolio correlation penalty (Section 3.2)
- Opportunity cost ranking for queued signals (Section 3.3)
- Hard Floor Enforcement: retained as independent non-bypassable layer (Section 8)
- Risk Manager: transitions from sizing authority to compliance monitor (DEC enforcement, audit logging)
- Order Manager: receives `AllocationRecommendation` instead of `OrderApprovedEvent`

**What the AllocationRecommendation replaces:**
- `OrderApprovedEvent` (binary approval → continuous recommendation)
- `modifications: dict` on `OrderApprovedEvent` (size adjustments → output of recommendation)

**What remains unchanged:**
- Hard circuit breakers (entirely separate layer, not touched)
- Broker abstraction, Order Manager order submission
- TradeLogger, MFE/MAE tracking, all persistence
- CounterfactualTracker, Learning Loop

**Rationale:** Phase 2 is a significant architectural refactor. It should only be attempted after Phase 1 has run for 60+ trading sessions, proving the edge estimation components are reliable, and after the ensemble scale (200+ variants) makes the correlation-aware sizing materially valuable.

---

## 5. Data Requirements

AllocationIntelligence's value is proportional to the quality and quantity of data available for each dimension. The following minimum data thresholds must be met before each phase can be reliably used:

| Dimension | Phase 1 Threshold | Phase 2 Threshold |
|-----------|-------------------|-------------------|
| Edge estimation (Section 3.1) | 200 trades per active strategy | 500+ trades; 3+ regime cycles |
| Portfolio correlation (Section 3.2) | Not required | 60+ trading sessions with ≥3 simultaneous positions |
| Opportunity cost (Section 3.3) | Not required | Regular signal queue contention (≥50 multi-signal windows) |
| Time-of-day multiplier (Section 3.4) | 20 trading sessions | 60+ sessions; stable by-hour win rate estimate |
| Drawdown response (Section 3.5) | 10+ drawdown events of varying severity | Same (Phase 1 sufficient) |
| Variant track record (Section 3.6) | 30+ shadow trades per active variant | 100+ trades; recency curve calibrated |

**Counterfactual data is not sufficient.** Shadow trades via CounterfactualTracker provide an approximation of live edge, but edge estimates for live sizing must come from actual executed trades. The distinction matters most for the time-of-day multiplier (shadow fills have different timing than live entries) and the portfolio correlation penalty (shadow positions don't consume real capital).

**Regime diversity requirement:** An edge estimate computed entirely in trending regimes will be overfit to that regime. Phase 1 edge posteriors are valid only when the training data spans at least one full regime transition (trending → choppy or choppy → volatile). RegimeVector history (stored in `data/regime_history.db`) provides the audit trail.

---

## 6. Architectural Sketch

### Phase 1 Architecture (Enhancement Within Current Boundaries)

```
SignalEvent
  │
  ▼
Risk Manager
  ├── Strategy-level checks (daily loss, circuit breakers)
  ├── Cross-strategy checks (concentration, correlation check)
  └── Account-level checks (buying power, daily loss limit)
  │
  │  [if approved]
  ▼
Enhanced DynamicPositionSizer  ◄─── AllocationIntelligence (Phase 1 components)
  ├── Edge posterior from Learning Loop (win_rate, trade_count, edge_std)
  ├── Fractional Kelly with uncertainty shrinkage
  ├── Time-of-day multiplier (rolling hourly edge)
  ├── Drawdown response curve (consecutive losses, % daily limit consumed)
  └── Variant track record multiplier (if experiment variant)
  │
  ▼
OrderApprovedEvent (with recommended shares)
  │
  ▼
Order Manager → Broker
```

**Key property:** Phase 1 adds intelligence to the DynamicPositionSizer. The Risk Manager continues to make binary approve/reject decisions. The Quality Engine continues to produce grades. The sizer produces share counts informed by the new inputs.

### Phase 2 Architecture (AllocationIntelligence Unification)

```
SignalEvent
  │
  ▼
AllocationIntelligence
  ├── Input: signal (strategy_id, symbol, entry, stop, pattern_strength)
  ├── Input: system_state (open_positions, correlation_matrix, daily_pnl,
  │         consecutive_losses, queued_signals, regime_vector, time_of_day)
  ├── Input: variant_record (track_record, shadow_days, recency_weights)
  │
  ├── Compute: edge_posterior (Learning Loop data)
  ├── Compute: kelly_fraction (edge_posterior, variance shrinkage)
  ├── Compute: correlation_penalty (CorrelationTracker, incremental variance)
  ├── Compute: time_of_day_multiplier (rolling hourly edge estimates)
  ├── Compute: drawdown_response (consecutive losses, daily PnL curve)
  ├── Compute: variant_maturity_multiplier (track record recency)
  ├── Compute: opportunity_rank (vs. queued signals)
  │
  └── Output: AllocationRecommendation(shares, confidence, edge_estimate,
                                        portfolio_impact, dominant_factor)
  │
  ▼
Hard Floor Enforcement (non-bypassable)
  ├── Daily loss circuit breaker (>3% → all trading stops)
  ├── Weekly loss circuit breaker (>5% → all trading stops)
  ├── Position size absolute minimum (0.25R floor from DEC-249)
  ├── Maximum single-symbol concentration (5% of account)
  └── Buying power check (shares × entry ≤ available_buying_power)
  │
  ▼
Order Manager → Broker
```

**What the Risk Manager becomes in Phase 2:** The Risk Manager transitions from a gating authority to a **compliance monitor**. It no longer makes approve/modify/reject decisions. Instead, it:
- Enforces the Hard Floor layer (non-overridable circuit breakers, position floors)
- Logs all AllocationIntelligence recommendations with full metadata for audit
- Emits `ComplianceViolationEvent` if AllocationIntelligence output violates a hard floor (should never happen if AI is correctly implemented — this is a safeguard)

---

## 7. Interface Design

### Phase 1: Enhanced DynamicPositionSizer

The Phase 1 interface is additive. `DynamicPositionSizer.calculate_shares()` gains additional optional inputs:

```python
@dataclass
class AllocationContext:
    """Additional context for Phase 1 enhanced sizing."""
    edge_posterior: EdgePosterior | None = None          # From Learning Loop
    time_of_day_multiplier: float = 1.0                  # 0.5–1.2 range
    drawdown_response_multiplier: float = 1.0            # 0.0–1.0 range
    variant_maturity_multiplier: float = 1.0             # 0.0–1.0 range

@dataclass
class EdgePosterior:
    mean_edge: float          # Mean of posterior edge estimate
    edge_std: float           # Standard deviation (uncertainty)
    trade_count: int          # Sample size driving the posterior
    regime_match_score: float # 0.0–1.0, how well training regime matches current
```

When `AllocationContext` is `None`, `calculate_shares()` falls back to the existing grade-to-tier lookup (Phase 0 behavior). This makes Phase 1 a backward-compatible enhancement.

### Phase 2: AllocationRecommendation

```python
@dataclass
class AllocationRecommendation:
    """Output of AllocationIntelligence.recommend()."""
    shares: int                        # Recommended position size (0 = do not trade)
    confidence: float                  # 0.0–1.0, confidence in edge estimate
    edge_estimate: float               # Expected edge per dollar risked
    portfolio_impact: PortfolioImpact  # Incremental correlation, concentration delta
    dominant_factor: str               # Which input most constrained the output
    kelly_fraction: float              # Raw Kelly fraction before adjustments
    size_adjustments: dict[str, float] # Per-dimension multipliers for audit log

@dataclass
class PortfolioImpact:
    incremental_variance_ratio: float  # How much this trade increases portfolio variance
    concentration_after: float         # Symbol concentration if trade executes
    correlation_penalty_applied: float # 0.0–1.0, reduction due to correlation
```

The `dominant_factor` field answers "why did the system size this at X shares?" with a single string: `"low_edge_uncertainty"`, `"high_correlation_penalty"`, `"drawdown_derisking"`, `"variant_immature"`, `"time_of_day_weak"`, or `"normal"` (no dominant constraint).

---

## 8. Hard Floor Definition

The Hard Floor is the boundary between "AllocationIntelligence decides" and "non-negotiable protection enforces." It is entirely separate from AllocationIntelligence and cannot be influenced by any factor AllocationIntelligence considers.

**Hard Floor rules (non-overridable in all phases):**

| Rule | Threshold | Action |
|------|-----------|--------|
| Daily loss limit | 3% of account (configurable) | All trading stops; circuit breaker fires; only manual resume |
| Weekly loss limit | 5% of account (configurable) | All trading stops; circuit breaker fires; resets next week |
| Consecutive loss breaker | Configurable N | All trading stops |
| Minimum position size | 0.25R floor (DEC-249) | If AllocationIntelligence returns <0.25R, reject entirely |
| Maximum single-symbol concentration | 5% of account | Reduce shares to fit; reject if reduction would go below 0.25R floor |
| Buying power check | shares × entry ≤ available_buying_power | Reduce or reject |
| EOD flatten | 3:55 PM ET | All positions closed; no new trades |

**What the Hard Floor does NOT do:**
- Optimize sizing within safe parameters (that's AllocationIntelligence's job)
- Consider edge quality, regime, or correlation (not its inputs)
- Respond smoothly to adverse conditions (that's the drawdown response in AllocationIntelligence)

**Principle:** The Hard Floor is the last line of defense against catastrophic outcomes. It is simple, auditable, and has no continuous parameters that could drift. If AllocationIntelligence produces a recommendation of 200 shares and the Hard Floor determines maximum allowable is 150 due to buying power, it returns 150 — no consultation with AllocationIntelligence.

**Circuit breakers remain owned by the Hard Floor, not AllocationIntelligence.** AllocationIntelligence's drawdown response curve (Section 3.5) is a smooth precursor to circuit breakers, not a substitute. A system that smoothly derisks as losses mount AND has non-bypassable hard limits at the extreme is more resilient than a system with only one of these mechanisms.

---

## 9. Relationship to Existing Components

### Risk Manager
- **Phase 1:** Unchanged. Risk Manager continues to make binary approve/reject decisions on SignalEvents. AllocationIntelligence enhancements live inside DynamicPositionSizer, which the Risk Manager calls after approval.
- **Phase 2:** Risk Manager transitions from gating authority to compliance monitor. Hard Floor enforcement moves to an explicit separate layer. Risk Manager retains audit logging and DEC enforcement.

### Quality Engine
- **Phase 1:** Unchanged. Grade still computed from 5 components (pattern strength, catalyst, volume profile, technical quality, regime alignment). Grade passed to enhanced DynamicPositionSizer as input, alongside the new edge posterior.
- **Phase 2:** Quality Engine grade becomes one input to AllocationIntelligence's edge estimation, not the sole determinant of size tier. High grade + uncertain edge → moderate size. High grade + mature track record + tight edge posterior → full size.

### Learning Loop
- **Phase 1:** Learning Loop V1 (Sprint 28) provides `WeightAnalyzer` and `CorrelationAnalyzer` outputs. AllocationIntelligence Phase 1 reads realized win rates, trade counts, and per-regime outcome breakdowns to compute edge posteriors.
- **Phase 2:** Learning Loop V2 (Sprint 40) provides richer calibration data for AllocationIntelligence. Edge posteriors become more reliable as trade counts accumulate. Recency weighting in the Learning Loop feeds directly into AllocationIntelligence's variant maturity multiplier.

### Experiment Pipeline
- **Phase 1:** Experiment variants use the same enhanced DynamicPositionSizer as live strategies. The variant track record multiplier (Section 3.6) directly consumes `CounterfactualTracker` shadow trade data and `ExperimentStore` promotion history.
- **Phase 2:** AllocationIntelligence treats live variants and shadow variants uniformly via the track record dimension. A variant that earns live status through PromotionEvaluator but has a thin live track record remains constrained by the maturity multiplier until evidence accumulates.

### Orchestrator
- **Phase 1:** Unchanged. Orchestrator continues to manage regime-based strategy activation/suspension, allocation percentages, and throttling. AllocationIntelligence operates at the per-signal level; Orchestrator operates at the per-strategy level.
- **Phase 2:** Orchestrator may consume `AllocationRecommendation.portfolio_impact` as a signal for regime-level rebalancing, but continues to own strategy-level activation decisions.

### CounterfactualTracker
- Both phases: CounterfactualTracker is a data source, not a logic layer. It provides the shadow trade outcomes that AllocationIntelligence uses for variant track record estimation. No changes to CounterfactualTracker are required for either phase.

---

## Appendix: Why Not Earlier?

Three prior architectural moments could have introduced AllocationIntelligence ideas:

**Sprint 24 (Quality Engine + DynamicPositionSizer):** The grade-to-tier lookup was deliberately chosen as a simple, auditable starting point. With fewer than 100 live trades per strategy, an edge posterior would have been untrustworthy.

**Sprint 28 (Learning Loop V1):** The Learning Loop was instrumented to collect the data AllocationIntelligence needs. It is not yet producing calibrated edge estimates because the dataset (paper trading from April 2026) is too small.

**Sprint 32 (Experiment Pipeline):** The ExperimentRunner and PromotionEvaluator were built to manage variant lifecycles at ensemble scale. They provide the infrastructure AllocationIntelligence needs to obtain per-variant track records.

The sequence is not accidental. ARGUS is building toward AllocationIntelligence in the correct order: first instruments the system (Learning Loop, CounterfactualTracker), then structures the variant universe (Experiment Pipeline), then uses the accumulated evidence to drive continuous sizing (AllocationIntelligence Phase 1, ~Sprint 34–35).

Attempting AllocationIntelligence before data maturity would produce sizing multipliers with error bars wider than the signal — worse than the current flat lookup table.

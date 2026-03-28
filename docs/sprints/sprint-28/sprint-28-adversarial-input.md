# Sprint 28: Adversarial Review Input Package

> Paste this document alongside the Sprint Spec and Specification by Contradiction into a fresh adversarial review conversation.

## Why This Sprint Warrants Adversarial Review

Sprint 28 introduces **ConfigProposalManager** — the first module in ARGUS that can programmatically modify live trading configuration files. Specifically, it writes to `config/quality_engine.yaml`, which controls how every trade setup is scored and sized. A bug in this module could silently alter position sizing, grade thresholds, or quality weights in ways that affect real trading decisions.

This is a Type C (Architecture-Shifting) sprint because of this config-modification capability. The adversarial review should stress-test the safety model around config changes, the data analysis pipeline's correctness, and the interaction between the Learning Loop and the existing trading pipeline.

---

## Architecture Context (Extracted)

### Quality Engine (Sprint 24)
The Quality Engine scores setups on 5 weighted dimensions:
- pattern_strength (30%) — from strategy's `_calculate_pattern_strength()` (0–100)
- catalyst_quality (25%) — from CatalystClassifier
- volume_profile (20%) — from RVOL
- historical_match (15%) — **currently stubbed at 50**
- regime_alignment (10%) — from RegimeVector match

Scores map to grades (A+ through C) via threshold config. Grades map to risk tier percentages via risk_tiers config. `min_grade_to_trade` (default C+) filters below-threshold signals.

Config lives in `config/quality_engine.yaml`. Pydantic validation via `QualityWeightsConfig`, `QualityThresholdsConfig`, `QualityRiskTiersConfig`.

### Config Architecture
ARGUS uses YAML → Pydantic BaseModel validation (DEC-032). Config is loaded at startup and held in memory. There is currently NO mechanism to reload config without restarting the application. Sprint 28 introduces the first config reload path.

Config files that affect trading:
- `config/quality_engine.yaml` — weights, thresholds, risk tiers (Sprint 28 target)
- `config/system_live.yaml` — system-wide settings
- `config/risk_limits.yaml` — risk parameters
- `config/orchestrator.yaml` — orchestrator settings
- `config/strategies/*.yaml` — per-strategy parameters

Sprint 28 ONLY modifies `quality_engine.yaml`. Other config files are NOT in scope.

### Data Sources for Analysis
1. **Trades (argus.db):** Actual trade outcomes with quality metadata (quality_score, quality_grade, per-dimension scores stored in quality_history table)
2. **Counterfactual positions (counterfactual.db):** Theoretical outcomes for every rejected signal (Sprint 27.7). Schema includes rejection_stage, rejection_reason, quality_score, quality_grade, regime_vector_snapshot, theoretical_pnl, theoretical_r_multiple.
3. **Quality history (argus.db):** Every scored setup (traded and untraded) with per-dimension scores and regime context.

### Existing Filter Accuracy
`FilterAccuracy` (Sprint 27.7) already computes per-breakdown accuracy: "what percentage of rejected signals would have lost money?" Breakdowns by stage, reason, grade, strategy, regime. Sprint 28's ThresholdAnalyzer complements this with the reverse view: "of signals that passed, what percentage were profitable?"

### Event Flow (Signal Pipeline)
```
Strategy generates signal (share_count=0, pattern_strength=N)
    ↓
_process_signal() in main.py:
    1. Quality Engine scores setup → quality_grade, quality_score
    2. If grade < min_grade_to_trade → REJECT (SignalRejectedEvent → Counterfactual)
    3. DynamicPositionSizer maps grade → risk tier → share count
    4. If share_count == 0 → REJECT (SignalRejectedEvent → Counterfactual)
    5. Risk Manager evaluates → APPROVE / APPROVE_MODIFIED / REJECT
    6. If REJECT → SignalRejectedEvent → Counterfactual
    7. If overflow capacity reached → SignalRejectedEvent(BROKER_OVERFLOW) → Counterfactual
    8. Order placed via Broker
```

Sprint 28 does NOT modify this pipeline. It only reads the outputs (trades, counterfactual positions, quality history) and recommends changes to the config that feeds step 1.

---

## Key Decisions to Challenge

### 1. ConfigProposalManager Safety Model
The module can write to `quality_engine.yaml`. Safety guardrails:
- Pydantic validation before every write
- `max_change_per_cycle` (±0.10 per weight per report)
- Weight changes enforce sum-to-1.0 via proportional redistribution
- Changes queue until next session start (not mid-session)
- Config change history for audit trail
- Revert capability

**Challenge:** Is this sufficient? What failure modes aren't covered? What about:
- Concurrent config writes (two browser tabs approving at the same time)?
- Race condition between config read and config write?
- File system permission errors mid-write leaving corrupt YAML?
- The proportional redistribution algorithm — does it handle edge cases (all weight moved to one dimension)?
- What if someone approves 10 proposals in rapid succession, each within max_change_per_cycle, but the cumulative effect is extreme?

### 2. Analysis Methodology
V1 uses Spearman rank correlation to assess whether quality dimension scores predict trade outcomes.

**Challenge:**
- Spearman correlation assumes monotonic relationship. What if the relationship is non-monotonic (e.g., medium catalyst quality predicts best outcomes, with both low and high underperforming)?
- With small sample sizes (early paper trading), Spearman can be highly unstable. Is the minimum sample threshold of 10 sufficient?
- The analysis combines trades (executed, subject to slippage/timing) with counterfactual positions (theoretical fills from TheoreticalFillModel). Are these comparable? Should they be weighted differently?
- Is Spearman the right metric? Would point-biserial correlation (for binary win/loss) be more appropriate?

### 3. Apply Timing Model
Changes queue until "next session start." But what defines "next session start"?

**Challenge:**
- Is this market open (9:30 AM ET)? Application restart? Pre-market data load phase?
- What if the application crashes and restarts mid-session — does the queued change apply?
- What if the user runs a weekend analysis and approves changes — when do they apply?
- Is there a risk of the user forgetting about queued changes?

### 4. Auto Post-Session Trigger
Analysis runs automatically after EOD flatten.

**Challenge:**
- What if EOD flatten fails or is incomplete (e.g., some positions couldn't be closed)?
- What if the Databento session is still winding down when the trigger fires?
- Is 120 seconds sufficient for analysis on 30 days of data?
- What if the user is still manually reviewing positions when the trigger fires?

### 5. Forward-Compatible Schema
LearningReport schema is designed for Sprint 32.5 ExperimentRegistry compatibility.

**Challenge:**
- What specific schema constraints does ExperimentRegistry impose? Is the compatibility claim verifiable without Sprint 32.5 implemented?
- Is the schema flexible enough to accommodate Learning Loop V2's ensemble-level analysis without breaking changes?

---

## Probing Angles

### Assumption Mining
1. The assumption that Spearman correlation is meaningful with <100 data points
2. The assumption that trade outcomes and counterfactual outcomes are comparable
3. The assumption that quality dimension scores are independently useful (no interaction effects)
4. The assumption that regime labels are stable enough for per-regime analysis
5. The assumption that config file writes are atomic (what about power failure mid-write?)

### Failure Mode Analysis
1. ConfigProposalManager writes corrupt YAML → application won't start
2. Analysis runs on insufficient data → generates misleading recommendations → user approves → quality scoring degraded
3. Weight redistribution creates pathological allocation (e.g., 0.96 on one dimension, 0.01 on others)
4. Auto trigger fires during manual position cleanup → interferes with operator workflow
5. Multiple rapid approvals circumvent max_change_per_cycle guard

### Future Regret (3-Month Horizon)
1. Will the LearningReport schema actually be compatible with ExperimentRegistry?
2. Will the ConfigProposalManager's YAML-file approach scale when config moves to a database?
3. Will the Spearman correlation approach produce useful recommendations, or will we need to replace it entirely?
4. Will the Performance page location be right, or will users want a dedicated Learning page?

### Integration Stress
1. The config reload path is NEW — no other module reloads config at runtime. Is the reload atomic? Thread-safe? Does it affect in-flight signal processing?
2. The auto trigger hooks into main.py's EOD flatten flow. Does this create a coupling that makes EOD flatten harder to modify in future sprints?
3. LearningStore creates a 5th SQLite database (argus.db, counterfactual.db, evaluation.db, regime_history.db, learning.db). Is DB proliferation becoming a maintenance burden?

---

## Relevant DEC References

- DEC-032: YAML → Pydantic config validation
- DEC-277: Fail-closed on missing data
- DEC-300: Config-gated features
- DEC-330–341: Quality Engine architecture
- DEC-345: Separate SQLite databases per subsystem
- DEC-357: ExperimentRegistry forward-compatibility
- DEC-369–377: Sprint 27.95 reconciliation/overflow (data quality context)

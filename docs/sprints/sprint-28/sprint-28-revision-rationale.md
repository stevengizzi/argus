# Sprint 28: Revision Rationale

> Post-adversarial-review revision log. All amendments adopted per Steven's approval.
> Date: March 28, 2026

## Summary

18 findings (3 Critical, 4 Significant, 11 Minor). All resolved via amendments to the Sprint Spec and Spec by Contradiction. No session re-split required — net effect is slight scope increase in analyzers (S2a/S2b) and slight scope decrease in config management (S4). Session count holds at 10.5.

## Key Design Changes

### 1. ConfigProposalManager: Startup-Only Application (Amendments 1, 2, 9)
**Before:** In-memory config reload on approval during runtime.
**After:** YAML written only at application startup via `apply_pending()`. Atomic write (tempfile + os.rename). Backup before write. No runtime reload.
**Why:** ARGUS has no existing runtime config reload path. Introducing one creates concurrency risks with the signal pipeline. Application restarts between sessions anyway (IB Gateway nightly resets). This is safer AND simpler.
**Impact:** S4 scope decreases (no reload mechanism needed). `apply_timing` config field removed.

### 2. Cumulative Drift Guard (Amendment 2)
**Before:** Only per-cycle `max_change_per_cycle` guard.
**After:** Added `max_cumulative_drift` (±0.20 per dimension over rolling 30-day window) to prevent gradual drift via sequential approvals.
**Impact:** New config fields. Guard logic in S4.

### 3. Separate-by-Source Analysis (Amendment 3)
**Before:** Trades and counterfactual records blended in single correlation.
**After:** Correlations computed separately by source. Trade-sourced preferred when sufficient; counterfactual fallback with MODERATE cap. Divergence > 0.3 flagged.
**Why:** Trades have real slippage; counterfactual uses theoretical fills. Different data quality.
**Impact:** S2a/S2b analyzers get source-separated computation.

### 4. Statistical Rigor (Amendments 4, 5, 15)
**Before:** min_sample_count=10, no p-value check, no recommendation formula.
**After:** min_sample_count=30, p-value < 0.10 required, explicit weight recommendation formula (normalized positive correlations), zero-variance outcome guard.
**Why:** N=10 is too small for meaningful Spearman. Explicit formula prevents ambiguity in implementation.

### 5. Proposal Supersession (Amendment 6)
**Before:** Old proposals remain PENDING indefinitely.
**After:** New report auto-supersedes all prior PENDING proposals. Only latest report's proposals are actionable.
**Why:** Prevents approval of stale recommendations based on outdated data.
**Impact:** SUPERSEDED status added. LearningService auto-supersedes on new report.

### 6. Implementation Clarifications (Amendments 7, 8, 10–14, 16)
- Regime grouping by `primary_regime` enum only (not full 11-dimension vector)
- Quality history schema verification as S1 pre-flight step
- Auto trigger via Event Bus (`SessionEndEvent`) not direct callback
- Zero-trade session guard on auto trigger
- Retention protection for reports referenced by APPLIED/REVERTED proposals
- ThresholdAnalyzer decision criteria: missed_opportunity > 0.40 or correct_rejection < 0.50
- Performance page: new "Learning" tab (lazy-loaded)
- DEF item for DB proliferation assessment post-Sprint 32.5

## Config Field Changes (Net)

**Removed:** `learning_loop.apply_timing`
**Added:**
- `learning_loop.max_cumulative_drift` (default 0.20)
- `learning_loop.cumulative_drift_window_days` (default 30)
- `learning_loop.correlation_p_value_threshold` (default 0.10)
**Changed:** `learning_loop.min_sample_count` default 10 → 30

## Impact on Session Estimates

No session re-split needed. S4 net simpler (no reload). S2a/S2b slightly larger (source separation). S5 gains SessionEndEvent. Overall: 10.5 sessions unchanged.

# Sprint 28: Review Context File

> Shared reference for all Tier 2 session reviews.
> All spec content below reflects the 16 amendments from adversarial review.

## Canonical Spec Documents
- **Sprint Spec (amended):** `sprint-28-sprint-spec.md`
- **Spec by Contradiction (amended):** `sprint-28-spec-by-contradiction.md`
- **Adversarial Review Output:** `sprint-28-adversarial-review-output.md`
- **Revision Rationale:** `sprint-28-revision-rationale.md`

## Critical Amendments — Verify in EVERY Review

1. **(A1) No in-memory config reload.** apply_pending() at startup only. Atomic write (tempfile + os.rename). Backup. YAML parse fail → CRITICAL, refuse to start.
2. **(A2) Cumulative drift guard.** max_cumulative_drift ±0.20/dimension, 30-day window.
3. **(A3) Separate-by-source analysis.** Trade and counterfactual correlations separate. Divergence > 0.3 flagged. Trade preferred, counterfactual fallback with MODERATE cap.
4. **(A4) min_sample_count=30 (not 10). P-value < 0.10 required.**
5. **(A5) Weight formula:** max(0,ρ_i) / Σmax(0,ρ_j), stub dimensions held constant.
6. **(A6) Proposal supersession.** SUPERSEDED status. Prior PENDING auto-expired on new report. Full state machine: PENDING → APPROVED/DISMISSED/SUPERSEDED/REJECTED_GUARD/REJECTED_VALIDATION → APPLIED → REVERTED.
7. **(A7) Regime grouping by primary_regime** (5-value enum) only.
8. **(A10) Auto trigger zero-trade guard.** Skip if 0 trades AND 0 counterfactual.
9. **(A11) Retention protection** for APPLIED/REVERTED-referenced reports.
10. **(A12) Threshold criteria:** missed > 0.40 → lower. correct < 0.50 → raise.
11. **(A13) Auto trigger via SessionEndEvent** on Event Bus, not direct callback.
12. **(A14) Learning tab** on Performance page, lazy-loaded.
13. **(A15) Zero-variance outcome guard** → INSUFFICIENT_DATA.

## Config Fields (Final — 13 fields, post-amendment)

```yaml
learning_loop:
  enabled: true                         # Config-gate (DEC-300)
  analysis_window_days: 30              # Lookback for analysis
  min_sample_count: 30                  # Raised from 10 (A4)
  min_sample_per_regime: 5              # Per-regime minimum
  max_weight_change_per_cycle: 0.10     # Per-proposal guard
  max_cumulative_drift: 0.20            # Rolling window guard (A2)
  cumulative_drift_window_days: 30      # Window for cumulative guard
  auto_trigger_enabled: true            # Post-session auto analysis
  correlation_window_days: 20           # Trailing window for correlation
  report_retention_days: 90             # Report cleanup
  correlation_threshold: 0.7            # Flagging threshold
  weight_divergence_threshold: 0.10     # Weight recommendation threshold
  correlation_p_value_threshold: 0.10   # Statistical significance (A4)
```

## Sprint-Level Regression Checklist

- [ ] QE produces identical scores when no proposals applied
- [ ] quality_engine.yaml weights sum to 1.0 after any proposal application
- [ ] All 7 strategies evaluate and generate signals correctly
- [ ] All existing API endpoints work (no route conflicts)
- [ ] Shutdown completes within timeout even with auto trigger
- [ ] Counterfactual and overflow routing unaffected
- [ ] OutcomeCollector queries are read-only
- [ ] learning.db uses WAL, doesn't affect other DBs
- [ ] All learning_loop.* YAML keys recognized by Pydantic model
- [ ] Full pytest passes: `python -m pytest --ignore=tests/test_main.py -n auto -q`
- [ ] Full Vitest passes: `cd argus/ui && npm test`
- [ ] No test hangs

## Sprint-Level Escalation Criteria

**Critical (Immediate):**
1. ConfigProposalManager writes invalid YAML
2. Config application causes scoring regression
3. Auto trigger blocks/delays shutdown
4. Mathematically impossible results (correlation outside [-1,1])

**Significant (After 1 Failed Fix):**
5. OutcomeCollector returns mismatched data
6. LearningStore fails to persist
7. Config change history gaps
8. Frontend mutations don't update UI

# Sprint 28: Learning Loop V1

> **Amended:** March 28, 2026 — incorporates all 16 amendments from adversarial review.
> See `sprint-28-revision-rationale.md` for change log.

## Goal

Close the feedback loop between the Quality Engine's predictions and actual trading outcomes. Build the analysis infrastructure, human-approved config proposal pipeline, and Performance page UI to surface structured weight/threshold/correlation recommendations — so the Quality Engine's hand-tuned parameters can be empirically calibrated from paper trading data.

## Scope

### Deliverables

1. **OutcomeCollector** — Unified read layer that queries trades (argus.db), counterfactual positions (counterfactual.db), and quality history (argus.db quality_history table), normalizes into a common analysis format with quality dimension scores, regime context, and P&L outcomes. Date-range and strategy-id filtering. Graceful handling of empty databases. Each record tagged with source ("trade" or "counterfactual") for separate-by-source analysis.

2. **WeightAnalyzer** — For each of the 5 quality dimensions, computes Spearman rank correlation between dimension score and trade P&L. **Computes correlations separately for trade-sourced and counterfactual-sourced records (A3).** Only used for recommendations when p-value < `correlation_p_value_threshold` (default 0.10) (A4). Trade-sourced preferred when sufficient; counterfactual fallback with MODERATE cap. Source divergence > 0.3 flagged (A3). Detects zero-variance dimensions and zero-variance P&L outcomes → INSUFFICIENT_DATA (A15). **Weight formula (A5):** recommended_weight_i = max(0, ρ_i) / Σ max(0, ρ_j), scaled to non-stub allocation. Stub dimensions held constant. Clamped by max_change_per_cycle. **Per-regime (A7):** groups by primary_regime (5-value MarketRegime enum) only. Adaptive sample threshold.

3. **ThresholdAnalyzer** — Per grade: missed-opportunity rate and correct-rejection rate from counterfactual data; pass-through profitability from trade data (A3). **Decision criteria (A12):** missed_opportunity_rate > 0.40 → lower; correct_rejection_rate < 0.50 → raise. Both can fire simultaneously. Min sample: 30 (A4).

4. **CorrelationAnalyzer** — Pairwise Pearson correlation of daily P&L. Trade-sourced preferred (A3). Flags pairs > threshold (default 0.7). Excludes zero-trade strategies.

5. **LearningReport** — Frozen dataclass. Data quality preamble, weight/threshold/correlation results, confidence tiers, version field for ExperimentRegistry forward-compat.

6. **LearningStore** — SQLite `data/learning.db` (DEC-345). WAL. Reports, proposals, change history. **Retention protects APPLIED/REVERTED-referenced reports (A11).** Proposal supersession support (A6).

7. **LearningService** — Orchestrator. Pipeline: collect → analyze → report → persist → supersede prior PENDING (A6) → generate proposals. Config-gated.

8. **ConfigProposalManager** — Approval → YAML changes at startup only (A1). `apply_pending()` at boot: reads APPROVED proposals by timestamp, applies sequentially, validates cumulative through Pydantic, atomic write (tempfile + os.rename) with backup (A9). `max_change_per_cycle` (±0.10) + `max_cumulative_drift` (±0.20 over 30 days) (A2). Weight sum-to-1.0 enforcement. YAML parse failure → CRITICAL, refuse to start. No in-memory reload (A1). Single write point `apply_change()` for future DB migration.

   **State Machine (A6):** PENDING → APPROVED/DISMISSED/SUPERSEDED/REJECTED_GUARD/REJECTED_VALIDATION. APPROVED → APPLIED (startup). APPLIED → REVERTED. All others illegal (400).

9. **REST API** — 8 endpoints (trigger, reports, proposals CRUD, config-history). JWT. 409 on concurrent. 400 on SUPERSEDED→APPROVED (A6).

10. **CLI** — `scripts/run_learning_analysis.py`. --window-days, --strategy-id, --dry-run.

11. **Auto Post-Session Trigger** — Subscribes to `SessionEndEvent` via Event Bus (A13). Zero-trade guard: skips when 0 trades AND 0 counterfactual; runs on counterfactual-only (A10). Timeout 120s. Fire-and-forget.

12. **Performance Page — Learning Insights Panel** — New "Learning" tab (A14), lazy-loaded. Recommendations with approve/dismiss + notes. Confidence badges. Report selector. Regime toggle.

13. **Performance Page — Strategy Health Bands** — Observational only. Green/amber/red against baseline. On Learning tab.

14. **Performance Page — Correlation Matrix** — Recharts heatmap. Blue-red scale (accessible). Flagged pairs. On Learning tab.

15. **Dashboard — Learning Summary Card** — Pending count, last analysis, data quality. Links to Performance Learning tab.

### Config Changes (13 fields)

| YAML Path | Pydantic Field | Default |
|-----------|---------------|---------|
| learning_loop.enabled | enabled | true |
| learning_loop.analysis_window_days | analysis_window_days | 30 |
| learning_loop.min_sample_count | min_sample_count | 30 |
| learning_loop.min_sample_per_regime | min_sample_per_regime | 5 |
| learning_loop.max_weight_change_per_cycle | max_weight_change_per_cycle | 0.10 |
| learning_loop.max_cumulative_drift | max_cumulative_drift | 0.20 |
| learning_loop.cumulative_drift_window_days | cumulative_drift_window_days | 30 |
| learning_loop.auto_trigger_enabled | auto_trigger_enabled | true |
| learning_loop.correlation_window_days | correlation_window_days | 20 |
| learning_loop.report_retention_days | report_retention_days | 90 |
| learning_loop.correlation_threshold | correlation_threshold | 0.7 |
| learning_loop.weight_divergence_threshold | weight_divergence_threshold | 0.10 |
| learning_loop.correlation_p_value_threshold | correlation_p_value_threshold | 0.10 |

### Performance Benchmarks

| Metric | Target |
|--------|--------|
| Analysis pipeline (30-day, 7 strategies) | < 5 seconds |
| Report retrieval API | < 100ms p95 |
| Config apply at startup | < 500ms |
| Performance page load | No regression (Learning tab lazy) |

## Dependencies
- Sprint 27.7 (Counterfactual Engine), 27.5 (Evaluation Framework), 27.6 (Regime Intelligence), 24 (Quality Engine), 27.95 (Broker Safety)
- Paper trading data accumulation

## Relevant Decisions
DEC-345, DEC-300, DEC-277, DEC-330–341, DEC-357, DEC-275, DEC-369–377

## Relevant Risks
- ConfigProposalManager writes trading config → mitigated by Pydantic, guards, atomic writes, startup-only, human approval
- Sparse data misleading correlations → mitigated by min_sample=30, p-value, confidence tiers, source separation

## Session Count: 10.5 (10 + 0.5 contingency)

# Sprint 28 Work Journal — Learning Loop V1

> Paste this into a fresh Claude.ai conversation to create the Sprint 28 Work Journal.
> Keep this conversation open for the duration of the sprint. Bring issues here as they arise.

---

## Sprint Context

**Sprint 28: Learning Loop V1**
**Goal:** Close the feedback loop between the Quality Engine's predictions and actual trading outcomes. Build analysis infrastructure, human-approved config proposal pipeline, and Performance page UI.
**Type:** C (Architecture-Shifting) — ConfigProposalManager can modify live trading config
**Execution mode:** Human-in-the-loop
**Adversarial review:** Completed. 16 amendments adopted (3 Critical, 4 Significant, 9 Minor).

**Key amendment (must be in every implementer's mind):** No in-memory config reload. Changes apply at application startup only via `apply_pending()`. Atomic writes. Backup before every write.

---

## Session Breakdown

| Session | Scope | Score | Creates | Modifies | Status |
|---------|-------|-------|---------|----------|--------|
| S1 | Data Models + Outcome Collector | 13 | `learning/__init__.py`, `models.py`, `outcome_collector.py` | None | |
| S2a | Weight + Threshold Analyzers | 12 | `weight_analyzer.py`, `threshold_analyzer.py` | None | |
| S2b | Correlation Analyzer | 8 | `correlation_analyzer.py` | None | |
| S3a | LearningStore (SQLite) | 11 | `learning_store.py` | None | |
| S3b | LearningService + CLI | 13 | `learning_service.py`, `scripts/run_learning_analysis.py` | None | |
| S4 | ConfigProposalManager | 13 | `config_proposal_manager.py`, `config/learning_loop.yaml` | `quality_engine.py`, QE Pydantic model | |
| S5 | REST API + Auto Trigger | 13 | `api/routes/learning.py` | `server.py`, `main.py`, `events.py` | |
| S6a | Frontend Hooks + Cards | 13 | 5 TS/TSX files | None | |
| S6b | Learning Insights Panel | 9 | `LearningInsightsPanel.tsx` | Performance page | |
| S6c | Health Bands + Correlation + Dashboard | 12 | 3 TSX files | Performance page, Dashboard | |
| S6cf | Visual-review fixes (contingency) | ~4 | TBD | TBD | |

**Dependency chain:**
```
S1 → S2a ──→ S3a → S3b ──→ S5 → S6a → S6b → S6c → S6cf
  └→ S2b ──┘               ↑
     S4 ────────────────────┘
```

**Parallelization windows:**
1. S2a ∥ S2b (both read S1 output, create independent files)
2. S4 ∥ S3a→S3b (zero file overlap, converge at S5)

---

## Do-Not-Modify Files

These files must NOT be modified by any session:
- Any strategy files (`argus/strategies/*`)
- `core/risk_manager.py`
- `core/orchestrator.py`
- `execution/order_manager.py`
- `intelligence/counterfactual.py`
- `intelligence/counterfactual_store.py`
- `intelligence/filter_accuracy.py`
- `analytics/evaluation.py`
- `analytics/comparison.py`
- `config/system_live.yaml`
- `config/orchestrator.yaml`
- `config/risk_limits.yaml`
- `config/counterfactual.yaml`
- Any existing test files

---

## Issue Category Definitions

When reporting issues during the sprint, classify them:

- **SCOPE_GAP:** Something the spec should have covered but didn't. Needs triage — does it block the current session, or can it be deferred?
- **PRIOR_BUG:** Bug in code from a previous sprint discovered during this one. Log as DEF item. Fix only if it blocks current session.
- **SPEC_AMBIGUITY:** The spec is unclear about how to handle a specific case. Needs clarification before proceeding.
- **COMPACTION_RISK:** Session is approaching context limits. May need to split remaining work.
- **ESCALATION:** Something that triggers the escalation criteria (see below).
- **CARRY_FORWARD:** Work that couldn't be completed in the current session and needs to be added to a subsequent session.

---

## Escalation Triggers

Escalate to Tier 3 review if:

**Critical (Immediate):**
1. ConfigProposalManager writes invalid YAML
2. Config application causes scoring regression
3. Auto trigger blocks or delays shutdown
4. Analysis produces mathematically impossible results (correlation outside [-1,1], negative rates)

**Significant (After 1 Failed Fix):**
5. OutcomeCollector returns mismatched data
6. LearningStore fails to persist
7. Config change history gaps
8. Frontend mutations don't update UI

---

## Reserved Numbering

- **DEC range:** Check current max in `docs/decision-log.md` before assigning. Sprint 27.95 used DEC-369–377. Next available: DEC-378+.
- **DEF range:** Check current max in `CLAUDE.md`. Sprint 27.9 logged DEF-103. Next available: DEF-104+.
- **DEF-NEW (from adversarial review):** DB proliferation assessment post-Sprint 32.5. Assign number at doc-sync.

---

## Key Amendments from Adversarial Review

These 16 amendments are adopted. Implementation sessions must follow them:

1. **A1 (Critical):** No in-memory config reload. apply_pending() at startup only. Atomic write.
2. **A2 (Critical):** Cumulative drift guard: max_cumulative_drift ±0.20 over 30-day window.
3. **A3 (Significant):** Separate analysis by data source (trade vs counterfactual).
4. **A4 (Significant):** min_sample_count raised to 30. P-value < 0.10 required.
5. **A5 (Significant):** Weight recommendation formula: normalized positive correlations.
6. **A6 (Significant):** Proposal supersession: SUPERSEDED status, auto-expire prior PENDING.
7. **A7 (Minor):** Regime grouping by primary_regime only (5-value enum).
8. **A8 (Minor):** Quality history schema verification in S1.
9. **A9 (Minor):** Atomic write spec (tempfile + os.rename). Covered by A1.
10. **A10 (Minor):** Auto trigger zero-trade guard.
11. **A11 (Minor):** Retention protection for APPLIED/REVERTED-referenced reports.
12. **A12 (Minor):** ThresholdAnalyzer criteria: missed>0.40 → lower, correct<0.50 → raise.
13. **A13 (Minor):** Auto trigger via SessionEndEvent on Event Bus, not direct callback.
14. **A14 (Minor):** Performance page: new "Learning" tab, lazy-loaded.
15. **A15 (Minor):** Zero-variance outcome guard → INSUFFICIENT_DATA.
16. **A16 (Minor):** DEF item for DB proliferation assessment.

---

## Verdict Tracking

Record session verdicts here as they complete:

| Session | Verdict | Test Delta | Notes |
|---------|---------|------------|-------|
| S1 | | | |
| S2a | | | |
| S2b | | | |
| S3a | | | |
| S3b | | | |
| S4 | | | |
| S5 | | | |
| S6a | | | |
| S6b | | | |
| S6c | | | |
| S6cf | | | |

---

## Outstanding Items

Track items that need attention across sessions:

| Item | Category | Discovered In | Resolved In | Notes |
|------|----------|--------------|-------------|-------|
| | | | | |

---

## Config Fields (Final — 13 fields)

For quick reference during implementation:

```yaml
learning_loop:
  enabled: true
  analysis_window_days: 30
  min_sample_count: 30
  min_sample_per_regime: 5
  max_weight_change_per_cycle: 0.10
  max_cumulative_drift: 0.20
  cumulative_drift_window_days: 30
  auto_trigger_enabled: true
  correlation_window_days: 20
  report_retention_days: 90
  correlation_threshold: 0.7
  weight_divergence_threshold: 0.10
  correlation_p_value_threshold: 0.10
```

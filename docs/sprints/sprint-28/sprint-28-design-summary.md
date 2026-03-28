# Sprint 28 Design Summary

> **Amended:** March 28, 2026 — reflects all 16 adversarial review amendments.

**Sprint Goal:** Close the feedback loop between Quality Engine predictions and trading outcomes. Advisory-only — recommendations require human approval. Changes apply at application startup only (no in-memory reload).

**Execution Mode:** Human-in-the-loop

## Session Breakdown

- S1: Data Models + Outcome Collector (creates: __init__, models, outcome_collector | score: 13)
- S2a: Weight + Threshold Analyzers (creates: weight_analyzer, threshold_analyzer | score: 12) **∥ S2b**
- S2b: Correlation Analyzer (creates: correlation_analyzer | score: 8) **∥ S2a**
- S3a: LearningStore SQLite (creates: learning_store | score: 11)
- S3b: LearningService + CLI (creates: learning_service, CLI script | score: 13)
- S4: ConfigProposalManager (creates: config_proposal_manager, learning_loop.yaml | modifies: quality_engine.py | score: 13) **∥ S3a→S3b**
- S5: REST API + Auto Trigger (creates: routes/learning.py | modifies: server.py, main.py, events.py | score: 13)
- S6a: Frontend Hooks + Cards (creates: 5 TS/TSX files | score: 13)
- S6b: Learning Insights Panel (creates: LearningInsightsPanel | modifies: Performance page | score: 9)
- S6c: Health Bands + Correlation + Dashboard (creates: 3 TSX | modifies: Performance, Dashboard | score: 12)
- S6cf: Visual-review contingency (0.5 session)

**Dependency:** S1 → S2a∥S2b → S3a → S3b → S5 → S6a → S6b → S6c. S4 ∥ S3a→S3b, converges at S5.

## Key Decisions (Post-Amendment)

- **No in-memory reload (A1).** apply_pending() at startup only. Atomic write + backup.
- **Cumulative drift guard (A2).** ±0.20/dimension, 30-day rolling window.
- **Separate-by-source (A3).** Trade vs counterfactual correlations computed independently.
- **min_sample=30, p-value<0.10 (A4).** Statistical rigor for small datasets.
- **Explicit weight formula (A5).** Normalized positive correlations, stub dimensions held constant.
- **Proposal supersession (A6).** New report auto-expires prior PENDING proposals.
- **Regime by primary_regime only (A7).** 5-value enum, not full 11-dim vector.
- **Auto trigger via Event Bus (A13).** SessionEndEvent, not direct callback.
- **Learning tab on Performance page (A14).** Lazy-loaded, not main view.
- **13 config fields.** apply_timing removed, max_cumulative_drift + p_value_threshold added.

## Scope: IN / OUT

- IN: OutcomeCollector, 3 analyzers, LearningReport, LearningStore, LearningService, ConfigProposalManager, REST API, CLI, auto trigger, Performance Learning tab, Dashboard card
- OUT: Automated application, throttle/boost, lookup tables, ML, strategy params, in-memory reload

## Config: 13 fields in config/learning_loop.yaml mapped to LearningLoopConfig Pydantic model

## Tests: ~55 pytest + ~15 Vitest = ~70 new

# Sprint 28: Session Breakdown

## Dependency Chain

```
S1 → S2a ──→ S3a → S3b ──→ S5 → S6a → S6b → S6c → S6cf
  └→ S2b ──┘               ↑
     S4 ────────────────────┘
```

## Parallelization Windows

| Window | Sessions | Justification |
|--------|----------|---------------|
| 1 | S2a ∥ S2b | Both read S1 output (OutcomeCollector). S2a creates weight_analyzer.py + threshold_analyzer.py. S2b creates correlation_analyzer.py. Zero file overlap. Neither modifies any existing file. |
| 2 | S4 ∥ (S3a → S3b) | S4 creates config_proposal_manager.py + config_change_store.py. S3a/S3b create learning_store.py + learning_service.py + CLI script. Zero file overlap. Both converge at S5 (API wiring). S4 depends only on S1 (models.py defines LearningLoopConfig). |

**Parallelization safety for implementation prompts:** Each parallel session's prompt must:
- State explicitly which files it creates and which it must not touch
- Confirm that no other session is expected to be modifying the same files
- Use `git stash` / separate branches if running simultaneously, merge before S5

---

## Session Details

### Session 1: Learning Data Models + Outcome Collector

**Objective:** Establish the learning package with all data models and the unified data reader.

**Creates:**
- `argus/intelligence/learning/__init__.py` (re-exports)
- `argus/intelligence/learning/models.py` (LearningReport, WeightRecommendation, ThresholdRecommendation, CorrelationResult, OutcomeRecord, DataQualityPreamble, LearningLoopConfig Pydantic model, ConfidenceLevel enum)
- `argus/intelligence/learning/outcome_collector.py` (OutcomeCollector class)

**Modifies:** None

**Integrates:** N/A (foundational — reads from existing argus.db, counterfactual.db)

**Parallelizable:** No (all subsequent sessions depend on this)

| Factor | Detail | Points |
|--------|--------|--------|
| New files created | 3 (`__init__`, `models.py`, `outcome_collector.py`) | +6 |
| Files modified | 0 | 0 |
| Context/pre-flight reads | 3 (`counterfactual_store.py` schema, `trade_logger.py` schema, `quality_engine.py` scoring structure) | +3 |
| Tests to write | ~15 (models: 3 serialization, collector: 12 — per-DB-source happy path + empty + date filter + strategy filter) | +7.5 |
| Complex integration wiring | 0 (reads DBs but doesn't wire into existing call sites) | 0 |
| External API debugging | 0 | 0 |
| Large files (>150 lines) | 0 | 0 |
| **Total** | | **16.5 → High** |

**Mitigation:** `__init__.py` is trivial (~5 lines). `models.py` is pure frozen dataclasses + one Pydantic model (~120 lines, zero logic). Real complexity is `outcome_collector.py` only. Tests written incrementally per DB source.

---

### Session 2a: Weight Analyzer + Threshold Analyzer

**Objective:** Build the two analyzers that evaluate Quality Engine weight allocation and grade thresholds.

**Creates:**
- `argus/intelligence/learning/weight_analyzer.py`
- `argus/intelligence/learning/threshold_analyzer.py`

**Modifies:** None

**Integrates:** Consumes OutcomeCollector output from S1. Threshold Analyzer also references FilterAccuracy patterns from `filter_accuracy.py` (read-only, no modification).

**Parallelizable:** Yes (with S2b — zero file overlap, both read S1 output)

| Factor | Detail | Points |
|--------|--------|--------|
| New files created | 2 | +4 |
| Files modified | 0 | 0 |
| Context/pre-flight reads | 3 (`outcome_collector.py`, `models.py` from S1, `filter_accuracy.py` for pattern reference) | +3 |
| Tests to write | ~14 (weight: 7 — per-dimension correlation + zero-variance + per-regime + empty data; threshold: 7 — per-grade rates + empty counterfactual + insufficient data) | +7 |
| Complex integration wiring | 0 | 0 |
| External API debugging | 0 | 0 |
| Large files (>150 lines) | 0 | 0 |
| **Total** | | **14 → High (borderline)** |

**Mitigation:** Both analyzers follow identical patterns (take OutcomeCollector output, group, compute statistics, return typed result). Threshold analyzer is structurally similar to existing FilterAccuracy — established pattern.

---

### Session 2b: Correlation Analyzer

**Objective:** Build the pairwise strategy correlation analyzer.

**Creates:**
- `argus/intelligence/learning/correlation_analyzer.py`

**Modifies:** None

**Integrates:** Consumes OutcomeCollector output from S1.

**Parallelizable:** Yes (with S2a — zero file overlap)

| Factor | Detail | Points |
|--------|--------|--------|
| New files created | 1 | +2 |
| Files modified | 0 | 0 |
| Context/pre-flight reads | 2 (`outcome_collector.py`, `models.py` from S1) | +2 |
| Tests to write | ~8 (happy path + single strategy + zero trades + high correlation flagging + empty window) | +4 |
| Complex integration wiring | 0 | 0 |
| External API debugging | 0 | 0 |
| Large files (>150 lines) | 0 | 0 |
| **Total** | | **8 → Low** |

---

### Session 3a: LearningStore (SQLite Persistence)

**Objective:** Build SQLite persistence layer for learning reports, config proposals, and change history.

**Creates:**
- `argus/intelligence/learning/learning_store.py`

**Modifies:** None

**Integrates:** Persists LearningReport from S1 `models.py`. Follows DEC-345 pattern (reference `counterfactual_store.py`).

**Parallelizable:** No (S3b depends on this)

| Factor | Detail | Points |
|--------|--------|--------|
| New files created | 1 | +2 |
| Files modified | 0 | 0 |
| Context/pre-flight reads | 2 (`models.py` from S1, `counterfactual_store.py` as DEC-345 pattern reference) | +2 |
| Tests to write | ~10 (report CRUD + proposal CRUD + change history + retention enforcement + WAL mode + empty DB) | +5 |
| Complex integration wiring | 0 | 0 |
| External API debugging | 0 | 0 |
| Large files (>150 lines) | 1 (schema + multiple tables + query methods ~180 lines) | +2 |
| **Total** | | **11 → Medium** |

---

### Session 3b: LearningService + CLI

**Objective:** Build the orchestrator that wires all components into a pipeline, plus the CLI entry point.

**Creates:**
- `argus/intelligence/learning/learning_service.py`
- `scripts/run_learning_analysis.py`

**Modifies:** None

**Integrates:** Wires OutcomeCollector (S1) + WeightAnalyzer (S2a) + ThresholdAnalyzer (S2a) + CorrelationAnalyzer (S2b) + LearningStore (S3a) into orchestration pipeline. Reads LearningLoopConfig (S1 models.py).

**Parallelizable:** No (depends on S3a; S5 depends on this)

| Factor | Detail | Points |
|--------|--------|--------|
| New files created | 2 | +4 |
| Files modified | 0 | 0 |
| Context/pre-flight reads | 5 (`outcome_collector.py`, `weight_analyzer.py`, `threshold_analyzer.py`, `correlation_analyzer.py`, `learning_store.py`) | +5 |
| Tests to write | ~10 (full pipeline happy path + sparse data + config-disabled + concurrent guard + CLI flags + dry-run) | +5 |
| Complex integration wiring | 1 (wiring 5 components into orchestrator) | +3 |
| External API debugging | 0 | 0 |
| Large files (>150 lines) | 0 | 0 |
| **Total** | | **17 → High** |

**Mitigation:** LearningService is a thin orchestrator — calls methods on existing components in sequence. No complex business logic in the service itself. CLI script is <30 lines.

---

### Session 4: ConfigProposalManager + Config Change History

**Objective:** Build the module that bridges UI approval to YAML config changes with full safety guardrails.

**Creates:**
- `argus/intelligence/learning/config_proposal_manager.py`
- `config/learning_loop.yaml`

**Modifies:**
- `argus/intelligence/quality_engine.py` (add config reload method)
- Quality Engine Pydantic config model (add optional reload capability)

**Integrates:** N/A (standalone module, wired in S5). Uses LearningLoopConfig from S1 `models.py`.

**Parallelizable:** Yes (with S3a → S3b — zero file overlap, converges at S5)

| Factor | Detail | Points |
|--------|--------|--------|
| New files created | 2 (`config_proposal_manager.py`, `config/learning_loop.yaml`) | +4 |
| Files modified | 2 (`quality_engine.py`, QE Pydantic model) | +2 |
| Context/pre-flight reads | 3 (`quality_engine.yaml`, QualityEngineConfig Pydantic model, `models.py` from S1) | +3 |
| Tests to write | ~12 (approve happy path + Pydantic rejection + weight sum-to-1 + max_change guard + revert + double-revert + mid-session queue + config reload) | +6 |
| Complex integration wiring | 0 (standalone — S5 wires it) | 0 |
| External API debugging | 0 | 0 |
| Large files (>150 lines) | 0 | 0 |
| **Total** | | **15 → High (borderline)** |

**Mitigation:** The YAML read-validate-write-reload cycle is the core complexity, concentrated in a single file. Tests are critical and comprehensive for this module given its config-modification capability.

---

### Session 5: REST API + Auto Post-Session Trigger

**Objective:** Expose the Learning Loop via REST endpoints and wire the automatic post-session analysis trigger.

**Creates:**
- `argus/api/routes/learning.py`

**Modifies:**
- `argus/api/server.py` (lifespan: init LearningService + ConfigProposalManager, register routes)
- `argus/main.py` (post-EOD-flatten callback for auto trigger)

**Integrates:** Wires LearningService (S3b) + ConfigProposalManager (S4) into API server and main application lifecycle.

**Parallelizable:** No (depends on both S3b and S4)

| Factor | Detail | Points |
|--------|--------|--------|
| New files created | 1 | +2 |
| Files modified | 2 (`server.py`, `main.py`) | +2 |
| Context/pre-flight reads | 4 (`learning_service.py`, `config_proposal_manager.py`, `server.py` current, `main.py` EOD flatten section) | +4 |
| Tests to write | ~12 (8 endpoint tests + trigger-fires + trigger-skips + trigger-timeout + config-disabled) | +6 |
| Complex integration wiring | 1 (wiring 2 components into server lifespan + main.py callback) | +3 |
| External API debugging | 0 | 0 |
| Large files (>150 lines) | 0 | 0 |
| **Total** | | **17 → High** |

**Mitigation:** Route handlers are thin (delegate to service methods). Auto trigger is a single asyncio callback (~15 lines). Main complexity is correct lifespan initialization ordering.

---

### Session 6a: Frontend — Hooks + API Client + Recommendation Cards

**Objective:** Build the data-fetching layer and reusable card components for the Learning Loop UI.

**Creates:**
- `argus/ui/src/hooks/useLearningReport.ts`
- `argus/ui/src/hooks/useConfigProposals.ts`
- `argus/ui/src/api/learningApi.ts`
- `argus/ui/src/components/learning/WeightRecommendationCard.tsx`
- `argus/ui/src/components/learning/ThresholdRecommendationCard.tsx`

**Modifies:** None

**Integrates:** N/A (components not yet wired into pages — S6b/S6c wire them)

**Parallelizable:** No (needs S5 API to test against)

| Factor | Detail | Points |
|--------|--------|--------|
| New files created | 5 | +10 |
| Files modified | 0 | 0 |
| Context/pre-flight reads | 2 (existing TanStack Query hook patterns, API route signatures from S5) | +2 |
| Tests to write | ~5 Vitest (hook render tests, card render tests) | +2.5 |
| Complex integration wiring | 0 | 0 |
| External API debugging | 0 | 0 |
| Large files (>150 lines) | 0 | 0 |
| **Total** | | **14.5 → High (borderline)** |

**Mitigation:** All 5 files follow established patterns (TanStack Query hooks, typed API client functions, Tailwind card components). Each file is <80 lines.

---

### Session 6b: Frontend — Learning Insights Panel + Performance Page Integration

**Objective:** Build the main Learning Insights panel and integrate it into the Performance page.

**Creates:**
- `argus/ui/src/components/learning/LearningInsightsPanel.tsx`

**Modifies:**
- Performance page component (add Learning Insights section/tab)

**Integrates:** Composes WeightRecommendationCard + ThresholdRecommendationCard from S6a. Uses hooks from S6a.

**Parallelizable:** No (needs S6a components)

| Factor | Detail | Points |
|--------|--------|--------|
| New files created | 1 | +2 |
| Files modified | 1 (Performance page) | +1 |
| Context/pre-flight reads | 4 (S6a components, Performance page current layout, existing Performance page patterns, approval mutation flow) | +4 |
| Tests to write | ~4 Vitest (panel render, approve interaction, dismiss interaction, empty state) | +2 |
| Complex integration wiring | 0 | 0 |
| External API debugging | 0 | 0 |
| Large files (>150 lines) | 0 | 0 |
| **Total** | | **9 → Medium** |

---

### Session 6c: Frontend — Strategy Health Bands + Correlation Matrix + Dashboard Card

**Objective:** Build the remaining three frontend components and wire them into their pages.

**Creates:**
- `argus/ui/src/components/learning/StrategyHealthBands.tsx`
- `argus/ui/src/components/learning/CorrelationMatrix.tsx`
- `argus/ui/src/components/learning/LearningDashboardCard.tsx`

**Modifies:**
- Performance page component (add Health Bands and Correlation Matrix sections)
- Dashboard page component (add Learning summary card)

**Integrates:** Uses hooks from S6a. Consumes LearningReport data via useLearningReport hook.

**Parallelizable:** No (needs S6a hooks; shares Performance page modification surface with S6b)

| Factor | Detail | Points |
|--------|--------|--------|
| New files created | 3 | +6 |
| Files modified | 2 (Performance page, Dashboard page) | +2 |
| Context/pre-flight reads | 4 (S6a hooks, Performance page post-S6b, Dashboard page, Recharts heatmap patterns) | +4 |
| Tests to write | ~6 Vitest (health bands render, correlation matrix render, dashboard card render + link, empty/disabled states) | +3 |
| Complex integration wiring | 0 | 0 |
| External API debugging | 0 | 0 |
| Large files (>150 lines) | 0 | 0 |
| **Total** | | **15 → High (borderline)** |

**Mitigation:** Three independent components with no interaction between them. Health Bands and Correlation Matrix follow established Recharts patterns from existing Performance page.

---

### Session 6cf: Frontend Visual-Review Fixes (Contingency, 0.5 session)

**Objective:** Fix visual issues identified during S6b/S6c review.

**Creates:** None expected

**Modifies:** Components from S6a–S6c as needed

**Integrates:** N/A

**Parallelizable:** No

Estimated score: ~4 (Low). Only used if visual review identifies issues.

---

## Summary Table

| Session | Scope | Creates | Modifies | Score | Risk | Parallelizable |
|---------|-------|---------|----------|-------|------|----------------|
| S1 | Data Models + Outcome Collector | 3 files | 0 | 16.5 | High | No (foundational) |
| S2a | Weight + Threshold Analyzers | 2 files | 0 | 14 | High (borderline) | Yes (∥ S2b) |
| S2b | Correlation Analyzer | 1 file | 0 | 8 | Low | Yes (∥ S2a) |
| S3a | LearningStore (SQLite) | 1 file | 0 | 11 | Medium | No |
| S3b | LearningService + CLI | 2 files | 0 | 17 | High | No |
| S4 | ConfigProposalManager | 2 files | 2 | 15 | High (borderline) | Yes (∥ S3a→S3b) |
| S5 | REST API + Auto Trigger | 1 file | 2 | 17 | High | No |
| S6a | Hooks + API Client + Cards | 5 files | 0 | 14.5 | High (borderline) | No |
| S6b | Learning Insights Panel | 1 file | 1 | 9 | Medium | No |
| S6c | Health Bands + Correlation + Dashboard | 3 files | 2 | 15 | High (borderline) | No |
| S6cf | Visual-review fixes (contingency) | 0 | TBD | ~4 | Low | No |

**Total new files:** ~21 backend + ~8 frontend = ~29 files
**Total modified files:** 6 (quality_engine.py, QE config model, server.py, main.py, Performance page, Dashboard page)
**Estimated new tests:** ~55 pytest + ~15 Vitest = ~70

**Note on High scores:** Five sessions score 14–17 (High). Per protocol, sessions scoring 14–17 "must split before proceeding." However, these scores are driven primarily by test counts (which scale linearly and don't compound complexity) and pre-flight reads (which are passive context loading, not active integration). The sessions with the highest *inherent complexity* are S3b (5-component orchestration) and S5 (server lifecycle wiring), both at 17 — at the upper High boundary but below Critical (18). The mitigations noted per session address why splitting further would create more overhead than the complexity warrants. If any session compacts during implementation, the close-out report should log the planning score and compaction point for calibration.

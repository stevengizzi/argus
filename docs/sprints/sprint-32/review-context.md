# Sprint 32: Review Context File

> This file is referenced by all 8 session review prompts. It contains the full
> Sprint Spec, Specification by Contradiction, Regression Checklist, and Escalation
> Criteria. Do not duplicate this content in individual review prompts.

---

## Sprint Spec

### Goal
Build the complete parameter externalization and experiment pipeline for PatternModule strategies. When complete, ARGUS can instantiate multiple parameterized variants of each pattern template, run them simultaneously (live and shadow), and autonomously promote or demote variants based on accumulated live shadow performance — without human intervention. This sprint combines the original Sprint 32 (Parameterized Templates) and Sprint 32.5 (Experiment Registry + Promotion Pipeline) into a single delivery.

### Deliverables
1. Pydantic config alignment — 28 missing detection param fields added across 6 pattern configs
2. Generic pattern factory — `build_pattern_from_config()` using PatternParam introspection
3. Parameter fingerprint — deterministic hash of detection params, ≤16 hex chars
4. Runtime wiring — main.py + PatternBacktester use factory, trades carry fingerprint
5. Experiment registry — SQLite-backed ExperimentStore (DEC-345 pattern)
6. Variant spawner — reads config, instantiates variants, registers with Orchestrator
7. Experiment runner — grid generation + BacktestEngine pre-filter
8. Promotion evaluator — autonomous shadow→live / live→shadow based on Pareto comparison
9. CLI + REST API — `run_experiment.py` + 4 endpoints + ExperimentConfig

### Key Constraints
- Config-gated: `experiments.enabled: false` by default
- Startup-only parameter loading; intraday mode changes (live↔shadow) for variants
- Non-zero-sum deployment: any number of variants can be live simultaneously
- BacktestEngine pre-filter before shadow spawning
- Shadow performance is the promotion gate, not backtests alone

---

## Specification by Contradiction

### Out of Scope
- Non-PatternModule strategy variants (ORB, VWAP, AfMo, R2G) — DEF-129
- Hot-reload of parameters — startup-only
- Anti-fragility / degradation detection / rollback — Sprint 33.5
- Actual parameter tuning — infrastructure only
- Novel strategy discovery — Sprint 36+
- UI changes — REST API only
- ABCD O(n³) optimization — DEF-122
- Learning Loop V2 auto-approval — Sprint 40
- Cross-strategy ensemble optimization — Sprint 34–35
- Variant-specific exit management — DEF-132

### Do NOT Modify
- Non-PatternModule strategy files (`orb_breakout.py`, `orb_scalp.py`, `vwap_reclaim.py`, `afternoon_momentum.py`, `red_to_green.py`)
- `argus/core/orchestrator.py`
- `argus/intelligence/learning/` package
- `argus/intelligence/counterfactual.py`
- Any frontend file in `argus/ui/`

### Interaction Boundaries
- This sprint does NOT change: Orchestrator registration API, Risk Manager gating, Order Manager signal processing, CounterfactualTracker signal handling, Event Bus pub/sub
- This sprint does NOT affect: Live trading execution path (config-gated), Learning Loop V1 proposals, Quality Engine scoring

---

## Regression Checklist

| # | Check | How to Verify |
|---|-------|---------------|
| R1 | All 12 existing strategies instantiate at startup | Startup log shows all 12 strategy IDs |
| R2 | Existing YAML configs still load with no changes | Load each pattern config through Pydantic — no errors |
| R3 | Pattern constructor defaults unchanged | `SomePattern()` with no args → same behavior |
| R4 | PatternBacktester supports pre-existing patterns | Factory for bull_flag, flat_top, abcd succeeds |
| R5 | PatternBacktester supports Sprint 29 patterns (DEF-121) | Factory for dip_and_rip, hod_break, gap_and_go, premarket_high_break succeeds |
| R6 | Shadow mode routing works | `mode: "shadow"` → signals route to CounterfactualTracker |
| R7 | CounterfactualTracker handles variant shadow signals | Shadow variant signal → SignalRejectedEvent received |
| R8 | Non-PatternModule strategies untouched | `git diff` shows zero changes to protected files |
| R9 | Test suite passes | pytest 4,200+ pass, Vitest 700+ pass |
| R10 | Config validation rejects invalid values | Invalid YAML → Pydantic error at startup |
| R11 | `experiments.enabled: false` → system unchanged | No extra strategies, no DB, no API |
| R12 | Paper trading overrides unaffected | Sprint 29.5 config values unchanged |
| R13 | No silently ignored config keys | Programmatic cross-validation test passes |
| R14 | Fingerprint is deterministic | Same config → same hash across restarts |
| R15 | trades table migration backward compatible | Historical trades still queryable |
| R16 | Orchestrator registration unchanged | No changes to orchestrator.py |

---

## Escalation Criteria

### Tier 3 Escalation
1. Shadow variants cause >10% throughput degradation to live strategies
2. Variant spawning causes >2× memory increase at startup
3. Event Bus contention from 35+ subscribers delays live signal processing
4. Parameter fingerprint hash collision between different configs
5. CounterfactualTracker can't handle shadow variant volume

### HALT Triggers
1. Factory fails to construct any existing pattern with current defaults
2. ARGUS fails to start with `experiments.enabled: false`
3. Any pre-existing test failure introduced by sprint changes
4. Detection parameter in YAML silently ignored (uses different value than config)

### WARNING Conditions
1. Experiment sweep >60 min for 50-point grid
2. Variant spawner startup >10 seconds
3. Promotion evaluator consistently finds insufficient data

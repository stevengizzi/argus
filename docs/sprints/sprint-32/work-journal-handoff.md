# Sprint 32 Work Journal — Handoff Prompt

> Paste this entire document into a fresh Claude.ai conversation to create
> the Sprint 32 Work Journal. Open this conversation before starting Session 1
> and bring issues to it throughout the sprint.

---

## Sprint Context

**Sprint 32: Parameterized Strategy Templates + Experiment Pipeline**

**Goal:** Build the complete parameter externalization and experiment pipeline for PatternModule strategies. When complete, ARGUS can instantiate multiple parameterized variants of each pattern template, run them simultaneously (live and shadow), and autonomously promote or demote variants based on accumulated live shadow performance.

**Execution mode:** Human-in-the-loop

**Test baseline:** ~4,212 pytest + 700 Vitest (0 pre-existing pytest failures, 1 pre-existing Vitest failure in GoalTracker.test.tsx)

**Branch:** `main`

## Session Breakdown

| Session | Scope | Creates | Modifies | Score |
|---------|-------|---------|----------|-------|
| S1 | Pydantic Config Alignment (28 missing fields) | — | `core/config.py` | 13 |
| S2 | Pattern Factory + Parameter Fingerprint | `patterns/factory.py` | — | 11 |
| S3 | Runtime Wiring (main.py + backtester + trade fingerprint) | — | `main.py`, `vectorbt_pattern.py`, `trade_logger.py`, `pattern_strategy.py` | 14 |
| S4 | Experiment Data Model + Registry Store | `experiments/__init__.py`, `models.py`, `store.py` | — | 14 |
| S5 | Variant Spawner + Startup Integration | `spawner.py`, `experiments.yaml` | `main.py` | 13 |
| S6 | Experiment Runner (Backtest Pre-Filter) | `runner.py` | — | 12 |
| S7 | Promotion Evaluator + Autonomous Loop | `promotion.py` | `main.py` | 11 |
| S8 | CLI + REST API + Server + Config | `run_experiment.py`, `routes/experiments.py`, `experiments/config.py` | `config.py`, `server.py` | 16 |

## Session Dependency Chain

```
S1 ──┐
     ├──→ S3 ──┐
S2 ──┤         │
     ├──→ S5 ──┤
     │         ├──→ S8
S4 ──┼──→ S6 ──┤
     │         │
     └──→ S7 ──┘
```

S1 and S2 can run in parallel (zero file overlap).

## Do Not Modify

- Non-PatternModule strategy files: `orb_breakout.py`, `orb_scalp.py`, `vwap_reclaim.py`, `afternoon_momentum.py`, `red_to_green.py`
- `argus/core/orchestrator.py`
- `argus/intelligence/learning/` package
- `argus/intelligence/counterfactual.py`
- Any frontend file in `argus/ui/`

## Issue Category Definitions

When bringing issues to this journal, classify them as:

- **BUG**: Defect in existing or newly written code
- **SCOPE_GAP**: Something the spec missed that must be addressed
- **SCOPE_CREEP**: Tempting but not in spec — defer unless blocking
- **REGRESSION**: Existing functionality broken by sprint changes
- **COMPACTION**: Session running out of context before completing
- **DEPENDENCY**: External blocker (API, library, infrastructure)
- **DESIGN_QUESTION**: Ambiguity that needs clarification before proceeding

## Escalation Triggers

Escalate to Tier 3 (stop implementation, discuss in Claude.ai) if:

1. Shadow variants cause >10% throughput degradation to live strategies
2. Variant spawning causes >2× memory increase at startup
3. Event Bus contention from shadow variants delays live signal processing
4. Parameter fingerprint hash collision between different configs
5. CounterfactualTracker can't handle shadow variant volume

HALT immediately if:

1. Factory fails to construct any existing pattern with defaults
2. ARGUS fails to start with `experiments.enabled: false`
3. Any pre-existing test failure from sprint changes
4. Detection parameter in YAML silently ignored

## Reserved DEC/RSK/DEF Numbers

- **DEC:** 382–395
- **DEF:** 129–133 (already allocated in spec-by-contradiction)
- **RSK:** 032–033 (already allocated in sprint spec)

## Carry-Forward Tracking

Track across sessions:
- Test count delta per session
- Any DEF/DEC items created during implementation
- Any spec deviations or amendments
- Session compaction risk score accuracy (predicted vs actual)

## Session Verdict Log

Update this table after each session close-out and review:

| Session | Verdict | Tests Added | Notes |
|---------|---------|-------------|-------|
| S1 | | | |
| S2 | | | |
| S3 | | | |
| S4 | | | |
| S5 | | | |
| S6 | | | |
| S7 | | | |
| S8 | | | |

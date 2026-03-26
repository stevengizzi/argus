# Sprint 27.95 — Review Context

> This file contains the shared review context for all Session reviews in Sprint 27.95.
> Individual review prompts reference this file by path. Do not duplicate this content
> in session review prompts.

---

## Review Instructions

You are conducting a Tier 2 code review. This is a READ-ONLY session.
Do NOT modify any source code files except the review report file.

Follow the review skill in `.claude/skills/review.md`.

Your review report MUST include a structured JSON verdict at the end,
fenced with ```json:structured-verdict. See the review skill for the
full schema and requirements.

---

## Sprint Spec

### Sprint 27.95: Broker Safety + Overflow Routing

**Goal:** Fix the reconciliation auto-cleanup bug that destroyed 336 of 371 positions during the March 26 market session, add dynamic overflow routing to CounterfactualTracker for maximum signal data capture without broker overload, and harden five related order management failure modes discovered during the same session diagnostic.

**Deliverables:**
1. Reconciliation redesign — broker-confirmed tracking, consecutive miss counter, never auto-close confirmed positions
2. Trade logger reconciliation close fix — synthetic closes no longer produce ERRORs
3. Stop resubmission cap — max 3 retries with backoff, then emergency flatten
4. Bracket amendment revision-rejected handling — detect and resubmit fresh order
5. Duplicate fill deduplication — guard by (order_id, cumulative_filled_qty)
6. Dynamic overflow routing — route overflow signals to CounterfactualTracker at broker_capacity threshold
7. Startup zombie cleanup — flatten unknown IBKR positions at boot (config-gated, default true)

**Config Changes:**

| YAML Path | Pydantic Model | Field Name | Default |
|-----------|---------------|------------|---------|
| `reconciliation.auto_cleanup_unconfirmed` | ReconciliationConfig | `auto_cleanup_unconfirmed` | `false` |
| `reconciliation.consecutive_miss_threshold` | ReconciliationConfig | `consecutive_miss_threshold` | `3` |
| `overflow.enabled` | OverflowConfig | `enabled` | `true` |
| `overflow.broker_capacity` | OverflowConfig | `broker_capacity` | `30` |
| `startup.flatten_unknown_positions` | StartupConfig | `flatten_unknown_positions` | `true` |

**Session Order:** 1a → 1b → 2 → 4 → 3a → 3b → 3c

---

## Specification by Contradiction

**Out of Scope:**
- Frontend UI changes for overflow signals
- Overflow routing dashboard/metrics API
- Dynamic broker_capacity adjustment based on margin
- Reconciliation position recovery (re-query missing positions)
- IBKR API rate limiting / request queuing
- Historical data cleanup (March 26 contaminated records)

**Do NOT modify:** `argus/strategies/`, `argus/backtest/`, `argus/intelligence/counterfactual.py` (core logic), `argus/analytics/evaluation.py`, `argus/ui/`, `argus/ai/`, `argus/data/`

**Do NOT change behavior of:** Signal generation, strategy evaluation, Quality Engine scoring, Risk Manager gating logic, Capital Allocation, EOD flatten scheduling, CounterfactualTracker shadow mode routing, BacktestEngine execution

**Edge Cases to Reject:** Overflow with partial fills in flight (point-in-time check), IBKR negative position sizes (log and skip), reconciliation during startup (handle gracefully, don't fix sequencing), concurrent modification of _broker_confirmed (single-threaded asyncio), overflow threshold of 0 (valid pure-observation mode)

---

## Sprint-Level Regression Checklist

- [ ] Normal position lifecycle unchanged: entry → fill → bracket placement → bracket amendment on slippage → stop/target fill → position close → trade logged
- [ ] Risk Manager gating logic unchanged: all 3 levels produce identical results for identical inputs
- [ ] Quality Engine pipeline unchanged: pattern_strength → quality score → grade → position sizing → signal enrichment
- [ ] EOD flatten still works for all real positions
- [ ] CounterfactualTracker shadow mode (StrategyMode.SHADOW) still works independently of overflow routing
- [ ] CounterfactualTracker rejected signal tracking (quality filter, position sizer, risk manager stages) still works
- [ ] BacktestEngine unaffected — BrokerSource.SIMULATED bypass confirmed for overflow check
- [ ] Reconciliation warn-only mode still works when `auto_cleanup_unconfirmed=false`
- [ ] `_flatten_pending` guard (DEC-363) still prevents duplicate flatten orders
- [ ] Bracket amendment on fill slippage (DEC-366) still operates correctly
- [ ] Position reconciliation periodic task (60s) still runs during market hours
- [ ] Real-time P&L publishing on ticks for open positions still works
- [ ] Signal generation rate unchanged — no strategies modified, no filter logic changed
- [ ] Execution record logging (Sprint 21.6) still fires on entry fills
- [ ] IntradayCandleStore (DEC-368) not affected
- [ ] New config fields verified against Pydantic model (no silently ignored keys)
- [ ] Default values produce correct behavior
- [ ] Full test suite passes (baseline: ~3,610 pytest + 645 Vitest)
- [ ] No test hangs introduced
- [ ] `--ignore=tests/test_main.py` still required for xdist (DEF-048)

---

## Sprint-Level Escalation Criteria

1. **Reconciliation change breaks position lifecycle tests** → halt, escalate (undocumented coupling)
2. **Overflow routing blocks signals that should reach broker** → halt, investigate (correctness-critical)
3. **_process_signal() flow change breaks quality pipeline or risk manager** → halt, escalate (overflow check must be purely additive)
4. **Stop resubmission cap causes unprotected positions** → halt, design fallback
5. **Startup flatten closes positions that should be kept** → halt, fix matching logic
6. **Pre-flight test failures not present at sprint entry** → investigate before proceeding
7. **Test hang (>10 minutes)** → halt, likely asyncio issue
8. **Signal count divergence after _process_signal() modification** → halt, flow integrity compromised

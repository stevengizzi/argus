# Sprint 28.5: Review Context

> This file is shared by all Tier 2 review prompts. Read it once at the start of review.

---

## Review Instructions

You are conducting a Tier 2 code review. Follow the review skill in `.claude/skills/review.md`. This is a READ-ONLY session — do NOT modify source code files. The sole permitted write is the review report file.

---

## Sprint Spec

[Embedded from sprint-spec.md — post-adversarial-review revision]

### Goal

Deliver configurable, per-strategy exit management to the Order Manager, BacktestEngine, and CounterfactualTracker — trailing stops (ATR/percent/fixed), partial profit-taking with trail on T1 remainder, and time-based exit escalation (progressive stop tightening).

### Key Deliverables

1. `argus/core/exit_math.py` — pure functions for trail stop, escalation stop, effective stop
2. `config/exit_management.yaml` + Pydantic models — config with field-level deep merge (AMD-1)
3. SignalEvent `atr_value` field — ATR(14) via IndicatorEngine (AMD-9)
4. Order Manager trailing stop engine — server-side trail, belt-and-suspenders, sell-first-cancel-second (AMD-2)
5. Order Manager exit escalation — progressive stop tightening, exempt from DEC-372 retry cap (AMD-6)
6. BacktestEngine alignment — prior-state-first bar processing (AMD-7)
7. CounterfactualTracker alignment — same AMD-7 bar processing

### Critical Safety Requirements (from Adversarial Review)

- **AMD-2:** Trail flatten order: (1) check _flatten_pending, (2) add to _flatten_pending, (3) submit market sell, (4) cancel broker safety stop
- **AMD-3:** Escalation stop resubmission failure → immediate flatten attempt
- **AMD-4:** shares_remaining > 0 guard on all trail/escalation flatten paths
- **AMD-5:** stop_to formulas use high_watermark (dynamic), not T1/T2 (static)
- **AMD-6:** Escalation stop updates exempt from DEC-372 retry cap
- **AMD-7:** Per bar: prior state → evaluate exit → THEN update high watermark
- **AMD-8:** _flatten_pending check FIRST before any broker interaction
- **AMD-12:** Negative/zero ATR → compute_trailing_stop returns None

### Config Changes

New file `config/exit_management.yaml` with TrailingStopConfig and ExitEscalationConfig Pydantic models. Per-strategy override via field-level deep merge. `stop_to` enum: breakeven, quarter_profit, half_profit, three_quarter_profit.

### Files Created

- `argus/core/exit_math.py`
- `config/exit_management.yaml`

### Files Modified

- `argus/core/events.py` (atr_value field)
- `argus/core/config.py` (Pydantic models)
- `argus/execution/order_manager.py` (trailing stop + escalation)
- `argus/backtest/engine.py` (trail/escalation state)
- `argus/intelligence/counterfactual.py` (trail/escalation state)
- `argus/main.py` (config loading)
- 7 strategy files (ATR emission)

### Do NOT Modify

- `argus/core/fill_model.py`
- `argus/core/risk_manager.py`
- `argus/intelligence/learning/`
- `argus/ui/`
- `argus/api/routes/`
- `argus/ai/`
- `config/risk_limits.yaml`
- `config/order_manager.yaml`

---

## Specification by Contradiction (Summary)

- No regime-adaptive exit parameters (Sprint 32+)
- No new ExitReason enum values (TRAILING_STOP already exists)
- No short selling exit logic (Sprint 30)
- No frontend changes
- No new API endpoints
- No broker-side trailing stop orders
- No multi-leg partial exits (T1/T2/T3)
- Non-opt-in strategies must have zero behavioral change

---

## Sprint-Level Regression Checklist

- [ ] Non-opt-in strategy behavior unchanged (OM, BacktestEngine, CounterfactualTracker)
- [ ] BacktestEngine non-trail regression (bit-identical results for existing configs)
- [ ] CounterfactualTracker non-trail regression
- [ ] SignalEvent/SignalRejectedEvent backward compatibility (atr_value=None default)
- [ ] T1/T2 bracket order flow preserved
- [ ] Stop-to-breakeven still works after T1
- [ ] Broker safety stop not cancelled prematurely (belt-and-suspenders)
- [ ] AMD-2: Flatten order is sell-first, cancel-second
- [ ] AMD-3: Escalation failure → flatten recovery
- [ ] AMD-4: shares_remaining > 0 guard
- [ ] AMD-6: Escalation exempt from retry cap
- [ ] AMD-7: Prior-state-first bar processing order
- [ ] AMD-8: _flatten_pending check FIRST
- [ ] AMD-12: Negative/zero ATR guard
- [ ] Risk Manager not touched (DEC-027)
- [ ] EOD flatten unconditional at 15:50 ET
- [ ] Flatten-pending guard (DEC-363) covers trail flattens
- [ ] Duplicate fill dedup (DEC-374) covers trail scenarios
- [ ] Overflow routing (DEC-375) unaffected
- [ ] AMD-1: Field-level deep merge for per-strategy config
- [ ] AMD-5: stop_to enum values correct (breakeven, quarter/half/three_quarter_profit)
- [ ] AMD-9: ATR(14) standardization + code comments
- [ ] AMD-10: Deprecated config warning at startup
- [ ] Config keys match Pydantic model (no silently ignored keys)
- [ ] ExitReason values logged correctly
- [ ] Full pytest suite passes (0 failures)
- [ ] Full Vitest suite passes (0 failures)

---

## Sprint-Level Escalation Criteria

### Critical (HALT)
1. Position leak in Order Manager (shares_remaining incorrect)
2. Silent behavioral change for non-opt-in strategies
3. Trail + broker safety stop deadlock (AMD-2 order-of-operations failure)
4. BacktestEngine regression for existing configs
5. Naked position from escalation failure (AMD-3 recovery also fails)

### Significant (complete session, then escalate)
6. compute_effective_stop priority confusion
7. IBKR bracket interaction issues during trail activation
8. Config merge complexity beyond simple recursive dict merge (AMD-1)
9. TheoreticalFillModel pressure (fill_model.py needs changes)
10. AMD-7 bar-processing order requires BacktestEngine loop restructure

### Informational (log in Work Journal)
11. ATR computation variance across strategies (AMD-9)
12. Test count exceeding estimate by >50%

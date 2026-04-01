# Sprint 32.75 Review Context

> This file is the shared reference for all Tier 2 review sessions.
> Each session review prompt references this file by path.

---

## Sprint Spec Summary

**Goal:** Deliver The Arena (real-time multi-chart position visualization page), fix 13 UI bugs/polish items, and resolve 5 operational issues from the April 1 market session debrief.

**Key deliverables:** Strategy identity completion (12 strategies), Arena page (9th page), Dashboard layout overhaul, Orchestrator P&L fix, TradeChart duplicate price lines fix, AI Insight context enhancement, operational fixes (overflow capacity, reconnect delay, EOD logging, IBC guide).

**Session order:** S1 (identity) → S2 (dashboard) → S3 (orchestrator) → S4 (bugs) → S5 (ops) → S6 (arena REST) → S7 (arena WS) → S8 (arena shell) → S9 (mini-chart) → S10 (integration) → S11 (live data) → S12 (animations) → S12f (visual fixes)

**Performance targets:** Arena 30 charts < 100ms/frame, 60 charts < 200ms/frame, WS 60 msg/sec, initial load < 2s.

---

## Specification by Contradiction (Key Points)

- Do NOT modify strategy detection logic, Risk Manager, Trade Logger, BacktestEngine, Experiment Pipeline, Learning Loop core, Event Bus
- Do NOT add per-strategy max_concurrent_positions enforcement
- Do NOT refactor strategy identity into single source of truth (add entries only)
- Do NOT implement Arena click-to-trade, historical replay, or L2/L3 visualization
- Do NOT optimize Arena for >60 simultaneous positions
- The Arena is monitoring-only — no order entry capabilities
- Post-reconnect delay must not block order operations or EOD flatten
- New `/ws/v1/arena` must not interfere with existing WS channels

---

## Sprint-Level Regression Checklist

### Test Suite Gates
- [ ] All pre-existing pytest tests pass (baseline: ~4,405 + Sprint 32.5 additions)
- [ ] All pre-existing Vitest tests pass (baseline: 700, 1 known failure in GoalTracker.test.tsx)
- [ ] No new test failures introduced

### Strategy Pipeline Invariants
- [ ] All 12 strategies generate signals during operating windows
- [ ] Signal → Quality → Risk Manager → Order Manager pipeline unchanged
- [ ] ORB mutual exclusion behavior unchanged
- [ ] Shadow mode routing unchanged
- [ ] Overflow routing unchanged (new threshold: 60)

### Event Bus & WebSocket Invariants
- [ ] `/ws/v1/live` position updates unchanged
- [ ] `/ws/v1/observatory` unchanged
- [ ] `/ws/v1/ai/chat` unchanged
- [ ] New `/ws/v1/arena` does not interfere with existing channels
- [ ] Event Bus FIFO delivery preserved

### Order Management Invariants
- [ ] Bracket order lifecycle unchanged
- [ ] EOD flatten at 3:50 PM ET unchanged
- [ ] Startup zombie cleanup unchanged
- [ ] Flatten-pending guard (DEC-363) unchanged
- [ ] Broker-confirmed positions never auto-closed (DEC-369)
- [ ] Stop resubmission cap unchanged (DEC-372)
- [ ] Post-reconnect delay does not block orders or EOD flatten

### Frontend Invariants
- [ ] Dashboard renders correctly in all 3 layouts (minus removed cards)
- [ ] Orchestrator, Performance, Trades, Pattern Library, Debrief, System, Observatory functional
- [ ] All existing pages show correct strategy colors and names

### Config & Data
- [ ] `overflow.broker_capacity: 60` read correctly
- [ ] Trade records retain strategy_id, quality_grade, config_fingerprint
- [ ] MFE/MAE, counterfactual, Learning Loop unchanged

---

## Sprint-Level Escalation Criteria

1. Arena 30-chart performance >200ms/frame → Tier 3 review
2. TradingView LC `update()` API inadequate for live candle formation → evaluate alternatives
3. Arena WS degrades main trading pipeline event delivery → immediate halt
4. Post-reconnect delay causes position state corruption → revert + escalate
5. Orchestrator P&L fix reveals systemic trade-to-strategy attribution gap → escalate

### Session-Level Halt Conditions
- >5 pre-existing test failures → halt
- Compaction imminent → close out partial work
- S11 compaction fallback: defer rAF batching + stats bar to S12

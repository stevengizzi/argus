# Sprint 29.5 Design Summary

**Sprint Goal:** Fix all operational, safety, UI, and data-capture issues from the March 31 session — critical flatten bugs, paper-trading data blockers, win rate display bug, position update speed, log noise, MFE/MAE tracking, and ORB Scalp structural shadow.

**Session Breakdown:**

- **Session 1: Flatten/Zombie Safety Overhaul** (Compaction: 14, HIGH — consider splitting S1a/S1b if needed)
  - Creates: None (all modifications to existing files)
  - Modifies: `argus/execution/order_manager.py`, `argus/execution/ibkr_broker.py`, `argus/core/config.py`, `config/order_manager.yaml`
  - Integrates: N/A
  - Tests: `tests/execution/test_order_manager.py`, `tests/execution/test_ibkr_broker.py`

- **Session 2: Paper Trading Data-Capture Mode** (Compaction: 6, LOW)
  - Creates: None
  - Modifies: `config/risk_limits.yaml`, `config/orchestrator.yaml`, `argus/core/config.py`, `argus/core/orchestrator.py`, `argus/core/throttle.py`
  - Integrates: N/A
  - Tests: `tests/core/test_orchestrator.py`, `tests/core/test_throttle.py`

- **Session 3: Win Rate Bug + UI Fixes** (Compaction: 10, MEDIUM)
  - Creates: None
  - Modifies: `argus/ui/src/features/trades/TradeStatsBar.tsx`, `argus/ui/src/pages/TradesPage.tsx`, `argus/ui/src/features/dashboard/OpenPositions.tsx`, `argus/ui/src/hooks/useTradeStats.ts`, `argus/api/routes/trades.py`, `argus/ui/src/features/dashboard/TodayStatsCard.tsx` (or equivalent)
  - Integrates: N/A
  - Tests: Vitest tests in `argus/ui/src/features/trades/`, `argus/ui/src/features/dashboard/`

- **Session 4: Real-Time Position Updates via WebSocket** (Compaction: 13, MEDIUM-HIGH)
  - Creates: `argus/ui/src/hooks/usePositionUpdates.ts`
  - Modifies: `argus/ui/src/features/dashboard/OpenPositions.tsx`, `argus/ui/src/hooks/usePositions.ts`
  - Integrates: Existing WS bridge `position.updated` events
  - Tests: Vitest tests for new hook

- **Session 5: Log Noise Reduction** (Compaction: 8, LOW-MEDIUM)
  - Creates: None
  - Modifies: `argus/execution/ibkr_broker.py`, `argus/core/risk_manager.py`, `argus/main.py`
  - Integrates: N/A
  - Tests: `tests/execution/test_ibkr_broker.py`, `tests/core/test_risk_manager.py`

- **Session 6: MFE/MAE Trade Lifecycle Tracking** (Compaction: 11, MEDIUM)
  - Creates: DB migration (if not using auto-create pattern)
  - Modifies: `argus/execution/order_manager.py`, `argus/analytics/trade_logger.py`, `argus/analytics/debrief_export.py`, `argus/db/manager.py` (or schema file)
  - Integrates: N/A
  - Tests: `tests/execution/test_order_manager.py`, `tests/analytics/test_trade_logger.py`

- **Session 7: ORB Scalp Exclusion Fix** (Compaction: 9, MEDIUM)
  - Creates: None
  - Modifies: `argus/strategies/orb_base.py`, `argus/core/config.py`, `config/orchestrator.yaml`, `argus/main.py` (pass config to strategy)
  - Integrates: N/A
  - Tests: `tests/strategies/test_orb_base.py`, `tests/strategies/test_orb_scalp.py`

**Key Decisions:**
- Error 404 root-cause fix: re-query IBKR position qty before resubmit (not just retry with same qty)
- Circuit breaker is safety net, not primary fix
- Paper risk limits set to effectively unlimited (1.0 = 100%) rather than feature-flag disabled — simpler, reversible
- ORB exclusion made configurable rather than removed — preserves DEC-261 for live trading
- MFE/MAE tracked at tick level on ManagedPosition, persisted on trade close — no separate DB table

**Scope Boundaries:**
- IN: Flatten safety, paper risk limits, win rate bug, UI polish, WS positions, log noise, MFE/MAE, ORB Scalp
- OUT: Time-of-day conditioning, regime-strategy profiles, Learning Loop changes, backtest re-validation, virtual scrolling

**Regression Invariants:**
1. All existing 4,178 pytest tests pass
2. All existing 689 Vitest tests pass (1 pre-existing GoalTracker failure)
3. Trailing stop behavior unchanged (57/57 winners pattern from March 31 must be reproducible)
4. Broker-confirmed positions NEVER auto-closed by reconciliation (DEC-369)
5. Config-gating pattern preserved — all new features have config on/off
6. EOD flatten still triggers auto-shutdown sequence
7. Quality Engine scoring unmodified
8. Catalyst pipeline unmodified
9. CounterfactualTracker shadow logic unmodified

**File Scope:**
- Modify: `order_manager.py`, `ibkr_broker.py`, `risk_manager.py`, `orchestrator.py`, `throttle.py`, `config.py`, `main.py`, `trade_logger.py`, `debrief_export.py`, `orb_base.py`, 6+ frontend files, 4+ config YAML files
- Do not modify: `argus/intelligence/learning/`, `argus/backtest/`, `argus/analytics/evaluation.py`, `argus/intelligence/counterfactual.py`, `argus/strategies/patterns/`

**Config Changes:**
- `orchestrator.throttler_suspend_enabled` → `OrchestratorConfig.throttler_suspend_enabled` (default `true`)
- `orchestrator.orb_family_mutual_exclusion` → `OrchestratorConfig.orb_family_mutual_exclusion` (default `true`)
- `order_manager.max_flatten_cycles` → `OrderManagerConfig.max_flatten_cycles` (default `2`)
- `risk_limits.account.weekly_loss_limit_pct` → value change to `1.0` (existing field)
- `risk_limits.account.daily_loss_limit_pct` → value change to `1.0` (existing field)

**Test Strategy:**
- S1: ~12 new pytest (flatten edge cases, error 404, circuit breaker, EOD broker-only, startup queue)
- S2: ~3 new pytest (throttler bypass, config validation)
- S3: ~5 new Vitest (win rate display, shares column, badge text)
- S4: ~3 new Vitest (WS hook, cache merge)
- S5: ~4 new pytest (log level filtering, throttled warnings, shutdown cleanup)
- S6: ~8 new pytest (MFE/MAE tracking, persistence, debrief export)
- S7: ~4 new pytest (exclusion toggle, both strategies fire)
- **Total estimated: ~39 new tests (+20 pytest, +8 Vitest approx)**

**Runner Compatibility:**
- Mode: human-in-the-loop (impromptu sprint, HITL preferred)
- Parallelizable sessions: S2 + S5 (no shared files), S3 + S7 (no shared files)
- Estimated token budget: ~7 sessions × 80K avg = ~560K tokens
- Runner-specific escalation notes: S1 touches safety-critical Order Manager — any CONCERNS finding triggers manual review

**Dependencies:**
- Sprint 29 merged to `main`
- IB Gateway running for integration testing of S1

**Escalation Criteria:**
- Any change to fill callback handling in Order Manager
- Any change to position close/reconciliation logic beyond the specified scope
- Any regression in trailing stop behavior
- Any modification to files in the "do not modify" list

**Doc Updates Needed:**
- `CLAUDE.md`: Sprint 29.5 completion, DEF-125 through DEF-128, new config fields
- `docs/project-knowledge.md`: Update Active Strategies (ORB Scalp exclusion note), Risk Limits (paper overrides), Order Manager (flatten circuit breaker, MFE/MAE), Key Learnings (IBKR error 404 pattern)
- `docs/sprint-history.md`: Sprint 29.5 entry
- `docs/decision-log.md`: DEC entries if novel decisions arise
- `docs/pre-live-transition-checklist.md`: Note paper risk limit values to restore
- `docs/roadmap.md`: Update build track queue (29.5 inserted)

**Artifacts to Generate:**
1. Sprint Spec ✅
2. Specification by Contradiction ✅
3. Design Summary (this document) ✅
4. Implementation Prompts ×7
5. Review Prompts ×7
6. Review Context File
7. Regression Checklist
8. Doc Update Checklist

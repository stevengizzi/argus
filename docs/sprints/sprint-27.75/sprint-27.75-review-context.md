# Sprint 27.75 — Review Context

## Sprint Overview
**Name:** Paper Trading Operational Hardening
**Type:** Impromptu sprint (unplanned operational fixes)
**Sessions:** 2 (S1: Backend + Config, S2: Frontend)
**Urgency:** URGENT — fixes needed before next market session (March 26, 2026)

## Sprint Spec (Abbreviated)

### Problem Statement
The March 25, 2026 market session revealed several operational issues:
1. JSONL log grew to 16,878 lines with 3,583 warnings/errors, making post-session diagnostics impractical
2. Four strategies were suspended by circuit-breaker throttling, preventing data collection during paper trading
3. Capital was exhausted in 6 minutes due to live-trading-sized positions, rejecting 414+ signals
4. Strategy Operations cards didn't show suspension state (only throttle state)
5. Trades page period filter shows changing counts but static Win Rate / Net P&L

### Design Decisions
- **Log rate-limiting** is per-key with configurable interval and suppressed count tracking
- **Config changes are config-only** — no code changes to throttle logic, only threshold values
- **Position sizing reduction is 10x** — enough for 100+ concurrent positions on $950K account
- **Suspension display is additive** — new section alongside existing throttle section, not replacing it
- **Risk floor reduced to $10** — prevents concentration-floor rejections for small paper positions

### What Changed in Session 1 (for S2 reviewer)
- New `argus/utils/log_throttle.py` utility
- Modified logging in `ibkr_broker.py`, `risk_manager.py`, `order_manager.py`
- Config changes in `quality_engine.yaml` and `system_live.yaml`

## Specification by Contradiction

### Things That Must NOT Be True After This Sprint
1. Strategy evaluation logic was modified (only logging + config)
2. Risk Manager approve/reject decisions changed (only logging around them)
3. ThrottledLogger can suppress the FIRST occurrence of any warning
4. Throttle section on StrategyOperationsCard behaves differently
5. Any strategy's operating window or entry/exit logic was altered
6. Config files fail to parse/validate

## Sprint-Level Regression Checklist
| Check | How to Verify |
|-------|---------------|
| All pytest pass | `python -m pytest tests/ --ignore=tests/test_main.py -x -q -n auto` |
| All Vitest pass | `cd argus/ui && npx vitest run` |
| Config loads | `python -c "from argus.core.config import SystemConfig; SystemConfig.from_yaml('config/system_live.yaml')"` |
| No strategy changes | `git diff --stat` shows no changes in `argus/strategies/` |
| Risk tier values correct | `python -c "import yaml; d=yaml.safe_load(open('config/quality_engine.yaml')); assert d['risk_tiers']['a_plus'] == [0.002, 0.003]"` |

## Sprint-Level Escalation Criteria
- ESCALATE if any existing test fails
- ESCALATE if strategy logic was modified
- ESCALATE if Risk Manager approve/reject logic (not just logging) was changed
- ESCALATE if ThrottledLogger could suppress the first occurrence of a warning
- ESCALATE if trades date filter fix introduces performance regression

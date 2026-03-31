# Sprint 29.5 — Doc Update Checklist

## Post-Sprint Documentation Updates

After all 7 sessions are complete and reviewed, the following documents need updating.
Generate a doc-sync prompt (per `templates/doc-sync-automation-prompt.md`) for Claude Code execution.

### CLAUDE.md Updates
- [ ] Sprint 29.5 completion entry under sprint status
- [ ] Test count updated (4178 + new → ~4218 pytest, 689 + new → ~697 Vitest)
- [ ] DEF-125: Time-of-day signal conditioning (deferred to Sprint 32)
- [ ] DEF-126: Regime-strategy interaction profiles (deferred to Sprint 32.5)
- [ ] DEF-127: Virtual scrolling for trades table (unscheduled)
- [ ] DEF-128: IBKR error 404 root cause — multi-position qty divergence prevention (deferred to Sprint 30)
- [ ] Note: `max_flatten_cycles` config field in OrderManagerConfig
- [ ] Note: `throttler_suspend_enabled` config field in OrchestratorConfig
- [ ] Note: `orb_family_mutual_exclusion` config field in OrchestratorConfig
- [ ] Note: MFE/MAE fields on ManagedPosition and trades table
- [ ] Remove DEF-118 if addressed (ib_async wrapper warnings)

### docs/project-knowledge.md Updates
- [ ] **Order Manager section**: Add flatten circuit breaker (`_flatten_abandoned`, `max_flatten_cycles`), EOD broker-only flatten, startup flatten queue, IBKR error 404 re-query-qty pattern, MFE/MAE tracking on ManagedPosition
- [ ] **Risk Limits section**: Note paper-trading overrides (daily/weekly at 1.0)
- [ ] **Orchestrator section**: Add `throttler_suspend_enabled` flag, `orb_family_mutual_exclusion` flag
- [ ] **Active Strategies table**: Note ORB Scalp exclusion now configurable; note ORB Scalp fired 0 signals on March 31 due to DEC-261 structural shadow
- [ ] **Exit Management section**: Add MFE/MAE fields to trade records
- [ ] **Active Constraints section**: Add note about paper risk limit overrides
- [ ] **Key Learnings**: Add IBKR error 404 pattern (multi-position qty divergence causes locate holds on SELL orders); add ORB Scalp structural shadow lesson
- [ ] **Monthly Costs**: Unchanged
- [ ] **Tech Stack**: Unchanged

### docs/sprint-history.md
- [ ] Sprint 29.5 entry: "Post-Session Operational Sweep — flatten safety, paper data-capture, UI fixes, MFE/MAE, ORB Scalp, log noise"
- [ ] Test count: ~4218+697V (estimate, use actual from final close-out)
- [ ] Date: April 2026

### docs/decision-log.md
- [ ] Add DEC entries if any novel decisions were made during implementation (DEC-382+ reserved)
- [ ] If no new DECs, note "No new DECs in Sprint 29.5 — all changes followed established patterns"

### docs/pre-live-transition-checklist.md
- [ ] `daily_loss_limit_pct: 0.03` (restore from 1.0)
- [ ] `weekly_loss_limit_pct: 0.05` (restore from 1.0)
- [ ] `throttler_suspend_enabled: true` (restore from false)
- [ ] `orb_family_mutual_exclusion: true` (restore from false)

### docs/roadmap.md
- [ ] Insert Sprint 29.5 between 29 and 30 in build track queue (completed)

### docs/risk-register.md
- [ ] Review RSK-022 (IB Gateway resets) — startup queue partially mitigates

---

# Sprint 29.5 — Regression Checklist

## Pre-Sprint Baseline
- pytest: ~4,178 passing
- Vitest: 689 passing (1 pre-existing GoalTracker failure)
- Branch: `sprint-29.5` from `main`

## Per-Session Verification

| Session | Test Command | Expected |
|---------|-------------|----------|
| S1 | `python -m pytest tests/execution/ -x -q` | All pass + 12 new |
| S2 | `python -m pytest tests/core/test_orchestrator.py tests/core/test_throttle.py -x -q` | All pass + 3 new |
| S3 | `cd argus/ui && npx vitest run` | All pass + 5 new |
| S4 | `cd argus/ui && npx vitest run` | All pass + 3 new |
| S5 | `python -m pytest tests/execution/ tests/core/test_risk_manager.py -x -q` | All pass + 4 new |
| S6 | `python -m pytest tests/execution/test_order_manager.py tests/analytics/ -x -q` | All pass + 8 new |
| S7 | `python -m pytest --ignore=tests/test_main.py -n auto -q` (FULL) | All pass + 4 new |

## Sprint-Level Invariants

| # | Invariant | How to Verify |
|---|-----------|---------------|
| 1 | All pre-existing tests pass | Full suite at S7 close-out |
| 2 | Trailing stop exits unchanged | `exit_math.py` untouched; existing trail tests pass |
| 3 | Broker-confirmed never auto-closed | `_broker_confirmed` dict preserved in order_manager.py |
| 4 | Config-gating on all new features | Grep for new config fields, verify defaults |
| 5 | EOD flatten → auto-shutdown | `ShutdownRequestedEvent` still published |
| 6 | Quality Engine unchanged | No modifications to quality_engine.py or position_sizer.py |
| 7 | Catalyst pipeline unchanged | No modifications to intelligence/ (except debrief_export) |
| 8 | Counterfactual logic unchanged | No modifications to counterfactual.py |
| 9 | "Do not modify" files untouched | `git diff --name-only main..sprint-29.5` excludes protected paths |
| 10 | MFE/MAE is O(1) per tick | Code review — comparison only, no loops |

## Post-Sprint Smoke Test
After merge to main, on next Argus boot:
- [ ] All 12 strategies instantiate (check "N strategies created" log)
- [ ] VWAP Reclaim is NOT suspended (throttler bypass active)
- [ ] No weekly loss limit rejection in first hour of trading
- [ ] MFE/MAE columns present in trades DB (check via SQLite CLI)
- [ ] ORB Scalp generates at least 1 signal (if market conditions permit)
- [ ] Log volume dramatically reduced (target: <5000 lines for full session vs 48K)

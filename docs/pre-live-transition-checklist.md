# ARGUS — Pre-Live Transition Checklist

> **Purpose:** Config values and test assertions that were modified for paper trading
> and must be restored before transitioning to live trading.
>
> **Created:** March 26, 2026 (Sprint 27.75 doc sync)
> **Last updated:** March 30, 2026

---

## Config Files to Restore

### config/quality_engine.yaml — Risk Tiers (10x increase)
Paper trading values are 10x reduced from live defaults. Restore to:
- A+ tier: `risk_pct: 0.02–0.03` (paper: `0.002–0.003`)
- A tier: `risk_pct: 0.015` (paper: `0.0015`)
- B+ tier: `risk_pct: 0.01` (paper: `0.001`)
- B tier: `risk_pct: 0.0075` (paper: `0.00075`)
- C+ tier: `risk_pct: 0.005` (paper: `0.0005`)
- C tier: `risk_pct: 0.0025` (paper: `0.00025`)

### config/system_live.yaml — Risk Tiers
Same 10x restoration as quality_engine.yaml. Check that risk_tiers section matches live defaults.

### config/orchestrator.yaml — Performance Throttling
Restore:
- `consecutive_loss_throttle: 5` (paper: `999`)
- `suspension_sharpe_threshold: 0.0` (paper: verify current value)
- `suspension_drawdown_pct: 0.15` (paper: verify current value)

### config/risk_limits.yaml — Position Risk Floor
Restore:
- `min_position_risk_dollars: 100.0` (paper: `10.0`)

---

## Test Files to Update

### ~~tests/backtest/test_engine_sizing.py~~ — RESOLVED (Sprint 27.8)
~~Assertions reference `min_position_risk_dollars: 10` (paper value).~~
Rewritten in Sprint 27.8 to be config-value-independent — reads YAML and asserts match.
No manual update needed at live transition.

### ~~tests/core/test_config.py~~ — RESOLVED (Sprint 27.8)
~~Risk tier assertions reference paper-trading values.~~
Rewritten in Sprint 27.8 to assert ordering invariants (A+ > A > B+ > ... > C > 0).
No manual update needed at live transition.

---

## Log Level Review

### ThrottledLogger IBKR Error 202 Severity
Sprint 27.75 promotes IBKR error 202 (order cancelled) to WARNING via ThrottledLogger.
For live trading, evaluate whether 202 events are expected/benign and if WARNING
is the right level (vs DEBUG). Error 202 in live trading typically indicates real
order rejections, not thin-book simulation artifacts.

---

## Verification Steps

After restoring all values:
1. Run full test suite: `python -m pytest --ignore=tests/test_main.py -n auto -x -q`
2. Verify config loads: `python -c "from argus.config.config import SystemConfig; c = SystemConfig.from_yaml('config/system_live.yaml'); print('OK')"`
3. Review all risk tier values in the Command Center System page after boot
4. Verify throttling is active: first 5 consecutive losses on a strategy should trigger suspension

---

## Overflow Routing (Sprint 27.95)

### config/overflow.yaml — Broker Capacity
Review and tune `broker_capacity` for live account equity:
- Paper: `broker_capacity: 30` (conservative for $935K paper account)
- Live: Evaluate based on actual account equity and margin requirements

### config/system.yaml / config/system_live.yaml — Startup Zombie Flatten
Confirm desired behavior for live:
- `startup.flatten_unknown_positions: true` (default) — flattens unrecognized IBKR positions at startup
- Consider setting to `false` for live if manual position management is preferred (note: RECO positions created with `flatten_unknown_positions=false` have `stop_price=0.0` and require manual stop placement)

### config/system.yaml / config/system_live.yaml — Reconciliation Cleanup
Decide if unconfirmed position cleanup should be enabled for live:
- `system.yaml`: `auto_cleanup_unconfirmed: false` (default, warn-only)
- `system_live.yaml`: `auto_cleanup_unconfirmed: true` (paper trading)
- **For live:** Recommend starting with `false` (warn-only) until reconciliation behavior is validated over multiple sessions

### config/order_manager.yaml — Stop Cancel Retry Max
Confirm default is appropriate for live latency:
- `stop_cancel_retry_max: 3` (default) — retries with 1s/2s/4s exponential backoff
- Live IBKR may have different latency characteristics than paper — monitor and tune

---

## Learning Loop (Sprint 28)

### config/learning_loop.yaml — Auto-Trigger + Change Limits
Review before live trading:
- `auto_trigger_enabled: true` — analysis auto-fires after EOD flatten via SessionEndEvent. May want to disable until confident in analysis quality over multiple sessions.
- `max_weight_change_per_cycle: 0.10` — maximum ±10% change per quality dimension weight per analysis cycle. Review if appropriate for live.
- `max_cumulative_drift: 0.20` — 30-day rolling ceiling for total weight drift from original values. Prevents gradual drift beyond 20%.

### ConfigProposalManager — Startup-Only Application
All config changes from ConfigProposalManager require:
1. Manual approval (PENDING → APPROVED) via REST API or frontend
2. System restart to apply (`apply_pending()` runs at startup only)

**No auto-apply risk** — the system never writes config mid-session. This is by design (adversarial review amendment A1).

---

## Exit Management (Sprint 28.5)

### config/exit_management.yaml — Trailing Stop Parameters
Review trailing stop parameters for each strategy before live trading:
- `trailing_stop.enabled`: Confirm which strategies should have active trailing stops
- `trailing_stop.mode`: Verify ATR/percent/fixed is appropriate per strategy
- `trailing_stop.atr_multiplier`: Review multiplier values — paper trading defaults may be conservative
- `trailing_stop.percent_distance`: Review percent distances for strategies using percent mode
- `trailing_stop.activation`: `on_t1` (default) activates trail after T1 fill; `immediate` activates on entry

### config/exit_management.yaml — Escalation Schedules
Review exit escalation phase schedules:
- `escalation.enabled`: Confirm which strategies should have active escalation
- `escalation.phases`: Review `after_seconds` and `stop_distance` values — ensure appropriate for live position sizes and volatility
- Phase ordering: Must be ascending by `after_seconds` (Pydantic enforces)

### Trail Distances for Live Position Sizes
Paper trading uses 10x reduced risk (quality_engine.yaml). Live positions will be larger, which means:
- Trail distances (ATR multiplier, percent, fixed) may need adjustment for wider spreads on larger orders
- Belt-and-suspenders pattern: Verify that both broker stop and client-side trail check fire correctly with real IBKR
- Test bracket leg amendment (AMD) pattern with real IBKR — paper trading may have different latency characteristics

### Belt-and-Suspenders Verification with Real IBKR
Confirm the following before live trading:
- Broker stop orders are correctly maintained as server-side safety net
- Client-side `on_tick` trail check correctly triggers flatten when price breaches trail stop
- Bracket leg amendment (cancel + resubmit stop at new trail level) works reliably with live IBKR latency
- Exit reason logging correctly distinguishes TRAILING_STOP from other exit types (note: DEF-110 cosmetic misattribution on escalation-failure positions)

### Legacy Trailing Stop Config (DEF-109)
`OrderManagerConfig.enable_trailing_stop` and `trailing_stop_atr_multiplier` are dead code after Sprint 28.5.
- These fields are no longer referenced in `on_tick`
- Can be removed in a future cleanup sprint
- Do NOT set these expecting trailing stop behavior — use `config/exit_management.yaml` instead

---

## Cross-References
- DEF-101: Tests coupled to paper-trading config values
- DEF-108: R2G atr_value=None sync limitation (uses percent fallback)
- DEF-109: V1 trailing stop config dead code on OrderManagerConfig
- DEF-110: Exit reason misattribution on escalation-failure + trail-active positions
- Sprint 27.75 S1 close-out: `docs/sprints/sprint-27.75/session-1-closeout.md`
- Sprint 27.75 S1 review: `docs/sprints/sprint-27.75/session-1-review.md` (Finding F1)

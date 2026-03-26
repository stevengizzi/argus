# ARGUS — Pre-Live Transition Checklist

> **Purpose:** Config values and test assertions that were modified for paper trading
> and must be restored before transitioning to live trading.
>
> **Created:** March 26, 2026 (Sprint 27.75 doc sync)
> **Last updated:** March 26, 2026

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

## Cross-References
- DEF-101: Tests coupled to paper-trading config values
- Sprint 27.75 S1 close-out: `docs/sprints/sprint-27.75/session-1-closeout.md`
- Sprint 27.75 S1 review: `docs/sprints/sprint-27.75/session-1-review.md` (Finding F1)

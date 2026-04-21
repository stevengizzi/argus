# Risk Management Rules

These rules protect real money. Violating them is a critical bug.

## Order Flow — The Mandatory Path

Every order MUST follow this exact path:

```
Strategy emits SignalEvent
  → Event Bus delivers to Risk Manager
    → Risk Manager evaluates (strategy-level → cross-strategy → account-level)
      → IF approved: OrderApprovedEvent emitted
        → Order Manager converts to broker order(s)
          → Broker Abstraction submits to brokerage
      → IF rejected: OrderRejectedEvent emitted (with reason)
        → Logged. No order placed.
```

There is NO shortcut. No "quick order" path. No "just this once" bypass. If code exists that places a broker order without passing through the Risk Manager, it is a critical bug.

## Circuit Breakers are Non-Overridable

When a circuit breaker triggers, ALL trading stops. No component may override this. The only way to resume is:
- Automatic: next trading day (for daily limits)
- Manual: user explicitly resumes via the dashboard/API after the cooling period

Circuit breaker conditions (all configurable in config/risk_limits.yaml):
- Daily loss limit hit (default: 3% of account)
- Weekly loss limit hit (default: 5% of account)
- N consecutive losses across all strategies (default: configurable)
- System error or infrastructure failure

### Margin Circuit Breaker (DEC-367, Sprint 32.9)

IBKR error 201 (margin rejection) trips a dedicated circuit breaker. Defaults:
`margin_rejection_threshold: 10` rejections within a rolling window opens the
breaker; `margin_circuit_reset_positions: 20` positions closed with no further
rejections auto-resets it. While open, no new entries are submitted. This is a
defense against repricing storms and broker-side margin disagreement causing
runaway order spam. See `config/order_manager.yaml`.

## Position Sizing Invariants

These must ALWAYS be true for any order:
1. `risk_amount <= strategy_allocated_capital * max_risk_per_trade_pct`
2. `risk_amount <= account_daily_remaining_risk`
3. `shares * entry_price <= available_buying_power`
4. `shares > 0` (never submit zero-share orders)
5. Total deployed capital after this trade does not breach the cash reserve minimum (20%)

If ANY of these are false, the order MUST be rejected.

### Clock Injection (DEC-087, DEF-001)

Both `BaseStrategy` and `RiskManager` accept an injected `Clock` protocol
(see [argus/core/clock.py](argus/core/clock.py)). Tests use `FixedClock` to
freeze time; backtests use the BacktestEngine's bar-clock. NEVER call
`datetime.now()` directly inside risk-critical code — go through the
injected clock so deterministic replay is preserved.

### Domain Model: `shares` vs `qty` (DEF-139/140)

`Position.shares` and `Order.qty` are different fields on different types.
Never use `getattr(pos, "qty", 0)` on a `Position` — the default hides bugs
and caused DEF-139/140 ("startup zombie flatten queue"). Narrow the type
(`isinstance`) or branch explicitly before reading. See `architecture.md`
§ Domain Model.

## Stop Loss Rules

- Every entry order MUST have an associated stop-loss order placed simultaneously (bracket order)
- Stop-loss orders MUST be placed server-side at the broker (not monitored client-side only)
- Stop-loss orders MUST NOT be widened (moved further from entry) under any circumstance
- Stop-loss orders MAY be tightened (moved closer to entry / toward profit) per strategy exit rules

### Broker-Confirmed Reconciliation (DEC-369, Sprint 27.95)

The Order Manager does NOT assume a position is closed until the broker
confirms it. Internal `_broker_confirmed` state gates cleanup operations
(flatten retry, stop-price updates). Bracket exhaustion (all legs cancelled
or filled) triggers an explicit reconciliation pass rather than
fire-and-forget "close this position" calls. DEF-140 root-caused to the
prior fire-and-forget pattern — flatten reported "positions closed" while
the broker still held them. Preserve this posture on any new close path.

### Non-Bypassable Validation (Sprint 31.85)

Validation that protects order submission or position state must be a
structural precondition, not a flag-toggleable step. No `--skip-validation`,
no `--force`, no `except: log.warning(...)` that swallows the failure.
See `architecture.md` § Non-Bypassable Validation for the general posture
and the `test_no_bypass_flag_exists` grep-guard pattern.

## End of Day

- ALL intraday positions MUST be closed by 3:55 PM ET (configurable, default 5 min before close). Use ET (which resolves to EDT or EST via `ZoneInfo("America/New_York")`) — never hardcode EST.
- The EOD flatten is a hard rule, not a suggestion.
- If a position cannot be closed (broker error, halted stock), it must be flagged as a critical alert.
- **Pre-EOD signal cutoff** (Sprint 32.9, `orchestrator.signal_cutoff_time: "15:30"` ET). New
  entries are blocked after the cutoff to ensure all resulting positions can
  complete their hold and still flatten by 3:55 PM ET. Cutoff is config-gated
  and ET-anchored.
- EOD flatten is synchronous-verified: each flatten awaits an `asyncio.Event`
  per symbol for the fill confirmation (30s timeout, 1 retry), with Pass 2
  running a broker-only sweep against anything the app still thinks is open
  (Sprint 32.9).

## Logging Requirements

Every risk decision must be logged with:
- Timestamp
- Signal details (strategy, symbol, side, size)
- Decision (approved / rejected / modified)
- Reason (especially for rejections — which specific limit was hit)
- Current state of all relevant limits (daily loss used, positions open, etc.)

This audit trail is essential for debugging and for trust in the system.

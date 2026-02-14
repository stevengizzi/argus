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

## Position Sizing Invariants

These must ALWAYS be true for any order:
1. `risk_amount <= strategy_allocated_capital * max_risk_per_trade_pct`
2. `risk_amount <= account_daily_remaining_risk`
3. `shares * entry_price <= available_buying_power`
4. `shares > 0` (never submit zero-share orders)
5. Total deployed capital after this trade does not breach the cash reserve minimum (20%)

If ANY of these are false, the order MUST be rejected.

## Stop Loss Rules

- Every entry order MUST have an associated stop-loss order placed simultaneously (bracket order)
- Stop-loss orders MUST be placed server-side at the broker (not monitored client-side only)
- Stop-loss orders MUST NOT be widened (moved further from entry) under any circumstance
- Stop-loss orders MAY be tightened (moved closer to entry / toward profit) per strategy exit rules

## End of Day

- ALL intraday positions MUST be closed by 3:55 PM EST (configurable, default 5 min before close)
- The EOD flatten is a hard rule, not a suggestion
- If a position cannot be closed (broker error, halted stock), it must be flagged as a critical alert

## Logging Requirements

Every risk decision must be logged with:
- Timestamp
- Signal details (strategy, symbol, side, size)
- Decision (approved / rejected / modified)
- Reason (especially for rejections — which specific limit was hit)
- Current state of all relevant limits (daily loss used, positions open, etc.)

This audit trail is essential for debugging and for trust in the system.

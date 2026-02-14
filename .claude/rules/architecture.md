# Architecture Rules

These rules are non-negotiable. They protect the integrity of the system's design.

## Component Isolation

Strategies are isolated modules. They MUST NOT:
- Import or reference other strategies
- Import or reference the Orchestrator
- Import or reference the Risk Manager
- Directly call the Broker or Order Manager
- Access the database directly

Strategies communicate ONLY by:
- Receiving events from the Event Bus (CandleEvent, TickEvent, IndicatorEvent)
- Publishing SignalEvents to the Event Bus
- Reading their own configuration from StrategyConfig
- Calling Data Service methods for market data and indicators

## Event Bus is the Backbone

All inter-component communication goes through the Event Bus. Direct method calls between major components (strategies, orchestrator, risk manager, order manager) are prohibited.

Exception: The Risk Manager may be called synchronously by the Order Manager for immediate signal evaluation, since this is a gating decision that must happen before order submission.

## Configuration is External

All tunable parameters live in YAML config files under `config/`. Never hardcode:
- Risk limits (percentages, dollar amounts, counts)
- Strategy parameters (timeframes, targets, stop ratios, filters)
- Broker settings (API endpoints, routing rules)
- Notification settings (channels, schedules, thresholds)
- System settings (market hours, timezone, logging level)

When adding a new configurable parameter, add it to the appropriate YAML file and document it with a comment explaining what it does, its type, and its default value.

## Abstraction Layers

Three critical abstractions must always be maintained:

1. **Broker Abstraction** (`execution/broker.py`): All broker interactions go through the abstract Broker interface. Strategies and the Order Manager never import alpaca-trade-api or ib_insync directly.

2. **Data Service Abstraction** (`data/service.py`): All market data access goes through the DataService interface. Strategies never subscribe to WebSocket feeds directly.

3. **Notification Abstraction** (`notifications/service.py`): All alerts go through the NotificationService. Components never send Telegram messages or emails directly.

These abstractions enable swapping implementations (e.g., Alpaca → IBKR, live data → replay data) without touching any consuming code.

## Database Access

- All database operations go through dedicated service classes (TradeLogger, PerformanceTracker, etc.)
- No raw SQL in strategy or core logic files
- Use parameterized queries, never string interpolation for SQL
- All schema changes must be documented in docs/ARCHITECTURE.md and applied via migration scripts

## Async Discipline

- The main event loop must never be blocked
- All I/O operations (broker API, data feeds, database, file system) must be async
- CPU-intensive work (indicator calculations, backtesting) should be run in an executor (asyncio.to_thread) if it could block for >100ms
- Never use time.sleep() — use asyncio.sleep()

## Safety-Critical Code

The following components are safety-critical and require extra rigor:

- **Risk Manager**: Every code path must be tested. Every rejection must include a clear reason string. Circuit breakers must be non-bypassable.
- **Order Manager**: Order state machine must be explicit. Every state transition must be logged. Emergency flatten must work even if other components are in error state.
- **Position Sizing**: Must always check buying power before submitting. Must always verify the risk amount does not exceed strategy and account limits.

Changes to safety-critical code require:
1. Unit tests covering the specific change
2. Integration test demonstrating the behavior end-to-end
3. Review of the change against relevant Risk Register entries

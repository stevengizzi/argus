# Architecture Rules

These rules are non-negotiable. They protect the integrity of the system's design.

**Target Python: 3.11+** (per `pyproject.toml`). Rely on PEP 604 union syntax
(`X | None`), built-in parameterized generics (`list[int]`, `dict[str, Any]`),
`ZoneInfo` from the stdlib, and `StrEnum` where it fits. Do not add
`from typing import List, Dict, Optional` for types the stdlib already supplies.

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
- System settings (market hours, timezone, logging level)

When adding a new configurable parameter, add it to the appropriate YAML file and document it with a comment explaining what it does, its type, and its default value.

### Config-Gating (DEC-032, codified Sprint 27.7+)

Every feature that reads a standalone YAML file under `config/` MUST be wired
through a Pydantic submodel on `SystemConfig` (see [argus/core/config.py](argus/core/config.py)):

- Create a Pydantic `BaseModel` (not `BaseSettings`) that mirrors the YAML
  structure and is imported by `SystemConfig`.
- Expose the config as a field on `SystemConfig` with a `default_factory` so
  the feature is safe to instantiate even when the YAML is absent.
- Include an `enabled: bool = False` top-level switch unless the feature is
  truly core (e.g., Risk Manager). Default-disabled means an in-progress
  feature cannot unintentionally run in a live session.
- Feature code reads config from the `SystemConfig` field, NEVER by opening
  the YAML directly at runtime. Direct `yaml.safe_load()` inside a feature
  module is an anti-pattern.

Precedents: counterfactual.yaml (DEC-368), exit_management.yaml (Sprint 28.5),
experiments.yaml (Sprint 32.5), historical_query.yaml (Sprint 31A.5), vix_regime.yaml (Sprint 27.9).

## Abstraction Layers

Two critical abstractions must always be maintained:

1. **Broker Abstraction** (`execution/broker.py`): All broker interactions go through the abstract Broker interface. Strategies and the Order Manager never import alpaca-trade-api or ib_insync directly.

2. **Data Service Abstraction** (`data/service.py`): All market data access goes through the DataService interface. Strategies never subscribe to WebSocket feeds directly.

These abstractions enable swapping implementations (e.g., Alpaca → IBKR, live data → replay data) without touching any consuming code.

> Notifications abstraction: the [argus/notifications/](argus/notifications/)
> package currently contains only an `__init__.py` stub. A NotificationService
> abstraction was scoped but never built — the project emits alerts through
> `HealthMonitor` / logging today. If a future sprint introduces push
> notifications, reinstate the abstraction here.

## Database Access

- All database operations go through dedicated service classes (TradeLogger, PerformanceTracker, etc.)
- No raw SQL in strategy or core logic files
- Use parameterized queries, never string interpolation for SQL
- All schema changes must be documented in [docs/architecture.md](docs/architecture.md) and applied via migration scripts

### Separate-DB Pattern (DEC-309, DEC-345)

When a high-volume or contention-prone subsystem needs persistence, create a
new SQLite file next to `argus.db` rather than a new table inside `argus.db`:

- catalyst.db (DEC-309 — Sprint 23.5 catalyst precedent)
- evaluation.db (DEC-345 — ring-buffer telemetry, 7-day retention, VACUUM, Sprint 25.6 / 31.8)
- counterfactual.db (Sprint 27.7 — shadow position tracking)
- experiments.db (Sprint 32 — experiment registry + promotions)
- regime_history.db (Sprint 27.6)
- learning.db (Sprint 28)
- vix_landscape.db (Sprint 27.9)

Rationale: write contention on `argus.db` is load-bearing for live trading.
High-volume analytical stores (telemetry, regime history, counterfactuals) MUST
NOT share the live-trade file, and SHOULD use WAL mode and fire-and-forget
writes (see below).

### Non-Bypassable Validation (Sprint 31.85)

For any operation that transforms or migrates data, validation must be a
structural precondition, not a flag-toggleable step:

- No `--skip-validation` / `--force` flag may bypass a row-count or integrity
  check. If a flag exists to ease operations, it MUST NOT touch validation.
- On validation failure, the code path that would produce the output MUST be
  unreachable (e.g., atomic `.tmp → rename` only runs after a check passes;
  there is no `except: os.rename(...)` swallowing the failure).
- Add a grep-guard test that proves no such bypass flag exists in the
  implementation. Canonical example:
  [`test_no_bypass_flag_exists`](tests/scripts/test_consolidate_parquet_cache.py)
  in the Parquet consolidation script.

See `risk-rules.md` for the risk-side articulation of this posture.

## Async Discipline

- The main event loop must never be blocked
- All I/O operations (broker API, data feeds, database, file system) must be async
- CPU-intensive work (indicator calculations, backtesting) should be run in an executor (asyncio.to_thread) if it could block for >100ms
- Never use time.sleep() — use asyncio.sleep()

### Fire-and-Forget Writes (DEC-345, DEC-368)

High-volume analytical stores (EvaluationEventStore, CounterfactualStore,
ExperimentStore, RegimeHistoryStore) write with fire-and-forget semantics:
the caller does not await the DB write, and the writer catches and logs its
own errors so a failing write cannot cascade into the hot path.

Rules:
- Fire-and-forget writes MUST surface failures. Log at WARNING, not DEBUG.
  Rate-limit with `ThrottledLogger` (see `code-style.md`) — typically 60s
  per-key — so a broken DB cannot drown the log.
- NEVER silently swallow serialization failures. DEF-151 (143 Night-1 sweep
  grid points silently lost to a `datetime` serialization crash) is the
  canonical anti-pattern; the fix is `json.dumps(..., default=str)` plus a
  round-trip test of new write paths (see `code-style.md` Serialization).
- Fire-and-forget is for telemetry/analytics only. Trade-logging writes
  (`TradeLogger`) remain awaited — they are live-trading audit records.

### Trust-Cache-on-Startup (DEC-362, DEF-155/156)

Lifespan handlers must never block indefinitely on synchronous I/O:

- Load from cached state at startup, then schedule a background refresh
  (`asyncio.to_thread` or a background task).
- When exposing a startup health signal (port bind, readiness probe), gate
  it on the observable event (port open) rather than the completion of
  heavy init. `_wait_for_port()` in `main.py` is the canonical pattern; it
  was the Sprint 31.8 fix for the 12-minute blocking HistoricalQueryService
  init that caused the API server to report healthy before it was ready.
- `trust_cache_on_startup: true` on reference-data/universe loaders means
  cached values are returned immediately and a background refresh updates
  stale entries without blocking the main loop.

## Domain Model: `shares` vs `qty` (DEF-139/140)

`Position` and `Order` are distinct types with different field names:

- `Position.shares: int` — how many shares the trader holds.
- `Order.qty: int` — how many shares an order is for.

Never use `getattr(x, "qty", 0)` on a value whose type you have not narrowed.
DEF-139/140 ("startup zombie flatten queue") was caused by four Order Manager
call sites that read `getattr(pos, "qty", 0)` on a `Position` and always got
the 0 default, so flatten code reported positions closed while the broker
retained them.

Narrow types (`isinstance(x, Position)`) before reading; if a helper must
accept both, branch explicitly on type. Never rely on "qty falls back to 0"
semantics — the default hides bugs.

## Safety-Critical Code

The following components are safety-critical and require extra rigor:

- **Risk Manager**: Every code path must be tested. Every rejection must include a clear reason string. Circuit breakers must be non-bypassable.
- **Order Manager**: Order state machine must be explicit. Every state transition must be logged. Emergency flatten must work even if other components are in error state.
- **Position Sizing**: Must always check buying power before submitting. Must always verify the risk amount does not exceed strategy and account limits.

Changes to safety-critical code require:
1. Unit tests covering the specific change
2. Integration test demonstrating the behavior end-to-end
3. Review of the change against relevant Risk Register entries

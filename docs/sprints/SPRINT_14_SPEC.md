# Sprint 14 — Command Center: API Layer + Project Scaffolding

## Implementation Specification for Claude Code

> **Context:** ARGUS trading system. 811 tests across Sprints 1–13.5. Read `CLAUDE.md`, `docs/03_ARCHITECTURE.md`, and `docs/10_PHASE3_SPRINT_PLAN.md` before starting. This sprint adds the FastAPI backend + React scaffolding for the Command Center.
>
> **Target:** ~80–100 new tests. Total: ~890–910 tests.
>
> **Estimated prompts:** 8–10 (follow the prompt plan at the bottom).

---

## Decisions (Active for This Sprint)

| ID | Decision | Summary |
|----|----------|---------|
| DEC-099 | API server runs in-process | Phase 11 of `main.py` startup. Same asyncio loop. `uvicorn.Server` programmatic API. Optional via `api.enabled` config. Also runnable standalone: `python -m argus.api.server --dev`. |
| DEC-100 | `AppState` dataclass + FastAPI `Depends()` | Singleton holding references to EventBus, TradeLogger, Broker, HealthMonitor, RiskManager, strategies, OrderManager, Clock, SystemConfig. Injected into route handlers. |
| DEC-101 | WebSocket forwards curated event list | Position/order/system events forwarded. TickEvents throttled to 1/sec/symbol for open-position symbols only. Clients can filter by type via subscription message. |
| DEC-102 | Single-user JWT auth, bcrypt password | No user table. Password hash in config. `python -m argus.api.setup_password` CLI to generate hash. JWT with 24h expiry. No 2FA in V1. |
| DEC-103 | Monorepo: `argus/api/` + `argus/ui/` | FastAPI serves built React in production. Vite proxy in development. |

---

## 1. New Dependencies

Add to project requirements (or pyproject.toml / requirements.txt — match existing pattern):

```
fastapi>=0.109
uvicorn[standard]>=0.27
python-jose[cryptography]>=3.3
passlib[bcrypt]>=1.7
httpx>=0.26
```

`httpx` is a test dependency (for `TestClient`). If the project separates dev dependencies, put it there.

---

## 2. Configuration

### 2.1 New Pydantic Config Model

File: `argus/config/api_config.py`

```python
from pydantic import BaseModel, Field


class ApiConfig(BaseModel):
    """Configuration for the Command Center API server."""
    enabled: bool = True
    host: str = "0.0.0.0"
    port: int = 8000
    password_hash: str = ""  # bcrypt hash — use setup_password CLI to generate
    jwt_secret_env: str = "ARGUS_JWT_SECRET"  # env var name for JWT signing key
    jwt_expiry_hours: int = 24
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])
    ws_heartbeat_interval_seconds: int = 30
    ws_tick_throttle_ms: int = 1000
    static_dir: str = ""  # path to built React app; empty = don't serve static
```

### 2.2 Add to SystemConfig

Add `api: ApiConfig` field to the existing `SystemConfig` model. Default to `ApiConfig()` so existing configs without an `api` section still work.

### 2.3 YAML Addition

Add to `config/system.yaml`:

```yaml
api:
  enabled: true
  host: "0.0.0.0"
  port: 8000
  password_hash: ""  # Run: python -m argus.api.setup_password
  jwt_secret_env: "ARGUS_JWT_SECRET"
  jwt_expiry_hours: 24
  cors_origins:
    - "http://localhost:5173"
  ws_heartbeat_interval_seconds: 30
  ws_tick_throttle_ms: 1000
```

---

## 3. File Structure

Create these new files/directories:

```
argus/
├── api/
│   ├── __init__.py          # Exports: create_app, AppState
│   ├── server.py            # ASGI app factory, startup/shutdown lifespan, standalone entry
│   ├── auth.py              # JWT create/verify, password verify, auth dependency
│   ├── dependencies.py      # AppState dataclass, get_app_state dependency
│   ├── serializers.py       # Event → JSON serialization helpers
│   ├── setup_password.py    # CLI: generate bcrypt password hash
│   ├── routes/
│   │   ├── __init__.py      # Router aggregation
│   │   ├── auth.py          # POST /auth/login, POST /auth/refresh
│   │   ├── account.py       # GET /account
│   │   ├── positions.py     # GET /positions
│   │   ├── trades.py        # GET /trades
│   │   ├── performance.py   # GET /performance/{period}
│   │   ├── health.py        # GET /health
│   │   └── strategies.py    # GET /strategies
│   └── websocket/
│       ├── __init__.py
│       └── live.py          # WS /ws/v1/live — Event Bus bridge
├── analytics/
│   └── performance.py       # NEW: PerformanceCalculator (extracted from backtest/metrics.py)
├── ui/                      # React project — scaffolded by npm/vite
│   ├── package.json
│   ├── vite.config.ts
│   ├── tsconfig.json
│   ├── tailwind.config.js
│   ├── postcss.config.js
│   ├── index.html
│   ├── public/
│   │   └── favicon.svg
│   └── src/
│       ├── main.tsx
│       ├── App.tsx
│       ├── api/
│       │   ├── client.ts    # Fetch wrapper with JWT auth
│       │   ├── types.ts     # TypeScript interfaces for all API responses
│       │   └── ws.ts        # Reconnecting WebSocket client
│       ├── hooks/
│       │   └── useAuth.ts   # Auth hook (login, logout, token state)
│       ├── stores/
│       │   ├── auth.ts      # Zustand auth store
│       │   └── live.ts      # Zustand store for WebSocket events
│       ├── components/
│       │   └── ProtectedRoute.tsx
│       └── pages/
│           ├── Login.tsx
│           └── ConnectionTest.tsx  # Dev validation page
tests/
├── api/
│   ├── __init__.py
│   ├── conftest.py          # Shared fixtures: mock AppState, test client, auth token
│   ├── test_auth.py
│   ├── test_account.py
│   ├── test_positions.py
│   ├── test_trades.py
│   ├── test_performance.py
│   ├── test_health.py
│   ├── test_strategies.py
│   ├── test_websocket.py
│   └── test_server.py       # Lifecycle, CORS, integration
├── analytics/
│   └── test_performance.py  # PerformanceCalculator tests
```

---

## 4. Component Specifications

### 4.1 AppState (`argus/api/dependencies.py`)

```python
from dataclasses import dataclass, field
from argus.core.event_bus import EventBus
from argus.core.risk_manager import RiskManager
from argus.core.health import HealthMonitor
from argus.core.clock import Clock
from argus.execution.order_manager import OrderManager
from argus.execution.broker import Broker
from argus.analytics.trade_log import TradeLogger
from argus.strategies.base_strategy import BaseStrategy
from argus.config.config import SystemConfig
from argus.data.service import DataService


@dataclass
class AppState:
    """Holds references to all trading engine components for API access."""
    event_bus: EventBus
    trade_logger: TradeLogger
    broker: Broker
    health_monitor: HealthMonitor
    risk_manager: RiskManager
    order_manager: OrderManager
    data_service: DataService
    strategies: dict[str, BaseStrategy]
    clock: Clock
    config: SystemConfig
    start_time: float = 0.0  # time.time() at startup, for uptime calc


# Module-level holder for the singleton
_app_state: AppState | None = None


def set_app_state(state: AppState) -> None:
    global _app_state
    _app_state = state


def get_app_state() -> AppState:
    if _app_state is None:
        raise RuntimeError("AppState not initialized")
    return _app_state
```

For `--dev` standalone mode, create a `MockAppState` factory in `argus/api/dev_state.py` that provides:
- `EventBus` — real instance (lightweight)
- `TradeLogger` — real instance connected to an in-memory or temp SQLite DB, pre-seeded with ~20 sample trades
- `SimulatedBroker` — with a fake $100K account
- `HealthMonitor` — real instance with all components set to healthy
- `RiskManager` — real instance (default config)
- `OrderManager` — real instance (no active positions)
- `DataService` — None or a stub (no streaming in dev mode)
- `strategies` — dict with one mock OrbBreakout strategy (inactive, sample config)
- `Clock` — `SystemClock()`
- `config` — default `SystemConfig` with api section populated

The dev state should also inject 2–3 sample `ManagedPosition` objects into the OrderManager so the positions endpoint returns data. Seed the TradeLogger with trades spanning the last 30 days with realistic-looking data (mix of wins, losses, different exit reasons, varying hold durations).

### 4.2 Auth (`argus/api/auth.py`)

```python
from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError
from passlib.hash import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials


security = HTTPBearer()
ALGORITHM = "HS256"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a bcrypt hash."""
    return bcrypt.verify(plain_password, hashed_password)


def create_access_token(jwt_secret: str, expires_hours: int = 24) -> tuple[str, datetime]:
    """Create a JWT access token. Returns (token, expires_at)."""
    expires_at = datetime.now(timezone.utc) + timedelta(hours=expires_hours)
    payload = {"exp": expires_at, "iat": datetime.now(timezone.utc), "sub": "operator"}
    token = jwt.encode(payload, jwt_secret, algorithm=ALGORITHM)
    return token, expires_at


def verify_token(token: str, jwt_secret: str) -> dict:
    """Verify and decode a JWT token. Raises HTTPException on failure."""
    try:
        payload = jwt.decode(token, jwt_secret, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )


def require_auth(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    state: "AppState" = Depends(get_app_state),
) -> dict:
    """FastAPI dependency that validates the JWT token."""
    jwt_secret = _resolve_jwt_secret(state.config.api)
    return verify_token(credentials.credentials, jwt_secret)


def _resolve_jwt_secret(api_config) -> str:
    """Resolve JWT secret from environment variable."""
    import os
    secret = os.environ.get(api_config.jwt_secret_env, "")
    if not secret:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="JWT secret not configured",
        )
    return secret
```

### 4.3 Setup Password CLI (`argus/api/setup_password.py`)

```python
"""CLI tool to generate a bcrypt password hash for API authentication.

Usage:
    python -m argus.api.setup_password
"""
import getpass
from passlib.hash import bcrypt


def main():
    print("ARGUS Command Center — Password Setup")
    print("=" * 40)
    password = getpass.getpass("Enter password: ")
    confirm = getpass.getpass("Confirm password: ")

    if password != confirm:
        print("Error: Passwords do not match.")
        return

    if len(password) < 8:
        print("Error: Password must be at least 8 characters.")
        return

    hashed = bcrypt.hash(password)
    print(f"\nAdd this to your config/system.yaml under api:")
    print(f'  password_hash: "{hashed}"')
    print(f"\nAlso set ARGUS_JWT_SECRET environment variable:")
    print(f"  export ARGUS_JWT_SECRET=$(python -c \"import secrets; print(secrets.token_hex(32))\")")


if __name__ == "__main__":
    main()
```

### 4.4 Server Factory (`argus/api/server.py`)

```python
"""
ARGUS API Server — FastAPI application factory.

Usage:
    # As part of trading engine (Phase 11 in main.py):
    from argus.api.server import create_app, run_server
    app = create_app(app_state)
    await run_server(app, config.api)

    # Standalone development mode:
    python -m argus.api.server --dev --port 8000
"""
import asyncio
import logging
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from argus.api.dependencies import AppState, set_app_state
from argus.api.routes import api_router
from argus.api.websocket.live import ws_router

logger = logging.getLogger(__name__)


def create_app(state: AppState) -> FastAPI:
    """Create and configure the FastAPI application."""

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        set_app_state(state)
        logger.info("API server starting — state injected")
        yield
        logger.info("API server shutting down")

    app = FastAPI(
        title="ARGUS Command Center API",
        version="1.0.0",
        lifespan=lifespan,
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=state.config.api.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Routes
    app.include_router(api_router, prefix="/api/v1")
    app.include_router(ws_router)

    # Serve built React app if configured
    if state.config.api.static_dir:
        app.mount("/", StaticFiles(directory=state.config.api.static_dir, html=True))

    return app


async def run_server(app: FastAPI, host: str, port: int) -> asyncio.Task:
    """Start uvicorn programmatically inside the existing event loop.
    Returns the server task so it can be cancelled on shutdown."""
    config = uvicorn.Config(app, host=host, port=port, log_level="info")
    server = uvicorn.Server(config)

    # Override server.install_signal_handlers to avoid conflict with main.py's handlers
    server.install_signal_handlers = lambda: None

    task = asyncio.create_task(server.serve())
    logger.info(f"API server listening on {host}:{port}")
    return task
```

**Standalone `__main__` block** (at bottom of `server.py` or as `argus/api/__main__.py`):

```python
"""Standalone API server for frontend development."""
import argparse
import asyncio


def main():
    parser = argparse.ArgumentParser(description="ARGUS API Server")
    parser.add_argument("--dev", action="store_true", help="Run with mock data for frontend development")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    if args.dev:
        from argus.api.dev_state import create_dev_state
        state = asyncio.run(create_dev_state())
    else:
        # Load real config and attempt to connect to engine components
        raise SystemExit("Non-dev standalone mode not implemented. Use --dev or start via main.py.")

    app = create_app(state)
    import uvicorn
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
```

### 4.5 Route Implementations

All routes live under `argus/api/routes/`. Each file defines a `router = APIRouter()` that gets included in the aggregated `api_router`.

#### `routes/__init__.py`

```python
from fastapi import APIRouter
from argus.api.routes.auth import router as auth_router
from argus.api.routes.account import router as account_router
from argus.api.routes.positions import router as positions_router
from argus.api.routes.trades import router as trades_router
from argus.api.routes.performance import router as performance_router
from argus.api.routes.health import router as health_router
from argus.api.routes.strategies import router as strategies_router

api_router = APIRouter()
api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(account_router, tags=["account"])
api_router.include_router(positions_router, tags=["positions"])
api_router.include_router(trades_router, tags=["trades"])
api_router.include_router(performance_router, tags=["performance"])
api_router.include_router(health_router, tags=["health"])
api_router.include_router(strategies_router, tags=["strategies"])
```

#### `routes/auth.py`

```python
# POST /api/v1/auth/login
# Request body: { "password": "string" }
# Response: { "access_token": "...", "token_type": "bearer", "expires_at": "ISO8601" }
# 401 on invalid password

# POST /api/v1/auth/refresh
# Requires valid token in Authorization header
# Returns new token with fresh expiry
```

#### `routes/account.py`

```python
# GET /api/v1/account
# Requires auth
# Sources: broker.get_account(), trade_logger queries, clock for market status
# Response shape defined in Section 6 (API Response Schemas)
```

**Market status logic:**
```python
def _get_market_status(clock: Clock) -> str:
    """Determine current market status from clock time (ET)."""
    now_et = clock.now().astimezone(ZoneInfo("America/New_York"))
    t = now_et.time()
    weekday = now_et.weekday()
    if weekday >= 5:
        return "closed"
    if time(4, 0) <= t < time(9, 30):
        return "pre_market"
    if time(9, 30) <= t < time(16, 0):
        return "open"
    if time(16, 0) <= t < time(20, 0):
        return "after_hours"
    return "closed"
```

#### `routes/positions.py`

```python
# GET /api/v1/positions
# Query params: strategy_id (optional)
# Requires auth
# Source: order_manager._managed_positions (internal access via a public method)
# Enrich each position with:
#   - current_price from data_service.get_current_price(symbol)
#   - unrealized_pnl = (current_price - entry_price) * shares_remaining
#   - unrealized_pnl_pct = unrealized_pnl / (entry_price * shares_remaining) * 100
#   - hold_duration_seconds from entry_time to clock.now()
#   - r_multiple_current = (current_price - entry_price) / (entry_price - stop_price)
```

**Important:** The `OrderManager` currently exposes `_managed_positions` as a private dict. Add a public method:

```python
# Add to OrderManager
def get_managed_positions(self) -> list[ManagedPosition]:
    """Return a snapshot of all managed positions (for API/UI consumption)."""
    result = []
    for positions in self._managed_positions.values():
        result.extend(positions)
    return result
```

#### `routes/trades.py`

```python
# GET /api/v1/trades
# Query params: strategy_id, date_from, date_to, outcome (win/loss/breakeven), limit (default 50), offset (default 0)
# Requires auth
# Source: TradeLogger database queries
```

**Required: Add query methods to TradeLogger** (or create a new `TradeQueryService` — prefer adding to `TradeLogger` for simplicity):

```python
# Add to TradeLogger (argus/analytics/trade_log.py)

async def query_trades(
    self,
    strategy_id: str | None = None,
    date_from: str | None = None,  # ISO date string "2026-02-01"
    date_to: str | None = None,
    outcome: str | None = None,  # "win", "loss", "breakeven"
    limit: int = 50,
    offset: int = 0,
) -> list[dict]:
    """Query trades with filtering and pagination.
    Returns list of trade dicts from the trades table.
    Ordered by entry_time DESC (most recent first)."""
    # Build WHERE clause dynamically
    # outcome filter: "win" = pnl_dollars > 0, "loss" = pnl_dollars < 0,
    #   "breakeven" = pnl_dollars == 0 (or is NULL for open trades)
    # date_from/date_to filter on entry_time
    ...

async def count_trades(
    self,
    strategy_id: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    outcome: str | None = None,
) -> int:
    """Count trades matching filters (for pagination)."""
    ...

async def get_daily_pnl(
    self,
    date_from: str | None = None,
    date_to: str | None = None,
) -> list[dict]:
    """Get daily P&L aggregation.
    Returns list of {date, pnl, trades} dicts.
    Source: strategy_daily_performance table, aggregated across strategies."""
    ...

async def get_todays_pnl(self) -> float:
    """Get today's total realized P&L across all strategies."""
    ...
```

#### `routes/performance.py`

```python
# GET /api/v1/performance/{period}
# period: "today", "week", "month", "all"
# Requires auth
# Source: PerformanceCalculator + TradeLogger queries
```

**Map period to date range:**
- `today`: today's date only
- `week`: Monday of current week to today
- `month`: 1st of current month to today
- `all`: all trades in database

Use the new `PerformanceCalculator` (see Section 5) to compute metrics from the trade list.

#### `routes/health.py`

```python
# GET /api/v1/health
# Requires auth
# Source: HealthMonitor.get_status(), component statuses, uptime from AppState.start_time
```

**Required:** HealthMonitor needs a public method to return all component statuses:

```python
# Add to HealthMonitor if not already present
def get_component_statuses(self) -> dict[str, dict]:
    """Return all component statuses as {name: {status, details}}."""
    ...

def get_overall_status(self) -> str:
    """Return overall system status: healthy, degraded, unhealthy."""
    ...
```

Check what the existing HealthMonitor already exposes and add minimal new methods.

#### `routes/strategies.py`

```python
# GET /api/v1/strategies
# Requires auth
# Source: AppState.strategies dict
# For each strategy, return: strategy_id, name, version, is_active, pipeline_stage,
#   allocated_capital, daily_pnl, trade_count_today, open_positions count,
#   config_summary (dict of key config params)
```

### 4.6 WebSocket Bridge (`argus/api/websocket/live.py`)

This is the most architecturally significant component. It bridges the internal Event Bus to external WebSocket clients.

```python
"""
WebSocket endpoint that bridges Event Bus events to frontend clients.

Architecture:
    EventBus → WebSocketBridge (subscriber) → connected WebSocket clients

Throttling:
    - TickEvents: max 1/sec/symbol, only for symbols with open positions
    - All other events: forwarded immediately
    - Heartbeat sent every ws_heartbeat_interval_seconds

Client subscription:
    Clients can optionally filter events by type via subscription messages.
    Default: receive all forwarded event types.

Protocol:
    Server → Client: { "type": "position.opened", "data": {...}, "sequence": N, "timestamp": "..." }
    Client → Server: { "action": "subscribe", "types": ["position.opened", ...] }
    Client → Server: { "action": "ping" } → Server: { "type": "pong", "timestamp": "..." }
"""

import asyncio
import json
import logging
import time
from datetime import datetime, timezone

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from starlette.websockets import WebSocketState

from argus.api.auth import verify_token, _resolve_jwt_secret
from argus.api.dependencies import get_app_state
from argus.api.serializers import serialize_event

logger = logging.getLogger(__name__)
ws_router = APIRouter()


# Event type mapping: internal Event class name → WS type string
EVENT_TYPE_MAP = {
    "PositionOpenedEvent": "position.opened",
    "PositionClosedEvent": "position.closed",
    "PositionUpdatedEvent": "position.updated",
    "OrderSubmittedEvent": "order.submitted",
    "OrderFilledEvent": "order.filled",
    "OrderCancelledEvent": "order.cancelled",
    "CircuitBreakerEvent": "system.circuit_breaker",
    "HeartbeatEvent": "system.heartbeat",
    "WatchlistEvent": "scanner.watchlist",
    "SignalEvent": "strategy.signal",
    "OrderApprovedEvent": "order.approved",
    "OrderRejectedEvent": "order.rejected",
}

# TickEvent is handled specially (throttled, position-filtered)
TICK_WS_TYPE = "price.update"


class ClientConnection:
    """Represents a single connected WebSocket client."""

    def __init__(self, websocket: WebSocket):
        self.websocket = websocket
        self.subscribed_types: set[str] | None = None  # None = all types
        self.send_queue: asyncio.Queue = asyncio.Queue(maxsize=1000)

    def wants_event(self, ws_type: str) -> bool:
        if self.subscribed_types is None:
            return True
        return ws_type in self.subscribed_types


class WebSocketBridge:
    """Bridges Event Bus events to WebSocket clients.

    Lifecycle:
    1. Created once during app startup.
    2. Subscribes to relevant Event Bus event types.
    3. On each event, serializes and enqueues for all interested clients.
    4. Each client has a sender task that drains its queue.
    """

    def __init__(self):
        self.clients: list[ClientConnection] = []
        self._tick_last_sent: dict[str, float] = {}  # symbol → timestamp
        self._tick_throttle_ms: int = 1000
        self._heartbeat_interval: int = 30
        self._heartbeat_task: asyncio.Task | None = None

    async def start(self, event_bus, order_manager, config) -> None:
        """Subscribe to Event Bus events and start heartbeat."""
        self._tick_throttle_ms = config.api.ws_tick_throttle_ms
        self._heartbeat_interval = config.api.ws_heartbeat_interval_seconds
        self._order_manager = order_manager

        # Subscribe to all forwarded event types
        from argus.core import events  # Import actual event classes
        for event_class_name in EVENT_TYPE_MAP:
            event_class = getattr(events, event_class_name, None)
            if event_class:
                event_bus.subscribe(event_class, self._on_event)

        # Subscribe to TickEvent separately for throttled handling
        from argus.core.events import TickEvent
        event_bus.subscribe(TickEvent, self._on_tick)

        # Start heartbeat
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())

    async def stop(self) -> None:
        if self._heartbeat_task:
            self._heartbeat_task.cancel()

    async def _on_event(self, event) -> None:
        """Handle a non-tick Event Bus event."""
        event_type_name = type(event).__name__
        ws_type = EVENT_TYPE_MAP.get(event_type_name)
        if not ws_type:
            return
        message = {
            "type": ws_type,
            "data": serialize_event(event),
            "sequence": event.sequence,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        await self._broadcast(message)

    async def _on_tick(self, event) -> None:
        """Handle TickEvent with throttling and position filtering."""
        # Only forward ticks for symbols with open positions
        open_symbols = {
            p.symbol for p in self._order_manager.get_managed_positions()
        }
        if event.symbol not in open_symbols:
            return

        # Throttle: max 1 per tick_throttle_ms per symbol
        now = time.monotonic()
        last = self._tick_last_sent.get(event.symbol, 0.0)
        if (now - last) * 1000 < self._tick_throttle_ms:
            return
        self._tick_last_sent[event.symbol] = now

        message = {
            "type": TICK_WS_TYPE,
            "data": {
                "symbol": event.symbol,
                "price": event.price,
                "volume": event.volume,
            },
            "sequence": event.sequence,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        await self._broadcast(message)

    async def _broadcast(self, message: dict) -> None:
        """Send message to all interested connected clients."""
        ws_type = message["type"]
        for client in self.clients:
            if client.wants_event(ws_type):
                try:
                    client.send_queue.put_nowait(message)
                except asyncio.QueueFull:
                    logger.warning("Client send queue full, dropping message")

    async def _heartbeat_loop(self) -> None:
        while True:
            await asyncio.sleep(self._heartbeat_interval)
            message = {
                "type": "system.heartbeat",
                "data": {"status": "alive"},
                "sequence": -1,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            await self._broadcast(message)

    def add_client(self, client: ClientConnection) -> None:
        self.clients.append(client)

    def remove_client(self, client: ClientConnection) -> None:
        self.clients.remove(client)


# Module-level singleton — initialized during app startup
_bridge: WebSocketBridge | None = None

def get_bridge() -> WebSocketBridge:
    global _bridge
    if _bridge is None:
        _bridge = WebSocketBridge()
    return _bridge


@ws_router.websocket("/ws/v1/live")
async def websocket_endpoint(websocket: WebSocket, token: str = Query(...)):
    """WebSocket endpoint for real-time event streaming."""
    # Authenticate
    try:
        state = get_app_state()
        jwt_secret = _resolve_jwt_secret(state.config.api)
        verify_token(token, jwt_secret)
    except Exception:
        await websocket.close(code=4001, reason="Authentication failed")
        return

    await websocket.accept()
    bridge = get_bridge()
    client = ClientConnection(websocket)
    bridge.add_client(client)

    # Sender task: drain client's queue and send
    async def sender():
        try:
            while True:
                message = await client.send_queue.get()
                if websocket.client_state == WebSocketState.CONNECTED:
                    await websocket.send_json(message)
        except Exception:
            pass

    sender_task = asyncio.create_task(sender())

    try:
        # Receiver loop: handle client messages
        while True:
            data = await websocket.receive_json()
            action = data.get("action")

            if action == "ping":
                await websocket.send_json({
                    "type": "pong",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })
            elif action == "subscribe":
                client.subscribed_types = set(data.get("types", []))
            elif action == "unsubscribe":
                types_to_remove = set(data.get("types", []))
                if client.subscribed_types is not None:
                    client.subscribed_types -= types_to_remove
            # Unknown actions silently ignored

    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.warning(f"WebSocket error: {e}")
    finally:
        sender_task.cancel()
        bridge.remove_client(client)
```

### 4.7 Event Serializer (`argus/api/serializers.py`)

```python
"""Serialize Event Bus events to JSON-compatible dicts for WebSocket/API consumption."""
from dataclasses import asdict
from datetime import datetime


def serialize_event(event) -> dict:
    """Convert an Event dataclass to a JSON-serializable dict.

    Handles datetime serialization and removes internal fields.
    Falls back to __dict__ if asdict fails.
    """
    try:
        data = asdict(event)
    except Exception:
        data = {k: v for k, v in event.__dict__.items() if not k.startswith("_")}

    # Convert datetime objects to ISO strings
    for key, value in data.items():
        if isinstance(value, datetime):
            data[key] = value.isoformat()

    # Remove sequence (it's in the wrapper, not the data payload)
    data.pop("sequence", None)

    return data
```

**Note:** Some events contain nested dataclasses (e.g., `OrderApprovedEvent.signal_event`). The `asdict` call handles this recursively. If any event has non-serializable fields (e.g., broker connection objects), add explicit handling. Test this with every forwarded event type.

### 4.8 PerformanceCalculator (`argus/analytics/performance.py`)

Extract metric computation from `argus/backtest/metrics.py` into a shared utility. The backtest metrics module should then import from this shared module.

```python
"""Shared performance metric computation for both live trading and backtesting.

Used by:
- API /performance endpoint (live trade data from TradeLogger)
- BacktestMetrics (backtest trade data from replay runs)
"""
from dataclasses import dataclass
import math


@dataclass
class PerformanceMetrics:
    """Computed performance metrics for a set of trades."""
    total_trades: int = 0
    wins: int = 0
    losses: int = 0
    breakeven: int = 0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    net_pnl: float = 0.0
    gross_pnl: float = 0.0
    total_commissions: float = 0.0
    avg_r_multiple: float = 0.0
    sharpe_ratio: float = 0.0
    max_drawdown_pct: float = 0.0
    avg_hold_seconds: float = 0.0
    largest_win: float = 0.0
    largest_loss: float = 0.0
    consecutive_wins_max: int = 0
    consecutive_losses_max: int = 0


def compute_metrics(trades: list[dict]) -> PerformanceMetrics:
    """Compute performance metrics from a list of trade dicts.

    Expected dict keys: pnl_dollars, pnl_r_multiple, commission,
    hold_duration_seconds, exit_price (None = still open, skip).

    Only closed trades (exit_price is not None) are included in calculations.
    """
    # Filter to closed trades only
    closed = [t for t in trades if t.get("exit_price") is not None]

    if not closed:
        return PerformanceMetrics()

    # ... compute all metrics ...
    # This is largely a refactor of what's already in backtest/metrics.py
    # Key computations:
    #   win_rate = wins / total
    #   profit_factor = gross_wins / abs(gross_losses)  (inf if no losses)
    #   sharpe = mean(daily_returns) / std(daily_returns) * sqrt(252)
    #   max_drawdown from cumulative P&L curve
    #   consecutive wins/losses from sequential scan
    ...
```

**Important:** Look at the existing `BacktestMetrics` in `argus/backtest/metrics.py`. Extract the core computation logic into `PerformanceCalculator.compute_metrics()`. Then refactor `BacktestMetrics` to call `compute_metrics()` internally. This avoids code duplication and ensures live and backtest metrics use identical formulas.

### 4.9 main.py Integration

Add Phase 11 to the existing startup sequence:

```python
# ─── Phase 11: API Server (optional) ────────────────────────────
if config.api.enabled:
    from argus.api.server import create_app, run_server
    from argus.api.dependencies import AppState, set_app_state
    from argus.api.websocket.live import get_bridge

    app_state = AppState(
        event_bus=event_bus,
        trade_logger=trade_logger,
        broker=broker,
        health_monitor=health_monitor,
        risk_manager=risk_manager,
        order_manager=order_manager,
        data_service=data_service,
        strategies={"orb_breakout": strategy},  # dict of active strategies
        clock=clock,
        config=config,
        start_time=time.time(),
    )

    api_app = create_app(app_state)

    # Start WebSocket bridge (subscribes to Event Bus)
    ws_bridge = get_bridge()
    await ws_bridge.start(event_bus, order_manager, config)

    # Start API server
    api_task = await run_server(api_app, config.api.host, config.api.port)
    logger.info("Phase 11: API server started")
else:
    api_task = None
    logger.info("Phase 11: API server disabled")
```

**Shutdown:** Add to the shutdown sequence (before existing component shutdowns):

```python
# Shutdown API server
if api_task:
    api_task.cancel()
    try:
        await api_task
    except asyncio.CancelledError:
        pass
    ws_bridge = get_bridge()
    await ws_bridge.stop()
    logger.info("API server stopped")
```

---

## 5. React Project Scaffolding

### 5.1 Initialize

```bash
cd argus/ui
npm create vite@latest . -- --template react-ts
npm install react-router-dom zustand @tanstack/react-query recharts lucide-react
npm install -D tailwindcss postcss autoprefixer @types/react @types/react-dom
npx tailwindcss init -p
```

### 5.2 Key Config Files

**`vite.config.ts`:**
```typescript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/ws': {
        target: 'ws://localhost:8000',
        ws: true,
      },
    },
  },
})
```

**`tailwind.config.js`:**
```javascript
/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        // ARGUS brand colors — dark theme for trading dashboard
        argus: {
          bg: '#0f1117',
          surface: '#1a1d27',
          border: '#2a2d3a',
          text: '#e1e4eb',
          'text-dim': '#8b8fa3',
          accent: '#3b82f6',    // blue
          success: '#22c55e',   // green — profit
          danger: '#ef4444',    // red — loss
          warning: '#f59e0b',   // amber — caution
        },
      },
    },
  },
  plugins: [],
}
```

**`src/index.css`:**
```css
@tailwind base;
@tailwind components;
@tailwind utilities;

body {
  @apply bg-argus-bg text-argus-text;
  font-family: 'Inter', system-ui, sans-serif;
}
```

### 5.3 TypeScript Types (`src/api/types.ts`)

```typescript
// === Auth ===
export interface LoginRequest {
  password: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  expires_at: string;
}

// === Account ===
export interface AccountInfo {
  equity: number;
  cash: number;
  buying_power: number;
  daily_pnl: number;
  daily_pnl_pct: number;
  open_positions_count: number;
  daily_trades_count: number;
  market_status: 'pre_market' | 'open' | 'closed' | 'after_hours';
  broker_source: 'alpaca' | 'ibkr' | 'simulated';
  data_source: 'alpaca' | 'databento';
  timestamp: string;
}

// === Positions ===
export interface Position {
  position_id: string;
  strategy_id: string;
  symbol: string;
  side: 'long' | 'short';
  entry_price: number;
  entry_time: string;
  shares_total: number;
  shares_remaining: number;
  current_price: number;
  unrealized_pnl: number;
  unrealized_pnl_pct: number;
  stop_price: number;
  t1_price: number;
  t2_price: number;
  t1_filled: boolean;
  hold_duration_seconds: number;
  r_multiple_current: number;
}

export interface PositionsResponse {
  positions: Position[];
  count: number;
  timestamp: string;
}

// === Trades ===
export interface Trade {
  id: string;
  strategy_id: string;
  symbol: string;
  side: 'long' | 'short';
  entry_price: number;
  entry_time: string;
  exit_price: number | null;
  exit_time: string | null;
  shares: number;
  pnl_dollars: number | null;
  pnl_r_multiple: number | null;
  exit_reason: string | null;
  hold_duration_seconds: number | null;
  commission: number;
  market_regime: string | null;
}

export interface TradesResponse {
  trades: Trade[];
  total_count: number;
  limit: number;
  offset: number;
  timestamp: string;
}

// === Performance ===
export interface PerformanceMetrics {
  total_trades: number;
  win_rate: number;
  profit_factor: number;
  net_pnl: number;
  gross_pnl: number;
  total_commissions: number;
  avg_r_multiple: number;
  sharpe_ratio: number;
  max_drawdown_pct: number;
  avg_hold_seconds: number;
  largest_win: number;
  largest_loss: number;
  consecutive_wins_max: number;
  consecutive_losses_max: number;
}

export interface DailyPnl {
  date: string;
  pnl: number;
  trades: number;
}

export interface StrategyPerformanceSummary {
  total_trades: number;
  win_rate: number;
  net_pnl: number;
  profit_factor: number;
}

export interface PerformanceResponse {
  period: string;
  date_from: string;
  date_to: string;
  metrics: PerformanceMetrics;
  daily_pnl: DailyPnl[];
  by_strategy: Record<string, StrategyPerformanceSummary>;
  timestamp: string;
}

// === Health ===
export interface ComponentHealth {
  status: 'healthy' | 'degraded' | 'unhealthy';
  details: string;
}

export interface HealthResponse {
  status: 'healthy' | 'degraded' | 'unhealthy';
  uptime_seconds: number;
  components: Record<string, ComponentHealth>;
  last_heartbeat: string;
  last_trade: string | null;
  last_data_received: string | null;
  paper_mode: boolean;
  timestamp: string;
}

// === Strategies ===
export interface Strategy {
  strategy_id: string;
  name: string;
  version: string;
  is_active: boolean;
  pipeline_stage: string;
  allocated_capital: number;
  daily_pnl: number;
  trade_count_today: number;
  open_positions: number;
  config_summary: Record<string, unknown>;
}

export interface StrategiesResponse {
  strategies: Strategy[];
  count: number;
  timestamp: string;
}

// === WebSocket ===
export interface WsMessage {
  type: string;
  data: Record<string, unknown>;
  sequence: number;
  timestamp: string;
}
```

### 5.4 API Client (`src/api/client.ts`)

```typescript
const BASE_URL = '';  // Proxied by Vite in dev, same origin in production

class ApiClient {
  private token: string | null = null;

  setToken(token: string | null) {
    this.token = token;
  }

  private async request<T>(path: string, options?: RequestInit): Promise<T> {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...(this.token ? { Authorization: `Bearer ${this.token}` } : {}),
    };

    const response = await fetch(`${BASE_URL}${path}`, {
      ...options,
      headers: { ...headers, ...options?.headers },
    });

    if (response.status === 401) {
      // Token expired — trigger re-login
      this.token = null;
      window.dispatchEvent(new Event('auth:expired'));
      throw new Error('Authentication expired');
    }

    if (!response.ok) {
      const body = await response.json().catch(() => ({}));
      throw new Error(body.detail || `HTTP ${response.status}`);
    }

    return response.json();
  }

  // Auth
  login(password: string) {
    return this.request<LoginResponse>('/api/v1/auth/login', {
      method: 'POST',
      body: JSON.stringify({ password }),
    });
  }

  refresh() {
    return this.request<LoginResponse>('/api/v1/auth/refresh', { method: 'POST' });
  }

  // Read endpoints
  getAccount() { return this.request<AccountInfo>('/api/v1/account'); }
  getPositions(strategyId?: string) {
    const params = strategyId ? `?strategy_id=${strategyId}` : '';
    return this.request<PositionsResponse>(`/api/v1/positions${params}`);
  }
  getTrades(params?: Record<string, string>) {
    const qs = params ? '?' + new URLSearchParams(params).toString() : '';
    return this.request<TradesResponse>(`/api/v1/trades${qs}`);
  }
  getPerformance(period: string) {
    return this.request<PerformanceResponse>(`/api/v1/performance/${period}`);
  }
  getHealth() { return this.request<HealthResponse>('/api/v1/health'); }
  getStrategies() { return this.request<StrategiesResponse>('/api/v1/strategies'); }
}

export const api = new ApiClient();
```

### 5.5 WebSocket Client (`src/api/ws.ts`)

```typescript
type MessageHandler = (message: WsMessage) => void;

export class ArgusWebSocket {
  private ws: WebSocket | null = null;
  private url: string;
  private token: string;
  private handlers: Set<MessageHandler> = new Set();
  private reconnectDelay = 1000;
  private maxReconnectDelay = 30000;
  private shouldReconnect = true;

  constructor(token: string) {
    this.token = token;
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    this.url = `${protocol}//${window.location.host}/ws/v1/live?token=${token}`;
  }

  connect() {
    this.shouldReconnect = true;
    this._connect();
  }

  private _connect() {
    this.ws = new WebSocket(this.url);

    this.ws.onopen = () => {
      this.reconnectDelay = 1000;  // Reset backoff
      console.log('[WS] Connected');
    };

    this.ws.onmessage = (event) => {
      try {
        const message: WsMessage = JSON.parse(event.data);
        this.handlers.forEach((handler) => handler(message));
      } catch (e) {
        console.warn('[WS] Failed to parse message:', e);
      }
    };

    this.ws.onclose = () => {
      console.log('[WS] Disconnected');
      if (this.shouldReconnect) {
        setTimeout(() => this._connect(), this.reconnectDelay);
        this.reconnectDelay = Math.min(this.reconnectDelay * 2, this.maxReconnectDelay);
      }
    };

    this.ws.onerror = (error) => {
      console.warn('[WS] Error:', error);
    };
  }

  disconnect() {
    this.shouldReconnect = false;
    this.ws?.close();
  }

  subscribe(types: string[]) {
    this.ws?.send(JSON.stringify({ action: 'subscribe', types }));
  }

  onMessage(handler: MessageHandler) {
    this.handlers.add(handler);
    return () => this.handlers.delete(handler);  // Unsubscribe function
  }

  get isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }
}
```

### 5.6 Zustand Stores

**`src/stores/auth.ts`:**
```typescript
import { create } from 'zustand';
import { api } from '../api/client';

interface AuthState {
  token: string | null;
  isAuthenticated: boolean;
  login: (password: string) => Promise<void>;
  logout: () => void;
  init: () => void;  // Check localStorage for existing token
}

export const useAuthStore = create<AuthState>((set) => ({
  token: null,
  isAuthenticated: false,

  login: async (password: string) => {
    const response = await api.login(password);
    api.setToken(response.access_token);
    localStorage.setItem('argus_token', response.access_token);
    set({ token: response.access_token, isAuthenticated: true });
  },

  logout: () => {
    api.setToken(null);
    localStorage.removeItem('argus_token');
    set({ token: null, isAuthenticated: false });
  },

  init: () => {
    const token = localStorage.getItem('argus_token');
    if (token) {
      api.setToken(token);
      set({ token, isAuthenticated: true });
    }
  },
}));
```

**`src/stores/live.ts`:**
```typescript
import { create } from 'zustand';
import { WsMessage } from '../api/types';

interface LiveState {
  connected: boolean;
  lastMessage: WsMessage | null;
  positions: Record<string, unknown>;
  recentEvents: WsMessage[];
  setConnected: (connected: boolean) => void;
  handleMessage: (message: WsMessage) => void;
}

export const useLiveStore = create<LiveState>((set) => ({
  connected: false,
  lastMessage: null,
  positions: {},
  recentEvents: [],

  setConnected: (connected) => set({ connected }),

  handleMessage: (message) => set((state) => ({
    lastMessage: message,
    recentEvents: [message, ...state.recentEvents].slice(0, 100),  // Keep last 100
  })),
}));
```

### 5.7 Pages

**`src/pages/Login.tsx`:** Simple dark-themed login form. Password input + submit button. Shows error on invalid credentials. Redirects to main page on success.

**`src/pages/ConnectionTest.tsx`:** Developer validation page. Sections:
1. **Auth Status** — Shows current JWT token (truncated), expiry
2. **API Endpoints** — Button per endpoint that fires the request and shows the JSON response (pretty-printed in a `<pre>` block)
3. **WebSocket** — Connection status indicator (green/red dot), live feed of incoming messages
4. **System Summary** — Account equity, position count, health status (from API responses)

This page proves the full stack works. It's replaced by the real dashboard in Sprint 15 but remains accessible at `/dev/connection` for debugging.

**`src/App.tsx`:**
```typescript
// React Router setup:
// /login — Login page
// / — Protected route → ConnectionTest (Sprint 14), Dashboard (Sprint 15)
// /dev/connection — Always-accessible ConnectionTest page
```

---

## 6. Test Plan

### 6.1 Test Fixtures (`tests/api/conftest.py`)

```python
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from argus.api.server import create_app
from argus.api.dependencies import AppState
# ... import mocks for each component ...


@pytest.fixture
def api_config():
    """ApiConfig with test values."""
    return ApiConfig(
        password_hash=bcrypt.hash("testpassword123"),
        jwt_secret_env="ARGUS_JWT_SECRET",
        cors_origins=["*"],
    )


@pytest.fixture
def jwt_secret(monkeypatch):
    """Set JWT secret environment variable."""
    monkeypatch.setenv("ARGUS_JWT_SECRET", "test-secret-key-for-jwt-signing")
    return "test-secret-key-for-jwt-signing"


@pytest_asyncio.fixture
async def app_state(api_config, ...):
    """Create AppState with mock/test components."""
    # Use real EventBus (lightweight)
    # Use real TradeLogger with in-memory SQLite (":memory:" or tmp file)
    # Use SimulatedBroker
    # Use real HealthMonitor
    # Use real RiskManager (default config)
    # Seed trade_logger with sample trades
    ...


@pytest_asyncio.fixture
async def client(app_state):
    """HTTP test client."""
    app = create_app(app_state)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def auth_headers(jwt_secret, api_config):
    """Valid Authorization headers for authenticated requests."""
    from argus.api.auth import create_access_token
    token, _ = create_access_token(jwt_secret)
    return {"Authorization": f"Bearer {token}"}
```

### 6.2 Test Breakdown

**`test_auth.py` (~10 tests):**
- `test_login_success` — valid password → 200 + token
- `test_login_wrong_password` — → 401
- `test_login_empty_password` — → 401 or 422
- `test_token_valid_access` — use token → can hit /account
- `test_token_expired` — expired token → 401
- `test_token_invalid_signature` — wrong secret → 401
- `test_token_missing` — no auth header → 401/403
- `test_refresh_success` — valid token → new token with extended expiry
- `test_refresh_expired_token` — expired token → 401
- `test_setup_password_cli` — test the hash generation function (unit test, not HTTP)

**`test_account.py` (~5 tests):**
- `test_get_account_success` — returns expected shape with correct values from mock broker
- `test_account_includes_daily_pnl` — daily P&L computed from trade logger
- `test_account_market_status_open` — during market hours returns "open"
- `test_account_market_status_closed` — outside market hours returns "closed"
- `test_account_unauthenticated` — → 401

**`test_positions.py` (~8 tests):**
- `test_get_positions_empty` — no positions → empty list
- `test_get_positions_with_data` — mock positions → correct enrichment (unrealized P&L, R-multiple)
- `test_positions_filter_by_strategy` — strategy_id param filters correctly
- `test_positions_computed_fields` — unrealized_pnl, pnl_pct, hold_duration, r_multiple all correct
- `test_positions_t1_filled_reflected` — t1_filled status shown
- `test_positions_multiple_strategies` — positions from different strategies returned
- `test_positions_current_price_failure` — if data service returns None/error, handle gracefully
- `test_positions_unauthenticated` — → 401

**`test_trades.py` (~10 tests):**
- `test_get_trades_default` — returns most recent 50 trades
- `test_trades_pagination` — limit + offset work correctly
- `test_trades_filter_by_strategy` — strategy_id filter
- `test_trades_filter_by_date_range` — date_from + date_to
- `test_trades_filter_by_outcome` — win/loss/breakeven filters
- `test_trades_combined_filters` — strategy + date + outcome together
- `test_trades_empty_result` — no matching trades → empty list, total_count=0
- `test_trades_total_count` — total_count reflects unfiltered total (for pagination)
- `test_trades_sort_order` — most recent first
- `test_trades_unauthenticated` — → 401

**`test_performance.py` (~10 tests):**
- `test_performance_today` — period="today" returns today's metrics
- `test_performance_week` — period="week" returns week metrics
- `test_performance_month` — period="month" returns month metrics
- `test_performance_all` — period="all" returns all-time metrics
- `test_performance_invalid_period` — → 422
- `test_performance_empty_data` — no trades → zeroed metrics
- `test_performance_daily_pnl_array` — daily_pnl includes correct entries
- `test_performance_by_strategy` — by_strategy breakdown matches
- `test_performance_win_rate_calculation` — verify correctness
- `test_performance_profit_factor_no_losses` — profit_factor handles zero losses

**`test_health.py` (~5 tests):**
- `test_health_all_healthy` — all components healthy → status "healthy"
- `test_health_degraded_component` — one degraded → status "degraded"
- `test_health_uptime` — uptime_seconds approximately correct
- `test_health_paper_mode` — paper_mode flag matches config
- `test_health_unauthenticated` — → 401

**`test_strategies.py` (~5 tests):**
- `test_get_strategies_list` — returns all strategies with correct fields
- `test_strategies_config_summary` — config_summary includes key params
- `test_strategies_daily_metrics` — daily_pnl and trade_count_today populated
- `test_strategies_open_positions_count` — matches actual open positions
- `test_strategies_unauthenticated` — → 401

**`test_websocket.py` (~12 tests):**
- `test_ws_connect_valid_token` — connection accepted
- `test_ws_connect_invalid_token` — connection rejected with 4001
- `test_ws_connect_no_token` — connection rejected
- `test_ws_receive_position_opened` — publish PositionOpenedEvent → client receives position.opened
- `test_ws_receive_order_filled` — publish OrderFilledEvent → client receives order.filled
- `test_ws_tick_throttling` — publish 100 TickEvents rapidly → client receives ≤ 2 (throttled)
- `test_ws_tick_only_open_positions` — TickEvents for non-position symbols are filtered
- `test_ws_subscribe_filter` — client subscribes to subset → only gets those types
- `test_ws_unsubscribe` — unsubscribe from type → stops receiving
- `test_ws_ping_pong` — client sends ping → receives pong
- `test_ws_heartbeat` — server sends heartbeat on schedule (use short interval in test)
- `test_ws_multiple_clients` — two clients both receive events

**`test_server.py` (~5 tests):**
- `test_app_creation` — create_app returns FastAPI instance
- `test_cors_headers` — CORS headers present in response
- `test_api_prefix` — all routes under /api/v1
- `test_openapi_schema` — /docs and /openapi.json accessible
- `test_static_files_not_mounted_when_empty` — no static_dir → no static mount

**`tests/analytics/test_performance.py` (~10 tests):**
- `test_compute_metrics_empty_trades` — returns zeroed metrics
- `test_compute_metrics_all_wins` — 100% win rate, no losses
- `test_compute_metrics_all_losses` — 0% win rate
- `test_compute_metrics_mixed` — realistic mix
- `test_profit_factor_no_losses` — returns infinity or large number
- `test_sharpe_ratio_computation` — verify against known data
- `test_max_drawdown_computation` — verify against known equity curve
- `test_consecutive_wins_losses` — verify streak tracking
- `test_open_trades_excluded` — trades without exit_price are skipped
- `test_breakeven_classification` — pnl_dollars=0 classified correctly

**Total: ~80 tests**

---

## 7. Prompt Plan

Execute in this order. Each prompt should result in all tests passing before moving to next.

### Prompt 1: Config + Dependencies + Project Structure
- Add `fastapi`, `uvicorn`, `python-jose[cryptography]`, `passlib[bcrypt]`, `httpx` to dependencies
- Create `ApiConfig` Pydantic model, add to `SystemConfig`
- Update `config/system.yaml` with `api` section
- Create directory structure: `argus/api/`, `argus/api/routes/`, `argus/api/websocket/`
- Create all `__init__.py` files
- Run existing tests — zero regressions

### Prompt 2: Auth + Setup Password
- Implement `argus/api/auth.py` (JWT create/verify, password verify, auth dependency)
- Implement `argus/api/setup_password.py` CLI
- Implement `argus/api/routes/auth.py` (login + refresh endpoints)
- Create `tests/api/conftest.py` with shared fixtures
- Write `tests/api/test_auth.py` (~10 tests)
- All tests pass

### Prompt 3: AppState + Server Factory + Account Endpoint
- Implement `argus/api/dependencies.py` (AppState, get_app_state, set_app_state)
- Implement `argus/api/server.py` (create_app, run_server)
- Implement `argus/api/routes/account.py`
- Add `get_managed_positions()` public method to OrderManager
- Write `tests/api/test_account.py` (~5 tests)
- Write `tests/api/test_server.py` (~5 tests)
- All tests pass

### Prompt 4: Positions + Trades Endpoints
- Implement `argus/api/routes/positions.py`
- Add `query_trades()`, `count_trades()`, `get_daily_pnl()`, `get_todays_pnl()` to TradeLogger
- Implement `argus/api/routes/trades.py`
- Write `tests/api/test_positions.py` (~8 tests)
- Write `tests/api/test_trades.py` (~10 tests)
- All tests pass

### Prompt 5: Performance Calculator + Performance Endpoint
- Create `argus/analytics/performance.py` (extract from backtest/metrics.py)
- Refactor `backtest/metrics.py` to use shared PerformanceCalculator (no behavior change)
- Implement `argus/api/routes/performance.py`
- Write `tests/analytics/test_performance.py` (~10 tests)
- Write `tests/api/test_performance.py` (~10 tests)
- Run full test suite — verify backtest tests still pass (no regression from extraction)
- All tests pass

### Prompt 6: Health + Strategies Endpoints
- Add any needed public methods to HealthMonitor (`get_component_statuses()`, `get_overall_status()`)
- Implement `argus/api/routes/health.py`
- Implement `argus/api/routes/strategies.py`
- Write `tests/api/test_health.py` (~5 tests)
- Write `tests/api/test_strategies.py` (~5 tests)
- All tests pass

### Prompt 7: WebSocket Bridge
- Implement `argus/api/serializers.py`
- Implement `argus/api/websocket/live.py` (WebSocketBridge, ClientConnection, endpoint)
- Write `tests/api/test_websocket.py` (~12 tests)
- All tests pass

### Prompt 8: Dev State + main.py Integration
- Implement `argus/api/dev_state.py` (MockAppState with seeded data)
- Implement `argus/api/__main__.py` (standalone `--dev` runner)
- Add Phase 11 to `argus/main.py` (API server startup + shutdown)
- Update CLAUDE.md commands section with new API commands
- Full test suite passes
- Manual verification: `python -m argus.api.server --dev` → hit endpoints with curl

### Prompt 9: React Scaffolding
- Initialize Vite + React + TypeScript project in `argus/ui/`
- Configure Tailwind with ARGUS dark theme colors
- Create `src/api/types.ts`, `src/api/client.ts`, `src/api/ws.ts`
- Create Zustand stores (`auth.ts`, `live.ts`)
- Create `ProtectedRoute.tsx` component
- Create `Login.tsx` page
- Create `ConnectionTest.tsx` page
- Create `App.tsx` with routing
- Verify: `cd argus/ui && npm install && npm run build` succeeds
- Verify: `npm run dev` + `python -m argus.api.server --dev` → login → see ConnectionTest page with real data

### Prompt 10: Cleanup + Docs
- Run `ruff check` and fix any lint issues
- Run full test suite — confirm total count ~890–910
- Update `argus/api/__init__.py` and `argus/analytics/__init__.py` exports
- Add `node_modules/` and `argus/ui/dist/` to `.gitignore`
- Update CLAUDE.md: Current State, Commands, Components
- Update docs as needed (Architecture section 4 with implementation status)

---

## 8. Gate Check (Sprint Complete When)

- [ ] All ~890–910 tests pass (zero regressions from 811 baseline)
- [ ] `ruff check` clean
- [ ] `python -m argus.api.setup_password` generates valid bcrypt hash
- [ ] `python -m argus.api.server --dev` starts successfully
- [ ] All 7 REST endpoints return valid JSON with correct shape
- [ ] WebSocket connects, receives events, handles subscription filters
- [ ] `cd argus/ui && npm run build` succeeds
- [ ] Login → ConnectionTest page shows live data from dev server
- [ ] `python -m argus.main` still starts correctly (with `api.enabled: true`)
- [ ] Existing paper trading functionality unaffected (zero regressions)

---

## 9. Docs Update Checklist (Post-Sprint)

| Doc | Update |
|-----|--------|
| `05_DECISION_LOG.md` | Add DEC-099 through DEC-103 |
| `02_PROJECT_KNOWLEDGE.md` | Update "Current Project State" (Sprint 14 complete, test count), add DEC-099–103 to decisions |
| `03_ARCHITECTURE.md` | Update Section 4 (API Server) with implementation status, add ApiConfig to config section |
| `10_PHASE3_SPRINT_PLAN.md` | Move Sprint 14 to completed table |
| `CLAUDE.md` | Update Current State, add API commands, update components list |

# Sprint 14 — Cross-Cutting Contracts (Active During Sprint 14)

These are the shared interfaces and patterns that ALL Sprint 14 code must follow.
Violating these causes cascading test failures across prompts.

## AppState (argus/api/dependencies.py)
Fields: event_bus, trade_logger, broker, health_monitor, risk_manager,
order_manager, data_service, strategies (dict[str, BaseStrategy]), clock, config (SystemConfig), start_time (float)

Access in routes: `state: AppState = Depends(get_app_state)`

## Auth Pattern
All protected routes add: `_auth: dict = Depends(require_auth)`
Auth module: `argus.api.auth` exports `require_auth`, `verify_password`, `create_access_token`, `verify_token`
JWT algorithm: HS256. Secret from env var named in `config.api.jwt_secret_env`.
Token subject: "operator" (single user).

## Test Fixtures (tests/api/conftest.py)
- `api_config` — ApiConfig with password_hash for "testpassword123"
- `jwt_secret` — monkeypatches ARGUS_JWT_SECRET env var, returns the secret string
- `app_state` — async fixture, AppState with real EventBus, in-memory TradeLogger, SimulatedBroker
- `client` — async fixture, httpx.AsyncClient with ASGITransport wrapping create_app(app_state)
- `auth_headers` — dict: {"Authorization": "Bearer <valid_token>"}

## Route File Pattern
Each route file in argus/api/routes/ defines: `router = APIRouter()`
Routes aggregated in routes/__init__.py as `api_router`
All mounted under prefix `/api/v1` in server.py

## API Response Conventions
- All responses include `"timestamp"` field (ISO 8601 UTC)
- List responses include `"count"` field
- Paginated responses include `"total_count"`, `"limit"`, `"offset"`
- Error responses: `{"detail": "message"}`

## TradeLogger Query Methods (added in Sprint 14)
```python
async def query_trades(self, strategy_id=None, date_from=None, date_to=None, outcome=None, limit=50, offset=0) -> list[dict]
async def count_trades(self, strategy_id=None, date_from=None, date_to=None, outcome=None) -> int
async def get_daily_pnl(self, date_from=None, date_to=None) -> list[dict]
async def get_todays_pnl(self) -> float
```

## OrderManager Public Method (added in Sprint 14)
```python
def get_managed_positions(self) -> list[ManagedPosition]
```

## WebSocket Event Type Mapping
Internal Event → WS type string:
- PositionOpenedEvent → "position.opened"
- PositionClosedEvent → "position.closed"
- PositionUpdatedEvent → "position.updated"
- OrderSubmittedEvent → "order.submitted"
- OrderFilledEvent → "order.filled"
- OrderCancelledEvent → "order.cancelled"
- CircuitBreakerEvent → "system.circuit_breaker"
- HeartbeatEvent → "system.heartbeat"
- WatchlistEvent → "scanner.watchlist"
- SignalEvent → "strategy.signal"
- OrderApprovedEvent → "order.approved"
- OrderRejectedEvent → "order.rejected"
- TickEvent → "price.update" (throttled, position-filtered)

## WebSocket Message Format (server → client)
```json
{"type": "position.opened", "data": {...}, "sequence": 12345, "timestamp": "ISO8601"}
```

## PerformanceCalculator (argus/analytics/performance.py)
```python
@dataclass
class PerformanceMetrics:
    total_trades, wins, losses, breakeven, win_rate, profit_factor, net_pnl,
    gross_pnl, total_commissions, avg_r_multiple, sharpe_ratio, max_drawdown_pct,
    avg_hold_seconds, largest_win, largest_loss, consecutive_wins_max, consecutive_losses_max

def compute_metrics(trades: list[dict]) -> PerformanceMetrics
```

## Config
ApiConfig lives in argus/config/ (or wherever existing configs are).
Added to SystemConfig as `api: ApiConfig` with default `ApiConfig()`.
YAML section: `api:` in config/system.yaml.

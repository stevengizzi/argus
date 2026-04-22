# API Conventions — Command Center FastAPI

> Cross-cutting contracts for the `argus/api/` layer. These conventions began
> in Sprint 14 and have carried through every subsequent API-touching sprint
> (17, 20, 21–21.7, 22, 23.5–23.9, 24.1, 25–25.6, 27.5–27.9, 28, 31A.5, 32–32.9).
> This file is a crib sheet, not a spec — when it disagrees with the code,
> the code wins and this file should be updated.

## AppState Dependency Injection (DEC-100)

[AppState](argus/api/dependencies.py) is a dataclass attached to
`app.state.app_state` at startup. Routes depend on it via
`Depends(get_app_state)`:

```python
from fastapi import Depends
from argus.api.dependencies import AppState, get_app_state

@router.get("/positions")
async def get_positions(
    state: AppState = Depends(get_app_state),
    _auth: dict = Depends(require_auth),
) -> dict:
    ...
```

**AppState has grown from 11 fields (Sprint 14) to 30+ (Sprint 32.9).** Do
not enumerate the current field list here — it drifts every sprint. Read
[argus/api/dependencies.py](argus/api/dependencies.py) for the authoritative
definition. New subsystems (quality engine, counterfactual store,
experiment store, historical query service, learning service, etc.) are
added as `Optional[...] = None` fields with a `default=None` — route
handlers that depend on an optional subsystem MUST check for `None` and
raise `HTTPException(status_code=503)` with a clear detail message
(see `get_debrief_service()` in `dependencies.py` for the canonical
pattern).

## Auth Pattern (DEC-102)

- All protected routes add `_auth: dict = Depends(require_auth)`.
- Auth module: `argus.api.auth` exports `require_auth`, `verify_password`,
  `create_access_token`, `verify_token`.
- JWT algorithm: HS256. Secret is read from the env var named in
  `config.api.jwt_secret_env` (typically `ARGUS_JWT_SECRET`).
- Token subject: `"operator"` (single-user system).
- **`HTTPBearer(auto_error=False)` + explicit 401** (DEC-351, Sprint 25.8).
  Unauthenticated requests return 401 Unauthorized, not 403 Forbidden.

A small number of public routes are intentionally unauthenticated
(`GET /api/v1/market/status` is one — the frontend uses it for unauthenticated
boot checks). These do NOT add `require_auth` and are documented as such in
their route docstring.

## Route File Pattern

- Each route file in [argus/api/routes/](argus/api/routes/) defines
  `router = APIRouter()` at module scope.
- Routes aggregated in `routes/__init__.py` as `api_router`.
- All mounted under prefix `/api/v1` in [argus/api/server.py](argus/api/server.py).
- New route files should follow the existing shape — a top-level `router`,
  `Depends(get_app_state)` on all handlers that need state, `Depends(require_auth)`
  on all protected handlers, explicit response models.

## API Response Conventions

- All responses include a `"timestamp"` field (ISO 8601, UTC).
- List responses include a `"count"` field (length of the list).
- Paginated responses include `"total_count"`, `"limit"`, `"offset"`, and
  optionally a `"has_more"` boolean.
- Error responses follow FastAPI's default `{"detail": "message"}` shape.
- 5xx responses are reserved for server faults (optional dependencies
  unavailable, subsystem crash). 4xx is for client-side issues (auth,
  validation, not-found).

## WebSocket Conventions (DEC-101)

- Endpoints live under `/ws/v1/`. Current active endpoints include
  `/ws/v1/events` (curated event fan-out), `/ws/v1/arena` (6 Arena message
  types including `arena_tick_price` per Sprint 32.8), and
  `/ws/v1/observatory` (pipeline push per Sprint 25).
- Server → client frame:
  `{"type": "<event>", "data": {...}, "sequence": <int>, "timestamp": <ISO8601>}`.
- TickEvent → `price.update` is throttled per-symbol to 1 Hz for the
  generic events stream; Arena bypasses the throttle via `arena_tick_price`
  (Sprint 32.8). Do not revert the Arena bypass without understanding the
  operator latency rationale.
- Hook-driven Vitest tests that render components depending on these WS
  endpoints MUST mock the hook — see `testing.md` § Vitest.

## TradeLogger Query Surface

[argus/analytics/trade_logger.py](argus/analytics/trade_logger.py) is the
sole persistence interface for trades (DEC-034). Representative public
methods on `TradeLogger`:

```python
async def query_trades(
    self,
    strategy_id: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    outcome: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[dict]: ...
async def count_trades(...) -> int: ...
async def get_daily_pnl(...) -> list[dict]: ...
async def get_todays_pnl(self) -> float: ...
async def get_todays_trade_count(self) -> int: ...
async def get_daily_summary(self, date: str) -> dict: ...
async def compute_metrics(trades: list[dict]) -> PerformanceMetrics: ...
```

Additional query-stats surface was added in Sprint 28.75 via
`GET /api/v1/trades/stats` (DEF-117 resolution) — server-side computation
replaces client-side aggregation from paginated subsets.

## OrderManager Query Surface

```python
def get_managed_positions(self) -> dict[str, list[ManagedPosition]]: ...
async def close_position(self, symbol: str, reason: str = "api_close") -> bool: ...   # DEC-352, Sprint 25.8
```

Routes that expose position-close functionality MUST route through
`OrderManager.close_position()` — never issue a raw broker call. DEF-085
(Sprint 25.8 close-position regression) root-caused to a route bypassing
the manager.

## PerformanceCalculator

[argus/analytics/performance.py](argus/analytics/performance.py):

```python
@dataclass
class PerformanceMetrics:
    total_trades: int
    wins: int
    losses: int
    breakeven: int
    win_rate: float
    profit_factor: float
    net_pnl: float
    gross_pnl: float
    total_commissions: float
    avg_r_multiple: float
    sharpe_ratio: float
    max_drawdown_pct: float
    avg_hold_seconds: float
    largest_win: float
    largest_loss: float
    consecutive_wins_max: int
    consecutive_losses_max: int

def compute_metrics(trades: list[dict]) -> PerformanceMetrics: ...
```

## Test Fixtures

`tests/api/conftest.py` defines the canonical fixtures:
- `api_config` — `ApiConfig` with `password_hash` for "testpassword123".
- `jwt_secret` — monkeypatches `ARGUS_JWT_SECRET`, yields the secret string.
- `app_state` — async fixture, `AppState` with real `EventBus`, in-memory
  `TradeLogger`, `SimulatedBroker`. Newer optional subsystems default to
  `None`; tests that need them wire them up explicitly.
- `client` — async fixture, `httpx.AsyncClient` with `ASGITransport` over
  `create_app(app_state)`.
- `auth_headers` — `{"Authorization": "Bearer <valid_token>"}`.

New route tests should reuse these fixtures rather than constructing
alternatives.

## Config

`ApiConfig` lives in [argus/core/config.py](argus/core/config.py) (alongside
the rest of the Pydantic config models). `SystemConfig.api: ApiConfig =
Field(default_factory=ApiConfig)`. The YAML section is `api:` in
`config/system.yaml` / `config/system_live.yaml`.

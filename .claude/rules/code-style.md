# Code Style Rules

## Python Style

Follow PEP 8 with these project-specific additions.

**Target Python: 3.11+** (per `pyproject.toml`). Rely on the stdlib:
`ZoneInfo`, `StrEnum`, PEP 604 unions (`X | None`), built-in parameterized
generics (`list[int]`, `dict[str, Any]`). Do NOT import `List`, `Dict`,
`Optional` from `typing` for types the language already supplies.

**Filesystem paths:** use `pathlib.Path`, not `os.path`. This is a project
rule — CLAUDE.md repeats it under "Code Style." Mixing `pathlib` and
`os.path` in the same module is a code-review flag.

### Type Hints
Every function must have complete type hints. No exceptions.

```python
# CORRECT
async def calculate_position_size(self, entry_price: float, stop_price: float) -> int:

# WRONG — missing return type
async def calculate_position_size(self, entry_price: float, stop_price: float):

# WRONG — missing parameter types
async def calculate_position_size(self, entry_price, stop_price) -> int:
```

### Docstrings (Google Style)
All public classes and methods require docstrings.

```python
async def evaluate_signal(self, signal: SignalEvent) -> OrderApprovedEvent | OrderRejectedEvent:
    """Evaluate a trade signal against all three risk levels.

    Runs the signal through strategy-level, cross-strategy, and account-level
    risk checks. Returns approved (possibly with modifications) or rejected.

    Args:
        signal: The trade signal from a strategy.

    Returns:
        OrderApprovedEvent if the signal passes all risk gates,
        OrderRejectedEvent with reason if it fails any gate.

    Raises:
        CircuitBreakerError: If account-level circuit breaker is active.
    """
```

### Data Structures
Use dataclasses or Pydantic models for all structured data. Never pass raw dicts between components.

```python
# CORRECT
@dataclass
class SignalEvent:
    strategy_id: str
    symbol: str
    side: str
    entry_price: float
    stop_price: float
    target_prices: list[float]
    share_count: int
    rationale: str

# WRONG — raw dict
signal = {"strategy_id": "orb", "symbol": "AAPL", "entry": 150.0}
```

### Enums for Fixed Value Sets
Use enums, not string literals, for values that have a fixed set of options.
Example pattern (the canonical `ExitReason` in
[argus/core/events.py](argus/core/events.py) has ~12 members including
`RECONCILIATION` (DEC-371) and `TRAILING_STOP`; keep the illustrative form
short):

```python
class ExitReason(str, Enum):
    TARGET_1 = "target_1"
    TARGET_2 = "target_2"
    STOP_LOSS = "stop_loss"
    TIME_STOP = "time_stop"
    END_OF_DAY = "eod"
    TRAILING_STOP = "trailing_stop"
    RECONCILIATION = "reconciliation"
    MANUAL = "manual"
    CIRCUIT_BREAKER = "circuit_breaker"
```

### Error Handling
- Use custom exception classes for domain errors, not generic Exception
- Never silently swallow exceptions — always log at minimum
- Broker and data service calls must have try/except with proper error handling and logging

### Serialization (DEF-151)

When serializing a dataclass or Pydantic model via `json.dumps`, always pass
`default=str` if the object *might* contain `datetime`, `date`, `Decimal`, or
any other type `json` does not natively handle:

```python
# CORRECT — date/datetime fields serialize to ISO strings
json.dumps(record.to_dict(), default=str)

# WRONG — raises TypeError if record contains any datetime
json.dumps(record.to_dict())
```

DEF-151 (Sprint 31.5 ExperimentStore) silently lost 143 sweep grid points
when `record.backtest_result` contained `datetime.date` fields from
`MultiObjectiveResult.to_dict()`. The `json.dumps()` call raised, the
fire-and-forget write path swallowed the exception, and the rows never
reached `experiments.db`. Any new write path that serializes a structured
object MUST include a round-trip test that confirms the serialized form
re-parses cleanly.

### Logging
- Use Python's logging module, not print statements
- Logger per module: `logger = logging.getLogger(__name__)`
- Log levels: DEBUG for verbose tracing, INFO for normal operations, WARNING for recoverable issues, ERROR for failures, CRITICAL for system-threatening events
- Every trade action (signal, approval, rejection, fill, close) must be logged at INFO level

### ThrottledLogger for High-Volume Logs (Sprint 27.75, DEC-363)

Any log line that can fire more than ~1× per second in normal operation
MUST use [argus/utils/throttled_logger.py](argus/utils/throttled_logger.py)
with a per-key suppression window. The pattern:

```python
from argus.utils.throttled_logger import ThrottledLogger

_throttled = ThrottledLogger(logger, suppression_seconds=60)
_throttled.warning(f"flatten already pending for {symbol}", key=symbol)
```

Known high-volume sites (all mitigated): IBKR error 399 repricing spam
(DEF-100), "flatten already pending" retries (DEF-113), "IBKR portfolio
snapshot missing" (DEF-114). When adding a new log line that could ever
fire inside a per-tick or per-order callback loop, default to throttled
first; downgrade to an unthrottled `logger` call only after you've
measured the rate.

Fire-and-forget DB write failures (`EvaluationEventStore`,
`CounterfactualStore`, etc.) are the canonical use case: the failure must
surface, but a broken DB cannot be allowed to flood the log.

## Time and Timezones (DEC-061, DEC-276)

- **ET is canonical for market-session reasoning.** Any code that compares
  the current time to a market hour (open, close, pre-EOD cutoff, ORB
  window) MUST convert UTC timestamps to ET first using
  `timestamp.astimezone(ZoneInfo("America/New_York"))`. Never compare
  `.timestamp.time()` directly against ET constants like `time(9, 30)` —
  that path silently misbehaves around DST and was DEC-061's bug.
- **UTC is canonical for inter-system comms.** HTTP response timestamps,
  database `created_at` audit fields, event-bus sequence timestamps, and
  anything serialized to JSON for another system uses `datetime.now(UTC)`.
- **Canonical import:** `from zoneinfo import ZoneInfo` (stdlib, Python 3.9+);
  `ZoneInfo("America/New_York")` resolves DST correctly. Do not use
  `pytz`, do not hardcode "EST" strings.
- **AI layer (DEC-276):** user-facing chat timestamps and conversation
  audit trails are ET — operator reads them in their trading timezone.

### Static Analysis (Pylance)

All code must be clean under Pylance's default type checking mode. No new
Pylance errors should be introduced in any session. Specifically:

- **Use parameterized generics:** `dict[str, Any]`, `list[str]`, not bare `dict`, `list`
- **Use typed row objects:** When working with `aiosqlite`, type rows as
  `aiosqlite.Row`, not `object`. Extract a `_row_to_dict()` helper method for
  `dict(row)` conversions to centralize the single necessary `# type: ignore`
- **Narrow optional types before use:** Use `assert x is not None` or
  `if x is not None:` guards before accessing attributes on optional values.
  Do not scatter `# type: ignore[union-attr]` comments
- **`# type: ignore` is a last resort:** Only use when the type system genuinely
  cannot express the correct type (e.g., third-party library typing gaps like
  `alpaca-py`'s `TimeFrame.Minute`). Each `# type: ignore` must include the
  specific error code (e.g., `# type: ignore[arg-type]`) and should be
  accompanied by a brief comment explaining why
- **Import types for annotations:** Use `from typing import Any` and
  `from __future__ import annotations` where appropriate. Use `TYPE_CHECKING`
  blocks for imports only needed by type checkers
- **Return types must match:** If a config field is `int | None`, the property
  exposing it must also return `int | None`, not `int`

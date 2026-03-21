# Code Style Rules

## Python Style

Follow PEP 8 with these project-specific additions:

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

```python
class ExitReason(str, Enum):
    TARGET_1 = "target_1"
    TARGET_2 = "target_2"
    STOP_LOSS = "stop_loss"
    TIME_STOP = "time_stop"
    END_OF_DAY = "eod"
    MANUAL = "manual"
    CIRCUIT_BREAKER = "circuit_breaker"
```

### Error Handling
- Use custom exception classes for domain errors, not generic Exception
- Never silently swallow exceptions — always log at minimum
- Broker and data service calls must have try/except with proper error handling and logging

### Logging
- Use Python's logging module, not print statements
- Logger per module: `logger = logging.getLogger(__name__)`
- Log levels: DEBUG for verbose tracing, INFO for normal operations, WARNING for recoverable issues, ERROR for failures, CRITICAL for system-threatening events
- Every trade action (signal, approval, rejection, fill, close) must be logged at INFO level

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
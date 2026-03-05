# Sprint 1 Cleanup — Pre-Sprint 2

Sprint 1 is complete and all 52 tests pass. Before starting Sprint 2, there are four cleanup items to address. Do them in order, run tests after each, and commit everything as a single cleanup commit at the end.

---

## Task 1: Verify Schema Table Count

The Architecture doc specifies 7 tables: `trades`, `strategy_daily_performance`, `account_daily_snapshot`, `orchestrator_decisions`, `approval_log`, `journal_entries`, `system_health`.

Check what's actually in `argus/db/schema.sql`. If any of the 7 are missing:
- If `system_health` is missing, that's fine — it's a Step 10 concern, add a comment noting it's deferred
- If any other table is missing, add it per the schema in `docs/03_ARCHITECTURE.md` Section 3.8

Report which tables are present.

---

## Task 2: Remove Unused `pydantic-settings` Dependency

Run: `grep -r "pydantic_settings" argus/ tests/`

If nothing imports from `pydantic_settings`, remove the `pydantic-settings>=2.1,<3` line from the `dependencies` list in `pyproject.toml`. Then run `pip install -e ".[dev]"` to verify the install still succeeds.

---

## Task 3: Consolidate Test Fixtures in conftest.py

The shared `conftest.py` at `tests/conftest.py` currently only has `config` and `fixtures_dir` fixtures. Add the following shared fixtures that Sprint 2+ tests will need:

```python
from argus.core.event_bus import EventBus
from argus.db.manager import DatabaseManager
from argus.analytics.trade_logger import TradeLogger

@pytest.fixture
def bus() -> EventBus:
    """Provide a fresh EventBus."""
    return EventBus()

@pytest.fixture
async def db(tmp_path) -> DatabaseManager:
    """Provide an initialized DatabaseManager with a temp database."""
    manager = DatabaseManager(tmp_path / "argus_test.db")
    await manager.initialize()
    yield manager
    await manager.close()

@pytest.fixture
async def trade_logger(db: DatabaseManager) -> TradeLogger:
    """Provide a TradeLogger backed by a temp database."""
    return TradeLogger(db)
```

Then refactor the existing Step 3 test files (`tests/db/test_manager.py`, `tests/analytics/test_trade_logger.py`, and `tests/models/test_trading.py`) to use these shared fixtures instead of defining their own local versions. Remove any duplicate fixture definitions from individual test files.

Make sure imports are clean and `ruff check` passes after the refactor.

---

## Task 4: Final Verification

Run the full suite:

```bash
ruff check argus/ tests/
pytest tests/ -v
```

All tests must pass, ruff must be clean.

---

## Commit

Once all four tasks are done and tests pass:

```bash
git add -A
git commit -m "chore: Sprint 1 cleanup — consolidate fixtures, remove unused dep, verify schema"
git push
```

---

## CLAUDE.md Update

Update the "Current State" section in CLAUDE.md to:

```
## Current State

Phase 1 — Sprint 1 complete. Config system, Event Bus, database layer, and Trade Logger are built and tested (52 tests). Currently preparing for Sprint 2 (Broker Abstraction + Risk Manager).

Update this section as development progresses.
```

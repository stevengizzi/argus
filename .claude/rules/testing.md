# Testing Rules

## Test Structure

Mirror the source tree:
```
argus/core/risk_manager.py    → tests/core/test_risk_manager.py
argus/strategies/orb.py       → tests/strategies/test_orb.py
argus/execution/broker.py     → tests/execution/test_broker.py
```

## Naming

Test functions describe behavior and expected outcome:
```python
# CORRECT
def test_signal_exceeding_daily_loss_limit_is_rejected():
def test_orb_entry_requires_volume_above_threshold():
def test_emergency_flatten_closes_all_positions():

# WRONG — vague
def test_risk_manager():
def test_orb():
def test_flatten():
```

## What Must Be Tested

### Safety-Critical (>95% coverage required)
- Risk Manager: every approval path, every rejection path, every circuit breaker condition
- Order Manager: every state transition, emergency flatten, EOD flatten
- Position Sizing: every invariant (see risk-rules.md)

### Core Logic (>90% coverage required)
- Strategy entry/exit logic (each criterion individually and in combination)
- Orchestrator allocation calculations
- Data Service candle building and indicator calculations

### Integration Tests
- Full signal-to-fill pipeline with SimulatedBroker
- Full backtest replay of a known historical period with expected results
- Risk Manager correctly blocks orders that violate cross-strategy limits

## Mocking

- Mock broker APIs in unit tests (never hit real Alpaca/IBKR in tests)
- Mock data feeds with deterministic historical data
- Use SimulatedBroker and ReplayDataService for integration tests
- Never mock the Risk Manager in integration tests — it must run for real

## Running Tests

Always run the full test suite before committing:
```
python -m pytest tests/ -x --tb=short
```

Run specific test files during development:
```
python -m pytest tests/core/test_risk_manager.py -v
```

## Test Execution in Claude Code Sessions

**Never pipe test output through `tail` or `head` for long-running suites.**
When pytest runs with `-n auto` (xdist), all output is buffered until every
worker finishes. If any test hangs, the pipe blocks forever and the session
appears stuck. Instead:
```bash
# WRONG — buffers forever if any test hangs
python -m pytest tests/ -n auto -q | tail -30

# CORRECT — write to file, check progress independently
python -m pytest tests/ -n auto -q 2>&1 | tee /tmp/pytest_output.txt

# CORRECT — write to file, read when done
python -m pytest tests/ -n auto -q > /tmp/pytest_output.txt 2>&1
cat /tmp/pytest_output.txt
```

**Standard test commands:**
```bash
# Full suite (use for sprint entry, closeouts, and final reviews):
python -m pytest --ignore=tests/test_main.py -n auto -q

# Scoped (use for mid-sprint pre-flights and development):
python -m pytest tests/core/test_orchestrator.py -x -q
```

Expected full suite runtime: ~39s with `-n auto`, ~208s sequential.
Only `tests/test_main.py` needs ignoring (DEF-048 xdist issue).

**When a test run appears stuck or output stops mid-way:**
Do NOT launch a second pytest process. Instead:
1. Check whether the original process is still running: `pgrep -fl pytest`
2. Identify the hanging test — the last `PASSED` line in the output is the test before the culprit
3. Kill all pytest processes before relaunching: `pkill -f pytest && sleep 2`
4. Fix the hanging test, then rerun

Accumulating multiple pytest processes from repeated relaunches degrades system
performance, produces confusing partial output, and can corrupt the timing of
subsequent full-suite runs. Kill first, diagnose second, relaunch third.

**Tests that use real `asyncio.sleep` are wall-clock-bound.**
Tests that await real time (e.g., poll loop integration tests with 1s intervals)
cannot be made faster by xdist parallelism — each one occupies a worker for its
full duration. When writing such tests, document the expected wall-clock cost in
a comment and set the test timeout expectation accordingly. If a test needs more
than ~3s of real sleep, reconsider whether it can be tested at a lower level
(e.g., testing the reset logic directly rather than through the poll loop).
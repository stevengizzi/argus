# Testing Rules

## Test Structure

Mirror the source tree:
```
argus/core/risk_manager.py    → tests/core/test_risk_manager.py
argus/strategies/orb.py       → tests/strategies/test_orb.py
argus/execution/broker.py     → tests/execution/test_broker.py
```

## Test Organization Style

Either class-based (`class TestFoo: def test_bar(self): ...`) or
function-based (`def test_bar(): ...`) organization is acceptable. The
suite currently mixes both. New tests should align with the file's
existing style; do not bulk-rewrite files to convert between styles.

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

## Non-Bypassable Validation (grep-guards)

Any validation step described in `risk-rules.md` / `architecture.md` as
non-bypassable MUST be paired with a grep-guard test that asserts no bypass
flag exists in the implementation. Canonical example:
`tests/scripts/test_consolidate_parquet_cache.py::test_no_bypass_flag_exists`.
The test reads the implementation file and fails if a string like
`--skip-validation`, `--force`, or a swallow-and-continue `except` block
appears around the validation site. Adding a new validated transform → add
the grep-guard at the same time.

## Test Baseline Invariant

Every code-modifying session must end with the pytest pass count **greater
than or equal to** the pre-session baseline. This is enforced by the
Phase 3 audit runner and by the close-out skill's regression checklist.

Exceptions:
- Removing a pre-existing failing test (DEF-cited) is allowed. Flag the
  removal in the close-out report with the DEF reference.
- Deliberately deleting a test whose behavior has been moved to a different
  test file is allowed; net count must still be ≥ 0 across the rename.

Never delete a passing test to make a refactor "easier." If a refactor
breaks a test, the test captures intended behavior — fix the refactor or
rewrite the test to match the new intent.

## Running Tests

**Standard commands:**
```bash
# Full suite (sprint entry, closeouts, final review):
python -m pytest --ignore=tests/test_main.py -n auto -q

# Scoped (mid-sprint pre-flights and development):
python -m pytest tests/core/test_orchestrator.py -x -q

# Single file:
python -m pytest tests/core/test_risk_manager.py -v
```

Expected full-suite runtime: ~39s with `-n auto`, ~208s sequential.
Only `tests/test_main.py` needs ignoring (DEF-048 xdist issue with
`load_dotenv`/`AIConfig` race).

xdist tiering is codified in DEC-328 (Sprint 23.8): full suite at sprint
entry, closeouts, and final review; scoped tests during development. Do not
run the full suite on every save — it churns CI cycles and doesn't add
signal over a scoped run.

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

**When a test run appears stuck or output stops mid-way:**
Do NOT launch a second pytest process. Instead:
1. Check whether the original process is still running: `pgrep -fl pytest`
2. Identify the hanging test — the last `PASSED` line in the output is the test before the culprit
3. Kill all pytest processes before relaunching: `pkill -f pytest && sleep 2`
4. Fix the hanging test, then rerun

Accumulating multiple pytest processes from repeated relaunches degrades system
performance, produces confusing partial output, and can corrupt the timing of
subsequent full-suite runs. Kill first, diagnose second, relaunch third.
(Universal RULE-037.)

**Tests that use real `asyncio.sleep` are wall-clock-bound.**
Tests that await real time (e.g., poll loop integration tests with 1s intervals)
cannot be made faster by xdist parallelism — each one occupies a worker for its
full duration. When writing such tests, document the expected wall-clock cost in
a comment and set the test timeout expectation accordingly. If a test needs more
than ~3s of real sleep, reconsider whether it can be tested at a lower level
(e.g., testing the reset logic directly rather than through the poll loop).

## Vitest (Frontend Tests)

`cd argus/ui && npx vitest run` — ~846 tests, runs in seconds.

### Unmocked WebSocket / hook hangs (DEF-138, Sprint 32.8)

React hooks that open real WebSockets (e.g., `useArenaWebSocket`) will hang
Vitest fork workers when rendered inside `jsdom` without a mock. The fix is
always the same:

```ts
// At the top of the test file, before any render:
vi.mock('@/features/arena/useArenaWebSocket', () => ({
  useArenaWebSocket: () => ({ connected: true, trades: [], ... }),
}))
```

As a safety net for any hook that slips through:

```ts
// vitest.config.ts
export default defineConfig({
  test: {
    testTimeout: 10_000,
    hookTimeout: 10_000,
  },
})
```

Sprint 32.8's `ArenaPage.test.tsx` is the canonical fix.

### Hardcoded dates

Do not embed absolute dates (`"2026-03-25"`) in Vitest assertions. Either
use `vi.useFakeTimers()` with `vi.setSystemTime()` or compute relative to
`new Date()`. See DEF-163 for the class of bug this pattern causes.

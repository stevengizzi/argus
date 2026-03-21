# Sprint 25.7 (Impromptu): Post-Session Operational Fixes + Debrief Export

## Pre-Flight Checks

Before making any changes:

1. Read these files to load context:
   - `CLAUDE.md`
   - `docs/protocols/market-session-debrief.md` (the full debrief protocol — this
     defines exactly what queries the debrief export must run)
   - `argus/execution/ibkr_broker.py` (focus on `get_account()`, `get_positions()`)
   - `argus/data/databento_data_service.py` (focus on `_dispatch_record()`, `fetch_daily_bars()`)
   - `argus/data/fmp_reference.py` (focus on API call pattern, session handling, base URL)
   - `argus/main.py` (focus on `_process_signal()` ~line 861 and `shutdown()` ~line 1104)
   - `argus/core/orchestrator.py` (focus on `run_pre_market()` and `reclassify_regime()`)
   - `argus/core/throttle.py` (focus on `PerformanceThrottler.check()`)
   - `argus/intelligence/position_sizer.py` (focus on `calculate_shares()`)
   - `argus/api/routes/health.py` (focus on `last_data_received`)
   - `argus/strategies/orb_base.py` (focus on `_check_breakout_conditions()` ~line 370
     and all `ENTRY_EVALUATION` recording calls)

2. Run the test baseline (DEC-328 — full suite, first session):
   ```bash
   python -m pytest --ignore=tests/test_main.py -n auto -q
   ```
   Expected: ~2,794 tests, all passing (tolerance: 50)

3. Verify you are on branch: `main`

4. Verify IB Gateway is running:
   ```bash
   nc -z 127.0.0.1 4002 && echo "IB Gateway reachable" || echo "NOT running — STOP"
   ```
   If NOT running: stop and report. The operator must start IB Gateway first.

## Objective

Resolve 6 operational issues discovered during the March 20 session debrief,
enrich entry evaluation telemetry metadata, and build an automated debrief data
export into the shutdown sequence so that future debriefs have full database
access.

## Requirements

### 0. Flatten orphaned IBKR paper account positions

Write and run a one-time script that:

1. Connects to IB Gateway (127.0.0.1:4002, **clientId=99** to avoid conflicting
   with ARGUS which uses clientId=1)
2. Fetches all current positions
3. For each position, places a market order to close it:
   - Short positions (qty < 0): BUY to cover
   - Long positions (qty > 0): SELL
4. Waits up to 30 seconds per order for fill confirmation
5. After all closes, fetches and prints the updated account summary:
   - `NetLiquidation`, `BuyingPower`, `AvailableFunds`, `GrossPositionValue`
6. Verifies: `BuyingPower > 0` and `positions == 0`
7. Disconnects cleanly

Use `ib_async` (already installed). Run this as a standalone script, NOT through
ARGUS. Print clear output showing each position closed and final account state.

**Safety:** Only run on paper accounts (account ID starts with `DU`). Abort if
the account prefix is not `DU`.

After verifying the account is clean, **delete the script** — this is a one-time
operation.

### 1. Implement `fetch_daily_bars()` via FMP (DEF-075, DEC-347)

**File:** `argus/data/databento_data_service.py`

Replace the stub `fetch_daily_bars()` method (currently returns `None`) with a
real implementation that fetches daily OHLCV bars from FMP's stable API.

**FMP endpoint:** `GET https://financialmodelingprep.com/stable/historical-price-eod/full`
- Query params: `symbol={symbol}`, `apikey={FMP_API_KEY}`
- Returns: JSON array of objects with `date`, `open`, `high`, `low`, `close`,
  `volume`, etc. Sorted newest-first by default.
- Available on Starter plan ($22/mo, already active via `FMP_API_KEY` env var).

Implementation details:
- Use `aiohttp.ClientSession` with `aiohttp.ClientTimeout(total=10)` for the request
- Read API key from `os.getenv("FMP_API_KEY")`
- If API key is not set, log a warning and return `None` (graceful degradation)
- Parse response JSON into a `pd.DataFrame` with columns: `date`, `open`, `high`,
  `low`, `close`, `volume`
- Sort by `date` ascending (FMP returns newest first)
- Limit to `lookback_days` most recent rows
- Return `None` on any error (timeout, HTTP error, malformed JSON, empty response)
- Log at INFO level: success with row count, or failure with reason
- This is called once at startup and once every 5 minutes — NOT hot path, no
  rate-limit concern
- Must not affect backtesting: the `BrokerSource.SIMULATED` path in the Orchestrator
  never calls `fetch_daily_bars()`, so no guard needed

### 2. Fix health endpoint `last_data_received` (DEF-076)

**File:** `argus/data/databento_data_service.py`

The health endpoint at `/api/v1/health` reads
`getattr(state.data_service, "last_update", None)` but `DatabentoDataService`
has no such attribute. Add it.

- In `__init__`, after `self._stale_published = False`, add:
  ```python
  self.last_update: datetime | None = None
  ```
- In `_dispatch_record()`, after `self._last_message_time = time.monotonic()`, add:
  ```python
  self.last_update = datetime.now(UTC)
  ```
- Ensure `from datetime import UTC, datetime` is in the file's imports (it may
  already be — check before adding).

### 3. Add diagnostic logging when sizer returns 0 (DEF-077)

**File:** `argus/main.py`

In `_process_signal()`, the block that logs "Signal skipped: ... sizer returned 0
shares" currently provides no diagnostic context. Replace it with a more
informative message.

Find the block (~line 940):
```python
if shares <= 0:
    logger.info(
        "Signal skipped: %s %s sizer returned 0 shares",
        signal.symbol,
        signal.strategy_id,
    )
```

Replace with:
```python
if shares <= 0:
    logger.info(
        "Signal skipped: %s %s sizer returned 0 shares "
        "(grade=%s, score=%.0f, allocated_capital=%.2f, "
        "buying_power=%.2f, entry=%.2f, stop=%.2f, risk_per_share=%.4f)",
        signal.symbol,
        signal.strategy_id,
        quality.grade,
        quality.score,
        strategy.allocated_capital,
        account.buying_power if account else 0.0,
        signal.entry_price,
        signal.stop_price,
        abs(signal.entry_price - signal.stop_price),
    )
```

### 4. Rate-limit regime reclassification warnings (DEF-078)

**File:** `argus/core/orchestrator.py`

The `reclassify_regime()` method logs "SPY data unavailable" every 5 minutes,
producing 76 identical warnings per session. Rate-limit to log on first
occurrence, then every 6th occurrence (every ~30 minutes).

In `__init__`, add:
```python
self._spy_unavailable_count: int = 0
```

In `reclassify_regime()`, replace:
```python
logger.warning(
    "Regime reclassification: SPY data unavailable, retaining %s",
    self._current_regime.value,
)
```

With:
```python
self._spy_unavailable_count += 1
if self._spy_unavailable_count <= 1 or self._spy_unavailable_count % 6 == 0:
    logger.warning(
        "Regime reclassification: SPY data unavailable, retaining %s (occurrence #%d)",
        self._current_regime.value,
        self._spy_unavailable_count,
    )
```

Also in `run_pre_market()`, apply the same pattern to the similar warning:
```python
logger.warning(
    "SPY data unavailable — using previous regime: %s",
    self._current_regime.value,
)
```

Reset the counter on success: when `spy_bars` IS valid and regime classification
succeeds, add `self._spy_unavailable_count = 0`.

### 5. Automated debrief data export at shutdown (DEF-079)

**New file:** `argus/analytics/debrief_export.py`
**Modified file:** `argus/main.py` (shutdown sequence)

Build a debrief data export that runs automatically during the shutdown sequence,
producing a `logs/debrief_YYYYMMDD.json` file containing everything the market
session debrief protocol (at `docs/protocols/market-session-debrief.md`) needs
from the databases.

**Read the debrief protocol first** — it defines the exact queries. The export
must cover Phases 4, 5, and account state.

#### 5a. Create `argus/analytics/debrief_export.py`

A single async function:

```python
async def export_debrief_data(
    session_date: str,          # "2026-03-20" (ET date)
    db: DatabaseManager,        # argus.db — open connection
    eval_store: EvaluationEventStore | None,  # evaluation.db — may be None
    catalyst_db_path: str | None,  # path to catalyst.db (separate connection)
    broker: Broker | None,      # for account state
    orchestrator: Orchestrator | None,  # for regime/allocation state
    output_dir: str = "logs",   # where to write the file
) -> str | None:                # returns filepath on success, None on failure
```

The function queries all three databases and the broker, then writes a single
JSON file to `{output_dir}/debrief_{session_date}.json`.

**JSON structure:**

```json
{
  "session_date": "2026-03-20",
  "exported_at": "2026-03-20T19:53:03+00:00",

  "orchestrator_decisions": [
    {"decision_type": "...", "strategy_id": "...", "details": "...", "rationale": "...", "created_at": "..."}
  ],

  "evaluation_summary": {
    "total_events": 12847,
    "by_strategy": {"strat_orb_breakout": {"count": 4230, "distinct_symbols": 1842}},
    "by_event_type_result": [{"event_type": "...", "result": "...", "count": 999}],
    "entry_evaluations": [
      {"symbol": "...", "strategy_id": "...", "result": "...", "reason": "...", "metadata_json": "..."}
    ]
  },

  "quality_history": [
    {"symbol": "...", "strategy_id": "...", "composite_score": 65.0, "grade": "B+", "calculated_shares": 0, "scored_at": "..."}
  ],

  "trades": [
    {"...full trade row as dict..."}
  ],

  "catalyst_summary": {
    "total_events_today": 1024,
    "by_source": {"sec_edgar": 200, "finnhub": 824},
    "sample_events": ["...first 20 events..."]
  },

  "account_state": {
    "equity": 984166.79,
    "buying_power": 0.0,
    "cash": 50000.0,
    "positions": [
      {"symbol": "GNTX", "quantity": -30732, "avg_cost": 21.03, "market_value": -646000.0}
    ]
  },

  "regime": {
    "current": "range_bound",
    "spy_data_available": false,
    "allocations": {"strat_orb_breakout": {"eligible": true, "allocation_dollars": 196833.0}}
  }
}
```

**Implementation details:**

- **orchestrator_decisions:** Query `orchestrator_decisions` table filtered by
  `date = '{session_date}'`. Return all rows as dicts.

- **evaluation_summary:** Query `evaluation_events` table in `evaluation.db`
  filtered by `trading_date = '{session_date}'`. Use `eval_store.execute_query()`
  (public method, Sprint 25 S10). Return:
  - Total count
  - Per-strategy count + distinct symbols (`GROUP BY strategy_id`)
  - Event type × result distribution (`GROUP BY event_type, result ORDER BY count DESC LIMIT 20`)
  - Last 50 `ENTRY_EVALUATION` events with full metadata (the "closest misses" query)

- **quality_history:** Query `quality_history` table in `argus.db` filtered by
  `created_at >= '{session_date}'`. Return all rows as dicts.

- **trades:** Query `trades` table in `argus.db` for today. Use
  `PRAGMA table_info(trades)` to get column names dynamically, then
  `SELECT * FROM trades WHERE date(created_at) = '{session_date}'`.
  Return all rows as dicts.

- **catalyst_summary:** Open `catalyst.db` with a separate `aiosqlite` connection
  (it's a different database file from argus.db). Query `catalyst_events` for today.
  Return total count, count by source, and first 20 events as sample. Close the
  connection when done.

- **account_state:** Call `broker.get_account()` for equity/buying_power/cash.
  Call `broker.get_positions()` for position list. Convert positions to dicts.

- **regime:** Read `orchestrator.current_regime`, check
  `orchestrator._spy_unavailable_count > 0` as proxy for SPY availability,
  and include current allocations from `orchestrator._current_allocations`.

**Error handling:**
- Wrap EACH section in its own try/except. If one section fails (e.g., catalyst.db
  doesn't exist), populate that section with `{"error": "reason"}` and continue.
  Never let one section's failure prevent other sections from being exported.
- Wrap the entire function in try/except. On failure, log a WARNING and return None.
- Use `json.dumps(..., default=str, indent=2)` for the final serialization to handle
  datetime objects, Decimal types, enums, etc.

#### 5b. Wire into shutdown sequence

**File:** `argus/main.py`

In the `shutdown()` method, insert the debrief export **after** the shutdown alert
(~line 1125) and **before** step 0 (stop API server). At this point all DBs and
the broker are still alive.

```python
# --- Debrief Export (before tearing down components) ---
try:
    from argus.analytics.debrief_export import export_debrief_data
    from zoneinfo import ZoneInfo

    et_tz = ZoneInfo("America/New_York")
    session_date = self._clock.now().astimezone(et_tz).strftime("%Y-%m-%d")

    catalyst_db_path = None
    data_dir_str = getattr(
        getattr(self._config, 'system', self._config), 'data_dir', 'data'
    )
    if self._catalyst_storage is not None:
        catalyst_db_path = str(Path(data_dir_str) / "catalyst.db")

    export_path = await export_debrief_data(
        session_date=session_date,
        db=self._db,
        eval_store=self._eval_store,
        catalyst_db_path=catalyst_db_path,
        broker=self._broker,
        orchestrator=self._orchestrator,
        output_dir="logs",
    )
    if export_path:
        logger.info("Debrief data exported: %s", export_path)
    else:
        logger.warning("Debrief data export failed — see earlier warnings")
except Exception as e:
    logger.warning("Debrief export error (non-fatal): %s", e)
```

The import is inside the try block so it never affects startup or normal operation.

### 6. Fix VWAP Reclaim false suspension on zero trade history (DEF-080)

**Files:** `argus/core/throttle.py`, possibly `argus/core/orchestrator.py`

VWAP Reclaim was suspended by the PerformanceThrottler on March 20 despite zero
trades ever having been executed by any strategy. The throttler logged
"performance threshold breached" for VWAP Reclaim, which received $0 allocation
and was marked inactive.

A strategy with no trade history should not trigger `ThrottleAction.SUSPEND`.

Investigate `PerformanceThrottler.check()` — determine what condition causes
SUSPEND when `trades=[]` and `daily_pnl=0.0`. Fix the edge case so that
strategies with no trade history return `ThrottleAction.NONE`.

If the fix is straightforward (initialization default, empty-list edge case,
division-by-zero guard), implement it with tests. If it requires deeper throttler
redesign, log it as DEF-080 with a description of the root cause and skip the
implementation — do not attempt a large refactor in this session.

### 7. Enrich entry evaluation metadata with condition progress (DEF-081)

**File:** `argus/strategies/orb_base.py`

The `ENTRY_EVALUATION` events recorded by `_check_breakout_conditions()` do not
include `conditions_passed` or `conditions_total` in their metadata, which
reduces the diagnostic value of the closest-miss analysis in debriefs.

The method checks 4 conditions sequentially (close > OR high, volume, VWAP, chase
protection) and returns on the first failure. Each ENTRY_EVALUATION already
records which condition failed, but not where it falls in the sequence.

Add `conditions_passed` and `conditions_total` to the metadata dict of every
`ENTRY_EVALUATION` call in `_check_breakout_conditions()`:

- Condition 1 (close > OR high) failure: `{"conditions_passed": 0, "conditions_total": 4, ...}`
- Condition 2 (volume) failure: `{"conditions_passed": 1, "conditions_total": 4, ...}`
- Condition 3 (VWAP) failure: `{"conditions_passed": 2, "conditions_total": 4, ...}`
- Condition 4 (chase) failure: `{"conditions_passed": 3, "conditions_total": 4, ...}`
- All pass: `{"conditions_passed": 4, "conditions_total": 4, ...}`

This is purely additive — merge these keys into the existing metadata dicts. Do
not restructure the method or change any evaluation logic.

Note: VWAP Reclaim and Afternoon Momentum use `CONDITION_CHECK` and
`STATE_TRANSITION` event types, not `ENTRY_EVALUATION`. They are out of scope
for this change.

### 8. Log new deferred items in CLAUDE.md

Add the following entries to the deferred items table in `CLAUDE.md`:

| ID | Item | Target | Notes |
|----|------|--------|-------|
| DEF-075 | `fetch_daily_bars()` via FMP for regime classification | Sprint 25.7 (this sprint) | Implemented. |
| DEF-076 | Health endpoint `last_data_received` always null | Sprint 25.7 | Implemented. |
| DEF-077 | Diagnostic logging when position sizer returns 0 shares | Sprint 25.7 | Implemented. |
| DEF-078 | Rate-limit regime reclassification warnings | Sprint 25.7 | Implemented. |
| DEF-079 | Automated debrief data export at shutdown | Sprint 25.7 | Implemented. |
| DEF-080 | VWAP Reclaim false suspension on zero trade history | Sprint 25.7 | Implemented (or deferred if complex — update accordingly). |
| DEF-081 | Entry evaluation conditions_passed/conditions_total metadata | Sprint 25.7 | Implemented. |
| DEF-082 | Quality engine catalyst_quality and volume_profile always 50.0 (neutral default) | Unscheduled | Expected when no real-time RVOL or symbol-specific catalysts. Will become useful as data sources are enriched. Priority: LOW. |

## Constraints

- Only modify `argus/strategies/orb_base.py` for Req 7 — do NOT modify individual
  strategy files (`orb_breakout.py`, `orb_scalp.py`, `vwap_reclaim.py`,
  `afternoon_momentum.py`)
- Do NOT modify risk manager behavior
- Do NOT modify the Quality Engine scoring logic
- Do NOT modify any frontend files
- Do NOT change the Orchestrator's allocation logic
- The IBKR position-flattening script is a one-time operation — delete it after use
- `fetch_daily_bars()` must return `None` on any error (preserving existing fallback)
- All changes must be backward-compatible with `BrokerSource.SIMULATED`
- The debrief export must NEVER prevent shutdown. Every section independently
  try/excepted, entire call wrapped in try/except in `shutdown()`.

## Test Targets

After implementation:
- Existing tests: all ~2,794 must still pass
- New tests to write:

**`fetch_daily_bars` tests (in `tests/data/` — new file or existing):**
1. `test_fetch_daily_bars_success` — mock FMP response, verify DataFrame columns,
   row count, ascending sort
2. `test_fetch_daily_bars_no_api_key` — unset `FMP_API_KEY`, verify returns `None`
3. `test_fetch_daily_bars_http_error` — mock 403/500, verify returns `None`
4. `test_fetch_daily_bars_timeout` — mock timeout, verify returns `None`
5. `test_fetch_daily_bars_empty_response` — mock empty JSON array, verify returns `None`
6. `test_fetch_daily_bars_lookback_limit` — mock 100 rows, request 60, verify 60

**`last_update` test:**
7. `test_last_update_set_on_dispatch` — verify `last_update` is set after dispatch

**Sizer logging test:**
8. `test_signal_skipped_logs_diagnostic_fields` — verify log contains buying_power etc.

**Regime warning tests:**
9. `test_regime_warning_rate_limited` — 12 calls, verify warning only on 1 and 6
10. `test_spy_unavailable_counter_resets_on_success` — verify counter resets

**Debrief export tests (new file `tests/analytics/test_debrief_export.py`):**
11. `test_export_creates_json_file` — mock all deps, verify JSON file with expected keys
12. `test_export_handles_missing_eval_store` — `eval_store=None`, verify partial export
13. `test_export_handles_missing_catalyst_db` — bad path, verify partial export
14. `test_export_handles_broker_error` — broker raises, verify partial export
15. `test_export_json_serializes_datetimes` — datetime values serialize cleanly

**VWAP throttle tests (in `tests/core/` — new file or existing):**
16. `test_throttler_no_trades_returns_none` — empty trade list, verify `ThrottleAction.NONE`
17. `test_throttler_no_trades_does_not_suspend` — verify strategy stays active with no history

**Entry evaluation metadata tests (in `tests/strategies/` — new file or existing):**
18. `test_entry_eval_metadata_has_conditions_passed` — trigger a failing condition,
    verify `conditions_passed` and `conditions_total` in the recorded metadata
19. `test_entry_eval_all_pass_conditions_count` — trigger a full pass, verify
    `conditions_passed == conditions_total`

- Minimum new test count: 19
- Test command: `python -m pytest --ignore=tests/test_main.py -n auto -q`

## Definition of Done

- [ ] 7 IBKR paper positions flattened, buying_power > 0 confirmed
- [ ] `fetch_daily_bars()` implemented via FMP, returning valid DataFrame for SPY
- [ ] Health endpoint `last_data_received` populated when data is flowing
- [ ] Sizer 0-share log includes grade, score, buying_power, allocated_capital
- [ ] Regime warnings rate-limited (~13 per session, not 76)
- [ ] Debrief export runs during shutdown, produces `logs/debrief_YYYYMMDD.json`
- [ ] Debrief export survives any single component failure gracefully
- [ ] VWAP Reclaim throttle bug investigated and fixed (or DEF-080 documented if complex)
- [ ] ENTRY_EVALUATION metadata includes conditions_passed/conditions_total
- [ ] DEF-075 through DEF-082 logged in CLAUDE.md
- [ ] All existing tests pass
- [ ] 19+ new tests written and passing
- [ ] Close-out report written to file
- [ ] Tier 2 review completed via @reviewer subagent

## Regression Checklist (Session-Specific)

| Check | How to Verify |
|-------|---------------|
| Backtesting unaffected | `python -m pytest tests/backtest/ -q` passes |
| Health endpoint still works | existing health tests pass |
| Orchestrator pre-market unchanged | `python -m pytest tests/core/test_orchestrator.py -q` passes |
| Quality pipeline unchanged | `python -m pytest tests/intelligence/ -q` passes |
| Data service starts correctly | `python -m pytest tests/data/ -q` passes |
| Strategy logic unchanged | `python -m pytest tests/strategies/ -q` passes |
| Shutdown completes even if export fails | Debrief export wrapped in try/except |
| No new imports at module level in main.py | Debrief import is inside shutdown() |
| ORB evaluation behavior unchanged | Only metadata enriched, no logic changes |

## Close-Out

After all work is complete, follow the close-out skill in `.claude/skills/close-out.md`.

The close-out report MUST include a structured JSON appendix at the end,
fenced with ```json:structured-closeout. See the close-out skill for the
full schema and requirements.

**Write the close-out report to a file** (DEC-330):
`docs/sprints/sprint-25.7/session-1-closeout.md`

Do NOT just print the report in the terminal. Create the file, write the
full report (including the structured JSON appendix) to it, and commit it.

**Create the sprint directory first:** `mkdir -p docs/sprints/sprint-25.7`

## Tier 2 Review (Mandatory — @reviewer Subagent)

After the close-out is written to file and committed, invoke the @reviewer
subagent to perform the Tier 2 review within this same session.

Provide the @reviewer with:
1. The close-out report path: `docs/sprints/sprint-25.7/session-1-closeout.md`
2. The diff range: `git diff HEAD~1` (or appropriate range covering all changes)
3. The test command: `python -m pytest --ignore=tests/test_main.py -n auto -q`
4. Files that should NOT have been modified:
   - `argus/strategies/orb_breakout.py`
   - `argus/strategies/orb_scalp.py`
   - `argus/strategies/vwap_reclaim.py`
   - `argus/strategies/afternoon_momentum.py`
   - `argus/core/risk_manager.py`
   - `argus/intelligence/quality_engine.py`
   - `argus/ui/**`

The @reviewer will produce its review report and write it to:
`docs/sprints/sprint-25.7/session-1-review.md`

## Post-Review Fix Documentation

If the @reviewer reports CONCERNS and you fix the findings within this same
session, you MUST update the artifact trail:

1. Append a "Post-Review Fixes" section to the close-out report file
2. Append a "Resolved" annotation to the review report file
3. Update the structured verdict JSON to `CONCERNS_RESOLVED`

See the implementation prompt template for full details.

## Session-Specific Review Focus (for @reviewer)

1. Verify `fetch_daily_bars()` returns `None` on all error paths (no exceptions leak)
2. Verify `last_update` is set in `_dispatch_record()` — the hot path — and confirm
   no performance impact (single `datetime.now()` call is negligible)
3. Verify the position-flattening script was deleted after use
4. Verify the regime warning counter resets on success
5. Verify diagnostic log message in `_process_signal()` uses correct variable names
   (especially `account.buying_power`, not `account.cash`)
6. Verify no FMP API key is hardcoded anywhere — must read from env var
7. Verify debrief export is fully wrapped in try/except in shutdown() — must never
   prevent graceful shutdown
8. Verify debrief export handles each section independently — one section's failure
   must not prevent other sections from being exported
9. Verify debrief export uses `json.dumps(default=str)` for datetime serialization
10. Verify debrief export imports are inside the function/shutdown block, not at module level
11. Verify throttle fix does not change behavior for strategies WITH trade history
12. Verify `conditions_passed`/`conditions_total` metadata is additive only — no
    changes to evaluation logic, result values, or method structure in `orb_base.py`

## Sprint-Level Escalation Criteria (for @reviewer)

- ESCALATE if: `fetch_daily_bars()` can raise an unhandled exception to the caller
- ESCALATE if: any change affects trade execution logic (Risk Manager, Order Manager)
- ESCALATE if: the position-flattening script was not deleted
- ESCALATE if: the debrief export can prevent graceful shutdown (missing try/except)
- ESCALATE if: new code introduces a circular import
- ESCALATE if: ORB evaluation logic was changed (not just metadata enrichment)
- ESCALATE if: throttle fix changes behavior for strategies with existing trade history

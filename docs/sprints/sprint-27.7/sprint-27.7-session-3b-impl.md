# Sprint 27.7, Session 3b: Startup Wiring + Event Subscriptions + EOD Task

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - `argus/intelligence/counterfactual.py` (CounterfactualTracker — track(), on_candle(), close_all_eod(), check_timeouts())
   - `argus/intelligence/counterfactual_store.py` (CounterfactualStore — initialize(), write_open(), write_close())
   - `argus/intelligence/startup.py` (existing factory functions — build_catalyst_pipeline pattern)
   - `argus/main.py` (startup sequence — `_initialize_phase_*` methods, EOD scheduling pattern, `_counterfactual_enabled` flag from S3a)
   - `argus/core/events.py` (SignalRejectedEvent from S3a, CandleEvent)
   - `config/system.yaml` (where to add counterfactual section)
2. Run scoped test baseline (DEC-328):
   ```
   python -m pytest tests/intelligence/ tests/test_signal_rejected.py -x -q
   ```
   Expected: all passing (Session 3a close-out confirmed full suite)
3. Verify you are on branch `main` or `sprint-27.7`

## Objective
Wire the Counterfactual Engine into the running ARGUS process: build tracker+store in the startup factory, register event bus subscriptions (SignalRejectedEvent → tracker, CandleEvent → tracker), schedule the EOD cleanup task, add counterfactual config to system YAML files, and flip the `_counterfactual_enabled` flag.

## Requirements

### 1. Add factory method to `argus/intelligence/startup.py`

Add a `build_counterfactual_tracker()` function following the existing `build_catalyst_pipeline()` pattern:

```python
async def build_counterfactual_tracker(
    config: SystemConfig,
    candle_store=None,
) -> tuple[CounterfactualTracker, CounterfactualStore] | None:
    """Build and initialize the Counterfactual Engine components.
    
    Returns None if counterfactual.enabled is False.
    """
    if not config.counterfactual.enabled:
        return None
    
    store = CounterfactualStore(db_path="data/counterfactual.db")
    await store.initialize()
    
    tracker = CounterfactualTracker(
        candle_store=candle_store,
        eod_close_time=config.counterfactual.eod_close_time,
        no_data_timeout_seconds=config.counterfactual.no_data_timeout_seconds,
    )
    tracker.set_store(store)  # Wire store for persistence
    
    return tracker, store
```

Note: The `tracker.set_store()` method may need to be added to CounterfactualTracker if not already present from Session 1. If it's missing, add it — it follows the same pattern as `StrategyEvaluationBuffer.set_store()`.

### 2. Wire into `argus/main.py` — Startup sequence

2a. Add instance variables in `ArgusApp.__init__()`:
```python
self._counterfactual_tracker: CounterfactualTracker | None = None
self._counterfactual_store: CounterfactualStore | None = None
```

2b. In the appropriate startup phase (after quality engine and orchestrator init, around Phase 9.5 or later — the tracker needs the candle store which is initialized early), add:
```python
# Counterfactual Engine (Sprint 27.7)
result = await build_counterfactual_tracker(
    config=self._config,
    candle_store=self._intraday_candle_store,
)
if result is not None:
    self._counterfactual_tracker, self._counterfactual_store = result
    self._counterfactual_enabled = True  # Flip the S3a flag
    logger.info("Counterfactual Engine initialized")
```

2c. Register event bus subscriptions (after tracker init):
```python
if self._counterfactual_tracker is not None:
    # Rejected signals → counterfactual tracking
    await self._event_bus.subscribe(
        SignalRejectedEvent,
        self._on_signal_rejected_for_counterfactual,
    )
    # Candle events → monitor open counterfactual positions
    await self._event_bus.subscribe(
        CandleEvent,
        self._counterfactual_tracker.on_candle,
    )
```

2d. Add the SignalRejectedEvent handler method:
```python
async def _on_signal_rejected_for_counterfactual(self, event: SignalRejectedEvent) -> None:
    """Route rejected signals to the Counterfactual Engine for shadow tracking."""
    if self._counterfactual_tracker is None or event.signal is None:
        return
    try:
        self._counterfactual_tracker.track(
            signal=event.signal,
            rejection_reason=event.rejection_reason,
            rejection_stage=RejectionStage(event.rejection_stage),
            metadata={
                "quality_score": event.quality_score,
                "quality_grade": event.quality_grade,
                "regime_vector_snapshot": event.regime_vector_snapshot,
                **(event.metadata or {}),
            },
        )
    except Exception:
        logger.warning("Counterfactual tracking failed for %s", event.signal.symbol, exc_info=True)
```

### 3. Schedule EOD cleanup task

Follow the existing asyncio task pattern (similar to regime reclassification 300s task or health monitor 60s task):

```python
if self._counterfactual_tracker is not None:
    # EOD close and timeout check — run every 60s during market hours
    async def _counterfactual_maintenance():
        while True:
            await asyncio.sleep(60)
            if not self._is_market_hours():
                continue
            # Check for timed-out positions
            try:
                self._counterfactual_tracker.check_timeouts()
            except Exception:
                logger.warning("Counterfactual timeout check failed", exc_info=True)
    
    self._counterfactual_maintenance_task = asyncio.create_task(_counterfactual_maintenance())
```

For the EOD close, hook into the existing shutdown/EOD flatten sequence. When the system shuts down or reaches EOD, call:
```python
if self._counterfactual_tracker is not None:
    await self._counterfactual_tracker.close_all_eod()
```

Also close the store on shutdown:
```python
if self._counterfactual_store is not None:
    await self._counterfactual_store.close()
```

### 4. Add counterfactual config to YAML files

**`config/system.yaml`** — add after the `observatory` section:
```yaml
# Counterfactual Engine (Sprint 27.7)
counterfactual:
  enabled: true
  retention_days: 90
  no_data_timeout_seconds: 300
  eod_close_time: "16:00"
```

**`config/system_live.yaml`** — add same section:
```yaml
# Counterfactual Engine (Sprint 27.7)
counterfactual:
  enabled: true
  retention_days: 90
  no_data_timeout_seconds: 300
  eod_close_time: "16:00"
```

### 5. Retention enforcement

Add a daily retention enforcement call. Either:
- In the startup sequence: `await store.enforce_retention(config.counterfactual.retention_days)` (runs once per boot), or
- On a 24h timer (less important for a 90-day retention window)

Once-per-boot is sufficient.

## Constraints
- Do NOT modify: `argus/core/risk_manager.py`, `argus/core/regime.py`, `argus/data/intraday_candle_store.py`, `argus/core/events.py` (S3a changes are complete), any strategy files, any frontend files
- Do NOT add: FilterAccuracy computation (S4), API endpoints (S4), shadow mode (S5)
- The `_on_signal_rejected_for_counterfactual` handler must be wrapped in try/except — counterfactual tracking must never disrupt the signal pipeline
- Event bus subscription for CandleEvent may receive high volume (~3,000+ symbols × ~390 bars/day). The tracker should short-circuit quickly for symbols with no open positions (`if symbol not in self._symbols_to_positions: return`).

## Test Targets
After implementation:
- Existing tests: all must still pass
- New tests to write:
  1. **startup: tracker created when enabled** — config enabled=true → build_counterfactual_tracker returns (tracker, store)
  2. **startup: None when disabled** — config enabled=false → returns None
  3. **startup: store initialized** — verify store.initialize() called (table created)
  4. **wiring: SignalRejectedEvent subscription delivers to tracker** — publish event on bus, verify tracker.track() called
  5. **wiring: CandleEvent subscription delivers to tracker** — publish candle on bus, verify tracker.on_candle() called
  6. **wiring: handler exception doesn't propagate** — tracker.track() raises → no exception escapes handler
  7. **eod: close_all_eod called on shutdown** — verify EOD close is triggered during shutdown sequence
  8. **timeout: check_timeouts fires periodically** — verify timeout check runs (can use short sleep in test)
  9. **config: system.yaml parses with counterfactual section** — load system.yaml, verify counterfactual config present
  10. **retention: enforce_retention called at startup** — verify retention runs once on boot
- Minimum new test count: 6
- Test file: `tests/intelligence/test_counterfactual_wiring.py` (or additions to existing test files)
- Test command: `python -m pytest tests/intelligence/ tests/test_signal_rejected.py -x -q`

## Definition of Done
- [ ] `build_counterfactual_tracker()` factory in `startup.py`
- [ ] Tracker + store initialized in main.py startup sequence
- [ ] `_counterfactual_enabled` flag flipped to True when tracker is created
- [ ] SignalRejectedEvent subscription registered on event bus
- [ ] CandleEvent subscription registered on event bus
- [ ] EOD close wired into shutdown sequence
- [ ] Timeout check task scheduled (60s during market hours)
- [ ] Retention enforcement at startup
- [ ] `counterfactual` section in system.yaml and system_live.yaml
- [ ] All existing tests pass
- [ ] ≥6 new tests written and passing
- [ ] Close-out report written to file
- [ ] Tier 2 review completed via @reviewer subagent

## Regression Checklist (Session-Specific)

| Check | How to Verify |
|-------|---------------|
| Event bus FIFO ordering preserved | Existing event bus tests pass; no priority changes to any event type |
| CandleEvent handler doesn't slow candle processing | Tracker short-circuits for symbols with no open positions |
| Startup sequence order unchanged for existing components | Existing startup tests pass |
| Shutdown sequence closes store | Verify `store.close()` in shutdown path |
| system.yaml and system_live.yaml parse correctly | Config loading tests pass |

## Close-Out
After all work is complete, follow the close-out skill in .claude/skills/close-out.md.

The close-out report MUST include a structured JSON appendix at the end,
fenced with ```json:structured-closeout. See the close-out skill for the
full schema and requirements.

**Write the close-out report to a file:**
`docs/sprints/sprint-27.7/session-3b-closeout.md`

Do NOT just print the report in the terminal. Create the file, write the
full report (including the structured JSON appendix) to it, and commit it.

## Tier 2 Review (Mandatory — @reviewer Subagent)
Provide the @reviewer with:
1. The review context file: `docs/sprints/sprint-27.7/review-context.md`
2. The close-out report path: `docs/sprints/sprint-27.7/session-3b-closeout.md`
3. The diff range: `git diff HEAD~1`
4. The test command: `python -m pytest tests/intelligence/ tests/test_signal_rejected.py -x -q`
5. Files that should NOT have been modified: `argus/core/risk_manager.py`, `argus/core/regime.py`, `argus/data/intraday_candle_store.py`, `argus/core/events.py`, any files in `argus/strategies/`, any files in `argus/ui/`

The @reviewer will write its report to:
`docs/sprints/sprint-27.7/session-3b-review.md`

## Post-Review Fix Documentation
If CONCERNS, update both close-out and review files per protocol.

## Session-Specific Review Focus (for @reviewer)
1. Verify `_on_signal_rejected_for_counterfactual` is wrapped in try/except — must never disrupt signal pipeline
2. Verify CandleEvent subscription handler short-circuits for symbols with no open counterfactual positions
3. Verify `_counterfactual_enabled` is only set to True after tracker initialization succeeds
4. Verify EOD close is called during shutdown (not just on a timer)
5. Verify store.close() is called during shutdown cleanup
6. Verify counterfactual config section in system.yaml and system_live.yaml matches the Pydantic model fields exactly

## Sprint-Level Regression Checklist (for @reviewer)
(see review-context.md)

## Sprint-Level Escalation Criteria (for @reviewer)
(see review-context.md)

# Sprint 27.7, Session 3a: SignalRejectedEvent + Rejection Publishing

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - `argus/intelligence/counterfactual.py` (RejectionStage enum)
   - `argus/core/events.py` (existing event patterns — SignalEvent, OrderRejectedEvent, CandleEvent)
   - `argus/main.py` (full `_process_signal()` method — lines ~1205–1342, and signal listener `_on_signal()` — lines ~1179–1203)
2. Run scoped test baseline (DEC-328):
   ```
   python -m pytest tests/intelligence/ tests/core/test_fill_model.py -x -q
   ```
   Expected: all passing (Session 2 close-out confirmed full suite)
3. Verify you are on branch `main` or `sprint-27.7`

## Objective
Add `SignalRejectedEvent` to the event model and publish it from three rejection points in `_process_signal()`. This session only adds the event and the publishing — subscription and startup wiring come in Session 3b.

## Requirements

### 1. Add `SignalRejectedEvent` to `argus/core/events.py`

Add after the `OrderRejectedEvent` class (in the Risk Events section):

```python
@dataclass(frozen=True)
class SignalRejectedEvent(Event):
    """A signal was rejected before reaching order submission.
    
    Published by _process_signal() when a signal is filtered out by the
    quality engine, position sizer, or risk manager. The Counterfactual
    Engine subscribes to this event to track theoretical outcomes.
    """
    signal: SignalEvent | None = None
    rejection_reason: str = ""
    rejection_stage: str = ""  # RejectionStage value: "QUALITY_FILTER", "POSITION_SIZER", "RISK_MANAGER", "SHADOW"
    quality_score: float | None = None
    quality_grade: str | None = None
    regime_vector_snapshot: dict | None = None  # RegimeVector.to_dict() if available
    metadata: dict = field(default_factory=dict)
```

Note: `rejection_stage` is typed as `str` (not importing RejectionStage from intelligence) to avoid a core→intelligence import dependency. The string values match the RejectionStage enum. The tracker will validate on receipt.

### 2. Publish `SignalRejectedEvent` in `argus/main.py` — three rejection points

**Important:** All three publishing points are conditional on the counterfactual system being available. Add a `self._counterfactual_enabled: bool` flag (initially `False`, set during startup in Session 3b). When False, no events are published.

For each rejection point, capture the current regime vector:
```python
regime_snapshot = None
if self._orchestrator is not None:
    rv = getattr(self._orchestrator, 'latest_regime_vector', None)
    if rv is not None and hasattr(rv, 'to_dict'):
        regime_snapshot = rv.to_dict()
```

**2a. Quality grade filter rejection** — in `_process_signal()`, after `_grade_meets_minimum()` returns False (around line 1262-1271):

After the existing `logger.info(...)` and before the `return`, add:
```python
if self._counterfactual_enabled:
    await self._event_bus.publish(SignalRejectedEvent(
        signal=signal,
        rejection_reason=f"Quality grade {quality.grade} below minimum {min_grade}",
        rejection_stage="QUALITY_FILTER",
        quality_score=quality.score,
        quality_grade=quality.grade,
        regime_vector_snapshot=regime_snapshot,
    ))
```

Note: At this point, `signal` still has `share_count=0` (strategies emit 0, quality pipeline sizes). The signal has `entry_price`, `stop_price`, and `target_prices` populated by the strategy.

**2b. Position sizer returns 0 shares** — after the `shares <= 0` check (around lines 1283-1299):

After the existing logger and before the `return`, add:
```python
if self._counterfactual_enabled:
    await self._event_bus.publish(SignalRejectedEvent(
        signal=signal,
        rejection_reason=f"Position sizer returned 0 shares (grade={quality.grade}, score={quality.score:.0f})",
        rejection_stage="POSITION_SIZER",
        quality_score=quality.score,
        quality_grade=quality.grade,
        regime_vector_snapshot=regime_snapshot,
    ))
```

**2c. Risk Manager rejection** — after `evaluate_signal()` returns `OrderRejectedEvent` (around line 1325-1326):

The current code is:
```python
result = await self._risk_manager.evaluate_signal(signal)
await self._event_bus.publish(result)
```

Add after the publish:
```python
if self._counterfactual_enabled and isinstance(result, OrderRejectedEvent):
    await self._event_bus.publish(SignalRejectedEvent(
        signal=signal,
        rejection_reason=result.reason,
        rejection_stage="RISK_MANAGER",
        quality_score=getattr(signal, 'quality_score', None),
        quality_grade=getattr(signal, 'quality_grade', None),
        regime_vector_snapshot=regime_snapshot,
    ))
```

Note: At this point, `signal` has been enriched with quality_score, quality_grade, and share_count by the quality pipeline. The Risk Manager rejection carries the structured reason.

### 3. Add `_counterfactual_enabled` flag to main.py

In the `ArgusApp.__init__()` method, add:
```python
self._counterfactual_enabled: bool = False
```

This will be set to `True` in Session 3b when the tracker is initialized. For now, it defaults to `False`, meaning no `SignalRejectedEvent` events are published. This ensures the Session 3a changes are inert until Session 3b completes the wiring.

## Constraints
- Do NOT modify: `argus/core/risk_manager.py` (rejection reasons already structured), `argus/intelligence/startup.py` (factory comes in S3b), `config/system.yaml`, `config/system_live.yaml` (S3b), any strategy files, any frontend files
- Do NOT add: Event bus subscriptions (S3b), startup initialization (S3b), EOD task (S3b)
- Do NOT import from `argus.intelligence` in `argus/core/events.py` — keep core→intelligence dependency direction clean. Use string literals for `rejection_stage`.
- The `_counterfactual_enabled` flag must default to `False` — no behavioral change until S3b wires it.

## Test Targets
After implementation:
- Existing tests: all must still pass
- New tests to write:
  1. **event: SignalRejectedEvent creation** — construct with all fields, verify frozen dataclass behavior
  2. **rejection: quality filter publishes event** — mock `_process_signal` with quality grade below minimum, verify SignalRejectedEvent published with stage=QUALITY_FILTER and correct quality_score/grade
  3. **rejection: sizer publishes event** — sizer returns 0, verify event published with stage=POSITION_SIZER
  4. **rejection: risk manager publishes event** — RM returns OrderRejectedEvent, verify SignalRejectedEvent published with stage=RISK_MANAGER and correct reason
  5. **rejection: disabled flag suppresses events** — `_counterfactual_enabled=False`, verify no SignalRejectedEvent published for any rejection
  6. **rejection: regime vector captured** — verify regime_vector_snapshot is populated when orchestrator has a regime vector
  7. **rejection: signal carries entry/stop/target** — verify the signal in the event has non-zero entry_price, stop_price, and target_prices
- Minimum new test count: 6
- Test file: `tests/test_signal_rejected.py` or `tests/test_main_counterfactual.py`
- Test command: `python -m pytest tests/test_signal_rejected.py -x -q` (or appropriate path)

## Definition of Done
- [ ] `SignalRejectedEvent` added to `argus/core/events.py`
- [ ] Three rejection points in `_process_signal()` publish SignalRejectedEvent
- [ ] `_counterfactual_enabled` flag added, defaults to False
- [ ] Regime vector snapshot captured at each rejection point
- [ ] No behavioral change for live-mode strategies (flag is False by default)
- [ ] All existing tests pass
- [ ] ≥6 new tests written and passing
- [ ] Close-out report written to file
- [ ] Tier 2 review completed via @reviewer subagent

## Regression Checklist (Session-Specific)

| Check | How to Verify |
|-------|---------------|
| `_process_signal()` behavior unchanged when `_counterfactual_enabled=False` | Existing tests pass unchanged — no new awaits on critical path when disabled |
| `OrderApprovedEvent`/`OrderRejectedEvent` still published correctly | Existing risk manager tests pass |
| No import from `argus.intelligence` in `argus/core/events.py` | Grep imports in events.py — only stdlib and core imports |
| Risk Manager not modified | `git diff argus/core/risk_manager.py` shows no changes |

## Close-Out
After all work is complete, follow the close-out skill in .claude/skills/close-out.md.

The close-out report MUST include a structured JSON appendix at the end,
fenced with ```json:structured-closeout. See the close-out skill for the
full schema and requirements.

**Write the close-out report to a file:**
`docs/sprints/sprint-27.7/session-3a-closeout.md`

Do NOT just print the report in the terminal. Create the file, write the
full report (including the structured JSON appendix) to it, and commit it.

## Tier 2 Review (Mandatory — @reviewer Subagent)
Provide the @reviewer with:
1. The review context file: `docs/sprints/sprint-27.7/review-context.md`
2. The close-out report path: `docs/sprints/sprint-27.7/session-3a-closeout.md`
3. The diff range: `git diff HEAD~1`
4. The test command: `python -m pytest tests/test_signal_rejected.py tests/intelligence/ -x -q`
5. Files that should NOT have been modified: `argus/core/risk_manager.py`, `argus/intelligence/startup.py`, `config/system.yaml`, `config/system_live.yaml`, any files in `argus/strategies/`, any files in `argus/ui/`

The @reviewer will write its report to:
`docs/sprints/sprint-27.7/session-3a-review.md`

## Post-Review Fix Documentation
If the @reviewer reports CONCERNS and you fix the findings within this same
session, update both the close-out and review files per the post-review fix
documentation protocol.

## Session-Specific Review Focus (for @reviewer)
1. Verify `rejection_stage` is a string literal, NOT an import from intelligence module — preserves core→intelligence dependency direction
2. Verify `_counterfactual_enabled` defaults to False and is checked before every publish
3. Verify the signal in each SignalRejectedEvent has entry_price/stop_price/target_prices populated (not zeroed)
4. Verify no new `await` calls are added to the critical path when `_counterfactual_enabled=False` — the flag check must be a simple boolean, not an async call
5. Verify the OrderApprovedEvent/OrderRejectedEvent publish in the existing code is not moved or reordered — SignalRejectedEvent is published AFTER the existing event flow, not instead of
6. At the Risk Manager rejection point, verify SignalRejectedEvent is published after `await self._event_bus.publish(result)` — the OrderRejectedEvent must go out first

## Sprint-Level Regression Checklist (for @reviewer)
(see review-context.md)

## Sprint-Level Escalation Criteria (for @reviewer)
(see review-context.md)

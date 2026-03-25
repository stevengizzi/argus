# Sprint 27.7, Session 5: Shadow Strategy Mode

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - `argus/strategies/base_strategy.py` (BaseStrategy class, config handling)
   - `argus/main.py` (post-S3b state — `_process_signal()`, `_counterfactual_enabled` flag, SignalRejectedEvent publishing)
   - `argus/intelligence/counterfactual.py` (RejectionStage.SHADOW)
   - `config/strategies/orb_breakout.yaml` (example strategy config — see field structure)
   - `argus/core/events.py` (SignalRejectedEvent)
2. Run scoped test baseline (DEC-328):
   ```
   python -m pytest tests/intelligence/ tests/test_signal_rejected.py tests/strategies/ -x -q
   ```
   Expected: all passing (Session 4 close-out confirmed full suite)
3. Verify you are on branch `main` or `sprint-27.7`

## Objective
Add `StrategyMode` enum, per-strategy `mode` config field, and routing logic in `_process_signal()` that sends shadow-mode signals directly to the counterfactual tracker instead of the quality/risk pipeline. The strategy itself is completely unaware of its mode — shadow mode is a routing decision.

## Requirements

### 1. Add `StrategyMode` to `argus/strategies/base_strategy.py`

```python
class StrategyMode(StrEnum):
    """Operating mode for a strategy (Sprint 27.7)."""
    LIVE = "live"      # Normal execution — signals go through quality + risk pipeline
    SHADOW = "shadow"  # Shadow mode — signals routed to CounterfactualTracker
```

Add this near the top of the file, after imports. Do NOT make strategies aware of their mode internally — the enum is used by the routing logic in main.py.

### 2. Add `mode` config field to strategy configuration

Determine where the per-strategy config model is defined. This is likely in the strategy's config class (e.g., within `StrategyConfig` or `BaseStrategyConfig`). Add:

```python
mode: str = "live"  # StrategyMode — "live" or "shadow"
```

Using `str` with default `"live"` ensures backward compatibility — all existing strategy YAML configs work without modification (they don't have a `mode` field, so Pydantic uses the default).

### 3. Add shadow-mode routing in `argus/main.py`

At the **top** of `_process_signal()`, before the quality engine bypass check, add:

```python
# Shadow mode routing (Sprint 27.7)
strategy_mode = getattr(strategy, 'mode', None) or getattr(getattr(strategy, 'config', None), 'mode', 'live')
if strategy_mode == "shadow" and self._counterfactual_enabled:
    # Shadow strategies bypass quality pipeline and risk manager entirely.
    # Route signal directly to counterfactual tracker.
    regime_snapshot = None
    if self._orchestrator is not None:
        rv = getattr(self._orchestrator, 'latest_regime_vector', None)
        if rv is not None and hasattr(rv, 'to_dict'):
            regime_snapshot = rv.to_dict()
    
    await self._event_bus.publish(SignalRejectedEvent(
        signal=signal,
        rejection_reason="Shadow mode — signal tracked counterfactually, not executed",
        rejection_stage="SHADOW",
        quality_score=None,
        quality_grade=None,
        regime_vector_snapshot=regime_snapshot,
    ))
    return
```

This ensures:
- Shadow signals never reach the quality engine, position sizer, or risk manager
- Shadow signals are published as SignalRejectedEvent with `rejection_stage="SHADOW"`
- The existing CounterfactualTracker subscription (from S3b) picks them up automatically
- If counterfactual is disabled (`_counterfactual_enabled=False`), shadow signals are silently dropped (no execution, no tracking — strategy runs but signals go nowhere)

### 4. Update strategy YAML configs (optional but recommended)

Add `mode: live` to each strategy YAML config for explicitness. This is technically optional since the Pydantic default is `"live"`, but makes the config self-documenting:

In each file under `config/strategies/`:
```yaml
mode: live  # "live" or "shadow" (Sprint 27.7)
```

Add this as the first field in the strategy section for visibility. If the config structure is nested, place it at the appropriate level.

## Constraints
- Do NOT modify: Individual strategy Python files (`orb_breakout.py`, `orb_scalp.py`, etc.) — shadow mode is routing, NOT strategy logic
- Do NOT modify: `argus/core/risk_manager.py`, `argus/core/regime.py`, `argus/intelligence/counterfactual.py`, `argus/intelligence/counterfactual_store.py`, `argus/intelligence/filter_accuracy.py`
- Do NOT add: Shadow-specific UI, shadow performance dashboard, shadow vs live comparison
- The StrategyMode enum lives in `base_strategy.py` but strategies do NOT import or use it — it's for the router in main.py only
- Shadow signals must NOT generate OrderApprovedEvent or OrderRejectedEvent — they are routed before reaching the risk manager

## Test Targets
After implementation:
- Existing tests: all must still pass
- New tests to write:
  1. **StrategyMode enum** — LIVE and SHADOW values exist, StrEnum behavior
  2. **shadow routing: signal goes to tracker** — strategy with mode=shadow, signal published as SignalRejectedEvent with SHADOW stage
  3. **shadow routing: bypasses quality engine** — shadow signal never reaches quality pipeline (quality score is None in the event)
  4. **shadow routing: bypasses risk manager** — shadow signal never reaches evaluate_signal()
  5. **live routing: unchanged** — strategy with mode=live follows normal path (quality → sizer → risk manager)
  6. **default mode is live** — strategy config without explicit mode field → treated as live
  7. **shadow + counterfactual disabled** — shadow signal silently dropped (no exception, no event published)
  8. **shadow signal tracked as counterfactual** — end-to-end: shadow signal → SignalRejectedEvent → tracker → candle monitoring → position close
  9. **config parsing** — strategy YAML with `mode: shadow` parses correctly
- Minimum new test count: 8
- Test file: `tests/test_shadow_mode.py` or `tests/strategies/test_shadow_mode.py`
- Test command (final session — full suite per DEC-328): `python -m pytest --ignore=tests/test_main.py -n auto -q`
- Expected: ~3,460 tests (3,412 existing + ~48 new across all sessions), all passing

## Definition of Done
- [ ] `StrategyMode` enum in `argus/strategies/base_strategy.py`
- [ ] `mode` field on strategy config model with default `"live"`
- [ ] Shadow routing in `_process_signal()` — shadow signals bypass quality/risk, route to tracker
- [ ] Shadow signals dropped silently when counterfactual disabled
- [ ] Strategy YAML configs updated with `mode: live` (explicit)
- [ ] All existing tests pass
- [ ] ≥8 new tests written and passing
- [ ] **Full test suite passes** (final session of sprint)
- [ ] Close-out report written to file
- [ ] Tier 2 review completed via @reviewer subagent

## Regression Checklist (Session-Specific)

| Check | How to Verify |
|-------|---------------|
| All existing strategies default to mode=live | Existing strategy tests pass without config changes |
| No strategy Python files modified | `git diff argus/strategies/orb_breakout.py argus/strategies/orb_scalp.py argus/strategies/vwap_reclaim.py argus/strategies/afternoon_momentum.py argus/strategies/red_to_green.py argus/strategies/patterns/bull_flag.py argus/strategies/patterns/flat_top_breakout.py` shows no changes |
| Shadow signals never produce OrderApprovedEvent | Test verifies no approved/rejected order events for shadow signals |
| _process_signal unchanged for live mode | Existing signal processing tests pass |

## Close-Out
After all work is complete, follow the close-out skill in .claude/skills/close-out.md.

The close-out report MUST include a structured JSON appendix at the end,
fenced with ```json:structured-closeout. See the close-out skill for the
full schema and requirements.

**Write the close-out report to a file:**
`docs/sprints/sprint-27.7/session-5-closeout.md`

Do NOT just print the report in the terminal. Create the file, write the
full report (including the structured JSON appendix) to it, and commit it.

**IMPORTANT: This is the final session of the sprint.** The close-out should note the final test count (all sessions combined) and confirm the full test suite passes.

## Tier 2 Review (Mandatory — @reviewer Subagent)
Provide the @reviewer with:
1. The review context file: `docs/sprints/sprint-27.7/review-context.md`
2. The close-out report path: `docs/sprints/sprint-27.7/session-5-closeout.md`
3. The diff range: `git diff HEAD~1`
4. The test command (FINAL SESSION — full suite per DEC-328): `python -m pytest --ignore=tests/test_main.py -n auto -q`
5. Files that should NOT have been modified: `argus/core/risk_manager.py`, `argus/core/regime.py`, `argus/intelligence/counterfactual.py`, `argus/intelligence/counterfactual_store.py`, `argus/intelligence/filter_accuracy.py`, `argus/data/intraday_candle_store.py`, individual strategy Python files (see list above), any files in `argus/ui/`

The @reviewer will write its report to:
`docs/sprints/sprint-27.7/session-5-review.md`

## Post-Review Fix Documentation
If CONCERNS, update both close-out and review files per protocol.

## Session-Specific Review Focus (for @reviewer)
1. Verify shadow routing is at the TOP of `_process_signal()` — before quality engine bypass check, before any quality/risk logic
2. Verify shadow signals never reach `self._risk_manager.evaluate_signal()` — no OrderApprovedEvent or OrderRejectedEvent
3. Verify the StrategyMode enum is NOT imported or used inside any strategy's Python code — strategies are unaware of their mode
4. Verify default mode is "live" — config without explicit mode works
5. Verify shadow + counterfactual disabled = silent drop (no exception, no log error, just return)
6. **Full regression check** — this is the final session. Run full test suite and verify all sprint deliverables are present.

## Sprint-Level Regression Checklist (for @reviewer — FULL CHECK, FINAL SESSION)
- [ ] All existing pytest tests pass (~3,412 + ~48 new ≈ ~3,460 ± tolerance)
- [ ] All existing Vitest tests pass (~633)
- [ ] BacktestEngine produces identical results after fill model extraction
- [ ] `_process_signal()` for live-mode strategies behaves identically to pre-sprint
- [ ] Event bus FIFO ordering preserved
- [ ] All strategies default to mode: live
- [ ] Strategy internal logic unaware of mode
- [ ] Config fields match Pydantic model names exactly
- [ ] CounterfactualStore uses `data/counterfactual.db`
- [ ] All do-not-modify files are untouched

## Sprint-Level Escalation Criteria (for @reviewer)
(see review-context.md)

# Sprint 29, Session 1: PatternParam Core + Reference Data Hook

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - `argus/strategies/patterns/base.py` (PatternModule ABC, CandleBar, PatternDetection)
   - `argus/strategies/pattern_strategy.py` (PatternBasedStrategy wrapper)
   - `argus/strategies/patterns/bull_flag.py` (reference: current `get_default_params()` return)
2. Run the test baseline:
   Full suite: `python -m pytest tests/ -x -q --timeout=30 -n auto`
   Expected: ~3,966 tests + 688 Vitest, all passing
3. Verify you are on branch `main`

## Objective
Define the PatternParam frozen dataclass, update the PatternModule ABC `get_default_params()` return type from `dict[str, Any]` to `list[PatternParam]`, and add an optional `set_reference_data()` method. This establishes the structured parameter metadata foundation for all PatternModule patterns and the reference data hook for patterns needing prior close / pre-market context.

## Requirements

1. In `argus/strategies/patterns/base.py`, add a **frozen dataclass** `PatternParam`:
   ```python
   @dataclass(frozen=True)
   class PatternParam:
       name: str                        # e.g., "pole_min_bars"
       param_type: type                 # int, float, bool
       default: Any                     # default value
       min_value: float | None = None   # numeric range minimum
       max_value: float | None = None   # numeric range maximum
       step: float | None = None        # grid step size for sweep
       description: str = ""            # human-readable
       category: str = ""               # grouping: "detection", "scoring", "filtering"
   ```

2. In `argus/strategies/patterns/base.py`, change the `get_default_params()` abstract method signature:
   - FROM: `def get_default_params(self) -> dict[str, Any]`
   - TO: `def get_default_params(self) -> list[PatternParam]`

3. In `argus/strategies/patterns/base.py`, add an optional method to PatternModule:
   ```python
   def set_reference_data(self, data: dict[str, Any]) -> None:
       """Receive reference data from Universe Manager (prior closes, etc.).
       Default no-op. Override in patterns that need external reference data."""
       pass
   ```

4. In `argus/strategies/pattern_strategy.py`, in the initialization path where the PatternBasedStrategy receives its PatternModule instance, call `self._pattern.set_reference_data(reference_data)` when UM reference data is available. This should be a conditional call — if no reference data is available, skip the call. The reference data dict should include at minimum `prior_closes: dict[str, float]` (symbol → last close price) when available from the Universe Manager's reference client.

5. Export `PatternParam` from the patterns package `__init__.py` if one exists, or ensure it's importable from `argus.strategies.patterns.base`.

## Constraints
- Do NOT modify: `core/events.py`, `execution/order_manager.py`, `core/risk_manager.py`, `ui/`, `api/`, `ai/`, `intelligence/`
- Do NOT change: `detect()`, `score()`, `name`, `lookback_bars` abstract members on PatternModule
- Do NOT change: CandleBar or PatternDetection dataclasses
- Do NOT modify Bull Flag or Flat-Top implementations (that is S2)
- The `set_reference_data()` method MUST have a default no-op implementation — it is optional for patterns to override

## Test Targets
After implementation:
- Existing tests: all must still pass (Bull Flag/Flat-Top tests may fail due to `get_default_params()` return type change — this is expected and will be fixed in S2. If they fail, note in close-out but do not fix here.)
- New tests to write:
  1. PatternParam construction with all fields
  2. PatternParam is frozen (immutable)
  3. PatternParam with param_type=int, verify min/max/step types
  4. PatternParam with param_type=float
  5. PatternParam with param_type=bool, verify min/max/step are None
  6. `set_reference_data()` default no-op does not raise
- Minimum new test count: 6
- Test command: `python -m pytest tests/strategies/patterns/ -x -q --timeout=30`

## Definition of Done
- [ ] PatternParam frozen dataclass with 8 fields in base.py
- [ ] `get_default_params()` returns `list[PatternParam]`
- [ ] `set_reference_data()` exists with default no-op
- [ ] PatternBasedStrategy calls `set_reference_data()` during init when reference data available
- [ ] PatternParam importable from `argus.strategies.patterns.base`
- [ ] 6+ new tests written and passing
- [ ] Close-out report written to file
- [ ] Tier 2 review completed via @reviewer subagent

## Regression Checklist (Session-Specific)
| Check | How to Verify |
|-------|---------------|
| PatternModule ABC still enforces 5 abstract members | `grep -n "abstractmethod" argus/strategies/patterns/base.py` — count should be 5 |
| CandleBar unchanged | `git diff argus/strategies/patterns/base.py` — no CandleBar changes |
| PatternDetection unchanged | `git diff argus/strategies/patterns/base.py` — no PatternDetection changes |
| set_reference_data is no-op by default | New test asserts no exception when called with empty dict |

## Close-Out
After all work is complete, follow the close-out skill in .claude/skills/close-out.md.

The close-out report MUST include a structured JSON appendix at the end,
fenced with ```json:structured-closeout. See the close-out skill for the
full schema and requirements.

**Write the close-out report to a file:**
docs/sprints/sprint-29/session-1-closeout.md

## Tier 2 Review (Mandatory — @reviewer Subagent)
After the close-out is written to file and committed, invoke the @reviewer
subagent to perform the Tier 2 review within this same session.

Provide the @reviewer with:
1. The review context file: `docs/sprints/sprint-29/review-context.md`
2. The close-out report path: `docs/sprints/sprint-29/session-1-closeout.md`
3. The diff range: `git diff HEAD~1`
4. The test command: `python -m pytest tests/strategies/patterns/ -x -q --timeout=30`
5. Files that should NOT have been modified: `core/events.py`, `execution/order_manager.py`, `core/risk_manager.py`, `ui/`, `api/`, `ai/`, `intelligence/`, `strategies/patterns/bull_flag.py`, `strategies/patterns/flat_top_breakout.py`

## Post-Review Fix Documentation
If the @reviewer reports CONCERNS and you fix the findings within this same
session, update both the close-out and review files per the implementation
prompt template instructions.

## Session-Specific Review Focus (for @reviewer)
1. Verify PatternParam is a frozen dataclass (not mutable)
2. Verify `get_default_params()` return type annotation is `list[PatternParam]`
3. Verify `set_reference_data()` has default no-op (pass), not abstract
4. Verify PatternBasedStrategy's reference data call is conditional (doesn't crash when no UM data)
5. Verify no changes to CandleBar, PatternDetection, detect(), score(), name, lookback_bars

## Sprint-Level Regression Checklist (for @reviewer)
See `docs/sprints/sprint-29/review-context.md` — Sprint-Level Regression Checklist section.

## Sprint-Level Escalation Criteria (for @reviewer)
See `docs/sprints/sprint-29/review-context.md` — Sprint-Level Escalation Criteria section.

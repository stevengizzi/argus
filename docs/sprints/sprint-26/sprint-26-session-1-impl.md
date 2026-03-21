# Sprint 26, Session 1: PatternModule ABC + Package

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - `argus/strategies/base_strategy.py` (BaseStrategy interface — do NOT modify)
   - `argus/core/events.py` (SignalEvent — do NOT modify)
   - `argus/intelligence/quality_engine.py` (quality engine interface — do NOT modify)
   - `docs/sprints/sprint-26/sprint-spec.md` (sprint spec)
2. Run the full test baseline (DEC-328 — Session 1):
   ```
   python -m pytest --ignore=tests/test_main.py -n auto -q
   ```
   Expected: ~2,815 tests, all passing
3. Verify you are on the correct branch: `main` (or sprint-26 branch if created)

## Objective
Create the `argus/strategies/patterns/` package with the PatternModule abstract base class, CandleBar dataclass, and PatternDetection result dataclass. This is the foundational infrastructure for all future pattern detection modules.

## Requirements

1. **Create `argus/strategies/patterns/__init__.py`:**
   - Export: `PatternModule`, `PatternDetection`, `CandleBar`
   - Brief module docstring explaining the patterns package purpose

2. **Create `argus/strategies/patterns/base.py`:**

   a. **`CandleBar` frozen dataclass:**
      - Fields: `timestamp: datetime`, `open: float`, `high: float`, `low: float`, `close: float`, `volume: float`
      - Frozen (immutable) for safety
      - No methods needed — pure data container

   b. **`PatternDetection` dataclass:**
      - Fields:
        - `pattern_type: str` (e.g., "bull_flag", "flat_top_breakout")
        - `confidence: float` (0–100, how strong the pattern match is)
        - `entry_price: float`
        - `stop_price: float`
        - `target_prices: tuple[float, ...] = ()` (pattern-derived targets, optional)
        - `metadata: dict = field(default_factory=dict)` (pattern-specific context)
      - NOT frozen (metadata dict is mutable)

   c. **`PatternModule` ABC:**
      ```python
      class PatternModule(ABC):
          """Abstract base class for pattern detection modules.

          Patterns are pure detection logic — they identify chart patterns
          in candle data and score them. They do NOT handle:
          - Operating windows (PatternBasedStrategy handles)
          - Position sizing (Quality Engine + Sizer handles)
          - State management (PatternBasedStrategy handles)
          - Signal generation (PatternBasedStrategy handles)
          """

          @property
          @abstractmethod
          def name(self) -> str:
              """Human-readable name of the pattern."""

          @property
          @abstractmethod
          def lookback_bars(self) -> int:
              """Number of recent candles needed for detection.
              PatternBasedStrategy maintains this window per symbol."""

          @abstractmethod
          def detect(
              self,
              candles: list[CandleBar],
              indicators: dict[str, float],
          ) -> PatternDetection | None:
              """Detect a pattern in the given candle window.

              Args:
                  candles: Recent candle history (most recent last),
                           length <= lookback_bars.
                  indicators: Current indicator values (vwap, atr, rvol, etc.)

              Returns:
                  PatternDetection if pattern found, None otherwise.
              """

          @abstractmethod
          def score(self, detection: PatternDetection) -> float:
              """Score the quality of a detected pattern (0–100).
              Used as pattern_strength input to Quality Engine."""

          @abstractmethod
          def get_default_params(self) -> dict:
              """Return default parameter values for this pattern.
              Used by Pattern Library UI and future BacktestEngine."""
      ```

## Constraints
- Do NOT modify `argus/strategies/base_strategy.py`
- Do NOT modify `argus/core/events.py`
- Do NOT import from `argus.core.events` — CandleBar is independent of CandleEvent
- Do NOT add any strategy execution logic — PatternModule is pure detection
- Do NOT add database persistence — pattern detections are transient
- Do NOT add Event Bus integration — patterns are internal to strategy logic

## Test Targets
After implementation:
- Existing tests: all must still pass
- New tests to write in `tests/strategies/patterns/test_pattern_base.py`:
  1. `test_pattern_module_cannot_be_instantiated` — TypeError on direct PatternModule()
  2. `test_candle_bar_creation` — valid construction with all fields
  3. `test_candle_bar_is_frozen` — FrozenInstanceError on attribute assignment
  4. `test_pattern_detection_creation` — valid construction with required + optional fields
  5. `test_pattern_detection_default_targets` — empty tuple when not specified
  6. `test_pattern_detection_with_targets` — target_prices populated correctly
  7. `test_pattern_detection_metadata_mutable` — metadata dict can be modified after creation
  8. `test_concrete_pattern_implements_interface` — create a mock concrete PatternModule subclass that implements all abstract methods, verify it instantiates and methods callable
  9. `test_score_bounds` — verify mock pattern's score returns value clamped to 0–100
  10. `test_lookback_bars_positive` — verify lookback_bars returns a positive integer
- Create `tests/strategies/patterns/__init__.py` (empty)
- Minimum new test count: 10
- Test command: `python -m pytest tests/strategies/patterns/test_pattern_base.py -x -v`

## Definition of Done
- [ ] `argus/strategies/patterns/__init__.py` created with exports
- [ ] `argus/strategies/patterns/base.py` created with CandleBar, PatternDetection, PatternModule
- [ ] PatternModule ABC enforces all 5 abstract members (name, lookback_bars, detect, score, get_default_params)
- [ ] CandleBar is frozen dataclass
- [ ] PatternDetection includes optional target_prices
- [ ] All existing tests pass
- [ ] 10 new tests written and passing
- [ ] Close-out report written to file
- [ ] Tier 2 review completed via @reviewer subagent

## Regression Checklist (Session-Specific)
| Check | How to Verify |
|-------|---------------|
| No existing files modified | `git diff --name-only HEAD` shows only new files in `argus/strategies/patterns/` and `tests/strategies/patterns/` |
| BaseStrategy unchanged | `git diff HEAD -- argus/strategies/base_strategy.py` is empty |
| events.py unchanged | `git diff HEAD -- argus/core/events.py` is empty |

## Close-Out
After all work is complete, follow the close-out skill in .claude/skills/close-out.md.

The close-out report MUST include a structured JSON appendix at the end,
fenced with ```json:structured-closeout. See the close-out skill for the
full schema and requirements.

**Write the close-out report to a file** (DEC-330):
docs/sprints/sprint-26/session-1-closeout.md

Do NOT just print the report in the terminal. Create the file, write the
full report (including the structured JSON appendix) to it, and commit it.

## Tier 2 Review (Mandatory — @reviewer Subagent)
After the close-out is written to file and committed, invoke the @reviewer
subagent to perform the Tier 2 review within this same session.

Provide the @reviewer with:
1. The review context file: `docs/sprints/sprint-26/review-context.md`
2. The close-out report path: `docs/sprints/sprint-26/session-1-closeout.md`
3. The diff range: `git diff HEAD~1`
4. The test command: `python -m pytest tests/strategies/patterns/test_pattern_base.py -x -v`
5. Files that should NOT have been modified: `argus/strategies/base_strategy.py`, `argus/core/events.py`, `argus/intelligence/quality_engine.py`

## Post-Review Fix Documentation
If the @reviewer reports CONCERNS and you fix the findings within this same
session, update both the close-out and review files per the implementation prompt template.

## Session-Specific Review Focus (for @reviewer)
1. Verify PatternModule ABC enforces all 5 abstract members — instantiating without any one should raise TypeError
2. Verify CandleBar does NOT import from argus.core.events
3. Verify no execution logic (operating windows, position sizing, signal generation) exists in patterns/base.py
4. Verify PatternDetection.confidence and score() return value are conceptually consistent (both 0-100, but confidence is detection-time assessment while score is post-detection quality assessment)

## Sprint-Level Regression Checklist
See `docs/sprints/sprint-26/review-context.md` — Regression Checklist section.

## Sprint-Level Escalation Criteria
See `docs/sprints/sprint-26/review-context.md` — Escalation Criteria section.

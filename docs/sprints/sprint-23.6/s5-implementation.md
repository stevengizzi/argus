# Sprint 23.6, Session 5: Runner Decomposition + Conformance Monitoring

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - `scripts/sprint_runner/main.py` (identify Colors, print_* functions, and argparse setup)
   - `scripts/sprint_runner/state.py` (RunState dataclass)
   - `scripts/sprint_runner/conformance.py` (conformance fallback — lines ~390-420)
2. Run the runner test suite: `python -m pytest tests/sprint_runner/ -x -q`
   Expected: 188 tests, all passing
3. Verify you are on the correct branch: `sprint-23.6`

## Objective
Extract CLI helpers from runner main.py to reduce its size by ~200 lines (S4), and add conformance fallback monitoring (S5).

## Requirements

### Part 1: CLI Extraction (S4)

1. **Create `scripts/sprint_runner/cli.py`** containing:
   - The `Colors` class (ANSI color constants)
   - `print_header(text: str)` function
   - `print_progress(...)` function
   - `print_summary_table(...)` function
   - `print_error(message: str)` function
   - `print_warning(message: str)` function
   - `print_success(message: str)` function
   - The argument parser construction (the `argparse.ArgumentParser` setup from main.py's `if __name__ == "__main__"` block or equivalent). Extract into a function:
     ```python
     def build_argument_parser() -> argparse.ArgumentParser:
     ```

2. **In `scripts/sprint_runner/main.py`**:
   - Replace the extracted classes/functions with imports from `cli.py`:
     ```python
     from .cli import Colors, print_header, print_progress, print_summary_table, print_error, print_warning, print_success, build_argument_parser
     ```
   - Remove the original definitions.
   - Verify all references in main.py still resolve to the imported names.

3. **Verification:** After extraction, main.py line count should be reduced by ~200 lines. All 188 existing runner tests must pass unchanged.

### Part 2: Conformance Fallback Monitoring (S5)

4. **In `scripts/sprint_runner/state.py`**, add to the `RunState` dataclass:
   ```python
   conformance_fallback_count: int = 0
   ```
   This persists across resume (it's in the JSON state file).

5. **In `scripts/sprint_runner/conformance.py`**, in the two places where conformance defaults to CONFORMANT on failure (around lines 392 and 409):
   - Accept `state: RunState` as a parameter to `run_check()` (or access it via the runner instance).
   - Actually, the cleaner approach: have `ConformanceChecker.run_check()` return a flag indicating whether the fallback was used. Then in `main.py`, increment the counter.
   - Alternatively, if `run_check()` already returns a `ConformanceVerdict`, add a `is_fallback: bool = False` field to `ConformanceVerdict` and set it to `True` in the fallback paths.

6. **In `scripts/sprint_runner/main.py`**, after receiving a conformance verdict:
   - If `verdict.is_fallback` (or equivalent): increment `self.state.conformance_fallback_count` and save state.
   - After all sessions complete (or at HALT), check: if `conformance_fallback_count > 2`, log WARNING:
     "Conformance check defaulted to CONFORMANT {count} times this run. Check conformance subagent reliability."

## Constraints
- Do NOT change runner execution behavior — S4 is pure refactoring
- Do NOT change conformance verdicts (CONFORMANT/DRIFT-MINOR/DRIFT-MAJOR)
- Do NOT modify any file under `argus/` — runner is in `scripts/`
- Do NOT change the runner's CLI interface (same arguments, same behavior)
- All 188 existing runner tests must pass unchanged after both changes

## Test Targets
After implementation:
- Existing tests: all 188 must pass unchanged
- New tests in `tests/sprint_runner/test_cli.py`:
  1. `test_cli_module_imports` — `from scripts.sprint_runner.cli import Colors, build_argument_parser` succeeds
  2. `test_build_argument_parser` — parser has expected arguments (--config, --sprint-dir, etc.)
  3. `test_print_functions_callable` — all print_* functions are callable without error
- New tests in `tests/sprint_runner/test_conformance.py` (or existing file):
  4. `test_conformance_fallback_sets_flag` — when conformance check fails, verdict has is_fallback=True
  5. `test_conformance_fallback_count_increments` — verify state counter increments on fallback
  6. `test_conformance_fallback_warning_threshold` — verify WARNING at count > 2
- Minimum new test count: 6
- Test command: `python -m pytest tests/sprint_runner/ -x -q`

## Definition of Done
- [ ] `scripts/sprint_runner/cli.py` created with extracted functions
- [ ] `main.py` imports from cli.py, original definitions removed
- [ ] main.py line count reduced by ~200 lines
- [ ] All 188 existing runner tests pass unchanged
- [ ] `conformance_fallback_count` field in RunState
- [ ] Fallback detection in conformance verdicts
- [ ] WARNING logged when count > 2
- [ ] 6+ new tests written and passing
- [ ] No ruff lint errors: `ruff check scripts/sprint_runner/`

## Regression Checklist (Session-Specific)
| Check | How to Verify |
|-------|---------------|
| All 188 runner tests pass | `python -m pytest tests/sprint_runner/ -x -q` (count must be ≥188) |
| Runner CLI works | `python scripts/sprint-runner.py --help` exits 0 |
| No changes to argus/ | `git diff HEAD -- argus/` empty |
| main.py line count reduced | `wc -l scripts/sprint_runner/main.py` shows ~1,987 or less (was 2,187) |

## Close-Out
After all work is complete, follow the close-out skill in .claude/skills/close-out.md.
The close-out report MUST include a structured JSON appendix at the end, fenced with ```json:structured-closeout.

## Sprint-Level Regression Checklist (for Tier 2 reviewer)
See `sprint-23.6/review-context.md`.

## Sprint-Level Escalation Criteria (for Tier 2 reviewer)
See `sprint-23.6/review-context.md`.

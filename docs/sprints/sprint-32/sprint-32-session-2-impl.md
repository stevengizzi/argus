# Sprint 32, Session 2: Pattern Factory + Parameter Fingerprint

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - `argus/strategies/patterns/base.py` (PatternModule ABC, PatternParam)
   - `argus/core/config.py` (StrategyConfig base + pattern config classes — verify S1 fields present)
   - `argus/strategies/patterns/bull_flag.py` (constructor signature reference)
   - `argus/strategies/patterns/abcd.py` (constructor signature reference — most params)
2. Run the test baseline (DEC-328 — Session 2+):
   Scoped: `python -m pytest tests/test_config_param_alignment.py -v`
   Expected: all passing (full suite confirmed by S1 close-out)
3. Verify you are on branch: `sprint-32`
4. Verify Session 1 changes are committed (28 new config fields present)

## Objective
Create the generic pattern factory and parameter fingerprint utility. Both are pure functions with no side effects — the factory constructs any PatternModule from its Pydantic config using PatternParam introspection, and the fingerprint computes a deterministic hash of detection parameters.

## Requirements

1. Create `argus/strategies/patterns/factory.py` with:

   a. **Pattern class registry** — a dict mapping pattern class names to import paths:
      ```python
      _PATTERN_REGISTRY: dict[str, tuple[str, str]] = {
          "BullFlagPattern": ("argus.strategies.patterns.bull_flag", "BullFlagPattern"),
          "FlatTopBreakoutPattern": ("argus.strategies.patterns.flat_top_breakout", "FlatTopBreakoutPattern"),
          "DipAndRipPattern": ("argus.strategies.patterns.dip_and_rip", "DipAndRipPattern"),
          "HODBreakPattern": ("argus.strategies.patterns.hod_break", "HODBreakPattern"),
          "GapAndGoPattern": ("argus.strategies.patterns.gap_and_go", "GapAndGoPattern"),
          "ABCDPattern": ("argus.strategies.patterns.abcd", "ABCDPattern"),
          "PreMarketHighBreakPattern": ("argus.strategies.patterns.premarket_high_break", "PreMarketHighBreakPattern"),
      }
      ```
      Also support snake_case lookup keys (e.g., "bull_flag" → "BullFlagPattern") for convenience.

   b. **`get_pattern_class(name: str) -> type[PatternModule]`** — resolve a pattern name (class name or snake_case) to the actual class via lazy import. Raises `ValueError` for unknown patterns.

   c. **`extract_detection_params(config: StrategyConfig, pattern_class: type[PatternModule]) -> dict[str, Any]`** — instantiate the pattern with defaults, call `get_default_params()`, collect `PatternParam.name` values, extract matching fields from the Pydantic config object. Return dict of `{param_name: config_value}`. Log WARNING for any PatternParam name not found in config (forward compat — pattern has a param the config doesn't know about yet).

   d. **`build_pattern_from_config(config: StrategyConfig, pattern_name: str | None = None) -> PatternModule`** — resolve pattern class (from `pattern_name` arg or `config.pattern_class` field if present, or infer from config class name), extract detection params, construct and return the pattern instance. This is the main public API.

   e. **`compute_parameter_fingerprint(config: StrategyConfig, pattern_class: type[PatternModule]) -> str`** — extract detection params, sort by key, serialize to canonical JSON string, compute SHA-256 hash, return first 16 hex chars. Must be deterministic: same config → same hash across process restarts. Non-detection params (strategy_id, name, operating_window, etc.) must NOT affect the hash.

2. Write comprehensive tests in `tests/strategies/patterns/test_factory.py`:
   - Factory constructs all 7 patterns from default configs
   - Factory constructs with non-default param values and verifies propagation
   - Factory raises ValueError for unknown pattern name
   - `extract_detection_params` returns only detection params, not base StrategyConfig fields
   - Fingerprint: identical configs → identical hash
   - Fingerprint: different detection param → different hash
   - Fingerprint: different non-detection param (e.g., strategy_id) → same hash
   - Fingerprint: deterministic (call twice → same result)
   - Snake_case name resolution works (e.g., "bull_flag" → BullFlagPattern)

## Constraints
- Do NOT modify any existing files — this session only creates new files
- Do NOT import any non-standard library for hashing (use `hashlib` from stdlib)
- Do NOT hardcode parameter names in the factory — use PatternParam introspection exclusively
- The factory must work for any future PatternModule pattern that follows the ABC + PatternParam contract

## Test Targets
After implementation:
- Existing tests: all must still pass
- New tests: `tests/strategies/patterns/test_factory.py`
- Minimum new test count: 10
- Test command: `python -m pytest tests/strategies/patterns/test_factory.py -v`

## Definition of Done
- [ ] `factory.py` created with all 5 public functions
- [ ] All existing tests pass
- [ ] Factory tests pass for all 7 patterns
- [ ] Fingerprint determinism verified
- [ ] Close-out report written to file
- [ ] Tier 2 review completed via @reviewer subagent

## Regression Checklist (Session-Specific)

| Check | How to Verify |
|-------|---------------|
| R3: Constructor defaults unchanged | Factory with default config produces pattern with same defaults as `SomePattern()` |
| R14: Fingerprint deterministic | Test calls fingerprint twice, asserts equal |
| No existing files modified | `git diff --name-only` shows only new files + test files |

## Close-Out
After all work is complete, follow the close-out skill in .claude/skills/close-out.md.
**Write the close-out report to:** docs/sprints/sprint-32/session-2-closeout.md

## Tier 2 Review (Mandatory — @reviewer Subagent)
Provide the @reviewer with:
1. Review context file: `docs/sprints/sprint-32/review-context.md`
2. Close-out report: `docs/sprints/sprint-32/session-2-closeout.md`
3. Diff range: `git diff HEAD~1`
4. Test command: `python -m pytest tests/strategies/patterns/test_factory.py -v`
5. Files that should NOT have been modified: `main.py`, `config.py`, any pattern `.py` file, `vectorbt_pattern.py`

## Post-Review Fix Documentation
If @reviewer reports CONCERNS, fix and update both close-out and review files per protocol.

## Session-Specific Review Focus (for @reviewer)
1. Verify factory uses PatternParam introspection — no hardcoded parameter lists
2. Verify fingerprint excludes non-detection fields (strategy_id, name, operating_window, etc.)
3. Verify fingerprint uses sorted keys and canonical JSON for determinism
4. Verify lazy imports in registry (patterns not imported at module level)
5. Verify `extract_detection_params` handles the case where a PatternParam name doesn't exist on the config (logs warning, skips)

## Sprint-Level Regression Checklist (for @reviewer)
See `docs/sprints/sprint-32/review-context.md`

## Sprint-Level Escalation Criteria (for @reviewer)
See `docs/sprints/sprint-32/review-context.md`

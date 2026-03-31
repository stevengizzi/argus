# Sprint 29, Session 8: Integration Verification + Smoke Backtests

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - Orchestrator config (system.yaml or system_live.yaml — whichever registers strategies)
   - `config/exit_management.yaml` (verify all 5 new pattern overrides present)
   - All new pattern configs: `config/strategies/{dip_and_rip,hod_break,gap_and_go,abcd,premarket_high_break}.yaml`
   - All new filter configs: `config/universe_filters/{dip_and_rip,hod_break,gap_and_go,abcd,premarket_high_break}.yaml`
2. Run the FULL test suite:
   `python -m pytest tests/ -x -q --timeout=30 -n auto`
   Expected: ~4,040+ tests, all passing (S1–S7 cumulative)
   Also run: `cd argus/ui && npx vitest run --reporter=verbose 2>&1 | tail -20`
   Expected: 680 tests, all passing
3. Verify you are on branch `main`

## Objective
Final verification session. Confirm all 5 new patterns (or 4 if PM High Break was skipped) load correctly in the full system, configs parse without error, universe filters route correctly, exit overrides apply, and smoke backtests produce reasonable results. This session produces NO new code in the success path — only tests and verification. Fixes are permitted only if issues are discovered, and must be documented.

## Requirements

### 1. System Startup Verification
Write or run a test that:
- Initializes the orchestrator with all strategies enabled
- Verifies all 12 (or 11) strategies load without error
- Verifies each new strategy has a non-empty watchlist after UM routing (or document if UM is not part of this test — in which case verify strategy registration only)
- Verifies no strategy ID collisions

### 2. Config Parse Verification
For each new pattern, verify:
- Strategy YAML loads via Pydantic model without warnings or ignored keys
- Universe filter YAML loads and all custom fields (min_relative_volume, min_gap_percent, min_premarket_volume) are recognized
- Exit management override loads and deep_update produces the expected merged config
- Run these as automated tests

### 3. Cross-Pattern Integration Checks
- Verify Quality Engine can process a simulated signal from each new pattern (share_count=0 path)
- Verify Risk Manager Check 0 rejects share_count ≤ 0 signals from new patterns (standard pipeline)
- Verify new patterns emit `_calculate_pattern_strength()` returning 0–100
- Verify CounterfactualTracker subscription handles new strategy IDs

### 4. Smoke Backtests
Run PatternBacktester (or BacktestEngine if more appropriate) on each new pattern:
- **Symbols:** AAPL, MSFT, NVDA, TSLA, META (liquid, likely to have patterns)
- **Period:** 6 months (use Parquet cache in `data/databento_cache`)
- **Expectation:** Completes without error. Some patterns may produce zero detections on this symbol set — that's a warning, not a failure. Document detection counts per pattern.
- **Command:** Use existing PatternBacktester CLI or write a simple script. Document the exact command in the close-out.

### 5. Full Regression Run
- Run the complete pytest suite with `-n auto`
- Run the complete Vitest suite
- Verify zero failures across both
- Document final test counts in close-out

### 6. Fix Any Issues Found
If verification reveals issues:
- Fix them within this session
- Document each fix in the close-out with: what was wrong, what was fixed, which session introduced the bug
- Each fix must be a separate commit for traceability

## Constraints
- Do NOT modify any pattern implementations unless a bug is found during verification
- Do NOT modify: `core/events.py`, `execution/order_manager.py`, `ui/`, `api/`, `ai/`
- Do NOT add new features — this is verification only
- If a pattern produces zero smoke backtest detections, do NOT tune parameters — just document

## Test Targets
- New integration tests: ~10
  1. All strategies load at startup
  2. Per-pattern config parse (×5)
  3. Per-pattern filter route verification
  4. Exit override merge verification
  5. Cross-strategy: no ID collisions
  6. Cross-strategy: all emit pattern_strength 0–100
- Test command (final): `python -m pytest tests/ -x -q --timeout=30 -n auto`
- Vitest command: `cd argus/ui && npx vitest run --reporter=verbose`

## Definition of Done
- [ ] All 12 (or 11) strategies load at startup without error
- [ ] All config YAMLs parse correctly via Pydantic
- [ ] All universe filter custom fields are recognized (not silently ignored)
- [ ] All exit overrides apply correctly
- [ ] Smoke backtest completes for each new pattern (document detection counts)
- [ ] Quality Engine / Risk Manager / Counterfactual pipeline works for new patterns
- [ ] Full pytest suite: 0 failures
- [ ] Full Vitest suite: 0 failures
- [ ] Any bugs found are documented with fix + origin session
- [ ] Close-out report written to file
- [ ] Tier 2 review completed via @reviewer subagent

## Regression Checklist (Session-Specific)
| Check | How to Verify |
|-------|---------------|
| ALL pre-existing tests pass | `python -m pytest tests/ -x -q --timeout=30 -n auto` — 0 failures |
| ALL Vitest pass | `cd argus/ui && npx vitest run` — 0 failures |
| No existing strategy behavior changed | Existing strategy tests all pass |
| No "Do not modify" files touched | `git diff --stat` — verify file list |

## Close-Out
Follow the close-out skill in .claude/skills/close-out.md.

The close-out report MUST include a structured JSON appendix at the end,
fenced with ```json:structured-closeout.

**Write the close-out report to a file:**
docs/sprints/sprint-29/session-8-closeout.md

**Additional close-out requirements for this final session:**
- Include final test counts: pytest total + Vitest total
- Include smoke backtest results table: pattern name, symbols tested, detection count, notes
- Include list of any bugs found and fixed (with origin session)
- Include total new test count for the sprint (sum across all sessions)

## Tier 2 Review (Mandatory — @reviewer Subagent)
This is the FINAL session of the sprint. The reviewer should run the full suite.

1. Review context: `docs/sprints/sprint-29/review-context.md`
2. Close-out: `docs/sprints/sprint-29/session-8-closeout.md`
3. Diff: `git diff sprint-29-start..HEAD` (or appropriate range covering all sprint work)
4. Test: `python -m pytest tests/ -x -q --timeout=30 -n auto` (FULL SUITE — final session)
5. Do not modify: `core/events.py`, `execution/order_manager.py`, `ui/`, `api/`, `ai/`

## Session-Specific Review Focus (for @reviewer)
1. Verify all 12 (or 11) strategies are registered and load
2. Verify no "Do not modify" files were touched across the entire sprint
3. Verify smoke backtest detection counts are documented (even if zero)
4. Verify any bugs fixed in this session are traced to origin session
5. Spot-check 2–3 patterns: verify detect/score/get_default_params are consistent
6. Verify total sprint test delta is reasonable (~90 new tests expected)

## Sprint-Level Regression Checklist (for @reviewer)
See `docs/sprints/sprint-29/review-context.md` — run the FULL checklist for the final review.

## Sprint-Level Escalation Criteria (for @reviewer)
See `docs/sprints/sprint-29/review-context.md`

# Sprint 29, Session 6b: ABCD Config + Wiring + Integration

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - `argus/strategies/patterns/abcd.py` (S6a output — the ABCD pattern implementation)
   - `argus/strategies/pattern_strategy.py` (wrapper)
   - `config/exit_management.yaml` (current structure)
   - Any existing strategy YAML in `config/strategies/` for reference
2. Run the scoped test baseline:
   `python -m pytest tests/strategies/patterns/ -x -q --timeout=30`
   Expected: all passing (including S6a's ABCD tests)
3. Verify you are on branch `sprint-29`

## Objective
Create ABCD strategy config, universe filter, exit management override, and register the strategy. Run a smoke backtest to verify end-to-end functionality. This is the lightweight wiring session after S6a's algorithm work.

## Requirements

### 1. Strategy Config: `config/strategies/abcd.yaml`
```yaml
pattern_class: "ABCDPattern"
operating_window:
  start: "10:00"
  end: "15:00"
allowed_regimes:
  - bullish_trending
  - bearish_trending
  - neutral
  - high_volatility
mode: "live"
```

### 2. Universe Filter: `config/universe_filters/abcd.yaml`
```yaml
min_price: 10.0
max_price: 300.0
min_avg_volume: 500000
```

### 3. Exit Management Override
Add to `config/exit_management.yaml`:
```yaml
abcd:
  trailing_stop:
    enabled: true
    mode: "atr"
    atr_multiplier: 2.5
    activation_r: 1.0
  partial_profit:
    enabled: true
    targets:
      - r_multiple: 1.5
        percent: 50
  time_escalation:
    enabled: true
    phases:
      - after_minutes: 60
        tighten_stop_percent: 20
      - after_minutes: 90
        action: "flatten"
```

### 4. Strategy Registration
Register ABCD in orchestrator/system config.

### 5. Smoke Backtest
Run PatternBacktester on ABCD with 5 symbols × 6 months. This is a sanity check — verify:
- The backtest completes without error
- ABCD detection fires at least once (if zero detections in 5 symbols, note in close-out as a warning — may indicate thresholds are too strict for the test data)
- Results are non-degenerate

Use liquid, trending symbols for the smoke test (e.g., AAPL, MSFT, NVDA, TSLA, META — these are likely to have ABCD patterns in 6 months of data).

## Constraints
- Do NOT modify: `abcd.py` (locked after S6a — if bugs found, document in close-out for fix session)
- Do NOT modify: `base.py`, `pattern_strategy.py`, existing patterns, `core/`, `execution/`, `ui/`, `api/`

## Test Targets
1. ABCD config YAML parses without error
2. Universe filter routes symbols correctly (min_price 10.0 check)
3. Exit override merges correctly via deep_update
4. ABCD loads at startup via orchestrator
5. Integration: ABCD pattern receives candles through PatternBasedStrategy wrapper
6. Smoke backtest completes (may be test or manual CLI run — document approach)
- Minimum new test count: 6
- Test command: `python -m pytest tests/strategies/patterns/ -x -q --timeout=30`

## Definition of Done
- [ ] Config, filter, exit override all parse correctly
- [ ] ABCD registered and loads at startup
- [ ] Smoke backtest completes (even if zero detections — document)
- [ ] 6+ new tests passing
- [ ] Close-out report written to file
- [ ] Tier 2 review completed via @reviewer subagent

## Regression Checklist (Session-Specific)
| Check | How to Verify |
|-------|---------------|
| abcd.py unchanged | `git diff argus/strategies/patterns/abcd.py` — empty |
| Exit management existing entries preserved | Only additions in diff |

## Close-Out
Follow the close-out skill in .claude/skills/close-out.md.

The close-out report MUST include a structured JSON appendix at the end,
fenced with ```json:structured-closeout.

**Write the close-out report to a file:**
docs/sprints/sprint-29/session-6b-closeout.md

## Tier 2 Review (Mandatory — @reviewer Subagent)
1. Review context: `docs/sprints/sprint-29/review-context.md`
2. Close-out: `docs/sprints/sprint-29/session-6b-closeout.md`
3. Diff: `git diff HEAD~1`
4. Test: `python -m pytest tests/strategies/patterns/ -x -q --timeout=30`
5. Do not modify: `abcd.py`, `base.py`, `pattern_strategy.py`, existing patterns, `core/`, `execution/`, `ui/`, `api/`

## Session-Specific Review Focus (for @reviewer)
1. Verify ABCD config uses correct pattern_class string
2. Verify exit override structure matches ExitManagementConfig schema
3. Verify strategy registration follows existing pattern exactly
4. Note smoke backtest results in review (zero detections = warning, not failure)

## Sprint-Level Regression Checklist / Escalation Criteria
See `docs/sprints/sprint-29/review-context.md`

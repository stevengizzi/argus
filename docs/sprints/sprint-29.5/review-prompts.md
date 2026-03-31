# Sprint 29.5 — Tier 2 Review Prompts (Fallback)

> These are fallback review prompts per the workflow template. Primary path is
> @reviewer subagent invocation at the end of each implementation session.

---

## Tier 2 Review: Sprint 29.5, Session 1

### Instructions
You are conducting a Tier 2 code review. This is a READ-ONLY session.
Do NOT modify any source code files.
Follow the review skill in .claude/skills/review.md.
Write the review report to: `docs/sprints/sprint-29.5/session-1-review.md`

### Review Context
Read: `docs/sprints/sprint-29.5/review-context.md`

### Tier 1 Close-Out Report
Read: `docs/sprints/sprint-29.5/session-1-closeout.md`

### Review Scope
- Diff: `git diff HEAD~1`
- Test command: `python -m pytest tests/execution/ -x -q`
- Files NOT modified: `argus/intelligence/`, `argus/backtest/`, `argus/strategies/patterns/`

### Session-Specific Review Focus
1. Verify error 404 detection does NOT interfere with normal SELL order flow
2. Verify circuit breaker `_flatten_abandoned` is cleared by EOD flatten
3. Verify EOD broker-only flatten does NOT close broker-confirmed positions
4. Verify startup queue drain only fires once
5. Verify `_flatten_unknown_position` correctly queues vs executes based on market hours
6. Verify no new race conditions between flatten retry, circuit breaker, and EOD flatten

---

## Tier 2 Review: Sprint 29.5, Session 2

### Instructions
READ-ONLY review. Write to: `docs/sprints/sprint-29.5/session-2-review.md`

### Review Context
Read: `docs/sprints/sprint-29.5/review-context.md`

### Tier 1 Close-Out Report
Read: `docs/sprints/sprint-29.5/session-2-closeout.md`

### Review Scope
- Diff: `git diff HEAD~1`
- Test command: `python -m pytest tests/core/test_orchestrator.py tests/core/test_throttle.py -x -q`
- Files NOT modified: `argus/intelligence/`, `argus/execution/`, `argus/strategies/`

### Session-Specific Review Focus
1. Verify throttler bypass is config-gated, not hard-coded
2. Verify pre-live checklist updated with all changed values
3. Verify risk limit changes are value-only (no structural changes to RiskManager)

---

## Tier 2 Review: Sprint 29.5, Session 3

### Instructions
READ-ONLY review. Write to: `docs/sprints/sprint-29.5/session-3-review.md`

### Review Context
Read: `docs/sprints/sprint-29.5/review-context.md`

### Tier 1 Close-Out Report
Read: `docs/sprints/sprint-29.5/session-3-closeout.md`

### Review Scope
- Diff: `git diff HEAD~1`
- Test command: `cd argus/ui && npx vitest run`
- Files NOT modified: `argus/execution/`, `argus/core/`, `argus/intelligence/`

### Session-Specific Review Focus
1. Verify win_rate multiplication is at display layer only — backend unchanged
2. Verify no OTHER formatPercentRaw calls broken by the pattern change
3. Verify Shares column uses `shares_remaining` not `shares_total`
4. Verify Trail badge abbreviation applied in both OpenPositions and TradeTable

### Visual Review
1. Trades page Win Rate: Shows "39.5%" style, NOT "0.39%"
2. Dashboard Today's Stats: Matches Trades page percentage
3. Trades table: Can scroll past 250 rows
4. Open Positions: Shares column visible on desktop
5. Exit badges: "trailing_stop" shows "Trail"

---

## Tier 2 Review: Sprint 29.5, Session 4

### Instructions
READ-ONLY review. Write to: `docs/sprints/sprint-29.5/session-4-review.md`

### Review Context
Read: `docs/sprints/sprint-29.5/review-context.md`

### Tier 1 Close-Out Report
Read: `docs/sprints/sprint-29.5/session-4-closeout.md`

### Review Scope
- Diff: `git diff HEAD~1`
- Test command: `cd argus/ui && npx vitest run`
- Files NOT modified: `argus/api/`, `argus/core/`, `argus/execution/`

### Session-Specific Review Focus
1. Verify WS hook properly handles reconnection/disconnection
2. Verify cache update is additive (merge), not destructive (replace)
3. Verify no race condition between WS update and REST refetch
4. Verify WS message format matches backend PositionUpdatedEvent serialization

### Visual Review
1. Dashboard positions P&L updates within 1-2 seconds
2. No table flickering on WS updates
3. Positions still load correctly on fresh page load (REST path)

---

## Tier 2 Review: Sprint 29.5, Session 5

### Instructions
READ-ONLY review. Write to: `docs/sprints/sprint-29.5/session-5-review.md`

### Review Context
Read: `docs/sprints/sprint-29.5/review-context.md`

### Tier 1 Close-Out Report
Read: `docs/sprints/sprint-29.5/session-5-closeout.md`

### Review Scope
- Diff: `git diff HEAD~1`
- Test command: `python -m pytest tests/execution/ tests/core/test_risk_manager.py -x -q`
- Files NOT modified: `argus/intelligence/`, `argus/strategies/`, `argus/analytics/`

### Session-Specific Review Focus
1. Verify error 404 is still visible in logs (not accidentally muted by ib_async level change)
2. Verify ThrottledLogger usage matches existing patterns in codebase
3. Verify shutdown task cancellation happens AFTER debrief export completes
4. Verify no aiohttp sessions left unclosed

---

## Tier 2 Review: Sprint 29.5, Session 6

### Instructions
READ-ONLY review. Write to: `docs/sprints/sprint-29.5/session-6-review.md`

### Review Context
Read: `docs/sprints/sprint-29.5/review-context.md`

### Tier 1 Close-Out Report
Read: `docs/sprints/sprint-29.5/session-6-closeout.md`

### Review Scope
- Diff: `git diff HEAD~1`
- Test command: `python -m pytest tests/execution/test_order_manager.py tests/analytics/ -x -q`
- Files NOT modified: `argus/intelligence/`, `argus/backtest/`, `argus/strategies/`

### Session-Specific Review Focus
1. Verify MFE/MAE computation is O(1) — no loops or DB queries in tick handler
2. Verify R-multiple uses `original_stop_price`, not current trail stop
3. Verify zero-risk guard (entry == stop) doesn't cause division by zero
4. Verify DB migration is additive (ALTER TABLE ADD COLUMN), not destructive
5. Verify debrief export includes MFE/MAE and handles NULL for legacy trades

---

## Tier 2 Review: Sprint 29.5, Session 7 (FINAL)

### Instructions
READ-ONLY review. Write to: `docs/sprints/sprint-29.5/session-7-review.md`

### Review Context
Read: `docs/sprints/sprint-29.5/review-context.md`

### Tier 1 Close-Out Report
Read: `docs/sprints/sprint-29.5/session-7-closeout.md`

### Review Scope
- Diff: `git diff HEAD~1`
- Test command (FULL SUITE — final session): `python -m pytest --ignore=tests/test_main.py -n auto -q`
- Files NOT modified: `argus/intelligence/learning/`, `argus/backtest/`, `argus/analytics/evaluation.py`, `argus/strategies/patterns/`

### Session-Specific Review Focus
1. Verify ClassVar pattern doesn't create test isolation issues
2. Verify exclusion flag set BEFORE strategy instances created in main.py
3. Verify both ORB strategies can independently fire on same symbol when disabled
4. Verify `_orb_family_triggered_symbols` NOT populated when exclusion disabled

### Sprint-Level Final Review
Since this is the final session, also verify:
- All 10 regression invariants from review-context.md
- Full test suite passes (4178+ pytest, 689 Vitest)
- No files in "do not modify" list were touched across entire sprint
- All new config fields have defaults preserving prior behavior
- Pre-live checklist updated with all paper-trading overrides

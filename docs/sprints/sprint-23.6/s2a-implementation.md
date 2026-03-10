# Sprint 23.6, Session 2a: Event & Source Fixes

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - `argus/core/events.py` (search for `CatalystEvent`)
   - `argus/intelligence/sources/sec_edgar.py`
   - `argus/intelligence/config.py`
2. Run the test suite: `python -m pytest tests/intelligence/ tests/core/ -x -q`
   Expected: all passing
3. Verify you are on the correct branch: `sprint-23.6`

## Objective
Fix two Tier 3 review findings: change CatalystEvent default timezone from UTC to ET (C3), and add SEC EDGAR email validation at startup (S6).

## Requirements

1. **In `argus/core/events.py`**, change CatalystEvent default factories:
   - Current: `published_at: datetime = field(default_factory=lambda: datetime.now(UTC))`
   - Change to: `published_at: datetime = field(default_factory=lambda: datetime.now(ZoneInfo("America/New_York")))`
   - Same for `classified_at`.
   - Add `from zoneinfo import ZoneInfo` at the top of the file if not already present.
   - Add a comment: `# ET per DEC-276 (intelligence layer convention)`

2. **In `argus/intelligence/sources/sec_edgar.py`**, add validation in `start()`:
   - Before any HTTP session creation, check `self._config.user_agent_email`.
   - If empty string (after strip): raise `ValueError("SEC EDGAR source enabled but user_agent_email is empty. Set catalyst.sources.sec_edgar.user_agent_email in config.")`
   - If non-empty: proceed as normal.

## Constraints
- Do NOT modify any file except `argus/core/events.py` and `argus/intelligence/sources/sec_edgar.py`
- Do NOT change the CatalystEvent field names or types — only the default factories
- Do NOT change any other Event class in events.py
- Do NOT modify the SEC EDGAR `fetch_catalysts()` or any other method besides `start()`

## Test Targets
After implementation:
- Existing tests: all must still pass
- New tests:
  1. `test_catalyst_event_defaults_et` — `CatalystEvent()` with no args produces ET-aware datetimes
  2. `test_catalyst_event_explicit_override` — explicit timestamp still works (no regression)
  3. `test_sec_edgar_start_empty_email_raises` — `start()` with `user_agent_email=""` raises ValueError
  4. `test_sec_edgar_start_whitespace_email_raises` — `start()` with `user_agent_email="  "` raises ValueError
  5. `test_sec_edgar_start_valid_email_succeeds` — `start()` with valid email does not raise
- Minimum new test count: 5
- Test command: `python -m pytest tests/intelligence/test_sources/test_sec_edgar.py tests/core/test_events.py -x -q`
  (Create `tests/core/test_events.py` if it doesn't exist for the CatalystEvent tests, or add to an existing events test file.)

## Definition of Done
- [ ] CatalystEvent defaults are ET, not UTC
- [ ] SEC EDGAR start() validates email
- [ ] All existing tests pass
- [ ] 5+ new tests written and passing
- [ ] No ruff lint errors

## Regression Checklist (Session-Specific)
| Check | How to Verify |
|-------|---------------|
| CatalystEvent defaults are ET | `python -c "from argus.core.events import CatalystEvent; e = CatalystEvent(); print(e.published_at.tzinfo)"` shows ET |
| Existing event tests pass | `python -m pytest tests/core/ -x -q` |
| No changes to protected files | `git diff HEAD -- argus/strategies/ argus/execution/ argus/ai/ argus/ui/` empty |

## Close-Out
After all work is complete, follow the close-out skill in .claude/skills/close-out.md.

The close-out report MUST include a structured JSON appendix at the end,
fenced with ```json:structured-closeout. See the close-out skill for the
full schema and requirements.

## Sprint-Level Regression Checklist (for Tier 2 reviewer)
See `sprint-23.6/review-context.md` — Regression Checklist section.

## Sprint-Level Escalation Criteria (for Tier 2 reviewer)
See `sprint-23.6/review-context.md` — Escalation Criteria section.

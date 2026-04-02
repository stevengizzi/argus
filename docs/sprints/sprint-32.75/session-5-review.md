# Tier 2 Review: Sprint 32.75, Session 5 — Operational Fixes + IBC Guide

---BEGIN-REVIEW---

## Summary

Session 5 delivered all 6 spec requirements: overflow capacity raised to 60, post-reconnect 3s delay with retry logic in `_reconnect()`, window summary logging infrastructure on `BaseStrategy`, stop retry analysis documented, IBC setup guide, and launchd plist template. 9 new tests added (spec minimum: 5). All 150 scoped tests pass.

## Test Results

```
Scoped suite: tests/execution/test_ibkr_broker.py + test_ibkr_errors.py
              + tests/strategies/test_base_strategy.py
              + tests/test_overflow_routing.py
Result: 150 passed, 0 failed, 3 warnings (2.58s)
New tests: 9
```

## Spec Compliance

| Requirement | Status | Notes |
|-------------|--------|-------|
| overflow.yaml broker_capacity=60 | PASS | Single-line value change, no Pydantic model update needed |
| ibkr_broker.py _reconnect() 3s delay | PASS | `asyncio.sleep(3.0)` after `connect()`, before portfolio query |
| ibkr_broker.py retry-once on empty positions | PASS | Correct: checks `len(post_positions)==0 and len(pre_positions)>0`, retries after 2s |
| Delay only on portfolio query, not orders | PASS | Both sleeps are inside `_reconnect()` which is only the reconnection flow; order methods (`place_order`, `place_bracket_order`) are separate code paths |
| base_strategy.py window summary logging | PASS | `_log_window_summary()`, `_maybe_log_window_summary()`, 3 tracking helpers, all counters reset in `reset_daily_state()` |
| Stop retry analysis | PASS | Documented in close-out; attributes 42 flattens to paper trading repricing storm + EOD mass flatten; no code change warranted |
| IBC guide (docs/ibc-setup.md) | PASS | 8 sections: prereqs, download, config.ini, credentials, launchd, verification, security, troubleshooting, upgrading |
| launchd plist template | PASS | `<REPLACE:...>` placeholders, no real credentials, RunAtLoad+KeepAlive+ThrottleInterval=30 |
| Minimum 5 new tests | PASS | 9 new tests added |

## Constraint Compliance

| Constraint | Status |
|------------|--------|
| Order Manager NOT modified | PASS |
| Risk Manager NOT modified | PASS |
| Event Bus NOT modified | PASS |
| Broker-confirmed position tracking (DEC-369) NOT modified | PASS |
| Reconnection attempt logic itself NOT modified | PASS — only additions after `connect()` returns |
| No real credentials committed | PASS |

## Findings

**F1 (NOTE): Cross-session file contamination in working tree.** `argus/api/routes/__init__.py` is modified (adding arena_router import) and `argus/api/routes/arena.py` exists as an untracked file. These are from Session 6 (Arena REST endpoints), not Session 5. The close-out report correctly does not mention these files in its change manifest. This is a working-tree hygiene issue, not a Session 5 defect — the S5 changes are correctly scoped. However, this means the working tree contains uncommitted changes from multiple sessions simultaneously.

**F2 (NOTE): Judgment call on `_managed_positions` vs `pre_positions`.** The spec referenced `self._managed_positions` as the pre-disconnect indicator, but `IBKRBroker` has no such attribute. The implementation correctly used `pre_positions` (derived from `_last_known_positions` at the top of `_reconnect()`), which is the semantically correct substitute. Close-out documented this judgment call transparently.

**F3 (NOTE): Window summary not wired into subclasses.** The `_maybe_log_window_summary()` and tracking helpers are added to `BaseStrategy` but no existing strategy subclass calls them. This is explicitly acknowledged in the close-out as a scope decision (RULE-001 — not modifying subclasses outside spec scope). The infrastructure is available for adoption in a future session.

**F4 (NOTE): `_maybe_log_window_summary` time parsing is simple `split(":")` without validation.** If `latest_entry` were ever set to an invalid format, `int(x)` would raise `ValueError` at runtime. The `OperatingWindow` Pydantic model uses a plain `str` field with default `"11:30"`, so there is no schema-level validation of the HH:MM format. This is a pre-existing concern with the config model, not introduced by this session. Low risk since all existing configs use valid HH:MM.

## Session-Specific Review Focus Answers

1. **Reconnect delay only on portfolio snapshot query?** Confirmed. Both `asyncio.sleep(3.0)` and the retry `asyncio.sleep(2.0)` are inside the `_reconnect()` method's position verification block, which only executes during reconnection. Order submission methods are entirely separate code paths.

2. **Window summary counters reset daily?** Confirmed. All 5 fields (`_window_symbols_evaluated`, `_window_signals_generated`, `_window_signals_rejected`, `_window_rejection_reasons`, `_window_summary_logged`) are reset in `reset_daily_state()`. Test `test_reset_daily_state_clears_window_counters` verifies this.

3. **IBC guide contains no real credentials?** Confirmed. Uses `${IBKR_USERNAME}` / `${IBKR_PASSWORD}` env var syntax in config.ini examples, `<REPLACE:...>` placeholders in plist, and `"your_ibkr_username"` / `"your_ibkr_password"` in the `.env` example.

4. **Overflow config: value change only?** Confirmed. Single-line change from `30` to `60`. No Pydantic model changes needed — `OverflowConfig.broker_capacity` is an `int` field that accepts any integer value.

## Verdict

All 6 spec requirements met. All constraints respected. 9 new tests, all passing. No blockers, no regressions. Findings are informational only.

---END-REVIEW---

```json:structured-verdict
{
  "verdict": "CLEAR",
  "findings": [
    {
      "id": "F1",
      "severity": "NOTE",
      "description": "Cross-session file contamination: argus/api/routes/__init__.py modified by S6 arena work, not S5. Working-tree hygiene issue only.",
      "file": "argus/api/routes/__init__.py"
    },
    {
      "id": "F2",
      "severity": "NOTE",
      "description": "Judgment call: spec referenced _managed_positions but IBKRBroker uses _last_known_positions. Correct substitute; documented in close-out.",
      "file": "argus/execution/ibkr_broker.py"
    },
    {
      "id": "F3",
      "severity": "NOTE",
      "description": "Window summary helpers exist on BaseStrategy but no subclass calls them yet. Intentional scope boundary per RULE-001.",
      "file": "argus/strategies/base_strategy.py"
    },
    {
      "id": "F4",
      "severity": "NOTE",
      "description": "latest_entry time parsing uses split(':') without format validation. Pre-existing config model gap, not introduced by S5.",
      "file": "argus/strategies/base_strategy.py"
    }
  ],
  "tests": {
    "command": "python -m pytest tests/execution/test_ibkr_broker.py tests/execution/test_ibkr_errors.py tests/strategies/test_base_strategy.py tests/test_overflow_routing.py -x -q",
    "passed": 150,
    "failed": 0,
    "new_tests": 9
  },
  "escalation_triggers": [],
  "close_out_self_assessment": "CLEAN",
  "reviewer_assessment": "CLEAR"
}
```

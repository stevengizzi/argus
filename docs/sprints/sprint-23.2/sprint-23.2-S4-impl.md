# Sprint 23.2, Session 4: Notifications

## Pre-Flight Checks
1. Read: `scripts/sprint_runner/main.py` (S3 — find TODO notification placeholders), `docs/protocols/notification-protocol.md` (full spec)
2. Run: `python -m pytest tests/ -x -q` — all passing

## Objective
Implement the notification system: ntfy.sh primary, Slack/email secondary, all 5 tiers, quiet hours, reminder escalation. Wire into the main loop's TODO placeholders.

## Requirements

1. **Create `scripts/sprint_runner/notifications.py`**:
   - `NotificationManager(config: NotificationsConfig)`.
   - **`send(tier: str, title: str, body: str)`**: Route to enabled channels. Check tier enabled. Check quiet hours. Queue if suppressed.
   - **`_send_ntfy(title, body, priority, tags)`**: HTTP POST to ntfy endpoint. Use `aiohttp` or `urllib.request`. Headers: Title, Priority, Tags. Optional auth_token. Handle connection errors gracefully (log, don't crash).
   - **`_send_slack(title, body)`**: POST to webhook URL with JSON payload. Optional.
   - **`_send_email(title, body)`**: SMTP send. Optional.
   - **Priority mapping per tier:** HALTED=5, SESSION_COMPLETE=3, PHASE_TRANSITION=2, WARNING=2, COMPLETED=3.
   - **Tag mapping:** HALTED="warning,rotating_light", SESSION_COMPLETE="white_check_mark", etc.
   - **Quiet hours:** Suppress SESSION_COMPLETE, PHASE_TRANSITION, WARNING during configured UTC window. HALTED and COMPLETED always send.
   - **Reminder escalation:** Track last HALTED notification time. If runner remains HALTED for `halted_reminder_minutes`, re-send.
   - **Message templates** per notification-protocol.md (HALTED, SESSION_COMPLETE, etc.)
   - **Logging:** All notifications logged to state.notifications_sent array.

2. **Modify `scripts/sprint_runner/main.py`**: Replace all TODO notification placeholders:
   - Session start: PHASE_TRANSITION "Implementation started"
   - Implementation complete: PHASE_TRANSITION "Implementation complete — extracting close-out"
   - Review complete: PHASE_TRANSITION "Review complete — verdict: {verdict}"
   - Session CLEAR: SESSION_COMPLETE with test counts and next session
   - Halt: HALTED with reason and run-log path
   - Sprint complete: COMPLETED with summary stats

## Constraints
- Do NOT modify anything under `argus/`. ALL HTTP calls mocked in tests.
- Use `aiohttp` (already in requirements) for ntfy.sh POST, or `urllib.request` for simplicity.

## Test Targets
- `test_notifications.py`: format all 5 tiers, ntfy delivery mock, quiet hours suppression, reminder timer, Slack mock, disabled tier skipped, priority mapping, error handling (~10)
- Minimum: 10 tests
- Command: `python -m pytest tests/sprint_runner/test_notifications.py -v`

## Definition of Done
- [ ] All notification tiers implemented and tested. Wired into main loop. All tests pass (≥10 new).

## Close-Out
Follow `.claude/skills/close-out.md`. Include structured JSON appendix.

## Sprint-Level Regression/Escalation
See `docs/sprints/sprint-23.2/review-context.md`

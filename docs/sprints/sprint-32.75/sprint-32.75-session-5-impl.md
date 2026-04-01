# Sprint 32.75, Session 5: Operational Fixes + IBC Guide

## Pre-Flight Checks
1. Read: `docs/sprints/sprint-32.75/review-context.md`, `config/overflow.yaml`, `argus/execution/ibkr_broker.py` (reconnect logic), `argus/strategies/base_strategy.py` (operating window)
2. Scoped tests: `python -m pytest tests/execution/test_ibkr*.py tests/strategies/test_base*.py -x -q`
3. Verify branch: `main`

## Objective
Raise overflow broker capacity to 60, add post-reconnect portfolio query delay, add per-strategy end-of-window evaluation summary logging, create IBC setup documentation.

## Requirements

1. **`config/overflow.yaml`**: Change `broker_capacity: 30` → `broker_capacity: 60`

2. **`argus/execution/ibkr_broker.py`**: In the `_reconnect()` method, after successful reconnection and before the first portfolio query:
   - Add `await asyncio.sleep(3.0)` delay
   - After the delay, query positions; if result count is 0 but `self._managed_positions` has entries, log a WARNING and retry once after 2s
   - This must NOT block order submission — only the portfolio snapshot query is delayed

3. **`argus/strategies/base_strategy.py`**: Add `_log_window_summary()` method called when the operating window closes (after `latest_entry` time passes). Logs at INFO level:
   ```
   Strategy {name} window closed: {n_symbols} symbols evaluated, {n_signals} signals generated, {n_rejected} rejected ({rejection_breakdown})
   ```
   Track these counters in the strategy's daily state (reset in `reset_daily_state()`).

4. **Stop retry analysis**: Review the April 1 log data (available in debrief notes). Document in close-out: are the 42 emergency flattens concentrated on specific symbols, specific times, or specific order types? Is this expected for a bearish trending day with 60+ positions?

5. **`docs/ibc-setup.md`**: Write comprehensive guide covering:
   - IBC installation (download, extract, configure)
   - `ibc/config.ini` setup with paper trading credentials
   - `launchd` plist for auto-start on macOS
   - Verification steps (how to confirm IBC is managing Gateway)
   - Security notes (credential storage, file permissions)

6. **`scripts/ibc/com.argus.ibgateway.plist`**: Template launchd plist that starts IBC with the Gateway profile.

## Constraints
- Do NOT modify Order Manager position management or flatten logic
- Do NOT modify broker-confirmed position tracking (DEC-369)
- Do NOT modify the reconnection attempt logic itself — only add delay after successful reconnect
- Do NOT include real IBKR credentials in any committed file

## Test Targets
- Test overflow config loads with new value
- Test reconnect delay (mock asyncio.sleep + portfolio query retry)
- Test _log_window_summary output format
- Minimum: 5 new tests
- Command: `python -m pytest tests/execution/test_ibkr*.py tests/strategies/test_base*.py tests/test_overflow*.py -x -q`

## Definition of Done
- [ ] overflow.yaml updated to 60
- [ ] Post-reconnect delay implemented with retry
- [ ] Window summary logging implemented
- [ ] Stop retry analysis documented in close-out
- [ ] IBC guide written
- [ ] launchd plist template created
- [ ] Close-out: `docs/sprints/sprint-32.75/session-5-closeout.md`
- [ ] Tier 2 review via @reviewer

## Close-Out
Write to: `docs/sprints/sprint-32.75/session-5-closeout.md`

## Tier 2 Review
Test: `python -m pytest tests/execution/ tests/strategies/test_base*.py tests/test_overflow*.py -x -q`. Files NOT to modify: OrderManager, Risk Manager, Event Bus.

## Session-Specific Review Focus
1. Verify reconnect delay is ONLY on the portfolio snapshot query, not on order operations
2. Verify window summary counters are reset daily
3. Verify IBC guide does not include any real credentials
4. Verify overflow config change doesn't require Pydantic model update (value change only)

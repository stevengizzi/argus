# Sprint 27.95: Broker Safety + Overflow Routing

## Goal
Fix the reconciliation auto-cleanup bug that destroyed 336 of 371 positions during the March 26 market session, add dynamic overflow routing to CounterfactualTracker for maximum signal data capture without broker overload, and harden five related order management failure modes discovered during the same session diagnostic.

## Scope

### Deliverables

1. **Reconciliation redesign** — Positions with confirmed IBKR entry fills are never auto-closed by reconciliation. Auto-cleanup restricted to unconfirmed positions (entry submitted, no fill callback) after N consecutive portfolio snapshot misses (configurable, default 3). Confirmed positions missing from snapshot produce WARNING logs only.

2. **Trade logger reconciliation close fix** — Reconciliation synthetic closes (PnL=0, reason=reconciliation) no longer produce ERROR-level "Failed to log trade" messages. Missing fields gracefully defaulted.

3. **Stop resubmission cap** — When IBKR rejects a stop order, retry up to `max_stop_retries` times (configurable, default 3) with exponential backoff. After retries exhausted, log ERROR and trigger emergency flatten for the position via existing `_flatten_pending` guard.

4. **Bracket amendment revision-rejected handling** — Detect IBKR "Revision rejected due to unapproved modification" cancellation reason. On detection, resubmit a fresh stop/target order instead of entering the stop resubmission loop. Ensures positions are never left without stop protection.

5. **Duplicate fill deduplication** — Guard against `ib_async` delivering multiple fill callbacks for the same order and cumulative quantity. Deduplicate by `(order_id, cumulative_filled_qty)`. Legitimate partial fills (increasing cumulative quantity) pass through normally.

6. **Dynamic overflow routing** — When the count of real IBKR positions reaches a configurable `broker_capacity` threshold (default 30), new approved signals are routed to CounterfactualTracker instead of placing IBKR orders. Signals published as `SignalRejectedEvent` with `RejectionStage.BROKER_OVERFLOW`. Config-gated via `overflow.enabled` (default true). Bypassed for `BrokerSource.SIMULATED`.

7. **Startup zombie cleanup** — At startup, IBKR positions with no matching ARGUS internal record are immediately flattened (config-gated via `startup.flatten_unknown_positions`, default true). Removes zombie RECO position entries. `scripts/ibkr_close_all_positions.py` made executable (`chmod +x`).

### Acceptance Criteria

1. **Reconciliation redesign:**
   - Position with confirmed IBKR fill is never auto-closed by reconciliation, even if missing from portfolio snapshot
   - Position with confirmed fill missing from snapshot produces WARNING log (not cleanup)
   - Unconfirmed position missing from 1 snapshot: no cleanup (miss counter incremented)
   - Unconfirmed position missing from N consecutive snapshots (N = `consecutive_miss_threshold`): auto-cleaned
   - Unconfirmed position reappearing in snapshot before threshold: miss counter reset to 0
   - When `auto_cleanup_unconfirmed` is false: no auto-cleanup of any kind (warn-only for all)
   - Existing reconciliation logging (mismatch counts, summaries) preserved

2. **Trade logger reconciliation close fix:**
   - Reconciliation close produces valid trade record with PnL=0, exit_reason=reconciliation
   - No ERROR-level log entries from trade logger during reconciliation closes
   - Normal trade close path (stop_loss, target_1, target_2, time_stop, eod_flatten) unchanged

3. **Stop resubmission cap:**
   - Stop rejected once → retry after backoff (attempt 2 of max_stop_retries)
   - Stop rejected N times → log ERROR, trigger emergency flatten
   - Emergency flatten respects `_flatten_pending` guard (no duplicate flatten orders)
   - Retry counter resets per position per stop order (not global)
   - Configurable `max_stop_retries` (default 3)

4. **Bracket amendment revision-rejected handling:**
   - "Revision rejected" cancellation detected by matching substring in IBKR error reason
   - On detection: fresh stop/target order submitted (not a retry of the cancelled order)
   - If fresh order also fails: enters normal stop resubmission flow (subject to retry cap)
   - Positions are never left without stop protection for more than one retry cycle

5. **Duplicate fill deduplication:**
   - Same `(order_id, cumulative_filled_qty)` received twice → second callback ignored with DEBUG log
   - Legitimate partial fill (order_id same, cumulative_filled_qty increased) → processed normally
   - Fill dedup state cleared when position closes

6. **Dynamic overflow routing:**
   - Position count < broker_capacity → signal routed to IBKR normally
   - Position count >= broker_capacity → signal published as SignalRejectedEvent with stage=BROKER_OVERFLOW, reason="Broker capacity reached ({count}/{capacity})"
   - CounterfactualTracker receives and tracks overflow signals (existing SignalRejectedEvent subscription)
   - BrokerSource.SIMULATED → overflow check skipped entirely
   - overflow.enabled=false → overflow check skipped entirely
   - Position count uses OrderManager's real (non-counterfactual) position count
   - Overflow check occurs after Risk Manager approval, before order placement

7. **Startup zombie cleanup:**
   - `flatten_unknown_positions=true` → unknown IBKR positions closed at startup with INFO log per symbol
   - `flatten_unknown_positions=false` → unknown IBKR positions produce WARNING log only (existing behavior)
   - Known positions (ARGUS has internal record) not affected by startup cleanup
   - `scripts/ibkr_close_all_positions.py` has executable bit set

### Performance Benchmarks
No performance benchmarks for this sprint — all changes are correctness and safety fixes.

### Config Changes

| YAML Path | Pydantic Model | Field Name | Default |
|-----------|---------------|------------|---------|
| `reconciliation.auto_cleanup_unconfirmed` | ReconciliationConfig | `auto_cleanup_unconfirmed` | `false` |
| `reconciliation.consecutive_miss_threshold` | ReconciliationConfig | `consecutive_miss_threshold` | `3` |
| `overflow.enabled` | OverflowConfig | `enabled` | `true` |
| `overflow.broker_capacity` | OverflowConfig | `broker_capacity` | `30` |
| `startup.flatten_unknown_positions` | StartupConfig | `flatten_unknown_positions` | `true` |

Note: `auto_cleanup_unconfirmed` defaults to false — the current Sprint 27.8 behavior (auto-cleanup enabled) is the bug. The new default disables auto-cleanup for unconfirmed positions too, making reconciliation fully warn-only. Operators who want cleanup of genuinely orphaned unconfirmed entries can opt in.

## Dependencies
- Codebase at post-Sprint 27.9 on main branch
- IBKR Gateway available for manual integration testing between sessions
- March 26 log file (`argus_20260326.jsonl`) available for reference during implementation

## Relevant Decisions
- DEC-363 (flatten-pending guard) — stop retry emergency flatten must use this guard
- DEC-364 (graceful shutdown order cancellation) — startup flatten uses similar broker interaction
- DEC-366 (bracket leg amendment on fill slippage) — revision-rejected handling fixes edge case in this logic
- DEC-367 (optional concurrent position limits) — overflow routing is a complementary mechanism, not a replacement
- DEC-300 (config-gated features) — all new features follow this pattern

## Relevant Risks
- RSK-022 (IBKR Gateway nightly resets) — startup zombie cleanup interacts with reconnection; must handle case where IBKR portfolio query fails at startup

## Session Count Estimate
7 sessions estimated. Split driven by compaction risk scoring: original 4-session plan had two sessions scoring 14+ (must-split threshold). No frontend work, no visual review contingency needed.

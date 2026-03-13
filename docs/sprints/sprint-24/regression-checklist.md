# Sprint 24: Sprint-Level Regression Checklist

Every session close-out and every Tier 2 review must verify these items. Mark each as PASS, FAIL, or N/A.

## Core Trading Pipeline

- [ ] All 4 strategies produce SignalEvents when entry criteria are met (signal generation unchanged)
- [ ] No strategy's entry/exit logic was altered (only pattern_strength calculation and share_count=0 added)
- [ ] Risk Manager's 7-check sequence operates correctly on enriched signals
- [ ] Risk Manager check 0 rejects signals with share_count ≤ 0 (defensive guard — Finding 6)
- [ ] Risk Manager never receives a signal with share_count=0 from the quality pipeline
- [ ] C/C- signals are filtered and never reach Risk Manager
- [ ] Circuit breakers remain non-overridable
- [ ] Event Bus FIFO ordering maintained — QualitySignalEvent does not block or delay OrderApprovedEvent/OrderRejectedEvent

## Backtest Bypass (Finding 1)

- [ ] Replay Harness with BrokerSource.SIMULATED produces identical signal count and sizes to pre-sprint
- [ ] Legacy sizing path uses strategy's original formula (allocated_capital × max_loss_per_trade_pct / risk_per_share)
- [ ] Quality scoring, dynamic sizing, quality history recording, and grade filtering are ALL skipped in backtest mode
- [ ] No `backtest/*` files were modified

## Config Gating (Finding 2)

- [ ] `quality_engine.enabled: true` present in both `system.yaml` and `system_live.yaml`
- [ ] When `quality_engine.enabled: false`, system behaves identically to pre-Sprint-24 (legacy sizing)
- [ ] When disabled, no quality_history rows are created
- [ ] When disabled, no QualitySignalEvents are published

## Signal Integrity

- [ ] SignalEvent backward compatibility: existing code constructing SignalEvent without new fields still works (defaults apply)
- [ ] `dataclasses.replace()` used for signal enrichment — original signal never mutated
- [ ] Enriched signal preserves all original fields (strategy_id, symbol, side, entry_price, stop_price, target_prices, rationale, time_stop_seconds)

## Strategy Behavior

- [ ] ORB Breakout: same signals fire under same conditions as pre-sprint (pattern_strength is additive, not gating)
- [ ] ORB Scalp: same signals fire under same conditions as pre-sprint
- [ ] VWAP Reclaim: same signals fire under same conditions as pre-sprint
- [ ] Afternoon Momentum: same signals fire under same conditions as pre-sprint
- [ ] Canary test: Replay Harness signal count and entry prices identical pre/post sprint

## Intelligence Pipeline

- [ ] CatalystPipeline still functions in per-symbol mode (firehose=False) for on-demand use
- [ ] CatalystClassifier unchanged — same categories, same classification logic
- [ ] CatalystStorage unchanged — same table schema, same query methods
- [ ] Catalyst pipeline config-gating (DEC-300) still works — pipeline disabled when `catalyst.enabled: false`
- [ ] FMP news circuit breaker (DEC-323) still active
- [ ] Daily cost ceiling (DEC-303) still enforced — on-demand lookups count against ceiling
- [ ] Firehose poll cycle makes ≤ 3 API calls per source (not N per symbol)

## Configuration

- [ ] New `quality_engine` config fields verified against Pydantic model (no silently ignored keys)
- [ ] `quality_engine.enabled: true` present in both config files
- [ ] Weight sum validation: weights must sum to 1.0 (±0.001), startup fails with ValidationError if violated
- [ ] Missing `quality_engine` section in YAML uses valid defaults (enabled=true, no crash)
- [ ] Both `system.yaml` and `system_live.yaml` include quality_engine section
- [ ] Existing config sections unmodified (ai, catalyst, universe_manager, etc.)

## Database

- [ ] `quality_history` table created in `argus.db` (not `catalyst.db`)
- [ ] Existing tables in `argus.db` unmodified (trades, orders, positions, etc.)
- [ ] `catalyst_events` table in `catalyst.db` unmodified
- [ ] quality_history rows persist across restarts

## API

- [ ] All existing API endpoints return same responses as pre-sprint
- [ ] New quality endpoints require JWT authentication
- [ ] Health endpoint still functions (quality engine health registered)

## Frontend

- [ ] Existing Dashboard panels unchanged (only new panels added)
- [ ] Existing Trades table columns unchanged (only new quality column added)
- [ ] Existing Performance charts unchanged (only new grade chart added)
- [ ] Existing Debrief tabs unchanged (only scatter plot added to relevant tab)
- [ ] Existing Orchestrator panels unchanged (only quality scores added)
- [ ] Pipeline health gating (DEC-329) still active for catalyst hooks
- [ ] All TanStack Query hooks for existing features still function

## Tests

- [ ] All 2,532 existing pytest tests pass
- [ ] All 446 existing Vitest tests pass
- [ ] No test file deleted or renamed
- [ ] Pre-existing xdist failures (DEF-048) remain isolated — no new xdist failures introduced

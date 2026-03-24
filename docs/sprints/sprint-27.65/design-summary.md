# Sprint 27.65: Market Session Safety + Operational Fixes

**Type:** Impromptu (discovered during March 24 market session)
**Urgency:** CRITICAL — Tier 1 items must be resolved before next market session
**Current sprint:** Between sprints (27.6 complete, 27.7 next planned)
**Predecessor:** Sprint 25.9 (Operational Resilience Fixes)

---

## Origin

During the March 24, 2026 live paper trading session, real-time log analysis
revealed 18 issues ranging from a critical order management bug to frontend
polish. The most severe finding: the Order Manager's time-stop mechanism
submits duplicate flatten orders every 5 seconds without tracking whether a
previous flatten is pending. This created $2.8M in phantom short positions at
IBKR that ARGUS was unaware of, requiring manual account cleanup. In live
trading, this would have been catastrophic.

## Scope

18 issues organized into 6 sessions (3 sequential steps with parallelization):

| Session | Name | Issues | Priority | Track |
|---------|------|--------|----------|-------|
| S1 | Order Management Safety | #11, #12, #17, #18 | CRITICAL | A |
| S2 | Trade Correctness + Risk Config | #14, #1, #16, #9 | HIGH | A |
| S3 | Strategy Fixes | #7, #13 | HIGH | B (parallel with S1) |
| S4 | IntradayCandleStore + Live P&L | #4, #5 | MEDIUM | A |
| S4.5 | Pattern Backfill Wire-Up + Final Integration | (wires S3 + S4) | MEDIUM | A (after S3 + S4) |
| S5 | Frontend + Observatory Fixes | #2, #3, #6, #8, #10 | LOW-MEDIUM | C (parallel with S2) |

### Parallel Execution Plan

```
Time →
Track A:  ████ S1 ████ → ████ S2 ████ → ████ S4 ████ → ████ S4.5 ████
Track B:  ████ S3 ████ ─────────────────────────────────────┘ (joins at S4.5)
Track C:                  ████ S5 ████
```

- S1 + S3 run in parallel (zero file overlap)
- S2 + S5 run in parallel (zero file overlap)
- S4 follows S2 (both touch order_manager.py)
- S4.5 is the final session — wires S3's backfill hook to S4's candle store,
  runs full integration test suite
- **3 sequential steps instead of 6**, calendar time reduced by ~50%

## Session 1: Order Management Safety (CRITICAL)

**Root cause:** `OrderManager._check_time_stops()` runs every 5 seconds and
submits a new flatten (market sell) order each cycle for any position exceeding
its time limit. It does not track whether a flatten order was already submitted.
This produces N duplicate SELL orders, where N = (time_until_fill / 5). In today's
session, CNK accumulated 36 duplicate orders, CSTM 58. Partial fills from the
paper simulator meant positions grew short as sells executed faster than buys.
At shutdown, ARGUS did not cancel open orders at IBKR, so orphaned orders
continued executing.

**Fixes:**
1. **`flatten_pending` guard:** Add a `_flatten_pending: dict[str, str]` mapping
   (symbol → order_id) to OrderManager. On first time-stop trigger, set the flag
   and submit the order. On subsequent cycles, check the flag — only resubmit
   if the previous order was confirmed cancelled/rejected (not just unfilled).
   Clear the flag on fill confirmation or explicit cancel.

2. **Graceful shutdown order cancellation:** In `main.py` shutdown sequence,
   call `ib.reqGlobalCancel()` (or iterate open orders and cancel each) before
   disconnecting from IB Gateway. This prevents orphaned orders from executing
   after ARGUS exits.

3. **Periodic position reconciliation:** Add a periodic task (60s interval,
   market hours only) that compares OrderManager's internal position dict against
   IBKR's actual positions via `ib.positions()`. Log WARNING on any discrepancy.
   Do not auto-correct (too risky) — just surface the mismatch for operator
   awareness. Add a `/api/v1/positions/reconciliation` endpoint for the frontend.

**Files touched:** `argus/execution/order_manager.py`, `argus/execution/ibkr_broker.py`,
`__main__.py` (shutdown), `argus/api/routes/` (reconciliation endpoint)

**Compaction risk:** 12 (Medium) — concentrated in order_manager.py which is
large and critical-path

## Session 2: Trade Correctness + Risk Config (HIGH)

**Fixes:**
1. **Bracket leg amendment after fill slippage (#14):** After entry fill
   confirmation, compare actual fill price vs signal entry price. If they differ,
   amend the stop and target bracket legs using the actual fill price as the new
   basis. At minimum, validate that target_price > actual_entry for longs (and
   vice versa for shorts) — if violated, cancel the bracket legs and submit
   corrected ones. This prevents the ZD scenario where a "target hit" at $43.42
   was actually a $265 loss because entry filled at $43.66.

2. **Make concurrent position limits optional (#1, #16):** In the Risk Manager,
   treat `max_concurrent_positions: 0` (or `null`) as "disabled" — skip the
   check entirely. Same for cross-strategy limit. Update strategy YAML configs
   and `system_live.yaml` to set these to 0. Leave the code path intact for
   future live trading where limits may be re-enabled.

3. **Zero-R signal guard (#9):** In `OrbBaseStrategy` (or whichever base emits
   scalp signals), add a guard: if `target_price <= entry_price` for longs (or
   `>= entry_price` for shorts), do not emit the signal. Log at DEBUG level.
   Prevents the PDBC scenario where entry=target=$16.86.

**Files touched:** `argus/execution/order_manager.py` (bracket amendment),
`argus/core/risk_manager.py` (optional limits), `argus/strategies/orb_base.py`
(zero-R guard), strategy YAML configs, `config/system_live.yaml`

**Compaction risk:** 10 (Medium)

## Session 3: Strategy Fixes (HIGH)

**Fixes:**
1. **Red-to-Green zero evaluations (#7):** Investigate why R2G has 3,324 symbols
   in its watchlist but zero evaluation events after 30+ minutes. Likely causes:
   (a) R2G's gap-down detection requires pre-market data that isn't available
   via Databento EQUS.MINI in live mode, (b) the strategy's `evaluate()` method
   has a guard that's never satisfied in live conditions, or (c) the strategy
   isn't receiving CandleEvents for its watchlist symbols. This session starts
   with diagnostic investigation before fixing.

2. **Bull Flag / Flat-Top insufficient history (#13):** The pattern strategies
   require 20-30 candle bars of history before evaluating. In live trading, this
   means they're offline for the first 20-30 minutes. Partial fix: on first
   candle arrival for a symbol, attempt to backfill from the IntradayCandleStore
   (if Session 4 is done) or from the in-memory candle buffer in
   DatabentoDataService. Full fix depends on IntradayCandleStore from S4.

**Files touched:** `argus/strategies/red_to_green.py`, `argus/strategies/pattern_strategy.py`,
potentially `argus/strategies/base_strategy.py`

**Compaction risk:** 9 (Medium) — investigation-heavy, may need multiple
diagnostic passes

## Session 4: IntradayCandleStore + Live P&L (MEDIUM)

**Fixes:**
1. **IntradayCandleStore (#4):** New component that subscribes to CandleEvent
   on the event bus and accumulates 1-minute bars per symbol in a dict of deques
   (max 390 bars per symbol = full trading day). Provides a `get_bars(symbol,
   start_time, end_time)` query API. Wire into the market bars REST endpoint
   (`/api/v1/market/{symbol}/bars`) to replace the current fallback-to-synthetic
   path. Also enables pattern strategy backfill (Session 3 fix #2).

   Location: `argus/data/intraday_candle_store.py`
   Initialization: in `main.py` after event bus, before strategies
   Subscription: `CandleEvent` on event bus

2. **Real-time position P&L via WebSocket (#5):** On each trade event (tick)
   for an open position, compute unrealized P&L and R-multiple. Push a
   `position_update` message through `/ws/v1/live` WebSocket. Frontend
   subscribes and updates position rows in real-time. Also push account
   equity updates when received from IBKR.

**Files touched:** New `argus/data/intraday_candle_store.py`, `argus/api/routes/market.py`,
`__main__.py`, `argus/execution/order_manager.py` (P&L broadcast),
`argus/api/websocket/live.py`, frontend position components

**Compaction risk:** 13 (Medium-High) — new component + integration wiring +
frontend changes

## Session 5: Frontend + Observatory Fixes (LOW-MEDIUM)

**Fixes:**
1. **Session Timeline missing 3 strategies (#2):** The Dashboard's Session
   Timeline component has a hardcoded strategy list. Switch to dynamically
   pulling from registered strategies via the API, or extend the static list
   to include Red-to-Green, Bull Flag, Flat-Top Breakout.

2. **Observatory Funnel all zeros (#3):** The `/api/v1/observatory/pipeline`
   endpoint returns all-zero stage counts despite data existing (session-summary
   shows 1,560 symbols, 77 evaluations, 3 signals). Investigate
   `ObservatoryService.get_pipeline_stages()` — likely not connected to
   UniverseManager for the static counts or not querying EvaluationEventStore
   correctly for the dynamic counts.

3. **FMP sector-performance 403 (#6):** Add a config note or suppress the
   ERROR to WARNING since this is a known Starter plan limitation. The circuit
   breaker already handles it correctly.

4. **ORB Scalp time-stop dominance (#8):** Observational — no code change.
   Add a note to the strategy spec sheet that the 120s window / 0.3R target
   parameters should be reviewed after collecting more session data.

5. **Frontend polling frequency (#10):** Reduce `/api/v1/performance/month`
   polling interval from ~25s to 60-120s. Observatory pipeline/session-summary
   polling similarly. These are TanStack Query `refetchInterval` values.

**Files touched:** Frontend Dashboard components, `argus/analytics/observatory_service.py`,
`argus/core/sector_rotation.py` (log level), frontend query hooks,
strategy spec docs

**Compaction risk:** 10 (Medium) — spread across many files but each change
is small

---

## Impact Assessment

### What could this break?
- **S1 (Order Management):** Highest risk. Changes to order lifecycle management
  could introduce new failure modes. Canary tests essential: verify normal
  stop-loss, target-hit, and time-stop paths still work with the new guard.
- **S2 (Bracket amendment):** Risk of breaking bracket order logic if amendment
  path has edge cases. Must test: partial fills, amendment rejection by IBKR,
  race conditions between fill and amendment.
- **S3 (Strategy fixes):** Low risk to other strategies. R2G is isolated.
- **S4 (CandleStore):** New additive component. Risk is in the wiring (replacing
  the existing synthetic bar fallback path).
- **S5 (Frontend):** Low risk. UI-only changes except Observatory service fix.

### Conflicts with planned work?
No. Sprint 27.7 (Counterfactual Engine) is next and doesn't touch Order Manager,
Risk Manager, or strategies. These fixes are orthogonal.

### Decision log impact?
New DECs needed for: flatten_pending guard, graceful shutdown, position
reconciliation, bracket amendment, optional concurrent limits, IntradayCandleStore.
Approximately 6-10 new DECs. Check `docs/decision-log.md` for current max.

### Deferred items?
Item #8 (ORB Scalp time-stop dominance) is observational only — log as DEF item
for parameter tuning after more data collection.

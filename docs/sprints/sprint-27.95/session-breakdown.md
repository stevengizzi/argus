# Sprint 27.95: Session Breakdown

## Session Order
1a → 1b → 2 → 4 → 3a → 3b → 3c

## Dependency Chain
```
1a (Reconciliation redesign)
├── 1b (Trade logger fix)
├── 2  (Order mgmt hardening)
├── 4  (Startup zombie cleanup)
└── 3a (Overflow config + enum)
    └── 3b (Overflow routing logic)
        └── 3c (Overflow → Counterfactual wiring)
```

---

### Session 1a: Reconciliation Redesign

**Objective:** Prevent reconciliation from destroying positions with confirmed IBKR entry fills. Add broker-confirmed tracking and consecutive miss counter for unconfirmed positions.

**Creates:** None
**Modifies:** `argus/execution/order_manager.py`, config Pydantic models (ReconciliationConfig)
**Integrates:** N/A (first session)
**Parallelizable:** false

| Factor | Detail | Points |
|--------|--------|--------|
| Files modified | order_manager.py, config models | 2 |
| Context reads | order_manager.py, events.py, existing reconciliation tests | 3 |
| New tests | ~10 (confirmed not cleaned, unconfirmed after N misses, mixed batch, counter reset, config disabled) | 5 |
| Complex integration | Reconciliation touches broker queries + position dict + trade close path | 3 |
| **Total** | | **13 (Medium)** |

**Key implementation details:**
- Add `_broker_confirmed: dict[str, bool]` — set True on entry fill callback
- Add `_reconciliation_miss_count: dict[str, int]` — per-symbol consecutive miss counter
- In reconciliation cycle: skip cleanup for confirmed positions (WARNING log only), increment miss counter for unconfirmed, cleanup unconfirmed at threshold
- Clear both dicts on position close
- Add `ReconciliationConfig` fields: `auto_cleanup_unconfirmed` (bool, default false), `consecutive_miss_threshold` (int, default 3)

---

### Session 1b: Trade Logger Reconciliation Close Fix

**Objective:** Fix ERROR-level "Failed to log trade" on reconciliation synthetic closes. Ensure synthetic close records with PnL=0 and reason=reconciliation are logged cleanly.

**Creates:** None
**Modifies:** `argus/analytics/trade_logger.py`
**Integrates:** Session 1a (reconciliation close now produces well-formed records via modified path)
**Parallelizable:** false

| Factor | Detail | Points |
|--------|--------|--------|
| Files modified | trade_logger.py | 1 |
| Context reads | trade_logger.py, order_manager.py (for close path context), existing tests | 3 |
| New tests | ~5 (synthetic close missing fields, normal close unchanged, reconciliation exit_reason) | 2.5 |
| **Total** | | **6.5 (Low)** |

**Key implementation details:**
- Identify which fields are missing in reconciliation close path (likely: exit_price, entry_price, strategy details)
- Add graceful defaults: exit_price=0.0, entry_price=0.0 or position's recorded entry, exit_reason="reconciliation"
- Ensure trade record is valid but clearly marked as reconciliation (not counted in P&L summaries)

---

### Session 2: Order Management Hardening

**Objective:** Cap stop resubmission retries, handle bracket amendment "Revision rejected" errors, and deduplicate fill callbacks.

**Creates:** None
**Modifies:** `argus/execution/order_manager.py`
**Integrates:** Session 1a (builds on modified order_manager.py with broker-confirmed tracking in place)
**Parallelizable:** false

| Factor | Detail | Points |
|--------|--------|--------|
| Files modified | order_manager.py | 1 |
| Context reads | order_manager.py (post-1a), events.py, existing tests | 3 |
| New tests | ~12 (stop retry 1/2/3/exhaust, backoff timing, emergency flatten, flatten_pending interaction, revision-rejected detection, fresh resubmit, duplicate fill same qty, partial fill increasing qty, fill dedup clear on close) | 6 |
| Large file | order_manager.py is already substantial, modifications touch 3 distinct areas | 2 |
| **Total** | | **12 (Medium)** |

**Key implementation details:**

*Stop resubmission cap:*
- Add `_stop_retry_count: dict[str, int]` — per-symbol retry counter
- On stop cancellation/rejection: increment counter, if < max_stop_retries → resubmit with backoff (1s, 2s, 4s), if >= max_stop_retries → log ERROR, trigger emergency flatten
- Emergency flatten uses existing `close_position()` → `_flatten_pending` guard
- Counter resets when a new stop order is successfully placed (not just submitted — placed without immediate rejection)
- Add `max_stop_retries` config field (default 3) — can use existing config structure or add to reconciliation config

*Bracket amendment revision-rejected handling:*
- In the order cancellation callback, check if cancel reason contains "Revision rejected"
- If so: do NOT enter the stop resubmission retry loop. Instead, create a fresh stop/target order with the amended prices (already computed by DEC-366 logic) and submit it as a new order
- If fresh order also fails: then enter normal stop resubmission flow (subject to retry cap)

*Duplicate fill deduplication:*
- Add `_last_fill_state: dict[str, tuple[str, float]]` — maps order_id → (order_id, last_cumulative_qty)
- On fill callback: check if (order_id, cumulative_filled_qty) matches last recorded state. If identical → log DEBUG "Duplicate fill callback ignored", return early
- If cumulative_qty increased → legitimate partial fill, process normally, update state
- Clear entry on position close

---

### Session 4: Startup Zombie Cleanup

**Objective:** Flatten unknown IBKR positions at startup (config-gated, default enabled). Fix script permissions.

**Creates:** None
**Modifies:** `argus/main.py` or `server.py` (startup position reconstruction logic), `scripts/ibkr_close_all_positions.py` (chmod +x), config Pydantic models (StartupConfig)
**Integrates:** Session 1a (concept of broker-confirmed vs unknown positions)
**Parallelizable:** false

| Factor | Detail | Points |
|--------|--------|--------|
| Files modified | main.py/server.py, script, config models | 3 |
| Context reads | main.py, order_manager.py, broker abstraction | 3 |
| New tests | ~8 (flatten enabled + unknown positions, flatten disabled + warning, empty IBKR portfolio, known positions not affected, IBKR query failure graceful handling) | 4 |
| **Total** | | **10 (Medium)** |

**Key implementation details:**
- During startup (after broker connects, before market data starts), query IBKR portfolio
- For each IBKR position: check if symbol exists in ARGUS internal position tracking
- If not found and `flatten_unknown_positions=true`: submit market sell order, log INFO "Startup cleanup: flattened unknown position {symbol} ({shares} shares)"
- If not found and `flatten_unknown_positions=false`: log WARNING "Unknown IBKR position at startup: {symbol} ({shares} shares) — manual cleanup required"
- Do NOT create RECO position entries for unknown positions when flatten is enabled
- Handle IBKR portfolio query failure gracefully: log WARNING, continue startup (don't block)
- `chmod +x scripts/ibkr_close_all_positions.py`
- Add `StartupConfig.flatten_unknown_positions` (bool, default true)

---

### Session 3a: Overflow Infrastructure

**Objective:** Add OverflowConfig Pydantic model, `config/overflow.yaml`, and `RejectionStage.BROKER_OVERFLOW` enum value.

**Creates:** `argus/config/overflow.yaml`
**Modifies:** `argus/core/events.py` (RejectionStage enum), config Pydantic models (OverflowConfig + SystemConfig wiring)
**Integrates:** N/A (infrastructure for Session 3b)
**Parallelizable:** false

| Factor | Detail | Points |
|--------|--------|--------|
| Files created | overflow.yaml | 2 |
| Files modified | events.py, config models | 2 |
| Context reads | events.py, existing config patterns (counterfactual.yaml as reference), Pydantic models | 3 |
| New tests | ~6 (config load, Pydantic validation, enum value exists, default values correct, config-disabled state) | 3 |
| **Total** | | **10 (Medium)** |

**Key implementation details:**
- `config/overflow.yaml`:
  ```yaml
  overflow:
    enabled: true
    broker_capacity: 30
  ```
- `OverflowConfig(BaseModel)`: enabled (bool, default True), broker_capacity (int, default 30, ge=0)
- Add to SystemConfig alongside existing config sections (follow counterfactual.yaml pattern)
- Add `BROKER_OVERFLOW = "broker_overflow"` to `RejectionStage` enum in events.py

---

### Session 3b: Overflow Routing Logic

**Objective:** Add overflow position count check in `_process_signal()`. Route overflow signals as SignalRejectedEvent with BROKER_OVERFLOW stage.

**Creates:** None
**Modifies:** `argus/main.py` (or wherever `_process_signal` lives)
**Integrates:** Session 3a (uses OverflowConfig + BROKER_OVERFLOW enum), Sessions 1a/2 (queries OrderManager position count)
**Parallelizable:** false

| Factor | Detail | Points |
|--------|--------|--------|
| Files modified | main.py/_process_signal | 1 |
| Context reads | main.py, order_manager.py (position count API), events.py, overflow config | 4 |
| New tests | ~6 (below threshold → normal, at threshold → overflow, above threshold → overflow, SIMULATED bypass, config-disabled bypass, correct SignalRejectedEvent fields) | 3 |
| Complex integration | Signal pipeline + OrderManager count + event publishing | 3 |
| **Total** | | **11 (Medium)** |

**Key implementation details:**
- In `_process_signal()`, after Risk Manager approval and before order placement:
  1. If `BrokerSource.SIMULATED` → skip overflow check
  2. If `overflow.enabled` is false → skip overflow check
  3. Get current real position count from OrderManager (need a method like `active_position_count` or use `len(self._positions)`)
  4. If count >= `overflow.broker_capacity` → publish `SignalRejectedEvent` with stage=BROKER_OVERFLOW, reason string, signal data, quality metadata, regime snapshot → return (do not place order)
  5. Otherwise → proceed with order placement as normal
- The SignalRejectedEvent follows the exact same schema used by quality filter/position sizer/risk manager rejections (Sprint 27.7)
- CounterfactualTracker already subscribes to SignalRejectedEvent — no changes needed there (verified in Session 3c)

---

### Session 3c: Overflow → CounterfactualTracker Wiring + Integration Tests

**Objective:** Verify end-to-end overflow → counterfactual pipeline. Add integration tests confirming overflow signals are tracked by CounterfactualTracker with correct metadata.

**Creates:** None
**Modifies:** Minimal — possibly `argus/intelligence/counterfactual.py` if BROKER_OVERFLOW stage needs special handling (unlikely, but verify)
**Integrates:** Session 3b (verifies full pipeline)
**Parallelizable:** false

| Factor | Detail | Points |
|--------|--------|--------|
| Files modified | Possibly counterfactual.py (minor), integration test files | 1 |
| Context reads | counterfactual.py, events.py, main.py, overflow config | 4 |
| New tests | ~6 (end-to-end overflow signal → counterfactual position opened, correct RejectionStage in store, overflow + shadow mode coexistence, counterfactual close produces valid record) | 3 |
| **Total** | | **8 (Low)** |

**Key implementation details:**
- Verify CounterfactualTracker's `_on_signal_rejected()` handler processes BROKER_OVERFLOW stage correctly
- If CounterfactualTracker filters by stage (e.g., only handles certain stages), add BROKER_OVERFLOW to the allowed set
- Write integration test: mock a signal pipeline where position count >= capacity → verify SignalRejectedEvent published → verify CounterfactualTracker opens shadow position → verify counterfactual store records the entry with correct stage
- Verify FilterAccuracy computation handles BROKER_OVERFLOW breakdown correctly (it should — it uses stage as a grouping key)

---

## Summary Table

| Session | Scope | Score | Risk | Depends On |
|---------|-------|-------|------|------------|
| 1a | Reconciliation redesign | 13 | Medium | — |
| 1b | Trade logger fix | 6.5 | Low | 1a |
| 2 | Order mgmt hardening (stop retry, revision-rejected, dedup) | 12 | Medium | 1a |
| 4 | Startup zombie cleanup | 10 | Medium | 1a |
| 3a | Overflow config + enum | 10 | Medium | — |
| 3b | Overflow routing in _process_signal | 11 | Medium | 3a, 1a, 2 |
| 3c | Overflow → Counterfactual wiring | 8 | Low | 3b |

**Estimated new tests:** ~53
**Estimated total test delta:** ~3,610 + 53 = ~3,663 pytest (Vitest unchanged — no frontend work)

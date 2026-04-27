# Sprint 31.91: What This Sprint Does NOT Do

> **Phase C artifact 2/7.** Defines the boundary the implementer must not cross
> and the Tier 2 reviewer must verify. Companion to `sprint-spec.md`.

## Out of Scope

These items are related to DEF-204 fix work but are explicitly excluded from
Sprint 31.91:

1. **Modifying DEF-199's A1 fix.** The 3-branch pattern at
   `argus/execution/order_manager.py:1670-1698` (EOD Pass 1 retry) and
   `:1719-1750` (EOD Pass 2) is the production safety net that catches phantom
   shorts at EOD. Session 3 mirrors this pattern; it does NOT modify the A1 code
   itself. Reason: protects the working safety net from accidental regression.

2. **Modifying IMPROMPTU-04's startup invariant.** `check_startup_position_invariant()`
   in `argus/main.py` and the `ArgusSystem._startup_flatten_disabled` attribute
   are out of scope. Reason: orthogonal mechanism (boot-time gate); changes here
   would expand sprint surface and require separate review.

3. **Adding `Position.broker_side: OrderSide` to the Pydantic Position model.**
   `Position.side: OrderSide` already exists at `argus/models/trading.py:160`
   and is correctly populated by `IBKRBroker.get_positions()` at line 942.
   Adding `broker_side` would be redundant. Reason: grep-verified during Phase
   A; DISCOVERY's proposal was based on a misread.

4. **Changing `Position.shares` Pydantic constraint.** `shares: int = Field(ge=1)`
   stays. We do not attempt to make `shares` carry signed broker state; signed
   state flows separately via `Position.side`. Reason: DEC-117 callers and
   downstream consumers depend on shares being positive.

5. **Touching AlpacaBroker.** `argus/execution/alpaca_broker.py` is out of scope
   end-to-end. Reason: queued for retirement in Sprint 31.94. Adding OCA support
   to a retiring broker is wasted effort.

6. **DEF-194/195/196 reconnect-recovery.** Lives in Sprint 31.93. Reason:
   distinct mechanism family (broker-state divergence on reconnect, not order
   placement / reconciliation contract). Cross-references to those DEFs are
   informational only.

7. **DEF-175/182/201/202 component ownership consolidation.** Lives in Sprint
   31.92. Reason: distinct concern (lifespan handler refactor); no overlap with
   exit-accounting code paths.

8. **Re-enabling live trading.** This sprint produces the prerequisite fix; the
   live-enable decision lives downstream. Reason: requires 3+ paper sessions of
   zero phantom-short accumulation as evidence post-merge, which can only happen
   after the sprint lands.

9. **Refactoring `_resubmit_stop_with_retry` retry-cap logic.** DEC-372's
   `stop_cancel_retry_max` and exponential-backoff schedule are unchanged.
   Session 1b only adds `ocaGroup` to the placed Order; retry behavior is
   untouched.

10. **Adding new exit-management semantics.** No new strategies for cancelling
    bracket children, no new exit reasons, no changes to trail/escalation
    activation logic. The Order Manager's exit-decision logic (when to flatten,
    when to escalate) is unchanged; only the `Order` objects produced by those
    decisions get OCA-group decoration.

11. **Backporting OCA grouping to existing managed positions.** Positions that
    exist in `_managed_positions` at the time Session 1a deploys have
    `oca_group_id = None`. Session 1b's standalone-SELL paths will see None and
    fall through to legacy no-OCA behavior for those positions. Operator daily
    flatten remains the safety net for positions opened before the upgrade.
    Reason: backporting requires querying IBKR for existing bracket parent IDs,
    which is operationally complex and time-bounded by the next session restart.
    Acceptable because positions on `main` at any moment are the same-day
    positions; they are flattened by EOD.

12. **Modifying SimulatedBroker's existing simulation logic.** SimulatedBroker
    gains a no-op acknowledgment of `ocaGroup` / `ocaType` (so unit tests that
    use it pass without error) but its fill-simulation logic is unchanged. No
    "simulated OCA cancellation" behavior is added. Reason: out-of-scope
    complexity; tests that need OCA-cancellation semantics use IBKR mocks.

## Edge Cases to Reject

The implementation should NOT handle these cases in this sprint. Each row
specifies the expected behavior:

| Edge Case | Expected Behavior | Notes |
|-----------|-------------------|-------|
| Bracket parent ULID is empty/None at the time `ocaGroup` is derived | Fall back to generating a fresh ULID via `generate_id()` for the OCA group | Defensive; should not occur in practice |
| `ManagedPosition.oca_group_id` is None when `_trail_flatten` is invoked | Place SELL with no `ocaGroup` (legacy behavior); log INFO once | Covers `reconstruct_from_broker`-derived positions |
| Two `ManagedPosition` instances exist for the same symbol simultaneously (multi-strategy concurrent trading) | Each carries its own distinct `oca_group_id`; both bracket trees operate independently | Verified by lifecycle test |
| IBKR rejects an order with `ocaType=1` (e.g., paper trading API limitation) | Log ERROR; let the existing rollback path cancel the parent | Existing error-handling at `ibkr_broker.py:783-805` |
| Reconciliation runs before any positions are tracked (cold-start) | `broker_positions` empty; both branches skip; no alert | Existing behavior preserved |
| Broker-orphan position has `side` field missing (older Position payload) | Log ERROR; do not engage entry gate; do not emit `phantom_short` alert (could be a long-orphan with stale type) | Fail-closed: don't escalate on uncertain data |
| Broker-orphan position has `side == OrderSide.BUY`, cycles 1–2 | Log WARNING only; no entry gate, no alert; increment `_broker_orphan_long_cycles[symbol]` | Cycle 1–2 long broker-orphan often resolves on next cycle (callback-in-flight) |
| Broker-orphan position has `side == OrderSide.BUY`, cycle ≥3 | Emit `SystemAlertEvent(alert_type="stranded_broker_long", severity="warning", symbol, shares, cycles)`; still no entry gate | Persistent unmanaged longs are exposure (no stop, no target); warning severity reflects lower urgency than phantom_short |
| `_check_flatten_pending_timeouts` queries the broker and the API call raises | Existing `except Exception` path preserved (use ARGUS qty); no new error-handling | Existing behavior preserved (DEC-158 retry resilience) |
| Phantom-short entry-gate is engaged and the operator wants to manually unblock | Operator hits `POST /api/v1/reconciliation/phantom-short-gate/clear` with `{"symbol": "AAPL", "reason": "..."}` — Session 2d delivers this endpoint. Audit-log entry written to `phantom_short_override_audit` table per M3 schema. Auto-clear via **5-cycle threshold** (default; configurable) also available without operator action. | Both manual and auto recovery paths in scope this sprint. M4 cost-of-error asymmetry: 5-cycle threshold (was 3) prevents premature gate clearing during transient broker-state fluctuations. |
| Same symbol gets phantom-short flagged AND has a margin-circuit gate | Both gates remain in effect; symbol is doubly-blocked. No interaction logic. | Each gate operates independently |

## Scope Boundaries

### Do NOT modify
- `argus/execution/order_manager.py:1670-1698` — DEF-199 A1 fix Pass 1 retry
- `argus/execution/order_manager.py:1707-1750` — DEF-199 A1 fix Pass 2
- `argus/main.py` — startup invariant region (`check_startup_position_invariant()`,
  `_startup_flatten_disabled` flag, the gate around `OrderManager.reconstruct_from_broker()`)
- `argus/models/trading.py` — `Position` class (existing `side` field is
  consumed; `shares: int = Field(ge=1)` constraint is preserved)
- `argus/execution/alpaca_broker.py` — business logic out of scope. **Exception:** Session 0 adds `cancel_all_orders(symbol)` ABC-compliance impl via `DeprecationWarning` per L1; this is the only AlpacaBroker change permitted in this sprint.
- **`argus/data/alpaca_data_service.py:593` Alpaca emitter TODO** — explicitly OUT of scope. Sprint 31.94 retires Alpaca by deletion; wiring this emitter site now would be 3 weeks of lifespan for throwaway code. Anti-regression test in Session 5b verifies the TODO comment is still present at `:593` after the sprint.
- `docs/sprints/sprint-31.9/IMPROMPTU-04-closeout.md` (historical artifact)
- `workflow/` submodule (RULE-018 — metarepo changes flow from metarepo to
  projects, not the reverse)

### Do NOT optimize
- Bracket placement latency: setting two extra Order fields adds <1µs at
  the placement site itself. **Note:** ocaType=1 introduces 50–200ms
  fill-latency on cancelling siblings (not the firing order) — see
  `sprint-spec.md` §"Performance Considerations". This is documented
  trade-off, not a regression to optimize away.
- Reconciliation polling cadence (60s): unchanged from existing
- Throttled-logger intervals: unchanged

### Do NOT refactor
- `_check_flatten_pending_timeouts` general structure (only the side-check is
  added; `flatten_pending_timeout_seconds` / `max_flatten_retries` /
  `_flatten_pending` dict shape are untouched)
- `place_bracket_order` general structure (only `ocaGroup` / `ocaType` Order-field
  setting is added; bracket parent / child relationships, transmit flags,
  rollback paths are untouched)
- `reconcile_positions` outer-loop structure (mismatch detection, consolidated
  WARNING summary, `_broker_confirmed` gating, `auto_cleanup_unconfirmed` /
  `auto_cleanup_orphans` branches — all preserved; only the broker-orphan
  branch is new)
- `Position` model field names or types (the existing `side` field is read; no
  fields are renamed or restructured)

### Do NOT add
- New `OrderType` enum values (the IBKR-side `ocaType` is an int, not an
  enum extension on our side)
- A "simulated OCA cancellation" behavior in SimulatedBroker
- A new `ExitReason` enum value for "phantom_short" (existing
  `ExitReason.RECONCILIATION` covers it; if the alert taxonomy needs extension,
  defer to a future sprint)
- A new event class (the existing `SystemAlertEvent` at `argus/core/events.py:405`
  has all the fields needed: `source`, `alert_type`, `message`, `severity`)
- A new circuit breaker (the per-symbol entry gate is not a "circuit" — it's a
  set membership check; mirrors DEC-367's per-symbol concentration check shape
  but does not introduce a new global breaker)

## Interaction Boundaries

This sprint does NOT change the behavior of:

- **DEC-117 atomic bracket invariant**: parent fails → all children cancelled.
  Preserved by existing rollback at `ibkr_broker.py:783-805`.
- **DEC-369 broker-confirmed positions never auto-closed**: the `confirmed`
  branch in `reconcile_positions` orphan loop (line 3045) is unchanged; new
  broker-orphan branch fires only for UNCONFIRMED positions.
- **DEC-370 auto-cleanup-unconfirmed default false**: unchanged.
- **DEC-372 stop retry caps**: `stop_cancel_retry_max`, exponential backoff,
  flatten-on-exhaustion — all unchanged.
- **DEC-367 margin circuit breaker**: unchanged. The per-symbol phantom-short
  entry gate is a separate state, not an extension of the margin circuit.
- **Sprint 29.5 EOD flatten circuit breaker**: unchanged.
- **DEF-158 dup-SELL prevention**: Session 3 modifies the exact function that
  contains DEF-158's logic; the dup-SELL prevention semantics for the ARGUS=N,
  IBKR=N normal case are preserved by construction (Session 3 only branches
  earlier on `side`).
- **OrderApprovedEvent → OrderManager → Broker pipeline**: unchanged; the
  per-symbol entry gate adds a pre-broker rejection, but all downstream events
  (`OrderRejectedEvent`, `SignalRejectedEvent` if applicable) flow through
  existing channels.

This sprint does NOT affect:

- The 11 catalyst pipeline data sources (catalyst, briefing, FMPNewsSource,
  FinnhubSource, SECEdgarSource, etc.)
- The Quality Engine pipeline (SetupQualityEngine, DynamicPositionSizer)
- The 15 strategies (no strategy receives new events; existing
  `OrderApprovedEvent` → strategy gating is unchanged)
- The Risk Manager's three-level gating
- The Counterfactual Tracker / shadow position routing
- The Learning Loop, Experiment Pipeline, Evaluation Framework
- Frontend code (no UI changes; the Command Center will surface phantom-short
  alerts via the existing `SystemAlertEvent` consumer if/when DEF-014 emitter
  side completes — that's outside this sprint)
- Backtesting (BacktestEngine doesn't run reconciliation; OCA grouping in
  simulated brackets is no-op)

## Deferred to Future Sprints

| Item | Target Sprint | DEF Reference |
|------|--------------|---------------|
| Component-ownership consolidation for `OrderManager` (DEF-175/182/201/202) | Sprint 31.92 | Pre-existing (DISCOVERY) |
| Reconnect-recovery and RejectionStage enum (DEF-194/195/196) | Sprint 31.93 | Pre-existing (DISCOVERY) |
| AlpacaBroker retirement (DEF-178/183) | Sprint 31.94 | Pre-existing (DISCOVERY) |
| HealthMonitor consumer for the new `phantom_short` alert | DEF-014 emitter expansion sprint (unscheduled) | DEF-014 (pre-existing) |
| Backend boot-commit-pair logging automation (referenced in `operational-debrief.md` §2) | Unscheduled | DEF-207 (pre-existing) |
| **SimulatedBroker should simulate OCA-group cancellation semantics matching ocaType=1** to align backtest fill behavior with live; until then, post-31.91 backtest T2-hit rates are upper bounds | Unscheduled | **DEF-208 (NEW — file at sprint close)** |
| **`analytics/debrief_export.py` and other historical-record writers must preserve `Position.side`** to support side-aware Learning Loop V2 promotion/demotion decisions | Sprint 35+ horizon (Learning Loop V2 prerequisite) | **DEF-209 (NEW — file at sprint close)** |

### Items previously deferred but now IN scope

The following items appeared in earlier drafts of this SbC as deferred;
the adversarial reviews (first + second pass) and Phase A revisit
surfaced them as in-scope blockers:

- **Operator-Command-Center API endpoint for clearing phantom-short entry
  gate** — moved to Session 2d (first revision).
- **Backporting OCA grouping safety to in-flight `reconstruct_from_broker`
  positions** — moved to Session 1c (first revision).
- **EOD flatten OCA threading** — moved to Session 1b (`_flatten_position`
  expansion) + Session 1c (broker-only paths) (first revision).
- **DEF-014 alert observability resolution** — Sessions 5a–5e (second
  revision; operator chose "all-in" rather than defer to follow-on
  sprint). Includes HealthMonitor consumer, WebSocket fan-out, REST
  endpoint, acknowledgment flow, Dashboard banner, toast notifications,
  Observatory alerts panel, cross-page integration. **Resolves DEF-014.**
- **IBKR emitter TODO sites at `:453` and `:531`** — Session 5b (second
  revision; bonus scope from DEF-014 resolution).
- **B5 three-site pattern fix** — Session 2b.2 (Phase A revisit; Risk
  Manager max-concurrent-positions + EOD Pass 2 short alert + Health
  integrity check side-aware).
- **Restart-required reverse-rollback** — H1 disposition documented in
  `live-operations.md` runbook (mid-session config flip explicitly
  unsupported).

---

*End Sprint 31.91 Specification by Contradiction.*

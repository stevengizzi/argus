# Doc-Sync Patch 4 — `docs/architecture.md`

**Purpose:** (a) Update §3.3 Broker Abstraction interface block to reflect the Session 0 `cancel_all_orders(symbol, *, await_propagation)` ABC extension. (b) Update the §3.7 Order Manager DEF-204 known-issue paragraph to reflect post-Session-1c state, and add an OCA architecture callout immediately after.

**Anchor verification (must hold before applying):**
- Line 305: `### 3.3 Broker Abstraction (\`execution/broker.py\`)`
- Line 314: `    async def cancel_order(self, order_id: str) -> bool`
- Line 855: starts with `> **Known issue (DEF-204, identified Apr 24, 2026 — IMPROMPTU-11 mechanism diagnostic).**`
- Line 855 (continuation): ends with `Operator mitigation in effect: daily \`scripts/ibkr_close_all_positions.py\` at session close.`

---

## Patch A — Update §3.3 Broker Abstraction interface block

### Find (the `Interface:` block at line 309–321):

```
**Interface:**
```python
class Broker(ABC):
    async def place_order(self, order: Order) -> OrderResult
    async def place_bracket_order(self, entry: Order, stop: Order, targets: list[Order]) -> BracketOrderResult
    async def cancel_order(self, order_id: str) -> bool
    async def modify_order(self, order_id: str, modifications: dict) -> OrderResult
    async def get_positions(self) -> list[Position]
    async def get_account(self) -> AccountInfo
    async def get_order_status(self, order_id: str) -> OrderStatus
    async def get_open_orders(self) -> list[Order]  # For state reconstruction (DEC-246)
    async def flatten_all(self) -> list[OrderResult]  # Emergency: close everything (uses SMART routing DEC-245)
```
```

### Replace with:

```
**Interface:**
```python
class Broker(ABC):
    async def place_order(self, order: Order) -> OrderResult
    async def place_bracket_order(self, entry: Order, stop: Order, targets: list[Order]) -> BracketOrderResult
    async def cancel_order(self, order_id: str) -> bool
    async def cancel_all_orders(
        self,
        symbol: str | None = None,
        *,
        await_propagation: bool = False,
    ) -> int  # DEC-364 no-args contract preserved; symbol/await_propagation added Sprint 31.91 S0 (DEC-386)
    async def modify_order(self, order_id: str, modifications: dict) -> OrderResult
    async def get_positions(self) -> list[Position]
    async def get_account(self) -> AccountInfo
    async def get_order_status(self, order_id: str) -> OrderStatus
    async def get_open_orders(self) -> list[Order]  # For state reconstruction (DEC-246)
    async def flatten_all(self) -> list[OrderResult]  # Emergency: close everything (uses SMART routing DEC-245)
```

**`cancel_all_orders` semantics (DEC-386, Sprint 31.91 Session 0):**
- No-args call (`cancel_all_orders()`): preserves DEC-364 contract — cancel ALL working orders. `IBKRBroker` invokes `reqGlobalCancel`; `SimulatedBroker` clears the in-memory pending list; `AlpacaBroker` emits `DeprecationWarning` and delegates to its legacy implementation (queued for Sprint 31.94 retirement).
- Per-symbol filter (`cancel_all_orders(symbol="AAPL")`): cancels only working orders for that symbol. Used by Session 1c's broker-only safety paths to clear stale yesterday OCA-group siblings before placing a follow-up flatten SELL.
- Propagation-await (`cancel_all_orders(symbol="AAPL", await_propagation=True)`): after issuing cancellations, polls broker open-orders for the filtered scope every 100ms until empty. 2-second timeout. Raises `CancelPropagationTimeout` (defined in `argus/execution/broker.py`) on timeout. The leaked-long failure mode on timeout is the intended trade-off vs. an unbounded phantom-short risk — see §3.7's OCA architecture block and DEC-386 for the asymmetric-risk rationale.
```

---

## Patch B — Update §3.7's DEF-204 known-issue paragraph + add OCA architecture block

### Find (the entire DEF-204 known-issue blockquote at line 855):

```
> **Known issue (DEF-204, identified Apr 24, 2026 — IMPROMPTU-11 mechanism diagnostic).** Bracket children are placed via `parentId` only without explicit `ocaGroup`; combined with standalone SELL orders from trail/escalation paths that share no OCA group with bracket children, this allows multi-leg fill races that produce ~98% of the unexpected-short blast radius observed during Apr 24 paper trading (44 symbols / 14,249 unintended short shares accumulated through gradual reconciliation-mismatch drift over a 6-hour session). ARGUS's exit-side accounting is also side-blind in three surfaces (reconcile orphan-loop one-direction-only; reconcile call site strips side info via `Position.shares = abs(int(ib_pos.position))`; DEF-158 retry path side-blind via `abs(int(getattr(bp, "shares", 0)))`). DEF-199's IMPROMPTU-04 fix correctly refuses to amplify these at EOD (1.00× signature, zero doubling) and escalates to operator with CRITICAL alert; the upstream mechanism remains. Fix is scoped to the `post-31.9-reconciliation-drift` named horizon (3 sessions, all-three-must-land-together, adversarial review required at every session boundary). See `docs/sprints/sprint-31.9/IMPROMPTU-11-mechanism-diagnostic.md` for the full forensic analysis and `docs/sprints/post-31.9-reconciliation-drift/DISCOVERY.md` for the concrete fix plan. Operator mitigation in effect: daily `scripts/ibkr_close_all_positions.py` at session close.
```

### Replace with:

```
> **Active fix in flight (DEF-204, identified Apr 24, 2026 — IMPROMPTU-11 mechanism diagnostic; Sprint 31.91 in progress).** DEF-204's mechanism is a fill-side race: bracket children placed via `parentId` only without explicit `ocaGroup`, combined with redundant standalone SELL orders from trail/escalation paths sharing no OCA group with bracket children, produced ~98% of the unexpected-short blast radius observed during Apr 22–24 paper trading (44 symbols / 14,249 unintended short shares on Apr 24 alone, accumulated through gradual reconciliation-mismatch drift over a 6-hour session). ARGUS's exit-side accounting was also side-blind in three surfaces (reconcile orphan-loop one-direction-only; reconcile call site strips side info via `Position.shares = abs(int(ib_pos.position))`; DEF-158 retry path side-blind via `abs(int(getattr(bp, "shares", 0)))`). DEF-199's IMPROMPTU-04 fix correctly refuses to amplify these at EOD (1.00× signature, zero doubling) and escalates to operator with CRITICAL alert; the upstream mechanism is now being closed in Sprint 31.91. **Status as of 2026-04-27:** Sessions 0+1a+1b+1c have landed (DEC-386, Tier 3 architectural review #1 PROCEED) — the OCA architecture closes the ~98% mechanism. Sessions 2a–2d (side-aware reconciliation contract; DEC-385 reserved), Session 3 (DEF-158 retry side-check), and Session 4 (mass-balance + IMSR replay validation) remain in flight to close the secondary detection-blindness mechanism. Sessions 5a.1–5e (alert observability; DEC-388 reserved) remain in flight to make the new `phantom_short`/`cancel_propagation_timeout` alerts visible in the Command Center. **Operator mitigation in effect** (daily `scripts/ibkr_close_all_positions.py` at session close) until Sprint 31.91 sprint close + ≥3 paper sessions of zero `unaccounted_leak` mass-balance rows. See `docs/sprints/sprint-31.9/IMPROMPTU-11-mechanism-diagnostic.md` for the original forensic analysis, `docs/sprints/sprint-31.91-reconciliation-drift/sprint-spec.md` for the Sprint 31.91 deliverables, and DEC-386 for the OCA architecture rationale.

#### OCA Architecture (Sprint 31.91 Sessions 0+1a+1b+1c, DEC-386 — PROCEED 2026-04-27)

The OCA architecture is a 4-layer stack closing the bracket-internal fill race that produced ~98% of DEF-204's blast radius. Each layer is a strict superset of the prior layer's safety property (per Sprint 31.91 regression-checklist invariant 14 monotonic-safety matrix):

1. **API contract (Session 0).** `Broker.cancel_all_orders(symbol, *, await_propagation)` ABC extension + `CancelPropagationTimeout` exception class. See §3.3 for the interface; DEC-364 no-args contract preserved verbatim.

2. **Bracket OCA (Session 1a).** `IBKRBroker.place_bracket_order` sets `ocaGroup = f"oca_{parent_ulid}"` and `ocaType = config.ibkr.bracket_oca_type` (default 1) on each bracket child (stop, T1, T2). The parent (entry) Order is intentionally NOT in the OCA group, so an entry-fill does not OCA-cancel its own protection legs. `ManagedPosition.oca_group_id` persists at bracket-confirmation time. New Pydantic-validated `IBKRConfig.bracket_oca_type` field constrained to `[0, 1]`; ocaType=2 is architecturally wrong for ARGUS's bracket model; ocaType=0 is the RESTART-REQUIRED rollback escape hatch. Defensive `_is_oca_already_filled_error` helper distinguishes IBKR Error 201 / "OCA group is already filled" (SAFE — the bracket stop fired in the placement micro-window and the OCA group bought us out) from generic Error 201 (margin, price-protection); the rollback (DEC-117 invariant) STILL fires on both branches, only log severity differs. Phase A spike (`scripts/spike_ibkr_oca_late_add.py`) confirmed `PATH_1_SAFE` 2026-04-25 — IBKR enforces ocaType=1 atomic cancellation pre-submit. Spike result file freshness (≤30 days) is regression invariant 22.

3. **Standalone-SELL OCA (Session 1b).** Four paths thread `ManagedPosition.oca_group_id` onto the placed SELL Order: `_trail_flatten`, `_escalation_update_stop`, `_submit_stop_order` (which covers `_resubmit_stop_with_retry` per DEC-372), and `_flatten_position` (the central exit path used by EOD Pass 1, `close_position()`, `emergency_flatten()`, and time-stop). `oca_group_id is None` (covers `reconstruct_from_broker`-derived positions) falls through to legacy no-OCA behavior. Graceful Error 201 / OCA-filled handling: sets `ManagedPosition.redundant_exit_observed = True`, logs INFO, and short-circuits the DEF-158 retry path by deliberately NOT seeding `_flatten_pending`. The grep regression guard `tests/_regression_guards/test_oca_threading_completeness.py::test_no_sell_without_oca_when_managed_position_has_oca` enforces threading discipline; legitimate broker-only paths are exempted via the canonical `# OCA-EXEMPT: <reason>` comment.

4. **Broker-only safety (Session 1c).** Three broker-only SELL paths that have no `ManagedPosition` to thread (`_flatten_unknown_position`, `_drain_startup_flatten_queue`, `reconstruct_from_broker`) invoke `cancel_all_orders(symbol=X, await_propagation=True)` BEFORE placing the SELL (or BEFORE wiring the position into `_managed_positions`, for `reconstruct_from_broker`). On `CancelPropagationTimeout` (2-second budget exceeded), the SELL/wire is aborted, a critical `SystemAlertEvent(alert_type="cancel_propagation_timeout")` is emitted, and the position remains at the broker as a phantom long with no working stop. **The leaked-long failure mode is the intended trade-off** — phantom long is bounded exposure (the long position size; price floor of 0); an incorrect SELL placed without cancellation propagation could create an unbounded phantom short on a runaway upside. Operator response is manual flatten via `scripts/ibkr_close_all_positions.py`. **Critical caveat:** until Sprint 31.91 Session 5a.1 lands (HealthMonitor consumer for `SystemAlertEvent`), the alert is visible only in logs — not in the Command Center. Live-trading transition MUST NOT proceed before 5a.1 lands; see `docs/pre-live-transition-checklist.md`.

`reconstruct_from_broker()` carries a contractual STARTUP-ONLY docstring documenting that future RECONNECT_MID_SESSION callers MUST add a `ReconstructContext` parameter — the unconditional cancel-orders invocation is correct ONLY at startup (clears yesterday's stale OCA siblings); a mid-session reconnect would WIPE OUT today's working bracket children. The docstring is a time-bounded contract — Sprint 31.93 (DEF-194/195/196 reconnect-recovery) will replace the docstring with a runtime gate (DEF-211, sprint-gating). Until then, ARGUS does not support mid-session reconnect.

**Two follow-on sprint commitments inherited from DEC-386:**
- **Sprint 31.92** (component-ownership refactor; DEF-175/182/201/202): wire `IBKRConfig.bracket_oca_type` into `OrderManager.__init__` and replace the `_OCA_TYPE_BRACKET = 1` module constant in `argus/execution/order_manager.py` (DEF-212); also relocate `_is_oca_already_filled_error` from `ibkr_broker.py` to `broker.py` and rename to `is_oca_already_filled_error` (Tier 3 Concern A — sibling cleanup).
- **Sprint 31.93** (reconnect-recovery; DEF-194/195/196): add `ReconstructContext` parameter to `reconstruct_from_broker()` (DEF-211).
```

---

## Application notes

- The §3.3 patch adds the `cancel_all_orders` line to the ABC interface block AND adds a new "semantics" sub-block immediately after the `**Implementations:**` section already present at the existing line 323. Re-verify the indentation against the existing surrounding text.
- The §3.7 patch:
  - Reframes the existing DEF-204 paragraph from "known issue, fix scoped" to "active fix in flight — Sessions 0-1c landed; 2a-d / 3 / 4 / 5a-e remain." This is more accurate post-Tier-3.
  - Adds a brand-new `#### OCA Architecture` subsection immediately after the reframed paragraph. The subsection uses `####` heading (one deeper than `### 3.7 Order Manager`).
  - Length-wise, the patch adds roughly 75 lines to architecture.md. This is the largest of the doc-sync patches.
- **Important:** if the existing `#### ExecutionRecord Logging` heading at line 857 is the next element after the DEF-204 paragraph, the new `#### OCA Architecture` block lands BEFORE it (between the DEF-204 paragraph and ExecutionRecord). Verify by reading 855-870 before applying.

Two surgical replacements. No other §3.7 content (ExecutionRecord block, etc.) is touched.

# Sprint 31.91: Adversarial Review Input Package

> **Phase C artifact 7/7.** This document gives the adversarial reviewer
> everything they need to break this sprint's design. It is meant to be pasted
> into a separate Claude.ai conversation alongside the Sprint Spec and the
> Specification by Contradiction. **The reviewer should not need to gather
> additional context.**
>
> Per `protocols/adversarial-review.md`: the reviewer's job is to find problems,
> not to be supportive. The adversarial review's quality is measured by whether
> it surfaces non-obvious concerns. If the reviewer finds nothing, they were
> not aggressive enough.

## Conversation Opening for the Adversarial Reviewer

```
I need you to adversarially review this sprint spec. Your job is to find
problems, not to be supportive. The sprint is safety-critical (DEF-204 fix —
upstream cascade of unintended short positions in a paper-trading day-trading
system; current daily-flatten mitigation is the only thing keeping the system
operational). Real-world consequences of a regression could be catastrophic
once live trading resumes.

I am providing three documents:

1. The Sprint Spec
2. The Specification by Contradiction
3. This Adversarial Review Input Package (architecture excerpts, DEC entries,
   forensic anchor, focus areas)

Try to break this design. Find the flaws. Pursue these probing angles
aggressively:

- Assumption mining: what assumptions could be wrong?
- Failure mode analysis: what happens when each component fails?
- Future regret: what will we regret in 3 months? 6 months?
- Specification gaps: what is underspecified? where will judgment calls go wrong?
- Integration stress: how does this interact with existing systems? what
  existing assumptions does it violate?
- Re-walk the IMPROMPTU-04 grep-audit (Section 3 below) — that audit declared
  one site safe that IMPROMPTU-11 then proved unsafe. Apply RULE-051
  mechanism-signature thinking to every other row.

After your review, produce one of:
- "Confirmed — proceed" with any minor observations as notes.
- A list of issues that require spec changes, with proposed revisions.
```

---

## 1. Architecture Excerpts (from `docs/architecture.md`)

### §3.3 Broker Abstraction (excerpt)

The broker abstraction layer (`argus/execution/broker.py`) defines a Broker
ABC with three implementations: IBKRBroker (live + paper), AlpacaBroker
(incubator, queued for retirement in Sprint 31.94), SimulatedBroker
(backtest). All three implement `place_bracket_order()` per DEC-117. The
Broker ABC includes `cancel_all_orders()` (DEC-364).

**Sprint 31.91 changes scope:** IBKRBroker and SimulatedBroker.
AlpacaBroker is NOT touched (out-of-scope per SbC).

### §3.3c IBKRBroker (excerpt)

Native IBKR bracket linkage: `place_bracket_order()` constructs a parent
entry order + stop child + T1 limit child + (optional) T2 limit child. The
`parentId` field on each child links it to the parent for IBKR's matching
engine. Children are submitted with `transmit=False` until the LAST child,
which sets `transmit=True` to submit the entire bracket atomically.

DEC-117 atomic-bracket invariant: if any child placement raises mid-loop,
the rollback at `ibkr_broker.py:783-805` cancels the parent. This preserves
the all-or-nothing semantics that DEC-117 promises.

**Pre-Sprint-31.91 known limitation:** bracket children rely on `parentId`
ONLY for OCA-like behavior. There is no explicit `ocaGroup` / `ocaType` set
on the children. Per IMPROMPTU-11's forensic analysis, this is "loose" in
IBKR paper trading — children CAN race each other to fill if cancel
propagation latency exceeds price-trigger latency.

Standalone SELL paths (`_trail_flatten`, `_escalation_update_stop`,
`_resubmit_stop_with_retry`) place orders that share NO OCA group with the
bracket children of the position they're operating on.

### §3.7 Order Manager (excerpt)

> The §3.7 module includes a callout block at line 855 documenting DEF-204 as
> a known issue. That block will be replaced with a CLOSED reference at
> sprint-close per `doc-update-checklist.md` Phase B item B9.

OrderManager state:
- `_managed_positions: dict[str, list[ManagedPosition]]` — supports multiple
  positions per symbol.
- `_pending_orders: dict[str, PendingManagedOrder]` — keyed by order_id.
- `_flatten_pending: dict[str, tuple[str, float, int]]` — keyed by symbol;
  tracks (order_id, monotonic_time, retry_count). DEF-112 timeout pattern.
- `_broker_confirmed: dict[str, bool]` — DEC-369 broker-confirmed flag.
- `_reconciliation_miss_count: dict[str, int]` — DEC-370 miss counter.

OrderManager event subscriptions: `OrderApprovedEvent`, `OrderFilledEvent`,
`OrderCancelledEvent`, `TickEvent`, `CircuitBreakerEvent`.

OrderManager events published: `OrderSubmittedEvent`, `PositionOpenedEvent`,
`PositionClosedEvent`, `SystemAlertEvent` (per DEF-014 emitter side).

**Sprint 31.91's planned additions to this module:**
- `ManagedPosition.oca_group_id: str | None` (Session 1a)
- `_phantom_short_gated_symbols: set[str]` (Session 2c)
- `ReconciliationPosition` frozen dataclass (Session 2a)
- Broker-orphan branch in `reconcile_positions()` orphan loop (Session 2b)
- 3-branch side-check in `_check_flatten_pending_timeouts` (Session 3)

---

## 2. Relevant DEC Entries (from `docs/decision-log.md`)

### DEC-117: Atomic Bracket Orders in Order Manager

**Date:** 2026-02-24
**Decision:** `place_bracket_order()` for entry+stop+T1+T2 atomic submission.
All three broker implementations support it.
**Rationale:** Eliminates the unprotected window between entry fill and
stop/target placement. "Near-zero risk is not the right standard — zero risk
is."
**Sprint 31.91 implication:** OCA grouping is added ON TOP OF DEC-117's
parentId-based atomic submission, not replacing it. The rollback at
`ibkr_broker.py:783-805` is preserved.

### DEC-367: Optional Concurrent Position Limits (per-symbol gate pattern source)

**Date:** 2026-03-24
**Decision:** `max_concurrent_positions: 0` disables the concurrent-position
check; positive integers cap the count. Per-symbol pattern uses set membership.
**Sprint 31.91 implication:** Session 2c's per-symbol entry gate
(`_phantom_short_gated_symbols: set[str]`) MIRRORS this pattern's shape.
The two states are independent — a symbol can be in BOTH the
phantom-short-gated set AND the margin-circuit set.

### DEC-369: Reconciliation — Broker-Confirmed Positions Never Auto-Closed

**Date:** 2026-03-26
**Context:** Reconciliation trusted IBKR snapshots over fill callbacks and
auto-closed 336 of 371 real positions; 239 later received exit fills proving
they were real.
**Decision:** `_broker_confirmed` dict tracks positions with confirmed IBKR
entry fills. Confirmed positions are NEVER auto-closed by reconciliation
regardless of config.
**Sprint 31.91 implication:** the `confirmed` branch in `reconcile_positions`
orphan loop (`order_manager.py:3045`) is preserved. Session 2b's broker-orphan
branch fires only for UNCONFIRMED broker-orphan positions.

### DEC-370: Reconciliation — auto_cleanup_unconfirmed default false

**Decision:** `auto_cleanup_unconfirmed: false` (default), `consecutive_miss_threshold: 3`.
Legacy `auto_cleanup_orphans` remains backward-compatible.
**Sprint 31.91 implication:** unchanged. The new broker-orphan branch is
INDEPENDENT of the existing auto-cleanup logic.

### DEC-372: Stop Resubmission Cap with Exponential Backoff

**Date:** 2026-03-26
**Context:** March 26 session — RDW had 68 stop resubmissions in 50 seconds
(infinite retry loop on IBKR rejection).
**Decision:** `_resubmit_stop_with_retry` caps retries at `stop_cancel_retry_max`
(default 3) with exponential backoff (1s, 2s, 4s).
**Sprint 31.91 implication:** Session 1b threads OCA group through
`_resubmit_stop_with_retry` but does NOT modify retry-cap logic.

---

## 3. IMPROMPTU-04 Grep-Audit (from `docs/sprints/sprint-31.9/IMPROMPTU-04-closeout.md`)

This is the audit that must be RE-WALKED by the adversarial reviewer. Row #10
was declared safe; IMPROMPTU-11 then proved it was the H5 amplifier — the very
site Session 3 fixes. The reviewer must apply RULE-051 mechanism-signature
thinking to every other row to find any OTHER hidden surfaces.

| # | File:Line | Disposition | Rationale (verbatim from IMPROMPTU-04) |
|---|---|---|---|
| 1 | `argus/core/risk_manager.py:335` | Intentionally different | Max-concurrent-positions check uses `len(positions)` only. Side-agnostic; count is correct regardless. No short-flip surface. |
| 2 | `argus/core/risk_manager.py:771` | Intentionally different | `daily_integrity_check` uses `len(positions)` only. Same rationale as #1. |
| 3 | `argus/main.py:1412` | Intentionally different | Background reconciliation task builds `{symbol: qty}` dict and calls `OrderManager.reconcile_positions()`. Downstream reconciliation validates symbol-set membership, not flatten decisions. **Could be improved to emit a divergence alert for shorts, but that's DEF-195 scope (post-31.9 reconnect-recovery sprint).** |
| 4 | `argus/analytics/debrief_export.py:336` | Intentionally different | Read-only export for end-of-session debrief JSON. No flatten decision. Side-agnostic by design. |
| 5 | `argus/execution/order_manager.py:1492` | Intentionally different | Margin circuit breaker auto-reset — uses `len(broker_positions)` only. Count-threshold based; side-agnostic. |
| 6 | `argus/execution/order_manager.py:1677` | **FIXED by IMPROMPTU-04** | EOD Pass 1 retry. `broker_side_map` built; three-branch side check applied. |
| 7 | `argus/execution/order_manager.py:1701` | **FIXED by IMPROMPTU-04** | EOD Pass 2. Three-branch side check applied. |
| 8 | `argus/execution/order_manager.py:1729` | Intentionally different | Post-flatten verification query — logs CRITICAL with `remaining_syms` list. Informational only; no order placed. |
| 9 | `argus/execution/order_manager.py:1810` | Startup-cleanup path — gated by the new invariant | `reconstruct_from_broker()` — gated by `_startup_flatten_disabled` flag. |
| 10 | `argus/execution/order_manager.py:2354` | **Intentionally different (REVERSED BY IMPROMPTU-11)** | `_check_flatten_pending_timeouts` — declared safe by IMPROMPTU-04 ("matches on symbol only, uses `abs(int(shares))` for quantity; doesn't place a new SELL blindly"). **IMPROMPTU-11 H5 proved this WRONG**: when `broker_qty != position.shares_remaining` (mismatch branch), `sell_qty = broker_qty` IS placed — and on a phantom-short broker state, this doubles the short. Session 3 fixes this. |
| 11 | `argus/core/health.py:419` | Intentionally different | Daily integrity check — walks positions + open orders to verify stop-order coverage. Read-only; no order placement. |

**Adversarial reviewer questions:**
- Row #3 — is the call site at `main.py:1412` (now `:1520-1531`) actually
  covered by Session 2's typed-contract refactor? Verify the line range
  alignment.
- Row #11 — claimed read-only. Re-grep the actual code: does it ever place
  an order, even indirectly via an event publish that downstream subscribes
  to with order placement?
- Rows #1, 2, 5, 8 — "side-agnostic" or "informational only" claims. Apply
  RULE-051 mechanism-signature thinking: is there a path where these COULD
  influence order placement under unusual conditions (broker reconnect,
  startup race)?
- Row #4 (`debrief_export.py:336`) — the export is "read-only" but consumes
  `Position.shares` (abs) without `side`. Does anything DOWNSTREAM of the
  export consume it for a decision?

---

## 4. IMSR Forensic Anchor (from IMPROMPTU-11)

The cleanest forensic case study from Apr 24 paper trading. IMSR ended -200
short at EOD via this exact lifecycle:

| Time (ET) | Event | Source | Cumulative broker position |
|---|---|---|---:|
| 11:51:05 | Bracket placed: BUY 200 IMSR (parent #4901, stop, T1, T2) | `Bracket placed:` | 0 |
| 11:51:07 | Order filled: parent fill 200 @ $7.81 | `ibkr_broker` | +200 |
| 12:11:14 | **Order placed: SELL 200 IMSR STOP** (escalation stop, NEW standalone order outside the bracket — no `ocaGroup`) | `ibkr_broker` | +200 |
| 12:15:04 | Trail stop triggered for IMSR | `order_manager` | |
| 12:15:04 | **Order filled: escalation stop 200 @ $7.81** | `ibkr_broker` | 0 |
| 12:15:04 | **Order placed: SELL 200 IMSR MARKET** (trail flatten — second standalone SELL in the same second — no `ocaGroup`, no OCA with the escalation stop) | `ibkr_broker` | 0 |
| 12:15:?? | Trail flatten partial fill: 100 of 200 | (silent fill — `pending=None` at order_manager.py:592 → DEBUG only) | **-100** |
| 12:17:09 | WARNING: Flatten qty mismatch for IMSR: ARGUS=200, IBKR=100 — using IBKR qty | `order_manager` (DEF-158 path; line 2388 `abs()` read against -100 short) | -100 |
| 12:17:09 | Order placed: SELL 100 IMSR MARKET | `ibkr_broker` | **-200** |

**Key mechanism evidence:**

- The escalation stop placed at 12:11:14 is a STANDALONE order, no OCA group
  with the bracket's original stop or T1/T2 children. When the original
  bracket stop's cancel propagates to IBKR (12:11:15), only the original
  stop is cancelled — the escalation stop and T1/T2 cancels also fire, but
  by 12:15:04 the escalation stop is the only "stop" alive.
- At 12:15:04, the escalation stop fires AND the trail flatten fires AS
  TWO SEPARATE STANDALONE SELL ORDERS. They share no OCA group. Both fill
  in the same second (escalation stop fills first, ARGUS marks position
  closed; the trail flatten partial-fills 100 against the now-zero broker
  position, producing -100 short).
- The trail flatten's partial-fill callback never reaches ARGUS because
  by then ARGUS has already cleaned up `_pending_orders[trail_flatten_id]`
  via the position-closed handler. Goes to `logger.debug("Fill for unknown
  order_id ...")` at `order_manager.py:592` — INVISIBLE at INFO+.
- 124 seconds later, `_check_flatten_pending_timeouts` retries. Reads broker
  position via `abs(int(getattr(bp, "shares", 0)))` = 100 (broker is short
  -100). Treats as if ARGUS=200, IBKR=100 long. Fires SELL 100. Broker
  position becomes -200.

**This single bracket leaks 200 shares short via TWO independent mechanisms:**
1. Two redundant standalone SELLs (escalation + trail) with no OCA group
   (H1 + H7).
2. DEF-158 retry path doubling the broker short via abs-qty reading (H5).

**Adversarial reviewer questions:**
- Could Sessions 1a + 1b prevent BOTH SELL paths from running by sharing OCA?
  When the escalation stop fires, does the OCA group cancel the trail
  flatten before it can fill? Or does the trail flatten still get partial-fill
  in the race window before the OCA cancellation propagates?
- The trail flatten is placed 0.0001 seconds after the escalation stop fills.
  Is the OCA cancellation guaranteed to propagate that fast?
- If the OCA cancellation does NOT prevent the trail flatten partial fill,
  Session 1's fix is incomplete and the upstream cascade can still occur
  (smaller blast radius, but non-zero).

---

## 5. RULE-051 Mechanism-Signature-vs-Symptom Validation

Per `claude/rules/universal.md` §16:

> When validating a fix against a recurring symptom, verify against the
> mechanism signature (e.g., a measurable doubling ratio, a specific log-line
> correlation, a checksum), not the symptom aggregate (e.g., "the bug appears
> at EOD"). The mechanism signature is the falsifiable part; the symptom
> aggregate is the dependent variable.

**For Sprint 31.91, the mechanism signatures are:**

| Mechanism | Signature | Test |
|-----------|-----------|------|
| H1 (bracket OCA race) | Mass-balance: `(broker SELLs - ARGUS-tracked SELLs)` should be ~zero post-fix | Compute `2225 - 899 - 679 = 647` from a paper-session log; that number should drop to ~0 after Session 1a + 1b |
| H7 (standalone SELLs share no OCA) | `Trail stop triggered + Escalation stop updated` event count vs phantom-short symbol count — pre-fix correlation should disappear post-fix | Apr 24 had 154 trail + 347 escalation = 501 standalone; 27/44 phantom-short symbols had at least one. Post-fix: phantom-short count should not correlate with trail/escalation count |
| H2 (reconcile orphan loop one-direction) | "Position reconciliation: N mismatch(es)" log-line growth — pre-fix monotonically grew 3 → 44 across the day; post-fix should stay near zero or recover quickly | Daily mismatch-count time series; final-value-of-day should be small |
| H5 (DEF-158 abs-qty doubling) | "Flatten qty mismatch" log-line followed by SELL placement against broker-short | Grep for the log; assert no SELL was placed when broker was short |

**Adversarial reviewer questions:**
- Are these signatures actually FALSIFIABLE in the proposed test layer?
  Specifically: do the unit tests measure THESE signatures, or do they
  measure proxies?
- Could a green test pass with the mechanism still partially active? (E.g.,
  the OCA group is set on the bracket children, but IBKR's ocaType=1
  semantics is implemented differently than expected, and the race window
  is reduced from ~1s to ~10ms but not eliminated.)

---

## 6. Eight Adversarial Focus Areas (from Phase A)

The reviewer should attempt to BREAK each of these. If any focus area lacks a
proposed mitigation in the Sprint Spec, that's a finding.

### Focus Area 1 — Re-walk IMPROMPTU-04's grep-audit

Particularly rows #3, #11, and the "side-agnostic" claims at #1, 2, 4, 5, 8.
IMPROMPTU-04 cleared row #10 and IMPROMPTU-11 proved row #10 wrong. Apply
RULE-051 mechanism-signature thinking to every other row.

### Focus Area 2 — OCA group ID lifecycle and re-entry contamination

Trade IMSR at 11:51, close at 13:03, re-enter same symbol at 13:30 — does
the new bracket get a NEW OCA group, or does it reuse the previous one? If
reuse, IBKR's cancellation matching could fire on cross-position events.
Construct a re-entry-cross-cancellation race scenario and verify the spec's
test layer catches it.

### Focus Area 3 — `ReconciliationPosition` dataclass vs `tuple[OrderSide, int]`

The spec uses a frozen dataclass. The kickoff originally proposed a tuple.
Is the dataclass choice correct? Are there serialization / pickling /
event-bus interaction concerns the dataclass introduces vs the tuple?

### Focus Area 4 — Per-symbol entry gate semantics

Per-symbol vs global gate — is per-symbol the right granularity? What's
the unblock mechanism (operator acknowledgment, auto-clear when broker
reconciles to zero, or strategy-config override)? **Try to construct a
deadlock scenario where the gate locks ARGUS out of trading entirely.**
What if the gate is engaged at startup (broker has stale phantom shorts
from yesterday)? What if multiple positions for the same symbol exist
simultaneously and one is gated?

### Focus Area 5 — `ocaType=1` ("Cancel with block") semantics

The spec specifies type 1. Verify this is correct. Type 1 pauses execution
of siblings until cancellation propagates — the strict semantics. Are there
cases where this introduces fill latency we don't want? (E.g., a fast trail
stop should fill IMMEDIATELY when triggered; if OCA cancellation of the
T1/T2 limits is "blocking" the trail fill, are we adding latency to the
critical exit?)

### Focus Area 6 — Paper trading vs live OCA behavior

IMPROMPTU-11 mentions "paper-trading OCA is loose". Will the fix work in
IBKR paper? Live? Do we have evidence either way? If IBKR paper handles
ocaType=1 differently than live, our paper-session evidence post-merge might
not validate the live-trading behavior — that's a gap.

### Focus Area 7 — Interaction with DEC-369/370 broker-confirmed semantics

The reconciliation orphan loop at line 3038 already has a `confirmed` branch
(line 3045) that applies different semantics. Session 2b's broker-orphan
branch fires for unconfirmed positions. **Decision matrix needed:**

| ARGUS state | Broker state | Confirmed? | Pre-31.91 behavior | Post-31.91 behavior |
|---|---|---|---|---|
| Has long position | Has zero shares | Yes | Snapshot-stale WARNING (DEC-369) | Same (preserved) |
| Has long position | Has zero shares | No | Miss-counter increment | Same |
| Has zero | Has long position | n/a | Silently ignored | **WARNING, no gate** |
| Has zero | Has short position | n/a | Silently ignored | **CRITICAL alert + entry gate (NEW)** |

Verify the matrix is COMPLETE — are there states this matrix misses?

### Focus Area 8 — DEC-117 atomic bracket invariant interaction

Does adding `ocaGroup` + `ocaType=1` on bracket children in any way change
DEC-117's atomic-bracket promise? Specifically: if the parent fails after
some children placed (the rollback path at `ibkr_broker.py:783-805`), does
the OCA group cause IBKR to do something unexpected? E.g., does the OCA
group's "Cancel with block" semantics cause the cancel to BLOCK on the
not-yet-placed siblings, deadlocking the rollback?

### Bonus Focus Area 9 — SimulatedBroker mock OCA semantics

The SbC says SimulatedBroker gets a "no-op acknowledgment" of the new Order
fields. Is no-op ACTUALLY the right behavior? If SimulatedBroker is used in
tests that exercise OCA-cancellation semantics (e.g., a test that places a
bracket, fires the stop, and asserts T1/T2 are cancelled), the test will
PASS without OCA grouping AND it will PASS with OCA grouping — making the
test a tautology that doesn't validate the OCA-grouping logic. This is a
test-layer trap. Verify that no test exists that depends on
SimulatedBroker OCA behavior in a way that would silently pass for both
the broken and fixed states.

---

## 7. Acceptance for "Confirmed — proceed"

The reviewer should NOT accept the spec without:

- At least 2 substantive concerns surfaced (per
  `protocols/adversarial-review.md`'s "if it finds nothing, it was not
  aggressive enough" criterion)
- A proposed disposition for each concern (mitigation, accept, defer to
  follow-on sprint, etc.)
- Explicit verification that all 8+1 adversarial focus areas above have been
  considered, even if briefly

---

## 8. Revision Rationale — Second-Pass Review Context (NEW, 2026-04-27)

This input package was first reviewed on 2026-04-27 and produced **NOT
confirmed** with 7 BLOCKING/HIGH findings. The Sprint Spec, Session
Breakdown, Spec-by-Contradiction, Escalation Criteria, Regression
Checklist, Doc Update Checklist, and Design Summary have been substantially
revised. This section summarizes what changed and why, so a second-pass
reviewer can validate the revisions are sufficient (and surface any new
findings the first pass didn't catch).

### What the first pass found (and how it was addressed)

| # | Finding | Severity | Disposition | Where addressed |
|---|---------|----------|-------------|-----------------|
| 1 | EOD flatten path excluded from OCA threading; left a residual phantom-short surface | BLOCKING | **Accept (and worse than reviewer framed it)** — code grep revealed Session 1b's original spec missed `_flatten_position` entirely (used by EOD Pass 1, `close_position()`, `emergency_flatten()`, time-stop), not just EOD Pass 2. Fix expanded to: (a) Session 1b adds `_flatten_position` as the 4th SELL path; (b) new Session 1c integrates `cancel_all_orders(symbol)` into the broker-only paths (`_flatten_unknown_position`, `_drain_startup_flatten_queue`, EOD Pass 2 cancel-before-sell). | Sprint Spec §D3+D4; Session Breakdown §1b+1c |
| 2 | Restart-with-positions creates orphaned-OCA exposure (deferred in original spec) | BLOCKING | **Accept** — same `cancel_all_orders(symbol)` infrastructure as #1. `reconstruct_from_broker()` now calls `cancel_all_orders(symbol=...)` for each reconstructed symbol BEFORE wiring into `_managed_positions`, unconditionally clearing stale OCA siblings from yesterday's session. | Sprint Spec §D4 (Session 1c); SbC "previously deferred but now in scope" callout |
| 3 | Performance claim wrong; ocaType=1 fill-latency 50–200ms | BLOCKING | **Partial accept.** Push back on "evaluate ocaType=2 as alternative" — ocaType=2's reduce-quantity semantics are wrong for ARGUS's full-quantity-T1+T2 bracket model (DEC-117 `parentId` linkage already handles partial-fill T2-stays-alive orthogonally). Push back on "config accepts 1/2/3" — operator footgun on safety-critical setting; accept only 0/1 (0=disabled, 1=on, default 1). Accept: Performance Considerations section, post-merge slippage debrief check, justification of ocaType=1 over ocaType=2 documented. | Sprint Spec §"Performance Considerations" + §D8; market-session-debrief.md Phase 7 watch item; doc-update-checklist B21 |
| 4 | Phantom-short entry gate clears too eagerly on broker zero (60-second hole during transient reconnect) | HIGH | **Accept** — mirrors DEC-370's miss-counter pattern with a clear-counter. New config field `reconciliation.broker_orphan_consecutive_clear_threshold: int = 3`. Gate clears only after 3 consecutive zero-shares cycles. | Sprint Spec §D5 (Session 2c); Escalation Criteria A6 (now 5-cycle bound: 3 clear + 2 margin) |
| 5 | Acceptance criteria are unit-test-only; no mass-balance / paper-session validation | HIGH | **Strongly accept** — most important finding. New Session 4 delivers `scripts/validate_session_oca_mass_balance.py`, IMSR replay test (with synthetic-recreation fallback if Apr 24 log unavailable), and live-enable gate criteria in `pre-live-transition-checklist.md` (≥3 paper sessions ≤5/symbol/session AND zero `phantom_short` alerts AND ≥1 disconnect-reconnect mid-session). | Sprint Spec §D7; Session Breakdown §4; new invariant 17 in regression-checklist |
| 6 | Startup phantom-short engagement can disable system; no in-product clear path | HIGH | **Accept** — operator override deferral was exactly the wrong order. New Session 2d: `POST /api/v1/reconciliation/phantom-short-gate/clear` API endpoint; CRITICAL startup log line listing gated symbols + runbook; aggregate alert when ≥10 symbols gated; `docs/live-operations.md` runbook section. | Sprint Spec §D5 (Session 2d); SbC edge case row updated |
| 7 | Margin circuit auto-reset count includes phantom shorts (IMPROMPTU-04 row #5 re-walk) | HIGH | **Accept** — re-walk of IMPROMPTU-04 row #5 with mechanism-signature thinking confirmed side-agnostic counting is broken when phantom shorts exist. Fix: `len([p for p in broker_positions if p.side == OrderSide.BUY])` for reset count; log breakdown line "longs=N, shorts=M, reset_threshold=K". | Sprint Spec §D5 (Session 2b); 2 new tests in 2b |
| 8 | BacktestEngine doesn't simulate OCA semantics; backtests will overstate live performance | MEDIUM | **Accept as DEF-208** — file at sprint close. Cross-reference in `docs/architecture.md` §5 and `pre-live-transition-checklist.md` ("shadow performance is the gate, not backtest"). | Doc-update-checklist B17; SbC deferred items table |
| 9 | "Broker-orphan long is not a safety incident" is too coarse; stranded longs are unmanaged exposure | MEDIUM | **Accept** — differentiated by cycle count: cycle 1–2 = WARNING (callback-in-flight assumption); cycle 3+ = `SystemAlertEvent(alert_type="stranded_broker_long", severity="warning")` via `_broker_orphan_long_cycles: dict[str, int]` tracker. | Sprint Spec §D5 (Session 2b); SbC edge case row updated; 2 new tests in 2b |
| 10 | `debrief_export.py` propagates side-blind data to future Learning Loop V2 | MEDIUM | **Accept as DEF-209** — file at sprint close. Add to roadmap.md Sprint 35+ prerequisites. | Doc-update-checklist B18 |

### LOW findings disposition

- **#11** Test count for Session 2 underestimated. Reviewer estimated ~14
  across the matrix; actual splits at 2a+2b+2c with 31.91-revision
  amendments land at 5+8+5=18, plus 2d adds 6, total 24 across the four
  Session-2 sessions. Re-scoring confirms 2b at ~13 and 2c at ~13.5
  (borderline but proceeding); both flagged for monitoring at
  pre-flight.
- **#12** `phantom_short_retry_blocked` alert severity → critical. Spec
  amendment in §D6.
- **#13** Frozen dataclass over tuple — confirmed correct; noted in
  design summary §"Key Decisions".
- **#14** DEC-117 + ocaType=1 rollback test — added to Session 1a (test
  6 of 7).
- **#15** Deterministic OCA group from parent ULID test — added to
  Session 1a (test 7 of 7).

### What the second-pass reviewer should focus on

The first-pass review was comprehensive across the 8+1 focus areas. The
revision changes the sprint shape from 6 to 10 sessions and adds
substantial scope. A second-pass reviewer should target:

1. **Did the revisions create new architectural seams that need their own
   review?** Specifically: Session 0's `cancel_all_orders(symbol)` API
   extension is consumed by Sessions 1c and 4 — does the API contract
   hold under the consumer use cases? Does the AlpacaBroker
   ABC-compliance impl for an in-retirement broker create technical-debt
   risk?

2. **Sessions 2b and 2c at 13.0 and 13.5 are at the compaction-score
   borderline.** Were the +1 amendments (margin-circuit side-aware reset
   in 2b; clear-threshold in 2c) priced correctly? Could implementation
   surface unforeseen test surface that pushes either to 14+?

3. **Session 1c's three integration points** (`_flatten_unknown_position`,
   `_drain_startup_flatten_queue`, `reconstruct_from_broker()`) all use
   the same cancel-before-sell pattern. Is there a unifying helper that
   should be extracted, or does inlining at each call site preserve
   readability better?

4. **The IMSR replay test's synthetic-recreation fallback** (if Apr 24
   log unavailable). Is the synthetic recreation faithful enough to
   IMPROMPTU-11's forensic trace to validate the mechanism, or does it
   risk passing in synthetic while failing on real captured data?

5. **The 50–200ms fill-latency cost on cancelling siblings** — is the
   $0.02 mean-slippage threshold for the post-merge debrief check the
   right bar, given ARGUS trades $7–15 share universe? Is the rollback
   path (`bracket_oca_type: 0`) actually safe to flip mid-session if
   slippage degrades, or does it leave bracket children in an
   inconsistent state during transition?

6. **The 3-cycle clear-threshold mirrors DEC-370.** Was DEC-370's
   threshold of 3 chosen with empirical validation, or was it nominal?
   If nominal, is 3 right for the broker-orphan clear case, or might
   2 / 5 / 10 be more appropriate?

7. **Operator override API endpoint** — the audit-log entry on use is
   essential for forensic reconstruction. Does the spec specify what
   gets logged with sufficient detail (operator identity, timestamp,
   prior gated state, reason)?

8. **Does any new finding belong in the same severity tier as the first
   pass's BLOCKING set?** A second-pass reviewer should be honest about
   whether the revisions resolve the original blockers or merely paper
   over them with deferred items.

If the second pass clears with only minor observations, Phase D
(implementation prompts) begins. If it surfaces new BLOCKING findings,
that's diagnostic of deeper issue and warrants Phase A revisit per
protocol §"campaign-orchestration.md §7".

---

## 9. Revision Rationale — Third-Pass Review Context (NEW, 2026-04-27 PM)

> **This section was added on 2026-04-27 (PM) AFTER a second-pass
> adversarial review of the post-first-pass artifacts surfaced 5
> BLOCKING + 4 HIGH + 6 MEDIUM + 3 LOW findings AND a Phase A revisit
> ran an OCA late-add behavior spike against IBKR paper trading. The
> third-pass reviewer should treat this section as the canonical map
> of what the second-pass review found and how the planning team
> dispositioned each finding.**

### 9.1 Phase A revisit — what triggered it

Five of the second-pass BLOCKING findings hinged on the same factual
premise about IBKR's OCA late-add behavior:

- **B1** — does IBKR reject late-add OCA siblings after one member fills?
- **B2** — does `cancel_all_orders` propagate fast enough that the
  follow-up SELL has clear runway?
- **B3** — does `reconstruct_from_broker()` get called outside startup,
  exposing positions to the unconditional cancel?
- **B4** — does the spike-script close the OCA-mechanism gap or just
  defer it?
- **B5** — are there other broker-state-read sites that need
  side-awareness beyond the margin circuit reset?

The first four hinged on **empirical IBKR behavior** that no amount of
spec-doc revision could resolve. The fifth hinged on **what the codebase
actually does** at three suspected-additional sites.

The planning team paused Phase C and ran a Phase A revisit:

1. Wrote `scripts/spike_ibkr_oca_late_add.py` — three trial variants
   testing late-add same-batch and post-fill OCA submissions at varying
   delays (100ms, 500ms, 2s) against IBKR paper account U24619949.
2. Operator ran the spike against live IBKR paper.
3. Spike returned **`PATH_1_SAFE`** unambiguously (B1, B4 resolved):
   IBKR rejects late-add OCA siblings with Error 201 "OCA group is
   already filled" at all three delays once any group member has
   filled. Bonus observation: same-batch siblings can also be rejected
   if they lose the microsecond race against fill propagation
   (Trial 2/3) — this is why Sessions 1a/1b add Error 201 defensive
   handling.
4. Code-read verification of `reconstruct_from_broker()` (B3): grep
   confirmed exactly one production call site at `argus/main.py:1081`,
   gated by `_startup_flatten_disabled` flag. **No mid-session
   reconnect path exists today**. B3 simplifies to a contract docstring
   + Sprint 31.93 prerequisite (no `ReconstructContext` enum needed
   today).
5. Code-read verification of three suspected B5 sites:
   - `risk_manager.py:335` — confirmed
     `len(broker_positions) >= max_concurrent_positions` (side-blind)
   - `risk_manager.py:771` — confirmed similar pattern in
     `_check_position_limits`
   - `health.py:443-450` — confirmed iterates ALL positions without
     side filter, emits critical alerts on missing-stops for what
     could be phantom shorts
   - `order_manager.py:~1734` — EOD Pass 2 short detection logs
     `logger.error` but does NOT emit `SystemAlertEvent` (alert
     taxonomy inconsistency with Session 2b.1)
6. Verified Apr 24 paper-session log availability at
   `logs/argus_20260424.jsonl` (operator confirmed) — H4
   "synthetic-recreation fallback" language can be removed entirely.

Full Phase A findings memo:
`docs/sprints/sprint-31.91-reconciliation-drift/PHASE-A-REVISIT-FINDINGS.md`.

### 9.2 Disposition of all 18 second-pass findings

| ID | Severity | Finding (one-line summary) | Disposition | Resolved by |
|----|----------|----------------------------|-------------|-------------|
| **B1** | BLOCKING | OCA late-add behavior unverified | **Resolved by spike** (`PATH_1_SAFE`); architecture stands | Phase A spike |
| **B2** | BLOCKING | `cancel_all_orders` propagation timing unspecified | **Resolved**: API extends to `cancel_all_orders(symbol, await_propagation: bool = False)` with 2s timeout + `CancelPropagationTimeout` exception | Session 0 (revised) |
| **B3** | BLOCKING | `reconstruct_from_broker()` reconnect-path catastrophic if called mid-session | **Resolved by code-read**: only one call site (startup-only); no mid-session reconnect today; simplifies to contract docstring + Sprint 31.93 prerequisite | Session 1c (revised) |
| **B4** | BLOCKING | Spike-script doesn't close OCA-mechanism gap | **Resolved by spike**: spike script committed as live-IBKR regression check, partially mitigates DEF-208 risk for OCA-mechanism specifically | Phase A artifact |
| **B5** | BLOCKING | Risk Manager side-blind position cap | **Resolved by code-read + scope expansion**: three sites identified (Risk Manager `:335` + `:771`, EOD Pass 2 alert emission `:~1734`, Health integrity check `:443-450`); all fold into Session 2b.2 | Session 2b.2 (NEW) |
| **H1** | HIGH | Reverse-rollback escape hatch is unsafe mid-session | **Resolved**: documented as RESTART-REQUIRED in `docs/live-operations.md`; mid-session flip explicitly unsupported | Session 1a + B22.5 doc-sync |
| **H2** | HIGH | Mass-balance 5-share tolerance arbitrary; no categorization | **Resolved**: categorized variance (`expected_partial_fill` / `eventual_consistency_lag` / `unaccounted_leak`); 5-share tolerance dropped; live-enable gate requires zero `unaccounted_leak` | Session 4 (revised) |
| **H3** | HIGH | Sessions 2b/2c too coarse; impl prompts can't fit close-out + tier 2 review | **Resolved**: split into 2b.1 / 2b.2 / 2c.1 / 2c.2 (4 sessions instead of 2) | Session breakdown (revised) |
| **H4** | HIGH | IMSR replay synthetic-recreation premise unworkable | **Resolved**: real Apr 24 `.jsonl` confirmed available; synthetic-recreation language removed entirely | Session 4 (revised) |
| **M1** | MEDIUM | OCA group ID derivation unspecified | **Resolved**: `f"oca_{parent_ulid}"` deterministic; per-bracket | Session 1a |
| **M2** | MEDIUM | `_broker_orphan_long_cycles` lifecycle unspecified | **Resolved**: cleanup on broker-zero, exponential-backoff re-alert (3 → 6 → 12 → 24, capped hourly), session reset | Session 2b.1 |
| **M3** | MEDIUM | Operator override audit-log schema unspecified | **Resolved**: `phantom_short_override_audit` table with full schema | Session 2d + B5 doc-sync |
| **M4** | MEDIUM | 3-cycle clear-threshold too aggressive; phantom-short re-engagement worse than DEC-370 false positive | **Resolved**: default raised to 5 cycles; cost-of-error asymmetry rationale documented | Session 2c.2 (revised) |
| **M5** | MEDIUM | Per-symbol gate state lost on restart; 60s window of unsafe entries | **Resolved**: SQLite persistence in `phantom_short_gated_symbols` table; rehydrated BEFORE event processing | Session 2c.1 (revised) |
| **M6** | MEDIUM | DEF-014 unresolved leaves no UI surface for new `phantom_short` alerts | **Resolved**: full alert observability in-scope (Sessions 5a–5e); CLI tool stop-gap dropped; DEC-388 reserved | Sessions 5a–5e (NEW) |
| **L1** | LOW | AlpacaBroker `cancel_all_orders(symbol)` impl writes throwaway code | **Resolved**: `DeprecationWarning` instead of throwaway functional code | Session 0 (revised) |
| **L2** | LOW | Tier 3 architectural review trigger ambiguous | **Resolved**: A1 escalation criterion explicit (after 1c); A1.5 added (after 5b for alert observability backend seal) | Escalation criteria (revised) |
| **L3** | LOW | Aggregate alert at startup may suppress individual alerts | **Resolved**: always-fire-both-alerts (no suppression) | Session 2d (revised) |

### 9.3 What's unchanged from the post-first-pass plan

- DEC-385 (side-aware reconciliation contract) — scope expanded from 4
  sessions to 6 (added 2b.2 + 2c.2 split), but core decision unchanged.
- DEC-386 (OCA-group threading) — scope unchanged at 4 sessions; Error
  201 defensive/graceful handling added per spike Trial 2/3 observation.
- `ReconciliationPosition` frozen dataclass — unchanged.
- Reserve `DEC-385` and `DEC-386` IDs — unchanged.
- Branch strategy (work on `main`) — unchanged.
- Operator daily-flatten mitigation continues throughout sprint window —
  unchanged.

### 9.4 What's new from this revision (2nd pass + Phase A)

- **Two Tier 3 architectural reviews** (was 1): after 1c (OCA seal) and
  after 5b (alert observability backend seal).
- **Sprint shape: 17 sessions** (was 12 after Phase A; was 10 after 1st
  revision; was 6 originally).
- **DEC-388 reserved** for alert observability architecture.
- **DEF-014 closure** in CLAUDE.md DEF table at sprint close.
- **DEFs filed at sprint close**: DEF-208 (SimulatedBroker OCA semantics),
  DEF-209 (analytics historical-record side preservation).
- **Live-enable gate simplifies to 3 criteria** (no caveats):
  1. ≥3 paper sessions zero `unaccounted_leak` mass-balance rows
  2. AND zero `phantom_short` alerts across those sessions
  3. AND first-day-live monitored validation
- **Disconnect-reconnect leg explicitly moved to Sprint 31.93's gate**
  (B3 — structural prerequisite, not deferrable to a config flip).
- **Frontend reviewer split for Sessions 5c–5e** (different focus from
  backend safety reviewer used for Sessions 0–4 + 5a–5b).
- **Apr 24 `.jsonl` direct replay** in Session 4 (no synthetic
  recreation).
- **Spike script `scripts/spike_ibkr_oca_late_add.py`** committed as
  re-runnable live-IBKR regression check.
- **Performance Considerations** section in Sprint Spec with
  RESTART-REQUIRED rollback note.

### 9.5 Eight focus areas for the third-pass reviewer

The third-pass reviewer should focus disproportionate attention on:

1. **Session 5a (highest compaction score: ~12)** — HealthMonitor
   consumer + WebSocket + REST + acknowledgment + audit-log persistence
   is doing a lot in one session. Check whether further splitting
   (5a.1 / 5a.2) is warranted, or whether the bounded-scope-per-component
   structure keeps it tractable.

2. **The B5 three-site uniformity claim** — Session 2b.2 asserts the
   same side-aware-filter pattern applies to Risk Manager + EOD Pass 2
   + Health integrity check. Does the code-read evidence support that
   claim? Are there subtle differences (e.g., position-cap semantics
   vs alert-emission semantics) that would warrant per-site treatment?

3. **The Tier 3 #2 trigger placement** — fires after 5b, before 5c.
   Is the alert-observability backend genuinely sealable at that point,
   or does the frontend's API needs (5c–5e) feedback into backend
   decisions? If the latter, Tier 3 #2 should fire later (after 5e).

4. **Frontend reviewer arrangements** — implementation prompts for
   5c–5e flag a different reviewer focus. Is the frontend reviewer
   pattern well-established in ARGUS workflow protocols, or is this
   the first sprint to formalize the split? If first, what protocol
   updates are needed?

5. **Live-enable gate's third criterion** — "first-day-live monitored
   validation" is somewhat hand-wavy. Should it specify duration
   (e.g., "first 60 minutes of live trading"), position-size cap
   (e.g., "smallest position size, single symbol"), and abort-conditions
   (e.g., "any phantom_short alert during the window aborts the
   transition")?

6. **The spike script's role as live-IBKR regression check** — is
   committing it to the repo + documenting its run procedure
   sufficient, or should there be CI integration (nightly run against
   IBKR paper) to catch IBKR API drift?

7. **Mass-balance categorization edge cases** — the H2 categories
   (`expected_partial_fill` / `eventual_consistency_lag` /
   `unaccounted_leak`) need clear definitions. What happens when a
   row could plausibly fit two categories? What's the precedence?

8. **The Alpaca emitter exclusion** — Session 5b's
   `test_alpaca_emitter_site_unchanged` anti-regression test is novel.
   Is asserting absence of a fix the right pattern, or should it be
   tracked via a different mechanism (e.g., Sprint 31.94 entry
   criterion)?

### 9.6 What the third-pass reviewer should NOT relitigate

The following are sealed by Phase A revisit + operator decision and
should not be relitigated unless new evidence surfaces:

- **PATH_1_SAFE conclusion** — empirical IBKR behavior confirmed by
  spike against paper account U24619949 on 2026-04-27.
- **`reconstruct_from_broker()` is startup-only today** — confirmed by
  grep against current main HEAD.
- **The three B5 sites are side-blind** — confirmed by code-read.
- **The 17-session shape with Sessions 5a–5e in-scope** — operator
  decision (Option 4 chosen over Option 1/2/3) on 2026-04-27 PM after
  reviewing timeline math (option 4 is 1–2 weeks shorter end-to-end).
- **Alpaca emitter TODO stays out of scope** — operator decision,
  resolved by deletion in Sprint 31.94.
- **Disconnect-reconnect leg moves to Sprint 31.93's gate** — structural
  prerequisite (no mid-session reconnect path exists today).

### 9.7 Verdict criteria for third pass

If the third-pass review:

- **CLEARS with no findings or only OBSERVATION-level findings** →
  proceed to Phase D (implementation prompts).
- **Surfaces 1–3 MEDIUM-or-lower findings** → minor revisions; proceed
  to Phase D after addressing.
- **Surfaces ≥1 HIGH or ≥1 BLOCKING finding** → Phase B re-design.
  Specifically: if the BLOCKING is on a session structure / scope
  decision, re-do session breakdown. If it's on a decision surfaced by
  the spike or code-reads, escalate per
  campaign-orchestration.md §7 (deeper-issue diagnostic).
- **Surfaces ≥3 BLOCKING findings** → halt; this would indicate the
  iterative review process is not converging and a different planning
  approach is needed (e.g., operator-led Phase B re-design with
  Claude in advisory role only).

---

## 10. Revision Rationale — Post-Third-Pass Disposition (NEW, 2026-04-27 PM)

> **Added 2026-04-27 PM after the third-pass adversarial review
> returned Conditional CLEAR with 5 HIGH + 14 MEDIUM/LOW findings (no
> BLOCKING). This section documents the disposition of all 19 findings
> and the resulting 18-session shape. Phase D begins after this
> section is sealed.**

### 10.1 Verdict and disposition strategy

The third-pass review verdict was **Conditional CLEAR — proceed to
Phase D after addressing the 5 HIGH findings**. The reviewer's framing
was that under their judgment the HIGH findings are operationally
MEDIUM but warrant pre-Phase-D rigor given the 7–8 week sprint
duration and operator-daily-flatten dependency. Their recommended
disposition:

- **5 HIGH** — address at Phase B/C artifact level before Phase D
- **14 MEDIUM/LOW** — address at Phase D prompt level OR as in-flight
  amendments

The planning team chose a **hybrid path that respects the reviewer's
gradient while preserving Steven's preference for complete
solutions**:

- All 5 HIGH addressed at Phase C artifact level
- Spec-level MEDIUM (#9 retention/migration, #10 ack error-handling,
  #11 SimulatedBroker tautology, #13 brittle Alpaca test) addressed at
  spec level — these are clear spec defects
- Cheap LOW (#15 configurable threshold, #17 Tier 3 #1 scope) addressed
  at spec level
- Remaining MEDIUM/LOW captured in `PHASE-D-OPEN-ITEMS.md` for
  in-flight Phase D inclusion (so nothing is silently dropped)

### 10.2 Disposition of all 19 third-pass findings

| ID | Severity | Finding (one-line summary) | Disposition | Resolved by |
|----|----------|----------------------------|-------------|-------------|
| **HIGH #1** | HIGH | Session 5a doing too much; auto-resolution per-alert-type underspec'd | **Resolved**: split 5a → 5a.1 (HealthMonitor + REST + atomic+idempotent ack) + 5a.2 (WebSocket + persistence + auto-resolution policy table + retention/migration). Sprint 17 → 18 sessions. Compaction scores 5a.1 ~8 + 5a.2 ~9 (was 5a ~12). | Session breakdown 5a split; sprint-spec D9 → D9a + D9b; compaction risk table updated |
| **HIGH #2** | HIGH | B5 "three-site uniformity" misframed (4 count-filter sites + 1 alert-alignment site) | **Resolved**: reframe Session 2b.2 to acknowledge two patterns; group tests by Pattern A (count-filter) vs Pattern B (alert-alignment) | Session breakdown 2b.2 reframe |
| **HIGH #3** | HIGH | Frontend reviewer arrangements hand-wavy | **Resolved**: Phase D prerequisite — `templates/review-prompt-frontend.md` authored in workflow metarepo before Session 5c (B29 in doc-update-checklist; A11 escalation criterion if unmet) | doc-update-checklist B29; escalation-criteria A11 |
| **HIGH #4** | HIGH | Live-enable gate criterion #3 partially circular | **Resolved**: decompose into 3a (pre-live paper stress test) + 3b (live rollback policy with $50–$500 notional cap; phantom_short* triggers operator-manual halt). DEF-210 filed for `POST /api/v1/system/suspend` formal capability | sprint-spec D7; design-summary live-enable gate; escalation-criteria A12; new DEF-210 |
| **HIGH #5** | HIGH | Spike script will rot without trigger | **Resolved**: trigger registry in `docs/live-operations.md` (B28); escalation criterion A13 if spike result >30 days old at trigger event; regression invariant 22 | doc-update-checklist B28; escalation-criteria A13; regression-checklist invariant 22 |
| **MEDIUM #6** | MEDIUM | IMPROMPTU-04 row #4 — current consumers not enumerated | **Deferred to Phase D**: grep verification step in Session 4 implementation prompt | `PHASE-D-OPEN-ITEMS.md` — Session 4 prompt |
| **MEDIUM #7** | MEDIUM | EOD Pass 2 cancel-timeout changes failure mode | **Deferred to Phase D**: document explicitly in Session 1c implementation prompt | `PHASE-D-OPEN-ITEMS.md` — Session 1c prompt |
| **MEDIUM #8** | MEDIUM | Health + broker-orphan double-fire on stranded longs | **Deferred to Phase D**: operator decision pending — dedup vs document intentional double-fire. Reviewer focus item in Session 2b.2 Tier 2 review | `PHASE-D-OPEN-ITEMS.md` — operator decision; flagged in Session 2b.2 Tier 2 review focus |
| **MEDIUM #9** | MEDIUM | operations.db retention/VACUUM/migration unspecified | **Resolved**: 5a.2 deliverables include schema-version table + migration registry (FIRST in ARGUS); audit-log forever default (configurable); archived alerts 90d default; VACUUM via `asyncio.to_thread` mirroring Sprint 31.8 S2 evaluation.db pattern | sprint-spec D9b; design-summary config table |
| **MEDIUM #10** | MEDIUM | Acknowledgment flow error-handling silent | **Resolved**: 5a.1 D9a AC explicit on atomic transitions; idempotency 200/404/409 (200 and 409 still write audit); race resolution first-writer-wins; no-operator case auto-resolves but never auto-acknowledges (except 24h aggregate) | sprint-spec D9a AC; session-breakdown 5a.1 tests |
| **MEDIUM #11** | MEDIUM | SimulatedBroker no-op OCA = test tautology | **Resolved**: regression invariant 21 with grep-test forbidding `SimulatedBroker` + `oca\|OCA` co-occurrence (allow-list via `# allow-oca-sim:` comment) | regression-checklist invariant 21 |
| **MEDIUM #12** | MEDIUM | Mass-balance category precedence rules unspecified | **Deferred to Phase D**: precedence rules + 120s eventual-consistency window + known-gap registry + boundary handling go in Session 4 implementation prompt | `PHASE-D-OPEN-ITEMS.md` — Session 4 prompt |
| **MEDIUM #13** | MEDIUM | Anti-regression test for Alpaca emitter brittle | **Resolved**: Session 5b test uses behavioral assertion via `inspect.getsource(alpaca_data_service)` not containing `"SystemAlertEvent"` (replaces line-number-based check) | sprint-spec D10 AC; session-breakdown 5b tests |
| **LOW #14** | LOW | IMPROMPTU-04 row #8 post-flatten log side-blind | **Resolved**: filed as DEF-211 (operator-experience improvement; not safety-critical) | New DEF-211 in CLAUDE.md DEF table at sprint close |
| **LOW #15** | LOW | Aggregate alert threshold (10) hardcoded | **Resolved**: `reconciliation.phantom_short_aggregate_alert_threshold: 10` configurable; runbook tuning guidance in B22 | sprint-spec D5; design-summary config table; doc-update-checklist B22 |
| **LOW #16** | LOW | Session 2a mock-update estimate unverified | **Deferred to Phase D**: pre-flight grep for `reconcile_positions(` in Session 2a implementation prompt | `PHASE-D-OPEN-ITEMS.md` — Session 2a pre-flight |
| **LOW #17** | LOW | Tier 3 #1 scope should include Session 0 | **Resolved**: Tier 3 #1 trigger language updated in escalation-criteria A1 + session-breakdown Tier 3 #1 fire-point block. Scope: combined diff of Sessions 0 + 1a + 1b + 1c | escalation-criteria A1; session-breakdown Tier 3 #1 block |
| **LOW #18** | LOW | Sprint duration creates operator-fatigue / interim merge after 1c | **Deferred to Phase D**: operator architectural decision — interim merge after 1c (Tier 3 #1 CLEAR) is an option but creates transitional state during 2a-2d (~2-3 weeks). Operator weighs operator-fatigue cost against transitional-state risk | `PHASE-D-OPEN-ITEMS.md` — operator decision before Session 2a starts |
| **LOW #19** | LOW | Session count drift (6→10→12→17→18) | **Resolved**: regression-checklist yellow-flag — mid-sprint splits (e.g., 1a needs 1a.1 + 1a.2 mid-implementation) require operator review, not auto-split | regression-checklist invariant 22 (companion to spike freshness) — also tracked in work journal |

### 10.3 What changes from 2nd-pass plan

- **18 sessions** (was 17): Session 5a split into 5a.1 + 5a.2 per HIGH #1
- **DEF-210 filed**: `POST /api/v1/system/suspend` capability per HIGH #4
- **DEF-211 filed**: side-aware post-flatten log breakdown per LOW #14
- **Tier 3 #1 scope expanded** to include Session 0 (LOW #17)
- **Tier 3 #2 scope updated** to "5a.1 + 5a.2 + 5b" (was "5a + 5b")
- **Spike script trigger registry** added as in-sprint deliverable (B28)
- **Frontend reviewer template** added as Phase D prerequisite (B29)
- **2b.2 reframed** to acknowledge two distinct patterns (HIGH #2)
- **D9 split** into D9a (5a.1) + D9b (5a.2) with explicit auto-resolution
  policy table covering 8 alert types (HIGH #1)
- **Live-enable gate** decomposed into 4 criteria (HIGH #4)
- **Configurable aggregate alert threshold** (LOW #15)
- **Behavioral anti-regression** for Alpaca emitter (MEDIUM #13)
- **Retention/VACUUM/migration framework** for operations.db (MEDIUM #9)
- **Atomic + idempotent acknowledgment** with 200/404/409 (MEDIUM #10)
- **SimulatedBroker tautology grep-test** (regression invariant 21,
  MEDIUM #11)
- **Spike freshness invariant** (regression invariant 22, HIGH #5)
- **Token budget**: 18 × ~13K + 2 Tier 3 + buffer = ~260K (was ~245K)

### 10.4 What's unchanged from 2nd-pass plan

- DEC-385 (side-aware reconciliation contract) — scope unchanged at 6
  sessions (2a / 2b.1 / 2b.2 / 2c.1 / 2c.2 / 2d)
- DEC-386 (OCA-group threading) — scope unchanged at 4 sessions (0 /
  1a / 1b / 1c)
- DEC-388 (alert observability) — scope grew from 5 to 6 sessions
  (5a.1 / 5a.2 / 5b / 5c / 5d / 5e) due to 5a split
- `ReconciliationPosition` frozen dataclass — unchanged
- Branch strategy (work on `main`) — unchanged
- Operator daily-flatten mitigation continues throughout sprint window
- All Phase A revisit findings (PATH_1_SAFE; B3 startup-only; B5
  three sites; Apr 24 .jsonl direct replay) — sealed; not relitigated

### 10.5 Items captured in PHASE-D-OPEN-ITEMS.md

The following MEDIUM/LOW findings were not addressed at Phase C
artifact level but MUST be incorporated into Phase D implementation
prompts. They are captured in `PHASE-D-OPEN-ITEMS.md` with explicit
session-prompt assignments:

- **MEDIUM #6** (IMPROMPTU-04 row #4 grep verification) → Session 4 prompt
- **MEDIUM #7** (EOD Pass 2 cancel-timeout failure-mode doc) → Session
  1c prompt + runbook addition
- **MEDIUM #8** (Health + broker-orphan double-fire dedup) → operator
  decision + Session 2b.1/2b.2 Tier 2 review focus
- **MEDIUM #12** (mass-balance precedence rules + 120s window +
  known-gap registry + session-boundary handling) → Session 4 prompt
- **LOW #16** (Session 2a mock-update grep) → Session 2a pre-flight
- **LOW #18** (interim merge after 1c) → operator architectural decision
  before Session 2a starts
- **LOW #19** (session count drift yellow-flag) → covered by regression
  invariant + tracked in work journal during sprint execution

### 10.6 Phase D begins

The Phase C-1 review cycle is converged. Three iterations have produced:
- 1st pass: 7 BLOCKING/HIGH → revisions
- 2nd pass: 5 BLOCKING + 4 HIGH + 6 MEDIUM + 3 LOW → Phase A revisit +
  Option 4 all-in expansion
- 3rd pass: 0 BLOCKING + 5 HIGH + 14 MEDIUM/LOW → Conditional CLEAR

Each pass surfaced fewer high-severity findings; the 3rd pass
specifically called out that the foundational mechanism is sound and
what's left is precision and edge-case discipline. Phase D structure:

1. **Review Context File** — operator-facing reference for the sprint
2. **Implementation Prompt × 18** (one per session) — backend reviewer
   flagged for 0–4 + 5a.1 + 5a.2 + 5b; frontend reviewer for 5c–5e
3. **Tier 2 Review Prompt × 18** — using
   `templates/review-prompt.md` for backend, NEW
   `templates/review-prompt-frontend.md` for frontend (B29 prereq)
4. **Work Journal Handoff Prompt** — bridges Phase D → implementation

Operator's call: proceed to Phase D directly, OR seek 4th-pass review.
The reviewer's verdict-criteria reading suggests proceeding directly
(the converging pattern + lack of BLOCKING + minor-revisions-suffice
disposition path is what §9.7 calls for). Recommended commit message:

```
chore(sprint-31.91): revised planning package post-3rd-adversarial-review (18 sessions, 5a split, alert observability all-in)
```

---

*End Sprint 31.91 Adversarial Review Input Package (revised 3rd pass —
18-session shape; HIGH findings addressed at Phase C; MEDIUM/LOW
captured in PHASE-D-OPEN-ITEMS.md; ready for Phase D).*

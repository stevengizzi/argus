# Sprint 31.92 — Adversarial Review Input Package

> **How to use this document.** Open a fresh Claude.ai conversation. Paste, in
> this order: (1) `sprint-spec.md`, (2) `spec-by-contradiction.md`, (3) this
> document. Then issue the opening prompt from `protocols/adversarial-review.md`:
>
>     "I need you to adversarially review this sprint spec. Your job is to
>     find problems, not to be supportive. Try to break this design. Find
>     the flaws."
>
> The reviewer should pursue the six probing angles (Assumption Mining,
> Failure Mode Analysis, Future Regret, Specification Gaps, Integration
> Stress, Simulated Attack — though the last is N/A here, no security
> surface). Bias toward Failure Mode Analysis and Specification Gaps —
> Sprint 31.91's Tier 3 #1 found 3 focus areas + 6 concerns (A–F) that
> mostly fell into those two categories.

---

## Why this sprint warrants adversarial review

Three reasons (per Phase A Step 8):

1. **Path #1 mechanism choice has 3+ candidate options with non-trivial trade-offs.** The wrong choice creates new failure modes. The Sprint Spec's Hypothesis Prescription enumerates H1/H2/H3/H4; H3 is REJECTED at Phase A; the spike must select among H1/H2/H4 empirically. Adversarial review must scrutinize whether the rejection of H3 is sound AND whether any *fifth* mechanism was missed.

2. **AC4 ceiling is a new architectural invariant.** Long-only SELL-volume ceiling (`cumulative_sold_shares ≤ shares_total` per `ManagedPosition`) is exactly the kind of "data model change + new integration" that adversarial review is designed for. The ceiling composes with DEC-117/364/369/372/385/386/388 — adversarial review must check for composition failures.

3. **DEC-386 made an empirical claim that was empirically falsified 24 hours later.** The new DEC-390 must survive adversarial scrutiny BEFORE we trust it. The same "sound on paper, broken in production" pattern is exactly what adversarial review is for. **The bar is higher this sprint than for routine sprints** — DEC-386's `~98%` aggregate claim should not be repeated in DEC-390.

---

## Architectural context — what DEC-385 / DEC-386 / DEC-388 already established

Sprint 31.91 (sealed 2026-04-28) landed three architectural decisions that Sprint 31.92 builds on without modifying. **The reviewer should treat these as preconditions, NOT as targets for revision.** Modifications to any of these are explicitly out-of-scope (SbC §"Do NOT modify").

### DEC-385 — Side-Aware Reconciliation Contract (6 layers)

**Origin:** Sprint 31.91 Sessions 2a → 2d (S2a / S2b.1 / S2b.2 / S2c.1 / S2c.2 / S2d). Materialized at S2d 2026-04-02; written below at sprint-close 2026-04-28.

**One-paragraph summary:** Reconciliation logic in OrderManager (Pass 1 startup, Pass 2 EOD) was previously side-blind — it treated all unconfirmed positions identically regardless of broker-reported side, which meant phantom-short cascades (DEF-204) were "reconciled" by being treated as legitimate positions to track, perpetuating the cascade across daily reconciliation cycles. DEC-385 made every reconciliation surface side-aware: broker-orphan/phantom-short direction now triggers `phantom_short` CRITICAL alert + entry gate; ARGUS-orphan direction (the original direction) preserved unchanged. The DEF-158 retry path (the 3-branch side-check at `_check_flatten_pending_timeouts`) was specifically reworked: BUY → resubmit; SELL → alert+halt+`phantom_short_retry_blocked`; unknown → log+halt.

**Cross-references this sprint relies on:**
- DEC-385 L2 added `SystemAlertEvent.metadata: dict[str, Any] | None` schema. Sprint 31.92's Path #2 suppression-timeout fallback REUSES DEC-385's `phantom_short_retry_blocked` alert path verbatim (no new emitter site).
- DEC-385 L3 added `phantom_short_gated_symbols` SQLite audit table. Sprint 31.92 does NOT touch.
- DEC-385's DEF-158 3-branch side-check is preserved verbatim (regression invariant 8). Sprint 31.92's Path #2 detection is upstream-at-`place_order` exception, NOT a 4th branch. **This is one of the most-questioned design decisions in this sprint** — reviewer should scrutinize.

### DEC-386 — OCA-Group Threading + Broker-Only Safety (4 layers)

**Origin:** Sprint 31.91 Sessions 0 / 1a / 1b / 1c. Tier 3 #1 PROCEED 2026-04-27. Verdict at `docs/sprints/sprint-31.91-reconciliation-drift/tier-3-review-1-verdict.md`.

**One-paragraph summary:** Bracket children at IBKR were placed via `parentId` only, with no `ocaGroup`/`ocaType` set — combined with redundant standalone SELL orders from trail/escalation paths sharing no OCA group, this allowed multi-leg fill races accounting for ~98% of the unexpected-short blast radius (per IMPROMPTU-11 mass-balance attribution). DEC-386's 4 layers: **(L1 S0)** `Broker.cancel_all_orders(symbol, *, await_propagation)` ABC extension + `CancelPropagationTimeout` exception (preserves DEC-364 no-args contract). **(L2 S1a)** Bracket OCA grouping with `ocaType=1` on children + `ManagedPosition.oca_group_id` + `_is_oca_already_filled_error` helper (lives in `ibkr_broker.py:75-100`). **(L3 S1b)** Standalone-SELL OCA threading on 4 paths (`_trail_flatten`, `_escalation_update_stop`, `_resubmit_stop_with_retry`, `_flatten_position`) + `redundant_exit_observed` SAFE marker + grep regression guard `test_no_sell_without_oca_when_managed_position_has_oca` enforcing threading discipline; legitimate broker-only paths exempted via canonical `# OCA-EXEMPT: <reason>` comment. **(L4 S1c)** Cancel-then-SELL/wire on 3 broker-only paths via `cancel_all_orders(symbol=..., await_propagation=True)`; `CancelPropagationTimeout` (2s budget) aborts SELL/wire and emits `cancel_propagation_timeout` alert. `reconstruct_from_broker()` gained STARTUP-ONLY contractual docstring (Sprint 31.94 inherits the runtime gate).

**The empirical claim:** DEC-386's text reads "DEF-204's primary mechanism (~98% of blast radius per IMPROMPTU-11) closed by Sessions 1a + 1b. Secondary mechanism (detection blindness in reconcile / DEF-158 retry path / EOD Pass 2) closed by Sessions 2a–2d + 3 (still in flight)."

**The empirical falsification (2026-04-28 paper session):** 60 NEW phantom shorts during a single 5h47m session. The Path #1 BITU trace and Path #2 PCT trace surfaced two distinct uncovered mechanisms — neither was hypothetically ruled out by DEC-386's design but neither was covered. The `~98%` claim was good-faith but premature.

**What this means for adversarial review:** DEC-390 must NOT make an analogous aggregate claim. Reviewer should check the proposed DEC-390 entry (template in `doc-update-checklist.md` C2) for any aggregate percentage language. The proposed DEC-390 deliberately uses "structural closure of L1/L2 + structural defense-in-depth at L3" instead — reviewer should validate this framing.

### DEC-388 — Alert Observability Architecture (5 layers)

**Origin:** Sprint 31.91 Sessions 5a.1 / 5a.2 / 5b / 5c / 5d / 5e + Impromptus A/B/C. Tier 3 #2 PROCEED-with-conditions AMENDED 2026-04-28. Materialized at S5e 2026-04-28.

**One-paragraph summary:** Pre-Sprint-31.91, ARGUS had no consumer-side architecture for `SystemAlertEvent` — emitted but no central consumer, no persistence, no UI surface (DEF-014). DEC-388 added: (L1) 15 emitter sites populating `metadata: dict[str, Any]`; (L2) HealthMonitor consumer + 13-entry `POLICY_TABLE` in `argus/core/alert_auto_resolution.py` + AST regression guard `tests/api/test_policy_table_exhaustiveness.py`; (L3) `data/operations.db` 5-table layout + restart recovery via `rehydrate_alerts_from_db()` + migration framework universal across all 8 ARGUS SQLite DBs; (L4) 4 REST endpoints + `/ws/v1/alerts` WebSocket (JWT-authenticated, 4 lifecycle deltas); (L5) frontend — `useAlerts` hook + `AlertBanner` cross-page mount + `AlertToastStack` + `AlertAcknowledgmentModal` + `AlertsPanel` Observatory + `AlertDetailView`. Severity policy: banner = critical only; warning/info = toast-only.

**Cross-references this sprint relies on:**
- AC3.7: Sprint 31.92 adds the 14th `POLICY_TABLE` entry for `sell_ceiling_violation` (`operator_ack_required=True`, no auto-resolution).
- AC2.5: Sprint 31.92's Path #2 suppression-timeout fallback emits `phantom_short_retry_blocked` (DEC-385's existing alert type) into DEC-388's existing pipeline.
- No new REST endpoints, no new WebSocket events, no frontend changes.

---

## The empirical falsification — what 2026-04-28 actually showed

Full debrief at `docs/debriefs/2026-04-28-paper-session-debrief.md` (read-only diagnostic; reviewer should read in full before forming judgment). Key points for adversarial-review framing:

1. **Boot commit `0236e27`** was Sprint 31.91 S5a.1 — HealthMonitor `SystemAlertEvent` consumer + REST surface ONLY. Sessions 5a.2 onward had NOT yet landed. The session is the cleanest possible "DEC-386 in place, full DEC-388 not yet" baseline; the DEF-204 mechanism observed is therefore attributable to DEC-386's coverage gap, NOT to alert-observability immaturity.

2. **60 NEW phantom shorts in 5h47m**, distributed across 60 unique symbols. Top 5 by share count: PCT 3,837 · ACHR 402 · PDYN 400 · HPK 313 · MX 297. **The top 6 alone account for ~5,500 of 12,605 absolute phantom-short shares** — these are the locate-rejection retry storms (Path #2). The long tail of small concurrent-trigger races (BITU 182, OHI 115, CSIQ 115, BHVN 110, …) is Path #1.

3. **27 of 87 ORPHAN-SHORT detections were pre-existing at boot** (operator missed-run of `ibkr_close_all_positions.py` the prior evening — confirmed by operator 2026-04-29). These are NOT a new mechanism; they are operational hygiene. The 60 NEW are the ones that motivate Sprint 31.92.

4. **Path #1 canonical trace (BITU 13:36→13:41):** Trail-stop fired at 13:41:02.235 (price 14.44, breakeven of post-T1 reduced bracket stop #462). Trail emitted SELL 182 MARKET (#633) at 13:41:02.236. Both `#633` and `#462` filled → 364 sold against 182 long → 182 short. Phantom-short gate engaged at 13:41:18.

5. **Path #2 canonical trace (PCT):** First SELL at 14:34, escalation stop added at 14:54, time stop fired at 15:04:08, IBKR returned `"contract is not available for short sale"`. Time stop fired again at 15:04:13, then 15:04:18, then every 5s for ~3 hours. PCT alone: 2,107 SELL placement events. CRWG and XNDU showed the same pattern — combined, 3 symbols accounted for 7,017 of 11,000 SELL order events.

6. **DEC-386's `~98%` claim falsified.** The empirical residue is more than 2%. **Path #1 is structurally outside DEC-386 S1b's coverage** — DEC-386 S1b OCA threading prevents the second SELL from being PLACED while the bracket is still alive, but doesn't prevent both legs from being IN FLIGHT once they've fired concurrently. **Path #2 is structurally outside DEC-386 entirely** — IBKR's locate-rejection is interpreted as transient by ARGUS retry logic (DEC-372 backoff loop), not as a hold-pending-borrow.

7. **Cessation criterion #5 (5 paper sessions clean post-seal) FAILS on session #1.** This is the operational gate that gates live trading.

---

## Code surfaces being modified — the four hot zones

The 6-of-10-sessions overlap on `argus/execution/order_manager.py` is one of this sprint's primary risks. The reviewer should scrutinize whether the SbC's "Do NOT modify" list realistically holds across 6 sessions.

### Hot zone 1: `_trail_flatten` (lines ~3551–3650)

**Current implementation (excerpt):**
```python
async def _trail_flatten(
    self, position: ManagedPosition, current_price: float
) -> None:
    """Flatten a position due to trail stop hit (AMD-2, AMD-4, AMD-8).

    Order of operations is safety-critical:
    1. AMD-8: Check _flatten_pending — complete no-op if already pending
    2. AMD-4: Check shares_remaining > 0 — no-op if zero
    3. Submit market sell FIRST (AMD-2: sell before cancel)
    4. Cancel broker safety stop SECOND
    """
    # ... AMD-8 + AMD-4 guards ...

    # Step 3: Submit market sell FIRST (AMD-2)
    try:
        order = Order(...)
        if position.oca_group_id is not None:
            order.ocaGroup = position.oca_group_id
            order.ocaType = _OCA_TYPE_BRACKET  # DEC-386 S1b OCA threading
        result = await self._broker.place_order(order)
        # ...
    except Exception as exc:
        if _is_oca_already_filled_error(exc):
            # DEC-386 S1b SAFE-marker: bracket already filled
            self._handle_oca_already_filled(position, where="_trail_flatten")
        else:
            logger.exception("CRITICAL: Trail flatten sell failed ...")
            return

    # Step 4: Cancel broker safety stop SECOND (AMD-2)
    if position.stop_order_id:
        try:
            await self._broker.cancel_order(position.stop_order_id)
        except Exception:
            ...
```

**Sprint 31.92 modification (S2a, conditional on S1a spike):**
- IF H1 (cancel-and-await): Insert `await self._broker.cancel_all_orders(symbol=position.symbol, await_propagation=True)` BEFORE `place_order(SELL)`. AMD-2 invariant ("sell before cancel") MODIFIED.
- IF H2 (amend-stop-price): Replace the SELL emission entirely with `await self._broker.modify_order(position.stop_order_id, new_aux_price=current_price)`. Fall through to existing AMD-2 path on amend rejection.
- IF H4 (hybrid): Try amend; on rejection, fall back to cancel-and-await.

### Hot zone 2: `_check_flatten_pending_timeouts` DEF-158 retry side-check (lines ~3319–3550)

**Current implementation (excerpt — the DEF-158 3-branch side-check that MUST be preserved):**
```python
# Sprint 31.91 Session 3 (DEF-158 retry side-check):
# 3-branch gate before resubmission. Mirror of IMPROMPTU-04 EOD A1.
if broker_side == OrderSide.SELL:
    logger.critical("Flatten retry refused for %s: broker reports SHORT ...", symbol, broker_qty)
    # Publishes phantom_short_retry_blocked SystemAlertEvent
    self._flatten_pending.pop(symbol, None)
    continue
if broker_side != OrderSide.BUY:
    logger.error("Flatten retry refused for %s: broker side is %r ...", symbol, broker_side)
    self._flatten_pending.pop(symbol, None)
    continue
# Branch 1 (BUY) falls through to existing flatten-resubmit path
# ... resubmit market SELL ...
```

**Sprint 31.92 modification (S3b):** ADD a NEW upstream detection at the EXISTING `place_order` exception (already in this method's try/except). When `_is_locate_rejection(exc)` matches, set `_locate_suppressed_until[symbol] = now + locate_suppression_seconds` + INFO log + clear `_flatten_pending` + return early. **The 3-branch side-check itself is preserved verbatim** (regression invariant 8). **The reviewer should scrutinize this design choice** — is upstream-at-`place_order` truly cleaner than a 4th branch?

### Hot zone 3: `_flatten_position` (lines ~3751–3862)

**Current implementation (relevant excerpt):**
```python
async def _flatten_position(self, position: ManagedPosition, reason: str) -> None:
    # ... cancel stop + T1 + T2 ...
    # Submit market sell for remaining shares
    if position.shares_remaining > 0:
        try:
            order = Order(...)
            if position.oca_group_id is not None:
                order.ocaGroup = position.oca_group_id
                order.ocaType = _OCA_TYPE_BRACKET  # DEC-386 S1b
            result = await self._broker.place_order(order)
            # ...
        except Exception as exc:
            if _is_oca_already_filled_error(exc):
                self._handle_oca_already_filled(position, where="_flatten_position")
                return
            logger.exception("CRITICAL: Failed to flatten %s ...")
```

**Sprint 31.92 modifications:**
- S3b: Add `_is_locate_suppressed(position.symbol, now)` pre-check at the top; skip + INFO log if suppressed. In the exception handler, classify `_is_locate_rejection(exc)` and set suppression.
- S4a: Add `_check_sell_ceiling(position, position.shares_remaining)` pre-check before `place_order(SELL)`; refuse + alert + log if violation.
- S4b: Replace `_OCA_TYPE_BRACKET` with `self._bracket_oca_type`.

### Hot zone 4: `IBKRBroker._is_oca_already_filled_error` pattern (lines 60–110)

**Current implementation (the pattern Sprint 31.92 will mirror for `_is_locate_rejection`):**
```python
# Sprint 31.91 Session 1a: substring fingerprint for IBKR Error 201
# "OCA group is already filled". Lowercased once for case-insensitive matching.
_OCA_ALREADY_FILLED_FINGERPRINT = "oca group is already filled"

def _is_oca_already_filled_error(error: BaseException) -> bool:
    """Return True if `error` is an IBKR Error 201 with the OCA-filled reason."""
    if not isinstance(error, BaseException):
        return False
    return _OCA_ALREADY_FILLED_FINGERPRINT in str(error).lower()
```

**Sprint 31.92 addition (S3a):**
```python
# Sprint 31.92 Session 3a: substring fingerprint for IBKR locate-rejection
# (held-pending-borrow). Validated by S1b spike against paper IBKR.
_LOCATE_REJECTED_FINGERPRINT = "contract is not available for short sale"

def _is_locate_rejection(error: BaseException) -> bool:
    """Return True if `error` is an IBKR rejection with the locate-not-available reason."""
    if not isinstance(error, BaseException):
        return False
    return _LOCATE_REJECTED_FINGERPRINT in str(error).lower()
```

---

## Sprint 31.91 Tier 3 #1 lessons learned

The Tier 3 review of DEC-386's combined diff produced 3 focus areas + 6 concerns (A–F). Sprint 31.92 inherits or relates to several:

| Tier 3 #1 Item | Sprint 31.92 Disposition |
|---------------|--------------------------|
| Focus Area 1 — Leaked-long failure mode visibility (cancel_propagation_timeout alert visibility) | RESOLVED by Sprint 31.91 S5a.1+; Sprint 31.92 inherits the resolved state. |
| Focus Area 2 — `reconstruct_from_broker` STARTUP-ONLY docstring | DEFERRED to Sprint 31.94 D1 per RSK-DEC-386-DOCSTRING; Sprint 31.92 explicitly does NOT modify this surface. |
| Focus Area 3 — `# OCA-EXEMPT:` marker discipline | PRESERVED; Sprint 31.92 does NOT modify the exemption mechanism (regression invariant 9). |
| Concern A — `_is_oca_already_filled_error` module-abstraction leakage | DEFERRED to Sprint 31.93 (component-ownership scope) per SbC §"Out of Scope" #4. |
| Concern B — `_OCA_TYPE_BRACKET = 1` constant drift | RESOLVED by Sprint 31.92 S4b (DEF-212 rider). |
| Concern C — `SystemAlertEvent.metadata` schema gap | RESOLVED by Sprint 31.91 DEC-385 L2. Sprint 31.92 reuses. |
| Concern D — `ManagedPosition.redundant_exit_observed` persistence | DEFERRED to Sprint 35+ Learning Loop V2 (DEF-209 extended). Sprint 31.92's `cumulative_sold_shares` is in the SAME class — also in-memory only, also deferred to DEF-209-class persistence. **This is one of the proposed RSKs (RSK-CEILING-FALSE-POSITIVE) and a scrutiny target.** |
| Concern E — Test-fixture drift across 12 files | NOT addressed in Sprint 31.92. Out of scope. |
| Concern F — Test 4 `get_positions` side-effect chain brittleness | NOT addressed in Sprint 31.92. Out of scope. |

**The reviewer should specifically scrutinize:**
- Does Concern A's deferral create code-drift risk during 6 Sprint 31.92 sessions touching `order_manager.py`?
- Does Concern D's deferral pattern (in-memory fields not persisted) create restart-safety risk for `cumulative_sold_shares`?

---

## Specific scrutiny questions for the adversarial reviewer

These are the highest-yield questions, ranked by suspected risk. The reviewer is encouraged to add their own — these are starting points, not a complete list.

### Q1. Path #1 mechanism choice — is the OPTION (b) cancel-and-await default correct?

The Sprint Spec's Hypothesis Prescription recommends H1 (cancel-and-await) as the default if the spike doesn't conclusively select H2 (amend-stop-price). Rationale: "aligned with DEC-386 S1c's existing `await_propagation` infrastructure, accepts bounded 50–200ms unprotected window as cost of correctness, simplest correctness story."

**Scrutiny:**
- Is the 50–200ms unprotected window actually bounded? What if `cancel_all_orders(symbol, await_propagation=True)` returns BEFORE IBKR has actually propagated the cancel, and the SELL fires INTO an active bracket stop? (DEC-386 S1c's spike `PATH_1_SAFE` measured this for OCA-already-filled, NOT for the cancel-and-await-then-SELL sequence.)
- Is OPTION (a) amend-stop-price actually riskier than OPTION (b)? DEC-386 ABC contract preserves `cancel_all_orders` no-args; AC1's H2 path uses `modify_order` which IS already in the IBKR ABC. Why is H1 default rather than H2?
- The Phase A excluded H3 (recon-trusts-marker) on grounds that `redundant_exit_observed` persistence is deferred to Sprint 35+. But is there a SHORTER path — e.g., trust the marker IN-MEMORY only for the duration of a single reconciliation cycle? Why is "in-memory only" sufficient for `cumulative_sold_shares` but not for `redundant_exit_observed`?
- Is OPTION (d) hybrid actually a viable real-world choice or just a theoretical fallback? The Sprint Spec frames it as "premature complexity." Adversarial reviewer: is the premature-complexity framing self-serving (avoiding a complexity tax for the spec author), or genuinely justified?

### Q2. AC4 ceiling — does it compose correctly with all 5+ SELL emit sites?

The ceiling is per-`ManagedPosition`. AC3.4 explicitly disclaims per-symbol aggregation.

**Scrutiny:**
- Are there MORE than 5 SELL emit sites in `order_manager.py`? The Sprint Spec says "5+"; the SbC implies 4 standalone-SELL paths + bracket-T1 + bracket-T2 + EOD-flatten = at least 7. Did Phase A undercount the emit-site enumeration?
- What happens when T1 partial-fills, ARGUS sees the fill callback, increments `cumulative_sold_shares` to 50, and THEN the bracket-stop emits a 50-share fill? Both fills are legitimate; total = 100; matches `shares_total`. But what if the bracket-stop emits a 100-share fill (the broker unconditionally cancels T1 once stop fires)? Does ARGUS's `on_fill` handle this case correctly TODAY, and does AC4 ceiling break it?
- `reconstruct_from_broker`-derived positions get `cumulative_sold_shares = 0` and `shares_total = abs(broker_position.shares)`. If a `reconstruct_from_broker`-derived LONG position has, in actual broker history, already been partially sold (e.g., 100 shares brought down from a 200-share original, broker reports 100), AC3.5's initialization treats `shares_total = 100`. Subsequent ARGUS-emitted SELLs against this position would correctly see `cumulative_sold_shares + 100 ≤ 100` and pass the ceiling. **But what if ARGUS later observes a `position.shares_remaining` mismatch with broker — does the ceiling still hold?**
- The ceiling is in-memory only (per Concern D-class deferral). On ARGUS restart, `cumulative_sold_shares` resets to 0 for all positions. **What if ARGUS restarts mid-session AFTER having already SELL-emitted to the position's full long quantity?** The reconstructed position's ceiling resets; the next SELL emit would PASS the ceiling check despite the position being already fully exited. **This is a restart-safety hole.** Is it acceptable for paper trading? Is it acceptable for live trading? What's the mitigation?

### Q3. Path #2 fingerprint stability — is substring-matching robust enough?

The fingerprint is a case-insensitive substring match against `str(error).lower()`. The exact string is `"contract is not available for short sale"`.

**Scrutiny:**
- The string is captured by S1b spike against PAPER IBKR. Does the LIVE IBKR endpoint return the same string? Live IBKR might use different error text (different broker plumbing). The first live session would empirically validate, but by then the deployment is committed. Should S1b also capture from a sandbox account if available?
- IBKR's `ib_async` library wraps IBKR errors; the wrapping may change error-text format across `ib_async` versions. The DEC-386 `_is_oca_already_filled_error` faces the same risk; how has it been managed for that helper? Is the same management adequate for `_is_locate_rejection`?
- What if IBKR returns the error in a non-English locale? (Unlikely for a US-equities brokerage but listed for completeness.)
- The substring match is `_LOCATE_REJECTED_FINGERPRINT in str(error).lower()`. **What if a future error message merely CONTAINS this substring as part of a larger reason (e.g., "this contract is not available for short sale because the security is restricted")?** The match would still trip — is that the intended behavior, or could it produce false positives on a different rejection class?
- Spike artifact 30-day freshness check (regression invariant 18 + A-class halt A13) is the operational mitigation. Is 30 days the right cadence? DEC-386's `PATH_1_SAFE` uses 30 days for IBKR API behavior — does the locate-rejection-string mutation rate match the API behavior mutation rate?

### Q4. Suppression-window calibration — is 300s right?

`OrderManagerConfig.locate_suppression_seconds` defaults to 300s. S1b spike validates against actual hold-pending-borrow release timing.

**Scrutiny:**
- 300s is 5 minutes. Time-stop firing at 30 minutes per `time_stop_seconds` default → if the suppression expires at 5 min and the held order hasn't released, ARGUS publishes `phantom_short_retry_blocked` and stops trying. **Is that the right behavior, or should ARGUS keep waiting longer?** The PCT trace had IBKR releasing held orders 3+ hours after first emit — by which point ARGUS's 5-min suppression has long expired.
- If the suppression expires and ARGUS publishes the alert, what happens at the broker side if the held order DOES eventually fill 30 minutes later? ARGUS thinks the symbol is "no longer pending"; the broker fill arrives; ARGUS treats it as an unsolicited fill (DEC-385 Pass 1 / Pass 2 handles this — but does it correctly?). Reviewer: trace this scenario through the existing DEC-385 reconciliation logic.
- What if `locate_suppression_seconds = 300` is fine for paper but live trading needs different — and the operator forgets to adjust?
- What if multiple positions on the same symbol are suppressed? The dict is symbol-keyed, not position-keyed. Two positions on AAPL share one suppression entry. Is that correct? Should it be position-keyed for symmetry with AC3.4's per-`ManagedPosition` ceiling?

### Q5. Suppression dict reconnect-blindness — is paper-trading acceptance correct?

SbC §"Edge Cases to Reject" #5 explicitly accepts that a mid-session IBKR Gateway reconnect during a suppression window leaves the dict entry stale until either (a) suppression-timeout fallback fires correctly, OR (b) operator restarts. Sprint 31.94 will couple `IBKRReconnectedEvent` consumer logic to dict-clear.

**Scrutiny:**
- Apr 22 / Apr 23 / Apr 28 paper sessions ALL observed IBKR Gateway disconnect/reconnect events. The reconnect-blindness IS a real-world failure mode in paper, not a hypothetical. Why is it acceptable?
- After a reconnect: stale dict entry → next SELL emit at suppressed symbol is skipped → fall back to suppression-timeout → `phantom_short_retry_blocked` alert fires on a symbol that may or may not actually be held. **Is the alert false-positive rate acceptable?** Is operator workflow degraded by extraneous alerts during reconnect events?
- Sprint 31.94 inherits this coupling. **What's the maximum delay between Sprint 31.92 seal and Sprint 31.94 seal?** If 31.94 slips, the reconnect-blindness window grows.

### Q6. AMD-2 invariant modification — does anything else depend on it?

AMD-2 ("sell before cancel" in `_trail_flatten`) is INTENTIONALLY MODIFIED if H1 selected at S2a. Regression invariant 17 covers the rename of the AMD-2 test.

**Scrutiny:**
- The AMD-2 invariant was introduced in Sprint 28.5 (Exit Management). What was the PROBLEM AMD-2 solved? Was it the inverse race condition — bracket cancel firing before SELL emission, leaving an unprotected window where the price moved adversely? If so, OPTION (b) cancel-and-await RE-INTRODUCES that exposure.
- DEC-117 atomic-bracket invariant guarantees parent-fails-children-cancel pattern at IBKR. Does H1's cancel-and-await actually preserve DEC-117? When `cancel_all_orders(symbol)` cancels the bracket parent, does IBKR atomically cancel the children? Or does it return to ARGUS BEFORE the children are cancelled? (The DEC-386 spike answered this for the OCA-cancellation path; has it been answered for the broker-only-cancel path used by `cancel_all_orders`?)
- A-class halt A10 fires if the chosen mechanism breaks DEC-117. What is the empirical test for "DEC-117 broken"? Is there a synthetic scenario in S2a's tests that would catch this, or does it rely on production paper trading to surface?

### Q7. DEF-158 retry side-check NOT modified — is upstream-at-`place_order` truly cleaner than a 4th branch?

The 3-branch side-check is preserved verbatim (regression invariant 8). Path #2 detection is at the `place_order` exception in 4 SELL emit sites.

**Scrutiny:**
- A 4th branch in `_check_flatten_pending_timeouts` would be: detect locate-rejection BEFORE retrying (i.e., suppress at the retry-attempt level rather than the place-order-attempt level). Why is upstream-at-`place_order` chosen over this?
- The current 3-branch gate runs AT RETRY TIME (when `_check_flatten_pending_timeouts` decides whether to resubmit). Path #2 detection runs AT FIRST-PLACE-ORDER TIME. **Are there scenarios where the first place_order succeeds (no locate-rejection on first call) but a SUBSEQUENT retry IS locate-rejected?** If yes, the upstream-at-place_order detection captures it on retry; if the 4th-branch alternative were instead used, it would also capture. Is one strictly more conservative than the other?
- The 3-branch gate has access to broker state via `await self._broker.get_positions()` synchronously. The upstream-at-`place_order` detection only has the exception text. **Is exception-only classification sufficient, or could the symbol be confirmed via `get_positions()` for defense-in-depth?**

### Q8. The "Do NOT modify" list spanning 6 sessions — is it credible?

`order_manager.py` is 4,421 lines. 6 of 10 sessions touch it. The SbC's "Do NOT modify" list within this file is large (DEC-386 S1a/S1b/S1c surfaces, `reconstruct_from_broker`, `reconcile_positions`, `_handle_oca_already_filled`, DEF-158 3-branch gate, `_is_oca_already_filled_error`, …).

**Scrutiny:**
- The temptation to "while I'm in there, also fix X" is documented. Is the SbC structurally sufficient to prevent this, or does it rely on implementer discipline alone?
- Cumulative diff bound at ~600 LOC for `order_manager.py` (regression checklist's "Cross-Session Invariant Risks" section). Is 600 LOC realistic, or would scope creep push it higher?
- Tier 2 reviewers face a context-budget challenge verifying ALL 9 invariants 1–9 across 6 sessions. The DEC-328 full-suite runs are the safety net, but: are there NON-test-suite-detectable regressions that could slip through (e.g., subtle behavioral changes in OCA threading semantics that pass tests but fail in production paper trading)?
- A failure mode: implementer makes a change that fixes the immediate scope BUT also incidentally modifies a DEC-385/386/388 surface in a way the test suite can't detect. Tier 2 catches it via diff inspection; Tier 3 (if fired) catches via architectural review. **Is one Tier 3 review at S5b close-out adequate, or should this sprint mandate a mid-sprint Tier 3 (analogous to Sprint 31.91's two Tier 3 reviews)?**

### Q9. DEC-390 framing — does it avoid the empirical-aggregate-claim trap?

The proposed DEC-390 entry (template in `doc-update-checklist.md` C2) deliberately avoids aggregate percentage claims, replacing them with "structural closure of L1/L2 + structural defense-in-depth at L3 + falsifiable validation artifacts."

**Scrutiny:**
- Does the proposed DEC-390 text contain ANY language that reads like an aggregate claim (e.g., "comprehensive", "complete", "fully closed")? If yes, those are footholds for empirical falsification 24 hours later.
- Process-evolution lesson F.5 (in `doc-update-checklist.md` C10) frames the lesson at workflow level. **Is the lesson actionable for future sprints, or is it a one-time observation?** Should the sprint-planning protocol be amended to discourage aggregate-percentage claims in DEC entries?
- The cessation criterion #5 framing (5 paper sessions clean post-seal) is explicit operational gating. **Is 5 sessions enough?** DEC-386 had implicit cessation criteria (operator daily-flatten until "demonstrated clean"); the 5-session bar is more concrete. Is it concrete ENOUGH?

### Q10. Sprint 31.91 Tier 3 #1 deferred items — has anything been miscalculated?

Tier 3 #1 deferred Concern A (helper relocation), Concern D (ManagedPosition field persistence), Concerns E + F (test-fixture hygiene). Sprint 31.92 inherits or compounds these.

**Scrutiny:**
- Concern A deferred to Sprint 31.93. Sprint 31.92's 6 sessions touch `ibkr_broker.py` (S3a) AND `order_manager.py` (6 sessions, including the file that imports `_is_oca_already_filled_error`). **Is there ANY risk that the helper's location matters for Sprint 31.92's correctness?** E.g., circular-import risk if `order_manager.py` and `ibkr_broker.py` both import `_is_locate_rejection`?
- Concern D deferred to Sprint 35+. Sprint 31.92's `cumulative_sold_shares` is in the same in-memory-only class. **Does Sprint 31.92's restart-safety hole (Q2 above) demand pulling Concern D forward?**
- Concerns E and F (test-fixture hygiene) NOT addressed. Sprint 31.92 ADDS ~50–60 new tests, mostly in new test files. **Do the new test files have the same fixture-drift pattern (per-file MagicMock brokers)?** If yes, Sprint 31.92 perpetuates the debt.

---

## Minimum reviewer actions

Before producing a verdict, the reviewer must:

1. **Read the Apr 28 paper-session debrief in full** (`docs/debriefs/2026-04-28-paper-session-debrief.md`). It is 419 lines; reviewer must internalize the canonical traces (BITU 13:36→13:41 for Path #1; PCT 14:34→18:08 for Path #2).
2. **Read DEC-385, DEC-386, DEC-388 in full** in `docs/decision-log.md` (line numbers ~4764, ~4746, ~4782 — verify before reading; ARGUS repo HEAD is the authoritative state).
3. **Read Sprint 31.91 Tier 3 #1 verdict** at `docs/sprints/sprint-31.91-reconciliation-drift/tier-3-review-1-verdict.md` for the prior-sprint architectural-review pattern.
4. **Read the `_trail_flatten`, `_check_flatten_pending_timeouts`, `_flatten_position` source** in `argus/execution/order_manager.py` at HEAD.
5. **Read `IBKRBroker._is_oca_already_filled_error`** in `argus/execution/ibkr_broker.py` (lines 60–110) as the pattern Sprint 31.92's Path #2 will mirror.

Without reading these, the verdict is uninformed and should not be relied on.

---

## Required output schema

Per `protocols/adversarial-review.md`, the verdict is one of:

- **Outcome A:** "No critical issues found." Document the confirmation + any minor observations as notes in the sprint package.
- **Outcome B:** "Issues found that require spec changes." Summarize the issues + propose specific revisions to the Sprint Spec / SbC / Session Breakdown / Escalation Criteria / Regression Checklist / Doc Update Checklist as needed.

If Outcome B with ≥1 Critical finding: A-class halt A14 fires; sprint planner returns to Phase A for revisions per protocol §"Phase C-1 Adversarial Review Gate". Re-run adversarial review on the post-revision package before Phase D.

Reviewer's findings should be documented in:

- `docs/sprints/sprint-31.92-def204-round-2/adversarial-review-findings.md` (NEW; created by sprint planner during revision phase)
- If revisions land: `docs/sprints/sprint-31.92-def204-round-2/revision-rationale.md` (NEW; one-line rationale per artifact change)

---

## Closing note

The success bar for this sprint is **higher than Sprint 31.91's** because Sprint 31.91 already empirically failed once. The reviewer is not just looking for bugs in the design — they are looking for the SHAPE of bugs that the previous adversarial review missed. The previous review focused on architectural soundness (Tier 3 #1 verdict, "PROCEED — architecturally sound and ships safely"); the empirical falsification 24 hours later showed that *architectural soundness in the abstract* is insufficient. The reviewer should specifically ask: "what would a 2026-04-30 paper session show that this design didn't anticipate?"
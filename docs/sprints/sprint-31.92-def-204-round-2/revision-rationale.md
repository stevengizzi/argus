# Sprint 31.92 — Revision Rationale (Phase C-1 Round 1)

> **Phase C-1 step 3d artifact.** Logs each decision made in response to the adversarial review verdict (Outcome B — issues found that require spec changes). Records what was accepted, what was partially accepted with a different fix, and the reasoning. Companion artifact: `adversarial-review-findings.md` (the verdict itself, archived alongside this document).
>
> **Verdict received:** 2026-04-29 (between Phase C and Phase D). 3 Critical + 4 High + 3 Medium findings.
> **Verdict author:** Adversarial Round 1 reviewer (separate Claude.ai conversation, per `protocols/adversarial-review.md`).
> **Disposition author:** Sprint 31.92 planner.
> **Revisions applied:** All 10 findings dispositioned; 7 accepted in full, 3 accepted with different fix shape.
> **Round 2 required:** YES — substantive revisions warrant second adversarial pass before Phase D.

## Summary

| # | Severity | Disposition | Fix shape (one-line) |
|---|----------|-------------|----------------------|
| C-1 | Critical | ACCEPT | `cumulative_pending_sell_shares` reservation pattern; emit-time bookkeeping closes the asyncio yield-gap race. |
| C-2 | Critical | PARTIAL ACCEPT (different) | `is_reconstructed: bool` flag refuses ARGUS-emitted SELLs on reconstructed positions; defer DEF-209 persistence. |
| C-3 | Critical | ACCEPT | Reverse Hypothesis Prescription: H2 amend-stop-price as primary, H1 cancel-and-await as last-resort fallback. |
| H-1 | High | ACCEPT | AC3.2 enumerates 5 standalone-SELL emit sites for ceiling check; bracket placement explicitly excluded. |
| H-2 | High | ACCEPT | Suppression dict keyed by `ManagedPosition.id` (ULID), not symbol. |
| H-3 | High | PARTIAL ACCEPT (different) | Broker-side verification at suppression-timeout BEFORE alert publication; defer reconnect-event coupling to 31.94. |
| H-4 | High | PARTIAL ACCEPT (different) | Startup warning when `bracket_oca_type != 1` + live-ops doc; do NOT remove field's runtime-flippability. |
| M-1 | Medium | ACCEPT | S1b spike measures hard-to-borrow microcaps; suppression default derived from spike p99+20% (likely 4–6hr, not 5min). |
| M-2 | Medium | ACCEPT | AC5.1/AC5.2 reframed as in-process logic validation; cessation criterion #5 framed as production gate. |
| M-3 | Medium | PARTIAL ACCEPT (different) | Pytest test produces JSON artifact as side-effect; CI runs daily for freshness. Preserves session budget. |

## Per-finding rationale

### C-1 — `cumulative_sold_shares` reads stale data between emit and fill — ACCEPT

**Reviewer's argument:** Two coroutines on the same `ManagedPosition` can both pass `_check_sell_ceiling` between `t=emit` and `t=fill` because asyncio yields control during `await place_order(...)`. The ceiling reads stale state. SbC §"Edge Cases to Reject" #1 conflates fill-side serialization (which asyncio provides) with emit-side serialization (which it does not). The ceiling is provably ineffective against the exact race that motivates Path #1.

**Disposition:** ACCEPT in full. The reviewer's trace is correct and the gap is real. The `cumulative_sold_shares ≤ shares_total` invariant only holds against fill-time bookkeeping; it does NOT hold against emit-time bookkeeping unless we add a separate accounting variable.

**Fix shape:** Two-variable accounting — `cumulative_pending_sell_shares` (incremented at place-time, synchronously before the `await`) plus `cumulative_sold_shares` (incremented at fill-time). Ceiling check: `cumulative_pending_sell_shares + cumulative_sold_shares + requested_qty ≤ shares_total`. State transitions enumerated in revised AC3.1: place enqueue increments pending; cancel/reject decrements pending; partial fill transfers from pending to sold; full fill transfers remainder.

**Affected artifacts:** Sprint Spec (AC3.1, AC3.2, AC3.3, AC3.4 — extensive); SbC (§"Edge Cases to Reject" #1 replaced); Session Breakdown (S4a test count +3); Regression Checklist (invariant 13 rewritten).

**Trade-offs considered:** Per-position `asyncio.Lock` was the alternative. Rejected because it serializes all SELL emits on a position even when there's no contention; the reservation pattern is finer-grained and the standard idiom for resource-bookkeeping under concurrency.

### C-2 — Restart-safety hole degrades both Path #1 and ceiling — PARTIAL ACCEPT, different fix

**Reviewer's argument:** `reconstruct_from_broker`-derived positions get `cumulative_sold_shares = 0` (per AC3.5) and `oca_group_id = None` (DEC-386 reconstruct path). On restart-during-active-position, the ceiling forgets prior sells and Path #1's cancel-and-await catches only non-OCA orders, leaving pre-restart bracket children alive at IBKR. Both defenses degrade in the same way DEC-386 did. Reviewer proposed three options: (a) read trades table on startup, (b) persist `cumulative_sold_shares` to SQLite (pull DEF-209 forward), (c) bias reconstructed positions toward FLATTEN-FIRST (DEF-211 D3 territory).

**Disposition:** PARTIAL ACCEPT — the failure mode is real, but reviewer's proposed fixes are either fragile (option a — multi-position-on-symbol attribution is ambiguous) or scope-violating (option b — pulls DEF-209 into Sprint 31.92, a 10+ sprint horizon). Option (c) directly is also out of scope (DEF-211 D3 is Sprint 31.94). The conservative posture inside Sprint 31.92's scope: refuse all ARGUS-emitted SELLs on reconstructed positions until DEF-211 D3 lands.

**Fix shape:** Add `is_reconstructed: bool = False` to `ManagedPosition`; set `True` in `reconstruct_from_broker`. Ceiling check refuses ALL ARGUS-emitted SELLs on reconstructed positions (as if `cumulative_sold_shares = shares_total`). The position can only be closed via `scripts/ibkr_close_all_positions.py` (operator manual, bypasses OrderManager) until Sprint 31.94 D3's policy decision lands.

**Why this is conservative:** The `_startup_flatten_disabled` flag (IMPROMPTU-04) already blocks reconstruction entirely on non-clean broker state. C-1's pending reservation closes the within-ARGUS race on reconstructed positions. The remaining failure mode is ARGUS-vs-stale-bracket-child race, which DEC-386 S1c covers when cancel-on-startup succeeds. The `is_reconstructed` refusal is belt-and-suspenders against the joint-failure case.

**Trade-offs:** Legitimate flatten paths (EOD, time stop) on reconstructed positions are blocked. EOD is already blocked by `_startup_flatten_disabled` on most non-clean states; time stop requires per-position state that doesn't survive restart anyway. The reconstructed position is in a degraded-management state by definition; refusing ARGUS SELLs is the safe posture.

**Affected artifacts:** Sprint Spec (new AC3.7 `is_reconstructed`; AC3.5 specifies handling); SbC (new "Out of Scope" entry rejecting reviewer's option (a)); Session Breakdown (S4a + S5b test additions, integration-test approach for reconstructed scenarios keeps S4a at 13 score); Regression Checklist (new invariant 19); Doc Update Checklist (new RSK-RECONSTRUCTED-POSITION-DEGRADATION; DEC-390 cross-references Sprint 31.94 D3 dependency).

### C-3 — H1 cancel-and-await default reintroduces AMD-2's closed gap — ACCEPT

**Reviewer's argument:** AMD-2 ("sell before cancel") was introduced in Sprint 28.5 specifically because cancel-then-sell leaves an unprotected window during cancel propagation. H1 reintroduces exactly that window. The Sprint Spec's "bounded 50–200ms" framing is a measurement, not a tolerance argument — a volatile $7–15 stock can move $0.50–$1.00 in 200ms during a fast move (which is precisely when trail stops fire). H2 (amend-stop-price) is structurally safer: no second order placed, AMD-2 preserved, DEC-117 preserved, zero unprotected window. H1's stated rationale ("aligned with DEC-386 S1c's existing `await_propagation` infrastructure, simplest correctness story") is a familiarity argument, not a safety argument.

**Disposition:** ACCEPT in full. The reviewer is right; the original spec's H1 default did not engage AMD-2's original engineering rationale and used operational-alignment as a stand-in for safety justification.

**Fix shape:** Reverse the Hypothesis Prescription. H2 (amend-stop-price) becomes PRIMARY DEFAULT. H4 (hybrid: amend with cancel-and-await fallback) becomes the choice if H2 alone is unreliable (5–20% rejection rate). H1 (cancel-and-await) becomes LAST-RESORT FALLBACK only if S1a empirically falsifies both H2 and H4.

**AC1.5 reframed by mechanism:**
- Under H2 (default): AMD-2 invariant **PRESERVED** — bracket stop remains live throughout, only `auxPrice` changes via `modifyOrder`.
- Under H4: AMD-2 PRESERVED on H2 success path; SUPERSEDED on H1 fallback path by AMD-2-prime (unprotected window bounded by `cancel_propagation_timeout` ≤ 2s per DEC-386 S1c). Operator-visible structured log emitted at every fallback occurrence.
- Under H1 (last-resort): AMD-2 globally SUPERSEDED by AMD-2-prime. Required: structured log + dashboard surface for "trail flatten with cancel-first" so operators can audit each occurrence. Sprint Spec must state explicitly that H1 is the last-resort mechanism.

**Affected artifacts:** Sprint Spec (Hypothesis Prescription rewritten; AC1.5 rewritten by mechanism; new AC1.6 for operator-audit logging); SbC (no change — AMD-2 modification scope was already accurate); Session Breakdown (S2a/S2b unchanged in count, mechanism flips); Regression Checklist (invariant 17 rewritten).

### H-1 — Ceiling-applicability ambiguity at bracket placement — ACCEPT

**Reviewer's argument:** AC3.2 says "BEFORE every `place_order(SELL)`," but bracket placement emits T1+T2+bracket-stop (total quantity = `shares_total`) atomically. If ceiling fires at bracket placement, no bracket can ever be placed. If it doesn't, the "every `place_order(SELL)`" framing is wrong. Both interpretations produce a bug or contradict the spec.

**Disposition:** ACCEPT. Clarification needed.

**Fix shape:** AC3.2 enumerates the 5 standalone-SELL emit sites where ceiling check applies: `_trail_flatten`, `_escalation_update_stop`, `_resubmit_stop_with_retry` (incl. emergency-flatten branch), `_flatten_position`, `_check_flatten_pending_timeouts` (DEF-158 retry resubmission, the existing `# OCA-EXEMPT:` site). Bracket placement (`place_bracket_order`) is EXPLICITLY EXCLUDED — bracket children quantity equals `shares_total` by construction; OCA enforces atomic cancellation; ceiling check would block all bracket placements.

AC3.1 unchanged: T1/T2/bracket-stop fills still increment `cumulative_sold_shares` because they ARE real sells.

**Affected artifacts:** Sprint Spec (AC3.2 rewritten; goal text "5+ SELL emit sites" → "5 standalone-SELL emit sites"); SbC (new "Edge Cases to Reject" entry on bracket placement exclusion).

### H-2 — Symbol-keyed suppression breaks legitimate cross-position SELLs — ACCEPT

**Reviewer's argument:** Two `ManagedPosition`s on AAPL (sequential entries within momentum-strategy re-entry pattern). Position #1 fires SELL → IBKR locate-rejection → suppression entry for symbol AAPL. Position #2 fires legitimate SELL (T2 hit, EOD) at t+50s → AC2.4 silently skips. Acceptable for paper, real safety regression for live.

**Disposition:** ACCEPT.

**Fix shape:** Convert suppression dict to position-keyed: `_locate_suppressed_until: dict[ULID, float]` keyed by `ManagedPosition.id`. Helper signature: `_is_locate_suppressed(position: ManagedPosition, now: float) -> bool`. Clears on (a) fill callback for that specific position, (b) position close, (c) suppression-window timeout. AC2.4 reframed: "Subsequent SELL emit attempts AT THE SAME `ManagedPosition` for a suppressed position within the window: skip + INFO log + return early." Other positions on same symbol fire normally.

**Affected artifacts:** Sprint Spec (AC2.2, AC2.3, AC2.4, AC2.5 — all rewritten with position-keyed semantics); Session Breakdown (S3a +1 test, S5b +1 test for cross-position safety under load); Regression Checklist (invariant 14 — position-keyed semantics in test signature).

### H-3 — Reconnect-cascades produce false-positive alert storm — PARTIAL ACCEPT, different fix

**Reviewer's argument:** Stale suppression dict entries after reconnect → next legitimate SELL on those symbols falls through to AC2.5 → publishes `phantom_short_retry_blocked` → cessation criterion #5 fails on noise, not phantom shorts. Reviewer proposed (a) IBKRReconnectedEvent consumer that clears the dict, or (b) redefine "clean" to exclude reconnect-attributable false positives.

**Disposition:** PARTIAL ACCEPT — the failure mode is real; both proposed fixes have problems. (a) requires IBKRReconnectedEvent producer that doesn't exist until Sprint 31.94. (b) dilutes the cessation criterion gate.

**Fix shape:** AC2.5's suppression-timeout fallback queries broker for the position's actual state BEFORE publishing alert. If broker shows ARGUS-expected long, suppress alert. If broker shows zero, log INFO ("held order resolved cleanly"). If broker shows unexpected state (short or qty divergence), publish `phantom_short_retry_blocked` per existing path.

```python
async def _handle_locate_suppression_timeout(self, position: ManagedPosition) -> None:
    broker_positions = await self._broker.get_positions()
    actual = next((p for p in broker_positions if p.symbol == position.symbol), None)
    if actual is None:
        logger.info("Locate suppression timeout for %s: broker shows zero. Held order resolved cleanly.", position.symbol)
        return
    if actual.side == OrderSide.BUY and abs(actual.shares) >= position.shares_remaining:
        logger.info("Locate suppression timeout for %s: broker shows expected long. No phantom short.", position.symbol)
        return
    # Broker shows unexpected state — phantom short evidence
    await self._event_bus.publish(SystemAlertEvent(alert_type="phantom_short_retry_blocked", ...))
```

**Why this is structurally cleaner:** Eliminates false-positive class without coupling to events that don't have producers yet. Latency 50–200ms acceptable on the slow path. Reconnect-event coupling stays deferred to Sprint 31.94 when `IBKRReconnectedEvent` producer lands.

**Affected artifacts:** Sprint Spec (AC2.5 rewritten with broker-verification step; new performance benchmark line); SbC (§"Edge Cases to Reject" #5 updated to reflect mitigation); Session Breakdown (S3b +2 tests — false-positive scenario, true-positive preservation); Regression Checklist (invariant 14 expanded).

### H-4 — `bracket_oca_type=0` rollback re-opens DEC-386's closed bug — PARTIAL ACCEPT, different fix

**Reviewer's argument:** AC4.4's parametrized test over `bracket_oca_type ∈ {0, 1}` affirms ocaType=0 as a supported configuration. But ocaType=0 disables OCA — exactly the configuration DEC-386 closed. By making the constant runtime-configurable, DEF-212 rider exceeds its stated scope: it adds a runtime-flippable lever for a safety-critical decision. Reviewer proposed (a) validator-restrict to literal 1, or (b) prominent documentation.

**Disposition:** PARTIAL ACCEPT — the concern is real, but reviewer's option (a) supersedes DEC-386's design intent (DEC-386 explicitly designed the rollback escape hatch for emergency operator response). Sprint 31.92 doesn't have the prerogative to change DEC-386's rollback mechanism.

**Fix shape:**
1. Startup warning when `bracket_oca_type != 1`: CRITICAL log emitted at OrderManager init time with explicit "DEC-386 ROLLBACK ACTIVE: DEF-204 race surface is REOPENED" framing.
2. AC4.4 reframed from "ocaType=0 works as rollback" to "lock-step preserved during emergency rollback." The test asserts that flipping to 0 produces consistent ocaType=0 across bracket children AND standalone-SELL OCA threading (no divergence). Affirms the lock-step property of the DEF-212 fix; does NOT affirm ocaType=0 as operationally valid.
3. Documentation in `docs/live-operations.md` of the rollback-reopens-DEF-204 risk + explicit operator emergency-response procedure.
4. Pre-live-transition-checklist verifies `bracket_oca_type=1` before live trading (already in Phase C C9; reaffirmed).

**Affected artifacts:** Sprint Spec (new AC4.6 startup warning; AC4.4 reframed); Session Breakdown (S4b unchanged in score; +1 test for startup warning); Regression Checklist (invariant 16 — lock-step framing); Doc Update Checklist (live-operations.md addition specified in Phase C C7).

### M-1 — 300s suppression vs 3-hour observed hold — ACCEPT

**Reviewer's argument:** Apr 28 PCT trace had IBKR releasing held orders 3+ hours after first emit. AC2.5's 300s timeout fires far too early. H6's "median release time < 60s and p99 < 240s" is not validated against the symbol class that produced the failure (PCT was a hard-to-borrow microcap). Spike measurements need to specifically target hard-to-borrow names.

**Disposition:** ACCEPT.

**Fix shape:** S1b spike requirements revised — operator pre-curates ≥5 known hard-to-borrow microcap symbols (PCT-class). Force SELL emission on each (paper trading, small share size). Measure: time from rejection to either fill OR explicit cancel. ≥10 trials per symbol. Output: median, p95, p99, max release window per symbol class. H6 confirms-if condition tightened to require representativeness.

Default `locate_suppression_seconds` derived from spike: target `p99 + 20% margin`. If spike measures p99 = 4hr, default to 5hr. Pydantic validator updated: `Field(default=18000, ge=300, le=86400)` (5min to 24hr).

The H-3 broker-verification fix composes correctly with long suppression windows: no false-positive alerts during the long wait, just silent waiting until the held order resolves or the timeout fires for verification.

**Affected artifacts:** Sprint Spec (Hypothesis Prescription H6 rewritten; AC2.5 default value placeholder for spike-driven number; Config Changes table updated); Session Breakdown (S1b operator pre-flight expanded).

### M-2 — SimulatedBroker validation framing — ACCEPT

**Reviewer's argument:** AC5 produces JSON artifacts via SimulatedBroker scenarios. Apr 28 incident occurred on paper IBKR, not SimulatedBroker. SimulatedBroker doesn't model IBKR API latency variance, network packet loss, modifyOrder timing, locate-rejection timing variability, or concurrent fill arrival ordering. "phantom_shorts_observed: 0" in synthetic scenario does not falsify production failure mode. The spec frames JSONs as "falsifiable evidence with 30-day freshness" — implying they substitute for production evidence. They don't.

**Disposition:** ACCEPT.

**Fix shape:** Reframe AC5.1 and AC5.2 as **in-process logic correctness via SimulatedBroker fixture; does NOT validate IBKR-API-interaction logic.** Cessation criterion #5 (5 paper sessions clean post-seal) is the production-validation gate. The 30-day freshness window applies to the in-process invariant — i.e., "when this code path is exercised against the SimulatedBroker fixture, it produces correct in-process bookkeeping" — not to "production safety is preserved."

**Affected artifacts:** Sprint Spec (AC5.1 + AC5.2 framing); Escalation Criteria (cessation criterion section reframed); Doc Update Checklist (regression invariant 18 framing).

### M-3 — Composite validation Pytest demotion trades freshness — PARTIAL ACCEPT, different fix

**Reviewer's argument:** AC5.3 was demoted from standalone JSON to Pytest test for compaction-risk reasons. JSONs have 30-day freshness; tests don't. Reviewer proposed (a) restore standalone script, or (b) daily CI check + timestamp.

**Disposition:** PARTIAL ACCEPT — restoring standalone composite script pushes S5b back over compaction-risk threshold; daily CI check is overhead. Cleaner: combine the test approach with a JSON-artifact-as-test-side-effect pattern.

**Fix shape:** Pytest integration test produces `scripts/spike-results/sprint-31.92-validation-composite.json` as a side-effect on successful run. The test fixture writes the JSON before assertion. Daily CI workflow runs the test; artifact mtime tracks freshness. Preserves session budget AND freshness property AND keeps composite logic in-suite where regressions fail noisy.

```python
def test_composite_validation_zero_phantom_shorts_under_load(...):
    result = run_composite_scenario(...)
    write_validation_artifact(
        path="scripts/spike-results/sprint-31.92-validation-composite.json",
        result=result,
    )
    assert result.phantom_shorts_observed == 0
    assert result.ceiling_violations_correctly_blocked >= 1
```

**Affected artifacts:** Sprint Spec (AC5.3 framing); Doc Update Checklist (CI workflow addition specified); Session Breakdown (S5b +1 LOC for fixture write helper, score unchanged).

## Workflow protocol amendment surfaced by this review

Reviewer's Q9 disposition recommended a sprint-planning-protocol amendment: "DEC entries claiming closure should use 'structural closure of mechanism X with falsifiable test fixture Y' rather than 'closes ~Z% of blast radius'."

This amendment is captured for the next campaign's RETRO-FOLD per `process-evolution.md` lesson F.5 (defined in Phase C `doc-update-checklist.md` C10). Not amended in-line here — protocol changes flow through the metarepo's per-file versioning pattern.

## Sprint package re-baseline

Net effect of revisions on session count: **unchanged at 10 sessions.** S4a's compaction risk score becomes 14 (HIGH) if all C-2 tests land at S4a; mitigation: defer the reconstructed-position regression tests to S5b (more naturally tested in integration). S4a stays at 13 (Medium). All 10 sessions preserve ≤13.5 score.

Net effect on test count: pytest target raised from 5,322–5,334 to ~5,340–5,360 (~75–95 new tests, up from 53–65). Vitest unchanged at 913.

Net effect on adversarial-review schedule: Round 2 required. Scope narrower than Round 1 — validate the fixes specifically, not the original design. See revised `adversarial-review-input-package.md` §"Round 2 framing" for scrutiny questions targeted at the revisions.
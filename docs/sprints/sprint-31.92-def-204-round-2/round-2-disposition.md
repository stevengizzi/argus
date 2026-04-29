# Sprint 31.92 — Round 2 Disposition

> **Phase C-1 Round 2 artifact.** Logs the disposition of each finding from the Round 2 adversarial review (Outcome B — 1 Critical + 5 High + 5 Medium + 3 Low). Companion to Round 1's `revision-rationale.md`. Records what was accepted, what was partially accepted with a different fix, and the reasoning. Surfaces the meta-pattern (primitive-semantics assumptions) that warrants protocol-level amendment.
>
> **Verdict received:** 2026-04-29.
> **Verdict author:** Adversarial Round 2 reviewer (separate Claude.ai conversation, per `protocols/adversarial-review.md`).
> **Disposition author:** Sprint 31.92 planner.
> **A-class halt fires:** A14 (Round 2 produced ≥1 Critical finding).
> **Phase D status:** NOT proceeding. Phase A-bounded re-entry required.
> **Round 3 required:** YES. Narrowest possible scope (validate Round 2 fixes; do not re-litigate Round 1).

---

## Summary

| # | Severity | Disposition | Fix shape (one-line) |
|---|----------|-------------|----------------------|
| C-R2-1 | Critical | PARTIAL ACCEPT (different) | New `Broker.refresh_positions()` ABC method; AC2.5 forces refresh-then-verify; new Branch 4 ("reconnect-stale") fires alert with `verification_stale: true`. |
| H-R2-1 | High | ACCEPT (option b) | Atomic `_reserve_pending_or_fail()` synchronous method; AST-level guard asserts no `await` in body. |
| H-R2-2 | High | ACCEPT | Under H1 fallback + locate-rejection: immediate `phantom_short_retry_blocked` alert + `halt_entry_until_operator_ack`; S1a halt-or-proceed gate tightened. |
| H-R2-3 | High | ACCEPT (partial) | RSK re-rated to MEDIUM-HIGH; Sprint Abort Condition #7 trigger lowered to 2 weeks; operator-flatten-script load profile spike added as deferred item; 31.94 D3 prioritization flagged for separate roadmap decision. |
| H-R2-4 | High | ACCEPT (combined) | AC4.6 emits BOTH ntfy.sh `system_warning` AND canonical-logger CRITICAL; new AC4.7 requires `--allow-rollback` CLI flag for startup with `bracket_oca_type != 1`. |
| H-R2-5 | High | ACCEPT | AC3.2 distinguishes standalone-exit SELLs (ceiling-checked) from stop-replacement SELLs (NOT ceiling-checked) via `is_stop_replacement: bool` flag; emergency-flatten branch remains ceiling-checked. |
| M-R2-1 | Medium | ACCEPT | S1b spike differentiates case A (held order, no exception) from case B (rejected); new AC2.7 `_pending_sell_age_seconds` watchdog if case A observed. |
| M-R2-2 | Medium | ACCEPT | AC2.6 specifies `on_position_closed` as canonical handler; regression test exercises all four position-close paths. |
| M-R2-3 | Medium | ACCEPT | A13 freshness check requires BOTH mtime ≤ 30 days AND JSON content satisfies success state. C9 item 10 clarifies "≥7 consecutive daily green runs" means content-green not just-ran. |
| M-R2-4 | Medium | ACCEPT (option b) | S1a uses Wilson upper-bound as decision input. 50-trial sample size preserved. |
| M-R2-5 | Medium | ACCEPT | Mandatory mid-sprint Tier 3 review scheduled at S4a close-out, BEFORE S5a/S5b validation begin. |
| L-R2-1 | Low | ACCEPT | SbC §"Out of Scope" #20/#21 rejection rationales rephrased from "definitively impossible" to "judged-not-worth-the-marginal-complexity." |
| L-R2-2 | Low | ACCEPT | DEC-390 Context section adds note on multi-position-on-symbol restart attribution loss as known limitation. |
| L-R2-3 | Low | ACCEPT | Cumulative diff bound on `order_manager.py` recalibrated to ~1100–1200 LOC. |

**14 of 14 findings accepted.** 4 with different/partial fix shape (C-R2-1, H-R2-3, H-R2-4, M-R2-4); 10 in full.

---

## Per-finding rationale

### C-R2-1 — H-3 broker-verification depends on unverified ib_async cache-freshness behavior — PARTIAL ACCEPT (different fix)

**Reviewer's argument:** The Round 1 disposition's chosen H-3 fix (broker-verification at suppression timeout via `broker.get_positions()`) inherits the cache-staleness problem the reconnect-event-consumer alternative was designed to eliminate. `ib_async` maintains a local position cache populated by `positionEvent` subscriptions; `IB.positions()` is a synchronous local-cache lookup, NOT a broker round-trip. After a reconnect, during the reconnection-and-resubscription window, the cache returns the pre-disconnect state. AC2.5's three-branch logic classifies stale-cached-long as Branch 1 (silent INFO; clear dict entry), masking exactly the post-reconnect anomaly the verification was designed to catch.

**Disposition:** PARTIAL ACCEPT. The reviewer's diagnosis is correct; the chosen fix shape is not. The reconnect-event-consumer alternative remains blocked by Sprint 31.94's producer-non-existence; the Round 1 fix's implicit assumption about cache freshness was unverified. The chosen fix preserves Round 1's deferred-coupling structure but adds the cache-refresh primitive and a stale-window safety net.

**Fix shape (different from reviewer's options a + b):**

1. **New `Broker.refresh_positions()` ABC method.** Forces broker round-trip on demand. `IBKRBroker` implementation calls `IB.reqPositions()`, awaits the `positionEndEvent`, with a configurable timeout (default 5s).

   ```python
   class Broker(ABC):
       @abstractmethod
       async def refresh_positions(self, *, timeout_seconds: float = 5.0) -> None:
           """Force broker-side position cache refresh. Blocks until cache is
           synchronized with broker state OR timeout expires. AC2.5 prerequisite.
           """
           ...

   class IBKRBroker(Broker):
       async def refresh_positions(self, *, timeout_seconds: float = 5.0) -> None:
           end_event = asyncio.Event()
           def _on_position_end():
               end_event.set()
           self._ib.positionEndEvent += _on_position_end
           try:
               self._ib.reqPositions()
               await asyncio.wait_for(end_event.wait(), timeout=timeout_seconds)
           finally:
               self._ib.positionEndEvent -= _on_position_end
   ```

2. **AC2.5 amended: refresh-then-verify, with Branch 4 safety net.**

   ```python
   async def _handle_locate_suppression_timeout(self, position: ManagedPosition) -> None:
       try:
           await self._broker.refresh_positions(timeout_seconds=5.0)
       except (asyncio.TimeoutError, Exception) as exc:
           # Branch 4: refresh failed — verification is stale by definition
           await self._event_bus.publish(SystemAlertEvent(
               alert_type="phantom_short_retry_blocked",
               metadata={
                   "position_id": position.id,
                   "symbol": position.symbol,
                   "verification_stale": True,
                   "verification_failure_reason": type(exc).__name__,
               },
           ))
           return
       broker_positions = await self._broker.get_positions()
       actual = next((p for p in broker_positions if p.symbol == position.symbol), None)
       # Existing Branches 1/2/3 logic continues here, now operating on refreshed data...
   ```

3. **S3b spike scope expanded** with a sub-spike that empirically falsifies (not merely measures) post-reconnect cache freshness:
   - Trial protocol: simulate Gateway disconnect/reconnect during paper hours; time the gap between `connectedEvent` firing and first `positionEvent` arrival; derive empirical "reconnect-staleness window."
   - Output JSON: `cache_staleness_p95_ms`, `cache_staleness_max_ms`, `refresh_success_rate`, `refresh_p95_ms`.
   - Halt-or-proceed gate: if `cache_staleness_max_ms > refresh_timeout_seconds * 1000`, the chosen fix is itself unreliable; halt and surface to operator.

4. **RSK-SUPPRESSION-LEAK rewritten.** Old text wrongly described silent-INFO-on-stale-long as the mitigation; new text captures cache-staleness explicitly and identifies the refresh-then-verify pattern + Branch 4 as the structural defense, with Sprint 31.94's reconnect-event consumer as the ultimate fix.

**Performance benchmark amendment.** AC2.5 latency budget grows to ~5.2s worst-case (refresh round-trip + 5s timeout + verification call). This is acceptable on the slow path (suppression timeout fires once per position per session in the worst case), unacceptable on hot paths. The benchmark line in the spec is updated to reflect the slow-path classification.

**Why not reviewer's option (a) directly?** Option (a) (force broker round-trip) is essentially what we're doing. The difference is structural: introducing the ABC method makes the contract explicit and testable, rather than embedding the refresh call inline in AC2.5. Option (b) (reconnect-staleness window guard with empirical N) is also incorporated as Branch 4's `verification_stale: true` metadata, but with the simpler "refresh fails → verification is stale by definition" semantic instead of a time-window heuristic.

**Affected artifacts:** Sprint Spec (AC2.5 rewritten; AC2.7 NEW for `Broker.refresh_positions()` contract; Performance Benchmarks updated; Config Changes table unchanged); SbC (§"Edge Cases to Reject" #5 updated to acknowledge refresh-then-verify; new Edge Case #18 for refresh-failure semantics); Session Breakdown (S3b score +1; sub-spike addition; +2 pytest tests for refresh-success and refresh-timeout-fallback paths); Regression Checklist (new invariant on `Broker.refresh_positions()` ABC contract; SimulatedBroker fixture must implement refresh as no-op or instant-success); Doc Update Checklist (DEC-390 L2 description amended); RSK list (RSK-SUPPRESSION-LEAK rewritten).

---

### H-R2-1 — Synchronous-before-await ordering structurally fragile — ACCEPT (option b)

**Reviewer's argument:** The C-1 reservation pattern's correctness rests on `_check_sell_ceiling` and `cumulative_pending_sell_shares += requested_qty` executing in the same synchronous slice with no `await` between them. This is implementation discipline, not enforcement. A future refactor introducing an `await` between check and increment silently re-opens the original race. AC3.5's race test verifies outcome under deterministic scheduling, not mechanism.

**Disposition:** ACCEPT, with reviewer's option (b) as the chosen fix. Atomic check-and-reserve method is the most refactor-safe option; AST-level guards make the contract typeable.

**Fix shape:**

```python
def _reserve_pending_or_fail(self, position: ManagedPosition, qty: int) -> bool:
    """Synchronously check ceiling and reserve qty if it passes.
    
    No await inside this method. Verified by `assert not asyncio.iscoroutinefunction`
    plus AST-level scan in regression suite. Caller awaits place_order ONLY
    after this returns True.
    """
    if not self._check_sell_ceiling(position, qty, is_stop_replacement=False):
        return False
    position.cumulative_pending_sell_shares += qty
    return True
```

Regression test:

```python
def test_reserve_pending_or_fail_is_synchronous():
    om = OrderManager(...)
    # Type-level: not a coroutine function
    assert not asyncio.iscoroutinefunction(om._reserve_pending_or_fail)
    # AST-level: no await keyword in body
    src = inspect.getsource(om._reserve_pending_or_fail)
    tree = ast.parse(textwrap.dedent(src))
    awaits = [n for n in ast.walk(tree) if isinstance(n, ast.Await)]
    assert len(awaits) == 0, "synchronous contract violated"
```

Defense-in-depth via reviewer's option (c): mocked-await injection test. Monkey-patch the implementation to insert `await asyncio.sleep(0)` between check and reserve; assert the race DOES happen. If the test passes (i.e., race observed under injection), the test is sensitive to mechanism. If the test still refuses the second coroutine under injection, the test is verifying outcome only and is unsound.

**Affected artifacts:** Sprint Spec (AC3.1 + AC3.2 rewritten to use `_reserve_pending_or_fail`; AC3.5 race test extended with AST guard + injection test); Session Breakdown (S4a +2 tests); Regression Checklist (new invariant: `_reserve_pending_or_fail` synchronous contract).

---

### H-R2-2 — H1 last-resort + locate-suppression composite failure mode — ACCEPT

**Reviewer's argument:** Under H1 fallback (cancel-and-await before SELL), if the post-cancel SELL is locate-rejected per AC2.1, the position has NO active stop AND NO active flatten attempt for the suppression-window duration (5hr default on hard-to-borrow microcaps). DEF-158 retry path is itself a ceiling-checked emit site (also blocked by suppression). On a high-volatility microcap, this is catastrophic-loss territory — RSK-DEC-390-CANCEL-AWAIT-LATENCY underestimates by 4 orders of magnitude (200ms vs 5hr).

**Disposition:** ACCEPT. The composite failure mode is real and severe under H1 selection.

**Fix shape:**

1. **AC1 amended for H1-fallback-locate-reject branch.** Do NOT enter normal suppression. Instead:
   - Fire IMMEDIATE `phantom_short_retry_blocked` alert with metadata `{cause: "h1_post_cancel_locate_reject", position_unprotected: true, position_id: <ulid>, symbol: <str>}`.
   - Mark position with `halt_entry_until_operator_ack: bool = True`.
   - Operator must explicitly acknowledge before any further action on that position.
   - DO NOT attempt re-bracket (that adds significant scope and would itself be subject to locate-rejection recurrence). Operator-driven resolution is the chosen path.

2. **S1a halt-or-proceed gate language tightened:**

   > "If H2 and H4 are both falsified, do NOT proceed to H1 silently. HALT and surface to operator with explicit confirmation step. Operator must confirm H1 selection in writing (close-out judgment-call section, with cross-reference to S1a JSON artifact). Cessation criterion #5 alone is insufficient evidence under H1 selection — paper trading on hard-to-borrow microcaps with H1 selected and a 5hr unprotected window may simply not produce the failure within 5 sessions."

3. **RSK-DEC-390-CANCEL-AWAIT-LATENCY rewritten** to capture the composite 5hr unprotected window. Severity: HIGH conditional on H1 selection.

4. **New deferred item:** if H1 is selected by S1a, file DEF for Sprint 31.94+ to evaluate whether cessation criterion needs strengthening for H1-selected paths.

**Why not the reviewer's "re-place a fresh bracket" option?** Re-bracketing on locate-rejection adds non-trivial scope (parent + T1 + T2 + bracket-stop placement, all subject to the same locate-rejection recurrence). The simpler operator-driven HALT-ENTRY posture is consistent with ARGUS's "non-bypassable validation as a design posture" learning and matches DEC-385's "defer to operator" patterns.

**Affected artifacts:** Sprint Spec (AC1 rewritten with H1-fallback-and-locate-reject branch; new ManagedPosition field `halt_entry_until_operator_ack: bool = False`); SbC (new Edge Case #19: H1-fallback-locate-reject is operator-resolved, not auto-recovered); Session Breakdown (S2b +2 tests for H1-fallback-locate-reject path and HALT-ENTRY enforcement); Regression Checklist (new invariant 23 on H1-fallback-locate-reject behavior); RSK list (RSK-DEC-390-CANCEL-AWAIT-LATENCY rewritten).

---

### H-R2-3 — RSK-RECONSTRUCTED-POSITION-DEGRADATION severity under-calibrated — ACCEPT (partial)

**Reviewer's argument:** RSK is filed at LOW-MEDIUM with mitigation "operator daily-flatten script handles cleanup." Apr 28 already proved this safety net can fail (27 of 87 ORPHAN-SHORT detections from a missed run). Sprint 31.94 D3 dependency could be 6+ weeks away if 31.93 + 31.94 each take 3 weeks. Multi-position-on-symbol restart loses attribution structure. Operator-flatten-script load profile under stress unmeasured.

**Disposition:** ACCEPT (partial). All four sub-points are valid. The Phase 0 prioritization decision (should 31.94 D3 land before 31.93?) is a roadmap-level question not appropriate for a Sprint 31.92 disposition; flagged for separate operator decision.

**Fix shape:**

1. **RSK-RECONSTRUCTED-POSITION-DEGRADATION re-rated to MEDIUM-HIGH.** Mitigation text expanded: operator daily-flatten is a known-fallible safety net; Apr 28 precedent demonstrates failure mode; RSK time-bound depends on Sprint 31.94 D3 sealing.

2. **Sprint Abort Condition #7 trigger lowered from 4 weeks to 2 weeks.** If Sprint 31.94 D3 has not sealed within 2 weeks of Sprint 31.92 seal, escalate to operator review. (Calendar-based; not auto-abort; surfaces the operational risk during the bound rather than suppressing it.)

3. **New deferred item:** "Operator-flatten script load profile under 50+ position scenarios" — small spike that loads `scripts/ibkr_close_all_positions.py` with a synthetic 50-position fixture and verifies clean close. NOT a Sprint 31.92 deliverable. Filed for Sprint 31.94 or earlier opportunistic touch.

4. **Roadmap-level question flagged for operator decision (NOT a Sprint 31.92 deliverable):** should Sprint 31.94 D3 (boot-time adoption-vs-flatten policy) be prioritized ahead of Sprint 31.93 (component-ownership refactor)? The current build-track puts 31.93 first based on "component-ownership enables 31.94 D1+D2." But Sprint 31.92 inherits the RSK-RECONSTRUCTED-POSITION-DEGRADATION dependency. Reordering would shorten the bound. Reordering would also delay component-ownership benefits (DEF-175/182/193/201/202 absorption). This is a trade-off requiring operator input + likely a separate Discovery activity.

5. **DEC-390 Context section** documents multi-position-on-symbol restart attribution loss as known limitation (per L-R2-2; folded into this disposition).

**Affected artifacts:** Sprint Spec (Sprint Abort Condition #7 trigger lowered); SbC (Deferred Items table adds operator-flatten-script load profile spike); Doc Update Checklist (DEC-390 Context note added); RSK list (RSK-RECONSTRUCTED-POSITION-DEGRADATION rewritten with MEDIUM-HIGH severity); roadmap recommendation surfaced separately to operator.

---

### H-R2-4 — AC4.6 startup CRITICAL warning observability-weak — ACCEPT (combined fix)

**Reviewer's argument:** "Via the canonical ARGUS logger pipeline" is file-only logging. The canonical operator-attention channel for ARGUS is ntfy.sh push notifications. The CRITICAL warning at startup is in a channel the operator does not actively monitor. The threat model is accidental rollback (intentional rollback already has operator awareness); the only audience is an operator who didn't intend to rollback, who by definition is not watching startup logs. Reviewer proposed (a) ntfy.sh emission OR (b) `--allow-rollback` flag requirement.

**Disposition:** ACCEPT, with BOTH (a) and (b) combined. Defense-in-depth is consistent with ARGUS's "non-bypassable validation as a design posture" learning AND preserves DEC-386's rollback escape hatch (operator can pass the flag).

**Fix shape:**

```python
# argus/main.py, in startup logic, before OrderManager construction
if config.ibkr.bracket_oca_type != 1:
    if not args.allow_rollback:
        sys.stderr.write(
            "FATAL: bracket_oca_type != 1 (DEC-386 ROLLBACK ACTIVE: DEF-204 race "
            "surface is REOPENED). To proceed intentionally, restart with --allow-rollback.\n"
        )
        sys.exit(2)
    # Operator confirmed via flag — emit BOTH channels
    logger.critical(
        "DEC-386 ROLLBACK ACTIVE: DEF-204 race surface is REOPENED "
        "(bracket_oca_type=%d, --allow-rollback=true)",
        config.ibkr.bracket_oca_type,
    )
    await ntfy_publish(
        topic="argus_alerts",
        priority="urgent",
        title="DEC-386 ROLLBACK ACTIVE",
        message="DEF-204 race surface is REOPENED. bracket_oca_type=%d." % config.ibkr.bracket_oca_type,
    )
```

**Why both channels?** ntfy.sh provides the operator-attention channel (push notification surfaces immediately on phone/desktop). Canonical-logger CRITICAL provides the audit-trail channel (recorded in `logs/argus_*.jsonl`). The `--allow-rollback` flag provides the gate that transforms "accidental rollback" (which the warning protects against) into "explicit operator action."

**Affected artifacts:** Sprint Spec (AC4.6 rewritten; new AC4.7 for CLI flag handling); SbC (§"Out of Scope" #22 updated — DEC-386 rollback escape hatch preserved via `--allow-rollback`, not via runtime-flippable field); Session Breakdown (S4b +1 test for startup with `--allow-rollback`; +1 test for startup without flag → exit code 2); Regression Checklist (new invariant: startup MUST exit non-zero when `bracket_oca_type != 1` and `--allow-rollback` absent).

---

### H-R2-5 — `_resubmit_stop_with_retry` ceiling-vs-protective conflict — ACCEPT

**Reviewer's argument:** The C-1 reservation ceiling is purpose-blind. `_resubmit_stop_with_retry`'s normal retry path exists specifically to ensure the position has an active bracket-stop after a transient placement failure. If the ceiling refuses the retry (because another flatten attempt has incremented `cumulative_pending_sell_shares`), the position has no stop. This is a NEW failure mode introduced by C-1's universal ceiling application. Standalone exit SELLs (over-flatten risk) and stop-replacement SELLs (protective) have different safety profiles; refusing a protective stop replacement is worse than the over-flatten the ceiling prevents.

**Disposition:** ACCEPT. The differentiation is correct — bracket children are already excluded from ceiling check (per H-1 disposition); stop replacements (which re-establish the bracket-child role after transient failure) deserve the same exemption.

**Fix shape:**

```python
def _check_sell_ceiling(
    self,
    position: ManagedPosition,
    requested_qty: int,
    *,
    is_stop_replacement: bool = False,
) -> bool:
    """Check whether emitting a SELL of `requested_qty` exceeds the long-only
    invariant (cumulative_pending + cumulative_sold + requested ≤ shares_total).
    
    Stop replacements (re-establishing protective bracket-stop after transient
    placement failure) are exempt from the ceiling — refusing a protective
    stop replacement is worse than the over-flatten the ceiling prevents.
    Caller MUST set is_stop_replacement=True ONLY for the normal retry path
    of _resubmit_stop_with_retry. Emergency-flatten branch (DEC-372 retry cap
    exhausted) MUST set is_stop_replacement=False.
    """
    if is_stop_replacement:
        return True
    return (
        position.cumulative_pending_sell_shares
        + position.cumulative_sold_shares
        + requested_qty
    ) <= position.shares_total
```

`_reserve_pending_or_fail` propagates the flag.

**Caller sites (5 standalone-SELL emit sites, AC3.2):**
- `_trail_flatten` → `is_stop_replacement=False`
- `_escalation_update_stop` → `is_stop_replacement=False`
- `_resubmit_stop_with_retry` (normal retry path) → `is_stop_replacement=True`
- `_resubmit_stop_with_retry` (emergency-flatten branch) → `is_stop_replacement=False`
- `_flatten_position` → `is_stop_replacement=False`
- `_check_flatten_pending_timeouts` (DEF-158 retry resubmission) → `is_stop_replacement=False`

**Affected artifacts:** Sprint Spec (AC3.2 rewritten with stop-replacement exemption; AC3.1 documents the flag's semantic and caller responsibilities); SbC (§"Edge Cases to Reject" #15 extended — bracket-children AND stop-replacement are both protective-placement exemptions; new Edge Case #20 explicitly forbids any other code path from using `is_stop_replacement=True`); Session Breakdown (S4a +2 tests: stop-replacement bypass succeeds even at ceiling; emergency-flatten branch still gated); Regression Checklist (new invariant 24: `is_stop_replacement=True` permitted ONLY at `_resubmit_stop_with_retry` normal-retry path; AST-level guard scans codebase for any other usage).

---

### M-R2-1 — Held-order semantics case A vs case B — ACCEPT

**Reviewer's argument:** IBKR exhibits two distinct behaviors on hard-to-borrow symbols: (A) order accepted, broker holds it pending borrow, no exception, pending counter stays incremented; (B) order rejected immediately with locate-rejection error string. AC2.1's substring fingerprint matches case (B) only. Case (A) leaves a stuck-pending order with the ceiling silently blocking subsequent emits.

**Disposition:** ACCEPT.

**Fix shape:**

1. **S1b spike differentiates case A and case B explicitly.** Output JSON includes `case_a_observed: bool`, `case_a_count: int`, `case_b_count: int`, `case_a_max_age_seconds: int` (longest pending duration before resolution).

2. **If case A is observed**, NEW AC2.7: `_pending_sell_age_seconds` watchdog. Periodic check (every 60s) on each `ManagedPosition` with `cumulative_pending_sell_shares > 0`; if oldest pending age exceeds threshold (default 600s = 10min), fire DEF-158 retry path proactively (bypassing locate-suppression check, since the suppression check would itself block this).

3. **If case A is NOT observed in S1b**, AC2.7 is deferred (filed as conditional DEF for revisit if case A surfaces in production paper trading).

**Why not handle case A unconditionally?** Adding a watchdog when the failure mode is unobserved is speculative complexity. Spike-driven gating is the disciplined pattern.

**Affected artifacts:** Sprint Spec (S1b output schema extended; new conditional AC2.7); Session Breakdown (S1b spike scope +1 measurement axis; conditional S3a/S3b test additions if case A observed); Regression Checklist (conditional invariant on watchdog if AC2.7 lands).

---

### M-R2-2 — AC2.6 "position close" trigger under-specified — ACCEPT

**Reviewer's argument:** AC2.6 clears suppression dict on "fill, position close, or timeout." But "position close" is multi-definitional in ARGUS: (a) broker confirms zero shares, (b) `_flatten_pending` clears, (c) `ManagedPosition` removed from active-positions dict, (d) `on_position_closed` event fires. Different timing semantics; if implementation clears only on (d) but position is removed via (c) without (d), the entry leaks.

**Disposition:** ACCEPT.

**Fix shape:**

1. **AC2.6 specifies `on_position_closed` event handler as canonical clear-path.** Existing event fires whenever `ManagedPosition` transitions to closed state.

2. **Regression test exercises all four position-close paths:**
   ```python
   def test_suppression_dict_cleared_on_all_position_close_paths():
       om = OrderManager(...)
       for close_path in ["broker_zero", "flatten_pending_clears", "active_positions_remove", "on_position_closed_fires"]:
           position = create_test_position()
           om._locate_suppressed_until[position.id] = time.time() + 18000
           trigger_close_path(close_path, position)
           assert position.id not in om._locate_suppressed_until, f"leak via {close_path}"
   ```

3. **If any close path does NOT trigger `on_position_closed`**, audit-and-fix-or-document at S3b. Either the event must fire from all close paths, OR the dict-clear logic subscribes to multiple events.

**Affected artifacts:** Sprint Spec (AC2.6 rewritten with `on_position_closed` canonical handler); Session Breakdown (S3b +1 test exercising all four close paths); Regression Checklist (new invariant 25 on suppression dict cleanup completeness).

---

### M-R2-3 — A-class halt A13 freshness check semantics — ACCEPT

**Reviewer's argument:** Pytest test (AC5.3) writes JSON before assertion. If assertion fails, JSON contains failure-state values. mtime updates regardless. Daily CI workflow consistently producing failed artifacts looks "fresh" to mtime-only check. Live transition could proceed on green-mtime + red-content.

**Disposition:** ACCEPT.

**Fix shape:**

A13 freshness check requires BOTH:
1. `mtime > now - 30 days` (freshness invariant)
2. JSON content satisfies success state: `phantom_shorts_observed == 0` AND `total_sold_le_total_bought == true` AND `ceiling_violations_correctly_blocked >= 1` AND `path1_safe == true` AND `path2_suppression_works == true`

If EITHER fails, A13 fires.

Pre-live-transition checklist C9 item 10 clarified: "≥7 consecutive daily green runs before live transition consideration" — operator MUST verify content-green AND mtime-green. CI workflow output should display both.

**Affected artifacts:** Sprint Spec (A-class halt A13 amended with content-check); Doc Update Checklist (C9 item 10 clarified); Regression Checklist (new invariant: A13 fires on either mtime-stale OR content-failed).

---

### M-R2-4 — S1a 50-trial sample size wide CIs — ACCEPT (option b: Wilson upper-bound)

**Reviewer's argument:** Wilson CI for true rejection rate of 5% with 50 trials is roughly [1.4%, 16.5%]. Mechanism choice between H2 alone and H4 hybrid is sensitive to a sampling artifact. Reviewer proposed (a) increase trials to ≥150 OR (b) use Wilson upper-bound as decision input.

**Disposition:** ACCEPT, option (b). 50 trials is operationally feasible during a single pre-market window; 150 trials would extend S1a session. Wilson upper-bound is the asymmetric-conservative choice (more fallback paths chosen — H4 over H2 when in doubt — which aligns with safety-driven hierarchy).

**Fix shape:** S1a halt-or-proceed gate updated:

> "Compute Wilson upper-bound (95% confidence) from observed rejection rate. Decision rule: pick H2 if Wilson UB < 5%; pick H4 if 5% ≤ Wilson UB < 20%; pick H1 if Wilson UB ≥ 20%. The Wilson UB asymmetrically biases toward more conservative fallback paths under sampling uncertainty."

**Affected artifacts:** Sprint Spec (Hypothesis Prescription updated with Wilson UB decision rule); S2a impl prompt template (consume Wilson UB from S1a JSON, not point estimate).

---

### M-R2-5 — Mid-sprint Tier 3 review absent — ACCEPT

**Reviewer's argument:** Sprint 31.91 had 2 Tier 3 reviews. Sprint 31.92 has architectural-closure ambition (DEC-390 as 4-layer structural defense), 10 sessions touching `order_manager.py` 6 times, critical Phase B → Phase C handoff at S4a. Tier 3 mentioned only as A-class halt trigger, not scheduled milestone. S4a close-out is the natural milestone (pending-reservation, ceiling, is_reconstructed, AC4.6 startup-warning all delivered; validation downstream).

**Disposition:** ACCEPT. The S4a milestone is the right gate — would catch any of the Round 2 High findings (or Critical) before validation locks them in.

**Fix shape:**

Mandatory mid-sprint Tier 3 review scheduled at S4a close-out, BEFORE S5a/S5b validation begin. Scope: architectural closure of DEC-390's 4-layer structure; cross-validation of pending-reservation pattern, ceiling, is_reconstructed posture, and startup-warning composition. Tier 3 reviewer is a fresh Claude.ai conversation with the revised package + S4a close-out artifact.

**Affected artifacts:** Sprint Spec (Escalation Criteria adds mandatory mid-sprint Tier 3 at S4a close-out); Session Breakdown (insert "Tier 3 review session" between S4a and S5a; estimate +1 session for the review itself; total estimate may rise to 11 sessions).

---

### L-R2-1 — Out-of-Scope #20/#21 rejection rationales rephrased — ACCEPT

Out-of-Scope #20 (trades-table reconstruction) and #21 (DEF-209 forward-pull) rejection rationales rephrased from definitional ("definitively impossible") to comparative ("judged not worth the marginal complexity given is_reconstructed posture"). Editorial only. SbC text edit at sprint-close.

### L-R2-2 — DEC-390 Context multi-position attribution note — ACCEPT

DEC-390 Context section adds note: "Reconstruction creates ONE ManagedPosition per symbol from broker-aggregate data, regardless of how many ManagedPosition objects existed pre-restart. Performance accounting attribution to the original signals/strategies is lost on reconstructed positions. This is consistent with the is_reconstructed = True refusal posture and is structurally accepted as a known limitation until Sprint 31.94 D3 lands."

### L-R2-3 — Cumulative diff bound recalibrated — ACCEPT

Cumulative diff bound on `argus/execution/order_manager.py` recalibrated from ~800–1000 LOC to ~1100–1200 LOC. Adding pending-reservation state machine (~100), is_reconstructed handling (~30), broker-verification helper (~80 plus refresh path ~50), AC4.6 startup-warning (~10 plus AC4.7 CLI flag handling ~20), operator-audit logging conditional on H1/H4 (~50), `_reserve_pending_or_fail` atomic method (~20), `_pending_sell_age_seconds` watchdog conditional on case A (~50). Sprint-execution concern, not safety.

---

## Meta-pattern: primitive-semantics assumptions

Round 1 caught the assumption that asyncio's single-threaded event loop serializes concurrent emit-side execution. False — coroutines yield control during `await`, and a second coroutine can run an entire ceiling-check-and-place sequence between yield points.

Round 2 caught the assumption that `broker.get_positions()` returns fresh broker-side state. False — `ib_async` caches positions populated via `positionEvent`, and after a reconnect there is a window where the cache is stale relative to broker state.

Both are about runtime semantics of an underlying primitive. Both are non-obvious. Both, when violated, silently produce the symptom class the fix claims to address. Both are caught only by close inspection.

The pattern is itself a process-evolution finding. Sprint planning's hypothesis-prescription protocol, when relying on a "primitive's semantics" assumption, should require an explicit S-spike that *falsifies* (not merely *measures*) the primitive's assumed behavior under the conditions where the failure mode would manifest.

**Recommended protocol amendment** (RETRO-FOLD candidate per process-evolution lesson F.5 lineage):

> Phase A Step 5 (Hypothesis Prescription) shall include a **Falsifiable Assumption Inventory** subsection listing every primitive-semantics assumption load-bearing on the proposed mechanism, plus the spike or test that falsifies (not merely measures) each assumption.

This is consistent with the existing key learning "Non-bypassable validation is a design posture, not a flag default." The inventory is the *epistemic* analog: the design's correctness depends on certain claims being true; those claims must be proven, not assumed.

For Sprint 31.92 specifically, the inventory covers at minimum:

| # | Primitive-semantics assumption | Falsifying spike / test |
|---|--------------------------------|-------------------------|
| 1 | asyncio event-loop serialization across concurrent emit-side calls | H-R2-1 AST-level guard + mocked-await injection test |
| 2 | `ib_async` position cache is fresh at AC2.5 timeout | C-R2-1 S3b expanded post-reconnect spike + `Broker.refresh_positions()` ABC method + Branch 4 fallback |
| 3 | IBKR `modifyOrder` is deterministic at sub-50ms latency | S1a `modifyOrder` rejection-rate measurement (already in spec; falsifiability via Wilson UB decision rule per M-R2-4) |
| 4 | IBKR locate-rejection error string is stable | S1b substring fingerprint validation across ≥5 symbols × ≥10 trials (already in spec) |
| 5 | `cancel_all_orders(symbol, await_propagation=True)` actually proves all bracket children cancelled before SELL emission | S1a `h1_propagation_converged: bool` (in spec but the falsifiability of `propagation_converged` is weak — flagged for Phase A re-entry to strengthen) |
| 6 | Held-order semantics — IBKR raises locate-rejection exception on hard-to-borrow symbols | S1b case A vs case B differentiation per M-R2-1 |
| 7 | `on_position_closed` event fires on all four ARGUS position-close paths | M-R2-2 regression test |

The inventory itself is a falsification artifact. If a future Round 3 finds an 8th primitive-semantics assumption not in this list, the inventory has failed; if it finds one in the list with an inadequately falsifying spike, the spike has failed. This makes the inventory testable.

---

## Phase A-bounded re-entry scope

This is what the next planning conversation must do.

**Phase A activities** (estimated 1 session):
1. Author the Falsifiable Assumption Inventory section.
2. Validate each Round 2 disposition's fix shape against the inventory.
3. Re-confirm Hypothesis Prescription (no architectural change expected — H2 primary stands; H1-fallback-locate-reject sub-mechanism added; Wilson UB decision rule).
4. Re-confirm session count (currently estimated 10–11 with mid-sprint Tier 3 added).
5. **Roadmap-level question to surface for operator decision**: should Sprint 31.94 D3 be prioritized ahead of Sprint 31.93? NOT a Sprint 31.92 deliverable; flagged for separate Discovery activity.

**Phase B activities** (estimated 1 session):
1. Updated Design Summary reflecting C-R2-1 redesign + Falsifiable Assumption Inventory + H-R2-1/H-R2-5 atomic-method/stop-replacement-exemption refinements + H-R2-2 H1-fallback-locate-reject sub-mechanism.
2. No architectural shape change.

**Phase C activities** (estimated 1 session):
1. Revised Sprint Spec applying all 14 dispositions.
2. Revised SbC.
3. Revised Session Breakdown.
4. Revised Regression Checklist.
5. Revised Doc Update Checklist.
6. Revised Escalation Criteria.
7. Round 3 Adversarial Review Input Package (narrowest possible scope).

**Phase C-1 (Round 3 adversarial review)** (estimated 1 session):
1. Fresh adversarial review on revised package.
2. Bias toward Assumption Mining only.
3. **If Round 3 produces ≥1 Critical**: full Phase A re-entry. The meta-pattern is then unambiguous and the protocol gap requires deeper structural treatment.
4. **If Round 3 is CLEAR or only Mediums/Lows**: proceed to Phase D.

Total estimated planning cost: 4 sessions before Phase D.

---

## Files this disposition produces (now)

- `docs/sprints/sprint-31.92-def204-round-2/round-2-disposition.md` (this file)

## Files deferred to Phase A re-entry

- Updated `sprint-spec.md` with all 14 dispositions applied
- Updated `spec-by-contradiction.md`
- Updated `session-breakdown.md`
- Updated `regression-checklist.md`
- Updated `doc-update-checklist.md`
- Updated `escalation-criteria.md`
- New `falsifiable-assumption-inventory.md` (or as a section in sprint-spec.md)
- New `adversarial-review-input-package-round-3.md`

## Operator confirmation required before Phase A re-entry

Before the next planning conversation begins, operator confirms:

1. Acknowledgment that A14 halt fired and Phase A-bounded re-entry is the chosen path (NOT full Phase A re-discovery; NOT direct-amendment-without-replan).
2. Acknowledgment that Round 3 is required and that another Critical in Round 3 would trigger full Phase A.
3. Optional: decision on the Sprint 31.94 D3 prioritization question (or defer to separate Discovery).
4. Optional: any additional findings from the operator's own review of Round 2 not surfaced in the Round 2 reviewer's report.

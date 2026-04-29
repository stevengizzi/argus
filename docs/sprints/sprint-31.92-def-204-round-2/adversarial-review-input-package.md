# Sprint 31.92 — Adversarial Review Input Package (Round 2)

> **How to use this document.** Open a fresh Claude.ai conversation. Paste, in
> this order: (1) `sprint-spec.md` (revised), (2) `spec-by-contradiction.md`
> (revised), (3) this document. Then issue the opening prompt:
>
>     "I need you to adversarially review this REVISED sprint spec. This is
>     Round 2 — Round 1 produced 3 Critical + 4 High + 3 Medium findings, all
>     dispositioned per revision-rationale.md. Your job is narrower this round:
>     find problems that the revisions INTRODUCED OR FAILED TO FULLY ADDRESS.
>     Try to break the revised design. Find the flaws."
>
> Round 2 scope is **narrower than Round 1** — validate the fixes, not the
> original design. Specifically: (a) did any revision introduce new failure
> modes? (b) did any partial-accept disposition leave residual risk that
> warrants escalation? (c) are the rejected-reviewer-alternatives (SbC items
> 20–23) correctly justified? (d) are the new edge cases (SbC items 1, 5,
> 15–17) structurally airtight?
>
> The reviewer should pursue the six probing angles (Assumption Mining,
> Failure Mode Analysis, Future Regret, Specification Gaps, Integration
> Stress, Simulated Attack — last is N/A). Bias toward Assumption Mining and
> Specification Gaps — these are where Round 1 surfaced the load-bearing
> findings.

---

## Why Round 2 is necessary

Per `protocols/adversarial-review.md` §"Resolution Outcome B": "If changes are minor, they can be applied directly. If changes are structural, re-run Phase B and Phase C of the sprint-planning protocol."

The Sprint 31.92 disposition author judged Round 1's revisions as **substantive but not structural** (session count unchanged at 10; sprint goal unchanged; architecture unchanged in shape — pending reservation is a refinement of the ceiling, not a different mechanism; H2-vs-H1 default reversal is a parameter choice within Path #1, not a different Path). On that basis, revisions were applied directly without a Phase B re-run.

But: the disposition author's judgment is itself subject to adversarial review. Round 2 must answer two structural-vs-substantive questions:

1. **Did C-1's pending-reservation pattern actually close the asyncio yield-gap race, or did it just relocate it?** The reservation pattern increments synchronously before `await`, but state-transition completeness across all 5 enumerated transitions (place / cancel / reject / partial-fill / full-fill) is now load-bearing. Round 2 must probe whether any state transition is missing or incorrectly modeled.

2. **Did C-2's `is_reconstructed` refusal posture actually close the restart-safety hole, or did it just trade it for an operational-degradation hole?** The conservative refusal is structurally correct but creates trapped-capital risk until Sprint 31.94 D3 lands. Round 2 must probe whether the operator daily-flatten infrastructure can sustain the load, and whether the time-bounding (Sprint 31.94 D3) is realistic.

Round 1's bar was "find any flaws in the original design." Round 2's bar is **higher**: "find flaws in the revisions, OR confirm that the revisions actually address Round 1's findings without introducing new problems." A Round 2 verdict of CLEAR is meaningful only if Round 2 was actually rigorous on the post-revision design.

---

## Round 1 disposition table (verbatim from `revision-rationale.md`)

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

Per-finding rationale is in `revision-rationale.md`. Round 2 reviewer should consult that file for the full reasoning behind each disposition (especially the partial-accepts on C-2, H-3, H-4, M-3 where the disposition author chose a different fix shape than the Round 1 reviewer proposed).

---

## Round 2 framing — what specifically to scrutinize

Round 2 questions are organized by **risk class**: Class I covers whether the accept-in-full revisions actually work; Class II covers whether the partial-accept-with-different-fix dispositions are defensible; Class III covers whether new edge cases and out-of-scope items are correctly bounded.

### Class I — Did the ACCEPT-in-full revisions actually work?

#### Q1.1. C-1 pending-reservation completeness — did the fix close the race or relocate it?

The revised AC3.1 enumerates 5 state transitions: place enqueue (synchronous, before await) → cancel/reject (decrement) → partial fill (transfer pending → sold for filled portion; remainder stays pending) → full fill (transfer remainder) → order timeout / DEF-158 retry (cancel original, place fresh).

**Probe:**
- **Are these 5 transitions exhaustive?** What about the case where `place_order` returns a non-success status that's neither full-fill nor reject — e.g., IBKR's "transmit deferred" or "order in pre-submit" states? Does ARGUS handle these via `place_order` exception (so they're caught by the cancel/reject decrement) or via a separate path that wouldn't decrement pending?
- **Is the synchronous-before-await ordering enforceable at code-review time?** A reviewer inspecting a diff at S4a sees `cumulative_pending_sell_shares += requested_qty` somewhere in the function. How does the reviewer verify that the increment happens BEFORE any `await` in the function? Is there a structural pattern (e.g., increment as the first statement after the `_check_sell_ceiling` returns True, before any other code) that the reviewer can grep for?
- **Concurrent partial-fill bookkeeping:** if T1 partial-fills 50/100 and bracket-stop concurrently fills 100/100, does `on_fill` correctly sequence the two fills? The fills arrive on separate broker callbacks; partial-fill's transfer (pending -= 50; sold += 50) and full-fill's transfer (pending -= remaining_50; sold += 50) need to compose. What happens if the bracket-stop's full-fill arrives BEFORE T1's partial-fill (network reordering)?
- **What about the case where T1 + bracket-stop both fill but ARGUS only sees one fill callback** (e.g., due to a transient broker glitch)? `cumulative_pending_sell_shares` would not decrement for the missed callback; eventual reconciliation would catch it, but during the gap, ceiling check at the next standalone-SELL emit site would compute `pending + sold + requested > shares_total` falsely.
- **The `cancel_order` confirmation path** — does ARGUS reliably receive cancel confirmations for orders that were rejected at place-time? If a reject and a cancel-confirmation race, could `cumulative_pending_sell_shares` be double-decremented?

#### Q1.3. C-3 H2-default mechanism — does the revised Hypothesis Prescription actually flow through the impl prompts correctly?

The revised Sprint Spec §"Hypothesis Prescription" reverses defaults: H2 primary → H4 hybrid fallback → H1 last-resort. AC1.5 framing is mechanism-conditional: AMD-2 preserved under H2; mixed under H4; superseded under H1. AC1.6 operator-audit logging is conditional on H1 or H4-with-fallback-active.

**Probe:**
- **Is the S1a impl prompt's halt-or-proceed logic structurally airtight?** S1a's JSON output gates which mechanism the S2a impl prompt implements. What if S1a's measurement falls into an ambiguous zone — e.g., H2 rejection rate measured at exactly 5.0% (the threshold between H2 alone and H4 hybrid)? Is the boundary inclusive or exclusive in the gate logic? Does the implementation prompt template provide explicit boundary handling?
- **Does the AC1.5 mechanism-conditional framing actually compose with the existing AMD-2 regression test?** The Round-1-revised spec says: "Existing AMD-2 regression test (`test_amd2_sell_before_cancel` from Sprint 28.5) continues to pass without modification under H2." But under H4, the test must be parametrized to cover both branches. Under H1, the test is renamed. **Does the impl prompt at S2a correctly handle these three different test-update patterns based on S1a's selection?** Is there risk that an implementer under time pressure picks the wrong branch?
- **The DEC-117 atomic-bracket invariant under H1:** `cancel_all_orders(symbol, await_propagation=True)` cancels the bracket parent and (per IBKR) atomically cancels children. **But does the cancel-and-await actually prove that ALL bracket children were cancelled before SELL emission?** DEC-386 S1c's spike `PATH_1_SAFE` measured this for the OCA-already-filled exception path; has the cancel-and-await-then-SELL sequence been independently validated? S1a is supposed to measure this, but the JSON schema in S1a's spike script has `h1_cancel_all_orders_p95_ms` and `h1_propagation_converged: bool` — is `h1_propagation_converged` actually a strong-enough signal?

#### Q1.4. H-1 ceiling check exclusion at bracket placement — is the bound correct?

Revised AC3.2 explicitly excludes `place_bracket_order` from ceiling check; AC3.1 keeps T1/T2/bracket-stop fills incrementing `cumulative_sold_shares`. SbC §"Edge Cases to Reject" #15 documents the exclusion rationale.

**Probe:**
- **What about non-standard bracket-children placements that might exist in DEC-386 broker-only paths?** DEC-386 S1c added 3 broker-only paths (cancel-then-SELL on `_handle_oca_already_filled`, etc.). Do any of these placements emit SELL orders that look like bracket-children but aren't? If so, do they fall under the standalone-SELL category (and should be ceiling-checked) or are they exempt under the `# OCA-EXEMPT:` mechanism?
- **The `_resubmit_stop_with_retry` path** — when DEC-372 retries a bracket-stop that failed to place, the retry submits a NEW stop order. Is this a bracket-child placement (excluded) or a standalone-SELL emit (ceiling-checked)? The spec lists `_resubmit_stop_with_retry` (including emergency-flatten branch) as a ceiling-checked emit site; but the NORMAL retry path (not emergency-flatten) is also placing a SELL. Is there ambiguity?
- **What if a bracket placement fails midway** — e.g., parent placed, T1 placed, but T2 fails to place? Does the partial bracket get reconciled in a way that creates a `place_order(SELL)` call from `OrderManager` reconciliation logic? If so, does that call go through the ceiling check?

#### Q1.5. H-2 position-keyed suppression dict — is the cross-position safety actually preserved?

Revised AC2.2 / AC2.4 keys the suppression dict by `ManagedPosition.id` (ULID). AC2.6 clears on fill, position close, or timeout.

**Probe:**
- **The `position close` clearing trigger:** when does ARGUS consider a position closed? Is it (a) when broker confirms zero shares for the symbol, (b) when ARGUS-side `_flatten_pending` clears, (c) when `ManagedPosition` is removed from the active-positions dict, OR (d) some other event? Each option has different timing semantics; the suppression dict clearing must match the position-lifecycle definition used elsewhere in the codebase.
- **What happens when a `ManagedPosition` is split or merged** — does ARGUS ever reassign `ManagedPosition.id`? If yes, does the suppression dict entry get correctly transferred? If a position is reconciled-and-replaced (e.g., DEC-385 reconciliation creates a new `ManagedPosition` with a different ULID), does the old suppression dict entry leak?
- **The dict accumulation pattern in long sessions:** if 10 positions on 5 symbols all get locate-rejected at different times during a 6-hour paper session, the dict accumulates 10 entries until each times out (default 18000s = 5hr). At session end (EOD teardown), the dict is cleared. **Does the dict ever grow beyond `len(active_managed_positions)`?** If a position closes but its dict entry doesn't get cleared (e.g., position-close-clearing is missed in some code path), the entry leaks until next EOD.

#### Q1.6. M-1 hard-to-borrow microcap spike scope — is the operator-curated list actually representative?

Revised S1b session breakdown adds operator pre-flight: ≥5 known hard-to-borrow microcap symbols (PCT-class), ≥10 trials per symbol. H6 tightened to require representativeness.

**Probe:**
- **Operator-curation methodology** — what makes a symbol "PCT-class"? The revised Sprint Spec mentions "recent IPOs with high short interest, popular short-interest names from Fintel/iborrowdesk/IBKR's hard-to-borrow list, microcaps in volatile sectors." Is this list specific enough? Could an operator under time pressure curate a list that doesn't trigger locate-rejections (defeating the spike's purpose)?
- **The H6 rules-out branch:** if S1b observes ZERO release events across all trials (held orders all timeout/cancel without filling), the default falls back to 18000s (5hr). But this means the suppression-window default is BLIND to actual release timing. **Is 5hr actually conservative enough?** The PCT trace was 3+ hours; what if the next paper session has a held order that releases at 4hr — within the 5hr window, so suppression is still active, but ARGUS treats it as a phantom-short-pending-alert until the broker-verification fires at 5hr.
- **The suppression dict garbage-collection at 5hr default:** during a typical 6.5-hour ARGUS session (9:30 AM ET to 4:00 PM ET), only ONE suppression cycle can complete per position. If a symbol gets locate-rejected at 10:00 AM, suppression is active until 3:00 PM. ARGUS cannot SELL that position via the standard paths until 3:00 PM. Is that operationally acceptable for paper trading? **Does the cessation-criterion-#5 "5 paper sessions clean" actually exercise this scenario?**
- **The hard floor of 18000s when H6 ruled out:** is this floor empirically derived or just a conservative guess? If S1b shows held orders releasing in 30 minutes consistently, the 5hr default is overly conservative; a position would be unnecessarily suppressed for 4.5 hours. Is there value in measuring released-only spike trials more aggressively to derive a tighter default?

#### Q1.7. M-2 SimulatedBroker validation framing — is the in-process scope actually clear?

Revised AC5.1/AC5.2 explicitly scopes JSON artifacts to "in-process logic correctness via SimulatedBroker fixture." Cessation criterion #5 (5 paper sessions clean) is the production-validation gate.

**Probe:**
- **What does "in-process logic" actually exclude?** AC5.1's revised text lists what SimulatedBroker doesn't model: "IBKR API timing, network packet loss during cancel/amend propagation, IBKR's actual `modifyOrder` response timing, concurrent fill arrival ordering across positions in production." Are there other production-relevant behaviors the SimulatedBroker doesn't model (e.g., margin-call interrupts, broker-side rate limits, order-modification race conditions across multiple TWS sessions)? The framing helps but doesn't exhaustively enumerate what's out.
- **Does the cessation-criterion #5 framing actually differentiate paper-session evidence from production safety?** Paper trading IS production-IBKR (just with paper account), so cessation criterion #5 captures the IBKR-API-interaction layer. But it's still NOT live-trading evidence (different execution venues, different liquidity dynamics). Should there be an EXPLICIT criterion #6 for "live trading minimum size" before DEF-204 is fully RESOLVED?

### Class II — Are the PARTIAL-ACCEPT-with-different-fix dispositions defensible?

#### Q2.1. C-2 `is_reconstructed` refusal posture — is the conservative trade-off actually correct?

Disposition rejected reviewer's options (a) reading trades table on startup (rejected: attribution ambiguity for multi-position-on-symbol scenarios) and (b) persisting counters to SQLite (rejected: pulls DEF-209 forward, scope-violating). Chose `is_reconstructed: bool` flag refusing ALL ARGUS-emitted SELLs on reconstructed positions until Sprint 31.94 D3 lands.

**Probe:**
- **Is the multi-position-on-symbol attribution ambiguity actually a real obstacle?** The trades table presumably has timestamps for each SELL; if reconstruction can identify which position corresponds to which broker-reported share count (by ordering), maybe the attribution IS resolvable. **Did the disposition author actually verify the attribution ambiguity, or did they assume it without testing?** A spike script that attempts trades-table reconstruction on the actual `data/argus.db` schema would falsify or confirm the assumption.
- **The trapped-capital failure mode:** AC3.7 forces operator-manual flatten via `scripts/ibkr_close_all_positions.py`. What if a paper session has 50 reconstructed positions accumulating across a day? Does the operator manual-flatten script handle 50 positions cleanly? RSK-RECONSTRUCTED-POSITION-DEGRADATION is filed at LOW-MEDIUM severity; **is the severity correctly calibrated?** Apr 28 had 27 of 87 ORPHAN-SHORT detections pre-existing at boot from a missed-run of the script. If the script is REQUIRED to run daily AND becomes the only mechanism to close reconstructed positions, the operational failure mode for missed runs is now MORE severe than Apr 28.
- **The Sprint 31.94 D3 time-bounding:** Sprint 31.94 D3 is the boot-time adoption-vs-flatten policy decision. **What's the realistic ETA?** Sprint Abort Condition #7 fires if D3 slips >4 weeks past Sprint 31.92 seal. But Sprint 31.93 (component-ownership) is also queued; if 31.93 takes 3 weeks and 31.94 takes another 3 weeks, the bound is at 6 weeks. Should Sprint 31.94 D3 be PRIORITIZED ahead of 31.93 specifically because Sprint 31.92 inherits this dependency?
- **What if the operator decides to SKIP daily-flatten one day** because they're traveling or sick? Reconstructed positions from that day's session persist into the next session. Does `_startup_flatten_disabled` block the next session entirely (per IMPROMPTU-04), forcing an operator-resolution? Or does the next session boot in a degraded state with persistent reconstructed positions?

#### Q2.2. H-3 broker-verification at suppression timeout — does the defense actually compose with reconnect events?

Disposition rejected reviewer's option (a) IBKRReconnectedEvent consumer (rejected: producer doesn't exist until Sprint 31.94) and option (b) cessation-criterion redefinition (rejected: dilutes the gate). Chose broker-side verification at suppression-timeout via `broker.get_positions()`.

**Probe:**
- **The `get_positions()` call latency budget is ≤200ms p95 per Performance Benchmarks.** Is this measurement validated by a spike, or is it assumed? IBKR's `get_positions` synchronizes broker-side state; if a reconnect has just occurred and `ib_async`'s position cache is stale, the call may need to round-trip to IBKR servers — latency could be much higher.
- **What if `get_positions()` returns stale data?** `ib_async` caches positions; if the cache hasn't refreshed since the suppressed SELL was attempted, `get_positions()` may return the PRE-locate-rejection state (i.e., long position still showing). The broker-verification would classify as "expected long" and suppress the alert. But the actual broker-side state (held order pending) is different. **Is there a mechanism to force a cache refresh before the verification call?**
- **The verification-failure fallback (B-class halt B12 disposition):** if `get_positions()` raises an exception or times out, the spec falls through to the existing DEC-385 `phantom_short_retry_blocked` alert path with `verification_failed: true` metadata. **Is this fallback actually safer than the original Round-1-reviewer-proposed IBKRReconnectedEvent consumer?** A reconnect event would clear the dict deterministically; broker-verification with failure-fallback might produce alerts that the operator can't act on (because the symbol's actual state is unknown).
- **Sprint 31.94's IBKRReconnectedEvent producer landing:** when 31.94 lands, is the existing AC2.5 broker-verification REPLACED by the consumer, or do both coexist? If both coexist, is there a coordination concern (e.g., the consumer clears the dict but the broker-verification then fires on an empty entry)?

#### Q2.3. H-4 startup CRITICAL warning — is the warning actually operationally meaningful?

Disposition rejected reviewer's option (a) validator-restrict to literal 1 (rejected: supersedes DEC-386 design intent). Chose startup CRITICAL warning when `bracket_oca_type != 1`.

**Probe:**
- **Where does the CRITICAL warning emit?** AC4.6 specifies "via the canonical ARGUS logger pipeline" but C11 (in escalation criteria) flags that operator may not see file-only logs. **Is there a stronger operator-visibility mechanism (e.g., emit to ntfy.sh notification channel, OR fail startup with non-zero exit code unless an explicit `--allow-rollback` flag is passed)?** The startup warning is only effective if operator actually reads startup logs.
- **What about during emergency rollback scenarios** — by definition, the operator is making the rollback intentionally. The CRITICAL warning then doesn't add information (operator already knows). It's only effective for ACCIDENTAL rollback (e.g., misconfigured YAML). Is accidental rollback a realistic concern given that the field's default is 1?
- **The Pydantic validator is unchanged.** This means `bracket_oca_type` accepts any int in [0, 1]. If a future config edit accidentally introduces `bracket_oca_type: 2` (e.g., someone trying to set `ocaType=2` per IBKR spec), the validator REJECTS at Pydantic level. **Is the field's range correct, or should it be a Literal[0, 1] for type-safety?** This is a smaller question than the H-4 disposition but worth probing.

#### Q2.4. M-3 Pytest test with JSON side-effect — is the freshness mechanism actually robust?

Disposition rejected reviewer's option (a) restore standalone composite script (rejected: pushes S5b compaction-risk over threshold). Chose Pytest test that writes JSON as side-effect; daily CI updates mtime.

**Probe:**
- **The daily CI workflow** — AC5.3 specifies "daily CI workflow runs the test and the artifact mtime tracks freshness." But B1 + B2 in `doc-update-checklist.md` defer the CI workflow file addition to "operator-manual sprint-close task" because adding it during S5b pushes compaction-risk over threshold. **Is the operator-manual deferral itself a single point of failure?** If the operator forgets to add the CI workflow, the freshness mechanism never activates. The Sprint 31.92 pre-live transition checklist (C9 item 10) requires "≥7 consecutive daily green runs before live transition consideration" — but if the workflow is never added, this gate is never satisfied OR is satisfied vacuously.
- **The Pytest test's side-effect of writing JSON before the assertion** — if the assertion fails, the JSON IS written (recording the failure state) but with values that DON'T satisfy the freshness check (e.g., `phantom_shorts_observed > 0`). Does the freshness check at A-class halt A13 also verify the JSON's CONTENT is in the success state, or just the mtime?
- **What if the daily CI workflow runs but the test is skipped** (e.g., due to a missing fixture, an environment issue, or a markexpr filter)? The mtime updates from the workflow run, but the actual test never executed. Does the artifact correctly reflect skip vs pass?

### Class III — Are the new edge cases and out-of-scope items correctly bounded?

#### Q3.1. SbC §"Edge Cases to Reject" #1 (replaced) — is the asyncio-yield-gap framing actually airtight?

Revised SbC #1: the original Round-1 framing claimed "asyncio prevents this race" — wrong. New framing: race IS real, AC3.1's reservation pattern structurally addresses it.

**Probe:**
- **Is the new framing TOO confident?** The reservation pattern depends on the synchronous-before-await ordering. If a future code refactor adds an `await` BEFORE the increment (e.g., to fetch some metadata for the SELL order), the race re-emerges silently. **Is there a structural guard (e.g., a linter rule, a test, a wrapper context manager) that ensures the ordering invariant?** Code review alone is fragile.
- **The C-1 race test (`test_concurrent_sell_emit_race_blocked_by_pending_reservation`)** — does it exercise the ordering invariant explicitly, or does it just verify the FINAL outcome (second coroutine refused)? A test that verifies outcomes without verifying the mechanism could pass even if the implementation accidentally moved the increment AFTER the await (in which case the race would be present but the test would pass for unrelated reasons).

#### Q3.2. SbC §"Out of Scope" items #20–23 (rejected reviewer alternatives) — are the rejection rationales correct?

#20: rejecting trades-table reconstruction on multi-position attribution ambiguity.
#21: rejecting SQLite persistence as DEF-209 scope creep.
#22: rejecting validator-restrict to literal 1 as DEC-386 design intent.
#23: rejecting Round 1 spec re-review on substantive-not-structural grounds.

**Probe:**
- **#20 (trades-table attribution):** Is the multi-position-on-symbol attribution ambiguity fundamental, or is it solvable with a small schema addition (e.g., add `managed_position_id` foreign key to the trades table)? If solvable with a small change, is the rejection actually correct?
- **#21 (DEF-209 forward-pull):** The disposition author says pulling DEF-209 forward couples 31.92 to a 10+ sprint horizon. **But the actual scope of pulling forward could be narrow** — only `cumulative_pending_sell_shares` and `cumulative_sold_shares` and `is_reconstructed` need persistence. Reading the DEF-209 entry: does DEF-209 actually require ALL the fields, or could a narrow scope satisfy Sprint 31.92's needs?
- **#22 (validator-restrict):** DEC-386 explicitly designed the rollback escape hatch. **But did DEC-386 design the rollback as runtime-flippable OR as a code-level escape requiring a deploy?** If the design intent was "operator deploys a config change AND restarts," then making it runtime-flippable was an unintentional design property, not a deliberate one. Validator-restrict to literal 1 would still allow the rollback path (operator changes the validator AND deploys), it just removes the runtime-flippability.
- **#23 (no Phase B re-run):** The disposition author judged revisions as substantive-not-structural. **What's the formal definition of structural?** If a future Round 2 reveals that Round 1's disposition was wrong, does that count as structural retroactively?

#### Q3.3. SbC §"Edge Cases to Reject" #15 — is bracket placement exclusion correctly bounded?

Revised SbC #15: bracket placement is ceiling-excluded; T1/T2/bracket-stop fills still increment cumulative_sold.

**Probe:**
- See Q1.4 above for the substantive question. Additionally:
- **Is the `place_bracket_order` function the ONLY bracket-placement entry point?** What about bracket re-placements after a partial bracket failure? What about emergency-bracket-replacement during reconnect-recovery (Sprint 31.94 territory)?

#### Q3.4. SbC §"Edge Cases to Reject" #16 — is multi-position-on-symbol restart really uniformly handled?

Revised SbC #16: multi-position-on-symbol restart cases all uniformly refuse via `is_reconstructed = True`.

**Probe:**
- **Is "uniform refusal" actually the right behavior?** What if one of the multi-positions has a confirmed exit that just hadn't been processed in ARGUS's state before restart? Refusing the SELL means the position stays open until operator-manual flatten, even though the broker would happily accept the SELL.
- **What if the pre-restart state had different `shares_total` per ManagedPosition** (sequential entries, different sizes)? The reconstructed state has `shares_total = abs(broker_position.shares)` — i.e., the SUM of all positions (broker reports symbol-level aggregate). Does ARGUS create ONE ManagedPosition per symbol on reconstruct, or does it preserve the multi-position structure? If ONE, then attribution to the original entries is lost. If multi, then `shares_total` is artificially split.

#### Q3.5. SbC §"Edge Cases to Reject" #17 — is the no-aggregate-percentage rule structurally enforceable?

Revised SbC #17: DEC-390 must use structural framing, not aggregate percentage claims. Process-evolution lesson F.5.

**Probe:**
- **The reviewer halts on tokens like "comprehensive," "complete," "fully closed," "covers ~N%."** Is this enforceable by automated regression test (e.g., grep on DEC-390's text in `decision-log.md` post-merge), or only by reviewer discipline?
- **Are there OTHER tokens that could sneak in** — e.g., "substantially closes," "addresses the bulk of," "the majority of"? The lesson F.5 framing focuses on percentage-claims; semantic-equivalence claims could still slip through.
- **Process-evolution lesson F.5's metarepo amendments** are RETRO-FOLD candidates for the next campaign, NOT applied in-line. **Is this deferral itself a process-evolution risk** — Sprint 31.93 or 31.94 might author DEC entries before the metarepo protocols are amended, repeating the pattern?

### Class IV — Cross-cutting structural concerns

#### Q4.1. Cumulative diff bound recalibration

Round-1-revised regression checklist recalibrates `order_manager.py` cumulative diff bound from 600 LOC to ~800–1000 LOC. **Is this realistic given the new scope?** Specifically: pending-reservation state machine (~100 LOC), is_reconstructed handling (~30 LOC), broker-verification helper (~80 LOC), operator-audit logging (~50 LOC if H1/H4), AC4.6 startup warning (~10 LOC). That's ~270 LOC of NEW code on top of Round 1's estimate. **Should the bound be ~1100–1200 LOC?**

#### Q4.2. Mid-sprint Tier 3 review

Round 1 reviewer's Q8 disposition recommended mid-sprint Tier 3 review at S4a close-out (post-ceiling delivery, pre-validation). **Is this in the revised package?** The escalation criteria mention Tier 3 but only as A-class halt triggers, not as a scheduled milestone. **Should mid-sprint Tier 3 be MANDATORY at S4a close-out, given the sprint's scope?** Sprint 31.91 had two Tier 3 reviews; this sprint, larger in scope and with the same architectural-closure ambition, has zero scheduled.

#### Q4.3. Phase D prompt generation timing

The revised Sprint Spec §"Dependencies" says "Adversarial Round 2 verdict received and resolved before Phase D prompt generation begins." **Is there explicit operator-confirmation step between Round 2 verdict and Phase D start?** What if Round 2 produces minor findings (e.g., only Mediums)? Does Phase D start automatically, or does the operator need to dispose first?

#### Q4.4. The 6-of-10 sessions touching `order_manager.py` overlap

Round 1 reviewer's Q8 raised this. The revised regression checklist's "Cross-Session Invariant Risks" section addresses it via cumulative-diff tracking and Tier 2 reviewer mandates. **But is there an architectural concern that Sprint 31.92's structural decisions (pending-reservation, is_reconstructed, suppression dict, AC4.6 warning) are all landing in the SAME 4,421-line file?** The component-ownership refactor (Sprint 31.93) is the structural answer, but it lands AFTER 31.92 — meaning 31.92's diff is committed to a structurally-overloaded file before refactor.

---

## Minimum reviewer actions

Before producing a Round 2 verdict, the reviewer must:

1. **Read `revision-rationale.md` in full** — understand each Round 1 disposition's rationale BEFORE evaluating whether the revision is sufficient.
2. **Read the revised Sprint Spec** — focus on AC1.5 (mechanism-conditional), AC1.6 (operator-audit), AC2.5 (broker-verification three branches), AC3.1 (5 state transitions), AC3.5 (race test), AC3.7 (`is_reconstructed`), AC4.6 (startup warning).
3. **Read the revised SbC** — focus on §"Edge Cases to Reject" items 1, 5, 15–17 (NEW or REPLACED) and §"Out of Scope" items 20–23 (rejecting reviewer alternatives).
4. **Read the revised Session Breakdown** — focus on S4a's score-mitigation chain (option α + γ + δ to land at 13.5) and S5b's deferred-test list. Verify the deferrals don't create test-coverage holes.
5. **Read the revised Regression Checklist** — focus on invariants 19–22 (NEW) and the per-session verification matrix updates.
6. **Read the revised Doc Update Checklist** — focus on C2's DEC-390 entry skeleton (especially the structural-closure framing in Decision and Rationale fields), C8.4–C8.6 (revised + new RSKs), and C10 lesson F.5.

Without reading these, the verdict is uninformed and should not be relied on.

---

## Required output schema

Per `protocols/adversarial-review.md`, the Round 2 verdict is one of:

- **Outcome A (Round 2 CLEAR):** "No critical issues introduced by the revisions; the revisions adequately address Round 1's findings." Document the confirmation + any minor observations in `adversarial-review-round-2-findings.md`. Sprint planner proceeds to Phase D.
- **Outcome B (Round 2 issues found):** "Issues found that require additional spec changes." Summarize the issues + propose specific revisions. If Outcome B with ≥1 Critical finding: A-class halt A14 fires (per revised Escalation Criteria); sprint planner returns to Phase A. **Round 2 Critical findings are MORE serious than Round 1's** — they mean the disposition author got a Round 1 finding's fix wrong, OR a revision introduced a new issue.

Reviewer's findings should be documented in:

- `docs/sprints/sprint-31.92-def204-round-2/adversarial-review-round-2-findings.md` (NEW; created by sprint planner during revision phase OR confirmed empty if Round 2 CLEAR)
- If Round 2 produces revisions: `docs/sprints/sprint-31.92-def204-round-2/revision-rationale-round-2.md` (NEW; one-line rationale per artifact change in Round 2)

---

## Closing note

The success bar for Round 2 is **higher than Round 1's** because Round 1 produced 3 Critical findings AND Sprint 31.91 already empirically failed once. The reviewer is not just looking for bugs in the revisions — they are looking for the SHAPE of bugs that BOTH the original spec AND Round 1's review missed.

Specifically: Round 1 missed the asyncio yield-gap race (caught only on close inspection by the spec author when probing C-1's race scenario). Round 2's bar is to ask: **what's the equivalent of the asyncio yield-gap race for the REVISED design?** What's the assumption the disposition author is making that, on close inspection, will turn out to be wrong?

If Round 2 finds nothing, the sprint proceeds to Phase D. If Round 2 finds something Critical, the sprint returns to Phase A — and the project's confidence in the rigor of its sprint-planning protocol takes a measurable hit. Both outcomes are acceptable; an undiscovered Round 2 Critical that surfaces empirically post-merge is NOT.

Bias toward halting over passing through. The cost of a missed Round 2 Critical is another DEC-386-class empirical falsification.
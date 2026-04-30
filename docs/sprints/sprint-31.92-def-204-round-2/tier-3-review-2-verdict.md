# Sprint 31.92 — Tier 3 Architectural Review #2 Verdict

> **Trigger:** ESCALATE — A-class halt **A1** (S1a spike returned `status: INCONCLUSIVE`).
> **Scope:** Path #1 mechanism-selection rule encoding. NOT cross-layer composition for DEC-391 (that's M-R2-5 mandatory mid-sprint Tier 3 at S4a-ii). NOT Path #2 spike (S1b out of scope here). NOT Sprint 31.94 reconnect-recovery design.
> **Date:** 2026-04-30
> **Reviewer:** Claude.ai (fresh conversation, project context loaded).
> **Verdict artifact landing:** `docs/sprints/sprint-31.92-def-204-round-2/tier-3-review-2-verdict.md`
> **Sessions reviewed:** S1a (anchor commit `c1b4bf2` — script delivered; operator-executed JSON `spike-def204-round2-path1-results.json` 2026-04-30T14:13Z).

---

## Top-of-Verdict Operator Urgency Flag

**`scripts/ibkr_close_all_positions.py` MUST be audited for the side-blind-flatten bug class BEFORE tomorrow's market open.** This is the operator's daily DEF-204 mitigation script. If it shares the same `if p.shares > 0: SELL` pattern observed in `spike_def204_round2_path1.py` L362–379, then on any session that accumulated a short position the daily mitigation has been **doubling the short**, not flattening it. The Sprint 31.91 cessation criterion #5 (5 paper sessions clean post-seal) cannot be met if the daily-flatten tool is itself adversarial.

This is filed as **DEF-216 (URGENT)** below with sprint-gating text. Audit before market open 2026-05-01.

---

## Verdict

**REVISE_PLAN** with bounded scope:

1. The S1a decision-rule encoding is **amended** (Pattern A materialization candidate; deferred to **Pattern B** sprint-close per §Output item 10's "use Pattern B when in doubt" — see DEC-390 below).
2. **Spike v2** is required, partitioned Cat A / Cat B per §Spike v2 Scope Envelope. Cat A fixes are correct regardless of the rule and may land before this verdict propagates. Cat B fixes wait for the rule amendment.
3. **S1b execution is paused** pending Cat A propagation to its harness (DEF-217).
4. **S2a + S2b implementation prompt generation remains halted** until clean spike v2 JSON lands.
5. The sprint plan otherwise proceeds; sessions S2a–S5c remain in their current scope.

This is REVISE_PLAN, not PAUSE_AND_INVESTIGATE: the architectural question is bounded to the spec's decision-rule fragment; the broader 4-layer DEC-391 architecture is unaffected; the sprint can resume with targeted spec amendments and a clean spike v2 re-run.

---

## The Architectural Question's Answer

**The worst-axis Wilson UB across {axis i, axis ii, axis iii, axis iv} as written does NOT reflect the intended H2/H4/H1 selection criterion.**

Verdict shape: **Option 2 from the briefing (rule amended to "production-reachable steady-state axis only"), refined.** The amended rule is:

> **Path #1 mechanism selection binds to `axis_i_concurrent_amends.wilson_upper_bound_pct` only.** Axes (ii) reconnect-window and (iv) joint reconnect+concurrent are RETAINED in the spike harness as **informational characterization** of H2 fail-loud behavior during Gateway disconnect (Sprint 31.94 reconnect-recovery design depends on this characterization). Their UB values are reported in the JSON artifact under `informational_axes_results` but do NOT contribute to the binding `axis_i_wilson_ub` field. **Axis (iii) stale-ID is DELETED entirely** from the spike — the state is unreachable in production code (DEC-117 + DEC-386 invariants prevent re-amendment of cancelled stops), and broker correctly rejecting modifications against cancelled orders is *desired* behavior. Including a desired-behavior signal in any binding metric is structurally degenerate.

**The amended H2/H4/H1 thresholds (axis (i) only):**
- H2 selected if `axis_i_wilson_ub < 5%` AND `h1_propagation_zero_conflict_in_100 == true` AND Mode A propagation deterministic (≥X/Y, X TBD per spike v2 Driver 1 fix) AND `modify_order` p95 ≤ 50ms.
- H4 selected if `5% ≤ axis_i_wilson_ub < 20%` AND `h1_propagation_zero_conflict_in_100 == true`.
- H1 (last-resort) eligible only if `axis_i_wilson_ub ≥ 20%` AND `h1_propagation_zero_conflict_in_100 == true` AND operator written confirmation.
- **HARD GATE preserved (Decision 2):** any 1 conflict in 100 Mode D trials → H1 ineligible regardless of axis (i) UB.

**Why the loose reading is correct, not the strict reading.**

The FAI #3 anchor ("rejection rate stable under adversarial conditions") admits two readings:

| Reading | Interpretation | Outcome |
|---------|----------------|---------|
| Strict | ALL four axes must remain ≤5% UB | H2 disqualified by axis (iii) at 100% UB; H4 forced; H1 contaminated; verdict structurally degenerate |
| Loose | Production-reachable steady-state must remain ≤5% UB | Axis (i) governs; axes (ii)/(iv) characterize fail-loud during reconnect (good signal for Branch 4); axis (iii) deleted |

The strict reading is degenerate because the broker correctly rejecting axis (iii) at 100% is the *correct* engineering behavior. No mechanism — H2, H4, OR H1 — can pass an axis that tests an unreachable production state where the broker is supposed to reject. The strict reading therefore disqualifies all candidate mechanisms by design, which is not a useful selection criterion. The loose reading recovers the engineering question: "does H2 work in steady-state production load, and does it fail loud (not silent) during the separately-addressed reconnect failure mode?"

**Composability with Sprint 31.94.** The amendment is structurally compatible with Sprint 31.94's reconnect-recovery work. Axes (ii) and (iv) remain in the spike harness so Sprint 31.94 design has empirical grounding for what H2's loud-fail surface looks like. The Sprint 31.92 Branch 4 + HALT-ENTRY coupling at C-R2-1↔H-R2-2 is precisely the structural defense that makes H2's reconnect-window failure operationally safe; that defense remains intact under the amendment. RSK-DEC390-31.94-COUPLING (below) tracks the time-bounded contract.

**Composability with H1 last-resort path.** Under the strict reading, H1's path was effectively impossible because the contaminated Mode D HARD GATE could never pass. Under the amended rule, H1 is reachable only if axis (i) UB ≥ 20% (which the empirical data rejects at axis (i) UB = 3.1%). H1 is now what the spec author said it should be: *last-resort fallback*, not the structural default forced by a degenerate metric.

**Composability with the cross-layer composition tests (CL-1 through CL-7).** The amendment touches only the S1a decision rule. CL-3 (L3+L5 cross-falsification) tests the H1 + Branch 4 composition — the test design is unaffected because it parameterizes on `selected_mechanism`, not on rule structure. CL-1, CL-2, CL-4, CL-5, CL-7 are untouched. **CL-6 remains out of scope per Decision 5.**

---

## Spike v2 Scope Envelope (Category A vs Category B)

### Category A — rule-independent, may land before verdict propagates

These fixes are correct regardless of which verdict shape Tier 3 produces. They address spike-side measurement bugs that contaminate every reading. **Operator may land Cat A before this verdict's mid-sync materializes**; doing so is strictly safer than running the spike again under the original rule.

- **Cat A.1 — Mode A propagation measurement bug fix (Driver 1).**
  - Fix shape (pragmatic): replace the 500ms `asyncio.sleep` + `_verify_aux_price(broker, stop_ulid, new_aux)` sample at L460–462 with one of:
    - (a) extend wait to **2.5–3.0s** AND log `t.order.auxPrice` actual values (so the operator can distinguish "cache lag" from "actually didn't propagate") — simplest;
    - (b) call `await broker._ib.reqOpenOrders()` to force a broker-side state pull before sampling — most authoritative;
    - (c) subscribe to the relevant `orderStatus` callback and `await` until the modification status is reflected (wired via `asyncio.Event`) — most precise but requires non-trivial refactor.
  - Recommended: **(a) + (b) combined** — extend wait, then `reqOpenOrders()`, then sample.
  - Acceptance: Mode A `propagation_ok` rate matches the H2 deterministic-acknowledgment claim (≥48/50) under unconstrained Gateway.
  - **DEF-213** filed below.

- **Cat A.2 — Side-aware `_flatten()` in spike harness (Driver 2).**
  - Fix shape (mirrors Sprint 31.91 IMPROMPTU-04 three-branch pattern):
    ```
    for p in positions:
        if p.symbol != symbol:
            continue
        # Use the underlying IBKR Position raw signed quantity, not the
        # absolute-value Position.shares attribute.
        signed_qty = int(p._raw_ib_pos.position) if hasattr(p, "_raw_ib_pos") else None
        if signed_qty is None:
            log.error("UNKNOWN side for %s — skipping cleanup", symbol)
            break
        if signed_qty > 0:        # genuine long
            await broker.place_order(_build_sell(symbol, signed_qty))
        elif signed_qty < 0:      # short — DO NOT SELL
            log.warning("SHORT position detected on %s (qty=%d). Long-only "
                        "policy: spike does NOT cover short. Aborting spike.",
                        symbol, signed_qty)
            raise SpikeShortPositionDetected(symbol, signed_qty)
        # signed_qty == 0 → already flat; no action
        break
    ```
  - **PLUS pre-spike position-sweep refusal-to-start gate** at `main_async()` start, after `broker.connect()`:
    ```
    pre_positions = await broker.get_positions()
    nonzero = [p for p in pre_positions if int(getattr(p, '_raw_ib_pos', p).position or 0) != 0]
    if nonzero:
        log.error("Pre-spike position sweep found nonzero positions: %s. "
                  "Spike refuses to start. Operator must flatten manually "
                  "(WITH SIDE-AWARE TOOLING) before re-running.", nonzero)
        sys.exit(2)
    ```
  - Acceptance: Mode D N=100 produces `zero_conflict_in_100 == true` OR a small bounded number of conflicts none of which are `position_state_inconsistency: shares=N` for unbounded N. The 16/18 QQQ contamination cluster must not recur.
  - **DEF-214** filed below.

- **Cat A.3 — `scripts/ibkr_close_all_positions.py` audit URGENT.**
  - Sister concern to Cat A.2. Operator runs this script daily. The audit checks whether the script uses `if p.shares > 0` (or equivalent absolute-value-side-blind pattern) at any flatten emit site. If yes: file as Cat 5 prior-session bug (per `protocols/in-flight-triage.md`) AND apply the same three-branch fix shape.
  - Acceptance: script visibly inspects signed quantity OR an `OrderSide` field before issuing any SELL/BUY. Refuses to act on UNKNOWN side.
  - **DEF-216 (URGENT)** filed below. Sprint-gating text: must be resolved before market open 2026-05-01.

### Category B — depends on the rule amendment, waits for verdict propagation

These fixes encode the rule amendment. Cat B work is partitioned into "delete," "demote," and "harden" categories.

- **Cat B.1 — DELETE axis (iii) entirely from `spike_def204_round2_path1.py`.**
  - Remove `_axis_stale_id()` (L620–654).
  - Remove the call site from `main_async()`.
  - Remove `stale_id_amends` key from JSON output schema.
  - Acceptance: spike v2 JSON has 3 keys under `adversarial_axes_results`/`informational_axes_results` partition (see Cat B.2).

- **Cat B.2 — DEMOTE axes (ii) and (iv) to informational.**
  - Restructure JSON output:
    ```
    "binding_axis_result": { "concurrent_amends": {…} },
    "informational_axes_results": {
        "reconnect_window_amends": {…},
        "joint_reconnect_concurrent_amends": {…}
    }
    ```
  - The `worst_axis_wilson_ub` field is RENAMED `axis_i_wilson_ub` and reflects only the binding axis.
  - The decision rule (`_apply_decision_rule()`) reads `axis_i_wilson_ub`, not max across axes.
  - Acceptance: JSON schema reflects partition; decision rule binds only on axis (i).

- **Cat B.3 — HARDEN axis (ii)/(iv) instrumentation: fail-loud-on-unprompted-Gateway.**
  - The Work Journal raised the concern that the operator did NOT perform manual disconnect during the previous run, despite the script's stdin-pause pattern. The script's behavior under unprompted-Gateway is implicit and undocumented; axes (ii)/(iv) values reflecting "modify against connected Gateway in some implicit failure mode" rather than "modify against actually-disconnected Gateway" are misleading even as informational signals.
  - Fix shape: before firing axis (ii)/(iv) amends, the script should:
    1. Sample `broker._ib.isConnected()` (or equivalent ib_async API) **immediately before** each amend.
    2. If `isConnected()` returns True throughout the axis, log WARNING `axis_ii_gateway_remained_connected: true` and tag the JSON axis result with `instrumentation_warning: "Gateway remained connected throughout — characterization invalid"`.
    3. Reverse: if `isConnected()` returns False before the operator has typed `RECONNECTED`, log INFO `axis_ii_disconnect_observed: true`.
  - Acceptance: spike v2 fails LOUD when the operator skips the disconnect step. The informational axis values cannot silently mislead Sprint 31.94 design.
  - **DEF-215** filed below.

### Cat A vs Cat B operator decision

The operator may land Cat A.1 + Cat A.2 + Cat A.3 in a single small commit at any time after this verdict reaches them. Cat B requires the rule amendment to propagate via this verdict's mid-sync (DEC-390 commitment + spec amendment in §Hypothesis Prescription). Cat B work blocks on the mid-sync's spec amendment commit; running spike v2 with Cat A applied but Cat B not applied would still produce a "worst-axis" reading that's structurally degenerate. **Cat A + Cat B must both land before spike v2 is run.**

---

## DEC Entries

**DEC-390 (NEW; Pattern B — defer materialization to Sprint 31.92 sprint-close per §Output item 10):**

> **Title:** S1a Decision-Rule Amendment — axis (iii) struck from binding metric; axes (ii)/(iv) demoted to informational; axis (i) binds H2/H4/H1 selection.
> **Status:** RESERVED — Pattern B sprint-close materialization scheduled at Sprint 31.92 D14 doc-sync.
> **Architectural narrative:** Materializes only after spike v2 produces a clean axis-(i)-binding verdict AND S2a/S2b implementation prompts confirm the rule amendment composes with the chosen mechanism. If spike v2 selects H2 (axis (i) UB < 5%), DEC-390 ships as "rule amendment + H2 confirmation." If spike v2 selects H4 (5% ≤ UB < 20%), DEC-390 ships as "rule amendment + H4 hybrid + fail-loud audit logging." If spike v2 selects H1 (UB ≥ 20%, requires operator confirmation), DEC-390 ships as "rule amendment + H1 last-resort + AMD-2-prime."
> **Reason for Pattern B:** the architectural narrative depends on subsequent sessions' outcomes (spike v2 + S2a/S2b composability). Per §Output item 10, "use Pattern B when in doubt."
> **DEC-390 ≠ DEC-391.** DEC-391 is reserved for sprint-close 4-layer DEF-204 architectural closure. DEC-390 is the rule-amendment subset that DEC-391 builds on.
> **Sprint-close gate:** DEC-390 cannot ship if spike v2 returns INCONCLUSIVE again or if Cat B work surfaces additional architectural concerns. In that case, DEC-390 escalates to a third Tier 3 review.

No other DEC entries.

> **Verdict-side numbering provenance:** the verdict was authored 2026-04-30 with verdict-side numbers DEC-389 (rule amendment) and DEC-390 (4-layer closure). Post-verdict cross-check against the live `dec-index.md` revealed DEC-389 was already materialized 2026-04-28 at Sprint 31.915 sprint-close (Config-Driven `evaluation.db` Retention). The collision was resolved at the Tier 3 Review #2 surgery commit 2026-04-30: verdict-side DEC-389 → DEC-390, verdict-side DEC-390 → DEC-391. See `tier-3-review-2-verdict-renumbering-corrections.md` for the canonical mapping.

---

## DEF Entries

All sprint-internal except DEF-216 (operator-tooling, prior-session bug class).

**DEF-213 (NEW; sprint-internal; resolved at spike v2 close-out):**
- **Title:** Mode A propagation measurement bug — 500ms sample window samples client-side cache before broker `orderStatus` callback updates `t.order.auxPrice`.
- **Manifestation:** S1a JSON `mode_a_trials` show 50/50 success at p50=0.98ms p95=1.33ms but 0/50 propagation_ok. The 1ms latency is fire-and-forget queue time, not broker round-trip.
- **Resolution scope:** Cat A.1 fix (extend wait + `reqOpenOrders()`).
- **Sprint home:** Sprint 31.92 (sprint-internal — close at spike v2 acceptance).

**DEF-214 (NEW; sprint-internal; resolved at spike v2 close-out):**
- **Title:** Side-blind `_flatten()` in spike harness — `if p.shares > 0: SELL` on `Position.shares = abs(int(ib_pos.position))` reproduces DEF-204 phantom-short cascade inside the spike's own cleanup.
- **Manifestation:** Mode D N=100 produced 16 contaminated `position_state_inconsistency: shares=2039/2040` conflicts on QQQ, killing the HARD GATE. Cat A.2 fix.
- **Sprint home:** Sprint 31.92 (sprint-internal — close at spike v2 acceptance).
- **Cross-reference:** structurally identical to the bug class addressed by Sprint 31.91 IMPROMPTU-04 (production code) and the production fix shape for Path #1 (Cat A.2's three-branch pattern is the same as the production fix).

**DEF-215 (NEW; sprint-internal; resolved at spike v2 close-out):**
- **Title:** Spike harness axis (ii)/(iv) instrumentation does not fail-loud when operator skips the manual Gateway disconnect step.
- **Manifestation:** the work journal flagged that the operator did not perform manual disconnect/reconnect during S1a's run; the script behavior under unprompted-Gateway is implicit and undocumented. Even as informational axes, this would silently corrupt Sprint 31.94 design grounding.
- **Resolution scope:** Cat B.3 fix (`isConnected()` sampling + JSON `instrumentation_warning` tag).
- **Sprint home:** Sprint 31.92 (sprint-internal — close at spike v2 acceptance).

**DEF-216 (NEW; URGENT, OPERATOR-TOOLING, PRIOR-SESSION BUG CLASS — Cat 5 per `protocols/in-flight-triage.md`):**
- **Title:** `scripts/ibkr_close_all_positions.py` side-blind audit — verify operator's daily DEF-204 mitigation script does not contain `if p.shares > 0: SELL` pattern that would double a short position on any session that accumulated a short.
- **Manifestation:** sister-bug to DEF-214; same author + same week + same surface area. The operator runs this script daily as the cessation criterion #5 mitigation.
- **Sprint-gating text:** **MUST be audited before market open 2026-05-01 (next trading day).** If audit confirms the bug, fix lands as a same-day hotfix outside Sprint 31.92 scope (operator-tooling repository or `scripts/` patch). If audit confirms NO bug, file as `RESOLVED-VERIFIED-NO-FIX` and close.
- **Sprint home:** Sprint 31.92 if audit succeeds (same-day); escalates to a separate Impromptu sprint if a fix is required.
- **Cross-reference:** the operator daily-flatten cessation criterion #5 (CLAUDE.md / project-knowledge.md) cannot be considered satisfied if the daily-flatten tool is itself adversarial.

**DEF-217 (NEW; sprint-internal; resolved at S1b spike acceptance):**
- **Title:** S1b spike (`scripts/spike_def204_round2_path2.py` at commit `becc28e`) likely contains the same side-blind `_flatten()` bug class as DEF-214; spike has not been operator-executed.
- **Resolution scope:** apply Cat A.1 (if Mode A or equivalent latency check is present) + Cat A.2 (side-aware `_flatten` + pre-spike sweep) before any operator execution. The S1b context (hard-to-borrow microcaps where locate-rejection retry storms specifically produce unintended shorts) makes the bug's blast radius higher than S1a.
- **Sprint home:** Sprint 31.92 (sprint-internal — close at S1b acceptance).
- **Cross-reference:** Work Journal halt analysis explicit recommendation; operator clientId=2 budget preserved by current commit.

**DEF-218 (NEW; CROSS-SPRINT; sprint-gating Sprint 31.94):**
- **Title:** Sprint 31.94 reconnect-recovery design depends on H2 fail-loud characterization from spike v2 axes (ii) and (iv).
- **Sprint-gating text:** Sprint 31.94's D-tasks (DEF-194/195/196 reconnect-recovery surfaces) consume `informational_axes_results.reconnect_window_amends` and `informational_axes_results.joint_reconnect_concurrent_amends` from the spike v2 JSON artifact. If spike v2 does not produce these informational results (e.g., axes are deleted under a stricter Cat B interpretation), Sprint 31.94 must re-run a reconnect-only spike before its D-tasks can be designed.
- **Sprint home:** Sprint 31.94 (carry-forward; lands in CLAUDE.md DEF table at this verdict's mid-sync per §Output item 3).

> **Verdict-side DEF numbering provenance:** the verdict was authored 2026-04-30 with verdict-side numbers DEF-213 through DEF-218. Post-verdict cross-check against the live CLAUDE.md DEF table revealed all six numbers were already assigned to Sprint 31.91 follow-ups (highest existing: DEF-235). The renumbering was applied at the Tier 3 Review #2 surgery commit 2026-04-30: DEF-213 → DEF-236, DEF-214 → DEF-237, DEF-215 → DEF-238, DEF-216 → DEF-239, DEF-217 → DEF-240, DEF-218 → DEF-241. See `tier-3-review-2-verdict-renumbering-corrections.md` for the canonical mapping.

---

## RSK Entries

**RSK-DEC390-31.94-COUPLING (NEW; time-bounded contract):**
- **Statement:** DEC-390's amended rule presumes that H2 fails LOUD (returns rejected status, observable as `axis_i_wilson_ub` in steady-state vs `informational_axes_results` in reconnect-window) during Gateway disconnect. Sprint 31.94 reconnect-recovery work may modify how `IBKRBroker.modify_order` surfaces during a reconnect — for example, queueing pending modifications and replaying them post-reconnect with success status. If such a queue-and-replay design lands in Sprint 31.94, the H2 mechanism's protection against silent over-flatten during reconnect must be re-validated, because H2 may no longer fail-loud during reconnect under the new implementation.
- **Time-bounded gating:** revisit at Sprint 31.94 design phase (Phase B). Sprint 31.94's Phase B DEC must explicitly cross-check against DEC-390. If queue-and-replay is the chosen design, file a follow-up DEF here and revisit DEC-390.
- **Cross-reference:** DEC-385 (side-aware reconciliation) + DEC-386 (OCA-group threading) both depend on H2 failing loud during reconnect to route via Branch 4 / HALT-ENTRY.

**RSK-MODE-D-CONTAMINATION-RECURRENCE (NEW; gate-coupling):**
- **Statement:** Even with Cat A.2 + pre-spike position-sweep gate, paper IBKR may retain residual positions across runs in ways the spike harness cannot detect (e.g., aggregated positions across `strategy_id` rows, pending-fill states the broker has not yet confirmed). If spike v2 N=100 Mode D again produces `zero_conflict_in_100 == false` driven by `position_state_inconsistency` conflicts, H1 cannot be either qualified or disqualified, blocking S2a/S2b prompt generation regardless of axis (i) UB.
- **Mitigation:** spike v2 should LOG every Mode D `position_state_inconsistency` signature with full broker state diagnostic (full `get_positions()` snapshot before AND after each conflicting trial). This permits the operator to distinguish "spike-side leak" from "real H1 cancel-await race."
- **Time-bounded gating:** revisit at spike v2 close-out. If recurrence observed, escalate to a third Tier 3 review.

**RSK-VERDICT-VS-FAI-3-COMPATIBILITY (NEW; spec-encoding):**
- **Statement:** DEC-390's amended rule contradicts the strict reading of FAI #3 ("rejection rate stable under adversarial conditions"). The verdict resolves the ambiguity in favor of the loose reading. Future reviewers (Round 3 adversarial review, M-R2-5 mid-sprint Tier 3, sprint-close adversarial review) should not re-litigate this ambiguity unless new evidence falsifies the loose reading's premise that axes (ii)/(iii)/(iv) test failure modes outside production reach or are addressed by separate sprints.
- **Time-bounded gating:** revisit if spike v2's axis (i) result is itself ambiguous (e.g., 4.5%–5.5% UB straddling the H2/H4 threshold). In that case, the loose reading's robustness becomes a gating question.

---

## Documentation Reconciliation

The verdict's disposition triggers a mid-sprint doc-sync per `protocols/mid-sprint-doc-sync.md` (workflow-version 1.0.0). The mid-sync produces a `tier-3-review-2-doc-sync-manifest.md` artifact in the sprint folder enumerating files touched + sprint-close transitions owed.

**Files touched at this mid-sync (Pattern A — materializes at this verdict's mid-sync):**
1. `docs/sprints/sprint-31.92-def-204-round-2/sprint-spec.md` — § Hypothesis Prescription rule encoding (L853–866) updated with axis (i)-binding + axes (ii)/(iv) informational + axis (iii) deleted. § Falsifiable Assumption Inventory FAI #3 (L804) updated to reflect loose reading. § Out-of-Scope item 27 added: "Worst-axis Wilson UB across all four axes — superseded by DEC-390; axis (iii) deleted; axes (ii)/(iv) informational."
2. `docs/sprints/sprint-31.92-def-204-round-2/spec-by-contradiction.md` — Edge Case 2 (L341–350) reference to "Decision 1" updated to point to DEC-390 rule.
3. `docs/sprints/sprint-31.92-def-204-round-2/falsifiable-assumption-inventory.md` — FAI #3 amended.
4. `docs/sprints/sprint-31.92-def-204-round-2/escalation-criteria.md` — A-class halt A1 amended: "spike returned INCONCLUSIVE under DEC-390 amended rule" (the new threshold).
5. `CLAUDE.md` § DEF table — DEF-213, DEF-214, DEF-215, DEF-216, DEF-217, DEF-218 added.
6. `CLAUDE.md` § RSK table — RSK-DEC390-31.94-COUPLING, RSK-MODE-D-CONTAMINATION-RECURRENCE, RSK-VERDICT-VS-FAI-3-COMPATIBILITY added.
7. `docs/risk-register.md` — three new RSKs added with full prose.
8. `scripts/spike_def204_round2_path1.py` — Cat A.1, A.2, B.1, B.2, B.3 applied. New commit; old commit `c1b4bf2` preserved as the contaminated reference.

**Files touched at sprint-close (Pattern B — materializes at Sprint 31.92 D14 doc-sync):**
9. `docs/decision-log.md` — DEC-390 full entry materialized; DEC-391 references DEC-390.
10. `docs/dec-index.md` — DEC-390 + DEC-391 added.
11. `docs/project-knowledge.md` — most-cited foundational decisions list amended; sprint-history table updated.

**Files NOT touched at this mid-sync:**
- `docs/architecture.md` — no architectural change at the production-code surface (the rule amendment is a spec-side amendment; production code unchanged).
- `docs/pre-live-transition-checklist.md` — no pre-live config change.
- `docs/process-evolution.md` — no new process lesson here that isn't already present (process-evolution lesson F.5 on percentage-claim discipline is intact).

---

## Cross-Sprint Implications

1. **Sprint 31.94 reconnect-recovery design.** Inherits the informational axes (ii)/(iv) characterization from spike v2. RSK-DEC390-31.94-COUPLING is the time-bounded contract. DEF-218 lands in CLAUDE.md DEF table at this mid-sync.

2. **Sprint 31.91 cessation criterion #5.** Cannot be considered satisfied if DEF-216 audit confirms the side-blind bug in `scripts/ibkr_close_all_positions.py`. The operator daily-flatten mitigation may have been adversarial during any session that accumulated a short. If DEF-216 fix lands, criterion #5's clock should restart from the fix date.

3. **Sprint 31.93 component-ownership refactor.** Touches `argus/execution/order_manager.py` heavily. The Cat A.2 three-branch pattern (signed-quantity inspection rather than `Position.shares > 0`) is the same pattern that should apply to any production-code site that flatten-emits SELLs. Sprint 31.93 should explicitly enumerate flatten-emit callsites and verify three-branch coverage. (DEC-385 already established this for OrderManager; Sprint 31.93's component-ownership work should generalize.)

4. **Sprint 30 short-selling work.** When ARGUS eventually supports short positions (post-revenue), the three-branch pattern's "SELL-side → BUY-to-cover or log+skip" branch becomes "SELL-side → BUY-to-cover with short-position-aware accounting." The Sprint 31.92 fix shape is forward-compatible.

5. **Recurring pattern: bug propagates from production into spike harnesses.** Sprint 31.91 IMPROMPTU-04 fixed the side-blind flatten in production. Sprint 31.92's S1a spike — written the same week, by the same implementer pattern, against the same surface area — reproduced the same bug. This is *evidence about the bug class itself*, not just one mistake. The recommendation is to add a static-analysis regression to the project: any function or method whose name contains `flatten` and whose body contains `place_order(...sell...)` or equivalent must be reviewed against the three-branch pattern. (Filed as a workflow protocol gap below; not a new DEF.)

---

## Workflow Protocol Gaps Surfaced

1. **Spike-harness review depth.** The Tier 2 review of S1a was deferred because the JSON artifact didn't yet exist. But the spike *script* (998 LOC) was reviewable, and a Tier 2 review of the script — not the JSON — would have caught DEF-214 before operator execution wasted the spike run. **Recommendation:** when a session's deliverable is a spike harness script whose execution requires operator orchestration, the Tier 2 review of the *script* should not be deferred to JSON-existence; it should run on the script alone and explicitly cover safety-load-bearing patterns (side-aware flatten, pre-execution position-sweep gates, fail-loud-on-instrumentation-skip). File this as a candidate amendment to `protocols/adversarial-review.md` or `protocols/in-flight-triage.md`. Not in scope to amend here; surfaced for the next workflow-evolution review.

2. **Mid-sprint Tier 3 mandatory triggers.** The Tier 3 protocol's own origin comment (`protocols/tier-3-review.md` §Mandatory Triggers, comment block at L79–88) was authored *because* Sprint 31.92 originally lacked a mid-sprint Tier 3. This ESCALATE-triggered Tier 3 confirms the value of the mandatory-trigger framework — a mid-sprint Tier 3 at the natural S1a milestone (after spike script delivery, before operator execution) would have caught DEF-214 earlier. **Recommendation:** consider adding a 7th mandatory trigger: "Spike harness involves operator-orchestrated safety-load-bearing patterns (side-aware flatten, pre-execution gates)" → mandatory mid-sprint Tier 3 at script-delivery milestone. Not in scope to amend here.

3. **Cross-spike bug-class propagation.** The Work Journal correctly noted that S1b likely shares DEF-214's bug class. **Recommendation:** when a sprint contains parallel spike sessions (S1a + S1b in this sprint), the close-out of either session should include an explicit "sister-spike audit" item: enumerate code patterns from this spike that could be present in the sister-spike, and flag for review before sister-spike execution. Not in scope to amend here.

---

## Inherited Follow-ups by Sprint

| Sprint | Item | Source DEF/RSK | Action |
|--------|------|----------------|--------|
| 31.92 (current) | Cat A.1 + A.2 + B.1 + B.2 + B.3 spike v2 fix landing | DEF-213/214/215 | Operator-driven; commit before spike v2 re-run |
| 31.92 (current) | S1b sister-spike Cat A application | DEF-217 | Apply before S1b operator execution |
| 31.92 (current) | DEC-390 sprint-close materialization | DEC-390 (Pattern B) | Sprint 31.92 D14 doc-sync |
| 31.92 (current) | Spike v2 close-out (Tier 2 + Cat A acceptance) | DEF-213/214/215 | Operator + @reviewer subagent |
| **2026-05-01** | DEF-216 `scripts/ibkr_close_all_positions.py` audit | DEF-216 (URGENT) | **BEFORE market open 2026-05-01** |
| 31.92 (current) | If spike v2 returns INCONCLUSIVE again: third Tier 3 review | RSK-MODE-D-CONTAMINATION-RECURRENCE | Operator-arranged |
| 31.94 | Reconnect-recovery design Phase B cross-check vs DEC-390 | RSK-DEC390-31.94-COUPLING + DEF-218 | Sprint 31.94 sprint planning |
| 31.93 | Component-ownership refactor enumerate flatten-emit callsites + three-branch coverage | (cross-reference to DEC-385) | Sprint 31.93 sprint planning |

---

## Summary

The S1a spike returned INCONCLUSIVE for three reasons, two of which (Drivers 1 and 2) are spike-side measurement bugs independent of the rule, and one of which (Driver 3) is a spec-encoding flaw in the worst-axis Wilson UB rule. This verdict:

- Confirms Drivers 1 and 2 as Cat A fixes (rule-independent).
- Settles the architectural question in favor of the loose reading: axis (i) binds H2/H4/H1 selection; axes (ii) and (iv) are informational (inputs to Sprint 31.94 design); axis (iii) is deleted entirely.
- Files DEC-390 (Pattern B sprint-close materialization) as the rule amendment.
- Files DEF-213 through DEF-218 capturing all spike-side bugs + the operator-tooling URGENT concern + the cross-spike sister-bug propagation + the Sprint 31.94 carry-forward.
- Files three RSKs covering the 31.94 coupling, the Mode D recurrence risk, and the FAI #3 compatibility caveat.
- Triggers a mid-sprint doc-sync per `protocols/mid-sprint-doc-sync.md`. Cat A fixes may land at the operator's discretion before the mid-sync; Cat B fixes wait for the spec amendment to commit.
- **Operator urgency: DEF-216 audit MUST run before market open 2026-05-01.** The Sprint 31.91 cessation criterion #5 cannot be satisfied with an unreviewed daily-flatten tool that may share DEF-214's bug class.

PROCEED-or-INCONCLUSIVE on spike v2 will be evaluable once Cat A + Cat B are applied. S2a + S2b implementation prompt generation remains halted until clean spike v2 JSON lands AND DEC-390's amended rule is encoded in the spec.

---

*End of Sprint 31.92 Tier 3 Architectural Review #2 verdict.*

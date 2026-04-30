# Sprint 31.92 — Tier 3 Architectural Review #3 Verdict

> **Trigger:** DEC-390 sprint-close gate fired per `tier-3-review-2-verdict.md` § "Sprint-close gate" — *"DEC-390 cannot ship if spike v2 returns INCONCLUSIVE again or if Cat B work surfaces additional architectural concerns."* **Both gate triggers fired** during operator-execution of spike v2 attempt 1 (2026-04-30 afternoon): (1) `status: INCONCLUSIVE` returned in crash-recovery JSON; (2) Cat B work surfaced an architectural concern (DEC-386 OCA-immutability eliminates H2/H4 categorically) beyond the framing of DEC-390's amended rule.
> **Scope:** Path #1 mechanism-replacement post-empirical-falsification of H2/H4. NOT cross-layer composition for DEC-391 (still M-R2-5 mandatory mid-sprint Tier 3 territory). NOT Path #2 (S1b out of scope). NOT Sprint 31.94 reconnect-recovery design (cross-sprint surface only).
> **Date:** 2026-04-30
> **Reviewer:** Claude.ai (fresh conversation, project context loaded).
> **Verdict artifact landing:** `docs/sprints/sprint-31.92-def-204-round-2/tier-3-review-3-verdict.md`
> **Sessions reviewed:** Unit 5 (anchor commit `b4e1a9a` — close-out + DEF-242/243 wrap-up; immediate predecessor `85eb511` Tier 2 CONCERN-1 docstring fix; spike-v2 attempt 1 operator-executed 2026-04-30T18:00–18:05Z, crash-recovery JSON `spike-v2-attempt-1-results.json`).

---

## Verdict

**REVISE_PLAN — Verdict shape 2 from briefing (PROCEED with Mechanism A selected pending a narrow follow-on spike).**

1. **H2 (`modify_order` PRIMARY DEFAULT) and H4 (hybrid amend) are structurally eliminated** by IBKR's broker-side categorical rejection of `modify_order` against any OCA group member. The empirical signal from spike v2 attempt 1 is overwhelming and load-bearing; the inference is CONFIRMED.
2. **Mechanism A — H1 cancel-and-resubmit-fresh-stop** — is the selected mechanism, conditional on a narrow follow-on spike validating its Mode-D-equivalent hard gate.
3. **DEC-390 amendment** (Pattern B sprint-close materialization, retained) is restructured: the rule degenerates from threshold-tiered H2/H4/H1 selection to a binary gate on Mechanism A's empirical viability.
4. **DEC-386 (OCA-Group Threading) is RETAINED without modification.** The downstream `modify_order` incompatibility is a load-bearing architectural constraint — not a defect — propagated forward via DEF-244 and RSK-DEC386-MODIFY-INCOMPATIBILITY.
5. **Sprint 31.92's 12-session structure mostly survives.** Session-resumption matrix below: 2 sessions amended (S2a, S5c CL-3); 1 session elevated in priority (S4b DEF-212 rider); **1 narrow follow-on spike session inserted** (Unit 6 — Mode-D-equivalent only); other sessions unaffected. M-R2-5 mid-sprint Tier 3 fires as scheduled at S4a-ii close-out, scope extended.

This is REVISE_PLAN, not PAUSE_AND_INVESTIGATE: Question 1's empirical answer is unambiguous; Mechanism A is architecturally clean; the remaining empirical question (Mode-D-equivalent against H1) is bounded and addressable by a narrow spike. This is also not a structural sprint amendment (verdict shapes 3 or 4) because the 12-session SbC framework is fundamentally sound — the amendment is mechanism-level, not session-structure-level.

---

## Question 1 Answer — OCA-Categorical-Rejection Inference: CONFIRMED

The Unit 5 close-out's inference that IBKR's broker policy is **categorical rejection** of `modify_order` against any OCA group member is confirmed. The empirical signal is overwhelming and structurally load-bearing for the rest of this verdict.

### Evidence

The operator log (`spike-v2-attempt-1-operator-log.txt`, 966 lines) contains:
- **211 occurrences** of the string `"OCA group revision is not allowed"` (counting [ERROR] + [WARNING] line pairs);
- **105 distinct error 10326 events** (each producing an [ERROR] + [WARNING] pair, ~22% of all log lines);
- **100% async-cancel rate** across Mode A (50 trials), axis (i) `concurrent_amends` (~90 amends across 30 trials × 3 positions), and axis (ii) `reconnect_window_amends` pre-disconnect (~30 amends);
- **Multiple symbols** (SPY, QQQ, IWM, XLF) and multiple bracket placements within the same run, all exhibiting identical behavior;
- **Mechanically consistent timing**: synchronous `modify_order` returns "accepted" → async error 10326 + cancel arrives via `errorEvent` callback within 1–6 ms.

### Refutation alternates considered and rejected

The briefing explicitly invited refutation if the evidence supported it. I considered three alternate readings:

1. **Stale-OCA-state contamination.** Hypothesis: error 10326 fires only because yesterday's positions left stale OCA groups that interact badly with today's amends. **REJECTED** by the log: error 10326 fires on FRESH bracket placements (e.g., bracket `01KQFRN4ZX1PPTPZF2V17VBGEV` placed at line 24, modified at line 32, error at line 37, cancelled at line 39 — all within the same 13-second window inside the same run). Stale state cannot explain the observation.

2. **Modified-order-already-cancelled.** Hypothesis: the broker correctly rejects amends against orders cancelled by prior events. **REJECTED**: at line 32, stop ULID `01KQFRN4ZYF8QGZSWZ7GPQ7JQ2` was modified; the cancellation at line 39 happened AFTER the error at line 37. The order was live at modify time; broker accepted synchronously, then rejected and cancelled.

3. **Specific `ocaType=1` weak-mode behavior vs `ocaType=0`.** DEC-386 ships `ocaType=1` per the Phase A spike `PATH_1_SAFE` validation (2026-04-25, valid ≤30 days). Could `ocaType=2` or some weaker variant exhibit different behavior? Possibly, but irrelevant — `ocaType=1` is what production ships, and that is what the empirical evidence binds. Rolling back to `ocaType=0` would defeat DEC-386's atomic-cancellation property and re-open ~98% of DEF-204's blast radius (per IMPROMPTU-11 diagnostic). The constraint is operationally fixed at `ocaType=1`.

### Mechanism cause confirmed

DEC-386 (Sprint 31.91 S2; commit `bf7b869`) shipped explicit `ocaGroup = f"oca_{parent_ulid}"` + `ocaType=1` threading on bracket children (stop, T1, T2). IBKR's broker policy categorically refuses modification of any order that is a member of an active OCA group. The broker's API contract returns "accepted" at the synchronous call boundary, then emits Error 10326 ("OCA group revision is not allowed") via the asynchronous `errorEvent` callback within milliseconds, followed by an order cancellation event.

This is **broker-side policy, not implementation defect, not stress-condition failure**. No amount of harness improvement, retry logic, or timing adjustment will recover `modify_order` against an OCA member.

### Note on minor evidentiary discrepancy (does not affect verdict)

The Unit 5 close-out reports "~170 amends, 100% async-cancel rate." Direct log inspection finds 105 distinct error events. The discrepancy reflects (a) some retries against already-cancelled `reqId`s firing additional error 10326 events without corresponding new modify_order calls, and (b) modest counting differences between "amend attempts" and "broker error responses." The 100% rate claim is robust regardless of the exact denominator: every modify_order against a bracket child observed in the log produced an error 10326 within 6 ms. Sample size dwarfs any threshold relevant to the architectural question.

---

## Question 2 Answer — Mechanism Replacement: Mechanism A (H1 cancel-and-resubmit-fresh-stop)

### Candidates evaluated

| Mechanism | Verdict | Rationale |
|-----------|---------|-----------|
| **A** — Cancel bracket-grouped stop, place fresh stop OUTSIDE the OCA bond | **SELECTED, pending follow-on spike** | Smallest blast radius. Compatible with DEC-385/DEC-386. Aligns with existing DEC-390 H1 last-resort design (now promoted to default). Mode-D-equivalent unstress-tested at the broker, but the test is bounded and the spike scope is small. |
| **B** — Cancel entire bracket, submit fresh bracket | REJECTED | Strictly larger surface area than A for the same outcome. Larger unprotected window (must wait for cancel-propagation AND new bracket placement). Stronger interaction with DEC-385 mid-flight reconciliation. No advantage over A. |
| **C** — Temporarily remove from OCA, modify, restore | REJECTED on architectural grounds | Empirically uncharacterized but most likely eliminated by the same broker-policy class that blocks `modify_order` against auxPrice (OCA membership is overwhelmingly likely to be immutable post-creation under the same enforcement regime — and even if it works, the "removed-from-OCA" window introduces a NEW unprotected window during which a concurrent fill of an OCA sibling can fire without atomic cancellation). Strictly worse than A. |
| **D** — Surface a fourth | NONE FOUND | The architectural solution space for "update bracket stop price safely under DEC-386 OCA threading" reduces to: in-place modification (eliminated), cancel-and-replace (A/B variants), OCA-membership manipulation (C). I do not see a viable additional candidate. The reviewer is empowered to surface alternates, but the briefing also notes "the verdict shouldn't reach for novelty for its own sake" and I respect that framing. |

### Mechanism A in detail

Pattern: when the trail-stop / escalation / emergency-flatten path needs to update the bracket stop's price, ARGUS:
1. Cancels the bracket-grouped stop order (which, under DEC-386 `ocaType=1`, atomically cancels ALL OCA siblings — entry, stop, target legs);
2. Awaits cancel-propagation broker-side (per AMD-2-prime contract, ≤ 2 s `cancel_propagation_timeout` — DEC-386 already established this primitive via `cancel_all_orders(symbol, await_propagation=True)`);
3. Places a fresh stop order OUTSIDE the OCA bond (stand-alone stop; no `ocaGroup` set; thread `ManagedPosition.oca_group_id = None` from this point forward, OR thread a NEW `oca_group_id` if the design wants to bind the fresh stop into a new single-member OCA group for some reason — the simpler choice is `None`);
4. Updates `ManagedPosition` accounting to reflect the new stop ULID and the now-detached-from-bracket state.

### Critical structural property

Mechanism A's correctness depends on the **unprotected window** between step 2 (cancel propagated) and step 3 (fresh stop confirmed) being operationally safe. AMD-2-prime bounds this window by `cancel_propagation_timeout ≤ 2 s` plus the fresh stop placement latency (typically 50–200 ms). Total bounded unprotected window: ~2.2 s.

The empirical question this spike must answer is: **does any conflicting fill or event occur within that window across N=100 trials under stressed conditions?** This is the Mode-D-equivalent hard gate, adapted from DEC-390's original "cancel-then-immediate-SELL" framing.

### Threshold values for DEC-390 amendment

The original threshold framing (`axis_i_wilson_ub < 5%` H2; `5% ≤ ... < 20%` H4; `≥ 20%` H1) is now meaningless — H2 and H4 are eliminated; only Mechanism A is viable. The amended rule structure:

> **Mechanism A is selected if and only if** all four conditions hold across the Unit 6 follow-on spike (N=100 trials):
> 1. `mechanism_a_zero_conflict_in_100 == true` (zero `position_state_inconsistency` or unintended-fill events);
> 2. `cancel_propagation_p50_ms ≤ 1000`;
> 3. `cancel_propagation_p95_ms ≤ 2000`;
> 4. `fresh_stop_placement_p95_ms ≤ 200`.
>
> **HARD GATE:** any 1 conflict in 100 → Mechanism A is NOT eligible; sprint halts; escalate to Tier 3 Review #4 (no viable mechanism remains in the H-class space; operator faces architectural decision: roll back DEC-386 to `ocaType=0` losing OCA atomic cancellation, OR fundamentally rethink the dynamic-stop-price pattern, OR defer DEF-204 Round 2 closure to a later sprint pending broker-side IBKR API evolution).

The Tier 3 Review #2 rule amendment (axis (i) binds; axes (ii)/(iv) informational; axis (iii) deleted) is **structurally moot** for Mechanism A selection — the threshold-tiered selection has been replaced by a binary gate. However, the amendment's *spirit* (loose-reading of FAI #3, production-reachable steady-state binds, broker-correct rejections do not contribute) is preserved and is now embodied in Mechanism A's empirical gate design.

### Follow-on spike scope (Unit 6 / "S1a-mode-d-followon")

Bounded scope, narrower than spike v2 attempt 1:
- **N=100 trials** of Mode-D-equivalent: cancel bracket-grouped stop → ≤ 10 ms gap → place fresh outside-OCA stop → measure unprotected-window duration and any conflicting events.
- **Single fixture**: paper IBKR, fresh OCA-grouped brackets created by spike itself (no operator orchestration; no manual disconnect; no joint conditions).
- **Pre-spike position-sweep refusal-to-start gate** (DEF-237's Cat A.2 fix shape) preserved.
- **DEF-243 fixes landed first**: async error capture via `errorEvent` listener; `logging.FileHandler`; `isConnected()` precondition gate (this last is unused in Unit 6 since no axis (iv) — but the fix is general and lands together).
- **No axes (i)/(ii)/(iii)/(iv)** — those constructs measured H2/H4's modify_order behavior; they are inapplicable to Mechanism A.
- **JSON output schema**: drop `axis_i_wilson_ub`, `informational_axes_results`, `worst_axis_wilson_ub` fields (no longer relevant). Add `mechanism_a_zero_conflict_in_100`, `cancel_propagation_p{50,95}_ms`, `fresh_stop_placement_p95_ms`, `unprotected_window_observations[]`.
- **Acceptance**: clean Mechanism A JSON with all four threshold conditions met → S2a impl-prompt generation proceeds; HARD GATE failure → escalate to Tier 3 Review #4.

Estimated effort: 1 implementer session (~3–5 hours) + 1 operator-execution session + 1 close-out review. Smaller than spike v2 attempt 1 by approximately 60–70%.

---

## Question 3 Answer — DEC-386 Disposition: RETAINED; cross-sprint constraint propagated forward

DEC-386 (Sprint 31.91 OCA-Group Threading + Broker-Only Safety) is **NOT relitigated** and **NOT modified**. The OCA threading remains the architectural defense whose retention is non-negotiable: it closed ~98% of DEF-204's mechanism per IMPROMPTU-11 diagnostic; rolling it back would re-open 44 symbols / 14,249 unintended short shares of blast radius (Apr 24 alone). The asymmetric-risk-aware default applies: bounded "cannot use modify_order" cost is preferable to unbounded "phantom-short cascade" cost.

### Was DEC-386 the right call given this side effect?

**Yes, with full retention.** The side effect (`modify_order` blocked against OCA members) is bounded and absorbable by Mechanism A. The cost of Mechanism A vs H2 is: every trail-stop update fires a cancel-and-replace cycle instead of a single modify, adding ~200–2200 ms of unprotected-window time per update and ~2× the broker call volume. This is operationally acceptable for ARGUS's strategy populations (trail-stop updates are infrequent — typically tens per session, not thousands). The OCA threading's safety property (atomic cancellation eliminating multi-leg fill races) dominates the modify-cost in the safety/cost calculus.

The broader process lesson — *"a load-bearing architectural commitment has downstream consequences that may not be priced in at design time, and those consequences propagate forward to all sprints touching the same surface"* — is filed as a process-evolution observation below (workflow protocol gaps section).

### Cross-sprint constraint disposition

Three downstream surfaces are implicated. I file:

**DEF-244 (NEW; CROSS-SPRINT, sprint-gating Sprint 31.94 reconnect-recovery):** Sprint 31.94's reconnect-recovery design (DEF-194/195/196) MUST NOT use `modify_order` against OCA-grouped bracket children. Any post-reconnect stop-price adjustment must use Mechanism A (cancel-and-resubmit-fresh-stop). RSK-DEC390-31.94-COUPLING is **retained but its STATEMENT is amended** (see RSK section below) — the original statement was about H2 fail-loud behavior; the amended statement is about the architectural constraint the OCA threading imposes on any stop-modification primitive Sprint 31.94 might design.

**RSK-DEC386-MODIFY-INCOMPATIBILITY (NEW; permanent architectural constraint, not time-bounded):** DEC-386's OCA-group threading on bracket children is structurally incompatible with `modify_order` against any bracket child. This is a load-bearing architectural property that propagates to all sprints touching post-placement bracket order adjustments — Sprint 31.92 (current — Mechanism A absorbs it), Sprint 31.93 (component-ownership refactor — DEF-212 IBKRConfig wiring is now a load-bearing escape-hatch primitive, not a cleanup nice-to-have), Sprint 31.94 (reconnect-recovery — DEF-244 binds), Sprint 35+ Learning Loop V2 (any dynamic-stop-price logic must use Mechanism A). The RSK is permanent (not time-bounded) because the constraint is permanent at the broker policy level.

**Sprint 31.93 (component-ownership refactor) elevated priority on DEF-212:** Tier 3 Review #1 (Phase A FAI completeness, 2026-04-29) Concern B already had Sprint 31.93 wiring `IBKRConfig.bracket_oca_type` into `OrderManager.__init__` to replace the `_OCA_TYPE_BRACKET = 1` module constant. **This wiring is now load-bearing, not cleanup**: it exposes the rollback-to-`ocaType=0` escape hatch as a proper config primitive, which is the operator's last-resort architectural fallback if Mechanism A's Mode-D-equivalent gate ever fails in production. DEF-212's Sprint 31.93 sprint-gating text should be amended at this verdict's mid-sync to reflect the elevated priority.

---

## Sprint 31.92 SbC Amendment Scope

The 12-session SbC framework is fundamentally sound; amendments are surgical, not structural.

| SbC section | Amendment |
|-------------|-----------|
| § Hypothesis Prescription (L825–884) | H2 + H4 hypotheses marked ELIMINATED-EMPIRICALLY (Tier 3 #3 2026-04-30, OCA-categorical-rejection). H1 hypothesis renamed "Mechanism A" and reframed from LAST-RESORT FALLBACK to PRIMARY DEFAULT. H3 remains REJECTED (already settled at Phase A). The threshold-tiered selection rule replaced by Mechanism A's binary gate (4 conditions across N=100 Unit 6 follow-on spike). |
| § Hypothesis Prescription escape-hatch language (L846–884) | Replace verbatim threshold-tier rule with Mechanism A binary gate (per Question 2 Answer above). Retain the "halt and write diagnostic findings file with status INCONCLUSIVE" pattern; surface to operator before proceeding clause; "the hierarchy is H2 > H4 > H1" sentence DELETED (no hierarchy remains; only Mechanism A). |
| § Falsifiable Assumption Inventory FAI #3 (L804) | AMENDED: H2 hypothesis empirically falsified by Tier 3 #3 (2026-04-30); FAI #3 now binds on Mechanism A's Mode-D-equivalent gate (cancel-propagation latency + zero-conflict-in-100). Status changed from "unverified — falsifying spike scheduled in S1a (v2 re-run post-DEC-390)" to "PARTIALLY-VERIFIED — H2 falsified by Tier 3 #3; Mechanism A verification pending Unit 6 follow-on spike." |
| § Falsifiable Assumption Inventory FAI #5 (L806) | AMENDED: original referenced "S1a strengthened cancel-then-immediate-SELL stress" — relocate to Unit 6 (Mode-D-equivalent for Mechanism A). The semantic content (zero-conflict-in-100 hard gate) preserved. |
| § Out-of-Scope items | New item 28 added: "Mechanism B (cancel-bracket / submit-fresh-bracket) and Mechanism C (OCA-membership manipulation) — eliminated per Tier 3 Review #3 verdict; future architectural reconsideration only if Mechanism A's Mode-D-equivalent gate fails." |
| § Acceptance Criteria Deliverable 1 | Updated mechanism description from "H2 amend / H4 hybrid / H1 last-resort cancel-and-await" to "Mechanism A cancel-and-resubmit-fresh-stop." AC1.5 framing updated: "AMD-2 superseded by AMD-2-prime; unprotected window bounded by `cancel_propagation_timeout` ≤ 2 s + fresh stop placement ≤ 200 ms p95." AC1.6 operator-audit logging frequency caveat: every trail-stop / escalation / emergency-flatten update fires a cancel-and-resubmit cycle (frequency higher than the original spec assumed — log at INFO, not WARN, to avoid log spam). |
| § Defense-in-Depth Cross-Layer Composition Tests CL-3 | Updated parameterization: "tests `selected_mechanism = Mechanism A`" (was "`selected_mechanism ∈ {H2, H4, H1}`"). Test design unchanged otherwise. |
| `falsifiable-assumption-inventory.md` | FAI #3 + FAI #5 amended per above. |
| `escalation-criteria.md` | A-class halt A1 amended: "spike returned INCONCLUSIVE under DEC-390 binary Mechanism A gate" (replacing the Tier 3 #2 amended rule reference). New A-class halt A4 added: "Mechanism A's Unit 6 hard gate fails (any 1 conflict in 100) → escalate to Tier 3 Review #4." |

---

## Session-Resumption Guidance

| Session | Disposition |
|---------|-------------|
| **Unit 6 / "S1a-mode-d-followon" (NEW)** | **INSERTED** between current state and S2a impl-prompt generation. Scope: narrow Mode-D-equivalent N=100 spike against fresh OCA-grouped brackets; DEF-243 fixes landed first. ~3–5 hours implementer + operator-execution + close-out. |
| S2a (Path #1 implementation) | **IMPL-PROMPT AMENDED** at this verdict's mid-sync. Mechanism is Mechanism A. AMD-2 superseded by AMD-2-prime. Operator-audit logging at INFO (not WARN) due to higher frequency. Code surface: `_trail_flatten`, `_resubmit_stop_with_retry` emergency path, `_escalation_update_stop`. Test surface: regression tests for cancel-propagation timeout handling (HALT-ENTRY on timeout per C-R2-1↔H-R2-2 coupling). |
| S2b (Path #2 implementation) | **UNAFFECTED.** Resumes as planned post-Unit-6. |
| S3a (Path #2 fingerprint validation) | **UNAFFECTED.** Resumes as planned. |
| S3b (refresh-then-verify validation) | **UNAFFECTED.** Resumes as planned. |
| S4a-i (callback atomicity AST scan) | **UNAFFECTED.** Resumes as planned. |
| S4a-ii (callback atomicity continued + H-R2-5 codebase scan) | **UNAFFECTED.** Resumes as planned. |
| **M-R2-5 mid-sprint Tier 3 review (between S4a-ii and S4b)** | **FIRES AS SCHEDULED.** Scope EXTENDED to validate Mechanism A's cross-layer composition with DEC-385/DEC-386/DEC-388 surfaces (the original M-R2-5 was scoped for DEC-391 4-layer closure validation; the extended scope adds Mechanism A as a new layer). |
| S4b (DEF-212 rider — `IBKRConfig.bracket_oca_type` wiring + dual-channel + `--allow-rollback`) | **UNCHANGED IN SCOPE, ELEVATED IN PRIORITY.** The `ocaType=0` rollback escape hatch is now load-bearing (per Question 3 Answer). Treat S4b as architecturally critical, not cleanup. |
| S5a (in-process Branch 4 validation) | **CL-3 PARAMETERIZATION AMENDED** (`selected_mechanism = Mechanism A`); other cross-layer tests untouched. Resumes as planned. |
| S5b (broker-verified timeout validation) | **UNAFFECTED.** Resumes as planned. |
| S5c (cross-layer composition tests + `SimulatedBrokerWithRefreshTimeout` fixture) | **CL-3 PARAMETERIZATION AMENDED** per S5a; CL-1, CL-2, CL-4, CL-5, CL-7 untouched. CL-6 remains out of scope per Decision 5. |
| **Sprint-close (D14 doc-sync)** | **DEC-390 + DEC-391 MATERIALIZATION TEXT DIFFERS** from Tier 3 #2 anticipated text. DEC-390 narrative now describes the H2/H4 empirical falsification + Mechanism A selection; DEC-391's 4-layer closure framing now references Mechanism A as the Layer 1 primitive. Pattern B retained for both (sprint-close materialization). |

---

## DEC Entries

**DEC-390 — Path #1 Mechanism Selection (AMENDED at this verdict; Pattern B sprint-close materialization).** The Tier 3 #2 rule amendment (axis (i) binds; axes (ii)/(iv) informational; axis (iii) deleted) is RETAINED as historical narrative but is structurally MOOT for selection — H2/H4 are empirically eliminated, only Mechanism A is viable. The amended rule is the binary gate described in Question 2 Answer above. **Sprint-close gate (renewed):** Sprint 31.92 cannot ship if Unit 6 follow-on spike's Mechanism A gate fails (any 1 conflict in 100). In that case, DEC-390 escalates to Tier 3 Review #4. (No viable mechanism remains in the H-class space; operator faces a hard architectural decision.)

**DEC-391 — DEF-204 Round-2 4-Layer Closure (UNCHANGED IN FRAMING; Pattern B sprint-close materialization).** Layer 1 primitive is now Mechanism A (was H2/H4/H1 conditional). Layers 2–4 (DEC-385 side-aware reconciliation cross-check, DEC-388 alert observability integration, DEC-386 OCA threading retention) unchanged. Cross-layer composition tests CL-1 through CL-7 retain their structure; CL-3 parameterization amended.

**No new DEC numbers reserved by this verdict.** Both DEC-390 and DEC-391 are pre-existing reservations from Tier 3 Review #2 (verdict-side numbering provenance: DEC-389→DEC-390 + DEC-390→DEC-391 surgery 2026-04-30 per `tier-3-review-2-verdict-renumbering-corrections.md`). The amendments land in-place at sprint-close per Pattern B.

> **Pre-pinning verification:** Highest materialized DEC in `docs/decision-log.md` confirmed DEC-389 (Sprint 31.915 evaluation.db retention). DEC-390 + DEC-391 RESERVED for Sprint 31.92 sprint-close. Next free DEC for any genuinely new entry would be DEC-392; **no DEC-392 reserved by this verdict.**

---

## DEF Entries

**DEF-244 (NEW; CROSS-SPRINT, sprint-gating Sprint 31.94 reconnect-recovery):**
- **Title:** Sprint 31.94 reconnect-recovery design must use Mechanism A (cancel-and-resubmit-fresh-stop), not `modify_order`, for any post-reconnect bracket-stop-price adjustment.
- **Sprint-gating text:** Sprint 31.94's D1 (`ReconstructContext` parameter), D2 (IMPROMPTU-04 startup invariant gate refactor), and D3 (boot-time adoption-vs-flatten policy decision) deliverables collectively define the post-reconnect bracket-management surface. Any deliverable that includes "re-amend stops post-reconnect" semantics MUST use Mechanism A. The IBKR broker-side categorical rejection of `modify_order` against OCA members (Tier 3 Review #3 2026-04-30 confirmed) is the architectural constraint. Sprint 31.94's Phase A FAI must include an entry asserting that all post-reconnect stop-price adjustment paths are routed through Mechanism A; Phase A Tier 3 (if triggered) must verify this.
- **Sprint home:** Sprint 31.94 (carry-forward; lands in CLAUDE.md DEF table at this verdict's mid-sync per protocol §Output item 3).
- **Cross-references:** RSK-DEC386-MODIFY-INCOMPATIBILITY (the architectural-constraint RSK); RSK-DEC390-31.94-COUPLING (statement amended at this verdict — see RSK section); DEF-241 (the Tier 3 #2 cross-sprint dependency, now superseded in semantic content by DEF-244 but retained for historical traceability — DEF-241's "informational axes (ii)/(iv) characterization" is no longer relevant since the spike harness's axes structure is superseded by Mechanism A's gate).

**DEF-245 (NEW; sprint-internal; resolved at Unit 6 follow-on spike close-out):**
- **Title:** Unit 6 follow-on spike scope — Mode-D-equivalent N=100 against fresh OCA-grouped brackets, with DEF-243 fixes landed first.
- **Resolution scope:** (a) Land DEF-243's three fixes (errorEvent listener, FileHandler, isConnected guard); (b) write a narrow spike script (`scripts/spike_def204_mechanism_a_followon.py` or similar) that creates fresh OCA-grouped brackets, runs N=100 cancel-and-resubmit-fresh-stop cycles, measures cancel-propagation latency + fresh-stop-placement latency + unprotected-window-event count; (c) operator-execute against IBKR paper (single client, single account, no manual disconnect, no operator orchestration); (d) Tier 2 review of script BEFORE operator execution per Tier 3 #2 workflow protocol gap recommendation #1; (e) close-out reports `mechanism_a_zero_conflict_in_100` + latency distributions; HARD GATE: any 1 conflict in 100 → escalate to Tier 3 Review #4.
- **Sprint home:** Sprint 31.92 (sprint-internal — close at Unit 6 follow-on spike acceptance).

> **Pre-pinning verification:** Highest existing DEF in CLAUDE.md confirmed DEF-243 (Unit 5 wrap-up commit `b4e1a9a`). DEF-244 + DEF-245 are next free.

---

## RSK Entries

**RSK-DEC386-MODIFY-INCOMPATIBILITY (NEW; permanent architectural constraint, NOT time-bounded):**
- **Statement:** DEC-386's OCA-group threading (`ocaGroup` + `ocaType=1`) on bracket children is structurally incompatible with `modify_order` against any bracket child. IBKR's broker policy categorically rejects modification of OCA group members (Error 10326, "OCA group revision is not allowed"). Synchronous return is "accepted"; async cancellation arrives within milliseconds via `errorEvent` callback. This is a permanent architectural constraint at the broker policy level, not a time-bounded contract.
- **Implications:** All sprints touching post-placement bracket-order adjustments inherit this constraint. Specifically: Sprint 31.92 (current — Mechanism A absorbs it); Sprint 31.93 (DEF-212 wiring is load-bearing escape-hatch primitive, not cleanup); Sprint 31.94 (DEF-244 binds — reconnect-recovery uses Mechanism A); Sprint 35+ Learning Loop V2 (any dynamic-stop-price logic uses Mechanism A); any future sprint that introduces a new bracket-modification surface must explicitly verify Mechanism A compatibility at Phase A.
- **Mitigation / escape hatch:** `IBKRConfig.bracket_oca_type = 0` (DEC-386's RESTART-REQUIRED rollback) reverts to no OCA bond on bracket children, recovering `modify_order` capability at the cost of losing atomic cancellation (re-opening DEF-204's blast radius). This is operationally a last-resort escape hatch; DEF-212's wiring (Sprint 31.93) makes it a proper config primitive.
- **Time-bounded gating:** **NONE — permanent.** This RSK does not have a "revisit at sprint X" trigger; it is a load-bearing project invariant.

**RSK-DEC390-31.94-COUPLING (EXISTING; STATEMENT AMENDED at this verdict; Pattern A mid-sync materialization):**
- **Original statement (Tier 3 #2):** DEC-390's amended rule presumes H2 fails LOUD during Gateway disconnect; Sprint 31.94 reconnect-recovery may modify how `IBKRBroker.modify_order` surfaces during reconnect.
- **Amended statement (Tier 3 #3):** DEC-390's mechanism is Mechanism A (not H2). Sprint 31.94's reconnect-recovery work must thread Mechanism A through any post-reconnect bracket-stop-price adjustment path. The "fail-loud during reconnect" framing is moot (Mechanism A doesn't use modify_order). The new coupling: Sprint 31.94's reconnect-recovery may introduce a post-reconnect re-amend pattern that must be routed through Mechanism A's cancel-and-resubmit-fresh-stop primitive, not a re-amend-via-modify primitive. DEF-244 is the canonical sprint-gating mechanism.
- **Time-bounded gating:** revisit at Sprint 31.94 Phase B. Sprint 31.94's Phase B DEC must explicitly cross-check against Mechanism A.

**RSK-MECHANISM-A-UNPROTECTED-WINDOW (NEW; gate-coupling to Unit 6 follow-on spike + S2a impl-prompt design):**
- **Statement:** Mechanism A's correctness depends on the unprotected window between (a) bracket-grouped stop cancel-propagation broker-side and (b) fresh outside-OCA stop placement confirmation. AMD-2-prime bounds this window by `cancel_propagation_timeout ≤ 2 s` + `fresh_stop_placement_p95 ≤ 200 ms`. If the window proves operationally unsafe (any 1 conflict in 100 Mode-D-equivalent trials), Mechanism A is ineligible and no viable mechanism remains in the H-class space (Tier 3 Review #4 escalation). Even if the gate passes, S2a's implementation must include defense-in-depth: HALT-ENTRY on `cancel_propagation_timeout` (per existing C-R2-1↔H-R2-2 coupling); operator-audit logging on every cancel-and-resubmit cycle; reconciliation cross-check during the unprotected window.
- **Time-bounded gating:** revisit at Unit 6 close-out. If Mechanism A gate passes, RSK is downgraded to "Mechanism A operational risk" and tracked through paper-trading observation (Sprint 31.91 cessation criterion #5 + post-Sprint-31.92 paper sessions). If the gate fails, RSK is superseded by Tier 3 Review #4's verdict.

**RSK-MODE-D-CONTAMINATION-RECURRENCE (EXISTING; RE-AFFIRMED, no statement amendment):**
- **Statement (Tier 3 #2, retained verbatim):** Even with side-aware `_flatten()` + pre-spike position-sweep gate, paper IBKR may retain residual positions across runs in ways the spike harness cannot detect. If Unit 6 follow-on spike's N=100 Mode-D-equivalent again produces `mechanism_a_zero_conflict_in_100 == false` driven by `position_state_inconsistency` conflicts, Mechanism A cannot be qualified or disqualified, blocking S2a impl-prompt generation.
- **Status update:** Spike v2 attempt 1 did NOT exercise Mode D (script crashed in axis (iv) before Mode D); the recurrence risk is unchanged from Tier 3 #2. Unit 6's narrow scope (Mode-D-equivalent only, no axes) reduces the surface area where contamination can enter. DEF-243's `errorEvent` listener fix also helps by capturing OCA-rejection signatures explicitly (rather than as silent measurement gaps).
- **Time-bounded gating:** revisit at Unit 6 close-out. If recurrence observed, escalate to Tier 3 Review #4.

**RSK-VERDICT-VS-FAI-3-COMPATIBILITY (EXISTING; SUPERSEDED — closing):**
- **Status:** SUPERSEDED-BY-EMPIRICAL-FINDING. The Tier 3 #2 ambiguity (loose vs strict reading of FAI #3) is moot because Mechanism A's selection is binary (gate-pass or gate-fail), not threshold-tiered across multiple axes. The underlying lesson — "primitive-semantics assumptions need empirical validation" — remains valid as a process invariant and is captured in the Tier 3 Review #1 self-falsifiability clause (FAI inventory).
- **Time-bounded gating:** none — closing at this verdict.

---

## Documentation Reconciliation

The verdict's disposition triggers a mid-sprint doc-sync per `protocols/mid-sprint-doc-sync.md` (workflow-version 1.0.0). The mid-sync produces a `tier-3-review-3-doc-sync-manifest.md` artifact in the sprint folder enumerating files touched + sprint-close transitions owed.

**Files touched at this mid-sync (Pattern A — materializes at this verdict's mid-sync):**
1. `docs/sprints/sprint-31.92-def-204-round-2/sprint-spec.md` — § Hypothesis Prescription, § FAI #3 + #5, § Out-of-Scope item 28, § Acceptance Criteria Deliverable 1, § CL-3 parameterization (per the SbC Amendment Scope table above).
2. `docs/sprints/sprint-31.92-def-204-round-2/spec-by-contradiction.md` — Edge Case 2 reference updated to point to Mechanism A.
3. `docs/sprints/sprint-31.92-def-204-round-2/falsifiable-assumption-inventory.md` — FAI #3 + FAI #5 amended.
4. `docs/sprints/sprint-31.92-def-204-round-2/escalation-criteria.md` — A-class halt A1 amended; new A-class halt A4 added.
5. `docs/sprints/sprint-31.92-def-204-round-2/session-breakdown.md` — Unit 6 inserted; compaction risk re-validated for Unit 6 (low score expected — narrow spike scope).
6. **Implementation prompts amended at this mid-sync:** S2a impl-prompt (mechanism is A); S5a + S5c CL-3 parameterization. S4b impl-prompt elevated-priority annotation. **Unit 6 impl-prompt generated NEW** at this mid-sync.
7. `CLAUDE.md` § DEF table — DEF-244 + DEF-245 added.
8. `CLAUDE.md` § RSK table — RSK-DEC386-MODIFY-INCOMPATIBILITY added; RSK-DEC390-31.94-COUPLING statement amended; RSK-MECHANISM-A-UNPROTECTED-WINDOW added; RSK-MODE-D-CONTAMINATION-RECURRENCE re-affirmed; RSK-VERDICT-VS-FAI-3-COMPATIBILITY closed.
9. `docs/risk-register.md` — same RSK changes as #8 with full prose.

**Files touched at sprint-close (Pattern B — materializes at Sprint 31.92 D14 doc-sync):**
10. `docs/decision-log.md` — DEC-390 full entry materialized (Mechanism A binary gate text); DEC-391 references DEC-390 + cross-references Mechanism A as Layer 1 primitive.
11. `docs/dec-index.md` — DEC-390 + DEC-391 added.
12. `docs/project-knowledge.md` — most-cited foundational decisions list amended; sprint-history table updated; DEC-390/DEC-391 narratives reflect Mechanism A.

**Files NOT touched at this mid-sync:**
- `docs/architecture.md` — no architectural change at the production-code surface yet (Mechanism A's production code lands at S2a; architecture.md updates at sprint-close in the same Pattern B materialization as DEC-390).
- `docs/pre-live-transition-checklist.md` — no pre-live config change at the verdict moment; Mechanism A's `cancel_propagation_timeout` config + S4b's `IBKRConfig.bracket_oca_type` rollback escape hatch land in the checklist at sprint-close.
- `docs/process-evolution.md` — captured below as workflow protocol gap surfacing; not touched at this mid-sync.

---

## Cross-Sprint Implications

1. **Sprint 31.94 reconnect-recovery design.** DEF-244 binds Sprint 31.94's D1+D2+D3 to Mechanism A. RSK-DEC390-31.94-COUPLING statement is amended at this mid-sync. Sprint 31.94's Phase A FAI must include an entry asserting Mechanism A is threaded through every post-reconnect bracket-stop adjustment path. Sprint 31.94's Phase A may itself trigger a Tier 3 review under the mandatory-trigger framework (criteria #1 and #3 likely fire).

2. **Sprint 31.93 component-ownership refactor.** DEF-212's `IBKRConfig.bracket_oca_type` wiring is now load-bearing escape-hatch primitive, not cleanup. Sprint 31.93's sprint planner should treat DEF-212 as architecturally critical. The Tier 3 Review #1 Concern A (relocate `_is_oca_already_filled_error` from `ibkr_broker.py` to `broker.py`) is unchanged in priority — still cleanup, but now adjacent to a load-bearing surface.

3. **Sprint 31.91 cessation criterion #5.** Unaffected by this verdict. Operator continues `scripts/ibkr_close_all_positions.py` daily-flatten until 5 paper sessions clean post-seal. The Sprint 31.92 mechanism-replacement does not affect Sprint 31.91's already-sealed work or its cessation timeline.

4. **Sprint 35+ Learning Loop V2.** Any dynamic-stop-price logic Learning Loop V2 introduces must use Mechanism A. RSK-DEC386-MODIFY-INCOMPATIBILITY is permanent and propagates to Sprint 35+. The `ManagedPosition.redundant_exit_observed` persistence (Tier 3 Review #1 Concern D / DEF-209) may need to evolve to track cancel-and-resubmit cycles too (every Mechanism A invocation generates a cancel + a resubmit, observable in trade audit log).

5. **Recurring meta-pattern: load-bearing architectural commitment with unpriced downstream consequence.** Sprint 31.91 DEC-386 closed DEF-204 Round 1 correctly, but the OCA threading's `modify_order` incompatibility was not surfaced at design time. Sprint 31.92 then attempted to use `modify_order` (H2/H4 PRIMARY DEFAULT) against the OCA-threaded bracket children, hitting the constraint empirically. **The pattern is: Sprint N's architectural-closure DEC has implications for Sprint N+1's primitive-selection that are visible only when Sprint N+1's primitives interact with Sprint N's architectural surface.** This is an instance of the lesson the workflow protocol gap (below) captures: architectural-closure DECs need a "downstream-primitive incompatibility audit" sub-step at design time. Filed as a workflow protocol gap, not a new DEF.

---

## Workflow Protocol Gaps Surfaced

1. **Architectural-closure DECs need a downstream-primitive-incompatibility audit step.** DEC-386's design (Sprint 31.91) correctly identified the safety property (atomic cancellation eliminating multi-leg fill races) and the rollback escape hatch (`ocaType=0`). But it did NOT enumerate what broker primitives are STRUCTURALLY INCOMPATIBLE with the chosen architecture (e.g., `modify_order` against OCA members). A 5-minute sub-step at DEC design time — "what broker primitives might a future sprint reasonably want to use against this architectural surface? Are they compatible?" — would have surfaced this constraint at DEC-386 design time, eliminated the H2/H4 hypotheses from Sprint 31.92's spec entirely, and saved a spike v2 attempt 1 + Tier 3 Review #3 cycle. **Recommendation:** consider adding a "Downstream-Primitive Incompatibility Audit" sub-step to `templates/decision-entry.md` for DECs claiming architectural closure of ≥3 layers. Not in scope to amend here; surfaced for the next workflow-evolution review.

2. **Tier 3 mandatory-trigger expansion.** The protocol's existing 6 mandatory triggers (`tier-3-review.md` § Mandatory Triggers) cover safety-load-bearing footprint (#1), architectural-closure ambition (#2), recent empirical falsification (#3), campaign-close absorption (#4), adversarial review N≥2 (#5), high disposition partial-accept ratio (#6). Sprint 31.92's Phase A correctly fired triggers #1 + #5 → Tier 3 Review #1 (2026-04-29). Sprint 31.92 ALSO would have benefited from a 7th trigger: "spike harness involves operator-orchestrated safety-load-bearing patterns" → mandatory mid-sprint Tier 3 at script-delivery milestone before operator execution. The Tier 3 Review #2 verdict already raised this (its workflow-protocol-gap recommendation #2). I confirm and amplify the recommendation here. Not in scope to amend.

3. **Cross-spike bug-class propagation continues to need explicit accounting.** Tier 3 Review #2's recommendation #3 (sister-spike audit at close-out) is reaffirmed. Sprint 31.92's S1b spike (DEF-240) remains in this status — paused pending Cat A application. The Unit 6 follow-on spike is itself a NEW spike harness; it inherits DEF-243's three fixes but should also be audited against DEF-237's side-blind-flatten bug class as a sister-spike check. Not a new recommendation; existing recommendation reaffirmed.

---

## Inherited Follow-ups by Sprint

| Sprint | Item | Source DEF/RSK | Action |
|--------|------|----------------|--------|
| 31.92 (current) | Unit 6 follow-on spike — Mechanism A Mode-D-equivalent N=100 | DEF-245 | Operator-driven; lands DEF-243 fixes first, then narrow spike script, then Tier 2 review BEFORE operator-execute, then operator-execute, then close-out |
| 31.92 (current) | S2a impl-prompt amended | RSK-MECHANISM-A-UNPROTECTED-WINDOW | This verdict's mid-sync; impl-prompt regeneration |
| 31.92 (current) | S5a + S5c CL-3 parameterization amended | (none — sprint-internal) | This verdict's mid-sync; impl-prompt regeneration |
| 31.92 (current) | S4b DEF-212 rider — elevated priority | RSK-DEC386-MODIFY-INCOMPATIBILITY | This verdict's mid-sync; impl-prompt annotation |
| 31.92 (current) | DEC-390 + DEC-391 sprint-close materialization (Mechanism A narrative) | DEC-390, DEC-391 (Pattern B) | Sprint 31.92 D14 doc-sync |
| 31.92 (current) | Sprint-close gate (renewed): Unit 6 Mechanism A gate pass | DEC-390 sprint-close gate | Operator-arranged; Tier 3 Review #4 if gate fails |
| 31.93 | Component-ownership refactor — DEF-212 elevated to load-bearing | RSK-DEC386-MODIFY-INCOMPATIBILITY | Sprint 31.93 sprint planning |
| 31.94 | Reconnect-recovery design Phase A FAI must include Mechanism A entry | DEF-244 + RSK-DEC390-31.94-COUPLING (amended) | Sprint 31.94 sprint planning |
| 35+ | Learning Loop V2 dynamic-stop logic uses Mechanism A | RSK-DEC386-MODIFY-INCOMPATIBILITY (permanent) | Sprint 35+ sprint planning |

---

## Summary

The empirical evidence from spike v2 attempt 1 is overwhelming: IBKR's broker policy categorically rejects `modify_order` against OCA group members. DEC-386's `ocaType=1` threading on bracket children is the architectural cause, and the rejection is broker-side policy, not implementation. H2 (`modify_order` PRIMARY DEFAULT) and H4 (hybrid amend) are structurally eliminated; H1 — promoted, renamed Mechanism A (cancel-and-resubmit-fresh-stop) — is the selected mechanism, conditional on a narrow Unit 6 follow-on spike validating its Mode-D-equivalent hard gate.

DEC-386 is RETAINED without modification — the OCA threading's safety property (atomic cancellation eliminating ~98% of DEF-204's blast radius) dominates the modify-incompatibility cost. The cross-sprint constraint propagates forward via DEF-244 (Sprint 31.94 reconnect-recovery binding) and RSK-DEC386-MODIFY-INCOMPATIBILITY (permanent architectural constraint). DEF-212's `IBKRConfig.bracket_oca_type` wiring (Sprint 31.93) is elevated from cleanup to load-bearing escape-hatch primitive.

This verdict:
- Confirms Question 1 (OCA-categorical-rejection) on overwhelming evidence;
- Selects Mechanism A for Question 2, pending Unit 6 follow-on spike;
- Retains DEC-386 unchanged for Question 3, propagating the constraint forward via DEF-244 + RSK-DEC386-MODIFY-INCOMPATIBILITY;
- Files DEF-244 (cross-sprint) + DEF-245 (sprint-internal) — both numbered at the live ceiling (DEF-243 + 1, +2);
- Files RSK-DEC386-MODIFY-INCOMPATIBILITY (permanent) + RSK-MECHANISM-A-UNPROTECTED-WINDOW (gate-coupling); amends RSK-DEC390-31.94-COUPLING statement; closes RSK-VERDICT-VS-FAI-3-COMPATIBILITY (superseded); re-affirms RSK-MODE-D-CONTAMINATION-RECURRENCE;
- Reserves no new DEC numbers — DEC-390 + DEC-391 reservations (from Tier 3 #2) carry forward unchanged; both materialize at sprint-close per Pattern B with amended narrative;
- Triggers a mid-sprint doc-sync per `protocols/mid-sprint-doc-sync.md`. Pattern A files materialize now; Pattern B files (DEC + index + project-knowledge narrative) defer to Sprint 31.92 D14 doc-sync per "use Pattern B when in doubt."

**Sprint 31.92 proceeds at REVISE_PLAN** with bounded amendments: Unit 6 follow-on spike inserted before S2a; S2a + S5a/S5c CL-3 + S4b impl-prompts amended; other 9 sessions unaffected. M-R2-5 mid-sprint Tier 3 fires as scheduled at S4a-ii close-out, scope extended to validate Mechanism A's cross-layer composition. **Sprint-close gate (renewed):** Unit 6's Mechanism A hard gate (zero-conflict-in-100 + cancel-propagation latency thresholds) must pass; failure escalates to Tier 3 Review #4, where the operator faces a hard architectural decision space (ocaType=0 rollback, fundamental dynamic-stop-price redesign, or Round 2 deferral pending IBKR API evolution).

The architectural commitment to DEC-386 is durable. The cost — Mechanism A's higher broker-call volume + bounded unprotected window per stop update — is operationally acceptable for ARGUS's strategy populations. The asymmetric-risk-aware default holds.

---

*End of Sprint 31.92 Tier 3 Architectural Review #3 verdict.*

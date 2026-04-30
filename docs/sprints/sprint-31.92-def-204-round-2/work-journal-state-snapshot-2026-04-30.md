# Sprint 31.92 — Work Journal State Snapshot (2026-04-30 post-Tier-3-#3-verdict)

> **Purpose:** Compaction-insurance snapshot of the Sprint 31.92 Work Journal's running register at 2026-04-30, after Tier 3 Review #3 verdict commit (`b274dd3`) and before Unit A (mid-sync) execution. If the live Work Journal conversation compacts or is lost, a fresh Work Journal conversation can be seeded with this snapshot + project knowledge + the sprint folder and resume cleanly at Unit A.
>
> **Authoritative beyond this snapshot:** `tier-3-review-3-verdict.md`, `tier-3-review-2-verdict.md`, `tier-3-review-1-verdict.md`, `tier-3-review-2-verdict-renumbering-corrections.md`, CLAUDE.md DEF + RSK tables, `docs/risk-register.md`, `docs/decision-log.md`. The snapshot summarizes; the artifacts bind.

---

## Current state

- **Sprint:** 31.92 (DEF-204 Round 2 — Path #1 mechanism replacement post-empirical-falsification of H2/H4)
- **HEAD on `origin/main`:** `b274dd3` — Tier 3 Review #3 verdict committed
- **Sprint phase:** Awaiting Unit A (mid-sync) execution per Tier 3 Review #3 §Documentation Reconciliation
- **Pytest baseline:** 5,337 (post-Unit-4 + post-CONCERN-1-docstring-fix). Vitest 913. Cumulative LOC on `argus/execution/order_manager.py`: 0/1350.
- **G1 (Path #1 mechanism gate):** NOT MET — gated on Unit 6 follow-on spike
- **Operator daily mitigation:** `scripts/ibkr_close_all_positions.py` continues until Sprint 31.91 cessation criterion #5 (5 paper sessions clean post-Sprint-31.92 seal). DEF-239 audit confirmed script is side-aware; daily-flatten is safe. Cessation clock unaffected by Sprint 31.92 work.

---

## Load-bearing decisions (Tier 3 #3 verdict outcomes)

1. **OCA-categorical-rejection inference: CONFIRMED.** IBKR error 10326 fires on 100% of `modify_order` against OCA-grouped bracket children. Broker-side policy. 211 occurrences in operator log; 105 distinct events; multiple symbols and fresh brackets observed.
2. **H2 (`modify_order` PRIMARY DEFAULT) and H4 (hybrid amend): structurally eliminated.** No mechanism amendment can recover them.
3. **Mechanism A (cancel-and-resubmit-fresh-stop) selected**, conditional on Unit 6 follow-on spike validating its Mode-D-equivalent hard gate (4 conditions across N=100).
4. **DEC-386 (Sprint 31.91 OCA threading): RETAINED unchanged.** Side effect (modify_order incompatibility) is bounded and absorbable by Mechanism A; safety property dominates the cost. Constraint propagated forward as permanent architectural property.
5. **Sprint structure: 12 sessions mostly intact.** Unit 6 inserted between current state and S2a. S2a + S5a + S5c CL-3 impl-prompts amended. S4b elevated from cleanup to load-bearing. Other 9 sessions unaffected. M-R2-5 mid-sprint Tier 3 fires as scheduled at S4a-ii close-out, scope extended.
6. **Sprint-close gate renewed:** Sprint 31.92 cannot ship if Unit 6's Mechanism A hard gate fails. Failure → Tier 3 Review #4 (operator faces hard architectural decision space: ocaType=0 rollback, dynamic-stop-price redesign, or Round 2 deferral).

## Mechanism A — pinned details

- **Pattern:** cancel bracket-grouped stop (atomically cancels OCA siblings) → await cancel-propagation (≤ 2 s per AMD-2-prime) → place fresh stop OUTSIDE OCA bond → update `ManagedPosition` accounting.
- **Unprotected window:** ~2.2 s bounded (cancel propagation ≤ 2 s + fresh stop placement ≤ 200 ms p95).
- **Hard gate (4 conditions, all must pass at Unit 6):**
  1. `mechanism_a_zero_conflict_in_100 == true`
  2. `cancel_propagation_p50_ms ≤ 1000`
  3. `cancel_propagation_p95_ms ≤ 2000`
  4. `fresh_stop_placement_p95_ms ≤ 200`
- **Higher broker call volume than H2:** every trail-stop / escalation / emergency-flatten update fires a cancel-and-resubmit cycle (~2× call volume). Operator-audit logging at INFO level (not WARN) per S2a impl-prompt amendment, to avoid log spam.

---

## Identifiers — current ceiling and pinned status

**Pre-pinning verification was performed for every identifier in this snapshot. Grep before assigning new IDs.**

### DEFs (highest in CLAUDE.md: DEF-245)

| ID | Title | Status |
|----|-------|--------|
| DEF-236 | Mode A propagation measurement bug (Cat A.1) | RESOLVED-PENDING-SPIKE-V2-VALIDATION (Unit 3 commit `90ba754`) |
| DEF-237 | Side-blind `_flatten()` in S1a harness (Cat A.2) | RESOLVED-PENDING-SPIKE-V2-VALIDATION (Unit 3 commit `90ba754`); Option B fix shape per Work Journal disposition (verdict's `_raw_ib_pos` not in codebase; applied via `(p.side, p.shares)` reading mirroring IMPROMPTU-04 production precedent at `argus/main.py::check_startup_position_invariant` + `order_manager.py:1878-1904/:1925-1947`) |
| DEF-238 | Spike harness axis (ii)/(iv) instrumentation no fail-loud (Cat B.3) | RESOLVED-PENDING-SPIKE-V2-VALIDATION (Unit 4 commit `b758e5d`) |
| DEF-239 | `scripts/ibkr_close_all_positions.py` audit | RESOLVED-VERIFIED-NO-FIX (audit anchor: `def-216-audit-resolved-verified.md`, 2026-04-30; script imports `ib_async.Position` directly, structurally inaccessible to DEF-237 bug class) |
| DEF-240 | S1b sister-spike same bug class | OPEN — paused pending Cat A application (S1b script at `becc28e`, not operator-executed) |
| DEF-241 | Sprint 31.94 reconnect-recovery dependency on informational axes | OPEN — semantic content superseded by DEF-244 post-Tier-3-#3, retained for historical traceability |
| DEF-242 | DEC-390 H2/H4 OCA-eliminated | OPEN — sprint home Sprint 31.92 (in-sprint pivot to Mechanism A absorbs this); resolution pending Unit 6 close-out |
| DEF-243 | Spike harness async error capture + file-logger gap | OPEN — Sprint 31.92 sprint-internal cleanup; lands in Unit B before Unit C (Unit 6 spike) |
| **DEF-244 (NEW)** | **Sprint 31.94 reconnect-recovery design must use Mechanism A** | OPEN — CROSS-SPRINT, sprint-gating Sprint 31.94. Filed in CLAUDE.md at Unit A mid-sync. |
| **DEF-245 (NEW)** | **Unit 6 follow-on spike scope** | OPEN — Sprint 31.92 sprint-internal; resolved at Unit 6 close-out. Filed in CLAUDE.md at Unit A mid-sync. |

**Next free DEF: DEF-246.** Verified by grep `^| DEF-` against CLAUDE.md.

### DECs

- **Highest materialized:** DEC-389 (Sprint 31.915 evaluation.db retention).
- **Reserved:** DEC-390 (Path #1 Mechanism Selection — amended at Tier 3 #3 to be Mechanism A binary gate; Pattern B sprint-close materialization). DEC-391 (4-layer DEF-204 closure; Layer 1 primitive is now Mechanism A; Pattern B sprint-close materialization).
- **Next free if any new DEC needed:** DEC-392. **None reserved by this snapshot.**

### RSKs (Sprint 31.92)

| RSK | Status |
|-----|--------|
| RSK-DEC390-31.94-COUPLING | EXISTING — STATEMENT AMENDED at Tier 3 #3 (now describes Mechanism A coupling, not H2 fail-loud); revisit at Sprint 31.94 Phase B |
| RSK-MODE-D-CONTAMINATION-RECURRENCE | EXISTING — RE-AFFIRMED, no statement amendment; revisit at Unit 6 close-out |
| RSK-VERDICT-VS-FAI-3-COMPATIBILITY | EXISTING — **CLOSED-SUPERSEDED** at Tier 3 #3 (Mechanism A's selection is binary; threshold ambiguity moot) |
| **RSK-DEC386-MODIFY-INCOMPATIBILITY (NEW)** | **PERMANENT, NOT TIME-BOUNDED.** Files at Unit A mid-sync. Propagates to Sprint 31.92, 31.93, 31.94, 35+. Mitigation: `IBKRConfig.bracket_oca_type = 0` (DEF-212 Sprint 31.93 wiring is now load-bearing escape hatch primitive). |
| **RSK-MECHANISM-A-UNPROTECTED-WINDOW (NEW)** | Gate-coupling to Unit 6 + S2a impl-prompt design. Files at Unit A mid-sync. Revisit at Unit 6 close-out — if gate passes, downgrade to "Mechanism A operational risk" and track through paper-trading observation. If gate fails, superseded by Tier 3 Review #4 verdict. |

### Tier 3 reviews (this sprint)

| Review | Date | Trigger | Verdict | Verdict file |
|--------|------|---------|---------|--------------|
| #1 | 2026-04-29 | Phase A FAI completeness (Round 1+2 FAI miss meta-pattern) | REVISE_PLAN with Sub-areas A–E | `tier-3-review-1-verdict.md` (commit `26875fe` + restored at `cc830a0`) |
| #2 | 2026-04-30 | A1 — S1a spike INCONCLUSIVE | REVISE_PLAN — DEC-390 rule amendment (axis (i) binds; axes (ii)/(iv) informational; axis (iii) deleted) | `tier-3-review-2-verdict.md` (mid-sync `0411e86`; surgery `cc830a0`) |
| #3 | 2026-04-30 | DEC-390 sprint-close gate | REVISE_PLAN shape 2 — Mechanism A selected pending Unit 6 | `tier-3-review-3-verdict.md` (commit `b274dd3`) |

---

## Sequencing — five work units (post-Tier-3-#3)

| Unit | Description | Gated on | Status |
|------|-------------|----------|--------|
| **A** | Mid-sync per `protocols/mid-sprint-doc-sync.md`. Pattern A files materialize per Tier 3 #3 §Documentation Reconciliation. Pattern B files (decision-log.md, dec-index.md, project-knowledge.md) defer to sprint-close. Unit 6 impl-prompt generated NEW. | Ready now | NOT STARTED |
| **B** | DEF-243 fixes — `errorEvent` listener tagging trials with `oca_rejected: true`; `logging.FileHandler`; `isConnected()` precondition gate | Unit A | Not started |
| **C** | Unit 6 follow-on spike script (new file, e.g. `scripts/spike_def204_mechanism_a_followon.py`). Mode-D-equivalent N=100 only; no axes (i)/(ii)/(iii)/(iv). | Unit B | Not started |
| **D** | Tier 2 review of Unit 6 script BEFORE operator execution. Per Tier 3 #2 workflow protocol gap recommendation #1. In-session @reviewer subagent. | Unit C | Not started |
| **E** | Operator executes Unit 6 spike; clean JSON with all 4 hard gate conditions met → S2a/S2b unblock. Failure on any condition → Tier 3 Review #4. | Unit D | Not started |

After Unit E passes: rest of Sprint 31.92 (S2a, S2b, S3a, S3b, S4a-i, S4a-ii, M-R2-5, S4b, S5a, S5b, S5c, sprint-close) proceeds per amended structure.

## Operator-confirmation gates (renewed for post-Tier-3-#3)

| Gate | Trigger | Confirms | Unblocks |
|------|---------|----------|----------|
| **G1** (renewed) | Unit 6 spike JSON landed | All 4 Mechanism A hard gate conditions met | S2a + S2b impl-prompt regeneration |
| **G2** | S1b spike JSON landed | `recommended_locate_suppression_seconds` value | S3a impl-prompt generation |
| **G3** | S4a-ii close-out + Tier 2 verdict | All 4 deliverables green | M-R2-5 mid-sprint Tier 3 fires |
| **G4** | M-R2-5 verdict | PROCEED / REVISE_PLAN / PAUSE_AND_INVESTIGATE | S4b + S5a + S5b + S5c |

---

## Pre-applied operator decisions (1–7) — all confirmed by canonical artifacts at 2026-04-30

| # | Decision | Canonical anchor |
|---|----------|------------------|
| 1 | S1a 4 axes (i/ii/iii/iv) for FAI #3 worst-axis Wilson UB | sprint-31.92-s1a-spike-path1-impl.md L54-87 + Round 3 M-R3-1 amendment. **Note post-Tier-3-#2 + #3:** axis (iii) deleted, axes (ii)/(iv) demoted to informational, axis (i) binding rule replaced by Mechanism A binary gate. |
| 2 | N=100 hard gate; any 1 conflict → H1 ineligible regardless of axis UB | adversarial-review-input-package-round-3.md L462 + S1a impl L146. **Spirit preserved post-Tier-3-#3** as Mechanism A's `mechanism_a_zero_conflict_in_100` gate. |
| 3 | FAI #8 option (a) — 3 reflective sub-tests | adversarial-review-input-package-round-3.md row 8 + S4a-ii impl L131/L286/L321-325. Unaffected by Tier 3 #3. |
| 4 | Watchdog auto-flip `auto`→`enabled` on first `case_a_in_production`; in-memory only, restart resets to `auto` | round-3-disposition.md §3.2 H-R3-2 + §5.2 RSK-WATCHDOG-AUTO-FLIP-RESTART-LOSS. Unaffected by Tier 3 #3. |
| 5 | CL-1 through CL-5 + CL-7 (Round 3 C-R3-1 amendment); CL-6 OUT; total 6 cross-layer tests. **CL-3 parameterization amended at Tier 3 #3** to `selected_mechanism = Mechanism A`. | sprint-31.92-s5c-cross-layer-composition-tests-review.md L110, L135, L194 |
| 6 | Sprint 31.94 D3 prioritization re-evaluation is separate Discovery, NOT Sprint 31.92 deliverable | adversarial-review-input-package-round-3.md L414 + round-2-disposition.md L437/L483. Unaffected by Tier 3 #3. |
| 7 | Round 3 pre-commitment: (a) primitive-semantics → Phase A re-entry; (b) any other Critical → RSK-and-ship. Round 3 produced C-R3-1; (b) override invoked. | escalation-criteria.md L142-158 + round-3-disposition.md §1 Operator Override Invocation |

---

## Process maturation observations (queued for sprint-close `process-evolution.md`)

1. **Pre-pinning verification discipline.** Three pre-pinning failures earlier in this sprint (DEF-213→218 verdict-side collided with Sprint 31.91 sealed range; DEC-389→390 verdict-side collided with Sprint 31.915 retention; tier-3-review-1-verdict.md path overwritten by ESCALATE-A1 verdict). Tier 3 #3 reviewer correctly grep-verified DEF-244 + DEF-245 against ceiling DEF-243 before pinning. Process tightening worked.

2. **Spike harness reproducing the very bug it tests for** (Cat A.2 / DEF-237). Strong evidence for the synchronous-update invariant extension across ALL flatten/SELL callsites + AST regression infrastructure. Validates Tier 3 entry #9 prior. Now a recurring lesson with multiple instances; pair with the DEF-239 audit's contrast (same structural pattern, different policy on each branch — long-only spike abort vs full-cleanup tool BUY-to-cover).

3. **Operator-tooling and ARGUS-production diverge on signed-quantity reading.** `scripts/ibkr_close_all_positions.py` reads `ib_async.Position.position` directly (raw signed). ARGUS reads `argus.models.trading.Position.shares = abs(int(ib_pos.position))` (absolute-value-wrapped) plus `Position.side`. Both correct in their contexts; Option B disposition for DEF-237 used the ARGUS production path mirroring IMPROMPTU-04, not the daily-flatten-script path.

4. **Verdict-prescribed literal code requires grep-verification before publication.** Tier 3 Review #2 verdict's Cat A.2 prescribed `p._raw_ib_pos.position` which had zero matches in codebase. Option B disposition substituted `(p.side, p.shares)` mirroring IMPROMPTU-04. Recommendation: future Tier 3 briefings include "cited primitives must be grep-verified" instruction.

5. **Tier 3 briefings must include current repo ceilings.** Without explicit live ceilings (DEF, DEC, sprint review numbering), fresh-conversation reviewers extrapolate from anticipated values and reliably collide. Tier 3 #3's briefing explicitly embedded DEF-243 / DEC-389 / sprint review N=3 ceilings; reviewer cited those ceilings before pinning new IDs. Pattern works.

6. **Architectural-closure DECs need a downstream-primitive-incompatibility audit step.** Tier 3 #3's surfacing: DEC-386's design correctly identified safety property + rollback escape hatch but didn't enumerate STRUCTURALLY INCOMPATIBLE broker primitives (`modify_order` against OCA members). Recommendation for next workflow-evolution review: add a "Downstream-Primitive Incompatibility Audit" sub-step to `templates/decision-entry.md` for DECs claiming architectural closure of ≥3 layers.

---

## Tier 2 reviewer convention (pinned for sprint)

In-session @reviewer subagent. Operator confirmed at Unit 3 close-out. Used for Units 3, 4 already; will be used for Unit 6 (Unit D) and downstream sessions.

## What the Work Journal owes the operator at sprint-close

`work-journal-closeout.md` deliverable per `templates/work-journal-closeout.md` standard structure top-half (12-session sprint, not Hybrid Mode 20+). Doc-sync handoff prompt that combines the closeout register + `templates/doc-sync-automation-prompt.md` framing. Operator pastes the deliverable into a fresh Claude.ai conversation prefixed with the doc-sync skill invocation per `.claude/skills/doc-sync.md`.

---

*End of Sprint 31.92 Work Journal State Snapshot — 2026-04-30 post-Tier-3-#3-verdict.*

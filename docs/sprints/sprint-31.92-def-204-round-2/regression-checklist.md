# Sprint 31.92: Sprint-Level Regression Checklist

> **Phase C artifact 6/8.** Specific, testable items the `@reviewer` must verify
> at every Tier 2 review. Embedded into every implementation prompt so the
> implementer can self-check before close-out and the reviewer has explicit
> assertions to test against. Each item lists which sessions are responsible
> for verifying it.

> **Pre-revision baseline.** This checklist is authored at Phase C, before
> adversarial review (Phase C-1). Adversarial review may add or sharpen
> invariants; the post-revision checklist takes precedence. Sprint 31.91's
> checklist grew from 9 invariants (original) → 22 invariants (third revision)
> across multiple passes — Sprint 31.92's first pass is intentionally
> conservative; reviewers should expect growth.

## Critical Invariants (Must Hold After Every Session)

The 18 invariants below are organized into three groups:
- **Invariants 1–9: PRESERVED FROM PRIOR SPRINTS** — DEC-117/364/369/372/385/386/388 + DEF-158 + `# OCA-EXEMPT:`. Sprint 31.92 must NOT regress any.
- **Invariants 10–12: BASELINE PRESERVATION** — test count, pre-existing flake count, frontend immutability.
- **Invariants 13–18: NEW IN SPRINT 31.92** — established by AC1/AC2/AC3/AC4.

### 1. DEC-117 Atomic Bracket Order Placement

**Test:** `tests/execution/test_atomic_brackets.py` (existing) — parent + 2 children placed atomically; parent failure cancels children; transmit-flag semantics preserved.

**Verified at:** Every session's close-out. **Critical for:** S2a, S2b (Path #1 mechanism touches `_trail_flatten` + `_resubmit_stop_with_retry`'s emergency-flatten branch, both of which interact with bracket-stop cancellation timing — must not regress atomic bracket invariants).

**Sessions responsible:** ALL.

---

### 2. DEC-364 `cancel_all_orders()` No-Args ABC Contract

**Test:** Pre-existing regression test that asserts `Broker.cancel_all_orders()` (no args) preserves DEC-364 behavior; DEC-386 S0's positional+keyword signature `cancel_all_orders(symbol: str | None = None, *, await_propagation: bool = False)` is BACKWARD-COMPATIBLE (zero-arg call = original DEC-364 behavior).

**Verified at:** Every session's close-out. **Critical for:** S2a, S2b (if Path #1 mechanism uses cancel-and-await, calls go through this ABC; must preserve no-args semantics for any existing callers).

**Sessions responsible:** ALL.

---

### 3. DEC-369 Broker-Confirmed Reconciliation Immunity

**Test:** Pre-existing test that broker-confirmed positions (with IBKR entry fill callbacks, `oca_group_id is None`-derived from `reconstruct_from_broker`) are NOT auto-closed by reconciliation. AC3.5 must compose with this: ceiling initialization for reconstruct-derived positions does not modify reconciliation behavior.

**Verified at:** Every session's close-out. **Critical for:** S4a (ceiling initialization for `reconstruct_from_broker`-derived positions per AC3.5).

**Sessions responsible:** ALL.

---

### 4. DEC-372 Stop Retry Caps + Exponential Backoff

**Test:** Pre-existing `test_stop_resubmission_cap` — retry attempts capped per config; backoff is 1s → 2s → 4s; emergency-flatten fires only after cap exhausted.

**Verified at:** Every session's close-out. **Critical for:** S2b (touches the emergency-flatten branch in `_resubmit_stop_with_retry`; must preserve retry-cap and backoff invariants while applying Path #1 mechanism to the emergency SELL).

**Sessions responsible:** ALL; especially S2b.

---

### 5. DEC-385 Six-Layer Side-Aware Reconciliation

**Test:** Pre-existing monotonic-safety matrix regression `test_def204_reconciliation_layers_monotonic` (Sprint 31.91 invariant 17). All 6 layers — main.py call-site → metadata schema → OrderManager Pass 1 → phantom-short gate → EOD verify → audit-log enrichment — preserved byte-for-byte.

**Verified at:** Every session's close-out. **Critical for:** S3a + S3b (Path #2's suppression-timeout fallback REUSES `phantom_short_retry_blocked` alert from DEC-385 L4; must not modify the alert path itself).

**Sessions responsible:** ALL; especially S3a, S3b.

**Specific edges:**
- DEF-158 retry 3-branch side-check (lines ~3424–3489) UNCHANGED — Path #2 adds upstream detection at `place_order` exception, NOT a 4th branch.
- `phantom_short_retry_blocked` SystemAlertEvent emitter unchanged in source code — Path #2's suppression-timeout fallback CALLS this existing emitter from `_check_flatten_pending_timeouts` housekeeping loop.

---

### 6. DEC-386 Four-Layer OCA Architecture

**Test:** Pre-existing monotonic-safety matrix regression `test_dec386_oca_layers_preserved`. All 4 layers — S0 ABC contract / S1a bracket OCA / S1b standalone-SELL OCA / S1c broker-only safety — preserved byte-for-byte.

**Verified at:** Every session's close-out. **Critical for:** S4b (DEF-212 rider modifies `OrderManager.__init__` and the 4 OCA-thread sites at `_trail_flatten`, `_escalation_update_stop`, `_submit_stop_order`/`_resubmit_stop_with_retry`, `_flatten_position`; the OCA-threading SEMANTICS must remain identical — only the source of `ocaType` value changes from module constant to instance attribute).

**Sessions responsible:** ALL; especially S4b.

**Specific edges:**
- `IBKRBroker.place_bracket_order` OCA threading (DEC-386 S1a) UNCHANGED.
- `_handle_oca_already_filled` SAFE-marker path (DEC-386 S1b) UNCHANGED.
- `# OCA-EXEMPT:` exemption mechanism preserved (see invariant 9).
- `_is_oca_already_filled_error` helper UNCHANGED (relocation deferred to Sprint 31.93 per SbC #4).

---

### 7. DEC-388 Alert Observability Subsystem

**Test:** Pre-existing tests for HealthMonitor consumer + REST + WebSocket + 5-layer storage. AST policy-table exhaustiveness regression `tests/api/test_policy_table_exhaustiveness.py` updated at S4a to include `sell_ceiling_violation` (now 14 entries).

**Verified at:** Every session's close-out. **Critical for:** S4a (adds 1 new alert type `sell_ceiling_violation` and 1 new `POLICY_TABLE` entry; must preserve all 13 existing entries) and S3b (Path #2's suppression-timeout fallback emits `phantom_short_retry_blocked` via the existing DEC-385 path — no new emitter site at the consumer side).

**Sessions responsible:** ALL; especially S4a.

**Specific edges:**
- `POLICY_TABLE` count: 13 (pre-S4a) → 14 (post-S4a). Verify by `grep -c '^[[:space:]]*"' argus/core/alert_auto_resolution.py | head` or AST count.
- `sell_ceiling_violation` policy entry: `operator_ack_required=True`, `auto_resolution_predicate=None` (manual-ack only).
- Existing 13 policy entries unchanged.

---

### 8. DEF-158 Retry Three-Branch Side-Check Preserved Verbatim

**Test:** New regression test `test_def158_3branch_side_check_preserved_verbatim` (S3b). Asserts that `_check_flatten_pending_timeouts` lines ~3424–3489 retain the BUY → resubmit / SELL → alert+halt / unknown → halt structure UNCHANGED. Path #2's NEW detection is at the `place_order` exception in the 4 SELL emit sites, NOT inside this gate.

**Verified at:** S3b close-out specifically; reviewed at every session as a do-not-modify boundary.

**Sessions responsible:** ALL; especially S3b. **A-class halt A5** fires if violated.

---

### 9. `# OCA-EXEMPT:` Exemption Mechanism Preserved

**Test:** Pre-existing grep regression guard `test_no_sell_without_oca_when_managed_position_has_oca` from DEC-386 S1b. Continues to fire only on `# OCA-EXEMPT: <reason>` comment annotations on legitimate broker-only paths.

**Verified at:** Every session's close-out. **Critical for:** S2a, S2b, S3b, S4a (any new SELL emit logic must either use OCA threading via `position.oca_group_id` OR carry an `# OCA-EXEMPT: <reason>` comment).

**Sessions responsible:** ALL.

**Specific edges:**
- DEF-158 retry SELL site at `_check_flatten_pending_timeouts` retains its existing `# OCA-EXEMPT:` comment unchanged.
- New SELL paths added in Sprint 31.92 (none expected — only modifications) would need the comment.

---

### 10. Test Count Baseline Holds

**Test:** Full suite pytest count ≥ 5,269 at every close-out (DEC-328 tiering: every session's close-out runs full suite). Vitest count = 913 unchanged at every close-out.

**Verified at:** Every session's close-out. **B-class halt B3** fires if pytest drops below baseline.

**Sessions responsible:** ALL.

**Per-session test deltas (estimated):**
| Session | Pytest Δ | Vitest Δ |
|---------|---------:|---------:|
| S1a | 0 | 0 |
| S1b | 0 | 0 |
| S2a | +5 | 0 |
| S2b | +7 | 0 |
| S3a | +5 | 0 |
| S3b | +8 | 0 |
| S4a | +6 (counted as +6 effective with 1 parametrized × 3) | 0 |
| S4b | +5 (counted as +9 effective with 1 parametrized × 4) | 0 |
| S5a | +4 | 0 |
| S5b | +5 | 0 |
| **Total range** | **+45 to +65** | **0** |

**Final target:** 5,314–5,334 pytest + 913 Vitest at S5b close-out.

---

### 11. Pre-Existing Flake Count Does Not Increase

**Test:** Run full suite at every session close-out; count failures attributable to DEF-150 (time-of-day arithmetic), DEF-167 (Vitest hardcoded-date scan), DEF-171 (ibkr_broker xdist), DEF-190 (pyarrow/xdist register_extension_type race), DEF-192 (runtime warning cleanup debt). Flake count ≤ baseline.

**Verified at:** Every session's close-out. **B-class halt B1** fires if any flake worsens or new flake appears.

**Sessions responsible:** ALL.

---

### 12. Frontend Immutability

**Test:** `git diff <session-base>..HEAD -- 'frontend/'` returns empty for every session. Vitest count = 913 at every close-out.

**Verified at:** Every session's close-out. **B-class halt B8** fires if violated.

**Sessions responsible:** ALL. (No session has frontend scope.)

---

### 13. Long-Only SELL-Volume Ceiling: `cumulative_sold_shares ≤ shares_total` Per `ManagedPosition`

**Test:** New parametrized test `test_check_sell_ceiling_blocks_excess_sell_at_each_emit_site` (S4a, parametrized × 3 emit sites + S5b composite × remaining 2 emit sites) — asserts that `_check_sell_ceiling(position, requested_qty)` returns False iff `position.cumulative_sold_shares + requested_qty > position.shares_total`. ALL 5+ SELL emit sites enforce the check before `place_order(SELL)`.

**Verified at:** S4a close-out (3 of 5 sites parametrized); S5b close-out (remaining 2 sites + composite stress test). **A-class halt A11** fires if false-positives observed in production paper trading.

**Sessions responsible:** S4a, S5b.

**Specific edges:**
- Per-`ManagedPosition`, NOT per-symbol (AC3.4).
- `reconstruct_from_broker`-derived: initialize `cumulative_sold_shares = 0`, `shares_total = abs(broker_position.shares)` (AC3.5).
- Config-gated: `OrderManagerConfig.long_only_sell_ceiling_enabled = false` returns True unconditionally (AC3.6).
- Increment in `on_fill` for SELL-side fills only (T1, T2, bracket stop, trail-flatten, escalation-flatten, retry-flatten, EOD-flatten, locate-released-flatten — AC3.1).

---

### 14. Path #2 Locate-Rejection Fingerprint Deterministic

**Test:** New regression test `test_is_locate_rejection_matches_canonical_string` (S3a). Asserts that `_is_locate_rejection()` returns True for the exact substring captured by S1b spike (`"contract is not available for short sale"`, case-insensitive); False for other Error 201 reasons (margin, price-protection, OCA-already-filled).

**Verified at:** S3a close-out; ongoing at quarterly re-validation (RSK-DEC-390-FINGERPRINT — operational hygiene). **A-class halt A2** fires if S1b returns INCONCLUSIVE; **A-class halt A13** fires if spike artifact >30 days old at first post-merge paper session.

**Sessions responsible:** S3a (establishes); S5b (validates against synthetic locate-rejection fixture).

**Specific edges:**
- Substring match (NOT regex unless S1b finds variants) — case-insensitive via `str(error).lower()`.
- Helper accepts `BaseException` (mirrors DEC-386's `_is_oca_already_filled_error` shape).
- Returns False for non-exception inputs (defensive).

---

### 15. `_OCA_TYPE_BRACKET` Module Constant Deleted

**Test:** New grep regression guard `test_no_oca_type_bracket_constant_remains_in_module` (S4b). Greps `argus/execution/order_manager.py` for the literal `_OCA_TYPE_BRACKET` and asserts ZERO matches post-S4b.

**Verified at:** S4b close-out; every subsequent session as a non-regression check. **B-class halt B11** fires if the count is wrong before S4b begins.

**Sessions responsible:** S4b (establishes); S5a, S5b (preserve).

**Specific edges:**
- Pre-S4b: 5 occurrences (1 declaration + 4 use sites at lines ~3212, ~3601, ~3714, ~3822 — verify via grep at session start; absolute line numbers are directional only per protocol v1.2.0).
- Post-S4b: 0 occurrences. All replaced by `self._bracket_oca_type`.
- `OrderManager.__init__` accepts `bracket_oca_type: int` keyword arg; `argus/main.py` construction site passes `config.ibkr.bracket_oca_type`.

---

### 16. AC4.4 OCA-Type Lock-Step: `bracket_oca_type=0` Threads Through Consistently

**Test:** New parametrized test `test_bracket_oca_type_0_threads_through_consistently` (S4b, parametrized × 4 OCA-thread sites). Asserts that flipping `IBKRConfig.bracket_oca_type` from 1 to 0 produces `ocaType=0` on bracket children AND on standalone-SELL OCA threading (NO divergence).

**Verified at:** S4b close-out.

**Sessions responsible:** S4b.

**Specific edges:**
- AC4.4: rollback escape hatch (RESTART-REQUIRED per DEC-386 H1) preserved.
- DEC-386 S1a + S1b OCA-threading semantics preserved: when `bracket_oca_type=0`, no OCA group is bound, but the threading code paths still execute (no conditional skipping).

---

### 17. AMD-2 Invariant Modification (Conditional on H1) Documented and Tested

**Test:** S2a updates the existing AMD-2 regression test (`test_amd2_sell_before_cancel` — Sprint 28.5 era). If S1a selects H1 (cancel-and-await): test renamed `test_amd2_modified_cancel_and_await_before_sell`, asserts `cancel_all_orders` called BEFORE `place_order(SELL)`. If S1a selects H2 (amend-stop-price): test renamed `test_amd2_preserved_with_amend_path`, asserts `modify_order` called before any SELL emission. If S1a selects H4 (hybrid): both tests retained with branching.

**Verified at:** S2a close-out. **A-class halt A10** fires if mechanism breaks DEC-117 atomic-bracket invariants.

**Sessions responsible:** S2a (modifies); S2b (preserves modification across other surfaces); S5a (validates end-to-end).

**Specific edges:**
- AMD-8 guard ("complete no-op if `_flatten_pending` already set") UNCHANGED.
- AMD-4 guard ("no-op if `shares_remaining ≤ 0`") UNCHANGED.
- AMD-2 modification documented in DEC-390 with rationale.
- RSK-DEC-390-AMEND filed at sprint-close if H2 selected.
- RSK-DEC-390-FINGERPRINT filed at sprint-close (regardless of H selection).

---

### 18. Spike Artifacts Committed and Fresh at First Post-Merge Paper Session

**Test:** Operational regression. Before the first post-Sprint-31.92-seal paper session boots, operator confirms:
- `scripts/spike-results/spike-def204-round2-path1-results.json` exists, has `status: PROCEED`, dated within 30 days.
- `scripts/spike-results/spike-def204-round2-path2-results.json` exists, has `status: PROCEED`, dated within 30 days.
- `scripts/spike-results/sprint-31.92-validation-path1.json` exists, has `path1_safe: true`, dated post-S5a-merge.
- `scripts/spike-results/sprint-31.92-validation-path2.json` exists, has `path2_suppression_works: true`, dated post-S5b-merge.

**Verified at:** Sprint-close (D14 doc-sync) AND before each subsequent paper session for 30 days post-seal. **A-class halt A13** fires if any artifact >30 days old at any future trigger event (live-transition consideration, `ib_async`/IBKR Gateway upgrade).

**Sessions responsible:** S1a (path1 spike), S1b (path2 spike), S5a (path1 validation), S5b (path2 validation + composite).

---

## Per-Session Verification Matrix

The matrix below shows which invariants each session's `@reviewer` MUST explicitly verify in the Tier 2 verdict. Cells marked ✓ are MANDATORY; cells marked ▢ are SOFT (verify if time permits, else trust the test suite).

| Invariant | S1a | S1b | S2a | S2b | S3a | S3b | S4a | S4b | S5a | S5b |
|-----------|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| 1. DEC-117 atomic bracket | ▢ | ▢ | ✓ | ✓ | ▢ | ▢ | ✓ | ✓ | ✓ | ✓ |
| 2. DEC-364 cancel_all_orders no-args ABC | ▢ | ▢ | ✓ | ✓ | ▢ | ▢ | ▢ | ▢ | ✓ | ✓ |
| 3. DEC-369 broker-confirmed immunity | ▢ | ▢ | ▢ | ▢ | ▢ | ▢ | ✓ | ▢ | ▢ | ✓ |
| 4. DEC-372 stop retry caps + backoff | ▢ | ▢ | ▢ | ✓ | ▢ | ▢ | ▢ | ▢ | ▢ | ✓ |
| 5. DEC-385 6-layer side-aware reconciliation | ▢ | ▢ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| 6. DEC-386 4-layer OCA architecture | ▢ | ▢ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| 7. DEC-388 alert observability | ▢ | ▢ | ▢ | ▢ | ▢ | ✓ | ✓ | ▢ | ▢ | ✓ |
| 8. DEF-158 3-branch side-check verbatim | ▢ | ▢ | ▢ | ▢ | ✓ | ✓ | ▢ | ▢ | ▢ | ✓ |
| 9. `# OCA-EXEMPT:` mechanism | ▢ | ▢ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| 10. Test count ≥ baseline | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| 11. Pre-existing flake count | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| 12. Frontend immutability | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| 13. SELL-volume ceiling | — | — | — | — | — | — | ✓ | ▢ | ▢ | ✓ |
| 14. Path #2 fingerprint deterministic | — | ✓ | — | — | ✓ | ✓ | — | — | — | ✓ |
| 15. `_OCA_TYPE_BRACKET` constant deleted | — | — | — | — | — | — | — | ✓ | ✓ | ✓ |
| 16. AC4.4 OCA-type lock-step | — | — | — | — | — | — | — | ✓ | — | ▢ |
| 17. AMD-2 modification (conditional) | — | — | ✓ | ✓ | — | — | — | — | ✓ | ✓ |
| 18. Spike artifacts fresh + committed | ✓ | ✓ | ▢ | ▢ | ▢ | ▢ | ▢ | ▢ | ✓ | ✓ |

**Legend:**
- ✓ = MANDATORY verification at this session's Tier 2 review.
- ▢ = SOFT verification (trust test suite unless suspicious diff).
- — = Not yet established (invariant emerges at a later session).

---

## Cross-Session Invariant Risks

The following risks span multiple sessions and must be tracked at sprint-close:

### Risk: `argus/execution/order_manager.py` Mass Modification

**Concern:** 6 of 10 sessions (S2a, S2b, S3a, S3b, S4a, S4b) modify `order_manager.py`. The file is 4,421 lines. Cumulative diff at S4b will be substantial. Tier 2 reviewers may face context-budget pressure verifying ALL 6 invariants 1–9 are preserved.

**Mitigation:**
- DEC-328 tiering keeps full suite at every close-out → automated regression catches semantic breaks.
- Per-session structural-anchor edits (protocol v1.2.0) keep diff hunks scoped.
- `git diff <session-base>..HEAD -- argus/execution/order_manager.py | wc -l` reported in every close-out for cumulative-diff tracking.
- Final review at S5b uses full suite + Tier 2 reviewer reads cumulative diff explicitly.

**Tracking:** Cumulative diff line count at each session close-out:

| Session | Expected Δ in `order_manager.py` | Cumulative Δ (bound) |
|---------|---------------------------------:|---------------------:|
| S2a | ~30–60 LOC | ~60 |
| S2b | ~40–80 LOC | ~140 |
| S3a | ~60–100 LOC (helper + dict + 2 lines on `__init__`) | ~240 |
| S3b | ~80–120 LOC (4 emit-site exception handlers + suppression-check + fallback) | ~360 |
| S4a | ~80–120 LOC (ManagedPosition field + on_fill increment + helper + 5 guards + POLICY_TABLE) | ~480 |
| S4b | ~10–20 LOC (only the 4 substitutions + constant deletion + `__init__` signature) | ~500 |

**Soft cap:** ~600 cumulative LOC for `order_manager.py` modifications. Anything beyond suggests scope creep → Tier 2 reviewer flags.

### Risk: Path #1 Mechanism Choice Cascading

**Concern:** S2a's H1/H2/H4 selection cascades into S2b (other surfaces), S5a (validation fixture), and the AMD-2 invariant modification (regression test renaming + DEC-390 documentation).

**Mitigation:**
- S2a close-out documents the chosen mechanism explicitly in a "Mechanism Selected" section.
- S2b's pre-flight reads S2a close-out + `scripts/spike-results/spike-def204-round2-path1-results.json` and asserts mechanism consistency.
- S5a's fixture is mechanism-agnostic (asserts AC1.1 `total_sold ≤ shares_total` regardless of HOW the mechanism prevents over-flatten).

**Tracking:** Sprint-close DEC-390 entry must explicitly cite the mechanism selected (not "one of H1/H2/H4" — the actual choice).

### Risk: Validation Artifact Drift

**Concern:** S5a + S5b commit JSON artifacts under `scripts/spike-results/`. If any subsequent change to `simulated_broker.py` test extensions OR to the production code paths these scripts exercise causes the artifacts to become stale, the post-merge paper-session preconditions become unverifiable.

**Mitigation:**
- Invariant 18 establishes 30-day freshness check.
- Pytest test `test_validate_path{1,2}_artifact_committed_to_repo` (S5a + S5b) asserts artifact exists at expected path with valid schema.
- Quarterly operational re-validation flagged in `docs/risk-register.md`.

**Tracking:** Sprint-close establishes baseline; sprint-history.md records artifact mtime/SHA.

---

## Adversarial Review Reference

The Adversarial Review Input Package (Phase C, artifact #8) will include this Regression Checklist verbatim. Adversarial reviewers should specifically scrutinize:

1. Whether 18 invariants is sufficient or if any A-class halt in `escalation-criteria.md` lacks a corresponding regression test invariant here.
2. Whether the per-session verification matrix correctly identifies which sessions are ✓-mandatory vs ▢-soft for invariants 5–9 (DEC-385/386/388/DEF-158/OCA-exempt).
3. Whether invariant 17 (AMD-2 modification) correctly handles all three H1/H2/H4 branches at S2a — specifically, whether H4 (hybrid) needs TWO regression tests rather than one.
4. Whether the cumulative-diff soft cap of ~600 LOC for `order_manager.py` is realistic given a 4,421-line file or needs to be tighter.
5. Whether invariant 18's 30-day artifact-freshness check is the right cadence (DEC-386 used 30 days; carrying that forward, but the failure mode is different — locate-rejection string drift is potentially less time-bounded than IBKR API behavior change).
6. Whether any DEC-385/386/388 invariant lacks adequate adversarial-review surface here (e.g., `# OCA-EXEMPT:` exemption mechanism — invariant 9 is one line; does it need more depth?).
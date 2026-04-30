# Sprint 31.92: Sprint-Level Regression Checklist

> **Phase C artifact 6/9 (revised post-Round-2-Disposition + Phase A
> Re-entry + Phase A Tier 3 + Phase B re-run).** Specific, testable items
> the `@reviewer` must verify at every Tier 2 review. Embedded into every
> implementation prompt so the implementer can self-check before close-out
> and the reviewer has explicit assertions to test against.
>
> **Revision history:** Round 1 authored 2026-04-28 with 18 invariants.
> Round-1-revised 2026-04-29: invariant 13 rewritten for pending-reservation
> pattern (C-1); invariant 14 expanded for position-keyed dict +
> broker-verification (H-2 + H-3); invariant 16 reframed as
> lock-step-not-validity (H-4); invariant 17 reframed for
> mechanism-conditional AMD-2 (C-3); NEW invariant 19 (`is_reconstructed`
> refusal); NEW invariant 20 (pending-reservation state-transition
> completeness); NEW invariant 21 (broker-verification three-branch
> coverage); NEW invariant 22 (mechanism-conditional operator-audit
> logging). Round 2 carried over to 22 invariants (no net invariant change;
> 14 dispositions distributed across existing invariants). **This Phase C
> revision (2026-04-29) adds invariants 23–27 per Phase B design summary
> § Regression Invariants and Tier 3 verdict items A–E + Decisions 3–5.**
> Total invariants: **27**.

## Critical Invariants (Must Hold After Every Session)

The 27 invariants are organized into four groups:
- **Invariants 1–9: PRESERVED FROM PRIOR SPRINTS** — DEC-117/364/369/372/385/386/388 + DEF-158 + `# OCA-EXEMPT:`.
- **Invariants 10–12: BASELINE PRESERVATION** — test count, pre-existing flake count, frontend immutability.
- **Invariants 13–22: NEW IN SPRINT 31.92 ROUND-1-REVISED** — established by AC1/AC2/AC3/AC4 (with Round-1 revisions, preserved through Round 2 and Phase A re-entry).
- **Invariants 23–27: NEW PER PHASE B RE-RUN (Tier 3 items A–E + Decisions 3–5)** — synchronous-update invariant scope extension, HALT-ENTRY coupling, Branch 4, AC2.7 auto-activation, 5 cross-layer compositions.

### 1. DEC-117 Atomic Bracket Order Placement

**Test:** `tests/execution/test_atomic_brackets.py` (existing) — parent + 2 children placed atomically; parent failure cancels children; transmit-flag semantics preserved.

**Verified at:** Every session's close-out. **Critical for:** S2a, S2b (Path #1 mechanism touches `_trail_flatten` + `_resubmit_stop_with_retry`'s emergency-flatten branch, both of which interact with bracket-stop cancellation OR amendment timing — must not regress atomic bracket invariants); S5c CL-2 explicitly stresses bracket invariants under `bracket_oca_type != 1` rollback.

**Sessions responsible:** ALL.

---

### 2. DEC-364 `cancel_all_orders()` No-Args ABC Contract

**Test:** Pre-existing regression test that asserts `Broker.cancel_all_orders()` (no args) preserves DEC-364 behavior; DEC-386 S0's positional+keyword signature is BACKWARD-COMPATIBLE (zero-arg call = original DEC-364 behavior).

**Verified at:** Every session's close-out. **Critical for:** S2a, S2b (if Path #1 mechanism uses H1 cancel-and-await fallback, calls go through this ABC; must preserve no-args semantics for any existing callers).

**Sessions responsible:** ALL.

---

### 3. DEC-369 Broker-Confirmed Reconciliation Immunity

**Test:** Pre-existing test that broker-confirmed positions (with IBKR entry fill callbacks, `oca_group_id is None`-derived from `reconstruct_from_broker`) are NOT auto-closed by reconciliation. AC3.6 + AC3.7 must compose with this: ceiling initialization for reconstruct-derived positions composes additively with DEC-369 immunity (BOTH protections apply; `is_reconstructed = True` adds a second layer of refusal, not a replacement).

**Verified at:** Every session's close-out. **Critical for:** S4a-i (ceiling initialization for `reconstruct_from_broker`-derived positions per AC3.6 + AC3.7); S5b restart-during-active-position validation.

**Sessions responsible:** ALL.

---

### 4. DEC-372 Stop Retry Caps + Exponential Backoff

**Test:** Pre-existing `test_stop_resubmission_cap` — retry attempts capped per config; backoff is 1s → 2s → 4s; emergency-flatten fires only after cap exhausted.

**Verified at:** Every session's close-out. **Critical for:** S2b (touches the emergency-flatten branch in `_resubmit_stop_with_retry`; must preserve retry-cap and backoff invariants while applying Path #1 mechanism to the emergency SELL).

**Sessions responsible:** ALL; especially S2b.

---

### 5. DEC-385 Six-Layer Side-Aware Reconciliation

**Test:** Pre-existing monotonic-safety matrix regression `test_def204_reconciliation_layers_monotonic` (Sprint 31.91 invariant 17). All 6 layers preserved byte-for-byte.

**Verified at:** Every session's close-out. **Critical for:** S3a + S3b (Path #2's broker-verified suppression-timeout fallback REUSES `phantom_short_retry_blocked` alert from DEC-385 L4 conditional on broker-verification result; must not modify the alert path itself); S5c CL-3 + Branch 4 unit test (uses the alert path under `verification_stale: true` metadata).

**Sessions responsible:** ALL; especially S3a, S3b, S5c.

**Specific edges:**
- DEF-158 retry 3-branch side-check (lines ~3424–3489) UNCHANGED — Path #2 adds upstream detection at `place_order` exception, NOT a 4th branch.
- `phantom_short_retry_blocked` SystemAlertEvent emitter unchanged in source code — Path #2's broker-verified fallback CALLS this existing emitter conditionally per AC2.5 case (c) + Branch 4.

---

### 6. DEC-386 Four-Layer OCA Architecture

**Test:** Pre-existing monotonic-safety matrix regression `test_dec386_oca_layers_preserved`. All 4 layers preserved byte-for-byte.

**Verified at:** Every session's close-out. **Critical for:** S4b (DEF-212 rider modifies `OrderManager.__init__` and the 4 OCA-thread sites; the OCA-threading SEMANTICS must remain identical — only the source of `ocaType` value changes from module constant to instance attribute).

**Sessions responsible:** ALL; especially S4b.

**Specific edges:**
- `IBKRBroker.place_bracket_order` OCA threading (DEC-386 S1a) UNCHANGED.
- `_handle_oca_already_filled` SAFE-marker path (DEC-386 S1b) UNCHANGED.
- `# OCA-EXEMPT:` exemption mechanism preserved (see invariant 9).
- `_is_oca_already_filled_error` helper UNCHANGED (relocation deferred to Sprint 31.93 per SbC §"Out of Scope" #4).
- `bracket_oca_type` Pydantic field validator UNCHANGED — runtime-flippability preserved per DEC-386 design intent (rollback escape hatch). Only the consumer side (OrderManager) gains construction-time wiring + AC4.6 dual-channel startup warning + AC4.7 `--allow-rollback` CLI gate.

---

### 7. DEC-388 Alert Observability Subsystem

**Test:** Pre-existing tests for HealthMonitor consumer + REST + WebSocket + 5-layer storage. AST policy-table exhaustiveness regression `tests/api/test_policy_table_exhaustiveness.py` updated at S4a-i to include `sell_ceiling_violation` (now 14 entries).

**Verified at:** Every session's close-out. **Critical for:** S4a-i (adds 1 new alert type `sell_ceiling_violation` and 1 new `POLICY_TABLE` entry; must preserve all 13 existing entries) and S3b (Path #2's broker-verified fallback emits `phantom_short_retry_blocked` via the existing DEC-385 path conditionally — no new emitter site at the consumer side; Branch 4 publishes the same alert with `verification_stale: true` metadata).

**Sessions responsible:** ALL; especially S4a-i, S3b.

**Specific edges:**
- `POLICY_TABLE` count: 13 (pre-S4a-i) → 14 (post-S4a-i).
- `sell_ceiling_violation` policy entry: `operator_ack_required=True`, `auto_resolution_predicate=None` (manual-ack only).
- Existing 13 policy entries unchanged.
- Branch 4 alert metadata extends but does NOT replace the existing `phantom_short_retry_blocked` policy entry.

---

### 8. DEF-158 Retry Three-Branch Side-Check Preserved Verbatim

**Test:** New regression test `test_def158_3branch_side_check_preserved_verbatim` (S3b). Asserts that `_check_flatten_pending_timeouts` lines ~3424–3489 retain the BUY → resubmit / SELL → alert+halt / unknown → halt structure UNCHANGED. Path #2's NEW detection is at the `place_order` exception in the 4 SELL emit sites, NOT inside this gate.

**Verified at:** S3b close-out specifically; reviewed at every session as a do-not-modify boundary.

**Sessions responsible:** ALL; especially S3b. **A-class halt A5** fires if violated.

---

### 9. `# OCA-EXEMPT:` Exemption Mechanism Preserved

**Test:** Pre-existing grep regression guard `test_no_sell_without_oca_when_managed_position_has_oca` from DEC-386 S1b.

**Verified at:** Every session's close-out. **Critical for:** S2a, S2b, S3b, S4a-i (any new SELL emit logic must either use OCA threading via `position.oca_group_id` OR carry an `# OCA-EXEMPT: <reason>` comment).

**Sessions responsible:** ALL.

---

### 10. Test Count Baseline Holds

**Test:** Full suite pytest count ≥ 5,269 at every close-out. Vitest count = 913 unchanged.

**Verified at:** Every session's close-out. **B-class halt B3** fires if pytest drops below baseline.

**Sessions responsible:** ALL.

**Per-session test deltas (revised per Phase B re-run):**

| Session | Pytest Δ | Vitest Δ |
|---------|---------:|---------:|
| S1a | 0 | 0 |
| S1b | 0 | 0 |
| S2a | +6 to +7 | 0 |
| S2b | +7 | 0 |
| S3a | +6 | 0 |
| S3b | +9 | 0 |
| S4a-i | +7 logical (≈9 effective) | 0 |
| S4a-ii | **+7 NEW** | 0 |
| S4b | +7 logical (≈11 effective with parametrize) | 0 |
| S5a | +4 | 0 |
| S5b | +9 logical | 0 |
| S5c | **+6 NEW** (5 CL tests + 1 Branch 4 unit test) | 0 |
| **Total range** | **+88 to +114** | **0** |

**Final target:** 5,357–5,403 pytest + 913 Vitest at S5c close-out.

---

### 11. Pre-Existing Flake Count Does Not Increase

**Test:** Run full suite at every session close-out; count failures attributable to DEF-150, DEF-167, DEF-171, DEF-190, DEF-192. Flake count ≤ baseline.

**Verified at:** Every session's close-out. **B-class halt B1** fires if any flake worsens or new flake appears.

**Sessions responsible:** ALL.

---

### 12. Frontend Immutability

**Test:** `git diff <session-base>..HEAD -- 'frontend/'` returns empty for every session. Vitest count = 913 at every close-out.

**Verified at:** Every session's close-out. **B-class halt B8** fires if violated.

**Sessions responsible:** ALL.

---

### 13. Long-Only SELL-Volume Ceiling: `cumulative_pending_sell_shares + cumulative_sold_shares + requested_qty ≤ shares_total` Per `ManagedPosition`

**Test:** New parametrized test `test_check_sell_ceiling_blocks_excess_sell_at_5_emit_sites_parametrized` (S4a-i, parametrized × 2 emit sites + S5b composite × remaining 3 emit sites + reconstructed-position refusal scenarios).

**REWRITTEN per Round-1 C-1; SCOPE EXTENDED per Tier 3 item A + B + entry #9:** Ceiling is a TWO-COUNTER reservation: `cumulative_pending_sell_shares` (incremented synchronously at place-time before `await`) + `cumulative_sold_shares` (incremented at fill). Ceiling check: `pending + sold + requested ≤ shares_total`. The race scenario (two coroutines on same `ManagedPosition`) is structurally prevented because the second coroutine's check sees the first coroutine's pending reservation. **The synchronous-update invariant extends to ALL bookkeeping mutation paths per Tier 3 entry #9 (see invariant 23 below for the AST regression infrastructure).**

**Verified at:** S4a-i close-out (2 of 5 sites parametrized + C-1 race test); S5b close-out (remaining 3 sites + composite stress test + reconstructed-position refusal); S5c CL-1 (force false-positive in `_reserve_pending_or_fail`, ceiling catches at reconciliation). **A-class halt A11** fires if false-positives observed in production paper trading.

**Sessions responsible:** S4a-i, S4a-ii (callback-path scope extension), S5b, S5c.

**Specific edges:**
- Per-`ManagedPosition`, NOT per-symbol (AC3.4).
- `reconstruct_from_broker`-derived: initialize `cumulative_pending_sell_shares = 0`, `cumulative_sold_shares = 0`, `is_reconstructed = True`, `shares_total = abs(broker_position.shares)` (AC3.6).
- Reconstructed positions refuse ALL ARGUS-emitted SELLs regardless of pending+sold+requested arithmetic (AC3.7) — early return in ceiling check before counter math.
- Config-gated: `OrderManagerConfig.long_only_sell_ceiling_enabled = false` returns True unconditionally (AC3.8).
- Increment in `on_fill` for SELL-side fills only — T1, T2, bracket stop, trail-flatten, escalation-flatten, retry-flatten, EOD-flatten, locate-released-flatten (AC3.1).
- Bracket placement EXCLUDED from ceiling check (AC3.2 + SbC §"Edge Cases to Reject" #15).
- **Stop-replacement ceiling exemption** (H-R2-5): `_check_sell_ceiling` accepts `is_stop_replacement: bool=False`; exemption permitted ONLY at `_resubmit_stop_with_retry` normal-retry path. AST callsite scan regression invariant 24 (existing) extended with reflective-pattern coverage per invariant 23.

---

### 14. Path #2 Locate-Rejection Fingerprint Deterministic + Position-Keyed Suppression + Broker-Verified Timeout

**Test:** Composite of multiple sub-tests (S3a + S3b):
1. `test_is_locate_rejection_matches_canonical_string` — exact substring captured by S1b spike, case-insensitive.
2. `test_is_locate_suppressed_position_keyed_returns_true_within_window` — keyed by `ManagedPosition.id` (ULID), NOT symbol (Round-1 H-2).
3. `test_suppression_timeout_broker_shows_*` × 3 branches — AC2.5 broker-verification three-branch coverage (Round-1 H-3).
4. **NEW per Tier 3 item C:** Branch 4 + HALT-ENTRY coupling tests (see invariants 24 + 25 below for the regression infrastructure).

**EXPANDED per Round-1 H-2 + H-3 + Tier 3 item C.**

**Verified at:** S3a close-out (sub-tests 1+2); S3b close-out (sub-test 3 broker-verification + Branch 4 + HALT-ENTRY coupling); ongoing at quarterly re-validation (RSK-DEC-390-FINGERPRINT — operational hygiene). **A-class halts A2 + A13 + B12** apply.

**Sessions responsible:** S3a (establishes); S3b (broker-verification wiring + Branch 4 + HALT-ENTRY coupling); S5b (validates against synthetic locate-rejection fixture with hold-then-release); S5c (CL-3 cross-layer composition).

**Specific edges:**
- Substring match (NOT regex unless S1b finds variants) — case-insensitive via `str(error).lower()`.
- Helper accepts `BaseException` (mirrors DEC-386's `_is_oca_already_filled_error` shape).
- Suppression dict keyed by `ManagedPosition.id` (ULID) — cross-position safety preserved.
- Broker-verification at AC2.5 timeout: 3 outcomes (broker-zero, broker-expected-long, broker-unexpected-state) + Branch 4 (`verification_stale: true`) on refresh failure.
- `Broker.refresh_positions(timeout_seconds=5.0)` is the new ABC method introduced at S3b (per C-R2-1).

---

### 15. `_OCA_TYPE_BRACKET` Module Constant Deleted

**Test:** New grep regression guard `test_no_oca_type_bracket_constant_remains_in_module` (S4b). Greps `argus/execution/order_manager.py` for the literal `_OCA_TYPE_BRACKET` and asserts ZERO matches post-S4b.

**Verified at:** S4b close-out; every subsequent session as a non-regression check. **B-class halt B11** fires if the count is wrong before S4b begins.

**Sessions responsible:** S4b (establishes); S5a, S5b, S5c (preserve).

**Specific edges:**
- Pre-S4b: 5 occurrences (1 declaration + 4 use sites).
- Post-S4b: 0 occurrences. All replaced by `self._bracket_oca_type`.
- `OrderManager.__init__` accepts `bracket_oca_type: int` keyword arg; `argus/main.py` construction site passes `config.ibkr.bracket_oca_type`.
- Absolute line numbers in spec text are DIRECTIONAL ONLY per protocol v1.2.0+; structural anchors (the constant name + the function/class names containing the use sites) bind.

---

### 16. AC4.4 OCA-Type Lock-Step (NOT Operational Validity) — `bracket_oca_type=0` Threads Through Consistently

**Test:** New parametrized test `test_bracket_oca_type_lockstep_preserved_under_rollback` (S4b, parametrized × 4 OCA-thread sites with `bracket_oca_type ∈ {0, 1}`). Asserts that flipping from 1 to 0 produces consistent `ocaType=0` on bracket children AND on standalone-SELL OCA threading (NO divergence).

**REFRAMED per Round-1 H-4:** Test affirms the lock-step PROPERTY of the DEF-212 fix; does NOT affirm `ocaType=0` as operationally valid. Test docstring explicitly: "ocaType=0 disables OCA enforcement and reopens DEF-204; this test asserts the rollback path is consistent, not that the rollback is operationally safe."

**Verified at:** S4b close-out. S5c CL-2 stresses lock-step under rollback as a cross-layer composition (verifies emergency-flatten branch still ceiling-checks even when L4 is in rollback mode).

**Sessions responsible:** S4b (establishes); S5c (cross-layer composition).

---

### 17. AMD-2 Invariant Mechanism-Conditional (H2 Preserved / H4 Mixed / H1 Superseded)

**Test:** S2a updates the existing AMD-2 regression test (`test_amd2_sell_before_cancel` — Sprint 28.5 era) per S1a-selected mechanism:
- **If H2 (default):** Existing test PRESERVED unchanged. New test `test_path1_h2_amend_called_before_any_sell_emit` asserts `modify_order` ordering. AMD-2 invariant intact.
- **If H4 (hybrid):** Parametrized over success and fallback branches; AMD-2 preserved on amend-success path; AMD-2-prime asserted on cancel-fallback path.
- **If H1 (last-resort):** Existing test renamed `test_amd2_modified_cancel_and_await_before_sell`; asserts new ordering. DEC-390 must explicitly call out H1 as last-resort with rationale. AC1.6 operator-audit logging required.

**REFRAMED per Round-1 C-3:** Mechanism-conditional framing. AMD-2 is NOT "intentionally modified" by default — it's preserved under H2 (the default). It's only superseded under H1 (last-resort) or on the H4 fallback path.

**Verified at:** S2a close-out. **A-class halt A10** fires if mechanism breaks DEC-117 atomic-bracket invariants.

**Sessions responsible:** S2a (establishes); S2b (preserves modification across other surfaces); S5a (validates end-to-end).

**Specific edges:**
- AMD-8 guard ("complete no-op if `_flatten_pending` already set") UNCHANGED across all mechanisms.
- AMD-4 guard ("no-op if `shares_remaining ≤ 0`") UNCHANGED across all mechanisms.
- AMD-2 framing (preserved/mixed/superseded) documented in DEC-390 with rationale for chosen mechanism.
- RSK-DEC-390-AMEND filed at sprint-close if H2 selected.
- RSK-DEC-390-CANCEL-AWAIT-LATENCY filed at sprint-close if H1 or H4 (with H1 fallback path possible).
- RSK-DEC-390-FINGERPRINT filed at sprint-close (regardless of mechanism selection).

---

### 18. Spike Artifacts Committed and Fresh at First Post-Merge Paper Session

**Test:** Operational regression. Before the first post-Sprint-31.92-seal paper session boots:
- `scripts/spike-results/spike-def204-round2-path1-results.json` exists, has `status: PROCEED`, dated within 30 days, includes `adversarial_axes_results`, `worst_axis_wilson_ub`, `h1_propagation_n_trials=100`, `h1_propagation_zero_conflict_in_100: bool` (per Decisions 1 + 2).
- `scripts/spike-results/spike-def204-round2-path2-results.json` exists, has `status: PROCEED`, dated within 30 days.
- `scripts/spike-results/sprint-31.92-validation-path1.json` exists, has `path1_safe: true`, dated post-S5a-merge.
- `scripts/spike-results/sprint-31.92-validation-path2.json` exists, has `path2_suppression_works: true` AND `broker_verification_at_timeout_works: true`, dated post-S5b-merge.
- `scripts/spike-results/sprint-31.92-validation-composite.json` exists, has composite-test pass criteria met, dated within 24 hours via daily CI.

**Verified at:** Sprint-close (D14 doc-sync) AND before each subsequent paper session for 30 days post-seal. **A-class halt A13** fires if any artifact >30 days old at any future trigger event (live-transition consideration, `ib_async`/IBKR Gateway upgrade).

**Sessions responsible:** S1a (path1 spike), S1b (path2 spike), S5a (path1 validation), S5b (path2 + composite validation), S5c (cross-layer + Branch 4).

---

### 19. (NEW per Round-1 C-2) `is_reconstructed = True` Refusal Posture Holds for All ARGUS-Emitted SELL Paths

**Test:** New regression test `test_restart_during_active_position_refuses_argus_sells` (S5b, AC5.4) — fixture: spawn ManagedPosition normally, partial-fill via T1, simulate restart by calling `reconstruct_from_broker()` (or directly setting `is_reconstructed=True` if test architecture requires), assert subsequent `_trail_flatten`, `_flatten_position`, `_check_flatten_pending_timeouts`, `_escalation_update_stop` invocations all refuse to emit SELL.

**Plus** unit-level `test_reconstruct_from_broker_initializes_is_reconstructed_true_and_zero_counters` (S5b) — asserts the single-line addition in `reconstruct_from_broker` correctly sets the flag.

**Verified at:** S5b close-out. **A-class halts A15 + A16** fire if violated in test OR in production paper trading.

**Sessions responsible:** S4a-i (establishes the field + ceiling-check short-circuit); S5b (regression test for refusal posture across all 4 standalone-SELL paths).

**Specific edges:**
- Field is in-memory only (NOT persisted to SQLite).
- Set ONLY in `reconstruct_from_broker` (single-line addition allowed inside the function body per SbC §"Do NOT modify").
- Refusal applies to ARGUS-emitted SELLs ONLY; operator-manual flatten via `scripts/ibkr_close_all_positions.py` is the only closing mechanism until Sprint 31.94 D3.
- RSK-RECONSTRUCTED-POSITION-DEGRADATION rated **MEDIUM-HIGH** per Severity Calibration Rubric (operator daily-flatten empirically failed Apr 28 — 27 of 87 ORPHAN-SHORT detections from a missed run; per H-R2-3). Sprint Abort Condition #7 trigger lowered from 4 weeks to 2 weeks. Time-bounded by Sprint 31.94 D3.

---

### 20. (NEW per Round-1 C-1) Pending-Reservation State-Transition Completeness

**Test:** Composite of S4a-i unit tests covering all 5 state transitions enumerated in AC3.1:
- `test_cumulative_pending_increments_synchronously_before_await` — asserts pending counter incremented BEFORE the `await place_order(...)` yield-point (the synchronous-before-await invariant is the architectural correctness contract).
- `test_cumulative_pending_decrements_on_cancel_reject` — order rejected/cancelled in `place_order` exception handler OR `cancel_order` confirmation: pending decrements.
- `test_cumulative_pending_transfers_to_sold_on_partial_fill` — partial fill: pending decrements by `filled_qty`, sold increments by `filled_qty`; remainder stays in pending.
- `test_cumulative_pending_transfers_to_sold_on_full_fill` — full fill: pending decrements by remaining, sold increments by remaining.
- `test_concurrent_sell_emit_race_blocked_by_pending_reservation` — **CANONICAL C-1 RACE TEST** (AC3.5).

**Verified at:** S4a-i close-out specifically; S4a-ii extends with AST-level regression (see invariant 23); S5b composite re-exercises in integration. **A-class halt A11** fires if any state transition leaks or under-decrements (e.g., pending counter drifts upward over session).

**Sessions responsible:** S4a-i (establishes all 5 state transitions); S4a-ii (AST-level regression scope extension to all bookkeeping callback paths); S5b (integration verification under load).

**Specific edges:**
- `cumulative_pending_sell_shares` is in-memory only (NOT persisted; per SbC §"Out of Scope" #21 — DEF-209 deferred).
- Synchronous-before-await ordering in code is load-bearing; reviewer must inspect diff for ordering violations.
- Cancel/reject paths must decrement (not just the success/fill paths).
- The H-R2-1 atomic `_reserve_pending_or_fail()` synchronous method is the place-time entry point; invariant 23 extends the AST guard to all other bookkeeping callbacks.

---

### 21. (NEW per Round-1 H-3) Broker-Verification Three-Branch Coverage at Suppression Timeout

**Test:** Three S3b tests covering AC2.5's three branches (post-refresh-success):
- `test_suppression_timeout_broker_shows_zero_logs_info_no_alert` — broker returns no entry for symbol; INFO log; no alert.
- `test_suppression_timeout_broker_shows_expected_long_logs_info_no_alert` — broker returns BUY-side entry with shares ≥ `position.shares_remaining`; INFO log; no alert.
- `test_suppression_timeout_broker_shows_unexpected_state_emits_alert` — broker returns short OR quantity divergence OR unknown side; publishes `phantom_short_retry_blocked` per DEC-385.

**Plus** Branch 4 / refresh-failure regression (see invariant 25 below for the dedicated Branch 4 invariant + HALT-ENTRY coupling per Tier 3 item C).

**Verified at:** S3b close-out. **A-class halt B12** fires if broker-verification logic fails in test OR production.

**Sessions responsible:** S3b.

**Specific edges:**
- Helper logic lives inline in `_check_flatten_pending_timeouts` housekeeping loop OR as a private method on OrderManager (NOT a new module — per SbC §"Do NOT add").
- `Broker.refresh_positions(timeout_seconds=5.0)` is the new ABC method introduced at S3b (per C-R2-1) and called BEFORE `broker.get_positions()`.
- `broker.get_positions()` call latency budget ≤ 200ms p95 per Performance Benchmarks; full refresh-then-verify path budgeted at ≤ 5.2s p95 worst case.
- Verification-failure fallback path (Branch 4) must NOT silently absorb the alert — operator-triage signal preserved via `verification_stale: true` metadata flag (see invariant 25).

---

### 22. (NEW per Round-1 C-3) Mechanism-Conditional Operator-Audit Logging Per AC1.6

**Test:** Conditional regression test (only if H1 or H4 selected at S1a):
- `test_path1_operator_audit_log_emitted_on_amd2_supersede` — asserts structured log line with required keys (`event`, `symbol`, `position_id`, `mechanism`, `cancel_propagation_ms`) fires when mechanism dispatches to H1 cancel-and-await branch (either as last-resort under H1 OR as fallback under H4).

**Verified at:** S2a close-out (if H1 or H4 selected); S2b close-out (extends to emergency-flatten branch).

**Sessions responsible:** S2a, S2b (conditional on S1a selection).

**Specific edges:**
- Log line must use canonical structured-log format (the existing ARGUS logger pipeline) — operator-visible.
- `mechanism` field discriminates `"h1_cancel_and_await"` (last-resort) from `"h4_fallback"` (hybrid fallback path).
- If H2 selected (default), this invariant is N/A — no AMD-2 supersede event ever fires.

---

### 23. (NEW per Tier 3 item A + B + Decision 3) Synchronous-Update Invariant on All Bookkeeping Callback Paths + Reflective-Pattern AST Coverage

**Test:** New regression file `tests/execution/order_manager/test_def204_callback_atomicity.py` (~120 LOC, 7 tests, S4a-ii):

- `test_no_await_in_reserve_pending_or_fail_body` — AST-no-await scan on `_reserve_pending_or_fail`. Reference implementation pattern (from S4a-i invariant 13 / 20).
- `test_no_await_between_bookkeeping_read_and_write_in_on_fill` — AST-no-await scan on `on_fill` partial-fill transfer path AND full-fill transfer path. Asserts `cumulative_pending_sell_shares` decrement and `cumulative_sold_shares` increment occur synchronously between the read and the write — no `await` between.
- `test_no_await_between_decrement_in_on_cancel` — AST-no-await scan on `on_cancel` decrement path.
- `test_no_await_between_decrement_in_on_reject` — AST-no-await scan on `on_reject` decrement path.
- `test_no_await_in_on_order_status_bookkeeping_mutations` — AST-no-await scan on `_on_order_status` paths that mutate `cumulative_pending_sell_shares` or `cumulative_sold_shares`.
- `test_no_await_in_check_sell_ceiling_multi_attribute_read` — AST-no-await scan on `_check_sell_ceiling`'s multi-attribute read sequence (the read of `cumulative_pending_sell_shares` + `cumulative_sold_shares` + `shares_total` + `is_reconstructed` must happen without an intervening `await`).
- **Plus** mocked-await injection regression: monkey-patch each path to insert `await asyncio.sleep(0)` between read and write; assert the race IS observable under injection.

**Plus** the H-R2-5 reflective-pattern sub-tests on AST callsite scan (existing invariant 24 reframed as AST guard for `is_stop_replacement=True` callers). Three reflective-pattern coverage tests (FAI #8 option (a) per Decision 3):
- `test_ast_callsite_scan_catches_kw_unpacking` — synthetic call site `_check_sell_ceiling(**{"is_stop_replacement": True, ...})`; AST scan must flag.
- `test_ast_callsite_scan_catches_computed_value_flag_assignment` — synthetic call site `flag = compute_flag(); _check_sell_ceiling(is_stop_replacement=flag)`; AST scan must flag.
- `test_ast_callsite_scan_catches_getattr_reflective_access` — synthetic call site `getattr(om, '_check_sell_ceiling')(is_stop_replacement=True)`; AST scan must flag.

**REWRITTEN per Tier 3 items A + B + Decision 3 / FAI entries #8 + #9:** The H-R2-1 atomic-reserve protection pattern is the reference implementation; the same AST guard + injection test apply to every callback path that mutates the bookkeeping counters. The L3 ceiling correctness depends on the asyncio single-event-loop guarantee applying to every path that mutates these counters, not only `_reserve_pending_or_fail`. Reflective-call coverage closes FAI #8.

**Verified at:** S4a-ii close-out. **A-class halt A11** fires if false-positives in production paper trading trace to a callback-path leak (i.e., the callback-path AST guard caught nothing in test but production exhibited a race).

**Sessions responsible:** S4a-ii (establishes the AST regression infrastructure + reflective-pattern coverage); S4a-i (establishes the reference implementation in `_reserve_pending_or_fail`); S5b (integration stress under load); S5c CL-1 (cross-layer composition: force `_reserve_pending_or_fail` false-positive, ceiling catches at reconciliation).

**Specific edges:**
- Preferred outcome of S4a-ii is **zero production-code change** with the test file establishing the regression guard. If static-analysis reveals an existing await between bookkeeping read and write, fix is in-scope for S4a-ii.
- Decision 3 explicitly chose option (a) over option (b) (accept-and-document NOT taken).
- DEF-FAI-CALLBACK-ATOMICITY (Tier 3 verdict; sprint-gating Round 3 advancement) — closure of this DEF requires invariant 23 to be active and green at S4a-ii close-out.
- DEF-FAI-8-OPTION-A (Tier 3 verdict; Sprint 31.92 S4a-ii) — closure requires the 3 reflective-pattern sub-tests above to be active and green.

---

### 24. (NEW per Tier 3 item C) `halt_entry_until_operator_ack=True` Posture Fires Under H1 Active + Refresh Failure

**Test:** New regression tests in `tests/execution/order_manager/test_def204_round2_path2.py` (extended at S3b):

- `test_halt_entry_fires_under_h1_active_and_refresh_timeout` — with H1 selected as active mechanism (mock `selected_mechanism="h1_cancel_and_await"`) AND `Broker.refresh_positions()` raising `asyncio.TimeoutError`, assert `position.halt_entry_until_operator_ack == True` after Branch 4 fires.
- `test_halt_entry_fires_under_h1_active_and_refresh_raises` — same but `refresh_positions()` raises arbitrary exception (e.g., `ConnectionError`).
- `test_halt_entry_does_NOT_fire_under_h2_active_and_refresh_timeout` — with H2 selected, refresh failure publishes Branch 4 alert with `verification_stale: true` metadata BUT does NOT mark `halt_entry_until_operator_ack`. (H1-specific coupling per Tier 3 item C.)
- `test_halt_entry_does_NOT_fire_under_h4_amend_success_and_refresh_timeout` — with H4 selected and amend-success path active, refresh failure does NOT mark halt-entry.
- `test_halt_entry_blocks_subsequent_sell_attempts_on_position` — once `halt_entry_until_operator_ack=True` is set, all subsequent `_trail_flatten`, `_flatten_position`, `_check_flatten_pending_timeouts`, `_escalation_update_stop` invocations on the position refuse to emit SELL.

**NEW per Tier 3 item C / C-R2-1↔H-R2-2 coupling:** Without this coupling, FAI #2 + FAI #5 compound when H1 is selected against a stale broker cache. The HALT-ENTRY posture is the structural defense.

**Verified at:** S3b close-out. **A-class halt A17** fires if Branch 4 fires + H1 active without HALT-ENTRY firing in test OR in production.

**Sessions responsible:** S3b (establishes); S5c CL-3 (cross-layer composition: force refresh timeout AND H1 selection; verify HALT-ENTRY catches the composite using `SimulatedBrokerWithRefreshTimeout` fixture).

**Specific edges:**
- `position.halt_entry_until_operator_ack: bool = False` is a NEW in-memory `ManagedPosition` field (4th field added by this sprint; threading documented in S3b).
- Operator-driven resolution: no automatic recovery; operator must explicitly clear the flag (out-of-scope for Sprint 31.92 — operator-manual via existing administrative path).
- No further SELL attempts on the position; no phantom short.
- AC2.5 Branch 4 always publishes the `phantom_short_retry_blocked` alert with `verification_stale: true` metadata — the HALT-ENTRY posture is an additional state mutation conditional on H1 active.

---

### 25. (NEW per Tier 3 item E + Decision 5) Branch 4 (`verification_stale: true`) Fires on `Broker.refresh_positions()` Failure + `SimulatedBrokerWithRefreshTimeout` Fixture Coverage

**Test:** Two test paths cover Branch 4:

1. **Direct unit test** in `tests/integration/test_def204_round2_validation.py` (S5c, ~1 test using fixture):
   - `test_branch_4_fires_on_refresh_timeout_with_simulated_fixture` — uses `SimulatedBrokerWithRefreshTimeout` from `tests/integration/conftest_refresh_timeout.py`. Assert: when `refresh_positions()` exceeds `timeout_seconds`, alert is published with `verification_stale: True` metadata + `verification_failure_reason: "TimeoutError"` + `position_id` + `symbol`. Locate-suppression dict entry for the position is NOT cleared.
2. **Cross-layer composition** CL-3 (see invariant 27).

**NEW per Tier 3 item E + Decision 5 / DEF-SIM-BROKER-TIMEOUT-FIXTURE:** Currently `SimulatedBroker.refresh_positions()` is no-op or instant-success; in-process tests cannot exercise Branch 4 without the fixture variant. The `SimulatedBrokerWithRefreshTimeout` fixture (S5c, `tests/integration/conftest_refresh_timeout.py`, ~80 LOC) subclasses `SimulatedBroker` and overrides `refresh_positions()` to raise `asyncio.TimeoutError` after a configurable delay.

**Verified at:** S5c close-out. **B-class halt B12** fires if Branch 4 fails to emit OR emits with wrong metadata.

**Sessions responsible:** S3b (establishes Branch 4 logic in production code per AC2.5); S5c (establishes the fixture + the dedicated Branch 4 unit test); S5c CL-3 (cross-layer composition).

**Specific edges:**
- The fixture lives ONLY in test code (`tests/integration/conftest_refresh_timeout.py`). Production `SimulatedBroker` is NOT modified (preserves SbC §"Do NOT modify" #2).
- Fixture is held to ≤80 LOC to avoid the large-file compaction penalty per S5c scoring.
- DEF-SIM-BROKER-TIMEOUT-FIXTURE (Tier 3 verdict; Sprint 31.92 S5c) — closure of this DEF requires this invariant active and green at S5c close-out.

---

### 26. (NEW per Decision 4) AC2.7 `_pending_sell_age_seconds` Watchdog Auto-Activation From `auto` to `enabled` on First `case_a_in_production` Event

**Test:** S3a + S4a-i regression tests in `tests/execution/order_manager/test_def204_round2_path2.py` and (state-transition test) in `tests/execution/order_manager/test_def204_round2_ceiling.py`:

- `test_pending_sell_age_watchdog_enabled_field_pydantic_validation` — `OrderManagerConfig.pending_sell_age_watchdog_enabled` accepts `"auto"`, `"enabled"`, `"disabled"` values; rejects others.
- `test_pending_sell_age_watchdog_default_is_auto` — config default is `"auto"`.
- `test_pending_sell_age_watchdog_auto_flips_to_enabled_on_case_a_event` — synthetic `case_a_in_production` event (production paper-session emit) flips the runtime state from `auto` to `enabled`. Recorded for sprint-close pre-live transition checklist (see C9 in `doc-update-checklist.md`).
- `test_pending_sell_age_watchdog_disabled_does_not_fire` — when set to `disabled`, watchdog does not fire even on aged pending positions.
- `test_pending_sell_age_watchdog_enabled_fires_on_aged_pending` — when set to `enabled`, watchdog fires when `now - position.last_sell_emit_time > pending_sell_age_seconds` AND no fill observed.

**NEW per Decision 4 (M-R2-1 strengthening):** The watchdog provides the structural fallback for any unmodeled locate-rejection string variant (FAI #4 mitigation). `auto` mode flips to `enabled` on first observed `case_a_in_production` event — NOT manual operator activation per Decision 4.

**Verified at:** S3a close-out (Pydantic field validation); S4a-i close-out (auto-activation logic); production observation post-merge (informational A-class trigger A18 — see escalation criteria).

**Sessions responsible:** S3a (establishes Pydantic field); S4a-i (establishes auto-activation logic).

**Specific edges:**
- Field default `"auto"` is fail-conservative — if the operator never touches the config, the watchdog activates on first need.
- Auto-flip is a one-way state transition (auto → enabled); no auto-deactivation. Operator must manually flip back to `disabled` if desired.
- Auto-flip event is logged as a structured INFO log line (operator-visible) AND recorded as runtime state for pre-live-transition checklist purposes.

---

### 27. (NEW per Decision 5) 5 Cross-Layer Composition Invariants — CL-1 through CL-5

**Test:** 5 cross-layer composition tests in `tests/integration/test_def204_round2_validation.py` (extended at S5c, ~5 tests + 1 Branch 4 unit test from invariant 25 = 6 net new tests at S5c). Each test by definition slow + ugly + spans multiple modules per `templates/sprint-spec.md` v1.2.0 § Defense-in-Depth Cross-Layer Composition Tests.

The 5 tests:

1. **CL-1 (L1 fails → L3 catches):** `test_l1_reserve_false_positive_caught_by_l3_ceiling` — Force `_reserve_pending_or_fail` false positive (mock the synchronous method to return True even when the ceiling would be exceeded). Verify the ceiling-violation invariant catches at reconciliation; locate-suppression-with-broker-verification alert path fires.

2. **CL-2 (L4 fails → L2 catches):** `test_l4_rollback_does_not_disable_l2_ceiling_on_emergency_flatten` — Force startup with `bracket_oca_type != 1` AND `--allow-rollback` (the operator-confirmed rollback path). Verify under DEC-386 rollback that the emergency-flatten branch (Layer 2 via `is_stop_replacement=False`) still ceiling-checks; this proves Layer 2 doesn't depend on Layer 4's enforcement.

3. **CL-3 (L3 + L5 cross-falsification — FAI #2 + #5 + Tier 3 item C):** `test_h1_active_plus_refresh_timeout_caught_by_halt_entry` — Force `Broker.refresh_positions()` timeout (using `SimulatedBrokerWithRefreshTimeout` fixture per invariant 25 / DEF-SIM-BROKER-TIMEOUT-FIXTURE) AND H1 selection by S1a output. Verify the H-R2-2 HALT-ENTRY posture catches the composite — position marked `halt_entry_until_operator_ack=True`; no further SELL attempts; no phantom short.

4. **CL-4 (L1 + L2; NEW per Tier 3 sub-area D):** `test_misclassified_stop_replacement_caught_by_l3_ceiling` — Reservation succeeds but `is_stop_replacement` decision is wrong (e.g., emergency-flatten misclassified as stop-replacement); verify L3 ceiling catches the resulting over-flatten.

5. **CL-5 (L2 + L3; NEW per Tier 3 sub-area D):** `test_protective_stop_replacement_with_locate_suppression_does_not_false_fire_branch_4` — `is_stop_replacement` correctly disambiguates a stop-replacement (L2 grants exemption) AND locate-suppression for the position is active. Verify the protective stop-replacement path is allowed AND that Branch 4 does not falsely fire on it.

**CL-6 (rollback + locate-suppression interaction) is OUT of scope per Decision 5** — deferred with rationale documented in `docs/process-evolution.md`. L4's compositions with runtime layers (other than CL-2) are weakly meaningful in the operationally-relevant case; the trade-off between exhaustive coverage and bounded session count was resolved in favor of bounded scope at this sprint.

**NEW per Decision 5 + Tier 3 item E:** Per `templates/sprint-spec.md` v1.2.0 (mandatory when DEC entries claim N≥3 layer defense), DEC-390's 4-layer structure activates the cross-layer requirement. Sprint 31.92 commits to 5 tests (above the template's "at least one" floor; above Tier 3's 3-test floor).

**Verified at:** S5c close-out. **A-class halt A17** triggers on CL-3 failure specifically (sub-class of "Branch 4 fires + H1 active without HALT-ENTRY firing"). General CL-1/CL-2/CL-4/CL-5 failure surfaces via Tier 2 verdict at S5c.

**Sessions responsible:** S5c (establishes all 5 tests).

**Specific edges:**
- CL-3 uses the `SimulatedBrokerWithRefreshTimeout` fixture per invariant 25.
- CL-2 stresses bracket atomic invariants under L4 rollback (composes with invariants 1 + 6 + 16).
- CL-5 must explicitly verify Branch 4 does NOT fire on a legitimate stop-replacement path (no false-positive in cross-layer composition).
- DEF-CROSS-LAYER-EXPANSION (Tier 3 verdict; Sprint 31.92 — 5 CL tests delivered, CL-6 deferred) — closure requires this invariant active and green at S5c close-out.
- Cross-layer tests are typically slow, ugly, and span multiple modules. That is the cost of catching composition failures structurally rather than relying on per-layer tests alone.

---

### 28. (NEW per Round 3 C-R3-1) `Broker.refresh_positions()` Body Wrapped in Single-Flight `asyncio.Lock` + 250ms Coalesce Window

**Test:** `tests/execution/test_ibkr_broker_concurrent_callers.py` (NEW file at S3b) exercises N=20 concurrent coroutines calling `IBKRBroker.refresh_positions()` near-simultaneously (≤10ms separation) with mocked-await injection between A's `reqPositions()` and B's `reqPositions()` and a deterministic broker-state-change between callers; asserts the race IS observable WITHOUT the single-flight serialization mitigation AND is NOT observable WITH the mitigation enabled.

**Verified at:** S3b close-out (sub-spike for FAI #10) AND S5c CL-7 (cross-layer composition).

**Sessions responsible:** S3b (establishes the single-flight wrapper + concurrent-caller regression test); S5c (extends with CL-7 cross-layer composition).

**Specific edges:**
- The 250ms coalesce window is bounded; coroutine B that arrives more than 250ms after coroutine A's cache-synchronization timestamp performs its own broker round-trip rather than coalescing.
- Coalesce window applies only to successive callers within the window; concurrent callers at the same instant serialize via the lock.
- Sprint Abort Condition (NEW per Round 3 C-R3-1) fires if Fix A spike fails AND no alternative serialization design surfaces.

---

### 29. (NEW per Round 3 H-R3-5) Bookkeeping Callsite-Enumeration AST Exhaustiveness

**Test:** `test_bookkeeping_callsite_enumeration_exhaustive` (S4a-ii regression scope, ~40 LOC) — AST scan walks `OrderManager`'s source for `ast.AugAssign` nodes targeting `cumulative_pending_sell_shares` or `cumulative_sold_shares`; finds the enclosing function name for each; asserts the set of enclosing functions is a subset of the FAI #9 protected callsite list (`_reserve_pending_or_fail`, `on_fill`, `on_cancel`, `on_reject`, `_on_order_status`, `_check_sell_ceiling` multi-attribute read, `reconstruct_from_broker` initialization). Falsifies if a mutation site exists outside the expected list.

**Verified at:** S4a-ii close-out.

**Sessions responsible:** S4a-ii.

**Specific edges:**
- FAI #11 falsification gate: the test must fail when a new mutation site is introduced that isn't added to the FAI #9 protected list.
- Resolution if falsified: extend the FAI #9 protected scope to include the discovered callsite (preferred) or document the coverage gap with explicit rationale.

---

### 30. (NEW per Round 3 M-R3-4) `refresh_positions`-then-`get_positions` Helper + AST-No-Await Scan Extension

**Test:** AST-no-await scan extended to `_read_positions_post_refresh()` helper body at S4a-ii — asserts no `ast.Await` between `refresh_positions` invocation completion and `get_positions` cache read. Per M-R3-4 fix shape, the helper composes both calls into a single synchronous read-after-refresh sequence, removing yield-gap-between-refresh-and-read class of races.

**Verified at:** S4a-ii close-out.

**Sessions responsible:** S3b (introduces helper at AC2.5 fallback site); S4a-ii (AST-no-await scan extension).

**Specific edges:**
- The helper is the single entry point for all refresh-then-read sequences in OrderManager; AC2.5 fallback paths use it instead of calling the two-step sequence directly.
- Performance budget per spec § Performance Benchmarks: ≤5µs per-call overhead.

---

### 31. (NEW per Round 3 H-R3-1) `time.monotonic()` at All Suppression-Timeout Sites

**Test:** `test_locate_suppression_resilient_to_wall_clock_skew` (S3b regression scope) — fixture sets up locate-suppression entry, then advances synthetic wall-clock by injecting a backwards jump (e.g., NTP correction during session), then asserts suppression-timeout calculation correctly reflects monotonic time elapsed rather than wall-clock delta.

**Verified at:** S3b close-out (test fixture); ongoing CI green.

**Sessions responsible:** S3b (introduces `time.monotonic()` at all 4 standalone-SELL exception handlers + AC2.5 timeout-check site).

**Specific edges:**
- All 4 standalone-SELL exception handlers + the AC2.5 timeout-check site use `time.monotonic()`, not `time.time()`.
- `OrderManagerConfig.locate_suppression_seconds` validator footnote per § 7.1 Config Changes: bounds (300–86400) are seconds in monotonic time; equivalent to wall-clock under normal operation.

---

### 32. (NEW per Round 3 H-R3-3) RiskManager Check 0 Halt-Entry Extension + Ack Mechanism

**Test:** Two regression tests at S3b:
- `test_risk_manager_check0_rejects_when_halt_entry_set` — instantiate ManagedPosition with `halt_entry_until_operator_ack=True`; emit entry signal for the SAME `ManagedPosition.id`; assert RiskManager rejects via Check 0 with reason="halt_entry_set"; assert per-position granularity preserved (new positions on same symbol unaffected).
- `test_clear_halt_endpoint_requires_position_id_and_clears_flag` — call `POST /api/v1/positions/{position_id}/clear_halt` with valid + invalid position IDs; assert valid clears the flag and emits `event="halt_entry_cleared"` log; invalid returns 404.

**Verified at:** S3b close-out.

**Sessions responsible:** S3b (extends RiskManager Check 0); separate sub-session within S3b implements the REST endpoint + CLI tool (`scripts/clear_position_halt.py`).

**Specific edges:**
- Per AC2.8: halt-entry flag does NOT survive restart; `is_reconstructed=True` posture (AC3.7) subsumes halt-entry by refusing ALL ARGUS-emitted SELLs on reconstructed positions.
- Per-position granularity: only the SAME `ManagedPosition.id` is affected; new positions on the same symbol bypass the halt.

---

### 33. (NEW per Round 3 H-R3-4) Interactive Ack at Startup + CI-Override Flag Separation

**Test:** Three regression tests at S4b:
- `test_startup_interactive_ack_required_when_rollback_active_and_tty` — instantiate ARGUS startup with `bracket_oca_type=0` AND `--allow-rollback` AND TTY-detected; mock stdin to provide exact phrase "I ACKNOWLEDGE ROLLBACK ACTIVE"; assert ARGUS proceeds.
- `test_startup_exits_3_when_rollback_active_and_tty_and_wrong_phrase` — same setup with stdin providing wrong phrase; assert exit code 3.
- `test_startup_skip_confirm_flag_bypasses_interactive_ack_for_ci` — `--allow-rollback-skip-confirm` flag present + `bracket_oca_type=0` + `--allow-rollback` flag present; assert ARGUS proceeds without prompt; assert canonical-logger CRITICAL emission still fires (CI evidence trail preserved).

**Verified at:** S4b close-out.

**Sessions responsible:** S4b.

**Specific edges:**
- Per Round 3 H-R3-4: `--allow-rollback-skip-confirm` is separate from `--allow-rollback`; production startup MUST require interactive ack (per SbC §19, NEW).
- Periodic re-ack every 4 hours: separate test (`test_periodic_reack_emits_every_4h_when_rollback_active`) verified via mock-time advance.

---

### 34. (NEW per Round 3 M-R3-2) Branch 4 Alert Throttling — 1-Hour Per-Position Cooldown

**Test:** `test_branch_4_throttle_one_per_hour_per_position` (S3b regression scope) — fire Branch 4 twice on the same `ManagedPosition.id` within 1-hour window; assert first firing publishes `phantom_short_retry_blocked` alert; second firing is suppressed at alert layer (logged INFO with `branch_4_throttled: true`); assert HALT-ENTRY effect persists across both firings; advance synthetic clock past 1-hour window AND fire third Branch 4; assert third firing publishes alert again.

**Verified at:** S3b close-out.

**Sessions responsible:** S3b (introduces Branch 4 throttle).

**Specific edges:**
- Throttle resets on `on_position_closed` OR successful refresh observation (whichever fires first).
- Throttling is at alert layer only — HALT-ENTRY effect persists; the throttle does NOT silently drop the safety property.

---

**Total invariants:** 27 (Round 2 baseline) + 7 (Round 3) = **34**.

---

## Per-Session Verification Matrix

The matrix below shows which invariants each session's `@reviewer` MUST explicitly verify in the Tier 2 verdict. **13 sessions total** (was 10 pre-Tier-3): S1a + S1b spikes; S2a + S2b Path #1; S3a + S3b Path #2; S4a-i + S4a-ii (split per Tier 3 items A + B); S4b DEF-212 rider; S5a + S5b validation; S5c (NEW per Decision 5 + Tier 3 item E).

| Invariant | S1a | S1b | S2a | S2b | S3a | S3b | S4a-i | S4a-ii | S4b | S5a | S5b | S5c |
|-----------|:---:|:---:|:---:|:---:|:---:|:---:|:-----:|:------:|:---:|:---:|:---:|:---:|
| 1. DEC-117 atomic bracket | ▢ | ▢ | ✓ | ✓ | ▢ | ▢ | ✓ | ▢ | ✓ | ✓ | ✓ | ✓ |
| 2. DEC-364 cancel_all_orders no-args ABC | ▢ | ▢ | ✓ | ✓ | ▢ | ▢ | ▢ | ▢ | ▢ | ✓ | ✓ | ▢ |
| 3. DEC-369 broker-confirmed immunity | ▢ | ▢ | ▢ | ▢ | ▢ | ▢ | ✓ | ▢ | ▢ | ▢ | ✓ | ▢ |
| 4. DEC-372 stop retry caps + backoff | ▢ | ▢ | ▢ | ✓ | ▢ | ▢ | ▢ | ▢ | ▢ | ▢ | ✓ | ▢ |
| 5. DEC-385 6-layer side-aware reconciliation | ▢ | ▢ | ✓ | ✓ | ✓ | ✓ | ✓ | ▢ | ✓ | ✓ | ✓ | ✓ |
| 6. DEC-386 4-layer OCA architecture | ▢ | ▢ | ✓ | ✓ | ✓ | ✓ | ✓ | ▢ | ✓ | ✓ | ✓ | ✓ |
| 7. DEC-388 alert observability | ▢ | ▢ | ▢ | ▢ | ▢ | ✓ | ✓ | ▢ | ▢ | ▢ | ✓ | ✓ |
| 8. DEF-158 3-branch side-check verbatim | ▢ | ▢ | ▢ | ▢ | ✓ | ✓ | ▢ | ▢ | ▢ | ▢ | ✓ | ▢ |
| 9. `# OCA-EXEMPT:` mechanism | ▢ | ▢ | ✓ | ✓ | ✓ | ✓ | ✓ | ▢ | ✓ | ✓ | ✓ | ✓ |
| 10. Test count ≥ baseline | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| 11. Pre-existing flake count | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| 12. Frontend immutability | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| 13. SELL-volume ceiling (pending+sold pattern) | — | — | — | — | — | — | ✓ | ✓ | ▢ | ▢ | ✓ | ✓ |
| 14. Path #2 fingerprint + position-keyed dict + broker-verification | — | ✓ | — | — | ✓ | ✓ | — | — | — | — | ✓ | ✓ |
| 15. `_OCA_TYPE_BRACKET` constant deleted | — | — | — | — | — | — | — | — | ✓ | ✓ | ✓ | ✓ |
| 16. AC4.4 OCA-type lock-step (not validity) | — | — | — | — | — | — | — | — | ✓ | — | ▢ | ✓ |
| 17. AMD-2 mechanism-conditional | — | — | ✓ | ✓ | — | — | — | — | — | ✓ | ✓ | ▢ |
| 18. Spike artifacts fresh + committed | ✓ | ✓ | ▢ | ▢ | ▢ | ▢ | ▢ | ▢ | ▢ | ✓ | ✓ | ✓ |
| 19. `is_reconstructed` refusal posture | — | — | — | — | — | — | ✓ | ▢ | ▢ | ▢ | ✓ | ▢ |
| 20. Pending-reservation state transitions | — | — | — | — | — | — | ✓ | ✓ | ▢ | ▢ | ✓ | ▢ |
| 21. Broker-verification three-branch | — | — | — | — | — | ✓ | ▢ | ▢ | ▢ | ▢ | ✓ | ✓ |
| 22. Operator-audit logging (conditional) | — | — | ✓¹ | ✓¹ | — | — | — | — | — | ✓¹ | ✓¹ | ▢¹ |
| 23. **(NEW)** Synchronous-update invariant on all bookkeeping callback paths + reflective-pattern AST | — | — | — | — | — | — | ▢ | ✓ | ▢ | ▢ | ✓ | ✓ |
| 24. **(NEW)** `halt_entry_until_operator_ack=True` posture under H1 + refresh fail | — | — | — | — | — | ✓ | — | — | — | — | ▢ | ✓ |
| 25. **(NEW)** Branch 4 (`verification_stale: true`) + `SimulatedBrokerWithRefreshTimeout` fixture | — | — | — | — | — | ✓ | — | — | — | — | ▢ | ✓ |
| 26. **(NEW)** AC2.7 watchdog auto-activation (`auto` → `enabled` on first `case_a_in_production`) | — | — | — | — | ✓ | — | ✓ | — | — | — | ▢ | ▢ |
| 27. **(NEW)** 5 Cross-Layer Composition tests (CL-1 through CL-5) | — | — | — | — | — | — | — | — | — | — | — | ✓ |

**Legend:**
- ✓ = MANDATORY verification at this session's Tier 2 review.
- ▢ = SOFT verification (trust test suite unless suspicious diff).
- — = Not yet established.
- ✓¹ = MANDATORY only if S1a selected H1 or H4 (otherwise N/A).
- ▢¹ = SOFT verification, conditional on H1 or H4 selection.

---

## Cross-Session Invariant Risks

### Risk: `argus/execution/order_manager.py` Mass Modification

**Concern:** 8 of 13 sessions modify `order_manager.py` (S2a/S2b/S3a/S3b/S4a-i/S4a-ii/S4b/S5c). Cumulative diff at S5c will be substantial.

**Mitigation (revised per Round-1 + Tier 3):**
- DEC-328 tiering keeps full suite at every close-out → automated regression catches semantic breaks.
- Per-session structural-anchor edits (protocol v1.2.0+) keep diff hunks scoped.
- `git diff <session-base>..HEAD -- argus/execution/order_manager.py | wc -l` reported in every close-out for cumulative-diff tracking.
- Final review at S5c uses full suite + Tier 2 reviewer reads cumulative diff explicitly.
- **Cumulative diff bound recalibrated per Tier 3 guidance (2026-04-29):** **~1150–1300 LOC** for `order_manager.py` (was ~1100–1200 pre-Tier-3; +50 to +100 for callback-path AST guards per Tier 3 items A + B + Branch 4 coupling per Tier 3 item C + AC2.7 auto-activation per Decision 4 + `halt_entry_until_operator_ack` field threading per Tier 3 item C).

**Tracking:** Cumulative diff line count at each session close-out:

| Session | Expected Δ in `order_manager.py` | Cumulative Δ (bound) |
|---------|---------------------------------:|---------------------:|
| S2a | ~30–60 LOC | ~60 |
| S2b | ~40–80 LOC | ~140 |
| S3a | ~70–110 LOC (+ `pending_sell_age_watchdog_enabled` field per Decision 4) | ~250 |
| S3b | ~150–220 LOC (4 emit-site exception handlers + suppression-check + broker-verification fallback + Branch 4 + HALT-ENTRY coupling per Tier 3 item C + `halt_entry_until_operator_ack` field threading) | ~470 |
| S4a-i | ~160–220 LOC (3 ManagedPosition fields + on_fill state machine + `_reserve_pending_or_fail` atomic helper + `_check_sell_ceiling` + 5 guards + reconstruct_from_broker line + POLICY_TABLE + AC2.7 auto-activation logic) | ~690 |
| S4a-ii | ~0–30 LOC (preferred outcome: zero production-code change; ≤30 LOC if static-analysis reveals an existing await between bookkeeping read and write) | ~720 |
| S4b | ~15–25 LOC (4 substitutions + constant deletion + `__init__` signature + dual-channel warning + `--allow-rollback` flag check) | ~745 |
| S5c | ~0 LOC (test-only — fixture + 5 CL tests + 1 Branch 4 unit test) | ~745 |

**Soft cap:** ~1300 cumulative LOC (was ~1000 pre-Tier-3). Anything beyond suggests scope creep → Tier 2 reviewer flags.

### Risk: Path #1 Mechanism Choice Cascading

**Concern:** S2a's H2/H4/H1 selection cascades into S2b (other surfaces), S5a (validation fixture), AMD-2 invariant framing (regression test renaming + DEC-390 documentation), conditional operator-audit logging (invariant 22), and CL-3 (cross-layer composition under H1 specifically per invariant 27).

**Mitigation (revised per Round-1 + Tier 3):**
- S2a close-out documents the chosen mechanism explicitly in a "Mechanism Selected" section.
- S2b's pre-flight reads S2a close-out + `scripts/spike-results/spike-def204-round2-path1-results.json` and asserts mechanism consistency.
- S5a's fixture is mechanism-agnostic (asserts AC1.1 `total_sold ≤ shares_total` regardless of HOW the mechanism prevents over-flatten).
- DEC-390 entry template (in `doc-update-checklist.md` C2) has placeholders for mechanism choice.
- **Operator-audit logging (invariant 22) is conditional on H1/H4 selection** — S2a impl prompt branches on the JSON `selected_mechanism` field.
- **CL-3 (invariant 27) requires H1 to be the active mechanism for the HALT-ENTRY posture verification.** If H2 is selected, CL-3 still runs but mocks `selected_mechanism="h1_cancel_and_await"` to exercise the coupling code path.
- **Decision 2 N=100 hard gate** — even if `modifyOrder` Wilson UB is favorable for H2, H1 is NOT eligible if `h1_propagation_zero_conflict_in_100 == false`. This shifts mechanism selection logic toward H2/H4.

**Tracking:** Sprint-close DEC-390 entry must explicitly cite the mechanism selected (not "one of H2/H4/H1" — the actual choice). RSK filing at sprint-close conditional on mechanism (RSK-DEC-390-AMEND for H2; RSK-DEC-390-CANCEL-AWAIT-LATENCY for H1 or H4-with-fallback-active).

### Risk: Validation Artifact Drift

**Concern:** S5a + S5b commit JSON artifacts under `scripts/spike-results/`. Composite artifact specifically uses Pytest-side-effect pattern with daily CI freshness.

**Mitigation (revised per Round-1 M-3 + Phase B re-run):**
- Invariant 18 establishes 30-day freshness check for spike + path1 + path2 artifacts.
- Composite artifact freshness: daily CI workflow runs the test and updates mtime. If CI workflow misconfigured or failing silently, freshness check at A13 catches at first post-merge paper session.
- Pytest test `test_validate_path{1,2}_artifact_committed_to_repo` (S5a + S5b) asserts artifact exists at expected path with valid schema.
- **NEW per Phase B re-run / pre-live transition checklist additions (see `doc-update-checklist.md` C9):** "Spike artifact freshness ≤30 days" gate; "daily composite test green ≥7 days content-AND-mtime"; pre-live transition checklist additions enforce both content AND mtime requirements.
- Quarterly operational re-validation flagged in `docs/risk-register.md`.

**Tracking:** Sprint-close establishes baseline; sprint-history.md records artifact mtimes/SHAs.

### Risk: `is_reconstructed` Refusal Posture Operational Degradation

**NEW per Round-1 C-2 disposition; severity ESCALATED per Phase B Severity Calibration Rubric application.**

**Concern:** Reconstructed positions accumulate operational state during paper trading; operator daily-flatten infrastructure must keep up; any failure of operator-manual flatten leaves capital trapped.

**Mitigation:**
- A-class halt A16 fires if operational degradation observed.
- Sprint Abort Condition #7 covers sustained degradation across multiple paper sessions; **trigger lowered from 4 weeks to 2 weeks per H-R2-3 + Severity Calibration Rubric** (operator daily-flatten empirically failed Apr 28 — 27 of 87 ORPHAN-SHORT detections from a missed run).
- RSK-RECONSTRUCTED-POSITION-DEGRADATION filed at sprint-close (severity **MEDIUM-HIGH**, time-bounded by Sprint 31.94 D3).
- Sprint 31.94 D3 (boot-time adoption-vs-flatten policy) eliminates the conservative posture; this risk is structurally bounded.

**Tracking:** Sprint-close RSK + Sprint 31.94 D3 inheritance pointer.

### Risk: Synchronous-Update Invariant Scope Gap (NEW per Tier 3 item A + B)

**Concern:** Tier 3 verdict identified that the H-R2-1 atomic-reserve protection pattern was previously scoped to `_reserve_pending_or_fail` only. The L3 ceiling correctness depends on the asyncio single-event-loop guarantee applying to every path that mutates the bookkeeping counters, not only the place-time path. Without scope extension, the asyncio yield-gap race could re-emerge via callback paths (`on_fill`, `on_cancel`, `on_reject`, `_on_order_status`).

**Mitigation:**
- Invariant 23 establishes AST-no-await scan + mocked-await injection regression on ALL bookkeeping mutation paths AND on `_check_sell_ceiling`'s multi-attribute read.
- S4a-ii (NEW SESSION) is dedicated to building this regression infrastructure.
- Preferred outcome of S4a-ii is **zero production-code change** with the test file establishing the regression guard. If static-analysis reveals an existing await between bookkeeping read and write, fix is in-scope for S4a-ii.
- DEF-FAI-CALLBACK-ATOMICITY (Tier 3 verdict; sprint-gating Round 3 advancement) — closure of this DEF requires invariant 23 to be active and green at S4a-ii close-out.

**Tracking:** Sprint-close DEC-390 explicitly cites synchronous-update invariant scope per regression invariant 23.

### Risk: Reflective Call Pattern Coverage Gap (NEW per Decision 3 / FAI #8)

**Concern:** AST callsite scan for `is_stop_replacement=True` callers (existing invariant 24 / regression infrastructure) may have false-negative paths via reflective or aliased call patterns: `**kw` unpacking, computed-value flag assignment, `getattr` reflective access.

**Mitigation:**
- Invariant 23 includes 3 reflective-pattern sub-tests at S4a-ii (FAI #8 option (a) per Decision 3).
- Decision 3 explicitly chose option (a) over option (b) (accept-and-document NOT taken).
- DEF-FAI-8-OPTION-A (Tier 3 verdict; Sprint 31.92 S4a-ii) — closure requires the 3 reflective-pattern sub-tests active and green.

**Tracking:** S4a-ii close-out explicitly reports the 3 reflective-pattern test outcomes.

### Risk: Cross-Layer Composition Test Incompleteness (NEW per Decision 5)

**Concern:** Cross-layer composition test count at 5 (above template floor; below exhaustive). DEC-386's empirical falsification justifies heightened bar; CL-6 (rollback + locate-suppression interaction) explicitly deferred.

**Mitigation:**
- Invariant 27 + S5c deliver 5 CL tests (CL-1 through CL-5).
- CL-6 deferral rationale documented in `docs/process-evolution.md` (per `doc-update-checklist.md` C10).
- RSK-CROSS-LAYER-INCOMPLETENESS filed at sprint-close (severity **MEDIUM**; Tier 3 verdict 2026-04-29).

**Tracking:** Sprint-close RSK + `docs/process-evolution.md` lesson on CL test count rationale.

---

## Adversarial Review Round 3 Reference

The Adversarial Review Input Package Round 3 will include this Regression Checklist verbatim. **Round 3 is full scope per `protocols/adversarial-review.md` v1.1.0 § Outcome C** (supersedes the Round-2 disposition's narrowest-scope recommendation; the 2026-04-29 metarepo amendment binds Round 3 to full scope).

Reviewers should specifically scrutinize:

1. Whether 27 invariants is sufficient or if any A-class halt in `escalation-criteria.md` lacks a corresponding regression test invariant.
2. Whether the per-session verification matrix correctly identifies which sessions are ✓-mandatory vs ▢-soft for invariants 5–9 (DEC-385/386/388/DEF-158/OCA-exempt) AND for the new invariants 19–27.
3. Whether invariant 17 (AMD-2 mechanism-conditional) correctly handles all three H2/H4/H1 branches at S2a — specifically, whether H4 (hybrid) needs nested parametrize for amend-success vs cancel-fallback paths.
4. Whether invariant 20 (pending-reservation state transitions) covers all 5 transitions enumerated in AC3.1 OR whether transition counts could be off (e.g., what about `place_order` returning a non-success status that's neither full-fill nor reject?).
5. Whether invariant 21 (broker-verification three branches) correctly handles the failure-mode case (B-class halt B12) — specifically, whether `verification_failed: true` metadata flag in the alert is operationally meaningful AND whether invariant 25's `verification_stale: true` is the canonical metadata key (it is — invariant 21 references the post-refresh-success branches; invariant 25 is the refresh-failure path).
6. Whether the cumulative-diff soft cap of ~1300 LOC for `order_manager.py` is realistic given the new pending-reservation state machine + Branch 4 coupling + AC2.7 auto-activation + `halt_entry_until_operator_ack` field threading OR needs to be tighter.
7. Whether invariant 19 (`is_reconstructed` refusal) creates a test-coverage hole for operator-manual flatten paths (i.e., does `scripts/ibkr_close_all_positions.py`'s flow get tested?).
8. **(NEW for Round 3 — FAI completeness check per Tier 3 self-falsifiability clause)** Whether the 9-entry FAI in `falsifiable-assumption-inventory.md` and `sprint-spec.md` § Falsifiable Assumption Inventory captures every primitive-semantics assumption load-bearing on the proposed mechanism. If Round 3 finds an additional load-bearing assumption not in the FAI, the inventory has failed and the mechanism's adversarial-review verdict must be downgraded — Decision 7 routes the response (a primitive-semantics-class Critical routes to Phase A re-entry; any other Critical class routes to RSK-and-ship).
9. **(NEW for Round 3 — Cross-Layer Composition Test completeness check per Tier 3 verdict)** Whether the 5 CL tests (CL-1 through CL-5; CL-6 deferred) cover the operationally-relevant compositions OR whether Round 3 surfaces an additional composition that should be covered. (Reviewer note: the CL test count is ABOVE the template's "at least one" floor and ABOVE the Tier 3 verdict's 3-test floor; absent a specific composition the reviewer can identify, the count is sufficient.)
10. **(NEW for Round 3 — Synchronous-update invariant scope check per Tier 3 items A + B)** Whether invariant 23's enumeration of bookkeeping mutation paths (`_reserve_pending_or_fail`, `on_fill`, `on_cancel`, `on_reject`, `_on_order_status`, `_check_sell_ceiling` multi-attribute read) is exhaustive OR whether Round 3 surfaces an additional path that mutates `cumulative_pending_sell_shares` or `cumulative_sold_shares` not in the list.

# Sprint 31.92: Sprint-Level Regression Checklist

> **Phase C artifact 6/8 (revised post-Round-1).** Specific, testable items the
> `@reviewer` must verify at every Tier 2 review. Embedded into every
> implementation prompt so the implementer can self-check before close-out and
> the reviewer has explicit assertions to test against.
>
> **Revision history:** Round 1 authored 2026-04-28 with 18 invariants. Round-1-revised 2026-04-29: invariant 13 rewritten for pending-reservation pattern (C-1); invariant 14 expanded for position-keyed dict + broker-verification (H-2 + H-3); invariant 16 reframed as lock-step-not-validity (H-4); invariant 17 reframed for mechanism-conditional AMD-2 (C-3); NEW invariant 19 (`is_reconstructed` refusal); NEW invariant 20 (pending-reservation state-transition completeness); NEW invariant 21 (broker-verification three-branch coverage); NEW invariant 22 (mechanism-conditional operator-audit logging). Total invariants: 22.

## Critical Invariants (Must Hold After Every Session)

The 22 invariants are organized into three groups:
- **Invariants 1–9: PRESERVED FROM PRIOR SPRINTS** — DEC-117/364/369/372/385/386/388 + DEF-158 + `# OCA-EXEMPT:`.
- **Invariants 10–12: BASELINE PRESERVATION** — test count, pre-existing flake count, frontend immutability.
- **Invariants 13–22: NEW IN SPRINT 31.92** — established by AC1/AC2/AC3/AC4 (with Round-1 revisions).

### 1. DEC-117 Atomic Bracket Order Placement

**Test:** `tests/execution/test_atomic_brackets.py` (existing) — parent + 2 children placed atomically; parent failure cancels children; transmit-flag semantics preserved.

**Verified at:** Every session's close-out. **Critical for:** S2a, S2b (Path #1 mechanism touches `_trail_flatten` + `_resubmit_stop_with_retry`'s emergency-flatten branch, both of which interact with bracket-stop cancellation OR amendment timing — must not regress atomic bracket invariants).

**Sessions responsible:** ALL.

---

### 2. DEC-364 `cancel_all_orders()` No-Args ABC Contract

**Test:** Pre-existing regression test that asserts `Broker.cancel_all_orders()` (no args) preserves DEC-364 behavior; DEC-386 S0's positional+keyword signature is BACKWARD-COMPATIBLE (zero-arg call = original DEC-364 behavior).

**Verified at:** Every session's close-out. **Critical for:** S2a, S2b (if Path #1 mechanism uses H1 cancel-and-await fallback, calls go through this ABC; must preserve no-args semantics for any existing callers).

**Sessions responsible:** ALL.

---

### 3. DEC-369 Broker-Confirmed Reconciliation Immunity

**Test:** Pre-existing test that broker-confirmed positions (with IBKR entry fill callbacks, `oca_group_id is None`-derived from `reconstruct_from_broker`) are NOT auto-closed by reconciliation. AC3.6 + AC3.7 must compose with this: ceiling initialization for reconstruct-derived positions composes additively with DEC-369 immunity (BOTH protections apply; `is_reconstructed = True` adds a second layer of refusal, not a replacement).

**Verified at:** Every session's close-out. **Critical for:** S4a (ceiling initialization for `reconstruct_from_broker`-derived positions per AC3.6 + AC3.7).

**Sessions responsible:** ALL.

---

### 4. DEC-372 Stop Retry Caps + Exponential Backoff

**Test:** Pre-existing `test_stop_resubmission_cap` — retry attempts capped per config; backoff is 1s → 2s → 4s; emergency-flatten fires only after cap exhausted.

**Verified at:** Every session's close-out. **Critical for:** S2b (touches the emergency-flatten branch in `_resubmit_stop_with_retry`; must preserve retry-cap and backoff invariants while applying Path #1 mechanism to the emergency SELL).

**Sessions responsible:** ALL; especially S2b.

---

### 5. DEC-385 Six-Layer Side-Aware Reconciliation

**Test:** Pre-existing monotonic-safety matrix regression `test_def204_reconciliation_layers_monotonic` (Sprint 31.91 invariant 17). All 6 layers preserved byte-for-byte.

**Verified at:** Every session's close-out. **Critical for:** S3a + S3b (Path #2's broker-verified suppression-timeout fallback REUSES `phantom_short_retry_blocked` alert from DEC-385 L4 conditional on broker-verification result; must not modify the alert path itself).

**Sessions responsible:** ALL; especially S3a, S3b.

**Specific edges:**
- DEF-158 retry 3-branch side-check (lines ~3424–3489) UNCHANGED — Path #2 adds upstream detection at `place_order` exception, NOT a 4th branch.
- `phantom_short_retry_blocked` SystemAlertEvent emitter unchanged in source code — Path #2's broker-verified fallback CALLS this existing emitter conditionally per AC2.5 case (c).

---

### 6. DEC-386 Four-Layer OCA Architecture

**Test:** Pre-existing monotonic-safety matrix regression `test_dec386_oca_layers_preserved`. All 4 layers preserved byte-for-byte.

**Verified at:** Every session's close-out. **Critical for:** S4b (DEF-212 rider modifies `OrderManager.__init__` and the 4 OCA-thread sites; the OCA-threading SEMANTICS must remain identical — only the source of `ocaType` value changes from module constant to instance attribute).

**Sessions responsible:** ALL; especially S4b.

**Specific edges:**
- `IBKRBroker.place_bracket_order` OCA threading (DEC-386 S1a) UNCHANGED.
- `_handle_oca_already_filled` SAFE-marker path (DEC-386 S1b) UNCHANGED.
- `# OCA-EXEMPT:` exemption mechanism preserved (see invariant 9).
- `_is_oca_already_filled_error` helper UNCHANGED (relocation deferred to Sprint 31.93 per SbC #4).
- **NEW (Round-1 H-4):** `bracket_oca_type` Pydantic field validator UNCHANGED — rollback escape hatch preserved per SbC §"Out of Scope" #22. Only the consumer side (OrderManager) gains construction-time wiring + AC4.6 startup warning.

---

### 7. DEC-388 Alert Observability Subsystem

**Test:** Pre-existing tests for HealthMonitor consumer + REST + WebSocket + 5-layer storage. AST policy-table exhaustiveness regression `tests/api/test_policy_table_exhaustiveness.py` updated at S4a to include `sell_ceiling_violation` (now 14 entries).

**Verified at:** Every session's close-out. **Critical for:** S4a (adds 1 new alert type `sell_ceiling_violation` and 1 new `POLICY_TABLE` entry; must preserve all 13 existing entries) and S3b (Path #2's broker-verified fallback emits `phantom_short_retry_blocked` via the existing DEC-385 path conditionally — no new emitter site at the consumer side).

**Sessions responsible:** ALL; especially S4a.

**Specific edges:**
- `POLICY_TABLE` count: 13 (pre-S4a) → 14 (post-S4a).
- `sell_ceiling_violation` policy entry: `operator_ack_required=True`, `auto_resolution_predicate=None` (manual-ack only).
- Existing 13 policy entries unchanged.

---

### 8. DEF-158 Retry Three-Branch Side-Check Preserved Verbatim

**Test:** New regression test `test_def158_3branch_side_check_preserved_verbatim` (S3b). Asserts that `_check_flatten_pending_timeouts` lines ~3424–3489 retain the BUY → resubmit / SELL → alert+halt / unknown → halt structure UNCHANGED. Path #2's NEW detection is at the `place_order` exception in the 4 SELL emit sites, NOT inside this gate.

**Verified at:** S3b close-out specifically; reviewed at every session as a do-not-modify boundary.

**Sessions responsible:** ALL; especially S3b. **A-class halt A5** fires if violated.

---

### 9. `# OCA-EXEMPT:` Exemption Mechanism Preserved

**Test:** Pre-existing grep regression guard `test_no_sell_without_oca_when_managed_position_has_oca` from DEC-386 S1b.

**Verified at:** Every session's close-out. **Critical for:** S2a, S2b, S3b, S4a (any new SELL emit logic must either use OCA threading via `position.oca_group_id` OR carry an `# OCA-EXEMPT: <reason>` comment).

**Sessions responsible:** ALL.

---

### 10. Test Count Baseline Holds

**Test:** Full suite pytest count ≥ 5,269 at every close-out. Vitest count = 913 unchanged.

**Verified at:** Every session's close-out. **B-class halt B3** fires if pytest drops below baseline.

**Sessions responsible:** ALL.

**Per-session test deltas (revised estimate):**
| Session | Pytest Δ | Vitest Δ |
|---------|---------:|---------:|
| S1a | 0 | 0 |
| S1b | 0 | 0 |
| S2a | +6 to +7 | 0 |
| S2b | +7 | 0 |
| S3a | +6 | 0 |
| S3b | +8 | 0 |
| S4a | +7 logical (≈8 effective) | 0 |
| S4b | +6 logical (≈10 effective with parametrize) | 0 |
| S5a | +4 | 0 |
| S5b | +9 logical | 0 |
| **Total range** | **+75 to +95** | **0** |

**Final target:** 5,344–5,374 pytest + 913 Vitest at S5b close-out.

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

**Test:** New parametrized test `test_check_sell_ceiling_blocks_excess_sell_at_5_emit_sites_parametrized` (S4a, parametrized × 2 emit sites + S5b composite × remaining 3 emit sites + reconstructed-position refusal scenarios).

**REWRITTEN per Round-1 C-1:** Ceiling is a TWO-COUNTER reservation: `cumulative_pending_sell_shares` (incremented synchronously at place-time before `await`) + `cumulative_sold_shares` (incremented at fill). Ceiling check: `pending + sold + requested ≤ shares_total`. The race scenario (two coroutines on same `ManagedPosition`) is structurally prevented because the second coroutine's check sees the first coroutine's pending reservation.

**Verified at:** S4a close-out (2 of 5 sites parametrized + C-1 race test); S5b close-out (remaining 3 sites + composite stress test + reconstructed-position refusal). **A-class halt A11** fires if false-positives observed in production paper trading.

**Sessions responsible:** S4a, S5b.

**Specific edges:**
- Per-`ManagedPosition`, NOT per-symbol (AC3.4).
- `reconstruct_from_broker`-derived: initialize `cumulative_pending_sell_shares = 0`, `cumulative_sold_shares = 0`, `is_reconstructed = True`, `shares_total = abs(broker_position.shares)` (AC3.6).
- Reconstructed positions refuse ALL ARGUS-emitted SELLs regardless of pending+sold+requested arithmetic (AC3.7) — early return in ceiling check before counter math.
- Config-gated: `OrderManagerConfig.long_only_sell_ceiling_enabled = false` returns True unconditionally (AC3.8).
- Increment in `on_fill` for SELL-side fills only — T1, T2, bracket stop, trail-flatten, escalation-flatten, retry-flatten, EOD-flatten, locate-released-flatten (AC3.1).
- Bracket placement EXCLUDED from ceiling check (AC3.2 + SbC §"Edge Cases to Reject" #15).

---

### 14. Path #2 Locate-Rejection Fingerprint Deterministic + Position-Keyed Suppression + Broker-Verified Timeout

**Test:** Composite of three sub-tests (S3a + S3b):
1. `test_is_locate_rejection_matches_canonical_string` — exact substring captured by S1b spike, case-insensitive.
2. `test_is_locate_suppressed_position_keyed_returns_true_within_window` — keyed by `ManagedPosition.id` (ULID), NOT symbol (Round-1 H-2).
3. `test_suppression_timeout_broker_shows_*` × 3 branches — AC2.5 broker-verification three-branch coverage (Round-1 H-3).

**EXPANDED per Round-1 H-2 + H-3.**

**Verified at:** S3a close-out (sub-tests 1+2); S3b close-out (sub-test 3 broker-verification); ongoing at quarterly re-validation (RSK-DEC-390-FINGERPRINT — operational hygiene). **A-class halts A2 + A13 + B12** apply.

**Sessions responsible:** S3a (establishes); S3b (broker-verification wiring); S5b (validates against synthetic locate-rejection fixture with hold-then-release).

**Specific edges:**
- Substring match (NOT regex unless S1b finds variants) — case-insensitive via `str(error).lower()`.
- Helper accepts `BaseException` (mirrors DEC-386's `_is_oca_already_filled_error` shape).
- Suppression dict keyed by `ManagedPosition.id` (ULID) — cross-position safety preserved.
- Broker-verification at AC2.5 timeout: 3 outcomes (broker-zero, broker-expected-long, broker-unexpected-state).

---

### 15. `_OCA_TYPE_BRACKET` Module Constant Deleted

**Test:** New grep regression guard `test_no_oca_type_bracket_constant_remains_in_module` (S4b). Greps `argus/execution/order_manager.py` for the literal `_OCA_TYPE_BRACKET` and asserts ZERO matches post-S4b.

**Verified at:** S4b close-out; every subsequent session as a non-regression check. **B-class halt B11** fires if the count is wrong before S4b begins.

**Sessions responsible:** S4b (establishes); S5a, S5b (preserve).

**Specific edges:**
- Pre-S4b: 5 occurrences (1 declaration + 4 use sites).
- Post-S4b: 0 occurrences. All replaced by `self._bracket_oca_type`.
- `OrderManager.__init__` accepts `bracket_oca_type: int` keyword arg; `argus/main.py` construction site passes `config.ibkr.bracket_oca_type`.

---

### 16. AC4.4 OCA-Type Lock-Step (NOT Operational Validity) — `bracket_oca_type=0` Threads Through Consistently

**Test:** New parametrized test `test_bracket_oca_type_lockstep_preserved_under_rollback` (S4b, parametrized × 4 OCA-thread sites with `bracket_oca_type ∈ {0, 1}`). Asserts that flipping from 1 to 0 produces consistent `ocaType=0` on bracket children AND on standalone-SELL OCA threading (NO divergence).

**REFRAMED per Round-1 H-4:** Test affirms the lock-step PROPERTY of the DEF-212 fix; does NOT affirm `ocaType=0` as operationally valid. Test docstring explicitly: "ocaType=0 disables OCA enforcement and reopens DEF-204; this test asserts the rollback path is consistent, not that the rollback is operationally safe."

**Verified at:** S4b close-out.

**Sessions responsible:** S4b.

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
- `scripts/spike-results/spike-def204-round2-path1-results.json` exists, has `status: PROCEED`, dated within 30 days.
- `scripts/spike-results/spike-def204-round2-path2-results.json` exists, has `status: PROCEED`, dated within 30 days.
- `scripts/spike-results/sprint-31.92-validation-path1.json` exists, has `path1_safe: true`, dated post-S5a-merge.
- `scripts/spike-results/sprint-31.92-validation-path2.json` exists, has `path2_suppression_works: true`, dated post-S5b-merge.
- `scripts/spike-results/sprint-31.92-validation-composite.json` exists, has composite-test pass criteria met, dated within 24 hours via daily CI.

**Verified at:** Sprint-close (D14 doc-sync) AND before each subsequent paper session for 30 days post-seal. **A-class halt A13** fires if any artifact >30 days old at any future trigger event (live-transition consideration, `ib_async`/IBKR Gateway upgrade).

**Sessions responsible:** S1a (path1 spike), S1b (path2 spike), S5a (path1 validation), S5b (path2 + composite validation).

---

### 19. (NEW per Round-1 C-2) `is_reconstructed = True` Refusal Posture Holds for All ARGUS-Emitted SELL Paths

**Test:** New regression test `test_restart_during_active_position_refuses_argus_sells` (S5b, AC5.4) — fixture: spawn ManagedPosition normally, partial-fill via T1, simulate restart by calling `reconstruct_from_broker()` (or directly setting `is_reconstructed=True` if test architecture requires), assert subsequent `_trail_flatten`, `_flatten_position`, `_check_flatten_pending_timeouts`, `_escalation_update_stop` invocations all refuse to emit SELL.

**Plus** unit-level `test_reconstruct_from_broker_initializes_is_reconstructed_true_and_zero_counters` (S5b) — asserts the single-line addition in `reconstruct_from_broker` correctly sets the flag.

**Verified at:** S5b close-out. **A-class halts A15 + A16** fire if violated in test OR in production paper trading.

**Sessions responsible:** S4a (establishes the field + ceiling-check short-circuit); S5b (regression test for refusal posture across all 4 standalone-SELL paths).

**Specific edges:**
- Field is in-memory only (NOT persisted to SQLite).
- Set ONLY in `reconstruct_from_broker` (single-line addition allowed inside the function body per SbC §"Do NOT modify").
- Refusal applies to ARGUS-emitted SELLs ONLY; operator-manual flatten via `scripts/ibkr_close_all_positions.py` is the only closing mechanism until Sprint 31.94 D3.
- RSK-RECONSTRUCTED-POSITION-DEGRADATION filed at sprint-close (time-bounded by Sprint 31.94 D3).

---

### 20. (NEW per Round-1 C-1) Pending-Reservation State-Transition Completeness

**Test:** Composite of S4a unit tests covering all 5 state transitions enumerated in AC3.1:
- `test_cumulative_pending_increments_synchronously_before_await` — asserts pending counter incremented BEFORE the `await place_order(...)` yield-point (the synchronous-before-await invariant is the architectural correctness contract).
- `test_cumulative_pending_decrements_on_cancel_reject` — order rejected/cancelled in `place_order` exception handler OR `cancel_order` confirmation: pending decrements.
- `test_cumulative_pending_transfers_to_sold_on_partial_fill` — partial fill: pending decrements by `filled_qty`, sold increments by `filled_qty`; remainder stays in pending.
- `test_cumulative_pending_transfers_to_sold_on_full_fill` — full fill: pending decrements by remaining, sold increments by remaining.
- `test_concurrent_sell_emit_race_blocked_by_pending_reservation` — **CANONICAL C-1 RACE TEST** (AC3.5).

**Verified at:** S4a close-out specifically; S5b composite re-exercises in integration. **A-class halt A11** fires if any state transition leaks or under-decrements (e.g., pending counter drifts upward over session).

**Sessions responsible:** S4a (establishes all 5 state transitions); S5b (integration verification under load).

**Specific edges:**
- `cumulative_pending_sell_shares` is in-memory only (NOT persisted; per SbC §"Out of Scope" #21 — DEF-209 deferred).
- Synchronous-before-await ordering in code is load-bearing; reviewer must inspect diff for ordering violations.
- Cancel/reject paths must decrement (not just the success/fill paths).

---

### 21. (NEW per Round-1 H-3) Broker-Verification Three-Branch Coverage at Suppression Timeout

**Test:** Three S3b tests covering AC2.5's three branches:
- `test_suppression_timeout_broker_shows_zero_logs_info_no_alert` — broker returns no entry for symbol; INFO log; no alert.
- `test_suppression_timeout_broker_shows_expected_long_logs_info_no_alert` — broker returns BUY-side entry with shares ≥ `position.shares_remaining`; INFO log; no alert.
- `test_suppression_timeout_broker_shows_unexpected_state_emits_alert` — broker returns short OR quantity divergence OR unknown side; publishes `phantom_short_retry_blocked` per DEC-385.

**Plus** failure-mode regression: `test_suppression_timeout_broker_query_failure_falls_through_to_alert` — if `broker.get_positions()` itself fails (exception, timeout), fall through to existing DEC-385 alert path with metadata flag `verification_failed: true` (per B-class halt B12 disposition).

**Verified at:** S3b close-out. **A-class halt B12** fires if broker-verification logic fails in test OR production.

**Sessions responsible:** S3b.

**Specific edges:**
- Helper logic lives inline in `_check_flatten_pending_timeouts` housekeeping loop OR as a private method on OrderManager (NOT a new module — per SbC §"Do NOT add").
- `broker.get_positions()` call latency budget ≤ 200ms p95 per Performance Benchmarks.
- Verification-failure fallback path must NOT silently absorb the alert — operator-triage signal preserved via metadata flag.

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

## Per-Session Verification Matrix

The matrix below shows which invariants each session's `@reviewer` MUST explicitly verify in the Tier 2 verdict.

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
| 13. SELL-volume ceiling (pending+sold pattern) | — | — | — | — | — | — | ✓ | ▢ | ▢ | ✓ |
| 14. Path #2 fingerprint + position-keyed dict + broker-verification | — | ✓ | — | — | ✓ | ✓ | — | — | — | ✓ |
| 15. `_OCA_TYPE_BRACKET` constant deleted | — | — | — | — | — | — | — | ✓ | ✓ | ✓ |
| 16. AC4.4 OCA-type lock-step (not validity) | — | — | — | — | — | — | — | ✓ | — | ▢ |
| 17. AMD-2 mechanism-conditional | — | — | ✓ | ✓ | — | — | — | — | ✓ | ✓ |
| 18. Spike artifacts fresh + committed | ✓ | ✓ | ▢ | ▢ | ▢ | ▢ | ▢ | ▢ | ✓ | ✓ |
| 19. `is_reconstructed` refusal posture (NEW) | — | — | — | — | — | — | ✓ | ▢ | ▢ | ✓ |
| 20. Pending-reservation state transitions (NEW) | — | — | — | — | — | — | ✓ | ▢ | ▢ | ✓ |
| 21. Broker-verification three-branch (NEW) | — | — | — | — | — | ✓ | ▢ | ▢ | ▢ | ✓ |
| 22. Operator-audit logging (conditional, NEW) | — | — | ✓¹ | ✓¹ | — | — | — | — | ✓¹ | ✓¹ |

**Legend:**
- ✓ = MANDATORY verification at this session's Tier 2 review.
- ▢ = SOFT verification (trust test suite unless suspicious diff).
- — = Not yet established.
- ✓¹ = MANDATORY only if S1a selected H1 or H4 (otherwise N/A).

---

## Cross-Session Invariant Risks

### Risk: `argus/execution/order_manager.py` Mass Modification

**Concern:** 6 of 10 sessions modify `order_manager.py`. Cumulative diff at S5b will be substantial.

**Mitigation (revised per Round-1):**
- DEC-328 tiering keeps full suite at every close-out → automated regression catches semantic breaks.
- Per-session structural-anchor edits (protocol v1.2.0) keep diff hunks scoped.
- `git diff <session-base>..HEAD -- argus/execution/order_manager.py | wc -l` reported in every close-out for cumulative-diff tracking.
- Final review at S5b uses full suite + Tier 2 reviewer reads cumulative diff explicitly.
- **Cumulative diff bound recalibrated per Round-1 reviewer Q8 feedback:** ~800–1,000 LOC for `order_manager.py` (Round 1 estimated 600 LOC; Round-1 revisions added pending-reservation state machine + `is_reconstructed` field handling + broker-verification helper + operator-audit logging — net ~200–400 LOC additional).

**Tracking:** Cumulative diff line count at each session close-out:

| Session | Expected Δ in `order_manager.py` | Cumulative Δ (bound) |
|---------|---------------------------------:|---------------------:|
| S2a | ~30–60 LOC | ~60 |
| S2b | ~40–80 LOC | ~140 |
| S3a | ~70–110 LOC | ~250 |
| S3b | ~120–180 LOC (4 emit-site exception handlers + suppression-check + broker-verification fallback) | ~430 |
| S4a | ~150–200 LOC (3 ManagedPosition fields + on_fill state machine + helper + 5 guards + reconstruct_from_broker line + POLICY_TABLE) | ~630 |
| S4b | ~15–25 LOC (4 substitutions + constant deletion + `__init__` signature + warning) | ~655 |

**Soft cap:** ~1000 cumulative LOC. Anything beyond suggests scope creep → Tier 2 reviewer flags.

### Risk: Path #1 Mechanism Choice Cascading

**Concern:** S2a's H2/H4/H1 selection cascades into S2b (other surfaces), S5a (validation fixture), AMD-2 invariant framing (regression test renaming + DEC-390 documentation), and conditional operator-audit logging (invariant 22).

**Mitigation (revised per Round-1):**
- S2a close-out documents the chosen mechanism explicitly in a "Mechanism Selected" section.
- S2b's pre-flight reads S2a close-out + `scripts/spike-results/spike-def204-round2-path1-results.json` and asserts mechanism consistency.
- S5a's fixture is mechanism-agnostic (asserts AC1.1 `total_sold ≤ shares_total` regardless of HOW the mechanism prevents over-flatten).
- DEC-390 entry template (in `doc-update-checklist.md` C2) has placeholders for mechanism choice.
- **Operator-audit logging (invariant 22) is conditional on H1/H4 selection** — S2a impl prompt branches on the JSON `selected_mechanism` field.

**Tracking:** Sprint-close DEC-390 entry must explicitly cite the mechanism selected (not "one of H2/H4/H1" — the actual choice). RSK filing at sprint-close conditional on mechanism (RSK-DEC-390-AMEND for H2; RSK-DEC-390-CANCEL-AWAIT-LATENCY for H1 or H4-with-fallback-active).

### Risk: Validation Artifact Drift

**Concern:** S5a + S5b commit JSON artifacts under `scripts/spike-results/`. Composite artifact specifically uses Pytest-side-effect pattern with daily CI freshness.

**Mitigation (revised per Round-1 M-3):**
- Invariant 18 establishes 30-day freshness check for spike + path1 + path2 artifacts.
- Composite artifact freshness: daily CI workflow runs the test and updates mtime. If CI workflow misconfigured or failing silently, freshness check at A13 catches at first post-merge paper session.
- Pytest test `test_validate_path{1,2}_artifact_committed_to_repo` (S5a + S5b) asserts artifact exists at expected path with valid schema.
- Quarterly operational re-validation flagged in `docs/risk-register.md`.

**Tracking:** Sprint-close establishes baseline; sprint-history.md records artifact mtimes/SHAs.

### Risk: `is_reconstructed` Refusal Posture Operational Degradation

**NEW per Round-1 C-2 disposition.**

**Concern:** Reconstructed positions accumulate operational state during paper trading; operator daily-flatten infrastructure must keep up; any failure of operator-manual flatten leaves capital trapped.

**Mitigation:**
- A-class halt A16 fires if operational degradation observed.
- Sprint Abort Condition #7 (NEW) covers sustained degradation across multiple paper sessions.
- RSK-RECONSTRUCTED-POSITION-DEGRADATION filed at sprint-close (time-bounded by Sprint 31.94 D3).
- Sprint 31.94 D3 (boot-time adoption-vs-flatten policy) eliminates the conservative posture; this risk is structurally bounded.

**Tracking:** Sprint-close RSK + Sprint 31.94 D3 inheritance pointer.

---

## Adversarial Review Round 2 Reference

The Adversarial Review Input Package Round 2 will include this Regression Checklist verbatim. Reviewers should specifically scrutinize:

1. Whether 22 invariants is sufficient or if any A-class halt in `escalation-criteria.md` lacks a corresponding regression test invariant.
2. Whether the per-session verification matrix correctly identifies which sessions are ✓-mandatory vs ▢-soft for invariants 5–9 (DEC-385/386/388/DEF-158/OCA-exempt) AND for the new invariants 19–22.
3. Whether invariant 17 (AMD-2 mechanism-conditional) correctly handles all three H2/H4/H1 branches at S2a — specifically, whether H4 (hybrid) needs nested parametrize for amend-success vs cancel-fallback paths.
4. Whether invariant 20 (pending-reservation state transitions) covers all 5 transitions enumerated in AC3.1 OR whether transition counts could be off (e.g., what about `place_order` returning a non-success status that's neither full-fill nor reject?).
5. Whether invariant 21 (broker-verification three branches) correctly handles the failure-mode case (B-class halt B12) — specifically, whether `verification_failed: true` metadata flag in the alert is operationally meaningful.
6. Whether the cumulative-diff soft cap of ~1000 LOC for `order_manager.py` is realistic given the new pending-reservation state machine OR needs to be tighter.
7. Whether invariant 19 (`is_reconstructed` refusal) creates a test-coverage hole for operator-manual flatten paths (i.e., does `scripts/ibkr_close_all_positions.py`'s flow get tested?).
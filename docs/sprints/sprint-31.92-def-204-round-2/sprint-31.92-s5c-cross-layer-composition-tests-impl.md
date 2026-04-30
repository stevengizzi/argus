# Sprint 31.92, Session S5c: Cross-Layer Composition Tests (CL-1..CL-5 + CL-7) + `SimulatedBrokerWithRefreshTimeout` Fixture — FINAL SESSION per Decision 5 + Tier 3 item E + Round 3 C-R3-1

> **🔄 TIER 3 REVIEW #3 AMENDMENT NOTICE (2026-04-30)**
>
> **CL-3 parameterization amended:** `selected_mechanism = Mechanism A`
> (was `selected_mechanism ∈ {H2, H4, H1}` / mock to `"h1_cancel_and_await"`
> pre-Tier-3-#3). H2 and H4 ELIMINATED-EMPIRICALLY by DEF-242; only
> Mechanism A (cancel-and-resubmit-fresh-stop, formerly H1, now PRIMARY
> DEFAULT) remains viable. CL-3 no longer needs to MOCK `selected_mechanism`
> to `"h1_cancel_and_await"` to exercise the HALT-ENTRY coupling — the
> production code's mechanism IS Mechanism A, so the test directly
> exercises the production path. The Branch 4 unit test parameter
> remains the same. **CL-1, CL-2, CL-4, CL-5, CL-7 untouched.** CL-6
> remains out of scope per Decision 5 and now also per Tier 3 #3
> (spec-by-contradiction.md §Out-of-Scope item 28). The
> `SimulatedBrokerWithRefreshTimeout` fixture is unchanged. Spike
> artifact source switches from `spike-def204-round2-path1-results.json`
> (S1a v2) to `spike-def204-mechanism-a-followon-results.json`
> (Unit 6 follow-on spike) for the mechanism-name read.
> Cross-references: `docs/sprints/sprint-31.92-def-204-round-2/tier-3-review-3-verdict.md`;
> sprint-spec.md §"Defense-in-Depth Cross-Layer Composition Tests" CL-3
> entry (amended); DEF-242, DEF-245;
> RSK-MECHANISM-A-UNPROTECTED-WINDOW.

## Pre-Flight Checks

Before making any changes:

1. **Read `.claude/rules/universal.md` in full and treat its contents as binding for this session.** The full set of universal RULE entries (currently RULE-001 through RULE-053) applies regardless of whether any specific rule is referenced inline in this prompt. Particularly load-bearing for S5c (the FINAL session of Sprint 31.92): RULE-038 (grep-verify discipline), RULE-040 (small-sample sweep / spike-artifact directional vs. authoritative), RULE-050 (CI green precondition — sprint-seal-gating), RULE-053 (architectural-seal verification — DEC-386 4-layer OCA + DEC-385 6-layer reconciliation + DEC-388 alert observability are sealed defenses; AC5.6 cross-layer composition tests assert composition holds, NOT that any layer is modified).

2. Read these files to load context:
   - `argus/execution/order_manager.py` — anchor by:
     - `_trail_flatten`, `_resubmit_stop_with_retry`, `_flatten_position`, `_check_flatten_pending_timeouts`, `_escalation_update_stop` (the 5 standalone-SELL emit sites + ceiling-guard surfaces).
     - `_check_sell_ceiling` + `_reserve_pending_or_fail` (S4a-i atomic-reserve method).
     - Branch 4 fallback path + `halt_entry_until_operator_ack` field threading per Tier 3 item C (S3b state).
     - `_locate_suppressed_until` dict + `_is_locate_suppressed` helper (S3a/S3b state).
     - `is_reconstructed` field + AC3.7 refusal short-circuit.
     - **Read what S2a/S2b/S3a/S3b/S4a-i/S4a-ii/S4b actually shipped; do not assume implementations.**
   - `argus/execution/simulated_broker.py` — anchor by class name `SimulatedBroker`. Confirm subclass extensibility for the `SimulatedBrokerWithRefreshTimeout` fixture variant (`refresh_positions()` override per DEF-SIM-BROKER-TIMEOUT-FIXTURE). Production `simulated_broker.py` MUST NOT be modified by S5c; the fixture lives in test code only.
   - `tests/integration/test_def204_round2_validation.py` — created at S5a; appended at S5b. S5c APPENDS the 6 cross-layer tests + 1 Branch 4 unit test (7 net new tests total).
   - `docs/sprints/sprint-31.92-def-204-round-2/sprint-spec.md` §"Defense-in-Depth Cross-Layer Composition Tests" (CL-1 through CL-5 + CL-7 verbatim text).
   - `docs/sprints/sprint-31.92-def-204-round-2/sprint-spec.md` §"Acceptance Criteria" Deliverable 5 (AC5.6).
   - `scripts/spike-results/spike-def204-round2-path1-results.json` — read `selected_mechanism` field; CL-3 may need to mock `selected_mechanism="h1_cancel_and_await"` if the actual mechanism is H2/H4 (per regression-checklist invariant 27 specific edge).

3. Run the test baseline (DEC-328 — Session 13 of 13 of sprint, **FINAL session — close-out skill invokes full suite** but pre-flight is **scoped**):

   ```
   python -m pytest tests/integration/ -n auto -q
   ```

   Expected: all passing (full suite was confirmed by S5b's close-out).

   **Note:** S5c is the FINAL session of Sprint 31.92. The close-out skill MUST run the FULL suite per DEC-328 final-review tier:

   ```
   python -m pytest --ignore=tests/test_main.py -n auto -q
   ```

   Expected pass count at S5c close-out: **5,357–5,403 pytest** (5,269 baseline + 88–134 new logical / 95–145 effective per Round 3 disposition aggregate). Vitest unchanged at 913.

4. Verify you are on the correct branch: **`main`**.

5. **Run the structural-anchor grep-verify commands** below. If drift is detected, disclose under RULE-038 in the close-out.

   ```bash
   # Verify all 5 standalone-SELL emit sites + ceiling helper exist post-S2a/S2b/S3a/S3b/S4a-i
   grep -n "def _trail_flatten\|def _resubmit_stop_with_retry\|def _flatten_position\|def _check_flatten_pending_timeouts\|def _escalation_update_stop\|def _check_sell_ceiling\|def _reserve_pending_or_fail" argus/execution/order_manager.py
   # Expected: 7 hits (one per function). Directional only.

   # Verify Branch 4 + halt_entry_until_operator_ack threading exists post-S3b
   grep -n "halt_entry_until_operator_ack\|verification_stale" argus/execution/order_manager.py | head -10
   # Expected: at least 2 hits (field declaration + Branch 4 metadata).

   # Verify SimulatedBroker class is intact (no semantic changes per SbC)
   grep -n "^class SimulatedBroker" argus/execution/simulated_broker.py
   # Expected: 1 hit.

   # Verify S5b's test file exists with 13 tests (4 from S5a + 9 from S5b)
   grep -c "^def test_" tests/integration/test_def204_round2_validation.py
   # Expected: 13.

   # Verify the spike artifact has selected_mechanism field
   python -c "import json; d = json.load(open('scripts/spike-results/spike-def204-round2-path1-results.json')); print(d.get('selected_mechanism'))"
   # Expected: one of "h2_amend_stop", "h4_hybrid", "h1_cancel_and_await". CL-3 may need to mock H1.
   ```

6. Verify all 11 prior sessions (S2a + S2b + S3a + S3b + S4a-i + S4a-ii + S4b + S5a + S5b + 2 spikes S1a + S1b) are complete and merged on `main`:

   ```bash
   ls docs/sprints/sprint-31.92-def-204-round-2/session-{s1a,s1b,s2a,s2b,s3a,s3b,s4a-i,s4a-ii,s4b,s5a,s5b}-closeout.md
   # All 11 close-out files must exist.
   ```

   If any close-out is missing, **HALT** — S5c is the final session and depends on all prior production-code sessions having landed.

7. Verify M-R2-5 mid-sprint Tier 3 verdict was CLEAR (PROCEED) and S4b/S5a/S5b have all closed CLEAR:

   ```bash
   ls docs/sprints/sprint-31.92-def-204-round-2/tier-3-review-2-verdict.md
   grep "PROCEED\|CLEAR" docs/sprints/sprint-31.92-def-204-round-2/tier-3-review-2-verdict.md | head -3
   ```

   If REVISE_PLAN or PAUSE_AND_INVESTIGATE, **HALT**.

## Objective

Implement the 6 cross-layer composition tests (CL-1 through CL-5 + CL-7 per Round 3 C-R3-1; CL-6 explicitly OUT per Decision 5) that exercise scenarios where the failure of one layer of DEC-390's 4-layer defense is supposed to be caught by another, plus 1 dedicated Branch 4 unit test using the `SimulatedBrokerWithRefreshTimeout` fixture variant (DEF-SIM-BROKER-TIMEOUT-FIXTURE per Tier 3 item E). The fixture variant lives in `tests/integration/conftest_refresh_timeout.py` (≤80 LOC to avoid the large-file penalty) and subclasses `SimulatedBroker` to override `refresh_positions()` with a configurable timeout, enabling in-process Branch 4 (`verification_stale: true`) testing that is otherwise unreachable. **AC5.6 framing: cross-layer tests are by definition slow + ugly + span multiple modules per `templates/sprint-spec.md` v1.2.0; per B10 still bounded ≤5s each.** Sprint sealing requires all 6 CL tests + Branch 4 unit test green AND full-suite green at S5c close-out (DEC-328 final-review tier).

## Requirements

1. **Create `tests/integration/conftest_refresh_timeout.py`** (≤80 LOC):

   ```python
   """SimulatedBrokerWithRefreshTimeout fixture variant
   (DEF-SIM-BROKER-TIMEOUT-FIXTURE per Tier 3 item E).

   Subclasses SimulatedBroker to override refresh_positions() with a
   configurable delay that exceeds timeout_seconds, enabling in-process
   Branch 4 (verification_stale: true) testing.

   Production simulated_broker.py is NOT modified per SbC §"Do NOT
   modify" #2. Fixture lives in test code only.
   """

   import asyncio

   import pytest

   from argus.execution.simulated_broker import SimulatedBroker


   class SimulatedBrokerWithRefreshTimeout(SimulatedBroker):
       """SimulatedBroker variant whose refresh_positions() raises
       asyncio.TimeoutError after a configurable delay.

       Used by:
       - CL-3 cross-layer composition test
       - test_branch_4_verification_stale_metadata_emitted_on_refresh_timeout_in_process
       """

       def __init__(self, *args, refresh_timeout_seconds: float = 0.001, **kwargs):
           super().__init__(*args, **kwargs)
           self._refresh_timeout_seconds = refresh_timeout_seconds

       async def refresh_positions(
           self, timeout_seconds: float = 5.0
       ) -> None:
           """Override: always raises asyncio.TimeoutError after the
           configured delay (configurable per fixture instance)."""
           await asyncio.sleep(self._refresh_timeout_seconds)
           raise asyncio.TimeoutError(
               f"SimulatedBrokerWithRefreshTimeout: forced timeout after "
               f"{self._refresh_timeout_seconds}s "
               f"(timeout_seconds={timeout_seconds})"
           )


   @pytest.fixture
   def simulated_broker_with_refresh_timeout():
       """Pytest fixture exposing the variant for CL-3 + Branch 4 unit
       test. Per-test refresh delay configurable via fixture parameter
       indirect."""
       return SimulatedBrokerWithRefreshTimeout()
   ```

   The fixture is ≤80 LOC. Do NOT add other test helpers to this file — focused single-purpose conftest per Tier 3 item E / DEF-SIM-BROKER-TIMEOUT-FIXTURE.

2. **Append 6 cross-layer composition tests + 1 Branch 4 unit test** to `tests/integration/test_def204_round2_validation.py`:

   ### CL-1 (L1 fails → L3 catches)

   ```python
   def test_cl_1_l1_fails_l3_catches_pending_reservation_false_positive(
       monkeypatch,
   ):
       """CL-1: Force `_reserve_pending_or_fail` false positive (mock the
       synchronous method to return True even when the ceiling would be
       exceeded). Verify the ceiling-violation invariant catches at
       reconciliation; locate-suppression-with-broker-verification alert
       path fires.

       Composes L1 (pending-reservation) + L3 (SELL-volume ceiling).
       """
       # Force _reserve_pending_or_fail to return True unconditionally
       # (false positive — would normally fail the ceiling check).
       monkeypatch.setattr(
           "argus.execution.order_manager.OrderManager._reserve_pending_or_fail",
           lambda self, position, requested_qty: True,
       )
       # Setup: position with shares_total=100, cumulative_sold_shares=80;
       # attempt SELL 50 (would exceed ceiling at 80+50=130 > 100).
       # Expected: _check_sell_ceiling catches at the ceiling-check site
       # (NOT at reservation, since L1 was forced-false-positive).
       # Assert sell_ceiling_violation alert fires + no SELL emitted.
   ```

   ### CL-2 (L4 fails → L2 catches)

   ```python
   def test_cl_2_l4_fails_l2_catches_emergency_flatten_under_rollback():
       """CL-2: Force startup with bracket_oca_type != 1 AND
       --allow-rollback (the operator-confirmed rollback path). Verify
       under DEC-386 rollback that the emergency-flatten branch (Layer 2
       via is_stop_replacement=False) still ceiling-checks; this proves
       Layer 2 doesn't depend on Layer 4's enforcement.

       Composes L2 (emergency-flatten) + L4 (DEF-212 wiring).
       """
       # Setup: instantiate OrderManager with bracket_oca_type=0 (rollback);
       # spawn ManagedPosition; trigger emergency-flatten branch via
       # _resubmit_stop_with_retry's exhaustion path.
       # Expected: ceiling check fires (NOT skipped) — emergency-flatten
       # passes is_stop_replacement=False, ceiling check engages.
       # Assert: ceiling check evaluates; legitimate emergency-flatten
       # is allowed (within ceiling); over-flatten attempt is blocked.
   ```

   ### CL-3 (L3 + L5 cross-falsification — uses `SimulatedBrokerWithRefreshTimeout` fixture)

   ```python
   def test_cl_3_l3_l5_cross_falsification_h1_active_refresh_timeout_halts_entry(
       simulated_broker_with_refresh_timeout, monkeypatch,
   ):
       """CL-3: Force Broker.refresh_positions() timeout
       (using SimulatedBrokerWithRefreshTimeout fixture per Tier 3 item E
       / DEF-SIM-BROKER-TIMEOUT-FIXTURE) AND H1 selection by S1a output.
       Verify the H-R2-2 HALT-ENTRY posture catches the composite —
       position marked halt_entry_until_operator_ack=True; no further
       SELL attempts; no phantom short.

       Composes L3 (broker-verification) + L5 (in-process logic). Uses
       the fixture variant from conftest_refresh_timeout.py.
       """
       # Mock S1a's selected_mechanism to "h1_cancel_and_await" if the
       # actual spike output differs (per regression-checklist invariant
       # 27 specific edge — CL-3 requires H1 to exercise the coupling).
       # Setup: ManagedPosition; locate-rejection on first SELL emit;
       # suppression engages; suppression-timeout fires;
       # refresh_positions() RAISES asyncio.TimeoutError via the fixture.
       # Expected: Branch 4 publishes phantom_short_retry_blocked alert
       # with verification_stale=True; HALT-ENTRY engages because H1 is
       # active; position.halt_entry_until_operator_ack=True;
       # subsequent SELL attempts on the position refuse.
   ```

   ### CL-4 (L1 + L2; misclassified stop-replacement)

   ```python
   def test_cl_4_l1_l2_misclassified_stop_replacement_l3_catches():
       """CL-4: Reservation succeeds but is_stop_replacement decision is
       wrong (e.g., emergency-flatten misclassified as stop-replacement);
       verify L3 ceiling catches the resulting over-flatten.

       Composes L1 (reservation-succeeds) + L2 (is_stop_replacement
       wrong) + L3 (ceiling catches).
       """
       # Setup: position with shares_total=100, cumulative_sold_shares=90;
       # emergency-flatten branch incorrectly invokes _check_sell_ceiling
       # with is_stop_replacement=True (misclassification — exemption
       # would normally be granted only for normal-retry path per H-R2-5).
       # Force the misclassification at the call site for this test.
       # Expected: L3 ceiling still catches via the cumulative_sold +
       # requested vs shares_total check, OR if the exemption was
       # incorrectly granted, the over-flatten emits and the test
       # fails — that failure mode is what CL-4 detects.
   ```

   ### CL-5 (L2 + L3; legitimate stop-replacement under suppression)

   ```python
   def test_cl_5_l2_l3_stop_replacement_with_active_suppression_no_false_fire():
       """CL-5: is_stop_replacement correctly disambiguates a
       stop-replacement (L2 grants exemption) AND locate-suppression for
       the position is active. Verify the protective stop-replacement
       path is allowed AND that Branch 4 does not falsely fire on it.

       Composes L2 (legitimate stop-replacement) + L3 (active
       suppression). Asserts no false-fire on legitimate path.
       """
       # Setup: position with active locate-suppression entry;
       # _resubmit_stop_with_retry normal-retry path triggers (NOT
       # emergency-flatten) — exemption granted via
       # is_stop_replacement=True.
       # Expected: stop-replacement allowed; Branch 4 does NOT fire on
       # this path; no phantom_short_retry_blocked alert.
   ```

   ### CL-7 (concurrent-caller correlation; NEW per Round 3 C-R3-1)

   ```python
   async def test_cl_7_concurrent_callers_no_stale_branch_2_classification(
       simulated_broker_with_refresh_timeout,
   ):
       """CL-7 (NEW per Round 3 C-R3-1): N=2 concurrent AC2.5 fallbacks
       (two coroutines each invoking Broker.refresh_positions()
       near-simultaneously; ≤10ms separation), broker state mutated
       between callers (e.g., position quantity changes between A's
       reqPositions and B's reqPositions via test-fixture injection);
       assert no stale Branch 2 classification — the single-flight
       serialization + 250ms coalesce window per Fix A guarantees
       coroutine B either awaits A's lock or coalesces on A's
       synchronization rather than reading a partially-converged cache.

       Falsifies if assertion holds WITHOUT the serialization mitigation
       (race observable) but holds WITH the mitigation.
       """
       # Setup: two coroutines invoke refresh_positions() with ≤10ms
       # separation; broker state mutated between A's invocation start
       # and B's invocation start (test-fixture injection).
       # Expected (with single-flight + coalesce): B reads same state
       # as A (or coalesces on A's synchronization); no stale Branch 2
       # classification.
       # Falsification: disable the lock + coalesce (mock-replace), assert
       # the race IS observable (counter-test); re-enable, assert the
       # race is NOT observable.
   ```

   ### Branch 4 unit test (using `SimulatedBrokerWithRefreshTimeout`)

   ```python
   def test_branch_4_verification_stale_metadata_emitted_on_refresh_timeout_in_process(
       simulated_broker_with_refresh_timeout,
   ):
       """Branch 4 in-process unit test using
       SimulatedBrokerWithRefreshTimeout fixture (the fixture-based
       equivalent of the S3b mock-raise test). Asserts:
       when refresh_positions() exceeds timeout_seconds, alert is
       published with verification_stale=True metadata +
       verification_failure_reason="TimeoutError" + position_id +
       symbol. Locate-suppression dict entry for the position is NOT
       cleared.

       Per invariant 25 + DEF-SIM-BROKER-TIMEOUT-FIXTURE.
       """
       # Setup: ManagedPosition with active suppression-timeout fallback
       # path; refresh_positions() raises asyncio.TimeoutError via fixture.
       # Expected: phantom_short_retry_blocked alert published with
       # metadata {verification_stale: True, verification_failure_reason:
       # "TimeoutError", position_id, symbol};
       # _locate_suppressed_until[position.id] still set (NOT cleared on
       # refresh failure — operator must investigate).
   ```

   **Effective test count: 7 logical / 7 effective at S5c.**

3. **Confirm cumulative test count target**:

   - Pre-S5c (after S5b close-out): 13 tests in `tests/integration/test_def204_round2_validation.py`.
   - Post-S5c: 13 + 6 CL + 1 Branch 4 = 20 tests in the file.
   - Sprint-total pytest: target 5,357–5,403 (5,269 baseline + 88–134 logical / 95–145 effective per Round 3 disposition aggregate).
   - The S5c close-out skill MUST run the FULL suite per DEC-328 final-review tier and report the exact pass count.

## Files to Modify

For each file the session edits, specify:

- **`tests/integration/conftest_refresh_timeout.py`** (NEW file, ≤80 LOC):
  - **Anchor:** module-level class definition `SimulatedBrokerWithRefreshTimeout` + Pytest fixture function.
  - **Edit shape:** insertion (new file).
  - **Pre-flight grep-verify:**
    ```
    $ ls tests/integration/conftest_refresh_timeout.py
    # Expected: file does NOT exist (this session creates it).
    ```
  - **LOC budget:** ≤80 LOC total. Per S5c compaction-risk score, exceeding 80 LOC pushes the new-file penalty from +2 to +4 (large-file threshold) and risks score landing at 15+ (HIGH).

- **`tests/integration/test_def204_round2_validation.py`** (MODIFIED — appends 7 tests):
  - **Anchor:** end-of-file insertion of 6 CL tests + 1 Branch 4 unit test.
  - **Edit shape:** insertion (append-only; do NOT modify the 13 S5a/S5b tests already in the file).
  - **Pre-flight grep-verify:**
    ```
    $ grep -c "^def test_\|^async def test_" tests/integration/test_def204_round2_validation.py
    # Expected: 13 (4 from S5a + 9 from S5b). After S5c: 20.
    ```

**Files NOT modified by S5c:** `argus/execution/order_manager.py`, `argus/execution/simulated_broker.py`, `argus/execution/ibkr_broker.py`, `argus/main.py`, `argus/core/config.py`, any production code. The fixture lives in test code only.

Line numbers MAY appear as directional cross-references but are NEVER the sole anchor.

## Constraints

- **Do NOT modify:**
  - `argus/execution/simulated_broker.py` (per SbC §"Do NOT modify" #2). The `SimulatedBrokerWithRefreshTimeout` fixture variant subclasses in test code only — production `simulated_broker.py` is unchanged.
  - `argus/execution/order_manager.py` (production-code state from S2a/S2b/S3a/S3b/S4a-i/S4a-ii/S4b is the validation target).
  - `argus/main.py`.
  - `argus/execution/ibkr_broker.py`.
  - `argus/core/config.py`.
  - DEC-385 / DEC-386 / DEC-388 entries in `docs/decision-log.md`.
  - Frontend (invariant 12).
  - DB schemas.
  - The `workflow/` submodule (RULE-018).
  - The 13 prior tests in `tests/integration/test_def204_round2_validation.py` (4 from S5a + 9 from S5b) — append-only.

- **Do NOT change:**
  - DEC-117 atomic-bracket invariants (invariant 1).
  - DEC-385 6-layer reconciliation (invariant 5).
  - DEC-386 4-layer OCA architecture (invariant 6).
  - DEC-388 alert observability (invariant 7).
  - The `_OCA_TYPE_BRACKET` constant deletion done at S4b (invariant 15).
  - The S2a-selected Path #1 mechanism. CL-3 may MOCK the mechanism to `"h1_cancel_and_await"` for the HALT-ENTRY coupling test, but does not modify the production code's selection.

- **Do NOT add:**
  - Real wall-clock `asyncio.sleep` calls in fixtures with positive durations >100ms (B-class halt B10).
  - A second fixture file in `tests/integration/`. The single `conftest_refresh_timeout.py` is the focused fixture per Tier 3 item E.
  - CL-6 (rollback + locate-suppression interaction) — explicitly OUT per Decision 5 with rationale documented in `docs/process-evolution.md`.
  - Production-side validation of IBKR API timing — AC5.6 explicitly scopes to in-process logic.
  - A CL test for `bracket_oca_type=1` rollback that DOES exercise `--allow-rollback-skip-confirm` in a way that bypasses the H-R3-4 interactive ack requirement in test code — the skip-confirm flag is for CI ONLY (SbC §19).

- Do NOT cross-reference other session prompts.

## Operator Choice (N/A this session)

S5c does not require operator pre-check.

## Canary Tests (N/A this session)

S5c appends to S5a/S5b's test file; the 13 prior tests are the implicit canary (must remain green throughout S5c's appends).

## Test Targets

After implementation:

- **Existing tests:** all must still pass — including the 13 prior tests in the same file AND every other test in the suite.
- **New tests appended to `tests/integration/test_def204_round2_validation.py`:**

  1. `test_cl_1_l1_fails_l3_catches_pending_reservation_false_positive` (CL-1; invariant 27)
  2. `test_cl_2_l4_fails_l2_catches_emergency_flatten_under_rollback` (CL-2; invariant 27 + invariant 16 cross-layer composition)
  3. `test_cl_3_l3_l5_cross_falsification_h1_active_refresh_timeout_halts_entry` (CL-3; invariant 27 + invariant 24 + invariant 25 — uses `SimulatedBrokerWithRefreshTimeout` fixture)
  4. `test_cl_4_l1_l2_misclassified_stop_replacement_l3_catches` (CL-4; invariant 27)
  5. `test_cl_5_l2_l3_stop_replacement_with_active_suppression_no_false_fire` (CL-5; invariant 27)
  6. `test_cl_7_concurrent_callers_no_stale_branch_2_classification` (CL-7; invariant 28 — NEW per Round 3 C-R3-1)
  7. `test_branch_4_verification_stale_metadata_emitted_on_refresh_timeout_in_process` (Branch 4 unit test; invariant 25 + DEF-SIM-BROKER-TIMEOUT-FIXTURE)

  **Effective test count: 7 logical / 7 effective.**

- **Test command** (S5c is FINAL — pre-flight scoped, but close-out invokes full suite per DEC-328):

  Pre-flight (before edit):
  ```
  python -m pytest tests/integration/ -n auto -q
  ```

  Close-out (after edit; FINAL session per DEC-328 final-review tier):
  ```
  python -m pytest --ignore=tests/test_main.py -n auto -q
  ```

  Expected pass count target: **5,357–5,403 pytest** (5,269 baseline + 88–134 new logical / 95–145 effective per Round 3 disposition aggregate). The close-out report MUST cite the exact post-S5c pass count.

## Config Validation (N/A this session)

S5c adds no config fields.

## Marker Validation (N/A this session)

S5c does not add pytest markers.

## Visual Review (N/A this session)

S5c is backend-only.

## Definition of Done

- [ ] `tests/integration/conftest_refresh_timeout.py` created (≤80 LOC) with `SimulatedBrokerWithRefreshTimeout` class + Pytest fixture.
- [ ] 7 new tests appended to `tests/integration/test_def204_round2_validation.py` (5 CL tests + 1 Branch 4 unit test + 1 CL-7).
- [ ] All 7 tests passing.
- [ ] Each individual test runtime ≤ 5s (B-class halt B10 threshold; cross-layer tests are slow + ugly by design but must still finish in <5s via fixture mocking).
- [ ] Production code untouched (`git diff HEAD~1 -- argus/` returns empty or only test directories).
- [ ] `tests/integration/conftest_refresh_timeout.py` is ≤80 LOC.
- [ ] FULL suite green at close-out per DEC-328 final-review tier (target 5,357–5,403 pytest).
- [ ] CI green on the session's final commit (RULE-050).
- [ ] Tier 2 review via @reviewer subagent — verdict CLEAR (or CONCERNS_RESOLVED).
- [ ] Close-out report written to file.
- [ ] Sprint-seal preconditions documented in close-out (DEC-390 materialization checklist; 6 NEW DEFs filed; 7 RSKs filed; etc.) — close-out skill enumerates these per AC6 + escalation-criteria § Closing the Sprint.

## Regression Checklist (Session-Specific)

After implementation, verify each of these:

| Check | How to Verify |
|-------|---------------|
| `tests/integration/conftest_refresh_timeout.py` ≤ 80 LOC | `wc -l tests/integration/conftest_refresh_timeout.py` |
| 6 CL tests + 1 Branch 4 unit test pass | `pytest tests/integration/test_def204_round2_validation.py -k "cl_\|branch_4"` |
| CL-3 uses `SimulatedBrokerWithRefreshTimeout` fixture | Read CL-3 source; confirm fixture parameter |
| CL-7 falsifies properly (race observable WITHOUT mitigation; not observable WITH) | Read CL-7 source; confirm both branches asserted |
| Branch 4 unit test asserts `verification_stale=True` + `verification_failure_reason="TimeoutError"` + `position_id` + `symbol` | Read Branch 4 unit test source |
| Branch 4 unit test asserts `_locate_suppressed_until[position.id]` NOT cleared on refresh failure | Read Branch 4 unit test source |
| Production code untouched | `git diff HEAD~1 -- argus/` returns empty (or test dirs only) |
| 13 prior S5a/S5b tests still green | `pytest tests/integration/test_def204_round2_validation.py -v -k "validate_\|composite_\|restart_\|reconstruct_"` |
| FULL suite at S5c close-out: 5,357–5,403 pytest | close-out skill runs full suite (DEC-328 final-review tier) |
| Vitest unchanged at 913 | `cd argus/ui && npx vitest run` (frontend immutability invariant 12) |
| Pre-existing flake count unchanged | DEF-150, DEF-167, DEF-171, DEF-190, DEF-192 (invariant 11) |
| Each individual test runtime ≤ 5s | `pytest --durations=10 tests/integration/test_def204_round2_validation.py` |
| `_OCA_TYPE_BRACKET` constant absent (preserves S4b) | `grep -c "_OCA_TYPE_BRACKET" argus/execution/order_manager.py` returns 0 (invariant 15) |
| AC4.4 OCA-type lock-step preserved (composite via CL-2) | CL-2 asserts; invariant 16 |

## Close-Out

After all work is complete, follow the close-out skill in `.claude/skills/close-out.md`.

The close-out report MUST include a structured JSON appendix at the end, fenced with ` ```json:structured-closeout `.

**Write the close-out report to a file** (DEC-330):

```
docs/sprints/sprint-31.92-def-204-round-2/session-s5c-closeout.md
```

The close-out MUST include:
- The exact post-S5c full-suite pass count (target 5,357–5,403 pytest).
- The exact LOC count of `tests/integration/conftest_refresh_timeout.py` (must be ≤80).
- Confirmation that the 13 prior S5a/S5b tests remained green throughout S5c's appends.
- Confirmation that production code (`argus/`) shows ZERO edits.
- Test runtime (per-test) for the 7 new tests, confirming each is ≤ 5s.
- **Sprint-seal precondition checklist** (per `escalation-criteria.md` § Closing the Sprint):
  - All 13 sessions Tier 2 verdict CLEAR.
  - M-R2-5 verdict received and dispositioned.
  - S5a's `sprint-31.92-validation-path1.json` artifact committed with `path1_safe: true`.
  - S5b's `sprint-31.92-validation-path2.json` artifact committed with `path2_suppression_works: true` AND `broker_verification_at_timeout_works: true`.
  - S5b's composite Pytest test green AND `sprint-31.92-validation-composite.json` committed.
  - S5b's restart-scenario test green.
  - S5c's 6 cross-layer composition tests + 1 Branch 4 unit test green.
  - `tests/integration/conftest_refresh_timeout.py` (`SimulatedBrokerWithRefreshTimeout` fixture) committed.
  - FULL suite green at S5c close-out (DEC-328 final-review tier).
  - DEC-390 written below in `docs/decision-log.md` per AC6 (likely deferred to D14 sprint-close doc-sync; flag in close-out).
  - DEF-204 row in `CLAUDE.md` to be marked **RESOLVED-PENDING-PAPER-VALIDATION** at D14 (NOT RESOLVED).
  - DEF-212 row in `CLAUDE.md` to be marked **RESOLVED** at D14.
  - 6 NEW DEFs from Tier 3 to be added to `CLAUDE.md` DEF table at D14: DEF-FAI-CALLBACK-ATOMICITY, DEF-CROSS-LAYER-EXPANSION, DEF-FAI-N-INCREASE, DEF-FAI-2-SCOPE, DEF-FAI-8-OPTION-A, DEF-SIM-BROKER-TIMEOUT-FIXTURE.
  - 7 new RSKs to be filed at D14.
  - Cessation criterion #5 counter explicitly RESET to 0/5.
  - Daily CI workflow added at sprint-close (operator-manual edit per `doc-update-checklist.md` C9; not in S5c diff).
  - Process-evolution lesson F.5 reaffirmation + FAI completeness pattern lesson + CL-6 deferral rationale.

## Tier 2 Review (Mandatory — @reviewer Subagent)

After the close-out is written to file and committed, invoke the @reviewer subagent.

Provide the @reviewer with:

1. The review context file: `docs/sprints/sprint-31.92-def-204-round-2/review-context.md`
2. The close-out report path: `docs/sprints/sprint-31.92-def-204-round-2/session-s5c-closeout.md`
3. The diff range: `git diff HEAD~1`
4. The test command (S5c is FINAL → **full suite** per DEC-328 final-review tier): `python -m pytest --ignore=tests/test_main.py -n auto -q`
5. Files that should NOT have been modified:
   - `argus/execution/order_manager.py`
   - `argus/execution/simulated_broker.py`
   - `argus/execution/ibkr_broker.py`
   - `argus/main.py`
   - `argus/core/config.py`
   - `argus/core/health.py`, `argus/api/routes/alerts.py`, `argus/api/websocket/alerts_ws.py`
   - Frontend
   - DB schemas
   - DEC-385 / DEC-386 / DEC-388 entries in decision-log
   - The `workflow/` submodule
   - The 13 prior S5a/S5b tests in `tests/integration/test_def204_round2_validation.py` (append-only)

The @reviewer must use the **backend safety reviewer** template.

The @reviewer will produce its review report at:

```
docs/sprints/sprint-31.92-def-204-round-2/session-s5c-review.md
```

## Post-Review Fix Documentation

If the @reviewer reports CONCERNS and you fix the findings within this same session, update the artifact trail (close-out → "Post-Review Fixes"; review → "Resolved" annotation + verdict update to `CONCERNS_RESOLVED`).

If the reviewer reports CLEAR or ESCALATE, skip this section entirely. ESCALATE on the FINAL session is particularly serious — operator decides whether to revert or fix-forward.

## Session-Specific Review Focus (for @reviewer)

1. **Production code untouched.** S5c is a test/validation-only session. `git diff HEAD~1 -- argus/` MUST return empty (or only touch test directories). Reviewer verifies via diff inspection.

2. **Append-only to S5a/S5b test file.** The 13 prior tests must remain byte-for-byte unchanged. Reviewer confirms via `git diff HEAD~1 -- tests/integration/test_def204_round2_validation.py` showing only end-of-file additions.

3. **Fixture LOC budget ≤80.** `wc -l tests/integration/conftest_refresh_timeout.py` MUST return ≤80. Exceeding triggers the large-file penalty per S5c compaction-risk score.

4. **Production `simulated_broker.py` untouched.** The `SimulatedBrokerWithRefreshTimeout` subclass lives in `tests/integration/conftest_refresh_timeout.py` ONLY. SbC §"Do NOT modify" #2 forbids semantic changes to production `simulated_broker.py`.

5. **All 6 CL tests + 1 Branch 4 unit test pass.** Reviewer runs the scoped command `pytest tests/integration/test_def204_round2_validation.py -k "cl_\|branch_4" -v` and confirms 7 tests pass.

6. **CL-3 uses the fixture.** Reviewer verifies CL-3's signature includes `simulated_broker_with_refresh_timeout` parameter. The Branch 4 unit test (test 7) similarly uses the fixture.

7. **CL-7 falsification logic correct.** CL-7 must assert: (a) the race IS observable WITHOUT the single-flight + coalesce mitigation (counter-test); (b) the race is NOT observable WITH the mitigation enabled. If only (b) is asserted, CL-7 cannot prove the fix is load-bearing — it would pass even if the mitigation were absent.

8. **Branch 4 metadata exhaustive.** The Branch 4 unit test asserts ALL FOUR metadata keys: `verification_stale=True`, `verification_failure_reason="TimeoutError"`, `position_id`, `symbol`. AND asserts `_locate_suppressed_until[position.id]` is NOT cleared on refresh failure (operator-triage signal).

9. **CL-6 NOT in the test list.** Reviewer confirms there is no `test_cl_6_*` test — CL-6 is explicitly OUT per Decision 5; rationale documented in `docs/process-evolution.md` at sprint-close per `doc-update-checklist.md` C10.

10. **No real wall-clock sleeps >100ms.** Reviewer scans new test code AND fixture for `asyncio.sleep(<positive_real>)` or `time.sleep(<positive_real>)`; the only allowed `asyncio.sleep` is the very small (≤1ms typical, ≤100ms max) sleep inside the fixture's `refresh_positions()` override that triggers the synthetic timeout.

11. **AC5.6 scope qualifier preserved.** Cross-layer test docstrings AND the close-out must explicitly state the in-process scope qualifier ("validates IN-PROCESS LOGIC against SimulatedBroker; does NOT validate IBKR-API timing").

12. **Per-test runtime ≤ 5s.** Reviewer runs `pytest --durations=10 tests/integration/test_def204_round2_validation.py` and confirms each new test is below 5s. Cross-layer tests are slow + ugly by design (per `templates/sprint-spec.md` v1.2.0) — they MUST still finish in <5s via `SimulatedBrokerWithRefreshTimeout` fixture mocking; reduce fixture scope OR mock the slow path; do NOT carry slow tests into the final suite.

13. **FULL-suite green at S5c close-out.** Reviewer runs `python -m pytest --ignore=tests/test_main.py -n auto -q` and confirms pass count is in target range 5,357–5,403. Failure to reach target (or full-suite red) is **B-class halt B3 / B4 — sprint cannot seal**.

14. **Sprint-seal precondition checklist completeness.** Reviewer verifies the close-out's sprint-seal precondition checklist enumerates all items per `escalation-criteria.md` § Closing the Sprint. Items typically deferred to D14 (DEC-390, DEF row markings, RSK filings, daily CI workflow) are flagged as such — not silently skipped.

## Sprint-Level Regression Checklist (for @reviewer)

The full Sprint-Level Regression Checklist is in `docs/sprints/sprint-31.92-def-204-round-2/regression-checklist.md` (34 invariants total).

✓-mandatory at S5c per the Per-Session Verification Matrix (S5c is the final-session sweep; nearly all invariants are validated in composition):

- **Invariant 1 (DEC-117 atomic bracket):** ✓ — preserved.
- **Invariant 5 (DEC-385 6-layer side-aware reconciliation):** ✓ — preserved.
- **Invariant 6 (DEC-386 4-layer OCA architecture):** ✓ — preserved; CL-2 stresses lock-step under rollback.
- **Invariant 7 (DEC-388 alert observability):** ✓ — preserved; Branch 4 unit test exercises `phantom_short_retry_blocked` alert path with `verification_stale=True` metadata.
- **Invariant 9 (`# OCA-EXEMPT:` mechanism):** ✓ — preserved.
- **Invariant 10 (test count baseline ≥ 5,269; target +7 at S5c, +88–134 sprint-total):** ✓ — full-suite count required at close-out.
- **Invariant 11 (pre-existing flake count):** ✓ — preserved.
- **Invariant 12 (frontend immutability):** ✓ — preserved.
- **Invariant 13 (SELL-volume ceiling pending+sold pattern):** ✓ — composite cross-layer via CL-1 + CL-4.
- **Invariant 14 (Path #2 fingerprint + position-keyed dict + broker-verification):** ✓ — composite via CL-3 + CL-5.
- **Invariant 15 (`_OCA_TYPE_BRACKET` constant deleted; S4b precondition):** ✓ — preserved.
- **Invariant 16 (AC4.4 OCA-type lock-step):** ✓ — composite via CL-2.
- **Invariant 18 (spike artifacts fresh + committed):** ✓ — S5a + S5b artifacts on `main`; daily CI workflow operator-task at sprint-close.
- **Invariant 21 (broker-verification three-branch coverage):** ✓ — composite via CL-3 + Branch 4 unit test.
- **Invariant 23 (synchronous-update invariant + reflective-pattern AST):** ✓ — composite via CL-1 (forces L1 false-positive; L3 catches).
- **Invariant 24 (HALT-ENTRY posture under H1 + refresh fail):** ✓ — composite via CL-3.
- **Invariant 25 (Branch 4 + `SimulatedBrokerWithRefreshTimeout` fixture):** ✓ — ESTABLISHES fixture + Branch 4 unit test.
- **Invariant 27 (5 cross-layer composition tests CL-1..CL-5):** ✓ — ESTABLISHES all 5 + CL-7.
- **Invariant 28 (single-flight serialization + 250ms coalesce window):** ✓ — composite via CL-7.

▢-soft (trust test suite unless suspicious diff): invariants 2, 3, 4, 8, 17, 19, 20, 22, 26, 29, 30, 31, 32, 33, 34.

## Sprint-Level Escalation Criteria (for @reviewer)

The full Sprint-Level Escalation Criteria are in `docs/sprints/sprint-31.92-def-204-round-2/escalation-criteria.md`.

Of particular relevance to S5c:

- **A3 (composite validation produces phantom_shorts > 0 OR `total_sold_le_total_bought: false` OR S5c CL-1/CL-2/CL-4/CL-5 fails):** halts sprint per A3. The mechanism closure is empirically falsified; same failure class that ended Sprint 31.91's `~98%` claim. Tier 3 reviews which session's coverage was insufficient. **Do NOT seal the sprint.**
- **A17 (CL-3 specifically — Branch 4 + H1 active without HALT-ENTRY firing):** halts sprint. The C-R2-1↔H-R2-2 coupling per Tier 3 item C is the structural defense for the FAI #2 + FAI #5 composite. CL-3 is the in-process safety net; if CL-3 fails OR was green but production exhibits the failure, the in-process fixture is missing a path.
- **B3 (pytest baseline ends below 5,269 at S5c close-out):** halt — sprint cannot seal.
- **B4 (CI fails on S5c's final commit AND failure is NOT a documented pre-existing flake):** halt per RULE-050. The sprint cannot seal until CI green.
- **B10 (any new pytest test > 5s individual runtime):** halt and investigate. Cross-layer tests are slow + ugly by design but MUST still finish in <5s via fixture mocking.
- **B1, B6, B8** — standard halt conditions.

### Verification Grep Precision

When running verification greps:
- Use `grep -c "^def test_\|^async def test_" tests/integration/test_def204_round2_validation.py` — expect exactly 20 hits post-S5c (4 from S5a + 9 from S5b + 7 from S5c).
- For LOC count of fixture file: `wc -l tests/integration/conftest_refresh_timeout.py` — expect ≤80.
- For full-suite pass count: read the final line of `pytest -q` output; pass count target 5,357–5,403.

### S5c Compaction-Risk Score Drift Disclosure (RULE-038)

The session-breakdown.md line 1584 manifest cites the post-amendment expected score for S5c as 11.5 with pre-amendment baseline 11. The actual session-breakdown scoring table at line 1574–1583 lands at 13.5 (Medium) post-amendment with 13 pre-amendment baseline. Per session-breakdown.md note (lines 1586–1598), this discrepancy is logged for the close-out manifest per RULE-038 — the disposition's amendment intent (add CL-7; keep within Medium tier) is preserved; the absolute baseline number is reconciled to the actual scoring table. **Reviewer should note this disclosure in the verdict; the Medium-tier classification is the load-bearing fact, not the absolute score.**

---

*End Sprint 31.92 Session S5c implementation prompt — FINAL session of Sprint 31.92.*

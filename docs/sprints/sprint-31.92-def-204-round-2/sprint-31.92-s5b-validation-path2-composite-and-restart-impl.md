# Sprint 31.92, Session S5b: Path #2 + Composite + Restart-Scenario Falsifiable Validation

## Pre-Flight Checks

Before making any changes:

1. **Read `.claude/rules/universal.md` in full and treat its contents as binding for this session.** The full set of universal RULE entries (currently RULE-001 through RULE-053) applies regardless of whether any specific rule is referenced inline in this prompt. Particularly load-bearing for S5b: RULE-038 (grep-verify discipline), RULE-040 (small-sample sweep / spike-artifact directional vs. authoritative — applies here because S5b is in-process logic validation, NOT production safety evidence), RULE-050 (CI green precondition).

2. Read these files to load context:
   - `argus/execution/order_manager.py` — anchor by:
     - `_flatten_position`, `_trail_flatten`, `_check_flatten_pending_timeouts`, `_escalation_update_stop` (the 4 standalone-SELL emit sites where Path #2 detection was wired at S3a/S3b).
     - `_check_sell_ceiling` (the 5 ceiling-guard surfaces from S4a-i).
     - `is_reconstructed` field on `ManagedPosition` (S4a-i + the `reconstruct_from_broker` single-line addition per AC3.7).
     - `halt_entry_until_operator_ack` field on `ManagedPosition` (S3b per Tier 3 item C).
     - **Read what S3a/S3b/S4a-i actually shipped; do not assume implementations.**
   - `argus/execution/ibkr_broker.py::_is_locate_rejection` — anchor by helper name (post-S3a state).
   - `argus/execution/simulated_broker.py` — extensibility for locate-rejection-with-release replay AND restart simulation (anchor by class name). Production `simulated_broker.py` MUST NOT be modified by S5b; fixtures live in test code only.
   - `tests/integration/test_def204_round2_validation.py` — created at S5a. S5b APPENDS scenarios to this existing file.
   - `docs/sprints/sprint-31.92-def-204-round-2/sprint-spec.md` §"Acceptance Criteria" Deliverable 5 (AC5.2 + AC5.3 Pytest-side-effect + AC5.4 restart scenario).
   - `scripts/spike-results/spike-def204-round2-path2-results.json` — read the captured `_LOCATE_REJECTED_FINGERPRINT` substring + `recommended_locate_suppression_seconds`.

3. Run the test baseline (DEC-328 — Session 11 of 13 of sprint, **scoped** because S5b is non-final):

   ```
   python -m pytest tests/integration/ tests/execution/order_manager/ -n auto -q
   ```

   Expected: all passing (full suite was confirmed by S5a's close-out).

4. Verify you are on the correct branch: **`main`**.

5. **Run the structural-anchor grep-verify commands** below. If drift is detected, disclose under RULE-038 in the close-out.

   ```bash
   # Verify Path #2 emit sites + helper exist post-S3a/S3b
   grep -n "def _flatten_position\|def _trail_flatten\|def _check_flatten_pending_timeouts\|def _escalation_update_stop" argus/execution/order_manager.py
   # Expected: 4 hits (one per function). Directional only.

   grep -n "def _is_locate_rejection" argus/execution/ibkr_broker.py
   # Expected: 1 hit.

   grep -n "def _check_sell_ceiling" argus/execution/order_manager.py
   # Expected: 1 hit.

   # Verify is_reconstructed and halt_entry_until_operator_ack fields exist on ManagedPosition
   grep -n "is_reconstructed\|halt_entry_until_operator_ack" argus/execution/order_manager.py | head -20
   # Expected: at least 2 hits (field declarations on the dataclass).

   # Verify the spike artifact exists with the gating fields
   python -c "import json; d = json.load(open('scripts/spike-results/spike-def204-round2-path2-results.json')); print(d.get('status'), d.get('recommended_locate_suppression_seconds'))"
   # Expected: status "PROCEED", suppression seconds populated. If KeyError or wrong status → halt.

   # Verify S5a's test file exists
   ls tests/integration/test_def204_round2_validation.py
   # Expected: exists; created at S5a; S5b APPENDS.
   ```

6. Verify S3a + S3b + S4a-i + S4a-ii + S4b + S5a are all complete and merged on `main`:

   ```bash
   ls docs/sprints/sprint-31.92-def-204-round-2/session-{s3a,s3b,s4a-i,s4a-ii,s4b,s5a}-closeout.md
   # All 6 close-out files must exist.
   ```

   If any close-out is missing, **HALT** — S5b depends on all six having landed.

## Objective

Build the Path #2 (locate-rejection-with-broker-verified-release) in-process validation harness, the composite Pytest integration tests producing `sprint-31.92-validation-composite.json` as a Pytest side-effect with daily CI freshness, the canonical C-2 restart-during-active-position regression test (AC5.4), and the deferred ceiling-emit-site coverage (S4a-i deferred 3 of 5 sites to here per AC3.2), per-`ManagedPosition` ceiling integration (AC3.4), cross-position safety (deferred from S3b per H-2), and config-flag-disabled coverage. **AC5.2 framing: same in-process scope qualifier as AC5.1 — does NOT validate IBKR API timing or production safety.** Cessation criterion #5 (5 paper sessions clean post-seal) remains the production-validation gate.

## Requirements

1. **Create `scripts/validate_def204_round2_path2.py`** — orchestrator script (~150 LOC, held to budget for compaction-risk):

   ```python
   """Sprint 31.92 S5b: Path #2 in-process falsifiable validation.

   Drives SimulatedBroker through a synthetic locate-rejection-with-release
   scenario: ARGUS attempts SELL on a hard-to-borrow microcap; broker
   raises locate-rejection; suppression engages per
   _locate_suppressed_until[position.id]; held order eventually fills
   (synthetic clock advancement); broker-verification at suppression
   timeout queries broker.refresh_positions() and applies three-branch
   classification.

   AC5.2 framing: validates IN-PROCESS LOGIC against SimulatedBroker;
   does NOT validate IBKR-API timing. Cessation criterion #5 is the
   production-validation gate.
   """
   ```

   Output JSON schema at `scripts/spike-results/sprint-31.92-validation-path2.json`:

   ```json
   {
     "validation_run_date": "<ISO 8601 UTC>",
     "fingerprint_under_test": "<the substring captured by S1b>",
     "fixture": "synthetic_locate_rejection_with_release",
     "path2_suppression_works": true,
     "sell_emits_per_position_within_window": 1,
     "held_order_fill_propagates": true,
     "broker_verification_at_timeout_works": true,
     "n_trials": 1,
     "argus_baseline_sha": "<git rev-parse HEAD short>",
     "spike_path2_artifact_sha": "<sha of spike-def204-round2-path2-results.json>"
   }
   ```

2. **Implement composite validation as Pytest integration test with JSON side-effect** (AC5.3):

   ```python
   # tests/integration/test_def204_round2_validation.py (appended)

   def test_composite_validation_zero_phantom_shorts_under_load(tmp_path):
       """AC5.3: composite under benign synthetic-broker load.
       Writes sprint-31.92-validation-composite.json BEFORE assertion.
       Daily CI updates artifact mtime."""
       # ... orchestrate Path #1 + Path #2 + ceiling + reconstructed-position
       # under synthetic-broker load; write JSON; assert
       # phantom_shorts_observed == 0 AND ceiling_violations_observed == 0.

   def test_composite_validation_ceiling_blocks_under_adversarial_load():
       """AC3.2 (remaining 4 of 5 emit sites deferred from S4a-i):
       under adversarial synthetic-broker load (forced over-flatten
       attempts at all 5 standalone-SELL emit sites),
       ceiling_violations_correctly_blocked >= 1."""
   ```

   The composite artifact lives at `scripts/spike-results/sprint-31.92-validation-composite.json`. Test fixture writes it BEFORE the assertion fires (so mtime tracks freshness even if the assertion fails — operator can see what state was captured).

3. **Implement the canonical C-2 restart-during-active-position test** (AC5.4):

   ```python
   def test_restart_during_active_position_refuses_argus_sells():
       """AC5.4 / invariant 19: spawn ManagedPosition normally,
       partial-fill via T1, simulate restart by calling
       reconstruct_from_broker() (or directly setting
       is_reconstructed=True if test architecture requires), assert
       subsequent _trail_flatten, _flatten_position,
       _check_flatten_pending_timeouts, _escalation_update_stop
       invocations all refuse to emit SELL."""
       # Step 1: spawn ManagedPosition with shares_total=100; partial T1 fill
       #         transfers 50 shares to cumulative_sold_shares.
       # Step 2: call reconstruct_from_broker() (or directly set
       #         position.is_reconstructed=True per the field's
       #         single-line set in the live function per AC3.7).
       # Step 3: invoke each of the 4 standalone-SELL paths in turn.
       # Step 4: assert NONE of them emit a SELL — all return early via
       #         _check_sell_ceiling's is_reconstructed short-circuit.
       # Step 5: optional — assert the operator-manual flatten path
       #         (scripts/ibkr_close_all_positions.py) is NOT blocked
       #         by the refusal posture (refusal applies to
       #         ARGUS-emitted SELLs ONLY per AC3.7).
   ```

4. **Implement deferred coverage tests** appended to `tests/integration/test_def204_round2_validation.py`:

   - `test_validate_path2_script_produces_suppression_works_true` (AC5.2)
   - `test_validate_path2_script_emits_one_sell_per_position_within_window`
   - `test_validate_path2_script_held_order_fill_propagates`
   - `test_composite_validation_per_managed_position_ceiling_not_per_symbol_integration` (AC3.4 — multi-position integration; deferred from S4a-i)
   - `test_composite_validation_multi_position_same_symbol_cross_safety` (AC2.4 — deferred from S3b; cross-position safety per Round-1 H-2)
   - `test_reconstruct_from_broker_initializes_is_reconstructed_true_and_zero_counters` (AC3.6 + AC3.7 — unit-level field initialization)

5. **Document daily CI workflow as sprint-close operational task** — but DO NOT add CI YAML in S5b.

   Per the session-breakdown.md note (lines 1460–1463), adding the daily workflow to `.github/workflows/` is documented in `doc-update-checklist.md` C9 as a sprint-close operational task (operator-manual edit post-merge); does NOT count as a modified file at S5b. The composite test produces the artifact; the daily CI workflow that runs the test is added by the operator at sprint-close. **DO NOT modify any `.github/workflows/` file in S5b.**

## Files to Modify

For each file the session edits, specify:

- **`scripts/validate_def204_round2_path2.py`** (NEW file):
  - **Anchor:** module-level `__main__` entry point + `main()` function.
  - **Edit shape:** insertion (new file).
  - **Pre-flight grep-verify:**
    ```
    $ ls scripts/validate_def204_round2_path2.py
    # Expected: file does NOT exist (this session creates it).
    ```

- **`scripts/spike-results/sprint-31.92-validation-path2.json`** (NEW file, autogenerated):
  - **Anchor:** the JSON schema fields above.
  - **Edit shape:** insertion (autogenerated by script first run; committed to repo).

- **`scripts/spike-results/sprint-31.92-validation-composite.json`** (NEW file, autogenerated as Pytest side-effect):
  - **Anchor:** Pytest fixture writes the JSON BEFORE the composite test's assertions.
  - **Edit shape:** insertion (autogenerated; committed to repo).

- **`tests/integration/test_def204_round2_validation.py`** (MODIFIED — appends scenarios):
  - **Anchor:** end-of-file insertion of 9 new logical tests + the path2 fixtures.
  - **Edit shape:** insertion (append-only; do NOT modify the 4 S5a tests already in the file).
  - **Pre-flight grep-verify:**
    ```
    $ grep -c "^def test_" tests/integration/test_def204_round2_validation.py
    # Expected: 4 (S5a's tests). After S5b: 13.
    ```

**Files NOT modified by S5b:** `argus/execution/order_manager.py`, `argus/execution/simulated_broker.py`, `argus/execution/ibkr_broker.py`, `argus/main.py`, any production code. The fixtures live in test code only. Per session-breakdown.md note (lines 1460–1463), `.github/workflows/` modification is a sprint-close operational task, NOT an S5b file modification.

Line numbers MAY appear as directional cross-references but are NEVER the sole anchor.

## Constraints

- **Do NOT modify:**
  - `argus/execution/simulated_broker.py` (per SbC §"Do NOT modify" #2; the `SimulatedBrokerWithRefreshTimeout` fixture lands at S5c per Tier 3 item E / DEF-SIM-BROKER-TIMEOUT-FIXTURE).
  - `argus/execution/order_manager.py` (production-code state from S2a/S2b/S3a/S3b/S4a-i is the validation target).
  - `argus/main.py`.
  - `argus/execution/ibkr_broker.py` (post-S3a state; `_is_locate_rejection` helper preserved).
  - `argus/core/config.py`.
  - DEC-385 / DEC-386 / DEC-388 entries in `docs/decision-log.md`.
  - Frontend (invariant 12).
  - DB schemas.
  - The `workflow/` submodule (RULE-018).
  - The 4 S5a tests already in `tests/integration/test_def204_round2_validation.py` — append-only.
  - **`.github/workflows/`** — sprint-close operational task per `doc-update-checklist.md` C9; NOT an S5b modification.

- **Do NOT change:**
  - DEC-117 atomic-bracket invariants (invariant 1).
  - DEC-369 broker-confirmed reconciliation immunity (invariant 3).
  - DEC-372 stop retry caps + backoff (invariant 4).
  - DEC-385 6-layer reconciliation (invariant 5).
  - DEC-386 4-layer OCA architecture (invariant 6).
  - DEC-388 alert observability (invariant 7).
  - DEF-158 retry 3-branch side-check verbatim (invariant 8).
  - The S2a-selected Path #1 mechanism — S5b validates whatever S2a/S2b shipped.

- **Do NOT add:**
  - Real wall-clock `asyncio.sleep` calls in fixtures (B-class halt B10).
  - A `SimulatedBrokerWithRefreshTimeout` fixture variant — that lands at S5c per Tier 3 item E.
  - Production-side validation of IBKR API timing — AC5.2 explicitly scopes to in-process logic.
  - A live-IBKR network call from validation scripts.
  - CI workflow YAML — sprint-close operator task.

- Do NOT cross-reference other session prompts.

## Operator Choice (N/A this session)

S5b does not require operator pre-check.

## Canary Tests (N/A this session)

S5b appends to S5a's test file; the 4 S5a tests are the implicit canary (must remain green throughout S5b's appends).

## Test Targets

After implementation:

- **Existing tests:** all must still pass — including the 4 S5a tests in the same file.
- **New tests appended to `tests/integration/test_def204_round2_validation.py`:**

  1. `test_validate_path2_script_produces_suppression_works_true` (AC5.2)
     - Invoke `validate_def204_round2_path2`; assert resulting JSON has `path2_suppression_works=true`.
  2. `test_validate_path2_script_emits_one_sell_per_position_within_window`
     - Same invocation; assert `sell_emits_per_position_within_window <= 1`.
  3. `test_validate_path2_script_held_order_fill_propagates`
     - Same invocation; assert `held_order_fill_propagates=true` AND `broker_verification_at_timeout_works=true`.
  4. `test_composite_validation_zero_phantom_shorts_under_load` (AC5.3 / Pytest with JSON side-effect)
     - Composite test writes `sprint-31.92-validation-composite.json` BEFORE assertion; assert under benign load `phantom_shorts_observed == 0` AND `ceiling_violations_observed == 0`.
  5. `test_composite_validation_ceiling_blocks_under_adversarial_load` (AC3.2 — remaining 4 of 5 emit sites)
     - Forced over-flatten attempts at all 5 standalone-SELL emit sites; assert `ceiling_violations_correctly_blocked >= 1`.
  6. `test_composite_validation_per_managed_position_ceiling_not_per_symbol_integration` (AC3.4)
     - Two `ManagedPosition`s on same symbol each have own ceiling (per-position, NOT per-symbol).
  7. `test_composite_validation_multi_position_same_symbol_cross_safety` (AC2.4)
     - Two `ManagedPosition`s on same symbol; locate-rejection on position A; position B's `_locate_suppressed_until` entry NOT affected.
  8. `test_restart_during_active_position_refuses_argus_sells` — **CANONICAL C-2 RESTART TEST** (AC5.4 / invariant 19)
     - Spawn ManagedPosition; partial-fill via T1; simulate restart via `reconstruct_from_broker()`; assert all 4 standalone-SELL paths refuse to emit SELL when `is_reconstructed=True`.
  9. `test_reconstruct_from_broker_initializes_is_reconstructed_true_and_zero_counters` (AC3.6 + AC3.7)
     - Unit-level: assert reconstruct-derived positions initialize `cumulative_pending_sell_shares=0`, `cumulative_sold_shares=0`, `is_reconstructed=True`, `shares_total=abs(broker_position.shares)`.

  **Effective test count: 9 logical / 9 effective.**

- **Test command** (scoped per DEC-328, S5b is non-final):

  ```
  python -m pytest tests/integration/ tests/execution/order_manager/ -n auto -q
  ```

## Config Validation (N/A this session)

S5b adds no config fields.

## Marker Validation (N/A this session)

S5b does not add pytest markers.

## Visual Review (N/A this session)

S5b is backend-only.

## Definition of Done

- [ ] `scripts/validate_def204_round2_path2.py` created (≤150 LOC).
- [ ] `scripts/spike-results/sprint-31.92-validation-path2.json` autogenerated and committed with `path2_suppression_works=true`, `sell_emits_per_position_within_window <= 1`, `held_order_fill_propagates=true`, `broker_verification_at_timeout_works=true` (AC5.2).
- [ ] `scripts/spike-results/sprint-31.92-validation-composite.json` autogenerated and committed (AC5.3).
- [ ] 9 new logical tests appended to `tests/integration/test_def204_round2_validation.py` (S5a's 4 tests preserved unchanged).
- [ ] All tests passing.
- [ ] Restart scenario test (`test_restart_during_active_position_refuses_argus_sells`) green (AC5.4 / invariant 19).
- [ ] Each individual test runtime ≤ 5s (B-class halt B10 threshold).
- [ ] No `.github/workflows/` modifications (sprint-close operator task).
- [ ] No production code modifications.
- [ ] CI green on the session's final commit (RULE-050).
- [ ] Tier 2 review via @reviewer subagent — verdict CLEAR (or CONCERNS_RESOLVED).
- [ ] Close-out report written to file.

## Regression Checklist (Session-Specific)

After implementation, verify each of these:

| Check | How to Verify |
|-------|---------------|
| Path #2 validation JSON has 4 gating fields true | Tests 1–3 assert |
| Composite JSON written BEFORE assertion (mtime tracks freshness) | Test 4 fixture order verified by code inspection |
| Composite under benign load: phantom_shorts=0, ceiling_violations=0 | Test 4 asserts |
| Composite under adversarial load: ceiling_violations_correctly_blocked >= 1 | Test 5 asserts |
| Per-`ManagedPosition` ceiling, NOT per-symbol | Test 6 asserts |
| Cross-position safety preserved (locate-rejection on A doesn't affect B) | Test 7 asserts |
| Restart scenario: 4 paths refuse SELL when is_reconstructed=True | Test 8 asserts |
| reconstruct_from_broker initializes 4 fields correctly | Test 9 asserts |
| `argus/execution/order_manager.py` byte-for-byte unchanged | `git diff HEAD~1 -- argus/execution/order_manager.py` returns empty |
| `argus/execution/simulated_broker.py` byte-for-byte unchanged | `git diff HEAD~1 -- argus/execution/simulated_broker.py` returns empty |
| `argus/execution/ibkr_broker.py` byte-for-byte unchanged | `git diff HEAD~1 -- argus/execution/ibkr_broker.py` returns empty |
| `argus/main.py` byte-for-byte unchanged | `git diff HEAD~1 -- argus/main.py` returns empty |
| `.github/workflows/` byte-for-byte unchanged (sprint-close operator task) | `git diff HEAD~1 -- '.github/workflows/'` returns empty |
| Frontend immutability holds | `git diff HEAD~1 -- 'argus/ui/'` returns empty (invariant 12) |
| `_OCA_TYPE_BRACKET` constant absent (preserves S4b) | `grep -c "_OCA_TYPE_BRACKET" argus/execution/order_manager.py` returns 0 (invariant 15) |
| 4 S5a tests still green | `pytest tests/integration/test_def204_round2_validation.py -v -k "validate_path1"` |
| DEF-158 3-branch side-check unchanged (invariant 8) | grep + diff verify |
| Pytest baseline ≥ 5,269 (target after S5b: ~5,345–5,370) | full suite via close-out skill |
| Each individual test runtime ≤ 5s | `pytest --durations=10 tests/integration/test_def204_round2_validation.py` |

## Close-Out

After all work is complete, follow the close-out skill in `.claude/skills/close-out.md`.

The close-out report MUST include a structured JSON appendix at the end, fenced with ` ```json:structured-closeout `.

**Write the close-out report to a file** (DEC-330):

```
docs/sprints/sprint-31.92-def-204-round-2/session-s5b-closeout.md
```

The close-out MUST include:
- The 3 JSON artifacts' full content quoted inline (path2 + composite + a delta against S5a's path1).
- Confirmation that all S5a tests remained green throughout S5b's appends.
- Confirmation that `argus/execution/order_manager.py`, `simulated_broker.py`, `ibkr_broker.py`, `main.py`, and `.github/workflows/` show ZERO edits.
- Test runtime (per-test) for the 9 new tests, confirming each is ≤ 5s.
- Explicit reference to the sprint-close operator task: "Daily CI workflow at `.github/workflows/...` is added by operator at sprint-close per `doc-update-checklist.md` C9 — NOT in this session's diff."

## Tier 2 Review (Mandatory — @reviewer Subagent)

After the close-out is written to file and committed, invoke the @reviewer subagent.

Provide the @reviewer with:

1. The review context file: `docs/sprints/sprint-31.92-def-204-round-2/review-context.md`
2. The close-out report path: `docs/sprints/sprint-31.92-def-204-round-2/session-s5b-closeout.md`
3. The diff range: `git diff HEAD~1`
4. The test command (S5b is non-final → scoped per DEC-328): `python -m pytest tests/integration/ tests/execution/order_manager/ -n auto -q`
5. Files that should NOT have been modified:
   - `argus/execution/order_manager.py`
   - `argus/execution/simulated_broker.py`
   - `argus/execution/ibkr_broker.py`
   - `argus/main.py`
   - `argus/core/config.py`
   - `argus/core/health.py`, `argus/api/v1/alerts.py`, `argus/ws/v1/alerts.py`
   - `.github/workflows/` (sprint-close operator task per `doc-update-checklist.md` C9)
   - Frontend
   - DB schemas
   - DEC-385 / DEC-386 / DEC-388 entries in decision-log
   - The `workflow/` submodule
   - The 4 S5a tests in `tests/integration/test_def204_round2_validation.py` (append-only)

The @reviewer must use the **backend safety reviewer** template.

The @reviewer will produce its review report at:

```
docs/sprints/sprint-31.92-def-204-round-2/session-s5b-review.md
```

## Post-Review Fix Documentation

If the @reviewer reports CONCERNS and you fix the findings within this same session, update the artifact trail (close-out → "Post-Review Fixes"; review → "Resolved" annotation + verdict update to `CONCERNS_RESOLVED`).

If the reviewer reports CLEAR or ESCALATE, skip this section entirely.

## Session-Specific Review Focus (for @reviewer)

1. **Production code untouched.** S5b is a test/validation-only session. `git diff HEAD~1 -- argus/` MUST return empty (or only touch test directories). Reviewer verifies via diff inspection.

2. **`.github/workflows/` untouched.** Daily CI workflow YAML is a sprint-close operator task per `doc-update-checklist.md` C9 — NOT in S5b's diff. Reviewer confirms via `git diff HEAD~1 -- '.github/workflows/'` returning empty.

3. **Append-only to S5a test file.** S5a's 4 tests must remain byte-for-byte unchanged. Reviewer confirms via `git diff HEAD~1 -- tests/integration/test_def204_round2_validation.py` showing only end-of-file additions.

4. **Composite JSON write-before-assert ordering.** Test 4's fixture must call `json.dump(...)` BEFORE the `assert phantom_shorts_observed == 0` line. Reviewer reads test 4 source; this ordering is the AC5.3 freshness contract — if the assertion fails, the artifact still captures the failure state for operator triage.

5. **Restart-scenario test exhaustive.** Test 8 invokes ALL 4 standalone-SELL paths (`_trail_flatten`, `_flatten_position`, `_check_flatten_pending_timeouts`, `_escalation_update_stop`). Reviewer counts the assertion calls; if any path is missing, this is the canonical C-2 coverage hole that A-class halt A15 fires on in production.

6. **Reconstruct-from-broker initialization fields.** Test 9 asserts initialization of FOUR fields: `cumulative_pending_sell_shares=0`, `cumulative_sold_shares=0`, `is_reconstructed=True`, `shares_total=abs(broker_position.shares)`. Reviewer confirms test 9's assertion list is exhaustive.

7. **Per-`ManagedPosition` (NOT per-symbol) ceiling.** Test 6 explicitly creates two distinct `ManagedPosition`s on the same symbol and asserts each has its own ceiling. Reviewer verifies the test's setup constructs distinct ULIDs.

8. **No real wall-clock sleeps.** Reviewer scans new test code for `asyncio.sleep(<positive_real>)` or `time.sleep(<positive_real>)`; any hit is a B-class halt B10 candidate.

9. **AC5.2 + AC5.3 scope qualifier preserved.** Both validation scripts AND the composite test docstrings AND the close-out must explicitly state the in-process scope qualifier ("validates IN-PROCESS LOGIC against SimulatedBroker; does NOT validate IBKR-API timing").

10. **Per-test runtime ≤ 5s.** Reviewer runs `pytest --durations=10 tests/integration/test_def204_round2_validation.py` and confirms each new test is below 5s.

## Sprint-Level Regression Checklist (for @reviewer)

The full Sprint-Level Regression Checklist is in `docs/sprints/sprint-31.92-def-204-round-2/regression-checklist.md` (34 invariants total).

✓-mandatory at S5b per the Per-Session Verification Matrix:

- **Invariant 1 (DEC-117 atomic bracket):** PASS — production code untouched.
- **Invariant 2 (DEC-364 cancel_all_orders no-args ABC):** PASS.
- **Invariant 3 (DEC-369 broker-confirmed immunity):** PASS — composes additively with `is_reconstructed=True` per AC3.6.
- **Invariant 4 (DEC-372 stop retry caps + backoff):** PASS.
- **Invariant 5 (DEC-385 6-layer side-aware reconciliation):** PASS.
- **Invariant 6 (DEC-386 4-layer OCA architecture):** PASS.
- **Invariant 7 (DEC-388 alert observability):** PASS.
- **Invariant 8 (DEF-158 3-branch side-check verbatim):** PASS — preserved.
- **Invariant 9 (`# OCA-EXEMPT:` mechanism):** PASS.
- **Invariant 10 (test count baseline ≥ 5,269; target +9):** PASS.
- **Invariant 11 (pre-existing flake count):** PASS.
- **Invariant 12 (frontend immutability):** PASS.
- **Invariant 13 (SELL-volume ceiling pending+sold pattern):** ✓-mandatory — composite test 5 stresses adversarial load at all 5 emit sites.
- **Invariant 17 (AMD-2 mechanism-conditional):** ✓-mandatory — composite preserves the S2a mechanism choice.
- **Invariant 18 (spike artifacts fresh + committed):** ✓-mandatory — S5b's 2 new artifacts join the freshness checklist.
- **Invariant 19 (`is_reconstructed` refusal posture):** ✓-mandatory — VALIDATES via test 8 + test 9.
- **Invariant 20 (pending-reservation state transitions):** ✓-mandatory — composite re-exercises in integration.
- **Invariant 21 (broker-verification three-branch coverage):** ✓-mandatory — Path #2 fixture exercises three-branch classification.

▢-soft (trust test suite unless suspicious diff): invariants 14, 15, 16, 22, 23, 24, 25, 26.

## Sprint-Level Escalation Criteria (for @reviewer)

The full Sprint-Level Escalation Criteria are in `docs/sprints/sprint-31.92-def-204-round-2/escalation-criteria.md`.

Of particular relevance to S5b:

- **A3 (composite validation produces phantom_shorts > 0 OR `total_sold_le_total_bought: false` OR restart-scenario test fails):** halts sprint per A3. This is the same failure class that ended Sprint 31.91's `~98%` claim. Tier 3 reviews which session's coverage was insufficient and what new mechanism path the validation surfaced. **Do NOT seal the sprint.**
- **A11 (ceiling false-positive in production):** if test 5 (composite-adversarial) fires a ceiling violation on a LEGITIMATE SELL, the implementation is wrong; halt and audit pending-reservation state transitions per AC3.1.
- **A15 (restart-scenario test fails OR production paper-session reveals an ARGUS-emitted SELL on `is_reconstructed=True` position):** halts sprint. The `is_reconstructed` refusal posture (AC3.7) is the structural defense for the C-2 restart-safety hole; failure means the conservative posture is leaking.
- **A16 (`is_reconstructed` refusal posture creates operationally undesirable failure mode):** halt; conservative refusal has trapped capital. Tier 3 reviews operator-manual flatten infrastructure.
- **B10 (any new pytest test > 5s individual runtime):** halt and investigate. Path #2 + composite fixtures must use synthetic-clock loops.
- **B1, B3, B4, B6, B8** — standard halt conditions.

### Verification Grep Precision

When running verification greps:
- Use `grep -c "^def test_" tests/integration/test_def204_round2_validation.py` — expect exactly 13 hits post-S5b (4 from S5a + 9 from S5b).
- For composite JSON write-before-assert ordering, inspect the test source line-by-line; do NOT rely on a string search.
- For per-test runtime, use `pytest --durations=10` (showing top 10 slowest).

---

*End Sprint 31.92 Session S5b implementation prompt.*

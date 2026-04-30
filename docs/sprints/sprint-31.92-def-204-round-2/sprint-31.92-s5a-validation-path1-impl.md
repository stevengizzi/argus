# Sprint 31.92, Session S5a: Path #1 In-Process Falsifiable Validation Against SimulatedBroker

## Pre-Flight Checks

Before making any changes:

1. **Read `.claude/rules/universal.md` in full and treat its contents as binding for this session.** The full set of universal RULE entries (currently RULE-001 through RULE-053) applies regardless of whether any specific rule is referenced inline in this prompt. Particularly load-bearing for S5a: RULE-038 (grep-verify discipline), RULE-040 (small-sample sweep / spike-artifact directional vs. authoritative — applies here because S5a is in-process logic validation, NOT production safety evidence), RULE-050 (CI green precondition).

2. Read these files to load context:
   - `argus/execution/order_manager.py::_trail_flatten` and `argus/execution/order_manager.py::_resubmit_stop_with_retry` — anchor by function names. These are the post-S2a/S2b state where Path #1 mechanism (H2 amend / H4 hybrid / H1 cancel-and-await) was wired. **Read what S2a/S2b actually landed; do not assume mechanism choice.**
   - `argus/execution/simulated_broker.py` — anchor by class name `SimulatedBroker`. Confirm extensibility for the Path #1 fixture (concurrent-trigger trace) per S1a/S1b spike outputs. Production `simulated_broker.py` MUST NOT be modified by S5a; fixtures live in test code only (per SbC §"Do NOT modify" #2).
   - `docs/sprints/sprint-31.92-def-204-round-2/sprint-spec.md` §"Acceptance Criteria" Deliverable 5 (AC5.1).
   - `scripts/spike-results/spike-def204-round2-path1-results.json` — read the `selected_mechanism` field (`"h2_amend_stop"` / `"h4_hybrid"` / `"h1_cancel_and_await"`); the validation script's `mechanism_under_test` field MUST match.
   - `docs/sprints/sprint-31.92-def-204-round-2/session-s2a-closeout.md` — read the "Mechanism Selected" section to confirm what S2a actually shipped.

3. Run the test baseline (DEC-328 — Session 10 of 13 of sprint, **scoped** because S5a is non-final):

   ```
   python -m pytest tests/integration/ tests/execution/ -n auto -q
   ```

   Expected: all passing (full suite was confirmed by S4b's close-out).

4. Verify you are on the correct branch: **`main`**.

5. **Run the structural-anchor grep-verify commands** below. If drift is detected, disclose under RULE-038 in the close-out and proceed against the actual structural anchors.

   ```bash
   # Verify _trail_flatten + _resubmit_stop_with_retry anchors exist post-S2a/S2b
   grep -n "def _trail_flatten\|def _resubmit_stop_with_retry" argus/execution/order_manager.py
   # Expected: 2 hits (one per function). Directional only.

   # Verify SimulatedBroker class is intact (no semantic changes per SbC)
   grep -n "^class SimulatedBroker" argus/execution/simulated_broker.py
   # Expected: 1 hit.

   # Verify the spike artifact exists with selected_mechanism field populated
   python -c "import json; d = json.load(open('scripts/spike-results/spike-def204-round2-path1-results.json')); print(d.get('selected_mechanism'))"
   # Expected: one of "h2_amend_stop", "h4_hybrid", "h1_cancel_and_await". If KeyError or None → halt.
   ```

6. Verify S2a + S2b + S4a-i + S4a-ii + S4b are all complete and merged on `main`:

   ```bash
   ls docs/sprints/sprint-31.92-def-204-round-2/session-{s2a,s2b,s4a-i,s4a-ii,s4b}-closeout.md
   # All 5 close-out files must exist.
   ```

   If any close-out is missing, **HALT** — S5a depends on all five having landed.

## Objective

Build a falsifiable in-process validation harness for Path #1 (trail-stop / bracket-stop concurrent-trigger over-flatten) that drives the SimulatedBroker through the canonical BITU 13:41 trace scenario (long position, bracket stop at $14.39, trail tripped at $14.44 in same tick), produces a JSON artifact at `scripts/spike-results/sprint-31.92-validation-path1.json` with the gating fields, and wires the validation as a Pytest integration test so daily CI catches regressions. **AC5.1 framing: this validates IN-PROCESS LOGIC against SimulatedBroker; it does NOT validate IBKR-API-interaction logic, network packet loss during cancel/amend propagation, or `modifyOrder` response timing in production.** Cessation criterion #5 (5 paper sessions clean post-seal) remains the production-validation gate.

## Requirements

1. **Create `scripts/validate_def204_round2_path1.py`** — orchestrator script (≤150 LOC, held to budget for compaction-risk):

   ```python
   """Sprint 31.92 S5a: Path #1 in-process falsifiable validation.

   Drives SimulatedBroker through the canonical BITU 13:41 trace scenario:
   long position with bracket stop at $14.39; trail tripped at $14.44 in
   same tick. Asserts no phantom shorts emerge under the S2a-selected
   mechanism (H2 amend / H4 hybrid / H1 cancel-and-await).

   AC5.1 framing: validates IN-PROCESS LOGIC against SimulatedBroker; does
   NOT validate IBKR-API-interaction logic. Cessation criterion #5 is the
   production-validation gate.
   """
   ```

   The script's CLI accepts `--output-path` (default `scripts/spike-results/sprint-31.92-validation-path1.json`) and runs synchronously. The output JSON schema:

   ```json
   {
     "validation_run_date": "<ISO 8601 UTC>",
     "mechanism_under_test": "<h2_amend_stop|h4_hybrid|h1_cancel_and_await>",
     "fixture": "bitu_13_41_concurrent_trigger",
     "path1_safe": true,
     "phantom_shorts_observed": 0,
     "total_sold_le_total_bought": true,
     "n_trials": 1,
     "argus_baseline_sha": "<git rev-parse HEAD short>",
     "spike_path1_artifact_sha": "<sha of spike-def204-round2-path1-results.json>"
   }
   ```

   Read `selected_mechanism` from the spike artifact at `scripts/spike-results/spike-def204-round2-path1-results.json` to populate `mechanism_under_test`.

2. **Implement the SimulatedBroker concurrent-trigger fixture** inline in the test file (NOT in `simulated_broker.py`):

   ```python
   # tests/integration/test_def204_round2_validation.py
   class _BituConcurrentTriggerFixture:
       """Fixture: long BITU position; bracket stop at $14.39; trail tripped
       at $14.44 in same tick. Forces the concurrent-trigger race that
       Path #1's mechanism prevents."""
       SYMBOL = "BITU"
       ENTRY_PRICE = 14.50
       STOP_PRICE = 14.39
       TRAIL_TRIGGER_PRICE = 14.44
       SHARES_TOTAL = 100
       # ... fixture impl that drives SimulatedBroker through the trace
   ```

   The fixture composes `SimulatedBroker` + `OrderManager` + `_trail_flatten` invocation in a deterministic synchronous loop. **No `asyncio.sleep` calls with real wall-clock duration** — use synthetic-clock advancement only, to keep individual test runtime under 5s (per B-class halt B10).

3. **Wire validation as Pytest integration tests** in `tests/integration/test_def204_round2_validation.py` (~100 LOC; this file will grow at S5b + S5c):

   ```python
   def test_validate_path1_script_produces_path1_safe_true():
       """AC5.1: the orchestrator script produces path1_safe=true."""
       # Invoke validate_def204_round2_path1 module-level entrypoint;
       # assert resulting JSON has path1_safe=True.

   def test_validate_path1_script_observes_zero_phantom_shorts():
       """Composite: phantom_shorts_observed must be exactly 0."""

   def test_validate_path1_script_total_sold_le_total_bought():
       """Composite: total_sold ≤ total_bought invariant per AC1.1."""

   def test_validate_path1_artifact_committed_to_repo():
       """Verify the JSON artifact exists at the expected path with
       valid schema (path1_safe, phantom_shorts_observed,
       total_sold_le_total_bought, mechanism_under_test,
       validation_run_date)."""
   ```

   All 4 tests run in ≤2s each (the SimulatedBroker fixture is fully synchronous).

4. **Commit the JSON artifact** to the repo at `scripts/spike-results/sprint-31.92-validation-path1.json`. The artifact is in-process falsifiable evidence; per regression invariant 18 it must exist on `main` BEFORE sprint-close (D14 doc-sync).

   The artifact is **regenerable** via `python scripts/validate_def204_round2_path1.py` — daily CI workflow (added separately at sprint-close per `doc-update-checklist.md` C9; NOT part of S5a's modified-files set) updates the mtime.

## Files to Modify

For each file the session edits, specify:

- **`scripts/validate_def204_round2_path1.py`** (NEW file):
  - **Anchor:** module-level `__main__` entry point + `main()` function.
  - **Edit shape:** insertion (new file).
  - **Pre-flight grep-verify:**
    ```
    $ ls scripts/validate_def204_round2_path1.py
    # Expected: file does NOT exist (this session creates it).
    ```

- **`scripts/spike-results/sprint-31.92-validation-path1.json`** (NEW file, autogenerated):
  - **Anchor:** the JSON schema fields above.
  - **Edit shape:** insertion (autogenerated by script first run; committed to repo).

- **`tests/integration/test_def204_round2_validation.py`** (NEW file):
  - **Anchor:** module-level test function definitions; `_BituConcurrentTriggerFixture` class.
  - **Edit shape:** insertion (new file).
  - **Pre-flight grep-verify:**
    ```
    $ ls tests/integration/test_def204_round2_validation.py
    # Expected: file does NOT exist (this session creates it; S5b + S5c append to it).
    ```

**Files NOT modified by S5a:** `argus/execution/order_manager.py`, `argus/execution/simulated_broker.py`, `argus/main.py`, any production code. The fixtures live in test code only.

Line numbers MAY appear as directional cross-references but are NEVER the sole anchor.

## Constraints

- **Do NOT modify:**
  - `argus/execution/simulated_broker.py` (per SbC §"Do NOT modify" #2). Fixtures live in test code only.
  - `argus/execution/order_manager.py` (post-S2a/S2b state is the validation target — modifying production code at S5a invalidates the validation contract).
  - `argus/main.py`.
  - `argus/execution/ibkr_broker.py`.
  - DEC-385 / DEC-386 / DEC-388 entries in `docs/decision-log.md`.
  - Frontend (invariant 12).
  - DB schemas.
  - The `workflow/` submodule (RULE-018).

- **Do NOT change:**
  - DEC-117 atomic-bracket invariants (invariant 1).
  - DEC-385 6-layer reconciliation (invariant 5).
  - DEC-386 4-layer OCA architecture (invariant 6).
  - The `_OCA_TYPE_BRACKET` constant deletion done at S4b (invariant 15) — must remain absent.
  - The S2a-selected Path #1 mechanism — S5a validates whatever S2a shipped; do not "improve" the mechanism.

- **Do NOT add:**
  - Real wall-clock `asyncio.sleep` calls in the fixture (B-class halt B10).
  - A new SimulatedBroker subclass in `simulated_broker.py` proper (the `SimulatedBrokerWithRefreshTimeout` fixture variant lands at S5c per Tier 3 item E / DEF-SIM-BROKER-TIMEOUT-FIXTURE; do NOT pre-add it here).
  - Production-side validation of IBKR API timing — AC5.1 explicitly scopes to in-process logic.
  - A live-IBKR network call from the validation script — the script must run offline / in CI without IBKR credentials.

- Do NOT cross-reference other session prompts. This prompt is standalone.

## Operator Choice (N/A this session)

S5a does not require operator pre-check. The validation surface is committed-to in `sprint-spec.md` AC5.1.

## Canary Tests (N/A this session)

S5a is a new validation harness, not a behavior modification. There is no pre-existing baseline to canary against; the validation IS the canary.

## Test Targets

After implementation:

- **Existing tests:** all must still pass.
- **New tests in `tests/integration/test_def204_round2_validation.py`:**

  1. `test_validate_path1_script_produces_path1_safe_true` (AC5.1)
     - Invoke `validate_def204_round2_path1` module-level entrypoint or run via subprocess; assert resulting JSON has `path1_safe=true`.
  2. `test_validate_path1_script_observes_zero_phantom_shorts`
     - Same invocation; assert `phantom_shorts_observed == 0`.
  3. `test_validate_path1_script_total_sold_le_total_bought`
     - Same invocation; assert `total_sold_le_total_bought == true`.
  4. `test_validate_path1_artifact_committed_to_repo`
     - Verify file exists at `scripts/spike-results/sprint-31.92-validation-path1.json` with valid schema (all required fields present + non-null + correct types).

  **Effective test count: 4 logical / 4 effective.** No parametrization at S5a.

- **Test command** (scoped per DEC-328, S5a is non-final):

  ```
  python -m pytest tests/integration/ tests/execution/ -n auto -q
  ```

## Config Validation (N/A this session)

S5a adds no config fields.

## Marker Validation (N/A this session)

S5a does not add pytest markers.

## Visual Review (N/A this session)

S5a is backend-only.

## Definition of Done

- [ ] `scripts/validate_def204_round2_path1.py` created (≤150 LOC).
- [ ] `scripts/spike-results/sprint-31.92-validation-path1.json` autogenerated and committed.
- [ ] `tests/integration/test_def204_round2_validation.py` created with 4 tests.
- [ ] All 4 tests passing.
- [ ] Validation JSON has `path1_safe=true`, `phantom_shorts_observed=0`, `total_sold_le_total_bought=true`, `mechanism_under_test` matching the S2a-selected mechanism (AC5.1).
- [ ] Each individual test runtime ≤ 5s (B-class halt B10 threshold).
- [ ] CI green on the session's final commit (RULE-050).
- [ ] Tier 2 review via @reviewer subagent — verdict CLEAR (or CONCERNS_RESOLVED).
- [ ] Close-out report written to file.

## Regression Checklist (Session-Specific)

After implementation, verify each of these:

| Check | How to Verify |
|-------|---------------|
| Validation JSON has `path1_safe=true` | Test 1 asserts |
| Validation JSON has `phantom_shorts_observed=0` | Test 2 asserts |
| Validation JSON has `total_sold_le_total_bought=true` | Test 3 asserts |
| Artifact committed at expected path with valid schema | Test 4 asserts |
| `mechanism_under_test` matches `selected_mechanism` from spike artifact | Read both JSONs in test 4; assert equality |
| `argus/execution/order_manager.py` byte-for-byte unchanged | `git diff HEAD~1 -- argus/execution/order_manager.py` returns empty |
| `argus/execution/simulated_broker.py` byte-for-byte unchanged | `git diff HEAD~1 -- argus/execution/simulated_broker.py` returns empty |
| `argus/main.py` byte-for-byte unchanged | `git diff HEAD~1 -- argus/main.py` returns empty |
| Frontend immutability holds | `git diff HEAD~1 -- 'argus/ui/'` returns empty (invariant 12) |
| Pytest baseline ≥ 5,269 (target after S5a: ~5,336–5,361) | full suite via close-out skill |
| Pre-existing flake count unchanged | DEF-150, DEF-167, DEF-171, DEF-190, DEF-192 (invariant 11) |
| Each individual test runtime ≤ 5s | `pytest --durations=10 tests/integration/test_def204_round2_validation.py` |
| `_OCA_TYPE_BRACKET` constant absent (preserves S4b) | `grep -c "_OCA_TYPE_BRACKET" argus/execution/order_manager.py` returns 0 (invariant 15) |
| AMD-2 mechanism-conditional framing preserved (invariant 17) | Verify `mechanism_under_test` field is one of the three valid mechanisms |

## Close-Out

After all work is complete, follow the close-out skill in `.claude/skills/close-out.md`.

The close-out report MUST include a structured JSON appendix at the end, fenced with ` ```json:structured-closeout `.

**Write the close-out report to a file** (DEC-330):

```
docs/sprints/sprint-31.92-def-204-round-2/session-s5a-closeout.md
```

Do NOT just print the report in the terminal. Create the file, write the full report (including the structured JSON appendix) to it, and commit it.

The close-out MUST include:
- The JSON artifact's full content quoted inline (so the close-out is self-contained for audit).
- The S2a-selected mechanism (`mechanism_under_test`) explicitly cited.
- Confirmation that `argus/execution/order_manager.py`, `argus/execution/simulated_broker.py`, and `argus/main.py` show ZERO edits.
- Test runtime (per-test) for the 4 new tests, confirming each is ≤ 5s.

## Tier 2 Review (Mandatory — @reviewer Subagent)

After the close-out is written to file and committed, invoke the @reviewer subagent to perform the Tier 2 review within this same session.

Provide the @reviewer with:

1. The review context file: `docs/sprints/sprint-31.92-def-204-round-2/review-context.md`
2. The close-out report path: `docs/sprints/sprint-31.92-def-204-round-2/session-s5a-closeout.md`
3. The diff range: `git diff HEAD~1`
4. The test command (S5a is non-final → scoped per DEC-328): `python -m pytest tests/integration/ tests/execution/ -n auto -q`
5. Files that should NOT have been modified:
   - `argus/execution/order_manager.py`
   - `argus/execution/simulated_broker.py`
   - `argus/main.py`
   - `argus/execution/ibkr_broker.py`
   - `argus/core/config.py`
   - `argus/core/health.py`, `argus/api/v1/alerts.py`, `argus/ws/v1/alerts.py`
   - Frontend
   - DB schemas
   - DEC-385 / DEC-386 / DEC-388 entries in decision-log
   - The `workflow/` submodule

The @reviewer must use the **backend safety reviewer** template (`templates/review-prompt.md` from the workflow metarepo).

The @reviewer will produce its review report at:

```
docs/sprints/sprint-31.92-def-204-round-2/session-s5a-review.md
```

## Post-Review Fix Documentation

If the @reviewer reports CONCERNS and you fix the findings within this same session, you MUST update the artifact trail (close-out file → "Post-Review Fixes" section; review file → "Resolved" annotation + verdict update to `CONCERNS_RESOLVED`).

If the reviewer reports CLEAR or ESCALATE, skip this section entirely.

## Session-Specific Review Focus (for @reviewer)

1. **Production code untouched.** S5a is a test/validation-only session. `git diff HEAD~1 -- argus/` MUST return empty (or only touch test directories). Reviewer verifies via diff inspection.

2. **Mechanism alignment.** The `mechanism_under_test` field in the validation JSON MUST match the `selected_mechanism` field in `scripts/spike-results/spike-def204-round2-path1-results.json`. If they diverge, the validation is testing a different mechanism than what S2a/S2b shipped — that is the silent-drift failure mode RULE-051 catches.

3. **Synthetic clock only.** No real wall-clock `asyncio.sleep` in the fixture. Reviewer scans the test file for `asyncio.sleep(<positive_real>)` calls; any hit is a B-class halt B10 candidate.

4. **Artifact schema completeness.** The JSON has all required fields: `validation_run_date`, `mechanism_under_test`, `fixture`, `path1_safe`, `phantom_shorts_observed`, `total_sold_le_total_bought`, `n_trials`, `argus_baseline_sha`, `spike_path1_artifact_sha`. Test 4 asserts this; reviewer confirms test 4's assertion list is exhaustive.

5. **AC5.1 scope qualifier preserved.** The script docstring AND the close-out AND the JSON artifact must all explicitly state: "validates IN-PROCESS LOGIC against SimulatedBroker; does NOT validate IBKR-API-interaction logic." This framing is non-negotiable per RULE-040 + AC5.1; treating the artifact as production safety evidence is the failure mode.

6. **Fixture lives in test code.** `_BituConcurrentTriggerFixture` (or equivalent) MUST live in `tests/integration/test_def204_round2_validation.py`, NOT in `argus/execution/simulated_broker.py`. SbC §"Do NOT modify" #2 explicitly forbids semantic changes to production `simulated_broker.py`.

7. **Per-test runtime ≤ 5s.** Reviewer runs `pytest --durations=10 tests/integration/test_def204_round2_validation.py` and confirms each new test is below 5s.

## Sprint-Level Regression Checklist (for @reviewer)

The full Sprint-Level Regression Checklist is in `docs/sprints/sprint-31.92-def-204-round-2/regression-checklist.md` (34 invariants total).

✓-mandatory at S5a per the Per-Session Verification Matrix:

- **Invariant 1 (DEC-117 atomic bracket):** PASS — production code untouched; the validation exercises but does not modify the bracket-placement contract.
- **Invariant 2 (DEC-364 cancel_all_orders no-args ABC):** PASS.
- **Invariant 5 (DEC-385 6-layer side-aware reconciliation):** PASS.
- **Invariant 6 (DEC-386 4-layer OCA architecture):** PASS.
- **Invariant 9 (`# OCA-EXEMPT:` mechanism):** PASS.
- **Invariant 10 (test count baseline ≥ 5,269; target +4):** PASS.
- **Invariant 11 (pre-existing flake count):** PASS.
- **Invariant 12 (frontend immutability):** PASS.
- **Invariant 15 (`_OCA_TYPE_BRACKET` constant deleted; S4b precondition):** PASS — preserved.
- **Invariant 17 (AMD-2 mechanism-conditional):** VALIDATES — S5a's `mechanism_under_test` matches the S2a-shipped mechanism.
- **Invariant 18 (spike artifacts fresh + committed):** ESTABLISHES — S5a's artifact joins the freshness checklist.

▢-soft (trust test suite unless suspicious diff): invariants 13, 16, 19, 20.

## Sprint-Level Escalation Criteria (for @reviewer)

The full Sprint-Level Escalation Criteria are in `docs/sprints/sprint-31.92-def-204-round-2/escalation-criteria.md`.

Of particular relevance to S5a:

- **A3 (composite validation produces phantom_shorts > 0):** halts sprint per A3. If S5a's `phantom_shorts_observed != 0` OR `total_sold_le_total_bought == false`, the mechanism closure is empirically falsified — same failure class that ended Sprint 31.91's `~98%` claim. Tier 3 reviews which session's coverage was insufficient and what new mechanism path the validation surfaced. **Do NOT seal the sprint.**
- **B10 (any new pytest test > 5s individual runtime):** halt and investigate. The Path #1 fixture must use synthetic-clock loops, not unmocked propagation.
- **B1, B3, B4, B6, B8** — standard halt conditions.

### Verification Grep Precision

When running verification greps:
- For schema completeness in test 4, use `assert "field_name" in json_data` for each required field, not a substring search.
- For per-test runtime, use `pytest --durations=10` (not `--durations=N` with N too small).

---

*End Sprint 31.92 Session S5a implementation prompt.*

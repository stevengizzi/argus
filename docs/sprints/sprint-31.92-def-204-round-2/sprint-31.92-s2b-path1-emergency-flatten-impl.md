# Sprint 31.92, Session 2b: Path #1 in `_resubmit_stop_with_retry` Emergency-Flatten + Conditionally `_escalation_update_stop` + H-R2-2 HALT-ENTRY Tests

> **⚠️ PENDING OPERATOR CONFIRMATION**
>
> This prompt is finalized only when:
> 1. S1a JSON artifact at `scripts/spike-results/spike-def204-round2-path1-results.json` is committed to `main` AND
> 2. Operator confirms `selected_mechanism` ∈ {`h2_amend`, `h4_hybrid`, `h1_cancel_and_await`} in writing per Decision 7 (and the H-R2-2-tightened gate language in `sprint-spec.md` § Hypothesis Prescription) AND
> 3. S2a close-out report is committed to `main` and documents the chosen mechanism + AMD-2 framing in its "Mechanism Selected" section.
>
> The Pre-Flight Checks below assume the spike artifact is present AND S2a's mechanism implementation has landed. If either is absent, halt and surface to operator.

## Pre-Flight Checks

Before making any changes:

1. **Read `.claude/rules/universal.md` in full and treat its contents as binding for this session.** RULE-038 (grep-verify discipline), RULE-039 (risky batch edit staging), RULE-050 (CI green) apply. The full set of universal RULE entries (currently RULE-001 through RULE-053) applies regardless of whether any specific rule is referenced inline in this prompt.

2. Read these files to load context:
   - `argus/execution/order_manager.py::_resubmit_stop_with_retry` (the editing
     target — emergency-flatten branch where DEC-372 retry cap is exhausted;
     anchor by function name; line numbers directional only) +
     `_escalation_update_stop` (conditional editing target IFF S1a confirmed
     amend semantics apply OR cancel-and-await translates cleanly; anchor by
     function name)
   - `docs/decision-log.md::DEC-372` (stop retry caps + emergency-flatten path)
   - `docs/sprints/sprint-31.92-def-204-round-2/sprint-spec.md` §"Acceptance
     Criteria" Deliverable 1 (specifically AC1.3 — extended surface to
     `_resubmit_stop_with_retry` emergency branch + AC1.4 AMD-8/AMD-4 guards
     preserved + AC1.5 mechanism-conditional AMD-2 framing + AC1.6 conditional
     audit logging) AND §"Hypothesis Prescription" H-R2-2 H1-fallback-locate-reject
     branch coupling
   - `docs/sprints/sprint-31.92-def-204-round-2/session-2a-closeout.md` —
     S2a close-out's "Mechanism Selected" section (the chosen mechanism and
     AMD-2 framing govern this session's identical mechanism application);
     also references the helper signature if S2a introduced a private
     `_amend_or_fallback()` helper for H4 hybrid logic.

3. Run the test baseline (DEC-328 — Session 4+ of sprint, scoped):

   ```
   python -m pytest tests/execution/order_manager/ -n auto -q
   ```

   Expected: all passing (full suite was confirmed by S2a's close-out).
   Note: In autonomous mode, the expected test count is dynamically adjusted
   by the runner based on the previous session's actual results.

4. Verify you are on the correct branch: **`main`**.

5. **Run the structural-anchor grep-verify commands** from the "Files to Modify"
   section below. For each entry, run the verbatim grep-verify command and confirm
   the anchor still resolves to the expected location. If drift is detected,
   disclose under RULE-038 in the close-out and proceed against the actual
   structural anchors. If the anchor is not found at all, HALT and request
   operator disposition rather than guess.

6. **Verify S1a + S2a deliverables present and consistent:**

   ```bash
   # S1a artifact present + PROCEED:
   test -f scripts/spike-results/spike-def204-round2-path1-results.json && \
     python -c "import json,sys; r=json.load(open('scripts/spike-results/spike-def204-round2-path1-results.json')); \
       sys.exit(0 if r.get('status')=='PROCEED' and r.get('selected_mechanism') in {'h2_amend','h4_hybrid','h1_cancel_and_await'} else 1)" \
     && echo "S1a artifact OK" \
     || { echo "S1a artifact missing or status != PROCEED — HALT"; exit 1; }

   # S2a close-out present:
   test -f docs/sprints/sprint-31.92-def-204-round-2/session-2a-closeout.md \
     || { echo "S2a close-out missing — HALT"; exit 1; }
   ```

   Read both: the S1a `selected_mechanism` field AND S2a's "Mechanism Selected"
   section. They MUST agree. If they disagree, halt — escalate to operator.

7. **Determine `_escalation_update_stop` applicability.** Read S1a's JSON
   carefully for any field flagging whether the chosen mechanism applies cleanly
   to `_escalation_update_stop` (e.g., a field like
   `escalation_update_stop_applicability: {h2: true, h4: true, h1: false}` or
   equivalent). If S1a does NOT confirm applicability OR the cancel-and-await
   semantics do NOT translate cleanly, the
   `_escalation_update_stop` test (test 3 below) is SKIPPED with documented
   reason and the function body is NOT modified at this session.
   This decision must be made BEFORE editing — it determines whether the session
   modifies one function or two.

## Objective

Apply S2a's chosen mechanism (H2 amend-stop-price / H4 hybrid / H1 cancel-and-await)
to `_resubmit_stop_with_retry` emergency-flatten branch (DEC-372 retry-cap
exhausted) — the second Path #1 surface per AC1.3. Conditionally apply the
mechanism to `_escalation_update_stop` IFF S1a confirms applicability (per
Pre-Flight #7). Add 7 tests covering AC1.3 mechanism preservation across the
extended surface, DEC-372 retry-cap + backoff regression, OCA-already-filled
short-circuit on the emergency-flatten surface, AMD-8 guard preservation, and
the H-R2-2 HALT-ENTRY posture under H1-fallback-locate-reject (Tier 3 item C
coupling).

## Requirements

1. **Apply S2a's chosen mechanism to `_resubmit_stop_with_retry` emergency-flatten
   branch** verbatim. The mechanism dispatch in `_resubmit_stop_with_retry`'s
   emergency-flatten path (where DEC-372's retry cap is exhausted and the code
   issues a market SELL as a final safety) must use the SAME H2/H4/H1 dispatch
   that S2a installed in `_trail_flatten`. If S2a introduced a private helper
   (e.g., `_amend_or_fallback()` for H4 hybrid logic), reuse that helper — do
   NOT re-implement the dispatch logic. Cross-session field-shape and helper-
   signature agreement is load-bearing.

2. **Preserve DEC-372 retry-cap + exponential-backoff invariants byte-for-byte.**
   `_resubmit_stop_with_retry` retains its 1s → 2s → 4s backoff progression and
   its retry cap (typically 3). The mechanism dispatch fires ONLY when the cap
   is exhausted (the emergency-flatten branch). Test 6 (`test_path1_dec372_backoff_unchanged`)
   regresses this explicitly.

3. **Preserve AMD-8 + `_handle_oca_already_filled` short-circuit on the
   emergency-flatten surface** byte-for-byte (AC1.4; regression invariants 6 + 17
   specific edges). Test 4 (`test_path1_emergency_flatten_oca_already_filled_short_circuit`)
   regresses the OCA-already-filled SAFE-marker path on the new surface.

4. **Conditionally apply S2a's mechanism to `_escalation_update_stop`**
   (per Pre-Flight #7 applicability decision). If applicable: same dispatch
   pattern; same AMD-8/AMD-4/`_handle_oca_already_filled` preservation. If NOT
   applicable: function body unchanged; test 3 SKIPPED with documented reason.

5. **AC1.6 operator-audit logging extends to the emergency-flatten branch**
   (conditional on H1 OR H4 selection). The structured log line per S2a's
   Requirement 3 fires identically on this surface — required keys
   (`event="amd2_supersede"`, `symbol`, `position_id`,
   `mechanism ∈ {"h1_cancel_and_await", "h4_fallback"}`,
   `cancel_propagation_ms`) AND consumed identically by future log analysis.
   No structural change to the log emission; only the call site differs.

6. **H-R2-2 HALT-ENTRY tests for H1-fallback-locate-reject branch** (NEW per
   Tier 3 item C). The `position.halt_entry_until_operator_ack: bool = False`
   field on `ManagedPosition` is wired by S4a-i; **this session's tests reference
   the field shape but do NOT add the field to production code.** Cross-session
   field-shape agreement is load-bearing; S2b's test fixtures construct
   `ManagedPosition` instances with `halt_entry_until_operator_ack=False` (the
   default, per AC2.8 / AC3 fields) and assert that under H1-fallback-locate-reject
   the field becomes True.

   The test 7 (`test_path1_h1_fallback_locate_reject_halts_entry`) is the test
   required by regression invariant 24 (which lands at S3b for the S3b path; this
   session establishes the surface that consumes the same posture). Conditional
   on H1 OR H4 selection: cancel-and-await dispatches, then locate-rejection
   arrives at SELL emission; assert
   `halt_entry_until_operator_ack=True` is set on the position; assert
   `phantom_short_retry_blocked` alert published with metadata
   `{verification_stale: True, verification_failure_reason: <type-name>,
   position_id, symbol}`; assert no further SELL attempts on the position.

   **Note on field source-of-truth:** the `halt_entry_until_operator_ack` field
   is added to `ManagedPosition` at S4a-i. S2b's tests USE the field (via test
   fixtures that construct `ManagedPosition` with the field present). If running
   S2b BEFORE S4a-i has landed (i.e., session order strictly S2b → S3a → S3b →
   S4a-i), the test fixture creates the field as part of the test setup (e.g.,
   via `dataclasses.replace(position, halt_entry_until_operator_ack=False)` if
   the dataclass has been extended) OR the test is SKIPPED with reason
   `"halt_entry_until_operator_ack field added at S4a-i"`. Document the
   approach taken in the close-out.

7. **Tests — extend `tests/execution/order_manager/test_def204_round2_path1.py`**
   (created at S2a). Add 7 new tests at this session:

   - `test_path1_resubmit_stop_emergency_flatten_no_overflatten` — mirror BITU
     race for `_resubmit_stop_with_retry` emergency branch (AC1.3); SimulatedBroker
     fixture; assert `total_sold ≤ position.shares_total` after retry-cap
     exhaustion fires the mechanism dispatch.
   - `test_path1_dec372_retry_cap_exhaustion_preserves_mechanism` — verify the
     mechanism (H2/H4/H1) fires at the cap-exhaustion boundary, not earlier
     (i.e., normal retries 1+2+3 do NOT trigger the new mechanism; only the
     emergency-flatten after cap exhaustion does).
   - `test_path1_escalation_update_stop_no_overflatten` — IF S1a applicability
     confirmed for `_escalation_update_stop`; SKIP otherwise with documented
     reason. Same shape as `_resubmit_stop_with_retry` test.
   - `test_path1_emergency_flatten_oca_already_filled_short_circuit` — preserve
     DEC-386 S1b SAFE-marker path on emergency-flatten surface. Mock the inner
     cancel/amend to raise `OCA-already-filled`; assert short-circuit fires;
     assert no standalone SELL emitted; assert position transitions to
     fully-closed.
   - `test_path1_emergency_flatten_amd8_guard_preserved` — assert AMD-8 no-op
     fires when `_flatten_pending` is already set; mechanism dispatch does NOT
     fire; no double-flatten.
   - `test_path1_dec372_backoff_unchanged` — regression on DEC-372 exponential
     backoff (1s, 2s, 4s) under simulated retry triggers; assert the timing
     unchanged.
   - **NEW per H-R2-2 + Tier 3 item C** `test_path1_h1_fallback_locate_reject_halts_entry`
     — IF H1 selected OR H4-with-fallback-active. Fixture: cancel-and-await
     dispatches, then locate-rejection arrives at the subsequent
     `place_order(SELL)` (mocked broker raises locate-rejection); assert
     `position.halt_entry_until_operator_ack == True`; assert
     `phantom_short_retry_blocked` alert published with `verification_stale:
     true` metadata; assert no further SELL attempts on the position. SKIP
     with reason if H2 selected.

   Test deltas summary: +7 logical tests at S2b (regression checklist line 154).

## Files to Modify

For each file the session edits, specify:

1. **`argus/execution/order_manager.py`** (MODIFY — `_resubmit_stop_with_retry`
   emergency-flatten branch + conditionally `_escalation_update_stop`):
   - Anchor (PRIMARY): function `_resubmit_stop_with_retry` (method on
     `OrderManager`) — specifically the emergency-flatten branch where DEC-372's
     retry cap is exhausted.
   - Edit shape: replacement of the emergency-flatten dispatch (where the code
     currently issues a market SELL as a final safety) with the S2a-installed
     mechanism dispatch. Preserve DEC-372 retry-cap + backoff + AMD-8 +
     `_handle_oca_already_filled` byte-for-byte.
   - Pre-flight grep-verify:
     ```
     $ grep -n "def _resubmit_stop_with_retry" argus/execution/order_manager.py
     # Expected: exactly 1 hit. (Directional only — verify the function still
     # exists at the structural anchor; line number drift acceptable per
     # protocol v1.2.0+.)
     $ grep -n "Emergency flattening\|emergency_flatten\|retry_cap_exhausted" argus/execution/order_manager.py
     # Expected: ≥1 hit identifying the emergency-flatten branch within the
     # function body. (Specific token may vary; the structural anchor is the
     # function name + the surrounding control flow.)
     ```

   - Anchor (SECONDARY, conditional on Pre-Flight #7): function
     `_escalation_update_stop`. Edit shape: replacement of the dispatch within
     `_escalation_update_stop` per the chosen mechanism.
     - Pre-flight grep-verify:
       ```
       $ grep -n "def _escalation_update_stop" argus/execution/order_manager.py
       # Expected: exactly 1 hit.
       ```
     - If applicability NOT confirmed: function body untouched; close-out
       documents the SKIP + reason.

2. **`tests/execution/order_manager/test_def204_round2_path1.py`** (MODIFY —
   created at S2a; extended at this session):
   - Anchor: file exists from S2a; this session APPENDS 7 new test functions.
   - Edit shape: insertion (additional test functions; ~80 LOC).
   - Pre-flight grep-verify:
     ```
     $ test -f tests/execution/order_manager/test_def204_round2_path1.py && \
       grep -c "^def test_" tests/execution/order_manager/test_def204_round2_path1.py
     # Expected: ≥6 (S2a's 6 logical tests are present; +1 conditional under
     # H1/H4 → ≥7 in that case).
     ```

## Constraints

- Do NOT modify:
  - `argus/execution/order_manager.py::_handle_oca_already_filled` (DEC-386 S1b
    SAFE-marker path) — preserve byte-for-byte.
  - `argus/execution/order_manager.py::_trail_flatten` (S2a's surface — this
    session preserves the helper but does not change its body).
  - `argus/execution/order_manager.py::reconstruct_from_broker` (Sprint 31.94 D1's
    surface; the single-line `is_reconstructed = True` addition belongs to S4a-i).
  - `argus/execution/order_manager.py::reconcile_positions` (DEC-385 L3 + L5).
  - `argus/execution/order_manager.py::_check_flatten_pending_timeouts` 3-branch
    side-check (DEF-158 fix anchor `a11c001`) — Path #2 detection at S3b adds
    upstream at `place_order` exception, NOT a 4th branch.
  - `argus/execution/order_manager.py::_check_sell_ceiling`,
    `_reserve_pending_or_fail` — these are S4a-i's surfaces.
  - `argus/execution/order_manager.py::_locate_suppressed_until` dict +
    `_is_locate_suppressed` helper — these are S3a's surfaces.
  - `argus/execution/ibkr_broker.py::place_bracket_order`,
    `_is_oca_already_filled_error`, `_OCA_ALREADY_FILLED_FINGERPRINT`.
  - `argus/main.py` — entire file (Sprint 31.94 D1+D2 surfaces).
  - `argus/models/trading.py::Position` class.
  - `argus/execution/alpaca_broker.py` (Sprint 31.95 retirement scope).
  - `argus/data/alpaca_data_service.py`.
  - `argus/core/health.py` — `HealthMonitor` consumer + `POLICY_TABLE`
    (S4a-i adds the 14th entry; this session adds none).
  - The `workflow/` submodule (Universal RULE-018).
  - Frontend (`argus/ui/`, `frontend/`) — Vitest must remain at 913.

- Do NOT change:
  - DEC-117 atomic-bracket invariant (regression invariant 1; A-class halt A10).
  - DEC-364 `cancel_all_orders()` no-args ABC contract (regression invariant 2).
  - DEC-372 stop retry caps + exponential backoff (regression invariant 4).
    Test 6 (`test_path1_dec372_backoff_unchanged`) regresses this explicitly.
  - DEC-385 6-layer side-aware reconciliation (regression invariant 5).
  - DEC-386 4-layer OCA architecture (regression invariant 6).
  - The mechanism choice from S2a. If a hidden constraint is discovered in
    `_resubmit_stop_with_retry` or `_escalation_update_stop` that makes the
    mechanism inappropriate for this surface, halt — A-class halt A10 fires
    if the resolution requires a DEC-117 amendment.

- Do NOT add:
  - A new mechanism branch (no fourth option beyond H2/H4/H1).
  - The `halt_entry_until_operator_ack` field to production code (S4a-i's
    surface). This session's tests USE the field shape; production code
    addition is at S4a-i.
  - A new alert type. The `phantom_short_retry_blocked` alert is reused per
    DEC-385 L4 (regression invariant 14 / 24).
  - A new helper module under `argus/execution/`.
  - A new config field (S3a adds the 4 OrderManagerConfig fields; this session
    adds none).

- Do NOT cross-reference other session prompts. This prompt is standalone.

## Operator Choice (N/A this session)

Session 2b inherits the mechanism choice from S2a's "Mechanism Selected" section.
No additional operator pre-check is required beyond the PENDING OPERATOR
CONFIRMATION preamble (which already gates on S1a's `selected_mechanism` field).

The `_escalation_update_stop` applicability decision (Pre-Flight #7) is data-driven
from S1a's JSON, not an operator-judgment call. If the JSON does not encode
applicability explicitly (i.e., the schema lacks a corresponding field), default
to the conservative posture — SKIP test 3 with documented reason; do NOT modify
`_escalation_update_stop`.

## Canary Tests (if applicable)

Before making any changes, run the canary-test skill in
`.claude/skills/canary-test.md` with these tests to confirm baseline behavior:

- `test_stop_resubmission_cap` (or whatever the exact pre-existing DEC-372
  retry-cap regression test is named — verify during pre-flight) — confirms
  DEC-372 cap + backoff pre-Session-2b.
- `test_dec386_oca_invariants_preserved_byte_for_byte` — confirms DEC-386 OCA
  invariants pre-Session-2b (regression invariant 6).
- `test_amd2_sell_before_cancel` (or its post-S2a renamed equivalent) —
  confirms AMD-2 framing established at S2a holds entering this session.

These set the "before" baseline for the after-implementation regression check.

## Test Targets

After implementation:

- Existing tests: all must still pass (regression invariant 10; baseline ≥5,269
  pytest plus S2a's +6 to +7 delta).
- New tests (7) appended to
  `tests/execution/order_manager/test_def204_round2_path1.py` per Requirement 7
  above. Counts: 6 unconditional (one is SKIPPED under non-applicability for
  `_escalation_update_stop`) + 1 conditional under H1/H4. Effective: 7 if H1/H4;
  6 if H2.
- Minimum new test count: **7** (regression checklist line 154 — S2b: +7).
- Test command (scoped per DEC-328):

  ```
  python -m pytest tests/execution/order_manager/ -n auto -q
  ```

## Config Validation (N/A this session)

Session 2b does not add or modify any YAML config fields.

## Marker Validation (N/A this session)

Session 2b does not add pytest markers.

## Risky Batch Edit — Staged Flow (N/A this session)

Session 2b modifies one function (PRIMARY: `_resubmit_stop_with_retry`) and,
conditionally, a second function (`_escalation_update_stop`). The edit footprint
is small and the dispatch logic is reused from S2a's helper (if H4 hybrid). A
risky-batch-edit staged flow is not required.

## Visual Review (N/A this session)

No UI changes. Backend-only session.

## Definition of Done

- [ ] S1a + S2a verification (Pre-Flight #6) confirms artifact present and
      mechanism agrees.
- [ ] `_escalation_update_stop` applicability decision (Pre-Flight #7)
      documented in close-out.
- [ ] `_resubmit_stop_with_retry` emergency-flatten branch dispatches via
      S2a's mechanism.
- [ ] Conditionally, `_escalation_update_stop` dispatches via S2a's mechanism
      (if applicability confirmed; else function body untouched + test 3
      SKIPPED).
- [ ] DEC-372 retry-cap + backoff preserved byte-for-byte (canary +
      `test_path1_dec372_backoff_unchanged`).
- [ ] AMD-8 + `_handle_oca_already_filled` preserved on the
      `_resubmit_stop_with_retry` surface (test 4 + test 5 green).
- [ ] If H1 or H4: AC1.6 operator-audit logging fires on emergency-flatten
      cancel-and-await dispatch (extends S2a's invariant 22 coverage to this
      surface).
- [ ] `halt_entry_until_operator_ack=True` posture test (test 7) green under
      H1-fallback-locate-reject (or SKIPPED with documented reason under H2).
- [ ] All 7 new tests written; conditional skips documented in close-out.
- [ ] All existing pytest baseline still passing.
- [ ] Vitest count = 913 (regression invariant 12).
- [ ] DEC-117 atomic-bracket invariants preserved (regression invariant 1;
      A-class halt A10).
- [ ] DEC-386 4-layer OCA architecture preserved (regression invariant 6).
- [ ] No do-not-modify list file appears in `git diff HEAD~1`.
- [ ] CI green on session's final commit (RULE-050).
- [ ] Close-out report written to file.
- [ ] Tier 2 review completed via @reviewer subagent.

## Regression Checklist (Session-Specific)

After implementation, verify each of these:

| Check | How to Verify |
|-------|---------------|
| `_resubmit_stop_with_retry` emergency branch uses S2a's mechanism | grep + manual trace of the function body; mechanism matches S2a close-out's "Mechanism Selected" section |
| `_escalation_update_stop` applicability decision documented | Close-out's "Applicability Decision" section explicitly cites S1a JSON field + chosen disposition |
| DEC-372 retry-cap (3) + backoff (1s, 2s, 4s) preserved | Test 6 + canary `test_stop_resubmission_cap` green |
| AMD-8 guard preserved on emergency-flatten surface | Test 5 green |
| `_handle_oca_already_filled` short-circuit preserved on emergency-flatten surface | Test 4 green |
| AMD-2 framing matches AC1.5 across S2a + S2b | Per-mechanism: H2 preserved no-SELL; H4 mixed; H1 superseded — close-out documents extended framing |
| AC1.6 operator-audit log fires on emergency-flatten cancel-and-await dispatch | Test 7 green (if H1/H4); required keys present |
| H-R2-2 HALT-ENTRY posture under H1-fallback-locate-reject | Test 7 green (if H1/H4); `halt_entry_until_operator_ack=True` set; `phantom_short_retry_blocked` alert published |
| `git diff HEAD~1 -- argus/execution/order_manager.py::_handle_oca_already_filled` empty | DEC-386 S1b preserved |
| `git diff HEAD~1 -- argus/execution/order_manager.py::_trail_flatten` empty | S2a's surface unchanged at this session |
| `git diff HEAD~1 -- argus/execution/order_manager.py::reconstruct_from_broker` empty | Sprint 31.94 D1 surface untouched |
| `git diff HEAD~1 -- argus/execution/order_manager.py::_check_flatten_pending_timeouts` lines ~3424–3489 empty | DEF-158 3-branch side-check verbatim (regression invariant 8) |
| `git diff HEAD~1 -- argus/main.py` empty | Sprint 31.94 D1+D2 surfaces untouched |
| `git diff HEAD~1 -- frontend/` and `argus/ui/` empty | Frontend immutability (regression invariant 12) |
| Vitest count unchanged at 913 | `cd argus/ui && npx vitest run --reporter=basic` |
| Pre-existing flake count unchanged | CI run: DEF-150, DEF-167, DEF-171, DEF-190, DEF-192 (regression invariant 11) |

## Close-Out

After all work is complete, follow the close-out skill in
`.claude/skills/close-out.md`.

The close-out report MUST include:

1. **A "Mechanism Applied" section** explicitly citing S2a's chosen mechanism
   (cross-referenced) and confirming it was applied identically to
   `_resubmit_stop_with_retry` emergency-flatten branch.
2. **An "Applicability Decision" section** documenting the Pre-Flight #7
   outcome — whether `_escalation_update_stop` was modified and why (citing
   S1a JSON field).
3. **A structured JSON appendix** at the end, fenced with
   ` ```json:structured-closeout `.

**Write the close-out report to a file** (DEC-330):

```
docs/sprints/sprint-31.92-def-204-round-2/session-2b-closeout.md
```

Do NOT just print the report in the terminal. Create the file, write the full
report (including the structured JSON appendix) to it, and commit it.

## Tier 2 Review (Mandatory — @reviewer Subagent)

After the close-out is written to file and committed, invoke the @reviewer
subagent to perform the Tier 2 review within this same session.

Provide the @reviewer with:

1. The review context file:
   `docs/sprints/sprint-31.92-def-204-round-2/review-context.md`
2. The close-out report path:
   `docs/sprints/sprint-31.92-def-204-round-2/session-2b-closeout.md`
3. The diff range: `git diff HEAD~1`
4. The test command (scoped per DEC-328; non-final session):
   `python -m pytest tests/execution/order_manager/ -n auto -q`
5. Files that should NOT have been modified:
   - `argus/execution/order_manager.py::_handle_oca_already_filled`
   - `argus/execution/order_manager.py::_trail_flatten` (S2a's surface)
   - `argus/execution/order_manager.py::reconstruct_from_broker`
   - `argus/execution/order_manager.py::reconcile_positions`
   - `argus/execution/order_manager.py::_check_flatten_pending_timeouts`
     (lines ~3424–3489 — DEF-158 3-branch side-check)
   - `argus/execution/order_manager.py::_check_sell_ceiling`,
     `_reserve_pending_or_fail` (S4a-i)
   - `argus/execution/order_manager.py::_locate_suppressed_until`,
     `_is_locate_suppressed` (S3a)
   - `argus/execution/ibkr_broker.py::place_bracket_order`,
     `_is_oca_already_filled_error`
   - `argus/main.py`
   - `argus/models/trading.py`
   - `argus/execution/alpaca_broker.py`
   - `argus/data/alpaca_data_service.py`
   - `argus/core/health.py`
   - `argus/ui/`, `frontend/`
   - `workflow/` submodule

The @reviewer must use the **backend safety reviewer** template
(`templates/review-prompt.md` from the workflow metarepo).

The @reviewer will produce its review report (including a structured JSON
verdict fenced with ` ```json:structured-verdict `) and write it to:

```
docs/sprints/sprint-31.92-def-204-round-2/session-2b-review.md
```

## Post-Review Fix Documentation

If the @reviewer reports CONCERNS and you fix the findings within this same
session, update the artifact trail per the implementation-prompt template
§"Post-Review Fix Documentation". Append "Post-Review Fixes" to the close-out
file and "Post-Review Resolution" to the review file. Update the verdict JSON
to `CONCERNS_RESOLVED`.

If the reviewer reports CLEAR or ESCALATE, skip this section entirely.
ESCALATE findings must NOT be fixed without human review.

## Session-Specific Review Focus (for @reviewer)

1. **S2a mechanism reuse, not re-implementation.** Verify
   `_resubmit_stop_with_retry` emergency-flatten branch reuses S2a's mechanism
   helper (if S2a introduced `_amend_or_fallback()` for H4) rather than
   re-implementing the dispatch logic. Cross-session helper reuse keeps the
   sprint's diff bound under control AND ensures any future fix to the helper
   propagates to both call sites.

2. **DEC-372 retry-cap + backoff preservation.** Verify test 6 green AND the
   canary `test_stop_resubmission_cap` green. The mechanism dispatch fires ONLY
   at cap exhaustion; normal retries 1+2+3 do NOT trigger the new mechanism.
   Inspect the diff line-by-line for any unintended change to retry-loop timing.

3. **`_escalation_update_stop` applicability decision well-grounded.** Verify
   the close-out's "Applicability Decision" section cites S1a JSON's actual
   field value (not a guess); test 3 is either green-and-applied OR
   skipped-with-reason; the function body change is consistent with the
   decision.

4. **AC1.6 operator-audit logging extends consistently.** If H1/H4 selected,
   verify test 7 fires the SAME structured log line (same keys, same format)
   that S2a established. The mechanism field discriminates between
   `"h1_cancel_and_await"` (last-resort) and `"h4_fallback"` (hybrid fallback).

5. **H-R2-2 HALT-ENTRY posture test against future S4a-i field.** Verify
   the close-out documents the field-shape approach (test fixture creates the
   field at test time vs. assumed-from-S4a-i). If S4a-i has not yet landed,
   the test should still be present; either via fixture-time field construction
   or via skip-with-reason. The cross-session field-shape agreement is
   load-bearing.

6. **DEC-117 + DEC-386 byte-for-byte preservation.** Per A-class halt A10, if
   the chosen mechanism on the emergency-flatten surface breaks DEC-117
   atomic-bracket invariants, halt. Inspect the diff line-by-line.

7. **Anti-tautology check on tests 1 + 7.** Verify test 1
   (`test_path1_resubmit_stop_emergency_flatten_no_overflatten`) ACTUALLY
   exercises the emergency-flatten dispatch path (not just the normal-retry
   path). Verify test 7
   (`test_path1_h1_fallback_locate_reject_halts_entry`) ACTUALLY drives the
   locate-rejection through the SELL emission path AND asserts the
   `halt_entry_until_operator_ack` field becomes True (not just that no SELL
   fires for unrelated reasons).

## Sprint-Level Regression Checklist (for @reviewer)

The full Sprint-Level Regression Checklist is in
`docs/sprints/sprint-31.92-def-204-round-2/regression-checklist.md`.

Of particular relevance to Session 2b (✓-mandatory invariants per the
per-session verification matrix at line 619):

- **Invariant 1 (DEC-117 atomic bracket):** ✓ — Path #1 mechanism on
  emergency-flatten surface MUST NOT break parent-fails-children-cancel
  pattern. A-class halt A10 fires on violation.
- **Invariant 2 (DEC-364 `cancel_all_orders()` no-args):** ✓ — H1/H4 fallback
  uses extended signature; backward-compatible.
- **Invariant 4 (DEC-372 stop retry caps + backoff):** ✓ — Test 6 +
  canary regression. Critical for THIS session per checklist line 64.
- **Invariant 5 (DEC-385 6-layer side-aware reconciliation):** ✓.
- **Invariant 6 (DEC-386 4-layer OCA architecture):** ✓.
- **Invariant 9 (`# OCA-EXEMPT:` mechanism):** ✓ — any new SELL emit either uses
  OCA threading OR carries the comment.
- **Invariant 10 (test count ≥ baseline):** ✓ — pytest delta is +7 per regression
  checklist line 155.
- **Invariant 11 (pre-existing flake count):** ✓.
- **Invariant 12 (frontend immutability; Vitest = 913):** ✓.
- **Invariant 17 (AMD-2 mechanism-conditional):** ✓ — preserves modification
  across the emergency-flatten surface.
- **Invariant 22 (operator-audit logging — conditional):** ✓¹ — MANDATORY only
  if S1a selected H1 or H4; SOFT (▢¹) under H2.

## Sprint-Level Escalation Criteria (for @reviewer)

The full Sprint-Level Escalation Criteria is in
`docs/sprints/sprint-31.92-def-204-round-2/escalation-criteria.md`.

Of particular relevance to Session 2b:

- **A4** — any session's diff modifies a DEC-385/386/388 surface listed in SbC
  "Do NOT modify" beyond explicit byte-for-byte preservation OR explicit
  additive points. Halt; revert; escalate.
- **A5** — DEF-158 retry 3-branch side-check structure modified. Halt.
- **A10** — Path #1 mechanism breaks DEC-117 atomic-bracket invariants on the
  emergency-flatten surface. Halt; operator decides.
- **B1** — pre-existing flake count increases. Halt; file DEF.
- **B3** — pytest baseline ends below 5,269. Halt.
- **B4** — CI fails on session's final commit and is NOT a documented
  pre-existing flake. Halt per RULE-050.
- **B5** — structural anchor mismatch during pre-flight grep-verify. Halt
  mid-pre-flight; re-anchor.
- **B6** — do-not-modify list file in session's `git diff`. Halt; revert.
- **A6** — Tier 2 verdict CONCERNS or ESCALATE. Operator + Tier 2 disposition.
- **C1** — implementer notices a bug or improvement opportunity outside scope.
  Document under "Deferred Items" (RULE-007). Do NOT fix.
- **C5** — implementer is uncertain whether a change crosses the do-not-modify
  boundary (e.g., the conditional `_escalation_update_stop` modification
  approaches the boundary). Pause; consult SbC; if still uncertain, escalate.

### Verification Grep Precision

When kickoffs include verification grep commands, prefer the more precise patterns:

- **Section counting:** use `^## [1-9]\.` rather than `^## [0-9]`.
- **Human-authored content with TitleCase:** use `grep -i`.
- **Token-presence checks across rejection-framed content:** scan only validation
  logic, not docstrings/rationale blocks.

---

*End Sprint 31.92 Session 2b implementation prompt.*

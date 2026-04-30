# Sprint 31.92, Session 2a: Path #1 Fix in `_trail_flatten` (mechanism per S1a) + M-R3-3 precondition check for existing per-position serialization

> **⚠️ PENDING OPERATOR CONFIRMATION**
>
> This prompt is finalized only when:
> 1. S1a JSON artifact at `scripts/spike-results/spike-def204-round2-path1-results.json` is committed to `main` AND
> 2. Operator confirms `selected_mechanism` ∈ {`h2_amend`, `h4_hybrid`, `h1_cancel_and_await`} in writing per Decision 7 (and the H-R2-2-tightened gate language in `sprint-spec.md` § Hypothesis Prescription).
>
> The Pre-Flight Checks below assume the spike artifact is present. If absent, halt and surface to operator.

## Pre-Flight Checks

Before making any changes:

1. **Read `.claude/rules/universal.md` in full and treat its contents as binding for this session.** RULE-038 (grep-verify discipline), RULE-039 (risky batch edit staging), RULE-050 (CI green), and RULE-053 (architectural-seal verification) apply. The full set of universal RULE entries (currently RULE-001 through RULE-053) applies regardless of whether any specific rule is referenced inline in this prompt.

2. Read these files to load context:
   - `argus/execution/order_manager.py::_trail_flatten` (the editing target) +
     `_handle_oca_already_filled` (DEC-386 S1b SAFE-marker preservation; do-not-modify) +
     existing `_amended_prices` dict (anchor by attribute name; AMD-8 / AMD-4 guard surface)
   - `argus/execution/ibkr_broker.py::modify_order` (H2 path consumer) +
     `cancel_all_orders` (H1 fallback / H4 cancel-fallback path; DEC-386 S1c reference;
     anchor by class + method names)
   - `docs/sprints/sprint-31.92-def-204-round-2/sprint-spec.md` §"Acceptance Criteria"
     Deliverable 1 (AC1.1, AC1.2 mechanism-conditional, AC1.4 AMD-8+AMD-4 guard preservation,
     AC1.5 mechanism-conditional AMD-2 framing, AC1.6 operator-audit logging) +
     §"Hypothesis Prescription" (H2/H4/H1 hierarchy + H-R2-2-tightened gate language)
   - `scripts/spike-results/spike-def204-round2-path1-results.json` (S1a output —
     `selected_mechanism` field is the binary gate; `worst_axis_wilson_ub` and
     `h1_propagation_zero_conflict_in_100` are the validation evidence)

3. Run the test baseline (DEC-328 — Session 3+ of sprint, scoped):

   ```
   python -m pytest tests/execution/order_manager/ -n auto -q
   ```

   Expected: all passing (full suite was confirmed by S1b's close-out).
   Note: In autonomous mode, the expected test count is dynamically adjusted by the
   runner based on the previous session's actual results.

4. Verify you are on the correct branch: **`main`**.

5. **Run the structural-anchor grep-verify commands** from the "Files to Modify"
   section below. For each entry, run the verbatim grep-verify command and confirm
   the anchor still resolves to the expected location. If drift is detected,
   disclose under RULE-038 in the close-out and proceed against the actual
   structural anchors. If the anchor is not found at all, HALT and request
   operator disposition rather than guess.

6. **Verify S1a artifact present and PROCEED:**

   ```bash
   test -f scripts/spike-results/spike-def204-round2-path1-results.json && \
     python -c "import json,sys; r=json.load(open('scripts/spike-results/spike-def204-round2-path1-results.json')); \
       sys.exit(0 if r.get('status')=='PROCEED' and r.get('selected_mechanism') in {'h2_amend','h4_hybrid','h1_cancel_and_await'} else 1)" \
     && echo "S1a artifact OK" \
     || { echo "S1a artifact missing or status != PROCEED — HALT"; exit 1; }
   ```

   Read the JSON's `selected_mechanism` field. The remainder of this prompt branches
   on that field. If `selected_mechanism` is `h1_cancel_and_await` AND
   `h1_propagation_zero_conflict_in_100 == false`, halt — the H-R2-2-tightened HARD
   GATE (Decision 2) excludes H1 in that case (escalation A9 fires). This is not
   expected to occur in practice; the spike's PROCEED status implies the gate
   passed. Defensive check only.

7. **M-R3-3 precondition check (per Round 3 disposition § 4.3):**

   Per Round 3 M-R3-3 partial-accept disposition, the implementation prompt is
   extended with a precondition check at session start: grep for existing
   per-position serialization on `_trail_flatten` (e.g., per-position `asyncio.Lock`
   or single-flight pattern at the call site).

   ```bash
   # Search for per-position lock or single-flight on _trail_flatten:
   grep -n -E "asyncio\.Lock|_flatten_lock|_position_lock|_trail_lock" argus/execution/order_manager.py | head -20
   # Search for the call site of _trail_flatten (typically in a periodic update loop):
   grep -n "_trail_flatten" argus/execution/order_manager.py
   ```

   Expected outcome:
   - If existing per-position serialization (per-position `asyncio.Lock` or a
     single-flight pattern at the call site keyed by `position.id`) is found:
     **document the finding in the close-out and proceed.** The serialization is a
     load-bearing assumption for H2's correctness on the same `ManagedPosition.id`
     and its presence justifies H2's adoption.
   - If no existing per-position serialization is found:
     **HALT the session and surface to operator before implementing H2** —
     same-position concurrent `modify_order` is not currently tested by S1a's
     adversarial axes; the absence of serialization is a load-bearing assumption
     for H2 that the spike did not validate. Operator decides whether to (a) add
     a minimal per-position lock at the `_trail_flatten` call site (≤10 LOC) as
     part of this session, OR (b) halt and rerun S1a with the same-position
     concurrent axis added.

   LOC impact: ≤10 LOC if mitigation needed; documentation otherwise.

## Objective

Implement the S1a-spike-selected mechanism (H2 amend-stop-price PREFERRED / H4
hybrid / H1 last-resort) in `_trail_flatten`. Add 6 baseline pytest covering the
canonical BITU 13:41 race trace, OCA-already-filled preservation, AMD-8 + AMD-4
guard preservation, and mechanism-conditional AMD-2 framing — plus a 7th test
under H1 or H4 covering AC1.6 operator-audit logging on every cancel-and-await
dispatch. M-R3-3 precondition check executed at session start (Pre-Flight #7).

## Requirements

1. **Branch all subsequent work on S1a's `selected_mechanism` field** read in
   Pre-Flight #6. The three branches are:

   - **H2 (`selected_mechanism == "h2_amend"`, PRIMARY DEFAULT):** amend the
     bracket stop's `auxPrice` via `IBKRBroker.modify_order(stop_order_id,
     new_aux_price=trail_stop_price)` BEFORE any `place_order(SELL)` invocation.
     The trail-flatten emission becomes a no-op standalone-SELL — the bracket stop
     itself takes care of exit when price hits the new aux. AMD-2 invariant
     PRESERVED (the stop comes before the cancel because the stop never goes
     away — it just moves).
   - **H4 (`selected_mechanism == "h4_hybrid"`):** try amend first. On amend
     rejection (modify_order raises), fall back to
     `cancel_all_orders(symbol=position.symbol, await_propagation=True)`
     BEFORE `place_order(SELL)`. AMD-2 PRESERVED on amend-success path;
     SUPERSEDED by AMD-2-prime on cancel-fallback path. AC1.6 operator-audit
     logging fires on cancel-fallback only.
   - **H1 (`selected_mechanism == "h1_cancel_and_await"`, LAST-RESORT):**
     `cancel_all_orders(symbol=position.symbol, await_propagation=True)` BEFORE
     `place_order(SELL)`. AMD-2 SUPERSEDED by AMD-2-prime; unprotected window
     bounded by `cancel_propagation_timeout ≤ 2s` per DEC-386 S1c. AC1.6
     operator-audit logging fires on every dispatch.

   **Do not implement all three branches.** Implement only the mechanism the
   spike selected. The other two branches' tests are SKIPPED with documented
   reason in the close-out.

2. **In `argus/execution/order_manager.py::_trail_flatten`:** apply the chosen
   mechanism's fix shape. Do NOT alter the surrounding `_trail_flatten` control
   flow beyond the mechanism dispatch — specifically:

   - Preserve AMD-8 guard ("complete no-op if `_flatten_pending` already set" —
     per AC1.4 / regression invariant 17 specific edges).
   - Preserve AMD-4 guard ("no-op if `shares_remaining ≤ 0`" — per AC1.4 /
     regression invariant 17 specific edges).
   - Preserve `_handle_oca_already_filled` short-circuit (DEC-386 S1b SAFE-marker
     path) verbatim — the OCA-already-filled exception inside the cancel/amend
     dispatch must continue to short-circuit cleanly.

   For H2 specifically: the stop_order_id is `position.bracket_stop_order_id`
   (or whichever attribute on `ManagedPosition` carries the bracket-stop's
   broker-assigned order ID); read the actual attribute name during pre-flight.
   For H4/H1: pass `await_propagation=True` per DEC-386 S1c contract.

3. **AC1.6 operator-audit logging** (conditional on H1 OR H4 selection — N/A
   under H2 default). On every cancel-and-await dispatch (H1 last-resort OR H4
   cancel-fallback), emit a structured log line:

   ```python
   logger.info(
       "amd2_supersede",
       extra={
           "event": "amd2_supersede",
           "symbol": position.symbol,
           "position_id": str(position.id),
           "mechanism": "h1_cancel_and_await",  # OR "h4_fallback"
           "cancel_propagation_ms": elapsed_ms,
       },
   )
   ```

   Required keys per AC1.6: `event`, `symbol`, `position_id`, `mechanism`,
   `cancel_propagation_ms`. The `mechanism` field discriminates
   `"h1_cancel_and_await"` (last-resort under H1) from `"h4_fallback"` (hybrid
   fallback under H4). Use the canonical structured-log format already in use
   for ARGUS WARNING/INFO emissions; do NOT introduce a new logger pipeline.

4. **Tests — create `tests/execution/order_manager/test_def204_round2_path1.py`**
   (~100 LOC at this session; will grow at S2b). Six logical tests
   unconditionally; the seventh test is conditional on H1 OR H4 selection.

   - `test_path1_canonical_bitu_race_no_overflatten` — synthetic BITU 13:41 trace
     fixture using SimulatedBroker; assert `total_sold ≤ position.shares_total`
     after trail-flatten dispatches under whatever mechanism is selected
     (mechanism-agnostic invariant per AC1.1; regression invariant 13).
   - **IF H2 selected only** — `test_path1_h2_amend_called_before_any_sell_emit`:
     mocks `IBKRBroker.modify_order`; asserts called with the bracket stop's
     order_id and the new aux price BEFORE any `place_order` invocation;
     asserts NO standalone SELL emission on success path (AC1.2 H2). Skip with
     `pytest.skip(reason="H2 not selected")` if S1a chose H4 or H1.
   - **IF H4 selected only** —
     `test_path1_h4_fallback_invokes_cancel_and_await_on_amend_rejection`:
     mocks `modify_order` to raise; asserts fallback to
     `cancel_all_orders(symbol=position.symbol, await_propagation=True)` BEFORE
     `place_order(SELL)` (AC1.2 H4). Skip with reason if S1a chose H2 or H1.
   - **IF H1 selected only** — `test_path1_h1_cancel_and_await_called_before_sell`:
     asserts `cancel_all_orders(symbol=position.symbol, await_propagation=True)`
     is called BEFORE `place_order(SELL)` (AC1.2 H1). Skip with reason if S1a
     chose H2 or H4.
   - `test_path1_oca_already_filled_short_circuit_preserved` — DEC-386 S1b
     SAFE-marker path unchanged across whichever mechanism is selected. Mock
     the inner cancel/amend to raise an OCA-already-filled exception; assert
     `_handle_oca_already_filled` is invoked; assert no standalone SELL is
     emitted; assert the position transitions to fully-closed via the existing
     SAFE-marker path. (Per regression invariant 6.)
   - `test_path1_amd2_invariant_per_mechanism` — mechanism-conditional regression
     per AC1.5 / invariant 17:
     - IF H2: assert AMD-2 invariant preserved (the existing
       `test_amd2_sell_before_cancel` continues to pass — i.e., no SELL emission
       at all because the stop is amended, not replaced).
     - IF H4: parametrized over (success, fallback) branches. Success path:
       AMD-2 preserved (no SELL). Fallback path: AMD-2-prime asserted (cancel
       propagates BEFORE SELL).
     - IF H1: existing test renamed conceptually (in the new file) to
       `test_amd2_modified_cancel_and_await_before_sell`. Assert cancel BEFORE
       SELL ordering.
   - **Conditional 7th test under H1 OR H4 selection** —
     `test_path1_operator_audit_log_emitted_on_amd2_supersede`: asserts the
     structured log line per AC1.6 fires when the mechanism dispatches to H1
     cancel-and-await (last-resort under H1) OR to H4 fallback (cancel-fallback
     under H4). Required keys: `event="amd2_supersede"`, `symbol`, `position_id`,
     `mechanism ∈ {"h1_cancel_and_await", "h4_fallback"}`, `cancel_propagation_ms`.
     Capture log via `caplog` fixture; assert exact key set; assert `mechanism`
     value matches the selected mechanism. Skip with reason if H2 selected.

5. **No production-code changes outside `_trail_flatten`** beyond the M-R3-3
   precondition mitigation (≤10 LOC, only if Pre-Flight #7 detected absence of
   serialization). All other Path #1 surfaces (`_resubmit_stop_with_retry`
   emergency-flatten branch, conditionally `_escalation_update_stop`) are
   handled at S2b.

## Files to Modify

For each file the session edits, specify:

1. **`tests/execution/order_manager/test_def204_round2_path1.py`** (NEW FILE):
   - Anchor: file does not exist yet; create at the specified path under the
     existing `tests/execution/order_manager/` directory.
   - Edit shape: insertion (new file ≤150 LOC).
   - Pre-flight grep-verify:
     ```
     $ ls -la tests/execution/order_manager/test_def204_round2_path1.py 2>&1 | head -1
     # Expected: "No such file or directory" (file does not yet exist).
     ```

2. **`argus/execution/order_manager.py`** (MODIFY):
   - Anchor (PRIMARY): function `_trail_flatten` (method on `OrderManager`).
   - Edit shape: replacement of the body of the cancel/SELL dispatch within
     `_trail_flatten` per the chosen mechanism (H2/H4/H1). Preserve AMD-8 +
     AMD-4 + `_handle_oca_already_filled` short-circuit byte-for-byte.
   - Pre-flight grep-verify:
     ```
     $ grep -n "def _trail_flatten" argus/execution/order_manager.py
     # Expected: exactly 1 hit. (Directional only — verify the function still
     # exists at the structural anchor; line number drift acceptable per
     # protocol v1.2.0+.)
     $ grep -n "_handle_oca_already_filled\|_amended_prices" argus/execution/order_manager.py
     # Expected: ≥2 hits (the helper + at least one consumer site). DEC-386 S1b
     # surfaces must remain present and untouched.
     ```

   - Anchor (SECONDARY, conditional on M-R3-3 mitigation): if Pre-Flight #7
     identified the absence of per-position serialization AND operator approved
     the in-session mitigation, add a minimal per-position `asyncio.Lock` keyed
     by `position.id` at the `_trail_flatten` call site. Anchor by call-site
     pattern (`grep -n "_trail_flatten" argus/execution/order_manager.py`); LOC
     impact ≤10. Document the mitigation in the close-out's "M-R3-3 Precondition
     Check" section.

## Constraints

- Do NOT modify:
  - `argus/execution/order_manager.py::_handle_oca_already_filled` (DEC-386 S1b
    SAFE-marker path) — preserve byte-for-byte.
  - `argus/execution/order_manager.py::reconstruct_from_broker` body
    (Sprint 31.94 D1's surface; the single-line `is_reconstructed = True`
    addition belongs to S4a-i, not this session).
  - `argus/execution/order_manager.py::reconcile_positions` Pass 1 startup
    branch + Pass 2 EOD branch (DEC-385 L3 + L5).
  - `argus/execution/order_manager.py::_check_flatten_pending_timeouts` 3-branch
    side-check (DEF-158 fix anchor `a11c001`) — Path #2 detection at S3b adds
    upstream at `place_order` exception, NOT a 4th branch.
  - `argus/execution/order_manager.py::_resubmit_stop_with_retry` and
    `_escalation_update_stop` — these are S2b's surfaces.
  - `argus/execution/order_manager.py::reconstruct_from_broker`,
    `_check_sell_ceiling`, `_reserve_pending_or_fail` (S3a/S4a-i surfaces).
  - `argus/execution/ibkr_broker.py::place_bracket_order` (DEC-386 S1a OCA
    threading) and `_is_oca_already_filled_error` / `_OCA_ALREADY_FILLED_FINGERPRINT`.
  - `argus/main.py` — entire file (Sprint 31.94 D1+D2 surfaces; see SbC §"Do NOT
    modify" `check_startup_position_invariant` + `_startup_flatten_disabled` +
    `argus/main.py:1081`).
  - `argus/models/trading.py::Position` class.
  - `argus/execution/alpaca_broker.py` (Sprint 31.95 retirement scope).
  - `argus/data/alpaca_data_service.py`.
  - `argus/core/health.py` — `HealthMonitor` consumer + `POLICY_TABLE`.
  - The `workflow/` submodule (Universal RULE-018).
  - Frontend (`argus/ui/`, `frontend/`) — Vitest must remain at 913.

- Do NOT change:
  - DEC-117 atomic-bracket invariant (regression invariant 1; A-class halt A10).
    If the chosen mechanism requires bracket-children cancellation that is not
    already covered by DEC-386 S0's `cancel_all_orders(..., await_propagation=True)`
    contract, halt — that crosses the DEC-117 do-not-modify boundary.
  - DEC-364 `cancel_all_orders()` no-args ABC contract (regression invariant 2).
    H1 / H4 fallback uses positional+keyword DEC-386 S0 signature; the no-args
    behavior is unchanged.
  - DEC-385 6-layer side-aware reconciliation (regression invariant 5). Path #1
    is upstream; reconciliation surfaces remain untouched.
  - DEC-386 4-layer OCA architecture (regression invariant 6). The OCA-already-filled
    short-circuit must continue to fire; the `# OCA-EXEMPT:` exemption mechanism
    (regression invariant 9) must be respected — any new SELL emit logic in
    `_trail_flatten` either uses OCA threading via `position.oca_group_id` OR
    carries an `# OCA-EXEMPT: <reason>` comment.
  - The reconciliation polling cadence.
  - Throttled-logger intervals.

- Do NOT add:
  - A new `RejectionStage` enum value (Sprint 31.94 territory; DEF-177).
  - A new `OrderType` enum value.
  - A new alert type (`sell_ceiling_violation` is S4a-i's; this session adds none).
  - A new helper module under `argus/execution/`.
  - A new config field (the `bracket_oca_type` field already exists; S3a adds the
    4 OrderManagerConfig fields; this session adds none).

- Do NOT cross-reference other session prompts. This prompt is standalone.

## Operator Choice (N/A this session)

Session 2a does not require operator pre-check beyond the PENDING OPERATOR
CONFIRMATION preamble (which gates the entire prompt's finalization on the S1a
spike artifact's `selected_mechanism` field). The mechanism choice is a function
of the spike's empirical findings + the H-R2-2-tightened gate language, not an
operator-judgment call mid-session.

## Canary Tests (if applicable)

Before making any changes, run the canary-test skill in
`.claude/skills/canary-test.md` with these tests to confirm baseline behavior:

- `test_amd2_sell_before_cancel` (or whatever the exact pre-existing AMD-2
  regression test is named — verify during pre-flight) — confirms AMD-2
  invariant pre-Session-2a.
- `test_dec386_oca_invariants_preserved_byte_for_byte` — confirms DEC-386 OCA
  invariants pre-Session-2a (regression invariant 6).

These set the "before" baseline for the after-implementation regression check.

## Test Targets

After implementation:

- Existing tests: all must still pass (regression invariant 10; baseline ≥5,269
  pytest).
- New tests (6 logical, 7 if H1 or H4 selected) in
  `tests/execution/order_manager/test_def204_round2_path1.py` per Requirement 4
  above.
- Minimum new test count: **6** (mechanism-conditional 7th test counted toward
  S2a's pytest delta only when applicable).
- Test command (scoped per DEC-328):

  ```
  python -m pytest tests/execution/order_manager/ -n auto -q
  ```

## Config Validation (N/A this session)

Session 2a does not add or modify any YAML config fields. Config validation is
S3a's responsibility (4 new `OrderManagerConfig` fields).

## Marker Validation (N/A this session)

Session 2a does not add pytest markers.

## Risky Batch Edit — Staged Flow (N/A this session)

Session 2a's edit footprint is small (single function body + new test file); a
risky-batch-edit staged flow is not required. The M-R3-3 mitigation, if triggered,
is ≤10 LOC.

## Visual Review (N/A this session)

No UI changes. Backend-only session.

## Definition of Done

- [ ] M-R3-3 precondition check executed at session start; finding documented in
      close-out (either "existing serialization found at <site>" OR "in-session
      mitigation applied at <site>" OR "halted and operator approved <action>").
- [ ] S1a `selected_mechanism` field read; chosen mechanism implemented per
      Requirement 1.
- [ ] `_trail_flatten` implements the chosen mechanism per Requirement 2.
- [ ] AMD-8 + AMD-4 + `_handle_oca_already_filled` short-circuit preserved
      byte-for-byte (verified by canary `test_dec386_oca_invariants_preserved_byte_for_byte`
      and AMD-8/AMD-4 regression).
- [ ] If H1 or H4: AC1.6 operator-audit logging emits on cancel-and-await
      dispatch with required keys (verified by 7th test).
- [ ] All 6 (or 7) new tests written and passing.
- [ ] All existing pytest baseline still passing (≥5,269).
- [ ] Vitest count = 913 (regression invariant 12).
- [ ] DEC-117 atomic-bracket invariants preserved (canary + regression invariant 1).
- [ ] DEC-386 4-layer OCA architecture preserved (regression invariant 6).
- [ ] No do-not-modify list file appears in `git diff HEAD~1` (regression
      invariant 4 — A-class halt A4 / B-class halt B6).
- [ ] CI green on session's final commit (RULE-050).
- [ ] Close-out report written to file.
- [ ] Tier 2 review completed via @reviewer subagent.

## Regression Checklist (Session-Specific)

After implementation, verify each of these:

| Check | How to Verify |
|-------|---------------|
| `_trail_flatten` mechanism matches S1a's `selected_mechanism` field | grep + manual trace of the function body; chosen branch is the only one implemented |
| AMD-8 guard preserved (`_flatten_pending` no-op) | Pre-existing AMD-8 regression test green |
| AMD-4 guard preserved (`shares_remaining ≤ 0` no-op) | Pre-existing AMD-4 regression test green |
| `_handle_oca_already_filled` short-circuit preserved | Test 5 (`test_path1_oca_already_filled_short_circuit_preserved`) green |
| AMD-2 framing matches AC1.5 for chosen mechanism | Test 6 (`test_path1_amd2_invariant_per_mechanism`) green; close-out documents framing (preserved/mixed/superseded) |
| AC1.6 operator-audit log fires on H1/H4 cancel-and-await dispatch | Test 7 (conditional) green; required keys present |
| `git diff HEAD~1 -- argus/execution/order_manager.py::_handle_oca_already_filled` empty | DEC-386 S1b preserved |
| `git diff HEAD~1 -- argus/execution/order_manager.py::reconstruct_from_broker` empty | Sprint 31.94 D1 surface untouched (S4a-i adds the single-line `is_reconstructed=True`, NOT this session) |
| `git diff HEAD~1 -- argus/execution/order_manager.py::_check_flatten_pending_timeouts` lines ~3424–3489 empty | DEF-158 3-branch side-check verbatim (regression invariant 8) |
| `git diff HEAD~1 -- argus/main.py` empty | Sprint 31.94 D1+D2 surfaces untouched |
| `git diff HEAD~1 -- frontend/` and `argus/ui/` empty | Frontend immutability (regression invariant 12) |
| Vitest count unchanged at 913 | `cd argus/ui && npx vitest run --reporter=basic` |
| Pre-existing flake count unchanged | CI run: DEF-150, DEF-167, DEF-171, DEF-190, DEF-192 (regression invariant 11) |

## Close-Out

After all work is complete, follow the close-out skill in
`.claude/skills/close-out.md`.

The close-out report MUST include:

1. **A "Mechanism Selected" section** explicitly citing the S1a
   `selected_mechanism` field value (`h2_amend` / `h4_hybrid` /
   `h1_cancel_and_await`) and the AMD-2 framing (preserved / mixed / superseded).
   This section is consumed by S2b's pre-flight read 4.
2. **A "M-R3-3 Precondition Check" section** documenting the Pre-Flight #7
   outcome (existing serialization found / in-session mitigation applied /
   halted-and-resumed).
3. **A structured JSON appendix** at the end, fenced with
   ` ```json:structured-closeout `. See the close-out skill for the full schema.

**Write the close-out report to a file** (DEC-330):

```
docs/sprints/sprint-31.92-def-204-round-2/session-2a-closeout.md
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
   `docs/sprints/sprint-31.92-def-204-round-2/session-2a-closeout.md`
3. The diff range: `git diff HEAD~1`
4. The test command (scoped per DEC-328; non-final session):
   `python -m pytest tests/execution/order_manager/ -n auto -q`
5. Files that should NOT have been modified:
   - `argus/execution/order_manager.py::_handle_oca_already_filled`
   - `argus/execution/order_manager.py::reconstruct_from_broker` (entire body)
   - `argus/execution/order_manager.py::reconcile_positions` (Pass 1 + Pass 2)
   - `argus/execution/order_manager.py::_check_flatten_pending_timeouts` (lines ~3424–3489)
   - `argus/execution/order_manager.py::_resubmit_stop_with_retry` (S2b's surface)
   - `argus/execution/order_manager.py::_escalation_update_stop` (S2b's surface)
   - `argus/execution/ibkr_broker.py::place_bracket_order`
   - `argus/execution/ibkr_broker.py::_is_oca_already_filled_error`
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
docs/sprints/sprint-31.92-def-204-round-2/session-2a-review.md
```

## Post-Review Fix Documentation

If the @reviewer reports CONCERNS and you fix the findings within this same
session, you MUST update the artifact trail so it reflects reality:

1. **Append a "Post-Review Fixes" section to the close-out report file** at
   `docs/sprints/sprint-31.92-def-204-round-2/session-2a-closeout.md`:

   ### Post-Review Fixes
   The following findings from the Tier 2 review were addressed in this session:
   | Finding | Fix | Commit |
   |---------|-----|--------|
   | [description from review] | [what you changed] | [short hash] |

   Commit the updated close-out file.

2. **Append a "Post-Review Resolution" annotation to the review report file**
   at `docs/sprints/sprint-31.92-def-204-round-2/session-2a-review.md`. Update
   the structured verdict JSON: change `"verdict": "CONCERNS"` to
   `"verdict": "CONCERNS_RESOLVED"` and add a `"post_review_fixes"` array.
   Commit the updated review file.

If the reviewer reports CLEAR or ESCALATE, skip this section entirely.
ESCALATE findings must NOT be fixed without human review.

## Session-Specific Review Focus (for @reviewer)

1. **S1a `selected_mechanism` consumption.** Verify the implemented mechanism in
   `_trail_flatten` matches the spike's `selected_mechanism` field. If H2 was
   selected, confirm `IBKRBroker.modify_order` is called BEFORE any
   `place_order(SELL)` invocation; the mechanism's correctness is the entire
   sprint's CRITICAL safety property.

2. **AMD-2 mechanism-conditional framing.** Verify AC1.5's framing
   (preserved / mixed / superseded) matches the chosen mechanism in the
   close-out's "Mechanism Selected" section AND in the test 6
   (`test_path1_amd2_invariant_per_mechanism`) docstring.

3. **AC1.6 operator-audit logging conditionality.** If H1 or H4 selected,
   confirm test 7 is present + green AND the structured log line emits
   `mechanism="h1_cancel_and_await"` (under H1) or `mechanism="h4_fallback"`
   (under H4 fallback path). If H2 selected, confirm test 7 is skipped with
   reason and no logging code was added (preserves H2's no-AMD-2-supersede
   property).

4. **AMD-8 + AMD-4 + `_handle_oca_already_filled` byte-for-byte preservation.**
   Inspect the diff line-by-line. The mechanism dispatch should be a clean
   replacement of the cancel/SELL block; surrounding guards untouched.

5. **DEC-117 + DEC-386 byte-for-byte preservation.** Per A-class halt A10, if
   the chosen mechanism breaks DEC-117 atomic-bracket invariants, halt. The
   reviewer's most critical structural check.

6. **M-R3-3 precondition check disposition.** Verify the close-out documents
   either an existing serialization site OR a documented in-session mitigation
   OR a halted-and-resumed-with-operator-approval outcome. If the operator
   approved an in-session lock addition, verify the lock is keyed by
   `position.id` and the LOC count is ≤10.

7. **Anti-tautology check on test 1
   (`test_path1_canonical_bitu_race_no_overflatten`).** Verify the test uses an
   IBKR mock or SimulatedBroker fixture that ACTUALLY exercises the
   trail-flatten dispatch path; assert `total_sold ≤ position.shares_total` as
   a measurement of the mechanism's effect, not just as a tautology against
   `total_sold = 0` because no SELL ever fired (which would be a false-pass).

## Sprint-Level Regression Checklist (for @reviewer)

The full Sprint-Level Regression Checklist is in
`docs/sprints/sprint-31.92-def-204-round-2/regression-checklist.md`.

Of particular relevance to Session 2a (✓-mandatory invariants per the per-session
verification matrix at line 619):

- **Invariant 1 (DEC-117 atomic bracket):** ✓ — Path #1 mechanism MUST NOT break
  parent-fails-children-cancel pattern. A-class halt A10 fires on violation.
- **Invariant 2 (DEC-364 `cancel_all_orders()` no-args):** ✓ — H1/H4 fallback
  uses extended signature; backward-compatible.
- **Invariant 5 (DEC-385 6-layer side-aware reconciliation):** ✓ — preserved
  byte-for-byte; Path #1 is upstream.
- **Invariant 6 (DEC-386 4-layer OCA architecture):** ✓ — `_handle_oca_already_filled`
  + `place_bracket_order` + `_is_oca_already_filled_error` byte-for-byte.
- **Invariant 9 (`# OCA-EXEMPT:` mechanism):** ✓ — any new SELL emit either uses
  OCA threading OR carries the comment.
- **Invariant 10 (test count ≥ baseline 5,269):** ✓ — pytest count delta is
  +6 to +7 per regression checklist line 154.
- **Invariant 11 (pre-existing flake count):** ✓.
- **Invariant 12 (frontend immutability; Vitest = 913):** ✓.
- **Invariant 17 (AMD-2 mechanism-conditional):** ✓ ESTABLISHES — Session 2a
  sets the framing for the sprint.
- **Invariant 22 (operator-audit logging — conditional):** ✓¹ — MANDATORY only
  if S1a selected H1 or H4. SOFT (▢¹) under H2.

## Sprint-Level Escalation Criteria (for @reviewer)

The full Sprint-Level Escalation Criteria is in
`docs/sprints/sprint-31.92-def-204-round-2/escalation-criteria.md`.

Of particular relevance to Session 2a:

- **A4** — any session's diff modifies a DEC-385/386/388 surface listed in SbC
  "Do NOT modify" beyond the explicit byte-for-byte preservation OR explicit
  additive points. Halt; revert; escalate.
- **A5** — DEF-158 retry 3-branch side-check structure modified instead of the
  spec-prescribed upstream-at-`place_order` detection. Halt.
- **A9** — Path #1 spike S1a worst-axis Wilson UB ≥20% on rejection rate OR
  observes ≥2 trials where amend semantics non-deterministic. (Should be
  pre-empted by Pre-Flight #6's PROCEED check; defensive.)
- **A10** — Path #1 mechanism breaks DEC-117 atomic-bracket invariants. Halt;
  operator decides whether to refine or amend DEC-117.
- **B5** — structural anchor mismatch during pre-flight grep-verify. Halt
  mid-pre-flight; re-anchor.
- **B6** — do-not-modify list file in session's `git diff`. Halt; revert.
- **A6** — Tier 2 verdict CONCERNS or ESCALATE. Operator + Tier 2 disposition.
- **C1** — implementer notices a bug or improvement opportunity outside the
  current session's scope. Document in close-out under "Deferred Items"
  (RULE-007). Do NOT fix in this session.
- **C5** — implementer is uncertain whether a change crosses the do-not-modify
  boundary. Pause; consult SbC; if still uncertain, escalate to operator.

### Verification Grep Precision

When kickoffs include verification grep commands, prefer the more precise patterns:

- **Section counting:** use `^## [1-9]\.` (anchor + literal dot) rather than
  `^## [0-9]` to avoid double-counting `## 10.`, `## 11.`, etc.
- **Human-authored content with TitleCase:** use `grep -i` for content like
  Markdown bold-list section names. Lowercase patterns will return false
  negatives against TitleCase source.
- **Token-presence checks across rejection-framed content:** when checking
  that a rejected pattern is absent, scan only validation logic, not
  docstrings/rationale blocks.

---

*End Sprint 31.92 Session 2a implementation prompt.*

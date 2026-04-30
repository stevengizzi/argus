# Sprint 31.92, Unit 6: Mechanism A Follow-on Spike — Mode-D-equivalent N=100 against fresh OCA-grouped brackets

> **🆕 NEW UNIT per Tier 3 Review #3 verdict 2026-04-30 (commit `b274dd3`).**
>
> Inserted between current sprint state and S2a impl per `docs/sprints/sprint-31.92-def-204-round-2/tier-3-review-3-verdict.md` §"Sprint 31.92 SbC Amendment Scope" / Session-Resumption Guidance. Resolves DEF-245 (Unit 6 follow-on spike scope). Prerequisite: DEF-243 fixes (errorEvent listener, FileHandler, isConnected guard) MUST commit FIRST as a separate Unit before this prompt is finalized.
>
> **Mechanism context:** H2 (modify_order PRIMARY DEFAULT) and H4 (hybrid amend) were ELIMINATED-EMPIRICALLY by Tier 3 Review #3 (DEF-242 — IBKR broker-side categorical rejection of `modify_order` against any OCA group member under DEC-386 `ocaType=1` threading; Error 10326; 100% async-cancel rate observed in spike v2 attempt 1). Mechanism A (cancel-and-resubmit-fresh-stop, formerly H1, now PRIMARY DEFAULT) is the only viable mechanism in the H-class space. This Unit 6 spike validates Mechanism A's Mode-D-equivalent hard gate before S2a impl.

## Pre-Flight Checks

Before making any changes:

1. **Read `.claude/rules/universal.md` in full and treat its contents as binding for this session.** RULE-038 (grep-verify discipline), RULE-039 (risky batch-edit staging), RULE-050 (CI green), RULE-051 (mechanism-signature-vs-symptom-aggregate), and RULE-053 (architectural-seal verification — DEC-386 OCA seal MUST remain present and unmodified throughout this Unit; rollback to `ocaType=0` is the operator's S4b-mediated escape hatch, NOT a Unit 6 spike-side modification) apply. The full set of universal RULE entries (currently RULE-001 through RULE-053) applies regardless of whether any specific rule is referenced inline in this prompt.

2. Read these files to load context:
   - `scripts/spike_def204_round2_path1.py` — anchor by file path. The S1a v2 spike harness (current as of commit `b4e1a9a` for Unit 5 wrap-up + DEF-243 fixes pending). **Unit 6 inherits its pre-spike position-sweep refusal-to-start gate verbatim** (DEF-237's Cat A.2 fix shape) but DROPS axes (i)/(ii)/(iii)/(iv) measurement modes — those validated H2's `modify_order` rejection rate, which is moot under Mechanism A. The Mode A propagation check is also dropped (Mode A measured `modify_order` propagation timing; Mechanism A doesn't call `modify_order`).
   - `argus/execution/ibkr_broker.py::cancel_all_orders` — anchor by class + method name. Mechanism A uses the existing `await_propagation=True` contract (DEC-386 S1c; cancel-propagation broker-side confirmation before return).
   - `argus/execution/ibkr_broker.py::place_order` AND `place_bracket_order` — anchor by class + method names. The fresh-outside-OCA stop is placed via `place_order` (no `ocaGroup` argument; `ocaType` defaults to 0 — i.e., NOT in any OCA group); brackets are created via `place_bracket_order` for the test setup phase (each trial creates a fresh OCA-grouped bracket via the production code path, then exercises Mechanism A against it).
   - `docs/sprints/sprint-31.92-def-204-round-2/tier-3-review-3-verdict.md` §Question 2 Answer / "Mechanism A in detail" / "Follow-on spike scope". Verbatim source for the binary halt gate language and the JSON output schema.
   - `docs/sprints/sprint-31.92-def-204-round-2/sprint-spec.md` §"Hypothesis Prescription" Mechanism A row + amended halt-or-proceed gate language.
   - `docs/sprints/sprint-31.92-def-204-round-2/falsifiable-assumption-inventory.md` FAI #5 (relocated from S1a to Unit 6; semantic content preserved — N=100 HARD GATE).

3. Run the test baseline (DEC-328 — Unit 6 is a spike; full-suite baseline confirmed at sprint-spec):

   ```
   python -m pytest --ignore=tests/test_main.py -n auto -q
   ```

   Expected: 5,337 passing pre-Unit-6 (matches the Unit A mid-sync baseline). Unit 6's spike script produces JSON artifacts only; no pytest delta.

4. Verify you are on the correct branch: **`main`**.

5. **Run the structural-anchor grep-verify commands** (per RULE-038):

   ```bash
   # Confirm DEF-243 fixes have landed BEFORE Unit 6 spike script is authored.
   # Without DEF-243's three fixes, Unit 6 is structurally incapable of
   # capturing OCA-categorical-rejection signals correctly.
   grep -n "errorEvent\|FileHandler\|isConnected" scripts/spike_def204_round2_path1.py
   # Expected: ≥3 hits across the three DEF-243 fix surfaces. If 0 hits,
   # HALT — DEF-243 is the blocking prerequisite and must commit first.

   # Confirm DEC-386 ocaType=1 threading is intact (the architectural
   # constraint that drove H2/H4 elimination — must remain unchanged).
   grep -n "ocaType.*=.*1\|ocaGroup.*=" argus/execution/ibkr_broker.py
   # Expected: ≥2 hits showing ocaGroup + ocaType=1 set on bracket children.
   ```

   **HALT** if DEF-243 fixes have not landed (the spike's measurement infrastructure depends on them) OR if DEC-386's `ocaType=1` threading is missing (the architectural premise of Tier 3 #3's verdict — if it were absent, Unit 6's premise would be wrong and the verdict would need revisiting).

6. **Verdict-prescribed primitive grep-verify (per RULE-038 / kickoff scope-binding):**

   ```bash
   # Verify the primitives the verdict prescribes for Mechanism A actually
   # exist with the expected signatures. If grep reveals deviation,
   # surface as Cat 3 substantial gap before generating the script.
   grep -n "def cancel_all_orders" argus/execution/ibkr_broker.py argus/execution/broker.py
   # Expected: 2 hits (ABC + IBKR impl). The `await_propagation: bool = False`
   # parameter is the DEC-386 S1c contract; verify present.
   grep -n "await_propagation" argus/execution/ibkr_broker.py argus/execution/broker.py argus/execution/order_manager.py
   # Expected: ≥3 hits (ABC + IBKR impl + ≥1 consumer site).
   ```

   If any prescribed primitive's signature deviates from the verdict's assumption, HALT and surface to operator before generating the script — this is the same lesson DEF-237 codified (verdict-prescribed primitives must grep-verify or surface for Work Journal disposition).

## Objective

Author a narrow Phase A diagnostic spike script (`scripts/spike_def204_mechanism_a_followon.py`, ~200 LOC) that runs N=100 Mode-D-equivalent cancel-and-resubmit-fresh-stop trials against fresh OCA-grouped brackets on paper IBKR, measuring three latency distributions and one binary safety property. Output a JSON artifact at `scripts/spike-results/spike-def204-mechanism-a-followon-results.json` whose four binary-gate fields determine Mechanism A's selection per the DEC-390 amended (Tier 3 #3) binary gate. Tier 2 reviewer audits the script BEFORE operator execution per Tier 3 Review #2 workflow protocol gap recommendation #1 — this is structurally non-negotiable to protect against the spike-script-side bug class DEF-237 / DEF-243 represent.

## Requirements

1. **Spike script structure.** Mirror `scripts/spike_def204_round2_path1.py`'s harness pattern (entry-point `main_async()`, dataclass-based result accumulation, JSON write at exit), but DROP the axis machinery and the Mode A propagation check. The single measurement loop is the Mode-D-equivalent N=100 cancel-and-resubmit cycle.

2. **Pre-spike position-sweep refusal-to-start gate (DEF-237 Cat A.2 inherited verbatim).** At `main_async()` start, query `await broker.get_positions()`. If any position is non-zero (`signed_qty != 0`), refuse to start with an explicit `SpikePreflightFailedShortPositionsExist` exception (or equivalent named exception). The operator must flatten manually via the side-aware tooling at `scripts/ibkr_close_all_positions.py` (DEF-239 verified side-aware) before re-running. **No bypass flag** (per RULE-039 / non-bypassable validation discipline).

3. **DEF-237 Cat A.2 side-aware `_flatten()` inherited verbatim.** If the spike harness contains any internal flatten helper (e.g., between trials, for cleanup), it MUST use the three-branch side-aware logic from IMPROMPTU-04: `signed_qty > 0 → SELL`; `signed_qty < 0 → SpikeShortPositionDetected raise`; `signed_qty == 0 → no-op`. Do NOT use `if p.shares > 0: SELL` (the `Position.shares = abs(int(ib_pos.position))` reading produces a side-blind bug per DEF-237).

4. **N=100 Mode-D-equivalent loop.** For each of N=100 trials:
   1. **Setup phase.** Place a fresh OCA-grouped bracket via `place_bracket_order(symbol, side="BUY", qty=1, entry_price=..., stop_price=..., target_price=...)` against a low-volatility liquid symbol (recommend SPY or equivalent operator-curated). The bracket children carry `ocaGroup=f"oca_{ulid}"` + `ocaType=1` per DEC-386. Record entry-fill confirmation.
   2. **Cancel phase.** Issue `await broker.cancel_all_orders(symbol=position.symbol, await_propagation=True)`. Measure cancel-propagation latency: `t_cancel_start = time.monotonic()` before the call; `t_cancel_done = time.monotonic()` after the call returns. `cancel_propagation_ms_trial = (t_cancel_done - t_cancel_start) * 1000`.
   3. **Fresh-stop placement phase.** Within ≤10 ms gap (measured), call `await broker.place_order(symbol=..., side="SELL", order_type="STP", qty=remaining_qty, aux_price=stop_price, ocaGroup=None, ocaType=0)` to place an outside-OCA stop. Measure placement latency: `t_place_start = time.monotonic()` before; `t_place_done = time.monotonic()` after. `fresh_stop_placement_ms_trial = (t_place_done - t_place_start) * 1000`.
   4. **Unprotected-window observation.** During steps (b) and (c), watch for any of: `position_state_inconsistency` (broker reports unexpected `signed_qty`), unintended fill at the cancel-grouped stop OR target after cancel-propagation supposedly returned, OCA conflict on the fresh-stop-placement step, locate suppression event. Record any observation under `unprotected_window_observations[]` with full event metadata.
   5. **Cleanup phase.** Cancel the fresh stop; flatten the position via the side-aware `_flatten()` helper from Requirement 3. Verify position is zero before next trial (else surface to operator + halt).

5. **JSON output schema.** Write to `scripts/spike-results/spike-def204-mechanism-a-followon-results.json` with these required keys:

   - `status: str` ∈ `{"PROCEED", "INCONCLUSIVE"}`
   - `selected_mechanism: str | None` ∈ `{"mechanism_a", null}`
   - `mechanism_a_zero_conflict_in_100: bool` (True only if `len(unprotected_window_observations) == 0` across all 100 trials)
   - `cancel_propagation_p50_ms: float`
   - `cancel_propagation_p95_ms: float`
   - `fresh_stop_placement_p50_ms: float` (informational; not gating)
   - `fresh_stop_placement_p95_ms: float` (gating)
   - `unprotected_window_observations: list[dict]` (full event metadata for any observed conflict; expected `[]` on PROCEED)
   - `trial_count: int` (= 100; if the loop exited early due to operator-halt, this records the actual count)
   - `spike_run_date: str` (ISO 8601 UTC)
   - `inconclusive_reason: str | None` (populated only when `status == "INCONCLUSIVE"`; pattern from DEF-243 fixes — narrative explaining what blocked clean PROCEED)

   **DROPPED keys (vs. S1a v2 spike artifact schema):** `axis_i_wilson_ub`, `informational_axes_results`, `worst_axis_wilson_ub`, `h2_modify_order_p50_ms`, `h2_modify_order_p95_ms`, `h2_rejection_rate_pct`, `h2_deterministic_propagation`, `h1_propagation_*`. These were measurement modes for H2/H4/H1 selection that no longer apply.

6. **Hard halt gate logic** (per DEC-390 amended at Tier 3 #3; per sprint-spec.md §"Hypothesis Prescription"):

   ```
   if (mechanism_a_zero_conflict_in_100 == true
       AND cancel_propagation_p50_ms <= 1000
       AND cancel_propagation_p95_ms <= 2000
       AND fresh_stop_placement_p95_ms <= 200):
       status = "PROCEED"
       selected_mechanism = "mechanism_a"
   else:
       status = "INCONCLUSIVE"
       selected_mechanism = None
       inconclusive_reason = <which condition failed>
   ```

   Any failure path produces `status: INCONCLUSIVE` and triggers escalation-criteria.md A20 (Mechanism A Unit 6 hard-gate failure → Tier 3 Review #4).

7. **DEF-243 fixes inherited (prerequisite — must already exist in the spike harness BEFORE Unit 6's script is authored):**
   - **`errorEvent` listener** that tags trials with `oca_rejected: true` if Error 10326 fires (defense-in-depth: even though Mechanism A doesn't call `modify_order`, the listener catches any unexpected OCA-related broker error).
   - **`logging.FileHandler`** writing to `scripts/spike-results/spike-mechanism-a-followon-{timestamp}.log` (full pre-result log preserved against crash; matches DEF-243 (b)).
   - **`isConnected()` precondition gate** at trial-loop entry — if the broker is disconnected mid-spike, abort the current trial and surface to operator (matches DEF-243 (c)).

8. **No production-code modifications.** This is a read-only spike. The only files this Unit creates are the new spike script + its autogenerated JSON output. No edits to `argus/execution/order_manager.py`, `argus/execution/ibkr_broker.py`, or any other production code.

## Files to Modify

For each file the session creates or edits:

1. **`scripts/spike_def204_mechanism_a_followon.py`** (NEW FILE):
   - Anchor: file does not exist yet; create at the specified path under the existing `scripts/` directory.
   - Edit shape: insertion (new file ~200 LOC).
   - Pre-flight grep-verify:
     ```
     $ ls -la scripts/spike_def204_mechanism_a_followon.py 2>&1 | head -1
     # Expected: "No such file or directory" (file does not yet exist).
     ```

2. **`scripts/spike-results/spike-def204-mechanism-a-followon-results.json`** (AUTOGENERATED, post-operator-execution):
   - The script writes this on every run (success or crash-recovery shape).
   - This file is committed to `main` only AFTER operator-execution and Tier 2 review of the result.

## Constraints

- Do NOT modify:
  - Any file under `argus/` (production code is unchanged at this Unit).
  - `scripts/spike_def204_round2_path1.py` (S1a v2 harness — preserved as historical reference; DEF-243 fixes land in a separate Unit B).
  - `scripts/spike_def204_round2_path2.py` (S1b — DEF-240's bug class still pending Cat A application; out of Unit 6 scope).
  - `scripts/ibkr_close_all_positions.py` (DEF-239 audited side-aware; preserved verbatim).
  - The `workflow/` submodule (Universal RULE-018).
  - Frontend (`argus/ui/`, `frontend/`) — Vitest must remain at 913.

- Do NOT change:
  - DEC-386's OCA threading on bracket children (`ocaGroup` + `ocaType=1`). The architectural premise of Tier 3 Review #3 is that DEC-386 is RETAINED unchanged; Mechanism A absorbs the `modify_order` incompatibility cost (per RSK-DEC386-MODIFY-INCOMPATIBILITY).
  - The `IBKRBroker.cancel_all_orders(..., await_propagation=True)` contract from DEC-386 S1c.

- Do NOT add:
  - A new `RejectionStage` enum value.
  - A new alert type.
  - A new helper module under `argus/execution/`.
  - A bypass flag for the pre-spike position-sweep refusal-to-start gate.

## Operator Choice (N/A this session)

Unit 6 does not require operator pre-check beyond the standard pre-flight (Gateway operational, market closed, single `clientId=1`, paper account U24619949 — see Dependencies). The mechanism is fixed (Mechanism A); the binary gate is structurally non-negotiable; operator input is required only at execution time (running the spike) and at close-out (verdict on PROCEED / INCONCLUSIVE).

## Tier 2 Review BEFORE Operator Execution

**Per Tier 3 Review #2 workflow protocol gap recommendation #1, Unit 6's spike script MUST be reviewed by the @reviewer subagent BEFORE operator execution.** The review checks:

1. **Side-aware `_flatten()` is inherited verbatim** from DEF-237 Cat A.2 fix shape. Audit any internal flatten helpers in the new script for the 3-branch logic (BUY → SELL; SELL → raise; zero → no-op).
2. **Pre-spike position-sweep refusal-to-start gate** is non-bypassable; no `--skip-position-sweep` or equivalent flag exists.
3. **DEF-243 fixes are inherited** from the upstream spike harness (errorEvent listener, FileHandler, isConnected guard).
4. **JSON schema matches the required-keys list** in Requirement 5.
5. **Hard halt gate logic** (Requirement 6) is encoded correctly: all four conditions must hold for PROCEED; any single failure produces INCONCLUSIVE.
6. **No production code is modified** (`git diff` shows changes only under `scripts/`).
7. **Sister-spike audit per Tier 3 #2 workflow protocol gap recommendation #3** — the script does not regress against DEF-237's bug class or DEF-243's measurement gap.

The Tier 2 verdict file `docs/sprints/sprint-31.92-def-204-round-2/sprint-31.92-unit-6-mechanism-a-followon-spike-review.md` is committed BEFORE the operator runs the spike. CONCERNS dispositioned in the same Unit before execution; ESCALATE halts.

## Test Targets

Unit 6 produces zero new pytest tests (spike script + JSON output only). The pytest baseline must remain at 5,337 post-Unit-6.

- Test command (DEC-328 — Unit 6 is a spike, full-suite invocation per close-out invariant):
  ```
  python -m pytest --ignore=tests/test_main.py -n auto -q
  ```

## Config Validation (N/A this Unit)

Unit 6 does not add or modify any YAML config fields.

## Marker Validation (N/A this Unit)

Unit 6 does not add pytest markers.

## Risky Batch Edit — Staged Flow (N/A this Unit)

Unit 6's edit footprint is a single new file (~200 LOC); a risky-batch-edit staged flow is not required.

## Visual Review (N/A this Unit)

No UI changes. Backend-only Unit.

## Definition of Done

- [ ] DEF-243 fixes verified present at the upstream spike harness BEFORE Unit 6's script is authored (Pre-Flight #5).
- [ ] DEC-386 `ocaType=1` threading on bracket children verified intact (Pre-Flight #5).
- [ ] Verdict-prescribed primitives grep-verified (Pre-Flight #6).
- [ ] `scripts/spike_def204_mechanism_a_followon.py` written per Requirements 1–7.
- [ ] No production-code changes (`git diff` shows changes only under `scripts/`).
- [ ] Tier 2 review @reviewer subagent invoked BEFORE operator execution (per "Tier 2 Review BEFORE Operator Execution" section).
- [ ] Tier 2 verdict file written to `docs/sprints/sprint-31.92-def-204-round-2/sprint-31.92-unit-6-mechanism-a-followon-spike-review.md` and committed.
- [ ] Operator executes the spike (separate session, post-Tier-2); JSON artifact committed.
- [ ] Close-out report written to file.
- [ ] All existing pytest baseline still passing (≥5,337).
- [ ] Vitest count = 913.
- [ ] CI green on session's final commit (RULE-050).

## Regression Checklist (Unit-Specific)

After implementation (and before operator execution):

| Check | How to Verify |
|-------|---------------|
| Side-aware `_flatten()` inherited verbatim | grep + manual trace of flatten helpers in the new script |
| Pre-spike position-sweep refusal-to-start gate present | grep for `SpikePreflightFailedShortPositionsExist` (or equivalent) at `main_async()` start; verify no bypass flag |
| DEF-243 errorEvent listener + FileHandler + isConnected guard inherited | grep against the new script's import + handler-registration block |
| JSON schema matches required-keys list | Manual schema inspection; example output JSON written for documentation |
| Hard halt gate logic | Read the result-evaluation block; verify all four conditions composed with AND |
| No production code modifications | `git diff -- argus/` returns empty |
| `git diff -- scripts/` shows only the new spike script | Single new file expected |
| Pytest baseline preserved at 5,337 | Full suite green |

## Close-Out

After all work is complete (Tier 2 review verdict CLEAR + script committed; operator execution is a separate session):

The close-out report MUST include:

1. **A "Mechanism A Gate Status" section** explicitly citing the four binary-gate field values from the JSON artifact AND the resulting `status` field. If `INCONCLUSIVE`, cite `inconclusive_reason` verbatim.
2. **A "DEF-243 Fix Inheritance" section** documenting that the three fixes (errorEvent listener, FileHandler, isConnected guard) were verified present at the upstream spike harness pre-Unit-6.
3. **A "Sister-Spike Audit" section** (per Tier 3 #2 workflow protocol gap recommendation #3) documenting that Unit 6's script does NOT regress against DEF-237's side-blind-flatten bug class or DEF-243's measurement-gap class.
4. **A structured JSON appendix** at the end, fenced with ` ```json:structured-closeout `.

Write the close-out report to:

```
docs/sprints/sprint-31.92-def-204-round-2/sprint-31.92-unit-6-mechanism-a-followon-spike-closeout.md
```

## Tier 2 Review (Mandatory — @reviewer Subagent — BEFORE Operator Execution)

After the script is written and committed, invoke the @reviewer subagent to perform the Tier 2 review BEFORE the operator runs the spike.

Provide the @reviewer with:

1. The review context file: `docs/sprints/sprint-31.92-def-204-round-2/review-context.md`
2. The script path: `scripts/spike_def204_mechanism_a_followon.py`
3. The diff range: `git diff HEAD~1`
4. The verdict source: `docs/sprints/sprint-31.92-def-204-round-2/tier-3-review-3-verdict.md` §Question 2 Answer
5. Files that should NOT have been modified:
   - Any file under `argus/`
   - `scripts/spike_def204_round2_path1.py`
   - `scripts/spike_def204_round2_path2.py`
   - `scripts/ibkr_close_all_positions.py`
   - `argus/ui/`, `frontend/`
   - `workflow/` submodule

The @reviewer must use the **backend safety reviewer** template (`templates/review-prompt.md` from the workflow metarepo).

The @reviewer will produce its review report (including a structured JSON verdict fenced with ` ```json:structured-verdict `) and write it to:

```
docs/sprints/sprint-31.92-def-204-round-2/sprint-31.92-unit-6-mechanism-a-followon-spike-review.md
```

## Dependencies

- DEF-243 fixes (errorEvent listener, FileHandler, isConnected guard) MUST commit FIRST as a separate Unit (Unit B).
- Sprint 31.91 SEALED at HEAD.
- Paper IBKR Gateway operational, single `clientId=1`, account U24619949.
- Market CLOSED at operator-execution time (non-safe-during-trading — pre-market or after-hours).
- Operator does NOT perform manual disconnect during execution (Unit 6 has no axis (ii)/(iv) reconnect-window measurement; spurious disconnect would corrupt the run).

## Cross-References

- `docs/sprints/sprint-31.92-def-204-round-2/tier-3-review-3-verdict.md` §Question 2 Answer / "Mechanism A in detail" / "Follow-on spike scope" — verbatim source for the binary halt gate language and JSON output schema.
- `docs/sprints/sprint-31.92-def-204-round-2/sprint-spec.md` §"Hypothesis Prescription" Mechanism A row + amended halt-or-proceed gate language.
- `docs/sprints/sprint-31.92-def-204-round-2/falsifiable-assumption-inventory.md` FAI #5 (relocated from S1a to Unit 6).
- DEF-242 (architectural finding driving H2/H4 elimination).
- DEF-243 (sibling spike-harness measurement-gap fixes; Unit B prerequisite).
- DEF-244 (Sprint 31.94 cross-sprint binding via Mechanism A).
- DEF-245 (this Unit's scope DEF).
- RSK-DEC386-MODIFY-INCOMPATIBILITY (permanent architectural constraint).
- RSK-MECHANISM-A-UNPROTECTED-WINDOW (gate-coupling RSK; revisit at Unit 6 close-out).
- escalation-criteria.md A1 (amended at Tier 3 #3) + A20 (NEW at Tier 3 #3, fires on Mechanism A binary-gate failure).

---

*End Sprint 31.92 Unit 6 (Mechanism A Follow-on Spike) implementation prompt.*

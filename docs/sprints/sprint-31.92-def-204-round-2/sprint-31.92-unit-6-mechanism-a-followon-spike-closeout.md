# Sprint 31.92 Unit C / Unit 6 — Mechanism A Follow-on Spike Script — Close-out

**Date:** 2026-04-30
**Anchor commit:** TBD (to be filled after `git commit`)
**Pre-Unit-C baseline anchor:** `4faa3c0` (Unit B DEF-243 fixes)
**Self-assessment:** **CLEAR**
**Spike NOT executed; --dry-run validation only.** Operator execution is Unit E, gated on Unit D Tier 2 review.

---

## Mechanism A Gate Status

The four binary-gate fields per DEC-390 amended at Tier 3 Review #3 verdict:

| Field | Status |
|---|---|
| `mechanism_a_zero_conflict_in_100` | **N/A — spike not executed** |
| `cancel_propagation_p50_ms` | N/A |
| `cancel_propagation_p95_ms` | N/A |
| `fresh_stop_placement_p95_ms` | N/A |
| `status` | N/A |

The gate's evaluation lives in `_apply_mechanism_a_decision()` at
`scripts/spike_def204_mechanism_a_followon.py:803-867`. All four conditions
are composed with structural AND (separate `if` branches; any single failure
returns `INCONCLUSIVE` with a specific `inconclusive_reason`). Trial count
must equal exactly 100 — partial runs cannot satisfy the gate.

Resolution scope per Tier 3 Review #3 verdict §Question 2 / Mechanism A in
detail / Follow-on spike scope; per DEF-245 close-out criterion
"`mechanism_a_zero_conflict_in_100` + latency distributions". Operator
execution (Unit E) will produce the JSON artifact at
`scripts/spike-results/spike-def204-mechanism-a-followon-results.json`; this
close-out covers only the script-authoring Unit (C).

---

## DEF-243 Fix Inheritance

Verified at Pre-Flight #5 (per impl-prompt) that all three DEF-243 fixes
landed at `4faa3c0` BEFORE Unit C began. All three are inherited verbatim
into `scripts/spike_def204_mechanism_a_followon.py`:

| Fix | Upstream surface | Unit C surface |
|---|---|---|
| **Fix B.1** — `errorEvent` listener (`_OcaRejectionTracker`) | `scripts/spike_def204_round2_path1.py:192-234` | `scripts/spike_def204_mechanism_a_followon.py:198-235` (class), `:1103-1104` (attachment) |
| **Fix B.2** — `logging.FileHandler` | `scripts/spike_def204_round2_path1.py:250-274` | `scripts/spike_def204_mechanism_a_followon.py:251-265` (helper), `:984` (attachment at top of `main_async`) |
| **Fix B.3** — `isConnected()` precondition gate | `scripts/spike_def204_round2_path1.py:1028,1100` (axis-iv entry) | `scripts/spike_def204_mechanism_a_followon.py:649-666` (trial-loop entry; per impl-prompt Requirement 7 — relocated from axis-iv to trial-loop entry since Unit C has no axes) |

**Adaptation notes (not regressions):**

- Fix B.1: the upstream `_OcaRejectionTracker` records error 10326 events to
  catch `modify_order` async-cancellation. Unit C uses the SAME tracker for a
  different purpose: Mechanism A's fresh stop has NO `ocaGroup` set, so error
  10326 should NEVER fire on the fresh-stop reqId — if it does, that is a
  structural Mechanism A failure (the supposedly-outside stop is being bound
  to the cancelled OCA group). The fresh-stop's broker-order-id is checked
  against the tracker in `_classify_mechanism_a_conflict` and any non-zero
  count is recorded under `unprotected_window_observations[]` with
  signature `oca_conflict_on_fresh_stop`.
- Fix B.2: log filename pattern changes from upstream's
  `spike-run-{ts}.log` to `spike-mechanism-a-followon-{ts}.log` so a future
  operator can pattern-match across spike harnesses without confusion.
- Fix B.3: relocated from axis-iv entry to trial-loop entry per impl-prompt
  Requirement 7 (Unit 6 has no axes, so trial-loop entry is the only
  precondition surface that matters). The relocated gate halts the trial
  loop on disconnect rather than skipping a single trial — Unit 6 has no
  per-trial reconnect path because the verdict explicitly says the operator
  does NOT manually disconnect during execution.

---

## Sister-Spike Audit

Per Tier 3 Review #2 workflow protocol gap recommendation #3 (sister-spike
audit). Unit C's script does NOT regress against:

### DEF-237 (side-blind `_flatten` bug class)

`scripts/spike_def204_mechanism_a_followon.py:454-528` (`_flatten` helper)
inherits the three-branch side-aware logic verbatim:

- `p.shares == 0` → no-op (defense-in-depth)
- `p.side == OrderSide.BUY and p.shares > 0` → SELL-flatten (genuine long)
- `p.side == OrderSide.SELL and p.shares > 0` → raise
  `SpikeShortPositionDetected` (long-only spike policy refuses to cover)

`grep -n "if p.shares > 0:" scripts/spike_def204_mechanism_a_followon.py`
returns zero matches in any flatten-related code path. The pre-spike
position-sweep gate at `:1060` does use `[p for p in pre_positions if
p.shares > 0]` but that's a "find any nonzero position" check, not a
flatten direction — it correctly catches both longs AND shorts for refusal.

### DEF-243 (spike-harness measurement gap)

All three Unit B fixes inherited verbatim (see DEF-243 Fix Inheritance
section above). Additionally, Mechanism A's fresh-stop placement check
extends Fix B.1's coverage: the fresh-stop reqId is queried against the
OCA-rejection tracker post-placement, so an unexpected error 10326 on the
fresh stop is recorded as `oca_conflict_on_fresh_stop` rather than silently
ignored. This closes a measurement gap that Mode A's pre-Cat-A.1 design had
(synchronous-return without checking async-cancellation).

### Pre-spike position-sweep refusal-to-start

`scripts/spike_def204_mechanism_a_followon.py:1043-1083`. Inherited from
upstream `scripts/spike_def204_round2_path1.py:1518-1558`. Non-bypassable:
no `--skip-position-sweep`, `--force`, or equivalent flag exists.
`grep -nE "skip-position-sweep|skip_position_sweep|--force|--bypass"
scripts/spike_def204_mechanism_a_followon.py` returns zero hits.

The refusal raises `SpikePreflightFailedShortPositionsExist` (new exception
class for Unit C; semantically distinct from `SpikeShortPositionDetected`
which raises during in-loop cleanup). The exception is caught in `main()`
and converted to exit code 2 so the operator sees a clear pre-flight halt
distinct from a mid-run crash.

---

## Change Manifest

### New files (1)

| Path | LOC | Purpose |
|---|---|---|
| `scripts/spike_def204_mechanism_a_followon.py` | 1,284 | Unit 6 follow-on spike script per Tier 3 Review #3 verdict §Question 2 |

### Modified files (0)

`git diff --stat -- argus/` returns empty. `git diff --stat -- scripts/`
shows only the new file. No production code changes.

### LOC discrepancy disclosure (per Universal RULE-038 sub-rule on kickoff
statistics)

The impl-prompt at `docs/sprints/sprint-31.92-def-204-round-2/
sprint-31.92-unit-6-mechanism-a-followon-spike-impl.md:67` estimated
"~200 LOC". Actual is 1,284 LOC. The impl-prompt also said in §Requirements
1: "Mirror `scripts/spike_def204_round2_path1.py`'s harness pattern" — and
the upstream is 1,802 LOC. Inherited helpers (`_flatten`,
`_open_entry_with_oca_bracket`, `_get_market_price`, `_OcaRejectionTracker`,
`_MarketClosedDetector`, `_setup_file_handler`, smoke test, pre-spike
sweep, side-aware exception classes, market-hours guard) account for
~700 LOC. Verbose docstrings cross-referencing the Tier 3 #3 verdict and
preserving the Option-B-precedent disposition narrative add ~200 LOC. The
remaining ~400 LOC is the new measurement loop + classification + decision
logic. The "~200 LOC" estimate was a directional underestimate; the
inherited-helper requirement is structural and unavoidable.

---

## Judgment Calls

### Verdict's prescribed `place_order` signature vs actual ABC

**Issue:** The Tier 3 Review #3 verdict at line 81 prescribes:
```
broker.place_order(symbol=..., side="SELL", order_type="STP",
                   qty=remaining_qty, aux_price=stop_price,
                   ocaGroup=None, ocaType=0)
```

The actual `Broker.place_order` ABC at `argus/execution/broker.py:57` is
`place_order(self, order: Order) -> OrderResult`. The `Order` Pydantic
model has no `ocaGroup` / `ocaType` fields. Only `place_bracket_order`
threads OCA fields, via `_build_ib_order` at
`argus/execution/ibkr_broker.py`.

**Disposition:** Same Option-B precedent as Sprint 31.92 Unit 3's Cat A.2
`p._raw_ib_pos.position` situation. The verdict's literal signature does not
match the codebase's actual primitive surface, but the verdict's *spirit*
(cancel and place a stop NOT in the original OCA group) is preserved by:

1. `_build_outside_oca_stop()` constructs an `Order` object with no
   ocaGroup-equivalent fields (no such fields exist on the Pydantic model);
2. `IBKRBroker.place_order(order)` calls `_build_ib_order(order)` which
   constructs an ib_async order WITHOUT setting `ocaGroup` / `ocaType`
   (only `place_bracket_order` sets them at `ibkr_broker.py:855-921`);
3. Therefore the resulting IBKR order is structurally outside any OCA
   group — exactly what the verdict prescribes.

**Why not HALT and surface to operator:** The verdict's signature is
clearly conceptual (it lists `aux_price=stop_price` which IS an `Order`
field but spelled differently — actual is `stop_price`). Reading the
signature as a literal Python call would imply a call shape that doesn't
exist. The Option-B precedent codified at Sprint 31.92 Unit 3 (operator
disposition: apply verdict's spirit) is directly applicable here. Surfacing
this would re-litigate a settled Work Journal disposition without changing
the implementation outcome.

**Documentation:** Inline docstring at
`scripts/spike_def204_mechanism_a_followon.py:347-367` records the
disposition + cross-reference. Future readers see both the verdict's
literal language AND the actual Python primitive used.

### Mechanism A trial #100 partial-state on disconnect

**Issue:** If the broker disconnects mid-trial-loop, the trial-loop returns
the partial trial list. `_apply_mechanism_a_decision` then sees
`trial_count != 100` and returns `INCONCLUSIVE` with reason
"trial count {N} != 100; gate requires complete N=100 run". This is
structurally correct per the verdict's binding semantic ("100 clean trials"
not "trial-conflict-rate < N%") but means a clean 99/100 run still
produces `INCONCLUSIVE` rather than `PROCEED`.

**Disposition:** Implementation matches the verdict's binding semantic
exactly. The verdict's HARD GATE language is "any 1 conflict in 100" — by
contrapositive, a partial run cannot satisfy this. If operator-execution
yields 99 clean trials and a broker disconnect, the operator's recourse is
to re-run with the disconnect cause addressed; the gate cannot be evaluated
without the full N=100.

**No documentation change needed:** The behavior is the verdict's
prescribed behavior.

---

## Scope Verification

Constraints from impl-prompt §Constraints:

| Constraint | Compliance |
|---|---|
| No file under `argus/` modified | ✅ `git diff --stat -- argus/` empty |
| `scripts/spike_def204_round2_path1.py` not modified | ✅ Not in diff |
| `scripts/spike_def204_round2_path2.py` not modified | ✅ Not in diff |
| `scripts/ibkr_close_all_positions.py` not modified | ✅ Not in diff |
| `argus/ui/`, `frontend/` not touched | ✅ Vitest unchanged at 913 |
| `workflow/` submodule not touched | ✅ Universal RULE-018 honored |
| DEC-386 OCA threading unchanged | ✅ Pre-Flight #5 verified `ocaType=1` + `ocaGroup` at `argus/execution/ibkr_broker.py:848,888,921` |
| `cancel_all_orders(await_propagation=True)` contract unchanged | ✅ Pre-Flight #6 grep-verified |
| No new `RejectionStage` enum value | ✅ N/A — script doesn't touch enums |
| No new alert type | ✅ N/A |
| No new helper module under `argus/execution/` | ✅ N/A |
| No bypass flag for pre-spike position-sweep gate | ✅ Grep returns zero hits |

---

## Regression Checklist (per impl-prompt)

| Check | Result |
|---|---|
| Side-aware `_flatten()` inherited verbatim | ✅ Three-branch logic at `:498-516` (BUY → SELL; SELL → raise; zero → no-op) |
| Pre-spike position-sweep refusal-to-start gate present | ✅ At `:1043-1083`; `SpikePreflightFailedShortPositionsExist` raised at `:1078` |
| No bypass flag for pre-spike gate | ✅ `grep -nE "skip-position-sweep\|--force\|--bypass"` returns zero hits |
| DEF-243 errorEvent listener inherited | ✅ `_OcaRejectionTracker` at `:198-235`; attached at `:1103-1104` |
| DEF-243 FileHandler inherited | ✅ `_setup_file_handler` at `:251-265`; called at `:984` |
| DEF-243 isConnected guard inherited | ✅ At trial-loop entry `:649-666` |
| JSON schema matches required-keys list | ✅ All 11 required keys present (`status`, `selected_mechanism`, `mechanism_a_zero_conflict_in_100`, `cancel_propagation_p50_ms`, `cancel_propagation_p95_ms`, `fresh_stop_placement_p50_ms`, `fresh_stop_placement_p95_ms`, `unprotected_window_observations`, `trial_count`, `spike_run_date`, `inconclusive_reason`); --dry-run schema validation at `:1001-1015` confirms all 11 keys |
| Hard halt gate logic | ✅ All 4 conditions composed with structural AND at `:833-862`; trial_count != 100 also fails the gate |
| No production code modifications | ✅ `git diff -- argus/` empty |
| `git diff -- scripts/` shows only the new file | ✅ Single new file |
| Pytest baseline preserved | ✅ 5,358 passed (matches user-stated baseline; +0 net delta from Unit C) |

---

## Pytest Baseline Discrepancy Disclosure

Per Universal RULE-038 sub-rule on kickoff-vs-actual statistics:

- **Impl-prompt §Pre-Flight #3:** stated "Expected: 5,337 passing pre-Unit-6
  (matches the Unit A mid-sync baseline)".
- **User's Pre-Flight kickoff:** stated "Confirm pytest baseline 5,358".
- **Measured at Unit C session start:** 5,358 passing.
- **Measured at Unit C session end (post-script-creation):** 5,358 passing.

The impl-prompt's "5,337" figure was stale — it was authored before Unit A
and Unit B added regression tests for Unit A's pattern + Unit B's DEF-243
fixes. The user's "5,358" figure is current and matches measurement.
Unit C produces zero new pytest tests per impl-prompt §Test Targets, so the
baseline is preserved (+0 net delta).

---

## Vitest Baseline

Not run (no frontend changes). Per impl-prompt §Constraints, Vitest must
remain at 913. No `argus/ui/` or `frontend/` touch in this Unit.

---

## Definition of Done

- [x] DEF-243 fixes verified present at upstream spike harness BEFORE Unit C began (Pre-Flight #5)
- [x] DEC-386 `ocaType=1` threading on bracket children verified intact (Pre-Flight #5)
- [x] Verdict-prescribed primitives grep-verified (Pre-Flight #6)
- [x] `scripts/spike_def204_mechanism_a_followon.py` written per Requirements 1–7
- [x] No production-code changes (`git diff -- argus/` empty)
- [ ] Tier 2 review @reviewer subagent (Unit D — separate session per kickoff)
- [ ] Tier 2 verdict file written (Unit D — separate session per kickoff)
- [ ] Operator executes the spike (Unit E — separate session post-Tier-2)
- [x] Close-out report written to file
- [x] All existing pytest baseline still passing (5,358 matches user baseline)
- [x] Vitest count unchanged at 913 (no frontend changes)
- [ ] CI green on session's final commit (RULE-050) — pending push + CI run

---

## Self-Assessment

**CLEAR.**

Justification:
- Script created per impl-prompt verbatim (all 7 Requirements implemented).
- All grep-guards pass.
- --dry-run validation clean (schema OK, all 11 required keys present).
- Pytest baseline preserved at 5,358 (no production code changes).
- No HALT conditions fired during Pre-Flight #5 / #6.
- One Judgment-Call documented (verdict's `place_order` signature vs actual
  ABC) with explicit Option-B-precedent reference; no operator disposition
  needed (precedent settled at Sprint 31.92 Unit 3).
- One LOC discrepancy disclosed (impl-prompt "~200 LOC" vs actual 1,284 LOC;
  attributable to inherited-helper requirement).
- One pytest baseline discrepancy disclosed (impl-prompt 5,337 vs measured
  5,358; impl-prompt was authored pre-Unit-A/B).

No deviations from spec; no skipped scope items; no test regressions.

---

## Deferred Items

None new in Unit C scope. Existing follow-on items continue:

- Unit D (Tier 2 review of script BEFORE operator execution) — separate
  session, per impl-prompt §"Tier 2 Review BEFORE Operator Execution".
- Unit E (operator execution of spike + JSON artifact commit) — separate
  session, gated on Unit D's verdict.
- DEF-244 (Sprint 31.94 reconnect-recovery cross-sprint binding) — already
  open; not affected by this Unit.
- DEF-245 (this Unit's scope DEF) — REMAINS OPEN until Unit E close-out;
  Unit C delivers the script (one of three resolution items: script + Tier 2
  + operator execution).

---

## Cross-References

- `docs/sprints/sprint-31.92-def-204-round-2/sprint-31.92-unit-6-mechanism-a-followon-spike-impl.md` — impl-prompt source.
- `docs/sprints/sprint-31.92-def-204-round-2/tier-3-review-3-verdict.md` §Question 2 / Mechanism A in detail / Follow-on spike scope — verdict source for binary halt gate + JSON schema.
- `docs/sprints/sprint-31.92-def-204-round-2/sprint-spec.md` §"Hypothesis Prescription" Mechanism A row.
- `docs/sprints/sprint-31.92-def-204-round-2/falsifiable-assumption-inventory.md` FAI #5 (relocated from S1a to Unit 6).
- `4faa3c0` — Unit B DEF-243 fixes anchor (prerequisite).
- `4ba14c0` — Unit A mid-sync.
- DEF-242 (architectural finding driving H2/H4 elimination — Tier 3 #3).
- DEF-243 (Unit B prerequisite — landed at `4faa3c0`).
- DEF-244 (Sprint 31.94 cross-sprint binding via Mechanism A).
- DEF-245 (this Unit's scope DEF — partial resolution; full closure at Unit E).
- RSK-DEC386-MODIFY-INCOMPATIBILITY (permanent architectural constraint).
- RSK-MECHANISM-A-UNPROTECTED-WINDOW (gate-coupling RSK; revisit at Unit E close-out).
- escalation-criteria.md A20 (fires on Mechanism A binary-gate failure).

---

```json:structured-closeout
{
  "unit": "Sprint 31.92 Unit C / Unit 6",
  "title": "Mechanism A Follow-on Spike Script",
  "self_assessment": "CLEAR",
  "anchor_pre_unit_c": "4faa3c0",
  "spike_executed": false,
  "dry_run_validation": "clean",
  "production_code_changes": 0,
  "new_files": [
    "scripts/spike_def204_mechanism_a_followon.py"
  ],
  "modified_files": [],
  "pytest_baseline": {
    "before": 5358,
    "after": 5358,
    "delta": 0,
    "kickoff_stated_5358_matches_measured": true,
    "impl_prompt_stated_5337_was_stale": true
  },
  "vitest_baseline": {
    "before": 913,
    "after": 913,
    "delta": 0
  },
  "loc": {
    "new_script_loc": 1284,
    "impl_prompt_estimate": 200,
    "discrepancy_disclosed": true,
    "discrepancy_attribution": "inherited helpers (DEF-237/DEF-243 patterns) + verbose docstrings preserving verdict cross-references; impl-prompt's '~200 LOC' was a directional underestimate"
  },
  "halt_conditions_fired": 0,
  "judgment_calls": [
    {
      "issue": "Verdict's prescribed place_order signature vs actual Broker ABC",
      "disposition": "Option-B-precedent (same as Sprint 31.92 Unit 3 Cat A.2 _raw_ib_pos disposition); apply verdict's spirit via Order objects; bare place_order produces outside-OCA stop natively",
      "documented_at": "scripts/spike_def204_mechanism_a_followon.py:347-367 (inline docstring)"
    },
    {
      "issue": "Trial #100 partial-state on disconnect",
      "disposition": "Implementation matches verdict's binding semantic exactly (gate requires complete N=100 run); 99/100 clean trials still produces INCONCLUSIVE per verdict text",
      "documented_at": "_apply_mechanism_a_decision docstring + closeout Judgment-Calls section"
    }
  ],
  "deferred_items": [
    {
      "id": "Unit D",
      "title": "Tier 2 review of script BEFORE operator execution",
      "blocking": "Unit E"
    },
    {
      "id": "Unit E",
      "title": "Operator execution of spike + JSON artifact commit",
      "blocking": "DEF-245 closure"
    }
  ],
  "regression_checklist_results": {
    "side_aware_flatten_inherited": true,
    "pre_spike_position_sweep_gate_present": true,
    "no_bypass_flag_exists": true,
    "def_243_error_event_listener_inherited": true,
    "def_243_file_handler_inherited": true,
    "def_243_isconnected_guard_inherited": true,
    "json_schema_matches_required_keys_list": true,
    "hard_halt_gate_logic_correct": true,
    "no_production_code_modifications": true,
    "git_diff_scripts_only_new_spike_script": true,
    "pytest_baseline_preserved": true
  },
  "context_state": "GREEN"
}
```

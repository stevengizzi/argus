# Sprint 31.91, Session 1a: Bracket OCA Grouping + Error 201 Defensive Handling

## Pre-Flight Checks

Before making any changes:

1. **Read `.claude/rules/universal.md` in full and treat its contents as binding for this session.** RULE-038 (grep-verify discipline) and RULE-050 (CI green) apply.

2. Read these files to load context:
   - `argus/execution/ibkr_broker.py` — specifically `place_bracket_order` method around lines 731-782 (verify line numbers via grep first; lines may have drifted)
   - `argus/execution/order_manager.py:74` — `ManagedPosition` dataclass
   - `argus/execution/simulated_broker.py` — `place_order` method
   - `argus/core/config.py:639` — `IBKRConfig` Pydantic model
   - `docs/sprints/sprint-31.91-reconciliation-drift/sprint-spec.md` — D2 acceptance criteria
   - `docs/sprints/sprint-31.91-reconciliation-drift/review-context.md` — Performance Considerations (ocaType=1 vs ocaType=2 rationale)
   - `scripts/spike_ibkr_oca_late_add.py` — the live-IBKR mechanism check that confirms `PATH_1_SAFE` (Error 201 / OCA-filled is the success signature)

3. Run the test baseline (DEC-328 — Session 2+ of sprint, scoped):

   ```
   python -m pytest tests/execution/ -n auto -q
   ```

   Expected: all passing (full suite was confirmed by Session 0's close-out).

4. Verify you are on the correct branch: **`main`**.

5. Verify Session 0's deliverables are present on `main`:

   ```bash
   grep -n "CancelPropagationTimeout" argus/execution/broker.py
   grep -n "await_propagation" argus/execution/broker.py
   ```

   Both must match. If not, halt — Session 0 has not landed yet.

## Objective

Set `ocaGroup = f"oca_{parent_ulid}"` and `ocaType=1` ("Cancel with block") on bracket children (stop, T1, T2) submitted via `IBKRBroker.place_bracket_order`. Persist `oca_group_id` on `ManagedPosition`. Add no-op support on `SimulatedBroker`. Add defensive Error 201 / "OCA group is already filled" handling on T1/T2 placement (rare but possible if the stop fills in the bracket-placement micro-window — the Phase A spike confirmed this is the success signature).

## Requirements

1. **Add `oca_group_id` field to `ManagedPosition`** in `argus/execution/order_manager.py` near line 74:

   ```python
   @dataclass
   class ManagedPosition:
       # ... existing fields ...
       oca_group_id: str | None = None  # Set by place_bracket_order; persists for lifetime of position
   ```

   The default `None` covers `reconstruct_from_broker`-derived positions (which have no parent ULID). The field is set at bracket-confirmation time inside `OrderManager._on_order_filled` or wherever the post-placement state is wired (verify the actual integration site in pre-flight; do NOT assume).

2. **Derive OCA group ID deterministically** from the bracket's parent order ULID:

   ```python
   oca_group_id = f"oca_{parent_order.id}"
   ```

   Per M1 disposition: deterministic derivation from `parent_ulid`. If `parent_order.id` is empty / None at the time the OCA group is derived (defensive — should not occur in practice per SbC edge cases), fall back to generating a fresh ULID via the existing `generate_id()` helper. Re-entry on the same symbol generates a new `oca_group_id` because the new bracket has a new parent ULID.

3. **Set `ocaGroup` and `ocaType` on bracket children** in `argus/execution/ibkr_broker.py:place_bracket_order` (around lines 731-782):

   The Order objects for stop, T1, and T2 (the three children) gain:

   ```python
   stop_order.ocaGroup = oca_group_id
   stop_order.ocaType = config.ibkr.bracket_oca_type  # 1 by default
   t1_order.ocaGroup = oca_group_id
   t1_order.ocaType = config.ibkr.bracket_oca_type
   t2_order.ocaGroup = oca_group_id
   t2_order.ocaType = config.ibkr.bracket_oca_type
   ```

   The parent (entry) Order does NOT get OCA fields — only the children. The `parentId` linkage between parent and children is unchanged (DEC-117 preserved).

4. **Add `bracket_oca_type` config field** to `IBKRConfig` in `argus/core/config.py` (around line 639):

   ```python
   bracket_oca_type: int = Field(
       default=1,
       ge=0,
       le=1,
       description=(
           "OCA type for bracket children. 1 = 'Cancel with block' "
           "(atomic cancellation when one OCA member fills); 0 = no OCA "
           "(pre-Sprint-31.91 behavior). ocaType=2 is architecturally "
           "wrong for ARGUS's bracket model — see Sprint 31.91 spec "
           "Performance Considerations. Switching from 1 to 0 is "
           "RESTART-REQUIRED — see live-operations.md runbook."
       ),
   )
   ```

   Add the field to `config/system.yaml` and `config/system_live.yaml` under the `ibkr:` section. Default value should be present in both YAMLs as `bracket_oca_type: 1` to make the contract explicit (do not rely on the Pydantic default to hide the value).

5. **SimulatedBroker no-op support** in `argus/execution/simulated_broker.py`:

   The `place_order` method must accept `Order` objects with `ocaGroup` and `ocaType` attributes set, store them on the in-memory order record (so a later inspection can verify they were passed through), but NOT implement any OCA cancellation semantics. This is the no-op acknowledgment per SbC §"Do NOT add: A 'simulated OCA cancellation' behavior in SimulatedBroker."

   Verify the existing `Order` model already supports `ocaGroup: str | None = None` and `ocaType: int = 0` fields. If not, add them (these are existing IBKR-side `ib_async` Order fields — verify against `ib_async` docs or the existing import).

6. **Defensive Error 201 / "OCA group is already filled" handling** on T1/T2 placement:

   In `place_bracket_order`, the existing rollback path at `argus/execution/ibkr_broker.py:783-805` handles errors via DEC-117. Session 1a EXTENDS that handler to distinguish:

   - **Generic Error 201** (margin rejection, price-protection, etc.): logged ERROR, rollback fires (existing behavior preserved).
   - **Error 201 with reason "OCA group is already filled"**: logged INFO not ERROR. Rollback STILL fires (cancel any partially-placed children) but the log severity is reduced because this is a SAFE outcome — the stop already filled and bought us out via OCA. The rollback completes; the position transitions to `is_fully_closed=True` via the stop fill callback.

   Reason-string parsing approach:

   ```python
   def _is_oca_already_filled_error(error: Exception) -> bool:
       """Parses IBKR Error 201 to distinguish OCA-filled (SAFE) from
       generic 201 (margin, price, etc.). The exact reason string is
       'OCA group is already filled' — verify against ib_async error
       payload shape during impl.

       Phase A spike (scripts/spike_ibkr_oca_late_add.py) confirmed
       PATH_1_SAFE: this string is the success signature for late-add
       OCA siblings.
       """
       if not isinstance(error, ...):  # the IBKR Error type from ib_async
           return False
       msg = str(error).lower()
       return "oca group is already filled" in msg
   ```

   Place this helper near the existing rollback logic in `ibkr_broker.py`.

7. **Add invariant 21 regression test** (per regression-checklist.md invariant 21 — SimulatedBroker OCA-assertion tautology guard, lands at Session 0 close-out per the spec but if Session 0's close-out deferred it, land it here):

   In a new file `tests/_regression_guards/test_oca_simulated_broker_tautology.py`:

   ```python
   def test_no_oca_assertion_uses_simulated_broker():
       """Anti-tautology guard (MEDIUM #11): tests asserting OCA behavior
       must use IBKR mocks. SimulatedBroker's OCA is a no-op
       acknowledgment, so any assertion of OCA-cancellation semantics
       against SimulatedBroker passes whether OCA is wired correctly or
       not. Future test authors who reach for SimulatedBroker because
       it's faster will produce false-passes.

       DEF-208 tracks the gap; spike script
       (scripts/spike_ibkr_oca_late_add.py) is the live-IBKR regression
       check that mitigates the gap.
       """
       import os, re
       forbidden = []
       for root, _, files in os.walk("tests"):
           for f in files:
               if not f.endswith(".py"):
                   continue
               path = os.path.join(root, f)
               with open(path) as fh:
                   src = fh.read()
               uses_sim = "SimulatedBroker" in src
               asserts_oca = bool(re.search(
                   r"oca|OCA|ocaGroup|ocaType",
                   src,
               ))
               if uses_sim and asserts_oca:
                   if "# allow-oca-sim:" in src:
                       continue
                   forbidden.append(path)
       assert not forbidden, (
           f"OCA-behavior tests must use IBKR mocks, not SimulatedBroker, "
           f"to avoid no-op tautology. Found in: {forbidden}. "
           f"Mark known-safe cases with `# allow-oca-sim: <reason>` comment."
       )
   ```

   Verify in the close-out whether Session 0 already landed this test; if so, just confirm it still passes.

## Constraints

- Do NOT modify:
  - `argus/execution/order_manager.py:1670-1750` — DEF-199 A1 fix (do-not-modify list).
  - `argus/main.py` — startup invariant region (do-not-modify list).
  - `argus/models/trading.py` — `Position` class. The new `oca_group_id` lives on `ManagedPosition` (in `order_manager.py`), NOT on `Position`.
  - `argus/execution/ibkr_broker.py:783-805` rollback structure — only EXTEND with the Error 201 / OCA-filled distinguishing helper. The atomic-bracket rollback DEC-117 invariant must be preserved end-to-end.
  - `argus/execution/alpaca_broker.py` — no Alpaca changes in Session 1a (Session 0 was the only AlpacaBroker change permitted).
  - `argus/data/alpaca_data_service.py:593` — out of scope.
  - The `workflow/` submodule (RULE-018).

- Do NOT change:
  - DEC-117 atomic-bracket invariant. If the `git diff` shows any change to the parent-fails-children-cancel pattern, escalation criterion A5 fires immediately — halt.
  - The reconciliation polling cadence.
  - Throttled-logger intervals.
  - `place_bracket_order`'s general structure: only `ocaGroup` / `ocaType` Order-field setting is added; bracket parent / child relationships, transmit flags, rollback paths are untouched in structure.

- Do NOT add:
  - A new `OrderType` enum value (the IBKR-side `ocaType` is an int, not an enum extension on our side).
  - "Simulated OCA cancellation" behavior in SimulatedBroker.
  - A second config field — only `bracket_oca_type` is added.

- Do NOT cross-reference other session prompts.

## Operator Choice (N/A this session)

Session 1a does not require operator pre-check. The OCA architecture is committed to (Phase A spike confirmed `PATH_1_SAFE`).

## Canary Tests (if applicable)

Before making any changes, run the canary-test skill in `.claude/skills/canary-test.md` with these tests to confirm baseline behavior:

- `test_dec117_rollback_on_t2_failure_cancels_t1_and_parent` (or whatever the exact pre-existing DEC-117 rollback test is named) — confirms DEC-117 atomic-bracket behavior pre-Session-1a.
- `test_bracket_order_places_three_children_under_parent` — confirms parent-child structure.

These set the "before" baseline for the after-implementation regression check.

## Test Targets

After implementation:

- Existing tests: all 5,080+ must still pass.
- New tests (~8 new pytest in `tests/execution/test_bracket_oca_grouping.py` or appended to the natural existing home — verify during pre-flight):

  1. `test_bracket_children_carry_oca_group`
     - Mock IBKR; call `place_bracket_order`; assert all 3 children Order objects have `ocaGroup == oca_group_id` and `ocaType == 1`.
  2. `test_bracket_oca_group_id_persists_to_managed_position`
     - After successful bracket placement, `ManagedPosition.oca_group_id` is the same value passed to children.
  3. `test_managed_position_oca_group_id_default_none`
     - ManagedPosition created via `reconstruct_from_broker` path has `oca_group_id is None`.
  4. `test_re_entry_after_close_gets_new_oca_group`
     - Close a position. Open a new one on the same symbol. Assert the new ManagedPosition has a DIFFERENT `oca_group_id` than the closed one.
  5. `test_bracket_oca_type_config_accepts_only_0_or_1`
     - Construct `IBKRConfig(bracket_oca_type=2)`. Assert Pydantic raises `ValidationError`. Same for negative integers.
  6. `test_dec117_rollback_with_oca_type_1_cancels_partial_children`
     - Force the T2 placement to raise mid-loop (after stop and T1 placed, before T2 placed). Assert the rollback at `ibkr_broker.py:783-805` fires; assert parent order is cancelled; assert T1 (which had ocaType=1) is also cancelled. **DEC-117 invariant must hold end-to-end.**
  7. `test_oca_group_deterministic_from_parent_ulid`
     - Per M1: `oca_group_id == f"oca_{parent_order.id}"`. Test the formula directly.
  8. `test_t1_t2_placement_error_201_oca_filled_handled_gracefully`
     - Mock IBKR to raise Error 201 with reason "OCA group is already filled" on T2 placement. Assert:
       - Logged at INFO not ERROR.
       - Existing rollback path STILL fires (T1 cancelled).
       - No orphaned OCA-A working orders remain.
       - No `phantom_short` alert emitted (this is a SAFE outcome).
     - Distinguishing test: same setup but with generic Error 201 ("Margin requirement not met"). Assert this case is logged at ERROR (existing behavior preserved).

- Test command (scoped per DEC-328):

  ```
  python -m pytest tests/execution/ tests/_regression_guards/ -n auto -q
  ```

## Config Validation

This session adds `ibkr.bracket_oca_type`. Write a test that loads the YAML config files and verifies the new key is recognized by the Pydantic model:

```python
def test_bracket_oca_type_yaml_loadable_no_silent_drop():
    """Sprint 31.91 Session 1a: verify config field added to YAML
    matches Pydantic model field name (no silent drop)."""
    import yaml
    from argus.core.config import IBKRConfig

    with open("config/system.yaml") as fh:
        cfg = yaml.safe_load(fh)
    ibkr_cfg = cfg.get("ibkr", {})
    assert "bracket_oca_type" in ibkr_cfg, (
        "config/system.yaml must include ibkr.bracket_oca_type "
        "explicitly; relying on Pydantic default hides the contract."
    )
    # Verify YAML keys are subset of model fields (no silent drop)
    yaml_keys = set(ibkr_cfg.keys())
    model_fields = set(IBKRConfig.model_fields.keys())
    extra = yaml_keys - model_fields
    assert not extra, f"YAML keys not in Pydantic model: {extra}"

    # Same for system_live.yaml
    with open("config/system_live.yaml") as fh:
        cfg_live = yaml.safe_load(fh)
    ibkr_cfg_live = cfg_live.get("ibkr", {})
    assert "bracket_oca_type" in ibkr_cfg_live
```

Expected mapping:

| YAML Key | Model Field |
|----------|-------------|
| `ibkr.bracket_oca_type` | `IBKRConfig.bracket_oca_type` |

## Marker Validation (N/A this session)

Session 1a does not add pytest markers.

## Definition of Done

- [ ] Bracket children carry `ocaGroup == oca_group_id` and `ocaType == 1` (verified by test 1).
- [ ] `oca_group_id = f"oca_{parent_ulid}"` deterministic derivation (test 7).
- [ ] `ManagedPosition.oca_group_id: str | None = None` field added.
- [ ] `bracket_oca_type` config accepts only 0 or 1; YAMLs include the field explicitly (test 5; config-validation test).
- [ ] Error 201 / "OCA group is already filled" logged INFO not ERROR; rollback STILL fires (test 8).
- [ ] Generic Error 201 (non-OCA reasons) still treated as ERROR (test 8 distinguishing case).
- [ ] DEC-117 rollback test passes end-to-end with `ocaType=1` (test 6).
- [ ] SimulatedBroker accepts `ocaGroup` / `ocaType` Order fields without crashing; stores them; does NOT implement cancellation semantics.
- [ ] Invariant 21 regression test (SimulatedBroker OCA-assertion tautology guard) lands or is verified to be present.
- [ ] All 5,080+ existing pytest still passing.
- [ ] CI green.
- [ ] Tier 2 review CLEAR.

## Regression Checklist (Session-Specific)

| Check | How to Verify |
|-------|---------------|
| `git diff HEAD~1 -- argus/execution/order_manager.py:1670-1750` shows zero edits | DEF-199 A1 fix protected (invariant 1) |
| `git diff HEAD~1 -- argus/execution/ibkr_broker.py:783-805` shows zero structural edits — only the new Error 201 distinguishing logic added near it | DEC-117 invariant (invariant 4); escalation A5 |
| `git diff HEAD~1 -- argus/main.py` shows zero edits | invariant 9 |
| `git diff HEAD~1 -- argus/models/trading.py` shows zero edits | invariant 15 |
| `git diff HEAD~1 -- argus/execution/alpaca_broker.py` shows zero edits | Session 0 was the only Alpaca change permitted |
| `git diff HEAD~1 -- argus/data/alpaca_data_service.py` shows zero edits | invariant 15 |
| Existing pre-Session-1a callers of `place_bracket_order` still work | grep for callers; verify all still execute |
| Pre-existing flake count unchanged | CI run: DEF-150, DEF-167, DEF-171, DEF-190, DEF-192 |
| `IBKRConfig.bracket_oca_type` rejects ocaType=2 | Pydantic ValidationError test |
| ocaType=1 50–200ms cancellation propagation cost is on cancelling siblings, not the firing order | Verified by Phase A spike `PATH_1_SAFE`; documented in Performance Considerations |

## Close-Out

After all work is complete, follow the close-out skill in `.claude/skills/close-out.md`.

The close-out report MUST include a structured JSON appendix at the end, fenced with ` ```json:structured-closeout `.

**Write the close-out report to a file** (DEC-330):

```
docs/sprints/sprint-31.91-reconciliation-drift/session-1a-closeout.md
```

Do NOT just print the report in the terminal. Create the file, write the full report (including the structured JSON appendix) to it, and commit it.

## Tier 2 Review (Mandatory — @reviewer Subagent)

After the close-out is written to file and committed, invoke the @reviewer subagent.

Provide the @reviewer with:

1. The review context file: `docs/sprints/sprint-31.91-reconciliation-drift/review-context.md`
2. The close-out report path: `docs/sprints/sprint-31.91-reconciliation-drift/session-1a-closeout.md`
3. The diff range: `git diff HEAD~1`
4. The test command: `python -m pytest tests/execution/ tests/_regression_guards/ -n auto -q` (scoped — DEC-328; non-final session)
5. Files that should NOT have been modified:
   - `argus/execution/order_manager.py:1670-1750` (DEF-199 A1 fix)
   - `argus/execution/ibkr_broker.py:783-805` (DEC-117 rollback STRUCTURE — only new distinguishing logic added near it)
   - `argus/main.py` (startup invariant region)
   - `argus/models/trading.py`
   - `argus/execution/alpaca_broker.py`
   - `argus/data/alpaca_data_service.py`
   - `docs/sprints/sprint-31.9/IMPROMPTU-04-closeout.md`
   - `workflow/` submodule

The @reviewer must use the **backend safety reviewer** template (`templates/review-prompt.md` from the workflow metarepo).

The @reviewer will produce its review report at:

```
docs/sprints/sprint-31.91-reconciliation-drift/session-1a-review.md
```

## Post-Review Fix Documentation

Same pattern as Session 0 — see implementation-prompt template §"Post-Review Fix Documentation". If @reviewer reports CONCERNS and you fix within this session, append "Post-Review Fixes" to the close-out file and "Post-Review Resolution" to the review file. Update the verdict JSON to `CONCERNS_RESOLVED`.

## Session-Specific Review Focus (for @reviewer)

1. **ocaType=1 vs `parentId` linkage compatibility.** Verify that adding `ocaGroup` / `ocaType` to children does NOT alter the `parentId` linkage between parent (entry) and the three children. The existing `transmit` flag pattern must be preserved — typically only the LAST child has `transmit=True` to trigger atomic placement.

2. **OCA group ID derivation determinism.** `oca_group_id = f"oca_{parent_order.id}"` — verify this formula in code matches what test 7 asserts.

3. **Error 201 distinguishing logic (OCA-filled vs generic).** Inspect the reason-string parser:
   - Does it match the exact `ib_async` error payload structure? (The spike script `scripts/spike_ibkr_oca_late_add.py` is the reference for the actual error message format.)
   - Does the generic Error 201 path (margin, price-protection) still emit ERROR severity? Test 8's distinguishing assertion catches this.
   - Does the OCA-filled path still trigger rollback? (DEC-117 must hold; the SAFE outcome doesn't bypass the invariant.)

4. **Re-entry produces new OCA groups.** The lifecycle test (test 4) verifies that closing a position and re-entering on the same symbol produces a distinct `oca_group_id`. Verify the test asserts this via direct comparison, not via just-not-None.

5. **DEC-117 atomic-bracket end-to-end behavior unchanged.** The most important review focus: if `git diff` reveals any change to the parent-fails-children-cancel pattern beyond the OCA-field additions, escalation A5 fires. Inspect `ibkr_broker.py:783-805` line-by-line and verify only the new distinguishing helper is added near the rollback — the rollback itself is structurally identical.

6. **YAML / Pydantic alignment.** Both `config/system.yaml` and `config/system_live.yaml` include `ibkr.bracket_oca_type: 1` explicitly. The config-validation test catches the silent-drop case (RULE-053 + protocol step 6).

7. **SimulatedBroker no-op-only.** The simulated broker accepts the new Order fields but does NOT implement OCA cancellation semantics. Search for any code in `simulated_broker.py` that simulates a cancellation when ocaGroup is set — if found, this is the exact behavior SbC §"Do NOT add" prohibits.

## Sprint-Level Regression Checklist (for @reviewer)

The full Sprint-Level Regression Checklist is in
`docs/sprints/sprint-31.91-reconciliation-drift/review-context.md`.

Of particular relevance to Session 1a:

- **Invariant 1 (DEF-199 A1 fix):** PASS — verify zero edits to `order_manager.py:1670-1750`.
- **Invariant 4 (DEC-117 atomic bracket invariant):** PASS — Session 1a is the ONLY session that touches bracket placement. Verify rollback still fires end-to-end.
- **Invariant 5 (5,080 pytest baseline holds):** PASS.
- **Invariant 9 (IMPROMPTU-04 startup invariant unchanged):** PASS.
- **Invariant 13 (New config fields parse without warnings):** PASS — the new `bracket_oca_type` field has both YAML+Pydantic alignment (config-validation test).
- **Invariant 14 (Monotonic-safety property):** Row "After Session 1a" — OCA bracket = YES; all others = NO (only bracket-side OCA wired this session).
- **Invariant 15 (do-not-modify list untouched):** PASS — verify the explicit list above.
- **Invariant 21 (SimulatedBroker OCA-assertion tautology guard):** Verify the test exists and passes (lands at Session 0 close-out per regression checklist; if not, lands at Session 1a).

## Sprint-Level Escalation Criteria (for @reviewer)

Of particular relevance to Session 1a:

- **A5** (Session 1a's bracket OCA grouping causes ANY change to DEC-117 atomic-bracket end-to-end behavior). The reviewer's most critical check. If found: halt, operator decides.
- **A4** (OCA-group ID lifecycle interacts with re-entry in a way the lifecycle tests didn't model). Test 4 covers re-entry; if a missed edge case surfaces during impl, document in close-out's "Discovered Edge Cases" section.
- **A8** (bracket placement performance regression — to be measured at Session 4 paper session debrief; observational only at Session 1a).
- **B1, B3, B4, B6** — standard halt conditions.

---

*End Sprint 31.91 Session 1a implementation prompt.*

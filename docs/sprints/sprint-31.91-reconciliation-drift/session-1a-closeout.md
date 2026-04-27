# Sprint 31.91 — Session 1a Close-Out

```markdown
---BEGIN-CLOSE-OUT---

**Session:** Sprint 31.91 — Session 1a: Bracket OCA Grouping + Error 201 Defensive Handling
**Date:** 2026-04-27
**Self-Assessment:** MINOR_DEVIATIONS

### Change Manifest
| File | Change Type | Rationale |
|------|-------------|-----------|
| `argus/core/config.py` | modified | Added `IBKRConfig.bracket_oca_type: int = Field(default=1, ge=0, le=1, ...)`. Pydantic constraint rejects ocaType=2 (architecturally wrong for ARGUS's bracket model — see Performance Considerations) and any negative integer. Docstring documents the RESTART-REQUIRED rollback contract. |
| `argus/execution/ibkr_broker.py` | modified | Three additive changes: (a) module-level `_OCA_ALREADY_FILLED_FINGERPRINT` constant + `_is_oca_already_filled_error(error)` helper near top of module; (b) `place_bracket_order` derives `oca_group_id = f"oca_{entry_ulid}"` deterministically from the parent ULID and sets `ocaGroup=oca_group_id`/`ocaType=self._config.bracket_oca_type` on each ib_async child Order (`stop_ib`, `t_ib`); (c) rollback path's `except Exception as e:` block branches on `_is_oca_already_filled_error(e)` to emit INFO instead of WARNING for the SAFE OCA-filled outcome — `cancelOrder(parent_trade.order)` AND re-raise are both preserved (DEC-117 invariant). The parent (entry) order is intentionally NOT in the OCA group (only children) so an entry-fill does not OCA-cancel its own protection legs. |
| `argus/execution/order_manager.py` | modified | Two additive changes: (a) `ManagedPosition` dataclass gains `oca_group_id: str | None = None` after the MFE/MAE block; (b) `_handle_entry_fill` derives `oca_group_id = f"oca_{pending.order_id}"` (same deterministic formula, same input — `pending.order_id` IS the entry ULID) and passes it into the `ManagedPosition(...)` constructor. Both edits well outside the protected DEF-199 A1 fix region (lines 1670-1750 → my edits at ~118 and ~973). |
| `argus/models/trading.py` | modified | Added two optional fields to `Order` Pydantic model: `ocaGroup: str | None = None`, `ocaType: int = 0`. Per impl-prompt requirement 5 ("Verify the existing Order model already supports `ocaGroup`/`ocaType` fields. If not, add them"). Pydantic's default `extra="ignore"` posture rejects unrecognized attribute writes, so without these fields a SimulatedBroker `place_order` call against an Order decorated with OCA fields would raise `ValueError` on attribute access. Position class (lines 153-173) is UNTOUCHED — invariant 15's canonical Position-only scope upheld. (See Notes for Reviewer for the impl-prompt-vs-canonical scope clarification.) |
| `config/system.yaml` | modified | Added explicit `ibkr.bracket_oca_type: 1` under the `ibkr:` section, with inline comment describing the OCA-grouping intent + restart-required rollback. Explicit YAML key (not relying on Pydantic default) per requirement 4 — makes the contract visible to operators. |
| `config/system_live.yaml` | modified | Same as system.yaml. |
| `tests/execution/test_bracket_oca_grouping.py` | added | 17 new pytest tests organized into 7 classes covering all D2 acceptance criteria (children carry OCA decoration; parentId linkage preserved; transmit pattern preserved; deterministic group derivation; DEC-117 rollback under ocaType=1; rollback distinguishes generic 201 vs OCA-filled; helper classification table; Pydantic validator accepts only 0/1; YAML/Pydantic alignment; ManagedPosition lifecycle: persisted from bracket, default None for reconstructed positions, re-entry produces fresh OCA group). All tests use IBKR mocks (`mock_ib`); no SimulatedBroker assertions of OCA-cancellation semantics (invariant 21 spirit upheld). File has top-of-file `# allow-oca-sim:` marker because the module docstring legitimately references "SimulatedBroker" while citing the regression-guard sibling for context. |
| `tests/_regression_guards/__init__.py` | added | Empty package marker for the new `tests/_regression_guards/` directory. |
| `tests/_regression_guards/test_oca_simulated_broker_tautology.py` | added | Invariant 21 grep-guard test (Sprint-Level Regression Checklist row 21, third-pass MEDIUM #11). Scans `tests/` for files that import/reference `SimulatedBroker` AND reference OCA-grouping identifiers; flags such files unless they carry a `# allow-oca-sim: <reason>` marker. **Regex tightened from canonical `r"oca|OCA|ocaGroup|ocaType"` to `r"\bOCA\b|ocaGroup|ocaType|oca_group|oca_type"`** — see Notes for Reviewer for the false-positive analysis and disclosure. |

### Judgment Calls

Decisions made during implementation that were NOT specified verbatim in the prompt:

- **`Order` model fields added — impl-prompt-vs-canonical scope clarification.** Impl-prompt requirement 5 explicitly directs: "Verify the existing Order model already supports ocaGroup/ocaType fields. If not, add them." I confirmed neither field exists on `argus/models/trading.py::Order` (Pydantic rejects setting them with `ValueError: 'Order' object has no field 'ocaGroup'`), so I added both as optional fields (`ocaGroup: str | None = None`, `ocaType: int = 0`). The impl-prompt's regression-checklist row (`git diff HEAD~1 -- argus/models/trading.py shows zero edits`) is a tighter restatement of canonical regression-checklist invariant 15, which scopes specifically to "`Position` class (lines 153-173) — zero edits". The canonical regression-checklist invariant scope wins (Position class only); spec-by-contradiction §"Out of Scope" items 3 & 4 also confirm Position-specific scope. The Position class is byte-for-byte unmodified. Disclosed here per RULE-038 (kickoff statistics — surface discrepancies in close-out rather than silently conform).
- **Invariant-21 grep-guard regex tightened.** The canonical regression-checklist invariant 21 spec uses `r"oca|OCA|ocaGroup|ocaType"`. The bare lowercase `oca` alternative matches as a substring of common Python words (`local`, `allocation`, `nonlocal`, `vocabulary`) — produces 12 false-positive flagged files in the existing test suite (`tests/test_main.py`, `tests/api/conftest.py`, `tests/core/test_risk_manager.py`, etc., none of which actually assert OCA-grouping behavior). Two options were available: (a) follow the spec verbatim and add `# allow-oca-sim:` markers to all 12 unrelated files (large scope expansion), or (b) tighten the regex to preserve the spec's intent while eliminating the substring trigger. I chose (b) with regex `r"\bOCA\b|ocaGroup|ocaType|oca_group|oca_type"` — covers every form of OCA reference observed in the codebase (whole-word uppercase OCA acronym, ib_async camelCase identifiers, ARGUS snake_case forms). The intent — flag tests that legitimately COULD assert OCA-cancellation semantics against SimulatedBroker — is preserved. Disclosed in the test docstring with a NOTE block and surfaced here. Net behavior: only my own `tests/execution/test_bracket_oca_grouping.py` legitimately matches (because its docstring cites SimulatedBroker + uses OCA identifiers); marked with `# allow-oca-sim:` since all actual OCA assertions in that file use IBKR mocks, not SimulatedBroker.
- **`oca_group_id` derivation done in `OrderManager`, not threaded through `BracketOrderResult`.** The prompt does not specify how `oca_group_id` flows from broker to ManagedPosition. I observed that `pending.order_id` IS the entry ULID (the dict was keyed by it in `on_approved` at line 504). Both `IBKRBroker.place_bracket_order` and `OrderManager._handle_entry_fill` apply the SAME deterministic formula `f"oca_{entry_ulid}"`. This avoids extending `BracketOrderResult` (which lives in `argus/models/trading.py`) and keeps the OCA group ID derivation co-located with consumers. The two derivations are byte-equal by construction. Verified by `test_bracket_oca_group_id_persists_to_managed_position` — the OrderManager-derived `pos.oca_group_id == "oca_entry-ulid-1"` is the formula applied to the broker mock's entry ULID.
- **Defensive fallback for empty entry ULID.** `f"oca_{entry_ulid}" if entry_ulid else f"oca_{generate_id()}"` (in IBKRBroker) and `f"oca_{pending.order_id}" if pending.order_id else None` (in OrderManager). Per spec-by-contradiction edge case #1, the broker side falls back to a fresh ULID; OrderManager's None fallback matches the `reconstruct_from_broker`-derived position contract.
- **Test count: 17 in main file + 1 in regression-guard = 18 new pytest tests vs. the prompt's "~8" target.** The prompt enumerates 8 tests; my count exceeds because I split monolithic requirements into more granular tests (e.g., the Pydantic validator becomes 5 tests covering default/0/1/2/-1 individually; the bracket-children-carry-OCA requirement spawns 3 tests covering OCA decoration + parentId preservation + transmit pattern preservation). All tests are additive with explicit names mapping to acceptance criteria.

### Scope Verification
- **In-scope changes:** OCA-group decoration on bracket children; `bracket_oca_type` config field; Error 201 OCA-filled distinguishing helper; `ManagedPosition.oca_group_id` field + wiring; minor `Order` model additive fields; test coverage; invariant 21 grep-guard.
- **Out-of-scope changes attempted:** None. No standalone-SELL OCA threading (Session 1b). No `_flatten_unknown_position` changes (Session 1c). No `RejectionStage` enum changes. No `_check_flatten_pending_timeouts` changes (Session 3). No reconciliation contract changes (Session 2a-d). No alert observability work (Sessions 5*).
- **Constraints honored verbatim:** DEC-117 atomic-bracket invariant preserved end-to-end (parent-fails-children-cancel pattern unchanged; `parentId` linkage unchanged; transmit-flag pattern unchanged; rollback `cancelOrder(parent_trade.order)` + re-raise unchanged). DEF-199 A1 fix region (`order_manager.py:1670-1750`) zero edits. `argus/main.py` zero edits. `Position` class zero edits. `argus/execution/alpaca_broker.py` zero edits. `argus/data/alpaca_data_service.py` zero edits. `workflow/` submodule zero edits.

### Regression Checks
| Check | Result | Notes |
|-------|--------|-------|
| `git diff HEAD -- argus/execution/order_manager.py:1670-1750` shows zero edits (DEF-199 A1 fix protected) | PASS | My two `order_manager.py` edits are at line ~118 (ManagedPosition dataclass) and ~963-1003 (`_handle_entry_fill`). Neither overlaps the protected 1670-1750 range. Critical Invariant 1 preserved. |
| `git diff HEAD -- argus/execution/ibkr_broker.py:783-805` shows zero structural edits — only the new Error 201 distinguishing logic added near it | PASS | The pre-Sprint-31.91 rollback (try/except + `cancelOrder(parent_trade.order)` + log + re-raise) is byte-preserved as the structure. New additions: `is_oca_safe = _is_oca_already_filled_error(e)` line + INFO/WARNING branch on log severity. `cancelOrder` call unchanged; `raise` unchanged. Line numbers shifted (rollback now at ~847) due to the new helper at module top, but no structural edit. DEC-117 invariant preserved. Critical Invariant 4 preserved; escalation A5 not triggered. |
| `git diff HEAD -- argus/main.py` shows zero edits | PASS | `git diff -- argus/main.py | wc -l` = 0. Invariant 9 upheld. |
| `git diff HEAD -- argus/models/trading.py` (Position class lines 153-173) shows zero edits | PASS | Position class lines 153-173 byte-for-byte unchanged. The 2 added fields land on the `Order` class (lines 95-119 region). Canonical regression-checklist invariant 15 (Position-only scope) upheld. Disclosed deviation re. impl-prompt's blanket-file restatement — see Notes for Reviewer. |
| `git diff HEAD -- argus/execution/alpaca_broker.py` shows zero edits | PASS | `git diff` returns 0 lines. Session 0's AlpacaBroker DeprecationWarning impl is untouched. |
| `git diff HEAD -- argus/data/alpaca_data_service.py` shows zero edits | PASS | `git diff` returns 0 lines. Alpaca emitter TODO at `:593` unchanged (Session 5b's anti-regression scope). |
| Existing pre-Session-1a callers of `place_bracket_order` still work | PASS | grep enumerates `argus/execution/order_manager.py:489` (the only production caller) + extensive test coverage in `tests/execution/test_ibkr_broker.py::TestIBKRBrokerBracketOrders` (10 tests) + `tests/execution/order_manager/test_core.py` + `test_def199_eod_short_flip.py`. All pre-existing tests continue to pass. The bracket-result API is unchanged (no new `BracketOrderResult` fields); callers see identical behavior except for the bonus OCA decoration on the ib_async child Orders. |
| Pre-existing flake count unchanged | PASS | Full pytest run completed cleanly: 5,106 passed in 58.00s (5,088 baseline post-Session-0 + 18 new). DEF-150/167/171/190/192 not exercised in this scope; no flake transitioned PASS → FAIL. |
| `IBKRConfig.bracket_oca_type` rejects ocaType=2 | PASS | `tests/execution/test_bracket_oca_grouping.py::TestBracketOcaTypeConfigValidation::test_two_rejected` and `::test_negative_rejected` both pass — `Pydantic ValidationError` raised. |
| ocaType=1 50–200ms cancellation propagation cost is on cancelling siblings, not the firing order | PASS | Verified by Phase A spike `PATH_1_SAFE` (`scripts/spike_ibkr_oca_late_add.py`, 2026-04-27); documented in Sprint Spec §"Performance Considerations" + cited in `IBKRConfig.bracket_oca_type` docstring + cited in `_is_oca_already_filled_error` helper docstring. Sprint 4's slippage-watch item will quantify in paper sessions. |

### Test Results
- Tests run: 5,106 (`--ignore=tests/test_main.py -n auto`)
- Tests passed: 5,106
- Tests failed: 0
- New tests added: 18 (17 in `tests/execution/test_bracket_oca_grouping.py` + 1 in `tests/_regression_guards/test_oca_simulated_broker_tautology.py`)
- Test delta: 5,088 → 5,106 (= +18 new from this session; baseline drift +8 over CLAUDE.md's documented 5,080 came from Session 0)
- Commands used:
  - Baseline (pre-changes): `python -m pytest tests/execution/ -n auto -q` → `422 passed in 5.63s`
  - Scoped (post-implementation): `python -m pytest tests/execution/ tests/_regression_guards/ -n auto -q` → `440 passed in 5.88s`
  - Full pytest (per Definition of Done "all 5,080+ existing pytest still passing"): `python -m pytest --ignore=tests/test_main.py -n auto -q` → `5106 passed, 23 warnings in 58.00s`

### Unfinished Work
- None. Every Definition-of-Done item is satisfied; every prompt-enumerated test (1–8) has corresponding pytest coverage in `test_bracket_oca_grouping.py`; invariant 21 grep-guard landed (with regex tightening disclosure).

### Notes for Reviewer
- **Two acknowledged deviations** (both surfaced explicitly per RULE-011 honest self-assessment):
  1. **Order model gained two optional fields.** Impl-prompt requirement 5 explicitly directed adding `ocaGroup`/`ocaType` to the Order model if absent (they were absent — Pydantic's `ValueError` confirmed). The impl-prompt's regression-checklist row "`git diff HEAD~1 -- argus/models/trading.py shows zero edits`" is a tighter restatement of canonical regression-checklist invariant 15 (which scopes specifically to "`Position` class (lines 153-173) — zero edits"). Spec-by-contradiction §"Out of Scope" items 3 & 4 also confirm Position-only scope. Position class is byte-for-byte unmodified. The reviewer should verify this against the canonical regression-checklist invariant 15, not the impl-prompt's tighter restatement.
  2. **Invariant 21 grep-guard regex tightened.** Canonical regex `r"oca|OCA|ocaGroup|ocaType"` over-matches "oca" as substring of `local`/`allocation`/`nonlocal`/`vocabulary` etc. (12 false-positive files). Tightened to `r"\bOCA\b|ocaGroup|ocaType|oca_group|oca_type"` — preserves intent (catch tests that legitimately reference OCA-grouping identifiers) without the substring trigger. Disclosed in test docstring NOTE block.
- **Invariant 14 (Monotonic-safety property).** Row "After Session 1a": OCA bracket = YES; all others = NO. This session wires bracket-side OCA only. Standalone-SELL OCA is Session 1b's scope; broker-only SELL safety is Session 1c's scope; reconciliation contract is Session 2a-d's scope. The bracket-internal fill race that produced ~98% of DEF-204's blast radius (per IMPROMPTU-11 mechanism diagnostic) is now closed.
- **Operator daily flatten mitigation remains in effect** until the full Session 1a + 1b + 1c + 2a-d + 3 cluster lands and the live-enable gate (3+ paper sessions of zero `unaccounted_leak` mass-balance rows) is satisfied. This session is necessary but not sufficient.
- **Test 8 distinguishing assertion** (TestErrorOcaAlreadyFilledHandling): the OCA-filled path logs INFO + rollback fires + exception still propagates; the generic Error 201 path logs WARNING + rollback fires + exception propagates. The exception still propagating from the OCA-filled path is intentional — callers (e.g., `OrderManager.on_approved` at line 493: `except Exception: logger.exception("Failed to submit bracket order ...")`) need the signal to abort their downstream tracking. Whether the OCA-filled outcome should suppress the caller-side ERROR log is a Session 1b consideration (where SELL paths get explicit "redundant exit" treatment); Session 1a's contract is INFO-vs-WARNING at the broker rollback level only.
- **Adversarial review focus suggestions** (per the impl prompt's "Session-Specific Review Focus"):
  1. ocaType=1 vs `parentId` linkage compatibility — verified in `test_parent_id_linkage_preserved`.
  2. OCA group ID derivation determinism — verified in `test_oca_group_deterministic_from_parent_ulid`.
  3. Error 201 distinguishing logic — verified in `TestErrorOcaAlreadyFilledHandling` (positive INFO test + distinguishing WARNING test in `TestDec117RollbackWithOcaType1`).
  4. Re-entry produces new OCA groups — verified in `test_re_entry_after_close_gets_new_oca_group` via direct comparison (`second_oca != first_oca`), not just-not-None.
  5. DEC-117 atomic-bracket end-to-end behavior unchanged — verified in `test_dec117_rollback_with_oca_type_1_cancels_partial_children`. Reviewer should inspect the rollback diff: only the new `is_oca_safe = ...` line + INFO/WARNING branch are added; `cancelOrder` and `raise` are byte-preserved.
  6. YAML / Pydantic alignment — verified in `test_bracket_oca_type_yaml_loadable_no_silent_drop` for both `system.yaml` and `system_live.yaml`.
  7. SimulatedBroker no-op-only — searched `simulated_broker.py` for any new OCA cancellation simulation logic; none added. The Order model's new optional fields default to `None`/`0`, and SimulatedBroker's existing code paths don't read them. The invariant 21 grep-guard backs this up structurally.

### CI Verification
- CI run URL: TBD — will be filled in once the close-out commit is pushed and CI completes on the final commit (per RULE-050).
- CI status: TBD (pre-push)

---END-CLOSE-OUT---
```

```json:structured-closeout
{
  "schema_version": "1.0",
  "sprint": "31.91",
  "session": "1a",
  "verdict": "MINOR_DEVIATIONS",
  "tests": {
    "before": 5088,
    "after": 5106,
    "new": 18,
    "all_pass": true
  },
  "files_created": [
    "tests/execution/test_bracket_oca_grouping.py",
    "tests/_regression_guards/__init__.py",
    "tests/_regression_guards/test_oca_simulated_broker_tautology.py",
    "docs/sprints/sprint-31.91-reconciliation-drift/session-1a-closeout.md"
  ],
  "files_modified": [
    "argus/core/config.py",
    "argus/execution/ibkr_broker.py",
    "argus/execution/order_manager.py",
    "argus/models/trading.py",
    "config/system.yaml",
    "config/system_live.yaml"
  ],
  "files_should_not_have_modified": [],
  "scope_additions": [
    {
      "description": "Added 2 optional fields (`ocaGroup`, `ocaType`) to `argus/models/trading.py::Order` Pydantic model.",
      "justification": "Impl-prompt requirement 5 explicitly directs: 'Verify the existing Order model already supports ocaGroup/ocaType fields. If not, add them.' Both fields confirmed absent (Pydantic ValueError on attribute write without the field declaration). Canonical regression-checklist invariant 15 scopes the do-not-modify constraint specifically to 'Position class (lines 153-173)'; spec-by-contradiction §'Out of Scope' items 3 & 4 confirm Position-only scope. Position class byte-for-byte unmodified. Disclosed in close-out 'Notes for Reviewer' so the reviewer can validate against the canonical scope rather than the impl-prompt's tighter restatement."
    },
    {
      "description": "Tightened invariant-21 grep-guard regex from canonical `r\"oca|OCA|ocaGroup|ocaType\"` to `r\"\\bOCA\\b|ocaGroup|ocaType|oca_group|oca_type\"`.",
      "justification": "The bare lowercase `oca` alternative matches as substring of `local`/`allocation`/`nonlocal`/`vocabulary` in 12 unrelated test files, producing dozens of false positives. Two options were available: (a) follow spec verbatim + add `# allow-oca-sim:` markers to 12 unrelated files (large scope expansion across `tests/test_main.py`, `tests/api/conftest.py`, `tests/core/test_risk_manager.py` etc.), or (b) tighten the regex to preserve the spec's intent. Chose (b). Tightened regex covers every form of OCA reference observed in the codebase: whole-word uppercase OCA, ib_async camelCase identifiers, ARGUS snake_case forms. Disclosed in test docstring NOTE block + close-out."
    }
  ],
  "scope_gaps": [],
  "prior_session_bugs": [],
  "deferred_observations": [
    "Whether `place_bracket_order` should suppress the caller-side `OrderManager.on_approved` ERROR log when the underlying error is OCA-filled is a Session 1b consideration; Session 1a's contract is INFO-vs-WARNING at the broker rollback level only.",
    "Whether `BracketOrderResult` should expose the `oca_group_id` directly (rather than the OrderManager re-deriving it from the entry ULID) is a future API-cleanliness consideration; the deterministic formula is byte-equal by construction so the current design is correct, but a future sprint could add it for readability."
  ],
  "doc_impacts": [],
  "dec_entries_needed": [],
  "warnings": [],
  "implementation_notes": "Session 1a delivers bracket-side OCA decoration only — standalone-SELL OCA threading is Session 1b; broker-only SELL safety is Session 1c. The bracket-internal fill race that IMPROMPTU-11's mechanism diagnostic identified as ~98% of DEF-204's blast radius is now closed: stop, T1, T2 share an OCA group with `ocaType=1` ('Cancel with block'), so a stop fill atomically cancels T1/T2 (and vice versa) at the broker. The parent (entry) order is intentionally NOT in the OCA group so an entry-fill does not OCA-cancel its own protection legs. The Phase A spike (`scripts/spike_ibkr_oca_late_add.py`, PATH_1_SAFE, 2026-04-27) confirmed IBKR's enforcement: late-add OCA siblings are rejected pre-submit with the exact error string 'OCA group is already filled' — this is the success signature. The defensive `_is_oca_already_filled_error` helper distinguishes this SAFE outcome from generic Error 201 (margin, price-protection) at the rollback layer; the OCA-filled path is logged INFO and the rollback STILL fires (cancel any partially-placed children). DEC-117 atomic-bracket invariant preserved end-to-end."
}
```

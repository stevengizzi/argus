# Sprint 31.92, Session S4a-ii: Synchronous-Update Invariant on All Bookkeeping Paths + FAI #8 Reflective-Call AST + FAI #11 Callsite-Enumeration Exhaustiveness — NEW SESSION per Tier 3 items A + B + Decision 3 + Round 3 H-R3-5

## Pre-Flight Checks

Before making any changes:

1. **Read `.claude/rules/universal.md` in full and treat its contents as binding for this session.** The full set of universal RULE entries (currently RULE-001 through RULE-053) applies regardless of whether any specific rule is referenced inline in this prompt. RULE-038 (grep-verify discipline), RULE-043 (`except Exception:` swallowing test signals — relevant when scrutinizing AST guards that catch exceptions and could mask `pytest.fail`), RULE-046 (no `Test*`-prefixed non-test classes), RULE-048 (verify library-behavior side-effects empirically rather than trusting kickoff claims), and RULE-050 (CI-green discipline) apply with particular force.

2. Read these files to load context:
   - `argus/execution/order_manager.py` — the 5 callback paths that mutate the bookkeeping counters: `on_fill` (partial-fill transfer + full-fill transfer), `on_cancel` (decrement), `on_reject` (decrement), `_on_order_status` (status-driven mutations), and `_check_sell_ceiling` (multi-attribute read sequence). Plus `_reserve_pending_or_fail` from S4a-i (the reference implementation). Plus the new `_read_positions_post_refresh` helper from S3b (per M-R3-4 — AST scan extends to its body too). Anchor by function names (line numbers DIRECTIONAL ONLY per protocol v1.2.0+).
   - `argus/execution/order_manager.py` callsites of `_check_sell_ceiling` and `_reserve_pending_or_fail` with `is_stop_replacement=True` — these need the H-R2-5 callsite-scan AST coverage including reflective-call patterns.
   - The S4a-i close-out: `docs/sprints/sprint-31.92-def-204-round-2/session-s4a-i-closeout.md`. Specifically, the existing AST guard test pattern from `_reserve_pending_or_fail` is the reference implementation for S4a-ii's broader scope.
   - The sprint spec § "Acceptance Criteria" Deliverable 3 (AC3.1 synchronous-update invariant + AC3.5 race test + AC3.5 extended scope per Tier 3 items A + B; FAI entry #9; Decision 3 reflective-call sub-tests).
   - `docs/sprints/sprint-31.92-def-204-round-2/falsifiable-assumption-inventory.md` — entries #1 + #8 + #9 (the falsifying mechanisms scheduled at S4a-ii) + the pending FAI #11 text in the bottom subsection (S4a-ii materializes #11 at close-out).
   - `docs/sprints/sprint-31.92-def-204-round-2/round-3-disposition.md` § 3.5 (H-R3-5 — AC3.1 callsite-enumeration AST exhaustiveness guard) + § 4.4 (M-R3-4 — `_read_positions_post_refresh` helper AST extension) + § 6.2 (FAI #11 verbatim text).

3. Run the test baseline (DEC-328 — Session 8+ of sprint, scoped):

   ```
   python -m pytest tests/execution/order_manager/ -n auto -q
   ```

   Expected: all passing (full suite was confirmed by S4a-i's close-out). Note: in autonomous mode, the expected test count is dynamically adjusted by the runner based on the previous session's actual results; the count above is the planning-time estimate.

4. Verify you are on the correct branch: **`main`**.

5. **Run the structural-anchor grep-verify commands** from the "Files to Modify" section below. For each entry, run the verbatim grep-verify command and confirm the anchor still resolves to the expected location. If drift is detected, disclose under RULE-038 in the close-out and proceed against the actual structural anchors. If the anchor is not found at all, HALT and request operator disposition rather than guess.

6. Verify S3b + S4a-i deliverables are present on `main`:

   ```bash
   grep -n "_reserve_pending_or_fail" argus/execution/order_manager.py
   grep -n "_check_sell_ceiling" argus/execution/order_manager.py
   grep -n "_read_positions_post_refresh" argus/execution/order_manager.py
   grep -n "cumulative_pending_sell_shares" argus/execution/order_manager.py
   grep -n "cumulative_sold_shares" argus/execution/order_manager.py
   grep -n "is_reconstructed" argus/execution/order_manager.py
   grep -n "test_no_await_in_reserve_pending_or_fail_body\|test_reserve_pending_or_fail_race_observable_under_injection" tests/execution/order_manager/test_def204_round2_ceiling.py
   ```

   All seven anchors must match. If any are missing, halt — S3b or S4a-i has not landed yet.

## Objective

Extend the H-R2-1 atomic-reserve protection pattern (AST-no-await scan + mocked-await injection regression) to ALL bookkeeping callback paths that mutate `cumulative_pending_sell_shares` or `cumulative_sold_shares` per Tier 3 items A + B / FAI entry #9 — `on_fill` (partial-fill + full-fill transfer), `on_cancel` (decrement), `on_reject` (decrement), `_on_order_status` (status-driven mutations), and the `_check_sell_ceiling` multi-attribute read; PLUS 3 reflective-call sub-tests per Decision 3 / FAI #8 option (a) probing for AST-scan false-negative paths via (a) `**kw` unpacking, (b) computed-value flag assignment, (c) `getattr` reflective access; PLUS `test_bookkeeping_callsite_enumeration_exhaustive` per Round 3 H-R3-5 / FAI #11 (~40 LOC test); PLUS AST-no-await scan extension to `_read_positions_post_refresh()` helper per M-R3-4. **Preferred outcome: zero production-code change.** The session is diagnostic — if static-analysis reveals an existing await between bookkeeping read and write in any callback path, production-code amendment is allowed under the same synchronous-before-await contract; otherwise the test file establishes the regression guard and S4a-ii closes with no production diff.

## Requirements

1. **Create `tests/execution/order_manager/test_def204_callback_atomicity.py`** (NEW FILE, ~120 LOC for 7 effective tests + ~40 LOC for the FAI #11 exhaustiveness test = ~160 LOC total — within the small-file budget).

2. **Implement the AST-no-await scan helper** (a small private fixture or module-level helper inside the test file — do NOT add a new module under `argus/`):

   ```python
   import ast, inspect, textwrap

   def _walk_for_awaits_between_attrs(
       func, attr_names: tuple[str, ...]
   ) -> list[ast.Await]:
       """Walk func's source for ast.Await nodes between any two
       statements where the FIRST statement reads an attribute in
       attr_names AND a SUBSEQUENT statement (within the same lexical
       block) writes an attribute in attr_names. Returns the list of
       ast.Await nodes that violate the synchronous-update invariant.

       For a coarse-grained guard, the function-level guard 'no
       ast.Await anywhere in the function body' is the simpler check;
       this helper lets us scope the assertion narrowly when a callback
       legitimately awaits OUTSIDE the bookkeeping region."""
       src = textwrap.dedent(inspect.getsource(func))
       tree = ast.parse(src)
       offending: list[ast.Await] = []
       # Implementation: walk sibling statements; track whether any
       # statement reads/writes the named attributes; for any await
       # between a read of an attr in attr_names and a write of an
       # attr in attr_names, append it. The exact algorithm detail is
       # left to the implementer; the test assertion is the contract.
       # KEEP THE HELPER UNDER ~30 LOC; if it grows beyond, the test
       # is becoming an analysis tool — flag and reconsider scope.
       return offending
   ```

   The helper's exact algorithm is left to the implementer; the asserting tests below are the contract. If the function-level "no ast.Await anywhere in the body" guard suffices for a given callback (e.g., `on_cancel` is small and synchronous-by-construction), use the simpler check; reach for the narrower bookkeeping-region scope only when a callback legitimately needs to await elsewhere.

3. **Wire 5 synchronous-update invariant tests** (one per bookkeeping callback path) per AC3.1 / FAI entry #9 / regression invariant 23. The first 4 tests use the same shape:

   ```python
   def test_synchronous_update_invariant_on_<callback_path>():
       """AC3.1 / regression invariant 23: <callback_path> mutates
       cumulative_pending_sell_shares and/or cumulative_sold_shares
       synchronously between the read and the write — no ast.Await
       between."""
       # Part A: AST-no-await scan over the relevant region.
       offending = _walk_for_awaits_between_attrs(
           OrderManager.<callback_path>,
           ("cumulative_pending_sell_shares", "cumulative_sold_shares"),
       )
       assert offending == [], (
           f"Synchronous-update invariant violated in "
           f"<callback_path>: ast.Await found between bookkeeping "
           f"read and write. Lines: {[a.lineno for a in offending]}"
       )

       # Part B: Mocked-await injection — assert the race IS observable
       # under injection (proves the test is sensitive enough to catch
       # a regression).
       # Detail: monkey-patch the implementation to insert
       # `await asyncio.sleep(0)` between the read and the write,
       # then run the C-1-race-style scenario; assert the race surfaces
       # (e.g., a torn-read produces an artificially-low ceiling check
       # that admits a SELL that should be blocked). The injection IS
       # the falsification — without it, the AST guard could be passing
       # for the wrong reason.
   ```

   The 5 paths and their bookkeeping-region semantics:

   - **(test 1) `on_fill` partial-fill transfer:** reads `cumulative_pending_sell_shares`, writes the decrement; reads `cumulative_sold_shares`, writes the increment. NO `ast.Await` between the decrement and the increment. (Per session-breakdown line 1098–1104, partial-fill and full-fill cases may merge via parametrize × 2 — counted as 1 logical test with 2 parametrize cases.)

   - **(test 2 — merged with test 1 via parametrize × 2)** `on_fill` full-fill transfer: same shape, full-fill semantics.

   - **(test 3) `on_cancel` decrement:** reads `cumulative_pending_sell_shares`, writes the decrement. NO `ast.Await` between read and write.

   - **(test 4) `on_reject` decrement:** reads `cumulative_pending_sell_shares`, writes the decrement. NO `ast.Await` between read and write.

   - **(test 5) `_check_sell_ceiling` multi-attribute read:** reads `cumulative_pending_sell_shares`, then reads `cumulative_sold_shares`, then computes the sum and compares to `shares_total`. NO `ast.Await` between the two reads OR between the second read and the computation. The torn-read race (where `pending` is decremented but `sold` not yet incremented) is exactly what this AST guard prevents.

   - **(test for `_on_order_status`) — per FAI #9 scope:** if `_on_order_status` mutates `cumulative_pending_sell_shares` or `cumulative_sold_shares`, add a 6th test with the same shape. If `_on_order_status` does NOT mutate either counter (verify during pre-flight), document that fact in the close-out and skip the test (the FAI #11 exhaustiveness check would fail noisily if a mutation slipped in later — that's the structural defense).

4. **Wire 3 reflective-call sub-tests** per Decision 3 / FAI #8 option (a) / regression invariant 23. These probe whether the AST callsite-scan for `is_stop_replacement=True` callers catches reflective patterns:

   - **(test 6) `test_ast_scan_catches_kw_unpacking_for_is_stop_replacement_callsite`** — synthetic call site where the source contains `kw = {"is_stop_replacement": True}; om._check_sell_ceiling(..., **kw)` (or analogous on `_reserve_pending_or_fail`). The AST scan must either (a) flag the `**kw` callsite as "potentially overriding the default" OR (b) document the gap as a known coverage hole. **Decision 3 chose option (a) detection-with-flag; (b) accept-and-document was NOT taken.** Build the synthetic source as a string, parse via `ast.parse`, and run the AST scanner against it; assert the scanner flags it.

   - **(test 7) `test_ast_scan_catches_computed_value_flag_for_is_stop_replacement_callsite`** — synthetic source: `flag = compute_flag(); om._check_sell_ceiling(..., is_stop_replacement=flag)`. Computed-value flag assignment masks the literal-`True` pattern; AST scan must flag.

   - **(test 8) `test_ast_scan_catches_getattr_reflective_access_for_check_sell_ceiling`** — synthetic source: `getattr(om, '_check_sell_ceiling')(..., is_stop_replacement=True)`. `getattr`-based reflective access masks the symbolic call; AST scan must flag.

   The exact AST-scanner implementation can be a small helper inside the same test file (or imported from S4a-i's existing AST infrastructure if S4a-i ships a reusable scanner). Each sub-test feeds a tiny synthetic-source string into `ast.parse` and asserts the scanner's output. The synthetic sources are NOT attempts to instrument production code — they're test-only AST inputs.

5. **Wire `test_bookkeeping_callsite_enumeration_exhaustive`** per FAI #11 / Round 3 H-R3-5 / regression invariant 29 (~40 LOC):

   ```python
   def test_bookkeeping_callsite_enumeration_exhaustive():
       """FAI #11 / regression invariant 29: AST scan walks
       OrderManager's source for ast.AugAssign nodes targeting
       cumulative_pending_sell_shares or cumulative_sold_shares;
       finds the enclosing function name for each; asserts the set
       of enclosing functions is a subset of the FAI #9 protected
       callsite list.

       Resolution if falsified: either add the discovered callsite to
       FAI #9's protection scope (preferred) OR document the coverage
       gap with explicit rationale.
       """
       PROTECTED_CALLSITES = {
           "_reserve_pending_or_fail",  # S4a-i (place-time)
           "on_fill",                    # S4a-i (partial + full fill transfer)
           "on_cancel",                  # S4a-i (decrement)
           "on_reject",                  # S4a-i (decrement)
           "_on_order_status",           # S4a-i if it mutates; otherwise
                                          # included for forward-compat.
           "_check_sell_ceiling",        # S4a-i (multi-attribute read; no
                                          # mutation, but FAI #9 scope
                                          # includes the read sequence).
           "reconstruct_from_broker",    # S4a-i (initialization to 0).
       }

       import ast, inspect
       from argus.execution.order_manager import OrderManager

       src = inspect.getsource(OrderManager)
       tree = ast.parse(src)

       found_callsites: set[str] = set()
       # Walk for ast.AugAssign nodes whose target is an Attribute
       # access on cumulative_pending_sell_shares OR
       # cumulative_sold_shares. Find the enclosing FunctionDef /
       # AsyncFunctionDef name and record it.
       # Implementation detail left to the implementer; the assertion
       # below is the contract.
       <ast walk with parent-tracking>

       extra = found_callsites - PROTECTED_CALLSITES
       assert extra == set(), (
           f"FAI #11 falsified: bookkeeping mutation callsites "
           f"outside the FAI #9 protected list: {extra}. "
           f"Resolution: add to PROTECTED_CALLSITES (preferred) OR "
           f"document the coverage gap with explicit rationale."
       )
   ```

   Note: `ast.walk` does not preserve parent links by default. Use `ast.walk` + a small parent-tracking pass (walk the tree once recording each node's enclosing FunctionDef name, then walk again looking for AugAssign), OR import `ast.NodeVisitor` and override `visit_FunctionDef` to maintain a `current_function` stack. Either pattern is acceptable; ~40 LOC budget covers the implementation including the visitor.

6. **Wire AST-no-await scan extension to `_read_positions_post_refresh()`** per M-R3-4 / regression invariant 30:

   ```python
   def test_no_await_between_refresh_and_read_in_read_positions_post_refresh():
       """Regression invariant 30 / M-R3-4: the helper composes
       refresh_positions() (await) + get_positions() (synchronous read)
       into a single synchronous read-after-refresh sequence. The ONLY
       ast.Await in the helper body is the refresh_positions call;
       there must be NO await between refresh completion and the
       cache read (no yield-gap-between-refresh-and-read race class)."""
       src = textwrap.dedent(inspect.getsource(
           OrderManager._read_positions_post_refresh
       ))
       tree = ast.parse(src)
       awaits = [n for n in ast.walk(tree) if isinstance(n, ast.Await)]
       # Expected: exactly 1 ast.Await — the refresh_positions call.
       assert len(awaits) == 1, (
           f"_read_positions_post_refresh body has {len(awaits)} "
           f"ast.Await nodes; expected exactly 1 (the refresh_positions "
           f"call). Yield-gap-between-refresh-and-read race class is "
           f"reopened if additional awaits appear."
       )
       # Optional secondary assertion: verify the single await is the
       # refresh_positions call, not e.g. a later await that slipped in.
       # The implementer can use ast.dump or attribute inspection to
       # confirm; this is defense-in-depth, not strictly required.
   ```

   This test merges into the same file as the other AST tests (no separate file).

7. **Production-code modification is conditional on static-analysis findings.** Per session-breakdown § "Why this is a NEW session (rationale)":

   > The NEW session's preferred outcome is **zero production-code change** — the test file establishes the regression guard. If static-analysis reveals an existing await between bookkeeping read and write, production-code amendment is allowed at S4a-ii under the same synchronous-before-await contract.

   Run all the AST tests during local development BEFORE writing the test file's final form. If any callback path fails the synchronous-update invariant scan in the current production code (i.e., there's an await between read and write that S4a-i didn't catch because S4a-i's scope was narrower), fix the production code at S4a-ii — but ONLY in the failing path. Do NOT refactor surrounding code per RULE-007 / RULE-001.

   Document the static-analysis findings in the close-out's "Static-Analysis Findings" section:
   - List of the 5+ callback paths inspected.
   - For each: PASS (no await between bookkeeping read and write) OR FAIL (await found at line N; production fix landed in this session).
   - Net production-code LOC change (target: 0; actual: ≤ 30 LOC if static-analysis fail).

## Files to Modify

For each file the session edits, the structural anchor + edit shape + pre-flight grep-verify command are listed below. Line numbers MAY appear as directional cross-references but are NEVER the sole anchor.

1. `tests/execution/order_manager/test_def204_callback_atomicity.py` (NEW FILE):
   - Anchor: file does not exist; CREATE.
   - Edit shape: new test file ~160 LOC for 7 effective tests + 1 FAI #11 exhaustiveness test + 1 M-R3-4 helper-AST test. Hard cap at ~200 LOC to avoid large-new-file compaction penalty.
   - Pre-flight grep-verify:
     ```bash
     ls tests/execution/order_manager/test_def204_callback_atomicity.py 2>/dev/null && echo "EXISTS" || echo "ABSENT (will create)"
     ```

2. `argus/execution/order_manager.py` (CONDITIONAL — only if static-analysis fails):
   - Anchor: the specific callback path that fails the synchronous-update invariant scan (function name).
   - Edit shape: surgical removal/relocation of the offending `await` so the bookkeeping read-and-write happens synchronously. ≤ 30 LOC budget; if larger, scope creep — halt and surface.
   - Pre-flight grep-verify:
     ```bash
     grep -n "def on_fill\|def on_cancel\|def on_reject\|def _on_order_status\|def _check_sell_ceiling\|def _read_positions_post_refresh\|def _reserve_pending_or_fail" argus/execution/order_manager.py
     # Expected: ≥6 hits. _on_order_status may be absent if S4a-i's
     # scope didn't include it — verify.
     ```

## Constraints

- Do NOT modify:
  - `argus/execution/order_manager.py` UNLESS static-analysis reveals an existing synchronous-update invariant violation in a callback path. Production-code change is conditional, ≤30 LOC, and surgical.
  - `argus/execution/order_manager.py::reconstruct_from_broker` BODY — the single-line `is_reconstructed = True` addition + AC3.6 zero-counter initialization landed at S4a-i; nothing further at S4a-ii (per AC3.7 + SbC §"Do NOT modify" #5 + A-class halt A12).
  - The DEF-199 A1 fix region.
  - The DEF-158 3-branch side-check inside `_check_flatten_pending_timeouts` (regression invariant 8 / A-class halt A5).
  - `argus/execution/ibkr_broker.py` — out-of-scope at S4a-ii.
  - `argus/execution/simulated_broker.py` — out-of-scope.
  - `argus/main.py` — A-class halt A12.
  - `argus/core/risk_manager.py` — out-of-scope at S4a-ii (the H-R3-3 Check 0 extension landed at S3b).
  - `argus/api/routes/positions.py` and `scripts/clear_position_halt.py` — landed at S3b.
  - The S3b Path #2 implementation (`_is_locate_rejection`, `_is_locate_suppressed`, `_handle_suppression_timeout_for_position`, the 4 emit-site exception handlers, the Branch 4 throttle).
  - The S4a-i ceiling implementation (`_reserve_pending_or_fail`, `_check_sell_ceiling` itself, the 3 callback-path mutation paths, the `_trail_flatten` guard, the watchdog auto-flip).
  - The frontend (`frontend/`, `argus/ui/`) — zero UI scope (regression invariant 12 / B-class halt B8).
  - The `workflow/` submodule (RULE-018).
  - The POLICY_TABLE — landed at S4a-i.

- Do NOT change:
  - DEC-117 atomic-bracket invariants (regression invariant 1 / A-class halt A10).
  - DEC-369 broker-confirmed reconciliation immunity (regression invariant 3 / A-class halt A8).
  - DEC-385 6-layer side-aware reconciliation (regression invariant 5).
  - DEC-386 4-layer OCA architecture (regression invariant 6).
  - DEC-388 alert observability (regression invariant 7) — POLICY_TABLE entry count remains at 14 (S4a-i landed the 14th).
  - The `# OCA-EXEMPT:` exemption mechanism (regression invariant 9).

- Do NOT add:
  - A new module under `argus/` for the AST scanner — keep the helper inside the test file or import from S4a-i's existing infrastructure.
  - Production-code refactors beyond the conditional ≤30 LOC fix path.
  - Tests for callback paths that don't actually mutate the bookkeeping counters — the FAI #11 exhaustiveness test catches new mutation sites; speculative tests for non-mutating paths are scope creep per RULE-007.
  - Reflective-call sub-tests beyond the 3 per Decision 3 / FAI #8 option (a). Operator decided option (a) over option (b); 3 sub-tests is the committed coverage.

- Do NOT cross-reference other session prompts. This prompt is standalone.

## Operator Choice (N/A this session)

S4a-ii does not require operator pre-check. The AST-scope-extension is committed via Tier 3 items A + B + Decision 3 (option (a)) + Round 3 H-R3-5.

## Canary Tests

Before making any changes, run the canary-test skill in `.claude/skills/canary-test.md` with these tests to confirm baseline behavior:

- `test_no_await_in_reserve_pending_or_fail_body` (S4a-i deliverable) — confirms S4a-i's reference AST guard pattern is alive.
- `test_reserve_pending_or_fail_race_observable_under_injection` (S4a-i deliverable) — confirms the mocked-await injection mechanism is sound.
- `test_concurrent_sell_emit_race_blocked_by_pending_reservation` (S4a-i C-1 race test) — confirms the existing canonical race coverage.

These set the "before" baseline for the after-implementation regression check.

## Test Targets

After implementation:

- Existing tests: all must still pass. Pytest baseline ≥ S4a-i baseline (regression invariant 10 / B-class halt B3). Vitest unchanged at 913 (regression invariant 12).
- New tests in `tests/execution/order_manager/test_def204_callback_atomicity.py` (NEW FILE — 7 effective tests + 1 FAI #11 exhaustiveness + 1 M-R3-4 helper-AST = 8 logical tests merging to ~7 effective per session-breakdown.md):

  1. `test_synchronous_update_invariant_on_on_fill_partial_fill_transfer` — AST-no-await scan asserts no `ast.Await` between `position.cumulative_pending_sell_shares -= filled_qty` and `position.cumulative_sold_shares += filled_qty`; mocked-await injection asserts the race IS observable under injection. (Merged with full-fill via parametrize × 2.)

  2. `test_synchronous_update_invariant_on_on_fill_full_fill_transfer` — same pattern, full-fill case (parametrize case of test 1).

  3. `test_synchronous_update_invariant_on_on_cancel_decrement` — AST scan + injection on `on_cancel` decrement path.

  4. `test_synchronous_update_invariant_on_on_reject_decrement` — AST scan + injection on `on_reject` decrement path.

  5. `test_synchronous_update_invariant_on_check_sell_ceiling_multi_attribute_read` — AST scan asserts no `ast.Await` between reading `pending` and reading `sold` and computing `pending + sold + requested`; injection test asserts torn-read race IS observable under injection.

  6. **(Decision 3 / FAI #8 option (a) sub-test 1)** `test_ast_scan_catches_kw_unpacking_for_is_stop_replacement_callsite` — synthetic call: `kw = {"is_stop_replacement": True}; om._check_sell_ceiling(..., **kw)`; AST scan flags as "potentially-overriding-default."

  7. **(Decision 3 / FAI #8 option (a) sub-test 2)** `test_ast_scan_catches_computed_value_flag_for_is_stop_replacement_callsite` — synthetic call: `flag = compute_flag(); om._check_sell_ceiling(..., is_stop_replacement=flag)`; AST scan flags as "potentially-overriding-default."

  8. **(Decision 3 / FAI #8 option (a) sub-test 3)** `test_ast_scan_catches_getattr_reflective_access_for_check_sell_ceiling` — synthetic call: `getattr(om, '_check_sell_ceiling')(..., is_stop_replacement=True)`; AST scan flags as "potentially-overriding-default."

  9. **(Round 3 H-R3-5 / FAI #11)** `test_bookkeeping_callsite_enumeration_exhaustive` — AST scan walks `OrderManager`'s source for `ast.AugAssign` nodes targeting `cumulative_pending_sell_shares` or `cumulative_sold_shares`; finds enclosing function names; asserts the set is a subset of FAI #9 protected callsite list. **Falsifies if a mutation site exists outside the expected list.**

  10. **(Round 3 M-R3-4)** `test_no_await_between_refresh_and_read_in_read_positions_post_refresh` — AST scan asserts `_read_positions_post_refresh` has exactly 1 `ast.Await` (the refresh_positions call), no awaits between refresh completion and cache read.

- **Optional 6th synchronous-update test** for `_on_order_status` — only if pre-flight grep confirms `_on_order_status` mutates `cumulative_pending_sell_shares` or `cumulative_sold_shares`. If it doesn't, the FAI #11 exhaustiveness test (test 9) is the structural defense for forward-compat.

- Test command (scoped per DEC-328, non-final session):

  ```
  python -m pytest tests/execution/order_manager/ -n auto -q
  ```

## Config Validation (N/A — no new YAML fields)

S4a-ii is test-only (preferred outcome) with conditional production-code surgery. No config changes.

## Marker Validation (N/A — no new pytest markers)

S4a-ii does not add pytest markers.

## Risky Batch Edit (N/A or staged)

S4a-ii is test-only in the preferred outcome. If static-analysis surfaces a production-code violation, the surgical fix (≤30 LOC, single function) is small enough to skip the staged-flow ceremony — but disclose the production-code change in close-out's "Static-Analysis Findings" section and confirm with operator before merging.

## Visual Review (N/A — backend-only)

S4a-ii is backend-only. Zero UI changes (regression invariant 12).

## Definition of Done

- [ ] `tests/execution/order_manager/test_def204_callback_atomicity.py` created with 8 logical tests merging to 7 effective + 1 FAI #11 exhaustiveness test + 1 M-R3-4 helper-AST test.
- [ ] All 5 (or 6 if `_on_order_status` qualifies) synchronous-update invariant tests passing.
- [ ] All 3 reflective-call sub-tests passing (Decision 3 / FAI #8 option (a)).
- [ ] FAI #11 exhaustiveness test passing — `cumulative_pending_sell_shares` / `cumulative_sold_shares` mutation sites are a subset of the protected callsite list.
- [ ] M-R3-4 helper-AST test passing — `_read_positions_post_refresh` has exactly 1 `ast.Await`.
- [ ] Static-Analysis Findings documented in close-out — preferred outcome zero production-code change; if any callback path failed the AST scan and was fixed at S4a-ii, document the fix in ≤30 LOC.
- [ ] All existing pytest still passing.
- [ ] Pre-existing flake count unchanged (regression invariant 11 / B-class halt B1).
- [ ] CI green per RULE-050.
- [ ] Close-out report written to file (DEC-330).
- [ ] **FAI #11 materialized in `falsifiable-assumption-inventory.md`** per D16 of `doc-update-checklist.md` — see Close-Out section below.
- [ ] **Mid-Sprint Tier 3 Review (M-R2-5) trigger metadata flagged in structured close-out JSON** — `mid_sprint_tier_3_required: true` (or equivalent metadata key per the close-out skill schema) so the work-journal recognizes M-R2-5 fires next, BEFORE S4b begins.
- [ ] Tier 2 review completed via @reviewer subagent.

## Regression Checklist (Session-Specific)

After implementation, verify each of these:

| Check | How to Verify |
|-------|---------------|
| `git diff HEAD~1 -- argus/execution/order_manager.py` returns empty in the preferred outcome; OR ≤30 LOC surgical fix at one specific callback path if static-analysis surfaced a violation | Manual diff inspection; close-out documents which case |
| `git diff HEAD~1 -- argus/main.py` returns empty | A-class halt A12 |
| `git diff HEAD~1 -- argus/execution/ibkr_broker.py` returns empty | Out-of-scope |
| `git diff HEAD~1 -- argus/execution/simulated_broker.py` returns empty | Out-of-scope |
| `git diff HEAD~1 -- argus/core/risk_manager.py` returns empty | Out-of-scope (S3b owned this) |
| `git diff HEAD~1 -- argus/api/routes/positions.py` returns empty | Out-of-scope (S3b owned this) |
| `git diff HEAD~1 -- frontend/` AND `argus/ui/` returns empty | Regression invariant 12 / B-class halt B8 |
| `git diff HEAD~1 -- argus/core/alert_auto_resolution.py` returns empty | POLICY_TABLE 14th entry was S4a-i's; S4a-ii doesn't touch |
| `python -c "import ast, inspect; from argus.execution.order_manager import OrderManager; src = inspect.getsource(OrderManager._reserve_pending_or_fail); awaits = [n for n in ast.walk(ast.parse(src)) if isinstance(n, ast.Await)]; print(len(awaits))"` returns `0` | S4a-i baseline (must still hold) |
| `python -c "import ast, inspect; from argus.execution.order_manager import OrderManager; src = inspect.getsource(OrderManager._read_positions_post_refresh); awaits = [n for n in ast.walk(ast.parse(src)) if isinstance(n, ast.Await)]; print(len(awaits))"` returns `1` | M-R3-4 / regression invariant 30 |
| Test count delta ≥ +7 effective new tests | Close-out reports actual delta |
| Pre-existing flake count unchanged | DEF-150, DEF-167, DEF-171, DEF-190, DEF-192 |

## Close-Out

After all work is complete, follow the close-out skill in `.claude/skills/close-out.md`.

The close-out report MUST include a structured JSON appendix at the end, fenced with ` ```json:structured-closeout `.

**Write the close-out report to a file** (DEC-330):

```
docs/sprints/sprint-31.92-def-204-round-2/session-s4a-ii-closeout.md
```

Do NOT just print the report in the terminal. Create the file, write the full report (including the structured JSON appendix) to it, and commit it.

### MANDATORY: Materialize FAI #11 per D16 of `doc-update-checklist.md`

After the close-out report is written and CI is green, materialize FAI #11 in `docs/sprints/sprint-31.92-def-204-round-2/falsifiable-assumption-inventory.md` per D16 of `docs/sprints/sprint-31.92-def-204-round-2/doc-update-checklist.md`:

1. Open `falsifiable-assumption-inventory.md`.
2. Append a new row to the main inventory table (entry #11) with the verbatim text from `round-3-disposition.md` § 6.2 (reproduced below). Update the inventory's preamble line `## Inventory (10 entries)` (post-D15) to `## Inventory (11 entries)`.
3. Mark the status field as `**falsified — green S4a-ii spike (commit: <SHA>)**` if `test_bookkeeping_callsite_enumeration_exhaustive` passed; otherwise document partial falsification with explicit rationale per FAI #11's resolution clause ("either add the discovered callsite to FAI #9's protection scope (preferred) OR document the coverage gap with explicit rationale").
4. Remove FAI #11's entry from the "Pending FAI extensions committed in `round-3-disposition.md`" subsection (since it has now been promoted into the main table). The pending-extensions subsection should be empty post-D16; remove the subsection itself OR leave it empty with a "Both pending FAI entries materialized; subsection retained for audit-trail history" note (operator preference).
5. Commit the doc change with message referencing D16 + the S4a-ii close-out commit SHA.

**Verbatim text for FAI #11 main-table row (per `round-3-disposition.md` § 6.2):**

> | 11 | All sites in `argus/execution/order_manager.py` that mutate `cumulative_pending_sell_shares` or `cumulative_sold_shares` are enumerated in the FAI #9 protected callsite list (`_reserve_pending_or_fail`, `on_fill`, `on_cancel`, `on_reject`, `_on_order_status`, plus `_check_sell_ceiling`'s multi-attribute read; plus `reconstruct_from_broker` for initialization). The L3 ceiling correctness depends on FAI #9's protection covering EVERY mutation site, not just the enumerated ones. | **Falsifying spike:** S4a-ii regression test `test_bookkeeping_callsite_enumeration_exhaustive` — AST scan walks `OrderManager`'s source for `ast.AugAssign` nodes targeting `cumulative_pending_sell_shares` or `cumulative_sold_shares`; finds the enclosing function name for each; asserts the set of enclosing functions is a subset of the expected callsite list. Falsifies if a mutation site exists outside the expected list (e.g., `_on_exec_details` if it exists in code). | **falsified — green S4a-ii spike (commit: \<SHA from S4a-ii close-out commit\>)**. Resolution if falsified: either add the discovered callsite to FAI #9's protection scope (preferred) or document the coverage gap with explicit rationale. |

### Mid-Sprint Tier 3 Review (M-R2-5) trigger

Per session-breakdown line ~1144 + escalation-criteria.md "Closing the Sprint" section, M-R2-5 fires AFTER S4a-ii close-out and BEFORE S4b/S5a/S5b/S5c begin. The close-out's structured JSON appendix MUST include a metadata key signaling this to the runner / work journal. Suggested key shape (adapt to whatever the close-out skill schema actually defines):

```json
{
  "mid_sprint_tier_3_required": true,
  "mid_sprint_tier_3_id": "M-R2-5",
  "mid_sprint_tier_3_scope": "Architectural closure of DEC-390's 4-layer structure post-S4a-ii. Cross-validation of pending-reservation pattern (H-R2-1 atomic method), ceiling guard at 5 standalone-SELL emit sites, callback-path synchronous-update invariant (Tier 3 items A + B / FAI #9), reflective-call AST coverage (Decision 3 / FAI #8 option (a)), bookkeeping-callsite enumeration exhaustiveness (FAI #11 / H-R3-5), and the C-R3-1 Fix A serialization closure (proportional re-review per round-3-disposition § 1.4)."
}
```

If the close-out skill schema does NOT include `mid_sprint_tier_3_required` as a recognized key, document the M-R2-5 trigger in prose at the top of the close-out file AND surface to operator before sealing the close-out — the runner needs an explicit signal to pause for M-R2-5 before S4b.

## Tier 2 Review (Mandatory — @reviewer Subagent)

After the close-out is written to file and committed, AND FAI #11 is materialized, AND the M-R2-5 trigger metadata is set, invoke the @reviewer subagent to perform the Tier 2 review within this same session.

Provide the @reviewer with:

1. The review context file: `docs/sprints/sprint-31.92-def-204-round-2/review-context.md`
2. The close-out report path: `docs/sprints/sprint-31.92-def-204-round-2/session-s4a-ii-closeout.md`
3. The diff range: `git diff HEAD~2..HEAD` (covers the implementation commit and the FAI #11 materialization commit; confirm exact range during review).
4. The test command: `python -m pytest tests/execution/order_manager/ -n auto -q` (scoped per DEC-328; non-final session).
5. Files that should NOT have been modified:
   - `argus/execution/order_manager.py` UNLESS static-analysis surfaced a violation; in which case ≤30 LOC surgical fix only, in the specific failing callback path.
   - `argus/main.py`
   - `argus/execution/ibkr_broker.py`
   - `argus/execution/simulated_broker.py`
   - `argus/core/risk_manager.py`
   - `argus/api/routes/positions.py`
   - `scripts/clear_position_halt.py`
   - `argus/core/alert_auto_resolution.py`
   - `argus/models/trading.py`
   - `argus/execution/alpaca_broker.py`
   - `argus/data/alpaca_data_service.py`
   - `frontend/`, `argus/ui/`
   - `workflow/` submodule

The @reviewer will produce its review report at:

```
docs/sprints/sprint-31.92-def-204-round-2/session-s4a-ii-review.md
```

The verdict JSON is fenced with ` ```json:structured-verdict `.

## Post-Review Fix Documentation

Same pattern as the implementation-prompt template — see template §"Post-Review Fix Documentation". If @reviewer reports CONCERNS and the findings are fixed within this session, append "Post-Review Fixes" to `session-s4a-ii-closeout.md` and "Post-Review Resolution" to `session-s4a-ii-review.md`. Update the verdict JSON to `CONCERNS_RESOLVED`. ESCALATE findings must NOT be fixed without human review.

## Session-Specific Review Focus (for @reviewer)

1. **AST guard soundness — the pair-wise pattern.** Each synchronous-update invariant test pairs an AST-no-await scan with a mocked-await injection check. The pair is what makes the guard SOUND: without injection, the AST scan could be passing because the function body is shaped differently than expected. Verify each of tests 1–5 has BOTH parts (AST scan AND injection assertion); a test with only one part is suspect.

2. **Reflective-call AST coverage scope (FAI #8 option (a)).** Verify tests 6–8 use synthetic SOURCE STRINGS fed into `ast.parse`, NOT attempts to instrument production code. The reflective-call sub-tests are checking the AST SCANNER'S coverage, not asserting that production code uses these patterns (production code should NOT use them; the test is the structural defense against future drift).

3. **FAI #11 exhaustiveness scope.** Verify test 9 walks `OrderManager`'s ENTIRE source (`inspect.getsource(OrderManager)`), not just specific functions. The point is to catch a NEW mutation site that's added in a future sprint without updating the FAI #9 protected list. Verify the `PROTECTED_CALLSITES` set in the test matches FAI #9's enumerated list exactly (`_reserve_pending_or_fail`, `on_fill`, `on_cancel`, `on_reject`, `_on_order_status`, `_check_sell_ceiling`, `reconstruct_from_broker`).

4. **M-R3-4 helper-AST test correctness.** Verify test 10 asserts EXACTLY 1 `ast.Await` in `_read_positions_post_refresh`. If the helper has been refactored to inline the refresh-then-read sequence at multiple call sites, the helper itself may have been removed — in which case the test should be removed or refactored to scan the inlined call sites. Document such drift in close-out's RULE-038 section.

5. **Static-analysis findings disclosure.** The close-out's "Static-Analysis Findings" section is the structural defense against silent production-code drift. Verify the close-out documents:
   - Each callback path inspected.
   - Pass/fail for each.
   - If any failure: the surgical fix landed in this session (≤30 LOC, single function).
   - The total production-code LOC change (target: 0; max: ≤30 — anything more is scope creep).

6. **`except Exception:` pattern check (RULE-043).** AST guard tests can be subtle — verify NO test catches `Exception` broadly in a way that could mask `pytest.fail` or assertion errors. Each test's exception handling should be narrow (specific exception types only).

7. **`Test*` class collection check (RULE-046).** If the AST helpers are organized into classes (e.g., a `Test*Visitor` AST visitor), verify they have `__test__ = False` so pytest doesn't try to collect them as test classes. The synchronous-update invariant tests themselves are functions, not classes, per the existing `tests/execution/order_manager/` style — verify alignment.

8. **FAI #11 materialization timing.** Verify the doc commit happened AFTER the implementation commit AND only when the regression test was green. Verify `falsifiable-assumption-inventory.md`'s preamble updated `10 entries` → `11 entries`. Verify the pending-FAI-#11 subsection had FAI #11 removed (FAI #10 should also have been removed at S3b close).

9. **M-R2-5 trigger metadata.** Verify the structured close-out JSON includes the M-R2-5 trigger metadata (or prose-form fallback if the schema doesn't accommodate the key). The runner / work-journal needs this signal to pause for M-R2-5 before S4b.

## Sprint-Level Regression Checklist (for @reviewer)

The full Sprint-Level Regression Checklist is in `docs/sprints/sprint-31.92-def-204-round-2/regression-checklist.md`.

Of particular relevance to S4a-ii (✓-mandatory at S4a-ii per the Per-Session Verification Matrix):

- **Invariant 10 (test count baseline holds):** PASS — test count ≥ S4a-i baseline; +7 effective new tests.
- **Invariant 11 (pre-existing flake count):** PASS — DEF-150/167/171/190/192.
- **Invariant 12 (frontend immutability):** PASS — zero UI scope.
- **Invariant 13 (SELL-volume ceiling pending+sold pattern):** EXTENDED — synchronous-update invariant scope now covers all 5 bookkeeping callback paths.
- **Invariant 20 (Pending-reservation state transitions):** EXTENDED — AST regression infrastructure validates all 5 transitions structurally.
- **Invariant 23 (NEW per Tier 3 item A + B + Decision 3 — synchronous-update invariant on all bookkeeping callback paths + reflective-pattern AST):** ESTABLISHES — this is the session's primary deliverable. Verify:
  - 5 synchronous-update invariant tests covering `on_fill`, `on_cancel`, `on_reject`, `_on_order_status` (if it qualifies), `_check_sell_ceiling` multi-attribute read.
  - 3 reflective-call sub-tests covering `**kw` unpacking, computed-value flag, `getattr` reflective access.
  - DEF-FAI-CALLBACK-ATOMICITY (Tier 3 verdict; sprint-gating Round 3 advancement) — closure requires invariant 23 active and green.
  - DEF-FAI-8-OPTION-A (Tier 3 verdict; Sprint 31.92 S4a-ii) — closure requires the 3 reflective-pattern sub-tests active and green.
- **Invariant 29 (NEW per Round 3 H-R3-5 — bookkeeping callsite-enumeration AST exhaustiveness):** ESTABLISHES — `test_bookkeeping_callsite_enumeration_exhaustive` walks `ast.AugAssign` and asserts subset of FAI #9 protected list.
- **Invariant 30 (NEW per Round 3 M-R3-4 — `_read_positions_post_refresh` helper AST scan):** ESTABLISHES — `test_no_await_between_refresh_and_read_in_read_positions_post_refresh` confirms exactly 1 `ast.Await` in helper body.

## Sprint-Level Escalation Criteria (for @reviewer)

The full Sprint-Level Escalation Criteria are in `docs/sprints/sprint-31.92-def-204-round-2/escalation-criteria.md`.

### A. Mandatory Halts (Tier 3 architectural review automatically fires)

Of particular relevance to S4a-ii:

- **A6** (Tier 2 review verdict CONCERNS or ESCALATE). Halt; iterate within session for CONCERNS; operator decides for ESCALATE.
- **A11** (AC4 SELL-volume ceiling false-positive in production paper trading). The S4a-ii AST regression infrastructure is the structural defense for the callback-path leak class; if production exhibits a leak that the regression infrastructure should have caught, A11's option (e) routes to S4a-ii diagnostic — verify the AST scanner doesn't have a false-negative path.
- **A12** (any session's diff touches `argus/main.py` or `reconstruct_from_broker` BODY beyond the single-line addition). S4a-ii's `argus/main.py` and `reconstruct_from_broker` BODY scope is ZERO — A12 fires on any modification.
- **A14** (Round 3 verdict produces ≥1 Critical finding). Already invoked operator override; S4a-ii is part of the in-sprint mitigation path.
- **A17** (NEW per Tier 3 item A — synchronous-update invariant violation in production paper trading): the S4a-ii regression infrastructure is the in-process structural defense. If a callback-path leak surfaces post-merge, A17 fires; Tier 3 evaluates whether the AST scanner has a false-negative path (option (a)) — extend the AST scan + reflective-pattern coverage to the surfacing path.

### B. Mandatory Halts (Tier 3 not required; operator + Tier 2 reviewer disposition)

- **B1** (pre-existing flake count increases). Per RULE-041, file DEF entry on first observation.
- **B3** (pytest baseline drops below S4a-i baseline). Halt; investigate.
- **B4** (CI fails on session's final commit AND failure is NOT a documented pre-existing flake). Halt per RULE-050.
- **B5** (structural anchor referenced in impl prompt does not match repo state during pre-flight). Re-anchor against actual structural anchors. Disclose under RULE-038.
- **B6** (a do-not-modify-list file appears in `git diff`). Revert. Particularly relevant given the conditional-production-code-modification clause: the conditional fix is allowed ONLY in the specific callback path that failed AST scan; touching anything else fires B6.
- **B7** (test runtime degrades >2× from baseline OR a single test exceeds 60s). The AST tests are pure-Python static analysis and should be sub-second; the mocked-await injection tests may have async overhead but should still finish in <5s each.
- **B8** (frontend modification — zero scope). Revert.

### C. Soft Halts (Continue with extra caution + close-out flag)

- **C1** (out-of-scope improvements). Document in close-out under "Deferred Items"; do NOT fix in this session.
- **C5** (uncertain whether a change crosses do-not-modify boundary). Pause; consult SbC; escalate to operator before making the change. The conditional-production-code clause is a narrow exception; broader changes require explicit approval.
- **C6** (line numbers drift 1–5 from spec). Continue; document actual line numbers in close-out.

### Sprint Abort Conditions (especially relevant to S4a-ii)

- **#8 (NEW per Tier 3 verdict — FAI self-falsifiability triggered fourth time):** If the FAI #11 exhaustiveness test surfaces a NEW mutation site that's outside the FAI #9 protected list, this is the FOURTH FAI miss within Sprint 31.92's planning cycle (asyncio yield-gap, ib_async cache freshness, callback-path bookkeeping atomicity, this fourth). Per Decision 7, the operator-override pre-commitment routes this to RSK-and-ship if the resolution is to add the discovered callsite to FAI #9's protection scope (preferred); the routing depends on whether the discovered site is structurally distinct (would require Phase A re-entry) or is a near-sibling of FAI #9 (RSK-and-document with the protected-list extension). Default disposition per FAI #11's resolution clause: add to PROTECTED_CALLSITES (preferred). Surface to operator before applying.

---

*End Sprint 31.92 Session S4a-ii implementation prompt.*

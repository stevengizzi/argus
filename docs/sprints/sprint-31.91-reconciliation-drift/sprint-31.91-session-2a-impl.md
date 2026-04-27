# Sprint 31.91, Session 2a: Reconciliation Contract Refactor + Typed ReconciliationPosition

> **Track:** Side-Aware Reconciliation Contract (Sessions 2a → 2b.1 → 2b.2 → 2c.1 → 2c.2 → 2d).
> **Position in track:** First session. Lays the typed contract; subsequent sessions consume it.

## Pre-Flight Checks

Before making any changes:

1. **Read `.claude/rules/universal.md` in full and treat its contents as binding for this session.** RULE-038 (grep-verify discipline), RULE-050 (CI green), RULE-019 (test-count must not decrease), and RULE-007 (out-of-scope discoveries) all apply.

2. Read these files to load context:
   - `argus/execution/order_manager.py:124` — area for the new dataclass insertion (verify line; may have drifted)
   - `argus/execution/order_manager.py` — current `reconcile_positions` signature and orphan loop body (`grep -n "reconcile_positions\|orphan" argus/execution/order_manager.py`)
   - `argus/main.py:1505-1535` — current call site that builds the broker-positions dict and invokes `reconcile_positions` (verify line range; may have drifted)
   - `argus/models/trading.py:153-173` — `Position` dataclass with `side` field (do-not-modify; consume only)
   - `argus/execution/ibkr_broker.py:935-946` — `get_positions()` returning `list[Position]` with side populated
   - `docs/sprints/sprint-31.91-reconciliation-drift/sprint-spec.md` — D5 acceptance criteria (Session 2a portion)
   - `docs/sprints/sprint-31.91-reconciliation-drift/spec-by-contradiction.md` — Do NOT add `broker_side` to `Position`; consume the EXISTING `side` field
   - `docs/sprints/sprint-31.91-reconciliation-drift/PHASE-A-REVISIT-FINDINGS.md` §A3 Row #3 — `main.py:1505-1535` is the correct call site (formerly `:1412`, drifted)
   - Existing reconciliation tests (`grep -rn "reconcile_positions" tests/`)

3. Run the full test baseline (DEC-328 — Session 2a is post-Tier-3 #1; full suite is appropriate at sprint re-entry):

   ```
   python -m pytest --ignore=tests/test_main.py -n auto -q
   python -m pytest tests/test_main.py -q
   ```

   Expected: ≥ 5,108 passing on the main suite (sprint baseline 5,080 + Sessions 0/1a/1b/1c new tests). Expected: 39 pass + 5 skip on `tests/test_main.py`. Cite both counts in the close-out.

4. Verify you are on the correct branch: **`main`**.

5. Verify Tier 3 #1 architectural review #1 has CLEARED. The session-breakdown explicitly gates Session 2a behind a Tier 3 CLEAR verdict on Sessions 0+1a+1b+1c. If the verdict is CONCERNS or ESCALATE, halt; do NOT begin Session 2a until operator dispositions.

6. **Pre-flight grep — verify the call site has not drifted further:**

   ```bash
   grep -n "reconcile_positions" argus/main.py
   grep -n "broker_pos_list = await self._broker.get_positions" argus/main.py
   ```

   The call site should match the `:1505-1535` range from the spec. If drifted by > 5 lines (per RULE-038), halt and reconcile; the prompt's line references are guides, not absolutes, but a drift > 5 lines indicates the call site has been substantially refactored and the spec needs operator review.

7. **Pre-flight grep — verify `Position.side` is populated by IBKRBroker:**

   ```bash
   grep -n -A 5 "def get_positions" argus/execution/ibkr_broker.py
   ```

   Confirm `Position(... side=OrderSide.BUY/SELL ...)` is assembled correctly inside `get_positions()`. If `side` is missing, halt — this entire sprint depends on `Position.side` being authoritative from the broker layer (per IMPROMPTU-04 already-shipped fix).

## Objective

Refactor the reconciliation contract from a side-stripped `dict[str, float]` (`{symbol: shares}`) to a typed `dict[str, ReconciliationPosition]` (`{symbol: ReconciliationPosition(symbol, side, shares)}`). The current contract is the structural cause of DEF-204 — by stripping the broker's side information at the type boundary, every downstream reconciliation read is forced to assume long-only, which produces phantom-short blindness.

Session 2a does ONLY the contract refactor and the end-to-end information-flow change. The orphan-loop branch detection (broker-orphan SHORT → `phantom_short` alert) lands in Session 2b.1; the side-aware reads at the four count-filter sites land in Session 2b.2. After Session 2a lands, the typed contract is wired through but the existing ARGUS-orphan branch is unchanged in behavior.

This session is structurally low-risk (a type/contract change with a 1:1 information mapping) but has high coupling — every reconciliation test fixture changes shape. The risk is in the mock fixtures, not in the production code.

## Requirements

1. **Create the `ReconciliationPosition` frozen dataclass** at `argus/execution/order_manager.py:~124` (place it near the existing module-level dataclass declarations; verify the right neighborhood by inspection):

   ```python
   from dataclasses import dataclass

   @dataclass(frozen=True)
   class ReconciliationPosition:
       """Typed broker-position contract for reconciliation. Frozen to
       prevent mutation in transit between main.py call site and
       order_manager.reconcile_positions.

       Sprint 31.91 (DEC-385 reserved): replaces the side-stripped
       `dict[str, float]` contract that was the structural cause of
       DEF-204 (phantom-short blindness).
       """
       symbol: str
       side: "OrderSide"  # forward ref; OrderSide imported above this dataclass
       shares: int

       def __post_init__(self) -> None:
           # Defensive: shares must be positive (the broker reports the
           # absolute size; direction is in `side`).
           if self.shares <= 0:
               raise ValueError(
                   f"ReconciliationPosition.shares must be positive; got {self.shares} for {self.symbol}"
               )
           if self.side is None:
               raise ValueError(
                   f"ReconciliationPosition.side must be set; got None for {self.symbol}"
               )
   ```

   Notes:
   - The defensive `__post_init__` checks are required (per spec). They make `side=None` a fail-closed condition, which Test 5 verifies.
   - Use `OrderSide` from wherever the existing module imports it (typically `argus.models.trading` or `argus.core.events`); do NOT re-import from a new location.
   - Frozen ensures the dataclass cannot be mutated downstream, which means any fix that wants to "patch up" a missing `side` field is structurally prevented from doing so silently.

2. **Modify `reconcile_positions` signature and body in `argus/execution/order_manager.py`:**

   - Old signature:
     ```python
     async def reconcile_positions(
         self, broker_positions: dict[str, float]
     ) -> None:
     ```
   - New signature:
     ```python
     async def reconcile_positions(
         self, broker_positions: dict[str, ReconciliationPosition]
     ) -> None:
     ```

   - **Body change scope:** Confined to the type plumbing. Wherever the body previously read `broker_positions[symbol]` as a float (the shares), it now reads `broker_positions[symbol].shares`. Wherever a future session needs the side, it will read `broker_positions[symbol].side` — but Session 2a does NOT add new side-aware logic; the existing ARGUS-orphan branch behavior must be preserved end-to-end (Test 4 verifies).

   - **Existing ARGUS-orphan loop body (`order_manager.py:3038-3039` area):** untouched in Session 2a. Session 2b.1 extends it with the broker-orphan branch.

   - **Existing reconciliation timing-window code:** untouched.

   - **DEC-369 / DEC-370 broker-confirmed immunity:** untouched. Tier 2 review will confirm zero behavioral change to those paths.

3. **Update the call site at `argus/main.py:1505-1535`:**

   The current code (per Phase A revisit):
   ```python
   broker_pos_list = await self._broker.get_positions()
   broker_positions: dict[str, float] = {}
   for pos in broker_pos_list:
       symbol = getattr(pos, "symbol", "")
       qty = float(getattr(pos, "shares", 0))
       if symbol and qty != 0:
           broker_positions[symbol] = qty

   await self._order_manager.reconcile_positions(broker_positions)
   ```

   New code:
   ```python
   broker_pos_list = await self._broker.get_positions()
   broker_positions: dict[str, ReconciliationPosition] = {}
   for pos in broker_pos_list:
       symbol = getattr(pos, "symbol", "")
       shares = int(abs(getattr(pos, "shares", 0)))  # broker may report negative for shorts; ReconciliationPosition takes absolute size
       side = getattr(pos, "side", None)
       if not symbol or shares == 0:
           continue
       if side is None:
           # Fail-closed: a position without a side cannot be safely reconciled.
           # Log CRITICAL and skip; the orphan loop will detect via separate
           # mechanisms in Session 2b.1.
           self._logger.critical(
               "Reconciliation skipped %s: broker Position missing side attribute. "
               "This indicates a broker-layer bug or a Position object constructed "
               "without side. Sprint 31.91 (DEF-204 mechanism) hardens against this.",
               symbol,
           )
           continue
       broker_positions[symbol] = ReconciliationPosition(
           symbol=symbol, side=side, shares=shares
       )

   await self._order_manager.reconcile_positions(broker_positions)
   ```

   Notes:
   - The `int(abs(...))` conversion handles brokers that report negative shares for shorts. `Position.shares` itself may be positive-with-side or signed; the conversion is defensive against either.
   - The `side is None` skip is the fail-closed path covered by Test 5. Per RULE-038 spirit, fail-closed > fail-open for safety-critical reconciliation.
   - The `import` for `ReconciliationPosition` at the top of `main.py`: add `from argus.execution.order_manager import ReconciliationPosition` (or whichever import path matches the project's existing pattern).

4. **No behavioral change to the existing ARGUS-orphan branch.** Test 4 verifies this: the existing orphan-detection logic (ARGUS has `_managed_positions[symbol]` but broker reports zero) must produce the same outputs (logs, alerts if any, state transitions) before and after the contract change.

5. **Update test fixtures.** Existing tests that call `reconcile_positions(some_dict)` need their fixtures updated. Per RULE-019, do NOT delete or skip any existing test; update the fixture and assertion shape to match the new contract:

   - `dict[str, float]` → `dict[str, ReconciliationPosition]`
   - Where the test previously did `{"AAPL": 100.0}`, now does `{"AAPL": ReconciliationPosition(symbol="AAPL", side=OrderSide.BUY, shares=100)}`
   - For tests that don't care about side (most of them, since the existing logic was side-blind), use `side=OrderSide.BUY` as the canonical default.

   The expected number of mock updates is ~3, but verify by exhaustive grep:
   ```bash
   grep -rn "reconcile_positions" tests/ | grep -v "\.pyc"
   ```

6. **DEC-369 broker-confirmed immunity preserved.** Inspect: any code path that auto-closes `_broker_confirmed=True` positions remains unchanged. Run pre-existing tests on broker-confirmed reconciliation immunity.

7. **No edits to do-not-modify regions.** Specifically:
   - `argus/execution/order_manager.py:1670-1750` (DEF-199 A1 fix) — zero edits
   - `argus/main.py` startup invariant region — zero edits. **Scoped exception (per invariant 15):** Session 2a's edit is confined to lines `:1505-1535` (the reconciliation call site); the startup invariant region (`check_startup_position_invariant()`, IMPROMPTU-04 fix) is BELOW or ABOVE this range and must not be touched. Verify with `git diff argus/main.py` showing only the call-site delta.
   - `argus/models/trading.py` Position class (lines 153-173) — zero edits. Consume `Position.side` only; do NOT add a `broker_side` field (explicit non-goal per spec-by-contradiction).
   - `argus/execution/alpaca_broker.py`, `argus/data/alpaca_data_service.py`, `argus/execution/ibkr_broker.py`, `argus/execution/broker.py`, `docs/sprints/sprint-31.9/IMPROMPTU-04-closeout.md`, `workflow/` — zero edits.
   - `argus/core/risk_manager.py` — zero edits in Session 2a (Session 2b.2 modifies it; Session 2a does not).

## Tests (~5 new + ~3 mock updates)

1. **`test_reconciliation_position_dataclass_frozen_round_trip`**
   - Construct a `ReconciliationPosition(symbol="AAPL", side=OrderSide.BUY, shares=100)`.
   - Assert: attempting `rp.shares = 200` raises `FrozenInstanceError` (or `dataclasses.FrozenInstanceError`).
   - Assert: `__post_init__` rejects `shares=0` (raises `ValueError`).
   - Assert: `__post_init__` rejects `shares=-100` (raises `ValueError`).
   - Assert: `__post_init__` rejects `side=None` (raises `ValueError`).

2. **`test_reconcile_positions_signature_typed_dict`**
   - Construct a `{"AAPL": ReconciliationPosition(...)}` dict and call `reconcile_positions(broker_positions=...)`.
   - Assert: no exceptions, return value is `None` (or whatever the existing signature returns), no AttributeError on `.shares`/`.side` access.
   - Negative case: passing `{"AAPL": 100.0}` (the OLD contract) raises a TypeError (mypy/runtime — ReconciliationPosition's `__post_init__` won't fire because the float isn't being constructed; instead the body's `.shares` access raises AttributeError). This is the structural enforcement that the contract is migrated.

3. **`test_main_call_site_builds_typed_dict_from_broker_positions`**
   - Mock `self._broker.get_positions()` to return `[Position(symbol="AAPL", side=OrderSide.BUY, shares=100), Position(symbol="MSFT", side=OrderSide.SELL, shares=50)]`.
   - Trigger the reconciliation call site (the periodic reconciliation tick or whatever wraps it).
   - Assert: `_order_manager.reconcile_positions` is called once with a dict whose values are all `ReconciliationPosition` instances.
   - Assert: the AAPL entry has `side=OrderSide.BUY, shares=100`; the MSFT entry has `side=OrderSide.SELL, shares=50`.

4. **`test_argus_orphan_branch_unchanged_with_typed_contract`** (the regression-protection test)
   - Setup: `_managed_positions[AAPL]` exists (ARGUS thinks it has 100 shares of AAPL); broker reports zero positions for AAPL (via empty `broker_positions` dict).
   - Call `reconcile_positions({})` (an empty typed dict — note the new contract).
   - Assert: existing orphan-detection logic fires the same log lines / state transitions as before Session 2a's refactor. (Use a snapshot test or capture log output and compare against a fixture.)
   - This is the critical anti-regression test: contract change must not silently change the orphan-loop body.

5. **`test_reconcile_positions_with_pos_missing_side_attribute_fails_closed`**
   - Mock `self._broker.get_positions()` to return a `Position` object whose `side` is `None` (or not present).
   - Trigger the call site.
   - Assert: the symbol is SKIPPED at the call site (no `ReconciliationPosition` constructed for it); a CRITICAL log line is emitted naming the symbol.
   - Assert: `_order_manager.reconcile_positions` is called with the dict NOT containing that symbol.
   - Assert: no exception bubbles up to crash the reconciliation loop — partial positions are skipped, others continue.

6. **(MOCK UPDATE)** Update the ~3 existing test fixtures that pass `dict[str, float]` to `reconcile_positions`. They must be updated to construct `dict[str, ReconciliationPosition]`. Per RULE-019, no test is deleted or skipped. The fixture update is mechanical.

   ```bash
   # exhaustively find affected tests
   grep -rn "reconcile_positions" tests/ | grep -v "\.pyc" | grep -v "test_reconciliation_position_dataclass"
   ```

## Definition of Done

- [ ] `ReconciliationPosition` frozen dataclass declared at `order_manager.py:~124` with `__post_init__` defensive checks.
- [ ] `reconcile_positions` signature accepts `dict[str, ReconciliationPosition]`.
- [ ] `main.py:1505-1535` call site builds the typed dict from broker positions; fail-closed on `side=None`.
- [ ] Existing ARGUS-orphan branch behavior preserved (Test 4 passes).
- [ ] DEC-369 / DEC-370 broker-confirmed immunity unchanged.
- [ ] 5 new tests + ~3 mock fixture updates; all passing.
- [ ] CI green; full pytest baseline ≥ 5,113 (5,108 entry baseline + 5 new tests).
- [ ] `tests/test_main.py` baseline holds at 39 pass + 5 skip (Session 2a touches `main.py`; explicit verification per invariant 6).
- [ ] All do-not-modify list items show zero `git diff`.
- [ ] Tier 2 review (backend safety reviewer) verdict CLEAR.
- [ ] Close-out report at `docs/sprints/sprint-31.91-reconciliation-drift/session-2a-closeout.md`.

## Close-Out Report

Write `docs/sprints/sprint-31.91-reconciliation-drift/session-2a-closeout.md` containing:

1. **Files modified** — exact paths + line ranges. Specifically: `order_manager.py` (~:124 dataclass + signature change + body type plumbing), `main.py:1505-1535` (call-site rewrite), test files + ~3 mock updates.
2. **Tests added** — 5 entries with one-line "what does each protect" notes.
3. **`git diff --stat`** output snippet.
4. **Test evidence** —
   - Full suite: `python -m pytest --ignore=tests/test_main.py -n auto -q` → expected ≥ 5,113 passing.
   - test_main.py: `python -m pytest tests/test_main.py -q` → expected 39 pass + 5 skip.
5. **Do-not-modify audit** — `git diff` excerpts proving:
   - `order_manager.py:1670-1750` (DEF-199 A1) zero edits
   - `main.py` startup invariant region zero edits (only `:1505-1535` shows the scoped delta)
   - `models/trading.py:153-173` zero edits
   - `risk_manager.py` zero edits (Session 2b.2 modifies; Session 2a does not)
   - All other do-not-modify entries clean
6. **Discovered Edge Cases** — note any. Common cases: tests that mock broker positions in shapes other than `list[Position]` (legacy fixtures); subtle type narrowing on `int` vs `float` for `shares`. If empty, write "None."
7. **Deferred Items (RULE-007)** — bugs/improvements outside scope; if empty, write "None."
8. **Verdict JSON block:**

   ```json
   {
     "session": "2a",
     "verdict": "PROPOSED_CLEAR",
     "tests_added": 5,
     "mock_updates": <fill>,
     "tests_total_after": <fill>,
     "test_main_py_count": "39 pass + 5 skip",
     "files_modified": [
       "argus/execution/order_manager.py",
       "argus/main.py",
       "<test files>"
     ],
     "donotmodify_violations": 0,
     "tier_3_track": "side-aware-reconciliation"
   }
   ```

## Tier 2 Review Invocation

After the close-out is written and committed, invoke the @reviewer subagent.

Provide the @reviewer with:
1. Review context: `docs/sprints/sprint-31.91-reconciliation-drift/review-context.md`
2. Close-out path: `docs/sprints/sprint-31.91-reconciliation-drift/session-2a-closeout.md`
3. Diff range: `git diff HEAD~1`
4. Test commands:
   - Full: `python -m pytest --ignore=tests/test_main.py -n auto -q`
   - test_main.py: `python -m pytest tests/test_main.py -q`
5. Files that should NOT have been modified (explicit `git diff` audit list):
   - `argus/execution/order_manager.py:1670-1750`
   - `argus/main.py` startup invariant region (only `:1505-1535` permitted; verify by reading the diff)
   - `argus/models/trading.py:153-173`
   - `argus/execution/alpaca_broker.py`
   - `argus/data/alpaca_data_service.py`
   - `argus/execution/ibkr_broker.py`
   - `argus/execution/broker.py`
   - `argus/core/risk_manager.py` (Session 2b.2 modifies; not 2a)
   - `argus/core/health.py`
   - `docs/sprints/sprint-31.9/IMPROMPTU-04-closeout.md`
   - `workflow/` submodule

The @reviewer must use the **backend safety reviewer** template (`templates/review-prompt.md`).

The @reviewer produces its review at `docs/sprints/sprint-31.91-reconciliation-drift/session-2a-review.md`.

## Post-Review Fix Documentation

Same pattern as prior sessions. CONCERNS-with-fix → append "Post-Review Fixes" + "Post-Review Resolution"; verdict JSON → `CONCERNS_RESOLVED`. ESCALATE → halt; operator dispositioning required.

## Session-Specific Review Focus (for @reviewer)

1. **Information end-to-end.** Verify by reading the diff that `Position.side` flows: broker returns `Position(side=BUY)` → call site at `main.py:1505-1535` reads `pos.side` → builds `ReconciliationPosition(side=...)` → `reconcile_positions()` body reads `broker_positions[sym].side`. The information must not be silently dropped at any junction.
2. **Frozen dataclass immutability.** The `@dataclass(frozen=True)` decorator must be present and the test must verify mutation raises. A bare `@dataclass` would compile but allow mutation, which silently defeats the structural protection.
3. **Defensive fail-closed when `side=None`.** Test 5 (`fails_closed`) is the verification. Reviewer reads the call site code and confirms the `if side is None:` block logs CRITICAL and `continue`s — does NOT fabricate a default side.
4. **Existing ARGUS-orphan branch behavior preserved.** Test 4 must pass. Reviewer additionally inspects the orphan loop body diff to confirm no logic change beyond the type plumbing (`broker_positions[sym]` → `broker_positions[sym].shares`).
5. **`main.py` edit scope.** Verify `git diff argus/main.py` shows changes ONLY in the `:1505-1535` range. Per invariant 9, the startup invariant region (`check_startup_position_invariant()`) must show zero edits. The IMPROMPTU-04 fix is sacrosanct.
6. **Mock fixture updates are mechanical, not behavioral.** Each updated fixture changes shape but not test intent. Reviewer should diff each fixture and confirm the assertions are equivalent (modulo the new dataclass type).
7. **Risk Manager Check 0 (`share_count <= 0` rejection) unchanged.** Per invariant 8, Risk Manager Check 0 logic must be untouched. Session 2a does not modify `risk_manager.py` at all; reviewer confirms zero edits to that file.

## Sprint-Level Regression Checklist (for @reviewer)

The full Sprint-Level Regression Checklist is in `docs/sprints/sprint-31.91-reconciliation-drift/review-context.md`. Of particular relevance to Session 2a:

- **Invariant 5 (5,080 pytest baseline holds):** PASS — expected ≥ 5,113 after Session 2a.
- **Invariant 6 (`tests/test_main.py` 39+5):** PASS — Session 2a edits `main.py`, so this invariant is at maximum risk in this session.
- **Invariant 8 (Risk Manager Check 0 unchanged):** PASS — `risk_manager.py` zero edits.
- **Invariant 9 (IMPROMPTU-04 startup invariant unchanged):** PASS — verify `main.py` diff is confined to `:1505-1535`.
- **Invariant 14 (Monotonic-safety property):** Row "After Session 2a" — OCA bracket = YES, OCA standalone (4) = YES, Broker-only safety = YES, Restart safety = YES, Recon detects shorts = NO (typed only — typed contract enables 2b.1's branch but 2a alone does not detect shorts).
- **Invariant 15 (do-not-modify list untouched):** PASS — verify the explicit list above. The scoped exception for `main.py:1505-1535` is documented.

## Sprint-Level Escalation Criteria (for @reviewer)

- **A2** (Tier 2 CONCERNS or ESCALATE).
- **B1, B3, B4, B5, B6** — standard halt conditions. B5 (line drift > 5 lines) most likely if the call site has continued to drift since DISCOVERY captured `:1505-1535`.
- **C5** (uncertain whether a change crosses a do-not-modify boundary) — `main.py` edit scope is the highest-risk site for this session.
- **C7** (existing test fails after fixture update) — if a mock-update test fails for a behavioral reason rather than the type change, that's an out-of-scope discovery; halt and escalate per RULE-007.

---

*End Sprint 31.91 Session 2a implementation prompt.*

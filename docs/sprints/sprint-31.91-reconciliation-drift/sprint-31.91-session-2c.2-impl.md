# Sprint 31.91, Session 2c.2: Clear-Threshold + Auto-Clear (Default 5 Cycles, M4 Disposition)

> **Track:** Side-Aware Reconciliation Contract (Sessions 2a → 2b.1 → 2b.2 → 2c.1 → **2c.2** → 2d).
> **Position in track:** Fifth session. Adds the auto-clear logic for the per-symbol entry gate Session 2c.1 engaged.

## Pre-Flight Checks

Before making any changes:

1. **Read `.claude/rules/universal.md` in full.** RULE-038, RULE-050, RULE-019, RULE-007.

2. Read these files to load context:
   - `argus/execution/order_manager.py` — Session 2c.1's gate state (`_phantom_short_gated_symbols`) and the gate-engagement code in `_handle_broker_orphan_short`
   - `argus/core/config.py:229` — `ReconciliationConfig` (where new field `broker_orphan_consecutive_clear_threshold` goes)
   - DEC-370 reference — existing `_reconciliation_miss_count` pattern (the M4 5-cycle threshold mirrors this pattern; verify the existing usage via `grep -n "_reconciliation_miss_count\|miss_count" argus/`)
   - `docs/sprints/sprint-31.91-reconciliation-drift/sprint-spec.md` — D5 (Session 2c.2 portion)
   - Session 2c.1's `_remove_gated_symbol_from_db()` stub (Session 2c.2 fully implements the auto-clear path)

3. Run scoped tests:

   ```
   python -m pytest tests/execution/ -n auto -q
   ```

4. Verify branch: **`main`**.

5. Verify Sessions 2a/2b.1/2b.2/2c.1 deliverables on `main`:

   ```bash
   grep -n "_phantom_short_gated_symbols" argus/execution/order_manager.py
   grep -n "phantom_short_gated_symbols" argus/main.py  # rehydration call
   grep -n "broker_orphan_entry_gate_enabled" argus/core/config.py
   ```

6. **Pre-flight grep — verify the reconciliation cycle entry point** (where the broker-orphan branch and ARGUS-orphan branch are dispatched). Session 2c.2 adds a new tracking dict (`_phantom_short_clear_cycles`) and decrement-on-broker-zero logic that runs every reconciliation cycle.

   ```bash
   grep -n "for symbol, recon_pos in broker_positions" argus/execution/order_manager.py
   grep -n "resolved_symbols" argus/execution/order_manager.py
   ```

   Confirm the orphan-loop body's broker-zero cleanup section (added in 2b.1) is the right neighborhood for the auto-clear logic.

## Objective

The per-symbol entry gate (Session 2c.1) blocks new entries on a symbol once `phantom_short` is detected. Without an auto-clear path, the gate would remain engaged indefinitely, even after operator intervention resolves the underlying phantom short. Session 2c.2 adds:

- A consecutive-cycle counter `_phantom_short_clear_cycles: dict[str, int]` that increments each reconciliation cycle that observes broker-zero shares for the gated symbol.
- An auto-clear threshold (default 5 cycles per M4 disposition; was 3 in earlier drafts) — when the counter reaches 5, the gate clears for that symbol.
- A counter reset on re-detection (preventing a "stuttering" gate that almost-clears then re-engages).
- A configurable threshold via `broker_orphan_consecutive_clear_threshold` in `ReconciliationConfig`.

The 5-cycle threshold (vs 3) is the M4 cost-of-error asymmetry decision: false-clear (gate releases while phantom short persists) is more dangerous than false-hold (gate stays engaged a few extra cycles). 5 cycles ≈ 5 minutes of confirmed broker-zero observations, which is operationally robust against transient broker reconnection / reconciliation gaps.

## Requirements

1. **Add `_phantom_short_clear_cycles: dict[str, int]` state field** to `OrderManager.__init__()`:

   ```python
   # Sprint 31.91 Session 2c.2: per-symbol consecutive-cycle counter for
   # auto-clearing the phantom_short gate. Increments on each reconciliation
   # cycle observing broker-zero for a gated symbol; reaches the configured
   # threshold (default 5 per M4) -> gate clears. Counter resets on
   # re-detection of phantom short (preventing stuttering).
   #
   # M4 cost-of-error asymmetry: 5 cycles (~5 min) > 3 cycles (~3 min) because
   # false-clear (gate releases while short persists) is more dangerous than
   # false-hold (gate stays engaged few extra cycles).
   self._phantom_short_clear_cycles: dict[str, int] = {}
   ```

2. **Add config field `broker_orphan_consecutive_clear_threshold: int = 5`** to `ReconciliationConfig` in `argus/core/config.py:229`:

   ```python
   broker_orphan_consecutive_clear_threshold: int = Field(
       default=5,
       ge=1,
       le=60,
       description=(
           "Number of consecutive reconciliation cycles observing broker-zero "
           "shares before the phantom-short gate auto-clears for a symbol. "
           "Default 5 (~5 minutes) per M4 cost-of-error asymmetry: false-clear "
           "is more dangerous than false-hold. Was 3 in earlier sprint drafts; "
           "raised to 5 during Phase A revisit. Range 1-60 (60 ~hourly cap)."
       ),
   )
   ```

   Update YAMLs (`config/system_live.yaml`, `config/system_paper.yaml`, etc.) with explicit `broker_orphan_consecutive_clear_threshold: 5`.

3. **Implement auto-clear logic in the reconciliation orphan-loop body:**

   The 2b.1 broker-orphan branch already has a "resolved_symbols" cleanup loop for the `_broker_orphan_long_cycles` counter. Session 2c.2 extends this with auto-clear logic for `_phantom_short_gated_symbols`. The high-level shape:

   ```python
   # NEW (Session 2c.2): auto-clear logic for phantom_short gate

   # Step 1: For each gated symbol, check if broker reports zero shares.
   threshold = self._config.reconciliation.broker_orphan_consecutive_clear_threshold
   gated_to_clear: list[str] = []

   for symbol in list(self._phantom_short_gated_symbols):  # snapshot to allow mutation
       broker_pos = broker_positions.get(symbol)
       broker_shares = broker_pos.shares if broker_pos else 0
       broker_is_short = (
           broker_pos is not None and broker_pos.side == OrderSide.SELL
       )

       if broker_is_short:
           # Re-detection of the phantom short — RESET the clear counter.
           # This prevents a stuttering gate where transient broker-zero
           # observations would almost-clear, then a re-detection would
           # restart from 0 with the operator never seeing the gate clear.
           if symbol in self._phantom_short_clear_cycles:
               self._phantom_short_clear_cycles.pop(symbol)
               self._logger.info(
                   "Phantom-short gate clear-counter RESET for %s "
                   "(broker still reports short; counter back to 0).",
                   symbol,
               )
           continue  # gate stays engaged

       if broker_shares == 0:
           # Broker reports zero — increment the clear counter
           current = self._phantom_short_clear_cycles.get(symbol, 0) + 1
           self._phantom_short_clear_cycles[symbol] = current

           self._logger.info(
               "Phantom-short gate clear-counter for %s: cycle %d/%d "
               "(broker reports zero shares).",
               symbol, current, threshold,
           )

           if current >= threshold:
               gated_to_clear.append(symbol)
       else:
           # Broker reports a non-zero LONG (no longer short) — also a "clear"
           # signal; the original phantom short has resolved (operator may
           # have manually flattened, then the symbol re-entered legitimately,
           # or another path created a long position).
           current = self._phantom_short_clear_cycles.get(symbol, 0) + 1
           self._phantom_short_clear_cycles[symbol] = current
           self._logger.info(
               "Phantom-short gate clear-counter for %s: cycle %d/%d "
               "(broker reports LONG shares=%d, not short).",
               symbol, current, threshold, broker_shares,
           )
           if current >= threshold:
               gated_to_clear.append(symbol)

   # Step 2: Clear the gate for symbols that hit the threshold.
   for symbol in gated_to_clear:
       self._phantom_short_gated_symbols.discard(symbol)
       self._phantom_short_clear_cycles.pop(symbol, None)
       # Persist the removal (Session 2c.1's stub method, fully wired here)
       asyncio.create_task(self._remove_gated_symbol_from_db(symbol))
       self._logger.warning(
           "Phantom-short gate AUTO-CLEARED for %s after %d consecutive "
           "broker-non-short cycles. Symbol may now receive new entries. "
           "If this clearance is in error, operator can re-engage via "
           "POST /api/v1/reconciliation/phantom-short-gate/clear "
           "(but the gate is for engagement, not re-engagement; re-detection "
           "via reconciliation will re-engage automatically if the phantom "
           "short reappears).",
           symbol, threshold,
       )
   ```

   Notes:
   - The branching on `broker_is_short` vs `broker_shares == 0` vs `broker_shares > 0 (long)` covers all three observable broker states. The "long shares > 0" path also counts as a clear signal because the underlying phantom-short condition is no longer present.
   - `list(self._phantom_short_gated_symbols)` snapshots the iteration target; mutation of the set during iteration is the typical Python footgun.
   - The `_remove_gated_symbol_from_db` invocation is the same fire-and-forget pattern as 2c.1's persistence — best-effort, with the next reconciliation cycle as the safety net if the write fails (re-detection re-engages).

4. **Counter reset on re-detection** (already covered above in the `broker_is_short` branch). Verify that:
   - Re-detection ALSO triggers `_handle_broker_orphan_short` (Session 2b.1 behavior; the alert re-fires).
   - Re-detection's gate engagement is idempotent (Session 2c.1's `if symbol not in self._phantom_short_gated_symbols` guard, but the symbol IS already in the set, so it's a no-op).
   - The clear-counter is the only state that resets on re-detection.

5. **Counter cleanup on auto-clear.** When the gate clears for a symbol, the counter is removed (`self._phantom_short_clear_cycles.pop(symbol, None)`). This prevents stale counter entries from accumulating indefinitely.

6. **No edits to do-not-modify regions.** Standard list. Note: Session 2c.2 does NOT modify `main.py` (no startup-sequence change).

## Tests (~4 new pytest)

1. **`test_gate_clears_after_5_consecutive_zero_cycles`**
   - Setup: gate engaged for AAPL (`_phantom_short_gated_symbols = {"AAPL"}`).
   - Trigger 5 consecutive reconciliation cycles, each with `broker_positions = {}` (no AAPL).
   - Assert: after cycle 4, gate still engaged; counter at 4.
   - Assert: after cycle 5, gate cleared; AAPL not in `_phantom_short_gated_symbols`; counter cleaned up; `_remove_gated_symbol_from_db` called.

2. **`test_gate_persists_through_transient_broker_zero_resets_counter`**
   - Setup: gate engaged for AAPL.
   - Cycle 1: broker reports zero → counter = 1.
   - Cycle 2: broker reports SHORT → counter resets to 0 (popped from dict); gate still engaged.
   - Cycle 3: broker reports zero → counter = 1 (NOT 3 — reset happened).
   - Cycle 4: broker reports zero → counter = 2.
   - ...
   - Assert: gate doesn't auto-clear until 5 consecutive non-short cycles starting from cycle 3.
   - Assert: at cycle 7 (cycle 3 + 4 more = 5 consecutive non-short), gate clears.

3. **`test_clear_threshold_config_loadable_default_5`**
   - Load default `ReconciliationConfig` (no override).
   - Assert: `config.broker_orphan_consecutive_clear_threshold == 5`.
   - Assert: the field is in the YAML (read `config/system_live.yaml` and check the value).

4. **`test_clear_threshold_configurable_override`**
   - Load `ReconciliationConfig` with `broker_orphan_consecutive_clear_threshold=10` override.
   - Setup: gate engaged for AAPL; trigger 10 consecutive zero cycles.
   - Assert: gate doesn't clear at cycle 5 (config override active); clears at cycle 10.
   - Assert: Pydantic rejects `broker_orphan_consecutive_clear_threshold=0` and `=61` (out of range).

## Definition of Done

- [ ] `_phantom_short_clear_cycles` state field initialized.
- [ ] `broker_orphan_consecutive_clear_threshold: int = 5` config field added with `ge=1, le=60` bounds.
- [ ] Auto-clear logic in reconciliation orphan-loop body:
  - Increments on broker-non-short cycle.
  - Resets on re-detection (broker reports SHORT again).
  - Clears gate at threshold; cleans up counter; persists removal.
- [ ] Counter reset on re-detection verified (Test 2).
- [ ] M4 5-cycle default verified (Test 3).
- [ ] Configurability verified (Test 4).
- [ ] 4 new tests; all passing.
- [ ] CI green; pytest baseline ≥ 5,138.
- [ ] All do-not-modify list items show zero `git diff`.
- [ ] Tier 2 review verdict CLEAR.
- [ ] Close-out at `docs/sprints/sprint-31.91-reconciliation-drift/session-2c.2-closeout.md`.

## Close-Out Report

Standard structure. Verdict JSON:

```json
{
  "session": "2c.2",
  "verdict": "PROPOSED_CLEAR",
  "tests_added": 4,
  "tests_total_after": <fill>,
  "files_modified": [
    "argus/execution/order_manager.py",
    "argus/core/config.py",
    "config/system_live.yaml",
    "config/system_paper.yaml",
    "<test files>"
  ],
  "donotmodify_violations": 0,
  "tier_3_track": "side-aware-reconciliation",
  "m4_threshold_default": 5
}
```

Cite in close-out:
- The exact code comment explaining M4 cost-of-error asymmetry (must be present in either the field's Field description or as an inline `# M4` comment).
- Whether the YAML override pattern is `system_live.yaml` only or all three (live + paper + dev).

## Tier 2 Review Invocation

Standard pattern. Backend safety reviewer template. Review report at `session-2c.2-review.md`.

## Session-Specific Review Focus (for @reviewer)

1. **Default value matches M4 disposition (5 not 3).** Reviewer reads the config field and verifies the `default=5`. Earlier drafts had 3; M4 disposition raised to 5. The Field description must explicitly mention M4.

2. **Cost-of-error asymmetry rationale documented in code comment.** Reviewer confirms either:
   - The Field description on the config field mentions cost-of-error asymmetry, OR
   - An inline `# M4 cost-of-error asymmetry: ...` comment is in the auto-clear logic body.

3. **Counter-reset edge cases** (Test 2 is the verification):
   - Re-detection during a partial clear sequence resets cleanly.
   - The reset code path `pop` is None-safe (`pop(symbol, None)`).
   - No off-by-one errors: cycle 5 (== threshold) clears, cycle 4 (< threshold) does not.

4. **Snapshot iteration safety.** `for symbol in list(self._phantom_short_gated_symbols)` snapshots before mutation. Reviewer confirms the snapshot is in place; without it, mutation during iteration would raise `RuntimeError`.

5. **Persistence on auto-clear.** `_remove_gated_symbol_from_db` must be invoked when the gate clears. Reviewer runs Test 1 with a fresh DB connection in the assertion phase to confirm the row is removed.

6. **No regressions from 2c.1.** Re-detection still triggers Session 2b.1's alert and Session 2c.1's gate engagement (idempotent). Run 2c.1's tests; all should still pass.

7. **The "long shares > 0" branch is intentional, not a bug.** When a gated symbol later shows a legitimate long position at the broker (e.g., operator manually flattened the phantom short and a strategy fired a new long), the cycle counter increments toward auto-clear. This is correct behavior — the original phantom-short condition has resolved. Reviewer reads the branch and confirms it's intentional.

## Sprint-Level Regression Checklist (for @reviewer)

- **Invariant 5:** PASS — expected ≥ 5,138.
- **Invariant 14:** Row "After Session 2c.2" — Recon detects shorts = "full + auto-clear (5-cycle)".
- **Invariant 15:** PASS — no scoped exception in 2c.2.

## Sprint-Level Escalation Criteria (for @reviewer)

- **A2** (Tier 2 CONCERNS or ESCALATE).
- **A3** (post-merge paper session shows phantom-short gate clearing prematurely or staying engaged forever — both are operational regressions).
- **B1, B3, B4, B6** — standard halt conditions.
- **C7** (existing reconciliation tests fail because the auto-clear logic perturbs cycle-counting expectations) — most likely escalation site this session.

---

*End Sprint 31.91 Session 2c.2 implementation prompt.*

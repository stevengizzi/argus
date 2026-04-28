# Sprint 31.91, Session 2b.2 — Close-Out

**Status:** PROPOSED_CLEAR
**Branch:** `main`
**Test delta:** 5,139 → 5,153 pytest (+14 new) — exceeds the spec's "≥5,128" gate.
**Scoped suite:** `tests/execution/ tests/core/` 1,230 → 1,244 (+14), all green.
**Tier 3 track:** side-aware-reconciliation
**Operator decisions applied:** Item 3 / Option C (hybrid double-fire with cross-reference).

---

## Verdict JSON

```json
{
  "session": "2b.2",
  "verdict": "PROPOSED_CLEAR",
  "tests_added": 14,
  "tests_total_after": 5153,
  "files_modified": [
    "argus/execution/order_manager.py",
    "argus/core/risk_manager.py",
    "argus/core/health.py",
    "tests/core/test_health.py",
    "tests/execution/order_manager/test_safety.py"
  ],
  "files_added": [
    "tests/core/test_session2b2_pattern_a.py",
    "tests/execution/order_manager/test_session2b2_pattern_a_b.py",
    "docs/sprints/sprint-31.91-reconciliation-drift/session-2b.2-closeout.md"
  ],
  "donotmodify_violations": 0,
  "tier_3_track": "side-aware-reconciliation",
  "operator_decisions_applied": ["Item 3 / Option C (hybrid double-fire with cross-reference)"]
}
```

---

## Change Manifest

### `argus/execution/order_manager.py`

- **Pattern A.1 — Margin circuit reset** (existing site previously at line 1567,
  now lines 1562–1598). Side-aware count filter:
  - Partition broker positions into `long_positions` / `short_positions` via
    `getattr(p, "side", None) == OrderSide.BUY|SELL`.
  - `position_count = len(long_positions)` is what's compared to the
    `margin_circuit_reset_positions` threshold.
  - Operator-facing INFO breakdown line:
    `"Margin circuit reset check: longs=%d, shorts=%d, reset_threshold=%d, will_reset=%s"`.
  - Existing reset RESET-line updated to read `"long position count %d"`.
- **Pattern B — EOD Pass 2 phantom_short alert** (lines 1851–1882). Appended
  immediately AFTER the existing `logger.error("EOD flatten: DETECTED
  UNEXPECTED SHORT POSITION ...")` inside the `elif side == OrderSide.SELL:`
  branch (line 1824). The DEF-199 A1 detection logic (`if side == OrderSide.BUY` /
  `elif side == OrderSide.SELL` / `else`) is unchanged. The alert emission
  is wrapped in a defensive `try/except logger.exception` per the 2b.1
  pattern.

### `argus/core/risk_manager.py`

- New import: `from argus.models.trading import OrderSide`.
- **Pattern A.2 — Max-concurrent gate (single site)** at line 337 (now lines
  337–356). Side-aware filter; `would_reject` precomputed; INFO breakdown
  line `"Risk Manager max-concurrent #1 (entry gate): longs=%d, shorts=%d,
  max_concurrent=%d, would_reject=%s"`. Existing rejection-path WARNING and
  `OrderRejectedEvent` shape unchanged.
- **Check 0 (`share_count <= 0` rejection at line 274–275) is UNCHANGED.**
  Per the spec's pre-flight grep #7 instruction, Check 0 was located prior
  to any edit and is at line 274 (NOT line 335 as the regression-checklist's
  invariant 8 description colloquially suggested). See "RULE-038
  Discrepancies" below.

### `argus/core/health.py`

- New imports: `SystemAlertEvent` (added to existing `argus.core.events`
  import); `OrderSide` from `argus.models.trading`; `OrderManager` (under
  `TYPE_CHECKING`).
- **`HealthMonitor.__init__`**: new field `self._order_manager: OrderManager | None = None`
  with explanatory comment for Option C cross-reference + a TODO citing the
  Session 5a.1+ migration path.
- **New public method `set_order_manager(order_manager: OrderManager) -> None`**.
  Setter pattern chosen because main.py is on the do-not-modify list — tests
  wire this directly; production wiring is deferred (close-out item 3 below).
- **`_run_daily_integrity_check` rewritten** as a Pattern A.4 hybrid:
  - Side-partition into `long_positions` / `short_positions`.
  - Long-orphans-without-stop → existing `_send_alert("Integrity Check FAILED", ...)`
    path is preserved; **Option C cross-reference** appended to the body
    when `self._order_manager._broker_orphan_last_alerted_cycle.get(symbol)`
    returns a non-zero value.
  - Every short → `phantom_short` `SystemAlertEvent` with
    `source="health.integrity_check"` and structured metadata.
  - INFO breakdown line:
    `"Health integrity check: longs=%d (without_stop=%d), shorts=%d
    (all phantom by long-only design), total_broker=%d"`.
  - `try/except` around `event_bus.publish` per the 2b.1 defensive pattern.
- "All %d positions have stops. OK." log emits only when there are no longs
  without stops AND no shorts (otherwise the breakdown line carries the
  signal).

### Test additions / migrations

- **NEW** `tests/execution/order_manager/test_session2b2_pattern_a_b.py` (5 tests).
  Pattern A.1 reset (3) + Pattern B EOD Pass 2 alert (2). Includes a
  non-regression test that an inverted comparator after the refactor would
  catch.
- **NEW** `tests/core/test_session2b2_pattern_a.py` (9 tests). Pattern A.2
  max-concurrent (4) + Pattern A.4 Health hybrid (5 — base / phantom /
  breakdown / cross-ref present / cross-ref absent).
- **MODIFIED** `tests/core/test_health.py`: 2 existing integrity-check tests
  updated to set `mock_position.side = OrderSide.BUY` (pre-Pattern A.4, the
  side filter would silently drop sideless mocks into neither bucket and
  the existing assertion would no longer fire).
- **MODIFIED** `tests/execution/order_manager/test_safety.py::test_concurrent_limit_still_works_when_set`
  updated to set `.side = OrderSide.BUY` on its 5 MagicMock positions so
  the side-aware filter counts them as longs against the cap. Behavioral
  intent unchanged.

---

## RULE-038 Discrepancies

Three grep-disprovable claims in the spec; the implementation reconciled
each per RULE-038's "flag the discrepancy in the close-out — do not invent a
fix for a claim that no longer holds" guidance.

### 1. `risk_manager.py:771` — second max-concurrent site does not exist

**Spec claim.** "Site A.3: Risk Manager max-concurrent-positions site #2
(`risk_manager.py:771`)."

**Grep-truth.** `risk_manager.py` has exactly ONE max-concurrent check, at
line 337. Line 771 is inside the docstring of `daily_integrity_check`; line
776 reads `broker.get_positions()` only to populate `IntegrityReport`'s
`positions_checked` field — it never enforces a cap. PHASE-A-REVISIT-FINDINGS
§A3 walks through "Row #1 / #2" but its detailed code reading shows only
one site (lines 102–122 of that doc). `git log -S "len(positions) >= max_pos"`
confirms only one historical commit ever touched a `len(positions) >= max_pos`
form in this file (Sprint 2 introduction); no second site has ever existed.

**Resolution.** Pattern A.2 applied once at the actual single site (line 337).
Test 4 (`test_risk_manager_max_concurrent_positions_uses_longs_only_771`)
and the second leg of Test 5 ("Same pattern at :771") in the spec's
Requirements Summary were dropped. Net new tests for Pattern A.2: 4
(Tests 3 + 5 + breakdown + non-regression at-cap), not 5.

### 2. `risk_manager.py:335` is max-concurrent, NOT Check 0

**Spec pre-flight #7 instruction.** "Verify that the file has not drifted
such that line 335 IS Check 0 now. … note the actual Check 0 line in your
close-out for the Tier 2 reviewer's clarity."

**Grep-truth.** Pre-edit, line 274–275 contained Check 0
(`if signal.share_count <= 0:`); line 335–337 contained max-concurrent.
Post-edit (because of added imports + breakdown logic), Check 0 is now at
line 275 and max-concurrent body spans 337–356. The substantive distinction
holds: Check 0 is a `share_count` guard near the top of `evaluate_signal`;
max-concurrent is a separate later check that calls `await
self._broker.get_positions()`. Session 2b.2 modified ONLY the max-concurrent
site. Check 0 has zero diff.

### 3. EOD Pass 2 line drift

**Spec claim.** "Site B.1: EOD Pass 2 short detection
(`order_manager.py:~1734`) … existing detection logic block at `:1670-1750`
is do-not-modify."

**Grep-truth.** The actual Pass 2 SELL-detection `logger.error("EOD flatten:
DETECTED UNEXPECTED SHORT POSITION ...")` is at lines 1828–1835
(post-edit: 1843–1850; the addition of Pattern A.1 above shifted line
numbers). The Pass 1 retry SELL-detection logger.error is at lines 1777–1785.
**Both** are OUTSIDE the spec's stated `:1670-1750` do-not-modify region;
neither is inside that range. The actual DEF-199-protective branching
(`if side == OrderSide.BUY` / `elif side == OrderSide.SELL` / `else`)
spans approximately lines 1747–1842 in Pass 1 retry and 1813–1842 in
Pass 2.

**Resolution.** Pattern B alert emission appended immediately AFTER the
existing Pass 2 `logger.error` at line 1850 (post-edit), well outside the
`:1670-1750` window. The new alert-publishing code is INSIDE the
`elif side == OrderSide.SELL:` branch — augmenting observability without
modifying the existing if/elif/else detection logic. Per RULE-007, the
parallel Pass 1 retry SELL detection at line 1777 was NOT augmented (the
spec scopes Pattern B to "EOD Pass 2"); a future session can extend the
alert taxonomy to that site for consistency. Verified via `git diff`: the
DEF-199 A1 protective branching has zero edits.

---

## Pattern Recognition (per Session-Specific Review Focus #1)

| Site | Pattern | Filter? | Alert addition? | Breakdown log line? | DEF-199 logic touched? |
|---|---|---|---|---|---|
| A.1 margin reset (`order_manager.py:1567`) | A | yes (long-only) | no | yes | n/a |
| A.2 max-concurrent (`risk_manager.py:337`) | A | yes (long-only) | no | yes | n/a |
| A.4 health integrity (`health.py:_run_daily_integrity_check`) | A hybrid | yes (long-only) + phantom-short branch | yes (`phantom_short` for shorts) | yes | n/a |
| B.1 EOD Pass 2 (`order_manager.py:1850`) | B | NO | yes (`phantom_short` alongside `logger.error`) | n/a | NOT TOUCHED |

Pattern B's distinguishing obligation: the existing detection is correct
and protected; we add the alert without filtering anything. Pattern A.4 is
hybrid because shorts get the `phantom_short` alert routing but longs
without stops continue to trip the existing alert.

---

## Alert Taxonomy Consistency Audit (per Review Focus #3)

Three `phantom_short` emission sites now exist; metadata shape is
deliberately uniform so Session 5a.2's auto-resolution policy table can
key on `alert_type` alone.

| Source | Site | `severity` | `metadata.symbol` | `metadata.shares` | `metadata.side` | `metadata.detection_source` |
|---|---|---|---|---|---|---|
| `reconciliation` | 2b.1 `_handle_broker_orphan_short` | critical | yes | yes | "SELL" | `reconciliation.broker_orphan_branch` |
| `health.integrity_check` | 2b.2 A.4 (`health.py`) | critical | yes | yes | "SELL" | `health.integrity_check` |
| `eod_flatten` | 2b.2 B.1 (`order_manager.py`) | critical | yes | yes | "SELL" | `eod_flatten.pass2` |

The `source` field varies (operator can route to surface-of-origin); the
`metadata.detection_source` field carries the precise emission point. All
three carry the same shape for `symbol` / `shares` / `side`.

---

## Discovered Edge Cases

1. **Health-cross-reference production wiring is no-op until Session 5a.1+.**
   `set_order_manager()` exists; `argus/main.py` is on the do-not-modify
   list, so production wiring is deferred. Tests wire this explicitly via
   the setter. Per the spec's RULE-007 guidance, no inter-session re-pointing
   was attempted. The `health.py:HealthMonitor.__init__` field carries an
   inline TODO citing the Session 5a.1+ migration to HealthMonitor's
   queryable active-alert state.

2. **Two existing tests required side migration.** `tests/core/test_health.py`'s
   `test_daily_check_finds_unprotected_position` and
   `test_daily_check_all_positions_have_stops` create `MagicMock()` positions
   without a `.side`. Post-Pattern A.4, sideless mocks land in neither
   bucket and the long-orphan branch never fires. Both were updated to set
   `mock_position.side = OrderSide.BUY`. Same migration applied to
   `tests/execution/order_manager/test_safety.py::test_concurrent_limit_still_works_when_set`.
   These migrations are backward-compatible with the original test intent;
   the only behavioral assumption changed is "positions without a `.side`
   do NOT count toward broker-side caps" — which is the correct new
   behavior under Pattern A.

3. **Pass 1 retry SELL detection is a sibling to Pass 2 but NOT alerted.**
   `order_manager.py:1777` (Pass 1 retry) also detects an unexpected short
   via the same protective branching (DEF-199 A1) and emits a `logger.error`,
   but Session 2b.2's spec scopes Pattern B to "EOD Pass 2" only. Per
   RULE-007 no scope expansion was performed; a future session can add the
   `phantom_short` alert at the Pass 1 retry site for full taxonomy
   coverage. This is a known consistency gap, not a behavior bug — the
   existing logger.error is unchanged.

4. **`logger.info` on the margin reset site was previously absent.** Pattern
   A.1 introduces the breakdown line as a new log line. Operators reading
   prior logs will not see it; new sessions will. No existing log-line
   assertion picks it up (verified via the full scoped + full pytest suite
   green).

---

## Regression Checklist Verification

- **Invariant 1 (DEF-199 A1 fix detects + refuses 100% of phantom shorts at
  EOD):** PASS. `argus/execution/order_manager.py` diff shows zero edits to
  the SELL-detection if/elif/else branching at Pass 1 retry (lines
  1777-1785) or Pass 2 (1843-1850). Pattern B's alert emission is appended
  AFTER the existing logger.error inside the SELL branch.
  Test `test_eod_pass2_short_emits_phantom_short_alert_alongside_logger_error`
  asserts both the existing logger.error AND `broker.place_order.assert_not_called()`.
- **Invariant 5 (test count ≥ baseline + new):** PASS. 5,139 → 5,153 (+14).
- **Invariant 8 (Risk Manager Check 0 unchanged):** PASS. Check 0 lives at
  `risk_manager.py:274-275`; modified region is the entirely separate
  max-concurrent block at line 337. `git diff` confirms no edits in
  `:1-330` of `risk_manager.py`.
- **Invariant 10 (DEC-367 margin circuit unchanged at the engagement
  level):** PASS. The threshold-COMPARISON is now side-aware (Pattern A.1)
  but the engagement / open-circuit behavior, the rejection counter, and
  the auto-shutdown side effects are byte-identical.
- **Invariant 14 (recon detects shorts):** PASS — partial + side-aware
  reads (4 filter sites + 1 alert-align). Pre-Session-2b.2 the
  reconciliation broker-orphan branch detected; now Pattern B at EOD Pass 2
  + Pattern A.4 at Health both also surface `phantom_short` alerts.
- **Invariant 15 (do-not-modify list):** PASS. `argus/main.py`,
  `argus/models/trading.py`, `argus/execution/alpaca_broker.py`,
  `argus/data/alpaca_data_service.py`, `argus/execution/ibkr_broker.py`,
  `argus/execution/broker.py`, `docs/sprints/sprint-31.9/IMPROMPTU-04-closeout.md`,
  and `workflow/` all show zero diff.

---

## Context State

GREEN. Session ran well within context limits; no compaction events
observed. All three production files plus two test files were edited /
created in a single linear pass. Three RULE-038 discrepancies were
identified at pre-flight and reconciled before any code edit.

---

## Next Session

- Tier 2 review at `docs/sprints/sprint-31.91-reconciliation-drift/session-2b.2-review.md`.
- Track continues: 2c.1 (per-symbol entry gate), 2c.2 (gate persistence),
  2d (operator override + observability), then 3, 4, 5*.

---

*End Sprint 31.91 Session 2b.2 close-out.*

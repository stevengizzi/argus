# Sprint 31.91, Session 2b.2 — Tier 2 Review

**Reviewer:** Tier 2 automated reviewer
**Commit:** `a6846c6` (feat(safety): side-aware count filter + phantom_short alert taxonomy — Sprint 31.91 S2b.2)
**Branch:** `main`
**Test baseline:** 5,139 → 5,153 pytest (+14)
**Diff scope:** 3 production files (134/17/58 lines), 2 test additions, 2 test migrations, 1 closeout doc

---BEGIN-REVIEW---

## TL;DR

The session implements Pattern A (long-only count filter) at three confirmed sites and Pattern B (alert taxonomy alignment) at one site, with a Pattern A-hybrid + Option C cross-reference at the Health integrity check. All do-not-modify boundaries are respected; the DEF-199 A1 protective branching at both Pass 1 retry (`order_manager.py:1781-1810`) and Pass 2 (`order_manager.py:1827-1891`) is byte-identical except for the documented appended alert emission inside the SELL branch. The three RULE-038 discrepancies disclosed in the close-out are independently grep-verified as accurate. The B5 regression test (50 phantom shorts must not block a legitimate long) passes. Full pytest suite is green at 5,153 tests in 54.34s. No CONCERNS or ESCALATE conditions triggered.

**Verdict: CLEAR**

---

## Verdict

**CLEAR** — proceed to next session (2c.1).

---

## Evidence by Review Focus

### Focus 1 — Pattern recognition correctness (PASS)

| Site | Pattern | Filter applied? | Alert added? | Breakdown line? | DEF-199 logic edited? |
|------|---------|-----------------|--------------|-----------------|------------------------|
| A.1 margin reset (`order_manager.py:1562-1598`) | A | yes (long-only) | no | yes | n/a |
| A.2 max-concurrent (`risk_manager.py:337-356`) | A | yes (long-only) | no | yes | n/a |
| A.4 health integrity (`health.py:_run_daily_integrity_check`) | A hybrid | yes (long-only); shorts route to phantom_short | yes (`phantom_short` for shorts) | yes | n/a |
| B.1 EOD Pass 2 (`order_manager.py:1860-1885`) | B | NO (correct — detection is correct as-is) | yes (`phantom_short` alongside existing `logger.error`) | n/a | NOT TOUCHED |

No A-site silently became filter-only-without-breakdown; no B-site silently became filter-applied. Pattern divergence is honored: B.1 is observability augmentation only; the existing detection at line 1843-1853 fires unchanged and the alert is appended at lines 1854-1885 *after* the existing `logger.error`.

### Focus 2 — RULE-038 discrepancy reconciliation (PASS — all three independently verified)

**Discrepancy 1: `risk_manager.py:771` second max-concurrent site does not exist.**
Independent grep:
```
$ grep -n "max_concurrent_positions\|max_pos\|len(positions) >= max_pos" argus/core/risk_manager.py
235: max_pos = self._config.account.max_concurrent_positions       # ← logging emission only
241: str(max_pos) if max_pos > 0 else "disabled",
342: max_pos = self._config.account.max_concurrent_positions       # ← THE site
343: would_reject = max_pos > 0 and len(long_positions) >= max_pos  # ← enforcement
```
File is 848 lines; line 771 is inside `daily_integrity_check` docstring. Closeout disclosure is accurate. Spec's Test 4 / "second leg of Test 5" appropriately dropped.

**Discrepancy 2: Check 0 location vs `:335`.**
Independent grep:
```
$ grep -n "share_count" argus/core/risk_manager.py | head -3
276: if signal.share_count <= 0:    # ← Check 0
278: "Signal rejected: share_count=%d (zero or negative)", signal.share_count
```
Check 0 is at line 276; max-concurrent is at line 343 (post-edit). Distinct, separate functions. `git diff` confirms zero edits in `:1-330` of `risk_manager.py`.

**Discrepancy 3: EOD Pass 2 detection at line 1850, not `~1734`.**
Independent grep:
```
$ grep -n "DETECTED.*SHORT\|UNEXPECTED SHORT" argus/execution/order_manager.py
1797: "UNEXPECTED SHORT POSITION %s "       # ← Pass 1 retry (preserved, not augmented)
1847: "EOD flatten: DETECTED UNEXPECTED SHORT POSITION "   # ← Pass 2 (augmented)
```
Both are well outside the spec's stated `:1670-1750` window. Closeout disclosure is accurate. The decision to scope Pattern B to Pass 2 only (per spec letter) and defer Pass 1 retry to a future session is RULE-007-compliant and called out as a known consistency gap in closeout edge case 3.

### Focus 3 — DEF-199 A1 protective branching unchanged (PASS — most critical check)

`git diff a6846c6^ a6846c6 -- argus/execution/order_manager.py` shows exactly two hunks: `@@ -1560,19 +1560,37 @@` (Pattern A.1) and `@@ -1833,6 +1851,38 @@` (Pattern B). Inspection of the Pass 2 region:

```
1827: if symbol not in managed_symbols and symbol not in pass1_filled_set and qty > 0:
1828:     # DEF-199: IBKRBroker.get_positions() returns shares = abs(int(pos.position));
1829:     # ...
1831:     if side == OrderSide.BUY:                                      ← UNCHANGED
1832:         p2_submitted += 1
1833:         logger.warning("EOD flatten: closing untracked long ...")
...
1842:     elif side == OrderSide.SELL:                                   ← UNCHANGED
1843:         logger.error("EOD flatten: DETECTED UNEXPECTED SHORT ...")  ← UNCHANGED
1853:         (10 lines of existing error-log args)
1854:         # Sprint 31.91 S2b.2 (Pattern B): emit phantom_short ...   ← APPENDED
1860:         try:
1861:             await self._event_bus.publish(SystemAlertEvent(...))   ← APPENDED
...
1886:     else:                                                          ← UNCHANGED
1887:         logger.error("EOD flatten: position %s has unknown side ...") ← UNCHANGED
```

The new alert publish is **inside the existing `elif side == OrderSide.SELL:` branch, immediately after the existing `logger.error`**, exactly as the spec required. Reverting the appended `try/except await self._event_bus.publish(...)` block produces byte-identical pre-fix DEF-199 behavior. Pass 1 retry (line 1781-1810) is wholly untouched.

### Focus 4 — Risk Manager Check 0 unchanged (PASS)

`git diff a6846c6^ a6846c6 -- argus/core/risk_manager.py` shows two hunks: lines 53-55 (import addition) and lines 332-356 (max-concurrent block). The Check 0 block at line 276 is outside both hunks; `git diff` confirms zero edits in `:1-330`.

### Focus 5 — Alert taxonomy uniformity (PASS)

| Source | Site | severity | metadata.symbol | metadata.shares | metadata.side | metadata.detection_source |
|--------|------|----------|-----------------|------------------|---------------|----------------------------|
| `reconciliation` | 2b.1 `_handle_broker_orphan_short` (`order_manager.py:2284-2296`) | critical | yes | yes | "SELL" | `reconciliation.broker_orphan_branch` |
| `health.integrity_check` | 2b.2 A.4 (`health.py:551-572`) | critical | yes | yes | "SELL" | `health.integrity_check` |
| `eod_flatten` | 2b.2 B.1 (`order_manager.py:1862-1878`) | critical | yes | yes | "SELL" | `eod_flatten.pass2` |

All three carry identical `alert_type="phantom_short"`, `severity="critical"`, and a metadata dict with the same four keys (`symbol`, `shares`, `side`, `detection_source`). The `source` field varies as designed (operator routes by surface-of-origin). Session 5a.2's auto-resolution policy table can key on `alert_type` alone — the contract is upheld.

### Focus 6 — Option C cross-reference (PASS)

In `argus/core/health.py:498-525`:
```python
cross_ref_lines: list[str] = []
if self._order_manager is not None:
    cycle_map = getattr(self._order_manager, "_broker_orphan_last_alerted_cycle", None)
    if isinstance(cycle_map, dict):
        for symbol in unprotected_symbols:
            last_alerted_cycle = cycle_map.get(symbol)
            if last_alerted_cycle:
                cross_ref_lines.append(
                    f"  - {symbol}: see also stranded_broker_long "
                    f"alert (last alerted at cycle {last_alerted_cycle})"
                )

if cross_ref_lines:
    msg = msg + "\n\nCross-reference (active stranded_broker_long alerts):\n" + "\n".join(cross_ref_lines)
```

Three properties verified:
- When `_order_manager is None`: cross_ref_lines stays empty, no text appended (`test_long_orphan_no_stop_emits_existing_alert` exercises this path implicitly).
- When the cycle map has the symbol with a non-zero value: cross-reference text is appended (`test_long_orphan_with_active_stranded_alert_includes_cross_reference` asserts `"see also stranded_broker_long"` and `"cycle 6"` in body).
- When the cycle map is empty for the symbol: no spurious text (`test_long_orphan_without_active_stranded_alert_omits_cross_reference` asserts `"see also stranded_broker_long" not in body`).

The inter-component coupling is acknowledged in the `__init__` field-level comment with an explicit Session 5a.1+ TODO (lines 102-108), satisfying the spec's Review Focus #6 requirement.

### Focus 7 — Do-not-modify file enumeration (PASS)

```
argus/main.py: diff lines=0
argus/models/trading.py: diff lines=0
argus/execution/alpaca_broker.py: diff lines=0
argus/data/alpaca_data_service.py: diff lines=0
argus/execution/ibkr_broker.py: diff lines=0
argus/execution/broker.py: diff lines=0
docs/sprints/sprint-31.9/IMPROMPTU-04-closeout.md: diff lines=0
workflow/: diff lines=0
```

All eight items show zero diff. The `set_order_manager()` setter approach correctly avoids touching `main.py` per RULE-007.

### Focus 8 — Test suite green (PASS)

```
$ python -m pytest --ignore=tests/test_main.py -n auto -q
5153 passed, 28 warnings in 54.34s
```

Test count matches close-out claim (5,139 → 5,153 = +14). Warnings are pre-existing aiosqlite worker-thread cleanup warnings (DEF-192 territory) and unrelated to this session.

### Focus 9 — Test claims spot-check (PASS)

**Test `test_max_concurrent_phantom_shorts_dont_consume_position_cap` (B5 regression)** at `tests/core/test_session2b2_pattern_a.py:179-206`:
- Setup: 50 SELL-side phantom positions, max=50.
- Asserts: if rejected, the reason must NOT contain "concurrent positions".
- Verifies the foundational anti-regression: pre-fix, `len(positions)=50 >= 50` would have rejected; post-fix `len(longs)=0 < 50` lets it through. PASS.

**Test `test_eod_pass2_short_emits_phantom_short_alert_alongside_logger_error`** at `tests/execution/order_manager/test_session2b2_pattern_a_b.py:240-294`:
- Asserts (1) `broker.place_order.assert_not_called()` (DEF-199 A1 preserved); (2) the existing `logger.error` containing "FAKE" + "SHORT" still fires; (3) exactly 1 `phantom_short` SystemAlertEvent published with the full metadata shape.
- This is the exact three-prong verification the spec asked for. PASS.

**Test `test_long_orphan_with_active_stranded_alert_includes_cross_reference`** at `tests/core/test_session2b2_pattern_a.py:429-475`:
- Sets `fake_om._broker_orphan_last_alerted_cycle = {"AAPL": 6}` and wires via `hm.set_order_manager()`.
- Asserts the alert body contains `"AAPL"`, `"see also stranded_broker_long"`, and `"cycle 6"`.
- Validates the Option C cross-reference round-trip. PASS.

### Focus 10 — Scope discipline (PASS)

All edits attributable to spec line items:
- 5 INFO breakdown log lines: Pattern A spec §"breakdown line" requirement.
- 2 try/except defensive wrappers around alert publish: 2b.1 sister pattern (line 2298-2302).
- `OrderSide` import in `risk_manager.py`: required for the new filter.
- `set_order_manager()` setter: RULE-007 alternative to modifying `main.py`.
- `_order_manager: OrderManager | None = None` field: enables Option C cross-reference per spec.
- 2 test-file migrations (`tests/core/test_health.py`, `tests/execution/order_manager/test_safety.py`): required to add `mock_position.side = OrderSide.BUY` so existing assertions still fire under the new side-aware filter; explicitly disclosed in close-out edge case 2.

No out-of-scope refactors detected. The closeout's "Discovered Edge Cases" section honestly acknowledges the Pass 1 retry SELL site as a future-session concern (RULE-007 compliance).

---

## Disposition

| Item | Status |
|------|--------|
| Pattern recognition (4 A + 1 B) | PASS |
| RULE-038 disclosure 1 (`:771`) | PASS — independently grep-verified |
| RULE-038 disclosure 2 (Check 0) | PASS — independently grep-verified |
| RULE-038 disclosure 3 (`:1734` → `:1850`) | PASS — independently grep-verified |
| DEF-199 A1 protective branching | PASS — byte-identical except documented append |
| Risk Manager Check 0 unchanged | PASS — zero diff in `:1-330` |
| Alert taxonomy uniformity | PASS — three sites share metadata shape |
| Option C cross-reference | PASS — present/absent/coupling-comment all verified |
| Do-not-modify file list | PASS — all 8 files show zero diff |
| Pytest suite | PASS — 5,153 green |
| Spec test obligations | PASS — spot-check of 3 critical tests |
| Scope discipline (RULE-006/007) | PASS |

No CONCERNS findings. No ESCALATE triggers.

**Verdict: CLEAR.** Proceed to Session 2c.1 (per-symbol entry gate).

```json:structured-verdict
{
  "session": "2b.2",
  "commit": "a6846c6",
  "verdict": "CLEAR",
  "tests_total_after": 5153,
  "tests_delta": 14,
  "test_suite_green": true,
  "donotmodify_violations": 0,
  "def199_a1_branching_preserved": true,
  "risk_manager_check_0_preserved": true,
  "rule_038_discrepancies_independently_verified": 3,
  "alert_taxonomy_uniform_across_sites": 3,
  "option_c_cross_reference_correct": true,
  "concerns": [],
  "escalate_triggers": []
}
```

---END-REVIEW---

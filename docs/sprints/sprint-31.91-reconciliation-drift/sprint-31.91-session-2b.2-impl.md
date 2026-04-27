# Sprint 31.91, Session 2b.2: Four Count-Filter Sites + One Alert-Alignment Site (Two-Pattern B5 Fix)

> **Track:** Side-Aware Reconciliation Contract (Sessions 2a → 2b.1 → **2b.2** → 2c.1 → 2c.2 → 2d).
> **Position in track:** Third session. Consumes 2b.1's `phantom_short` alert taxonomy; applies **two distinct patterns** at five sites (4 filter + 1 alert-alignment).

## Pre-Flight Checks

Before making any changes:

1. **Read `.claude/rules/universal.md` in full and treat its contents as binding for this session.** RULE-038 (grep-verify discipline), RULE-050 (CI green), RULE-019, and RULE-007 (out-of-scope discoveries) all apply.

2. Read these files to load context:
   - `argus/execution/order_manager.py:1492` — margin circuit reset (Pattern A, site 1; verify line)
   - `argus/execution/order_manager.py:~1734` — EOD Pass 2 short detection (Pattern B; verify line)
   - `argus/core/risk_manager.py:335` — max-concurrent-positions site #1 (Pattern A, site 2)
   - `argus/core/risk_manager.py:771` — max-concurrent-positions site #2 (Pattern A, site 3)
   - `argus/core/health.py:443-450` — daily integrity check (Pattern A — hybrid: filter + alert routing)
   - `docs/sprints/sprint-31.91-reconciliation-drift/PHASE-A-REVISIT-FINDINGS.md` §A3 — B5 audit-row analysis
   - `docs/sprints/sprint-31.91-reconciliation-drift/sprint-spec.md` D5 — Session 2b.2 portion (Pattern A + Pattern B)
   - `docs/sprints/sprint-31.91-reconciliation-drift/PHASE-D-OPEN-ITEMS.md` Item 3 — operator decision pre-applied (Option C: hybrid double-fire)
   - Session 2b.1 deliverables: `_handle_broker_orphan_long`'s `stranded_broker_long` alert (read it; Pattern A Health hybrid cross-references it)

3. Run the scoped test baseline:

   ```
   python -m pytest tests/execution/ tests/core/ -n auto -q
   ```

   Expected: all passing (Session 2b.1's close-out confirmed scoped suite).

4. Verify you are on the correct branch: **`main`**.

5. Verify Sessions 2a + 2b.1 deliverables are present on `main`:

   ```bash
   grep -n "class ReconciliationPosition" argus/execution/order_manager.py
   grep -n "_broker_orphan_long_cycles\|broker_orphan_alert_enabled" argus/execution/order_manager.py
   grep -n "stranded_broker_long\|phantom_short" argus/execution/order_manager.py
   ```

   All three must match. If not, halt.

6. **Pre-flight grep — verify all five sites still exist at the expected lines:**

   ```bash
   # Pattern A sites (count filters)
   grep -n -A 5 "_check_margin_circuit\|margin_circuit_reset" argus/execution/order_manager.py | head -30
   grep -n -B 2 -A 5 "max_concurrent_positions" argus/core/risk_manager.py
   grep -n -B 2 -A 5 "integrity\|missing_stop" argus/core/health.py | head -30

   # Pattern B site (alert alignment, no filter)
   grep -n -B 2 -A 8 "DETECTED UNEXPECTED SHORT POSITION\|short position.*EOD\|pass2.*short" argus/execution/order_manager.py | head -30
   ```

   Verify each site's line number is within ±5 lines of the spec. If drift > 5, halt and reconcile per RULE-038.

7. **Pre-flight grep — verify Risk Manager Check 0 (`share_count <= 0` rejection) location, distinct from line 335:**

   ```bash
   grep -n "share_count\|share_count <= 0\|Check 0" argus/core/risk_manager.py
   ```

   The regression-checklist invariant 8 description says "Risk Manager Check 0 around `risk_manager.py:335`" — this is **incorrect attribution** (per Phase A revisit findings). Line 335 is the max-concurrent-positions check. Check 0 is a different check elsewhere in `risk_manager.py`. Session 2b.2 modifies `:335` (max-concurrent) and `:771` (max-concurrent #2), and must NOT modify Check 0. Note the actual Check 0 line in your close-out for the Tier 2 reviewer's clarity.

## Reframe (per third-pass HIGH #2)

Earlier framings called this a "three sites with the same side-aware-filter pattern" change. That framing was wrong twice over: wrong on count (4 filter sites + 1 alert-alignment site = 5) and wrong on uniformity (the EOD Pass 2 site has a different obligation — alert taxonomy alignment, not filter application).

Two distinct patterns:

- **Pattern A (4 sites — count filter):** Apply long-only filtering to broker-state reads that drive safety decisions. Phantom shorts must not inflate counts that could lock out legitimate longs.
- **Pattern B (1 site — alert taxonomy alignment):** EOD Pass 2 short detection at `order_manager.py:~1734` already detects the short and logs ERROR (preserved by DEF-199 A1 fix; do-not-modify region `:1670-1750`). It does NOT need a filter — the detection is correct. It needs an additional `phantom_short` SystemAlertEvent emission so the alert taxonomy is consistent across all detection sites.

A reviewer reading "same pattern uniformly applied" might verify all 5 sites were patched with filters and miss that Pattern B's obligation is different. The reframe makes the divergent obligation explicit.

## Operator Decision Pre-Applied (Item 3 — MEDIUM #8 Disposition)

PHASE-D-OPEN-ITEMS Item 3: Health + broker-orphan double-fire dedup. Both 2b.1's `stranded_broker_long` alert and 2b.2's Health "Integrity Check FAILED" alert can fire for the same condition (broker-orphan long with no stop). Operator chose **Option C (hybrid)** before this session begins:

- Both alerts continue to fire (different cadences: 2b.1 fires per-reconciliation-cycle; Health check fires once daily).
- 2b.2's Health integrity check alert message includes a cross-reference: `"see also: stranded_broker_long alert active for this symbol since [timestamp]"` when the symbol has an active `stranded_broker_long` alert in HealthMonitor's state (queryable post-Session 5a.1) OR — for sessions before 5a.1 lands — in the `_broker_orphan_last_alerted_cycle` map directly.

For Session 2b.2's purposes (Sessions 5a.1/5a.2 haven't shipped yet), the cross-reference uses `OrderManager._broker_orphan_last_alerted_cycle.get(symbol)` to determine if a `stranded_broker_long` alert was emitted recently for the symbol. If yes, append the cross-reference text to the Health alert message. This is a temporary inter-session coupling; once Session 5a.1 ships, it can be re-pointed to HealthMonitor's queryable state — but per RULE-007, **do not re-point in this session**; that's Session 5a.1+ work.

## Objective

Apply **Pattern A** at four sites (margin circuit reset, Risk Manager max-concurrent #1, Risk Manager max-concurrent #2, Health integrity check) so that broker-state reads driving safety decisions count only LONG positions. Apply **Pattern B** at one site (EOD Pass 2 short detection) to emit the `phantom_short` alert alongside the existing `logger.error`. Apply Option C cross-reference at the Health integrity check.

After Session 2b.2 lands:
- Phantom shorts no longer inflate the margin-circuit reset count, the Risk Manager max-concurrent count, or the Health "missing stop" count — the side-blind reads are repaired.
- The `phantom_short` alert taxonomy fires from all three detection sites (reconciliation orphan, EOD Pass 2, Health integrity check) consistently.
- Session 5a.2's auto-resolution policy table can consume `phantom_short` alerts uniformly regardless of source.

## Requirements

### Pattern A — Count Filter (4 sites)

The pattern shape is the same at all four sites:

```python
# BEFORE (side-blind):
positions = await self._broker.get_positions()
count = len(positions)

# AFTER (side-aware, long-only):
positions = await self._broker.get_positions()
long_positions = [p for p in positions if p.side == OrderSide.BUY]
short_positions = [p for p in positions if p.side == OrderSide.SELL]
count = len(long_positions)
self._logger.info(
    "<site name> count check: longs=%d, shorts=%d, total_broker=%d, "
    "<threshold-or-action>",
    len(long_positions), len(short_positions), len(positions),
)
```

The `logger.info` "breakdown line" is required at all four sites — it's the operator's primary observability into "phantom shorts inflated the count by N" without needing to read the raw broker state.

#### Site A.1: Margin circuit reset (`order_manager.py:~1492`)

Existing logic resets the margin-circuit-breaker when broker-position count drops below `margin_circuit_reset_positions: 20`. Phantom shorts inflate the count, preventing the reset from firing.

Apply Pattern A. Breakdown log line:

```python
self._logger.info(
    "Margin circuit reset check: longs=%d, shorts=%d, "
    "reset_threshold=%d, will_reset=%s",
    len(long_positions), len(short_positions),
    self._config.account.margin_circuit_reset_positions,
    len(long_positions) < self._config.account.margin_circuit_reset_positions,
)
```

#### Site A.2: Risk Manager max-concurrent-positions site #1 (`risk_manager.py:335`)

Existing logic at `:335` rejects new entries when `len(positions) >= max_concurrent_positions`. Phantom shorts inflate the count, preventing legitimate longs.

Apply Pattern A. Breakdown log line on rejection path AND on the pass-through path. Specifically:

```python
positions = await self._broker.get_positions()
long_positions = [p for p in positions if p.side == OrderSide.BUY]
short_positions = [p for p in positions if p.side == OrderSide.SELL]
max_pos = self._config.account.max_concurrent_positions

self._logger.info(
    "Risk Manager max-concurrent #1 (entry gate): longs=%d, shorts=%d, "
    "max_concurrent=%d, would_reject=%s",
    len(long_positions), len(short_positions), max_pos,
    max_pos > 0 and len(long_positions) >= max_pos,
)

if max_pos > 0 and len(long_positions) >= max_pos:
    return OrderRejectedEvent(reason=f"Max concurrent positions ({max_pos}) reached")
```

**CRITICAL anti-regression note:** `risk_manager.py:335` line drift. The Phase A revisit findings document confirmed `:335` as the max-concurrent site (NOT Check 0). However, invariant 8's description in `regression-checklist.md` colloquially refers to "Risk Manager Check 0 around line 335" — this is mistaken attribution. **Verify at pre-flight that:**
- Line 335 area shows `len(positions) >= max_concurrent_positions` (max-concurrent check, in scope for 2b.2)
- Check 0 (`share_count <= 0` rejection) is at a different line (NOT in scope)

If the file has drifted such that line 335 IS Check 0 now, halt and reconcile.

#### Site A.3: Risk Manager max-concurrent-positions site #2 (`risk_manager.py:771`)

Same pattern as A.2, applied at the second max-concurrent site (likely a different code path — possibly a strategy-level check or a sibling guard). Verify the site by reading the surrounding context; the breakdown log line uses `"Risk Manager max-concurrent #2 ..."` to distinguish from #1 in operator logs.

#### Site A.4: Health daily integrity check (`health.py:443-450`) — HYBRID

This site is Pattern A with a hybrid extension: the side-aware count filter for the longs-without-stops detection, PLUS an alert routing decision (longs without stops → existing alert; shorts → `phantom_short` alert via 2b.1's taxonomy).

```python
# BEFORE (side-blind):
positions = await self._broker.get_positions()
positions_without_stop = [
    p for p in positions if not self._has_active_stop(p.symbol)
]
if positions_without_stop:
    self._emit_integrity_check_failed_alert(positions_without_stop)

# AFTER (Session 2b.2 Pattern A hybrid):
positions = await self._broker.get_positions()
long_positions = [p for p in positions if p.side == OrderSide.BUY]
short_positions = [p for p in positions if p.side == OrderSide.SELL]

# Longs without stops -> existing alert path (preserved)
longs_without_stop = [
    p for p in long_positions if not self._has_active_stop(p.symbol)
]

# Shorts -> phantom_short alert taxonomy (2b.1's alert type)
# These are by-construction phantom shorts; ARGUS is long-only by design.

self._logger.info(
    "Health integrity check: longs=%d (without_stop=%d), shorts=%d "
    "(all phantom by long-only design), total_broker=%d",
    len(long_positions), len(longs_without_stop),
    len(short_positions), len(positions),
)

# Pattern A hybrid — long-orphan branch with Option C cross-reference
if longs_without_stop:
    cross_ref_lines = []
    for pos in longs_without_stop:
        # Option C cross-reference (PHASE-D-OPEN-ITEMS Item 3)
        last_alerted_cycle = self._order_manager._broker_orphan_last_alerted_cycle.get(
            pos.symbol
        )
        if last_alerted_cycle is not None:
            cross_ref_lines.append(
                f"  - {pos.symbol}: see also stranded_broker_long alert "
                f"(last alerted at cycle {last_alerted_cycle})"
            )

    cross_ref_text = (
        "\n\nCross-reference (active stranded_broker_long alerts):\n"
        + "\n".join(cross_ref_lines)
        if cross_ref_lines else ""
    )
    self._emit_integrity_check_failed_alert(
        longs_without_stop, extra_message=cross_ref_text,
    )

# Phantom shorts -> phantom_short alert (Session 2b.1's taxonomy)
for pos in short_positions:
    alert = SystemAlertEvent(
        severity="critical",
        source="health.integrity_check",
        alert_type="phantom_short",
        message=(
            f"Health integrity check found broker-side short position for "
            f"{pos.symbol}: shares={pos.shares}. ARGUS is long-only by design."
        ),
        metadata={
            "symbol": pos.symbol,
            "shares": pos.shares,
            "side": "SELL",
            "detection_source": "health.integrity_check",
        },
    )
    self._event_bus.publish(alert)
```

**Notes on the Health hybrid:**
- The cross-reference reads `_broker_orphan_last_alerted_cycle` directly. This creates an inter-component coupling between Health and OrderManager that would normally be inappropriate; Sessions 5a.1+ replace it with a HealthMonitor active-alert query. For Session 2b.2's purposes, the direct read is acceptable per the Option C operator decision.
- The `_emit_integrity_check_failed_alert` helper may need a new `extra_message` parameter (or the cross-reference text may need to be appended to a fixed message field). Verify against the existing helper signature; per RULE-007, prefer extending the helper minimally over restructuring.
- The Pattern A breakdown log line in Health uses different field names (`without_stop`, `phantom`) because Health's vocabulary is different from OrderManager's. Match the existing Health idiom.

### Pattern B — Alert Taxonomy Alignment (1 site)

#### Site B.1: EOD Pass 2 short detection (`order_manager.py:~1734`)

The existing detection at `:1734` (within the do-not-modify region `:1670-1750` for the A1 fix logic, but `:~1734` is the alert-emission line which IS modifiable per spec — verify by inspection that the line you're modifying is OUTSIDE the protected logic block) already logs `ERROR "DETECTED UNEXPECTED SHORT POSITION"`. The detection is correct. Add an additional `phantom_short` SystemAlertEvent emission alongside the existing logger.error:

```python
# BEFORE:
self._logger.error("DETECTED UNEXPECTED SHORT POSITION: %s shares=%d", ...)

# AFTER (Session 2b.2 Pattern B — alert taxonomy alignment):
self._logger.error("DETECTED UNEXPECTED SHORT POSITION: %s shares=%d", ...)
# NEW: emit phantom_short alert for taxonomy consistency with
# reconciliation orphan branch (2b.1) and Health integrity check (2b.2 A.4).
# Sessions 5a.2's auto-resolution policy table consumes alerts by taxonomy,
# not by source — all three detection sites must produce the same alert type.
alert = SystemAlertEvent(
    severity="critical",
    source="eod_flatten",
    alert_type="phantom_short",
    message=(
        f"EOD Pass 2 detected unexpected short position for {symbol}: "
        f"shares={shares}. Will not place flatten SELL (DEF-199 A1 protected)."
    ),
    metadata={
        "symbol": symbol,
        "shares": shares,
        "side": "SELL",
        "detection_source": "eod_flatten.pass2",
    },
)
self._event_bus.publish(alert)
```

**CRITICAL: do not modify the DEF-199 A1 fix.** The detection logic block at `:1670-1750` is do-not-modify. The alert emission ADDED by Session 2b.2 must be at a line outside that range — likely at `:~1734` if the existing `logger.error` is itself inside the protected block, the alert emission must be relocated to immediately after the block or the existing emission line must be confirmed outside `:1670-1750`. **At pre-flight, verify the exact line of the existing `logger.error` you'll be augmenting and confirm it's NOT inside `:1670-1750`.**

If the only `logger.error("DETECTED UNEXPECTED SHORT POSITION...")` line IS inside `:1670-1750`, halt and escalate — the spec needs amendment to specify whether the new alert emission goes immediately after the block or in a different post-detection hook.

## Requirements (Summary Checklist)

- [ ] Pattern A applied at A.1 (margin circuit reset)
- [ ] Pattern A applied at A.2 (Risk Manager max-concurrent #1, line 335)
- [ ] Pattern A applied at A.3 (Risk Manager max-concurrent #2, line 771)
- [ ] Pattern A hybrid applied at A.4 (Health integrity check) WITH Option C cross-reference reading `_broker_orphan_last_alerted_cycle`
- [ ] Pattern B applied at B.1 (EOD Pass 2 short detection) — alert emission OUTSIDE the `:1670-1750` do-not-modify region
- [ ] Each site has a `logger.info` breakdown line with site-specific naming
- [ ] No edits to `:1670-1750` (DEF-199 A1 fix)
- [ ] No edits to Risk Manager Check 0 (`share_count <= 0` rejection — locate via grep, distinct from `:335` max-concurrent)
- [ ] No edits to `argus/main.py`, `argus/models/trading.py`, `argus/execution/alpaca_broker.py`, `argus/data/alpaca_data_service.py`, `argus/execution/ibkr_broker.py`, `argus/execution/broker.py`, `docs/sprints/sprint-31.9/IMPROMPTU-04-closeout.md`, `workflow/`

## Tests (~9 new pytest, grouped by pattern)

### Pattern A — Count-Filter Tests (8)

1. **`test_margin_circuit_reset_uses_longs_only`**
   - Setup: 18 long positions + 5 short positions at broker; `margin_circuit_reset_positions: 20`.
   - Assert: margin circuit RESETS (because `len(longs)=18 < 20`); without the fix, `len(positions)=23` would block reset.

2. **`test_margin_circuit_reset_logs_breakdown`**
   - Setup as Test 1.
   - Assert: log capture contains `"longs=18, shorts=5, reset_threshold=20, will_reset=True"`.

3. **`test_risk_manager_max_concurrent_positions_uses_longs_only_335`**
   - Setup: 49 long + 5 short positions; `max_concurrent_positions: 50`.
   - Trigger Risk Manager entry-gate check at `:335`.
   - Assert: entry NOT rejected (longs=49 < 50); without fix, total=54 would reject.

4. **`test_risk_manager_max_concurrent_positions_uses_longs_only_771`**
   - Same pattern as Test 3 but exercising the second max-concurrent site at `:771`.

5. **`test_risk_manager_phantom_shorts_dont_consume_position_cap`** (B5 regression test)
   - Setup: 0 long + 50 short positions (extreme case — all phantom shorts); `max_concurrent_positions: 50`.
   - Trigger entry gate at `:335`.
   - Assert: entry NOT rejected (longs=0 < 50). The 50 phantom shorts should not block the next legitimate long.
   - Same pattern at `:771`.

6. **`test_health_integrity_check_long_orphan_no_stop_emits_existing_alert`**
   - Setup: 1 long position without stop, 0 shorts.
   - Trigger daily integrity check.
   - Assert: existing `_emit_integrity_check_failed_alert` fires with the long; NO `phantom_short` alert (because there are no shorts).

7. **`test_health_integrity_check_short_routes_to_phantom_short_alert`**
   - Setup: 0 longs, 1 short position.
   - Trigger daily integrity check.
   - Assert: `phantom_short` `SystemAlertEvent` with `source="health.integrity_check"` published; NO `_emit_integrity_check_failed_alert` fires (because there are no longs without stops).

8. **`test_health_integrity_check_log_breakdown_longs_protected_shorts_phantom`**
   - Setup: 3 longs (2 with stops, 1 without), 2 shorts.
   - Trigger.
   - Assert: log line `"longs=3 (without_stop=1), shorts=2 (all phantom by long-only design)..."`.

### Pattern B — Alert-Alignment Test (1)

9. **`test_eod_pass2_short_detection_emits_phantom_short_alert_alongside_existing_logger_error`**
   - Setup: trigger EOD Pass 2 with a phantom short.
   - Assert: existing `logger.error("DETECTED UNEXPECTED SHORT POSITION ...")` fires (preserved behavior).
   - Assert: `phantom_short` `SystemAlertEvent` with `source="eod_flatten"` published.
   - Assert: the SELL is NOT placed (DEF-199 A1 fix preserved).
   - Assert: `:1670-1750` shows zero `git diff`.

### Option C cross-reference verification (folded into Test 6 + a new mini-test)

10. **(implicit, within Test 6 expansion or as Test 9.5)** `test_health_integrity_check_long_orphan_with_active_stranded_alert_includes_cross_reference`
    - Setup: long orphan AAPL without stop; OrderManager has `_broker_orphan_last_alerted_cycle["AAPL"] = 6`.
    - Trigger Health integrity check.
    - Assert: the integrity check alert message contains the cross-reference text `"see also stranded_broker_long alert (last alerted at cycle 6)"` for AAPL.

## Definition of Done

- [ ] All 4 Pattern A sites use long-only filter; all 4 emit breakdown log lines.
- [ ] Pattern B EOD Pass 2 site emits `phantom_short` alert alongside `logger.error`; A1 fix preserved.
- [ ] Health integrity check side-aware (Pattern A hybrid): longs → existing alert (with Option C cross-reference if applicable); shorts → `phantom_short` alert.
- [ ] All 9 (+1 cross-reference) tests pass.
- [ ] Test 5 (B5 regression test, phantom shorts don't lock out longs) passes — the foundational anti-regression.
- [ ] CI green (scoped suite); pytest baseline ≥ 5,128.
- [ ] All do-not-modify list items show zero `git diff`.
- [ ] Tier 2 review verdict CLEAR.
- [ ] Close-out report at `docs/sprints/sprint-31.91-reconciliation-drift/session-2b.2-closeout.md`.

## Close-Out Report

Standard structure. Verdict JSON:

```json
{
  "session": "2b.2",
  "verdict": "PROPOSED_CLEAR",
  "tests_added": 9,
  "tests_total_after": <fill>,
  "files_modified": [
    "argus/execution/order_manager.py",
    "argus/core/risk_manager.py",
    "argus/core/health.py",
    "<test files>"
  ],
  "donotmodify_violations": 0,
  "tier_3_track": "side-aware-reconciliation",
  "operator_decisions_applied": ["Item 3 / Option C (hybrid double-fire with cross-reference)"]
}
```

Add a note in "Discovered Edge Cases" specifically calling out:
- Whether `risk_manager.py:335` was confirmed as max-concurrent (in scope) vs Check 0 (out of scope) at pre-flight; cite the actual Check 0 line for the reviewer's clarity.
- Whether the EOD Pass 2 alert emission landed inside vs outside `:1670-1750`. Cite the exact line.

## Tier 2 Review Invocation

Standard pattern. Backend safety reviewer template. Review report at `docs/sprints/sprint-31.91-reconciliation-drift/session-2b.2-review.md`.

## Session-Specific Review Focus (for @reviewer)

1. **Pattern recognition.** This is the central reviewer focus per the third-pass HIGH #2 reframe. Read each site's diff and confirm:
   - The 4 Pattern A sites use long-only filter + breakdown log line.
   - The 1 Pattern B site emits the `phantom_short` alert alongside (NOT replacing) the existing `logger.error`.
   - No Pattern A site is missing the filter; no Pattern B site silently became filter-only.

2. **B5 regression test (Test 5) verifies the structural fix.** Run it explicitly. This is the test that demonstrates the pre-fix behavior would have locked out legitimate longs.

3. **Alert taxonomy consistency** (cross-session). Compare three alert emissions:
   - Session 2b.1: `_handle_broker_orphan_short` → `alert_type="phantom_short", source="reconciliation"`
   - Session 2b.2 A.4 (Health hybrid): `alert_type="phantom_short", source="health.integrity_check"`
   - Session 2b.2 B.1 (EOD Pass 2): `alert_type="phantom_short", source="eod_flatten"`

   All three must produce alerts that Session 5a.2's auto-resolution policy table consumes uniformly (auto-resolution predicate keyed on `alert_type`, not `source`). Reviewer confirms the metadata payloads have the same shape (symbol, shares, side, detection_source).

4. **`:1670-1750` zero edits.** This is the most important do-not-modify check this session. The B.1 alert emission must be at a line outside this range. Reviewer reads the diff line numbers and verifies.

5. **Risk Manager Check 0 untouched.** Per invariant 8, the `share_count <= 0` rejection logic must be unchanged. Reviewer locates the Check 0 line (distinct from the `:335` max-concurrent line) and verifies zero edits.

6. **Health double-fire cross-reference (Option C, MEDIUM #8).** Read the Health alert message construction. Confirm:
   - When a long orphan has an active `stranded_broker_long` alert in `_broker_orphan_last_alerted_cycle`, the cross-reference text is appended.
   - When no active alert exists, the cross-reference text is empty (no spurious "active stranded_broker_long" line).
   - The coupling to `OrderManager._broker_orphan_last_alerted_cycle` is acknowledged in a code comment as inter-session-temporary, with a TODO to migrate to HealthMonitor's active-alert query post-Session 5a.1.

7. **Pattern A breakdown log lines are operator-readable.** Sample the log output during Test 8; confirm the breakdown line is human-parseable at first glance ("longs=3 (without_stop=1), shorts=2..."). The breakdown is the operator's primary observability into "phantom shorts inflated this count by N."

## Sprint-Level Regression Checklist (for @reviewer)

- **Invariant 1 (DEF-199 A1 fix detects + refuses 100% of phantom shorts at EOD):** PASS — `:1670-1750` zero edits. Test 9 verifies the A1 fix is preserved alongside the new alert emission.
- **Invariant 5:** PASS — expected ≥ 5,128 (entry baseline 5,119 + 9 new tests).
- **Invariant 8 (Risk Manager Check 0 unchanged):** PASS — `risk_manager.py` modifications are scoped to `:335` and `:771` (max-concurrent sites); Check 0 is at a different line (cite in close-out).
- **Invariant 10 (DEC-367 margin circuit unchanged):** PASS at the *behavior* level; the margin-circuit reset *threshold check* is now side-aware (Pattern A.1), but the circuit-breaker engagement logic is untouched. Reviewer verifies via reading the diff.
- **Invariant 14:** Row "After Session 2b.2" — Recon detects shorts = "partial + side-aware reads (4 filter + 1 alert-align)".
- **Invariant 15:** PASS — verify list.

## Sprint-Level Escalation Criteria (for @reviewer)

- **A2** (Tier 2 CONCERNS or ESCALATE).
- **A6** (B5 regression test 5 fails — would mean the structural fix didn't actually fix the structural bug).
- **B1, B3, B4, B6** — standard halt conditions.
- **C5** (uncertain whether a change crosses a do-not-modify boundary) — `:1670-1750` is the primary high-risk site; the EOD Pass 2 alert emission line is the closest to that boundary in this session.
- **C7** (existing test fails for a behavioral reason that wasn't anticipated) — most likely if the Pattern A breakdown log lines are picked up by an existing log-line snapshot test.

---

*End Sprint 31.91 Session 2b.2 implementation prompt.*

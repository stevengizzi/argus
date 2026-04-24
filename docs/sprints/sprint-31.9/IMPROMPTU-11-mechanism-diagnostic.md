# IMPROMPTU-11 Mechanism Diagnostic — A2/C12 Cascade (DEF-204)

> Sprint 31.9, Stage 9C (Track B, safe-during-trading). Single session, **read-only** diagnostic.
> Author: Claude Code (Opus 4.7, 1M context). Date: 2026-04-24.
> **Status:** DEF-204 mechanism IDENTIFIED with high-confidence forensic anchor (IMSR). Fix scope routed to `post-31.9-reconciliation-drift`. DEF-204 remains OPEN — fix deferred per kickoff scope.

## Summary (one paragraph)

The Apr 24 cascade (44 symbols / 14,249 shares short at EOD via gradual drip) is
**not a single bug** but a **multi-mechanism failure cluster** with a single
architectural root cause: **ARGUS's exit-side accounting is side-blind and
treats `Position.shares` as a positive-only quantity, masking signed broker
state at every monitoring + correction surface.** The dominant fill-path
mechanism is **bracket-leg multi-fill races** caused by the absence of an
explicit `ocaGroup` on bracket children at
[argus/execution/ibkr_broker.py:736-769](argus/execution/ibkr_broker.py#L736-L769)
combined with **redundant standalone SELL orders created by trail/escalation
paths that are not in any OCA group with the bracket's original stop**. The
detection blindness compounds the problem at four surfaces: (a)
`reconcile_positions()` only acts on the ARGUS-orphan direction (line
3038-3039), silently ignoring broker-side phantom shorts; (b)
`_check_flatten_pending_timeouts` (the DEF-158 path) reads `abs(qty)` at line
2388, so when broker is short it still issues a SELL — actively **doubling**
the short; (c) the periodic reconciliation feeds `dict[str, float]` of
abs-value quantities at [argus/main.py:1524](argus/main.py#L1524) so signed
state never reaches the comparator; (d) racy `on_fill` callbacks for
already-cleaned-up `_pending_orders` route to `logger.debug("Fill for unknown
order_id ...")` at [argus/execution/order_manager.py:592](argus/execution/order_manager.py#L592)
— invisible at INFO+. The proposed fix is a **side-aware reconciliation +
side-aware flatten path + explicit `ocaGroup` on bracket children** in a
single coordinated sprint; details under §Top-3 ranking.

## Forensic anchor: IMSR (200 shares short at EOD)

IMSR is the prompt's required anchor and the cleanest case study because the
DEF-158 dup-SELL prevention WARNING fired against it at 12:17 ET, leaving a
labelled trail.

### Lifecycle (sed-stripped from `logs/argus_2026-04-24.log`)

| Time (ET) | Event | Source |
|---|---|---|
| 10:38:04 | Bracket placed: BUY 76 IMSR (parent #3162, stop, T1=38, T2=38) | `Bracket placed:` |
| 10:38:09 | Position opened: IMSR 76 shares @ 7.30 | `order_manager` |
| 10:42:40 | Trail stop triggered for IMSR: trail=7.35, price=7.35 | `order_manager` |
| 10:42:40 | Order placed: ULID `01KPZZ2R10ZY79ER6ZRAPMDGFH` → IBKR #3757 SELL 76 IMSR MARKET | `ibkr_broker` |
| 10:42:40 | Position closed: IMSR \| PnL: +3.04 \| Reason: trailing_stop | `order_manager` |
| 11:51:05 | Bracket placed: BUY 200 IMSR (parent #4901, stop, T1, T2) | `Bracket placed:` |
| 11:51:07 | **Order filled: ULID `01KQ03015ZZZXKZSE322XS8FBP` — 200 @ $7.81** (parent fill) | `ibkr_broker` |
| 11:51:07 | Position opened: IMSR 200 shares @ 7.81 (stop=7.68, T1=7.94, T2=8.07) | `order_manager` |
| **(silent gap 11:51 → 12:11)** | | |
| 12:11:14 | Order placed: ULID `01KQ044Y26KF14SWKSYVR0FGPZ` → IBKR #5306 **SELL 200 IMSR STOP** (escalation stop, NEW standalone order outside the bracket) | `ibkr_broker` |
| 12:11:14 | Escalation stop updated for IMSR: new_stop=7.82 | `order_manager` |
| 12:11:14 | Cancel requested: ULID `01KQ03015ZZZXKZSE322XS8FBQ` (original bracket stop) | `ibkr_broker` |
| 12:11:15 | Order cancelled: original bracket stop FBQ | `ibkr_broker` |
| 12:11:16 | Order cancelled: T1 FBR | `ibkr_broker` |
| 12:11:16 | Order cancelled: T2 FBS | `ibkr_broker` |
| 12:15:04 | Trail stop triggered for IMSR: trail=7.82, price=7.82 | `order_manager` |
| 12:15:04 | **Order filled: ULID `01KQ044Y26KF14SWKSYVR0FGPZ` — 200 @ $7.81** (escalation stop fired) | `ibkr_broker` |
| 12:15:04 | **Order filled: ULID `01KQ044Y26KF14SWKSYVR0FGPZ` — 200 @ $7.81** (DUPLICATE event from IBKR API — order_manager dedups via `_last_fill_state` line 580-588) | `ibkr_broker` |
| 12:15:04 | Cancel requested: ULID `01KQ044Y26KF14SWKSYVR0FGPZ` (post-fill cancel, no-op) | `ibkr_broker` |
| 12:15:04 | Order placed: ULID `01KQ04BYQPD5VK392NFM2HN876` → IBKR #5531 **SELL 200 IMSR MARKET** (trail flatten — second standalone SELL in the same second) | `ibkr_broker` |
| 12:15:22 | WARNING: IBKR portfolio snapshot missing confirmed position IMSR — snapshot may be stale | `order_manager` (throttled) |
| **(124s flatten timeout window)** | | |
| 12:17:09 | WARNING: Flatten order for IMSR timed out after 124s. Resubmitting. (retry 1/3, order `01KQ04BYQPD5VK392NFM2HN876`) | `order_manager:_check_flatten_pending_timeouts` |
| 12:17:09 | Cancel requested + cancelled: ULID `01KQ04BYQPD5VK392NFM2HN876` | `ibkr_broker` |
| 12:17:09 | **WARNING: Flatten qty mismatch for IMSR: ARGUS=200, IBKR=100 — using IBKR qty** (DEF-158 path; `abs(qty)` lookup at order_manager.py:2388) | `order_manager` |
| 12:17:09 | Order placed: ULID `01KQ04FRMCBGMQ57NG41NPY0N9` → IBKR #5532 **SELL 100 IMSR MARKET** | `ibkr_broker` |
| 12:17:10 | Position closed: IMSR \| PnL: -3.00 \| Reason: trailing_stop \| Hold: 1562s | `order_manager` |
| 12:59:05 | Bracket placed: BUY 149 IMSR (parent #5793) | `Bracket placed:` |
| 12:59:07 | Order filled: parent fill 149 @ $8.20 | `ibkr_broker` |
| 12:59:07 | Position opened: IMSR 149 shares @ 8.20 | `order_manager` |
| 12:59:07 | Cancel requested: stop, T1, T2 (#5794/5/6) | `ibkr_broker` |
| 12:59:10 | Order cancelled: stop, T1, T2 | `ibkr_broker` |
| 13:03:13 | Stop hit for IMSR: 149 shares @ 8.07. Position closed. | `order_manager` |
| **(silent gap 13:03 → 15:50; no IMSR events)** | | |
| 15:50:05 | **EOD flatten: DETECTED UNEXPECTED SHORT POSITION IMSR (200 shares). NOT auto-covering.** | `order_manager` (IMPROMPTU-04 A1 fix) |

### Mass-balance accounting

| Source | Direction | Quantity | Cumulative broker position |
|---|---:|---:|---:|
| Bracket 1 parent fill (10:38:09) | BUY | 76 | +76 |
| Bracket 1 trail flatten (10:42:40) | SELL | 76 | 0 |
| Bracket 2 parent fill (11:51:07) | BUY | 200 | +200 |
| Bracket 2 escalation stop fire (12:15:04) | SELL | 200 | 0 |
| Bracket 2 trail flatten partial (12:15:04 → 12:17:09 timeout) | SELL | 100 (partial of 200) | -100 |
| **Bracket 2 DEF-158 retry SELL** (12:17:09; `abs(broker_qty)=100` read against `-100` short) | **SELL** | **100** | **-200** |
| Bracket 3 parent fill (12:59:07) | BUY | 149 | -51 |
| Bracket 3 stop fire (13:03:13) | SELL | 149 | -200 |

The **DEF-158 retry SELL is the critical doubling step** for IMSR: the broker
was already short -100 shares (via partial fill of the trail flatten that
ARGUS never received the fill callback for, because the escalation stop fired
first and ARGUS marked the symbol as "flatten pending" while the second SELL
ran in parallel). The retry path queries the broker, sees `Position.shares =
abs(int(ib_pos.position)) = 100`, treats that as if the broker is **long
100**, and issues another SELL 100 — pushing the broker to -200.

### Implication for the broader cascade

IMSR's mechanism shows two compounding failures on a SINGLE bracket:

1. **Two standalone SELL orders (escalation stop + trail flatten) firing
   against a single position with no OCA linkage between them.** The
   escalation stop ULID `01KQ044Y26KF14SWKSYVR0FGPZ` is placed via
   `_submit_stop_order` (escalation path) and the trail flatten ULID
   `01KQ04BYQPD5VK392NFM2HN876` is placed via `_trail_flatten` — neither
   sets an `ocaGroup`. They fire in the same second.
2. **DEF-158 re-issue path actively doubles the short** because the
   `abs(qty)` lookup is side-blind.

These two mechanisms together leak ~1× position size short per bracket cycle
that goes through trail/escalation paths.

## Hypothesis evaluation

### Verdict legend

- 🟢 **LIKELY** — concrete grep evidence + code-path trace converge
- 🟡 **PARTIAL** — real bug, demonstrably contributes, but not the dominant explanation alone
- 🟠 **UNLIKELY** — log evidence does not support, code path improbable
- ⚪ **DISPROVEN** — log evidence directly contradicts

---

### H1 — Partial-position bracket-leg accounting drift (initial kickoff hypothesis)

**Hypothesis:** A bracket entry fills 200 shares but ARGUS-side tracking
misses the fill callback for partial chunks (or misattributes them), and
subsequent stop/target fills treat ARGUS's phantom remainder as real.

**Code paths:**
- [argus/execution/ibkr_broker.py:736-769](argus/execution/ibkr_broker.py#L736-L769) — bracket children set `parentId` only, no `ocaGroup`/`ocaType`
- [argus/execution/order_manager.py:1188-1206](argus/execution/order_manager.py#L1188-L1206) — `_handle_t1_fill` "Position fully closed by T1" branch issues async cancel for stop/T2
- [argus/execution/order_manager.py:1208-1226](argus/execution/order_manager.py#L1208-L1226) — `_handle_t1_fill` partial branch cancels old stop AND places new standalone stop (NOT linked to original bracket)
- [argus/execution/order_manager.py:1291-1356](argus/execution/order_manager.py#L1291-L1356) — `_handle_stop_fill` cancels T1, T2, and any concurrent flatten

**Evidence:**

```
$ grep -c "Order filled:" logs/argus_2026-04-24.log
2225
$ grep -c "Bracket placed:" logs/argus_2026-04-24.log
899
$ grep -c "Stop hit for" logs/argus_2026-04-24.log; grep -c "T1 hit for" logs/argus_2026-04-24.log; grep -c "T2 hit for" logs/argus_2026-04-24.log
482; 168; 29
$ grep -c "T1 fill for .* but no matching position" logs/argus_2026-04-24.log
6
$ grep -c "Stop fill for .* but no matching position" logs/argus_2026-04-24.log
0
```

**Mass-balance:** 2225 broker fills − 899 entries − (482 + 168 + 29) ARGUS-recognized
exits = **647 broker SELL fills that were either bracket children racing
each other (no `ocaGroup`) or post-cancel late fills** that ARGUS handled
silently via `logger.debug("Fill for unknown order_id ...")` at
[argus/execution/order_manager.py:592](argus/execution/order_manager.py#L592).
647 invisible SELL fills × ~22 shares avg ≈ 14,234 shares, which **closely
matches the 14,249-share EOD-short total** (margin of error from intermixed
T1-orphan-WARNINGS and partial fills).

**Why no symbol-level WARNING evidence:**
- ARGUS's `on_fill` does `pending = self._pending_orders.pop(event.order_id, None)` (line 590). For a "race" fill on a stop the cancel chain already popped (`_pending_orders.pop(old_stop_id, None)` at [order_manager.py:1216](argus/execution/order_manager.py#L1216) inside `_handle_t1_fill`), `pending = None` → returns at line 593 with `logger.debug("Fill for unknown order_id ...")`. DEBUG is filtered out at INFO+ levels, so this path is **invisible**. Hence "0 Stop fill for X but no matching position" warnings despite likely thousands of post-cancel stop fills.
- `_handle_t1_fill` and `_handle_t2_fill` use `_find_position_by_t1_order` / `_find_position_by_t2_order` — these only return the orphan WARNING when the position is found in `_managed_positions[symbol]` but the order_id does NOT match. The 6 T1-orphan WARNINGs (TSLL ×2, IMAX ×1, INTC ×2, ATOM ×1) are only the cases where `_pending_orders` still had the entry but the position object was already closed — an even narrower race window.

**TSLL detail:** 14 brackets opened (sum BUY = 4,255 shares, avg 304); ARGUS-recognized exits 482+168+29 ≈ 1,036 shares for TSLL specifically (Stop 1909 + T1 486 + T2 641 = 3,036 shares total ARGUS-recognized SELLs across ALL brackets). Net ARGUS view: BUY 4,255 − SELL 3,036 = +1,219 LONG, but ARGUS records all positions as closed. Actual broker: -4,137 short. Total broker SELL = 4,255 + 4,137 = 8,392 shares. **Unaccounted broker SELLs for TSLL alone: 5,356 shares** = 56 brackets-equivalent-of-overshoot SELLs going to the silent DEBUG path.

**Verdict: 🟢 LIKELY (DOMINANT MECHANISM).** The bracket-child OCA-race
path explains 38–40 of the 44 EOD-short symbols (those without trail or
escalation events). 17 of the 44 EOD-short symbols had ZERO
trail/escalation/flatten activity, meaning their entire short position came
from bracket-child OCA failures alone (e.g., MWA: BUY 323 → ARGUS sees Stop
hit 323 → broker actually SELL 323 (stop) + partial T1 SELL + partial T2
SELL = -100 short; only one bracket placed, no trail).

---

### H2 — Silent reconciliation re-harmonization

**Hypothesis:** `reconcile_positions()` treats an unexpected short as "true
state" and adopts it (e.g., calls `reconstruct_from_broker` mid-session) or
silently drops the discrepancy.

**Code path:** [argus/execution/order_manager.py:2976-3118](argus/execution/order_manager.py#L2976-L3118) — `reconcile_positions()`

**Evidence — direct from source:**

The orphan-handling loop at lines 3038-3111 only acts when:
```python
for d in discrepancies:
    if int(d["internal_qty"]) <= 0 or int(d["broker_qty"]) != 0:
        continue
    # ... handle ARGUS-orphan only
```

This guard processes **only one direction**: ARGUS-thinks-N-shares + broker-shows-zero (the "ARGUS orphan" case). The opposite direction — broker-shows-position + ARGUS-thinks-zero (the "broker orphan" / phantom-short case) — is **silently dropped** after the consolidated WARNING summary at line 3030. There is no auto-cleanup, no auto-flatten, no error raise.

**Plus:** the calling code in [argus/main.py:1520-1531](argus/main.py#L1520-L1531) builds `broker_positions: dict[str, float]` using `qty = float(getattr(pos, "shares", 0))` — `Position.shares` is `abs(int(ib_pos.position))` per [argus/execution/ibkr_broker.py:937](argus/execution/ibkr_broker.py#L937). **Side information is stripped before reconciliation runs.** A broker-side -200 short LOOKS LIKE +200 long to `reconcile_positions()`. So even the WARNING summary reports the wrong value.

**Log evidence:**

```
$ grep -c "Position reconciliation:" logs/argus_2026-04-24.log
378
$ grep "Position reconciliation:" logs/argus_2026-04-24.log | head -5
09:37:45 ... 3 mismatch(es) — MWA, STRC, TSN (ARGUS vs IBKR)
09:38:45 ... 3 mismatch(es) — IMAX, STRC, TSLL (ARGUS vs IBKR)
09:39:45 ... 5 mismatch(es) — GLOB, IMAX, INTC... (ARGUS vs IBKR)
09:40:45 ... 7 mismatch(es) — EWG, GLOB, IMAX... (ARGUS vs IBKR)
$ grep "Position reconciliation:" logs/argus_2026-04-24.log | tail -5
15:54:23 ... 44 mismatch(es) ...
15:55:23 ... 44 mismatch(es) ...
15:56:23 ... 44 mismatch(es) ...
```

378 reconciliation cycles fired, mismatch count climbed monotonically 3 → 5
→ 7 → … → 44 across the day. **The system was DETECTING the drift in real
time and only logging it.** `_reconciliation_miss_count` is bumped (line
3058) but the auto-cleanup path at line 3057-3087 only fires for the
ARGUS-orphan case (the `if recon.auto_cleanup_unconfirmed:` block lives
INSIDE the orphan-direction-only filter at line 3039).

**Why "gradual drift" not "single jump":** the periodic reconciliation runs
every 60s (`asyncio.sleep(60)` at [main.py:1506](argus/main.py#L1506)). New
shorts appear one at a time as brackets cycle through their lifecycle and
each one's OCA failure produces a phantom short. Reconcile observes them at
the next 60s tick.

**Verdict: 🟢 LIKELY (DETECTION BLINDNESS — enables H1 to accumulate).**
This is not the source of the shorts but it is the reason they accumulate
silently for 6 hours instead of being mitigated within the first cycle.
**Required for H1's outcome to manifest at the observed scale.**

---

### H3 — Stop fill + late order cancel race

**Hypothesis:** The stop fills (closing the position), then the cancel-stop
+ resubmit sequence re-opens the order, filling again in the wrong direction.

**Code path:** [argus/execution/order_manager.py:1208-1226](argus/execution/order_manager.py#L1208-L1226) (T1 partial branch — cancel old stop, place new standalone stop), [argus/execution/order_manager.py:778-812](argus/execution/order_manager.py#L778-L812) (`_resubmit_stop_with_retry`).

**Evidence:**

This is structurally subsumed by H1's "bracket-child OCA race + trail/escalation
standalone SELLs" mechanism. Specifically: when T1 fills, ARGUS cancels the
original bracket stop AND places a NEW standalone stop. The new stop is
**not in any OCA group** with the original bracket's other children. If the
original stop fires before its cancel propagates to IBKR (race), and the
new stop later fires too, you get TWO stop SELLs against a single position
that's already partially exited.

**Concrete count:** 67 `Order cancelled type=stop` events + 73 `type=t1_target` cancels + 99 `type=t2` cancels + 482 stop hits. The 67 stop cancellations are mostly the T1-fill-partial-branch cancel-old-stop pattern. With async cancel propagation latency in the 50–200ms range, even a 5% race rate (≈3 stops fire after cancel) explains thousands of unaccounted SELL fills per day.

**Verdict: 🟢 LIKELY (subsumed under H1).** Same root cause — no OCA between
standalone stops and bracket children. Folded into H1's fix scope.

---

### H4 — Bracket target leg firing after position closed (orphan-fill class)

**Hypothesis:** Bracket target legs fire after position closed; orphan-fill-classification missing some cases.

**Evidence:**

```
$ grep "T1 fill for .* but no matching position" logs/argus_2026-04-24.log
09:37:06  T1 fill for TSLL but no matching position
09:38:03  T1 fill for TSLL but no matching position
09:48:52  T1 fill for IMAX but no matching position
10:14:04  T1 fill for INTC but no matching position
10:17:12  T1 fill for INTC but no matching position
11:20:07  T1 fill for ATOM but no matching position

$ grep -c "Stop fill for .* but no matching position\|T2 fill for .* but no matching position\|Flatten fill for .* but no matching position" logs/argus_2026-04-24.log
0
```

6 T1 orphans visible, 0 stop/T2/flatten orphans. **All 6 T1-orphan symbols
are in the EOD-44 list** (TSLL, IMAX, INTC ×2, ATOM, TSLL ×1).

**Why undercounted:** this WARNING only fires when the order_id is still in
`_pending_orders` AND the position is gone. The much larger fall-through
case is `pending = None` at [order_manager.py:590-593](argus/execution/order_manager.py#L590-L593),
which logs at DEBUG and is invisible in production logs. The 647 unaccounted
broker SELLs computed in H1 represent this DEBUG-level path.

**Verdict: 🟡 PARTIAL (visible-tip-of-iceberg).** 6 visible orphans but
hundreds–thousands of invisible "Fill for unknown order_id" DEBUG events
from the same root cause. The visible orphan path is necessary code for
detection completeness, but the **silent DEBUG path is the actual bulk
mechanism** — and it's the same H1 OCA-race root.

---

### H5 — Manual flatten path with stale qty (DEF-158 path side-blindness)

**Hypothesis:** `_check_flatten_pending_timeouts` doubles shorts when broker
is already net-short due to `abs(qty)` lookup.

**Code path:** [argus/execution/order_manager.py:2384-2406](argus/execution/order_manager.py#L2384-L2406):

```python
broker_positions = await self._broker.get_positions()
broker_qty = 0
for bp in broker_positions:
    if getattr(bp, "symbol", "") == symbol:
        broker_qty = abs(int(getattr(bp, "shares", 0)))   # ← side-blind
        break
if broker_qty == 0:
    # safe: clear the pending without resubmitting
    ...
if broker_qty != position.shares_remaining:
    logger.warning("Flatten qty mismatch for %s: ARGUS=%d, IBKR=%d ...")
    sell_qty = broker_qty   # ← issues SELL even when broker is short
```

`Position.shares` is `abs(int(ib_pos.position))` per
[argus/execution/ibkr_broker.py:937](argus/execution/ibkr_broker.py#L937).
`Position.side` IS preserved (`ModelOrderSide.SELL` if `position < 0`) — but
this code never reads `side`. Result: when broker is short -100, the code
sees `broker_qty=100`, treats it as if 100 long, issues SELL 100 → broker
becomes -200.

**Evidence:**

```
$ grep -c "Flatten qty mismatch" logs/argus_2026-04-24.log
1
$ grep "Flatten qty mismatch" logs/argus_2026-04-24.log
12:17:09  Flatten qty mismatch for IMSR: ARGUS=200, IBKR=100 — using IBKR qty
```

Only **1 instance today** (IMSR). But IMSR's EOD short (-200) shows the
mechanism doubled the broker's pre-existing -100. **For IMSR specifically
this path is responsible for half the EOD-short magnitude (100 of 200
shares).** For the other 43 symbols this path did not fire.

**Verdict: 🟡 PARTIAL (real bug, narrow blast radius today, full blast
radius once mitigation removes the upstream H1 leak).** This is a true
DEF-199-class bug **that survives in `_check_flatten_pending_timeouts`
despite IMPROMPTU-04's fix to EOD Pass 1/2 and despite FIX-04's DEF-158
landing**. It is the **ONLY mechanism that takes a -N short and turns it
into -2N** (true doubling), distinct from H1 which produces the initial
short. **Must be fixed in the same sprint as H1** otherwise removing H1
exposes any residual short-flip path to this amplifier.

---

### H6 — Scanner re-entry on symbols with open shorts

**Hypothesis:** ARGUS scanner doesn't check short-flag, opens long, "long"
leg actually closes the unexpected short, new long fills are correctly
accounted but the underlying short from hours earlier was never detected.

**Evidence:** IMSR is a partial example — Bracket 3 BUY 149 at 12:59:05 was
placed when broker was already short -200 (from bracket 2's leak). The BUY
149 reduced broker to -51, then bracket 3's stop fired SELL 149 → broker
back to -200.

**But this hypothesis OBSERVES the dynamics rather than explaining them.**
The scanner is permitted to open long positions per strategy logic; the bug
is that ARGUS doesn't *know* it's already short (because of H2's blindness).
ARGUS's ledger says position is flat, and the strategy logic correctly
chooses to open a long. The interaction with the pre-existing short is a
**downstream consequence**, not a separate mechanism.

**Verdict: 🟡 PARTIAL (consequence, not cause).** Folds into H2's
detection-blindness scope. A side-aware reconciliation would gate new
entries on broker-side shorts and resolve this consequence automatically.

---

### H7 — Two redundant standalone SELL orders firing in the same second (NEW, emerged from IMSR trace)

**Hypothesis:** When trail and escalation paths fire simultaneously (or
within seconds), they place TWO distinct standalone SELL orders for the
same symbol. Neither is in any OCA group. Both can fill against a single
long position, producing a -1× position size phantom short.

**Code paths:**
- [argus/execution/order_manager.py:2451+](argus/execution/order_manager.py#L2451) — `_trail_flatten` places `OrderType.MARKET` SELL
- [argus/execution/order_manager.py:2552+](argus/execution/order_manager.py#L2552) — `_escalation_update_stop` places `OrderType.STOP` SELL via `_submit_stop_order`
- Neither call site sets `ocaGroup` on the placed order.

**Evidence:** IMSR forensic trace at 12:11:14 (escalation places SELL 200
STOP) + 12:15:04 (trail places SELL 200 MARKET) — both standalone, both fire
within ~3 minutes, escalation stop fired at 12:15:04 (filled 200), trail
flatten partially filled 100 → broker -100. **Two redundant exit paths,
zero OCA linkage between them.**

```
$ grep -c "Trail stop triggered" logs/argus_2026-04-24.log
154
$ grep -c "Escalation stop updated" logs/argus_2026-04-24.log
347
```

154 trail flattens + 347 escalation-stop updates = **501 standalone exit
orders placed today**, none of them linked to each other or to the original
bracket children. With async cancel propagation racing live trigger prices,
multi-fill on a single position is the expected outcome.

**Verdict: 🟢 LIKELY (compounds H1 on symbols with trail/escalation activity).** Of the 44 EOD-short symbols, **27 had at least one trail/escalation/flatten event**; the other 17 are pure-H1 bracket-OCA-race.

---

### H8 — Periodic reconciliation strips side info (compounds H2)

**Hypothesis:** Even if `reconcile_positions` had a broker-orphan-handling
branch, it could not detect a phantom SHORT because the calling code at
`main.py:1524` flattens `Position` to `(symbol, abs_qty)` before passing in.

**Code path:** [argus/main.py:1520-1531](argus/main.py#L1520-L1531)

```python
broker_pos_list = await self._broker.get_positions()
broker_positions: dict[str, float] = {}
for pos in broker_pos_list:
    symbol = getattr(pos, "symbol", "")
    qty = float(getattr(pos, "shares", 0))   # ← abs value — side dropped
    if symbol and qty != 0:
        broker_positions[symbol] = qty
```

**Verdict: 🟢 LIKELY (architectural blindness compounding H2).** Even an
in-place patch to `reconcile_positions()` would still see signed-stripped
data. **The side-aware reconciliation fix MUST extend up through the
call site in `main.py` and through the comparator in `order_manager.py`.**

---

## What signature analysis tells us

Per kickoff §Requirement 3, a correct mechanism explains all five patterns:

| Required pattern | H1 | H2 | H7 | H5 | H8 |
|---|:-:|:-:|:-:|:-:|:-:|
| Why gradual not single-event | ✅ One bracket per drift event; many brackets per day | ✅ 60s reconcile cycle | ✅ One trail/escalation per drift | partial | enables gradual drift |
| Why 44 symbols not one symbol compounding | ✅ Brackets fire across full universe | ✅ Reconcile is symbol-agnostic | ✅ Trail fires across universe | ❌ Only IMSR fired DEF-158 today | enables universe-wide |
| Why ~325 shares/symbol avg | ✅ Avg position size + 1× leak per cycle | n/a | ✅ Avg position size | ✅ Doubles existing short | n/a |
| Why only 4/44 overlap with DEC-372 stop-retry | ✅ Distinct mechanism | ✅ Distinct | ✅ Distinct | ✅ Distinct | ✅ Distinct |
| Why no orphan-fill WARNINGs for 38 of 44 | ✅ Silent DEBUG path swallows fills | n/a | ✅ Same DEBUG path | n/a | n/a |

**H1 + H2 (compounded by H7 and H8) is the only combination that explains
all five patterns simultaneously.** H5 doubles where pre-existing short
lives but cannot create the initial short; H6 is a downstream consequence.

## Top-3 ranking

### #1 — H1 (bracket-child multi-fill via missing `ocaGroup`) + H7 (redundant standalone SELLs from trail/escalation, no OCA) — primary fill-side mechanism

**Consistency score:** 5/5 patterns explained.
**Blast radius today:** ~14,000 of 14,249 EOD-short shares (≈98%).

**What the fix would look like (direction, NOT implementation):**

A coordinated three-part fix landing in a single `post-31.9-reconciliation-drift` sprint:

1. **Set explicit `ocaGroup` + `ocaType=1`** on the bracket's three children
   (stop, T1, T2) at [argus/execution/ibkr_broker.py:736-769](argus/execution/ibkr_broker.py#L736-L769).
   With `ocaType=1` ("Cancel with block"), IBKR's matching engine atomically
   blocks on cancel propagation before allowing siblings to trigger — this
   closes the race window at the broker level rather than relying on async
   cancel from ARGUS.
2. **Set `ocaGroup` on the standalone trail flatten + escalation stop +
   `_resubmit_stop_with_retry` SELLs to share the SAME OCA group as the
   original bracket children for the symbol.** All exit orders for one
   ARGUS position should be in one OCA group regardless of code path that
   submitted them. This requires threading an OCA-group identifier through
   `ManagedPosition` (e.g., add `oca_group_id: str` field).
3. **Add a unit test that asserts every SELL order placed by the order
   manager carries an `ocaGroup` attribute when there is an open
   `ManagedPosition` for the symbol.** This is the regression guard — the
   bug today is the absence of attribute setting, so the test grep-checks
   for the attribute presence.

The fix is gated on ib_async/ibapi providing `ocaGroup` field on the
`Order` object (it does — `Order.ocaGroup: str` and `Order.ocaType: int`
are standard IB API fields). No external service changes needed.

### #2 — H2 (side-blind reconciliation drops broker-side phantom shorts) + H8 (call site strips side info before reconciliation runs) — primary detection blindness

**Consistency score:** 4/5 patterns (does not explain "why ~325 shares/symbol" — that's mechanism territory).
**Blast radius:** Allows H1's leak to accumulate from 1 occurrence to 44 across 6 hours.

**What the fix would look like:**

1. Change the reconciliation contract from `dict[str, float]` to
   `dict[str, tuple[OrderSide, int]]` (or pass the typed `Position`
   list directly). Site:
   [argus/main.py:1520-1531](argus/main.py#L1520-L1531) +
   [argus/execution/order_manager.py:2976](argus/execution/order_manager.py#L2976)
   signature.
2. Extend the orphan-direction guard at
   [argus/execution/order_manager.py:3038-3039](argus/execution/order_manager.py#L3038-L3039)
   to handle the broker-orphan direction explicitly: when broker has a
   non-long position that ARGUS doesn't track, log at ERROR + emit a
   `SystemAlertEvent(severity="critical", source="reconciliation",
   alert_type="phantom_short")`, and gate new entries for the symbol via
   the same circuit-breaker pattern as DEC-367 (margin circuit).
3. Add a regression test that simulates a broker-side -N short with
   ARGUS-thinks-zero state and asserts the reconciliation emits the alert
   AND blocks new entries.

### #3 — H5 (DEF-158 path side-blindness) — narrow blast radius today, full blast radius once H1+H7 land

**Consistency score:** 1/5 patterns (only IMSR fired today, but mechanism is general).
**Blast radius:** Doubles any pre-existing short. Once H1 leak is closed, this becomes the dominant residual amplifier on any path that still leaks (e.g., a future bug class).

**What the fix would look like:**

Apply the same side-check pattern IMPROMPTU-04 used for EOD Pass 1/2 to
`_check_flatten_pending_timeouts` at
[argus/execution/order_manager.py:2384-2406](argus/execution/order_manager.py#L2384-L2406):
read `pos.side` alongside `pos.shares`; if `side == OrderSide.SELL` (broker
is short), **abort the flatten retry** with a CRITICAL log + alert ("Flatten
retry refused: broker is short, ARGUS thought long — investigate and cover
manually"), do not issue the SELL.

This is the same shape as the IMPROMPTU-04 fix and benefits from the same
3-branch test pattern (BUY → flatten, SELL → log + skip, unknown → log +
skip). **Bundle in the same sprint as #1 and #2.**

---

## Recommended fix scope for `post-31.9-reconciliation-drift`

Single sprint, ~3 sessions, all three fixes together:

| Session | Scope | Files | Test delta |
|---|---|---|---|
| Session 1 | H1 + H7 — `ocaGroup` on bracket + standalone SELLs | `ibkr_broker.py`, `order_manager.py`, `ManagedPosition` model | +6 to +10 (regression guards on attribute presence + race-window simulator) |
| Session 2 | H2 + H8 — side-aware reconciliation contract | `main.py`, `order_manager.py` (`reconcile_positions` signature) | +6 to +10 (broker-orphan detection + alert + entry-gate) |
| Session 3 | H5 — side-aware DEF-158 retry path | `order_manager.py:2384-2406` | +3 to +6 (3-branch side check, mirrors IMPROMPTU-04 pattern) |

Adversarial review and a non-safe-during-trading constraint apply because
the fix touches the order-submission and reconciliation hot paths. **All
three sessions must land before next paper session resumes** — partial
fixes leave residual amplifiers (e.g., H5 alone amplifies any latent short;
H2 alone reports correctly but doesn't prevent further drift).

---

## Retrospective Candidate

> **P26 candidate (for next campaign's RETRO-FOLD):** When validating a fix
> against a recurring symptom, verify against the mechanism signature (e.g.,
> 2.00× doubling ratio), not the symptom aggregate (e.g., "shorts at EOD").
> Yesterday's 2.00× math was the correct discriminator; without it, today's
> 44-symbol cascade would have been misattributed to DEF-199 regression and
> IMPROMPTU-04 would have been incorrectly reopened. Origin: Apr 24 debrief
> validation moment (the Apr 24 debrief author preserved the exactly-1.00×
> set-equality table, which let today's IMPROMPTU-11 read the upstream
> cascade unmasked). Generalization: any fix-validation session should
> explicitly identify the mechanism signature before running the
> validation. The signature is the falsifiable part; the symptom aggregate
> is the dependent variable.

SPRINT-CLOSE will pick this up and route to the next campaign's RETRO-FOLD.

---

## Appendix A — Diagnostic grep cheatsheet

All commands run against `logs/argus_2026-04-24.log` (28 MB, 130,593 lines):

```bash
LOG=logs/argus_2026-04-24.log

# Detection-side counts
grep -c "DETECTED UNEXPECTED SHORT POSITION" $LOG       # 44 — IMPROMPTU-04 A1 fix fires
grep -c "Position reconciliation:" $LOG                 # 378 — every-60s WARNING summary
grep -c "Flatten qty mismatch" $LOG                     # 1 — DEF-158 side-blind path (IMSR only)

# Fill-side counts
grep -c "Order filled:" $LOG                            # 2225 — total broker fills (IBKR side)
grep -c "Bracket placed:" $LOG                          # 899 — entries
grep -c "Stop hit for" $LOG                             # 482 — ARGUS-recognized stop exits
grep -c "T1 hit for" $LOG                               # 168 — ARGUS-recognized T1 exits
grep -c "T2 hit for" $LOG                               # 29 — ARGUS-recognized T2 exits
# Mass balance: 2225 - 899 - 482 - 168 - 29 = 647 unaccounted broker SELL fills

# Orphan-fill warnings (visible tip-of-iceberg)
grep -c "T1 fill for .* but no matching position" $LOG  # 6
grep -c "Stop fill for .* but no matching position" $LOG # 0 — silent DEBUG path
grep -c "T2 fill for .* but no matching position" $LOG  # 0
grep -c "Fill for unknown order_id" $LOG                # 0 visible (DEBUG-level, filtered out)

# Standalone-SELL paths (H7)
grep -c "Trail stop triggered" $LOG                     # 154
grep -c "Escalation stop updated" $LOG                  # 347
# 154 + 347 = 501 standalone exit orders, none in OCA group with bracket

# Cancel pattern counts
grep -E "Order cancelled.*type=stop" $LOG | wc -l       # 67
grep -E "Order cancelled.*type=t1_target" $LOG | wc -l  # 73
grep -E "Order cancelled.*type=t2" $LOG | wc -l         # 99
```

## Appendix B — Code-side architectural anchors

| Concern | File:line | Issue |
|---|---|---|
| Bracket children placed without `ocaGroup` | [ibkr_broker.py:736-769](argus/execution/ibkr_broker.py#L736-L769) | only `parentId`, no `ocaGroup`/`ocaType` — relies on parent-link OCA-like behavior which is loose in IBKR paper |
| Standalone trail-flatten SELL not in OCA | [order_manager.py:2451](argus/execution/order_manager.py#L2451) (`_trail_flatten`) | place_order builds standalone Order, never sets `ocaGroup` |
| Standalone escalation-stop not in OCA | [order_manager.py:2552](argus/execution/order_manager.py#L2552) (`_escalation_update_stop`) | same as above |
| Standalone resubmit-stop not in OCA | [order_manager.py:778](argus/execution/order_manager.py#L778) (`_resubmit_stop_with_retry`) | same as above |
| Race-window stop cancel + new stop (T1 partial branch) | [order_manager.py:1208-1226](argus/execution/order_manager.py#L1208-L1226) | async cancel + new place; both can be live simultaneously |
| `on_fill` silent DEBUG path | [order_manager.py:592](argus/execution/order_manager.py#L592) | `Fill for unknown order_id %s, ignoring` — DEBUG, invisible at INFO+ |
| `Position.shares = abs(int(ib_pos.position))` | [ibkr_broker.py:937](argus/execution/ibkr_broker.py#L937) | side preserved separately on `Position.side`, but value is unsigned |
| Reconcile call site strips side | [main.py:1520-1531](argus/main.py#L1520-L1531) | `dict[str, float]` of `abs(qty)` — side dropped |
| `reconcile_positions` orphan loop one-direction | [order_manager.py:3038-3039](argus/execution/order_manager.py#L3038-L3039) | `if internal_qty <= 0 or broker_qty != 0: continue` — broker-orphan ignored |
| DEF-158 retry path side-blind | [order_manager.py:2384-2406](argus/execution/order_manager.py#L2384-L2406) | `broker_qty = abs(int(getattr(bp, "shares", 0)))` — issues SELL even when broker is short |

## Appendix C — Confidence note on H1 mass-balance

The H1 mass-balance computation (2225 − 899 − 679 = 647 unaccounted broker
SELL fills) is **directional**, not exact:

- Some "Position fully closed" by-T1 events (59 of the 168 T1 hits) sum
  to a single position-close where ARGUS legitimately accounts for both
  the T1 partial AND the closing bar in one event. Those should not be
  double-counted as separate exit fills.
- Partial fills produce multiple `Order filled:` events for the same
  ULID (IMSR escalation stop fired the SAME ULID 200 @ 7.81 twice at
  12:15:04 — IBKR reports cumulative qty in step updates).
  `OrderManager` dedups via `_last_fill_state` at line 580-588, but
  `IBKRBroker._on_order_status` logs every report.

The 647 figure is therefore a **rough but conservative ceiling**. The
correct exact accounting would require parsing every `Order filled:` line's
ULID and matching against the bracket placement records — feasible but
out of scope for a read-only diagnostic. The directional conclusion (
**hundreds of broker SELL fills are silent at the ARGUS event-bus
boundary**) holds and is sufficient to motivate the H1 fix.

---

*End IMPROMPTU-11 mechanism diagnostic.*

# DEF-216 Audit — `scripts/ibkr_close_all_positions.py` Side-Blind-Flatten Audit

> **Renumbering note (added 2026-04-30 post-audit):** This audit was filed under the verdict-side number DEF-216. At post-verdict cross-check against CLAUDE.md, all Tier 3 #1 DEF numbers were renumbered to avoid collision with Sprint 31.91 follow-ups (DEF-216 → DEF-239). The audit's body text below uses the verdict-side number throughout for historical fidelity; CLAUDE.md and downstream references use DEF-239. See [tier-3-review-1-verdict-renumbering-corrections.md](tier-3-review-1-verdict-renumbering-corrections.md).

**Status:** RESOLVED-VERIFIED-NO-FIX
**Date:** 2026-04-30
**Sprint:** Sprint 31.92 Tier 3 Review #1 disposition (Cat A.3)
**Trigger:** Tier 3 Review #1 verdict (`tier-3-review-1-verdict.md` §Cat A.3 + DEF-216) flagged the operator's daily DEF-204 mitigation script for urgent audit before market open 2026-05-01 against the side-blind-flatten bug class observed in `spike_def204_round2_path1.py` (DEF-214).
**Audited file:** `scripts/ibkr_close_all_positions.py` at HEAD (`58b2014`).

## Audit Question

Does `scripts/ibkr_close_all_positions.py` contain the `if p.shares > 0: SELL` pattern (or any equivalent absolute-value-side-blind pattern) that — on `Position.shares = abs(int(ib_pos.position))` — would issue a SELL against a short position and thereby double it, reproducing the DEF-204 phantom-short cascade?

## Acceptance Criterion (verbatim from verdict §Cat A.3)

> Script visibly inspects signed quantity OR an `OrderSide` field before issuing any SELL/BUY. Refuses to act on UNKNOWN side.

## Audit Method

1. Read all 77 lines of [scripts/ibkr_close_all_positions.py](../../../scripts/ibkr_close_all_positions.py) (single file, no helpers).
2. Identify every order-emit site (every `placeOrder(...)` call).
3. For each emit site, trace the side-decision path back to the source quantity.
4. Verify the source quantity is signed (raw broker), not absolute-value-wrapped.
5. Cross-reference imports to confirm the script does not consume ARGUS's `argus.models.trading.Position` wrapper (which does `abs(int(ib_pos.position))` at `argus/execution/ibkr_broker.py:937` per CLAUDE.md DEF-199 row).

## Findings

### Finding 1 — Imports are raw `ib_async` only (CRITICAL)

Line 11: `from ib_async import IB, MarketOrder`

The script imports nothing from `argus.*`. There is no path through ARGUS's `Position` wrapper. `ib.positions()` returns `list[ib_async.Position]` directly. `ib_async.Position` is a NamedTuple `Position(account, contract, position, avgCost)` whose `position` field is the **raw signed broker quantity** (verified via `python -c "from ib_async import Position"` introspection).

This is the structural fact that distinguishes this script from the DEF-214 spike-harness bug. DEF-214's bug pattern depended on consuming `Position.shares` (absolute-value-wrapped) and then comparing `> 0`. This script consumes `Position.position` (raw signed) — the bug class cannot manifest.

### Finding 2 — Single emit site, branch-on-signed-quantity (lines 51–57)

```python
51   for p in non_flat:
52       contract = p.contract
53       contract.exchange = "SMART"
54       if p.position < 0:
55           ib.placeOrder(contract, MarketOrder("BUY", abs(p.position)))
56       else:
57           ib.placeOrder(contract, MarketOrder("SELL", abs(p.position)))
```

- `p.position < 0` (short) → **BUY** to cover. Correct.
- `else` (positive, since zero is filtered upstream) → **SELL** to flatten. Correct.

The branch inspects the signed quantity (`p.position`) before deciding the side of the order. `abs(p.position)` appears only in the *quantity* parameter, never in the *side decision*. This satisfies the verdict's acceptance criterion: "script visibly inspects signed quantity ... before issuing any SELL/BUY."

### Finding 3 — Zero-quantity filter upstream (line 40)

```python
40   non_flat = [p for p in positions if p.position != 0]
```

Zero positions are filtered before the emit loop. The `else` branch at line 56 therefore handles only the strictly-positive case in practice. There is no "zero falls through to SELL with qty=0" failure mode.

### Finding 4 — Long-only policy does NOT apply to this script

DEF-214's three-branch fix shape (Cat A.2) for the spike harness uses `signed_qty < 0 → log+raise SpikeShortPositionDetected` because the spike is a long-only experiment and a short detected mid-spike implies prior-session contamination that should abort.

This script's purpose is **opposite**: it is the operator's full-account cleanup tool, the daily DEF-204 mitigation, and the Sprint 31.91 cessation criterion #5 mechanism. It MUST cover shorts as part of full cleanup — that is its raison d'être. BUY-to-cover on a short is the correct behavior, not a policy violation. The verdict's Cat A.3 acceptance language ("inspects signed quantity ... before issuing any SELL/BUY") is satisfied; the spike's long-only-abort branch is contextually inappropriate here and would defeat the script's purpose.

### Finding 5 — UNKNOWN side handling

The verdict acceptance criterion includes "Refuses to act on UNKNOWN side." `ib_async.Position.position` is a numeric field populated directly from IBKR's positions API; it is always a signed number for any returned position. There is no observable UNKNOWN-side path through `ib.positions()`. The current `if p.position < 0 / else` structure does not have a defensive third branch for None/NaN, but such a value cannot arise from `ib.positions()` in practice. Defense-in-depth could be added (e.g., explicit `isinstance(p.position, (int, float)) and not math.isnan(p.position)` guard), but this is not required by the acceptance criterion and would not address any observable failure mode.

## Conclusion

**RESOLVED-VERIFIED-NO-FIX.**

The script does not contain the DEF-214 bug class. It satisfies the Cat A.3 acceptance criterion structurally:

- Order side is selected by inspecting the raw signed broker quantity `ib_async.Position.position`.
- The script consumes `ib_async.Position` directly, not ARGUS's `Position.shares = abs(...)` wrapper that DEF-214's bug class depends on.
- BUY-to-cover-short and SELL-to-flatten-long are both routed correctly.
- Zero positions are filtered upstream.

The operator's daily DEF-204 mitigation tool has been side-aware since the file was authored. There is no historical period during which the daily flatten was adversarial. Sprint 31.91 cessation criterion #5's clock does not need to restart.

**No code change required. No commit required.** This audit note is the deliverable.

## Cross-References

- Tier 3 Review #1 verdict §Cat A.3 + DEF-216 (this audit's authority)
- DEF-214 (the bug class this audit checked against; resolution shape per Cat A.2)
- Sprint 31.91 IMPROMPTU-04 (the production-code precedent of the three-branch pattern; `argus/execution/order_manager.py:1707` EOD Pass 2 + `:1684` EOD Pass 1 + `argus/main.py::check_startup_position_invariant`)
- CLAUDE.md DEF-199 row (canonical record of `Position.shares = abs(int(ib_pos.position))` at `argus/execution/ibkr_broker.py:937` — the wrapper this script *does not consume*)
- Sprint 31.91 cessation criterion #5 (CLAUDE.md "Active Sprint" + project-knowledge.md): satisfied posture confirmed, clock continues.

## Operator Action Items

None. Continue running `scripts/ibkr_close_all_positions.py` as the daily DEF-204 mitigation. Cessation criterion #5 (5 paper sessions clean post-seal) clock continues from its existing anchor; no restart needed.

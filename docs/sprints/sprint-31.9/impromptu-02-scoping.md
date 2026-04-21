# IMPROMPTU-02 (scoping) — Bracket amendment leak investigation

> Generated from 2026-04-21 market session debrief. Paste into a fresh Claude Code session. This prompt is **standalone** — do not read other session prompts in this campaign.

## Scope

**Type:** Read-only investigation
**Findings investigated:** F-03 (bracket amendment leak), F-04 (flatten retry against non-existent positions), F-10 (emergency flatten frequency) — all from `docs/debriefs/2026-04-21.md`
**Files read (no writes to source):**
- `argus/execution/order_manager.py` (3,036 lines — focus on `_handle_entry_fill` and bracket amendment code path)
- `argus/execution/ibkr_broker.py` (focus on order cancel/amend flow)
- `argus/models/trading.py` (Position and ManagedPosition data models)
- `argus/core/config.py` (for OrderManagerConfig and bracket amendment settings)
- Historical reference: the logs from 2026-04-21 session if helpful

**Files written (investigation artifacts only):**
- `docs/sprints/sprint-31.9/impromptu-02-findings.md` (new — the findings report)
- `docs/sprints/sprint-31.9/impromptu-02-fix.md` (overwrite the placeholder — the generated fix prompt)

**Safety tag:** `read-only` — this session writes no source files, no config, no tests. Only two markdown files under `docs/sprints/sprint-31.9/`.

## Pre-Session Verification (REQUIRED — do not skip)

### 1. Prerequisite — FIX-04 must have landed

```bash
# Verify FIX-04 (audit Phase 3 Stage 3) has committed to main.
# The commit message should include "audit(FIX-04)" and reference P1-C1-C01.
git log --oneline --all | grep -i "audit(FIX-04)" | head -3
```

If no FIX-04 commit appears, **STOP**. This scoping session must run after FIX-04 lands so the investigation reads Order Manager code with the `entry_price=0` bug (F-02) already corrected. Otherwise F-02's symptoms and F-03's symptoms will be entangled in the trace.

### 2. Environment check

```bash
# This is a read-only investigation. Paper trading can be running.
# No test run required — this session doesn't modify code.
./scripts/launch_monitor.sh status 2>/dev/null || echo "monitor offline — OK for read-only"
```

### 3. Branch & workspace

Work directly on `main`. Single commit at the end: the two markdown artifacts.

## What the 2026-04-21 debrief tells us

From `docs/debriefs/2026-04-21.md` and supporting analysis:

### The correlation

**45 of 46** IBKR positions that had to be manually closed at 3:53 PM ET on 2026-04-21 had a `"Bracket amended for <SYM>: fill slippage +<N>.<NN>, new stop=X, new T1=Y"` log line during the session. The correlation is 98%.

### The mechanism hypothesis (needs confirmation or refutation)

When an entry fill has slippage > some threshold (likely $0.01 or the configured `_amended_prices` delta), `_handle_entry_fill` (or wherever the DEC-366 bracket amendment logic lives) invokes a code path that:

1. Cancels the original stop order
2. Places a new stop order at the slippage-adjusted price
3. Cancels the original T1 order
4. Places a new T1 order at the slippage-adjusted price

**The hypothesis:** step 3–4 for T2 is **not performed**. The original T2 at the pre-slippage price remains active on IBKR. For a BUY entry, the original T2 is BELOW the actual fill price (because entry filled above-plan), which makes the T2 a marketable LIMIT. IBKR fills the original T2 immediately upon receipt of the amendment sequence, producing an unexpected SELL that ARGUS's state machine does not reconcile against the bracket.

### Supporting evidence from the log

- Two explicit "T1 fill for X but no matching position" warnings (LCID at 14:26:49, ETHA at 19:24:21). These are cases where a bracket leg fired AFTER ARGUS marked the position closed — consistent with orphan legs left over from amendment.
- 3 "SAFETY: Amended T1 <= fill → Cancelling position" events on NVTS, WOLF, FCEL, AVEX. These are cases where the amendment math produced an inverted T1 (T1 below fill); the protection fired but the affected symbols still appeared in the 45 untracked EOD list, suggesting the protection itself doesn't fully clean up the bracket state.
- For KBR specifically, ARGUS logged clean T1 (13:41:05) + T2 (13:41:28) fills totaling 533 SELLs for a 533 entry — perfect net-flat internally. IBKR showed KBR: -200 at EOD. That 200-share delta means extra SELLs fired that ARGUS's state machine did not expect.
- 2,011 "IBKR error 201: not available for short sale" rejections during the session are downstream: flatten attempts for positions ARGUS thinks it owns but IBKR shows no long for — the leaked short side from prior amendment sequences.
- 43 "Stop retry failed → Emergency flattening" events (F-10), roughly 1 every 10 min. Likely the same bracket-amendment race: amending the stop repeatedly bumps into IBKR state-machine edge cases (10148, 10147) that cascade into retry exhaustion.

## What this scoping session must produce

### Artifact 1: `docs/sprints/sprint-31.9/impromptu-02-findings.md`

A findings report covering:

1. **Code path map** — the exact call chain from entry fill event → bracket amendment → new stop + T1 placement → (does or does not) T2 placement. Include file paths and line numbers. Include any conditional branches that skip or modify amendment behavior.

2. **Hypothesis verification** — confirm or refute:
   - Does the amendment code touch T2? (yes/no, with line references)
   - If no: is this deliberate (T2 expected to trigger at its original price regardless of fill slippage) or accidental (bug)?
   - If yes: what does the amendment do to T2, and is the logic correct for a +slippage entry fill?
   - Does the amendment cancel ALL existing bracket legs before placing new ones, or does it modify in place?
   - What happens to bracket legs if the entry fill arrives BEFORE the brackets are fully placed (race condition)?

3. **Race conditions identified** — any order-of-operations between ARGUS's internal state machine and IBKR's event stream that could leave orphan legs. Specifically check:
   - What happens between `_last_fill_state` dedup (DEC-374) and `_amended_prices` tracking?
   - What happens if an IBKR `cancel_order` returns 10148 ("cannot be cancelled") — does the code assume the order was cancelled, or does it re-query state?
   - What happens to `_broker_confirmed[symbol]` during amendment? Does the symbol remain "confirmed" throughout?

4. **Second bug: flatten-retry-against-phantom-position** — trace how ARGUS can hold a `_managed_positions` entry AND `_broker_confirmed[symbol]` entry for a symbol that IBKR's portfolio snapshot does NOT show. Identify the conditions under which `_broker_confirmed` can get stale. Propose invalidation semantics (e.g., "after N consecutive snapshot misses, remove from `_broker_confirmed` and trigger a gentle reconciliation rather than a flatten order").

5. **Root cause statement** — a single paragraph summarizing the defect(s) in plain language. If there are multiple intertwined bugs (not one root cause), say so explicitly — this triggers the campaign escalation criterion in the Work Journal handoff and the operator will decide whether to split the fix into multiple sessions.

6. **Fix proposal** — 3–5 bullet points describing the intended fix at the design level. Not code. Examples:
   - "Extend amendment path to include T2"
   - "Replace 'cancel then place' with IBKR's `modifyOrder()` API to eliminate the gap where no bracket leg is live"
   - "On IBKR 201 on a flatten, treat as definitive evidence the position is flat at IBKR and remove from `_managed_positions`"
   - "Track `_broker_confirmed_last_seen[symbol]` and invalidate after 3 consecutive snapshot misses"

7. **Test strategy** — what regression tests should the fix session write? For each:
   - Test name
   - What it asserts
   - What ManagedPosition / IBKR fixture state it sets up

8. **Risk assessment** — any concerns about the fix (e.g., "modifyOrder() semantics differ between paper and live IBKR; need to verify", "removing `_broker_confirmed` too aggressively risks re-enabling the original DEC-369 failure mode this protection was added for"). List explicitly so the fix session can plan around them.

### Artifact 2: `docs/sprints/sprint-31.9/impromptu-02-fix.md` (overwrite the placeholder)

A full Claude Code fix prompt in the same format as the other FIX-NN prompts in `docs/audits/audit-2026-04-21/phase-3-prompts/`. Required sections:

- Scope (files touched, findings addressed, safety tag: `weekend-only`)
- Pre-Session Verification (paper trading paused, baseline test run, branch)
- Implementation Order
- Per-finding: File/line, current code, problem, fix, regression test, commit bullet
- Post-Implementation Verification (tests, scope check)
- Commit message template
- Close-out instruction

The fix prompt should be executable as a single Claude Code session with an expected compaction risk score of ≤13 (Medium). If the scope is too large for one session (compaction risk ≥14), split into `impromptu-02a-fix.md` and `impromptu-02b-fix.md` and update the Sprint 31.9 README accordingly. **Escalate to the Work Journal before committing a split** so the operator can confirm the stage plan change.

## Suggested investigation approach

1. **Start with `_handle_entry_fill`** — locate it in `order_manager.py`. Read end-to-end. Note every code path that touches stop or target orders.

2. **Find the amendment branch** — look for `_amended_prices`, `"Bracket amended"`, `fill slippage`, or `DEC-366`. Identify the entry point and the cancel-and-place sequence.

3. **Check what happens to T2** — grep for "target" / "T2" / "second target" in the amendment code path. This is the hypothesis-critical question.

4. **Trace the KBR case** — if useful, open `logs/argus_20260421.jsonl` (or a recent session log) and filter for KBR events between the entry fill and the position close. Cross-reference log lines with the code path you've mapped.

5. **Read `_broker_confirmed` lifecycle** — grep for `_broker_confirmed`. Find where it's set, where it's read, where it's cleared. Check whether any code path clears it on reconciliation miss.

6. **Read the flatten path** — `_flatten_pending`, `close_position`, `eod_flatten`. Trace what happens when a flatten SELL is rejected with IBKR error 201. Does the Order Manager believe the position is gone, or does it retry?

7. **Look for "cancel returning 10148"** — this IBKR error means the order is already cancelled. Check whether the amendment code treats a 10148 as "ok, order is gone" or as "uncertain state, retry".

You may read the 2026-04-21 JSONL log (if available on disk) to cross-reference behavior with code paths. Do not run ARGUS or place any orders.

## What this scoping session must NOT do

- Do not modify `argus/**` (no source, no tests, no configs)
- Do not attempt to apply the fix — that's a separate session
- Do not run pytest or Vitest (nothing changed, would just confirm baseline)
- Do not commit code changes — only the two markdown artifacts

If during investigation you discover the bug is trivially 1-line and want to fix it immediately, **STOP** and escalate to the Work Journal. Even a 1-line execution-layer fix is weekend-only and should go through the full fix-session pattern with a review.

## Commit

Single commit at the end:

```
audit(IMPROMPTU-02-scoping): bracket amendment leak investigation

Part of Sprint 31.9 Health & Hardening campaign (Track B, session 2/2 scoping).
Read-only session. Investigates F-03, F-04, F-10 from
docs/debriefs/2026-04-21.md.

Produces two artifacts:
- docs/sprints/sprint-31.9/impromptu-02-findings.md (root cause + fix proposal)
- docs/sprints/sprint-31.9/impromptu-02-fix.md (Claude Code fix prompt)

No source, config, or test files modified.
```

## Close-out

This is a read-only session, so the standard close-out skill still applies but several sections will be short:

- Self-assessment: CLEAN (or FLAGGED if the investigation revealed the bug is more complex than a single fix can handle — see "What this scoping session must produce" item 5)
- Change manifest: the two markdown files
- Scope verification: no source/test/config modified (list explicitly)
- Test results: not run (this is read-only)
- Notes for reviewer: anything surprising, anything the fix session will need to be careful about

No Tier 2 review needed — this is investigation output, not implementation. Paste the close-out block into the Work Journal and confirm the findings + fix-prompt artifacts are ready for the operator to review before IMPROMPTU-02 fix is scheduled.

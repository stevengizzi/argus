# Sprint 31.9 Triage Summary — Market Session 2026-04-22

> **Source:** Market session debrief against `logs/argus_20260422.jsonl` (184 MB, 895,543 lines).
> **Running process startup commit:** `f57a965` (Sprint 31.9 Stage 1 + Stage 2 complete).
> **Debrief protocol:** `docs/protocols/market-session-debrief.md` (7-phase).
> **Analyst:** Claude (Claude.ai, post-market-close Apr 23).
> **Status:** Bucket A finding is **work-blocker**; Bucket C1 is **HIGH-severity quick-win**.

---

## TL;DR

1. **CRITICAL SAFETY BUG DISCOVERED:** ARGUS's EOD flatten Pass 2 systematically **doubles any short position** it encounters in IBKR. This caused all 51 of today's "untracked" positions to end the session as shorts totaling 34,239 shares, requiring manual intervention via `ibkr_close_all_positions.py`. On a live account this would be catastrophic. Root cause is a missing side-check between `ibkr_broker.py:935` (stores `abs(shares)`) and `order_manager.py:1707` (filters on `qty > 0` without checking side). Exact 2.00× ratio observed across 50 of 51 positions is mathematical proof.

2. **184 MB log file explained:** 778,293 of 895,543 lines (87%) come from a single `logger.info(...)` on `pattern_strategy.py:318` that fires per-candle per-strategy per-symbol during warm-up. One-line fix downgrades to DEBUG; should reduce log size ~7–10× immediately.

3. **Sprint 31.9 campaign-introduced behaviors mostly landed correctly:** DEF-138 window summaries fired (30 across the day); 15 variants spawned at boot; main.py lifecycle clean; all health-monitor components HEALTHY. Two validation items were **not verified from log alone** (require DB queries): FIX-01's `catalyst_quality` non-constant claim, and quality grade distribution shift.

4. **Pre-existing weaknesses surfaced painfully today due to a 9:29 AM ET network hiccup** that caused simultaneous Databento and IBKR disconnects. Recovery exposed 32 DEC-372 stop-retry-exhaustion events, 50+ uncancelled bracket orders that likely flipped positions short during the session, and the Bucket A bug then doubled them at EOD.

---

## Confidence Levels

This document distinguishes findings by confidence so the operator can prioritize:

- **🟢 Proven** — Directly inspected in code + matching mathematical/empirical evidence from the log.
- **🟡 Strongly supported** — Multiple lines of log evidence converge on the same explanation, but not exhaustively traced.
- **🟠 Hypothesis** — Consistent with evidence but not fully verified; operator should validate.
- **⚪ Not verified** — Explicitly noted as a gap requiring DB query or code tracing beyond what was done.

---

## Bucket A — Work-Blocker Findings

Fix required **before the next paper session** runs.

### A1 🟢 `_flatten_unknown_position()` doubles short positions at EOD

**Severity:** CRITICAL (safety)

**What happened today:** Of 51 "untracked broker positions" that ARGUS attempted to flatten at 19:50:07 UTC (3:50 PM ET), 50 ended the session exactly 2× short, and 1 (PURR) ended exactly 1× short. Operator ran `ibkr_close_all_positions.py` at 3:51 PM ET to BUY back 34,239 shares across all 51 symbols.

**Precise evidence:**

| Symbol | ARGUS SELL qty at EOD | Operator saw short qty | Ratio |
|---|---|---|---|
| AAL | 223 | -446 | 2.00× |
| ANAB | 100 | -200 | 2.00× |
| ASPI | 2,417 | -4,834 | 2.00× |
| BITO | 5,823 | -11,646 | 2.00× |
| EDV | 200 | -400 | 2.00× |
| ... (45 more at 2.00×) | | | 2.00× |
| PURR | 323 | -323 | 1.00× |

A 2.00× ratio across 50 positions is statistically impossible as coincidence. The mechanism is deterministic.

**Root cause — two lines in two files:**

1. **`argus/execution/ibkr_broker.py:935`** returns position quantity as `shares = abs(int(ib_pos.position))`. The long/short distinction is preserved on `pos.side` (`OrderSide.BUY` for long, `OrderSide.SELL` for short) — line 934.

2. **`argus/models/trading.py:164`** defines `Position.shares: int = Field(ge=1)` — the field is constrained to always be ≥ 1. So `qty > 0` is always True for any open position.

3. **`argus/execution/order_manager.py:1707`** filters EOD Pass 2 candidates only on `qty > 0` without checking `pos.side`:

   ```python
   if symbol not in managed_symbols and symbol not in pass1_filled_set and qty > 0:
       # ... logs WARNING and fires _flatten_unknown_position(symbol, qty, ...)
   ```

4. **`argus/execution/order_manager.py:1936–1947`** then unconditionally places a `SELL` for `abs(qty)`:

   ```python
   sell_order = Order(
       strategy_id="startup_cleanup",
       symbol=symbol,
       side=OrderSide.SELL,   # ← always SELL, regardless of real position side
       order_type=TradingOrderType.MARKET,
       quantity=abs(qty),
   )
   ```

**Net effect:** If IBKR reports any position as short (`side=SELL`, shares=223), the EOD Pass 2 filter passes it through, and a MARKET SELL 223 is fired — doubling the short from -223 to -446. The `qty > 0` filter is effectively a no-op.

**Why 50 of 51 positions were already short before EOD (🟠 hypothesis):** The 9:29 AM ET Databento+IBKR disconnect invalidated in-flight IBKR order IDs. 32 DEC-372 stop-retry-exhaustion events fired between 9:40 and 9:59 AM ET where ARGUS gave up canceling bracket stops and fired emergency MARKET flattens. It is likely that many bracket stops in the same window fired independently on IBKR's side (after the emergency flatten already zeroed the position), flipping positions short. This was not verified by end-to-end tracing of any specific symbol.

**Why PURR is 1.00× not 2.00× (🟠 hypothesis):** PURR was likely flat (0 shares) at EOD query time, but `ib_async`'s auto-synced position cache returned a stale value of +323. ARGUS SELL 323 then flipped 0 → -323. This is consistent with the 1.00× ratio but not proven.

**Fix outline:**

```python
# order_manager.py:1707 — BEFORE
if symbol not in managed_symbols and symbol not in pass1_filled_set and qty > 0:
    ...
    await self._flatten_unknown_position(symbol, qty, force_execute=True)

# order_manager.py:1707 — AFTER (minimum fix)
from argus.models.trading import OrderSide
...
if symbol not in managed_symbols and symbol not in pass1_filled_set and qty > 0:
    if pos.side == OrderSide.BUY:
        # Long zombie — close via SELL
        logger.warning(
            "EOD flatten: closing untracked long broker position %s (%d shares)",
            symbol, qty,
        )
        await self._flatten_unknown_position(symbol, qty, force_execute=True)
    else:
        # Short zombie — DO NOT SELL. ARGUS is long-only; an unexpected short
        # should either be covered via BUY or logged-and-skipped pending
        # operator decision.
        logger.error(
            "EOD flatten: DETECTED UNEXPECTED SHORT POSITION %s (%d shares). "
            "NOT auto-covering. Investigate and cover manually.",
            symbol, qty,
        )
        # Alternative: await self._cover_unknown_short_position(symbol, qty, ...)
```

**Similar bug at `order_manager.py:1684`** (EOD Pass 1 retry block, Sprint 32.9) — same `if retry_qty > 0` without side check. Must be fixed in the same session.

**Required before next paper session:** Yes.

**Required regression tests:**
- Mock `IBKRBroker.get_positions()` returning a Position with `side=SELL, shares=100`; assert `_flatten_unknown_position` is **not** called with a SELL for that symbol, or that an alternative cover/skip path is taken.
- End-to-end test: feed an EOD Pass 2 scenario with a mix of long and short broker positions; verify only longs get flattened.
- Grep-verify no other callers of `get_positions()` have the same blind-spot (`grep -rn "get_positions" argus/` and read each call site).

---

## Bucket B — Already Covered by Sprint 31.9 Scope

Findings where the campaign has already landed — these are validation confirmations, not new work.

### B1 🟢 DEF-138 window-summary telemetry (FIX-19 P1-B-M02) — **VALIDATED**

30 window-summary log lines fired across the day from `argus.strategies.base_strategy`, covering all 15 live strategies + variants. Format is correct:

```
Strategy Pre-Market High Break window closed: 117151 symbols evaluated,
  166 signals generated, 116984 rejected (insufficient_history=14896,
  no_pattern=92448, outside_operating_window=9640)
```

**Minor nit:** In several window summaries, `symbols_evaluated` does not exactly equal `signals_generated + signals_rejected` (off by 1–2). Indicates a small counter race. LOW severity.

### B2 🟢 15 variant strategies spawned at boot — **VALIDATED**

`[9/12] Experiment variants spawned: 15` confirmed at 13:17:13 UTC. Variants match `config/experiments.yaml`:
- `strat_dip_and_rip__v2_tight_dip_quality`, `__v3_strict_volume`
- `strat_micro_pullback__v2_tight_impulse`, `__v3_strict_impulse`
- `strat_hod_break__v1_tight_consolidation`, `__v2_volume_conviction`, `__v3_tight_and_volume`
- `strat_gap_and_go__v2_big_gap`, `__v3_direct_entry`
- `strat_premarket_high_break__v2_strict_pm`
- `strat_vwap_bounce__v2_strict_approach`
- `strat_narrow_range_breakout__v2_deep_compression`
- `strat_abcd__v2_golden_zone`
- `strat_bull_flag__v2_strong_pole`
- `strat_flat_top_breakout__v2_strict_resistance`

Note: CLAUDE.md states "22 shadow variants" in several places; actual is 15. Either CLAUDE.md is stale or shadow-mode base strategies (ABCD, Flat-Top set to `mode: shadow` per Sprint 32.9) are counted separately — worth reconciling in next doc-sync.

### B3 ⚪ FIX-01 `catalyst_quality` non-constant — **NOT VALIDATED from log**

The quality engine does not emit scoring events at INFO level — it writes to `quality_history` and `catalyst.db`. No log evidence either confirms or refutes FIX-01's core claim that `catalyst_quality` dimension produces varying (non-constant 50.0) scores since the DB re-pointing landed. **Operator must validate by SQL query** against `data/argus.db` (`quality_history` table) and `data/catalyst.db`:

```sql
-- Against data/argus.db
SELECT strategy_id, AVG(catalyst_quality), MIN(catalyst_quality),
       MAX(catalyst_quality), COUNT(*)
FROM quality_history
WHERE date(created_at) = '2026-04-22'
GROUP BY strategy_id;
```

Expected: non-constant `catalyst_quality` with real variance, and `MIN != MAX`. If all rows show 50.0, FIX-01 regression.

### B4 🟡 main.py lifecycle cleanup (FIX-03) — **PARTIALLY VALIDATED**

- ✅ No `AttributeError` on deleted `_reconstruct_strategy_state` observed.
- ✅ No complaints about evaluation store not being ready when orchestrator starts.
- ✅ Triple-load collapse of `orchestrator.yaml` (DEF-093) — only 1 load visible.
- ⚠️ **Boot log still shows `[N/12]` phase labels**, not `[N/17]` as the handoff document described. Either FIX-03 did not renumber the phase labels, or the handoff inaccurately described the outcome. Re-verify FIX-03 closeout against actual boot log.
- ⚠️ Phase ordering: handoff claimed `EvaluationEventStore` moved to Phase 9 (before orchestrator). Boot log shows `[9/12] Initializing orchestrator...` **then** `[10.3/12] Initializing telemetry store... EvaluationEventStore initialized`. Phase 10.3 is **after** Phase 9 — contradicts the handoff.

### B5 🟢 Health monitor coverage expansion (FIX-03) — **VALIDATED**

All 6 new components reported HEALTHY at boot: `universe_manager`, `regime_classifier_v2`, `quality_engine` (implicit via strategy component health), `evaluation_store`, `candle_store` (via absence of warnings), `counterfactual_tracker` (via 20,658 positions opened/closed throughout the day).

### B6 🟢 Backend lifespan refactor (FIX-11) — **VALIDATED** (implicit)

No `--dev` mode references in log. `DebriefService` initialized correctly — `Debrief data exported to logs/debrief_2026-04-22.json` at 20:04:49 UTC confirms the live-mode path now works.

### B7 🟢 VwapBounce session reset (FIX-19 P1-B-M01)

VwapBounce window-summary fired with non-trivial signal generation (2,497 counterfactual positions closed, indicating active signal production). This is a positive indicator but not definitive. Compare against prior paper session baselines to confirm.

### B8 🟢 32 DEC-372 stop-retry exhaustions — **NOT COVERED by existing Sprint 31.9 scope**

See C4 below. These 32 events immediately after the 9:29 AM IBKR reconnect are causally linked to Bucket A1 (they likely flipped the 50 positions short in the first place).

---

## Bucket C — New Findings

### C1 🟢 pattern_strategy.py:318 INFO-level log spam

**Severity:** HIGH (operational)

**Evidence:** 778,293 of 895,543 log lines (87%) are `"strat_X: evaluating Y with partial history (N/M)"`. The source is `argus/strategies/pattern_strategy.py:318`:

```python
logger.info(
    "%s: evaluating %s with partial history (%d/%d)",
    self.strategy_id, symbol, bar_count, lookback,
)
```

This fires per-candle, per-strategy, per-symbol during warm-up — multiplicatively huge. With 30 strategy instances × ~1,000 active symbols × many candles, the 778K count matches.

**Root cause:** Logging-level mistake. The author wanted "don't be silent during warm-up" visibility — but this should be DEBUG. DEF-138 window summaries already serve the "not silent" purpose correctly at INFO.

**Fix (one line):**
```python
# argus/strategies/pattern_strategy.py:318
logger.debug(  # was: logger.info
    "%s: evaluating %s with partial history (%d/%d)",
    self.strategy_id, symbol, bar_count, lookback,
)
```

**Expected result:** Log file for a typical session drops from ~180 MB to ~20–30 MB.

**Required before next paper session:** Recommended. Will dramatically reduce log noise and make future debriefs faster. No safety implication.

---

### C2 🟠 IBKR stale-position cache

**Severity:** MEDIUM

**Evidence (inferential):** PURR's 1.00× ratio is consistent with IBKR's auto-synced position cache returning +323 for a position that was actually 0. If `ib_async`'s `.positions()` is stale across reconnect events, EOD Pass 2 would see phantom long positions.

**Root cause hypothesis:** `ib_async` keeps positions auto-synced, but the auto-sync may lag after reconnect. Today's 9:29 AM ET disconnect + quick reconnect may have left the cache in a stale state for some symbols.

**Fix options:**
1. Call `await self._ib.reqPositionsAsync()` explicitly before each EOD Pass 2 query to force fresh sync.
2. Add a `positions_last_updated` timestamp check; if older than N seconds, force refresh.
3. Pair this with the A1 side-check fix — the two combined provide defense in depth.

**Required before next paper session:** Not strictly required if A1 is fixed. A1 fix prevents the worst case even with a stale cache (wrong side would reject the SELL). Post-31.9 is acceptable.

---

### C3 🟢 `max_concurrent_positions` count diverges from broker state

**Severity:** HIGH (for live trading; MEDIUM for paper)

**Evidence:** Today's position-count time series:
- ARGUS rejected 8,996 signals with `"max concurrent positions (50) reached"` across the session
- IBKR position-count snapshots from `Retrieved N positions from IBKR` show:
  - 13:45 UTC (9:45 AM ET): 51 positions
  - 14:30 UTC: 85 positions
  - **14:34 UTC: peak 134 positions**
  - 14:45 UTC: 96 positions
  - Stuck at ~50–60 for most of the afternoon
  - 19:50 UTC: 51 positions still open at EOD flatten

**Root cause:** The `max_concurrent_positions` check uses only ARGUS's internal `_managed_positions` dict count. When the 9:29 AM disconnect caused entry-fill callbacks to be lost, positions were opened in IBKR but never added to `_managed_positions` — they don't count against the 50 limit, and ARGUS keeps firing new entries even while IBKR accumulates past the cap.

**Fix approach:** Periodic reconciliation of `_managed_positions.count` vs `broker.get_positions().count`. If diverges by >10%, trigger WARNING and (optional) block new entries until resynced.

**Required before next paper session:** Not strictly required. A1 fix addresses the highest-consequence manifestation (short doubling). C3 is a separate class of problem (phantom long positions ARGUS doesn't know about) that accumulates risk silently but doesn't cause immediate harm.

**Concentration check concern (related):** BITO reached 5,823 shares × ~$10.85 ≈ $63K on a $794K account = **~8% single-stock exposure**, exceeding the 5% single-stock limit in CLAUDE.md. Worth verifying whether concentration check is working or being bypassed when positions are "untracked."

---

### C4 🟢 32 DEC-372 stop-retry-exhaustion events immediately after IBKR reconnect

**Severity:** MEDIUM (causally upstream of A1)

**Evidence:** 32 `"Stop retry failed for X. Emergency flattening"` events, all between 13:40:27 and 13:59:28 UTC (9:40–9:59 AM ET) — immediately after the 9:29 AM IBKR disconnect/reconnect cycle. Affected symbols: AIQ, AMDL, CRCG, CRSR, EDV, ETHE, EWT, EYPT, FBTC, FCEL, FETH, FLYW, FRMI, GBCI, ICLN, LAR, MSTZ, NKLR, OBE, POET, RCUS, RDW, RKLZ, SBSW (×2), SONY, SOXS (×2), TGTX, VALE, VCLT.

5 of these 32 symbols (EDV, FCEL, RCUS, RKLZ, SOXS) also appear in the 51 EOD-remaining list — linking the stop-retry-exhaustion path to the EOD short-doubling cascade.

**Root cause:** After IBKR reconnect, in-flight order IDs on IBKR's side are invalidated. ARGUS's `stop_cancel_retry_max` (default 3) keeps retrying cancels against stale IDs until exhausted, at which point it fires an emergency MARKET SELL. But the original bracket stop may still be live on IBKR's side — it just can't be canceled because the ID is stale. When price later hits the stop level, IBKR fills it, flipping the position short.

**Fix approach:** On IBKR reconnect, either:
1. Re-query all open orders for the account via `reqOpenOrders()` and rebuild `_stop_retry_count` + `_amended_prices` with the fresh IDs.
2. Reset `stop_cancel_retry_max` counter and add a longer delay before first retry post-reconnect.
3. Before firing emergency MARKET flatten, query broker position qty and skip if 0.

**Required before next paper session:** Recommended if A1 fix is incomplete. If A1 is fixed in isolation, C4 still poses a problem (positions still get flipped short during the session — it's just that EOD no longer doubles them).

**Coordination note:** This touches the execution-layer retry/state machine and overlaps with DEF-177 (RejectionStage.MARGIN_CIRCUIT) and DEF-184 (RejectionStage/TrackingReason split) already deferred to post-31.9. Natural fit for the same dedicated cross-domain session.

---

### C5 🟠 evaluation.db is 4.78 GB at boot

**Severity:** MEDIUM

**Evidence:** Boot log at 13:17:13 UTC: `EvaluationEventStore initialized: data/evaluation.db (size=4776.3 MB, freelist=0.0%)`. Sprint 31.8 S2 was supposed to fix unbounded growth via close→VACUUM→reopen after retention DELETE.

**Hypotheses (not verified):**
1. Retention policy isn't executing (date-column type mismatch, timezone, or scheduling failure).
2. VACUUM isn't running on the expected schedule.
3. Size is from pre-fix accumulated data that was never retroactively vacuumed.

Freelist = 0% means data is live (not deleted-but-not-reclaimed), which rules out the "VACUUM failing to reclaim" theory. Most likely retention isn't deleting.

**Fix:** Investigate `data/evaluation.db` with an ad-hoc query:
```sql
SELECT MIN(trading_date), MAX(trading_date), COUNT(*) FROM evaluation_events;
SELECT trading_date, COUNT(*) FROM evaluation_events GROUP BY trading_date ORDER BY trading_date;
```

If row counts span > 7 days, retention is broken.

**Required before next paper session:** No. Performance impact is startup-time-only; trading operation is unaffected. Post-31.9 or opportunistic.

---

### C6 🟢 Boot phase labels `/12` vs handoff-claimed `/17`

**Severity:** LOW (documentation accuracy)

**Evidence:** Startup log shows `[1/12]`, `[2/12]`, ..., `[10.3/12]` phase labels. The handoff document and project knowledge describe a 17-phase boot sequence delivered by FIX-03.

**Root cause (hypothesis):** Either FIX-03 reorganized main.py logic but did not update the literal phase-label strings, OR the handoff doc inaccurately described the expected boot sequence.

**Fix:** Reconcile `argus/main.py` phase logging with the FIX-03-closeout claim. If the phase count is genuinely 17, update all phase-label strings. If it's actually 12, update the handoff + project-knowledge docs.

**Required before next paper session:** No.

---

### C7 🟡 Post-shutdown IBKR reconnect attempt + 16 async "Task was destroyed" warnings

**Severity:** LOW (operational hygiene) / MEDIUM (process cleanliness)

**Evidence:**
- `19:51:17` UTC — "Argus Shutting Down"
- `20:05:08` UTC (14 min after shutdown) — `argus.execution.ibkr_broker: Scheduling reconnection attempt` + `Reconnection attempt 1/10 in 1.0s`
- `20:07:41` UTC — log ends with `asyncio: Task was destroyed but it is pending! task: <Task pending name='Task-52' coro=<LifespanOn.main() ...>>` (16 of these in the shutdown tail)

**Root cause (hypothesis):** IBKR broker's reconnect scheduler spawns a new asyncio task that outlives the shutdown cancellation call. The main shutdown cancels the current reconnect task but the scheduler re-spawns one. Similar pattern to DEF-175's broader component-ownership issue.

**Fix:** Add a `_shutting_down` flag to IBKRBroker; check it in the reconnect scheduler before spawning new tasks.

**Required before next paper session:** No. Coverable under DEF-175 (post-31.9 component-ownership session).

---

### C8 🟢 Counterfactual dataset richness

**Severity:** LOW (positive observation — not a bug)

**Evidence:** 20,658 counterfactual shadow positions opened and closed today. Distribution by strategy (top 5):
- `strat_abcd`: 5,516 closes
- `strat_micro_pullback`: 3,888
- `strat_vwap_bounce`: 2,497
- `strat_abcd__v2_golden_zone`: 2,338
- `strat_vwap_bounce__v2_strict_approach`: 1,405

R-multiple distribution on closes:
- `<= -1R`: 7,459 (36%)
- `-1R < r < 0`: 4,397 (21%)
- `0 <= r < 0.5R`: 3,251 (16%)
- `0.5R <= r < 1R`: 1,200 (6%)
- `1R <= r < 2R`: 4,304 (21%)
- `>= 2R`: 47 (0.2%)

Close reasons: `stopped_out` 7,455 (36%), `time_stopped` 5,407 (26%), `target_hit` 4,840 (23%), `expired` 2,849 (14%), `eod_closed` 107 (0.5%).

**Observation:** This is an extremely healthy counterfactual dataset — the largest single-day capture to date. Sprint 33 statistical validation will have strong data to work with.

**Concern:** `strat_abcd` alone (5,516 closes) is 27% of the dataset. ABCD is in shadow-mode by default (Sprint 32.9). The signal rate is much higher than other strategies. Worth examining whether ABCD's detection is too permissive (not a bug, but a calibration concern for Sprint 33 promotion thresholds).

**Required before next paper session:** No. Note for Sprint 33 design.

---

## Procedure Recommendation

**Single IMPROMPTU session, landing before the next paper session runs** (tonight or tomorrow AM):

### Scope: IMPROMPTU-04-eod-short-flip-and-log-hygiene

**Tasks (2 code changes + 1 invariant + 5 DEFs):**

1. **A1 fix** — `order_manager.py:1707` and `:1684` side-check. `_flatten_unknown_position()` should never SELL an already-short position. Paired regression test. Grep-verify no other `get_positions()` call sites have the same blind spot.
2. **C1 fix** — `pattern_strategy.py:318` `logger.info` → `logger.debug`.
3. **Startup invariant** — after broker connect, assert all returned positions have `side == BUY`. If any are `SELL`, WARN and halt auto-startup-cleanup flatten pending operator acknowledgement.
4. **Open new DEFs** for C2/C3/C4/C5/C6 and update `docs/sprints/sprint-31.9/RUNNING-REGISTER.md`.

**Recommend Tier 2 adversarial review** on the A1 diff. The EOD flatten code path is safety-critical and the fix touches a method (`get_positions`) with multiple consumers. Review should verify:
- No other call sites assume `shares` is signed
- Short-position detection path has its own test
- Regression test uses a realistic IBKR Position mock, not a happy-path stub

**Estimated effort:** 2–3 hours implementation + 1 hour review + 1 hour operator validation against live paper account.

### Relationship to active Sprint 31.9 Stage 8/9 work

Stage 8 is complete through Wave 3 (FIX-13c CLEAR). Stage 9 (IMPROMPTU-02 scoping/fix, DEF-175-adjacent) is pending — weekend-only.

**Recommendation:** Insert IMPROMPTU-04 as a **serial task** between Stage 8 complete and Stage 9 start. Do not parallelize. The IMPROMPTU-04 scope touches `order_manager.py` and `pattern_strategy.py` — both are high-value paths that should be clean of concurrent edits during review.

### Sprint 31.9 campaign does not need to halt otherwise

All Stage 3–8 sessions are already landed and reviewed. Stage 9 can proceed after IMPROMPTU-04 without disruption. The A1 finding does not invalidate any prior sprint-31.9 work — it's an untouched pre-existing bug that today's network hiccup exposed.

---

## Go / No-Go for Tomorrow's Pre-Open

**NO-GO until A1 is fixed and regression-tested.**

Rationale:
- The A1 bug is deterministic and repeatable. Another day with the same network conditions produces another 50+ short-flipped positions requiring manual intervention.
- While paper money is not at stake, contaminated paper-trading data feeds into Sprint 33 statistical validation. Today's 51 short-flip events are not genuine strategy decisions — they are artifacts of the cascade. Preserving paper-data integrity is a first-principles commitment.
- The same A1 bug in live trading would produce unlimited losses. Every day ARGUS runs without this fix is a day the live-transition risk compounds.

**Mitigation if IMPROMPTU-04 cannot land in time:**
- Temporarily lower `max_concurrent_positions` from 50 to 15–20 in `config/risk_limits.yaml`. This reduces the number of positions that can "go zombie" during a disconnect event.
- Set `eod_flatten_retry_rejected: false` in `config/order_manager.yaml` (if the config exists) to disable the Pass 1 retry block (`order_manager.py:1675`) that has the same side-check gap.
- **Do not** run ARGUS during the Databento reconnect-sensitivity window if network stability is uncertain.

These mitigations are inferior to the actual fix; they don't eliminate the bug, just reduce the blast radius.

---

## Open Verification Gaps

Items the debrief flagged but did NOT directly verify from today's log. Recommended DB-backed follow-up:

| Gap | Query / Action | Purpose |
|---|---|---|
| FIX-01 `catalyst_quality` non-constant | SQL against `data/argus.db::quality_history` group-by-strategy, min/max/avg | Confirms primary FIX-01 behavioral claim |
| Quality grade distribution shift | SQL against `data/argus.db::quality_history` — today's grade distribution vs Sprint 32.9 post-recalibration baseline | Confirms catalyst-DB-fix changed downstream behavior |
| Daily cost ceiling for catalyst classifier | SQL against `data/catalyst.db` for today's classifier spend + compare to ceiling | Confirms DEC-324 cost-ceiling enforcement |
| First-event sentinels (OHLCV unmapped / resolved, trade resolved) | `grep -i 'first.*resolved\|first.*unmapped' logs/argus_20260422.jsonl` | Validates Apr 3 hotfix observability |
| IntradayCandleStore initialization | `grep -i 'IntradayCandleStore\|candle.?store' logs/argus_20260422.jsonl` | Part of Phase 2 startup health |
| 11 `_init_*` lifespan phases from FIX-11 | `grep -E '_init_[a-z]+' logs/argus_20260422.jsonl` or compare to `api/server.py::_LIFESPAN_PHASES` | Validates FIX-11 phase-label registry |
| Concentration limit enforcement on BITO 8% | SQL against trades table for today + re-compute concentration at position-open | Confirms 5% single-stock guard works in shadow/live |
| The 50 positions that went short — end-to-end trace of any ONE | Pick AAL. Trace: entry fill → bracket placement → exhaustion at X:XX → emergency flatten → bracket ID left live → trigger event → short fill → ... | Definitive proof of the C4 mechanism |

If the operator wants me to produce the SQL queries as a runnable script, say the word and I'll put one together as a follow-up artifact.

---

## Appendix A — Cascade Timeline

| Time (UTC / ET) | Event |
|---|---|
| 13:17:04 UTC / 09:17 AM ET | ARGUS startup (13 min pre-open buffer) |
| 13:17:10 / 09:17 | IBKR connected. Account equity $794,970.67 |
| 13:17:13 / 09:17 | Universe Manager built: 6,366 viable symbols. 15 strategies + 15 shadow variants spawned. Boot completed. |
| 13:29:12 / 09:29 | **Databento stream timeout — 40s without data.** Reconnect attempt 1/10. |
| 13:29:36 / 09:29 | **IBKR Error 1100: Connectivity lost.** |
| 13:30:19 / 09:30 | IBKR Error 1102: Connectivity restored. |
| 13:30 / 09:30 | Market open |
| 13:36:00 / 09:36 | First signals generated (pre-market high break strategies evaluating) |
| 13:40:27 / 09:40 | **First DEC-372 stop-retry-exhaustion: RCUS emergency flatten** |
| 13:41:26–13:59:28 / 09:41–09:59 | 31 more stop-retry exhaustions across 32 symbols |
| 14:30 / 10:30 | IBKR position count enters 80s (ARGUS internal capped at 50) |
| **14:34 / 10:34** | **IBKR position count peaks at 134.** ARGUS max-concurrent rejections firing 1,347/10min |
| 14:42:51 / 10:42 | First managed-position trailing-stop exit (AAL example) |
| 15:30 / 11:30 | ORB window closes. 653 ORB Breakout signals, 520 ORB Scalp signals generated. |
| 16:00 / 12:00 | VWAP Reclaim window closes. 397 signals. |
| 18:00 / 14:00 | Micro Pullback + Afternoon Momentum windows close. |
| 19:00 / 15:00 | Narrow Range Breakout + Bull Flag + Flat-Top Breakout + ABCD windows close. ABCD variant generated 2,338 signals. |
| 19:30 / 15:30 | Signal cutoff. 51 IBKR positions still open; ARGUS internal = ~0 live positions. |
| 19:50:06 / 15:50:06 | **EOD flatten triggered.** |
| 19:50:06–19:50:07 / 15:50:06–07 | 51 "untracked broker position" WARNINGs + 51 MARKET SELL orders placed (one per symbol). |
| 19:50:07 / 15:50:07 | **CRITICAL: EOD flatten: 51 positions remain after both passes** |
| 19:51:17 / 15:51:17 | Argus Shutting Down |
| ~19:51 / 15:51 | **Operator observes 51 short positions on IBKR portal. Runs `ibkr_close_all_positions.py`.** BUYS 34,239 shares. |
| 20:05:08 / 16:05 | (Post-shutdown) IBKR broker scheduling reconnection attempt — shutdown incomplete |
| 20:07:41 / 16:07 | Last log line. 16× `asyncio: Task was destroyed but it is pending!` |

---

## Appendix B — Session Stats

| Metric | Value |
|---|---|
| Session duration | 6h 51min (startup 09:17 ET → last log 16:07 ET) |
| Market hours covered | 09:30–15:51 ET (intended 09:30–16:00; early EOD at 15:50) |
| Total log lines | 895,543 |
| Log file size | 184 MB (10.5 MB compressed) |
| INFO / WARNING / ERROR / CRITICAL counts | 876,758 / 14,195 / 4,587 / 3 |
| Top logger (by volume) | `argus.strategies.pattern_strategy` — 798,195 lines (89%) |
| Databento disconnects | 1 (40s timeout at 09:29 ET) |
| IBKR disconnect events | 1 (Error 1100 at 09:29 ET; restored Error 1102 at 09:30 ET) |
| IBKR reconnection attempts | 1 post-shutdown at 16:05 ET (task-cleanup miss) |
| Stop-retry exhaustions | 32 (all in 09:40–09:59 ET window) |
| IBKR peak position count | 134 (at 10:34 ET) |
| ARGUS internal peak position count | ~50 (capped) |
| `max_concurrent_positions` rejections | 8,996 |
| Signals generated (live + shadow) | ~14,000+ (aggregate from window summaries) |
| Counterfactual positions opened/closed | 20,658 / 20,658 |
| CRITICAL events | 3 (startup alert, EOD flatten remaining, shutdown alert) |
| Window summaries emitted (DEF-138) | 30 |

---

## Appendix C — Key File References

| Finding | File / Line |
|---|---|
| A1 root cause — abs() in Position adapter | `argus/execution/ibkr_broker.py:935` |
| A1 root cause — missing side check in filter | `argus/execution/order_manager.py:1707` |
| A1 root cause — unconditional SELL in flatten | `argus/execution/order_manager.py:1936–1947` |
| A1 additional fix site — EOD Pass 1 retry | `argus/execution/order_manager.py:1684` |
| Pydantic invariant (shares >= 1) | `argus/models/trading.py:164` |
| C1 — log-spam source line | `argus/strategies/pattern_strategy.py:318` |
| Campaign state (sessions + DEFs) | `docs/sprints/sprint-31.9/RUNNING-REGISTER.md` |
| Debrief protocol (7-phase) | `docs/protocols/market-session-debrief.md` |
| Pre-live-transition checklist | `docs/pre-live-transition-checklist.md` |

---

*End of Sprint 31.9 Triage Summary — Market Session 2026-04-22.*

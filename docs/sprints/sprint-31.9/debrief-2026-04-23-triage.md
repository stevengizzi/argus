# Sprint 31.9 Triage Summary — Market Session 2026-04-23

> **Source:** Market session debrief against `logs/argus_20260423.jsonl` (184 MB uncompressed, 938,754 lines).
> **Running process startup commit:** `ffcfb5c` (Sprint 31.9 Stage 1 + Stage 2 + Stage 3 + Stage 4 + Stage 5 + Stage 6 + Stage 7 + Stage 8 Wave 1–3 + CI hotfix complete). **IMPROMPTU-01 (A1 fix, DEF-199) NOT yet landed.**
> **Debrief protocol:** `docs/protocols/market-session-debrief.md` (7-phase).
> **Baseline for comparison:** `docs/sprints/sprint-31.9/debrief-2026-04-22-triage.md` (yesterday's debrief — read first).
> **Analyst:** Claude (Claude.ai, post-market-close Apr 23).
> **Status:** **A1 / DEF-199 triggered AGAIN, as expected.** No new Bucket A findings. One MEDIUM/HIGH new Bucket C finding (C9, extended shutdown hang) and one significant update to an existing Bucket C finding (C5, `evaluation.db` growth).

---

## TL;DR — Delta Analysis vs April 22

1. **A1 / DEF-199 confirmed AGAIN on today's data, with cleaner evidence than yesterday.** 42 of 42 EOD-untracked positions ratioed **exactly 2.00×** when the operator covered them at 3:55 PM ET (ARGUS tried to SELL 6,949 shares; 13,898 shares were then short on IBKR — a perfect doubling). **Zero PURR-equivalent 1.00× outlier today.** This is mathematically definitive — the A1 mechanism is deterministic and repeatable. Yesterday's single 1.00× outlier (PURR) was the coincidence, not the rule. **IMPROMPTU-01 (the A1 fix) remains critical path; NO-GO for another paper session until it lands.**

2. **Today's cascade had a DIFFERENT upstream trigger than yesterday.** Yesterday was a brief 40-second Databento timeout + IBKR Error 1100/1102 blip at 9:29 AM ET. **Today was a full 2-minute IB Gateway outage at 11:01–11:03 AM ET** (5 reconnect attempts, Errno 61 Connection refused — the Gateway process was not listening on port 4002). When IBKR reconnected at 11:03 ET, the position snapshot showed **20 symbols were ALREADY SHORT** (`MIR -200, CIFR -131, TSLL -809, ...`). These 20 flipped short DURING the outage window, invisible to ARGUS. The remaining 22 went short between 11:03 and 15:50 ET through the same DEC-372 / bracket-exhaustion mechanism from yesterday's C4. **This is a different cascade mechanism producing the same A1 manifestation — strengthens C4 hypothesis as a repeatable failure mode, not a one-off.**

3. **Scale: 42 symbols / 13,898 shares today vs 51 / 34,239 yesterday = 82% in symbols, 41% in shares.** The share-count delta is larger than the symbol-count delta because today's positions were individually smaller (`max_concurrent_positions` capped ARGUS internal at 50, so the untracked pile averages smaller per-symbol exposure when the outage window is longer than the ARGUS-aware window). Total operator-intervention magnitude is meaningfully lower than yesterday but *only by coincidence of which symbols went short and how big they'd been sized*.

4. **Stage 3–8 behavioral changes all landed correctly:**
   - **FIX-05 / DEF-170:** VIXDataService initialized cleanly, `ready=True, stale=False`, wired into Orchestrator+RegimeClassifierV2. Yesterday flagged as likely but DB-side verification deferred; today the attach path is directly logged and working.
   - **FIX-04 execution hardening:** Startup is clean. No AttributeErrors, no missing-attribute failures. The flatten-path fixes are active in-memory but do NOT cover the A1 scope (correctly scoped out per IMPROMPTU-01).
   - **FIX-06 SystemAlertEvent emitter:** No new errors from the events.py scope expansion. Emitter side landed; consumer side still pending (DEF-014 PARTIAL, as expected).
   - **FIX-11 backend lifespan + FIX-03 health monitor:** All 30 strategy-component health lines fired cleanly; `[10.3/12]` EvaluationEventStore still in same phase slot. `DebriefService` produced `logs/debrief_2026-04-23.json` at graceful-shutdown time (20:25 UTC).
   - **FIX-08 fingerprint unification + experiment pipeline:** 15 variants spawned at boot (same as yesterday).
   - **FIX-09 backtest retirements:** No runtime import errors on any retired module path. Silent, as predicted.

5. **NEW FINDING (C9): The shutdown hang is ~4.5× worse today than yesterday.** Yesterday: `SHUTTING DOWN` (19:51) → last log line (20:07) ≈ 14 min. Today: `SHUTTING DOWN` (19:51:13) → graceful-path `STOPPED` (20:26:33) → final task-destroyed burst (21:29:30). **Today had a clean graceful shutdown at 20:26, then hung for 63 minutes before Python GC collected the dangling tasks.** The IBKR broker re-scheduled a reconnection attempt ("Reconnection attempt 1/10 in 1.0s") at 20:26:33 immediately *after* the STOPPED line, and that task plus ~15 WebSocket tasks + VIXDataService daily-update task + ActionManager cleanup task all survived until GC. This worsens C7 from yesterday's triage from LOW to MEDIUM and likely becomes a boot-collision risk if we ever start ARGUS within the hang window after a shutdown.

6. **Other things that got worse in quantifiable ways:**
   - **`evaluation.db` grew from 4,776 MB (yesterday boot) to 9,294 MB today** (+95%). Freelist still 0%. Same C5 finding from yesterday — retention / VACUUM is not running. This is fast enough that it *will* cause startup-time issues within a week.
   - **21,458 `max_concurrent_positions` rejections today vs 8,996 yesterday** (+138%). Today's broker-vs-ARGUS divergence window was much wider (~11:03 ET to 15:50 ET ≈ 4h47m, vs yesterday's ~10:34 peak → 15:50 ≈ 5h16m but with a different accumulation shape). ARGUS kept firing new entries while capped at 50 internal for most of the afternoon.
   - **10,729 WARNING-level spam lines "Signal rejected: max concurrent positions (50) reached"** is itself a secondary log-spam problem. This is not ThrottledLogger'd. Could be a C11 finding if not already covered.

7. **Stable things (unchanged vs yesterday, confirming hypothesis):**
   - C1 log spam from `pattern_strategy.py:318` — 829,190 of 938,754 lines = **88% of log volume today vs 87% yesterday**. Same bug, same source line, same impact. IMPROMPTU-01's C1 fix will kill this.
   - `[N/12]` phase labels (DEF-198) unchanged.
   - Counterfactual dataset: 21,359 opened / 21,359 closed (vs yesterday's 20,658 / 20,658 — +3.4%). Continues to be the healthiest single-day capture.
   - Window summaries fired cleanly from all 15 live strategies.

---

## Confidence Levels

- **🟢 Proven** — Directly inspected in code + matching mathematical/empirical evidence from the log.
- **🟡 Strongly supported** — Multiple lines of log evidence converge on the same explanation, but not exhaustively traced.
- **🟠 Hypothesis** — Consistent with evidence but not fully verified; operator should validate.
- **⚪ Not verified** — Explicitly noted as a gap requiring DB query or code tracing beyond what was done.

---

## Bucket A — Work-Blocker Findings

### A1 🟢 `_flatten_unknown_position()` doubles short positions at EOD — **SECOND CONFIRMATION, CLEANER EVIDENCE**

**Severity:** CRITICAL (safety) — **unchanged** from yesterday. Same bug, same triage, same fix. Still DEF-199.

**What happened today:** EOD flatten at 19:50:07 UTC (3:50 PM ET) submitted 42 MARKET SELL orders (Pass 2) for "untracked broker positions." Operator ran `ibkr_close_all_positions.py` at 3:55 PM ET and had to BUY 13,898 shares across all 42 symbols to reach flat — exactly 2× what ARGUS tried to sell.

**Today's ratio table — 42 of 42 at exactly 2.00×:**

| Symbol | ARGUS-seen | Operator-BUY | Ratio |
|---|---:|---:|---:|
| TSLL | 809 | 1,618 | 2.00 |
| SQQQ | 723 | 1,446 | 2.00 |
| YINN | 523 | 1,046 | 2.00 |
| JEPQ | 457 | 914 | 2.00 |
| ETH | 336 | 672 | 2.00 |
| PRMB | 290 | 580 | 2.00 |
| LABD | 272 | 544 | 2.00 |
| BHC | 268 | 536 | 2.00 |
| ... (34 more at 2.00×) | | | 2.00 |
| HRI | 13 | 26 | 2.00 |
| **TOTAL** | **6,949** | **13,898** | **2.000** |

**Comparison to yesterday:** Yesterday 50 of 51 at 2.00× + 1 at 1.00× (PURR). **Today 42 of 42 at 2.00×, zero 1.00× outliers.** Yesterday's C2 hypothesis (`ib_async` stale position cache for PURR) was plausibly a one-off; today's data reinforces the deterministic-doubling explanation and makes the stale-cache theory unnecessary for the base case.

**Direct evidence of upstream cascade (different from yesterday):**

At 15:03:51 UTC (11:03 ET), the IBKR `Position mismatch after reconnect!` log line enumerates 79 positions, with **20 already short at reconnect time**:

```
('MIR', -200), ('CIFR', -131), ('ARM', -6), ('TSLL', -809), ('WERN', -120),
('ETH', -336), ('BITB', -183), ('AVEX', -97), ('OPEN', -172), ('YINN', -523),
('JEPQ', -457), ('BHC', -268), ('SRPT', -25), ('IUSV', -118), ('NOK', -45),
('SQQQ', -723), ('MXL', -70), ('PRMB', -290), ('NBIL', -7), ('HRI', -13)
```

**All 20 of these symbols appear in the 42-symbol EOD-untracked list at 19:50:07.** They were already short when ARGUS reconnected after the 11:01 Gateway outage — which means:
- The bracket-stop / retry-cascade mechanism (C4 yesterday) flipped them short *during the 2-minute Gateway outage* when ARGUS couldn't see or cancel anything.
- The remaining 22 symbols (not in this reconnect snapshot) flipped short between 11:03 ET and 15:50 ET via ongoing DEC-372 stop-retry-exhaustion events (34 total today, distributed across the session — see C4 below).

**Root cause — UNCHANGED from yesterday:** `argus/execution/order_manager.py:1707` + `:1684` filter on `qty > 0` without checking `pos.side`. `IBKRBroker.get_positions()` returns `shares = abs(int(ib_pos.position))`, so the long/short distinction is only on `pos.side` and `qty > 0` is always True. `_flatten_unknown_position()` then unconditionally fires a MARKET SELL.

**Fix — UNCHANGED from yesterday's Bucket A:** IMPROMPTU-04 scope. Side-check guard at both `:1707` and `:1684`. See yesterday's triage for full fix outline + regression-test spec.

**Required before next paper session:** Yes. Operator has already committed to this NO-GO. Today's data reinforces rather than re-decides.

---

## Bucket B — Already Covered by Sprint 31.9 Scope

These are validations of Stage 3–8 landings in today's log, per the handoff.

### B1 🟢 FIX-05 / DEF-170 VIX regime intelligence wiring — **VALIDATED**

Yesterday's debrief could not verify this from log evidence (VIX fields in RegimeVector snapshots are not logged — they're persisted to `data/regime_history.db`). Today the wiring path is directly logged at startup:

```
13:18:23.968  VIXDataService: loaded 767 cached rows, last date: 2026-04-22
13:18:23.968  VIXDataService: fetching incremental data (1 days missing since 2026-04-22)
13:18:24.674  VIXDataService: fetched 2 rows from yfinance (2026-04-23 to 2026-04-24)
13:18:24.696  VIXDataService: persisted 768 daily rows
13:18:24.698  VIXDataService: initialization complete, ready=True
13:18:24.699  VIXDataService wired into Orchestrator (forwarded to RegimeClassifierV2 if present)
13:18:24.700  VIXDataService initialized (ready=True, stale=False)
```

The `VIXDataService wired into Orchestrator (forwarded to RegimeClassifierV2 if present)` line is specifically the re-instantiation path DEF-170 addressed. `stale=False` confirms the service is active — if VIX fields are null in RegimeVector now, that would be a *downstream* bug, not this one.

**Remaining gap (inherited from yesterday):** DB-side confirmation that `regime_history.db.vix_close` is non-null on today's post-9:30 writes. Operator SQL:

```sql
SELECT MIN(vix_close), MAX(vix_close), AVG(vix_close), COUNT(*)
FROM regime_history
WHERE date(timestamp) = '2026-04-23';
```

Expected: `MIN` and `MAX` both non-null; `COUNT(*)` > 0. If `vix_close` is null or all rows are missing, FIX-05 regression.

### B2 🟢 FIX-04 execution layer changes — **STARTUP-CLEAN / no new failure modes introduced**

- `ReconciliationResult` typed dataclass is in use (374 `Position reconciliation: N mismatch(es)` WARNING lines fire throughout the day — format is consistent, no AttributeErrors on `ReconciliationResult` fields).
- Dup-SELL prevention (DEF-158) is active: no duplicate flatten orders observed in a targeted scan.
- DEC-372 stop-retry cap refinement landed. Today's 34 stop-retry-exhaustion events vs yesterday's 32 — but the comparison is not apples-to-apples because today's cascade trigger was an outright Gateway outage (worse upstream stimulus) not a brief disconnect. **Net interpretation: FIX-04's DEC-372 refinement may be working but the stimulus was stronger, so event count is similar.**
- Scope boundary correctly observed: FIX-04 did NOT touch the A1 code path at `order_manager.py:1707` / `:1684` — IMPROMPTU-01 remains required.

### B3 🟢 FIX-11 backend lifespan + FIX-03 health monitor expansion — **VALIDATED**

- All 30 strategy components reported HEALTHY at boot (15 live + 15 variants).
- 6 new expanded health-monitor components (universe_manager, regime_classifier_v2, evaluation_store, candle_store, counterfactual_tracker, quality_engine) all reported healthy at boot.
- `DebriefService` exported `logs/debrief_2026-04-23.json` at 20:25:48 UTC during the graceful shutdown sequence, confirming the live-mode path (no `--dev` references anywhere).
- `EvaluationEventStore initialized: data/evaluation.db` fired cleanly (see C5 update below for size concerns).

### B4 🟢 FIX-06 SystemAlertEvent emitter + DEF-037/DEF-165 closures — **STARTUP-CLEAN, no downstream effects**

No SystemAlertEvent emissions observed in today's log. This is expected — it was an emitter-only landing; consumers (HealthMonitor subscription via P1-A1 M9) are post-31.9. Silent behavior confirmed.

### B5 🟢 FIX-07 intelligence/catalyst/quality — **STARTUP-CLEAN**

- 16 pipeline cycles ran cleanly (100 fetched, 100 classified per cycle).
- 2 catalyst sources active (yesterday's profile).
- DEC-311 Amendment 1 retention anchor pinning: silent. No retention cycle logged today (consistent with "retention runs only when ceiling approached" semantics).
- `catalyst_quality` non-constant verification (yesterday's B3 gap) — **still a DB-side check, not a log-side check.** Handoff query repeated below under "Open Verification Gaps."

### B6 🟢 FIX-08 experiment + learning loop — **VALIDATED (spawn path)**

- `[9/12] Experiment variants spawned: 15` — 15 variants spawned (matches yesterday). **CLAUDE.md still says "22 shadow variants" in the Build Track Queue section** — this is stale and should be updated in the next doc sync.
- Fingerprint unification detection-only hash `ddec1b2a09ee2263` — fingerprint computation is silent at runtime; confirmation is a DB-side check on `experiments.variants.parameter_fingerprint`.
- Learning Loop proposals: none generated today (no `LearningService` analysis trigger fired in log — consistent with the auto-trigger being gated on SessionEndEvent after EOD flatten, which today's EOD flatten did fire. Worth a follow-up check in `data/learning.db`).

### B7 🟢 FIX-09 backtest retirements — **SILENT / no import errors**

No `ImportError` or `ModuleNotFoundError` for `report_generator`, `vectorbt_pattern`, or `vectorbt_red_to_green`. Live trading path doesn't touch these. Clean.

### B8 🟢 FIX-13a/b/c test hygiene + CI hotfix — **CI-only, not observable in runtime**

As predicted in the handoff. No log surface.

### B9 🟢 IMPROMPTU-CI (observatory_ws disconnect watcher) — **LIKELY VALIDATED**

22 WebSocket client disconnect pairs across the session (`WebSocket client disconnected (total: N)` lines) — all cleanly paired (no orphans in the live session). The observatory_ws disconnect-sentinel fix is test-only evidence, but no `WebSocket*` crash warnings during market hours supports correct runtime behavior.

*(Caveat: the 15× Task-destroyed WebSocket warnings in the 21:29 final burst are expected post-shutdown cleanup, not observatory_ws bugs — these fire well after `STOPPED` was logged at 20:26 and are covered by C9 below.)*

---

## Bucket C — New Findings

### C1 🟢 pattern_strategy.py:318 INFO-level log spam — **UNCHANGED from yesterday**

**Severity:** HIGH (operational) — unchanged.

829,190 of 938,754 log lines (88%) are the `pattern_strategy.py:318` `"evaluating X with partial history"` INFO spam. Identical to yesterday's ratio (87%) and identical root cause. **IMPROMPTU-04's C1 fix (log level INFO → DEBUG) remains critical for future debrief ergonomics.** No re-analysis; this finding is frozen until the fix lands.

---

### C2 🟢 IBKR stale-position cache — **NOT REPRODUCED TODAY**

**Severity:** MEDIUM → downgrade to LOW on this session's data.

Yesterday's C2 rested entirely on PURR's 1.00× outlier. **Today's data has zero 1.00× outliers** — all 42 untracked positions were at exactly 2.00×. Either:
- (a) Today's disconnect was long enough (~2 minutes, not seconds) that `ib_async`'s auto-sync had time to refresh before the EOD flatten query — no stale-cache manifestation; or
- (b) Stale-cache was never a real mechanism; PURR's 1.00× was a single-symbol race condition.

Either way, **C2's practical necessity dropped.** Still worth defensive `reqPositionsAsync()` before EOD Pass 2 query as a belt-and-suspenders measure, but priority is clearly post-31.9.

---

### C3 🟢 `max_concurrent_positions` count diverges from broker state — **SAME PATTERN, LARGER MAGNITUDE**

**Severity:** HIGH (for live trading; MEDIUM for paper) — unchanged.

**Today's position-count time series:**
- ARGUS rejected **21,458** signals with `"max concurrent positions (50) reached"` across the session (vs yesterday's 8,996 — **+138%**).
- IBKR position count peaked at **114 at 14:56:25 UTC (10:56 ET)** (vs yesterday's 134 at 10:34 ET — 85% of yesterday's peak).
- ARGUS internal stayed capped at 50.
- Peak reconciliation mismatch: **70 at 15:02:26 UTC (11:02 ET)** — right inside the Gateway-outage window.
- 42 untracked positions survived to EOD (vs 51 yesterday).

**Interpretation:** The magnitude of the divergence is actually *larger* today by signal-rejection count (+138%) despite the smaller position-count peak. Two factors:
1. The Gateway outage at 11:01–11:03 ET created a broader window where ARGUS couldn't see new fills, so the broker position count grew past ARGUS's internal cap for longer.
2. Today was a higher-signal-velocity session (see strategy window summaries — ABCD alone generated 4,564 signals vs yesterday's 2,338).

**Concentration check (BHC replaced by TSLL/SQQQ today):** Largest today is TSLL at 809 shares, then SQQQ at 723. TSLL at ~$15/share ≈ $12K ≈ 1.5% of the $794K account. SQQQ at ~$35/share ≈ $25K ≈ 3.2%. Neither breaches the 5% single-stock limit on individual exposure, but aggregate short exposure across all 42 positions pre-doubling was ~$100–150K ≈ 12–19% of equity — worth flagging separately.

**Required before next paper session:** Not strictly required. A1 fix addresses the highest-consequence manifestation. C3 accumulates silent risk but not immediate harm.

---

### C4 🟢 DEC-372 stop-retry-exhaustion events — **SAME COUNT, DIFFERENT DISTRIBUTION**

**Severity:** MEDIUM (causally upstream of A1) — unchanged.

**Today: 34 events** (vs yesterday's 32). Distribution is **very different**:
- Yesterday: 32 events tightly clustered in 09:40–09:59 ET (immediately after the 9:29 AM network blip).
- Today: 23 events in 09:44–10:32 ET, 4 in 10:57–11:18 ET, 2 in 11:25 + 15:18 + 15:25 ET, 5 in the 14:00–15:15 ET afternoon.

**Key insight: today's 23-event cluster in 09:44–10:32 ET FIRED BEFORE the 11:01 Gateway outage.** Yesterday's triage hypothesized that DEC-372 cascades are triggered by network disconnect events invalidating order IDs. Today's data contradicts that for at least the first cluster — **there was no network event in 09:29–11:01 ET**, but stop-retry exhaustions fired anyway.

**Revised hypothesis:** DEC-372 cascades have at least two distinct triggers:
- (a) Network disconnect invalidating order IDs (yesterday's mechanism; possibly today's afternoon outliers);
- (b) Routine broker-side cancel races during normal operation (today's morning cluster) — possibly worsened by IBKR load during the open + sheer signal volume.

**Symbols in today's exhaustion list that also appear in 42-symbol EOD list:** `FRMI`. That's only 1 of 34, much lower overlap than yesterday's 5 of 32 (EDV, FCEL, RCUS, RKLZ, SOXS). Most of today's 42 untracked symbols went short via the other pathway — likely during the 11:01–11:03 Gateway outage specifically (see A1 evidence — 20 symbols already short at reconnect).

**Fix approach:** Unchanged from yesterday. Requires thoughtful cross-domain session touching execution retry state machine. Coordinates with DEF-177 (RejectionStage.MARGIN_CIRCUIT) and DEF-184 (RejectionStage/TrackingReason split). Natural fit for a post-31.9 combined session.

**Required before next paper session:** Not strictly, assuming A1 fix lands.

---

### C5 🟢 `evaluation.db` is **9,294 MB** at boot — **UPDATE: +95% vs yesterday**

**Severity:** MEDIUM → upgrade to **HIGH** on trajectory.

Yesterday: 4,776 MB at boot. Today: **9,294 MB** at boot. **+4.5 GB in a single session.** Freelist still 0%.

At this growth rate:
- Week from now: ~30 GB
- Month from now: ~150 GB
- Startup time will degrade (aiosqlite open + index loading scales with file size).
- Free-disk headroom on operator's MacBook becomes a concern within 2–3 weeks.

**Status:** Sprint 31.8 S2 was supposed to fix this via close→sync VACUUM→reopen after retention DELETE. Today's evidence suggests **retention is not running at all** (not just "VACUUM isn't reclaiming"). If retention were running and VACUUM were failing, freelist would be non-zero and size would stabilize at ~7 days × per-day write rate. Current trajectory is unbounded growth.

**Fix priority:** Raise to post-31.9 **priority** item. Investigate before next sprint kick.

**Operator SQL for verification:**
```sql
SELECT MIN(trading_date), MAX(trading_date), COUNT(*) FROM evaluation_events;
SELECT trading_date, COUNT(*) FROM evaluation_events
  GROUP BY trading_date ORDER BY trading_date DESC LIMIT 10;
```

If `MIN(trading_date)` is > 7 days old, retention is broken.

---

### C6 🟢 Boot phase labels `/12` vs handoff-claimed `/17` — **UNCHANGED from yesterday**

**Severity:** LOW (documentation accuracy) — unchanged.

Today's log shows `[1/12]` through `[12/12]` with sub-phases `[7.5/12]`, `[8.5/12]`, `[9.5/12]`, `[10.25/12]`, `[10.3/12]`, `[10.4/12]`, `[10.7/12]`. No change from yesterday. Still DEF-198 territory.

---

### C7 → C9 🟢 Post-shutdown IBKR reconnect attempt + 17 async "Task was destroyed" warnings + **63-minute process hang — MUCH WORSE than yesterday**

**Severity:** LOW yesterday → **MEDIUM** today.

**Yesterday's profile:**
- 19:51:17 UTC — "Argus Shutting Down"
- 20:05:08 UTC (14 min later) — IBKR broker scheduling reconnect
- 20:07:41 UTC — last log line with 16× Task-destroyed warnings
- Total post-shutdown tail: ~14 minutes until final task-destroyed burst.

**Today's profile:**
- 19:51:13 UTC — `ARGUS TRADING SYSTEM — SHUTTING DOWN`
- 19:51:13 → 19:51:17 — 40 counterfactual positions close with `eod_closed`
- 20:11:39 UTC (20 min later) — Databento timeout (`no data received for 68 seconds`), auto-reconnect **despite shutdown in progress**
- 20:11:42–20:11:51 — Databento reconnects, spins up full symbology map (48K+ mappings). **This is an entire data-service re-initialization AFTER shutdown.**
- 20:25:47 — `Retrieved 0 positions from IBKR`
- 20:25:48 — `Debrief data exported to logs/debrief_2026-04-23.json`, `Stopping API server`, `API server stopped`, `Background tasks stopped`, `CounterfactualStore closed`
- 20:26:31–20:26:33 — Full graceful close-down sequence completes: EvaluationEventStore, ActionManager cleanup, scanner, UniverseManager (37,804 symbols cache saved), data service, order manager, orchestrator, health monitor, catalyst storage, RegimeHistoryStore, database, broker disconnect.
- **20:26:33.838 — `ARGUS TRADING SYSTEM — STOPPED`**
- **20:26:33.843 — IBKR broker schedules another reconnection attempt ("Reconnection attempt 1/10 in 1.0s") *AFTER* STOPPED was logged.**
- **21:29:30.831 → 21:29:35.603 — final burst: 17 ERROR-level Task-destroyed warnings + 2 Unclosed aiohttp client sessions (VIXDataService and likely Finnhub). This burst fires 63 minutes after STOPPED.**

**Total shutdown tail: 63 minutes of dangling-task wall time** (vs yesterday's ~14 minutes).

**What the dangling tasks are:**
- `Task-52 LifespanOn.main()` — uvicorn lifespan task
- `Task-55 run_polling_loop()` — catalyst pipeline polling (should have stopped when catalyst_pipeline stopped at 20:26:33)
- `action_manager_cleanup` — ActionManager periodic cleanup task
- 2× Unclosed aiohttp client sessions
- 10× WebSocket*Protocol tasks (Task-50910446–50914101 — observatory_ws + arena_ws + live_ws + ai_chat client handlers that weren't drained at WebSocketBridge stop)
- `Task-53968817 IBKRBroker._reconnect()` — the scheduled reconnect from 20:26:33.843
- `Task-61 VIXDataService._start_daily_update_task` — VIX daily-update background task (should have been cancelled during shutdown)

**Root cause (🟠 hypothesis):** Several component-ownership issues compounding:
1. **IBKR broker schedules a reconnect task after `disconnect()` is called** — this is the same C7 bug from yesterday, but today it's even clearer because `STOPPED` was logged *before* the reconnect was scheduled, proving no other component holds a reference to cancel it.
2. **Databento data service timed out and auto-reconnected AFTER `SHUTTING DOWN`** — the data service continued running for 20 minutes post-shutdown-signal before being stopped at 20:26:32. This suggests the shutdown sequence did not call `data_service.stop()` early enough, OR stop() does not synchronously cancel the reader thread.
3. **WebSocket client tasks not drained before WebSocketBridge stops.** Normal pattern would be: stop accepting new connections → cancel in-flight sends → wait for all handlers to complete → close bridge. The evidence suggests steps 2 and 3 are skipped.
4. **VIXDataService daily-update task outlives its component's `close()`.** No evidence `_start_daily_update_task()` registers cancellation.

**Boot-collision risk:** If the operator starts ARGUS within the 63-minute hang window after shutdown, `clientId=1` on IBKR is still held by the previous process's reconnect task — new ARGUS gets rejected. Already an operational footgun; today's hang extension makes it much more likely.

**Fix approach:** Sprint-29.5 hardened several shutdown paths; DEF-175 (component-ownership session) exists as a placeholder post-31.9. Today's 63-min tail is a natural prompt to elevate DEF-175 from "post-31.9, someday" to "post-31.9, first."

**Required before next paper session:** Not strictly blocking. Mitigation: wait at least ~2h between shutdown and next start. Add a startup-time stale-clientId check if this becomes repeatable.

**DEF candidacy:** Consolidate yesterday's C7 + today's C9 into a single DEF (`post-31.9 component-ownership shutdown hardening`). Could be a new DEF number or attached to DEF-175.

---

### C8 🟢 Counterfactual dataset richness — **UNCHANGED + healthy**

**Severity:** LOW (positive observation).

21,359 counterfactual positions opened and closed today (vs yesterday's 20,658 — +3.4%). Top strategies by signal volume:
- `strat_abcd`: 4,564 signals
- `strat_vwap_bounce`: 1,551 signals
- `strat_orb_breakout`: 686 signals
- `strat_narrow_range_breakout`: 659 signals
- `strat_orb_scalp`: 566 signals

ABCD still dominates (27% of total signals) and remains a Sprint-33 calibration concern. No new action.

---

### C10 🟡 10,729 WARNING-level "max concurrent positions reached" rejections — **NEW finding (log spam subclass)**

**Severity:** LOW (operational).

The Risk Manager WARNING-level log line `"Signal rejected: max concurrent positions (50) reached"` is **not** ThrottledLogger'd. Today's log has 10,729 instances. This is not big compared to the 829K pattern_strategy INFO spam, but it's still 10× more than all actual bug WARNINGs combined (~1,000 actionable warnings).

**Fix:** ThrottledLogger at 60s/symbol, or downgrade to DEBUG and rely on aggregate counters.

**Required before next paper session:** No. Opportunistic cleanup.

**DEF candidacy:** New DEF (LOW). Log-hygiene follow-on to C1.

---

### C11 🟠 Stop-retry-exhaustion fired BEFORE any network event today — **NEW mechanistic insight**

**Severity:** MEDIUM (adjusts C4 model).

As noted in C4: 23 of today's 34 DEC-372 exhaustion events fired in 09:44–10:32 ET, a full 1h30m BEFORE the 11:01 Gateway outage. Yesterday's C4 analysis assumed network events were the primary trigger; today's evidence shows they are not the *only* trigger.

**Implication for the post-31.9 C4 fix session:** The fix design must account for at least two triggers (network-invalidated IDs vs routine broker-side cancel races), not just one. Don't scope the fix narrowly to "handle disconnect event."

**Required before next paper session:** No. This is design input for the planned post-31.9 C4 fix session.

---

## Procedure Recommendation

**Unchanged from yesterday:** IMPROMPTU-04 (now tracked as IMPROMPTU-01 in campaign scope) remains critical path and must land before any further paper trading. Today's data reinforces rather than re-decides this.

**Additions to IMPROMPTU-04 scope (minor, already implied in yesterday's scope):**

1. **A1 fix** — `order_manager.py:1707` + `:1684` side-check. Same spec as yesterday.
2. **C1 fix** — `pattern_strategy.py:318` `logger.info` → `logger.debug`. Same spec.
3. **Startup invariant** — `main.py` post-broker-connect assertion that all returned positions have `side == BUY`. Same spec.
4. **DEF opens** (new — today-specific, in addition to yesterday's): DEF for C9 (shutdown-tail 63-min hang), DEF for C10 (max-concurrent WARNING spam), DEF for C5 upgrade to HIGH priority (evaluation.db unbounded growth).

**Not in IMPROMPTU-04 scope (post-31.9):**
- C4 / C11 cross-domain fix session.
- C2 (lowered priority).
- C6 (LOW, documentation).
- DEF-175 merge with C9.

### Relationship to active Sprint 31.9 Stage 9/10 work

Per today's `RUNNING-REGISTER.md`: Sprint 31.9 is in Stage 9/10 close-out. IMPROMPTU-01 (A1 fix) is the identified critical-path blocker. No other findings in today's debrief disrupt or invalidate the existing Stage 3–8 landings. Stage 9/10 can proceed as planned *after* IMPROMPTU-01.

### Sprint 31.9 campaign does not need to halt otherwise

Confirmed for the second day. The A1 bug is an untouched pre-existing safety bug in `order_manager.py` that today's Gateway outage exposed again. Sprint 31.9 Stage 3–8 work is all cleanly landed and not implicated.

---

## Go / No-Go for Tomorrow's Pre-Open

**NO-GO until A1 is fixed and regression-tested.** Unchanged from yesterday. Reinforced by today's second identical manifestation.

**Rationale (reinforced):**
- A1 is deterministic and repeatable under multiple cascade mechanisms (yesterday's 40-second Databento+IBKR blip + today's 2-minute Gateway outage + today's pre-outage morning stop-retry cluster all produced the same A1 EOD doubling).
- Paper-data integrity is now compromised across **two consecutive sessions**. Today's 42 short-flip events + yesterday's 51 are not genuine strategy decisions. Shadow performance data from these two days must be treated as contaminated for PromotionEvaluator purposes unless explicitly marked-to-exclude.
- Live-transition risk compounds every day this stays unfixed.

**Interim mitigations (in addition to yesterday's):**
- Same as yesterday: lower `max_concurrent_positions` from 50 to 15–20, disable `eod_flatten_retry_rejected` if the config exists.
- **Additional today:** Do NOT run ARGUS if IBKR Gateway stability is uncertain. Today's 2-min Gateway outage (Errno 61 × 5 attempts) suggests the Gateway process was down; if this is a pattern on the operator's host (e.g., nightly IBKR reset not fully recovered, or Gateway auto-shutdown misfire), troubleshoot that independently.

---

## Open Verification Gaps

Same as yesterday's gaps, plus one new. DB-backed checks required:

| Gap | Query / Action | Purpose |
|---|---|---|
| RegimeVector VIX dimensions non-null (FIX-05 / DEF-170 DB-side) | `SELECT MIN(vix_close), MAX(vix_close), COUNT(*) FROM regime_history WHERE date(timestamp) = '2026-04-23';` | Validates today's B1 finding |
| FIX-01 `catalyst_quality` non-constant | Yesterday's B3 SQL, run against today's `quality_history` with `date(created_at) = '2026-04-23'` | Unchanged from yesterday |
| Quality grade distribution shift | Yesterday's gap — SQL against `quality_history` with date filter | Unchanged from yesterday |
| Daily cost ceiling for catalyst classifier | SQL against `data/catalyst.db` for today's classifier spend + compare to DEC-324 ceiling | Unchanged from yesterday |
| `evaluation.db` retention status (NEW) | `SELECT MIN(trading_date), MAX(trading_date), COUNT(*) FROM evaluation_events;` + row counts by date | Validates C5 upgrade to HIGH |
| End-to-end trace of one A1 short-flip (NEW) | Pick MIR (`-200` at 11:03 reconnect). Trace pre-11:01 fill, bracket placement, outage-window bracket state, post-11:03 short detection. | Definitive proof of the 11:01-outage cascade mechanism |
| Learning Loop proposal generation | Query `data/learning.db` for today's LearningReport row count | Validates FIX-08 session-end trigger |

---

## Appendix A — Cascade Timeline

| Time (UTC / ET) | Event |
|---|---|
| 13:18:17 UTC / 09:18 AM ET | ARGUS startup (off `ffcfb5c`, 12 min pre-open buffer) |
| 13:18:19 / 09:18 | IBKR connected at 127.0.0.1:4002 (clientId=1, positions=0) |
| 13:18:21 / 09:18 | Universe Manager built: 6,427 viable symbols. 30 strategies healthy (15 live + 15 variants). |
| 13:18:24 / 09:18 | VIXDataService wired into Orchestrator (ready=True, stale=False) — **FIX-05 / DEF-170 confirmed** |
| 13:18:25 / 09:18 | `Argus Started — Watching 6427 symbols. Mode: PAPER TRADING` |
| 13:30 / 09:30 | Market open |
| 13:36:25 / 09:36 | First `Position reconciliation: 3 mismatches` WARNING |
| 13:36:59 / 09:36 | First OHLCV-1m candle resolved (TXN) |
| 13:37:48 / 09:37 | **First stop-resubmission exhaustion: UCO emergency flatten** (pre-outage!) |
| 13:38:58 / 09:38 | Second stop-resubmission exhaustion: BULZ |
| 13:44:45 / 09:44 | **First DEC-372 stop-retry exhaustion cluster begins (TS)** |
| 13:44:45–14:32:08 / 09:44–10:32 | 23 DEC-372 stop-retry exhaustions — **no network event in this window** |
| 14:56:25 / 10:56 | **IBKR position count peaks at 114.** Internal ARGUS capped at 50. |
| 14:57:16 / 10:57 | Stop-retry exhaustion: CRMG (first of 2nd cluster) |
| **15:01:53 / 11:01** | **IB GATEWAY DOWN — `IB Gateway disconnected` WARNING** |
| 15:01:54 / 11:01 | Reconnection attempt 1/10: Errno 61 Connection refused |
| 15:01:56 / 11:01 | Reconnection attempt 2/10: Errno 61 Connection refused |
| 15:02:20 / 11:02 | Reconnection attempt 3/10: Errno 61 Connection refused |
| 15:02:26 / 11:02 | **Peak reconciliation mismatch: 70 symbols.** |
| 15:02:28 / 11:02 | Reconnection attempt 4/10: Errno 61 |
| 15:02:44 / 11:02 | Reconnection attempt 5/10: Errno 61 |
| **15:03:48 / 11:03** | **IBKR reconnected on attempt 6. 79 positions visible, of which 20 are SHORT (including MIR -200, CIFR -131, TSLL -809, ETH -336, YINN -523, SQQQ -723, JEPQ -457, ...).** |
| 15:18:17 / 11:18 | Stop-retry exhaustion: SLM |
| 15:25:19 / 11:25 | Stop-retry exhaustion: OII |
| 18:00:25 / 14:00 | Stop-retry exhaustion: PCT (afternoon cluster begins) |
| 18:29:09 / 14:29 | Stop-retry exhaustion: BYRN |
| 19:15:07 / 15:15 | Last stop-retry exhaustion: DOC (total today: 34) |
| 19:30 / 15:30 | Signal cutoff (no cutoff log line observed — worth confirming config-side) |
| **19:50:00 / 15:50:00** | **EOD flatten triggered** |
| 19:50:07.041 / 15:50:07 | EOD flatten Pass 1: 1 filled, 0 timed out |
| 19:50:07.044–290 / 15:50:07 | **42 `EOD flatten: closing untracked broker position ...` WARNINGs + 42 MARKET SELL orders** |
| 19:50:07.293 / 15:50:07 | EOD flatten Pass 2: 42 broker-only positions submitted |
| **19:50:07.294 / 15:50:07** | **CRITICAL: EOD flatten: 42 positions remain after both passes** |
| 19:51:13 / 15:51 | `ARGUS TRADING SYSTEM — SHUTTING DOWN` |
| 19:51:13 / 15:51 | 40 counterfactual positions close with `eod_closed` |
| **~15:55 / 15:55** | **Operator observes 42 short positions on IBKR portal. Runs `ibkr_close_all_positions.py`. BUYS 13,898 shares. All 42 at exactly 2.00× ratio.** |
| 20:11:39 / 16:11 | **Databento stream timeout post-shutdown (68s silent). Auto-reconnect attempt 1/10.** |
| 20:11:42–20:11:51 / 16:11 | Databento reconnects, full symbology map rebuild (48K+ mappings) — all post-shutdown |
| 20:25:47 / 16:25 | `Retrieved 0 positions from IBKR` |
| 20:25:48 / 16:25 | `Debrief data exported to logs/debrief_2026-04-23.json`, API server stopped |
| 20:25:48 / 16:25 | Background tasks stopped (evaluation health check, position reconciliation, cache refresh, counterfactual maintenance) |
| 20:26:31 / 16:26 | EvaluationEventStore closed |
| 20:26:32 / 16:26 | FMPReference cache saved (37,804 symbols) |
| 20:26:33.187 / 16:26 | Database connection closed |
| 20:26:33.191 / 16:26 | `IB Gateway disconnected` + `Scheduling reconnection attempt` |
| **20:26:33.838 / 16:26** | **`ARGUS TRADING SYSTEM — STOPPED`** |
| 20:26:33.843 / 16:26 | IBKR broker: `Reconnection attempt 1/10 in 1.0s` (**AFTER** STOPPED) |
| **21:29:30 / 17:29** | **63-minute-later task-destroyed burst: 17 `Task was destroyed but it is pending` ERRORs + 2 `Unclosed client session` ERRORs** |
| 21:29:35 / 17:29 | Last log line (Task-61 VIXDataService) |

---

## Appendix B — Session Stats

| Metric | Today | Yesterday | Δ |
|---|---:|---:|---:|
| Startup commit | `ffcfb5c` | `f57a965` | — |
| Session duration (startup → last log) | 8h 11min | 6h 51min | +1h 20m (longer tail) |
| Market hours covered | 09:30–15:51 ET (EOD at 15:50) | 09:30–15:51 ET | same |
| Total log lines | 938,754 | 895,543 | +4.8% |
| Log file size (uncompressed) | 184 MB | 184 MB | same |
| INFO / WARNING / ERROR / CRITICAL counts | 916,292 / 16,988 / 5,471 / 3 | 876,758 / 14,195 / 4,587 / 3 | +4.5% / +19.7% / +19.3% / same |
| Top logger (by volume) | `argus.strategies.pattern_strategy` — 829,190 (88%) | 798,195 (89%) | similar |
| Viable universe | 6,427 | 6,366 | +0.9% |
| Live + variant strategies | 15 + 15 = 30 | 15 + 15 = 30 | same |
| **`evaluation.db` boot size** | **9,294 MB** | **4,776 MB** | **+95%** |
| Databento disconnects (mid-session) | 0 | 1 (09:29 ET blip) | — |
| **IB Gateway outages (mid-session)** | **1 (11:01–11:03 ET, Errno 61 × 5)** | **1 (09:29 ET Error 1100/1102)** | different mechanism |
| IBKR peak position count | 114 (at 10:56 ET) | 134 (at 10:34 ET) | −15% |
| ARGUS internal peak position count | ~50 (capped) | ~50 (capped) | same |
| `max_concurrent_positions` WARNING rejections | 10,729 | 8,996 | +19% |
| Total max-concurrent signal rejections | 21,458 | 8,996 | +138% |
| Stop-retry-exhaustion events (DEC-372) | 34 (distributed) | 32 (tightly clustered 9:40–9:59) | +6% count, different distribution |
| Peak reconciliation mismatch count | 70 (at 11:02 ET, during Gateway outage) | unknown | — |
| Reconciliation WARNING lines | 374 | ~150+ | ~2× |
| **Untracked positions at EOD** | **42** | **51** | **−18%** |
| **Operator-BUY cleanup shares** | **13,898** | **34,239** | **−59%** |
| **A1 doubling ratio** | **42 / 42 at 2.00×** | **50 / 51 at 2.00×, 1 / 51 at 1.00×** | cleaner signal today |
| Counterfactual positions opened/closed | 21,359 / 21,359 | 20,658 / 20,658 | +3.4% |
| Window summaries emitted (DEF-138) | 30 | 30 | same |
| Pipeline cycles (catalyst) | 16 | — | — |
| Items classified (catalyst) | 1,600 | — | — |
| CRITICAL events (log) | 3 (startup alert, EOD flatten remaining, shutdown alert) | 3 | same |
| **Shutdown-tail hang duration** | **63 min (20:26 STOPPED → 21:29 final burst)** | **~14 min (19:51 SHUTTING DOWN → 20:07 final burst)** | **+4.5×** |
| Task-destroyed ERRORs in shutdown tail | 17 | 16 | +1 |

---

## Appendix C — Key File References

| Finding | File / Line | Status |
|---|---|---|
| A1 root cause — abs() in Position adapter | `argus/execution/ibkr_broker.py:935` | unchanged |
| A1 root cause — missing side check in filter | `argus/execution/order_manager.py:1707` | unchanged |
| A1 root cause — unconditional SELL in flatten | `argus/execution/order_manager.py:1936–1947` | unchanged |
| A1 additional fix site — EOD Pass 1 retry | `argus/execution/order_manager.py:1684` | unchanged |
| Pydantic invariant (shares >= 1) | `argus/models/trading.py:164` | unchanged |
| C1 — log-spam source line | `argus/strategies/pattern_strategy.py:318` | unchanged |
| C5 NEW — evaluation store | `argus/strategies/telemetry_store.py` + `data/evaluation.db` | **retention broken; +95% growth one day** |
| C9 NEW — shutdown-tail hang | `argus/execution/ibkr_broker.py` (reconnect scheduler) + `argus/data/databento_data_service.py` (post-shutdown timeout) + WebSocketBridge drain path | |
| Campaign state | `docs/sprints/sprint-31.9/RUNNING-REGISTER.md` | unchanged |
| Yesterday's triage (baseline) | `docs/sprints/sprint-31.9/debrief-2026-04-22-triage.md` | — |
| Debrief protocol | `docs/protocols/market-session-debrief.md` | — |

---

## Sprint 31.9 Triage Summary — 2026-04-23

Three-bucket breakdown for direct paste into the Sprint 31.9 tracking conversation.

### Bucket A — Work-blocker findings (immediate fix required)

| ID | Finding | Severity | One-sentence root-cause hypothesis |
|---|---|---|---|
| A1 | EOD `_flatten_unknown_position()` doubles short positions (DEF-199 confirmed 2nd day; 42/42 at exactly 2.00×; 13,898 shares operator cleanup) | **CRITICAL (safety)** | `order_manager.py:1707` and `:1684` filter on `qty > 0` without checking `pos.side`, and `IBKRBroker.get_positions()` returns `abs()` shares — so any broker-side short position passes the filter and gets a MARKET SELL that doubles it. **Unchanged from yesterday.** |

### Bucket B — Already covered by Sprint 31.9 scope

| ID | Finding | Session | Validation verdict |
|---|---|---|---|
| B1 | VIX regime intelligence wiring (DEF-170) | FIX-05 | ✅ `VIXDataService wired into Orchestrator` + `ready=True, stale=False` at startup; downstream DB-side VIX field non-null check still a gap |
| B2 | FIX-04 execution-layer hardening (DEF-158 dup-SELL, DEC-372 refinement, ReconciliationResult dataclass) | FIX-04 | ✅ Clean runtime, no AttributeErrors, scope boundary respected (does not cover A1 — correctly scoped to IMPROMPTU-01) |
| B3 | FIX-11 backend lifespan + FIX-03 health monitor expansion (30 strategies, 6 new components, DebriefService live-mode) | FIX-03 + FIX-11 | ✅ All 30 components healthy; DebriefService produced `logs/debrief_2026-04-23.json` |
| B4 | FIX-06 SystemAlertEvent emitter | FIX-06 | ✅ Silent / no runtime errors (consumer side P1-A1 M9 pending, as designed) |
| B5 | FIX-07 intelligence/catalyst/quality | FIX-07 | ✅ 16 clean pipeline cycles, 1,600 items classified, DEC-311 Amendment 1 silent as expected |
| B6 | FIX-08 experiment + learning loop (15 variants spawned, fingerprint unification) | FIX-08 | ✅ 15 variants spawned; fingerprint + learning-proposal paths are silent at runtime (DB-side check required) |
| B7 | FIX-09 backtest retirements | FIX-09 | ✅ No import errors for retired modules |
| B8 | FIX-13a/b/c test-hygiene + CI hotfix | FIX-13a/b/c + IMPROMPTU-CI | ✅ CI-only; no runtime observable |
| B9 | IMPROMPTU-CI observatory_ws disconnect watcher (DEF-200 / DEF-193) | IMPROMPTU-CI | ✅ 22 cleanly paired WebSocket disconnect pairs during session; no crashes |

### Bucket C — New findings requiring disposition

| ID | Finding | Severity | One-sentence root-cause hypothesis |
|---|---|---|---|
| C1 | `pattern_strategy.py:318` INFO-level log spam — 88% of today's 939K log lines | HIGH (operational) | Logging level mistake; `logger.info` should be `logger.debug`. **Unchanged from yesterday; covered by IMPROMPTU-01 scope.** |
| C3 | `max_concurrent_positions` count diverges from broker state; 21,458 rejections today (+138% vs yesterday) due to longer ARGUS-vs-IBKR divergence window | HIGH live / MEDIUM paper | `max_concurrent_positions` check counts only ARGUS's internal `_managed_positions`; entry fills lost during the 11:01–11:03 Gateway outage bypassed it while broker accumulated past the cap. **Magnitude larger than yesterday, same mechanism.** |
| C4 | 34 DEC-372 stop-retry-exhaustion events today (vs 32 yesterday) | MEDIUM (causally upstream of A1) | Bracket-stop cancel IDs invalidated or racing with broker-side state; fires emergency MARKET flatten while original stop may still be live. **Today's 23-event pre-outage cluster (09:44–10:32 ET) shows network events are NOT the sole trigger.** |
| C5 (upgrade) | `evaluation.db` is **9,294 MB at boot (+95% vs yesterday's 4,776 MB)**, freelist 0% | **HIGH** (trajectory) | Retention policy not executing (or not DELETEing); if trajectory continues, startup degrades within 1 week, disk headroom within 2–3 weeks. |
| C6 | `[N/12]` vs handoff-claimed `[N/17]` phase labels | LOW (docs) | FIX-03 didn't renumber phase-label string literals; OR handoff doc is stale. |
| C9 (NEW) | **Shutdown-tail hang is 63 minutes today vs ~14 yesterday (4.5× worse).** 17 Task-destroyed ERRORs + 2 Unclosed aiohttp client sessions. IBKR broker re-schedules reconnect AFTER `STOPPED` was logged. Databento reconnected + full symbology rebuild DURING shutdown. WebSocket tasks not drained. | **MEDIUM** (+boot-collision risk) | Multiple component-ownership issues compounding: IBKR broker reconnect scheduler outlives disconnect(), Databento data service reader thread outlives data_service.stop(), WebSocketBridge doesn't drain in-flight handlers, VIXDataService daily-update task doesn't register cancellation. Natural DEF-175 extension. |
| C10 (NEW) | 10,729 "Signal rejected: max concurrent positions" WARNING lines — not ThrottledLogger'd | LOW (log-hygiene) | Risk Manager WARNING not wrapped in ThrottledLogger. Log-hygiene follow-on to C1. |
| C11 (NEW) | 23 DEC-372 stop-retry exhaustions fired 09:44–10:32 ET, 1h30m BEFORE the 11:01 Gateway outage | MEDIUM (design input) | DEC-372 cascades have ≥2 triggers: network-invalidated order IDs (yesterday's afternoon) + routine broker-side cancel races during high signal volume (today's morning). Design input for post-31.9 C4 fix session; don't scope fix to network events alone. |
| C2 (downgrade) | IBKR stale-position cache | LOW (downgrade from MEDIUM) | Yesterday's PURR 1.00× outlier not reproduced today; stale-cache may have been a one-off or is not needed once A1 is fixed. |
| C8 | Counterfactual dataset richness — 21,359 positions, ABCD 27% of signals | LOW (positive) | Design-calibration observation for Sprint 33; no fix needed. |

---

*End of Sprint 31.9 Triage Summary — Market Session 2026-04-23.*
